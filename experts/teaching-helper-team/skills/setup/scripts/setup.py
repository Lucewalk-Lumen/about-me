#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
教学帮帮团（Teaching Helper Team）一键初始化脚本  —  skills/setup/scripts/setup.py

目的
----
让专家包「装完开箱即用」：把原本分散在 7 个技能里、需要用户首次使用时
手动安装的外部运行时依赖，在安装/首次会话阶段一次性初始化好。

覆盖的依赖（与 skills/*/SKILL.md 的「依赖安装」节一一对应）
-----------------------------------------------------------
  - crawler (静态采集)     : requests + beautifulsoup4 + lxml
  - text-to-speech         : edge-tts
  - case-writer   : python-docx
  - thesis-mentor          : matplotlib / seaborn / numpy / scipy （可选出图）
  - minutes-organizer        : rapidocr-onnxruntime / onnxruntime / opencv-python / pillow-heif（+ Node `docx`）
  - crawler (前端采集)     : 依赖官方**腾讯 BrowserSkill 技能**提供的 `bsk` CLI 与 Chrome MV3 扩展（本包**不再随附**任何二进制；由 WorkBuddy 技能中心/市场安装 BrowserSkill 后自动获得 `bsk`）。setup 仅做可达性检测 + 缺失时自动软链修复 / 给出一键安装引导；首次使用浏览器自动化前需在该技能内加载官方扩展（popup 显示绿色）。
  - content-summary        : 仅生成 .env 凭证占位模板（密钥由用户自填，绝不硬编码）

设计原则（与团队约束一致）
--------------------------
  - 依赖隔离：一律装进 WorkBuddy 托管 venv，禁止裸 pip install 到全局 Python。
  - 零密钥硬编码：API key 只生成「占位模板」，真实值由用户自行填写。
  - 失败不阻塞：单步失败汇总后继续，退出码反映整体状态（0=全成功 / 1=部分 / 2=环境不支持）。
  - 跨平台：macOS·Linux 用 <venv>/bin/python，Windows 用 <venv>\\Scripts\\python.exe。
  - 幂等：venv 已存在**且通过功能校验**才复用；不可用的半成品 venv 会被移开（`.broken-*`）并重建。
  - 渐进式状态：**进程一起来就先写一次状态**（`stage=starting`），venv 就绪后再写一次
    （`stage=venv_ready`，含 venv_python），此后**每完成一组立即刷新**；
    任何时刻中断都留下可用状态，下次会话能判「已装哪些 / 还差哪些」，不必全量重来。
  - 可分批 / 可续装：`--only <组>` 只装指定组；默认跳过已完成组（等效 `--resume`）；
    `--minimal` 等价 `--only crawler`（静态爬虫最小可用集，冷启动约 1 分钟）。

常用命令
--------
    setup.py                            # 幂等全量：只装缺的组，已完成的跳过
    setup.py --minimal                  # 只装 crawler 组（静态爬虫，冷启动约 1 分钟）
    setup.py --only crawler,ppt-maker   # 只装指定组
    setup.py --only crawler --force     # 忽略已完成状态，强制重装
    setup.py --json                     # 机器可读输出

状态文件（供主理人判断是否已初始化）
------------------------------------
    ~/.workbuddy/teaching-helper-team/setup-status.json   # 完整状态（含 groups 进度）
    ~/.workbuddy/teaching-helper-team/venv_python.txt     # 单行纯文本 = 解释器绝对路径
    后者是为「取解释器」这一步准备的**免解析旁路**：直接读文件即可，无需先有 python 解析 JSON。

注意：本脚本仅依赖 Python 标准库，可在「尚未安装任何依赖」的裸环境下直接运行。
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import time
from pathlib import Path

# --------------------------------------------------------------------------- #
# 路径探测
# --------------------------------------------------------------------------- #
HOME = Path.home()
WB = HOME / ".workbuddy"

# 专用 venv（与 default 隔离，避免和其他包混用）
VENV_DIR = WB / "binaries" / "python" / "envs" / "teaching-helper-team"
# 持久化状态（用户级，不被包更新覆盖）
STATUS_DIR = WB / "teaching-helper-team"
STATUS_FILE = STATUS_DIR / "setup-status.json"
# 免解析旁路：单行纯文本 = 解释器绝对路径。
# 存在的意义：读取解释器这一步**不应**再依赖「先有一个可用的 python 来解析 JSON」，
# 否则会退化成循环依赖（没有 venv → 取不到 venv_python → 不能用 python 去取）。
# 任何 agent / 脚本直接读这个文件的首行即可拿到解释器路径，无需 JSON 解析、无需预置 python。
VENV_PY_TXT = STATUS_DIR / "venv_python.txt"
# 状态文件的自述说明（写进 setup-status.json 的 note 字段）
STATUS_NOTE = "本文件由 setup 生成，供主理人判断是否已初始化；删掉即可触发重新初始化。"

# 静默模式：`--json` 时置 True，避免非结构化提示混进 JSON 输出流。
STATUS_QUIET = False

# 包根：scripts/setup.py -> <skills/setup/scripts> -> <skills/setup> -> <skills> -> <包根>（parents[3]）
PKG_ROOT = Path(__file__).resolve().parents[3]

# bsk 由官方腾讯 BrowserSkill 技能提供（本包不再随附任何二进制）。
# setup 仅检测 bsk 是否可达；若已从官方技能获得但未进 PATH，则自动软链到 ~/.local/bin。
BSK_LINK_DIR = HOME / ".local" / "bin"


def find_managed_python() -> str | None:
    """优先 WorkBuddy 托管 Python，否则使用系统 python3。

    跨平台说明：WorkBuddy 托管运行时在 Windows 上的布局为
    ``<versions>/<ver>/python.exe``（无 ``bin/`` 子目录），POSIX 上为
    ``<versions>/<ver>/bin/python3``。历史缺陷是只探测 POSIX 布局，导致
    Windows 上探测失败并回退到 PATH —— 而 PATH 上的 ``python3``/``python``
    往往是微软应用商店的 App-Execution-Alias 桩（执行返回 9009），
    最终在创建 venv 阶段 FATAL 退出，整个初始化不可用。
    """
    ver_dir = WB / "binaries" / "python" / "versions"
    if ver_dir.is_dir():
        versions = sorted(
            [v for v in ver_dir.glob("*") if v.is_dir()],
            key=lambda p: p.name,
            reverse=True,
        )
        for v in versions:
            for cand in (v / "python.exe", v / "bin" / "python3", v / "bin" / "python"):
                if cand.is_file():
                    return str(cand)
    # 回退系统解释器：排除 Windows 应用商店的 App-Execution-Alias 桩（rc=9009，无法创建 venv）
    for name in ("python3", "python"):
        exe = shutil.which(name)
        if exe and "WindowsApps" not in exe:
            return exe
    return None


def venv_python() -> Path:
    if platform.system() == "Windows":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


# --------------------------------------------------------------------------- #
# 依赖清单（按技能分组，与 SKILL.md 对齐）
# --------------------------------------------------------------------------- #
PY_DEPS: dict[str, list[str]] = {
    # 依赖全部加锁上下界（与包根 requirements.lock 对齐），杜绝未声明上界导致的静默大版本升级回归。
    "crawler": ["requests>=2.32.0,<3.0.0", "beautifulsoup4>=4.12,<5.0.0", "lxml>=6.1.0,<7.0.0"],  # CVE 修复线对齐（抬升主版本至 6.x）
    "text-to-speech": ["edge-tts>=6.0.0,<8.0.0"],  # 上界取 <8.0.0 以匹配 PyPI 现行版本线（6.x/7.x）；上界过窄将导致无匹配版本可装
    # 以下办公类依赖为离线生成路径用途：平台自带办公技能（tencent-pptx / tencent-docx）可用时无需安装，
    # 安装失败不阻断整体初始化（见 install_py_deps 的 optional 处理）。
    "case-writer": ["python-docx>=1.1.2,<2.0.0"],
    "ppt-maker": ["python-pptx>=0.6.23,<1.0.0", "pymupdf>=1.23.0,<2.0.0"],  # 传统 .pptx 生成（build_pptx.py）+ PPT/PDF 转换抽取（extract_pptx.py / extract_pdf.py）
    # thesis-mentor 运行时零必需依赖；图表库（matplotlib/seaborn/numpy/scipy）为可选，
    # 未装时 chart_engine.py 优雅退出，故不在此必装。
    "material-extractor": ["pypdf>=6.0.0,<7.0.0", "pdfminer.six>=20221105,<20270101", "ebooklib>=0.18,<1.0.0", "beautifulsoup4>=4.12,<5.0.0", "python-docx>=1.1.2,<2.0.0", "striprtf>=0.0.20,<0.1.0"],  # 注：pdfminer.six 采用日历化版本号（20260107）
    "minutes-organizer": [
        "rapidocr-onnxruntime>=1.1.0,<2.0.0",  # 下界取 >=1.1.0 以匹配 PyPI 现行线（1.1.x/1.2.x）；下界过紧将导致无匹配版本可装
        "onnxruntime>=1.18.0,<2.0.0",
        "opencv-python>=4.9.0,<5.0.0",
        "pillow-heif>=0.16.0,<1.0.0",
    ],
}

# --------------------------------------------------------------------------- #
# 组与执行顺序
# 顺序即执行顺序 —— crawler 放最前：用户最常需要、依赖最少、最快见效（冷启动约 1 分钟）。
# --------------------------------------------------------------------------- #
GROUP_ORDER: list[str] = [
    "crawler",
    "text-to-speech",
    "case-writer",
    "ppt-maker",
    "material-extractor",
    "minutes-organizer",   # 含 Node `docx`（pip 包装完后接续装 node 包）
    "browser",             # bsk 可达性检测（非 pip）
    "env",                 # content-summary 凭证模板（非 pip）
    "selfcheck",           # deai 自检（非 pip）
]

# 非 pip 组：不参与依赖安装，但可被 --only 选中；默认全量时总是执行（都很轻量）
NON_PIP_GROUPS: tuple[str, ...] = ("browser", "env", "selfcheck")

# --minimal 的语义 = 静态爬虫最小可用集
MINIMAL_GROUPS: list[str] = ["crawler"]

# content-summary 凭证占位（仅占位，不写真实值）
ENV_TEMPLATE: dict[str, str] = {
    "OPENAI_API_KEY": "",
    "ANTHROPIC_API_KEY": "",
    "XAI_API_KEY": "",
    "GEMINI_API_KEY": "",
    "GOOGLE_GENERATIVE_AI_API_KEY": "",
    "GOOGLE_API_KEY": "",
    "FIRECRAWL_API_KEY": "",
    "APIFY_API_TOKEN": "",
}


# --------------------------------------------------------------------------- #
# 安全外部调用
# --------------------------------------------------------------------------- #
# 问题：某些外部命令（如浏览器自动化 CLI）在异常状态下会长时间不返回。若直接用
# `subprocess.run(..., capture_output=True, timeout=N)`，超时只 kill 直接子进程；
# 一旦该进程又派生了子进程并持有管道读端，`communicate()` 仍会继续阻塞，表现为
# 「一调用就卡住」且看不到原因。safe_run 的处置：
#   1) 独立进程组（Windows CREATE_NEW_PROCESS_GROUP / POSIX start_new_session）；
#   2) 超时后终止整棵进程树（Windows taskkill /T /F；POSIX killpg）；
#   3) 输出用读线程 + 总时限兜底 ⇒ 必定在 timeout 附近返回。
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


def safe_run(cmd: list[str], timeout: int = 60) -> tuple[int, str, str, bool]:
    """安全调起外部命令，**必定在 timeout 附近返回**。

    返回 ``(rc, stdout, stderr, timed_out)``；超时被终止时 rc = -9 且 timed_out=True。
    """
    import threading

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
# 安装动作
# --------------------------------------------------------------------------- #
def _venv_is_usable(vp: Path) -> tuple[bool, str]:
    """venv **功能级**可用性校验（不是"文件在不在"）。

    为什么不能只判文件存在：
        `venv` 创建过程被中断时，`Scripts/python.exe` 往往**已经生成**，但 `pip`
        / `site-packages` 尚未就绪。只判 `vp.is_file()` 会**复用这个半成品**，
        ⇒ 之后**每一组**依赖安装都必然失败，而且用户没有任何自愈入口
        （`--force` 只管"组"，不管 venv）——使初始化一旦中断就难以恢复。

    判据：解释器可执行 + pip 可用。两项都过才算可用。
    """
    if not vp.is_file():
        return False, "解释器不存在"
    for args, label in (
        ([str(vp), "-c", "import sys; sys.exit(0 if sys.prefix else 1)"], "解释器可执行"),
        ([str(vp), "-m", "pip", "--version"], "pip 可用"),
    ):
        try:
            r = subprocess.run(args, capture_output=True, text=True, timeout=120)
        except Exception as e:  # noqa: BLE001
            return False, f"{label} 检查异常: {e}"
        if r.returncode != 0:
            return False, f"{label} 失败: {(r.stderr or r.stdout)[-200:].strip()}"
    return True, "ok"


def ensure_venv(managed_py: str) -> Path:
    """确保 venv 可用；**不可用则移开重建**（移开而非删除，可还原、可审计）。"""
    vp = venv_python()
    ok, why = _venv_is_usable(vp)
    if ok:
        return vp

    had_dir = VENV_DIR.exists()
    if had_dir:
        stamp = time.strftime("%Y%m%d-%H%M%S")
        broken = VENV_DIR.with_name(f"{VENV_DIR.name}.broken-{stamp}")
        n = 1
        while broken.exists():
            broken = VENV_DIR.with_name(f"{VENV_DIR.name}.broken-{stamp}-{n}")
            n += 1
        try:
            os.replace(str(VENV_DIR), str(broken))
            note = (f"检测到不可用的 venv（{why}），已移开为 {broken.name} 并重建"
                    f"（确认无误后可手动删除该 .broken-* 目录）")
        except OSError:
            # 跨卷 / 占用等情况下退化为就地清理：这里清的是**本工具自己创建的损坏 venv**，
            # 不是用户数据；且上面已尽力尝试可还原的移开路径。
            shutil.rmtree(str(VENV_DIR), ignore_errors=True)
            note = f"检测到不可用的 venv（{why}），移开失败，已就地清理并重建"
        if not STATUS_QUIET:
            print(f"[setup] {note}")

    subprocess.run([managed_py, "-m", "venv", str(VENV_DIR)], check=True)
    vp2 = venv_python()
    ok2, why2 = _venv_is_usable(vp2)
    if not ok2:
        raise RuntimeError(f"venv 重建后仍不可用: {why2}")
    return vp2


def pip_install(vp: Path, packages: list[str], timeout: int = 600, retries: int = 2) -> list[dict]:
    """pip 安装（支持失败重试 2 次 + 超时镜像提示）。"""
    results: list[dict] = []
    for pkg in packages:
        last_detail = "unknown"
        ok = False
        for attempt in range(retries + 1):
            try:
                r = subprocess.run(
                    [str(vp), "-m", "pip", "install", "--no-cache-dir", pkg],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )
                ok = r.returncode == 0
                last_detail = "installed" if ok else (r.stderr or r.stdout)[-400:].strip()
                if ok:
                    break
            except subprocess.TimeoutExpired:
                last_detail = f"安装超时（>{timeout}s），请检查网络后重试"
            except Exception as e:  # noqa: BLE001
                last_detail = str(e)[:400]
            if not ok and attempt < retries:
                last_detail += f"（第{attempt+1}次失败，重试中…）"
        if not ok and "超时" in last_detail:
            last_detail += "；如持续失败可加镜像: pip install --index-url https://pypi.tuna.tsinghua.edu.cn/simple"
        results.append({"pkg": pkg, "ok": ok, "detail": last_detail})
    return results


def install_node_docx() -> dict:
    npm = shutil.which("npm")
    if not npm:
        return {"ok": False, "detail": "未找到 npm，跳过 Node `docx` 安装（会议纪要 Word 输出将不可用）"}
    try:
        # 优先安装到 WorkBuddy 托管 node workspace（环境隔离，不污染用户全局 node 环境）
        wb_nm = WB / "binaries" / "node" / "workspace"
        last_detail = f"未找到托管 node workspace 目录 {wb_nm}"
        if wb_nm.is_dir():
            r2 = subprocess.run(
                [npm, "install", "docx", "--prefix", str(wb_nm)],
                capture_output=True,
                text=True,
                timeout=600,
            )
            if r2.returncode == 0:
                return {"ok": True, "detail": f"已安装 docx 到 {wb_nm / 'node_modules'}"}
            last_detail = (r2.stderr or "")[-400:].strip()
        # 仅在托管 workspace 不可用 / 安装失败时，才回退到全局安装（会污染全局 node 环境）
        r = subprocess.run(
            [npm, "install", "-g", "docx"],
            capture_output=True,
            text=True,
            timeout=600,
        )
        if r.returncode == 0:
            return {"ok": True, "detail": "已使用全局安装，可能污染全局 node 环境"}
        return {"ok": False, "detail": ((r.stderr or "") or last_detail)[-400:].strip()}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "detail": str(e)[:400]}


def _locate_bsk_on_disk() -> Path | None:
    """在常见位置查找已存在的 bsk 二进制（来自官方 BrowserSkill 技能或手动安装）。

    返回首个命中的绝对路径；找不到返回 None。本函数**不**下载任何内容，
    仅用于在「技能已装但 bsk 未进 PATH」时自动建立软链修复。
    """
    candidates = [
        HOME / ".local" / "bin" / "bsk",
        Path("/usr/local/bin/bsk"),
        Path("/opt/homebrew/bin/bsk"),
        Path("/usr/bin/bsk"),
        WB / "binaries" / "browser-skill" / "bsk",
    ]
    # 扫描 WorkBuddy 技能目录下可能随 BrowserSkill 技能落地的 bsk
    skills_root = WB / "skills"
    if skills_root.is_dir():
        for hit in skills_root.glob("**/bsk"):
            candidates.append(hit)
        for hit in skills_root.glob("**/bsk.exe"):
            candidates.append(hit)
    for c in candidates:
        if c.is_file() and os.access(str(c), os.X_OK):
            return c
    return None


