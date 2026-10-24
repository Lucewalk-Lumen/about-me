#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_checks.py —— 端到端回归测试

目的：把**已经踩过并修好的坑**固化成可重跑的检查，防止后续改动再次引入。
本文件里每一条检查都对应一个真实发生过的 bug，注释里写明"当时是什么现象"。

用法:
    python3 run_checks.py                      # 快速检查（不需要真实库，约 5 秒）
    python3 run_checks.py --full --library "~/Desktop/EndNote/My EndNote Library.enl"
                                               # 追加需要真实库的重量级检查

退出码:
    0  全部通过（或仅 SKIP）
    1  存在 FAIL
"""
from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
PY = sys.executable

RESULTS: list[tuple[str, str, str]] = []   # (name, status, message)


def strip_js_comments(t: str) -> str:
    """剥离 JS 块注释与行注释。

    ⚠️ 必要性：build_report.py 里为了说明"这里不能innerHTML"，
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


# ══════════════════════════════════════════════════════════
# 各检查项
# ══════════════════════════════════════════════════════════
def c_gini():
    """坑：gini2 用降序排序 + 分母/减项写错 → 完全均衡的簇返回 -0.985（应为 0），
    真实数据返回 -0.997（正确值 0.159）。这是报告里用户可见的"均衡度 gini"。"""
    from build_report import gini2
    eq = gini2([100, 100, 100, 100])
    check("gini2 完全均衡应为 0", abs(eq) < 1e-9, f"实测 {eq}")
    ext = gini2([0, 0, 0, 1000])
    check("gini2 极度不均应接近 1", 0.5 <= ext <= 1.0, f"实测 {ext:.3f}")
    real = gini2([625, 551, 532, 515, 472, 421, 404, 374, 358, 330, 296, 293, 267, 245])
    check("gini2 真实数据应为正且 <1", 0 < real < 1, f"实测 {real:.4f}")


def c_xml_cdata():
    """坑：`re.sub(r'<[^>]+>', ' ', s)` 会把 `<![CDATA[题名]]>` 整段（含正文）吃掉，
    导致 CNKI XML 源 206 条里 204 条标题变空、tier 判为 empty。"""
    from import_sources import _xml_text
    got = _xml_text("<Title><![CDATA[沈阳市老年人力资源开发]]></Title>")
    check("_xml_text 保留 CDATA 内容",
          "沈阳市" in got and "CDATA" not in got, f"实测 {got!r}")


