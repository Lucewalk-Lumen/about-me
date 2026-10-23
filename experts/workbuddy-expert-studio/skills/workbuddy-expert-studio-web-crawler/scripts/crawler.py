#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
crawler.py — 稳健单页抓取与正文抽取（零第三方依赖）

安全（F-001 + F-GAP-01 + H3 + H4 治理）：所有 URL 在进入 urllib / Edge 两条路径之前，先过统一
准入闸门 `_check_url()`（scheme 白名单 + IANA 特殊用途网段黑名单（含 CGNAT
100.64.0.0/10 与云元数据）+ IPv4-mapped IPv6 解映射复检 + DNS 解析后快照复检）。
**逐跳重定向校验适用于 urllib 路径**（`_SafeRedirectHandler`）：每一跳目标均复检。
**Edge 渲染路径（H3）**：进入 Edge 之前，先用同一 `_SafeRedirectHandler` 对入口 URL 解析
HTTP 3xx 重定向链并取最终 URL（任一跳被拒 → 直接 url_denied，不进 Edge），渲染只以该
**已校验的最终 URL** 为目标。**边界**：JS / meta-refresh 等**客户端**跳转无法经服务端逐跳
复检覆盖，Edge 内部的这类跳转仍不复检（见 `_resolve_redirect_chain`/`_render_via_edge` 注释）。
**DNS 重绑定（H4）**：解析快照中已校验的 IP 会在**连接层被钉定**（自定义
`HTTPConnection`/`HTTPSConnection.connect()` 直连该 IP），消除「校验后再次解析」的 TOCTOU
窗口；Host 头与 TLS 的 SNI / 证书校验仍用主机名，**不放松任何 TLS 校验**。
`--from-file` 亦经统一闸门（拒绝伪装 URL + 限定项目工作区 CWD/PKG_ROOT + 大小上限 + 拒绝二进制）。
拒绝一律返回结构化 `{"ok": false, "error_type": "url_denied"|"path_denied"|...}`，绝不抛 traceback。

浏览器渲染优先：运行时优先检测并调用本机已安装的 Microsoft Edge
（--headless --dump-dom）；未安装 Edge 时自动回退 urllib 直取。绝不下载
Chromium/Chrome。Edge 每次使用一次性临时 profile（--user-data-dir）用后清理；
默认不摘渲染进程沙箱（F-003）。

用法：
  python crawler.py <url> [--json] [--no-robots]
  python crawler.py --from-file <html> [--allow-dir <dir> ...]  # 抽取本地 HTML（供 browser-skill 渲染结果回灌）
  python crawler.py --self-test          # 离线验证抽取器 + URL 准入（不联网）

输出（成功）：{ok:true, url, final_url, status, title, text, links:[...], bytes, rendered_by?}
输出（失败）：{ok:false, error_type, error, url|file}
"""
import sys
import os
import re
import shutil
import socket
import json
import time
import ipaddress
import tempfile
import argparse
import subprocess
import urllib.request
import urllib.error
import urllib.robotparser
import urllib.parse
import http.client
from html.parser import HTMLParser

HERE = os.path.dirname(os.path.abspath(__file__))
CONTRACT = os.path.join(HERE, "..", "contract.yaml")
PKG_ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))  # 专家包根目录（--from-file 工作区上界）

# ── 安全闸门常量（URL 准入 / 文件边界） ───────────────────────────
ALLOWED_SCHEMES = ("http", "https")   # 仅允许公网 HTTP(S)；拒绝 file/ftp/data/...

# IANA 特殊用途网段黑名单：**显式列出**，不依赖 `is_private`/`is_global` 等会随
# Python 版本变化的属性语义（本包需兼容 3.9+ 系统 Python）。属性判据仅作兜底。
_BLOCKED_V4 = tuple(ipaddress.ip_network(n) for n in (
    "0.0.0.0/8",          # 本网络 / 未指定
    "10.0.0.0/8",         # RFC1918 私有
    "100.64.0.0/10",      # RFC6598 共享地址（CGNAT）——含阿里云元数据 100.100.100.200
    "127.0.0.0/8",        # 回环
    "169.254.0.0/16",     # 链路本地（含 169.254.169.254 云元数据）
    "172.16.0.0/12",      # RFC1918 私有
    "192.0.0.0/24",       # IETF 协议分配
    "192.0.2.0/24",       # TEST-NET-1
    "192.88.99.0/24",     # 6to4 中继（已弃用）
    "192.168.0.0/16",     # RFC1918 私有
    "198.18.0.0/15",      # 基准测试（RFC2544）
    "198.51.100.0/24",    # TEST-NET-2
    "203.0.113.0/24",     # TEST-NET-3
    "224.0.0.0/4",        # 多播
    "240.0.0.0/4",        # 保留（含 255.255.255.255）
))
_BLOCKED_V6 = tuple(ipaddress.ip_network(n) for n in (
    "::/128",             # 未指定
    "::1/128",            # 回环
    "100::/64",           # 丢弃前缀
    "2001:db8::/32",      # 文档
    "64:ff9b::/96",       # NAT64 知名前缀（DNS64 环境可映射内网，C11/L8）
    "fc00::/7",           # 唯一本地（ULA）
    "fe80::/10",          # 链路本地
    "ff00::/8",           # 多播
))
_IPV4_MAPPED_NET = ipaddress.ip_network("::ffff:0:0/96")  # IPv4-mapped IPv6
# 云元数据服务：显式点名（AWS/GCP/Azure/Aliyun IPv4 + AWS EC2 IPv6 IMDS）
CLOUD_METADATA_IPS = ("169.254.169.254", "100.100.100.200", "fd00:ec2::254")

DEFAULTS = {
    "user_agent": "Mozilla/5.0 (compatible; workbuddy-expert-studio-web-crawler/1.0.2; +https://workbuddy.cn)",
    "timeout_seconds": 15,
    "retries": 2,
    "backoff_base_seconds": 1.5,
    "max_bytes": 2000000,
    "respect_robots": True,
    "follow_redirects": True,
    "max_redirects": 5,
    "prefer_browser": "edge",       # 优先用本机已安装的 Edge 无头渲染；未安装则回退 urllib（绝不下载 Chrome）
    "allow_no_sandbox": False,      # 默认关闭；置 true 会摘掉 Edge 渲染进程沙箱（仅 root/容器按需，开启即放弃沙箱）
    "from_file_max_bytes": 10485760,  # --from-file 单文件上限（10 MB）
    "from_file_allow_dirs": "",     # 逗号分隔的额外允许目录（须落在 CWD/PKG_ROOT 内才生效）
}


def _strip_comment(v):
    """去掉行内注释（不在引号内的 # 之后内容）。"""
    out, q = [], None
    for ch in v:
        if q:
            out.append(ch)
            if ch == q:
                q = None
        elif ch in ('"', "'"):
            q = ch
            out.append(ch)
        elif ch == '#':
            break
        else:
            out.append(ch)
    return "".join(out).strip()


