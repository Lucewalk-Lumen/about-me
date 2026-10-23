#!/usr/bin/env python3
"""HRM 实战参谋团 · 计算引擎服务（进程内注册）

把三个独立脚本（payroll_engine / candidate_scorer / org_health）收敛为统一服务：
- 进程内：`dispatch(endpoint, payload)` 直接调用，供 Agent/编排层复用
- 统一 schema：`dispatch_envelope(endpoint, payload)` 返回
  `{status, version, baseline_date, payload, errors, warnings}`（见 knowledge-map.md）

入参兼容既有 camelCase JSON；缺失/类型错误一律 fail-fast（抛 *Error）。
出参统一 snake_case。
"""
from __future__ import annotations

import json
import re
from decimal import Decimal, InvalidOperation
from typing import Any, Callable, Dict, List

from payroll_engine import (
    calculate_year_end_bonus, bonus_result_to_dict, payroll_monthly_from_payload,
    InputValidationError as PayrollInputError,
)
from candidate_scorer import decide, InputValidationError as CandidateInputError
from org_health import diagnose, OrgSchemaError

__all__ = ["dispatch", "dispatch_envelope", "dispatch_envelope_json", "emit_envelope", "ENDPOINTS", "EngineError"]

# 统一 schema 元信息（见 knowledge-map.md）
SCHEMA_VERSION = "3.3.0"
# 各端点法规/政策数据基准日期：payroll 为 2026 税率表；org_health 无政策依赖用包版本日
BASELINE_DATE: Dict[str, str] = {
    "payroll.monthly": "2026-01-01",
    "payroll.bonus": "2026-01-01",
    "candidate.score": "2026-01-01",
    "org.health": "2026-01-01",
}


class EngineError(Exception):
    """引擎层统一错误；含 HTTP 状态码建议。"""
    status = 400


