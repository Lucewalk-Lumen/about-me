#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trend_effects.py —— 主题 × 时期的效应量与趋势强度

回答一个文献计量里常被追问、但通常只靠"看图"回答的问题：
**「各主题的年份分布，真的有实质差异吗？差异有多大？」**

只报"某主题近年占比上升"是点估计，审稿人会问两件事：
  1. 主题与时期是否**真的相关**（不是随机波动）→ Cramér's V
  2. 主题能解释多少**年份方差**               → η²
再给每个主题的"近期占比"一个 bootstrap 置信区间，避免只报单点。

方法：
  · 列联表 = 主题 × 时期（早期 / 近期），Cramér's V = √(χ²/(n·min(r-1,c-1)))
  · η² = SS_between / SS_total（分组=主题，连续变量=出版年份）
  · 每个主题近期占比的 95% 百分位 bootstrap CI
  · ⚠️ 只给效应量与区间，**不给 p 值**（文献库不是抽样样本，p 值易被误读）

用法:
    python3 trend_effects.py "<库路径或 refs.json>" --topics ./out/topics.json
                             [--cut 2021] [--out ./out]
    # --cut 省略时默认 = 库内最大年份 - 4（即"近五年 vs 之前"）
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from endnote_core import EXIT, EnlError, emit, load_refs  # noqa: E402
from stat_helpers import bootstrap_ci, cramers_v, crosstab, eta_squared  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="主题 × 时期的效应量")
    ap.add_argument("target", help="库路径或 refs.json")
    ap.add_argument("--topics", required=True, help="topics.json（含 ref_ids）")
    ap.add_argument("--cut", type=int, default=None,
                    help="分期年份：>= cut 记为近期；默认 = 库内最大年份 - 4")
    ap.add_argument("--workspace", default="./.endnote_work")
    ap.add_argument("--out", default="./out")
    a = ap.parse_args()

    try:
        refs, meta = load_refs(a.target, a.workspace)
        topics = json.loads(Path(a.topics).read_text(encoding="utf-8"))
    except EnlError:
        raise
    except Exception as e:  # noqa: BLE001
        print(f"[error] 输入读取失败：{e}", file=sys.stderr)
        print(f"[hint] {EXIT[2]}", file=sys.stderr)
        return 2

    # ref_id → cluster_id
    ref2c: dict = {}
    for c in topics.get("clusters", []):
        for rid in c.get("ref_ids", []):
            ref2c[str(rid)] = int(c["cluster_id"])
    label_of = {int(c["cluster_id"]): ", ".join(c.get("top_terms", [])[:4])
                for c in topics.get("clusters", [])}

    years = [r.year for r in refs if r.year]
    if not years:
        print("[error] 全库无年份数据，无法做分期比较", file=sys.stderr)
        print(f"[hint] {EXIT[2]}", file=sys.stderr)
        return 2
    max_y = max(years)
    cut = a.cut if a.cut is not None else max_y - 4

    # 分组
    period_of, cluster_of = {}, {}
    years_by_cluster: dict[int, list[int]] = defaultdict(list)
    used = 0
    for r in refs:
        if not r.year:
            continue
        cid = ref2c.get(str(r.id))
        if cid is None:
            continue
        p = 1 if r.year >= cut else 0      # 1=近期, 0=早期
        key = (r.id,)
        period_of[r.id] = p
        cluster_of[r.id] = cid
        years_by_cluster[cid].append(int(r.year))
        used += 1

    if used < 30:
        print(f"[error] 可分期且已聚类的文献仅 {used} 篇，样本不足", file=sys.stderr)
        print(f"[hint] {EXIT[4]}", file=sys.stderr)
        return 4

    ids = sorted(cluster_of)
    ys = [period_of[i] for i in ids]
    cs = [cluster_of[i] for i in ids]

    # ── 效应量 ──
    cids_sorted = sorted(set(cs))
    idx = {c: i for i, c in enumerate(cids_sorted)}
    nk = len(cids_sorted)
    table = [[0, 0] for _ in range(nk)]
    for c, p in zip(cs, ys):
        table[idx[c]][p] += 1
    V = cramers_v(table)
    eta2 = eta_squared(*[years_by_cluster[c] for c in cids_sorted])

    # ── 每主题的前后期占比 + bootstrap CI ──
    import numpy as np
    arr_c = np.asarray([idx[c] for c in cs], dtype=int)
    arr_p = np.asarray(ys, dtype=int)
    n_total = len(arr_p)
    n_recent = int(arr_p.sum())
    n_early = n_total - n_recent

    rows = []
    for c in cids_sorted:
        m = arr_c == idx[c]
        e = int(((arr_p == 0) & m).sum())
        r = int(((arr_p == 1) & m).sum())
        tot = e + r
        if tot == 0:
            continue
        share_e = e / n_early * 100 if n_early else 0.0
        share_r = r / n_recent * 100 if n_recent else 0.0

        # CI 必须与所报统计量同源：报出的是「近期文献中该簇的占比」，
        # 故对（簇, 时期）配对整体重抽样并重算 r / n_recent。
        idx_all = np.arange(n_total)

        def _share_recent(ix):
            cc = arr_c[ix]
            pp = arr_p[ix]
            denom = int((pp == 1).sum())
            if denom == 0:
                return 0.0
            return float(((cc == idx[c]) & (pp == 1)).sum()) / denom

        lo, hi = bootstrap_ci(idx_all, _share_recent, n_boot=1000, alpha=0.05, seed=42)
        delta = share_r - share_e
        if abs(delta) < 2.0:
            direction = "平稳"
        elif delta > 0:
            direction = "上升"
        else:
            direction = "下降"
        rows.append({
            "cluster_id": int(c),
            "label": label_of.get(c, ""),
            "n_early": e, "n_recent": r, "n_total": tot,
            "share_early_pct": round(share_e, 1),
            "share_recent_pct": round(share_r, 1),
            "delta_pp": round(delta, 1),
            "recent_share_ci95": [round(lo * 100, 1), round(hi * 100, 1)],
            "direction": direction,
            "mean_year": round(float(np.mean(years_by_cluster[c])), 1),
        })
    rows.sort(key=lambda x: -x["delta_pp"])

    # 解读（阈值沿用通用约定：V 0.1 小 / 0.3 中 / 0.5 大；η² 0.01/0.06/0.14）
    def _lv(v, lo, mid, hi):
        return "大" if v >= hi else ("中" if v >= mid else ("小" if v >= lo else "可忽略"))
    interp = {
        "cramers_v": round(V, 4),
        "cramers_v_level": _lv(V, 0.10, 0.30, 0.50),
        "eta_squared": round(eta2, 4),
        "eta_squared_level": _lv(eta2, 0.01, 0.06, 0.14),
        "reading": (
            "主题与时期的关联强度为{v_lv}（V={v}），主题解释了年份方差的 "
            "{e:.1%}（η²={e}）。"
        ).format(v_lv=_lv(V, 0.10, 0.30, 0.50), v=round(V, 3),
                 e=round(eta2, 4)),
    }
    if V < 0.10:
        interp["caveat"] = ("关联很弱：各主题的年份分布差异不大，"
                            "不宜把个别主题的占比变化当作趋势结论。")
    else:
        interp["caveat"] = ("存在可辨识的时序结构；但仍需注意早期年份样本量较小，"
                            "结论应结合每主题的实际篇数判断。")

    payload = {
        "ok": True,
        "source": meta.get("source_label"),
        "cut_year": cut,
        "n_used": used,
        "n_early": n_early, "n_recent": n_recent,
        "n_clusters": nk,
        "effects": interp,
        "by_cluster": rows,
        "note": "只提供效应量与 bootstrap 置信区间，不含 p 值（文献库非抽样样本）。",
    }

    outdir = Path(a.out)
    try:
        outdir.mkdir(parents=True, exist_ok=True)
    except FileExistsError:
        pass
    (outdir / "trend_effects.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"[ok] 分期：早期 <{cut}（{n_early} 篇） / 近期 >={cut}（{n_recent} 篇）",
          file=sys.stderr)
    print(f"[ok] Cramér's V = {V:.3f}（{interp['cramers_v_level']}）  "
          f"η² = {eta2:.4f}（{interp['eta_squared_level']}）", file=sys.stderr)
    print(f"     {interp['reading']}", file=sys.stderr)
    print(f"     {interp['caveat']}", file=sys.stderr)
    for r in rows[:5]:
        print(f"     簇{r['cluster_id']:>2} {r['direction']} "
              f"{r['share_early_pct']}%→{r['share_recent_pct']}% "
              f"(Δ{r['delta_pp']:+.1f}pp) CI{r['recent_share_ci95']} "
              f"{r['label'][:34]}", file=sys.stderr)
    emit(payload)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except EnlError as e:
        print(f"[error] {e}", file=sys.stderr)
        print(f"[hint] {EXIT[e.code]}", file=sys.stderr)
        sys.exit(e.code)
    except Exception as e:  # noqa: BLE001
        # ⚠️ 缺这层兜底时，未预期异常会裸 traceback 并**退出码 1**——
        # 而 1 在 EXIT 契约里是「源库不可用：请检查移动硬盘是否连接」，
        # Agent 会据此给用户完全错误的修复指引（独立复审实测）。
        print(f"[error] 未预期异常：{type(e).__name__}: {e}", file=sys.stderr)
        print(f"[hint] {EXIT[5]}", file=sys.stderr)
        sys.exit(5)