def _scalar(v):
    """把 YAML 标量解析为 str/bool/int/float，并去除引号。"""
    v = v.strip()
    if len(v) >= 2 and ((v[0] == '"' and v[-1] == '"') or (v[0] == "'" and v[-1] == "'")):
        return v[1:-1]
    if v.lower() in ("true", "false"):
        return v.lower() == "true"
    try:
        return float(v) if "." in v else int(v)
    except ValueError:
        return v


def load_cfg():
    """从 contract.yaml 读取 crawl 段；无 PyYAML 时用极简解析兜底（支持行内注释与引号）。"""
    cfg = dict(DEFAULTS)
    try:
        with open(os.path.abspath(CONTRACT), encoding="utf-8") as fh:
            txt = fh.read()
        in_block = False
        for line in txt.splitlines():
            if line.strip().startswith("crawl:"):
                in_block = True
                continue
            if in_block:
                if line and not line.startswith(" ") and not line.startswith("#"):
                    break
                if ":" in line:
                    k, _, v = line.partition(":")
                    k = k.strip()
                    if k in cfg:
                        cfg[k] = _scalar(_strip_comment(v))
    except Exception:
        pass
    return cfg


# ── 安全闸门：URL 准入（F-001 治本 + F-GAP-01） ────────────────────

def _unmap_v4(ip):
    """若为 IPv4-mapped IPv6（::ffff:a.b.c.d）返回其 IPv4Address，否则 None。

    兼容 Python 3.9 —— 该版本无 `ipv4_mapped` 属性，改用位运算手动解映射。
    """
    if isinstance(ip, ipaddress.IPv6Address):
        mapped = getattr(ip, "ipv4_mapped", None)
        if mapped is not None:
            return mapped
        try:
            if ip in _IPV4_MAPPED_NET:
                return ipaddress.IPv4Address(int(ip) & 0xFFFFFFFF)
        except Exception:
            return None
    return None


def _ip_blocked(ip):
    """判定 IP 是否属于内网 / 回环 / 链路本地 / 保留 / 多播 / 未指定 / 云元数据。

    主判据 = 显式 IANA 特殊用途网段黑名单（版本无关）；属性判据仅作兜底。
    IPv4-mapped IPv6 先解映射后按 v4 复检（::ffff:127.0.0.1 等不得漏）。
    """
    mapped = _unmap_v4(ip)
    if mapped is not None:
        return _ip_blocked(mapped)
    # 云元数据端点：显式点名（C8 —— 使该常量真实生效，而非装饰性死代码）
    if str(ip) in CLOUD_METADATA_IPS:
        return True
    nets = _BLOCKED_V6 if isinstance(ip, ipaddress.IPv6Address) else _BLOCKED_V4
    for net in nets:
        if ip in net:
            return True
    # 属性兜底（语义可能随 Python 版本变化，仅作补充，不单独依赖）
    return bool(ip.is_private or ip.is_loopback or ip.is_link_local
                or ip.is_reserved or ip.is_multicast or ip.is_unspecified)


# ── H4：DNS 重绑定防护 —— 连接层「钉 IP」基础设施 ────────────────────
# 校验时（_check_url）保存该主机的解析快照；连接时（connect）直接使用快照中的 IP 建连，
# 不再二次解析主机名，从而消除「解析快照校验」与「连接时再次解析」之间的 TOCTOU 窗口
# （短 TTL 域名可在此期间把记录换绑到内网 IP）。
# 不放松 TLS：HTTPSConnection 仍以主机名做 SNI 与证书校验（server_hostname=主机名）。
# 代理场景：经 HTTP(S) 代理时 urllib 会把 req.host 改为代理主机，本表的键（目标主机）
# 命中不到 → 自动回退标准 connect，交由代理建连，功能不受影响（此处亦不做钉定）。
_PINNED_ADDRS = {}  # {hostname_lower: [(family, socktype, proto, ip_str), ...]}


def _pin_host(host, infos):
    """登记某主机「已通过 _check_url 校验」的解析快照（供连接层钉 IP 使用）。"""
    if not host or not infos:
        return
    _PINNED_ADDRS[host.lower()] = list(infos)