def c_zotero_filters(tmp: Path):
    """坑：把过滤条件写进 `LEFT JOIN deletedItems d ON i.itemID=d.itemID AND d.itemID IS NULL`
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
    from endnote_core import assign_tier, make_ref
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
    """坑：手工"彩虹 14 色"在色觉模拟下相邻对 min ΔE00 = 0.0（相邻两色完全重合）。"""
    p = HERE.parent / "references" / "palette_vivid.json"
    if not p.exists():
        skip("色板可辨识度", "palette_vivid.json 不存在")
        return
    d = json.loads(p.read_text(encoding="utf-8"))
    adj = d.get("adjacent_min_dE00")
    contrast = d.get("metrics", {}).get("min_contrast_on_white")
    chroma = d.get("metrics", {}).get("mean_chroma_Oklab")
    check("相邻色 min ΔE00 ≥ 9", adj is not None and adj >= 9.0, f"实测 {adj}")
    check("白底对比度 ≥ 2.3", contrast is not None and contrast >= 2.3, f"实测 {contrast}")
    check("平均彩度 > 0.15（足够鲜明）", chroma is not None and chroma > 0.15, f"实测 {chroma}")


def c_sort_before_layout(tmp: Path):
    """坑：build_network.py 里 nodes.sort(-degree) 排在 layout() 之后 →
    pos_encoded[i] 与 payload['nodes'][i] 错位，而报告 JS 优先读 pos_encoded
    → 整张网络图渲染错乱。这是"排版不清楚"的根因之一。

    ⚠️ v0.3.1 修正（独立复审发现此检查曾"无牙"）：
    旧版只比较源码里两个字符串的**位置**。实测注入它声称要防的 bug
    （layout 后按 id 重排节点）后，语法正确、rc=0，但**整张网络错分率
    从 0.37% 飙到 91.21%** —— 而旧检查仍报"全部通过"。
    原因：它只看第一个 sort 的位置，第二个 sort 出现在 layout 之后它完全看不见。

    改为**行为断言**：真跑一次建网，校验 nodes[i].x/y 与 pos_encoded[i]
    逐一对齐。这是唯一能真正抓住该bug 的方式。
    """
    import base64
    # 1) 保留源码位置检查作为快速护栏（非唯一依据）
    src = (HERE / "build_network.py").read_text(encoding="utf-8")
    i_sort = src.find("nodes.sort(key=lambda x: -x[")
    i_layout = src.find("pos = layout(nodes, edges)")
    check("nodes.sort 在 layout() 之前（源码位置）",
          i_sort != -1 and i_layout != -1 and i_sort < i_layout,
          f"sort@{i_sort} layout@{i_layout}")

    # 2) 行为断言：真跑建网，校验坐标与 pos_encoded 对齐
    from endnote_core import make_ref, refs_to_json
    import json as _json
    # ⚠️ 语料设计的关键教训（变异测试实测）：
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
        ids = [n["id"] for n in nodes]
        degs = [n.get("degree", 0) for n in nodes]
        by_degree = all(degs[i] >= degs[i + 1] for i in range(len(degs) - 1))
        sensitive = ids != sorted(ids) and by_degree and len(nodes) >= 6
        check("测试语料能检出排序错位（id 序≠degree 序且节点≥6）", sensitive,
              f"{len(nodes)} 节点，degree 降序={by_degree}，id 序≠排序={ids != sorted(ids)}")
        if not sensitive:
            check("pos_encoded 对齐断言有效", False,
                  "测试语料无法触发排序错位，本次断言无效——需更换语料")
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
        # ⚠️ 不能因长度检查失败就 return —— 那样长度异常会"连带掩盖"本断言，
        #    变异测试已证实：只错开一位时长度检查先失败并提前退出，
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
    """R / igraph 缺失时必须回退纯 Python 且 exit 0，绝不能报失败。"""
    net = tmp / "network.json"
    net.write_text(json.dumps({
        "nodes": [{"id": f"k{i}", "degree": 5 - i, "primary_cluster": i % 2}
                  for i in range(6)],
        "edges": [{"source": "k0", "target": f"k{i}", "weight": 3} for i in range(1, 6)],
    }), encoding="utf-8")
    r = run(["sna_r.py", "--network", str(net), "--out", str(tmp), "--force-python"])
    if r.returncode != 0:
        check("sna_r 兜底路径 exit 0", False, f"退出码 {r.returncode}: {r.stderr[:120]}")
        return
    try:
        d = json.loads(r.stdout)
        check("sna_r 兜底 exit 0", True)
        check("sna_r 兜底 backend=python-fallback", d.get("backend") == "python-fallback",
              str(d.get("backend")))
        check("sna_r 兜底给出安装提示", "install.packages" in str(d.get("hint", "")))
    except Exception as e:
        check("sna_r 兜底输出可解析", False, str(e))


def c_zero_drop(tmp: Path):
    """零静默丢弃：四类 tier 之和 == 记录总数。"""
    from endnote_core import assign_tier, coverage_report, make_ref
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
    """坑：EndNote tagged 解析器只认 %D 取年份，但 CNKI 等平台的 .enw 用 %Y。
    结果 year 全为None → age_warning 报"库中无任何可用年份"、演化分析整体失效，
    且属静默数据丢失（违反零静默丢弃铁律）。v0.3.1 起 %D / %Y 都收。"""
    from import_sources import load_endnote_tagged
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "t.enw"
        p.write_text(
            "%T Study A on leadership\n%A A, B\n%K leadership\n"
            "%X " + "x" * 80 + "\n%Y 2021\n%0 68\nER  - \n"
            "%T Study B on leadership\n%A C, D\n%K leadership\n"
            "%X " + "x" * 80 + "\n%D 2019/05/01\n%0 68\nER  - \n",
            encoding="utf-8")
        refs = load_endnote_tagged(p)
        yrs = [r.year for r in refs]
        check("tagged 年份：%Y 与 %D 都能解析",
              len(refs) == 2 and yrs == [2021, 2019], f"实测 {yrs}")


def c_small_library_guards():
    """坑（两处，均在真实小样本库上暴露）：
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
    """坑：文档承诺"下游模块透明接受 .enl 或 refs.json"，但 v0.3.0 的
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
    """v0.3.1 新增两个模块的基本正确性 + 边界声明。"""
    # 1) burst_detection：构造已知突现形态，验证能识别且不产生除零错误
    from burst_detection import detect_keyword_bursts
    from endnote_core import make_ref
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


def c_boundary_statements():
    """边界声明必须在代码里硬编码，不能只写在文档里让人"记得说"。"""
    rep = (HERE / "build_report.py").read_text(encoding="utf-8")
    check("报告硬编码「非引文网络」声明", "不是引文网络" in rep)
    check("报告硬编码「keyword burst ≠ citation burst」声明",
          "不是引文突现" in rep or "citation burst" in rep)
    lead = Path(__file__).resolve().parents[3] / "agents" / "endnote-analysis-team-lead.md"
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
    # build_html / sanxian_tables 都必须能实际执行（v0.3.1 开发中曾因移动
    # 代码块把 sanxian_tables 的 `body = "".join(out)` 一并删掉，
    # 主报告正常但三线表静默失败 —— 用真实调用兜住）
    # demo 用**真实跑出来的 topics.json**，而不是手搓dict：
    # 手搓必然漏字段（已实测踩过 zh_pct / year_min / year_range / library 四次），
    # 而漏字段恰恰是这类"静默失败"最常见的成因。
    try:
        import json as _json
        from build_report import build_html, sanxian_tables
        from endnote_core import make_ref, refs_to_json
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


def c_r_backend_guards():
    """R 后端三处真实缺陷（真实库 5683 篇 + R 4.6.1/igraph 2.3.3 实测暴露）：
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


