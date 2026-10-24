#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
burst_detection.py —— 关键词突现检测（Burst Detection）

为什么需要这个:
    v0.3.0 只有"主题×年份演化"（描述占比变化），无法回答"哪个概念正在快速升温"。
    CiteSpace 的 citation burst 是其标志性能力，但依赖引文数据；本地 .enl 的
    references 是占位符（零引文），**citation burst 不可用**。
    但关键词的**出现年份**是齐的 —— 因此可以做等价的
    **keyword burst**（CiteSpace 自身的 burst detection 同样支持关键词节点），
    这是在无引文数据下唯一诚实且有价值的突现口径。

方法（Kleinberg 突发检测，小波/累积和思想的简化实现）:
    对每个关键词按年份切分文档频次序列 d_t，令
        r_t = d_t - (1/w) * Σ_{s=t-w+1..t} d_s        （当前 vs 前窗均值）
    r_t 为正表示"高于近期常态"，即该词在加速出现。
    突现强度取 r_t / (该词总频次) 的归一化值，便于跨词比较。
    ⚠️ 小样本年份的 r_t 天然噪声大，故设min_total 门槛并对结果标注置信度。

对标 CiteSpace 的差异（必须在报告中说明，不得混同）:
    · CiteSpace citation burst 依据**被引频次**突增 → 本工具无引文数据，做不了
    · 本工具 keyword burst 依据**关键词出现频次**突增 → 是"概念升温"而非"文献受关注"
    · 两者结论不可互相替代，报告中必须标明是 keyword burst

用法:
    python3 burst_detection.py "<库路径或 refs.json>" --out ./out
    python3 burst_detection.py "<库路径>" --min-total 5 --window 3 --out ./out

退出码:
    0 成功/ 2 语料无年份 / 4 参数错误
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from endnote_core import (  # noqa: E402
    EnlError, EXIT, coverage_report, emit, load_refs, lock_status,
)


