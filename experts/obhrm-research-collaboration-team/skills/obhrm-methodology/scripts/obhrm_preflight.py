#!/usr/bin/env python3
"""OBHRM 交付文本预检（依赖无关，标准库实现）。

对生成的论文 / 基金 / 综述 / 审稿 / 返修文本做确定性文本审计：
- 未关闭占位符（待作者输入 / 待补 / 待核验）
- 超范围 / 无边界强化主张（填补了空白 / 首次证明 / 普遍适用 / 必然导致）
- AI 模板腔（系统梳理 / 充分论证 / 进一步探讨 / 关键作用 / 不言而喻 / 值得注意的是）
- 图题注重复、标题层级跳级
- 编号引用与参考文献条目闭合

本脚本只做确定性文本预检，不验证研究事实、统计正确性、期刊适配或版式渲染。
它与套件既有 `quality_check.py`（AI 痕迹词库）互补：本脚本偏「交付前结构闸门」，
quality_check.py 偏「学术书面语痕迹」。二者不互斥。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

PLACEHOLDER_PATTERNS = [
    r"待作者输入",
    r"\[待办(?::[^\]]*)?\]",
    r"\[待补(?:充|证据|数据|引用)?\]",
    r"待核验",
    r"待补证据",
]

OVERCLAIM_TERMS = [
    "填补了空白",
    "首次证明",
    "完全证明",
    "必然导致",
    "普遍适用",
    "毋庸置疑",
    "unprecedented",
    "proves that",
    "always holds",
    "never fails",
]

AI_SLOP_TERMS = [
    "系统梳理",
    "充分论证",
    "进一步探讨",
    "关键作用",
    "不言而喻",
    "值得注意的是",
    "具有重要意义",
    "it is worth noting that",
    "plays a crucial role",
]


def issue(code: str, severity: str, message: str, line: int | None = None) -> dict:
    item = {"code": code, "severity": severity, "message": message}
    if line is not None:
        item["line"] = line
    return item


def line_number(text: str, start: int) -> int:
    return text.count("\n", 0, start) + 1


def _mask_code(text: str) -> str:
    """把围栏代码块（``` / ~~~ 成对）整体替换为**同长度空白**。

    代码块内的 `# 注释行` 不是 Markdown 标题，示例命令/JSON 也不属于正文表述；
    因此标题层级、空泛词、强化主张、题注等静态检查一律只在「非代码区」进行，
    避免把代码示例误报为正文问题。同长度掩码保证行号与字符偏移完全不变。
    """
    fence = re.compile(r"^[ \t]{0,3}(?:```|~~~)")
    out = []
    in_fence = False
    for line in text.splitlines(keepends=True):
        body = line.rstrip("\r\n")
        toggle = bool(fence.match(body))
        if toggle:
            in_fence = not in_fence
        if toggle or in_fence:
            out.append("".join(ch if ch in "\r\n" else " " for ch in line))
        else:
            out.append(line)
    return "".join(out)


def audit(text: str) -> dict:
    issues: list[dict] = []

    # 先屏蔽围栏代码块（同长度掩码，行号与偏移不变），只在正文区做静态检查
    text = _mask_code(text)

    for pattern in PLACEHOLDER_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            issues.append(issue("PLACEHOLDER", "P0", f"存在未关闭占位符：{match.group(0)}", line_number(text, match.start())))

    for term in OVERCLAIM_TERMS:
        for match in re.finditer(re.escape(term), text, re.IGNORECASE):
            issues.append(issue("OVERCLAIM", "P1", f"可能存在无边界强化主张：{match.group(0)}", line_number(text, match.start())))

    for term in AI_SLOP_TERMS:
        for match in re.finditer(re.escape(term), text, re.IGNORECASE):
            issues.append(issue("VAGUE_LANGUAGE", "P2", f"建议检查空泛或模板化表达：{match.group(0)}", line_number(text, match.start())))

    headings = []
    for idx, line in enumerate(text.splitlines(), start=1):
        match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if match:
            headings.append((idx, len(match.group(1)), match.group(2)))
    for previous, current in zip(headings, headings[1:]):
        if current[1] > previous[1] + 1:
            issues.append(issue("HEADING_JUMP", "P2", f"标题层级从 H{previous[1]} 跳到 H{current[1]}：{current[2]}", current[0]))

    caption_patterns = (
        ("图", r"(?im)^\s*(?:图|Fig(?:ure)?\.?)\s*([A-Za-z]?\d+)\s*[：:. ]"),
        ("表", r"(?im)^\s*(?:表|Table)\s*([A-Za-z]?\d+)\s*[：:. ]"),
    )
    for kind, pattern in caption_patterns:
        captions = re.findall(pattern, text)
        duplicates = [value for value, count in Counter(captions).items() if count > 1]
        if duplicates:
            issues.append(issue("DUPLICATE_CAPTION", "P2", f"{kind}题注编号可能重复：{', '.join(sorted(duplicates))}"))

    cn_citations = set(re.findall(r"\[(\d+)\]", text))
    refs_match = re.search(r"(?im)^#{0,6}\s*(参考文献|references)\s*$", text)
    if cn_citations and refs_match:
        body_citations = set(re.findall(r"\[(\d+)\]", text[: refs_match.start()]))
        ref_numbers = set(re.findall(r"(?m)^\s*\[(\d+)\]", text[refs_match.end() :]))
        missing_refs = sorted(body_citations - ref_numbers, key=int)
        uncited_refs = sorted(ref_numbers - body_citations, key=int)
        if missing_refs:
            issues.append(issue("MISSING_REFERENCE", "P0", f"正文引用缺少参考文献条目：{', '.join(missing_refs)}"))
        if uncited_refs:
            issues.append(issue("UNCITED_REFERENCE", "P1", f"参考文献未在正文引用：{', '.join(uncited_refs)}"))

    severity_counts = Counter(item["severity"] for item in issues)
    return {
        "status": "FAIL" if severity_counts["P0"] else "WARN" if issues else "PASS",
        "summary": {"P0": severity_counts.get("P0", 0), "P1": severity_counts.get("P1", 0), "P2": severity_counts.get("P2", 0)},
        "issues": issues,
        "limitations": [
            "只做确定性文本预检，不验证研究事实、统计分析、期刊适配或版式渲染。",
            "围栏代码块（``` / ~~~）整体屏蔽后再检查，代码注释与示例命令不会被误报为标题或空泛表达。",
            "图表检查只识别独立成行的题注，正文交叉引用与复杂排版仍需人工复核。",
            "与 quality_check.py（AI 痕迹词库）互补，不替代其学术书面语检测。",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit an OBHRM deliverable Markdown or text file.")
    parser.add_argument("input", type=Path)
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--strict", action="store_true", help="Treat P1/P2 warnings as failure.")
    args = parser.parse_args()

    if not args.input.is_file():
        print(f"Input file not found: {args.input}", file=sys.stderr)
        return 2
    text = args.input.read_text(encoding="utf-8")
    result = audit(text)

    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Status: {result['status']}")
        print(f"P0={result['summary']['P0']} P1={result['summary']['P1']} P2={result['summary']['P2']}")
        for item in result["issues"]:
            location = f" line {item['line']}" if "line" in item else ""
            print(f"[{item['severity']}] {item['code']}{location}: {item['message']}")
        for note in result["limitations"]:
            print(f"LIMIT: {note}")

    if result["summary"]["P0"]:
        return 1
    if args.strict and result["issues"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
