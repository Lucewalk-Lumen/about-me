#!/usr/bin/env python3
# 确保套件包可导入（包目录在上级目录）
import os, sys
_skill_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _skill_dir not in sys.path:
    sys.path.append(_skill_dir)


"""
生成格式化 Word 审稿意见文档。

用法: python generate_review_docx.py --report 诊断结果.json --output 审稿报告.docx
"""

import os
import platform
from pathlib import Path

try:
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn
    from docx.shared import Pt
except ImportError:
    print("错误：缺少 python-docx 依赖。请运行：pip install python-docx")
    sys.exit(1)


try:
    from obhrm_research_base.core._common_init import log_warning
except Exception:
    def log_warning(msg):
        print(f"[!] {msg}", file=sys.stderr)


def _detect_cn_font():
    system = platform.system()
    if system == "Darwin":
        return "Songti SC"
    elif system == "Windows":
        return "SimSun"
    else:
        return "Noto Sans CJK SC"


_CN_FONT = _detect_cn_font()


class ReviewDocBuilder:
    """审稿意见 Word 文档生成器。

    自动处理：
    - 中文宋体 + 英文 Times New Roman
    - 全文两端对齐
    - 标题加粗 14pt，正文 12pt
    - 先中文后英文分页
    """

    def __init__(self, output_path):
        self.output_path = output_path
        self.doc = Document()
        self._setup_styles()
        self._current_lang = None  # 'cn' or 'en'

    def _setup_styles(self):
        """设置默认样式：两端对齐、字体"""
        style = self.doc.styles["Normal"]
        style.font.name = "Times New Roman"
        style.font.size = Pt(12)
        try:
            rPr = style.element.get_or_add_rPr()
            rFonts = rPr.get_or_add_rFonts()
            rFonts.set(qn("w:eastAsia"), _CN_FONT)
        except Exception as e:
            log_warning(f"字体设置失败: {e}")
        pf = style.paragraph_format
        pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        pf.space_after = Pt(6)
        pf.line_spacing = 1.0

        for i in range(1, 5):
            hs = self.doc.styles[f"Heading {i}"]
            hs.font.name = "Times New Roman"
            hs.font.size = Pt(14)
            hs.font.bold = True
            try:
                rPr = hs.element.get_or_add_rPr()
                rFonts = rPr.get_or_add_rFonts()
                rFonts.set(qn("w:eastAsia"), _CN_FONT)
            except Exception as e:
                log_warning(f"字体设置失败: {e}")
            hs.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    def _add_para(self, text, bold=False):
        """添加两端对齐段落"""
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        r = p.add_run(text)
        r.bold = bold
        r.font.name = "Times New Roman"
        r.font.size = Pt(12)
        try:
            rPr = r._element.get_or_add_rPr()
            rFonts = rPr.get_or_add_rFonts()
            rFonts.set(qn("w:eastAsia"), _CN_FONT)
        except Exception as e:
            log_warning(f"字体设置失败: {e}")
        return p

    def _add_heading(self, text, level=2):
        """添加标题"""
        h = self.doc.add_heading(text, level=level)
        h.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        for run in h.runs:
            run.font.name = "Times New Roman"
            run.font.size = Pt(14)
            try:
                run._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), _CN_FONT)
            except Exception as e:
                log_warning(f"字体设置失败: {e}")
        return h

    def _set_run_cn(self, run, bold=False):
        """Set CJK font on a run with platform detection and error handling."""
        try:
            run._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), _CN_FONT)
        except Exception as e:
            log_warning(f"字体设置失败: {e}")

    def add_manuscript_info(self, title, journal, manuscript_id, keywords):
        """添加稿件基本信息"""
        self._add_heading("审稿意见", level=1)

        for label, value in [
            ("稿件：", title),
            ("期刊：", journal),
            ("稿件编号：", manuscript_id),
            ("关键词：", keywords),
        ]:
            p = self.doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            r = p.add_run(label)
            r.bold = True
            r.font.name = "Times New Roman"
            r.font.size = Pt(12)
            self._set_run_cn(r, bold=True)
            r2 = p.add_run(value)
            r2.font.name = "Times New Roman"
            r2.font.size = Pt(12)
            self._set_run_cn(r2)

        self._add_para("─" * 60)

    def start_chinese(self):
        """开始中文审稿意见部分"""
        self._current_lang = "cn"
        self._add_heading("中文审稿意见", level=2)

    def start_english(self):
        """开始英文审稿意见部分（自动分页）"""
        self._current_lang = "en"
        self.doc.add_page_break()
        self._add_heading("English Review Comments", level=2)

    def add_overall_evaluation(self, *paragraphs):
        """添加总体评价（可传入多个段落）"""
        self._add_heading("总体评价" if self._current_lang == "cn" else "Overall Evaluation", level=3)
        for para in paragraphs:
            self._add_para(para)

    def add_issue(self, dimension, *paragraphs):
        """添加一条问题（按维度分组）。dimension 为维度名称，paragraphs 为 3-5 段分析文本"""
        self._add_heading(dimension, level=4)
        for para in paragraphs:
            self._add_para(para)

    def start_dimension(self, dimension):
        """开始一个维度分组"""
        self._add_heading(dimension, level=4)

    def add_recommendation(self, text):
        """添加推荐意见"""
        heading = "推荐意见" if self._current_lang == "cn" else "Recommendation"
        self._add_heading(heading, level=3)
        self._add_para(text)

    def add_six_criteria_summary(self, items):
        """添加六项评价总结。items 为 6 个字符串的列表"""
        heading = "六项评价总结" if self._current_lang == "cn" else "Summary Evaluation on the Six Criteria"
        self._add_heading(heading, level=3)
        for item in items:
            self._add_para(item)

    def add_closing(self, text):
        """添加结语"""
        self._add_heading("结语" if self._current_lang == "cn" else "Closing", level=3)
        self._add_para(text)

    def add_separator(self):
        """添加分隔线"""
        self._add_para("─" * 60)

    def save(self):
        """保存文档并返回文件信息"""
        self.doc.save(self.output_path)
        output_path = Path(self.output_path)
        size = output_path.stat().st_size
        exists = output_path.exists()
        return {"path": self.output_path, "size": size, "exists": exists}


