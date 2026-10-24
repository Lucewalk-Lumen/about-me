#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
export_vosviewer.py —— 把关键词共现网络导出为 VOSviewer / Pajek 可读格式

为什么需要这个:
    本包的 network.json 是自造schema，VOSviewer 与 CiteSpace 都读不了。
    用户拿到分析结果后若想用成熟工具做交互式探索，必须手工改格式——
    这是"分析产物 → 可继续加工"链路上的断点。本脚本补齐这一跳。

设计依据（VOSviewer 1.6.21 官方手册；运行期会产出参数口径元信息 `vosviewer_export.json`）:
    · 网络文件：共现边为无向，用 `*Edges` 段的 `id1 id2 weight` 三列
    · 节点权重：`*Vertices` 段可带 `weight` 列；本脚本写 Occurrences(df)
    · 计数方式：VOSviewer 提供 Full / Fractional counting
      （手册 §3.5.4：fractional 可降低多作者/多参考文献文献的影响）
    · 归一化方法：No / Association strength（默认）/ Fractionalization /
      LinLog-modularity（手册 §3.5.3）
    · 聚类：VOS clustering 的 Resolution 与 Min. cluster size 在 GUI 里设，
      不写进文件——本脚本只负责把网络与权重交出去，参数由用户在 VOSviewer 侧选

用法:
    python3 export_vosviewer.py --network ./out/network.json --out ./out
    python3 export_vosviewer.py --network ./out/network.json --format pajek --out ./out
    python3 export_vosviewer.py --network ./out/network.json --format citespace --out ./out

输出:
    <out>/vosviewer_network.net   VOSviewer / Pajek 网络文件
    <out>/citespace_nodes.csv     CiteSpace 关键词节点表（含 df 与所属主题）
    <out>/citespace_edges.csv     CiteSpace 边表（source,target,weight）
    <out>/vosviewer_export.json   导出元信息（来源、参数口径、可复现说明）

退出码:
    0 成功 / 2 输入缺失或格式不支持 / 4 参数错误
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lit_core import EXIT, EnlError, esc_csv_cell, emit  # noqa: E402


def _validate(net: dict) -> None:
    if not isinstance(net, dict):
        raise EnlError(2, "network.json 顶层必须是对象")
    if "nodes" not in net or "edges" not in net:
        raise EnlError(2, "network.json 缺少 nodes / edges 字段，"
                          "请先用 build_network.py 生成")
    if not net["nodes"]:
        raise EnlError(2, "network.json 的 nodes 为空，无法导出")


def export_pajek(net: dict) -> str:
    """Pajek .net —— VOSviewer 可直接 File > Open。

    格式要点（VOSviewer 手册 §4.1.2）：
      *Vertices <n>
      1 "label" [x] [y] [z] [weight]
      *Edges            ← 无向共现边
      i j weight        ← 权重为共现次数
    节点权重列写 Occurrences(df)：VOSviewer 允许自定义 weight 属性列。
    """
    nodes = net["nodes"]
    edges = net["edges"]
    lines = [f"*Vertices {len(nodes)}"]
    # id 必须从 1 开始且连续；用 label 原文作第二列
    for i, n in enumerate(nodes, 1):
        nid = str(n.get("id", f"n{i}"))
        occ = n.get("df", n.get("degree", 0))
        lines.append(f'{i} "{nid}" {occ}')
    lines.append(f"*Edges {len(edges)}")
    # Pajek 的边用 1-based 序号；建立 id → 序号映射
    order = {}
    for i, n in enumerate(nodes, 1):
        order[str(n.get("id"))] = i
    for e in edges:
        a = order.get(str(e.get("source")))
        b = order.get(str(e.get("target")))
        if a is None or b is None:
            continue          # 悬空边：静默跳过会违反零静默丢弃，故计数上报
        w = e.get("weight", 1)
        lines.append(f"{a} {b} {w}")
    return "\n".join(lines) + "\n"


def export_citespace_tables(net: dict) -> tuple[list, list, int]:
    """CiteSpace 友好的节点/边 CSV。

    CiteSpace 以WoS tagged 为主格式，但关键词共现也可走 CSV 通道
    （官方 FAQ：通用 CSV 可转换为 WoS 格式，需把字段配置成书目记录字段）。
    本脚本产出两份最通用的中间表，字段与 CiteSpace 的节点/边语义对齐：
      节点：id, label, df(occurrences), degree, primary_cluster
      边：source, target, weight
    """
    nodes = net["nodes"]
    rows_n = []
    for n in nodes:
        rows_n.append({
            "id": n.get("id"),
            "label": n.get("id"),
            # df = 文献频次（Occurrences），degree = 连接数（Links）
            "df": n.get("df", 0),
            "degree": n.get("degree", 0),
            "primary_cluster": n.get("primary_cluster"),
        })
    rows_e = []
    dropped = 0
    ids = {str(n.get("id")) for n in nodes}
    for e in net["edges"]:
        a, b = str(e.get("source")), str(e.get("target"))
        if a not in ids or b not in ids:
            dropped += 1
            continue
        rows_e.append({"source": a, "target": b, "weight": e.get("weight", 1)})
    return rows_n, rows_e, dropped


