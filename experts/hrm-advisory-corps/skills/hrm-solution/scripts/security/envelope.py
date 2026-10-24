#!/usr/bin/env python3
"""HRM 实战参谋团 · Agent 消息信封（鉴权 + 结构化）

跨 Agent 信息流（经总调度中转）统一封装为信封，并对信封做 HMAC 签名，
防止伪造/重放；成员间禁止直连（由编排层强制经总调度）。

签名密钥解析顺序（跨进程互验默认可用）：
  1. 环境变量 ``HRM_ENVELOPE_KEY`` —— 优先级最高，适合密钥集中下发；
  2. **持久化密钥文件** —— ``$HRM_ENVELOPE_KEY_FILE``，未设置时默认
     ``<用户数据目录>/hrm-advisory-corps/envelope.key``；首次使用时以
     ``secrets.token_bytes(32)`` 生成并以 ``0600`` 模式写入。**平台差异与加固**：
     - POSIX：``os.open(..., 0o600)`` 生效，文件对同组/其他用户不可读；
     - Windows：``os.open`` 的模式位与 ``os.chmod`` 均**不改变 ACL**（实测权限位仍为
       ``0666``）。因此本模块在创建/读取该文件后，**主动调用 ``icacls``** 收紧 ACL：
       ``icacls "<path>" /inheritance:r /grant:r "<USER>:F"``（``<USER>`` 取
       ``USERDOMAIN\\USERNAME``，必要时退化为 ``USERNAME``；以 ``subprocess`` 列表参数
       传入、``shell=False``，故用户名含空格/非 ASCII 也不会被错误切分），随后**回读
       ``icacls "<path>"`` 输出并校验**「继承已关闭且仅当前用户被授权」。
       **降级边界（不承诺过头）**：若 ``icacls`` 不存在 / 被安全策略拦截 / 返回非 0 /
       校验不通过，则**不中断主流程**，仅发 ``RuntimeWarning`` 并明示「保密性降级为依赖
       用户数据目录本身 ACL」；开启 ``HRM_ENVELOPE_STRICT=1`` 时该情形**改为抛
       ``EnvelopeKeyError``**。即：加固成功时 Windows 上密钥文件仅当前用户可读；加固失败
       时其保密性**仍等同于用户数据目录 ACL**（通常仅当前用户与管理员可读），并非等于
       已强制隔离。
     该文件绝不落在插件安装目录内，从而同一用户下的不同进程可共享同一把钥匙、互验签名；
  3. **无安全位置时不再落盘**：若 Windows 上 ``APPDATA`` 与 ``LOCALAPPDATA`` 均不可用，
     视为**无安全位置**——**绝不**回退到系统临时目录（世界可写）或任何其他不安全位置，
     而是直接进入第 4 条降级路径（``HRM_ENVELOPE_STRICT=1`` 时抛错）。
  4. 仅当既无环境变量、亦无可用安全位置时，才降级为**进程内一次性随机密钥**（并发一次
     ``RuntimeWarning``）——此时跨进程互验会失败，仅单进程自签自验可用。

``key_source()`` 返回当前来源：``env:HRM_ENVELOPE_KEY`` / ``keyfile:<path>`` /
``process-random``。设置 ``HRM_ENVELOPE_STRICT=1`` 时，若既无环境变量亦无可用
密钥文件，则直接抛 ``EnvelopeKeyError``（推荐生产环境开启）。

CLI（``python3 envelope.py <cmd>``）：
  - ``key-source``                        打印当前签名密钥来源（输出格式保持不变）
  - ``key-protect``                       打印密钥文件路径 / OS / 是否已加固 / 生效 ACL
                                          摘要；已受保护→退出 0，未受保护→退出 1
  - ``verify <envelope.json> [--max-age S]``  校验信封（打印 OK/INVALID + 来源，退出 0/4）
  - ``selftest``                          签名→验签往返自检，打印结果

示例：
  python3 envelope.py key-source
  python3 envelope.py key-protect
  python3 envelope.py selftest
  python3 envelope.py verify /tmp/env.json --max-age 3600
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import locale
import os
import re
import secrets
import shutil
import subprocess
import sys
import time
import warnings
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

_SIGN_KEY_ENV = "HRM_ENVELOPE_KEY"
_STRICT_ENV = "HRM_ENVELOPE_STRICT"
_KEY_FILE_ENV = "HRM_ENVELOPE_KEY_FILE"
_APP_NAME = "hrm-advisory-corps"
_key_cache: Optional[bytes] = None
_key_source: Optional[str] = None
_degrade_warned: bool = False
_icacls_state: Dict[str, Any] = {}   # 最近一次 Windows ACL 加固结果（供 key-protect 展示）


class EnvelopeKeyError(RuntimeError):
    """严格模式（HRM_ENVELOPE_STRICT=1）下未注入稳定签名密钥。"""


def _user_base_dir() -> Optional[str]:
    """用户级数据根目录（绝不使用插件安装目录，也绝不回退到世界可写的临时目录）。

    返回 ``None`` 表示**无安全目录可用**（Windows 上 ``APPDATA`` 与 ``LOCALAPPDATA``
    均缺失）。调用方据此走降级路径（进程内随机密钥）或（STRICT 下）抛错——**绝不**把
    HMAC 密钥写入系统临时目录等世界可写位置。
    """
    if os.name == "nt":
        return os.getenv("APPDATA") or os.getenv("LOCALAPPDATA") or None
    return os.getenv("XDG_DATA_HOME") or os.path.join(os.path.expanduser("~"), ".local", "share")


def _key_file_path() -> Optional[str]:
    """持久化密钥文件路径：环境变量优先，否则用户数据目录下；无安全目录时返回 None。"""
    env = os.getenv(_KEY_FILE_ENV)
    if env:
        return env
    base = _user_base_dir()
    if not base:
        return None
    return os.path.join(base, _APP_NAME, "envelope.key")


# ---------------------------------------------------------------------------
# Windows 密钥文件 ACL 加固（icacls）
# ---------------------------------------------------------------------------
_ACE_RE = re.compile(r'([^\s():]+)\s*:(\([^)]*\)(?:\([^)]*\))*)')


def _decode_bytes(b: Any) -> str:
    """健壮解码子进程输出（Windows 本地化输出可能非 UTF-8）。"""
    if isinstance(b, str):
        return b
    if not isinstance(b, (bytes, bytearray)):
        return "" if b is None else str(b)
    for enc in ("utf-8", "mbcs", "gbk", locale.getpreferredencoding(False), "latin-1"):
        try:
            return bytes(b).decode(enc)
        except Exception:
            continue
    return bytes(b).decode("latin-1", "replace")


def _windows_user_principal() -> Optional[str]:
    """当前用户的 ACL 主体名（优先 ``USERDOMAIN\\USERNAME``，必要时退化为 ``USERNAME``）。"""
    user = os.environ.get("USERNAME")
    if not user:
        return None
    dom = os.environ.get("USERDOMAIN")
    return ("%s\\%s" % (dom, user)) if dom else user


def _parse_acl(text: str) -> Tuple[List[str], bool]:
    """解析 ``icacls <path>`` 输出，返回 (非继承授权主体列表, 是否仍存在继承 ACE)。"""
    grantees: List[str] = []
    inherited = False
    for m in _ACE_RE.finditer(text):
        principal, ace = m.group(1), m.group(2)
        if "(I)" in ace:
            inherited = True
            continue
        grantees.append(principal)
    return grantees, inherited


def _harden_windows_acl(path: str) -> Tuple[bool, str, str]:
    """用 icacls 关闭继承并仅授予当前用户，随后回读校验。

    返回 ``(ok, summary, detail)``。**本函数绝不抛异常**（任何失败都返回 ``ok=False``），
    由调用方按 STRICT 决定「告警」还是「抛错」。
    """
    icacls = shutil.which("icacls")
    if not icacls:
        return False, "icacls 不可用", "在 PATH 中找不到 icacls"
    user = _windows_user_principal()
    if not user:
        return False, "无法确定当前用户", "USERNAME 环境变量缺失"
    # 以列表参数 + shell=False 调用：用户名含空格/非 ASCII 也不会被错误切分。
    try:
        p = subprocess.run([icacls, path, "/inheritance:r", "/grant:r", "%s:F" % user],
                           shell=False, capture_output=True)
    except Exception as e:  # noqa: BLE001 - 加固失败不得崩溃主流程
        return False, "icacls 调用异常", repr(e)
    if p.returncode != 0:
        return False, "icacls 返回非 0（%d）" % p.returncode, \
            (_decode_bytes(p.stdout) + _decode_bytes(p.stderr)).strip()
    # 回读校验：确认继承已关闭且仅当前用户被授权
    try:
        q = subprocess.run([icacls, path], shell=False, capture_output=True)
    except Exception as e:  # noqa: BLE001
        return False, "icacls 校验调用异常", repr(e)
    out = _decode_bytes(q.stdout)
    grantees, inherited = _parse_acl(out)
    uname = os.environ.get("USERNAME", "")
    expected = {user.lower()}
    if uname:
        expected.add(uname.lower())
    actual = set(g.lower() for g in grantees)
    ok = (not inherited) and bool(actual) and actual <= expected
    summary = "继承=%s；授权主体=%s" % (
        "已关闭" if not inherited else "仍存在（未达预期）",
        sorted(actual) if actual else "无")
    return ok, summary, out.strip()


def _protect_keyfile(path: str) -> None:
    """对已落盘的密钥文件做平台加固（Windows 用 icacls）。

    结果缓存于 ``_icacls_state`` 供 ``key-protect`` 展示。POSIX 上 ``os.open(..., 0o600)``
    已保证权限，无需额外动作。加固失败：非 STRICT → 告警；STRICT → 抛 ``EnvelopeKeyError``。
    """
    global _icacls_state
    if os.name != "nt":
        return
    strict = os.getenv(_STRICT_ENV, "").strip().lower() in ("1", "true", "yes", "on")
    ok, summary, detail = _harden_windows_acl(path)
    _icacls_state = {"path": path, "ok": ok, "summary": summary, "detail": detail}
    if not ok:
        msg = ("密钥文件 ACL 加固未成功（%s）；保密性降级为依赖用户数据目录本身 ACL。"
               % summary)
        if strict:
            raise EnvelopeKeyError(msg)
        warnings.warn(msg, RuntimeWarning, stacklevel=3)


def _load_or_create_keyfile(path: Optional[str]) -> Optional[bytes]:
    """读取持久化密钥；不存在则以 0600 模式创建，并对文件做平台加固。

    POSIX：``os.open(..., 0o600)`` 生效；Windows：创建/读取后调用 icacls 收紧 ACL 并校验
    （见模块 docstring 的降级边界）。失败返回 None（交由上层降级）。
    """
    if not path:
        return None
    try:
        if os.path.exists(path):
            with open(path, "rb") as f:
                data = f.read()
            if data:
                _protect_keyfile(path)
                return data
        d = os.path.dirname(path)
        if d:
            os.makedirs(d, exist_ok=True)
        new_key = secrets.token_bytes(32)
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            # 并发下别的进程先建好，直接读取
            with open(path, "rb") as f:
                data = f.read()
            _protect_keyfile(path)
            return data or None
        with os.fdopen(fd, "wb") as f:
            f.write(new_key)
        try:
            # POSIX 上 os.open 已按 0o600 创建；Windows 上本调用**不改变 ACL**，
            # 真正的收紧见下方 _protect_keyfile（icacls）。
            os.chmod(path, 0o600)
        except OSError:
            pass
        _protect_keyfile(path)
        return new_key
    except OSError:
        return None


def _sign_key() -> bytes:
    """签名密钥：环境变量 > 持久化密钥文件 > 进程内随机（降级）。

    进程内缓存保证同一进程内 sign 与 verify 使用同一把钥匙；持久化密钥文件
    保证不同进程默认共享同一把钥匙，使跨进程验签开箱即用。
    """
    global _key_cache, _key_source, _degrade_warned
    v = os.getenv(_SIGN_KEY_ENV)
    if v:
        _key_source = "env:" + _SIGN_KEY_ENV
        return v.encode("utf-8")
    if _key_cache is None:
        kf = _key_file_path()
        got = _load_or_create_keyfile(kf)
        if got is not None:
            _key_cache = got
            _key_source = "keyfile:" + (kf or "")
    if _key_cache is not None:
        return _key_cache
    kf = _key_file_path()
    where = kf if kf else "APPDATA/LOCALAPPDATA 均不可用（无安全位置，已拒绝回退到世界可写临时目录）"
    if os.getenv(_STRICT_ENV, "").strip().lower() in ("1", "true", "yes", "on"):
        raise EnvelopeKeyError(
            f"{_STRICT_ENV} 已开启但既未注入 {_SIGN_KEY_ENV}、也无法在安全位置创建密钥文件"
            f"（{where}）；跨进程签名互验必然失败，拒绝降级运行。"
        )
    if not _degrade_warned:
        _degrade_warned = True
        warnings.warn(
            f"未能获得稳定签名密钥（{_SIGN_KEY_ENV} 未注入，且无可用安全密钥文件位置：{where}），"
            "已降级为进程内一次性随机密钥：仅单进程自签自验可用，跨进程互验将失败。"
            f"生产环境请注入 {_SIGN_KEY_ENV}，或设 {_STRICT_ENV}=1 让此情形直接失败。",
            RuntimeWarning,
            stacklevel=3,
        )
    _key_cache = secrets.token_bytes(32)
    _key_source = "process-random"
    return _key_cache


def key_source() -> str:
    """返回当前签名密钥来源（便于部署排查）。

    - ``"env:HRM_ENVELOPE_KEY"``：已注入稳定密钥（推荐）
    - ``"keyfile:<path>"``：使用用户数据目录下的持久化密钥文件（跨进程互验可用）
    - ``"process-random"``：进程内一次性随机密钥（仅本地单进程校验可用；跨进程互验必失败）
    """
    if os.getenv(_SIGN_KEY_ENV):
        return "env:" + _SIGN_KEY_ENV
    if _key_source is None:
        _sign_key()  # 首次调用时解析并（在可行时）创建持久化密钥文件
    return _key_source or "process-random"


def _key_protection_status() -> Dict[str, Any]:
    """汇总密钥文件的保护状态（供 ``key-protect`` 子命令展示）。

    ``protected`` 语义：密钥已处于受保护状态——由环境变量注入（不落盘），或密钥文件已被
    成功加固（Windows ACL / POSIX 0600）。无安全位置或加固失败时为 False。
    """
    src = key_source()
    kf = _key_file_path()
    status: Dict[str, Any] = {
        "os": ("Windows" if os.name == "nt" else os.name),
        "key_source": src,
        "key_file": kf,
        "exists": bool(kf and os.path.exists(kf)),
        "hardened": None,
        "acl_summary": "",
        "protected": False,
        "note": "",
    }
    if src.startswith("env:"):
        status["protected"] = True
        status["note"] = "密钥由环境变量注入（不落盘，无文件可加固）"
        return status
    if not kf:
        status["note"] = "无安全位置可用，未创建密钥文件（进程内随机密钥）"
        return status
    if not status["exists"]:
        status["note"] = "密钥文件不存在（尚未生成）"
        return status
    if os.name == "nt":
        if _icacls_state.get("path") == kf:
            status["hardened"] = bool(_icacls_state.get("ok"))
            status["acl_summary"] = _icacls_state.get("summary", "")
        else:
            ok, summary, _ = _harden_windows_acl(kf)
            status["hardened"] = ok
            status["acl_summary"] = summary
        status["protected"] = bool(status["hardened"])
        if not status["protected"]:
            status["note"] = "ACL 加固未成功，保密性依赖用户数据目录 ACL"
    else:
        try:
            st = os.stat(kf)
            status["acl_summary"] = "POSIX mode=%s" % oct(st.st_mode & 0o777)
            status["hardened"] = (st.st_mode & 0o077) == 0
            status["protected"] = bool(status["hardened"])
        except OSError as e:
            status["note"] = "无法读取文件权限: %s" % e
    return status


def _canon(*parts: str) -> bytes:
    """长度前缀规范化拼接，消除字段边界歧义。

    早期实现用 `f"{msg_id}|{trace_id}|{body}"` 直接拼接，字段边界可滑动：
    `(msg_id="A|B", trace_id="C")` 与 `(msg_id="A", trace_id="B|C")` 会
    产出同一条待签串，从而得到相同签名。改为对每段写入其 UTF-8 字节长度前缀，
    使任意分段方式一一对应唯一字节串。
    """
    out = bytearray()
    for p in parts:
        b = p.encode("utf-8")
        out += str(len(b)).encode("ascii") + b":" + b
    return bytes(out)


def sign(msg_id: str, trace_id: str, body: str) -> str:
    return hmac.new(_sign_key(), _canon(msg_id, trace_id, body),
                    hashlib.sha256).hexdigest()


@dataclass
class Envelope:
    msg_id: str
    trace_id: str
    frm: str
    to: str
    phase: str
    intent: str
    payload: Dict[str, Any] = field(default_factory=dict)
    artifacts: List[Dict[str, Any]] = field(default_factory=list)
    compliance: Dict[str, Any] = field(default_factory=lambda: {"gate": "PENDING", "risk_level": None, "dri": None})
    ts: str = ""
    nonce: str = ""

    def __post_init__(self) -> None:
        if not self.ts:
            self.ts = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        if not self.nonce:
            self.nonce = secrets.token_hex(8)

    def body_str(self) -> str:
        # 签名覆盖完整路由元数据 + 内容，防止伪造/重放/篡改
        return json.dumps({
            "from": self.frm, "to": self.to, "phase": self.phase,
            "intent": self.intent, "ts": self.ts, "nonce": self.nonce,
            "payload": self.payload, "artifacts": self.artifacts,
            "compliance": self.compliance,
        }, ensure_ascii=False, sort_keys=True)

    def sign(self) -> str:
        return sign(self.msg_id, self.trace_id, self.body_str())

    def to_dict(self, with_sig: bool = True) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "msg_id": self.msg_id, "trace_id": self.trace_id,
            "from": self.frm, "to": self.to, "phase": self.phase,
            "intent": self.intent, "payload": self.payload,
            "artifacts": self.artifacts, "compliance": self.compliance,
            "ts": self.ts, "nonce": self.nonce,
        }
        if with_sig:
            d["signature"] = self.sign()
        return d

    @staticmethod
    def verify(d: Dict[str, Any], max_age_sec: Optional[int] = None) -> bool:
        """校验信封签名与基本结构；失败返回 False（疑似伪造/篡改）。

        max_age_sec: 若提供，则对 ts 做时效校验（防重放）；超期返回 False。
        """
        if not all(k in d for k in ("msg_id", "trace_id", "signature", "payload", "compliance", "nonce")):
            return False
        env = Envelope(
            msg_id=d["msg_id"], trace_id=d["trace_id"], frm=d.get("from", ""),
            to=d.get("to", ""), phase=d.get("phase", ""), intent=d.get("intent", ""),
            payload=d["payload"], artifacts=d.get("artifacts", []),
            compliance=d["compliance"], ts=d.get("ts", ""), nonce=d.get("nonce", ""),
        )
        if not hmac.compare_digest(env.sign(), d["signature"]):
            return False
        if max_age_sec is not None and d.get("ts"):
            try:
                # ts 形如 2026-08-08T16:15:31+0800，%z 解析
                ts_dt = datetime.strptime(d["ts"], "%Y-%m-%dT%H:%M:%S%z")
                if (datetime.now(timezone.utc) - ts_dt.astimezone(timezone.utc)).total_seconds() > max_age_sec:
                    return False
            except (ValueError, TypeError):
                return False
        return True


def main(argv: Optional[List[str]] = None) -> int:
    """CLI 入口：key-source / key-protect / verify / selftest。"""
    ap = argparse.ArgumentParser(
        prog="envelope.py",
        description="HRM 信封签名工具（key-source / key-protect / verify / selftest）",
        epilog='示例: python3 envelope.py verify /tmp/env.json --max-age 3600',
    )
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("key-source", help="打印当前签名密钥来源")
    sub.add_parser("key-protect", help="打印密钥文件保护状态（已保护→0，未保护→1）")
    pv = sub.add_parser("verify", help="校验信封 JSON（OK→0，INVALID→4）")
    pv.add_argument("envelope", help="信封 JSON 文件路径")
    pv.add_argument("--max-age", type=int, default=None, metavar="SEC", help="时效上限（秒），超出判 INVALID")
    sub.add_parser("selftest", help="签名→验签往返自检")
    args = ap.parse_args(argv)

    if args.cmd == "key-source":
        print(key_source())
        return 0

    if args.cmd == "key-protect":
        try:
            st = _key_protection_status()
        except EnvelopeKeyError as e:
            sys.stderr.write("[ERR] %s\n" % e)
            return 1
        print("key file : %s" % (st["key_file"] or "<none>"))
        print("os       : %s" % st["os"])
        print("key source: %s" % st["key_source"])
        print("exists   : %s" % st["exists"])
        print("hardened : %s" % ("n/a" if st["hardened"] is None else st["hardened"]))
        print("acl      : %s" % (st["acl_summary"] or "-"))
        if st["note"]:
            print("note     : %s" % st["note"])
        print("protected: %s" % st["protected"])
        return 0 if st["protected"] else 1

    if args.cmd == "verify":
        try:
            with open(args.envelope, encoding="utf-8") as f:
                d = json.load(f)
        except (OSError, ValueError) as e:
            sys.stderr.write(f"[ERR] 无法读取信封: {args.envelope}: {e}\n")
            return 4
        ok = Envelope.verify(d, max_age_sec=args.max_age)
        print(("OK" if ok else "INVALID") + " (key source: %s)" % key_source())
        return 0 if ok else 4

    if args.cmd == "selftest":
        env = Envelope(
            msg_id="selftest", trace_id="selftest-trace",
            frm="hrm-advisory-corps-lead", to="labor-compliance",
            phase="test", intent="selftest", payload={"ok": True},
        )
        ok = Envelope.verify(env.to_dict())
        print("selftest: %s (key source: %s)" % ("OK" if ok else "FAIL", key_source()))
        return 0 if ok else 1

    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