# 便捷函数：一键生成完整审稿意见

# 8 个论文流程节点是 issues 的唯一规范键（CN/EN 二选一全集），six_criteria 必须恰好 6 项字符串。
# 校验失败 → 报错拒绝输出（不再宽容占位），防止「八维维度名当章节标题」的错结构报告出包。
CANONICAL_DIMENSIONS_CN = [
    "研究问题", "引言与文献综述", "理论基础与假设推导", "研究设计与方法",
    "实证结果与分析", "讨论与启示", "研究伦理与透明度", "写作质量",
]
CANONICAL_DIMENSIONS_EN = [
    "Research Question", "Introduction & Literature Review",
    "Theoretical Foundation & Hypotheses", "Research Design & Methods",
    "Empirical Results & Analysis", "Discussion & Implications",
    "Research Ethics & Transparency", "Writing Quality",
]
CANONICAL_CN_SET = set(CANONICAL_DIMENSIONS_CN)
CANONICAL_EN_SET = set(CANONICAL_DIMENSIONS_EN)
EXPECTED_CRITERIA_COUNT = 6  # 六项 Emerald 标准：Originality / Relationship to Literature / Methodology / Results / Implications / Quality of Communication


def _validate_contract(section, name, strict=True):
    """校验单个 language section 是否满足 C4 交付契约。

    strict=True（默认）：issues 键集必须 == 8 节点全集（CN 或 EN），six_criteria 必须恰好 6 项字符串。
    任一不满足抛 ValueError；strict=False 仅提示，不阻断（内部调试用）。
    空 section（未提供该语言版）视为合法，跳过。
    """
    if not section:
        return
    issues = section.get("issues", {}) or {}
    if isinstance(issues, list):
        issues = {it.get("dimension", ""): it for it in issues}
    keys = set(issues.keys())
    ok_cn = keys == CANONICAL_CN_SET
    ok_en = keys == CANONICAL_EN_SET
    if not (ok_cn or ok_en):
        missing_cn = sorted(CANONICAL_CN_SET - keys)
        extra_cn = sorted(keys - CANONICAL_CN_SET)
        msg = (f"{name}.issues 节点须为 8 个规范维度（CN 或 EN 全集）；"
               f"当前 {len(keys)} 键，缺 {len(missing_cn)} 个（{missing_cn[:3]}…），"
               f"多余 {len(extra_cn)} 个（{extra_cn[:3]}…）。"
               f"请按 output_structure_spec.md「三·五」节把八维诊断重组为 8 节点正文，"
               f"不要把八维维度名（选题质量/文献覆盖…）当章节标题。")
        if strict:
            raise ValueError(msg)
        print(f"[!] [{name}] 契约警告：{msg}", file=sys.stderr)

    sc = section.get("six_criteria")
    if sc is None:
        if strict:
            raise ValueError(f"{name}.six_criteria 缺失：必须为恰好 {EXPECTED_CRITERIA_COUNT} 项的字符串列表"
                             f"（六项 Emerald 总结，见 output_structure_spec.md 第八节）。")
        return
    if not isinstance(sc, (list, tuple)) or len(sc) != EXPECTED_CRITERIA_COUNT:
        raise ValueError(f"{name}.six_criteria 必须为恰好 {EXPECTED_CRITERIA_COUNT} 项的列表，"
                         f"当前 {len(sc)} 项（不得把八维总结 8 项冒充六项）。")
    for item in sc:
        if not isinstance(item, str):
            raise ValueError(f"{name}.six_criteria 元素必须是字符串（Word 六维文字总结），"
                             f"数值评分请放 six_criteria_numeric，而非写入 six_criteria。")
    return


