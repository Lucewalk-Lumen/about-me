#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
case-writer · Markdown → Word 转换器

所有排版常量（字体 / 字号 / 缩进 / 行距 / 引用规范 / 四条路径映射）统一从
上级目录的 config/case-config.json 读取，作为单一真源。SKILL.md 与脚本不再各自硬编码，
LLM 上下文也不必携带这些数字（省 token）。

行为：
- 正文 [N] → Word 上标（防字面方括号残留）
- 正文 **...** → 粗体（防字面星号残留）
- 标题 #/##/### → 黑体分级
- 『参考文献』标题之后进入悬挂缩进模式，条目保留 [N] 字面
- 正文：宋体 + Times New Roman、两端对齐、首行缩进 2 字符

用法：
    python md_to_docx.py <src.md> [out.docx]

依赖：python-docx（未安装时给出可执行的安装提示，而非 ImportError 堆栈）
"""

import sys
import os
import re
import json

try:
    from docx import Document
    from docx.shared import Pt
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn
except ImportError:  # pragma: no cover - 环境缺依赖时的友好提示
    sys.stderr.write(
        "[ERROR] 缺少依赖 python-docx，无法生成 Word 文档。\n"
        "        请先安装：pip install python-docx\n"
    )
    sys.exit(2)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)
CONFIG_PATH = os.path.join(SKILL_DIR, "config", "case-config.json")

# 兜底默认值：config 缺失时仍可运行
_DEFAULTS = {
    "docx": {
        "fonts": {"body_cn": "宋体", "body_en": "Times New Roman",
                  "heading_cn": "黑体", "heading_en": "Times New Roman",
                  "title_cn": "黑体"},
        # body=12（小四），与 config/case-config.json 及 SKILL.md 阶段 4 的用户面向规范一致。
        # 原值 10.5（五号）与两者均不符，config 缺失时会静默降级为错误字号。
        "sizes_pt": {"title": 18, "h1": 16, "h2": 14, "h3": 12, "body": 12},
        "align": "justify",
        "first_line_indent_pt": 21,
        "ref_hang_indent_pt": 21,
        "spacing": {"title_line": 1.3, "title_after": 6,
                    "heading_line": 1.25, "heading_before": 12,
                    "heading_before_sub": 8, "heading_after": 6,
                    "body_line": 1.5, "body_after": 6,
                    "ref_line": 1.4, "ref_after": 3,
                    "bullet_line": 1.4, "bullet_after": 3},
    },
    "citation": {"inline_superscript": True, "ref_trigger_heading": "参考文献"},
}


def _deep_merge(base, override):
    """把 override 深度合并进 base 的副本，override 优先。

    只做两层 setdefault 会让缺失键回落失败：config 中若存在 sizes_pt 但缺少某个键（如 body），
    该键不会被默认值补齐，后续取值直接 KeyError。此处按缺省值逐键递归补全，任意深度缺键都能兜底。
    """
    merged = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(merged.get(k), dict):
            merged[k] = _deep_merge(merged[k], v)
        else:
            merged[k] = v
    return merged


def load_config():
    """读取 config/case-config.json；任何读取/解析失败都降级为内置默认值，不中断转换。"""
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except FileNotFoundError:
        sys.stderr.write(f"[WARN] 未找到配置文件 {CONFIG_PATH}，使用内置默认值。\n")
        return dict(_DEFAULTS)
    except (json.JSONDecodeError, OSError, UnicodeDecodeError) as e:
        # 配置文件损坏或无读权限时一并降级为内置默认值，避免因读取失败中断转换。
        sys.stderr.write(f"[WARN] 配置文件不可用（{type(e).__name__}: {e}），使用内置默认值。\n")
        return dict(_DEFAULTS)

    if not isinstance(cfg, dict):
        sys.stderr.write("[WARN] 配置文件顶层不是对象，使用内置默认值。\n")
        return dict(_DEFAULTS)

    return _deep_merge(_DEFAULTS, cfg)


CFG = load_config()
D = CFG["docx"]
F = D["fonts"]
SZ = D["sizes_pt"]
SP = D["spacing"]
ALIGN = WD_ALIGN_PARAGRAPH.JUSTIFY if D.get("align") == "justify" else WD_ALIGN_PARAGRAPH.LEFT
INDENT = Pt(D["first_line_indent_pt"])
REF_INDENT = Pt(D["ref_hang_indent_pt"])
TITLE_SIZE = Pt(SZ["title"])
H1_SIZE = Pt(SZ["h1"])
H2_SIZE = Pt(SZ["h2"])
H3_SIZE = Pt(SZ["h3"])
BODY_SIZE = Pt(SZ["body"])


def set_font(run, cn=F["body_cn"], en=F["body_en"], size=BODY_SIZE, bold=False):
    run.font.size = size
    run.font.bold = bold
    run.font.name = en
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = rpr.makeelement(qn("w:rFonts"), {})
        rpr.append(rfonts)
    rfonts.set(qn("w:eastAsia"), cn)
    rfonts.set(qn("w:ascii"), en)
    rfonts.set(qn("w:hAnsi"), en)


def add_title(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(SP["title_after"])
    p.paragraph_format.line_spacing = SP["title_line"]
    set_font(p.add_run(text), cn=F["title_cn"], en=F["heading_en"],
             size=TITLE_SIZE, bold=True)
    return p


def add_meta(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing = 1.2
    set_font(p.add_run(text), size=BODY_SIZE)
    return p


def add_heading(doc, text, level):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.space_before = Pt(SP["heading_before"] if level == 1 else SP["heading_before_sub"])
    p.paragraph_format.space_after = Pt(SP["heading_after"])
    p.paragraph_format.line_spacing = SP["heading_line"]
    size = H1_SIZE if level == 1 else H2_SIZE if level == 2 else H3_SIZE
    set_font(p.add_run(text), cn=F["heading_cn"], en=F["heading_en"],
             size=size, bold=True)
    return p


# 匹配 [N] 上标 或 **粗体** 的内联标记
INLINE_RE = re.compile(r"(\[\d+\]|\*\*[^*]+?\*\*)")


def add_inline_runs(doc, p, text, is_ref=False):
    """把含 [N] / **bold** 的文本拆成多个 run，相应设上标或加粗。
    is_ref=True 时（如参考文献段）保留 [N] 字面，不转上标。"""
    if is_ref:
        parts = re.split(r"(\*\*[^*]+?\*\*)", text)
    else:
        parts = INLINE_RE.split(text)
    for part in parts:
        if not part:
            continue
        if not is_ref and CFG["citation"].get("inline_superscript", True):
            m = re.match(r"^\[(\d+)\]$", part)
            if m:
                run = p.add_run(m.group(1))
                run.font.superscript = True
                set_font(run, size=BODY_SIZE)
                continue
        if part.startswith("**") and part.endswith("**") and len(part) >= 4:
            run = p.add_run(part[2:-2])
            run.font.bold = True
            set_font(run)
            continue
        run = p.add_run(part)
        set_font(run)


def add_body(doc, text):
    p = doc.add_paragraph()
    p.alignment = ALIGN
    p.paragraph_format.first_line_indent = INDENT
    p.paragraph_format.line_spacing = SP["body_line"]
    p.paragraph_format.space_after = Pt(SP["body_after"])
    add_inline_runs(doc, p, text)
    return p


def add_bullet(doc, text):
    p = doc.add_paragraph()
    p.alignment = ALIGN
    p.paragraph_format.left_indent = INDENT
    p.paragraph_format.first_line_indent = -INDENT
    p.paragraph_format.line_spacing = SP["bullet_line"]
    p.paragraph_format.space_after = Pt(SP["bullet_after"])
    set_font(p.add_run("• " + text))
    return p


def add_ref(doc, text):
    """参考文献条目：悬挂缩进，无首行缩进；[N] 保持字面。"""
    p = doc.add_paragraph()
    p.alignment = ALIGN
    p.paragraph_format.left_indent = REF_INDENT
    p.paragraph_format.first_line_indent = -REF_INDENT
    p.paragraph_format.line_spacing = SP["ref_line"]
    p.paragraph_format.space_after = Pt(SP["ref_after"])
    add_inline_runs(doc, p, text, is_ref=True)
    return p


def convert(src, out):
    with open(src, "r", encoding="utf-8") as f:
        lines = f.read().split("\n")

    doc = Document()
    normal = doc.styles["Normal"]
    normal.font.name = F["body_en"]
    normal.font.size = BODY_SIZE
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), F["body_cn"])

    ref_trigger = CFG["citation"].get("ref_trigger_heading", "参考文献")

    title_done = False
    in_code = False
    in_refs = False
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i].rstrip()
        i += 1

        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue

        stripped = line.strip()

        if stripped.startswith("# ") and not title_done:
            add_title(doc, stripped[2:].strip())
            title_done = True
            continue

        if stripped.startswith(">"):
            txt = stripped.lstrip(">").strip()
            if txt:
                add_meta(doc, txt)
            continue

        if stripped.startswith("### "):
            heading_text = stripped[4:].strip()
            in_refs = heading_text.startswith(ref_trigger)
            add_heading(doc, heading_text, 3)
            continue
        if stripped.startswith("## "):
            heading_text = stripped[3:].strip()
            in_refs = heading_text.startswith(ref_trigger)
            add_heading(doc, heading_text, 2)
            continue
        if stripped.startswith("# "):
            heading_text = stripped[2:].strip()
            in_refs = heading_text.startswith(ref_trigger)
            add_heading(doc, heading_text, 1)
            continue

        if re.match(r"^[-*—]\s+", stripped):
            add_bullet(doc, re.sub(r"^[-*—]\s+", "", stripped))
            continue

        if stripped == "":
            continue

        if in_refs:
            add_ref(doc, stripped)
        else:
            add_body(doc, stripped)

    doc.save(out)
    print(f"[OK] 已生成: {out}")


def main(argv):
    if len(argv) < 2:
        sys.stderr.write("用法: python md_to_docx.py <输入.md> [输出.docx]\n")
        return 1

    src = argv[1]
    if not os.path.isfile(src):
        # 提前校验并给出可读错误，避免直接 open() 抛出非工程用户不可读的堆栈。
        sys.stderr.write(f"[ERROR] 输入文件不存在: {src}\n")
        return 1

    out = argv[2] if len(argv) > 2 else os.path.splitext(src)[0] + ".docx"
    out_dir = os.path.dirname(os.path.abspath(out))
    if not os.path.isdir(out_dir):
        sys.stderr.write(f"[ERROR] 输出目录不存在: {out_dir}\n")
        return 1
    # 输出路径 containment：仅允许落在输入文件所在目录或当前工作目录内，防越界写入
    out_abs = os.path.abspath(out)
    src_dir = os.path.dirname(os.path.abspath(src))
    cwd = os.getcwd()
    if not (out_abs == src_dir or out_abs.startswith(src_dir + os.sep)
            or out_abs == cwd or out_abs.startswith(cwd + os.sep)):
        sys.stderr.write(f"[ERROR] 输出路径越界，拒绝写入（须位于输入目录或当前目录内）: {out}\n")
        return 1

    try:
        convert(src, out)
    except OSError as e:
        sys.stderr.write(f"[ERROR] 转换失败（{type(e).__name__}: {e}）\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