def _pinned_for(host):
    """取某主机已登记的钉定地址；无登记返回 None（回退标准连接行为）。"""
    if not host:
        return None
    return _PINNED_ADDRS.get(host.lower())


def _hostname_of(netloc):
    """从 req.host（可能含端口 / IPv6 方括号）提取纯主机名。"""
    if not netloc:
        return ""
    try:
        return urllib.parse.urlsplit("//" + netloc).hostname or ""
    except Exception:
        return netloc.split(":")[0]


def _pinned_sockaddr(family, ip, port):
    """兼容保留：create_connection 需 2 元组 (host, port)，IP 字面量由其内部按族解析。"""
    return (ip, port)


class _PinnedHTTPConnection(http.client.HTTPConnection):
    """连到「已校验 IP」而非重新解析主机名（H4）。pinned 为空时退回标准行为。"""

    def __init__(self, host, port=None, *, pinned=None, **kwargs):
        super().__init__(host, port, **kwargs)
        self._pinned = list(pinned) if pinned else None

    def connect(self):
        if not self._pinned:
            return super().connect()
        last = None
        for family, _socktype, _proto, ip in self._pinned:
            try:
                self.sock = socket.create_connection(
                    _pinned_sockaddr(family, ip, self.port), self.timeout, self.source_address)
                return
            except OSError as e:
                last = e
        raise last if last else OSError("pinned_connect_failed")


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    """连到「已校验 IP」，但 TLS 的 SNI / 证书校验仍用主机名（H4，不放松 TLS）。"""

    def __init__(self, host, port=None, *, pinned=None, **kwargs):
        super().__init__(host, port, **kwargs)
        self._pinned = list(pinned) if pinned else None

    def connect(self):
        if not self._pinned:
            return super().connect()
        last = None
        for family, _socktype, _proto, ip in self._pinned:
            try:
                sock = socket.create_connection(
                    _pinned_sockaddr(family, ip, self.port), self.timeout, self.source_address)
            except OSError as e:
                last = e
                continue
            try:
                # 关键：server_hostname 用主机名（self.host），不用 IP —— 保留 SNI 与证书校验
                server_hostname = self._tunnel_host if self._tunnel_host else self.host
                self.sock = self._context.wrap_socket(sock, server_hostname=server_hostname)
                return
            except Exception:
                try:
                    sock.close()
                except Exception:
                    pass
                raise
        raise last if last else OSError("pinned_tls_connect_failed")


class _PinnedHTTPHandler(urllib.request.HTTPHandler):
    """把目标主机的「已校验 IP」透传给连接层（H4）。"""

    def http_open(self, req):
        return self.do_open(_PinnedHTTPConnection, req,
                            pinned=_pinned_for(_hostname_of(getattr(req, "host", ""))))


class _PinnedHTTPSHandler(urllib.request.HTTPSHandler):
    """HTTPS 版：透传钉定 IP，同时保留 context 的 SNI / 证书校验（H4）。"""

    def https_open(self, req):
        return self.do_open(_PinnedHTTPSConnection, req, context=self._context,
                            pinned=_pinned_for(_hostname_of(getattr(req, "host", ""))))


def _check_url(u):
    """URL 准入闸门：返回 (ok: bool, reason: str)。

    规则：
      ① scheme 白名单（仅 http/https，拒绝 file/ftp/data/...）；
      ② host 非空、非 localhost、非百分号编码（防解析歧义）；
      ③ host 为字面 IP 时直接按黑名单判定（含 CGNAT / 云元数据 / mapped v6）；
      ④ host 为域名时 DNS 解析后**快照复检**每个解析地址（可挡内网域名 / 十进制·八进制·
         十六进制等数字形态 IP）；通过校验的解析快照同时登记为**连接层钉定目标**（H4），
         连接阶段直接使用该 IP、不再二次解析，闭合「校验 → 连接」间的 DNS 重绑定（TOCTOU）窗口。

    任何拒绝理由均为稳定字符串，供上游以 `error_type=url_denied` 消费。
    """
    try:
        p = urllib.parse.urlparse((u or "").strip())
    except Exception as e:
        return False, f"url_parse_failed:{type(e).__name__}"
    if (p.scheme or "").lower() not in ALLOWED_SCHEMES:
        return False, f"scheme_not_allowed:{p.scheme or 'empty'}"
    if "%" in p.netloc:
        return False, "percent_encoded_host"
    host = p.hostname
    if not host:
        return False, "host_missing"
    if host.lower() in ("localhost", "localhost.localdomain", "0.0.0.0"):
        return False, f"host_denied:{host}"
    try:                                   # 字面 IPv4 / IPv6
        if _ip_blocked(ipaddress.ip_address(host)):
            return False, f"internal_ip:{host}"
        return True, ""
    except ValueError:
        pass
    try:                                   # DNS 解析后再判，防 rebinding / 数字形态 IP
        infos = socket.getaddrinfo(host, None)
    except Exception as e:
        return False, f"dns_failed:{type(e).__name__}"
    pinned = []
    try:
        for info in infos:
            ip = ipaddress.ip_address(info[4][0])
            if _ip_blocked(ip):
                return False, f"internal_ip_resolved:{ip}"
            pinned.append((info[0], info[1], info[2], info[4][0]))
    except Exception as e:
        return False, f"dns_failed:{type(e).__name__}"
    # H4：登记「通过校验的解析快照」为连接层钉定目标（连接时不再解析，消除 TOCTOU）
    _pin_host(host, pinned)
    return True, ""


class _RedirectDenied(Exception):
    """重定向目标未通过 URL 准入时抛出，由 fetch() 转为结构化 url_denied。"""


