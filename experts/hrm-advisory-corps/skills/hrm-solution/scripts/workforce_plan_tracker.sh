#!/bin/bash
# workforce_plan_tracker.sh — 人力规划数据生成 / 缺口实算 / 跟踪
# 配套 skills/org-planning/references/workforce-planning.md 使用
# 用法：
#   ./workforce_plan_tracker.sh generate <output.json> [--revenue N] [--headcount N] [--industry saas|consulting|manufacturing|retail]
#   ./workforce_plan_tracker.sh gap <plan.json>
#   ./workforce_plan_tracker.sh priority <gap.json>
#   ./workforce_plan_tracker.sh mix <ftes> <contractors> <outsourced> <ai_agents>
#
# 口径说明：
#   generate / mix 为确定性计算；
#   gap 对「编制缺口」做实算（需求 − 现有），其余缺口维度依赖原件的额外输入，只输出公式与填报指引；
#   priority 按 §3 公式计分（需提供 3 项 1–5 评分），缺评分时为「引导式」输出。
#
# JSON 解析说明：
#   优先使用 jq（正确处理任意嵌套与转义）；无 jq 时回退到内置 awk 提取器。
#   注意：不要退化为朴素的 sed/grep 键提取——嵌套 JSON 上会命中最后出现的
#   同名键而静默错值（例如外层 25/20 被内层 999/1 覆盖却仍 exit 0）。
#   现改为：提取器统计同名键的**出现次数**，出现多次即判定为歧义并以非零码退出，
#   绝不静默在错误数据上计算。
#   残留局限（诚实声明）：无 jq 时，awk 提取器按「键名唯一出现」的前提工作，
#   不支持转义引号（\"）与键名出现在字符串值内部的极端情况；
#   生产环境建议安装 jq，本脚本会自动优先使用。
set -euo pipefail

VERSION="1.0.0"
INDUSTRY_RPE_DEFAULT=200  # 默认 SaaS 万元/人

cmd=${1:-help}
shift || true

# ---------- helpers ----------
err() { echo "[ERR] $*" >&2; exit 1; }
info() { echo "[INFO] $*"; }
hr() { echo "----------------------------------------"; }

# 非负整数校验（避免 abc / -1 触发裸 unbound variable）
is_nonneg_int() { [[ "$1" =~ ^[0-9]+$ ]]; }

have_jq() { command -v jq >/dev/null 2>&1; }

# JSON 取值：$1=文件 $2=键 $3=类型(num|str)
# 计数同名键，出现 >1 次视为歧义 → 报错退出（不静默取错层）。
json_get() {
  local file=$1 key=$2 typ=$3
  if have_jq; then
    local n
    n=$(jq --arg k "$key" '[paths(scalars) as $p | select($p[-1] == $k)] | length' "$file" 2>/dev/null) || n=0
    if [[ "$n" -gt 1 ]]; then
      err "$(basename "$file"): 键 \"$key\" 出现 $n 次，无法确定取值层级（疑似嵌套重复键）。请用 jq 或消除重复键后重试"
    fi
    # jq 分支：num/str 取值表达式一致（jq -r 对字符串自动去引号），故只调用一次。
    jq -r --arg k "$key" 'first(paths(scalars) as $p | select($p[-1] == $k) | getpath($p)) // empty' "$file"
    return 0
  fi
  # --- awk 回退：无 jq 时的 best-effort 提取 ---
  local re
  if [[ "$typ" == num ]]; then
    re="\"$key\"[[:space:]]*:[[:space:]]*-?[0-9]+"
  else
    re="\"$key\"[[:space:]]*:[[:space:]]*\""
  fi
  local count
  count=$(awk -v re="$re" 'BEGIN{n=0} {t=$0; while (match(t, re)) {n++; t=substr(t, RSTART+RLENGTH)}} END{print n+0}' "$file")
  if [[ "$count" -gt 1 ]]; then
    err "$(basename "$file"): 键 \"$key\" 出现 $count 次，无法确定取值层级（疑似嵌套重复键；未安装 jq 时无法判定正确的层）。请安装 jq 或消除重复键后重试"
  fi
  if [[ "$count" -eq 0 ]]; then
    return 0
  fi
  if [[ "$typ" == num ]]; then
    sed -n "s/.*\"$key\"[[:space:]]*:[[:space:]]*\(-\{0,1\}[0-9][0-9]*\).*/\1/p" "$file" | head -1
  else
    sed -n "s/.*\"$key\"[[:space:]]*:[[:space:]]*\"\([^\"]*\)\".*/\1/p" "$file" | head -1
  fi
}

# 从生成的扁平 JSON 中取数值
json_num() { json_get "$1" "$2" num; }
# 从扁平 JSON 中取字符串
json_str() { json_get "$1" "$2" str; }

