#!/usr/bin/env python3
"""自动更新同步调度计算器 — 源分级同步周期、SLA 合规率、日增量、全量重放窗口
闭式模型：周期由源级别决定（P0=1h/P1=6h/P2=24h/P3=168h），合规判定 = 周期 ≤ SLA。
增量条目数 = 日更新率 × 周期小时数 / 24。峰值并发导入 = Σ max(单源增量, 1)。
"""
import argparse, json, sys

LEVEL_CYCLE_HOURS = {"P0": 1, "P1": 6, "P2": 24, "P3": 168}


def source_cycle(level):
    return LEVEL_CYCLE_HOURS.get(level, 24)


def is_compliant(level, sla_hours):
    """周期 ≤ SLA 即新鲜度合规"""
    return source_cycle(level) <= sla_hours


def daily_import_items(rate_per_day, level):
    """日导入量 = 源日更新率（增量口径，与周期无关；周期只影响单次批大小）"""
    return max(0, rate_per_day)


def peak_batch_items(rate_per_day, level):
    """单批导入量 = 日更新率 × 周期 / 24（P0 实时源批小频高，P3 批大频低）"""
    c = source_cycle(level)
    return round(rate_per_day * c / 24, 1)


def schedule_sources(sources):
    out = []
    for s in sources:
        level = s.get("level", "P2")
        sla = s.get("sla_hours", 24)
        rate = s.get("rate_per_day", 0)
        out.append({
            "name": s.get("name", "unknown"),
            "level": level,
            "cycle_hours": source_cycle(level),
            "sla_hours": sla,
            "compliant": is_compliant(level, sla),
            "daily_items": daily_import_items(rate, level),
            "peak_batch_items": peak_batch_items(rate, level),
        })
    return out


def summarize(sources):
    rows = schedule_sources(sources)
    total_daily = sum(r["daily_items"] for r in rows)
    peak_batch = sum(max(r["peak_batch_items"], 1.0) for r in rows)
    compliant = sum(1 for r in rows if r["compliant"])
    sla_rate = round(compliant / len(rows), 4) if rows else 0.0
    return {
        "sources": rows,
        "total_daily_items": total_daily,
        "peak_concurrent_batch_items": round(peak_batch, 1),
        "sla_compliance_rate": sla_rate,
        "full_replay_window_days": 7,  # 全量重放建议每周一次（幂等去重）
    }


def main():
    p = argparse.ArgumentParser(description="自动更新同步调度计算")
    p.add_argument('--mode', choices=['schedule', 'compliance', 'full'], default='full')
    p.add_argument('--sources', type=str,
                   help='JSON 数组：[{"name":"法规库","level":"P0","sla_hours":1,"rate_per_day":20}, ...]')
    args = p.parse_args()

    if not args.sources:
        print("ERROR: --sources 必填"); sys.exit(1)
    sources = json.loads(args.sources)
    if not isinstance(sources, list) or not sources:
        print("ERROR: --sources 必须是非空 JSON 数组"); sys.exit(1)

    result = summarize(sources)
    if args.mode == 'schedule':
        print(json.dumps({"sources": result["sources"]}, ensure_ascii=False))
    elif args.mode == 'compliance':
        print(json.dumps({
            "sla_compliance_rate": result["sla_compliance_rate"],
            "non_compliant": [r["name"] for r in result["sources"] if not r["compliant"]],
        }, ensure_ascii=False))
    else:
        print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
