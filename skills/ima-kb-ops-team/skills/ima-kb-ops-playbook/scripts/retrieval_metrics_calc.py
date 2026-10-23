#!/usr/bin/env python3
"""检索效果计算器 — 召回率@K、精确率@K、MRR、NDCG"""
import argparse, json, sys

def calc_recall_at_k(relevant_retrieved, total_relevant):
    """召回率@K"""
    if total_relevant == 0: return 0.0
    return round(relevant_retrieved / total_relevant, 4)

def calc_precision_at_k(relevant_retrieved, k):
    """精确率@K"""
    if k == 0: return 0.0
    return round(min(relevant_retrieved, k) / k, 4)

def calc_mrr(rankings):
    """MRR（平均倒数排名）"""
    if not rankings: return 0.0
    rr_sum = 0.0
    for r in rankings:
        if r > 0:
            rr_sum += 1.0 / r
    return round(rr_sum / len(rankings), 4)

def calc_ndcg(relevances, k=5):
    """NDCG@K"""
    if not relevances: return 0.0
    dcg = 0.0
    for i, rel in enumerate(relevances[:k]):
        dcg += (2**rel - 1) / (i + 1)
    ideal = sorted(relevances, reverse=True)
    idcg = 0.0
    for i, rel in enumerate(ideal[:k]):
        idcg += (2**rel - 1) / (i + 1)
    if idcg == 0: return 0.0
    return round(dcg / idcg, 4)

def main():
    p = argparse.ArgumentParser(description="检索效果计算")
    p.add_argument('--mode', choices=['recall', 'precision', 'mrr', 'ndcg', 'full'], default='full')
    p.add_argument('--relevant-retrieved', type=int, help='检索到的相关文档数')
    p.add_argument('--total-relevant', type=int, help='总相关文档数')
    p.add_argument('--k', type=int, default=5, help='Top-K')
    p.add_argument('--rankings', type=str, help='JSON 数组，每个查询的首相关文档排名')
    p.add_argument('--relevances', type=str, help='JSON 数组，检索结果的相关性分数')
    args = p.parse_args()

    if args.mode == 'recall':
        if args.relevant_retrieved is None or args.total_relevant is None:
            print("ERROR: --relevant-retrieved 和 --total-relevant 必填"); sys.exit(1)
        print(json.dumps({"recall_at_k": calc_recall_at_k(args.relevant_retrieved, args.total_relevant)}, ensure_ascii=False))

    elif args.mode == 'precision':
        if args.relevant_retrieved is None:
            print("ERROR: --relevant-retrieved 必填"); sys.exit(1)
        print(json.dumps({"precision_at_k": calc_precision_at_k(args.relevant_retrieved, args.k)}, ensure_ascii=False))

    elif args.mode == 'mrr':
        if not args.rankings: print("ERROR: --rankings 必填"); sys.exit(1)
        rankings = json.loads(args.rankings)
        print(json.dumps({"mrr": calc_mrr(rankings)}, ensure_ascii=False))

    elif args.mode == 'ndcg':
        if not args.relevances: print("ERROR: --relevances 必填"); sys.exit(1)
        relevances = json.loads(args.relevances)
        print(json.dumps({"ndcg_at_k": calc_ndcg(relevances, args.k)}, ensure_ascii=False))

    elif args.mode == 'full':
        results = {}
        if args.relevant_retrieved is not None and args.total_relevant is not None:
            results['recall_at_k'] = calc_recall_at_k(args.relevant_retrieved, args.total_relevant)
        if args.relevant_retrieved is not None:
            results['precision_at_k'] = calc_precision_at_k(args.relevant_retrieved, args.k)
        if args.rankings:
            results['mrr'] = calc_mrr(json.loads(args.rankings))
        if args.relevances:
            results['ndcg_at_k'] = calc_ndcg(json.loads(args.relevances), args.k)
        print(json.dumps(results, ensure_ascii=False))

if __name__ == '__main__':
    main()
