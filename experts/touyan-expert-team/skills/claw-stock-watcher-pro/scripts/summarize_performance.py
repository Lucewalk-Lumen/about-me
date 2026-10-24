#!/usr/bin/env python3
"""
Summarize the performance of all stocks in the watchlist.
User-visible current quotes are fetched through market_data_guard.py.
"""
import json
import os
from pathlib import Path
import subprocess
import sys

# Standardized watchlist file path
WATCHLIST_FILE = os.path.expanduser("~/.clawdbot/stock_watcher/watchlist.txt")

def canonical_symbol(stock_code):
    """Add an exchange suffix for common six-digit A-share codes."""
    code = stock_code.strip()
    if code.startswith(("6", "9")):
        return f"{code}.SH"
    if code.startswith(("0", "2", "3")):
        return f"{code}.SZ"
    if code.startswith(("4", "8")):
        return f"{code}.BJ"
    return code


def fetch_verified_quote(stock_code):
    """Fetch a current quote through the package's fail-closed guard."""
    guard_script = Path(__file__).resolve().parents[2] / "astock-report" / "scripts" / "market_data_guard.py"
    if not guard_script.is_file():
        return {"status": "failed"}
    try:
        proc = subprocess.run(
            [sys.executable, str(guard_script), "quote", canonical_symbol(stock_code), "--json"],
            check=False,
            text=True,
            capture_output=True,
            timeout=45,
        )
        return json.loads(proc.stdout or "{}")
    except Exception as e:
        print(f"Error fetching verified quote for {stock_code}: {e}", file=sys.stderr)
        return {"status": "failed"}

def summarize_performance():
    """Summarize performance of all stocks in watchlist."""
    if not os.path.exists(WATCHLIST_FILE):
        return
    
    with open(WATCHLIST_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    if not lines or all(not line.strip() for line in lines):
        return
    
    for line in lines:
        line = line.strip()
        if line:
            parts = line.split('|')
            if len(parts) == 2:
                code, name = parts
                
                payload = fetch_verified_quote(code)
                quote = payload.get("quote") or {}
                if payload.get("status") == "ok" and quote.get("price") is not None:
                    pct = quote.get("pct")
                    pct_text = f"{float(pct):+.2f}%" if pct is not None else "涨跌幅暂缺"
                    quote_time = quote.get("time") or "时间暂缺"
                    source = quote.get("primary_source") or "AkShare + 核验源"
                    print(f"{code} - {name} - 当前价: {float(quote['price']):.2f} ({pct_text}) - 截至 {quote_time} - 来源: {source}")
                else:
                    print(f"{code} - {name} - 暂无可验证实时行情")

if __name__ == "__main__":
    summarize_performance()