def generate_review(output_path, manuscript_info, chinese_sections, english_sections, strict_dims=True):
    """快速生成完整审稿意见。

    Args:
        output_path: 输出路径
        manuscript_info: dict，包含 title, journal, manuscript_id, keywords
        chinese_sections: dict，包含 overall_evaluation(list), issues(dict{维度: [段落列表]}),
                          recommendation(str), six_criteria(list), closing(str)
        english_sections: 同上结构
        strict_dims: 默认 True 硬校验 C4 交付契约（issues 8 节点键 + six_criteria 6 项），
                     不满足抛 ValueError 拒绝输出；False 仅用于内部调试。
    """
    if strict_dims:
        _validate_contract(chinese_sections, "chinese_sections", strict=True)
        _validate_contract(english_sections, "english_sections", strict=True)
    builder = ReviewDocBuilder(output_path)

    # 兼容最小 manuscript_info；recommendation 不属于稿件基本信息，不传入 add_manuscript_info。
    builder.add_manuscript_info(
        title=manuscript_info.get("title", manuscript_info.get("manuscript_title", "稿件标题待定")),
        journal=manuscript_info.get("journal", "目标期刊待定"),
        manuscript_id=manuscript_info.get("manuscript_id", manuscript_info.get("id", "稿件编号待补充")),
        keywords=manuscript_info.get("keywords", "关键词待补充"),
    )

    def _as_list(value, default=None):
        if value is None:
            return default or []
        if isinstance(value, list):
            return value
        return [str(value)]

    def _issues(section):
        issues = section.get("issues", {})
        if isinstance(issues, dict):
            return issues
        if isinstance(issues, list):
            return {
                item.get("dimension", f"问题{i+1}"): _as_list(
                    item.get("text") or item.get("description") or item.get("issue")
                )
                for i, item in enumerate(issues)
            }
        return {}

    # 中文
    builder.start_chinese()
    builder.add_overall_evaluation(
        *_as_list(chinese_sections.get("overall_evaluation", chinese_sections.get("summary", "")))
    )
    for dim, paras in _issues(chinese_sections).items():
        builder.add_issue(dim, *_as_list(paras))
    builder.add_recommendation(
        chinese_sections.get("recommendation", manuscript_info.get("recommendation", "未给出推荐意见"))
    )
    builder.add_six_criteria_summary(_as_list(chinese_sections.get("six_criteria", []), default=["六项评价总结待补充"]))
    builder.add_closing(chinese_sections.get("closing", "以上意见供作者修改参考。"))

    # 英文
    builder.start_english()
    builder.add_overall_evaluation(
        *_as_list(english_sections.get("overall_evaluation", english_sections.get("summary", "")))
    )
    for dim, paras in _issues(english_sections).items():
        builder.add_issue(dim, *_as_list(paras))
    builder.add_recommendation(
        english_sections.get("recommendation", manuscript_info.get("recommendation", "Not specified"))
    )
    builder.add_six_criteria_summary(
        _as_list(english_sections.get("six_criteria", []), default=["Six-criteria summary not provided."])
    )
    builder.add_closing(english_sections.get("closing", "These comments are provided for the authors’ revision."))

    return builder.save()


