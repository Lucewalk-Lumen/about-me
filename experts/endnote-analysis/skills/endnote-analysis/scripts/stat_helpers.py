#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
stat_helpers.py —— 轻量统计量（纯 numpy，无 scipy 依赖）

来源：改编自 OBHRM 研究团 `data-analysis/scripts/stat_helpers.py`
（cohen_d / eta_squared / cramers_v / bootstrap_ci / cronbach_alpha）。
本包只取与「文献计量稳健性」有关的四个，并统一为 numpy 实现，
避免为几个效应量引入 scipy 依赖。

用途
----
· robust_k.py  用 cramers_v / adjusted_rand 衡量两次聚类结果的一致性；
· author_topic.py 等可用 eta_squared 衡量「主题」对作者分布的解释力；
· bootstrap_ci 为主题占比等关键比例给出置信区间（中文期刊常要求）。

⚠️ 诚实边界：本文件只做**描述统计与效应量**，不做推断检验的 p 值。
   文献聚类不是抽样调查，p 值在这里容易被误读，故不提供。
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


def cohen_d(g1, g2, pooled: bool = True) -> float:
    """两组均值差异的效应量（ pooled 用合并标准差）。"""
    np = _np()
    g1 = np.asarray(g1, dtype=float)
    g2 = np.asarray(g2, dtype=float)
    n1, n2 = len(g1), len(g2)
    if n1 < 2 or n2 < 2:
        return float("nan")
    v1 = g1.var(ddof=1)
    v2 = g2.var(ddof=1)
    if pooled:
        s = math.sqrt(((n1 - 1) * v1 + (n2 - 1) * v2) / (n1 + n2 - 2))
    else:
        s = math.sqrt((v1 + v2) / 2)
    if s == 0:
        return 0.0
    return float((g1.mean() - g2.mean()) / s)


def eta_squared(*groups) -> float:
    """η²：分组变量对连续变量的解释比例 = SS_between / SS_total。

    在文献计量里的典型用法：η² 表示"主题"解释了"作者产出量"多少方差。
    """
    np = _np()
    gs = [np.asarray(g, dtype=float) for g in groups if len(g)]
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
        return 0.0
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


__all__ = ["cramers_v", "crosstab", "cohen_d", "eta_squared", "bootstrap_ci"]
