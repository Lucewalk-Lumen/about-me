#!/usr/bin/env python3
"""Parse K-line CSV data and emit a compact technical summary as JSON."""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
import statistics
import sys
from typing import Any


FIELD_ALIASES = {
    "date": {"date", "time", "datetime", "日期", "时间"},
    "open": {"open", "开盘", "开盘价"},
    "close": {"close", "收盘", "收盘价"},
    "high": {"high", "最高", "最高价"},
    "low": {"low", "最低", "最低价"},
    "volume": {"volume", "vol", "成交量"},
    "amount": {"amount", "成交额", "成交金额"},
    "amplitude_pct": {"amplitude", "amplitude_pct", "振幅", "振幅%"},
    "change_pct": {"change_pct", "pct_chg", "涨跌幅", "涨跌幅%"},
    "change_amount": {"change_amount", "涨跌额"},
    "turnover_pct": {"turnover", "turnover_pct", "换手率", "换手率%"},
}


def normalize_header(name: str) -> str:
    return name.strip().lower().replace(" ", "").replace("%", "_pct")


def canonical_field(header: str) -> str | None:
    normalized = normalize_header(header)
    for field, aliases in FIELD_ALIASES.items():
        if normalized in {normalize_header(alias) for alias in aliases}:
            return field
    return None


def to_number(value: str | None) -> float | None:
    if value is None:
        return None
    cleaned = value.strip().replace(",", "").replace("%", "")
    if cleaned in {"", "-", "--", "nan", "None"}:
        return None
    try:
        num = float(cleaned)
    except ValueError:
        return None
    if math.isnan(num) or math.isinf(num):
        return None
    return num


def parse_csv(text: str) -> tuple[list[dict[str, Any]], list[str]]:
    reader = csv.DictReader(io.StringIO(text.strip()))
    if not reader.fieldnames:
        return [], ["CSV 缺少表头"]

    mapping: dict[str, str] = {}
    ignored: list[str] = []
    for header in reader.fieldnames:
        field = canonical_field(header)
        if field:
            mapping[header] = field
        else:
            ignored.append(header)

    rows: list[dict[str, Any]] = []
    warnings: list[str] = []
    required = {"date", "open", "close", "high", "low"}
    present = set(mapping.values())
    missing_required = sorted(required - present)
    if missing_required:
        warnings.append("缺少关键字段: " + ", ".join(missing_required))

    for raw in reader:
        row: dict[str, Any] = {}
        for header, field in mapping.items():
            if field == "date":
                row[field] = (raw.get(header) or "").strip()
            else:
                row[field] = to_number(raw.get(header))
        if row.get("date"):
            rows.append(row)

    rows.sort(key=lambda item: item["date"])
    previous_close: float | None = None
    for row in rows:
        open_ = row.get("open")
        high = row.get("high")
        low = row.get("low")
        close = row.get("close")
        base = previous_close if previous_close else open_
        if row.get("amplitude_pct") is None and None not in (high, low, base) and base:
            row["amplitude_pct"] = round((high - low) / base * 100, 2)
        if row.get("change_amount") is None and previous_close is not None and close is not None:
            row["change_amount"] = round(close - previous_close, 4)
        if row.get("change_pct") is None and previous_close and close is not None:
            row["change_pct"] = round((close / previous_close - 1) * 100, 2)
        if close is not None:
            previous_close = close
    if ignored:
        warnings.append("忽略未识别字段: " + ", ".join(ignored))
    return rows, warnings


def last(values: list[float | None], window: int) -> float | None:
    if len(values) < window:
        return None
    subset = [value for value in values[-window:] if value is not None]
    if len(subset) < window:
        return None
    return round(statistics.fmean(subset), 4)


def max_level(rows: list[dict[str, Any]], window: int) -> dict[str, Any] | None:
    subset = [row for row in rows[-window:] if row.get("high") is not None]
    if not subset:
        return None
    row = max(subset, key=lambda item: item["high"])
    return {"date": row["date"], "price": row["high"]}


def min_level(rows: list[dict[str, Any]], window: int) -> dict[str, Any] | None:
    subset = [row for row in rows[-window:] if row.get("low") is not None]
    if not subset:
        return None
    row = min(subset, key=lambda item: item["low"])
    return {"date": row["date"], "price": row["low"]}


def summarize(rows: list[dict[str, Any]], warnings: list[str], period: str, adjust: str) -> dict[str, Any]:
    closes = [row.get("close") for row in rows]
    volumes = [row.get("volume") for row in rows]
    last_bar = rows[-1] if rows else {}
    close = last_bar.get("close")

    moving_averages = {
        "ma5": last(closes, 5),
        "ma10": last(closes, 10),
        "ma20": last(closes, 20),
        "ma60": last(closes, 60),
    }
    price_position = {}
    if close is not None:
        for key, value in moving_averages.items():
            price_position[key] = None if value is None else round((close / value - 1) * 100, 2)

    latest_volume = last_bar.get("volume")
    avg_volume_5 = last(volumes, 5)
    avg_volume_20 = last(volumes, 20)
    volume_profile = {
        "latest_volume": latest_volume,
        "avg_volume_5": avg_volume_5,
        "avg_volume_20": avg_volume_20,
        "latest_vs_avg20": None,
    }
    if latest_volume is not None and avg_volume_20:
        volume_profile["latest_vs_avg20"] = round(latest_volume / avg_volume_20, 2)

    if len(rows) < 20:
        warnings.append("样本少于 20 根，趋势和均线判断置信度有限")
    if len(rows) < 60:
        warnings.append("样本少于 60 根，MA60 和中期结构可能不可计算")

    notes: list[str] = []
    if last_bar:
        open_ = last_bar.get("open")
        high = last_bar.get("high")
        low = last_bar.get("low")
        if None not in (open_, close, high, low):
            body = abs(close - open_)
            full = high - low
            if full > 0:
                upper = high - max(open_, close)
                lower = min(open_, close) - low
                if upper / full >= 0.45:
                    notes.append("最新K线存在较长上影线")
                if lower / full >= 0.45:
                    notes.append("最新K线存在较长下影线")
                if body / full <= 0.25:
                    notes.append("最新K线实体较小，分歧或等待确认特征较强")

    return {
        "source": "csv",
        "period": period,
        "adjust": adjust,
        "range": {
            "start": rows[0]["date"] if rows else None,
            "end": rows[-1]["date"] if rows else None,
            "bars": len(rows),
        },
        "quality": {
            "ok": bool(rows) and {"date", "open", "close", "high", "low"}.issubset(rows[-1].keys()),
            "warnings": warnings,
        },
        "last_bar": last_bar,
        "moving_averages": moving_averages,
        "price_position_pct": price_position,
        "volume_profile": volume_profile,
        "key_levels": {
            "high_20": max_level(rows, 20),
            "low_20": min_level(rows, 20),
            "high_60": max_level(rows, 60),
            "low_60": min_level(rows, 60),
        },
        "candlestick_notes": notes,
        "raw_sample_tail": rows[-5:],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze K-line CSV data")
    parser.add_argument("--file", help="CSV file path. Reads stdin when omitted.")
    parser.add_argument("--period", default="day", help="Display period, such as day/week/month/5m.")
    parser.add_argument("--adjust", default="unknown", help="Adjustment label: none/qfq/hfq/unknown.")
    args = parser.parse_args()

    if args.file:
        with open(args.file, encoding="utf-8-sig") as handle:
            text = handle.read()
    else:
        text = sys.stdin.read()

    rows, warnings = parse_csv(text)
    print(json.dumps(summarize(rows, warnings, args.period, args.adjust), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
