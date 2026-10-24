#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""inject_by_anchor.py — 按锚点向 Markdown 正文注入内容（支持批量、从下往上）。

核心原则：同一文件多处注入时，按锚点行号从大到小（从下往上）依次插入，
避免行号偏移导致锚点失效。

用法：
  # 单次注入：在锚点前/后插入内容文件
  python3 inject_by_anchor.py inject <md_path> <anchor> <content_path> \
      [--position before|after] [--line-before N] [--line-after N] [--occurrence first|last|all]

  # 批量注入（推荐）：JSON 描述多处注入，自动从下往上执行
  python3 inject_by_anchor.py batch <md_path> <injections.json> [--dry-run]

injections.json 示例：
[
  {"anchor": "## 思政融入", "line_before": 400, "content": "ch6_inject.md", "position": "before"},
  {"anchor": "## 第 19 章", "content": "opc_inject.md", "position": "before"}
]

字段说明：
  anchor        必填，锚点文本（章节标题、`## 思政融入`、`---` 等稳定标记）
  content       必填，待注入内容文件路径
  position      可选，before=插到锚点之前（默认），after=插到锚点之后
  line_before   可选，只匹配行号 < N 的锚点（用于限定唯一性）
  line_after    可选，只匹配行号 > N 的锚点
  occurrence    可选，first|last|all，默认 first
"""

import argparse
import json
import sys


def read_lines(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.readlines()


def read_content(path):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    if not content.endswith('\n'):
        content += '\n'
    return content


def find_anchor(lines, anchor, occurrence='first', line_before=None, line_after=None):
    """Return list of 0-based line indices matching the anchor, after applying constraints."""
    matches = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        # 精确匹配锚点行；若锚点以 # 开头，则按标题行匹配
        if anchor.startswith('#'):
            hit = stripped.startswith(anchor)
        else:
            hit = (stripped == anchor) or (stripped.startswith(anchor + ' ')) or (stripped.startswith(anchor + '：'))
        if not hit:
            continue
        if line_before is not None and i >= line_before:
            continue
        if line_after is not None and i <= line_after:
            continue
        matches.append(i)
    if not matches:
        return []
    if occurrence == 'first':
        return [matches[0]]
    if occurrence == 'last':
        return [matches[-1]]
    return matches


def inject_single(md_path, anchor, content_path, position='before', line_before=None,
                  line_after=None, occurrence='first', dry_run=False):
    lines = read_lines(md_path)
    content = read_content(content_path)
    indexes = find_anchor(lines, anchor, occurrence=occurrence,
                          line_before=line_before, line_after=line_after)
    if not indexes:
        print(f"[SKIP] anchor not found: {anchor} (constraints: <{line_before} / >{line_after})")
        return 0
    n = len(content.split('\n')) - 1
    for idx in sorted(indexes, reverse=True):
        insert_at = idx + 1 if position == 'after' else idx
        lines.insert(insert_at, content)
        print(f"[OK] injected {content_path} ({n} lines) {position} '{anchor}' at line {insert_at + 1}")
    if not dry_run:
        with open(md_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        print(f"[SAVED] {md_path} ({len(lines)} lines)")
    else:
        print("[DRY-RUN] no file written")
    return len(indexes)


def batch(md_path, injections_path, dry_run=False):
    with open(injections_path, 'r', encoding='utf-8') as f:
        injections = json.load(f)
    lines = read_lines(md_path)

    # 解析所有注入点（按当前行号），然后按行号降序插入 = 从下往上，避免偏移
    plan = []
    for inj in injections:
        anchor = inj['anchor']
        content = read_content(inj['content'])
        indexes = find_anchor(lines, anchor,
                              occurrence=inj.get('occurrence', 'first'),
                              line_before=inj.get('line_before'),
                              line_after=inj.get('line_after'))
        if not indexes:
            print(f"[SKIP] anchor not found: {anchor}")
            continue
        for idx in indexes:
            insert_at = idx + 1 if inj.get('position', 'before') == 'after' else idx
            plan.append((insert_at, content, anchor))

    plan.sort(key=lambda x: x[0], reverse=True)  # 从下往上
    for insert_at, content, anchor in plan:
        lines.insert(insert_at, content)
        print(f"[OK] injected {len(content.splitlines())} lines before line {insert_at + 1} (anchor '{anchor}')")

    if not dry_run:
        with open(md_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        print(f"[SAVED] {md_path} ({len(lines)} lines, {len(plan)} injections)")
    else:
        print(f"[DRY-RUN] {len(plan)} injections planned, no file written")


def main():
    parser = argparse.ArgumentParser(description='按锚点向 Markdown 注入内容（从下往上避免行号偏移）')
    sub = parser.add_subparsers(dest='cmd', required=True)

    p_inject = sub.add_parser('inject', help='单次注入')
    p_inject.add_argument('md_path', help='目标 md 文件')
    p_inject.add_argument('anchor', help='锚点文本')
    p_inject.add_argument('content', help='内容文件')
    p_inject.add_argument('--position', choices=['before', 'after'], default='before')
    p_inject.add_argument('--line-before', type=int, default=None, help='只匹配行号 < N 的锚点')
    p_inject.add_argument('--line-after', type=int, default=None, help='只匹配行号 > N 的锚点')
    p_inject.add_argument('--occurrence', choices=['first', 'last', 'all'], default='first')
    p_inject.add_argument('--dry-run', action='store_true')

    p_batch = sub.add_parser('batch', help='批量注入（自动从下往上）')
    p_batch.add_argument('md_path', help='目标 md 文件')
    p_batch.add_argument('injections', help='注入描述 JSON 文件')
    p_batch.add_argument('--dry-run', action='store_true')

    args = parser.parse_args()
    if args.cmd == 'inject':
        inject_single(args.md_path, args.anchor, args.content,
                      position=args.position, line_before=args.line_before,
                      line_after=args.line_after, occurrence=args.occurrence,
                      dry_run=args.dry_run)
    else:
        batch(args.md_path, args.injections, dry_run=args.dry_run)


if __name__ == '__main__':
    sys.exit(main())
