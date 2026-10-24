#!/usr/bin/env python3
"""检索调优权衡计算器 — Top-K 上限、上下文窗口占用、Precision 随 K 衰减、延迟-质量权衡分
闭式模型：
  K_max(上下文预算) = floor(上下文token预算 / 单chunk token)
  P@K = relevant/K（K ≤ relevant 时），K > relevant 后 P@K = relevant/K 继续衰减
  窗口占用率 = chunk_size * K / context_budget
  权衡分 W = (0.5 * P@K + 0.5 * MRR) - λ * P99延迟超标倍数，λ 默认 0.1
"""
import argparse, json, math, sys


def calc_k_max(context_budget, chunk_size):
    """上下文可容纳的最大 Top-K（单变量：改 chunk 粒度时先重算此项）"""
    if chunk_size <= 0:
        return 0
    return max(0, int(context_budget // chunk_size))


def precision_at_k_curve(relevant, k_list):
    """P@K 衰减曲线：min(relevant, K) / K"""
    out = {}
    for k in k_list:
        if k <= 0:
            continue
        out[str(k)] = round(min(relevant, k) / k, 4)
    return out


def context_occupancy(chunk_size, k, context_budget):
    """Top-K 检索结果占下游上下文窗口的比例"""
    if context_budget <= 0:
        return 0.0
    return round(min(1.0, chunk_size * k / context_budget), 4)


def tradeoff_score(p_at_k, mrr, latency_p99_s, latency_sla_s, lam=0.1):
    """延迟-质量权衡分：质量项(0-1) 减去 延迟超标惩罚 λ*max(0, P99/SLA - 1)"""
    quality = 0.5 * p_at_k + 0.5 * mrr
    over = max(0.0, (latency_p99_s / latency_sla_s - 1.0)) if latency_sla_s > 0 else 0.0
    return round(quality - lam * over, 4)


def tune(chunk_size, relevant, mrr, context_budget, k_list, latency_p99_s, latency_sla_s, lam=0.1):
    k_max = calc_k_max(context_budget, chunk_size)
    k_list = [k for k in k_list if 0 < k <= k_max] or [k_max]
    curve = precision_at_k_curve(relevant, k_list)
    best = None
    for k in k_list:
        p = curve[str(k)]
        w = tradeoff_score(p, mrr, latency_p99_s, latency_sla_s, lam)
        row = {"k": k, "p_at_k": p, "occupancy": context_occupancy(chunk_size, k, context_budget), "tradeoff_score": w}
        if best is None or row["tradeoff_score"] > best["tradeoff_score"]:
            best = row
    return {"k_max": k_max, "p_at_k_curve": curve, "recommended": best}


def main():
    p = argparse.ArgumentParser(description="检索调优权衡计算")
    p.add_argument('--mode', choices=['kmax', 'curve', 'tradeoff', 'full'], default='full')
    p.add_argument('--chunk-size', type=int, help='单 chunk token 数（如 200/500/800）')
    p.add_argument('--context-budget', type=int, default=8192, help='下游上下文 token 预算')
    p.add_argument('--relevant', type=int, default=10, help='典型查询的相关文档总数')
    p.add_argument('--mrr', type=float, default=0.5, help='当前 MRR')
    p.add_argument('--k-list', type=str, default='[1,3,5,10]', help='JSON 数组，候选 Top-K')
    p.add_argument('--latency-p99-s', type=float, default=1.2, help='当前 P99 延迟（秒）')
    p.add_argument('--latency-sla-s', type=float, default=2.0, help='延迟 SLA（秒）')
    p.add_argument('--lambda', type=float, default=0.1, dest='lam', help='延迟惩罚系数')
    args = p.parse_args()

    if args.chunk_size is None:
        print("ERROR: --chunk-size 必填"); sys.exit(1)
    k_list = json.loads(args.k_list)

    if args.mode == 'kmax':
        print(json.dumps({"k_max": calc_k_max(args.context_budget, args.chunk_size)}, ensure_ascii=False))
    elif args.mode == 'curve':
        print(json.dumps({"p_at_k_curve": precision_at_k_curve(args.relevant, k_list)}, ensure_ascii=False))
    elif args.mode == 'tradeoff':
        r = tune(args.chunk_size, args.relevant, args.mrr, args.context_budget, k_list,
                 args.latency_p99_s, args.latency_sla_s, args.lam)
        print(json.dumps({"recommended": r["recommended"], "p_at_k_curve": r["p_at_k_curve"]}, ensure_ascii=False))
    else:
        r = tune(args.chunk_size, args.relevant, args.mrr, args.context_budget, k_list,
                 args.latency_p99_s, args.latency_sla_s, args.lam)
        print(json.dumps({
            "k_max": r["k_max"],
            "p_at_k_curve": r["p_at_k_curve"],
            "recommended": r["recommended"],
        }, ensure_ascii=False))


if __name__ == '__main__':
    main()
