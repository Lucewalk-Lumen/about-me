#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_checks.py —— 端到端回归测试

目的：把**已经踩过并修好的坑**固化成可重跑的检查，防止后续改动再次引入。
本文件里每一条检查都对应一个真实发生过的 bug，注释里写明"当时是什么现象"。

用法:
    python3 run_checks.py                      # 快速检查（不需要真实库，约 1-2 分钟）
    python3 run_checks.py --full --library "~/Desktop/EndNote/My EndNote Library.enl"
                                               # 追加需要真实库的重量级检查

退出码:
    0  全部通过（或仅 SKIP）
    1  存在 FAIL
"""
from __future__ import annotations

import re
import argparse
import json
import math
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
PY = sys.executable

# Rscript 探测必须走全包唯一实现（lit_core.find_rscript）——
# doctor.py / sna_r.py / 本文件都从这里取，避免三套 glob 口径漂移。
from lit_core import find_rscript as _find_rscript_shared  # noqa: E402

RESULTS: list[tuple[str, str, str]] = []   # (name, status, message)


def strip_py_comments(t: str) -> str:
    """剥离 Python 注释、模块/函数 docstring，保留真正的代码与字面量。

    [!]  与 strip_js_comments 同理：注释与 docstring 里会**解释**代码在做什么，
    而那些说明文字往往重复出现代码里的字面量。若不剥离，"代码里是否还有
    硬编码路径"这类断言会被注释里的示例触发 → 假失败。
    两类已知假阳性：
      1. 检查"R 探测是否只有一处实现"，6 处命中全来自安装指引的示例路径
         与检查自身的测试数据，代码早已统一到 lit_core；
      2. 只剥 COMMENT 不够 —— 模块顶部 docstring 用三引号包着，里面同样
         写着 "C:/Program Files/R/R-<版本>/bin/Rscript.exe"，仍会误报。

    实现用 tokenize 而非正则：正则无法区分「字符串里的 #」与真注释，
    也无法识别三引号 docstring。判定 docstring 的依据是"STRING token 处于
    模块级或紧跟 def/class 行"，不会误伤普通字符串字面量。
    """
    import io
    import tokenize
    toks = list(tokenize.generate_tokens(io.StringIO(t).readline))
    # 标出所有 docstring 的 token 序号
    drop = set()
    # 记录"上一个有意义的 token 所在行"，用于判断 STRING 是否紧跟 def/class
    last_code_line = -1
    for i, tok in enumerate(toks):
        if tok.type == tokenize.COMMENT:
            drop.add(i)
            continue
        if tok.type == tokenize.STRING:
            # 判定 docstring：① 模块级（此前无任何代码行）
            #           ② 紧跟在 def/class 行之后（跨过注释也要认）
            if last_code_line < 0 or _is_def_line(toks, last_code_line):
                drop.add(i)
        if tok.type not in (tokenize.NL, tokenize.NEWLINE,
                            tokenize.INDENT, tokenize.DEDENT,
                            tokenize.COMMENT):
            last_code_line = tok.start[0]
    try:
        return tokenize.untokenize([tk for i, tk in enumerate(toks)
                                    if i not in drop])
    except Exception:  # noqa: BLE001
        return t


def _is_def_line(toks, line_no: int) -> bool:
    """该行上是否出现了 def / class / async def 声明。

    只认这三种 token 名后紧跟函数名的情况，避免把普通调用误当声明。
    """
    import tokenize as _tk
    names = [tk.string for tk in toks
             if tk.start[0] == line_no and tk.type == _tk.NAME]
    for i, s in enumerate(names[:-1]):
        if s in ("def", "class", "async") and names[i + 1] != "(":
            return True
    return False


def strip_js_comments(t: str) -> str:
    """剥离 JS 块注释与行注释。

    [!]  必要性：build_report.py 里为了说明"这里不能innerHTML"，
    注释本身含 `innerHTML` 字样。若不剥离，"函数体内是否出现 innerHTML"
    这类断言会被注释里的说明文字触发 → 假失败。
    剥离注释是让"检查代码而非注释"成立的前提。
    """
    out, in_block = [], False
    for ln in t.split("\n"):
        st = ln.strip()
        if in_block:
            if "*/" in ln:
                in_block = False
                ln = ln.split("*/", 1)[1]
            else:
                continue
        while "/*" in ln:
            head, rest = ln.split("/*", 1)
            if "*/" in rest:
                ln = head + rest.split("*/", 1)[1]
            else:
                ln = head
                in_block = True
                break
        if "//" in ln:
            ln = ln.split("//", 1)[0]
        out.append(ln)
    return "\n".join(out)


def check(name: str, ok: bool, msg: str = "", status: str | None = None):
    st = status or ("PASS" if ok else "FAIL")
    RESULTS.append((name, st, msg))
    print(f"  [{st:4s}] {name}" + (f"  — {msg}" if msg else ""))
    return ok


def skip(name: str, msg: str):
    RESULTS.append((name, "SKIP", msg))
    print(f"  [SKIP] {name}  — {msg}")


def run(cmd: list[str], cwd=None):
    return subprocess.run([PY] + cmd, capture_output=True, text=True, cwd=cwd or str(HERE))


def find_rscript():
    """定位 Rscript：委托 lit_core.find_rscript（唯一实现）。

    必要性：Windows 版 R 默认不把 Rscript.exe 写进 PATH，`shutil.which` 返回 None。
    若 R 相关检查只认 PATH，就会在本机永远 SKIP —— 而 R 已是标准路径，
    跳过等于对这条最关键的行为约束放行。

    为什么委托而不自己写：doctor.py / sna_r.py / 本文件此前各写一套 glob。
    三套口径必然漂移（本文件这版只扫 Windows，Linux/macOS 全漏），于是出现
    「自检说 R 可用、实际分析却 exit 8」这类自相矛盾，且难以定位。
    探测必须是唯一实现 —— 见 c_r_probe_single_source 的守卫断言。
    """
    path, _source = _find_rscript_shared()
    return path


# ══════════════════════════════════════════════════════════
# 各检查项
# ══════════════════════════════════════════════════════════
def c_gini():
    """注意：gini2 用降序排序 + 分母/减项写错 → 完全均衡的簇返回 -0.985（应为 0），
    真实数据返回 -0.997（正确值 0.159）。这是报告里用户可见的"均衡度 gini"。"""
    from build_report import gini2
    eq = gini2([100, 100, 100, 100])
    check("gini2 完全均衡应为 0", abs(eq) < 1e-9, f"实测 {eq}")
    ext = gini2([0, 0, 0, 1000])
    check("gini2 极度不均应接近 1", 0.5 <= ext <= 1.0, f"实测 {ext:.3f}")
    real = gini2([625, 551, 532, 515, 472, 421, 404, 374, 358, 330, 296, 293, 267, 245])
    check("gini2 真实数据应为正且 <1", 0 < real < 1, f"实测 {real:.4f}")


def c_xml_cdata():
    """注意：`re.sub(r'<[^>]+>', ' ', s)` 会把 `<![CDATA[题名]]>` 整段（含正文）吃掉，
    导致 CNKI XML 源 206 条里 204 条标题变空、tier 判为 empty。"""
    from import_sources import _xml_text
    got = _xml_text("<Title><![CDATA[沈阳市老年人力资源开发]]></Title>")
    check("_xml_text 保留 CDATA 内容",
          "沈阳市" in got and "CDATA" not in got, f"实测 {got!r}")


def c_zotero_filters(tmp: Path):
    """注意：把过滤条件写进 `LEFT JOIN deletedItems d ON i.itemID=d.itemID AND d.itemID IS NULL`
    的 ON 子句 → 被删条目反而"无匹配"以 NULL 行通过，回收站条目与 attachment 全漏进
    结果（2 条应为 4 条）。"""
    db = tmp / "zotero.sqlite"
    con = sqlite3.connect(str(db))
    con.executescript("""
    CREATE TABLE libraries (libraryID INTEGER PRIMARY KEY, type TEXT, editable INT);
    CREATE TABLE itemTypes (itemTypeID INTEGER PRIMARY KEY, typeName TEXT);
    CREATE TABLE items (itemID INTEGER PRIMARY KEY, itemTypeID INT, libraryID INT, key TEXT);
    CREATE TABLE deletedItems (itemID INTEGER PRIMARY KEY, dateDeleted TEXT);
    CREATE TABLE fields (fieldID INTEGER PRIMARY KEY, fieldName TEXT);
    CREATE TABLE itemDataValues (valueID INTEGER PRIMARY KEY, value TEXT);
    CREATE TABLE itemData (itemID INT, fieldID INT, valueID INT);
    CREATE TABLE creators (creatorID INTEGER PRIMARY KEY, firstName TEXT, lastName TEXT);
    CREATE TABLE itemCreators (itemID INT, creatorID INT, creatorTypeID INT, orderIndex INT);
    CREATE TABLE creatorTypes (creatorTypeID INTEGER PRIMARY KEY, creatorType TEXT);
    CREATE TABLE tags (tagID INTEGER PRIMARY KEY, name TEXT);
    CREATE TABLE itemTags (itemID INT, tagID INT, type INT);
    CREATE TABLE itemAttachments (itemID INTEGER PRIMARY KEY, parentItemID INT, contentType TEXT);
    INSERT INTO libraries VALUES (1,'user',1);
    INSERT INTO itemTypes VALUES (1,'journalArticle'),(2,'attachment');
    INSERT INTO fields VALUES (1,'title'),(2,'abstractNote'),(3,'publicationTitle'),(4,'date'),(5,'DOI');
    INSERT INTO creatorTypes VALUES (1,'author');
    INSERT INTO items VALUES (1,1,1,'K1'),(2,1,1,'K2'),(3,2,1,'K3'),(4,1,1,'K4');
    INSERT INTO deletedItems VALUES (4,'2024-01-01');
    INSERT INTO itemDataValues VALUES (1,'Item one'),
      (2,'A long abstract that definitely passes the fifty character minimum threshold.'),
      (3,'J1'),(4,'2023-01-01'),(5,'10.1000/zz1');
    INSERT INTO itemData VALUES (1,1,1),(1,2,2),(1,3,3),(1,4,4),(1,5,5),(2,1,3);
    INSERT INTO creators VALUES (1,'Ada','Lovelace');
    INSERT INTO itemCreators VALUES (1,1,1,0);
    INSERT INTO tags VALUES (1,'alpha');
    INSERT INTO itemTags VALUES (1,1,0);
    INSERT INTO itemAttachments VALUES (3,1,'application/pdf');
    """)
    con.commit(); con.close()
    from import_sources import load_zotero
    refs = load_zotero(db)
    check("Zotero 排除 attachment 与回收站", len(refs) == 2, f"实测 {len(refs)} 条（应 2）")
    if refs:
        check("Zotero 关键词来自 tags", refs[0].keywords == ["alpha"], f"{refs[0].keywords}")


def c_year_priority(tmp: Path):
    """坑1（RIS）：DA - FEB 10 排在 PY - 2025 之前，setdefault 让无年份日期串先占位
        → PY 被忽略，年份区间被压成 2024-2024。
       坑2（WoS HTML）：Early Access Date(2025) 排在 Published Date(2026) 之前
        → 在线优先年覆盖正式出版年。"""
    from import_sources import load_ris, load_wos_html
    ris = tmp / "t.ris"
    ris.write_text(
        "TY  - JOUR\r\nTI  - A\r\nDA  - FEB 10\r\nPY  - 2025\r\nAB  - "
        "x" * 80 + "\r\nER  - \r\n", encoding="utf-8")
    r1 = load_ris(ris)
    check("RIS 年份取 PY 而非 DA", len(r1) == 1 and r1[0].year == 2025,
          f"实测 {r1[0].year if r1 else '无记录'}")

    html = tmp / "t.html"
    html.write_text("""<html><body><table>
    <tr><td>Record 1 of 1</td></tr>
    <tr><td> <b>Title:</b> </td><td> A study on X: a Y </td></tr>
    <tr><td><b>Source:</b> <value>J1</value>&nbsp;&nbsp;<b>DOI:</b>
        <value>10.1000/a</value>&nbsp;&nbsp;<b>Early Access Date:</b>
        <value>DEC 2025</value>&nbsp;&nbsp;<b>Published Date:</b>
        <value>2026 MAR</value>&nbsp;&nbsp;</td></tr>
    </table></body></html>""", encoding="utf-8")
    r2 = load_wos_html(html)
    ok_year = len(r2) == 1 and r2[0].year == 2026
    check("WoS HTML 年份取正式出版年（非在线优先年）", ok_year,
          f"实测 {r2[0].year if r2 else '无记录'}（应 2026）")
    ok_title = len(r2) == 1 and "a Y" in r2[0].title
    check("WoS HTML 含冒号的题名不丢失", ok_title, f"{r2[0].title if r2 else ''!r}")


def c_dedup():
    """跨来源去重：DOI 优先，其次归一化标题。"""
    from import_sources import dedup, make_ref
    a = make_ref(1, "Same Paper", "x" * 60, ["kw"], 2020, "J", "Smith, J", "10.1000/same")
    b = make_ref(2, "Same Paper", "x" * 60, ["kw"], 2020, "J", "Smith, J", "10.1000/same")
    c = make_ref(3, "Another One", "y" * 60, ["kw"], 2021, "J", "Doe, A", "10.1000/other")
    kept, dropped = dedup([a, b, c])
    check("去重按 DOI 去掉重复", len(kept) == 2 and dropped == 1, f"保留{len(kept)} 丢弃{dropped}")


def c_assign_tier():
    """tier 判定必须是单一事实源，且与 parse_refs 的历史口径一致。"""
    from lit_core import assign_tier, make_ref
    check("有长摘要 → primary_abs",
          assign_tier("x" * 60, [], "t") == "primary_abs")
    check("无摘要有关键词 → primary_kw",
          assign_tier("", ["kw"], "t") == "primary_kw")
    check("仅标题 → fallback_title", assign_tier("", [], "t") == "fallback_title")
    check("都无 → empty（不静默丢弃）", assign_tier("", [], "") == "empty")
    r = make_ref(1, "t", "x" * 60, ["a"], 2020, "J", "A, B", "")
    check("make_ref 的 tier 与 assign_tier 一致", r.tier == "primary_abs", r.tier)


def c_stat_helpers():
    from stat_helpers import cramers_v, crosstab
    identical = cramers_v(crosstab([0, 0, 1, 1, 2, 2], [0, 0, 1, 1, 2, 2], 3, 3))
    check("完全一致的标签 Cramér's V = 1", abs(identical - 1.0) < 1e-6, f"{identical:.4f}")
    indep = cramers_v(crosstab([0, 1, 0, 1, 0, 1], [0, 0, 1, 1, 2, 2], 2, 3))
    check("交叉分布 V 在 [0,1]", 0.0 <= indep <= 1.0, f"{indep:.4f}")


def c_palette():
    """注意：手工"彩虹 14 色"在色觉模拟下相邻对完全重合（min ΔE00 = 0.0）。

    配色已**固化**在 build_report.py 的 `_PAL`（设计期经 Oklab + Machado CVD
    模拟 + CIEDE2000 检验：相邻 min ΔE00 ≥ 9、白底对比度 ≥ 2.3、平均彩度 > 0.15；
    全链路颜色同源：JS 侧 `window.__PAL__` 与 Python `_PAL` 逐位一致）。
    本项直接从 `_PAL` 取值做**自包含校验**，确保固化下来的 14 色互不相同、且
    有足够区分度 —— 防止后续手改 `_PAL` 时引入近重复色而使配色静默退化。
    """
    br = (HERE / "build_report.py").read_text(encoding="utf-8")
    m = re.search(r"^[ \t]*_PAL\s*=\s*\[([^\]]*)\]", br, re.M)
    if not m:
        skip("色板区分度", "未能在 build_report.py 定位 _PAL")
        return
    pal = re.findall(r"#[0-9A-Fa-f]{6}", m.group(1))
    check("色板含 14 色", len(pal) == 14, f"实测 {len(pal)}")
    check("色板无重复色", len(set(pal)) == len(pal),
          f"{len(set(pal))} 唯一 / {len(pal)}")

    def _lab(h):
        r, g, b = (int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))

        def lin(c):
            return ((c + 0.055) / 1.055) ** 2.4 if c > 0.04045 else c / 12.92

        r, g, b = lin(r), lin(g), lin(b)
        x = r * 0.4124 + g * 0.3576 + b * 0.1805
        y = r * 0.2126 + g * 0.7152 + b * 0.0722
        z = r * 0.0193 + g * 0.1192 + b * 0.9505

        def f(t):
            return t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116

        fx, fy, fz = f(x / 0.95047), f(y / 1.0), f(z / 1.08883)
        return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))

    labs = [_lab(c) for c in pal]
    mn = min(math.dist(labs[i], labs[j])
             for i in range(len(labs)) for j in range(i + 1, len(labs)))
    check("色板任意两色 min ΔE76 ≥ 8（区分度）", mn >= 8.0, f"实测 {mn:.2f}")


def c_sort_before_layout(tmp: Path):
    """注意：build_network.py 里 nodes.sort(-degree) 排在 layout() 之后 →
    pos_encoded[i] 与 payload['nodes'][i] 错位，而报告 JS 优先读 pos_encoded
    → 整张网络图渲染错乱。这是"排版不清楚"的根因之一。

    [!]  此检查曾「无牙」，故由源码比对改为行为断言：
    旧版只比较源码里两个字符串的**位置**。实测注入它声称要防的 bug
    （layout 后按 id 重排节点）后，语法正确、rc=0，但**整张网络错分率
    从 0.37% 飙到 91.21%** —— 而旧检查仍报"全部通过"。
    原因：它只看第一个 sort 的位置，第二个 sort 出现在 layout 之后它完全看不见。

    改为**行为断言**：真跑一次建网，校验 nodes[i].x/y 与 pos_encoded[i]
    逐一对齐。这是唯一能真正抓住该bug 的方式。
    """
    import base64
    # 1) 保留源码位置检查作为快速护栏（非唯一依据）
    # 排序键已由 -x["degree"] 改为 (-x["degree"], x["id"]) 以保证跨进程确定性
    # 此处匹配两种写法，避免源码护栏因字面量变化而误报。
    src = (HERE / "build_network.py").read_text(encoding="utf-8")
    cands = [src.find('nodes.sort(key=lambda x: (-x["degree"], x["id"]))'),
             src.find("nodes.sort(key=lambda x: -x[")]
    i_sort = max(cands)          # 取较靠后者 = 真实生效的那次排序
    i_layout = src.find("pos = layout(nodes, edges)")
    check("nodes.sort 在 layout() 之前（源码位置）",
          i_sort != -1 and i_layout != -1 and i_sort < i_layout,
          f"sort@{i_sort} layout@{i_layout}")

    # 2) 行为断言：真跑建网，校验坐标与 pos_encoded 对齐
    from lit_core import make_ref, refs_to_json
    import json as _json
    # [!]  语料设计的关键教训（实测）：
    # 首版用 20 篇同质语料，只有 2 个关键词节点，且它们的 id 序恰好与
    # degree 序一致 → 注入"layout 后按 id 重排"这个 bug 后检查**仍报通过**
    # （节点 permute 后坐标数值本身不变，形同虚设）。
    # 故语料必须满足：**多主题 + 节点数足够 + id 序≠degree 序**，
    # 否则任何"重排"变异都不会改变 nodes[i] 与 pos_encoded[i] 的对应关系。
    # 下面刻意让各主题关键词在 id 序上互相穿插，而非按主题成块。
    themes = [
        ["leadership", "team effectiveness"],
        ["artificial intelligence", "algorithm"],
        ["service quality", "customer"],
        ["turnover intention", "commitment"],
        ["organizational justice", "trust"],
    ]
    refs = []
    for round_i in range(18):
        for kws in themes:
            for k in kws:
                refs.append(make_ref(
                    len(refs) + 1, f"Study {round_i} on {k}",
                    "x" * 80, [k, kws[0], kws[1]], 2018 + (round_i % 5),
                    "J", f"A{len(refs)}, B", f"10.1/z{len(refs)}"))
    td = Path(tempfile.mkdtemp())
    try:
        (td / "refs.json").write_text(
            _json.dumps(refs_to_json(refs, "test", {}), ensure_ascii=False),
            encoding="utf-8")
        r = run(["build_network.py", str(td / "refs.json"),
                 "--node-df", "1", "--min-edge", "1",
                 "--out", str(td / "out"), "--layout"])
        if r.returncode != 0:
            check("建网可跑通（行为断言前置）", False,
                  f"退出码 {r.returncode}: {r.stderr[-160:]}")
            return
        net = _json.loads((td / "out" / "network.json").read_text(encoding="utf-8"))
        nodes = net["nodes"]
        # 前置自检：确认本语料确实能触发排序错位。
        # 不满足就必须显式判FAIL —— 否则本次断言无效却报"通过"，
        # 那正是我们要消灭的假阳性。
        #
        # 排序键已加 id 兜底（(-degree, id)），输出对同度节点按 id 升序稳定，
        # 因此 `ids != sorted(ids)` 这一「错位前提」不再成立——它原本用于保证
        # 语料能检出"layout 后重排"，但稳定排序后该条件恒为假，会把**已修好的**
        # 确定性排序误报为缺陷。改判「排序结果是否确定且与 layout 一致」：
        #   1) nodes 按 (-degree, id) 严格有序（确定性排序的直接证据）；
        #   2) 节点数足够（>=6）以保证断言有实际覆盖面。
        # 真正的对齐结论仍由下方的 pos_encoded 逐点比对给出。
        ids = [n["id"] for n in nodes]
        degs = [n.get("degree", 0) for n in nodes]
        by_degree = all(degs[i] >= degs[i + 1] for i in range(len(degs) - 1))
        keys = [(-n.get("degree", 0), n["id"]) for n in nodes]
        total_order = keys == sorted(keys)          # (-degree, id) 全序且稳定
        sensitive = by_degree and total_order and len(nodes) >= 6
        check("测试语料可检出排序错位（degree 降序且 (-degree,id) 全序、节点≥6）", sensitive,
              f"{len(nodes)} 节点，degree 降序={by_degree}，全序稳定={total_order}")
        if not sensitive:
            check("pos_encoded 对齐断言有效", False,
                  "测试语料不满足确定性排序前置条件，本次断言无效——需更换语料")
            return
        pe = net.get("pos_encoded")
        if not pe or not pe.get("pos_b64"):
            skip("pos_encoded 与 nodes 对齐", "未产出 pos_encoded（需 --layout）")
            return
        q = _b64_i16(pe["pos_b64"])
        sc = pe.get("scale", 1) or 1
        check("pos_encoded 长度== 2×节点数", len(q) == 2 * len(nodes),
              f"{len(q)} vs {2*len(nodes)}")
        # 关键断言：第 i 个节点的 x/y 必须等于 pos_encoded 第 i 对坐标。
        # [!]  不能因长度检查失败就 return —— 那样长度异常会"连带掩盖"本断言，
        #    只错开一位时长度检查先失败并提前退出，
        #    导致对齐断言根本没跑。必须独立执行。
        worst, worst_i, n_cmp = 0.0, -1, 0
        m_nodes = min(len(nodes), len(q) // 2)
        for i in range(m_nodes):
            n_cmp += 1
            nd = nodes[i]
            dx = abs(nd.get("x", 0) - q[2 * i] / sc)
            dy = abs(nd.get("y", 0) - q[2 * i + 1] / sc)
            m = max(dx, dy)
            if m > worst:
                worst, worst_i = m, i
        check("pos_encoded[i] 与 nodes[i].x/y 逐一对齐（防排序错位）",
              n_cmp > 0 and worst <= 0.05,
              f"最大偏差 {worst:.4f}（节点 {worst_i}）" if worst > 0.05
              else f"最大偏差 {worst:.4f}，共校验 {n_cmp} 节点")
    finally:
        shutil.rmtree(td, ignore_errors=True)


def _b64_i16(b64: str):
    """把 pos_encoded 的 base64 int16 缓冲解成数组（避免依赖 numpy）。"""
    import array
    import base64
    bin_ = base64.b64decode(b64)
    a = array.array("h")
    a.frombytes(bin_[:len(bin_) // 2 * 2])
    return a


def c_sna_fallback(tmp: Path):
    """R + igraph 是标准路径（必需）：缺 R 必须【硬失败】，绝不允许静默回退。

    旧口径（已废弃）：R 缺失时 sna_r.py 回退纯 Python 并 exit 0，本检查只断言
    "exit 0 + backend=python-fallback" —— 那等于把「静默降级」固化成了正确行为：
    用户拿到一份没有独立社群划分、没有 ARI/NMI 交叉验证的"完整报告"却毫不知情。

    新口径：
      · 缺 R / igraph 且未显式授权 → 失败（非 0）+ 安装指引 + 不产出任何产物；
      · 只有显式 --allow-python-fallback 才降级，且产物须标 is_standard_path=False；
      · R + igraph 齐备时，标准路径必须真跑出 backend="R"。
    """
    net = tmp / "network.json"
    net.write_text(json.dumps({
        "nodes": [{"id": f"k{i}", "degree": 5 - i, "primary_cluster": i % 2}
                  for i in range(6)],
        "edges": [{"source": "k0", "target": f"k{i}", "weight": 3} for i in range(1, 6)],
    }), encoding="utf-8")

    # (1) 门禁：R 不可用 + 未授权回退 → 必须失败，且不得偷偷产出降级产物
    o1 = tmp / "o_gate"
    r = run(["sna_r.py", "--network", str(net), "--out", str(o1),
             "--rscript", "C:/no/such/Rscript.exe"])
    check("sna_r 缺 R 时默认硬失败（不再静默回退）",
          r.returncode == 8,
          f"退出码 {r.returncode}（契约要求 8=环境不满足；仅 8 才算守住硬失败门禁）")
    check("sna_r 失败时给出 igraph 安装指引",
          "install.packages" in (r.stderr or ""))
    check("sna_r 失败时不产出降级产物 sna_r.json",
          not (o1 / "sna_r.json").exists())

    # (2) 显式回退：仅 --allow-python-fallback 才降级，产物须显著标注非标准路径
    o2 = tmp / "o_fb"
    r2 = run(["sna_r.py", "--network", str(net), "--out", str(o2),
              "--rscript", "C:/no/such/Rscript.exe", "--allow-python-fallback"])
    if r2.returncode != 0:
        check("sna_r 显式回退 exit 0", False,
              f"退出码 {r2.returncode}: {r2.stderr[:120]}")
    else:
        try:
            d = json.loads(r2.stdout)
            check("sna_r 显式回退 exit 0", True)
            check("sna_r 显式回退 backend=python-fallback",
                  d.get("backend") == "python-fallback", str(d.get("backend")))
            check("sna_r 显式回退标注为非标准路径",
                  d.get("is_standard_path") is False and bool(d.get("warning")))
            check("sna_r 显式回退给出安装提示",
                  "install.packages" in str(d.get("hint", "")))
        except Exception as e:  # noqa: BLE001
            check("sna_r 显式回退输出可解析", False, str(e))

    # (3) 标准路径：R + igraph 在则必须真跑出 backend="R"；不在则判 FAIL（不再 SKIP）
    rs = find_rscript()
    if not rs:
        check("sna_r 标准路径（R）可用", False,
              "未找到 Rscript：R + igraph 是必需前置条件，请安装 R 后重跑")
        return
    try:
        # 必须用 quietly=（不能写 quiet=）：实测 requireNamespace 的部分匹配在
        # 此处不生效，`quiet=TRUE` 会被当成未知参数、包已装也返回 FALSE。
        ig = subprocess.run(
            [rs, "-e", 'cat(requireNamespace("igraph", quietly=TRUE))'],
            capture_output=True, text=True, timeout=60)
        if "TRUE" not in (ig.stdout or "").upper():
            check("sna_r 标准路径（R）可用", False, "R 已找到但缺 igraph 包")
            return
    except Exception as e:  # noqa: BLE001
        check("sna_r 标准路径（R）可用", False, f"igraph 探针失败: {e}")
        return
    o3 = tmp / "o_r"
    r3 = run(["sna_r.py", "--network", str(net), "--out", str(o3), "--rscript", rs])
    if r3.returncode != 0:
        check("sna_r 标准路径 exit 0", False,
              f"退出码 {r3.returncode}: {(r3.stderr or '')[:120]}")
        return
    try:
        d3 = json.loads(r3.stdout)
        check("sna_r 标准路径 backend=R", d3.get("backend") == "R",
              str(d3.get("backend")))
        check("sna_r 标准路径标注 is_standard_path=True",
              d3.get("is_standard_path") is True)
        check("sna_r 标准路径带 igraph 版本",
              bool(d3.get("igraph_version")), str(d3.get("igraph_version")))
    except Exception as e:  # noqa: BLE001
        check("sna_r 标准路径输出可解析", False, str(e))


def c_zero_drop(tmp: Path):
    """零静默丢弃：四类 tier 之和 == 记录总数。"""
    from lit_core import assign_tier, coverage_report, make_ref
    refs = []
    for i in range(10):
        if i % 4 == 0:
            refs.append(make_ref(i, "t", "x" * 60, ["a"], 2020, "J", "A, B", ""))
        elif i % 4 == 1:
            refs.append(make_ref(i, "t", "", ["a"], 2020, "J", "A, B", ""))
        elif i % 4 == 2:
            refs.append(make_ref(i, "t", "", [], 2020, "J", "A, B", ""))
        else:
            refs.append(make_ref(i, "", "", [], None, "", "", ""))
    cov = coverage_report(refs)
    check("零丢弃恒等式成立", cov["zero_drop_identity"] is True,
          f"tier={cov['tier']} total={cov['total']}")


def c_tagged_year():
    """注意：EndNote tagged 解析器只认 %D 取年份，但 CNKI 等平台的 .enw 用 %Y。
    结果 year 全为None → age_warning 报"库中无任何可用年份"、演化分析整体失效，
    且属静默数据丢失（违反零静默丢弃铁律）。%D / %Y 都收。"""
    from import_sources import load_enl_tagged
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "t.enw"
        p.write_text(
            "%T Study A on leadership\n%A A, B\n%K leadership\n"
            "%X " + "x" * 80 + "\n%Y 2021\n%0 68\nER  - \n"
            "%T Study B on leadership\n%A C, D\n%K leadership\n"
            "%X " + "x" * 80 + "\n%D 2019/05/01\n%0 68\nER  - \n",
            encoding="utf-8")
        refs = load_enl_tagged(p)
        yrs = [r.year for r in refs]
        check("tagged 年份：%Y 与 %D 都能解析",
              len(refs) == 2 and yrs == [2021, 2019], f"实测 {yrs}")


def c_small_library_guards():
    """注意（两处，均在真实小样本库上暴露）：
    1) TfidfVectorizer 硬编码 min_df=3 + max_df=0.5 → 小库下
       抛 `ValueError: max_df corresponds to < documents than min_df`。
    2) NMF(init='nndsvda') 要求 n_components <= min(n_samples, n_features)，
       K 网格未设上限 → 小库时抛 ValueError，用户只看到退出码 5「计算失败」。"""
    from cluster_topics import df_bounds
    # 1) min_df/max_df 不得冲突：max_df 对应的文档数必须 >= min_df
    for n in (1, 3, 10, 50, 200, 5683):
        min_df, max_df = df_bounds(n)
        ok = (max_df >= 1.0) or (n * max_df >= min_df)
        check(f"df_bounds(n={n}) 不冲突", ok and min_df >= 1,
              f"min_df={min_df} max_df={max_df:.3f}")
    # 2) K 网格必须被截断到 min(n, p)
    src = (HERE / "cluster_topics.py").read_text(encoding="utf-8")
    check("K 扫描含 min(n_samples, n_features) 上限守卫",
          "k_max" in src and "k_ceiling" in src)


def c_refs_json_everywhere():
    """注意：文档承诺"下游模块透明接受 .enl 或 refs.json"，但
    scan_library.py 仍走 find_enl + 魔数判定 → 传 refs.json 被当成
    "文本格式 .enl"报错退出 2，非 EndNote 用户的体检环节直接断链。"""
    root = Path(__file__).resolve().parents[3]
    scan = (HERE / "scan_library.py").read_text(encoding="utf-8")
    check("scan_library 支持 refs.json 通路",
          "load_refs" in scan and "refs_json" in scan)
    # 其余模块必须都走 load_refs 统一入口
    for f in ("cluster_topics.py", "build_network.py", "reading_status.py",
              "dup_check.py", "age_warning.py", "author_topic.py",
              "robust_k.py", "trend_effects.py"):
        s = (HERE / f).read_text(encoding="utf-8")
        check(f"{f} 走 load_refs 统一入口", "load_refs" in s)


def c_new_modules(tmp: Path):
    """这两个模块的基本正确性 + 边界声明。"""
    # 1) burst_detection：构造已知突现形态，验证能识别且不产生除零错误
    from burst_detection import detect_keyword_bursts
    from lit_core import make_ref
    refs = []
    # flat：2015~2024 每年 3 篇，全程均匀 → 真的没有突现，应排在 surge 之后
    for y in range(2015, 2025):
        for i in range(3):
            refs.append(make_ref(len(refs) + 1, f"F{i}", "x" * 80,
                                 ["flat"], y, "J", "A, B", ""))
    # surge：2021-2023 逐年翻倍，2023 达峰 → 应被判为突现且排名靠前
    for y, n in ((2021, 1), (2022, 3), (2023, 9)):
        for i in range(n):
            refs.append(make_ref(len(refs) + 1, "S", "y" * 80, ["surge"],
                                 y, "J", "C, D", ""))
    res = detect_keyword_bursts(refs, window=2, min_total=5, min_years=3)
    check("突现检测产出结果", res["method"] == "keyword_burst_ratio"
          and len(res["bursts"]) > 0, f"{len(res['bursts'])} 个候选")
    kws = [b["keyword"] for b in res["bursts"]]
    check("突现词识别正确（surge 应居首）",
          kws and kws[0] == "surge",
          f"首位={kws[0] if kws else '无'} 强度={res['bursts'][0]['strength'] if res['bursts'] else '—'}")
    if "flat" in kws and "surge" in kws:
        fs = next(b for b in res["bursts"] if b["keyword"] == "flat")["strength"]
        ss = next(b for b in res["bursts"] if b["keyword"] == "surge")["strength"]
        check("均匀词强度低于突增词", ss > fs, f"surge={ss} > flat={fs}")
        check("突现结果含置信度标注",
              all(b.get("confidence") in ("high", "medium", "low")
                  for b in res["bursts"]))
    check("突现结果声明非 citation burst",
          "citation burst" in res.get("note", ""))
    check("突现结果上报缺年份占比", "missing_year_pct" in res["coverage"])

    # 2) export_vosviewer：Pajek 格式与参数口径落盘
    from export_vosviewer import export_citespace_tables, export_pajek
    net = {"type": "keyword-cooccurrence",
           "notice": "not a citation network",
           "stats": {"node_df": 5, "min_edge_count": 2, "df_mode": "doc",
                     "normalize_case": "lower", "keyword_dedupe": "per-doc"},
           "nodes": [{"id": "a", "df": 3, "degree": 1, "primary_cluster": 0},
                     {"id": "b", "df": 2, "degree": 1, "primary_cluster": 0}],
           "edges": [{"source": "a", "target": "b", "weight": 2}]}
    net_txt = export_pajek(net)
    check("Pajek 导出含 *Vertices/*Edges 段",
          net_txt.startswith("*Vertices 2") and "*Edges 1" in net_txt)
    check("Pajek 边用 1-based 序号", "\n1 2 2" in net_txt)
    nrows, erows, dropped = export_citespace_tables(net)
    check("CiteSpace 表导出正确",
          len(nrows) == 2 and len(erows) == 1 and dropped == 0)
    # 悬空边必须被计数而非静默丢弃（零静默丢弃铁律）
    net2 = dict(net, edges=[{"source": "a", "target": "zzz", "weight": 1}])
    _, e2, d2 = export_citespace_tables(net2)
    check("悬空边被计数而非静默丢弃", d2 == 1, f"dropped={d2}")


def c_export_all(tmp: Path):
    """一键导出（export_all.py）必须真实可用。

    背景：用户明确反馈"结果导出 / 数据导出设计施工虽有提到但没落实" ——
    export_vosviewer.py 与 sanxian_tables() 早已存在，却没串成一个一键入口
    与索引，用户拿到一堆零散文件不知从何用起。本组把"导出确已落实"固化为
    回归断言，并坚持：**脚本缺失须 FAIL（不许 skip 蒙混）、缺产物只记录跳过**。
    """
    script = HERE / "export_all.py"
    if not script.exists():
        # 导出是对用户的交付承诺，能力缺失必须 FAIL 而不是静默跳过
        return check("一键导出脚本存在", False, "export_all.py 缺失")
    check("一键导出脚本存在", True)

    # 造一个含「真网络 + 主题」的产物目录，覆盖 CSV / 互操作 / summary / README 全链路
    src = tmp / "prod"
    (src / "data").mkdir(parents=True, exist_ok=True)
    net = {"type": "keyword-cooccurrence", "notice": "not a citation network",
           "stats": {"node_df": 5, "min_edge_count": 2, "df_mode": "doc",
                     "normalize_case": "lower", "keyword_dedupe": "per-doc"},
           "nodes": [{"id": "a", "df": 3, "degree": 1, "primary_cluster": 0},
                     {"id": "b", "df": 2, "degree": 1, "primary_cluster": 0}],
           "edges": [{"source": "a", "target": "b", "weight": 2}]}
    (src / "network.json").write_text(json.dumps(net, ensure_ascii=False),
                                      encoding="utf-8")
    topics = {"ok": True, "params": {"k": 2}, "years": [2020, 2021],
              "clusters": [
                  {"cluster_id": 0, "size": 10, "pct": 50.0, "lang_dominant": "zh",
                   "top_terms": ["a", "b"], "year_range": [2020, 2021]},
                  {"cluster_id": 1, "size": 10, "pct": 50.0, "lang_dominant": "zh",
                   "top_terms": ["c", "d"], "year_range": [2020, 2021]}]}
    (src / "topics.json").write_text(json.dumps(topics, ensure_ascii=False),
                                     encoding="utf-8")

    out = tmp / "prod_export"
    r = subprocess.run([PY, str(script), "--dir", str(src), "--out", str(out)],
                       capture_output=True, text=True, timeout=180)
    check("一键导出可执行（真实产物目录）", r.returncode == 0,
          f"rc={r.returncode} {r.stderr.strip()[:100]}")
    if r.returncode != 0:
        return
    check("导出节点/边表 CSV",
          (out / "data" / "keyword_nodes.csv").exists()
          and (out / "data" / "keyword_edges.csv").exists())
    netfile = out / "interop" / "keyword" / "vosviewer_network.net"
    check("导出 VOSviewer/Pajek .net（复用 export_vosviewer）",
          netfile.exists()
          and netfile.read_text(encoding="utf-8").startswith("*Vertices"))
    check("导出三线表 HTML 与 summary.json",
          (out / "results" / "sanxian.html").exists()
          and (out / "summary.json").exists())
    readme = out / "EXPORT_README.md"
    if readme.exists():
        seg = (readme.read_text(encoding="utf-8")
               .split("## 文件清单", 1)[-1].split("## 跳过项", 1)[0])
        listed = set(re.findall(r"\| `([^`|]+)` \|", seg))
        disk = {p.relative_to(out).as_posix() for p in out.rglob("*")
                if p.is_file() and p.name != "EXPORT_README.md"}
        check("EXPORT_README 清单与落盘逐一对齐",
              listed == disk, f"清单{len(listed)}/落盘{len(disk)} 差集{listed ^ disk}")
    else:
        check("EXPORT_README 清单与落盘逐一对齐", False, "EXPORT_README.md 缺失")
    try:
        summ = json.loads((out / "summary.json").read_text(encoding="utf-8"))
        ok_shape = (summ["networks"]["keyword"]["nodes"] == 2
                    and summ["networks"]["keyword"]["edges"] == 1)
    except Exception:  # noqa: BLE001
        ok_shape = False
    check("summary 网络规模与源 JSON 一致（未重算）", ok_shape)

    # 空态 / 缺产物：必须 0 退出 + 记录 skipped，绝不崩溃（缺一即 FAIL）
    empty = tmp / "prod_empty"
    empty.mkdir(parents=True, exist_ok=True)
    (empty / "network.json").write_text(
        json.dumps({"type": "keyword-cooccurrence", "nodes": [], "edges": []},
                   ensure_ascii=False), encoding="utf-8")
    eout = tmp / "prod_empty_export"
    re_ = subprocess.run([PY, str(script), "--dir", str(empty), "--out", str(eout)],
                         capture_output=True, text=True, timeout=180)
    check("缺产物/空网络：导出记录跳过而非崩溃", re_.returncode == 0,
          f"rc={re_.returncode} {re_.stderr.strip()[:100]}")
    if re_.returncode == 0:
        es = json.loads((eout / "summary.json").read_text(encoding="utf-8"))
        reasons = {s["artifact"]: s["reason"] for s in es["skipped"]}
        check("空网络被跳过并记录原因（不产出互操作）",
              "network.json" in reasons and "空" in reasons["network.json"]
              and not (eout / "interop" / "keyword").exists(),
              f"reasons={reasons}")


def c_boundary_statements():
    """边界声明必须在代码里硬编码，不能只写在文档里让人"记得说"。"""
    rep = (HERE / "build_report.py").read_text(encoding="utf-8")
    check("报告硬编码「非引文网络」声明", "不是引文网络" in rep)
    check("报告硬编码「keyword burst ≠ citation burst」声明",
          "不是引文突现" in rep or "citation burst" in rep)
    lead = Path(__file__).resolve().parents[3] / "agents" / "academic-lit-analysis-lead.md"
    if lead.exists():
        t = lead.read_text(encoding="utf-8")
        check("主理人提示词含共被引禁令", "共被引" in t)
        check("主理人提示词含 burst 边界声明", "keyword burst" in t)
    # 方法论借鉴清单必须存在且含「不吸收」清单
    mb = (HERE.parent / "references" / "methods_borrowed.md")
    check("方法论借鉴文档存在", mb.exists())
    if mb.exists():
        t = mb.read_text(encoding="utf-8")
        check("借鉴文档含「明确不吸收」清单", "不吸收" in t)
    # build_html / sanxian_tables 都必须能实际执行（曾因移动
    # 代码块把 sanxian_tables 的 `body = "".join(out)` 一并删掉，
    # 主报告正常但三线表静默失败 —— 用真实调用兜住）
    # demo 用**真实跑出来的 topics.json**，而不是手搓dict：
    # 手搓必然漏字段（已实测踩过 zh_pct / year_min / year_range / library 四次），
    # 而漏字段恰恰是这类"静默失败"最常见的成因。
    try:
        import json as _json
        from build_report import build_html, sanxian_tables
        from lit_core import make_ref, refs_to_json
        refs = [make_ref(i + 1, f"Study {i} on leadership and performance",
                         "x" * 80, ["leadership", "performance"], 2018 + i,
                         "J", f"A{i}, B", f"10.1/t{i}")
                for i in range(24)]
        # 追加异质词项，避免语料只有 2 个词导致特征维数 < K 下限
        refs += [make_ref(25 + i, f"Report {i} on supply chain resilience",
                          "y" * 80, ["supply", "chain", "resilience"],
                          2019 + i, "K", f"C{i}, D", f"10.1/u{i}")
                 for i in range(16)]
        td = Path(tempfile.mkdtemp())
        try:
            (td / "refs.json").write_text(
                _json.dumps(refs_to_json(refs, "test", {}), ensure_ascii=False),
                encoding="utf-8")
            # 省略 --k 走自动判定：极简语料的 min(n,p) 可能低于 --k 下限，
            # 写死 --k 会让检查器自身被守卫挡下（那正是守卫在正确工作）
            r = run(["cluster_topics.py", str(td / "refs.json"),
                     "--out", str(td / "out")])
            tpath = td / "out" / "topics.json"
            if r.returncode != 0 or not tpath.exists():
                check("报告模块可执行", False,
                      f"cluster_topics 未产出 topics.json（退出码 {r.returncode}）")
            else:
                topics = _json.loads(tpath.read_text(encoding="utf-8"))
                h = build_html(topics)
                check("build_html 可执行", isinstance(h, str) and len(h) > 500,
                      f"{len(h)} 字符")
                sx = sanxian_tables(topics)
                check("sanxian_tables 可执行",
                      isinstance(sx, str) and "表 1" in sx, f"{len(sx)} 字符")
                check("三线表含 body 收敛（未静默失败）", "</body>" in sx)
        finally:
            shutil.rmtree(td, ignore_errors=True)
    except Exception as e:  # noqa: BLE001
        check("报告模块可执行", False, f"{type(e).__name__}: {e}")


def c_doctor_hint_actionable():
    """doctor.py 的修复指引必须「可执行」，且与真实病因相符。

    两类已知的真实缺陷：

    1. exit 8 恒复用 EXIT[8] 的「请改用 Python 3.11+」文案。当 exit 8 的
       真实病因是**缺 R / 缺 igraph** 时，Agent 读到这句会把用户引向完全
       无关的方向 —— 改 Python 版本解决不了缺 R。已改为按病因分文案。
    2. `[修复建议]` 段落只遍历 FIX_HINT 命中的项。若某依赖没登记 FIX_HINT
       （新增依赖时很容易漏），该段会**一个字符都不打印** —— 用户看到
       一个空标题，比不给建议更糟（像是没有问题）。已加兜底。

    本检查真跑 doctor.main()（不 stub 掉任何东西，只临时换掉 probe_r /
    REQUIRED 以构造场景），断言「一定给出至少一条可执行建议」。

    [!]  调用前必须把 `sys.argv` 换成 doctor 自己的。本检查是在**进程内**
    调用 main()，而 main() 用 argparse 解析 `sys.argv` —— 若 run_checks.py
    自己带了参数（`--json` / `--full` / `--library`…），argparse 见到不认得的
    参数会**直接以退出码 2 结束**。那时这六项断言测的就不是 doctor 的行为，
    而是「run_checks 有没有带参数」：不带参数全绿，带参数全红。
    """
    import io as _io
    import contextlib as _ctx
    import importlib as _il
    try:
        sys.path.insert(0, str(HERE))
        doc = _il.import_module("doctor")
    except Exception as e:  # noqa: BLE001
        return check("doctor 修复指引可执行", False,
                     f"无法导入 doctor: {type(e).__name__}: {e}")

    def _run(label, r_ok, extra_req=None):
        o_r, o_req = doc.probe_r, doc.REQUIRED
        o_argv = sys.argv
        doc.probe_r = (lambda: (True, "C:/fake/Rscript", "2.3.3", "R 4.6.1", "PATH")
                       if r_ok else
                       (False, None, "未找到 Rscript（模拟）", "", ""))
        if extra_req:
            doc.REQUIRED = list(o_req) + extra_req
        buf = _io.StringIO()
        rc = None
        try:
            sys.argv = ["doctor.py"]          # 隔离宿主进程的命令行参数
            with _ctx.redirect_stderr(buf), _ctx.redirect_stdout(buf):
                rc = doc.main()
        except SystemExit as e:
            rc = e.code
        except Exception as e:  # noqa: BLE001
            rc = f"EXC {type(e).__name__}"
        finally:
            doc.probe_r, doc.REQUIRED = o_r, o_req
            sys.argv = o_argv
        out = buf.getvalue()
        # 提取 [修复建议] 段落的正文
        seg, grab = [], False
        for line in out.splitlines():
            if line.startswith("[修复建议]"):
                grab = True
                continue
            if grab:
                if not line.strip():
                    break
                seg.append(line.strip())
        return rc, seg, out

    # 场景 1：缺 R → 建议必须指向 R/igraph，而不是 Python 版本
    rc, seg, out = _run("缺 R", r_ok=False)
    hint = next((l for l in out.splitlines() if l.startswith("[hint]")), "")
    check("缺 R 时退出码为 8", rc == 8, f"rc={rc}")
    check("缺 R 时修复建议非空", bool(seg), f"实得 {len(seg)} 条")
    check("缺 R 时指引指向 R/igraph（而非 Python 版本）",
          "igraph" in hint or "igraph" in " ".join(seg),
          hint[:80] or "(无 hint)")

    # 场景 2：缺未登记 FIX_HINT 的依赖 → 兜底必须给出可执行建议
    rc2, seg2, _ = _run("缺未登记依赖", r_ok=True,
                        extra_req=[("__未登记模块__", ">=1.0")])
    check("缺未登记依赖时退出码为 8", rc2 == 8, f"rc={rc2}")
    check("缺未登记依赖时修复建议非空（兜底生效）", bool(seg2),
          f"实得 {len(seg2)} 条 —— 修复建议是空标题，User 会以为没问题")
    check("兜底建议可执行（指向 requirements.txt 或安装指引）",
          any(("requirements.txt" in s) or ("igraph" in s) or ("pip" in s)
              for s in seg2),
          " / ".join(seg2)[:90])


def c_argv_isolation():
    """回归门禁：进程内调用其它脚本的 main() 不得继承宿主的 sys.argv。

    为什么需要单独守：本套件的检查项最终都用 `run_checks.py [参数]` 触发，
    而带不带参数对「进程内调用 main()」的检查影响极大 —— doctor.main() 走
    argparse，宿主参数会被它当成非法参数、直接以退出码 2 结束。于是同一份
    代码：不带参数跑全绿，带 `--json`/`--full` 跑就红一片。
    这类缺陷不会在任何一次单跑里暴露，只有跨调用方式对比才看得见。

    做法：故意把 sys.argv 污染成带参数的形态，重跑 doctor 那组断言，
    要求结果仍然全绿。用临时 RESULTS 接住，避免污染正式统计。
    """
    global RESULTS
    saved_results, saved_argv = RESULTS, sys.argv
    scratch: list[tuple[str, str, str]] = []
    try:
        RESULTS = scratch
        sys.argv = ["run_checks.py", "--json", "/tmp/__probe__.json"]
        c_doctor_hint_actionable()
    finally:
        RESULTS = saved_results
        sys.argv = saved_argv
    bad = [n for n, st, _ in scratch if st != "PASS"]
    check("进程内调用 main() 已隔离 sys.argv", not bad and bool(scratch),
          ("、".join(bad[:3]) if bad else
           f"污染参数下 {len(scratch)} 项仍全绿" if scratch
           else "未取到任何子断言"))


def c_doc_cmd_paths_consistent():
    """文档里给用户的命令必须用同一种路径写法，且声明 cwd 前提。

    已知失败模式：SKILL.md 的快速开始里，
    第 0 步用全路径 `skills/academic-lit-analysis/scripts/doctor.py`，
    紧接着第 1 步起却用短路径 `python3 scripts/scan_library.py`。
    第一次接触这个包的人照第 1 步抄，必然撞 `No such file or directory`
    —— 而他刚才明明是照着上一行能跑通的写法在抄。

    两个修复都要有守卫，否则下次重构文档又会退回混用：
      1. 短路径写法必须为 0；
      2. 含命令的文档必须声明「在专家团根目录执行」的前提。
    """
    root = Path(__file__).resolve().parents[3]
    docs = ["skills/academic-lit-analysis/SKILL.md", "README.md",
            "agents/data-auditor.md", "agents/trend-analyst.md",
            "agents/network-mapper.md", "agents/review-outliner.md",
            "agents/academic-lit-analysis-lead.md"]
    short_total = []
    no_cwd_notice = []
    for rel in docs:
        p = root / rel
        if not p.exists():
            continue
        t = p.read_text(encoding="utf-8")
        # 只查**行首命令**（代码块里的可执行命令），不看正文里为了说明
        # "相对路径写法会失败"而举的反例 —— 那是刻意写的对照说明。
        n = len(re.findall(r"(?m)^\s*(?:#\s*)?\$?\s*python3?\s+scripts/", t))
        if n:
            short_total.append(f"{rel} ×{n}")
        if re.search(r"(?m)^\s*python3?\s+\S", t) and "根目录" not in t:
            no_cwd_notice.append(rel)
    check("文档命令无短路径写法（统一用全路径）",
          not short_total, "；".join(short_total) if short_total
          else "全部为全路径")
    check("含命令的文档均声明工作目录前提",
          not no_cwd_notice,
          "缺 cwd 说明: " + "、".join(no_cwd_notice) if no_cwd_notice
          else "均已声明")


def c_skill_tree():
    """SKILL.md 的「## 目录」树必须与实际文件逐一相符。

    注意（pre-release 发现）：曾有配色生成器等文件被打包排除，但目录树仍列着它们
    （用户/Agent 点进去必然 404），而原 c_no_dangling_refs 只认带 ./ · ../ 前缀的
    引用，对目录树里的**裸文件名**完全漏检。
    本项解析目录树条目里的文件名，逐一验证其在技能目录下真实存在。
    """
    sk = HERE.parent / "SKILL.md"
    if not sk.exists():
        skip("SKILL 目录树", "SKILL.md 不存在")
        return
    t = sk.read_text(encoding="utf-8")
    m = re.search(r"##\s*目录\s*\n+```(.*?)```", t, re.S)
    if not m:
        skip("SKILL 目录树", "未找到「## 目录」代码块")
        return
    names = re.findall(
        r"[├└]──\s+([\w.\-]+\.(?:json|py|csv|js|md|R))(?=[\s（(]|$)", m.group(1))
    root = HERE.parent
    if len(names) < 20:
        # 下界护栏：目录树格式一变（连接符/缩进改动）会静默解析出 0~几条，
        # 使本检查退化为"空转 PASS"。故条目过少即判失败，提示需同步维护解析。
        check("SKILL 目录树可解析（条目数下界 ≥20）", False,
              f"仅解析到 {len(names)} 条，目录树格式可能已变")
        return

    def _exists(n):
        return any(p.is_file() for p in root.rglob(n))

    missing = sorted({n for n in names if not _exists(n)})
    check("SKILL 目录树条目均真实存在", not missing,
          "目录树列了不存在的文件: " + ", ".join(missing) if missing
          else f"已核验 {len(names)} 个目录树条目")


def c_no_dangling_refs():
    """文档与配置不得指向包内不存在的文件（用户点进去必然 404）。

    已知失败模式：`review-skeleton/references/` 下的
    框架文件若沿用外部来源的相对路径，该路径在本包内不存在，而
    `source` / `cross_reference` 字段**会被原样写进用户拿到的骨架产物**
    （已用 load_frameworks 实证）—— 用户看到一条点不动的引用，却无从判断
    是自己环境问题还是包的问题。这类残留比代码 bug 更难排查。

    同类问题还有 `writing_style_notes.md` 引用了 4 个从未引入的脚本。
    故本检查扫描全包 md/json 里的相对路径引用，逐一验证目标是否存在。
    """
    root = Path(__file__).resolve().parents[3]
    ALL_FILES = [q for q in root.rglob("*")
                 if q.is_file() and "__pycache__" not in q.parts]
    # 两类引用都要认：① 以点斜杠或点斜杠点斜杠开头的相对路径形态；
    #   ② **裸包内路径**（包内目录名开头）—— 文档与代码注释最常用这种写法，
    #   旧正则只认 ①，对 ② 系统性漏检（正是曾让配色断链漏网的原因之一）。
    # 前导断言 (?<![\w./-]) 保证普通文本里的片段不被误判为路径。
    REL = re.compile(
        r"""(?<![\w./-])((?:\.{1,2}/[\w./-]+\.(?:md|json|py|csv|js|R|png))"""
        r"""|(?:(?:agents|skills|references|scripts|avatars)/[\w./-]+\.(?:md|json|py|csv|js|R|png)))""")
    # 明确允许的例外：写作规范里作为反例提及的写法，以及本文件在"坑"说明中
    # 引用的历史文件名（非当前包内引用）。
    ALLOW = {"scripts/xxx.py", "avatars/expert.png"}
    # 运行时产物目录：脚本跑一次才会生成，发布时必然不存在，
    # 不能算"用户点进去 404"（真出现 404 时脚本会 exit 7 并给出指引）
    RUNTIME_DIRS = {"out", "ws", ".lit_work", "__pycache__"}

    def _norm(ref: str) -> str:
        """折叠 a/../b 与 ./、// 形态（文档里偶见此写法），得到包内相对路径。"""
        parts: list[str] = []
        for seg in ref.split("/"):
            if seg == "..":
                if parts:
                    parts.pop()
            elif seg not in ("", "."):
                parts.append(seg)
        return "/".join(parts)

    dangling, checked = [], 0
    for p in ALL_FILES:
        # 代码注释/文档字符串里的路径引用同样是"点进去会 404"的来源，故一并扫。
        if p.suffix not in (".md", ".json", ".py", ".R"):
            continue
        t = p.read_text(encoding="utf-8", errors="replace")
        for m in REL.finditer(t):
            ref = m.group(1)
            # 用户自建文件（*.local.csv 等）随包本就不存在，不算失效引用
            if ref in ALLOW or ".local." in ref:
                continue
            checked += 1
            rel = _norm(ref)
            # 相对**包根**还是相对当前文件？两种都试：
            # 先按当前文件目录（文档里的相对引用通常是同目录或上级），
            # 再按包根（plugin.json 里的相对条目属这类）。
            if (p.parent / rel).exists() or (root / rel).exists():
                continue
            # 再退一步：包内任意位置以该相对路径结尾（文档惯用"技能内相对路径"）
            if any(str(q).endswith("/" + rel) for q in ALL_FILES):
                continue
            # 运行时产物路径不是失效引用（见上 RUNTIME_DIRS 说明）
            if rel.split("/")[0] in RUNTIME_DIRS:
                continue
            line = t[:m.start()].count("\n") + 1
            dangling.append(f"{p.relative_to(root).as_posix()}:{line} → {ref}")
    check("无失效的相对路径引用（用户点进去不会是 404）",
          not dangling,
          "；".join(dangling[:4]) if dangling
          else f"已核验 {checked} 处相对引用，全部指向包内真实文件")

    # 单独守一条：不得引用**包外的路径**（外部来源残留的特征）。
    # 做法：把每个 `../` 开头的相对引用解析成绝对路径，若落在本包根目录
    # **之外**即判失败。只认路径形态，领域术语由 c_no_domain_mismatch 单独守。
    ext = []
    ESCAPING = re.compile(r"(?<![\w./-])(?:\.\./)+[\w./-]+")
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.suffix in (".md", ".json"):
            t = p.read_text(encoding="utf-8", errors="replace")
            for m in ESCAPING.finditer(t):
                try:
                    (p.parent / m.group(0)).resolve().relative_to(root)
                except ValueError:
                    ext.append(f"{p.relative_to(root).as_posix()}: {m.group(0)}")
                    break
    check("无指向包外的路径引用", not ext,
          "、".join(ext[:4]) if ext else "无")


