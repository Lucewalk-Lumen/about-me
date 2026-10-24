#!/usr/bin/env python3
"""HRM Smart Solution Team（HRM 实战参谋团） · 候选人五维评分引擎

作者：Xing Bu

五维评分（技术/经验/学习/匹配/稳定）加权综合 + 录用决策矩阵。
评分由调用方（LLM 解析结果）传入 0-10 数值，本引擎负责加权与决策。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from errors import StructuredError


class InputValidationError(StructuredError):
    """候选人评分子缺维/类型错误时抛出（fail-fast，替代原静默按 0 计权）。

    继承 `StructuredError`（结构化错误码）：携带确定性 `code` / `field`，
    仍保持 `ValueError` 子类，CLI 的 `except (TypeError, ValueError)` 不变。
    """


WEIGHTS: Dict[str, float] = {
    "technical": 0.25,
    "professional": 0.20,
    "learning": 0.20,
    "role_fit": 0.20,
    "stability": 0.15,
}

DIMENSION_NAMES: Dict[str, str] = {
    "technical": "技术能力",
    "professional": "专业经验",
    "learning": "学习能力",
    "role_fit": "岗位匹配",
    "stability": "稳定性",
}


@dataclass
class ScoreResult:
    dimensions: Dict[str, float]
    overall: float
    recommendation: str # recommend | conditional | not_recommend
    risk_level: str # low | medium | high
    note: str = ""


def _clamp(v: float) -> float:
    return max(0.0, min(10.0, float(v)))


def _is_score(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def validate_scores(dimensions: Dict) -> None:
    """fail-fast：五维必填且为 0-10 数字，缺维/非数字直接报错（不再按 0 计权）。"""
    if not isinstance(dimensions, dict):
        raise InputValidationError(f"评分必须是 JSON 对象，实际收到 {type(dimensions).__name__}", code="E020", field=None)
    missing = [d for d in WEIGHTS if d not in dimensions]
    if missing:
        # 字段名用反引号包裹，便于 engine_service._error_field 精确提取（多维度缺漏时一并列出）
        raise InputValidationError(
            f"缺失评分维度：{', '.join(f'`{d}`' for d in missing)}。五维必须全部提供"
            f"（technical/professional/learning/role_fit/stability）。",
            code="E001", field=", ".join(missing),
        )
    for dim in WEIGHTS:
        v = dimensions[dim]
        if not _is_score(v):
            raise InputValidationError(f"维度 `{dim}` 必须是 0-10 的数字，实际收到 {v!r}", code="E020", field=dim)
        if not (0 <= float(v) <= 10):
            raise InputValidationError(f"维度 `{dim}` 超出 0-10 范围，实际 {v}", code="E040", field=dim)


def overall_score(dimensions: Dict[str, float]) -> float:
    """加权综合分（0-10，保留 1 位）。调用前应先经 validate_scores。"""
    total = 0.0
    for dim, weight in WEIGHTS.items():
        total += _clamp(dimensions.get(dim, 0.0)) * weight
    return round(total, 1)


def decide(dimensions: Dict[str, float]) -> ScoreResult:
    """根据五维分数输出综合分 + 决策矩阵判定。缺维/类型错误抛 InputValidationError。"""
    validate_scores(dimensions)
    overall = overall_score(dimensions)
    raw = {k: _clamp(v) for k, v in dimensions.items()}

    if overall >= 8.0:
        rec, risk, note = "recommend", "low", "优质候选人，建议录用"
    elif overall >= 7.0:
        rec, risk, note = "conditional", "medium", "基本合格，有条件录用"
    elif overall >= 6.0:
        rec, risk, note = "conditional", "medium", "有短板，需谨慎评估"
    else:
        rec, risk, note = "not_recommend", "high", "不符合要求，不建议录用"

    return ScoreResult(
        dimensions=raw, overall=overall,
        recommendation=rec, risk_level=risk, note=note,
    )


def format_report(result: ScoreResult, candidate: str = "") -> str:
    """生成 Markdown 报告（与知识库 02 报告结构对齐）。"""
    header = f"## 面试评估报告 — {candidate}" if candidate else "## 面试评估报告"
    lines = [header, "", "### 五维评分", "", "| 维度 | 权重 | 评分 |", "|------|:----:|------|"]
    for dim, weight in WEIGHTS.items():
        name = DIMENSION_NAMES[dim]
        score = result.dimensions.get(dim, 0.0)
        lines.append(f"| {name} | {int(weight * 100)}% | {score:.1f} |")
    lines += [
        "", f"### 综合评分：{result.overall:.1f}/10",
        "", f"### 录用建议：{result.note}",
        f"- recommendation: {result.recommendation}",
        f"- risk_level: {result.risk_level}",
    ]
    return "\n".join(lines)


def _cli() -> int:
    import argparse
    import json

    parser = argparse.ArgumentParser(description="候选人五维评分引擎")
    parser.add_argument(
        "--scores", metavar="JSON", required=True,
        help="五维评分 JSON：{\"technical\":8.5,\"professional\":8,\"learning\":9,\"role_fit\":8.5,\"stability\":6}",
    )
    parser.add_argument("--candidate", metavar="NAME", default="", help="候选人姓名（可选，用于报告标题）")
    parser.add_argument("--format", choices=["json", "report"], default="json", help="输出格式：json 或 markdown 报告")
    parser.add_argument(
        "--envelope", action="store_true",
        help="经 engine_service.dispatch_envelope_json 输出统一 schema（status/version/payload/errors/warnings）",
    )
    args = parser.parse_args()

    if args.envelope:
        # 惰性导入：仅在 --envelope 时经 engine_service 中转统一 schema，避免循环导入
        from engine_service import emit_envelope
        return emit_envelope("candidate.score", args.scores)

    try:
        dimensions = json.loads(args.scores)
    except json.JSONDecodeError as e:
        parser.error(f"--scores 不是合法 JSON：{e}")
    if not isinstance(dimensions, dict):
        parser.error("--scores 必须是 JSON 对象（顶层 { }）")
    try:
        result = decide(dimensions)
    except (TypeError, ValueError) as e:
        parser.error(f"评分值必须是 0-10 的数字：{e}")

    if args.format == "report":
        print(format_report(result, args.candidate))
    else:
        print(json.dumps({
            "dimensions": {k: round(v, 1) for k, v in result.dimensions.items()},
            "overall": result.overall,
            "recommendation": result.recommendation,
            "risk_level": result.risk_level,
            "note": result.note,
        }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
