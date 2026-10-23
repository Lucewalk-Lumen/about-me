#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
holiday_lookup.py — 节假日 / 调休上班日「日期性质」查表（N1 核心）。

用途
----
对给定日期或日期区间回答一个问题：这一天是「法定假日」「调休上班日」，还是
「未命中 unknown」。答案只能来自包内 data/holidays-<year>.json 的已登记条目，
绝不来自「周末就是休息日」这类通用推演——调休上班日恰恰经常落在周末
（如 2026-09-20 周日、2026-10-10 周六必须上班），这正是本项目诊断点名的易错点。

输入
----
  默认数据源（包内只读基线）：
    <包根>/data/holidays-2026.json    已官宣年，默认参与排程
    <包根>/data/holidays-2027.json    未官宣年，status=predicted，默认不参与排程
  --data-dir <PATH>  指向另一份数据副本（供门禁做负向对照，不对两个真源做破坏实验）

输出
----
  stdout 文本报告（纯文本标记 [OK]/[WARN]/[FAIL]，无 emoji，Windows 控制台可直接打印）
  --json            额外输出机器可读 JSON（供渲染脚本 / fact-verifier 消费）
  每条结果字段：date / weekday（纯日历算术，非结论）/ nature / confidence /
                status / source_id / counts_as / note

P0 红线
-------
  未命中一律返回 nature="unknown"，禁止填充为「普通周末」或「工作日」。
  若确实需要「这一天的日历星期是周六/周日」的算术基线，必须显式传
  --with-weekday-baseline；该基线单独成列并 explicit 标注「非放行结论，不得用于排程」。
  2027 预测数据默认不参与排程，只有 --include-predicted 显式开启才会被查、且结果一律标
  [WARN] predicted。

退出码
------
  0  查询完成（返回 unknown 也是合法答案，不是错误）
  1  命令行参数错误 / 用法错误 / 日期格式非法 / 区间倒挂
  2  自检（--selfcheck）失败，或双向索引一致性校验失败
  3  数据文件缺失、不可读或 JSON 解析失败

用法
----
  python holiday_lookup.py --date 2026-10-10
  python holiday_lookup.py --range 2026-09-07 2027-01-24
  python holiday_lookup.py --range 2026-10-01 2026-10-31 --json
  python holiday_lookup.py --selfcheck
  python holiday_lookup.py --year 2027 --date 2027-01-01 --include-predicted

