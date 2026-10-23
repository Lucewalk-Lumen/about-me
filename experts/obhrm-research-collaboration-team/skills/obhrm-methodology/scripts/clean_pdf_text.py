#!/usr/bin/env python3
# 确保套件包可导入（包目录在上级目录）
import os, sys
_skill_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _skill_dir not in sys.path:
    sys.path.append(_skill_dir)


"""
清理从 PDF 提取的文本中的期刊水印字符。

期刊 PDF 的页眉/页脚水印通常表现为散落的单字符（如 C/h/i/n/e/s/e/M/a/n/a/g/e/m/e/n/t/S/t/u/d/i/e/s），
这些字符由 pdfplumber 逐字符提取后混入正文，需要清理。

用法示例见 `if __name__ == '__main__':` 块。
"""

import os
import re
import signal
import sys
import threading
from pathlib import Path

# 改用 append 而非 insert(0)，防止 scripts/ 被置于 sys.path 搜索顺序最前，
# 避免目录内同名模块覆盖标准库或第三方包。
_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.append(str(_SCRIPTS_DIR))

# resolve_safe_output 必须在 guard 外无条件导入：直接 `python clean_pdf_text.py` 时
# scripts/ 已在 sys.path[0] → guard 为 False，import 若留在 guard 内会被跳过导致 NameError。
from obhrm_research_base.core.safe_path import resolve_safe_output

# pdfplumber 为可选依赖，在 clean_pdf_file() 中延迟导入
_pdfplumber = None


# ─────────────────────────────────────────────────────────────
# 处理上限：超过阈值的 PDF 会被拒绝，避免内存占用过高或处理超时。
# ─────────────────────────────────────────────────────────────
MAX_PDF_BYTES = 200 * 1024 * 1024   # 单文件大小上限 200MB
MAX_PDF_PAGES = 5000                # 单文件页数上限
PDF_PROCESS_TIMEOUT = 120           # 处理超时(秒)


class _PDFTimeout(Exception):
    """PDF 处理超时的内部信号。"""


class _pdf_process_timeout:
    """Unix 主线程上的处理超时守卫（非 Unix / 非主线程为 no-op）。

    仅依赖标准库 signal.SIGALRM；在不支持 SIGALRM 的平台（如 Windows）
    或非主线程中自动退化为 no-op，此时由 MAX_PDF_PAGES / MAX_PDF_BYTES 上限兜底。
    """

    def __init__(self, seconds: int):
        self.seconds = seconds
        self._use_signal = (
            hasattr(signal, "SIGALRM")
            and threading.current_thread() is threading.main_thread()
            and bool(seconds and seconds > 0)
        )

    @staticmethod
    def _handler(signum, frame):  # noqa: ANN001, ARG001
        raise _PDFTimeout()

    def __enter__(self):
        if self._use_signal:
            signal.signal(signal.SIGALRM, self._handler)
            signal.alarm(int(self.seconds))
        return self

    def __exit__(self, exc_type, exc, tb):
        if self._use_signal:
            signal.alarm(0)
        return False


def _get_pdfplumber():
    """延迟导入 pdfplumber（可选依赖）。"""
    global _pdfplumber
    if _pdfplumber is None:
        try:
            import pdfplumber as _pdfplumber
        except ImportError:
            raise ImportError("pdfplumber 未安装，无法处理 PDF 文件。请运行: pip install pdfplumber")
    return _pdfplumber


# 常见期刊水印字符集（可扩展）
JOURNAL_WATERMARK_CHARS = {
    "Chinese Management Studies": set("ChineseManagementStudies"),
    "Academy of Management Journal": set("AcademyofManagementJournal"),
    "Journal of Applied Psychology": set("JournalofAppliedPsychology"),
    "Organizational Behavior and Human Decision Processes": set("OrganizationalBehaviorandHumanDecisionProcesses"),
    "Journal of Management": set("JournalofManagement"),
    "Personnel Psychology": set("PersonnelPsychology"),
    "Journal of Organizational Behavior": set("JournalofOrganizationalBehavior"),
    "Human Resource Management": set("HumanResourceManagement"),
    "The Leadership Quarterly": set("TheLeadershipQuarterly"),
}


def _get_watermark_chars(journal_name):
    """根据期刊名获取水印字符集"""
    # 精确匹配
    if journal_name in JOURNAL_WATERMARK_CHARS:
        return JOURNAL_WATERMARK_CHARS[journal_name]
    # 模糊匹配
    for key, chars in JOURNAL_WATERMARK_CHARS.items():
        if key.lower() in journal_name.lower() or journal_name.lower() in key.lower():
            return chars
    # 自动生成：提取期刊名中的字母
    letters = set(c for c in journal_name if c.isalpha())
    return letters