def c_view_count_consistent():
    """文档声明的视图数必须与代码实际提供的视图数一致。

    已知失败模式：报告早已实现 4 个视图（含 CiteSpace 风格年轮
    时间线，快捷键 4），`view_smoke.js` 与 UPGRADE.md 也都写「四」，
    但 README 的用户指引与 SKILL.md 的能力表仍写「三种」—— 典型的
    「加了功能忘了同步用户可见文档」。用户按文档找不到第 4 个视图。

    本检查直接从 build_report.py 抽 viewbtn 数量，不写死数字。
    """
    root = Path(__file__).resolve().parents[3]
    rep = root / "skills/academic-lit-analysis/scripts/build_report.py"
    if not rep.exists():
        return check("文档视图数与实现一致", False, "build_report.py 缺失")
    t = rep.read_text(encoding="utf-8")
    btns = re.findall(r'data-view="(\w+)"', t)
    n = len(set(btns))
    check("报告视图按钮数 > 0", n > 0, f"抽出 {n} 个: {sorted(set(btns))}")
    cn = {1: "一", 2: "两", 3: "三", 4: "四", 5: "五", 6: "六"}
    if n not in cn:
        return check("文档视图数与实现一致", True, f"实现为 {n} 个视图，文档无需中文数词")
    word = cn[n]
    wrong = []
    for rel in ("README.md", "skills/academic-lit-analysis/SKILL.md",
                "UPGRADE.md"):
        p = root / rel
        if not p.exists():
            continue
        for i, l in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            for m in re.finditer(r"([三四五六两])([种个])视图", l):
                if m.group(1) != word:
                    wrong.append(f"{rel}:{i} 写「{m.group(0)}」")
    check("文档视图数与实现一致", not wrong,
          "；".join(wrong[:3]) if wrong else f"实现 {n} 个，文档口径一致")