# 行业 → 人均收入（万元）
industry_rpe() {
  case "$1" in
    saas) echo 200 ;;
    internet) echo 180 ;;
    consulting) echo 130 ;;
    manufacturing) echo 55 ;;
    retail) echo 42 ;;
    *) echo "$INDUSTRY_RPE_DEFAULT" ;;
  esac
}

# ---------- generate ----------
do_generate() {
  out=""
  rev=""
  hc=""
  industry="saas"
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --revenue)
        [[ -n "${2:-}" ]] || err "generate: --revenue 缺少取值"
        rev=$2; shift 2 ;;
      --headcount)
        [[ -n "${2:-}" ]] || err "generate: --headcount 缺少取值"
        hc=$2; shift 2 ;;
      --industry)
        [[ -n "${2:-}" ]] || err "generate: --industry 缺少取值"
        industry=$2; shift 2 ;;
      *) [[ -z "$out" ]] && out=$1; shift ;;
    esac
  done
  [[ -z "$out" ]] && err "generate: 缺少 <output.json> 参数"
  [[ -z "$rev" ]] && err "generate: 缺少 --revenue N（目标年收入，万元）"
  [[ -z "$hc" ]] && err "generate: 缺少 --headcount N（现有编制）"
  is_nonneg_int "$rev" || err "generate: --revenue 必须是非负整数"
  is_nonneg_int "$hc" || err "generate: --headcount 必须是非负整数"
  [[ $rev -le 0 ]] && err "generate: --revenue 必须大于 0"
  [[ $hc -le 0 ]] && err "generate: --headcount 必须大于 0"

  rpe=$(industry_rpe "$industry")
  required=$(awk -v r="$rev" -v e="$rpe" 'BEGIN{printf "%d", r/e+0.5}')
  gap=$((required - hc))

  cat > "$out" <<EOF
{
  "industry": "$industry",
  "revenue_target_wan": $rev,
  "revenue_per_employee_wan": $rpe,
  "current_headcount": $hc,
  "required_headcount": $required,
  "headcount_gap": $gap,
  "gap_status": "$([ $gap -gt 0 ] && echo "under-staffed" || ([ $gap -lt 0 ] && echo "over-staffed" || echo "balanced"))",
  "generated_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
  info "已生成: $out (需求 $required / 现有 $hc / 缺口 $gap)"
}

# ---------- gap（实算：编制缺口）----------
do_gap() {
  plan=${1:-}
  [[ -n "$plan" ]] || err "gap: 缺少 <plan.json> 参数"
  [[ -f "$plan" ]] || err "gap: 文件不存在 $plan"

  req=$(json_num "$plan" required_headcount)
  cur=$(json_num "$plan" current_headcount)
  [[ -n "$req" && -n "$cur" ]] || err "gap: $plan 缺少 required_headcount / current_headcount（请先运行 generate 生成）"

  abs=$((req - cur))
  if [[ $cur -gt 0 ]]; then
    ratio=$(awk -v a="$abs" -v c="$cur" 'BEGIN{printf "%+.1f", a*100/c}')
  else
    ratio="n/a"
  fi
  if [[ $abs -gt 0 ]]; then status="under-staffed（缺编）"; elif [[ $abs -lt 0 ]]; then status="over-staffed（超编）"; else status="balanced（平衡）"; fi

  info "缺口分析（实算）："
  info "源文件: $plan"
  info "  编制缺口 = 需求(headcount) − 现有(headcount) = $req − $cur = $abs 人"
  info "  缺口比率 = $ratio%（相对现有编制）"
  info "  状态: $status"
  info "  注：原件 §3 公式为「需求 − 现有 − 管道中待入职」；管道中人数未随 generate 生成，如需精确请补填后重算。"
  hr
  info "以下维度依赖原件 §3 表格中未随 generate 生成的输入，本脚本不臆造输入，仅给出公式与填报指引："
  info "  - 技能缺口   = 目标技能等级 − 现有平均技能等级（按胜任力分组）"
  info "  - 经验缺口   = 需 5+ 年岗位数 − 现有 5+ 年员工数"
  info "  - 多样性缺口 = 目标代表性 − 现有代表性（性别/学历/年龄结构）"
  info "  - 预算缺口   = 所需全负荷成本 − 已批预算"
  info "  请将上述 4 项缺口填入 workforce-planning.md §3 表格。"
}

