#!/usr/bin/env python3
"""诊断报告生成器：八维度逐项诊断。

维度口径以 `../../peer-review/SKILL.md` 的「诊断八维度」为权威来源。

用法: python diagnosis_report.py --paper 诊断数据.json --output 诊断报告.md
"""
# 确保套件包可导入（包目录在上级目录）
import os, sys
_skill_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _skill_dir not in sys.path:
    sys.path.append(_skill_dir)

SEVERITY_LEVELS = {
    "必须修改": "影响结论可信度或录用/立项，不修改则建议拒稿",
    "强烈建议修改": "重要问题，影响研究质量或印象分",
    "建议修改": "可改进的次要问题，建议但不强制",
    "可选改进": "锦上添花的优化建议",
}

# 诊断八维度（与 ../../peer-review/SKILL.md「诊断八维度」保持一致）
DIAGNOSIS_DIMENSIONS = [
    "选题质量",
    "文献覆盖",
    "理论深度",
    "方法严谨",
    "写作质量",
    "创新程度",
    "图表呈现",
    "逻辑连接",
]

# 期刊论文诊断可选视角（六大维框架，供 build_journal_diagnosis 使用；
# 与上方八维度是两套独立框架，不混用）
JOURNAL_DIMENSIONS = [
    ("一、理论贡献", ["理论对话位置是否清晰", "贡献是否具体（而非口号化）", "是否推进了已有理论或开辟新对话"]),
    ("二、方法论", ["研究设计是否匹配研究问题", "样本和抽样是否合理", "变量测量是否可靠"]),
    ("三、实证证据", ["假设检验是否充分", "结果是否稳健", "效应量是否有意义"]),
    ("四、讨论与启示", ["讨论是否回到文献缺口", "实践启示是否基于研究发现", "局限是否诚实且有意义"]),
    ("五、研究伦理与透明度", ["是否声明伦理审查", "数据是否可获取声明", "分析是否预注册"]),
    ("六、写作质量", ["逻辑链条是否完整", "表述是否准确简洁", "格式是否合规"]),
]


FIELD_ALIASES = {
    "dimension": ["dimension", "维度", "诊断维度", "类别", "模块"],
    "severity": ["severity", "严重程度", "风险等级", "风险", "等级"],
    "description": ["description", "问题描述", "问题", "主要问题", "issue"],
    "suggestion": ["suggestion", "修改建议", "建议", "改进建议", "solution"],
    "location": ["location", "对应位置", "位置", "章节", "段落"],
}


def _issue_value(issue: dict, field: str, default: str = "") -> str:
    """兼容中英文字段名，避免调用方字段不同导致空表。"""
    for key in FIELD_ALIASES.get(field, [field]):
        if key in issue and issue.get(key) not in (None, ""):
            return str(issue.get(key))
    return default


def _normalize_issue(issue: dict) -> dict:
    """规范化诊断问题字段。"""
    sev = _issue_value(issue, "severity", "建议修改")
    # 统一内容严重度至 4 级中文；兼容历史别名（high/medium/low、高/中/低、致命/重大/中等、P0-P3）
    if sev in ["必须改", "P0", "high", "高", "致命"]:
        sev = "必须修改"
    elif sev in ["高优先级", "强烈建议", "P1", "medium", "中", "重大"]:
        sev = "强烈建议修改"
    elif sev in ["中优先级", "一般建议", "P2", "low", "低", "中等"]:
        sev = "建议修改"
    elif sev in ["低优先级", "可选", "P3", "optional"]:
        sev = "可选改进"
    return {
        "dimension": _issue_value(issue, "dimension", "未分类"),
        "severity": sev,
        "description": _issue_value(issue, "description", ""),
        "suggestion": _issue_value(issue, "suggestion", ""),
        "location": _issue_value(issue, "location", ""),
    }


def build_diagnosis_table(issues: list, target_object: str = "", target_level: str = "") -> str:
    """生成诊断问题表（Markdown格式）。

    Args:
        issues: 问题列表，每个为字典：
            - dimension: 诊断维度
            - severity: 严重程度（必须修改/强烈建议修改/建议修改/可选改进）
            - description: 问题描述
            - suggestion: 修改建议
            - location: 对应位置（可选）
            - priority: 修改优先级（可选，自动按严重程度排序）
        target_object: 诊断对象（如"投稿前论文"）
        target_level: 目标层级

    Returns:
        Markdown 格式的诊断报告
    """
    lines = []

    header = "## 诊断报告"
    if target_object:
        header += f"\n**诊断对象**：{target_object}"
    if target_level:
        header += f"  |  **目标层级**：{target_level}"
    lines.append(header + "\n")

    # 问题表
    lines.append("| 维度 | 严重程度 | 问题描述 | 修改建议 | 对应位置 |")
    lines.append("|------|---------|---------|---------|---------|")

    normalized_issues = [_normalize_issue(issue) for issue in issues]
    for issue in normalized_issues:
        sev = issue.get("severity", "建议修改")
        sev_note = SEVERITY_LEVELS.get(sev, "")
        lines.append(
            f"| {issue.get('dimension','')} "
            f"| {sev}（{sev_note}） "
            f"| {issue.get('description','')} "
            f"| {issue.get('suggestion','')} "
            f"| {issue.get('location','')} |"
        )

    # 统计
    severity_counts = {}
    for issue in normalized_issues:
        sev = issue.get("severity", "建议修改")
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

    lines.append("\n### 问题统计\n")
    lines.append("| 严重程度 | 数量 |")
    lines.append("|---------|------|")
    for sev in ["必须修改", "强烈建议修改", "建议修改", "可选改进"]:
        count = severity_counts.get(sev, 0)
        if count > 0:
            lines.append(f"| {sev} | {count} |")

    return "\n".join(lines)


