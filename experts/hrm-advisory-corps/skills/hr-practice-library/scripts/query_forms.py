#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HR 实务工具库检索入口（hr-practice-library / knowledge 自包含，纯标准库零依赖）

本技能归属 hrm-advisory-corps：199 份 HR 制度与表单模板，按六大模块归口到本包的
7 个 scoped 技能 / agent，并可连接到对应的 SOP 引擎与统一合规闸门 compliance_gate.py。

用法:
  python3 query_forms.py "绩效"                    # 关键词检索（标题/字段/条款/正文）
  python3 query_forms.py "F096" --full            # form_id 精确 + 字段骨架与正文
  python3 query_forms.py "离职" --module ER       # 限定模块
  python3 query_forms.py "" --kind 表格 --limit 5  # 限定类型（关键词可为空，须配合筛选条件）
  python3 query_forms.py --skill recruitment-pipeline   # 反查：某技能/agent 负责哪些表单
  python3 query_forms.py --engine payroll_engine.py     # 反查：哪些表单用到某 SOP 引擎
  python3 query_forms.py --flow F096              # 流程关联：某表单在 HR 闭环中的上下游
  python3 query_forms.py --modules                # 列出 7 大模块与编号段、归属技能
  python3 query_forms.py --verify-files           # 校验 199 条原件路径均存在（相对 skill 根）
  python3 query_forms.py "F096" --json            # 输出原始 JSON（供程序消费）

匹配优先级: form_id 精确(F001) > 标题 > 字段骨架 > 正文（均大小写不敏感的子串匹配）。
空查询处理: 单独空查询被拒绝（会命中全部条目，结果无意义）；配合 --module / --kind /
--skill / --engine / --flow 时视为「只按筛选条件列举」，允许为空。
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
KNOW = os.path.join(SKILL, "knowledge")
IDX = os.path.join(KNOW, "_practice_index.json")
MMAP = os.path.join(KNOW, "_module_map.json")
FORMS = os.path.join(KNOW, "forms")
TEMPLATES = os.path.join(SKILL, "templates")

RE_FORM_ID = re.compile(r"^[fF]\d{1,3}$")


def normalize_form_id(q):
    """把 F1 / f001 之类的查询词补零为库内实际 ID 形态 F001。

    库内 form_id 统一为 F+3 位零填充（F001…F199），而 RE_FORM_ID 允许只写
    1-3 位数字，故 `query_forms.py "F1"` 原本会走到精确比较而「未命中」。
    非 form_id 查询词原样返回。
    """
    if not RE_FORM_ID.match(q):
        return q
    return "F%03d" % int(q[1:])


def load_json(p, what):
    if not os.path.exists(p):
        sys.exit("[错误] 缺少%s: %s" % (what, p))
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def norm(s):
    return (s or "").lower().strip()


def _positive_int(s):
    try:
        v = int(s)
    except ValueError:
        raise argparse.ArgumentTypeError("必须是正整数，收到: %r" % s)
    if v < 1:
        raise argparse.ArgumentTypeError("必须是 >=1 的整数，收到: %d" % v)
    return v


def full_record(n):
    fp = os.path.join(FORMS, n["form_id"] + ".json")
    if os.path.exists(fp):
        with open(fp, encoding="utf-8") as f:
            return json.load(f)
    return n


def matches(node, rec, q, use_body):
    """rec 为 None 时只按索引字段匹配（快路径）；否则可深入正文。"""
    if RE_FORM_ID.match(q):
        return node["form_id"].upper() == normalize_form_id(q).upper()
    if q in norm(node["title"]):
        return True
    if rec is not None and any(q in norm(x) for x in rec.get("outline", [])):
        return True
    if use_body and rec is not None and q in norm(rec.get("body", "")):
        return True
    return False


def by_skill(nodes, skill, limit):
    skill = norm(skill)
    out = [n for n in nodes
           if norm(n.get("solution_links", {}).get("owner_skill", "")) == skill
           or norm(n.get("solution_links", {}).get("owner_agent", "")) == skill]
    return out[:limit]


def by_engine(nodes, engine, limit):
    engine = norm(engine)
    out = []
    for n in nodes:
        sl = n.get("solution_links", {})
        engines = [norm(e) for e in sl.get("primary_engines", []) + sl.get("extra_engines", [])]
        if engine in engines:
            out.append(n)
    return out[:limit]


