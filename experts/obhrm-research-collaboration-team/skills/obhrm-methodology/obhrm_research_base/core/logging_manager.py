#!/usr/bin/env python3
"""
logging_manager.py — OBHRM 研究协作团统一日志管理器

提供标准化的日志记录接口，所有脚本和工作流通过此模块获取日志器。
支持多级别日志输出（DEBUG/INFO/WARNING/ERROR/CRITICAL），
自动格式化时间戳和模块名。

用法:
    from obhrm_research_base.core.logging_manager import get_logger
    logger = get_logger("my_module")
    logger.info("操作成功")
"""

import logging
import sys
from typing import Optional


class LoggingManager:
    """日志管理器 — 封装标准 logging 模块，提供统一接口"""

    def __init__(self, name: str, level: int = logging.INFO):
        self._name = name
        self._logger = logging.getLogger(name)
        if not self._logger.handlers:
            handler = logging.StreamHandler(sys.stderr)
            formatter = logging.Formatter(
                "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            handler.setFormatter(formatter)
            self._logger.addHandler(handler)
        self._logger.setLevel(level)

    # -- 标准日志方法 --
    def debug(self, msg: str, *args, **kwargs) -> None:
        self._logger.debug(msg, *args, **kwargs)

    def info(self, msg: str, *args, **kwargs) -> None:
        self._logger.info(msg, *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs) -> None:
        self._logger.warning(msg, *args, **kwargs)

    def error(self, msg: str, *args, **kwargs) -> None:
        self._logger.error(msg, *args, **kwargs)

    def critical(self, msg: str, *args, **kwargs) -> None:
        self._logger.critical(msg, *args, **kwargs)

    # -- 兼容别名 --
    def log_debug(self, msg: str) -> None:
        self.debug(msg)

    def log_info(self, msg: str) -> None:
        self.info(msg)

    def log_warning(self, msg: str) -> None:
        self.warning(msg)

    def log_error(self, msg: str) -> None:
        self.error(msg)

    def log_critical(self, msg: str) -> None:
        self.critical(msg)


# 模块级日志器缓存
_loggers: dict = {}


def get_logger(name: Optional[str] = None) -> LoggingManager:
    """获取或创建指定名称的日志器（单例模式）。

    Args:
        name: 日志器名称。为 None 时自动推断调用模块名。

    Returns:
        LoggingManager 实例
    """
    if name is None:
        import inspect

        frame = inspect.stack()[1]
        name = frame.frame.f_globals.get("__name__", "unknown")

    if name not in _loggers:
        _loggers[name] = LoggingManager(name)
    return _loggers[name]


# 便捷函数（与 _common_init.py 降级函数接口一致）
def log_debug(msg: str) -> None:
    get_logger().debug(msg)


def log_info(msg: str) -> None:
    get_logger().info(msg)


def log_warning(msg: str) -> None:
    get_logger().warning(msg)


def log_error(msg: str) -> None:
    get_logger().error(msg)


__all__ = [
    "LoggingManager",
    "get_logger",
    "log_debug",
    "log_info",
    "log_warning",
    "log_error",
]
