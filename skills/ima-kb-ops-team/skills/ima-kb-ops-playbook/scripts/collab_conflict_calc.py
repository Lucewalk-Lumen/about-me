#!/usr/bin/env python3
"""共享知识库协作冲突计算器 — 冲突率、评审负载、权限覆盖、同名条目归属
闭式模型：
  单次变更冲突概率 = (1 - 1/角色数) × 同主题重叠率
    （某次变更撞上"其他角色同时在改同一主题"的概率；角色数≥2 才有冲突）
  冲突率 = 单次变更冲突概率（0-1）
  月冲突数 = 月变更量 × 冲突率
  月评审工时 = 月冲突数 × 单条评审分钟 / 60
  评审人力缺口 = max(0, 月评审工时 - 可用评审人数×人均可用工时)
  权限覆盖 = 已授权操作数 / 应授权操作数（最小权限基线）
"""
import argparse, json, sys


def conflict_probability(roles, overlap_rate):
    """单次变更撞上其他角色同主题并发变更的概率（0-1）"""
    if roles < 2:
        return 0.0
    ovr = max(0.0, min(1.0, overlap_rate))
    return round((1.0 - 1.0 / roles) * ovr, 4)


def conflict_count(month_changes, roles, overlap_rate):
    """月冲突数 = 月变更量 × 冲突率"""
    if month_changes <= 0:
        return 0
    return int(round(max(0, month_changes) * conflict_probability(roles, overlap_rate)))


def review_hours(conflicts, minutes_per_conflict):
    return round(conflicts * max(0.0, minutes_per_conflict) / 60.0, 1)


def reviewer_gap(review_total_hours, reviewers, hours_per_reviewer):
    capacity = max(0, reviewers) * max(0.0, hours_per_reviewer)
    return max(0.0, review_total_hours - capacity)


def permission_coverage(granted_ops, expected_ops):
    if not expected_ops:
        return 1.0
    return round(min(1.0, max(0.0, granted_ops) / expected_ops), 4)


def main():
    p = argparse.ArgumentParser(description="共享知识库协作冲突计算")
    p.add_argument('--mode', choices=['conflict', 'full'], default='full')
    p.add_argument('--month-changes', type=int, default=0, help='月条目增删改次数')
    p.add_argument('--roles', type=int, default=2, help='参与变更的角色数（≥2 才可能冲突）')
    p.add_argument('--overlap-rate', type=float, default=0.3, help='同主题重叠率 0-1（默认 0.3）')
    p.add_argument('--minutes-per-conflict', type=float, default=8, help='单条冲突评审分钟数')
    p.add_argument('--reviewers', type=int, default=1, help='可用评审人数')
    p.add_argument('--reviewer-hours', type=float, default=20, help='每人月可评审工时')
    p.add_argument('--granted-ops', type=int, default=0, help='已授权操作数')
    p.add_argument('--expected-ops', type=int, default=0, help='应授权操作数（最小权限基线）')
    args = p.parse_args()

    rate = conflict_probability(args.roles, args.overlap_rate)
    conflicts = conflict_count(args.month_changes, args.roles, args.overlap_rate)
    hours = review_hours(conflicts, args.minutes_per_conflict)
    gap = reviewer_gap(hours, args.reviewers, args.reviewer_hours)
    perm = permission_coverage(args.granted_ops, args.expected_ops)

    # 冲突等级：低(<5%) / 中(5-15%) / 高(>15%)
    level = "低" if rate < 0.05 else ("中" if rate <= 0.15 else "高")

    result = {
        "monthly_conflicts": conflicts,
        "conflict_rate": rate,
        "conflict_level": level,
        "review_hours_per_month": hours,
        "reviewer_gap_hours": gap,
        "reviewer_ok": gap <= 0,
        "permission_coverage": perm,
        "same_name_rule": "first_come_or_authoritative_source（须显式选择，禁止沉默）",
    }

    if args.mode == 'conflict':
        print(json.dumps({k: result[k] for k in ("monthly_conflicts", "conflict_rate", "conflict_level")}, ensure_ascii=False))
    else:
        print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
