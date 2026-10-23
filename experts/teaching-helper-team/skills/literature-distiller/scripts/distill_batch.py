#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""论文速览 · 批量提取编排（literature-distiller）—— 跨平台实现。

职责边界（先读这一段）：
  本脚本只做蒸馏流程中**确定性的那一段**——把 PDF 批量转成结构化全文。
  蒸馏报告本身（M1 元数据 / M2 逻辑骨架 / M3-M5 深度分析）由 AI 按
  skills/literature-distiller/SKILL.md 的工作流生成。
  本脚本不生成报告，也不会输出任何「已完成蒸馏」的字样。

用法：
  python distill_batch.py [选项]
    --input  <dir>   输入目录（默认 <skill>/assets/）
    --output <dir>   输出目录（默认 <skill>/distilled_papers/）
    --single <file>  只处理单个 PDF
    --mode   <mode>  提取模式：text（默认）或 technical（含表格/代码块）
    --dry-run        只列出待处理清单与将要执行的命令，不实际提取
    -h, --help       显示本帮助

解释器：
  提取器需要解析依赖，统一由 setup 托管的 venv 提供。用环境变量 VENV_PY 指定：
      Windows:  set VENV_PY=C:\\path\\to\\venv\\Scripts\\python.exe
      POSIX :   export VENV_PY="$(cat ~/.workbuddy/teaching-helper-team/venv_python.txt)"
  未设置时回退到当前解释器，并在输出中显式提示（不会静默替换）。

退出码：0 = 全部成功；2 = 存在失败项；3 = 参数或环境错误

实现注记（为什么改用 Python）：
  旧版为 POSIX shell 实现，依赖 find / grep / wc / bc 等外部命令，Windows 原生
  环境不可用；若要覆盖 Windows 就需再维护一份 PowerShell 实现，两套必然漂移。
  提取器本身即 Python 组件，故批量编排一并由 Python 承载：单一实现全平台可用，
  同目录的 distill_batch.sh 仅作 POSIX 便捷入口，内部转发到本文件。
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
PKG_ROOT = SKILL_DIR.parent.parent
EXTRACTOR = PKG_ROOT / "skills" / "material-extractor" / "scripts" / "extract_entry.py"

PDF_MAGIC = b"%PDF"
VALID_MODES = ("text", "technical")