def _bsk_version(bsk_path: str, timeout: int = 20) -> str:
    """返回 `bsk --version` 输出摘要；超时 / 失败返回可读的 unknown 说明。

    走 safe_run，因此必定返回，不会挂起。
    """
    rc, out, err, timed_out = safe_run([bsk_path, "--version"], timeout=timeout)
    if timed_out:
        return f"unknown（`bsk --version` 无响应 >{timeout}s）"
    if rc == 0:
        return (out or err).strip() or "unknown"
    return "unknown"


# --------------------------------------------------------------------------- #
# bsk 可达性保障（本包不再随附 bsk 二进制）
# --------------------------------------------------------------------------- #
# bsk 由官方腾讯 BrowserSkill 技能（WorkBuddy 技能中心/市场安装）提供，跨平台自带，
# 安装后自动进入 PATH。本脚本只做可达性检测：若磁盘已有 bsk 但未进 PATH 则自动软链修复，
# 若全盘缺失则给出精确安装引导（见 install_browser_skill）。不再做二进制 SHA256 比对
# 与 quarantine 解除——这些由官方技能的安装/自更新与签名保证。


def _bsk_daemon_selfheal(bsk_bin: str) -> str:
    """daemon 启动失败后的陈旧残留自愈（仅在确认无活 daemon 时执行）。

    daemon 被强制终止或异常退出后，会在 ~/.bsk/run/daemon.sock
    留下陈旧 socket 与 daemon.json.tmp.*，导致此后 `bsk daemon start` 一律报
    "bind IPC endpoint ... already exists" 而失败，前端浏览器自动化 100% 不可用，
    且症状与「扩展未加载」极为相似、极易误判。清理残留后重启即恢复。
    安全闸：先 `bsk status` 确认无活 daemon 才清理，绝不误杀运行中的实例。
    """
    home = HOME / ".bsk"
    sock = home / "run" / "daemon.sock"
    lock = home / "daemon.lock"
    stale = [p for p in (sock, lock, *home.glob("daemon.json.tmp.*")) if p.exists()]
    if not stale:
        return "无残留需清理"
    # `bsk status` 在异常 daemon 下可能长时间不返回，故走 safe_run 并加超时
    rc_status, _, _, timed_out = safe_run([bsk_bin, "status"], timeout=15)
    if timed_out:
        # 状态未知 ⇒ 保守不动：宁可留残留，也不误杀可能正在运行的 daemon
        return "`bsk status` 无响应（>15s），状态未知 → 跳过残留清理以避免误伤活 daemon"
    alive = rc_status == 0
    if alive:
        return "daemon 已在运行，跳过残留清理"
    cleaned = []
    for p in stale:
        try:
            p.unlink(missing_ok=True)
            cleaned.append(p.name)
        except OSError:
            pass
    return "已清理：" + ", ".join(cleaned) if cleaned else "残留清理失败（权限不足）"


