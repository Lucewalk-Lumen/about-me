#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
search.py — 尽力式公开检索（零第三方依赖）

通过 DuckDuckGo lite HTML 端点做尽力检索，解析结果链接与摘要，输出结构化 JSON。
网络不可达 / 被限流时优雅失败（error_type=network_timeout / parse_error），不崩溃。
不保证结果完整性——它是 WebSearch / WebFetch 之外的兜底采集脚本。

安全（F-001 侧翼收口）：返回的每条 `results[].url` 亦过统一 URL 准入 `_check_url`，
拒绝 file:// / 内网 / 回环 / 链路本地 / 云元数据等，避免经搜索结果侧重新打回 SSRF。

用法：
  python search.py "<query>" [--max N] [--json]
  python search.py --self-test        # 离线自测（参数解析 + URL 准入 + 网络失败结构化）
"""
import sys
import os
import json
import socket
import ipaddress
import argparse
import urllib.request
import urllib.parse
import urllib.error
import http.client
import re
import html
from html.parser import HTMLParser

HERE = os.path.dirname(os.path.abspath(__file__))
CONTRACT = os.path.join(HERE, "..", "contract.yaml")

# ── 安全闸门常量（与 crawler.py 口径一致） ─────────────────────────
ALLOWED_SCHEMES = ("http", "https")
# IANA 特殊用途网段黑名单（显式列出，版本无关）；属性判据仅作兜底
_BLOCKED_V4 = tuple(ipaddress.ip_network(n) for n in (
    "0.0.0.0/8", "10.0.0.0/8", "100.64.0.0/10", "127.0.0.0/8",
    "169.254.0.0/16", "172.16.0.0/12", "192.0.0.0/24", "192.0.2.0/24",
    "192.88.99.0/24", "192.168.0.0/16", "198.18.0.0/15", "198.51.100.0/24",
    "203.0.113.0/24", "224.0.0.0/4", "240.0.0.0/4",
))
_BLOCKED_V6 = tuple(ipaddress.ip_network(n) for n in (
    "::/128", "::1/128", "100::/64", "2001:db8::/32",
    "64:ff9b::/96",   # NAT64 知名前缀（DNS64 环境可映射内网，C11/L8）
    "fc00::/7", "fe80::/10", "ff00::/8",
))
_IPV4_MAPPED_NET = ipaddress.ip_network("::ffff:0:0/96")
CLOUD_METADATA_IPS = ("169.254.169.254", "100.100.100.200", "fd00:ec2::254")

DEFAULTS = {
    "endpoint": "https://lite.duckduckgo.com/lite/",
    "max_results": 10,
    "timeout_seconds": 15,
    "user_agent": "Mozilla/5.0 (compatible; workbuddy-expert-studio-web-crawler/1.0.2; +https://workbuddy.cn)",
}


def _strip_comment(v):
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
    """从 contract.yaml 读取 search 段；极简解析兜底（支持行内注释与引号）。"""
    cfg = dict(DEFAULTS)
    try:
        with open(os.path.abspath(CONTRACT), encoding="utf-8") as fh:
            txt = fh.read()
        in_block = False
        for line in txt.splitlines():
            if line.strip().startswith("search:"):
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


# ── 安全闸门：URL 准入（与 crawler._check_url 同口径，自包含以便单脚本运行） ──

def _unmap_v4(ip):
    """若为 IPv4-mapped IPv6（::ffff:a.b.c.d）返回其 IPv4Address，否则 None（兼容 Python 3.9）。"""
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
    IPv4-mapped IPv6 先解映射后按 v4 复检。
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
    return bool(ip.is_private or ip.is_loopback or ip.is_link_local
                or ip.is_reserved or ip.is_multicast or ip.is_unspecified)


# ── H4：DNS 重绑定防护 —— 连接层「钉 IP」（与 crawler.py 同口径，自包含以便单脚本运行） ──
# 校验时（_check_url）保存解析快照；连接时直接使用快照中的 IP 建连，不再二次解析主机名，
# 消除「校验 → 连接」之间的 TOCTOU 窗口。TLS 的 SNI / 证书校验仍用主机名（不放松 TLS）。
_PINNED_ADDRS = {}  # {hostname_lower: [(family, socktype, proto, ip_str), ...]}


def _pin_host(host, infos):
    if not host or not infos:
        return
    _PINNED_ADDRS[host.lower()] = list(infos)


def _pinned_for(host):
    if not host:
        return None
    return _PINNED_ADDRS.get(host.lower())


def _hostname_of(netloc):
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
    def http_open(self, req):
        return self.do_open(_PinnedHTTPConnection, req,
                            pinned=_pinned_for(_hostname_of(getattr(req, "host", ""))))


class _PinnedHTTPSHandler(urllib.request.HTTPSHandler):
    def https_open(self, req):
        return self.do_open(_PinnedHTTPSConnection, req, context=self._context,
                            pinned=_pinned_for(_hostname_of(getattr(req, "host", ""))))


def _build_opener():
    """构造连接层钉 IP 的 opener（H4）。"""
    return urllib.request.build_opener(_PinnedHTTPHandler(), _PinnedHTTPSHandler())


_SEARCH_OPENER = None


def _get_opener():
    global _SEARCH_OPENER
    if _SEARCH_OPENER is None:
        _SEARCH_OPENER = _build_opener()
    return _SEARCH_OPENER


def _check_url(u):
    """URL 准入闸门：返回 (ok: bool, reason: str)。规则见 crawler.py 同名函数。"""
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
    try:
        if _ip_blocked(ipaddress.ip_address(host)):
            return False, f"internal_ip:{host}"
        return True, ""
    except ValueError:
        pass
    try:
        infos = socket.getaddrinfo(host, None)
    except Exception as e:
        return False, f"dns_failed:{type(e).__name__}"
    pinned = []
    try:
        for info in infos:
            ip = ipaddress.ip_address(info[4][0])
            if _ip_blocked(ip):
                return False, f"internal_ip_resolved:{info[4][0]}"
            pinned.append((info[0], info[1], info[2], info[4][0]))
    except Exception as e:
        return False, f"dns_failed:{type(e).__name__}"
    # H4：登记「通过校验的解析快照」为连接层钉定目标（连接时不再解析）
    _pin_host(host, pinned)
    return True, ""


class _ResultParser(HTMLParser):
    """从 DuckDuckGo lite 结果页抽取 (标题, 链接, 摘要)。

    兼容两种结果标记结构：
      • A：摘要 `td.result-snippet` **嵌在**结果 `<a class="result-link">` 内部；
      • B：摘要 `td.result-snippet` **位于**结果 `<a>` 之后的独立行（DDG-lite 真实结构，
           即「链接行 + 摘要行」的两行 table）。
    摘要是否可得仍取决于来源页面的标记结构，取不到时 `snippet` 为空串（不构成错误）。
    结果在「下一个 result-link 开始」或 `close()` 时结算（不再在 `</a>` 处结算，
    否则结构 B 的摘要 td 到来时 _cur 已被清空，摘要将恒为空）。
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.results = []
        self._cur = None
        self._grab = None  # 'title' | 'snippet'
        self._buf = []

    def _flush(self):
        if self._cur is not None and self._cur.get("url"):
            self.results.append(self._cur)
        self._cur = None

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        cls = d.get("class", "")
        if tag == "a" and "result-link" in cls:
            href = d.get("href", "")
            if href and href.startswith("http"):
                self._flush()  # 新结果开始 → 先结算上一个
                self._cur = {"title": "", "url": href, "snippet": ""}
                self._grab = "title"
                self._buf = []
        elif tag == "td" and "result-snippet" in cls and self._cur is not None:
            if self._grab == "title":  # 结构 A：标题文本被摘要 td 打断 → 先落标题
                self._cur["title"] = " ".join("".join(self._buf).split())
            self._grab = "snippet"
            self._buf = []

    def handle_endtag(self, tag):
        if tag in ("a", "td") and self._grab:
            text = " ".join("".join(self._buf).split())
            if self._cur is not None and text:
                self._cur[self._grab] = text
            self._grab = None
            self._buf = []

    def handle_data(self, data):
        if self._grab:
            self._buf.append(data)

    def close(self):
        super().close()  # 先冲尽解析器缓冲（尾部的标签/文本）
        self._flush()    # 再结算最后一个结果


