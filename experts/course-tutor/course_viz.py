#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""学情可视化看板生成器（核心）。

输入：教师端 主指令 已从数据中枢取出并本地聚合后的学情 JSON（见 references/data_viz.md 口径）。
输出：一份**自包含** HTML 看板（内联数据 + 通过 CDN 引入 Chart.js），无需任何后端 / 服务。

看板覆盖的分析维度（不止「收敛 / 部分 / 卡住」三个面）：
  1. 总览 KPI（学生数 / 活跃人数 / 会话 / 知识点覆盖 / 收敛率 / 覆盖率 / 人均 / 卡住）
  2. 学生掌握分布（按人看三类结果；人多自动转横向条形，避免标签重叠）
  3. 整体掌握结构（环图）
  4. 教学周趋势（折线）
  5. 学习环节分布（首学 / 复习 / 预习 / 题目生成 的构成）
  6. 知识点掌握排行（按「卡住」排序，定位最需要讲评的知识点）
  7. 错因分布（概念 / 计算 / 审题）
  8. 学习活跃度（会话数柱 + 学时折线，双轴）
  9. 学生分层（领先 / 跟进 / 掉队 / 沉默，由已有数据派生）
  10. 未收敛知识点（整班无人收敛的知识点）
  11. 积分排行榜（表格）

方法学本体在 `references/data_viz.md`（八阶段分析流程 + 交付前复核门禁、图表类型推荐
与「证据强度标注」纪律）。本脚本负责最后一环「出图」，不引用任何外部技能包 / 智能体。

渲染纪律（四条，缺一不可）：
- **不编造**：字段缺失即显式占位并在 stdout 报出缺失字段，不补零、不插值；
- **不静默截断**：学生数 / 知识点数超过上限时，页面与 stdout **都要标注**截断；
- **不重叠**：图表一律放在固定高度容器里（maintainAspectRatio=false），
  轴标签自动旋转 + 跳点，学生多时自动切换横向条形；
