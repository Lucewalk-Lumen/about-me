#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
office_bin.py - 本地办公软件二进制探测器（ppt-maker 技能）

目的
----
需要“原生 .pptx / 办公二进制”能力时，优先复用用户**本机已装**的办公软件
（WPS / 微软 PowerPoint / 微软 Word），**绝不**自动下载 LibreOffice。

本模块是纯探测：只返回首个可用二进制绝对路径；任何情况下都不触发下载、
不修改系统、不联网。仅在全盘无可用二进制时返回 ``None``，由调用方决定后续
（回退 python-pptx 离线生成 / 委托平台内置 tencent-pptx 技能 / 提示用户自装）。

优先级（从高到低）
------------------
  Windows : wps → wpp → powerpnt → winword → soffice
  macOS   : Microsoft PowerPoint.app → WPS Office.app（若装）→ LibreOffice.app
  Linux   : soffice → libreoffice → wps

环境变量
--------
  OFFICE_BIN : 若设置且为可执行文件，直接采用并跳过探测（供 CI / 受限环境手动指定）。

用法
----
  from office_bin import find_office_bin
  bin_path = find_office_bin()   # str 绝对路径 或 None
"""

from __future__ import annotations

import os
import platform
import shutil
from pathlib import Path

# 探测候选（顺序即优先级）。PATH 探测与已知目录探测共用此表结构。
_WIN_PATH_NAMES = ("wps", "wpp", "powerpnt", "winword", "soffice")
_WIN_KNOWN_DIRS = [
    # LibreOffice（最后兜底，仍优先于“下载”）
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    # WPS Office（演示 wpp / 文字 wps）
    r"C:\Program Files (x86)\Kingsoft\WPS Office\wps.exe",
    r"C:\Program Files\Kingsoft\WPS Office\wps.exe",
    r"C:\Program Files (x86)\Kingsoft\WPS Office\wpp.exe",
    r"C:\Program Files\Kingsoft\WPS Office\wpp.exe",
    # 微软 Office（PowerPoint / Word）
    r"C:\Program Files\Microsoft Office\root\Office16\POWERPNT.EXE",
    r"C:\Program Files\Microsoft Office\Office16\POWERPNT.EXE",
    r"C:\Program Files (x86)\Microsoft Office\root\Office16\POWERPNT.EXE",
    r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE",
    r"C:\Program Files (x86)\Microsoft Office\root\Office16\WINWORD.EXE",
]

_MAC_KNOWN_APPS = [
    "/Applications/Microsoft PowerPoint.app/Contents/MacOS/Microsoft PowerPoint",
    "/Applications/WPS Office.app/Contents/MacOS/WPS",  # WPS 若装（macOS 路径随版本可能不同）
    "/Applications/LibreOffice.app/Contents/MacOS/soffice",
]

_LINUX_PATH_NAMES = ("soffice", "libreoffice", "wps")


def _is_executable(path: str) -> bool:
    """路径存在且可执行（文件 + 可执行位）。"""
    try:
        return os.path.isfile(path) and os.access(path, os.X_OK)
    except OSError:
        return False


def find_office_bin() -> str | None:
    """返回首个可用办公二进制绝对路径；无任何可用二进制时返回 None。

    关键：本函数**绝不触发任何下载**。探测顺序：
      1) 环境变量 ``OFFICE_BIN``（若非空且可执行，直接返回，跳过其余探测）；
      2) 按当前 OS 用 ``shutil.which`` 在 PATH 上探测；
      3) 按当前 OS 枚举已知安装目录/应用包探测。
    全部未命中则返回 ``None``。
    """
    # 1) 环境变量优先（永不下载，仅校验可执行）
    env = os.environ.get("OFFICE_BIN")
    if env and env.strip():
        env = env.strip()
        if _is_executable(env):
            return env
        # 显式指定但不可用：不要静默回退到别处——尊重用户意图，明确告知未命中
        return None

    sysn = platform.system()
    if sysn == "Windows":
        candidates = list(_WIN_PATH_NAMES) + _WIN_KNOWN_DIRS
    elif sysn == "Darwin":
        candidates = _MAC_KNOWN_APPS
    else:  # Linux / 其他 POSIX
        candidates = list(_LINUX_PATH_NAMES)

    # 2) PATH 探测（shutil.which 已含目录解析，仅对命令名有效）
    for name in candidates:
        if os.path.sep not in name:  # 纯命令名 → 走 PATH
            hit = shutil.which(name)
            if hit and _is_executable(hit):
                return hit

    # 3) 已知目录 / 应用包探测（绝对路径）
    for path in candidates:
        if os.path.sep in path and _is_executable(path):
            return path

    return None


if __name__ == "__main__":
    found = find_office_bin()
    if found:
        print(found)
    else:
        raise SystemExit(1)
