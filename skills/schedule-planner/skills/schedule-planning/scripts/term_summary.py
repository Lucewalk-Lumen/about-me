#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
term_summary.py — N5-c 学期总结：聚合功劳档案 + 学期周次，输出 Markdown（可选 HTML）。

设计目的
--------
回答「我这一学期到底做成了什么」。功劳档案是流水账，总结是把它按周 / 按月 / 按优先级
重新聚合，并把「事实错误」类归因单列出来交回 fact-verifier 重核。

能力
----
  * 完成率三口径：任务数 / 工时 / P0（P0 单列一节）
  * 连击：当前连击与历史最长连击
  * 按周聚合表、按月聚合表
  * 归因六类分布（含「无偏差」与「事实错误」）
  * 事实错误项清单 → 回退 fact-verifier 重核
  * 产物：Markdown 版（默认）+ 可选 HTML 版

数据来源
--------
功劳档案 `%USERPROFILE%/.schedule-planner/logbook.jsonl`（JSONL append-only，用户目录，包内只读）。
**档案不存在或为空时优雅降级**：输出「暂无记录」版总结（结构与正常版一致，数值为 0），
退出码仍为 0，不抛异常。

约束（P0 红线）：仅标准库 / 无 CDN 外链 / 无第三方图表库 / 无 emoji / utf-8-sig 读输入。

用法
----
    python term_summary.py --out term-summary.md
    python term_summary.py --logbook ~/.schedule-planner/logbook.jsonl --out term-summary.md --html term-summary.html
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


def week_of(d, term_start, weeks):
    delta = (d - term_start).days
    if delta < 0 or delta >= weeks * 7:
        return None
    return delta // 7 + 1


def aggregate(recs, term_start, weeks, today):
    a = {
        "total": 0, "done": 0, "partial": 0, "skipped": 0,
        "planned": 0, "actual": 0, "done_actual": 0, "done_planned": 0,
        "minutes_total": 0,
        "p0_total": 0, "p0_done": 0, "p0_items": [],
        "attr": {k: 0 for k, _ in ATTRIBUTION}, "fact_errors": [],
        "by_week": {}, "by_month": {}, "dates": set(),
        "streak": 0, "max_streak": 0, "undated": 0,
    }
    for r in recs:
        a["total"] += 1
        st = str(r.get("status", "")).lower()
        if st == "done":
            a["done"] += 1
        elif st == "partial":
            a["partial"] += 1
        elif st == "skipped":
            a["skipped"] += 1
        pl, ac = rec_min(r, "planned_minutes"), rec_min(r, "actual_minutes")
        a["planned"] += pl
        a["actual"] += ac
        a["minutes_total"] += rec_int(r, "minutes")
        if st == "done":
            a["done_actual"] += ac
            a["done_planned"] += pl
        pri = str(r.get("priority", "")).upper()
        if pri == "P0":
            a["p0_total"] += 1
            if st == "done":
                a["p0_done"] += 1
            a["p0_items"].append({
                "date": r.get("date", ""), "title": r.get("title", ""),
                "status": st, "planned": pl, "actual": ac,
                "attribution": r.get("attribution", "")})
        at = str(r.get("attribution", "none") or "none").lower()
        if at in a["attr"]:
            a["attr"][at] += 1
        if at == "fact_error":
            a["fact_errors"].append({
                "id": r.get("id", ""), "date": r.get("date", ""),
                "title": r.get("title", ""), "refs": r.get("fact_refs", []) or []})
        d = rec_date(r)
        if d is None:
            a["undated"] += 1
            continue
        a["dates"].add(d)
        w = week_of(d, term_start, weeks)
        if w:
            bw = a["by_week"].setdefault(w, {"n": 0, "done": 0, "planned": 0, "actual": 0})
        bm = a["by_month"].setdefault(d.strftime("%Y-%m"), {"n": 0, "done": 0, "planned": 0, "actual": 0})
        bm["n"] += 1
        if st == "done":
            bm["done"] += 1
        bm["planned"] += pl
        bm["actual"] += ac
        if w:
            bw["n"] += 1
            if st == "done":
                bw["done"] += 1
            bw["planned"] += pl
            bw["actual"] += ac

    a["rate_task"] = (a["done"] / a["total"] * 100) if a["total"] else 0.0
    # 工时完成率 = Σ planned(done) / Σ planned(全部)，与 render_dashboard.py 同口径（计划加权）。
    # 不用「实际/实际」：慢工会虚高完成率；不用「实际/计划」：分子分母不同源、可越过 100%。
    # 零分母纪律：Σplanned == 0 → None（无计划工时），不得回 0.0%；
    # done == 0 但 Σplanned > 0 → 真正的 0.0%。两者必须区分。
    a["rate_min"] = (a["done_planned"] / a["planned"] * 100) if a["planned"] else None
    a["rate_input"] = (a["actual"] / a["planned"] * 100) if a["planned"] else None
    a["rate_p0"] = (a["p0_done"] / a["p0_total"] * 100) if a["p0_total"] else 0.0
    if a["dates"]:
        latest = max(a["dates"])
        cur, k = latest, 0
        while cur in a["dates"]:
            k += 1
            cur -= timedelta(days=1)
        a["streak"] = 0 if (today - latest).days > 1 else k
        best, run, prev = 0, 0, None
        for d in sorted(a["dates"]):
            run = run + 1 if (prev and (d - prev).days == 1) else 1
            best = max(best, run)
            prev = d
        a["max_streak"] = best
        a["first"] = min(a["dates"]).isoformat()
        a["last"] = latest.isoformat()
    else:
        a["first"] = a["last"] = ""
    a["cur_week"] = week_of(today, term_start, weeks) or 1
    return a


