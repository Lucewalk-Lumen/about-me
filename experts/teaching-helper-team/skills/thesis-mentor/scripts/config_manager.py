#!/usr/bin/env python3
"""
config_manager.py
管理学论文导师技能包 — 统一配置管理模块
修复：浅拷贝问题（使用 copy.deepcopy）
"""

import copy, json
from pathlib import Path
from typing import Any, Dict, Optional

DEFAULT_CONFIG = {
    "general": {"skill_name": "thesis-mentor", "version": "1.0.2", "language": "zh-CN", "config_version": "1.0"},
    "thesis": {
        "dimensions": ["选题价值", "理论贡献", "方法严谨", "论证逻辑", "格式规范", "实践意义"],
        "extra_dims": ["创新点", "数据支撑", "结构清晰", "表达准确"],
        "ai_detection_threshold": 4,
    },
    "document": {"default_font_size": 11, "title_font_size": 18, "heading_font_size": 14, "line_spacing": 1.5},
    "logging": {"level": "INFO", "log_file": "thesis.log", "console_output": True, "file_output": True},
    "paths": {"references_dir": "references", "templates_dir": "templates", "scripts_dir": "scripts", "output_dir": "outputs"},
}


class ConfigManager:
    def __init__(self, config_file: Optional[str] = None):
        self.config: Dict[str, Any] = copy.deepcopy(DEFAULT_CONFIG)
        self.config_file = config_file
        if config_file and Path(config_file).exists():
            self.load(config_file)

    def load(self, config_file: str) -> None:
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                self._merge_config(json.load(f))
        except Exception as e:
            print(f"[WARN] 无法加载配置: {e}，使用默认配置")

    def _merge_config(self, user_config: Dict) -> None:
        for key, value in user_config.items():
            if key in self.config and isinstance(self.config[key], dict) and isinstance(value, dict):
                self.config[key] = copy.deepcopy(self.config[key])
                self.config[key].update(copy.deepcopy(value))
            else:
                self.config[key] = copy.deepcopy(value)

    def save(self, config_file: str) -> None:
        # 约束：禁止覆写技能包自身目录内的文件，仅允许写入技能包目录之外的路径（如用户工作目录）。
        target = Path(config_file).resolve()
        skill_root = Path(__file__).resolve().parent  # scripts/
        pkg_root = skill_root
        for p in [skill_root, *skill_root.parents]:
            if (p / "SKILL.md").exists():
                pkg_root = p
                break
        in_pkg = False
        try:
            target.relative_to(pkg_root.resolve())
            in_pkg = True
        except ValueError:
            in_pkg = False
        if in_pkg:
            raise ValueError(
                f"安全策略拒绝：config_manager.save() 不允许写入技能包目录内 ({target})，"
                f"以防覆写脚本。请将配置保存到技能包之外的路径（如用户工作目录）。")
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)

    def get(self, section: str, key: Optional[str] = None, default: Any = None) -> Any:
        if key is None:
            return copy.deepcopy(self.config.get(section, default))
        sec = self.config.get(section, {})
        return copy.deepcopy(sec.get(key, default)) if isinstance(sec, dict) else default

    def set(self, section: str, key: str, value: Any) -> None:
        if section not in self.config:
            self.config[section] = {}
        if isinstance(self.config[section], dict):
            self.config[section][key] = copy.deepcopy(value)

    def validate(self): return {"valid": True, "issues": []}

_default_cm = None

def get_config(config_file=None):
    global _default_cm
    if _default_cm is None:
        _default_cm = ConfigManager(config_file)
    return _default_cm
