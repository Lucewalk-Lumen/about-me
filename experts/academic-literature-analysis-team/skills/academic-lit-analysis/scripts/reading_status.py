#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
reading_status.py —— 未读 / 待读清单

用法:
    python3 reading_status.py <库目录或.enl> [--workspace DIR]
                              [--csv 未读清单.csv] [--top N]

行为:
    - 读取题录库 read 字段（实测：'0'=未读/待读 5201 篇，'1'=已读 357 篇）
    - 统计 已读 / 未读 / 未知 分布
    - 列出待读文献（默认最近 N 篇，按年份降序；可用 --csv 全量导出）
    - 全程只读

注意: 题录库 read 字段取值约定——'1'=已读，其余（含 '0' 与空）按"未读/待读"处理。
      若用户库约定不同，请在报告中明示本约定，由用户确认。
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lit_core import (  # noqa: E402
    EnlError, EXIT, emit, esc_csv_cell, find_enl, lock_status,
    load_refs,
)


def main() -> int:
    ap = argparse.ArgumentParser(description="题录未读/待读清单")
    ap.add_argument("target", help="题录库目录或 .enl 文件路径")
    ap.add_argument("--workspace", default="./.lit_work")
    ap.add_argument("--csv", default=None, help="全量未读清单导出路径")
    ap.add_argument("--top", type=int, default=50, help="报告中列出的待读样本数")
    args = ap.parse_args()

    try:
        target = Path(args.target).expanduser()
        is_norm = target.is_file() and target.suffix.lower() == ".json"
        enl = None if is_norm else find_enl(target)
        busy, _probe_ok, _probe_notice = (False, True, None) if is_norm else lock_status(enl)
        refs, src_meta = load_refs(target, args.workspace)

        total = len(refs)
        rc = Counter(r.read_status for r in refs)
        read = rc.get("1", 0)
        unread = sum(v for k, v in rc.items() if k != "1")  # '0' 与空都算待读
        unknown = total - read - unread

        # 待读样本：按年份降序取前 N（年份缺失排末尾）
        unread_refs = [r for r in refs if r.read_status != "1"]
        unread_refs.sort(key=lambda r: (r.year is None, -(r.year or 0)))
        samples = [
            {"id": r.id, "title": r.title, "year": r.year,
             "journal": r.journal, "has_pdf": r.has_pdf, "doi": r.doi}
            for r in unread_refs[: max(0, args.top)]
        ]

        if args.csv:
            out = Path(args.csv)
            out.parent.mkdir(parents=True, exist_ok=True)
            with open(out, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f)
                w.writerow(["id", "title", "year", "journal", "has_pdf", "doi"])
                for r in unread_refs:
                    w.writerow([r.id, esc_csv_cell(r.title), r.year or "",
                                esc_csv_cell(r.journal),
                                "Y" if r.has_pdf else "N", esc_csv_cell(r.doi)])
            print(f"[ok] 已导出 {len(unread_refs)} 条待读 -> {out}", file=sys.stderr)

        payload = {
            "ok": True, "exit_code": 0,
            "library": {"name": src_meta["display_path"],
            "display_path": "…/" + src_meta["display_path"],
            "source": src_meta["source_label"]},
            "mode": {"busy_detected": busy,
                     "lock_probe_available": _probe_ok,
                     "lock_probe_notice": _probe_notice,
                     "notice": ("检测到 EndNote 正在运行，数据可能不是最新。"
                                "建议关闭 EndNote 后重新扫描。") if busy else None},
            "reading": {
                "total": total, "read": read, "unread": unread,
                "unknown": unknown,
                "pct_unread": round(unread / total * 100, 1) if total else 0.0,
                "convention": "read_status='1' 为已读；'0'/空 计为待读（按题录库默认约定）",
                "samples": samples,
            },
        }
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