class _SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    """逐跳校验重定向目标：任何一跳未过 _check_url 即拒绝。

    真正实现 contract.yaml 的 follow_redirects / max_redirects，
    并防御「公网地址 302 到内网」的 SSRF 绕过（仅校验入口 URL 不足以防御）。
    """

    def __init__(self, max_redirects=5, follow=True):
        super().__init__()
        self.max_redirections = int(max_redirects)
        self._follow = bool(follow)

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not self._follow:
            raise _RedirectDenied("redirects_disabled")
        allow, why = _check_url(newurl)
        if not allow:
            raise _RedirectDenied(f"redirect_denied:{why}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _build_opener(cfg):
    """构造 opener：逐跳校验重定向（替换默认 HTTPRedirectHandler）+ 连接层钉 IP（H4）。

    传入 _PinnedHTTPHandler/_PinnedHTTPSHandler 使 build_opener 跳过默认 HTTP(S)Handler，
    使每条连接都走「已校验 IP」的 connect（无钉定登记时自动回退标准行为）。
    """
    redirect = _SafeRedirectHandler(cfg.get("max_redirects", 5),
                                    cfg.get("follow_redirects", True))
    return urllib.request.build_opener(_PinnedHTTPHandler(), _PinnedHTTPSHandler(), redirect)


def _resolve_redirect_chain(url, cfg):
    """H3：进入 Edge 前，用 _SafeRedirectHandler 逐跳校验地解析 URL，返回「已校验的最终 URL」。

    返回 (final_url, error_type, reason)：
      - 成功：final_url 为通过逐跳校验的最终 URL，error_type="" ；
      - 任一跳被拒（内网 / 元数据 / scheme 等）：final_url=None, error_type="url_denied" ；
      - 无法完成解析（网络失败）：final_url=None, error_type="resolve_failed" ；
      - 非重定向的 HTTP 错误（如 403 反爬）：不阻断，返回 (url, "", "") 交由 Edge 尝试。

    边界（如实标注）：仅覆盖**服务端 HTTP 3xx** 重定向链；JS / meta-refresh 等**客户端**跳转
    无法经服务端逐跳复检覆盖 —— Edge 渲染阶段发起的这类跳转仍不复检（见 _render_via_edge）。
    本函数只读 1 字节即关闭连接，不取正文（仅用于拿到 final_url）。
    """
    opener = _build_opener(cfg)
    req = urllib.request.Request(url, headers={"User-Agent": cfg["user_agent"],
                                               "Accept": "text/html,application/xhtml+xml,*/*"})
    try:
        with opener.open(req, timeout=cfg["timeout_seconds"]) as resp:
            final_url = resp.geturl() or url
            try:
                resp.read(1)   # 触发潜在延迟错误；只读 1 字节，不取正文
            except Exception:
                pass
        return final_url, "", ""
    except _RedirectDenied as e:
        return None, "url_denied", str(e)
    except urllib.error.HTTPError as e:
        if e.code in (301, 302, 303, 307, 308):
            return None, "url_denied", f"redirect_rejected:HTTP {e.code}"
        return url, "", ""     # 非重定向 HTTP 错误：不作为拒绝，交由 Edge 尝试渲染
    except Exception as e:
        return None, "resolve_failed", f"{type(e).__name__}: {e}"


class _TextExtractor(HTMLParser):
    """抽取标题与可见正文，剔除 script/style/noscript/head。"""

    VOID_SKIP = {"script", "style", "noscript", "iframe"}  # 不含 head：title 需抽取

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._skip = 0
        self._in_title = False
        self.title = ""
        self._buf = []
        self.links = []
        self._seen = set()

    def handle_starttag(self, tag, attrs):
        if tag in self.VOID_SKIP:
            self._skip += 1
        if tag == "title":
            self._in_title = True
        if tag == "a":
            d = dict(attrs)
            href = d.get("href")
            if href and href not in self._seen:
                self._seen.add(href)
                self.links.append(href)

    def handle_endtag(self, tag):
        if tag in self.VOID_SKIP and self._skip > 0:
            self._skip -= 1
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._skip > 0:
            return
        if self._in_title:
            self.title += data
        else:
            if data.strip():
                self._buf.append(data)

    def text(self):
        raw = " ".join(self._buf)
        raw = " ".join(raw.split())
        return raw


def _clean_url(u):
    return u.strip()


def _robots_allowed(url, ua, timeout, opener):
    """读取 robots.txt 并按 ua 判定；用带 timeout 的 opener，避免无超时挂死。"""
    try:
        p = urllib.parse.urlparse(url)
        robots_url = f"{p.scheme}://{p.netloc}/robots.txt"
        if not _check_url(robots_url)[0]:
            return True  # 与入口同 host，理论不可达；不阻断
        req = urllib.request.Request(robots_url, headers={"User-Agent": ua})
        with opener.open(req, timeout=timeout) as resp:
            raw = resp.read(65536)
        data = raw.decode("utf-8", "ignore")
        rp = urllib.robotparser.RobotFileParser()
        rp.parse(data.splitlines())
        return rp.can_fetch(ua, url)
    except _RedirectDenied:
        return True
    except Exception:
        return True  # 取不到 robots 不阻断，仅记录


# Edge 探测/渲染的一次性状态缓存（C5）：进程内复用，避免每请求重复探测、重复超时等待
_EDGE_BIN_CACHE = []              # 缓存探测结果（可能是 None）
_EDGE_DISABLED = False            # Edge 渲染异常/超时一次后置位，后续请求直接回退 urllib
EDGE_TIMEOUT_GRACE_SECONDS = 25   # Edge 无头渲染在 cfg.timeout 之外的附加预算


def _detect_edge_binary():
    """检测本机已安装的 Microsoft Edge 可执行文件；未安装返回 None。

    仅做本地探测，绝不触发任何浏览器下载（不引入 playwright/selenium）。
    结果在**进程内缓存**（C5），避免每次抓取都重复做路径探测。
    """
    if _EDGE_BIN_CACHE:
        return _EDGE_BIN_CACHE[0]
    if sys.platform.startswith("win"):
        base_x86 = os.environ.get("ProgramFiles(x86)") or r"C:\Program Files (x86)"
        base = os.environ.get("ProgramFiles") or r"C:\Program Files"
        candidates = [
            os.path.join(base_x86, "Microsoft", "Edge", "Application", "msedge.exe"),
            os.path.join(base, "Microsoft", "Edge", "Application", "msedge.exe"),
        ]
    elif sys.platform == "darwin":
        candidates = ["/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"]
    else:  # linux
        candidates = ["microsoft-edge", "microsoft-edge-stable", "msedge"]
    found = None
    for c in candidates:
        if os.path.isfile(c):
            found = c
            break
        found = shutil.which(c)
        if found:
            break
    _EDGE_BIN_CACHE.append(found)
    return found


def _render_via_edge(url, cfg, ua, timeout):
    """用本机已安装的 Edge 以无头模式渲染页面并回传 DOM 文本。

    安全（F-003）：默认**不**加 `--no-sandbox`（保留渲染进程沙箱，需在
    contract.yaml 显式 `allow_no_sandbox: true` 才开启）；每次调用分配一次性
    `--user-data-dir` 临时 profile，结束后清理，避免复用用户默认登录态 / 争用锁。

    信任边界（C6，如实描述）：入参 url 应为**已经过 _check_url、且经 _SafeRedirectHandler
    逐跳解析到最终 URL** 的目标（见 _resolve_redirect_chain）。Edge 渲染阶段**自身**发起的
    跳转（JS / meta-refresh 等客户端跳转，及其后的 HTTP 302）**不再逐跳复检**（与 urllib 路径
    的 _SafeRedirectHandler 不同）。因此「JS / meta-refresh 重定向的逐跳校验」在本分支不适用，
    上游不应据此宣称 SSRF 已完全阻断。

    任意失败（未安装 / 超时 / 无输出）均返回 None，由调用方回退 urllib。失败会**打印一行
    纯文本提示并（异常/超时情况下）在进程内禁用后续 Edge 尝试**（C5），避免每次抓取都
    静默叠加一次超时等待。
    """
    global _EDGE_DISABLED
    if _EDGE_DISABLED:
        return None  # 本进程已确认 Edge 不可用，直接回退（C5）
    binp = _detect_edge_binary()
    if not binp:
        return None
    profile_dir = None
    try:
        profile_dir = tempfile.mkdtemp(prefix="wes_edge_profile_")
        flags = ["--headless=new", "--disable-gpu", "--disable-extensions",
                 "--disable-background-networking", "--no-first-run",
                 "--no-default-browser-check", f"--user-data-dir={profile_dir}",
                 "--timeout=15000", "--virtual-time-budget=8000",
                 f"--user-agent={ua}", "--dump-dom"]
        if cfg.get("allow_no_sandbox"):
            # 显式开关：仅 root/容器环境按需开启；开启即放弃渲染进程沙箱
            flags.insert(1, "--no-sandbox")
        cmd = [binp] + flags + [url]
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              timeout=timeout + EDGE_TIMEOUT_GRACE_SECONDS)
        dom = proc.stdout or ""
        if not dom.strip():
            # 渲染成功但无 DOM：可能是本页特例，仅提示、不禁用（C5）
            print("[WARN] edge render returned empty DOM, fallback to urllib",
                  file=sys.stderr)
            return None
        return dom
    except Exception as e:  # noqa: BLE001
        # 未安装之外的运行期失败（超时/崩溃）：提示并按进程禁用，避免重复等待（C5）
        _EDGE_DISABLED = True
        print(f"[WARN] edge render unavailable ({type(e).__name__}), fallback to urllib",
              file=sys.stderr)
        return None
    finally:
        if profile_dir:
            shutil.rmtree(profile_dir, ignore_errors=True)


