#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_ics.py — 从结构化课表/日程 JSON 生成标准 iCalendar (.ics) 与明细 CSV。

设计目的
--------
日程方案必须能离开聊天框，落到手机日历里，并在课前主动提醒"去哪栋楼"。
本脚本把"周次规则"（每周 / 单周 / 双周 / 指定周次 / 空周排除）翻译成正确的
RRULE + EXDATE，并输出自检报告，防止单周被排成每周这类数量不守恒的错误。

用法
----
    python generate_ics.py input.json --out schedule.ics [--csv schedule.csv] [--report]

输入 JSON 结构
--------------
{
  "term_start": "2026-09-07",          // 第 1 周周一日期 (YYYY-MM-DD)
  "timezone": "Asia/Shanghai",         // 可选，默认 Asia/Shanghai
  "default_alarm_minutes": 10,         // 可选，默认 10（课前提醒）
  "prodid": "-//Schedule Planner//ZH-CN//EN",  // 可选
  "events": [
    {
      "summary": "高等数学",
      "location": "乐学楼301",          // 必须是「楼栋 + 房号」
      "description": "教师：张三",
      "day": 1,                        // 1=周一 ... 7=周日
      "start": "08:00",
      "end": "09:40",
      "week_rule": {"type": "weekly", "count": 16},
      "alarm_minutes": 10              // 可选，覆盖默认值
    }
  ]
}

week_rule.type 取值
-------------------
  weekly         每周；count 或 until 必填其一
  odd            单周（第 1,3,5... 周）；interval=2，首周为第 1 周
  even           双周（第 2,4,6... 周）；interval=2，首周为第 2 周
  range          连续周次区间；需 start_week / end_week
  custom_weeks   指定周次列表；需 weeks: [1,3,5]，区间内其余周用 EXDATE 排除

通用可选字段（任意 type 均可携带）：
  start_week     起始周（weekly/odd/even 亦可用，用于从第 N 周开始）
  exclude_weeks  需要排除的周次（如空周 [1,17,20]）
  exclude_dates  需要排除的具体日期 ["2026-09-07", ...]