class _BadRequest(EngineError):
    status = 400

    def __init__(self, message: str, code: str | None = None, field: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.field = field

    def __str__(self) -> str:
        return self.message


class _NotFound(EngineError):
    status = 404
    code = "E080"


def _decimal_default(o):
    if isinstance(o, Decimal):
        return str(o)
    raise TypeError(f"not serializable: {type(o)}")


def _to_jsonable(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_jsonable(v) for v in obj]
    if isinstance(obj, Decimal):
        return str(obj)
    return obj


def _classify_error(endpoint: str, exc: Exception) -> str:
    """确定性地把引擎异常映射为统一错误码（结构化，替代关键词启发式）。

    优先级：
    1. 未知端点 `_NotFound` → 恒定 `E080`；
    2. 直抛的 `_BadRequest`（如 bonusAmount 类型错 / payload 非对象）→ 读自身 `.code`（默认 `E020`）；
    3. 包装的引擎异常（`dispatch` 中 `raise _BadRequest(str(e)) from e`）→ 读 `exc.__cause__.code`
       （`orig` 即带 `.code` 的引擎异常 `StructuredError`）；
    4. 兜底旧关键词启发式 `_classify_error_legacy`（理论不再命中，仅防御性保留函数体）。
    """
    if isinstance(exc, _NotFound):
        return "E080"
    if isinstance(exc, _BadRequest):
        code = getattr(exc, "code", None)
        if code:
            return code
        return "E020"
    cause = getattr(exc, "__cause__", None)
    if cause is not None:
        code = getattr(cause, "code", None)
        if code:
            return code
    return _classify_error_legacy(exc)


def _classify_error_legacy(exc: Exception) -> str:
    """关键词启发式兜底（防御性兜底，无法归类时返回 E099）。

    映射规则基于异常消息关键词，保守判定；无法归类时兜底 E099。
    """
    msg = str(exc)
    if "未知端点" in msg:
        return "E080" # 内部错误（端点不存在）
    if "非法 JSON" in msg:
        return "E020" # 类型/格式错误
    if ("累计" in msg and "完整提供" in msg) or "部分提供" in msg:
        return "E060" # 跨字段约束违反
    if "不能为负数" in msg or "越界" in msg or "超出" in msg:
        return "E040" # 值越界
    if "必须是" in msg or "类型" in msg or "不是" in msg:
        return "E020" # 类型错误
    if "缺失" in msg or "必填" in msg or "缺" in msg:
        return "E001" # 缺必填字段
    return "E099" # 内部错误（未归类）


def _error_field(exc: Exception) -> Any:
    """从异常中提取出错字段名（优先读结构化字段，回退正则提取）。

    优先级：
    1. `exc.__cause__.field`（包装的引擎异常所带确定性字段）；
    2. 直抛 `_BadRequest` 自身 `.field`（如 bonusAmount 类型错）；
    3. 回退正则提取反引号字段（保序去重，沿用既有行为）。

    返回类型保持 str | None，契约不变。
    """
    cause = getattr(exc, "__cause__", None)
    if cause is not None and getattr(cause, "field", None):
        return cause.field
    direct_field = getattr(exc, "field", None)
    if direct_field:
        return direct_field
    msg = str(exc)
    fields = re.findall(r"`([^`]+)`", msg)
    if not fields:
        return None
    # 去重保序：同一字段在消息中可能被列出多次（如「缺失必填键/必填键」）
    seen, uniq = set(), []
    for f in fields:
        if f not in seen:
            seen.add(f)
            uniq.append(f)
    return ", ".join(uniq)


def _derive_warnings(endpoint: str, in_payload: Dict, out_payload: Dict) -> List[Dict]:
    """从成功计算结果推导非致命警告。

    触发条件全部可由现有字段推导：
    - W001 payroll.bonus：输出 `in_trap_range is True`（引擎已算出的跳档陷阱），
      field=`bonusAmount`，message 直接取引擎算出的 `trap_note`；
    - W002 payroll.monthly：输入未提供任一累计值（cumulativeIncome/Insurance/Special
      均缺失或 null）且 `month > 1`，field=`cumulativeIncome`，固定规约文案；
    - W003 org.health：输出 `risks[]` 中存在 `severity == "WARNING"` 的软风险，
      逐条投影为 warning（payload.risks 仍作为权威完整列表保留）。

    不改动任何引擎 `_ep_*` 处理器与旧 `dispatch` 的返回结构（向后兼容）。
    """
    warnings: List[Dict] = []
    if endpoint == "payroll.bonus":
        if out_payload.get("in_trap_range") is True:
            warnings.append({
                "code": "W001",
                "message": out_payload.get(
                    "trap_note",
                    "年终奖落在跳档陷阱区间，税后收入可能不增反降，建议调整金额。",
                ),
                "field": "bonusAmount",
                "severity": "warning",
            })
    elif endpoint == "payroll.monthly":
        cum_keys = ("cumulativeIncome", "cumulativeInsurance", "cumulativeSpecial")
        provided = [k for k in cum_keys if k in in_payload and in_payload[k] is not None]
        if not provided and in_payload.get("month", 1) > 1:
            warnings.append({
                "code": "W002",
                "message": "未提供累计值，个税按每月恒定近似估算，可能与累计预扣法存在偏差。",
                "field": "cumulativeIncome",
                "severity": "warning",
            })
    elif endpoint == "org.health":
        for risk in out_payload.get("risks", []):
            if risk.get("severity") == "WARNING":
                warnings.append({
                    "code": "W003",
                    "message": f"组织健康度风险：{risk.get('type', '')} — {risk.get('detail', '')}",
                    "field": None,
                    "severity": "warning",
                })
    return warnings


# ---------------------------------------------------------------------------
# 端点实现（每个把 payload 规整为脚本函数所需的入参）
# ---------------------------------------------------------------------------

def _ep_payroll_monthly(payload: Dict) -> Dict:
    # 入参映射与出参结构统一由 payroll_engine.payroll_monthly_from_payload 提供，
    # 与 CLI `--payroll` 共用同一份契约（两处共用映射，防字段口径漂移）。
    return payroll_monthly_from_payload(payload)


def _ep_payroll_bonus(payload: Dict) -> Dict:
    amt = payload.get("bonusAmount")
    if not isinstance(amt, (int, float)) or isinstance(amt, bool):
        raise _BadRequest("payroll.bonus 需要数字字段 bonusAmount", code="E020", field="bonusAmount")
    return bonus_result_to_dict(calculate_year_end_bonus(amt))


def _ep_candidate_score(payload: Dict) -> Dict:
    result = decide(payload)
    return {
        "dimensions": {k: round(v, 1) for k, v in result.dimensions.items()},
        "overall": result.overall,
        "recommendation": result.recommendation,
        "risk_level": result.risk_level,
        "note": result.note,
    }


def _ep_org_health(payload: Dict) -> Dict:
    result = diagnose(payload)
    return {
        "org_health": {
            "span_of_control": result.span_of_control,
            "hierarchy_depth": result.hierarchy_depth,
            "ic_manager_ratio": result.ic_manager_ratio,
            "team_size": result.team_size,
        },
        "risks": result.risks,
    }


ENDPOINTS: Dict[str, Callable[[Dict], Dict]] = {
    "payroll.monthly": _ep_payroll_monthly,
    "payroll.bonus": _ep_payroll_bonus,
    "candidate.score": _ep_candidate_score,
    "org.health": _ep_org_health,
}


def _humanize_exc(exc: Exception) -> str:
    """把包装异常的原始信息转成不含内部类名的用户可见文案。

    `decimal.InvalidOperation` / `OverflowError` 等 `str()` 会退化为类 repr
    （如 ``[<class 'decimal.InvalidOperation'>]``），不得泄漏给调用方。
    """
    if isinstance(exc, InvalidOperation):
        return "计算失败：金额超出可计算范围（数值溢出或精度异常）。"
    if isinstance(exc, OverflowError):
        return "计算失败：数值溢出（结果超出可表示范围）。"
    msg = str(exc).strip()
    if not msg or "<class" in msg or msg.startswith("["):
        return "计算失败：输入数值无法完成计算。"
    return f"计算失败：{msg}"


def dispatch(endpoint: str, payload: Dict) -> Dict:
    """进程内调用入口。失败抛 EngineError（含 .status）。"""
    handler = ENDPOINTS.get(endpoint)
    if handler is None:
        raise _NotFound(f"未知端点：{endpoint}（可用：{', '.join(ENDPOINTS)}）")
    if not isinstance(payload, dict):
        raise _BadRequest("payload 必须是 JSON 对象", code="E020", field=None)
    try:
        return _to_jsonable(handler(payload))
    except (PayrollInputError, CandidateInputError, OrgSchemaError) as e:
        raise _BadRequest(str(e), code=getattr(e, "code", None), field=getattr(e, "field", None)) from e
    except (TypeError, ValueError, ArithmeticError) as e:
        raise _BadRequest(_humanize_exc(e), code=getattr(e, "code", None), field=getattr(e, "field", None)) from e


def dispatch_envelope(endpoint: str, payload: Dict) -> Dict:
    """统一 schema 入口。

    返回 `{status, version, baseline_date, payload, errors, warnings}`（见
    knowledge-map.md）。永不抛异常：错误一律进
    `errors[]` 数组，`status=error`；成功进 `payload`，`status=ok`。
    """
    env: Dict[str, Any] = {
        "status": "ok",
        "version": SCHEMA_VERSION,
        "baseline_date": BASELINE_DATE.get(endpoint, "2026-01-01"),
        "payload": {},
        "errors": [],
        "warnings": [],
    }
    try:
        env["payload"] = dispatch(endpoint, payload)
    except EngineError as e:
        code = _classify_error(endpoint, e)
        env["status"] = "error"
        env["errors"].append({
            "code": code,
            "message": str(e),
            "field": _error_field(e),
            "severity": "fatal",
        })
    else:
        env["warnings"] = _derive_warnings(endpoint, payload, env["payload"])
    return env


def dispatch_envelope_json(endpoint: str, body: str) -> str:
    """统一 schema 的 JSON 字符串入口。"""
    try:
        payload = json.loads(body) if body else {}
    except json.JSONDecodeError as e:
        return json.dumps({
            "status": "error",
            "version": SCHEMA_VERSION,
            "baseline_date": BASELINE_DATE.get(endpoint, "2026-01-01"),
            "payload": {},
            "errors": [{"code": "E020", "message": f"非法 JSON：{e}", "field": None, "severity": "fatal"}],
            "warnings": [],
        }, ensure_ascii=False, indent=2)
    return json.dumps(dispatch_envelope(endpoint, payload), ensure_ascii=False, indent=2)


def emit_envelope(endpoint: str, body: str) -> int:
    """统一 schema 的 CLI 出口：打印到 stdout 并返回进程退出码。

    四个 CLI 入口（`payroll_engine.py` / `candidate_scorer.py` / `org_health.py`
    / `engine_service.py`）在 `--envelope` 下共用本函数，避免各自复制判定逻辑。

    契约（`INDEX.md` §5 第 3 条）：
    - `status == "ok"`    → 返回 0；
    - `status == "error"` → 返回 2；
    - 无论成败，完整统一 schema JSON **一律打印到 stdout**（便于 `| jq` / `> file`
      消费），stderr 不另写内容。

    本函数永不抛异常（底层 `dispatch_envelope_json` 已吞掉 JSON 解析错误）；
    仅当渲染结果不可解析（防御性分支）时返回 2。

    Args:
        endpoint: 端点名，如 `"payroll.bonus"`。
        body: 请求体 JSON 字符串。

    Returns:
        0（`status == "ok"`）或 2（`status == "error"` / 不可解析）。
    """
    rendered = dispatch_envelope_json(endpoint, body)
    print(rendered)
    try:
        status = json.loads(rendered).get("status")
    except json.JSONDecodeError:
        return 2
    return 0 if status == "ok" else 2


def dispatch_json(endpoint: str, body: str) -> str:
    """JSON 字符串入口，返回 JSON 字符串。"""
    try:
        payload = json.loads(body) if body else {}
    except json.JSONDecodeError as e:
        raise _BadRequest(f"非法 JSON：{e}") from e
    return json.dumps(dispatch(endpoint, payload), ensure_ascii=False, indent=2)


if __name__ == "__main__":
    # 命令行冒烟：
    # python3 engine_service.py payroll.bonus '{"bonusAmount":36000}'
    # python3 engine_service.py --envelope payroll.monthly '{"baseSalary":25000,"city":"深圳"}'
    import sys
    args = sys.argv[1:]
    use_envelope = False
    if args and args[0] == "--envelope":
        use_envelope = True
        args = args[1:]
    if len(args) >= 1:
        ep = args[0]
        body = args[1] if len(args) > 1 else "{}"
        if use_envelope:
            # 统一 schema 出口：stdout 打印，status==error 时退出 2（见 emit_envelope）
            raise SystemExit(emit_envelope(ep, body))
        try:
            print(dispatch_json(ep, body))
        except EngineError as e:
            sys.stderr.write(f"[engine] {e}\n")
            raise SystemExit(2)
    else:
        print("可用端点：", ", ".join(ENDPOINTS))
