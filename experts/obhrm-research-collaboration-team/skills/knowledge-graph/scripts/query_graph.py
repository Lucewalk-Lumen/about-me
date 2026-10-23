#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OBHRM 跨库索引检索入口（knowledge-graph / 连接 量表-理论-R 三库）

用法:
  python3 query_graph.py "self determination"   # 按构念查关联的量表/理论/R方法
  python3 query_graph.py "S347"                 # 查某量表的关联理论(via)
  python3 query_graph.py "T003"                 # 查某理论的关联量表(via)
  python3 query_graph.py "8.1"                  # 查某 R 方法的 construct 适用域
  python3 query_graph.py "社会交换" --json       # 输出原始 JSON

说明: 跨库主键为 construct_id(构念归一化slug)。scale/theory 通过 construct_id 与 R 方法
     (r_applicability[method_no].construct_ids) 关联。边 scale_to_theory / theory_to_scale
     携带 via(关联媒介词)，悬空=0。
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KNOW = os.path.normpath(os.path.join(HERE, "..", "knowledge"))
IDX = os.path.join(KNOW, "cross-library-index.json")


def load():
    with open(IDX, encoding="utf-8") as f:
        return json.load(f)


def norm(s):
    return (s or "").lower().strip()


# R 方法适用性类别别名 -> r_applicability.categories 的取值。
# 仅做「全等」匹配：若用包含匹配，"theory"/"理论" 会命中 83 个 construct_id，
# 把本该走构念检索的查询错误改道到 R 方法分支。
CATEGORY_ALIASES = {
    "scale": "scale", "量表": "scale",
    "theory": "theory", "理论": "theory",
    "general": "general", "通用": "general",
}
CATEGORY_LABELS = {
    "scale": "适用于量表库", "theory": "适用于理论库", "general": "通用方法",
}


