#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
课程伴学 · 腾讯文档通道封装（course_tdoc.py）

为什么需要它
------------
平台 V2 MCP Gateway 的凭据提供者在返回个人 OAuth 令牌的同时，会把 `api_base`
覆盖成一个腾讯文档的 WorkBuddy 镜像域名（如 `www-docs.workbuddy.cn`）。该镜像
偶发不可达，导致 `tencentdocs.py` 向它 POST 时返回 `502 Bad Gateway` / `Tunnel
connection failed`，而真实端点 `https://docs.qq.com` 始终正常（个人 OAuth 令牌
对该端点有效）。排查记录见《通道故障排查与修正说明》。

本封装的作用（把"故障后才重试"提前成"默认就走权威端点"）
-----------------------------------------------------------------
1. 默认把 `TDOC_API_BASE_URL` 强制指向权威端点 `https://docs.qq.com`，绕开失效镜像。
   仅当用户已**显式**设置 `TDOC_API_BASE_URL` 时才尊重其值（便于高级排错）。
2. 原样透传其余参数与环境变量，调用真实的 `tencentdocs.py`。
3. 若用户显式指定了镜像类域名且调用返回 502 / Tunnel 失败，自动以权威端点重试一次。

用法
----
    python3 course_tdoc.py "<tencentdocs.py 绝对路径>" <子命令> [参数...]

或设置环境变量 TDOC_PY="<tencentdocs.py 绝对路径>" 后：

    python3 course_tdoc.py <子命令> [参数...]

所有原本写给 `tencentdocs.py` 的实参（`tdoc_init` / `tdoc_call` / `tdoc_list` /
`tdoc_schema` 及其后的 JSON / `--timeout` 等）原样透传。

说明
----
- 本文件**不携带** `tencentdocs.py`（那是平台内置腾讯文档插件的资产），只负责
  在调用前注入正确的 `api_base` 并兜底重试。