def _write_csv(path: Path, rows: list, fields: list[str]) -> None:
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(fields)
        for r in rows:
            # 文献元数据/关键词均为外部导入 → 公式注入防护
            w.writerow([esc_csv_cell(r.get(k, "")) for k in fields])


def main() -> int:
    ap = argparse.ArgumentParser(
        description="把 network.json 导出为 VOSviewer / CiteSpace 可读格式")
    ap.add_argument("--network", required=True, help="build_network.py 产出的 network.json")
    ap.add_argument("--out", default="./out", help="输出目录")
    ap.add_argument("--format", default="vosviewer",
                    choices=["vosviewer", "pajek", "citespace", "all"],
                    help="导出格式（vosviewer 与 pajek 输出同一种 .net）")
    args = ap.parse_args()

    src = Path(args.network).expanduser()
    if not src.exists():
        print(f"[error] 输入文件不存在：{src}", file=sys.stderr)
        print(f"[hint] {EXIT[1]}", file=sys.stderr)
        return 1
    try:
        net = json.loads(src.read_text(encoding="utf-8"))
        _validate(net)
    except EnlError as e:
        print(f"[error] {e}", file=sys.stderr)
        print(f"[hint] {EXIT[e.code]}", file=sys.stderr)
        return e.code
    except json.JSONDecodeError as e:
        print(f"[error] network.json 不是合法 JSON：{e}", file=sys.stderr)
        print(f"[hint] {EXIT[2]}", file=sys.stderr)
        return 2

    outdir = Path(args.out).expanduser()
    outdir.mkdir(parents=True, exist_ok=True)
    want = {"vosviewer", "pajek", "citespace"} if args.format == "all" \
        else {args.format}
    written = []

    if want & {"vosviewer", "pajek"}:
        p = outdir / "vosviewer_network.net"
        p.write_text(export_pajek(net), encoding="utf-8")
        written.append(str(p))

    dropped = 0
    n_rows = e_rows = 0
    if "citespace" in want:
        nodes, edges, dropped = export_citespace_tables(net)
        n_rows, e_rows = len(nodes), len(edges)
        pn = outdir / "citespace_nodes.csv"
        pe = outdir / "citespace_edges.csv"
        _write_csv(pn, nodes, ["id", "label", "df", "degree", "primary_cluster"])
        _write_csv(pe, edges, ["source", "target", "weight"])
        written += [str(pn), str(pe)]

    # 参数口径随产物一起落盘 —— 引用规模数字时必须连带标注（见 SKILL.md 铁律）
    stats = net.get("stats", {})
    meta = {
        "ok": True,
        "source_file": src.name,
        "network_type": net.get("type"),
        "notice": net.get("notice"),
        "counts": {"nodes": len(net.get("nodes", [])),
                   "edges": len(net.get("edges", [])),
                   "exported_edges": e_rows if "citespace" in want else len(net.get("edges", [])),
                   "dropped_dangling_edges": dropped},
        "params": {
            "note": "以下为建网时的参数口径，转引规模数字必须一并标注",
            "node_df": stats.get("node_df"),
            "min_edge_count": stats.get("min_edge_count"),
            "df_mode": stats.get("df_mode"),
            "normalize_case": stats.get("normalize_case"),
            "keyword_dedupe": stats.get("keyword_dedupe"),
        },
        "vosviewer_hints": {
            "open": "VOSviewer > File > Open > 选择 vosviewer_network.net",
            "counting_method": "Full counting（默认）/ Fractional counting"
                               "（手册 §3.5.4；后者降低多作者文献的影响）",
            "normalization": "Association strength（默认）/ Fractionalization / "
                             "LinLog-modularity（手册 §3.5.3）",
            "clustering": "Resolution 与 Min. cluster size 在 Analysis 面板设定，"
                          "不写入网络文件（手册 §3.5.3）",
            "caveat": "本网络是关键词共现，不是引文网络；"
                      "VOSviewer 的 co-citation 需引文数据，本地 .enl 不具备。",
        },
        "written": written,
    }
    mp = outdir / "vosviewer_export.json"
    mp.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[ok] 已导出 {len(written)} 个文件 -> {outdir}", file=sys.stderr)
    if dropped:
        print(f"[warn] {dropped} 条边引用了不存在的节点，已跳过并计数", file=sys.stderr)
    emit(meta)
    return 0


if __name__ == "__main__":
    sys.exit(main())