def install_browser_skill(start_daemon: bool = False) -> dict:
    """确保官方腾讯 BrowserSkill 技能提供的 bsk 可达（本包不再随附任何二进制）。

    移除随包内置 bsk，改为依赖官方 BrowserSkill 技能（WorkBuddy 技能中心/市场
    安装，跨平台自带 bsk CLI 与 Chrome MV3 扩展）。本函数只做可达性保障：
      - bsk 已在 PATH → 返回 ok，并提示在浏览器加载官方扩展、可手动 `bsk daemon start`；
      - 磁盘某处已有 bsk 但未进 PATH → 自动软链到 ~/.local/bin/bsk 并复检（一键修复常见情形）；
      - 全盘无 bsk → 返回 ok=False，给出精确安装引导（用户可在 WorkBuddy 技能中心自行安装，或让 WorkBuddy 助手按默认方式代为安装）。
    单步失败仅记 WARN，不阻塞其余技能（仅 crawler 前端浏览器自动化依赖该技能）。

    start_daemon：bsk 已就位时是否顺带 `bsk daemon start`（默认不启动，由用户手动）。
    """
    # 1) PATH 直接命中
    existing = shutil.which("bsk")
    if existing:
        ver = _bsk_version(existing)
        daemon_note = ""
        if start_daemon:
            # 走 safe_run：超时终止整棵进程树并返回 rc=-9，而不是无限等待
            rc1, _, _, to1 = safe_run([existing, "daemon", "start"], timeout=60)
            if to1:
                daemon_note = "；daemon start: 无响应（>60s，已终止；bsk 可能在等待扩展连接）"
            elif rc1 == 0:
                daemon_note = "；daemon start: rc=0（已就绪）"
            else:
                # 陈旧残留会让后续启动一律 bind 失败，先自愈再重试一次
                heal = _bsk_daemon_selfheal(existing)
                rc2, _, _, to2 = safe_run([existing, "daemon", "start"], timeout=60)
                rc2s = "无响应(>60s)" if to2 else str(rc2)
                daemon_note = f"；daemon start: rc={rc1} → 自愈[{heal}] → 重试 rc={rc2s}"
        return {
            "ok": True,
            "path": existing,
            "on_path": True,
            "extension": "(由官方 BrowserSkill 技能提供)",
            "detail": (
                f"已检测到官方 BrowserSkill 技能提供的 bsk：{existing}（{ver}）。browser-skill 可用；"
                "请确认已在 Chromium 内核浏览器加载官方 BrowserSkill 扩展（popup 显示绿色），"
                f"并可视需手动 `bsk daemon start`{daemon_note}。"
            ),
        }

    # 2) 磁盘已有 bsk 但未进 PATH → 自动软链修复（一键修复常见情形）
    found = _locate_bsk_on_disk()
    if found:
        BSK_LINK_DIR.mkdir(parents=True, exist_ok=True)
        link = BSK_LINK_DIR / "bsk"
        # 已在同一路径则无需重建，直接据实报告
        if found.resolve() == link.resolve():
            ver = _bsk_version(str(found))
            return {
                "ok": True,
                "path": str(found),
                "on_path": True,
                "extension": "(由官方 BrowserSkill 技能提供)",
                "detail": (
                    f"已在 {found} 发现 bsk（{ver}）；请确认已在浏览器加载官方 BrowserSkill 扩展（popup 显示绿色）。"
                ),
            }
        try:
            if link.is_symlink():
                link.unlink()
            elif link.exists():
                # 目标已存在且不是符号链接（可能是用户自己的可执行文件）：不覆盖，直接跳过
                return {
                    "ok": False,
                    "detail": (
                        f"{link} 已存在且不是符号链接，为避免覆盖用户文件已跳过，请手动处理后重试。"
                    ),
                }
            link.symlink_to(found)
            ver = _bsk_version(str(link))
            if ver != "unknown":
                return {
                    "ok": True,
                    "path": str(found),
                    "on_path": True,
                    "extension": "(由官方 BrowserSkill 技能提供)",
                    "detail": (
                        f"已发现 bsk（{found}）但未在 PATH，已自动软链至 {link} 并复检通过（{ver}）。"
                        "请确认已在浏览器加载官方 BrowserSkill 扩展（popup 显示绿色）。"
                    ),
                }
            return {
                "ok": False,
                "detail": (
                    f"已将 {found} 软链至 {link}，但执行 `bsk --version` 失败；"
                    "请确认二进制可执行并重载 PATH，或重装官方 BrowserSkill 技能。"
                ),
            }
        except OSError as e:
            return {
                "ok": False,
                "detail": (
                    f"已在 {found} 发现 bsk，但自动软链到 {link} 失败（{e}）；"
                    "请手动将该路径加入 PATH，或重装官方 BrowserSkill 技能。"
                ),
            }

    # 3) 全盘无 bsk → 给出精确安装引导（不阻塞其余技能）
    return {
        "ok": False,
        "detail": (
            "未检测到 bsk（PATH 与常见安装位置均无）。crawler 前端浏览器自动化依赖官方腾讯 "
            "BrowserSkill 技能提供的 bsk CLI，本包不再随附二进制。请任选一种方式安装：\n"
            "  【方式 A · 自助，推荐】在 WorkBuddy 中：设置 → 技能中心（或技能市场）→ 搜索 "
            "“BrowserSkill” → 安装（腾讯开源）。安装后 bsk 会自动加入 PATH（可能需要重开终端），"
            "再到 Chromium 内核浏览器加载官方 BrowserSkill 扩展（popup 显示绿色）。\n"
            "  【方式 B · 助手代装】直接在对话中说“帮我安装 BrowserSkill”，由 WorkBuddy 助手按默认方式"
            "（marketplace-skill-installer）代为安装并验证 bsk 就位。\n"
            "安装完成后重跑本脚本即可自动通过。（不影响其余技能；仅 crawler 前端采集依赖该技能）"
        ),
    }


