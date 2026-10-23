#!/usr/bin/env python3
"""promotion_gate_check.py - 晋级门槛元数据预检（机械层，零三方依赖）。

对候选条目做「可确定性核对」的预检：frontmatter 元数据基线齐全性、status 取值合法性、
official 候选的 owner/valid_for 必填性。判断层（内容质量够不够晋级）由关晋人工完成，本脚本不做。

输入：一个或多个 Markdown 文件路径；也接受目录路径（递归展开其中的 .md 文件，空目录明确提示而非误报缺失）。
输出：逐文件核对表 + 汇总结论（文本）。退出码：0 全部通过；1 有未通过项；2 参数/读取错误。
"""
import argparse
import os
import re
import sys

REQUIRED_BASE = ["created", "updated", "source", "status"]
REQUIRED_OFFICIAL = ["owner", "valid_for"]
VALID_STATUS = {"idea", "draft", "official", "archive"}

FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
FIELD_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:", re.MULTILINE)


def expand_inputs(paths):
    """把文件/目录输入统一展开为 md 文件清单。返回 (files, notes)：
    files = 排序后的 .md 绝对/相对路径列表；notes = 需要向用户说明的提示（如目录无 md、路径不存在）。"""
    files = []
    notes = []
    for p in paths:
        if os.path.isfile(p):
            files.append(p)
        elif os.path.isdir(p):
            found = []
            for root, _dirs, names in os.walk(p):
                for n in sorted(names):
                    if n.lower().endswith(".md"):
                        found.append(os.path.join(root, n))
            if found:
                files.extend(sorted(found))
                notes.append("目录 %s 展开为 %d 个 .md 文件" % (p, len(found)))
            else:
                notes.append("目录 %s 下未找到任何 .md 文件（无可预检候选）" % p)
        else:
            notes.append("路径不存在，已跳过: %s" % p)
    return files, notes


def parse_frontmatter(text):
    m = FM_RE.match(text)
    if not m:
        return None
    fields = {}
    for fm in FIELD_RE.finditer(m.group(1)):
        fields[fm.group(1)] = True
    sm = re.search(r"^status\s*:\s*([A-Za-z]+)\s*$", m.group(1), re.MULTILINE)
    status = sm.group(1).strip() if sm else None
    return fields, status


def check_file(path, target):
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
    except (OSError, UnicodeDecodeError) as e:
        return path, None, ["读取失败: %s" % e]

    parsed = parse_frontmatter(text)
    if parsed is None:
        return path, None, ["缺少 YAML frontmatter（--- 包裹的元数据头）"]
    fields, status = parsed

    problems = []
    for req in REQUIRED_BASE:
        if req not in fields:
            problems.append("缺元数据字段: %s" % req)
    if status is None:
        problems.append("status 字段缺失或无值")
    elif status not in VALID_STATUS:
        problems.append("status 取值非法: %s（合法值: idea/draft/official/archive）" % status)
    if target == "official":
        for req in REQUIRED_OFFICIAL:
            if req not in fields:
                problems.append("晋级 official 必填字段缺失: %s" % req)
    return path, status, problems


def main(argv=None):
    p = argparse.ArgumentParser(
        description="晋级门槛元数据预检：核对 frontmatter 基线字段与 status 合法性（判断层由人工完成）。",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("files", nargs="+", help="候选条目 Markdown 文件或目录路径（目录递归展开 .md）")
    p.add_argument("--target", choices=["draft", "official"], default="official",
                   help="晋级目标档位（official 档追加 owner/valid_for 必填核对）")
    args = p.parse_args(argv)

    files, notes = expand_inputs(args.files)
    for note in notes:
        print("[提示] %s" % note)
    if not files:
        print("---")
        print("预检汇总: 0 个候选可预检（请检查路径或目录内容）")
        return 2

    total = 0
    failed = 0
    for path in files:
        total += 1
        _, status, problems = check_file(path, args.target)
        if problems:
            failed += 1
            print("[FAIL] %s | status=%s" % (path, status))
            for prob in problems:
                print("       - %s" % prob)
        else:
            print("[OK]   %s | status=%s | 元数据基线齐全" % (path, status))

    print("---")
    print("预检汇总: %d 个候选, %d 通过, %d 未通过（机械层预检，判断层由评审官完成）"
          % (total, total - failed, failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
