#!/usr/bin/env python3
# 确保套件包可导入（包目录在上级目录）
import os, sys
_skill_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _skill_dir not in sys.path:
    sys.path.append(_skill_dir)


"""
generate_deliverable_pack.py
OBHRM研究套件 — 交付包自动组织打包脚本

用途：将任务输出文件按标准结构组织成交付包，生成文件清单和压缩包。
适用场景：完整流程交付、项目书、博士论文方案等需要多文件交付的任务。

用法：
    python generate_deliverable_pack.py --source-dir ./outputs --output-dir ./deliverables \\
        --task-type "项目书申报" --title "组织行为研究项目书" --version "v1.0"

功能：
    - 按标准目录结构组织文件（主文档/过程文件/证据文件/图表/脚本/核查清单）
    - 生成文件清单 JSON
    - 生成 zip 压缩包
    - 校验关键文件是否存在
"""

from obhrm_research_base.core._common_init import init_logger
from obhrm_research_base.core.safe_path import resolve_safe_output

logger = init_logger()

import argparse
import json
import os
import re
import shutil
import sys
import zipfile
from datetime import datetime
from pathlib import Path

# 标准交付包结构
DELIVERABLE_STRUCTURES = {
    "论文研究生产": {
        "主文档": ["论文方案总报告.docx", "论文方案总报告.md"],
        "过程文件": ["选题诊断.md", "文献对话与理论缺口.md", "研究设计细化.md"],
        "证据文件": ["证据检索记录.md", "参考文献列表.md"],
        "图表": ["技术路线图.mmd", "理论模型图.mmd", "变量矩阵.mmd"],
        "核查清单": ["quality_checklist.md", "提交前检查.md"],
    },
    "项目书申报": {
        "主文档": ["项目书总报告.docx", "项目书总报告.md"],
        "过程文件": ["选题依据.md", "研究现状述评.md", "研究内容设计.md", "技术路线.md"],
        "证据文件": ["证据检索记录.md", "前期成果列表.md"],
        "图表": ["技术路线图.mmd", "年度计划图.mmd"],
        "核查清单": ["quality_checklist.md", "提交前检查.md", "匿名活页检查.md"],
    },
    "诊断评审": {
        "主文档": ["诊断报告.docx", "诊断报告.md"],
        "过程文件": ["问题分类.md", "修改建议.md"],
        "证据文件": ["原文对照.md"],
        "核查清单": ["quality_checklist.md"],
    },
    "博士论文方案": {
        "主文档": ["博士论文方案总报告.docx", "博士论文方案总报告.md"],
        "过程文件": ["选题诊断.md", "文献对话.md", "总体模型.md", "分研究设计.md"],
        "证据文件": ["证据检索记录.md"],
        "图表": ["技术路线图.mmd", "分研究承接矩阵.mmd", "理论模型图.mmd"],
        "核查清单": ["quality_checklist.md", "风险检查清单.md"],
    },
}


def _sanitize_segment(value: str) -> str:
    """净化用于交付包目录名的用户片段。

    移除路径分隔符（/、\\）、Windows 盘符冒号，并折叠连续点号（.. 等逃逸
    序列），仅保留安全文件名字符，防止 `../../../../tmp/evil` 这类片段让
    pack_dir 超出允许的基目录。
    """
    if not value:
        return "untitled"
    value = str(value)
    # 移除路径分隔符与 Windows 盘符冒号
    value = value.replace("\\", "_").replace("/", "_").replace(":", "_")
    # 折叠连续点号，避免 `..` / `....` 等逃逸序列
    value = re.sub(r"\.{1,}", "_", value)
    # 清理首尾空白与多余分隔符
    value = value.strip().strip("_").strip("-")
    return value or "untitled"


def organize_files(source_dir, output_dir, task_type, title, version="v1.0"):
    """组织文件到标准交付包结构"""
    source = Path(source_dir)
    output = Path(output_dir)

    if not source.exists():
        print(f"错误：源目录不存在: {source}")
        return None

    # 创建交付包目录
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pack_name = f"{title}_{task_type}_{version}_{timestamp}"
    pack_dir = output / pack_name
    pack_dir.mkdir(parents=True, exist_ok=True)

    structure = DELIVERABLE_STRUCTURES.get(task_type, DELIVERABLE_STRUCTURES["论文研究生产"])

    # 按结构组织文件
    file_manifest = {}
    for category, expected_files in structure.items():
        cat_dir = pack_dir / category
        cat_dir.mkdir(exist_ok=True)
        copied = []
        for expected in expected_files:
            src_file = source / expected
            if src_file.exists():
                dst = cat_dir / expected
                shutil.copy2(src_file, dst)
                copied.append(str(dst.relative_to(pack_dir)))
        # 同时尝试匹配源目录中的任意文件
        for src_file in source.iterdir():
            if src_file.is_file() and src_file.name not in expected_files:
                # 根据文件扩展名和名称推断分类
                cat = infer_category(src_file.name, structure)
                if cat:
                    cat_d = pack_dir / cat
                    cat_d.mkdir(exist_ok=True)
                    dst = cat_d / src_file.name
                    if not dst.exists():
                        shutil.copy2(src_file, dst)
                        copied.append(str(dst.relative_to(pack_dir)))
        file_manifest[category] = copied

    # 将未分类文件归档到"其他"
    other_files = []
    for src_file in source.iterdir():
        if src_file.is_file():
            already_copied = any(
                str(src_file.name) in [Path(f).name for f in files] for files in file_manifest.values()
            )
            if not already_copied:
                other_dir = pack_dir / "其他"
                other_dir.mkdir(exist_ok=True)
                dst = other_dir / src_file.name
                shutil.copy2(src_file, dst)
                other_files.append(str(dst.relative_to(pack_dir)))
    if other_files:
        file_manifest["其他"] = other_files

    return pack_dir, file_manifest