def search(query, cfg, max_results=None):
    max_results = max_results or cfg["max_results"]
    data = urllib.parse.urlencode({"q": query, "kl": "cn-zh"}).encode("utf-8")
    req = urllib.request.Request(cfg["endpoint"], data=data,
                                 headers={"User-Agent": cfg["user_agent"],
                                          "Content-Type": "application/x-www-form-urlencoded"})
    try:
        with _get_opener().open(req, timeout=cfg["timeout_seconds"]) as resp:
            body = resp.read(2_000_000).decode("utf-8", errors="replace")
    except (urllib.error.URLError, socket.timeout, ConnectionError, OSError) as e:
        return {"ok": False, "query": query, "error_type": "network_timeout",
                "error": str(e), "results": []}
    try:
        p = _ResultParser()
        p.feed(body)
        p.close()  # 结算最后一个结果（结果不再在 </a> 处结算）
        results = p.results[:max_results]
        if not results:
            return {"ok": False, "query": query, "error_type": "parse_error",
                    "error": "no results parsed (endpoint may have changed or rate-limited)",
                    "results": []}
        # 安全闸门：逐条结果 URL 过 _check_url，拒绝内网 / file:// 等
        kept, denied = [], 0
        for r in results:
            if _check_url(r.get("url", ""))[0]:
                kept.append(r)
            else:
                denied += 1
        if not kept:
            return {"ok": False, "query": query, "error_type": "url_denied",
                    "error": f"all {denied} result URLs rejected by URL guard",
                    "results": []}
        return {"ok": True, "query": query, "count": len(kept),
                "filtered_out": denied, "results": kept}
    except Exception as e:
        return {"ok": False, "query": query, "error_type": "parse_error",
                "error": f"{type(e).__name__}: {e}", "results": []}