def fetch(url, cfg, respect_robots=None):
    """稳健抓取：URL 准入 + 超时 + 重试退避 + 编码容错 + robots。返回 dict。"""
    url = _clean_url(url)
    # 统一入口闸门：任何 URL 先过 _check_url（urllib 与 Edge 两条路径之前）
    allow, why = _check_url(url)
    if not allow:
        return {"ok": False, "url": url, "error_type": "url_denied", "error": why}
    if respect_robots is None:
        respect_robots = cfg["respect_robots"]
    opener = _build_opener(cfg)
    if respect_robots and not _robots_allowed(url, cfg["user_agent"], cfg["timeout_seconds"], opener):
        return {"ok": False, "url": url, "error_type": "robots_disallowed",
                "error": "robots.txt disallows this URL"}

    # 浏览器渲染优先：本机已安装 Edge 时，先无头渲染取 DOM（解决 SPA/反爬页面的空正文异常）
    prefer = str(cfg.get("prefer_browser", "")).strip().lower()
    if prefer in ("edge", "edge_first"):
        # H3：进入 Edge 前先用 _SafeRedirectHandler 逐跳校验解析 HTTP 3xx 重定向链，
        # 只把「已通过校验的最终 URL」交给 Edge；任一跳被拒（内网/元数据/scheme）→
        # 直接 url_denied，不进 Edge。无法完成解析（网络失败）则不赌 Edge，回退 urllib。
        edge_url, e_type, e_why = _resolve_redirect_chain(url, cfg)
        if e_type == "url_denied":
            return {"ok": False, "url": url, "error_type": "url_denied", "error": e_why}
        if e_type == "" and edge_url:
            dom = _render_via_edge(edge_url, cfg, cfg["user_agent"], cfg["timeout_seconds"])
            if dom:
                ex = _TextExtractor()
                ex.feed(dom)
                text = ex.text()
                if text:
                    return {"ok": True, "url": url, "final_url": edge_url, "status": 200,
                            "title": ex.title.strip(), "text": text[:cfg["max_bytes"]],
                            "links": ex.links, "bytes": len(dom.encode("utf-8", "ignore")),
                            "rendered_by": "edge"}
                # 渲染成功但无可见正文，继续走 urllib 兜底

    headers = {"User-Agent": cfg["user_agent"], "Accept": "text/html,application/xhtml+xml,*/*"}
    last_err = None
    for attempt in range(cfg["retries"] + 1):
        try:
            req = urllib.request.Request(url, headers=headers)
            with opener.open(req, timeout=cfg["timeout_seconds"]) as resp:
                final_url = resp.geturl()
                ctype = resp.headers.get("Content-Type", "")
                raw = resp.read(cfg["max_bytes"])
                # 编码容错
                charset = "utf-8"
                m = re.search(r"charset=([\w-]+)", ctype, re.I)
                if m:
                    charset = m.group(1)
                try:
                    body = raw.decode(charset, errors="replace")
                except (LookupError, UnicodeError):
                    body = raw.decode("utf-8", errors="replace")
                if "html" not in ctype.lower() and "<html" not in body[:512].lower():
                    return {"ok": False, "url": url, "final_url": final_url,
                            "error_type": "non_html", "error": f"content-type={ctype}"}
                ex = _TextExtractor()
                ex.feed(body)
                text = ex.text()
                if not text:
                    return {"ok": False, "url": url, "final_url": final_url,
                            "error_type": "empty_body", "error": "no visible text extracted"}
                return {"ok": True, "url": url, "final_url": final_url,
                        "status": getattr(resp, "status", 200), "title": ex.title.strip(),
                        "text": text[:cfg["max_bytes"]], "links": ex.links, "bytes": len(raw)}
        except _RedirectDenied as e:
            # 逐跳重定向校验拒绝（重定向到内网 / 重定向被禁用）
            return {"ok": False, "url": url, "error_type": "url_denied", "error": str(e)}
        except urllib.error.HTTPError as e:
            # OBS-1 归一：重定向因目标 scheme 不被允许 / 超出 max_redirects 被拒时，
            # urllib 抛 3xx HTTPError；统一归入拒绝类 url_denied，避免上游误判为网络故障而重试
            if e.code in (301, 302, 303, 307, 308):
                return {"ok": False, "url": url, "error_type": "url_denied",
                        "error": f"redirect_rejected:HTTP {e.code}:{getattr(e, 'reason', '')}"}
            last_err = ("http_error", f"HTTP {e.code}")
            if e.code in (403, 404, 410):  # 确定性失败，不重试
                return {"ok": False, "url": url, "error_type": "http_error", "error": f"HTTP {e.code}"}
        except (urllib.error.URLError, socket.timeout, http.client.HTTPException, ConnectionError) as e:
            last_err = ("network_timeout", str(e))
        except Exception as e:  # 兜底：绝不裸奔崩溃
            last_err = ("unknown", f"{type(e).__name__}: {e}")
        if attempt < cfg["retries"]:
            time.sleep(cfg["backoff_base_seconds"] * (2 ** attempt))
    et, em = last_err or ("unknown", "unknown")
    return {"ok": False, "url": url, "error_type": et, "error": em}


