#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""资产检索 / 结构校验 / 索引重建（读多写少，默认不写任何文件）。

用法:
  python3 bin/query_capsules.py 关键词 [关键词2 ...]   # 按关键词检索（默认前 5 条）
  python3 bin/query_capsules.py --all                  # 列出全部（简表）
  python3 bin/query_capsules.py --id C003              # 展示单条全文（六段）
  python3 bin/query_capsules.py --check                # 结构校验
  python3 bin/query_capsules.py --rebuild-index        # 由胶囊库重建 index.md

选项:
  --assets DIR   资产库目录（默认 ~/.workbuddy/distill-assets，可用 DISTILL_ASSETS_DIR 覆盖）
  --top N        检索返回条数（默认 5）
  --json         以 JSON 输出检索结果（供程序消费）

退出码:
  0 = 有结果 / 校验通过（可能带 [!] 提示，提示不阻断）
  1 = 无结果 / 校验发现**结构错误**
  2 = 参数或资产库错误
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import assets_lib as A  # noqa: E402


def _load(args):
    assets = Path(args.assets).expanduser()
    if not assets.is_dir():
        print('[X] 资产库目录不存在: %s' % assets, file=sys.stderr)
        print('    （首次使用请先跑一次蒸馏，或用 --assets 指定资产库目录）', file=sys.stderr)
        return None, None
    try:
        caps, path = A.load_capsules(assets)
    except FileNotFoundError as e:
        print('[X] 胶囊库不存在: %s' % e, file=sys.stderr)
        return None, None
    except (ValueError, json.JSONDecodeError) as e:
        print('[X] 胶囊库无法解析: %s' % e, file=sys.stderr)
        return None, None
    return caps, assets


def _short(c: dict) -> str:
    return '[%s] %s  %s' % (c.get('type', '?'), c.get('id', '?'), A.first_line(c))


def _full(c: dict) -> str:
    out = ['=== %s ===' % c.get('id', '?')]
    out.append('类型: %s' % c.get('type', '?'))
    out.append('出处: %s' % A._field_text(c, 'source'))
    out.append('标签: %s' % A._tag_text(c))
    out.append('')
    for s, title in (('R', 'R 原文'), ('I', 'I 自述'), ('A1', 'A1 已发生用例'),
                     ('A2', 'A2 未来触发'), ('E', 'E 可执行步骤'), ('B', 'B 边界')):
        v = c.get(s, '')
        if isinstance(v, (list, tuple)):
            body = '\n'.join('  %d) %s' % (i, x) for i, x in enumerate(v, 1))
        else:
            body = '  %s' % v
        out.append('--- %s ---' % title)
        out.append(body)
    return '\n'.join(out)


def main():
    p = argparse.ArgumentParser(description='蒸馏资产检索 / 结构校验 / 索引重建')
    p.add_argument('keywords', nargs='*', default=[], help='检索关键词（空格分隔，全部命中才算相关则用 --all-required）')
    p.add_argument('--assets', default=os.environ.get('DISTILL_ASSETS_DIR', str(Path.home() / '.workbuddy' / 'distill-assets')),
                   help='资产库目录（默认 ~/.workbuddy/distill-assets）')
    p.add_argument('--all', action='store_true', help='列出全部资产（简表）')
    p.add_argument('--id', default='', help='展示指定 id 的全文')
    p.add_argument('--check', action='store_true', help='结构校验（不检索）')
    p.add_argument('--rebuild-index', action='store_true', help='由胶囊库重建 index.md')
    p.add_argument('--top', type=int, default=5, help='检索返回条数（默认 5）')
    p.add_argument('--json', action='store_true', help='JSON 输出')
    args = p.parse_args()

    caps, assets = _load(args)
    if caps is None:
        return 2

    if args.check:
        errors, notices = A.validate_capsules_report(caps)
        print('资产库: %s' % assets)
        print('胶囊数: %d' % len(caps))
        if errors:
            print('[X] 结构校验发现 %d 处问题:' % len(errors))
            for x in errors:
                print('   - %s' % x)
            for n in notices:
                print('[!] 另有提示: %s' % n)
            return 1
        print('[OK] 结构校验通过（%d 条：必需字段、六段正文、E 段可解析、id 无重复）' % len(caps))
        for n in notices:
            print('[!] %s' % n)
        return 0

    if args.rebuild_index:
        text = A.render_index(caps, source_note='来源：%s' % assets.name)
        targets = [assets / 'index.md']
        if (assets / 'capsules' / 'index.md').exists():
            targets.append(assets / 'capsules' / 'index.md')
        for t in targets:
            wrote = A.write_index(t, text)
            print('[%s] %s' % ('OK' if wrote else 'SKIP', t) +
                  ('' if wrote else '（已存在且非脚本生成，未覆盖；如需强制覆盖请先备份后手动替换）'))
        return 0

    if args.id:
        hit = [c for c in caps if str(c.get('id')) == args.id]
        if not hit:
            print('[X] 未找到 id=%s（共 %d 条）' % (args.id, len(caps)), file=sys.stderr)
            return 1
        print(_full(hit[0]))
        return 0

    if args.all or not args.keywords:
        if not args.keywords and not args.all:
            p.print_help()
            return 0
        print('资产库: %s' % assets)
        print('共 %d 条:' % len(caps))
        for c in caps:
            print('  %s' % _short(c))
        return 0

    results = A.search(caps, args.keywords)[: max(1, args.top)]
    if args.json:
        print(json.dumps([{'score': s, 'why': w, 'capsule': c} for s, w, c in results],
                         ensure_ascii=False, indent=2))
        return 0 if results else 1
    if not results:
        print('[X] 无命中（关键词：%s）；可先用 --all 看全部 %d 条' % (' '.join(args.keywords), len(caps)),
              file=sys.stderr)
        return 1
    print('资产库: %s  |  关键词: %s  |  命中 %d 条，显示前 %d 条'
          % (assets, ' '.join(args.keywords), len(A.search(caps, args.keywords)), len(results)))
    print()
    for i, (score, why, c) in enumerate(results, 1):
        print('%d) %s' % (i, _short(c)))
        print('   何时用：%s' % A._field_text(c, 'A2').replace('\n', ' ')[:120])
        print('   命中：%s' % why)
        print('   取全文：python3 bin/query_capsules.py --id %s' % c.get('id'))
        print()
    return 0


if __name__ == '__main__':
    sys.exit(main())
