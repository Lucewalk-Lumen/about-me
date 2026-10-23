#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
quality_eval.py — 五维质量评估（资产接入 WorkBuddy 体验）

从「构成完整性 / 任务完成度 / 指令遵从性 / 事实辨别性 / 规则遵从性」五个维度，
检测一个专家资产（技能 / 专家 / 专家团）接入后的真实体验。

重要（C7 止损说明）：本脚本产出的是**体验层启发式参考分**（基于文本关键词打分），
**不得单独作为放行依据**，也不要把它当作硬门禁。结构完整性/合规的**权威放行判据**是：
  - `python3 scripts/verify.py --zip <包>.zip`（退出码 0）
  - `python3 scripts/gates.py .`（退出码 0）
即：verify.py / gates.py 才是「能不能接入」的判据；本脚本仅供体验改进参考。数值门控
（displayDescription 中文字数、tags/quickPrompts 数量、categoryId 枚举）的**唯一事实源**
是 `skills/workbuddy-expert-studio-toolkit/contract.yaml`（本脚本从那里读取，contract
缺失时才回退内置默认）。

用法：
  python scripts/quality_eval.py <package_dir> [--json]
  python scripts/quality_eval.py            # 默认评估当前专家团目录

输出：逐维评分(1-10) + 证据 + 精修清单(文件:行号:建议) + 参考门控结论。
退出码（参考语义，非放行依据）：0=体验良好 / 1=需修改 / 2=需重点改进
        （放行请以 verify.py --zip 与 gates.py 的退出码为准）

方法论：基于本专家团 workbuddy-expert-studio-flow-9stage.md 阶段 1/阶段 5 的五维推演
        与一轮实测沉淀的评分锚点、严重度门控（同源自有方法论，不引用第三方包）。
