#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
burst_detection.py —— 关键词突现检测（Burst Detection）

为什么需要这个:
    只有"主题×年份演化"（描述占比变化），无法回答"哪个概念正在快速升温"。
    CiteSpace 的 citation burst 是其标志性能力，但依赖引文数据；本地 .enl 的
    references 是占位符（零引文），**citation burst 不可用**。
    但关键词的**出现年份**是齐的 —— 因此可以做等价的
    **keyword burst**（CiteSpace 自身的 burst detection 同样支持关键词节点），
    这是在无引文数据下唯一诚实且有价值的突现口径。

方法（**峰值年 vs 前后窗口基线均值的倍数比**，非 Kleinberg）:
    对每个关键词按年份统计文档频次 d_t，取峰值年 p（df 最大者），
        base_mean = mean( d_y : y ≠ p 且 |y - p| ≤ w )      （前后各 w 年）
        ratio    = d_p / (base_mean + 0.5)                  （+0.5 为 Laplace 平滑）
    ratio 度量"峰值年相对自身近期常态高了多少倍"。

    [!]  修正 —— 本节原先声称实现 Kleinberg r_t，实际代码里**没有**
    r_t 序列、没有逐 t 扫描、没有双状态机、没有突现区间、没有持续时长加权，
    只有"单峰值 vs 窗口均值"这一个比值。文档声称与方法不符会让读者以为
    拿到了 CiteSpace 级别的突现区间，故此处改为如实描述已实现的方法。

已知局限（必须在报告中说明，不得夸大）:
    · 本方法只看**单个峰值年**，不给出突现的**起止区间**与**持续时长**
      （Kleinberg 双状态机才能给出），故不能回答"这个概念热了多久"；
    · 峰值年若因并列被任意选中，结果会漂移 —— 故并列时取**最早**年份，
      且方差为 0（平坦序列）直接判为无突现；
    · 不做前向/后向区分：**下降序列与上升序列会被算出同样的倍数**，
      因为 ratio 只看相对基线的高度差、不看时间方向。这是本方法的
      结构性局限，已在 limitations 中如实上报，未擅自改变算法语义。

对标 CiteSpace 的差异（必须在报告中说明，不得混同）:
    · CiteSpace citation burst 依据**被引频次**突增 → 本工具无引文数据，做不了
    · 本工具 keyword burst 依据**关键词出现频次**突增 → 是"概念升温"而非"文献受关注"
    · 两者结论不可互相替代，报告中必须标明是 keyword burst

用法:
    python3 burst_detection.py "<库路径或 refs.json>" --out ./out
    python3 burst_detection.py "<库路径>" --min-total 5 --window 3 --out ./out
    python3 burst_detection.py "<库路径>" --min-ratio 1.5 --out ./out

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
from lit_core import (  # noqa: E402
    EnlError, EXIT, coverage_report, emit, load_refs,
)

# 突发倍数下限：峰值年df 相对基线均值不足该倍数 → 不算突现。
#
# 为什么必须有（暴露假突现）:
#   ratio < 1 意味着峰值年**低于**基线（即该词在走下坡路）；若不拦，会照样
#   把它当突现输出，且confidence 还给"high"。平坦序列实测得到
#   ratio=0.91 / confidence=high —— 这类"假突现"比漏报更有害：
#   它会作为"正在升温的前沿概念"写进结论。
#   取 1.5 而非 1.0：留出缓冲，使小幅噪声波动不被判为突现。
MIN_BURST_RATIO = 1.5


