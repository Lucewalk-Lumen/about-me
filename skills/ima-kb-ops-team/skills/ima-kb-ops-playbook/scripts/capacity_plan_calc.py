#!/usr/bin/env python3
"""容量规划计算器 — 条目增长预测 + 存储估算 + 检索性能预测"""
import argparse, json, sys

def project_growth(initial, rate_months, months):
    """条目增长预测（线性/指数）"""
    results = []
    current = initial
    for m in range(1, months + 1):
        current = current * (1 + rate_months)
        results.append({"month": m, "entries": int(current)})
    return results

def calc_storage(entries, avg_entry_kb=5):
    """存储估算（假设平均条目 5KB）"""
    total_kb = entries * avg_entry_kb
    total_mb = total_kb / 1024
    total_gb = total_mb / 1024
    return {"entries": entries, "avg_entry_kb": avg_entry_kb, "total_mb": round(total_mb, 2), "total_gb": round(total_gb, 4)}

def predict_retrieval(total_entries, top_k=5):
    """检索性能预测（基于经验模型）"""
    # 经验公式：检索时间 ≈ 基础延迟 + 条目数 × 每条目处理时间
    # 假设：基础延迟 0.5s，每条目 0.001s
    base_latency = 0.5
    per_entry = 0.001
    estimated_time = base_latency + total_entries * per_entry
    
    # 召回率预测：随条目增加而下降（对数模型）
    import math
    recall = max(0.5, 0.95 - 0.05 * math.log10(max(1, total_entries)))
    
    return {
        "estimated_time_s": round(estimated_time, 3),
        "recall_at_k": round(recall, 3),
        "top_k": top_k,
        "recommendation": "拆分知识库" if total_entries > 10000 else "单库可接受"
    }

def main():
    p = argparse.ArgumentParser(description="容量规划计算")
    p.add_argument('--mode', choices=['growth', 'storage', 'retrieval', 'full'], default='full')
    p.add_argument('--initial', type=int, default=100, help='初始条目数')
    p.add_argument('--rate', type=float, default=0.1, help='月增长率（0.1=10%）')
    p.add_argument('--months', type=int, default=12, help='预测月数')
    p.add_argument('--entries', type=int, help='当前条目数（用于检索预测）')
    p.add_argument('--top-k', type=int, default=5)
    args = p.parse_args()

    if args.mode == 'growth':
        results = project_growth(args.initial, args.rate, args.months)
        print(json.dumps({"initial": args.initial, "rate": args.rate, "projection": results}, ensure_ascii=False))

    elif args.mode == 'storage':
        if not args.entries: print("ERROR: --entries 必填"); sys.exit(1)
        result = calc_storage(args.entries)
        print(json.dumps(result, ensure_ascii=False))

    elif args.mode == 'retrieval':
        if not args.entries: print("ERROR: --entries 必填"); sys.exit(1)
        result = predict_retrieval(args.entries, args.top_k)
        print(json.dumps(result, ensure_ascii=False))

    elif args.mode == 'full':
        if not args.entries: print("ERROR: --entries 必填"); sys.exit(1)
        growth = project_growth(args.initial, args.rate, args.months)
        storage = calc_storage(args.entries)
        retrieval = predict_retrieval(args.entries, args.top_k)
        print(json.dumps({
            "growth_projection": growth,
            "storage_estimate": storage,
            "retrieval_prediction": retrieval
        }, ensure_ascii=False))

if __name__ == '__main__':
    main()
