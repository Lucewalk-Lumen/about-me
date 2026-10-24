#!/usr/bin/env python3
"""通用技能 / agent 包校验器（平台无关）

校验项：
  [结构]   SKILL.md 存在、frontmatter 含 name/description、name 与目录名一致
  [引用]   SKILL.md 引用的 references/scripts/assets 路径存在
  [编排]   plugin.json 的 agents/skills 条目均存在；agent frontmatter 的
           skills[] 均能解析到真实技能目录；lead/member 声明与 agents 列表一致
  [凭证]   token / api key / password / 私钥
  [PII]    绝对家目录路径、真实姓名、非占位邮箱
  [身份锁] 包级署名必须恒为 IDENTITY（默认 "Xing Bu <buxing@gdufe.edu.cn>"，即 plugin.json 的 author 字段）；
           单文件 author 字段为「可选」元数据，缺失不报错；仅当包内出现「其他（非 IDENTITY）署名」时才阻断。
  [卫生]   __pycache__ / *.pyc / .DS_Store / *.log 等不应入包的产物

退出码：0 通过，1 存在阻断项。
"""
import argparse
import json
import os
import re
import sys

sys.dont_write_bytecode = True  # 校验时不写 __pycache__，避免自检误报冗余产物

# ---------------------------------------------------------------- 常量配置

#: 不可更改的法定署名标识。任何包内出现的其他署名一律视为阻断项。
IDENTITY = "Xing Bu <buxing@gdufe.edu.cn>"
#: IDENTITY 拆分形态：结构化元数据（plugin.json / pyproject.toml）必须以 name+email 双字段表达，
#: 因此按拆分字段等价判定：同文件内同时出现「Xing Bu」与「buxing@gdufe.edu.cn」即视为合规。
IDENTITY_PARTS = ("Xing Bu", "buxing@gdufe.edu.cn")

#: 参与文本扫描的扩展名（含脚本、配置与文本类文件）。
SCAN_EXT = (
    ".md", ".py", ".js", ".mjs", ".cjs", ".ts", ".json",
    ".txt", ".toml", ".yaml", ".yml", ".html", ".css", ".sh",
)

#: 不应出现在发布包中的构建/系统产物。
DIRT_PATTERNS = ("__pycache__", ".pytest_cache", ".DS_Store", ".ipynb_checkpoints")
DIRT_SUFFIX = (".pyc", ".pyo", ".log", ".bak", ".orig", ".swp")
#: skills/ 下的非 skill 支撑目录：模板/参考/源代码/脚本/数据库/领域数据等，
#: 不应被当作未登记的 skill（用于复合型 skill 包的合理嵌套结构）。
NON_SKILL_DIRS = (
    "src", "scripts", "templates", "references", "agents",
    "db", "domains", "tests", "data", "assets", "examples",
    "schemas", "static", "utils", "lib", "core", "common",
    "_shared",  # 团队共享支撑目录（数据契约等），不是独立技能
    # 三级分组目录：真实技能嵌套在它们之下
    # （如 skills/case-writer）。这些只是层级容器，不是独立技能，
    # 且不应被当作「缺少 SKILL.md / 未登记孤儿」。校验时向下递归寻找真实技能。
    "domain", "foundation", "quality",
)

#: 凭证类敏感信息（仅匹配"赋值出现的值"，避免误伤对字段名的文档性列举）。
SENSITIVE_RE = re.compile(
    r"(?:"
    r"(?:aws|volcengine|aliyun|tencentcloud)[_-]?(?:access[_-]?key|secret[_-]?id|secret[_-]?key)\s*[=:]\s*[\"']?[A-Za-z0-9/+]{8,}|"
    r"api[_-]?key\s*[=:]\s*[\"']?[A-Za-z0-9]{12,}|"
    r"password\s*[=:]\s*[\"']?[^\s\"']{4,}|"
    r"access[_-]?token\s*[=:]\s*[\"']?[A-Za-z0-9._-]{12,}|"
    r"sk-[a-z0-9]{20,}|"
    r"-----BEGIN (?:RSA )?PRIVATE KEY-----"
    r")",
    re.IGNORECASE,
)

