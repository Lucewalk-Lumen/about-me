#!/usr/bin/env python3
"""知识库采纳率计算器 — 采纳漏斗转化率、激活率、留存率、使用深度
闭式模型：
  漏斗转化率   = 下层用户数 / 上层用户数（逐层）
  激活率       = 完成首次成功检索用户 / 触达用户
  周留存率     = 第 2 周仍活跃 / 第 1 周活跃
  使用深度     = 深度用户(周≥5次检索) / 周活用户
  最大卡点     = 转化率最低的漏斗层
"""
import argparse, json, sys


def funnel_conversion(counts):
    """counts: {"aware":1000,"signup":400,"first_use":180,"weekly_active":120,"power":45}
    返回逐层转化率与最大卡点层"""
    keys = list(counts.keys())
    rates = {}
    max_drop = None
    for i in range(1, len(keys)):
        upper = counts.get(keys[i - 1], 0)
        lower = counts.get(keys[i], 0)
        r = round(lower / upper, 4) if upper > 0 else 0.0
        rates[f"{keys[i-1]}->{keys[i]}"] = r
        if max_drop is None or r < rates[f"{keys[max_drop]}->{keys[max_drop+1]}"]:
            max_drop = i
    bottleneck = f"{keys[max_drop-1]}->{keys[max_drop]}" if max_drop else None
    return {"rates": rates, "bottleneck": bottleneck}


def calc_activation(first_success, reached):
    """激活率 = 完成首次成功检索 / 触达"""
    if reached <= 0:
        return 0.0
    return round(max(0, first_success) / reached, 4)


def calc_retention(week2_active, week1_active):
    """周留存率 = 第2周活跃 / 第1周活跃"""
    if week1_active <= 0:
        return 0.0
    return round(max(0, week2_active) / week1_active, 4)


def calc_depth(power_users, weekly_active):
    """使用深度 = 深度用户(周≥5次) / 周活"""
    if weekly_active <= 0:
        return 0.0
    return round(max(0, power_users) / weekly_active, 4)


def main():
    p = argparse.ArgumentParser(description="知识库采纳率计算")
    p.add_argument('--mode', choices=['funnel', 'activation', 'full'], default='full')
    p.add_argument('--counts', type=str,
                   default='{"aware":1000,"signup":400,"first_use":180,"weekly_active":120,"power":45}',
                   help='JSON：漏斗各层用户数')
    p.add_argument('--reached', type=int, default=1000, help='触达用户数')
    p.add_argument('--first-success', type=int, default=180, help='完成首次成功检索用户')
    p.add_argument('--week1-active', type=int, default=120, help='第1周活跃用户')
    p.add_argument('--week2-active', type=int, default=72, help='第2周活跃用户')
    p.add_argument('--power-users', type=int, default=45, help='深度用户(周≥5次检索)')
    args = p.parse_args()

    counts = json.loads(args.counts)
    if args.mode == 'funnel':
        r = funnel_conversion(counts)
        print(json.dumps(r, ensure_ascii=False))
    elif args.mode == 'activation':
        print(json.dumps({
            "activation_rate": calc_activation(args.first_success, args.reached),
            "weekly_retention": calc_retention(args.week2_active, args.week1_active),
            "usage_depth": calc_depth(args.power_users, args.week1_active),
        }, ensure_ascii=False))
    else:
        r = funnel_conversion(counts)
        print(json.dumps({
            "funnel": r,
            "activation_rate": calc_activation(args.first_success, args.reached),
            "weekly_retention": calc_retention(args.week2_active, args.week1_active),
            "usage_depth": calc_depth(args.power_users, args.week1_active),
        }, ensure_ascii=False))


if __name__ == '__main__':
    main()
