#!/usr/bin/env python3
"""Render a professional K-line review report from summary JSON."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any


PERIOD_LABELS = {
    "day": "日线",
    "d": "日线",
    "101": "日线",
    "week": "周线",
    "w": "周线",
    "102": "周线",
    "month": "月线",
    "m": "月线",
    "103": "月线",
    "1m": "1分钟",
    "5m": "5分钟",
    "15m": "15分钟",
    "30m": "30分钟",
    "60m": "60分钟",
}
ADJUST_LABELS = {
    "none": "不复权",
    "qfq": "前复权",
    "hfq": "后复权",
    "unknown": "未知",
    None: "未知",
}
FORBIDDEN_TERMS = [
    "建议买入",
    "建议卖出",
    "加仓",
    "减仓",
    "仓位",
    "目标价",
    "稳赚",
    "保本",
    "一定涨",
    "必涨",
]


def fmt(value: Any, suffix: str = "") -> str:
    if value is None:
        return "不可计算"
    if isinstance(value, float):
        return f"{value:.2f}{suffix}"
    return f"{value}{suffix}"


def fmt_big(value: Any) -> str:
    if value is None:
        return "不可计算"
    if isinstance(value, (int, float)):
        return f"{value:,.0f}"
    return str(value)


def load_summary(path: str | None) -> dict[str, Any]:
    if path:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    return json.load(sys.stdin)


def trend_state(summary: dict[str, Any]) -> str:
    last_bar = summary.get("last_bar") or {}
    close = last_bar.get("close")
    position = summary.get("price_position_pct") or {}
    ma = summary.get("moving_averages") or {}
    if close is None:
        return "数据不足，无法形成盘面状态判断。"

    above = [key for key in ("ma5", "ma10", "ma20", "ma60") if position.get(key) is not None and position[key] > 0]
    if all(position.get(key, -1) > 0 for key in ("ma5", "ma10", "ma20") if position.get(key) is not None):
        bias = "偏强"
    elif all(position.get(key, 1) < 0 for key in ("ma5", "ma10", "ma20") if position.get(key) is not None):
        bias = "偏弱"
    else:
        bias = "震荡"

    ma_order = ""
    if all(ma.get(key) is not None for key in ("ma5", "ma10", "ma20")):
        if ma["ma5"] > ma["ma10"] > ma["ma20"]:
            ma_order = "，短中期均线呈多头排列"
        elif ma["ma5"] < ma["ma10"] < ma["ma20"]:
            ma_order = "，短中期均线呈空头排列"
    if len(above) >= 3:
        position_text = f"位于 {'、'.join(above).upper()} 上方"
    elif above:
        position_text = f"围绕 {'、'.join(above).upper()} 附近震荡"
    else:
        position_text = "位于主要均线下方"
    return f"当前结构{bias}，最新收盘价{position_text}，该判断需要结合量能确认{ma_order}。"


def volume_comment(summary: dict[str, Any]) -> str:
    profile = summary.get("volume_profile") or {}
    ratio = profile.get("latest_vs_avg20")
    latest = profile.get("latest_volume")
    avg20 = profile.get("avg_volume_20")
    if ratio is None:
        return f"最新成交量 {fmt_big(latest)}，20 根均量 {fmt_big(avg20)}，样本不足或字段缺失导致相对量能不可计算。"
    if ratio >= 1.5:
        tone = "明显放量"
    elif ratio >= 1.15:
        tone = "温和放量"
    elif ratio <= 0.75:
        tone = "缩量"
    else:
        tone = "量能接近均量"
    return f"最新成交量 {fmt_big(latest)}，20 根均量 {fmt_big(avg20)}，相对量能 {ratio:.2f} 倍，属于{tone}。"


def level_text(level: dict[str, Any] | None) -> str:
    if not level:
        return "不可计算"
    return f"{fmt(level.get('price'))}（{level.get('date', '日期未知')}）"


def failure_report(summary: dict[str, Any]) -> str:
    quality = summary.get("quality") or {}
    warnings = quality.get("warnings") or ["数据获取失败，未返回可用 K 线。"]
    source = summary.get("source", "unknown")
    symbol = summary.get("symbol", "未提供")
    period = PERIOD_LABELS.get(str(summary.get("period")), str(summary.get("period") or "未知"))
    return "\n".join([
        "## 数据说明",
        f"- 标的：{symbol}",
        "- 市场/类型：A股/ETF",
        f"- 周期：{period}",
        "- 区间：不可用",
        f"- 复权：{ADJUST_LABELS.get(summary.get('adjust'), summary.get('adjust') or '未知')}",
        f"- 来源：{source}",
        "- 数据质量：不可用",
        "",
        "## 盘面状态",
        "当前未取得可用 K 线数据，不能生成技术复盘结论。",
        "",
        "## 趋势位置",
        "- 均线：不可计算",
        "- 价格位置：不可计算",
        "- 多周期关系：不可计算",
        "",
        "## 量价结构",
        "- 成交量：不可计算",
        "- 波动：不可计算",
        "- K线特征：不可计算",
        "",
        "## 关键价位",
        "- 近端压力：不可计算",
        "- 近端支撑：不可计算",
        "- 失效条件：数据源恢复或用户提供 CSV 后重新评估",
        "",
        "## 风险与观察清单",
        *[f"- {item}" for item in warnings],
        "- 可稍后重试东方财富数据源，或粘贴 CSV K 线数据走离线复盘。",
        "- 在数据恢复前，不应基于空数据推断趋势、形态或价位。",
        "",
        "## 免责声明",
        "本解读仅用于技术研究和复盘，不构成投资建议、收益承诺或买卖指令。",
        "",
    ])


def render(summary: dict[str, Any], symbol: str | None = None, name: str | None = None, market_type: str = "A股/ETF") -> str:
    quality = summary.get("quality") or {}
    if not quality.get("ok"):
        return failure_report(summary)

    last_bar = summary.get("last_bar") or {}
    ma = summary.get("moving_averages") or {}
    position = summary.get("price_position_pct") or {}
    key_levels = summary.get("key_levels") or {}
    report_symbol = symbol or summary.get("symbol") or "用户CSV"
    report_name = name or summary.get("name") or ""
    period = PERIOD_LABELS.get(str(summary.get("period")), str(summary.get("period") or "CSV周期"))
    adjust = ADJUST_LABELS.get(summary.get("adjust"), summary.get("adjust") or "未知")
    range_info = summary.get("range") or {}
    warnings = quality.get("warnings") or []
    notes = summary.get("candlestick_notes") or []

    lines = [
        "## 数据说明",
        f"- 标的：{report_symbol}{' ' + report_name if report_name else ''}",
        f"- 市场/类型：{market_type}",
        f"- 周期：{period}",
        f"- 区间：{range_info.get('start')} 至 {range_info.get('end')}，共 {range_info.get('bars')} 根",
        f"- 复权：{adjust}",
        f"- 来源：{summary.get('source', 'unknown')}",
        "- 数据质量：" + ("；".join(warnings) if warnings else "可用于基础技术复盘"),
        "",
        "## 盘面状态",
        trend_state(summary),
        "",
        "## 趋势位置",
        f"- 均线：MA5 {fmt(ma.get('ma5'))}，MA10 {fmt(ma.get('ma10'))}，MA20 {fmt(ma.get('ma20'))}，MA60 {fmt(ma.get('ma60'))}。",
        f"- 价格位置：最新收盘 {fmt(last_bar.get('close'))}；相对 MA5 {fmt(position.get('ma5'), '%')}，MA10 {fmt(position.get('ma10'), '%')}，MA20 {fmt(position.get('ma20'), '%')}，MA60 {fmt(position.get('ma60'), '%')}。",
        "- 多周期关系：当前摘要为单周期数据；如需共振判断，需要补充周线/月线或分钟线摘要。",
        "",
        "## 量价结构",
        f"- 成交量：{volume_comment(summary)}",
        f"- 波动：最新振幅 {fmt(last_bar.get('amplitude_pct'), '%')}，涨跌幅 {fmt(last_bar.get('change_pct'), '%')}。",
        "- K线特征：" + ("；".join(notes) if notes else "未检测到极端长影线或小实体特征，仍需结合连续 K 线确认。"),
        "",
        "## 关键价位",
        f"- 近端压力：20 根高点 {level_text(key_levels.get('high_20'))}；60 根高点 {level_text(key_levels.get('high_60'))}。",
        f"- 近端支撑：20 根低点 {level_text(key_levels.get('low_20'))}；60 根低点 {level_text(key_levels.get('low_60'))}。",
        "- 失效条件：若后续收盘价重新跌回关键均线下方且量能无法修复，当前偏强结构需要降级；若放量突破后无法守住前高，也要防范假突破。",
        "",
        "## 风险与观察清单",
        "- 技术结构只描述价格与成交量，不代表基本面或资金面结论。",
        "- 若样本不足或数据源延迟，均线、关键价位和量能倍数需要重新计算。",
        "- 观察后续能否在关键价位附近保持量价配合，而不是只看单根 K 线。",
        "- 观察回踩时是否缩量、反弹时是否放量。",
        "- 观察跌破关键均线后的修复速度，作为结构强弱的验证条件。",
        "",
        "## 免责声明",
        "本解读仅用于技术研究和复盘，不构成投资建议、收益承诺或买卖指令。",
        "",
    ]
    text = "\n".join(lines)
    lowered = text.lower()
    found = [term for term in FORBIDDEN_TERMS if term.lower() in lowered]
    if found:
        raise RuntimeError("rendered report contains forbidden terms: " + ", ".join(found))
    return text


def main() -> int:
    parser = argparse.ArgumentParser(description="Render K-line report from summary JSON")
    parser.add_argument("--file", help="Summary JSON file. Reads stdin when omitted.")
    parser.add_argument("--symbol", help="Override display symbol")
    parser.add_argument("--name", help="Override display name")
    parser.add_argument("--market-type", default="A股/ETF")
    args = parser.parse_args()

    summary = load_summary(args.file)
    print(render(summary, symbol=args.symbol, name=args.name, market_type=args.market_type), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