def self_test():
    """离线自测：参数解析 + URL 准入 + 结果解析 + 网络失败返回结构化错误（不触外网）。"""
    ok = True
    details = {}

    # ① argparse 可用（缺 import argparse 时此前必然 NameError）
    try:
        ap = argparse.ArgumentParser()
        ap.add_argument("query")
        ap.add_argument("--max", type=int, default=None)
        ns = ap.parse_args(["self test query", "--max", "3"])
        details["argparse"] = (ns.query == "self test query" and ns.max == 3)
    except Exception as e:
        details["argparse"] = f"error:{type(e).__name__}"
    ok = ok and details["argparse"] is True

    # ② URL 准入：拒绝 file / 内网 / 回环 / 链路本地 / 云元数据 / 非 http(s)；放行公网字面 IP
    deny_cases = ["file:///etc/passwd", "ftp://example.com/", "http://127.0.0.1/",
                  "http://10.0.0.1/", "http://169.254.169.254/latest/meta-data/",
                  "http://100.100.100.200/", "http://localhost/"]
    guard = all(not _check_url(u)[0] for u in deny_cases) and _check_url("https://93.184.216.34/")[0]
    details["url_guard"] = guard
    ok = ok and guard

    # ②b IANA 网段边界（F-GAP-01 守门）：CGNAT 必拒，紧邻公网段必放
    deny_ips = ["100.100.100.200", "100.64.0.0", "100.127.255.255",
                "127.0.0.1", "169.254.169.254", "192.168.1.1", "198.18.0.1",
                "240.0.0.1", "::1", "fc00::1", "fe80::1", "::ffff:127.0.0.1"]
    allow_ips = ["100.63.255.255", "100.128.0.0", "8.8.8.8"]
    cidr = (all(_ip_blocked(ipaddress.ip_address(x)) for x in deny_ips)
            and all(not _ip_blocked(ipaddress.ip_address(x)) for x in allow_ips))
    details["cidr_boundary"] = cidr
    ok = ok and cidr

    # ③ 结果解析器：结构 A（摘要 td 在 <a> 内）与结构 B（摘要 td 在 <a> 之后）都必须取到摘要
    sample_a = ('<a class="result-link" href="https://93.184.216.34/a">标题A'
                '<td class="result-snippet">摘要A</td></a>')
    sample_b = ('<a class="result-link" href="https://93.184.216.34/b">标题B</a>'
                '<td class="result-snippet">摘要B</td>')
    pa = _ResultParser()
    pa.feed(sample_a)
    pa.close()
    p = _ResultParser()
    p.feed(sample_b)
    p.close()
    parsed = (len(pa.results) == 1 and pa.results[0]["snippet"] == "摘要A"
              and len(p.results) == 1 and p.results[0]["snippet"] == "摘要B"
              and p.results[0]["url"].startswith("https://"))
    details["parser_structures_AB"] = parsed
    ok = ok and parsed

    # ③b 结构兼容改造不得放松 URL 准入：解析出的内网 / 云元数据 URL 仍必须被闸门拒绝
    blocked_sample = (
        '<a class="result-link" href="http://127.0.0.1/x">b1</a><td class="result-snippet">s</td>'
        '<a class="result-link" href="http://169.254.169.254/m">b2</a><td class="result-snippet">s</td>'
        '<a class="result-link" href="http://100.100.100.200/m">b3</a><td class="result-snippet">s</td>'
        '<a class="result-link" href="https://93.184.216.34/ok">ok</a><td class="result-snippet">s</td>')
    pg = _ResultParser()
    pg.feed(blocked_sample)
    pg.close()
    urls = [r["url"] for r in pg.results]
    denied = [u for u in urls if not _check_url(u)[0]]
    allowed = [u for u in urls if _check_url(u)[0]]
    guard_after_parse = (len(urls) == 4 and len(denied) == 3
                         and allowed == ["https://93.184.216.34/ok"])
    details["url_guard_after_parse"] = guard_after_parse
    ok = ok and guard_after_parse

    # ④ 网络失败必须返回结构化错误而非 traceback（连本机 1 端口，拒绝连接，不触外网）
    try:
        r = search("x", {"endpoint": "http://127.0.0.1:1/", "max_results": 1,
                         "timeout_seconds": 2, "user_agent": "self-test"})
        net_struct = isinstance(r, dict) and r.get("ok") is False and ("error_type" in r)
    except Exception as e:
        net_struct = f"raised:{type(e).__name__}"
    details["network_failure_structured"] = net_struct
    ok = ok and net_struct is True

    print(json.dumps({"self_test": "pass" if ok else "fail", **details},
                     ensure_ascii=False, indent=2))
    sys.exit(0 if ok else 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query", nargs="?")
    ap.add_argument("--max", type=int, default=None)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        self_test()
    if args.query is None:
        self_test()  # 完全不带参数 → 既有便捷行为：跑自测
    cfg = load_cfg()
    if not args.query.strip():
        # OBS-2：显式传入空值不得静默变成 self-test
        res = {"ok": False, "query": args.query, "error_type": "bad_args",
               "error": "empty query value (omit args to run --self-test)", "results": []}
    else:
        res = search(args.query, cfg, args.max)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    sys.exit(0 if res.get("ok") else 1)


if __name__ == "__main__":
    main()
