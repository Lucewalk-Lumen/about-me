#!/usr/bin/env python3
"""Fetch US-stock real-time quotes from Eastmoney public API with a status=ok guard.

Mirrors the A-share market_data_guard discipline: only status=ok results may be
quoted as current prices by the agent. Price scaling follows the f59 decimal
count (US: f43=345240, f59=3 -> 345.24; A-share convention differs, hence the
dynamic scaling instead of a hardcoded divisor).
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from typing import Any


ENDPOINTS = [
    "https://push2.eastmoney.com/api/qt/stock/get",
    "http://push2.eastmoney.com/api/qt/stock/get",
]
EASTMONEY_UT = "fa5fd1943c7b386f172d6893dbfba10b"
QUOTE_FIELDS = "f43,f44,f45,f46,f47,f48,f57,f58,f59,f60,f86,f169,f170"
US_MARKETS = {"nasdaq": "105", "nyse": "106", "amex": "107"}
US_MARKET_NAMES = {"105": "NASDAQ", "106": "NYSE", "107": "AMEX"}


def guess_us_secid(symbol: str, market: str = "nasdaq", secid: str | None = None) -> str:
    if secid:
        if "." not in secid:
            raise ValueError("--secid must look like 105.AAPL / 106.BABA / 107.APT")
        prefix = secid.split(".", 1)[0]
        if prefix not in US_MARKET_NAMES:
            raise ValueError(f"美股 secid 前缀须为 105/106/107，收到: {prefix}")
        return secid
    code = "".join(ch for ch in symbol if ch.isalnum() or ch == ".").upper()
    core = code.replace(".", "")
    if not (core.isalpha() and 1 <= len(core) <= 6):
        raise ValueError("仅支持美股字母代码（如 AAPL、TSLA、BRK.B）")
    return f"{US_MARKETS[market]}.{code}"


def us_eastern_time(ts: int) -> tuple[datetime, str]:
    """Convert a unix timestamp to US/Eastern wall time.

    DST rule (US): second Sunday of March 02:00 local -> first Sunday of
    November 02:00 local. Implemented with stdlib only.
    """
    utc = datetime.fromtimestamp(ts, tz=timezone.utc)

    def nth_weekday(year: int, month: int, weekday: int, n: int) -> datetime:
        first = datetime(year, month, 1, tzinfo=timezone.utc)
        offset = (weekday - first.weekday()) % 7
        return first + timedelta(days=offset + 7 * (n - 1))

    year = utc.year
    dst_start = nth_weekday(year, 3, 6, 2) + timedelta(hours=7)   # 02:00 EST = 07:00 UTC
    dst_end = nth_weekday(year, 11, 6, 1) + timedelta(hours=6)    # 02:00 EDT = 06:00 UTC
    is_dst = dst_start <= utc < dst_end
    tz = timezone(timedelta(hours=-4 if is_dst else -5))
    local = utc.astimezone(tz)
    return local, ("EDT" if is_dst else "EST")


def market_status(et: datetime) -> str:
    """Rough US equities session status from Eastern wall-clock time."""
    if et.weekday() >= 5:
        return "closed_weekend"
    minutes = et.hour * 60 + et.minute
    if 9 * 60 + 30 <= minutes < 16 * 60:
        return "trading"
    if 4 * 60 <= minutes < 9 * 60 + 30:
        return "pre_market"
    if 16 * 60 <= minutes < 20 * 60:
        return "after_hours"
    return "closed"


def scale_price(value: Any, decimals: int) -> float | None:
    if value in (None, "", "-", "--"):
        return None
    try:
        return round(int(value) / (10 ** max(decimals, 0)), max(decimals, 2))
    except (TypeError, ValueError):
        return None


def fetch_quote(secid: str, symbol: str) -> dict[str, Any]:
    errors: list[str] = []
    for endpoint in ENDPOINTS:
        try:
            params = {"secid": secid, "ut": EASTMONEY_UT, "fields": QUOTE_FIELDS}
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
            if not data or data.get("f43") in (None, "", "-"):
                raise RuntimeError(f"东方财富未返回美股报价: {payload.get('message') or payload.get('rc')}")
            decimals = int(data.get("f59") or 2)
            now = datetime.now(timezone.utc)
            quote_ts = int(data.get("f86") or now.timestamp())
            et, tz_label = us_eastern_time(quote_ts)
            age_hours = round((now.timestamp() - quote_ts) / 3600, 2)
            session = market_status(et)
            warnings: list[str] = []
            if age_hours > 24:
                warnings.append(f"报价时间戳已过 {age_hours:.1f} 小时（可能遇休市/数据延迟），仅可作参考价")
            if session != "trading":
                warnings.append(f"当前非盘中（美东 {et.strftime('%Y-%m-%d %H:%M')} {tz_label}，状态 {session}），报价为收盘/延时价")
            confidence = "high" if age_hours <= 1 and session == "trading" else ("medium" if age_hours <= 24 else "low")
            return {
                "source": "eastmoney-us-quote",
                "market": "US",
                "symbol": str(data.get("f57") or symbol),
                "name": str(data.get("f58") or ""),
                "secid": secid,
                "exchange": US_MARKET_NAMES.get(secid.split(".", 1)[0], "UNKNOWN"),
                "price": {
                    "latest": scale_price(data.get("f43"), decimals),
                    "open": scale_price(data.get("f46"), decimals),
                    "high": scale_price(data.get("f44"), decimals),
                    "low": scale_price(data.get("f45"), decimals),
                    "prev_close": scale_price(data.get("f60"), decimals),
                    "decimals": decimals,
                    "currency": "USD",
                },
                "change": {
                    "amount": scale_price(data.get("f169"), decimals),
                    "pct": None if data.get("f170") in (None, "", "-") else round(int(data["f170"]) / 100, 2),
                },
                "volume": data.get("f47"),
                "amount": data.get("f48"),
                "quote_time_et": et.strftime("%Y-%m-%d %H:%M:%S") + f" {tz_label}",
                "quote_time_utc": datetime.fromtimestamp(quote_ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                "session_status": session,
                "data_age_hours": age_hours,
                "quality": {
                    "ok": True,
                    "warnings": warnings,
                },
                "traceability": {
                    "source": f"{endpoint} (secid={secid})",
                    "fetched_at_utc": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
                    "validation": "status=ok（东方财富公开接口实时返回）",
                    "confidence": confidence,
                },
                "diagnostics": {"endpoint": endpoint, "attempted": len(errors) + 1},
            }
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{endpoint}: {type(exc).__name__}: {exc}")
            time.sleep(0.5)
    raise RuntimeError("；".join(errors))


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch US-stock real-time quote from Eastmoney (guarded)")
    parser.add_argument("symbol", help="US ticker, e.g. AAPL, TSLA, BRK.B")
    parser.add_argument("--market", default="nasdaq", choices=sorted(US_MARKETS), help="Exchange (default: nasdaq)")
    parser.add_argument("--secid", help="Override Eastmoney secid, e.g. 105.AAPL / 106.BABA.")
    parser.add_argument("--strict", action="store_true", help="Return non-zero when the quote fetch fails.")
    args = parser.parse_args()

    try:
        secid = guess_us_secid(args.symbol, args.market, args.secid)
    except Exception as exc:
        print(json.dumps({
            "source": "eastmoney-us-quote",
            "market": "US",
            "symbol": args.symbol,
            "quality": {"ok": False, "warnings": [f"代码识别失败: {exc}"]},
            "traceability": {"validation": "status=fail（代码不合规）", "confidence": "none"},
        }, ensure_ascii=False, indent=2))
        return 2 if args.strict else 0

    try:
        result = fetch_quote(secid, args.symbol)
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({
            "source": "eastmoney-us-quote",
            "market": "US",
            "symbol": args.symbol,
            "secid": secid,
            "quality": {
                "ok": False,
                "warnings": [
                    f"东方财富美股报价获取失败: {type(exc).__name__}: {exc}",
                    "不得引用任何未经本脚本核验的实时价格；请稍后重试或让用户确认行情。",
                ],
            },
            "traceability": {"validation": "status=fail（取数失败）", "confidence": "none"},
        }, ensure_ascii=False, indent=2))
        return 2 if args.strict else 0

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