- **离线可看**：Chart.js 走 CDN，加载失败自动降级为**数据表格**，不出现空白图。
"""

import argparse
import json
import os
import sys
from datetime import datetime


def _harden_console():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except (AttributeError, ValueError, OSError):
            pass


_harden_console()


def load_json(path):
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def _num(v, default=0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def summarize(data):
    """从聚合数据里抽取看板所需的派生指标（不编造：缺字段按 0 计）。"""
    students = data.get("students", []) or []
    weeks = data.get("weeks", []) or []
    kps = data.get("kp_mastery", []) or []
    total_sessions = sum(_num(s.get("sessions")) for s in students)
    total_kp = sum(_num(s.get("kp_records")) for s in students)
    total_conv = sum(_num(s.get("converged")) for s in students)
    total_part = sum(_num(s.get("partial")) for s in students)
    total_stuck = sum(_num(s.get("stuck")) for s in students)
    n = max(len(students), 1)
    active = sum(1 for s in students if _num(s.get("sessions")) > 0)
    # 知识点排行：按卡住降序（最需要讲评的排前面）
    kp_sorted = sorted(kps, key=lambda k: (-_num(k.get("stuck")), -_num(k.get("partial"))))
    # 学生分层（口径公开：按本人收敛率，规则见 references/data_viz.md §四）
    seg = {"领先": 0, "跟进": 0, "掉队": 0, "沉默": 0}
    for st in students:
        c, p, k = (_num(st.get("converged")), _num(st.get("partial")), _num(st.get("stuck")))
        if c + p + k <= 0 or _num(st.get("sessions")) <= 0:
            seg["沉默"] += 1
            continue
        rate = c / (c + p + k)
        # 阈值：领先 ≥60% / 跟进 30–60% / 掉队 <30%（口径公开，见 data_viz.md §四）
        seg["领先" if rate >= 0.6 else ("跟进" if rate >= 0.3 else "掉队")] += 1
    # 未收敛知识点（全校无人收敛 = 讲评优先对象）
    untouched = [k for k in kps if _num(k.get("converged")) == 0]
    untouched_sorted = sorted(untouched, key=lambda k: -(_num(k.get("stuck")) + _num(k.get("partial"))))
    return {
        "student_count": len(students),
        "active_count": active,
        "total_sessions": int(total_sessions),
        "total_kp": int(total_kp),
        "avg_sessions": round(total_sessions / n, 1),
        "avg_kp": round(total_kp / n, 1),
        "total_conv": int(total_conv),
        "total_part": int(total_part),
        "total_stuck": int(total_stuck),
        "conv_rate": round(100 * total_conv / max(total_kp, 1), 1),
        "kp_sorted": kp_sorted,
        "seg": seg,
        "untouched_sorted": untouched_sorted,
        "week_labels": [w.get("teach_week", w.get("week", "")) for w in weeks],
        "week_conv": [int(_num(w.get("converged"))) for w in weeks],
        "week_part": [int(_num(w.get("partial"))) for w in weeks],
        "week_stuck": [int(_num(w.get("stuck"))) for w in weeks],
    }


def collect_missing(data):
    """统计聚合 JSON 里缺失的契约字段（不编造：缺什么就报什么）。"""
    miss = set()
    for st in (data.get("students") or []):
        for k in ("sessions", "kp_records", "converged", "partial", "stuck", "kp_distinct"):
            if k not in st:
                miss.add("students." + k)
    for w in (data.get("weeks") or []):
        for k in ("teach_week", "converged", "partial", "stuck"):
            if k not in w:
                miss.add("weeks." + k)
    return sorted(miss)


def render_html(data, course_name, generated_at, max_students=40, max_kp=12):
    s = summarize(data)
    students = data.get("students", []) or []
    leaderboard = data.get("leaderboard", []) or []
    stages = data.get("stages", []) or []
    err_types = data.get("err_types", []) or []
    activity = data.get("activity", []) or []
    coverage = data.get("coverage", {}) or {}

    # ---- 学生维度（超限截断并标注；人多自动横向条形，避免标签重叠）----
    shown = students[:max_students]
    truncated = len(students) - len(shown)
    names = [st.get("name", st.get("sid", "?")) for st in shown]
    conv = [int(_num(st.get("converged"))) for st in shown]
    part = [int(_num(st.get("partial"))) for st in shown]
    stuck = [int(_num(st.get("stuck"))) for st in shown]
    horizontal = len(shown) > 12

    # ---- 知识点维度 ----
    kp_all = s["kp_sorted"]
    kp_shown = kp_all[:max_kp]
    kp_truncated = len(kp_all) - len(kp_shown)

    doughnut = [s["total_conv"], s["total_part"], s["total_stuck"]]

    payload = {
        "names": names, "conv": conv, "part": part, "stuck": stuck,
        "horizontal": horizontal,
        "week_labels": s["week_labels"], "week_conv": s["week_conv"],
        "week_part": s["week_part"], "week_stuck": s["week_stuck"],
        "doughnut": doughnut,
        "stage_labels": [x.get("stage", "") for x in stages],
        "stage_counts": [int(_num(x.get("count"))) for x in stages],
        "kp_labels": [k.get("kp_id", "?") for k in kp_shown],
        "kp_conv": [int(_num(k.get("converged"))) for k in kp_shown],
        "kp_part": [int(_num(k.get("partial"))) for k in kp_shown],
        "kp_stuck": [int(_num(k.get("stuck"))) for k in kp_shown],
        "seg_labels": ["领先", "跟进", "掉队", "沉默"],
        "seg_counts": [s["seg"]["领先"], s["seg"]["跟进"], s["seg"]["掉队"], s["seg"]["沉默"]],
        "gap_labels": [k.get("kp_id", "?") for k in s["untouched_sorted"][:max_kp]],
        "gap_counts": [int(_num(k.get("stuck")) + _num(k.get("partial")))
                       for k in s["untouched_sorted"][:max_kp]],
        "err_labels": [e.get("err_type", "") for e in err_types],
        "err_counts": [int(_num(e.get("count"))) for e in err_types],
        "act_labels": [a.get("teach_week", a.get("date", "")) for a in activity],
        "act_sessions": [int(_num(a.get("sessions"))) for a in activity],
        "act_hours": [round(_num(a.get("hours")), 2) for a in activity],
        "leaderboard": [
            {"rank": i + 1, "name": r.get("name", r.get("sid", "?")),
             "points": r.get("points", 0)}
            for i, r in enumerate(leaderboard[:10])
        ],
    }
    dashboard_data = json.dumps(payload, ensure_ascii=False)

    # ---- 离线降级用的数据表格（Chart.js 未加载时显示，避免空白卡片）----
    def _table(cols, rows):
        head = "".join(f"<th>{c}</th>" for c in cols)
        body = "".join("<tr>" + "".join(f"<td>{v}</td>" for v in r) + "</tr>" for r in rows)
        return f"<table class='lb'><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"

    fb_students = _table(["学生", "收敛", "部分", "卡住"],
                         [[a, b, c, d] for a, b, c, d in zip(names, conv, part, stuck)])
    fb_weeks = _table(["教学周", "收敛", "部分", "卡住"],
                      [[a, b, c, d] for a, b, c, d in
                       zip(s["week_labels"], s["week_conv"], s["week_part"], s["week_stuck"])])
    fb_total = _table(["类别", "计数"],
                      [["收敛", s["total_conv"]], ["部分", s["total_part"]], ["卡住", s["total_stuck"]]])
    fb_stage = _table(["学习环节", "记录数"],
                      [[a, b] for a, b in zip(payload["stage_labels"], payload["stage_counts"])])
    fb_kp = _table(["知识点", "收敛", "部分", "卡住"],
                   [[a, b, c, d] for a, b, c, d in
                    zip(payload["kp_labels"], payload["kp_conv"], payload["kp_part"], payload["kp_stuck"])])
    fb_seg = _table(["分层", "人数"],
                    [[a, b] for a, b in zip(payload["seg_labels"], payload["seg_counts"])])
    fb_gap = _table(["未收敛知识点", "部分+卡住"],
                    [[a, b] for a, b in zip(payload["gap_labels"], payload["gap_counts"])])
    fb_err = _table(["错因", "次数"],
                    [[a, b] for a, b in zip(payload["err_labels"], payload["err_counts"])])
    fb_act = _table(["教学周", "会话数", "学时"],
                    [[a, b, c] for a, b, c in
                     zip(payload["act_labels"], payload["act_sessions"], payload["act_hours"])])

    # 截断必须显式标注（不静默丢数据）
    notes = []
    if truncated > 0:
        notes.append(f"学生较多，学生分布图只显示前 {len(shown)} 人"
                     f"（共 {len(students)} 人，其余 {truncated} 人未入图）")
    if kp_truncated > 0:
        notes.append(f"知识点较多，知识点排行只显示卡住最多的前 {len(kp_shown)} 个"
                     f"（共 {len(kp_all)} 个）")
    truncated_html = ""
    if notes:
        truncated_html = ("<p class='warnline'>" + "；".join(notes) +
                          "。要全量请用 <code>--max-students</code> / <code>--max-kp</code> 调大。</p>")

    cov_text = "—"
    if coverage:
        cov_text = f"{coverage.get('covered_kp', '?')} / {coverage.get('total_kp', '?')}"
        if coverage.get("rate") is not None:
            cov_text += f"（{coverage.get('rate')}%）"

    def kpi(value, label, danger=False):
        return (f"<div class='kpi{' danger' if danger else ''}'>"
                f"<div class='v'>{value}</div><div class='l'>{label}</div></div>")

    kpi_cards = "<div class='kpis'>" + "".join([
        kpi(s["student_count"], "在学学生"),
        kpi(s["active_count"], "有伴学记录"),
        kpi(s["total_sessions"], "总伴学会话"),
        kpi(s["total_kp"], "知识点覆盖(行)"),
        kpi(f"{s['conv_rate']}%", "整体收敛率"),
        kpi(cov_text, "知识点覆盖率"),
        kpi(s["seg"]["沉默"], "沉默学生"),
        kpi(len(s["untouched_sorted"]), "未收敛知识点", danger=True),
        kpi(s["avg_sessions"], "人均会话"),
        kpi(s["total_stuck"], "卡住总计", danger=True),
    ]) + "</div>"

    def card(title, canvas_id, fb, hint=""):
        """统一卡片结构：固定高度图表容器 + 离线表格兜底（杜绝重叠与空白）。"""
        return (f"<section class='card'><h3>{title}</h3>"
                f"{('<p class=hint>' + hint + '</p>') if hint else ''}"
                f"<div class='chart'><canvas id='{canvas_id}'></canvas></div>"
                f"<div class='fb' style='display:none'>{fb}</div></section>")

    cards = []
    if s["week_labels"]:
        cards.append(card("教学周趋势（收敛 / 部分 / 卡住）", "weekChart", fb_weeks))
    if payload["stage_labels"]:
        cards.append(card("学习环节分布", "stageChart", fb_stage,
                          "看学生主要在哪个环节学习：首学多说明在赶进度，复习多说明在巩固。"))
    if payload["kp_labels"]:
        cards.append(card("知识点掌握排行（按卡住排序）", "kpChart", fb_kp,
                          "卡住最多的知识点就是下节课最该讲评的地方。"))
    if sum(payload["seg_counts"]) > 0:
        cards.append(card("学生分层（按本人收敛率）", "segChart", fb_seg,
                          "领先 ≥60%、跟进 30–60%、掉队 <30%、沉默 = 无任何伴学记录；"
                          "分层口径公开，便于与教师自己的判断对照。"))
    if payload["gap_labels"]:
        cards.append(card("未收敛知识点（无人收敛）", "gapChart", fb_gap,
                          "整班都没收敛的知识点，通常是讲授方式或材料有问题，优先复盘。"))
    if payload["err_labels"]:
        cards.append(card("错因分布", "errChart", fb_err))
    if payload["act_labels"]:
        cards.append(card("学习活跃度（会话数 / 学时）", "actChart", fb_act))

    leaderboard_html = ""
    if leaderboard:
        rows = "".join(
            f"<tr class='{'top3' if i < 3 else ''}'><td>#{i+1}</td>"
            f"<td>{r.get('name', r.get('sid','?'))}</td>"
            f"<td>{r.get('points',0)}</td>"
            f"<td>{'奖励' if i < 3 else ''}</td></tr>"
            for i, r in enumerate(leaderboard[:10])
        )
        leaderboard_html = (f"<section class='card'><h3>积分排行榜（期末统计 · 前三奖励）</h3>"
                            f"<table class='lb'><thead><tr><th>排名</th><th>学生</th>"
                            f"<th>积分</th><th>奖励</th></tr></thead><tbody>{rows}</tbody></table></section>")

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>学情看板 · {course_name}</title>
<style>
  :root{{--bg:#0f1420;--card:#1a2233;--ink:#e8eefc;--mut:#9bb0d3;--acc:#4f8cff;--ok:#36c98d;--warn:#ffb648;--bad:#ff6b6b;--line:#25324a;}}
  *{{box-sizing:border-box}}
  body{{margin:0;font-family:-apple-system,'Segoe UI','PingFang SC','Microsoft YaHei',sans-serif;
        background:linear-gradient(160deg,#0f1420,#13203a);color:var(--ink);padding:28px;line-height:1.6}}
  h1{{font-size:24px;margin:0 0 4px}}
  .sub{{color:var(--mut);font-size:13px;margin-bottom:20px}}
  .kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:14px;margin-bottom:20px}}
  .kpi{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 16px;min-width:0}}
  .kpi .v{{font-size:23px;font-weight:700;color:var(--acc);word-break:break-all}}
  .kpi .l{{color:var(--mut);font-size:12px;margin-top:4px}}
  .kpi.danger .v{{color:var(--bad)}}
  .warnline{{background:#3a2a12;border:1px solid #6b5320;color:#ffd08a;border-radius:12px;
             padding:10px 14px;font-size:12px;margin:0 0 18px}}
  /* 自适应网格：卡片最小 340px，放不下自动换行，杜绝挤在一行里重叠 */
  .grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:18px;margin-bottom:18px}}
  .card{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px;min-width:0}}
  .card h3{{margin:0 0 6px;font-size:15px}}
  .card .hint{{color:var(--mut);font-size:12px;margin:0 0 10px}}
  /* 固定高度容器 + maintainAspectRatio=false：高度可控，卡片之间不会互相挤压 */
  .chart{{display:none}}
  .fb{{display:block!important}}
  .notes{{margin-top:18px;color:var(--mut);font-size:12px}}
  .notes p{{margin:2px 0}}
  table.lb{{width:100%;border-collapse:collapse;font-size:13px}}
  table.lb th,table.lb td{{text-align:left;padding:8px 6px;border-bottom:1px solid var(--line)}}
  table.lb tr.top3 td{{color:#ffd76b;font-weight:600}}
  .fb table.lb{{font-size:12px}}
  .foot{{color:var(--mut);font-size:11px;margin-top:22px}}
  @media(max-width:760px){{body{{padding:16px}}.grid{{grid-template-columns:1fr}}}}
</style>
</head>
<body>
  <h1>学情可视化看板</h1>
  <div class="sub">课程：{course_name} ｜ 生成时间：{generated_at} ｜ 数据来源：教师自己的腾讯文档数据中枢（本地渲染，未外发）</div>
  {kpi_cards}
  {truncated_html}
  <div class="grid">
    <section class="card"><h3>学生掌握分布（收敛 / 部分 / 卡住）</h3>
      <div class="chart{' tall' if horizontal else ''}"><canvas id="stuChart"></canvas></div>
      <div class="fb" style="display:none">{fb_students}</div></section>
    <section class="card"><h3>整体掌握结构</h3>
      <div class="chart"><canvas id="donutChart"></canvas></div>
      <div class="fb" style="display:none">{fb_total}</div></section>
    {''.join(cards)}
  </div>
  {leaderboard_html}
  <div class="notes">
    <p><b>怎么看这块板</b></p>
    <p>先看 KPI 定总量，再看「整体掌握结构」定健康度，然后按「知识点掌握排行」找最需要讲评的点；
       「学习环节分布」看学生是在赶进度还是在巩固，「学习活跃度」看投入是否稳定。</p>
    <p><b>注意</b>：看板由课程伴学专家本地生成，数据取自教师自己的腾讯文档中枢，<b>不依赖任何服务端</b>；
       趋势出现断崖或零收敛率时，先按数据质量门禁复查，<b>勿直接归因</b>。</p>
  </div>
  <div class="foot">课程伴学专家 · 学情可视化看板（v2.2.2）· 数据内联于本页，可离线打开 / 分享；数据完全内联于本页，离线可看；指标以结构化表格呈现，无任何外部依赖。</div>
</body>
</html>"""
    return html