def _within(p, base):
    """判断 realpath p 是否落在 realpath base 之内（含相等）。

    C4 修复：base 与 p 均先 realpath/abspath 规范化，再用 `commonpath([base,p])==base`
    判定（对边界、符号链接、`..` 均正确；不同盘/异常时 ValueError 回退为 False）。
    若 base 归一后为空或等于文件系统根（os.sep，即 `/`），视为**无效锚点**一律返回 False
    —— 不得把 `/` 当工作区（否则 CWD=`/` 时退化为全盘放行）。
    """
    base = os.path.realpath(os.path.abspath(base))
    p = os.path.realpath(os.path.abspath(p))
    if not base or base == os.sep:
        return False
    try:
        return os.path.commonpath([base, p]) == base
    except ValueError:
        return False


def _effective_allow_dirs(cli_dirs, cfg):
    """计算 --from-file 的有效允许根（F-GAP-02 收敛）。

    允许根 = CWD ∪ PKG_ROOT ∪ contract.from_file_allow_dirs
              ∪（仅那些 realpath 落在 CWD 或 PKG_ROOT 之内的 --allow-dir 取值）。
    **两个来源（contract 与 CLI）都须落在工作区锚点（CWD ∪ PKG_ROOT）内才生效**——单个
    参数无法把边界放宽到项目工作区之外（C3：contract 通道此前未做包含校验，与
    contract.yaml:16-19 及 SKILL.md 的宣称不符）。

    返回 (roots, rejected)：rejected 为越出项目工作区而被拒绝的原始值（含 contract 与 CLI）。
    """
    # 无效锚点（规范化后为空或等于文件系统根 `/`）不纳入，避免 CWD=`/` 时全盘放行（C4）
    anchors = [a for a in (os.path.realpath(os.path.abspath(os.getcwd())),
                           os.path.realpath(os.path.abspath(PKG_ROOT)))
               if a and a != os.sep]
    roots = list(anchors)
    rejected = []
    # contract 通道：同样须落在锚点内才生效
    extra = cfg.get("from_file_allow_dirs") or ""
    if isinstance(extra, str):
        for d in extra.split(","):
            d = d.strip()
            if not d:
                continue
            real = os.path.realpath(os.path.abspath(d))
            if any(_within(real, a) for a in anchors):
                roots.append(real)
            else:
                rejected.append(d)
    # CLI 通道
    for d in (cli_dirs or []):
        real = os.path.realpath(os.path.abspath(d))
        if any(_within(real, a) for a in anchors):
            roots.append(real)
        else:
            rejected.append(d)
    seen, uniq = set(), []
    for r in roots:
        if r not in seen:
            seen.add(r)
            uniq.append(r)
    return uniq, rejected


