#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""发文量统计与趋势分析（整库或单个主题子集）。

## 解决什么问题

用户常见的两类诉求，此前包内没有对应产物：

1. **「这个领域一年发多少篇？」** —— 需要逐年发文量、总发文量，
   单纯的 `age_warning` 只给"最旧文献预警"，不给趋势。
2. **「只看某一个主题的题录，能分析吗？」** —— 用户手上可能只有一个
   细分方向的题录（如"工作重塑"专题库），却只能跑整库分析。

故本脚本提供：
    · `--topic <名称或关键词>` 只统计匹配该主题的题录（子集分析）
    · 逐年发文量、年份跨度、峰值年、增长趋势、拐点年份
    · 年份 × 主题的交叉（若给了 topics），支撑"哪个主题在扩张"

## 口径说明（重要）

* **总发文量**= 题录条数（去重前）。若传入 `--dedup` 则先按 DOI/标题去重。
* **年份缺失**的题录不计入逐年分布，但计入总数——因此
  `sum(逐年) <= 总数`，差额即为缺年份条数，报告里显式给出。
* 趋势判断用**前后段增长率**而非拟合线（文献量小、波动大时更稳健）。
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from lit_core import EXIT, load_refs  # noqa: E402


def _year_of(r):
    y = getattr(r, "year", None)
    try:
        return int(y) if y else None
    except (TypeError, ValueError):
        return None


def _match_topic(r, pattern: str) -> bool:
    """子集匹配：标题/摘要/关键词任一包含 pattern 即命中（不区分大小写）。"""
    p = pattern.lower()
    for f in ("title", "abstract", "journal"):
        v = getattr(r, f, None)
        if v and p in str(v).lower():
            return True
    kw = getattr(r, "keywords", None) or []
    for k in kw:
        if p in str(k).lower():
            return True
    return False


