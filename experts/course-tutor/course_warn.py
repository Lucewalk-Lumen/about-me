#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
课程伴学 · 学生端学习预警（course_warn.py）

功能（对应设计稿 ：学生端学习预警）
----------------------------------------
- 信号源：Usage 文件 `summaries`（每行含 `学号` + `时间` + `时长`(duration_min)）。
- 配置：Hub `term_config` 的 `warn_idle_days` / `warn_deficit_ratio` / `warn_enabled`。
- 检测（学生在每次会话开场自检时执行）：
  1. 读该生 summaries，取 `max(时间)=最后活跃`，`gap = 今天 - 最后活跃`；
     若 `gap > warn_idle_days` → **超期未学预警**（带教学周上下文）。
  2. 本周（按教学周）累计 `时长` < `周建议学时 × warn_deficit_ratio` → **需补学时预警**。
  3. 同一预警 24h 内只提示一次（用 `last_warn_time` 去重，可放 summaries 备注/独立字段）。
- 话术分级：首次轻提醒；超阈值 2 倍升级提醒并给出出口。不阻塞伴学。

设计要点
--------
- 纯标准库；输出纯文本标记，避免 GBK 控制台 emoji 崩溃。
- 全部为纯函数，可被 `_test_course_warn.py` 直接 import 做绿红双证。
- 未录校历时 `teach_week` 回退 ISO 周并标注「未对齐校历」，不阻断。

用法
----
    python3 course_warn.py check --summaries <summaries.json> --student <学号> \
        --calendar <cal.json> --term-config <tc.json> --today <YYYY-MM-DD> \
        [--last-warn <ISO时间>]