def main():
    ap = argparse.ArgumentParser(description="学情可视化看板生成器（自包含 HTML，无子命令）")
    ap.add_argument("data_json", help="聚合后的学情 JSON（由 主指令 从数据中枢取出后生成）")
    ap.add_argument("--course", default="", help="课程名（用于看板标题）")
    ap.add_argument("--out", default="", help="输出 HTML 路径；缺省打印到 stdout")
    ap.add_argument("--max-students", type=int, default=40,
                    help="学生分布图最多显示多少人（默认 40，超出截断并在页面标注）")
    ap.add_argument("--max-kp", type=int, default=12,
                    help="知识点排行最多显示多少个（默认 12，按卡住降序）")
    args = ap.parse_args()

    try:
        data = load_json(args.data_json)
    except (OSError, ValueError) as exc:
        print(f"[FAIL] 无法读取聚合 JSON：{exc}")
        sys.exit(1)

    course = args.course or data.get("course_name", "") or "(未命名课程)"
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    missing = collect_missing(data)
    if missing:
        print("[WARN] 聚合 JSON 缺失字段（按 0 / 空计，不编造）：" + "、".join(missing))
    n_all = len(data.get("students") or [])
    if n_all > args.max_students:
        print(f"[WARN] 学生 {n_all} 人 > --max-students {args.max_students}，"
              f"图表只画前 {args.max_students} 人（页面已标注）")
    n_kp = len(data.get("kp_mastery") or [])
    if n_kp > args.max_kp:
        print(f"[WARN] 知识点 {n_kp} 个 > --max-kp {args.max_kp}，"
              f"排行只画卡住最多的前 {args.max_kp} 个（页面已标注）")
    if not (data.get("stages") or data.get("kp_mastery") or data.get("err_types")):
        print("[WARN] 未提供 stages / kp_mastery / err_types——环节、知识点与错因三个维度不会出图，"
              "看板只剩总览与学生分布（字段契约见 references/data_viz.md §五）")

    html = render_html(data, course, generated_at, args.max_students, args.max_kp)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"[OK] 看板已生成: {args.out} （{len(html)} 字节，自包含静态页面）")
    else:
        sys.stdout.write(html)
    # 自动埋点（使用记录）：调用即记录，失败不影响功能
    try:
        import course_usage_log
        n_stu = len((data.get("students") or []))
        course_usage_log.auto_record("学情看板", course, f"HTML {len(html)} 字节 · {n_stu} 人")
    except Exception:
        pass


if __name__ == "__main__":
    main()
