#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
robust_k.py —— 主题数 K 的稳健性检验

为什么要有它
------------
主题数目前按「最小簇占比 ≥ 3%」自动判定，或由用户 --k 指定。
但审稿人最常问的一句就是：**「换个 K，你的结论还成立吗？」**
本脚本用三层检验回答它（可直接在论文的「稳健性检验」一节引用）：

  ① 换 K（核心）：在一组 K 上重跑 NMF，比较**同一批文献的簇归属是否稳定**
                 —— 用 ARI 与 Cramér's V 衡量，而非只看簇数变没变。
  ② 换随机种子：同 K、不同 random_state 重跑，检验初始化敏感性
                 （NMF 用 init='nndsvda' 是确定性初始化，理论上应完全一致）。
  ③ 换语料口径：hybrid / keyword / title 三种语料各跑一次，
                 检验结论是否依赖语料构造方式。

方法来源：借鉴 OBHRM `data-analysis/references/robustness-matrix.md`
的稳健性检验矩阵（检验类别 / 具体做法 / 回应的质疑 / 结果 / 判定）。

判定阈值（ARI，取所选 K 与相邻 K 的最小值）
------------------------------------------
    ≥ 0.60  稳定     —— 可放心只报单一 K
    0.40–0.60 中等   —— 建议正文报主 K，同时注明相邻 K 结果一致/差异
    < 0.40  不稳定   —— 不应只依赖单一 K 的簇划分

⚠️ 只做描述性一致性与效应量，不提供 p 值（文献聚类非抽样调查，p 值易被误读）。

用法:
    python3 robust_k.py "<库路径或 refs.json>" [--k 14] [--ladder 8,12,14,16,20]
                        [--seeds 42,7,2024] [--corpus hybrid,keyword]
                        [--out DIR]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from endnote_core import (  # noqa: E402
    EXIT, EnlError, build_corpus, emit, load_refs, tokenize_factory,
)
from stat_helpers import bootstrap_ci, cramers_v, crosstab  # noqa: E402

try:
    from sklearn.metrics import adjusted_rand_score
except Exception:  # pragma: no cover
    adjusted_rand_score = None


def load_jieba():
    try:
        import jieba
        return jieba
    except Exception:
        return None


def build_matrix(refs, corpus_mode="hybrid"):
    """构建 TF-IDF 矩阵一次，供多个 K 复用（避免重复分词，实测分词占 3.7s）。"""
    from sklearn.feature_extraction.text import TfidfVectorizer
    jieba = load_jieba()
    corpus = build_corpus(refs, mode=corpus_mode)
    tok = tokenize_factory(jieba)
    t0 = time.time()
    vec = TfidfVectorizer(
        tokenizer=tok, token_pattern=None,
        max_features=20000, min_df=3, max_df=0.5, sublinear_tf=True,
    )
    X = vec.fit_transform(corpus)
    return X, vec, time.time() - t0


def run_nmf(X, k, random_state=42):
    from sklearn.decomposition import NMF
    t0 = time.time()
    nmf = NMF(n_components=k, init="nndsvda", random_state=random_state, max_iter=200)
    W = nmf.fit_transform(X)
    labels = [int(x) for x in W.argmax(axis=1)]
    return labels, nmf.components_, time.time() - t0


def cluster_stats(labels, k, n_docs):
    sizes = Counter(labels)
    sz_desc = sorted(sizes.values(), reverse=True)
    if not sz_desc:
        return {}
    n = sum(sz_desc)
    # 基尼系数：0=完全均衡，越大越集中。
    # 与 build_report.gini2 同一约定：**升序**排序（降序会使符号翻转）。
    sz = sorted(sizes.values())
    idx = sum((i + 1) * x for i, x in enumerate(sz))
    g = (2 * idx) / (len(sz) * n) - (len(sz) + 1) / len(sz) if len(sz) > 1 else 0.0
    return {
        "k": k,
        "n_clusters_filled": len(sz),
        "min_size": int(sz[-1]),
        "max_size": int(sz[0]),
        "min_pct": round(sz[-1] / n_docs * 100, 1),
        "max_pct": round(sz[0] / n_docs * 100, 1),
        "gini": round(g, 3),
        "empty_clusters": k - len(sz),
    }


def terms_per_cluster(components, terms, k, topn=15):
    out = {}
    for cid in range(k):
        out[cid] = set(terms[j] for j in components[cid].argsort()[::-1][:topn])
    return out


def jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def term_stability(t1: dict, t2: dict) -> float:
    """两个 K 的簇关键词集合的平均最佳匹配 Jaccard（对称平均）。"""
    def one_way(src, dst):
        vals = []
        for _cid, s in src.items():
            best = max((jaccard(s, d) for d in dst.values()), default=0.0)
            vals.append(best)
        return sum(vals) / len(vals) if vals else 0.0
    return round((one_way(t1, t2) + one_way(t2, t1)) / 2, 3)


def ari(a, b) -> float:
    if adjusted_rand_score is None:
        return None
    return round(float(adjusted_rand_score(a, b)), 4)


def main() -> int:
    ap = argparse.ArgumentParser(description="主题数 K 的稳健性检验")
    ap.add_argument("target", help="库路径或 refs.json")
    ap.add_argument("--k", type=int, default=None, help="主 K（默认取 ladder 中位）")
    ap.add_argument("--ladder", default="8,12,14,16,20", help="待检验的 K 序列")
    ap.add_argument("--seeds", default="42,7,2024", help="同 K 换种子的种子序列")
    ap.add_argument("--corpus", default="hybrid,keyword", help="语料口径序列")
    ap.add_argument("--workspace", default="./.endnote_work")
    ap.add_argument("--out", default="./out")
    a = ap.parse_args()

    ladder = [int(x) for x in a.ladder.split(",") if x.strip()]
    if not (all(4 <= k <= 40 for k in ladder)):
        print("[error] --ladder 的 K 需在 4~40", file=sys.stderr)
        print(f"[hint] {EXIT[4]}", file=sys.stderr)
        return 4
    ladder = sorted(set(ladder))
    main_k = a.k if a.k is not None else ladder[len(ladder) // 2]

    try:
        refs, meta = load_refs(a.target, a.workspace)
        n_docs = len(refs)
        if n_docs < 20:
            raise EnlError(4, f"文献数 {n_docs} 过少，无法做 K 稳健性检验")

        X, vec, t_vec = build_matrix(refs)
        terms = vec.get_feature_names_out()
        t_all = time.time()

        # ── ① 换 K ──
        per_k, labels_by_k, terms_by_k = [], {}, {}
        for k in ladder:
            labels, comp, t_nmf = run_nmf(X, k)
            st = cluster_stats(labels, k, n_docs)
            st["nmf_sec"] = round(t_nmf, 2)
            per_k.append(st)
            labels_by_k[k] = labels
            terms_by_k[k] = terms_per_cluster(comp, terms, k)
            print(f"[ok] K={k:>2}  填充簇 {st['n_clusters_filled']}/{k}  "
                  f"最小簇 {st['min_pct']}%  gini={st['gini']}  ({t_nmf:.1f}s)",
                  file=sys.stderr)

        # 相邻 K 的一致性
        pairs = []
        for i in range(len(ladder) - 1):
            k1, k2 = ladder[i], ladder[i + 1]
            l1, l2 = labels_by_k[k1], labels_by_k[k2]
            a_ = ari(l1, l2)
            v = round(cramers_v(crosstab(l1, l2, k1, k2)), 4)
            pairs.append({"k1": k1, "k2": k2, "ari": a_,
                          "cramers_v": v,
                          "term_jaccard": term_stability(terms_by_k[k1], terms_by_k[k2])})

        # ── ①b 主 K 的簇占比 bootstrap 置信区间（95%）──
        # 论文里报"某主题占 11.0%"容易被追问精度；给区间更稳妥。
        import numpy as np
        lab_main = np.asarray(labels_by_k[main_k], dtype=int)
        share_ci = []
        for cid in sorted(Counter(lab_main.tolist()).items(),
                          key=lambda kv: -kv[1])[:5]:
            c, _n = cid
            ind = (lab_main == c).astype(float)

            def _mean(x):
                return float(np.mean(x))
            lo, hi = bootstrap_ci(ind, _mean, n_boot=1000, alpha=0.05, seed=42)
            share_ci.append({"cluster": int(c),
                             "pct": round(float(ind.mean()) * 100, 1),
                             "ci95": [round(lo * 100, 1), round(hi * 100, 1)]})

        # ── ② 换种子（在主 K 上）──
        seeds = [int(x) for x in a.seeds.split(",") if x.strip()]
        seed_res = []
        base = labels_by_k[main_k]
        for s in seeds:
            if s == 42:
                seed_res.append({"seed": s, "ari_vs_base": 1.0})
                continue
            lb, _c, _t = run_nmf(X, main_k, random_state=s)
            seed_res.append({"seed": s, "ari_vs_base": ari(base, lb)})

        # ── ③ 换语料口径 ──
        corpus_res = []
        for cm in [c.strip() for c in a.corpus.split(",") if c.strip()]:
            if cm == "hybrid":
                lb, comp, _t = run_nmf(X, main_k)
            else:
                Xc, vecc, _tv = build_matrix(refs, corpus_mode=cm)
                lb, comp, _t = run_nmf(Xc, main_k)
            corpus_res.append({"corpus_mode": cm, "ari_vs_hybrid": ari(base, lb)})

        # ── 判定 ──
        neigh = [p for p in pairs if main_k in (p["k1"], p["k2"])]
        min_ari = min([p["ari"] for p in neigh if p["ari"] is not None], default=None)
        min_v = min([p["cramers_v"] for p in neigh], default=None)
        if min_ari is None:
            verdict, advice = "无法判定", "缺少相邻 K 的一致性数据"
        elif min_ari >= 0.60:
            verdict = "稳定"
            advice = "可在正文只报主 K；建议表注注明已做相邻 K 检验。"
        elif min_ari >= 0.40:
            verdict = "中等"
            advice = ("相邻 K 下簇归属有实质变化：正文报主 K，并说明相邻 K 的异同，"
                      "避免把簇划分说成唯一结论。")
        else:
            verdict = "不稳定"
            advice = ("簇划分对 K 高度敏感，不宜只依赖单一 K 的结论；"
                      "建议改为报告跨 K 稳定的主题（关键词集合）而非簇编号。")

        # 借鉴 robustness-matrix.md 的矩阵结构
        matrix = [
            {"优先级": "必做", "检验类别": "替换主题数 K",
             "具体做法": f"在 K={ladder} 上重跑 NMF，比较同一批文献的簇归属",
             "回应的质疑": "「换个 K 就没了」",
             "结果": f"相邻 K 最小 ARI={min_ari}, Cramér's V={min_v}",
             "判定": verdict},
            {"优先级": "必做", "检验类别": "替换随机种子",
             "具体做法": f"同 K={main_k}，random_state={seeds}",
             "回应的质疑": "「结果只是某个随机初始化的产物」",
             "结果": "ARI=" + ", ".join(str(x["ari_vs_base"]) for x in seed_res),
             "判定": "通过" if all(x["ari_vs_base"] == 1.0 for x in seed_res)
                     else "存在初始化敏感性"},
            {"优先级": "高", "检验类别": "替换语料口径",
             "具体做法": f"corpus_mode={a.corpus}",
             "回应的质疑": "「结论只是语料构造方式的产物」",
             "结果": "ARI=" + ", ".join(f'{x["corpus_mode"]}:{x["ari_vs_hybrid"]}'
                                       for x in corpus_res),
             "判定": "见数值（语料口径改变必然影响簇，重点看主题是否仍可辨识）"},
        ]

        payload = {
            "ok": True,
            "source": meta.get("source_label"),
            "n_docs": n_docs,
            "main_k": main_k,
            "ladder": ladder,
            "vectorize_sec": round(t_vec, 2),
            "per_k": per_k,
            "share_ci95": share_ci,
            "pairs": pairs,
            "seed_check": seed_res,
            "corpus_check": corpus_res,
            "verdict": verdict,
            "min_ari_adjacent": min_ari,
            "min_cramers_v_adjacent": min_v,
            "advice": advice,
            "robustness_matrix": matrix,
            "elapsed_sec": round(time.time() - t_all, 1),
            "note": "只提供描述性一致性与效应量，不含 p 值（聚类非抽样调查）。",
        }

        outdir = Path(a.out)
        try:
            outdir.mkdir(parents=True, exist_ok=True)
        except FileExistsError:
            pass
        (outdir / "robust_k.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
        print("\n──────── 稳健性检验矩阵 ────────", file=sys.stderr)
        for m in matrix:
            print(f"[{m['优先级']}] {m['检验类别']} → {m['判定']}\n"
                  f"      做法：{m['具体做法']}\n      回应：{m['回应的质疑']}\n"
                  f"      结果：{m['结果']}", file=sys.stderr)
        print(f"\n综合判定：{verdict}（最小 ARI={min_ari}）\n{advice}", file=sys.stderr)
        emit(payload)
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
