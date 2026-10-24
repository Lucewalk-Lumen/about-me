#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gates.py — college-competition-coaching-team 包级门禁（零第三方依赖）。

七项子门禁 + manifest 硬门禁，落实 WorkBuddy 专家开发工坊对 team 型包的合规要求：
  composition  成员 agent 结构六要素（角色定义/擅长领域/分析框架/数据获取/结构化输出/回传要求）
  length       主文件 <= 18000 字符（平台注入上限口径，CRLF 计 2）
  shard        plugin.json 声明的 agents/skills 条目在磁盘存在（C005）
  avatar       头像可达且 >= 10240 字节（防占位图顶替）
  deadlink     md 链接 + 包内路径引用无死链
  traversal    无本机绝对路径泄露（/Users/、C:\\Users\\、/home/）
  exec         scripts/*.py 可编译且 CLI --help 冒烟
  manifest     九项硬指标（displayDescription CJK 40-50、tags=3、quickPrompts=3、
               defaultInitPrompt==quickPrompts[0]、expertType=team、members 字段白名单、
               categoryId 枚举、plugin==name==顶层目录名、四向一致性）

退出码：0 = 无 WARN 且无 FAIL；1 = 仅 WARN；2 = 有 FAIL
--self-test   绿红双证：好包必 PASS；删一成员文件必 FAIL。
--check-urls  可选：对 knowledge/*.md 中外源 URL 做存活探测（仅打印报告，不并入
              默认门禁、不影响退出码；403/412 等按"疑似反爬"判 WARN，浏览器通常可达）。
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata

LENGTH_WARN_LIMIT = 18000
AVATAR_MIN_BYTES = 10240
MEMBERS_ALLOWED_FIELDS = ("id", "name", "profession", "avatar", "role")
CATEGORY_IDS = [
    "01-ProductDesign", "02-Engineering", "03-GameSpatial", "04-DataAI",
    "05-MarketingGrowth", "06-ContentCreative", "07-SalesCommerce",
    "08-FinanceInvestment", "09-OperationsHR", "10-ProjectQuality",
    "11-SecurityCompliance", "12-IndustryConsultant", "13-TencentZone",
    "14-WorldWise", "15-Education",
]
COMPOSITION_ELEMENTS = ["角色定义", "擅长领域", "分析框架", "数据获取", "结构化输出", "回传要求"]


def _pkg_root_from_script():
    # scripts/ 的上一级即包根
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _plugin_path(pkg):
    return os.path.join(pkg, ".codebuddy-plugin", "plugin.json")


def _load_plugin(pkg):
    p = _plugin_path(pkg)
    if not os.path.exists(p):
        return None, "plugin.json 缺失"
    try:
        with open(p, encoding="utf-8") as fh:
            return json.load(fh), None
    except Exception as e:  # noqa: BLE001
        return None, "plugin.json 解析失败: %s" % e


def _heading_hit(txt, element):
    return any(re.match(r"^#{1,6}\s*" + re.escape(element), line) for line in txt.splitlines())


# --------------------------------------------------------------------------- composition
def check_composition(pkg):
    ok, warn, fail = [], [], []
    d, err = _load_plugin(pkg)
    if d is None:
        fail.append("composition: %s" % err)
        return ok, warn, fail
    lead = d.get("teamInfo", {}).get("leadAgent") or d.get("agentName")
    members = [m.get("id") for m in d.get("members", [])]
    adir = os.path.join(pkg, "agents")
    bad = 0
    for mid in members:
        if mid == lead:
            continue
        fp = os.path.join(adir, "%s.md" % mid)
        if not os.path.exists(fp):
            fail.append("composition: 成员文件缺失 %s.md" % mid)
            bad += 1
            continue
        with open(fp, encoding="utf-8", errors="ignore") as fh:
            txt = fh.read()
        miss = [e for e in COMPOSITION_ELEMENTS if e not in txt]
        if miss:
            fail.append("composition: %s.md 缺结构要素 %s" % (mid, miss))
            bad += 1
        else:
            ok.append("composition: %s.md 六要素齐全（lead 豁免）" % mid)
    if bad == 0:
        ok.append("composition: 全部成员 agent 结构六要素齐全")
    return ok, warn, fail


# --------------------------------------------------------------------------- length
def check_length(pkg):
    ok, warn, fail = [], [], []
    files = []
    adir = os.path.join(pkg, "agents")
    if os.path.isdir(adir):
        for f in sorted(os.listdir(adir)):
            if f.endswith(".md"):
                files.append(os.path.join(adir, f))
    sdir = os.path.join(pkg, "skills")
    if os.path.isdir(sdir):
        for sk in sorted(os.listdir(sdir)):
            sp = os.path.join(sdir, sk, "SKILL.md")
            if os.path.exists(sp):
                files.append(sp)
    over = 0
    for fp in files:
        with open(fp, "rb") as fh:
            data = fh.read()
        n = len(data.decode("utf-8", "replace"))
        rel = os.path.relpath(fp, pkg)
        if n > LENGTH_WARN_LIMIT:
            warn.append("length: %s 长度 %d > %d" % (rel, n, LENGTH_WARN_LIMIT))
            over += 1
        else:
            ok.append("length: %s 长度 %d" % (rel, n))
    if over:
        fail.append("length: %d 个文件超长" % over)
    else:
        ok.append("length: 全部文件 <= %d" % LENGTH_WARN_LIMIT)
    return ok, warn, fail


# --------------------------------------------------------------------------- shard
def check_shard(pkg):
    ok, warn, fail = [], [], []
    d, err = _load_plugin(pkg)
    if d is None:
        fail.append("shard: %s" % err)
        return ok, warn, fail
    missing = 0
    for a in d.get("agents", []):
        if os.path.exists(os.path.join(pkg, a)):
            ok.append("shard: agents 条目存在 %s" % a)
        else:
            fail.append("shard: agents 条目缺失 %s" % a)
            missing += 1
    for s in d.get("skills", []):
        if os.path.isdir(os.path.join(pkg, s)):
            ok.append("shard: skills 条目存在 %s" % s)
        else:
            fail.append("shard: skills 条目缺失 %s" % s)
            missing += 1
    if not missing:
        ok.append("shard: 清单条目全部存在")
    return ok, warn, fail


# --------------------------------------------------------------------------- avatar
def check_avatar(pkg):
    ok, warn, fail = [], [], []
    d, err = _load_plugin(pkg)
    if d is None:
        fail.append("avatar: %s" % err)
        return ok, warn, fail
    refs = []
    if d.get("avatar"):
        refs.append(("顶层 avatar", d["avatar"]))
    for m in d.get("members", []):
        if m.get("avatar"):
            refs.append((m.get("id"), m["avatar"]))
        else:
            fail.append("avatar: 成员 %s 未声明 avatar" % m.get("id"))
    n_ok = 0
    for who, rel in refs:
        fp = os.path.join(pkg, rel)
        if not os.path.exists(fp):
            fail.append("avatar: 断链/缺失 %s -> %s" % (who, rel))
            continue
        sz = os.path.getsize(fp)
        if sz < AVATAR_MIN_BYTES:
            fail.append("avatar: %s -> %s 体积 %dB < %dB（疑似占位图）" % (who, rel, sz, AVATAR_MIN_BYTES))
            continue
        n_ok += 1
    if n_ok == len(refs) and not fail:
        ok.append("avatar: %d 个头像全部可达且 >= %dB" % (n_ok, AVATAR_MIN_BYTES))
    return ok, warn, fail


# --------------------------------------------------------------------------- deadlink
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
CODE_RE = re.compile(r"`([^`\n]+?)`")
CODE_EXT = (".py", ".md", ".json", ".yaml", ".yml", ".html", ".htm", ".sh",
            ".csv", ".tsv", ".txt", ".png", ".jpg", ".js", ".svg")
PKG_PREFIXES = ("scripts/", "skills/", "knowledge/", "agents/", "avatars/",
                "assets/", ".codebuddy-plugin/")


def _resolve(pkg, md_path, ref):
    if ref.startswith(("http://", "https://", "#", "mailto:")):
        return "external"
    ref = ref.split("#")[0].split("?")[0]
    if not ref:
        return "external"
    for b in (pkg, os.path.dirname(md_path), os.path.dirname(os.path.dirname(md_path))):
        cand = os.path.normpath(os.path.join(b, ref))
        if os.path.exists(cand):
            return cand
    return None


def check_deadlink(pkg):
    ok, warn, fail = [], [], []
    n_link = n_code = 0
    broken = []
    for root, _dirs, files in os.walk(pkg):
        if ".git" in root or "__pycache__" in root:
            continue
        for f in files:
            if not f.endswith(".md"):
                continue
            fp = os.path.join(root, f)
            with open(fp, encoding="utf-8", errors="ignore") as fh:
                txt = fh.read()
            for m in LINK_RE.finditer(txt):
                n_link += 1
                if _resolve(pkg, fp, m.group(1)) is None:
                    broken.append("死链 %s: (%s)" % (os.path.relpath(fp, pkg), m.group(1)))
            for m in CODE_RE.finditer(txt):
                ref = m.group(1).strip()
                if (not ref or " " in ref or "/" not in ref or not ref.startswith(PKG_PREFIXES)
                        or not ref.endswith(CODE_EXT) or any(c in ref for c in "*?<>")):
                    continue
                n_code += 1
                if _resolve(pkg, fp, ref) is None:
                    broken.append("悬空路径 %s: `%s`" % (os.path.relpath(fp, pkg), ref))
    ok.append("deadlink: 检查 %d 个 md 链接 + %d 个路径引用, 死链 %d" % (n_link, n_code, len(broken)))
    for b in broken:
        fail.append("deadlink: %s" % b)
    if broken:
        fail.append("deadlink: %d 处死链" % len(broken))
    return ok, warn, fail


# --------------------------------------------------------------------------- traversal
ABS = re.compile(r"(/Users/[A-Za-z0-9][^ \"'\t\n\r]*"
                 r"|C:\\\\Users\\\\[A-Za-z0-9][^ \"'\t\n\r]*"
                 r"|/home/[A-Za-z0-9][^ \"'\t\n\r]*)")
TRAVERSAL_EXT = (".json", ".yaml", ".yml", ".py", ".js", ".sh", ".html", ".htm",
                 ".md", ".txt", ".csv", ".tsv", ".toml", ".cfg", ".ini", ".R")


def check_traversal(pkg):
    ok, warn, fail = [], [], []
    n, hits = 0, []
    for root, _dirs, files in os.walk(pkg):
        if ".git" in root or "__pycache__" in root:
            continue
        for f in files:
            if not f.endswith(TRAVERSAL_EXT):
                continue
            fp = os.path.join(root, f)
            n += 1
            with open(fp, encoding="utf-8", errors="ignore") as fh:
                txt = fh.read()
            for m in ABS.finditer(txt):
                hits.append("%s: %s" % (os.path.relpath(fp, pkg), m.group(1)))
    if hits:
        for h in hits:
            fail.append("traversal: 本机绝对路径 %s" % h)
        fail.append("traversal: %d 处绝对路径泄露" % len(hits))
    else:
        ok.append("traversal: 扫描 %d 个文本文件，无本机绝对路径泄露" % n)
    return ok, warn, fail


# --------------------------------------------------------------------------- exec
_CLI_HINT = re.compile(r"argparse|--help|--self-test|[\"']-h[\"']")


def check_exec(pkg):
    ok, warn, fail = [], [], []
    sd = os.path.join(pkg, "scripts")
    if not os.path.isdir(sd):
        ok.append("exec: 未发现脚本")
        return ok, warn, fail
    import py_compile
    tmpd = tempfile.mkdtemp(prefix="ccc_gates_")
    n_c = n_h = 0
    try:
        for f in sorted(os.listdir(sd)):
            if not f.endswith(".py"):
                continue
            fp = os.path.join(sd, f)
            rel = os.path.relpath(fp, pkg)
            try:
                py_compile.compile(fp, cfile=os.path.join(tmpd, f + ".pyc"), doraise=True)
                n_c += 1
            except py_compile.PyCompileError as e:
                fail.append("exec: %s 编译失败: %s" % (rel, getattr(e, "msg", e)))
                continue
            with open(fp, encoding="utf-8", errors="ignore") as fh:
                src = fh.read()
            if not _CLI_HINT.search(src):
                continue
            try:
                r = subprocess.run([sys.executable, fp, "--help"], capture_output=True,
                                   text=True, timeout=30)
            except subprocess.TimeoutExpired:
                fail.append("exec: %s --help 超时" % rel)
                continue
            if r.returncode != 0:
                tail = (r.stderr or r.stdout or "").strip().splitlines()
                fail.append("exec: %s --help 退出码 %d: %s" % (rel, r.returncode, tail[-1] if tail else ""))
                continue
            n_h += 1
    finally:
        shutil.rmtree(tmpd, ignore_errors=True)
    if not fail:
        ok.append("exec: %d 个脚本可编译，%d 个 CLI --help 冒烟通过" % (n_c, n_h))
    return ok, warn, fail


# --------------------------------------------------------------------------- manifest (九项硬指标)
def _cjk_count(s):
    n = 0
    for ch in s:
        if ("\u4e00" <= ch <= "\u9fff") or ("\u3000" <= ch <= "\u303f") or ("\uff00" <= ch <= "\uffef"):
            n += 1
        else:
            nm = unicodedata.name(ch, "")
            if "CJK" in nm or "IDEOGRAPHIC" in nm:
                n += 1
    return n


def check_manifest(pkg):
    ok, warn, fail = [], [], []
    d, err = _load_plugin(pkg)
    if d is None:
        fail.append("manifest: %s" % err)
        return ok, warn, fail
    # plugin == name == 顶层目录名
    top = os.path.basename(os.path.normpath(pkg))
    if d.get("plugin") == d.get("name") == top:
        ok.append("manifest: plugin==name==目录名 (%s)" % top)
    else:
        fail.append("manifest: plugin/name/目录名 不一致: %s / %s / %s"
                    % (d.get("plugin"), d.get("name"), top))
    # expertType team
    if d.get("expertType") == "team":
        ok.append("manifest: expertType=team")
    else:
        fail.append("manifest: expertType 非 team")
    # displayDescription.zh CJK 40-50
    dd = (d.get("displayDescription") or {}).get("zh", "")
    c = _cjk_count(dd)
    if 40 <= c <= 50:
        ok.append("manifest: displayDescription.zh CJK=%d（40-50）" % c)
    else:
        fail.append("manifest: displayDescription.zh CJK=%d，须在 40-50" % c)
    # tags 3 / quickPrompts 3
    tags = d.get("tags", [])
    qp = d.get("quickPrompts", [])
    if len(tags) == 3:
        ok.append("manifest: tags 数量=3")
    else:
        fail.append("manifest: tags 数量=%d（须 3）" % len(tags))
    if len(qp) == 3:
        ok.append("manifest: quickPrompts 数量=3")
    else:
        fail.append("manifest: quickPrompts 数量=%d（须 3）" % len(qp))
    # defaultInitPrompt.zh == quickPrompts[0].zh
    dip = (d.get("defaultInitPrompt") or {}).get("zh", "")
    qp0 = qp[0].get("zh", "") if qp else ""
    if dip and dip == qp0:
        ok.append("manifest: defaultInitPrompt == quickPrompts[0]")
    else:
        fail.append("manifest: defaultInitPrompt 未等于 quickPrompts[0]")
    # categoryId 枚举
    if d.get("categoryId") in CATEGORY_IDS:
        ok.append("manifest: categoryId=%s（枚举内）" % d.get("categoryId"))
    else:
        fail.append("manifest: categoryId=%s 不在枚举" % d.get("categoryId"))
    # members 字段白名单
    bad_fields = []
    for m in d.get("members", []):
        extra = [k for k in m.keys() if k not in MEMBERS_ALLOWED_FIELDS]
        if extra:
            bad_fields.append("%s:%s" % (m.get("id"), extra))
    if bad_fields:
        fail.append("manifest: members 含非白名单字段 %s" % bad_fields)
    else:
        ok.append("manifest: members 字段均为白名单")
    # 四向一致性：members id <-> agents/{id}.md <-> frontmatter name
    adir = os.path.join(pkg, "agents")
    for m in d.get("members", []):
        mid = m.get("id")
        fp = os.path.join(adir, "%s.md" % mid)
        if not os.path.exists(fp):
            fail.append("manifest: 成员 %s 无 agents/%s.md" % (mid, mid))
            continue
        with open(fp, encoding="utf-8", errors="ignore") as fh:
            head = fh.read(600)
        fm = re.search(r"^name:\s*([A-Za-z0-9_\-]+)\s*$", head, re.MULTILINE)
        if fm and fm.group(1) == mid:
            ok.append("manifest: 成员 %s 四向一致" % mid)
        else:
            fail.append("manifest: 成员 %s frontmatter name 不一致" % mid)
    # teamInfo.leadAgent == members[0].id == agentName
    lead = d.get("teamInfo", {}).get("leadAgent")
    m0 = d.get("members", [{}])[0].get("id")
    an = d.get("agentName")
    if lead == m0 == an:
        ok.append("manifest: leadAgent==members[0]==agentName (%s)" % lead)
    else:
        fail.append("manifest: leadAgent/members[0]/agentName 不一致")
    return ok, warn, fail


# --------------------------------------------------------------------------- urls（可选报告）
URL_RE = re.compile(r"""https?://[^\s)\]>"'』」）】]+""")
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept": "text/html,application/xhtml+xml,*/*;q=0.8"}
ANTI_CRAWL = {403, 406, 412, 429, 503, 999}


