#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_author_network.py —— 作者共现网络（co-authorship network）

用法:
    python3 build_author_network.py <refs.json 或 .enl> \
            [--min-docs 2] [--min-edge 1] [--max-nodes 300] \
            [--keep-isolated] [--out DIR] [--no-layout] [--seed 42]

产出:
    author_network.json        节点 / 边 / 统计（schema 对齐 network.json）
    author_network_nodes.csv   节点明细
    author_network_edges.csv   边明细

## 默认剔除孤立作者 / 每个节点带"合作群"

度为 0 的作者在本库内没有任何共现 —— 没有关系信息，画进网络只是噪音，故
**默认不输出**（stats 里记录剔除了多少个，不静默删除）。显式加 `--keep-isolated`
可保留它们。阈值口径（min_docs / min_edge / 篇内去重）**不受此开关影响**。

每个节点额外带 `component` / `component_size`：该作者所属连通分量（合作群）
的整数 id 与规模。id 按「分量规模降序、规模相同按最小成员名升序」编号 →
同输入必然同输出，且 id=0 恒为最大合作群，便于报告端让大群优先拿到最区分度
最高的颜色。

## 与关键词共现网络的区别（务必分清，报告里也据此分章）

    关键词网络：节点 = 概念，回答「概念之间有什么关联」；
    作者网络  ：节点 = 作者，回答「谁和谁合作、核心作者群是谁」。

两者数据源不同（keywords vs authors），**不可互相替代**，故独立成章独立画布。

## 为什么口径是「同一篇文献内两两共现一次」

作者共现的定义就是「同处一篇文章」这一事实。同一篇里 A、B 无论出现几次，
合作关系只算一次，故**篇内先去重**（用 set）再两两配对 —— 否则一篇作者列表
被重复解析时会人为放大权重。

## 本库实测（500 篇，CNKI 中文题录）

    docs = 500，其中单作者 216 篇（43%）—— 作者共现本就稀疏，这是数据事实。
    归一后作者 1029 个，但 df≥2 的只有 94 个、df≥3 仅 22 个（最高 df=5）。
    全量共现对 1313 条，但权重≥2 的仅 48 条（多数合作只发生一次）。

    [!] 因此**不能**照搬关键词网络的默认阈值（node_df=5 / min_edge=2）：
       · min_docs=5 → 一个作者都不剩（最高 df 只有 5，取 ≥5 恰好为 0）；
       · min_edge=2 → 砍掉 96% 的边，图退化成几十个孤点。
       本脚本默认 min_docs=2 / min_edge=1：实测 94 节点 / 62 边，可读且信息量足。
       （min_docs=1 会带进 835 个「只合作过一次」的节点 → 一根毛线球，
        min_docs=3 只剩 9 个节点 → 看不出结构。故 2 是本库的正确档位。）

## 零第三方依赖

本环境没有 numpy（关键词网络脚本的布局依赖 numpy）。作者网络节点数不大
（默认上限 300），故布局用**纯标准库**的 Fruchterman–Reingold 实现，
O(n²) 迭代在 100–300 节点下耗时可接受；固定随机种子 → 同输入必得同输出。
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import re
import sys
import time
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# 布局 / 编码：共享实现（见 _netutil.py —— 收敛此前三处逐字节复制）
from _netutil import fr_layout as _fr, encode_pos, encode_edges  # noqa: E402
from lit_core import (  # noqa: E402
    EnlError, EXIT, coverage_report, emit, esc_csv_cell, find_enl,
    load_refs, lock_status,
)

# 分隔符：空白（含全角空格）+ 换行 + 中西文常见作者分隔符。
# [!]  这里**故意不拆 ASCII 逗号**：英文题录用「Last, F. M.」形式，
#   一拆就把一个作者劈成「姓」和「名」两个假作者。本库是 CNKI 中文题录
#   （作者字段以空格分隔），逗号罕见，故牺牲「逗号分隔中文作者」这种边缘情况，
#   换取英文姓名不被劈开。若将来出现逗号分隔的中文库，需另加判据。
_SPLIT = re.compile(r"[\s\u3000\r\n;；、，]+")

