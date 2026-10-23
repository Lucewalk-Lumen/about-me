#!/usr/bin/env python3
"""dual_proof.py — 门禁绿红双证自检（G003）。

每条门禁必须能判红也能判绿：好输入应过、坏输入应拦。
本脚本**调用 gates.py 的真实门禁函数**（不自写重实现副本）做负向对照，
覆盖 length / shard / version / G004 emoji / exec（脚本可执行性）/ 场景路由 /
构成完整性 / P0 视觉 / 死链 / 路径安全 等门禁。
用法：python3 scripts/dual_proof.py
"""
import argparse
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import quality_eval  # noqa: E402
import gates  # noqa: E402

# G004 emoji 样本（用码点构造，避免本文件自身含 emoji 字面量而自伤）
EMOJI_SAMPLES = "".join(chr(c) for c in (0x2705, 0x274C))


def _write(path, s):
    with open(path, "w", encoding="utf-8") as f:
        f.write(s)


def _length_fail(pkg):
    _o, _w, f = gates._length_check(pkg)
    return f


def assert_dual(gate, good, bad, label):
    g = gate(good)
    b = gate(bad)
    assert g is True, f"{label}: 绿证失败（好输入应过）"
    assert b is False, f"{label}: 红证失败（坏输入应拦）"
    print(f"[OK] dual_proof {label}: 绿证通过 + 红证拦截")


def scenario_gate_ok(pkg, meta):
    r = quality_eval.check_scenario_routing(pkg, "plugin", meta)
    return r["penalty"] == 0


