#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_network.py —— M4: 关键词共现网络

用法:
    python3 build_network.py <库目录或.enl> [--node-df 5] [--min-edge 2] [--out DIR]
                             [--topics topics.json] [--layout]

[!]  执行顺序：共现网络的主题着色依赖聚类结果，故cluster_topics.py 必须先跑。
   不传 --topics 时本脚本完全独立可用（节点无主题字段，报告回退单色）。

口径（引用规模数字时必须连带标注，缺一不予采信）:
    normalize_case = lower   ← 关键：实测449 个概念有大小写变体，不归一会割裂社区
    df_mode        = doc     ← 文档频次（非词频）
    node_df        = 5
    min_edge_count = 2
    keyword_dedupe = per-doc

默认口径实测结果: 1094 节点 / 10672 边

[!]  本网络是【关键词共现网络】，不是【引文网络】。
   本地 .enl 的 references 字段是长度恒为10 的占位符（distinct=1），
   零引文数据 —— 这是 .enl 无 API 下的物理限制。
"""
from __future__ import annotations

import argparse
import base64
import itertools
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lit_core import (  # noqa: E402
    EnlError, EXIT, apply_term_aliases, coverage_report, emit, esc_csv_cell,
    find_enl, load_refs, load_term_aliases, lock_status, merge_suggestions,
)
from stat_helpers import fdr_bh, hypergeom_sf  # noqa: E402

# 噪声词：人口统计学 + 通用词。实测这些会成为 hub 吸走大量连线。
# [!]  不可"剔除 Top10"——workaholism(172度) 是核心研究构念，按度数一刀切会误删。
DEFAULT_NOISE = {
    "performance", "humans", "human", "work", "female", "male", "adult",
    "adults", "aged", "middle", "young", "old", "age", "sex", "gender",
    "model", "models", "theory", "research", "study", "effect", "effects",
    "analysis", "data", "results", "method", "methods", "role", "based",
}


def attach_topics(nodes, refs, topics, min_share=0.0, strong_share=0.5):
    """把「关键词 → 主题簇」关联写进节点。

    做法：用 topics.json 的 ref_ids（= int(r.id)，稳定主键）建 ref→cid 映射，
    再遍历每篇文献的关键词，给每个关键词累计它在各簇文献中出现的次数。
      count[w][cid]  = 关键词 w 出现在多少篇 cid 簇的文献里
    占比 = count[w][cid] / sum(count[w].values())，即该簇文献贡献了多少比例。

    产出字段：
      cluster_ids    —— 该关键词出现过的所有簇（按占比降序）
      primary_cluster—— 占比最高的簇（着色用）；无归属为 None
      primary_share  —— 最高占比 0–1（1.0 = 纯单簇）
      n_clusters     —— 出现过的簇数
      is_bridge      —— primary_share < strong_share，即「主簇不够 dominating」，
                        真正横跨多个主题的桥接词。报告里给它加次色描边。

    [!]  实测口径提醒（本数据集 1094 节点）：
       n_clusters>1 的节点占 94.8%，若用「跨簇数>1」判定桥接词，
       几乎所有节点都会被标为桥接 —— 该信号失去区分度。
       故桥接判定用 primary_share < 0.5（实测约 51% 节点），
       它衡量的是「归属是否集中」而非「是否出现过多簇」。

    注意：df 统计口径是「全部文献」，而占比的分母只算「落在某个簇里的文献」。
    未被聚类覆盖的文献（tier=empty 等）不参与分母，故 df 与占比之和不必相等。
    """
    ref2cid = {}
    for c in topics.get("clusters", []):
        cid = int(c["cluster_id"])
        for rid in c.get("ref_ids", []):
            ref2cid[int(rid)] = cid

    count = defaultdict(Counter)
    for r in refs:
        cid = ref2cid.get(int(r.id))
        if cid is None:
            continue
        for w in set(r.keywords):
            count[w][cid] += 1

    n_single = n_cross = n_none = n_bridge = 0
    for nd in nodes:
        w = nd["id"]
        c = count.get(w)
        if not c:
            nd["cluster_ids"] = []
            nd["primary_cluster"] = None
            nd["primary_share"] = 0.0
            nd["n_clusters"] = 0
            nd["is_bridge"] = False
            n_none += 1
            continue
        tot = sum(c.values())
        ranked = sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))
        cids = [cid for cid, _ in ranked]
        if min_share > 0:
            cids = [cid for cid, _ in ranked
                    if _ / tot >= min_share or cid == ranked[0][0]]
        share = ranked[0][1] / tot
        nd["cluster_ids"] = cids
        nd["primary_cluster"] = ranked[0][0]
        nd["primary_share"] = round(share, 4)
        nd["n_clusters"] = len(cids)
        nd["is_bridge"] = share < strong_share
        if len(cids) == 1:
            n_single += 1
        else:
            n_cross += 1
        if nd["is_bridge"]:
            n_bridge += 1

    # 簇规模（用于报告里按主题聚合关键词）
    cluster_meta = {
        int(c["cluster_id"]): {
            "size": c.get("size"),
            "pct": c.get("pct"),
            "top_terms": c.get("top_terms", [])[:12],
            "lang_dominant": c.get("lang_dominant"),
        }
        for c in topics.get("clusters", [])
    }
    n = len(nodes) or 1
    stats = {
        "topic_attribution": {
            "enabled": True,
            "source": "topics.json",
            "nodes_total": len(nodes),
            "single_cluster": n_single,
            "multi_cluster": n_cross,
            "unattributed": n_none,
            "bridge": n_bridge,
            "single_pct": round(n_single / n * 100, 1),
            "multi_pct": round(n_cross / n * 100, 1),
            "unattributed_pct": round(n_none / n * 100, 1),
            "bridge_pct": round(n_bridge / n * 100, 1),
            "bridge_threshold": strong_share,
            "clusters": len(cluster_meta),
            "note": ("multi_cluster 占比高（跨簇词多）是本领域关键词的固有特征，"
                     "故桥接词以 primary_share < %.2f 判定，而非「出现簇数>1」"
                     % strong_share),
        }
    }
    return stats, cluster_meta


def build(refs, node_df=5, min_edge=2, drop_noise=True, max_nodes=None,
          alias_map=None):
    """构建共现网络。返回 (nodes, edges, stats, edges_sig)。

    
      · alias_map 术语别名合并：中英对照（工作重塑=job crafting）与同义变体
        在**计数之前**归并到规范名；合并明细写入 stats["term_merge"]，
        未命中表的词一律保持原样（不自动做语义归并）。
      · 边级超几何精确检验 + BH-FDR 校正：edges_sig 与 edges 一一对应，
        stats["significance"] 给出检验口径与显著边数。
    """
    t0 = time.time()

    # 术语别名合并（先于一切计数）
    # v1.0.0：统计前先做**形式归一**（连字符/下划线 → 空格、压缩空白、小写）
    # —— organizational-behavior / artificial-intelligence 这类连字符写法
    # 即使命不中别名表也统一为空格形式，避免同一概念以两种写法各占节点。
    alias_hits = []
    per_doc_kw: list[set] = []
    try:
        from topic_labels import canonical_kw  # noqa: E402
    except Exception:
        def canonical_kw(k): return str(k).strip().lower()
    for r in refs:
        kws = [canonical_kw(k) for k in r.keywords]
        if alias_map:
            kws, hits = apply_term_aliases(kws, alias_map)
            alias_hits.extend(hits)
        per_doc_kw.append(set(kws))

    # 文档频次（per-doc 去重）+ 词→文档集（供泛词合并建议）
    # v1.0.0：统一变量口径过滤——网络节点/主题 chips 只保留有学术含义的
    # 研究变量（剔 MeSH 人口词、方法词、GENERIC 泛词、虚词），与
    # cluster_topics / keyword_network / cross_matrix 完全一致。
    try:
        from topic_labels import is_variable_term, _concept_zh  # noqa: E402
    except Exception:
        def is_variable_term(k): return True
        def _concept_zh(k): return None
    df = Counter()
    doc_sets: dict = defaultdict(set)
    for i, kws in enumerate(per_doc_kw):
        for w in kws:
            # 概念归一：词典命中的英文概念统一转中文名（hrm→人力资源管理），
            # 消灭画布中英夹杂——同一概念不再以两种语言各占节点
            w = _concept_zh(w) or w
            if not is_variable_term(w):
                continue
            df[w] += 1
            doc_sets[w].add(i)

    # 噪声词过滤：只剔人口统计学/通用词，不按度数剔
    if drop_noise:
        drop = {w for w in DEFAULT_NOISE if w in df}
    else:
        drop = set()

    keep = {w for w, c in df.items() if c >= node_df and w not in drop}
    if max_nodes and len(keep) > max_nodes:
        # [!]  并列 df 必须用 id 兜底排序。原key 只有 -df[w]，
        #而输入是 set —— 并列项的先后取决于 PYTHONHASHSEED，
        # 于是同一份库在不同进程里会选中**不同的**关键词子集。
        keep = set(sorted(keep, key=lambda w: (-df[w], w))[:max_nodes])

    # 边：per-doc 去重 + 排除自环 + 边键sorted 归一
    edge_count = Counter()
    for kws in per_doc_kw:
        sel = sorted({w for w in kws if w in keep})
        for a, b in itertools.combinations(sel, 2):
            if a == b:              # 必须跳自环，否则会产生大量 (k,k)
                continue
            edge_count[(a, b)] += 1

    edges = [(a, b, c) for (a, b), c in edge_count.items() if c >= min_edge]

    # ── 边级显著性：超几何精确检验 P(X>=w) + BH-FDR ──
    # 零假设：N 篇含关键词的文献里，两端词各自出现的 df_a / df_b 篇随机独立。
    n_docs = sum(1 for kws in per_doc_kw if kws)
    pvals = [hypergeom_sf(c, n_docs, df[a], df[b]) for a, b, c in edges]
    qs = fdr_bh(pvals)
    edges_sig = [{"source": a, "target": b, "weight": c,
                  "p": (f"{p:.2e}" if p < 1e-4 else round(p, 6)),
                  "q": (f"{q:.2e}" if q < 1e-4 else round(q, 6)),
                  "sig_fdr05": bool(q < 0.05)}
                 for (a, b, c), p, q in zip(edges, pvals, qs)]

    nodes = []
    deg = Counter()
    wsum = Counter()
    for a, b, c in edges:
        deg[a] += 1; deg[b] += 1
        wsum[a] += c; wsum[b] += c
    # [!]  keep 是 set，直接 `for w in keep` 的遍历顺序依赖
    # PYTHONHASHSEED —— 同一份库在不同进程里会得到不同的 nodes[] 顺序。
    # 由于 encode_pos()/encode_edges() 都按 nodes 顺序编号，
    # 这会让「第 i 个坐标」在不同运行里绑到**不同的关键词**上。
    # 故此处按 id 排序遍历，使顺序可复现。
    for w in sorted(keep):
        nodes.append({"id": w, "df": df[w], "degree": deg.get(w, 0),
                      "weight": wsum.get(w, 0)})

    # 规范名展示对照（报告中英文对照展示）：canonical -> "canonical / EN"
    term_display = {}
    if alias_map:
        for m in alias_map.values():
            c = m["canonical"]
            if c in keep and m.get("display_en"):
                term_display[c] = f"{c} / {m['display_en']}"

    stats = {
        "nodes": len(nodes), "edges": len(edges),
        "params": {
            "normalize_case": "lower", "df_mode": "doc", "node_df": node_df,
            "min_edge_count": min_edge, "keyword_dedupe": "per-doc",
            "drop_noise": drop_noise,
            "noise_words": sorted(drop)[:12],
            "term_aliases": bool(alias_map),
        },
        "term_merge": {
            "alias_pairs_applied": len(alias_hits),
            "merged_examples": alias_hits[:8],
            "display": term_display,
            # 泛词合并建议：只建议不自动合并，等用户确认后写 .local.csv
            "merge_suggestions": merge_suggestions(
                df, {w: doc_sets[w] for w in keep if w in doc_sets}),
        },
        "significance": {
            "test": "hypergeometric exact, upper tail P(X >= weight)",
            "population_docs": n_docs,
            "n_edges_tested": len(edges_sig),
            "n_sig_fdr05": sum(1 for e in edges_sig if e["sig_fdr05"]),
            "correction": "Benjamini-Hochberg FDR (q)",
        },
        "coverage": {
            "docs_with_keywords": sum(1 for kws in per_doc_kw if kws),
            "docs_total": len(refs),
        },
        "elapsed": round(time.time() - t0, 3),
        "isolated_keywords": len({w for kws in per_doc_kw for w in kws} - keep),
    }
    return nodes, edges, stats, edges_sig


def _fr_local(m, edges_idx, iters=60, rng=None):
    """簇内 Fruchterman-Reingold（纯 numpy）。返回 (m,2)，已归一化到 max|·| = 1。

    平衡点推导：斥力 k²/d² 与引力 d²/k 相等时 d = k，故取 k = 2/√m
    （目标区域为 [-1,1]²，即面积 4，k = √(4/m)），节点自然铺满而不外溢。
    """
    import numpy as np
    if m <= 1:
        return np.zeros((max(m, 0), 2))
    rng = rng if rng is not None else np.random.default_rng(0)
    pos = rng.random((m, 2)) * 2.0 - 1.0
    k = 2.0 / np.sqrt(m)
    if len(edges_idx):
        ea = np.fromiter((e[0] for e in edges_idx), dtype=np.int64, count=len(edges_idx))
        eb = np.fromiter((e[1] for e in edges_idx), dtype=np.int64, count=len(edges_idx))
    else:
        ea = eb = np.zeros(0, dtype=np.int64)
    t = 0.16 * (m ** 0.1)
    dt = t / (iters + 1)
    for _ in range(iters):
        diff = pos[:, None, :] - pos[None, :, :]
        d2 = (diff ** 2).sum(axis=2) + 0.01
        rep = (k * k / d2)[:, :, None] * diff
        np.einsum("iij->ij", rep)[...] = 0          # 对角置零
        att = np.zeros_like(pos)
        if len(ea):
            d = pos[ea] - pos[eb]
            dist = np.sqrt((d ** 2).sum(axis=1)) + 0.01
            f = (d / dist[:, None]) * (dist[:, None] ** 2 / k)
            np.add.at(att, ea, f)
            np.add.at(att, eb, -f)
        disp = rep.sum(axis=1) + att
        disp -= pos * 0.10                          # 轻微向心：抑制外扩、保持方形
        norm = np.linalg.norm(disp, axis=1, keepdims=True) + 1e-9
        pos += disp / norm * np.minimum(norm, t)   # 步长按温度衰减
        t -= dt
    pos -= pos.mean(axis=0, keepdims=True)
    span = float(np.abs(pos).max()) or 1.0
    return pos / span


def _pack_islands(islands, n_total, gap=0.30, aspect=1.55):
    """行式 shelf packing：把各主题「岛」排布到平面上，**保证互不重叠**。

    岛半径按 √(簇节点数) 分配（面积 ∝ 节点数），大簇视觉上更大。
    相邻岛心距恒 ≥ r_i + r_j + gap（水平与垂直方向都成立），
    因此不存在「软性排斥力调参」那种此消彼长的重叠问题。

    返回按全局节点下标拼装的 (n_total,2) 坐标。
    """
    import math
    import numpy as np
    if not islands:
        return np.zeros((n_total, 2))

    # 半径按 √size 分配，并归一到均值 1
    sizes = np.array([len(isl["members"]) for isl in islands], dtype=float)
    rs = np.sqrt(np.maximum(sizes, 1.0))
    rs = rs / rs.mean()

    # 目标版面：总面积（含填充损耗）→ 宽/高 ≈ aspect
    area = math.pi * float((rs ** 2).sum()) * 1.35
    W = math.sqrt(area * aspect)
    W = max(W, 2.0 * rs.max() + gap)

    order = sorted(range(len(islands)), key=lambda i: -rs[i])
    rows, cur, right = [], [], 0.0
    for i in order:
        r = float(rs[i])
        need = 2.0 * r + gap
        if cur and right + need > W:
            rows.append((cur, right))
            cur, right = [], 0.0
        cur.append((i, right + r))     # 行内左对齐堆叠，记录岛心 x
        right += need
    if cur:
        rows.append((cur, right))

    centers = {}
    y = 0.0
    for row, _w in rows:
        h = 2.0 * max(float(rs[i]) for i, _ in row)
        for i, cx in row:
            centers[i] = (cx, y + h / 2.0)
        y += h + gap

    max_w = max((w for _row, w in rows), default=1.0)
    pos = np.zeros((n_total, 2))
    for i, isl in enumerate(islands):
        cx, cy = centers[i]
        cx -= max_w / 2.0
        cy -= y / 2.0
        pos[isl["members"]] = isl["local"] * float(rs[i]) + (cx, cy)
    return pos


def layout(nodes, edges, iters=60, seed=42, cluster_seed=True, gravity=0.02):
    """关键词共现网络的「分簇岛」布局（纯 numpy、确定性、不依赖 networkx）。

    两阶段 + 几何打包，**从构造上保证簇间零重叠**：
      1. 簇内布局：每个主题簇独立跑 FR（只用簇内边），归一化到半径 1；
      2. 岛打包：按 √簇大小 分配半径，行式 packing，相邻岛心距 ≥ r_i+r_j+gap；
      3. 平移合成：各岛局部坐标平移到打包位。

    跨簇边**不参与布局**（渲染为岛间长边），故不会把岛拽合 —— 若让跨簇边参与
    布局、靠斥力/引力软性博弈，簇必然互相渗透，渲染成「彩色毛球」。

    无主题节点（primary_cluster is None）自成一个中性岛。
    `gravity` 仅为兼容旧签名保留，本实现不使用。
    cluster_seed=False 时退化为整体单次 FR（保持旧行为）。

    输出契约：返回 (n,2) ndarray，已居中且 np.abs(pos).max() == 1，
    供 encode_pos()（int16 量化）与报告渲染使用。
    """
    import numpy as np
    rng = np.random.default_rng(seed)
    n = len(nodes)
    if n == 0:
        return np.zeros((0, 2))

    idx = {nd["id"]: i for i, nd in enumerate(nodes)}
    pairs = [(idx[a], idx[b]) for a, b, _ in edges if a in idx and b in idx]

    islands = []
    if not cluster_seed:
        pos = _fr_local(n, pairs, iters, rng)
    else:
        cl = np.array([(nd.get("primary_cluster")
                        if nd.get("primary_cluster") is not None else -1)
                       for nd in nodes], dtype=int)
        # 中性岛（-1）排在最后
        for c in sorted(set(cl.tolist()), key=lambda c: (c == -1, c)):
            members = np.where(cl == c)[0]
            if len(members) == 0:
                continue
            remap = {int(g): j for j, g in enumerate(members)}
            loc_pairs = [(remap[ia], remap[ib]) for ia, ib in pairs
                         if cl[ia] == c and cl[ib] == c]
            islands.append({
                "members": members,
                "local": _fr_local(len(members), loc_pairs, iters, rng),
            })
        pos = _pack_islands(islands, n)

    # 按包围盒居中（而非均值），使 span 在两轴对称 → 充分利用画布与 int16 量程
    pos -= (pos.max(axis=0) + pos.min(axis=0)) / 2.0
    span = float(np.abs(pos).max()) or 1.0
    return pos / span



def encode_edges(edges, nodes):
    """边编码为 varint + base64。实测优于 gzip。
    注意：不能截断边数据 —— 实测摘要截断反使 HTML 增大 1532KB。"""
    idx = {nd["id"]: i for i, nd in enumerate(nodes)}
    buf = bytearray()
    for a, b, c in edges:
        for v in (idx[a], idx[b], c):
            while True:
                byte = v & 0x7F
                v >>= 7
                buf.append(byte | (0x80 if v else 0))
                if not v:
                    break
    return base64.b64encode(bytes(buf)).decode("ascii")


def encode_pos(pos, quantum=100):
    """布局坐标编码：int16 定点量化 + base64。

    体积实测：1094 节点 × 2 维 × 2 字节 = 4376 B → base64 约 5.9KB，
    相对 700KB 报告可忽略，却省掉首屏 O(n²) 计算。

    布局函数已把坐标归一化到 [-1,1]，故这里按 span 线性映射到 int16：
        q = round(coord / span * 30000)
    渲染端还原：coord = q / scale，scale = 30000/span。
    """
    import numpy as np
    a = np.asarray(pos, dtype=float)
    if a.size == 0:
        return {"pos_b64": "", "scale": 1.0, "span": 1.0, "quantum": quantum}
    span = float(np.abs(a).max()) or 1.0
    scale = 30000.0 / span
    q = np.rint(a * scale).astype("<i2")      # 已居中，可为负，int16 足够
    return {
        "pos_b64": base64.b64encode(q.tobytes()).decode("ascii"),
        "scale": round(scale, 8),
        "span": round(span, 6),
        "quantum": quantum,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="构建关键词共现网络")
    ap.add_argument("target")
    ap.add_argument("--node-df", type=int, default=5)
    ap.add_argument("--min-edge", type=int, default=2)
    ap.add_argument("--out", default="./out")
    ap.add_argument("--workspace", default="./.lit_work")
    ap.add_argument("--keep-noise", action="store_true", help="保留噪声词")
    ap.add_argument("--no-term-aliases", action="store_true",
                    help="关闭术语别名合并（默认启用 references/term_aliases.csv "
                         "的中英对照与同义合并；合并明细见 stats.term_merge）")
    ap.add_argument("--layout", action="store_true", help="预计算布局坐标")
    ap.add_argument("--topics", help="cluster_topics.py 产出的 topics.json；"
                                     "传入则计算关键词→主题归属（须先跑聚类）")
    ap.add_argument("--min-share", type=float, default=0.0,
                    help="跨簇主题计入 cluster_ids 的最小占比，0=全部计入")
    ap.add_argument("--bridge-share", type=float, default=0.5,
                    help="primary_share 低于此值判为桥接词（加次色描边）")
    args = ap.parse_args()

    try:
        target = Path(args.target).expanduser()
        is_norm = target.is_file() and target.suffix.lower() == ".json"
        enl = None if is_norm else find_enl(target)
        busy, _probe_ok, _probe_notice = (False, True, None) if is_norm else lock_status(enl)
        refs, src_meta = load_refs(target, args.workspace)

        alias_map = None if args.no_term_aliases else load_term_aliases()
        nodes, edges, stats, edges_sig = build(
            refs, node_df=args.node_df, min_edge=args.min_edge,
            drop_noise=not args.keep_noise, alias_map=alias_map)

        # ── 主题归属（须在 layout 之前，cluster_seed 依赖 primary_cluster）──
        cluster_meta = None
        if args.topics:
            tp = Path(args.topics).expanduser()
            if not tp.exists():
                print(f"[error] --topics 文件不存在: {tp}", file=sys.stderr)
                print(f"[hint] {EXIT[2]}", file=sys.stderr)
                return 2
            topics = json.loads(tp.read_text(encoding="utf-8"))
            attr_stats, cluster_meta = attach_topics(
                nodes, refs, topics, min_share=args.min_share,
                strong_share=args.bridge_share)
            stats.update(attr_stats)
        else:
            stats["topic_attribution"] = {
                "enabled": False,
                "hint": "未传 --topics，节点无主题字段；报告将回退单色渲染。",
            }

        cov = coverage_report(refs)
        # [!]  排序必须发生在 layout()/encode_pos() 之前。
        #    layout() 按传入 nodes 的顺序产出坐标；若在其后再排序，
        #    pos_encoded[i] 就与 payload["nodes"][i] 错位，而报告 JS 优先读
        #    pos_encoded（x/y 仅作兜底）→ 整张网络图渲染错乱、簇块被打散。
        # [!]  排序键必须构成**全序**。原 key 只有 -degree，
        #    并列度数时Python 的 sort 是稳定排序，但并列项的先后继承自
        #    上游 nodes 顺序（曾来自 set 遍历）→ 跨进程不稳定。
        #    追加 id 作为决胜键，使同输入必得同输出。
        nodes.sort(key=lambda x: (-x["degree"], x["id"]))

        pos = None
        if args.layout and nodes:
            pos = layout(nodes, edges)
            for i, nd in enumerate(nodes):
                nd["x"] = round(float(pos[i][0]), 2)
                nd["y"] = round(float(pos[i][1]), 2)

        payload = {
            "ok": True, "exit_code": 0,
            "library": {"name": src_meta["display_path"],
            "display_path": "…/" + src_meta["display_path"],
            "source": src_meta["source_label"]},
            "type": "keyword-cooccurrence",
            "mode": {
                "busy_detected": busy,
                "lock_probe_available": _probe_ok,
                "lock_probe_notice": _probe_notice,
            },
            "notice": "这是关键词共现网络，不是引文网络。本地 .enl 的 references "
                     "字段为占位符（长度恒为 10），零引文数据。",
            "stats": stats,
            "coverage": cov,
            "nodes": nodes,
            "edges": [{"source": a, "target": b, "weight": c} for a, b, c in edges],
            "edges_sig": edges_sig,
            "term_display": stats.get("term_merge", {}).get("display", {}),
        }
        if cluster_meta is not None:
            payload["cluster_meta"] = cluster_meta
        if nodes and args.layout:
            payload["edges_encoded"] = encode_edges(edges, nodes)
            payload["pos_encoded"] = encode_pos(pos)

        outdir = Path(args.out); outdir.mkdir(parents=True, exist_ok=True)
        (outdir / "network.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")

        # 明细 CSV：cluster_id 列输出真实主题归属（此前误写节点序号）
        import csv
        with open(outdir / "network_nodes.csv", "w", newline="",
                  encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["keyword", "df_doc", "degree", "weight",
                        "primary_cluster", "primary_share", "n_clusters",
                        "all_clusters"])
            for nd in nodes:
                w.writerow([
                    #关键词来自外部导入（CNKI/WoS/Zotero），属不可信输入，
                    # 以 = + - @ 开头会被 Excel 当公式执行 → 必须加固。
                    esc_csv_cell(nd["id"]),
                    nd["df"], nd["degree"], nd["weight"],
                    nd.get("primary_cluster") if nd.get("primary_cluster")
                    is not None else "",
                    nd.get("primary_share", ""), nd.get("n_clusters", ""),
                    esc_csv_cell(";".join(str(c) for c in nd.get("cluster_ids", []))),
                ])

        emit({"ok": True, "out": str(outdir), "stats": stats})
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
