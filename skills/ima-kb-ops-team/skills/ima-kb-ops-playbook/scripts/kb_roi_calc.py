#!/usr/bin/env python3
"""知识库 ROI 计算器 — 月价值、月成本、ROI 倍数、投入回收期、孤儿/冷门率
闭式模型：
  月价值   = 月命中次数 × 单次节省工时(小时) × 时薪单价(元)
  月成本   = 人力维护工时 × 时薪 + 存储月费 + Token月费
  ROI倍数  = 月价值 / 月成本
  回收期月 = 一次性建设投入 / (月价值 − 月成本)（月收益 ≤0 时判为无法回收）
  冷门率   = 零命中条目数 / 总条目数（30 天口径）
  孤儿率   = 零标签且零被引条目数 / 总条目数
"""
import argparse, json, sys


def calc_monthly_value(hits_per_month, minutes_saved, hourly_rate):
    """月价值 = 命中次数 × (节省分钟/60) × 时薪"""
    return round(max(0, hits_per_month) * max(0, minutes_saved) / 60.0 * max(0, hourly_rate), 2)


def calc_monthly_cost(maintain_hours, hourly_rate, storage_fee, token_fee):
    """月成本 = 人力 + 存储 + Token"""
    return round(max(0, maintain_hours) * max(0, hourly_rate) + max(0, storage_fee) + max(0, token_fee), 2)


def calc_roi(value, cost):
    """ROI 倍数；成本为 0 时按无穷大处理（记为 null + 说明）"""
    if cost <= 0:
        return None
    return round(value / cost, 2)


def calc_payback_months(capex, value, cost):
    """回收期（月）；月净收益 ≤ 0 → 无法回收（返回 None）"""
    net = value - cost
    if capex <= 0:
        return 0.0
    if net <= 0:
        return None
    return round(capex / net, 1)


def calc_cold_rate(zero_hit, total):
    if total <= 0:
        return 0.0
    return round(max(0, zero_hit) / total, 4)


def calc_orphan_rate(orphan, total):
    if total <= 0:
        return 0.0
    return round(max(0, orphan) / total, 4)


def full(
        hits_per_month, minutes_saved, hourly_rate,
        maintain_hours, storage_fee, token_fee, capex,
        total_entries, zero_hit_entries, orphan_entries):
    value = calc_monthly_value(hits_per_month, minutes_saved, hourly_rate)
    cost = calc_monthly_cost(maintain_hours, hourly_rate, storage_fee, token_fee)
    roi = calc_roi(value, cost)
    payback = calc_payback_months(capex, value, cost)
    return {
        "monthly_value_yuan": value,
        "monthly_cost_yuan": cost,
        "monthly_net_yuan": round(value - cost, 2),
        "roi_multiple": roi,
        "roi_note": "成本为 0，ROI 无定义（价值全部为正收益）" if roi is None else None,
        "payback_months": payback,
        "payback_note": "月净收益 ≤ 0，无法回收一次性投入" if payback is None else None,
        "cold_rate_30d": calc_cold_rate(zero_hit_entries, total_entries),
        "orphan_rate": calc_orphan_rate(orphan_entries, total_entries),
    }


def main():
    p = argparse.ArgumentParser(description="知识库 ROI 计算")
    p.add_argument('--mode', choices=['value', 'cost', 'full'], default='full')
    p.add_argument('--hits-per-month', type=int, help='月命中次数')
    p.add_argument('--minutes-saved', type=float, default=5, help='单次命中节省工时（分钟）')
    p.add_argument('--hourly-rate', type=float, default=100, help='时薪单价（元/小时）')
    p.add_argument('--maintain-hours', type=float, help='月维护人力工时（小时）')
    p.add_argument('--storage-fee', type=float, default=0, help='存储月费（元）')
    p.add_argument('--token-fee', type=float, default=0, help='Token/推理月费（元）')
    p.add_argument('--capex', type=float, default=0, help='一次性建设投入（元）')
    p.add_argument('--total-entries', type=int, default=0, help='知识库总条目数')
    p.add_argument('--zero-hit-entries', type=int, default=0, help='30 天零命中条目数')
    p.add_argument('--orphan-entries', type=int, default=0, help='孤儿条目数（零标签且零被引）')
    args = p.parse_args()

    if args.hits_per_month is None:
        print("ERROR: --hits-per-month 必填"); sys.exit(1)
    if args.maintain_hours is None:
        print("ERROR: --maintain-hours 必填"); sys.exit(1)

    if args.mode == 'value':
        print(json.dumps({"monthly_value_yuan":
                          calc_monthly_value(args.hits_per_month, args.minutes_saved, args.hourly_rate)},
                         ensure_ascii=False))
    elif args.mode == 'cost':
        print(json.dumps({"monthly_cost_yuan":
                          calc_monthly_cost(args.maintain_hours, args.hourly_rate, args.storage_fee, args.token_fee)},
                         ensure_ascii=False))
    else:
        r = full(
            args.hits_per_month, args.minutes_saved, args.hourly_rate,
            args.maintain_hours, args.storage_fee, args.token_fee, args.capex,
            args.total_entries, args.zero_hit_entries, args.orphan_entries)
        print(json.dumps(r, ensure_ascii=False))


if __name__ == '__main__':
    main()
