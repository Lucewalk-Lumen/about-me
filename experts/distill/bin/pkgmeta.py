#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bin/pkgmeta.py — 包元数据读取（版本号与署名）。

版本号与署名一律取自 plugin.json，不在脚本里硬编码，避免发布新版本后
生成的分发包仍带旧版本号。也支持环境变量覆盖（DISTILL_VERSION /
DISTILL_AUTHOR），便于分叉或再发布。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

# 包根目录（bin/ 的上一级）
PKG_ROOT = Path(__file__).resolve().parent.parent

_UNKNOWN = "0.0.0"


def _version_from_dirname() -> str:
    """plugin.json 不可读时的兜底：从包目录名解析版本号（如 distill-1.2.3）。

    宁可给出可辨认的兜底值，也不写死一个会随版本失真的常量。
    """
    m = re.search(r"-(\d+\.\d+\.\d+)$", PKG_ROOT.name)
    return m.group(1) if m else _UNKNOWN


def load_pkg_meta() -> dict:
    """读取专家包元数据（version / author_name / author_email）。失败安全：解析失败回退兜底值。"""
    default = {"version": _version_from_dirname(), "author_name": "Distill", "author_email": ""}
    try:
        with open(PKG_ROOT / ".codebuddy-plugin" / "plugin.json", encoding="utf-8") as f:
            meta = json.load(f)
        author = meta.get("author", {}) or {}
        # 署名取纯显示名（去掉「（机构）」等后缀：对外署名统一、隐私最小化）
        author_name = author.get("name", "Distill")
        author_name = author_name.split("（")[0].split("(")[0].strip()
        return {
            "version": meta.get("version", _version_from_dirname()),
            "author_name": author_name,
            "author_email": author.get("email", "") or "",
        }
    except Exception:
        return default
