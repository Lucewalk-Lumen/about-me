#!/usr/bin/env python3
"""workbuddy-expert-studio 包级门禁（判据来源：toolkit 的 contract.yaml + 知识库第 5 节合规硬指标）。

零第三方依赖，仅标准库。从包根运行：python3 scripts/verify.py
  python3 scripts/verify.py                         # 包级总门禁（无 zip 参时跳过 zip 结构判据并提示）
  python3 scripts/verify.py --zip <包>.zip          # 附加 zip 条目结构判据（顶层前缀唯一 == name）
退出码：0 = 无 WARN 且无 FAIL；1 = 仅 WARN；2 = 有 FAIL
"""
import argparse
import hashlib
import json
import os
import re
import sys
import unicodedata
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)  # <pkg>/

# 统一子门禁模块（零第三方依赖，同目录）
sys.path.insert(0, HERE)
import gates  # noqa: E402

# 默认判据（当 contract.yaml 缺失时回退；正常情况以 contract.yaml 为唯一事实源）
DEFAULT_CATEGORY_IDS = {
    "01-ProductDesign", "02-Engineering", "03-GameSpatial", "04-DataAI",
    "05-MarketingGrowth", "06-ContentCreative", "07-SalesCommerce",
    "08-FinanceInvestment", "09-OperationsHR", "10-ProjectQuality",
    "11-SecurityCompliance", "12-IndustryConsultant", "13-TencentZone",
    "14-WorldWise", "15-Education",
}
# members[] 允许字段的唯一事实源是 contract.yaml 的 manifest.members_allowed_fields
DEFAULT_MEMBER_FIELDS = ("id", "name", "profession", "avatar", "role")
DEFAULT_RULES = {"cjk_min": 40, "cjk_max": 50, "tags": 3, "qp": 3,
                 "members_allowed_fields": tuple(DEFAULT_MEMBER_FIELDS)}
# plugin.json 顶层已知字段（官方 schema）。含官方合法可选字段（skills/homepage/license/
# keywords/dependencies 等），**不可照搬 members[] 的严格白名单**，否则会误伤合法可选字段。
KNOWN_TOP_FIELDS = {
    "name", "version", "description", "author", "agents", "skills", "expertType",
    "agentName", "teamInfo", "displayName", "profession", "displayDescription",
    "avatar", "categoryId", "defaultInitPrompt", "plugin", "tags", "quickPrompts", "members",
    # 官方合法可选字段 / 展示型扩展（不得当未知字段误伤）
    "homepage", "license", "keywords", "dependencies", "display_name", "display_name_en",
    "category", "allowed-tools", "disable-model-invocation", "user-invocable",
    "icon", "readme", "repository", "scripts", "mcpServers", "connectors",
}
# G004：脚本输出不得用 emoji（用 [OK]/[WARN]/[FAIL] 纯文本标记）
# 用码点构造，避免本文件自身含 emoji 字面量而自伤
EMOJI_CHARS = "".join(chr(c) for c in (0x2705, 0x274C, 0x1F534, 0x1F7E0, 0x1F7E1,
                                       0x1F7E2, 0x1F535, 0x26A0, 0x1F680, 0x1F527))

OK, WARN, FAIL = [], [], []


def ok(m):
    OK.append(m)


def warn(m):
    WARN.append(m)


def fail(m):
    FAIL.append(m)


def cjk_count(s):
    return sum(1 for c in s if "CJK" in unicodedata.name(c, ""))


def load_contract(pkg):
    """从 toolkit 的 contract.yaml 读取判据（categoryId 枚举 + 合规硬指标阈值）。

    零第三方依赖：只解析本文件用到的 YAML 子集（顶层列表 + manifest 标量）。
    返回 (category_ids, rules, found)：found=False 表示未见 contract.yaml。
    """
    p = os.path.join(pkg, "skills", "workbuddy-expert-studio-toolkit", "contract.yaml")
    if not os.path.exists(p):
        return set(DEFAULT_CATEGORY_IDS), dict(DEFAULT_RULES), False
    cats, rules, in_cats = set(), dict(DEFAULT_RULES), False
    try:
        with open(p, encoding="utf-8", errors="ignore") as fh:
            lines = fh.read().splitlines()
    except Exception:
        return set(DEFAULT_CATEGORY_IDS), dict(DEFAULT_RULES), False
    for line in lines:
        if line.startswith("category_ids:"):
            in_cats = True
            continue
        if in_cats:
            s = line.strip()
            if s.startswith("- "):
                cats.add(s[2:].strip().strip('"').strip("'"))
                continue
            if s and not s.startswith("#"):
                in_cats = False
        m = re.match(r"\s*display_description_cjk_(min|max):\s*(\d+)", line)
        if m:
            rules["cjk_" + m.group(1)] = int(m.group(2))
        m = re.match(r"\s*tags_count:\s*(\d+)", line)
        if m:
            rules["tags"] = int(m.group(1))
        m = re.match(r"\s*quick_prompts_count:\s*(\d+)", line)
        if m:
            rules["qp"] = int(m.group(1))
        m = re.match(r"\s*members_allowed_fields:\s*\[(.*?)\]", line)
        if m:
            rules["members_allowed_fields"] = tuple(
                x.strip().strip('"').strip("'") for x in m.group(1).split(",") if x.strip())
    return (cats or set(DEFAULT_CATEGORY_IDS)), rules, True


