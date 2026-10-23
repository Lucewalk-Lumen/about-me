#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""关键词共现网络 + CiteSpace 式年轮权重（逐词 × 逐年频次）。

## 为什么单独一个脚本

原 `build_network.py` 产出的**也是关键词共现网络**（节点=关键词、边=同篇共现），
服务于主题着色与分簇岛布局；本脚本在此基础上**额外产出逐词 × 逐年频次**，
供 CiteSpace 式年轮与关键词突现检测使用：

    节点 = 关键词
    边的粗细 = 两词共现次数（同篇文献内同时出现）
    年轮色带 = 该词在各年份的出现频次（紫=早 → 红=晚）
    年轮厚度 ∝ 该年频次

两种网络回答不同问题，混在一起会让读者误读，因此独立产出。

## 与 CiteSpace 的对应关系

| CiteSpace 概念 | 本脚本字段 |
|---|---|
| 节点大小 = 词频 | `degree`（= 该词参与共现的次数） |
| 节点年轮 = 逐年颜色 | `years: {年份: 频次}` |
| 年轮颜色紫→红 | 年份越早越紫、越晚越红（与 overlay 视图一致） |
| 年轮厚度 ∝ 频次 | 绘制时按 `years` 的占比分配角度 |
| 高中介中心性 = 转折点 | `betweenness`（由 build_network.py 的 SNA 补充） |

## 设计取舍

- **只保留出现在 ≥2 篇文献里的词**（共现至少 1 次），单篇词无法构成共现。
- **低频但重要的词可通过 `--min-df` 放宽**；默认 2 是文献计类的惯例。
- 年轮数据直接来自题录的年份字段，无需外部数据源，离线可跑。
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from lit_core import (  # noqa: E402
    EXIT, Ref, emit, esc_csv_cell, load_refs, load_term_aliases,
)

# v1.0.0：关键词网络也过别名 + 剔除非变量词。
# 问题：网络里混进 humans/model/mediating role 等 MeSH 人口/方法词、
# performance/work 等泛词；且同一概念被拆成「工作重塑 / job crafting」
# 两个节点，把网络拉稀、节点数被稀释。
# 口径全链路统一：is_variable_term 是唯一过滤函数（MeSH + 方法词 +
# GENERIC 泛词 + 虚词），与 cluster_topics / cross_matrix / 报告 chips
# 完全一致 —— 全链路统一口径。
try:
    from topic_labels import (is_variable_term, canonical_kw,
                              _concept_zh)  # noqa: E402
except Exception:
    def is_variable_term(k): return True
    def canonical_kw(k): return (k or "").strip().lower()
    def _concept_zh(k): return None


def collect_keyword_stats(refs: list[Ref], alias_map: dict | None = None,
                          only_variable: bool = True) -> tuple[Counter, Counter, dict]:
    """统计 (词→出现频次 df, 词→逐年频次, 词→共现伙伴计数)。

    关键词整词保留（不切分）——它们本身即作者给定的完整术语，
    切碎会破坏语义（详见 domain_dict 模块说明）。

    两道清洗：
      1) 别名归一：`alias_map` 把「job crafting / 工作重塑」折成同一个节点，
         避免同概念分裂导致网络稀释、节点数被低估；
      2) 变量过滤：`only_variable=True` 剔除 MeSH 人口词（humans/adult/female）、
         方法词（model/mediating role/consequences）、GENERIC 泛词
         （performance/work/behavior）——它们不是研究变量，
         进网络/时间线没有学术含义。
    """
    df: Counter = Counter()
    yc: dict[str, Counter] = defaultdict(Counter)
    co: dict[str, Counter] = defaultdict(Counter)

    for r in refs:
        kws = list(getattr(r, "keywords", None) or [])
        if not kws:
            continue
        # 别名归一（v1.0.0）——连字符变体先归一再查表，
        # 让「social-exchange theory」命中「social exchange theory」；
        # 落节点 key 统一 canonical 形式（job-performance → job performance）
        # 再做**概念归一**：词典命中的英文概念统一转中文名（hrm→人力资源管理、
        # leader member exchange→领导-成员交换）——多次实测画布中英夹杂，
        # 中文库里的同一概念以两种语言各占节点，合并后网络更紧、画布统一。
        if alias_map:
            normed = []
            for k in kws:
                k = str(k).strip()
                m = alias_map.get(k.lower()) or alias_map.get(canonical_kw(k))
                if m:
                    k = m["canonical"]
                normed.append(canonical_kw(k))
            kws = normed
        else:
            kws = [canonical_kw(k) for k in kws]
        kws = [_concept_zh(k) or k for k in kws]
        # 变量过滤（v1.0.0，统一口径）
        if only_variable:
            kws = [k for k in kws if is_variable_term(k)]
        if not kws:
            continue
        # 同一文献内去重（一篇文献里同一词出现多次只计一次）
        uniq = sorted(set(kws))
        year = getattr(r, "year", None)
        for w in uniq:
            df[w] += 1
            if year:
                yc[w][int(year)] += 1
        # 共现：同篇内两两配对
        for i in range(len(uniq)):
            for j in range(i + 1, len(uniq)):
                a, b = uniq[i], uniq[j]
                co[a][b] += 1
                co[b][a] += 1
    return df, yc, co


