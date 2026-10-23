#!/usr/bin/env python3
"""HRM 实战参谋团 · 审计日志（append-only，零三方依赖）

所有关键决策、合规闸裁决、真实副作用动作均 append 到审计文件，
每条带 trace_id / ts / event / 结果，供可观测性与事后追溯。
默认路径：环境变量 HRM_AUDIT_LOG；否则优先用户级数据目录
（~/.local/share/hrm-advisory-corps/audit.log，Windows 用 %APPDATA%，遵循 XDG_DATA_HOME），
仅当用户目录不可写时回退到系统临时目录并显式告警（不写入脚本/插件安装目录）。
注意：审计日志本身也经 PII 脱敏后再落盘。

路径解析是**惰性**的：仅在首次真正写入/读取时才解析并缓存；仅导入本模块
**不会**创建任何文件（import 期零写试探副作用）。
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .pii import redact_pii

_APP_NAME = "hrm-advisory-corps"

# 保留键：由 log() 内部生成，调用方 fields 不可覆盖（过滤丢弃，避免污染追溯字段）
_RESERVED_KEYS = frozenset({"ts", "trace_id", "event"})

# 进程内写锁（保证多产物并发追加不交错）；跨进程由宿主文件系统语义兜底
_write_lock = threading.Lock()
_warned = False  # 写失败仅告警一次，避免刷屏且不阻断主流程

# 惰性缓存：首次解析后固定，避免 import 期副作用
_default_path_cache: Optional[str] = None


def _nearest_writable_dir(path: str) -> bool:
    """非变更式可写性检查：向上找到最近的已存在目录，用 os.access 判定可写。

    不创建任何目录/文件（纯 os.access 可写性判定，无写试探）。
    """
    d = os.path.dirname(os.path.abspath(path))
    while d and not os.path.isdir(d):
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return bool(d) and os.path.isdir(d) and os.access(d, os.W_OK)


def _default_user_candidates() -> list:
    """用户级审计目录候选（按平台给出，路径均用 os.path.expanduser 构造）。"""
    candidates: list = []
    if os.name == "nt":
        for env in ("APPDATA", "LOCALAPPDATA"):
            base = os.getenv(env)
            if base:
                candidates.append(os.path.join(base, _APP_NAME, "audit.log"))
    else:
        xdg = os.getenv("XDG_DATA_HOME")
        if xdg:
            candidates.append(os.path.join(xdg, _APP_NAME, "audit.log"))
        candidates.append(
            os.path.join(os.path.expanduser("~/.local/share"), _APP_NAME, "audit.log")
        )
        # 用户级缓存目录次选（数据目录不可写时的过渡层，仍属用户空间，优于系统临时目录）
        xdg_cache = os.getenv("XDG_CACHE_HOME")
        if xdg_cache:
            candidates.append(os.path.join(xdg_cache, _APP_NAME, "audit.log"))
        if sys.platform == "darwin":
            candidates.append(
                os.path.join(os.path.expanduser("~/Library/Caches"), _APP_NAME, "audit.log")
            )
        candidates.append(
            os.path.join(os.path.expanduser("~/.cache"), _APP_NAME, "audit.log")
        )
    return candidates


def _resolve_default_path() -> str:
    """解析审计日志默认路径（跨平台、对只读/受限安装目录健壮）。

    优先级：用户级数据目录（`~/.local/share/hrm-advisory-corps/audit.log`；
    Windows 为 `%APPDATA%/hrm-advisory-corps/audit.log`，并遵循 `XDG_DATA_HOME`）
    > 用户级缓存目录（`XDG_CACHE_HOME` / macOS `~/Library/Caches` / `~/.cache`）
    > 系统临时目录。**不写入脚本/插件安装目录**，避免污染只读安装位置。
    仅当用户级目录均不可写时回退到系统临时目录，并显式告警。
    仅做 os.access 可写性判定，不创建任何文件。
    """
    for c in _default_user_candidates():
        if _nearest_writable_dir(c):
            return c

    fallback = os.path.join(tempfile.gettempdir(), _APP_NAME, "audit.log")
    # 用户级目录不可写：显式告警（不静默），再回退到系统临时目录
    sys.stderr.write(
        f"[audit] 警告：用户级审计目录不可写，回退到系统临时目录 {fallback}\n"
    )
    return fallback


def _default_path() -> str:
    """惰性解析并缓存默认路径（首次使用时才计算，import 期零副作用）。"""
    global _default_path_cache
    if _default_path_cache is None:
        _default_path_cache = _resolve_default_path()
    return _default_path_cache


class AuditLogger:
    def __init__(self, path: Optional[str] = None) -> None:
        # 不在此处解析默认路径，避免构造单例时的 import/实例化副作用
        self._explicit = path
        self._resolved: Optional[str] = None

    @property
    def path(self) -> str:
        if self._explicit is not None:
            return self._explicit
        env = os.getenv("HRM_AUDIT_LOG")
        if env:
            return env
        if self._resolved is None:
            self._resolved = _default_path()
        return self._resolved

    def log(self, event: str, trace_id: str = "-", **fields: Any) -> Dict[str, Any]:
        """追加一条审计记录（PII 脱敏后）。返回该记录。"""
        record = {
            "ts": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
            "trace_id": trace_id,
            "event": event,
        }
        for k, v in fields.items():
            if k in _RESERVED_KEYS:
                continue  # 保留键优先，调用方同名字段过滤丢弃
            record[k] = v
        line = json.dumps(record, ensure_ascii=False, default=str)
        line = redact_pii(line)  # 落盘前脱敏
        try:
            target = self.path
            os.makedirs(os.path.dirname(target), exist_ok=True)  # 仅真正写入时才建目录
            with _write_lock, open(target, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError as e:
            # 审计不可用不应阻断主流程，但必须显式告警（不再静默吞掉），
            # 由宿主可观测性兜底；仅告警一次避免刷屏。
            global _warned
            if not _warned:
                sys.stderr.write(
                    f"[audit] 警告：审计日志写入失败（{self.path}）：{e}；"
                    f"本次审计未落盘。\n"
                )
                _warned = True
        return record

    def tail(self, n: int = 50) -> list:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                lines = f.readlines()[-n:]
            return [json.loads(x) for x in lines if x.strip()]
        except OSError:
            return []


# 进程内共享单例（构造本身不再触发任何路径解析/文件创建）
logger = AuditLogger()
