# -*- coding: utf-8 -*-
"""
topic_labels.py —— 主题命名与「非主题」判定

## 为什么需要它

算法只能给出 Top 词，给不出「这个主题叫什么」。而报告若只显示
`employees / positive / negative / social`，对教师毫无用处——他需要的是
「员工感知与职业适应」这样的学术标签。

## 命名来源分四级（优先级从高到低）

1. **用户自定义** `references/topic_labels.local.csv`
   格式：`fingerprint<TAB>主题名`（fingerprint 为逗号分隔的 top 词前缀）
   存在则优先于一切内置逻辑。**建议用户把自己满意的命名写进这个文件**，
   工具下次运行即采用——这样命名能力随使用累积。

2. **本文件内置的 OB/HRM 通用命名表**（TOPIC_LABELS）
   键为该簇的 top_terms 特征指纹，值为中文主题名。
   指纹取「Top 词里最具主题指向性的词的组合」，因此不同库只要主题结构
   相似即可命中。

3. **概念概括命名器**（_concept_name）
   识别簇内 1-2 个核心变量概念，用学术模板「X 与 Y 研究」主动概括，
   而不是把关键词拼起来当主题名。详见下方「学科适用性」说明。

4. **LLM 命名**（可选，由 Agent 侧完成）
   把 Top 20 中心词 + 5 篇代表文献摘要交给 Agent 生成标签，
   结果写回 `topic_labels.local.csv`。20 个簇仅需 20 次调用，成本可忽略。
   **任何命名失败都必须降级，绝不能让 LLM 故障阻塞主流程。**

## 学科适用性（重要设计约束）

概念词典（CONCEPT_ZH）是**面向 OB/HRM 学科**建立的——它覆盖组织行为、
人力资源领域的核心构念（job crafting→工作重塑、LMX→领导-成员交换…）。
其他学科（教育、医学、计算机、经济学…）的核心概念完全不同，
直接套用 OB/HRM 词典会大量未命中。

因此命名器按「学科无关的机制 + 学科可替换的词典」分层设计：

* **机制层（学科无关）**：概念提取、语言纯度过滤、冗余合并、学术命名模板、
  非主题簇识别——这些规则对任何学科都成立。
* **词典层（学科相关）**：
  - 内置 OB/HRM 概念包（CONCEPT_ZH）；
  - 用户扩展 `references/concept_dict.local.csv`，格式
    `英文术语<TAB>中文名`（# 开头为注释）。**其他学科的用户把自己领域的
    概念映射写进这个文件即可生效，无需修改任何代码。**
* **优雅兜底（任何学科都不会产出垃圾名）**：
  - 词典未覆盖的中文概念 → 保留原文（中文术语本身可读）；
  - 词典未覆盖的英文概念 → 若整簇有中文概念则丢弃该英文词
    （绝不混入中文名造成「人工智能、technology与X研究」拼盘）；
  - 整簇完全没有可用中文概念时 → 整簇退回英文命名模板
    `Research on X and Y`——**单个主题名永远只含一种语言**。
  这样即使是一个全新学科、词典零覆盖，产出的主题名也是干净的
  同学术语言短语，而不是中英混杂的关键词碎片。

## 非主题簇的判定

不是所有簇都是「研究主题」。实测发现三类非主题簇，它们应被显式标注
而非混在主题里：

- **残差簇**：关键词缺失率高（实测 77.3%），落进来的都是没信号的文献
- **测量/元研究簇**：以方法词为主（问卷、量表、信效度）
- **人口统计簇**：以 adult/female/male 等 MeSH 人口统计头为主

非主题簇的识别经由内置指纹表显式标注（见 TOPIC_LABELS 中标「非主题」的条目）。
"""

from __future__ import annotations

import re
from pathlib import Path

# ── 内置 OB/HRM 主题命名表 ────────────────────────────────
# 键：top_terms 的指纹（按顺序取前若干词的规范化组合）
# 值：主题名。该表基于对 5558 篇 OB/HRM 中英文混合库的实际聚类结果提炼。
TOPIC_LABELS: dict[str, str] = {
    'employees,employee,positive,negative,social,through': "其他·未归类文献",  # 非主题·853篇
    'management,review,human,resource,artificial,intelligence': "理论构建与领域元研究",  # 元研究·543篇
    '组织,企业,创新,人工智能,技术,管理': "组织创新与数字化转型",                    # 主题·514篇
    '工作,员工,自我,感知,压力,资源': "员工感知与职业适应",                       # 主题·473篇
    '领导,团队,创造力,员工,创新,下属': "领导行为与员工创造力",                     # 主题·396篇
    'team,performance,teams,creativity,innovation,diversity': "团队过程与团队绩效",  # 主题·380篇
    'leadership,leader,transformational,ethical,identity,leaders': "领导风格与领导效能",  # 主题·370篇
    'workaholism,work,addiction,engagement,health,burnout': "工作成瘾与过度投入",  # 主题·355篇
    'humans,relations,surveys,questionnaires,century,psychological': "测量方法与元研究",  # 非主题·353篇
    'job,satisfaction,engagement,work,demands,performance': "工作满意度与工作投入",  # 主题·346篇
    'organizational,commitment,citizenship,turnover,support,identification': "组织公民行为与组织承诺",  # 主题·308篇
    'conflict,work-family,family,balance,life,resources': "工作-家庭冲突与平衡",  # 主题·259篇
    'adult,female,male,humans,aged,middle': "人口统计测量与个体差异",  # 非主题·235篇
    'behavior,abusive,citizenship,exchange,supervision,workplace': "负面领导与职场不文明",  # 主题·173篇
}

# 命中的通用主题名（当指纹未命中时按关键词回退匹配）
KEYWORD_FALLBACK: list[tuple[str, str]] = [
    ("workaholism", "工作成瘾与过度投入"),
    ("work-family", "工作-家庭冲突与平衡"),
    ("citizenship", "组织公民行为与组织承诺"),
    ("creativity", "团队创造力与创新"),
    ("transformational", "领导风格与效能"),
    ("artificial intelligence", "AI 与人力资源管理"),
    ("人工智能", "AI 与人力资源管理"),
    ("satisfaction", "工作满意度与工作投入"),
    ("burnout", "工作倦怠与情绪耗竭"),
    ("ostracism", "职场不文明"),
    ("team", "团队过程与绩效"),
    ("leadership", "领导行为与效能"),
    ("voice", "员工建言"),
    ("organizational citizenship", "组织公民行为"),
]

NON_TOPIC_KEY = "其他·未归类文献"


