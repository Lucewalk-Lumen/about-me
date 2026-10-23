#!/usr/bin/env bash
# OKR 任务管理工具（hrm-advisory-corps）
#
# 存储：每行一条，制表符分隔 ——  status<TAB>priority<TAB>remind<TAB>created<TAB>text
#   status   : todo | done
#   priority : low | medium | high
#   remind   : YYYY-MM-DD 或 "-"（无提醒）
#   created  : YYYY-MM-DD
#   text     : 条目正文（不含制表符）
# 数据目录默认为用户可写位置（${OKR_TRACKER_DIR:-$HOME/hrm-advisory-corps/okr-data}），
# 绝不写入插件安装目录；目录惰性创建，仅写入类子命令才会建目录。
# 回退链（HOME 缺失时）：XDG_CACHE_HOME > 系统临时目录（末位兜底）。
set -euo pipefail

VERSION="1.0.0"
APP_NAME="hrm-advisory-corps"
DATA_DIR="${OKR_TRACKER_DIR:-${HOME:-${XDG_CACHE_HOME:-${TMPDIR:-/tmp}}}/$APP_NAME/okr-data}"
DB="$DATA_DIR/data.log"
HISTORY="$DATA_DIR/history.log"

# ---------- helpers ----------

# 惰性创建数据目录；失败时给出清晰 [ERR] 并退出（不抛裸 bash 错误）。
ensure_data_dir() {
    if [ -d "$DATA_DIR" ]; then
        if [ ! -w "$DATA_DIR" ]; then
            echo "[ERR] 数据目录不可写: $DATA_DIR（可用 OKR_TRACKER_DIR 指定可写目录）" >&2
            exit 1
        fi
        return 0
    fi
    if ! mkdir -p "$DATA_DIR" 2>/dev/null; then
        echo "[ERR] 无法创建数据目录: $DATA_DIR（可用 OKR_TRACKER_DIR 指定可写目录）" >&2
        exit 1
    fi
}

# 记录一条写入类操作到 history.log（仅写入类子命令调用）。
_record() {
    printf '%s\t%s\t%s\n' "$(date '+%Y-%m-%dT%H:%M:%S')" "$1" "${2:-}" >> "$HISTORY"
}

# 读取 DB 第 $1 行的第 $2 个字段（无 DB 时为空）。
_field() {
    [ -f "$DB" ] || return 0
    awk -v n="$1" -v f="$2" -F'\t' 'NR==n{print $f; exit}' "$DB"
}

# 取条目总数（无 DB 记 0）。
_total() {
    [ -f "$DB" ] && wc -l < "$DB" | tr -d ' ' || echo 0
}

# 校验条目编号并在 [1,total] 内；失败打印 [ERR] 并返回 1。$1=子命令 $2=编号
_require_index() {
    local cmd="$1" idx="$2" total
    if [ -z "$idx" ]; then
        echo "[ERR] $cmd: 缺少条目编号" >&2
        return 1
    fi
    if ! [[ "$idx" =~ ^[0-9]+$ ]] || [ "$idx" -lt 1 ]; then
        echo "[ERR] $cmd: 条目编号必须为正整数，收到: $idx" >&2
        return 1
    fi
    if [ ! -f "$DB" ]; then
        echo "[ERR] $cmd: 当前无任何条目" >&2
        return 1
    fi
    total=$(_total)
    if [ "$idx" -gt "$total" ]; then
        echo "[ERR] $cmd: 条目编号越界（有效范围 1-$total），收到: $idx" >&2
        return 1
    fi
}

# 原子改写 DB 第 $1 行的第 $2 个字段为 $3（临时文件 + mv）。
_rewrite_field() {
    local n="$1" f="$2" v="$3" tmp="$DB.tmp.$$"
    awk -v n="$n" -v f="$f" -v v="$v" -F'\t' -v OFS='\t' 'NR==n{$f=v} {print}' "$DB" > "$tmp" && mv "$tmp" "$DB"
}

# 校验 YYYY-MM-DD 日期（真实解析：格式 + 月/日实际天数，拒绝 2026-02-30 等非法日期）。
_valid_date() {
    local d="$1"
    # 纯格式/范围快筛（拒绝 0000-00-00 等）
    [[ "$d" =~ ^[0-9]{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])$ ]] || return 1
    # 真实解析：能被 date 解析回同一日期才算合法（跨平台：BSD date 优先，回退 GNU date）
    if date -j -f "%Y-%m-%d" "$d" "+%Y-%m-%d" >/dev/null 2>&1; then
        [ "$(date -j -f "%Y-%m-%d" "$d" "+%Y-%m-%d")" = "$d" ]
    else
        [ "$(date -d "$d" "+%Y-%m-%d" 2>/dev/null)" = "$d" ]
    fi
}

# YYYY-MM-DD + N 天（跨平台：BSD date 优先，回退 GNU date）。
_iso_add_days() {
    local d="$1" n="$2"
    if date -j -f "%Y-%m-%d" "$d" "+%Y-%m-%d" >/dev/null 2>&1; then
        date -j -v"+${n}d" -f "%Y-%m-%d" "$d" "+%Y-%m-%d"
    else
        date -d "$d +$n days" "+%Y-%m-%d"
    fi
}

# ---------- subcommands ----------

cmd_add() {
    if [ "$#" -lt 1 ] || [ -z "${1:-}" ]; then
        echo "[ERR] add: 缺少条目内容" >&2
        return 1
    fi
    ensure_data_dir
    local text="$*"
    # 制表符会破坏 TSV 列结构（以及 history.log 的字段分列），统一替换为空格
    text="${text//$'\t'/ }"
    printf 'todo\tmedium\t-\t%s\t%s\n' "$(date +%F)" "$text" >> "$DB"
    echo "  已添加 #$( _total )：$text"
    _record add "$text"
}

