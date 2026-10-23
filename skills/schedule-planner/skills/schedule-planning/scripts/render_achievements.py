#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
render_achievements.py — N5-b 学期成就页：进度条 + 连击打卡 + 成就徽章墙，单文件离线 HTML。

设计目的
--------
用户要的是「查看自己一学期的功劳」，不是要一个游戏。所以 N5-b 落地为**学期成就页**：
把功劳档案里已经发生的事，用进度条、连击日历和徽章墙呈现出来。

**不做真游戏**：无积分商城、无排行榜、无后端、无账号。徽章全部由本地功劳档案
确定性计算得出，点一下能看到「解锁条件 + 当前进度」，不提供任何虚拟货币或兑换。

能力
----
  * 学期进度条：已过周次 / 总周次（按 term_start 反推，未硬编码）
  * 连击打卡日历：整学期 20 周 × 7 天，有记录的格子着色，当前连击天数高亮
  * 成就徽章墙：12 枚徽章，纯 SVG 几何图形（无 emoji、无图标字体），
      点击任意徽章 → 右侧显示解锁条件与当前进度
  * 当前连击天数、累计记录数、累计工时三个数字卡

数据来源
--------
功劳档案 `%USERPROFILE%/.schedule-planner/logbook.jsonl`（用户目录，包内只读）。
档案不存在或为空时优雅降级：徽章全部为「未解锁」并显示条件，页面不崩溃。

约束（P0 红线）：仅标准库 / 无 CDN 外链 / 无第三方图表库 / 无 emoji / 浅色主题 / utf-8-sig 读输入。

用法
----
    python render_achievements.py --out achievements.html --report
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

DAY_NAME = {1: "一", 2: "二", 3: "三", 4: "四", 5: "五", 6: "六", 7: "日"}

# 手写 SVG 几何图形（禁用 emoji 作功能图标，一律矢量图形）
ICONS = {
    "dot":      "M32 32 m-9 0 a9 9 0 1 0 18 0 a9 9 0 1 0 -18 0",
    "tri":      "M32 17 L45 45 L19 45 Z",
    "diamond":  "M32 16 L46 32 L32 48 L18 32 Z",
    "hex":      "M32 15 L46 24 L46 40 L32 49 L18 40 L18 24 Z",
    "chevron":  "M22 20 L34 32 L22 44 L28 44 L40 32 L28 20 Z",
    "bars":     "M20 40 h6 v-16 h-6 Z M29 40 h6 v-24 h-6 Z M38 40 h6 v-10 h-6 Z",
    "ring":     "M32 32 m-14 0 a14 14 0 1 0 28 0 a14 14 0 1 0 -28 0 M32 32 m-7 0 a7 7 0 1 1 14 0 a7 7 0 1 1 -14 0",
    "cross":    "M26 18 h12 v10 h10 v12 h-10 v10 h-12 v-10 h-10 v-12 h10 Z",
    "square":   "M20 20 h24 v24 h-24 Z",
    "steps":    "M18 44 h10 v-8 h10 v-8 h10 v-8 h8 v24 Z",
}


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


def json_for_html(obj):
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")


def assert_not_in_package(path):
    p = os.path.normcase(os.path.abspath(path))
    root = os.path.normcase(os.path.abspath(PKG_ROOT))
    if p == root or p.startswith(root + os.sep):
        raise SystemExit("[FAIL] 禁止写入包内目录（包内 data/ 为只读基线）：%s" % path)


def ensure_parent(path):
    d = os.path.dirname(os.path.abspath(path))
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)


def read_logbook(path):
    if not path or not os.path.isfile(path):
        return [], {"exists": False, "lines": 0, "bad": 0, "path": path}
    recs, bad, lines = [], 0, 0
    with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            lines += 1
            try:
                obj = json.loads(line)
            except Exception:
                bad += 1
                continue
            if isinstance(obj, dict):
                recs.append(obj)
            else:
                bad += 1
    return recs, {"exists": True, "lines": lines, "bad": bad, "path": path}


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


