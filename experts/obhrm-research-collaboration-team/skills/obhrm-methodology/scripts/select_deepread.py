#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""select_deepread.py — 从已读文献中选取论文进行「精读」。

本脚本：
  --all      全量精读（选中所有已读文献）
  --limit N  可配置上限（默认全量；给出 N 则按完整度排序取前 N 篇）
  --topic T  按主题关键词过滤（标题/摘要命中，可多次指定）
输出 deepread.md：选中论文的 标题 / 笔记路径 / 全文路径 / 抽取摘要，供精读 agent 使用。

输入可为：
  - ingest 目录（含 notes/ 与 texts/）：复用 build_readings 抽取逻辑
  - 已构建的 READINGS.md：直接解析其中的 `### ` 摘要块
"""
import argparse
import os
import re
import sys

# 复用同目录下的 build_readings（若作为脚本直接运行，确保能 import）
# 使用 append 而非 insert(0)，避免目录内同名模块覆盖标准库。
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.append(_HERE)

import build_readings as br  # noqa: E402
from obhrm_research_base.core.safe_path import resolve_safe_output  # noqa: E402


def _load_entries(input_path):
    """从 ingest 目录或 READINGS.md 载入文献条目列表。"""
    if os.path.isdir(input_path):
        notes = os.path.join(input_path, "notes")
        if os.path.isdir(notes):
            return br.build_readings(input_path)
        raise SystemExit("目录不含 notes/，无法作为 ingest 产物：%s" % input_path)
    # 视为 READINGS.md：解析 ### 标题块
    return _parse_readings_md(input_path)


def _parse_readings_md(path):
    """解析 build_readings 产出的 READINGS.md，重建条目列表。"""
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    entries = []
    # 切分 ### N. Title 块
    blocks = re.split(r"(?m)^###\s+\d+\.\s+", text)
    # 首个块是文献条目区，丢弃；其余每个块对应一篇
    for blk in blocks[1:]:
        title = blk.splitlines()[0].strip() if blk.strip() else "Untitled"
        missing = "**缺失**" in blk
        m_src = re.search(r"-\s*来源:\s*`?(.*?)`?\s*$", blk)
        m_txt = re.search(r"-\s*全文:\s*`?(.*?)`?\s*$", blk)
        m_abs = re.search(r"-\s*摘要:\s*(.*?)(?=\n- |\Z)", blk, re.S)
        entries.append({
            "title": title,
            "author": "",
            "year": "",
            "source": m_src.group(1) if m_src else "",
            "text_path": m_txt.group(1) if m_txt else "",
            "abstract": (m_abs.group(1).strip() if m_abs else "") if not missing else "",
            "missing": missing,
            "ref_line": title,
        })
    return entries


def _completeness(e):
    """完整度评分：有全文 + 有摘要 > 仅全文 > 缺失。"""
    score = 0
    if not e["missing"] and e.get("text_path"):
        score += 2
    if e.get("abstract"):
        score += 1
    return score


def select(entries, all_flag, limit, topics):
    """按参数筛选精读论文。"""
    if topics:
        lowered = [t.lower() for t in topics]
        entries = [e for e in entries
                   if any(t in (e["title"] + " " + (e.get("abstract") or "")).lower()
                          for t in lowered)]
    if all_flag:
        return entries
    if topics and limit is None:
        # 有主题过滤但无 --all/--limit：返回全部命中（不被 31 限制）
        return entries
    # 无 --all：默认全量；--limit N 则按完整度排序取前 N
    if limit is None:
        return entries
    ranked = sorted(entries, key=_completeness, reverse=True)
    return ranked[:limit]


def write_deepread(entries, out_path, opts):
    lines = ["# 精读清单（deepread）", ""]
    lines.append("> 由 select_deepread.py 生成；"
                 "模式：%s。" % opts)
    if not entries:
        lines.append("")
        lines.append("_无匹配文献。_")
    for i, e in enumerate(entries, 1):
        lines.append("")
        lines.append("## %d. %s" % (i, e["title"]))
        if e["missing"]:
            lines.append("- 全文: **缺失**（跳过精读或先补齐 PDF）")
        else:
            lines.append("- 全文: `%s`" % e["text_path"])
        lines.append("- 来源: `%s`" % (e.get("source") or "（未记录）"))
        lines.append("- 摘要: %s" % (e.get("abstract") or "（未能抽取）"))
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description="选取论文进行精读")
    ap.add_argument("input", help="ingest 目录 或 已构建的 READINGS.md")
    ap.add_argument("--out", default=None, help="输出路径（默认 <input 同级>/deepread.md）")
    ap.add_argument("--all", action="store_true",
                    help="全量精读：选中所有已读文献")
    ap.add_argument("--limit", type=int, default=None,
                    help="上限篇数（按完整度排序取前 N；默认全量）")
    ap.add_argument("--topic", action="append", default=[], metavar="KEYWORD",
                    help="按主题关键词过滤（可多次指定）")
    args = ap.parse_args(argv)

    entries = _load_entries(args.input)
    if not entries:
        raise SystemExit("未载入任何文献条目。")

    selected = select(entries, args.all, args.limit, args.topic)
    if args.out:
        # 显式输出路径：校验落在允许基目录（cwd）之内，超出范围即拒绝写入
        out = str(resolve_safe_output(args.out, base=os.getcwd()))
    else:
        # 默认输出：与输入同级目录
        base_dir = (os.path.dirname(os.path.abspath(args.input))
                    if os.path.isfile(args.input) else os.path.abspath(args.input))
        out = os.path.join(base_dir, "deepread.md")
        out = str(resolve_safe_output(out, base=base_dir))

    opts = "全量精读(--all)" if args.all else (
        "主题过滤(%s)" % ",".join(args.topic) if args.topic else "全量（无上限）")
    if args.limit is not None:
        opts += " + 上限 %d" % args.limit

    write_deepread(selected, out, opts)
    print("已从 %d 篇中选取 %d 篇精读 -> %s" % (len(entries), len(selected), out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
