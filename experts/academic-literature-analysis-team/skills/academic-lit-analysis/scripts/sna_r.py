#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sna_r.py —— 共现网络的社会网络分析（SNA）封装层

设计铁律（口径变更）:
    R + igraph 是【标准路径，必需】。计量分析要有标准工具链，结果才可复现、
    才能与他人的 bibliometrix / igraph 结果对话。因此：
      · R / igraph 不可用 → 【直接失败】并给出可复制的安装指引，绝不静默回退；
      · 若确需在缺 R 的机器上产出，必须由用户【显式】传 --allow-python-fallback，
        且产物 sna_r.json 会如实写 backend="python-fallback" 并显著标注为非标准路径。

    为什么默认取「硬失败」而非「静默回退」:
      旧行为下 R 缺失也会 exit 0、产出一份 backend="python-fallback" 的结果，
      下游报告照常渲染成一整份「完整报告」，用户却不知道其中的网络部分
      既没有独立社群划分、也没有 ARI/NMI 交叉验证 —— 只是度数排序。
      这种静默降级最危险：用户极可能在读图或写方法章节时把它当成标准 SNA 结果引用。

退出码（沿用 lit_core.EXIT house 契约，唯一事实源）:
    0  成功（standard=R 路径，或经 --allow-python-fallback 显式回退）
    4  参数错误（如 --network 指向的 network.json 不存在）
    8  环境不满足：R / igraph 不可用且未允许回退（必需前置条件缺失）

用法:
    sna_r.py --network network.json --out DIR
             [--topics topics.json] [--rscript /path/to/Rscript]
             [--allow-python-fallback]

输出:
    <out>/sna_r.json   机器可读的稳定 schema（见下方 build_result）
    同时向 stdout emit() 一条 JSON 摘要；日志全部走 stderr。
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lit_core import emit, EXIT, find_rscript  # noqa: E402  house 契约：stdout 仅 JSON，日志走 stderr

from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score

R_SCRIPT = Path(__file__).with_name("sna_r.R")

# 可复制的安装指引：R 下载 → 镜像配置 → install.packages('igraph')。
# 装到用户库（R_LIBS_USER）而非 R 安装目录 —— 后者在 Windows 上通常需管理员
# 权限、直接失败；用户库无需提权，且 .libPaths() 默认已包含它。
IGRAPH_INSTALL_HINT = (
    "R + igraph 是计量分析的标准路径，必须安装后才能运行：\n"
    "  1) 安装 R（>=4.2）: https://cran.r-project.org/  "
    "（Windows 下载 base 安装包；安装向导里勾选「Add R to PATH」可省去路径烦恼）\n"
    "  2) 配置国内镜像加速（写入 ~/.Rprofile 更持久）:\n"
    "     options(repos = c(CRAN = \"https://mirrors.tuna.tsinghua.edu.cn/CRAN/\"))\n"
    "  3) 安装 igraph（装到用户库，无需管理员权限）:\n"
    "     Rscript -e \"install.packages('igraph', lib=Sys.getenv('R_LIBS_USER'), "
    "repos='https://mirrors.tuna.tsinghua.edu.cn/CRAN/')\"\n"
    "  若 Rscript 不在 PATH（Windows 常见），直接用完整路径，例如\n"
    "     \"C:/Program Files/R/R-<版本>/bin/Rscript.exe\" 或向 sna_r.py 传 --rscript。"
)

# R 运行超时（秒）。文献库规模下 walktrap 通常在数十秒内完成。
R_TIMEOUT = 300


# ── R 可用性探测 ─────────────────────────────────────────────
# 探测实现已上收到 lit_core.find_rscript（唯一实现）：doctor.py（门禁）
# 此前另写了一套只扫 Windows 路径的 glob，两处口径不一致会导致
# 「doctor 说环境 OK、sna_r 却 exit 8」的自相矛盾。原先本文件里的
# _glob_rscript() 因无调用方已删除 —— 留着只会让人以为还有第二条路径。
def detect_rscript(explicit: str | None):
    """定位 Rscript，返回 (path | None, source)。

    R 现在是标准路径的**必需**前置条件，故本函数只负责「找到没有」，
    不再承担「找不到就静默回退」的职责 —— 是否回退由 main() 依据
    --allow-python-fallback 决定。source 用于把「装好但没进 PATH」讲清楚。
    """
    if explicit:
        if Path(explicit).exists():
            return explicit, "explicit"
        return None, f"--rscript 指定路径不存在: {explicit}"
    # 探测委托 lit_core.find_rscript（唯一实现），source 语义如下：
    # "PATH" = 命中 PATH；"glob" = 装好了但不在 PATH。
    path, source = find_rscript()
    if path:
        return path, source
    return None, "未在 PATH 或常见安装目录找到 Rscript"


