#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scan_library.py —— M1: 扫描 EndNote 库并输出数据质量体检报告

用法:
    python3 scan_library.py <EndNote库目录或.enl路径> [--workspace DIR] [--no-shadow]

行为:
    - 自动探测 .enl（用户可直接拖入文件夹）
    - 识别文本格式并给出明确指引（退出码 2）
    - EndNote 持锁时自动降级为影子副本，并在输出中标注 busy 状态
    - stdout 只输出 JSON；所有提示走 stderr
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from endnote_core import (  # noqa: E402
    EnlError, EXIT, coverage_report, emit, find_enl, lib_digest,
    load_refs, lock_probe_available, lock_status, make_shadow, open_enl_readonly, parse_refs,
)

SQLITE_MAGIC = b"SQLite format 3"


def probe_format(path: Path) -> str:
    """用魔数判定，不能靠扩展名。"""
    with open(path, "rb") as f:
        magic = f.read(16)
    if magic.startswith(SQLITE_MAGIC):
        return "sqlite"
    return "text"


def scan_normalized(p: Path) -> int:
    """refs.json 通路：多来源归一化产物的体检。

    坑：v0.3.0 文档承诺"下游 6 个模块透明接受 .enl 或 refs.json"，但本脚本
    仍走find_enl + 魔数判定 → 传 refs.json 会被当成"文本格式 .enl"报错退出 2，
    体检环节直接断链，非 EndNote 用户无法完成 M1。此处补齐归一化通路。
    """
    refs, meta = load_refs(p)
    rep = coverage_report(refs)
    emit({
        "ok": True,
        "exit_code": 0,
        "library": {
            "name": p.name,
            "display_path": "…/" + p.name,
            "size_bytes": p.stat().st_size,
            "format": "refs_json",
            "source": meta["source"],
            "source_label": meta["source_label"],
            "digest_blake2b": "",
        },
        "mode": {
            "shadow_copy": False,
            "endnote_busy_detected": False,
            "notice": None,
        },
        "coverage": rep,
    })
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="扫描文献库并输出体检报告")
    ap.add_argument("target", help="文献库目录 / .enl 路径 / refs.json")
    ap.add_argument("--workspace", default="./.endnote_work",
                    help="影子副本与派生文件工作目录")
    ap.add_argument("--no-shadow", action="store_true",
                    help="强制直连源库（不推荐）")
    args = ap.parse_args()

    try:
        target = Path(args.target).expanduser()
        # 归一化产物通路：与下游其余模块保持一致的入口约定
        if target.is_file() and target.suffix.lower() == ".json":
            return scan_normalized(target)
        enl = find_enl(target)
        fmt = probe_format(enl)

        if fmt != "sqlite":
            print(
                f"[error] 检测到文本格式 .enl（{enl.name}）。\n"
                "MVP 仅支持 EndNote 20+ 的 SQLite 格式。\n"
                "请在 EndNote 中将库另存/升级为新格式后重试。",
                file=sys.stderr,
            )
            print(f"[hint] {EXIT[2]}", file=sys.stderr)
            return 2

        # 影子副本：实测 EndNote 持锁时直连报 database is locked
        busy, _probe_ok, _probe_notice = lock_status(enl)
        probe_ok = lock_probe_available(enl)
        used_shadow = False
        opened = enl
        if busy and not args.no_shadow:
            opened = make_shadow(enl, args.workspace)
            used_shadow = True
            print("[info] 检测到 EndNote 可能正在运行，已切换影子副本模式", file=sys.stderr)
        elif not args.no_shadow:
            opened = make_shadow(enl, args.workspace)
            used_shadow = True

        con = open_enl_readonly(opened, immutable=used_shadow)
        data_dir = enl.parent / (enl.stem + ".Data")
        refs = parse_refs(con, data_dir if data_dir.exists() else None)
        rep = coverage_report(refs)
        con.close()

        out = {
            "ok": True,
            "exit_code": 0,
            "library": {
                "name": enl.name,
                # 路径脱敏：只回传文件名，完整路径不外泄
                "display_path": "…/" + enl.name,
                "size_bytes": enl.stat().st_size,
                "format": "sqlite",
                "digest_blake2b": lib_digest(enl),
            },
            "mode": {
                "shadow_copy": used_shadow,
                "endnote_busy_detected": busy,
                # 降级+红警策略：busy 时继续分析但必须显式标注
                "notice": ("检测到 EndNote 正在运行，数据可能不是最新。"
                           "建议关闭 EndNote 后重新扫描。") if busy else None,
                # 占用探测能力本身是否可用（跨平台）。
                # 不可用时必须说"探测不可用"，不能默认"未占用"——
                # 那是把"不知道"说成"没有"，属事实性错误。
                "lock_probe_available": probe_ok,
                "lock_probe_notice": None if probe_ok else
                    ("当前平台缺少持锁探测工具（lsof/fuser/pgrep/tasklist），"
                     "无法判断 EndNote 是否持锁。数据可能不是最新。"),
            },
            "coverage": rep,
        }
        emit(out)
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
