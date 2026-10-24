#!/usr/bin/env python3
"""
_common_init.py — OBHRM 研究协作团统一引导模块

自动处理公共模块导入和日志初始化，消除各脚本中的重复导入代码。
所有业务脚本只需 `from _common_init import init_logger, HAVE_COMMON` 即可。

用法:
    from _common_init import init_logger, HAVE_COMMON
    logger = init_logger(__name__)
"""

import sys
from pathlib import Path

# 确保本模块所在目录 obhrm_research_base/core/ 在 sys.path 中，使下方 `from config_manager import ...`
# 这类同目录平铺导入在任意工作目录下都成立（config_manager.py / logging_manager.py 与
# 本文件同属 obhrm_research_base/core/）。注意：此处加入的是 obhrm_research_base/core/，不是 scripts/——脚本目录由各脚本
# 自身的引导头负责，本模块不承担该职责。
# 改用 append 而非 insert(0)，将目录追加到 sys.path 末尾，
# 避免目录内同名模块覆盖标准库或第三方包（sys.path 越靠前优先级越高）。
_CORE_DIR = Path(__file__).resolve().parent
if str(_CORE_DIR) not in sys.path:
    sys.path.append(str(_CORE_DIR))

# 尝试导入公共模块
try:
    from config_manager import ConfigManager, get_config
    from logging_manager import get_logger, log_debug, log_error, log_info, log_warning

    HAVE_COMMON = True
except ImportError:
    HAVE_COMMON = False

    # 提供空操作降级函数，避免调用方每次检查 HAVE_COMMON
    def get_config(*args, **kwargs):  # noqa: E306  # type: ignore[misc]
        return None

    def ConfigManager(*args, **kwargs):  # noqa: E306, N802  # type: ignore[misc]
        return None

    def get_logger(*args, **kwargs):  # noqa: E306  # type: ignore[misc]
        return None

    def log_info(*args, **kwargs):  # noqa: E306  # type: ignore[misc]
        pass

    def log_error(*args, **kwargs):  # noqa: E306  # type: ignore[misc]
        pass

    def log_warning(*args, **kwargs):  # noqa: E306  # type: ignore[misc]
        pass

    def log_debug(*args, **kwargs):  # noqa: E306  # type: ignore[misc]
        pass


# 向后兼容别名
HAVE_COMMON_MODULES = HAVE_COMMON


def init_logger(name: str = None):
    """
    初始化脚本日志器。

    Args:
        name: 日志器名称。若为 None，根据调用栈自动推断调用脚本名。

    Returns:
        logging.Logger 实例
    """
    if HAVE_COMMON:
        if name is None:
            import inspect

            frame = inspect.stack()[1]
            name = Path(frame.filename).stem
        return get_logger(name)
    else:
        import logging

        logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
        if name is None:
            import inspect

            frame = inspect.stack()[1]
            name = Path(frame.filename).stem
        return logging.getLogger(name)


__all__ = [
    "HAVE_COMMON",
    "HAVE_COMMON_MODULES",
    "init_logger",
    "get_config",
    "ConfigManager",
    "get_logger",
    "log_info",
    "log_error",
    "log_warning",
    "log_debug",
]