def build_edges(co: dict[str, Counter], df: Counter,
                min_df: int = 2) -> list[dict]:
    """生成共现边。过滤：两端都需满足 min_df，且边权≥1。"""
    ids = [w for w, f in df.items() if f >= min_df]
    idset = set(ids)
    edges: list[dict] = []
    for a in ids:
        for b, w in co.get(a, {}).items():
            if b not in idset or b <= a:      # 去重：只取 a<b
                continue
            if w < 1:
                continue
            edges.append({"source": a, "target": b, "weight": w})
    edges.sort(key=lambda e: (-e["weight"], e["source"], e["target"]))
    return edges


def layout(nodes: list[dict], edges: list[dict], width: int = 1000,
           height: int = 760, iters: int = 260) -> None:
    """确定性力导向布局（纯 numpy-free 实现，保持零重依赖）。

    与 build_network.py 同思路：先按度数给初始同心圆位置，再用
    「边吸引 + 全体斥力」迭代。无随机数 → 同一输入必得同一输出
    （包内run_checks.py 有可复现性断言）。
    """
    import numpy as np

    n = len(nodes)
    if n == 0:
        return
    idx = {d["id"]: i for i, d in enumerate(nodes)}
    rng = np.random.default_rng(42)      # 固定种子 → 可复现
    # 初始位置：按度数降序排成同心圆，半径随序号增大
    order = np.argsort([-d["degree"] for d in nodes])
    pos = np.zeros((n, 2))
    for rank, i in enumerate(order):
        ang = 2 * math.pi * rank / max(n, 1)
        rad = 60 + 330 * math.sqrt(rank / max(n, 1))
        pos[i] = [rad * math.cos(ang), rad * math.sin(ang)]

    adj = np.zeros((n, n))
    for e in edges:
        i, j = idx.get(e["source"]), idx.get(e["target"])
        if i is not None and j is not None:
            adj[i, j] = adj[j, i] = e["weight"]
    deg = np.array([d["degree"] for d in nodes], dtype=float)
    wmax = float(deg.max()) if n else 1.0

    area = width * height
    k = math.sqrt(area / n) * 0.62
    temp = width * 0.08
    cool = temp / (iters + 1)

    for it in range(iters):
        delta = pos[:, None, :] - pos[None, :, :]          # (n,n,2)
        dist = np.linalg.norm(delta, axis=2)                # (n,n)
        np.fill_diagonal(dist, 1e-6)
        # 斥力：所有节点对之间；delta 与 dist 同形，逐对相加后按行汇总
        rep_vec = (k * k / dist ** 2)[:, :, None] * delta   # (n,n,2)
        rep = rep_vec.sum(axis=1)                           # (n,2)
        # 吸引力：仅边存在处
        att = np.zeros_like(pos)                            # (n,2)
        m = adj > 0
        if m.any():
            rows, cols = np.nonzero(m)
            for r, c in zip(rows, cols):
                d_ = dist[r, c]
                f_ = (adj[r, c] / wmax) * d_ / k
                v_ = delta[r, c] / d_
                att[r] -= f_ * v_
                att[c] += f_ * v_
        disp = rep + att
        norm = np.linalg.norm(disp, axis=1, keepdims=True)
        norm[norm == 0] = 1e-9
        pos += disp / norm * np.minimum(norm, temp)
        pos[:, 0] = np.clip(pos[:, 0], -width / 2 + 30, width / 2 - 30)
        pos[:, 1] = np.clip(pos[:, 1], -height / 2 + 30, height / 2 - 30)
        temp -= cool

    pos -= pos.mean(axis=0)
    for i, d in enumerate(nodes):
        d["x"] = round(float(pos[i, 0]), 2)
        d["y"] = round(float(pos[i, 1]), 2)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="关键词共现网络（含逐年频次，供 CiteSpace 式年轮绘制）")
    ap.add_argument("target", help="题录库目录 / .enl 文件 / refs.json")
    ap.add_argument("--workspace", default="./.lit_work")
    ap.add_argument("--out", default="./out")
    ap.add_argument("--min-df", type=int, default=2,
                    help="关键词最少出现文献数（默认 2，共现的最低门槛）")
    ap.add_argument("--top", type=int, default=120,
                    help="最多保留多少个节点（按词频降序，默认 120；v1.0.0 从 60 提高，"
                         " 实测 60 词在高密度库中显得网络稀疏、标签不足）")
    args = ap.parse_args()

    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)

    try:
        refs, meta = load_refs(args.target, args.workspace)
    except Exception as e:                      # noqa: BLE001
        print(f"[error] 题录装载失败: {e}", file=sys.stderr)
        print(f"[hint] {EXIT[1]}", file=sys.stderr)
        return 1

    if not refs:
        print("[error] 题录为空，无关键词可分析", file=sys.stderr)
        print(f"[hint] {EXIT[4]}", file=sys.stderr)
        return 4

    df, yc, co = collect_keyword_stats(refs, alias_map=load_term_aliases(),
                                       only_variable=True)
    if not df:
        print("[error] 所有题录都没有关键词字段——共现网络无从构建", file=sys.stderr)
        print("[hint] 请确认导入时是否保留了 %K / keywords 字段", file=sys.stderr)
        return 2

    edges = build_edges(co, df, args.min_df)
    ids = sorted({w for w, f in df.items() if f >= args.min_df},
                 key=lambda w: (-df[w], w))[: args.top]
    idset = set(ids)
    edges = [e for e in edges if e["source"] in idset and e["target"] in idset]

    if not ids or not edges:
        print("[error] 过滤后没有可用的关键词共现边——请降低 --min-df 或 --top", file=sys.stderr)
        print(f"[hint] {EXIT[4]}", file=sys.stderr)
        return 4

    # 节点度数 = 该词参与共现的次数
    deg: Counter = Counter()
    for e in edges:
        deg[e["source"]] += 1
        deg[e["target"]] += 1

    yr_lo = min((y for w in ids for y in yc.get(w, {})), default=None)
    yr_hi = max((y for w in ids for y in yc.get(w, {})), default=None)

    nodes = []
    for w in ids:
        years = {str(y): c for y, c in sorted(yc.get(w, {}).items())}
        yvals = list(yc.get(w, {}).values())
        nodes.append({
            "id": w,
            "df": df[w],                 # 词频（文献数）
            "degree": deg[w],            # 共现度
            "years": years,              # 年轮数据：逐年频次
            "first_year": min(yc[w]) if yc.get(w) else None,
            "last_year": max(yc[w]) if yc.get(w) else None,
            "peak_year": (max(yc[w].items(), key=lambda kv: (kv[1], -kv[0]))[0]
                          if yc.get(w) else None),
        })

    layout(nodes, edges)

    payload = {
        "ok": True,
        "type": "keyword_cooccurrence",
        "purpose": "年轮权重：节点=关键词，边=共现次数，年轮色带=逐年频次",
        "library": meta.get("display_path"),
        "source": meta.get("source"),
        "source_label": meta.get("source_label"),
        "params": {"min_df": args.min_df, "top": args.top},
        "year_range": [yr_lo, yr_hi],
        "stats": {
            "refs_total": len(refs),
            "keywords_total": len(df),
            "keywords_kept": len(nodes),
            "edges": len(edges),
            "refs_with_keywords": sum(
                1 for r in refs if getattr(r, "keywords", None)),
        },
        "coverage": {
            "keyword_coverage_pct": round(
                100.0 * sum(1 for r in refs if getattr(r, "keywords", None)) / len(refs), 1),
            "dropped_below_min_df": len(df) - len(
                [w for w in df if df[w] >= args.min_df]),
            "dropped_beyond_top": max(
                0, len([w for w in df if df[w] >= args.min_df]) - len(nodes)),
        },
        "nodes": nodes,
        "edges": edges,
    }

    (outdir / "keyword_network.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    with open(outdir / "keyword_network_edges.csv", "w", newline="",
              encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["source", "target", "weight"])
        for e in edges:
            w.writerow([esc_csv_cell(e["source"]),
                        esc_csv_cell(e["target"]), e["weight"]])

    emit(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())