def _resolve_from_file(path, cfg, roots):
    """--from-file 硬化闸门：限定工作区目录 + 大小上限 + 拒绝二进制。

    返回 (ok, reason, error_type, realpath)。
    """
    try:
        real = os.path.realpath(os.path.abspath(path))
    except Exception as e:
        return False, f"{type(e).__name__}: {e}", "unknown", None
    if not any(_within(real, b) for b in roots):
        return False, f"path_outside_allowlist:{real}", "path_denied", None
    if not os.path.isfile(real):
        return False, "not_a_regular_file", "path_denied", None
    try:
        size = os.path.getsize(real)
    except OSError as e:
        return False, f"{type(e).__name__}: {e}", "unknown", None
    if size > cfg["from_file_max_bytes"]:
        return False, f"file_too_large:{size}", "file_too_large", None
    try:
        with open(real, "rb") as fh:
            head = fh.read(4096)
    except Exception as e:
        return False, f"{type(e).__name__}: {e}", "unknown", None
    if b"\x00" in head:
        return False, "binary_content", "non_text_file", None
    return True, "", "", real


def extract_file(path, cfg, allow_dirs=None):
    """从本地 HTML 文件抽取正文（供 browser-skill 渲染后的页面回灌）。返回 dict。

    统一入口闸门：① 拒绝伪装成 URL 的入参；② 校验 --allow-dir 不得越出项目工作区；
    ③ 路径白名单 / 大小 / 二进制检查。
    """
    # 闸门①：显式拒绝 URL 形态入参（复用统一 URL 准入 _check_url）
    if "://" in (path or ""):
        allow, why = _check_url(path)
        if not allow:
            return {"ok": False, "file": path, "error_type": "url_denied", "error": why}
        return {"ok": False, "file": path, "error_type": "url_denied",
                "error": "from-file does not fetch URLs; pass the URL as a positional arg"}
    # 闸门②：--allow-dir 不得越出项目工作区（消除注入放大面）
    roots, rejected = _effective_allow_dirs(allow_dirs, cfg)
    if rejected:
        return {"ok": False, "file": path, "error_type": "path_denied",
                "error": "allow_dir_outside_project:" + ",".join(rejected) +
                         " (允许目录不得越出项目工作区 CWD/PKG_ROOT)"}
    # 闸门③：路径白名单 + 大小上限 + 拒绝二进制
    ok, why, etype, real = _resolve_from_file(path, cfg, roots)
    if not ok:
        return {"ok": False, "file": path, "error_type": etype, "error": why}
    try:
        with open(real, "rb") as fh:
            raw = fh.read(cfg["from_file_max_bytes"] + 1)
    except Exception as e:
        return {"ok": False, "file": path, "error_type": "unknown",
                "error": f"{type(e).__name__}: {e}"}
    charset = "utf-8"
    m = re.search(r"charset=[\"']?([\w-]+)", raw[:2048].decode("latin-1", "ignore"), re.I)
    if m:
        charset = m.group(1)
    try:
        body = raw.decode(charset, errors="replace")
    except (LookupError, UnicodeError):
        body = raw.decode("utf-8", errors="replace")
    ex = _TextExtractor()
    ex.feed(body)
    text = ex.text()
    if not text:
        return {"ok": False, "file": path, "error_type": "empty_body",
                "error": "no visible text extracted"}
    return {"ok": True, "file": path, "title": ex.title.strip(),
            "text": text[:cfg["max_bytes"]], "links": ex.links, "bytes": len(raw)}