def fingerprint(top_terms: list[str], n: int = 6) -> str:
    """由 Top 词生成指纹。

    必须同时支持中英文 —— 实测中文簇占 14 簇中的 3 个，
    若只收英文词会让中文簇指纹为空、命名全部失配。
    保留同簇内的语言纯度：若前若干词已同属一种语言，就不混入另一种。
    """
    picked: list[str] = []
    for t in top_terms[:n * 3]:
        tl = str(t).strip().lower()
        if not tl or not re.match(r"^[a-z][a-z\- ]*[0-9]*$", tl) and not re.search(
                r"[\u4e00-\u9fff]", tl):
            continue
        # 判语言：已 picked 里若已有中文，就不再收英文（反之亦然）
        is_cjk = bool(re.search(r"[\u4e00-\u9fff]", tl))
        if picked:
            prev_cjk = bool(re.search(r"[\u4e00-\u9fff]", picked[0]))
            if is_cjk != prev_cjk:
                break
        picked.append(tl)
        if len(picked) >= n:
            break
    return ",".join(picked)


def load_user_labels(path: str | Path | None = None) -> dict[str, str]:
    """加载用户自定义命名（优先于内置表）。"""
    p = (Path(path) if path else
         Path(__file__).resolve().parent.parent / "references" / "topic_labels.local.csv")
    if not p.exists():
        return {}
    out: dict[str, str] = {}
    try:
        with open(p, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "," not in line:
                    continue
                # 格式 fingerprint<TAB>名称；也兼容 fingerprint,名称
                if "\t" in line:
                    fp, name = line.split("\t", 1)
                else:
                    fp, name = line.split(",", 1)
                out[fp.strip()] = name.strip()
    except Exception:
        return {}
    return out


def label_topic(top_terms: list[str], user_labels: dict[str, str] | None = None) -> tuple[str, str]:
    """返回 (主题名, 来源)。来源 ∈ {user, builtin, keyword, none}

    匹配顺序是正确性约束：
    先「全指纹精确匹配」→ 再「逐级缩短匹配」→ 最后「关键词回退」。
    绝不能一上来就缩短匹配 —— 把 `employees,employee,...` 这种
    长指纹缩到 3 词后，误命中另一个簇的短键，导致**主题名张冠李戴**
    （如把「人口统计测量」簇标成「工作满意度与工作投入」）。
    """
    user_labels = user_labels if user_labels is not None else load_user_labels()
    tables = (user_labels, TOPIC_LABELS)
    names = ("user", "builtin")

    # 0) 非主题簇自动识别（优先级最高）：
    #    实测：簇13 全是 MeSH 人口词（humans/female/male/adult），
    #    命名器却把它标成「工作成瘾与young研究」——把人口统计误当研究主题。
    #    该判定学科无关（MeSH 是跨学科标引），在任何精确匹配之前执行。
    nt = detect_non_topic(top_terms)
    if nt:
        return nt, "non_topic"

    # 1) 全指纹精确匹配（最可靠）
    for n in range(0, 7):
        fp = fingerprint(top_terms, n=n) if n else fingerprint(top_terms)
        if not fp:
            continue
        for tbl, src in zip(tables, names):
            if fp in tbl:
                return tbl[fp], src

    # 2) 缩短匹配：取前 3 词做宽松匹配（避免更短的 2 词前缀误命中）
    parts = [str(t).strip().lower() for t in top_terms[:8] if str(t).strip()]
    for k in (4, 3):
        if len(parts) < k:
            continue
        sub = ",".join(parts[:k])
        for tbl, src in zip(tables, names):
            if sub in tbl:
                return tbl[sub], src

    # 3) 概念概括（v1.0.0 重构，优先于关键词回退）：
    #    需求来源：KEYWORD_FALLBACK 是「单词→固定名」的映射，多个簇都含
    #    "satisfaction"/"engagement" 时被映射到同一个名，dedupe 只能拼「·后缀」，
    #    结果如「工作满意度与工作投入·工作重塑」——不是主题，是关键词罗列。
    #    概念概括是主动的：识别簇内 1-3 个核心变量概念（多词术语优先、
    #    剔除方法词/MeSH 人口词/GENERIC_WORDS），用学术模板「X 与 Y 研究」生成，
    #    且整簇统一一种语言（中文优先）。不同簇提的概念天然不同，无需 dedupe 拼盘。
    picked = _concept_name(top_terms)
    if picked:
        return picked, "derived"

    # 4) 关键词回退（概念概括失败才用：通常是词池被剔空）
    low = " ".join(str(t).lower() for t in top_terms)
    for kw, name in KEYWORD_FALLBACK:
        if kw in low:
            return name, "keyword"

    # 5) 实在提不出概念（极端情况：全是方法词/MeSH），退回单词兜底
    picked = _topic_headword(top_terms)
    if picked:
        return picked, "derived"
    return "", "none"


# ── 概念概括命名器（回应实测需求）──────────────
# 实测问题：兜底命名把簇12（工作满意度+工作投入+工作重塑 拼盘）标成
# 「工作满意度与工作投入·工作重塑」——这不是主题，是关键词罗列。
# 真正的主题名应该是**主动概括**：识别簇内 1-3 个核心变量概念，
# 用学术命名模板（「X 与 Y 研究」）生成，且**整簇统一一种语言**（中文优先）。
#
# 实现分三层：
#   1) CONCEPT_ZH 词典：OB/HRM 核心变量概念 → 中文学术名（多词术语优先）。
#      覆盖本领域绝大多数高频构念（job crafting→工作重塑、LMX→领导-成员交换…）。
#   2) extract_concepts()：从词池中按权重序提取 1-3 个互不冗余的核心概念。
#      冗余判定：中文按字符串包含（"工作投入" ⊃ "投入"），英文按词集合子集
#      （"job performance" ⊃ "performance"）——避免「X 与 X 研究」。
#   3) 模板命名：1 概念「X 研究」、2 概念「X 与 Y 研究」、3 概念「X、Y 与 Z 研究」。

# OB/HRM 核心变量概念 → 中文学术名（键统一小写；多词术语优先于单词）
# 设计原则：
#   · 键覆盖**原始关键词可能出现的写法**（含连字符/缩写/单复数/中英）；
#   · 值是**学界通行的中文构念名**，不是字面翻译（job crafting → 工作重塑）；
#   · 只收"变量/构念"，不收方法词/人口词（那些在 METHOD_WORDS / _MESH_RE 剔除）。
CONCEPT_ZH: dict[str, str] = {
    # ── 工作设计 / 主动行为 ──
    "job crafting": "工作重塑", "工作重塑": "工作重塑", "crafting": "工作重塑",
    "job design": "工作设计", "工作设计": "工作设计",
    "job autonomy": "工作自主性", "autonomy": "自主性", "工作自主性": "自主性",
    "proactive personality": "主动性人格", "主动性人格": "主动性人格",
    "proactivity": "主动性行为", "proactive behavior": "主动性行为",
    "person-job fit": "人-岗匹配", "person-organization fit": "人-组织匹配",
    "person-environment fit": "人-环境匹配",
    "employee engagement": "工作投入", "work engagement": "工作投入",
    "工作投入": "工作投入", "engagement": "工作投入",
    # ── 态度 / 满意度 / 承诺 ──
    "job satisfaction": "工作满意度", "job-satisfaction": "工作满意度",
    "工作满意度": "工作满意度", "satisfaction": "工作满意度",
    "organizational commitment": "组织承诺", "组织承诺": "组织承诺",
    "affective commitment": "情感承诺", "organizational identification": "组织认同",
    "组织认同": "组织认同", "identification": "认同感",
    "psychological contract": "心理契约", "心理契约": "心理契约",
    "psychological safety": "心理安全感", "心理安全感": "心理安全感",
    "psychological capital": "心理资本", "心理资本": "心理资本",
    "well-being": "幸福感", "wellbeing": "幸福感", "幸福感": "幸福感",
    "job insecurity": "工作不安全感", "工作不安全感": "工作不安全感",
    # ── 领导 ──
    "transformational leadership": "变革型领导", "变革型领导": "变革型领导",
    "ethical leadership": "伦理型领导", "伦理型领导": "伦理型领导",
    "servant leadership": "服务型领导", "公仆型领导": "服务型领导",
    "authentic leadership": "真实型领导", "真实型领导": "真实型领导",
    "empowering leadership": "授权型领导", "授权型领导": "授权型领导",
    "inclusive leadership": "包容型领导", "包容型领导": "包容型领导",
    "shared leadership": "共享领导", "charismatic leadership": "魅力型领导",
    "abusive supervision": "辱虐管理", "辱虐管理": "辱虐管理",
    "leader-member exchange": "领导-成员交换", "lmx": "领导-成员交换",
    "领导-成员交换": "领导-成员交换",
    "destructive leadership": "破坏性领导", "toxic leadership": "毒性领导",
    # ── 行为 ──
    "organizational citizenship behavior": "组织公民行为",
    "organizational citizenship": "组织公民行为", "组织公民行为": "组织公民行为",
    "citizenship behavior": "组织公民行为", "ocb": "组织公民行为",
    "counterproductive work behavior": "反生产行为", "反生产行为": "反生产行为",
    "deviant behavior": "偏差行为", "workplace deviance": "职场偏差行为",
    "employee voice": "员工建言", "voice behavior": "建言行为",
    "员工建言": "员工建言", "建言行为": "建言行为",
    "silence": "员工沉默", "employee silence": "员工沉默", "员工沉默": "员工沉默",
    "impression management": "印象管理", "印象管理": "印象管理",
    "taking charge": "担责行为", "bootleg innovation": "越轨创新",
    "workplace ostracism": "职场排斥", "职场排斥": "职场排斥",
    "workplace incivility": "职场不文明行为", "职场不文明": "职场不文明行为",
    "knowledge hiding": "知识隐藏", "知识隐藏": "知识隐藏",
    "knowledge sharing": "知识共享", "知识共享": "知识共享",
    "knowledge management": "知识管理", "知识管理": "知识管理",
    # ── 创造力 / 创新 / 绩效 ──
    "employee creativity": "员工创造力", "员工创造力": "员工创造力",
    "team creativity": "团队创造力", "团队创造力": "团队创造力",
    "creative self-efficacy": "创造力自我效能",
    "innovative behavior": "创新行为", "innovation behavior": "创新行为",
    "创新行为": "创新行为", "员工创新行为": "员工创新行为",
    "job performance": "工作绩效", "task performance": "任务绩效",
    "工作绩效": "工作绩效", "绩效": "绩效",
    "career success": "职业成功", "职业成功": "职业成功",
    "career adaptability": "职业适应力", "职业适应力": "职业适应力",
    "career development": "职业发展", "职业发展": "职业发展",
    # ── 情绪 / 健康 ──
    "emotional labor": "情绪劳动", "情绪劳动": "情绪劳动",
    "emotion regulation": "情绪调节", "情绪调节": "情绪调节",
    "positive affect": "积极情绪", "negative affect": "消极情绪",
    "emotional exhaustion": "情绪耗竭", "情绪耗竭": "情绪耗竭",
    "burnout": "工作倦怠", "job burnout": "工作倦怠",
    "工作倦怠": "工作倦怠", "倦怠": "倦怠",
    "workaholism": "工作成瘾", "work addiction": "工作成瘾",
    "工作成瘾": "工作成瘾",
    "occupational stress": "职业压力", "job stress": "工作压力",
    "工作压力": "工作压力", "职业压力": "职业压力",
    "mental health": "心理健康", "心理健康": "心理健康",
    "depression": "抑郁", "anxiety": "焦虑",
    "work-family conflict": "工作-家庭冲突", "work family conflict": "工作-家庭冲突",
    "工作-家庭冲突": "工作-家庭冲突", "工作家庭冲突": "工作-家庭冲突",
    "work-family balance": "工作-家庭平衡", "work-life balance": "工作-生活平衡",
    "工作-家庭平衡": "工作-家庭平衡", "工作-生活平衡": "工作-生活平衡",
    "work-family enrichment": "工作-家庭促进", "work-family spillover": "工作-家庭溢出",
    # ── 认知 / 人格 / 动机 ──
    "self-efficacy": "自我效能感", "自我效能感": "自我效能感",
    "core self-evaluation": "核心自我评价", "核心自我评价": "核心自我评价",
    "self-esteem": "自尊", "self-regulation": "自我调节",
    "big five": "大五人格", "five-factor model": "大五人格",
    "dark triad": "暗黑三人格", "narcissism": "自恋", "machiavellianism": "马基雅维利主义",
    "intrinsic motivation": "内在动机", "extrinsic motivation": "外在动机",
    "内在动机": "内在动机", "自我决定理论": "自我决定理论",
    "self-determination theory": "自我决定理论", "sdt": "自我决定理论",
    "goal orientation": "目标定向", "learning goal orientation": "学习目标定向",
    "growth mindset": "成长型思维",
    # ── 社会认知 / 关系 ──
    "social identity": "社会认同", "社会认同": "社会认同",
    "social support": "社会支持", "社会支持": "社会支持",
    "social capital": "社会资本", "社会资本": "社会资本",
    "social exchange": "社会交换", "social exchange theory": "社会交换理论",
    "social learning": "社会学习", "social cognitive theory": "社会认知理论",
    "social networks": "社会网络", "social network": "社会网络",
    "社会网络": "社会网络", "network analysis": "网络分析",
    "trust": "信任", "organizational trust": "组织信任", "信任": "信任",
    "perceived organizational support": "组织支持感",
    "组织支持感": "组织支持感", "organizational support": "组织支持感",
    "organizational justice": "组织公平", "组织公平": "组织公平",
    "distributive justice": "分配公平", "procedural justice": "程序公平",
    "interactional justice": "互动公平",
    "leader-member": "领导-成员交换",  # LMX 的连写碎片也归并
    # ── 团队 / 组织 ──
    "team performance": "团队绩效", "团队绩效": "团队绩效",
    "team diversity": "团队多样性", "团队多样性": "团队多样性",
    "team climate": "团队氛围", "team learning": "团队学习",
    "virtual team": "虚拟团队", "虚拟团队": "虚拟团队",
    "organizational culture": "组织文化", "组织文化": "组织文化",
    "organizational climate": "组织氛围", "组织氛围": "组织氛围",
    "organizational change": "组织变革", "组织变革": "组织变革",
    "organizational learning": "组织学习", "组织学习": "组织学习",
    "high performance work system": "高绩效工作系统",
    "human resource management": "人力资源管理", "hrm": "人力资源管理",
    "人力资源管理": "人力资源管理", "人力资源开发": "人力资源开发",
    "hr practices": "人力资源实践", "hrm practices": "人力资源实践",
    "e-hrm": "电子人力资源", "wfc": "工作-家庭冲突",
    "talent management": "人才管理", "人才管理": "人才管理",
    "strategic human resource management": "战略人力资源管理",
    # ── 数字化 / AI ──
    "artificial intelligence": "人工智能", "人工智能": "人工智能",
    "ai": "人工智能", "machine learning": "机器学习",
    "digital transformation": "数字化转型", "数字化转型": "数字化转型",
    "digital leadership": "数字领导力",
    "algorithmic management": "算法管理",
    "platform economy": "平台经济", "gig economy": "零工经济",
    "gig work": "零工工作", "零工": "零工经济",
    # ── 理论 / 机制 ──
    "job demands-resources": "工作要求-资源模型", "jd-r": "工作要求-资源模型",
    "conservation of resources": "资源保存理论", "cor": "资源保存理论",
    "conservation of resources theory": "资源保存理论",
    "job demands resources theory": "工作要求-资源模型",
    "资源保存理论": "资源保存理论",
    "social cognitive": "社会认知理论", "social information processing": "社会信息加工",
    "affective events": "情感事件理论", "affective events theory": "情感事件理论",
    "signaling theory": "信号理论", "contingency theory": "权变理论",
    # ── 离职 / 流动 ──
    "turnover intention": "离职倾向", "turnover": "员工离职",
    "离职倾向": "离职倾向", "员工离职": "员工离职", "离职": "离职",
    "retention": "员工保留", "employee retention": "员工保留",
    "job embeddedness": "工作嵌入", "工作嵌入": "工作嵌入",
    "job mobility": "工作流动",
    # ── 其他高频构念 ──
    "mindfulness": "正念", "正念": "正念",
    "resilience": "心理韧性", "心理韧性": "心理韧性",
    "grit": "坚毅", "坚毅": "坚毅",
    "emotional intelligence": "情绪智力", "情绪智力": "情绪智力", "情商": "情绪智力",
    "calling": "职业使命", "work calling": "职业使命", "职业使命": "职业使命", "使命感": "职业使命",
    "meaning of work": "工作意义", "meaningful work": "工作意义",
    "工作意义": "工作意义", "意义感": "意义感",
    "thriving": "旺盛状态", "thriving at work": "工作旺盛感",
    "flow": "心流", "心流": "心流",
    "aging workforce": "老龄化劳动力", "older workers": "年长员工",
    "人口老龄化": "人口老龄化", "老龄化": "人口老龄化",
    "积极老龄化": "积极老龄化",
    "new generation": "新生代员工", "新生代": "新生代员工",
    "millennials": "千禧一代",
    "remote work": "远程办公", "telework": "远程办公", "远程办公": "远程办公",
    "work from home": "居家办公", "居家办公": "居家办公",
    "job insecurity": "工作不安全感",
    "employability": "就业能力", "就业能力": "就业能力",
    "career plateau": "职业高原", "职业高原": "职业高原",
    "workaholic": "工作成瘾",
    "presenteeism": "出勤主义", "absenteeism": "缺勤",
    "incivility": "不文明行为", "ostracism": "排斥",
    "exploitative leadership": "剥削型领导",
}

# 词根 → 构念合并表：簇内同时出现 "employee creativity" 和 "creativity" 时，
# 只保留更具体的前者。键是被吞并的泛词，值是不吞并时的具体概念后缀。
# 本表在 extract_concepts() 里通过「字符串包含/词集合子集」判定，无需显式列出。


# ── 概念族（v1.0.0，主题凝聚命名）─────────────────────────────
# 实测：「创新行为、工作绩效与人工智能研究」读起来仍是关键词列举，
# 不是主题。根因：同族构念被并列罗列（变革型领导+伦理型领导+共享领导
# 其实是同一个「领导风格」家族的 3 个成员）。
# 概念族表：族名 → 族内成员（中文名，与 CONCEPT_ZH 值域一致）。
# 主题命名时若同族成员 ≥2 同时入选，合并为族名——主题名从「A、B与C研究」
# 凝聚成「领导风格研究」「职业成功与工作态度研究」这类领域名。
# 族名规范：2-6 字、不含「与」（避免模板拼接出现「与与」）。
CONCEPT_FAMILY: dict[str, list[str]] = {
    "领导风格": ["变革型领导", "伦理型领导", "服务型领导", "真实型领导",
                 "包容型领导", "授权型领导", "共享领导", "魅力型领导",
                 "破坏性领导", "毒性领导", "剥削型领导"],
    "工作态度": ["工作投入", "工作满意度", "组织承诺", "情感承诺",
                 "工作不安全感"],
    "职业健康": ["工作成瘾", "工作倦怠", "倦怠", "情绪耗竭", "工作压力",
                 "职业压力", "心理健康", "抑郁", "焦虑"],
    "工作设计": ["工作重塑", "工作设计", "工作自主性", "主动性人格",
                 "主动性行为", "人-岗匹配", "人-组织匹配", "人-环境匹配"],
    "创造力": ["员工创造力", "团队创造力", "创造力自我效能", "创新行为",
               "员工创新行为", "创新绩效"],
    "社会交换": ["领导-成员交换", "组织支持感", "心理契约", "组织公平",
                 "信任"],
    "社会认同": ["社会认同", "组织认同", "认同感"],
    "工作-家庭": ["工作-家庭冲突", "工作-家庭平衡", "工作-生活平衡",
                  "工作-家庭促进", "工作-家庭溢出"],
    "职业发展": ["职业成功", "职业适应力", "职业发展", "就业能力",
                 "职业高原", "职业使命"],
}

# 反向索引：概念 → 族名（一个概念只归一个族，先到先得——表序即优先级）
_CONCEPT_FAMILY_IDX: dict[str, str] | None = None


def _family_index() -> dict[str, str]:
    global _CONCEPT_FAMILY_IDX
    if _CONCEPT_FAMILY_IDX is None:
        idx: dict[str, str] = {}
        for fam, members in CONCEPT_FAMILY.items():
            for m in members:
                idx.setdefault(m, fam)
        _CONCEPT_FAMILY_IDX = idx
    return _CONCEPT_FAMILY_IDX


def _family_merge(cs: list[str]) -> list[str]:
    """概念族合并：同族成员 ≥2 同时入选 → 折叠为族名（保序，去其余成员）。"""
    fam_of = _family_index()
    # 统计每族在 cs 中出现的成员数
    counts: dict[str, int] = {}
    for c in cs:
        f = fam_of.get(c)
        if f:
            counts[f] = counts.get(f, 0) + 1
    hit_fam = None
    for fam, members in CONCEPT_FAMILY.items():   # 表序优先
        if counts.get(fam, 0) >= 2:
            hit_fam = fam
            break
    if not hit_fam:
        return cs
    out: list[str] = []
    replaced = False
    for c in cs:
        if fam_of.get(c) == hit_fam:
            if not replaced:
                out.append(hit_fam)
                replaced = True
            # 其余同族成员丢弃
        else:
            out.append(c)
    return out


# 方法词 / 非变量词：出现即跳过，绝不进主题名。
# 实测：簇 4（人力资源开发库）被命名为「元分析」，把方法误当主题。
METHOD_WORDS = {
    "元分析", "meta-analysis", "meta analysis", "metaanalysis", "systematic review",
    "literature review", "综述", "文献综述", "bibliometric", "文献计量",
    "citespace", "vosviewer", "co-citation", "共被引", "扎根理论",
    "grounded theory", "case study", "案例研究", "问卷", "questionnaire",
    "scale", "量表", "信度", "效度", "reliability", "validity",
    "moderating role", "mediating role", "mediation", "moderation",
    "中介", "调节", "中介效应", "调节效应", "中介作用", "调节作用",
    "结构方程", "structural equation", "sem", "回归", "regression",
    "因子分析", "factor analysis", "信效度", "psychometric",
    "theoretical contribution", "constitutes", "implications",
    "research agenda", "future research", "future", "directions",
    "theoretical", "empirical", "framework", "model", "models",
    "mechanism", "path", "路径", "机制", "模型", "框架", "理论",
    "impact", "effect", "effects", "influence", "role", "relationship",
    "antecedents", "consequences", "antecedent", "consequence",
    "前因", "后果", "影响", "作用", "关系", "视角", "基于",
    "study", "studies", "research", "analysis", "approach",
    "time", "two", "through", "abstract", "how", "why",
    # 摘要/标题里的非变量碎片（v1.0.0 实测：主题 7 出现 "definition"）
    "definition", "definitions", "introduction", "background", "overview",
    "summary", "conclusion", "conclusions", "purpose", "aim", "aims",
    "objective", "objectives",
    # 第四轮实测：量表验证/维度拆解类方法词（kw_top 首现年表残留）
    "validation", "validated", "validate", "dimensions", "dimension",
    "psychometrics", "psychometric", "measurement", "measure", "measures",
    # MeSH 倒装标引（名词, 修饰）：是数据库树号不是自然关键词
    "models, psychological", "factor analysis, statistical",
    "surveys and questionnaires", "psychology, applied", "psychology, social",
    "employment, psychology",
}

# MeSH 人口/数据库符号：出现即剔除（不应进主题名）。
# 学科无关：PubMed MeSH 是跨学科通用的主题标引体系。
# 注意：人口词必须**整词匹配**——"human resource management" 虽以 "human" 开头，
# 但它是 OB/HRM 的核心构念（人力资源管理），绝不能当 MeSH 人口头剔除。
_MESH_TERMS = {
    "humans", "human", "adult", "adults", "adolescent", "adolescents",
    "child", "children", "female", "females", "male", "males", "aged",
    "middle aged", "young adult", "young adults", "older adult", "older adults",
    "history", "history, 20th century", "history, 21st century",
    "surveys and questionnaires", "survey", "surveys", "questionnaire",
    "questionnaires", "reproducibility of results", "cross-sectional studies",
    "longitudinal studies", "prospective studies", "retrospective studies",
    "follow-up studies", "risk factors",
    # MeSH 地理标引：是国家/地区标注不是研究变量
    "united states", "china", "japan", "europe", "asia", "africa",
    "australia", "canada", "germany", "uk", "england", "korea", "india",
    "taiwan", "hong kong", "spain", "italy", "france", "netherlands",
    "brazil", "turkey", "iran", "scandinavia",
}


# MeSH 判定用归一集合：词典键（标准连字符写法）+ 连字符→空格变体。
# canonical 归一后英文连字符统一为空格，判定集预展开两种形式，
# 判定侧只需一次整词匹配——避免「逐位枚举」在热路径上的开销与遗漏。
_MESH_ALL = _MESH_TERMS | {w.replace("-", " ") for w in _MESH_TERMS}


def _is_mesh(t: str) -> bool:
    """整词或 MeSH 符号（* /）判定。"""
    low = _norm_term(t)
    if low in _MESH_ALL:
        return True
    if t.lstrip().startswith("*"):
        return True
    # "employment/psychology"、"employment/*psychology" 等 MeSH 树号写法
    if "/" in t:
        return True
    return False


_MESH_RE = re.compile(r"^(?:\*|\b(?:humans?|adults?|adolescent|child|female|male|"
                      r"aged|middle\s+aged|young\s+adult|history|surveys?\s+and\s+questionnaires?|"
                      r"questionnaires?|reproducibility|cross-sectional|longitudinal|"
                      r"prospective|retrospective|follow-up|risk\s+factors?|"
                      r"employment/psychology|employment/\*psychology|"
                      r"\w+/psychology|\w+/\*psychology)\b)", re.I)


# ── 用户自定义学科概念词典 ────────────────────────────────────
# 其他学科（教育/医学/计算机…）的用户把自己领域的「英文术语 → 中文名」映射
# 写进 references/concept_dict.local.csv，无需修改任何代码即可让命名器
# 覆盖该学科。加载后与内置 OB/HRM 词典合并，用户条目**覆盖**同键的内置条目。
def load_user_concepts(path: str | Path | None = None) -> dict[str, str]:
    """加载用户自定义学科概念词典（与内置 CONCEPT_ZH 合并，用户覆盖同键）。"""
    p = (Path(path) if path else
         Path(__file__).resolve().parent.parent / "references" / "concept_dict.local.csv")
    if not p.exists():
        return {}
    out: dict[str, str] = {}
    try:
        with open(p, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "\t" in line:
                    en, zh = line.split("\t", 1)
                elif "," in line:
                    en, zh = line.split(",", 1)
                else:
                    continue
                en, zh = en.strip().lower(), zh.strip()
                if en and zh:
                    out[en] = zh
    except Exception:
        return {}
    return out


# 合并词典（模块加载时一次性构建；用户词典覆盖内置）
_CONCEPT_ALL: dict[str, str] | None = None


def _concept_dict() -> dict[str, str]:
    global _CONCEPT_ALL
    if _CONCEPT_ALL is None:
        d = dict(CONCEPT_ZH)
        d.update(load_user_concepts())
        _CONCEPT_ALL = d
    return _CONCEPT_ALL


# ── 非主题簇自动识别（学科无关）────────────────────────────────
# 实测：簇13 全是 MeSH 人口词（humans/female/male/adult/middle aged），
# 命名器却把它标成「工作成瘾与young研究」——把人口统计误当研究主题。
# 判定规则：前 12 个高权重词里，MeSH 人口词 或 方法词 占比 ≥ 阈值 → 非主题。
# 该规则对任何学科成立（MeSH 是跨学科通用标引，方法词在多学科都高频）。

def _non_topic_share(top_terms: list[str], k: int = 12) -> tuple[float, float]:
    """返回 (MeSH 人口词占比, 方法词占比)，取前 k 个词统计。"""
    mesh_n = method_n = tot = 0
    for t in top_terms[:k]:
        t = str(t).strip()
        if not t:
            continue
        tot += 1
        low = _norm_term(t)
        if _is_mesh(t):
            mesh_n += 1
        elif low in METHOD_WORDS:
            method_n += 1
    if not tot:
        return 0.0, 0.0
    return mesh_n / tot, method_n / tot


def detect_non_topic(top_terms: list[str]) -> str | None:
    """若非主题簇，返回对应的固定名；否则返回 None。

    阈值经 out_v4 真实 14 簇校准：
      簇13（人口簇）mesh_share=12/12=1.00 且含 female/male/adolescent → 人口
      簇8（方法簇） mesh_share=6/12=0.50 但人口学词少、量表词多 → 测量方法
      其余主题簇   mesh_share ≤ 0.17     → 不触发
    """
    mesh_share, method_share = _non_topic_share(top_terms)
    if mesh_share >= 0.50:
        # 进一步区分：强人口学词（性别/年龄段）出现 ≥2 个才标人口；
        # 否则是测量方法簇（survey/questionnaire/scale 为主，adult 只是顺带的
        # 研究对象标注）。
        low = [_norm_term(t) for t in top_terms[:12]]
        strong_demo = sum(1 for w in low if w in (
            "female", "male", "adolescent", "child", "children",
            "aged", "middle aged", "young adult", "older adult"))
        if strong_demo >= 2:
            return "人口统计测量与个体差异"
        return "测量方法与元研究"
    if method_share >= 0.50:
        return "测量方法与元研究"
    return None


def _norm_term(t: str) -> str:
    """规范化：去 MeSH 星号、去多余空白、小写（中文不受影响）。"""
    t = str(t).strip().lstrip("*").strip()
    return re.sub(r"\s+", " ", t).lower()


def _is_concept(term: str) -> bool:
    """判定 term 是否是一个可命名的「变量/构念」。"""
    if not term or len(term) < 2:
        return False
    low = _norm_term(term)
    if not low or low.isdigit():
        return False
    if low in METHOD_WORDS or low in GENERIC_WORDS:
        return False
    if _is_mesh(term):
        return False
    return True


# ── 全链路统一的关键词口径（v1.0.0 最终版）────────────────────
# 全链路统一口径：所有模块的关键词列表（主题代表关键词 kw_top、
# 关键词共现网络节点、首现年表、作者核心词、主题详情 chips）必须是
# **同一个口径**——"作者标注的、有学术含义的研究变量"。
# 各模块必须共用同一套 _is_variable_kw；否则会出现「主题卡片干净、
# 首现年表仍有 performance」这类不一致（判定标准：
# 「各个模块关键词切割都有问题，改了一个没有统一」）。
#
# 口径（全量，不再保留泛词）：
#   剔 MeSH 人口/数据库符号（humans/adult/female/middle aged/*leadership）
#   剔 方法词（model/mediating role/meta-analysis/元分析…）
#   剔 GENERIC 泛词（performance/work/behavior/satisfaction/leadership/
#     motivation/management/personality/resources/emotions/identity… 及中文碎片）
#   剔 摘要碎片虚词（definition/background/purpose/through/two…）
# 保留：多词学术术语（job satisfaction / leader-member exchange / 工作重塑）
#       与词典命中的构念（经 canonical_kw 归一后查 GENERIC 以概念级判定）。
def is_variable_term(k: str) -> bool:
    """统一判定：k 是否是值得展示的「研究变量」关键词（全模块唯一口径）。

    这是**唯一**的关键词过滤函数——cluster_topics / build_keyword_network /
    cross_matrix / build_report 的关键词列表全部调用它，禁止各自再写宽窄
    不一的私有版本。
    """
    if not k or len(str(k).strip()) < 2:
        return False
    low = _norm_term(k)
    if not low or low.isdigit():
        return False
    if low in METHOD_WORDS or low in GENERIC_WORDS:
        return False
    # 连字符/下划线变体同判（job-performance 等价 job performance）
    low2 = re.sub(r"[-_]", " ", low)
    if low2 != low and (low2 in METHOD_WORDS or low2 in GENERIC_WORDS):
        return False
    if _is_mesh(str(k)):
        return False
    return True


def canonical_kw(k: str) -> str:
    """统一归一：去 MeSH 符号、压缩空白、小写、连字符变体 → 空格形式。

    用于把「social-exchange theory」和「social exchange theory」折叠成
    同一个 key。
    注意：只做**形式归一**，不做翻译；中英概念翻译走 _concept_zh。

    v1.0.0 修：连字符归一**只对含拉丁字母的词**做——
    中文连接号有语义（「工作-家庭冲突」是标准学术写法），转空格会变成
    「工作 家庭冲突」碎片；纯中文词原样保留。
    """
    low = _norm_term(k)
    if re.search(r"[a-z]", low):
        return re.sub(r"\s+", " ", re.sub(r"[-_]+", " ", low)).strip()
    return low


def _concept_zh(term: str) -> str:
    """把概念转成中文学术名。

    优先级：
      1) 用户词典 / 内置词典 精确命中（小写规范后）；
      2) 连字符/下划线变体归一为空格后再查（job-performance → job performance）；
      3) 中文原样返回；
      4) 未收录英文：返回 None（由调用方决定丢弃或整簇退回英文模板，
         绝不混入中文名造成「人工智能、technology与X研究」拼盘）。
    """
    low = _norm_term(term)
    d = _concept_dict()
    if low in d:
        return d[low]
    # 连字符/下划线变体（双向、逐位枚举）：
    #   正向 job-performance → job performance（PDF 断词写法）
    #   反向 leader member exchange → leader-member exchange（术语固有连字符，
    #   词典以标准连字符形式收录）。逐位枚举每个空格的「空格/连字符」组合，
    #   而不是全替换——「leader member exchange」的键是
    #   「leader-member exchange」（仅一个连字符），全替换会得到
    #   「leader-member-exchange」而漏配。
    words = low.split(" ")
    if len(words) >= 2:
        from itertools import product
        for sepc in product((" ", "-"), repeat=len(words) - 1):
            cand = words[0]
            for sep, w in zip(sepc, words[1:]):
                cand += sep + w
            if cand != low and cand in d:
                return d[cand]
    if re.search(r"[\u4e00-\u9fff]", term):
        return term.strip()
    return None  # 未收录英文：不做机翻，避免错译


def _concept_contains(a: str, b: str) -> bool:
    """概念 a 是否「覆盖」概念 b（b 是 a 的一部分/同义泛化）。"""
    if a == b:
        return True
    # 中文字符串包含：a="工作投入" b="投入"
    if re.search(r"[\u4e00-\u9fff]", a) and re.search(r"[\u4e00-\u9fff]", b):
        return b in a or a in b
    # 英文词集合子集：a="job performance" b="performance"
    aw = set(_norm_term(a).split())
    bw = set(_norm_term(b).split())
    if not aw or not bw:
        return False
    return bw.issubset(aw) or aw.issubset(bw)


def extract_concepts(top_terms: list[str], max_n: int = 3) -> list[str]:
    """从词池提取 1-3 个互不冗余的核心概念（中文名）。

    步骤：
      1) 过滤：剔除非概念词（方法词/MeSH/GENERIC）；
      2) 冗余合并：后出现的概念若被已有概念覆盖则跳过
         （"工作投入" 和 "engagement" 映射同名后只留一个）；
      3) 概念转中文名：词典命中则转；中文原文保留；
         **未收录英文直接丢弃**（不混入中文名）。
    返回：中文概念名列表（0-3 个）。全部为 None/空时返回 []。
    """
    if not top_terms:
        return []
    cands: list[str] = []
    for t in top_terms[:24]:  # 只扫前 24 个高权重词，避免尾部噪声
        t = str(t).strip()
        if _is_concept(t):
            cands.append(t)
    if not cands:
        return []

    picked: list[str] = []
    picked_raw: list[str] = []  # 保留原文用于覆盖判定
    for t in cands:
        if any(_concept_contains(existing, t) for existing in picked_raw):
            continue
        zh = _concept_zh(t)
        if zh is None:
            # 未收录英文：不混入中文名；但记进 picked_raw 以避免
            # 后续同义英文词重复占位
            picked_raw.append(t)
            continue
        if zh in picked:
            continue
        picked.append(zh)
        picked_raw.append(t)
        if len(picked) >= max_n:
            break
    return picked


def _concept_name(top_terms: list[str]) -> str:
    """用概念概括法生成主题名。

    返回格式（统一中文，最多 2 个概念）：
      1 概念 → 「X 研究」
      2 概念 → 「X 与 Y 研究」
    概念为 0 时返回空串（交给上层兜底）。

    v1.0.0 修：
      · 先提 5 个候选概念，再做**概念族合并**——同族构念 ≥2 同时入选时
        折叠为族名（变革型领导+伦理型领导 → 「领导风格」），最后取前 2。
      · 3 概念的「X、Y与Z研究」废除：读起来就是列举。
    产出示例：
      「创新行为、工作绩效与人工智能研究」→「创新行为与人工智能研究」
      「伦理型领导、变革型领导与共享领导研究」→「领导风格研究」
    """
    cs = extract_concepts(top_terms, max_n=5)
    if not cs:
        return ""
    cs = _family_merge(cs)
    cs = cs[:2]
    if not cs:
        return ""
    if len(cs) == 1:
        return f"{cs[0]}研究"
    return f"{cs[0]}与{cs[1]}研究"


def _topic_headword(top_terms):
    """选一个词作为主题名。

    主题名应该是**一个完整的概念**，而不是两个词拼在一起。
    取词规则（按优先级）：
      1) 长度 >=3 的词优先——中文里 3 字以上通常才是完整概念
         （"数字化转型"是概念，"数字"只是词根）；
      2) 同长度时取更靠前（TF-IDF 权重更高）的；
      3) 全部都很短时取最长的那个，至少信息量最大。
    """
    words = []
    for t in (top_terms or []):
        t = str(t).strip()
        if len(t) < 2 or t.isdigit():
            continue
        words.append(t)
    if not words:
        return ""
    # 优先：长度>=3、非通用套话
    concepts = [w for w in words if len(w) >= 3 and w not in GENERIC_WORDS]
    if not concepts:
        concepts = [w for w in words if w not in GENERIC_WORDS]
    pool = concepts or words
    # 保持原顺序（top_terms 已按权重降序），取第一个
    return pool[0]


# 通用学术套话不能当主题名——它们几乎出现在每篇文献里，
# 拿"影响因素""挑战性"当标题等于什么都没说。
# 分两类：
#   学术套话——每篇都出现，等于什么都没说
#   研究手段/工具——是"用什么方法做"，不是"研究什么"，
#     拿它们当主题名等于把方法误当领域（如"调查表""中介效应"）
GENERIC_WORDS = {
    # 学术套话
    "影响因素", "挑战性", "研究方法", "研究结果", "研究结论", "对策建议",
    "理论基础", "研究背景", "研究意义", "文献综述", "研究现状", "存在问题",
    "结论", "建议", "方法", "结果", "分析", "框架", "模型", "机制", "影响",
    "作用", "意义", "价值", "路径", "策略", "对策", "现状", "趋势",
    # 研究手段与统计术语
    "调查表", "问卷", "量表", "访谈", "案例", "样本", "数据", "实证",
    "回归", "中介效应", "调节效应", " moderation", "控制变量",
    "信度", "效度", "结构方程", "面板数据", "倾向得分",
    # 单词泛指（脱离上下文没有信息量，见需求来源：performance/creativity）
    "performance", "creativity", "innovation", "behavior", "engagement",
    "satisfaction", "commitment", "burnout", "leadership", "stress",
    "绩效", "创造力", "创新", "行为", "投入", "满意度", "承诺", "倦怠",
    # 高频低信息量词（v1.0.0 实测：dedupe 把它们当区分词，主题名惨不忍睹
    #   「AI 与人力资源管理·员工」「工作满意度与工作投入·crafting」）。
    #   中英文都收：泛角色词 / 泛领域词 / MeSH 人口头 / 单动词词根。
    "员工", "领导", "组织", "工作", "团队", "视角", "企业", "中介", "感知",
    "认知", "效应", "个体", "下属", "社会", "调节", "过程", "如何",
    "management", "work", "human", "resource", "humans", "adult", "adults",
    "team", "teams", "motivation", "crafting", "social", "psychological",
    "positive", "negative", "employee", "employees", "leader", "leaders",
    "female", "male", "aged", "middle", "century", "relations", "surveys",
    "questionnaires", "through", "review", "meta", "scale", "study",
    # 再一轮实测：dedupe 仍捞到 knowledge/impact/personality/gender 这类
    # 单体泛词 —— 它们高频横跨所有 OB 主题，没有区分度。
    "knowledge", "impact", "personality", "gender", "attitude", "attitudes",
    "perception", "perceptions", "context", "factor", "factors", "outcome",
    "outcomes", "antecedent", "antecedents", "consequence", "consequences",
    "relationship", "relationships", "effect", "effects", "role", "model",
    "models", "approach", "perspective", "framework", "mechanism",
    # 第三轮实测：首现年表/kw_top 里的单体泛词——
    # resources/emotions/identity/self 等高频横跨所有主题，无区分度。
    # 多词术语（job resources / social identity / self-efficacy）不受影响。
    "resources", "resource", "emotions", "emotion", "identity", "identities",
    "self", "organizations", "organisation", "organisations", "workplace",
    "workplaces", "health", "wellbeing", "well-being", "time", "experience",
    "experiences", "behavior", "behaviors", "behaviour", "behaviours",
    "performance", "performances", "stress", "strains", "strain",
    "motivation", "motivations", "management", "satisfaction", "dissatisfaction",
    "leadership", "engagement", "burnout", "exhaustion", "commitment",
    "turnover", "creativity", "innovation", "performance",
    "wellbeing", "affect", "mood", "moods", "trait", "traits",
    # 第五轮实测：关键词共现网络里的单体碎片词
    "firm", "firms", "bias", "biases", "conflict", "conflicts",
    "conservation", "labor", "labour", "retail", "coping", "activation",
    "construction", "power", "employment", "individuality", "cognition",
    "morals", "science", "future", "dimensions", "success", "career",
    "employees", "employee",
    # 第六轮实测：概念归一后仍残留的单体碎片
    "job", "jobs", "life", "culture", "cultures", "predictors", "predictor",
    "multilevel", "communication", "responses", "response", "experiences",
    "员工", "领导", "组织", "工作", "团队", "视角", "企业", "中介", "感知",
    "认知", "效应", "个体", "下属", "社会", "调节", "过程", "如何",
    "绩效", "创造力", "创新", "行为", "投入", "满意度", "承诺", "倦怠",
    "资源", "情绪", "认同", "自我", "压力", "动机", "健康", "性别",
    "开发", "经济", "战略", "人才", "我国", "农村", "研究",
}


# 非主题簇的固定名集合：dedupe 对它们跳过——「测量方法·emotions」
# 这种后缀没有意义，非主题簇本来就是兜底归类，允许同名。
_NON_TOPIC_NAMES = {
    "人口统计测量与个体差异", "测量方法与元研究", "其他·未归类文献",
}


def _split_concept_name(name: str) -> list[str]:
    """「X、Y与Z研究」→ [X, Y, Z]；非概念概括名返回 []。"""
    if not name or not name.endswith("研究"):
        return []
    core = name[: -len("研究")]
    parts = re.split(r"[、与]", core)
    return [p for p in parts if p]


def _join_concept_name(cs: list[str]) -> str:
    """[X, Y, Z] → 「X、Y与Z研究」（与 _concept_name 同模板）。"""
    if not cs:
        return ""
    if len(cs) == 1:
        return f"{cs[0]}研究"
    if len(cs) == 2:
        return f"{cs[0]}与{cs[1]}研究"
    return f"{cs[0]}、{cs[1]}与{cs[2]}研究"


def disambiguate_concept_names(names, top_terms_list, max_n: int = 3):
    """概念概括名的跨簇消歧（v1.0.0）。

    实测：主题 12「工作重塑、工作投入与工作满意度研究」与主题 13
    「工作成瘾、工作满意度与工作投入研究」——概念集合重叠 2 个，
    读起来是同一个主题，主题归类失去意义。

    规则（确定性）：
      1) 非概念概括名（无「研究」后缀 / 非主题固定名）原样返回；
      2) 按顺序扫描：当前名的概念集合与**任一已见名**重叠 ≥2 个概念
         → 触发消歧；
      3) 消歧：从本簇词池重新提概念（extract_concepts 取更深位），
         用「不出现在任何已见名中」的独有概念替换重叠概念；
      4) 换不出独有概念 → 原样保留（dedupe_labels 还有同名兜底）。
    """
    out = list(names or [])
    seen: list[set] = []           # 已见名的概念集合
    for i, nm in enumerate(out):
        if nm in _NON_TOPIC_NAMES or not nm:
            seen.append(set())
            continue
        cs = _split_concept_name(nm)
        if not cs:
            seen.append(set())
            continue
        cs_set = set(cs)
        hit = None
        for prev in seen:
            if prev and len(cs_set & prev) >= 2:
                hit = prev
                break
        if hit is None:
            seen.append(cs_set)
            continue
        # 消歧：用独有概念替换重叠概念
        banned: set = set()
        for prev in seen:
            banned |= prev
        cands = extract_concepts(list(top_terms_list[i] or []), max_n=max_n + 3)
        new_cs = list(cs)
        for c in cands:
            if c in banned or c in new_cs:
                continue
            for j, old in enumerate(new_cs):
                if old in hit:
                    new_cs[j] = c
                    break
            else:
                continue
            if len(set(new_cs) & hit) < 2:
                break
        if set(new_cs) != cs_set and len(set(new_cs) & hit) < 2:
            out[i] = _join_concept_name(new_cs)
            seen.append(set(new_cs))
        else:
            seen.append(cs_set)
    return out


def dedupe_labels(names, top_terms_list):
    """主题名全局去重：同名簇用各自的**区分性关键词**拉开。

    实测问题：多个簇名称完全一样，但包含的关键词
    不一样 —— 兜底命名 `_topic_headword` 对多个簇取到了同一个最特征词。
    规则（确定性，同输入同输出）：
      1) 非主题簇（测量/人口/未归类）直接原样返回——允许同名；
      2) 名字唯一 → 原样返回；
      3) 同名簇逐个找「本簇有、其他同名簇没有」的最靠前非套话词，
         拼成「原名·区分词」；
      4) 实在没有区分词时追加罗马数字「原名 II / III」——**绝不输出同名主题**。
    """
    from collections import Counter
    # 非主题簇不参与去重（允许同名，加后缀无意义）
    names = [n if n in _NON_TOPIC_NAMES else n for n in names]
    cnt = Counter(n for n in names if n and n not in _NON_TOPIC_NAMES)
    out = list(names)
    roman = {0: " II", 1: " III", 2: " IV", 3: " V"}
    for name, k in cnt.items():
        if k < 2:
            continue
        dup_idx = [i for i, n in enumerate(names) if n == name]
        taken = set()
        for rank, i in enumerate(dup_idx):
            terms = [str(t).strip() for t in (top_terms_list[i] or [])
                     if str(t).strip()]
            others: set = set()
            for j in dup_idx:
                if j == i:
                    continue
                others |= {str(t).strip().lower()
                           for t in (top_terms_list[j] or [])}
            dist = None
            # 先过一遍：候选词必须是「完整概念」——中文≥3字 或 英文不含空格
            # 且非套话、非他簇词。含空格的英文短语（social desirability）
            # 多半是泛搭配，不拿来当区分词（会读出「·social」这种碎片）。
            def _ok(t: str) -> bool:
                if len(t) < 2 or t.isdigit():
                    return False
                if t.lower() in others or t in GENERIC_WORDS:
                    return False
                if t.lower() in GENERIC_WORDS or t.lower() == name.lower():
                    return False
                if t in taken:
                    return False
                if " " in t:          # 英文多词泛短语，不当主题名片
                    return False
                # MeSH 主题词常带 *（加权标记）和 /（树号），如
                # *leadership、*employment/psychology —— 是数据库符号，
                # 不是自然语言名片，当区分词会读出「·*leadership」。
                t2 = t.lstrip("*")
                if t2 != t or "/" in t2:
                    return False
                return True
            for t in terms:
                if _ok(t):
                    dist = t
                    break
            if dist:
                taken.add(dist)
                out[i] = f"{name}·{dist}"
            else:
                out[i] = f"{name}{roman.get(rank, f' {rank + 1}')}"
    return out
