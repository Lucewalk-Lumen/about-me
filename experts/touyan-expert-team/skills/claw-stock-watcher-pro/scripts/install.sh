#!/bin/bash
# Install stock-watcher skill dependencies and initialize watchlist directory

set -e

echo "Installing stock-watcher skill dependencies..."

# Create the watchlist directory
mkdir -p ~/.clawdbot/stock_watcher

# Create empty watchlist file if it doesn't exist
WATCHLIST_FILE="$HOME/.clawdbot/stock_watcher/watchlist.txt"
if [ ! -f "$WATCHLIST_FILE" ]; then
    touch "$WATCHLIST_FILE"
    echo "Created empty watchlist file: $WATCHLIST_FILE"
fi

# Check if required Python packages are available
if ! python3 -c "import akshare, requests, bs4" 2>/dev/null; then
    echo "Warning: Required Python packages (akshare, requests, beautifulsoup4) not found."
    echo "Install the package dependencies from the Agent workspace: pip install -r requirements.txt"
fi

echo "Stock-watcher skill installed successfully!"
echo "Watchlist directory: ~/.clawdbot/stock_watcher/"
echo "Watchlist file: ~/.clawdbot/stock_watcher/watchlist.txt"
