#!/usr/bin/env python3
"""Fetch A-share/ETF K-line data from Eastmoney and emit CSV or summary JSON."""

from __future__ import annotations

import argparse
import csv
import io
import json
import statistics
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ENDPOINTS = [
    "https://push2his.eastmoney.com/api/qt/stock/kline/get",
    "http://push2his.eastmoney.com/api/qt/stock/kline/get",
]
EASTMONEY_UT = "fa5fd1943c7b386f172d6893dbfba10b"
FIELDS1 = "f1,f2,f3,f4,f5,f6"
FIELDS2 = "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61"
CSV_FIELDS = [
    "date",
    "open",
    "close",
    "high",
    "low",
    "volume",
    "amount",
    "amplitude_pct",
    "change_pct",
    "change_amount",
    "turnover_pct",
]
PERIODS = {
    "1m": 1,
    "1": 1,
    "5m": 5,
    "5": 5,
    "15m": 15,
    "15": 15,
    "30m": 30,
    "30": 30,
    "60m": 60,
    "60": 60,
    "day": 101,
    "d": 101,
    "101": 101,
    "week": 102,
    "w": 102,
    "102": 102,
    "month": 103,
    "m": 103,
    "103": 103,
}
ADJUST = {
    "none": 0,
    "0": 0,
    "qfq": 1,
    "front": 1,
    "1": 1,
    "hfq": 2,
    "back": 2,
    "2": 2,
}


def guess_secid(symbol: str, secid: str | None = None) -> str:
    if secid:
        if "." not in secid:
            raise ValueError("--secid must look like 1.510300 or 0.300750")
        return secid
    code = "".join(ch for ch in symbol if ch.isalnum()).upper()
    if not (len(code) == 6 and code.isdigit()):
        raise ValueError("仅支持 6 位 A 股/ETF 代码；名称请先转换为代码")
    if code.startswith(("5", "6", "9")):
        market = "1"
    elif code.startswith(("0", "1", "2", "3")):
        market = "0"
    else:
        raise ValueError("暂不自动识别北交所或未知市场代码，请提供沪深 A 股/ETF 代码")
    return f"{market}.{code}"


def to_float(value: str) -> float | None:
    if value in {"", "-", "--"}:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def fetch_once(endpoint: str, secid: str, symbol: str, period: str, adjust: str, beg: str, end: str, limit: int) -> dict[str, Any]:
    params = {
        "fields1": FIELDS1,
        "fields2": FIELDS2,
        "beg": beg,
        "end": end,
        "rtntype": "6",
        "secid": secid,
        "klt": str(PERIODS[period]),
        "fqt": str(ADJUST[adjust]),
        "lmt": str(limit),
        "ut": EASTMONEY_UT,
    }
    url = endpoint + "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
            "Accept": "application/json,text/plain,*/*",
            "Referer": "https://quote.eastmoney.com/",
            "Connection": "close",
        },
    )
    with urllib.request.urlopen(request, timeout=12) as response:
        payload = json.loads(response.read().decode("utf-8"))
    data = payload.get("data")
    if not data or not data.get("klines"):
        raise RuntimeError(f"东方财富未返回 K 线数据: {payload.get('message') or payload.get('rc')}")
    return {
        "symbol": str(data.get("code") or symbol),
        "name": str(data.get("name") or ""),
        "secid": secid,
        "period": period,
        "adjust": adjust,
        "rows": [parse_kline(line) for line in data["klines"][-limit:]],
    }


def cache_file_path(cache_dir: str | None, secid: str, period: str, adjust: str, beg: str, end: str, limit: int) -> Path | None:
    if not cache_dir:
        return None
    safe = f"{secid}_{period}_{adjust}_{beg}_{end}_{limit}".replace(".", "_")
    return Path(cache_dir).expanduser() / f"{safe}.json"


def cache_age_hours(cached_at: str | None) -> float | None:
    if not cached_at:
        return None
    try:
        timestamp = datetime.fromisoformat(cached_at.replace("Z", "+00:00"))
    except ValueError:
        return None
    return (datetime.now(timezone.utc) - timestamp.astimezone(timezone.utc)).total_seconds() / 3600