def pct(x):
    return "%.1f%%" % x


def fmt_rate(x):
    """工时类比率格式化：None（无计划工时，维度缺失）显示「—（无计划工时）」，否则 '%.1f%%'。

    对应零分母纪律：Σplanned == 0 时返回 None（不是 0.0%）—— 与 logbook.py 的
    minutes_rate/effort_ratio 零分母返回 None 对齐。done == 0 但 Σplanned > 0 时
    返回真正的 0.0%，不被误判为「无计划工时」。
    """
    if x is None:
        return "—（无计划工时）"
    return "%.1f%%" % x


def build_markdown(a, ctx):
    L = []
    ts, weeks = ctx["term_start"], ctx["weeks"]
    L.append("# 学期总结")
    L.append("")
    L.append("- 学期起点：%s" % ts.isoformat())
    L.append("- 学期窗口：%s ~ %s（%d 周）" % (ts.isoformat(),
                                          (ts + timedelta(days=weeks * 7 - 1)).isoformat(), weeks))
    L.append("- 当前周次：第 %d 周" % a["cur_week"])
    L.append("- 功劳档案：`%s`" % (ctx["lb"]["path"] or "(未指定)"))
    L.append("- 生成时间：%s" % datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    L.append("")

    if not a["total"]:
        reason = "档案文件不存在" if not ctx["lb"]["exists"] else "档案存在但无有效记录"
        L.append("> **暂无记录**：%s（%s）。以下指标全部为 0，结构保持不变，"
                 "待 logbook.py add 写入记录后重跑即可。" % (reason, ctx["lb"]["path"]))
        L.append("")
    else:
        L.append("记录跨度：%s ~ %s，共 %d 条（完成 %d / 部分 %d / 跳过 %d）。"
                 % (a["first"], a["last"], a["total"], a["done"], a["partial"], a["skipped"]))
        L.append("")

    L.append("## 1. 完成率三口径")
    L.append("")
    L.append("| 口径 | 分子 / 分母 | 完成率 |")
    L.append("|---|---|---|")
    L.append("| 任务数 | %d / %d | %s |" % (a["done"], a["total"], pct(a["rate_task"])))
    L.append("| 工时（计划加权） | %d / %d 分钟 | %s |"
             % (a["done_planned"], a["planned"], fmt_rate(a["rate_min"])))
    L.append("| P0 | %d / %d 项 | %s |" % (a["p0_done"], a["p0_total"], pct(a["rate_p0"])))
    L.append("")
    L.append("工时口径说明：完成率 = 已完成任务的**计划**工时 / 全部任务的计划工时（计划加权，"
             "全部完成即 100%%）。另有工时投入率 %s（实际投入 %d / 计划 %d 分钟），"
             ">100%% 表示估时偏低，属估时偏差信号，不是完成率。"
             % (fmt_rate(a["rate_input"]), a["actual"], a["planned"]))
    L.append("总投入（Σ记录分钟）：%d 分（其中 Σactual_minutes %d 分）—— 与 logbook.py minutes_total 对齐。"
             % (a["minutes_total"], a["actual"]))
    L.append("")
    if a["partial"]:
        L.append("> 部分记录：%d 条 partial 未计完成（无 progress 字段，按 0 计入）"
                 "—— 工时完成率仅统计 done 的计划工时。" % a["partial"])
        L.append("")
    L.append("连击：当前 %d 天，历史最长 %d 天。" % (a["streak"], a["max_streak"]))
    L.append("")

    L.append("## 2. 按周聚合")
    L.append("")
    if a["by_week"]:
        L.append("| 周次 | 记录 | 完成 | 完成率 | 计划工时 | 实际工时 |")
        L.append("|---|---|---|---|---|---|")
        for w in sorted(a["by_week"]):
            g = a["by_week"][w]
            L.append("| 第 %d 周 | %d | %d | %s | %d | %d |"
                     % (w, g["n"], g["done"], pct(g["done"] / g["n"] * 100 if g["n"] else 0),
                        g["planned"], g["actual"]))
    else:
        L.append("暂无按周数据。")
    L.append("")

    L.append("## 3. 按月聚合")
    L.append("")
    if a["by_month"]:
        L.append("| 月份 | 记录 | 完成 | 完成率 | 计划工时 | 实际工时 |")
        L.append("|---|---|---|---|---|---|")
        for m in sorted(a["by_month"]):
            g = a["by_month"][m]
            L.append("| %s | %d | %d | %s | %d | %d |"
                     % (m, g["n"], g["done"], pct(g["done"] / g["n"] * 100 if g["n"] else 0),
                        g["planned"], g["actual"]))
    else:
        L.append("暂无按月数据。")
    L.append("")

    L.append("## 4. P0 单列")
    L.append("")
    if a["p0_items"]:
        L.append("| 日期 | 任务 | 状态 | 计划 | 实际 | 归因 |")
        L.append("|---|---|---|---|---|---|")
        for it in a["p0_items"]:
            L.append("| %s | %s | %s | %d | %d | %s |"
                     % (it["date"], it["title"], it["status"], it["planned"], it["actual"],
                        it["attribution"]))
    else:
        L.append("暂无 P0 记录。")
    L.append("")

    L.append("## 5. 归因分布")
    L.append("")
    L.append("| 归因 | 条数 | 占比 |")
    L.append("|---|---|---|")
    for k, label in ATTRIBUTION:
        n = a["attr"][k]
        L.append("| %s | %d | %s |" % (label, n, pct(n / a["total"] * 100 if a["total"] else 0)))
    L.append("")

    L.append("## 6. 事实错误项（回退 fact-verifier 重核）")
    L.append("")
    if a["fact_errors"]:
        for x in a["fact_errors"]:
            L.append("- %s｜%s｜%s｜事实编号：%s" % (x["date"], x["title"], x["id"],
                                                  ", ".join(x["refs"]) or "-"))
    else:
        L.append("无事实错误归因记录。")
    L.append("")
    L.append("---")
    L.append("")
    L.append("生成脚本：`term_summary.py` ｜ 数据来源：本地功劳档案（用户目录，包内只读）")
    return "\n".join(L) + "\n"


CSS = """
:root{--bg:#f6f7f9;--panel:#fff;--ink:#1f2328;--muted:#5b6470;--faint:#8b949e;
 --line:#e3e6ea;--line2:#eef0f3;--accent:#2f6feb;--accent-soft:#e8f0fe;--accent-ink:#1b4bb8;
 --warn:#8a5300;--warn-bg:#fdf3e2;--warn-line:#f0d9ac}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
 font-family:"Segoe UI","Microsoft YaHei","PingFang SC",system-ui,sans-serif;font-size:14px;line-height:1.7}
.wrap{max-width:960px;margin:0 auto;padding:24px 20px 56px}
header.hd{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:18px 20px;margin-bottom:16px}
h1{margin:0 0 6px;font-size:19px;font-weight:650}
h2{font-size:16px;margin:22px 0 10px;font-weight:650;padding-bottom:6px;border-bottom:1px solid var(--line)}
.sub{color:var(--muted);font-size:13px}
.notice{background:var(--warn-bg);border:1px solid var(--warn-line);color:var(--warn);
 border-radius:10px;padding:12px 16px;margin-bottom:16px;font-size:13px}
.notice.soft{background:#eef2f7;border:1px solid var(--line);color:var(--muted)}
table{width:100%;border-collapse:collapse;background:var(--panel);border:1px solid var(--line);
 border-radius:10px;overflow:hidden;font-size:13px;margin-bottom:8px}
th,td{padding:8px 12px;border-bottom:1px solid var(--line2);text-align:left;font-variant-numeric:tabular-nums}
th{background:#fafbfc;color:var(--muted);font-weight:600;font-size:12px}
tr:last-child td{border-bottom:0}
.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:12px 0}
@media(max-width:760px){.cards{grid-template-columns:1fr}}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px 16px}
.card .k{color:var(--muted);font-size:12px}
.card .v{font-size:24px;font-weight:650;font-variant-numeric:tabular-nums}
ul{margin:0;padding-left:22px}
li{color:var(--muted);font-size:13px}
footer.ft{margin-top:16px;color:var(--faint);font-size:12px}
"""


def build_html(a, ctx, md):
    cards = ('<div class="cards">'
             '<div class="card"><div class="k">任务数完成率</div><div class="v">%s</div>'
             '<div class="k">%d / %d 条</div></div>'
             '<div class="card"><div class="k">工时完成率（计划加权）</div><div class="v">%s</div>'
             '<div class="k">已完成计划 %d / 总计划 %d 分钟<br>实际投入 %d 分钟（投入率 %s）</div></div>'
             '<div class="card"><div class="k">P0 完成率</div><div class="v">%s</div>'
             '<div class="k">%d / %d 项</div></div></div>'
             % (pct(a["rate_task"]), a["done"], a["total"],
                fmt_rate(a["rate_min"]), a["done_planned"], a["planned"],
                a["actual"], fmt_rate(a["rate_input"]),
                pct(a["rate_p0"]), a["p0_done"], a["p0_total"]))

    def table_from_md(section):
        """把 Markdown 段落里的小表格转成 HTML 表格（仅本脚本产出的固定格式）。"""
        rows = [l for l in section.split("\n") if l.startswith("|")]
        if len(rows) < 2:
            return '<div class="sub">暂无数据。</div>'
        cells = [r.strip("|").split("|") for r in rows]
        head, body = cells[0], cells[2:]
        h = "<table><thead><tr>%s</tr></thead><tbody>%s</tbody></table>" % (
            "".join("<th>%s</th>" % esc(c.strip()) for c in head),
            "".join("<tr>%s</tr>" % "".join("<td>%s</td>" % esc(c.strip()) for c in r) for r in body))
        return h

    md_sections = md.split("\n## ")
    def sec(name):
        for s in md_sections:
            if s.startswith(name):
                return s
        return ""

    notice = ""
    if not a["total"]:
        notice = ('<div class="notice">暂无记录：功劳档案 %s。任务数 / P0 为 0，'
                  '工时类（无计划工时）按「—（无计划工时）」显示，结构保持不变。</div>'
                  % esc(ctx["lb"]["path"] or "(未指定)"))

    fe = ""
    if a["fact_errors"]:
        fe = "<ul>%s</ul>" % "".join(
            "<li>%s｜%s｜%s｜事实编号 %s</li>"
            % (esc(x["date"]), esc(x["title"]), esc(x["id"]), esc(", ".join(x["refs"]) or "-"))
            for x in a["fact_errors"])
    else:
        fe = '<div class="sub">无事实错误归因记录。</div>'

    # partial 提示：partial 记录无 progress 字段，按 0 计入完成率（不插值、不取 0.5）
    phint = ""
    if a["partial"]:
        phint = ('<div class="notice soft">partial %d 条未计完成（无 progress 字段，按 0 计入）'
                 '—— 工时完成率仅统计 done 的计划工时。</div>' % a["partial"])

    return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="v4-current-week" content="%(cw)d">
<title>学期总结 · 第 %(cw)d 周</title>
<!-- %(sc)s -->
<style>%(css)s</style>
</head>
<body data-v4-view="term-summary" data-v4-current-week="%(cw)d" data-v4-term-start="%(ts)s">
<div class="wrap">
  <header class="hd">
    <h1>学期总结 · 第 %(cw)d 周</h1>
    <div class="sub">学期窗口 %(a)s ~ %(b)s（%(weeks)d 周）｜ 功劳档案 %(src)s ｜ 生成于 %(now)s</div>
  </header>

  %(notice)s
  %(cards)s
  %(phint)s

  <h2>按周聚合</h2>%(tw)s
  <h2>按月聚合</h2>%(tm)s
  <h2>P0 单列</h2>%(tp)s
  <h2>归因分布</h2>%(ta)s
  <h2>事实错误项（回退 fact-verifier 重核）</h2>%(fe)s

  <footer class="ft">
    生成脚本 term_summary.py ｜ 数据来源：本地功劳档案（用户目录，包内只读）｜
    本文件无外链、无 CDN、无第三方库，全部样式内联。
  </footer>
</div>
</body>
</html>
""" % {
        "cw": a["cur_week"], "ts": ctx["term_start"].isoformat(), "weeks": ctx["weeks"],
        "a": ctx["term_start"].isoformat(),
        "b": (ctx["term_start"] + timedelta(days=ctx["weeks"] * 7 - 1)).isoformat(),
        "src": esc(ctx["lb"]["path"] or "(未指定)"),
        "now": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "notice": notice, "cards": cards, "phint": phint,
        "tw": table_from_md(sec("2. 按周聚合")), "tm": table_from_md(sec("3. 按月聚合")),
        "tp": table_from_md(sec("4. P0 单列")), "ta": table_from_md(sec("5. 归因分布")),
        "fe": fe, "css": CSS, "sc": SELFCHECK_COMMENT,
    }


def main():
    _safe_stdout()
    ap = argparse.ArgumentParser(description="聚合功劳档案，输出学期总结（Markdown + 可选 HTML）")
    ap.add_argument("input", nargs="?", default=None, help="课表/日程 JSON（可选，用于学期起点）")
    ap.add_argument("--out", default=None, help="Markdown 输出路径（默认用户目录 out/term-summary.md）")
    ap.add_argument("--html", default=None, help="可选：HTML 版输出路径")
    ap.add_argument("--logbook", default=DEFAULT_LOGBOOK, help="功劳档案 JSONL 路径")
    ap.add_argument("--term-start", default=None, help="学期起点（YYYY-MM-DD）")
    ap.add_argument("--weeks", type=int, default=20, help="学期总周数")
    ap.add_argument("--today", default=None, help="覆盖「今天」（YYYY-MM-DD）")
    ap.add_argument("--stdout", action="store_true", help="把 Markdown 全文打到标准输出")
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
    a = aggregate(recs, term_start, weeks, today)
    ctx = {"lb": lb, "term_start": term_start, "weeks": weeks, "today": today}
    md = build_markdown(a, ctx)

    out = args.out or os.path.join(DEFAULT_OUT_DIR, "term-summary.md")
    assert_not_in_package(out)
    ensure_parent(out)
    with open(out, "w", encoding="utf-8", newline="") as f:
        f.write(md)

    html_size = None
    if args.html:
        assert_not_in_package(args.html)
        ensure_parent(args.html)
        html = build_html(a, ctx, md)
        with open(args.html, "w", encoding="utf-8", newline="") as f:
            f.write(html)
        html_size = os.path.getsize(args.html)

    print("[OK] 学期总结已生成")
    print("    功劳档案 : %s（存在=%s，%d 行，%d 行解析失败）"
          % (args.logbook, lb["exists"], lb["lines"], lb["bad"]))
    print("    记录条数 : %d（完成 %d / 部分 %d / 跳过 %d）"
          % (a["total"], a["done"], a["partial"], a["skipped"]))
    if a["partial"]:
        print("    部分记录 : %d 条 partial 未计完成（无 progress 字段，按 0 计入）" % a["partial"])
    if a["total"] == 0:
        print("    降级提示 : 暂无记录，已输出结构化空总结（未崩溃）")
    print("    Markdown : %s ｜ %d 字节" % (os.path.abspath(out), os.path.getsize(out)))
    if html_size is not None:
        print("    HTML     : %s ｜ %d 字节" % (os.path.abspath(args.html), html_size))
    print("    完成率   : 任务数 %s ｜ 工时 %s ｜ P0 %s ｜ 工时投入率 %s"
          % (pct(a["rate_task"]), fmt_rate(a["rate_min"]), pct(a["rate_p0"]), fmt_rate(a["rate_input"])))
    print("    总投入   : Σ记录分钟 %d 分（Σactual_minutes %d 分）—— 与 logbook.py minutes_total 对齐"
          % (a["minutes_total"], a["actual"]))
    print("    连击     : 当前 %d 天 ｜ 历史最长 %d 天" % (a["streak"], a["max_streak"]))
    print("    事实错误 : %d 条" % len(a["fact_errors"]))
    if args.report:
        print("    ---- 自检 ----")
        print("      [%s] Markdown 非空" % ("OK" if os.path.getsize(out) > 0 else "FAIL"))
        if a["total"] == 0:
            print("      [%s] 空档案降级含「暂无记录」" % ("OK" if "暂无记录" in md else "FAIL"))
    if args.stdout:
        print()
        print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
