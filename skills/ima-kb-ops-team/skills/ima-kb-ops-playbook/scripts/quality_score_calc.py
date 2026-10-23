#!/usr/bin/env python3
"""质量评分计算器 — 五维加权评分 + 统计分析 + 等级判定"""
import argparse, json, sys

def calc_quality(accuracy, completeness, consistency, timeliness, retrievability):
    """五维加权评分"""
    score = accuracy*0.3 + completeness*0.2 + consistency*0.2 + timeliness*0.15 + retrievability*0.15
    return round(score * 5, 1)  # 转换为50分制（×5 使满分=50）

def grade(score):
    if score >= 40: return "优秀"
    if score >= 30: return "良好"
    if score >= 20: return "合格"
    return "不合格"

def batch_calc(entries):
    results = []
    for e in entries:
        s = calc_quality(e['accuracy'], e['completeness'], e['consistency'], e['timeliness'], e['retrievability'])
        results.append({**e, 'score': s, 'grade': grade(s)})
    avg = round(sum(r['score'] for r in results) / len(results), 1) if results else 0
    return results, avg

def main():
    p = argparse.ArgumentParser(description="质量评分计算")
    p.add_argument('--mode', choices=['single', 'batch', 'stats'], default='single')
    p.add_argument('--accuracy', type=float, help='准确性 0-10')
    p.add_argument('--completeness', type=float, help='完整性 0-10')
    p.add_argument('--consistency', type=float, help='一致性 0-10')
    p.add_argument('--timeliness', type=float, help='时效性 0-10')
    p.add_argument('--retrievability', type=float, help='可检索性 0-10')
    p.add_argument('--entries', type=str, help='JSON 数组，每项含五维评分')
    args = p.parse_args()

    if args.mode == 'single':
        if not all([args.accuracy, args.completeness, args.consistency, args.timeliness, args.retrievability]):
            print("ERROR: 五维评分均为必填"); sys.exit(1)
        s = calc_quality(args.accuracy, args.completeness, args.consistency, args.timeliness, args.retrievability)
        print(json.dumps({"score": s, "grade": grade(s)}, ensure_ascii=False))

    elif args.mode == 'batch':
        if not args.entries: print("ERROR: --entries 必填"); sys.exit(1)
        entries = json.loads(args.entries)
        results, avg = batch_calc(entries)
        print(json.dumps({"results": results, "average": avg, "count": len(results)}, ensure_ascii=False))

    elif args.mode == 'stats':
        if not args.entries: print("ERROR: --entries 必填"); sys.exit(1)
        entries = json.loads(args.entries)
        scores = [calc_quality(e['accuracy'], e['completeness'], e['consistency'], e['timeliness'], e['retrievability']) for e in entries]
        grades = [grade(s) for s in scores]
        stats = {
            "count": len(scores),
            "average": round(sum(scores)/len(scores), 1),
            "max": max(scores),
            "min": min(scores),
            "std": round((sum((s-sum(scores)/len(scores))**2 for s in scores)/len(scores))**0.5, 2),
            "distribution": {
                "excellent": grades.count("优秀"),
                "good": grades.count("良好"),
                "pass": grades.count("合格"),
                "fail": grades.count("不合格")
            }
        }
        print(json.dumps(stats, ensure_ascii=False))

if __name__ == '__main__':
    main()
