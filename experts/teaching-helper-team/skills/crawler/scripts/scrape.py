#!/usr/bin/env python3
"""web-scraper — 教学帮帮团数据采集工具（静态 + 可选 JS 渲染）。

子命令：
  extract   <url> --selector "<css>"   按 CSS 选择器提取
  tables    <url>                      自动检测并提取表格
  links     <url>                      提取全部链接
  structure <url>                      分析页面结构（标题/区块/链接数）
  crawl     <start> --pages N          分页跟随爬取

输出格式：--format text|json|csv|md（默认 text）
合规约束（强制）：默认遵守 robots.txt、默认 1 req/s、SSRF 防护（拒绝内网/回环）、敏感数据不入库。

依赖：
  静态：requests + beautifulsoup4 + lxml（WorkBuddy 托管 Python 运行时安装）
  动态：playwright + chromium（可选，--js 时启用）
"""
from __future__ import annotations

import argparse
import csv
import io
import ipaddress
import json
import socket
import sys
import time
import urllib.parse
import urllib.robotparser


try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    sys.stderr.write("缺少依赖：请先运行 setup 技能初始化（依赖装入专用 venv，见 skills/setup/SKILL.md），再以 setup-status.json 的 venv_python 运行本脚本。\n")
    sys.exit(2)

DEFAULT_DELAY = 1.0
USER_AGENT = "teaching-helper-team-web-scraper/1.1 (+educational)"
PRIVATE_NETS = (
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("100.64.0.0/10"),  # CGNAT（运营商级 NAT）
)
PRIVATE_SUFFIXES = (".local", ".internal", ".example", ".invalid")


def _resolve_all_ips(host: str) -> list:
    """返回 host 对应的全部 IP（A + AAAA）；IP 字面量直接返回单元素列表。

    使用 getaddrinfo 而非 gethostbyname，以覆盖 IPv6 并枚举全部地址，
    便于在 SSRF 防护中要求「全部地址均为公网」（防 DNS 重绑定留口）。
    """
    try:
        return [str(ipaddress.ip_address(host))]
    except ValueError:
        pass
    try:
        return [info[4][0] for info in socket.getaddrinfo(host, None)]
    except Exception:
        return []


def _ip_is_public(ip_str: str) -> bool:
    """判定单个 IP 是否为可接受的「公网」地址（拒绝回环/链路本地/未指定/组播/私网/CGNAT）。"""
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return False
    if ip.version == 6 and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    if ip.is_loopback or ip.is_link_local or ip.is_unspecified or ip.is_multicast:
        return False
    if any(ip in net for net in PRIVATE_NETS):
        return False
    return True


def is_safe_url(url: str) -> bool:
    """SSRF 防护：仅允许公网 http/https，拒绝内网/回环/链路本地/未指定/组播/CGNAT 地址。

    对每个解析出的 IP（A + AAAA）逐一校验，要求「全部为公网」——只要任一地址非公网
    （如 DNS 同时返回公网 IP 与内网 IP）即拒绝，规避 DNS 重绑定。
    """
    try:
        p = urllib.parse.urlparse(url)
    except Exception:
        return False
    if p.scheme not in ("http", "https"):
        return False
    host = (p.hostname or "").lower().rstrip(".")
    if not host:
        return False
    if any(host.endswith(suf) for suf in PRIVATE_SUFFIXES):
        return False
    ips = _resolve_all_ips(host)
    if not ips:
        return False
    return all(_ip_is_public(ip) for ip in ips)


def _redact(url: str) -> str:
    """日志合规：抹去 URL 中的查询串（可能携带 token= 等敏感参数）。"""
    try:
        p = urllib.parse.urlparse(url)
        if p.query:
            return urllib.parse.urlunparse(p._replace(query="<redacted>"))
        return url
    except Exception:
        return url


