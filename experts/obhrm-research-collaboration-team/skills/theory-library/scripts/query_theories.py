#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OBHRM 理论库检索入口（theory-library）。

检索内核由共享模块 `skills/obhrm-bridge/kernel/library_query.py` 提供，
theory-library / scale-library / r-analysis 三个技能复用同一份匹配、安全边界、
JSON 契约与覆盖率逻辑，本文件只做领域参数 + 渲染回调的薄包装。

用法:
  python3 query_theories.py "stakeholder"          # 关键词(中/英/构念)检索
  python3 query_theories.py "T001" --full          # theory_id 精确 + 完整记录
  python3 query_theories.py "社会交换" --limit 5
  python3 query_theories.py "T001" --json           # 输出原始 JSON

匹配优先级: theory_id 精确(T001) > construct_id/理论名(中/英) 包含(大小写不敏感)。
全角 Ｔ００１ 与半角 T001 等价；编号查询不做子串匹配。
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KNOW = os.path.normpath(os.path.join(HERE, "..", "knowledge"))
IDX = os.path.join(KNOW, "_theory_index.json")
THEORIES = os.path.join(KNOW, "theories")

_KERNEL = os.path.normpath(os.path.join(HERE, "..", "..", "obhrm-bridge", "kernel"))
if _KERNEL not in sys.path:
    sys.path.insert(0, _KERNEL)
from library_query import query_library, norm, positive_int, trunc_hint  # noqa: E402

# 四段正文：内容 / 作用机制 / 结构 / 应用。缺一段都会在输出里显式标注「原文未覆盖」。
_SEGMENTS = (("what", "【内容】"), ("processes", "【作用机制】"),
             ("structure", "【结构】"), ("application", "【应用】"))


def _render_header(n):
    flags = "".join([
        " [WHAT]" if n.get("has_what") else "",
        " [PROC]" if n.get("has_processes") else "",
        " [STRUCT]" if n.get("has_struct") else "",
        " [APP]" if n.get("has_app") else "",
    ])
    out = [
        f"\n● {n['theory_id']}  {n.get('name_zh','')} / {n.get('name_en','')}{flags}",
        f"  construct_id: {n.get('construct_id','')}  | "
        f"参考文献:{n.get('n_refs',0)} 状态:{n.get('status','')}",
    ]
    if n.get("note"):
        out.append(f"  备注: {n['note']}")
    if "内源补足" in (n.get("note") or ""):
        out.append("  ⚠️ [内源补足警示] 本条正文部分由内部教材 D1 自动补足，非原始同行评议文献，"
                   "补足内容不得作为经核验的权威引用；以 status 字段判定可信度。")
    return "\n".join(out)


def _render_full(rec, n):
    for key, label in _SEGMENTS:
        v = rec.get(key)
        if isinstance(v, list):
            for item in v[:4]:
                t = item.get("text", "") if isinstance(item, dict) else str(item)
                print(f"  {key}: {t[:80]}{trunc_hint(t)}")
            # 消除静默截断：显示上限之外仍有内容时必须写明
            if len(v) > 4:
                print(f"  {key}: ...（共 {len(v)} 段，此处仅显示前 4 段）")
        elif isinstance(v, dict):
            print(f"  {key}: {json.dumps(v, ensure_ascii=False)[:120]}")
        elif v:
            print(f"  {key}: {str(v)[:120]}{trunc_hint(v)}")
        else:
            # 空段不得留白：不标注就会让使用者误以为原文没有这一段
            print(f"  {key}: （原文未覆盖）")
    refs = rec.get("references")
    if refs:
        print(f"  【文献】{str(refs)[:200]}{'…' if len(str(refs)) > 200 else ''}")


def main():
    ap = argparse.ArgumentParser(description="OBHRM 理论库检索")
    ap.add_argument("query", help="关键词 / construct_id / theory_id(如 T001)")
    ap.add_argument("--full", action="store_true", help="输出完整记录（四段正文 + 文献）")
    ap.add_argument("--limit", type=positive_int, default=10,
                    help="最多展示条数（>=1 的整数，默认 10）")
    ap.add_argument("--json", action="store_true", help="输出原始 JSON")
    args = ap.parse_args()

    return query_library(
        idx_path=IDX,
        records_dir=THEORIES,
        id_field="theory_id",
        id_prefix="tT",
        search_fields=["theory_id", "construct_id", "name_en", "name_zh"],
        label="理论库",
        noun_key="theories",
        query=args.query,
        full=args.full,
        limit=args.limit,
        as_json=args.json,
        render_header=_render_header,
        render_full=_render_full,
    )


if __name__ == "__main__":
    sys.exit(main())
