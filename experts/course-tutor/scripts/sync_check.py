#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""跨端脚本一致性校验。

背景：教师端源码仓与学生端包是两份产物，历史上出现过「教师端修完、
学生端包零同步」的问题。本脚本在**教师端打包/发布学生端包之前**运行：
以教师端源码仓为权威，比对三份共有脚本的哈希，不一致即失败——把「修复回流」从口头约定变成打包门禁。

权威侧（本脚本所在仓）：course_points.py / course_warn.py / course_tdoc.py（仓库根目录）
跟随侧：学生端包（course_points.py 在 scripts/ 下，其余在包根）

用法：
  python3 scripts/sync_check.py                     # 默认学生端包路径
  python3 scripts/sync_check.py --student-pkg <路径> # 指定学生端包根目录

退出码：0 = 三份脚本两端一致；1 = 存在漂移或文件缺失（先同步再打包）。
"""

import argparse
import hashlib
import os
import sys

# 权威侧文件 → 跟随侧相对路径（相对学生端包根）
SHARED_SCRIPTS = {
    "course_points.py": os.path.join("scripts", "course_points.py"),
    "course_warn.py": "course_warn.py",
    "course_tdoc.py": "course_tdoc.py",
}

DEFAULT_STUDENT_PKG = os.path.join(
    os.path.expanduser("~"), ".workbuddy", "plugins", "marketplaces",
    "my-experts", "plugins", "course-companion",
)


def _md5(path):
    with open(path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


def main():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ap = argparse.ArgumentParser(description="教师端/学生端共有脚本一致性校验")
    ap.add_argument("--student-pkg", default=DEFAULT_STUDENT_PKG,
                    help="学生端包根目录（默认为已安装位置）")
    args = ap.parse_args()

    fails = []
    print(f"权威侧：{repo_root}")
    print(f"跟随侧：{args.student_pkg}\n")
    for name, rel in SHARED_SCRIPTS.items():
        auth = os.path.join(repo_root, name)
        follow = os.path.join(args.student_pkg, rel)
        if not os.path.isfile(auth):
            fails.append(f"{name}: 权威侧缺失（{auth}）")
            print(f"[FAIL] {name}: 权威侧缺失")
            continue
        if not os.path.isfile(follow):
            fails.append(f"{name}: 跟随侧缺失（{follow}）")
            print(f"[FAIL] {name}: 跟随侧缺失")
            continue
        ha, hf = _md5(auth), _md5(follow)
        if ha == hf:
            print(f"[OK]   {name}: 两端一致 ({ha[:12]})")
        else:
            fails.append(f"{name}: 哈希漂移 权威={ha[:12]} 跟随={hf[:12]}")
            print(f"[FAIL] {name}: 哈希漂移 权威={ha[:12]} 跟随={hf[:12]}（先同步再打包）")

    print()
    if fails:
        print(f"VERDICT=FAIL（{len(fails)} 项漂移）——禁止打学生端包，先同步")
        sys.exit(1)
    print("VERDICT=PASS（共有脚本两端一致）")


if __name__ == "__main__":
    main()
