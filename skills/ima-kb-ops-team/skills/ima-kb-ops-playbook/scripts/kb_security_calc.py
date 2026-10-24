#!/usr/bin/env python3
"""知识库合规安全计算器 — 数据分级暴露面、合规风险分、高危条目占比
闭式模型：
  暴露面   = Σ(各分级条目数 × 该级访问面系数) / 总条目数
            访问面系数：公开=1.0 / 内部=0.5 / 受限=0.2 / 机密=0.05
  高危占比 = (受限条目数 + 机密条目数) / 总条目数
  合规风险分 R = 100 × ( 0.5×高危占比 + 0.3×(1−审计覆盖率) + 0.2×PII未处置占比 )
            R ∈ [0,100]，越高越危险；等级：≥70 高危 / 40-69 中 / <40 低
"""
import argparse, json, sys

ACCESS_COEF = {"public": 1.0, "internal": 0.5, "restricted": 0.2, "confidential": 0.05}


def calc_exposure(levels, total_entries):
    """暴露面 = Σ(分级条目数 × 访问面系数) / 总条目数，∈ [0,1]"""
    if total_entries <= 0:
        return 0.0
    weighted = 0.0
    for lvl, cnt in levels.items():
        weighted += max(0, cnt) * ACCESS_COEF.get(lvl, 0.2)
    return round(min(1.0, weighted / total_entries), 4)


def calc_high_risk_ratio(restricted, confidential, total_entries):
    """高危条目占比 = (受限 + 机密) / 总条目数"""
    if total_entries <= 0:
        return 0.0
    return round((max(0, restricted) + max(0, confidential)) / total_entries, 4)


def calc_compliance_risk(high_ratio, audit_coverage, pii_unhandled_ratio):
    """合规风险分 = 100 × (0.5×高危占比 + 0.3×(1-审计覆盖率) + 0.2×PII未处置占比)"""
    raw = (0.5 * high_ratio + 0.3 * (1.0 - max(0.0, min(1.0, audit_coverage)))
           + 0.2 * pii_unhandled_ratio)
    score = round(100.0 * max(0.0, min(1.0, raw)), 1)
    if score >= 70:
        grade = "高危"
    elif score >= 40:
        grade = "中"
    else:
        grade = "低"
    return {"score": score, "grade": grade}


def main():
    p = argparse.ArgumentParser(description="知识库合规安全计算")
    p.add_argument('--mode', choices=['exposure', 'risk', 'full'], default='full')
    p.add_argument('--levels', type=str, default='{"public":100,"internal":50,"restricted":20,"confidential":5}',
                   help='JSON：各分级条目数 {"public":n,"internal":n,"restricted":n,"confidential":n}')
    p.add_argument('--total', type=int, help='总条目数（缺省用 levels 之和）')
    p.add_argument('--audit-coverage', type=float, default=1.0, help='受限/机密条目审计日志覆盖率 0-1')
    p.add_argument('--pii-unhandled', type=float, default=0.0, help='PII 未处置条目占 PII 总数比例 0-1')
    args = p.parse_args()

    levels = json.loads(args.levels)
    total = args.total if args.total is not None else sum(levels.values())
    exposure = calc_exposure(levels, total)
    high_ratio = calc_high_risk_ratio(levels.get('restricted', 0), levels.get('confidential', 0), total)

    if args.mode == 'exposure':
        print(json.dumps({"exposure": exposure}, ensure_ascii=False))
    elif args.mode == 'risk':
        r = calc_compliance_risk(high_ratio, args.audit_coverage, args.pii_unhandled)
        print(json.dumps({"compliance_risk": r, "high_risk_ratio": high_ratio}, ensure_ascii=False))
    else:
        r = calc_compliance_risk(high_ratio, args.audit_coverage, args.pii_unhandled)
        print(json.dumps({
            "levels": levels,
            "total_entries": total,
            "exposure": exposure,
            "high_risk_ratio": high_ratio,
            "compliance_risk": r,
        }, ensure_ascii=False))


if __name__ == '__main__':
    main()