def self_test():
    """离线自测：正文抽取器 + URL 准入 + IANA 网段边界 + 钉 IP 登记 + Edge 探测/回退（不联网）。"""
    sample = (
        "<!DOCTYPE html><html><head><title>测试页</title>"
        "<style>.x{color:red}</style><script>var a=1;</script></head>"
        "<body><h1>标题</h1><p>第一段正文。</p>"
        "<p>第二段<b>加粗</b>正文。</p>"
        '<a href="/a">链接A</a><a href="https://x.com/b">链接B</a>'
        "</body></html>"
    )
    ex = _TextExtractor()
    ex.feed(sample)
    text = ex.text()
    ok_extract = (ex.title.strip() == "测试页") and ("第一段正文" in text) and ("加粗" in text) \
        and ("var a=1" not in text) and (len(ex.links) == 2)

    # URL 准入：scheme / 主机 / 非 http(s)（离线）
    deny_urls = [
        "file:///etc/passwd", "ftp://example.com/", "gopher://example.com/",
        "data:text/html,x", "javascript:alert(1)", "http://127.0.0.1/",
        "http://10.0.0.1/", "http://192.168.1.1/", "http://169.254.169.254/",
        "http://100.100.100.200/", "http://localhost/", "http://[::1]/",
        "http://[fc00::1]/", "http://[fe80::1]/", "http://2130706433/",
    ]
    ok_guard = all(not _check_url(u)[0] for u in deny_urls)
    # 公网字面 IP 必须放行（不触发 DNS，离线可判）
    ok_guard = ok_guard and _check_url("https://93.184.216.34/")[0]

    # IANA 网段边界（F-GAP-01 永久守门）—— 必须 DENY / 必须 ALLOW
    deny_ips = ["100.100.100.200", "100.64.0.0", "100.127.255.255", "0.0.0.0",
                "10.1.2.3", "127.0.0.1", "169.254.169.254", "172.16.5.5",
                "192.0.0.1", "192.0.2.1", "192.88.99.1", "192.168.1.1",
                "198.18.0.1", "198.51.100.1", "203.0.113.1", "224.0.0.1",
                "255.255.255.255", "::", "::1", "100::1", "2001:db8::1",
                "fc00::1", "fe80::1", "ff02::1", "::ffff:127.0.0.1", "::ffff:7f00:1"]
    allow_ips = ["100.63.255.255", "100.128.0.0", "8.8.8.8", "93.184.216.34"]
    ok_cidr = (all(_ip_blocked(ipaddress.ip_address(x)) for x in deny_ips)
               and all(not _ip_blocked(ipaddress.ip_address(x)) for x in allow_ips))

    # H4：连接层钉 IP 的登记 / 取用管线（纯内存，离线可判，不联网）
    _pin_host("Example.COM", [("fam", 1, 6, "93.184.216.34")])
    ok_pin = (_pinned_for("example.com") == [("fam", 1, 6, "93.184.216.34")]
              and _hostname_of("example.com:8443") == "example.com"
              and _hostname_of("[::1]:80") == "::1"
              and _pinned_for("unpinned.example") is None)

    # F4 / D6：Edge 探测 / 禁用回退分支的**离线**回归断言（不联网，不起真实渲染进程）
    global _EDGE_DISABLED
    saved_cache, saved_disabled = list(_EDGE_BIN_CACHE), _EDGE_DISABLED
    edge_fallback = True
    try:
        probe_cfg = dict(DEFAULTS)
        probe_url = "https://example.invalid/"
        # ① 未安装 Edge（探测缓存置为 None）→ 回退 None，不抛异常、不 spawn、不联网
        del _EDGE_BIN_CACHE[:]
        _EDGE_BIN_CACHE.append(None)
        _EDGE_DISABLED = False
        edge_fallback = edge_fallback and (_detect_edge_binary() is None)
        edge_fallback = edge_fallback and (
            _render_via_edge(probe_url, probe_cfg, probe_cfg["user_agent"], 1) is None)
        # ② 进程内已禁用 → 短路回退 None（连探测都不做）
        _EDGE_DISABLED = True
        edge_fallback = edge_fallback and (
            _render_via_edge(probe_url, probe_cfg, probe_cfg["user_agent"], 1) is None)
        # ③ 二进制路径不存在 → 运行期失败 → 回退 None 且置禁用，不抛异常、不联网
        del _EDGE_BIN_CACHE[:]
        _EDGE_BIN_CACHE.append(os.path.join(tempfile.gettempdir(), "wes_no_such_edge_bin_xyz"))
        _EDGE_DISABLED = False
        r3 = _render_via_edge(probe_url, probe_cfg, probe_cfg["user_agent"], 1)
        edge_fallback = edge_fallback and (r3 is None) and (_EDGE_DISABLED is True)
    except Exception:
        edge_fallback = False
    finally:
        del _EDGE_BIN_CACHE[:]
        _EDGE_BIN_CACHE.extend(saved_cache)
        _EDGE_DISABLED = saved_disabled

    ok = ok_extract and ok_guard and ok_cidr and ok_pin and edge_fallback
    print(json.dumps({"self_test": "pass" if ok else "fail",
                      "extractor": ok_extract, "url_guard": ok_guard, "cidr_boundary": ok_cidr,
                      "pin_map": ok_pin, "edge_fallback": edge_fallback,
                      "title": ex.title.strip(), "links": ex.links,
                      "text_len": len(text)}, ensure_ascii=False, indent=2))
    sys.exit(0 if ok else 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url", nargs="?")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--no-robots", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--from-file", metavar="HTML", default=None,
                    help="从本地 HTML 文件抽取正文（供 browser-skill 渲染后回灌）")
    ap.add_argument("--allow-dir", action="append", default=[], metavar="DIR",
                    help="扩展 --from-file 允许目录（仅当 realpath 落在项目工作区 CWD/PKG_ROOT 内时生效）")
    args = ap.parse_args()
    if args.self_test:
        self_test()
    if args.url is None and args.from_file is None:
        self_test()  # 完全不带参数 → 既有便捷行为：跑自测
    cfg = load_cfg()
    if args.from_file is not None:
        if not args.from_file.strip():
            res = {"ok": False, "file": args.from_file, "error_type": "bad_args",
                   "error": "empty --from-file value (omit args to run --self-test)"}
        else:
            res = extract_file(args.from_file, cfg, allow_dirs=args.allow_dir)
    else:
        if not (args.url or "").strip():
            res = {"ok": False, "url": args.url, "error_type": "bad_args",
                   "error": "empty url value (omit args to run --self-test)"}
        else:
            res = fetch(args.url, cfg, respect_robots=not args.no_robots)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    sys.exit(0 if res.get("ok") else 1)


if __name__ == "__main__":
    main()
