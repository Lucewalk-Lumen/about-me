#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PDF 资料库摄取脚本：递归提取文件夹内全部 PDF，生成结构化笔记、清单与覆盖核对表。

用法:
    python ingest_pdfs.py <pdf_folder> [--out OUTPUT_DIR]
                           [--limit N] [--offset N]
                           [--incremental] [--manifest MANIFEST]

产出 (OUTPUT_DIR):
    texts/<name>.txt            每篇 PDF 的全文提取（不丢失，磁盘留存）
    notes/<name>.md             每篇 PDF 的结构化笔记（元数据 + 预览 + 待补摘要占位）
    00-MANIFEST.md              全部 PDF 清单（路径/页数/字数/状态）
    MANIFEST.json               机器可读清单（增量模式写入，含 size/mtime/key）
    00-COVERAGE-CHECKLIST.md    覆盖核对清单（逐条勾选，保证 0 遗漏）

退出码:
    0  成功（含"无 PDF"的正常退出）
    2  文件夹不存在 / 输入错误
    3  无可用 PDF 后端（pypdf / pdfplumber 均未安装）

设计说明:
    增量模式（--incremental）读取已有 MANIFEST（优先 MANIFEST.json，兼容 00-MANIFEST.md），
    按"相对路径 + 文件大小 + 修改时间"计算文件指纹，仅对新文件重新提取，旧条目保留。
