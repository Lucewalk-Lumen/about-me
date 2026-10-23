#!/usr/bin/env python3
# 确保套件包可导入（包目录在上级目录）
import os, sys
_skill_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _skill_dir not in sys.path:
    sys.path.append(_skill_dir)


"""
quality_check.py
OBHRM研究套件 — 交付质量自动检查脚本

新功能：
- 支持配置文件自定义风险词库
- 增强的引用格式检查（APA 7.0）
- JSON 格式报告输出
- 批量处理优化
- 详细的修复建议
"""

from obhrm_research_base.core._common_init import HAVE_COMMON, init_logger
from obhrm_research_base.core.safe_path import resolve_safe_output

logger = init_logger()

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# 默认风险词库（从 config_manager 获取，避免重复定义）
# 如果 config_manager 不可用，使用此内置副本
_DEFAULT_RISK_WORDS_BACKUP: Dict[str, List[str]] = {
    "AI痕迹": [
        "值得注意的是", "不难发现", "显而易见", "综上所述",
        "总而言之", "不可否认的是", "毫无疑问", "众所周知",
        "在当今社会", "随着科技的进步", "总之", "可以说",
        "从某种意义上说", "众所周知的是", "显而易见的是",
        "需要指出的是", "不容忽视的是",
        "系统梳理", "系统整理", "系统分析", "系统阐述", "系统介绍",
        "充分论证", "充分说明", "充分体现", "充分展现",
        "进一步探讨", "进一步研究", "进一步分析", "进一步说明", "进一步阐述",
        "关键作用", "关键因素", "关键变量", "重要作用", "重要因素",
        "值得注意的是", "综上所述", "由此可见", "不难看出",
        "§",
    ],
    "夸张表述": [
        "首次", "开创性", "革命性", "颠覆性",
        "里程碑", "绝无仅有", "前所未有", "无与伦比",
        "填补空白", "世界第一", "国际领先",
        "填补了国内外空白", "具有里程碑意义", "重大突破",
    ],
    "不规范用语": [
        "笔者", "本人", "我们", "笔者认为", "我们认为",
        "本文认为", "不难发现", "众所周知", "显而易见",
        "从某种意义上",
    ],
    "敏感词": [
        "数据造假", "篡改", "抄袭", "一稿多投",
        "重复发表", "虚假署名", "编造文献",
        "虚构审稿意见", "虚构项目基础",
    ],
}