# 需要从姓名两端剥掉的「多余分隔符 / 编号装饰」。
_TRIM = " \t\r\n,;；、，.。·・'\"“”‘’()（）[]【】<>《》—-_/\\|"

# 机构后缀：author_list 形如 '余疆|' / 'Zhang|Peking Univ'，竖线后是本该放机构的位置。
# 只保留竖线前半，故按 '|' 截断即可（本库 1148/1148 机构段全空）。
_INST_SEP = "|"

# ── v1.0.0 修复「作者网络中英文截取词错误」 ─────────────────────
# 根因：_SPLIT 含 \s（会劈 \r），英文题录 'Smith, J.\rZhang, L.' 被按空白劈成
# 'Smith,' / 'J.' / 'Zhang,' / 'L.' —— 每个作者的「名首字母」都成了独立假作者，
# 作者贡献统计被同名首字母污染。修复 = 先按记录分隔，再处理段内逗号。
_RECORD_SPLIT = re.compile(r"[\r\n;；、，]+")   # ASCII 逗号不在此列（属于单个作者内部）
_INITIAL_ONLY = re.compile(r"^[A-Za-z]\.?$")   # 残片：单个字母（可带点）


def _split_author_field(raw: str) -> list[str]:
    """把 author 字符串切成「作者记录」列表（不劈开单个作者内部）。

    三种实测格式：
      · .enl      ：'Last, F. M.' 以 \r 分隔 → 按记录分隔符切，逗号保留在记录内；
      · CNKI      ：'张三 李四 王五'（空格分隔、无逗号）→ 按空白切；
      · 逗号多作者：'Smith J, Zhang L'（每个非空段都含空白）→ 按逗号切段。
    判定歧义的安全侧：'Smith, J.' 只有一个非空段含空白 → 整段视为一个作者。
    """
    out: list[str] = []
    for rec in _RECORD_SPLIT.split(raw):
        rec = rec.strip()
        if not rec:
            continue
        if "," in rec:
            nonempty = [p.strip() for p in rec.split(",") if p.strip()]
            if len(nonempty) >= 2 and all(" " in p for p in nonempty):
                out.extend(nonempty)          # 'Smith J, Zhang L' 式多作者
            else:
                out.append(rec)               # 'Last, F. M.' 整段是一个作者
        else:
            out.extend(t for t in _SPLIT.split(rec) if t)
    return out


def normalize_author(raw: str) -> str:
    """作者名归一。

    步骤（顺序有讲究）：
      1) NFKC 统一全角/半角 —— 全角字母数字（ＡＢＣ）与半角（ABC）视为同一人；
      2) 按竖线截断，丢弃机构段（'名|机构' → '名'）；
      3) 内部空白压成单空格（'张 三' 与 '张三' 是否合并在第 4 步之后由
         等价规则决定 —— 本函数只做「同一 token 内」的清洗，不跨 token 合并）；
      4) 剥掉两端多余分隔符；
      5) 返回空串表示该 token 不是有效作者名（调用方应丢弃）。
    """
    if not raw:
        return ""
    s = unicodedata.normalize("NFKC", str(raw))
    if _INST_SEP in s:
        s = s.split(_INST_SEP, 1)[0]
    # 内部连续空白（含全角）压成单空格，再去两端冗余符号
    s = re.sub(r"[\s\u3000]+", " ", s).strip()
    s = s.strip(_TRIM).strip()
    return s


