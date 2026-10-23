#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
render_week_view.py — N3 周视图：单周横向时间轴（周一至周日 × 时间），单文件离线 HTML。

设计目的
--------
「可视化有没有体现」的第一张图：把一周七天的安排铺在一条横向时间轴上，
让人一眼看出哪天空、哪天挤、哪两段之间要跨楼转场。

能力
----
  * 横向时间轴：行 = 周一至周日，列 = 时间（自 06:00 起，按事件自动扩展到 22:30）
  * 稳定区 / 弹性区用不同色块：
      - 稳定区 = 每周固定（week_rule.type == weekly），实心强调色
      - 弹性区 = 单周 / 双周 / 指定区间 / 指定周次，浅色 + 虚线描边
      - 事件可用 "zone": "stable" | "elastic" 显式覆盖
  * 转场连线：同日相邻两项之间画线，按间隔与是否跨楼判定三级风险
      - 临界（跨楼且间隔 <= 15 分钟）→ 红色实线
      - 紧张（跨楼且间隔 <= 30 分钟）→ 琥珀色虚线
      - 宽松 → 中性灰虚线
  * 顶部标注本周内的法定节假日与调休上班日

约束（P0 红线）：仅标准库 / 无 CDN 外链 / 无第三方图表库 / 无 emoji / 浅色主题 / utf-8-sig 读输入。

用法
----
    python render_week_view.py timetable.json --out week-view.html
    python render_week_view.py timetable.json --week 7 --report
