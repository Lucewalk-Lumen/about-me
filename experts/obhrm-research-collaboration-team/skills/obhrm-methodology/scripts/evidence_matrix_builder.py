#!/usr/bin/env python3
"""文献证据矩阵生成器。

用法示例见 `if __name__ == '__main__':` 块。
"""



# 确保套件包可导入（包目录在上级目录）
import os, sys
_skill_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _skill_dir not in sys.path:
    sys.path.append(_skill_dir)
def build_evidence_matrix(literatures: list) -> str:
    """生成文献证据矩阵（Markdown表格）。

    Args:
        literatures: 文献条目列表，每个条目为字典，支持以下字段：
            - id: 编号（E1、E2、E3 等唯一编号）
            - level: 证据等级（A/B/C）
            - type: 文献类型（理论根基/近五年前沿/方法测量/政策实践）
            - author_year: 作者年份
            - title: 完整题名
            - source: 来源期刊/出版社
            - constructs: 核心构念
            - sample: 研究对象/样本
            - method: 方法
            - finding: 关键发现
            - limitation: 不足或边界
            - embedding: 本研究嵌入位置
            - doi: DOI/URL

    Returns:
        Markdown 格式的证据矩阵表格
    """
    if not literatures:
        return "（暂无文献条目）"

    # 检查是否有A/B/C分级
    has_level = any(lit.get("level") for lit in literatures)

    lines = []
    lines.append("## 文献证据矩阵\n")

    if has_level:
        lines.append(
            "| 编号 | 等级 | 类型 | 作者/年份 | 题名 | 来源 | 核心构念 | 样本 | 方法 | 关键发现 | 不足/边界 | 嵌入位置 | DOI |"
        )
        lines.append(
            "|------|------|------|----------|------|------|---------|------|------|---------|----------|---------|-----|"
        )
        for lit in literatures:
            lines.append(
                f"| {lit.get('id','')} | {lit.get('level','')} | {lit.get('type','')} "
                f"| {lit.get('author_year','')} | {lit.get('title','')} | {lit.get('source','')} "
                f"| {lit.get('constructs','')} | {lit.get('sample','')} | {lit.get('method','')} "
                f"| {lit.get('finding','')} | {lit.get('limitation','')} "
                f"| {lit.get('embedding','')} | {lit.get('doi','')} |"
            )
    else:
        lines.append(
            "| 编号 | 类型 | 作者/年份 | 题名 | 来源 | 核心构念 | 样本 | 方法 | 关键发现 | 不足/边界 | 嵌入位置 | DOI |"
        )
        lines.append(
            "|------|------|----------|------|------|---------|------|------|---------|----------|---------|-----|"
        )
        for lit in literatures:
            lines.append(
                f"| {lit.get('id','')} | {lit.get('type','')} "
                f"| {lit.get('author_year','')} | {lit.get('title','')} | {lit.get('source','')} "
                f"| {lit.get('constructs','')} | {lit.get('sample','')} | {lit.get('method','')} "
                f"| {lit.get('finding','')} | {lit.get('limitation','')} "
                f"| {lit.get('embedding','')} | {lit.get('doi','')} |"
            )

    return "\n".join(lines)


def build_literature_chain(
    chain_id: int,
    theme: str,
    existing: list,
    recent_advance: str,
    gap: str,
    this_study: str,
    core_refs: list = None,
    pending: list = None,
) -> str:
    """生成单条文献链（Markdown格式）。

    Args:
        chain_id: 文献链编号
        theme: 主题名称
        existing: 已有研究代表文献列表（作者年份）
        recent_advance: 近五年推进描述
        gap: 仍然不足
        this_study: 本研究推进
        core_refs: A/B级核心文献列表（可选）
        pending: C级待核验线索（可选）

    Returns:
        Markdown 格式的文献链
    """
    lines = []
    lines.append(f"### 文献链{chain_id}：{theme}\n")
    lines.append(f"- **已有研究**：{'；'.join(existing)}")
    lines.append(f"- **近五年推进**：{recent_advance}")
    lines.append(f"- **仍然不足**：{gap}")
    lines.append(f"- **本研究推进**：{this_study}")

    if core_refs:
        lines.append(f"- **可引用核心证据**：{'；'.join(core_refs)}")
    if pending:
        lines.append(f"- **待核验线索**：{'；'.join(pending)}")

    return "\n".join(lines)


