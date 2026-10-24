#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
import_school_calendar.py — 校历 / 课表导入器（N5-a）。

用途
----
把用户手上的校历（学期起始日、总周数、周次构成、自定义停课日）与课表（课程行）
转成排程唯一可直接消费的 term-space.json，并在放行前做完整合法性判定。
**图片 / PDF 校历不在本脚本处理范围**：必须先由 fact-verifier 双通道转写成 JSON
再导入，导入器不做 OCR。

输入
----
  JSON：{ "term_start": "2026-09-07", "weeks": 20,
          "week_constitution": [{"from":1,"to":16,"kind":"teaching"}, ...],
          "holidays": [{"name":"运动会","start":"...","end":"...","kind":"break"}],
          "courses": [ {"title":"高等数学","weekday":1,"start":"08:00","end":"09:40",
                         "location":"乐学楼301","weeks_rule":"range:1-16","teacher":"张三"} ] }
        CSV：课程行表，列名映射见下方 CSV_COLUMNS；term_start/weeks 由
             --term-start / --weeks 提供（CSV 表本身不承载学期元信息）。
  --format json|csv 可强制指定，缺省按扩展名判定。

输出
----
  term-space.json（含周次索引表、周次构成、停课日、展开后的课次日期），
  默认写到 %USERPROFILE%/.schedule-planner/term-space.json；
  stdout 打印校验报告与正负例判定结论。加 --dry-run 只报告不落盘。

错误码（可读性优先，一眼看出该改什么）
--------------------------------------
  E001 MISSING_FIELD            缺必需字段（一次性列全部缺口，不零敲碎打）
  E002 TERM_START_NOT_MONDAY    学期起始日不是周一（--force 可放行但须声明偏差）
  E003 WEEKS_OUT_OF_RANGE       总周数越界，须 ∈ [1,40]
  E004 DATE_FORMAT_INVALID      日期格式非法，须 YYYY-MM-DD
  E005 RANGE_INVERTED           起止倒挂（周次区间 / 停课日区间）
  E006 TIME_FORMAT_INVALID      时间格式非法，须 HH:MM
  E007 TIME_OUT_OF_BOUNDS       时间越界或 end<=start（允许区间 06:00–22:30）
  E008 WEEKDAY_OUT_OF_RANGE     星期越界，须 1–7 或 Mon–Sun
  E009 WEEKS_RULE_UNPARSEABLE   周次规则不可解析（如「单双周」混写、range 端点倒置）
  E010 EMPTY_TITLE              课程名为空
  E011 SCHEDULE_OVERLAP         同一天同一时段课次重叠
  E012 WEEK_INDEX_OUT_OF_TERM   周次超出学期总周数
  E013 HOLIDAY_CONFLICT         课次落在已放行节假日/调休上班日上且未声明 override（告警，不静默放行）
  E014 FORMAT_UNSUPPORTED       输入格式不支持（图片/PDF/未知扩展名）
  E-PKG-WRITE                   拒绝写入包内目录（包内只读基线）

退出码
------
  0  判定通过并成功写出 term-space.json（--dry-run 同样返回 0）
  1  命令行参数错误 / 用法错误
  2  校验未通过被拒绝（含 E013 未 ack 的冲突）
  3  输入文件缺失 / 不可读 / 解析失败
  4  拒绝写入包内目录（E-PKG-WRITE）

用法
----
  python import_school_calendar.py calendar.json
  python import_school_calendar.py courses.csv --term-start 2026-09-07 --weeks 20
  python import_school_calendar.py --selftest
  python import_school_calendar.py calendar.json --dry-run --report

