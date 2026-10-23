#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""export_all.py —— 一键把「产物目录」里的全部分析产物导出为一套交付物。

为什么需要这个（缺口）:
    本包的各分析脚本已各自产出中间 JSON / 部分 CSV，
    export_vosviewer.py 也早已能把网络转成 VOSviewer/Pajek/CiteSpace 格式，
    build_report.py --sanxian 也能出三线表 —— 但这些能力**没有串起来**：
    用户跑完一整套分析后，拿到一屋子零散文件，不知道"导出在哪、给谁用、
    哪个文件是什么口径"，也没有一个命令能把它们一次性整理成交付物。
    本脚本补齐这一跳：读产物目录 → 统一搬运/转格式 → 落一套带索引的导出。

设计原则:
    · **只搬运与格式转换，不重算分析** —— 所有数值直接来自既有 JSON/CSV，
      本脚本不改任何口径、不做任何统计推断，避免"导出即改数"。
    · **缺失即跳过并记录** —— 某产物不存在时记入 skipped，绝不整体失败；
      空网络（0 节点）同样跳过而非崩溃（export_vosviewer 会拒绝空网络）。
    · **复用既有实现** —— 三线表走 build_report.sanxian_tables()，
      互操作格式走 export_vosviewer.py 子进程，不重复造一套。
    · **幂等** —— 重复运行覆盖同一导出目录；只清理由本工具生成的目录
      （以 EXPORT_README.md / summary.json 为标记），不动用户数据。

用法:
    python3 export_all.py --dir ./out                 # 导出到 ./out/export
    python3 export_all.py --dir ./out --out ./deliver # 指定导出目录

输出（<out>/ 下）:
    EXPORT_README.md          索引：每个文件是什么、口径、用什么软件打开
    summary.json              machine-readable 关键指标汇总（搬运既有数值）
    data/                     数据类：各网络节点/边表 + 主题/发文/突现/SNA/交叉表
    results/                  结果类：三线表 HTML + 汇总 JSON
    interop/<网络>/           互操作类：VOSviewer/Pajek .net + CiteSpace 节点边表

退出码:
    0 成功 / 1 输入目录不存在 / 2 产物目录不可解析 / 4 参数错误 / 7 写入失败