def load_cache(path: Path | None, max_age_hours: float, allow_stale: bool) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    with path.open(encoding="utf-8") as handle:
        result = json.load(handle)
    age = cache_age_hours(result.get("cached_at"))
    if age is not None and age > max_age_hours and not allow_stale:
        return None
    result["source"] = "eastmoney-cache"
    result.setdefault("warnings", [])
    if age is None:
        result["warnings"].append("使用本地缓存，缓存时间不可识别，请谨慎参考。")
    elif age > max_age_hours:
        result["warnings"].append(f"使用本地过期缓存，缓存约 {age:.1f} 小时前生成。")
    else:
        result["warnings"].append(f"使用本地缓存，缓存约 {age:.1f} 小时前生成。")
    result["diagnostics"] = {
        **result.get("diagnostics", {}),
        "cache_file": str(path),
        "cache_age_hours": None if age is None else round(age, 2),
    }
    return result


def save_cache(path: Path | None, result: dict[str, Any]) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(result)
    payload["cached_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def fetch(symbol: str, period: str, adjust: str, beg: str, end: str, limit: int, secid_override: str | None = None) -> dict[str, Any]:
    secid = guess_secid(symbol, secid_override)
    errors: list[str] = []
    for endpoint in ENDPOINTS:
        try:
            result = fetch_once(endpoint, secid, symbol, period, adjust, beg, end, limit)
            result["diagnostics"] = {"endpoint": endpoint, "attempted": len(errors) + 1}
            return result
        except Exception as exc:
            errors.append(f"{endpoint}: {type(exc).__name__}: {exc}")
            time.sleep(0.5)
    raise RuntimeError("；".join(errors))


def parse_kline(line: str) -> dict[str, Any]:
    values = line.split(",")
    row: dict[str, Any] = {}
    for field, value in zip(CSV_FIELDS, values):
        row[field] = value if field == "date" else to_float(value)
    return row


def mean(values: list[float | None], window: int) -> float | None:
    if len(values) < window:
        return None
    subset = [value for value in values[-window:] if value is not None]
    if len(subset) < window:
        return None
    return round(statistics.fmean(subset), 4)


def high_level(rows: list[dict[str, Any]], window: int) -> dict[str, Any] | None:
    subset = [row for row in rows[-window:] if row.get("high") is not None]
    if not subset:
        return None
    row = max(subset, key=lambda item: item["high"])
    return {"date": row["date"], "price": row["high"]}


def low_level(rows: list[dict[str, Any]], window: int) -> dict[str, Any] | None:
    subset = [row for row in rows[-window:] if row.get("low") is not None]
    if not subset:
        return None
    row = min(subset, key=lambda item: item["low"])
    return {"date": row["date"], "price": row["low"]}


def summarize(result: dict[str, Any]) -> dict[str, Any]:
    rows = result["rows"]
    closes = [row.get("close") for row in rows]
    volumes = [row.get("volume") for row in rows]
    last_bar = rows[-1] if rows else {}
    close = last_bar.get("close")
    ma = {
        "ma5": mean(closes, 5),
        "ma10": mean(closes, 10),
        "ma20": mean(closes, 20),
        "ma60": mean(closes, 60),
    }
    price_position = {
        key: None if close is None or value is None else round((close / value - 1) * 100, 2)
        for key, value in ma.items()
    }
    latest_volume = last_bar.get("volume")
    avg_volume_5 = mean(volumes, 5)
    avg_volume_20 = mean(volumes, 20)
    warnings = list(result.get("warnings", []))
    if len(rows) < 20:
        warnings.append("样本少于 20 根，趋势和均线判断置信度有限")
    if len(rows) < 60:
        warnings.append("样本少于 60 根，MA60 和中期结构可能不可计算")
    return {
        "source": result.get("source", "eastmoney"),
        "symbol": result["symbol"],
        "name": result["name"],
        "secid": result["secid"],
        "period": result["period"],
        "adjust": result["adjust"],
        "range": {
            "start": rows[0]["date"] if rows else None,
            "end": rows[-1]["date"] if rows else None,
            "bars": len(rows),
        },
        "quality": {
            "ok": bool(rows),
            "warnings": warnings,
        },
        "last_bar": last_bar,
        "moving_averages": ma,
        "price_position_pct": price_position,
        "volume_profile": {
            "latest_volume": latest_volume,
            "avg_volume_5": avg_volume_5,
            "avg_volume_20": avg_volume_20,
            "latest_vs_avg20": None if latest_volume is None or not avg_volume_20 else round(latest_volume / avg_volume_20, 2),
        },
        "key_levels": {
            "high_20": high_level(rows, 20),
            "low_20": low_level(rows, 20),
            "high_60": high_level(rows, 60),
            "low_60": low_level(rows, 60),
        },
        "raw_sample_tail": rows[-5:],
        "diagnostics": result.get("diagnostics", {}),
    }


def as_csv(rows: list[dict[str, Any]]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=CSV_FIELDS)
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch Eastmoney K-line data")
    parser.add_argument("symbol", help="6-digit A-share or ETF code")
    parser.add_argument("--period", default="day", choices=sorted(PERIODS))
    parser.add_argument("--adjust", default="qfq", choices=sorted(ADJUST))
    parser.add_argument("--beg", default="19000101", help="YYYYMMDD")
    parser.add_argument("--end", default="20500101", help="YYYYMMDD")
    parser.add_argument("--limit", type=int, default=120)
    parser.add_argument("--secid", help="Override Eastmoney secid, for example 1.510300 or 0.300750.")
    parser.add_argument("--format", choices=("summary", "csv"), default="summary")
    parser.add_argument("--strict", action="store_true", help="Return non-zero when Eastmoney fetch fails.")
    parser.add_argument("--cache-dir", help="Directory for local raw K-line cache.")
    parser.add_argument("--prefer-cache", action="store_true", help="Use fresh cache before requesting Eastmoney.")
    parser.add_argument("--allow-stale-cache", action="store_true", help="Use stale cache when live fetch fails.")
    parser.add_argument("--cache-max-age-hours", type=float, default=24.0)
    args = parser.parse_args()

    if args.limit <= 0 or args.limit > 1000:
        raise SystemExit("--limit must be in 1..1000")

    try:
        secid_for_cache = guess_secid(args.symbol, args.secid)
    except Exception as exc:
        secid_for_cache = args.secid or args.symbol
        guess_error = exc
    else:
        guess_error = None

    cache_path = cache_file_path(
        args.cache_dir,
        secid_for_cache,
        args.period,
        args.adjust,
        args.beg,
        args.end,
        args.limit,
    )

    if args.prefer_cache:
        cached = load_cache(cache_path, args.cache_max_age_hours, args.allow_stale_cache)
        if cached:
            if args.format == "csv":
                print(as_csv(cached["rows"]), end="")
            else:
                print(json.dumps(summarize(cached), ensure_ascii=False, indent=2))
            return 0

    try:
        if guess_error:
            raise guess_error
        result = fetch(args.symbol, args.period, args.adjust, args.beg, args.end, args.limit, args.secid)
        save_cache(cache_path, result)
    except Exception as exc:
        cached = load_cache(cache_path, args.cache_max_age_hours, True if args.allow_stale_cache else False)
        if cached:
            cached.setdefault("warnings", [])
            cached["warnings"].append(f"实时东方财富获取失败，已降级使用缓存: {type(exc).__name__}: {exc}")
            if args.format == "csv":
                print(as_csv(cached["rows"]), end="")
            else:
                print(json.dumps(summarize(cached), ensure_ascii=False, indent=2))
            return 0
        print(json.dumps({
            "source": "eastmoney",
            "symbol": args.symbol,
            "period": args.period,
            "adjust": args.adjust,
            "secid": args.secid or secid_for_cache,
            "quality": {
                "ok": False,
                "warnings": [
                    f"东方财富数据获取失败: {type(exc).__name__}: {exc}",
                    "请稍后重试，或让用户粘贴 CSV K 线数据走离线 fallback。",
                    "若此前已有成功数据，可配置 --cache-dir 并启用 --prefer-cache 或 --allow-stale-cache 读取本地缓存。",
                ],
            },
            "diagnostics": {
                "endpoints": ENDPOINTS,
                "soft_failure": not args.strict,
                "cache_file": None if cache_path is None else str(cache_path),
            },
            "raw_sample_tail": [],
        }, ensure_ascii=False, indent=2))
        return 2 if args.strict else 0
    time.sleep(0.3)
    if args.format == "csv":
        print(as_csv(result["rows"]), end="")
    else:
        print(json.dumps(summarize(result), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
