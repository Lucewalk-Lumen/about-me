#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
logbook.py — N4 功劳档案（Term Achievement Record）写入与读取。

设计目的
--------
用户原话：「完成的任务能否有总结和记录」「查看自己一学期的功劳，给出总结」。
没有这份档案，下游 N5-c 学期总结（term_summary.py）就没有数据可聚合。
本脚本是它的**唯一上游数据源**。

存储契约（不得偏离）
--------------------
- 路径：默认 `%USERPROFILE%/.schedule-planner/logbook.jsonl`
- 格式：JSONL，append-only，一行一条，UTF-8 无 BOM
- **隐私门禁（P0 红线）**：档案只落用户目录，**严禁写进专家包目录**。
  检测到指向包内路径时用 `assert` 拦住并报错，绝不静默改落别处。

行 schema（每行一个 JSON 对象）
------------------------------
必需 9 字段：
    timestamp  ISO8601 本地时间，写入时刻
    date       YYYY-MM-DD，任务发生日期
    task_id    任务编号，如 T1.1
    title      任务标题
    status     done | partial | skipped
    minutes    int >= 0，实际投入分钟
    week_no    int，按 term_start 反推（**不硬编码**）
    tags       字符串数组
    note       字符串或 null

可选扩展字段（给了就原样落盘，不给不写，保证 JSONL 干净）：
    id / plan_id / priority / attribution / fact_refs /
    planned_minutes / actual_minutes / evidence

下游桥接（重要）：term_summary.py 直接读本 JSONL，按 planned_minutes /
actual_minutes 聚合工时口径，且 planned 为 0 时工时完成率恒为 0.0%。
故未显式提供这两个字段时，本模块用 minutes 兜底写入二者（显式传入则以其为准），
避免下游「工时 0 / 0 分钟」这类因上游缺字段导致的静默归零。

读时兼容：`term_week` 视为 `week_no` 的别名（设计稿字段命名），
`planned_minutes`/`actual_minutes` 缺失时回落到 `minutes`。

用法
----
    logbook.py --add --date 2026-10-21 --task-id T1.1 --title "完成实验报告" \
               --status done --minutes 90 --tags 实验 --note "..."
    logbook.py --add --json '{"date":"2026-10-21","task_id":"T1.1",...}'
    logbook.py --list [--week 7] [--from YYYY-MM-DD --to YYYY-MM-DD]
    logbook.py --stats
    logbook.py --export [--out <路径>] [--fmt json|csv|md]
    logbook.py --purge --yes
    logbook.py --selftest

也接受设计稿的子命令写法：`add` / `read` / `stats` / `purge` / `export`。
其中 `read` 等价于 `--list`，`read --week 7` / `read --range a b` 均可。

Python API（供 term_summary.py 导入）
------------------------------------
    from logbook import Logbook, load_entries
    lb = Logbook()                     # 默认用户目录
    lb.add(date=..., task_id=..., title=..., status=..., minutes=..., tags=[], note=None)
    entries = load_entries()           # -> list[dict]
    lb.by_week(7)                      # -> 第 7 周的条目
    lb.stats()                         # -> dict