仅依赖 Python 标准库，无第三方包要求。
"""

import argparse
import csv
import json
import sys
from datetime import date, datetime, timedelta, timezone

BYDAY = {1: "MO", 2: "TU", 3: "WE", 4: "TH", 5: "FR", 6: "SA", 7: "SU"}
DAY_NAME = {1: "周一", 2: "周二", 3: "周三", 4: "周四", 5: "周五", 6: "周六", 7: "周日"}
RULE_LABEL = {"weekly": "每周", "odd": "单周", "even": "双周",
              "range": "指定区间", "custom_weeks": "指定周次"}


# --------------------------------------------------------------------------- #
# 基础工具
# --------------------------------------------------------------------------- #
def fold(line: str) -> str:
    """RFC 5545 折行：单行不超过 75 字节（按 UTF-8 计），续行以空格开头。"""
    raw = line.encode("utf-8")
    if len(raw) <= 75:
        return line
    out, cur = [], b""
    for ch in line:
        b = ch.encode("utf-8")
        limit = 74 if not out else 73  # 续行首字符是空格，需预留
        if len(cur) + len(b) > limit:
            out.append(cur)
            cur = b if not out else b" " + b
        else:
            cur += b
    if cur:
        out.append(cur)
    return "\r\n ".join(part.decode("utf-8") for part in out)


def esc(text: str) -> str:
    """iCalendar 文本转义。"""
    if text is None:
        return ""
    return (str(text).replace("\\", "\\\\")
                     .replace(";", "\\;")
                     .replace(",", "\\,")
                     .replace("\n", "\\n"))


def parse_hm(value: str) -> tuple:
    hh, mm = value.split(":")
    return int(hh), int(mm)


def ics_dt(d: date, hh: int, mm: int) -> str:
    return f"{d.year:04d}{d.month:02d}{d.day:02d}T{hh:02d}{mm:02d}00"


def ics_date(d: date) -> str:
    return f"{d.year:04d}{d.month:02d}{d.day:02d}"


def now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


# --------------------------------------------------------------------------- #
# 周次规则 → RRULE / 起始日期 / EXDATE
# --------------------------------------------------------------------------- #
def _weeks_from_count_or_until(rule, term_start, base_week, step):
    """按 count 或 until 生成周次序列（step=1 每周，step=2 隔周）。"""
    n = rule.get("count")
    if n is not None:
        return [base_week + step * i for i in range(int(n))]
    if not rule.get("until"):
        raise ValueError("周次规则必须提供 count 或 until")
    until_d = datetime.strptime(rule["until"], "%Y-%m-%d").date()
    anchor = term_start + timedelta(days=(base_week - 1) * 7)
    n = ((until_d - anchor).days // (7 * step)) + 1
    return [base_week + step * i for i in range(max(int(n), 1))]


def resolve(rule: dict, term_start: date, day: int):
    """返回 (rrule, first_date, occurrences, exclude_dates)。

    occurrences 是**扣除空周/排除日期后**的真实事件数，
    用于交付自检的数量守恒校验——单周排成每周、空周漏扣，都会在这里暴露。
    """
    rtype = rule.get("type", "weekly")
    byday = BYDAY[day]

    def week_date(w):
        return term_start + timedelta(days=(w - 1) * 7 + (day - 1))

    # 1) 生成未排除前的完整周次序列
    if rtype == "range":
        sw, ew = int(rule["start_week"]), int(rule["end_week"])
        if ew < sw:
            raise ValueError(f"range 周次非法: {sw}-{ew}")
        gen_weeks = list(range(sw, ew + 1))
        keep = set(gen_weeks)
    elif rtype == "custom_weeks":
        weeks = sorted(int(w) for w in rule["weeks"])
        if not weeks:
            raise ValueError("custom_weeks 的 weeks 不能为空")
        gen_weeks = list(range(weeks[0], weeks[-1] + 1))
        keep = set(weeks)
    elif rtype in ("odd", "even"):
        base = int(rule.get("start_week", 1 if rtype == "odd" else 2))
        if rtype == "odd" and base % 2 == 0:
            base += 1            # 单周必须从奇数周起
        if rtype == "even" and base % 2 == 1:
            base += 1            # 双周必须从偶数周起
        gen_weeks = _weeks_from_count_or_until(rule, term_start, base, 2)
        keep = set(gen_weeks)
    else:  # weekly
        base = int(rule.get("start_week", 1))
        gen_weeks = _weeks_from_count_or_until(rule, term_start, base, 1)
        keep = set(gen_weeks)

    if not gen_weeks:
        raise ValueError(f"周次序列为空: {rule}")

    # 2) 扣除空周与显式排除日期
    keep -= set(int(w) for w in rule.get("exclude_weeks", []))
    exclude_dates = {datetime.strptime(s, "%Y-%m-%d").date()
                     for s in rule.get("exclude_dates", [])}
    generated_dates = [week_date(w) for w in gen_weeks]
    kept_dates = [d for w, d in zip(gen_weeks, generated_dates)
                  if w in keep and d not in exclude_dates]
    if not kept_dates:
        raise ValueError(f"排除后无剩余周次: {rule}")

    # 3) RRULE：COUNT 用生成序列长度，被排除的用 EXDATE 剔除
    span = len(gen_weeks)
    if rtype in ("odd", "even"):
        rrule = f"FREQ=WEEKLY;INTERVAL=2;BYDAY={byday};COUNT={span}"
    else:
        rrule = f"FREQ=WEEKLY;BYDAY={byday};COUNT={span}"

    exclude = sorted((set(generated_dates) - set(kept_dates)) |
                     (exclude_dates & set(generated_dates)))
    return rrule, generated_dates[0], len(kept_dates), exclude


# --------------------------------------------------------------------------- #
# 生成 .ics
# --------------------------------------------------------------------------- #
VTIMEZONE = """BEGIN:VTIMEZONE
TZID:Asia/Shanghai
BEGIN:STANDARD
DTSTART:19700101T000000
TZOFFSETFROM:+0800
TZOFFSETTO:+0800
TZNAME:CST
END:STANDARD
END:VTIMEZONE"""


def build_ics(data: dict) -> tuple:
    tz = data.get("timezone", "Asia/Shanghai")
    term_start = datetime.strptime(data["term_start"], "%Y-%m-%d").date()
    default_alarm = int(data.get("default_alarm_minutes", 10))
    prodid = data.get("prodid", "-//Schedule Planner Team//ZH-CN//EN")
    events = data["events"]

    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", f"PRODID:{prodid}",
             "CALSCALE:GREGORIAN", "METHOD:PUBLISH"]
    lines.extend(VTIMEZONE.strip().split("\n"))   # 统一行分隔，避免混入裸 LF
    total = 0
    rows = []

    for idx, ev in enumerate(events, 1):
        summary = ev["summary"]
        location = ev.get("location", "")
        desc = ev.get("description", "")
        day = int(ev["day"])
        sh, sm = parse_hm(ev["start"])
        eh, em = parse_hm(ev["end"])
        rule = ev.get("week_rule", {"type": "weekly", "count": 16})
        alarm = int(ev.get("alarm_minutes", default_alarm))

        rrule, first, occ, exclude = resolve(rule, term_start, day)
        occurrences = occ if occ is not None else 0
        total += occurrences

        lines.append("BEGIN:VEVENT")
        lines.append(f"UID:sched-{idx:04d}-{first.isoformat()}-{sh:02d}{sm:02d}@schedule-planner")
        lines.append(f"DTSTAMP:{now_stamp()}")
        lines.append(f"DTSTART;TZID={tz}:{ics_dt(first, sh, sm)}")
        lines.append(f"DTEND;TZID={tz}:{ics_dt(first, eh, em)}")
        lines.append(f"RRULE:{rrule}")
        if exclude:
            uniq = sorted(set(exclude))
            lines.append("EXDATE;TZID=%s:%s" % (tz, ",".join(ics_date(d) for d in uniq)))
        lines.append(f"SUMMARY:{esc(summary)}")
        if location:
            lines.append(f"LOCATION:{esc(location)}")
        if desc:
            lines.append(f"DESCRIPTION:{esc(desc)}")
        lines.append("TRANSP:OPAQUE")

        if alarm > 0:
            lines.append("BEGIN:VALARM")
            lines.append("ACTION:DISPLAY")
            lines.append(f"TRIGGER:-PT{alarm}M")
            lines.append("DESCRIPTION:%s" % esc(
                f"课前提醒 {alarm} 分钟｜{summary}"
                + (f"｜{location}" if location else "")))
            lines.append("END:VALARM")

        lines.append("END:VEVENT")

        rows.append({
            "编号": f"E-{idx:03d}",
            "名称": summary,
            "星期": DAY_NAME.get(day, str(day)),
            "开始": ev["start"],
            "结束": ev["end"],
            "地点": location,
            "周次规则": RULE_LABEL.get(rule.get("type", "weekly"), rule.get("type", "")),
            "展开次数": occurrences,
            "提醒(分钟)": alarm,
            "描述": desc,
        })

    lines.append("END:VCALENDAR")
    body = "\r\n".join(fold(l) for l in lines) + "\r\n"
    return body, total, rows


# --------------------------------------------------------------------------- #
# 自检报告
# --------------------------------------------------------------------------- #
def report(rows, total, ics_path, csv_path=None):
    print("=" * 60)
    print("ICS 生成自检报告")
    print("=" * 60)
    print(f"事件模板数（台账条目）: {len(rows)}")
    print(f"展开后实际事件数      : {total}")
    print(f"ICS 文件              : {ics_path}")
    if csv_path:
        print(f"CSV 明细              : {csv_path}")
    print("-" * 60)
    by_rule = {}
    for r in rows:
        by_rule[r["周次规则"]] = by_rule.get(r["周次规则"], 0) + 1
    for k, v in sorted(by_rule.items()):
        print(f"  {k}: {v} 门/项")
    print("-" * 60)
    warns = []
    for r in rows:
        if not r["地点"]:
            warns.append(f"{r['编号']} {r['名称']} 缺少地点（提醒里没有楼栋房号 = 防走错楼失效）")
        if r["展开次数"] == 0:
            warns.append(f"{r['编号']} {r['名称']} 展开次数为 0，请检查周次规则")
    if warns:
        print("[WARN] 警告:")
        for w in warns:
            print(f"   - {w}")
    else:
        print("[OK] 无警告：所有事件均含地点，周次展开正常")
    print("-" * 60)
    print("抽查建议：导入手机日历后，请核对 2-3 个事件的时间与地点。")
    print("=" * 60)


def _safe_stdout():
    """Windows GBK 控制台下中文/符号会抛 UnicodeEncodeError，尽力切到 UTF-8。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def main():
    _safe_stdout()
    ap = argparse.ArgumentParser(description="生成可执行日历 .ics 与明细 CSV")
    ap.add_argument("input", help="课表 JSON 文件路径")
    ap.add_argument("--out", default="schedule.ics", help="输出 .ics 路径")
    ap.add_argument("--csv", default=None, help="输出明细 CSV 路径（可选）")
    ap.add_argument("--report", action="store_true", help="打印自检报告")
    args = ap.parse_args()

    # utf-8-sig 兼容中文用户用记事本保存时带 BOM 的 JSON
    with open(args.input, "r", encoding="utf-8-sig") as f:
        data = json.load(f)

    body, total, rows = build_ics(data)

    with open(args.out, "w", encoding="utf-8", newline="") as f:
        f.write(body)

    if args.csv:
        with open(args.csv, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)

    if args.report:
        report(rows, total, args.out, args.csv)

    return 0


if __name__ == "__main__":
    sys.exit(main())
