#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
课程伴学 · 校历与教学周次判定（course_calendar.py）

功能（对应设计稿 ：校历录入与学习周次判定）
------------------------------------------------
- 读入校历 JSON（Hub 文件 `calendar` 子表导出 / 或对话式录入生成），把任意会话日期
  映射到「教学周序号 + 学期标识」，得到统一口径的 `teach_week` 标签（如 `2026-秋-W3`）。
- 未录校历时回退为 ISO 周（`2026-W39`）并显式标注「未对齐校历」，不阻断统计。
- 按学生某教学周的会话集合判定「周状态」：正常 / 滞后 / 缺勤 / 假期 / 考试周 / 非教学周。

设计要点
--------
- 纯标准库（datetime / json / argparse / sys / os），无第三方依赖，学生端也可直接 import。
- 输出统一用纯文本标记 `[OK]/[FAIL]/[!]`，避免 Windows GBK 控制台渲染 emoji 崩溃。
- 所有判定函数均为**纯函数**，可被 `_test_course_calendar.py` 直接 import 做绿红双证。

校历 JSON 结构（与数据中枢 `calendar` 子表对齐）
-----------------------------------------------------------------------------
{
  "term": "2026-秋",                 // 学期标识
  "term_start": "2026-09-07",        // 学期第一周周一（ISO 日期）
  "total_weeks": 18,                 // 教学周总数
  "weeks": [                         // 逐周展开
    {"week_no": 1, "week_start": "2026-09-07", "week_end": "2026-09-13",
     "week_type": "教学", "study_days": "一,三,五", "note": ""},
    {"week_no": 7, "week_start": "2026-10-19", "week_end": "2026-10-25",
     "week_type": "假期", "study_days": "", "note": "国庆调休"},
    {"week_no": 17, "week_start": "2026-12-28", "week_end": "2027-01-03",
     "week_type": "考试", "study_days": "", "note": "期末考试周"}
  ]
}

