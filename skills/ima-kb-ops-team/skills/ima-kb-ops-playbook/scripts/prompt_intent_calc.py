#!/usr/bin/env python3
"""提示词解析指标计算器 — 槽位完整度、意图置信度加权、改写覆盖率、追问必要性判定"""
import argparse, json, sys


def calc_slot_completeness(filled, total):
    """槽位完整度 = 已填槽位 / 总槽位（缺失项必须显式列出）"""
    if total == 0:
        return 1.0  # 无槽位的纯查询，视为完整
    filled = max(0, min(filled, total))
    return round(filled / total, 4)


def calc_intent_confidence(scores):
    """意图置信度 = 各意图得分的归一化最大占比（softmax-lite）
    scores: [0.8, 0.3, 0.1] 各候选意图的原始得分（0-1）
    """
    if not scores:
        return 0.0
    total = sum(max(0.0, s) for s in scores)
    if total == 0:
        return 0.0
    return round(max(max(scores), 0.0) / total, 4)


def calc_rewrite_coverage(entities, rewritten_entities):
    """改写覆盖率 = 改写后保留的实体数 / 原始实体数（禁止丢失限定词）"""
    if not entities:
        return 1.0
    kept = 0
    for e in entities:
        if any(e in r for r in rewritten_entities):
            kept += 1
    return round(kept / len(entities), 4)


def calc_missing_info_score(filled, total):
    """缺失信息评分（0-100）：槽位越缺分越低，用于追问必要性判定"""
    comp = calc_slot_completeness(filled, total)
    return round(comp * 100, 1)


def needs_clarification(filled, total, confidence, threshold=0.7):
    """追问判定：完整度 < 0.7 或 置信度 < 0.7 → 必须追问（交叉校验规则）"""
    comp = calc_slot_completeness(filled, total)
    return (comp < threshold) or (confidence < threshold)


def main():
    p = argparse.ArgumentParser(description="提示词解析指标计算")
    p.add_argument('--mode', choices=['single', 'clarify', 'full'], default='full')
    p.add_argument('--filled', type=int, help='已填槽位数')
    p.add_argument('--total', type=int, help='总槽位数')
    p.add_argument('--intent-scores', type=str, help='JSON 数组，各候选意图原始得分 0-1')
    p.add_argument('--entities', type=str, help='JSON 数组，原始提示词实体')
    p.add_argument('--rewritten-entities', type=str, help='JSON 数组，改写后问法中出现的实体')
    p.add_argument('--threshold', type=float, default=0.7, help='追问判定阈值（默认 0.7）')
    args = p.parse_args()

    if args.mode == 'single':
        if args.filled is None or args.total is None:
            print("ERROR: --filled 和 --total 必填"); sys.exit(1)
        conf = calc_intent_confidence(json.loads(args.intent_scores)) if args.intent_scores else None
        print(json.dumps({
            "slot_completeness": calc_slot_completeness(args.filled, args.total),
            "missing_info_score": calc_missing_info_score(args.filled, args.total),
            "intent_confidence": conf,
        }, ensure_ascii=False))

    elif args.mode == 'clarify':
        if args.filled is None or args.total is None:
            print("ERROR: --filled 和 --total 必填"); sys.exit(1)
        conf = calc_intent_confidence(json.loads(args.intent_scores)) if args.intent_scores else 0.0
        need = needs_clarification(args.filled, args.total, conf, args.threshold)
        print(json.dumps({
            "need_clarification": need,
            "threshold": args.threshold,
            "intent_confidence": conf,
            "slot_completeness": calc_slot_completeness(args.filled, args.total),
            "reason": "slot" if calc_slot_completeness(args.filled, args.total) < args.threshold else "confidence",
        }, ensure_ascii=False))

    elif args.mode == 'full':
        results = {}
        if args.filled is not None and args.total is not None:
            results['slot_completeness'] = calc_slot_completeness(args.filled, args.total)
            results['missing_info_score'] = calc_missing_info_score(args.filled, args.total)
        if args.intent_scores:
            results['intent_confidence'] = calc_intent_confidence(json.loads(args.intent_scores))
        if args.entities and args.rewritten_entities:
            results['rewrite_coverage'] = calc_rewrite_coverage(
                json.loads(args.entities), json.loads(args.rewritten_entities))
        if args.filled is not None and args.total is not None and args.intent_scores:
            conf = results.get('intent_confidence', 0.0)
            results['need_clarification'] = needs_clarification(args.filled, args.total, conf, args.threshold)
        print(json.dumps(results, ensure_ascii=False))

    if args.mode == 'full' and not results:
        print("ERROR: 至少提供一组输入参数"); sys.exit(1)


if __name__ == '__main__':
    main()