def frontmatter_name(fp):
    """读取 agent md 的 frontmatter name 字段。"""
    try:
        with open(fp, encoding="utf-8", errors="ignore") as fh:
            txt = fh.read()
    except Exception:
        return None
    m = re.match(r"^---\s*\n(.*?)\n---", txt, re.S)
    if not m:
        return None
    mm = re.search(r"^name:\s*(\S+)\s*$", m.group(1), re.M)
    return mm.group(1) if mm else None


def report():
    print("=" * 56)
    print(f"verify.py · OK={len(OK)} WARN={len(WARN)} FAIL={len(FAIL)}")
    for m in OK:
        print(f"  [OK]   {m}")
    for m in WARN:
        print(f"  [WARN] {m}")
    for m in FAIL:
        print(f"  [FAIL] {m}")
    print("=" * 56)
    sys.exit(2 if FAIL else (1 if WARN else 0))


def build_parser():
    ap = argparse.ArgumentParser(
        prog="verify.py",
        description="workbuddy-expert-studio 包级门禁（plugin.json 字段 / 版本真源 / 一致性 / 子门禁 / zip 结构）。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="退出码：0 = 无 WARN 且无 FAIL；1 = 仅 WARN；2 = 有 FAIL")
    ap.add_argument("pkg", nargs="?", default=None, help="包根目录（默认脚本上级目录）")
    ap.add_argument("--zip", dest="zip_path", default=None,
                    help="待校验的成品 zip 路径（可选；提供则附加 zip 条目结构判据）")
    return ap


def main(argv=None):
    global PKG
    args = build_parser().parse_args(argv)
    if args.pkg:
        PKG = os.path.abspath(args.pkg)
    zip_path = args.zip_path
    CATEGORY_IDS, RULES, has_contract = load_contract(PKG)
    if has_contract:
        ok(f"已从 contract.yaml 读取判据（categoryId {len(CATEGORY_IDS)} 类 / CJK {RULES['cjk_min']}-{RULES['cjk_max']}）")
    else:
        warn("未找到 contract.yaml，回退内置默认判据")

    pj = os.path.join(PKG, ".codebuddy-plugin", "plugin.json")
    if not os.path.exists(pj):
        fail("plugin.json 缺失")
        return report()
    with open(pj, encoding="utf-8") as fh:
        d = json.load(fh)

    name = d.get("name")
    plugin = d.get("plugin")
    if name != plugin:
        fail(f"plugin({plugin}) != name({name})")
    else:
        ok("plugin == name")

    top = os.path.basename(os.path.abspath(PKG))
    if top == name:
        ok("name == 顶层目录名")
    else:
        # 保留为提示、severity 不升：该判据双向失真（换目录名即假阴性、合规包改名即假阳性），
        # 权威判据是 `--zip` 的 zip 条目前缀判据（不可被目录命名绕过）。
        warn(f"顶层目录名({top}) != name({name})")

    # plugin.json 顶层未知字段：WARN + 列出字段名（不照搬 members[] 严格白名单，避免误伤官方可选字段）
    unknown_top = sorted(set(d.keys()) - KNOWN_TOP_FIELDS)
    if unknown_top:
        warn(f"plugin.json 顶层未知字段（请核对官方 schema，勿自采字段）: {unknown_top}")
    else:
        ok("plugin.json 顶层字段均在已知集合内")

    au = d.get("author", {})
    if not au.get("email"):
        fail("author.email 缺失（官方 author 为 {name, email}）")
    else:
        ok(f"author.email 已声明（{au.get('email')}）")

    zh = d.get("displayDescription", {}).get("zh", "")
    n = cjk_count(zh)
    if not (RULES["cjk_min"] <= n <= RULES["cjk_max"]):
        fail(f"displayDescription.zh CJK={n} 不在 {RULES['cjk_min']}-{RULES['cjk_max']}（len 整串={len(zh)}）")
    else:
        ok(f"displayDescription.zh CJK={n} / len={len(zh)}")

    if len(d.get("tags", [])) != RULES["tags"]:
        fail(f"tags 数={len(d.get('tags', []))} != {RULES['tags']}")
    else:
        ok(f"tags == {RULES['tags']}")
    if len(d.get("quickPrompts", [])) != RULES["qp"]:
        fail(f"quickPrompts 数={len(d.get('quickPrompts', []))} != {RULES['qp']}")
    else:
        ok(f"quickPrompts == {RULES['qp']}")

    dip = d.get("defaultInitPrompt", {})
    qp0 = d.get("quickPrompts", [{}])[0]
    if dip.get("zh") != qp0.get("zh") or dip.get("en") != qp0.get("en"):
        fail("defaultInitPrompt != quickPrompts[0]")
    else:
        ok("defaultInitPrompt == quickPrompts[0]")

    if d.get("expertType") != "team":
        fail(f"expertType={d.get('expertType')} != team")
    else:
        ok("expertType == team")

    # profession 与 displayName 保持一致（知识库第 5 节第 7 条）
    dn = d.get("displayName", {})
    pf = d.get("profession", {})
    for lang in ("zh", "en"):
        a, b = dn.get(lang, ""), pf.get(lang, "")
        if not a or not b:
            warn(f"displayName.{lang} / profession.{lang} 缺一，无法核对一致性")
        elif a in b or b in a:
            ok(f"profession.{lang} 与 displayName.{lang} 一致")
        else:
            warn(f"profession.{lang}({b}) 未包含 displayName.{lang}({a})，请核对一致性")

    ti = d.get("teamInfo", {})
    lead = ti.get("leadAgent")
    members_ids = [m["id"] for m in d.get("members", [])]
    if not (lead == members_ids[0] == d.get("agentName")):
        fail(f"teamInfo.leadAgent({lead}) != members[0]({members_ids[0]}) != agentName({d.get('agentName')})")
    else:
        ok("teamInfo.leadAgent == members[0] == agentName")

    bad = set()
    allowed_member_fields = set(RULES.get("members_allowed_fields") or DEFAULT_MEMBER_FIELDS)
    for m in d.get("members", []):
        bad |= (set(m.keys()) - allowed_member_fields)
    if bad:
        fail(f"members 多余字段: {sorted(bad)}")
    else:
        ok(f"members 字段合规（仅 {'/'.join(sorted(allowed_member_fields))}）")

    if d.get("categoryId") not in CATEGORY_IDS:
        fail(f"categoryId={d.get('categoryId')} 不在 {len(CATEGORY_IDS)} 类枚举")
    else:
        ok("categoryId 合法")

    agents_dir = os.path.join(PKG, "agents")
    agent_files = {f[:-3] for f in os.listdir(agents_dir) if f.endswith(".md")} if os.path.isdir(agents_dir) else set()
    if set(members_ids) != agent_files:
        only_members = set(members_ids) - agent_files
        only_files = agent_files - set(members_ids)
        fail(f"members/agents 不一致: 仅成员侧={only_members} 仅文件侧={only_files}")
    else:
        ok("members id 集合 == agents 文件集合（四方一致之一）")

    # 四方一致之二：每个 agent 文件 frontmatter.name 须等于其成员 id
    fm_bad = []
    for mid in members_ids:
        fp = os.path.join(agents_dir, f"{mid}.md")
        fm = frontmatter_name(fp) if os.path.exists(fp) else None
        if fm != mid:
            fm_bad.append((mid, fm))
    if fm_bad:
        fail(f"agent frontmatter.name 与成员 id 不一致: {fm_bad}")
    else:
        ok("agents/*.md frontmatter.name == members id（四方一致之二）")

    sj = os.path.join(PKG, "settings.json")
    if os.path.exists(sj):
        with open(sj, encoding="utf-8") as fh:
            sa = json.load(fh).get("agent")
        if sa != lead:
            fail(f"settings.json.agent({sa}) != lead({lead})")
        else:
            ok("settings.json.agent == lead")
    else:
        warn("settings.json 缺失")

    # 版本单一真源：plugin.version vs CHANGELOG / 内嵌脚本常量
    ver = str(d.get("version", ""))
    cl = os.path.join(PKG, "CHANGELOG.md")
    if os.path.exists(cl):
        with open(cl, encoding="utf-8", errors="ignore") as fh:
            txt = fh.read()
        if re.search(rf"##\s*v?{re.escape(ver)}\b", txt) or ver in txt:
            ok(f"CHANGELOG 含版本 {ver}")
        else:
            warn(f"CHANGELOG 未检出版本 {ver}")
    # 内嵌版本串（如 web-crawler user-agent 中的 /x.y.z）须与 plugin.version 一致
    # （复用 gates.embedded_version_scan —— 单一实现，dual_proof 亦调用同一函数做双证）
    embedded, bad_ver = gates.embedded_version_scan(PKG, ver)
    if bad_ver:
        fail(f"内嵌版本串与 plugin.version({ver}) 不一致: {bad_ver}")
    elif embedded:
        ok(f"内嵌版本串一致（{len(embedded)} 处 == {ver}）")
    else:
        ok("无内嵌版本串（版本单一真源仅 plugin.json/CHANGELOG）")

    # G004：脚本输出不得用 emoji（用 [OK]/[WARN]/[FAIL] 纯文本标记）
    # （复用 gates.emoji_scan —— 单一实现，dual_proof 亦调用同一函数做双证）
    emoji_hits = gates.emoji_scan(PKG, EMOJI_CHARS)
    if emoji_hits:
        fail(f"脚本输出含 emoji（违反 G004）: {emoji_hits}")
    else:
        ok("脚本无 emoji 输出（G004 已守）")

    # 技能 SKILL.md frontmatter：官方必填 description / description_zh / description_en / version / author
    sk_bad = []
    for fn in ("workbuddy-expert-studio-toolkit", "workbuddy-expert-studio-web-crawler"):
        sp = os.path.join(PKG, "skills", fn, "SKILL.md")
        if not os.path.exists(sp):
            sk_bad.append(f"{fn}: SKILL.md 缺失")
            continue
        with open(sp, encoding="utf-8", errors="ignore") as fh:
            sk_src = fh.read()
        fm = re.match(r"^---\s*\n(.*?)\n---", sk_src, re.S)
        block = fm.group(1) if fm else ""
        miss = [k for k in ("description", "description_zh", "description_en", "version", "author")
                if not re.search(rf"^{k}:", block, re.M)]
        if miss:
            sk_bad.append(f"{fn}: 缺 {miss}")
    if sk_bad:
        fail(f"技能 SKILL.md frontmatter 不合规: {sk_bad}")
    else:
        ok("技能 SKILL.md frontmatter 齐全（description/_zh/_en/version/author）")

    # 知识库 manifest 哈希锚：content_sha256 须与快照实测一致，漂移 WARN（提示重锚）
    man_p = os.path.join(PKG, "knowledge", "standards-manifest.json")
    snap_p = os.path.join(PKG, "knowledge", "workbuddy-expert-studio-standards.md")
    if os.path.exists(man_p) and os.path.exists(snap_p):
        try:
            with open(man_p, encoding="utf-8") as fh:
                man = json.load(fh)
            with open(snap_p, "rb") as fh:
                actual = hashlib.sha256(fh.read()).hexdigest()
            if man.get("content_sha256") == actual:
                ok("知识库 manifest 哈希锚与快照一致")
            else:
                warn(f"知识库 manifest 哈希锚漂移（manifest={str(man.get('content_sha256'))[:12]} 快照={actual[:12]}），请重锚")
        except Exception as e:
            warn(f"知识库 manifest 读取异常: {e}")
    else:
        ok("无知识库 manifest（跳过哈希锚检查）")

    # zip 结构判据（权威、不可被目录命名绕过）：zip 全部条目的顶层前缀须唯一等于包名 name。
    # 说明：dirname 判据（顶层目录名）双向失真，仅作提示；真正防「换目录名绕过」靠本判据。
    if zip_path:
        if not os.path.exists(zip_path):
            fail(f"zip: 文件不存在 {zip_path}")
        else:
            try:
                names = zipfile.ZipFile(zip_path).namelist()
            except Exception as e:  # noqa: BLE001
                fail(f"zip: 无法读取 {zip_path}: {e}")
            else:
                tops = {n.split("/")[0] for n in names if n.strip()}
                if tops != {name}:
                    fail(f"zip: 顶层条目前缀 {sorted(tops)} != {{'{name}'}}（不合规打包：须有且仅有 {name}/ 一个顶层目录）")
                else:
                    ok(f"zip: 顶层条目前缀唯一为 {name}（{len(names)} 条，结构合规）")
    else:
        warn("zip: 未提供 --zip，跳过 zip 结构判据（打包后请以 `python3 scripts/verify.py --zip <包>.zip` 复核）")

    # 子门禁（统一模块 gates.py，直接调用，不再经 subprocess 碎裂）
    g_ok, g_warn, g_fail = gates.run_all(PKG)
    OK.extend(g_ok)
    WARN.extend(g_warn)
    FAIL.extend(g_fail)
    return report()


if __name__ == "__main__":
    main()
