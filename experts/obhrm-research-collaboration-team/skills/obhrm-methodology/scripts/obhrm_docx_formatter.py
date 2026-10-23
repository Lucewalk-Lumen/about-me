#!/usr/bin/env python3
# 确保套件包可导入（包目录在上级目录）
import os, sys
_skill_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _skill_dir not in sys.path:
    sys.path.append(_skill_dir)


"""
obhrm_docx_formatter.py — OBHRM研究套件 Word学术文档格式化生成脚本
WPS通用论文格式：A4/宋体小四/黑体标题/TNR英文/五号表格/图片嵌入/真Word表格

用法: python obhrm_docx_formatter.py --input 草稿.md --output 论文.docx
"""

import argparse
import os
import re
import sys
from pathlib import Path

from obhrm_research_base.core._common_init import HAVE_COMMON_MODULES, init_logger, log_debug, log_warning, get_config

logger = init_logger("obhrm_docx_formatter")

from obhrm_research_base.core.safe_path import resolve_safe_output
from obhrm_research_base.core.audit_log import log_event

try:
    from docx import Document
    from docx.enum.style import WD_STYLE_TYPE
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import parse_xml
    from docx.oxml.ns import nsdecls, qn
    from docx.shared import Cm, Pt, RGBColor
except ImportError:
    print("错误：缺少 python-docx 依赖。请运行：pip install python-docx")
    sys.exit(1)


def _detect_platform_fonts():
    """Detect available CJK fonts based on platform, returns (cn_body, cn_heading, cn_code) tuples."""
    import platform

    system = platform.system()
    if system == "Darwin":  # macOS
        return "Songti SC", "Heiti SC", "STFangsong"
    elif system == "Windows":
        return "SimSun", "SimHei", "FangSong"
    else:  # Linux and others
        return "Noto Sans CJK SC", "Noto Sans CJK SC", "Noto Sans CJK SC"


# 模块加载时预探测系统字体
_PLATFORM_CN_BODY, _PLATFORM_CN_HEADING, _PLATFORM_CN_CODE = _detect_platform_fonts()


def get_font_from_config(font_type: str = "chinese_body"):
    """从配置获取字体"""
    if HAVE_COMMON_MODULES:
        config = get_config()
        return config.get_font(font_type)
    return _PLATFORM_CN_BODY


def set_run_font(run, cn_font=None, en_font="Times New Roman", size=Pt(12), bold=False, italic=False, color=None):
    """设置字体"""
    if cn_font is None:
        cn_font = get_font_from_config("chinese_body")

    run.font.size = size
    run.bold = bold
    run.italic = italic
    if color:
        run.font.color.rgb = color
    run.font.name = en_font
    r = run._element
    rPr = r.find(qn("w:rPr"))
    if rPr is None:
        rPr = r.makeelement(qn("w:rPr"), {})
        r.insert(0, rPr)
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = rPr.makeelement(qn("w:rFonts"), {})
        rPr.insert(0, rFonts)
    rFonts.set(qn("w:eastAsia"), cn_font)
    log_debug(f"设置字体: {cn_font} / {en_font}, 大小: {size}")


def set_cell_borders(cell):
    """设置单元格边框"""
    try:
        tc = cell._tc
        tcPr = tc.get_or_add_tcPr()
        borders_xml = (
            "<w:tcBorders {ns}>"
            '  <w:top w:val="single" w:size="4" w:space="0" w:color="999999"/>'
            '  <w:left w:val="single" w:size="4" w:space="0" w:color="999999"/>'
            '  <w:bottom w:val="single" w:size="4" w:space="0" w:color="999999"/>'
            '  <w:right w:val="single" w:size="4" w:space="0" w:color="999999"/>'
            "</w:tcBorders>"
        ).format(ns=nsdecls("w"))
        tcPr.append(parse_xml(borders_xml))
    except Exception as e:
        log_warning(f"设置单元格边框失败: {e}")