# ---------- priority（§3 公式；缺评分为引导式）----------
do_priority() {
  gapfile=${1:-}
  [[ -n "$gapfile" ]] || err "priority: 缺少 <gap.json> 参数"
  [[ -f "$gapfile" ]] || err "priority: 文件不存在 $gapfile"

  bi=$(json_num "$gapfile" business_impact)
  ft=$(json_num "$gapfile" fill_time)
  ar=$(json_num "$gapfile" availability_risk)

  if [[ -n "$bi" && -n "$ft" && -n "$ar" ]]; then
    for pair in "业务影响:$bi" "填补周期:$ft" "可得性风险:$ar"; do
      v=${pair#*:}
      { [[ "$v" =~ ^[0-9]+$ ]] && [[ $v -ge 1 && $v -le 5 ]]; } || err "priority: ${pair%%:*} 必须是 1-5 的整数，收到: $v"
    done
    score=$(( bi * 3 + ft * 2 + ar * 1 ))
    info "优先级评分（实算，workforce-planning.md §3 公式）："
    info "  优先级 = 业务影响($bi)×3 + 填补周期($ft)×2 + 可得性风险($ar)×1 = $score"
    if [[ $score -ge 20 ]]; then
      info "  ≥ 20：进入「立即行动」队列"
    else
      info "  < 20：常规排期"
    fi
  else
    info "[引导式] 优先级评分："
    info "  公式: 优先级 = (业务影响 × 3) + (填补周期 × 2) + (可得性风险 × 1)，每项 1-5 分，≥ 20 立即行动"
    info "  源数据: $gapfile 未提供 business_impact / fill_time / availability_risk 三项评分"
    info "  请人工按 1-5 分评估后填入 workforce-planning.md §3 表格（本脚本不臆造评分）。"
  fi
}

# ---------- mix ----------
do_mix() {
  ftes=${1:?mix: 缺少 ftes}
  contractors=${2:?mix: 缺少 contractors}
  outsourced=${3:?mix: 缺少 outsourced}
  ai_agents=${4:?mix: 缺少 ai_agents}

  for v in "$ftes" "$contractors" "$outsourced" "$ai_agents"; do
    is_nonneg_int "$v" || err "mix: 各用工数必须是非负整数，收到: $v"
  done

  total=$((ftes + contractors + outsourced + ai_agents))
  [[ $total -le 0 ]] && err "mix: 总数不能为 0"

  p_fte=$(awk -v a="$ftes" -v t="$total" 'BEGIN{printf "%.1f", a*100/t}')
  p_con=$(awk -v a="$contractors" -v t="$total" 'BEGIN{printf "%.1f", a*100/t}')
  p_out=$(awk -v a="$outsourced" -v t="$total" 'BEGIN{printf "%.1f", a*100/t}')
  p_ai=$(awk -v a="$ai_agents" -v t="$total" 'BEGIN{printf "%.1f", a*100/t}')

  info "用工结构占比："
  info "  全职   : $ftes ($p_fte%)  [目标 70-80%]"
  info "  合同/顾: $contractors ($p_con%)  [目标 10-15%]"
  info "  外包   : $outsourced ($p_out%)  [目标 5-10%]"
  info "  AI 智能: $ai_agents ($p_ai%)  [目标 5-15%]"

  # 简易偏离提示（边界值视为合规）
  if ! awk -v p="$p_fte" 'BEGIN{exit (p+0 < 70 || p+0 > 80)}'; then info "[!]  全职占比偏离 70-80% 目标"; fi
  if ! awk -v p="$p_con" 'BEGIN{exit (p+0 < 10 || p+0 > 15)}'; then info "[!]  合同占比偏离 10-15% 目标"; fi
  if ! awk -v p="$p_out" 'BEGIN{exit (p+0 < 5 || p+0 > 10)}'; then info "[!]  外包占比偏离 5-10% 目标"; fi
  if ! awk -v p="$p_ai" 'BEGIN{exit (p+0 < 5 || p+0 > 15)}'; then info "[!]  AI 智能体占比偏离 5-15% 目标"; fi
}

# ---------- help ----------
do_help() {
  cat <<EOF
workforce_plan_tracker.sh v$VERSION
配套 workforce-planning.md 使用

子命令：
  generate <out.json> [--revenue N] [--headcount N] [--industry saas|consulting|manufacturing|retail|internet]
      确定性计算：所需编制 = 目标收入 ÷ 人均收入
  gap <plan.json>
      实算：编制缺口 = 需求 − 现有（绝对 / 比率 / 状态）；其余缺口维度给出公式与填报指引
  priority <gap.json>
      优先级评分（引导式）：提供 business_impact / fill_time / availability_risk 三项 1-5 评分则按 §3 公式计算，否则输出填写指引
  mix <ftes> <contractors> <outsourced> <ai_agents>
      确定性计算：用工结构占比与偏离提示
  help
EOF
}

# ---------- main ----------
case "$cmd" in
  generate) do_generate "$@" ;;
  gap) do_gap "$@" ;;
  priority) do_priority "$@" ;;
  mix) do_mix "$@" ;;
  help|--help|-h|"") do_help ;;
  *) err "未知子命令: $cmd（运行 help 查看用法）" ;;
esac
