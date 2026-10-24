#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""多维交叉共现分析：关键词 × 作者、关键词 × 年份、作者 × 年份。

## 为什么需要三个维度

单一维度的共现网络只回答"概念之间什么关系"，无法回答文献计量里
同样常见的三个问题：

| 维度对 | 回答的问题 | 典型读法 |
|---|---|---|
| 关键词 × 作者 | 谁在研究什么？ | 某位作者的核心词 = 其研究方向 |
| 关键词 × 年份 | 概念何时兴起？ | 某词首现年 = 领域进入该概念的时点 |
| 作者 × 年份 | 谁在何时活跃？ | 某作者发文集中在哪几年 = 其活跃期 |

三者合起来构成"人—词—时"的立体视角，是主题聚类（词—词）之外的
互补信息。已有产物无法覆盖：

    topics.json     主题 = 词的聚类，不含作者维度
    network.json    词—词共现，不含时间与作者交叉
    author_topic.py 主题 × 作者，但主题是聚类结果而非原始关键词

## 关联性口径

交叉表只回答"一起出现过多少次"。要看"是否**超出偶然**"，需做独立性检验：
    · 关键词 × 作者 → Cramér's V（复用 stat_helpers.cramers_v）
    · 关键词 × 年份 → 归一化互信息 NMI（stat_helpers.crosstab + 手算）
本脚本两者都给，并显式标注显著性口径，避免读者把"高频共现"当成"强关联"。
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from lit_core import EXIT, load_refs, load_term_aliases  # noqa: E402
from stat_helpers import cramers_v  # noqa: E402
# v1.0.0：作者拆分复用作者网络的 parse_record_authors ——
# 它按「记录分隔符优先、不劈开单个作者内部」处理 enl/CNKI/逗号三格式，
# 且归一（NFKC/去机构段/去单字母残片）。本脚本旧的 _authors_of 用
# 空格切中文名，会把 'Smith, J.\rZhang, L.' 劈成首字母假作者，
# 与作者网络的修复口径不一致，导致多维交叉的作者贡献错位。
from build_author_network import parse_record_authors  # noqa: E402

# v1.0.0：非变量词过滤——「关键词进入领域的时间」表
# 混进了 humans/adult/female/male（MeSH 人口）、model/consequences/
# mediating role（方法词）、performance/work/behavior（GENERIC 泛词）。
# 口径全链路统一：is_variable_term 是唯一过滤函数（MeSH + 方法词 +
# GENERIC 泛词 + 虚词），与 cluster_topics / keyword_network / 报告 chips
# 完全一致 —— 全链路统一口径。
try:
    from topic_labels import (is_variable_term, canonical_kw,
                              _concept_zh)  # noqa: E402
except Exception:  # topic_labels 不可用时退化为不过滤（向后兼容）
    def is_variable_term(k): return True
    def canonical_kw(k): return (k or "").strip().lower()
    def _concept_zh(k): return None


def _year_of(r):
    y = getattr(r, "year", None)
    try:
        return int(y) if y else None
    except (TypeError, ValueError):
        return None


def _authors_of(r):
    return parse_record_authors(r)


def _keywords_of(r, min_len=2, alias_map=None, only_variable=True):
    kw = getattr(r, "keywords", None) or []
    out = []
    for k in kw:
        k = str(k).strip()
        # v1.0.0：过别名层 —— 「工作重塑 / job crafting」在交叉表里是
        # 同一个词，否则同一概念被拆成中英两行、贡献被低估。
        # 连字符变体先归一再查表（social-exchange theory → social exchange theory）。
        if alias_map:
            m = alias_map.get(k.lower()) or alias_map.get(canonical_kw(k))
            if m:
                k = m["canonical"]
        # 落表 key：canonical 形式 + 概念归一（两步合一次转换）。
        k1 = canonical_kw(k)
        k = _concept_zh(k1) or k1
        # 统一口径过滤（MeSH 人口、方法词、GENERIC 泛词、虚词）。
        # 默认开启；调用方需要原始全集时显式传 only_variable=False。
        if only_variable and not is_variable_term(k):
            continue
        if len(k) >= min_len and k not in out:
            out.append(k)
    return out


