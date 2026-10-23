#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""源码包干净打包（course-tutor-src-<版本>.zip）。

定位：把整个 course-tutor 源仓（教师端 + 学生端模块源 + 全部构建/运维脚本）原样打包，
供维护者存档 / 迁移 / 二次开发。**不含** dist 产物、构建暂存、版本库与工程垃圾。

与上架包的区别：教师端/学生端上架包只含运行所需子集；源码包是完整源仓快照。

在教师包根目录运行：
    python scripts/build_src_package.py

产物：dist/course-tutor-src-<版本>.zip
"""

import json
import os
import shutil
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, "dist")
STAGING = os.path.join(ROOT, ".build_staging", "src_pkg")

# 整仓打包时的排除项（产物 / 暂存 / 版本库 / 工程垃圾 / 工程实现记录）
SKIP_DIRS = {".git", "dist", ".build_staging", "__pycache__", ".env", "dev"}
SKIP_FILES = {".DS_Store", "Thumbs.db", "desktop.ini", "DEVLOG.md"}
SKIP_SUFFIX = (".pyc", ".pyo", ".bak")


def _harden():
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(errors="replace")
        except (AttributeError, ValueError, OSError):
            pass


_harden()


def read_version():
    p = os.path.join(ROOT, ".codebuddy-plugin", "plugin.json")
    return json.load(open(p, encoding="utf-8-sig")).get("version", "0.0.0")


def main():
    version = read_version()
    if os.path.exists(STAGING):
        shutil.rmtree(STAGING)
    os.makedirs(STAGING)

    # 整仓拷贝（排除产物/暂存/版本库/垃圾/备份）
    for item in sorted(os.listdir(ROOT)):
        if item in SKIP_DIRS:
            continue
        src = os.path.join(ROOT, item)
        dst = os.path.join(STAGING, item)
        if os.path.isdir(src):
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns(
                "__pycache__", "*.pyc", "*.pyo", "*.bak",
                ".DS_Store", "Thumbs.db", "desktop.ini",
                "dev", "DEVLOG.md"))
        else:
            if item in SKIP_FILES or item.endswith(SKIP_SUFFIX):
                continue
            shutil.copyfile(src, dst)

    # 自扫：源码包内不得残留备份 / 垃圾 / 缓存
    leftovers = []
    for dp, dirs, fns in os.walk(STAGING):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fn in fns:
            if fn in SKIP_FILES or fn.endswith(SKIP_SUFFIX):
                leftovers.append(os.path.relpath(os.path.join(dp, fn), STAGING))
    if leftovers:
        print("[FAIL] 源码包含不应入包项：", leftovers[:8])
        shutil.rmtree(STAGING)
        sys.exit(1)

    os.makedirs(DIST, exist_ok=True)
    top = f"course-tutor-src-{version}"
    zp = os.path.join(DIST, top + ".zip")
    if os.path.exists(zp):
        os.remove(zp)
    n = 0
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for dp, dirs, fns in os.walk(STAGING):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for fn in fns:
                if fn in SKIP_FILES or fn.endswith(SKIP_SUFFIX):
                    continue
                fp = os.path.join(dp, fn)
                rel = os.path.relpath(fp, STAGING).replace(os.sep, "/")
                z.write(fp, f"{top}/{rel}")
                n += 1
    shutil.rmtree(STAGING)
    print(f"[OK] 源码包已生成：{zp}（{os.path.getsize(zp)} 字节，{n} 条目，整仓快照含全部脚本）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
