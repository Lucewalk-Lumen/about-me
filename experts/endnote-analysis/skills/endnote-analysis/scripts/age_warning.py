#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
age_warning.py —— 功能#4：文献时效性（陈旧度）预警

用法:
    python3 age_warning.py <库目录或.enl> [--out DIR] [--workspace DIR]
                           [--top 30] [--csv 最旧清单.csv]

指标:
    - 年份分布（直方图）
    - 相对库内最新年的「近三年」占比（前沿性）
    - 早于 2019 年文献占比（陈旧度）
    - 缺失年份文献占比（数据质量）
    - 最旧 N 篇清单

⚠️ 时效性以【库内最新年份】为基准（而非系统时钟）—— 避免把一份
   2015 年封存的库误判为「全部陈旧」。
全程只读。输出 age.json + 可选 CSV。
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from endnote_core import (  # noqa: E402
    EnlError, EXIT, emit, esc_csv_cell, find_enl, lock_status, load_refs,
    make_shadow, open_enl_readonly, parse_refs,
)

RECENT_WINDOW = 3          # 近三年窗口
OLD_CUTOFF = 2019          # 陈旧分界年
LOW_RECENT_PCT = 25.0      # 近三年占比低于此值 → 前沿性预警
HIGH_OLD_PCT = 40.0        # 早于分界年占比高于此值 → 陈旧预警
HIGH_MISSING_PCT = 10.0    # 缺失年份占比高于此值 → 数据质量预警


def main() -> int:
    ap = argparse.ArgumentParser(description="EndNote 文献时效性预警")
    ap.add_argument("target", help="EndNote 库目录或 .enl 文件路径")
    ap.add_argument("--out", default="./out")
    ap.add_argument("--workspace", default="./.endnote_work")
    ap.add_argument("--top", type=int, default=30, help="最旧清单样本数")
    ap.add_argument("--csv", default=None, help="最旧文献 CSV 导出路径")
    ap.add_argument("--old-cutoff", type=int, default=OLD_CUTOFF,
                    help="陈旧分界年（默认 2019）")
    args = ap.parse_args()

    try:
        target = Path(args.target).expanduser()
        is_norm = target.is_file() and target.suffix.lower() == ".json"
        enl = None if is_norm else find_enl(target)
        busy, _probe_ok, _probe_notice = (False, True, None) if is_norm else lock_status(enl)
        refs, src_meta = load_refs(target, args.workspace)
        total = len(refs)

        years = [r.year for r in refs if r.year]
        n_with_year = len(years)
        n_missing = total - n_with_year
        if not years:
            print("[error] 库中无任何可用年份，无法做时效性分析", file=sys.stderr)
            print(f"[hint] {EXIT[5]}", file=sys.stderr)
            return 5

        max_year = max(years)
        min_year = min(years)
        hist = Counter(years)
        year_hist = {str(y): hist[y] for y in sorted(hist)}

        last_n = [y for y in years if y >= max_year - (RECENT_WINDOW - 1)]
        recent = len(last_n)
        recent_pct = round(recent / n_with_year * 100, 1)

        old = [y for y in years if y < args.old_cutoff]
        old_pct = round(len(old) / n_with_year * 100, 1)

        missing_pct = round(n_missing / total * 100, 1)

        # 中位数 / 均值
        sy = sorted(years)
        mid = sy[len(sy) // 2]
        mean_year = round(sum(sy) / len(sy), 1)

        oldest = sorted((r for r in refs if r.year), key=lambda r: r.year)[: max(0, args.top)]
        oldest_samples = [
            {"id": r.id, "title": r.title, "year": r.year,
             "journal": r.journal, "has_pdf": r.has_pdf}
            for r in oldest
        ]

        warnings = []
        if recent_pct < LOW_RECENT_PCT:
            warnings.append(
                f"近三年（{max_year - RECENT_WINDOW + 1}–{max_year}）文献仅占 "
                f"{recent_pct}%，综述前沿性可能不足，建议补充最新进展。")
        if old_pct > HIGH_OLD_PCT:
            warnings.append(
                f"{old_pct}% 的文献早于 {args.old_cutoff} 年，库可能偏陈旧，"
                f"建议补充近五年文献以更新综述基础。")
        if missing_pct > HIGH_MISSING_PCT:
            warnings.append(
                f"{missing_pct}% 的文献缺失年份（{n_missing} 篇），"
                f"时效性判断与年份分布可能失真。")
        if not warnings:
            warnings.append("文献时效性未见明显风险。")

        payload = {
            "ok": True, "exit_code": 0,
            "library": {"name": src_meta["display_path"],
            "display_path": "…/" + src_meta["display_path"],
            "source": src_meta["source_label"]},
            "mode": {
                "endnote_busy_detected": busy,
            "lock_probe_available": _probe_ok,
            "lock_probe_notice": _probe_notice,
                "notice": ("检测到 EndNote 正在运行，数据可能不是最新。"
                           "建议关闭 EndNote 后重新扫描。") if busy else None,
            },
            "params": {
                "reference_year": max_year,
                "recent_window": RECENT_WINDOW,
                "old_cutoff": args.old_cutoff,
                "thresholds": {
                    "low_recent_pct": LOW_RECENT_PCT,
                    "high_old_pct": HIGH_OLD_PCT,
                    "high_missing_pct": HIGH_MISSING_PCT,
                },
                "note": "时效性以库内最新年份为基准，而非系统时钟。",
            },
            "total_refs": total,
            "year_stats": {
                "min_year": min_year, "max_year": max_year,
                "median_year": mid, "mean_year": mean_year,
                "with_year": n_with_year, "missing_year": n_missing,
                "missing_pct": missing_pct,
            },
            "recency": {
                "recent_window_years": [max_year - RECENT_WINDOW + 1, max_year],
                "recent_count": recent, "recent_pct": recent_pct,
            },
            "staleness": {
                "old_cutoff": args.old_cutoff,
                "old_count": len(old), "old_pct": old_pct,
            },
            "year_histogram": year_hist,
            "warnings": warnings,
            "oldest_samples": oldest_samples,
        }

        outdir = Path(args.out)
        outdir.mkdir(parents=True, exist_ok=True)
        (outdir / "age.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

        if args.csv:
            out = Path(args.csv)
            out.parent.mkdir(parents=True, exist_ok=True)
            with open(out, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f)
                w.writerow(["id", "title", "year", "journal", "has_pdf"])
                for r in oldest:
                    w.writerow([r.id, esc_csv_cell(r.title), r.year or "",
                                esc_csv_cell(r.journal),
                                "Y" if r.has_pdf else "N"])
            print(f"[ok] 已导出最旧 {len(oldest)} 篇 -> {out}", file=sys.stderr)

        # 年份直方图 CSV
        with open(outdir / "year_hist.csv", "w", newline="",
                  encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["year", "count"])
            for y in sorted(hist):
                w.writerow([y, hist[y]])

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