def build_keyword_matrix(constructs: dict) -> str:
    """生成构念词表与关键词矩阵。

    Args:
        constructs: 构念字典，如 {
            "反向师徒关系": {
                "en_standard": "reverse mentoring",
                "en_extended": ["reciprocal mentoring", "upward mentoring"],
                "cn_standard": "反向师徒关系",
                "cn_extended": ["逆向导师制", "代际学习"]
            },
            # 继续添加更多文献记录
        }

    Returns:
        Markdown 格式的关键词矩阵
    """
    lines = []
    lines.append("## 构念词表与关键词矩阵\n")
    lines.append("| 构念 | 英文标准术语 | 英文扩展词 | 中文标准术语 | 中文扩展词 |")
    lines.append("|------|------------|-----------|------------|-----------|")
    for cn_name, terms in constructs.items():
        en_std = terms.get("en_standard", "")
        en_ext = "；".join(terms.get("en_extended", []))
        cn_std = terms.get("cn_standard", cn_name)
        cn_ext = "；".join(terms.get("cn_extended", []))
        lines.append(f"| {cn_name} | {en_std} | {en_ext} | {cn_std} | {cn_ext} |")

    return "\n".join(lines)


def build_search_matrix(searches: list) -> str:
    """生成检索式矩阵。

    Args:
        searches: 检索式列表，每个为字典 {type, query, purpose, results}
    """
    lines = []
    lines.append("## 检索式矩阵\n")
    lines.append("| 检索类型 | 检索式 | 目的 | 结果数 |")
    lines.append("|---------|--------|------|--------|")
    for s in searches:
        lines.append(f"| {s.get('type','')} | {s.get('query','')} | {s.get('purpose','')} | {s.get('results','')} |")
    return "\n".join(lines)


if __name__ == "__main__":
    import argparse
    import json
    import os
    import sys
    from pathlib import Path
    from obhrm_research_base.core.safe_path import resolve_safe_output

    parser = argparse.ArgumentParser(
        description="文献证据矩阵生成器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "--refs 接受文献条目列表 JSON（每个条目支持 id/level/type/author_year/title/source/constructs/\n"
            "sample/method/finding/limitation/embedding/doi 等字段）。\n"
            "示例:\n"
            "  python evidence_matrix_builder.py --refs references.json\n"
            "  python evidence_matrix_builder.py --refs references.json --output 证据矩阵.md\n"
        ),
    )
    parser.add_argument(
        "--refs", "-i",
        required=True,
        help="文献条目 JSON 文件（列表）",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="输出 Markdown 路径，默认打印到标准输出",
    )
    args = parser.parse_args()

    refs_path = Path(args.refs)
    if not refs_path.exists():
        print(f"错误：输入文件不存在: {refs_path}", file=sys.stderr)
        sys.exit(1)

    with open(refs_path, "r", encoding="utf-8") as f:
        literatures = json.load(f)

    if not isinstance(literatures, list):
        print("错误：--refs 指向的 JSON 应为文献条目列表", file=sys.stderr)
        sys.exit(1)

    matrix = build_evidence_matrix(literatures)

    if args.output:
        try:
            safe_output = resolve_safe_output(args.output, base=os.getcwd())
        except ValueError as e:
            print(f"错误：{e}", file=sys.stderr)
            sys.exit(1)
        with open(str(safe_output), "w", encoding="utf-8") as f:
            f.write(matrix + "\n")
        print("证据矩阵已生成:", safe_output, f"（{len(literatures)} 条文献）")
    else:
        print(matrix)
