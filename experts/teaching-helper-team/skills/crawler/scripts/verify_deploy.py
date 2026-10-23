#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
crawler 部署自检 —— 前端闸门 + 环境总览。

纯标准库（os / shutil / subprocess / threading）、零第三方依赖；
以退出码硬判定，替代「依赖 agent 自觉执行多步 bash 文字约定」。

本技能依赖官方**腾讯 BrowserSkill 技能**提供的 `bsk` CLI 与 Chrome MV3 扩展
（本包不随附任何二进制）。

两种用法
--------
    verify_deploy.py            前端闸门：判定「现在能不能调前端采集」
    verify_deploy.py --doctor   环境总览：一条命令回答「爬虫到底能不能用」

退出码（两种模式通用）
----------------------
    0 = 就绪
    1 = BSK_MISSING：未安装官方 BrowserSkill 技能，或 bsk 不在 PATH
    2 = daemon 未运行
    3 = 扩展未连接（browsers connected = 0）
    4 = bsk 可达但执行异常 / `bsk doctor` 输出无法解析
    5 = BSK_NO_RESPONSE：bsk 无响应（超时已终止）—— 明确报错，不再挂起

非零退出一律**禁止调用前端采集**，按 stdout 提示处置后重跑本脚本。
`--json` 输出机器可读结果。运行解释器不限（本脚本零依赖）。
"""
from __future__ import annotations

import json
import os
import platform
import re
import shutil
import subprocess
import sys
import threading
from pathlib import Path

# --------------------------------------------------------------------------- #
# 路径
# --------------------------------------------------------------------------- #
WB = Path.home() / ".workbuddy"
STATUS_DIR = WB / "teaching-helper-team"
STATUS_FILE = STATUS_DIR / "setup-status.json"
VENV_PY_TXT = STATUS_DIR / "venv_python.txt"          # 单行纯文本旁路
VENV_DIR = WB / "binaries" / "python" / "envs" / "teaching-helper-team"

# 静态采集（scrape.py）所需的最小依赖集
STATIC_DEPS = ("requests", "bs4", "lxml")

BSK_TIMEOUT = 30        # bsk --version / status
DOCTOR_TIMEOUT = 45     # bsk doctor（首次可能因 bsk 自动升级而明显偏慢，故留足余量）

INSTALL_HINT = (
    "安装官方腾讯 BrowserSkill 技能即可获得 bsk：WorkBuddy → 专家中心 / 技能中心 → "
    "搜索 “BrowserSkill” → 安装（腾讯开源）；安装后 bsk 自动加入 PATH（可能需重开终端），"
    "再到 Chromium 内核浏览器「开发者模式 → 加载已解压的扩展」加载官方扩展（popup 绿色）。"
    "或让 WorkBuddy 助手按默认方式（marketplace-skill-installer）代为安装并验证。"
)

LOAD_EXT_HINT = (
    "扩展未连接。请在 Chromium 内核浏览器（Chrome / Edge / Brave）以「开发者模式 → "
    "加载已解压的扩展」加载官方 BrowserSkill 技能提供的 chrome-mv3 扩展目录，"
    "popup 显示绿色后重跑本脚本。Firefox / Safari 非 Chromium 内核，不支持。"
)

DAEMON_HINT = (
    "daemon 未运行。先执行 `bsk daemon start`；若启动失败报 bind/IPC 错误，"
    "多为陈旧 socket 残留，重跑 setup（自带自愈）或手动清理 ~/.bsk/run/daemon.sock 后重试。"
)

NO_RESPONSE_HINT = (
    "bsk 无响应（已超时终止，未挂起）。已知可复现的原因有三：\n"
    "  1. bsk 正在自动升级 —— 若 stderr 出现 “A new bsk version is available”，稍等片刻重跑本脚本即可；\n"
    "  2. daemon 处于半死状态；\n"
    "  3. bsk 正在等待浏览器扩展连接。\n"
    "处置：稍候重跑；仍无响应则先 `bsk daemon stop` 再 `bsk daemon start`；"
    "再不行则清理 ~/.bsk/run/daemon.sock 并重装官方 BrowserSkill 技能。"
)


# --------------------------------------------------------------------------- #
# 安全外部调用：超时终止整棵进程树 ⇒ 必定返回
# --------------------------------------------------------------------------- #
# 为什么不用 subprocess.run(timeout=...)：它在超时后只 kill 直接子进程；若该进程
# 又派生了子进程并持有管道读端，communicate() 会继续阻塞，表现为「一调用就卡死」
# 且看不到原因。这里显式建进程组，超时后终止整棵树，并用读线程 + 总时限兜底。
def _kill_tree(proc: "subprocess.Popen") -> None:
    """终止整棵进程树（尽力而为，不抛异常）。"""
    try:
        if platform.system() == "Windows":
            subprocess.run(
                ["taskkill", "/T", "/F", "/PID", str(proc.pid)],
                capture_output=True,
                timeout=15,
            )
        else:
            import signal as _signal

            try:
                os.killpg(os.getpgid(proc.pid), _signal.SIGKILL)
            except Exception:  # noqa: BLE001
                proc.kill()
    except Exception:  # noqa: BLE001
        try:
            proc.kill()
        except Exception:  # noqa: BLE001
            pass


def _run(cmd: list[str], timeout: int = 60) -> tuple[int, str, str, bool]:
    """安全执行外部命令；返回 (rc, stdout, stderr, timed_out)。超时终止时 rc=-9。"""
    is_win = platform.system() == "Windows"
    popen_kw: dict = {
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "stdin": subprocess.DEVNULL,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
    }
    if is_win:
        popen_kw["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    else:
        popen_kw["start_new_session"] = True

    try:
        proc = subprocess.Popen(cmd, **popen_kw)
    except Exception as e:  # noqa: BLE001
        return 127, "", f"无法启动进程: {e}", False

    out_buf: list[str] = []
    err_buf: list[str] = []

    def _pump(stream, buf: list) -> None:
        try:
            for line in stream:
                buf.append(line)
        except Exception:  # noqa: BLE001
            pass

    th_out = threading.Thread(target=_pump, args=(proc.stdout, out_buf), daemon=True)
    th_err = threading.Thread(target=_pump, args=(proc.stderr, err_buf), daemon=True)
    th_out.start()
    th_err.start()

    timed_out = False
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        _kill_tree(proc)
        # 短暂等待进程真正消亡（失败也无妨，不构成阻塞）
        try:
            proc.wait(timeout=3)
        except Exception:  # noqa: BLE001
            pass

    # 收尾策略（关键）：
    #   正常路径 → 进程已退出、管道 EOF，join 一下即可收全输出；
    #   超时路径 → **不 join、不 close 流**。进程被终止后若管道未 EOF（例如子孙进程
    #   仍持有写端），读线程会阻塞在底层 read() 并持有缓冲锁，此时 close() 会永久等待，
    #   反而制造出新的挂起。读线程是 daemon，随解释器退出回收，无需显式清理。
    if not timed_out:
        th_out.join(timeout=1.0)
        th_err.join(timeout=1.0)

    rc = proc.returncode if proc.returncode is not None else -9
    if timed_out:
        rc = -9
    return rc, "".join(out_buf), "".join(err_buf), timed_out


# --------------------------------------------------------------------------- #
# 三级解释器探测（不依赖「先有一个可用的 python 去解析 JSON」）
# --------------------------------------------------------------------------- #
def resolve_venv_python() -> tuple[str | None, str]:
    """返回 (解释器路径, 命中来源)。三级：文本旁路 → 状态文件 → venv 目录候选。"""
    # L1：单行纯文本旁路（免解析、免预置 python）
    if VENV_PY_TXT.is_file():
        try:
            for line in VENV_PY_TXT.read_text(encoding="utf-8", errors="replace").splitlines():
                if line.strip():
                    return line.strip(), "L1 venv_python.txt"
        except Exception:  # noqa: BLE001
            pass
    # L2：状态文件
    if STATUS_FILE.is_file():
        try:
            data = json.loads(STATUS_FILE.read_text(encoding="utf-8"))
            vp = (data or {}).get("venv_python")
            if vp:
                return str(vp), "L2 setup-status.json"
        except Exception:  # noqa: BLE001
            pass
    # L3：venv 目录按平台候选
    for cand in (VENV_DIR / "Scripts" / "python.exe", VENV_DIR / "bin" / "python", VENV_DIR / "bin" / "python3"):
        if cand.is_file():
            return str(cand), "L3 venv 目录"
    return None, "未找到"


def check_static_deps(venv_py: str | None) -> tuple[bool | None, str]:
    """检查静态采集最小依赖是否可导入；返回 (是否ok, 说明)。None = 无法判定。"""
    if not venv_py:
        return None, "未找到专用解释器（可能尚未初始化），无法检测"
    if not Path(venv_py).is_file():
        return False, f"解释器路径不存在：{venv_py}"
    code = "import " + ", ".join(STATIC_DEPS)
    rc, out, err, timed_out = _run([venv_py, "-c", code], timeout=30)
    if timed_out:
        return False, "依赖自检无响应（超时已终止）"
    if rc == 0:
        return True, " / ".join(STATIC_DEPS) + " 均可导入"
    detail = (err or out).strip().splitlines()
    tail = detail[-1][:200] if detail else "导入失败"
    return False, f"缺少依赖：{tail}（运行 setup.py --only crawler 补装）"


def _bsk_doctor(bsk: str) -> tuple[dict, str, bool]:
    """运行 `bsk doctor`；返回 ({检查项: 是否ok}, 原始输出, 是否超时)。"""
    rc, out, err, timed_out = _run([bsk, "doctor"], timeout=DOCTOR_TIMEOUT)
    if timed_out:
        return {}, "", True
    text = (out or "") + (err or "")
    checks: dict[str, bool] = {}
    for line in text.splitlines():
        # 行格式：`<状态>  <检查项>  <值>`；状态可为 ok / WARN / FAIL / N/A（大小写不敏感）。
        # WARN 视同「不是 ok」，以免把带警告的项误判为就绪。
        m = re.match(r"^(ok|warn|fail|n/a)\s+(.+?)\s{2,}", line, re.I)
        if m:
            checks[m.group(2).strip()] = m.group(1).lower() == "ok"
    return checks, text, False


def _locate_bsk() -> str | None:
    bsk = shutil.which("bsk")
    if bsk:
        return bsk
    local = Path.home() / ".local" / "bin" / "bsk"
    if os.access(str(local), os.X_OK):
        return str(local)
    return None


def main() -> int:
    argv = sys.argv[1:]
    as_json = "--json" in argv
    doctor_mode = "--doctor" in argv

    def emit(code: int, status: str, detail: str) -> int:
        if as_json:
            print(json.dumps({"ok": code == 0, "code": code, "status": status, "detail": detail},
                             ensure_ascii=False))
        else:
            tag = "[PASS]" if code == 0 else f"[FAIL rc={code}]"
            print(f"{tag} {status}\n{detail}")
        return code

    bsk = _locate_bsk()

    # ================= --doctor：五项环境总览 =================
    if doctor_mode:
        rows: list[tuple[str, bool | None, str]] = []

        venv_py, src = resolve_venv_python()
        rows.append(("解释器 venv_python", bool(venv_py and Path(venv_py).is_file()),
                     f"{venv_py or '(未找到)'}  [{src}]"))

        deps_ok, deps_msg = check_static_deps(venv_py)
        rows.append(("静态依赖 " + " / ".join(STATIC_DEPS), deps_ok, deps_msg))

        rows.append(("bsk 在 PATH", bool(bsk), bsk or "未找到（见下方安装引导）"))

        if not bsk:
            rows.append(("bsk daemon", False, "bsk 缺失，无法检测"))
            rows.append(("浏览器扩展", False, "bsk 缺失，无法检测"))
            fe_code, fe_status, fe_detail = 1, "BSK_MISSING", INSTALL_HINT
        else:
            checks, raw, timed_out = _bsk_doctor(bsk)
            if timed_out:
                rows.append(("bsk daemon", False, f"无响应（>{DOCTOR_TIMEOUT}s 已终止）"))
                rows.append(("浏览器扩展", False, f"无响应（>{DOCTOR_TIMEOUT}s 已终止）"))
                fe_code, fe_status, fe_detail = 5, "BSK_NO_RESPONSE", NO_RESPONSE_HINT
            else:
                d = next((v for k, v in checks.items() if "daemon running" in k), None)
                e = next((v for k, v in checks.items() if "extension connected" in k), None)
                rows.append(("bsk daemon", bool(d), "运行中" if d else "未运行"))
                rows.append(("浏览器扩展", bool(e), "已连接" if e else "未连接"))
                if d is None or e is None:
                    fe_code, fe_status, fe_detail = 4, "DOCTOR_OUTPUT_UNPARSED", \
                        "无法解析 `bsk doctor` 输出（格式可能已变更），请人工确认后重试。\n" + raw[:600]
                elif not d:
                    fe_code, fe_status, fe_detail = 2, "DAEMON_NOT_RUNNING", DAEMON_HINT
                elif not e:
                    fe_code, fe_status, fe_detail = 3, "EXTENSION_NOT_CONNECTED", LOAD_EXT_HINT
                else:
                    fe_code, fe_status, fe_detail = 0, "READY", "前端采集就绪（daemon 运行中，扩展已连接）"

        if as_json:
            print(json.dumps({
                "ok": fe_code == 0,
                "code": fe_code,
                "status": fe_status,
                "mode": "doctor",
                "checks": [{"name": n, "ok": o, "detail": d} for n, o, d in rows],
                "static_ready": bool(deps_ok),
                "frontend_ready": fe_code == 0,
                "detail": fe_detail,
            }, ensure_ascii=False, indent=2))
            return fe_code

        print("=== crawler 环境自检（--doctor）===")
        for name, ok, detail in rows:
            mark = "OK  " if ok else ("FAIL" if ok is False else "??  ")
            print(f"[{mark}] {name:<34}: {detail}")
        print("-" * 60)
        if deps_ok is True:
            print("静态采集（crawler 静态模式 scrape.py）: 可用")
        elif deps_ok is False:
            print("静态采集（crawler 静态模式 scrape.py）: 不可用 → 运行 `setup.py --only crawler`（冷启动约 1 分钟）")
        else:
            print("静态采集（crawler 静态模式 scrape.py）: 未初始化 → 运行 `setup.py --only crawler`（冷启动约 1 分钟）")
        print(f"前端采集（browser-automation）      : {'可用' if fe_code == 0 else '不可用'}")
        if fe_code != 0:
            print("-" * 60)
            print(f"[rc={fe_code} {fe_status}] {fe_detail}")
        return fe_code

    # ================= 默认：前端闸门 =================
    # 硬门 1：bsk 可达
    if not bsk:
        return emit(1, "BSK_MISSING", INSTALL_HINT)

    rc, out, err, timed_out = _run([bsk, "--version"], timeout=BSK_TIMEOUT)
    if timed_out:
        return emit(5, "BSK_NO_RESPONSE", NO_RESPONSE_HINT)
    if rc != 0:
        return emit(4, "BSK_VERSION_FAILED",
                    f"`bsk --version` 返回非零（rc={rc}）：{(err or '').strip()[:200]}")
    ver = (out or err).strip() or "ok"

    # 硬门 2/3：doctor 实测 daemon 与扩展连接（不采信任何历史部署状态字段）
    checks, raw, timed_out = _bsk_doctor(bsk)
    if timed_out:
        return emit(5, "BSK_NO_RESPONSE", NO_RESPONSE_HINT + f"\n--- bsk doctor 超时（>{DOCTOR_TIMEOUT}s）---")

    daemon_ok = next((v for k, v in checks.items() if "daemon running" in k), None)
    ext_ok = next((v for k, v in checks.items() if "extension connected" in k), None)

    if daemon_ok is False:
        return emit(2, "DAEMON_NOT_RUNNING", DAEMON_HINT + f"\n--- bsk doctor 输出（节选）---\n{raw[:600]}")
    if ext_ok is False:
        return emit(3, "EXTENSION_NOT_CONNECTED", LOAD_EXT_HINT + f"\n--- bsk doctor 输出（节选）---\n{raw[:600]}")
    if daemon_ok is None or ext_ok is None:
        # doctor 输出格式变化，无法解析 —— 保守判定为未就绪，附原始输出供人工研判
        return emit(4, "DOCTOR_OUTPUT_UNPARSED",
                    "无法解析 `bsk doctor` 输出（格式可能已变更），请人工确认后重试。\n" + raw[:800])

    return emit(0, "READY",
                f"crawler 前端就绪：bsk {ver.splitlines()[0]}，daemon 运行中，扩展已连接。可调用 browser-automation。")


if __name__ == "__main__":
    sys.exit(main())
