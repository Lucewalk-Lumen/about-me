#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
author_topic.py —— 功能#3：主题 × 作者矩阵 / 核心作者识别

用法:
    python3 author_topic.py <库目录或.enl> --topics topics.json
                            [--out DIR] [--workspace DIR]
                            [--top-authors 10] [--top-core 20] [--matrix-authors 40]

依赖: 须先运行 cluster_topics.py 产出 topics.json（提供 ref→主题簇映射）。
      未传 --topics 时仍可输出「全局核心作者」，但主题矩阵为空。

口径:
    - 作者 canon = 'surname|initials'（来自 lit_core.parse_authors），
      同名不同名靠 initials 区分。
    - 主题归属以 topics.json 的 ref_ids 为稳定主键（= int(r.id)）。
    - 矩阵 cell = 该作者在该主题簇文献中出现的次数（非占比）。

输出: author_topic.json / author_topic.csv（长表）/ matrix.csv（宽表，供报告渲染热图）。
全程只读。
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lit_core import (  # noqa: E402
    EnlError, EXIT, emit, esc_csv_cell, find_enl, lock_status, load_refs,
)


def pretty(canon: str) -> str:
    """'smith|ja' → 'Smith JA'。姓氏首字母大写，缩写全大写。"""
    if "|" in canon:
        sur, ini = canon.split("|", 1)
    else:
        sur, ini = canon, ""
    sur = sur.strip().capitalize()
    ini = "".join(ch for ch in ini if ch.isalpha()).upper()
    return f"{sur} {ini}".strip()