def set_cell_shading(cell, color_hex):
    """设置单元格背景色"""
    try:
        tcPr = cell._tc.get_or_add_tcPr()
        tcPr.append(parse_xml('<w:shd {ns} w:fill="{fill}"/>'.format(ns=nsdecls("w"), fill=color_hex)))
    except Exception as e:
        log_warning(f"设置单元格背景色失败: {e}")


def clean_bold(text):
    """清理加粗标记"""
    if text:
        return re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    return text


class OBHRMDocFormatter:

    def __init__(self, title="", images_dir=None):
        self.doc = Document()
        self.title = title
        self.images_dir = images_dir
        self._setup_styles()
        self._setup_page()
        self._table_buffer = []
        self._pending_caption = None

    def _set_cn_font(self, style, font=None):
        if font is None:
            font = _PLATFORM_CN_BODY
        try:
            rPr = style.element.get_or_add_rPr()
            rFonts = rPr.get_or_add_rFonts()
            rFonts.set(qn("w:eastAsia"), font)
        except Exception as e:
            log_warning(f"样式设置失败: {e}")

    def _setup_styles(self):
        n = self.doc.styles["Normal"]
        n.font.name = "Times New Roman"
        n.font.size = Pt(12)
        self._set_cn_font(n, _PLATFORM_CN_BODY)
        pf = n.paragraph_format
        pf.line_spacing = 1.5
        pf.space_after = Pt(0)
        pf.space_before = Pt(0)
        pf.first_line_indent = Cm(0.74)

        hcfg = {
            "Heading 1": (_PLATFORM_CN_HEADING, Pt(16), True, WD_ALIGN_PARAGRAPH.CENTER, Pt(24), Pt(18)),
            "Heading 2": (_PLATFORM_CN_HEADING, Pt(14), True, WD_ALIGN_PARAGRAPH.LEFT, Pt(12), Pt(6)),
            "Heading 3": (_PLATFORM_CN_HEADING, Pt(12), True, WD_ALIGN_PARAGRAPH.LEFT, Pt(6), Pt(3)),
            "Heading 4": (_PLATFORM_CN_BODY, Pt(12), True, WD_ALIGN_PARAGRAPH.LEFT, Pt(3), Pt(3)),
        }
        for sn, (cn, sz, b, al, sb, sa) in hcfg.items():
            try:
                h = self.doc.styles[sn]
                h.font.name = "Times New Roman"
                h.font.size = sz
                h.font.bold = b
                h.font.color.rgb = RGBColor(0, 0, 0)
                h.paragraph_format.alignment = al
                h.paragraph_format.space_before = sb
                h.paragraph_format.space_after = sa
                h.paragraph_format.first_line_indent = Cm(0)
                self._set_cn_font(h, cn)
            except KeyError:
                pass

        for ls in ["List Bullet", "List Number"]:
            try:
                s = self.doc.styles[ls]
                s.font.name = "Times New Roman"
                s.font.size = Pt(12)
                self._set_cn_font(s, _PLATFORM_CN_BODY)
                s.paragraph_format.line_spacing = 1.5
                s.paragraph_format.space_after = Pt(0)
                s.paragraph_format.left_indent = Cm(0.74)
                s.paragraph_format.first_line_indent = Cm(0)
            except Exception as e:
                log_warning(f"样式设置失败: {e}")

        for sn, sz, al in [
            ("TableCaption", Pt(10.5), WD_ALIGN_PARAGRAPH.CENTER),
            ("FigureCaption", Pt(10.5), WD_ALIGN_PARAGRAPH.CENTER),
            ("Reference", Pt(10.5), WD_ALIGN_PARAGRAPH.LEFT),
        ]:
            try:
                s = self.doc.styles.add_style(sn, WD_STYLE_TYPE.PARAGRAPH)
                s.font.name = "Times New Roman"
                s.font.size = sz
                self._set_cn_font(s, _PLATFORM_CN_BODY)
                s.paragraph_format.alignment = al
                s.paragraph_format.line_spacing = 1.5
                s.paragraph_format.first_line_indent = Cm(0)
                if sn == "Reference":
                    s.paragraph_format.first_line_indent = Cm(-0.74)
            except Exception as e:
                log_warning(f"样式设置失败: {e}")

    def _setup_page(self):
        sec = self.doc.sections[0]
        sec.page_width = Cm(21.0)
        sec.page_height = Cm(29.7)
        sec.top_margin = Cm(2.54)
        sec.bottom_margin = Cm(2.54)
        sec.left_margin = Cm(3.17)
        sec.right_margin = Cm(3.17)
        hdr = sec.header
        hdr.is_linked_to_previous = False
        hp = hdr.paragraphs[0]
        hp.text = self.title or "OBHRM Research Document"
        hp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for r in hp.runs:
            set_run_font(r, cn_font=_PLATFORM_CN_BODY, size=Pt(9), color=RGBColor(128, 128, 128))
        ftr = sec.footer
        ftr.is_linked_to_previous = False
        fp = ftr.paragraphs[0]
        fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r1 = fp.add_run()
        r1._element.append(r1._element.makeelement(qn("w:fldChar"), {qn("w:fldCharType"): "begin"}))
        r2 = fp.add_run()
        it = r2._element.makeelement(qn("w:instrText"), {})
        it.text = " PAGE "
        r2._element.append(it)
        r3 = fp.add_run()
        r3._element.append(r3._element.makeelement(qn("w:fldChar"), {qn("w:fldCharType"): "end"}))

    def add_cover_page(self, title, subtitle=None, fund_type="moegen"):
        """添加基金项目书封面页。fund_type: 'nsfc'=国自科, 'nssf'=国社科, 'moegen'=教育部.

        调用示例：
            fmt = OBHRMDocFormatter(title="...")
            fmt.add_cover_page("项目标题", "教育部人文社会科学研究规划基金项目申请书")
            fmt.parse_markdown(md_text)  # 接着写正文
            fmt.save("output.docx")
        """
        # 空行
        for _ in range(3):
            self.doc.add_paragraph()
        # 项目类型行
        if subtitle:
            p = self.doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            set_run_font(p.add_run(subtitle), cn_font=_PLATFORM_CN_HEADING, size=Pt(22), bold=True)
        # 空行
        for _ in range(2):
            self.doc.add_paragraph()
        # 标题行
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        set_run_font(p.add_run(title), cn_font=_PLATFORM_CN_HEADING, size=Pt(18), bold=True)
        # 分页
        self.doc.add_page_break()

    def _flush_table(self):
        if not self._table_buffer:
            return
        rows_data = self._table_buffer
        self._table_buffer = []
        ncols = max(len(r) for r in rows_data)
        for r in rows_data:
            while len(r) < ncols:
                r.append("")
        if self._pending_caption:
            cp = self.doc.add_paragraph()
            cp.paragraph_format.first_line_indent = Cm(0)
            cp.paragraph_format.space_before = Pt(6)
            cp.paragraph_format.space_after = Pt(3)
            cp.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
            cp.paragraph_format.line_spacing = 1.5
            set_run_font(cp.add_run(self._pending_caption), size=Pt(10.5), bold=True, cn_font=_PLATFORM_CN_HEADING)
            self._pending_caption = None
        tbl = self.doc.add_table(rows=len(rows_data), cols=ncols)
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        for i, rd in enumerate(rows_data):
            for j, txt in enumerate(rd):
                cell = tbl.cell(i, j)
                cell.text = ""
                set_cell_borders(cell)
                p = cell.paragraphs[0]
                p.paragraph_format.first_line_indent = Cm(0)
                p.paragraph_format.space_before = Pt(2)
                p.paragraph_format.space_after = Pt(2)
                p.paragraph_format.line_spacing = 1.25
                ct = re.sub(r"\*\*([^*]+)\*\*", r"\1", txt)
                if i == 0:
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    set_cell_shading(cell, "F2F2F2")
                    set_run_font(p.add_run(ct.strip()), size=Pt(10.5), bold=True, cn_font=_PLATFORM_CN_HEADING)
                else:
                    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                    set_run_font(p.add_run(ct.strip()), size=Pt(10.5), cn_font=_PLATFORM_CN_BODY)
        self.doc.add_paragraph().paragraph_format.space_before = Pt(0)

    def _process_inline(self, para, text):
        parts_list = re.split(r"(\x60[^\x60]+\x60)", text)
        for part in parts_list:
            if part.startswith("\x60") and part.endswith("\x60"):
                set_run_font(para.add_run(part[1:-1]), cn_font="FangSong", en_font="Courier New", size=Pt(10.5))
            else:
                bps = re.split(r"(\*\*[^*]+\*\*)", part)
                for bp in bps:
                    if bp.startswith("**") and bp.endswith("**"):
                        set_run_font(para.add_run(bp[2:-2]), bold=True)
                    else:
                        ips = re.split(r"(\*[^*]+\*)", bp)
                        for ip in ips:
                            if ip.startswith("*") and ip.endswith("*") and not ip.startswith("**"):
                                set_run_font(para.add_run(ip[1:-1]), italic=True)
                            else:
                                set_run_font(para.add_run(ip))

    def _add_body(self, text):
        p = self.doc.add_paragraph()
        p.paragraph_format.first_line_indent = Cm(0.74)
        p.paragraph_format.line_spacing = 1.5
        self._process_inline(p, text)
        return p

    def _add_image(self, img_path, caption=""):
        abs_path = None
        if Path(img_path).is_absolute():
            abs_path = img_path
        elif self.images_dir:
            abs_path = str(Path(self.images_dir) / img_path)
        # 自动补全常见图片后缀（Markdown中常省略.png/.jpg等）
        if abs_path and not Path(abs_path).exists():
            for ext in (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".svg", ".tiff"):
                candidate = abs_path + ext
                if Path(candidate).exists():
                    abs_path = candidate
                    break
        if not abs_path or not Path(abs_path).exists():
            p = self.doc.add_paragraph()
            p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
            set_run_font(p.add_run("[图片: {}]".format(img_path)), color=RGBColor(180, 0, 0), italic=True)
            return
        # 用户提供的图片路径需先做范围校验，超出范围（如指向其他目录的绝对路径、
        # 或 ../ 跳出 cwd / images_dir）一律拒绝读取，仅渲染占位符。
        try:
            base_roots = [os.getcwd()]
            if self.images_dir:
                base_roots.append(self.images_dir)
            safe_img = resolve_safe_output(abs_path, base=base_roots)
        except ValueError as e:
            print(f"  提示: 图片路径超出允许范围，拒绝读取 — {e}")
            log_event("read_image_blocked", path=str(abs_path))
            p = self.doc.add_paragraph()
            p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
            set_run_font(p.add_run("[图片: {}]".format(img_path)), color=RGBColor(180, 0, 0), italic=True)
            return
        try:
            from PIL import Image as PILImage

            with PILImage.open(safe_img) as im:
                wp, hp_px = im.size
                _dpi_raw = im.info.get("dpi") if hasattr(im, "info") else None
                dpi = (_dpi_raw[0] if _dpi_raw and _dpi_raw[0] else 96)
            wc = wp / dpi * 2.54
            hc = hp_px / dpi * 2.54
            maxw = 15.0
            if wc > maxw:
                s = maxw / wc
                wc = maxw
                hc *= s
            p = self.doc.add_paragraph()
            p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_before = Pt(6)
            p.paragraph_format.space_after = Pt(3)
            p.paragraph_format.first_line_indent = Cm(0)
            p.add_run().add_picture(str(safe_img), width=Cm(wc))
            log_event("read_image", path=str(safe_img))
        except Exception as e:
            p = self.doc.add_paragraph()
            p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
            set_run_font(p.add_run("[图片加载失败: {}]".format(str(e))), color=RGBColor(180, 0, 0), italic=True)
        if caption:
            cp = self.doc.add_paragraph()
            cp.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
            cp.paragraph_format.space_before = Pt(3)
            cp.paragraph_format.space_after = Pt(6)
            cp.paragraph_format.first_line_indent = Cm(0)
            cp.paragraph_format.line_spacing = 1.5
            set_run_font(cp.add_run(caption), size=Pt(10.5))

    def _read_markdown_file(self, p, base=None):
        """读取 Markdown 文件内容。

        base 为 None 时按原路径读取(显式 source_path，属用户主动指定的输入文件);
        base 给定时先经 resolve_safe_output 做范围校验。
        """
        path = Path(str(p).strip())
        if base is not None:
            path = resolve_safe_output(path, base=base)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        print("已从文件读取 Markdown 内容:", path)
        log_event("read_markdown", path=str(path))
        return content

    def parse_markdown(self, md_text=None, source_path=None):
        # 显式文件路径模式：caller 通过 source_path 指明"这是文件路径"，
        # 避免把正文内容误判为文件路径。
        if source_path is not None:
            md_text = self._read_markdown_file(source_path)  # 用户主动指定，按原路径读取
        elif isinstance(md_text, str) and md_text.strip().endswith(".md"):
            # 向后兼容：旧调用把路径直接当 md_text 传入；读取前做范围校验（限 cwd 内）
            p = Path(md_text.strip())
            if p.exists() and p.is_file():
                md_text = self._read_markdown_file(p, base=os.getcwd())
        if md_text is None:
            md_text = ""
        lines = md_text.splitlines()
        i = 0
        in_code = False
        code_lines = []

        while i < len(lines):
            line = lines[i]
            s = line.strip()

            if s.startswith("```"):
                if in_code:
                    self._flush_table()
                    self._add_code_block("\n".join(code_lines))
                    code_lines = []
                    in_code = False
                else:
                    self._flush_table()
                    in_code = True
                i += 1
                continue

            if in_code:
                code_lines.append(line)
                i += 1
                continue

            # 图片 ![alt](path) — 支持行内任意位置匹配
            img_m = re.search(r"!\[([^\]]*)\]\(([^)]+)\)", s)
            if img_m:
                self._flush_table()
                # 处理行内所有图片
                remaining = s
                while True:
                    m2 = re.search(r"!\[([^\]]*)\]\(([^)]+)\)", remaining)
                    if not m2:
                        break
                    self._add_image(m2.group(2), m2.group(1))
                    remaining = remaining[m2.end() :]
                i += 1
                continue

            # 标题
            if s.startswith("# "):
                self._flush_table()
                self.doc.add_heading(re.sub(r"\*\*([^*]+)\*\*", r"\1", s[2:].strip()), level=1)
            elif s.startswith("## "):
                self._flush_table()
                self.doc.add_heading(re.sub(r"\*\*([^*]+)\*\*", r"\1", s[3:].strip()), level=2)
            elif s.startswith("### "):
                self._flush_table()
                self.doc.add_heading(re.sub(r"\*\*([^*]+)\*\*", r"\1", s[4:].strip()), level=3)
            elif s.startswith("#### "):
                self._flush_table()
                self.doc.add_heading(re.sub(r"\*\*([^*]+)\*\*", r"\1", s[5:].strip()), level=4)
            elif s.startswith("---") or s.startswith("***"):
                pass
            elif s.startswith("|"):
                cells = [c.strip() for c in s.split("|") if c.strip()]
                if not all(re.match(r"^[-:]+$", c) for c in cells):
                    if not self._table_buffer and i > 0:
                        prev = lines[i - 1].strip()
                        if prev and not prev.startswith("|") and not prev.startswith("#") and not prev.startswith("-"):
                            self._pending_caption = prev
                    self._table_buffer.append(cells)
            else:
                self._flush_table()
                if s.startswith(">"):
                    txt = re.sub(r"^>\s*", "", s)
                    p = self.doc.add_paragraph()
                    p.paragraph_format.left_indent = Cm(1.0)
                    p.paragraph_format.first_line_indent = Cm(0)
                    p.paragraph_format.line_spacing = 1.5
                    set_run_font(p.add_run(txt), italic=True, color=RGBColor(80, 80, 80))
                elif s.startswith("- "):
                    t = s[2:]
                    if not t.startswith("---") and not t.startswith("***"):
                        p = self.doc.add_paragraph(style="List Bullet")
                        self._process_inline(p, t)
                        p.paragraph_format.left_indent = Cm(0.74)
                elif re.match(r"^\s*\d+\s*=\s*.+", s):
                    p = self.doc.add_paragraph()
                    p.paragraph_format.left_indent = Cm(2.0)
                    p.paragraph_format.first_line_indent = Cm(0)
                    set_run_font(p.add_run(s))
                elif re.match(r"^\s*\d+\.\s", s):
                    t = re.sub(r"^\s*\d+\.\s", "", s)
                    p = self.doc.add_paragraph(style="List Number")
                    self._process_inline(p, t)
                elif s == "":
                    pass
                else:
                    self._add_body(s)
            i += 1
        self._flush_table()

    def _add_code_block(self, code_text):
        p = self.doc.add_paragraph()
        p.paragraph_format.left_indent = Cm(1.0)
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.line_spacing = 1.15
        set_run_font(
            p.add_run(code_text),
            cn_font=_PLATFORM_CN_CODE,
            en_font="Courier New",
            size=Pt(9),
            color=RGBColor(50, 50, 50),
        )

    def save(self, output_path):
        self.doc.save(output_path)
        print("文档已保存:", output_path)
        log_event("write_docx", path=str(output_path))


