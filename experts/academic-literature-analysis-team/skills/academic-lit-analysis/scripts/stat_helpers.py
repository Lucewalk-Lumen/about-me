#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
stat_helpers.py —— 轻量统计量（纯 numpy / 标准库，无 scipy 依赖）

来源：本包内置实现（从一组通用效应量中取与「文献计量稳健性」有关的部分），
统一为 numpy 实现，避免为几个效应量引入 scipy 依赖。

用途
----
· robust_k.py  用 cramers_v / adjusted_rand 衡量两次聚类结果的一致性；
· author_topic.py 等可用 eta_squared 衡量「主题」对作者分布的解释力；
· bootstrap_ci 为主题占比等关键比例给出置信区间（中文期刊常要求）。

推断检验（v1.0.0 起加入，回应实测需求「报告要使用统计显著性检验指标」）
----
· hypergeom_sf      共现边的超几何精确检验 P(X>=k)：一条边在「随机配对」零假设
                    下出现 w 次及以上的概率（总体=N 篇文献，两端关键词各出现
                    df_a / df_b 篇）。共现网络的标准检验。
· fdr_bh            Benjamini–Hochberg FDR 校正：共现网络一次检验成千上万条边，
                    必须做多重比较校正，否则 p<0.05 全是假阳性。

[!]  诚实边界：这些检验回答的是「在共现/计数随机模型下是否罕见」，
   不是抽样调查意义上的总体推断；报告仍须给出效应量与检验口径，
   两者并列，不可只用其一。
