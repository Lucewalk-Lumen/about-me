#!/usr/bin/env python3
"""SBTI 人格结果计算引擎（32 题确定性人格匹配）。

根据用户的 32 题作答，计算各维度得分、匹配最近似人格类型，并返回完整结果 JSON。
计算过程确定性，相同输入始终产生相同输出。

用法：
  python3 scripts/sbti_assessment.py --answers '{"q1": 1, "q2": 3, ...}'

路径解析：脚本位于 skills/hrm-solution/scripts/，资产位于 skills/personality-assessment/assets/sbti/。
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

try:  # 与 hrm-solution/scripts/errors.py 同源；跨目录调用时回退为同构内置定义
    from errors import StructuredError
except ImportError:  # pragma: no cover - 仅在被当作独立模块导入时触发
    class StructuredError(ValueError):  # type: ignore[no-redef]
        """结构化错误（与 errors.py 同构的最小回退实现）。"""

        def __init__(self, message: str, code: str | None = None,
                     field: str | None = None, severity: str = "fatal") -> None:
            super().__init__(message)
            self.message = message
            self.code = code
            self.field = field
            self.severity = severity


# 15 个维度的固定顺序，与题库 JSON 中的 dim 字段对应
DIM_ORDER: List[str] = [
    "S1", "S2", "S3",
    "E1", "E2", "E3",
    "A1", "A2", "A3",
    "Ac1", "Ac2", "Ac3",
    "So1", "So2", "So3",
]


def _skill_root() -> Path:
    """返回资产根目录：skills/personality-assessment/assets/sbti/。

    架构重构将 SBTI 资产（题库 / 人格海报 / 图片映射表）随
    personality-assessment 技能下沉至该技能目录；脚本位于
    skills/hrm-solution/scripts/，故向上三级到 skills/ 后再进入
    personality-assessment/assets/sbti。
    """
    return Path(__file__).resolve().parent.parent.parent / "personality-assessment" / "assets" / "sbti"


def load_test_data() -> Dict[str, Any]:
    """加载题库与人格文案数据。"""
    p = _skill_root() / "data" / "sbti_questions.json"
    return json.loads(p.read_text(encoding="utf-8"))


def load_image_map() -> Dict[str, str]:
    """加载人格 code → 海报图文件名的映射表。"""
    p = _skill_root() / "personality_image_map.json"
    return json.loads(p.read_text(encoding="utf-8"))


def level_from_dim_sum(total: int) -> str:
    """将维度原始得分转换为 L/M/H 三档等级。"""
    if total <= 3:
        return "L"
    if total == 4:
        return "M"
    return "H"


def level_to_num(level: str) -> int:
    """将等级字符映射为数值，用于模式距离计算。"""
    return {"L": 1, "M": 2, "H": 3}[level]


def _allowed_values(question: Dict[str, Any]) -> set:
    """取该题声明的可选值集合（题库 options[].value），未声明时返回空集。"""
    values = set()
    for opt in question.get("options") or []:
        if isinstance(opt, dict) and isinstance(opt.get("value"), int):
            values.add(opt["value"])
    return values


def _validate_answer(qid: str, raw: Any, question: Dict[str, Any]) -> int:
    """校验单题作答：必须是题目声明的可选值之一。

    作答必须是题目声明的可选值之一：0 / -5 / 99 等越界值会污染维度累加
    （99 会把维度分推到 100 而判为 "H"），None 会抛裸 TypeError；
    越界作答属输入错误，须 fail-fast。
    """
    if isinstance(raw, bool) or not isinstance(raw, int):
        raise StructuredError(
            f"题目 {qid} 的作答必须是整数，实际收到 {raw!r}（{type(raw).__name__}）",
            code="E020", field=qid,
        )
    allowed = _allowed_values(question)
    if allowed and raw not in allowed:
        raise StructuredError(
            f"题目 {qid} 的作答 {raw} 超出可选范围 {sorted(allowed)}",
            code="E040", field=qid,
        )
    return raw


def build_user_levels(answers: Dict[str, int], test_data: Dict[str, Any]) -> Dict[str, str]:
    """遍历题目定义，按维度累加得分，返回每个维度的 L/M/H 等级。"""
    sums: Dict[str, int] = {d: 0 for d in DIM_ORDER}

    for q in test_data["questions"]:
        qid = q["id"]
        # 隐藏分支题（special 字段标记）：仅作背景采集——校验取值合法性，但不参与维度累加
        if q.get("special"):
            _validate_answer(qid, answers[qid], q)
            continue

        dim = q["dim"]
        if dim not in sums:
            continue

        if qid not in answers:
            raise ValueError(f"缺少必填题目的作答：{qid}")
        sums[dim] += _validate_answer(qid, answers[qid], q)

    return {dim: level_from_dim_sum(total) for dim, total in sums.items()}


def levels_to_pattern(levels: Dict[str, str]) -> str:
    """将 15 个维度等级拼接为 5 组 3 字符的模式串，如 LMH-HML-..."""
    letters = [levels[d] for d in DIM_ORDER]
    groups = ["".join(letters[i: i + 3]) for i in range(0, 15, 3)]
    return "-".join(groups)


@dataclass
class Match:
    """单个人格类型的匹配评分结果。"""
    code: str
    pattern: str
    distance: int # 越小越近
    exact: int # 完全匹配的维度数，越大越好
    similarity: int # 综合相似度百分比，越大越好


def score_matches(user_levels: Dict[str, str], test_data: Dict[str, Any]) -> List[Match]:
    """对所有已知人格类型打分，按 distance 升序、exact 降序、similarity 降序排列。"""
    user_nums = [level_to_num(user_levels[d]) for d in DIM_ORDER]

    patterns_raw = test_data.get("patterns") or []
    patterns: Dict[str, str] = {}
    if isinstance(patterns_raw, list):
        for item in patterns_raw:
            patterns[item["code"]] = item["pattern"]
    else:
        patterns = patterns_raw

    matches: List[Match] = []

    for code, ptn in patterns.items():
        p_letters = [c for c in ptn.replace("-", "")]
        if len(p_letters) != 15:
            continue

        p_nums = [level_to_num(ch) for ch in p_letters]
        diffs = [abs(a - b) for a, b in zip(user_nums, p_nums)]
        total_distance = int(sum(diffs))
        exact = int(sum(1 for d in diffs if d == 0))
        similarity = max(0, int(round((1 - total_distance / 30) * 100)))

        matches.append(Match(
            code=code,
            pattern=ptn,
            distance=total_distance,
            exact=exact,
            similarity=similarity,
        ))

    matches.sort(key=lambda m: (m.distance, -m.exact, -m.similarity))
    return matches


def pick_final_code(answers: Dict[str, int], matches: List[Match]) -> Tuple[str, str]:
    """根据匹配度阈值，确定最终人格 code。

    注：原「彩蛋 1」（隐藏题作答强制改判为特定人格）已于内容合规格审查中移除。
    饮酒/爱好类隐藏题属非能力信息，不得改变测评结果，故不再参与最终判定。
    """

    if not matches:
        return "HHHH", "无可用常规人格匹配模型，结果使用兜底人格 HHHH。"

    best = matches[0]

    # 兜底规则：最高匹配度 < 60% → 兜底 HHHH
    if best.similarity < 60:
        return "HHHH", (
            f"常规人格最高匹配度仅 {best.similarity}%（< 60%），触发兜底人格 HHHH。"
        )

    return best.code, (
        f"按 Distance 最小、Exact 最大、Similarity 最高排序，主类型人格为 {best.code}（Similarity={best.similarity}%）。"
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="SBTI 人格结果计算引擎")
    ap.add_argument(
        "--answers",
        required=True,
        help='JSON 字符串，格式：\'{"q1": 1, "q2": 3, ...}\'',
    )
    args = ap.parse_args()

    # 友好报错：JSON 解析失败 / 非对象 / 值非整数 一律给出明确提示，不抛裸 traceback
    try:
        raw = json.loads(args.answers)
    except json.JSONDecodeError as e:
        sys.stderr.write(f"[ERR] --answers 不是合法 JSON：{e}\n")
        return 2
    if not isinstance(raw, dict):
        sys.stderr.write("[ERR] --answers 必须是 JSON 对象（顶层 { }），如 '{\"q1\": 1, ...}'\n")
        return 2
    # 原值透传：不在此处做 int() 强转（那会把 2.7 静默截断为 2、把 True 视作 1），
    # 逐题的类型与取值范围校验统一由 build_user_levels → _validate_answer 负责。
    answers: Dict[str, Any] = dict(raw)

    test_data = load_test_data()
    image_map = load_image_map()

    # 键集合 fail-fast（对齐 org_health.py 的严格 schema 风格，禁止静默忽略脏输入）：
    # 未知键（不在题库 32 题中，如 q31+ / 手误键名）一律拒绝。
    valid_keys = {q["id"] for q in test_data["questions"]}
    unknown = sorted(k for k in answers if k not in valid_keys)
    if unknown:
        sys.stderr.write(
            f"[ERR] 存在未知作答键（不在 32 题题库中，共 {len(unknown)} 个）："
            + ", ".join(f"`{k}`" for k in unknown)
            + "\n"
        )
        return 2

    # 缺题友好提示：一次性列出全部缺失的必答题目。
    # 隐藏题（drink_gate_q1/q2）同为必答（仅不参与人格判定），与 SKILL.md 契约一致。
    required = [q["id"] for q in test_data["questions"]]
    missing = [qid for qid in required if qid not in answers]
    if missing:
        sys.stderr.write(
            f"[ERR] 缺少必填题目的作答（共 {len(missing)} 题）：{', '.join(missing)}\n"
        )
        return 2

    try:
        user_levels = build_user_levels(answers=answers, test_data=test_data)
    except ValueError as e:
        sys.stderr.write(f"[ERR] {e}\n")
        return 2
    user_pattern = levels_to_pattern(user_levels)

    matches = score_matches(user_levels=user_levels, test_data=test_data)
    final_code, reason = pick_final_code(answers=answers, matches=matches)

    result_def = (test_data.get("results_mapping") or {}).get(final_code) or {}

    out = {
        "final": {
            "code": final_code,
            "cn": result_def.get("cn"),
            "intro": result_def.get("intro"),
            "desc": result_def.get("desc"),
            "image": {
                "file_name": image_map.get(final_code),
                "relative_path": (
                    f"assets/sbti/images/{image_map.get(final_code)}"
                    if image_map.get(final_code) else None
                ),
            },
        },
        "reason": reason,
        "user": {
            "levels": user_levels,
            "pattern": user_pattern,
        },
        "best_match": (
            {
                "code": matches[0].code,
                "pattern": matches[0].pattern,
                "distance": matches[0].distance,
                "exact": matches[0].exact,
                "similarity": matches[0].similarity,
            }
            if matches else None
        ),
    }

    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
