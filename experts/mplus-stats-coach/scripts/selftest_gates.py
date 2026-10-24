#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
selftest_gates.py — 包级门禁绿红双证自检（G003）

为什么需要它
    「门禁全绿」本身**不是**有效性证明 —— 一个恒返回 OK 的摆设也全绿。
    本脚本对 `scripts/verify.py` 的**真实实现**做双向对照：
      · 绿证（不冤枉好人）：合规包须全过；合法写法（块标量 description）不得误判
      · 红证（真会报警）：注入已知缺陷后，**对应那一行**必须变 FAIL
    红证只断言**目标门禁编号**翻转，其余维度状态不参与判定（局部化证明）。

覆盖范围
    A7  头像可达 + 体积区间（占位实色图须判红）
    A9  非官方枚举目录（knowledge/）须自带口径声明，且该声明不得被删
    C10 P0 红线 ID 全量落地（红线表不得有洞）
    D6  版本单一真源：SKILL.md 版本不得与 plugin.json 漂移
    D7  警告四口径可复算（62 类键 / 39 种消息 / 219 条 / 90 份 .out）
    F1  主 Agent frontmatter 必填 4 项齐全
    F2  主 Agent 与 plugin.json 交叉一致（name / displayName / profession / skills）
    F3  每个 SKILL.md 必填 5 项齐全
    F4  字段体系不混用 + 主 Agent 无官方禁止的 tools 键

用法
    python3 scripts/selftest_gates.py
退出码
    0 = 全部绿红双证通过；1 = 有断言失败（打印失败项）
"""
import io
import json
import os
import shutil
import struct
import sys
import tempfile
import zlib

sys.dont_write_bytecode = True          # 不生成 __pycache__（E1 卫生门禁）

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import verify  # noqa: E402
import make_avatars  # noqa: E402
import render_selection_svg as rss  # noqa: E402

FAILS = []


def note(ok, label, detail=""):
    print("[%s] %s%s" % ("OK" if ok else "FAIL", label, (" -- " + detail) if detail else ""))
    if not ok:
        FAILS.append(label)
    return ok


def w(path, s, nl="\n"):
    with io.open(path, "w", encoding="utf-8", newline=nl) as f:
        f.write(s)


def png_noise(path, side=32):
    """写一张 side×side 伪随机 PNG。

    ⚠ 夹具口径（实测踩过）：512×512 全随机 → 压缩率极低、约 1MB，**会超 A7 的 512000 上限**，
      故这里只用来造「占位小图」（远小于 10240 下界）；合规头像一律调 make_avatars 真实生成器，
      顺带证明生成器本身产出的是合规头像。
    """
    raw = bytearray()
    s = 20261007
    for _ in range(side):
        raw.append(0)
        for _ in range(side):
            s = (1103515245 * s + 12345) & 0x7FFFFFFF
            raw += bytes(((s >> 16) & 0xFF, (s >> 8) & 0xFF, s & 0xFF, 255))

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n"
                + chunk(b"IHDR", struct.pack(">IIBBBBB", side, side, 8, 6, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(bytes(raw), 6))
                + chunk(b"IEND", b""))


def real_avatar(path):
    """调真实生成器产一张合规头像。"""
    make_avatars.build().write_png(path)


DD_ZH = "用于门禁自检的示例智能体，仅验证结构字段与交叉一致性，不承担任何实际业务功能，供打包前回归使用。"
AGENT_MD_GOOD = """---
name: demo-agent
description: Demo agent used only by the gate dual-proof self-test.
displayName:
  en: "Demo"
  zh: "阿测"
profession:
  en: "Demo Agent"
  zh: "示例智能体"
maxTurns: 50
skills:
  - demo-skill
---

# 示例智能体

门禁自检用夹具，不承担任何实际职责。

红线编号（C10 要求全量落地）：P0-0a P0-0b P0-0c P0-0d P0-1 P0-2 P0-3 P0-4 P0-5 P0-6
"""
SKILL_MD_GOOD = """---
name: demo-skill
description: Demo skill used only by the gate dual-proof self-test.
description_zh: 门禁自检用示例技能。
description_en: Demo skill used only by the gate dual-proof self-test.
version: "0.1.0"
author: selftest
---

# 示例技能