def setup_content_summary_env() -> dict:
    skill_dir = PKG_ROOT / "skills" / "content-summary"
    if not skill_dir.is_dir():
        return {"ok": False, "detail": "未找到 content-summary 技能目录"}
    lines = ["# content-summary 凭证模板（由 setup 生成，密钥请自行填写，禁止提交明文）", ""]
    lines += [f"{k}={v}" for k, v in ENV_TEMPLATE.items()]
    body = "\n".join(lines) + "\n"
    # 写入用户目录（~/.workbuddy/teaching-helper-team），避免把凭据落在插件安装目录：
    # 安装目录会被升级 / 清缓存清除，且命中自身自检的 FORBIDDEN_NAMES 禁止名单。
    env_dir = WB / "teaching-helper-team"
    env_dir.mkdir(parents=True, exist_ok=True)
    example = env_dir / ".env.example"
    env = env_dir / ".env"
    example.write_text(body, encoding="utf-8")
    created = False
    if not env.exists():
        env.write_text(body, encoding="utf-8")
        created = True
    return {
        "ok": True,
        "example": str(example),
        "env": str(env),
        "created": created,
        "detail": "已生成 .env 凭证模板" + ("；.env 已创建（占位，待填真实 key）" if created else "；.env 已存在，未覆盖"),
    }