def infer_category(filename, structure):
    """根据文件名推断文件分类"""
    fname_lower = filename.lower()
    if any(x in fname_lower for x in [".mmd", "图", "chart", "visual", "matrix", "flow"]):
        return "图表"
    if any(x in fname_lower for x in ["检查", "checklist", "核查", "校验"]):
        return "核查清单"
    if any(x in fname_lower for x in ["检索", "evidence", "ref", "文献"]):
        return "证据文件"
    if any(x in fname_lower for x in ["过程", "design", "draft", "outline"]):
        return "过程文件"
    if any(x in fname_lower for x in ["总报告", "main", "final"]):
        return "主文档"
    return None


def create_manifest(pack_dir, file_manifest, task_type, title, version):
    """生成交付清单 JSON"""
    manifest = {
        "created_at": datetime.now().isoformat(),
        "task_type": task_type,
        "title": title,
        "version": version,
        "pack_dir": str(pack_dir),
        "files": file_manifest,
        "notes": "交付包按 OBHRM 研究协作团 标准结构组织",
    }
    manifest_path = pack_dir / "delivery_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    return manifest_path


def create_zip(pack_dir):
    """创建 zip 压缩包"""
    zip_path = pack_dir.with_suffix(".zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(pack_dir):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(pack_dir.parent)
                zf.write(file_path, arcname)
    return zip_path


def validate_pack(pack_dir, task_type):
    """校验交付包完整性"""
    issues = []

    # 检查主文档是否存在
    main_doc_dir = pack_dir / "主文档"
    if not main_doc_dir.exists() or not any(main_doc_dir.iterdir()):
        issues.append("缺少主文档")

    # 检查核查清单
    check_dir = pack_dir / "核查清单"
    if not check_dir.exists() or not any(check_dir.iterdir()):
        issues.append("缺少核查清单")

    return issues


def main():
    parser = argparse.ArgumentParser(description="OBHRM交付包自动组织打包")
    parser.add_argument("--source-dir", "-s", required=True, help="源文件目录")
    parser.add_argument("--output-dir", "-o", default="./deliverables", help="输出目录")
    parser.add_argument(
        "--task-type", "-t", required=True, choices=list(DELIVERABLE_STRUCTURES.keys()), help="任务类型"
    )
    parser.add_argument("--title", required=True, help="交付包标题")
    parser.add_argument("--version", "-v", default="v1.0", help="版本号")
    args = parser.parse_args()

    # 净化用于交付包目录名的用户片段，移除路径分隔符与 `..`，防止穿越
    title = _sanitize_segment(args.title)
    task_type = _sanitize_segment(args.task_type)
    version = _sanitize_segment(args.version)

    # 校验输出根目录落在 cwd 之内，超出允许范围（含 ../ 逃逸、绝对路径指向系统
    # 目录等）一律拒绝，避免交付包被写到 cwd 之外的任意位置。
    try:
        output_dir = str(resolve_safe_output(args.output_dir, base=os.getcwd()))
    except ValueError as e:
        print(f"错误：{e}")
        sys.exit(1)

    pack_dir, file_manifest = organize_files(args.source_dir, output_dir, task_type, title, version)
    if not pack_dir:
        sys.exit(1)

    # 清单元数据必须与磁盘目录名一致：使用已净化的 task_type/title/version，
    # 而非原始 args.*（原始串可能含 /、.. 等，会与 pack_dir 命名不一致并写入未净化文本）。
    manifest_path = create_manifest(pack_dir, file_manifest, task_type, title, version)
    zip_path = create_zip(pack_dir)
    issues = validate_pack(pack_dir, task_type)

    print(f"交付包已生成: {pack_dir}")
    print(f"  清单文件: {manifest_path}")
    print(f"  压缩包: {zip_path}")
    print("  文件分类:")
    for cat, files in file_manifest.items():
        print(f"    {cat}: {len(files)} 个文件")
    if issues:
        print(f"  校验警告: {issues}")
    else:
        print("  校验: 通过")


if __name__ == "__main__":
    main()