def show_modules(mmap, nodes):
    print("=== HR 实务工具库 · 7 大模块（编号段 = 职能闭环顺序）===")
    by = {}
    for n in nodes:
        by.setdefault(n["module_code"], []).append(n)
    for m in mmap["modules"]:
        g = by.get(m["code"], [])
        owner = next((n.get("solution_links", {}).get("owner_skill") for n in g), "—")
        print("\n%s %s  %s" % (m["code"], m["zh"], m["id_range"]))
        print("  定位: %s" % m["role"])
        print("  构成: 制度 %d / 表格 %d" % (
            sum(1 for x in g if x["kind"] == "制度"),
            sum(1 for x in g if x["kind"] == "表格")))
        print("  归属技能/agent: %s" % owner)
        if m.get("no_anchor_reason"):
            print("  说明: %s" % m["no_anchor_reason"])
    print("\n交接单据 %d 条，详见 --flow <form_id> 或 knowledge/_module_map.json"
          % len(mmap.get("handoffs", [])))
    return 0


def verify_files(nodes):
    """校验全部节点的 file 路径均存在（相对 skill 根）；缺失则列出并返回 1。"""
    total = len(nodes)
    missing = [n["file"] for n in nodes
               if not os.path.exists(os.path.join(SKILL, n["file"]))]
    root = os.path.relpath(TEMPLATES, SKILL)
    if missing:
        print("=== 原件存在性校验（根: %s）：%d/%d 存在，%d 缺失 ==="
              % (root, total - len(missing), total, len(missing)))
        for m in missing:
            print("  缺失: %s" % m)
        return 1
    print("=== 原件存在性校验（根: %s）：%d/%d 全部存在 ===" % (root, total, total))
    return 0


def show_flow(fid, mmap, nodes):
    fid = normalize_form_id(fid.strip()).upper()
    by_id = {n["form_id"]: n for n in nodes}
    n = by_id.get(fid)
    if not n:
        print("[未命中] 库内无此 form_id: %s" % fid)
        return 0
    mod = next((m for m in mmap["modules"] if m["code"] == n["module_code"]), None)
    print("=== 流程关联: %s %s（%s / %s）===" % (fid, n["title"], n["module_zh"], n["kind"]))
    print("原件: %s" % n["file"])
    sl = n.get("solution_links", {})
    if sl:
        print("归属: 技能 %s / agent %s" % (sl.get("owner_skill"), sl.get("owner_agent")))
        print("SOP 引擎: %s%s" % (
            "、".join(sl.get("primary_engines", [])) or "—",
            ("（增强: " + "、".join(sl.get("extra_engines", [])) + "）") if sl.get("extra_engines") else ""))
        print("终检闸门: %s（%s）" % (sl.get("gate", {}).get("engine"), sl.get("gate", {}).get("path")))
    if mod:
        print("模块位置: %s（%s）" % (mod["zh"], mod["id_range"]))
    ins = [h for h in mmap.get("handoffs", []) if h["to"] == fid]
    outs = [h for h in mmap.get("handoffs", []) if h["from"] == fid]
    print("\n【上游单据 → 本单据】%d" % len(ins))
    for h in ins:
        src = by_id.get(h["from"], {})
        print("  %s %s —— %s（%s）" % (h["from"], src.get("title", "?"), h["what"], h["stage"]))
    print("【本单据 → 下游单据】%d" % len(outs))
    for h in outs:
        dst = by_id.get(h["to"], {})
        print("  %s %s —— %s（%s）" % (h["to"], dst.get("title", "?"), h["what"], h["stage"]))
    if not ins and not outs:
        print("  （本单据未纳入跨模块交接表；模块内流程见 knowledge/_module_map.json）")
    return 0