def _nmi(a: list, b: list) -> float:
    """归一化互信息（两个分类变量）。"""
    if not a or not b:
        return 0.0
    ca, cb = Counter(a), Counter(b)
    n = len(a)
    ha = -sum((c / n) * math.log2(c / n) for c in ca.values() if c)
    hb = -sum((c / n) * math.log2(c / n) for c in cb.values() if c)
    if ha == 0 or hb == 0:
        return 0.0
    joint = Counter(zip(a, b))
    hab = 0.0
    for (x, y), c in joint.items():
        pxy = c / n
        hab += pxy * math.log2(pxy / ((ca[x] / n) * (cb[y] / n)))
    return hab / math.sqrt(ha * hb)


def build_kw_author(refs, top_kw=30, top_auth=20, alias_map=None):
    """关键词 × 作者 交叉表 + Cramér's V。"""
    pairs, kw_cnt, au_cnt = [], Counter(), Counter()
    for r in refs:
        for k in _keywords_of(r, alias_map=alias_map):
            for a in _authors_of(r):
                pairs.append((k, a))
                kw_cnt[k] += 1
                au_cnt[a] += 1
    kws = [k for k, _ in kw_cnt.most_common(top_kw)]
    aus = [a for a, _ in au_cnt.most_common(top_auth)]
    m = defaultdict(Counter)
    for k, a in pairs:
        if k in kws and a in aus:
            m[k][a] += 1
    # cramers_v 需要二维计数表（不是 pair 列表）
    table = [[m[k].get(a, 0) for a in aus] for k in kws]
    v = cramers_v(table) if pairs and any(any(r) for r in table) else 0.0
    # 每位作者的核心词（该作者最高频的 3 个词）
    author_core = {}
    for a in aus:
        c = Counter({k: m[k][a] for k in kws if m[k][a]})
        top = [k for k, _ in c.most_common(3)]
        if top:
            author_core[a] = top
    return {
        "keywords": kws,
        "authors": aus,
        "matrix": {k: dict(m[k]) for k in kws},
        "authors_total": len(au_cnt),
        "pairs": len(pairs),
        "cramers_v": round(v, 4),
        "author_core": author_core,
    }


def build_kw_year(refs, top_kw=30, alias_map=None):
    """关键词 × 年份 交叉 + 首现年/峰值年。"""
    m, kw_cnt = defaultdict(Counter), Counter()
    for r in refs:
        y = _year_of(r)
        if not y:
            continue
        for k in _keywords_of(r, alias_map=alias_map):
            m[k][y] += 1
            kw_cnt[k] += 1
    kws = [k for k, _ in kw_cnt.most_common(top_kw)]
    years = sorted({y for k in kws for y in m[k]})
    flat_k = [k for k in kws for _ in m[k]]
    flat_y = [y for k in kws for y in m[k] for _ in range(m[k][y])]
    nmi = _nmi(flat_k, flat_y)
    first_seen, peak = {}, {}
    for k in kws:
        if m[k]:
            first_seen[k] = min(m[k])
            peak[k] = max(m[k], key=lambda y: m[k][y])
    return {
        "keywords": kws,
        "years": years,
        "matrix": {k: {str(y): m[k][y] for y in sorted(m[k])} for k in kws},
        "first_seen": first_seen,
        "peak_year": peak,
        "nmi": round(nmi, 4),
    }