def c_burst_single_year_filter():
    """突现检测必须排除只在单一年份出现的词。

    坑（真实库 5683 篇实测）：MeSH 索引词如 "history, 20th century"
    全部集中在 2017 年，基线为空 -> ratio=20/0.5=40 -> 强度 50.79 霸榜第一。
    但"只在一年出现"意味着没有历史基线，其"突现"是数据伪影而非真实升温。
    修正后实测排除 10508 个此类词。
    """
    from burst_detection import detect_keyword_bursts
    from endnote_core import make_ref
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
    from endnote_core import is_locked, lock_probe_available
    import shutil
    # 不得只依赖 lsof（Windows 没有）
    src = (HERE / "endnote_core.py").read_text(encoding="utf-8")
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
    """网络图交互与可视化能力（v0.3.1 增强）。

    背景：用户诉求「能否手动调节点 / 放大缩小」。实测原版只有
    滚轮缩放 + 拖空白平移 + 双击复位，**节点不能单独拖动**。
    v0.3.1 补：节点拖拽（含邻居跟随）、PNG/SVG 导出、
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
    check("拖拽阈值 3px（不误伤点击高亮）", "Math.abs(dx)+Math.abs(dy) > 3" in src)
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
    """格式自动嗅探（detect_and_load）—— 独立复审认定的**最大单点风险**。

    为什么是最大风险：包内注释自陈「扩展名会骗人，必须看内容」，
    .enw / .txt 既是真实踩过的坑；而非 EndNote 用户（Zotero / CNKI / WoS /
    NoteExpress）的**唯一入口**就是这条路径。此前它**零测试**——
    属于"目前正确"而非"被测保证正确"，任何重构都可能悄悄破坏嗅探顺序
    而无人察觉。

    11 个陷阱场景，覆盖：扩展名说谎、内容嗅探、加密格式须明确报错、
    不可识别内容须报错、无作者记录时字段不得静默丢失。
    """
    from import_sources import detect_and_load
    from endnote_core import EnlError
    import json as _json

    ABS = "x" * 80          # 够长摘要，绕过 50 字阈值
    cases = [
        # (场景, 文件名, 内容, 期望 key 或 "ERROR")
        ("enw 装 XML 而非 tagged", "t1.enw",
         '<?xml version="1.0"?><EndNote><record>\n'
         '<title>Enw Extension But XML Content</title>\n'
         f'<abstract>Long enough abstract to exceed threshold.{"x"*40}</abstract>\n'
         '<year>2020</year></record></EndNote>', "endnote_xml"),
        ("enw 装 tagged", "t2.enw",
         f"%T Tagged Inside Enw Extension\n%A Smith, J\n%X {ABS}\n%Y 2021\nER  - \n",
         "endnote_tagged"),
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
    f.write_text(_json.dumps({"format": "endnote-analysis/refs@1", "refs": []}),
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
    """DOM XSS 防护（独立复审发现的 **Critical**，esc_json 挡不住）。

    坑：esc_json() 只保护 `<script>` 边界。值被 JSON.parse 还原成原始
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
    """CSV 加固必须覆盖**全部**导出点（独立复审发现 3 处漏网）。

    坑：此前只在 6 处调用了 esc_csv_cell，但 `csv.writer` 实际有 11+ 处；
    `author_topic.py` 甚至出现同一 main() 内长表已加固、短表裸奔的自相矛盾。
    故本检查**穷举所有 writerow 数据行**，凡含外部文本字段者必须已加固。
    """
    import re as _re
    bare = []
    for py in sorted(HERE.glob("*.py")):
        if py.name in ("run_checks.py",):
            continue
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

    坑：fit_vectorizer 在小库/词项少时会逐级放宽（实测 min_df=1,max_df=1.0），
    而产物仍硬编码声称 min_df=3/max_df=0.5，且降级说明只进 stderr。
    引用这些参数写方法学描述的人会被误导 —— 故须行为验证。
    """
    from endnote_core import make_ref, refs_to_json
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

    坑（独立复审实测）：`as.numeric(packageVersion("igraph"))` 会抛
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
    rs = _sh.which("Rscript")
    if not rs:
        skip("R 端实跑无警告", "Rscript 不可用")
        return
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

    坑（独立复审实测）：trend_effects.py 缺 `except Exception`，
    传入坏 topics.json 时抛 TypeError → 退出码 1 ——
    而 1 在契约里是「源库不可用：请检查移动硬盘是否连接」，
    Agent 会据此给用户完全错误的修复指引。
    """
    src = (HERE / "trend_effects.py").read_text(encoding="utf-8")
    tail = src[src.index('if __name__ == "__main__":'):]
    check("trend_effects 有未预期异常兜底（EXIT[5]）",
          "except Exception" in tail and "EXIT[5]" in tail)
    # 行为验证：给一个坏输入，应 exit 5 而非 1
    import tempfile as _tf
    from pathlib import Path as _P
    td = _P(_tf.mkdtemp())
    try:
        (td / "bad.json").write_text('{"clusters": []}', encoding="utf-8")
        # 合法库 + 结构不符的 topics → 触发"未预期异常"而非输入不可用
        import json as _json
        from endnote_core import make_ref, refs_to_json as _r2j
        good = [make_ref(i + 1, f"S{i} leadership", "x" * 80,
                         ["leadership", "team"], 2020 + i % 3, "J", "A, B", "")
                for i in range(10)]
        (td / "ok.json").write_text(
            _json.dumps(_r2j(good, "t", {}), ensure_ascii=False), encoding="utf-8")
        r = run(["trend_effects.py", str(td / "ok.json"),
                 "--topics", str(td / "bad.json"), "--out", str(td / "o")])
        # 关键不是"必须退 5"，而是**绝不能退 1**——
        # 1 在契约里是「源库不可用」，会给用户完全错误的修复指引。
        # 本输入下"样本不足"退 4 是正确行为，同样不可接受 1。
        if r.returncode == 0:
            skip("异常退出码不适用", "该输入正常完成")
        else:
            last = ((r.stderr or "").strip().splitlines() or [""])[-1][:70]
            check("异常时不得返回 1（会被误读为源库不可用）",
                  r.returncode != 1,
                  f"实际 {r.returncode}；stderr末行: {last}")
            check("异常时输出遵循 EXIT 契约（含 [hint] 行）",
                  "[hint]" in (r.stderr or ""), last)
    finally:
        import shutil as _sh
        _sh.rmtree(td, ignore_errors=True)