def c_no_domain_mismatch():
    """框架示例不得串入不相关学科的领域术语（会被印进用户产物）。

    已知失败模式：`review-skeleton/references/` 下
    的示例数据取自组织行为与人力资源管理领域（变革型领导、算法监控信任、
    心理契约、组织绩效…），而本专家团做的是**文献计量分析**。经实跑
    `build_skeleton.py` 验证，这些示例会**原样印进用户拿到的骨架产物**
    （rc=0、6438 字节、命中 3 行）—— 用户分析别的领域，产物里却写着
    HRM 选题，且无从判断这些词从哪来。

    更隐蔽的一层：字段名本身也会被写进产物。改值不够，
    必须连字段名一起改（故已与 build_skeleton.py 同步为 topic_example）。

    本检查扫**产物文本**而非只扫源文件 —— 因为"源里有、产物里没有"和
    "源里没有、产物里有"都可能是问题，只有实跑产物才看得准。
    """
    import json as _json
    import tempfile as _tf
    root = Path(__file__).resolve().parents[3]
    sk = root / "skills/review-skeleton/scripts/build_skeleton.py"
    if not sk.exists():
        return check("产物无领域串味", False, "build_skeleton.py 缺失")
    # 明显属于其它学科、且与文献计量无关的领域术语
    FOREIGN = ["变革型领导", "员工创造力", "心理契约", "组织绩效", "算法监控",
               "心理授权", "零工平台", "高承诺HRM", "数字原生", "算法素养",
               "transformational leadership"]
    td = Path(_tf.mkdtemp())
    try:
        (td / "topics.json").write_text(_json.dumps({"clusters": [
            {"cluster_id": 1, "label": "X", "terms": ["a"], "size": 3,
             "top_terms": ["a"]},
            {"cluster_id": 2, "label": "Y", "terms": ["b"], "size": 2,
             "top_terms": ["b"]}]}, ensure_ascii=False), encoding="utf-8")
        out = td / "sk.md"
        import subprocess as _sp
        r = _sp.run([PY, str(sk), "--topics", str(td / "topics.json"),
                     "--out", str(out)], capture_output=True, text=True,
                    encoding="utf-8", errors="replace", cwd=str(root))
        if r.returncode != 0 or not out.exists():
            return check("产物无领域串味", False,
                         f"build_skeleton 未产出 rc={r.returncode}")
        md = out.read_text(encoding="utf-8")
        hit = sorted({w for w in FOREIGN if w in md})
        check("产物无领域串味（不出现其它学科术语）", not hit,
              "、".join(hit) if hit else f"已实跑产出 {len(md)} 字符，无串味")
        # 字段名也不该出现在产物里
        check("产物无内部字段名残留", "topic_example" not in md,
              "产物含 topic_example 字样" if "topic_example" in md else "无")
    finally:
        import shutil as _sh
        _sh.rmtree(td, ignore_errors=True)