def _peer_ip_public(resp) -> bool:
    """连接后二次校验对端 IP（防 DNS 重绑定：解析→连接期间 IP 被换成内网）。

    取实际 socket 的对端地址判定；若无法取得（socket 缺失）则 **fail-closed**：
    拒绝放行并记日志，交由上层按 SSRF 拒绝处理，绝不静默通过。
    """
    import logging
    log = logging.getLogger("web-scraper.ssrf")
    try:
        conn = getattr(resp.raw, "_connection", None)
        sock = conn.sock if conn else None
        if sock is None:
            log.warning("SSRF 防护：无法取得对端 socket，按不安全处理（fail-closed 拒绝）")
            return False
        peer = sock.getpeername()[0]
        return _ip_is_public(peer)
    except Exception:
        log.warning("SSRF 防护：对端 IP 校验异常，按不安全处理（fail-closed 拒绝）")
        return False


class SSRFRejected(Exception):
    """SSRF 防护：请求目标（含重定向 / 子资源）被判定为内网 / 回环时抛出。"""


MAX_BODY_BYTES = 20 * 1024 * 1024  # 20MB 上限，防响应体过大导致内存耗尽(DoS)


def _safe_get(url: str, headers: dict, timeout: int, max_redirects: int = 5):
    """发起 GET 并逐跳校验 SSRF；关闭盲 SSRF 且连接后二次校验对端 IP（防 DNS 重绑定）。

    使用 stream=True 保留底层连接以便取对端 IP，并分块读取以施加响应体积上限。
    """
    cur = url
    for _ in range(max_redirects + 1):
        if not is_safe_url(cur):
            raise SSRFRejected(cur)
        r = requests.get(cur, headers=headers, timeout=timeout,
                         allow_redirects=False, stream=True)
        if not _peer_ip_public(r):
            r.close()
            raise SSRFRejected("DNS 重绑定：对端 IP 为内网/回环（已拒绝）")
        if r.status_code in (301, 302, 303, 307, 308) and "Location" in r.headers:
            cur = urllib.parse.urljoin(r.url, r.headers["Location"])
            r.close()
            continue
        return r
    raise SSRFRejected("重定向次数过多")


def robots_allows(url: str, ignore_robots: bool) -> bool:
    if ignore_robots:
        return True
    p = urllib.parse.urlparse(url)
    base = f"{p.scheme}://{p.netloc}"
    rp = urllib.robotparser.RobotFileParser()
    try:
        # 复用 _safe_get 而非 rp.read()：robots.txt 自身也可能被 301 到内网，
        # rp.read() 会绕过本脚本的 SSRF 校验。
        rb = _safe_get(base + "/robots.txt", headers={"User-Agent": USER_AGENT}, timeout=10)
        rp.parse(rb.text.splitlines())
        rb.close()
        return rp.can_fetch(USER_AGENT, url)
    except Exception:  # noqa: BLE001
        # robots 不可读或被 SSRF 校验拒绝时保守放行（仅静态抓取，目标页仍受 SSRF/限速约束）
        return True


def fetch_html(url: str, use_js: bool, ignore_robots: bool) -> str:
    if not is_safe_url(url):
        sys.stderr.write(f"[SSRF] 拒绝内网/回环地址：{_redact(url)}\n")
        sys.exit(3)
    if not robots_allows(url, ignore_robots):
        sys.stderr.write(f"[robots] 目标禁止抓取：{_redact(url)}\n")
        sys.exit(4)
    time.sleep(DEFAULT_DELAY)
    if use_js:
        return _fetch_js(url)
    try:
        r = _safe_get(url, headers={"User-Agent": USER_AGENT}, timeout=20)
        r.raise_for_status()
        r.encoding = r.apparent_encoding or "utf-8"
        buf = bytearray()
        for chunk in r.iter_content(8192):
            buf.extend(chunk)
            if len(buf) > MAX_BODY_BYTES:
                r.close()
                sys.stderr.write("[fetch] 响应体过大（>20MB），已中止以防内存耗尽\n")
                sys.exit(6)
        return buf.decode(r.encoding or "utf-8", errors="replace")
    except SSRFRejected as e:
        sys.stderr.write(f"[SSRF] 拒绝内网/回环地址（含重定向/DNS 重绑定）：{e}\n")
        sys.exit(3)
    except Exception as e:  # noqa: BLE001
        sys.stderr.write(f"[fetch] 失败：{e}\n")
        sys.exit(5)


