#!/usr/bin/env python3
"""HRM 实战参谋团 · PII 脱敏与 DLP 过滤（零三方依赖）

用于在 L0 接入网关与日志/转写中对个人敏感信息脱敏，阻断 PII 泄露。
- mask_phone / mask_email / mask_idcard：结构化脱敏
- redact_pii(text)：对自由文本做 DLP 正则脱敏（日志/转写落盘前调用）
"""
from __future__ import annotations

import re

# DLP 规则（保守优先，宁可多脱敏）
_PATTERNS = {
    "phone": re.compile(r"(?<!\d)(1[3-9]\d{9})(?!\d)"),
    "email": re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"),
    "idcard": re.compile(r"(?<!\d)(\d{17}[\dXx]|\d{15})(?!\d)"),
}


def _mask_phone(m: "re.Match") -> str:
    p = m.group(1)
    return p[:3] + "****" + p[7:]


def mask_phone(text: str) -> str:
    # 用 sub 替换全部匹配（search+replace 只处理首个，会泄漏其余手机号）
    return _PATTERNS["phone"].sub(_mask_phone, text)


def mask_email(text: str) -> str:
    def _rep(m):
        local, domain = m.group(0).split("@", 1)
        keep = local[:2]
        return f"{keep}***@{domain}"
    return _PATTERNS["email"].sub(_rep, text)


def _mask_idcard(m: "re.Match") -> str:
    idc = m.group(1)
    if len(idc) == 15:
        # 15 位：保留前 6 后 3，中间 6 位打码（保持 15 位长度，避免错位成 18 位）
        return idc[:6] + "*" * 6 + idc[-3:]
    # 18 位：保留前 6 后 4，中间 8 位打码
    return idc[:6] + "*" * 8 + idc[-4:]


def mask_idcard(text: str) -> str:
    # 用 sub 替换全部匹配（search+replace 只处理首个，会泄漏其余证件号）
    return _PATTERNS["idcard"].sub(_mask_idcard, text)


def redact_pii(text: str) -> str:
    """对自由文本脱敏，返回脱敏后文本。用于日志/转写落盘前。"""
    if not text:
        return text
    text = mask_phone(text)
    text = mask_email(text)
    text = mask_idcard(text)
    return text


def contains_pii(text: str) -> bool:
    if not text:
        return False
    return any(p.search(text) for p in _PATTERNS.values())