def parse_record_authors(ref) -> list[str]:
    """从一条题录里取出归一后的作者列表（**保留原始顺序，篇内去重**）。

    数据源优先用 `authors` 字符串（本库 500/500 填充，空格分隔）；
    为空时回退 `author_list`（形如 ['余疆|', ...]）。
    两者都描述同一批作者，任取其一即可 —— 不走「并集」，避免英文题录里
    出现 'Burke, F.' 与 'burke|f' 两份表示而被重复计数。
    """
    raw = (getattr(ref, "authors", "") or "").strip()
    if raw:
        toks = _split_author_field(raw)
    else:
        al = getattr(ref, "author_list", None) or []
        toks = [str(x) for x in al]
    out: list[str] = []
    seen = set()
    for t in toks:
        nm = normalize_author(t)
        if not nm or nm in seen:
            continue
        if _INITIAL_ONLY.match(nm):
            continue          # 名首字母残片（假作者），丢弃——修复截词错误
        seen.add(nm)
        out.append(nm)
    return out


def build(refs, min_docs: int = 2, min_edge: int = 1,
          max_nodes: int | None = 300,
          keep_isolated: bool = False,
          min_component: int = 3) -> tuple[list, list, dict]:
    """构建作者共现网络。返回 (nodes, edges, stats)。

    共现口径：同一篇文献内作者两两共现一次，**篇内去重**。

    默认剔除度为 0 的孤立作者（无共现 = 无关系信息，画上去只是噪音）；
    `keep_isolated=True` 可保留。每个节点带 `component` / `component_size`
    （连通分量 id 与规模，按规模降序稳定编号，最大合作群 id=0）。

    `min_component`：只保留 ≥N 人的连通分量（默认 3；实测需求 2 人
    合作对只是偶然合写，不构成可深挖的合作群体）。0/1/2 退化为不过滤。
    """
    t0 = time.time()

    # 原始名 → 归一名的映射（只用于统计归一前后合并了多少，见下）
    df: Counter = Counter()                    # 作者 → 出现文献数（文档频次）
    docs_with_authors = 0
    n_author_slots = 0                         # 所有文献的作者「人次」（去重后）

    # 篇内作者集合（供建边）+ 逐篇累计 df
    per_doc_authors: list[list[str]] = []
    for r in refs:
        names = parse_record_authors(r)
        if names:
            docs_with_authors += 1
        n_author_slots += len(names)
        for nm in names:
            df[nm] += 1
        per_doc_authors.append(sorted(set(names)))

    # ── 归一合并统计 ──
    # 归一后同名合并：把「原始 token → 归一结果」记下来，统计有多少规范名
    # 由多个原始写法坍缩而来（如全角/半角差异、尾随标点差异）。
    raw_variants: dict[str, set] = defaultdict(set)
    for r in refs:
        raw = (getattr(r, "authors", "") or "").strip()
        if not raw:
            for x in (getattr(r, "author_list", None) or []):
                nm = normalize_author(str(x))
                if nm:
                    raw_variants[nm].add(str(x).strip())
            continue
        for t in _split_author_field(raw):
            t = t.strip()
            if not t:
                continue
            nm = normalize_author(t)
            if nm:
                raw_variants[nm].add(t)
    merged_groups = {k: v for k, v in raw_variants.items() if len(v) > 1}
    raw_distinct = sum(len(v) for v in raw_variants.values())

    # ── 节点筛选：df >= min_docs ──
    keep = {a for a, c in df.items() if c >= min_docs}
    # max_nodes 兜底：并列 df 时用 id 兜底排序，保证跨进程可复现
    # （照搬 build_network.py 教训：set 遍历顺序依赖 PYTHONHASHSEED）
    if max_nodes and len(keep) > max_nodes:
        keep = set(sorted(keep, key=lambda w: (-df[w], w))[:max_nodes])

    # ── 边：篇内两两共现，篇内已去重 ──
    edge_count: Counter = Counter()
    for names in per_doc_authors:
        sel = sorted({w for w in names if w in keep})
        for a, b in itertools.combinations(sel, 2):
            if a == b:                         # 防御性：正常已去重
                continue
            edge_count[(a, b)] += 1
    edges = [(a, b, c) for (a, b), c in edge_count.items() if c >= min_edge]

    # ── 节点度数 / 权重（weight = 邻边权重之和）──
    deg: Counter = Counter()
    wsum: Counter = Counter()
    for a, b, c in edges:
        deg[a] += 1
        deg[b] += 1
        wsum[a] += c
        wsum[b] += c

    # ── 孤立节点（度为 0）默认剔除 ──
    # 为什么：度为 0 的作者在本库内没有任何共现 —— 没有关系信息，画进网络只是
    # 噪音。**阈值口径一律不动**（min_docs /
    # min_edge 语义、共现计数、篇内去重都不变），这里只是把"已入选但没有任何边"
    # 的节点从**输出**里拿掉；剔除数写进 stats，不用静默删除糊弄读者。
    isolated_ids = {a for a in keep if deg.get(a, 0) == 0}
    out_set = set(keep) if keep_isolated else (keep - isolated_ids)

    # ── 连通分量（并查集）+ 稳定编号 ──
    # 编号规则：分量**规模降序**；规模相同按**最小成员名升序** → 同输入必然同输出。
    # id=0 即最大合作群，报告端据此让大群优先拿到最区分度高的颜色（直接对调色板取模）。
    parent = {a: a for a in out_set}

    def _find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b, _c in edges:
        if a in parent and b in parent:
            ra, rb = _find(a), _find(b)
            if ra != rb:
                parent[ra] = rb
    _by_root: dict = defaultdict(list)
    for a in out_set:
        _by_root[_find(a)].append(a)
    ordered_groups = sorted((sorted(v) for v in _by_root.values()),
                            key=lambda g: (-len(g), g[0]))
    comp_id: dict[str, int] = {}
    comp_size: dict[str, int] = {}
    for _i, _g in enumerate(ordered_groups):
        for _a in _g:
            comp_id[_a] = _i
            comp_size[_a] = len(_g)

    # ── 小分量过滤──
    # 2 人合作对（component_size=2）只是「合写过一篇」的偶然配对，不构成
    # 可持续深挖的「合作群体」（低于 3 人不构成可深挖的合作网络）。
    # 默认只保留 ≥3 人的分量；--min-component 可调（0/1/2 退化为不过滤）。
    min_comp = max(0, int(min_component))
    dropped_small = 0
    if min_comp >= 2:
        before = len(out_set)
        out_set = {a for a in out_set if comp_size.get(a, 0) >= min_comp}
        dropped_small = before - len(out_set)
        # 同步过滤 edges（两端都在保留集内）
        edges = [(a, b, c) for a, b, c in edges
                 if a in out_set and b in out_set]
        # 重算度数（剔除小分量后部分节点度会变化；孤立节点再次剔除）
        deg = Counter()
        wsum = Counter()
        for a, b, c in edges:
            deg[a] += 1
            deg[b] += 1
            wsum[a] += c
            wsum[b] += c
        out_set = {a for a in out_set if deg.get(a, 0) > 0}
        # 分量 id 重排（过滤后原 id 有空洞）
        _re_groups: dict[int, list] = defaultdict(list)
        for a in out_set:
            _re_groups[comp_id[a]].append(a)
        ordered_groups = sorted((sorted(v) for v in _re_groups.values()),
                                key=lambda g: (-len(g), g[0]))
        comp_id, comp_size = {}, {}
        for _i, _g in enumerate(ordered_groups):
            for _a in _g:
                comp_id[_a] = _i
                comp_size[_a] = len(_g)

    # 排序构成**全序**：(-degree, -df, id) —— 保证 nodes[] 顺序可复现
    nodes = []
    for a in sorted(out_set):
        nodes.append({
            "id": a,
            "df": df[a],
            "degree": deg.get(a, 0),
            "weight": wsum.get(a, 0),
            "isolated": deg.get(a, 0) == 0,
            "component": comp_id[a],
            "component_size": comp_size[a],
        })
    nodes.sort(key=lambda x: (-x["degree"], -x["df"], x["id"]))

    n_out = len(out_set)
    largest = max((len(g) for g in ordered_groups), default=0)
    isolated_out = sum(1 for a in out_set if deg.get(a, 0) == 0)
    density = (2.0 * len(edges) / (n_out * (n_out - 1))) if n_out > 1 else 0.0

    stats = {
        "nodes": n_out,
        "nodes_before_isolated_drop": len(keep),      # 剔除孤立前的节点数（对账用）
        "edges": len(edges),
        "authors_total": len(df),                    # 归一后全部作者
        "authors_kept": len(keep),                   # 仅按 min_docs 阈值筛选者
        "author_slots": n_author_slots,              # 作者人次（去重后）
        "max_df": max(df.values()) if df else 0,
        "max_degree": max((n["degree"] for n in nodes), default=0),
        "max_weight": max((e[2] for e in edges), default=0),
        "components": len(ordered_groups),
        "largest_component": largest,
        "largest_component_pct": round(100.0 * largest / n_out, 1) if n_out else 0.0,
        "isolated": isolated_out,                     # 输出图里的孤立节点数（默认 0）
        "isolated_found": len(isolated_ids),          # 阈值筛选后发现的孤立数
        "isolated_dropped": (0 if keep_isolated else len(isolated_ids)),
        "keep_isolated": keep_isolated,
        "density": round(density, 6),
        "params": {
            "min_docs": min_docs,
            "min_edge": min_edge,
            "max_nodes": max_nodes,
            "keep_isolated": keep_isolated,
            "dedupe": "per-doc",
            "normalize": "NFKC+trim+drop_institution",
            "cooccurrence": "same-doc pairwise (weight = #shared docs)",
        },
        "merge": {
            "raw_distinct": raw_distinct,
            "normalized_distinct": len(df),
            "merged_groups": len(merged_groups),
            "merged_examples": [
                {"normalized": k, "variants": sorted(v)[:4]}
                for k, v in sorted(merged_groups.items())[:5]
            ],
        },
        "coverage": {
            "docs_total": len(refs),
            "docs_with_authors": docs_with_authors,
            "authors_coverage_pct": round(
                100.0 * docs_with_authors / len(refs), 1) if refs else 0.0,
        },
        "elapsed": round(time.time() - t0, 3),
    }
    return nodes, edges, stats