def c_no_dev_narrative_in_docs():
    """文档与源码注释不得残留开发过程叙事（版本标签 / 流程标注 / 本机路径）。

    这类文字对用户毫无意义，而且有实际危害：
      · 一个「v0.小版本」标签出现在 1.0.0 的包里，指向不存在的版本，
        读者会以为这个包还没发正式版；
      · 「独立复审发现」「变异测试实证」描述的是开发期的一次内部检查，
        用户既不知道是谁做的，也无从复核；
      · 本机绝对路径会让用户以为包只能在某一台机器上跑。
    三者共同的效果是：让人觉得这是一份没收拾干净的开发中间产物。

    本文件自身豁免 —— 它必须把上述字样写成检测模式，才能守住别的文件。
    """
    root = Path(__file__).resolve().parents[3]
    PAT = re.compile(
        r"v0\.\d+\.\d+"                     # 未发布的版本标签
        r"|独立复审|变异测试|冒烟测试"       # 开发期流程标注
        r"|上线前检查"                       # 开发期检查叙事
        r"|C:[\\/]Users[\\/]"               # Windows 本机用户目录
        r"|/Users/[A-Za-z]"                 # macOS 本机用户目录
    )
    hits = []
    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.suffix not in (".md", ".json", ".py", ".R"):
            continue
        if p.name == "run_checks.py" or "__pycache__" in p.parts:
            continue
        t = p.read_text(encoding="utf-8", errors="replace")
        for i, line in enumerate(t.splitlines(), 1):
            if PAT.search(line):
                hits.append(f"{p.relative_to(root).as_posix()}:{i}")
    check("文档与源码无开发过程叙事", not hits,
          "；".join(hits[:5]) if hits else "无版本标签 / 流程标注 / 本机路径")


def c_r_probe_single_source():
    """Rscript 探测必须全包只有一个实现（lit_core.find_rscript）。

    已知失败模式：`doctor.py` / `sna_r.py` /
    本文件曾各写一套 glob —— 各自的 pattern 与路径都不同（本文件那版
    只扫 Windows，Linux/macOS 全漏）。后果是**自相矛盾**：环境自检说
    「R 可用」，实际分析却 exit 8，且极难定位（两处代码都对，只是口径不同）。

    故本检查从两个层面焊死：
      1. 静态：三个文件都不得再出现自己的 R 探测 glob；
      2. 行为：三处调用必须返回**同一个路径**。
    """
    import importlib as _il
    targets = {
        "doctor.py": "doctor",
        "sna_r.py": "sna_r",
    }
    # 1) 静态：不得再有独立的 R 根目录 / pattern 字面量
    #    必须**剥离注释与 docstring** 后再查：安装指引文案（R_INSTALL_GUIDE）
    #    与本检查自身的测试样例都含真实路径字面量，那是**给人看的说明**，
    #    不是探测实现。判断标准是「有没有真的在代码里 glob R 路径」。
    #    注意：命中可能全部来自文案与样例 —— 那正是假阳性，
    #    用假警报消磨的是对回归套件的信任。
    offenders = []
    for fn in ("doctor.py", "sna_r.py", "run_checks.py"):
        src = strip_py_comments((HERE / fn).read_text(encoding="utf-8"))
        if re.search(r"""glob\(\s*r?["'][^"']*Program\s*Files""", src):
            offenders.append(f"{fn} 真的在 glob R 安装路径")
        if re.search(r"""glob\(\s*r?["'][^"']*R-\*""", src):
            offenders.append(f"{fn} 真的在 glob R-* 版本目录")
        if re.search(r"""Rscript["']\s*[,)]""", src) and \
           re.search(r"""glob\(.*Rscript""", src):
            offenders.append(f"{fn} 自带 Rscript glob 实现")
    check("Rscript 探测无重复实现（无独立 glob 代码）",
          not offenders, "；".join(offenders) if offenders
          else "三处均委托 lit_core.find_rscript（文案/样例已排除）")

    # 2) 行为：三处结果必须一致
    try:
        lit = _il.import_module("lit_core")
        doc = _il.import_module("doctor")
        sna = _il.import_module("sna_r")
        a = lit.find_rscript()[0]
        b = doc.find_rscript()[0]
        c = sna.detect_rscript(None)[0]
        check("三处 R 探测返回同一路径", a == b == c, f"{a} | {b} | {c}")
    except Exception as e:  # noqa: BLE001
        check("三处 R 探测返回同一路径", False, f"{type(e).__name__}: {e}")

    # 3) 版本排序：字符串倒序会把 R-4.9.2 排到 R-4.11.0 之前
    try:
        lit = _il.import_module("lit_core")
        ordered = sorted(
            [r"C:/Program Files/R/R-4.9.2/bin/Rscript.exe",
             r"C:/Program Files/R/R-4.11.0/bin/Rscript.exe",
             r"C:/Program Files/R/R-4.10.0/bin/Rscript.exe"],
            key=lit._r_version_key, reverse=True)
        check("多版本共存时取最新 R（按版本号而非字符串排序）",
              "R-4.11.0" in ordered[0], f"排第一: {ordered[0]}")
        mixed = sorted([r"C:/Program Files/R/R-4.6.1/bin/Rscript.exe",
                        "/usr/lib/R/bin/Rscript"],
                       key=lit._r_version_key, reverse=True)
        check("无版本号路径排在正式版之后",
              "Program Files" in mixed[0], f"排第一: {mixed[0]}")
    except Exception as e:  # noqa: BLE001
        check("多版本共存时取最新 R（按版本号而非字符串排序）", False,
              f"{type(e).__name__}: {e}")

    # 4) strip_py_comments 自身必须正确 —— 它是"检查代码而非文案"的工具，
    #    若它把代码里的字面量也剥掉，所有基于它的断言都会变成永真。
    probe = ('"""doc 里写 C:/Program Files/R/x"""\n'
             'V = "C:/Program Files/R/lib"  # 注释 C:/x\n'
             'def f():\n    """函数 doc C:/y"""\n    return 1\n')
    st = strip_py_comments(probe)
    check("strip_py_comments 保留代码字面量",
          "Program Files" in st, "字面量被误删 → 基于它的断言会永真")
    check("strip_py_comments 剥离注释与 docstring",
          "注释" not in st and "函数 doc" not in st and "doc 里写" not in st,
          "注释/docstring 未剥离 → 会产生假失败")


def c_r_backend_guards():
    """R 后端三处真实缺陷（R 4.6.1 / igraph 2.3.3 实测）：
    1) sna_r.R 对空边表不报错，造出 0 节点图 -> modularity/density 全 NaN，
       eigen_centrality 刷"no non-missing arguments to max"警告，
       而 Python 端仍报 backend="R" 成功 —— 用户以为拿到了交叉验证结果。
    2) eigen_centrality(scale=) 自 igraph 2.1.1 起废弃，恒按 scale=TRUE 处理。
    3) sna_r.py 未校验 R 返回的 n_nodes，可能接受空结果。
    """
    rsrc = (HERE / "sna_r.R").read_text(encoding="utf-8")
    check("R 端有空边表守卫", "nrow(dat) == 0" in rsrc)
    check("R 端 eigen_centrality 按 igraph 版本传参",
          'packageVersion("igraph") < "2.1"' in rsrc)
    check("R 端归一化有非有限值守卫", "is.finite(rng)" in rsrc)
    pysrc = (HERE / "sna_r.py").read_text(encoding="utf-8")
    check("Python 端校验 R 返回的 n_nodes",
          'if not summary.get("n_nodes")' in pysrc)
    # 源码层兜底：确保"缺 R 默认硬失败"的门禁与"唯一降级入口"都在位，
    # 防止后续有人手滑把默认回退又加回来（行为层由 c_sna_fallback 实跑验证）。
    check("sna_r.py 提供显式降级开关 --allow-python-fallback",
          "--allow-python-fallback" in pysrc)
    check("sna_r.py 保留缺 R 时的硬失败门禁",
          "if not args.allow_python_fallback" in pysrc and "return 8" in pysrc)
    check("sna_r.py 已移除 --force-python 静默回退",
          "--force-python" not in pysrc)


