#!/usr/bin/env python3
"""
config_manager.py — OBHRM 研究协作团配置管理器

提供统一的配置读写接口，支持 YAML/JSON 配置文件和字典式访问。
所有脚本通过此模块获取全局配置，避免硬编码和散落的环境变量读取。

用法:
    from obhrm_research_base.core.config_manager import ConfigManager, get_config
    cfg = get_config()
    output_dir = cfg.get("output_dir", "./output")
"""

import json
import logging
import os
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional

_LOGGER = logging.getLogger("obhrm.config")

# 确保本模块所在目录 obhrm_research_base/core/ 在 sys.path（与 _common_init 保持一致），
# 便于下方平铺导入 safe_path / audit_log（二者与本文件同属 obhrm_research_base/core/）。
# 改用 append 而非 insert(0)，避免该目录被置于 sys.path 搜索顺序最前，
# 从而覆盖标准库或第三方包。
_CORE_DIR = Path(__file__).resolve().parent
if str(_CORE_DIR) not in sys.path:
    sys.path.append(str(_CORE_DIR))
from safe_path import resolve_safe_output
from audit_log import log_event

# load 允许根：当前为扁平布局——本文件位于 obhrm_research_base/core/，其上级
# _PKG_DIR = obhrm_research_base/ 即 Python 包目录；技能包根在其再上一级
# (skills/obhrm-research-base/)。注释与命名一律按当前扁平布局书写。
# _PKG_DIR 仅作为 load 允许根（读取技能包内配置）；save 仅允许写入 cwd，
# 不覆写技能包自身文件。
_PKG_DIR = _CORE_DIR.parent  # obhrm_research_base/
_SKILL_DIR = _PKG_DIR  # 向后兼容别名：外部若有引用，取值与行为保持不变
# 允许根延后到调用时构造（避免模块加载时 cwd 缺失导致 FileNotFoundError）
def _load_roots():
    return [os.getcwd(), _PKG_DIR]

def _save_roots():
    return [os.getcwd()]




