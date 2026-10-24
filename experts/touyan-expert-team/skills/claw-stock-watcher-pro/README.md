# Stock Watcher Skill

A standardized stock watchlist management skill for Clawdbot that provides clean, consistent functionality for tracking Chinese A-share stocks.

> 跨平台：文中命令统一 `python3`，Windows 上解释器名通常为 `python`。

## Features

- ✅ **Add stocks** to watchlist using 6-digit stock codes
- ✅ **View watchlist** with clear formatting
- ✅ **Remove individual stocks** from watchlist
- ✅ **Clear entire watchlist** with one command
- ✅ **Get performance summary** for all watched stocks
- ✅ **Standardized storage path** - no more path confusion!
- ✅ **Easy installation/uninstallation**

## Installation

For new users, the skill will be automatically installed when first used. The installation script creates:

- Standardized watchlist directory: `~/.clawdbot/stock_watcher/`
- Watchlist file: `~/.clawdbot/stock_watcher/watchlist.txt`
- All necessary scripts in the skill directory

## Usage Commands

### Add a stock
```bash
cd ./skills/claw-stock-watcher-pro/scripts && python3 add_stock.py 600053
```

### View watchlist
```bash
cd ./skills/claw-stock-watcher-pro/scripts && python3 list_stocks.py
```

### Remove a stock
```bash
cd ./skills/claw-stock-watcher-pro/scripts && python3 remove_stock.py 600053
```

### Clear watchlist
```bash
cd ./skills/claw-stock-watcher-pro/scripts && python3 clear_watchlist.py
```

### Get performance summary
```bash
cd ./skills/claw-stock-watcher-pro/scripts && python3 summarize_performance.py
```

## Data Source

- **Current quote gateway**: `./skills/astock-report/scripts/market_data_guard.py quote`
- **Quote policy**: AkShare primary + at least one verifier; only `status=ok` is shown as a current quote
- **10jqka usage**: stock-name lookup and detail links only, not the user-visible current quote
- **Supported markets**: Shanghai, Shenzhen, STAR Market, and common Beijing Stock Exchange codes

## File Structure

```
stock-watcher/
├── SKILL.md                 # Skill metadata and instructions
├── scripts/
│   ├── config.py           # Centralized configuration
│   ├── add_stock.py        # Add stock to watchlist
│   ├── list_stocks.py      # List all stocks in watchlist
│   ├── remove_stock.py     # Remove specific stock
│   ├── clear_watchlist.py  # Clear entire watchlist
│   ├── summarize_performance.py # Get stock performance data
│   ├── install.sh          # Installation script
│   └── uninstall.sh        # Uninstallation script
└── references/             # (Reserved for future reference docs)
```

## Storage Location

All user data is stored in a single, standardized location:
- **Directory**: `~/.clawdbot/stock_watcher/`
- **Watchlist file**: `~/.clawdbot/stock_watcher/watchlist.txt`

Format: `stock_code|stock_name` (e.g., `600053|九鼎投资`)

## Troubleshooting

### "Command not found" errors
Ensure you have Python 3 and required packages installed:
```bash
pip3 install requests beautifulsoup4
```

### Network issues
The skill uses the local market-data guard for current quotes and may use 10jqka.com.cn for stock-name lookup. Ensure network access is available for the configured sources.

### Permission errors
Make sure the `~/.clawdbot/` directory is writable by your user.

## Uninstallation

To completely remove the skill and all data:
```bash
cd ./skills/claw-stock-watcher-pro/scripts && ./uninstall.sh
```

This removes the watchlist data under `~/.clawdbot/stock_watcher/`; it does not delete the packaged skill scripts.
