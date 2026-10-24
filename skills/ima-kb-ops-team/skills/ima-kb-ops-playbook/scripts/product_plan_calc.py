#!/usr/bin/env python3
"""知识产物产能计算器 — 月产能、复用系数、质量门、工时缺口
闭式模型：
  月需求件数 = Σ(各产物类型月频次)
  复用系数 = 高复用主题数 / 库存主题域数（一条库存支撑多类产物的程度）
  可用产能件数 = 可用生成工时 / 单产物平均工时
  产能缺口 = max(0, 月需求 - 可用产能)
  质量门通过数 = 库存条目中质量分≥门限的条目数（输入）
  可排产件数 = min(月需求, 可用产能, 质量门通过主题支撑件数)
"""
import argparse, json, math, sys


def monthly_demand(frequencies):
    """frequencies: dict{产物类型: 月频次} → 总需求件数"""
    return sum(max(0, int(v)) for v in frequencies.values())


def reuse_coefficient(high_reuse_topics, total_topic_domains):
    """复用系数 = 高复用主题数 / 主题域总数（0-1）"""
    if total_topic_domains <= 0:
        return 0.0
    return round(min(1.0, max(0, high_reuse_topics) / total_topic_domains), 4)


def production_capacity(available_hours, minutes_per_product):
    """可用产能件数 = 工时 / 单件分钟 × 60"""
    if minutes_per_product <= 0:
        return 0
    return int(max(0.0, available_hours) * 60.0 / minutes_per_product)


def quality_gate_eligible(total_entries, passing_entries):
    """质量门通过率 = 通过条目 / 总条目（决定可排产主题支撑）"""
    if total_entries <= 0:
        return 0.0
    return round(min(1.0, max(0, passing_entries) / total_entries), 4)


def main():
    p = argparse.ArgumentParser(description="知识产物产能计算")
    p.add_argument('--mode', choices=['capacity', 'full'], default='full')
    p.add_argument('--frequencies', type=str, required=True,
                   help='JSON：各产物类型月频次，如 {"podcast":4,"mindmap":8,"report":2,"ai_note":6}')
    p.add_argument('--available-hours', type=float, default=0, help='月可用生成工时')
    p.add_argument('--minutes-per-product', type=float, default=30, help='单产物平均分钟数')
    p.add_argument('--high-reuse-topics', type=int, default=0, help='高复用主题数（支撑≥3类产物）')
    p.add_argument('--total-topics', type=int, default=0, help='库存主题域总数')
    p.add_argument('--total-entries', type=int, default=0, help='库存条目总数')
    p.add_argument('--passing-entries', type=int, default=0, help='质量分≥门限的条目数')
    p.add_argument('--quality-gate', type=float, default=0.6, help='质量门阈值（0-1 归一分，默认0.6）')
    args = p.parse_args()

    freqs = json.loads(args.frequencies)
    demand = monthly_demand(freqs)
    capacity = production_capacity(args.available_hours, args.minutes_per_product)
    gap = max(0, demand - capacity)
    reuse = reuse_coefficient(args.high_reuse_topics, args.total_topics)
    gate_pass_rate = quality_gate_eligible(args.total_entries, args.passing_entries)
    # 可排产件数受三重约束：需求、产能、质量门通过主题支撑
    schedulable = min(demand, capacity, int(round(demand * gate_pass_rate))) if demand else 0

    result = {
        "monthly_demand": demand,
        "demand_breakdown": freqs,
        "production_capacity": capacity,
        "capacity_gap": gap,
        "schedulable_units": schedulable,
        "reuse_coefficient": reuse,
        "quality_gate": {
            "threshold": args.quality_gate,
            "pass_rate": gate_pass_rate,
            "passing": args.passing_entries,
            "total": args.total_entries,
        },
        "recommendation": "需求>产能，裁剪低频产物或加工时" if gap > 0 else "产能满足",
        "ima_product_scope": ["podcast", "mindmap", "report", "ai_note", "lesson_plan"],
    }

    if args.mode == 'capacity':
        print(json.dumps({
            "production_capacity": capacity,
            "capacity_gap": gap,
            "schedulable_units": schedulable,
        }, ensure_ascii=False))
    else:
        print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