def probe_igraph(rscript: str):
    """探针 igraph 是否可加载，返回 (version | None, error)。

    直接取 packageVersion，既可判定可用性又顺手拿到版本号（用于日志与产物）。
    """
    try:
        out = subprocess.run(
            [rscript, "-e", 'cat(as.character(packageVersion("igraph")))'],
            capture_output=True, text=True, timeout=60,
        )
        ver = (out.stdout or "").strip().splitlines()[-1] if out.stdout else ""
        if out.returncode == 0 and ver and "Error" not in ver:
            return ver, ""
        return None, "R 已找到，但未安装 igraph 包"
    except Exception as e:  # noqa: BLE001
        return None, f"igraph 探针调用失败：{type(e).__name__}: {e}"


def r_version_of(rscript: str) -> str:
    """取 R 版本串（失败返回空串，仅用于报错提示，不阻断）。"""
    try:
        v = subprocess.run([rscript, "--version"],
                           capture_output=True, text=True, timeout=30)
        return (v.stdout or v.stderr or "").splitlines()[0].strip()
    except Exception:  # noqa: BLE001
        return ""


# ── 边表写出 ────────────────────────────────────────────────
def write_edges_csv(network: dict, outdir: Path) -> Path:
    """把 network.json 的 edges 写成 R 可读的 from,to,weight CSV（UTF-8）。

    [!]  关于 esc_csv_cell：此处**故意不用**。该文件是包内中间产物，
    from/to 必须与 network.json 的节点 id 逐字一致，否则 R 侧的
    社群成员名会与报告对不上（加单引号会破坏节点身份对应）。
    风险可控：文件不流向用户的 Excel，且不做任何网络分享。
    若将来要导出给用户看，必须先改为"仅在展示层转义、落盘层保留原值"。
    """
    path = outdir / "sna_r_edges.csv"
    # 不加 BOM：BOM 会让 R 把首列名读成 "﻿from"，导致列名校验失败。
    # Windows 中文区域设置下 R 对无 BOM UTF-8 的解码由 sna_r.R 侧负责
    # （那里用二进制连接 + 显式 UTF-8 解码，已实测通过）。
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["from", "to", "weight"])
        for e in network.get("edges", []):
            w.writerow([e.get("source"), e.get("target"),
                        e.get("weight", 1)])
    return path