def _fr_by_component(nodes, edges, seed: int = 42) -> list[list[float]]:
    """按连通分量分别布局、再网格平铺 —— 修复「网络聚集成一团」（v1.0.0）。

    作者共现网络是 21 个彼此无边的分离社群。单图 Fruchterman–Reingold
    用统一理想边长 k=2/√n，会把每个社群压成紧球、且所有球共享一个
    中心（向心力把整团往中间挤）—— 视觉上就是「一坨」。

    正确做法（VOSviewer / Gephi 处理多分量图的标准方式）：
      1) 每个连通分量独立做 FR 布局（小图在自己空间里充分展开）；
      2) 把各分量的「包围盒」按大小降序，用简单货架式网格排开，
         分量之间留出明显空隙 —— 社群边界一目了然。
    返回 n×2 坐标，已归一化到 max|·| = 1（与 encode_pos 契约一致）。
    """
    idx = {nd["id"]: i for i, nd in enumerate(nodes)}
    # 按 component 分组（无 component 字段时退化为整图单分量）
    comps = {}
    for nd in nodes:
        comps.setdefault(nd.get("component", 0), []).append(nd["id"])
    # 每个分量的边
    comp_edges = {c: [] for c in comps}
    for a, b, w in edges:
        if a in idx and b in idx:
            c = nodes[idx[a]].get("component", 0)
            if nodes[idx[b]].get("component", 0) == c:
                comp_edges.setdefault(c, []).append((a, b, w))
    # 按分量大小降序布局
    order = sorted(comps, key=lambda c: -len(comps[c]))
    laid = {}   # node_id -> (x, y) 局部分量坐标
    boxes = []  # (w, h, [(node,x,y),...]) 每分量的包围盒与成员
    for c in order:
        ids = comps[c]
        sub_nodes = [nodes[idx[i]] for i in ids]
        sub_edges = comp_edges.get(c, [])
        pos = _fr(sub_nodes, sub_edges, seed=seed)
        xs = [p[0] for p in pos] or [0.0]
        ys = [p[1] for p in pos] or [0.0]
        w = max(xs) - min(xs) or 1.0
        h = max(ys) - min(ys) or 1.0
        # 记录「相对最小点」的局部坐标，便于平铺时整体平移
        members = [(nid, (pos[k][0] - min(xs)) / w if w else 0.0,
                    (pos[k][1] - min(ys)) / h if h else 0.0)
                   for k, nid in enumerate(ids)]
        boxes.append([w, h, members, len(ids)])
    # 货架式平铺：按宽度降序放入网格，单元格随最大分量缩放 + 留缝
    # v1.0.0 修：小分量（2~3 人的孤立合作对）数量多但内容少，
    # 若与 193 人大社群用同一 cell 边距会把画面撑成松散网格。
    # 改为「大小分组」：大分量（>=6 人）占主区网格、小分量沿底部密排，
    # 大社群有足够空间展开，小对紧凑收边不抢镜。
    big = [b for b in boxes if b[3] >= 6]
    small = [b for b in boxes if b[3] < 6]
    final = [[0.0, 0.0] for _ in nodes]

    def _tile(group, ox0, oy0, ncol, cell, gap):
        for bi, (w, h, members, _sz) in enumerate(group):
            r, c = divmod(bi, ncol)
            ox = ox0 + c * (cell + gap)
            oy = oy0 + r * (cell + gap)
            for nid, fx, fy in members:
                final[idx[nid]] = [ox + fx * w, oy + fy * h]
        rows = (len(group) + ncol - 1) // ncol if group else 0
        return oy0 + rows * (cell + gap)   # 返回该组占用的底部 y

    gap = 0.30
    big_cell = max((b[0] for b in big), default=1.0)
    big_ncol = max(1, math.ceil(math.sqrt(len(big)))) if big else 1
    y_end = _tile(big, 0.0, 0.0, big_ncol, big_cell, gap)
    # 小分量：cell 取大分量的 0.45（紧凑），列数按大区分栏宽度对齐，
    # 紧贴大分量下方密排，不再用自身宽度把一行拉得过长。
    sm_cell = big_cell * 0.45
    sm_ncol = max(big_ncol * 2, math.ceil((big_ncol * (big_cell + gap)) / (sm_cell + gap))) if small else 1
    _tile(small, 0.0, y_end + gap, sm_ncol, sm_cell, gap)
    # 居中：用**包围盒中心**（不是质心）—— 大分量节点多会让质心偏移，
    # 导致整团挤到角落。包围盒中心让画面在视口正中。
    n = len(final)
    if n:
        xs = [p[0] for p in final]
        ys = [p[1] for p in final]
        ccx = (max(xs) + min(xs)) / 2
        ccy = (max(ys) + min(ys)) / 2
        for p in final:
            p[0] -= ccx
            p[1] -= ccy
        span = max((max(abs(p[0]), abs(p[1])) for p in final), default=1.0) or 1.0
        final = [[p[0] / span, p[1] / span] for p in final]
    return final


