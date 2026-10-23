#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
render_term_heatmap.py — N3 学期负载热力图：20 周 × 7 天负载强度，单文件离线 HTML。

设计目的
--------
回答「这学期哪几周会被压垮」。单周视图看不出节奏，热力图把 20 周一次性铺开：
空周、缓冲周、密集周一眼可见，节假日与调休上班日在格子上直接标记。

能力
----
  * 20 周 × 7 天热力格，色阶按当天安排**分钟数**分 5 档（手写 CSS，无图表库）
  * 空周（整周 0 项）/ 缓冲周（整周 ≤ 2 项）/ 密集周（整周 ≥ 8 项）在周次列标注
  * 法定节假日格子加红边，调休上班日格子加琥珀边
  * 底部给出密集周清单与学期窗内节假日统计

约束（P0 红线）：仅标准库 / 无 CDN 外链 / 无第三方图表库 / 无 emoji / 浅色主题 / utf-8-sig 读输入。

用法
----
    python render_term_heatmap.py timetable.json --out term-heatmap.html --report
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
DAY_SHORT = {1: "一", 2: "二", 3: "三", 4: "四", 5: "五", 6: "六", 7: "日"}
SELFCHECK_COMMENT = ("v4-selfcheck: single-file offline HTML | no-cdn | no-external-link | "
                     "no-third-party-chart-lib | svg-css-handwritten | no-emoji | light-theme")

# 色阶阈值（分钟）：0 / 1-90 / 91-180 / 181-270 / >270
LEVEL_EDGES = [0, 91, 181, 271]
LEVEL_BG = ["#f2f4f7", "#dce8fd", "#b9d2fb", "#8bb6f8", "#5b95f2"]
LEVEL_INK = ["#8b949e", "#2b3440", "#2b3440", "#163a7a", "#ffffff"]

DENSE_MIN = 8      # 密集周阈值（整周项数）
BUFFER_MAX = 2     # 缓冲周阈值（整周项数）


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


def level_of(minutes):
    if minutes <= 0:
        return 0
    lv = 1
    for edge in LEVEL_EDGES[1:]:
        if minutes >= edge:
            lv += 1
    return min(lv, 4)


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


SAMPLE_HOL = {
    "2026-09-25": {"id": "H-S-01", "name": "中秋节"}, "2026-09-26": {"id": "H-S-01", "name": "中秋节"},
    "2026-09-27": {"id": "H-S-01", "name": "中秋节"}, "2026-10-01": {"id": "H-S-02", "name": "国庆节"},
    "2026-10-02": {"id": "H-S-02", "name": "国庆节"}, "2026-10-03": {"id": "H-S-02", "name": "国庆节"},
    "2026-10-04": {"id": "H-S-02", "name": "国庆节"}, "2026-10-05": {"id": "H-S-02", "name": "国庆节"},
    "2026-10-06": {"id": "H-S-02", "name": "国庆节"}, "2026-10-07": {"id": "H-S-02", "name": "国庆节"},
}
SAMPLE_MK = {
    "2026-09-20": {"id": "HM-S-01", "name": "国庆调休上班/补课"},
    "2026-10-10": {"id": "HM-S-02", "name": "国庆调休上班/补课"},
}


