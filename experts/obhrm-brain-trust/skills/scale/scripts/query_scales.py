#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OBHRM 量表库检索入口（scale-library）。

检索内核由共享模块 `skills/bridge/kernel/library_query.py` 提供，
theory-library / scale-library / r-analysis 三个技能复用同一份匹配、安全边界、
JSON 契约与覆盖率逻辑，本文件只做领域参数 + 渲染回调的薄包装。

用法:
  python3 query_scales.py "trust"                 # 关键词(中/英/构念)检索
  python3 query_scales.py "S001" --full           # scale_id 精确 + 完整条目(含 items)
  python3 query_scales.py "self determination"     # 英文构念词
  python3 query_scales.py "领导" --limit 5
  python3 query_scales.py "S001" --json           # 输出原始 JSON(供程序消费)

匹配优先级: scale_id 精确(S001) > construct_id/变量名/标题 包含(大小写不敏感)。
全角 Ｓ００１ 与半角 S001 等价；编号查询不做子串匹配。
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KNOW = os.path.normpath(os.path.join(HERE, "..", "knowledge"))
IDX = os.path.join(KNOW, "_scale_index.json")
SCALES = os.path.join(KNOW, "scales")

_KERNEL = os.path.normpath(os.path.join(HERE, "..", "..", "bridge", "kernel"))
if _KERNEL not in sys.path:
    sys.path.insert(0, _KERNEL)
from library_query import query_library, positive_int  # noqa: E402

_ITEM_SHOW = 10   # --full 时逐题展示的条数上限，超出部分显式写明总数
_BG_LIMIT = 200   # --full 时原始出处展示的字符上限，超出部分显式标注截断


def _render_header(n):
    out = [
        f"\n● {n['scale_id']}  {n.get('variable_zh','')} / {n.get('variable_en','')}",
        f"  construct_id: {n.get('construct_id','')}  | "
        f"维度:{n.get('n_dims',0)} 题:{n.get('n_items',0)} 状态:{n.get('status','')}",
    ]
    if n.get("reference_used"):
        ru = n["reference_used"]
        # reference_used 是「条目文本的取用文献」，不是量表原始出处，故不称「出处」
        out.append(f"  取用文献: {ru}{'…' if len(ru) >= 80 else ''}")
    # 计分方式在原始导出中即缺失时显式告知，不静默省略：
    # 省略会让使用者以为该量表无需计分，或误把「未载明」当作「已载明」。
    if n.get("has_scoring") is False:
        out.append("  计分方式: （原文未覆盖）该量表各维度的计分方式在原始资料中未载明，"
                   "使用前须回原始文献核对，不臆造计分规则。")
    if n.get("note"):
        out.append(f"  备注: {n['note']}")
    return "\n".join(out)


def _render_full(rec, n):
    for d in rec.get("dimensions", []):
        rng = d.get("item_range")
        rng_s = ""
        if isinstance(rng, (list, tuple)) and len(rng) >= 2:
            rng_s = f" {rng[0]}-{rng[1]}"
        sc = f", {d.get('scoring')}" if d.get("scoring") else ", （计分方式未载明）"
        print(f"  维度: {d.get('name_zh','')}/{d.get('name_en','')}"
              f" ({d.get('item_count',0)}题{rng_s}{sc})")
    items = rec.get("items", [])
    for it in items[:_ITEM_SHOW]:
        mark = "  [反向计分]" if it.get("reverse") else ""
        print(f"    {it.get('no','')}. {it.get('text','')[:64]}{mark}")
    if len(items) > _ITEM_SHOW:
        print(f"    ...(共 {len(items)} 题)")
    # 反向题必须显式汇总：漏掉会让使用者按正向计分，直接得到错误的量表得分。
    rev_nos = [str(it.get("no", "")) for it in items if it.get("reverse")]
    if rev_nos:
        print(f"  [反向计分题] 共 {len(rev_nos)} 题：第 {'、'.join(rev_nos)} 题（计分前须反向处理）")
    # 量表原始出处：主理人「引用四铁律·不编造参考文献」要求以 background 为准，
    # 该字段此前在任何文本模式入口都取不到，成员只能拿 reference_used（取用文献）
    # 冒出处——此处补渲染，并显式标注截断。
    bg = (rec.get("background") or "").strip()
    if bg:
        if len(bg) > _BG_LIMIT:
            bg = bg[:_BG_LIMIT].rstrip() + f"……（原始出处原文较长，此处按 {_BG_LIMIT} 字符上限截断，完整原文见条目 background 字段）"
        print(f"  原始出处: {bg}")
    else:
        print("  原始出处: （原文未覆盖）——正式引用前须回原始文献核对，不得以取用文献替代")


def main():
    ap = argparse.ArgumentParser(description="OBHRM 量表库检索")
    ap.add_argument("query", help="关键词 / construct_id / scale_id(如 S001)")
    ap.add_argument("--full", action="store_true", help="输出完整条目(含 items)")
    ap.add_argument("--limit", type=positive_int, default=10,
                    help="最多展示条数（>=1 的整数，默认 10）")
    ap.add_argument("--json", action="store_true", help="输出原始 JSON")
    args = ap.parse_args()

    return query_library(
        idx_path=IDX,
        records_dir=SCALES,
        id_field="scale_id",
        id_prefix="sS",
        search_fields=["scale_id", "construct_id", "variable_en", "variable_zh", "title"],
        label="量表库",
        noun_key="scales",
        query=args.query,
        full=args.full,
        limit=args.limit,
        as_json=args.json,
        render_header=_render_header,
        render_full=_render_full,
    )


if __name__ == "__main__":
    sys.exit(main())
