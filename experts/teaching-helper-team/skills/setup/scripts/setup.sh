#!/bin/sh
# 教学帮帮团 初始化引导（macOS / Linux）
# 直接用 WorkBuddy 托管 Python 运行 setup.py；未找到则使用系统 python3。
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PY="$(ls -d "$HOME/.workbuddy/binaries/python/versions/"*/bin/python3 2>/dev/null | sort -r | head -1)"
PY="${PY:-$(command -v python3 || command -v python)}"
if [ -z "$PY" ]; then
  echo "FATAL: 未找到 Python（需 3.8+）" >&2
  exit 2
fi
exec "$PY" "$SCRIPT_DIR/setup.py" "$@"