term_config JSON（学期参数 + 预警阈值，对应 `term_config` 子表）
---------------------------------------------------------------
{
  "term_start": "2026-09-07",
  "total_weeks": 18,
  "required_hours_per_week": 3.0,    // 周建议学时（小时）
  "required_hours_per_course": 54.0, // 总建议学时（小时）
  "warn_idle_days": 7,               // 超期未学阈值（天）
  "warn_deficit_ratio": 0.7,         // 周学时不足比例阈值
  "warn_enabled": true
}
"""

import argparse
import json
import os
import sys
from datetime import date, datetime


# 周类型枚举（与 `calendar.week_type` 对齐）
WEEK_TYPE_TEACH = "教学"
WEEK_TYPE_HOLIDAY = "假期"
WEEK_TYPE_EXAM = "考试"
WEEK_TYPE_MAKEUP = "补课"
WEEK_TYPE_PRACTICE = "实践"

# 周状态枚举（week_status 返回值）
STATUS_NORMAL = "正常"
STATUS_LAGGING = "滞后"
STATUS_ABSENT = "缺勤"
STATUS_HOLIDAY = "假期"
STATUS_EXAM = "考试周"
STATUS_NONTEACH = "非教学周"

# 周状态里「不参与滞后判定」的类型
_NON_LAGGING_TYPES = (WEEK_TYPE_HOLIDAY, WEEK_TYPE_EXAM, WEEK_TYPE_MAKEUP, WEEK_TYPE_PRACTICE)


def _parse_date(value):
    """把 'YYYY-MM-DD' 或 datetime 解析为 date；非法输入抛 ValueError。"""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        s = value.strip()
        if " " in s:
            s = s.split(" ")[0]
        if "T" in s:
            s = s.split("T")[0]
        return datetime.strptime(s, "%Y-%m-%d").date()
    raise ValueError("无法解析的日期: %r" % (value,))


def load_json(path):
    """读 JSON（utf-8-sig 剥离 BOM，与全包读取口径一致）。"""
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def compute_teach_week(calendar, session_date):
    """返回 (week_no:int|None, term:str|None)。

    命中规则：week_start <= session_date <= week_end 的那一行。
    无命中（落在假期/未排/学期外）→ (None, None)，由调用方按「非教学周」处理。
    """
    if not calendar:
        return (None, None)
    d = _parse_date(session_date)
    term = calendar.get("term")
    for w in calendar.get("weeks", []) or []:
        try:
            ws = _parse_date(w.get("week_start"))
            we = _parse_date(w.get("week_end"))
        except (ValueError, TypeError):
            continue
        if ws <= d <= we:
            try:
                return (int(w.get("week_no")), term)
            except (TypeError, ValueError):
                return (None, None)
    return (None, None)


def iso_week_label(session_date):
    """ISO 周标签 `YYYY-Www`（如 `2026-W39`），未对齐校历时用作回退口径。"""
    d = _parse_date(session_date)
    y, w, _ = d.isocalendar()
    return "%d-W%02d" % (y, w)


def teach_week_label(calendar, session_date):
    """返回 (label:str, aligned:bool)。

    - 校历命中 → (`2026-秋-W3`, True)
    - 未录校历 / 未命中 → (ISO 周标签, False)，调用方应标注「未对齐校历」
    """
    wn, term = compute_teach_week(calendar, session_date)
    if wn is not None:
        t = term or "term"
        return ("%s-W%d" % (t, wn), True)
    return (iso_week_label(session_date), False)


def week_type_of(calendar, week_no):
    """返回校历中指定教学周的 week_type；week_no 为 None 或查不到返回 None。"""
    if not calendar or week_no is None:
        return None
    for w in calendar.get("weeks", []) or []:
        try:
            if int(w.get("week_no")) == int(week_no):
                return w.get("week_type")
        except (TypeError, ValueError):
            continue
    return None


def _session_minutes(week_sessions):
    """汇总某生某教学周的累计学时（分钟）。week_sessions 为 dict 列表，含 duration_min 键。"""
    total = 0
    for s in week_sessions or []:
        try:
            total += float(s.get("duration_min") or 0)
        except (TypeError, ValueError):
            continue
    return total


def week_status(calendar, term_config, week_sessions, session_date):
    """按学生某教学周的会话集合判定周状态。

    入参
    ----
    - calendar: 校历 JSON（可空）
    - term_config: 学期参数 JSON（含 required_hours_per_week / warn_deficit_ratio）
    - week_sessions: 该生该教学周的会话明细列表（每项含 duration_min），可为空
    - session_date: 用于定位教学周的任一会话日期（YYYY-MM-DD）

    返回：STATUS_* 之一（见文件顶部枚举）。
    """
    wn, _ = compute_teach_week(calendar, session_date)
    if wn is None:
        return STATUS_NONTEACH

    wt = week_type_of(calendar, wn)
    if wt == WEEK_TYPE_HOLIDAY:
        return STATUS_HOLIDAY
    if wt == WEEK_TYPE_EXAM:
        return STATUS_EXAM
    if wt in (WEEK_TYPE_MAKEUP, WEEK_TYPE_PRACTICE):
        # 补课/实践周非强制教学周：无会话记录不得计为缺勤（不纳入缺勤统计），
        # 仅在有会话记录时才继续按时长做滞后/正常判定。
        if not week_sessions or _session_minutes(week_sessions) <= 0:
            return STATUS_NONTEACH

    duration = _session_minutes(week_sessions)
    if not week_sessions or duration <= 0:
        return STATUS_ABSENT

    req_hours = (term_config or {}).get("required_hours_per_week")
    ratio = (term_config or {}).get("warn_deficit_ratio", 0.7)
    try:
        req_min = float(req_hours) * 60.0 if req_hours is not None else 0.0
    except (TypeError, ValueError):
        req_min = 0.0
    if req_min > 0 and duration < req_min * float(ratio):
        return STATUS_LAGGING
    return STATUS_NORMAL


def _emit(prefix, msg):
    sys.stderr.write("[%s] course_calendar: %s\n" % (prefix, msg))


def _cmd_week(args):
    cal = load_json(args.calendar) if args.calendar else None
    label, aligned = teach_week_label(cal, args.date)
    if aligned:
        _emit("OK", "教学周标签: %s" % label)
    else:
        _emit("!", "未对齐校历，回退 ISO 周: %s（建议录入校历）" % label)
    print(label)
    return 0


def _cmd_status(args):
    cal = load_json(args.calendar) if args.calendar else None
    tc = load_json(args.term_config) if args.term_config else {}
    week_sessions = []
    if args.sessions:
        week_sessions = load_json(args.sessions)
        if not isinstance(week_sessions, list):
            week_sessions = []
    st = week_status(cal, tc, week_sessions, args.date)
    _emit("OK", "周状态: %s" % st)
    print(st)
    return 0


def main(argv):
    parser = argparse.ArgumentParser(
        description="课程伴学校历与教学周次判定（week / status）"
    )
    sub = parser.add_subparsers(dest="cmd")

    pw = sub.add_parser("week", help="求某日期的教学周标签")
    pw.add_argument("--calendar", help="校历 JSON 路径（缺省则回退 ISO 周）")
    pw.add_argument("--date", required=True, help="会话日期 YYYY-MM-DD")
    pw.set_defaults(func=_cmd_week)

    ps = sub.add_parser("status", help="求某学生某教学周的周状态")
    ps.add_argument("--calendar", help="校历 JSON 路径")
    ps.add_argument("--term-config", dest="term_config", help="学期参数 JSON 路径")
    ps.add_argument("--sessions", help="该生该周会话明细 JSON 路径（列表，含 duration_min）")
    ps.add_argument("--date", required=True, help="用于定位教学周的会话日期 YYYY-MM-DD")
    ps.set_defaults(func=_cmd_status)

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