def analyze(refs, label: str = "全库", match=None) -> dict:
    """计算发文量统计与趋势。match: 可选的筛选函数。"""
    if match is not None:
        refs = [r for r in refs if match(r)]
    total = len(refs)
    yc = Counter()
    no_year = 0
    for r in refs:
        y = _year_of(r)
        if y is None:
            no_year += 1
        else:
            yc[y] += 1

    years = sorted(yc)
    per_year = {str(y): yc[y] for y in years}
    span = (years[0], years[-1]) if years else (None, None)

    # ── 趋势判断：用前后段增长率，比线性拟合稳健 ──
    # 段长取「至少 2 年」以免单年噪声主导判断。
    trend = "数据不足"
    yoy = []          # 逐年环比增速（%）
    growth = None
    peak_year = None
    turning = []      # 拐点：增速由正转负或反之
    if len(years) >= 3:
        peak_year = max(years, key=lambda y: yc[y])
        seg = max(2, len(years) // 3)
        first_seg = years[:seg]
        last_seg = years[-seg:]
        a = sum(yc[y] for y in first_seg)
        b = sum(yc[y] for y in last_seg)
        if a > 0:
            growth = round((b - a) / a * 100, 1)
            if b > a * 1.25:
                trend = "上升"
            elif b < a * 0.8:
                trend = "下降"
            else:
                trend = "平稳"
        for i in range(1, len(years)):
            prev, cur = yc[years[i - 1]], yc[years[i]]
            if prev > 0:
                yoy.append({
                    "year": years[i],
                    "from": prev, "to": cur,
                    "pct": round((cur - prev) / prev * 100, 1),
                })
        # 拐点：连续两年方向反转
        for i in range(1, len(yoy) - 1):
            a1, b1 = yoy[i - 1]["pct"], yoy[i]["pct"]
            if a1 > 0 >= b1 or a1 <= 0 < b1:
                turning.append(yoy[i]["year"])

    # 连续增长年数（当前仍在扩张？用最后 3 年的方向判断）
    recent = years[-3:]
    growing = len(recent) >= 2 and all(
        yc[recent[i]] >= yc[recent[i - 1]] for i in range(1, len(recent))
    )
    if len(recent) >= 2 and yc[recent[-1]] < yc[recent[-2]]:
        growing = False

    return {
        "ok": True,
        "label": label,
        "total": total,
        "with_year": total - no_year,
        "missing_year": no_year,
        "missing_year_pct": round(no_year / total * 100, 1) if total else 0.0,
        "year_range": list(span),
        "span_years": (span[1] - span[0] + 1) if span[0] else 0,
        "per_year": per_year,
        "peak_year": peak_year,
        "peak_count": yc.get(peak_year, 0) if peak_year else None,
        "mean_per_year": round(total / len(years), 1) if years else 0.0,
        "trend": trend,
        "growth_pct": growth,
        "yoy": yoy,
        "turning_years": turning,
        "currently_growing": growing if len(years) >= 2 else None,
    }


def _readout(st) -> list[str]:
    """把统计量翻成人话结论（报告直接展示）。"""
    out = []
    if not st["total"]:
        return ["题录为空，无法统计发文量。"]
    out.append(f"共 <b>{st['total']:,}</b> 篇"
               + (f"（其中 {st['missing_year']} 篇缺年份，"
                  f"占 {st['missing_year_pct']}%）" if st["missing_year"] else ""))
    if st["year_range"][0]:
        out.append(f"时间跨度 {st['year_range'][0]}–{st['year_range'][1]}"
                   f"（{st['span_years']} 年），年均约 {st['mean_per_year']} 篇。")
    if st["peak_year"]:
        out.append(f"发文高峰在 <b>{st['peak_year']}</b> 年（{st['peak_count']} 篇）。")
    if st["trend"] != "数据不足":
        g = st["growth_pct"]
        gtxt = f"（末段较首段 {g:+.0f}%）" if g is not None else ""
        out.append(f"整体趋势<b>{st['trend']}</b>{gtxt}。")
    if st["currently_growing"] is True:
        out.append("近三年逐年递增，仍在扩张期。")
    elif st["currently_growing"] is False:
        out.append("最近一年较上年回落，需留意是否进入平台期。")
    if st["turning_years"]:
        out.append("增速方向反转的年份："
                   + "、".join(str(y) for y in st["turning_years"]) + "。")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(
        description="发文量统计与趋势分析（支持只分析某一个主题的题录）")
    ap.add_argument("target", help="题录：.json 产物 / 题录库 / 题录文件")
    ap.add_argument("--workspace", default="./.lit_work")
    ap.add_argument("--out", default="./out")
    ap.add_argument("--topic", help="只统计匹配该主题/关键词的题录（子集分析）")
    ap.add_argument("--topics", help="topics.json（可选，用于年份 × 主题交叉）")
    ap.add_argument("--json-out", default="publication_stats.json")
    args = ap.parse_args()

    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)

    try:
        refs, meta = load_refs(args.target, args.workspace)
    except Exception as e:  # noqa: BLE001
        print(f"[error] 题录装载失败: {e}", file=sys.stderr)
        print(f"[hint] {EXIT[1]}", file=sys.stderr)
        return 1

    if not refs:
        print("[error] 题录为空", file=sys.stderr)
        return 4

    match = (lambda r: _match_topic(r, args.topic)) if args.topic else None
    if args.topic:
        subset = [r for r in refs if match(r)]
        if not subset:
            print(f"[error] 没有题录匹配主题「{args.topic}」——"
                  f"请换个关键词，或去掉 --topic 做全库统计", file=sys.stderr)
            print(f"[hint] {EXIT[4]}", file=sys.stderr)
            return 4
        st = analyze(subset, label=f"主题：{args.topic}")
    else:
        st = analyze(refs, label="全库")

    st["library"] = meta.get("display_path")
    st["source"] = meta.get("source")
    st["source_label"] = meta.get("source_label")
    st["readout"] = _readout(st)

    # 年份 × 主题交叉（若给了 topics）
    if args.topics and Path(args.topics).exists():
        try:
            td = json.loads(Path(args.topics).read_text(encoding="utf-8"))
            # clusters[].members/ids 视产物结构而定，容错取用
            cyc = defaultdict(Counter)
            for c in td.get("clusters", []):
                cid = c.get("cluster_id")
                members = c.get("members") or c.get("ids") or []
                for mid in members:
                    for r in refs:
                        rid = getattr(r, "id", None) or getattr(r, "_id", None)
                        if rid == mid or str(rid) == str(mid):
                            y = _year_of(r)
                            if y:
                                cyc[cid][y] += 1
            if cyc:
                st["topic_year_matrix"] = {
                    str(c): {str(y): n for y, n in sorted(v.items())}
                    for c, v in cyc.items()
                }
        except Exception:  # noqa: BLE001
            # 交叉是增强项，失败不阻塞主产物
            st["topic_year_matrix"] = {}

    (outdir / args.json_out).write_text(
        json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(
        {k: st[k] for k in ("label", "total", "year_range", "peak_year",
                            "trend", "growth_pct", "currently_growing")},
        ensure_ascii=False))
    for line in st["readout"]:
        print("  · " + line, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())