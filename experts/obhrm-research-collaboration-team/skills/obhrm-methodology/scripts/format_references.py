#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""参考文献 APA7 规范化器。

读取 READINGS 风格的书目清单（Markdown，每行一条，以 '- ' 开头），将每条归一为
APA 7th 格式，并按第一作者姓氏排序（拉丁姓氏在前、中文按首字 Unicode 序在后），
输出 Markdown。可被 litreview_docx_export.py 以模块方式导入（normalize_references）。

归一规则由 ../../literature-review/knowledge/reference_formats.json 的对应样式驱动（作者连接符、DOI 拼接、
输出模板均可配置）；缺省回退内置 DEFAULT_SPEC，保证模块导入零依赖。

仅依赖 Python 标准库。

用法
----
    python format_references.py <readings.md> [--out references_apa7.md] [--style apa7]
"""
# 确保套件包可导入（包目录在上级目录）
import os, sys
_skill_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _skill_dir not in sys.path:
    sys.path.append(_skill_dir)

import argparse
import json
import os
import re
import sys

# 确保 scripts/ 在路径中（便于以脚本方式直接运行 / 被导入），再导入同目录工具
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from obhrm_research_base.core.safe_path import resolve_config_path, resolve_safe_output  # noqa: E402

YEAR_RE = re.compile(r"[（(]((?:19|20)\d{2}[a-z]?)[）)]")
DOI_RE = re.compile(r"https?://\S+")
CJK_RE = re.compile(r"[一-鿿]")
# 作者段连接符：'and' 必须加词边界 \b，否则会误切姓名内部字母
# （如 Sandberg→S/berg、Fernandez→Fern/ez、Anderson→erson）
_AUTHOR_SEP = re.compile(r"\s*(?:&|与|和|\band\b|,|，)\s*")

# 内置默认样式：与 ../../literature-review/knowledge/reference_formats.json 的 apa7 等价。
# 当 JSON 缺失或样式不存在时回退，保证 litreview_docx_export.py 以库方式导入时零副作用。
DEFAULT_SPEC = {
    "name": "APA 7th Edition (国际期刊)",
    "template": "{authors}. ({year}). {remainder}{doi}",
    "en": {"author_join": ", & "},
    "cn": {"author_join": "，"},
    "doi": {"join": " "},
}


def _is_chinese(text):
    return bool(CJK_RE.search(text))


def _strip_initials(chunk):
    """英文姓名去名缩写，保留姓。'Last, F. M.' -> 'Last'；'F. M. Last' -> 'Last'。"""
    if "," in chunk:
        chunk = chunk.split(",")[0]
    else:
        chunk = re.sub(r"(?<![A-Za-z])\b[A-Za-z]\b\.?", " ", chunk)
        parts = [p for p in chunk.split() if p]
        if parts:
            chunk = parts[-1]
    return chunk


def _first_surname(author_part):
    """提取第一作者姓氏作为排序键（归一化小写）。"""
    first = _AUTHOR_SEP.split(author_part)[0].strip()
    first = _strip_initials(first)
    return re.sub(r"[^A-Za-z一-龥]", "", first).lower()


def _fix_english_authors(author_part, join=", & "):
    """将 '&' 前的连接归一为 join（默认 ', & '）。

    吸收 '&' 前后已有的逗号与空格再统一替换，因此 'A & B'、'A, & B'、'A&B'
    都归一为单一形态，避免对已合规输入重复插入逗号（如 'R., , & Anderson'）。
    """
    return re.sub(r"\s*,?\s*&\s*", join, author_part)


def normalize_entry(raw, spec=None):
    """将一条原始书目归一为 (sort_key, apa_text)；解析失败返回 None。

    spec: 样式 dict（含 template / en.author_join / cn.author_join / doi.join）。
          为 None 时回退 DEFAULT_SPEC，使库导入零副作用。
    """
    spec = spec or DEFAULT_SPEC
    raw = raw.strip()
    if not raw:
        return None
    doi_match = DOI_RE.search(raw)
    doi = doi_match.group(0) if doi_match else ""
    body = raw
    if doi_match:
        body = raw[:doi_match.start()].rstrip() + raw[doi_match.end():]
    body = body.strip()

    ym = YEAR_RE.search(body)
    if not ym:
        return None
    year = ym.group(1)
    author_part = body[:ym.start()].strip().rstrip(" ,，&与和")
    remainder = body[ym.end():].strip().lstrip(". ")

    lang = "cn" if _is_chinese(author_part) else "en"
    if lang == "en":
        authors = _fix_english_authors(author_part, spec["en"].get("author_join", ", & "))
    else:
        authors = author_part

    text = spec["template"].format(
        authors=authors.rstrip("."),
        year=year,
        remainder=remainder.rstrip(),
        doi=("" if not doi else spec["doi"].get("join", " ") + doi),
    )
    if not doi and not text.rstrip().endswith("."):
        text = text.rstrip() + "."
    return _first_surname(author_part), text


def normalize_references(markdown_text, spec=None):
    """解析 READINGS markdown，返回按第一作者姓氏排序的 APA 文本列表（英文在前、中文在后）。"""
    items = []
    for line in markdown_text.splitlines():
        s = line.strip()
        if not s.startswith("-"):
            continue
        entry = s[1:].strip()
        if not entry:
            continue
        res = normalize_entry(entry, spec)
        if res is None:
            continue
        items.append(res)
    items.sort(key=lambda x: x[0])
    return [t for _, t in items]


def render_markdown(refs_list, heading="参考文献"):
    """渲染 APA7 参考文献 Markdown（每条一自然段，段间空行）。"""
    lines = ["# %s" % heading, ""]
    for t in refs_list:
        lines.append(t)
        lines.append("")
    return "\n".join(lines)


def _load_reference_style_spec():
    """读取 config.json 的 reference_format 与 ../../literature-review/knowledge/reference_formats.json。

    返回 spec dict（取 reference_format 对应样式；缺失时回退 DEFAULT_SPEC）。
    仅由 main 调用，模块导入时不触发，保证被 litreview_docx_export.py 以库方式 import 时零副作用。
    """
    here = os.path.dirname(os.path.abspath(__file__))
    style_key = "apa7"
    cfg_path = resolve_config_path(script_file=__file__)
    if os.path.isfile(cfg_path):
        try:
            with open(cfg_path, encoding="utf-8") as fh:
                style_key = json.load(fh).get("reference_format", "apa7") or "apa7"
        except (ValueError, OSError):
            pass
    spec = None
    spec_path = os.path.join(here, "..", "knowledge", "reference_formats.json")
    if os.path.isfile(spec_path):
        try:
            with open(spec_path, encoding="utf-8") as fh:
                spec = json.load(fh).get(style_key)
        except (ValueError, OSError):
            pass
    return spec or DEFAULT_SPEC


def main(argv):
    ap = argparse.ArgumentParser(
        description="参考文献 APA7 规范化（格式由 config.json 的 reference_format 决定，"
                    "规则见 ../../literature-review/knowledge/reference_formats.json）")
    ap.add_argument("readings", help="READINGS 风格书目清单 Markdown")
    ap.add_argument("--out", default=None, help="输出路径（默认 <readings>_APA7.md）")
    ap.add_argument("--style", default=None,
                    help="覆盖格式（默认取 ../config.json 的 reference_format，当前仅支持 apa7）")
    args = ap.parse_args(argv)

    spec = _load_reference_style_spec()
    if args.style:
        here = os.path.dirname(os.path.abspath(__file__))
        spec_path = os.path.join(here, "..", "knowledge", "reference_formats.json")
        if os.path.isfile(spec_path):
            try:
                with open(spec_path, encoding="utf-8") as fh:
                    spec = json.load(fh).get(args.style) or spec
            except (ValueError, OSError):
                pass

    if not os.path.isfile(args.readings):
        print("错误: 书目文件未找到: %s" % args.readings, file=sys.stderr)
        return 2
    with open(args.readings, encoding="utf-8") as fh:
        text = fh.read()
    refs = normalize_references(text, spec)
    out = render_markdown(refs)
    out_path = args.out or (os.path.splitext(args.readings)[0] + "_APA7.md")
    # 强制 范围校验，防止 --out 写出允许范围
    try:
        out_path = str(resolve_safe_output(out_path, base=os.getcwd()))
    except ValueError as exc:
        print("错误(--out): %s" % exc, file=sys.stderr)
        return 2
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(out)
    print("已生成 %s 参考文献: %s" % (spec.get("name", "APA7"), out_path))
    print("合计 %d 条" % len(refs))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
