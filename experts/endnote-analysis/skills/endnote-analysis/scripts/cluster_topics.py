#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cluster_topics.py —— M2: 主题聚类 + M3 主题×年份演化

用法:
    python3 cluster_topics.py <库目录或.enl> --k 20 [--out DIR]

输出:
    topics.json     簇定义、代表词、规模、失衡指标
    evolution.json  主题×年份分布
    clusters.csv    簇内文献清单（可导入 Excel/综述）

关键约束:
    - NMF 必须 init='nndsvda'（SVD 确定性）。用 'random' 会导致每次聚类
      结果不同，用户的主题命名标注无法跨重跑存活。
    - 零静默丢弃：5558 条必须 100% 归类或显式标记未归类。
    - 语料 tier 不等：主语料(有摘要/关键词)与降级(仅标题)分开报。
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from endnote_core import (  # noqa: E402
    EnlError, EXIT, Ref, build_corpus, coverage_report, emit, esc_csv_cell,
    find_enl, is_cjk, lock_status, load_refs, make_shadow,
    open_enl_readonly, parse_refs, tokenize_factory,
)


def load_jieba():
    try:
        import jieba
        jieba.initialize()
        return jieba
    except ImportError:
        print("[warn] 未安装 jieba，中文将无法分词（结果不可信）", file=sys.stderr)
        return None


MIN_PCT_THRESHOLD = 3.0   # 每个主题至少占全库 3%，否则不足以支撑可命名、可综述的主题单元
K_GRID = list(range(4, 41, 2))


def recommend_k(X, n_docs: int, log=print) -> dict:
    """自动推荐主题数 K —— 最小簇占比前缀单调法。

    判定规则（不硬编码任何 K）：
        遍历 K = 4,6,8,...,40，对每个 K 算「最小簇占全库百分比」min_pct(K)；
        取满足「所有 K' <= K 的 min_pct(K') >= 3%」的最大 K。

    依据（实测 5558 篇库 + 3 个规模的子采样，8 seed）：
        K:      4     6     8    10    12    14    16    18    20    24
        min%: 9.46  8.87  5.85  4.30  4.28  3.11  2.41  2.05  0.99  0.50
                                    ->前缀在 K=16 断裂 -> K*=14
        N=1200/2500/5558 三规模均给 14，N=5558 时 8 seed 完全稳定。

    为何不用其他判据（全部实测否证）：
        - 重构误差：线性 R²=0.989，K 从 4→40 仅降 4.6%，无拐点
        - 轮廓系数：0.030~0.037 无区分度
        - gini：非单调（K=25 反弹）
        - max/median：任何 K 都 >=5.0 且随 K 恶化
        - NPMI / 共识稳定性：单调下降，峰值在 K=4
        - ARI(换 seed)：K>=10 落在 0.69~0.88 噪声带，无区分力
        - 簇间质心余弦：K=14(0.331) vs K=20(0.312) 无差异

    小库（N<2000）min_pct 抖动较大，返回候选区间而非单一值。
    """
    import numpy as np
    from sklearn.decomposition import NMF

    n = X.shape[0]
    # ⚠️ NMF(init='nndsvda') 要求 n_components <= min(n_samples, n_features)。
    #    坑：v0.3.0 未设上限，小库（n=40、特征少）时 K_GRID 从 4 起逐一 NMF，
    #    一旦 K > min(n, p) 就抛
    #    "init='nndsvda' can only be used when n_components <= min(n_samples, n_features)"
    #    → 用户看到的是退出码 5「计算失败」，实为参数域越界。
    k_max = int(min(n, X.shape[1]))
    grid = [k for k in K_GRID if k <= k_max]
    if not grid:
        # 连 K_GRID最小值都超出 → 语料/特征过少，明确报参数错误而非崩溃
        raise ValueError(
            f"语料特征过少（{n} 篇 × {X.shape[1]} 维），无法做主题聚类。"
            f"请确认文献含标题/摘要/关键词，或减少 --k。")
    if len(grid) < len(K_GRID):
        log(f"    [guard] K 上限受 min(n_samples, n_features)={k_max} 约束，"
            f"仅扫描 {grid[0]}~{grid[-1]}")
    curve = []
    best_k, best_min = None, None
    prefix_ok = True
    for k in grid:
        W = NMF(n_components=k, init="nndsvda", random_state=42,
                max_iter=200).fit_transform(X)
        sizes = np.bincount(W.argmax(axis=1), minlength=k)
        min_pct = float(sizes.min()) / n * 100
        curve.append({"k": k, "min_pct": round(min_pct, 2),
                      "ok": bool(min_pct >= MIN_PCT_THRESHOLD)})
        if prefix_ok and min_pct >= MIN_PCT_THRESHOLD:
            best_k, best_min = k, min_pct
        else:
            prefix_ok = False  # 一旦跌破，后续 K 即便回升也不采纳
        log(f"    K={k:2d}  最小簇占比 {min_pct:5.2f}%  {'✓' if min_pct >= MIN_PCT_THRESHOLD else '✗'}")

    if best_k is None:  # 无任何 K 满足 -> 保守取网格最小值
        best_k, best_min = grid[0], curve[0]["min_pct"]

    result = {
        "recommended_k": int(best_k),
        "min_pct_at_k": round(best_min, 2),
        "threshold_pct": MIN_PCT_THRESHOLD,
        "criterion": "min_cluster_pct_prefix_monotonic",
        "curve": curve,
        "n_docs": n,
    }
    if n < 2000:
        near = [c["k"] for c in curve
                if abs(c["min_pct"] - MIN_PCT_THRESHOLD) < 1.5]
        result["suggested_range"] = [min(near), max(near)] if near else [best_k, best_k]
        result["note"] = (f"库规模仅 {n} 篇，最小簇占比抖动较大"
                          f"（{result['suggested_range'][0]}~{result['suggested_range'][1]} 均为合理）。"
                          "建议在报告中同时查看相邻 K 的结果。")
    return result