#: 开发机绝对路径。技能包必须可移植，一律改用 ~ 、环境变量或 CLI 参数。
ABS_PATH_RE = re.compile(r"(?:/Users/[A-Za-z0-9._-]+|/home/[A-Za-z0-9._-]+|[A-Z]:\\\\Users\\\\[A-Za-z0-9._-]+)")

#: 允许出现的占位邮箱，其余邮箱视为 PII。
EMAIL_ALLOWLIST = {"noreply@github.com", "noreply@example.com"}
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

#: 已知需要脱敏的实名 / 机构写法。命中即要求替换为 IDENTITY。
#: 注意：CJK 字面量一律用 \u 转义书写，否则本文件会扫到自己的正则源码而误报。
#: 说明：作者真实中文名未在包内确认（包内仅署名英文名 "Xing Bu"），故身份锁只依赖
#:       英文 name/email 精确匹配；此处不再列入可能误伤普通词语的汉字常量。
_ORG_CN = "\u5e7f\u4e1c\u8d22\u7ecf\u5927\u5b66"  # 机构全称（中文）
REALNAME_RE = re.compile(
    r"(?:Xing\s+Bu|" + _ORG_CN + r")",
    re.IGNORECASE,
)

#: 身份锁白名单：这些写法是合规的最终形态，不算实名泄露。
IDENTITY_OK_RE = re.compile(re.escape(IDENTITY))


def _author_name_matches(name):
    """author.name 是否命中身份锁英文名。

    容忍「Xing Bu（机构）」/「Xing Bu (org)」等带括号后缀的写法（机构/头衔标注），
    只要主干与 IDENTITY_PARTS[0] 精确一致即视为合规。
    """
    n = (name or "").strip()
    if n == IDENTITY_PARTS[0]:
        return True
    return bool(re.match(re.escape(IDENTITY_PARTS[0]) + r"\s*[（(]", n))


# ---------------------------------------------------------------- 工具函数

def read_text(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except OSError:
        return ""


def parse_frontmatter(md):
    """极简 frontmatter 解析：只取顶层 `key: value`，够用且无三方依赖。"""
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", md, re.DOTALL)
    if not m:
        return {}
    fm = {}
    for line in m.group(1).splitlines():
        if line.startswith((" ", "\t", "#")) or ":" not in line:
            continue
        k, v = line.split(":", 1)
        fm[k.strip()] = v.strip()
    return fm


def parse_list_field(raw):
    """解析 `skills: [a, b]` 这类内联数组。"""
    raw = (raw or "").strip()
    if not raw.startswith("["):
        return []
    inner = raw.strip("[]").strip()
    if not inner:
        return []
    return [x.strip().strip("\"'") for x in inner.split(",") if x.strip()]


def iter_scan_files(root):
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in DIRT_PATTERNS and d != ".git"]
        for fn in fns:
            if fn.endswith(SCAN_EXT):
                yield os.path.join(dp, fn)


# ---------------------------------------------------------------- 校验单元