输出 JSON：{"suppressed": bool, "teach_week": str, "warnings": [ {type,level,message}, ... ]}
"""

import argparse
import importlib.util
import json
import os
import sys
from datetime import datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))

# —— 内置默认阈值：term_config 未配置时**自动兜底**，保证预警不因缺配置而静默失效——
# 与 teacher_setup.md §2.0.6 登记的默认值保持一致（单一真源，改这里要同步那份文档）。
DEFAULT_WARN_IDLE_DAYS = 7
DEFAULT_WARN_DEFICIT_RATIO = 0.7
DEFAULT_REQUIRED_HOURS_PER_WEEK = 3.0


def _load_calendar_mod():
    spec = importlib.util.spec_from_file_location(
        "course_calendar", os.path.join(HERE, "course_calendar.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


try:
    _cal = _load_calendar_mod()
except Exception:  # pragma: no cover
    _cal = None


def _norm(s):
    return (s or "").strip()


def _norm_rows(x):
    """ 修复：把数据通道取回的原始结构展平成扁平行。

    支持三种入参：
      - 扁平行数组：[{"学号":"0000", ...}, ...] —— 原样返回；
      - data plane 原始结构：{"records":[{"field_values":[{"field":"学号",
        "text_value":{"items":[{"text":"0000"}]}}]}]} —— 展平为扁平行数组；
      - 其他形态：抛 ValueError（**不静默返回空**）。

    为什么要显式抛错：过去只认扁平行，喂原结构时会迭代到字典的键字符串，
    匹配不到任何字段 → 结果为空且**不报错**，预警 / 到期复习 / 目标进度三条链路
    全部假阴性（看起来像"没有到期项"，实则是"没识别到任何行"）。
    """
    if isinstance(x, list):
        return x
    if isinstance(x, dict) and isinstance(x.get("records"), list):
        out = []
        for rec in x["records"]:
            if not isinstance(rec, dict):
                continue
            row = {}
            for fv in (rec.get("field_values") or []):
                if not isinstance(fv, dict):
                    continue
                field = fv.get("field")
                if not field:
                    continue
                items = (fv.get("text_value") or {}).get("items") or []
                row[field] = "".join(i.get("text", "") for i in items if isinstance(i, dict))
            if row:
                out.append(row)
        return out
    raise ValueError("未识别的入参形态：期望扁平行数组或 {records:[...]}，请确认已展平")


def _check_columns(rows, label):
    """展平后仍无中文列 → 显式提示（不要把「没数据」和「没到期项」混为一谈）。"""
    if not rows:
        return
    keys = set()
    for r in rows[:5]:
        if isinstance(r, dict):
            keys |= set(r.keys())
    if not keys & {"学号", "时间", "知识点", "结果", "时长"}:
        sys.stderr.write("[WARN] %s 里没有识别到中文列名（学号/时间/知识点/结果/时长），"
                        "入参可能未展平——结果为空不代表没有到期项\n" % label)


def _row_get(row, *candidates):
    for c in candidates:
        if c in row and row[c] not in (None, ""):
            return row[c]
    return None


def _parse_dt(s):
    s = _norm(s)
    if not s:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d", "%Y/%m/%d %H:%M:%S", "%Y/%m/%d"):
        try:
            return datetime.strptime(s[:19], fmt)
        except Exception:
            continue
    return None


def _student_rows(summaries, student_id):
    sid = _norm(student_id)
    out = []
    for r in (summaries or []):
        if _norm(_row_get(r, "学号", "student_id")) == sid:
            out.append(r)
    return out


def last_active_date(summaries, student_id):
    """该生最后活跃日期（date）；无记录返回 None。"""
    best = None
    for r in _student_rows(summaries, student_id):
        dt = _parse_dt(_row_get(r, "时间", "session_time", "date"))
        if dt and (best is None or dt > best):
            best = dt
    return best.date() if best else None


def idle_gap_days(summaries, student_id, today):
    """超期未学天数；无记录返回 None（由调用方按缺勤口径处理）。"""
    la = last_active_date(summaries, student_id)
    if la is None:
        return None
    return (today - la).days


def week_duration_min(summaries, student_id, calendar, today):
    """该生「当前教学周」累计时长（分钟）+ 教学周标签。"""
    tw_label = "未知周"
    if _cal is not None:
        try:
            tw_label, _ = _cal.teach_week_label(calendar, today.isoformat())
        except Exception as e:
            _emit("!", "校历解析失败，回退 ISO 周：%s" % e)
    if tw_label == "未知周":
        # 无 _cal 兜底：手写 ISO 周
        try:
            y, w, _ = today.isocalendar()
            tw_label = "%d-W%02d" % (y, w)
        except Exception:
            pass
    total = 0
    for r in _student_rows(summaries, student_id):
        rdt = _parse_dt(_row_get(r, "时间", "session_time", "date"))
        if rdt is None:
            continue
        # 仅累计「当前教学周」内的会话（用教学周标签对齐）
        rlabel = tw_label
        if _cal is not None:
            try:
                rlabel, _ = _cal.teach_week_label(calendar, rdt.date().isoformat())
            except Exception as e:
                _emit("!", "校历解析失败，回退 ISO 周：%s" % e)
        if rlabel != tw_label:
            continue
        try:
            total += float(_row_get(r, "时长", "duration_min") or 0)
        except (TypeError, ValueError):
            continue
    return total, tw_label


def should_suppress(last_warn_time, now):
    """24h 去重：距上次提醒不足 24h 则抑制（返回 True）。"""
    if not last_warn_time:
        return False
    dt = _parse_dt(last_warn_time)
    if dt is None:
        return False
    return (now - dt) < timedelta(hours=24)


def evaluate_warning(summaries, student_id, calendar, term_config, today,
                     last_warn_time=None):
    """返回 {suppressed, teach_week, warnings:[...], config_status}。

    warnings 每项：{type, level, message}。type ∈ {idle, deficit}。
    config_status：本次评估用的阈值来源与是否用了默认值——**供调用方回报，
    避免「没提醒」被误当成「学生很自觉」**。
    """
    tc = term_config or {}
    # —— 自动兜底：term_config 缺失/缺键时用内置默认，**不因未配置而静默失效**——
    warn_enabled = tc.get("warn_enabled", True)
    idle_days = tc.get("warn_idle_days", DEFAULT_WARN_IDLE_DAYS)
    ratio = tc.get("warn_deficit_ratio", DEFAULT_WARN_DEFICIT_RATIO)
    req_hours = tc.get("required_hours_per_week")
    if req_hours in (None, ""):
        req_hours = DEFAULT_REQUIRED_HOURS_PER_WEEK

    config_status = {
        "source": "term_config" if tc else "builtin_default",
        "used_defaults": sorted([
            k for k, v in (
                ("warn_idle_days", DEFAULT_WARN_IDLE_DAYS),
                ("warn_deficit_ratio", DEFAULT_WARN_DEFICIT_RATIO),
                ("required_hours_per_week", DEFAULT_REQUIRED_HOURS_PER_WEEK),
            ) if tc.get(k) in (None, "")
        ]),
        "warn_enabled": bool(warn_enabled),
        "has_calendar": bool(calendar),
        "thresholds": {
            "warn_idle_days": idle_days,
            "warn_deficit_ratio": ratio,
            "required_hours_per_week": req_hours,
        },
    }

    tw_label = "未知周"
    if _cal is not None:
        try:
            tw_label, aligned = _cal.teach_week_label(calendar, today.isoformat())
            if not aligned:
                tw_label = tw_label + "(未对齐校历)"
        except Exception as e:
            _emit("!", "校历解析失败，回退 ISO 周：%s" % e)

    result = {"suppressed": False, "teach_week": tw_label, "warnings": [],
              "config_status": config_status}
    if not warn_enabled:
        config_status["source"] = "disabled_by_teacher"
        return result

    now = datetime.combine(today, datetime.min.time()) if not isinstance(today, datetime) else today
    if should_suppress(last_warn_time, now):
        result["suppressed"] = True
        return result

    # 1) 超期未学
    gap = idle_gap_days(summaries, student_id, today)
    if gap is not None and gap > int(idle_days):
        level = "升级提醒" if gap > 2 * int(idle_days) else "轻提醒"
        result["warnings"].append({
            "type": "idle",
            "level": level,
            "message": "第 %s 你已 %d 天未学习，建议安排一次伴学（或约个固定学习时间）。"
                       % (tw_label, gap),
        })

    # 2) 需补学时（req_hours 已兜底默认值，故**未配置也能判定**）
    try:
        req_min = float(req_hours) * 60.0
    except (TypeError, ValueError):
        req_min = DEFAULT_REQUIRED_HOURS_PER_WEEK * 60.0
    if req_min > 0:
        dur, _ = week_duration_min(summaries, student_id, calendar, today)
        threshold = req_min * float(ratio)
        if dur < threshold:
            level = "升级提醒" if dur < threshold * 0.5 else "轻提醒"
            result["warnings"].append({
                "type": "deficit",
                "level": level,
                "message": "第 %s 本周累计学时 %.0f 分钟，低于建议的 %.0f 分钟（%.0f%%），建议补学。"
                           % (tw_label, dur, threshold, float(ratio) * 100),
            })

    return result


def _emit(prefix, msg):
    sys.stderr.write("[%s] course_warn: %s\n" % (prefix, msg))


# ---------------------------------------------------------------------------
# -B 间隔重复提醒（艾宾浩斯：部分/卡住知识点 1/3/7 天后提议复习）
# ---------------------------------------------------------------------------
REVIEW_RESULTS = ("部分收敛", "卡住")


def due_reviews(summaries, student_id, today, intervals=(1, 3, 7)):
    """该生到期复习清单：部分/卡住的知识点，距最后一次练习 1/3/7 天。

    每个知识点只取最近一次记录；返回 [{kp, result, last_date, gap_days}]（按 kp 排序）。
    """
    latest = {}
    for r in _student_rows(summaries, student_id):
        kp = _norm(_row_get(r, "知识点", "kp"))
        res = _norm(_row_get(r, "结果", "result"))
        dt = _parse_dt(_row_get(r, "时间", "session_time", "date"))
        if not kp or dt is None:
            continue
        if kp not in latest or dt > latest[kp][1]:
            latest[kp] = (res, dt)
    out = []
    for kp, (res, dt) in latest.items():
        if res not in REVIEW_RESULTS:
            continue
        gap = (today - dt.date()).days
        if gap in intervals:
            out.append({"kp": kp, "result": res, "last_date": dt.date().isoformat(),
                        "gap_days": gap})
    out.sort(key=lambda x: x["kp"])
    return out


# ---------------------------------------------------------------------------
# -C 学习目标与进度追踪
# ---------------------------------------------------------------------------
def goal_progress(summaries, usage_rows, student_id, today,
                  target_hours=None, target_kps=None, calendar=None):
    """本周目标进度：学时（summaries 时长合计）+ 知识点数（usage 去重）对比学生自定目标。

    周口径与预警一致（当前教学周，无校历回退 ISO 周）。
    返回 {"week": 标签, "hours": n, "hours_ratio": f|None,
          "kps": n, "kps_ratio": f|None, "met": bool}。
    """
    tw_label = "未知周"
    if _cal is not None:
        try:
            tw_label, aligned = _cal.teach_week_label(calendar, today.isoformat())
            if not aligned:
                tw_label = tw_label + "(未对齐校历)"
        except Exception as e:
            _emit("!", "校历解析失败，回退 ISO 周：%s" % e)

    def _in_week(rdt):
        if _cal is not None:
            try:
                label, _ = _cal.teach_week_label(calendar, rdt.date().isoformat())
                return label == tw_label.split("(")[0]
            except Exception as e:
                _emit("!", "校历解析失败，回退 ISO 周：%s" % e)
        try:
            y, w, _ = rdt.isocalendar()
            return "%d-W%02d" % (y, w) == tw_label.split("(")[0]
        except Exception:
            return False

    hours = 0.0
    for r in _student_rows(summaries, student_id):
        rdt = _parse_dt(_row_get(r, "时间", "session_time", "date"))
        if rdt is None or not _in_week(rdt):
            continue
        try:
            hours += float(_row_get(r, "时长", "duration_min") or 0)
        except (TypeError, ValueError):
            continue

    kps = set()
    for r in (usage_rows or []):
        if _norm(_row_get(r, "学号", "student_id")) != _norm(student_id):
            continue
        rdt = _parse_dt(_row_get(r, "时间", "date", "session_time"))
        if rdt is None or not _in_week(rdt):
            continue
        kp = _norm(_row_get(r, "知识点", "kp"))
        if kp:
            kps.add(kp)

    hours_ratio = (hours / 60.0 / float(target_hours)) if target_hours else None
    kps_ratio = (len(kps) / float(target_kps)) if target_kps else None
    met = True
    if target_hours:
        met = met and hours >= float(target_hours) * 60.0
    if target_kps:
        met = met and len(kps) >= int(target_kps)
    return {"week": tw_label, "hours": hours, "hours_ratio": hours_ratio,
            "kps": len(kps), "kps_ratio": kps_ratio, "met": met}


def _coerce_val(v):
    """ 修复：云端 term_config 的「值」列类型化（'7'→7.0 / 'true'→True / 其余原样）。"""
    if isinstance(v, str):
        s = v.strip()
        low = s.lower()
        if low in ("true", "是", "yes", "开"):
            return True
        if low in ("false", "否", "no", "关"):
            return False
        try:
            return float(s)
        except ValueError:
            return s
    return v


def _norm_term_config(x):
    """ 修复：云端读出的 [{参数,值}] 行列表 → {参数:值} dict；dict 原样透传。"""
    if isinstance(x, dict):
        return x
    if isinstance(x, list):
        out = {}
        for r in x:
            if not isinstance(r, dict):
                continue
            k = str(r.get("参数") or r.get("key") or r.get("name") or "").strip()
            if not k:
                continue
            v = r.get("值", r.get("value"))
            out[k] = _coerce_val(v)
        return out
    return {}


def _norm_calendar(x, tc=None):
    """ 修复：云端读出的 [{week_no,week_start,...}] 行列表 → {term, weeks:[...]}；dict 原样透传。"""
    if isinstance(x, dict):
        return x
    if isinstance(x, list):
        rows = [r for r in x if isinstance(r, dict) and r.get("week_no") is not None]
        rows.sort(key=lambda r: int(r.get("week_no") or 0))
        cal = {"weeks": rows}
        tcd = _norm_term_config(tc) if tc else {}
        cal["term"] = tcd.get("term") or tcd.get("学期") or "term"
        for k in ("term_start", "total_weeks"):
            if tcd.get(k) is not None:
                cal[k] = tcd[k]
        return cal
    return x


def _cmd_check(args):
    summaries = _norm_rows(json.load(open(args.summaries, "r", encoding="utf-8-sig")))
    _check_columns(summaries, "summaries")
    cal_raw = json.load(open(args.calendar, "r", encoding="utf-8-sig")) if args.calendar else None
    tc = _norm_term_config(json.load(open(args.term_config, "r", encoding="utf-8-sig"))
                           if args.term_config else {})
    cal = _norm_calendar(cal_raw, tc) if cal_raw is not None else None
    today = _parse_dt(args.today)
    if today is None:
        _emit("FAIL", "today 解析失败: %s" % args.today)
        return 2
    today = today.date()
    res = evaluate_warning(summaries, args.student, cal, tc, today, args.last_warn)
    print(json.dumps(res, ensure_ascii=False))
    return 0


def _cmd_review(args):
    #  修复：数据源首选 usage（「结果」列在 usage 表；summaries 无结果列会恒空转）。
    # --summaries 保留向后兼容，但仅当未提供 --usage 时使用。
    if getattr(args, "usage", ""):
        rows = _norm_rows(json.load(open(args.usage, "r", encoding="utf-8-sig")))
    elif getattr(args, "summaries", ""):
        rows = _norm_rows(json.load(open(args.summaries, "r", encoding="utf-8-sig")))
    else:
        _emit("FAIL", "需要 --usage <usage.json>（首选）或 --summaries <summaries.json>")
        return 2
    _check_columns(rows, "学情")
    today = _parse_dt(args.today)
    if today is None:
        _emit("FAIL", "today 解析失败: %s" % args.today)
        return 2
    today = today.date()
    intervals = tuple(int(x) for x in str(args.intervals).split(",") if x.strip())
    res = due_reviews(rows, args.student, today, intervals)
    print(json.dumps({"due": res}, ensure_ascii=False))
    return 0


def _cmd_goal(args):
    summaries = _norm_rows(json.load(open(args.summaries, "r", encoding="utf-8-sig"))) if args.summaries else []
    usage = _norm_rows(json.load(open(args.usage, "r", encoding="utf-8-sig"))) if args.usage else []
    _check_columns(usage, "学情")
    cal_raw = json.load(open(args.calendar, "r", encoding="utf-8-sig")) if args.calendar else None
    cal = _norm_calendar(cal_raw) if cal_raw is not None else None
    today = _parse_dt(args.today)
    if today is None:
        _emit("FAIL", "today 解析失败: %s" % args.today)
        return 2
    today = today.date()
    res = goal_progress(summaries, usage, args.student, today,
                        args.target_hours, args.target_kps, cal)
    print(json.dumps(res, ensure_ascii=False))
    return 0


def main(argv):
    parser = argparse.ArgumentParser(description="课程伴学学生端学习预警（）与间隔复习/目标进度（）")
    sub = parser.add_subparsers(dest="cmd")
    pc = sub.add_parser("check", help="评估某生预警")
    pc.add_argument("--summaries", required=True, help="summaries JSON")
    pc.add_argument("--student", required=True, help="学号")
    pc.add_argument("--calendar", help="校历 JSON")
    pc.add_argument("--term-config", dest="term_config", help="学期参数 JSON")
    pc.add_argument("--today", required=True, help="今天 YYYY-MM-DD")
    pc.add_argument("--last-warn", dest="last_warn", help="上次提醒时间（ISO），用于 24h 去重")
    pc.set_defaults(func=_cmd_check)

    pr = sub.add_parser("review", help="到期复习清单（部分/卡住知识点 1/3/7 天）")
    pr.add_argument("--usage", default="", help="usage JSON（注：首选数据源，「结果」列在此表）")
    pr.add_argument("--summaries", default="", help="summaries JSON（向后兼容；无 --usage 时使用）")
    pr.add_argument("--student", required=True, help="学号")
    pr.add_argument("--today", required=True, help="今天 YYYY-MM-DD")
    pr.add_argument("--intervals", default="1,3,7", help="到期天数，逗号分隔（默认 1,3,7）")
    pr.set_defaults(func=_cmd_review)

    pg = sub.add_parser("goal", help="本周目标进度（学时 + 知识点数）")
    pg.add_argument("--summaries", help="summaries JSON（算学时）")
    pg.add_argument("--usage", help="usage 表 JSON（算知识点数）")
    pg.add_argument("--student", required=True, help="学号")
    pg.add_argument("--today", required=True, help="今天 YYYY-MM-DD")
    pg.add_argument("--target-hours", dest="target_hours", type=float, help="本周目标学时（小时）")
    pg.add_argument("--target-kps", dest="target_kps", type=int, help="本周目标知识点数")
    pg.add_argument("--calendar", help="校历 JSON")
    pg.set_defaults(func=_cmd_goal)

    if not argv[1:]:
        parser.print_help(sys.stderr)
        return 2
    args = parser.parse_args(argv[1:])
    if not getattr(args, "func", None):
        parser.print_help(sys.stderr)
        return 2
    rc = args.func(args)
    # 自动埋点（）：调用即记录，失败不影响功能
    # 学生包布局：course_warn.py 在包根、course_usage_log.py 在 scripts/——两个位置都试
    try:
        import os as _os
        here = _os.path.dirname(_os.path.abspath(__file__))
        for cand in (here, _os.path.join(here, "scripts")):
            if cand not in sys.path:
                sys.path.insert(0, cand)
        import course_usage_log
        course_usage_log.auto_record("学习预警·%s" % args.cmd, "",
                                     "student=%s" % getattr(args, "student", ""))
    except Exception:
        pass
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv))