"""

import argparse
import json
import os
import sys
from datetime import date, datetime, timedelta

_HERE = os.path.dirname(os.path.abspath(__file__))
PKG_ROOT = os.path.abspath(os.path.join(_HERE, "..", "..", ".."))
DEFAULT_HOLIDAY_FILE = os.path.join(PKG_ROOT, "data", "holidays-2026.json")
_USER_HOME = os.environ.get("USERPROFILE") or os.path.expanduser("~")
DEFAULT_OUT_DIR = os.path.join(_USER_HOME, ".schedule-planner", "out")

DAY_NAME = {1: "周一", 2: "周二", 3: "周三", 4: "周四", 5: "周五", 6: "周六", 7: "周日"}
RULE_LABEL = {"weekly": "每周", "odd": "单周", "even": "双周",
              "range": "指定区间", "custom_weeks": "指定周次"}
SELFCHECK_COMMENT = ("v4-selfcheck: single-file offline HTML | no-cdn | no-external-link | "
                     "no-third-party-chart-lib | svg-css-handwritten | no-emoji | light-theme")

CRIT_MIN = 15     # 临界转场阈值（分钟）
TIGHT_MIN = 30    # 紧张转场阈值（分钟）


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


def to_min(hhmm):
    hh, mm = str(hhmm).split(":")
    return int(hh) * 60 + int(mm)


def fmt_hm(m):
    return "%02d:%02d" % (m // 60, m % 60)


def weeks_of(rule, total_weeks):
    rule = rule or {}
    rtype = rule.get("type", "weekly")
    if rtype == "range":
        sw, ew = int(rule["start_week"]), int(rule["end_week"])
        gen = list(range(sw, ew + 1))
        keep = set(gen)
    elif rtype == "custom_weeks":
        ws = sorted(int(x) for x in rule["weeks"])
        gen = list(range(ws[0], ws[-1] + 1))
        keep = set(ws)
    elif rtype in ("odd", "even"):
        base = int(rule.get("start_week", 1 if rtype == "odd" else 2))
        if rtype == "odd" and base % 2 == 0:
            base += 1
        if rtype == "even" and base % 2 == 1:
            base += 1
        n = int(rule.get("count", 8))
        gen = [base + 2 * i for i in range(max(n, 1))]
        keep = set(gen)
    else:
        base = int(rule.get("start_week", 1))
        n = int(rule.get("count", 16))
        gen = [base + i for i in range(max(n, 1))]
        keep = set(gen)
    keep -= set(int(x) for x in rule.get("exclude_weeks", []))
    return sorted(w for w in gen if 1 <= w <= total_weeks and w in keep), set(rule.get("exclude_dates", []) or [])


def _span(start, end):
    if not start or not end:
        return []
    d0, d1 = parse_date(start), parse_date(end)
    out, cur = [], d0
    while cur <= d1:
        out.append(cur.isoformat())
        cur += timedelta(days=1)
    return out


def load_holidays(path):
    if not path or not os.path.isfile(path):
        return {
            "2026-09-25": {"id": "H-S-01", "name": "中秋节"}, "2026-09-26": {"id": "H-S-01", "name": "中秋节"},
            "2026-09-27": {"id": "H-S-01", "name": "中秋节"}, "2026-10-01": {"id": "H-S-02", "name": "国庆节"},
            "2026-10-02": {"id": "H-S-02", "name": "国庆节"}, "2026-10-03": {"id": "H-S-02", "name": "国庆节"},
            "2026-10-04": {"id": "H-S-02", "name": "国庆节"}, "2026-10-05": {"id": "H-S-02", "name": "国庆节"},
            "2026-10-06": {"id": "H-S-02", "name": "国庆节"}, "2026-10-07": {"id": "H-S-02", "name": "国庆节"},
        }, {
            "2026-09-20": {"id": "HM-S-01", "name": "国庆调休上班/补课"},
            "2026-10-10": {"id": "HM-S-02", "name": "国庆调休上班/补课"},
        }, {"source_kind": "sample", "source_label": "内置样例（data/holidays-2026.json 尚未就绪）",
            "entries_count": 4}
    raw = load_json(path)
    hol, mk = {}, {}
    for e in raw.get("entries", []):
        eid, name = e.get("id", ""), e.get("name", "")
        days = [e["date"]] if e.get("date") else _span(e.get("start"), e.get("end"))
        if e.get("type") == "make_up_workday":
            for x in days:
                mk[x] = {"id": eid, "name": name}
            continue
        for x in days:
            hol[x] = {"id": eid, "name": name,
                      "source_url": e.get("source_url", ""),
                      "confidence": e.get("confidence", ""),
                      "status": e.get("status", "")}
        for mu in (e.get("make_up_workdays") or []):
            mk[mu["date"]] = {"id": eid, "name": mu.get("note") or (name + " 调休")}
    return hol, mk, {"source_kind": "file",
                     "source_label": "%s（%s）" % (raw.get("source", {}).get("document_id", "data 文件"),
                                                  raw.get("source", {}).get("authority", "")),
                     "entries_count": len(raw.get("entries", [])),
                     "verified": bool(raw.get("source", {}).get("originally_verified", False))}


CSS = """
:root{
  --bg:#f6f7f9; --panel:#fff; --ink:#1f2328; --muted:#5b6470; --faint:#8b949e;
  --line:#e3e6ea; --line2:#eef0f3;
  --accent:#2f6feb; --accent-soft:#e8f0fe; --accent-ink:#1b4bb8;
  --hol-bg:#fdeceb; --hol-ink:#a5231b; --hol-line:#f3c7c2;
  --mk-bg:#fdf3e2; --mk-ink:#8a5300; --mk-line:#f0d9ac;
  --crit:#c0392b; --tight:#b7791f;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font-family:"Segoe UI","Microsoft YaHei","PingFang SC",system-ui,sans-serif;font-size:14px;line-height:1.6}
.wrap{max-width:1180px;margin:0 auto;padding:24px 20px 56px}
header.hd{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:18px 20px;margin-bottom:16px}
h1{margin:0 0 6px;font-size:19px;font-weight:650}
.sub{color:var(--muted);font-size:13px}
.meta{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px}
.chip{display:inline-flex;gap:6px;background:var(--line2);border:1px solid var(--line);color:var(--muted);
  border-radius:999px;padding:3px 11px;font-size:12px}
.chip b{color:var(--ink);font-weight:600}
.chip.cur{background:var(--accent-soft);border-color:#c7dbfb;color:var(--accent-ink)}
.chip.hol{background:var(--hol-bg);border-color:var(--hol-line);color:var(--hol-ink)}
.chip.mk{background:var(--mk-bg);border-color:var(--mk-line);color:var(--mk-ink)}
.chip.warn{background:var(--mk-bg);border-color:var(--mk-line);color:var(--mk-ink)}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:10px;overflow:hidden}
.axis{display:grid;grid-template-columns:104px 1fr;border-bottom:1px solid var(--line);background:#fafbfc}
.axis .pad{}
.axis .ticks{position:relative;height:30px}
.tick{position:absolute;top:7px;transform:translateX(-50%);color:var(--faint);font-size:11px;
  font-variant-numeric:tabular-nums;white-space:nowrap}
.row{display:grid;grid-template-columns:104px 1fr;border-bottom:1px solid var(--line2)}
.row:last-child{border-bottom:0}
.row.is-today{background:#f4f8ff}
.row.is-holiday{background:var(--hol-bg)}
.row.is-makeup{background:var(--mk-bg)}
.dl{padding:10px 12px;border-right:1px solid var(--line2)}
.dl .n{font-weight:650}
.dl .d{color:var(--faint);font-size:12px;font-variant-numeric:tabular-nums}
.dl .f{font-size:11px;font-weight:600}
.track{position:relative;height:58px;margin:6px 10px 6px 0}
.gline{position:absolute;top:0;bottom:0;width:1px;background:var(--line2)}
.blk{position:absolute;top:8px;height:42px;border-radius:6px;padding:4px 7px;overflow:hidden;
  font-size:12px;line-height:1.35;color:#fff;background:var(--accent);border:1px solid var(--accent);
  transition:filter .12s ease-out}
.blk:hover{filter:brightness(.94)}
.blk.elastic{background:#dfe5ee;color:#2b3440;border:1px dashed #9aa4b0}
.blk .bt{font-weight:650;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;display:block}
.blk .bm{opacity:.9;font-variant-numeric:tabular-nums;white-space:nowrap}
.links{position:absolute;left:0;top:0;width:100%;height:58px;pointer-events:none}
.lab{position:absolute;top:2px;transform:translateX(-50%);font-size:10px;white-space:nowrap;
  padding:0 4px;border-radius:3px;background:#fff;border:1px solid var(--line);color:var(--muted)}
.lab.crit{border-color:var(--crit);color:var(--crit);font-weight:650}
.lab.tight{border-color:var(--tight);color:var(--tight)}
.lg{display:flex;flex-wrap:wrap;gap:16px;padding:10px 14px;border-top:1px solid var(--line2);
  background:#fafbfc;color:var(--muted);font-size:12px;align-items:center}
.sw{display:inline-block;width:14px;height:11px;border-radius:3px;vertical-align:-1px;margin-right:5px}
.ln{display:inline-block;width:22px;height:0;border-top-width:2px;border-top-style:solid;vertical-align:3px;margin-right:5px}
h2.sec{font-size:15px;margin:22px 0 10px;font-weight:650}
table{width:100%;border-collapse:collapse;background:var(--panel);border:1px solid var(--line);
  border-radius:10px;overflow:hidden;font-size:13px}
th,td{padding:8px 12px;border-bottom:1px solid var(--line2);text-align:left}
th{background:#fafbfc;color:var(--muted);font-weight:600;font-size:12px}
tr:last-child td{border-bottom:0}
.tag{border-radius:4px;padding:1px 6px;font-size:11px;font-weight:600}
.tag.crit{background:#fbdedb;color:var(--crit)}
.tag.tight{background:#f9edcf;color:var(--tight)}
.tag.ok{background:var(--line2);color:var(--muted)}
.empty{color:var(--faint);padding:14px}
footer.ft{margin-top:16px;color:var(--faint);font-size:12px}
"""


def build_html(ctx):
    ts, week, weeks = ctx["term_start"], ctx["week"], ctx["weeks"]
    hol, mk, hmeta = ctx["hol"], ctx["mk"], ctx["hmeta"]
    rows = ctx["rows"]          # 7 天，每天 {"date","items":[...]}
    t0, t1 = ctx["t0"], ctx["t1"]
    span = max(t1 - t0, 1)
    today_iso = ctx["today"].isoformat()

    # 顶部时间刻度
    ticks = []
    start_h = (t0 // 60) if t0 % 60 == 0 else (t0 // 60)
    m = t0
    while m <= t1:
        pct = (m - t0) / span * 100
        ticks.append('<span class="tick" style="left:%.3f%%">%s</span>' % (pct, fmt_hm(m)))
        m += 120
    axis = ('<div class="axis"><div class="pad"></div><div class="ticks">%s</div></div>'
            % "".join(ticks))

    row_html, transitions = [], []
    for r in rows:
        d = r["date"]
        iso = d.isoformat()
        cls = ["row"]
        flag = ""
        if iso in hol:
            cls.append("is-holiday")
            flag = '<div class="f" style="color:var(--hol-ink)">%s</div>' % esc(hol[iso]["name"])
        elif iso in mk:
            cls.append("is-makeup")
            flag = '<div class="f" style="color:var(--mk-ink)">调休上班</div>'
        if iso == today_iso:
            cls.append("is-today")

        glines = []
        m = t0
        while m <= t1:
            glines.append('<div class="gline" style="left:%.3f%%"></div>' % ((m - t0) / span * 100))
            m += 120

        blocks, svg, labels = [], [], []
        items = r["items"]
        for i, it in enumerate(items):
            s, e = to_min(it["start"]), to_min(it["end"])
            left = (s - t0) / span * 100
            width = max((e - s) / span * 100, 1.2)
            zone = it.get("zone") or ("stable" if it.get("ruleType", "weekly") == "weekly" else "elastic")
            blocks.append(
                '<div class="blk %s" style="left:%.3f%%;width:%.3f%%" title="%s %s-%s %s">'
                '<span class="bt">%s</span><span class="bm">%s-%s</span></div>'
                % ("stable" if zone == "stable" else "elastic", left, width,
                   esc(it["title"]), it["start"], it["end"], esc(it.get("loc", "")),
                   esc(it["title"]), it["start"], it["end"]))
            if i + 1 < len(items):
                nxt = items[i + 1]
                gap = to_min(nxt["start"]) - e
                cross = (it.get("loc", "") != nxt.get("loc", "")) and bool(it.get("loc")) and bool(nxt.get("loc"))
                if cross and gap <= CRIT_MIN:
                    lvl, color, dash = "crit", "var(--crit)", "0"
                elif cross and gap <= TIGHT_MIN:
                    lvl, color, dash = "tight", "var(--tight)", "4 3"
                else:
                    lvl, color, dash = "ok", "#b9c0c9", "4 4"
                x1 = (e - t0) / span * 1000
                x2 = (to_min(nxt["start"]) - t0) / span * 1000
                svg.append(
                    '<line x1="%.2f" y1="29" x2="%.2f" y2="29" stroke="%s" stroke-width="2" '
                    'stroke-dasharray="%s" vector-effect="non-scaling-stroke"/>' % (x1, x2, color, dash))
                mid = (left + width + (to_min(nxt["start"]) - t0) / span * 100) / 2
                labels.append('<span class="lab %s" style="left:%.3f%%">%s%s</span>'
                              % (lvl if lvl != "ok" else "", mid,
                                 ("跨楼 " if cross else ""), ("%d 分" % gap)))
                transitions.append({
                    "date": iso, "day": DAY_NAME[d.isoweekday()],
                    "a": it["title"], "b": nxt["title"],
                    "from": it.get("loc", ""), "to": nxt.get("loc", ""),
                    "gap": gap, "level": lvl, "cross": cross,
                })

        row_html.append(
            '<div class="row %s"><div class="dl"><div class="n">%s</div>'
            '<div class="d">%s</div>%s</div>'
            '<div class="track">%s'
            '<svg class="links" viewBox="0 0 1000 58" preserveAspectRatio="none">%s</svg>'
            '%s%s</div></div>'
            % (" ".join(cls), DAY_NAME[d.isoweekday()], d.strftime("%m-%d"), flag,
               "".join(glines), "".join(svg), "".join(labels), "".join(blocks)))

    # 转场清单表
    if transitions:
        trs = []
        for t in transitions:
            lvl_cn = {"crit": "临界", "tight": "紧张", "ok": "宽松"}[t["level"]]
            trs.append(
                "<tr><td>%s %s</td><td>%s</td><td>%s</td><td>%s → %s</td><td>%d 分钟</td>"
                "<td><span class=\"tag %s\">%s</span></td></tr>"
                % (t["day"], t["date"][5:], esc(t["a"]), esc(t["b"]),
                   esc(t["from"] or "-"), esc(t["to"] or "-"), t["gap"],
                   t["level"], lvl_cn))
        tbl = ("<h2 class=\"sec\">转场清单（同日相邻两项）</h2>"
               "<table><thead><tr><th>日期</th><th>前一项</th><th>后一项</th><th>地点</th>"
               "<th>间隔</th><th>风险</th></tr></thead><tbody>%s</tbody></table>" % "".join(trs))
    else:
        tbl = '<h2 class="sec">转场清单</h2><div class="panel"><div class="empty">本周没有相邻安排，无需转场。</div></div>'

    n_crit = sum(1 for t in transitions if t["level"] == "crit")
    n_tight = sum(1 for t in transitions if t["level"] == "tight")
    n_stable = sum(1 for r in rows for it in r["items"]
                   if (it.get("zone") or ("stable" if it.get("ruleType", "weekly") == "weekly" else "elastic")) == "stable")
    n_elastic = sum(1 for r in rows for it in r["items"]
                    if (it.get("zone") or ("stable" if it.get("ruleType", "weekly") == "weekly" else "elastic")) == "elastic")

    if hmeta["source_kind"] == "sample":
        warn = '<span class="chip warn">节假日为内置样例数据，非官宣基线</span>'
    elif not hmeta.get("verified", True):
        warn = ('<span class="chip warn">节假日数据 originally_verified=false：'
                '未逐条核验原文，正式使用前须以 gov.cn 原文为准</span>')
    else:
        warn = ""

    return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="v4-week" content="%(week)d">
<title>周视图 · 第 %(week)d 周</title>
<!-- %(sc)s -->
<style>%(css)s</style>
</head>
<body data-v4-view="week-view" data-v4-week="%(week)d" data-v4-term-start="%(ts)s">
<div class="wrap">
  <header class="hd">
    <h1>周视图 · 第 %(week)d 周（%(range)s）</h1>
    <div class="sub">横向时间轴：行 = 周一至周日，列 = 时间。稳定区 / 弹性区分区着色，相邻项之间标注转场风险。</div>
    <div class="meta">
      <span class="chip">学期起点 <b>%(ts)s</b></span>
      <span class="chip cur">第 <b>%(week)d</b> 周 / 共 %(weeks)d 周</span>
      <span class="chip">稳定区 <b>%(ns)d</b> 项</span>
      <span class="chip">弹性区 <b>%(ne)d</b> 项</span>
      <span class="chip">临界转场 <b>%(nc)d</b></span>
      <span class="chip">紧张转场 <b>%(nt)d</b></span>
      %(warn)s
    </div>
  </header>

  <div class="panel">
    %(axis)s
    %(rows)s
    <div class="lg">
      <span><i class="sw" style="background:#2f6feb;border:1px solid #2f6feb"></i>稳定区（每周固定）</span>
      <span><i class="sw" style="background:#dfe5ee;border:1px dashed #9aa4b0"></i>弹性区（单双周 / 指定周次）</span>
      <span><i class="ln" style="border-top-color:#c0392b"></i>临界转场（跨楼 ≤15 分钟）</span>
      <span><i class="ln" style="border-top-color:#b7791f;border-top-style:dashed"></i>紧张转场（跨楼 ≤30 分钟）</span>
      <span><i class="ln" style="border-top-color:#b9c0c9;border-top-style:dashed"></i>宽松</span>
    </div>
  </div>

  %(tbl)s

  <footer class="ft">
    节假日来源 %(hsrc)s ｜ 课表 %(insrc)s ｜ 生成脚本 render_week_view.py ｜
    本文件无外链、无 CDN、无第三方库，全部样式内联。
  </footer>
</div>
</body>
</html>
""" % {
        "week": week, "weeks": weeks, "ts": ts.isoformat(),
        "range": ctx["range_label"], "axis": axis, "rows": "".join(row_html),
        "tbl": tbl, "ns": n_stable, "ne": n_elastic, "nc": n_crit, "nt": n_tight,
        "warn": warn, "css": CSS, "sc": SELFCHECK_COMMENT,
        "hsrc": esc(hmeta["source_label"]), "insrc": esc(ctx["input_path"]),
    }


def main():
    _safe_stdout()
    ap = argparse.ArgumentParser(description="生成单周横向时间轴 HTML（N3 周视图）")
    ap.add_argument("input", help="课表/日程 JSON 文件路径")
    ap.add_argument("--out", default=None, help="输出 HTML 路径（默认用户目录 out/week-view.html）")
    ap.add_argument("--term-start", default=None, help="覆盖 term_start")
    ap.add_argument("--weeks", type=int, default=20, help="学期总周数")
    ap.add_argument("--week", type=int, default=None, help="目标周次，默认取当前周")
    ap.add_argument("--today", default=None, help="覆盖「今天」（YYYY-MM-DD）")
    ap.add_argument("--holidays", default=DEFAULT_HOLIDAY_FILE, help="节假日数据文件路径")
    ap.add_argument("--report", action="store_true", help="打印详细自检报告")
    args = ap.parse_args()

    data = load_json(args.input)
    ts = parse_date(args.term_start or data.get("term_start") or "2026-09-07")
    weeks = int(args.weeks or data.get("weeks") or 20)
    today = parse_date(args.today) if args.today else date.today()

    if args.week:
        week = int(args.week)
    else:
        delta = (today - ts).days
        week = 1 if (delta < 0 or delta >= weeks * 7) else delta // 7 + 1
    week = max(1, min(week, weeks))

    hol, mk, hmeta = load_holidays(args.holidays)

    mon = ts + timedelta(days=(week - 1) * 7)
    rows = []
    for k in range(7):
        d = mon + timedelta(days=k)
        items = []
        for ev in data.get("events", []):
            if int(ev["day"]) != (k + 1):
                continue
            rule = ev.get("week_rule", {"type": "weekly", "count": 16})
            hit, excl = weeks_of(rule, weeks)
            if week not in hit or d.isoformat() in excl:
                continue
            items.append({
                "title": ev.get("summary") or ev.get("course") or "(未命名)",
                "loc": ev.get("location", ""),
                "start": ev["start"], "end": ev["end"],
                "ruleType": rule.get("type", "weekly"),
                "rule": RULE_LABEL.get(rule.get("type", "weekly"), rule.get("type", "")),
                "zone": ev.get("zone"),
            })
        items.sort(key=lambda x: to_min(x["start"]))
        rows.append({"date": d, "items": items})

    all_mins = [to_min(it[s]) for r in rows for it in r["items"] for s in ("start", "end")]
    t0 = min([360] + all_mins)
    t1 = max([1320] + all_mins)
    t0 = (t0 // 120) * 120
    t1 = -((-t1) // 120) * 120

    out = args.out or os.path.join(DEFAULT_OUT_DIR, "week-view.html")
    assert_not_in_package(out)
    ensure_parent(out)

    html = build_html({
        "term_start": ts, "week": week, "weeks": weeks, "today": today,
        "hol": hol, "mk": mk, "hmeta": hmeta, "rows": rows,
        "t0": t0, "t1": t1,
        "range_label": "%s ~ %s" % (mon.isoformat(), (mon + timedelta(days=6)).isoformat()),
        "input_path": args.input,
    })
    with open(out, "w", encoding="utf-8", newline="") as f:
        f.write(html)

    print("[OK] 周视图已生成")
    print("    产物路径 : %s" % os.path.abspath(out))
    print("    字节数   : %d" % os.path.getsize(out))
    print("    周次     : 第 %d 周（%s ~ %s）" % (week, mon.isoformat(),
                                                 (mon + timedelta(days=6)).isoformat()))
    print("    时间轴   : %s ~ %s" % (fmt_hm(t0), fmt_hm(t1)))
    print("    安排项数 : %d" % sum(len(r["items"]) for r in rows))
    if args.report:
        print("    ---- 自检标记 ----")
        for mark in ('data-v4-week="%d"' % week, "稳定区", "弹性区", "转场清单",
                     SELFCHECK_COMMENT.split("|")[0].strip()):
            print("      [%s] %s" % ("OK" if mark in html else "FAIL", mark))
    return 0


if __name__ == "__main__":
    sys.exit(main())