def check_skill_dir(root, errors, warns, prefix=""):
    """校验单个技能目录（含 SKILL.md）。"""
    skill_md = os.path.join(root, "SKILL.md")
    if not os.path.isfile(skill_md):
        return False

    text = read_text(skill_md)
    fm = parse_frontmatter(text)
    dir_name = os.path.basename(root.rstrip("/"))

    if "name" not in fm:
        errors.append(f"{prefix}SKILL.md frontmatter 缺少 'name'")
    elif fm["name"] != dir_name:
        errors.append(f"{prefix}SKILL.md name '{fm['name']}' 与目录名 '{dir_name}' 不一致")

    if "description" not in fm:
        errors.append(f"{prefix}SKILL.md frontmatter 缺少 'description'")
    else:
        desc = fm["description"]
        # 过长的 description 会稀释技能路由的匹配信号。
        if len(desc) > 320 and not desc.startswith("|"):
            warns.append(
                f"{prefix}description 长度 {len(desc)} 字符，超出建议上限 320，"
                f"会削弱技能路由准确度")

    # 负向后顾 (?<![\w/.\-]) 确保只匹配技能内的相对引用，不会把
    # `skills/other-skill/references/x.md` 这类跨技能全路径切一半来误判。
    # 额外把「-」「.」纳入后顾禁集：避免把 `paper-templates/...` 误切成 `templates/...`
    # 而错误判定「引用不存在」（实际文件存在，属校验器误报）。paper-templates 亦显式列入关键词。
    ref_re = re.compile(r"(?<![\w/.\-])(?:references|scripts|assets|config|templates|paper-templates)/[A-Za-z0-9._\-/]+")
    for m in ref_re.finditer(text):
        rel = m.group(0).rstrip("/")
        if not os.path.exists(os.path.join(root, rel)):
            warns.append(f"{prefix}SKILL.md 引用路径不存在: {rel}")
    return True


def iter_skill_dirs(skills_root):
    """递归产出 skills/ 下所有含 SKILL.md 的真实技能目录（跳过分组/支撑目录）。

    domain/foundation/quality 三级分组下嵌套真实技能（如 skills/case-writer）。
    本函数下钻分组目录，使每个真实技能都被 check_skill_dir 覆盖。
    """
    if not os.path.isdir(skills_root):
        return
    for d in sorted(os.listdir(skills_root)):
        sub = os.path.join(skills_root, d)
        if not os.path.isdir(sub):
            continue
        if d in NON_SKILL_DIRS:
            # 分组/支撑目录：继续向下递归寻找真实技能，自身不作为技能校验
            yield from iter_skill_dirs(sub)
            continue
        if os.path.isfile(os.path.join(sub, "SKILL.md")):
            yield sub


