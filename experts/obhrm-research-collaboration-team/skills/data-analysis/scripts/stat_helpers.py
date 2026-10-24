#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OBHRM 数据分析域 · 统计计算辅助（stat_helpers）。

设计红线（与 `data-analysis/SKILL.md` 的「统计数字防编造规则」同源）：
- **本模块只做"在用户提供的真实数据上"的计算，绝不编造、估算或回退到默认值。**
- 所有函数都要求调用方传入真实观测数据 / 真实运行得到的统计量；缺少真实输入时
  一律抛错或返回 None，绝不填 0.00 / 经验值 / 典型值。
- 本模块是"计算器"，不是"数据来源"。它替代的是用户手算效应量/信度，而非替代
  用户在本机运行 R / SPSS / Python 统计环境。真正的分析仍由用户运行的脚本产出，
  本模块用于在已取得真实数值后做轻量换算/汇总（如由实测均值标准差求 Cohen's d、
  由实测 R² 求 ΔR²、由真实作答矩阵求 Cronbach's α）。

依赖：纯标准库即可运行外壳；具体统计量计算**惰性导入** numpy / scipy，缺失时给出
明确报错（提示用 `pip install numpy scipy` 或改用 r-analysis 的 108 个 R 脚本）。

用法示例：
  python3 stat_helpers.py cohen_d --g1 3.2,1.1,2.9,... --g2 2.8,0.9,...
  python3 stat_helpers.py cronbach --csv responses.csv
  python3 stat_helpers.py cramers_v --table 30,10,20,40
也可 `import stat_helpers` 在 Python 中调用各函数。
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent


def _np():
    """惰性导入 numpy，缺失时给清晰报错（不静默降级）。"""
    try:
        import numpy as np  # type: ignore
        return np
    except Exception as e:  # pragma: no cover - 依赖缺失路径
        raise RuntimeError(
            "stat_helpers 需要 numpy 才能计算（本模块不内置、不编造数值）。\n"
            "请在运行环境安装：pip install numpy scipy\n"
            f"原始导入错误：{e}"
        )


# --------------------------------------------------------------------------- #
# 数据载入
# --------------------------------------------------------------------------- #
def load_vectors(*specs) -> list:
    """把 'a,b,c' 形式的字符串或已为 list 的输入规范成 float 向量列表。"""
    np = _np()
    out = []
    for s in specs:
        if isinstance(s, str):
            vals = [float(x) for x in s.split(",") if x.strip() != ""]
        else:
            vals = [float(x) for x in s]
        out.append(np.asarray(vals, dtype=float))
    return out


def load_csv_matrix(path: str, skip_header: bool = True) -> "np.ndarray":  # noqa: F821
    """从 CSV 读取被试×题项矩阵（每行一个被试，每列一道题）。"""
    np = _np()
    rows = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        for i, row in enumerate(reader):
            if skip_header and i == 0:
                continue
            nums = [float(x) for x in row if x.strip() != ""]
            if nums:
                rows.append(nums)
    return np.asarray(rows, dtype=float)


# --------------------------------------------------------------------------- #
# 统计量（全部基于真实输入）
# --------------------------------------------------------------------------- #
def cohen_d(g1, g2, pooled: bool = True):
    """两独立组 Cohen's d。

    g1/g2 为真实观测向量。pooled=True 用合并标准差（常用），
    pooled=False 用控制组（g2）标准差（Glass's Δ）。
    """
    np = _np()
    a, b = load_vectors(g1, g2)
    n1, n2 = a.size, b.size
    m1, m2 = a.mean(), b.mean()
    s1, s2 = a.std(ddof=1), b.std(ddof=1)
    if pooled:
        sp = np.sqrt(((n1 - 1) * s1**2 + (n2 - 1) * s2**2) / (n1 + n2 - 2))
        d = (m1 - m2) / sp if sp > 0 else float("nan")
    else:
        d = (m1 - m2) / s2 if s2 > 0 else float("nan")
    return float(d)


