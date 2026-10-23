#!/usr/bin/env python3
"""
thesis-mentor 技能审计脚本

功能：
  1. 检查 SKILL.md frontmatter 完整性
  2. 检查 references 目录文件完整性
  3. 检查虚构文献残留（示例作者名、假引用）
  4. 检查"HR"缩写残留
  5. 统计文件规模（行数、字符、估算 token）
  6. 检查版本号一致性
  7. 检查内部指令泄露（如"去AI味"等在输出中暴露）
  8. 检查 UTF-8 编码和 CRLF 行尾

用法：
  python3 scripts/audit.py

退出码：
  0 = 全部通过
  1 = 发现问题（需修复）
"""

import os
import re
import sys

# === 配置 ===
SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL_FILE = os.path.join(SKILL_DIR, "SKILL.md")
REFERENCES_DIR = os.path.join(SKILL_DIR, "references")

# 虚构文献示例作者名（这些只应出现在 thesis-structure-guide.md 的示例段落，不应出现在其他文件）
FAKE_AUTHORS = ["张明", "李华", "王芳", "赵伟", "刘强", "陈静", "李明", "王伟", "张伟", "Price", "Hom", "Smith", "Johnson"]

# 不应出现在任何 reference 文件正文中的内容（只应出现在 SKILL.md 的说明里）
INTERNAL_TERMS = [
    "去AI味",
    "AI痕迹",
    "查重",
    "降重",
    "虚构文献",
    "编造文献",
    "编造数据",
]

# 参考文件清单
REQUIRED_REFS = [
    "topic-evaluation-criteria.md",
    "literature-review-guide.md",
    "management-topic-bank.md",
    "writing-pitfalls-and-common-errors.md",
    "output-templates.md",
    "thesis-structure-guide.md",
]

issues = []
warnings = []


def log_issue(msg):
    issues.append(f"  [ERROR] {msg}")


def log_warning(msg):
    warnings.append(f"  [WARN]  {msg}")