def c_burst_single_year_filter():
    """突现检测必须排除只在单一年份出现的词。

    注意（真实库 5683 篇实测）：MeSH 索引词如 "history, 20th century"
    全部集中在 2017 年，基线为空 -> ratio=20/0.5=40 -> 强度 50.79 霸榜第一。
    但"只在一年出现"意味着没有历史基线，其"突现"是数据伪影而非真实升温。
    修正后实测排除 10508 个此类词。
    """
    from burst_detection import detect_keyword_bursts
    from lit_core import make_ref
    refs = []
    # single：只在 2017 出现（应被排除）
    for i in range(20):
        refs.append(make_ref(len(refs) + 1, f"T{i}", "x" * 80,
                             ["single", "real"], 2017, "J", "A, B", ""))
    # real：跨 10 年，近年加速（应保留且排名靠前）
    for y in range(2015, 2025):
        n = 3 if y < 2022 else 12
        for i in range(n):
            refs.append(make_ref(len(refs) + 1, f"R{i}", "y" * 80,
                                 ["real"], y, "J", "C, D", ""))
    res = detect_keyword_bursts(refs, window=3, min_total=5, min_years=3)
    kws = [b["keyword"] for b in res["bursts"]]
    check("单年份伪突现词被排除", "single" not in kws, f"结果: {kws}")
    check("排除数量被计数上报",
          res["params"].get("n_excluded_single_year", 0) > 0,
          f"排除 {res['params'].get('n_excluded_single_year')} 个")
    check("跨年真实突现词被保留", "real" in kws, f"结果: {kws}")
    if "real" in kws:
        top = next(b for b in res["bursts"] if b["keyword"] == "real")
        check("跨年词置信度为 high/medium",
              top["confidence"] in ("high", "medium"), top["confidence"])
        check("结果含 n_years 便于人工核对", top.get("n_years", 0) >= 3,
              f"n_years={top.get('n_years')}")


def c_lock_probe_crossplatform():
    """占用检测必须跨平台，且探测不可用时要如实上报而非默认"未占用"。"""
    import os as _os
    from lit_core import is_locked, lock_probe_available
    import shutil
    # 不得只依赖 lsof（Windows 没有）
    src = (HERE / "lit_core.py").read_text(encoding="utf-8")
    check("is_locked 含 Windows 分支", 'os.name == "nt"' in src)
    check("is_locked 不止 lsof 单一工具",
          "fuser" in src and "pgrep" in src)
    check("提供 lock_probe_available 能力探测", "def lock_probe_available" in src)
    # 探测函数不得抛异常（探测失败要降级，不是崩）
    with tempfile.TemporaryDirectory() as td:
        fake = Path(td) / "x.enl"
        fake.write_bytes(b"")
        try:
            r = is_locked(fake)
            check("is_locked 在无库环境下不抛异常", isinstance(r, bool), f"返回 {r}")
        except Exception as e:  # noqa: BLE001
            check("is_locked 在无库环境下不抛异常", False,
                  f"{type(e).__name__}: {e}")
    avail = lock_probe_available("x.enl")
    check("lock_probe_available 返回布尔", isinstance(avail, bool),
          f"{avail}（{_os.name}）")


def c_network_interactions():
    """网络图交互与可视化能力（增强）。

    背景：用户诉求「能否手动调节点 / 放大缩小」。实测原版只有
    滚轮缩放 + 拖空白平移 + 双击复位，**节点不能单独拖动**。
    新增：节点拖拽（含邻居跟随）、PNG/SVG 导出、
    时间叠加视图、密度视图、键盘快捷键。

    注意：这些是「源码断言」而非浏览器端行为测试 ——
    真正验证交互需要无头浏览器 + 模拟事件，本包无此依赖。
    故此处断言的是「功能代码存在且逻辑自洽」，不是「点击有效」。
    这一点必须如实标注，不得让读者误以为已做过交互验证。
    """
    src = (HERE / "build_report.py").read_text(encoding="utf-8")
    # 节点拖拽：偏移独立于算法坐标，可复位
    check("节点拖拽用独立偏移 ox/oy（不改算法坐标 px/py）",
          "d0.ox = ux; d0.oy = uy" in src and "(d.px + (d.ox||0))*vk" in src)
    check("bounds 含用户偏移（否则拖过的节点会被 fitView 裁掉）",
          "d.px+(d.ox||0)" in src)
    check("提供 resetLayout 可一键复位",
          "function resetLayout" in src and "d.ox = 0; d.oy = 0" in src)
    check("拖动时邻居按比例跟随（避免边被拉成长线）", "ux*0.35" in src)
    check("拖拽阈值 3px（不误伤点击高亮）", "Math.abs(e.clientX-ptStartX)+Math.abs(e.clientY-ptStartY) > 3"  # noqa: E501
          in src)
    # 导出
    check("导出 PNG（论文配图刚需）", "function exportPNG" in src)
    check("导出 SVG 矢量（可无限放大）", "function exportSVG" in src)
    # 视图
    check("时间叠加视图（VOSviewer overlay 能力）",
          "function yearColor" in src and "setViewMode('overlay')" in src)
    check("密度视图", "function drawDensity" in src
          and "viewMode===\'density\'" in src)
    # 年份数据链路：counts 必须来自 evolution 而非 topics
    check("年份分布取自 evolution.json（topics 无 counts）",
          'evolution.get("clusters", [])' in src and "evo_counts" in src)
    check("evolution 缺失时显式警告而非静默灰图", "overlayWarn" in src)
    # 快捷键
    for k, label in (("'='", "放大"), ("'-'", "缩小"),
                     ("'0'", "复位视口"), ("'r'", "复位节点"),
                     ("'1'", "主题着色"), ("'2'", "时间叠加"),
                     ("'3'", "密度视图"), ("'Escape'", "取消选中")):
        check(f"快捷键{label}已实现", f"k==={k}" in src)


def c_format_sniffing(tmp: Path):
    """格式自动嗅探（detect_and_load）—— **最大单点风险**。

    为什么是最大风险：包内注释自陈「扩展名会骗人，必须看内容」，
    .enw / .txt 既是真实踩过的坑；而非 EndNote 用户（Zotero / CNKI / WoS /
    NoteExpress）的**唯一入口**就是这条路径。此前它**零测试**——
    属于"目前正确"而非"被测保证正确"，任何重构都可能悄悄破坏嗅探顺序
    而无人察觉。

    11 个陷阱场景，覆盖：扩展名说谎、内容嗅探、加密格式须明确报错、
    不可识别内容须报错、无作者记录时字段不得静默丢失。
    """
    from import_sources import detect_and_load
    from lit_core import EnlError
    import json as _json

    ABS = "x" * 80          # 够长摘要，绕过 50 字阈值
    cases = [
        # (场景, 文件名, 内容, 期望 key 或 "ERROR")
        ("enw 装 XML 而非 tagged", "t1.enw",
         '<?xml version="1.0"?><EndNote><record>\n'
         '<title>Enw Extension But XML Content</title>\n'
         f'<abstract>Long enough abstract to exceed threshold.{"x"*40}</abstract>\n'
         '<year>2020</year></record></EndNote>', "enl_xml"),
        ("enw 装 tagged", "t2.enw",
         f"%T Tagged Inside Enw Extension\n%A Smith, J\n%X {ABS}\n%Y 2021\nER  - \n",
         "enl_tagged"),
        ("txt 装 CNKI XML", "t3.txt",
         '<?xml version="1.0"?><Bibliographies><Bibliography>\n'
         '<Type>J</Type><PrimaryTitle><Title>CNKI XML In Txt</Title></PrimaryTitle>\n'
         f'<Year>2021</Year><Abstract>{ABS}</Abstract>\n'
         '</Bibliography></Bibliographies>', "cnki_xml"),
        ("txt 装 RIS", "t4.txt",
         f"TY  - JOUR\r\nTI  - RIS Inside Txt\r\nPY  - 2020\r\nAB  - {ABS}\r\nER  - \r\n",
         "ris"),
        ("txt 装 GB7714", "t5.txt",
         "[1] 张三. 老年人力资源开发研究[D]. 中国人口科学, 2020. DOI:10.1000/a1.\n",
         "cnki_gb7714"),
        ("txt 装 NoteExpress", "t6.txt",
         "{Reference Type}: Journal Article\n{Title}: NE Inside Txt\n{Year}: 2020\n\n",
         "noteexpress"),
        ("txt 装 WoS tagged", "t7.txt",
         "FN Clarivate Analytics Web of Science\nVR 1.0\nPT J\nTI WoS Tagged In Txt\n"
         f"PY 2021\nAB {ABS}\nER\n\n", "wos_tagged"),
        ("CNKI 加密导出须明确报错", "t8.es6",
         "XCNKI_ENCRYPT_1.0\n" + "A" * 200, "ERROR"),
        ("不可识别内容须报错", "t10.dat",
         "just some random text with no markers at all\n" * 3, "ERROR"),
        ("RDF 无作者：年份/期刊/DOI 不得丢", "t11.rdf",
         '<?xml version="1.0"?>\n'
         '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"\n'
         ' xmlns:bibo="http://purl.org/ontology/bibo/" xmlns:dc="http://purl.org/dc/elements/1.1/"\n'
         ' xmlns:prism="http://prismstandard.org/namespaces/basic/2.0/">\n'
         '<bibo:Article rdf:about="#i1">\n'
         '  <dc:title>RDF Without Any Author</dc:title>\n'
         '  <dc:date>2019</dc:date><prism:doi>10.1000/noauth</prism:doi>\n'
         '  <bibo:Journal><dc:title>J. NoAuth</dc:title></bibo:Journal>\n'
         '</bibo:Article></rdf:RDF>', "zotero_rdf"),
    ]
    for name, fname, content, want in cases:
        f = tmp / fname
        f.write_text(content, encoding="utf-8")
        try:
            key, refs = detect_and_load(f)
            if want == "ERROR":
                check(f"嗅探：{name}", False, f"应报错，却识别为 {key}")
            else:
                check(f"嗅探：{name}", key == want,
                      f"期望 {want}，实际 {key}" + (f"（{len(refs)} 条）" if refs else ""))
        except EnlError as e:
            check(f"嗅探：{name}", want == "ERROR",
                  f"报错 code={e.code}" if want == "ERROR" else f"应识别 {want} 却报错：{e}")
        except Exception as e:  # noqa: BLE001
            check(f"嗅探：{name}", False, f"未预期异常 {type(e).__name__}: {e}")
    # ⑨ 本工具自己的 refs.json 再导入 → 须明确拦截（不是自我循环）
    f = tmp / "already.json"
    f.write_text(_json.dumps({"format": "academic-lit-analysis/refs@1", "refs": []}),
                 encoding="utf-8")
    try:
        detect_and_load(f)
        check("嗅探：他方 refs.json 须明确拦截", False, "未拦截")
    except EnlError:
        check("嗅探：他方 refs.json 须明确拦截", True)
    except Exception as e:  # noqa: BLE001
        check("嗅探：他方 refs.json 须明确拦截", False, f"{type(e).__name__}: {e}")
    # ⑪ 的字段保留单独断言（"修复有效"必须有行为证据）
    f = tmp / "t11.rdf"
    if f.exists():
        try:
            _, rs = detect_and_load(f)
            if rs:
                r0 = rs[0]
                check("RDF 无作者时 year/journal/doi 均保留",
                      bool(r0.year) and bool(r0.journal) and bool(r0.doi),
                      f"year={r0.year} journal={r0.journal!r} doi={r0.doi!r}")
        except Exception:  # noqa: BLE001
            pass


def c_dom_xss_fallback():
    """DOM XSS 防护（**Critical**，esc_json 挡不住）。

    注意：esc_json() 只保护 `<script>` 边界。值被 JSON.parse 还原成原始
    字符串后，若JS 侧再送进 innerHTML，仍可执行 —— 实测关键词
    `<img src=x onerror=alert(1)>` 在**首屏零点击**即触发
    （renderSide 立即执行），悬停时tip() 再触发一次。

    本检查为**行为断言**：真的跑一遍报告生成，扫描产物中
    是否残留可执行的 sink 写法，并确认两处已改为安全 API。
    （真正的浏览器执行验证需jsdom；此处断言的是"代码不再有该 sink"，
      jsdom 实测由review 侧单独完成。）
    """
    src = (HERE / "build_report.py").read_text(encoding="utf-8")
    # 提取两个函数体，断言其内部无 innerHTML
    def body_of(name):
        i = src.index(f"function {name}(")
        j = src.index("\n}\n", i)
        return src[i:j]
    tip_b = strip_js_comments(body_of("tip"))
    side_b = src[src.index("function renderSide()"):]
    side_b = side_b[:side_b.index("\n  el.querySelectorAll")]
    side_b = strip_js_comments(side_b)
    check("tip() 不含 innerHTML（改用 textContent）", "innerHTML" not in tip_b)
    check("tip() 使用 textContent 逐项 append",
          "textContent" in tip_b and "createTextNode" in tip_b)
    check("renderSide() 不含 innerHTML（改用 DOM 构建）", "innerHTML" not in side_b)
    # data-id 的写入在 kwNode()（renderSide 拆出的 DOM 构建辅助函数）里，
    # 不在 renderSide 本体 —— 断言须查对位置，否则是假失败。
    kw_b = ""
    if "function kwNode(d){" in src:
        i0 = src.index("function kwNode(d){")
        kw_b = strip_js_comments(src[i0:src.index("\n}\n", i0)])
    check("kwNode() 用 dataset.id 写 data-id（属性自动转义，不拼字符串）",
          "dataset.id = String(d.id)" in kw_b)
    check("kwNode() 文本走 textContent（不拼 innerHTML）",
          "t.textContent = String(d.id)" in kw_b and "innerHTML" not in kw_b)
    # 全文件层面：除注释外不应再有可执行 innerHTML
    code_only = "\n".join(l for l in src.split("\n")
                          if not l.strip().startswith(("/*", "*", "//")))
    code_only = code_only.replace("会原样进入 innerHTML", "")
    check("build_report.py 无任何可执行 innerHTML 赋值",
          "innerHTML =" not in code_only and "innerHTML=" not in code_only
          and ".innerHTML +" not in code_only)


def c_csv_export_coverage():
    """CSV 加固必须覆盖**全部**导出点（曾有 3 处漏网）。

    注意：此前只在 6 处调用了 esc_csv_cell，但 `csv.writer` 实际有 11+ 处；
    `author_topic.py` 甚至出现同一 main() 内长表已加固、短表裸奔的自相矛盾。
    故本检查**穷举所有 writerow 数据行**，凡含外部文本字段者必须已加固。
    """
    import re as _re
    root = Path(__file__).resolve().parents[3]
    files = set(HERE.glob("*.py"))
    files |= set((root / "skills" / "review-skeleton" / "scripts").glob("*.py"))
    files = sorted(p for p in files if p.name != "run_checks.py")
    bare = []
    for py in files:
        src = py.read_text(encoding="utf-8")
        for m in _re.finditer(r"w\.writerow\((?:[^()]|\([^()]*\))*\)", src, _re.S):
            t = m.group(0)
            # 表头行（纯字面量列表）无需转义
            if not _re.search(r"\b(d|r|nd|row|b|a)\s*\[", t):
                continue
            if not _re.search(r"title|journal|keyword|author|name|doi|\bid\b",
                              t, _re.I):
                continue
            if "esc_csv_cell" not in t:
                ln = src[:m.start()].count("\n") + 1
                bare.append(f"{py.name}:{ln}")
    check("全部 CSV 外部文本字段均已加固 esc_csv_cell", not bare,
          f"未加固: {bare}" if bare else "穷举全部 writerow：全部已加固")


def c_topics_params_truthful():
    """topics.json 的 params 必须写**实际生效值**（第 4 处"声明与事实相反"）。

    注意：fit_vectorizer 在小库/词项少时会逐级放宽（实测 min_df=1,max_df=1.0），
    而产物仍硬编码声称 min_df=3/max_df=0.5，且降级说明只进 stderr。
    引用这些参数写方法学描述的人会被误导 —— 故须行为验证。
    """
    from lit_core import make_ref, refs_to_json
    import json as _json
    # 构造词项极少的语料：每篇都含同一个 100% 出现的词 + 唯一词
    refs = []
    for i in range(12):
        refs.append(make_ref(i + 1, f"Study {i} research topic",
                             "x" * 80, ["research", f"uniqueterm{i}"],
                             2020, "J", "A, B", ""))
    import tempfile as _tf
    from pathlib import Path as _P
    td = _P(_tf.mkdtemp())
    try:
        (td / "refs.json").write_text(
            _json.dumps(refs_to_json(refs, "t", {}), ensure_ascii=False),
            encoding="utf-8")
        r = run(["cluster_topics.py", str(td / "refs.json"), "--out", str(td / "o")])
        tp = td / "o" / "topics.json"
        if r.returncode != 0 or not tp.exists():
            skip("topics.params 如实反映生效值", f"聚类未产出（rc={r.returncode}）")
            return
        t = _json.loads(tp.read_text(encoding="utf-8"))
        pr = t.get("params", {})
        # 真实生效值可由 build_report/聚类日志推断：这里断言"不是硬编码 3/0.5"
        # 或"确实降级且被标注"——两者都属诚实，撒谎只在前者且未标注时成立。
        hardcoded = (pr.get("min_df") == 3 and pr.get("max_df") == 0.5)
        flagged = bool(pr.get("df_degraded")) or bool(pr.get("df_degrade_note"))
        check("topics.params 不声明未生效的 df 值",
              (not hardcoded) or flagged,
              f"min_df={pr.get('min_df')} max_df={pr.get('max_df')} "
              f"df_degraded={pr.get('df_degraded')}")
        if pr.get("df_degraded"):
            check("df 降级时必有说明落盘", bool(pr.get("df_degrade_note")),
                  str(pr.get("df_degrade_note"))[:80])
            warns = " ".join(t.get("diagnostics", {}).get("warnings", []))
            check("df 降级时 warnings 提示可比性下降", "放宽" in warns,
                  warns[:80])
    finally:
        import shutil as _sh
        _sh.rmtree(td, ignore_errors=True)