def check_orchestration(root, errors, warns):
    """校验 plugin.json、agents/ 与 skills/ 三者的引用一致性。"""
    pj = os.path.join(root, ".codebuddy-plugin", "plugin.json")
    if not os.path.isfile(pj):
        return

    try:
        meta = json.loads(read_text(pj))
    except json.JSONDecodeError as e:
        errors.append(f"plugin.json 解析失败: {e}")
        return

    # 1) agents / skills 声明的路径必须真实存在
    #    复合型 skill 包可能把整个 skills/ 目录作为单一入口登记，识别此类「复合入口」避免误报
    declared_skills = set()
    composite_skills = set()  # 仅作复合入口声明的，不参与「未挂载」检查
    for rel in meta.get("skills", []):
        p = os.path.join(root, rel.lstrip("./"))
        if not os.path.isdir(p):
            errors.append(f"plugin.json skills 条目不存在: {rel}")
        else:
            base = os.path.basename(p.rstrip("/"))
            # 复合入口：声明路径直接是 skills/ 或 agents/ 等顶层目录
            if base in ("skills", "agents"):
                composite_skills.add(base)
            else:
                declared_skills.add(base)

    declared_agents = set()
    for rel in meta.get("agents", []):
        p = os.path.join(root, rel.lstrip("./"))
        if not os.path.isfile(p):
            errors.append(f"plugin.json agents 条目不存在: {rel}")
        else:
            declared_agents.add(os.path.splitext(os.path.basename(p))[0])

    # 2) 磁盘上多出来、却没在 plugin.json 里登记的技能 = 不会被加载的孤儿
    #    例外1：skills/ 下的支撑目录（src/templates/references 等）属于复合型 skill 包的合理嵌套
    #    例外2：当整个 skills/ 作为复合入口登记（plugin.json 声明 "skills" 目录而非逐子技能）时，
    #          其下全部真实子技能已被聚合入口覆盖，不应被误报为「未登记孤儿」
    skills_dir = os.path.join(root, "skills")
    if os.path.isdir(skills_dir):
        composite_skills_root = "skills" in composite_skills
        for d in sorted(os.listdir(skills_dir)):
            if os.path.isdir(os.path.join(skills_dir, d)) and d not in declared_skills:
                if d in NON_SKILL_DIRS:
                    continue
                if composite_skills_root:
                    continue  # 复合入口已聚合覆盖，真实子技能不算孤儿
                errors.append(f"技能 '{d}' 存在于磁盘但未在 plugin.json 登记，将不会被加载")

    # 3) 每个 agent 的 skills[] 必须能解析到已登记的技能
    agents_dir = os.path.join(root, "agents")
    mounted = set()
    if os.path.isdir(agents_dir):
        for fn in sorted(os.listdir(agents_dir)):
            if not fn.endswith(".md"):
                continue
            fm = parse_frontmatter(read_text(os.path.join(agents_dir, fn)))
            for s in parse_list_field(fm.get("skills", "")):
                mounted.add(s)
                if s not in declared_skills:
                    errors.append(f"agent '{fn}' 绑定了未登记的技能: {s}")

    # 4) 登记了却没有任何 agent 挂载的技能 = 永远不会被触发
    #    复合入口（声明路径直接是顶层 skills/agents 目录）属于合法聚合入口，跳过此类「未挂载」检查
    for s in sorted(declared_skills - mounted):
        if s in composite_skills:
            continue
        errors.append(f"技能 '{s}' 已登记但无任何 agent 挂载，运行期不可达")

    # 5) teamInfo 与 agents 列表一致性
    team = meta.get("teamInfo") or {}
    for key in ("leadAgent",):
        if team.get(key) and team[key] not in declared_agents:
            errors.append(f"teamInfo.{key} '{team[key]}' 不在 agents 列表中")
    for m in team.get("memberAgents", []):
        if m not in declared_agents:
            errors.append(f"teamInfo.memberAgents 中的 '{m}' 不在 agents 列表中")

    # 6) 身份锁：plugin.json 的 author 必须恒等于 IDENTITY（支持内联或拆分形态）
    #    - 内联形态：author 字段直接是字符串 IDENTITY
    #    - 拆分形态：author 是 {"name": ..., "email": ...}，两字段需同时匹配 IDENTITY_PARTS
    author_obj = meta.get("author") or {}
    if isinstance(author_obj, str):
        author_inline = author_obj
        author_split_ok = False
    elif isinstance(author_obj, dict):
        author_inline = ""
        author_split_ok = (
            _author_name_matches(author_obj.get("name"))
            and author_obj.get("email") == IDENTITY_PARTS[1]
        )
    else:
        author_inline = ""
        author_split_ok = False
    if author_inline != IDENTITY and not author_split_ok:
        actual = (
            f"{author_inline}" if author_inline
            else f"{author_obj.get('name', '')} <{author_obj.get('email', '')}>"
        )
        errors.append(f"身份锁失败：plugin.json author = '{actual}'，应为 '{IDENTITY}'")


def check_hygiene(root, errors, warns):
    """检查不应入包的构建/系统产物。"""
    for dp, dns, fns in os.walk(root):
        for d in list(dns):
            if d in DIRT_PATTERNS:
                errors.append(f"冗余产物入包: {os.path.relpath(os.path.join(dp, d), root)}/")
        for fn in fns:
            if fn in DIRT_PATTERNS or fn.endswith(DIRT_SUFFIX):
                errors.append(f"冗余产物入包: {os.path.relpath(os.path.join(dp, fn), root)}")


def _is_identity_mention(mention: str) -> bool:
    """仅当匹配文本属于合法 IDENTITY 自身（姓名/所属机构/邮箱）时才豁免；第三方 PII 不豁免。

    作者所属机构（_ORG_CN，即 plugin.json author.name 括号后缀）是身份签名的一部分，
    与姓名/邮箱同等豁免，避免用本校验器校验本包时把作者自身署名误报为泄露。
    """
    s = re.sub(r"\s+", " ", mention.strip())
    if s == IDENTITY_PARTS[0]:
        return True
    if s == _ORG_CN:
        return True
    if IDENTITY_PARTS[1] in s:
        return True
    return False


