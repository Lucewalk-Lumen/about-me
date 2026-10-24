# 本地桥故障恢复流程（分片）

> 本文件是管家指令（`agents/ai-butler.md`）的分片。**仅当**正文的 `/` 探测未返回 200 时才需要 Read。

### 本地桥服务（管家强制自启）

**桥是管家与工作台通信的唯一通道，任何操作前必须确保桥在跑。** 触发时机：打开工作台时、用户请求分析/播报/速记回写时、自动化执行时——均在行动前先探测桥状态，未运行则自动拉起，失败则明确告知用户原因。

```bash
# 0) 包根（本专家包的安装目录，即含 bridge/ 与 assets/ 的那一层）；可用 WB_PKG_ROOT 覆盖
PKG_ROOT="${WB_PKG_ROOT:-<包根绝对路径>}"
# 1) 探测桥是否「活着且能服务」：GET / 返回 200 才算已启动
#    —— 判据必须是 / 而不是 /latest、/health：
#       · /latest 在无快照时正常返回 404，会被当成「没启动」；
#       · /health 任何占着 18765 的进程都能回 200（含指向已删除文件的旧版桥），
#         会被当成「已启动」，新桥再启即 EADDRINUSE 静默失败，用户看到 404 或旧界面。
#    关键：必须 --noproxy '*' 绕过沙箱 HTTP 代理；代理会拦截 127.0.0.1 并返回 502，导致判断错误。
CODE=$(curl --noproxy '*' -s -o /dev/null --max-time 3 -w '%{http_code}' http://127.0.0.1:18765/ 2>/dev/null)
if [ "$CODE" != "200" ]; then
  # 2) 端口被占（非 000）时先清理占用进程，避免新桥 EADDRINUSE 静默失败
  #    best-effort：沙箱环境常无 lsof，取不到 PID 也必须继续走后面的启动尝试
  if [ -n "$CODE" ] && [ "$CODE" != "000" ]; then
    # 2.1) 先识别占用者，并只保留「命令行确属本包桥」的 PID：
    #      18765 可能被其他应用占用，绝不因其占据端口就杀掉陌生进程
    PIDS=$(lsof -nP -iTCP:18765 -sTCP:LISTEN -t 2>/dev/null)
    SAFE_PIDS=""; UNKNOWN=""
    for PID in $PIDS; do
      CMD=$(ps -p "$PID" -o command= 2>/dev/null)
      case "$CMD" in
        *teacher-workbench-bridge*) SAFE_PIDS="$SAFE_PIDS $PID" ;;
        *) UNKNOWN="$UNKNOWN $PID(${CMD:-命令行不可读})" ;;
      esac
    done
    [ -n "$UNKNOWN" ] && echo "WARN: 端口 18765 被非本包进程占用：$UNKNOWN —— 已跳过，不会强杀。"
    # 2.2) 确认闸门：必须先向用户说明将终止的进程（PID + 命令行）并征得其同意，
    #      再以 WB_BRIDGE_KILL_CONFIRMED=1 重跑本段；未经确认不得 kill，更不得 kill -9 静默强杀。
    #      无人值守的自动化执行不得设置该变量（保持报错退出并告知用户）。
    if [ -n "$SAFE_PIDS" ]; then
      if [ "$WB_BRIDGE_KILL_CONFIRMED" = "1" ]; then
        kill $SAFE_PIDS 2>/dev/null || kill -9 $SAFE_PIDS 2>/dev/null || true
        sleep 1   # 给端口释放留时间，否则新桥仍会 EADDRINUSE
      else
        echo "ERROR: 端口 18765 被本包本地桥进程占用（PID:$SAFE_PIDS，命令行含 teacher-workbench-bridge）。"
        echo "       管家须先向用户说明「将终止上述 PID 的本地桥进程并重启」，取得确认后"
        echo "       再以 WB_BRIDGE_KILL_CONFIRMED=1 重新执行；未经确认不可静默跳过。"
        exit 1
      fi
    fi
    # 清理后仍不通 200：占用进程杀不掉（无权限 / 非本用户）或端口仍被占。
    # 此时启动新桥必然 EADDRINUSE 静默失败 —— 按规约明确报错，不可静默跳过。
    CODE2=$(curl --noproxy '*' -s -o /dev/null --max-time 2 -w '%{http_code}' http://127.0.0.1:18765/ 2>/dev/null)
    if [ -n "$CODE2" ] && [ "$CODE2" != "000" ]; then
      echo "ERROR: 端口 18765 被占用且无法自动清理（占用 PID: ${PIDS:-未识别，可能无 lsof}；响应码 ${CODE2}）。请手动执行 lsof -nP -iTCP:18765 -sTCP:LISTEN 查看占用进程并结束后重试。"
      exit 1
    fi
  fi
  # 3) 定位包内桥脚本：优先「包内相对路径」——本包自带 bridge/teacher-workbench-bridge.js；
  #    ~/.workbuddy 仅作兜底位置。顺序不可颠倒：
  #    只查 ~/.workbuddy 会在本包未安装到该目录时必然失败，导致读快照/播报/速记全部连带失效。
  SCRIPT="$PKG_ROOT/bridge/teacher-workbench-bridge.js"
  [ -f "$SCRIPT" ] || SCRIPT=$(find "$PKG_ROOT" -name teacher-workbench-bridge.js -type f 2>/dev/null | head -1)
  [ -n "$SCRIPT" ] || SCRIPT=$(find ~/.workbuddy -name teacher-workbench-bridge.js -type f 2>/dev/null | head -1)
  # 4) 桥脚本为包内唯一实现（bridge/teacher-workbench-bridge.js），缺失即报错
  if [ -z "$SCRIPT" ] || [ ! -f "$SCRIPT" ]; then
    echo "ERROR: 未找到 bridge/teacher-workbench-bridge.js（已查：${PKG_ROOT}/bridge/、~/.workbuddy）。"
    echo "       请确认 Teacher Workbench 完整安装，或设置 WB_PKG_ROOT=<包根> 后重试。"
    exit 1
  fi
  # 5) 自动发现 Node（WorkBuddy 托管 > 系统 PATH）
  NODE=$(find ~/.workbuddy -name node -type f 2>/dev/null | head -1)
  [ -z "$NODE" ] && NODE=$(command -v node 2>/dev/null)
  if [ -z "$NODE" ]; then
    echo "ERROR: Node.js 未找到（WorkBuddy 托管运行时和系统 PATH 均未检测到）"
    exit 1
  fi
  # 6) 后台启动（必须非阻塞：桥是长驻进程，前台运行会把本次会话挂起到超时）
  #    nohup + & + 输出重定向，启动后立刻返回，由下面的轮询确认是否真的起来了
  #    日志落在系统临时目录（POSIX $TMPDIR，Windows %TEMP%；等价于 Node 的 os.tmpdir()），不硬编码 /tmp
  LOG_FILE="${TMPDIR:-${TEMP:-/tmp}}/teacher-workbench-bridge.log"
  nohup "$NODE" "$SCRIPT" >"$LOG_FILE" 2>&1 &
  # 7) 最多等 5 秒确认桥可用（仍按 GET / 判据），超时即明确报错，不可静默跳过
  for i in 1 2 3 4 5 6 7 8 9 10; do
    CODE=$(curl --noproxy '*' -s -o /dev/null --max-time 1 -w '%{http_code}' http://127.0.0.1:18765/ 2>/dev/null)
    [ "$CODE" = "200" ] && break
    sleep 0.5
  done
  if [ "$CODE" != "200" ]; then
    echo "ERROR: 本地桥已尝试启动但探测未通过（末次响应码 ${CODE:-000}）。请查看日志：${LOG_FILE}"
    exit 1
  fi
fi
```

> 桥在首次打开工作台时即拉起，后续按需保持；若探测失败（端口不可达、Node 不可用、脚本缺失）**必须告知用户失败原因**，不可静默跳过——没有桥就没有管家 ⇄ 工作台的连接。
>
> **两条不得绕过的保护**：① 端口占用时只终止「命令行含 `teacher-workbench-bridge`」的进程，且须先向用户说明 PID 与命令行、征得确认后再执行（非本包进程一律不杀，仅报警）；② 桥脚本发现以**包内路径优先**（`bridge/teacher-workbench-bridge.js`），`~/.workbuddy` 仅为兜底。
>
> **平台说明**：上述自启脚本为 POSIX shell（依赖 `curl` / `lsof` / `ps` / `kill` / `nohup` / `uname`），macOS / Linux 可直接运行；**Windows 需在 WSL / Git-Bash 等 POSIX 兼容环境下运行**，或由用户手动启动 `node bridge/teacher-workbench-bridge.js`（桥自身仍是跨平台零依赖 Node 脚本）。不得向 Windows 用户承诺「双击即可自动拉起桥」。