def compute_stats(recs, today, term_start, weeks):
    s = {"total": 0, "done": 0, "dates": {}, "streak": 0, "max_streak": 0,
         "p0_done": 0, "fact_error": 0, "weekend": 0, "accurate": 0, "measured": 0,
         "minutes": 0, "full_weeks": 0, "latest": ""}
    if not recs:
        s["cur_week"] = week_of(today, term_start, weeks)
        return s
    ds = set()
    by_week = {}
    for r in recs:
        s["total"] += 1
        if str(r.get("status", "")).lower() == "done":
            s["done"] += 1
            if str(r.get("priority", "")).upper() == "P0":
                s["p0_done"] += 1
        if str(r.get("attribution", "")).lower() == "fact_error":
            s["fact_error"] += 1
        s["minutes"] += rec_min(r, "actual_minutes")
        pl, ac = rec_min(r, "planned_minutes"), rec_min(r, "actual_minutes")
        if pl > 0 and ac > 0:
            s["measured"] += 1
            if abs(ac - pl) / pl <= 0.20:
                s["accurate"] += 1
        d = rec_date(r)
        if d:
            ds.add(d)
            s["dates"][d.isoformat()] = s["dates"].get(d.isoformat(), 0) + 1
            if d.isoweekday() >= 6:
                s["weekend"] += 1
            w = (d - term_start).days // 7 + 1
            if 1 <= w <= weeks:
                by_week.setdefault(w, set()).add(d)
    s["cur_week"] = week_of(today, term_start, weeks)
    if ds:
        # 当前连击：从最近记录日往前回溯
        latest = max(ds)
        s["latest"] = latest.isoformat()
        cur, k = latest, 0
        while cur in ds:
            k += 1
            cur -= timedelta(days=1)
        s["streak"] = 0 if (today - latest).days > 1 else k
        # 历史最长连击
        best, run, prev = 0, 0, None
        for d in sorted(ds):
            run = run + 1 if (prev and (d - prev).days == 1) else 1
            best = max(best, run)
            prev = d
        s["max_streak"] = best
        s["full_weeks"] = sum(1 for w, dd in by_week.items() if len(dd) == 7)
    return s


def week_of(d, term_start, weeks):
    delta = (d - term_start).days
    if delta < 0 or delta >= weeks * 7:
        return 1
    return delta // 7 + 1


