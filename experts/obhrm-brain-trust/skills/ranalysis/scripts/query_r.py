#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OBHRM R 分析库检索入口（ranalysis）。

检索内核由共享模块 `skills/bridge/kernel/library_query.py` 提供，
theory / scale / ranalysis 三个技能复用同一份匹配、安全边界、
JSON 契约逻辑，本文件只做领域参数 + 渲染回调的薄包装。

用法:
  python3 query_r.py "regression"                 # 关键词(中/英)检索方法
  python3 query_r.py "8.1" --full                 # method_no 精确 + 打印脚本路径与门控
  python3 query_r.py "13.1"                       # 编号前缀直查：命中 13.1.1/13.1.2 … 等子级
  python3 query_r.py "中介" --limit 5
  python3 query_r.py "1.1" --json                  # 输出原始 JSON

匹配优先级: method_no 精确(8.1) > method_no 前缀(13.1 命中 13.1.x 子级) > title/stage/use_condition 包含(大小写不敏感)。
编号查询按「精确相等 + 点分层级前缀」比较——"8.1" 只命中自身，"13.1" 命中 13.1.x 全部子级；不做裸子串包含（避免 "8.1" 误中 "18.1"）。
注: 每个 R 脚本遵循 G3 数据前置门禁(须传数据文件), 见 use_condition; G4 环境探测 ensure_pkg 不代装。
"""
import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.normpath(os.path.join(HERE, ".."))
IDX = os.path.join(SKILL_ROOT, "knowledge", "_r_index.json")

_KERNEL = os.path.normpath(os.path.join(HERE, "..", "..", "bridge", "kernel"))
if _KERNEL not in sys.path:
    sys.path.insert(0, _KERNEL)
from library_query import query_library, positive_int, under, display_path  # noqa: E402

RE_METHOD_NO = re.compile(r"^\d+(\.\d+)*$")
_HEAD_LINES = 12   # 按行读取脚本头，避免按字节截断多字节 UTF-8


def _display_base():
    """输出相对路径的基准：技能布局取「skills/」的上级（专家团根），平铺布局取库根。"""
    lib_root = os.path.dirname(SKILL_ROOT)
    if os.path.basename(lib_root) == "skills":
        return os.path.dirname(lib_root)
    return lib_root


def _script_path(node):
    """解析脚本绝对路径；索引 file 字段越出技能根时返回 None（按「未找到」处理）。

    _r_index.json 的 file 属包内但用户可编辑的数据，os.path.join 允许 `../`
    逃出技能根、绝对路径更是直接吞掉 root，造成任意文件读取，故必须做包含性校验。
    """
    rel = node.get("file", "")
    if not rel:
        return None
    p = os.path.join(SKILL_ROOT, rel)
    return p if under(p, SKILL_ROOT) else None


def _render_header(n):
    out = [f"\n● {n.get('method_no','')}  {n.get('title','')}  [段:{n.get('stage','')}]"]
    if n.get("deps"):
        out.append(f"  依赖: {', '.join(n['deps'])}")
    if n.get("use_condition"):
        out.append(f"  门控(G3数据前置): {n['use_condition']}")
    return "\n".join(out)


def _render_full(rec, n):
    p = _script_path(n)
    rel = display_path(p, _display_base()) if p else ""
    if not rel:
        # 区分「索引没给 file」与「file 越界已拒绝」，否则安全拒绝会被误读成数据缺失
        rel = ("(索引 file 字段越出技能根，已拒绝读取)" if (n.get("file") or "")
               else "(索引未提供 file 字段)")
        print(f"  脚本路径(未找到): {rel}")
        return
    if not os.path.exists(p):
        print(f"  脚本路径(未找到): {rel}")
        return
    print(f"  脚本路径: {rel}")
    try:
        with open(p, encoding="utf-8", errors="replace") as f:
            head = "".join(f.readlines()[:_HEAD_LINES])
    except OSError as e:
        print(f"  脚本头: [不可读 {type(e).__name__}]")
        return
    print(f"  脚本头:\n{head}")


def main():
    ap = argparse.ArgumentParser(description="OBHRM R 分析库检索")
    ap.add_argument("query", help="关键词 / method_no(如 8.1)")
    ap.add_argument("--full", action="store_true", help="打印脚本路径与门控说明")
    ap.add_argument("--limit", type=positive_int, default=10,
                    help="最多展示条数（>=1 的整数，默认 10）")
    ap.add_argument("--json", action="store_true", help="输出原始 JSON")
    args = ap.parse_args()

    # R 方法库「索引即记录」：无逐条 .json，故 records_dir=None；
    # 方法条目不带 verified/draft 生命周期，故关掉覆盖率面板。
    return query_library(
        idx_path=IDX,
        records_dir=None,
        id_field="method_no",
        id_regex=RE_METHOD_NO,
        search_fields=["method_no", "title", "stage", "use_condition"],
        label="R 库",
        noun_key="methods",
        query=args.query,
        full=args.full,
        limit=args.limit,
        as_json=args.json,
        use_coverage=False,
        render_header=_render_header,
        render_full=_render_full,
    )


if __name__ == "__main__":
    sys.exit(main())
