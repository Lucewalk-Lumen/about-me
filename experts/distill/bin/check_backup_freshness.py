#!/usr/bin/env python3
"""
Stage 0 备份新鲜度守卫 — 可独立运行的检查脚本
不引入定时器, 不调度, 只在用户主动触发蒸馏时被调用

用法:
  python3 bin/check_backup_freshness.py                  # 默认 3/7 天阈值
  python3 bin/check_backup_freshness.py --warn 2 --crit 5  # 自定义阈值
  python3 bin/check_backup_freshness.py --quiet          # 仅在超阈值时输出（"从未备份过"等异常状态仍会输出）
  python3 bin/check_backup_freshness.py --exit-code      # 退出码: 0=正常, 1=提醒, 2=强烈建议

退出码配合 shell 钩子:
  * 0 = 正常
  * 1 = 距上次导出 >= warn 天
  * 2 = 距上次导出 >= crit 天
  * 3 = 从未导出过

说明: 「上次导出」取 events.jsonl 中**最后一次** type=export 事件——脚本遍历
     全文件取最后一条，不假定它正好落在文件末行。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Optional
from datetime import datetime, timezone, timedelta
from pathlib import Path


# 记录惯例：事件时间戳统一 +08:00（见 restore_backup.py / distill.md）
TZ8 = timezone(timedelta(hours=8))

# 用户可见提示语：多处复用，收敛为一处定义，避免同一句散落多份后各自漂移
HINT_EXPORT = '   一句话「导出蒸馏资产」即可触发 EXPORT'


def find_last_export(assets_dir: Path) -> Optional[dict]:
    """从 events.jsonl 找最近一次 type=export 事件 (append-only 权威记录, 不信 zip mtime)"""
    ev = assets_dir / 'events.jsonl'
    if not ev.exists():
        return None
    last = None
    for line in ev.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            if obj.get('type') == 'export':
                last = obj
        except json.JSONDecodeError:
            continue
    return last


def parse_ts(ts: str) -> datetime:
    """解析 ISO 8601 时间戳 (兼容 +08:00 与无时区)"""
    # 去掉 Z 后缀
    ts = ts.replace('Z', '+00:00')
    try:
        dt = datetime.fromisoformat(ts)
    except ValueError:
        # 退化: 当作 +08:00（与记录惯例一致，避免被误判为 UTC 产生 8h 偏差）
        dt = datetime.fromisoformat(ts.rsplit('+', 1)[0]).replace(tzinfo=TZ8)
    if dt.tzinfo is None:
        # naive 时间戳按 +08:00 解析（记录端固定 +08:00），不当作 UTC
        dt = dt.replace(tzinfo=TZ8)
    return dt


def main():
    _PKG_ROOT = Path(__file__).resolve().parent.parent
    p = argparse.ArgumentParser(description='检查是否该备份了 (Stage 0 备份新鲜度守卫)')
    p.add_argument('--assets', default=os.environ.get('DISTILL_ASSETS_DIR', str(os.path.expanduser('~/.workbuddy/distill-assets'))),
                   help='资产库目录 (默认 ~/.workbuddy/distill-assets，可用 DISTILL_ASSETS_DIR 覆盖)')
    p.add_argument('--warn', type=int, default=3, help='提醒阈值天数 (默认 3)')
    p.add_argument('--crit', type=int, default=7, help='强烈建议阈值天数 (默认 7)')
    p.add_argument('--quiet', action='store_true', help='仅在超阈值时输出（"从未备份过"等异常状态仍会输出）')
    p.add_argument('--exit-code', action='store_true', help='用退出码表示状态')
    args = p.parse_args()

    assets_dir = Path(args.assets).expanduser()
    last = find_last_export(assets_dir)
    now = datetime.now(timezone(timedelta(hours=8)))

    if last is None:
        # 异常状态（从未备份过）**必报**：--quiet 只抑制"一切正常"的常规输出，
        # 不得把「还从未备份过」这条本该提醒的状态静默掉
        print('[!] 从未备份过 (events.jsonl 找不到 type=export 事件)')
        print(HINT_EXPORT)
        if args.exit_code:
            return 3
        return 0

    # export 事件缺 ts / ts 非 ISO 时容错，归为「无有效导出」，避免守卫脚本崩溃
    _raw_ts = last.get('ts')
    if not isinstance(_raw_ts, str):
        last = None
    else:
        try:
            last_ts = parse_ts(_raw_ts)
        except (ValueError, TypeError):
            last = None

    if last is None:
        # 同「从未备份过」：ts 坏掉属异常状态，--quiet 下也必须报出
        print('[!] 未找到有效的导出时间戳 (events.jsonl 最近的 export 事件缺/坏 ts)')
        print(HINT_EXPORT)
        if args.exit_code:
            return 3
        return 0
    delta = now - last_ts
    days = delta.total_seconds() / 86400

    if days < 0:
        # 未来时间戳 / 时钟异常不应显示为「新鲜」；同属异常状态，--quiet 下也必须报出
        print(f'[!] 时钟异常或未来时间戳: 上次导出 {last_ts.strftime("%Y-%m-%d %H:%M:%S")} 晚于当前时间，请检查系统时钟')
        if args.exit_code:
            return 1
        return 0

    if days >= args.crit:
        level = '强烈建议'
        prefix = ''
    elif days >= args.warn:
        level = '提醒'
        prefix = '[!]'
    else:
        if not args.quiet:
            days_str = f'{days:.1f}'
            print(f'[OK] 备份新鲜: {days_str} 天前 ({last_ts.strftime("%Y-%m-%d %H:%M:%S")})')
        return 0

    days_str = f'{days:.1f}'
    print(f'{prefix} 备份{level}: 已 {days_str} 天未备份')
    print(f'   上次导出: {last_ts.strftime("%Y-%m-%d %H:%M:%S")} (events.jsonl)')
    print(f'   阈值: warn={args.warn}d / crit={args.crit}d')
    print(HINT_EXPORT)
    if args.exit_code:
        return 1 if level == '提醒' else 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
