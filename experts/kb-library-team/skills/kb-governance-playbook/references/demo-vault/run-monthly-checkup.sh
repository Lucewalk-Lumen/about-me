#!/bin/bash
# 客户运营知识库 - 月度体检一键脚本
# 用法：bash run-monthly-checkup.sh
# 产出：demo-vault 全量机械层体检报告（ stdout ）

VAULT="$(cd "$(dirname "$0")" && pwd)"
SCRIPTS="$(cd "$VAULT/.." && pwd)/../scripts"
PY="$(command -v python3)"

if [ ! -x "$PY" ]; then
  echo "[FAIL] 未找到 python3，请先安装 Python 3 后重试。"
  exit 2
fi

echo "================================================================"
echo "客户运营知识库 - 月度体检报告 $(date +%Y-%m-%d)"
echo "库路径：$VAULT"
echo "================================================================"
echo

echo "【1/4】死链与孤儿扫描"
echo "----------------------------------------------------------------"
"$PY" "$SCRIPTS/link_integrity_scan.py" "$VAULT"
echo

echo "【2/4】重复/高度相近条目检测"
echo "----------------------------------------------------------------"
"$PY" "$SCRIPTS/duplicate_detect.py" "$VAULT"
echo

echo "【3/4】晋级门槛预检（元数据基线）"
echo "----------------------------------------------------------------"
"$PY" "$SCRIPTS/promotion_gate_check.py" "$VAULT"
echo

echo "【4/4】四池分布统计（供健康分计算）"
echo "----------------------------------------------------------------"
IDEA=$(find "$VAULT/01-ideas" -name "*.md" 2>/dev/null | wc -l | tr -d ' ')
DRAFT=$(find "$VAULT/02-drafts" -name "*.md" 2>/dev/null | wc -l | tr -d ' ')
OFFICIAL=$(find "$VAULT/03-official" -name "*.md" 2>/dev/null | wc -l | tr -d ' ')
ARCHIVE=$(find "$VAULT/04-archive" -name "*.md" 2>/dev/null | wc -l | tr -d ' ')
META=$(find "$VAULT/99-meta" -name "*.md" 2>/dev/null | wc -l | tr -d ' ')
TOTAL=$((IDEA + DRAFT + OFFICIAL + ARCHIVE + META))
echo "idea=$IDEA draft=$DRAFT official=$OFFICIAL archive=$ARCHIVE meta=$META total=$TOTAL"
echo
echo "提示：把上述四池分布与第 1/2/3 步计数喂给 health_score_calc.py 即可得总分。"
echo "================================================================"