- 输出统一用纯文本标记 `[OK]/[FAIL]/[!]`，避免 Windows GBK 控制台渲染 emoji 崩溃。
- 本封装**不会**把任何覆盖写入持久配置或脚本之外的地方；环境变量仅作用于本次子进程。
"""
import glob
import json
import os
import re
import subprocess
import sys

CANONICAL_API_BASE = "https://docs.qq.com"

# 失效镜像域名特征：命中即视为"被网关错指到挂掉的镜像"
DEAD_MIRROR_HINTS = ("workbuddy.cn", "workbuddy.com")

# 502 / 隧道层失败的特征串（不区分大小写匹配子进程输出）
TRANSPORT_502_HINTS = ("502", "tunnel connection failed", "bad gateway")


def _autodiscover_tdoc():
    """自动扫插件缓存定位最新版 tencentdocs.py。

    覆盖两种实装形态：模块缓存（plugins/cache/workbuddy-builtin/tencent-docs-plugin/...）
    与市场插件目录（plugins/marketplaces/...）。取修改时间最新的一个，免去每次
    新会话 / 插件升级后手填绝对路径。找不到返回 None（走原报错）。
    """
    home = os.path.expanduser("~")
    patterns = [
        os.path.join(home, ".workbuddy", "plugins", "cache", "workbuddy-builtin",
                     "tencent-docs-plugin", "*", "skills", "tencent-docs", "tencentdocs.py"),
        os.path.join(home, ".workbuddy", "plugins", "marketplaces", "**",
                     "tencent-docs-plugin", "*", "skills", "tencent-docs", "tencentdocs.py"),
    ]
    hits = []
    for pat in patterns:
        hits.extend(glob.glob(pat, recursive=True))
    if not hits:
        return None
    hits.sort(key=lambda p: (os.path.getmtime(p), p))
    return hits[-1]


def _resolve_script(args):
    """从实参或环境变量定位 tencentdocs.py 绝对路径。返回 (script, rest_args)。"""
    script = os.environ.get("TDOC_PY")
    rest = list(args)
    if script:
        return script, rest
    # 找第一个以 .py 结尾的实参作为脚本名（即 `tencentdocs.py <subcmd> ...` 形态）
    for i, a in enumerate(rest):
        if a.endswith(".py"):
            script = rest.pop(i)
            return script, rest
    return None, rest


def _looks_like_mirror(api_base):
    if not api_base:
        return False
    low = api_base.lower()
    return any(h in low for h in DEAD_MIRROR_HINTS)


def _log(prefix, msg):
    sys.stderr.write("[%s] course_tdoc: %s\n" % (prefix, msg))


def _call(script, rest, env):
    cmd = [sys.executable, script] + rest
    try:
        return subprocess.call(cmd, env=env)
    except (FileNotFoundError, OSError) as exc:
        _log("FAIL", "解释器或脚本无法执行：%s / %s（%s）" % (sys.executable, script, exc))
        return 2


def _capture(script, rest, env=None):
    """运行 tencentdocs.py 子命令并捕获 stdout（probe 用）。"""
    cmd = [sys.executable, script] + rest
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120,
                           encoding="utf-8", errors="replace", env=env)
        return r.stdout or ""
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired) as exc:
        _log("FAIL", "探测执行失败：%s" % exc)
        return ""


def _cmd_make_records(rows_path):
    """把简单行 [{列:值}] 转成 smartsheet add_records 的 field_values 规范格式。

    背景：直接写 {fields:{列:值}} 会「返回成功但数据为空」——文本字段必须带
    text_value.items[].type="text"。本子命令纯本地转换，不联网、不依赖 tencentdocs.py。

    用法：python3 course_tdoc.py make_records <rows.json>   （stdout 输出 {"records":[...]}）
    """
    with open(rows_path, "r", encoding="utf-8-sig") as f:
        rows = json.load(f)
    if isinstance(rows, dict):
        rows = [rows]
    # §5.2 防呆断言：本封装只认「行 {列:值}」简单结构，由这里统一产出 text_value(单数)。
    # 若调用方误传已手工拼好的 field_values / 复数 text_values 结构（历史 seq19 静默失败
    # 即因键名写成 text_values 被腾讯文档静默忽略），当场报错阻断，绝不交给平台静默丢弃。
    _FORBIDDEN_KEYS = ("text_values", "field_values")
    for _row in rows:
        if isinstance(_row, dict):
            for _k in _FORBIDDEN_KEYS:
                if _k in _row:
                    _log("FAIL", "make_records 拒绝：行内含已拼接结构键 %r——"
                         "本封装只接受简单行 {列:值}，field_values/text_value 由这里统一生成"
                         % _k)
                    return 2
    recs = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        fv = []
        for k, v in row.items():
            if v is None or v == "":
                continue
            fv.append({"field": str(k),
                       "text_value": {"items": [{"text": str(v), "type": "text"}]}})
        recs.append({"field_values": fv})
    sys.stdout.write(json.dumps({"records": recs}, ensure_ascii=False, indent=2))
    return 0


def main(argv):
    # ：make_records 是纯本地转换子命令，无需定位 tencentdocs.py，最先分流
    if argv[1:2] == ["probe"]:
        # ：工具探测以 tdoc_schema 为准（tdoc_list 返回不可信）。
        # 用法：course_tdoc.py probe <service> <tool>  → exit 0 可用（打印参数名），exit 1 不可用
        if len(argv) < 4:
            _log("FAIL", "用法: probe <service> <tool>")
            return 2
        service, tool = argv[2], argv[3]
        script, rest = _resolve_script(argv[4:])
        if not script:
            script = _autodiscover_tdoc()
        if not script:
            _log("FAIL", "未定位 tencentdocs.py")
            return 2
        out = _capture(script, ["tdoc_schema", service, tool])
        ok = ("参数（" in out) and ("不可用" not in out) and ("not found" not in out.lower())
        if ok:
            params = re.findall(r"\[✓\] ([A-Za-z_]+)", out)
            _log("OK", "%s.%s 可用，必填参数: %s" % (service, tool, ", ".join(params) or "无"))
            return 0
        _log("FAIL", "%s.%s 不可用" % (service, tool))
        return 1

    if argv[1:2] == ["make_records"]:
        if len(argv) < 3:
            _log("FAIL", "用法：make_records <rows.json>")
            return 2
        return _cmd_make_records(argv[2])

    script, rest = _resolve_script(argv[1:])
    if not script:
        script = _autodiscover_tdoc()
        if script:
            _log("OK", "已自动定位 tencentdocs.py（插件缓存最新版）：%s" % script)
    if not script:
        _log("FAIL", "未定位 tencentdocs.py：请将其绝对路径作为首个实参，或设置 TDOC_PY 环境变量")
        return 2
    if not os.path.isfile(script):
        _log("FAIL", "tencentdocs.py 不存在：%s" % script)
        return 2

    env = dict(os.environ)
    user_override = env.get("TDOC_API_BASE_URL")

    if not user_override:
        # 默认强制权威端点：绕开网关偶发指到失效镜像导致的 502
        env["TDOC_API_BASE_URL"] = CANONICAL_API_BASE
        _log("OK", "默认将 api_base 指向权威端点 %s（绕开失效镜像）" % CANONICAL_API_BASE)
    else:
        _log("OK", "使用用户指定的 api_base：%s" % user_override)

    rc = _call(script, rest, env)

    # 兜底重试：仅当用户显式指定了镜像类域名且首次调用疑似传输层 502 时，
    # 强制以权威端点再试一次。默认路径（已走 docs.qq.com）不会进入此处。
    if rc != 0 and user_override and _looks_like_mirror(user_override):
        _log("!", "用户指定的 api_base 疑似失效镜像且调用失败，强制以权威端点重试一次")
        env["TDOC_API_BASE_URL"] = CANONICAL_API_BASE
        rc = _call(script, rest, env)

    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv))
