#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
课程伴学 · 周/月学情分布报告（course_report.py）

功能（对应设计稿 ：周/月学情分布报告）
----------------------------------------
- 输入：Usage 文件 `usage` 表导出（按学生 × 知识点 一行） + 名册（算在册人数）
  + 可选 `summaries`（算人均会话数）+ 校历（教学周维度）+ 学期参数 + 课程知识点总数。
- 聚合维度：`teach_week`（教学周，缺省回退 ISO 周）按需再按自然月汇总。
- 输出：markdown 周报 / 月报（本地生成，不写回中枢）+ 可导出 CSV 供下载。
- 隐私：报告仅含聚合与匿名化清单（卡住学生清单带学号——教师端可见，不向外暴露个人原文）。

设计要点
--------
- 纯标准库；输出纯文本标记，避免 GBK 控制台 emoji 崩溃。
- 所有聚合函数为纯函数，可被 `_test_course_report.py` 直接 import 做绿红双证。
- 聚合前先按 `references/teacher_data_contract.md` 的 §4.2 过滤：教师端行 / 空学号 / 测试号(0000)。

用法
----
    python3 course_report.py weekly  --usage <usage.json> --roster <roster.json> \
        [--calendar <cal.json>] [--term-config <tc.json>] [--kp-total N] \
        [--week 2026-秋-W3] [--out report.md] [--csv report.csv]
    python3 course_report.py monthly --usage <usage.json> --roster <roster.json> \
        [--calendar <cal.json>] [--term-config <tc.json>] [--kp-total N] \
        [--month 2026-09] [--out report.md] [--csv report.csv]