"""


# 确保套件包可导入（包目录在上级目录）
import os, sys
_skill_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _skill_dir not in sys.path:
    sys.path.append(_skill_dir)
import argparse
import datetime
import glob
import json
import os
import re
import sys

# --out 输出路径强制 范围校验
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from obhrm_research_base.core.safe_path import resolve_safe_output  # noqa: E402

try:
    import pypdf
    BACKEND = "pypdf"
except Exception:  # noqa: BLE001
    pypdf = None
    try:
        import pdfplumber
        BACKEND = "pdfplumber"
    except Exception:  # noqa: BLE001
        pdfplumber = None
        BACKEND = None

PREVIEW_CHARS = 2000
MANIFEST_JSON = "MANIFEST.json"
MANIFEST_MD = "00-MANIFEST.md"
CHECKLIST_MD = "00-COVERAGE-CHECKLIST.md"

# 处理护栏：限制单个 PDF 的体积与页数，避免内存占用过高或处理卡死
# 复用 clean_pdf_text 已校准的阈值；超过任一上限的 PDF 在 extract_text() 内被拒绝
try:
    from clean_pdf_text import MAX_PDF_BYTES, MAX_PDF_PAGES, PDF_PROCESS_TIMEOUT, _pdf_process_timeout
    _HAS_GUARDS = True
except Exception:  # clean_pdf_text 缺失时降级为仅 MAX_PAGES 兜底
    MAX_PDF_BYTES = 200 * 1024 * 1024
    MAX_PDF_PAGES = 5000
    PDF_PROCESS_TIMEOUT = 120
    _pdf_process_timeout = None
    _HAS_GUARDS = False


# --------------------------------------------------------------------------- #
# 提取核心
# --------------------------------------------------------------------------- #
def extract_text(path):
    """返回 (text, pages) 或 (错误信息, 0)。

    执行前检查 MAX_PDF_BYTES / MAX_PDF_PAGES 双重护栏，
    SIGALRM 限时（仅 Unix 主线程）防卡死。失败/超限返回错误消息字符串。
    """
    # (1) 大小护栏：先于打开 PDF 之前检查文件大小
    try:
        size = os.path.getsize(path)
    except OSError as exc:
        return "[文件状态读取失败: %s]" % exc, 0
    if size > MAX_PDF_BYTES:
        return (
            f"[拒绝处理：PDF 文件过大（{size} 字节），超过上限 {MAX_PDF_BYTES} 字节，"
            f"可能为畸形文件或资源耗尽攻击。]", 0
        )

    # (2) SIGALRM 限时（仅在 Unix 主线程有效）
    if _pdf_process_timeout is not None:
        timeout_ctx = _pdf_process_timeout(PDF_PROCESS_TIMEOUT)
    else:
        from contextlib import nullcontext
        timeout_ctx = nullcontext()

    with timeout_ctx:
        if BACKEND == "pdfplumber":
            try:
                with pdfplumber.open(path) as pdf:
                    pages = len(pdf.pages)
                    if pages > MAX_PDF_PAGES:
                        return (
                            f"[拒绝处理：PDF 页数 {pages} 超过上限 {MAX_PDF_PAGES} 页，"
                            f"可能为畸形文件或资源耗尽攻击。]", 0
                        )
                    parts = [pg.extract_text() or "" for pg in pdf.pages]
                return "\n".join(parts), pages
            except Exception as exc:  # noqa: BLE001
                return "[提取失败: %s]" % exc, 0
        if BACKEND == "pypdf":
            try:
                reader = pypdf.PdfReader(path)
                pages = len(reader.pages)
                if pages > MAX_PDF_PAGES:
                    return (
                        f"[拒绝处理：PDF 页数 {pages} 超过上限 {MAX_PDF_PAGES} 页，"
                        f"可能为畸形文件或资源耗尽攻击。]", 0
                    )
                parts = [(reader.pages[i].extract_text() or "") for i in range(pages)]
                return "\n".join(parts), pages
            except Exception as exc:  # noqa: BLE001
                return "[提取失败: %s]" % exc, 0
        return "[无可用 PDF 库: 请 pip install pdfplumber]", 0


def count_cjk(text):
    """统计中日韩字符数。"""
    return sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")


# --------------------------------------------------------------------------- #
# 增量模式核心函数
# --------------------------------------------------------------------------- #
def compute_file_key(rel_path, size, mtime):
    """计算 PDF 的稳定指纹键，用于增量比对。

    Args:
        rel_path: 相对源文件夹的路径（str）。
        size: 文件字节大小（int）。
        mtime: 文件修改时间（float，秒）。

    Returns:
        str: 形如 ``<rel_path>|<size>|<mtime>`` 的指纹。
    """
    return "%s|%d|%.3f" % (rel_path, int(size or 0), float(mtime or 0.0))


def _parse_markdown_manifest(path):
    """兼容解析旧版 00-MANIFEST.md 表格，返回 {rel_path: entry}。"""
    entries = {}
    note_re = re.compile(r"notes/(.+?)\.md")
    try:
        with open(path, encoding="utf-8") as fh:
            lines = fh.readlines()
    except Exception:  # noqa: BLE001
        return entries
    for line in lines:
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 7:
            continue
        if cells[0] in ("#", "序号") or set(cells[0]) <= set("-"):
            continue  # 表头或分隔行
        rel_raw = cells[1].strip("`")
        rel_path = rel_raw
        try:
            pages = int(cells[2])
        except ValueError:
            pages = 0
        try:
            cjk = int(cells[3])
        except ValueError:
            cjk = 0
        try:
            total = int(cells[4])
        except ValueError:
            total = 0
        status = cells[5]
        safe = ""
        m = note_re.search(cells[6])
        if m:
            safe = m.group(1)
        entries[rel_path] = {
            "rel_path": rel_path,
            "size": 0,
            "mtime": 0.0,
            "name": safe[3:] if safe else rel_path,
            "pages": pages,
            "cjk": cjk,
            "total": total,
            "status": status,
            "safe": safe,
        }
    return entries


def load_existing_manifest(path):
    """读取已有 MANIFEST，返回 {rel_path: entry}。

    优先解析 JSON（MANIFEST.json，含 size/mtime/key），亦兼容 Markdown 格式
    （00-MANIFEST.md，仅含 rel_path 与统计字段）。

    Args:
        path: 清单文件路径；为 None 或不存在时返回空 dict。

    Returns:
        dict: 以 rel_path 为键的条目字典。
    """
    if not path or not os.path.isfile(path):
        return {}
    if path.endswith(".json"):
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception:  # noqa: BLE001
            return {}
        entries = {}
        for e in data.get("files", []):
            key = e.get("rel_path")
            if key:
                entries[key] = e
        return entries
    return _parse_markdown_manifest(path)


def _resolve_manifest(manifest_arg, out_dir):
    """解析增量模式使用的清单路径。"""
    if manifest_arg:
        return os.path.abspath(manifest_arg)
    for cand in (os.path.join(out_dir, MANIFEST_JSON),
                 os.path.join(out_dir, MANIFEST_MD)):
        if os.path.isfile(cand):
            return cand
    return None


def filter_incremental(records, existing):
    """比对已提取文件，拆分出新文件与需保留的旧条目。

    增量判定使用稳定指纹键 ``key``（rel_path + size + mtime）：
    仅当同一 rel_path 且 size 与 mtime 均未变化时，才视为已提取、可保留；
    若文件被替换（大小或修改时间任一变化），则归入待处理、触发重提。

    Args:
        records: 当前扫描到的 PDF 记录列表（每项含 rel_path / size /
            mtime / key）。
        existing: load_existing_manifest 返回的 {rel_path: entry}（entry
            含 key 字段）。

    Returns:
        Tuple[List, List]: (待处理的新记录列表, 需保留的旧条目列表)。
    """
    to_process = []
    preserved = []
    for rec in records:
        prev = existing.get(rec["rel_path"])
        if prev is not None and prev.get("key") == rec.get("key"):
            preserved.append(prev)
        else:
            to_process.append(rec)
    return to_process, preserved


# --------------------------------------------------------------------------- #
# 输出构建
# --------------------------------------------------------------------------- #
def _row_from_extraction(idx, rec, text, pages):
    """从一次新提取结果构造统一的行字典。"""
    cjk = count_cjk(text)
    total = len(text)
    status = "OK" if (pages > 0 and not text.startswith("[")) else "需人工核对"
    safe = "%02d-%s" % (idx, rec["name"])
    return {
        "idx": idx,
        "rel_path": rec["rel_path"],
        "size": rec["size"],
        "mtime": rec["mtime"],
        "key": rec["key"],
        "name": rec["name"],
        "pages": pages,
        "cjk": cjk,
        "total": total,
        "status": status,
        "safe": safe,
    }


def _normalize_preserved(entry, idx):
    """将保留的旧条目规范为统一的行字典。"""
    return {
        "idx": idx,
        "rel_path": entry.get("rel_path", ""),
        "size": int(entry.get("size", 0) or 0),
        "mtime": float(entry.get("mtime", 0.0) or 0.0),
        "key": entry.get("key", entry.get("rel_path", "")),
        "name": entry.get("name", entry.get("safe", "")[3:]),
        "pages": int(entry.get("pages", 0) or 0),
        "cjk": int(entry.get("cjk", 0) or 0),
        "total": int(entry.get("total", 0) or 0),
        "status": entry.get("status", "需人工核对"),
        "safe": entry.get("safe", ""),
    }


def _write_manifest_md(out_dir, folder, rows):
    """写 00-MANIFEST.md（兼容人类可读清单）。"""
    path = os.path.join(out_dir, MANIFEST_MD)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("# PDF 资料库清单 (MANIFEST)\n\n")
        fh.write("- 生成时间: %s\n" % datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
        fh.write("- 源文件夹: `%s`\n" % folder)
        fh.write("- PDF 总数: %d\n" % len(rows))
        fh.write("- 提取后端: %s\n\n" % BACKEND)
        fh.write("| # | 相对路径 | 页数 | CJK字数 | 总字符 | 状态 | 笔记 |\n")
        fh.write("|---|----------|------|---------|--------|------|------|\n")
        for r in rows:
            fh.write("| %d | `%s` | %d | %d | %d | %s | [笔记](notes/%s.md) |\n"
                     % (r["idx"], r["rel_path"], r["pages"], r["cjk"],
                        r["total"], r["status"], r["safe"]))


def _write_manifest_json(out_dir, folder, incremental, rows):
    """写 MANIFEST.json（机器可读，增量模式）。"""
    path = os.path.join(out_dir, MANIFEST_JSON)
    data = {
        "version": "1.0",
        "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "source_folder": folder,
        "backend": BACKEND,
        "incremental": bool(incremental),
        "files": [
            {
                "rel_path": r["rel_path"],
                "key": r.get("key", r["rel_path"]),
                "size": r.get("size", 0),
                "mtime": r.get("mtime", 0.0),
                "name": r["name"],
                "pages": r["pages"],
                "cjk": r["cjk"],
                "total": r["total"],
                "status": r["status"],
                "safe": r["safe"],
            }
            for r in rows
        ],
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


def _write_checklist(out_dir, rows):
    """写 00-COVERAGE-CHECKLIST.md（覆盖核对清单）。"""
    path = os.path.join(out_dir, CHECKLIST_MD)
    ok = sum(1 for r in rows if r["status"] == "OK")
    need = len(rows) - ok
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("# 覆盖核对清单（全量总结 · 不丢失）\n\n")
        fh.write("> 目标：确保源文件夹内每一篇 PDF 都被提取并总结，0 遗漏。逐项勾选。\n\n")
        fh.write("总计 %d 篇。已成功提取 %d 篇，需人工核对 %d 篇。\n\n"
                 % (len(rows), ok, need))
        fh.write("| # | 文件名 | 相对路径 | 处理状态 |\n")
        fh.write("|---|--------|----------|----------|\n")
        for r in rows:
            fh.write("| %d | %s | `%s` |  已提取   已总结   已挂载框架 |\n"
                     % (r["idx"], r["safe"][3:], r["rel_path"]))


# --------------------------------------------------------------------------- #
# 主流程
# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser(description="递归摄取文件夹内全部 PDF（支持增量模式）")
    ap.add_argument("folder", help="含 PDF 的源文件夹（递归扫描子文件夹）")
    ap.add_argument("--out", default=None, help="输出目录，默认 <folder>/_ingest")
    ap.add_argument("--limit", type=int, default=0,
                    help="最多处理 N 篇（0=全部），用于大资料库分块提取")
    ap.add_argument("--offset", type=int, default=0, help="跳过前 N 篇")
    ap.add_argument("--incremental", action="store_true",
                    help="增量模式：比对已有 MANIFEST，仅处理新文件，旧条目保留")
    ap.add_argument("--manifest", default=None,
                    help="指定已有清单路径（默认优先 <out>/MANIFEST.json，其次 00-MANIFEST.md）")
    args = ap.parse_args()

    folder = os.path.abspath(args.folder)
    if not os.path.isdir(folder):
        print("错误: 文件夹不存在: %s" % folder, file=sys.stderr)
        sys.exit(2)
    if BACKEND is None:
        print("错误: 无可用 PDF 后端（pypdf / pdfplumber 均未安装）", file=sys.stderr)
        sys.exit(1)

    if args.out:
        # 仅对用户显式提供的 --out 做范围校验（防越界逃逸）；默认输出目录落在源文件夹
        # 内，属受信任的内部默认值，不应以 cwd 为基判定越界——否则源文件夹在 cwd 外时
        # 默认行为必失败。
        out = os.path.abspath(args.out)
        try:
            out = str(resolve_safe_output(out, base=os.getcwd()))
        except ValueError as exc:
            print("错误(--out): %s" % exc, file=sys.stderr)
            sys.exit(2)
    else:
        out = os.path.join(folder, "_ingest")
    texts_dir = os.path.join(out, "texts")
    notes_dir = os.path.join(out, "notes")
    os.makedirs(texts_dir, exist_ok=True)
    os.makedirs(notes_dir, exist_ok=True)

    pdfs = sorted(glob.glob(os.path.join(folder, "**", "*.pdf"), recursive=True))
    pdfs = [p for p in pdfs if "/__MACOSX/" not in p]
    if args.offset:
        pdfs = pdfs[args.offset:]
    if args.limit:
        pdfs = pdfs[:args.limit]
    if not pdfs:
        print("未找到任何 PDF")
        sys.exit(0)

    # 构建当前记录
    records = []
    for path in pdfs:
        rel = os.path.relpath(path, folder)
        size = os.path.getsize(path)
        mtime = os.path.getmtime(path)
        name = os.path.splitext(os.path.basename(path))[0]
        records.append({
            "path": path,
            "rel_path": rel,
            "size": size,
            "mtime": mtime,
            "key": compute_file_key(rel, size, mtime),
            "name": name,
        })

    preserved = []
    if args.incremental:
        manifest_path = _resolve_manifest(args.manifest, out)
        existing = load_existing_manifest(manifest_path)
        to_process, preserved = filter_incremental(records, existing)
        print("增量模式：已有 %d 篇跳过，待处理 %d 篇" % (len(preserved), len(to_process)))
    else:
        to_process = records

    print("后端: %s | 发现 %d 个 PDF（本次提取 %d 篇）"
          % (BACKEND, len(records), len(to_process)))

    new_rows = []
    for rec in to_process:
        text, pages = extract_text(rec["path"])
        safe = "%02d-%s" % (len(preserved) + len(new_rows) + 1, rec["name"])

        tpath = os.path.join(texts_dir, safe + ".txt")
        try:
            with open(tpath, "w", encoding="utf-8") as fh:
                fh.write(text)
        except OSError as e:
            print("[!] 写出失败，跳过 %s: %s" % (tpath, e))
            continue

        preview = text[:PREVIEW_CHARS].replace("\n", " ")
        npath = os.path.join(notes_dir, safe + ".md")
        try:
            with open(npath, "w", encoding="utf-8") as fh:
                fh.write("# %s\n\n" % rec["name"])
                fh.write("- 源路径: `%s`\n" % rec["rel_path"])
                fh.write("- 页数: %d\n" % pages)
                fh.write("- 字数(含CJK): %d / 总字符: %d\n" % (count_cjk(text), len(text)))
                fh.write("- 全文: `texts/%s.txt`\n\n" % safe)
                fh.write("## 结构化笔记（待 AI/研究者补全）\n")
                fh.write("- 研究问题:\n- 研究方法:\n- 核心结论:\n")
                fh.write("- 与本主题的关联:\n- 可用于综述的哪一部分:\n\n")
                fh.write("## 原文预览（前 %d 字）\n\n%s\n" % (PREVIEW_CHARS, preview))
        except OSError as e:
            print("[!] 写出失败，跳过 %s: %s" % (npath, e))
            continue

        new_rows.append(_row_from_extraction(
            len(preserved) + len(new_rows) + 1, rec, text, pages))

    # 合并：旧条目保留 + 新条目
    merged = [_normalize_preserved(e, i + 1) for i, e in enumerate(preserved)]
    merged.extend(new_rows)

    _write_manifest_md(out, folder, merged)
    if args.incremental:
        _write_manifest_json(out, folder, True, merged)
    _write_checklist(out, merged)

    print("完成。输出目录: %s" % out)
    print("清单: %s" % os.path.join(out, MANIFEST_MD))
    if args.incremental:
        print("机器清单: %s" % os.path.join(out, MANIFEST_JSON))
    print("核对表: %s" % os.path.join(out, CHECKLIST_MD))


if __name__ == "__main__":
    main()
