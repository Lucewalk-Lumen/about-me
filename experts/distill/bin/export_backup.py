#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage 6.1 EXPORT 导出脚本（agent 可调用的低层原语）

把资产库打包成 backup-YYYYMMDD-HHMMSS.zip，写到用户指定的备份目录。
仅使用 Python 标准库，因此在没有 `zip` 命令的系统（如 Windows 默认环境）
上同样可用。归档顶层固定为 `distill-assets/`，与本包的恢复脚本对接。

不导出（按设计排除）：版本备份目录、内部计数器、临时文件。

用法:
  python3 bin/export_backup.py                          # 输出到 ~/Documents/distill-backup/
  python3 bin/export_backup.py --out-dir <目录>          # 自定义备份目录
  python3 bin/export_backup.py --assets <资产库目录>      # 自定义资产库
  python3 bin/export_backup.py --dry-run                # 只列将打包的内容
  python3 bin/export_backup.py --list                   # 只列已有备份

退出码:
  0 = 成功
  1 = 资产库不存在
  2 = 参数/路径错误
"""
from __future__ import annotations

import argparse
import os
import sys
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import assets_lib as A  # noqa: E402
from audit_chain import append_event  # noqa: E402
from pkgmeta import load_pkg_meta  # noqa: E402

TZ8 = timezone(timedelta(hours=8))

# 归档时需要排除的运行时内部状态（相对资产库根的路径前缀）
SKIP_PREFIXES = ('distill-versions/',)
SKIP_NAMES = ('.counter', '.DS_Store', 'Thumbs.db')
SKIP_DIRS = ('__pycache__',)
SKIP_SUFFIXES = ('.pyc', '.pyo', '.swp', '.swo', '~')


def _iter_members(assets_dir: Path):
    """列出应进入备份的文件（相对资产库根，使用 POSIX 分隔符）。"""
    out = []
    for f in sorted(assets_dir.rglob('*')):
        if not f.is_file():
            continue
        rel = f.relative_to(assets_dir).as_posix()
        parts = rel.split('/')
        if any(rel.startswith(p) for p in SKIP_PREFIXES):
            continue
        if any(p in SKIP_DIRS for p in parts[:-1]) or parts[-1] in SKIP_DIRS:
            continue
        if parts[-1] in SKIP_NAMES or parts[-1].endswith(SKIP_SUFFIXES):
            continue
        out.append(rel)
    return out


def _pick_name(out_dir: Path) -> str:
    base = 'backup-%s' % datetime.now().strftime('%Y%m%d-%H%M%S')
    name = base + '.zip'
    i = 1
    while (out_dir / name).exists():
        i += 1
        name = '%s-%d.zip' % (base, i)
    return name


def main():
    p = argparse.ArgumentParser(description='导出蒸馏资产库备份 (Stage 6.1 EXPORT)')
    p.add_argument('--assets', default=os.environ.get('DISTILL_ASSETS_DIR',
                   str(Path.home() / '.workbuddy' / 'distill-assets')),
                   help='资产库目录 (默认 ~/.workbuddy/distill-assets，可用 DISTILL_ASSETS_DIR 覆盖)')
    p.add_argument('--out-dir', default=os.environ.get('DISTILL_BACKUP_DIR',
                   str(Path.home() / 'Documents' / 'distill-backup')),
                   help='备份输出目录 (默认 ~/Documents/distill-backup，可用 DISTILL_BACKUP_DIR 覆盖)')
    p.add_argument('--dry-run', action='store_true', help='只列将打包的内容，不实际打包')
    p.add_argument('--list', action='store_true', help='只列已有备份，不打包')
    args = p.parse_args()

    assets_dir = Path(args.assets).expanduser()
    out_dir = Path(args.out_dir).expanduser()

    if args.list:
        if not out_dir.is_dir():
            print('备份目录不存在: %s' % out_dir, file=sys.stderr)
            return 2
        zips = sorted(out_dir.glob('backup-*.zip'), key=lambda x: x.name, reverse=True)
        print('备份目录: %s' % out_dir)
        print('共 %d 个备份，按时间戳从新到旧:' % len(zips))
        for z in zips:
            print('  %8.1f KB  %s' % (z.stat().st_size / 1024, z.name))
        return 0

    if not assets_dir.is_dir():
        print('[X] 资产库不存在: %s' % assets_dir, file=sys.stderr)
        print('    先跑一次蒸馏产出资产，或用 --assets 指定资产库目录', file=sys.stderr)
        return 1

    rels = _iter_members(assets_dir)
    total = sum((assets_dir / r).stat().st_size for r in rels)
    print('资产库: %s' % assets_dir)
    print('将打包 %d 个文件，合计 %.1f KB' % (len(rels), total / 1024))
    if not (assets_dir / 'capsules' / 'capsules.json').exists():
        print('   [!] 资产库内没有 capsules/capsules.json（尚未产出过胶囊）——备份仍会生成，'
              '但恢复后只会带回操作模式等既有内容')

    if args.dry_run:
        for r in rels:
            print('  %8d 字节  distill-assets/%s' % ((assets_dir / r).stat().st_size, r))
        print('【DRY RUN】未实际打包')
        return 0

    out_dir.mkdir(parents=True, exist_ok=True)
    pack_name = _pick_name(out_dir)
    out_path = out_dir / pack_name

    with zipfile.ZipFile(out_path, 'w', zipfile.ZIP_DEFLATED) as z:
        for r in rels:
            z.write(assets_dir / r, 'distill-assets/' + r)

    size_kb = out_path.stat().st_size / 1024
    print('[OK] 备份已生成: %s (%.1f KB, %d 文件)' % (out_path, size_kb, len(rels)))

    # 审计链（type=export）：备份新鲜度守卫据此判断"上次导出"，因此必须记录
    try:
        ev_path = assets_dir / 'events.jsonl'
        prev_hash = ''
        if ev_path.exists():
            lines = [l for l in ev_path.read_text(encoding='utf-8').splitlines() if l.strip()]
            if lines:
                import json as _json
                prev_hash = _json.loads(lines[-1]).get('hash', '')
        evt = {
            'ts': datetime.now(TZ8).isoformat(timespec='seconds'),
            'type': 'export',
            'actor': os.environ.get('DISTILL_AUTHOR') or load_pkg_meta()['author_name'],
            'msg': '导出备份 %s (%d 文件)' % (out_path.name, len(rels)),
            'pack_path': out_path.name,   # 只存文件名，避免审计链暴露主目录绝对路径
            'files': len(rels),
            'zip_bytes': out_path.stat().st_size,
            'sha256': A.sha256_file(out_path),
            'prev_hash': prev_hash,
        }
        append_event(ev_path, evt)
    except Exception as e:
        print('[!]  审计链写入失败 (备份已生成, 不影响数据): %s' % e, file=sys.stderr)

    return 0


if __name__ == '__main__':
    sys.exit(main())