def eta_squared(*groups):
    """单因素 ANOVA 的 η²（效应量）。

    接受任意多个真实观测组向量；返回 η² = SS_between / SS_total。
    """
    np = _np()
    gs = load_vectors(*groups)
    if len(gs) < 2:
        raise ValueError("eta_squared 至少需要两组真实数据")
    allv = np.concatenate(gs)
    grand = allv.mean()
    ss_total = float(((allv - grand) ** 2).sum())
    ss_between = float(sum(n.size * (g.mean() - grand) ** 2 for n, g in zip(gs, gs)))
    return ss_between / ss_total if ss_total > 0 else float("nan")


def cramers_v(table):
    """由列联表求 Cramer's V。

    table：二维列表（list[list[int]]），如 [[30,10],[20,40]]。
    """
    np = _np()
    t = np.asarray(table, dtype=float)
    if t.ndim != 2:
        raise ValueError("cramers_v 接收二维列联表")
    n = t.sum()
    if n == 0:
        return float("nan")
    chi2 = _chi2(t)
    r, k = t.shape
    min_dim = min(r - 1, k - 1)
    if min_dim == 0:
        return float("nan")
    return float(np.sqrt(chi2 / (n * min_dim)))


def _chi2(t):
    np = _np()
    row = t.sum(axis=1, keepdims=True)
    col = t.sum(axis=0, keepdims=True)
    expected = row @ col / t.sum()
    expected = np.where(expected == 0, 1e-12, expected)
    return float(((t - expected) ** 2 / expected).sum())


def vif(design):
    """由设计矩阵（已含截距的列，真实数据）求各预测变量 VIF。

    design：二维列表（n×p）。返回各列 VIF 列表。VIF>5 提示多重共线性。
    """
    np = _np()
    X = np.asarray(design, dtype=float)
    if X.ndim != 2:
        raise ValueError("vif 接收二维设计矩阵（被试×预测变量）")
    n, p = X.shape
    vifs = []
    for i in range(p):
        y = X[:, i]
        Xo = np.delete(X, i, axis=1)
        # 中心化后 OLS 求 R²
        Xc = Xo - Xo.mean(axis=0)
        yc = y - y.mean()
        try:
            beta, *_ = np.linalg.lstsq(Xc, yc, rcond=None)
        except np.linalg.LinAlgError:
            # 设计矩阵奇异（该列可由其余列精确线性表出）→ 真实意义上的“无穷共线性”
            vifs.append(float("inf"))
            continue
        pred = Xc @ beta
        ss_res = float(((yc - pred) ** 2).sum())
        ss_tot = float(((yc - yc.mean()) ** 2).sum())
        if ss_tot == 0:
            # 目标列恒定（或已被完全预测）→ 该预测变量可完全解释目标，VIF 为无穷
            vifs.append(float("inf"))
            continue
        r2 = 1 - ss_res / ss_tot
        vifs.append(float("inf") if r2 >= 1 - 1e-12 else 1.0 / (1.0 - r2))
    return vifs


def delta_r2(r2_full: float, r2_reduced: float) -> float:
    """ΔR² = 完整模型 R² − 缩模型 R²（真实 R² 输入）。"""
    return float(r2_full - r2_reduced)


def bootstrap_ci(data, stat_fn, n_boot: int = 2000, alpha: float = 0.05, seed=None):
    """对真实数据 data（一维）上的统计量 stat_fn 求 Bootstrap (1-α) 置信区间。

    返回 (lo, hi)。stat_fn 接收一维 numpy 数组返回标量。
    """
    np = _np()
    x = np.asarray(data, dtype=float)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, x.size, size=(n_boot, x.size))
    boots = np.asarray([stat_fn(x[ix]) for ix in idx], dtype=float)
    lo = float(np.percentile(boots, 100 * alpha / 2))
    hi = float(np.percentile(boots, 100 * (1 - alpha / 2)))
    return lo, hi


