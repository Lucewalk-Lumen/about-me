#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_netutil.py —— 网络构建脚本共享的布局与编码工具（仅本目录内部使用）

为什么存在：`encode_pos` / `encode_edges` / `_fr` / `_layout` / `_communities`
此前在 build_author_network.py、build_institution_network.py、
build_citation_network.py 三处逐字节复制。复制虽满足"脚本自包含"，却带来
"改一处忘两处"的漂移风险 —— 事实上作者网络的 `_fr` 已悄悄多出一轮"重叠消除"
而另两处没有（同源不全一致）。故统一收敛到本模块，消除漂移。

不改变任何对外产物：报告端只依赖 `pos_encoded` 契约
（{pos_b64, scale, span, quantum}，scale = 30000/span，int16 小端），
抽取前后逐字节一致；三个脚本的布局/编码行为现已完全一致。

[!] 与 build_network.py 的关系：该脚本的 `_fr_local` / `encode_pos` / `encode_edges`
    是 numpy 实现（为更大的关键词图优化），与本文本模块（纯标准库）是两条独立
    实现线，产物契约相同但代码不共享。
"""
from __future__ import annotations

import base64
import math
import random
from collections import defaultdict


def fr_layout(nodes, edges, iters: int = 260, seed: int = 42,
              relax: bool = True) -> list[list[float]]:
    """Fruchterman–Reingold 力导向布局（纯标准库，确定性）。

    与 build_network.py 的 `_fr_local` 同思路（斥力 k²/d²、引力 d²/k、
    温度线性退火 + 轻微向心），但用 list 代替 numpy —— 本环境无 numpy。
    目标区域取 [-1,1]²（面积 4），故 k = 2/√n，节点自然铺满而不外溢。

    `relax=True` 时，在收敛后追加一轮"重叠消除"松弛（见下）；
    返回 n×2 坐标，已居中并归一化到 max|·| = 1（与 pos_encoded 的量化契约一致）。
    """
    n = len(nodes)
    if n == 0:
        return []
    if n == 1:
        return [[0.0, 0.0]]
    rnd = random.Random(seed)
    pos = [[rnd.uniform(-1.0, 1.0), rnd.uniform(-1.0, 1.0)] for _ in range(n)]
    idx = {nd["id"]: i for i, nd in enumerate(nodes)}
    # 内部 edges 是 (a, b, weight) 三元组（与 build_network.py 一致）
    pairs = [(idx[a], idx[b]) for a, b, _c in edges if a in idx and b in idx]

    k = 2.0 / math.sqrt(n)
    t = 0.16 * (n ** 0.1)          # 初始温度
    dt = t / (iters + 1)

    # 向心力系数：0.10 对大分量（百人级）过强——hub 节点被往中间拉、
    # 外围点堆不出去。降到 0.06 让大分量充分舒展；小分量 n 小、向心占比
    # 天然更低，不受影响。
    _centripetal = 0.06 if n >= 40 else 0.10

    for _ in range(iters):
        disp = [[0.0, 0.0] for _ in range(n)]
        # 斥力：所有节点对
        for i in range(n):
            xi, yi = pos[i]
            for j in range(i + 1, n):
                dx = xi - pos[j][0]
                dy = yi - pos[j][1]
                d2 = dx * dx + dy * dy + 0.01
                f = (k * k) / d2
                d = math.sqrt(d2)
                ux, uy = dx / d, dy / d
                fx, fy = ux * f, uy * f
                disp[i][0] += fx
                disp[i][1] += fy
                disp[j][0] -= fx
                disp[j][1] -= fy
        # 引力：仅边存在处
        for a, b in pairs:
            dx = pos[a][0] - pos[b][0]
            dy = pos[a][1] - pos[b][1]
            d = math.hypot(dx, dy) + 0.01
            f = (d * d) / k
            ux, uy = dx / d, dy / d
            fx, fy = ux * f, uy * f
            disp[a][0] -= fx
            disp[a][1] -= fy
            disp[b][0] += fx
            disp[b][1] += fy
        for i in range(n):
            dx, dy = disp[i]
            dx -= pos[i][0] * _centripetal
            dy -= pos[i][1] * _centripetal
            norm = math.hypot(dx, dy) + 1e-9
            step = min(norm, t)
            pos[i][0] += dx / norm * step
            pos[i][1] += dy / norm * step
        t -= dt

    cx = sum(p[0] for p in pos) / n
    cy = sum(p[1] for p in pos) / n
    for p in pos:
        p[0] -= cx
        p[1] -= cy
    span = max((max(abs(p[0]), abs(p[1])) for p in pos), default=1.0) or 1.0
    pos = [[p[0] / span, p[1] / span] for p in pos]

    if relax:
        # ── 重叠消除（v1.0.0，实测「节点聚在一起、圆圈重叠」）──
        # FR 收敛后大分量中心区节点间距 < 节点渲染半径（4~22px），视觉上糊成一片。
        # 松弛：距离 < min_dist 的点对沿连线各推开一半差量，迭代至无重叠。
        # min_dist = 1.5/√n：让每个节点平均占据约 (1.5/√n)² 的领域，
        # 与 FR 的理想边长同量级，不会把布局撑爆。确定性、无随机。
        min_dist = 1.5 / math.sqrt(n)
        for _ in range(80):
            moved = 0
            for i in range(n):
                for j in range(i + 1, n):
                    dx = pos[i][0] - pos[j][0]
                    dy = pos[i][1] - pos[j][1]
                    d = math.hypot(dx, dy) + 1e-9
                    if d < min_dist:
                        push = (min_dist - d) / 2.0
                        ux, uy = dx / d, dy / d
                        pos[i][0] += ux * push
                        pos[i][1] += uy * push
                        pos[j][0] -= ux * push
                        pos[j][1] -= uy * push
                        moved += 1
            if not moved:
                break
        # 松弛会轻微外扩，重新居中归一（与量化契约一致）
        cx = sum(p[0] for p in pos) / n
        cy = sum(p[1] for p in pos) / n
        for p in pos:
            p[0] -= cx
            p[1] -= cy
        span = max((max(abs(p[0]), abs(p[1])) for p in pos), default=1.0) or 1.0
        pos = [[p[0] / span, p[1] / span] for p in pos]
    return pos


def layout(nodes, edges, seed: int = 42, max_nodes: int = 1500) -> list[list[float]]:
    """确定性布局调度器 —— FR 的"大图安全阀"。

    为什么需要它：`fr_layout` 的斥力是逐对 O(n²)，260+ 轮下 3000+ 节点要跑
    ~500 秒（实测 WoS 共被引 3338 节点纯布局 ≈ 525s），远超可接受范围。故分两层降级：
      1) **度=0 的孤立节点不参与力导向**：它们没有任何边，力导向对它们只是纯斥力
         散开，既无结构意义又拖慢全局。改为按确定性同心环排在 FR 核心外围
         （只有 --keep-isolated 才会产生这类节点）。
      2) 参与力导向的核心节点仍可能上千（真实大库）。超过 `max_nodes` 时按
         "度 desc、文献频次 desc、名称 asc"确定性取前 N 个进 FR，其余同样排到外环。
         **绝不静默丢弃节点**，只是它们不再享受力导向位置。
    返回与 nodes 等长的坐标（全部有限、确定性可复现）。max_nodes<=0 表示不限核心规模。
    """
    n = len(nodes)
    if n == 0:
        return []
    def _deg(d):
        return d.get("degree") or 0
    core = [i for i, d in enumerate(nodes) if _deg(d) > 0]
    ring = [i for i, d in enumerate(nodes) if _deg(d) == 0]
    if not ring and (max_nodes <= 0 or len(core) <= max_nodes):
        # 默认路径（已剔除孤立点、且核心不超上限）：与旧行为逐字节一致
        return fr_layout(nodes, edges, seed=seed)
    if max_nodes > 0 and len(core) > max_nodes:
        core.sort(key=lambda i: (-_deg(nodes[i]), -(nodes[i].get("df") or 0),
                                 str(nodes[i].get("label") or nodes[i].get("id") or "")))
        ring = ring + core[max_nodes:]
        core = core[:max_nodes]
    out = [None] * n
    if core:
        pos = fr_layout([nodes[i] for i in core], edges, seed=seed)
        for k, i in enumerate(core):
            out[i] = pos[k]
    # 外环：起始半径 1.5（> FR 归一化方框对角 √2，保证与核心不重叠），
    # 节点弧距≈0.06，超出当前环容量则半径 +0.08 再起一环。纯确定性，无随机数。
    r, i = 1.5, 0
    while i < len(ring):
        cap = max(1, int(round(2.0 * math.pi * r / 0.06)))
        for k in range(min(cap, len(ring) - i)):
            ang = 2.0 * math.pi * k / cap
            out[ring[i + k]] = [r * math.cos(ang), r * math.sin(ang)]
        i += cap
        r += 0.08
    return out


def communities(node_keys, edges, max_iter: int = 100):
    """加权标签传播（Label Propagation）社群发现 —— 纯标准库、确定性。

    为什么需要它（着色维度修正）：引文网络常是"几乎全连通"的图 —— WoS 共被引
    最大**连通分量**占 92.1%，若按连通分量着色，一张图基本只剩一个颜色，"多色"名存实亡。
    社群发现把大分量拆成若干"内部联系更紧密"的群体（实测 WoS 引文：连通分量 6 个/
    最大 92.1% → 社群 18 个/最大 21.2%），颜色才真正分得开。
    为什么选标签传播：纯标准库（不引入 networkx/numpy）、O(轮数×边数) 很快、实现短。
    确定性：节点按键升序遍历；每轮每个节点取"邻居标签的**权重和**"最大者，并列取
    最小标签；全程无随机数 —— 遍历顺序固定即已确定，同输入必然同输出（无需随机种子）。
    权重：每票份量 = 边权（共现/共被引次数），比无权更贴合"关系更紧"的语义。
    孤立点（无邻居）标签保持不变 → 各自成一个单元素社群，与分量语义一致。
    返回 (label_of, modularity)：label_of 取值无序号语义（编号由调用方按稳定规则做，
    以保证与 component 的编号规则一致）；modularity 为标准无向加权模块度，O(E) 成本。
    """
    keys = list(node_keys)
    if not keys:
        return {}, 0.0
    adj: dict = {k: [] for k in keys}
    for a, b, w in edges:
        if a in adj and b in adj:
            ww = float(w) if w else 1.0
            adj[a].append((b, ww))
            adj[b].append((a, ww))
    lab = {k: k for k in keys}
    order = sorted(keys, key=str)
    for _ in range(max_iter):
        changed = 0
        for k in order:
            nb = adj[k]
            if not nb:
                continue
            acc: dict = defaultdict(float)
            for m, w in nb:
                acc[lab[m]] += w
            best_w = max(acc.values())
            best = min((l for l, w in acc.items() if w == best_w), key=str)
            if lab[k] != best:
                lab[k] = best
                changed += 1
        if changed == 0:
            break
    # 模块度 Q = Σ_c [ 内边权和/m − (度权和/(2m))² ]（标准无向加权模块度，O(n+E)）
    total_w = 0.0
    deg: dict = defaultdict(float)
    inner: dict = defaultdict(float)
    for a, b, w in edges:
        if a in adj and b in adj:
            ww = float(w) if w else 1.0
            total_w += ww
            deg[a] += ww
            deg[b] += ww
            if lab[a] == lab[b]:
                inner[lab[a]] += ww
    Q = 0.0
    if total_w > 0:
        ksum: dict = defaultdict(float)
        for k in keys:
            ksum[lab[k]] += deg[k]
        for c in set(lab.values()):
            Q += inner.get(c, 0.0) / total_w - (ksum[c] / (2.0 * total_w)) ** 2
    return lab, round(Q, 4)


def encode_pos(pos, quantum: int = 100) -> dict:
    """坐标编码：int16 定点量化 + base64（与 build_network.py 契约同构）。

    报告端 JS 用同一套解码逻辑（Int16Array → /scale），故两者必须逐字节兼容：
        q = round(coord / span * 30000)，还原 coord = q / scale，scale = 30000/span。
    """
    if not pos:
        return {"pos_b64": "", "scale": 1.0, "span": 1.0, "quantum": quantum}
    span = max((max(abs(p[0]), abs(p[1])) for p in pos), default=1.0) or 1.0
    scale = 30000.0 / span
    flat = []
    for p in pos:
        flat.append(int(round(p[0] * scale)))
        flat.append(int(round(p[1] * scale)))
    # int16 小端
    buf = bytearray()
    for v in flat:
        v = max(-32768, min(32767, v))
        buf += int(v).to_bytes(2, "little", signed=True)
    return {
        "pos_b64": base64.b64encode(bytes(buf)).decode("ascii"),
        "scale": round(scale, 8),
        "span": round(span, 6),
        "quantum": quantum,
    }


def encode_edges(edges, nodes) -> str:
    """边编码为 varint + base64（与 build_network.py 契约同构，供报告端省字节）。"""
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
