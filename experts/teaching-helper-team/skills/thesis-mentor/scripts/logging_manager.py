#!/usr/bin/env python3
"""
logging_manager.py
管理学论文导师技能包 — 统一日志管理模块
修复：修正 CRITICAL 拼写错误

 按「派生 fork 去重铁律」，应将本文件独有增量回灌单一真源 shared-core 并改为引用，
而非保留多份副本。本会话仅同步安全加固（未做删除式去重，避免破坏跨包运行时导入）。
"""

import logging, os, sys
from pathlib import Path
from typing import Dict, Optional

LEVEL_MAP = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


class LoggingManager:
    def __init__(self, name: str = "thesis-mentor", config: Optional[Dict] = None):
        self.name = name
        self.config = config or {}
        self.log_file = None
        self.logger = None
        self._setup()

    def _setup(self):
        self.logger = logging.getLogger(self.name)
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers.clear()
        fmt = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

        if self.config.get("console_output", True):
            ch = logging.StreamHandler(sys.stdout)
            ch.setLevel(LEVEL_MAP.get(str(self.config.get("level", "INFO")).upper(), logging.INFO))
            ch.setFormatter(fmt)
            self.logger.addHandler(ch)

        # 默认仅输出到控制台；显式开启落盘时写入用户缓存目录（XDG_CACHE_HOME 或 ~/.cache），
        # 避免把日志写进技能安装目录（会被升级/清缓存清除，且可能被重新打包分发出去）。
        if self.config.get("file_output", False):
            lf = self.config.get("log_file")
            if not lf:
                cache = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
                lf = str(Path(cache) / "workbuddy" / "thesis-mentor" / "thesis.log")
            lf = Path(lf).expanduser()
            try:
                lf.parent.mkdir(parents=True, exist_ok=True)
                fh = logging.FileHandler(str(lf), encoding="utf-8")
                fh.setLevel(logging.DEBUG)
                fh.setFormatter(fmt)
                self.logger.addHandler(fh)
                self.log_file = str(lf)
            except OSError as e:
                # 落盘失败不应中断主流程，改为纯控制台输出。
                self.logger.warning("日志文件不可写(%s)，已改为控制台输出", e)

    def _log(self, level, msg, **kw):
        self.logger.log(level, msg, extra=kw) if kw else self.logger.log(level, msg)

    def debug(self, msg, **kw): self._log(logging.DEBUG, msg, **kw)
    def info(self, msg, **kw): self._log(logging.INFO, msg, **kw)
    def warning(self, msg, **kw): self._log(logging.WARNING, msg, **kw)
    def error(self, msg, **kw): self._log(logging.ERROR, msg, **kw)
    def critical(self, msg, **kw): self._log(logging.CRITICAL, msg, **kw)
    def get_log_file(self): return self.log_file

_default_logger = None

def get_logger(name="thesis-mentor", config=None):
    global _default_logger
    if _default_logger is None:
        _default_logger = LoggingManager(name, config)
    return _default_logger