def main() -> int:
    ap = argparse.ArgumentParser(description="构建作者共现网络（co-authorship）")
    ap.add_argument("target", help="题录库目录 / .enl 文件 / refs.json")
    ap.add_argument("--min-docs", type=int, default=2,
                    help="作者最少出现文献数（默认 2；本库 500 篇下的正确档位，"
                         "详见文件头实测说明）")
    ap.add_argument("--min-edge", type=int, default=1,
                    help="边的最小共现次数（默认 1；作者合作多为一次性，"
                         "取 2 会砍掉 96%% 的边）")
    ap.add_argument("--max-nodes", type=int, default=300,
                    help="节点数上限（按 df 降序，0=不限；防大库布局退化）")
    ap.add_argument("--out", default="./out")
    ap.add_argument("--workspace", default="./.lit_work")
    ap.add_argument("--seed", type=int, default=42, help="布局随机种子（可复现）")
    ap.add_argument("--no-layout", action="store_true",
                    help="跳过布局（只出 nodes/edges，报告端自行现场布局）")
    ap.add_argument("--keep-isolated", action="store_true",
                    help="保留度为 0 的孤立作者（默认剔除；孤立节点在本库内无任何"
                         "共现，画进网络只是噪音）")
    ap.add_argument("--min-component", type=int, default=3,
                    help="只保留 ≥N 人的连通分量（默认 3；2 人合作对只是偶然合写，"
                         "不构成可深挖的合作群体。0/1/2 退化为不过滤）")
    args = ap.parse_args()

    try:
        target = Path(args.target).expanduser()
        is_norm = target.is_file() and target.suffix.lower() == ".json"
        enl = None if is_norm else find_enl(target)
        busy, _ok, _notice = (False, True, None) if is_norm else lock_status(enl)
        refs, src_meta = load_refs(target, args.workspace)

        if not refs:
            print("[error] 题录为空，无作者可分析", file=sys.stderr)
            print(f"[hint] {EXIT[4]}", file=sys.stderr)
            return 4

        nodes, edges, stats = build(
            refs, min_docs=args.min_docs, min_edge=args.min_edge,
            max_nodes=(args.max_nodes or None), keep_isolated=args.keep_isolated,
            min_component=args.min_component)

        if nodes and not args.no_layout:
            # v1.0.0：按连通分量分簇布局（修复整图聚集一团）。
            # 单图 FR 对 21 个分离社群会压成一坨；分簇布局让各社群散开。
            pos = _fr_by_component(nodes, edges, seed=args.seed)
            for i, nd in enumerate(nodes):
                nd["x"] = round(pos[i][0], 2)
                nd["y"] = round(pos[i][1], 2)

        cov = coverage_report(refs)
        payload = {
            "ok": True, "exit_code": 0,
            "type": "author-cooccurrence",
            "library": {
                "name": src_meta.get("display_path"),
                "display_path": src_meta.get("display_path"),
                "source": src_meta.get("source_label"),
            },
            "notice": ("这是作者共现网络（co-authorship）：同一篇文献内作者两两共现。"
                       "回答「谁和谁合作、核心作者群是谁」，与关键词共现网络是两种"
                       "不同的网络，不可互相替代。"),
            "stats": stats,
            "coverage": cov,
            "nodes": nodes,
            "edges": [{"source": a, "target": b, "weight": c} for a, b, c in edges],
        }
        if nodes and not args.no_layout:
            payload["pos_encoded"] = encode_pos(
                [[nd["x"], nd["y"]] for nd in nodes])
            payload["edges_encoded"] = encode_edges(edges, nodes)

        outdir = Path(args.out)
        outdir.mkdir(parents=True, exist_ok=True)
        (outdir / "author_network.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")

        import csv
        with open(outdir / "author_network_nodes.csv", "w", newline="",
                  encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["author", "df_docs", "degree", "weight", "isolated",
                        "component", "component_size", "x", "y"])
            for nd in nodes:
                # 作者名同样来自外部导入，属不可信输入 → CSV 注入加固
                w.writerow([esc_csv_cell(nd["id"]), nd["df"], nd["degree"],
                            nd["weight"], int(bool(nd.get("isolated"))),
                            nd.get("component", ""), nd.get("component_size", ""),
                            nd.get("x", ""), nd.get("y", "")])
        with open(outdir / "author_network_edges.csv", "w", newline="",
                  encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["source", "target", "weight"])
            for a, b, c in edges:
                w.writerow([esc_csv_cell(a), esc_csv_cell(b), c])

        emit({"ok": True, "out": str(outdir), "stats": stats,
              "library": payload["library"]})
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
