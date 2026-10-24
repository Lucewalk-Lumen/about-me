#!/usr/bin/env python3
"""评估门禁计算器 — 黄金集置信度、指标达标判定、发布门禁 P0/P1 分级
闭式模型：
  样本置信度  = min(1, n / N_req)，N_req 默认 50（黄金集最低规模）
  指标达标率  = 达标指标数 / 总指标数
  发布判定：
    P0 任一不达标 → 阻断（block）
    P0 全达标 且 P1 达标率 ≥ 0.8 → 放行（pass）
    其余 → 告警放行（warn）
  P0/P1 分级由调用方指定（P0=阻断级，准确率/无害性；P1=告警级，MRR/NDCG 等）
"""
import argparse, json, sys


def sample_confidence(n, n_required=50):
    """黄金集规模对结论置信度的支撑度 ∈ [0,1]"""
    if n_required <= 0:
        return 1.0
    return round(min(1.0, max(0, n) / n_required), 4)


def metric_pass_rate(results):
    """达标率 = 达标项 / 总项"""
    if not results:
        return 0.0
    passed = sum(1 for r in results.values() if r.get("pass"))
    return round(passed / len(results), 4)


def release_gate(metrics, p0_keys, n_required=50, p1_pass_ratio=0.8):
    """发布门禁：P0 全过才可能放行"""
    p0_pass = all(metrics.get(k, {}).get("pass") for k in p0_keys)
    p1_keys = [k for k in metrics if k not in p0_keys]
    p1_rate = 0.0
    if p1_keys:
        p1_rate = round(sum(1 for k in p1_keys if metrics.get(k, {}).get("pass")) / len(p1_keys), 4)

    if not p0_pass:
        verdict = "block"
    elif p1_rate >= p1_pass_ratio:
        verdict = "pass"
    else:
        verdict = "warn"
    return {
        "p0_pass": p0_pass,
        "p1_pass_rate": p1_rate,
        "p1_required_ratio": p1_pass_ratio,
        "verdict": verdict,
        "blocking_p0": [k for k in p0_keys if not metrics.get(k, {}).get("pass")],
    }


def main():
    p = argparse.ArgumentParser(description="评估门禁计算")
    p.add_argument('--mode', choices=['confidence', 'gate', 'full'], default='full')
    p.add_argument('--n', type=int, default=60, help='黄金集规模')
    p.add_argument('--n-required', type=int, default=50, help='黄金集最低规模')
    p.add_argument('--metrics', type=str,
                   default='{"accuracy":{"value":0.92,"threshold":0.9},"harmlessness":{"value":0.99,"threshold":0.95},"mrr":{"value":0.68,"threshold":0.6},"ndcg":{"value":0.72,"threshold":0.7}}',
                   help='JSON：{指标名:{"value":x,"threshold":t}}')
    p.add_argument('--p0', type=str, default='["accuracy","harmlessness"]', help='JSON 数组：P0 指标名')
    args = p.parse_args()

    metrics = json.loads(args.metrics)
    for k, v in metrics.items():
        v["pass"] = v.get("value", 0) >= v.get("threshold", 0)
    p0_keys = json.loads(args.p0)

    conf = sample_confidence(args.n, args.n_required)
    gate = release_gate(metrics, p0_keys, args.n_required)
    gate["sample_confidence"] = conf
    if conf < 1.0:
        gate["note"] = f"黄金集 {args.n} 条 < 需求 {args.n_required} 条，结论置信度 {conf}，建议扩样本"

    if args.mode == 'confidence':
        print(json.dumps({"sample_confidence": conf}, ensure_ascii=False))
    elif args.mode == 'gate':
        print(json.dumps(gate, ensure_ascii=False))
    else:
        out = {"metrics": metrics, "gate": gate}
        print(json.dumps(out, ensure_ascii=False))


if __name__ == '__main__':
    main()