def _probe_url(url, timeout=8):
    import urllib.error
    import urllib.request
    try:
        req = urllib.request.Request(url, method="HEAD", headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status
    except urllib.error.HTTPError as e:
        if e.code == 405:  # 不支持 HEAD → 改用 ranged GET
            try:
                req2 = urllib.request.Request(url, headers=dict(UA, Range="bytes=0-0"))
                with urllib.request.urlopen(req2, timeout=timeout) as r2:
                    return r2.status
            except urllib.error.HTTPError as e2:
                return e2.code
            except Exception:
                return None
        return e.code
    except Exception:
        return None


def report_urls(pkg):
    """可选报告：knowledge/*.md 中外源 URL 存活探测。只打印，不影响退出码。"""
    kdir = os.path.join(pkg, "knowledge")
    urls = []
    if os.path.isdir(kdir):
        for f in sorted(os.listdir(kdir)):
            if not f.endswith(".md"):
                continue
            with open(os.path.join(kdir, f), encoding="utf-8", errors="ignore") as fh:
                txt = fh.read()
            for m in URL_RE.finditer(txt):
                u = m.group(0).rstrip(".,;、")
                if u not in urls:
                    urls.append(u)
    print("=" * 60)
    print("gates.py --check-urls · 外源 URL 存活报告（仅报告，不影响退出码）")
    print("  注：脚本探测存在客户端指纹误差（部分站点对非浏览器返回 403/404）；")
    print("      DEAD/WARN 条目建议以浏览器复核为准后再处置。")
    if not urls:
        print("  [INFO] knowledge/ 未发现外源 URL")
        print("=" * 60)
        return
    n_ok = n_warn = n_dead = 0
    for u in urls:
        code = _probe_url(u)
        if code is not None and 200 <= code < 400:
            n_ok += 1
            print("  [OK]   %s -> %s" % (code, u))
        elif code in ANTI_CRAWL:
            n_warn += 1
            print("  [WARN] %s -> %s（疑似反爬/限流，浏览器通常可达）" % (code, u))
        elif code in (404, 410):
            n_dead += 1
            print("  [DEAD] %s -> %s（建议复核或移除）" % (code, u))
        else:
            n_warn += 1
            print("  [WARN] %s -> %s（网络不可达或超时）" % (code if code is not None else "ERR", u))
    print("-" * 60)
    print("  合计 %d：OK=%d WARN=%d DEAD=%d" % (len(urls), n_ok, n_warn, n_dead))
    print("=" * 60)


ALL_CHECKS = [
    ("manifest", check_manifest),
    ("composition", check_composition),
    ("length", check_length),
    ("shard", check_shard),
    ("avatar", check_avatar),
    ("deadlink", check_deadlink),
    ("traversal", check_traversal),
    ("exec", check_exec),
]


def run_all(pkg):
    ok, warn, fail = [], [], []
    for _name, fn in ALL_CHECKS:
        o, w, f = fn(pkg)
        ok.extend(o)
        warn.extend(w)
        fail.extend(f)
    return ok, warn, fail


def _print_report(ok, warn, fail):
    print("=" * 60)
    print("gates.py · OK=%d WARN=%d FAIL=%d" % (len(ok), len(warn), len(fail)))
    for m in ok:
        print("  [OK]   %s" % m)
    for m in warn:
        print("  [WARN] %s" % m)
    for m in fail:
        print("  [FAIL] %s" % m)
    print("=" * 60)


def _self_test(pkg):
    print("--- self-test（绿红双证）---")
    # 绿：好包必 PASS
    o, w, f = run_all(pkg)
    green = (not f)
    print("  [绿证] 好包 FAIL=%d -> %s" % (len(f), "PASS" if green else "FAIL"))
    # 红：删一成员文件必 FAIL
    tmp = tempfile.mkdtemp(prefix="ccc_selftest_")
    try:
        shutil.copytree(pkg, os.path.join(tmp, "pkg"))
        tp = os.path.join(tmp, "pkg")
        # 删一个非 lead 成员文件
        victim = None
        d, _ = _load_plugin(pkg)
        lead = d.get("teamInfo", {}).get("leadAgent") or d.get("agentName")
        for m in d.get("members", []):
            mid = m.get("id")
            if mid != lead:
                victim = mid
                break
        os.remove(os.path.join(tp, "agents", "%s.md" % victim))
        ro, rw, rf = run_all(tp)
        red = bool(rf)
        print("  [红证] 缺 %s.md 后 FAIL=%d -> %s" % (victim, len(rf), "PASS(错!)" if not red else "FAIL(预期)"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    ok_self = green and red
    print("  self-test: %s" % ("PASS" if ok_self else "FAIL"))
    return 0 if ok_self else 2


def build_parser():
    ap = argparse.ArgumentParser(
        prog="gates.py",
        description="college-competition-coaching-team 包级门禁：manifest/构成/长度/清单/头像/死链/路径安全/脚本可执行性。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="退出码：0=无WARN无FAIL；1=仅WARN；2=有FAIL")
    ap.add_argument("pkg", nargs="?", default=None, help="包根目录（默认脚本上级目录）")
    ap.add_argument("--self-test", action="store_true", help="绿红双证自检")
    ap.add_argument("--check-urls", action="store_true",
                    help="可选：对 knowledge/*.md 外源 URL 做存活检查（仅报告，不影响退出码）")
    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)
    pkg = args.pkg or _pkg_root_from_script()
    if not os.path.isdir(pkg):
        print("[FAIL] gates: 包根不是目录: %s" % pkg, file=sys.stderr)
        sys.exit(2)
    if args.self_test:
        rc = _self_test(pkg)
        sys.exit(rc)
    if args.check_urls:
        report_urls(pkg)
        sys.exit(0)
    ok, warn, fail = run_all(pkg)
    _print_report(ok, warn, fail)
    sys.exit(2 if fail else (1 if warn else 0))


if __name__ == "__main__":
    main()