def _is_identity_email(email: str) -> bool:
    return email.lower() == IDENTITY_PARTS[1].lower()


def check_content(root, errors, warns):
    """逐文件扫描凭证、PII 与身份漂移。"""
    for p in iter_scan_files(root):
        # 统一为正斜杠：os.path.relpath 在 Windows 上产出反斜杠，
        # 否则 assets 豁免失效，会对内置 minified 产物误报凭证/路径类告警。
        rel = os.path.relpath(p, root).replace(os.sep, "/")
        # 随包内置的第三方产物（bsk 二进制、官方浏览器扩展等）不属于自研内容，
        # 跳过凭证/PII/身份扫描，避免对 minified 代码（如 React 里的 password 字段写法）误报。
        if ("/assets/" in rel) or rel.startswith("assets/"):
            continue
        text = read_text(p)

        if SENSITIVE_RE.search(text):
            errors.append(f"凭证泄露: {rel}")

        for m in ABS_PATH_RE.finditer(text):
            errors.append(f"硬编码开发机路径: {rel} → {m.group(0)}")
            break  # 每文件报一次即可，避免刷屏

        for m in REALNAME_RE.finditer(text):
            mention = m.group(0)
            if _is_identity_mention(mention):
                continue  # 合法署名自身写法，不算泄露
            line_no = text[:m.start()].count("\n") + 1
            errors.append(
                f"身份锁失败：{rel}:{line_no} 出现实名/机构写法 '{mention}'，"
                f"应统一为 '{IDENTITY}'")
            break

        for m in EMAIL_RE.finditer(text):
            email = m.group(0)
            if email.lower() in EMAIL_ALLOWLIST:
                continue
            if _is_identity_email(email):
                continue  # 合法署名邮箱，不算泄露
            errors.append(f"邮箱泄露: {rel} → {email}")
            break

        # 身份锁豁免已在上述 REALNAME_RE / EMAIL_RE 循环中按"匹配文本是否属 IDENTITY 自身"
        # 精确判定（见 _is_identity_mention / _is_identity_email），第三方真实 PII 不会被误豁免。


# ---------------------------------------------------------------- 主流程

def main():
    ap = argparse.ArgumentParser(description="Generic skill/agent-pack validator")
    ap.add_argument("pack_dir", nargs="?", default=".")
    ap.add_argument("--strict", action="store_true", help="将警告一并视为阻断项")
    args = ap.parse_args()

    root = os.path.abspath(args.pack_dir)
    errors, warns = [], []

    if not os.path.isdir(root):
        print(f"ERROR: pack_dir not found: {root}")
        sys.exit(1)

    is_skill = check_skill_dir(root, errors, warns)

    if not is_skill:
        # agent-pack 模式：继续校验编排与每个子技能。
        skills_dir = os.path.join(root, "skills")
        if os.path.isdir(skills_dir):
            for sub in iter_skill_dirs(skills_dir):
                rel = os.path.relpath(sub, root)
                check_skill_dir(sub, errors, warns, prefix=f"[{rel}] ")
        else:
            warns.append("pack 根目录无 SKILL.md 且无 skills/ 子目录")
        check_orchestration(root, errors, warns)

    check_hygiene(root, errors, warns)
    check_content(root, errors, warns)

    for w in warns:
        print(f"WARN: {w}")
    if errors:
        for e in errors:
            print(f"ERROR: {e}")
        print(f"\nFAIL: {len(errors)} 个错误, {len(warns)} 个警告")
        sys.exit(1)
    if args.strict and warns:
        print(f"\nFAIL(strict): 0 个错误, {len(warns)} 个警告")
        sys.exit(1)
    print(f"\nOK: {root}")
    print(f"通过：0 个错误, {len(warns)} 个警告 · 身份锁 = {IDENTITY}")
    sys.exit(0)


if __name__ == "__main__":
    main()