def main() -> int:
    ap = argparse.ArgumentParser(description="题录主题×作者矩阵")
    ap.add_argument("target", help="题录库目录或 .enl 文件路径")
    ap.add_argument("--topics", help="cluster_topics.py 产出的 topics.json")
    ap.add_argument("--out", default="./out")
    ap.add_argument("--workspace", default="./.lit_work")
    ap.add_argument("--top-authors", type=int, default=10,
                    help="每个主题列出的最多作者数")
    ap.add_argument("--top-core", type=int, default=20,
                    help="全局核心作者数")
    ap.add_argument("--matrix-authors", type=int, default=40,
                    help="矩阵行数（取全局出现最多的前 N 位作者）")
    args = ap.parse_args()

    try:
        target = Path(args.target).expanduser()
        is_norm = target.is_file() and target.suffix.lower() == ".json"
        enl = None if is_norm else find_enl(target)
        busy, _probe_ok, _probe_notice = (False, True, None) if is_norm else lock_status(enl)
        refs, src_meta = load_refs(target, args.workspace)
        total = len(refs)

        topics = None
        ref2cid: dict[int, int] = {}
        cid_meta: dict[int, dict] = {}
        if args.topics:
            tp = Path(args.topics).expanduser()
            if not tp.exists():
                print(f"[error] --topics 文件不存在: {tp}", file=sys.stderr)
                print(f"[hint] {EXIT[2]}", file=sys.stderr)
                return 2
            topics = json.loads(tp.read_text(encoding="utf-8"))
            for c in topics.get("clusters", []):
                cid = int(c["cluster_id"])
                cid_meta[cid] = c
                for rid in c.get("ref_ids", []):
                    ref2cid[int(rid)] = cid

        author_cluster: dict[str, Counter] = defaultdict(Counter)
        author_total: Counter = Counter()
        refs_with_authors = 0
        for r in refs:
            al = r.author_list
            if not al:
                continue
            refs_with_authors += 1
            cid = ref2cid.get(r.id)
            for a in al:
                author_total[a] += 1
                if cid is not None:
                    author_cluster[a][cid] += 1

        # ── 每个主题 top 作者 ──
        top_per_topic = []
        if topics is not None:
            for c in sorted(topics.get("clusters", []),
                            key=lambda x: -x.get("size", 0)):
                cid = int(c["cluster_id"])
                cand = [(a, author_cluster[a].get(cid, 0))
                        for a in author_total
                        if author_cluster[a].get(cid, 0) > 0]
                cand.sort(key=lambda x: (-x[1], x[0]))
                top_per_topic.append({
                    "cluster_id": cid,
                    "size": c.get("size"),
                    "pct": c.get("pct"),
                    "top_terms": c.get("top_terms", [])[:8],
                    "n_authors_in_topic": len(cand),
                    "top_authors": [
                        {"author": a, "name": pretty(a), "count": cnt}
                        for a, cnt in cand[: max(0, args.top_authors)]
                    ],
                })

        # ── 全局核心作者 ──
        core = author_total.most_common(args.top_core)
        global_core = [{"author": a, "name": pretty(a), "total": cnt}
                       for a, cnt in core]

        # ── 宽矩阵（行=前 N 核心作者，列=主题簇按规模降序）──
        matrix_rows = []
        col_cids = [int(c["cluster_id"]) for c in
                    sorted(topics.get("clusters", []),
                           key=lambda x: -x.get("size", 0))] if topics else []
        for a, _ in author_total.most_common(args.matrix_authors):
            row = {"author": a, "name": pretty(a), "total": author_total[a]}
            for cid in col_cids:
                row[str(cid)] = author_cluster[a].get(cid, 0)
            matrix_rows.append(row)

        counts = {
            "distinct_authors": len(author_total),
            "refs_with_authors": refs_with_authors,
            "refs_total": total,
            "author_coverage_pct": round(refs_with_authors / total * 100, 1)
            if total else 0.0,
            "topics_available": topics is not None,
            "topics_count": len(col_cids),
        }

        payload = {
            "ok": True, "exit_code": 0,
            "library": {"name": src_meta["display_path"],
            "display_path": "…/" + src_meta["display_path"],
            "source": src_meta["source_label"]},
            "mode": {
                "busy_detected": busy,
                "lock_probe_available": _probe_ok,
                "lock_probe_notice": _probe_notice,
                "lock_probe_available": _probe_ok,
                "lock_probe_notice": _probe_notice,
                "notice": ("检测到 EndNote 正在运行，数据可能不是最新。"
                           "建议关闭 EndNote 后重新扫描。") if busy else None,
            },
            "params": {
                "top_authors_per_topic": args.top_authors,
                "top_core_authors": args.top_core,
                "matrix_authors": args.matrix_authors,
                "author_canon": "surname|initials（同名靠缩写区分）",
                "note": ("未传 --topics 则仅输出全局核心作者，主题矩阵为空；"
                         "作者聚合基于本地 author 字段，未做跨库消歧。"),
            },
            "counts": counts,
            "top_per_topic": top_per_topic,
            "global_core_authors": global_core,
            "matrix": {"col_cluster_ids": col_cids, "rows": matrix_rows},
        }

        outdir = Path(args.out)
        outdir.mkdir(parents=True, exist_ok=True)
        (outdir / "author_topic.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

        # 长表 CSV
        with open(outdir / "author_topic.csv", "w", newline="",
                  encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["scope", "cluster_id", "rank", "author", "name",
                        "count", "topic_terms"])
            for i, a in enumerate(global_core, 1):
                w.writerow(["global_core", "", i, esc_csv_cell(a["author"]),
                            esc_csv_cell(a["name"]), a["total"], ""])
            for t in top_per_topic:
                for i, a in enumerate(t["top_authors"], 1):
                    w.writerow(["topic", t["cluster_id"], i, esc_csv_cell(a["author"]),
                                esc_csv_cell(a["name"]), a["count"],
                                esc_csv_cell(";".join(t["top_terms"][:6]))])

        # 宽矩阵 CSV
        with open(outdir / "matrix.csv", "w", newline="",
                  encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["author", "name", "total"] + [f"c{c}" for c in col_cids])
            # [!]  作者名/姓名来自外部导入（不可信输入），须与同文件的
            #    author_topic.csv 一样过 esc_csv_cell —— 此行漏网，
            #    导致同一份数据的长表已加固、宽表裸奔的不一致。
            for row in matrix_rows:
                w.writerow([esc_csv_cell(row["author"]), esc_csv_cell(row["name"]),
                            row["total"]] +
                           [row.get(str(c), 0) for c in col_cids])

        emit(payload)
        return 0

    except EnlError as e:
        print(f"[error] {e}", file=sys.stderr)
        print(f"[hint] {EXIT[e.code]}", file=sys.stderr)
        return e.code
    except Exception as e:  # noqa: BLE001
        print(f"[error] 未预期异常：{type(e).__name__}: {e}", file=sys.stderr)
        print(f"[hint] {EXIT[5]}", file=sys.stderr)
        return 5


if __name__ == "__main__":
    sys.exit(main())
