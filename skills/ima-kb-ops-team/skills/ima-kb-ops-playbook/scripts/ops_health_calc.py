#!/usr/bin/env python3
"""运营健康度计算器 — 综合健康评分 + 指标归一化 + 趋势分析"""
import argparse, json, sys

def normalize(value, min_val, max_val):
    """归一化到 0-100"""
    if max_val == min_val: return 50.0
    return round(max(0, min(100, (value - min_val) / (max_val - min_val) * 100)), 2)

def calc_health(metrics):
    """
    综合健康评分
    metrics: dict with keys:
      - recall: 召回率 (0-1)
      - precision: 精确率 (0-1)
      - response_time_s: 响应时间 (秒)
      - satisfaction: 用户满意度 (0-5)
      - coverage: 知识覆盖率 (0-1)
      - skill_success_rate: Skill调用成功率 (0-1)
      - content_freshness: 内容新鲜度 (0-1)
    """
    # 各指标归一化
    recall_score = metrics.get('recall', 0) * 100
    precision_score = metrics.get('precision', 0) * 100
    # 响应时间：目标 <3s，>10s 为 0 分
    response_score = normalize(metrics.get('response_time_s', 3), 10, 1)
    response_score = 100 - response_score  # 反转：越快越好
    satisfaction_score = metrics.get('satisfaction', 4) / 5 * 100
    coverage_score = metrics.get('coverage', 0) * 100
    skill_score = metrics.get('skill_success_rate', 0) * 100
    freshness_score = metrics.get('content_freshness', 0) * 100

    # 加权综合
    weights = {
        'recall': 0.20,
        'precision': 0.15,
        'response': 0.15,
        'satisfaction': 0.15,
        'coverage': 0.15,
        'skill': 0.10,
        'freshness': 0.10
    }

    total = (
        recall_score * weights['recall'] +
        precision_score * weights['precision'] +
        response_score * weights['response'] +
        satisfaction_score * weights['satisfaction'] +
        coverage_score * weights['coverage'] +
        skill_score * weights['skill'] +
        freshness_score * weights['freshness']
    )

    return round(total, 2)

def health_grade(score):
    if score >= 85: return "优秀"
    if score >= 70: return "良好"
    if score >= 55: return "合格"
    if score >= 40: return "待改进"
    return "不合格"

def main():
    p = argparse.ArgumentParser(description="运营健康度计算")
    p.add_argument('--mode', choices=['health', 'normalize', 'trend'], default='health')
    p.add_argument('--metrics', type=str, help='JSON 对象，含各指标值')
    p.add_argument('--values', type=str, help='JSON 数组，历史健康度值（用于趋势）')
    args = p.parse_args()

    if args.mode == 'health':
        if not args.metrics: print("ERROR: --metrics 必填"); sys.exit(1)
        m = json.loads(args.metrics)
        score = calc_health(m)
        print(json.dumps({
            "health_score": score,
            "grade": health_grade(score),
            "components": {
                "recall": round(m.get('recall', 0) * 100, 1),
                "precision": round(m.get('precision', 0) * 100, 1),
                "response": round(100 - normalize(m.get('response_time_s', 3), 10, 1), 1),
                "satisfaction": round(m.get('satisfaction', 4) / 5 * 100, 1),
                "coverage": round(m.get('coverage', 0) * 100, 1),
                "skill_success": round(m.get('skill_success_rate', 0) * 100, 1),
                "freshness": round(m.get('content_freshness', 0) * 100, 1)
            }
        }, ensure_ascii=False))

    elif args.mode == 'normalize':
        # 单指标归一化
        if not args.metrics: print("ERROR: --metrics 必填"); sys.exit(1)
        m = json.loads(args.metrics)
        value = m.get('value', 0)
        min_v = m.get('min', 0)
        max_v = m.get('max', 100)
        print(json.dumps({"normalized": normalize(value, min_v, max_v)}, ensure_ascii=False))

    elif args.mode == 'trend':
        if not args.values: print("ERROR: --values 必填"); sys.exit(1)
        vals = json.loads(args.values)
        if len(vals) < 2:
            print(json.dumps({"trend": "stable", "change": 0}))
            return
        change = vals[-1] - vals[0]
        pct = (change / vals[0] * 100) if vals[0] != 0 else 0
        trend = "up" if change > 5 else ("down" if change < -5 else "stable")
        print(json.dumps({
            "trend": trend,
            "change": round(change, 2),
            "change_pct": round(pct, 2),
            "values": vals
        }, ensure_ascii=False))

if __name__ == '__main__':
    main()
