#!/usr/bin/env python3
"""HRM Smart Solution Team（HRM 实战参谋团） · 组织健康度引擎

作者：Xing Bu

根据组织输入（团队列表 / 层级深度）计算四项健康指标并给出诊断。

输入格式（JSON，键名严格校验）：
{
  "teams": [
    {"name": "研发组", "size": 8, "manager": true, "manager_count": 1, "manager_only": false}
  ],
  "total_depth": 5
}

键名约定：
- 顶层必填 `teams`、`total_depth`，不接受未知键；
- 每个团队必填 `size`，可选 `name` / `manager` / `manager_count` / `manager_only`。

任何键名拼写错误、类型错误或缺失都会抛出 OrgSchemaError 并终止，
不会退化成"看似成功但全部指标为空"的无效报告。
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Sequence, Tuple

from errors import StructuredError


# 健康区间（含端点）
HEALTHY: Dict[str, Tuple[float, float]] = {
    "span_of_control": (5, 8),
    "hierarchy_depth": (4, 6),
    "ic_manager_ratio": (6.0, 10.0),
    "team_size": (5, 9),
}

# 临界区间：健康区外但仍在此区间内记 warning，越过则 critical
CRITICAL: Dict[str, Tuple[float, float]] = {
    "span_of_control": (3, 12),
    "hierarchy_depth": (1, 8),
    "ic_manager_ratio": (4.0, 12.0),
    "team_size": (4, 12),
}

TOP_LEVEL_REQUIRED: Tuple[str, ...] = ("teams", "total_depth")
TEAM_REQUIRED: Tuple[str, ...] = ("size",)
TEAM_OPTIONAL: Tuple[str, ...] = ("name", "manager", "manager_count", "manager_only")

SCHEMA_EXAMPLE = (
    '{"teams": [{"name": "研发组", "size": 8, "manager": true}], "total_depth": 5}'
)


class OrgSchemaError(StructuredError):
    """输入 JSON 的键名或类型不符合约定时抛出。

    继承 `StructuredError`（结构化错误码）：携带确定性 `code` / `field`，
    仍保持 `ValueError` 子类，CLI 的 `except OrgSchemaError` 不变。
    """


@dataclass
class OrgHealthResult:
    span_of_control: Dict = field(default_factory=dict)
    hierarchy_depth: Dict = field(default_factory=dict)
    ic_manager_ratio: Dict = field(default_factory=dict)
    team_size: Dict = field(default_factory=dict)
    risks: List[Dict] = field(default_factory=list)


# ---------------------------------------------------------------------------
# 输入校验（fail-fast，不做静默降级）
# ---------------------------------------------------------------------------

def _check_keys(
    scope: str,
    received: Dict,
    required: Sequence[str],
    optional: Sequence[str] = (),
) -> None:
    """校验键名集合：必填键必须齐全，且不允许出现未知键。"""
    missing = [k for k in required if k not in received]
    unknown = [k for k in received if k not in required and k not in optional]
    if not missing and not unknown:
        return

    lines = [f"{scope} 的键名不符合约定："]
    if missing:
        lines.append(" - 缺失必填键：" + ", ".join(f"`{k}`" for k in missing))
    if unknown:
        lines.append(" - 存在未知键：" + ", ".join(f"`{k}`" for k in unknown))
    lines.append(" - 必填键：" + ", ".join(f"`{k}`" for k in required))
    if optional:
        lines.append(" - 可选键：" + ", ".join(f"`{k}`" for k in optional))
    lines.append(f" - 正确示例：{SCHEMA_EXAMPLE}")
    # 缺必填键优先 E001（首个缺失键）；否则未知键 E020（首个未知键）
    if missing:
        code, field = "E001", missing[0]
    else:
        code, field = "E020", unknown[0]
    raise OrgSchemaError("\n".join(lines), code=code, field=field)


def _check_positive_int(value: Any, scope: str, minimum: int = 1) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise OrgSchemaError(
            f"{scope} 必须是 >= {minimum} 的整数，实际收到 {value!r}"
            f"（{type(value).__name__}）",
            code="E020", field=scope,
        )
    return value


def _check_bool(value: Any, scope: str) -> bool:
    if not isinstance(value, bool):
        raise OrgSchemaError(
            f"{scope} 必须是布尔值 true/false，实际收到 {value!r}"
            f"（{type(value).__name__}）",
            code="E020", field=scope,
        )
    return value


def validate_org(org: Any) -> Tuple[List[Dict], int]:
    """校验组织输入并返回 (teams, total_depth)。不合法即抛 OrgSchemaError。"""
    if not isinstance(org, dict):
        raise OrgSchemaError(
            f"组织输入必须是 JSON 对象（顶层 {{ }}），实际收到 {type(org).__name__}。"
            f"\n - 正确示例：{SCHEMA_EXAMPLE}",
            code="E020", field=None,
        )

    _check_keys("组织输入顶层", org, TOP_LEVEL_REQUIRED)

    teams = org["teams"]
    if not isinstance(teams, list):
        raise OrgSchemaError(
            f"`teams` 必须是数组，实际收到 {type(teams).__name__}",
            code="E020", field="teams",
        )
    if not teams:
        raise OrgSchemaError(
            "`teams` 为空数组：没有可诊断的团队，请至少提供 1 个团队",
            code="E001", field="teams",
        )

    for i, team in enumerate(teams):
        scope = f"teams[{i}]"
        if not isinstance(team, dict):
            raise OrgSchemaError(
                f"{scope} 必须是 JSON 对象，实际收到 {type(team).__name__}",
                code="E020", field=scope,
            )
        _check_keys(scope, team, TEAM_REQUIRED, TEAM_OPTIONAL)
        _check_positive_int(team["size"], f"{scope}.size")
        if "name" in team and not isinstance(team["name"], str):
            raise OrgSchemaError(f"{scope}.name 必须是字符串，实际收到 {team['name']!r}",
                                 code="E020", field=f"{scope}.name")
        if "manager" in team:
            _check_bool(team["manager"], f"{scope}.manager")
        if "manager_only" in team:
            _check_bool(team["manager_only"], f"{scope}.manager_only")
        if "manager_count" in team:
            _check_positive_int(team["manager_count"], f"{scope}.manager_count", minimum=0)

    total_depth = _check_positive_int(org["total_depth"], "`total_depth`（组织层级数）")
    return teams, total_depth


# ---------------------------------------------------------------------------
# 指标判定
# ---------------------------------------------------------------------------

def _status(value: float, metric: str) -> str:
    """healthy / warning / critical 判定：健康区外为 warning，越过临界为 critical。"""
    lo, hi = HEALTHY[metric]
    crit_lo, crit_hi = CRITICAL[metric]
    if value < lo:
        return "warning" if value >= crit_lo else "critical"
    if value > hi:
        return "warning" if value <= crit_hi else "critical"
    return "healthy"


def diagnose(org: Any) -> OrgHealthResult:
    """诊断组织健康度。输入 schema 不匹配时抛 OrgSchemaError。"""
    teams, total_depth = validate_org(org)

    spans: List[int] = []
    sizes: List[int] = []
    total_managers = 0
    total_ic = 0
    for team in teams:
        size = team["size"]
        has_manager = team.get("manager", False)
        is_manager_only = team.get("manager_only", False)
        mc = team.get("manager_count", None)
        sizes.append(size)
        if not is_manager_only:
            spans.append(size)
        if is_manager_only:
            # 整队都是管理者：管理者数取 manager_count（若给出且 > 0），否则取 size；无 IC
            n_mgrs = mc if (mc is not None and mc > 0) else size
            n_ic = 0
        else:
            # manager_count 优先；未给出则按 manager 布尔计 1（无 manager 则 0）
            if mc is not None and mc > 0:
                n_mgrs = mc
            else:
                n_mgrs = 1 if has_manager else 0
            n_ic = max(size - n_mgrs, 0)
        total_managers += n_mgrs
        total_ic += n_ic

    if not spans:
        raise OrgSchemaError(
            "所有团队均标记 `manager_only: true`，管理幅度无从计算。"
            "请至少保留一个承载 IC 的团队。",
            code="E001", field="teams",
        )
    if total_managers == 0:
        raise OrgSchemaError(
            "没有任何团队提供管理者（既无 `manager: true`，也无 `manager_count` > 0），"
            "IC:经理比无从计算。请为有管理者的团队显式设置 `manager: true` 或 `manager_count`。",
            code="E001", field="teams",
        )

    result = OrgHealthResult()

    avg_span = sum(spans) / len(spans)
    max_span = max(spans)
    # 平均幅度决定健康/warning；任一团队幅度越过临界即整体 critical（单团队失控）
    crit_lo, crit_hi = CRITICAL["span_of_control"]
    result.span_of_control = {
        "min": min(spans),
        "max": max_span,
        "avg": round(avg_span, 1),
        "status": (
            "critical" if max_span > crit_hi or max_span < crit_lo
            else _status(avg_span, "span_of_control")
        ),
    }

    result.hierarchy_depth = {
        "current": total_depth,
        "status": _status(total_depth, "hierarchy_depth"),
    }

    if total_ic == 0:
        result.ic_manager_ratio = {"current": f"0:{total_managers}", "status": "critical"}
    else:
        result.ic_manager_ratio = {
            "current": f"{total_ic}:{total_managers}",
            "status": _status(total_ic / total_managers, "ic_manager_ratio"),
        }

    avg_size = sum(sizes) / len(sizes)
    result.team_size = {
        "min": min(sizes),
        "max": max(sizes),
        "avg": round(avg_size, 1),
        "status": _status(avg_size, "team_size"),
    }

    for metric, label, detail in (
        (result.span_of_control, "管理裂化",
         f"平均幅度 {result.span_of_control['avg']} / 最大幅度 {result.span_of_control['max']}"),
        (result.ic_manager_ratio, "头重脚轻",
         f"IC:经理比 {result.ic_manager_ratio['current']}"),
        (result.hierarchy_depth, "决策链过长",
         f"层级 {result.hierarchy_depth['current']}"),
        (result.team_size, "团队孤立",
         f"平均团队规模 {result.team_size['avg']}"),
    ):
        if metric["status"] != "healthy":
            result.risks.append({
                "type": label,
                "severity": metric["status"].upper(),
                "detail": detail,
            })

    return result


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------

def main(argv: List[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    use_envelope = False
    if args and args[0] == "--envelope":
        use_envelope = True
        args = args[1:]
    if len(args) != 1:
        sys.stderr.write("用法: python3 org_health.py [--envelope] <org.json>\n")
        return 2

    path = args[0]
    try:
        with open(path, encoding="utf-8") as f:
            raw = f.read()
    except OSError as e:
        sys.stderr.write(f"[org-health] 无法读取输入文件 {path}：{e}\n")
        return 2

    if use_envelope:
        # 惰性导入：仅在 --envelope 时经 engine_service 中转统一 schema，避免循环导入
        from engine_service import emit_envelope
        return emit_envelope("org.health", raw)

    try:
        org = json.loads(raw)
    except json.JSONDecodeError as e:
        sys.stderr.write(f"[org-health] JSON 解析失败：{e}\n")
        return 2

    try:
        result = diagnose(org)
    except OrgSchemaError as e:
        sys.stderr.write(f"[org-health] 输入结构错误：{e}\n")
        return 2

    print(json.dumps(
        {
            "org_health": {
                "span_of_control": result.span_of_control,
                "hierarchy_depth": result.hierarchy_depth,
                "ic_manager_ratio": result.ic_manager_ratio,
                "team_size": result.team_size,
            },
            "risks": result.risks,
        },
        ensure_ascii=False, indent=2,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
