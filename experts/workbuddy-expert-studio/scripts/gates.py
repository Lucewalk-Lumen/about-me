#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gates.py — workbuddy-expert-studio 包级子门禁统一模块（单一职责、零第三方依赖）。

合并原五个散落子门禁脚本（成员结构六要素 / 主文件长度 / 清单条目 / 链接死链 / 路径安全）
的判据逻辑，消除重复的 pkg_root() 与各脚本间不一致的调用方式。

对外暴露两类接口：
  ① *_check(pkg) -> (ok_list, warn_list, fail_list)
     供 verify.py 直接调用，聚合成包级 [OK]/[WARN]/[FAIL] 报告，不再经 subprocess 碎裂调用。
  ② deadlink_scan(pkg) / traversal_scan(pkg) / embedded_version_scan(pkg, expected) / emoji_scan(pkg, chars)
     供 dual_proof.py 复用做绿红双证（签名与旧脚本保持一致）。

用法：python3 scripts/gates.py [-h] [包根]   # 作为 CLI 时逐项打印并退出
退出码：0 = 无 WARN 且无 FAIL；1 = 仅 WARN；2 = 有 FAIL
"""
import argparse
import json
import os
import py_compile
import re
import shutil
import subprocess
import sys
import tempfile

# ---------------------------------------------------------------------------
# 阈值：唯一事实源是 toolkit 的 contract.yaml（本模块只留「契约缺失时」的内置兜底）
# ---------------------------------------------------------------------------

DEFAULT_LENGTH_WARN_LIMIT = 18000
DEFAULT_MEMBERS_ALLOWED_FIELDS = ("id", "name", "profession", "avatar", "role")
# 头像最小体积（bytes）：正式插画头像远大于此；占位实色 PNG（约 4KB）会被判红
DEFAULT_MIN_AVATAR_BYTES = 10240


def _contract_path(pkg):
    return os.path.join(pkg, "skills", "workbuddy-expert-studio-toolkit", "contract.yaml")


def load_contract_thresholds(pkg):
    """从 contract.yaml 读取本模块用到的阈值，返回 dict。

    键：length_warn_limit / members_allowed_fields / avatar_min_bytes。
    contract.yaml 是「唯一事实源」；仅在文件缺失/不可读时退回内置默认，避免脚本各写一份。
    """
    th = {
        "length_warn_limit": DEFAULT_LENGTH_WARN_LIMIT,
        "members_allowed_fields": list(DEFAULT_MEMBERS_ALLOWED_FIELDS),
        "avatar_min_bytes": DEFAULT_MIN_AVATAR_BYTES,
    }
    p = _contract_path(pkg)
    if not os.path.exists(p):
        return th
    try:
        with open(p, encoding="utf-8", errors="ignore") as fh:
            lines = fh.read().splitlines()
    except Exception:  # noqa: BLE001
        return th
    for line in lines:
        m = re.match(r"\s*warn_limit:\s*(\d+)", line)
        if m:
            th["length_warn_limit"] = int(m.group(1))
        m = re.match(r"\s*min_bytes:\s*(\d+)", line)
        if m:
            th["avatar_min_bytes"] = int(m.group(1))
        m = re.match(r"\s*members_allowed_fields:\s*\[(.*?)\]", line)
        if m:
            th["members_allowed_fields"] = [x.strip().strip('"').strip("'")
                                            for x in m.group(1).split(",") if x.strip()]
    return th


# ---------------------------------------------------------------------------
# 构成门禁：成员文档结构六要素（角色定义 / 擅长领域 / 分析框架 /
# 数据获取 / 结构化输出 / 回传要求）。标题命中=通过；仅正文子串=WARN；皆无=FAIL。
# 主理人按编排角色豁免形状检查。
# ---------------------------------------------------------------------------

COMPOSITION_ELEMENTS = ["角色定义", "擅长领域", "分析框架", "数据获取", "结构化输出", "回传要求"]


def _composition_check(pkg):
    """返回 (ok_list, warn_list, fail_list)。"""
    ok, warn, fail = [], [], []
    pj = os.path.join(pkg, ".codebuddy-plugin", "plugin.json")
    if not os.path.exists(pj):
        warn.append("composition: 未找到 plugin.json，跳过")
        return ok, warn, fail
    try:
        with open(pj, encoding="utf-8") as fh:
            d = json.load(fh)
    except Exception as e:  # noqa: BLE001
        fail.append(f"composition: plugin.json 解析失败 {e}")
        return ok, warn, fail

    ti = d.get("teamInfo", {})
    lead = ti.get("leadAgent") or d.get("agentName")
    members = [m.get("id") for m in d.get("members", [])]
    agents_dir = os.path.join(pkg, "agents")

    checked, bad, weak_any = 0, 0, False
    for mid in members:
        if mid == lead:
            continue  # 主理人按编排角色豁免
        fp = os.path.join(agents_dir, f"{mid}.md")
        if not os.path.exists(fp):
            fail.append(f"composition: 成员文件缺失 {mid}.md")
            bad += 1
            continue
        with open(fp, encoding="utf-8", errors="ignore") as fh:
            txt = fh.read()
        weak = [e for e in COMPOSITION_ELEMENTS if not _heading_hit(txt, e) and e in txt]
        miss = [e for e in COMPOSITION_ELEMENTS if e not in txt]
        checked += 1
        if miss:
            fail.append(f"composition: {mid}.md 缺结构要素 {miss}")
            bad += 1
        elif weak:
            # C9：跨成员累积，避免「某中间成员 warn + 末尾成员干净」时仍打印『六要素齐全』
            weak_any = True
            warn.append(f"composition: {mid}.md 结构要素仅正文子串、未作标题 {weak}")

    if bad == 0 and not weak_any:
        ok.append(f"composition: {checked} 个成员 agent 结构六要素齐全（lead 豁免）")
    return ok, warn, fail


def _heading_hit(txt, element):
    return any(re.match(r"^#{1,6}\s*" + re.escape(element), line) for line in txt.splitlines())


# ---------------------------------------------------------------------------
# 长度门禁：主文件 code points 长度 <= contract.yaml 的 warn_limit
# （与平台 fs.readFile 口径一致，CRLF 计 2）。
# ---------------------------------------------------------------------------


def _length_check(pkg):
    ok, warn, fail = [], [], []
    warn_limit = load_contract_thresholds(pkg)["length_warn_limit"]
    files = []
    agents = os.path.join(pkg, "agents")
    if os.path.isdir(agents):
        for f in sorted(os.listdir(agents)):
            if f.endswith(".md"):
                files.append(os.path.join(agents, f))
    # 全部 skills/*/SKILL.md 纳入（不只 toolkit —— 修漏检 web-crawler 的问题）
    skills_dir = os.path.join(pkg, "skills")
    if os.path.isdir(skills_dir):
        for sk in sorted(os.listdir(skills_dir)):
            sp = os.path.join(skills_dir, sk, "SKILL.md")
            if os.path.exists(sp):
                files.append(sp)
    over = 0
    for fp in files:
        with open(fp, "rb") as fh:
            data = fh.read()
        n = len(data.decode("utf-8", "replace"))  # CRLF 计 2，与平台口径一致
        rel = os.path.relpath(fp, pkg)
        if n > warn_limit:
            warn.append(f"length: {rel}: 长度 {n} > {warn_limit}，建议分片")
            over += 1
        else:
            ok.append(f"length: {rel}: 长度 {n}")
    if over:
        fail.append(f"length: {over} 个文件超长")
    else:
        ok.append(f"length: 全部文件 <= {warn_limit}")
    return ok, warn, fail


# ---------------------------------------------------------------------------
# 清单门禁：plugin.json 声明的 agents[] 与 skills[] 在磁盘上都存在（C005）。
# ---------------------------------------------------------------------------

def _shard_check(pkg):
    ok, warn, fail = [], [], []
    pj = os.path.join(pkg, ".codebuddy-plugin", "plugin.json")
    if not os.path.exists(pj):
        fail.append("shard: plugin.json 缺失")
        return ok, warn, fail
    with open(pj, encoding="utf-8") as fh:
        d = json.load(fh)
    missing = 0
    for a in d.get("agents", []):
        fp = os.path.join(pkg, a)
        if not os.path.exists(fp):
            fail.append(f"shard: agents 条目缺失: {a}")
            missing += 1
        else:
            ok.append(f"shard: agents 条目存在: {a}")
    for s in d.get("skills", []):
        fp = os.path.join(pkg, s)
        if not os.path.isdir(fp):
            fail.append(f"shard: skills 条目缺失: {s}")
            missing += 1
        else:
            ok.append(f"shard: skills 条目存在: {s}")
    if missing:
        fail.append(f"shard: {missing} 条目标缺失")
    else:
        ok.append("shard: 清单条目全部存在")
    return ok, warn, fail


# ---------------------------------------------------------------------------
# 头像门禁：落实知识库第 9 条「头像文件全部可达、无断链」+ 体积门禁（防占位图顶替正式图）。
# ---------------------------------------------------------------------------

def avatar_refs(pkg):
    """返回 (引用列表, fail_list)。引用列表为 (来源说明, 相对路径)。"""
    refs, fail = [], []
    pj = os.path.join(pkg, ".codebuddy-plugin", "plugin.json")
    if not os.path.exists(pj):
        fail.append("avatar: 未找到 plugin.json")
        return refs, fail
    try:
        with open(pj, encoding="utf-8") as fh:
            d = json.load(fh)
    except Exception as e:  # noqa: BLE001
        fail.append(f"avatar: plugin.json 解析失败 {e}")
        return refs, fail
    if d.get("avatar"):
        refs.append(("顶层 avatar", d["avatar"]))
    for m in d.get("members", []):
        if m.get("avatar"):
            refs.append((f"成员 {m.get('id')}", m["avatar"]))
        else:
            fail.append(f"avatar: 成员 {m.get('id')} 未声明 avatar")
    return refs, fail


def _avatar_check(pkg):
    ok, warn, fail = [], [], []
    min_bytes = load_contract_thresholds(pkg)["avatar_min_bytes"]
    refs, pre_fail = avatar_refs(pkg)
    fail.extend(pre_fail)
    if not refs:
        if not pre_fail:
            warn.append("avatar: 未发现任何头像引用，跳过")
        return ok, warn, fail

    n_ok = 0
    for who, rel in refs:
        fp = os.path.join(pkg, rel)
        if not os.path.exists(fp):
            fail.append(f"avatar: 断链/缺失 {who} -> {rel}")
            continue
        size = os.path.getsize(fp)
        if size < min_bytes:
            fail.append(f"avatar: {who} -> {rel} 体积 {size}B < {min_bytes}B"
                        f"（疑似占位图未替换为插画风格头像，违反知识库第 9 条）")
            continue
        n_ok += 1
    if n_ok == len(refs) and not fail:
        ok.append(f"avatar: {n_ok} 个头像文件全部可达且体积达标（>= {min_bytes}B）")
    return ok, warn, fail


# ---------------------------------------------------------------------------
# 脚本可执行性门禁（R2 治本）：scripts/*.py 与 skills/*/scripts/*.py 逐个
#  ① py_compile（语法可编译，失败即 FAIL）；
#  ② 对声明了 CLI（argparse / -h / --help / --self-test）的脚本执行 `<script> --help`
#     冒烟（import 期崩溃 / 参数解析崩溃 / NameError 等运行期必崩缺陷，非零退出即 FAIL）。
# 这样 R1（脚本必崩）、R3 类缺陷会在出厂前被自己的门禁拦住。
# ---------------------------------------------------------------------------

_CLI_HINT = re.compile(r"argparse|--help|--self-test|[\"']-h[\"']")


def iter_py_scripts(pkg):
    """枚举包内脚本：scripts/*.py 与 skills/*/scripts/*.py。"""
    out = []
    sd = os.path.join(pkg, "scripts")
    if os.path.isdir(sd):
        for f in sorted(os.listdir(sd)):
            if f.endswith(".py"):
                out.append(os.path.join(sd, f))
    skd = os.path.join(pkg, "skills")
    if os.path.isdir(skd):
        for sk in sorted(os.listdir(skd)):
            sdir = os.path.join(skd, sk, "scripts")
            if os.path.isdir(sdir):
                for f in sorted(os.listdir(sdir)):
                    if f.endswith(".py"):
                        out.append(os.path.join(sdir, f))
    return out


def _exec_check(pkg):
    ok, warn, fail = [], [], []
    scripts = iter_py_scripts(pkg)
    if not scripts:
        ok.append("exec: 未发现脚本")
        return ok, warn, fail
    tmpd = tempfile.mkdtemp(prefix="gates_pyc_")
    n_compile = n_help = 0
    try:
        for fp in scripts:
            rel = os.path.relpath(fp, pkg)
            # ① 语法可编译性
            try:
                py_compile.compile(fp, cfile=os.path.join(tmpd, os.path.basename(fp) + ".pyc"),
                                   doraise=True)
                n_compile += 1
            except py_compile.PyCompileError as e:
                msg = getattr(e, "msg", None) or str(e)
                fail.append(f"exec: {rel} 语法编译失败: {msg}")
                continue
            except Exception as e:  # noqa: BLE001
                fail.append(f"exec: {rel} 编译异常: {type(e).__name__}: {e}")
                continue
            # ② 声明了 CLI 的脚本做 --help 冒烟（捕捉 import/运行期必崩）
            try:
                with open(fp, encoding="utf-8", errors="ignore") as fh:
                    src = fh.read()
            except Exception:  # noqa: BLE001
                src = ""
            if not _CLI_HINT.search(src):
                continue
            try:
                r = subprocess.run([sys.executable, fp, "--help"],
                                   capture_output=True, text=True, timeout=30)
            except subprocess.TimeoutExpired:
                fail.append(f"exec: {rel} --help 超时（>30s）")
                continue
            if r.returncode != 0:
                lines = (r.stderr or r.stdout or "").strip().splitlines()
                tail = lines[-1] if lines else "无输出"
                fail.append(f"exec: {rel} --help 退出码 {r.returncode}: {tail}")
                continue
            n_help += 1
    finally:
        shutil.rmtree(tmpd, ignore_errors=True)
    if not fail:
        ok.append(f"exec: {n_compile} 个脚本可编译，{n_help} 个 CLI 脚本 --help 冒烟通过")
    return ok, warn, fail


# ---------------------------------------------------------------------------
# 死链门禁：md 链接 + 反引号路径引用的三基准解析（包根 / 所在目录 / 上级目录）。
# ---------------------------------------------------------------------------

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
CODE_RE = re.compile(r"`([^`\n]+?)`")
CODE_EXT = (".py", ".md", ".json", ".yaml", ".yml", ".html", ".htm",
            ".sh", ".csv", ".tsv", ".txt", ".png", ".jpg", ".js", ".svg")
# 仅校验以包内顶层目录开头的反引号路径（运行期工作目录路径如 `01-诊断/…` 不在此列）
PKG_PREFIXES = ("scripts/", "skills/", "references/", "knowledge/", "agents/",
                "avatars/", "assets/", ".codebuddy-plugin/")


def _resolve(pkg, md_path, ref):
    if ref.startswith(("http://", "https://", "#", "mailto:")):
        return "external"
    ref = ref.split("#")[0].split("?")[0]
    if not ref:
        return "external"
    baselines = [pkg, os.path.dirname(md_path),
                 os.path.dirname(os.path.dirname(md_path))]
    for b in baselines:
        cand = os.path.normpath(os.path.join(b, ref))
        if os.path.exists(cand):
            return cand
    return None


def deadlink_scan(pkg):
    """扫描 pkg 下全部 md，返回 (md 链接数, 路径引用数, 死链消息列表)。供 dual_proof 复用。"""
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
                ref = m.group(1)
                n_link += 1
                if _resolve(pkg, fp, ref) is None:
                    broken.append(f"死链 {os.path.relpath(fp, pkg)}: ({ref})")
            for m in CODE_RE.finditer(txt):
                ref = m.group(1).strip()
                if (not ref or " " in ref or "/" not in ref
                        or not ref.startswith(PKG_PREFIXES)
                        or not ref.endswith(CODE_EXT)
                        or any(c in ref for c in "*?<>")):  # 跳过通配 / 占位符
                    continue
                n_code += 1
                if _resolve(pkg, fp, ref) is None:
                    broken.append(f"悬空路径引用 {os.path.relpath(fp, pkg)}: `{ref}`")
    return n_link, n_code, broken


def _deadlink_check(pkg):
    ok, warn, fail = [], [], []
    n_link, n_code, broken = deadlink_scan(pkg)
    for b in broken:
        fail.append(f"deadlink: {b}")
    ok.append(f"deadlink: 检查 {n_link} 个 md 链接 + {n_code} 个路径引用, 死链 {len(broken)}")
    if broken:
        fail.append(f"deadlink: {len(broken)} 处死链")
    return ok, warn, fail


# ---------------------------------------------------------------------------
# 路径安全门禁：本机绝对路径泄露 / 数据驱动绝对路径拼接（七维①安全）。
# ---------------------------------------------------------------------------

# 要求路径段以字母数字开头，避免把占位符 `/Users/...` 误判为本机路径
ABS = re.compile(r"(/Users/[A-Za-z0-9][^ \"'\t\n\r]*"
                 r"|C:\\\\Users\\\\[A-Za-z0-9][^ \"'\t\n\r]*"
                 r"|/home/[A-Za-z0-9][^ \"'\t\n\r]*)")
TRAVERSAL_TEXT_EXT = (".json", ".yaml", ".yml", ".py", ".js", ".sh", ".html", ".htm",
                      ".md", ".txt", ".csv", ".tsv", ".toml", ".cfg", ".ini", ".R")


def traversal_scan(pkg):
    """返回 (扫描文件数, 命中列表)。"""
    n, hits = 0, []
    for root, _dirs, files in os.walk(pkg):
        if ".git" in root or "__pycache__" in root:
            continue
        for f in files:
            if not f.endswith(TRAVERSAL_TEXT_EXT):
                continue
            fp = os.path.join(root, f)
            n += 1
            with open(fp, encoding="utf-8", errors="ignore") as fh:
                txt = fh.read()
            for m in ABS.finditer(txt):
                hits.append(f"{os.path.relpath(fp, pkg)}: {m.group(1)}")
    return n, hits


def _traversal_check(pkg):
    ok, warn, fail = [], [], []
    n, hits = traversal_scan(pkg)
    for h in hits:
        fail.append(f"traversal: 本机绝对路径 {h}")
    if hits:
        fail.append(f"traversal: {len(hits)} 处绝对路径泄露")
    else:
        ok.append(f"traversal: 扫描 {n} 个文本文件，无本机绝对路径泄露、无数据驱动绝对路径拼接")
    return ok, warn, fail


def heading_pollution_scan(pkg):
    """扫描 agents/*.md 的围栏代码块内是否出现 `## ` 二级标题（K10 标题污染）。

    输出契约等模板在代码块内展示时，章节标题必须用 `### N.`（三级）或纯文本编号，
    禁止 `##`（二级）——否则渲染器把它当文档自身的章节标题，污染目录、误导章节统计。
    返回命中列表 [(相对路径, 行号, 行内容)]。
    """
    hits = []
    adir = os.path.join(pkg, "agents")
    if not os.path.isdir(adir):
        return hits
    fence_re = re.compile(r"^\s*```")
    h2_re = re.compile(r"^##\s+\S")
    for fn in sorted(os.listdir(adir)):
        if not fn.endswith(".md"):
            continue
        fp = os.path.join(adir, fn)
        with open(fp, encoding="utf-8", errors="ignore") as fh:
            lines = fh.read().splitlines()
        in_code = False
        for i, line in enumerate(lines, 1):
            if fence_re.match(line):
                in_code = not in_code
                continue
            if in_code and h2_re.match(line):
                hits.append((os.path.relpath(fp, pkg), i, line.strip()))
    return hits


def _heading_pollution_check(pkg):
    ok, warn, fail = [], [], []
    hits = heading_pollution_scan(pkg)
    for rel, ln, content in hits:
        fail.append(f"heading: {rel}:{ln} 代码块内二级标题（应用 ### 或纯文本）: {content}")
    if hits:
        fail.append(f"heading: {len(hits)} 处代码块内标题污染（K10）")
    else:
        ok.append("heading: agents/*.md 代码块内无二级标题污染（K10 已守）")
    return ok, warn, fail



# ---------------------------------------------------------------------------
# 版本单一真源 / G004 emoji 的**可复用扫描函数**（供 verify.py 与 dual_proof.py 共用，
# 避免 dual_proof 自写重实现副本 —— G003 精神）。
# ---------------------------------------------------------------------------

def embedded_version_scan(pkg, expected):
    """扫描 skills/ 与 scripts/ 下的 .py/.js/.sh 中的 `/x.y.z` 版本串。

    返回 (embedded_list, bad_list)：embedded 为 [(相对路径, 版本串)]；
    bad 为与 expected 不一致的子集。

    正则用前后界排除「更长的点分数字（如 IP 127.0.0.1 / 169.254.169.254 /
    93.184.216.34）」——它们不是版本号，旧式 `/(\\d+\\.\\d+\\.\\d+)` 会把 IP 误判为版本漂移
    （假阳性 / 冤枉好人）。故要求 `/x.y.z` 的 z 后**不再是数字或点**、且 x 前不再是数字或点。

    斜杠前须是**标识符字符**（字母 / 数字 / 下划线 / 连字符）：真实的内嵌版本串形如
    `<标识符>/x.y.z`（本包 UA 串即此式），必带标识符前缀；而「斜杠 + 三段数字」的文档片段
    （如注释里写出 `/93.184.216`）没有标识符前缀，不再被误判。此约束修的是**假红**
    （G003：假红与假绿同等对待）——曾实测：docstring 里写该片段会把 verify.py 逼成 FAIL。
    回归夹具见 `scripts/dual_proof.py` 的 `embedded_version_scan` 绿红双证。
    """
    embedded = []
    ver_re = re.compile(r"(?<=[A-Za-z0-9_-])/(\d+\.\d+\.\d+)(?![\d.])")
    for base in ("skills", "scripts"):
        bd = os.path.join(pkg, base)
        if not os.path.isdir(bd):
            continue
        for root, _dirs, files in os.walk(bd):
            for fn in files:
                if not fn.endswith((".py", ".js", ".sh")):
                    continue
                fp = os.path.join(root, fn)
                with open(fp, encoding="utf-8", errors="ignore") as fh:
                    src = fh.read()
                for m in ver_re.finditer(src):
                    embedded.append((os.path.relpath(fp, pkg), m.group(1)))
    bad = [(f, v) for f, v in embedded if v != expected]
    return embedded, bad


def emoji_scan(pkg, emoji_chars):
    """扫描 scripts/ 与 skills/ 下的 .py 是否含 emoji 字符（G004）。返回命中文件相对路径列表。"""
    hits = []
    for base in ("scripts", "skills"):
        bd = os.path.join(pkg, base)
        if not os.path.isdir(bd):
            continue
        for root, _dirs, files in os.walk(bd):
            for fn in files:
                if not fn.endswith(".py"):
                    continue
                fp = os.path.join(root, fn)
                with open(fp, encoding="utf-8", errors="ignore") as fh:
                    txt = fh.read()
                if any(e in txt for e in emoji_chars):
                    hits.append(os.path.relpath(fp, pkg))
    return hits


# ---------------------------------------------------------------------------
# 统一调度
# ---------------------------------------------------------------------------

# 顺序即门禁执行次序；verify.py 按此顺序聚合并打印。
ALL_CHECKS = [
    ("composition", _composition_check),
    ("length", _length_check),
    ("shard", _shard_check),
    ("avatar", _avatar_check),
    ("deadlink", _deadlink_check),
    ("traversal", _traversal_check),
    ("heading", _heading_pollution_check),
    ("exec", _exec_check),
]


def run_all(pkg):
    """运行全部子门禁，返回聚合的 (ok_list, warn_list, fail_list)。"""
    ok, warn, fail = [], [], []
    for _name, fn in ALL_CHECKS:
        o, w, f = fn(pkg)
        ok.extend(o)
        warn.extend(w)
        fail.extend(f)
    return ok, warn, fail


def build_parser():
    ap = argparse.ArgumentParser(
        prog="gates.py",
        description="workbuddy-expert-studio 包级子门禁：构成/长度/清单/头像/死链/路径安全/脚本可执行性。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="退出码：0 = 无 WARN 且无 FAIL；1 = 仅 WARN；2 = 有 FAIL")
    ap.add_argument("pkg", nargs="?", default=None, help="包根目录（默认脚本上级目录）")
    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)
    pkg = args.pkg or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if not os.path.isdir(pkg):
        print(f"[FAIL] gates: 包根不是已存在的目录: {pkg}", file=sys.stderr)
        sys.exit(2)
    ok, warn, fail = run_all(pkg)
    print("=" * 56)
    print(f"gates.py · OK={len(ok)} WARN={len(warn)} FAIL={len(fail)}")
    for m in ok:
        print(f"  [OK]   {m}")
    for m in warn:
        print(f"  [WARN] {m}")
    for m in fail:
        print(f"  [FAIL] {m}")
    print("=" * 56)
    sys.exit(2 if fail else (1 if warn else 0))


if __name__ == "__main__":
    main()
