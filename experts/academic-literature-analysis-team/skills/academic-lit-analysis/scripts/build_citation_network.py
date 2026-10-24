#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_citation_network.py —— 引文网络（共被引 co-citation / 文献耦合 coupling）

用法:
    python3 build_citation_network.py <refs.json> [--mode cocitation|coupling]
        [--min-edge 2] [--min-df 1] [--top N] [--keep-isolated]
        [--seed 42] [--no-layout] [--out DIR]

为什么单独一个脚本（而不是扩展 build_network.py）:
    与 build_institution_network.py 同理——build_network.py 已被 run_checks 的
    行为断言锁定，且其节点语义是关键词。引文网络节点语义完全不同，独立成文件
    可把回归面收敛在新增脚本内。

两种口径的区别（用户明确要求说清）:
    · 共被引 co-citation（默认）：节点 = **参考文献**；两篇参考文献被同一篇
      文献同时引用即连边。回答"哪些被引工作经常被一起引用"。
    · 文献耦合 bibliographic coupling：节点 = **文献本身**；两篇文献引用集合
      有交集即连边，边权 = 共同引用的参考文献数。回答"哪些文献在引用层面上相似"。
    二者方向相反：共被引看"被引端"的相似，耦合看"施引端"的相似。

输入契约（唯一来源：import_sources.py 模块头「机构与被引字段」）:
    refs.json 的每条记录可含可选字段 references: ["<被引原始条目>", ...]。
    缺该键 ⇔ 该篇无被引数据（CNKI / Zotero 导出通常无 → 会触发空态提示）。

被引条目归一（ref_key）——决定"两条被引是不是同一篇"的关键:
    1) 含 DOI  → key = "doi:<doi 小写>"（最可靠，优先）；
    2) 否则    → key = "au:<作者归一>|<年份>"（WoS CR 形如 "SMITH J, 2020, …"；
                 CNKI 形如 "[1] 张三. 题名[D]. 来源, 2020."）；
    3) 再否则  → key = "str:<归一化整串前 80 字>"（兜底）。
    [!]  已知限制：无 DOI 时靠"作者+年份"启发式判定同一篇，可能把同一作者同年的
    不同著作误并、或把同一著作的不同写法误分。**优先用带 DOI 的来源（WoS）**。

## 布局与着色（与作者网络同一套契约，2026-10 修复「一个色 / 都排在一起」）

报告端机构 / 引文两张画布原先**没有任何坐标**，报告 JS 只能走"最后防线"把节点
排成规则网格，且节点填充色是单一常量，可读性差。
本脚本现在与 `build_author_network.py` 完全同构地产出：

    · pos_encoded / edges_encoded —— base64(int16) 内联坐标 / 边（省首屏布局）；
    · nodes[i].x / nodes[i].y   —— 明文坐标（pos_encoded 缺失时的兜底）；
    · nodes[i].component / component_size —— 连通分量（供报告端按群着色）。

布局、编码与社群发现由共享模块 `_netutil.py` 提供（此前在作者 / 机构 / 引文三脚本
逐字节复制，易漂移；现统一收敛，三类网络行为完全一致）。布局为纯标准库
Fruchterman–Reingold（本环境无 numpy），固定 `--seed`（默认 42）→ 同输入必得同输出；
`_netutil.fr_layout` 含 v1.0.0 的"重叠消除"松弛。

## 孤立节点默认剔除（与作者网络同一策略）

度为 0 的节点（本库内不与其他任何节点共现）没有关系信息，画进网络只是噪音，
故**默认不输出**；剔除数量如实写进 `stats.isolated_dropped`，不静默删除。
显式加 `--keep-isolated` 可保留（保留时它们各自成为单元素分量，报告端按群着色）。

输出（schema 与 build_network.py 的 network.json 严格对齐）:
    <out>/citation_network.json
    <out>/citation_network_nodes.csv
空态: 0 篇含 references 时打印明确中文提示并落盘 empty_state=true 的 JSON，exit 0。