def build_parser():
    ap = argparse.ArgumentParser(
        prog="dual_proof.py",
        description="门禁绿红双证自检（G003）：调用 gates.py 真实门禁函数，好输入过 / 坏输入拦。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="退出码：0=全部双证通过；非 0=某条绿证/红证失败（断言失败）。")
    return ap


BAD_LEAD_MD = (
    "# 主理人\n\n"
    "| 场景 | 目标用户 |\n"
    "|---|---|\n"
    "| 教学 | 教师 |\n"
)


def main(argv=None):
    build_parser().parse_args(argv)

    # ---- 长度门禁：调用 gates._length_check 真实实现（不再自写重实现副本）----
    tmp0 = tempfile.mkdtemp(prefix="dualproof_length_")
    try:
        os.makedirs(os.path.join(tmp0, "agents"))
        _write(os.path.join(tmp0, "agents", "a.md"), "# a\n" + "正常长度的指令文本")
        assert not _length_fail(tmp0), "length: 绿证失败（未超长却 FAIL）"
        print("[OK] dual_proof length: 绿证通过（未超长文件）")
        _write(os.path.join(tmp0, "agents", "a.md"), "x" * 25000)
        assert _length_fail(tmp0), "length: 红证失败（超长文件应 FAIL）"
        print("[OK] dual_proof length_negctrl: 红证拦截（注入超长文件）")
    finally:
        shutil.rmtree(tmp0, ignore_errors=True)

    # ---- 清单门禁（gates._shard_check）：绿证 = 条目都在；红证 = 缺条目必拦 ----
    tmpS = tempfile.mkdtemp(prefix="dualproof_shard_")
    try:
        os.makedirs(os.path.join(tmpS, ".codebuddy-plugin"))
        os.makedirs(os.path.join(tmpS, "agents"))
        os.makedirs(os.path.join(tmpS, "skills", "s1"))
        _write(os.path.join(tmpS, "agents", "lead.md"), "# lead\n")
        _write(os.path.join(tmpS, ".codebuddy-plugin", "plugin.json"),
               json.dumps({"agents": ["./agents/lead.md"], "skills": ["./skills/s1"]}))
        assert not gates._shard_check(tmpS)[2], "shard: 绿证失败（条目都存在却 FAIL）"
        print("[OK] dual_proof shard: 绿证通过（清单条目全部存在）")
        _write(os.path.join(tmpS, ".codebuddy-plugin", "plugin.json"),
               json.dumps({"agents": ["./agents/missing.md"], "skills": ["./skills/s1"]}))
        assert gates._shard_check(tmpS)[2], "shard: 红证失败（缺条目应 FAIL）"
        print("[OK] dual_proof shard: 红证拦截（agents 条目缺失）")
    finally:
        shutil.rmtree(tmpS, ignore_errors=True)

    # ---- 版本真源（gates.embedded_version_scan）：绿证 = 假红已关 + 召回未丢；红证 = 漂移必拦 ----
    #   假红夹具（G003：假红与假绿同等对待）：文档里「斜杠 + 三段数字」（如 `/93.184.216`）无
    #   标识符前缀，**不得**被当成内嵌版本串；真版本必带标识符前缀（本包 UA 串即 `<名>/x.y.z`）。
    #   版本号一律用 ".join([...])" 动态构造，避免本文件源码出现 `/x.y.z` 字面量自伤本门禁。
    tmpV = tempfile.mkdtemp(prefix="dualproof_version_")
    try:
        os.makedirs(os.path.join(tmpV, "skills", "note"))
        good_v = ".".join(["1", "0", "0"])   # -> 1.0.0
        bad_v = ".".join(["2", "3", "4"])    # -> 2.3.4

        # 绿证（假红已关）：同一文件含「斜杠+三段数字」假红片段 + IPv4(带端口) + 合法版本串，
        #                  扫描须**只**识别出合法版本、其余 0 误判。
        _write(os.path.join(tmpV, "skills", "note", "a.py"),
               "NOTE = 'see /93.184.216 in docs'\n"
               "URL = 'http://127.0.0.1:18099/x'\n"
               "UA = 'wbes/%s'\n" % good_v)
        emb, bad = gates.embedded_version_scan(tmpV, good_v)
        assert emb == [("skills/note/a.py", good_v)] and not bad, \
            f"version: 绿证失败（假红未关：/93.184.216 等被误判；embedded={emb} bad={bad}）"
        print("[OK] dual_proof version: 绿证通过（假红已关：斜杠+三段数字/IPv4 不误判，仅识别内嵌版本串）")

        # 绿证2（召回未丢）：合法标识符前缀（字母/数字/_/-）的版本串必须被识别。
        _write(os.path.join(tmpV, "skills", "note", "a.py"), "UA = 'web-crawler/%s'\n" % good_v)
        emb2, _bad2 = gates.embedded_version_scan(tmpV, good_v)
        assert emb2 == [("skills/note/a.py", good_v)], \
            f"version: 绿证2 失败（标识符前缀版本串漏检；embedded={emb2}）"
        print("[OK] dual_proof version: 绿证2 通过（标识符前缀版本串召回未丢）")

        # 红证（真会红）：版本串漂移（!= expected）必须被判 bad。
        _write(os.path.join(tmpV, "skills", "note", "a.py"), "UA = 'wbes/%s'\n" % bad_v)
        _emb, bad = gates.embedded_version_scan(tmpV, good_v)
        assert bad == [("skills/note/a.py", bad_v)], \
            f"version: 红证失败（漂移应报 bad；bad={bad}）"
        print("[OK] dual_proof version: 红证拦截（内嵌版本串漂移 != plugin.version）")
    finally:
        shutil.rmtree(tmpV, ignore_errors=True)

    # ---- G004 emoji（gates.emoji_scan）：绿证 = 无 emoji；红证 = 注入 emoji 必拦 ----
    tmpE = tempfile.mkdtemp(prefix="dualproof_emoji_")
    try:
        os.makedirs(os.path.join(tmpE, "scripts"))
        _write(os.path.join(tmpE, "scripts", "a.py"), "print('[OK] fine')\n")
        assert not gates.emoji_scan(tmpE, EMOJI_SAMPLES), "emoji: 绿证失败（无 emoji 却命中）"
        print("[OK] dual_proof emoji(G004): 绿证通过（纯文本标记）")
        _write(os.path.join(tmpE, "scripts", "a.py"),
               "print('done " + EMOJI_SAMPLES[0] + "')\n")
        assert gates.emoji_scan(tmpE, EMOJI_SAMPLES), "emoji: 红证失败（含 emoji 应命中）"
        print("[OK] dual_proof emoji(G004): 红证拦截（脚本输出含 emoji）")
    finally:
        shutil.rmtree(tmpE, ignore_errors=True)

    # ---- 脚本可执行性门禁（gates._exec_check）：绿证 = 好脚本过；红证 = 注入语法错误必拦 ----
    tmpX = tempfile.mkdtemp(prefix="dualproof_exec_")
    try:
        os.makedirs(os.path.join(tmpX, "scripts"))
        _write(os.path.join(tmpX, "scripts", "good.py"),
               "import argparse\n"
               "def main():\n"
               "    ap = argparse.ArgumentParser()\n"
               "    ap.add_argument('x', nargs='?')\n"
               "    ap.parse_args()\n"
               "if __name__ == '__main__':\n"
               "    main()\n")
        _o, _w, f = gates._exec_check(tmpX)
        assert not f, f"exec: 绿证失败（好脚本应过）{f}"
        print("[OK] dual_proof exec: 绿证通过（可编译 + --help 冒烟）")
        _write(os.path.join(tmpX, "scripts", "broken.py"), "def broken(:\n    pass\n")
        _o, _w, f = gates._exec_check(tmpX)
        assert any("broken.py" in m for m in f), f"exec: 红证失败（注入 def broken(: 应被拦）{f}"
        print("[OK] dual_proof exec: 红证拦截（注入 `def broken(:` 语法错误）")
    finally:
        shutil.rmtree(tmpX, ignore_errors=True)

    #   绿证 = 真实包场景路由全过（表在 / 三场景齐 / 关键词有落点 / 回退可用）
    #   红证 = 临时包注入缺「附加门禁」列的残缺路由表，必须被拦
    with open(os.path.join(PKG, ".codebuddy-plugin", "plugin.json"), encoding="utf-8") as fh:
        meta = json.load(fh)
    assert scenario_gate_ok(PKG, meta), "scenario_routing: 绿证失败（当前包场景路由应全过）"
    print("[OK] dual_proof scenario_routing: 绿证通过（真实包场景路由全过）")
    tmp = tempfile.mkdtemp(prefix="dualproof_bad_scene_")
    try:
        os.makedirs(os.path.join(tmp, ".codebuddy-plugin"))
        os.makedirs(os.path.join(tmp, "agents"))
        bad_meta = {
            "name": "bad", "plugin": "bad", "expertType": "team",
            "agentName": "lead", "teamInfo": {"leadAgent": "lead"},
            "quickPrompts": [],
        }
        with open(os.path.join(tmp, ".codebuddy-plugin", "plugin.json"), "w", encoding="utf-8") as f:
            json.dump(bad_meta, f, ensure_ascii=False)
        with open(os.path.join(tmp, "agents", "lead.md"), "w", encoding="utf-8") as f:
            f.write(BAD_LEAD_MD)
        assert not scenario_gate_ok(tmp, bad_meta), \
            "scenario_routing: 红证失败（残缺路由表应被拦）"
        print("[OK] dual_proof scenario_routing: 红证拦截（缺场景行 / 快启无场景信号）")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # 绿证2：场景词**不再硬编码** —— 用「自定义场景词汇」（答辩/商务/党建党政）的临时包验证会通过
    tmp2 = tempfile.mkdtemp(prefix="dualproof_custom_scene_")
    try:
        os.makedirs(os.path.join(tmp2, ".codebuddy-plugin"))
        os.makedirs(os.path.join(tmp2, "agents"))
        os.makedirs(os.path.join(tmp2, "references"))
        custom_meta = {
            "name": "custom", "plugin": "custom", "expertType": "team",
            "agentName": "lead", "teamInfo": {"leadAgent": "lead"},
            "quickPrompts": [{"zh": "我要做一份答辩材料"}, {"zh": "b"}, {"zh": "c"}],
        }
        with open(os.path.join(tmp2, ".codebuddy-plugin", "plugin.json"), "w", encoding="utf-8") as f:
            json.dump(custom_meta, f, ensure_ascii=False)
        with open(os.path.join(tmp2, "agents", "lead.md"), "w", encoding="utf-8") as f:
            f.write("# 主理人\n\n"
                    "| 场景 | 触发词 |\n|---|---|\n"
                    "| 答辩 | 答辩、开题 |\n"
                    "| 商务 | 述职、汇报 |\n"
                    "| 党建党政 | 党课、党纪 |\n")
        with open(os.path.join(tmp2, "references", "x.md"), "w", encoding="utf-8") as f:
            f.write("# ref\n")
        assert scenario_gate_ok(tmp2, custom_meta), \
            "scenario_routing: 绿证2 失败（自定义场景词汇的完整包应过 —— 证明场景词由本包自声明推导）"
        print("[OK] dual_proof scenario_routing: 绿证2 通过（自定义场景词汇包，证明未硬编码）")
        # 红证2：同一包 —— 一行变空壳 + 快启不命中任何自声明场景
        with open(os.path.join(tmp2, "agents", "lead.md"), "w", encoding="utf-8") as f:
            f.write("# 主理人\n\n"
                    "| 场景 | 触发词 |\n|---|---|\n"
                    "| 答辩 | 答辩、开题 |\n"
                    "| 商务 |  |\n")
        bad_meta2 = dict(custom_meta)
        bad_meta2["quickPrompts"] = [{"zh": "无关文本"}]
        assert not scenario_gate_ok(tmp2, bad_meta2), \
            "scenario_routing: 红证2 失败（空壳场景行 + 快启无场景信号应被拦）"
        print("[OK] dual_proof scenario_routing: 红证2 拦截（空壳场景行 + 快启无场景信号）")
    finally:
        shutil.rmtree(tmp2, ignore_errors=True)

    # 绿证3：references 位于 skills/<name>/references/ 的 plugin 布局，E 维「记忆与上下文」须认账
    tmp3 = tempfile.mkdtemp(prefix="dualproof_nested_refs_")
    try:
        os.makedirs(os.path.join(tmp3, "skills", "playbook", "references"))
        with open(os.path.join(tmp3, "skills", "playbook", "references", "a.md"), "w", encoding="utf-8") as f:
            f.write("# a\n")
        n_e, e_ev, _ = quality_eval.dim_composition_completeness(tmp3, "plugin", {}, "x")
        assert "记忆与上下文" not in " ".join(e_ev), \
            "composition: 绿证3 失败（skills/<name>/references 布局应被识别为「记忆与上下文」）"
        print("[OK] dual_proof composition: 绿证3 通过（识别 skills/<name>/references 布局）")
        tmp4 = tempfile.mkdtemp(prefix="dualproof_norefs_")
        try:
            _, e_ev4, _ = quality_eval.dim_composition_completeness(tmp4, "plugin", {}, "x")
            assert "记忆与上下文" in " ".join(e_ev4), \
                "composition: 红证3 失败（完全无 references/knowledge 应被拦）"
            print("[OK] dual_proof composition: 红证3 拦截（无 references/knowledge）")
        finally:
            shutil.rmtree(tmp4, ignore_errors=True)
    finally:
        shutil.rmtree(tmp3, ignore_errors=True)
    # P0 视觉红线判据（维度 D）：绿证 = 禁令清单/否定语境不误判；红证 = 真·使用语境必拦
    #   绿证：本条即本包真实写法（"禁止 3D / 卡通 / 二次元 / 营销插画 / 装饰渐变大图"），
    #        否定词与关键词相距远，旧版固定 ±24 窗口会误判，故以此固化为回归用例。
    assert quality_eval.p0_visual_violation(
        "禁止 3D / 卡通 / 二次元 / 营销插画 / 装饰渐变大图。") is False, \
        "p0_visual: 绿证失败（长禁令清单不应被判违规）"
    print("[OK] dual_proof p0_visual: 绿证通过（长禁令清单 / 否定语境不误判）")
    #   红证：真·描述性使用（渐变按钮 + 毛玻璃 + 发光描边）必须被拦
    assert quality_eval.p0_visual_violation(
        "标题栏使用 Indigo 到 Pink 的渐变按钮，卡片加毛玻璃与发光描边。") is True, \
        "p0_visual: 红证失败（非禁止语境使用渐变/毛玻璃/发光应被拦）"
    print("[OK] dual_proof p0_visual: 红证拦截（非禁止语境使用渐变/毛玻璃/发光）")
    # 死链门禁（gates.deadlink_scan）：绿证 = 有效路径引用 / md 链接不误判；红证 = 悬空引用必拦
    tmp5 = tempfile.mkdtemp(prefix="dualproof_deadlink_")
    try:
        os.makedirs(os.path.join(tmp5, "references"))
        os.makedirs(os.path.join(tmp5, "knowledge"))
        with open(os.path.join(tmp5, "knowledge", "b.md"), "w", encoding="utf-8") as f:
            f.write("# b\n")
        with open(os.path.join(tmp5, "references", "a.md"), "w", encoding="utf-8") as f:
            f.write("见 `knowledge/b.md` 与 [文档](knowledge/b.md)。\n")
        _, n_code, broken = gates.deadlink_scan(tmp5)
        assert n_code >= 1, "deadlink: 绿证失败（有效反引号路径引用未被计入）"
        assert not broken, f"deadlink: 绿证失败（有效引用被误判死链）{broken}"
        print("[OK] dual_proof deadlink: 绿证通过（有效路径引用 / md 链接不误判）")
        with open(os.path.join(tmp5, "references", "a.md"), "w", encoding="utf-8") as f:
            f.write("见 `knowledge/missing.md`。\n")
        _, _, broken = gates.deadlink_scan(tmp5)
        assert broken, "deadlink: 红证失败（悬空路径引用应被拦）"
        print("[OK] dual_proof deadlink: 红证拦截（悬空路径引用）")
    finally:
        shutil.rmtree(tmp5, ignore_errors=True)
    # 路径安全门禁（gates.traversal_scan）：绿证 = 相对路径不误判；红证 = 本机绝对路径泄露必拦
    tmp6 = tempfile.mkdtemp(prefix="dualproof_traversal_")
    try:
        with open(os.path.join(tmp6, "a.json"), "w", encoding="utf-8") as f:
            f.write('{"path": "assets/ok.png"}')
        _, hits = gates.traversal_scan(tmp6)
        assert not hits, f"traversal: 绿证失败（相对路径不应命中）{hits}"
        print("[OK] dual_proof traversal: 绿证通过（相对路径不误判）")
        with open(os.path.join(tmp6, "a.json"), "w", encoding="utf-8") as f:
            f.write('{"path": "%s"}' % ("/" + "Users/someone/secret/key.pem"))
        _, hits = gates.traversal_scan(tmp6)
        assert hits, "traversal: 红证失败（本机绝对路径应被拦）"
        print("[OK] dual_proof traversal: 红证拦截（本机绝对路径泄露）")
    finally:
        shutil.rmtree(tmp6, ignore_errors=True)
    print("[OK] dual_proof: 门禁绿红双证通过（好输入过 / 坏输入拦）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