cmd_list() {
    if [ ! -f "$DB" ]; then
        echo "  (empty)"
        return 0
    fi
    awk -F'\t' '$1!="done"{n++; printf "  #%d [ ] 优先级:%-6s 提醒:%-10s 创建:%s  %s\n", n, $2, $3, $4, $5}
                $1=="done"{n++}' "$DB"
    return 0
}

cmd_done() {
    local idx="${1:-}"
    _require_index done "$idx" || return 1
    if [ "$(_field "$idx" 1)" = "done" ]; then
        echo "  (#$idx 已是完成状态)"
        return 0
    fi
    local text; text="$(_field "$idx" 5)"
    _rewrite_field "$idx" 1 done
    echo "  已完成 #${idx}：$text"
    _record done "$idx"
}

cmd_priority() {
    local idx="${1:-}" level="${2:-}"
    _require_index priority "$idx" || return 1
    if [ -z "$level" ]; then
        echo "[ERR] priority: 缺少优先级（low|medium|high）" >&2
        return 1
    fi
    case "$level" in
        low|medium|high) ;;
        *) echo "[ERR] priority: 优先级必须是 low|medium|high，收到: $level" >&2; return 1 ;;
    esac
    _rewrite_field "$idx" 2 "$level"
    echo "  #$idx 优先级 -> $level"
    _record priority "$idx=$level"
}

cmd_remind() {
    local idx="${1:-}" when="${2:-}"
    _require_index remind "$idx" || return 1
    if [ -z "$when" ]; then
        echo "[ERR] remind: 缺少提醒日期（YYYY-MM-DD）" >&2
        return 1
    fi
    if ! _valid_date "$when"; then
        echo "[ERR] remind: 日期不存在或非法（应为 YYYY-MM-DD），收到: $when" >&2
        return 1
    fi
    _rewrite_field "$idx" 3 "$when"
    echo "  #$idx 提醒日 -> $when"
    _record remind "$idx=$when"
}

cmd_today() {
    if [ ! -f "$DB" ]; then echo "  (empty)"; return 0; fi
    local today; today="$(date +%F)"
    awk -v t="$today" -F'\t' '$1!="done" && $3==t{printf "  #%d [ ] 优先级:%s 提醒:%s  %s\n", NR, $2, $3, $5}' "$DB"
    return 0
}

cmd_week() {
    if [ ! -f "$DB" ]; then echo "  (empty)"; return 0; fi
    local today end; today="$(date +%F)"; end="$(_iso_add_days "$today" 6)"
    echo "  本周（$today ~ $end）："
    awk -v t="$today" -v e="$end" -F'\t' '$1!="done" && $3!="-" && $3>=t && $3<=e{printf "  #%d [ ] 优先级:%s 提醒:%s  %s\n", NR, $2, $3, $5}' "$DB"
    return 0
}

cmd_stats() {
    if [ ! -f "$DB" ]; then
        echo "  总计: 0  未完成: 0  已完成: 0  含提醒: 0  已逾期: 0"
        return 0
    fi
    local today; today="$(date +%F)"
    awk -v t="$today" -F'\t' '
        {total++}
        $1=="done"{done++}
        $1!="done"{todo++; if($3!="-"){remind++; if($3<t) overdue++}}
        END{printf "  总计: %d  未完成: %d  已完成: %d  含提醒: %d  已逾期: %d\n", total, todo, done, remind, overdue}
    ' "$DB"
    return 0
}

cmd_clear() {
    ensure_data_dir
    if [ ! -f "$DB" ]; then echo "  (无条目)"; return 0; fi
    local before after tmp; before="$(_total)"; tmp="$DB.tmp.$$"
    awk -F'\t' '$1!="done"{print}' "$DB" > "$tmp" && mv "$tmp" "$DB"
    after="$(_total)"
    echo "  已清理 $((before - after)) 条已完成条目（剩余 $after 条，编号已重排）"
    _record clear "$((before - after))"
}

cmd_export() {
    if [ ! -f "$DB" ]; then echo "No data"; return 0; fi
    cat "$DB"
    return 0
}

show_help() {
    cat <<EOF
okr-tracker v$VERSION

OKR 任务管理工具

Usage: okr-tracker <command> [args]

Commands:
  add <text>                       添加一条待办
  list                             列出未完成条目
  done <n>                         将第 n 条标记为完成
  priority <n> <low|medium|high>   设置第 n 条优先级
  remind <n> <YYYY-MM-DD>          设置第 n 条提醒日
  today                            今日提醒
  week                             未来 7 天提醒
  stats                            统计
  clear                            清理已完成条目并重排编号
  export                           导出全部条目（制表符分隔）
  help                             显示本帮助
  version                          显示版本

Data: \$DATA_DIR
EOF
}

case "${1:-help}" in
    add) shift; cmd_add "$@" ;;
    list) shift; cmd_list "$@" ;;
    done) shift; cmd_done "$@" ;;
    priority) shift; cmd_priority "$@" ;;
    remind) shift; cmd_remind "$@" ;;
    today) shift; cmd_today "$@" ;;
    week) shift; cmd_week "$@" ;;
    stats) shift; cmd_stats "$@" ;;
    clear) shift; cmd_clear "$@" ;;
    export) shift; cmd_export "$@" ;;
    help|-h|--help) show_help ;;
    version|-v|--version) echo "okr-tracker v$VERSION" ;;
    *) echo "[ERR] 未知子命令: ${1:-}" >&2; show_help; exit 1 ;;
esac
