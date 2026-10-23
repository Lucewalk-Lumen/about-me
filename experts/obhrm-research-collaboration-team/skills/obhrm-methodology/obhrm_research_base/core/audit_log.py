#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
audit_log.py — OBHRM 研究协作团运行留痕日志

仅依赖标准库，将安全相关动作（配置读写 / 文件写出 / 外部网络请求 / 受限文件读取）
以追加方式写入审计日志，便于事后溯源。

设计原则（#22 /  修订）:
- 零新增依赖: 仅用标准库（os / json / logging / threading / datetime / pathlib）。
- 失败可见: 任何审计写入异常都**不再静默吞掉**，而是向 stderr 打印一次
  ``logging.error``、递增失败计数器并返回 ``False``，便于调用方/冒烟测试感知。
- 线程安全: 写文件用进程内锁串行化，避免多脚本并发写损坏日志行。
- 外置落点: 默认写入**包目录之外**的可写目录（``OBHRM_LOG_DIR`` 或
  ``$XDG_STATE_HOME/obhrm/audit.log`` 及其平台等价路径），不再落包目录，
  避免污染分发产物与触发只读挂载写入失败。
- 隐私最小化：记录的 ``source`` URL 会剔除查询串与片段；设置
  ``OBHRM_AUDIT_OFF=1`` 可完全关闭审计日志（log_event 直接 no-op 不落盘）。

用法:
    from audit_log import log_event
    log_event("config_save", path=str(safe_path))
    log_event("network_request", source="https://api.crossref.org/works")
    log_event("read_image_blocked", path=os.path.join(os.sep, "tmp", "obhrm_security_test_blocked"))
"""

import json
import logging
import os
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# 进程内锁，保证多线/多子进程并发追加写入不互相交错损坏日志行。
_AUDIT_LOCK = threading.Lock()

# 审计日志默认写入**包目录之外**的可写目录（见 _default_audit_path）。
# 可由 set_audit_log() 覆盖。
_audit_log_path: Optional[Path] = None

# 失败计数：连续/累计的审计写入失败次数，供冒烟测试与运行态监控读取。
_failure_count: int = 0

# 隐私退出开关：设置 ``OBHRM_AUDIT_OFF=1`` 后，log_event 直接返回
# True 且不落盘，便于隐私敏感用户完全关闭本地审计日志。审计仅写入本机，
# 此开关确保用户可自主决定不生成任何审计文件。
ENV_AUDIT_OFF = "OBHRM_AUDIT_OFF"


def _strip_url_query_fragment(url):
    """剔除 URL 的查询串与片段（隐私最小化，避免 token / session / 埋点外泄）。"""
    if not isinstance(url, str):
        return url
    url = url.split("#", 1)[0]
    url = url.split("?", 1)[0]
    return url

# 专用 logger，默认 INFO 及以上输出到 stderr（logging 基础行为），
# 保证审计失败可见、可重定向，且不依赖任何全局 logging 配置。
_LOGGER = logging.getLogger("obhrm.audit")


def _default_audit_path() -> Path:
    """计算默认审计日志路径（包目录之外、宿主可写）。

    优先级：
    1. ``OBHRM_LOG_DIR`` 环境变量（若存在，落其下的 ``audit.log``）。
    2. ``$XDG_STATE_HOME/obhrm/audit.log``（Linux 规范）。
    3. 平台等价：macOS ``~/Library/Logs/obhrm/audit.log``；
       Windows ``%LOCALAPPDATA%/obhrm/audit.log``；其余同 XDG。
    """
    env = os.environ.get("OBHRM_LOG_DIR")
    if env:
        return Path(env).expanduser().resolve() / "audit.log"
    xdg = os.environ.get("XDG_STATE_HOME")
    if xdg:
        base = Path(xdg).expanduser()
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Logs"
    elif sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
    else:
        base = Path.home() / ".local" / "state"
    return (base / "obhrm" / "audit.log").resolve()


def set_audit_log(path=None) -> Path:
    """设置审计日志文件路径（默认落到包目录之外的可写位置）。

    Args:
        path: 自定义日志路径；为 None 时使用外置默认路径（见 ``_default_audit_path``）。

    Returns:
        最终生效的日志路径（Path）。
    """
    global _audit_log_path
    if path is None:
        _audit_log_path = _default_audit_path()
    else:
        _audit_log_path = Path(path).resolve()
    return _audit_log_path


def get_audit_log_path() -> Path:
    """返回当前审计日志路径（惰性初始化为外置默认路径）。"""
    if _audit_log_path is None:
        set_audit_log()
    return _audit_log_path


def get_audit_failure_count() -> int:
    """返回累计审计写入失败次数（使失败可见、可断言）。"""
    return _failure_count


def log_event(action: str, path: Optional[str] = None, source: Optional[str] = None,
              detail: Optional[str] = None) -> bool:
    """记录一条安全相关审计事件。

    Args:
        action: 动作类型，如 ``config_load`` / ``config_save`` / ``write_docx`` /
                ``network_request`` / ``read_markdown`` / ``read_image`` /
                ``read_image_blocked``。
        path:   涉及的文件路径（写入/读取动作）。
        source: 外部来源（如网络请求的 URL）。
        detail: 其它补充信息。

    Returns:
        ``True`` 表示写入成功；``False`` 表示写入失败（已向 stderr 记录，
        并递增失败计数）。**不再静默吞异常**。

    注意：审计失败**不应**阻断主流程（审计只是溯源手段），但必须可见——
    故失败时返回 ``False`` 并打印一次 ``logging.error``，由调用方决定如何应对。
    """
    global _failure_count
    # 隐私退出：OBHRM_AUDIT_OFF=1 时不再写入任何审计记录。
    if os.environ.get(ENV_AUDIT_OFF) in ("1", "true", "yes", "on"):
        return True
    try:
        log_path = get_audit_log_path()
        # 确保父目录存在（外置目录可能尚未创建）。若创建失败也进入 except 分支，
        # 由下面的 fail-visible 逻辑统一处理，不会静默。
        log_path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "action": str(action),
        }
        if path is not None:
            record["path"] = str(path)
        if source is not None:
            # 隐私最小化：剔除 URL 查询串 / 片段后再记录。
            record["source"] = str(_strip_url_query_fragment(source))
        if detail is not None:
            record["detail"] = str(detail)
        line = json.dumps(record, ensure_ascii=False)
        with _AUDIT_LOCK:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        return True
    except Exception as exc:  # noqa: BLE001 - 审计失败必须可见，而非吞掉
        _failure_count += 1
        _LOGGER.error(
            "审计日志写入失败（累计 %d 次）：%s -> %s",
            _failure_count, exc,
            get_audit_log_path() if _audit_log_path else "(未初始化)",
        )
        return False


__all__ = [
    "log_event",
    "set_audit_log",
    "get_audit_log_path",
    "get_audit_failure_count",
]
