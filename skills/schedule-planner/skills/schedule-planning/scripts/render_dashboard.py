#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
render_dashboard.py — N3 完成度仪表盘：三环完成率 + 连击打卡 + 本周 vs 上周，单文件离线 HTML。

设计目的
--------
回答「我到底完成了多少」。三个口径分开算（任务数 / 工时 / P0），
因为只看任务数会被「做了十件小事、跳过一件大事」骗过去。

能力
----
  * 三环完成率：手写 SVG stroke-dasharray 环形图（无第三方图表库）
      - 任务数完成率 = done / 总记录
      - 工时完成率   = Σ actual_minutes(done) / Σ planned_minutes
      - P0 完成率    = P0 done / P0 总数
  * 连续打卡天数（连击）：按记录日期逐日回溯，断一天即归零
  * 本周 vs 上周对比：记录数 / 完成数 / 计划工时 / 实际工时 / 完成率
  * 五类偏差归因分布条（含「无偏差」与「事实错误」）

数据来源
--------
功劳档案 `%USERPROFILE%/.schedule-planner/logbook.jsonl`（JSONL append-only，用户目录，包内只读）。
档案不存在或为空时**优雅降级**：三环显示 0%，并给出「暂无记录」提示，不崩溃。

约束（P0 红线）：仅标准库 / 无 CDN 外链 / 无第三方图表库 / 无 emoji / 浅色主题 / utf-8-sig 读输入。

用法
----
    python render_dashboard.py --out dashboard.html --report
    python render_dashboard.py timetable.json --logbook ~/.schedule-planner/logbook.jsonl --out dashboard.html