# --------------------------------------------------------------------------- #
# 徽章定义：条件 + 进度，全部由本地数据确定性计算（无后端、无排行榜、无积分）
# --------------------------------------------------------------------------- #
def badge_defs(s, weeks):
    cur = s["cur_week"]
    return [
        {"id": "B01", "name": "初次落笔", "icon": "dot", "cond": "功劳档案写入第 1 条记录",
         "have": s["total"], "need": 1},
        {"id": "B02", "name": "三日成型", "icon": "tri", "cond": "连续打卡 ≥ 3 天",
         "have": s["max_streak"], "need": 3},
        {"id": "B03", "name": "一周不断", "icon": "hex", "cond": "连续打卡 ≥ 7 天",
         "have": s["max_streak"], "need": 7},
        {"id": "B04", "name": "半月坚持", "icon": "steps", "cond": "连续打卡 ≥ 14 天",
         "have": s["max_streak"], "need": 14},
        {"id": "B05", "name": "二十起步", "icon": "bars", "cond": "累计记录 ≥ 20 条",
         "have": s["total"], "need": 20},
        {"id": "B06", "name": "百条功勋", "icon": "square", "cond": "累计记录 ≥ 100 条",
         "have": s["total"], "need": 100},
        {"id": "B07", "name": "P0 清道夫", "icon": "chevron", "cond": "P0 任务完成 ≥ 10 项",
         "have": s["p0_done"], "need": 10},
        {"id": "B08", "name": "零事实错误", "icon": "ring",
         "cond": "累计 ≥ 20 条且 attribution 无 fact_error",
         "have": s["total"] if (s["total"] >= 20 and s["fact_error"] == 0) else min(s["total"], 19),
         "need": 20},
        {"id": "B09", "name": "学期过半", "icon": "diamond",
         "cond": "当前周次 ≥ 学期总周数的一半（%d 周）" % max(weeks // 2, 1),
         "have": cur, "need": max(weeks // 2, 1)},
        {"id": "B10", "name": "估时精准", "icon": "cross",
         "cond": "≥15 条有效估时记录，且实际/计划偏差 ≤20% 的占比 ≥70%",
         "have": int(s["accurate"] / s["measured"] * 100) if s["measured"] else 0,
         "need": 70, "ok": s["measured"] >= 15},
        {"id": "B11", "name": "周末不休", "icon": "steps", "cond": "周六或周日有记录 ≥ 5 条",
         "have": s["weekend"], "need": 5},
        {"id": "B12", "name": "满勤一周", "icon": "square", "cond": "存在某一周 7 天全部有记录",
         "have": s["full_weeks"], "need": 1},
    ]


def badge_svg(icon, unlocked):
    d = ICONS.get(icon, ICONS["dot"])
    fill = "#2f6feb" if unlocked else "#f2f4f7"
    stroke = "#2f6feb" if unlocked else "#c8ced6"
    inner = "#ffffff" if unlocked else "#aeb6c0"
    return ('<svg viewBox="0 0 64 64" width="56" height="56" aria-hidden="true">'
            '<circle cx="32" cy="32" r="29" fill="%s" stroke="%s" stroke-width="2"/>'
            '<path d="%s" fill="%s"/></svg>' % (fill, stroke, d, inner))


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
.notice{background:var(--warn-bg);border:1px solid var(--warn-line);color:var(--warn);
  border-radius:10px;padding:12px 16px;margin-bottom:16px;font-size:13px}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:16px}
h2.sec{font-size:15px;margin:22px 0 10px;font-weight:650}
.prog{height:16px;background:var(--line2);border-radius:8px;overflow:hidden;position:relative}
.prog i{display:block;height:100%;background:var(--accent)}
.prog-row{display:flex;justify-content:space-between;font-size:12px;color:var(--muted);margin-bottom:6px}
.ticks{display:flex;justify-content:space-between;color:var(--faint);font-size:11px;margin-top:4px}
.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:14px}
@media(max-width:760px){.cards{grid-template-columns:1fr}}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px 16px}
.card .k{color:var(--muted);font-size:12px}
.card .v{font-size:26px;font-weight:650;font-variant-numeric:tabular-nums;line-height:1.2}
.card .d{font-size:12px;color:var(--faint)}
.cal{display:grid;grid-template-columns:repeat(20,1fr);gap:4px}
@media(max-width:900px){.cal{grid-template-columns:repeat(10,1fr)}}
.cw{display:flex;flex-direction:column;gap:4px}
.cc{height:14px;border-radius:3px;background:#f2f4f7;border:1px solid #e8ebef}
.cc.l1{background:#cfe0fb}.cc.l2{background:#8bb6f8}.cc.l3{background:#4a8bf0}
.cc.out{background:#fbfbfc;border-style:dashed}
.calhead{display:grid;grid-template-columns:repeat(20,1fr);gap:4px;color:var(--faint);font-size:11px;margin-bottom:4px}
@media(max-width:900px){.calhead{display:none}}
.wall{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}
@media(max-width:860px){.wall{grid-template-columns:repeat(2,1fr)}}
.badge{appearance:none;background:var(--panel);border:1px solid var(--line);border-radius:10px;
  padding:14px 10px;text-align:center;cursor:pointer;transition:border-color .12s ease-out,background .12s ease-out}
.badge:hover{border-color:var(--accent);background:#fafcff}
.badge .nm{font-weight:650;font-size:13px;margin-top:6px}
.badge .st{font-size:11px;color:var(--faint)}
.badge.on .st{color:var(--accent-ink)}
.badge.sel{border-color:var(--accent);box-shadow:inset 0 0 0 1px var(--accent)}
.split{display:grid;grid-template-columns:1fr 320px;gap:16px;align-items:start}
@media(max-width:900px){.split{grid-template-columns:1fr}}
.side{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:16px;position:sticky;top:16px}
.side h3{margin:0 0 6px;font-size:14px;font-weight:650}
.side .cond{color:var(--muted);font-size:13px;margin-bottom:10px}
.mini{height:10px;background:var(--line2);border-radius:5px;overflow:hidden;margin:8px 0 4px}
.mini i{display:block;height:100%;background:var(--accent)}
.pv{color:var(--faint);font-size:12px}
.tag{display:inline-block;border-radius:4px;padding:1px 7px;font-size:11px;font-weight:600}
.tag.on{background:var(--accent-soft);color:var(--accent-ink)}
.tag.off{background:var(--line2);color:var(--muted)}
footer.ft{margin-top:16px;color:var(--faint);font-size:12px}
"""

JS = """
(function(){
  var B = JSON.parse(document.getElementById('v4-badge-data').textContent);
  var box = document.getElementById('v4-badge-detail');
  // 徽章文案拼进 innerHTML 前转义，防止尖括号/引号破坏结构
  function E(s){
    return String(s == null ? '' : s).replace(/[&<>"']/g, function(c){
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];
    });
  }
  function show(id){
    var b = null;
    for (var i = 0; i < B.length; i++) { if (B[i].id === id) { b = B[i]; } }
    if (!b) { return; }
    var pct = b.need > 0 ? Math.min(100, Math.round(b.have / b.need * 100)) : 100;
    var h = '<h3>' + E(b.name) + '</h3>';
    h += '<div><span class="tag ' + (b.unlocked ? 'on' : 'off') + '">'
      + (b.unlocked ? '已解锁' : '未解锁') + '</span></div>';
    h += '<div class="cond" style="margin-top:8px">解锁条件：' + E(b.cond) + '</div>';
    h += '<div class="mini"><i style="width:' + pct + '%"></i></div>';
    h += '<div class="pv">当前进度：' + b.have + ' / ' + b.need + '（' + pct + '%）</div>';
    box.innerHTML = h;
    var all = document.querySelectorAll('.badge');
    for (var k = 0; k < all.length; k++) { all[k].classList.remove('sel'); }
    var one = document.querySelector('[data-badge="' + id + '"]');
    if (one) { one.classList.add('sel'); }
  }
  document.addEventListener('click', function(e){
    var el = e.target.closest ? e.target.closest('[data-badge]') : null;
    if (el) { show(el.getAttribute('data-badge')); }
  });
  if (B.length) { show(B[0].id); }
})();
"""


def main():
    _safe_stdout()
    ap = argparse.ArgumentParser(description="生成学期成就页 HTML（N5-b 降级形态）")
    ap.add_argument("input", nargs="?", default=None, help="课表/日程 JSON（可选，用于学期起点）")
    ap.add_argument("--out", default=None, help="输出 HTML 路径（默认用户目录 out/achievements.html）")
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
    s = compute_stats(recs, today, term_start, weeks)
    cur = s["cur_week"]

    badges = []
    for b in badge_defs(s, weeks):
        if b.get("ok") is not None:
            unlocked = bool(b["ok"]) and b["have"] >= b["need"]
        else:
            unlocked = b["have"] >= b["need"]
        badges.append({"id": b["id"], "name": b["name"], "cond": b["cond"],
                       "have": b["have"], "need": b["need"], "unlocked": unlocked,
                       "icon": b["icon"]})
    n_on = sum(1 for b in badges if b["unlocked"])

    # 打卡日历：列 = 周次，行 = 周一至周日
    cal_head = "".join('<div style="text-align:center">%d</div>' % w for w in range(1, weeks + 1))
    cal = ['<div class="cal">']
    for d in range(1, 8):
        cal.append('<div class="cw">')
        for w in range(1, weeks + 1):
            dd = term_start + timedelta(days=(w - 1) * 7 + (d - 1))
            n = s["dates"].get(dd.isoformat(), 0)
            cls = "cc"
            if n == 0:
                cls += " out" if dd > today else ""
            elif n == 1:
                cls += " l1"
            elif n == 2:
                cls += " l2"
            else:
                cls += " l3"
            cal.append('<div class="%s" title="%s 周%d：%d 条"></div>'
                       % (cls, dd.isoformat(), d, n))
        cal.append("</div>")
    cal.append("</div>")
    cal_ticks = ('<div class="pv" style="margin-top:8px">行 = 周一至周日（第 1 行是周一）；'
                 '列 = 第 1 周至第 %d 周。颜色越深当天记录越多，虚线格 = 未来日期。</div>' % weeks)

    wall = "".join(
        '<button type="button" class="badge %s" data-badge="%s">%s'
        '<div class="nm">%s</div><div class="st">%s</div></button>'
        % ("on" if b["unlocked"] else "", b["id"], badge_svg(b["icon"], b["unlocked"]),
           esc(b["name"]), "已解锁" if b["unlocked"] else "未解锁")
        for b in badges)

    notice = ""
    if not lb["exists"] or not recs:
        notice = ('<div class="notice">暂无记录：功劳档案 %s %s。'
                  '所有徽章按「未解锁」显示并给出解锁条件 —— 这不是页面坏了，是还没开始记账。</div>'
                  % (esc(lb["path"] or "(未指定)"),
                     "不存在" if not lb["exists"] else "无有效记录"))

    prog_pct = min(cur / weeks * 100, 100)
    html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="v4-current-week" content="%(cur)d">
<title>学期成就 · 第 %(cur)d 周</title>
<!-- %(sc)s -->
<style>%(css)s</style>
</head>
<body data-v4-view="achievements" data-v4-current-week="%(cur)d" data-v4-term-start="%(ts)s">
<div class="wrap">
  <header class="hd">
    <h1>学期成就 · 第 %(cur)d 周 / 共 %(weeks)d 周</h1>
    <div class="sub">学期进度 + 连击打卡 + 成就徽章墙。全部由本地功劳档案确定性计算，无后端、无账号、无排行榜。</div>
    <div class="meta">
      <span class="chip">学期起点 <b>%(ts)s</b></span>
      <span class="chip cur">当前 <b>第 %(cur)d 周</b></span>
      <span class="chip">徽章 <b>%(n_on)d / 12</b> 已解锁</span>
      <span class="chip">记录 <b>%(total)d</b> 条</span>
    </div>
  </header>

  %(notice)s

  <h2 class="sec">学期进度</h2>
  <div class="panel">
    <div class="prog-row"><span>已过 %(cur)d 周</span><span>剩余 %(left)d 周</span></div>
    <div class="prog"><i style="width:%(prog).1f%%"></i></div>
    <div class="ticks"><span>第 1 周</span><span>第 %(half)d 周</span><span>第 %(weeks)d 周</span></div>
  </div>

  <div class="cards">
    <div class="card"><div class="k">当前连击</div><div class="v">%(streak)d 天</div>
      <div class="d">历史最长 %(maxs)d 天</div></div>
    <div class="card"><div class="k">累计记录</div><div class="v">%(total)d 条</div>
      <div class="d">其中完成 %(done)d 条</div></div>
    <div class="card"><div class="k">累计工时</div><div class="v">%(mins)d 分</div>
      <div class="d">约 %(hours).1f 小时</div></div>
  </div>

  <h2 class="sec">连击打卡日历</h2>
  <div class="panel">
    <div class="calhead">%(calhead)s</div>
    %(cal)s
    %(calticks)s
  </div>

  <h2 class="sec">成就徽章墙（点击徽章查看解锁条件）</h2>
  <div class="split">
    <div class="wall">%(wall)s</div>
    <aside class="side" id="v4-badge-detail"></aside>
  </div>

  <footer class="ft">
    数据来源：功劳档案 %(src)s（用户目录，包内只读）｜ 生成脚本 render_achievements.py ｜
    本文件无外链、无 CDN、无第三方库，全部样式与交互内联。徽章为本地计算结果，不构成任何积分或兑换。
  </footer>
</div>
<script type="application/json" id="v4-badge-data">%(payload)s</script>
<script>%(js)s</script>
</body>
</html>
""" % {
        "cur": cur, "weeks": weeks, "ts": term_start.isoformat(), "n_on": n_on,
        "total": s["total"], "done": s["done"], "streak": s["streak"],
        "maxs": s["max_streak"], "mins": s["minutes"], "hours": s["minutes"] / 60.0,
        "left": max(weeks - cur, 0), "prog": prog_pct, "half": max(weeks // 2, 1),
        "notice": notice, "calhead": cal_head, "cal": "".join(cal),
        "calticks": cal_ticks, "wall": wall, "css": CSS, "sc": SELFCHECK_COMMENT,
        "src": esc(lb["path"] or "(未指定)"),
        "payload": json_for_html([{k: b[k] for k in ("id", "name", "cond", "have", "need", "unlocked")}
                                  for b in badges]),
        "js": JS,
    }

    out = args.out or os.path.join(DEFAULT_OUT_DIR, "achievements.html")
    assert_not_in_package(out)
    ensure_parent(out)
    with open(out, "w", encoding="utf-8", newline="") as f:
        f.write(html)

    print("[OK] 学期成就页已生成")
    print("    产物路径 : %s" % os.path.abspath(out))
    print("    字节数   : %d" % os.path.getsize(out))
    print("    功劳档案 : %s（存在=%s，%d 行，%d 行解析失败）"
          % (args.logbook, lb["exists"], lb["lines"], lb["bad"]))
    print("    学期进度 : 第 %d / %d 周（%.1f%%）" % (cur, weeks, prog_pct))
    print("    连击     : 当前 %d 天 ｜ 历史最长 %d 天" % (s["streak"], s["max_streak"]))
    print("    徽章     : %d / %d 已解锁" % (n_on, len(badges)))
    if args.report:
        print("    ---- 自检标记 ----")
        for mark in ('data-v4-current-week="%d"' % cur, "v4-badge-data",
                     SELFCHECK_COMMENT.split("|")[0].strip()):
            print("      [%s] %s" % ("OK" if mark in html else "FAIL", mark))
        for b in badges:
            print("      [%s] %s %s  %d/%d" % ("ON " if b["unlocked"] else "OFF",
                                               b["id"], b["name"], b["have"], b["need"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