门禁自检用夹具。
"""


def build_pkg(root):
    """构造一个**合规**的最小 agent 型包（用于绿证）。"""
    os.makedirs(os.path.join(root, ".codebuddy-plugin"))
    os.makedirs(os.path.join(root, "agents"))
    os.makedirs(os.path.join(root, "avatars"))
    os.makedirs(os.path.join(root, "skills", "demo-skill"))
    os.makedirs(os.path.join(root, "skills", "mplus-syntax-lab", "scripts"))
    os.makedirs(os.path.join(root, "knowledge", "official"))
    os.makedirs(os.path.join(root, "knowledge", "facts"))

    meta = {
        "name": "demo-pkg", "plugin": "demo-pkg", "expertType": "agent",
        "version": "0.1.0", "description": "Dual-proof fixture package.",
        "author": {"name": "selftest", "email": "selftest@example.com"},
        "agents": ["./agents/demo-agent.md"], "agentName": "demo-agent",
        "skills": ["./skills/demo-skill"],
        "displayName": {"zh": "阿测", "en": "Demo"},
        "profession": {"zh": "示例智能体", "en": "Demo Agent"},
        "displayDescription": {"zh": DD_ZH, "en": "Dual-proof fixture agent."},
        "avatar": "avatars/demo.png", "categoryId": "15-Education",
        "defaultInitPrompt": {"zh": "问题一", "en": "Q1"},
        "tags": [{"zh": "标签一", "en": "t1"}, {"zh": "标签二", "en": "t2"},
                 {"zh": "标签三", "en": "t3"}],
        "quickPrompts": [{"zh": "问题一", "en": "Q1"}, {"zh": "问题二", "en": "Q2"},
                         {"zh": "问题三", "en": "Q3"}],
        "license": "MIT", "keywords": ["demo"],
    }
    w(os.path.join(root, ".codebuddy-plugin", "plugin.json"),
      json.dumps(meta, ensure_ascii=False, indent=2))
    w(os.path.join(root, "settings.json"), json.dumps({"agent": "demo-agent"}))
    w(os.path.join(root, "README.md"), "# 说明\n\n门禁自检夹具。\n")
    w(os.path.join(root, "CHANGELOG.md"), "# 更新日志\n\n## 0.1.0\n\n夹具。\n")
    w(os.path.join(root, "agents", "demo-agent.md"), AGENT_MD_GOOD)
    w(os.path.join(root, "skills", "demo-skill", "SKILL.md"), SKILL_MD_GOOD)
    # C5 需要该路径下的文件含指定声明文案
    w(os.path.join(root, "skills", "mplus-syntax-lab", "scripts", "check_inp.py"),
      "# 夹具：本检查仅覆盖语法层。\n")
    real_avatar(os.path.join(root, "avatars", "demo.png"))
    # D4 / D5：索引 ↔ 语料 ↔ 事实 三层同源（各 1 条）
    w(os.path.join(root, "knowledge", "official", "ex1.inp"), "TITLE: fixture;\n")
    w(os.path.join(root, "knowledge", "cases.jsonl"), json.dumps({
        "id": "demo-ex1", "inp_path": "knowledge/official/ex1.inp",
        "facts_id": "demo-ex1", "source_url": "https://example.com/ex1.inp",
    }, ensure_ascii=False) + "\n")
    w(os.path.join(root, "knowledge", "facts", "case-facts.jsonl"),
      json.dumps({"id": "demo-ex1"}, ensure_ascii=False) + "\n")
    # A9：非官方枚举目录须自带口径声明（D5）
    w(os.path.join(root, "knowledge", "INDEX.md"),
      "# 知识库入口\n\n## 零、目录约定\n\n`knowledge/` 不在官方基础结构枚举内，属**非官方**目录。\n")
    # D7：警告四口径（62 类键 / 39 种消息 / 219 条 / 90 份 .out）须可复算
    w(os.path.join(root, "knowledge", "facts", "warning-library.jsonl"), warn_lib_fixture())
    return meta


def warn_lib_fixture():
    """造 62 条警告类键，使 R1/R2/R3 归并后恰为 39 种消息、219 条、90 份 .out。

    归并算式：62 −(13−1)−(10−1)−(3−1) = 39。
    条数：第 1 行 n=158，其余 61 行 n=1 → 158+61 = 219。
    文件并集：前 28 行各带 2 个不同 case，其余各 1 个 → 62+28 = 90。
    """
    r1 = "INPUT LINE EXCEEDED 90 CHARACTERS"
    r2 = "ALL CONTINUOUS LATENT VARIABLE COVARIANCES INVOLVING"
    r3 = "THE LATENT VARIABLE COVARIANCE MATRIX (PSI) IN GROUP"
    lines = []
    for i in range(1, 63):
        if i <= 13:
            cls = r1 + " %d" % i
        elif i <= 23:
            cls = r2 + " V%d" % i
        elif i <= 26:
            cls = r3 + " %d" % i
        else:
            cls = "FIXTURE WARNING MESSAGE %d" % i
        cases = ["c%02d" % i] + (["a%02d" % i] if i <= 28 else [])
        lines.append(json.dumps({"class": cls, "text_full": cls, "n": 158 if i == 1 else 1,
                                 "cases": cases, "commands": {"MODEL": 1},
                                 "wclass_id": "W%02d" % i, "n_cases": len(cases)},
                                ensure_ascii=False))
    return "\n".join(lines) + "\n"


def run(pkg):
    """跑 verify.py 的**真实实现**，返回 (counts, code->levels)。"""
    rep = verify.Report()
    cfg = verify.check_structure(pkg, rep)
    verify.check_metrics(cfg, rep)
    verify.check_p0(pkg, cfg, rep)
    verify.check_consistency(pkg, rep)
    verify.check_frontmatter(pkg, cfg, rep)
    verify.check_hygiene(pkg, rep)
    by = {}
    for it in rep.items:
        by.setdefault(it["code"], []).append(it["level"])
    return rep.counts(), by


def level_of(by, code):
    lv = by.get(code)
    if not lv:
        return None
    return "FAIL" if "FAIL" in lv else ("WARN" if "WARN" in lv else "OK")


def main():
    tmp = tempfile.mkdtemp(prefix="selftest_gates_")
    pkg = os.path.join(tmp, "demo-pkg")          # 目录名须 == name == plugin
    try:
        meta = build_pkg(pkg)
        n = len(verify.CJK.findall(meta["displayDescription"]["zh"]))
        note(40 <= n <= 50, "夹具自检: displayDescription.zh CJK 字数落在 40-50", "n=%d" % n)

        # ---------- 绿证 1：合规包必须全过（不冤枉好人） ----------
        counts, by = run(pkg)
        note(counts["FAIL"] == 0 and counts["WARN"] == 0,
             "绿证 verify: 合规夹具包全过",
             "OK=%d WARN=%d FAIL=%d" % (counts["OK"], counts["WARN"], counts["FAIL"]))
        for code in ("A7", "A9", "C10", "D6", "D7", "F1", "F2", "F3", "F4"):
            note(level_of(by, code) == "OK", "绿证 %s: 目标门禁为 OK" % code)

        # ---------- 绿证 2：假红防护 —— 官方合法写法不得误判 ----------
        ap = os.path.join(pkg, "agents", "demo-agent.md")
        sp = os.path.join(pkg, "skills", "demo-skill", "SKILL.md")
        w(ap, AGENT_MD_GOOD.replace(
            "description: Demo agent used only by the gate dual-proof self-test.",
            "description: |\n  Demo agent used only by the gate dual-proof self-test.\n  Second line of a block scalar."))
        w(sp, SKILL_MD_GOOD.replace(
            "description: Demo skill used only by the gate dual-proof self-test.",
            "description: |\n  Demo skill used only by the gate dual-proof self-test.\n  Second line."))
        _, by = run(pkg)
        note(level_of(by, "F1") == "OK" and level_of(by, "F3") == "OK",
             "绿证 块标量:   description 用 | 块标量时 F1/F3 仍 OK（假红已关）")
        w(ap, AGENT_MD_GOOD)
        w(sp, SKILL_MD_GOOD)

        # ---------- 红证：逐个注入缺陷，断言目标门禁变 FAIL ----------
        cases = [
            ("F1", "红证 F1: 删掉 frontmatter 起始 ---",
             ap, lambda s: s.replace("---\nname: demo-agent", "name: demo-agent", 1)),
            ("F2", "红证 F2: frontmatter.name 改成错值",
             ap, lambda s: s.replace("name: demo-agent", "name: renamed-agent", 1)),
            ("F2", "红证 F2: displayName.zh 与 plugin.json 不一致",
             ap, lambda s: s.replace('zh: "示例智能体"', 'zh: "对不上的名字"', 1)),
            ("F3", "红证 F3: SKILL.md 删掉 version 行",
             sp, lambda s: s.replace('version: "0.1.0"\n', "", 1)),
            ("F4", "红证 F4: 主 Agent 注入官方禁止的 tools 键",
             ap, lambda s: s.replace("maxTurns: 50", "maxTurns: 50\ntools:\n  - Read", 1)),
            ("F4", "红证 F4: SKILL.md 混入专家专有键 displayDescription",
             sp, lambda s: s.replace('author: selftest', 'author: selftest\ndisplayDescription:\n  zh: "x"', 1)),
        ]
        base = {"F1": AGENT_MD_GOOD, "F2": AGENT_MD_GOOD,
                "F3": SKILL_MD_GOOD, "F4": AGENT_MD_GOOD}
        for code, label, path, mutate in cases:
            orig = io.open(path, encoding="utf-8").read()
            w(path, mutate(orig))
            _, by = run(pkg)
            note(level_of(by, code) == "FAIL", label + " -> %s FAIL" % code)
            w(path, orig)
        _ = base

        # ---------- 红证 A7：头像缩成占位实色图 ----------
        avp = os.path.join(pkg, "avatars", "demo.png")
        nb = os.path.getsize(avp)
        note(verify.AVATAR_MIN <= nb <= verify.AVATAR_MAX,
             "绿证 A7 前置: 零依赖夹具生成器产出的头像落在体积区间内", "%d 字节" % nb)
        png_noise(avp, side=32)                 # 32x32 噪声 → 远小于 10240 字节
        note(os.path.getsize(avp) < verify.AVATAR_MIN,
             "红证 A7 前置: 夹具头像已缩至下界以下", "%d 字节" % os.path.getsize(avp))
        _, by = run(pkg)
        note(level_of(by, "A7") == "FAIL", "红证 A7: 占位小图 -> A7 FAIL")
        real_avatar(avp)
        _, by = run(pkg)
        note(level_of(by, "A7") == "OK", "绿证 A7: 恢复合规头像后 -> A7 OK")

        # ---------- 红证 A9：非官方枚举目录的口径声明不得被删 ----------
        #   D5 的处置是「保留 knowledge/ + 明写这是非官方目录」；该声明一旦被静默删掉，
        #   后来人会误以为平台书面支持该目录。A9 就是防这一手。
        idxp = os.path.join(pkg, "knowledge", "INDEX.md")
        idx_good = io.open(idxp, encoding="utf-8").read()
        os.remove(idxp)
        _, by = run(pkg)
        note(level_of(by, "A9") == "FAIL", "红证 A9: 删掉 knowledge/INDEX.md -> A9 FAIL")
        w(idxp, "# 知识库入口\n\n本目录用于存放索引与事实层。\n")      # 有文件，但没声明口径
        _, by = run(pkg)
        note(level_of(by, "A9") == "FAIL", "红证 A9: INDEX.md 存在但删掉「非官方」口径 -> A9 FAIL")
        w(idxp, idx_good)
        _, by = run(pkg)
        note(level_of(by, "A9") == "OK", "绿证 A9: 复位口径声明后 -> A9 OK")

        # ---------- 红证 C10：P0 红线表不得有洞 ----------
        #   真实前例：P0-2（禁 AI 模板视觉套路）曾只写在脚本 docstring 里，
        #   主 Agent 红线表里根本没有这一条 —— 读者会以为它不存在。C10 就是抓这个。
        w(ap, AGENT_MD_GOOD.replace(" P0-2 ", " ", 1))
        _, by = run(pkg)
        note(level_of(by, "C10") == "FAIL", "红证 C10: 抹掉 P0-2 条文 -> C10 FAIL")
        w(ap, AGENT_MD_GOOD)
        _, by = run(pkg)
        note(level_of(by, "C10") == "OK", "绿证 C10: 复位后 -> C10 OK")

        # ---------- 红证 D7：警告口径必须能从数据复算 ----------
        #   「39 种消息」是对外承诺覆盖率的**分母**，不能是拍脑袋的数。
        #   D7 把归并规则写成算式重算；此处证明它真会红。
        wlp = os.path.join(pkg, "knowledge", "facts", "warning-library.jsonl")
        wl_good = io.open(wlp, encoding="utf-8").read()
        wrows = [json.loads(l) for l in wl_good.splitlines() if l.strip()]
        # (a) 少一行 → 62 变成 61
        w(wlp, "\n".join(json.dumps(r, ensure_ascii=False) for r in wrows[1:]) + "\n")
        _, by = run(pkg)
        note(level_of(by, "D7") == "FAIL", "红证 D7a: 警告库少一行 -> D7 FAIL")
        # (b) 破坏 R1 的归并组（把 13 类里的 1 类改名）→ 命中数不再等于 13
        wrows2 = [dict(r) for r in wrows]
        wrows2[0]["class"] = "RENAMED SO R1 NO LONGER MATCHES"
        w(wlp, "\n".join(json.dumps(r, ensure_ascii=False) for r in wrows2) + "\n")
        _, by = run(pkg)
        note(level_of(by, "D7") == "FAIL", "红证 D7b: 破坏 R1 归并组 -> D7 FAIL")
        # (c) 把 R2 组里的一类移名成 R1 前缀 → R1 变 14、R2 变 9，两组计数同时不符
        wrows3 = [dict(r) for r in wrows]
        wrows3[13]["class"] = "INPUT LINE EXCEEDED 90 CHARACTERS MISPLACED"
        w(wlp, "\n".join(json.dumps(r, ensure_ascii=False) for r in wrows3) + "\n")
        _, by = run(pkg)
        note(level_of(by, "D7") == "FAIL", "红证 D7c: 类键串组（R2 类挪进 R1）-> D7 FAIL")
        w(wlp, wl_good)
        _, by = run(pkg)
        note(level_of(by, "D7") == "OK", "绿证 D7: 复位后 -> D7 OK（62/39/219/90 复算一致）")

        # ---------- 红证 D6：SKILL.md 版本不得与 plugin.json 漂移 ----------
        #   真实风险：上架件里有 4 处版本号（清单 + 3 个技能），
        #   允许各自漂移就会出现「包是 1.0.0、技能还是 0.1.0」这种无法解释的发布物。
        w(sp, SKILL_MD_GOOD.replace('version: "0.1.0"', 'version: "9.9.9"', 1))
        _, by = run(pkg)
        note(level_of(by, "D6") == "FAIL", "红证 D6: SKILL.md 版本漂移 -> D6 FAIL")
        w(sp, SKILL_MD_GOOD)
        _, by = run(pkg)
        note(level_of(by, "D6") == "OK", "绿证 D6: 复位后版本对齐 -> D6 OK")

        # ---------- 绿红双证：自绘选型图的版式断言 ----------
        #   「图没人压字」不能靠肉眼，故生成器自带越界/压字断言；此处证明该断言真会红。
        rss.build()
        note(rss.layout_check() == [], "绿证 选型图版式: 本包真实图无越界/压字",
             "%d 条文字" % len(rss.TEXTS))
        rss.build()
        rss.text(1000, 120, "故意写得极长的一条文字用于触发越界与压字断言这是红证", 20)
        note(len(rss.layout_check()) > 0, "红证 选型图版式: 注入越界长文本 -> 断言报警")
        rss.build()                                   # 复位，避免污染后续
        note(rss.layout_check() == [], "绿证2 选型图版式: 复位后恢复无告警")

        # XML 合法性断言（实测补上：正文裸 `<` 几何断言查不出，却会让 SVG 报废）
        rss.build()
        good_svg = "\n".join(rss.S)
        note(rss.xml_check(good_svg) == [], "绿证 选型图XML: 本包真实产物为合法 XML")
        rss.S.append("<text>未转义的裸小于号 < 会让 SVG 报废</text>")
        note(len(rss.xml_check("\n".join(rss.S))) > 0,
             "红证 选型图XML: 注入未转义裸 < -> 断言报警")
        rss.build()
        note(rss.xml_check("\n".join(rss.S)) == [], "绿证2 选型图XML: 复位后重新合法")

        # ---------- 收尾：全部恢复后必须回到全绿 ----------
        counts, _ = run(pkg)
        note(counts["FAIL"] == 0, "收尾 verify: 恢复后回到全绿",
             "OK=%d WARN=%d FAIL=%d" % (counts["OK"], counts["WARN"], counts["FAIL"]))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    if FAILS:
        print("-" * 68)
        print("SELFTEST GATES FAILED (%d 项): %s" % (len(FAILS), FAILS))
        return 1
    print("-" * 68)
    print("SELFTEST GATES PASSED (绿红双证全部成立)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