def _fetch_js(url: str) -> str:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.stderr.write(
            "[js] 动态渲染需要 Playwright。请装进本团专用 venv（勿用裸 pip / 裸 python3——会装错环境）：\n"
            '  "$VENV_PY" -m pip install playwright && "$VENV_PY" -m playwright install chromium\n'
            "（$VENV_PY 的取法见 skills/setup/SKILL.md 的「关键约定」三级探测）\n"
        )
        sys.exit(2)
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            try:
                page = browser.new_page(user_agent=USER_AGENT)
                # SSRF 防护：拦截任何非安全 URL（含重定向与子资源）的请求
                def _route(route):
                    if not is_safe_url(route.request.url):
                        route.abort()
                    else:
                        route.continue_()
                page.route("**/*", _route)
                page.goto(url, wait_until="networkidle", timeout=30000)
                html = page.content()
            finally:
                browser.close()
            return html
    except SSRFRejected:
        sys.stderr.write(f"[SSRF] 拒绝内网/回环地址：{_redact(url)}\n")
        sys.exit(3)
    except KeyboardInterrupt:
        raise
    except Exception as e:  # noqa: BLE001
        # page.route 拦截非安全请求时 abort 会令 goto 抛错（net::ERR_ABORTED 等），
        # 以及其他 Playwright 运行时异常——统一转成友好错误，不裸抛 traceback。
        msg = str(e).strip() or type(e).__name__
        sys.stderr.write(
            f"[js] 页面加载失败：{msg}\n"
            f"     提示：若目标页面含内网/回环/子资源被 SSRF 拦截，或被反爬限制，"
            "加载可能被中止；可改用静态模式（去掉 --js）重试。\n"
        )
        sys.exit(5)


def to_text(soup: BeautifulSoup) -> str:
    for tag in soup(["script", "style"]):
        tag.decompose()
    return soup.get_text(separator="\n", strip=True)


def cmd_extract(args: argparse.Namespace) -> object:
    html = fetch_html(args.url, args.js, args.ignore_robots)
    soup = BeautifulSoup(html, "lxml")
    nodes = soup.select(args.selector) if args.selector else [soup]
    items = [to_text(BeautifulSoup(str(n), "lxml")) for n in nodes]
    return items


def cmd_tables(args: argparse.Namespace) -> object:
    html = fetch_html(args.url, args.js, args.ignore_robots)
    soup = BeautifulSoup(html, "lxml")
    out = []
    for t in soup.find_all("table"):
        rows = []
        for tr in t.find_all("tr"):
            cells = [c.get_text(strip=True) for c in tr.find_all(["th", "td"])]
            if cells:
                rows.append(cells)
        if rows:
            out.append(rows)
    return out


def cmd_links(args: argparse.Namespace) -> object:
    html = fetch_html(args.url, args.js, args.ignore_robots)
    soup = BeautifulSoup(html, "lxml")
    base = args.url
    links = []
    for a in soup.find_all("a", href=True):
        href = urllib.parse.urljoin(base, a["href"])
        links.append({"text": a.get_text(strip=True), "href": href})
    return links


def cmd_structure(args: argparse.Namespace) -> object:
    html = fetch_html(args.url, args.js, args.ignore_robots)
    soup = BeautifulSoup(html, "lxml")
    return {
        "title": soup.title.get_text(strip=True) if soup.title else "",
        "h1": [h.get_text(strip=True) for h in soup.find_all("h1")],
        "h2": [h.get_text(strip=True) for h in soup.find_all("h2")],
        "paragraphs": len(soup.find_all("p")),
        "tables": len(soup.find_all("table")),
        "links": len(soup.find_all("a", href=True)),
        "forms": len(soup.find_all("form")),
    }