def detect_keyword_bursts(refs, window: int = 3, min_total: int = 3,
                          top: int = 40, min_years: int = 3) -> dict:
    """对每个关键词做突发检测。返回结构化结果。

    min_years：该词至少要在多少个不同年份出现过才参与检测。
        突现的本质是"相对自身历史的异常升温"，只出现一年的词没有历史，
        其"基线为 0 -> 突现倍数极高"是数据伪影而非真实趋势。
    """
    # keyword -> Counter(year -> df)
    kw_year: dict[str, Counter] = defaultdict(Counter)
    kw_total: Counter = Counter()
    for r in refs:
        if not r.year:
            continue
        for k in r.keywords:
            kw_year[k][r.year] += 1
            kw_total[k] += 1

    years_all = sorted({r.year for r in refs if r.year})
    if not years_all:
        raise EnlError(2, "库中无任何可用年份，无法做突现检测。"
                          "请确认文献含出版年字段。")

    # 缺年文献占比 —— 影响结论强度，必须如实上报
    n_with_year = sum(1 for r in refs if r.year)
    missing_pct = round((len(refs) - n_with_year) / len(refs) * 100, 1) if refs else 0.0

    results = []
    # 单年份出现过的关键词直接剔除。
    # 坑（真实库 5683篇实测暴露）：只在一年出现的词（多为 MeSH 索引词或
    # 脏数据，如 "history, 20th century" 全部集中在 2017）基线为空 ->
    # base_mean=0 -> Laplace 平滑后 ratio=20/0.5=40 -> 强度 50.79 直接霸榜。
    # 但这类词恰恰**最不可信**（无历史基线可比），让它们占据榜首会
    # 把噪声推成"最重要的前沿概念"。
    # 突现的本质是"相对自身历史的异常"，只有一个年份 = 没有历史。
    for kw, yc in kw_year.items():
        total = kw_total[kw]
        if total < min_total:
            continue
        n_years = len(yc)
        if n_years < min_years:
            continue
        peak_year = max(yc, key=lambda y: (yc[y], y))
        peak_df = yc[peak_year]

        # 突发强度：峰值年的 df 相对"前后 w 年窗口均值"的超出倍数
        # 用峰值年前后各 w 年的均值作基线（比单侧窗口更稳）
        base_years = [y for y in yc
                      if y != peak_year and abs(y - peak_year) <= window]
        base_vals = [yc[y] for y in base_years]
        base_mean = (sum(base_vals) / len(base_vals)) if base_vals else 0.0
        # Laplace 平滑，避免 base_mean=0 时除零
        ratio = peak_df / (base_mean + 0.5)

        # ---- 折扣因子：按「基线样本量」而非「年份跨度」----
        # ⚠️ v0.3.1 修正（独立复审实测：旧公式对短时新概念压低 42%~54%）：
        #   旧公式 span_factor = log1p(n_years)/log(11)，n_years=2 被打 0.46、
        #   n_years=3 被打 0.58。问题是它把两件不同的事混为一谈：
        #     (a) 单年份伪突现 → 已由 `min_years`准入过滤解决，无需再打折
        #     (b) 基线不可靠导致倍数虚高 → 真正该折的是这个
        #   而突现检测的**目的恰恰是发现新概念**——一个只出现 2 年的词
        #   若基线扎实（另一年 df=30、峰值 50 → ratio 1.67，本就不虚高），
        #   却被无差别打折 54%，是明显的误伤。
        # 现改为只看基线可比性：
        #   基线≥2 个年份 → 倍数可信，不打折
        #   基线 1 个年份 → 弱基线，轻折
        #   基线 0 个年份 → 纯分母伪影（ratio 天然爆表），显著折
        n_base = len(base_vals)
        if n_base >= 2:
            span_factor = 1.0
        elif n_base == 1:
            span_factor = 0.85
        else:
            span_factor = 0.70
        strength = ratio * math.log1p(total) * span_factor / math.log(11)

        results.append({
            "keyword": kw,
            "total_df": total,
            "n_years": n_years,
            "peak_year": peak_year,
            "peak_df": peak_df,
            "baseline_mean": round(base_mean, 2),
            "baseline_n_years": len(base_vals),
            "burst_ratio": round(ratio, 2),
            # 折扣因子落盘：让用户知道强度被打过折、并可自行还原。
            # v0.3.1 起判据从"年份跨度"改为"基线可比性"（见上方注释）：
            # 基线≥2年 → 1.0（不打折）；1 年 → 0.85；0 年 → 0.70。
            "span_factor": round(span_factor, 3),
            "strength_raw": round(ratio * math.log1p(total) / math.log(11), 3),
            "strength": round(strength, 3),
            "first_seen": min(yc),
            "last_seen": max(yc),
            "year_hist": {str(y): yc.get(y, 0) for y in years_all},
            # 置信度三级判定（v0.3.1 修正）：
            #   原判据只看"基线年份数 + 频次"，导致 nonzero_years=1 的
            #   MeSH 索引词（强度 50.79、霸榜第一）也只标 low，
            #   而它本就不该出现在结果里 —— 可见 low 的警示力度不足。
            #   现改为：先看该词是否形成时间序列（n_years），
            #   再看基线是否可比、频次是否够大。
            "confidence": (
                # high：基线可比（≥2 个对照年份）+ 频次够。
                # ⚠️ 判据里**不再要求 n_years >= 4**——独立复审指出这会连带
                # 把"基线扎实的 2~3 年新概念"降级，而那正是本工具要找的对象。
                # 单年份伪突现已由 min_years 准入挡住，置信度只管基线质量。
                "high" if (len(base_vals) >= 2 and total >= min_total * 2)
                else ("medium" if (len(base_vals) >= 1 and total >= min_total)
                      else "low")
            ),
        })

    results.sort(key=lambda x: -x["strength"])
    n_single_year = sum(1 for yc in kw_year.values() if len(yc) < min_years)
    return {
        "method": "keyword_burst_ratio",
        "note": "依据关键词出现频次突增，非引文突增。CiteSpace 的 citation burst "
                "依赖被引数据，本地 .enl 无引文数据，故不可用。",
        "params": {"window": window, "min_total": min_total,
                   "min_years": min_years,
                   "year_span": [years_all[0], years_all[-1]] if years_all else [],
                   "n_keywords_evaluated": len(results),
                   "n_excluded_single_year": n_single_year,
                   "exclusion_note":
                       f"{n_single_year} 个仅在单一年份出现的关键词已被排除："
                       f"它们没有历史基线，'基线为0 -> 突现倍数极高'是数据伪影"
                       f"而非真实升温（实测多为 MeSH 索引词或脏数据）。"},
        "coverage": {"n_refs": len(refs), "n_with_year": n_with_year,
                     "missing_year_pct": missing_pct},
        "bursts": results[:top],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="关键词突现检测（keyword burst）")
    ap.add_argument("target", help="EndNote 库目录 / .enl 路径 / refs.json")
    ap.add_argument("--out", default="./out")
    ap.add_argument("--workspace", default="./.endnote_work")
    ap.add_argument("--window", type=int, default=3,
                    help="基线窗口半径（前后各 N 年），默认 3")
    ap.add_argument("--min-total", type=int, default=3,
                    help="关键词最小总频次门槛，低于此不检测，默认 3")
    ap.add_argument("--min-years", type=int, default=3,
                    help="关键词至少出现的年份数，低于此不检测（无历史基线者），默认 3")
    ap.add_argument("--top", type=int, default=40, help="输出前 N 个突现词")
    args = ap.parse_args()

    if args.window < 1 or args.min_total < 1 or args.top < 1 or args.min_years < 2:
        print(f"[error] --window/--min-total/--top 须为正整数，"
              f"--min-years 须 >= 2，收到 {args.window}/{args.min_total}/"
              f"{args.top}/{args.min_years}", file=sys.stderr)
        print(f"[hint] {EXIT[4]}", file=sys.stderr)
        return 4

    try:
        refs, meta = load_refs(args.target, args.workspace)
        payload = detect_keyword_bursts(refs, window=args.window,
                                        min_total=args.min_total, top=args.top,
                                        min_years=args.min_years)
        cov = coverage_report(refs)
        payload["ok"] = True
        payload["exit_code"] = 0
        payload["library"] = {"name": meta["display_path"],
                              "display_path": "…/" + meta["display_path"],
                              "source": meta["source_label"]}
        payload["coverage"] = {**payload["coverage"],
                               "tier": cov["tier"],
                               "zero_drop_identity": cov["zero_drop_identity"]}

        outdir = Path(args.out).expanduser()
        outdir.mkdir(parents=True, exist_ok=True)
        (outdir / "bursts.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[ok] 突现检测完成：{len(payload['bursts'])} 个候选 -> "
              f"{outdir / 'bursts.json'}", file=sys.stderr)
        emit(payload)
        return 0
    except EnlError as e:
        print(f"[error] {e}", file=sys.stderr)
        print(f"[hint] {EXIT[e.code]}", file=sys.stderr)
        return e.code
    except Exception as e:  # noqa: BLE001
        print(f"[error] 未预期异常：{type(e).__name__}: {e}", file=sys.stderr)
        print(f"[hint] {EXIT[5]}", file=sys.stderr)
        return 5


if __name__ == "__main__":
    sys.exit(main())