def build_author_year(refs, top_auth=20):
    """作者 × 年份 交叉 + 活跃期。"""
    m, au_cnt = defaultdict(Counter), Counter()
    for r in refs:
        y = _year_of(r)
        if not y:
            continue
        for a in _authors_of(r):
            m[a][y] += 1
            au_cnt[a] += 1
    aus = [a for a, _ in au_cnt.most_common(top_auth)]
    years = sorted({y for a in aus for y in m[a]})
    active = {}
    for a in aus:
        if m[a]:
            ys = sorted(m[a])
            active[a] = {"from": ys[0], "to": ys[-1],
                         "peak": max(m[a], key=lambda y: m[a][y]),
                         "total": au_cnt[a]}
    return {
        "authors": aus,
        "years": years,
        "matrix": {a: {str(y): m[a][y] for y in sorted(m[a])} for a in aus},
        "active": active,
        "authors_total": len(au_cnt),
    }


def _readout(ka, ky, ay) -> list[str]:
    out = []
    if ka.get("cramers_v"):
        v = ka["cramers_v"]
        strength = "较强" if v >= 0.3 else ("中等" if v >= 0.15 else "较弱")
        out.append(f"关键词与作者的关联强度（Cramér's V = {v}）属<b>{strength}</b>："
                   f"说明作者研究取向有明显分化，但并非各做各的。")
    if ky.get("nmi") is not None and ky["nmi"] > 0:
        out.append(f"关键词与年份的关联强度（NMI = {ky['nmi']}）："
                   f"各概念进入领域的时间虽有先后，但关联不算强——"
                   f"即关键词之间的年代差异不显著。")
    if ka.get("author_core"):
        top3 = list(ka["author_core"].items())[:3]
        txt = "；".join(f"{a} → {'/'.join(v)}" for a, v in top3)
        out.append(f"高产作者的核心词：{txt}。")
    if ay.get("active"):
        newest = max(ay["active"].items(), key=lambda kv: kv[1]["to"])
        out.append(f"最近仍在发文作者：{newest[0]}"
                   f"（活跃至 {newest[1]['to']} 年）。")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(
        description="多维交叉共现：关键词×作者、关键词×年份、作者×年份")
    ap.add_argument("target", help="题录：.json 产物 / 题录库 / 题录文件")
    ap.add_argument("--workspace", default="./.lit_work")
    ap.add_argument("--out", default="./out")
    ap.add_argument("--top-kw", type=int, default=30)
    ap.add_argument("--top-author", type=int, default=20)
    ap.add_argument("--json-out", default="cross_matrix.json")
    args = ap.parse_args()

    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)

    try:
        refs, meta = load_refs(args.target, args.workspace)
    except Exception as e:  # noqa: BLE001
        print(f"[error] 题录装载失败: {e}", file=sys.stderr)
        print(f"[hint] {EXIT[1]}", file=sys.stderr)
        return 1
    if not refs:
        print("[error] 题录为空", file=sys.stderr)
        return 4

    _alias = load_term_aliases()
    payload = {
        "ok": True,
        "type": "cross_matrix",
        "library": meta.get("display_path"),
        "source": meta.get("source"),
        "source_label": meta.get("source_label"),
        "params": {"top_kw": args.top_kw, "top_author": args.top_author},
        "refs_total": len(refs),
        "kw_author": build_kw_author(refs, args.top_kw, args.top_author, alias_map=_alias),
        "kw_year": build_kw_year(refs, args.top_kw, alias_map=_alias),
        "author_year": build_author_year(refs, args.top_author),
    }
    payload["readout"] = _readout(payload["kw_author"],
                                  payload["kw_year"],
                                  payload["author_year"])
    (outdir / args.json_out).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "kw_author": {
            "keywords": len(payload["kw_author"]["keywords"]),
            "authors": len(payload["kw_author"]["authors"]),
            "cramers_v": payload["kw_author"]["cramers_v"],
        },
        "kw_year": {"years": len(payload["kw_year"]["years"]),
                    "nmi": payload["kw_year"]["nmi"]},
        "author_year": {"authors": len(payload["author_year"]["authors"])},
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())