if __name__ == "__main__":
    import argparse
    import json
    import sys
    from obhrm_research_base.core.safe_path import resolve_safe_output

    parser = argparse.ArgumentParser(
        description="生成格式化 Word 审稿意见文档",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "输入 JSON 结构:\n"
            "  {\n"
            '    "manuscript_info": {"title": "...", "journal": "...", "manuscript_id": "...", "keywords": "..."},\n'
            '    "chinese_sections": {"overall_evaluation": [...], "issues": {维度: [段落]}, "recommendation": "...", "six_criteria": [...], "closing": "..."},\n'
            '    "english_sections": {... 同结构 ...}\n'
            "  }\n"
            "示例:\n"
            "  python generate_review_docx.py --report 诊断结果.json\n"
            "  python generate_review_docx.py --report 诊断结果.json --output 审稿报告.docx\n"
        ),
    )
    parser.add_argument(
        "--report", "-i",
        required=True,
        help="审稿数据 JSON 文件（含 manuscript_info / chinese_sections / english_sections）",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="输出 Word 文档路径（.docx），默认与输入同名 + _review.docx",
    )
    parser.add_argument(
        "--no-strict-dims",
        action="store_true",
        help="关闭 C4 契约硬校验（issues 8 节点键 + six_criteria 6 项）。仅内部调试用，交付必须保持校验开启",
    )
    args = parser.parse_args()

    report_path = Path(args.report)
    if not report_path.exists():
        print(f"错误：输入文件不存在: {report_path}", file=sys.stderr)
        sys.exit(1)

    with open(report_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict):
        manuscript_info = data.get("manuscript_info", {}) or {}
        chinese_sections = data.get("chinese_sections", {}) or {}
        english_sections = data.get("english_sections", {}) or {}
    else:
        print("错误：JSON 顶层应为对象，包含 manuscript_info / chinese_sections / english_sections", file=sys.stderr)
        sys.exit(1)

    if args.output:
        try:
            # 所有用户可控输出路径统一经 resolve_safe_output 范围校验：
            # 相对路径以 cwd 为基准，绝对路径同样要求落在允许范围内；
            # 越界（含 `..` 上跳或工作区外绝对路径）一律拒绝写出。
            _out_raw = os.path.expanduser(args.output)
            output_path = str(resolve_safe_output(_out_raw, base=os.getcwd()))
        except ValueError as e:
            print(f"错误：{e}", file=sys.stderr)
            sys.exit(1)
    else:
        # 默认派生路径（与 --report 同目录）同样必须经范围校验：
        # 若 --report 指向工作区外，默认输出会把交付物写到区外，故一律拒绝。
        try:
            output_path = str(resolve_safe_output(
                report_path.with_name(report_path.stem + "_review.docx"), base=os.getcwd()))
        except ValueError as e:
            print(f"错误：默认输出路径超出工作区范围（请用 --output 指定工作区内路径）: {e}",
                  file=sys.stderr)
            sys.exit(1)

    try:
        result = generate_review(
            output_path, manuscript_info, chinese_sections, english_sections,
            strict_dims=not args.no_strict_dims,
        )
    except ValueError as e:
        print(f"[X] 审稿报告生成失败（C4 交付契约校验未通过）: {e}", file=sys.stderr)
        print("提示：将八维诊断按 output_structure_spec.md「三·五」节重组为 8 节点正文 + 六项 Emerald 总结后再生成。", file=sys.stderr)
        sys.exit(2)
    print("审稿报告已生成:", result)
