"""
_bootstrap.py — 统一引导模块

为所有脚本提供统一的日志和配置入口，支持降级运行。

 同步要求：本文件与 config_manager/logging_manager/audit 为
核心模块的本地副本，与上游一致（sys.path 用 append
而非 insert(0) 避免同名模块覆盖、并做路径校验）保持同步；修改后请同步更新其余副本，避免再次漂移。
"""

import logging
import sys
from pathlib import Path
from typing import Any, Callable, Optional

__all__ = [
    "HAVE_COMMON", "HAVE_COMMON_MODULES",
    "init_logger", "get_config", "get_logger", "ConfigManager",
    "log_info", "log_error", "log_warning", "log_debug",
]

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    # 用 append 而非 insert(0)，
    # 避免目录内同名模块劫持标准库/第三方包（shadow injection）
    sys.path.append(str(_SCRIPTS_DIR))

try:
    from logging_manager import get_logger as _gl  # noqa
    from config_manager import ConfigManager, get_config as _gc  # noqa
    HAVE_COMMON_MODULES = True
except ImportError:
    HAVE_COMMON_MODULES = False
    # 降级兜底：ConfigManager 为 __all__ 导出（脚本可能直接引用）；get_config 的
    # 降级已由下方统一出口处理（HAVE_COMMON=False 时返回 {}），无需重复定义
    ConfigManager = lambda: None  # noqa: E731

HAVE_COMMON = HAVE_COMMON_MODULES


def init_logger(name: Optional[str] = None) -> Any:
    if name is None:
        import inspect
        frame = inspect.stack()[1]
        name = Path(frame.filename).stem
    if HAVE_COMMON:
        return _gl(name)
    lgr = logging.getLogger(name)
    if not lgr.handlers:
        h = logging.StreamHandler()
        h.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
        lgr.addHandler(h)
        lgr.setLevel(logging.INFO)
    return lgr


def get_config(*args: Any, **kwargs: Any) -> Any:
    return _gc(*args, **kwargs) if HAVE_COMMON else {}


def get_logger(name: Optional[str] = None) -> Any:
    return _gl(name) if (HAVE_COMMON and name) else init_logger(name or "_bootstrap")


def _make_log_fn(level: int) -> Callable[[str], None]:
    def fn(msg: str) -> None:
        init_logger("_bootstrap").log(level, msg)
    return fn


log_info = _make_log_fn(logging.INFO)
log_error = _make_log_fn(logging.ERROR)
log_warning = _make_log_fn(logging.WARNING)
log_debug = _make_log_fn(logging.DEBUG)