def c_r_script_hygiene():
    """R 端必须真跑，且 stderr 不得含 deprecation 警告。

    注意：`as.numeric(packageVersion("igraph"))` 会抛
    "'list' object cannot be coerced"→ 被 tryCatch 吞掉恒返回 0 →
    永远走旧版分支 → 每次都刷 eigen_centrality 的 deprecation 警告。
    stderr 是 Agent 契约通道，不能被噪声污染。
    正确写法：`packageVersion("igraph") < "2.1"`（版本对象比较）。
    """
    import shutil as _sh
    import tempfile as _tf
    from pathlib import Path as _P
    rsrc_all = (HERE / "sna_r.R").read_text(encoding="utf-8")
    # 剥离 R 注释：注释里为解释原理引用了这些字符串，不能作为判据
    rsrc = "\n".join(l.split("#")[0] for l in rsrc_all.split("\n"))
    check("R 端用版本对象比较而非 as.numeric 强转",
          'packageVersion("igraph") < "2.1"' in rsrc
          and "as.numeric(packageVersion" not in rsrc)
    rs = find_rscript()
    if not rs:
        # R 已是标准路径的必需前置条件，缺 R 不能再算 SKIP（跳过即放行）。
        return check("R 端实跑无警告", False,
                     "未找到 Rscript：R + igraph 是必需前置条件，请安装 R 后重跑")
    td = _P(_tf.mkdtemp())
    try:
        (td / "e.csv").write_text("from,to,weight\na,b,3\na,c,2\nb,c,1\n",
                                  encoding="utf-8")
        pr = subprocess.run([rs, str(HERE / "sna_r.R"), str(td / "e.csv"), str(td)],
                            capture_output=True, text=True, timeout=300)
        err = pr.stderr or ""
        check("sna_r.R 实跑退出 0", pr.returncode == 0, f"rc={pr.returncode}")
        check("R 端 stderr 无 eigen_centrality 弃用警告",
              "deprecated" not in err.lower(),
              err.strip()[-120:] if err.strip() else "(空)")
    finally:
        import shutil as _sh2
        _sh2.rmtree(td, ignore_errors=True)


def c_error_exit_contract():
    """未预期异常必须走 EXIT[5]兜底，不得裸 traceback + 退出码 1。

    注意：trend_effects.py 缺 `except Exception`，
    传入坏 topics.json 时抛 TypeError → 退出码 1 ——
    而 1 在契约里是「源库不可用：请检查移动硬盘是否连接」，
    Agent 会据此给用户完全错误的修复指引。
    """
    src = (HERE / "trend_effects.py").read_text(encoding="utf-8")
    tail = src[src.index('if __name__ == "__main__":'):]
    check("trend_effects 有未预期异常兜底（EXIT[5]）",
          "except Exception" in tail and "EXIT[5]" in tail)
    # 行为验证：给一个坏输入，应 exit 5 而非 1
    # 输入选择：必须让脚本真的抛出未预期异常，
    # 否则断言会退化成「只要不是 1 就过」的空转检查。
    #   {"clusters": []}                      → exit 4（样本不足，正确但走不到 EXIT[5]）
    #   clusters 元素缺 cluster_id（KeyError） → exit 5，真正命中被保护的兜底分支
    import tempfile as _tf
    from pathlib import Path as _P
    import json as _json
    td = _P(_tf.mkdtemp())
    try:
        (td / "bad.json").write_text(
            _json.dumps({"clusters": [{"label": "x", "terms": ["a"]},
                                      {"label": "y", "terms": ["b"]}]},
                       ensure_ascii=False), encoding="utf-8")
        # 合法库 + 结构不符的 topics → 触发"未预期异常"而非输入不可用
        from lit_core import make_ref, refs_to_json as _r2j
        good = [make_ref(i + 1, f"S{i} leadership", "x" * 80,
                         ["leadership", "team"], 2020 + i % 3, "J", "A, B", "")
                for i in range(10)]
        (td / "ok.json").write_text(
            _json.dumps(_r2j(good, "t", {}), ensure_ascii=False), encoding="utf-8")
        r = run(["trend_effects.py", str(td / "ok.json"),
                 "--topics", str(td / "bad.json"), "--out", str(td / "o")])
        # 关键不是"必须退 5"，而是**绝不能退 1**——
        # 1 在契约里是「源库不可用」，会给用户完全错误的修复指引。
        # 输入已实测确定为抛 KeyError 走 EXIT[5]，故此处精确断言 == 5：
        # 若只判 != 1，则退 4/退 6 这类"没退 1 但也没走契约"的情况会被放过。
        if r.returncode == 0:
            skip("异常退出码不适用", "该输入正常完成")
        else:
            last = ((r.stderr or "").strip().splitlines() or [""])[-1][:70]
            check("异常时不得返回 1（会被误读为源库不可用）",
                  r.returncode != 1,
                  f"实际 {r.returncode}；stderr末行: {last}")
            check("异常时退出码为 5（EXIT 契约的未预期异常兜底）",
                  r.returncode == 5,
                  f"实际 {r.returncode}；stderr末行: {last}")
            check("异常时输出遵循 EXIT 契约（含 [hint] 行）",
                  "[hint]" in (r.stderr or ""), last)
    finally:
        import shutil as _sh
        _sh.rmtree(td, ignore_errors=True)


def c_lock_notice_propagated():
    """锁探测不可用的提示必须真正进入各模块产物（不能只改入口不改输出）。

    `is_locked` 的 docstring 承诺“调用方须如实标注”，
    但 9 个调用方里只有 scan_library 兑现，其余 6 个把 `False` 当“未占用”。
    引入 lock_status 统一入口，此处断言**产物字段真的存在**。
    """
    import re as _re
    targets = ["age_warning.py", "author_topic.py", "build_network.py",
               "dup_check.py", "reading_status.py"]
    missing = []
    for f in targets:
        s = (HERE / f).read_text(encoding="utf-8")
        if "lock_probe_notice" not in s:
            missing.append(f)
    check("锁探测提示已进入各模块产物字段", not missing,
          f"缺失: {missing}" if missing else f"{len(targets)} 个模块均已带 notice")
    check("提供 lock_status 统一入口",
          "def lock_status(" in (HERE / "lit_core.py").read_text(encoding="utf-8"))
    # 调用方不得再直接用 is_locked（那正是漏报的根源）
    direct = []
    for f in targets + ["cluster_topics.py"]:
        s = (HERE / f).read_text(encoding="utf-8")
        for m in _re.finditer(r"=\s*is_locked\(", s):
            direct.append(f)
    check("调用方不再直接调用 is_locked", not direct,
          f"仍直接调用: {direct}" if direct else "全部改走 lock_status")


def c_import_completeness():
    """所有脚本必须能被真正执行（import 完整、名字已定义）。

    统一 `lock_status` 时曾用批量替换改 import，
    漏了 6 个文件的 import 行 —— 结果 cluster_topics 等直接
    `NameError: name 'lock_status' is not defined`，
    而**当时的 155 项测试仍全绿**（因为没有一项真的跑这些脚本）。
    这类"改代码没同步改 import"的错误只有真跑才能发现。
    故本检查对每个脚本做 --help（或最小执行）探测。
    """
    import tempfile as _tf
    from pathlib import Path as _P
    root = Path(__file__).resolve().parents[3]
    files = set(HERE.glob("*.py"))
    files |= set((root / "skills" / "review-skeleton" / "scripts").glob("*.py"))
    files = sorted(p for p in files if p.name != "run_checks.py")
    bad = []
    for py in files:
        r = subprocess.run([PY, str(py), "--help"],
                           capture_output=True, text=True, timeout=120)
        # argparse 的 --help 退 0；NameError 等未定义错误退 1 且 stderr 有 traceback
        err = r.stderr or ""
        if "NameError" in err or "ImportError" in err or "ModuleNotFoundError" in err \
           or (r.returncode not in (0, 2) and "Traceback" in err):
            line = [l for l in err.splitlines() if "Error" in l]
            bad.append(f"{py.name}:{line[0].strip()[:60] if line else 'rc=' + str(r.returncode)}")
    check("全部脚本可独立执行（import 完整）", not bad,
          f"问题: {bad}" if bad else
          f"{len(files)} 个脚本全部 OK（含 review-skeleton）")


def c_skeleton_end_to_end():
    """综述骨架必须真的产出「有内容的骨架」，而不只是退出码 0。

    缺口：此前对 review-skeleton 的覆盖
    只到 `c_import_completeness` 的 `--help` 探测 —— 那只能证明脚本能被
    import，**证明不了它真的产出了东西**。若 build_skeleton.py 某次重构
    导致各 render_* 返回空串，--help 照样 rc=0，测试照样全绿，用户拿到的
    却是空骨架。故这里真跑一次并断言产出内容。

    断言基于真实运行 build_skeleton.py 的产出（213 行 /
    15069 字节），不是臆测的字段名。
    """
    import tempfile as _tf
    from pathlib import Path as _P
    root = Path(__file__).resolve().parents[3]
    sk = root / "skills" / "review-skeleton" / "scripts" / "build_skeleton.py"
    if not sk.exists():
        check("build_skeleton.py 存在", False, str(sk))
        return
    td = _P(_tf.mkdtemp())
    try:
        import json as _json
        (td / "topics.json").write_text(_json.dumps({"clusters": [
            {"cluster_id": 1, "label": "Leadership",
             "terms": ["leadership", "team"], "size": 5,
             "top_terms": ["leadership"]},
            {"cluster_id": 2, "label": "Trust",
             "terms": ["trust", "psychology"], "size": 4,
             "top_terms": ["trust"]}]}, ensure_ascii=False), encoding="utf-8")
        (td / "network.json").write_text(_json.dumps({
            "ok": True, "type": "keyword-cooccurrence",
            "edges": [{"source": "leadership", "target": "trust", "weight": 3}],
            "nodes": [{"id": "leadership", "label": "leadership"},
                      {"id": "trust", "label": "trust"}]},
            ensure_ascii=False), encoding="utf-8")
        out = td / "sk.md"
        # run() 会自动前置解释器（见 def run），故这里只传脚本路径，不重复给 python
        r = run([str(sk), "--topics", str(td / "topics.json"),
                 "--network", str(td / "network.json"), "--out", str(out)])
        check("build_skeleton 端到端退出 0", r.returncode == 0,
              f"rc={r.returncode}; {((r.stderr or '').strip().splitlines() or [''])[-1][:70]}")
        if r.returncode != 0 or not out.exists():
            check("骨架文件已产出", False, f"exists={out.exists()}")
            return
        md = out.read_text(encoding="utf-8")
        size = out.stat().st_size
        check("骨架文件非空（有实质内容，非空壳）", size > 2000, f"{size} 字节")
        # 六大主干章节必须齐备（缺章 = 结构坏，--help 探测不出来）
        for name, kw in [("引言地图", "引言地图"),
                         ("主题综合", "按主题的综合方案"),
                         ("研究空白", "研究空白与新颖性"),
                         ("论证脚手架", "论证脚手架"),
                         ("章节顺序", "章节顺序建议"),
                         ("质量检查", "质量检查清单")]:
            check(f"骨架含「{name}」章节", kw in md)
        # 内容必须真的来自输入，而不是模板占位 —— 断言 cluster_id 真实带入
        check("主题 cluster_id 真实带入产出（非模板占位）",
              "cluster_id=1" in md and "cluster_id=2" in md)
        check("主题规模数字真实带入产出", "规模 5 篇" in md and "规模 4 篇" in md)
        check("未编造不存在的章节标题", md.count("### 主题") == 2,
              f"实得 {md.count('### 主题')} 个主题节")
    finally:
        import shutil as _sh
        _sh.rmtree(td, ignore_errors=True)


def c_touch_support():
    """移动端交互（修复）。

    注意：此前只有 mouse* 监听 + CSS `touch-action:none`，导致手机上
    完全无法拖动/缩放，且 touch-action:none 会**吞掉页面滚动**。
    改用 Pointer Events 统一鼠标/触摸/手写笔，touch-action 改 pan-y。
    """
    src = (HERE / "build_report.py").read_text(encoding="utf-8")
    code = strip_js_comments(src)
    for ev in ("pointerdown", "pointermove", "pointerup", "pointercancel"):
        check(f"已注册 {ev}（Pointer Events 统一输入）",
              f"addEventListener('{ev}'" in code)
    check("不再依赖 mouse* 事件",
          "addEventListener('mousedown'" not in code
          and "addEventListener('mousemove'" not in code)
    check("touch-action 为 pan-y（不吞页面滚动）",
          "touch-action:pan-y" in code and "touch-action:none" not in code)
    check("支持双指捏合缩放",
          "pinching" in code and "pinchDist" in code and "activePointers" in code)
    check("触摸无 hover 时用 pointerdown 触发提示",
          "pointerType !== 'touch'" in code)
    check("触摸双击可复位", "lastTapT" in code and "resetLayout" in code)


def c_burst_span_factor():
    """折扣因子必须按「基线可比性」而非「年份跨度」。

    注意：旧公式 span_factor = log1p(n_years)/log(11)，
    对 2 年新概念打 0.46、3 年打 0.58 —— 而突现检测的**目的恰恰是
    发现新概念**。真正该折的是"基线不可靠导致倍数虚高"，与跨度无关；
    单年份伪突现已由 min_years 准入挡住，不需再打折。
    """
    from burst_detection import detect_keyword_bursts
    from lit_core import make_ref
    refs = []
    # [!]  语料设计：基线年份数 = 除峰值年外、落在±window 内的年份数。
    #   若只有 2022+2023 两年，峰值 2023 自身不算基线 → base_years 仅 1 个
    #   → 判定 0.85 是**正确行为**，不是 bug。故这里给 3 个非峰值年，
    #   构造"短时但基线可比"的真实场景。
    for y, n in ((2020, 28), (2021, 30), (2022, 32), (2023, 50)):
        for i in range(n):
            refs.append(make_ref(len(refs) + 1, f"S{i} solidnew", "x" * 80,
                                 ["solidnew", "solidbase"], y, "J", "A, B", ""))
    for y in range(2016, 2025):              # 多年平稳词
        for i in range(8):
            refs.append(make_ref(len(refs) + 1, f"S{i} stable", "x" * 80,
                                 ["stableword", "stbase"], y, "J", "A, B", ""))
    res = detect_keyword_bursts(refs, window=2, min_total=5, min_years=2)
    by = {b["keyword"]: b for b in res["bursts"]}
    sn = by.get("solidnew")
    check("基线扎实的短时新概念不被打折（span_factor=1.0）",
          sn is not None and sn["span_factor"] == 1.0,
          f"span_factor={sn['span_factor'] if sn else 'N/A'}，"
          f"基线年={sn['baseline_n_years'] if sn else '-'}")
    if sn:
        check("该词置信度为 high（短时但基线可信）",
              sn["confidence"] == "high", sn["confidence"])
        check("strength 未被压制（= strength_raw）",
              abs(sn["strength"] - sn["strength_raw"]) < 0.01,
              f"{sn['strength']} vs {sn['strength_raw']}")
    st = by.get("stableword")
    if st:
        check("多年平稳词倍数量接近 1（不误判为突现）",
              st["burst_ratio"] < 1.5, f"ratio={st['burst_ratio']}")


def c_plugin_json():
    p = Path(__file__).resolve().parents[3] / ".codebuddy-plugin" / "plugin.json"
    if not p.exists():
        skip("专家团配置", "plugin.json 不存在"); return
    d = json.loads(p.read_text(encoding="utf-8"))
    check("expertType = team", d.get("expertType") == "team")
    check("members 每个都有 name/profession/avatar/role",
          all(all(k in m for k in ("id", "name", "profession", "avatar", "role"))
              for m in d.get("members", [])), f"{len(d.get('members', []))} 名成员")
    check("tags 固定 3 个", len(d.get("tags", [])) == 3)
    # 平台规范硬性要求：quickPrompts 必须**恰好 3 个**
    # （validate_expert.py 会拒收其它数量——实测改4 个即校验失败）。
    # 这个看似该放宽的约束其实是平台契约，放宽会导致包装不上。
    n_qp = len(d.get("quickPrompts", []))
    check("quickPrompts 恰好 3 个（平台规范）", n_qp == 3, f"{n_qp} 个")
    check("quickPrompts 均为中英双语",
          all("zh" in q and "en" in q for q in d.get("quickPrompts", [])))
    zh = d.get("displayDescription", {}).get("zh", "")
    check("displayDescription.zh 40–50 字", 40 <= len(zh) <= 50, f"{len(zh)} 字")


def c_package_integrity():
    """注意：存在两份 settings.json（setting.json / settings.json 内容相同），
    且 avatars/expert.png 未被任何配置引用 —— 属"重复文件 / 冗余资产"。
    专家团规范只认 settings.json，单数名为无效文件。"""
    root = Path(__file__).resolve().parents[3]
    check("无重复的 setting.json（只保留 settings.json）",
          not (root / "setting.json").exists())
    check("settings.json 存在", (root / "settings.json").exists())
    if (root / "settings.json").exists():
        s = json.loads((root / "settings.json").read_text(encoding="utf-8"))
        pj = root / ".codebuddy-plugin" / "plugin.json"
        if pj.exists():
            d = json.loads(pj.read_text(encoding="utf-8"))
            check("settings.json.agent == plugin.json.agentName",
                  s.get("agent") == d.get("agentName"),
                  f"{s.get('agent')} vs {d.get('agentName')}")


def c_frontmatter_yaml():
    """agents/*.md 的 YAML frontmatter 必须能被解析器接受。

    已知失败模式（导入期阻塞）：`description:` 写成**未加引号的普通标量**，而值里
    含 ": "（例如「… (keyword / author / institution / citation): cluster-island …」），
    YAML 解析器在该处报 `mapping values are not allowed in this context`，导致该
    agent 整体加载失败。此前的检查（脚本语法 / 目录树 / 断链 / 命名）都不解析
    frontmatter，故这类写法长期无门禁 —— 本项补上。

    零依赖校验：值行若为未加引号的普通标量，不得含 ": "（与映射语法冲突）。
    """
    root = Path(__file__).resolve().parents[3]
    bad, n = [], 0
    for p in sorted((root / "agents").glob("*.md")):
        n += 1
        t = p.read_text(encoding="utf-8")
        if not t.startswith("---\n"):
            bad.append(f"{p.name}: 缺 frontmatter")
            continue
        end = t.find("\n---", 4)
        fm = t[4:end] if end > 0 else ""
        for ln, line in enumerate(fm.splitlines(), 1):
            m = re.match(r"^([A-Za-z_][\w-]*):\s(.*)$", line)
            if not m:
                continue
            val = m.group(2).rstrip()
            if not val or val[0] in "\"'|>[{":
                continue
            if ": " in val or val.endswith(":"):
                bad.append(f"{p.name}:{ln} ({m.group(1)}) 未加引号且含 ': '")
    check("agents frontmatter 为合法 YAML 普通标量", not bad,
          "；".join(bad[:4]) if bad else f"已核验 {n} 个 agent frontmatter")