class QualityChecker:
    """质量检查器"""

    def __init__(self, config_file: Optional[str] = None):
        # 优先从 config_manager 获取风险词库，避免重复定义
        if HAVE_COMMON:
            try:
                from obhrm_research_base.core.config_manager import get_config

                cfg = get_config()
                # ConfigManager.get 支持点号分隔的嵌套键（如 quality_check.risk_words）
                risk_cfg = cfg.get("quality_check.risk_words", {})
                if risk_cfg:
                    self.risk_words: Dict[str, List[str]] = risk_cfg.copy()
                else:
                    self.risk_words = _DEFAULT_RISK_WORDS_BACKUP.copy()
            except ImportError:
                self.risk_words = _DEFAULT_RISK_WORDS_BACKUP.copy()
        else:
            self.risk_words = _DEFAULT_RISK_WORDS_BACKUP.copy()

        if config_file and Path(config_file).exists():
            self.load_config(config_file)

    def load_config(self, config_file: str) -> None:
        """加载自定义配置文件"""
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
                if "risk_words" in config:
                    self.risk_words.update(config["risk_words"])
        except Exception as e:
            print(f"警告：无法加载配置文件 {config_file}: {e}")

    def check_file(self, filepath: str, base_dir: str = ".") -> Dict[str, Any]:
        """检查单个文件"""
        results = {
            "file": filepath,
            "stats": None,
            "risks": [],
            "dead_links": [],
            "empty_headers": [],
            "code_blocks": [],
            "ref_issues": [],
            "apa_issues": [],
            "passed": True,
            "errors": [],
        }

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                text = f.read()
        except FileNotFoundError:
            results["errors"].append(f"文件不存在: {filepath}")
            results["passed"] = False
            return results
        except UnicodeDecodeError:
            results["errors"].append(f"文件编码错误: {filepath}")
            results["passed"] = False
            return results
        except Exception as e:
            results["errors"].append(f"读取文件失败: {e}")
            results["passed"] = False
            return results

        fname = Path(filepath).name
        results["stats"] = self.count_text_stats(text)
        results["risks"] = self.check_risk_words(text, fname)
        results["dead_links"] = self.check_dead_links(text, fname, base_dir)
        results["empty_headers"] = self.check_empty_headers(text, fname)
        results["code_blocks"] = self.check_code_blocks(text, fname)
        results["ref_issues"] = self.check_references(text, fname)
        results["apa_issues"] = self.check_apa_format(text, fname)

        # 判断通过与否：死链 / 空标题 / 未闭合代码块 / APA 格式问题 / 参考文献缺失 /
        # 致命风险词 任一存在即判不通过（apa_issues、ref_issues 一并纳入放行判定）。
        if (
            results["dead_links"]
            or results["empty_headers"]
            or results["code_blocks"]
            or results["apa_issues"]
            or results["ref_issues"]
            or any(r["level"] == "致命" for r in results["risks"])
        ):
            results["passed"] = False

        return results

    def count_text_stats(self, text: str) -> Dict[str, int]:
        """统计文本字数信息"""
        lines = text.splitlines()
        paragraphs = [l for l in lines if l.strip()]

        cjk_chars = len(re.findall("[\u4e00-\u9fff]", text))
        english_words = len(re.findall(r"[a-zA-Z]{2,}", text))
        total_chars = len(text)
        effective_words = cjk_chars + english_words

        return {
            "cjk_chars": cjk_chars,
            "english_words": english_words,
            "effective_words": effective_words,
            "total_chars": total_chars,
            "paragraphs": len(paragraphs),
            "lines": len(lines),
        }

    def check_risk_words(self, text: str, file_name: str = "") -> List[Dict[str, Any]]:
        """检查风险词"""
        findings = []
        for category, words in self.risk_words.items():
            for word in words:
                matches = list(re.finditer(re.escape(word), text))
                for m in matches:
                    start = max(0, m.start() - 30)
                    end = min(len(text), m.end() + 30)
                    context = text[start:end].replace("\n", " ")
                    findings.append(
                        {
                            "file": file_name,
                            "category": category,
                            "level": self.get_risk_level(category),
                            "word": word,
                            "position": m.start(),
                            "context": context,
                            "suggestion": self.get_fix_suggestion(word),
                        }
                    )
        return findings

    def get_risk_level(self, category: str) -> str:
        """获取风险等级"""
        level_map = {"AI痕迹": "提示", "夸张表述": "警告", "不规范用语": "提示", "敏感词": "致命"}
        return level_map.get(category, "提示")

    def get_fix_suggestion(self, word: str) -> str:
        """获取修复建议"""
        suggestions = {
            "值得注意的是": "直接陈述事实，删除过渡语",
            "综上所述": "用具体结论替代套话",
            "填补空白": "具体说明推进了什么研究",
            "笔者": "改为客观表述或直接删除",
        }
        return suggestions.get(word, "建议删除或替换")

    def check_dead_links(self, text: str, file_name: str = "", base_dir: str = ".") -> List[Dict[str, str]]:
        """检查死链接"""
        dead = []
        # 检查 references/ 引用
        refs = re.findall(r"`references/([^`]+\.md)`", text)
        for ref in refs:
            full = Path(base_dir) / "references" / ref
            if not full.exists():
                dead.append({"file": file_name, "missing": f"references/{ref}"})
        return dead

    def check_empty_headers(self, text: str, file_name: str = "") -> List[Dict[str, Any]]:
        """检查空标题"""
        empty = []
        for i, line in enumerate(text.splitlines(), 1):
            if re.match(r"^#{1,6}\s*$", line):
                empty.append({"file": file_name, "line": i})
        return empty

    def check_code_blocks(self, text: str, file_name: str = "") -> List[Dict[str, Any]]:
        """检查未闭合代码块"""
        code_delims = text.count("```")
        if code_delims % 2 != 0:
            return [{"file": file_name, "count": code_delims}]
        return []

    def check_references(self, text: str, file_name: str = "") -> List[Dict[str, Any]]:
        """检查参考文献格式问题"""
        issues = []
        # 检测常见学术引用格式：[1]、[1,2,3]、(Author, 2020)、[^1] 等
        cite_patterns = re.findall(
            r"\[\d+(?:[,，]\s*\d+)*\]"  # [1] 或 [1,2,3]
            r"|\([A-Z][a-z]+.*?\d{4}[a-z]?\)"  # (Author et al., 2020)
            r"|\[\^?\d+\]"  # [^1] 脚注引用
            r"|（[^）]+\d{4}[^）]*）",  # 中文括号引用（作者，年份）
            text,
        )
        if len(cite_patterns) > 15 and "参考文献" not in text and "References" not in text:
            issues.append({"file": file_name, "issue": "引用较多（>15）但未见到参考文献列表，请确认已附参考文献"})
        return issues

    def check_apa_format(self, text: str, file_name: str = "") -> List[Dict[str, Any]]:
        """检查 APA 格式问题"""
        issues = []
        # 检查中文引用的常见错误：仅当括号内使用「半角逗号」或缺少分隔符时判定为
        # 格式问题。正确格式「（作者，年份）」含全角逗号，不应被误报。
        if re.search(r"（[^）]*,\s*\d{4}）", text):
            issues.append({"file": file_name, "issue": "中文引用请使用全角逗号：（作者，年份）格式，当前疑似使用半角逗号"})
        return issues

    def format_report(
        self, results_list: List[Dict[str, Any]], threshold_cjk: int = 2000, output_format: str = "text"
    ) -> str:
        """格式化检查报告"""
        if output_format == "json":
            return json.dumps(results_list, ensure_ascii=False, indent=2)

        # 文本格式
        lines = []
        lines.append("=" * 60)
        lines.append("OBHRM 交付质量检查报告")
        lines.append("=" * 60)

        total_files = len(results_list)
        passed = sum(1 for r in results_list if r["passed"])

        lines.append(f"\n检查文件数: {total_files}")
        lines.append(f"通过: {passed} / 未通过: {total_files - passed}")

        for result in results_list:
            lines.append(f"\n{'─' * 60}")
            lines.append(f"文件: {Path(result['file']).name}")

            if result["stats"]:
                s = result["stats"]
                lines.append(
                    f"  中文字符: {s['cjk_chars']} | 英文单词: {s['english_words']} | 等效字数: {s['effective_words']}"
                )
                if s["cjk_chars"] < threshold_cjk and s["cjk_chars"] > 500:
                    lines.append(f"  [!] 中文字符数({s['cjk_chars']})偏低，建议达到 {threshold_cjk}+")

            if result["risks"]:
                lines.append("\n  风险词检测:")
                by_level = {}
                for r in result["risks"]:
                    by_level.setdefault(r["level"], []).append(r)
                for level in ["致命", "警告", "提示"]:
                    if level in by_level:
                        lines.append(f"    [{level}] {len(by_level[level])} 处")
                        for item in by_level[level][:3]:
                            lines.append(f"      - {item['category']}: '{item['word']}'")
                            lines.append(f"        建议: {item['suggestion']}")

            if result["apa_issues"]:
                lines.append("\n  [!] APA格式问题:")
                for issue in result["apa_issues"]:
                    lines.append(f"    - {issue['issue']}")

            if result["errors"]:
                lines.append("\n  [X] 错误:")
                for e in result["errors"]:
                    lines.append(f"    - {e}")

            if result["passed"] and not result["risks"]:
                lines.append("  [OK] 通过")
            elif result["passed"]:
                lines.append("  ○ 通过（有风险提示）")
            else:
                lines.append("  [X] 未通过")

        lines.append(f"\n{'=' * 60}")
        return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="OBHRM交付质量检查")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--input", "-i", help="单个输入文件（.md/.txt）")
    group.add_argument("--dir", "-d", help="目录路径，递归检查")
    parser.add_argument("--recursive", "-r", action="store_true", help="递归检查子目录")
    parser.add_argument("--risk-words", action="store_true", help="启用风险词检测")
    parser.add_argument("--stats", action="store_true", help="输出字数统计")
    parser.add_argument("--output", "-o", help="输出报告文件路径")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="输出格式")
    parser.add_argument("--base-dir", default=".", help="查找引用的基准目录")
    parser.add_argument("--threshold", type=int, default=2000, help="中文字符数阈值")
    parser.add_argument("--config", help="自定义配置文件（JSON格式）")

    args = parser.parse_args()

    checker = QualityChecker(args.config)
    results = []

    if args.input:
        if not Path(args.input).exists():
            print(f"错误：文件不存在: {args.input}")
            sys.exit(1)
        results.append(checker.check_file(args.input, args.base_dir))

    elif args.dir:
        target = Path(args.dir)
        if not target.exists():
            print(f"错误：目录不存在: {args.dir}")
            sys.exit(1)

        pattern = "**/*.md" if args.recursive else "*.md"
        for fpath in target.glob(pattern):
            results.append(checker.check_file(str(fpath), args.base_dir))

    if not results:
        print("未找到可检查的文件")
        return

    report = checker.format_report(results, args.threshold, args.format)
    print(report)

    if args.output:
        # args.output 属于用户输入，校验其落在 cwd 之内，超出允许范围即拒绝写入
        try:
            out_path = resolve_safe_output(args.output, base=os.getcwd())
        except ValueError as e:
            print(f"错误：输出路径超出允许范围，拒绝写入 — {e}", file=sys.stderr)
            sys.exit(1)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"\n报告已保存: {out_path}")


if __name__ == "__main__":
    main()
