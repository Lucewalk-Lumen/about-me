#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify.py — Mplus 统计教练 · 包级门禁（阶段 4/5/6 共用）

设计原则（对齐 harness 铁律 4：能写成 Linter 的约束，别写成文档）
    每条硬红线都**可代码化强制**；输出 FAIL 即阻断上线，WARN 为提审前应修项。
    门禁**不查「本仓库是否有匹配」**，而查「该匹配是否全部通过」——
    避免「零匹配 = 通过」的伪绿。

检查维度
    A 结构（8）      目录 / 路径 / 三方一致 / 头像可达与体积
    B 硬指标（6）    displayDescription 字数 / tags·quickPrompts 数 / 默认首条一致 等
    C P0 门禁（9）   禁内置原文 / 禁全量加载 / 禁 emoji / 禁 AI 模板味 / 双输入声明
    D 一致性（5）    索引 ↔ 语料 ↔ 事实三层同源；JSON / py_compile；版本真源
    E 卫生（2）      __pycache__ / .DS_Store / 空文件 / 绝对路径泄漏
    F frontmatter（4）Agent 与 SKILL.md 官方必填项 / 交叉一致 / 字段体系不混用

用法
    python3 scripts/verify.py --pkg <包根>
    python3 scripts/verify.py --pkg <包根> --strict      # WARN 亦致 FAIL
    python3 scripts/verify.py --pkg <包根> --json        # 机器可读