def check_frontmatter():
    """检查 SKILL.md frontmatter"""
    if not os.path.exists(SKILL_FILE):
        log_issue(f"SKILL.md 不存在: {SKILL_FILE}")
        return

    with open(SKILL_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    # 检查 frontmatter 存在
    if not content.startswith("---"):
        log_issue("SKILL.md 缺少 frontmatter (---)")
        return

    # 提取 YAML 块
    try:
        end = content.index("---", 3)
        yaml_block = content[3:end].strip()
    except ValueError:
        log_issue("SKILL.md frontmatter 未正确闭合")
        return

    # 检查必填字段（agent_created 可选，release 包中不应包含）
    for field in ["name:", "version:", "description:"]:
        if field not in yaml_block:
            log_issue(f"SKILL.md frontmatter 缺少字段: {field}")

    # 提取版本号（支持 "4.0.0" 和 4.0.0 两种格式）
    version_match = re.search(r'version:\s*"?([\d.]+)"?', yaml_block)
    if version_match:
        version = version_match.group(1)
        # 检查版本号是否与版本历史一致
        if f"v{version}" not in content:
            log_issue(f"SKILL.md 版本号 v{version} 与版本历史不一致")
    else:
        log_issue("SKILL.md frontmatter 无法提取版本号")


def check_references_completeness():
    """检查参考文件是否完整"""
    for ref in REQUIRED_REFS:
        path = os.path.join(REFERENCES_DIR, ref)
        if not os.path.exists(path):
            log_issue(f"参考文件缺失: references/{ref}")
        else:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            if len(content.strip()) < 500:
                log_warning(f"references/{ref} 内容过短（<500字符），可能不完整")


def check_fictional_citations():
    """检查虚构文献残留"""
    for root, dirs, files in os.walk(SKILL_DIR):
        for f in files:
            if not f.endswith(".md"):
                continue
            path = os.path.join(root, f)
            rel = os.path.relpath(path, SKILL_DIR)

            with open(path, "r", encoding="utf-8") as fh:
                content = fh.read()
                lines = content.split("\n")

            in_code_block = False
            for i, line in enumerate(lines, 1):
                # 跟踪代码块状态
                if line.strip().startswith("```"):
                    in_code_block = not in_code_block
                    continue

                for author in FAKE_AUTHORS:
                    if author in line:
                        # thesis-structure-guide.md 只在代码块内允许虚构作者
                        if "thesis-structure-guide" in rel:
                            if not in_code_block:
                                log_issue(f"{rel} L{i}: 发现虚构文献作者名'{author}'（在代码块外，仅代码块内允许）")
                        else:
                            log_issue(f"{rel} L{i}: 发现虚构文献作者名'{author}'（不应在非示例文件中出现）")


def check_hr_abbreviation():
    """检查'HR'缩写残留"""
    for root, dirs, files in os.walk(SKILL_DIR):
        for f in files:
            if not f.endswith(".md"):
                continue
            path = os.path.join(root, f)
            rel = os.path.relpath(path, SKILL_DIR)

            with open(path, "r", encoding="utf-8") as fh:
                content = fh.read()
                lines = content.split("\n")

            for i, line in enumerate(lines, 1):
                # 排除文件名中的 hr- 前缀
                if f == "SKILL.md" and line.startswith("name:"):
                    continue
                # 匹配 "HR" 作为独立单词（前后有边界）
                if re.search(r'\bHR\b', line):
                    log_issue(f"{rel} L{i}: 发现'HR'缩写残留（应使用全称）")


def check_internal_term_leakage():
    """检查内部指令是否泄露到用户可见内容"""
    for root, dirs, files in os.walk(SKILL_DIR):
        for f in files:
            if not f.endswith(".md"):
                continue
            path = os.path.join(root, f)
            rel = os.path.relpath(path, SKILL_DIR)

            with open(path, "r", encoding="utf-8") as fh:
                content = fh.read()
                lines = content.split("\n")

            for i, line in enumerate(lines, 1):
                for term in INTERNAL_TERMS:
                    if term in line:
                        # SKILL.md 允许有这些术语（用于指令约束）
                        if rel == "SKILL.md":
                            continue
                        # 其他 reference 文件不应出现这些术语
                        log_warning(f"{rel} L{i}: 发现内部术语'{term}'（确认是否应出现在用户可见内容中）")


def check_encoding_and_line_endings():
    """检查 UTF-8 和 LF 行尾"""
    for root, dirs, files in os.walk(SKILL_DIR):
        for f in files:
            if not f.endswith(".md"):
                continue
            path = os.path.join(root, f)
            rel = os.path.relpath(path, SKILL_DIR)

            with open(path, "rb") as fh:
                raw = fh.read()

            # 检查 CRLF
            if b"\r\n" in raw:
                log_warning(f"{rel}: 包含 CRLF 行尾（建议改为 LF）")

            # 检查非 UTF-8 字符（简单检查 BOM）
            if raw.startswith(b"\xef\xbb\xbf"):
                log_warning(f"{rel}: 包含 UTF-8 BOM（建议去掉）")


def check_word_count_consistency():
    """检查 SKILL.md 与 thesis-structure-guide.md 各章字数口径一致性"""
    skill_path = os.path.join(SKILL_DIR, "SKILL.md")
    paper_path = os.path.join(REFERENCES_DIR, "thesis-structure-guide.md")

    if not os.path.exists(skill_path) or not os.path.exists(paper_path):
        return

    with open(skill_path, "r", encoding="utf-8") as f:
        skill_content = f.read()
    with open(paper_path, "r", encoding="utf-8") as f:
        paper_content = f.read()

    # 提取章节字数范围（匹配：一、章节名（1500-2000字）或（约 1500-2000 字））
    pattern = r'[一二三四五]、[^（]*（(?:约\s*)?(\d+)-(\d+)\s*字）'

    skill_matches = re.findall(pattern, skill_content)
    paper_matches = re.findall(pattern, paper_content)

    if len(skill_matches) < 5 or len(paper_matches) < 5:
        log_warning("无法完整提取五章字数范围，请检查格式")
        return

    cn_nums = ["一", "二", "三", "四", "五"]
    for i, (s_match, p_match) in enumerate(zip(skill_matches[:5], paper_matches[:5])):
        if s_match != p_match:
            log_issue(
                f"第{cn_nums[i]}章字数不一致："
                f"SKILL.md={s_match[0]}-{s_match[1]}字，"
                f"thesis-structure-guide.md={p_match[0]}-{p_match[1]}字"
            )


def check_file_size():
    """统计文件规模"""
    total_chars = 0
    total_lines = 0

    print("\n  [统计] 文件规模统计:")
    print(f"  {'文件':<50} {'行数':>8} {'字符':>8} {'~tokens':>8}")
    print(f"  {'-'*50} {'-'*8} {'-'*8} {'-'*8}")

    for root, dirs, files in os.walk(SKILL_DIR):
        for f in sorted(files):
            if not f.endswith(".md"):
                continue
            path = os.path.join(root, f)
            rel = os.path.relpath(path, SKILL_DIR)

            with open(path, "r", encoding="utf-8") as fh:
                content = fh.read()

            lines = len(content.split("\n"))
            chars = len(content)
            tokens = chars // 4
            total_chars += chars
            total_lines += lines

            print(f"  {rel:<50} {lines:>8} {chars:>8} {tokens:>8}")

    print(f"  {'-'*50} {'-'*8} {'-'*8} {'-'*8}")
    print(f"  {'总计':<50} {total_lines:>8} {total_chars:>8} {total_chars//4:>8}")

    # 检查 SKILL.md 是否过长（>5000字符建议精简）
    skill_path = os.path.join(SKILL_DIR, "SKILL.md")
    if os.path.exists(skill_path):
        with open(skill_path, "r", encoding="utf-8") as f:
            skill_chars = len(f.read())
        if skill_chars > 5000:
            log_warning(f"SKILL.md 字符数 {skill_chars}，建议精简至 5000 以下（减少 token 消耗）")


def main():
    print("=" * 60)
    print("  thesis-mentor 技能审计")
    print("=" * 60)

    print("\n  [1/7] 检查 frontmatter...")
    check_frontmatter()

    print("  [2/7] 检查参考文件完整性...")
    check_references_completeness()

    print("  [3/7] 检查虚构文献残留...")
    check_fictional_citations()

    print("  [4/7] 检查'HR'缩写残留...")
    check_hr_abbreviation()

    print("  [5/7] 检查内部术语泄露...")
    check_internal_term_leakage()

    print("  [6/7] 检查编码和行尾...")
    check_encoding_and_line_endings()

    print("  [7/7] 检查字数口径一致性...")
    check_word_count_consistency()

    # 文件规模统计
    check_file_size()

    # 输出结果
    print("\n" + "=" * 60)
    if issues:
        print(f"  发现 {len(issues)} 个错误，需修复:")
        for issue in issues:
            print(issue)
    else:
        print("  未发现错误")

    if warnings:
        print(f"\n  发现 {len(warnings)} 个警告，建议关注:")
        for warning in warnings:
            print(warning)
    else:
        print("  无警告")

    print("=" * 60)

    sys.exit(1 if issues else 0)


if __name__ == "__main__":
    main()