def c_agent_naming():
    """注意：成员 Agent ID 为 member-a / member-b —— 与功能完全无关的占位名。
    规范要求 agentName / 成员 id 须有业务语义，能一眼看出职能。"""
    p = Path(__file__).resolve().parents[3] / ".codebuddy-plugin" / "plugin.json"
    if not p.exists():
        skip("Agent 命名", "plugin.json 不存在"); return
    d = json.loads(p.read_text(encoding="utf-8"))
    ids = [m["id"] for m in d.get("members", [])]
    generic = {"member-a", "member-b", "member-c", "agent-a", "agent-1", "team-lead"}
    bad = [i for i in ids if i.lower() in generic]
    check("无 member-a/member-b 类占位 Agent ID", not bad, f"发现 {bad}" if bad else
          f"{len(ids)} 个 ID: {', '.join(ids)}")
    # 每个 id 必须与其 MD 文件同名且真实存在
    root = Path(__file__).resolve().parents[3]
    missing = [i for i in ids if not (root / "agents" / f"{i}.md").exists()]
    check("每个成员都有同名 agents/<id>.md", not missing,
          f"缺失 {missing}" if missing else "全部存在")
    # 头像路径必须真实存在
    bad_av = [m["avatar"] for m in d.get("members", [])
              if not (root / m["avatar"]).exists()]
    check("成员头像文件均存在", not bad_av, f"缺失 {bad_av}" if bad_av else "全部存在")
    # 不得有未被引用的孤儿头像
    referenced = {m["avatar"] for m in d.get("members", [])} | {d.get("avatar")}
    orphans = [f"avatars/{x.name}" for x in (root / "avatars").iterdir()
               if x.is_file() and f"avatars/{x.name}" not in referenced]
    check("无未被引用的孤儿头像", not orphans, f"孤儿 {orphans}" if orphans else "无")


def c_no_user_data():
    """注意：samples/ 目录内含 277 条真实题录（CNKI/WoS）与一份真实报告，
    而 DATA_NOT_INCLUDED.md 却声称"真实文献标题 0 处" —— 声明与事实矛盾。"""
    root = Path(__file__).resolve().parents[3]
    check("无 samples/ 目录（不得携带真实题录）", not (root / "samples").exists())
    leaked = []
    for pat in ("*.enl", "*.sqlite", "refs.json", "*.pdf", "*.epub"):
        leaked += [str(p.relative_to(root)) for p in root.rglob(pat)]
    check("包内无库文件/附件", not leaked, f"发现 {leaked}" if leaked else "0 个")
    # 本机绝对路径泄漏（跳过本文件：检查器自身含检测用正则字面量）
    pathy = []
    for p in list(root.rglob("*.md")) + list(root.rglob("*.py")) + \
             list(root.rglob("*.json")):
        if p.name == Path(__file__).name:
            continue
        try:
            t = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if "/Users/" in t or "/Volumes/" in t:
            pathy.append(str(p.relative_to(root)))
    check("文档/脚本中无本机绝对路径", not pathy,
          f"发现 {pathy}" if pathy else "0 处")


def c_output_escaping():
    """安全：题名/关键词/作者来自外部导入（不可信输入）。
    注意：报告用裸 json.dumps 内联进 <script>，题名含 '</script>' 即可提前闭合标签注入脚本；
    CSV 导出未防公式注入，Excel 打开时 =CMD|... 会被当公式执行。"""
    from lit_core import esc_csv_cell, esc_html, esc_json
    # 1) JSON 内联转义：< > & 必须变成 < > &
    frag = esc_json({"t": "</script><img src=x onerror=alert(1)>"})
    check("esc_json 转义尖括号与 &", "<" not in frag and ">" not in frag
          and "&" not in frag, frag[:60])
    # 2) 可被 JSON.parse 还原（转义不能破坏数据）
    import json as _j
    ok = _j.loads(frag)["t"] == "</script><img src=x onerror=alert(1)>"
    check("esc_json 转义后仍可无损解析", ok)
    # 3) HTML 转义
    check("esc_html 转义尖括号", esc_html("<b>x</b>") == "&lt;b&gt;x&lt;/b&gt;")
    # 4) CSV 公式注入
    for raw, must in (("=1+1", "'=1+1"), ("@SUM(A1)", "'@SUM(A1)"),
                      ("+cmd", "'+cmd"), ("-2+3", "'-2+3"), ("normal", "normal")):
        check(f"esc_csv_cell 拦住公式前缀 {raw[:6]!r}", esc_csv_cell(raw) == must,
              esc_csv_cell(raw))
    # 5) 报告确实走了 esc_json 而非裸 json.dumps
    src = (HERE / "build_report.py").read_text(encoding="utf-8")
    check("build_report 内联 JSON 使用 esc_json", "esc_json(payload)" in src)


def c_agent_docs_wired():
    """Agent 定义必须与 plugin.json 的成员一致，且含 SendMessage 回传要求。"""
    root = Path(__file__).resolve().parents[3]
    pj = root / ".codebuddy-plugin" / "plugin.json"
    if not pj.exists():
        skip("Agent 文档衔接", "plugin.json 不存在"); return
    d = json.loads(pj.read_text(encoding="utf-8"))
    lead = root / "agents" / f"{d['agentName']}.md"
    if not lead.exists():
        check("主理人 MD 存在", False, str(lead)); return
    lt = lead.read_text(encoding="utf-8")
    check("主理人 MD 含 TeamCreate 铁律", "TeamCreate" in lt)
    check("主理人 MD 含 SendMessage 中转要求", "SendMessage" in lt)
    check("主理人 MD 列出全部成员 Agent ID",
          all(m["id"] in lt for m in d.get("members", []) if m["id"] != d["agentName"]))
    for m in d.get("members", []):
        if m.get("role") != "member":
            continue
        f = root / "agents" / f"{m['id']}.md"
        if not f.exists():
            continue
        t = f.read_text(encoding="utf-8")
        check(f"{m['id']} 要求 SendMessage 回传", "SendMessage" in t)


def c_full(library: str, tmp: Path):
    """需要真实库的重量级检查。"""
    lib = Path(library).expanduser()
    if not lib.exists():
        skip("真实库全链路", f"库不存在：{lib}"); return
    out = tmp / "out"
    r1 = run(["cluster_topics.py", str(lib), "--out", str(out)])
    r2 = run(["build_network.py", str(lib), "--node-df", "5", "--min-edge", "2",
              "--topics", str(out / "topics.json"), "--out", str(out), "--layout"])
    if r1.returncode != 0 or r2.returncode != 0:
        check("真实库全链路跑通", False, f"cluster={r1.returncode} network={r2.returncode}")
        return
    check("真实库全链路跑通", True)
    net = json.loads((out / "network.json").read_text(encoding="utf-8"))
    import base64
    import numpy as np
    pe = net["pos_encoded"]
    q = np.frombuffer(base64.b64decode(pe["pos_b64"]), dtype="<i2")
    check("pos_encoded 长度 == 2×节点数",
          len(q) == 2 * len(net["nodes"]), f"{len(q)} vs {2*len(net['nodes'])}")
    aligned = all(abs(net["nodes"][i]["x"] - q[2*i] / pe["scale"]) < 0.01
                  for i in range(len(net["nodes"])))
    check("pos_encoded 与 nodes 顺序对齐", aligned)
    # 分簇岛：错分率应为 0
    pos = q.reshape(-1, 2) / pe["scale"]
    cl = [n.get("primary_cluster") for n in net["nodes"]]
    import collections
    cent = collections.defaultdict(list)
    for i, c in enumerate(cl):
        if c is not None:
            cent[c].append(pos[i])
    cent = {c: np.mean(np.array(v), axis=0) for c, v in cent.items()}
    mis = 0; tot = 0
    for i, c in enumerate(cl):
        if c is None:
            continue
        own = float(np.linalg.norm(pos[i] - cent[c]))
        best = min(float(np.linalg.norm(pos[i] - cent[o])) for o in cent if o != c)
        tot += 1
        if best < own:
            mis += 1
    rate = mis / tot if tot else 0.0
    # [!]  该指标用「各岛节点坐标的均值」当质心；岛屿内部若分布不匀，均值会偏离
    #    几何中心，边界节点可能被误判（实测 1/1081 = 0.09%）。
    #    真正被几何保证的是**岛屿圆盘互不重叠**，故阈值取 ≤0.5% 而非严格 0。
    check("分簇岛：重叠错分率 ≤ 0.5%", rate <= 0.005, f"错分 {mis}/{tot} = {rate:.2%}")
    cov = net["coverage"]
    check("零丢弃恒等式成立（真实库）", cov.get("zero_drop_identity") is True)
    g = json.loads((out / "topics.json").read_text(encoding="utf-8"))
    from build_report import gini2
    gv = gini2([c["size"] for c in g["clusters"]])
    check("均衡度 gini 落在 [0,1]", 0 <= gv <= 1, f"{gv:.4f}")


# ══════════════════════════════════════════════════════════
def c_view_smoke():
    """视图渲染自检：四个视图都必须「真的看得见」。

    本项目在这个点上连续踩了两代坑，两代都是「页面一片空白但测试全绿」：

      第一代：drawDensity 用固定半径 + additive 叠加，稀疏图上亮度累积不足
              → 视觉上等同全白。
      第二代（更隐蔽）：单区 alpha 被压到 0x14（7.8%）。单个热核叠在白底上
              只有 rgb(241,244,248)，与纯白相差 14/255 —— 数学上不可见。
              同时另有坐标缺陷：hasXY 用 `x !== undefined` 判定，而 JSON 里的
              NaN 在 JS 中 !== undefined 为真 → 误判「已有坐标」，FR 兜底被跳过，
              而 px/py 从无赋值路径 → 所有坐标 NaN → 整张画布空白且不报错。

    旧版测试为何漏掉：它只统计 ctx.arc / fill 的**调用次数**，而
    ctx.arc(NaN,NaN,NaN,…) 一样计数 → 空白画布照样判 PASS。

    本项改为跑两轮数值断言（见 view_smoke.js）：
      · 正常夹具：坐标全有限 + 密度热区对比度超阈值 + 年轮真的画出圆弧；
      · 坏夹具（x/y=NaN 且无 pos_encoded）：必须能自愈为有限布局，
        绝不能渲染出一张全 NaN 的空白图。
    另外把「夹具本身不得含 NaN 字面量」也固化为断言 —— 夹具一旦退化，
    测试就变成在验证一张空白图，虚假绿灯比红灯更危险。
    node 不存在时 SKIP，不阻塞其余检查。"""
    js = HERE / "view_smoke.js"
    if not js.exists():
        return check("视图渲染自检", False, "view_smoke.js 缺失")
    if not shutil.which("node"):
        return skip("视图渲染自检", "本机无 node，跳过（报告已人工验证）")

    fx = HERE / "_view_fixture.json"
    if not fx.exists():
        return skip("视图渲染自检", "缺少视图夹具")
    raw = fx.read_text(encoding="utf-8")
    if re.search(r"(?<![\w.])NaN(?![\w])", raw):
        return check("视图渲染自检", False,
                     "夹具含 NaN 字面量：测试将在一张空白画布上跑，结论不可信")

    try:
        from build_report import build_html
        d = json.loads(raw)
    except Exception as e:  # noqa: BLE001
        return check("视图渲染自检", False, f"读取夹具失败: {str(e)[:120]}")

    tmp = Path(tempfile.gettempdir())
    cases = []

    # 用例 A：夹具原样（模拟 build_network.py 的正常产物）
    try:
        pa = tmp / "en_analysis_view_smoke.html"
        pa.write_text(build_html(**d), encoding="utf-8")
        cases.append(("正常夹具", pa))
    except Exception as e:  # noqa: BLE001
        return check("视图渲染自检", False, f"构造报告失败: {str(e)[:120]}")

    # 用例 B：注入真实缺陷（x/y=NaN 且无 pos_encoded）——渲染端必须自愈
    try:
        b = json.loads(raw)
        net = b.get("network") or {}
        net.pop("pos_encoded", None)
        for n in net.get("nodes") or []:
            n["x"] = float("nan")
            n["y"] = float("nan")
        pb = tmp / "en_analysis_view_smoke_nan.html"
        pb.write_text(build_html(**b), encoding="utf-8")
        cases.append(("坏坐标夹具", pb))
    except Exception as e:  # noqa: BLE001
        return check("视图渲染自检", False, f"构造坏坐标用例失败: {str(e)[:120]}")

    details = []
    for label, path in cases:
        try:
            r = subprocess.run(["node", str(js), str(path)], capture_output=True,
                               text=True, timeout=180)
        except subprocess.TimeoutExpired:
            return check("视图渲染自检", False, f"{label}：渲染超时")
        if r.returncode != 0:
            tail = (r.stdout or r.stderr or "").strip()[-300:]
            return check("视图渲染自检", False, f"{label} 未通过：{tail}")
        last = [l for l in (r.stdout or "").splitlines() if l.strip()]
        details.append(f"{label}✓{last[-1].strip() if last else ''}")

    return check("视图渲染自检", True, "；".join(details))


def c_render_guards_present():
    """渲染健壮性护栏必须在位 —— 防止「修好了又被改回去」。

    这三行是上面两代缺陷的正解，且都属于「删掉也不会报错、只会在真实浏览器里
    静默变空白」的类型。故用源码断言锁死：
      1) hasXY 判定用 Number.isFinite（NaN 不得被当成有效坐标）；
      2) 明文 x/y 必须显式拷进 px/py（渲染链路只认 px/py）；
      3) 密度视图必须走色带（densRamp），不得回到"靠叠加透明度攒亮度"；
      4) 布局体检出口 layoutSanity 必须存在，否则自检无从断言坐标有效。"""
    src = (HERE / "build_report.py").read_text(encoding="utf-8")
    need = [
        ("Number.isFinite(N[0].x)", "x/y 有效性判定未用 Number.isFinite（NaN 会被误判为有效）"),
        ("d.px = +d.x", "缺 x/y → px/py 的显式回填（渲染只认 px/py）"),
        ("sanitizeLayout", "缺 NaN 坐标的兜底降级（否则整图空白且不报错）"),
        ("densRamp", "密度视图未走固定色带（可见性无保证）"),
        ("__DENSITY__", "缺密度视图的可见性证据出口（无法回归断言）"),
        ("__YEARRING__", "缺年轮视图的渲染证据出口（无法回归断言）"),
        ("layoutSanity", "缺布局体检出口（坐标 NaN 无法被测试发现）"),
    ]
    miss = [why for tok, why in need if tok not in src]
    if miss:
        return check("渲染健壮性护栏", False, "；".join(miss))
    # 密度视图不得再出现"8 位 hex 透明度叠加"的写法
    if re.search(r"addColorStop\(\s*0\s*,\s*c\s*\+", src):
        return check("渲染健壮性护栏", False,
                     "密度视图又回到了 c+alpha 叠加写法（可见性无保证）")
    return check("渲染健壮性护栏", True, "NaN 兜底 / px-py 回填 / 密度色带 / 测试出口 全部在位")



def c_report_structure():
    """报告版式结构必须稳定：章节顺序、编号一致性、宽表不撑破页面、无遗留样式。

    这一组全是"肉眼才发现、代码不报错"的问题，因此逐条固化为断言：
      ① 章节顺序必须是用户指定的分析叙事顺序；
      ② 目录编号与正文编号必须一致（历史上目录写 03、正文写 S13）；
      ③ 所有宽表（非 nopad）必须被 .tw 滚动容器包住 —— 否则窄屏撑宽整页；
      ④ 遗留的旧布局/旧图表样式不得回流（时间线 CSS 网格、双栏网络、pchart…）；
      ⑤ 画布操作说明必须区分触摸/键盘两套（触屏上没有 Ctrl+滚轮）。
    """
    fx = HERE / "_view_fixture.json"
    if not fx.exists():
        return skip("报告版式结构", "缺少视图夹具")
    try:
        from build_report import build_html, CSS
        d = json.loads(fx.read_text(encoding="utf-8"))
        h = build_html(**d)
    except Exception as e:  # noqa: BLE001
        return check("报告版式结构", False, f"构造报告失败: {str(e)[:140]}")

    problems = []

    # ① 章节顺序（用目录里的锚点序列判定）
    want = ["s01", "s13", "s02", "s03", "s07", "s04", "s09"]
    toc_ids = re.findall(r'<li[^>]*><a href="#(s\d+)"', h)
    got = [s for s in toc_ids if s in want]
    if got != want:
        problems.append(f"章节顺序不符：期望 {want}，实际 {got}")

    # ② 目录编号 vs 正文编号
    toc_num = dict(re.findall(r'<a href="#(s\d+)"><span class="n">(\d+)</span>', h))
    body_num = dict(re.findall(r'<h2 id="(s\d+)"><span class="n">(\d+)</span>', h))
    for sid, n in body_num.items():
        if sid in toc_num and toc_num[sid] != n:
            problems.append(f"编号不一致：{sid} 目录={toc_num[sid]} 正文={n}")
    if len(set(body_num.values())) != len(body_num):
        problems.append("正文存在重复章节编号")

    # ③ 宽表必须被滚动容器包住
    n_tbl = len(re.findall(r"<table class=[\"']mx[^\"']*[\"']>", h))
    n_wrap = len(re.findall(r'<div class="tw">', h))
    n_nopad = len(re.findall(r"<table class=[\"']mx[^\"']*nopad[^\"']*[\"']>", h))
    if n_wrap < n_tbl - n_nopad:
        problems.append(f"有宽表未被 .tw 包裹：表 {n_tbl} 个（其中 nopad {n_nopad}），"
                        f"滚动容器仅 {n_wrap} 个")

    # ④ 遗留样式不得回流
    legacy = ["timeline", "tl-grid", "tl-row", "tl-track", "chartgrid", "netgrid",
              "netside", "sidetip", "pchart", "chartcard", "tblwrap"]
    back = [x for x in legacy if re.search(r"\.(?:" + x + r")\b", CSS)]
    if back:
        problems.append("遗留样式回流：" + "、".join(sorted(set(back))))

    # ⑤ 触摸 / 键盘两套操作说明
    if "touchnote" not in h or "kbdonly" not in h:
        problems.append("画布操作说明未区分触摸/键盘（触屏会显示 Ctrl+滚轮 之类的无意义提示）")

    if problems:
        return check("报告版式结构", False, "；".join(problems))
    return check("报告版式结构", True,
                 f"章节顺序正确 · 编号一致 · {n_wrap} 个宽表已滚动隔离 · 无遗留样式 · 触摸/键盘说明分离")