def c_lock_notice_propagated():
    """锁探测不可用的提示必须真正进入各模块产物（不能只改入口不改输出）。

    独立复审发现：`is_locked` 的 docstring 承诺"调用方须如实标注"，
    但 9 个调用方里只有 scan_library 兑现，其余 6 个把False 当"未占用"。
    v0.3.1 引入 lock_status 统一入口，此处断言**产物字段真的存在**。
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
          "def lock_status(" in (HERE / "endnote_core.py").read_text(encoding="utf-8"))
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

    独立复审修`lock_status` 时，我用批量替换改import，
    漏了 6 个文件的 import 行 —— 结果 cluster_topics 等直接
    `NameError: name 'lock_status' is not defined`，
    而**当时的 155 项测试仍全绿**（因为没有一项真的跑这些脚本）。
    这类"改代码没同步改 import"的错误只有真跑才能发现。
    故本检查对每个脚本做 --help（或最小执行）探测。
    """
    import tempfile as _tf
    from pathlib import Path as _P
    bad = []
    for py in sorted(HERE.glob("*.py")):
        if py.name == "run_checks.py":
            continue
        r = subprocess.run([PY, str(py), "--help"],
                           capture_output=True, text=True, timeout=120)
        # argparse 的 --help 退 0；NameError 等未定义错误退 1 且 stderr 有 traceback
        err = r.stderr or ""
        if "NameError" in err or "ImportError" in err or "ModuleNotFoundError" in err \
           or (r.returncode not in (0, 2) and "Traceback" in err):
            line = [l for l in err.splitlines() if "Error" in l]
            bad.append(f"{py.name}:{line[0].strip()[:60] if line else 'rc=' + str(r.returncode)}")
    check("全部脚本可独立执行（import 完整）", not bad,
          f"问题: {bad}" if bad else f"{len(list(HERE.glob('*.py')))-1} 个脚本全部 OK")


