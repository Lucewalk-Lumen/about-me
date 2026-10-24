#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_readings.py — 由 ingest 产物（notes/ + texts/）构建「已读文献」索引 READINGS.md。

全文路径一律以 .txt 基名解析（笔记为 .md、全文为 .txt，二者基名对应）；
全文缺失时显式标记，不做静默回退。

产出 READINGS.md 含两块：
  ## 文献条目（供闭环引证核验）
      每行一条 `Author (Year). Title.`（与 closed_loop_check.py --readings 兼容）
  ## 摘要（自动抽取，待校正）
      每篇 `### Title` + 抽取摘要 + 来源/全文路径 + 缺失标记

用法：
  python build_readings.py <ingest_dir> [--out READINGS.md] [--abstract-chars N]
  ingest_dir 需含 notes/ 与 texts/ 两个子目录。
"""
# 确保套件包可导入（包目录在上级目录）
import os, sys
_skill_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _skill_dir not in sys.path:
    sys.path.append(_skill_dir)
import argparse
import os
import re
import sys

# --out 输出路径强制 范围校验
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from obhrm_research_base.core.safe_path import resolve_safe_output, safe_open_for_write  # noqa: E402

# --------------------------------------------------------------------------- #
# 笔记解析
# --------------------------------------------------------------------------- #
# 注：所有正则必须带 re.M（MULTILINE），否则 `$` 只匹配整个字符串结尾、
# 无法匹配 body（多行）中某一行的行尾，导致年份/作者/全文全部解析为空。
_META_RE = {
    "source": re.compile(r"-\s*源路径:\s*`?(.*?)`?\s*$", re.M),
    "year": re.compile(r"-\s*候选年份\(自动识别\):\s*(.+?)\s*$", re.M),
    "author": re.compile(r"-\s*候选作者\(自动识别\):\s*(.+?)\s*$", re.M),
    "fulltext": re.compile(r"-\s*全文:\s*`?(.*?)`?\s*$", re.M),
}
_H1_RE = re.compile(r"^#\s+(.*)$", re.M)
_DIGIT_PREFIX_RE = re.compile(r"^\d+-")


def _note_title(note_path, body):
    """优先用笔记 H1，否则取文件名（去序号前缀与扩展名）。"""
    m = _H1_RE.search(body)
    if m and m.group(1).strip():
        return m.group(1).strip()
    base = os.path.splitext(os.path.basename(note_path))[0]
    return _DIGIT_PREFIX_RE.sub("", base) or base


def _clean_text(text, max_chars):
    """折叠空白并截断到 max_chars。"""
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > max_chars:
        text = text[:max_chars].rstrip() + "…"
    return text


def parse_note(note_path):
    """解析单个笔记 .md，返回元数据字典。"""
    with open(note_path, encoding="utf-8") as fh:
        body = fh.read()
    meta = {"source": "", "year": "", "author": "", "fulltext": "",
            "title": _note_title(note_path, body), "body": body}
    for key, rx in _META_RE.items():
        m = rx.search(body)
        if m:
            meta[key] = m.group(1).strip()
    return meta


def _force_txt_name(base):
    """把任意基名规整为『去扩展名后强制 .txt』，兼容 .md / 双 .txt / 无扩展名。"""
    name, _ = os.path.splitext(base)
    if name.lower().endswith(".txt"):
        name, _ = os.path.splitext(name)
    return name + ".txt"


def resolve_text_path(notes_dir, texts_dir, meta):
    """解析全文 .txt 路径（B1 修复核心）。

    优先用笔记 `全文:` 行给出的基名（强制 .txt）；不存在时回退到
    笔记同名 .txt。均失败返回 None。
    """
    if meta.get("fulltext"):
        base = os.path.basename(meta["fulltext"])
        cand = os.path.join(texts_dir, _force_txt_name(base))
        if os.path.isfile(cand):
            return cand
    # 回退：笔记基名 + .txt
    note_base = os.path.splitext(os.path.basename(meta.get("_path", "")))[0]
    # _path 可能未传入，调用方需保证；此处再退一步用 title 不可靠，故仅当 fulltext 失败时尝试
    if note_base:
        cand = os.path.join(texts_dir, _force_txt_name(note_base))
        if os.path.isfile(cand):
            return cand
    return None


def extract_abstract(text, max_chars=1200):
    """从全文抽取摘要：优先英文 Abstract / 中文 摘要 段，否则首段。

    返回 "" 表示无全文（调用方应据此标记缺失，而非静默回退 600 字）。
    """
    if not text:
        return ""
    # 英文 Abstract
    m = re.search(
        r"(?is)\babstract\b\s*[:\-—]?\s*(.*?)(?:\n\s*\n|\bkeywords\b|\bindex terms\b|摘要|1\.)",
        text)
    if m and len(m.group(1).strip()) >= 30:
        return _clean_text(m.group(1), max_chars)
    # 中文 摘要
    m = re.search(
        r"(?is)摘要\s*[:：—]?\s*(.*?)(?:\n\s*\n|关键词|关键字|1\.)", text)
    if m and len(m.group(1).strip()) >= 30:
        return _clean_text(m.group(1), max_chars)
    # 回退：首个足够长的段落（真实文本，非 600 字静默回退）
    for para in re.split(r"\n\s*\n", text):
        p = para.strip()
        if len(p) >= 40:
            return _clean_text(p, max_chars)
    return _clean_text(text, max_chars)


def _ref_line(meta):
    """构造一条参考文献行（Author (Year). Title.），供闭环引证核验。"""
    author = meta.get("author") or "Unknown"
    year = meta.get("year") or "n.d."
    title = meta.get("title") or "Untitled"
    return "%s (%s). %s." % (author, year, title)


# --------------------------------------------------------------------------- #
# 主流程
# --------------------------------------------------------------------------- #
def build_readings(ingest_dir, abstract_chars=1200):
    """扫描 ingest_dir/notes/*.md，构建文献条目列表。

    Returns:
        List[dict]: 每项含 title / author / year / source / text_path /
                    abstract / missing(bool) / ref_line。
    """
    notes_dir = os.path.join(ingest_dir, "notes")
    texts_dir = os.path.join(ingest_dir, "texts")
    if not os.path.isdir(notes_dir):
        raise SystemExit("找不到 notes 目录：%s" % notes_dir)
    entries = []
    for fn in sorted(os.listdir(notes_dir)):
        if not fn.lower().endswith(".md"):
            continue
        note_path = os.path.join(notes_dir, fn)
        meta = parse_note(note_path)
        meta["_path"] = note_path
        text_path = resolve_text_path(notes_dir, texts_dir, meta)
        if text_path and os.path.isfile(text_path):
            # 限制单次读取上限(4 MiB)，避免超大 PDF 抽取文本导致 OOM；
            # extract_abstract 仅用头部文本，截断足够且安全。
            _MAX_TEXT_READ = 4 * 1024 * 1024
            with open(text_path, encoding="utf-8", errors="ignore") as fh:
                text = fh.read(_MAX_TEXT_READ)
            abstract = extract_abstract(text, abstract_chars)
            missing = False
        else:
            abstract = ""
            missing = True
        entries.append({
            "title": meta["title"],
            "author": meta.get("author", ""),
            "year": meta.get("year", ""),
            "source": meta.get("source", ""),
            "text_path": text_path or "",
            "abstract": abstract,
            "missing": missing,
            "ref_line": _ref_line(meta),
        })
    return entries


def write_readings(entries, out_path, codes=False):
    """写出 READINGS.md（文献条目块 + 摘要块）。

    codes=True 时，在每篇摘要条目下追加 5 个 LRR 阅读密码空槽位
    （SPL/CPL/GAP/RAT/ROF），仅留占位文本待人工/LLM 精读填充，绝不自动编造。
    """
    lines = ["# 已读文献清单（READINGS，自动构建）", ""]
    lines.append("> 由 build_readings.py 从 ingest 产物自动生成；"
                 "文献条目与摘要均待研究者校正，勿直接视作已核实引用。")
    lines.append("")
    lines.append("## 文献条目（供闭环引证核验）")
    for e in entries:
        lines.append("- " + e["ref_line"])
    lines.append("")
    lines.append("## 摘要（自动抽取，待校正）")
    for i, e in enumerate(entries, 1):
        lines.append("")
        lines.append("### %d. %s" % (i, e["title"]))
        if e["missing"]:
            lines.append("- 全文: **缺失**（未在 texts/ 找到对应 .txt，未抽取摘要）")
        else:
            lines.append("- 全文: `%s`" % e["text_path"])
        lines.append("- 来源: `%s`" % (e["source"] or "（未记录）"))
        lines.append("- 摘要: %s" % (e["abstract"] or "（未能抽取）"))
        if codes:
            lines.append("- LRR 阅读密码（待精读填充，勿自动编造）:")
            lines.append("  - SPL（研究问题）: （待精读填充）")
            lines.append("  - CPL（核心贡献）: （待精读填充）")
            lines.append("  - GAP（研究缺口）: （待精读填充）")
            lines.append("  - RAT（论证逻辑）: （待精读填充）")
            lines.append("  - ROF（研究发现）: （待精读填充）")
    with safe_open_for_write(out_path, base=os.getcwd(), encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description="由 ingest 产物构建 READINGS.md")
    ap.add_argument("ingest_dir", help="含 notes/ 与 texts/ 的 ingest 输出目录")
    ap.add_argument("--out", default=None, help="输出路径（默认 <ingest_dir>/READINGS.md）")
    ap.add_argument("--abstract-chars", type=int, default=1200,
                    help="摘要最大字数（默认 1200）")
    ap.add_argument("--codes", action="store_true",
                    help="为每篇文献追加 LRR 阅读密码空槽位（SPL/CPL/GAP/RAT/ROF），"
                         "默认关闭；开启仅留空占位，不自动编造内容")
    args = ap.parse_args(argv)
    out = args.out or os.path.join(args.ingest_dir, "READINGS.md")
    # 强制 范围校验，防止 --out 写出允许范围
    try:
        out = str(resolve_safe_output(out, base=os.getcwd()))
    except ValueError as exc:
        print("错误(--out): %s" % exc, file=sys.stderr)
        return 2
    entries = build_readings(args.ingest_dir, args.abstract_chars)
    write_readings(entries, out, codes=args.codes)
    missing = sum(1 for e in entries if e["missing"])
    print("已构建 %d 篇文献索引 -> %s（全文缺失 %d 篇，已显式标记）"
          % (len(entries), out, missing))
    return 0


if __name__ == "__main__":
    sys.exit(main())