def main():
    ap = argparse.ArgumentParser(description="OBHRM 跨库索引检索")
    ap.add_argument("query", help="construct_id / scale_id(Sxxx) / theory_id(Txxx) / method_no / 关键词")
    ap.add_argument("--category", metavar="类别", default=None,
                    help="按 R 方法适用类别检索（scale/量表 | theory/理论 | general/通用）；"
                         "类别级检索，不区分构念")
    ap.add_argument("--json", action="store_true", help="输出原始 JSON")
    args = ap.parse_args()

    if not os.path.exists(IDX):
        print(f"[错误] 索引缺失: {IDX}", file=sys.stderr)
        return 1

    d = load()
    ci = d.get("construct_index", {})          # dict: construct_id -> {...}
    s2t = d.get("scale_to_theory", {})         # dict: scale_id -> [edge]
    t2s = d.get("theory_to_scale", {})         # dict: theory_id -> [edge]
    ra = d.get("r_applicability", {})          # dict: method_no -> {...}

    q = args.query.strip()
    ql = norm(q)

    # 0) 显式类别检索：--category scale|theory|general（含中文别名）
    if args.category is not None:
        cat = CATEGORY_ALIASES.get(norm(args.category))
        if cat is None:
            print(f"[错误] 未知类别: {args.category}；可选: "
                  f"{', '.join(sorted(set(CATEGORY_ALIASES)))}", file=sys.stderr)
            return 1
        methods = sorted(m for m, v in ra.items() if cat in v.get("categories", []))
        if args.json:
            print(json.dumps({
                "category": cat, "level": "category",
                "note": "仅类别级适用性，非构念级关联；r_applicability[*].construct_ids 当前为空",
                "methods": methods,
            }, ensure_ascii=False, indent=2))
            return 0
        print(f"=== R 方法类别「{CATEGORY_LABELS[cat]}」命中 {len(methods)} 个 (共 {len(ra)}) ===")
        print("[!]  仅类别级适用性，无构念级绑定："
              "`r_applicability[*].construct_ids` 当前为空，无法按构念反查 R 方法。")
        for m in methods[:30]:
            print(f"  {m}  {ra[m].get('title_hint') or ''}".rstrip())
        if len(methods) > 30:
            print(f"  … 另有 {len(methods) - 30} 个（用 --json 查看全部）")
        return 0

    # 1) scale_id 精确
    if len(q) > 1 and q[0] in ("s", "S") and q[1:].isdigit() and q in s2t:
        edges = s2t[q]
        if args.json:
            print(json.dumps({"scale_id": q, "related_theories": edges}, ensure_ascii=False, indent=2))
        else:
            print(f"=== 量表 {q} 的关联理论 ({len(edges)}) ===")
            for e in edges:
                print(f"  → {e['theory_id']}  via: {e.get('via','')}  (construct: {e.get('construct_id','')})")
        return 0

    # 2) theory_id 精确
    if len(q) > 1 and q[0] in ("t", "T") and q[1:].isdigit() and q in t2s:
        edges = t2s[q]
        if args.json:
            print(json.dumps({"theory_id": q, "related_scales": edges}, ensure_ascii=False, indent=2))
        else:
            print(f"=== 理论 {q} 的关联量表 ({len(edges)}) ===")
            for e in edges:
                print(f"  → {e['scale_id']}  via: {e.get('via','')}  (construct: {e.get('construct_id','')})")
        return 0

    # 3) method_no 精确
    if q in ra:
        rec = ra[q]
        if args.json:
            print(json.dumps({"method_no": q, **rec}, ensure_ascii=False, indent=2))
        else:
            print(f"=== R 方法 {q} 适用域 ===")
            print(f"  分类: {', '.join(rec.get('categories', []))}")
            print(f"  关联 construct_ids: {', '.join(rec.get('construct_ids', [])) or '(通用)'}")
        return 0

    # 4) construct_id / 标签关键词匹配
    hits = []
    for cid, v in ci.items():
        if ql == cid or ql in cid or ql in norm(v.get("label_zh", "")) or ql in norm(v.get("label_en", "")):
            hits.append((cid, v))
    if not hits:
        # 5) R 方法「类别级」适用性检索（全等匹配，排在构念检索之后）
        cat = CATEGORY_ALIASES.get(ql)
        if cat is not None:
            methods = sorted(m for m, v in ra.items() if cat in v.get("categories", []))
            if args.json:
                print(json.dumps({
                    "category": cat,
                    "level": "category",
                    "note": "仅类别级适用性，非构念级关联；r_applicability[*].construct_ids 当前为空",
                    "methods": methods,
                }, ensure_ascii=False, indent=2))
                return 0
            print(f"=== R 方法类别「{CATEGORY_LABELS[cat]}」命中 {len(methods)} 个 (共 {len(ra)}) ===")
            print("[!]  仅类别级适用性，无构念级绑定："
                  f"`r_applicability[*].construct_ids` 当前为空，无法按构念反查 R 方法。")
            for m in methods[:30]:
                print(f"  {m}  {ra[m].get('title_hint') or ''}".rstrip())
            if len(methods) > 30:
                print(f"  … 另有 {len(methods) - 30} 个（用 --json 查看全部）")
            return 0

        print(f"[未命中] 跨库索引(construct {len(ci)} 条)无匹配: {q}")
        return 0

    if args.json:
        print(json.dumps([{"construct_id": c, **v} for c, v in hits], ensure_ascii=False, indent=2))
        return 0

    for cid, v in hits:
        print(f"\n=== 构念: {v.get('label_zh','')} / {v.get('label_en','')} ===")
        print(f"  construct_id: {cid}")
        print(f"  关联理论: {', '.join(v.get('theory_ids', [])) or '(无)'}")
        print(f"  关联量表: {', '.join(v.get('scale_ids', [])) or '(无)'}")
        print(f"  关联R方法: {', '.join(v.get('r_methods', [])) or '(无)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
