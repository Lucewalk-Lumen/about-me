#!/usr/bin/env python3
"""Run simple strategy backtests on K-line CSV data. Pure standard library.

Input: CSV files produced by fetch_us_kline.py / fetch_eastmoney_kline.py
(fields: date, open, close, high, low, volume, amount, ...) — only `date` and
`close` are required.

Strategies:
  ma_cross  dual moving-average crossover (params: fast, slow)
  buy_hold  buy at first bar close, sell at last bar close
  dca       fixed-interval dollar-cost averaging (param: interval)

Metrics: total return, annualized return, Sharpe (rf=0, 252 trading days),
max drawdown, per-trade win rate, trade log and equity-curve tail.

Guardrails: at most 5 symbols per run; each series capped at the most recent
500 bars (configurable up to 2000); results are historical, never a promise.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any

TRADING_DAYS_PER_YEAR = 252
MAX_SYMBOLS = 5
DEFAULT_BAR_CAP = 500
HARD_BAR_CAP = 2000
DISCLAIMER = (
    "回测基于历史数据与简化假设（不含交易成本、滑点、涨跌停/做空限制、资金费率），"
    "仅供研究参考，不代表未来收益，不构成投资建议。"
)


def read_kline_csv(path: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or "date" not in reader.fieldnames or "close" not in reader.fieldnames:
            raise ValueError(f"CSV 需含 date 与 close 列: {path}")
        for raw in reader:
            date = (raw.get("date") or "").strip()
            close_raw = (raw.get("close") or "").strip()
            if not date or close_raw in {"", "-", "--"}:
                continue
            try:
                close = float(close_raw)
            except ValueError:
                continue
            rows.append({"date": date, "close": close})
    if len(rows) < 2:
        raise ValueError(f"有效 K 线少于 2 根: {path}")
    return rows


def sma(values: list[float], window: int) -> list[float | None]:
    out: list[float | None] = [None] * len(values)
    running = 0.0
    for i, value in enumerate(values):
        running += value
        if i >= window:
            running -= values[i - window]
        if i >= window - 1:
            out[i] = running / window
    return out


def simulate_ma_cross(closes: list[float], dates: list[str], fast: int, slow: int) -> dict[str, Any]:
    fast_ma = sma(closes, fast)
    slow_ma = sma(closes, slow)
    holding = False
    entry_price = 0.0
    entry_date = ""
    equity: list[float] = []
    trades: list[dict[str, Any]] = []
    for i, price in enumerate(closes):
        if fast_ma[i] is None or slow_ma[i] is None:
            equity.append(price if not holding else price)
            continue
        prev_ready = i > 0 and fast_ma[i - 1] is not None and slow_ma[i - 1] is not None
        crossed_up = prev_ready and fast_ma[i] > slow_ma[i] and fast_ma[i - 1] <= slow_ma[i - 1]
        crossed_down = prev_ready and fast_ma[i] < slow_ma[i] and fast_ma[i - 1] >= slow_ma[i - 1]
        if crossed_up and not holding:
            holding = True
            entry_price = price
            entry_date = dates[i]
        elif crossed_down and holding:
            pnl_pct = round((price / entry_price - 1) * 100, 2)
            trades.append({
                "entry_date": entry_date,
                "entry_price": entry_price,
                "exit_date": dates[i],
                "exit_price": price,
                "pnl_pct": pnl_pct,
            })
            holding = False
        equity.append(price)
    if holding:  # 期末仍持仓，按最后收盘价平仓计入
        price = closes[-1]
        trades.append({
            "entry_date": entry_date,
            "entry_price": entry_price,
            "exit_date": dates[-1],
            "exit_price": price,
            "pnl_pct": round((price / entry_price - 1) * 100, 2),
            "note": "期末强平（回测截止）",
        })
    # 以 1 单位资金按信号满仓轮动，近似净值曲线
    nav = 1.0
    nav_curve: list[float] = []
    pos = False
    entry_nav = 1.0
    entry_price = 0.0
    for i, price in enumerate(closes):
        if fast_ma[i] is None or slow_ma[i] is None:
            nav_curve.append(nav)
            continue
        prev_ready = i > 0 and fast_ma[i - 1] is not None and slow_ma[i - 1] is not None
        crossed_up = prev_ready and fast_ma[i] > slow_ma[i] and fast_ma[i - 1] <= slow_ma[i - 1]
        crossed_down = prev_ready and fast_ma[i] < slow_ma[i] and fast_ma[i - 1] >= slow_ma[i - 1]
        if crossed_up and not pos:
            pos = True
            entry_nav = nav
            entry_price = price
        elif crossed_down and pos:
            nav = entry_nav * (price / entry_price)
            pos = False
        nav_curve.append(nav if not pos else entry_nav * (price / entry_price))
    return {"trades": trades, "nav": nav_curve}


def simulate_buy_hold(closes: list[float], dates: list[str]) -> dict[str, Any]:
    nav = [price / closes[0] for price in closes]
    trades = [{
        "entry_date": dates[0],
        "entry_price": closes[0],
        "exit_date": dates[-1],
        "exit_price": closes[-1],
        "pnl_pct": round((closes[-1] / closes[0] - 1) * 100, 2),
    }]
    return {"trades": trades, "nav": nav}


def simulate_dca(closes: list[float], dates: list[str], interval: int) -> dict[str, Any]:
    shares = 0.0
    cash = 1.0
    per_buy = 1.0 / max(1, len(range(0, len(closes), interval)))
    nav: list[float] = []
    for i, price in enumerate(closes):
        if i % interval == 0 and cash > 1e-12:
            buy_units = min(per_buy, cash) / price
            shares += buy_units
            cash -= min(per_buy, cash)
        nav.append(cash + shares * price)
    trades = [{
        "entry_date": dates[0],
        "entry_price": closes[0],
        "exit_date": dates[-1],
        "exit_price": closes[-1],
        "pnl_pct": round((nav[-1] / nav[0] - 1) * 100, 2),
        "note": f"每 {interval} 根定额买入，期末整体结算",
    }]
    return {"trades": trades, "nav": nav}


def metrics(nav: list[float], trades: list[dict[str, Any]]) -> dict[str, Any]:
    if len(nav) < 2:
        return {"total_return_pct": 0.0}
    total_return = nav[-1] / nav[0] - 1
    daily = [nav[i] / nav[i - 1] - 1 for i in range(1, len(nav)) if nav[i - 1] > 0]
    sharpe = None
    if len(daily) >= 2 and statistics.pstdev(daily) > 0:
        sharpe = round(statistics.fmean(daily) / statistics.pstdev(daily) * math.sqrt(TRADING_DAYS_PER_YEAR), 2)
    peak = nav[0]
    max_dd = 0.0
    for value in nav:
        peak = max(peak, value)
        if peak > 0:
            max_dd = min(max_dd, value / peak - 1)
    years = len(nav) / TRADING_DAYS_PER_YEAR
    annualized = (1 + total_return) ** (1 / years) - 1 if years > 0 and (1 + total_return) > 0 else None
    closed = [t for t in trades if "pnl_pct" in t]
    wins = [t for t in closed if t["pnl_pct"] > 0]
    return {
        "total_return_pct": round(total_return * 100, 2),
        "annualized_return_pct": None if annualized is None else round(annualized * 100, 2),
        "sharpe": sharpe,
        "max_drawdown_pct": round(max_dd * 100, 2),
        "trades": len(closed),
        "win_rate_pct": None if not closed else round(len(wins) / len(closed) * 100, 2),
    }


def run_one(path: str, strategy: str, fast: int, slow: int, interval: int, bar_cap: int) -> dict[str, Any]:
    rows = read_kline_csv(path)
    truncated = len(rows) > bar_cap
    if truncated:
        rows = rows[-bar_cap:]
    dates = [r["date"] for r in rows]
    closes = [r["close"] for r in rows]
    symbol = Path(path).stem
    warnings: list[str] = []
    if truncated:
        warnings.append(f"K 线超过 {bar_cap} 根，已截取最近 {bar_cap} 根")
    need = {"ma_cross": slow + 1, "buy_hold": 2, "dca": 2}.get(strategy, 2)
    if len(closes) < need:
        return {
            "symbol": symbol,
            "strategy": strategy,
            "quality": {"ok": False, "warnings": [f"有效 K 线 {len(closes)} 根 < 策略所需 {need} 根，跳过"]},
        }
    if strategy == "ma_cross":
        result = simulate_ma_cross(closes, dates, fast, slow)
        params = {"fast": fast, "slow": slow}
    elif strategy == "buy_hold":
        result = simulate_buy_hold(closes, dates)
        params = {}
    else:
        result = simulate_dca(closes, dates, interval)
        params = {"interval": interval}
    return {
        "symbol": symbol,
        "strategy": strategy,
        "params": params,
        "range": {"start": dates[0], "end": dates[-1], "bars": len(closes)},
        "metrics": metrics(result["nav"], result["trades"]),
        "trades": result["trades"],
        "equity_curve_tail": [round(v, 4) for v in result["nav"][-10:]],
        "quality": {"ok": True, "warnings": warnings},
    }


def run_grid(path: str, fasts: list[int], slows: list[int], bar_cap: int) -> dict[str, Any]:
    rows = read_kline_csv(path)
    if len(rows) > bar_cap:
        rows = rows[-bar_cap:]
    dates = [r["date"] for r in rows]
    closes = [r["close"] for r in rows]
    grid: list[dict[str, Any]] = []
    for fast in fasts:
        for slow in slows:
            if fast >= slow:
                continue
            if len(closes) < slow + 1:
                continue
            result = simulate_ma_cross(closes, dates, fast, slow)
            m = metrics(result["nav"], result["trades"])
            grid.append({"fast": fast, "slow": slow, **m})
    grid.sort(key=lambda item: (item["sharpe"] is not None, item["sharpe"] or -99), reverse=True)
    return {
        "symbol": Path(path).stem,
        "strategy": "ma_cross",
        "grid": grid,
        "quality": {"ok": bool(grid), "warnings": [] if grid else ["无满足 fast<slow 且样本足够的参数组合"]},
    }


def parse_grid(text: str) -> tuple[list[int], list[int]]:
    fasts: list[int] = []
    slows: list[int] = []
    for part in text.split(";"):
        if "=" not in part:
            continue
        key, _, values = part.partition("=")
        nums = [int(v) for v in values.split(",") if v.strip().isdigit()]
        if key.strip() == "fast":
            fasts = nums
        elif key.strip() == "slow":
            slows = nums
    return fasts, slows


def main() -> int:
    parser = argparse.ArgumentParser(description="Backtest simple strategies on K-line CSV (pure stdlib)")
    parser.add_argument("inputs", nargs="+", help="K-line CSV file path(s), at most 5")
    parser.add_argument("--strategy", default="ma_cross", choices=("ma_cross", "buy_hold", "dca"))
    parser.add_argument("--fast", type=int, default=5, help="Fast MA window (ma_cross)")
    parser.add_argument("--slow", type=int, default=20, help="Slow MA window (ma_cross)")
    parser.add_argument("--interval", type=int, default=20, help="DCA interval in bars (dca)")
    parser.add_argument("--grid", help='Param grid, e.g. "fast=5,10,20;slow=20,60" (ma_cross only)')
    parser.add_argument("--bar-cap", type=int, default=DEFAULT_BAR_CAP, help=f"Max bars per symbol (<= {HARD_BAR_CAP})")
    parser.add_argument("--format", choices=("json", "table"), default="json")
    args = parser.parse_args()

    if len(args.inputs) > MAX_SYMBOLS:
        print(json.dumps({"quality": {"ok": False, "warnings": [f"单次最多 {MAX_SYMBOLS} 个标的，收到 {len(args.inputs)} 个"]}}, ensure_ascii=False, indent=2))
        return 2
    if args.bar_cap <= 0 or args.bar_cap > HARD_BAR_CAP:
        print(json.dumps({"quality": {"ok": False, "warnings": [f"--bar-cap 须在 1..{HARD_BAR_CAP}"]}}, ensure_ascii=False, indent=2))
        return 2
    if args.fast <= 0 or args.slow <= 0 or args.fast >= args.slow:
        print(json.dumps({"quality": {"ok": False, "warnings": ["ma_cross 需 0 < fast < slow"]}}, ensure_ascii=False, indent=2))
        return 2

    results: list[dict[str, Any]] = []
    for path in args.inputs:
        try:
            if args.grid:
                fasts, slows = parse_grid(args.grid)
                if not fasts or not slows:
                    raise ValueError('--grid 格式应为 "fast=5,10;slow=20,60"')
                results.append(run_grid(path, fasts, slows, args.bar_cap))
            else:
                results.append(run_one(path, args.strategy, args.fast, args.slow, args.interval, args.bar_cap))
        except Exception as exc:  # noqa: BLE001
            results.append({
                "symbol": Path(path).stem,
                "quality": {"ok": False, "warnings": [f"回测失败: {type(exc).__name__}: {exc}"]},
            })

    ok = any(r.get("quality", {}).get("ok") for r in results)
    payload = {
        "source": "strategy-backtest",
        "strategy": "ma_cross" if args.grid else args.strategy,
        "results": results,
        "disclaimer": DISCLAIMER,
        "quality": {"ok": ok, "warnings": []},
    }

    if args.format == "table":
        for r in results:
            print(f"== {r.get('symbol')} [{r.get('strategy')}] ==")
            if not r.get("quality", {}).get("ok"):
                print("   跳过:", r["quality"]["warnings"])
                continue
            if "grid" in r:
                for row in r["grid"][:10]:
                    print(f"   fast={row['fast']:>3} slow={row['slow']:>3}  收益={row['total_return_pct']:>7}%  夏普={row['sharpe']}  回撤={row['max_drawdown_pct']}%  胜率={row['win_rate_pct']}%")
            else:
                m = r["metrics"]
                print(f"   区间 {r['range']['start']}~{r['range']['end']}（{r['range']['bars']} 根）")
                print(f"   总收益={m['total_return_pct']}%  年化={m['annualized_return_pct']}%  夏普={m['sharpe']}  最大回撤={m['max_drawdown_pct']}%  交易={m['trades']}  胜率={m['win_rate_pct']}%")
        print(f"\n{DISCLAIMER}")
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