def cmd_crawl(args: argparse.Namespace) -> object:
    visited, queue, idx = set(), [args.url], 0
    pages = []
    while queue and idx < args.pages:
        url = queue.pop(0)
        if url in visited or not is_safe_url(url):
            continue
        visited.add(url)
        idx += 1
        html = fetch_html(url, args.js, args.ignore_robots)
        soup = BeautifulSoup(html, "lxml")
        pages.append({"url": url, "title": soup.title.get_text(strip=True) if soup.title else "",
                      "text": to_text(soup)[:20000]})
        for a in soup.find_all("a", href=True):
            nxt = urllib.parse.urljoin(url, a["href"])
            if urllib.parse.urlparse(nxt).netloc == urllib.parse.urlparse(args.url).netloc:
                if nxt not in visited:
                    queue.append(nxt)
    return {"pages_crawled": len(pages), "pages": pages}


def render(data: object, fmt: str) -> str:
    if fmt == "json":
        return json.dumps(data, ensure_ascii=False, indent=2)
    if fmt == "csv":
        buf = io.StringIO()
        if isinstance(data, list) and data and isinstance(data[0], list):
            writer = csv.writer(buf)
            for i, table in enumerate(data):
                if i > 0:
                    buf.write("\n")  # 表间空行分隔
                for row in table:
                    writer.writerow(row)
        elif isinstance(data, list) and data and isinstance(data[0], dict):
            w = csv.DictWriter(buf, fieldnames=list(data[0].keys()))
            w.writeheader()
            w.writerows(data)
        return buf.getvalue()
    if fmt == "md":
        if isinstance(data, dict) and "pages" in data:
            lines = [f"# 爬取结果（{data.get('pages_crawled')} 页）\n"]
            for p in data["pages"]:
                lines.append(f"\n## {p['title']}\n{p['url']}\n\n{p['text'][:4000]}\n")
            return "\n".join(lines)
        if isinstance(data, list) and data and isinstance(data[0], list):
            return "\n\n".join(
                "\n".join(" | ".join(c) for c in tbl) for tbl in data
            )
    # text
    if isinstance(data, list):
        return "\n\n".join(
            "\n".join(f"- {d['text']}: {d['href']}" if isinstance(d, dict) and "href" in d else str(d)
                      for d in (item if isinstance(item, list) else [item]))
            for item in data
        )
    if isinstance(data, dict):
        return "\n".join(f"{k}: {v}" for k, v in data.items())
    return str(data)


def main() -> None:
    global DEFAULT_DELAY
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--delay", type=float, default=DEFAULT_DELAY, help="请求间隔秒（默认 1）")
    common.add_argument("--ignore-robots", action="store_true", help="显式忽略 robots.txt（需授权留痕）")
    common.add_argument("--format", choices=["text", "json", "csv", "md"], default="text")
    ap = argparse.ArgumentParser(description="教学帮帮团网页数据采集（静态 + 可选 JS 渲染）", parents=[common])
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_ex = sub.add_parser("extract", parents=[common]); p_ex.add_argument("url")
    p_ex.add_argument("--selector", default=None); p_ex.add_argument("--js", action="store_true")
    p_ex.set_defaults(func=cmd_extract)
    p_tb = sub.add_parser("tables", parents=[common]); p_tb.add_argument("url"); p_tb.add_argument("--js", action="store_true")
    p_tb.set_defaults(func=cmd_tables)
    p_lk = sub.add_parser("links", parents=[common]); p_lk.add_argument("url"); p_lk.add_argument("--js", action="store_true")
    p_lk.set_defaults(func=cmd_links)
    p_st = sub.add_parser("structure", parents=[common]); p_st.add_argument("url"); p_st.add_argument("--js", action="store_true")
    p_st.set_defaults(func=cmd_structure)
    p_cr = sub.add_parser("crawl", parents=[common]); p_cr.add_argument("url"); p_cr.add_argument("--pages", type=int, default=5)
    p_cr.add_argument("--js", action="store_true"); p_cr.set_defaults(func=cmd_crawl)

    args = ap.parse_args()
    DEFAULT_DELAY = args.delay
    result = args.func(args)
    print(render(result, args.format))


if __name__ == "__main__":
    main()