零第三方依赖。
"""
import os, sys, json, re, glob, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

CATEGORY_ENUM = {
    "01-ProductDesign","02-Engineering","03-GameSpatial","04-DataAI","05-MarketingGrowth",
    "06-ContentCreative","07-SalesCommerce","08-FinanceInvestment","09-OperationsHR",
    "10-ProjectQuality","11-SecurityCompliance","12-IndustryConsultant","13-TencentZone",
    "14-WorldWise","15-Education",
}
P0_VISUAL = ["渐变", "毛玻璃", "发光", "glow", "gradient", "glassmorphism"]

# 数值门控的唯一事实源（toolkit contract.yaml）+ 内置兜底（C7）
_CONTRACT_REL = os.path.join("skills", "workbuddy-expert-studio-toolkit", "contract.yaml")


def load_contract_criteria(pkg):
    """从 toolkit 的 contract.yaml 读取数值阈值与 categoryId 枚举（唯一事实源）。

    零第三方依赖：仅解析本文件用到的 YAML 子集（顶层 category_ids 列表 + manifest 标量）。
    contract 缺失/不可读时回退内置默认（与旧硬编码值一致），不改变既有判据语义。
    C7：消除 quality_eval 内的第三份硬编码副本（verify.py 与 gates.py 已从 contract 读取）。
    """
    crit = {"cjk_min": 40, "cjk_max": 50, "tags": 3, "quick_prompts": 3,
            "category_ids": set(CATEGORY_ENUM)}
    p = os.path.join(pkg, _CONTRACT_REL)
    if not os.path.exists(p):
        return crit
    try:
        with open(p, encoding="utf-8", errors="ignore") as fh:
            lines = fh.read().splitlines()
    except Exception:
        return crit
    cats, in_cats = set(), False
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
            crit["cjk_" + m.group(1)] = int(m.group(2))
        m = re.match(r"\s*tags_count:\s*(\d+)", line)
        if m:
            crit["tags"] = int(m.group(1))
        m = re.match(r"\s*quick_prompts_count:\s*(\d+)", line)
        if m:
            crit["quick_prompts"] = int(m.group(1))
    if cats:
        crit["category_ids"] = cats
    return crit


def cjk_len(s):
    return sum(1 for c in s if "\u4e00" <= c <= "\u9fff")


def read_text(p):
    try:
        with open(p, encoding="utf-8", errors="ignore") as fh:
            return fh.read()
    except Exception:
        return ""


def collect_md_files(pkg):
    files = []
    for ext in ("*.md",):
        files += glob.glob(os.path.join(pkg, "**", ext), recursive=True)
    return files


def detect_type(pkg):
    if os.path.exists(os.path.join(pkg, ".codebuddy-plugin", "plugin.json")):
        return "plugin", os.path.join(pkg, ".codebuddy-plugin", "plugin.json")
    pj = os.path.join(pkg, "plugin.json")
    if os.path.exists(pj):
        return "plugin", pj
    sk = os.path.join(pkg, "SKILL.md")
    if os.path.exists(sk):
        return "skill", sk
    return "unknown", None


# ---------------------------------------------------------------------------
# P0 视觉红线判据（抽为纯函数，便于 dual_proof 做绿红双证）
# ---------------------------------------------------------------------------
# 合规语境关键词：命中「禁/无/移除/红线…」即视为「在讲禁止」而非「在用」
NEG_CTX = re.compile(r"禁|禁用|不得|避免|不要|移除|去除|杜绝|红线|非|无|严禁|不该")


def _line_context(text, pos, span=200):
    """取 pos 所在**整行**作为上下文（左右各至多 span 字符兜底）。

    取「按行」而非固定 ±N 字符的原因：P0 禁令常写成一条长清单
    （如「禁止 3D / 卡通 / 二次元 / 营销插画 / 装饰渐变大图」），
    固定窗口会因否定词离关键词过远而**误判为违规**。
    """
    ls = text.rfind("\n", 0, pos)
    le = text.find("\n", pos)
    ls = 0 if ls == -1 else ls + 1
    le = len(text) if le == -1 else le
    return text[max(ls, pos - span):min(le, pos + span)]


def p0_visual_violation(text):
    """P0 视觉红线：在**非禁止语境**下出现 渐变/毛玻璃/发光/glow/gradient/glassmorphism 即违规。

    返回 True = 违规（应拦）；False = 合规（仅出现在「禁/无/移除」等提醒语境）。
    """
    for v in P0_VISUAL:
        for m in re.finditer(re.escape(v), text):
            if NEG_CTX.search(_line_context(text, m.start())):
                continue
            return True
    return False


def anchor(score):
    if score <= 3:
        return "[FAIL] 阻断"
    if score <= 6:
        return "[WARN] 需修改"
    if score <= 8:
        return "[OK] 可用"
    return "[OK] 成熟"


# ------------------------- 五维评估 -------------------------
def dim_task_completion(pkg, meta, body_files_text):
    """维度 A：任务完成度"""
    ev, fixes = [], []
    score = 10
    desc = (meta.get("description") or "") if isinstance(meta, dict) else ""
    dd = ""
    if isinstance(meta, dict):
        d = meta.get("displayDescription")
        if isinstance(d, dict):
            dd = d.get("zh", "")
    if not desc and not dd:
        ev.append("【静态推断】未找到核心任务声明(description/displayDescription 均空)")
        fixes.append(f"在 plugin.json/SKILL.md 补全一句话核心任务声明")
        score = min(score, 2)
    else:
        ev.append(f"【静态推断】核心任务声明存在(desc {len(desc)}字 / dd {cjk_len(dd)}字)")
    # 工作流完整性
    flow_hits = len(re.findall(r"阶段|SOP|工作流|步骤|Phase|workflow", body_files_text))
    if flow_hits < 3:
        ev.append(f"【静态推断】工作流关键词稀少({flow_hits}处)，流程可能不完整")
        fixes.append("在 agent/SKILL 正文补齐「识别→执行→交付」完整阶段与步骤")
        score = min(score, 5)
    else:
        ev.append(f"【静态推断】工作流结构完整(命中 {flow_hits} 处阶段/步骤关键词)")
    # 输出模板
    if "```" not in body_files_text and "输出格式" not in body_files_text and "模板" not in body_files_text:
        ev.append("【静态推断】未发现固定输出模板/格式")
        fixes.append("为正文补充固定输出模板与验收标准(可复判的通过条件)")
        score = min(score, 6)
    else:
        ev.append("【静态推断】存在输出模板/格式约定")
    return max(1, score), ev, fixes


LEGACY_SCENE_WORDS = ("教学", "个人", "企业")
SCENE_TABLE_HEADER_KEYS = ("场景",)
_NORM_SCENE = re.compile(r"[*`\s]")


def _clean_scene(cell):
    """把场景单元格归一化成关键词：去加粗/反引号/括号注。'**教学**'→'教学'；'其他单位（兜底）'→'其他单位'。"""
    s = re.sub(r"（[^）]*）|\([^)]*\)", "", cell)
    s = _NORM_SCENE.sub("", s)
    return s.strip()


def declared_scenes(lead_txt):
    """从主理人正文的**场景表**推导本包自声明的场景词。

    判据：表头含「场景」的 markdown 表，取其首列（去表头/分隔行）作为场景词。
    推导失败则回退 LEGACY_SCENE_WORDS（向后兼容：老包仍按 教学/个人/企业 校验）。
    这样扫描器不再把某一套场景词汇硬编码为全局真理。
    """
    blocks, cur = [], []
    for line in lead_txt.splitlines():
        s = line.strip()
        if s.startswith("|"):
            cur.append([c.strip() for c in s.strip("|").split("|")])
        else:
            if cur:
                blocks.append(cur)
                cur = []
    if cur:
        blocks.append(cur)
    for b in blocks:
        if len(b) < 2 or "场景" not in "".join(b[0]):
            continue
        rows = [r for r in b[1:] if not all(set(c) <= set("-: ") for c in r)]
        words = []
        for r in rows:
            if not r:
                continue
            raw = r[0]
            # 兜底/回退行不是"场景"，是默认桶（如「其他单位（兜底）」），不计入声明场景
            if re.search(r"兜底|回退|默认桶|fallback", raw) or _clean_scene(raw).startswith("其他"):
                continue
            w = _clean_scene(raw)
            if w and len(w) <= 8:
                words.append(w)
        if len(words) >= 2:
            return words
    return list(LEGACY_SCENE_WORDS)


def _split_gate_keywords(cell):
    """把「附加门禁」单元格拆成关键词：按 +/＋/、/;/；/,/，分隔，去括号注。"""
    kws = []
    for tok in re.split(r"[+＋、;；,，]", cell):
        tok = re.sub(r"（[^）]*）|\([^)]*\)", "", tok).strip()
        if len(tok) >= 2:
            kws.append(tok)
    return kws


def check_scenario_routing(pkg, typ, meta):
    """场景化合规检查（维度 B 附加判据）：场景路由表从文档承诺变脚本可验证。

    校验五项：
      1) 主理人正文存在场景路由表（含 场景/交付物定位/附加门禁 列，六列结构）；
      2) 三场景（教学/个人/企业）齐备；
      3) 各行交付物定位与附加门禁非空；
      4) 每条「附加门禁」关键词在判据文献（references/ + 其他 agents/，排除承诺
         所在的主理人文件——自引用不算落点）中可检索到；
      5) quickPrompts 覆盖三场景枚举（路由不确定时的回退真正可用）。

    返回 dict(penalty, evidence, fixes)；penalty>0 时维度 B 按 10-penalty 计分。
    """
    ev, fixes = [], []
    penalty = 0
    if typ != "plugin" or not isinstance(meta, dict) or meta.get("expertType") != "team":
        ev.append("【静态推断】非 team 型插件，场景路由检查不适用")
        return {"penalty": 0, "evidence": ev, "fixes": fixes}
    lead = (meta.get("teamInfo", {}) or {}).get("leadAgent") or meta.get("agentName") or ""
    lead_path = os.path.join(pkg, "agents", f"{lead}.md")
    lead_txt = read_text(lead_path)
    if not lead_txt:
        ev.append("【静态推断】主理人文件缺失，场景路由无法核验")
        fixes.append(f"补全 agents/{lead}.md（teamInfo.leadAgent 指向的文件）")
        return {"penalty": 4, "evidence": ev, "fixes": fixes}

    # 解析主理人正文中的 markdown 表（按连续块切分）
    blocks, cur = [], []
    for line in lead_txt.splitlines():
        s = line.strip()
        if s.startswith("|"):
            cur.append([c.strip() for c in s.strip("|").split("|")])
        else:
            if cur:
                blocks.append(cur)
                cur = []
    if cur:
        blocks.append(cur)
    scenes = declared_scenes(lead_txt)

    tbl = None
    for b in blocks:
        if len(b) >= 2 and all(k in "".join(b[0]) for k in SCENE_TABLE_HEADER_KEYS):
            hdr = b[0]
            rows = [r for r in b[1:] if not all(set(c) <= set("-: ") for c in r)]
            tbl = (hdr, rows)
            break

    if tbl is None:
        ev.append("【静态推断】主理人正文未找到场景表（含「场景」列表头）")
        fixes.append("在主理人正文补场景表（首列枚举本包声明的场景，各场景行非空）")
        penalty += 4
    else:
        hdr, rows = tbl
        ev.append(f"【静态推断】场景表存在（{len(hdr)} 列 × {len(rows)} 行；本包自声明场景 {len(scenes)} 个：{'/'.join(scenes)}）")
        # 场景齐备性：以**本包自声明**的场景为准（不再硬编码某套词汇）
        first_cells = [_clean_scene(r[0]) if r else "" for r in rows]
        missing_scenes = [w for w in scenes if not any(w and w in c for c in first_cells)]
        if missing_scenes:
            ev.append(f"【静态推断】场景表缺自声明场景：{'、'.join(missing_scenes)}")
            fixes.append(f"补齐场景行：{'、'.join(missing_scenes)}")
            penalty += 2 * len(missing_scenes)
        else:
            ev.append(f"【静态推断】自声明场景齐备（{'/'.join(scenes)}）")
        # 每行须携带真实信息（拒绝空壳行）
        shell_rows = [i for i, r in enumerate(rows) if len(r) < 2 or not any(c.strip() for c in r[1:])]
        if shell_rows:
            ev.append(f"【静态推断】场景表第 {shell_rows} 行为空壳（除场景外无内容）")
            fixes.append("补全各场景行的交付物/规范信息")
            penalty += 2
        # 「附加门禁」列：**仅当本包声明该列时**校验其判据落点（对声明方保持约束力）
        idx_gate = next((i for i, c in enumerate(hdr) if "附加门禁" in c), -1)
        if idx_gate >= 0:
            ref_texts = {}
            for d in ("references", "agents"):
                for p in glob.glob(os.path.join(pkg, d, "*.md")):
                    if os.path.abspath(p) != os.path.abspath(lead_path):
                        ref_texts[p] = read_text(p)
            for p in glob.glob(os.path.join(pkg, "skills", "*", "references", "*.md")):
                if os.path.abspath(p) != os.path.abspath(lead_path):
                    ref_texts[p] = read_text(p)
            all_missing = []
            for r in rows:
                if len(r) <= idx_gate:
                    continue
                scene = _clean_scene(r[0]) if r else "?"
                for kw in _split_gate_keywords(r[idx_gate]):
                    if not any(kw in t for t in ref_texts.values()):
                        all_missing.append(f"{scene}·{kw}")
            if all_missing:
                ev.append(f"【静态推断】{len(all_missing)} 条附加门禁无判据落点：{'、'.join(all_missing)}")
                fixes.append("为缺失门禁补判据落点（references/ 场景附加门禁判据表），或在路由表收敛措辞")
                penalty += 2 * len(all_missing)
            else:
                ev.append("【静态推断】附加门禁关键词全部有判据落点（排除主理人自引用）")

    qp = meta.get("quickPrompts") or []
    qpzh = " ".join(q.get("zh", "") for q in qp if isinstance(q, dict))
    hit = [w for w in scenes if w in qpzh]
    if not hit:
        ev.append(f"【静态推断】quickPrompts 未命中任何自声明场景：{'、'.join(scenes)}（路由无信号）")
        fixes.append(f"quickPrompts 至少覆盖 1 个自声明场景（{'、'.join(scenes)}）")
        penalty += 2
    else:
        extra = "" if len(hit) == len(scenes) else f"；{len(hit)}/{len(scenes)}（快启位固定 3 个，场景多于 3 时无法全枚举，属结构限制）"
        ev.append(f"【静态推断】quickPrompts 命中自声明场景：{'、'.join(hit)}{extra}")

    return {"penalty": min(penalty, 9), "evidence": ev, "fixes": fixes}


def dim_instruction_compliance(pkg, typ, meta, body_files_text):
    """维度 B：指令遵从性（含场景化合规检查）"""
    ev, fixes = [], []
    score = 10
    crit = load_contract_criteria(pkg)   # C7：阈值取自 contract.yaml
    trig = len(re.findall(r"触发|trigger|当用户|适用场景|使用时机", body_files_text))
    if trig < 2:
        ev.append(f"【静态推断】触发/边界描述薄弱({trig}处)")
        fixes.append("补全触发词与 near-miss 边界(四要素：场景/触发/能力/边界)")
        score = min(score, 5)
    else:
        ev.append(f"【静态推断】触发与边界描述充分({trig}处)")
    # 一致性：官方硬性要求是 defaultInitPrompt.zh == quickPrompts[0].zh。
    # displayDescription 为展示文案，允许与两者措辞不同，不计入一致性比对（否则误报）。
    if isinstance(meta, dict):
        qp = meta.get("quickPrompts") or []
        dip = meta.get("defaultInitPrompt")
        qp0zh = qp[0].get("zh", "") if (qp and isinstance(qp[0], dict)) else ""
        dipzh = dip.get("zh", "") if isinstance(dip, dict) else ""
        if qp0zh and dipzh:
            if qp0zh == dipzh:
                ev.append("【静态推断】defaultInitPrompt.zh == quickPrompts[0].zh（官方一致性要求满足）")
            else:
                ev.append("【静态推断】defaultInitPrompt.zh 与 quickPrompts[0].zh 不一致")
                fixes.append("defaultInitPrompt 须与 quickPrompts[0] 完全一致（官方硬性要求）")
                score = min(score, 5)
        else:
            ev.append("【静态推断】defaultInitPrompt / quickPrompts[0] 中文缺项")
            fixes.append("补全 defaultInitPrompt.zh 与 quickPrompts[0].zh")
            score = min(score, 7)
        if len(qp) != crit["quick_prompts"]:
            ev.append(f"【静态推断】quickPrompts 数量={len(qp)}，非固定{crit['quick_prompts']}个")
            fixes.append(f"quickPrompts 固定 {crit['quick_prompts']} 个，且与 defaultInitPrompt/首条一致")
            score = min(score, 7)
    # 场景化合规：场景路由表从文档承诺变脚本可验证（见 check_scenario_routing）
    sc = check_scenario_routing(pkg, typ, meta)
    ev.extend(sc["evidence"])
    fixes.extend(sc["fixes"])
    if sc["penalty"]:
        score = min(score, max(1, 10 - sc["penalty"]))
    return max(1, score), ev, fixes


def dim_fact_discrimination(pkg, meta, body_files_text):
    """维度 C：事实辨别性"""
    ev, fixes = [], []
    score = 10
    # 量化声明无来源：数字+% / 样本量 / p值 等，且无三态标注
    has_tri = bool(re.search(r"【实测】|【待验证】|来源未经确证|待确认", body_files_text))
    quant = re.findall(r"\d+\s*%|样本\s*量|p\s*[<>=]?\s*0?\.\d+|N\s*=\s*\d+", body_files_text)
    if quant and not has_tri:
        ev.append(f"【静态推断】发现 {len(quant)} 处量化断言但无三态/来源标注，疑似未锚定事实")
        fixes.append("为量化断言补【实测】/【待验证】或来源标注，禁止编造统计/样本/p值")
        score = min(score, 4)
    elif quant and has_tri:
        ev.append(f"【静态推断】{len(quant)} 处量化断言均有三态标注，事实可锚定")
    else:
        ev.append("【静态推断】未发现未锚定量化断言")
    # 伪造来源警示：出现「据研究/研究表明」但无具体出处
    if re.search(r"研究表明|据研究|大量研究证明", body_files_text) and "http" not in body_files_text and "来源" not in body_files_text:
        ev.append("【静态推断】存在空泛「研究表明」式断言，缺具体出处")
        fixes.append("删除或替换为带出处的真实引用；无来源不写确定性结论")
        score = min(score, 6)
    return max(1, score), ev, fixes


def dim_rule_compliance(pkg, typ, meta_path, meta, body_files_text):
    """维度 D：规则遵从性"""
    ev, fixes = [], []
    score = 10
    if typ != "plugin" or not isinstance(meta, dict):
        # 技能型：仅查 frontmatter 基本项
        if typ == "skill":
            sk = read_text(os.path.join(pkg, "SKILL.md"))
            if "description" in sk and "version" in sk:
                ev.append("【静态推断】SKILL.md 含 description/version 基本项")
            else:
                ev.append("【静态推断】SKILL.md 缺 description/version")
                fixes.append("SKILL.md frontmatter 补全 description/description_zh/description_en/version/author")
                score = min(score, 5)
        return max(1, score), ev, fixes

    crit = load_contract_criteria(pkg)   # C7：阈值/枚举取自 contract.yaml（唯一事实源）
    name = meta.get("name", "")
    # 1) name==plugin
    if meta.get("plugin") != name:
        ev.append("【静态推断】plugin 字段 != name")
        fixes.append(f"plugin 字段须 == name({name})")
        score = min(score, 4)
    # 2) displayDescription CJK 字数（上下界取自 contract.yaml）
    dd = meta.get("displayDescription", {})
    ddzh = dd.get("zh", "") if isinstance(dd, dict) else ""
    n = cjk_len(ddzh)
    if not (crit["cjk_min"] <= n <= crit["cjk_max"]):
        ev.append(f"【静态推断】displayDescription.zh 中文字数={n}，应在 {crit['cjk_min']}-{crit['cjk_max']}")
        fixes.append(f"displayDescription.zh 调至 {crit['cjk_min']}-{crit['cjk_max']} 字(当前 {n})")
        score = min(score, 4)
    else:
        ev.append(f"【静态推断】displayDescription.zh 字数合规({n})")
    # 3) tags/quickPrompts 数量（取自 contract.yaml）
    if len(meta.get("tags", [])) != crit["tags"]:
        ev.append(f"【静态推断】tags 数量={len(meta.get('tags',[]))}，非{crit['tags']}")
        fixes.append(f"tags 固定 {crit['tags']} 个")
        score = min(score, 5)
    if len(meta.get("quickPrompts", [])) != crit["quick_prompts"]:
        ev.append(f"【静态推断】quickPrompts 数量={len(meta.get('quickPrompts',[]))}，非{crit['quick_prompts']}")
        fixes.append(f"quickPrompts 固定 {crit['quick_prompts']} 个")
        score = min(score, 5)
    # 4) defaultInitPrompt == quickPrompts[0]
    #    防护：quickPrompts 可能为空 []（非法但真实存在），须用 `qp or []` + 下标前判空，
    #    否则 qp0[0] 抛 IndexError（参照 dim_instruction_compliance 的写法）。
    qp0 = meta.get("quickPrompts") or []
    qp0zh = qp0[0].get("zh", "") if (qp0 and isinstance(qp0[0], dict)) else ""
    dip = meta.get("defaultInitPrompt", {})
    dipzh = dip.get("zh", "") if isinstance(dip, dict) else ""
    if qp0zh and dipzh and qp0zh != dipzh:
        ev.append("【静态推断】defaultInitPrompt.zh != quickPrompts[0].zh")
        fixes.append("defaultInitPrompt 须与 quickPrompts[0] 一致")
        score = min(score, 5)
    # 5) categoryId 枚举（取自 contract.yaml）
    if meta.get("categoryId") not in crit["category_ids"]:
        ev.append(f"【静态推断】categoryId={meta.get('categoryId')} 不在枚举（{len(crit['category_ids'])} 类）")
        fixes.append("categoryId 取 contract.yaml category_ids 枚举之一(见知识库第4节)")
        score = min(score, 5)
    # 6) 协作铁律(专家团)
    if meta.get("expertType") == "team":
        for kw in ["TeamCreate", "中转", "代写", "成员结论为准"]:
            if kw not in body_files_text:
                ev.append(f"【静态推断】主理人正文缺铁律关键词「{kw}」")
                fixes.append(f"主理人 agent 补铁律：「{kw}」相关约束")
                score = min(score, 6)
    # 7) 安全红线：仅当「赋值 + 引号值(≥6位)」才算硬编码凭据，
    #    避免 prose 中 secret/token/password 等词（如说明文字）误报。
    if re.search(r'(?:api_key|apikey|secret|password|token|access_key|private_key)\s*=\s*["\'][^"\']{6,}["\']', body_files_text, re.I):
        ev.append("【静态推断】疑似硬编码密钥/凭据")
        fixes.append("移除硬编码密钥，改为官方配置入口说明")
        score = min(score, 2)
    if re.search(r"eval\(|exec\(", body_files_text):
        ev.append("【静态推断】正文中出现 eval/exec 动态执行")
        fixes.append("移除 eval/exec 动态执行外部内容的设计")
        score = min(score, 3)
    # 8) P0 视觉：仅在「非禁止语境」下才算违规（判据见 p0_visual_violation）。
    if p0_visual_violation(body_files_text):
        ev.append("【静态推断】出现 P0 视觉红线词(渐变/毛玻璃/发光) 且处于非禁止语境")
        fixes.append("移除 Indigo→Pink 渐变+发光+毛玻璃 等 AI 模板味视觉")
        score = min(score, 7)
    return max(1, score), ev, fixes


def dim_composition_completeness(pkg, typ, meta, body_files_text):
    """维度 E：构成完整性（Agent 构成模型六要素是否落地，非空壳）"""
    ev, fixes = [], []

    def has_dir(*names):
        # 包根直接命中
        if any(os.path.isdir(os.path.join(pkg, n)) for n in names):
            return True
        # 兼容 plugin 型专家团的常见布局：references / knowledge 位于 skills/<name>/ 之下
        for n in names:
            for hit in glob.glob(os.path.join(pkg, "**", n), recursive=True):
                if os.path.isdir(hit):
                    return True
        return False

    def has_any(pat):
        return bool(glob.glob(os.path.join(pkg, "**", pat), recursive=True))

    checks = []
    # ① 身份与边界
    checks.append(("身份与边界", bool(meta) or has_any("SKILL.md"),
                   "补 plugin.json / SKILL.md 的角色与名称声明"))
    # ② 工具与能力
    checks.append(("工具与能力", has_dir("skills", "scripts"),
                   "补 skills/ 或 scripts/ 承载能力"))
    # ③ 记忆与上下文
    checks.append(("记忆与上下文", has_dir("references", "knowledge"),
                   "补 references/ 或 knowledge/ 承载知识与上下文"))
    # ④ 编排与循环
    if typ == "plugin" and isinstance(meta, dict):
        lead = (meta.get("teamInfo", {}) or {}).get("leadAgent") or meta.get("agentName")
        orch = bool(lead) and os.path.exists(os.path.join(pkg, "agents", f"{lead}.md"))
    else:
        orch = bool(re.search(r"阶段|流程|步骤|workflow|SOP", body_files_text))
    checks.append(("编排与循环", orch, "补主理人 / 流程编排定义"))
    # ⑤ 输出契约
    checks.append(("输出契约", ("输出格式" in body_files_text or "模板" in body_files_text
                             or "```" in body_files_text),
                   "补固定输出模板与交付物落点"))
    # ⑥ 门禁与演化
    checks.append(("门禁与演化", (os.path.exists(os.path.join(pkg, "scripts", "verify.py"))
                             or has_any("CHANGELOG.md")),
                   "补门禁脚本或 CHANGELOG"))

    missing = [name for name, ok, _ in checks if not ok]
    for name, ok, fix in checks:
        if not ok:
            fixes.append(f"{name}：{fix}")
    if missing:
        ev.append(f"【静态推断】构成六要素缺 {len(missing)} 项：{'、'.join(missing)}")
        penalty = {1: 3, 2: 5, 3: 7}.get(len(missing), 9)
        score = max(1, 10 - penalty)
    else:
        ev.append("【静态推断】构成六要素齐备（身份 / 工具 / 记忆 / 编排 / 输出 / 门禁）")
        score = 10
    return max(1, score), ev, fixes


def build_parser():
    ap = argparse.ArgumentParser(
        prog="quality_eval.py",
        description="五维质量评估：构成完整性 / 任务完成度 / 指令遵从性 / 事实辨别性 / 规则遵从性。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="退出码：0=PASS(可接入) 1=WARN(需修改) 2=FAIL(阻断)")
    ap.add_argument("package_dir", nargs="?", default=None,
                    help="待评估的包目录（默认当前专家团目录）")
    ap.add_argument("--json", action="store_true", help="以 JSON 输出报告")
    return ap


def evaluate(args):
    pkg = args.package_dir or ROOT
    as_json = args.json
    typ, meta_path = detect_type(pkg)
    meta = {}
    if meta_path and typ == "plugin":
        try:
            with open(meta_path, encoding="utf-8") as fh:
                meta = json.load(fh)
        except Exception as e:
            print(f"[quality_eval] plugin.json 解析失败: {e}", file=sys.stderr)
    elif typ == "skill":
        # 解析 SKILL.md frontmatter(name/description/version)
        sk = read_text(meta_path)
        fm = re.match(r"^---\s*\n(.*?)\n---", sk, re.S)
        if fm:
            for line in fm.group(1).splitlines():
                m = re.match(r'\s*(\w[\w-]*)\s*:\s*(.+)?', line)
                if m:
                    meta[m.group(1)] = (m.group(2) or "").strip()

    md_files = collect_md_files(pkg)
    body = "\n".join(read_text(f) for f in md_files)

    dims = {}
    dims["A_任务完成度"] = dim_task_completion(pkg, meta, body)
    dims["B_指令遵从性"] = dim_instruction_compliance(pkg, typ, meta, body)
    dims["C_事实辨别性"] = dim_fact_discrimination(pkg, meta, body)
    dims["D_规则遵从性"] = dim_rule_compliance(pkg, typ, meta_path, meta, body)
    dims["E_构成完整性"] = dim_composition_completeness(pkg, typ, meta, body)

    scores = {k: v[0] for k, v in dims.items()}
    avg = round(sum(scores.values()) / len(scores), 1)
    fails = [k for k, s in scores.items() if s <= 3]
    warns = [k for k, s in scores.items() if 4 <= s <= 7]
    all_pass = all(s >= 8 for s in scores.values()) and avg >= 8.0

    if fails or avg < 6.0:
        gate = "[FAIL] 需重点改进（体验参考，非放行依据）"
        code = 2
    elif all_pass:
        gate = "[OK] 体验良好（体验参考，非放行依据）"
        code = 0
    else:
        gate = "[WARN] 需修改（体验参考，非放行依据）"
        code = 1

    report = {
        "package": os.path.abspath(pkg),
        "type": typ,
        "average": avg,
        "gate": gate,
        "disclaimer": ("体验层启发式参考分（文本关键词打分），不得单独作为放行依据；"
                       "结构/合规放行以 verify.py --zip 与 gates.py 的退出码为准。"),
        "authoritative_gates": ["python3 scripts/verify.py --zip <包>.zip",
                                "python3 scripts/gates.py ."],
        "dimensions": {k: {"score": v[0], "anchor": anchor(v[0]), "evidence": v[1], "fixes": v[2]} for k, v in dims.items()},
    }

    if as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"=== 五维质量评估：{os.path.basename(pkg)} (type={typ}) ===")
        print(f"平均分：{avg}   参考门控：{gate}\n")
        for k, v in dims.items():
            print(f"[{v[0]:>2}/10 {anchor(v[0])}] {k}")
            for e in v[1]:
                print(f"      · {e}")
            for fx in v[2]:
                print(f"      · 精修：{fx}")
            print()
        if fails:
            print("需重点改进维度：", ", ".join(fails))
        if warns:
            print("待修改维度：", ", ".join(warns))
        print("\n[提示] 本脚本为体验层启发式参考分，非放行依据；放行以 `verify.py --zip` 与 `gates.py` 退出码为准。")
        print("退出码（参考）：", code, "（0=体验良好 / 1=需修改 / 2=需重点改进）")
    return code


def main(argv=None):
    """CLI 入口：真 argparse（-h/--help 可用）；内部异常收敛为结构化错误，不裸抛 traceback。"""
    args = build_parser().parse_args(argv)
    try:
        code = evaluate(args)
    except Exception as e:  # noqa: BLE001
        # R3：任何内部异常都以结构化 JSON 输出（error_type=internal_error），而非 traceback 裸奔。
        print(json.dumps({
            "ok": False,
            "error_type": "internal_error",
            "error": f"{type(e).__name__}: {e}",
            "package": os.path.abspath(getattr(args, "package_dir", None) or ROOT),
        }, ensure_ascii=False, indent=2))
        sys.exit(2)
    sys.exit(code)


if __name__ == "__main__":
    main()
