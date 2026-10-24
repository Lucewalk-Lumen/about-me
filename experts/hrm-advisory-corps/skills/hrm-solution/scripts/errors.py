#!/usr/bin/env python3
"""HRM 实战参谋团 · 结构化错误基类。

提供 `StructuredError(ValueError)`，携带确定性错误码 `code` / 出错字段 `field` /
严重度 `severity`，供 `engine_service` 统一映射为 `errors[]` 数组，替代关键词启发式
映射（原 `_classify_error` 关键词法）。

设计要点：
- 继承 `ValueError`：三引擎异常改为继承本类后，各引擎 CLI 的
  `except (TypeError, ValueError)` 仍按既有行为生效，退出码不变（向后兼容）。
- `code` / `field` 在 raise 站点显式给定（见 `scripts/INDEX.md` 错误码字典），
  由数据确定性决定，不依赖异常消息措辞。
- 本模块不导入任何其它模块，确保 `engine_service` ↔ 三引擎 ↔ `errors` 之间无环。
"""
from __future__ import annotations

import typing


class StructuredError(ValueError):
    """结构化错误基类：携带确定性错误码 / 出错字段 / 严重度。

    属性：
        message: 错误描述文本（与 ``str(self)`` 一致）
        code: 统一错误码（E001/E020/E040/E060/E080/E099 等），可空
        field: 出错字段名（多字段用 ", " 拼接），可空
        severity:"fatal"（错误）或 "warning"（警告）
    """

    def __init__(
        self,
        message: str,
        code: typing.Optional[str] = None,
        field: typing.Optional[str] = None,
        severity: str = "fatal",
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.field = field
        self.severity = severity

    def __str__(self) -> str:
        return self.message
