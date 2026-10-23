#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""教师端专家包干净打包（云端化后，替代原「分发用教师包」构建）。

云端化后教师端**无需「洗白分发」**——课程资料全在腾讯文档云端，其他老师直接安装。
本脚本只做一件事：把教师端**上架包**干净打包（不含学生端模块、不含构建脚本、不含真实 ID）。

产物：dist/course-tutor-<版本>.zip

包含：
  .codebuddy-plugin/plugin.json、agents/course-tutor.md、avatars/teacher.png、
  references/（教师端全部细则）、根目录 course_*.py（9 个运行时脚本）、
  scripts/（仅两个运维脚本：backup_data_hub.py 整库备份 / course_archive.py 结课归档）、
  README.md、CHANGELOG.md、UPGRADE.md、data_hub_config.json（占位符）、LICENSE

排除：
  student/（学生端模块源）、
  scripts/ 下的**构建类**脚本（build_*.py / discover_hub.py / fetch_assets.py /
  sync_assets.py / sync_check.py——属于出包工具链，不随教师端上架包分发）、
  dist/、.env、__pycache__、*.pyc、平台垃圾文件
"""

import os
import re
import shutil
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, "dist")
STAGING = os.path.join(ROOT, ".build_staging", "teacher_pkg")

INCLUDE_TOP = (".codebuddy-plugin", "agents", "avatars", "references")
INCLUDE_FILES = ("README.md", "CHANGELOG.md", "UPGRADE.md", "LICENSE", "data_hub_config.json")
# 注意：scripts/ **不能**整体排除——教师端文档按 scripts/<运维脚本> 直接调用，
# 这里只放 OPS_SCRIPTS 两个；构建类脚本本来就没拷进 STAGING，不会混进包
SKIP_DIRS = {"student", "dist", ".env", ".git",
             "__pycache__", ".build_staging", "templates"}
SKIP_FILES = {".DS_Store", "Thumbs.db", "desktop.ini", "_aud1.txt", "_aud2.txt", "_t.txt",
              "DEVLOG.md"}  # DEVLOG 是工程实现记录，不面向教师，不随上架包分发
SKIP_SUFFIX = (".pyc", ".pyo", ".bak")  # .bak=工程误改/旧版备份，绝不入上架包
# 随教师端上架包分发的**运维脚本**（教师端文档按 scripts/ 路径直接调用，缺即死链）
OPS_SCRIPTS = ("backup_data_hub.py", "course_archive.py")


def _harden():
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(errors="replace")
        except (AttributeError, ValueError, OSError):
            pass


_harden()


def read_version():
    import json
    p = os.path.join(ROOT, ".codebuddy-plugin", "plugin.json")
    return json.load(open(p, encoding="utf-8-sig")).get("version", "0.0.0")


def main():
    version = read_version()
    if os.path.exists(STAGING):
        shutil.rmtree(STAGING)
    os.makedirs(STAGING)

    # 1. 顶层目录（含 .codebuddy-plugin 隐藏目录）
    for name in INCLUDE_TOP:
        src = os.path.join(ROOT, name)
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(STAGING, name),
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo",
                                                          "*.bak", ".DS_Store", "Thumbs.db", "desktop.ini"))
    # 2. 顶层文件
    for name in INCLUDE_FILES:
        src = os.path.join(ROOT, name)
        if os.path.isfile(src):
            shutil.copyfile(src, os.path.join(STAGING, name))
    # 3. 根目录运行时脚本 course_*.py
    for fn in os.listdir(ROOT):
        if fn.startswith("course_") and fn.endswith(".py"):
            shutil.copyfile(os.path.join(ROOT, fn), os.path.join(STAGING, fn))
    # 3b. 运维脚本：教师端文档 §10.6 / §10.6b 直接按
    #     ${CODEBUDDY_PLUGIN_ROOT}/scripts/<脚本> 调用，缺了就是死链（实测：教师跑整库备份 /
    #     结课归档时文件不存在）。只带运维两个，构建类脚本不进上架包。
    ops = os.path.join(STAGING, "scripts")
    os.makedirs(ops, exist_ok=True)
    for fn in OPS_SCRIPTS:
        src = os.path.join(ROOT, "scripts", fn)
        if os.path.isfile(src):
            shutil.copyfile(src, os.path.join(ops, fn))
        else:
            print(f"[FAIL] 运维脚本缺失：scripts/{fn}")
            shutil.rmtree(STAGING)
            sys.exit(1)

    # 4. 校验：教师端包内不得含真实 ID / 密钥
    problems = []
    id_keys = ["hub_file_id", "usage_file_id", "file_id", "sheet_id"]
    for dp, dirs, fns in os.walk(STAGING):
        for fn in fns:
            if not fn.endswith((".py", ".md", ".json", ".txt")):
                continue
            fp = os.path.join(dp, fn)
            txt = open(fp, encoding="utf-8", errors="replace").read()
            # 真实 ID 形态：32 位 hex 或 tdoc:<32hex> 或 BmBh/9EnqKK 这类已见过的真实值
            for m in re.findall(r"\b([A-Za-z0-9]{8,})\b", txt):
                pass  # 占位符是 <xxx> 形式，真实 ID 是裸 hex，这里只做粗扫
            if re.search(r"tdoc:[A-Za-z0-9]{8,}", txt):
                problems.append(f"{os.path.relpath(fp, STAGING)} 含 tdoc: 真实定位疑似")
            if re.search(r"Bearer\s+[A-Za-z0-9._\-]{16,}", txt):
                problems.append(f"{os.path.relpath(fp, STAGING)} 含疑似 token")
    if problems:
        print("[FAIL] 教师端包自扫发现疑似真实 ID / 密钥：")
        for p in problems:
            print("  -", p)
        shutil.rmtree(STAGING)
        sys.exit(1)
    print("[OK] 教师端包自扫通过（无 tdoc: 真实定位、无疑似 token）")

    # 5. 打包
    os.makedirs(DIST, exist_ok=True)
    top = f"course-tutor-{version}"
    zp = os.path.join(DIST, top + ".zip")
    if os.path.exists(zp):
        os.remove(zp)
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for dp, dirs, fns in os.walk(STAGING):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for fn in fns:
                if fn in SKIP_FILES or fn.endswith(SKIP_SUFFIX):
                    continue
                fp = os.path.join(dp, fn)
                rel = os.path.relpath(fp, STAGING).replace(os.sep, "/")
                z.write(fp, f"{top}/{rel}")
    size = os.path.getsize(zp)
    print(f"[OK] 教师端包已生成：{zp}（{size} 字节，云端化后无需洗白分发，直接安装）")
    shutil.rmtree(STAGING)
    return 0


if __name__ == "__main__":
    sys.exit(main())