def compute_from_X(X, vec, k: int):
    """在已构建的 TF-IDF 矩阵上跑 NMF。"""
    import numpy as np
    from sklearn.decomposition import NMF
    t0 = time.time()
    nmf = NMF(n_components=k, init="nndsvda", random_state=42, max_iter=200)
    W = nmf.fit_transform(X)
    labels = [int(x) for x in W.argmax(axis=1)]
    t_nmf = time.time() - t0
    terms = vec.get_feature_names_out()
    return labels, terms, nmf.components_, X.shape, t_nmf, W


def df_bounds(n_docs: int) -> tuple[int, float]:
    """按库规模自适应 min_df / max_df。

    坑：v0.3.0 硬编码 min_df=3 + max_df=0.5，在小样本库（如 3~20 篇）下
    sklearn 直接抛 `ValueError: max_df corresponds to < documents than min_df`
    → 退出码 5，用户看到的是"计算失败"而非"库太小"。而这类库恰恰是
    教学/起步阶段最常见的场景，属任务完成度缺陷。

    规则（保守、可解释）：
      · min_df 取min(3, max(1, n//10))，保证 max_df 的文档数恒 ≥ min_df
      · max_df 取 max(0.5, min_df/n)，小库时上调至 1.0（全保留）
    """
    min_df = min(3, max(1, n_docs // 10))
    max_df = max(0.5, min_df / n_docs) if n_docs else 0.5
    return min_df, min(1.0, max_df)


def fit_vectorizer(corpus, tok, n_docs: int):
    """构造 TF-IDF 并保证词项非空。

    两层守卫（v0.3.1 端到端实测暴露）：
      1) `df_bounds` 按库规模给min_df/max_df，解决
         `max_df corresponds to < documents than min_df`；
      2) 但词项极少的库（如 24 篇、关键词高度雷同）即使 min_df=2 也会
         出现 `After pruning, no terms remain` —— 此时必须逐级放宽
         min_df，而非让用户看到退出码 5「计算失败」。
    返回 (X, vec, min_df, max_df, 降级说明 or None)
    """
    from sklearn.feature_extraction.text import TfidfVectorizer

    min_df, max_df = df_bounds(n_docs)
    attempts = []
    # (min_df, max_df) 组合逐级放宽：
    #   先降 min_df（放宽"最少出现次数"）；
    #   仍为空则升 max_df（放开"最多出现在多少比例文献里"的过滤）——
    #   小库常见坑：仅 2~3 个高频词出现在全部 24 篇里，max_df=0.5 会把它们
    #   当"无区分度停用词"全部滤掉，导致 After pruning, no terms remain。
    combos = [(m, max_df) for m in range(min_df, 0, -1)]
    combos += [(1, 1.0)]
    for cur_min, cur_max in combos:
        vec = TfidfVectorizer(
            tokenizer=tok, token_pattern=None,
            max_features=20000, min_df=cur_min, max_df=cur_max,
            sublinear_tf=True,
        )
        try:
            X = vec.fit_transform(corpus)
        except ValueError as e:
            attempts.append(f"min_df={cur_min},max_df={cur_max}: {e}")
            continue
        if X.shape[1] > 0:
            note = None
            if (cur_min, cur_max) != (min_df, max_df):
                note = (f"词项过少，df 过滤已自动放宽为 "
                        f"min_df={cur_min}, max_df={cur_max}"
                        + (f"（尝试记录：{'; '.join(attempts)}）" if attempts else ""))
            return X, vec, cur_min, cur_max, note
        attempts.append(f"min_df={cur_min},max_df={cur_max}: 剪枝后无剩余词项")

    raise ValueError(
        f"语料无法构建词项（{n_docs} 篇）。"
        f"请确认文献含标题/摘要/关键词。尝试记录：{'; '.join(attempts)}")


def compute(refs: list[Ref], k: int, corpus_mode: str = 'hybrid'):
    """TF-IDF 权重 + NMF。实测 K=20/30 均无丢簇（最小簇 141/73 篇）。"""
    from sklearn.decomposition import NMF

    jieba = load_jieba()
    corpus = build_corpus(refs, mode=corpus_mode)
    tok = tokenize_factory(jieba)

    t0 = time.time()
    X, vec, min_df, max_df, degrade = fit_vectorizer(corpus, tok, len(refs))
    t_vec = time.time() - t0
    if degrade:
        log(f"    [warn] {degrade}")

    t0 = time.time()
    # init='nndsvda' 是确定性 SVD 初始化 —— 禁用 'random'
    nmf = NMF(n_components=k, init="nndsvda", random_state=42, max_iter=200)
    W = nmf.fit_transform(X)
    labels = [int(x) for x in W.argmax(axis=1)]
    t_nmf = time.time() - t0

    terms = vec.get_feature_names_out()
    components = nmf.components_
    return labels, terms, components, X.shape, t_vec, t_nmf, X


def build_topics(refs, labels, terms, components, k):
    """组装簇定义 + 失衡诊断。"""
    clusters = []
    sizes = Counter(labels)
    for cid in range(k):
        idx = [int(i) for i, l in enumerate(labels) if int(l) == cid]
        if not idx:
            continue
        top = [terms[j] for j in components[cid].argsort()[::-1][:20]]
        members = [refs[i] for i in idx]
        lang = Counter("zh" if is_cjk(r.title) or is_cjk(r.abstract) else "en" for r in members)
        years = [r.year for r in members if r.year]
        clusters.append({
            "cluster_id": cid,
            "label": None,              # 待 LLM 命名或用户重命名
            "size": int(len(idx)),
            "pct": round(len(idx) / len(refs) * 100, 1),
            "top_terms": top,
            "lang_zh": int(lang.get("zh", 0)),
            "lang_en": int(lang.get("en", 0)),
            "lang_dominant": "zh" if lang.get("zh", 0) > lang.get("en", 0) else "en",
            "year_range": [int(min(years)), int(max(years))] if years else None,
            "ref_ids": [int(r.id) for r in members],
        })
    clusters.sort(key=lambda c: -c["size"])
    return clusters


def build_evolution(refs, labels, k):
    """主题×年份矩阵。注意：2019 前每年仅 85-155 篇，样本量不足需提示。"""
    mat = defaultdict(lambda: defaultdict(int))
    for i, l in enumerate(labels):
        y = refs[i].year
        if y:
            mat[l][y] += 1
    years = sorted({y for l in labels for y in [refs[i].year for i, ll in enumerate(labels)
                                               if ll == l and refs[i].year]})
    return [
        {"cluster_id": c, "counts": {str(y): mat[c].get(y, 0) for y in years},
         "total": sum(mat[c].values())}
        for c in sorted(mat, key=lambda x: -sum(mat[x].values()))
    ], years


def main() -> int:
    ap = argparse.ArgumentParser(description="EndNote 主题聚类")
    ap.add_argument("target")
    ap.add_argument("--k", type=int, default=None,
                    help="主题数。省略则按「最小簇占比 >= 3%%」规则自动判定")
    ap.add_argument("--threshold", type=float, default=3.0,
                    help="自动判定阈值：每个主题至少占全库百分比（默认 3.0%%）")
    ap.add_argument("--out", default="./out", help="输出目录")
    ap.add_argument("--corpus", default="hybrid",
                    choices=["hybrid", "title", "keyword"],
                    help="语料方案：hybrid=关键词为主+摘要兜底(推荐) / "
                         "title=标题+摘要+关键词加权 / keyword=纯关键词")
    ap.add_argument("--workspace", default="./.endnote_work")
    args = ap.parse_args()

    if args.k is not None and not (4 <= args.k <= 40):
        print(f"[error] --k 需在 4~40 之间，收到 {args.k}", file=sys.stderr)
        print(f"[hint] {EXIT[4]}", file=sys.stderr)
        return 4
    if not (0.5 <= args.threshold <= 20):
        print(f"[error] --threshold 需在 0.5~20 之间，收到 {args.threshold}",
              file=sys.stderr)
        print(f"[hint] {EXIT[4]}", file=sys.stderr)
        return 4

    try:
        t_all = time.time()
        target = Path(args.target).expanduser()
        is_norm = target.is_file() and target.suffix.lower() == ".json"
        enl = None if is_norm else find_enl(target)
        busy, _probe_ok, _probe_notice = (False, True, None) if is_norm else lock_status(enl)
        refs, src_meta = load_refs(target, args.workspace)

        t_parse = time.time() - t_all

        # ---- 语料与 TF-IDF（先建一次，K 扫描与最终聚类共用）----
        jieba = load_jieba()
        corpus = build_corpus(refs, mode=args.corpus)
        tok = tokenize_factory(jieba)
        t0 = time.time()
        try:
            X, vec, min_df, max_df, degrade = fit_vectorizer(corpus, tok, len(refs))
        except ValueError as e:
            print(f"[error] {e}", file=sys.stderr)
            print(f"[hint] {EXIT[2]}", file=sys.stderr)
            return 2
        t_vec = time.time() - t0
        if degrade:
            print(f"[warn] {degrade}", file=sys.stderr)

        # 显式 --k 同样受 NMF 的 n_components <= min(n_samples, n_features) 约束
        k_ceiling = int(min(X.shape[0], X.shape[1]))
        if args.k is not None and args.k > k_ceiling:
            print(f"[error] --k={args.k} 超过本库上限 {k_ceiling}"
                  f"（{X.shape[0]} 篇 × {X.shape[1]} 维特征）。"
                  f"请改用 --k {max(2, k_ceiling)} 或省略 --k 让工具自动判定。",
                  file=sys.stderr)
            print(f"[hint] {EXIT[4]}", file=sys.stderr)
            return 4

        # ---- K 自动判定（未指定 --k 时）----
        global MIN_PCT_THRESHOLD
        MIN_PCT_THRESHOLD = args.threshold
        k_decision = None
        if args.k is None:
            print(f"[info] 未指定 --k，按「最小簇占比 >= {args.threshold}%」规则自动判定：",
                  file=sys.stderr)
            k_decision = recommend_k(X, len(refs),
                                     log=lambda m: print(m, file=sys.stderr))
            chosen_k = k_decision["recommended_k"]
            print(f"[info] 推荐 K = {chosen_k}", file=sys.stderr)
        else:
            chosen_k = args.k
            print(f"[info] 使用指定 K = {chosen_k}", file=sys.stderr)

        t0 = time.time()
        labels, terms, comps, shape, t_vec2, t_nmf = compute_from_X(
            X, vec, chosen_k)
        t_nmf = time.time() - t0
        t_total = time.time() - t_all

        clusters = build_topics(refs, labels, terms, comps, chosen_k)
        evolution, years = build_evolution(refs, labels, chosen_k)
        cov = coverage_report(refs)

        # 失衡诊断 —— 不由工具替用户改 K，但必须披露
        sizes = sorted((c["size"] for c in clusters), reverse=True)
        med = int(sizes[len(sizes) // 2]) or 1
        imbalance = round(float(sizes[0]) / med, 2)
        warnings = []
        total = cov["total"]
        if max(sizes) / total * 100 > 25:
            warnings.append(
                f"最大主题占全库{max(sizes) / total * 100:.1f}%，可能偏粗；"
                f"可手动提高 --k 试试。但主题切分是学术判断，工具不自动改。")
        if min(sizes) / total * 100 < MIN_PCT_THRESHOLD:
            warnings.append(
                f"最小主题仅占全库{min(sizes) / total * 100:.1f}%，"
                f"低于{MIN_PCT_THRESHOLD}% 阈值，可能切得过细。")
        if cov["pre_2015"] > 0:
            warnings.append(
                f"{cov['pre_2015']} 篇文献早于 2015 年，演化图已纳入"
                f"（{cov['year_min']}–{cov['year_max']}），未做截断。")
        if cov["keyword_coverage_pct"] < 100:
            warnings.append(
                f"关键词覆盖 {cov['keyword_coverage_pct']}%"
                f"（{cov['no_keywords']} 篇无关键词），共现网络仅基于这部分文献。")
        if busy:
            warnings.append("检测到 EndNote 正在运行，数据可能不是最新。")
        if _probe_notice:
            # 探测能力不可用时必须如实上报，不能让"不知道"被读成"没有"
            warnings.append(_probe_notice)

        outdir = Path(args.out)
        outdir.mkdir(parents=True, exist_ok=True)
        # ⚠️ 必须写**实际生效值**，不能硬编码 min_df=3/max_df=0.5。
        # 独立复审发现：fit_vectorizer 在小库/词项少时会逐级放宽
        # （实测生效 min_df=1, max_df=1.0），而产物仍声称 3/0.5——
        # 属"声明与事实相反"，且降级只进了 stderr，产物无任何痕迹。
        # 引用这些参数做方法学描述的人会被误导。
        params = {
            "k": chosen_k, "k_source": ("auto:min_cluster_pct_prefix" if args.k is None else "user_specified"),
            "k_threshold_pct": args.threshold, "normalize_case": "lower", "df_mode": "tfidf",
            "weight": "tfidf_sublinear",
            "min_df": min_df, "max_df": max_df,
            # df 过滤是否被放宽，以及为什么——必须随产物落盘
            "df_degraded": bool(degrade),
            "df_degrade_note": degrade,
            "max_features": 20000, "nmf_init": "nndsvda", "random_state": 42,
            "corpus_mode": args.corpus,
            "corpus": {
                "hybrid": "keywords*3 + title + abstract[:120]（有关键词）/ title*3 + abstract（无关键词兜底）",
                "title": "title*3 + abstract + keywords*2",
                "keyword": "仅 keywords",
            }[args.corpus],
        }
        if degrade:
            # 放宽后无区分度词可能进入词表 → 结果可比性下降，必须显式警示
            warnings.append(
                f"df 过滤已放宽（实际生效 min_df={min_df}, max_df={max_df}）："
                f"部分高频无区分度词可能进入词表，主题划分结果的可比性下降。"
                f"详见 params.df_degrade_note。")
        payload = {
            "ok": True, "exit_code": 0,
            "library": {"name": src_meta["display_path"],
            "display_path": "…/" + src_meta["display_path"],
            "source": src_meta["source_label"]},
            "params": params,
            "timing": {"parse": round(t_parse, 2), "tfidf": round(t_vec, 2),
                       "nmf": round(t_nmf, 2), "total": round(t_total, 2)},
            "coverage": cov,
            "diagnostics": {
                "nonempty_clusters": len(clusters), "requested_k": chosen_k,
                "k_decision": k_decision,
                "max_cluster": int(sizes[0]), "min_cluster": int(sizes[-1]),
                "median_cluster": int(med), "max_over_median": float(imbalance),
                "matrix_shape": [int(x) for x in shape], "warnings": warnings,
            },
            "clusters": clusters,
            "years": [int(y) for y in years],
        }
        (outdir / "topics.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        (outdir / "evolution.json").write_text(
            json.dumps({"clusters": evolution, "years": [int(y) for y in years]},
                       ensure_ascii=False, indent=2), encoding="utf-8")

        import csv
        with open(outdir / "clusters.csv", "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["cluster_id", "size", "lang", "year", "title", "journal", "doi", "pdf"])
            for c in clusters:
                for r in [refs[i] for i in range(len(refs)) if labels[i] == c["cluster_id"]]:
                    w.writerow([c["cluster_id"], c["size"], c["lang_dominant"],
                                r.year or "", esc_csv_cell(r.title),
                                esc_csv_cell(r.journal), esc_csv_cell(r.doi),
                                "Y" if r.has_pdf else "N"])

        emit({"ok": True, "out": str(outdir),
              "k_decision": ({"recommended_k": k_decision["recommended_k"],
                             "criterion": k_decision["criterion"],
                             "threshold_pct": k_decision["threshold_pct"]}
                            if k_decision else
                            {"recommended_k": chosen_k, "criterion": "user_specified"}),
              "summary": payload["diagnostics"],
              "top_clusters": [{"id": c["cluster_id"], "size": c["size"],
                                "lang": c["lang_dominant"],
                                "terms": c["top_terms"][:8]} for c in clusters[:6]]})
        return 0

    except EnlError as e:
        print(f"[error] {e}", file=sys.stderr)
        print(f"[hint] {EXIT[e.code]}", file=sys.stderr)
        return e.code
    except Exception as e:  # noqa: BLE001
        print(f"[error] {type(e).__name__}: {e}", file=sys.stderr)
        print(f"[hint] {EXIT[5]}", file=sys.stderr)
        return 5


if __name__ == "__main__":
    sys.exit(main())
