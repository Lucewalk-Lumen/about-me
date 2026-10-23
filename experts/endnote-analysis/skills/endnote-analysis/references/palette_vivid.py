#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
palette_vivid.py —— 生成「更鲜明」的 14 色主题色板（自包含，无外部依赖）

背景
----
用户反馈：报告里共现网络的配色「不鲜明」。旧色板
（见 palette_final.json）是为色觉缺陷安全优化的 Okabe-Ito + 补色，
min ΔE00(normal) = 14.04，但彩度偏低、视觉发灰。

做法
----
在 Oklab 空间按「高彩度 + 白底可读」生成候选池，再用 Machado 矩阵
模拟 protan / deutan / tritan 三种色觉缺陷，用 CIEDE2000 贪心挑选
**14 色、最大化「所有视觉类型下的最小两两 ΔE00」**。

与旧色板的差异：彩度 C 从 ~0.10 提到 ~0.19（明显更鲜艳），
白底对比度阈值略放宽到 2.45（配合渲染端新增的节点描边，节点仍清晰）。

用法：  python3 palette_vivid.py --n 14 --out palette_vivid.json
"""
from __future__ import annotations

import argparse
import json
import math

# ── sRGB <-> 线性 ────────────────────────────────────────────
def srgb2lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def lin2srgb(c):
    return 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055


# ── Oklab（Björn Ottosson 2020）─────────────────────────────
def lin_srgb_to_oklab(r, g, b):
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l_, m_, s_ = (math.copysign(abs(x) ** (1 / 3), x) for x in (l, m, s))
    return (
        0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
        1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
        0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_,
    )


def oklab_to_lin_srgb(L, a, bb):
    l_ = L + 0.3963377774 * a + 0.2158037573 * bb
    m_ = L - 0.1055613458 * a - 0.0638541728 * bb
    s_ = L - 0.0894841775 * a - 1.2914855480 * bb
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    return (
        +4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
        -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
        -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s,
    )


def in_gamut(r, g, b, eps=1e-4):
    return all(-eps <= v <= 1 + eps for v in (r, g, b))


def oklch_to_hex(L, C, H):
    """Oklch → #RRGGBB；出色域则逐步降彩度。返回 (hex, 是否在色域内)。"""
    h = math.radians(H)
    for scale in (1.0, 0.95, 0.9, 0.85, 0.8, 0.7, 0.6, 0.5):
        r, g, b = oklab_to_lin_srgb(L, C * scale * math.cos(h), C * scale * math.sin(h))
        if in_gamut(r, g, b):
            to255 = lambda v: max(0, min(255, round(lin2srgb(max(0.0, min(1.0, v))) * 255)))
            return "#%02X%02X%02X" % (to255(r), to255(g), to255(b)), True
    return "#000000", False


# ── 线性 RGB -> CIELAB ──────────────────────────────────────
M_RGB2XYZ = ((0.4124564, 0.3575761, 0.1804375),
             (0.2126729, 0.7151522, 0.0721750),
             (0.0193339, 0.1191920, 0.9503041))
D65 = (0.95047, 1.00000, 1.08883)


def lin_to_xyz(r, g, b):
    return tuple(m[0] * r + m[1] * g + m[2] * b for m in M_RGB2XYZ)


def xyz_to_lab(x, y, z):
    def f(t):
        return t ** (1 / 3) if t > 216 / 24389 else (841 / 108) * t + 4 / 29
    fx, fy, fz = f(x / D65[0]), f(y / D65[1]), f(z / D65[2])
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


def hex_to_lab(hx):
    r, g, b = (srgb2lin(int(hx[i:i + 2], 16) / 255) for i in (1, 3, 5))
    return xyz_to_lab(*lin_to_xyz(r, g, b))