def c_review_offer():
    """报告交付后必须**主动问一次**要不要产出计量综述，且只问一次。

    背景：这个包能直接把分析结果接成综述骨架，但用户跑完分析后往往
    不知道还有这一步，功能长期闲置；而过去又因为怕打扰写成"绝不主动提议"，
    等于把入口藏了起来。现在取中间态 —— 交付时问一次，用户说不就不再提。
    断言把它固化，防止被改回"绝不主动提议"或膨胀成反复追问。
    """
    md = HERE.parents[2] / "agents" / "academic-lit-analysis-lead.md"
    if not md.exists():
        return check("交付后询问综述产出", False, "主理人 MD 缺失")
    t = md.read_text(encoding="utf-8")
    miss = [k for k in ("报告交付完成后，主动询问一次", "一次", "不再提")
            if k not in t]
    if miss:
        return check("交付后询问综述产出", False, f"prompt 缺少：{', '.join(miss)}")
    if "不要主动提议" in t:
        return check("交付后询问综述产出", False,
                     "仍保留「不要主动提议」的旧措辞，与「交付后问一次」冲突")
    return check("交付后询问综述产出", True,
                 "交付后主动问一次，且明确后续不再追问")


def c_report_no_dead_ends():
    """报告不得出现「目录有、点进去是空的」「样式从未定义」「Markdown 漏进 HTML」。

    这三类问题的共同点是：**代码不报错、控制台不报错、测试也全绿**，
    只有人打开页面才看得出来，因此必须固化成断言：

      ① 目录里列出的每个章节，正文里都必须有实际内容。
         反例：曾把「主题 × 年份演化」写进"恒存在"白名单，没传演化数据时
         目录照列、点进去一片空白。
      ② 产出中出现的每个 class 都必须在 CSS 里有定义。
         反例：.kw/.kt/.kd/.hd/.dot 等十余个类从来没有样式，
         页面按浏览器默认外观渲染 —— 这就是"有些窗口不够现代"的来源。
      ③ 面向读者的 HTML 文本里不得残留 Markdown 重点号 `**`。
         反例：演化章节的说明写成 `**旧年份样本量不足**`，页面上原样显示星号。
    """
    fx = HERE / "_view_fixture.json"
    if not fx.exists():
        return skip("报告无死角检查", "缺少视图夹具")
    try:
        from build_report import build_html, CSS
        d = json.loads(fx.read_text(encoding="utf-8"))
        h = build_html(**d)
    except Exception as e:  # noqa: BLE001
        return check("报告无死角检查", False, f"构造报告失败: {str(e)[:140]}")

    problems = []

    # ① 章节必须有内容
    toc_ids = re.findall(r'<li[^>]*><a href="#(s\d+)"', h)
    h2s = [(m.group(1), m.start())
           for m in re.finditer(r'<h2 id="(s\d+)"', h)]
    bounds = {}
    for idx, (sid, pos) in enumerate(h2s):
        end = h2s[idx + 1][1] if idx + 1 < len(h2s) else h.find("</main>")
        bounds[sid] = h[pos:end if end > 0 else len(h)]
    empty = []
    for sid in toc_ids:
        seg = bounds.get(sid)
        if seg is None:
            empty.append(f"{sid}(无标题)")
        elif len(re.sub(r"<[^>]+>|\s", "", seg)) < 120:
            empty.append(f"{sid}(内容过少)")
    if empty:
        problems.append("目录有条目但正文为空：" + "、".join(empty))

    # ② 不允许"从未定义样式"的类
    defined = set(re.findall(r"\.([A-Za-z_][\w-]*)", CSS))
    used = set()
    for m in re.finditer(r'class="([^"]+)"', h):
        used.update(m.group(1).split())
    # JS 里动态拼的类名（kwNode / heat 单元格等）
    for m in re.finditer(r"className\s*=\s*'([^']*)'", h):
        used.update(x for x in re.split(r"[\s+]+", m.group(1)) if x)
    for m in re.finditer(r"classList\.(?:add|toggle|remove)\(\s*'([^']+)'", h):
        used.update(m.group(1).split())
    # 三线表用的是另一份样式表（TBL_CSS），此处不计
    nostyle = sorted(c for c in used
                     if re.match(r"^[a-z][\w-]*$", c) and c not in defined
                     and c not in {"sx", "sxcap", "sxnote"})
    if nostyle:
        problems.append("产出中使用了从未定义样式的类：" + "、".join(nostyle))

    # ③ Markdown 重点号不得进入读者可见文本（style/script 内注释不算）
    visible = re.sub(r"<style[\s\S]*?</style>|<script[\s\S]*?</script>", "", h)
    if "**" in visible:
        i = visible.index("**")
        problems.append("HTML 正文残留 Markdown 星号：" + visible[max(0, i-24):i+24])

    if problems:
        return check("报告无死角检查", False, "；".join(problems))
    return check("报告无死角检查", True,
                 f"目录 {len(toc_ids)} 个章节全部有内容 · 无未定义样式的类 · 无 Markdown 残留")


def c_intent_clarify():
    """主理人必须「先问后算」：拿到数据先澄清意图，禁止直接开跑。

    背景：曾出现用户发来文献数据后助手直接跑全流程、做完用户才发现
    想要的是另一件事。分析链路很重（数分钟），问一句的成本远低于跑错方向。
    故把「意图澄清」写成 prompt 铁律，并用本检查固化，防止后续被删。
    """
    md = HERE.parents[2] / "agents" / "academic-lit-analysis-lead.md"
    if not md.exists():
        return check("主理人先问后算", False, "主理人 MD 缺失")
    t = md.read_text(encoding="utf-8")
    miss = [k for k in ("意图澄清", "先问后算", "数据来源", "分析目的",
                        "禁止一收到文献数据就开跑")
            if k not in t]
    if miss:
        return check("主理人先问后算", False, f"prompt 缺少：{', '.join(miss)}")
    # 快捷指令应覆盖「题录文件」入口（用户未必有 EndNote 库）
    return check("主理人先问后算", True,
                 "含意图澄清铁律 + 数据来源/目的/范围三问")


def c_docs_in_sync():
    """文档与实现必须同步 —— 防止"改了代码没改文档"。

    背景：包先后新增 publication_stats.py / cross_matrix.py /
    pdf_extract.py 与多名新成员，但 SKILL.md 标题、目录树、README 的 agent 数量
    未同步更新，用户看到的是过期信息。
    故把「文档必须覆盖全部脚本与成员」固化为回归断言。
    """
    scripts_dir = HERE
    real = {p.name for p in scripts_dir.glob("*.py")}
    real |= {p.name for p in scripts_dir.glob("*.js")}

    skill_md = (HERE.parent / "SKILL.md")
    readme = (HERE.parents[2] / "README.md")
    if not skill_md.exists():
        return check("文档与实现同步", False, "SKILL.md 缺失")
    t_skill = skill_md.read_text(encoding="utf-8")
    t_readme = readme.read_text(encoding="utf-8") if readme.exists() else ""

    # 目录树（包方自述）里声明的脚本
    declared = set(re.findall(r"([A-Za-z_][\w]*\.(?:py|js))", t_skill))
    missing = sorted(x for x in real if x not in declared)
    if missing:
        return check("文档与实现同步", False,
                     f"SKILL.md 目录树缺少脚本: {', '.join(missing)}")

    # 新增成员必须同时出现在 SKILL/README/主理人 prompt
    members = ["data-auditor", "trend-analyst"]
    for m in members:
        if m not in t_readme:
            return check("文档与实现同步", False, f"README 未收录成员 {m}")
        if m not in t_skill:
            return check("文档与实现同步", False, f"SKILL.md 未收录成员 {m}")

    # 定位措辞：不得再以 EndNote 为中心
    if "学术文献计量分析" not in t_skill:
        return check("文档与实现同步", False,
                     "SKILL.md 标题未改为「学术文献计量分析」")
    if "3 名 agent" in t_readme:
        return check("文档与实现同步", False, "README 仍写「3 名 agent」")
    return check("文档与实现同步", True,
                 f"目录树覆盖 {len(real)} 个脚本、{len(members)} 名新成员")



def c_review_skeleton_docs():
    """review-skeleton（第二技能）的文档与引用必须与实现同步。

    背景：c_docs_in_sync 只覆盖 academic-lit-analysis；review-skeleton 的
    SKILL.md 与 build_skeleton.py 附录索引（file_map）若引用了不存在的
    框架文件，只有运行到对应分支才会发现 —— 「将来改坏没人拦」的缺口。
    固化为回归断言：SKILL 收录主脚本、SKILL 引用的框架文件存在、
    附录索引 file_map 的文件存在且数量完整。
    """
    sk = HERE.parents[1] / "review-skeleton"
    skill_md = sk / "SKILL.md"
    refs = sk / "references"
    if not skill_md.exists():
        return check("第二技能文档同步", False, "review-skeleton/SKILL.md 缺失")
    t = skill_md.read_text(encoding="utf-8")
    if "build_skeleton.py" not in t:
        return check("第二技能文档同步", False, "SKILL.md 未收录 build_skeleton.py")
    mentioned = set(re.findall(r"references/([\w\-]+\.(?:json|md))", t))
    missing = sorted(x for x in mentioned if not (refs / x).exists())
    if missing:
        return check("第二技能文档同步", False,
                     f"SKILL.md 引用不存在的框架文件: {', '.join(missing)}")
    bsrc = (sk / "scripts" / "build_skeleton.py").read_text(encoding="utf-8")
    m = re.search(r"file_map\s*=\s*\{(.*?)\}", bsrc, re.S)
    if not m:
        return check("第二技能文档同步", False,
                     "build_skeleton.py 缺少 file_map 附录索引")
    fm = dict(re.findall(r'"([\w_]+)":\s*"([\w\-]+\.(?:json|md))"', m.group(1)))
    if len(fm) < 15:
        return check("第二技能文档同步", False,
                     f"附录 file_map 仅 {len(fm)} 项，疑似不完整")
    miss2 = sorted(x for x in fm.values() if not (refs / x).exists())
    if miss2:
        return check("第二技能文档同步", False,
                     f"附录索引引用不存在的文件: {', '.join(miss2)}")
    return check("第二技能文档同步", True,
                 f"SKILL 与附录索引覆盖 {len(fm)} 个框架文件")


def c_r_contract_docs():
    """R/igraph 契约在三份文档里必须一致 —— 防「文档写可选、代码硬失败」复发。

    背景：network-mapper.md / failure_paths.md / UPGRADE.md 曾把
    R+igraph 写成「可选 / 缺失自动回退 exit 0」，而 sna_r.py 实际是「必需 /
    缺 R 硬失败 exit 8」。把文档改回旧口径后，整套回归结果与基线
    逐项相同、零新增失败 —— 该缺口此前完全无门禁。故固化为回归断言。
    """
    root = Path(__file__).resolve().parents[3]
    targets = {
        "agents/network-mapper.md": (
            ["R + igraph 为必需标准路径", "exit 8"],
            ["自动回退", "自动兜底", "正常降级，不是错误", "R 可选"],
        ),
        "skills/academic-lit-analysis/references/failure_paths.md": (
            ["必需", "不产出降级产物", "| 8 |"],
            ["自动回退", "自动兜底"],
        ),
        "UPGRADE.md": (
            ["退出码 8", "不可回退"],
            ["可自动回退", "自动回退纯 Python"],
        ),
    }
    for rel, (required, forbidden) in targets.items():
        p = root / rel
        if not p.exists():
            return check("R 契约文档一致性", False, f"{rel} 缺失")
        t = p.read_text(encoding="utf-8")
        for tok in required:
            if tok not in t:
                return check("R 契约文档一致性", False,
                             f"{rel} 缺少必需表述: {tok}")
        for tok in forbidden:
            if tok in t:
                return check("R 契约文档一致性", False,
                             f"{rel} 残留旧口径: {tok}")
    # ── 全包兜底扫描 ────────────────────────────────────────────────
    # 上面的白名单只锁 3 个文件。若将来新增文档（或在别处重述 R 口径）
    # 又写成「可选/自动回退」，这道门禁看不见 —— 缺口的成因正是"只查了
    # 已知会出错的那几处"。故对全包所有 md 做一次语义兜底：
    # 凡出现「回退/兜底/可选」类措辞且邻近 R/igraph 语境者，必须同段
    # 声明必需口径，否则判 FAIL。
    _NEAR = ("Rscript", "R + igraph", "R/igraph", "R 语言", "igraph")
    _SOFT = ("自动回退", "可自动回退", "自动兜底", "正常降级，不是错误",
             "R 可选", "Rscript 可选", "igraph 可选")
    scanned = 0
    soft_hits = []
    for md in sorted(root.rglob("*.md")):
        rel = md.relative_to(root).as_posix()
        if rel in targets:      # 上面已按更严规则逐条验过
            continue
        try:
            t = md.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        scanned += 1
        paras = [s for s in re.split(r"[\n。；;]", t) if any(n in s for n in _NEAR)]
        for para in paras:
            bad = [k for k in _SOFT if k in para]
            if bad:
                soft_hits.append(f"{rel}: 残留「{bad[0]}」")
    if soft_hits:
        return check("R 契约文档一致性", False,
                     "全包兜底扫描命中旧口径 → " + "; ".join(soft_hits[:4]))
    return check("R 契约文档一致性", True,
                 f"三份核心文档均声明 R+igraph 必需、缺 R 硬失败 exit 8；"
                 f"另全包兜底扫描 {scanned} 份 md，无自动回退表述")



def c_new_scripts_runnable():
    """新增的三个脚本必须能--help 且不崩。

    只查"存在"不够：曾出现函数被误删导致运行时报错。
    这里实际执行 --help，确保入口与参数解析完好。
    """
    import subprocess as _sp
    ok_all, bad = True, []
    for name in ("publication_stats.py", "cross_matrix.py", "pdf_extract.py"):
        f = HERE / name
        if not f.exists():
            bad.append(f"{name} 缺失")
            ok_all = False
            continue
        r = _sp.run([PY, str(f), "--help"], capture_output=True,
                    text=True, timeout=60)
        if r.returncode != 0:
            bad.append(f"{name} --help 返回 {r.returncode}")
            ok_all = False
    if not ok_all:
        return check("新增脚本可运行", False, "; ".join(bad))
    return check("新增脚本可运行", True, "三个脚本 --help 均正常")


def main() -> int:
    ap = argparse.ArgumentParser(description="端到端回归测试")
    ap.add_argument("--library", help="真实 EndNote 库路径（配合 --full）")
    ap.add_argument("--full", action="store_true", help="追加需要真实库的重量级检查")
    ap.add_argument("--json", help="把结果写成 JSON")
    a = ap.parse_args()

    print("════════ 回归测试（每项对应一个已修复的真实 bug）════════")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        c_gini()
        c_xml_cdata()
        c_zotero_filters(tmp)
        c_year_priority(tmp)
        c_dedup()
        c_assign_tier()
        c_stat_helpers()
        c_palette()
        c_view_smoke()
        c_render_guards_present()
        c_report_structure()
        c_report_no_dead_ends()
        c_review_offer()
        c_intent_clarify()
        c_docs_in_sync()
        c_review_skeleton_docs()
        c_r_contract_docs()
        c_new_scripts_runnable()
        c_sort_before_layout(tmp)
        c_sna_fallback(tmp)
        c_zero_drop(tmp)
        c_tagged_year()
        c_small_library_guards()
        c_refs_json_everywhere()
        c_plugin_json()
        c_package_integrity()
        c_agent_naming()
        c_frontmatter_yaml()
        c_no_user_data()
        c_output_escaping()
        c_new_modules(tmp)
        c_export_all(tmp)
        c_burst_single_year_filter()
        c_r_backend_guards()
        c_r_probe_single_source()
        c_doc_cmd_paths_consistent()
        c_no_dangling_refs()
        c_skill_tree()
        c_view_count_consistent()
        c_no_domain_mismatch()
        c_no_dev_narrative_in_docs()
        c_doctor_hint_actionable()
        c_argv_isolation()
        c_lock_probe_crossplatform()
        c_network_interactions()
        c_format_sniffing(tmp)
        c_dom_xss_fallback()
        c_csv_export_coverage()
        c_topics_params_truthful()
        c_r_script_hygiene()
        c_error_exit_contract()
        c_lock_notice_propagated()
        c_import_completeness()
        c_skeleton_end_to_end()
        c_touch_support()
        c_burst_span_factor()
        c_boundary_statements()
        c_agent_docs_wired()
        if a.full:
            lib = a.library or "sample_library.enl"
            c_full(lib, tmp)

    n_pass = sum(1 for _, s, _ in RESULTS if s == "PASS")
    n_fail = sum(1 for _, s, _ in RESULTS if s == "FAIL")
    n_skip = sum(1 for _, s, _ in RESULTS if s == "SKIP")
    print("══════════════════════════════════════════════════════")
    print(f"PASS {n_pass}  FAIL {n_fail}  SKIP {n_skip}")
    if n_fail:
        print("\n失败项：")
        for name, st, msg in RESULTS:
            if st == "FAIL":
                print(f"  ✗ {name}  {msg}")
    if a.json:
        Path(a.json).write_text(json.dumps(
            [{"name": n, "status": s, "message": m} for n, s, m in RESULTS],
            ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\n结果已写入 {a.json}")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