def run_deai_selfcheck(vp: Path) -> dict:
    """用刚装好的 venv 验证 deai_preflight 可运行（交付前门禁自检）。"""
    preflight = PKG_ROOT / "skills" / "deai-rules" / "scripts" / "deai_preflight.py"
    if not preflight.is_file():
        return {"ok": False, "detail": "未找到 deai_preflight.py"}
    try:
        r = subprocess.run(
            [str(vp), str(preflight), "--help"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return {"ok": r.returncode == 0, "detail": "deai_preflight 可运行" if r.returncode == 0 else r.stderr[-200:]}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "detail": str(e)[:200]}


# --------------------------------------------------------------------------- #
# 报告与状态
# --------------------------------------------------------------------------- #
def write_status(status: dict) -> None:
    """落地状态：JSON 全量 + 单行文本旁路（供免解析读取解释器路径）。

    要点：
      - **原子替换**（先写 .tmp 再 os.replace），避免进程被杀时留下半截 JSON；
      - 只在已知 venv_python 时刷新 venv_python.txt，绝不用空值覆盖已有好值。
    """
    STATUS_DIR.mkdir(parents=True, exist_ok=True)
    payload = dict(status)
    payload["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    tmp = STATUS_FILE.with_name(STATUS_FILE.name + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, STATUS_FILE)
    vp = payload.get("venv_python")
    if vp:
        VENV_PY_TXT.write_text(str(vp) + "\n", encoding="utf-8")


def load_status() -> dict | None:
    """读取已有状态；不存在或解析失败返回 None（不抛异常）。"""
    if not STATUS_FILE.is_file():
        return None
    try:
        data = json.loads(STATUS_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:  # noqa: BLE001
        return None


def summarize(results: dict) -> tuple[int, str]:
    """返回 (exit_code, human_text)。"""
    lines = ["=== 教学帮帮团 初始化报告 ===", ""]
    fails = 0
    for section, items in results.items():
        if section in ("venv_python", "meta"):
            continue
        if isinstance(items, dict) and "ok" in items:
            mark = "OK " if items["ok"] else "WARN"
            if not items["ok"]:
                fails += 1
            lines.append(f"[{mark}] {section}: {items.get('detail', '')}")
        elif isinstance(items, list):
            ok_items = [i for i in items if i.get("ok")]
            bad_items = [i for i in items if not i.get("ok")]
            fails += len(bad_items)
            if bad_items:
                lines.append(f"[WARN] {section}: {len(ok_items)} 成功 / {len(bad_items)} 失败")
                for b in bad_items:
                    lines.append(f"        - {b['pkg']}: {b['detail']}")
            else:
                pkgs = ", ".join(i["pkg"] for i in items)
                lines.append(f"[OK ] {section}: {pkgs}")
    lines.append("")
    if fails == 0:
        lines.append("状态: 全部就绪 (退出码 0)")
        lines.append("下一步: 直接用各技能即可；crawler 前端依赖的 bsk 由官方 BrowserSkill 技能提供（见上方状态；扩展需以开发者模式加载）。")
        return 0, "\n".join(lines)
    lines.append(f"状态: 部分完成（{fails} 项需关注，退出码 1）")
    lines.append("下一步: 按上方 WARN 项排查（多为网络/权限），可重跑本脚本幂等修复。")
    return 1, "\n".join(lines)


# --------------------------------------------------------------------------- #
# 主流程
# --------------------------------------------------------------------------- #
def run_group(group: str, vp: Path, args: argparse.Namespace, results: dict) -> bool:
    """执行单个组，把结果写进 results；返回该组是否成功。"""
    if group in PY_DEPS:
        items = pip_install(vp, PY_DEPS[group])
        results[group] = items
        ok = all(i["ok"] for i in items)
        if group == "minutes-organizer" and not args.skip_node:
            # Node docx 属可选（平台自带办公技能可用时无需离线生成），其失败不改判本组
            results["minutes-organizer-node-docx"] = install_node_docx()
        return ok
    if group == "browser":
        # bsk 缺失属可恢复 WARN（仅影响 crawler 前端），不判 fatal
        results["browser-skill-install"] = install_browser_skill(start_daemon=args.start_daemon)
        return True
    if group == "env":
        results["content-summary-env"] = setup_content_summary_env()
        return True
    if group == "selfcheck":
        res = run_deai_selfcheck(vp)
        results["deai-selfcheck"] = res
        return bool(res.get("ok"))
    return True


def resolve_groups(args: argparse.Namespace) -> "list[str] | None":
    """把命令行参数解析成「按执行顺序排列的组列表」；非法输入返回 None。"""
    if args.minimal and args.only:
        print("FATAL: --minimal 与 --only 不能同时使用")
        return None
    if args.minimal:
        selected = list(MINIMAL_GROUPS)
    elif args.only:
        raw = [s.strip() for s in args.only.split(",") if s.strip()]
        if "all" in raw:
            selected = list(GROUP_ORDER)
        else:
            bad = [s for s in raw if s not in GROUP_ORDER]
            if bad:
                print(f"FATAL: 未知组名 {bad}；可用组：{', '.join(GROUP_ORDER)}")
                return None
            selected = [g for g in GROUP_ORDER if g in raw]
    else:
        selected = list(GROUP_ORDER)
    if args.skip_browser:
        selected = [g for g in selected if g != "browser"]
    return selected


def main() -> int:
    global STATUS_QUIET
    ap = argparse.ArgumentParser(
        description="教学帮帮团一键初始化：安装运行时依赖（支持分批 / 续装）。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""可用组：
  {chr(10).join(GROUP_ORDER)}

示例：
  setup.py --minimal                  只装 crawler 组（最快）
  setup.py --only crawler,ppt-maker   只装指定组
  setup.py --resume                   只补未完成的组（等于默认行为）
  setup.py --only crawler --force     强制重装指定组
""",
    )
    ap.add_argument("--json", action="store_true", dest="as_json", help="输出机器可读 JSON")
    ap.add_argument("--only", metavar="G1,G2", default=None,
                    help="只处理指定组（逗号分隔，见文末列表）；传 all 表示全部")
    ap.add_argument("--resume", action="store_true",
                    help="只补装未完成的组（默认行为，显式指定便于脚本化）")
    ap.add_argument("--minimal", action="store_true",
                    help="等价 --only crawler（静态爬虫最小可用集，冷启动约 1 分钟）")
    ap.add_argument("--force", action="store_true",
                    help="忽略已完成状态，对选定组强制重装")
    ap.add_argument("--skip-node", action="store_true", help="跳过 Node docx 安装")
    ap.add_argument("--skip-browser", action="store_true", help="跳过 browser-skill 可达性检测")
    ap.add_argument("--start-daemon", action="store_true",
                    help="bsk 已就位时立即启动其 daemon（默认不启动，由用户手动 `bsk daemon start`）")
    args = ap.parse_args()
    STATUS_QUIET = bool(args.as_json)

    selected = resolve_groups(args)
    if selected is None:
        return 2

    # ---- 启动即落盘状态（此前这里没有任何状态写入）----
    # 为什么必须写在这里：
    #    若第一次 write_status 发生在 `ensure_venv()` **之后**，则 venv 创建期间
    #    （本机约 17 s）**状态文件根本不存在**，A1「任何时刻中断都留下可用状态」
    #    的承诺在该区间不成立。
    # 现在：进程一起来就先写一次 `stage=starting` 的状态，把可观测窗口收敛到 0。
    # 注意：本次不提供 venv_python（此刻还没有），但**必须保留上一次已知的好值**，
    #       否则会把主理人唯一的解释器旁路信息覆盖成空。
    _prev0 = load_status() or {}
    _vp0 = _prev0.get("venv_python")
    if _vp0 and not Path(str(_vp0)).is_file():
        _vp0 = None
    write_status({
        "status": "in_progress",
        "stage": "starting",
        "venv_python": _vp0,
        "pkg_root": str(PKG_ROOT),
        "selected": selected,
        "groups": dict(_prev0.get("groups") or {}),
        "details": {},
        "started_at": _prev0.get("started_at") or time.strftime("%Y-%m-%d %H:%M:%S"),
        "note": STATUS_NOTE,
    })

    # 数据总线目录（三段式 incoming/working/outgoing，见 DATA-CONTRACT.md）
    for _seg in ("incoming", "working", "outgoing"):
        (STATUS_DIR / "data" / "pipeline" / _seg).mkdir(parents=True, exist_ok=True)

    managed_py = find_managed_python()
    if not managed_py:
        # 即使无法继续也落地状态 —— 保证「任何时刻中断都有状态可查」
        write_status({
            "status": "failed",
            "venv_python": None,
            "pkg_root": str(PKG_ROOT),
            "selected": selected,
            "groups": {},
            "details": {},
            "fatal": "未找到可用 Python，无法继续",
            "note": STATUS_NOTE,
        })
        msg = {"ok": False, "detail": "未找到可用 Python，无法继续"}
        print(json.dumps({"fatal": msg}, ensure_ascii=False, indent=2) if args.as_json else "FATAL: " + msg["detail"])
        return 2

    try:
        vp = ensure_venv(managed_py)
    except Exception as e:  # noqa: BLE001
        write_status({
            "status": "failed",
            "venv_python": None,
            "pkg_root": str(PKG_ROOT),
            "selected": selected,
            "groups": {},
            "details": {},
            "fatal": f"创建 venv 失败: {e}",
            "note": STATUS_NOTE,
        })
        print(f"FATAL: 创建 venv 失败: {e}")
        return 2

    # ---- 关键：venv 一就绪就落盘状态（含解释器路径）----
    # 此刻起无论后面哪一组中断，都存在可用状态；"取不到 venv_python ⇒ 不能用 python 去取"的死锁随之解除。
    prev = load_status() or {}
    prev_groups: dict = prev.get("groups") or {}
    prev_details: dict = prev.get("details") or {}

    state: dict = {
        "status": "in_progress",
        "stage": "venv_ready",
        "venv_python": str(vp),
        "pkg_root": str(PKG_ROOT),
        "managed_python": managed_py,
        "selected": selected,
        "groups": dict(prev_groups),
        "details": {},
        "started_at": prev.get("started_at") or time.strftime("%Y-%m-%d %H:%M:%S"),
        "note": STATUS_NOTE,
    }
    write_status(state)

    results: dict = {"meta": {"pkg_root": str(PKG_ROOT), "venv": str(VENV_DIR)}, "venv_python": str(vp)}
    skipped: list[str] = []

    for group in selected:
        if not args.force and prev_groups.get(group) == "ok":
            # 续装 / 幂等：已完成组直接跳过（--force 可强制重装）
            skipped.append(group)
            state["groups"][group] = "ok"
            results[group] = prev_details.get(group) or {"ok": True, "detail": "已完成，本次跳过（--force 可重装）"}
            write_status(state)
            continue

        try:
            ok = run_group(group, vp, args, results)
        except Exception as e:  # noqa: BLE001
            ok = False
            results[group] = {"ok": False, "detail": f"执行异常: {e}"}
        state["groups"][group] = "ok" if ok else "failed"
        state["details"] = dict(results)
        write_status(state)   # * 每完成一组立即刷新状态

    # ---- 收尾 ----
    ok_all = all(state["groups"].get(g) in ("ok", "skipped") for g in selected)
    state["status"] = "ok" if ok_all else "partial"
    state["details"] = dict(results)
    state["skipped"] = skipped
    state["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    write_status(state)

    code = 0 if ok_all else 1
    if args.as_json:
        print(json.dumps(state, ensure_ascii=False, indent=2))
    else:
        print(f"选定组（{len(selected)}）：{', '.join(selected)}")
        if skipped:
            print(f"本次跳过（已就绪）：{', '.join(skipped)}")
        _unused_code, text = summarize(results)
        print(text)
    return code


def all_ok(results: dict) -> bool:
    """按 results 判断是否全绿（保留供外部引用）；bsk 缺失 / .env 模板属可恢复 WARN。"""
    for section, items in results.items():
        if section in ("venv_python", "meta", "minutes-organizer-node-docx"):
            continue
        if isinstance(items, dict) and "ok" in items and not items["ok"]:
            if section in ("browser-skill-install", "content-summary-env"):
                continue
            return False
        elif isinstance(items, list) and any(not i.get("ok") for i in items):
            return False
    return True


if __name__ == "__main__":
    raise SystemExit(main())