def count_chars_stats(doc_path):
    doc = Document(doc_path)
    total_chars = cjk = eng = 0
    paras = 0
    for para in doc.paragraphs:
        t = para.text.strip()
        if not t:
            continue
        paras += 1
        total_chars += len(t)
        cjk += len(re.findall(r"[\u4e00-\u9fff]", t))
        eng += len(re.findall(r"[a-zA-Z]+", t))
    return dict(
        cjk_chars=cjk,
        english_words=eng,
        effective_words=cjk + eng,
        total_chars=total_chars,
        paragraphs=paras,
        tables=len(doc.tables),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="OBHRM Word 学术文档生成器：将 Markdown 转换为格式化 Word 文档（A4/宋体/黑体/TNR/真表格）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  python obhrm_docx_formatter.py -i 草稿.md -o 论文.docx\n"
            "  python obhrm_docx_formatter.py --input 草稿.md --output 论文.docx --template '我的论文' --images ./figs\n"
        ),
    )
    parser.add_argument(
        "-i", "--input",
        required=True,
        help="输入 Markdown 源文件路径（.md）",
    )
    parser.add_argument(
        "-o", "--output",
        required=True,
        help="输出 Word 文档路径（.docx）",
    )
    parser.add_argument(
        "-t", "--template",
        default="",
        help="文档标题（写入页眉/封面，可选）",
    )
    parser.add_argument(
        "--images",
        default=None,
        help="图片目录（Markdown 中图片相对路径的基础目录，可选）",
    )
    args = parser.parse_args()

    formatter = OBHRMDocFormatter(title=args.template or "", images_dir=args.images)
    formatter.parse_markdown(source_path=args.input)
    try:
        safe_output = resolve_safe_output(args.output, base=os.getcwd())
    except ValueError as e:
        print(f"错误：{e}")
        sys.exit(1)
    formatter.save(str(safe_output))
