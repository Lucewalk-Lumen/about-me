#!/usr/bin/env python3
"""health_score_calc.py - 知识库健康分闭式计算（零三方依赖）。

四维加权：结构健康 25 / 内容新鲜度 25 / 质量巡检 30 / 成熟度分布 20（默认权重，可用参数覆盖）。
所有输入为已统计好的计数，本脚本不做任何文件扫描——扫描由成员用系统工具完成后把数字喂进来。

输出：JSON（维度分 + 加权总分 0-100 + 等级）。
退出码：0 正常；2 参数错误。
"""
import argparse
import json
import sys

WEIGHTS = {"structure": 25, "freshness": 25, "quality": 30, "maturity": 20}


def clamp(x, lo=0.0, hi=100.0):
    return max(lo, min(hi, x))


def structure_score(total, broken_links, orphans):
    if total <= 0:
        return 0.0
    bad_ratio = (broken_links + orphans) / total
    return clamp(100.0 * (1.0 - 2.0 * bad_ratio))


def freshness_score(total_official, stale_official, total_draft, stagnant_draft):
    parts = []
    if total_official > 0:
        parts.append(100.0 * (1.0 - stale_official / total_official))
    if total_draft > 0:
        parts.append(100.0 * (1.0 - stagnant_draft / total_draft))
    if not parts:
        return 100.0
    return clamp(sum(parts) / len(parts))


def quality_score(high, medium, low):
    # 每个高档发现扣 15，中档扣 5，低档扣 1
    return clamp(100.0 - 15.0 * high - 5.0 * medium - 1.0 * low)


def maturity_score(idea, draft, official, archive):
    total = idea + draft + official + archive
    if total <= 0:
        return 0.0
    score = 100.0
    idea_ratio = idea / total
    official_ratio = official / total
    # idea 淤积扣分：超过 50% 起扣
    if idea_ratio > 0.5:
        score -= (idea_ratio - 0.5) * 120.0
    # official 占比过低扣分：低于 10% 起扣
    if official_ratio < 0.1:
        score -= (0.1 - official_ratio) * 200.0
    return clamp(score)


def grade(total):
    if total >= 85:
        return "A"
    if total >= 70:
        return "B"
    if total >= 50:
        return "C"
    return "D"


def main(argv=None):
    p = argparse.ArgumentParser(
        description="知识库健康分闭式计算：输入各类计数，输出四维加权总分（0-100）。",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--total", type=int, required=True, help="条目总数（四池合计）")
    p.add_argument("--broken-links", type=int, default=0, help="死链数")
    p.add_argument("--orphans", type=int, default=0, help="孤儿条目数（无入链且未挂索引）")
    p.add_argument("--idea", type=int, default=0, help="idea 池条目数")
    p.add_argument("--draft", type=int, default=0, help="draft 池条目数")
    p.add_argument("--official", type=int, default=0, help="official 池条目数")
    p.add_argument("--archive", type=int, default=0, help="archive 池条目数")
    p.add_argument("--stale-official", type=int, default=0, help="逾期未复核的 official 数")
    p.add_argument("--stagnant-draft", type=int, default=0, help="滞留超期的 draft 数")
    p.add_argument("--high", type=int, default=0, help="巡检高严重度发现数")
    p.add_argument("--medium", type=int, default=0, help="巡检中严重度发现数")
    p.add_argument("--low", type=int, default=0, help="巡检低严重度发现数")
    p.add_argument("--w-structure", type=float, default=WEIGHTS["structure"], help="结构健康权重")
    p.add_argument("--w-freshness", type=float, default=WEIGHTS["freshness"], help="内容新鲜度权重")
    p.add_argument("--w-quality", type=float, default=WEIGHTS["quality"], help="质量巡检权重")
    p.add_argument("--w-maturity", type=float, default=WEIGHTS["maturity"], help="成熟度分布权重")
    args = p.parse_args(argv)

    for name in ("total", "broken_links", "orphans", "idea", "draft", "official",
                 "archive", "stale_official", "stagnant_draft", "high", "medium", "low"):
        if getattr(args, name) < 0:
            print("[FAIL] 计数参数不得为负: --%s" % name.replace("_", "-"), file=sys.stderr)
            return 2

    w = {
        "structure": args.w_structure,
        "freshness": args.w_freshness,
        "quality": args.w_quality,
        "maturity": args.w_maturity,
    }
    wsum = sum(w.values())
    if wsum <= 0:
        print("[FAIL] 权重之和必须为正", file=sys.stderr)
        return 2

    dims = {
        "structure": structure_score(args.total, args.broken_links, args.orphans),
        "freshness": freshness_score(args.official, args.stale_official, args.draft, args.stagnant_draft),
        "quality": quality_score(args.high, args.medium, args.low),
        "maturity": maturity_score(args.idea, args.draft, args.official, args.archive),
    }
    total = sum(dims[k] * w[k] for k in dims) / wsum

    out = {
        "weights": w,
        "dimension_scores": {k: round(v, 2) for k, v in dims.items()},
        "total_score": round(total, 2),
        "grade": grade(total),
        "inputs": {
            "total": args.total, "broken_links": args.broken_links, "orphans": args.orphans,
            "idea": args.idea, "draft": args.draft, "official": args.official, "archive": args.archive,
            "stale_official": args.stale_official, "stagnant_draft": args.stagnant_draft,
            "high": args.high, "medium": args.medium, "low": args.low,
        },
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