class ConfigManager:
    """配置管理器 — 字典式访问 + 文件持久化 + 版本控制"""

    _DEFAULTS: Dict[str, Any] = {
        "output_dir": "./output",
        "log_level": "INFO",
        "target_level": "csci",  # 目标层级：csci / ssci / 硕士 / 博士
        "language": "zh-CN",
        "charts": {
            "dpi": 300,
            "format": "png",
            "theme": "default",
        },
    }

    def __init__(self, config_path: Optional[str] = None):
        """初始化配置管理器。

        Args:
            config_path: 配置文件路径（JSON）。为 None 时只使用默认配置。
        """
        self._config: Dict[str, Any] = deepcopy(self._DEFAULTS)
        self._config_path = config_path
        self._dirty = False

        if config_path and os.path.exists(config_path):
            self.load(config_path)

    # -- 字典式访问 --
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项（支持点号分隔的嵌套键，如 'charts.dpi'）。"""
        keys = key.split(".")
        node = self._config
        for k in keys:
            if isinstance(node, dict) and k in node:
                node = node[k]
            else:
                return default
        return deepcopy(node) if isinstance(node, (dict, list)) else node

    def set(self, key: str, value: Any) -> None:
        """设置配置项（支持点号分隔的嵌套键）。"""
        keys = key.split(".")
        node = self._config
        for k in keys[:-1]:
            if k not in node:
                node[k] = {}
            node = node[k]
        node[keys[-1]] = value
        self._dirty = True

    def __getitem__(self, key: str) -> Any:
        result = self.get(key)
        if result is None:
            raise KeyError(key)
        return result

    def __contains__(self, key: str) -> bool:
        return self.get(key) is not None

    # -- 字体解析（供 docx 引擎使用） --
    def get_font(self, font_type: str = "chinese_body") -> str:
        """返回适合 docx 的字体名（CJK 友好，永不返回 None）。

        供 ``obhrm_docx_formatter.py`` 的 ``get_font_from_config`` 调用。
        解析顺序：
            1. 若配置中显式定义了 ``fonts.<font_type>`` 则优先返回；
            2. 否则按运行平台探测 CJK 友好字体；
            3. 最终结果做非空兜底，绝不会返回 ``None`` 导致下游崩溃。

        Args:
            font_type: 字体角色，支持
                ``chinese_body``/``body`` 中文正文（默认）、
                ``chinese_heading``/``heading`` 中文标题、
                ``chinese_code``/``code`` 中文代码块、
                ``english``/``en`` 英文/数字字体、
                ``default`` 默认正文。

        Returns:
            字体名字符串。
        """
        import platform

        # 配置优先级最高
        cfg_font = self.get(f"fonts.{font_type}")
        if isinstance(cfg_font, str) and cfg_font.strip():
            return cfg_font.strip()

        system = platform.system()
        # (cn_body, cn_heading, cn_code) — 与 obhrm_docx_formatter.py 平台探测保持一致
        if system == "Darwin":  # macOS
            plat = ("Songti SC", "PingFang SC", "STFangsong")
        elif system == "Windows":
            plat = ("SimSun", "SimHei", "FangSong")
        else:  # Linux 及其他
            plat = ("Noto Sans CJK SC", "Noto Sans CJK SC", "Noto Sans CJK SC")

        en_fallback = "Times New Roman"

        mapping = {
            "chinese_body": plat[0],
            "body": plat[0],
            "chinese_heading": plat[1],
            "heading": plat[1],
            "chinese_code": plat[2],
            "code": plat[2],
            "english": en_fallback,
            "en": en_fallback,
            "default": plat[0],
        }
        result = mapping.get(font_type, plat[0]) or plat[0]
        # 安全兜底：绝不返回 None / 空串
        if not result:
            result = "Calibri"
        return result

    # -- 文件持久化 --
    def load(self, path: str) -> None:
        """从 JSON 文件加载配置（合并到当前配置）。

        路径安全: path 必须落在允许根目录之内（cwd 或技能目录），
        超出允许范围（含 ``..`` 逃逸、指向系统目录等）一律抛 ValueError，绝不读取。
        """
        safe = resolve_safe_output(path, base=_load_roots())
        try:
            with open(safe, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"配置文件 JSON 解析失败：{safe}（{e}）")
        self._merge(data)
        self._config_path = str(safe)
        self._dirty = False
        log_event("config_load", path=str(safe))

    def save(self, path: Optional[str] = None) -> None:
        """保存当前配置到 JSON 文件。

        输出路径约束：target 仅允许落在 cwd 之内，不覆写技能包自身脚本。
        """
        target = path or self._config_path
        if not target:
            raise ValueError("未指定保存路径")
        safe_path = resolve_safe_output(target, base=_save_roots())
        os.makedirs(os.path.dirname(str(safe_path)) or ".", exist_ok=True)
        with open(safe_path, "w", encoding="utf-8") as f:
            json.dump(self._config, f, ensure_ascii=False, indent=2)
        self._dirty = False
        log_event("config_save", path=str(safe_path))


    # -- 内部 --
    def _merge(self, data: Dict[str, Any]) -> None:
        """深度合并配置字典（浅拷贝问题修复：使用 deepcopy）。"""
        for key, value in data.items():
            if key in self._config and isinstance(self._config[key], dict) and isinstance(value, dict):
                self._merge_dict(self._config[key], value)
            else:
                self._config[key] = deepcopy(value)

    @staticmethod
    def _merge_dict(target: dict, source: dict) -> None:
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                ConfigManager._merge_dict(target[key], value)
            else:
                target[key] = deepcopy(value)

    def to_dict(self) -> Dict[str, Any]:
        """返回配置的深拷贝字典。"""
        return deepcopy(self._config)


# 全局单例
_default_config: Optional[ConfigManager] = None


def get_config(config_path: Optional[str] = None) -> ConfigManager:
    """获取全局配置管理器（单例模式）。

    Args:
        config_path: 可选的配置文件路径。仅在首次调用时生效。

    Returns:
        ConfigManager 实例
    """
    global _default_config
    if _default_config is None:
        _default_config = ConfigManager(config_path)
    return _default_config


def reset_config() -> None:
    """重置全局配置（主要用于测试）。"""
    global _default_config
    _default_config = None


__all__ = [
    "ConfigManager",
    "get_config",
    "reset_config",
]
