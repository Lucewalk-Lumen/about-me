#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
doctor.py —— 环境自检（R10 防护）

为什么必须有这个:
  实测本机存在两个 Python 3.13.12，一个装了scikit-learn + jieba，
  另一个没有 ——同一句 `python3 xxx.py` 在不同环境下包可用性完全不同。
  且系统 python3.9.6 连 numpy 都没有。
  → 用户按`python3 xxx.py` 会得到误导性的 No module named numpy / sklearn，
  而真正的原因是【解释器选错】，不是【包没装】。

退出码:
    0 = 环境就绪
    8 = 环境不满足（EXIT_ENV_UNMET）
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

REQUIRED = [
    ("numpy", ">=1.24"),
    ("scipy", ">=1.10"),
    ("sklearn", ">=1.3"),
    ("jieba", ">=0.42"),
]
OPTIONAL = [
    ("networkx", ">=3.0（本包布局用纯 numpy 实现，非必需）"),
]
MIN_PY = (3, 9)

FIX_HINT = {
    "numpy":   "pip install numpy",
    "scipy":   "pip install scipy",
    "sklearn": "pip install scikit-learn",
    "jieba":   "pip install jieba  # 注意：0.42.1 直接 pip 安装可能报 OSError:EEXIST，"
               "需手动解包后 pip install .（见 README 故障排查）",
}


def probe(mod_name: str):
    try:
        mod = __import__(mod_name)
        return True, getattr(mod, "__version__", "?"), None
    except ImportError as e:
        return False, None, str(e)
    except Exception as e:  # noqa: BLE001
        return False, None, f"{type(e).__name__}: {e}"


def main() -> int:
    print("=" * 56, file=sys.stderr)
    print("EndNote 文献分析 · 环境自检", file=sys.stderr)
    print("=" * 56, file=sys.stderr)
    print(f"\n当前解释器: {sys.executable}", file=sys.stderr)
    print(f"Python 版本: {sys.version.split()[0]}", file=sys.stderr)
    print(f"脚本位置  : {Path(__file__).resolve().parent}", file=sys.stderr)

    problems: list[str] = []

    if sys.version_info[:2] < MIN_PY:
        problems.append(
            f"Python 版本过低：{sys.version.split()[0]} < "
            f"{MIN_PY[0]}.{MIN_PY[1]}")

    print("\n[必需依赖]", file=sys.stderr)
    for name, spec in REQUIRED:
        ok, ver, err = probe(name)
        mark = "✓" if ok else "✗"
        line = f"  {mark} {name:12s} {ver or '缺失'}"
        if not ok:
            line += f"  ({err})"
            problems.append(f"{name} 缺失或不可导入")
        print(line + f"   要求 {spec}", file=sys.stderr)

    print("\n[可选依赖]", file=sys.stderr)
    for name, note in OPTIONAL:
        ok, ver, _ = probe(name)
        mark = "✓" if ok else "—"
        print(f"  {mark} {name:12s} {ver or '未安装'}   {note}", file=sys.stderr)

    # 解释器歧义提示 —— 本机实测存在两个 3.13.12 依赖不同
    if sys.version_info[:2] >= (3, 13):
        print(
            "\n[提示] 本机可能存在多个 Python 3.13 环境，依赖不同。\n"
            "      若上面某项显示「缺失」但你确信装过，请改用包完整的解释器：\n"
            "        <该环境>/bin/python scan_library.py ...",
            file=sys.stderr,
        )

    if problems:
        print(f"\n[结论] 环境不满足，共{len(problems)} 项问题：", file=sys.stderr)
        for p in problems:
            print(f"  · {p}", file=sys.stderr)
        print("\n[修复建议]", file=sys.stderr)
        for name, _ in REQUIRED:
            if any(name in p for p in problems) and name in FIX_HINT:
                print(f"  {name}: {FIX_HINT[name]}", file=sys.stderr)
        print(
            "\n  若你不确定该用哪个解释器，可查找可用环境：\n"
            "    ls -d /path/to/*/bin/python3  && 逐个运行 doctor.py",
            file=sys.stderr,
        )
        print(f"[hint] {EXIT[8]}", file=sys.stderr)
        return 8

    print("\n[结论] 环境就绪，可以运行 scan_library.py / cluster_topics.py", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