"""

import argparse
import csv
import importlib.util
import json
import os
import sys
from datetime import datetime

# ---------- 复用 course_calendar 的教学周标签能力（同包根，学生端亦随包携带）----------
HERE = os.path.dirname(os.path.abspath(__file__))


def _load_calendar_mod():
    spec = importlib.util.spec_from_file_location(
        "course_calendar", os.path.join(HERE, "course_calendar.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


try:
    _cal = _load_calendar_mod()
except Exception:  # pragma: no cover - 仅当包根缺 course_calendar 时降级
    _cal = None


# 结果枚举（与 usage 表「结果」列对齐）
RESULT_CONVERGED = "已收敛"
RESULT_PARTIAL = "部分收敛"
RESULT_STUCK = "卡住"

# 过滤用的来源 / 测试号
SOURCE_TEACHER = "教师端"
TEST_STUDENT_ID = "0000"


def _norm(s):
    return (s or "").strip()


def _row_get(row, *candidates):
    """从一行里取第一个存在的候选键（中英文列名都兼容）。"""
    for c in candidates:
        if c in row and row[c] not in (None, ""):
            return row[c]
    return None


def normalize_row(row):
    """把（中英文皆可的）一行归一成内部 dict。"""
    sid = _row_get(row, "学号", "student_id")
    kp = _row_get(row, "知识点", "kp")
    result = _row_get(row, "结果", "result")
    phase = _row_get(row, "环节", "phase")
    # 历史行「苏格拉底引导」按「首学」口径计入聚合
    if _norm(phase) == "苏格拉底引导":
        phase = "首学"
    source = _row_get(row, "来源", "source")
    date = _row_get(row, "时间", "date", "session_time")
    teach_week = _row_get(row, "teach_week")
    week_iso = _row_get(row, "周次", "week")
    return {
        "student_id": sid,
        "kp": kp,
        "result": result,
        "phase": phase,
        "source": source,
        "date": date,
        "teach_week": teach_week,
        "week_iso": week_iso,
    }


def is_filtered(row):
    """§4.2 聚合前过滤：教师端行 / 空学号 / 测试号(0000) 一律剔除。"""
    sid = _norm(row.get("student_id"))
    src = _norm(row.get("source"))
    if src == SOURCE_TEACHER:
        return True
    if not sid:
        return True
    if sid == TEST_STUDENT_ID:
        return True
    return False


def resolve_week_key(row, calendar):
    """教学周分组键：优先 teach_week 列 → 周次(ISO) 列 → 校历算 → ISO 回退。"""
    tw = _norm(row.get("teach_week"))
    if tw:
        return tw
    wi = _norm(row.get("week_iso"))
    if wi:
        return wi
    date = _norm(row.get("date"))
    if date and _cal is not None:
        try:
            label, _ = _cal.teach_week_label(calendar, date)
            return label
        except Exception as e:
            _emit("!", "校历解析失败，回退 ISO 周：%s" % e)
    if date:
        try:
            d = datetime.strptime(date[:10], "%Y-%m-%d")
            y, w, _ = d.isocalendar()
            return "%d-W%02d" % (y, w)
        except Exception:
            pass
    return "未知周"


def resolve_month_key(row):
    date = _norm(row.get("date"))
    if date:
        # 同时归一化斜杠/短横分隔符，避免 2026/09/08 与 2026-09-08 被 date[:7]
        # 切成 “2026/09” 而和 “2026-09” 落到不同月份桶（此前斜杠分隔符走降级路径）。
        d = _parse_date(date.replace("/", "-"))
        if d is not None:
            return d.strftime("%Y-%m")
    # 没有日期无法定位自然月；教学周标签缺少年月信息时不足以落到某自然月，
    # 返回“未知月”而非用年份段冒充月份（原实现返回年份前缀，会把不同周误归为一个“月”）。
    return "未知月"


def filter_student_rows(rows):
    out = []
    for r in rows:
        nr = normalize_row(r)
        if is_filtered(nr):
            continue
        out.append(nr)
    return out


def _parse_date(s):
    s = _norm(s)
    if not s:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(s[:19] if " " in s else s[:10], fmt)
        except Exception:
            continue
    return None


def aggregate_week(rows, week_label, calendar=None):
    """对某一教学周的学生行做聚合，返回指标 dict。

    calendar 透传至 resolve_week_key，使“按校历定教学周”真正生效
    （此前调用方硬编码 calendar=None，导致校历功能形同虚设）。
    """
    wk_rows = [r for r in rows if resolve_week_key(r, calendar) == week_label]
    active = set()
    kp_records = 0
    converged = partial = stuck = 0
    kp_set = set()
    stuck_students = set()
    sessions = set()
    for r in wk_rows:
        sid = _norm(r.get("student_id"))
        if sid:
            active.add(sid)
        kp_records += 1
        res = _norm(r.get("result"))
        if res == RESULT_CONVERGED:
            converged += 1
        elif res == RESULT_PARTIAL:
            partial += 1
        elif res == RESULT_STUCK:
            stuck += 1
            if sid:
                stuck_students.add(sid)
        kp = _norm(r.get("kp"))
        if kp:
            kp_set.add(kp)
        d = _norm(r.get("date"))
        if sid and d:
            sessions.add((sid, d[:10]))
    total_res = converged + partial + stuck
    conv_rate = (converged / total_res) if total_res else 0.0
    return {
        "week": week_label,
        "active": sorted(active),
        "active_count": len(active),
        "kp_records": kp_records,
        "sessions": len(sessions),
        "converged": converged,
        "partial": partial,
        "stuck": stuck,
        "kp_covered": sorted(kp_set),
        "kp_covered_count": len(kp_set),
        "stuck_students": sorted(stuck_students),
        "conv_rate": conv_rate,
    }


def all_weeks(rows, calendar=None):
    return sorted({resolve_week_key(r, calendar) for r in rows})


def build_weekly_report(usage_rows, roster_ids, calendar=None, term_config=None,
                        kp_total=None, target_week=None):
    """生成某教学周的 markdown 周报。"""
    rows = filter_student_rows(usage_rows)
    enrolled = set(_norm(x) for x in (roster_ids or [])) if roster_ids else None
    enrolled_count = len(enrolled) if enrolled is not None else 0
    weeks = all_weeks(rows, calendar)
    if not weeks:
        return "> 该范围暂无学情记录，未生成周报（防空报）。"
    if target_week and target_week in weeks:
        wk_list = [target_week]
    elif target_week:
        return "> 指定教学周 %s 无学情记录，未生成周报。" % target_week
    else:
        wk_list = [weeks[-1]]  # 默认最新有数据的周

    lines = []
    for wk in wk_list:
        m = aggregate_week(rows, wk, calendar)
        lines.append("## 学情周报 · %s" % wk)
        lines.append("")
        active = m["active_count"]
        enrolled_disp = enrolled_count if enrolled_count else active
        lines.append("- **参与度**：活跃 %d / 在册 %d；人均会话 %.2f；KP 记录 %d 条"
                     % (active, enrolled_disp,
                        (m["sessions"] / active) if active else 0.0, m["kp_records"]))
        lines.append("- **掌握分布**：已收敛 %d / 部分收敛 %d / 卡住 %d（收敛率 %.1f%%）"
                     % (m["converged"], m["partial"], m["stuck"], m["conv_rate"] * 100))
        if m["stuck_students"]:
            lines.append("- **卡住学生**（高亮）：%s" % "、".join(m["stuck_students"]))
        # 知识点覆盖
        if kp_total:
            try:
                kt = int(kp_total)
            except (TypeError, ValueError):
                kt = 0
            if kt:
                covered = m["kp_covered_count"]
                lines.append("- **知识点覆盖**：本周覆盖 %d / 课程共 %d（%.1f%%）"
                             % (covered, kt, (covered / kt) * 100 if kt else 0))
        # 趋势（与上一教学周环比）
        idx = weeks.index(wk)
        if idx > 0:
            prev = aggregate_week(rows, weeks[idx - 1], calendar)
            prev_rate = prev["conv_rate"] * 100
            if enrolled is not None:
                cur_den = enrolled_disp if enrolled_disp else 0
                prev_den = len(enrolled) if enrolled_count else (prev["active_count"] or 1)
                cur_pct = (active / cur_den * 100) if cur_den else 0.0
                prev_pct = (prev["active_count"] / prev_den * 100) if prev_den else 0.0
                act_trend = "%+.1f%%" % (cur_pct - prev_pct)
            else:
                # 无名册则无法计算真实在册占比，禁止伪造“活跃度环比 0%”
                act_trend = "未提供名册/无数据"
            lines.append("- **趋势（环比上周）**：活跃度 %s、收敛率 %+.1f%%"
                         % (act_trend, m["conv_rate"] * 100 - prev_rate))
        # 异常
        if enrolled is not None:
            absent = sorted(enrolled - set(m["active"]))
            lines.append("- **异常**：缺勤学生 %d 人%s"
                         % (len(absent), ("（%s）" % "、".join(absent)) if absent else ""))
        else:
            # 无名册：不得伪造“缺勤 0 人”，显式标记无数据
            lines.append("- **异常**：未提供名册 / 无数据（缺勤率暂不统计）")
        lines.append("")
    return "\n".join(lines)


def build_monthly_report(usage_rows, roster_ids, calendar=None, term_config=None,
                         kp_total=None, target_month=None):
    """生成自然月聚合月报。"""
    rows = filter_student_rows(usage_rows)
    months = sorted({resolve_month_key(r) for r in rows})
    if not months:
        return "> 该范围暂无学情记录，未生成月报。"
    if target_month and target_month in months:
        m_list = [target_month]
    elif target_month:
        return "> 指定月份 %s 无学情记录，未生成月报。" % target_month
    else:
        m_list = [months[-1]]

    lines = []
    for mo in m_list:
        mo_rows = [r for r in rows if resolve_month_key(r) == mo]
        # 月报：把月内所有教学周的聚合再汇总
        weeks_in_month = sorted({resolve_week_key(r, calendar) for r in mo_rows})
        active = set()
        kp_records = 0
        conv = par = stu = 0
        kp_set = set()
        stuck_stu = set()
        for w in weeks_in_month:
            m = aggregate_week(mo_rows, w)
            active.update(m["active"])
            kp_records += m["kp_records"]
            conv += m["converged"]
            par += m["partial"]
            stu += m["stuck"]
            kp_set.update(m["kp_covered"])
            stuck_stu.update(m["stuck_students"])
        total_res = conv + par + stu
        rate = (conv / total_res) if total_res else 0.0
        lines.append("## 学情月报 · %s" % mo)
        lines.append("")
        lines.append("- **参与度**：活跃 %d 人；KP 记录 %d 条；覆盖教学周 %d 个"
                     % (len(active), kp_records, len(weeks_in_month)))
        lines.append("- **掌握分布**：已收敛 %d / 部分收敛 %d / 卡住 %d（收敛率 %.1f%%）"
                     % (conv, par, stu, rate * 100))
        if stuck_stu:
            lines.append("- **共性薄弱（卡住学生）**：%s" % "、".join(sorted(stuck_stu)))
        if kp_total:
            try:
                kt = int(kp_total)
            except (TypeError, ValueError):
                kt = 0
            if kt:
                lines.append("- **知识点覆盖**：本月覆盖 %d / 课程共 %d（%.1f%%）"
                             % (len(kp_set), kt, (len(kp_set) / kt) * 100 if kt else 0))
        lines.append("")
    return "\n".join(lines)


def write_csv(path, usage_rows, calendar=None):
    """导出「按教学周聚合」的 CSV（供教师下载）。"""
    rows = filter_student_rows(usage_rows)
    weeks = all_weeks(rows, calendar)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["教学周", "活跃学生数", "KP记录数", "已收敛", "部分收敛", "卡住",
                    "收敛率", "覆盖知识点数", "卡住学生"])
        for wk in weeks:
            m = aggregate_week(rows, wk, calendar)
            w.writerow([wk, m["active_count"], m["kp_records"], m["converged"],
                        m["partial"], m["stuck"], "%.1f%%" % (m["conv_rate"] * 100),
                        m["kp_covered_count"], "、".join(m["stuck_students"])])


def _emit(prefix, msg):
    sys.stderr.write("[%s] course_report: %s\n" % (prefix, msg))


# ---------------------------------------------------------------------------
# 报告落库（结果收口）：report 子表 add_records 载荷
# ---------------------------------------------------------------------------
def build_report_payload(report_kind, period_label, md_ref=None, csv_ref=None,
                         generated_at=None):
    """构造 report 子表写入载荷（smartsheet add_records 形态）。

    列标题口径：类型 / 周期 / 生成时间 / MD 存址 / CSV 存址（建库时按此建列；
    实际列名以线上表为准，此处为契约缺省）。
    """
    gen = generated_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _fv(field, text):
        return {"field": field, "text_value": {"items": [{"text": text or "", "type": "text"}]}}

    return {"records": [{"field_values": [
        _fv("类型", report_kind),
        _fv("周期", period_label),
        _fv("生成时间", gen),
        _fv("MD 存址", md_ref),
        _fv("CSV 存址", csv_ref),
    ]}]}


def _cmd_push(args):
    payload = build_report_payload(args.kind, args.period, args.md, args.csv,
                                   args.generated_at)
    payload_json = json.dumps(payload, ensure_ascii=False)
    if not args.do_exec:
        print(payload_json)
        return 0
    tdoc_py = args.tdoc_py or os.environ.get("TDOC_PY")
    if not tdoc_py:
        _emit("!", "未设置 TDOC_PY / --tdoc-py，仅输出载荷不执行；"
                   "可把上方 JSON 经 course_tdoc.py 透传写入 report 子表")
        print(payload_json)
        return 0
    import subprocess
    wrapper = os.path.join(HERE, "course_tdoc.py")
    cmd = [sys.executable, wrapper, tdoc_py, "tdoc_call", payload_json]
    _emit("OK", "经 course_tdoc.py 透传执行 tdoc_call（api_base 默认权威端点）")
    return subprocess.call(cmd)


def _cmd_weekly(args):
    usage = json.load(open(args.usage, "r", encoding="utf-8-sig"))
    roster = []
    if args.roster:
        reg = json.load(open(args.roster, "r", encoding="utf-8-sig"))
        if isinstance(reg, list):
            roster = [_row_get(r, "学号", "student_id") for r in reg]
        elif isinstance(reg, dict):
            roster = reg.get("ids") or reg.get("roster") or []
    cal = json.load(open(args.calendar, "r", encoding="utf-8-sig")) if args.calendar else None
    tc = json.load(open(args.term_config, "r", encoding="utf-8-sig")) if args.term_config else None
    md = build_weekly_report(usage, roster, cal, tc, args.kp_total, args.week)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(md + "\n")
        _emit("OK", "周报已写出: %s" % args.out)
    else:
        print(md)
    if args.csv:
        write_csv(args.csv, usage, cal)
        _emit("OK", "周报 CSV 已写出: %s" % args.csv)
    return 0


def _cmd_monthly(args):
    usage = json.load(open(args.usage, "r", encoding="utf-8-sig"))
    roster = []
    if args.roster:
        reg = json.load(open(args.roster, "r", encoding="utf-8-sig"))
        if isinstance(reg, list):
            roster = [_row_get(r, "学号", "student_id") for r in reg]
        elif isinstance(reg, dict):
            roster = reg.get("ids") or reg.get("roster") or []
    cal = json.load(open(args.calendar, "r", encoding="utf-8-sig")) if args.calendar else None
    tc = json.load(open(args.term_config, "r", encoding="utf-8-sig")) if args.term_config else None
    md = build_monthly_report(usage, roster, cal, tc, args.kp_total, args.month)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(md + "\n")
        _emit("OK", "月报已写出: %s" % args.out)
    else:
        print(md)
    if args.csv:
        write_csv(args.csv, usage, cal)
        _emit("OK", "月报 CSV 已写出: %s" % args.csv)
    return 0


def main(argv):
    parser = argparse.ArgumentParser(description="课程伴学周/月学情报告（weekly / monthly / push）")
    sub = parser.add_subparsers(dest="cmd")

    pw = sub.add_parser("weekly", help="生成周报")
    pw.add_argument("--usage", required=True, help="usage 表 JSON")
    pw.add_argument("--roster", help="名册 JSON（算在册人数）")
    pw.add_argument("--calendar", help="校历 JSON")
    pw.add_argument("--term-config", dest="term_config", help="学期参数 JSON")
    pw.add_argument("--kp-total", dest="kp_total", type=int, help="课程知识点总数")
    pw.add_argument("--week", help="指定教学周（缺省取最新有数据周）")
    pw.add_argument("--out", help="markdown 输出路径")
    pw.add_argument("--csv", help="CSV 输出路径")
    pw.set_defaults(func=_cmd_weekly)

    pm = sub.add_parser("monthly", help="生成月报")
    pm.add_argument("--usage", required=True, help="usage 表 JSON")
    pm.add_argument("--roster", help="名册 JSON")
    pm.add_argument("--calendar", help="校历 JSON")
    pm.add_argument("--term-config", dest="term_config", help="学期参数 JSON")
    pm.add_argument("--kp-total", dest="kp_total", type=int, help="课程知识点总数")
    pm.add_argument("--month", help="指定自然月 YYYY-MM")
    pm.add_argument("--out", help="markdown 输出路径")
    pm.add_argument("--csv", help="CSV 输出路径")
    pm.set_defaults(func=_cmd_monthly)

    pp = sub.add_parser("push", help="生成报告落库载荷（report 子表）；设 TDOC_PY 可透传执行")
    pp.add_argument("--kind", default="周报", choices=["周报", "月报"], help="报告类型")
    pp.add_argument("--period", required=True, help="周期标签（教学周或月份）")
    pp.add_argument("--md", help="markdown 存址")
    pp.add_argument("--csv", help="CSV 存址")
    pp.add_argument("--generated-at", dest="generated_at", help="生成时间（缺省取当前）")
    pp.add_argument("--exec", dest="do_exec", action="store_true",
                    help="经包根 course_tdoc.py 透传执行（需 TDOC_PY 或 --tdoc-py）")
    pp.add_argument("--tdoc-py", dest="tdoc_py", help="tencentdocs.py 绝对路径")
    pp.set_defaults(func=_cmd_push)

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