def build_revision_roadmap(issues: list) -> str:
    """生成修改路线图（按优先级排序）。

    Args:
        issues: 同 build_diagnosis_table 的 issues 列表

    Returns:
        Markdown 格式的修改路线图
    """
    severity_order = {"必须修改": 0, "强烈建议修改": 1, "建议修改": 2, "可选改进": 3}
    normalized_issues = [_normalize_issue(issue) for issue in issues]
    sorted_issues = sorted(normalized_issues, key=lambda x: severity_order.get(x.get("severity", "建议修改"), 9))

    lines = ["## 修改路线图\n"]
    for i, issue in enumerate(sorted_issues, 1):
        lines.append(f"### {i}. [{issue.get('severity','')}] {issue.get('dimension','')}\n")
        lines.append(f"- **问题**：{issue.get('description','')}")
        lines.append(f"- **修改建议**：{issue.get('suggestion','')}")
        lines.append(f"- **对应位置**：{issue.get('location','对应位置待补充')}")
        lines.append("")

    return "\n".join(lines)


def build_journal_diagnosis(title: str, journal: str, dimensions: list) -> str:
    """生成期刊论文六大维度诊断框架（Markdown）。

    Args:
        title: 稿件标题
        journal: 目标期刊
        dimensions: 期刊六大维框架的诊断结果列表（对应 JOURNAL_DIMENSIONS），每个为字典：
            - name: 维度名称
            - score: 总体评价（接受/小修/大修/拒稿）
            - findings: 发现的问题列表
            - suggestions: 建议列表

    Returns:
        Markdown 格式的六大维度诊断报告
    """
    lines = []
    lines.append("# 期刊论文诊断报告\n")
    lines.append(f"**稿件**：{title}  |  **目标期刊**：{journal}\n")

    for dim in dimensions:
        lines.append(f"## {dim.get('name', '')}\n")
        lines.append(f"**总体评价**：{dim.get('score', '')}\n")

        findings = dim.get("findings", [])
        if findings:
            lines.append("**发现**：")
            for f in findings:
                lines.append(f"- {f}")
            lines.append("")

        suggestions = dim.get("suggestions", [])
        if suggestions:
            lines.append("**建议**：")
            for s in suggestions:
                lines.append(f"- {s}")
            lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    import argparse
    import json
    import os
    import sys
    from pathlib import Path
    from obhrm_research_base.core.safe_path import resolve_safe_output, safe_open_for_write

    parser = argparse.ArgumentParser(
        description="八维度诊断报告生成器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "--paper 接受两类 JSON：\n"
            "  1) 列表式: [{\"dimension\": \"选题价值\", \"severity\": \"必须修改\", \"description\": \"...\", \"suggestion\": \"...\", \"location\": \"...\"}, ...]\n"
            "  2) 对象式: {\"issues\": [...], \"target_object\": \"投稿前论文\", \"target_level\": \"csci\"}\n"
            "示例:\n"
            "  python diagnosis_report.py --paper 诊断数据.json\n"
            "  python diagnosis_report.py --paper 诊断数据.json --output 诊断报告.md --target-object '投稿前论文'\n"
        ),
    )
    parser.add_argument(
        "--paper", "-i",
        required=True,
        help="诊断数据 JSON 文件（issues 列表或含 issues 的对象）",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="输出 Markdown 报告路径，默认与输入同名 + _diagnosis.md",
    )
    parser.add_argument(
        "--target-object",
        default="",
        help="诊断对象（如 '投稿前论文'）",
    )
    parser.add_argument(
        "--target-level",
        default="",
        help="目标层级（如 csci / ssci / 硕士 / 博士）",
    )
    parser.add_argument(
        "--mode",
        choices=["table", "roadmap", "all"],
        default="all",
        help="输出内容：table=问题表, roadmap=修改路线图, all=两者(默认)",
    )
    args = parser.parse_args()

    paper_path = Path(args.paper)
    if not paper_path.exists():
        print(f"错误：输入文件不存在: {paper_path}", file=sys.stderr)
        sys.exit(1)

    with open(paper_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        issues = data
        target_object = args.target_object
        target_level = args.target_level
    elif isinstance(data, dict):
        issues = data.get("issues", []) or []
        target_object = data.get("target_object", args.target_object)
        target_level = data.get("target_level", args.target_level)
    else:
        print("错误：JSON 顶层应为列表或含 issues 字段的对象", file=sys.stderr)
        sys.exit(1)

    blocks = []
    if args.mode in ("table", "all"):
        blocks.append(build_diagnosis_table(issues, target_object=target_object, target_level=target_level))
    if args.mode in ("roadmap", "all"):
        blocks.append(build_revision_roadmap(issues))
    report = "\n\n".join(b for b in blocks if b)

    if args.output:
        try:
            output_path = str(resolve_safe_output(args.output, base=os.getcwd()))
        except ValueError as e:
            print(f"错误：{e}", file=sys.stderr)
            sys.exit(1)
    else:
        output_path = str(paper_path.with_name(paper_path.stem + "_diagnosis.md"))
    with safe_open_for_write(output_path, base=os.getcwd(), encoding="utf-8") as f:
        f.write(report + "\n")
    print("诊断报告已生成:", output_path, f"（{len(issues)} 条问题）")