仅依赖 Python 标准库。输出禁用 emoji（Windows GBK 控制台会抛
UnicodeEncodeError），一律用 [OK] / [WARN] / [FAIL]。
"""

import argparse
import csv
import io
import json
import os
import sys
import tempfile
from datetime import date, datetime, timedelta

# --------------------------------------------------------------------------
# 常量与默认值
# --------------------------------------------------------------------------

#: 第 1 周周一。可被 --term-start 覆盖，**不在代码里硬编码周次**。
DEFAULT_TERM_START = "2026-09-07"

ARCHIVE_NAME = "logbook.jsonl"
DATA_DIR_NAME = ".schedule-planner"

STATUS_DONE = "done"
STATUS_PARTIAL = "partial"
STATUS_SKIPPED = "skipped"
VALID_STATUS = (STATUS_DONE, STATUS_PARTIAL, STATUS_SKIPPED)

#: 设计稿 D-N4 六值归因（含「无偏差」）
VALID_ATTRIBUTION = (
    "none", "overload", "estimate", "interrupted", "motivation", "fact_error",
)

REQUIRED_FIELDS = (
    "date", "task_id", "title", "status", "minutes",
)
OPTIONAL_FIELDS = (
    "id", "plan_id", "priority", "attribution", "fact_refs",
    "planned_minutes", "actual_minutes", "evidence",
)

# 包根：.../schedule-planner/skills/schedule-planning/scripts/logbook.py
# dirname x4 -> skills 的上一级，即专家包根。
_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
_SKILL_DIR = os.path.dirname(_SCRIPTS_DIR)
_SKILLS_DIR = os.path.dirname(_SKILL_DIR)
PACKAGE_ROOT = os.path.dirname(_SKILLS_DIR)

#: 隐私门禁额外拦截的敏感路径片段（专家包/插件市场所在区域）
_FORBIDDEN_SEGMENTS = (".workbuddy", ".claude", ".codebuddy", "marketplaces")


class PrivacyViolation(Exception):
    """隐私门禁被触发：试图把用户数据写进专家包目录。"""


class ValidationError(Exception):
    """记录 schema 校验失败。"""


# --------------------------------------------------------------------------
# 控制台输出（防 GBK UnicodeEncodeError，禁 emoji）
# --------------------------------------------------------------------------

def _init_stdio():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def out(msg=""):
    print(msg)


def ok(msg):
    print("[OK] " + msg)


def warn(msg):
    print("[WARN] " + msg)


def fail(msg):
    print("[FAIL] " + msg, file=sys.stderr)


# --------------------------------------------------------------------------
# 隐私门禁
# --------------------------------------------------------------------------

def _norm(path):
    return os.path.normcase(os.path.normpath(os.path.abspath(path)))


def is_inside_package(path):
    """判定 path 是否落在专家包目录内（或其敏感宿主目录内）。"""
    p = _norm(path)
    pkg = _norm(PACKAGE_ROOT)
    try:
        if os.path.commonpath([p, pkg]) == pkg:
            return True
    except ValueError:
        # 不同盘符，commonpath 抛异常，按不冲突处理
        pass
    lowered = p.replace("\\", "/").lower()
    for seg in _FORBIDDEN_SEGMENTS:
        if "/" + seg.lower() + "/" in lowered or lowered.endswith("/" + seg.lower()):
            return True
    return False


def guard_user_writable(path, what="目标路径"):
    """隐私门禁：用户数据一律不得写入专家包目录。

    主线用 assert 拦（P0 红线要求）；再补一道显式抛错兜底，
    防止 `python -O` 关掉 assert 后门禁失效被静默绕过。
    """
    reason = None
    if is_inside_package(path):
        reason = (
            "隐私门禁拒绝：%s 位于专家包目录内（%s）。"
            "功劳档案属用户数据，只能落在用户目录，严禁写入包内。"
            % (what, path)
        )
    assert reason is None, reason          # 主线拦截
    if reason is not None:                 # -O 兜底，双重保险
        raise PrivacyViolation(reason)
    return True


def default_data_dir():
    """默认用户目录 %USERPROFILE%\\.schedule-planner（Unix 下为 ~）。"""
    home = os.path.expanduser("~")
    if not home or home == "~":
        home = os.environ.get("USERPROFILE") or os.environ.get("HOME") or os.getcwd()
    return os.path.join(home, DATA_DIR_NAME)


# --------------------------------------------------------------------------
# 日期 / 周次
# --------------------------------------------------------------------------

def parse_date(value):
    """解析 YYYY-MM-DD -> datetime.date；非法抛 ValidationError。"""
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("date 缺失或不是字符串：%r" % (value,))
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except ValueError:
        raise ValidationError("date 必须是 YYYY-MM-DD 格式：%r" % (value,))


def parse_term_start(value):
    """解析学期起始日，并断言必须是周一。"""
    d = parse_date(value)
    if d.weekday() != 0:
        raise ValidationError(
            "term_start 必须是周一，%s 是周%s" % (d.isoformat(), "一二三四五六日"[d.weekday()])
        )
    return d


def week_no_of(day, term_start):
    """按 term_start（第 1 周周一）反推周次；早于学期则 <= 0。"""
    d = parse_date(day)
    ts = parse_date(term_start)
    return (d - ts).days // 7 + 1


def week_range(week_no, term_start):
    """第 week_no 周的 [周一, 周日]。"""
    ts = parse_date(term_start)
    monday = ts + timedelta(days=(int(week_no) - 1) * 7)
    return monday, monday + timedelta(days=6)


def now_timestamp():
    """本地时间 ISO8601，带分钟精度（不带时区偏移，避免跨平台差异）。"""
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


# --------------------------------------------------------------------------
# 记录校验与归一化
# --------------------------------------------------------------------------

def _coerce_tags(value):
    if value is None:
        return []
    if isinstance(value, str):
        parts = [p.strip() for p in value.replace("，", ",").split(",")]
        return [p for p in parts if p]
    if isinstance(value, (list, tuple)):
        return [str(t).strip() for t in value if str(t).strip()]
    raise ValidationError("tags 必须是字符串数组或逗号分隔字符串：%r" % (value,))


def _coerce_minutes(value, field="minutes"):
    if value is None:
        raise ValidationError("%s 缺失" % field)
    try:
        m = int(value)
    except (TypeError, ValueError):
        raise ValidationError("%s 必须是整数：%r" % (field, value))
    if m < 0:
        raise ValidationError("%s 不能为负数：%d" % (field, m))
    return m


def normalize_record(raw, term_start):
    """把外部输入（CLI 参数或 --json）归一化成完整记录；缺字段抛 ValidationError。"""
    if not isinstance(raw, dict):
        raise ValidationError("记录必须是 JSON 对象，收到 %s" % type(raw).__name__)

    rec = dict(raw)

    # 读时兼容别名
    if "week_no" not in rec and "term_week" in rec:
        rec["week_no"] = rec["term_week"]
    if "minutes" not in rec:
        for alt in ("actual_minutes", "planned_minutes"):
            if alt in rec and rec[alt] is not None:
                rec["minutes"] = rec[alt]
                break

    missing = [f for f in REQUIRED_FIELDS if rec.get(f) in (None, "")]
    if missing:
        raise ValidationError("缺少必需字段：%s" % "、".join(missing))

    d = parse_date(rec["date"])
    status = str(rec["status"]).strip().lower()
    if status not in VALID_STATUS:
        raise ValidationError(
            "status 取值必须是 %s 之一，收到 %r" % (" / ".join(VALID_STATUS), rec["status"])
        )

    minutes = _coerce_minutes(rec["minutes"])
    tags = _coerce_tags(rec.get("tags"))
    note = rec.get("note")
    if note is not None:
        note = str(note)

    entry = {
        "timestamp": rec.get("timestamp") or now_timestamp(),
        "date": d.isoformat(),
        "task_id": str(rec["task_id"]).strip(),
        "title": str(rec["title"]).strip(),
        "status": status,
        "minutes": minutes,
        "week_no": week_no_of(d, term_start),
        "tags": tags,
        "note": note,
    }

    # 可选扩展字段：给了才落盘
    for f in OPTIONAL_FIELDS:
        if rec.get(f) is not None:
            entry[f] = rec[f]

    # 下游桥接：term_summary.py 直接读 JSONL，按 planned_minutes/actual_minutes
    # 聚合工时口径，且 planned==0 时 工时完成率 恒为 0.0%（会显示 "0 / 0 分钟"）。
    # 本模块的规范时间字段是 minutes，故未显式提供计划/实际工时时用 minutes 兜底，
    # 避免下游指标因上游缺字段而静默归零。显式传入则以其为准，不被覆盖。
    if entry.get("actual_minutes") is None:
        entry["actual_minutes"] = minutes
    if entry.get("planned_minutes") is None:
        entry["planned_minutes"] = entry["actual_minutes"]

    attribution = entry.get("attribution")
    if attribution is not None and str(attribution) not in VALID_ATTRIBUTION:
        raise ValidationError(
            "attribution 取值必须是 %s 之一，收到 %r"
            % (" / ".join(VALID_ATTRIBUTION), attribution)
        )

    return entry


# --------------------------------------------------------------------------
# 统计口径（全包唯一权威定义，logbook.py 与下游 term_summary.py 通用）
# --------------------------------------------------------------------------
#   完成率(按条数) = done 条数 / 总条数
#   完成率(按工时) = Σ planned_minutes(done) / Σ planned_minutes(all)      <- 计划加权
#   工时投入率     = Σ actual_minutes(all)  / Σ planned_minutes(all)      <- 估时偏差信号
#
# 为什么「按工时」用计划加权而非实际耗时：
#   「完成」是相对于「承诺」而言的，不是相对于「花了多少时间」而言的。
#   以实际耗时为分母时，一件计划 90 分钟却磨了 300 分钟的任务会把完成率抬高，
#   极端情况下「一条都没做完」也能读出非零完成率。计划加权口径具备两条不变量：
#     全 done  -> 恒等于 100%
#     零 done  -> 恒等于 0%
#   这两条不变量是审计可一眼验真伪的性质。
#
# 为什么另立「工时投入率」：
#   它是估时偏差信号，不是完成率。
#     > 100% -> 普遍低估（实际比计划花得多）
#     < 100% -> 普遍高估（实际比计划花得少）
#   把「实际投入」从完成率里剥离出来单独成行，信息不丢，也不再冒充完成率。
#
# 零分母纪律：
#   Σplanned(all) == 0 时两个工时口径均返回 None（显示「—（无计划工时）」），
#   不得显示 0.0%。0/0 是「无计划工时」（维度缺失），
#   与「Σplanned>0 且 done=0」的真零（0.0%）必须可区分。


def _num(entry, *keys):
    """取第一个存在且可转 int 的字段；都缺失时回落到 minutes（对齐上游兜底与下游 rec_min）。"""
    for k in keys:
        v = entry.get(k)
        if v is not None:
            try:
                return int(v)
            except (TypeError, ValueError):
                return 0
    return int(entry.get("minutes") or 0)


# --------------------------------------------------------------------------
# 核心类
# --------------------------------------------------------------------------

class Logbook(object):
    """功劳档案读写器。默认落 %USERPROFILE%/.schedule-planner/logbook.jsonl。"""

    def __init__(self, data_dir=None, term_start=DEFAULT_TERM_START):
        self.data_dir = data_dir or default_data_dir()
        # 隐私门禁：构造即校验，不等到写盘才拦
        guard_user_writable(self.data_dir, "档案目录")
        self.term_start = term_start
        self.path = os.path.join(self.data_dir, ARCHIVE_NAME)

    # -- 落盘 -------------------------------------------------------------

    def _ensure_dir(self):
        guard_user_writable(self.data_dir, "档案目录")
        if not os.path.isdir(self.data_dir):
            os.makedirs(self.data_dir, exist_ok=True)

    def add(self, date=None, task_id=None, title=None, status=None, minutes=None,
            tags=None, note=None, record=None, **extra):
        """append 一条记录，返回落盘的 dict。校验失败抛 ValidationError。"""
        raw = {"date": date, "task_id": task_id, "title": title,
               "status": status, "minutes": minutes, "tags": tags, "note": note}
        raw = {k: v for k, v in raw.items() if v is not None}
        if record:
            raw.update(record)
        raw.update(extra)

        entry = normalize_record(raw, self.term_start)
        self._ensure_dir()
        guard_user_writable(self.path, "档案文件")
        with io.open(self.path, "a", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
            fh.flush()
        return entry

    def purge(self, confirm=False):
        """清空档案。必须 confirm=True（CLI 侧对应 --yes）才执行。"""
        if not confirm:
            raise ValidationError(
                "purge 需要二次确认：请加 --yes（CLI）或 confirm=True（API），已取消，未做任何改动。"
            )
        guard_user_writable(self.path, "档案文件")
        self._ensure_dir()
        with io.open(self.path, "w", encoding="utf-8", newline="\n"):
            pass
        return 0

    # -- 读取 -------------------------------------------------------------

    def load(self):
        """读全部条目；文件不存在返回 []；坏行跳过并计数。"""
        return load_entries(self.path, term_start=self.term_start)

    def list_entries(self, week=None, date_from=None, date_to=None):
        entries = self.load()
        return self._filter(entries, week, date_from, date_to)

    def _filter(self, entries, week, date_from, date_to):
        result = entries
        if week is not None:
            w = int(week)
            result = [e for e in result if self._week_of(e) == w]
        if date_from:
            a = parse_date(date_from).isoformat()
            result = [e for e in result if e.get("date", "") >= a]
        if date_to:
            b = parse_date(date_to).isoformat()
            result = [e for e in result if e.get("date", "") <= b]
        return sorted(result, key=lambda e: (e.get("date", ""), e.get("task_id", "")))

    def _week_of(self, entry):
        if entry.get("week_no") is not None:
            return int(entry["week_no"])
        if entry.get("term_week") is not None:
            return int(entry["term_week"])
        if entry.get("date"):
            return week_no_of(entry["date"], self.term_start)
        return None

    def by_week(self, week):
        """返回第 week 周的条目（按日期排序）。"""
        return self.list_entries(week=week)

    def by_term(self):
        return self.load()

    def by_range(self, date_from, date_to):
        return self.list_entries(date_from=date_from, date_to=date_to)

    # -- 统计 -------------------------------------------------------------

    def stats(self):
        entries = self.load()
        total = len(entries)
        by_status = {s: 0 for s in VALID_STATUS}
        minutes_total = 0     # Σminutes：实际投入总量（仅作展示，不作完成率分母）
        minutes_done = 0
        planned_total = 0     # Σplanned_minutes：完成率的分母
        planned_done = 0      # Σplanned_minutes(done)：完成率的分子
        actual_total = 0      # Σactual_minutes：工时投入率的分子
        for e in entries:
            st = e.get("status")
            if st in by_status:
                by_status[st] += 1
            m = int(e.get("minutes") or 0)
            minutes_total += m
            if st == STATUS_DONE:
                minutes_done += m
            pl = _num(e, "planned_minutes")
            ac = _num(e, "actual_minutes")
            planned_total += pl
            actual_total += ac
            if st == STATUS_DONE:
                planned_done += pl
            # 注：partial 权重为 0（无 progress 字段，不插值、不取 0.5）

        def rate(n, d):
            return round(100.0 * n / d, 1) if d else 0.0

        # 完成率(按工时)：计划加权。零分母返回 None（无计划工时），不得回 0.0
        minutes_rate = (round(100.0 * planned_done / planned_total, 1)
                        if planned_total else None)
        # 工时投入率：估时偏差信号，非完成率。零分母同样返回 None
        effort_ratio = (round(100.0 * actual_total / planned_total, 1)
                        if planned_total else None)

        # 归因六值分布 + P0 口径（对齐 logbook-spec.md §4.1「三口径 + 归因分布」）
        attribution = {}
        p0_total = 0
        p0_done = 0
        for e in entries:
            at = str(e.get("attribution") or "none").lower()
            attribution[at] = attribution.get(at, 0) + 1
            if str(e.get("priority") or "").upper() == "P0":
                p0_total += 1
                if e.get("status") == STATUS_DONE:
                    p0_done += 1

        dates = sorted({e["date"] for e in entries if e.get("date")})
        weeks = sorted({self._week_of(e) for e in entries if self._week_of(e) is not None})
        tags = {}
        for e in entries:
            for t in (e.get("tags") or []):
                tags[t] = tags.get(t, 0) + 1

        return {
            "count": total,
            "by_status": by_status,
            "completion_rate": rate(by_status[STATUS_DONE], total),
            "minutes_total": minutes_total,
            "minutes_done": minutes_done,
            "hours_total": round(minutes_total / 60.0, 2),
            "minutes_rate": minutes_rate,
            "effort_ratio": effort_ratio,
            "planned_total": planned_total,
            "actual_total": actual_total,
            "planned_done": planned_done,
            "streak_days": _streak(dates),
            "best_streak_days": _best_streak(dates),
            "active_days": len(dates),
            "first_date": dates[0] if dates else None,
            "last_date": dates[-1] if dates else None,
            "p0_total": p0_total,
            "p0_done": p0_done,
            # P0 完成率：零分母返回 None（无 P0 项），不得回 0.0；对齐 minutes_rate
            "p0_rate": (round(100.0 * p0_done / p0_total, 1)
                        if p0_total else None),
            "attribution": attribution,
            "weeks_covered": weeks,
            "tags": tags,
            "term_start": str(self.term_start),
        }

    # -- 导出 -------------------------------------------------------------

    def export(self, out_path=None, fmt="json"):
        entries = self.load()
        fmt = (fmt or "json").lower()
        if out_path is None:
            out_path = os.path.join(self.data_dir, "logbook-export." + fmt)
        guard_user_writable(out_path, "导出文件")
        parent = os.path.dirname(os.path.abspath(out_path))
        if parent and not os.path.isdir(parent):
            os.makedirs(parent, exist_ok=True)

        if fmt == "json":
            payload = {
                "schema": "schedule-planner.logbook/v1",
                "exported_at": now_timestamp(),
                "term_start": str(self.term_start),
                "count": len(entries),
                "entries": entries,
            }
            with io.open(out_path, "w", encoding="utf-8", newline="\n") as fh:
                json.dump(payload, fh, ensure_ascii=False, indent=2)
        elif fmt == "csv":
            cols = ["timestamp", "date", "week_no", "task_id", "title",
                    "status", "minutes", "tags", "note"]
            with io.open(out_path, "w", encoding="utf-8-sig", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
                w.writeheader()
                for e in entries:
                    row = dict(e)
                    row["tags"] = "|".join(e.get("tags") or [])
                    row["note"] = e.get("note") or ""
                    w.writerow(row)
        elif fmt == "md":
            lines = ["# 功劳档案导出", "",
                     "- 导出时间：%s" % now_timestamp(),
                     "- 学期起始：%s" % self.term_start,
                     "- 记录条数：%d" % len(entries), ""]
            if entries:
                lines += ["| 日期 | 周次 | 任务 | 标题 | 状态 | 分钟 | 标签 | 备注 |",
                          "|---|---|---|---|---|---|---|---|"]
                for e in entries:
                    lines.append("| %s | W%s | %s | %s | %s | %s | %s | %s |" % (
                        e.get("date", ""), self._week_of(e), e.get("task_id", ""),
                        e.get("title", ""), e.get("status", ""), e.get("minutes", 0),
                        "、".join(e.get("tags") or []), (e.get("note") or "").replace("|", "/")))
            with io.open(out_path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write("\n".join(lines) + "\n")
        else:
            raise ValidationError("不支持的导出格式：%s（可选 json / csv / md）" % fmt)
        return out_path


def _streak(dates):
    """自最近一条记录往前数，连续打卡天数（按天去重）。"""
    if not dates:
        return 0
    uniq = sorted(set(dates))
    streak = 1
    for i in range(len(uniq) - 1, 0, -1):
        prev = parse_date(uniq[i - 1])
        cur = parse_date(uniq[i])
        if (cur - prev).days == 1:
            streak += 1
        else:
            break
    return streak


def _best_streak(dates):
    """历史最长连续打卡天数。"""
    if not dates:
        return 0
    uniq = sorted(set(dates))
    best = cur = 1
    for i in range(1, len(uniq)):
        if (parse_date(uniq[i]) - parse_date(uniq[i - 1])).days == 1:
            cur += 1
            best = max(best, cur)
        else:
            cur = 1
    return best


def load_entries(path=None, term_start=DEFAULT_TERM_START):
    """读 JSONL -> list[dict]。文件不存在返回 []；坏行跳过。

    读 JSON 一律 utf-8-sig，兼容 Windows 记事本写入的 BOM。
    """
    if path is None:
        path = os.path.join(default_data_dir(), ARCHIVE_NAME)
    if not os.path.exists(path):
        return []
    entries = []
    bad = 0
    with io.open(path, "r", encoding="utf-8-sig", errors="replace") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except ValueError:
                bad += 1
                warn("跳过第 %d 行：不是合法 JSON" % lineno)
                continue
            if not isinstance(obj, dict):
                bad += 1
                warn("跳过第 %d 行：不是 JSON 对象" % lineno)
                continue
            if obj.get("week_no") is None and obj.get("date"):
                try:
                    obj["week_no"] = week_no_of(obj["date"], term_start)
                except ValidationError:
                    pass
            entries.append(obj)
    if bad:
        warn("共跳过 %d 行坏数据" % bad)
    return entries


# --------------------------------------------------------------------------
# 命令行
# --------------------------------------------------------------------------

def build_parser():
    p = argparse.ArgumentParser(
        prog="logbook.py",
        description="N4 功劳档案：append-only JSONL，落用户目录，包内禁止写入。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    g = p.add_mutually_exclusive_group()
    g.add_argument("--add", action="store_true", help="append 一条记录")
    g.add_argument("--list", action="store_true", help="列出记录（等价 read）")
    g.add_argument("--stats", action="store_true", help="完成率 / 总分钟 / 连续打卡")
    g.add_argument("--export", action="store_true", help="导出开放格式，保证可迁移")
    g.add_argument("--purge", action="store_true", help="清空档案（须 --yes）")
    g.add_argument("--selftest", action="store_true", help="内建自检")

    p.add_argument("--date", help="任务日期 YYYY-MM-DD")
    p.add_argument("--task-id", dest="task_id", help="任务编号，如 T1.1")
    p.add_argument("--title", help="任务标题")
    p.add_argument("--status", choices=list(VALID_STATUS), help="done / partial / skipped")
    p.add_argument("--minutes", type=int, help="实际投入分钟，>= 0")
    p.add_argument("--tags", help="标签，逗号分隔，如 实验,复习")
    p.add_argument("--note", default=None, help="备注")
    p.add_argument("--json", dest="json_record", help="整条记录的 JSON 字符串（add 用）")

    # 设计稿 D-N4 扩展字段：下游 term_summary.py 的 P0 完成率 / 归因分布依赖
    p.add_argument("--priority", help="优先级，如 P0/P1/P2")
    p.add_argument("--attribution", choices=list(VALID_ATTRIBUTION),
                   help="偏差归因（六值，含 none）")
    p.add_argument("--plan-id", dest="plan_id", help="所属计划编号，如 P-2026-W07")
    p.add_argument("--planned-minutes", dest="planned_minutes", type=int,
                   help="计划工时（不给则回落到 minutes）")
    p.add_argument("--actual-minutes", dest="actual_minutes", type=int,
                   help="实际工时（不给则回落到 minutes）")
    p.add_argument("--fact-refs", dest="fact_refs", help="关联台账编号，逗号分隔，如 F-01,H-2026-03")

    p.add_argument("--week", type=int, help="按周次过滤，如 7")
    p.add_argument("--from", dest="date_from", help="起始日期 YYYY-MM-DD")
    p.add_argument("--to", dest="date_to", help="结束日期 YYYY-MM-DD")
    p.add_argument("--range", nargs=2, metavar=("A", "B"), help="read --range a b")

    p.add_argument("--out", help="导出文件路径")
    p.add_argument("--fmt", choices=["json", "csv", "md"], default="json", help="导出格式")
    p.add_argument("--yes", action="store_true", help="purge 的二次确认开关")

    p.add_argument("--dir", dest="data_dir", help="覆盖档案目录（不得指向包内）")
    p.add_argument("--term-start", dest="term_start", default=DEFAULT_TERM_START,
                   help="第 1 周周一，默认 2026-09-07")
    p.add_argument("--json-out", action="store_true",
                   help="list/stats 以 JSON 输出，供下游脚本消费")
    return p


def _preprocess_argv(argv):
    """兼容设计稿的子命令写法：add / read / stats / purge / export / selftest。"""
    if not argv:
        return argv
    head = argv[0]
    mapping = {"add": "--add", "read": "--list", "stats": "--stats",
               "purge": "--purge", "export": "--export", "selftest": "--selftest"}
    if head in mapping and not head.startswith("-"):
        return [mapping[head]] + list(argv[1:])
    return argv


def _print_entries(entries, title):
    if not entries:
        out("暂无记录")
        return
    out(title + "（%d 条）" % len(entries))
    out("-" * 72)
    for e in entries:
        tags = "、".join(e.get("tags") or [])
        out("  %s  W%-2s  %-8s %-22s %-8s %4sm  %s" % (
            e.get("date", "?"), e.get("week_no", "?"), e.get("task_id", "?"),
            (e.get("title", "") or "")[:22], e.get("status", "?"),
            e.get("minutes", 0), tags))
        if e.get("note"):
            out("        备注：%s" % e["note"])
    out("-" * 72)


def main(argv=None):
    _init_stdio()
    argv = list(sys.argv[1:] if argv is None else argv)
    argv = _preprocess_argv(argv)
    args = build_parser().parse_args(argv)

    if not any([args.add, args.list, args.stats, args.export, args.purge, args.selftest]):
        build_parser().print_help()
        return 2

    if args.selftest:
        return run_selftest()

    if args.range:
        args.date_from, args.date_to = args.range[0], args.range[1]

    # --dir 显式指向包内 -> 隐私门禁拦截（负向对照入口）
    if args.data_dir:
        try:
            guard_user_writable(args.data_dir, "--dir 指定的档案目录")
        except (AssertionError, PrivacyViolation) as exc:
            fail(str(exc))
            out("提示：功劳档案属用户数据，请改用默认目录或 --dir <用户目录下的路径>。")
            return 2

    try:
        lb = Logbook(data_dir=args.data_dir, term_start=args.term_start)
    except PrivacyViolation as exc:
        fail(str(exc))
        return 2
    except AssertionError as exc:
        fail(str(exc))
        return 2
    except ValidationError as exc:
        fail("term_start 非法：%s" % exc)
        return 2

    try:
        if args.add:
            rec = None
            if args.json_record:
                try:
                    rec = json.loads(args.json_record)
                except ValueError as exc:
                    fail("--json 不是合法 JSON：%s" % exc)
                    return 2
                if not isinstance(rec, dict):
                    fail("--json 必须是 JSON 对象")
                    return 2
            # 扩展字段：只传非空项，避免把 None 写进 JSONL
            extra = {k: v for k, v in (
                ("priority", args.priority),
                ("attribution", args.attribution),
                ("plan_id", args.plan_id),
                ("planned_minutes", args.planned_minutes),
                ("actual_minutes", args.actual_minutes),
            ) if v is not None}
            if args.fact_refs:
                extra["fact_refs"] = _coerce_tags(args.fact_refs)

            entry = lb.add(date=args.date, task_id=args.task_id, title=args.title,
                           status=args.status, minutes=args.minutes,
                           tags=args.tags, note=args.note, record=rec, **extra)
            ok("已记录：%s W%s %s [%s] %s 分钟" % (
                entry["date"], entry["week_no"], entry["task_id"],
                entry["status"], entry["minutes"]))
            out("档案：%s" % lb.path)
            return 0

        if args.list:
            entries = lb.list_entries(week=args.week,
                                      date_from=args.date_from, date_to=args.date_to)
            if args.json_out:
                out(json.dumps(entries, ensure_ascii=False, indent=2))
                return 0
            scope = "全部记录"
            if args.week is not None:
                monday, sunday = week_range(args.week, lb.term_start)
                scope = "第 %s 周（%s ~ %s）" % (args.week, monday.isoformat(), sunday.isoformat())
            elif args.date_from or args.date_to:
                scope = "%s ~ %s" % (args.date_from or "最早", args.date_to or "最新")
            _print_entries(entries, scope)
            return 0

        if args.stats:
            s = lb.stats()
            if args.json_out:
                out(json.dumps(s, ensure_ascii=False, indent=2))
                return 0
            if s["count"] == 0:
                out("暂无记录")
                return 0
            out("功劳档案统计（学期起始 %s）" % s["term_start"])
            out("-" * 72)
            out("  记录条数      ：%d" % s["count"])
            out("  完成率(按条数)：%.1f%%  (%s/%s)" % (
                s["completion_rate"], s["by_status"][STATUS_DONE], s["count"]))
            if s["minutes_rate"] is None:
                out("  完成率(按工时)：—（无计划工时）")
                out("  工时投入率    ：—（无计划工时）")
            else:
                out("  完成率(按工时)：%.1f%%  (%s/%s 分钟)" % (
                    s["minutes_rate"], s["planned_done"], s["planned_total"]))
                out("  工时投入率    ：%.1f%%  (%s/%s)  [估时偏差信号，非完成率]" % (
                    s["effort_ratio"], s["actual_total"], s["planned_total"]))
            out("  总投入分钟    ：%d 分钟（约 %.2f 小时）" % (
                s["minutes_total"], s["hours_total"]))
            out("  连续打卡天数  ：%d 天（最近一次 %s）" % (
                s["streak_days"], s["last_date"]))
            out("  最长连续打卡  ：%d 天" % s["best_streak_days"])
            out("  活跃天数      ：%d 天（%s ~ %s）" % (
                s["active_days"], s["first_date"], s["last_date"]))
            if s["p0_rate"] is None:
                out("  P0 完成率     ：—（无 P0 项）")
            else:
                out("  P0 完成率     ：%.1f%%  (%s/%s 项)" % (
                    s["p0_rate"], s["p0_done"], s["p0_total"]))
            out("  状态分布      ：done %d / partial %d / skipped %d" % (
                s["by_status"][STATUS_DONE], s["by_status"][STATUS_PARTIAL],
                s["by_status"][STATUS_SKIPPED]))
            if s["by_status"][STATUS_PARTIAL]:
                out("  注：partial %d 条未计完成（无 progress 字段，按 0 计入）"
                    % s["by_status"][STATUS_PARTIAL])
            if s["attribution"]:
                out("  归因分布      ：%s" % "、".join(
                    "%s x%d" % (k, v) for k, v in sorted(
                        s["attribution"].items(), key=lambda kv: -kv[1])))
            out("  覆盖周次      ：%s" % (
                "、".join("W%d" % w for w in s["weeks_covered"]) or "无"))
            if s["tags"]:
                out("  标签分布      ：%s" % "、".join(
                    "%s x%d" % (k, v) for k, v in sorted(
                        s["tags"].items(), key=lambda kv: -kv[1])))
            out("-" * 72)
            return 0

        if args.export:
            path = lb.export(out_path=args.out, fmt=args.fmt)
            n = len(lb.load())
            size = os.path.getsize(path) if os.path.exists(path) else 0
            if n == 0:
                out("暂无记录")
            ok("已导出 %d 条 -> %s（%d 字节，格式 %s）" % (n, path, size, args.fmt))
            return 0

        if args.purge:
            if not args.yes:
                fail("拒绝执行：purge 会清空全部功劳档案，请显式加 --yes 二次确认。")
                out("示例：logbook.py --purge --yes")
                return 2
            lb.purge(confirm=True)
            ok("档案已清空：%s" % lb.path)
            return 0

    except PrivacyViolation as exc:
        fail(str(exc))
        return 2
    except AssertionError as exc:
        fail(str(exc))
        return 2
    except ValidationError as exc:
        fail(str(exc))
        return 2
    except OSError as exc:
        fail("读写档案失败：%s" % exc)
        return 2

    return 2


# --------------------------------------------------------------------------
# 内建自检（--selftest）
# --------------------------------------------------------------------------

def run_selftest():
    """在临时目录里跑，绝不污染用户真实档案。"""
    checks = []

    def check(name, fn):
        try:
            fn()
            checks.append((True, name, ""))
            ok(name)
        except Exception as exc:
            checks.append((False, name, "%s: %s" % (type(exc).__name__, exc)))
            fail("%s -> %s: %s" % (name, type(exc).__name__, exc))

    tmp = tempfile.mkdtemp(prefix="logbook-selftest-")

    # 1. 周次反推（对齐设计稿 D-N5-a 锚点）
    def _week():
        assert week_no_of("2026-09-07", DEFAULT_TERM_START) == 1
        assert week_no_of("2026-10-19", DEFAULT_TERM_START) == 7
        assert week_no_of("2026-10-25", DEFAULT_TERM_START) == 7
        assert week_no_of("2027-01-04", DEFAULT_TERM_START) == 18
        assert week_no_of("2027-01-11", DEFAULT_TERM_START) == 19
        assert week_no_of("2027-01-18", DEFAULT_TERM_START) == 20
        monday, sunday = week_range(7, DEFAULT_TERM_START)
        assert monday.isoformat() == "2026-10-19" and sunday.isoformat() == "2026-10-25"
    check("周次反推（W7=10-19~10-25，W18/19/20 锚点）", _week)

    # 2. term_start 必须是周一
    def _monday():
        try:
            parse_term_start("2026-09-08")
        except ValidationError:
            return
        raise AssertionError("非周一的 term_start 未被拒绝")
    check("term_start 非周一被拒绝", _monday)

    # 3. 空档案优雅降级
    def _empty():
        lb = Logbook(data_dir=os.path.join(tmp, "empty"))
        assert lb.load() == []
        assert lb.by_week(7) == []
        s = lb.stats()
        assert s["count"] == 0 and s["minutes_total"] == 0 and s["streak_days"] == 0
        p = lb.export(out_path=os.path.join(tmp, "empty-export.json"))
        assert os.path.getsize(p) > 0
    check("空档案优雅降级（list/stats/export 不抛异常）", _empty)

    # 4. 追加三条 + 读回
    def _rw():
        lb = Logbook(data_dir=os.path.join(tmp, "rw"))
        lb.add(date="2026-10-19", task_id="T1.1", title="完成实验报告",
               status="done", minutes=90, tags=["实验"], note="第一章")
        lb.add(date="2026-10-21", task_id="T1.2", title="复习高数",
               status="partial", minutes=45, tags=["复习", "高数"], note=None)
        lb.add(date="2026-10-25", task_id="T1.3", title="跑步",
               status="skipped", minutes=0, tags="运动", note="下雨")
        entries = lb.load()
        assert len(entries) == 3, entries
        assert [e["week_no"] for e in entries] == [7, 7, 7]
        assert lb.by_week(7).__len__() == 3
        assert lb.by_week(8) == []
        assert lb.by_range("2026-10-20", "2026-10-24").__len__() == 1
        assert entries[0]["note"] == "第一章" and entries[1]["note"] is None
        assert entries[1]["tags"] == ["复习", "高数"]
    check("add x3 -> 读回，week_no 与过滤均正确", _rw)

    # 4b. 下游桥接字段（term_summary.py 的工时口径依赖）
    def _bridge():
        lb = Logbook(data_dir=os.path.join(tmp, "bridge"))
        e1 = lb.add(date="2026-10-21", task_id="B1", title="t", status="done", minutes=90)
        assert e1["actual_minutes"] == 90 and e1["planned_minutes"] == 90, e1
        e2 = lb.add(date="2026-10-22", task_id="B2", title="t", status="partial",
                    minutes=45, planned_minutes=120, actual_minutes=45)
        assert e2["planned_minutes"] == 120 and e2["actual_minutes"] == 45, e2
        # 兜底后下游 planned 总和非零，工时完成率不会恒为 0
        assert sum(int(x.get("planned_minutes") or 0) for x in lb.load()) == 210
    check("下游桥接：planned/actual 工时兜底（防下游 0/0）", _bridge)

    # 5. 统计口径
    def _stats():
        lb = Logbook(data_dir=os.path.join(tmp, "rw"))
        s = lb.stats()
        assert s["count"] == 3
        assert s["minutes_total"] == 135, s["minutes_total"]
        assert s["minutes_done"] == 90
        assert s["by_status"] == {"done": 1, "partial": 1, "skipped": 1}
        assert abs(s["completion_rate"] - 33.3) < 0.05
        assert abs(s["minutes_rate"] - 66.7) < 0.05
        assert s["active_days"] == 3
    check("stats 完成率 / 总分钟 / 活跃天数可手工验证", _stats)

    # 5b. 三口径完成率 + 归因分布（对齐 logbook-spec.md §4.1）
    def _three_rate():
        d = os.path.join(tmp, "rate")
        lb = Logbook(data_dir=d)
        lb.add(date="2026-10-19", task_id="A1", title="t", status="done",
               minutes=60, priority="P0", attribution="none")
        lb.add(date="2026-10-20", task_id="A2", title="t", status="skipped",
               minutes=30, priority="P0", attribution="estimate")
        lb.add(date="2026-10-21", task_id="A3", title="t", status="done",
               minutes=20, priority="P2", attribution="fact_error")
        s = lb.stats()
        assert s["count"] == 3 and s["by_status"][STATUS_DONE] == 2
        assert abs(s["completion_rate"] - 66.7) < 0.05, s["completion_rate"]
        assert abs(s["minutes_rate"] - 72.7) < 0.05, s["minutes_rate"]
        assert s["p0_total"] == 2 and s["p0_done"] == 1
        assert abs(s["p0_rate"] - 50.0) < 0.05, s["p0_rate"]
        assert s["attribution"] == {"none": 1, "estimate": 1, "fact_error": 1}, s["attribution"]
    check("三口径完成率 + 归因分布（P0 单列）", _three_rate)

    # 5c. P0 完成率零分母：无 P0 项 → None（—（无 P0 项））；混合 → 真零/真值
    def _p0_zero():
        # 无 priority 字段：p0_total==0，必须 None，不得 0.0（0/0 假红）
        d0 = os.path.join(tmp, "p0zero")
        Logbook(data_dir=d0).add(date="2026-10-19", task_id="Z1", title="t",
                                status="done", minutes=10)
        s0 = Logbook(data_dir=d0).stats()
        assert s0["p0_total"] == 0 and s0["p0_rate"] is None, (s0["p0_total"], s0["p0_rate"])
        # 1 条 P0 done + 1 条 P0 skipped：p0_total=2, p0_done=1 → 50.0%（真值）
        dm = os.path.join(tmp, "p0mix")
        lb = Logbook(data_dir=dm)
        lb.add(date="2026-10-19", task_id="M1", title="t", status="done",
               minutes=10, priority="P0")
        lb.add(date="2026-10-20", task_id="M2", title="t", status="skipped",
               minutes=10, priority="P0")
        sm = lb.stats()
        assert sm["p0_total"] == 2 and sm["p0_done"] == 1
        assert abs(sm["p0_rate"] - 50.0) < 0.05, sm["p0_rate"]
        assert sm["by_status"][STATUS_SKIPPED] == 1  # 真零（分母>0 且 done=0）仍成立
    check("P0 完成率零分母：无 P0 项→None，混合→真值", _p0_zero)

    # 6. 连续打卡
    def _streak_calc():
        # 注意：闭包内不可命名为 _streak，否则遮蔽模块级 _streak(dates)
        assert _streak(["2026-10-19", "2026-10-20", "2026-10-21"]) == 3
        assert _streak(["2026-10-19", "2026-10-21"]) == 1
        assert _streak(["2026-10-19"]) == 1
        assert _streak([]) == 0
        assert _best_streak(["2026-10-19", "2026-10-20", "2026-10-22", "2026-10-23"]) == 2
        assert _best_streak([]) == 0
    check("连续打卡天数计算", _streak_calc)

    # 7. append-only（多次 add 不覆盖）
    def _append_only():
        d = os.path.join(tmp, "append")
        lb = Logbook(data_dir=d)
        for i in range(5):
            lb.add(date="2026-10-2%d" % min(i, 5), task_id="T%d" % i,
                   title="t%d" % i, status="done", minutes=10)
        assert len(load_entries(os.path.join(d, ARCHIVE_NAME))) == 5
    check("append-only：连续写入不被覆盖", _append_only)

    # 8. BOM 兼容
    def _bom():
        d = os.path.join(tmp, "bom")
        os.makedirs(d, exist_ok=True)
        p = os.path.join(d, ARCHIVE_NAME)
        with io.open(p, "w", encoding="utf-8-sig") as fh:
            fh.write(json.dumps({"date": "2026-10-21", "task_id": "B1",
                                 "title": "BOM", "status": "done",
                                 "minutes": 5, "tags": [], "note": None}) + "\n")
        e = load_entries(p)
        assert len(e) == 1 and e[0]["title"] == "BOM" and e[0]["week_no"] == 7
    check("BOM 档案可读（utf-8-sig）", _bom)

    # 9. 坏行跳过
    def _badline():
        d = os.path.join(tmp, "bad")
        os.makedirs(d, exist_ok=True)
        p = os.path.join(d, ARCHIVE_NAME)
        with io.open(p, "w", encoding="utf-8") as fh:
            fh.write("not json at all\n")
            fh.write(json.dumps({"date": "2026-10-21", "task_id": "G1", "title": "good",
                                 "status": "done", "minutes": 5, "tags": [], "note": None}) + "\n")
        e = load_entries(p)
        assert len(e) == 1 and e[0]["task_id"] == "G1"
    check("坏行跳过，好数据仍可读", _badline)

    # 10. schema 校验拒绝
    def _invalid():
        lb = Logbook(data_dir=os.path.join(tmp, "invalid"))
        for bad in (
            {"date": "2026-10-21", "task_id": "X", "title": "t", "status": "yeah", "minutes": 5},
            {"date": "2026-13-45", "task_id": "X", "title": "t", "status": "done", "minutes": 5},
            {"date": "2026-10-21", "task_id": "X", "title": "t", "status": "done"},
            {"date": "2026-10-21", "task_id": "X", "title": "t", "status": "done", "minutes": -3},
        ):
            try:
                lb.add(record=bad)
            except ValidationError:
                continue
            raise AssertionError("非法记录未被拒绝：%r" % bad)
        assert not os.path.exists(os.path.join(tmp, "invalid", ARCHIVE_NAME))
    check("非法记录被拒绝（status/date/minutes/缺字段）", _invalid)

    # 11. 隐私门禁：包内路径必须被拦
    def _privacy():
        blocked = 0
        for target in (PACKAGE_ROOT,
                       os.path.join(PACKAGE_ROOT, "data"),
                       _SCRIPTS_DIR):
            try:
                Logbook(data_dir=target)
            except (AssertionError, PrivacyViolation):
                blocked += 1
        assert blocked == 3, "只拦了 %d/3 个包内路径" % blocked
        try:
            guard_user_writable(os.path.join(PACKAGE_ROOT, "logbook.jsonl"), "档案文件")
        except (AssertionError, PrivacyViolation):
            blocked += 1
        assert blocked == 4
    check("隐私门禁：包内路径一律拦截（4/4）", _privacy)

    # 12. 用户目录默认可用
    def _default_dir():
        d = default_data_dir()
        assert not is_inside_package(d), d
        guard_user_writable(d, "默认档案目录")
    check("默认目录落在用户侧且通过门禁", _default_dir)

    # 13. purge 二次确认
    def _purge():
        d = os.path.join(tmp, "purge")
        lb = Logbook(data_dir=d)
        lb.add(date="2026-10-21", task_id="P1", title="p", status="done", minutes=5)
        try:
            lb.purge(confirm=False)
        except ValidationError:
            pass
        else:
            raise AssertionError("未加确认的 purge 未被拒绝")
        assert len(lb.load()) == 1, "purge 未确认却改动了数据"
        lb.purge(confirm=True)
        assert lb.load() == []
    check("purge 须二次确认（未确认不动数据）", _purge)

    # 14. 导出三种格式
    def _export():
        lb = Logbook(data_dir=os.path.join(tmp, "rw"))
        for f in ("json", "csv", "md"):
            p = lb.export(out_path=os.path.join(tmp, "e." + f), fmt=f)
            assert os.path.getsize(p) > 0, f
        with io.open(os.path.join(tmp, "e.json"), encoding="utf-8") as fh:
            obj = json.load(fh)
        assert obj["count"] == 3 and len(obj["entries"]) == 3
    check("导出 json/csv/md 均非空且 json 可解析", _export)

    # 清理临时目录
    try:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)
    except Exception:
        pass

    passed = sum(1 for c in checks if c[0])
    total = len(checks)
    out("")
    if passed == total:
        ok("selftest 全部通过：%d/%d" % (passed, total))
        return 0
    fail("selftest 未通过：%d/%d" % (passed, total))
    for good, name, msg in checks:
        if not good:
            out("  [FAIL] %s -> %s" % (name, msg))
    return 1


if __name__ == "__main__":
    sys.exit(main())