def load_holidays(path):
    if not path or not os.path.isfile(path):
        return dict(SAMPLE_HOL), dict(SAMPLE_MK), {
            "source_kind": "sample",
            "source_label": "内置样例（data/holidays-2026.json 尚未就绪）",
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
            hol[x] = {"id": eid, "name": name}
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
  --hol:#a5231b; --mk:#8a5300;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font-family:"Segoe UI","Microsoft YaHei","PingFang SC",system-ui,sans-serif;font-size:14px;line-height:1.6}
.wrap{max-width:1000px;margin:0 auto;padding:24px 20px 56px}
header.hd{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:18px 20px;margin-bottom:16px}
h1{margin:0 0 6px;font-size:19px;font-weight:650}
.sub{color:var(--muted);font-size:13px}
.meta{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px}
.chip{display:inline-flex;gap:6px;background:var(--line2);border:1px solid var(--line);color:var(--muted);
  border-radius:999px;padding:3px 11px;font-size:12px}
.chip b{color:var(--ink);font-weight:600}
.chip.cur{background:var(--accent-soft);border-color:#c7dbfb;color:var(--accent-ink)}
.chip.warn{background:#fdf3e2;border-color:#f0d9ac;color:var(--mk)}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:10px;overflow:hidden}
.grid{display:grid;grid-template-columns:96px repeat(7,1fr);gap:5px;padding:12px}
.hd-cell{color:var(--faint);font-size:12px;text-align:center;padding-bottom:2px}
.wk-label{display:flex;flex-direction:column;justify-content:center;padding-right:6px}
.wk-no{font-weight:650;font-size:13px}
.wk-tag{font-size:11px;border-radius:4px;padding:0 5px;align-self:flex-start;margin-top:2px;color:#fff}
.wk-tag.cur{background:var(--accent)}
.wk-tag.empty{background:#9aa4b0}
.wk-tag.buffer{background:#7a8a99}
.wk-tag.dense{background:#a5231b}
.cell{border-radius:5px;min-height:34px;display:flex;align-items:center;justify-content:center;
  font-size:12px;font-variant-numeric:tabular-nums;border:1px solid transparent;cursor:default}
.cell.hol{border-color:var(--hol);box-shadow:inset 0 0 0 1px var(--hol)}
.cell.mk{border-color:var(--mk);box-shadow:inset 0 0 0 1px var(--mk)}
.cell.today{outline:2px solid var(--accent);outline-offset:1px}
.lg{display:flex;flex-wrap:wrap;gap:14px;padding:10px 14px;border-top:1px solid var(--line2);
  background:#fafbfc;color:var(--muted);font-size:12px;align-items:center}
.sw{display:inline-block;width:20px;height:12px;border-radius:3px;border:1px solid var(--line);
  vertical-align:-1px;margin-right:5px}
.bd{display:inline-block;width:12px;height:12px;border-radius:3px;border:1.5px solid var(--hol);vertical-align:-1px;margin-right:5px}
.bd.mk{border-color:var(--mk)}
h2.sec{font-size:15px;margin:22px 0 10px;font-weight:650}
ul.notes{background:var(--panel);border:1px solid var(--line);border-radius:10px;margin:0;padding:12px 14px 12px 30px;
  color:var(--muted);font-size:13px}
ul.notes li{margin-bottom:4px}
footer.ft{margin-top:16px;color:var(--faint);font-size:12px}
"""


def main():
    _safe_stdout()
    ap = argparse.ArgumentParser(description="生成学期负载热力图 HTML（N3）")
    ap.add_argument("input", help="课表/日程 JSON 文件路径")
    ap.add_argument("--out", default=None, help="输出 HTML 路径（默认用户目录 out/term-heatmap.html）")
    ap.add_argument("--term-start", default=None, help="覆盖 term_start")
    ap.add_argument("--weeks", type=int, default=20, help="学期总周数，默认 20")
    ap.add_argument("--today", default=None, help="覆盖「今天」（YYYY-MM-DD）")
    ap.add_argument("--holidays", default=DEFAULT_HOLIDAY_FILE, help="节假日数据文件路径")
    ap.add_argument("--report", action="store_true", help="打印详细自检报告")
    args = ap.parse_args()

    data = load_json(args.input)
    ts = parse_date(args.term_start or data.get("term_start") or "2026-09-07")
    weeks = int(args.weeks or data.get("weeks") or 20)
    today = parse_date(args.today) if args.today else date.today()
    delta = (today - ts).days
    cur_week = 1 if (delta < 0 or delta >= weeks * 7) else delta // 7 + 1
    hol, mk, hmeta = load_holidays(args.holidays)

    # 展开：{周次: {day: {"count":n, "min":m, "names":[...]}}}
    grid = {w: {d: {"count": 0, "min": 0, "names": []} for d in range(1, 8)}
            for w in range(1, weeks + 1)}
    for ev in data.get("events", []):
        day = int(ev["day"])
        rule = ev.get("week_rule", {"type": "weekly", "count": 16})
        hit, excl = weeks_of(rule, weeks)
        dur = to_min(ev["end"]) - to_min(ev["start"])
        title = ev.get("summary") or ev.get("course") or "(未命名)"
        for w in hit:
            d = ts + timedelta(days=(w - 1) * 7 + (day - 1))
            if d.isoformat() in excl:
                continue
            g = grid[w][day]
            g["count"] += 1
            g["min"] += dur
            g["names"].append("%s %s-%s" % (title, ev["start"], ev["end"]))

    body = ['<div class="grid">', '<div class="hd-cell"></div>']
    for d in range(1, 8):
        body.append('<div class="hd-cell">%s</div>' % DAY_NAME[d])
    totals = {}
    for w in range(1, weeks + 1):
        wcount = sum(grid[w][d]["count"] for d in range(1, 8))
        totals[w] = wcount
        tag = ""
        if w == cur_week:
            tag = '<span class="wk-tag cur">本周</span>'
        elif wcount == 0:
            tag = '<span class="wk-tag empty">空周</span>'
        elif wcount <= BUFFER_MAX:
            tag = '<span class="wk-tag buffer">缓冲</span>'
        elif wcount >= DENSE_MIN:
            tag = '<span class="wk-tag dense">密集</span>'
        body.append('<div class="wk-label"><span class="wk-no">第 %d 周</span>%s</div>' % (w, tag))
        for d in range(1, 8):
            g = grid[w][d]
            lv = level_of(g["min"])
            dd = ts + timedelta(days=(w - 1) * 7 + (d - 1))
            iso = dd.isoformat()
            cls = ["cell"]
            extra = ""
            if iso in hol:
                cls.append("hol")
                extra = "｜%s" % hol[iso]["name"]
            elif iso in mk:
                cls.append("mk")
                extra = "｜调休上班"
            if iso == today.isoformat():
                cls.append("today")
            tip = "%s %s：%d 项 / %d 分钟%s" % (dd.isoformat(), DAY_NAME[d], g["count"], g["min"], extra)
            if g["names"]:
                tip += "｜" + "；".join(g["names"])
            body.append('<div class="%s" style="background:%s;color:%s" title="%s">%s</div>'
                        % (" ".join(cls), LEVEL_BG[lv], LEVEL_INK[lv], esc(tip),
                           str(g["count"]) if g["count"] else ""))
    body.append("</div>")

    dense = [w for w in sorted(totals) if totals[w] >= DENSE_MIN]
    empty_weeks = [w for w in sorted(totals) if totals[w] == 0]
    buffer_weeks = [w for w in sorted(totals) if 0 < totals[w] <= BUFFER_MAX]
    hol_days = sum(1 for i in range(weeks * 7) if (ts + timedelta(days=i)).isoformat() in hol)
    mk_days = sum(1 for i in range(weeks * 7) if (ts + timedelta(days=i)).isoformat() in mk)
    grand = sum(totals.values())

    def lst(xs):
        return "、".join("第 %d 周" % w for w in xs) if xs else "无"

    notes = [
        "密集周（整周 ≥ %d 项）：%s" % (DENSE_MIN, lst(dense)),
        "空周（整周 0 项）：%s" % lst(empty_weeks),
        "缓冲周（整周 1-%d 项）：%s" % (BUFFER_MAX, lst(buffer_weeks)),
        "学期窗内法定节假日 %d 天、调休上班日 %d 天（调休上班日按工作日计容量）。" % (hol_days, mk_days),
        "色阶按当天安排<b>分钟数</b>分档：0 / 1-90 / 91-180 / 181-270 / >270 分钟。",
    ]
    if hmeta["source_kind"] == "sample":
        warn = '<span class="chip warn">节假日为内置样例数据，非官宣基线</span>'
    elif not hmeta.get("verified", True):
        warn = ('<span class="chip warn">节假日数据 originally_verified=false：'
                '未逐条核验原文，正式使用前须以 gov.cn 原文为准</span>')
    else:
        warn = ""

    html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="v4-current-week" content="%(cur)d">
<title>学期负载热力图 · %(weeks)d 周</title>
<!-- %(sc)s -->
<style>%(css)s</style>
</head>
<body data-v4-view="term-heatmap" data-v4-current-week="%(cur)d" data-v4-term-start="%(ts)s">
<div class="wrap">
  <header class="hd">
    <h1>学期负载热力图 · %(weeks)d 周 × 7 天</h1>
    <div class="sub">颜色深浅 = 当天安排分钟数。红边 = 法定节假日，琥珀边 = 调休上班日，蓝框 = 今天。</div>
    <div class="meta">
      <span class="chip">学期起点 <b>%(ts)s</b></span>
      <span class="chip cur">当前 <b>第 %(cur)d 周</b></span>
      <span class="chip">安排总数 <b>%(grand)d</b> 项</span>
      <span class="chip">密集周 <b>%(nd)d</b></span>
      <span class="chip">空周 <b>%(ne)d</b></span>
      <span class="chip">节假日 <b>%(hd)d</b> 天</span>
      <span class="chip">调休上班 <b>%(md)d</b> 天</span>
      %(warn)s
    </div>
  </header>

  <div class="panel">
    %(grid)s
    <div class="lg">
      <span><i class="sw" style="background:#f2f4f7"></i>0</span>
      <span><i class="sw" style="background:#dce8fd"></i>1-90 分</span>
      <span><i class="sw" style="background:#b9d2fb"></i>91-180 分</span>
      <span><i class="sw" style="background:#8bb6f8"></i>181-270 分</span>
      <span><i class="sw" style="background:#5b95f2"></i>&gt;270 分</span>
      <span><i class="bd"></i>法定节假日</span>
      <span><i class="bd mk"></i>调休上班日</span>
    </div>
  </div>

  <h2 class="sec">节奏判读</h2>
  <ul class="notes">%(notes)s</ul>

  <footer class="ft">
    节假日来源 %(hsrc)s ｜ 课表 %(insrc)s ｜ 生成脚本 render_term_heatmap.py ｜
    本文件无外链、无 CDN、无第三方库，全部样式内联。
  </footer>
</div>
</body>
</html>
""" % {
        "cur": cur_week, "weeks": weeks, "ts": ts.isoformat(), "grand": grand,
        "nd": len(dense), "ne": len(empty_weeks), "hd": hol_days, "md": mk_days,
        "warn": warn, "grid": "".join(body), "css": CSS, "sc": SELFCHECK_COMMENT,
        "hsrc": esc(hmeta["source_label"]), "insrc": esc(args.input),
        "notes": "".join("<li>%s</li>" % n for n in notes),
    }

    out = args.out or os.path.join(DEFAULT_OUT_DIR, "term-heatmap.html")
    assert_not_in_package(out)
    ensure_parent(out)
    with open(out, "w", encoding="utf-8", newline="") as f:
        f.write(html)

    print("[OK] 学期负载热力图已生成")
    print("    产物路径 : %s" % os.path.abspath(out))
    print("    字节数   : %d" % os.path.getsize(out))
    print("    学期窗口 : %s ~ %s（%d 周）" % (ts.isoformat(),
                                             (ts + timedelta(days=weeks * 7 - 1)).isoformat(), weeks))
    print("    安排总数 : %d 项" % grand)
    print("    密集周   : %s" % lst(dense))
    print("    空周     : %s" % lst(empty_weeks))
    if args.report:
        print("    ---- 自检标记 ----")
        for mark in ('data-v4-current-week="%d"' % cur_week, "第 %d 周" % cur_week,
                     SELFCHECK_COMMENT.split("|")[0].strip()):
            print("      [%s] %s" % ("OK" if mark in html else "FAIL", mark))
    return 0


if __name__ == "__main__":
    sys.exit(main())