退出码: 0 成功（含空态降级）/ 1 输入不可用 / 2 输入非 refs.json / 5 未预期缺陷
"""
from __future__ import annotations

import argparse
import csv
import itertools
import json
import re
import sys
import time
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# 布局 / 编码 / 社群：共享实现（见 _netutil.py —— 收敛此前三处逐字节复制）
from _netutil import (  # noqa: E402
    layout as _layout, communities as _communities,
    encode_pos, encode_edges,
)
from lit_core import EXIT, EnlError, emit, esc_csv_cell  # noqa: E402

_REFS_FORMAT = "academic-lit-analysis/refs@1"
_DOI = re.compile(r"(10\.\d{4,9}/[^\s\"<>]+)")
_YEAR = re.compile(r"(?:19|20)\d{2}")
_LEAD_NUM = re.compile(r"^\s*\[\d+\]\s*")            # CNKI 引文的 "[1]" 前缀
_NOT_WORD = re.compile(r"[^\w\u4e00-\u9fff]+")


def load_payload(path: Path) -> dict:
    """读取 refs.json 原始载荷（不经 refs_from_json，避免扩展字段被丢弃）。"""
    if path.suffix.lower() != ".json":
        raise EnlError(2, f"本能力依赖 refs.json 的 references 字段；"
                          f"请先用 import_sources.py 把 {path.name} 归一化为 refs.json")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise EnlError(2, f"不是合法 JSON：{e}")
    if payload.get("format") != _REFS_FORMAT:
        raise EnlError(2, f"不是本工具 refs.json 产物（format={payload.get('format')!r}）")
    return payload


def ref_key(raw: str):
    """把一条被引条目归一为 (key, label)。无法识别时返回 (None, None)。"""
    s = re.sub(r"\s+", " ", unicodedata.normalize("NFKC", str(raw or ""))).strip().rstrip(".")
    if not s:
        return None, None
    m = _DOI.search(s)
    if m:
        doi = m.group(1).rstrip(".,;)").lower()
        return "doi:" + doi, s
    s2 = _LEAD_NUM.sub("", s)
    ym = _YEAR.search(s2)
    year = ym.group(0) if ym else ""
    s3 = s2[: ym.start()] if ym else s2
    # 作者段：优先取首个逗号前（WoS CR），否则首个句点前（CNKI GB/T），再否则整段
    if "," in s3:
        au = s3.split(",", 1)[0]
    elif "." in s3:
        au = s3.split(".", 1)[0]
    elif "[" in s3:
        au = s3.split("[", 1)[0]
    else:
        au = s3
    au = _NOT_WORD.sub(" ", au).strip().casefold()
    if au and year:
        return f"au:{au}|{year}", s
    norm = _NOT_WORD.sub("", s2.casefold())
    if not norm:
        return None, None
    return "str:" + norm[:80], s


def build(refs: list, mode: str = "cocitation", min_edge: int = 2,
          min_df: int = 1, top: int | None = None,
          keep_isolated: bool = False):
    """构建引文网络。返回 (nodes, edges, stats)。

    默认剔除度为 0 的孤立节点（无共现 = 无关系信息，画上去只是噪音）；
    `keep_isolated=True` 可保留。每个节点带 `component` / `component_size`
    （连通分量 id 与规模，按规模降序稳定编号，最大群 id=0）。
    """
    t0 = time.time()
    docs_total = len(refs)
    docs_with_refs = sum(1 for r in refs if (r.get("references") or []))

    if mode == "cocitation":
        # 每篇文献的参考文献 key 集合（篇内去重）
        disp_count: dict[str, Counter] = defaultdict(Counter)
        doc_keys: list[list[str]] = []
        for r in refs:
            keys = []
            for raw in (r.get("references") or []):
                k, lab = ref_key(raw)
                if not k:
                    continue
                disp_count[k][lab] += 1
                keys.append(k)
            doc_keys.append(sorted(set(keys)))

        df = Counter()
        for keys in doc_keys:
            for k in keys:
                df[k] += 1

        edge_count = Counter()
        for keys in doc_keys:
            for a, b in itertools.combinations(keys, 2):
                edge_count[(a, b)] += 1

        edges_k = [(a, b, c) for (a, b), c in edge_count.items() if c >= min_edge]
        deg = Counter()
        for a, b, c in edges_k:
            deg[a] += 1
            deg[b] += 1
        keep = {k for k, n in df.items() if n >= min_df}
        if top and len(keep) > top:
            keep = set(sorted(keep, key=lambda k: (-deg.get(k, 0), -df[k], k))[:top])
        edges_k = [(a, b, c) for (a, b, c) in edges_k if a in keep and b in keep]

        deg = Counter()
        wsum = Counter()
        for a, b, c in edges_k:
            deg[a] += 1
            deg[b] += 1
            wsum[a] += c
            wsum[b] += c

        def label_of(k):
            return sorted(disp_count[k].items(), key=lambda kv: (-kv[1], kv[0]))[0][0][:160]

        nodes = [{
            "id": k, "label": label_of(k), "df": df[k],
            "degree": deg.get(k, 0), "weight": wsum.get(k, 0),
        } for k in sorted(keep, key=lambda k: (-deg.get(k, 0), -df[k], k))]
        edges = [{"source": a, "target": b, "weight": c} for a, b, c in edges_k]

    else:  # coupling：节点=文献，边=共享被引数
        doc_keys = {}
        for r in refs:
            ks = {ref_key(raw)[0] for raw in (r.get("references") or [])}
            ks.discard(None)
            if ks:
                doc_keys[str(r.get("id"))] = ks
        docs = sorted(doc_keys)
        title_of = {str(r.get("id")): (r.get("title") or "")[:160] for r in refs}
        edge_count = Counter()
        for i, j in itertools.combinations(docs, 2):
            shared = len(doc_keys[i] & doc_keys[j])
            if shared:
                edge_count[(i, j)] = shared
        edges_k = [(a, b, c) for (a, b), c in edge_count.items() if c >= min_edge]
        # coupling 的 min_df 对"文献节点"无意义（df=被引条目数），故不据此裁节点
        keep = {d for d in docs if len(doc_keys[d]) >= 1}
        if top and len(keep) > top:
            deg = Counter()
            for a, b, _ in edges_k:
                deg[a] += 1
                deg[b] += 1
            keep = set(sorted(keep, key=lambda d: (-deg.get(d, 0), -len(doc_keys[d]), d))[:top])
        edges_k = [(a, b, c) for (a, b, c) in edges_k if a in keep and b in keep]
        deg = Counter()
        wsum = Counter()
        for a, b, c in edges_k:
            deg[a] += 1
            deg[b] += 1
            wsum[a] += c
            wsum[b] += c
        nodes = [{
            "id": d, "label": title_of.get(d, d), "df": len(doc_keys[d]),
            "degree": deg.get(d, 0), "weight": wsum.get(d, 0),
        } for d in sorted(keep, key=lambda d: (-deg.get(d, 0), d))]
        edges = [{"source": a, "target": b, "weight": c} for a, b, c in edges_k]

    edges.sort(key=lambda e: (-e["weight"], e["source"], e["target"]))

    # ── 孤立节点（度为 0）默认剔除 ──
    # 为什么：度为 0 的节点在本库内不与其他任何节点共现 —— 没有关系信息，画进网络
    # 只是噪音（与作者网络同一策略，用户亦明确要求"没有共现的就别画"）。**计数口径
    # 一律不动**（min_edge / min_df / 篇内去重都不变），这里只是把"已入选但没有任何
    # 边"的节点从**输出**里拿掉；剔除数写进 stats，不静默删除。保留时（--keep-isolated）
    # 它们各自成为单元素分量，报告端仍按群着色而非退回单色。
    deg_final = Counter()
    for a, b, _c in edges_k:
        deg_final[a] += 1
        deg_final[b] += 1
    nodes_before = len(nodes)
    isolated_ids = {n["id"] for n in nodes if deg_final.get(n["id"], 0) == 0}
    if not keep_isolated:
        nodes = [n for n in nodes if n["id"] not in isolated_ids]

    # ── 连通分量（并查集）+ 稳定编号 ──
    # 编号规则：分量**规模降序**；规模相同按**最小成员名升序** → 同输入必然同输出。
    # id=0 即最大群，报告端据此让大群优先拿到区分度最高的颜色（直接对调色板取模）。
    out_ids = [n["id"] for n in nodes]
    parent = {i: i for i in out_ids}

    def _find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b, _c in edges_k:
        if a in parent and b in parent:
            ra, rb = _find(a), _find(b)
            if ra != rb:
                parent[ra] = rb
    _by_root: dict = defaultdict(list)
    for i in out_ids:
        _by_root[_find(i)].append(i)
    ordered_groups = sorted((sorted(v) for v in _by_root.values()),
                            key=lambda g: (-len(g), g[0]))
    comp_id: dict[str, int] = {}
    comp_size: dict[str, int] = {}
    for _i, _g in enumerate(ordered_groups):
        for _a in _g:
            comp_id[_a] = _i
            comp_size[_a] = len(_g)
    for n in nodes:
        n["component"] = comp_id[n["id"]]
        n["component_size"] = comp_size[n["id"]]

    # ── 社群发现（加权标签传播）+ 稳定编号 ──
    # 与 component 并存、不替代：component 回答"能否连通"，community 回答"关系紧不紧"。
    # 渲染端**优先**用 community 上色（近乎全连通的引文网络按 component 上色必然单色）；
    # component 字段保留，供作者网络语义与旧产物/下游依赖使用。
    # 编号规则与 component **完全一致**（规模降序、同规模按最小成员名升序），
    # 保证"同输入同编号"、并与报告端 JS 兜底自算的规则对齐。
    _lab, _mod = _communities(out_ids, edges_k)
    _cgrp: dict = defaultdict(list)
    for _i in out_ids:
        _cgrp[_lab[_i]].append(_i)
    _cordered = sorted((sorted(v) for v in _cgrp.values()),
                       key=lambda g: (-len(g), g[0]))
    comm_id: dict[str, int] = {}
    comm_size: dict[str, int] = {}
    for _ci, _g in enumerate(_cordered):
        for _a in _g:
            comm_id[_a] = _ci
            comm_size[_a] = len(_g)
    for n in nodes:
        n["community"] = comm_id[n["id"]]
        n["community_size"] = comm_size[n["id"]]

    n_out = len(nodes)
    largest = max((len(g) for g in ordered_groups), default=0)
    isolated_out = sum(1 for n in nodes if n["degree"] == 0)
    density = (2.0 * len(edges) / (n_out * (n_out - 1))) if n_out > 1 else 0.0

    stats = {
        "nodes": n_out, "edges": len(edges),
        "nodes_before_isolated_drop": nodes_before,   # 剔除孤立前的节点数（对账用）
        "components": len(ordered_groups),
        "largest_component": largest,
        "largest_component_pct": round(100.0 * largest / n_out, 1) if n_out else 0.0,
        "isolated": isolated_out,                     # 输出图里的孤立节点数（默认 0）
        "isolated_found": len(isolated_ids),           # 阈值筛选后发现的孤立数
        "isolated_dropped": (0 if keep_isolated else len(isolated_ids)),
        "keep_isolated": keep_isolated,
        "max_degree": max((n["degree"] for n in nodes), default=0),
        "max_weight": max((e["weight"] for e in edges), default=0),
        "density": round(density, 6),
        # 社群发现（着色维度）：社群数 / 最大社群规模与占比 / 模块度（越低越碎，
        # 越高越说明划分贴合真实群落；单社群恒为 0）。占比是关键 —— 若 >80% 说明
        # 图本身社群结构单一，颜色仍会偏单色（如实报告，不粉饰）。
        "communities": len(_cordered),
        "largest_community": max((len(g) for g in _cordered), default=0),
        "largest_community_pct": (round(100.0 * max((len(g) for g in _cordered), default=0) / n_out, 1)
                                  if n_out else 0.0),
        "modularity": _mod,
        "community_algorithm": "label_propagation(weighted, deterministic-order)",
        "params": {
            "mode": mode, "min_edge_count": min_edge, "node_df": min_df,
            "dedupe": "per-doc", "ref_identity": "doi > author+year > string",
            "keep_isolated": keep_isolated,
        },
        "coverage": {
            "docs_total": docs_total,
            "docs_with_references": docs_with_refs,
            "references_pct": round(docs_with_refs / docs_total * 100, 1) if docs_total else 0.0,
            "raw_reference_entries": sum(len(r.get("references") or []) for r in refs),
        },
        "elapsed": round(time.time() - t0, 3),
    }
    return nodes, edges, stats


def build_empty_notice(total: int) -> str:
    return ("本数据源不含 references 字段：%d 篇文献中 0 篇含被引/参考文献，引文网络无法构建。"
            "请确认导入源是否提供被引字段（WoS 的 CR / Cited References、"
            "RIS 的 CR）；CNKI 与 Zotero 导出通常不含被引（CiteSpace 官方 FAQ 亦确认 CNKI 无 cited references）。"
            % total)


def main() -> int:
    ap = argparse.ArgumentParser(description="引文网络（共被引 / 文献耦合）")
    ap.add_argument("target", help="import_sources.py 产出的 refs.json")
    ap.add_argument("--mode", choices=["cocitation", "coupling"], default="cocitation",
                    help="cocitation=共被引（节点=参考文献，默认）；coupling=文献耦合（节点=文献）")
    ap.add_argument("--min-edge", type=int, default=2,
                    help="边的最小权重（共被引默认 2：至少被 2 篇同时引用才有意义）")
    ap.add_argument("--min-df", type=int, default=1, help="节点最小文献频次（默认 1）")
    ap.add_argument("--top", type=int, default=None, help="最多保留多少节点（默认不限）")
    ap.add_argument("--keep-isolated", action="store_true",
                    help="保留度为 0 的孤立节点（默认剔除；孤立节点在本库内不与其他"
                         "任何节点共现，画进网络只是噪音）")
    ap.add_argument("--seed", type=int, default=42, help="布局随机种子（可复现）")
    ap.add_argument("--layout-max-nodes", type=int, default=1500,
                    help="参与力导向布局（FR）的核心节点上限（默认 1500，0=不限）。"
                         "超限时按度/文献频次确定性取前 N 个进 FR，其余与度=0 的孤立点"
                         "一起按确定性同心环排到网络外围；避免 O(n²) 在数千节点上退化到"
                         "分钟级（实测 3338 节点纯布局 ≈525s）")
    ap.add_argument("--no-layout", action="store_true",
                    help="跳过布局（只出 nodes/edges，报告端自行现场布局）")
    ap.add_argument("--out", default="./out")
    args = ap.parse_args()

    try:
        src = Path(args.target).expanduser()
        if not src.exists():
            print(f"[error] 输入不存在：{src}", file=sys.stderr)
            print(f"[hint] {EXIT[1]}", file=sys.stderr)
            return 1
        payload = load_payload(src)
        refs = payload.get("refs", [])
        nodes, edges, stats = build(
            refs, mode=args.mode, min_edge=args.min_edge,
            min_df=args.min_df, top=args.top, keep_isolated=args.keep_isolated)

        # ── 布局：与作者网络同一套确定性 FR（固定种子 → 同输入同输出）──
        # 坐标同时写入明文 x/y（pos_encoded 缺失时的兜底）与 pos_encoded/edges_encoded
        # （报告端首屏直接用，省一次现场布局）。注意必须在 nodes 排序**之后**布局，
        # 否则 pos_encoded[i] 会与 nodes[i] 错位（见 run_checks.c_sort_before_layout）。
        if nodes and not args.no_layout:
            pos = _layout(nodes, edges, seed=args.seed, max_nodes=args.layout_max_nodes)
            for i, nd in enumerate(nodes):
                nd["x"] = round(pos[i][0], 2)
                nd["y"] = round(pos[i][1], 2)
            # 如实记账：多少节点走了力导向、多少排在外环（规模与降级幅度可被外部核验）
            _iso = sum(1 for d in nodes if not (d.get("degree") or 0))
            _conn = len(nodes) - _iso
            _cap = args.layout_max_nodes
            _fr_n = _conn if (_cap <= 0 or _conn <= _cap) else _cap
            stats["layout_nodes"] = len(nodes)
            stats["layout_fr_nodes"] = _fr_n
            stats["layout_ring_nodes"] = len(nodes) - _fr_n
            stats["layout_max_nodes"] = _cap

        empty = stats["coverage"]["docs_with_references"] == 0
        if empty:
            notice = build_empty_notice(stats["coverage"]["docs_total"])
            print(f"[warn] {notice}", file=sys.stderr)
        else:
            notice = ("引文网络（%s）：%s" % (
                "共被引 co-citation，节点=参考文献，边=被同一篇文献同时引用"
                if args.mode == "cocitation" else
                "文献耦合 bibliographic coupling，节点=文献，边=共同被引数",
                "共被引看被引端相似，耦合看施引端相似，二者方向相反。"))
            # 如实交代孤立节点剔除（不静默删）：本库共被引常含大量孤立参考文献
            # （只被 1 篇引用、与任何其他被引都不共现），默认不画入图中。
            _drop = stats.get("isolated_dropped", 0)
            if _drop:
                notice += (" 已剔除 %d 个孤立节点（度=0，本库内不与其他任何节点共现，"
                           "未画入图中）；如需保留请加 --keep-isolated。"
                           % _drop)
            # 反过来说清"保留/超限"时布局怎么处理：外环节点没有被丢，只是不进 FR。
            _ring = stats.get("layout_ring_nodes", 0)
            if _ring:
                notice += (" 其中 %d 个节点未参与力导向布局（度=0 的孤立点，或超过 "
                           "--layout-max-nodes=%d 上限的核心尾部），已按确定性同心环排在"
                           "网络外围——节点未丢弃，仅不享受力导向位置。"
                           % (_ring, stats.get("layout_max_nodes", 0)))
            # 说清着色维度：按社群（而非连通分量）着色 —— 近乎全连通的引文网络只有
            # 按社群上色才分得开颜色，这里如实报出社群数与最大占比（便于判断是否仍偏单色）。
            _nc = stats.get("communities", 0)
            if _nc:
                notice += (" 节点颜色按社群（加权标签传播）划分，共 %d 个社群，最大社群占 "
                           "%.1f%%（同色 = 同一共现社群）。" % (_nc, stats.get("largest_community_pct", 0.0)))

        payload_out = {
            "ok": True, "exit_code": 0,
            "library": {"name": src.name, "display_path": src.name,
                        "source": payload.get("source_label") or payload.get("source")},
            "type": ("citation-cocitation" if args.mode == "cocitation"
                     else "bibliographic-coupling"),
            "empty_state": empty,
            "notice": notice,
            "stats": stats,
            "coverage": stats["coverage"],
            "nodes": nodes,
            "edges": edges,
        }
        if nodes and not args.no_layout:
            payload_out["pos_encoded"] = encode_pos(
                [[nd["x"], nd["y"]] for nd in nodes])
            payload_out["edges_encoded"] = encode_edges(
                [(e["source"], e["target"], e["weight"]) for e in edges], nodes)

        outdir = Path(args.out).expanduser()
        outdir.mkdir(parents=True, exist_ok=True)
        (outdir / "citation_network.json").write_text(
            json.dumps(payload_out, ensure_ascii=False, indent=1), encoding="utf-8")
        with open(outdir / "citation_network_nodes.csv", "w", newline="",
                  encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["id", "label", "df_doc", "degree", "weight",
                        "component", "component_size", "community", "community_size", "x", "y"])
            for nd in nodes:
                w.writerow([esc_csv_cell(nd["id"]), esc_csv_cell(nd["label"]),
                            nd["df"], nd["degree"], nd["weight"],
                            nd.get("component", ""), nd.get("component_size", ""),
                            nd.get("community", ""), nd.get("community_size", ""),
                            nd.get("x", ""), nd.get("y", "")])

        emit({"ok": True, "out": str(outdir), "mode": args.mode,
              "empty_state": empty, "stats": stats, "notice": notice})
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
