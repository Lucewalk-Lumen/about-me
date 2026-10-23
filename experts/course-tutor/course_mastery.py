#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
课程伴学 · 学情洞察（course_mastery.py）

功能（对应设计稿  闭环增强 A / D / E / F / G）
------------------------------------------------
- A 知识点掌握画像：按知识点聚合该生 收敛/部分/卡住 率，生成个人掌握画像；薄弱点优先补练。
- D 匿名同伴基准：班级掌握度中位 vs 个人，输出「领先/落后 X 个百分点」（仅聚合，不出名单）。
- E 教师端学情异常预警：连续卡住学生 / 班级共性薄弱知识点 / 活跃度骤降学生，自动标红。
- F 内容覆盖缺口：课程知识点全集 vs 实际练过的知识点，列出未练到的点。
- G 学习路径推荐：依掌握画像 + 知识点依赖（可选）给出「先补 X 再练 Y」的顺序建议。

数据源
------
- Usage 文件 `usage` 表导出 JSON（每行：学号 + 知识点 + 结果 + 时间 …），口径同 course_report.py：
  聚合前先过 §4.2 过滤（教师端行 / 空学号 / 测试号 0000）。
- 知识点全集 / 依赖关系由教师从课程资产提供（JSON），缺失时对应能力降级跳过。

设计要点
--------
- 纯标准库；输出纯文本标记，避免 GBK 控制台 emoji 崩溃。
- 聚合函数全部为纯函数，可被 `_test_course_mastery.py` 直接 import 做绿红双证。
- 隐私：面向学生的输出只含聚合百分比，不含他人名单；教师端异常清单带学号（教师可见）。

用法
----
    python3 course_mastery.py insight --usage <usage.json> [--roster <roster.json>]
        [--prev-usage <上周 usage.json>] [--kp-universe <全集.json>] [--deps <依赖.json>]
        [--student <学号>] [--week <教学周>] [--out report.md]
