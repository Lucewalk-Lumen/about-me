#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dup_check.py —— 功能#2：重复 / 近似重复文献检测

用法:
    python3 dup_check.py <库目录或.enl> [--out DIR] [--workspace DIR]
                         [--near-threshold 0.85] [--csv 重复清单.csv]

检测口径（三重，互不替代）:
    1) 标题精确重复：归一化标题（lower + 去标点 + 压缩空白）完全相同 → 同一篇。
    2) DOI 精确碰撞：非空 DOI 被 ≥2 篇共享 → 强信号（即便标题写法不同）。
    3) 近似重复：同「期刊 + 年份」桶内，归一化标题 difflib 相似度 ≥ 阈值
       （默认 0.85）。用排序邻域（sliding-window）避免 O(n²) 爆炸。

全程只读。输出 dup.json（供报告集成）+ 可选 CSV。

[!]  本检测仅基于本地元数据（标题/DOI/期刊/年份），不依赖任何外部引文库。
   相似标题可能对应「同一会议的不同版本 / 预印本与正式版」，需用户人工确认合并。
"""
from __future__ import annotations

import argparse
import csv
import difflib
import json
import re
import sys
from collections import defaultdict

from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lit_core import (  # noqa: E402
    EnlError, EXIT, emit, esc_csv_cell, find_enl, lock_status, load_refs,
)

_CJK = re.compile(r"[一-鿿]")


def norm_title(t: str | None) -> str:
    """归一化标题：lower + 仅保留字母/数字/中日韩 + 压缩空白。

    去标点是为了让 'Work engagement.' 与 'work engagement' 不被误判为不同篇。
    """
    if not t:
        return ""
    s = (t or "").lower()
    s = re.sub(r"[^a-z0-9一-鿿]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def main() -> int:
    ap = argparse.ArgumentParser(description="题录重复/近似重复检测")
    ap.add_argument("target", help="题录库目录或 .enl 文件路径")
    ap.add_argument("--out", default="./out", help="输出目录（dup.json / dup.csv）")
    ap.add_argument("--workspace", default="./.lit_work")
    ap.add_argument("--near-threshold", type=float, default=0.85,
                    help="近似重复相似度阈值（0–1，默认 0.85）")
    ap.add_argument("--csv", default=None, help="重复清单 CSV 导出路径")
    ap.add_argument("--window", type=int, default=30,
                    help="同桶内排序邻域比较窗口（默认 30）")
    ap.add_argument("--max-bucket", type=int, default=400,
                    help="超过此规模的同期刊同年桶跳过近似比较（默认 400）")
    args = ap.parse_args()

    if not (0.5 <= args.near_threshold <= 1.0):
        print(f"[error] --near-threshold 需在 0.5~1.0，收到 {args.near_threshold}",
              file=sys.stderr)
        print(f"[hint] {EXIT[4]}", file=sys.stderr)
        return 4

    try:
        target = Path(args.target).expanduser()
        is_norm = target.is_file() and target.suffix.lower() == ".json"
        enl = None if is_norm else find_enl(target)
        busy, _probe_ok, _probe_notice = (False, True, None) if is_norm else lock_status(enl)
        refs, src_meta = load_refs(target, args.workspace)
        total = len(refs)

        # ── 1) 标题精确重复 ──
        by_title: dict[str, list] = defaultdict(list)
        for r in refs:
            k = norm_title(r.title)
            if k:
                by_title[k].append(r)
        exact_title_groups = [v for v in by_title.values() if len(v) >= 2]

        # ── 2) DOI 精确碰撞 ──
        by_doi: dict[str, list] = defaultdict(list)
        for r in refs:
            if r.doi:
                by_doi[r.doi].append(r)
        exact_doi_groups = [v for v in by_doi.values() if len(v) >= 2]

        # ── 3) 近似重复（同期刊同年，排序邻域 + difflib）──
        buckets: dict[tuple, list] = defaultdict(list)
        for r in refs:
            if r.year and r.journal:
                buckets[(r.journal, r.year)].append(r)

        # 并查集：仅用于把近似对聚成组
        parent: dict[int, int] = {}

        def find(x: int) -> int:
            parent.setdefault(x, x)
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a: int, b: int) -> None:
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb

        # 近似对先并查集
        skipped_large = 0
        near_pairs = 0
        for (j, y), items in buckets.items():
            if len(items) > args.max_bucket:
                skipped_large += 1
                continue
            items_sorted = sorted(items, key=lambda r: norm_title(r.title))
            n = len(items_sorted)
            for i in range(n):
                ni = norm_title(items_sorted[i].title)
                if not ni:
                    continue
                xi = items_sorted[i].id
                for jj in range(i + 1, min(i + 1 + args.window, n)):
                    nj = norm_title(items_sorted[jj].title)
                    if not nj or ni == nj:  # 已属标题精确重复，跳过
                        continue
                    ratio = difflib.SequenceMatcher(None, ni, nj).ratio()
                    if ratio >= args.near_threshold:
                        union(xi, items_sorted[jj].id)
                        near_pairs += 1

        # 收集近似组（排除已属标题精确 / DOI 精确的 id，避免重复计数）
        exact_ids = set()
        for g in exact_title_groups:
            exact_ids.update(r.id for r in g)
        for g in exact_doi_groups:
            exact_ids.update(r.id for r in g)

        near_groups_map: dict[int, list] = defaultdict(list)
        for r in refs:
            if r.id in exact_ids:
                continue
            rid = find(r.id)
            # 仅当该根下至少有 2 个非精确重复成员才算近似组
            near_groups_map[rid].append(r)
        near_groups = [v for v in near_groups_map.values() if len(v) >= 2]

        def _grp(typ: str, gid: int, members: list) -> dict:
            return {
                "type": typ,
                "group_id": gid,
                "size": len(members),
                "ids": [r.id for r in members],
                "sample_titles": [r.title for r in members[:5]],
                "years": sorted({r.year for r in members if r.year}),
            }

        groups = []
        gid = 0
        for g in exact_title_groups:
            groups.append(_grp("exact_title", gid, g)); gid += 1
        for g in exact_doi_groups:
            groups.append(_grp("exact_doi", gid, g)); gid += 1
        for g in near_groups:
            groups.append(_grp("near", gid, g)); gid += 1

        flagged_ids = set()
        for g in groups:
            flagged_ids.update(g["ids"])

        counts = {
            "exact_title_groups": len(exact_title_groups),
            "exact_title_refs": sum(len(g) for g in exact_title_groups),
            "exact_doi_groups": len(exact_doi_groups),
            "exact_doi_refs": sum(len(g) for g in exact_doi_groups),
            "near_groups": len(near_groups),
            "near_refs": sum(len(g) for g in near_groups),
            "total_flagged_refs": len(flagged_ids),
            "pct_flagged": round(len(flagged_ids) / total * 100, 1) if total else 0.0,
            "near_pairs_compared": near_pairs,
            "buckets_skipped_large": skipped_large,
        }

        warnings = []
        if counts["exact_title_refs"] > 0:
            warnings.append(
                f"发现 {counts['exact_title_refs']} 篇标题完全重复的文献"
                f"（{counts['exact_title_groups']} 组），建议人工确认后合并。")
        if counts["exact_doi_refs"] > 0:
            warnings.append(
                f"发现 {counts['exact_doi_refs']} 篇共享 DOI 的文献"
                f"（{counts['exact_doi_groups']} 组），高度疑似同一篇。")
        if counts["near_refs"] > 0:
            warnings.append(
                f"发现 {counts['near_refs']} 篇近似重复（同刊同年、标题相似度≥"
                f"{args.near_threshold}），需人工核对是否为版本/预印本差异。")
        if not warnings:
            warnings.append("未检测到重复或近似重复文献。")

        payload = {
            "ok": True, "exit_code": 0,
            "library": {"name": src_meta["display_path"],
            "display_path": "…/" + src_meta["display_path"],
            "source": src_meta["source_label"]},
            "mode": {
                "busy_detected": busy,
            "lock_probe_available": _probe_ok,
            "lock_probe_notice": _probe_notice,
                "notice": ("检测到 EndNote 正在运行，数据可能不是最新。"
                           "建议关闭 EndNote 后重新扫描。") if busy else None,
            },
            "params": {
                "norm": "lower + 去标点 + 压缩空白",
                "near_threshold": args.near_threshold,
                "window": args.window,
                "max_bucket": args.max_bucket,
                "note": "近似检测仅基于本地元数据，不依赖外部引文库；"
                        "合并前需人工确认。",
            },
            "total_refs": total,
            "counts": counts,
            "warnings": warnings,
            "groups": groups,
        }

        outdir = Path(args.out)
        outdir.mkdir(parents=True, exist_ok=True)
        (outdir / "dup.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

        if args.csv:
            out = Path(args.csv)
            out.parent.mkdir(parents=True, exist_ok=True)
            with open(out, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f)
                w.writerow(["type", "group_id", "id", "title", "year",
                            "journal", "doi"])
                for g in groups:
                    for r in refs:
                        if r.id in set(g["ids"]):
                            w.writerow([g["type"], g["group_id"], r.id,
                                        esc_csv_cell(r.title), r.year or "",
                                        esc_csv_cell(r.journal), esc_csv_cell(r.doi)])
            print(f"[ok] 已导出 {len(flagged_ids)} 条重复候选 -> {out}",
                  file=sys.stderr)

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
