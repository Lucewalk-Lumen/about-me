#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
render_desktop_calendar.py — N2 桌面日历：整学期本地 HTML 日历应用（单文件、离线可开）。

设计目的
--------
Windows 侧不存在可移植的「写系统日历」通道（实测：Outlook COM 返回 80040154 未注册、
Windows 日历 AppX 未安装、.ics 关联处理器是 UWP 版 Outlook 且不暴露 COM）。
因此 N2「桌面端直接调用日历」的可落地形态是：生成本地单文件 HTML 日历应用，
在 WorkBuddy 预览面板直接打开。本脚本就是该形态的生成器。

能力
----
  * 整学期按周次铺开（周次由 term_start 反推，禁止硬编码）
  * 高亮当前周（默认取系统当日；可用 --today 覆盖）
  * 标注法定节假日与调休上班日（消费 data/holidays-2026.json；文件未就绪时用内置最小样例）
  * 点击某天 → 查看当天安排（名称 / 时间 / 地点 / 周次规则）与当日日期性质
  * 周次视图 / 月历视图切换（纯内联 JS，无外链）

约束（P0 红线）
--------------
  * 仅 Python 标准库；禁止任何第三方图表库（Chart.js / ECharts / D3 一律不用）
  * 所有 CSS / JS 内联，禁止 CDN 外链
  * 禁止 emoji，装饰一律用 CSS 形状或 SVG 路径
  * 浅色主题：浅底深字，不用深色底
  * 输入 JSON 一律 utf-8-sig 读取（兼容记事本 BOM）
  * 禁止写入包内目录（含包内 data/），写入路径一律走用户目录

用法
----
    python render_desktop_calendar.py timetable.json --out desktop-calendar.html
    python render_desktop_calendar.py timetable.json --term-start 2026-09-07 --weeks 20 --report