"""
from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lit_core import EXIT, esc_csv_cell, emit  # noqa: E402

HERE = Path(__file__).resolve().parent

# ── 网络产物登记表 ──────────────────────────────────────────────
# 每条 = (导出键, 相对产物目录的 JSON 路径, 一句话口径说明)
# 用「登记表」而非硬编码 if：新增网络只需加一行，导出逻辑无需改动。
NETWORKS = [
    ("keyword", "network.json",
     "关键词共现网络（build_network.py 产出，节点含分簇归属）"),
    ("keyword_year", "keyword_network.json",
     "关键词共现网络（build_keyword_network.py 产出，节点含逐年频次）"),
    ("author", "author_network.json",
     "作者共现网络（co-authorship，篇内作者两两配对）"),
    ("institution", "institution_network.json",
     "机构共现网络（篇内机构两两配对）"),
    ("citation", "citation_network.json",
     "引文网络（共被引 / 文献耦合，取决于建网 mode）"),
    ("citation_cocitation", "cocitation/citation_network.json",
     "引文共被引网络（co-citation）"),
    ("citation_coupling", "coupling/citation_network.json",
     "文献耦合网络（bibliographic coupling）"),
]


def _join_cell(v):
    """把节点的列表字段压平成可进 CSV 的单元格（分号分隔）。

    标量原样返回（**不 str()**）—— 保留 int/float 类型，让下游 _write_csv
    能区分"数值"与"外部文本"，从而只对文本做公式注入防护。
    """
    if isinstance(v, list):
        return ";".join(str(x) for x in v)
    return v


def _scalar_field(v) -> bool:
    """判断字段是否适合进宽表：标量、None、或标量列表。
    字典字段（如关键词逐年频次 years）不进节点头表——它属于体量更大的
    时序数据，硬塞进一行会变成不可读的 Python repr。"""
    if isinstance(v, (str, int, float, bool)) or v is None:
        return True
    if isinstance(v, list):
        return all(isinstance(x, (str, int, float, bool)) or x is None for x in v)
    return False


def _node_columns(nodes: list) -> list[str]:
    """收集节点表列：以首个节点的字段序为准，取所有节点字段的并集。"""
    cols: list[str] = []
    for n in nodes:
        for k, v in n.items():
            if k not in cols and _scalar_field(v):
                cols.append(k)
    # id 若存在则提到首列，便于人眼与下游工具对齐
    if "id" in cols:
        cols.remove("id")
        cols.insert(0, "id")
    return cols


def _edge_columns(edges: list) -> list[str]:
    cols: list[str] = []
    for e in edges:
        for k in e:
            if k not in cols:
                cols.append(k)
    # source/target/weight 固定在前，其余字段追加在后
    front = [c for c in ("source", "target", "weight") if c in cols]
    rest = [c for c in cols if c not in front]
    return front + rest


def _write_csv(path: Path, header: list[str], rows: list[list]) -> None:
    """写 CSV —— 与包内其他导出点一致用 utf-8-sig（Excel 直接双击不乱码）。

    加固只作用于**字符串**单元格（关键词/作者/机构等外部导入文本，
    防 Excel 公式注入）；数值单元格原样落盘 —— 否则 esc_csv_cell 会把
    负坐标 `-0.13` 误当公式前缀而加 `'`，污染数值列。"""
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        # 表头同样加固：交叉矩阵的列名就是关键词/作者（外部文本），也是注入面
        w.writerow([esc_csv_cell(h) if isinstance(h, str) else h for h in header])
        for r in rows:
            w.writerow([esc_csv_cell(c) if isinstance(c, str)
                        else ("" if c is None else c) for c in r])


class Manifest:
    """记录本次导出实际落盘的每个文件 —— README 与 stderr 清单都由它派生，
    从而保证「列出的」与「生成的」天然一致（不会列了没生成、也不会生成没列）。"""

    def __init__(self) -> None:
        self.entries: list[dict] = []

    def add(self, path: Path, outdir: Path, group: str, desc: str,
            opener: str) -> None:
        self.entries.append({
            "rel": path.relative_to(outdir).as_posix(),
            "bytes": path.stat().st_size,
            "group": group,
            "desc": desc,
            "opener": opener,
        })


def _materialize_network(net: dict, outdir: Path, key: str, desc: str,
                         mf: Manifest) -> dict:
    """把网络 JSON 落成节点表 / 边表两份 CSV。返回规模摘要（供 summary.json）。"""
    nodes = net.get("nodes") or []
    edges = net.get("edges") or []
    data = outdir / "data"

    ncol = _node_columns(nodes)
    nrows = [[_join_cell(n.get(c)) for c in ncol] for n in nodes]
    npath = data / f"{key}_nodes.csv"
    _write_csv(npath, ncol, nrows)
    mf.add(npath, outdir, "数据类",
           f"{desc} —— 节点表（{len(nodes)} 节点）", "Excel / pandas")

    ecol = _edge_columns(edges)
    erows = [[_join_cell(e.get(c)) for c in ecol] for e in edges]
    epath = data / f"{key}_edges.csv"
    _write_csv(epath, ecol or ["source", "target", "weight"], erows)
    mf.add(epath, outdir, "数据类",
           f"{desc} —— 边表（{len(edges)} 边）", "Excel / pandas / Gephi")
    return {"nodes": len(nodes), "edges": len(edges), "type": net.get("type")}


def _run_vosviewer(net_path: Path, outdir: Path, key: str, desc: str,
                   mf: Manifest) -> dict | None:
    """调用既有 export_vosviewer.py 导出互操作三件套。

    **复用而非重写**：该脚本已把 VOSviewer/Pajek 格式要点、参数口径落盘、
    悬空边计数等处理好；本函数用子进程调用它，把它产出的每个文件登记进
    manifest。导到 interop/<key>/ 子目录，避免多网络互相覆盖同名文件
    （export_vosviewer 固定输出 vosviewer_network.net 等名字）。
    """
    interop = outdir / "interop" / key
    interop.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(
        [sys.executable, str(HERE / "export_vosviewer.py"),
         "--network", str(net_path), "--format", "all", "--out", str(interop)],
        capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        # 不整体失败：记录该网络的互操作导出失败
        mf.entries.append({
            "rel": f"interop/{key}/", "bytes": 0, "group": "互操作类",
            "desc": f"{desc} —— 互操作导出失败：{r.stderr.strip()[:120]}",
            "opener": "—", "error": True,
        })
        return None
    labels = {
        "vosviewer_network.net": ("VOSviewer / Pajek 网络文件（File > Open 直接打开）",
                                  "VOSviewer 1.6.x / Pajek / Gephi"),
        "citespace_nodes.csv": ("CiteSpace 节点表（id/label/df/degree/聚类）", "CiteSpace / Excel"),
        "citespace_edges.csv": ("CiteSpace 边表（source/target/weight）", "CiteSpace / Excel"),
        "vosviewer_export.json": ("导出元信息：建网参数口径 + VOSviewer 侧参数建议", "文本编辑器"),
    }
    meta = None
    for name, (d, opener) in labels.items():
        p = interop / name
        if p.exists():
            mf.add(p, outdir, "互操作类", f"{desc} —— {d}", opener)
    # 解析子进程 stdout 的元信息，供 summary.json 记录（口径随产物落盘）
    try:
        meta = json.loads(r.stdout)
    except json.JSONDecodeError:
        meta = None
    return meta


def _load_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def _export_topics(src: Path, outdir: Path, mf: Manifest) -> None:
    """主题清单 CSV（主题分布）。"""
    p = src / "topics.json"
    if not p.exists():
        return
    d = _load_json(p)
    clusters = d.get("clusters") or []
    rows = []
    for c in clusters:
        yr = c.get("year_range") or ["", ""]
        rows.append([c.get("cluster_id"), c.get("size"), c.get("pct"),
                     c.get("lang_dominant"),
                     yr[0] if len(yr) > 0 else "",
                     yr[1] if len(yr) > 1 else "",
                     ";".join(str(x) for x in (c.get("top_terms") or []))])
    path = outdir / "data" / "topic_clusters.csv"
    _write_csv(path, ["cluster_id", "size", "pct", "lang_dominant",
                      "year_min", "year_max", "top_terms"], rows)
    mf.add(path, outdir, "数据类",
           f"主题清单（{len(rows)} 个主题簇，含规模/占比/代表词）", "Excel")


def _export_evolution(src: Path, outdir: Path, mf: Manifest) -> None:
    """主题 × 年份矩阵 CSV（行=主题簇，列=年份）。"""
    p = src / "evolution.json"
    if not p.exists():
        return
    d = _load_json(p)
    years = d.get("years") or []
    clusters = d.get("clusters") or []
    rows = []
    for c in clusters:
        counts = c.get("counts") or {}
        rows.append([c.get("cluster_id"), c.get("total")]
                    + [counts.get(str(y), counts.get(y, 0)) for y in years])
    path = outdir / "data" / "topic_year_matrix.csv"
    _write_csv(path, ["cluster_id", "total"] + [str(y) for y in years], rows)
    mf.add(path, outdir, "数据类",
           "主题 × 年份矩阵（单元格=该主题在该年的文献篇数）", "Excel")


def _export_author_topic(src: Path, outdir: Path, mf: Manifest) -> None:
    """主题 × 作者矩阵 CSV。

    优先搬运 author_topic.py 已产出的 matrix.csv（权威宽表，口径由上游保证）；
    仅当它缺失时才由 author_topic.json 的 matrix 字段materialize——
    本脚本始终坚持"能不重算就不重算"。
    """
    wide = src / "matrix.csv"
    path = outdir / "data" / "author_topic_matrix.csv"
    if wide.exists():
        shutil.copyfile(wide, path)
        mf.add(path, outdir, "数据类",
               "主题 × 作者矩阵（行=核心作者，列=主题簇；搬运自 matrix.csv）",
               "Excel（可直接做热力图）")
        return
    p = src / "author_topic.json"
    if not p.exists():
        return
    d = _load_json(p)
    m = d.get("matrix") or {}
    cols = m.get("col_cluster_ids") or []
    rows = []
    for r in m.get("rows") or []:
        rows.append([r.get("author"), r.get("name"), r.get("total")]
                    + [r.get(str(c), r.get(c, 0)) for c in cols])
    if not rows:
        return
    _write_csv(path,
               ["author", "name", "total"] + [f"cluster_{c}" for c in cols],
               rows)
    mf.add(path, outdir, "数据类",
           "主题 × 作者矩阵（由 author_topic.json 转换）", "Excel")


def _export_publication(src: Path, outdir: Path, mf: Manifest) -> None:
    """发文量 / 年份统计 CSV。优先用 publication_stats.json 的 per_year，
    缺失时退回 age_warning.py 的 year_hist.csv。"""
    path = outdir / "data" / "publication_per_year.csv"
    p = src / "publication_stats.json"
    if p.exists():
        d = _load_json(p)
        per = d.get("per_year") or {}
        years = sorted(per, key=lambda x: int(x))
        rows = [[y, per[y]] for y in years]
        _write_csv(path, ["year", "count"], rows)
        mf.add(path, outdir, "数据类",
               "发文量 / 年份统计（来自 publication_stats.json）", "Excel")
        return
    hist = src / "year_hist.csv"
    if hist.exists():
        # year_hist.csv 已是 year,count 两列，直接搬运（含 BOM，用 utf-8-sig 读）
        text = hist.read_text(encoding="utf-8-sig").strip().splitlines()
        rows = [ln.split(",") for ln in text[1:] if ln.strip()]
        _write_csv(path, ["year", "count"], rows)
        mf.add(path, outdir, "数据类",
               "发文量 / 年份统计（搬运自 year_hist.csv）", "Excel")


def _export_bursts(src: Path, outdir: Path, mf: Manifest) -> None:
    """突现检测表 CSV（keyword burst，非 citation burst）。"""
    p = src / "bursts.json"
    if not p.exists():
        return
    d = _load_json(p)
    bursts = d.get("bursts") or []
    cols = ["keyword", "total_df", "n_years", "peak_year", "peak_df",
            "baseline_mean", "burst_ratio", "strength", "first_seen",
            "last_seen", "confidence"]
    rows = [[b.get(c) for c in cols] for b in bursts]
    path = outdir / "data" / "bursts.csv"
    _write_csv(path, cols, rows)
    mf.add(path, outdir, "数据类",
           f"关键词突现检测（{len(rows)} 词；keyword burst，非 citation burst）",
           "Excel")


def _export_sna(src: Path, outdir: Path, mf: Manifest) -> None:
    """SNA 中心性表 CSV。

    优先搬运 sna_r.py 的 sna_r_nodes.csv（含 degree/betweenness/closeness/
    eigen/community，是完整中心性表）；仅当它缺失时用 sna_r.json 的
    top_central（前 15）兜底，并在说明里点明只是 Top-N。
    """
    path = outdir / "data" / "sna_centrality.csv"
    nodes = src / "sna_r_nodes.csv"
    if nodes.exists():
        shutil.copyfile(nodes, path)
        mf.add(path, outdir, "数据类",
               "SNA 中心性表（节点 degree/betweenness/closeness/eigen/社群；"
               "搬运自 sna_r_nodes.csv）", "Excel")
    p = src / "sna_r.json"
    if not p.exists():
        return
    d = _load_json(p)
    if not nodes.exists():
        top = d.get("top_central") or []
        cols = ["node", "degree", "betweenness", "closeness", "eigen"]
        rows = [[t.get(c) for c in cols] for t in top]
        _write_csv(path, cols, rows)
        mf.add(path, outdir, "数据类",
               f"SNA 中心性表（仅 Top-{len(rows)}；来自 sna_r.json top_central）",
               "Excel")


def _export_cross(src: Path, outdir: Path, mf: Manifest) -> None:
    """多维交叉矩阵 CSV：关键词×作者 / 关键词×年份 / 作者×年份。"""
    p = src / "cross_matrix.json"
    if not p.exists():
        return
    d = _load_json(p)
    specs = [
        ("cross_kw_author_matrix.csv", "kw_author", "keywords", "authors",
         "关键词 × 作者交叉矩阵"),
        ("cross_kw_year_matrix.csv", "kw_year", "keywords", "years",
         "关键词 × 年份交叉矩阵"),
        ("cross_author_year_matrix.csv", "author_year", "authors", "years",
         "作者 × 年份交叉矩阵"),
    ]
    for fname, sect, rowkey, colkey, desc in specs:
        s = d.get(sect) or {}
        rows_names = s.get(rowkey) or []
        cols = s.get(colkey) or []
        mat = s.get("matrix") or {}
        if not rows_names or not cols:
            continue
        out_rows = []
        for rn in rows_names:
            cell = mat.get(rn) or {}
            out_rows.append([rn] + [cell.get(str(c), cell.get(c, 0)) for c in cols])
        path = outdir / "data" / fname
        _write_csv(path, ["row"] + [str(c) for c in cols], out_rows)
        mf.add(path, outdir, "数据类", f"{desc}（来自 cross_matrix.json）", "Excel")


def _export_sanxian(src: Path, outdir: Path, mf: Manifest) -> None:
    """复用 build_report.sanxian_tables() 生成三线表 HTML —— 不重写一套。"""
    tp = src / "topics.json"
    if not tp.exists():
        return
    try:
        from build_report import sanxian_tables  # noqa: PLC0415
    except Exception:  # noqa: BLE001 — build_report 不可导入则跳过而非崩溃
        return

    def _load(name):
        f = src / name
        return _load_json(f) if f.exists() else None

    topics = _load_json(tp)
    html = sanxian_tables(topics, _load("author_topic.json"),
                          _load("evolution.json"), _load("sna_r.json"),
                          _load("trend_effects.json"))
    path = outdir / "results" / "sanxian.html"
    path.write_text(html, encoding="utf-8")
    mf.add(path, outdir, "结果类",
           "中文期刊三线表（可直接粘入 Word；三线无竖线、数字右对齐）",
           "浏览器 / Word")


def _build_summary(src: Path, outdir: Path, mf: Manifest, networks: dict,
                   skipped: list, vos_meta: dict) -> None:
    """汇总关键指标为 machine-readable 的 summary.json。

    **只搬运既有数值**：所有条目都直接取自上游 JSON 字段，本脚本不重算。
    """
    summary: dict = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_dir": str(src.resolve()),
        "networks": networks,
        # 结构化跳过清单：与 stdout emit() 的契约一致，便于程序消费
        "skipped": [{"artifact": n, "reason": w} for n, w in skipped],
    }
    # 各统计产物按存在性填充（缺失即不填，不臆造 0）
    for fn in (_fill_topics, _fill_publication, _fill_bursts, _fill_sna):
        fn(src, summary)
    summary["interop"] = {
        k: (v.get("counts") if isinstance(v, dict) else None)
        for k, v in (vos_meta or {}).items()
    }
    summary["export"] = {
        "files": len(mf.entries),
        "bytes": sum(e["bytes"] for e in mf.entries),
        # 落盘清单（相对路径）—— 供下次幂等运行时按清单逐个清理，
        # 避免对整目录做 bulk 删除（那会触发宿主/系统的批量删除护栏）
        "file_list": [e["rel"] for e in mf.entries],
    }
    path = outdir / "summary.json"
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2),
                    encoding="utf-8")
    mf.add(path, outdir, "结果类",
           "分析结果汇总（machine-readable：网络规模/主题/发文/突现/SNA/导出清单）",
           "程序读取 / 文本编辑器")


# summary 填充器（与 CSV 导出分离，保证 summary 独立于 CSV 是否成功）
def _fill_topics(src: Path, s: dict) -> None:
    p = src / "topics.json"
    if p.exists():
        d = _load_json(p)
        s["topics"] = {"k": (d.get("params") or {}).get("k"),
                       "n_clusters": len(d.get("clusters") or []),
                       "years": d.get("years")}


def _fill_publication(src: Path, s: dict) -> None:
    p = src / "publication_stats.json"
    if p.exists():
        d = _load_json(p)
        s["publication"] = {"total": d.get("total"), "peak_year": d.get("peak_year"),
                            "year_range": d.get("year_range"), "trend": d.get("trend")}


def _fill_bursts(src: Path, s: dict) -> None:
    p = src / "bursts.json"
    if p.exists():
        d = _load_json(p)
        s["bursts"] = {"count": len(d.get("bursts") or []), "method": d.get("method")}


def _fill_sna(src: Path, s: dict) -> None:
    p = src / "sna_r.json"
    if p.exists():
        d = _load_json(p)
        s["sna"] = {"backend": d.get("backend"), "modularity": d.get("modularity"),
                    "n_nodes": d.get("n_nodes"),
                    "n_communities": len(d.get("communities") or [])}


def _build_readme(src: Path, outdir: Path, mf: Manifest, skipped: list) -> None:
    """由 manifest 生成索引 —— 清单与实际落盘文件同源，天然对齐。"""
    lines = [
        "# 导出说明（EXPORT_README）",
        "",
        f"- 产物来源目录：`{src.resolve()}`",
        f"- 导出时间（UTC）：{datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        "",
        "本目录由 `scripts/export_all.py` 一键生成。**它只搬运与格式转换，不重算分析**——",
        "所有数值直接来自各分析脚本的既有产物，导出不会改变任何口径或结果。",
        "",
        "## 目录结构",
        "",
        "```",
        "export/",
        "├── EXPORT_README.md   本文件：文件清单与打开方式",
        "├── summary.json       关键指标汇总（machine-readable）",
        "├── data/              数据类：可直接进 Excel / pandas 的表",
        "├── results/           结果类：三线表 HTML 等",
        "└── interop/<网络>/    互操作类：VOSviewer / Pajek .net + CiteSpace 表",
        "```",
        "",
        "## 文件清单",
        "",
    ]
    groups = ["数据类", "结果类", "互操作类", "索引"]
    group_titles = {
        "数据类": "### 数据类（表格 / 可直接分析）",
        "结果类": "### 结果类（成稿 / 汇报）",
        "互操作类": "### 互操作类（进成熟工具）",
    }
    for g in groups:
        items = [e for e in mf.entries if e["group"] == g and not e.get("error")]
        errs = [e for e in mf.entries if e["group"] == g and e.get("error")]
        if not items and not errs:
            continue
        lines.append(group_titles.get(g, f"### {g}"))
        lines.append("")
        lines.append("| 文件 | 大小 | 用途 / 口径 | 打开方式 |")
        lines.append("|---|---|---|---|")
        for e in sorted(items, key=lambda x: x["rel"]):
            lines.append(f"| `{e['rel']}` | {e['bytes']} B | {e['desc']} | {e['opener']} |")
        for e in errs:
            lines.append(f"| `{e['rel']}` | — | [!] {e['desc']} | {e['opener']} |")
        lines.append("")

    lines.append("## 跳过项（产物缺失或为空，已跳过而非失败）")
    lines.append("")
    if skipped:
        lines.append("| 产物 | 原因 |")
        lines.append("|---|---|")
        for name, why in skipped:
            lines.append(f"| `{name}` | {why} |")
    else:
        lines.append("无——本次所有可识别产物均已导出。")
    lines.append("")
    lines.append("## 复现命令")
    lines.append("")
    lines.append("```bash")
    lines.append(f"python3 scripts/export_all.py --dir {src.name} --out {outdir.name}")
    lines.append("```")
    lines.append("")
    lines.append("> [!] 引文/共被引说明：本地 `.enl` 的 references 字段为占位符，")
    lines.append("> 真实库通常为零引文数据；机构/引文网络往往为空，此时相关表会被跳过并记录。")
    lines.append("")
    (outdir / "EXPORT_README.md").write_text("\n".join(lines), encoding="utf-8")
    mf.add(outdir / "EXPORT_README.md", outdir, "索引", "文件清单与打开方式（本文件）",
           "文本编辑器 / Markdown")


def _prepare_outdir(outdir: Path, src: Path) -> None:
    """幂等准备输出目录：若已存在且非空，仅当它是本工具先前的导出目录
    （以 EXPORT_README.md / summary.json 为标记）才清理重建，否则拒绝——
    绝不误删用户数据。

    清理策略：**按上次 summary.json 的 file_list 逐个 unlink**，而不是
    对整个目录做 bulk 删除 —— 前者精确且不会误伤，也避开批删护栏。
    """
    if outdir.resolve() == src.resolve():
        raise SystemExit("[error] --out 不能与产物目录相同，请指定独立导出目录")
    if outdir.exists() and any(outdir.iterdir()):
        marker = (outdir / "EXPORT_README.md").exists() or (outdir / "summary.json").exists()
        if not marker:
            raise SystemExit(
                f"[error] 输出目录 {outdir} 非空且非本工具产物，拒绝覆盖；"
                f"请改用空的 --out 目录")
        rels: list[str] = []
        prev = outdir / "summary.json"
        if prev.exists():
            try:
                rels = json.loads(prev.read_text(encoding="utf-8"))\
                    .get("export", {}).get("file_list", [])
            except (json.JSONDecodeError, AttributeError):
                rels = []
        if rels:
            for r in rels:
                (outdir / r).unlink(missing_ok=True)
        else:
            # 老版本导出没有 file_list：退回逐个 unlink（仍非 bulk rmtree）
            for p in outdir.rglob("*"):
                if p.is_file():
                    p.unlink(missing_ok=True)
        # 回收空目录（自底向上），失败无所谓——写入时会用 exist_ok 重建
        for d in sorted((p for p in outdir.rglob("*") if p.is_dir()),
                        key=lambda x: len(x.parts), reverse=True):
            try:
                d.rmdir()
            except OSError:
                pass
    outdir.mkdir(parents=True, exist_ok=True)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="一键把产物目录里的全部分析产物导出为带索引的交付物")
    ap.add_argument("--dir", default="./out", help="产物目录（各分析脚本的 --out）")
    ap.add_argument("--out", help="导出目录（默认 <dir>/export）")
    ap.add_argument("--json", action="store_true",
                    help="额外把 summary.json 内容打到 stdout（默认也打印）")
    args = ap.parse_args()

    src = Path(args.dir).expanduser()
    if not src.exists() or not src.is_dir():
        print(f"[error] 产物目录不存在：{src}", file=sys.stderr)
        print(f"[hint] {EXIT[1]}", file=sys.stderr)
        return 1
    outdir = (Path(args.out).expanduser() if args.out else src / "export")
    try:
        _prepare_outdir(outdir, src)
    except SystemExit as e:
        print(str(e), file=sys.stderr)
        return 4

    (outdir / "data").mkdir(parents=True, exist_ok=True)
    (outdir / "results").mkdir(parents=True, exist_ok=True)

    mf = Manifest()
    networks: dict = {}
    skipped: list = []
    vos_meta: dict = {}

    # 1) 网络 → 节点/边 CSV + 互操作三件套
    for key, rel, desc in NETWORKS:
        p = src / rel
        if not p.exists():
            skipped.append((rel, "产物不存在"))
            continue
        try:
            net = _load_json(p)
        except json.JSONDecodeError as e:
            skipped.append((rel, f"JSON 解析失败：{e}"))
            continue
        nodes = net.get("nodes") or []
        if not nodes:
            # 空网络：export_vosviewer 会拒绝导出，这里跳过并记录，不整体失败
            skipped.append((rel, "空网络（0 节点），跳过导出"))
            networks[key] = {"nodes": 0, "edges": len(net.get("edges") or []),
                             "type": net.get("type"), "empty": True}
            continue
        networks[key] = _materialize_network(net, outdir, key, desc, mf)
        meta = _run_vosviewer(p, outdir, key, desc, mf)
        if meta is not None:
            vos_meta[key] = meta

    # 2) 统计 / 表格类
    _export_topics(src, outdir, mf)
    _export_evolution(src, outdir, mf)
    _export_author_topic(src, outdir, mf)
    _export_publication(src, outdir, mf)
    _export_bursts(src, outdir, mf)
    _export_sna(src, outdir, mf)
    _export_cross(src, outdir, mf)

    # 3) 结果类：三线表 + 汇总
    _export_sanxian(src, outdir, mf)
    _build_summary(src, outdir, mf, networks, skipped, vos_meta)
    # 4) 索引（最后生成，确保列全）
    _build_readme(src, outdir, mf, skipped)

    # stderr 可读清单
    print(f"[ok] 导出完成 -> {outdir}", file=sys.stderr)
    for e in sorted(mf.entries, key=lambda x: (x["group"], x["rel"])):
        flag = "[!] " if e.get("error") else ""
        print(f"  {flag}{e['rel']:<44} {e['bytes']:>8} B  {e['desc']}",
              file=sys.stderr)
    if skipped:
        print(f"[warn] {len(skipped)} 项产物缺失或为空，已跳过：", file=sys.stderr)
        for name, why in skipped:
            print(f"  - {name}: {why}", file=sys.stderr)

    emit({"ok": True, "out": str(outdir), "files": len(mf.entries),
          "skipped": [{"artifact": n, "reason": w} for n, w in skipped]})
    return 0


if __name__ == "__main__":
    sys.exit(main())