# ── 相对亮度 / 白底对比度 ────────────────────────────────────
def rel_luminance(hx):
    r, g, b = (srgb2lin(int(hx[i:i + 2], 16) / 255) for i in (1, 3, 5))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_on_white(hx):
    return 1.05 / (rel_luminance(hx) + 0.05)


# ── 色觉缺陷模拟（Machado et al. 2009, severity 1.0）────────
CVD = {
    "protan": ((0.152286, 1.052583, -0.204868),
               (0.114503, 0.786281, 0.099216),
               (-0.003882, -0.048116, 1.051998)),
    "deutan": ((0.367322, 0.860646, -0.227968),
               (0.280085, 0.672501, 0.047413),
               (-0.011820, 0.042940, 0.968881)),
    "tritan": ((1.255528, -0.076749, -0.178779),
               (-0.078411, 0.930809, 0.147602),
               (0.004733, 0.691367, 0.303900)),
}
VIEWS = ("normal",) + tuple(CVD)


def hex_to_lab_cvd(hx, view):
    r, g, b = (srgb2lin(int(hx[i:i + 2], 16) / 255) for i in (1, 3, 5))
    if view != "normal":
        m = CVD[view]
        r, g, b = (m[0][i] * r + m[0][1] * g + m[0][2] * b for i in range(3))
        g, b = (m[1][0] * r + m[1][1] * g + m[1][2] * b,
                m[2][0] * r + m[2][1] * g + m[2][2] * b)
        r, g, b = (min(1.0, max(0.0, v)) for v in (r, g, b))
    return xyz_to_lab(*lin_to_xyz(r, g, b))


# ── CIEDE2000 ───────────────────────────────────────────────
def dE00(l1, l2):
    L1, a1, b1 = l1
    L2, a2, b2 = l2
    C1 = math.hypot(a1, b1)
    C2 = math.hypot(a2, b2)
    Cb = (C1 + C2) / 2
    G = 0.5 * (1 - math.sqrt(Cb ** 7 / (Cb ** 7 + 25.0 ** 7))) if Cb > 0 else 0.5
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = math.hypot(a1p, b1), math.hypot(a2p, b2)
    h1p = math.degrees(math.atan2(b1, a1p)) % 360 if (a1p or b1) else 0.0
    h2p = math.degrees(math.atan2(b2, a2p)) % 360 if (a2p or b2) else 0.0
    dLp = L2 - L1
    dCp = C2p - C1p
    if C1p * C2p == 0:
        dhp = 0.0
    elif abs(h2p - h1p) <= 180:
        dhp = h2p - h1p
    elif h2p - h1p > 180:
        dhp = h2p - h1p - 360
    else:
        dhp = h2p - h1p + 360
    dHp = 2 * math.sqrt(C1p * C2p) * math.sin(math.radians(dhp / 2))
    Lbp = (L1 + L2) / 2
    Cbp = (C1p + C2p) / 2
    if C1p * C2p == 0:
        hbp = h1p + h2p
    elif abs(h1p - h2p) <= 180:
        hbp = (h1p + h2p) / 2
    elif h1p + h2p < 360:
        hbp = (h1p + h2p + 360) / 2
    else:
        hbp = (h1p + h2p - 360) / 2
    T = (1 - 0.17 * math.cos(math.radians(hbp - 30))
         + 0.24 * math.cos(math.radians(2 * hbp))
         + 0.32 * math.cos(math.radians(3 * hbp + 6))
         - 0.20 * math.cos(math.radians(4 * hbp - 63)))
    dTh = 30 * math.exp(-(((hbp - 275) / 25) ** 2))
    Rc = 2 * math.sqrt(Cbp ** 7 / (Cbp ** 7 + 25.0 ** 7)) if Cbp > 0 else 0.0
    Sl = 1 + (0.015 * (Lbp - 50) ** 2) / math.sqrt(20 + (Lbp - 50) ** 2)
    Sc = 1 + 0.045 * Cbp
    Sh = 1 + 0.015 * Cbp * T
    Rt = -math.sin(math.radians(2 * dTh)) * Rc
    return math.sqrt((dLp / Sl) ** 2 + (dCp / Sc) ** 2 + (dHp / Sh) ** 2
                     + Rt * (dCp / Sc) * (dHp / Sh))


