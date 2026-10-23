#!/usr/bin/env bash
# 论文速览 · 批量提取编排（literature-distiller）—— POSIX 便捷入口
#
# 真正的实现在同目录的 distill_batch.py（跨平台，Windows 原生亦可用）。
# 本文件只做参数转发，不再承载任何业务逻辑——因此不存在「.sh 与 .py
# 双实现漂移」的问题；保留它只是为了不破坏既有的 bash 调用方式。
#
# 用法（选项与 .py 完全一致）：
#   bash scripts/distill_batch.sh [--input DIR] [--output DIR] [--single FILE]
#                                 [--mode text|technical] [--dry-run]
#
# 解释器优先级：$VENV_PY > python3 > python
# 退出码：0 = 全部成功；2 = 存在失败项；3 = 参数或环境错误（由 .py 决定并透传）

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

PY="${VENV_PY:-}"
if [ -z "$PY" ]; then
    if command -v python3 >/dev/null 2>&1; then
        PY="python3"
    elif command -v python >/dev/null 2>&1; then
        PY="python"
    else
        echo "[错误] 未找到 python3 / python；请安装 Python 3 或设置 VENV_PY 环境变量。" >&2
        exit 3
    fi
fi

exec "$PY" "$SCRIPT_DIR/distill_batch.py" "$@"