"""

import argparse
import json
import os
import sys
from datetime import date, datetime, timedelta

_HERE = os.path.dirname(os.path.abspath(__file__))
PKG_ROOT = os.path.abspath(os.path.join(_HERE, "..", "..", ".."))
_USER_HOME = os.environ.get("USERPROFILE") or os.path.expanduser("~")
DEFAULT_LOGBOOK = os.path.join(_USER_HOME, ".schedule-planner", "logbook.jsonl")
DEFAULT_OUT_DIR = os.path.join(_USER_HOME, ".schedule-planner", "out")

SELFCHECK_COMMENT = ("v4-selfcheck: single-file offline HTML | no-cdn | no-external-link | "
                     "no-third-party-chart-lib | svg-css-handwritten | no-emoji | light-theme")

ATTRIBUTION = [
    ("none", "无偏差"), ("overload", "超载"), ("estimate", "估时偏差"),
    ("interrupted", "被打断"), ("motivation", "动力不足"), ("fact_error", "事实错误"),
]


def _safe_stdout():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def load_json(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def parse_date(s):
    return datetime.strptime(str(s).strip(), "%Y-%m-%d").date()


def esc(s):
    if s is None:
        return ""
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                  .replace('"', "&quot;"))


def assert_not_in_package(path):
    p = os.path.normcase(os.path.abspath(path))
    root = os.path.normcase(os.path.abspath(PKG_ROOT))
    if p == root or p.startswith(root + os.sep):
        raise SystemExit("[FAIL] 禁止写入包内目录（包内 data/ 为只读基线）：%s" % path)


def ensure_parent(path):
    d = os.path.dirname(os.path.abspath(path))
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)


# --------------------------------------------------------------------------- #
# 功劳档案读取
# --------------------------------------------------------------------------- #
def read_logbook(path):
    """返回 (记录列表, 统计字典)。文件不存在 / 为空 / 全坏行 均返回空列表，不抛异常。"""
    if not path or not os.path.isfile(path):
        return [], {"exists": False, "lines": 0, "bad": 0, "path": path}
    recs, bad = [], 0
    with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                bad += 1
                continue
            if isinstance(obj, dict):
                recs.append(obj)
            else:
                bad += 1
    total_lines = 0
    with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
        total_lines = sum(1 for x in f if x.strip())
    return recs, {"exists": True, "lines": total_lines, "bad": bad, "path": path}


def rec_date(r):
    for k in ("date", "logged_at"):
        v = r.get(k)
        if not v:
            continue
        try:
            return datetime.strptime(str(v)[:10], "%Y-%m-%d").date()
        except Exception:
            continue
    return None


def rec_int(r, key):
    try:
        return int(r.get(key) or 0)
    except Exception:
        return 0


def rec_min(r, key):
    """工时字段兜底（P1-1 修复后）。

    修复前：`return v if v else rec_int(r, "minutes")` —— 显式 planned_minutes=0 被
    `if v` 判 falsy，误回落 minutes，把零计划工时算成假完成率（如 60.0%），与
    logbook.py 的「—（无计划工时）」不一致 → 假绿（审计 P1-1）。

    最终修法（主理人复核）：判「缺失」必须看**原始键是否存在**，不能用 rec_int
    —— rec_int 是 int(r.get(key) or 0)，缺失与非法一律归 0、永不返回 None，
    用它判缺失会把「键缺失」误判成「显式 0」，反而打破与 logbook.py 的同口径
    （缺失 planned 的档案会被误显示成「—（无计划工时）」，而 logbook 侧按兜底
    算出真实完成率）。
    故：
      键缺失（r.get(key) is None）→ 回落 minutes，与 logbook.py 上游兜底幂等；
      键存在且为 0（显式零计划工时）→ 保留 0，交下游零分母守卫打「—（无计划工时）」；
      非法值（不可转 int）→ 回落 minutes。
    """
    raw = r.get(key)
    if raw is None:
        return rec_int(r, "minutes")
    try:
        return int(raw)
    except (TypeError, ValueError):
        return rec_int(r, "minutes")


def fmt_rate(x):
    """工时类比率格式化：None（无计划工时，维度缺失）显示「—（无计划工时）」，否则 '%.1f%%'。

    对应零分母纪律：Σplanned == 0 时返回 None（不是 0.0%）—— 与 logbook.py 的
    minutes_rate/effort_ratio 零分母返回 None 对齐。done == 0 但 Σplanned > 0 时
    返回真正的 0.0%，不被误判为「无计划工时」。
    """
    if x is None:
        return "—（无计划工时）"
    return "%.1f%%" % x


def compute_metrics(recs, today, term_start, weeks):
    m = {
        "total": len(recs), "done": 0, "partial": 0, "skipped": 0,
        "planned_min": 0, "actual_min": 0, "done_actual_min": 0, "done_planned_min": 0,
        "minutes_total": 0,
        "p0_total": 0, "p0_done": 0,
        "streak": 0, "attr": {k: 0 for k, _ in ATTRIBUTION},
        "fact_errors": [],
    }
    if not recs:
        m["rate_task"] = m["rate_p0"] = 0.0
        # 无记录即无计划工时（维度缺失）→ None，显示「—（无计划工时）」，不得回 0.0%
        m["rate_min"] = m["rate_input"] = None
        m["cur"] = m["prev"] = blank_week()
        m["cur_week"] = week_of(today, term_start, weeks)
        return m

    dates = set()
    for r in recs:
        st = str(r.get("status", "")).lower()
        if st == "done":
            m["done"] += 1
        elif st == "partial":
            m["partial"] += 1
        elif st == "skipped":
            m["skipped"] += 1
        pl = rec_min(r, "planned_minutes")
        am = rec_min(r, "actual_minutes")
        m["planned_min"] += pl
        m["actual_min"] += am
        m["minutes_total"] += rec_int(r, "minutes")
        if st == "done":
            m["done_actual_min"] += am
            m["done_planned_min"] += pl
        pri = str(r.get("priority", "")).upper()
        if pri == "P0":
            m["p0_total"] += 1
            if st == "done":
                m["p0_done"] += 1
        a = str(r.get("attribution", "none") or "none").lower()
        if a in m["attr"]:
            m["attr"][a] += 1
        if a == "fact_error":
            m["fact_errors"].append({
                "id": r.get("id", ""), "title": r.get("title", ""),
                "date": r.get("date", ""), "refs": r.get("fact_refs", []) or [],
            })
        d = rec_date(r)
        if d:
            dates.add(d)

    m["rate_task"] = (m["done"] / m["total"] * 100) if m["total"] else 0.0
    # 工时完成率 = Σ planned_minutes(done) / Σ planned_minutes(全部)  —— 计划加权口径
    # 不采用「实际/实际」或「实际/计划」：前者会因慢工虚高（300 分钟做完 90 分钟的计划
    # 会让完成率虚涨），后者分子分母不同源、可越过 100%。计划加权下「全部完成 == 100%」恒成立。
    # 零分母纪律：Σplanned == 0 → None（无计划工时），不得回 0.0%；
    # done == 0 但 Σplanned > 0 → 真正的 0.0%。两者必须区分。
    m["rate_min"] = (m["done_planned_min"] / m["planned_min"] * 100) if m["planned_min"] else None
    # 辅助指标：工时投入率 = Σ actual / Σ planned（>100% 即估时偏低，是估时偏差信号，非完成率）
    m["rate_input"] = (m["actual_min"] / m["planned_min"] * 100) if m["planned_min"] else None
    m["rate_p0"] = (m["p0_done"] / m["p0_total"] * 100) if m["p0_total"] else 0.0

    # 连击：从最近一条记录日期往前逐日回溯
    if dates:
        latest = max(dates)
        streak, cur = 0, latest
        while cur in dates:
            streak += 1
            cur -= timedelta(days=1)
        # 若最近记录距今超过 1 天，连击视为已中断
        if (today - latest).days > 1:
            streak = 0
        m["streak"] = streak
        m["latest"] = latest.isoformat()
    else:
        m["latest"] = ""

    cw = week_of(today, term_start, weeks)
    m["cur_week"] = cw
    m["cur"] = week_stats(recs, term_start, cw)
    m["prev"] = week_stats(recs, term_start, cw - 1)
    return m


def blank_week():
    return {"records": 0, "done": 0, "planned": 0, "actual": 0, "rate": 0.0}


def week_of(d, term_start, weeks):
    delta = (d - term_start).days
    if delta < 0 or delta >= weeks * 7:
        return 1
    return delta // 7 + 1


def week_stats(recs, term_start, w):
    if w < 1:
        return blank_week()
    a = term_start + timedelta(days=(w - 1) * 7)
    b = a + timedelta(days=6)
    sel = [r for r in recs if (rec_date(r) and a <= rec_date(r) <= b)]
    if not sel:
        return blank_week()
    done = sum(1 for r in sel if str(r.get("status", "")).lower() == "done")
    planned = sum(rec_min(r, "planned_minutes") for r in sel)
    actual = sum(rec_min(r, "actual_minutes") for r in sel)
    return {"records": len(sel), "done": done, "planned": planned, "actual": actual,
            "rate": (done / len(sel) * 100) if sel else 0.0}


# --------------------------------------------------------------------------- #
# HTML
# --------------------------------------------------------------------------- #
CSS = """
:root{
  --bg:#f6f7f9; --panel:#fff; --ink:#1f2328; --muted:#5b6470; --faint:#8b949e;
  --line:#e3e6ea; --line2:#eef0f3;
  --accent:#2f6feb; --accent-soft:#e8f0fe; --accent-ink:#1b4bb8;
  --warn:#8a5300; --warn-bg:#fdf3e2; --warn-line:#f0d9ac;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font-family:"Segoe UI","Microsoft YaHei","PingFang SC",system-ui,sans-serif;font-size:14px;line-height:1.6}
.wrap{max-width:1080px;margin:0 auto;padding:24px 20px 56px}
header.hd{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:18px 20px;margin-bottom:16px}
h1{margin:0 0 6px;font-size:19px;font-weight:650}
.sub{color:var(--muted);font-size:13px}
.meta{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px}
.chip{display:inline-flex;gap:6px;background:var(--line2);border:1px solid var(--line);color:var(--muted);
  border-radius:999px;padding:3px 11px;font-size:12px}
.chip b{color:var(--ink);font-weight:600}
.chip.cur{background:var(--accent-soft);border-color:#c7dbfb;color:var(--accent-ink)}
.chip.warn{background:var(--warn-bg);border-color:var(--warn-line);color:var(--warn)}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:16px}
.notice{background:var(--warn-bg);border:1px solid var(--warn-line);color:var(--warn);
  border-radius:10px;padding:12px 16px;margin-bottom:16px;font-size:13px}
.notice.soft{background:#eef2f7;border:1px solid var(--line);color:var(--muted)}
.rings{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
@media(max-width:760px){.rings{grid-template-columns:1fr}}
.ring{text-align:center;padding:8px 4px}
.ring .cap{font-weight:650;margin-bottom:2px}
.ring .note{color:var(--faint);font-size:12px;margin-top:4px}
.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:16px}
@media(max-width:760px){.cards{grid-template-columns:1fr}}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px 16px}
.card .k{color:var(--muted);font-size:12px}
.card .v{font-size:26px;font-weight:650;font-variant-numeric:tabular-nums;line-height:1.2}
.card .d{font-size:12px;color:var(--faint)}
.up{color:#1a7f52}.down{color:#b42318}
h2.sec{font-size:15px;margin:22px 0 10px;font-weight:650}
table{width:100%;border-collapse:collapse;background:var(--panel);border:1px solid var(--line);
  border-radius:10px;overflow:hidden;font-size:13px}
th,td{padding:8px 12px;border-bottom:1px solid var(--line2);text-align:left;font-variant-numeric:tabular-nums}
th{background:#fafbfc;color:var(--muted);font-weight:600;font-size:12px}
tr:last-child td{border-bottom:0}
.bar-row{display:grid;grid-template-columns:96px 1fr 62px;gap:10px;align-items:center;margin-bottom:7px;font-size:13px}
.bar{height:12px;background:var(--line2);border-radius:3px;overflow:hidden}
.bar i{display:block;height:100%;background:var(--accent)}
.bar i.hot{background:#b42318}
.barv{color:var(--muted);font-size:12px;text-align:right;font-variant-numeric:tabular-nums}
.empty{color:var(--faint);font-size:13px}
footer.ft{margin-top:16px;color:var(--faint);font-size:12px}
ul.fe{margin:0;padding-left:22px;font-size:13px;color:var(--muted)}
"""


def ring_svg(pct, color="#2f6feb"):
    if pct is None:
        # 无计划工时（维度缺失）：环为空，中心显示「—（无计划工时）」，不得显示 0.0%
        pct_show, center = 0.0, "—（无计划工时）"
    else:
        pct_show, center = pct, "%.0f%%" % pct
    r = 54.0
    c = 2 * 3.141592653589793 * r
    on = max(0.0, min(float(pct_show), 100.0)) / 100.0 * c
    return ('<svg viewBox="0 0 140 140" width="140" height="140" role="img" '
            'aria-label="完成率 %s">'
            '<circle cx="70" cy="70" r="54" fill="none" stroke="#eef0f3" stroke-width="14"/>'
            '<circle cx="70" cy="70" r="54" fill="none" stroke="%s" stroke-width="14" '
            'stroke-dasharray="%.2f %.2f" transform="rotate(-90 70 70)"/>'
            '<text x="70" y="72" text-anchor="middle" font-size="20" font-weight="650" '
            'fill="#1f2328" font-family="Segoe UI,Microsoft YaHei,sans-serif">%s</text>'
            '</svg>' % (center, color, on, c, center))


def build_html(m, ctx):
    notice = ""
    if not ctx["lb"]["exists"]:
        notice = ('<div class="notice">暂无记录：功劳档案 %s 不存在。'
                  '任务数 / P0 按 0%% 显示，工时类（无计划工时）按「—（无计划工时）」显示 —— '
                  '先执行 <b>logbook.py add</b> 写入完成记录，再看这里。</div>'
                  % esc(ctx["lb"]["path"] or "(未指定)"))
    elif m["total"] == 0:
        notice = ('<div class="notice">暂无记录：功劳档案 %s 存在但没有有效记录（%d 行，其中 %d 行解析失败）。'
                  '任务数 / P0 按 0%% 显示，工时类（无计划工时）按「—（无计划工时）」显示。</div>'
                  % (esc(ctx["lb"]["path"]), ctx["lb"]["lines"], ctx["lb"]["bad"]))

    # partial 提示：partial 记录无 progress 字段，按 0 计入完成率（不插值、不取 0.5）
    phint = ""
    if m["partial"]:
        phint = ('<div class="notice soft">partial %d 条未计完成（无 progress 字段，按 0 计入）'
                 '—— 工时完成率仅统计 done 的计划工时。</div>' % m["partial"])

    rings = "".join(
        '<div class="ring"><div class="cap">%s</div>%s<div class="note">%s</div></div>'
        % (cap, ring_svg(val, color), note)
        for cap, val, color, note in [
            ("任务数完成率", m["rate_task"], "#2f6feb",
             "%d / %d 条已完成" % (m["done"], m["total"])),
            ("工时完成率", m["rate_min"], "#1a7f52",
             "已完成计划 %d / 总计划 %d 分钟<br>实际投入 %d 分钟（投入率 %s）"
             % (m["done_planned_min"], m["planned_min"], m["actual_min"],
                fmt_rate(m["rate_input"]))),
            ("P0 完成率", m["rate_p0"], "#8a5300",
             "%d / %d 项 P0" % (m["p0_done"], m["p0_total"])),
        ])

    def delta(a, b, unit=""):
        d = a - b
        if d == 0:
            return '<span class="d">与上周持平</span>'
        cls = "up" if d > 0 else "down"
        return '<span class="d"><b class="%s">%s%d%s</b> 较上周</span>' % (
            cls, "+" if d > 0 else "", d, unit)

    cards = (
        '<div class="card"><div class="k">连续打卡</div><div class="v">%d 天</div>'
        '<div class="d">%s</div></div>'
        '<div class="card"><div class="k">本周完成</div><div class="v">%d / %d</div>%s</div>'
        '<div class="card"><div class="k">本周实际工时</div><div class="v">%d 分</div>%s</div>'
        % (m["streak"],
           ("最近记录 %s" % m["latest"]) if m.get("latest") else "暂无记录",
           m["cur"]["done"], m["cur"]["records"],
           delta(m["cur"]["done"], m["prev"]["done"]),
           m["cur"]["actual"], delta(m["cur"]["actual"], m["prev"]["actual"], " 分")))

    cmp_tbl = (
        "<table><thead><tr><th>指标</th><th>本周（第 %d 周）</th><th>上周（第 %d 周）</th><th>变化</th></tr></thead>"
        "<tbody>"
        "<tr><td>记录条数</td><td>%d</td><td>%d</td><td>%s</td></tr>"
        "<tr><td>完成条数</td><td>%d</td><td>%d</td><td>%s</td></tr>"
        "<tr><td>完成率</td><td>%.0f%%</td><td>%.0f%%</td><td>%s</td></tr>"
        "<tr><td>计划工时（分）</td><td>%d</td><td>%d</td><td>%s</td></tr>"
        "<tr><td>实际工时（分）</td><td>%d</td><td>%d</td><td>%s</td></tr>"
        "</tbody></table>"
        % (m["cur_week"], max(m["cur_week"] - 1, 1),
           m["cur"]["records"], m["prev"]["records"], delta(m["cur"]["records"], m["prev"]["records"]),
           m["cur"]["done"], m["prev"]["done"], delta(m["cur"]["done"], m["prev"]["done"]),
           m["cur"]["rate"], m["prev"]["rate"], delta(m["cur"]["rate"], m["prev"]["rate"], "%"),
           m["cur"]["planned"], m["prev"]["planned"], delta(m["cur"]["planned"], m["prev"]["planned"]),
           m["cur"]["actual"], m["prev"]["actual"], delta(m["cur"]["actual"], m["prev"]["actual"])))

    maxattr = max([m["attr"][k] for k, _ in ATTRIBUTION] + [1])
    bars = "".join(
        '<div class="bar-row"><span>%s</span>'
        '<span class="bar"><i class="%s" style="width:%.1f%%"></i></span>'
        '<span class="barv">%d 条</span></div>'
        % (label, "hot" if key == "fact_error" else "", m["attr"][key] / maxattr * 100, m["attr"][key])
        for key, label in ATTRIBUTION)

    fe = ""
    if m["fact_errors"]:
        fe = ('<h2 class="sec">事实错误项（须回退 fact-verifier 重核）</h2>'
              '<div class="panel"><ul class="fe">%s</ul></div>'
              % "".join("<li>%s｜%s｜%s｜事实编号 %s</li>"
                        % (esc(x["date"]), esc(x["title"]), esc(x["id"]),
                           esc(",".join(x["refs"]) or "-"))
                        for x in m["fact_errors"][:20]))

    return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="v4-current-week" content="%(cw)d">
<title>完成度仪表盘 · 第 %(cw)d 周</title>
<!-- %(sc)s -->
<style>%(css)s</style>
</head>
<body data-v4-view="dashboard" data-v4-current-week="%(cw)d" data-v4-term-start="%(ts)s">
<div class="wrap">
  <header class="hd">
    <h1>完成度仪表盘 · 第 %(cw)d 周</h1>
    <div class="sub">三口径完成率（任务数 / 工时 / P0）+ 连击打卡 + 本周 vs 上周。环形图为手写 SVG，无第三方图表库。</div>
    <div class="meta">
      <span class="chip">学期起点 <b>%(ts)s</b></span>
      <span class="chip cur">当前 <b>第 %(cw)d 周</b></span>
      <span class="chip">功劳档案 <b>%(total)d</b> 条</span>
      <span class="chip">连击 <b>%(streak)d</b> 天</span>
    </div>
  </header>

  %(notice)s

  <div class="panel"><div class="rings">%(rings)s</div></div>
  %(phint)s
  <div class="cards">%(cards)s</div>

  <h2 class="sec">本周 vs 上周</h2>
  %(cmp)s

  <h2 class="sec">偏差归因分布</h2>
  <div class="panel">%(bars)s</div>

  %(fe)s

  <footer class="ft">
    数据来源：功劳档案 %(src)s（用户目录，包内只读）｜ 生成脚本 render_dashboard.py ｜
    本文件无外链、无 CDN、无第三方库，全部样式内联。
  </footer>
</div>
</body>
</html>
""" % {
        "cw": m["cur_week"], "ts": ctx["term_start"].isoformat(), "total": m["total"],
        "streak": m["streak"], "notice": notice, "rings": rings, "cards": cards,
        "phint": phint,
        "cmp": cmp_tbl, "bars": bars, "fe": fe, "css": CSS, "sc": SELFCHECK_COMMENT,
        "src": esc(ctx["lb"]["path"] or "(未指定)"),
    }


def main():
    _safe_stdout()
    ap = argparse.ArgumentParser(description="生成完成度仪表盘 HTML（N3）")
    ap.add_argument("input", nargs="?", default=None, help="课表/日程 JSON（可选，用于学期起点）")
    ap.add_argument("--out", default=None, help="输出 HTML 路径（默认用户目录 out/dashboard.html）")
    ap.add_argument("--logbook", default=DEFAULT_LOGBOOK, help="功劳档案 JSONL 路径")
    ap.add_argument("--term-start", default=None, help="学期起点（YYYY-MM-DD）")
    ap.add_argument("--weeks", type=int, default=20, help="学期总周数")
    ap.add_argument("--today", default=None, help="覆盖「今天」（YYYY-MM-DD）")
    ap.add_argument("--report", action="store_true", help="打印详细自检报告")
    args = ap.parse_args()

    term_start = None
    if args.term_start:
        term_start = parse_date(args.term_start)
    elif args.input and os.path.isfile(args.input):
        try:
            term_start = parse_date(load_json(args.input).get("term_start", ""))
        except Exception:
            term_start = None
    if term_start is None:
        term_start = parse_date("2026-09-07")

    weeks = int(args.weeks or 20)
    today = parse_date(args.today) if args.today else date.today()

    recs, lb = read_logbook(args.logbook)
    m = compute_metrics(recs, today, term_start, weeks)

    out = args.out or os.path.join(DEFAULT_OUT_DIR, "dashboard.html")
    assert_not_in_package(out)
    ensure_parent(out)
    html = build_html(m, {"lb": lb, "term_start": term_start})
    with open(out, "w", encoding="utf-8", newline="") as f:
        f.write(html)

    print("[OK] 完成度仪表盘已生成")
    print("    产物路径 : %s" % os.path.abspath(out))
    print("    字节数   : %d" % os.path.getsize(out))
    print("    功劳档案 : %s（存在=%s，%d 行，%d 行解析失败）"
          % (args.logbook, lb["exists"], lb["lines"], lb["bad"]))
    print("    记录条数 : %d（完成 %d / 部分 %d / 跳过 %d）"
          % (m["total"], m["done"], m["partial"], m["skipped"]))
    if m["partial"]:
        print("    部分记录 : %d 条 partial 未计完成（无 progress 字段，按 0 计入）" % m["partial"])
    print("    完成率   : 任务数 %.1f%% ｜ 工时 %s ｜ P0 %.1f%% ｜ 工时投入率 %s"
          % (m["rate_task"], fmt_rate(m["rate_min"]), m["rate_p0"], fmt_rate(m["rate_input"])))
    print("    总投入   : Σ记录分钟 %d 分（Σactual_minutes %d 分）—— 与 logbook.py minutes_total 对齐"
          % (m["minutes_total"], m["actual_min"]))
    print("    连击打卡 : %d 天" % m["streak"])
    print("    本周     : 第 %d 周 %d 条 / 完成 %d ｜ 上周 %d 条 / 完成 %d"
          % (m["cur_week"], m["cur"]["records"], m["cur"]["done"],
             m["prev"]["records"], m["prev"]["done"]))
    if args.report:
        print("    ---- 自检标记 ----")
        for mark in ('data-v4-current-week="%d"' % m["cur_week"], "stroke-dasharray",
                     SELFCHECK_COMMENT.split("|")[0].strip()):
            print("      [%s] %s" % ("OK" if mark in html else "FAIL", mark))
    return 0


if __name__ == "__main__":
    sys.exit(main())