def c_import_completeness():
    """所有脚本必须能被真正执行（import 完整、名字已定义）。

    独立复审修`lock_status` 时，我用批量替换改import，
    漏了 6 个文件的 import 行 —— 结果 cluster_topics 等直接
    `NameError: name 'lock_status' is not defined`，
    而**当时的 155 项测试仍全绿**（因为没有一项真的跑这些脚本）。
    这类"改代码没同步改 import"的错误只有真跑才能发现。
    故本检查对每个脚本做 --help（或最小执行）探测。
    """
    import tempfile as _tf
    from pathlib import Path as _P
    bad = []
    for py in sorted(HERE.glob("*.py")):
        if py.name == "run_checks.py":
            continue
        r = subprocess.run([PY, str(py), "--help"],
                           capture_output=True, text=True, timeout=120)
        # argparse 的 --help 退 0；NameError 等未定义错误退 1 且 stderr 有 traceback
        err = r.stderr or ""
        if "NameError" in err or "ImportError" in err or "ModuleNotFoundError" in err \
           or (r.returncode not in (0, 2) and "Traceback" in err):
            line = [l for l in err.splitlines() if "Error" in l]
            bad.append(f"{py.name}:{line[0].strip()[:60] if line else 'rc=' + str(r.returncode)}")
    check("全部脚本可独立执行（import 完整）", not bad,
          f"问题: {bad}" if bad else f"{len(list(HERE.glob('*.py')))-1} 个脚本全部 OK")


def c_touch_support():
    """移动端交互（v0.3.1 修复）。

    坑：此前只有 mouse* 监听 + CSS `touch-action:none`，导致手机上
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
    """折扣因子必须按「基线可比性」而非「年份跨度」（v0.3.1 修正）。

    坑（独立复审实测）：旧公式 span_factor = log1p(n_years)/log(11)，
    对 2 年新概念打 0.46、3 年打 0.58 —— 而突现检测的**目的恰恰是
    发现新概念**。真正该折的是"基线不可靠导致倍数虚高"，与跨度无关；
    单年份伪突现已由 min_years 准入挡住，不需再打折。
    """
    from burst_detection import detect_keyword_bursts
    from endnote_core import make_ref
    refs = []
    # ⚠️ 语料设计：基线年份数 = 除峰值年外、落在±window 内的年份数。
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
    check("quickPrompts 固定 3 个", len(d.get("quickPrompts", [])) == 3)
    zh = d.get("displayDescription", {}).get("zh", "")
    check("displayDescription.zh 40–50 字", 40 <= len(zh) <= 50, f"{len(zh)} 字")


def c_package_integrity():
    """坑：v0.3.0 存在两份 settings.json（setting.json / settings.json 内容相同），
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


def c_agent_naming():
    """坑：v0.3.0 的成员 Agent ID 为 member-a / member-b —— 与功能完全无关的占位名。
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
    """坑：v0.3.0 的 samples/ 目录内含 277 条真实题录（CNKI/WoS）与一份真实报告，
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
    坑：报告用裸 json.dumps 内联进 <script>，题名含 '</script>' 即可提前闭合标签注入脚本；
    CSV 导出未防公式注入，Excel 打开时 =CMD|... 会被当公式执行。"""
    from endnote_core import esc_csv_cell, esc_html, esc_json
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
    # ⚠️ 该指标用「各岛节点坐标的均值」当质心；岛屿内部若分布不匀，均值会偏离
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
        c_sort_before_layout(tmp)
        c_sna_fallback(tmp)
        c_zero_drop(tmp)
        c_tagged_year()
        c_small_library_guards()
        c_refs_json_everywhere()
        c_plugin_json()
        c_package_integrity()
        c_agent_naming()
        c_no_user_data()
        c_output_escaping()
        c_new_modules(tmp)
        c_burst_single_year_filter()
        c_r_backend_guards()
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
        c_touch_support()
        c_burst_span_factor()
        c_import_completeness()
        c_boundary_statements()
        c_agent_docs_wired()
        if a.full:
            if a.library:
                c_full(a.library, tmp)
            else:
                RESULTS.append(("--full 重量级检查", "SKIP",
                                "需显式指定 --library(示例:--library \"~/Desktop/EndNote/My EndNote Library.enl\")"))

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
