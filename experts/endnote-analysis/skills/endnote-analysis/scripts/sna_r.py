#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sna_r.py —— 共现网络的社会网络分析（SNA）封装层

设计铁律（与 EndNote 工具链一致）:
    Python-first, R optional, always degrade gracefully.
    许多用户没有 R；若 R 缺失 / igraph 缺失 / R 运行出错或超时，
    本脚本【绝不失败】，回退到纯 Python 度数排序，并以 exit 0 退出，
    让下游 build_report.py 继续。

退出码（沿用 house 契约，R 问题永远不是硬失败）:
    0  成功（含 python-fallback 降级）
    1  用法错误（参数非法）
    2  输入文件缺失（network.json 不存在）

用法:
    sna_r.py --network network.json --out DIR
             [--topics topics.json] [--rscript /usr/local/bin/Rscript]
             [--force-python]

输出:
    <out>/sna_r.json   机器可读的稳定 schema（见下方 build_result）
    同时向 stdout emit() 一条 JSON 摘要；日志全部走 stderr。
"""
from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from endnote_core import emit  # noqa: E402  house 契约：stdout 仅 JSON，日志走 stderr

import numpy as np
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score

R_SCRIPT = Path(__file__).with_name("sna_r.R")
IGRAPH_INSTALL_HINT = (
    'Rscript -e \'install.packages("igraph", '
    'repos="https://cloud.r-project.org")\''
)

# R 运行超时（秒）。文献库规模下 walktrap 通常在数十秒内完成。
R_TIMEOUT = 300


# ── R 可用性探测 ─────────────────────────────────────────────
def detect_rscript(explicit: str | None) -> str | None:
    """返回可用的 Rscript 路径；--force-python 或找不到则返回 None。"""
    if explicit:
        if Path(explicit).exists():
            return explicit
        # 显式给定但不存在：视为不可用（走 fallback，不报错）
        print(f"[warn] --rscript 指定路径不存在: {explicit}，回退纯 Python",
              file=sys.stderr)
        return None
    found = shutil.which("Rscript")
    return found


def has_igraph(rscript: str) -> bool:
    """探针：igraph 包是否可加载。失败（含 R 异常）一律视为不可用。"""
    try:
        out = subprocess.run(
            [rscript, "-e", 'cat(requireNamespace("igraph", quietly=TRUE))'],
            capture_output=True, text=True, timeout=60,
        )
        return "TRUE" in (out.stdout or "").upper()
    except Exception as e:  # noqa: BLE001
        print(f"[warn] igraph 探针失败: {e}", file=sys.stderr)
        return False


# ── 边表写出 ────────────────────────────────────────────────
def write_edges_csv(network: dict, outdir: Path) -> Path:
    """把 network.json 的 edges 写成 R 可读的 from,to,weight CSV（UTF-8）。

    ⚠️ 关于 esc_csv_cell：此处**故意不用**。该文件是包内中间产物，
    from/to 必须与 network.json 的节点 id 逐字一致，否则 R 侧的
    社群成员名会与报告对不上（加单引号会破坏节点身份对应）。
    风险可控：文件不流向用户的 Excel，且不做任何网络分享。
    若将来要导出给用户看，必须先改为"仅在展示层转义、落盘层保留原值"。
    """
    path = outdir / "sna_r_edges.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["from", "to", "weight"])
        for e in network.get("edges", []):
            w.writerow([e.get("source"), e.get("target"),
                        e.get("weight", 1)])
    return path


# ── R 调用 ──────────────────────────────────────────────────
def run_r(rscript: str, edges_csv: Path, outdir: Path):
    """调用 sna_r.R。返回 (ok, summary_dict, nodes_list)。失败抛 RuntimeError。"""
    proc = subprocess.run(
        [rscript, str(R_SCRIPT), str(edges_csv), str(outdir)],
        capture_output=True, text=True, timeout=R_TIMEOUT,
    )
    if proc.returncode != 0:
        msg = (proc.stderr or proc.stdout or "").strip().splitlines()
        raise RuntimeError("R 运行返回非 0: " + (msg[-1] if msg else "未知错误"))

    summary_path = outdir / "sna_r_summary.json"
    nodes_path = outdir / "sna_r_nodes.csv"
    if not summary_path.exists() or not nodes_path.exists():
        raise RuntimeError("R 未产出预期的汇总/节点文件")

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    # 防御：R 可能"成功退出但交回空图"（如边表只剩表头）。
    # 这种情况必须当作失败走 fallback，否则会报backend="R" 却 n_nodes=0，
    # 用户以为拿到了交叉验证结果，实际什么也没有。
    if not summary.get("n_nodes"):
        raise RuntimeError(
            "R 成功退出但网络为空（0 节点）—— 无有效交叉验证结果。"
            "通常是共现网络被 --min-edge 过滤后无剩余边，请降低阈值重跑。")
    nodes = []
    with open(nodes_path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            nodes.append({
                "node": row["node"],
                "degree": float(row["degree"]),
                "betweenness": float(row["betweenness"]),
                "closeness": float(row["closeness"]),
                "eigen": float(row["eigen"]),
                "community": int(row["community"]),
            })
    return summary, nodes


# ── 纯 Python 降级分析 ──────────────────────────────────────
def undirected_modularity(nodes_ids, adj_weight, partition):
    """纯 Python 计算无向图模块度 Q（加权）。

    Q = Σ_c [ inside_c/(2m) - (K_c/(2m))² ]
    adj_weight: dict[(i,j)] = w（仅上三角或全存均可，按对累计）
    partition: dict[node] = comm_id
    """
    deg = {n: 0.0 for n in nodes_ids}
    m = 0.0
    for (a, b), w in adj_weight.items():
        deg[a] += w
        deg[b] += w
        m += w  # 每条边被 2 个端点各加一次 => 2m
    m = m / 2.0
    if m == 0:
        return 0.0
    inside = {}
    comm_deg = {}
    for (a, b), w in adj_weight.items():
        if partition.get(a) == partition.get(b):
            c = partition[a]
            inside[c] = inside.get(c, 0.0) + w
        ca, cb = partition.get(a), partition.get(b)
        comm_deg[ca] = comm_deg.get(ca, 0.0) + w
        comm_deg[cb] = comm_deg.get(cb, 0.0) + w
    Q = 0.0
    for c in set(partition.values()):
        in_c = inside.get(c, 0.0)
        Kc = comm_deg.get(c, 0.0)
        Q += in_c / (2 * m) - (Kc / (2 * m)) ** 2
    return Q


def fallback_analysis(network: dict):
    """R 不可用时的纯 Python 兜底：度数排序 + primary_cluster 伪社群。"""
    nodes = network.get("nodes", [])
    edges = network.get("edges", [])
    n_nodes = len(nodes)
    n_edges = len(edges)

    node_ids = [nd.get("id") for nd in nodes]
    # 度数（network.json 已有 degree；缺失时从边表重算）
    deg = {nd.get("id"): float(nd.get("degree", 0)) for nd in nodes}
    if sum(deg.values()) == 0 and edges:
        for e in edges:
            deg[e.get("source")] = deg.get(e.get("source"), 0) + 1
            deg[e.get("target")] = deg.get(e.get("target"), 0) + 1

    adj = {}
    for e in edges:
        a, b = e.get("source"), e.get("target")
        if a is None or b is None or a == b:
            continue
        key = tuple(sorted((a, b)))
        adj[key] = adj.get(key, 0.0) + float(e.get("weight", 1))

    # primary_cluster 作为伪社群
    comm_of = {nd.get("id"): nd.get("primary_cluster") for nd in nodes}
    comm_ids = sorted({c for c in comm_of.values() if c is not None})
    comm_sizes = {}
    for c in comm_ids:
        comm_sizes[c] = sum(1 for nd in nodes if nd.get("primary_cluster") == c)
    communities = [
        {"id": c, "size": comm_sizes[c],
         "top_nodes": sorted(
             [nd.get("id") for nd in nodes
              if nd.get("primary_cluster") == c],
             key=lambda x: -deg.get(x, 0))[:8]}
        for c in comm_ids
    ]
    communities.sort(key=lambda x: -x["size"])

    # 模块度 / 密度（无向口径）
    Q = undirected_modularity(node_ids, adj, comm_of)
    dens = (2.0 * len(edges) / (n_nodes * (n_nodes - 1))) if n_nodes > 1 else 0.0

    # top_central：按度数排序，中心性指标置 null（无 igraph 无法计算）
    ranked = sorted(nodes, key=lambda nd: -deg.get(nd.get("id"), 0))
    top_central = [
        {"node": nd.get("id"),
         "degree": deg.get(nd.get("id"), 0),
         "betweenness": None, "closeness": None, "eigen": None}
        for nd in ranked[:15]
    ]
    return {
        "n_nodes": n_nodes, "n_edges": n_edges,
        "modularity": round(Q, 6), "density": round(dens, 6),
        "communities": communities, "top_central": top_central,
    }


# ── 交叉验证 ────────────────────────────────────────────────
def cross_validate(comm_labels, nmf_labels):
    """ARI / NMI：R 社群 vs NMF 主题簇（primary_cluster）。"""
    pairs = [(c, n) for c, n in zip(comm_labels, nmf_labels)
             if c is not None and n is not None]
    if len(pairs) < 2:
        return None, None
    c_lab = [p[0] for p in pairs]
    n_lab = [p[1] for p in pairs]
    try:
        ari = float(adjusted_rand_score(n_lab, c_lab))
    except Exception:  # noqa: BLE001
        ari = None
    try:
        nmi = float(normalized_mutual_info_score(n_lab, c_lab))
    except Exception:  # noqa: BLE001
        nmi = None
    return ari, nmi


# ── 主流程 ──────────────────────────────────────────────────
def build_result(network, backend, *, reason="", r_version="", igraph_version="",
                summary=None, r_nodes=None, hint=""):
    nodes = network.get("nodes", [])
    # NMF primary_cluster（交叉验证基准）
    nmf_of = {nd.get("id"): nd.get("primary_cluster") for nd in nodes}

    if backend == "R" and summary is not None and r_nodes is not None:
        n_nodes = int(summary["n_nodes"])
        n_edges = int(summary["n_edges"])
        modularity = summary.get("modularity")
        density = summary.get("density")
        # 社群规模（来自 R summary）
        comm_sizes = {c["id"]: c["size"] for c in summary.get("communities", [])}
        # 每社群 top 节点（按度数）
        by_comm = {}
        for nd in r_nodes:
            by_comm.setdefault(nd["community"], []).append(nd)
        communities = []
        for cid, size in comm_sizes.items():
            members = sorted(by_comm.get(cid, []),
                             key=lambda d: -d["betweenness"])[:8]
            communities.append({
                "id": cid, "size": size,
                "top_nodes": [m["node"] for m in members],
            })
        communities.sort(key=lambda x: -x["size"])
        top_central = [
            {"node": d["node"], "degree": d["degree"],
             "betweenness": d["betweenness"], "closeness": d["closeness"],
             "eigen": d["eigen"]}
            for d in sorted(r_nodes, key=lambda d: -d["betweenness"])[:15]
        ]
        r_comm_labels = [nd["community"] for nd in r_nodes]
        nmf_labels = [nmf_of.get(nd["node"]) for nd in r_nodes]
    else:
        fb = fallback_analysis(network)
        n_nodes, n_edges = fb["n_nodes"], fb["n_edges"]
        modularity, density = fb["modularity"], fb["density"]
        communities, top_central = fb["communities"], fb["top_central"]
        r_comm_labels = [nmf_of.get(nd.get("id")) for nd in nodes]
        nmf_labels = [nmf_of.get(nd.get("id")) for nd in nodes]

    ari, nmi = cross_validate(r_comm_labels, nmf_labels)
    if backend == "R":
        cv_note = "R walktrap 社群 vs NMF primary_cluster 的一致性"
    else:
        cv_note = ("R 不可用，交叉验证需 R 的 walktrap 社群，已省略；"
                   "python-fallback 仅做度数排序与 primary_cluster 伪社群")

    return {
        "ok": True,
        "backend": backend,
        "reason": reason,
        "r_version": r_version,
        "igraph_version": igraph_version,
        "n_nodes": n_nodes,
        "n_edges": n_edges,
        "modularity": modularity,
        "density": density,
        "communities": communities,
        "top_central": top_central,
        "cross_validation": {
            "ari_vs_nmf": ari,
            "nmi_vs_nmf": nmi,
            "note": cv_note,
        },
        "hint": hint,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="共现网络 SNA（可选 R 增强）")
    ap.add_argument("--network", required=True, help="network.json 路径")
    ap.add_argument("--out", required=True, help="输出目录")
    ap.add_argument("--topics", help="topics.json（可选，兼容 CLI；主用 network.json 的 primary_cluster）")
    ap.add_argument("--rscript", default="/usr/local/bin/Rscript",
                    help="Rscript 路径（默认 /usr/local/bin/Rscript）")
    ap.add_argument("--force-python", action="store_true",
                    help="强制使用纯 Python 降级路径，不尝试 R")
    args = ap.parse_args()

    net_path = Path(args.network)
    if not net_path.exists():
        print(f"[error] 输入文件缺失: {net_path}", file=sys.stderr)
        print(f"[hint] {EXIT[2]}", file=sys.stderr)
        return 2

    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    network = json.loads(net_path.read_text(encoding="utf-8"))

    # 1) R 可用性判定
    rscript = None if args.force_python else detect_rscript(args.rscript)
    ig_ok = False
    r_version = ""
    if rscript:
        ig_ok = has_igraph(rscript)
        if not ig_ok:
            # 仍尝试取 R 版本号用于提示
            try:
                v = subprocess.run([rscript, "--version"],
                                   capture_output=True, text=True, timeout=30)
                r_version = (v.stdout or v.stderr or "").splitlines()[0].strip()
            except Exception:
                pass

    # 2) 尝试 R 路径
    if rscript and ig_ok:
        try:
            edges_csv = write_edges_csv(network, outdir)
            summary, r_nodes = run_r(rscript, edges_csv, outdir)
            result = build_result(
                network, "R",
                r_version=summary.get("r_version", ""),
                igraph_version=summary.get("igraph_version", ""),
                summary=summary, r_nodes=r_nodes,
            )
            (outdir / "sna_r.json").write_text(
                json.dumps(result, ensure_ascii=False, indent=2),
                encoding="utf-8")
            emit(result)
            return 0
        except subprocess.TimeoutExpired:
            reason = f"R 运行超时（>{R_TIMEOUT}s），已回退纯 Python"
            print(f"[warn] {reason}", file=sys.stderr)
        except Exception as e:  # noqa: BLE001
            reason = f"R 路径失败：{type(e).__name__}: {e}，已回退纯 Python"
            print(f"[warn] {reason}", file=sys.stderr)
    else:
        if args.force_python:
            reason = "用户指定 --force-python，使用纯 Python 降级路径"
        elif not rscript:
            reason = "未找到可用的 Rscript，使用纯 Python 降级路径"
        else:
            reason = "R 已安装但缺少 igraph 包，使用纯 Python 降级路径"
        print(f"[warn] {reason}", file=sys.stderr)

    # 3) 降级路径（永不失败）
    result = build_result(
        network, "python-fallback",
        reason=reason,
        r_version=r_version,
        igraph_version="",
        hint=IGRAPH_INSTALL_HINT,
    )
    (outdir / "sna_r.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8")
    emit(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