输入 JSON（与 generate_ics.py 同构）
-----------------------------------
{
  "term_start": "2026-09-07",
  "events": [
    {"summary":"高等数学","location":"乐学楼301","description":"教师：王老师",
     "day":1,"start":"08:00","end":"09:40",
     "week_rule":{"type":"weekly","count":16}}
  ]
}
"""

import argparse
import json
import os
import sys
from datetime import date, datetime, timedelta

# --------------------------------------------------------------------------- #
# 包根解析：脚本自解析，避免相对路径随工作目录漂移
#   skills/schedule-planning/scripts/ -> 上三级 = 包根
# --------------------------------------------------------------------------- #
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


# --------------------------------------------------------------------------- #
# 基础工具
# --------------------------------------------------------------------------- #
def _safe_stdout():
    """Windows GBK 控制台下中文/符号会抛 UnicodeEncodeError，尽力切到 UTF-8。"""
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


def json_for_html(obj):
    """内联 JSON：转义 </ 防止提前闭合 script 标签。"""
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")


def assert_not_in_package(path):
    """硬门禁：任何写入包内目录的行为一律拒绝（包内 data/ 为只读基线）。"""
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


# --------------------------------------------------------------------------- #
# 周次规则展开（与 generate_ics.py 同口径）
# --------------------------------------------------------------------------- #
def weeks_of(rule, total_weeks):
    """返回 (命中的周次列表, 需排除的具体日期集合)。"""
    rtype = (rule or {}).get("type", "weekly")
    rule = rule or {}
    if rtype == "range":
        sw, ew = int(rule["start_week"]), int(rule["end_week"])
        if ew < sw:
            raise ValueError("range 周次非法: %s-%s" % (sw, ew))
        gen = list(range(sw, ew + 1))
        keep = set(gen)
    elif rtype == "custom_weeks":
        ws = sorted(int(x) for x in rule["weeks"])
        if not ws:
            raise ValueError("custom_weeks 的 weeks 不能为空")
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
    else:  # weekly
        base = int(rule.get("start_week", 1))
        n = int(rule.get("count", 16))
        gen = [base + i for i in range(max(n, 1))]
        keep = set(gen)

    keep -= set(int(x) for x in rule.get("exclude_weeks", []))
    exclude_dates = set(rule.get("exclude_dates", []) or [])
    hit = sorted(w for w in gen if 1 <= w <= total_weeks and w in keep)
    return hit, exclude_dates


def expand_events(data, term_start, total_weeks):
    """展开为 {ISO日期: [条目...]}。条目含周次、时间、地点与规则标签。"""
    index = {}
    for ev in data.get("events", []):
        day = int(ev["day"])
        rule = ev.get("week_rule", {"type": "weekly", "count": 16})
        hit, exclude_dates = weeks_of(rule, total_weeks)
        label = RULE_LABEL.get(rule.get("type", "weekly"), rule.get("type", ""))
        detail = ""
        if rule.get("type") == "range":
            detail = "%d-%d 周" % (int(rule["start_week"]), int(rule["end_week"]))
        elif rule.get("type") == "custom_weeks":
            detail = ",".join(str(x) for x in rule["weeks"]) + " 周"
        for w in hit:
            d = term_start + timedelta(days=(w - 1) * 7 + (day - 1))
            iso = d.isoformat()
            if iso in exclude_dates:
                continue
            index.setdefault(iso, []).append({
                "w": w,
                "title": ev.get("summary") or ev.get("course") or "(未命名)",
                "loc": ev.get("location", ""),
                "desc": ev.get("description", ""),
                "start": ev["start"],
                "end": ev["end"],
                "rule": label,
                "ruleDetail": detail,
                "zone": "stable" if rule.get("type", "weekly") == "weekly" else "elastic",
            })
    for k in index:
        index[k].sort(key=lambda x: (to_min(x["start"]), x["title"]))
    return index


# --------------------------------------------------------------------------- #
# 节假日：优先 data/holidays-2026.json，未就绪则回落内置最小样例
# --------------------------------------------------------------------------- #
def _sample_holidays():
    """内置最小样例（4 条，仅覆盖本学期窗 2026-09-07 ~ 2027-01-24）。

    data/holidays-2026.json 由 fact-verifier 侧产出；在其落地前用本样例跑通渲染链路。
    样例标记 status=sample，UI 上会显式提示「样例数据，非官宣基线」。
    """
    src = "内置样例 _sample_holidays()（data/holidays-2026.json 尚未就绪）"
    return {
        "source_kind": "sample",
        "source_label": src,
        "holidays": {
            "2026-09-25": {"id": "H-S-01", "name": "中秋节", "type": "holiday", "status": "sample"},
            "2026-09-26": {"id": "H-S-01", "name": "中秋节", "type": "holiday", "status": "sample"},
            "2026-09-27": {"id": "H-S-01", "name": "中秋节", "type": "holiday", "status": "sample"},
            "2026-10-01": {"id": "H-S-02", "name": "国庆节", "type": "holiday", "status": "sample"},
            "2026-10-02": {"id": "H-S-02", "name": "国庆节", "type": "holiday", "status": "sample"},
            "2026-10-03": {"id": "H-S-02", "name": "国庆节", "type": "holiday", "status": "sample"},
            "2026-10-04": {"id": "H-S-02", "name": "国庆节", "type": "holiday", "status": "sample"},
            "2026-10-05": {"id": "H-S-02", "name": "国庆节", "type": "holiday", "status": "sample"},
            "2026-10-06": {"id": "H-S-02", "name": "国庆节", "type": "holiday", "status": "sample"},
            "2026-10-07": {"id": "H-S-02", "name": "国庆节", "type": "holiday", "status": "sample"},
        },
        "makeups": {
            "2026-09-20": {"id": "HM-S-01", "name": "国庆调休上班/补课", "weekday": "周日"},
            "2026-10-10": {"id": "HM-S-02", "name": "国庆调休上班/补课", "weekday": "周六"},
        },
        "entries_count": 4,
    }


def load_holidays(path):
    """读取节假日数据，输出 (节假日日期映射, 调休上班日映射, 元信息)。"""
    if not path or not os.path.isfile(path):
        s = _sample_holidays()
        return s["holidays"], s["makeups"], {
            "path": path or DEFAULT_HOLIDAY_FILE,
            "source_kind": "sample",
            "source_label": s["source_label"],
            "entries_count": s["entries_count"],
            "confidence": "unknown",
            "status": "sample",
        }

    raw = load_json(path)
    hol, mk = {}, {}
    for e in raw.get("entries", []):
        eid = e.get("id", "")
        name = e.get("name", "")
        etype = e.get("type", "")
        days = [e["date"]] if e.get("date") else _span(e.get("start"), e.get("end"))
        if etype == "make_up_workday":
            for d in days:
                mk[d] = {"id": eid, "name": name, "weekday": e.get("weekday", "")}
            continue
        for d in days:
            hol[d] = {"id": eid, "name": name, "type": "holiday",
                      "status": e.get("status", "official"),
                      "confidence": e.get("confidence", "unknown"),
                      "source_url": e.get("source_url", ""),
                      "fetched_at": e.get("fetched_at", "")}
        for mu in (e.get("make_up_workdays") or []):
            mk[mu["date"]] = {"id": eid, "name": mu.get("note") or (name + " 调休"),
                              "weekday": mu.get("weekday", "")}
    return hol, mk, {
        "path": path,
        "source_kind": "file",
        "source_label": "%s（%s）" % (raw.get("source", {}).get("document_id", "data 文件"),
                                     raw.get("source", {}).get("authority", "")),
        "entries_count": len(raw.get("entries", [])),
        "confidence": raw.get("entries", [{}])[0].get("confidence", "unknown"),
        "status": raw.get("entries", [{}])[0].get("status", "official"),
        # 防编造：数据自带「未逐条核验原文」标记时，UI 必须显式声明，不得静默当作已核验基线
        "verified": bool(raw.get("source", {}).get("originally_verified", False)),
    }


def _span(start, end):
    if not start or not end:
        return []
    d0, d1 = parse_date(start), parse_date(end)
    out, cur = [], d0
    while cur <= d1:
        out.append(cur.isoformat())
        cur += timedelta(days=1)
    return out


def day_nature(d, hol, mk):
    """判定某日性质：法定假日 / 调休上班日 / 普通周末 / 工作日。"""
    iso = d.isoformat()
    if iso in hol:
        return "holiday", hol[iso]
    if iso in mk:
        return "makeup", mk[iso]
    if d.isoweekday() >= 6:
        return "weekend", {}
    return "workday", {}


NATURE_LABEL = {"holiday": "法定节假日", "makeup": "调休上班日",
                "weekend": "普通周末", "workday": "工作日"}


# --------------------------------------------------------------------------- #
# HTML
# --------------------------------------------------------------------------- #
CSS = """
:root{
  --bg:#f6f7f9; --panel:#ffffff; --ink:#1f2328; --muted:#5b6470; --faint:#8b949e;
  --line:#e3e6ea; --line2:#eef0f3;
  --accent:#2f6feb; --accent-soft:#e8f0fe; --accent-ink:#1b4bb8;
  --hol-bg:#fdeceb; --hol-ink:#a5231b; --hol-line:#f3c7c2;
  --mk-bg:#fdf3e2; --mk-ink:#8a5300; --mk-line:#f0d9ac;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font-family:"Segoe UI","Microsoft YaHei","PingFang SC",system-ui,sans-serif;font-size:14px;line-height:1.6}
.wrap{max-width:1180px;margin:0 auto;padding:24px 20px 56px}
header.hd{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:18px 20px;margin-bottom:16px}
h1{margin:0 0 6px;font-size:19px;font-weight:650;letter-spacing:.2px}
.sub{color:var(--muted);font-size:13px}
.meta{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px}
.chip{display:inline-flex;align-items:center;gap:6px;background:var(--line2);border:1px solid var(--line);
  color:var(--muted);border-radius:999px;padding:3px 11px;font-size:12px}
.chip b{color:var(--ink);font-weight:600}
.chip.cur{background:var(--accent-soft);border-color:#c7dbfb;color:var(--accent-ink)}
.chip.warn{background:var(--mk-bg);border-color:var(--mk-line);color:var(--mk-ink)}
.tabs{display:flex;gap:6px;margin:16px 0 12px}
.tab{appearance:none;border:1px solid var(--line);background:var(--panel);color:var(--muted);
  padding:6px 16px;border-radius:8px;font-size:13px;cursor:pointer;transition:background .12s ease-out,color .12s ease-out}
.tab:hover{background:var(--line2)}
.tab.on{background:var(--accent);border-color:var(--accent);color:#fff}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:10px;overflow:hidden}
.view{display:none}.view.on{display:block}
.wk-row{display:grid;grid-template-columns:132px 1fr;border-top:1px solid var(--line2)}
.wk-row:first-child{border-top:0}
.wk-row.is-current{background:#f4f8ff}
.wk-label{padding:10px 12px;border-right:1px solid var(--line2);position:relative}
.wk-row.is-current .wk-label{border-left:3px solid var(--accent);padding-left:9px}
.wk-no{font-weight:650;font-size:14px}
.wk-range{color:var(--faint);font-size:12px;font-variant-numeric:tabular-nums}
.badge{display:inline-block;margin-left:6px;background:var(--accent);color:#fff;border-radius:4px;
  padding:0 6px;font-size:11px;font-weight:600;vertical-align:1px}
.wk-days{display:grid;grid-template-columns:repeat(7,1fr);gap:6px;padding:8px}
.day{appearance:none;text-align:left;border:1px solid var(--line);background:#fff;border-radius:7px;
  padding:6px 7px;cursor:pointer;min-height:62px;display:flex;flex-direction:column;gap:2px;
  transition:border-color .12s ease-out,background .12s ease-out}
.day:hover{border-color:var(--accent);background:#fafcff}
.day.is-today{border-color:var(--accent);box-shadow:inset 0 0 0 1px var(--accent)}
.day.is-holiday{background:var(--hol-bg);border-color:var(--hol-line)}
.day.is-makeup{background:var(--mk-bg);border-color:var(--mk-line)}
.day.is-empty{background:#fbfbfc}
.dnum{font-size:15px;font-weight:650;font-variant-numeric:tabular-nums}
.dwd{color:var(--faint);font-size:11px}
.dtag{align-self:flex-start;margin-top:auto;border-radius:4px;padding:0 5px;font-size:11px;line-height:17px}
.dtag.n{background:var(--accent-soft);color:var(--accent-ink)}
.dtag.h{background:#f7d4d0;color:var(--hol-ink)}
.dtag.m{background:#f6e2be;color:var(--mk-ink)}
.dholiday{color:var(--hol-ink);font-size:11px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.month{margin-bottom:14px}
.month-t{font-weight:650;padding:10px 14px;border-bottom:1px solid var(--line2);background:#fafbfc}
.mhead{display:grid;grid-template-columns:repeat(7,1fr);gap:6px;padding:8px 10px 0;color:var(--faint);font-size:12px;text-align:center}
.mgrid{display:grid;grid-template-columns:repeat(7,1fr);gap:6px;padding:8px 10px 12px}
.split{display:grid;grid-template-columns:1fr 340px;gap:16px;align-items:start}
@media(max-width:900px){.split{grid-template-columns:1fr}}
.side{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:16px;position:sticky;top:16px}
.side h2{font-size:14px;margin:0 0 4px;font-weight:650}
.side .dt{color:var(--muted);font-size:12px;margin-bottom:10px}
.nat{border:1px solid var(--line);border-radius:7px;padding:9px 11px;margin-bottom:12px;background:#fafbfc;font-size:13px}
.nat.holiday{background:var(--hol-bg);border-color:var(--hol-line);color:var(--hol-ink)}
.nat.makeup{background:var(--mk-bg);border-color:var(--mk-line);color:var(--mk-ink)}
.ev{border-left:3px solid var(--accent);padding:7px 0 7px 10px;margin-bottom:8px}
.ev.elastic{border-left-color:#9aa4b0;border-left-style:dashed}
.ev .t{font-variant-numeric:tabular-nums;color:var(--muted);font-size:12px}
.ev .n{font-weight:600}
.ev .l{color:var(--muted);font-size:12px}
.ev .r{color:var(--faint);font-size:11px}
.empty{color:var(--faint);font-size:13px;padding:8px 0}
.lg{display:flex;flex-wrap:wrap;gap:14px;padding:10px 14px;border-top:1px solid var(--line2);
  background:#fafbfc;color:var(--muted);font-size:12px}
.sw{display:inline-block;width:11px;height:11px;border-radius:3px;border:1px solid var(--line);vertical-align:-1px;margin-right:5px}
footer.ft{margin-top:16px;color:var(--faint);font-size:12px}
.src{font-size:12px;color:var(--muted);word-break:break-all}
"""

JS = """
(function(){
  var DATA = JSON.parse(document.getElementById('v4-day-data').textContent);
  var box = document.getElementById('v4-detail');
  // 课表来自用户 JSON，拼进 innerHTML 前必须转义，防止尖括号/引号破坏结构
  function E(s){
    return String(s == null ? '' : s).replace(/[&<>"']/g, function(c){
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];
    });
  }
  function pick(iso){
    var d = DATA.days[iso];
    var date = new Date(iso + 'T00:00:00');
    var wd = ['周日','周一','周二','周三','周四','周五','周六'][date.getDay()];
    var h = '<h2>' + E(iso) + ' ' + wd + '</h2>';
    h += '<div class="dt">教学周第 ' + d.week + ' 周</div>';
    var natCls = d.nature === 'holiday' ? 'holiday' : (d.nature === 'makeup' ? 'makeup' : '');
    h += '<div class="nat ' + natCls + '"><b>' + E(d.natureLabel) + '</b>';
    if (d.natureName) { h += ' · ' + E(d.natureName); }
    if (d.natureId) { h += '<div style="font-size:12px;margin-top:3px">编号 ' + E(d.natureId)
      + (d.natureConf ? ' · confidence=' + E(d.natureConf) : '')
      + (d.natureStatus ? ' · status=' + E(d.natureStatus) : '') + '</div>'; }
    if (d.natureUrl) { h += '<div class="src" style="margin-top:3px">来源 ' + E(d.natureUrl) + '</div>'; }
    h += '</div>';
    if (!d.events.length) { h += '<div class="empty">当天没有安排。</div>'; }
    else {
      d.events.forEach(function(e){
        h += '<div class="ev ' + (e.zone === 'elastic' ? 'elastic' : '') + '">'
          + '<div class="t">' + E(e.start) + ' - ' + E(e.end) + '</div>'
          + '<div class="n">' + E(e.title) + '</div>'
          + (e.loc ? '<div class="l">地点：' + E(e.loc) + '</div>' : '')
          + (e.desc ? '<div class="l">' + E(e.desc) + '</div>' : '')
          + '<div class="r">周次规则：' + E(e.rule) + (e.ruleDetail ? '（' + E(e.ruleDetail) + '）' : '')
          + ' · ' + (e.zone === 'elastic' ? '弹性区' : '稳定区') + '</div></div>';
      });
    }
    box.innerHTML = h;
    var all = document.querySelectorAll('.day');
    for (var i = 0; i < all.length; i++) { all[i].classList.remove('is-sel'); }
    var sels = document.querySelectorAll('[data-date="' + iso + '"]');
    for (var j = 0; j < sels.length; j++) { sels[j].classList.add('is-sel'); }
  }
  document.addEventListener('click', function(ev){
    var el = ev.target.closest ? ev.target.closest('[data-date]') : null;
    if (el) { pick(el.getAttribute('data-date')); }
  });
  var tabs = document.querySelectorAll('.tab');
  for (var k = 0; k < tabs.length; k++) {
    tabs[k].addEventListener('click', function(){
      for (var i = 0; i < tabs.length; i++) { tabs[i].classList.remove('on'); }
      this.classList.add('on');
      var tgt = this.getAttribute('data-view');
      var vs = document.querySelectorAll('.view');
      for (var j = 0; j < vs.length; j++) {
        vs[j].classList.toggle('on', vs[j].getAttribute('id') === tgt);
      }
    });
  }
  pick(DATA.today);
})();
"""


def build_html(ctx):
    """ctx: term_start, weeks, today, cur_week, day_index, hol, mk, hmeta, out_name"""
    ts, weeks, today = ctx["term_start"], ctx["weeks"], ctx["today"]
    hol, mk, hmeta = ctx["hol"], ctx["mk"], ctx["hmeta"]
    cur_week = ctx["cur_week"]
    day_index = ctx["day_index"]

    # ---- 数据载荷（供内联 JS 消费） ----
    payload = {"today": today.isoformat(), "termStart": ts.isoformat(),
               "weeks": weeks, "currentWeek": cur_week, "days": {}}
    term_end = ts + timedelta(days=weeks * 7 - 1)
    d = ts
    while d <= term_end:
        w = (d - ts).days // 7 + 1
        nat, info = day_nature(d, hol, mk)
        payload["days"][d.isoformat()] = {
            "week": w,
            "nature": nat,
            "natureLabel": NATURE_LABEL[nat],
            "natureName": info.get("name", ""),
            "natureId": info.get("id", ""),
            "natureConf": info.get("confidence", ""),
            "natureStatus": info.get("status", ""),
            "natureUrl": info.get("source_url", ""),
            "events": day_index.get(d.isoformat(), []),
        }
        d += timedelta(days=1)

    # ---- 周次视图 ----
    wk_rows = []
    for w in range(1, weeks + 1):
        is_cur = (w == cur_week)
        mon = ts + timedelta(days=(w - 1) * 7)
        sun = mon + timedelta(days=6)
        cells = []
        for k in range(7):
            dd = mon + timedelta(days=k)
            nat, info = day_nature(dd, hol, mk)
            evs = day_index.get(dd.isoformat(), [])
            cls = ["day"]
            if nat == "holiday":
                cls.append("is-holiday")
            elif nat == "makeup":
                cls.append("is-makeup")
            if dd == today:
                cls.append("is-today")
            if not evs:
                cls.append("is-empty")
            tag = ""
            if nat == "holiday":
                tag = '<span class="dtag h">%s</span>' % esc(info.get("name", "放假"))
            elif nat == "makeup":
                tag = '<span class="dtag m">补班</span>'
            elif evs:
                tag = '<span class="dtag n">%d 项</span>' % len(evs)
            cells.append(
                '<button type="button" class="%s" data-date="%s">'
                '<span class="dnum">%d</span><span class="dwd">%s</span>%s</button>'
                % (" ".join(cls), dd.isoformat(), dd.day, DAY_NAME[k + 1], tag))
        wk_rows.append(
            '<div class="wk-row%s" data-week="%d">'
            '<div class="wk-label"><span class="wk-no">第 %d 周</span>%s'
            '<div class="wk-range">%s ~ %s</div></div>'
            '<div class="wk-days">%s</div></div>'
            % (" is-current" if is_cur else "", w, w,
               '<span class="badge">本周</span>' if is_cur else "",
               mon.strftime("%m-%d"), sun.strftime("%m-%d"), "".join(cells)))

    # ---- 月历视图 ----
    months = []
    d = ts.replace(day=1)
    while d <= term_end:
        ym = (d.year, d.month)
        last_day = (d.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        head = "".join("<div>%s</div>" % DAY_NAME[i] for i in range(1, 8))
        lead = d.isoweekday() % 7  # 周一 -> 0
        cells = ["<div></div>"] * lead
        cur = d
        while cur <= last_day:
            nat, info = day_nature(cur, hol, mk)
            in_term = ts <= cur <= term_end
            evs = day_index.get(cur.isoformat(), [])
            cls = ["day"]
            if nat == "holiday":
                cls.append("is-holiday")
            elif nat == "makeup":
                cls.append("is-makeup")
            if cur == today:
                cls.append("is-today")
            if not in_term or not evs:
                cls.append("is-empty")
            tag = ""
            if nat == "holiday":
                tag = '<span class="dtag h">%s</span>' % esc(info.get("name", "放假"))
            elif nat == "makeup":
                tag = '<span class="dtag m">补班</span>'
            elif evs:
                tag = '<span class="dtag n">%d 项</span>' % len(evs)
            style = "" if in_term else ' style="opacity:.45"'
            cells.append('<button type="button" class="%s" data-date="%s"%s>'
                         '<span class="dnum">%d</span>%s</button>'
                         % (" ".join(cls), cur.isoformat(), style, cur.day, tag))
            cur += timedelta(days=1)
        months.append(
            '<div class="month"><div class="month-t">%d 年 %d 月</div>'
            '<div class="mhead">%s</div><div class="mgrid">%s</div></div>'
            % (d.year, d.month, head, "".join(cells)))
        d = (d.replace(day=28) + timedelta(days=4)).replace(day=1)

    warn = ""
    if hmeta["source_kind"] == "sample":
        warn = ('<span class="chip warn">节假日为内置样例数据，非官宣基线；'
                'data/holidays-2026.json 到位后需重跑</span>')
    elif not hmeta.get("verified", True):
        warn = ('<span class="chip warn">节假日数据文件自带 originally_verified=false：'
                '未逐条核验原文，正式使用前须以 gov.cn 原文为准</span>')

    return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="v4-current-week" content="%(cur)d">
<meta name="v4-term-start" content="%(ts)s">
<title>桌面日历 · 第 %(cur)d 周</title>
<!-- %(sc)s -->
<style>%(css)s</style>
</head>
<body data-v4-current-week="%(cur)d" data-v4-term-start="%(ts)s" data-v4-view="desktop-calendar">
<div class="wrap">
  <header class="hd">
    <h1>桌面日历 · %(title)s</h1>
    <div class="sub">本地单文件 HTML 日历应用 · 离线可开 · 周次由 term_start 反推，未硬编码</div>
    <div class="meta">
      <span class="chip">学期起点 <b>%(ts)s</b></span>
      <span class="chip">共 <b>%(weeks)d</b> 周</span>
      <span class="chip cur">当前 <b>第 %(cur)d 周</b>（%(wrange)s）</span>
      <span class="chip">今天 <b>%(today)s</b></span>
      <span class="chip">节假日条目 <b>%(hent)d</b></span>
      %(warn)s
    </div>
  </header>

  <div class="tabs">
    <button type="button" class="tab on" data-view="v-week">按周次</button>
    <button type="button" class="tab" data-view="v-month">按月历</button>
  </div>

  <div class="split">
    <div>
      <div class="panel view on" id="v-week">%(wkrows)s
        <div class="lg">
          <span><i class="sw" style="background:#e8f0fe;border-color:#c7dbfb"></i>有安排</span>
          <span><i class="sw" style="background:#fdeceb;border-color:#f3c7c2"></i>法定节假日</span>
          <span><i class="sw" style="background:#fdf3e2;border-color:#f0d9ac"></i>调休上班日</span>
          <span><i class="sw" style="background:#fbfbfc"></i>无安排</span>
          <span>蓝色左边框 + 「本周」徽章 = 当前周（第 %(cur)d 周）</span>
        </div>
      </div>
      <div class="panel view" id="v-month">%(months)s</div>
    </div>
    <aside class="side" id="v4-detail"></aside>
  </div>

  <footer class="ft">
    数据来源：节假日 %(hsrc)s ｜ 课表 %(insrc)s ｜ 生成脚本 render_desktop_calendar.py ｜
    本文件无外链、无 CDN、无第三方库，全部样式与交互内联。
  </footer>
</div>
<script type="application/json" id="v4-day-data">%(payload)s</script>
<script>%(js)s</script>
</body>
</html>
""" % {
        "cur": cur_week, "ts": ts.isoformat(), "weeks": weeks,
        "title": "第 %d 周 / 共 %d 周" % (cur_week, weeks),
        "wrange": "%s ~ %s" % ((ts + timedelta(days=(cur_week - 1) * 7)).strftime("%m-%d"),
                               (ts + timedelta(days=(cur_week - 1) * 7 + 6)).strftime("%m-%d")),
        "today": today.isoformat(), "hent": hmeta["entries_count"], "warn": warn,
        "wkrows": "".join(wk_rows), "months": "".join(months),
        "payload": json_for_html(payload), "js": JS, "css": CSS, "sc": SELFCHECK_COMMENT,
        "hsrc": esc(hmeta["source_label"]), "insrc": esc(ctx["input_path"]),
    }


# --------------------------------------------------------------------------- #
# 主流程
# --------------------------------------------------------------------------- #
def main():
    _safe_stdout()
    ap = argparse.ArgumentParser(description="生成整学期本地 HTML 桌面日历（N2）")
    ap.add_argument("input", help="课表/日程 JSON 文件路径")
    ap.add_argument("--out", default=None, help="输出 HTML 路径（默认用户目录 out/desktop-calendar.html）")
    ap.add_argument("--term-start", default=None, help="覆盖 JSON 中的 term_start（YYYY-MM-DD）")
    ap.add_argument("--weeks", type=int, default=20, help="学期总周数，默认 20")
    ap.add_argument("--today", default=None, help="覆盖「今天」（YYYY-MM-DD），用于周次高亮定位")
    ap.add_argument("--holidays", default=DEFAULT_HOLIDAY_FILE, help="节假日数据文件路径")
    ap.add_argument("--report", action="store_true", help="打印详细自检报告")
    args = ap.parse_args()

    data = load_json(args.input)
    ts = parse_date(args.term_start or data.get("term_start") or "2026-09-07")
    if ts.isoweekday() != 1:
        print("[WARN] term_start=%s 不是周一，周次推算可能偏移" % ts.isoformat())
    weeks = int(args.weeks or data.get("weeks") or 20)

    today = parse_date(args.today) if args.today else date.today()
    delta = (today - ts).days
    if delta < 0 or delta >= weeks * 7:
        cur_week = 1
        print("[WARN] today=%s 不在学期区间内，当前周回落为第 1 周" % today.isoformat())
    else:
        cur_week = delta // 7 + 1

    hol, mk, hmeta = load_holidays(args.holidays)
    day_index = expand_events(data, ts, weeks)

    out = args.out or os.path.join(DEFAULT_OUT_DIR, "desktop-calendar.html")
    assert_not_in_package(out)
    ensure_parent(out)

    html = build_html({
        "term_start": ts, "weeks": weeks, "today": today, "cur_week": cur_week,
        "day_index": day_index, "hol": hol, "mk": mk, "hmeta": hmeta,
        "input_path": args.input,
    })
    with open(out, "w", encoding="utf-8", newline="") as f:
        f.write(html)

    size = os.path.getsize(out)
    total_occ = sum(len(v) for v in day_index.values())
    print("[OK] 桌面日历已生成")
    print("    产物路径 : %s" % os.path.abspath(out))
    print("    字节数   : %d" % size)
    print("    学期起点 : %s ｜ 共 %d 周" % (ts.isoformat(), weeks))
    print("    当前周   : 第 %d 周（%s ~ %s）" % (
        cur_week,
        (ts + timedelta(days=(cur_week - 1) * 7)).isoformat(),
        (ts + timedelta(days=(cur_week - 1) * 7 + 6)).isoformat()))
    print("    展开安排 : %d 条（模板 %d 条）" % (total_occ, len(data.get("events", []))))
    print("    节假日   : %s ｜ 条目 %d" % (hmeta["source_kind"], hmeta["entries_count"]))
    if args.report:
        print("    ---- 自检标记 ----")
        for mark in ("data-v4-current-week=\"%d\"" % cur_week, "is-current",
                     "第 %d 周" % cur_week, SELFCHECK_COMMENT.split("|")[0].strip()):
            print("      [%s] %s" % ("OK" if mark in html else "FAIL", mark))
        n_hol = sum(1 for v in payload_weeks(ts, weeks, hol) if v)
        print("    学期窗内节假日天数 : %d" % n_hol)
        print("    学期窗内调休上班日 : %d" % sum(
            1 for i in range(weeks * 7)
            if (ts + timedelta(days=i)).isoformat() in mk))
    return 0


def payload_weeks(ts, weeks, hol):
    for i in range(weeks * 7):
        yield (ts + timedelta(days=i)).isoformat() in hol


if __name__ == "__main__":
    sys.exit(main())
