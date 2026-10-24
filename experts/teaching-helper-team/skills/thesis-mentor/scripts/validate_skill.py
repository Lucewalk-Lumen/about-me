#!/usr/bin/env python3
"""
validate_skill.py — 论文辅导技能包完整性验证

用法：
    python validate_skill.py --skill-dir /path/to/thesis-mentor
    python validate_skill.py --skill-dir .
"""

from _bootstrap import init_logger

logger = init_logger()

import argparse
import re
import sys
from pathlib import Path
from typing import List, Tuple


class SkillValidator:
    def __init__(self, skill_dir: str):
        self.skill_dir = Path(skill_dir)
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def validate_structure(self) -> bool:
        print(" 检查目录结构...")
        # 本技能为 LLM 驱动，工作流由 SKILL.md + references/ 承载，不需要 Python 框架层。
        required_dirs = ["references", "scripts", "templates"]
        # 本技能无必需第三方依赖，故不再要求 requirements 清单。
        required_files = ["SKILL.md"]
        for d in required_dirs:
            if not (self.skill_dir / d).exists():
                self.errors.append(f"缺失目录: {d}/")
        for f in required_files:
            if not (self.skill_dir / f).exists():
                self.errors.append(f"缺失文件: {f}")
        return len(self.errors) == 0

    def validate_skill_md(self) -> bool:
        print(" 检查 SKILL.md...")
        skill_md = self.skill_dir / "SKILL.md"
        if not skill_md.exists():
            return False
        content = skill_md.read_text(encoding="utf-8")
        if not content.startswith("---"):
            self.errors.append("SKILL.md 缺少 frontmatter")
        else:
            match = re.search(r"^---\n(.*?)\n---", content, re.DOTALL)
            if match:
                fm = match.group(1)
                for field in ["name", "version", "description"]:
                    if field + ":" not in fm:
                        self.errors.append(f"SKILL.md frontmatter 缺少字段: {field}")
        return len(self.errors) == 0

    def validate_references(self) -> bool:
        print(" 检查参考文档...")
        ref_dir = self.skill_dir / "references"
        if not ref_dir.exists():
            return False
        md_files = list(ref_dir.glob("*.md"))
        print(f"  找到 {len(md_files)} 个参考文档")
        for mf in md_files:
            if mf.stat().st_size < 100:
                self.warnings.append(f"参考文档过小: {mf.name} ({mf.stat().st_size} bytes)")
        return True

    def validate_scripts(self) -> bool:
        print(" 检查脚本...")
        script_dir = self.skill_dir / "scripts"
        if not script_dir.exists():
            return False
        py_files = list(script_dir.glob("*.py"))
        print(f"  找到 {len(py_files)} 个 Python 脚本")
        for pf in py_files:
            try:
                compile(pf.read_text(), pf.name, "exec")
            except SyntaxError as e:
                self.errors.append(f"脚本语法错误: {pf.name} - {e}")
        return len(self.errors) == 0

    def validate_cross_references(self) -> bool:
        print(" 检查交叉引用...")
        all_files = set()
        for ext in ["*.md", "*.py", "*.txt", "*.toml"]:
            for f in self.skill_dir.rglob(ext):
                if "__pycache__" in str(f):
                    continue
                all_files.add(str(f.relative_to(self.skill_dir)))

        # 保留：若后续重新引入工作流模块，此处自动校验其 references 引用。
        for wf in self.skill_dir.rglob("workflow.py"):
            wf_content = wf.read_text(encoding="utf-8")
            _cjk = "\u4e00-\u9fff"
            wf_refs = re.findall(
                r"references/([\w\-" + _cjk + r"/.]+\.md)",
                wf_content,
            )
            for ref in wf_refs:
                ref_file = f"references/{ref}"
                if ref_file not in all_files:
                    matches = [f for f in all_files if ref in f]
                    if matches:
                        self.warnings.append(
                            f"{wf.name} 引用可能不匹配: {ref} -> {matches}")
                    else:
                        self.errors.append(
                            f"{wf.name} 引用文件不存在: references/{ref}")

        skill_md = self.skill_dir / "SKILL.md"
        if skill_md.exists():
            content = skill_md.read_text(encoding="utf-8")
            content_no_code = re.sub(r"```[\s\S]*?```", "", content)
            _cjk = "\u4e00-\u9fff"
            refs = re.findall(
                r"`?(references|scripts|domains|core)/([\w\-" + _cjk + r"/.]+\.(?:md|py))`?",
                content_no_code,
                re.IGNORECASE,
            )
            for prefix, path in refs:
                ref_file = f"{prefix}/{path}"
                if ref_file not in all_files:
                    self.errors.append(f"SKILL.md 引用文件不存在: {ref_file}")

        return len(self.errors) == 0

    def run_all(self) -> Tuple[bool, List[str], List[str]]:
        print("=" * 60)
        print("论文辅导技能包完整性验证")
        print("=" * 60)
        print()
        self.validate_structure()
        self.validate_skill_md()
        self.validate_references()
        self.validate_scripts()
        self.validate_cross_references()
        print()
        print("=" * 60)
        print(f"验证结果：错误 {len(self.errors)} / 警告 {len(self.warnings)}")
        print("=" * 60)
        return len(self.errors) == 0, self.errors, self.warnings


def main():
    parser = argparse.ArgumentParser(description="论文辅导技能包完整性验证")
    parser.add_argument("--skill-dir", "-d", required=True, help="技能包目录路径")
    args = parser.parse_args()
    if not Path(args.skill_dir).exists():
        print(f"错误：目录不存在: {args.skill_dir}")
        sys.exit(1)
    validator = SkillValidator(args.skill_dir)
    success, errors, warnings = validator.run_all()
    if errors:
        print("\n 错误：")
        for e in errors:
            print(f"  - {e}")
    if warnings:
        print("\n  警告：")
        for w in warnings:
            print(f"  - {w}")
    if success:
        print("\n 验证通过！")
        sys.exit(0)
    else:
        print("\n 验证失败！")
        sys.exit(1)


if __name__ == "__main__":
    main()