"""
import argparse
import json
import os
import py_compile
import re
import struct
import subprocess
import sys
import tempfile

CATEGORY_IDS = {
    "01-ProductDesign", "02-Engineering", "03-GameSpatial", "04-DataAI",
    "05-MarketingGrowth", "06-ContentCreative", "07-SalesCommerce",
    "08-FinanceInvestment", "09-OperationsHR", "10-ProjectQuality",
    "11-SecurityCompliance", "12-IndustryConsultant", "13-TencentZone",
    "14-WorldWise", "15-Education",
}

# P0-4：包内**禁止出现**的扩展名（原文类资产一律不入包）
BANNED_EXT = {".pdf", ".dat", ".dgm", ".gh5", ".zip", ".sav", ".dta", ".xlsx",
              ".xls", ".pptx", ".ppt", ".docx", ".doc", ".out", ".png2", ".jpg",
              ".mp4", ".msi", ".pkg", ".properties", ".csv", ".ipynb"}

# 头像等白名单（允许的二进制）
ALLOWED_BIN = {"avatars/mplus-stats-coach.png"}

CJK = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")

# ---------------------------------------------------------------------------
# P0-1 emoji 检出：**只**判「图形化 emoji」，不误伤排版符号。
#   ⚠ 自指坑（实测）：若把箭头 / 几何符号一并算 emoji，会命中 U+2190–U+21FF 与
#   U+2713 / U+2717，进而误报正常文档。P0-1 的原意是「禁用 emoji 作功能图标」，故：
#     命中集 = 图形化码位段（U+1F000–U+1FAFF / 区域旗 / 变体选择符 / 键帽）
#              + 明确按 emoji 使用的符号（U+2705 U+274C U+2757 U+2753 U+2795
#                U+2796 U+2B50 U+2B55 U+2728）
#     放行集 = 排版符号（箭头 / 数学符号 / U+2713 U+2717 U+26A0 · § × ≈ ≤ ≥ ≠）
#   ⚠ 本文件**不得**出现上述 emoji 的字面量，否则扫描器会被自己命中。
# ---------------------------------------------------------------------------
EMOJI_PICTO = re.compile(
    "[\U0001F000-\U0001FAFF\U0001F1E6-\U0001F1FF\U0000FE0F\U000020E3]"
)
EMOJI_ICON = re.compile("[\u2705\u274C\u2757\u2753\u2795\u2796\u2B50\u2B55\u2728]")
EMOJI = re.compile("(?:" + EMOJI_PICTO.pattern + "|" + EMOJI_ICON.pattern + ")")

TEMPLATE_SMELL = [r"Lorem ipsum", r"easeOutBounce", r"\bbounce\b"]

# C2 / C4 / C9 的扫描面：**只扫会被注入上下文的文本**，不扫 scripts/
# （脚本里出现 `knowledge/` 路径是职责所在，不是「全量加载语料」）。
INJECTABLE_PREFIX = ("agents/", "skills/", "references/", "knowledge/")
INJECTABLE_TOP = ("README.md", "CHANGELOG.md", "UPGRADE.md")

# P0 红线 ID（C10 要求**全部**在注入类文档中有条文，缺一条即判红）
P0_IDS = ("P0-0a", "P0-0b", "P0-0c", "P0-0d", "P0-1", "P0-2",
          "P0-3", "P0-4", "P0-5", "P0-6")


def is_injectable(rel):
    r = rel.replace(os.sep, "/")
    return r.startswith(INJECTABLE_PREFIX) or r in INJECTABLE_TOP

TEXT_EXT = {".md", ".json", ".jsonl", ".py", ".txt", ".yaml", ".yml"}

MAIN_LIMIT = 18000
SHARD_LIMIT = 8000

# 头像门禁（官方：PNG 推荐 · 512×512 · 单张 ≤500KB · 漫画/插画风格）
# 下界参照工作坊契约 avatar.min_bytes=10240：实色占位 PNG 约 4–5KB，须判红。
AVATAR_MIN = 10240
AVATAR_MAX = 512000
AVATAR_SIDE = 512


class Report:
    def __init__(self):
        self.items = []

    def add(self, level, code, msg):
        self.items.append({"level": level, "code": code, "msg": msg})

    def fail(self, code, msg):
        self.add("FAIL", code, msg)

    def warn(self, code, msg):
        self.add("WARN", code, msg)

    def ok(self, code, msg):
        self.add("OK", code, msg)

    def counts(self):
        c = {"FAIL": 0, "WARN": 0, "OK": 0}
        for it in self.items:
            c[it["level"]] += 1
        return c


def walk_files(pkg):
    for root, dirs, files in os.walk(pkg):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git")]
        for fn in files:
            yield os.path.relpath(os.path.join(root, fn), pkg)


# ---------------- A 结构 ----------------
def check_structure(pkg, rep):
    pj = os.path.join(pkg, ".codebuddy-plugin", "plugin.json")
    if not os.path.exists(pj):
        rep.fail("A1", "缺 .codebuddy-plugin/plugin.json")
        return None
    try:
        cfg = json.load(open(pj, encoding="utf-8"))
    except json.JSONDecodeError as e:
        rep.fail("A1", "plugin.json 非法 JSON：%s" % e)
        return None
    rep.ok("A1", "plugin.json 存在且 JSON 合法")

    top = os.path.basename(os.path.abspath(pkg))
    trio = {cfg.get("name"), cfg.get("plugin"), top}
    if len(trio) != 1:
        rep.fail("A2", "name/plugin/顶层目录名 三方不一致：%s" % sorted(str(x) for x in trio))
    else:
        rep.ok("A2", "name == plugin == 顶层目录名（%s）" % top)

    if cfg.get("expertType") not in ("agent", "team"):
        rep.fail("A3", "expertType 非 agent/team：%r" % cfg.get("expertType"))
    else:
        rep.ok("A3", "expertType = %s" % cfg["expertType"])

    agents = cfg.get("agents") or []
    missing = [a for a in agents if not os.path.exists(os.path.join(pkg, a.lstrip("./")))]
    if not agents:
        rep.fail("A4", "agents[] 为空")
    elif missing:
        rep.fail("A4", "agents[] 路径不存在：%s" % missing)
    else:
        stem = os.path.splitext(os.path.basename(agents[0]))[0]
        if cfg.get("agentName") != stem:
            rep.fail("A4", "agentName(%r) != agents[0] stem(%r)" % (cfg.get("agentName"), stem))
        else:
            rep.ok("A4", "agents[] 可达且 agentName 与主文件一致（%s）" % stem)

    sk_missing = []
    for s in cfg.get("skills") or []:
        d = os.path.join(pkg, s.lstrip("./"))
        if not os.path.isdir(d) or not os.path.exists(os.path.join(d, "SKILL.md")):
            sk_missing.append(s)
    if cfg.get("skills") and sk_missing:
        rep.fail("A5", "skills[] 缺 SKILL.md：%s" % sk_missing)
    elif cfg.get("skills"):
        rep.ok("A5", "skills[] 全部含 SKILL.md（%d 个）" % len(cfg["skills"]))

    st = os.path.join(pkg, "settings.json")
    if not os.path.exists(st):
        rep.fail("A6", "缺 settings.json")
    else:
        try:
            s = json.load(open(st, encoding="utf-8"))
            if s.get("agent") != cfg.get("agentName"):
                rep.fail("A6", "settings.json.agent(%r) != agentName(%r)" % (s.get("agent"), cfg.get("agentName")))
            else:
                rep.ok("A6", "settings.json.agent 指向主 Agent")
        except json.JSONDecodeError as e:
            rep.fail("A6", "settings.json 非法 JSON：%s" % e)

    av = cfg.get("avatar")
    if not av:
        rep.fail("A7", "缺 avatar 字段")
    elif not os.path.exists(os.path.join(pkg, av)):
        rep.fail("A7", "avatar 指向的文件不存在：%s" % av)
    else:
        ap = os.path.join(pkg, av)
        nb = os.path.getsize(ap)
        if nb < AVATAR_MIN:
            rep.fail("A7", "avatar 仅 %d 字节 < %d —— 判为占位实色图（官方要求漫画/插画风格）：%s"
                     % (nb, AVATAR_MIN, av))
        elif nb > AVATAR_MAX:
            rep.fail("A7", "avatar %d 字节 > 单张上限 %d：%s" % (nb, AVATAR_MAX, av))
        else:
            rep.ok("A7", "avatar 可达且体积合规（%d 字节，区间 %d–%d）" % (nb, AVATAR_MIN, AVATAR_MAX))
            # 尺寸（PNG IHDR）→ 推荐 512×512，不符只 WARN
            try:
                with open(ap, "rb") as fh:
                    head = fh.read(24)
                if head[:8] == b"\x89PNG\r\n\x1a\n":
                    w, h = struct.unpack(">II", head[16:24])
                    if (w, h) != (AVATAR_SIDE, AVATAR_SIDE):
                        rep.warn("A7", "avatar 尺寸 %dx%d != 推荐 %dx%d" % (w, h, AVATAR_SIDE, AVATAR_SIDE))
                    else:
                        rep.ok("A7b", "avatar 尺寸 %dx%d == 官方推荐" % (w, h))
                else:
                    rep.warn("A7", "avatar 非 PNG（官方推荐 PNG）：%s" % av)
            except (OSError, struct.error) as e:
                rep.warn("A7", "avatar 尺寸不可解析：%s" % e)

    if not os.path.exists(os.path.join(pkg, "README.md")):
        rep.warn("A8", "缺 README.md")
    else:
        rep.ok("A8", "README.md 存在")

    # A9：非官方枚举目录必须自带口径声明（D5）
    # 官方「基础结构」枚举里没有 knowledge/；本包保留它，则必须把「这是非官方目录」写在
    # 地图文件的 §零，避免被后来人误当成官方支持、也避免该段被静默删掉。
    EXTRA_DIRS = ("knowledge",)
    for d in EXTRA_DIRS:
        dp = os.path.join(pkg, d)
        if not os.path.isdir(dp):
            continue
        idx = os.path.join(dp, "INDEX.md")
        if not os.path.exists(idx):
            rep.fail("A9", "%s/ 属官方未枚举目录，但缺 %s/INDEX.md 承载口径声明" % (d, d))
            continue
        head = open(idx, encoding="utf-8").read(4000)
        if "非官方" not in head:
            rep.fail("A9", "%s/INDEX.md 未声明「非官方枚举」，口径段疑似被删——"
                            "须写明该目录不在官方基础结构枚举内" % d)
        else:
            rep.ok("A9", "%s/ 已声明为非官方枚举目录并给出迁移路径" % d)
    return cfg


# ---------------- B 硬指标 ----------------
def check_metrics(cfg, rep):
    if cfg is None:
        return
    dd = (cfg.get("displayDescription") or {}).get("zh", "")
    n = len(CJK.findall(dd))
    if 40 <= n <= 50:
        rep.ok("B1", "displayDescription.zh CJK 字数 = %d（落在 40–50）" % n)
    else:
        rep.fail("B1", "displayDescription.zh CJK 字数 = %d，须在 40–50" % n)

    for key, want in (("tags", 3), ("quickPrompts", 3)):
        v = cfg.get(key) or []
        if len(v) != want:
            rep.fail("B2", "%s 长度 = %d，须固定 %d" % (key, len(v), want))
        else:
            rep.ok("B2", "%s = %d 条" % (key, want))

    dip = cfg.get("defaultInitPrompt") or {}
    qp0 = (cfg.get("quickPrompts") or [{}])[0]
    bad = [k for k in ("zh", "en") if dip.get(k) != qp0.get(k)]
    if bad:
        rep.fail("B3", "defaultInitPrompt != quickPrompts[0]（差异字段：%s）" % bad)
    else:
        rep.ok("B3", "defaultInitPrompt == quickPrompts[0]（zh/en 双向一致）")

    # B4 依据专家智能体官方规范（open.workbuddy.cn/docs/expert）：displayName 为市场展示名称
    # （人名位，官方示例 Diana/黛安娜），profession 为职业头衔——二者是独立字段，官方示例不同；
    # 「必须相等」是专家团（/docs/expert-team）的规则，不适用于 expertType=agent。
    dn, pf = cfg.get("displayName") or {}, cfg.get("profession") or {}
    bads = {k: [y for y in ("zh", "en")
                if not isinstance(v.get(y), str) or not v.get(y).strip()]
            for k, v in (("displayName", dn), ("profession", pf))}
    if any(bads.values()):
        rep.fail("B4", "displayName/profession 缺失或双语不齐：%s" % bads)
    elif dn == pf:
        rep.warn("B4", "displayName == profession（专家智能体规范下二者为不同字段："
                       "displayName=人名、profession=职业头衔，建议区分）")
    else:
        rep.ok("B4", "displayName=%s/%s（人名位）；profession=%s/%s（职业头衔位）——双语齐备且已区分"
               % (dn.get("zh"), dn.get("en"), pf.get("zh"), pf.get("en")))

    cid = cfg.get("categoryId")
    if cid not in CATEGORY_IDS:
        rep.fail("B5", "categoryId 不在 15 类枚举内：%r" % cid)
    else:
        rep.ok("B5", "categoryId = %s ∈ 15 类" % cid)

    if not (cfg.get("author") or {}).get("email"):
        rep.warn("B6", "author.email 缺失（上架前须补全）")
    else:
        rep.ok("B6", "author 信息齐备")


# ---------------- C P0 门禁 ----------------
def check_p0(pkg, cfg, rep):
    files = list(walk_files(pkg))

    # P0-4 禁内置原文
    hits = []
    for f in files:
        ext = os.path.splitext(f)[1].lower()
        if ext in BANNED_EXT and f.replace(os.sep, "/") not in ALLOWED_BIN:
            hits.append(f)
    if hits:
        rep.fail("C1", "P0-4 包内出现禁止的内置原文类文件 %d 个（例：%s）" % (len(hits), hits[:5]))
    else:
        rep.ok("C1", "P0-4 无 PDF/.out/.dat/.dgm/.gh5/.zip/.sav 等原文类文件")

    # P0-5 禁全量加载语料（只扫会被注入的文本；脚本内出现 knowledge/ 路径属职责所在）
    pat = re.compile(r"@\s*knowledge\b|@knowledge/(official|facts|\.\.)", re.I)
    bad = []
    for f in files:
        if not is_injectable(f):
            continue
        if os.path.splitext(f)[1].lower() not in TEXT_EXT:
            continue
        t = open(os.path.join(pkg, f), encoding="utf-8", errors="replace").read()
        if pat.search(t):
            bad.append(f)
    if bad:
        rep.fail("C2", "P0-5 存在对语料目录的整体引用：%s" % bad)
    else:
        rep.ok("C2", "P0-5 无对 knowledge/ 子目录的整体引用（扫描面：注入类文本 %d 个规则）"
               % len(INJECTABLE_PREFIX))

    # P0-1 禁 emoji（图形化 emoji，不含排版符号）
    emo = []
    for f in files:
        if os.path.splitext(f)[1].lower() not in TEXT_EXT:
            continue
        t = open(os.path.join(pkg, f), encoding="utf-8", errors="replace").read()
        m = EMOJI.search(t)
        if m:
            emo.append("%s(U+%04X)" % (f, ord(m.group(0))))
    if emo:
        rep.fail("C3", "P0-1 检出图形化 emoji：%s" % emo[:5])
    else:
        rep.ok("C3", "P0-1 无图形化 emoji（排版符号如箭头 / ✓ / ⚠ 已放行）")

    # P0-3 AI 模板味（只扫注入类文本 + md/json 的裸 hex 色值；.py 不扫，避免正则字面量自指）
    smell = []
    for f in files:
        if not is_injectable(f):
            continue
        ext = os.path.splitext(f)[1].lower()
        if ext not in TEXT_EXT:
            continue
        t = open(os.path.join(pkg, f), encoding="utf-8", errors="replace").read()
        for p in TEMPLATE_SMELL:
            if re.search(p, t):
                smell.append("%s <- %s" % (f, p))
        if re.search(r"#[0-9a-fA-F]{6}\b", t):
            smell.append("%s <- 裸 hex 色值" % f)
    if smell:
        rep.warn("C4", "P0-3 疑似 AI 模板味：%s" % smell[:5])
    else:
        rep.ok("C4", "P0-3 无 AI 模板味命中")

    # P0-6 双输入声明：check_inp.py 源码内必须含该声明文案
    ci = os.path.join(pkg, "skills", "mplus-syntax-lab", "scripts", "check_inp.py")
    if not os.path.exists(ci):
        rep.warn("C5", "未找到 check_inp.py，P0-6 声明未核")
    else:
        t = open(ci, encoding="utf-8", errors="replace").read()
        if "仅覆盖语法层" not in t:
            rep.fail("C5", "P0-6 check_inp.py 缺「仅覆盖语法层」声明文案")
        else:
            rep.ok("C5", "P0-6 双输入覆盖率声明存在")

    # P0-0b 运行状态闸门：不得出现伪造的 RUN_VERIFIED 常量
    bad0 = []
    for f in files:
        if os.path.splitext(f)[1].lower() != ".py":
            continue
        t = open(os.path.join(pkg, f), encoding="utf-8", errors="replace").read()
        if re.search(r"verification_status\s*=\s*[\"']RUN_VERIFIED[\"']", t):
            bad0.append(f)
    if bad0:
        rep.fail("C6", "P0-0b 检出硬编码 RUN_VERIFIED：%s" % bad0)
    else:
        rep.ok("C6", "P0-0b 无硬编码 RUN_VERIFIED")

    # 主文件 / 分片字符上限
    main = os.path.join(pkg, "agents", "%s.md" % (cfg or {}).get("agentName", "mplus-stats-coach"))
    if os.path.exists(main):
        n = len(open(main, encoding="utf-8").read())
        if n > MAIN_LIMIT:
            rep.fail("C7", "主文件 %d 字符 > %d，须分片" % (n, MAIN_LIMIT))
        else:
            rep.ok("C7", "主文件 %d 字符 ≤ %d" % (n, MAIN_LIMIT))
    else:
        rep.warn("C7", "主文件未找到：%s" % main)

    over = []
    for f in files:
        base = os.path.basename(f)
        if base == "SKILL.md" or "/references/" in f.replace(os.sep, "/"):
            n = len(open(os.path.join(pkg, f), encoding="utf-8", errors="replace").read())
            if n > SHARD_LIMIT:
                over.append("%s(%d)" % (f, n))
    if over:
        rep.fail("C8", "分片超 %d 字符：%s" % (SHARD_LIMIT, over))
    else:
        rep.ok("C8", "全部 SKILL.md / references 分片 ≤ %d 字符" % SHARD_LIMIT)

    # 绝对路径泄漏（只扫注入类文本；脚本内的正则字面量不算泄漏）
    leak = []
    for f in files:
        if not is_injectable(f):
            continue
        if os.path.splitext(f)[1].lower() not in TEXT_EXT:
            continue
        t = open(os.path.join(pkg, f), encoding="utf-8", errors="replace").read()
        if "/Users/" in t or "/Volumes/" in t:
            leak.append(f)
    if leak:
        rep.warn("C9", "检出绝对路径（打包前须清理）：%s" % leak[:5])
    else:
        rep.ok("C9", "无 /Users/ 或 /Volumes/ 绝对路径泄漏")

    # P0 红线 ID 全量落地：少一条就是「红线表有洞」——读者会以为那条根本不存在。
    # （实测前例：P0-2 只写在脚本 docstring 里，主 Agent 红线表里没有，属真实漏项。）
    body = []
    for f in walk_files(pkg):
        if not is_injectable(f) or os.path.splitext(f)[1].lower() not in TEXT_EXT:
            continue
        body.append(open(os.path.join(pkg, f), encoding="utf-8", errors="replace").read())
    blob = "\n".join(body)
    lack = [p for p in P0_IDS if p not in blob]
    if lack:
        rep.fail("C10", "以下 P0 红线在注入类文档中无条文落地（红线表有洞）：%s" % lack)
    else:
        rep.ok("C10", "P0 红线 %d 条全部在注入类文档中落地" % len(P0_IDS))


# ---------------- D 一致性 ----------------
def check_consistency(pkg, rep):
    # JSON / JSONL 合法性 + py_compile
    bad_json, bad_py, empty = [], [], []
    n_py = 0
    for f in walk_files(pkg):
        p = os.path.join(pkg, f)
        ext = os.path.splitext(f)[1].lower()
        if os.path.getsize(p) == 0:
            empty.append(f)
        if ext == ".json":
            try:
                json.load(open(p, encoding="utf-8"))
            except json.JSONDecodeError as e:
                bad_json.append("%s: %s" % (f, e))
        elif ext == ".jsonl":
            with open(p, encoding="utf-8") as fh:
                for i, line in enumerate(fh, 1):
                    if not line.strip():
                        continue
                    try:
                        json.loads(line)
                    except json.JSONDecodeError as e:
                        bad_json.append("%s:%d %s" % (f, i, e))
                        break
        elif ext == ".py":
            n_py += 1
            out = tempfile.mkdtemp()
            try:
                py_compile.compile(p, cfile=os.path.join(out, "x.pyc"), doraise=True)
            except py_compile.PyCompileError as e:
                bad_py.append("%s: %s" % (f, str(e).splitlines()[0]))
    if bad_json:
        rep.fail("D1", "JSON/JSONL 非法：%s" % bad_json[:3])
    else:
        rep.ok("D1", "全部 JSON / JSONL 合法")
    if bad_py:
        rep.fail("D2", "py_compile 失败：%s" % bad_py[:3])
    else:
        rep.ok("D2", "%d 个 .py 全部编译通过" % n_py)
    if empty:
        rep.warn("D3", "存在空文件：%s" % empty[:5])
    else:
        rep.ok("D3", "无空文件")

    # 三层同源：cases.jsonl ↔ 包内 .inp ↔ case-facts
    idx = os.path.join(pkg, "knowledge", "cases.jsonl")
    if not os.path.exists(idx):
        rep.fail("D4", "缺 knowledge/cases.jsonl")
    else:
        rows = [json.loads(l) for l in open(idx, encoding="utf-8") if l.strip()]
        # ⚠ 口径（本轮修正）：D4 的「包内 .inp」只指数**语料层** `knowledge/official/` 下的官方示例。
        #   原实现数全包 `.inp`，会把 `skills/*/templates/inp-skeletons/` 下**自编骨架**一并计入，
        #   得出「索引 519 != 包内 527」（差 8 = 8 个骨架）——那是**口径错误**，不是真的漏索引。
        #   两层都点清：语料层必须与索引逐条对齐；语料层之外的 `.inp` 单独报数，防止被误当漏项。
        all_inp = [f.replace(os.sep, "/") for f in walk_files(pkg) if f.endswith(".inp")]
        corpus_inp = [f for f in all_inp if f.startswith("knowledge/official/")]
        tmpl_inp = [f for f in all_inp if not f.startswith("knowledge/official/")]
        n_inp = len(corpus_inp)
        no_url = [r["id"] for r in rows if not r.get("source_url")]
        bad_p = [r["id"] for r in rows if not os.path.exists(os.path.join(pkg, r.get("inp_path") or ""))]
        outside = [r["id"] for r in rows
                   if not (r.get("inp_path") or "").replace(os.sep, "/").startswith("knowledge/official/")]
        prob = []
        if len(rows) != n_inp:
            prob.append("索引 %d 条 != 语料层 .inp %d 份" % (len(rows), n_inp))
        if no_url:
            prob.append("缺 source_url %d 条" % len(no_url))
        if bad_p:
            prob.append("inp_path 失效 %d 条" % len(bad_p))
        if outside:
            prob.append("索引指向语料层之外 %d 条" % len(outside))
        if prob:
            rep.fail("D4", "索引 ↔ 语料 不一致：%s" % prob)
        else:
            rep.ok("D4", "索引 %d 条 ↔ 语料层 .inp %d 份 ↔ source_url 齐备（另有自编骨架 %d 份，不计入语料口径）"
                   % (len(rows), n_inp, len(tmpl_inp)))

        cf = os.path.join(pkg, "knowledge", "facts", "case-facts.jsonl")
        if not os.path.exists(cf):
            rep.fail("D5", "缺 knowledge/facts/case-facts.jsonl")
        else:
            want = {r["id"] for r in rows if r.get("facts_id")}
            got = {json.loads(l)["id"] for l in open(cf, encoding="utf-8") if l.strip()}
            if want != got:
                rep.fail("D5", "事实层与索引 facts_id 不一致：缺 %d / 多 %d"
                         % (len(want - got), len(got - want)))
            else:
                rep.ok("D5", "事实层与索引 facts_id 完全一致（%d 条）" % len(got))

    # 版本单一真源
    ver = (json.load(open(os.path.join(pkg, ".codebuddy-plugin", "plugin.json"), encoding="utf-8"))
           if os.path.exists(os.path.join(pkg, ".codebuddy-plugin", "plugin.json")) else {})
    pver = ver.get("version")
    # 版本对齐（**本包发布的版本纪律**，非官方强制）：SKILL.md 的 version 必须与 plugin.json 一致。
    # 理由：上架件里有 4 处版本号（清单 + 3 个技能），若允许各自漂移，
    #      就会出现「包是 1.0.0、技能还是 0.1.0」这种无法解释的发布物。
    # 放宽条件：若将来确实需要技能独立版本，须**同时**在本注释与 08-版本/01-版本记录.md 说明。
    drift = []
    n_sk = 0
    skdir = os.path.join(pkg, "skills")
    if os.path.isdir(skdir):
        for d in sorted(os.listdir(skdir)):
            sm = os.path.join(skdir, d, "SKILL.md")
            if not os.path.exists(sm):
                continue
            n_sk += 1
            fm, _body, err = parse_frontmatter(open(sm, encoding="utf-8").read())
            if fm and fm.get("version") and _unq(str(fm["version"])) != pver:
                drift.append("%s: %s" % (d, _unq(str(fm["version"]))))
    if drift:
        rep.fail("D6", "SKILL.md 版本与 plugin.json(%s) 不一致：%s" % (pver, drift))
    else:
        rep.ok("D6", "版本单一真源 = plugin.json(%s)；%d 个 SKILL.md 版本均已对齐；CHANGELOG 不作为版本依据"
               % (pver, n_sk))

    # D7：警告口径必须**可从数据复算**（62 类键 / 39 种消息 / 219 条 / 90 份 .out）
    #     为什么单列一条：覆盖率（2/39 · 5.1%）是**对用户做承诺**的数字，
    #     一旦「39」变成拍脑袋的数，整套覆盖率表述就失去依据。
    #     故把归并规则（31-warning-taxonomy.md §一 R1/R2/R3）写成可执行的算式在此重算。
    wlp = os.path.join(pkg, "knowledge", "facts", "warning-library.jsonl")
    if not os.path.exists(wlp):
        rep.warn("D7", "缺 warning-library.jsonl，警告口径未复核")
    else:
        wl = [json.loads(l) for l in open(wlp, encoding="utf-8") if l.strip()]
        merges = {"INPUT LINE EXCEEDED 90 CHARACTERS": 13,
                  "ALL CONTINUOUS LATENT VARIABLE COVARIANCES INVOLVING": 10,
                  "THE LATENT VARIABLE COVARIANCE MATRIX (PSI) IN GROUP": 3}
        got = {}
        for pref in merges:
            got[pref] = [w.get("wclass_id") for w in wl if (w.get("class") or "").startswith(pref)]
        bad = ["%s 命中 %d 类（文档 %d）" % (p[:22], len(v), merges[p])
               for p, v in got.items() if len(v) != merges[p]]
        seen, dup = set(), False
        for v in got.values():
            dup = dup or bool(seen & set(v))
            seen |= set(v)
        n_msg = len(wl) - sum(len(v) - 1 for v in got.values())
        n_rec = sum(w.get("n", 0) for w in wl)
        n_files = len({c for w in wl for c in (w.get("cases") or [])})
        if bad or dup:
            rep.fail("D7", "警告口径不可复算：%s%s" % (bad, "（R1/R2/R3 互斥被破坏）" if dup else ""))
        elif (len(wl), n_msg, n_rec, n_files) != (62, 39, 219, 90):
            rep.fail("D7", "警告四口径与冻结值不符：类键 %d/62 · 消息 %d/39 · 条数 %d/219 · 文件 %d/90"
                     % (len(wl), n_msg, n_rec, n_files))
        else:
            rep.ok("D7", "警告四口径可复算且与冻结值一致：62 类键 / 39 种消息（R1–R3 互斥归并）/ 219 条 / 90 份 .out")


# ---------------- F frontmatter（官方 Agent / 技能定义规范） ----------------
# 官方依据（开放平台开发文档 · 专家(agent)/技能(skill) 规范）：
#   Agent 定义文件：**文件头部用 YAML frontmatter 声明配置**，正文为系统提示词。
#     必填 name / description / displayName{en,zh} / profession{en,zh}
#     可选 maxTurns（默认 50）/ skills（填技能**名称**，区别于 plugin.json 的**路径**）
#     官方明令：**开发者不可自行添加 tools**（工具权限由系统统一分配）
#   SKILL.md：必填 description / description_zh / description_en / version / author
#     可选 name / display_name / display_name_en / category / allowed-tools /
#          disable-model-invocation / user-invocable
#   ⚠ 两套字段体系**不可混用**（技能用 description_zh…，专家用 displayDescription…），
#     官方原话：混用会导致解析失败。
#   ⚠ 本包无 PyYAML → 自写**子集**解析器；解析不动的写法一律**不报 FAIL**
#     （门禁不得因解析器自身的缺陷误伤内容 —— 对齐 G007 的「不冤枉好人」）。

AGENT_REQUIRED = ("name", "description", "displayName", "profession")
SKILL_REQUIRED = ("description", "description_zh", "description_en", "version", "author")
# 字段体系混用检测（各自**不得**出现的对方专有键）
AGENT_FORBIDDEN = ("description_zh", "description_en", "display_name", "display_name_en")
SKILL_FORBIDDEN = ("displayDescription", "displayName", "categoryId", "avatar", "quickPrompts")


def _unq(v):
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in ("'", '"'):
        return v[1:-1]
    return v


def parse_frontmatter(text):
    """零依赖解析 YAML frontmatter 的**够用子集**。

    返回 (fm, body, err)：fm 支持「顶层标量 / 一层缩进子映射 / 顶层列表 / 块标量」。
    任何解析不动的写法都不抛异常、不置 err —— 门禁只对**确定缺字段**判红。
    """
    if not text.startswith("---"):
        return None, text, "文件未以 --- 开头（无 frontmatter）"
    end = text.find("\n---", 3)
    if end < 0:
        return None, text, "frontmatter 未闭合（缺结束的 --- 行）"
    raw, body = text[3:end], text[end + 4:]

    fm, lines, i = {}, raw.splitlines(), 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#") or line[0] in (" ", "\t"):
            i += 1
            continue
        if ":" not in line:
            i += 1
            continue
        key, _, val = line.partition(":")
        key, val = key.strip(), val.strip()

        if val in ("|", "|-", "|+", ">", ">-", ">+"):          # 块标量
            blk, j = [], i + 1
            while j < len(lines) and (lines[j].startswith((" ", "\t")) or not lines[j].strip()):
                blk.append(lines[j])
                j += 1
            joiner = "\n" if val.startswith("|") else " "
            fm[key] = joiner.join(b.lstrip() for b in blk if b.strip()).strip()
            i = j
            continue

        if val == "":                                          # 子映射或列表
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines) and lines[j].lstrip().startswith("- "):
                items = []
                while j < len(lines):
                    s = lines[j].strip()
                    if s.startswith("- "):
                        items.append(_unq(s[2:]))
                    elif s and not lines[j].startswith((" ", "\t")):
                        break
                    j += 1
                fm[key] = items
                i = j
                continue
            if j < len(lines) and lines[j].startswith((" ", "\t")) and ":" in lines[j]:
                sub = {}
                while j < len(lines):
                    ln = lines[j]
                    if not ln.strip():
                        j += 1
                        continue
                    if not ln.startswith((" ", "\t")):
                        break
                    if ":" in ln:
                        sk, _, sv = ln.partition(":")
                        sub[sk.strip()] = _unq(sv)
                    j += 1
                fm[key] = sub
                i = j
                continue
            fm[key], i = "", i + 1
            continue

        fm[key], i = _unq(val), i + 1
    return fm, body, None


def _is_dual(v):
    """{en, zh} 双语字段须两项皆非空。"""
    return isinstance(v, dict) and all((v.get(k) or "").strip() for k in ("en", "zh"))


def check_frontmatter(pkg, cfg, rep):
    cfg = cfg or {}
    agent_stem = cfg.get("agentName") or "mplus-stats-coach"
    apath = os.path.join(pkg, "agents", "%s.md" % agent_stem)

    # ---- F1 主 Agent frontmatter 必填齐全 ----
    if not os.path.exists(apath):
        rep.fail("F1", "主 Agent 文件不存在：agents/%s.md" % agent_stem)
        return
    a_fm, _, err = parse_frontmatter(open(apath, encoding="utf-8").read())
    if a_fm is None:
        rep.fail("F1", "主 Agent %s：%s" % (os.path.basename(apath), err))
        return
    lack = [k for k in AGENT_REQUIRED if not a_fm.get(k)]
    undual = [k for k in ("displayName", "profession") if not _is_dual(a_fm.get(k))]
    if lack or undual:
        rep.fail("F1", "主 Agent frontmatter 必填项缺失：%s%s"
                 % (lack, ("；双语字段 en/zh 不全：%s" % undual) if undual else ""))
    else:
        rep.ok("F1", "主 Agent frontmatter 必填 4 项齐全（name/description/displayName/profession，双语齐备）")

    # ---- F2 主 Agent ↔ plugin.json 交叉一致 ----
    bad = []
    if a_fm.get("name") != agent_stem:
        bad.append("frontmatter.name(%r) != agentName/文件名(%r)" % (a_fm.get("name"), agent_stem))
    for f, key in (("displayName", "displayName"), ("profession", "profession")):
        if a_fm.get(f) != cfg.get(key):
            bad.append("%s 与 plugin.json 不一致" % f)
    fm_sk = a_fm.get("skills")
    if isinstance(fm_sk, list):
        want = {os.path.basename(s.rstrip("/")) for s in (cfg.get("skills") or [])}
        got = set(fm_sk)
        if want and got != want:
            bad.append("frontmatter.skills 与 plugin.json.skills 不符：多 %s / 少 %s"
                       % (sorted(got - want), sorted(want - got)))
    if bad:
        rep.fail("F2", "主 Agent 与 plugin.json 交叉不一致：%s" % bad)
    else:
        rep.ok("F2", "主 Agent name/displayName/profession/skills 与 plugin.json 双向一致")

    # ---- F3 每个 SKILL.md 必填 5 项齐全 ----
    sdir = os.path.join(pkg, "skills")
    if not os.path.isdir(sdir):
        rep.warn("F3", "无 skills/ 目录，跳过 SKILL.md frontmatter 校验")
        return
    prob, n = [], 0
    for d in sorted(os.listdir(sdir)):
        sp = os.path.join(sdir, d, "SKILL.md")
        if not os.path.isfile(sp):
            continue
        n += 1
        s_fm, _, serr = parse_frontmatter(open(sp, encoding="utf-8").read())
        if s_fm is None:
            prob.append("%s：%s" % (d, serr))
            continue
        miss = [k for k in SKILL_REQUIRED if not s_fm.get(k)]
        if miss:
            prob.append("%s 缺 %s" % (d, miss))
    if not n:
        rep.warn("F3", "skills/ 下未找到 SKILL.md")
    elif prob:
        rep.fail("F3", "SKILL.md frontmatter 必填项不合规：%s" % prob)
    else:
        rep.ok("F3", "全部 %d 个 SKILL.md 必填 5 项齐全（description/_zh/_en/version/author）" % n)

    # ---- F4 字段体系不混用 + 禁用保留键 ----
    mix = []
    hit = [k for k in AGENT_FORBIDDEN if k in a_fm]
    if hit:
        mix.append("主 Agent 混入技能专有键 %s" % hit)
    if "tools" in a_fm:
        mix.append("主 Agent 出现官方禁止的 tools 键（工具权限由系统统一分配）")
    for d in sorted(os.listdir(sdir)):
        sp = os.path.join(sdir, d, "SKILL.md")
        if not os.path.isfile(sp):
            continue
        s_fm, _, _ = parse_frontmatter(open(sp, encoding="utf-8").read())
        if not isinstance(s_fm, dict):
            continue
        hit = [k for k in SKILL_FORBIDDEN if k in s_fm]
        if hit:
            mix.append("SKILL.md(%s) 混入专家专有键 %s" % (d, hit))
    if mix:
        rep.fail("F4", "字段体系混用/保留键违规：%s" % mix)
    else:
        rep.ok("F4", "Agent 与 SKILL 两套字段体系未混用；主 Agent 无 tools 键")


def check_hygiene(pkg, rep):
    junk = [f for f in walk_files(pkg)
            if "__pycache__" in f or f.endswith(".pyc") or f.endswith(".DS_Store")
            or os.path.basename(f) == ".DS_Store"]
    if junk:
        rep.fail("E1", "包内混入缓存/垃圾文件：%s" % junk[:5])
    else:
        rep.ok("E1", "无 __pycache__ / .pyc / .DS_Store")
    if os.path.exists(os.path.join(pkg, "CHANGELOG.md")):
        rep.ok("E2", "CHANGELOG.md 存在")
    else:
        rep.warn("E2", "缺 CHANGELOG.md")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pkg", required=True)
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    pkg = os.path.abspath(args.pkg)

    rep = Report()
    cfg = check_structure(pkg, rep)
    check_metrics(cfg, rep)
    check_p0(pkg, cfg, rep)
    check_consistency(pkg, rep)
    check_frontmatter(pkg, cfg, rep)
    check_hygiene(pkg, rep)

    c = rep.counts()
    if args.json:
        print(json.dumps({"counts": c, "items": rep.items}, ensure_ascii=False, indent=2))
    else:
        for it in rep.items:
            if it["level"] != "OK":
                print("[%-4s] %-4s %s" % (it["level"], it["code"], it["msg"]))
        print("-" * 68)
        print("OK=%d  WARN=%d  FAIL=%d" % (c["OK"], c["WARN"], c["FAIL"]))
        print("VERIFY %s" % ("PASSED" if c["FAIL"] == 0 and (not args.strict or c["WARN"] == 0) else "FAILED"))
    rc = 1 if c["FAIL"] else (1 if (args.strict and c["WARN"]) else 0)
    return rc


if __name__ == "__main__":
    sys.exit(main())