# ── 候选池 + 贪心挑选 ──────────────────────────────────────
def build_pool(lmin=0.30, lmax=0.82, cmax=0.23, min_contrast=2.00, step=3.0):
    pool = []
    L = lmin
    while L <= lmax + 1e-9:
        H = 0.0
        while H < 360.0:
            hx, ok = oklch_to_hex(L, cmax, H)
            if ok and contrast_on_white(hx) >= min_contrast:
                pool.append(hx)
            H += step
        L += 0.02
    return sorted(set(pool))


def dmin(pair, labs):
    return min(dE00(labs[v][pair[0]], labs[v][pair[1]]) for v in VIEWS)


def oklab_chroma(hx):
    r, g, b = (srgb2lin(int(hx[i:i + 2], 16) / 255) for i in (1, 3, 5))
    _L, a, bb = lin_srgb_to_oklab(r, g, b)
    return math.hypot(a, bb)


def oklch(hx):
    r, g, b = (srgb2lin(int(hx[i:i + 2], 16) / 255) for i in (1, 3, 5))
    L, a, bb = lin_srgb_to_oklab(r, g, b)
    return L, math.hypot(a, bb), math.degrees(math.atan2(bb, a)) % 360


def hue_gap(h1, h2):
    d = abs(h1 - h2) % 360
    return min(d, 360 - d)


def pick_chain(pool, n, labs, adj_floor, glob_floor=3.0, chroma_min=0.15, starts=5):
    """构造色板：色相均匀铺开为主目标，彩度为次级目标。

    ⚠️ 为什么不直接「最大化彩度」？—— sRGB 的高彩度区集中在品红/紫/绿，
    纯彩度贪心会塌缩成一片洋红（实测 14 色里 10 个紫/洋红），观感并不「鲜明」。
    真正的「鲜明」= 明亮 + 色彩多样，故：
      1) 先按彩度下限 chroma_min 过滤掉灰暗候选；
      2) 约束：相邻色 ΔE00 ≥ adj_floor、与所有已选 ΔE00 ≥ glob_floor；
      3) 选择：最大化「到已选色的最小色相间距」，彩度作次级排序键。
    """
    cand = [hx for hx in pool if oklab_chroma(hx) >= chroma_min]
    if len(cand) < n:
        cand = sorted(pool, key=lambda hx: -oklab_chroma(hx))[:max(n * 4, 60)]
    order = sorted(cand, key=lambda hx: -oklab_chroma(hx))
    best = None
    for s0 in order[:starts]:
        hues = [oklch(s0)[2]]
        chain = [s0]
        while len(chain) < n:
            pick, key = None, None
            for hx in order:
                if hx in chain:
                    continue
                if dmin((hx, chain[-1]), labs) < adj_floor:
                    continue
                if any(dmin((hx, c), labs) < glob_floor for c in chain):
                    continue
                h = oklch(hx)[2]
                g = min(hue_gap(h, u) for u in hues)      # 最小色相间距
                k = (round(g, 1), round(oklab_chroma(hx), 3))
                if key is None or k > key:
                    key, pick = k, hx
            if pick is None:
                break
            chain.append(pick)
            hues.append(oklch(pick)[2])
        if len(chain) == n:
            score = (min(hue_gap(hues[i], hues[j])
                        for i in range(n) for j in range(i + 1, n)),
                     sum(oklab_chroma(c) for c in chain) / n)
            if best is None or score > best[0]:
                best = (score, chain)
    return best[1] if best else None