def _force_utf8() -> None:
    """Windows 控制台默认非 UTF-8；脚本输出含中文与 em dash，强制 UTF-8 避免
    在重定向到文件或管道时抛 UnicodeEncodeError。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        except (AttributeError, ValueError):
            pass


def human_size(n: int) -> str:
    if n >= 1048576:
        return f"{n / 1048576:.1f} MB"
    if n >= 1024:
        return f"{n // 1024} KB"
    return f"{n} B"


def slugify(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", name) or "paper"


def looks_like_pdf(p: Path) -> bool:
    """前 5 字节是否以 %PDF 开头（与原 shell 版的 `head -c 5 | grep -q '%PDF'` 同义）。

    注意必须用 startswith：读 5 字节却与 4 字节的 PDF_MAGIC 做 **全等** 比较会恒为假，
    导致所有正常 PDF 都被误判为损坏文件而跳过。
    """
    try:
        with p.open("rb") as fh:
            return fh.read(5).startswith(PDF_MAGIC)
    except OSError:
        return False


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="distill_batch.py",
        add_help=False,
        description="论文速览 · 批量提取编排（只做批量提取，不生成蒸馏报告）",
    )
    ap.add_argument("--input", default=str(SKILL_DIR / "assets"),
                    help="输入目录（默认 <skill>/assets/）")
    ap.add_argument("--output", default=str(SKILL_DIR / "distilled_papers"),
                    help="输出目录（默认 <skill>/distilled_papers/）")
    ap.add_argument("--single", default="", help="只处理单个 PDF")
    ap.add_argument("--mode", default="text", help="提取模式：text（默认）或 technical")
    ap.add_argument("--dry-run", action="store_true", help="只列清单，不实际提取")
    ap.add_argument("-h", "--help", action="store_true", help="显示本帮助")
    return ap


def main(argv=None) -> int:
    _force_utf8()
    ap = build_parser()
    try:
        ns = ap.parse_args(argv)
    except SystemExit:
        # argparse 对未知参数 / 缺值 / 非法 choices 一律 exit(2)；
        # 本脚本约定「参数或环境错误」为 3，故统一转码。
        return 3

    if ns.help:
        ap.print_help()
        return 0

    if ns.mode not in VALID_MODES:
        print(f"[错误] --mode 只接受 text 或 technical，收到：{ns.mode}", file=sys.stderr)
        return 3

    input_dir = Path(ns.input)
    output_dir = Path(ns.output)

    venv_py = os.environ.get("VENV_PY", "").strip()
    if not venv_py:
        venv_py = sys.executable or "python3"
        print(f"[提示] 未设置环境变量 VENV_PY，回退使用 {venv_py}；解析依赖可能不全。")

    # ---- 待处理清单 ----
    if ns.single:
        cand = Path(ns.single)
        if not cand.is_file():
            cand = input_dir / ns.single
        if not cand.is_file():
            print(f"[错误] 文件不存在：{ns.single}", file=sys.stderr)
            return 3
        files = [cand]
    else:
        if not input_dir.is_dir():
            print(f"[错误] 输入目录不存在：{input_dir}", file=sys.stderr)
            print("       请把待处理的 PDF 放入该目录后重试（或先用 --input 指定目录）。",
                  file=sys.stderr)
            return 3
        files = sorted(p for p in input_dir.rglob("*.pdf") if p.is_file())

    total = len(files)
    if total == 0:
        print(f"[提示] 未找到任何 .pdf 文件。输入目录：{input_dir}")
        print("       请放入 PDF 后重试。")
        return 0

    if not EXTRACTOR.is_file():
        print(f"[错误] 未找到提取器：{EXTRACTOR}", file=sys.stderr)
        print("       本脚本依赖包内的 material-extractor 技能。", file=sys.stderr)
        return 3

    # ---- 输出头 ----
    print("论文速览 · 批量提取（literature-distiller）")
    print("-" * 40)
    print(f" 输入目录 : {input_dir}")
    print(f" 输出目录 : {output_dir}")
    print(f" 提取器   : {EXTRACTOR}")
    print(f" 解释器   : {venv_py}")
    print(f" 提取模式 : {ns.mode}")
    print(f" 待处理   : {total} 个 PDF")
    if ns.dry_run:
        print(" 运行方式 : 试运行（不实际提取）")
    print("-" * 40)
    print()

    manifest = output_dir / f"extract_manifest_{time.strftime('%Y%m%d')}.tsv"
    if not ns.dry_run:
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            print(f"[错误] 无法创建输出目录：{output_dir}（{exc}）", file=sys.stderr)
            return 3
        manifest.write_text("index\tfile\tbytes\tstatus\ttext_path\tlog_path\n",
                            encoding="utf-8")

    ok = skipped = failed = 0
    for idx, pdf in enumerate(files, 1):
        name = pdf.name
        try:
            size_b = pdf.stat().st_size
        except OSError:
            size_b = 0
        print(f"[{idx}/{total}] {name}  ({human_size(size_b)})")

        if not looks_like_pdf(pdf):
            print("         跳过：开头 5 字节不含 %PDF，文件可能损坏或并非 PDF")
            skipped += 1
            if not ns.dry_run:
                with manifest.open("a", encoding="utf-8") as fh:
                    fh.write(f"{idx}\t{name}\t{size_b}\tskipped_not_pdf\t-\t-\n")
            print()
            continue

        slug = slugify(pdf.stem)
        outdir = output_dir / slug

        if ns.dry_run:
            print(f"         将执行：BOOK_SKILL_WORKDIR=\"{outdir}\" "
                  f"{venv_py} {EXTRACTOR} \"{pdf}\" --mode {ns.mode}")
            print()
            continue

        log = outdir / "extract.log"
        try:
            outdir.mkdir(parents=True, exist_ok=True)
            env = dict(os.environ, BOOK_SKILL_WORKDIR=str(outdir))
            with log.open("w", encoding="utf-8", errors="replace") as fh:
                proc = subprocess.run(
                    [venv_py, str(EXTRACTOR), str(pdf), "--mode", ns.mode],
                    stdout=fh, stderr=subprocess.STDOUT, env=env,
                    check=False, timeout=1800,
                )
            rc = proc.returncode
        except subprocess.TimeoutExpired:
            print(f"         失败：提取器超时（>1800s），已跳过：{pdf}", file=sys.stderr)
            rc = 124
        except OSError as exc:
            print(f"         失败：无法启动提取器（{exc}）", file=sys.stderr)
            rc = 127

        if rc == 0:
            found = sorted(outdir.rglob("full_text.txt"))
            if found:
                print(f"         完成：{found[0]}")
                ok += 1
                with manifest.open("a", encoding="utf-8") as fh:
                    fh.write(f"{idx}\t{name}\t{size_b}\tok\t{found[0]}\t{log}\n")
            else:
                print(f"         失败：提取器返回 0，但未产出 full_text.txt（详见 {log}）")
                failed += 1
                with manifest.open("a", encoding="utf-8") as fh:
                    fh.write(f"{idx}\t{name}\t{size_b}\tno_output\t-\t{log}\n")
        else:
            print(f"         失败：提取器返回 {rc}（详见 {log}）")
            failed += 1
            with manifest.open("a", encoding="utf-8") as fh:
                fh.write(f"{idx}\t{name}\t{size_b}\terror_rc_{rc}\t-\t{log}\n")
        print()

    print("-" * 40)
    print(f" 提取完成：成功 {ok} / 跳过 {skipped} / 失败 {failed}（共 {total}）")
    if not ns.dry_run:
        print(f" 提取清单：{manifest}")
    print()
    print("下一步（本脚本不代劳）：按 skills/literature-distiller/SKILL.md 的工作流，")
    print("对每个 full_text.txt 生成蒸馏报告（M1 元数据 / M2 逻辑骨架 / M3-M5 深度分析）；")
    print("成稿前须运行 python skills/deai-rules/scripts/deai_preflight.py <成稿路径> 并 PASS。")

    return 2 if failed > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