# ── R 调用 ──────────────────────────────────────────────────
def _ascii_staging_dir(tag: str) -> Path:
    """R 在 Windows 下无法接收含中文的命令行参数（路径会被损坏成
    「文件不存在」）。故把R 的工作目录中转到一个纯 ASCII 的临时目录。"""
    base = Path(os.environ.get("TEMP") or tempfile.gettempdir())
    d = base / f"en_analysis_r_{tag}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def run_r(rscript: str, edges_csv: Path, outdir: Path):
    """调用 sna_r.R。返回 (ok, summary_dict, nodes_list)。失败抛 RuntimeError。

    Windows 下 Rscript 对含中文的命令行参数会解码损坏，故统一在纯 ASCII
    目录中转：脚本、边表、产出三者的路径都先复制到中转目录，执行完再取回。
    """
    staging = _ascii_staging_dir("stage")
    for p in staging.glob("*"):
        try:
            p.unlink()
        except OSError:
            pass
    r_script_stage = staging / R_SCRIPT.name
    edges_stage = staging / "sna_r_edges.csv"
    shutil.copy2(R_SCRIPT, r_script_stage)
    shutil.copy2(edges_csv, edges_stage)

    proc = subprocess.run(
        [rscript, str(r_script_stage), str(edges_stage), str(staging)],
        capture_output=True, text=True, timeout=R_TIMEOUT,
    )
    if proc.returncode != 0:
        msg = (proc.stderr or proc.stdout or "").strip().splitlines()
        raise RuntimeError("R 运行返回非 0: " + (msg[-1] if msg else "未知错误"))

    summary_path = staging / "sna_r_summary.json"
    nodes_path = staging / "sna_r_nodes.csv"
    if not summary_path.exists() or not nodes_path.exists():
        raise RuntimeError("R 未产出预期的汇总/节点文件")

    # 产物取回真实输出目录
    for name in ("sna_r_summary.json", "sna_r_nodes.csv"):
        src = staging / name
        if src.exists():
            shutil.copy2(src, outdir / name)

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    # 防御：R 可能"成功退出但交回空图"（如边表只剩表头）。
    # 这种情况必须当作失败走 fallback，否则会报backend="R" 却 n_nodes=0，
    # 用户以为拿到了交叉验证结果，实际什么也没有。
    if not summary.get("n_nodes"):
        raise RuntimeError(
            "R 成功退出但网络为空（0 节点）—— 无有效交叉验证结果。"
            "通常是共现网络被 --min-edge 过滤后无剩余边，请降低阈值重跑。")
    nodes = []
    # utf-8-sig：R 侧按 UTF-8-BOM 写出，用普通 utf-8 读会把 BOM 当成首列名
    # 的第一个字符（列名变成 "﻿node"），导致 KeyError。
    def _f(v):
        # v1.0.0：不连通图下 igraph 可能写出空/NA/NaN 中心性，
        # float(None)/float("NA") 会崩 —— 一律容错为 0.0。
        try:
            x = float(v)
            return x if x == x and x not in (float("inf"), float("-inf")) else 0.0
        except (TypeError, ValueError):
            return 0.0

    with open(nodes_path, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            nodes.append({
                "node": row["node"],
                "degree": _f(row.get("degree")),
                "betweenness": _f(row.get("betweenness")),
                "closeness": _f(row.get("closeness")),
                "eigen": _f(row.get("eigen")),
                "community": int(float(row.get("community") or 0)),
            })
    return summary, nodes


# ── 纯 Python 降级分析 ──────────────────────────────────────
def undirected_modularity(nodes_ids, adj_weight, partition):
    """纯 Python 计算无向图模块度 Q（加权）。

    标准定义（与 networkx.algorithms.community.modularity 一致）:
        W      = 所有边权之和（每条边只加一次）
        in_c   = 社区 c 内部边权之和（每条边只加一次）
        K_c    = 社区 c 内所有节点的加权度数之和
        Q = Σ_c [ in_c/W - (K_c/(2W))² ]

    [!] 模块度口径说明:
       原实现每条边只 `m += w` 一次，故m 是总边权W；随后又`m = m / 2.0`
       把W 变成 W/2，却仍按 `in_c/(2m) - (Kc/(2m))²` 代入 —— 第一项于是
       变成 in_c/W（正确），第二项变成 (Kc/W)²（**错了 4 倍**，应为
       (Kc/(2W))²）。缺一个稀疏社群时即可得到负Q，而标准归一化模块度
       的期望值是非负的，负值对用户完全不可解释。
       现直接以 W 为分母，避免再引入"半个m"这种歧义命名。

    adj_weight: dict[(i,j)] = w（无向，每条边只出现一次）
    partition: dict[node] = comm_id
    """
    deg = {n: 0.0 for n in nodes_ids}
    W = 0.0
    for (a, b), w in adj_weight.items():
        deg[a] += w
        deg[b] += w
        W += w  # 每条边只加一次 => W = 总边权（不是 2W）
    if W == 0:
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
        Q += in_c / W - (Kc / (2 * W)) ** 2
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
        # 每社群top 节点（按度数）
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
        # 唯一有意义的交叉验证：walktrap 社群 vs NMF 主题簇（互相独立）
        r_comm_labels = [nd["community"] for nd in r_nodes]
        nmf_labels = [nmf_of.get(nd["node"]) for nd in r_nodes]
    else:
        fb = fallback_analysis(network)
        n_nodes, n_edges = fb["n_nodes"], fb["n_edges"]
        modularity, density = fb["modularity"], fb["density"]
        communities, top_central = fb["communities"], fb["top_central"]
        # [!]  修正：此处**不做**交叉验证。
        # 无 R 时不存在独立的社群划分（fallback 只有 primary_cluster 伪社群），
        # 若拿 primary_cluster 与自身比较，ARI/NMI 恒等于 1.0 —— 那是"自己跟自己
        # 比"，不是方法学交叉验证，却会被报告成"社群与主题高度一致"，
        # 凭空制造一条并不存在的验证结论。故置 None，如实上报"未做"。
        r_comm_labels = None
        nmf_labels = None

    if r_comm_labels is None:
        ari, nmi = None, None
    else:
        ari, nmi = cross_validate(r_comm_labels, nmf_labels)
    if backend == "R":
        cv_note = "R walktrap 社群 vs NMF primary_cluster 的一致性"
    else:
        cv_note = ("R 不可用，**未做交叉验证**（无独立的社群划分可比；"
                   "python-fallback 仅做度数排序与 primary_cluster 伪社群，"
                   "拿它与自身比较会恒得 ARI=NMI=1.0，属伪造结论）。"
                   "启用 R 后可获得真实的「共现社群 vs 研究主题」交叉验证。")

    # 显著标注：只有 R 才是标准路径。回退产物必须让下游/用户一眼看出
    # 「这不是标准 SNA 结果」，避免被当成 R 交叉验证结果引用。
    warning = ""
    if backend != "R":
        warning = (
            "非标准路径：本次由 --allow-python-fallback 触发纯 Python 回退，"
            "未经 R/igraph 验证（无独立社群划分、无 ARI/NMI 交叉验证）。"
            "计量分析要求标准工具链与可复现，请安装 R + igraph 后重跑。")
    return {
        "ok": True,
        "backend": backend,
        "is_standard_path": backend == "R",
        "warning": warning,
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
    ap = argparse.ArgumentParser(
        description="共现网络 SNA（R/igraph 为标准路径；缺 R 默认失败，不回退）")
    ap.add_argument("--network", required=True, help="network.json 路径")
    ap.add_argument("--out", required=True, help="输出目录")
    ap.add_argument("--topics", help="topics.json（可选，兼容 CLI；主用 network.json 的 primary_cluster）")
    ap.add_argument("--rscript", default=None,
                    help="显式指定 Rscript 路径（默认自动探测 PATH 与常见安装目录）")
    ap.add_argument("--allow-python-fallback", action="store_true",
                    help="显式允许 R/igraph 不可用时回退纯 Python（非标准路径，产物会显著标注）")
    args = ap.parse_args()

    net_path = Path(args.network)
    if not net_path.exists():
        print(f"[error] 输入文件缺失: {net_path}", file=sys.stderr)
        print(f"[hint] {EXIT[4]}；先运行 build_network.py 生成 network.json，"
              "再把其路径传给 --network。", file=sys.stderr)
        return 4

    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    network = json.loads(net_path.read_text(encoding="utf-8"))

    # 1) 定位 R 并探针 igraph（R 为标准路径，必须齐备）
    rscript, src = detect_rscript(args.rscript)
    if rscript and src == "glob":
        # 「找到了 R 但没在 PATH」是 Windows 的常见情形，单独讲清楚，
        # 否则用户会以为工具没找到 R、又去重装一遍。
        print(f"[info] 未在 PATH 找到 Rscript，已按常见安装目录回退到:\n"
              f"       {rscript}\n"
              f"       （Windows 版 R 默认不把 bin 加进 PATH；可将其加入 PATH，"
              f"或日后用 --rscript 显式指定。）", file=sys.stderr)
    r_version = r_version_of(rscript) if rscript else ""
    ig_ver, ig_err = probe_igraph(rscript) if rscript else (None, "未找到 Rscript")

    # 2) 标准路径：R + igraph 齐备则跑 R
    if rscript and ig_ver:
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
            fail_reason = f"R 运行超时（>{R_TIMEOUT}s）"
        except Exception as e:  # noqa: BLE001
            fail_reason = f"R 路径运行失败：{type(e).__name__}: {e}"

    # 3) 标准路径不可用 —— 默认硬失败，绝不静默回退
    if not rscript:
        detail = src
    elif not ig_ver:
        detail = f"{ig_err}（R: {r_version or rscript}）"
    else:
        detail = fail_reason
    print(f"\n[error] 标准 SNA 路径不可用：{detail}", file=sys.stderr)

    if not args.allow_python_fallback:
        print("[hint] R + igraph 是计量分析的标准路径（必需前置条件），"
              "本脚本不再静默回退纯 Python。\n"
              "       如确需在缺 R 的机器上勉强产出（非标准、不可与 R 结果互换引用），"
              "请显式加 --allow-python-fallback。\n"
              + IGRAPH_INSTALL_HINT, file=sys.stderr)
        return 8

    # 4) 显式回退（唯一允许的降级入口；产物显著标注为非标准路径）
    reason = f"{detail}；经用户显式 --allow-python-fallback 回退纯 Python（非标准路径）"
    print(f"[warn] {reason}", file=sys.stderr)
    print(IGRAPH_INSTALL_HINT, file=sys.stderr)
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