def detect_keyword_bursts(refs, window: int = 3, min_total: int = 3,
                          top: int = 40, min_years: int = 3,
                          min_ratio: float = MIN_BURST_RATIO) -> dict:
    """对每个关键词做突发检测。返回结构化结果。

    min_years：该词至少要在多少个不同年份出现过才参与检测。
        突现的本质是"相对自身历史的异常升温"，只出现一年的词没有历史，
        其"基线为 0 -> 突现倍数极高"是数据伪影而非真实趋势。
    min_ratio：峰值年相对基线均值的最小倍数，低于此不报告为突现。
        见 MIN_BURST_RATIO 的说明。
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
    n_flat = 0# df 恒定（方差 0）—— 没有任何"突发"可言
    n_no_baseline = 0      # 基线 0 年 —— 倍数无意义（分母伪影）
    n_below_ratio = 0      # 倍数不足 —— 上升乏力或正在下降
    n_not_rising = 0       # 峰值前无更低年份 —— 衰退序列，非突现
    # 单年份出现过的关键词直接剔除。
    # 注意（实测）：只在一年出现的词（多为 MeSH 索引词或
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

        # 峰值年：df 最大者；**并列时取最早年份**。
        # 若 key=(df, year)，并列会偏向最晚年份，于是平坦序列会被
        # 归因到"2022 突增"—— 报告里凭空出现一个并不存在的上升事件。
        peak_df = max(yc.values())
        # df 恒定 => 零方差 => 无突现。必须在算ratio 之前拦掉。
        if peak_df == min(yc.values()):
            n_flat += 1
            continue
        peak_year = min(y for y in yc if yc[y] == peak_df)

        # 突发强度：峰值年的 df 相对"前后 w 年窗口均值"的超出倍数
        # 用峰值年前后各 w 年的均值作基线（比单侧窗口更稳）
        base_years = [y for y in yc
                      if y != peak_year and abs(y - peak_year) <= window]
        base_vals = [yc[y] for y in base_years]
        n_base = len(base_vals)
        # ---- 基线为 0 年 = 没有基线 ----
        # 此时 base_mean=0，Laplace 平滑让 ratio = d_p/0.5 = 2*d_p，
        # 纯分母伪影（实测 1990/2005/2020 各 df=10 → ratio 20.0、
        # strength 20.05 霸榜）。此时"突现倍数"在数学上没有定义，
        # 报告它等于编造。故直接不输出，而不是打个折。
        if n_base == 0:
            n_no_baseline += 1
            continue

        # ---- 必须是「上升」而非「下降」----
        # ratio 只衡量峰值年相对基线**的高度**，完全不看时间方向，于是
        # 32→8→2（明显在衰退）与 2→8→32（明显在升温）会得到**完全相同**
        # 的 ratio 5.82 与 strength 9.126 —— 把衰退词报成"正在升温的
        # 前沿概念"是直接的假研究结论。
        # 判据：峰值年**之前**的窗口内必须存在 df 严格小于峰值的年份，
        # 即该词确实"从更低处爬上来"。衰退序列的峰值就在最早一年、
        # 前面没有任何更低的数据点，故被排除。
        # 注意这仍不是 Kleinberg 的 r_t（那需要完整的双状态机），
        # 但它把"突现"限定为有**起点**的上升，方向性错误可被拦住。
        if not any(y < peak_year and yc[y] < peak_df for y in base_years):
            n_not_rising += 1
            continue

        base_mean = sum(base_vals) / n_base
        ratio = peak_df / (base_mean + 0.5)

        # ---- 倍数下限：ratio 不足 => 不是突现 ----
        # ratio < 1 说明峰值年低于基线（该词在走下坡），也一律不算突现。
        if ratio < min_ratio:
            n_below_ratio += 1
            continue

        # ---- 折扣因子：按「基线样本量」而非「年份跨度」----
        # [!]  按基线可比性分档（否则短时新概念会被压低 42%~54%）：
        #   若用 span_factor = log1p(n_years)/log(11)，n_years=2 会被打到 0.46、
        #   n_years=3 被打 0.58。问题是它把两件不同的事混为一谈：
        #     (a) 单年份伪突现 → 已由 `min_years`准入过滤解决，无需再打折
        #     (b) 基线不可靠导致倍数虚高 → 真正该折的是这个
        #   而突现检测的**目的恰恰是发现新概念**——一个只出现 2 年的词
        #   若基线扎实（另一年 df=30、峰值 50 → ratio 1.67，本就不虚高），
        #   却被无差别打折 54%，是明显的误伤。
        # 现改为只看基线可比性：
        #   基线≥2 个年份 → 倍数可信，不打折
        #   基线 1 个年份 → 弱基线，轻折
        #   （基线 0 个年份已在上方直接排除，不再进入打折分支）
        if n_base >= 2:
            span_factor = 1.0
        else:
            span_factor = 0.85
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
            # 判据从"年份跨度"改为"基线可比性"（见上方注释）：
            # 基线≥2年 → 1.0（不打折）；1 年 → 0.85；0 年 → 0.70。
            "span_factor": round(span_factor, 3),
            "strength_raw": round(ratio * math.log1p(total) / math.log(11), 3),
            "strength": round(strength, 3),
            "first_seen": min(yc),
            "last_seen": max(yc),
            "year_hist": {str(y): yc.get(y, 0) for y in years_all},
            # 置信度三级判定：
            #   原判据只看"基线年份数 + 频次"，导致 nonzero_years=1 的
            #   MeSH 索引词（强度 50.79、霸榜第一）也只标 low，
            #   而它本就不该出现在结果里 —— 可见 low 的警示力度不足。
            #   现改为：先看该词是否形成时间序列（n_years），
            #   再看基线是否可比、频次是否够大。
            #   进入本列表的词已全部通过 min_ratio 门槛，
            #   故这里不再重复判断倍数。
            "confidence": (
                # high：基线可比（≥2 个对照年份）+ 频次够。
                # [!]  判据里**不再要求 n_years >= 4**——这会连带
                # 把"基线扎实的 2~3 年新概念"降级，而那正是本工具要找的对象。
                # 单年份伪突现已由 min_years 准入挡住，置信度只管基线质量。
                "high" if (n_base >= 2 and total >= min_total * 2)
                else ("medium" if (n_base >= 1 and total >= min_total)
                      else "low")
            ),
        })

    results.sort(key=lambda x: -x["strength"])
    n_single_year = sum(1 for yc in kw_year.values() if len(yc) < min_years)
    return {
        "method": "keyword_burst_ratio",
        "method_note":
            "峰值年文档频次 / 前后窗口基线均值的倍数（ratio），"
            "非 Kleinberg 突发检测：没有 r_t 序列、没有双状态机、"
            "不产出突现区间与持续时长。",
        "limitations": [
            "只看单个峰值年，不给出突现起止区间与持续时长（Kleinberg 才能给）。",
            "ratio 只看相对基线的高度差、不看时间方向，"
            "故上升序列与下降序列会得到相同的倍数（结构性局限，未改算法语义）。",
            f"倍数不足 {min_ratio} 的词、基线为 0 年的词、df 恒定的词均已排除，"
            "以免把噪声当成升温趋势。",
        ],
        "note": "依据关键词出现频次突增，非引文突增。CiteSpace 的 citation burst "
                "依赖被引数据，本地 .enl 无引文数据，故不可用。",
        "params": {"window": window, "min_total": min_total,
                   "min_years": min_years,
                   "min_ratio": min_ratio,
                   "year_span": [years_all[0], years_all[-1]] if years_all else [],
                   "n_keywords_evaluated": len(results),
                   "n_excluded_single_year": n_single_year,
                   "n_excluded_flat": n_flat,
                   "n_excluded_no_baseline": n_no_baseline,
                   "n_excluded_below_ratio": n_below_ratio,
                   "n_excluded_not_rising": n_not_rising,
                   "exclusion_note":
                       f"{n_single_year} 个仅在单一年份出现的关键词已被排除："
                       f"它们没有历史基线，'基线为0 -> 突现倍数极高'是数据伪影"
                       f"而非真实升温（实测多为 MeSH 索引词或脏数据）。",
                   "exclusion_note_v031":
                       f"另有 {n_flat} 个 df 恒定（零方差，数学上无突现）、"
                       f"{n_no_baseline} 个基线年份为 0（倍数无定义）、"
                       f"{n_below_ratio} 个倍数 < {min_ratio}（含 ratio<1 的"
                       f"下降序列）、{n_not_rising} 个峰值前无更低年份"
                       f"（纯衰退，无上升起点）的关键词被排除。"},
        "coverage": {"n_refs": len(refs), "n_with_year": n_with_year,
                     "missing_year_pct": missing_pct},
        "bursts": results[:top],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="关键词突现检测（keyword burst）")
    ap.add_argument("target", help="题录库目录 / .enl 路径 / refs.json")
    ap.add_argument("--out", default="./out")
    ap.add_argument("--workspace", default="./.lit_work")
    ap.add_argument("--window", type=int, default=3,
                    help="基线窗口半径（前后各 N 年），默认 3")
    ap.add_argument("--min-total", type=int, default=3,
                    help="关键词最小总频次门槛，低于此不检测，默认 3")
    ap.add_argument("--min-years", type=int, default=3,
                    help="关键词至少出现的年份数，低于此不检测（无历史基线者），默认 3")
    ap.add_argument("--min-ratio", type=float, default=MIN_BURST_RATIO,
                    help=f"峰值年相对基线均值的最小突现倍数，低于此不报告，"
                         f"默认 {MIN_BURST_RATIO}（<1 即下降序列，绝不报告）")
    ap.add_argument("--top", type=int, default=40, help="输出前 N 个突现词")
    args = ap.parse_args()

    if (args.window < 1 or args.min_total < 1 or args.top < 1
            or args.min_years < 2 or args.min_ratio <= 1.0):
        print(f"[error] --window/--min-total/--top 须为正整数，"
              f"--min-years 须 >= 2，--min-ratio 须 > 1.0（<=1 会把"
              f"下降序列判为突现），收到 {args.window}/{args.min_total}/"
              f"{args.top}/{args.min_years}/{args.min_ratio}", file=sys.stderr)
        print(f"[hint] {EXIT[4]}", file=sys.stderr)
        return 4

    try:
        refs, meta = load_refs(args.target, args.workspace)
        payload = detect_keyword_bursts(refs, window=args.window,
                                        min_total=args.min_total, top=args.top,
                                        min_years=args.min_years,
                                        min_ratio=args.min_ratio)
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