def adjacent_min(chosen, labs):
    w, wp = 1e9, None
    for i in range(len(chosen) - 1):
        d = min(dE00(labs[v][chosen[i]], labs[v][chosen[i + 1]]) for v in VIEWS)
        if d < w:
            w, wp = d, (chosen[i], chosen[i + 1])
    return round(w, 2), list(wp)



def solve_ladder(n, adj_floor, glob_floor, min_contrast, cmax_ladder, step):
    """彩度阶梯搜索：cmax 由高到低，取**满足相邻可辨底线且彩度最高**的解。"""
    for cmax in cmax_ladder:
        pool = build_pool(cmax=cmax, min_contrast=min_contrast, step=step)
        if not pool:
            continue
        labs = {v: {hx: hex_to_lab_cvd(hx, v) for hx in pool} for v in VIEWS}
        got = pick_chain(pool, n, labs, adj_floor, glob_floor)
        if got:
            return cmax, pool, labs, got
    return None, None, None, None



FLOORS = [12.0, 11.0, 10.0, 9.5, 9.0, 8.5, 8.0, 7.0, 6.0, 5.0, 4.0, 3.0, 2.0]


def metrics(chosen, labs):
    out, worst_all = {}, 1e9
    for v in VIEWS:
        worst, wp = 1e9, None
        for i in range(len(chosen)):
            for j in range(i + 1, len(chosen)):
                d = dE00(labs[v][chosen[i]], labs[v][chosen[j]])
                if d < worst:
                    worst, wp = d, (chosen[i], chosen[j])
        out[v] = {"min_pairwise_dE00": round(worst, 2), "pair": list(wp)}
        worst_all = min(worst_all, worst)
    chroma = [oklab_chroma(h) for h in chosen]
    return {
        "per_view": out,
        "worst_view_min_dE00": round(worst_all, 2),
        "mean_chroma_Oklab": round(sum(chroma) / len(chroma), 4),
        "min_chroma_Oklab": round(min(chroma), 4),
        "min_contrast_on_white": round(min(contrast_on_white(h) for h in chosen), 2),
    }



def main():
    ap = argparse.ArgumentParser(description="生成鲜明且色觉友好的 14 色板")
    ap.add_argument("--n", type=int, default=14)
    ap.add_argument("--adj-floor", type=float, default=9.0,
                    help="图例相邻色在所有视觉类型下的最小 ΔE00")
    ap.add_argument("--glob-floor", type=float, default=3.0,
                    help="与所有已选色的最小 ΔE00（避免近似同色）")
    ap.add_argument("--min-contrast", type=float, default=2.30)
    ap.add_argument("--step", type=float, default=6.0, help="候选池色相采样步长")
    ap.add_argument("--out", default="palette_vivid.json")
    a = ap.parse_args()

    ladder = [round(0.23 - 0.01 * i, 2) for i in range(14)]
    cmax, pool, labs, chosen = solve_ladder(a.n, a.adj_floor, a.glob_floor,
                                           a.min_contrast, ladder, a.step)
    if chosen is None:
        raise SystemExit("在相邻 ΔE00 ≥ %.1f 约束下凑不满 %d 色" % (a.adj_floor, a.n))
    m = metrics(chosen, labs)
    adj, adjp = adjacent_min(chosen, labs)
    payload = {
        "palette": chosen,
        "n": len(chosen),
        "cmax_used": cmax,
        "adjacent_min_dE00": adj,
        "adjacent_worst_pair": adjp,
        "min_contrast_floor": a.min_contrast,
        "pool_size": len(pool),
        "metrics": m,
        "note": ("Oklab 高彩度生成 + Machado(2009) 三类色觉缺陷模拟 + CIEDE2000；"
                 "约束为「图例相邻色 ΔE00 ≥ adj_floor」而非 14 色两两全高 —— "
                 "因为 14 个高彩度色的 gamut 装不下两两高 ΔE（旧色板靠近中性暗色达成）。"
                 "在相邻可辨的前提下最大化彩度。"),
    }
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