"""
from __future__ import annotations

import math


def _np():
    import numpy as np
    return np


def cramers_v(table) -> float:
    """Cramér's V：两个分类变量（如两次聚类标签）的关联强度，取值 [0,1]。

    V = sqrt( χ² / (n · min(r-1, c-1)) )
    与 ARI 互补：ARI 对簇数量敏感，V 更接近"关联强度"的直觉。
    """
    np = _np()
    t = np.asarray(table, dtype=float)
    if t.ndim != 2 or t.size == 0:
        return 0.0
    n = t.sum()
    if n <= 0:
        return 0.0
    r, c = t.shape
    k = min(r - 1, c - 1)
    if k <= 0:
        return 0.0
    exp = np.outer(t.sum(axis=1), t.sum(axis=0)) / n
    with np.errstate(divide="ignore", invalid="ignore"):
        chi2 = np.nansum(np.where(exp > 0, (t - exp) ** 2 / exp, 0.0))
    return float(math.sqrt(chi2 / (n * k)))


def crosstab(a, b, k_a: int | None = None, k_b: int | None = None):
    """两个标签序列的列联表。"""
    np = _np()
    a = np.asarray(a, dtype=int)
    b = np.asarray(b, dtype=int)
    ka = k_a or int(a.max()) + 1
    kb = k_b or int(b.max()) + 1
    t = np.zeros((ka, kb), dtype=float)
    for i, j in zip(a, b):
        t[i, j] += 1.0
    return t


def eta_squared(*groups) -> float:
    """η²：分组变量对连续变量的解释比例 = SS_between / SS_total。

    在文献计量里的典型用法：η² 表示"主题"解释了"作者产出量"多少方差。

    [!]  三处退化输入的处理：
      1) 分组变量**无组内变异**（所有观测同值）时 SS_total == 0，
         η² = 0/0 在数学上**未定义** → 返回 **nan**；若返回 0.0，
         等于宣称"我们测到解释力为零"，而真相是"测不出来"——
         这是把「无法计算」误报成「实测为零」，是分析工具最危险的失败模式。
      2) `eta_squared(1, 2, 3)` 这类传入**标量**的调用不再抛
         TypeError（旧的 `len(g)` 对 0-d 数组直接炸）；
         标量按长度 1 的分组处理。
      3) 所有分组皆空 → nan（同为未定义）。
    """
    np = _np()
    # atleast_1d：标量 -> 长度 1 的分组，避免 0-d 数组上 len() 抛 TypeError
    gs = [np.atleast_1d(np.asarray(g, dtype=float)) for g in groups
          if np.size(g) > 0]
    if not gs:
        return float("nan")
    allv = np.concatenate(gs)
    n = len(allv)
    if n == 0:
        return float("nan")
    gm = allv.mean()
    ss_between = sum(len(g) * (g.mean() - gm) ** 2 for g in gs)
    ss_total = ((allv - gm) ** 2).sum()
    if ss_total == 0:
        # 所有观测同值 → η² = 0/0 未定义（而非"解释力为零"）
        return float("nan")
    return float(ss_between / ss_total)


def bootstrap_ci(data, stat_fn, n_boot: int = 2000, alpha: float = 0.05, seed=None):
    """对任意统计量做百分位 bootstrap，返回 (lower, upper)。

    用于给"某主题占比""某作者占比"这类比例一个区间，
    避免只报一个点估计（中文期刊常见扣分点）。
    """
    np = _np()
    rng = np.random.default_rng(seed)
    d = np.asarray(data)
    n = len(d)
    if n == 0:
        return (float("nan"), float("nan"))
    idx = rng.integers(0, n, size=(n_boot, n))
    vals = np.array([stat_fn(d[i]) for i in idx])
    lo = float(np.percentile(vals, 100 * (alpha / 2)))
    hi = float(np.percentile(vals, 100 * (1 - alpha / 2)))
    return (lo, hi)


__all__ = ["cramers_v", "crosstab", "eta_squared", "bootstrap_ci",
           "hypergeom_sf", "fdr_bh"]


# ── 推断检验（纯标准库，无 scipy） ──────────────────

def hypergeom_sf(k: int, big_n: int, K: int, n: int) -> float:
    """超几何分布上尾概率 P(X >= k)（精确求和，无近似）。

    零假设：在 N 篇文献中，两端点各自出现的 K 篇与 n 篇是随机独立配对。
    观测到两集合交集 >= k 的概率即共现边的显著性。
      k   观测共现次数（交集大小）
      N   文献总数
      K   端点 A 出现的文献数（df_a）
      n   端点 B 出现的文献数（df_b）

    [!]  实现说明：P(X>=k) = 1 - P(X<=k-1)，用 math.comb 逐项求和。
       交集上限 min(K,n) 通常不大（共现网络里极少超过几百），
       精确求和可行；k<=0 时返回 1.0（无共现谈不上显著）。
    """
    if k <= 0 or big_n <= 0 or K <= 0 or n <= 0:
        return 1.0
    lo = max(0, K + n - big_n)
    hi = min(K, n)
    if k > hi:
        return 0.0          # 观测超过理论上限 → p=0（记作 <1e-16 更诚实，见下）
    # P(X = i) = comb(K,i)*comb(N-K,n-i)/comb(N,n)；从 lo 累加到 k-1 得下尾
    log_denom = math.lgamma(big_n + 1) - math.lgamma(big_n - n + 1)  # log C(N,n) 分步
    log_denom += math.lgamma(n + 1)
    lower = 0.0
    for i in range(lo, min(k, hi + 1)):
        # P(X=i) = C(K,i)·C(N-K,n-i) / C(N,n)，对数域防溢出
        logp = (_log_comb(K, i) + _log_comb(big_n - K, n - i) - _log_comb(big_n, n))
        lower += math.exp(logp)
    return max(0.0, min(1.0, 1.0 - lower))


def _log_comb(n: int, k: int) -> float:
    """log C(n,k)。k 越界时返回 -inf（概率 0）。"""
    if k < 0 or k > n:
        return float("-inf")
    return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)


def fdr_bh(pvals) -> list[float]:
    """Benjamini–Hochberg FDR 校正：返回与输入等长的 q 值列表。

    共现网络对全部边一次性检验，多重比较下不做校正则 p<0.05 大面积假阳性。
    q 值含义：把该边判为显著时，错误发现率不超过 q。
    """
    m = len(pvals)
    if m == 0:
        return []
    idx = sorted(range(m), key=lambda i: pvals[i])
    q = [0.0] * m
    prev = 1.0
    for rank in range(m, 0, -1):
        i = idx[rank - 1]
        val = pvals[i] * m / rank
        prev = min(prev, val)
        q[i] = max(0.0, min(1.0, prev))
    return q