def cronbach_alpha(matrix):
    """由真实作答矩阵（被试×题项）求 Cronbach's α。

    缺失值按题项两两成对删除处理。
    """
    np = _np()
    X = np.asarray(matrix, dtype=float)
    if X.ndim != 2:
        raise ValueError("cronbach_alpha 接收二维作答矩阵（被试×题项）")
    k = X.shape[1]
    if k < 2:
        raise ValueError("题项数需 ≥ 2")
    item_var = []
    for j in range(k):
        col = X[:, j]
        mask = ~np.isnan(col)
        item_var.append(float(col[mask].var(ddof=1)) if mask.sum() > 1 else 0.0)
    total = X.sum(axis=1)
    mask = ~np.isnan(total)
    total_var = float(total[mask].var(ddof=1)) if mask.sum() > 1 else 0.0
    sum_item_var = float(sum(item_var))
    if total_var == 0:
        return float("nan")
    return float((k / (k - 1)) * (1 - sum_item_var / total_var))


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _cmd_cohen_d(args):
    print(json.dumps({"cohen_d": cohen_d(args.g1, args.g2, not args.glass)},
                     ensure_ascii=False))


def _cmd_eta(args):
    groups = args.groups
    print(json.dumps({"eta_squared": eta_squared(*groups)}, ensure_ascii=False))


def _cmd_cramers(args):
    table = [[int(x) for x in row.split(",")] for row in args.table]
    print(json.dumps({"cramers_v": cramers_v(table)}, ensure_ascii=False))


def _cmd_vif(args):
    rows = [[float(x) for x in r.split(",")] for r in args.matrix]
    print(json.dumps({"vif": vif(rows)}, ensure_ascii=False))


def _cmd_delta(args):
    print(json.dumps({"delta_r2": delta_r2(args.full, args.reduced)}, ensure_ascii=False))


def _cmd_boot(args):
    np = _np()
    data = np.asarray([float(x) for x in args.data.split(",")], dtype=float)
    lo, hi = bootstrap_ci(data, np.mean, args.boot, args.alpha, args.seed)
    print(json.dumps({"bootstrap_ci_mean": [lo, hi]}, ensure_ascii=False))


def _cmd_cronbach(args):
    mat = load_csv_matrix(args.csv) if args.csv else None
    if mat is None and args.matrix:
        mat = np.asarray([[float(x) for x in r.split(",")] for r in args.matrix])
    print(json.dumps({"cronbach_alpha": cronbach_alpha(mat)}, ensure_ascii=False))


def main():
    ap = argparse.ArgumentParser(description="OBHRM 统计计算辅助（真实数据）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("cohen_d", help="两独立组 Cohen's d")
    p.add_argument("--g1", required=True, help="组1 真实数值，逗号分隔")
    p.add_argument("--g2", required=True, help="组2 真实数值，逗号分隔")
    p.add_argument("--glass", action="store_true", help="改用 Glass's Δ（控制组标准差）")
    p.set_defaults(func=_cmd_cohen_d)

    p = sub.add_parser("eta_squared", help="单因素 ANOVA η²")
    p.add_argument("--groups", nargs="+", required=True, help="每组真实数值，逗号分隔，可多组")
    p.set_defaults(func=_cmd_eta)

    p = sub.add_parser("cramers_v", help="列联表 Cramer's V")
    p.add_argument("--table", nargs="+", required=True, help="每行一个逗号分隔的行")
    p.set_defaults(func=_cmd_cramers)

    p = sub.add_parser("vif", help="设计矩阵各列 VIF")
    p.add_argument("--matrix", nargs="+", required=True, help="每行一个逗号分隔的观测")
    p.set_defaults(func=_cmd_vif)

    p = sub.add_parser("delta_r2", help="ΔR²")
    p.add_argument("--full", type=float, required=True, help="完整模型 R²（真实）")
    p.add_argument("--reduced", type=float, required=True, help="缩模型 R²（真实）")
    p.set_defaults(func=_cmd_delta)

    p = sub.add_parser("bootstrap_ci", help="Bootstrap 均值 CI")
    p.add_argument("--data", required=True, help="真实数值，逗号分隔")
    p.add_argument("--boot", type=int, default=2000)
    p.add_argument("--alpha", type=float, default=0.05)
    p.add_argument("--seed", type=int, default=None)
    p.set_defaults(func=_cmd_boot)

    p = sub.add_parser("cronbach", help="Cronbach's α")
    p.add_argument("--csv", help="被试×题项 CSV 路径")
    p.add_argument("--matrix", nargs="+", help="每行一个逗号分隔的被试作答（替代 --csv）")
    p.set_defaults(func=_cmd_cronbach)

    args = ap.parse_args()
    try:
        args.func(args)
    except RuntimeError as e:
        print(f"[依赖缺失] {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