def main():
    ap = argparse.ArgumentParser(description="HR 实务工具库检索（hrm-advisory-corps）")
    ap.add_argument("query", nargs="?", default="",
                    help="关键词 / form_id(如 F096)；配合筛选条件时可省略")
    ap.add_argument("--full", action="store_true", help="输出字段骨架与正文")
    ap.add_argument("--limit", type=_positive_int, default=10)
    ap.add_argument("--module", help="限定模块代码（HRP/REC/TRN/PER/COM/ER/ARC）")
    ap.add_argument("--kind", choices=["制度", "表格"], help="限定类型")
    ap.add_argument("--skill", help="反查：列出归属该 scoped 技能/agent 的表单")
    ap.add_argument("--engine", help="反查：列出用到该 SOP 引擎脚本的表单（如 payroll_engine.py）")
    ap.add_argument("--flow", metavar="FORM_ID", help="流程关联：该表单的上下游交接单据")
    ap.add_argument("--modules", action="store_true", help="列出 7 大模块与编号段、归属技能")
    ap.add_argument("--verify-files", action="store_true",
                    help="校验全部节点 file 路径均存在（相对 skill 根），缺失则非零退出")
    ap.add_argument("--json", action="store_true", help="输出原始 JSON")
    args = ap.parse_args()

    data = load_json(IDX, "实务工具索引")
    nodes = data["nodes"]
    mmap = load_json(MMAP, "模块映射文件")

    if args.verify_files:
        return verify_files(nodes)
    if args.modules:
        return show_modules(mmap, nodes)
    if args.flow:
        return show_flow(args.flow, mmap, nodes)

    if args.module:
        codes = {m["code"] for m in mmap["modules"]}
        if args.module.upper() not in codes:
            ap.error("未知模块代码 %r，可选: %s" % (args.module, "/".join(sorted(codes))))
        nodes = [n for n in nodes if n["module_code"] == args.module.upper()]
    if args.kind:
        nodes = [n for n in nodes if n["kind"] == args.kind]
    if args.skill:
        hits = by_skill(nodes, args.skill, args.limit)
        if not hits:
            print("[未命中] 无表单归属技能/agent %r（库内共 %d 条）" % (args.skill, len(data["nodes"])))
            return 0
        print("=== 归属「%s」的表单 %d 条（筛选范围内 %d）===" % (args.skill, len(hits), len(nodes)))
        for n in hits:
            print("  %s [%s/%s] %s" % (n["form_id"], n["module_code"], n["kind"], n["title"]))
        return 0
    if args.engine:
        hits = by_engine(nodes, args.engine, args.limit)
        if not hits:
            print("[未命中] 无表单使用引擎 %r（库内共 %d 条）" % (args.engine, len(data["nodes"])))
            return 0
        print("=== 使用引擎「%s」的表单 %d 条（筛选范围内 %d）===" % (args.engine, len(hits), len(nodes)))
        for n in hits:
            print("  %s [%s/%s] %s" % (n["form_id"], n["module_code"], n["kind"], n["title"]))
        return 0

    q = norm(args.query)
    if not q:
        if not (args.module or args.kind):
            ap.error("查询词不能为空（空查询会命中全部条目，结果无意义）；"
                     "如需按模块/类型/技能/引擎列举，请加对应参数")
        hits = nodes[:args.limit]
    elif RE_FORM_ID.match(q):
        fid = normalize_form_id(q).upper()
        hits = [n for n in nodes if n["form_id"].upper() == fid]
        if not hits:
            print("[未命中] 库内无此 form_id: %s" % args.query)
            return 0
    else:
        hits = [n for n in nodes if q in norm(n["title"])]
        if not hits:
            hits = [n for n in nodes if matches(n, full_record(n), q, True)]
        hits = hits[:args.limit]

    if not hits:
        print("[未命中] 实务工具库（筛选范围内 %d 条）无匹配: %s" % (len(nodes), args.query))
        return 0

    if args.json:
        out = [full_record(n) if args.full else n for n in hits]
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0

    print("=== 实务工具库命中 %d 条（筛选范围内 %d，库共 %d）==="
          % (len(hits), len(nodes), len(data["nodes"])))
    for n in hits:
        sl = n.get("solution_links", {})
        print("\n● %s  [%s %s / %s]  %s"
              % (n["form_id"], n["module_code"], n["module_zh"], n["kind"], n["title"]))
        print("  原件: %s（字段/条款 %d，正文 %d 字符）"
              % (n["file"], n["n_outline"], n["body_chars"]))
        if sl:
            eng = "、".join(sl.get("primary_engines", [])) or "—"
            extra = sl.get("extra_engines", [])
            extra_s = ("（增强: " + "、".join(extra) + "）") if extra else ""
            print("  归属: 技能 %s / agent %s" % (sl.get("owner_skill"), sl.get("owner_agent")))
            print("  SOP 引擎: %s%s" % (eng, extra_s))
            print("  终检闸门: %s" % sl.get("gate", {}).get("engine"))
            if sl.get("related_refs"):
                print("  相关参考: " + "；".join(r["path"] for r in sl["related_refs"][:4])
                      + ("…" if len(sl["related_refs"]) > 4 else ""))
        if args.full:
            rec = full_record(n)
            for x in rec.get("outline", [])[:30]:
                print("    · %s" % x)
            if len(rec.get("outline", [])) > 30:
                print("    …（共 %d 项）" % len(rec["outline"]))
            body = rec.get("body", "")
            if body:
                print("    ── 正文 ──")
                for ln in body.split("\n")[:40]:
                    print("    %s" % ln)
                if len(body.split("\n")) > 40:
                    print("    …（正文共 %d 行，完整文本见 %s）" % (len(body.split("\n")), rec.get("file")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