"""

import argparse
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def _load_report_mod():
    spec = importlib.util.spec_from_file_location(
        "course_report", os.path.join(HERE, "course_report.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


try:
    _cr = _load_report_mod()
except Exception:  # pragma: no cover - 仅当包根缺 course_report 时降级
    _cr = None


def _norm(s):
    return (s or "").strip()


def _median(xs):
    vals = sorted(x for x in xs if x is not None)
    if not vals:
        return None
    n = len(vals)
    mid = n // 2
    if n % 2:
        return vals[mid]
    return (vals[mid - 1] + vals[mid]) / 2.0


# ---------------------------------------------------------------------------
# A 掌握画像
# ---------------------------------------------------------------------------
def mastery_per_kp(rows, student_id=None):
    """按知识点聚合收敛/部分/卡住 → {kp: {converged, partial, stuck, total, rate}}。

    rows 为已归一化（course_report.normalize_row）的行；student_id 给定时只看该生。
    """
    agg = {}
    for r in rows:
        if student_id is not None and _norm(r.get("student_id")) != _norm(student_id):
            continue
        kp = _norm(r.get("kp"))
        if not kp:
            continue
        a = agg.setdefault(kp, {"converged": 0, "partial": 0, "stuck": 0,
                                "unknown": 0, "total": 0})
        res = _norm(r.get("result"))
        if res == "已收敛":
            a["converged"] += 1
        elif res == "部分收敛":
            a["partial"] += 1
        elif res == "卡住":
            a["stuck"] += 1
        else:
            # 未识别的结果（如“未知状态/其它”）显式计数，不再静默丢弃
            a["unknown"] += 1
            continue
        a["total"] += 1
    for a in agg.values():
        a["rate"] = (a["converged"] / a["total"]) if a["total"] else 0.0
    return agg


def overall_rate(rows, student_id=None):
    """整体收敛率（按 KP 行计）。"""
    m = mastery_per_kp(rows, student_id)
    total = sum(a["total"] for a in m.values())
    conv = sum(a["converged"] for a in m.values())
    return (conv / total) if total else 0.0


# ---------------------------------------------------------------------------
# D 匿名同伴基准
# ---------------------------------------------------------------------------
def class_baseline(rows):
    """班级基准：每个知识点「各生收敛率的中位」+ 全体「个人整体收敛率的中位」。"""
    per_kp = mastery_per_kp(rows)
    kp_median = {}
    students = sorted({(_norm(r.get("student_id"))) for r in rows} - {""})
    for kp in per_kp:
        rates = []
        for sid in students:
            m = mastery_per_kp(rows, sid)
            if kp in m and m[kp]["total"]:
                rates.append(m[kp]["rate"])
        med = _median(rates)
        if med is not None:
            kp_median[kp] = med
    overall = _median([overall_rate(rows, s) for s in students]) if students else None
    return {"per_kp_median": kp_median, "overall_median": overall, "students": len(students)}


def delta_vs_baseline(rows, student_id, baseline=None):
    """个人 vs 班级中位：返回 {"overall": +pct, "per_kp": {kp: +pct}}（百分点差）。"""
    base = baseline or class_baseline(rows)
    stu = mastery_per_kp(rows, student_id)
    per_kp = {}
    for kp, m in stu.items():
        if not m["total"]:
            continue
        med = base.get("per_kp_median", {}).get(kp)
        if med is not None:
            per_kp[kp] = (m["rate"] - med) * 100.0
    overall = None
    if base.get("overall_median") is not None:
        overall = (overall_rate(rows, student_id) - base["overall_median"]) * 100.0
    return {"overall": overall, "per_kp": per_kp}


# ---------------------------------------------------------------------------
# F 覆盖缺口
# ---------------------------------------------------------------------------
def coverage_gaps(universe, rows):
    """课程知识点全集 - 实际练过 = 未覆盖清单（排序返回）。"""
    practiced = {_norm(r.get("kp")) for r in rows} - {""}
    uni = {_norm(x) for x in (universe or [])} - {""}
    return sorted(uni - practiced)


# ---------------------------------------------------------------------------
# G 学习路径推荐
# ---------------------------------------------------------------------------
def _order_weak(weak, deps):
    """在薄弱点集合内做拓扑稳定排序：无依赖的先排；成环时按原顺序兜底追加。"""
    weak = list(weak)
    if not deps:
        return weak
    weak_set = set(weak)
    remaining = {k: 0 for k in weak}
    children = {k: [] for k in weak}
    for k in weak:
        for pre in deps.get(k, []):
            if pre in weak_set:
                remaining[k] += 1
                children[pre].append(k)
    order = []
    ready = [k for k in weak if remaining[k] == 0]
    while ready:
        k = ready.pop(0)
        order.append(k)
        for c in children[k]:
            remaining[c] -= 1
            if remaining[c] == 0:
                ready.append(c)
    order += [k for k in weak if k not in set(order)]  # 成环兜底
    return order


def path_suggestion(rows, student_id, deps=None):
    """先补 X 再练 Y：卡住多的优先，其次部分收敛；deps 给定时先补前置。"""
    m = mastery_per_kp(rows, student_id)
    weak = [(kp, a) for kp, a in m.items() if a["total"] and a["rate"] < 1.0]
    weak.sort(key=lambda t: (-t[1]["stuck"], -t[1]["partial"], t[1]["rate"], t[0]))
    return _order_weak([kp for kp, _ in weak], deps)


# ---------------------------------------------------------------------------
# E 教师端异常预警
# ---------------------------------------------------------------------------
def anomalies(rows, prev_rows=None, stuck_ratio=0.5, min_total=2,
              weak_kp_ratio=0.5, drop_ratio=0.3):
    """自动标红：连续卡住学生 / 班级共性薄弱知识点 / 活跃度骤降学生。

    - stuck_students：个人 stuck 占比 ≥ stuck_ratio 且 KP 行数 ≥ min_total；
    - weak_kps：班级某 KP 卡住占比 ≥ weak_kp_ratio 且行数 ≥ min_total；
    - dropped_students：上周有会话、本周会话数降幅 ≥ drop_ratio 的学生
      （会话数 = 去重 (学号, 日期)）。
    """
    students = sorted({(_norm(r.get("student_id"))) for r in rows} - {""})
    stuck_students = []
    for sid in students:
        m = mastery_per_kp(rows, sid)
        total = sum(a["total"] for a in m.values())
        stuck = sum(a["stuck"] for a in m.values())
        if total >= min_total and total and (stuck / total) >= stuck_ratio:
            stuck_students.append(sid)

    weak_kps = []
    for kp, a in mastery_per_kp(rows).items():
        if a["total"] >= min_total and (a["stuck"] / a["total"]) >= weak_kp_ratio:
            weak_kps.append(kp)
    weak_kps.sort()

    dropped = []
    if prev_rows is not None:
        def _sessions(rs):
            out = {}
            for r in rs:
                sid = _norm(r.get("student_id"))
                d = _norm(r.get("date"))[:10]
                if sid and d:
                    out.setdefault(sid, set()).add(d)
            return {k: len(v) for k, v in out.items()}
        prev_s = _sessions(prev_rows)
        cur_s = _sessions(rows)
        for sid in sorted(set(prev_s) & set(cur_s)):
            if cur_s[sid] < prev_s[sid] * (1.0 - drop_ratio):
                dropped.append(sid)

    return {"stuck_students": stuck_students, "weak_kps": weak_kps,
            "dropped_students": dropped}


# ---------------------------------------------------------------------------
# 汇总报告（markdown）
# ---------------------------------------------------------------------------
def build_insight_report(rows, prev_rows=None, universe=None, deps=None,
                         student_id=None, week_label=None):
    """教师端学情洞察报告（聚合与匿名基准；异常清单仅教师可见）。"""
    if _cr is not None:
        rows = _cr.filter_student_rows(rows)
        if prev_rows is not None:
            prev_rows = _cr.filter_student_rows(prev_rows)
    else:
        # §4.2 过滤（教师端/空学号/测试号）未生效，聚合数据可能含脏数据——显式告警，
        # 避免“静默跳过过滤”后产出看似正常的数字。
        _emit("!", "未加载校历/过滤解析器（course_report 缺失），§4.2 过滤【未生效】，"
                     "聚合数据可能含教师端行/空学号/测试号（0000）")
    lines = []
    title = "学情洞察 · %s" % (week_label or "全部教学周")
    lines.append("## %s" % title)
    lines.append("")

    # E 异常预警
    an = anomalies(rows, prev_rows)
    lines.append("### 异常预警（E）")
    lines.append("- 连续卡住学生：%s" % ("、".join(an["stuck_students"]) or "无"))
    lines.append("- 班级共性薄弱知识点：%s" % ("、".join(an["weak_kps"]) or "无"))
    lines.append("- 活跃度骤降学生：%s" % ("、".join(an["dropped_students"]) or "无"))
    lines.append("")

    # A 班级掌握画像
    km = mastery_per_kp(rows)
    lines.append("### 班级掌握画像（A，按知识点）")
    lines.append("")
    lines.append("| 知识点 | 收敛 | 部分 | 卡住 | 收敛率 |")
    lines.append("|---|---|---|---|---|")
    for kp in sorted(km):
        a = km[kp]
        lines.append("| %s | %d | %d | %d | %.0f%% |"
                     % (kp, a["converged"], a["partial"], a["stuck"], a["rate"] * 100))
    lines.append("")

    # D 匿名基准
    base = class_baseline(rows)
    lines.append("### 匿名同伴基准（D）")
    lines.append("- 班级整体收敛率中位：%.0f%%（%d 名学生参与聚合）"
                 % ((base["overall_median"] or 0.0) * 100, base["students"]))
    for kp in sorted(base["per_kp_median"]):
        lines.append("- %s：班级中位 %.0f%%" % (kp, base["per_kp_median"][kp] * 100))
    lines.append("")

    # F 覆盖缺口
    if universe:
        gaps = coverage_gaps(universe, rows)
        lines.append("### 内容覆盖缺口（F）")
        lines.append("- 未练到 %d 个：%s" % (len(gaps), ("、".join(gaps)) or "无"))
        lines.append("")

    # G / D 个人视角
    if student_id:
        path = path_suggestion(rows, student_id, deps)
        lines.append("### 个人视角 · %s（G 路径推荐）" % student_id)
        lines.append("- 建议补练顺序：%s" % (" → ".join(path) or "暂无薄弱点，保持节奏"))
        d = delta_vs_baseline(rows, student_id, base)
        if d["overall"] is not None:
            pos = "领先" if d["overall"] >= 0 else "落后"
            lines.append("- 较班级中位%s %.1f 个百分点（匿名聚合，仅供自我参照）"
                         % (pos, abs(d["overall"])))
        lines.append("")

    lines.append("> 口径：已按 §4.2 过滤（教师端 / 空学号 / 测试号）；基准为匿名聚合，"
                 "不含任何个人名单。")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _emit(prefix, msg):
    sys.stderr.write("[%s] course_mastery: %s\n" % (prefix, msg))


def _load_json(path):
    if not path:
        return None
    return json.load(open(path, "r", encoding="utf-8-sig"))


def _roster_ids(roster_path):
    reg = _load_json(roster_path)
    if reg is None:
        return None
    if isinstance(reg, list):
        return [_cr._row_get(r, "学号", "student_id") for r in reg] if _cr else []
    return reg.get("ids") or reg.get("roster") or []


def _cmd_insight(args):
    if _cr is None:
        _emit("FAIL", "未加载校历解析器（course_report 缺失），无法生成洞察")
        return 2
    usage = _load_json(args.usage) or []
    prev = _load_json(args.prev_usage) if args.prev_usage else None
    universe = _load_json(args.kp_universe) if args.kp_universe else None
    if isinstance(universe, dict):
        universe = universe.get("kps") or []
    deps = _load_json(args.deps) if args.deps else None
    week_label = args.week
    if not week_label:
        weeks = sorted({_cr.resolve_week_key(_cr.normalize_row(r), None) for r in usage})
        week_label = weeks[-1] if weeks else None
        # 洞察默认看全部数据（画像/基准跨周更稳），week 仅用于标题
    md = build_insight_report(usage, prev, universe, deps, args.student, week_label)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(md + "\n")
        _emit("OK", "洞察报告已写出: %s" % args.out)
    else:
        print(md)
    return 0


def main(argv):
    parser = argparse.ArgumentParser(description="课程伴学学情洞察（画像/基准/异常/缺口/路径）")
    sub = parser.add_subparsers(dest="cmd")
    pi = sub.add_parser("insight", help="生成学情洞察报告")
    pi.add_argument("--usage", required=True, help="usage 表 JSON")
    pi.add_argument("--roster", help="名册 JSON（保留参数，当前报告不依赖在册数）")
    pi.add_argument("--prev-usage", dest="prev_usage", help="上一周期 usage JSON（活跃度骤降检测）")
    pi.add_argument("--kp-universe", dest="kp_universe", help="知识点全集 JSON（list 或 {kps:[...]})")
    pi.add_argument("--deps", help="知识点依赖 JSON {kp: [前置...]}")
    pi.add_argument("--student", help="追加个人视角（路径推荐 + 匿名基准对比）")
    pi.add_argument("--week", help="报告标题用的教学周标签")
    pi.add_argument("--out", help="markdown 输出路径")
    pi.set_defaults(func=_cmd_insight)

    if not argv[1:]:
        parser.print_help(sys.stderr)
        return 2
    args = parser.parse_args(argv[1:])
    if not getattr(args, "func", None):
        parser.print_help(sys.stderr)
        return 2
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