仅依赖 Python 标准库，无第三方包要求。已实跑于 Windows + Python 3.13。
"""

import argparse
import csv as csvmod
import importlib.util
import json
import os
import sys
from datetime import datetime, timedelta

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
PKG_ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))  # scripts -> <skill> -> skills -> <pkg>

WEEKDAY_CN = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
WEEKDAY_EN = {"mon": 1, "tue": 2, "wed": 3, "thu": 4, "fri": 5, "sat": 6, "sun": 7}
WEEKDAY_CN2NUM = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "日": 7, "天": 7}

DAY_MIN, DAY_MAX = "06:00", "22:30"
WEEKS_MIN, WEEKS_MAX = 1, 40

CSV_COLUMNS = {
    # 标准字段名 -> 允许的同义列名（大小写不敏感）
    "title": ["课程", "课程名", "名称", "title", "course", "subject"],
    "weekday": ["星期", "weekday", "day", "day_of_week"],
    "start_time": ["开始", "开始时间", "start", "start_time", "begin"],
    "end_time": ["结束", "结束时间", "end", "end_time"],
    "location": ["地点", "location", "room", "place"],
    "weeks_rule": ["周次", "上课周次", "weeks_rule", "weeks", "week_rule"],
    "teacher": ["教师", "老师", "teacher", "instructor"],
}

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff", ".heic", ".pdf"}


# --------------------------------------------------------------------------
# 工具
# --------------------------------------------------------------------------
def parse_date(text):
    if not isinstance(text, str) or len(text) != 10 or text[4] != "-" or text[7] != "-":
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return None


def parse_time(text):
    if not isinstance(text, str) or len(text) != 5 or text[2] != ":":
        return None
    try:
        return datetime.strptime(text, "%H:%M").time()
    except ValueError:
        return None


def _min_of(text):
    t = parse_time(text)
    return t.hour * 60 + t.minute if t else None


def week_range(term_start, n):
    """第 n 周（1-based）的周一至周日。"""
    first = term_start + timedelta(days=7 * (n - 1))
    return first, first + timedelta(days=6)


def parse_weekday(value):
    """接受 1-7 / int / 'Mon'..'Sun' / '周一'..'周日' / '星期X'。返回 (num, ok)。"""
    if isinstance(value, bool):
        return (None, False)
    if isinstance(value, int):
        return (value, 1 <= value <= 7)
    if isinstance(value, float) and value.is_integer():
        return (int(value), 1 <= int(value) <= 7)
    if not isinstance(value, str):
        return (None, False)
    s = value.strip()
    if not s:
        return (None, False)
    if s.isdigit():
        n = int(s)
        return (n, 1 <= n <= 7)
    low = s.lower()
    if low in WEEKDAY_EN:
        return (WEEKDAY_EN[low], True)
    for key, num in WEEKDAY_CN2NUM.items():
        if s == "周" + key or s == "星期" + key or s == key:
            return (num, True)
    return (None, False)


def parse_weeks_rule(rule, weeks_total, errs, where):
    """解析周次规则，返回 week 列表。不可解析则 append E009 并返回 None。"""
    if rule is None or rule == "" or rule == "all":
        return list(range(1, weeks_total + 1))

    # 也支持 dict 形式 {"type":"range","start":1,"end":9}
    if isinstance(rule, dict):
        rtype = rule.get("type")
        if rtype in ("weekly", "all", None):
            return list(range(1, weeks_total + 1))
        if rtype == "odd":
            return [w for w in range(1, weeks_total + 1) if w % 2 == 1]
        if rtype == "even":
            return [w for w in range(1, weeks_total + 1) if w % 2 == 0]
        if rtype == "range":
            a, b = rule.get("start"), rule.get("end")
            if not isinstance(a, int) or not isinstance(b, int) or a > b:
                errs.append(("E009", "%s 周次规则 range 端点非法/倒置：%r" % (where, rule)))
                return None
            return [w for w in range(a, b + 1) if 1 <= w <= weeks_total]
        if rtype in ("list", "custom_weeks"):
            lst = rule.get("weeks") or rule.get("list") or []
            return [w for w in lst if isinstance(w, int) and 1 <= w <= weeks_total]
        errs.append(("E009", "%s 周次规则类型不可识别：%r" % (where, rtype)))
        return None

    if not isinstance(rule, str):
        errs.append(("E009", "%s 周次规则类型非法（须字符串或对象）：%r" % (where, rule)))
        return None

    s = rule.strip()
    low = s.lower()
    # 「单双周」混写必须被拒绝，因此先检查混写形态
    if ("单" in s and "双" in s) or ("odd" in low and "even" in low):
        errs.append(("E009", "%s 周次规则不可解析（「单周」「双周」混写互斥）：%r" % (where, rule)))
        return None
    if low in ("all", "weekly", "每周", "全周", "全部"):
        return list(range(1, weeks_total + 1))
    if low in ("odd", "单周", "单"):
        return [w for w in range(1, weeks_total + 1) if w % 2 == 1]
    if low in ("even", "双周", "双"):
        return [w for w in range(1, weeks_total + 1) if w % 2 == 0]
    if low.startswith("range:"):
        body = low[len("range:"):]
        for sep in ("-", "~", "..", "至", "到"):
            if sep in body:
                a, b = body.split(sep, 1)
                if not (a.strip().isdigit() and b.strip().isdigit()):
                    errs.append(("E009", "%s 周次规则 range 端点非整数：%r" % (where, rule)))
                    return None
                x, y = int(a.strip()), int(b.strip())
                if x > y:
                    errs.append(("E009", "%s 周次规则 range 端点倒置（%d > %d）：%r" % (where, x, y, rule)))
                    return None
                if x < WEEKS_MIN or y > weeks_total:
                    errs.append(("E012", "%s 周次规则 range 超出学期总周数 %d：%r" % (where, weeks_total, rule)))
                    return None
                return list(range(x, y + 1))
        errs.append(("E009", "%s 周次规则 range 缺少分隔：%r" % (where, rule)))
        return None
    if low.startswith("list:"):
        body = low[len("list:"):]
        parts = [p.strip() for p in body.replace("，", ",").split(",") if p.strip()]
        nums = []
        for p in parts:
            if not p.isdigit():
                errs.append(("E009", "%s 周次规则 list 含非整数 %r" % (where, p)))
                return None
            n = int(p)
            if not (WEEKS_MIN <= n <= weeks_total):
                errs.append(("E012", "%s 周次 %d 超出学期总周数 %d" % (where, n, weeks_total)))
                return None
            nums.append(n)
        if not nums:
            errs.append(("E009", "%s 周次规则 list 为空" % where))
            return None
        return sorted(set(nums))
    # 裸「1-9」「1,3,5」也放行，宽松但确定
    if "-" in s or "~" in s:
        sep = "-" if "-" in s else "~"
        a, b = s.split(sep, 1)
        if a.strip().isdigit() and b.strip().isdigit():
            x, y = int(a.strip()), int(b.strip())
            if x > y:
                errs.append(("E005", "%s 周次区间倒挂：%d > %d" % (where, x, y)))
                return None
            return [w for w in range(x, y + 1) if 1 <= w <= weeks_total]
    if "," in s or "，" in s:
        parts = [p.strip() for p in s.replace("，", ",").split(",") if p.strip()]
        if all(p.isdigit() for p in parts) and parts:
            nums = [int(p) for p in parts]
            bad = [n for n in nums if not (WEEKS_MIN <= n <= weeks_total)]
            if bad:
                errs.append(("E012", "%s 周次 %s 超出学期总周数 %d" % (where, bad, weeks_total)))
                return None
            return sorted(set(nums))
    errs.append(("E009", "%s 周次规则不可解析：%r（允许 all/odd/even/range:a-b/list:n,m）" % (where, rule)))
    return None


# --------------------------------------------------------------------------
# 读取输入
# --------------------------------------------------------------------------
def read_json_payload(path):
    with open(path, "r", encoding="utf-8-sig") as fh:
        try:
            return json.load(fh)
        except ValueError as exc:
            raise ValueError("JSON 解析失败：%s" % exc)


def read_csv_payload(path):
    with open(path, "r", encoding="utf-8-sig", newline="") as fh:
        rows = list(csvmod.DictReader(fh))
    if not rows:
        return {"courses": []}
    alias = {}
    for std, names in CSV_COLUMNS.items():
        for n in names:
            alias[n.lower()] = std
    courses = []
    for i, row in enumerate(rows, start=2):
        norm = {}
        for k, v in row.items():
            if k is None:
                continue
            std = alias.get(k.strip().lower())
            if std and v is not None:
                norm[std] = v.strip()
        courses.append(norm)
    return {"courses": courses, "__csv_rows": len(courses)}


def load_payload(path, forced_format=None):
    ext = os.path.splitext(path)[1].lower()
    ext_handled = True
    fmt = forced_format or (ext.lstrip(".") or "")
    if ext in IMAGE_EXTS:
        raise ValueError(
            "E014 FORMAT_UNSUPPORTED：不支持直接导入 %s 文件。"
            "图片 / PDF 校历须先由 fact-verifier 做双通道转写产出 JSON 后再导入，"
            "本导入器不做 OCR。" % ext
        )
    ext_handled = fmt in ("json", "csv")
    if not ext_handled:
        raise ValueError("E014 FORMAT_UNSUPPORTED：无法判定输入格式 %r（支持 json / csv）" % (ext or path))
    if fmt == "json":
        return read_json_payload(path), "json"
    return read_csv_payload(path), "csv"


# --------------------------------------------------------------------------
# 校验
# --------------------------------------------------------------------------
def _collect_term_meta(payload, args, errs, warns):
    term_start_raw = args.term_start if args.term_start else payload.get("term_start")
    weeks_raw = args.weeks if args.weeks is not None else payload.get(
        "weeks", payload.get("total_weeks", payload.get("weeks_total")))

    missing = []
    if term_start_raw in (None, ""):
        missing.append("term_start（学期第 1 周周一，YYYY-MM-DD）")
    if weeks_raw in (None, ""):
        missing.append("weeks（总周数，整数）")
    if missing:
        errs.append(("E001", "缺必需字段：%s" % "；".join(missing)))
        return None

    ts = parse_date(term_start_raw)
    if ts is None:
        errs.append(("E004", "term_start 日期格式非法：%r（須 YYYY-MM-DD）" % term_start_raw))
        return None
    if ts.weekday() != 0:
        msg = "term_start=%s 是%s，法定必须为周一" % (ts.isoformat(), WEEKDAY_CN[ts.weekday()])
        if args.force:
            warns.append(("E002", "TERM_START_NOT_MONDAY（--force 已放行，报告须声明偏差）：%s" % msg))
        else:
            errs.append(("E002", "TERM_START_NOT_MONDAY：%s；如确需放行请加 --force" % msg))

    if isinstance(weeks_raw, bool) or not isinstance(weeks_raw, int):
        if isinstance(weeks_raw, str) and weeks_raw.strip().isdigit():
            weeks_raw = int(weeks_raw.strip())
        else:
            errs.append(("E003", "weeks 必须是整数：%r" % weeks_raw))
            return None
    if not (WEEKS_MIN <= weeks_raw <= WEEKS_MAX):
        errs.append(("E003", "WEEKS_OUT_OF_RANGE：weeks=%d 越界，须 ∈ [%d,%d]" % (weeks_raw, WEEKS_MIN, WEEKS_MAX)))
        return None

    return {"term_start": ts, "weeks": weeks_raw}


def _collect_constitution(payload, total_weeks, errs):
    raw = payload.get("week_constitution") or payload.get("week_composition") or []
    if isinstance(raw, dict):
        raw = [dict(v, kind=k) for k, v in raw.items()]
    out = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            errs.append(("E004", "week_constitution[%d] 必须是对象" % i))
            continue
        a = item.get("from", item.get("start_week"))
        b = item.get("to", item.get("end_week"))
        kind = item.get("kind") or item.get("type") or "teaching"
        if not isinstance(a, int) or not isinstance(b, int):
            errs.append(("E004", "week_constitution[%d] 的 from/to 必须是整数周次" % i))
            continue
        if a > b:
            errs.append(("E005", "RANGE_INVERTED：week_constitution[%d] 周次倒挂 %d > %d" % (i, a, b)))
            continue
        if a < 1 or b > total_weeks:
            errs.append(("E012", "WEEK_INDEX_OUT_OF_TERM：week_constitution[%d] %d-%d 超出 1-%d" % (i, a, b, total_weeks)))
            continue
        out.append({"from": a, "to": b, "kind": kind})
    return out


def _collect_holidays(payload, term_meta, errs):
    raw = payload.get("holidays") or payload.get("breaks") or []
    out = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            errs.append(("E004", "holidays[%d] 必须是对象" % i))
            continue
        name = item.get("name") or item.get("title") or ""
        if not str(name).strip():
            errs.append(("E010", "holidays[%d] 缺 name/title" % i))
        s_raw = item.get("start") or item.get("date")
        e_raw = item.get("end") or s_raw
        s, e = parse_date(s_raw), parse_date(e_raw)
        if s is None or e is None:
            errs.append(("E004", "holidays[%d] 日期格式非法：start=%r end=%r" % (i, s_raw, e_raw)))
            continue
        if e < s:
            errs.append(("E005", "RANGE_INVERTED：holidays[%d] %s 起止倒挂 (%s > %s)" % (i, name, s, e)))
            continue
        out.append({
            "name": name,
            "start": s.isoformat(),
            "end": e.isoformat(),
            "days": (e - s).days + 1,
            "kind": item.get("kind") or item.get("type") or "break",
            "source": "user_declared",
        })
    return out


def _collect_courses(payload, term_meta, errs, warns):
    raw = payload.get("courses") or payload.get("events") or payload.get("rows") or []
    if isinstance(raw, dict):
        raw = raw.get("courses") or []
    out = []
    seen_slots = {}
    # term_start/weeks 不可用时仍体检周次规则的「写法」，但不再叠加 E012 级联误报
    wtotal = term_meta["weeks"] or WEEKS_MAX
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            errs.append(("E004", "courses[%d] 必须是对象" % i))
            continue
        tag = "courses[%d]%s" % (i, "(%s)" % item.get("title") if item.get("title") else "")

        title = (item.get("title") or item.get("course") or item.get("name") or "").strip()
        if not title:
            errs.append(("E010", "%s 课程名为空" % tag))

        wd_raw = item.get("weekday", item.get("day"))
        wd, ok = parse_weekday(wd_raw)
        if not ok:
            errs.append(("E008", "%s weekday=%r 越界，須 1–7 或 Mon–Sun 或 周一–周日" % (tag, wd_raw)))
            wd = None

        st_raw = item.get("start_time") or item.get("start")
        en_raw = item.get("end_time") or item.get("end")
        st, en = parse_time(st_raw), parse_time(en_raw)
        if st is None:
            errs.append(("E006", "%s start_time=%r 格式非法，須 HH:MM" % (tag, st_raw)))
        if en is None:
            errs.append(("E006", "%s end_time=%r 格式非法，須 HH:MM" % (tag, en_raw)))
        if st and en:
            if en <= st:
                errs.append(("E007", "%s TIME_OUT_OF_BOUNDS：end(%s) <= start(%s)" % (tag, en_raw, st_raw)))
            else:
                lo, hi = _min_of(st_raw), _min_of(en_raw)
                if lo < _min_of(DAY_MIN) or hi > _min_of(DAY_MAX):
                    errs.append(("E007", "%s 时间越界：须落在 %s–%s，实际 %s–%s"
                                 % (tag, DAY_MIN, DAY_MAX, st_raw, en_raw)))

        weeks = parse_weeks_rule(item.get("weeks_rule", item.get("week_rule")),
                                 wtotal, errs, tag)
        if weeks is None:
            weeks = None
        else:
            bad = [w for w in weeks if not (1 <= w <= term_meta["weeks"])]
            if bad and term_meta["weeks"]:
                errs.append(("E012", "%s 周次 %s 超出学期总周数 %d" % (tag, bad, term_meta["weeks"])))

        # 同日同时段重叠检测（按区间相交判定，不是比对相同时间串）
        lo, hi = _min_of(st_raw), _min_of(en_raw)
        if wd and lo is not None and hi is not None and weeks and term_meta["term_start"]:
            for w in weeks:
                mon, _ = week_range(term_meta["term_start"], w)
                day = (mon + timedelta(days=wd - 1)).isoformat()
                bucket = seen_slots.setdefault(day, [])
                clash = [t for (a, b, t) in bucket if lo < b and a < hi]
                if clash:
                    errs.append(("E011", "SCHEDULE_OVERLAP：%s 与 %s 在 %s %s-%s 时段重叠"
                                 % (title, "、".join(clash), day, st_raw, en_raw)))
                else:
                    bucket.append((lo, hi, title))

        out.append({
            "title": title,
            "weekday": wd,
            "weekday_cn": WEEKDAY_CN[wd - 1] if wd else None,
            "start_time": st_raw,
            "end_time": en_raw,
            "location": item.get("location") or "",
            "teacher": item.get("teacher") or "",
            "weeks_rule": item.get("weeks_rule", item.get("week_rule")),
            "weeks": weeks,
            "override_holiday": bool(item.get("override_holiday")),
        })
    return out


def _attach_holiday_view(term_meta, courses, warns):
    """软集成 holiday_lookup：给每周标出法定假日 / 调休上班日，并检查课次冲突。

    找不到 holiday_lookup.py 时降级为不标注（不致命，明确 WARN）。

    返回 (week_view, pending_confirmation)
    """
    week_view = []
    pending = []
    module = _load_holiday_module()
    idx = None
    if module is not None:
        try:
            idx = module.CalendarIndex(os.path.join(PKG_ROOT, "data"), [2026, 2027], allow_predicted=False)
        except Exception as exc:  # 数据源不可用时降级，不阻断导入
            warns.append(("W-HOLIDAY", "节假日数据加载失败，本次未做节假日冲突检查：%s" % exc))
            module = None

    for w in range(1, term_meta["weeks"] + 1):
        mon, sun = week_range(term_meta["term_start"], w)
        entry = {"week": w, "start": mon.isoformat(), "end": sun.isoformat(), "holiday_dates": []}
        if idx is not None:
            cur = mon
            while cur <= sun:
                rec = idx.classify(cur)
                if rec.get("hit"):
                    entry["holiday_dates"].append({
                        "date": rec["date"],
                        "nature": rec["nature"],
                        "source_id": rec["source_id"],
                        "name": rec.get("name"),
                    })
                cur += timedelta(days=1)
        week_view.append(entry)

    # 课次落在节假日/调休上班日上且未声明 override -> 不静默放行
    for entry in week_view:
        if not entry["holiday_dates"]:
            continue
        hit_dates = {h["date"]: h for h in entry["holiday_dates"]}
        for c in courses:
            if not c["weeks"] or not c["weekday"]:
                continue
            if entry["week"] not in c["weeks"]:
                continue
            mon, _ = week_range(term_meta["term_start"], entry["week"])
            day = (mon + timedelta(days=c["weekday"] - 1)).isoformat()
            h = hit_dates.get(day)
            if not h:
                continue
            if c.get("override_holiday"):
                warns.append(("E013(acked)", "%s 第%d周 %s 落在%s（%s），已声明 override_holiday，放行并记档"
                              % (c["title"], entry["week"], day, h["nature"], h["source_id"])))
            else:
                pending.append({
                    "course": c["title"], "week": entry["week"], "date": day,
                    "nature": h["nature"], "source_id": h["source_id"],
                    "reason": "课次落在已放行节假日/调休上班日上且未声明 override",
                })
    return week_view, pending


_HOLIDAY_MODULE_CACHE = {}


def _load_holiday_module():
    if "mod" in _HOLIDAY_MODULE_CACHE:
        return _HOLIDAY_MODULE_CACHE["mod"]
    path = os.path.join(HERE, "holiday_lookup.py")
    if not os.path.isfile(path):
        _HOLIDAY_MODULE_CACHE["mod"] = None
        return None
    try:
        spec = importlib.util.spec_from_file_location("_holiday_lookup_local", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    except Exception:
        mod = None
    _HOLIDAY_MODULE_CACHE["mod"] = mod
    return mod


def validate(payload, args):
    """返回 (term_space, errs, warns, pending)。errs 非空即拒绝。"""
    errs, warns = [], []
    term_meta = _collect_term_meta(payload, args, errs, warns)
    meta_ok = term_meta is not None
    if term_meta is None:
        # term_start / weeks 不可用时不断流：继续体检其余字段，保证「缺口一次性列全」
        term_meta = {"term_start": None, "weeks": 0, "invalid": True}

    constitution = _collect_constitution(payload, term_meta["weeks"], errs)
    holidays = _collect_holidays(payload, term_meta, errs)
    courses = _collect_courses(payload, term_meta, errs, warns)
    if meta_ok:
        week_view, pending = _attach_holiday_view(term_meta, courses, warns)
    else:
        week_view, pending = [], []

    if errs or not meta_ok:
        return (None, errs, warns, [])

    _, last_sun = week_range(term_meta["term_start"], term_meta["weeks"])
    term_space = {
        "schema_version": "1.0",
        "generated_by": "import_school_calendar.py",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "term_start": term_meta["term_start"].isoformat(),
        "term_start_weekday": WEEKDAY_CN[term_meta["term_start"].weekday()],
        "term_end": last_sun.isoformat(),
        "weeks": term_meta["weeks"],
        "forced": bool(args.force),
        "week_constitution": constitution,
        "declared_holidays": holidays,
        "courses": [{k: v for k, v in c.items() if k != "override_holiday" or v} for c in courses],
        "week_index": week_view,
        "pending_confirmation": pending,
    }
    return term_space, errs, warns, pending


# --------------------------------------------------------------------------
# 输出
# --------------------------------------------------------------------------
def report(term_space, errs, warns, pending, source_hint, dry_run):
    print("=" * 68)
    print("校历导入校验报告")
    print("  输入        : %s" % source_hint)
    if term_space:
        print("  term_start  : %s（%s）" % (term_space["term_start"], term_space["term_start_weekday"]))
        print("  term_end    : %s" % term_space["term_end"])
        print("  总周数      : %d" % term_space["weeks"])
        print("  课次行数    : %d" % len(term_space["courses"]))
        print("  停课日      : %d" % len(term_space["declared_holidays"]))
        print("  周次构成    : %s" % (", ".join("%d-%d:%s" % (c["from"], c["to"], c["kind"])
                                             for c in term_space["week_constitution"]) or "-"))
    print("-" * 68)
    for code, msg in warns:
        print("[WARN] %s %s" % (code, msg) if not code.startswith("E013") else "[ACK ] %s %s" % (code, msg))
    for code, msg in errs:
        print("[FAIL] %s %s" % (code, msg))
    for item in pending:
        print("[WARN] E013 %s：第%d周 %s 落在 %s（来源 %s）上且未声明 override —— 不静默放行，已进待确认清单"
              % (item["course"], item["week"], item["date"], item["nature"], item["source_id"]))
    print("-" * 68)
    if errs:
        print("[FAIL] 判定结果：拒绝（%d 项错误，一次性列出如上）" % len(errs))
        return 2
    if pending:
        print("[WARN] 判定结果：放行但存在 %d 项待确认（须 fact-verifier / 用户确认后生效）" % len(pending))
    else:
        print("[OK] 判定结果：放行")
    if dry_run:
        print("[OK] --dry-run：未落盘")
    return 0


def resolve_out_dir(args):
    if args.out_dir:
        out = os.path.abspath(args.out_dir)
    else:
        home = os.environ.get("USERPROFILE") or os.path.expanduser("~")
        out = os.path.join(home, ".schedule-planner")
    return out


def write_term_space(term_space, out_dir):
    pkg = os.path.abspath(PKG_ROOT)
    out = os.path.abspath(out_dir)
    try:
        inside = os.path.commonpath([pkg, out]) == pkg
    except ValueError:  # 不同盘符
        inside = False
    if inside:
        raise RuntimeError("E-PKG-WRITE：禁止写入包内目录 %s（包内 data/ 为只读基线）" % out)
    os.makedirs(out, exist_ok=True)
    target = os.path.join(out, "term-space.json")
    with open(target, "w", encoding="utf-8") as fh:
        json.dump(term_space, fh, ensure_ascii=False, indent=2)
    return target


# --------------------------------------------------------------------------
# 内建 self-test
# --------------------------------------------------------------------------
TERM_ANCHOR = "2026-09-07"
ANCHOR_CASES = [
    (1, "2026-09-07", "2026-09-13"),
    (7, "2026-10-19", "2026-10-25"),
    (18, "2027-01-04", "2027-01-10"),
    (19, "2027-01-11", "2027-01-17"),
    (20, "2027-01-18", "2027-01-24"),
]

BAD_CASES = [
    ("缺 term_start", {"weeks": 20, "courses": []}, "E001"),
    ("term_start 非周一", {"term_start": "2026-09-08", "weeks": 20}, "E002"),
    ("term_start 格式非法", {"term_start": "2026/09/07", "weeks": 20}, "E004"),
    ("周数越界(0)", {"term_start": TERM_ANCHOR, "weeks": 0}, "E003"),
    ("周数越界(41)", {"term_start": TERM_ANCHOR, "weeks": 41}, "E003"),
    ("起止倒挂(课次)", {
        "term_start": TERM_ANCHOR, "weeks": 20,
        "courses": [{"title": "A", "weekday": 1, "start": "10:00", "end": "09:00"}]}, "E007"),
    ("日期格式非法(停课日)", {
        "term_start": TERM_ANCHOR, "weeks": 20,
        "holidays": [{"name": "运动会", "start": "2026-10-01", "end": "2026/10/03"}]}, "E004"),
    ("停课日起止倒挂", {
        "term_start": TERM_ANCHOR, "weeks": 20,
        "holidays": [{"name": "运动会", "start": "2026-10-05", "end": "2026-10-03"}]}, "E005"),
    ("周次规则不可解析", {
        "term_start": TERM_ANCHOR, "weeks": 20,
        "courses": [{"title": "A", "weekday": 1, "start": "08:00", "end": "09:40",
                     "weeks_rule": "单双周"}]}, "E009"),
    ("range 端点倒置", {
        "term_start": TERM_ANCHOR, "weeks": 20,
        "courses": [{"title": "A", "weekday": 1, "start": "08:00", "end": "09:40",
                     "weeks_rule": "range:9-1"}]}, "E009"),
    ("星期越界", {
        "term_start": TERM_ANCHOR, "weeks": 20,
        "courses": [{"title": "A", "weekday": 8, "start": "08:00", "end": "09:40"}]}, "E008"),
    ("课程名为空", {
        "term_start": TERM_ANCHOR, "weeks": 20,
        "courses": [{"title": "   ", "weekday": 1, "start": "08:00", "end": "09:40"}]}, "E010"),
    ("时间越界", {
        "term_start": TERM_ANCHOR, "weeks": 20,
        "courses": [{"title": "A", "weekday": 1, "start": "23:00", "end": "23:50"}]}, "E007"),
    ("课次重叠", {
        "term_start": TERM_ANCHOR, "weeks": 20,
        "courses": [
            {"title": "A", "weekday": 1, "start": "08:00", "end": "09:40"},
            {"title": "B", "weekday": 1, "start": "09:00", "end": "10:40"}]}, "E011"),
]


def run_selftest():
    failed = 0
    print("=" * 68)
    print("import_school_calendar.py 内建 self-test")
    print("-" * 68)

    # 段 1：周次算术锚点（REQUIREMENTS.md 唯一事实锚点）
    ts = parse_date(TERM_ANCHOR)
    if ts is None or ts.weekday() != 0:
        print("[FAIL] 锚点 %s 解析失败或不是周一" % TERM_ANCHOR)
        failed += 1
    else:
        print("[OK] 锚点 %s 确为周一" % TERM_ANCHOR)
    for week, want_a, want_b in ANCHOR_CASES:
        a, b = week_range(ts, week)
        got_a, got_b = a.isoformat(), b.isoformat()
        if (got_a, got_b) == (want_a, want_b):
            print("[OK] 第 %-2d 周 = %s ~ %s" % (week, got_a, got_b))
        else:
            print("[FAIL] 第 %-2d 周 = %s ~ %s（期望 %s ~ %s）" % (week, got_a, got_b, want_a, want_b))
            failed += 1

    args = argparse.Namespace(term_start=None, weeks=None, force=False)

    # 段 2：负例必须被拦（每条都能指名 Benefit 错误码）
    print("-" * 68)
    for label, payload, want_code in BAD_CASES:
        _ts, errs, _w, _p = validate(payload, args)
        codes = [c for c, _ in errs]
        if want_code in codes:
            hit = [m for c, m in errs if c == want_code][0]
            print("[OK] 负例拦截：%-16s -> %s %s" % (label, want_code, hit[:58]))
        else:
            print("[FAIL] 负例漏放行：%-16s 期望 %s，实际 codes=%s" % (label, want_code, codes or "空"))
            failed += 1

    # 段 3：正例必须放行，且缺字段要一次性列全
    print("-" * 68)
    good = {
        "term_start": TERM_ANCHOR,
        "weeks": 20,
        "week_constitution": [{"from": 1, "to": 16, "kind": "teaching"},
                              {"from": 17, "to": 20, "kind": "exam"}],
        "holidays": [{"name": "校运会", "start": "2026-11-05", "end": "2026-11-06"}],
        "courses": [
            {"title": "高等数学", "weekday": 1, "start": "08:00", "end": "09:40",
             "location": "乐学楼301", "weeks_rule": "range:1-16"},
            {"title": "大学英语", "weekday": 3, "start": "10:00", "end": "11:40",
             "location": "外语楼202", "weeks_rule": "odd"},
        ],
    }
    ts_obj, errs, _warns, pending = validate(good, args)
    if errs:
        print("[FAIL] 正例被误拒：%s" % "; ".join("%s %s" % e for e in errs))
        failed += 1
    else:
        w7 = [w for w in ts_obj["week_index"] if w["week"] == 7][0]
        print("[OK] 正例放行：第 7 周 = %s ~ %s，课次 %d 条"
              % (w7["start"], w7["end"], len(ts_obj["courses"])))
        late_weeks = [(w["week"], w["start"], w["end"]) for w in ts_obj["week_index"] if w["week"] == 18]
        for w, s, e in late_weeks:
            print("[OK] 正例放行：第 %d 周 = %s ~ %s" % (w, s, e))

    multi = validate({"weeks": 20, "courses": [{"title": "", "weekday": 9}]}, args)[1]
    codes = sorted({c for c, _ in multi})
    if len(codes) >= 2 and "E001" in codes:
        print("[OK] 缺字段一次性列全：%s（%d 项）" % (",".join(codes), len(multi)))
    else:
        print("[FAIL] 缺口未一次性列出：%s" % codes)
        failed += 1

    # 段 4：周次构成越界必须拦
    _t, errs4, _w4, _p4 = validate(
        {"term_start": TERM_ANCHOR, "weeks": 20,
         "week_constitution": [{"from": 1, "to": 21, "kind": "teaching"}]}, args)
    if any(c == "E012" for c, _ in errs4):
        print("[OK] 周次构成越界拦截：E012")
    else:
        print("[FAIL] 周次构成越界未拦截")
        failed += 1

    print("-" * 68)
    if failed:
        print("[FAIL] SELFTEST 未通过：%d 项失败" % failed)
        return 2
    print("[OK] SELFTEST 通过：锚点周次换算 / %d 个负例拦截 / 正例放行 / 缺口一次性列出"
          % len(BAD_CASES))
    return 0


# --------------------------------------------------------------------------
# 入口
# --------------------------------------------------------------------------
def build_parser():
    p = argparse.ArgumentParser(
        prog="import_school_calendar.py",
        description="校历 / 课表导入器：JSON / CSV 输入，正负例判定，产出 term-space.json",
    )
    p.add_argument("input", nargs="?", help="输入文件路径 (.json / .csv)")
    p.add_argument("--format", choices=["json", "csv"], help="强制指定输入格式")
    p.add_argument("--term-start", help="学期第 1 周周一（CSV 输入时必需）")
    p.add_argument("--weeks", type=int, help="学期总周数（CSV 输入时必需）")
    p.add_argument("--out-dir", help="term-space.json 输出目录（默认 %%USERPROFILE%%/.schedule-planner）")
    p.add_argument("--dry-run", action="store_true", help="只出报告，不落盘")
    p.add_argument("--force", action="store_true", help="放行 E002（term_start 非周一）并在报告声明偏差")
    p.add_argument("--selftest", action="store_true", help="内建断言自检")
    p.add_argument("--report", action="store_true", help="打印完整周次索引表")
    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.selftest:
        return run_selftest()
    if not args.input:
        print("[FAIL] 缺少输入文件路径（或用 --selftest 跑内建断言）")
        return 1
    if not os.path.isfile(args.input):
        print("[FAIL] 输入文件不存在：%s" % args.input)
        return 3

    try:
        payload, fmt = load_payload(args.input, args.format)
    except ValueError as exc:
        print("[FAIL] %s" % exc)
        return 3
    except OSError as exc:
        print("[FAIL] 输入文件不可读：%s" % exc)
        return 3

    term_space, errs, warns, pending = validate(payload, args)
    rc = report(term_space, errs, warns, pending,
                "%s [%s]" % (os.path.abspath(args.input), fmt), args.dry_run)
    if rc != 0 or term_space is None:
        return rc

    if args.report:
        print("-" * 68)
        print("周次索引表")
        for w in term_space["week_index"]:
            mark = ""
            if w["holiday_dates"]:
                mark = "  <- " + ", ".join("%s(%s)" % (h["date"], h["nature"]) for h in w["holiday_dates"])
            print("  第 %-2d 周  %s ~ %s%s" % (w["week"], w["start"], w["end"], mark))

    if args.dry_run:
        print(json.dumps(term_space, ensure_ascii=False, indent=2)[:1200]
              + "\n  ... (dry-run 预览，已截断)")
        return 0

    try:
        target = write_term_space(term_space, resolve_out_dir(args))
    except RuntimeError as exc:
        print("[FAIL] %s" % exc)
        return 4
    print("[OK] 已写出：%s（%d 字节）" % (target, os.path.getsize(target)))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BrokenPipeError:
        sys.exit(0)