仅依赖 Python 标准库，无第三方包要求。已实跑于 Windows + Python 3.13。
"""

import argparse
import json
import os
import sys
from datetime import date, datetime, timedelta

try:  # Windows GBK 控制台兜底：强制按 UTF-8 输出，非法字符降级为 '?' 而不是抛异常
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # 非 CPython / 无 reconfigure 时不致命，走默认编码
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
PKG_ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))  # scripts -> <skill> -> skills -> <pkg>
DEFAULT_DATA_DIR = os.path.join(PKG_ROOT, "data")

WEEKDAY_CN = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

NATURE_HOLIDAY = "holiday"
NATURE_MAKEUP = "make_up_workday"
NATURE_UNKNOWN = "unknown"

NATURE_CN = {
    NATURE_HOLIDAY: "法定假日",
    NATURE_MAKEUP: "调休上班日",
    NATURE_UNKNOWN: "unknown",
}

VALID_CONFIDENCE = {"high", "medium", "low", "unknown"}
VALID_STATUS = {"official", "predicted"}
VALID_TYPE = {"holiday", "make_up_workday"}

MAX_RANGE_DAYS = 800  # 防止手滑把几十年区间灌进来


# --------------------------------------------------------------------------
# 文本输出工具
# --------------------------------------------------------------------------
def _display_width(s):
    """按终端实际占位宽度算：CJK 全角字符算 2 列。"""
    w = 0
    for ch in s:
        w += 2 if ord(ch) > 0x2E7F else 1
    return w


def pad(s, width, align="left"):
    """按显示宽度补空格，保证中英混排表格对齐。"""
    gap = width - _display_width(s)
    if gap <= 0:
        return s
    if align == "right":
        return " " * gap + s
    return s + " " * gap


def parse_date(text, field=None):
    """严格 ISO YYYY-MM-DD 解析。失败返回 (None, errmsg)。"""
    if not isinstance(text, str) or len(text) != 10 or text[4] != "-" or text[7] != "-":
        return (None, "日期格式非法（须 YYYY-MM-DD）：%r%s" % (text, " @%s" % field if field else ""))
    try:
        return (datetime.strptime(text, "%Y-%m-%d").date(), None)
    except ValueError as exc:
        return (None, "日期格式非法（%s）：%r%s" % (exc, text, " @%s" % field if field else ""))


# --------------------------------------------------------------------------
# 数据加载与索引
# --------------------------------------------------------------------------
class DataError(Exception):
    """数据文件缺失 / 不可解析 —— 对应退出码 3。"""
    pass


def load_year_file(path, year):
    """读取并做基础性体检。失败抛 DataError。"""
    if not os.path.isfile(path):
        raise DataError("数据文件缺失：%s" % path)
    try:
        with open(path, "r", encoding="utf-8-sig") as fh:
            raw = fh.read()
    except OSError as exc:
        raise DataError("数据文件不可读：%s (%s)" % (path, exc))
    try:
        doc = json.loads(raw)
    except ValueError as exc:
        raise DataError("JSON 解析失败：%s (%s)" % (path, exc))
    if not isinstance(doc, dict):
        raise DataError("顶层结构非法（应为 object）：%s" % path)
    if "entries" not in doc or not isinstance(doc["entries"], list):
        raise DataError("缺少 entries 数组：%s" % path)
    doc["__path"] = path
    doc["__year"] = year
    return doc


def _entry_key_days(entry):
    """返回该条目实际占用的日期列表；未裁决（resolved=false / start=null）返回 []。"""
    if entry.get("resolved") is False:
        return []
    start = entry.get("start")
    end = entry.get("end")
    if not start or not end:
        return []
    s, err = parse_date(start)
    e, err2 = parse_date(end)
    if s is None or e is None:
        return []
    if e < s:
        return []
    days = []
    cur = s
    while cur <= e:
        days.append(cur.isoformat())
        cur += timedelta(days=1)
    return days


class CalendarIndex(object):
    """双向索引：节假日 -> 调休上班日（正向），调休上班日 -> 所属节假日（反向）。"""

    def __init__(self, data_dir, years, allow_predicted=False):
        self.data_dir = data_dir
        self.years = list(years)
        self.allow_predicted = allow_predicted
        self.docs = {}
        self.holiday_by_date = {}
        self.makeup_by_date = {}
        self.holiday_entries = {}
        self.makeup_entries = {}
        self.unresolved_zones = []  # [(start_iso, end_iso, entry)] 未裁决冲突区间
        self.predicted_entries = []
        self._build()

    # -- 构建 ----------------------------------------------------------
    def _build(self):
        for year in self.years:
            path = os.path.join(self.data_dir, "holidays-%d.json" % year)
            doc = load_year_file(path, year)
            self.docs[year] = doc
            for entry in doc.get("entries", []):
                self._register(entry, doc)

    def _register(self, entry, doc):
        eid = entry.get("id")
        etype = entry.get("type")
        is_predicted = (entry.get("status") == "predicted"
                        or doc.get("participates_in_scheduling_default") is False)
        if is_predicted:
            self.predicted_entries.append(entry)
            # predicted 数据默认不进查询索引：只有 --include-predicted 才登记，
            # 但「未裁决冲突区间」始终登记，以便 unknown 结果能说明为何 unknown。
            if not self.allow_predicted and entry.get("resolved") is False:
                self._register_unresolved(entry)
                return
            if not self.allow_predicted:
                return
        if etype == NATURE_HOLIDAY:
            self.holiday_entries[eid] = entry
            for iso in entry.get("dates") or _entry_key_days(entry):
                self.holiday_by_date[iso] = entry
            if entry.get("resolved") is False:
                self._register_unresolved(entry)
        elif etype == NATURE_MAKEUP:
            key = entry.get("date") or entry.get("start")
            if key:
                self.makeup_entries[eid] = entry
                self.makeup_by_date[key] = entry

    def _register_unresolved(self, entry):
        conflict = entry.get("conflict") or {}
        for scheme in conflict.get("schemes") or []:
            if scheme.get("start") and scheme.get("end"):
                self.unresolved_zones.append((scheme["start"], scheme["end"], entry))

    # -- 查询 ----------------------------------------------------------
    def classify(self, d):
        """返回该日期的性质字典。未命中 -> nature=unknown（不脑补）。"""
        iso = d.isoformat()
        base = {
            "date": iso,
            "weekday_index": d.weekday() + 1,
            "weekday": WEEKDAY_CN[d.weekday()],
        }
        hit = self.makeup_by_date.get(iso)
        if hit is not None:
            base.update({
                "nature": NATURE_MAKEUP,
                "nature_cn": NATURE_CN[NATURE_MAKEUP],
                "name": hit.get("name"),
                "confidence": hit.get("confidence"),
                "status": hit.get("status"),
                "source_id": hit.get("id"),
                "counts_as": hit.get("counts_as") or "workday",
                "belongs_to": hit.get("belongs_to"),
                "source_url": hit.get("source_url"),
                "originally_verified": hit.get("originally_verified"),
                "official_basis": hit.get("official_basis"),
                "official_basis_document": hit.get("official_basis_document"),
                "note": hit.get("note") or "",
                "hit": True,
            })
            return self._decorate(base)

        hit = self.holiday_by_date.get(iso)
        if hit is not None:
            base.update({
                "nature": NATURE_HOLIDAY,
                "nature_cn": NATURE_CN[NATURE_HOLIDAY],
                "name": hit.get("name"),
                "confidence": hit.get("confidence"),
                "status": hit.get("status"),
                "source_id": hit.get("id"),
                "counts_as": "rest",
                "belongs_to": None,
                "source_url": hit.get("source_url"),
                "originally_verified": hit.get("originally_verified"),
                "official_basis": hit.get("official_basis"),
                "official_basis_document": hit.get("official_basis_document"),
                "note": hit.get("note") or "",
                "hit": True,
            })
            return self._decorate(base)

        base.update({
            "nature": NATURE_UNKNOWN,
            "nature_cn": NATURE_CN[NATURE_UNKNOWN],
            "name": None,
            "confidence": None,
            "status": None,
            "source_id": None,
            "counts_as": None,
            "belongs_to": None,
            "source_url": None,
            "originally_verified": None,
            "official_basis": None,
            "official_basis_document": None,
            "note": ("未命中 %s 中的任何已登记条目%s" % (
                "、".join("holidays-%s.json" % y for y in sorted(self.years)),
                "（predicted 年份默认未启用查询结果）"
                if (not self.allow_predicted and any(y != 2026 for y in self.years)) else "",
            )),
            "hit": False,
        })
        return self._decorate(base)

    def _decorate(self, rec):
        """预测数据显式降权 + 未裁决冲突区告警。"""
        rec["participates_in_scheduling"] = True
        if rec.get("status") == "predicted":
            rec["participates_in_scheduling"] = bool(self.allow_predicted)
            rec["note"] = "[WARN] predicted 数据，默认不参与排程。" + (rec.get("note") or "")
        if rec["nature"] == NATURE_UNKNOWN:
            zone = self.unresolved_zone_of(rec["date"])
            if zone:
                s, e, entry = zone
                rec["note"] += (
                    " 该日落在「%s」的未裁决预测冲突区间 %s~%s 之内（共 %d 套互斥方案，未选定真值），"
                    "因此仍返回 unknown，须由 fact-verifier 列入待确认清单。" %
                    (entry.get("name"), s, e, len((entry.get("conflict") or {}).get("schemes") or []))
                )
        return rec

    def unresolved_zone_of(self, iso):
        for s, e, entry in self.unresolved_zones:
            if s <= iso <= e:
                return (s, e, entry)
        return None

    def weekday_baseline(self, d):
        """纯日历算术基线（周六/周日/工作日字样），明确非放行结论。"""
        wd = d.weekday()
        if wd >= 5:
            return "普通周末（日历算术）"
        return "工作日（日历算术）"


# --------------------------------------------------------------------------
# 自检
# --------------------------------------------------------------------------
def _required_fields_check(idx, lines):
    """每条必备字段 + 取值合法性 + declared counts 是否对得上。"""
    required = ["id", "name", "type", "start", "end", "days",
                "source_url", "fetched_at", "confidence", "status",
                "official_basis", "make_up_workdays"]
    for year, doc in sorted(idx.docs.items()):
        entries = doc.get("entries", [])
        for i, entry in enumerate(entries):
            tag = "%d#%d(%s)" % (year, i, entry.get("id"))
            missing = [k for k in required if k not in entry]
            if missing:
                lines.append("[FAIL] %s 缺必备字段：%s" % (tag, ", ".join(missing)))
                continue
            if entry.get("type") not in VALID_TYPE:
                lines.append("[FAIL] %s type 取值非法：%r" % (tag, entry.get("type")))
            if entry.get("confidence") not in VALID_CONFIDENCE:
                lines.append("[FAIL] %s confidence 取值非法：%r" % (tag, entry.get("confidence")))
            if entry.get("status") not in VALID_STATUS:
                lines.append("[FAIL] %s status 取值非法：%r" % (tag, entry.get("status")))
            if not isinstance(entry.get("make_up_workdays"), list):
                lines.append("[FAIL] %s make_up_workdays 必须是数组" % tag)
            # 已裁决条目的天数自洽
            if entry.get("resolved") is not False and isinstance(entry.get("days"), int):
                start, err1 = parse_date(entry["start"])
                end, err2 = parse_date(entry["end"])
                if err1 or err2:
                    lines.append("[FAIL] %s start/end 日期非法：%s%s" % (tag, err1 or "", err2 or ""))
                    continue
                span = (end - start).days + 1
                if span != entry["days"]:
                    lines.append("[FAIL] %s days=%s 与区间跨度 %d 不符" % (tag, entry["days"], span))
                if end < start:
                    lines.append("[FAIL] %s 起止倒挂：%s > %s" % (tag, entry["start"], entry["end"]))
                declared = entry.get("dates")
                if declared is not None:
                    real = _entry_key_days(entry)
                    if declared != real:
                        lines.append("[FAIL] %s dates[] 与 start/end 展开不一致" % tag)
                    if len(set(declared)) != len(declared):
                        lines.append("[FAIL] %s dates[] 存在重复日期" % tag)
                    if declared != sorted(declared):
                        lines.append("[FAIL] %s dates[] 未按升序排列" % tag)
                # 星期标注防抄写错
                if entry.get("start_weekday") and entry["start_weekday"] != WEEKDAY_CN[start.weekday()]:
                    lines.append("[FAIL] %s start_weekday=%s 与实际 %s 不符"
                                 % (tag, entry["start_weekday"], WEEKDAY_CN[start.weekday()]))
                if entry.get("end_weekday") and entry["end_weekday"] != WEEKDAY_CN[end.weekday()]:
                    lines.append("[FAIL] %s end_weekday=%s 与实际 %s 不符"
                                 % (tag, entry["end_weekday"], WEEKDAY_CN[end.weekday()]))
            # 年份归属
            for key in ("start", "end"):
                v = entry.get(key)
                if isinstance(v, str) and v[:4].isdigit() and int(v[:4]) != year:
                    lines.append("[FAIL] %s %s=%s 不属于 %d 年文件" % (tag, key, v, year))
            # 侵害篡改标记
            if "originally_verified" not in entry:
                lines.append("[FAIL] %s 缺 originally_verified 字段（禁止冒充已核验）" % tag)

        # 声明条数 vs 实际条数
        counts = doc.get("counts") or {}
        h = len([e for e in entries if e.get("type") == NATURE_HOLIDAY])
        m = len([e for e in entries if e.get("type") == NATURE_MAKEUP])
        for key, real in (("holiday_entries", h), ("make_up_workday_entries", m), ("entries_total", len(entries))):
            declared = counts.get(key)
            if isinstance(declared, int) and declared != real:
                lines.append("[FAIL] %d 年 counts.%s 声明 %d，实际 %d" % (year, key, declared, real))


def _bidirectional_index_check(idx, lines):
    """双向索引一致 + 调休日不得与节假日本体重叠。"""
    forward = set()
    forward_owner = {}
    for hid, entry in idx.holiday_entries.items():
        for mu in entry.get("make_up_workdays") or []:
            d = mu.get("date")
            if not d:
                lines.append("[FAIL] %s 的 make_up_workdays 元素缺 date" % hid)
                continue
            forward.add(d)
            forward_owner.setdefault(d, []).append(hid)
            want = parse_date(d)[0]
            if want is not None and mu.get("weekday") and mu["weekday"] != WEEKDAY_CN[want.weekday()]:
                lines.append("[FAIL] %s.make_up_workdays[%s] weekday=%s 与实际 %s 不符"
                             % (hid, d, mu["weekday"], WEEKDAY_CN[want.weekday()]))

    backward = {}
    for mid, entry in idx.makeup_entries.items():
        d = entry.get("date") or entry.get("start")
        backward.setdefault(d, []).append(mid)
        owner = entry.get("belongs_to")
        if not owner:
            lines.append("[FAIL] %s 缺 belongs_to：反向索引断裂（无法反查所属节假日）" % mid)
        elif owner not in idx.holiday_entries:
            lines.append("[FAIL] %s.belongs_to=%s 不存在" % (mid, owner))
        elif owner not in forward_owner.get(d, []):
            lines.append("[FAIL] 双向索引不一致：节假日 %s 的 make_up_workdays 未内嵌调休日 %s" % (owner, d))
        if entry.get("weekday"):
            real = parse_date(d)[0]
            if real is not None and entry["weekday"] != WEEKDAY_CN[real.weekday()]:
                lines.append("[FAIL] %s weekday=%s 与实际 %s 不符" % (mid, entry["weekday"], WEEKDAY_CN[real.weekday()]))

    only_forward = sorted(forward - set(backward))
    only_backward = sorted(set(backward) - forward)
    if only_forward:
        lines.append("[FAIL] 只出现在节假日 make_up_workdays 内、无对应条目：%s" % ", ".join(only_forward))
    if only_backward:
        lines.append("[FAIL] 只出现在独立条目、未被任何节假日内嵌：%s" % ", ".join(only_backward))
    for d, owners in sorted(forward_owner.items()):
        if len(owners) > 1:
            lines.append("[FAIL] 调休日 %s 被多个节假日内嵌：%s" % (d, ", ".join(owners)))

    # 调休上班日不得落在任何节假日区间内
    for d in sorted(forward):
        owner = idx.holiday_by_date.get(d)
        if owner is not None:
            lines.append("[FAIL] 调休上班日 %s 与节假日本体 %s(%s~%s) 重叠"
                         % (d, owner.get("id"), owner.get("start"), owner.get("end")))


def _participation_declaration_check(idx, lines):
    """「是否参与排程」的声明必须与数据实际状态一致，防止顶层标识撒谎。"""
    for year, doc in sorted(idx.docs.items()):
        entries = doc.get("entries", [])
        flag = doc.get("participates_in_scheduling_default")
        has_predicted = any(e.get("status") == "predicted" for e in entries)
        all_official = bool(entries) and all(e.get("status") == "official" for e in entries)
        if has_predicted and flag is not False:
            lines.append("[FAIL] %d 年含 predicted 条目，participates_in_scheduling_default=%r（必须为 false）"
                         % (year, flag))
        if all_official and flag is not True:
            lines.append("[FAIL] %d 年全部条目 official，participates_in_scheduling_default=%r（必须为 true）"
                         % (year, flag))
        for e in entries:
            if e.get("status") != "predicted":
                continue
            for key in ("participates_in_scheduling", "participates_in_scheduling_default"):
                if e.get(key) is not False:
                    lines.append("[FAIL] %s 为 predicted 但 %s=%r（必须为 false）"
                                 % (e.get("id"), key, e.get(key)))
            if e.get("resolved") is False:
                conflict = e.get("conflict") or {}
                if conflict.get("selected_scheme") is not None:
                    lines.append("[FAIL] %s 声明未裁决但已选定 %r：不得私自选定冲突方案"
                                 % (e.get("id"), conflict.get("selected_scheme")))
                schemes = conflict.get("schemes") or []
                if len(schemes) < 2:
                    lines.append("[FAIL] %s 标记未裁决却只有 %d 套方案，无法构成互斥冲突" % (e.get("id"), len(schemes)))
                if e.get("start") or e.get("end") or e.get("days"):
                    lines.append("[FAIL] %s 未裁决条目的 start/end/days 必须为 null，实际 %r/%r/%r"
                                 % (e.get("id"), e.get("start"), e.get("end"), e.get("days")))


def _default_participation_check(data_dir, lines):
    """2027（predicted）默认不参与排程；unknown 不得被填充。"""
    probe = CalendarIndex(data_dir, [2026, 2027], allow_predicted=False)
    d2027, err = parse_date("2027-01-01")
    if err:
        lines.append("[FAIL] 探针日期非法：%s" % err)
        return None
    rec = probe.classify(d2027)
    if rec["nature"] != NATURE_UNKNOWN:
        lines.append("[FAIL] 2027 预测数据未被默认隔离：2027-01-01 返回 %s（应为 unknown）" % rec["nature"])

    probe_all = CalendarIndex(data_dir, [2026, 2027], allow_predicted=True)
    rec2 = probe_all.classify(d2027)
    if rec2["nature"] != NATURE_HOLIDAY:
        lines.append("[FAIL] 显式开启预测后 2027-01-01 应为 holiday，实际 %s" % rec2["nature"])
    if rec2.get("status") != "predicted":
        lines.append("[FAIL] 显式开启预测后 status 应为 predicted，实际 %r" % rec2.get("status"))

    probe_unknown = CalendarIndex(data_dir, [2026], allow_predicted=False)
    for iso in ("2026-03-10", "2026-11-17", "2026-12-24"):
        dd, _ = parse_date(iso)
        rec3 = probe_unknown.classify(dd)
        if rec3["nature"] != NATURE_UNKNOWN:
            lines.append("[FAIL] 未登记日期 %s 应返回 unknown，实际 %s" % (iso, rec3["nature"]))
        if rec3.get("counts_as") is not None:
            lines.append("[FAIL] unknown 日期 %s 的 counts_as 必须为 null，实际 %r" % (iso, rec3["counts_as"]))
    return probe


def _piercing_check(idx, lines):
    """调休穿透完好性：make_up_workday 必须按工作日计。"""
    for mid, entry in sorted(idx.makeup_entries.items()):
        if entry.get("counts_as") != "workday":
            lines.append("[FAIL] %s counts_as=%r，调休上班日必须按工作日计" % (mid, entry.get("counts_as")))
        d = entry.get("date") or entry.get("start")
        real = parse_date(d)[0]
        if real is not None and real.weekday() >= 5:
            rec = idx.classify(real)
            if rec["nature"] != NATURE_MAKEUP:
                lines.append("[FAIL] 周末调休日 %s 未穿透：返回 %s（禁止被「周末即休息」吞掉）"
                             % (d, rec["nature"]))


def run_selfcheck(idx):
    lines = []
    _required_fields_check(idx, lines)
    _bidirectional_index_check(idx, lines)
    _piercing_check(idx, lines)
    _participation_declaration_check(idx, lines)
    _default_participation_check(idx.data_dir, lines)

    fails = [l for l in lines if l.startswith("[FAIL]")]
    warns = [l for l in lines if l.startswith("[WARN]")]
    for line in lines:
        print(line)
    total = sum(len(d.get("entries", [])) for d in idx.docs.values())
    print("-" * 68)
    print("[OK] 自检覆盖：%d 个年份 / %d 条条目；检查项 %d 条（FAIL %d / WARN %d）"
          % (len(idx.docs), total, len(lines), len(fails), len(warns)))
    if fails:
        print("[FAIL] SELFCHECK 未通过")
        return 2
    print("[OK] SELFCHECK 通过：双向索引一致 / 调休日不重叠 / 2027 默认隔离 / unknown 未被填充")
    return 0


# --------------------------------------------------------------------------
# 报告渲染
# --------------------------------------------------------------------------
HEADERS = ["日期", "星期", "性质", "置信度", "状态", "来源编号", "所属节假日", "计入", "说明"]


def render_table(rows, with_baseline):
    widths = [10, 4, 12, 7, 9, 11, 11, 10, 40]
    heads = list(HEADERS)
    if with_baseline:
        heads.insert(3, "日历算术基线")
        widths.insert(3, 20)
    line0 = "  ".join(pad(h, w) for h, w in zip(heads, widths))
    print(line0)
    print("  ".join("-" * w for w in widths))
    for rec in rows:
        cells = [
            rec["date"],
            rec["weekday"],
            rec["nature_cn"],
            rec.get("confidence") or "-",
            rec.get("status") or "-",
            rec.get("source_id") or "-",
            rec.get("belongs_to") or "-",
            {"workday": "工作日", "rest": "休息", None: "不可计"}.get(rec.get("counts_as"), "-"),
            (rec.get("note") or "-").replace("\n", " ")[:40],
        ]
        if with_baseline:
            cells.insert(3, rec.get("_baseline", "-"))
        print("  ".join(pad(str(c), w) for c, w in zip(cells, widths)))


def capacity_summary(rows):
    total = len(rows)
    hol = sum(1 for r in rows if r["nature"] == NATURE_HOLIDAY)
    mk = sum(1 for r in rows if r["nature"] == NATURE_MAKEUP)
    unk = sum(1 for r in rows if r["nature"] == NATURE_UNKNOWN)
    print("-" * 68)
    print("调休穿透后的容量账（区间 %s ~ %s）" % (rows[0]["date"], rows[-1]["date"]))
    print("  自然日总数              : %d" % total)
    print("  法定假日（休息）        : %d 天" % hol)
    print("  调休上班日（按工作日计）: %d 天" % mk)
    print("  unknown（不得自行计入） : %d 天" % unk)
    print("  可直接计入容量的天数    : %d 天（= 仅调休上班日；其余必须逐条放行后使用）" % mk)
    hit_ratio = (hol + mk) / total * 100 if total else 0.0
    print("  表命中率                : %.1f%%" % hit_ratio)
    if any("_baseline" in r for r in rows):
        est = sum(1 for r in rows
                  if r["nature"] == NATURE_MAKEUP
                  or (r["nature"] == NATURE_UNKNOWN and r.get("_baseline", "").startswith("工作日")))
        print("  [估算] 含日历算术基线   : %d 天（= 调休上班日 + 未被占用且非周末的 unknown 日）" % est)
        print("  [WARN] 估算口径含未经查表命中的日期，属非放行口径，禁止直接写入正式排程。")


def cmd_date(idx, args):
    d, err = parse_date(args.date)
    if err:
        print("[FAIL] %s" % err)
        return 1
    rec = idx.classify(d)
    if args.with_weekday_baseline:
        rec["_baseline"] = idx.weekday_baseline(d)
    rows = [rec]
    render_table(rows, args.with_weekday_baseline)
    print("-" * 68)
    print("日期      : %s（%s）" % (rec["date"], rec["weekday"]))
    print("性质      : %s" % rec["nature_cn"])
    if rec["hit"]:
        print("名称      : %s" % rec["name"])
        print("置信度    : %s" % rec["confidence"])
        print("状态      : %s" % rec["status"])
        print("来源编号  : %s" % rec["source_id"])
        print("来源 URL  : %s" % rec["source_url"])
        print("官宣依据  : %s" % rec.get("official_basis"))
        print("原文已核验: %s" % rec.get("originally_verified"))
        print("容量计入  : %s" % {"workday": "按工作日计", "rest": "按休息日计"}.get(rec["counts_as"], "-"))
    else:
        print("[WARN] 该日期未在已加载数据中命中，性质 = unknown。")
        print("[WARN] 不按「周末即休息」填充任何结论；如需进入排程，须由 fact-verifier 放行。")
    if rec.get("note"):
        print("说明      : %s" % rec["note"])
    if args.with_weekday_baseline:
        print("[WARN] 日历算术基线 = %s：纯日期算术，非放行结论，不得用于排程。" % rec["_baseline"])
    if args.json:
        print("-" * 68)
        print(json.dumps({"mode": "date", "results": rows}, ensure_ascii=False, indent=2))
    return 0


def cmd_range(idx, args):
    start, err1 = parse_date(args.range[0], "range.start")
    end, err2 = parse_date(args.range[1], "range.end")
    if err1 or err2:
        for e in (err1, err2):
            if e:
                print("[FAIL] %s" % e)
        return 1
    if end < start:
        print("[FAIL] 区间倒挂：%s > %s" % (start.isoformat(), end.isoformat()))
        return 1
    span = (end - start).days + 1
    if span > MAX_RANGE_DAYS:
        print("[FAIL] 区间跨度 %d 天超过上限 %d 天，请缩小范围" % (span, MAX_RANGE_DAYS))
        return 1
    rows = []
    cur = start
    while cur <= end:
        rec = idx.classify(cur)
        if args.with_weekday_baseline:
            rec["_baseline"] = idx.weekday_baseline(cur)
        rows.append(rec)
        cur += timedelta(days=1)
    hits = [r for r in rows if r["hit"]]
    print("命中条目 %d 条 / 区间 %d 天" % (len(hits), len(rows)))
    print("=" * 68)
    if args.only_hits:
        rows_shown = hits
        if not rows_shown:
            print("[WARN] 该区间内无任何已登记条目（全部 unknown）。")
        else:
            render_table(rows_shown, args.with_weekday_baseline)
    else:
        render_table(rows, args.with_weekday_baseline)
    capacity_summary(rows)
    if idx.unresolved_zones:
        print("[WARN] 已加载 %d 个未裁决预测冲突区间（2027 春节），落在其内的日期仍返回 unknown。" % len(idx.unresolved_zones))
    if args.json:
        print("-" * 68)
        print(json.dumps({"mode": "range", "results": rows}, ensure_ascii=False, indent=2))
    return 0


def cmd_year(idx, args):
    year = args.year
    doc = idx.docs.get(year)
    if doc is None:
        print("[FAIL] 未加载 %d 年数据文件（可选：%s）" % (year, ", ".join(str(y) for y in idx.years)))
        return 3
    entries = doc.get("entries", [])
    print("%d 年条目清单（共 %d 条）" % (year, len(entries)))
    print("=" * 68)
    widths = [11, 14, 12, 12, 8, 8, 9, 6]
    heads = ["编号", "名称", "类型", "区间", "天数", "置信度", "状态", "参与"]
    print("  ".join(pad(h, w) for h, w in zip(heads, widths)))
    print("  ".join("-" * w for w in widths))
    for e in entries:
        if e.get("resolved") is False:
            span = "未裁决"
            days = "-"
        else:
            span = "%s~%s" % (e.get("start"), e.get("end"))
            days = e.get("days")
        part = "no" if e.get("participates_in_scheduling") is False or \
                       e.get("participates_in_scheduling_default") is False else "yes"
        cells = [e.get("id"), e.get("name"), e.get("type"), span, str(days),
                 e.get("confidence"), e.get("status"), part]
        print("  ".join(pad(str(c), w) for c, w in zip(cells, widths)))
    if year == 2027:
        print("[WARN] 2027 年为未官宣预测数据：全部 status=predicted，默认不参与排程。")
        print("[WARN] 春节存在三套互斥方案，resolved=false，未选定真值。")
    if args.json:
        print("-" * 68)
        _VALIDATED_ATTRS = ("schema_version", "data_kind", "read_only", "source", "governance",
                            "basis_document", "limits")
        meta = {k: doc.get(k) for k in _VALIDATED_ATTRS if k in doc}
        print(json.dumps({"mode": "year", "year": year, "meta": meta, "entries": entries},
                         ensure_ascii=False, indent=2))
    return 0


# --------------------------------------------------------------------------
# 入口
# --------------------------------------------------------------------------
def build_parser():
    p = argparse.ArgumentParser(
        prog="holiday_lookup.py",
        description="节假日 / 调休上班日日期性质查表（未命中一律 unknown，禁止通用规则脑补）",
    )
    p.add_argument("--date", metavar="YYYY-MM-DD", help="单日查询")
    p.add_argument("--range", nargs=2, metavar=("START", "END"), help="区间查询")
    p.add_argument("--year", type=int, metavar="YYYY", help="列出该年份全部条目（配合 json 可导出）")
    p.add_argument("--selfcheck", action="store_true", help="双向索引 / 重叠 / 2027 隔离 / unknown 自检")
    p.add_argument("--data-dir", default=DEFAULT_DATA_DIR, metavar="PATH",
                   help="数据目录（默认包内 data/；负向对照时指向副本）")
    p.add_argument("--years", nargs="+", type=int, default=[2026, 2027], metavar="YYYY",
                   help="加载哪些年份文件（默认 2026 2027）")
    p.add_argument("--include-predicted", action="store_true",
                   help="显式开启 predicted 年份参与查询（默认关闭）")
    p.add_argument("--with-weekday-baseline", action="store_true",
                   help="附一列纯日历算术基线（周六/周日），明确标注非放行结论")
    p.add_argument("--only-hits", action="store_true", help="--range 时只打印命中行")
    p.add_argument("--json", action="store_true", help="额外输出机器可读 JSON")
    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    modes = [bool(args.date), bool(args.range), args.selfcheck, args.year is not None]
    if sum(1 for m in modes if m) != 1:
        print("[FAIL] 必须且只能指定一种模式：--date / --range / --selfcheck / --year")
        return 1

    data_dir = os.path.abspath(args.data_dir)
    if not os.path.isdir(data_dir):
        print("[FAIL] 数据目录不存在：%s" % data_dir)
        return 3

    try:
        idx = CalendarIndex(data_dir, args.years, allow_predicted=bool(args.include_predicted))
    except DataError as exc:
        print("[FAIL] %s" % exc)
        return 3

    if args.selfcheck:
        return run_selfcheck(idx)
    if args.year is not None:
        return cmd_year(idx, args)
    if args.date:
        return cmd_date(idx, args)
    return cmd_range(idx, args)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BrokenPipeError:  # 管道被截断时静默退出，避免刷屏
        sys.exit(0)