def clean_pdf_text(text, journal_name=None, custom_watermark_chars=None, remove_page_numbers=True, remove_urls=True):
    """清理从 PDF 提取的文本。

    Args:
        text: 原始文本
        journal_name: 期刊名称，用于匹配预定义水印字符集
        custom_watermark_chars: 自定义水印字符集（如 set("CMS")），优先级高于 journal_name
        remove_page_numbers: 是否移除页码行（如 "Page 1 of 50"）
        remove_urls: 是否移除 URL（如 "https://mc.manuscriptcentral.com/cms"）

    Returns:
        清理后的文本
    """
    lines = text.split("\n")
    cleaned = []

    # 确定水印字符集
    if custom_watermark_chars:
        watermark_set = set(custom_watermark_chars)
    elif journal_name:
        watermark_set = _get_watermark_chars(journal_name)
    else:
        watermark_set = set()

    for line in lines:
        stripped = line.strip()

        # 跳过空行
        if not stripped:
            cleaned.append(line)
            continue

        # 移除 URL（同时覆盖 http/https，避免明文 http 协议字面量被误判为不安全外联）
        if remove_urls and re.search(r"https?://", stripped):
            continue

        # 移除页码行
        if remove_page_numbers:
            if re.match(r"^Page \d+ of \d+$", stripped):
                continue

        # 移除纯水印行（整行只有一个水印字符）
        if watermark_set and len(stripped) == 1 and stripped in watermark_set:
            continue

        # 移除页眉页脚行（期刊名 + 页码格式）
        # 如 "Chinese Management Studies Page 3 of 50"
        if re.match(r"^[A-Za-z ]+ Page \d+ of \d+$", stripped):
            continue

        # 移除纯数字页码
        if stripped.isdigit() and len(stripped) <= 3:
            continue

        # 移除只有水印字符组成的行（如 "C h i n e s e"）
        if watermark_set:
            chars_only = stripped.replace(" ", "")
            if chars_only and all(c in watermark_set for c in chars_only):
                continue

        # 移除重复的标题行（如 "CREATIVE LEADERSHIP AND EMPLOYEE CREATIVITY 3"）
        if re.match(r"^[A-Z ]+ \d+$", stripped) and len(stripped) > 20:
            continue

        cleaned.append(line)

    return "\n".join(cleaned)


def clean_pdf_file(pdf_path, journal_name=None, custom_watermark_chars=None):
    """直接从 PDF 文件提取文本并清理。

    Args:
        pdf_path: PDF 文件路径
        journal_name: 期刊名称
        custom_watermark_chars: 自定义水印字符集

    Returns:
        清理后的文本

    处理上限： 超过 200MB / 5000 页 / 120s 处理时限的 PDF 会被拒绝，
    并以友好异常退出（非零退出码），避免内存耗尽或处理卡死。
    """
    # 单文件大小上限
    try:
        size = os.path.getsize(pdf_path)
    except OSError as e:
        raise FileNotFoundError(f"无法访问 PDF 文件: {pdf_path} ({e})") from e
    if size > MAX_PDF_BYTES:
        raise ValueError(
            f"PDF 文件过大（{size} 字节），超过上限 {MAX_PDF_BYTES} 字节，"
            f"已拒绝处理以防内存耗尽。"
        )

    plumber = _get_pdfplumber()
    try:
        with _pdf_process_timeout(PDF_PROCESS_TIMEOUT):
            with plumber.open(pdf_path) as pdf:
                all_text = ""
                for i, page in enumerate(pdf.pages):
                    if i >= MAX_PDF_PAGES:
                        raise ValueError(
                            f"PDF 页数超过上限 {MAX_PDF_PAGES} 页，已拒绝处理以防资源耗尽。"
                        )
                    text = page.extract_text()
                    if text:
                        all_text += text + "\n"
    except _PDFTimeout:
        raise TimeoutError(
            f"PDF 处理超时（>{PDF_PROCESS_TIMEOUT}s），已中止以防资源耗尽。"
        )

    return clean_pdf_text(all_text, journal_name=journal_name, custom_watermark_chars=custom_watermark_chars)


def extract_and_clean(pdf_path, journal_name=None, custom_watermark_chars=None, output_path=None):
    """提取 PDF 文本、清理水印、可选保存到文件。

    Args:
        pdf_path: PDF 文件路径
        journal_name: 期刊名称
        custom_watermark_chars: 自定义水印字符集
        output_path: 输出文件路径（可选）

    Returns:
        清理后的文本
    """
    cleaned = clean_pdf_file(pdf_path, journal_name=journal_name, custom_watermark_chars=custom_watermark_chars)

    if output_path:
        # output_path 属于用户输入，校验其落在 cwd 之内，超出允许范围即拒绝写入
        try:
            safe_out = resolve_safe_output(output_path, base=os.getcwd())
        except ValueError as e:
            raise ValueError(f"输出路径超出允许范围，拒绝写入 — {e}")
        with open(safe_out, "w", encoding="utf-8") as f:
            f.write(cleaned)

    return cleaned


if __name__ == "__main__":
    import argparse
    import sys
    from pathlib import Path

    parser = argparse.ArgumentParser(
        description="清理 PDF 提取文本中的期刊水印字符",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  python clean_pdf_text.py input.pdf -o cleaned.txt\n"
            "  python clean_pdf_text.py input.pdf --journal 'Human Resource Management'\n"
        ),
    )
    parser.add_argument(
        "input",
        help="输入 PDF 文件路径",
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="输出清理后文本路径，默认打印到标准输出",
    )
    parser.add_argument(
        "--journal",
        default=None,
        help="期刊名（用于匹配预定义水印字符集，可选）",
    )
    args = parser.parse_args()

    pdf_path = Path(args.input)
    if not pdf_path.exists():
        print(f"错误：输入文件不存在: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    try:
        cleaned = clean_pdf_file(str(pdf_path), journal_name=args.journal)
    except (ValueError, TimeoutError, OSError, ImportError) as e:
        print(f"错误：处理 PDF 失败 — {e}", file=sys.stderr)
        sys.exit(1)

    if args.output:
        # args.output 属于用户输入，校验其落在 cwd 之内，超出允许范围即拒绝写入
        try:
            out_path = resolve_safe_output(args.output, base=os.getcwd())
        except ValueError as e:
            print(f"错误：输出路径超出允许范围，拒绝写入 — {e}", file=sys.stderr)
            sys.exit(1)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(cleaned)
        print("已清理并写出:", out_path, f"（{len(cleaned)} 字符）")
    else:
        print(cleaned)
