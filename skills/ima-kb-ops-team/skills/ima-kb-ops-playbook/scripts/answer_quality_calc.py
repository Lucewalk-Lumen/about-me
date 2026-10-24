#!/usr/bin/env python3
"""问答质量与溯源门禁计算器 — 溯源命中率、幻觉率、拒答精准率、发布门禁
闭式模型：
  溯源命中率 = 有有效溯源的回答数 / 总回答数
  幻觉率 = 含库内不存在断言的回答数 / 总回答数（黄金集双盲标注计数）
  拒答精准率 = 应拒且实拒数 / 应拒数
  误拒率 = 应答却拒数 / 应答数
  P0 门禁（任一不过 → 阻断对外发布）：
    溯源命中率 ≥ 0.90
    幻觉率 ≤ 0.05
  P1 门禁（不过 → 需修复，不阻断）：
    拒答精准率 ≥ 0.80
  库外问题被回答数 单独高危计数（= 幻觉高危子集）
"""
import argparse, json, sys

P0_SOURCE_MIN = 0.90
P0_HALLUCINATION_MAX = 0.05
P1_REFUSAL_MIN = 0.80


def source_hit_rate(hit, total):
    return round(hit / total, 4) if total else 0.0


def hallucination_rate(halluc, total):
    return round(halluc / total, 4) if total else 0.0


def refusal_precision(should_refuse, refused_correctly):
    return round(refused_correctly / should_refuse, 4) if should_refuse else 1.0


def false_refusal_rate(should_answer, wrongly_refused):
    return round(wrongly_refused / should_answer, 4) if should_answer else 0.0


def main():
    p = argparse.ArgumentParser(description="问答质量与溯源门禁计算")
    p.add_argument('--mode', choices=['metrics', 'gate', 'full'], default='full')
    p.add_argument('--total-answers', type=int, required=True, help='评估样本总回答数')
    p.add_argument('--sourced', type=int, required=True, help='带有效溯源（可跳回库存条目）的回答数')
    p.add_argument('--hallucinations', type=int, default=0, help='黄金集双盲确认的幻觉回答数')
    p.add_argument('--out-of-kb-answered', type=int, default=0,
                   help='库外问题被回答（未拒答）数——高危幻觉子集，必须 ⊆ hallucinations')
    p.add_argument('--should-refuse', type=int, default=0, help='应拒答样本数（库外问题）')
    p.add_argument('--refused-correctly', type=int, default=0, help='应拒且实拒数')
    p.add_argument('--should-answer', type=int, default=0, help='应回答样本数（库内问题）')
    p.add_argument('--wrongly-refused', type=int, default=0, help='误拒（库内能答却拒）数')
    args = p.parse_args()

    total = args.total_answers
    # 高危校验：库外被回答数不得大于幻觉总数
    if args.out_of_kb_answered > args.hallucinations:
        print(json.dumps({"error": "out_of_kb_answered 不得大于 hallucinations（库外回答是幻觉高危子集）"}, ensure_ascii=False))
        sys.exit(1)

    src_rate = source_hit_rate(args.sourced, total)
    hallu_rate = hallucination_rate(args.hallucinations, total)
    ref_prec = refusal_precision(args.should_refuse, args.refused_correctly)
    false_ref = false_refusal_rate(args.should_answer, args.wrongly_refused)

    p0_source_ok = src_rate >= P0_SOURCE_MIN
    p0_hallu_ok = hallu_rate <= P0_HALLUCINATION_MAX
    p1_refusal_ok = ref_prec >= P1_REFUSAL_MIN

    verdict = "pass"
    p0_fail = []
    if not p0_source_ok:
        p0_fail.append(f"溯源命中率 {src_rate} < {P0_SOURCE_MIN}")
    if not p0_hallu_ok:
        p0_fail.append(f"幻觉率 {hallu_rate} > {P0_HALLUCINATION_MAX}")
    p1_fail = []
    if not p1_refusal_ok:
        p1_fail.append(f"拒答精准率 {ref_prec} < {P1_REFUSAL_MIN}")

    if p0_fail:
        verdict = "block"      # P0 任一不过 → 阻断发布
    elif p1_fail:
        verdict = "fix"        # 仅 P1 不过 → 需修复
    # 库外问题被回答 = 高危，强制降级
    if args.out_of_kb_answered > 0:
        verdict = "block"

    result = {
        "total_answers": total,
        "source_hit_rate": src_rate,
        "hallucination_rate": hallu_rate,
        "out_of_kb_answered": args.out_of_kb_answered,
        "refusal_precision": ref_prec,
        "false_refusal_rate": false_ref,
        "gates": {
            "P0_source_min": P0_SOURCE_MIN,
            "P0_source_ok": p0_source_ok,
            "P0_hallucination_max": P0_HALLUCINATION_MAX,
            "P0_hallucination_ok": p0_hallu_ok,
            "P1_refusal_min": P1_REFUSAL_MIN,
            "P1_refusal_ok": p1_refusal_ok,
        },
        "p0_failures": p0_fail,
        "p1_failures": p1_fail,
        "verdict": verdict,
        "sample_sufficient": total >= 30,
        "note": "样本<30 条时结论降级为参考值" if total < 30 else None,
    }

    if args.mode == 'metrics':
        print(json.dumps({k: result[k] for k in ("source_hit_rate", "hallucination_rate", "refusal_precision", "false_refusal_rate")}, ensure_ascii=False))
    elif args.mode == 'gate':
        print(json.dumps({"verdict": verdict, "p0_failures": p0_fail, "p1_failures": p1_fail, "out_of_kb_answered": args.out_of_kb_answered}, ensure_ascii=False))
    else:
        print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
