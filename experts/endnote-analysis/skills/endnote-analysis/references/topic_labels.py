# -*- coding: utf-8 -*-
"""
topic_labels.py —— 主题命名与「非主题」判定

## 为什么需要它

算法只能给出 Top 词，给不出「这个主题叫什么」。而报告若只显示
`employees / positive / negative / social`，对教师毫无用处——他需要的是
「员工感知与职业适应」这样的学术标签。

## 命名来源分两级（优先级从高到低）

1. **本文件内置的 OB/HRM 通用命名表**（TOPIC_LABELS）
   键为该簇的 top_terms 特征指纹，值为中文主题名。
   指纹取「Top 词里最具主题指向性的词的组合」，因此不同库只要主题结构
   相似即可命中。

2. **用户自定义** `references/topic_labels.local.csv`
   格式：`fingerprint<TAB>主题名`（fingerprint 为逗号分隔的 top 词前缀）
   存在则优先于内置表。**建议用户把自己满意的命名写进这个文件**，
   工具下次运行即采用——这样命名能力随使用累积。

3. **LLM 命名**（可选，由 Agent 侧完成）
   把 Top 20 中心词 + 5 篇代表文献摘要交给 Agent 生成标签，
   结果写回 `topic_labels.local.csv`。20 个簇仅需 20 次调用，成本可忽略。
   **任何命名失败都必须降级，绝不能让 LLM 故障阻塞主流程。**

## 非主题簇的判定

不是所有簇都是「研究主题」。实测发现三类非主题簇，它们应被显式标注
而非混在主题里：

- **残差簇**：关键词缺失率高（实测 77.3%），落进来的都是没信号的文献
- **测量/元研究簇**：以方法词为主（问卷、量表、信效度）
- **人口统计簇**：以 adult/female/male 等 MeSH 人口统计头为主

判据用「主题纯度」：随机抽样 N 篇标题，命中该簇 top_terms 的比例。
纯度极低（实测 5%）即判为非主题。
"""

from __future__ import annotations

import csv
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

# ── 非主题簇判定阈值（来自实测）─────────────────────────
NON_TOPIC_MAX_PURITY = 0.30   # 主题纯度低于此值 → 判为非主题簇
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
    p = Path(path) if path else Path(__file__).parent / "topic_labels.local.csv"
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

    匹配顺序很重要（实测踩过的坑）：
    先「全指纹精确匹配」→ 再「逐级缩短匹配」→ 最后「关键词回退」。
    绝不能一上来就缩短匹配 —— 会把 `employees,employee,...` 这种
    长指纹缩到 3 词后，误命中另一个簇的短键，导致**主题名张冠李戴**
    （实测曾把「人口统计测量」簇标成「工作满意度与工作投入」）。
    """
    user_labels = user_labels if user_labels is not None else load_user_labels()
    tables = (user_labels, TOPIC_LABELS)
    names = ("user", "builtin")

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

    # 3) 关键词回退
    low = " ".join(str(t).lower() for t in top_terms)
    for kw, name in KEYWORD_FALLBACK:
        if kw in low:
            return name, "keyword"
    return "", "none"


def is_non_topic(purity: float, threshold: float = NON_TOPIC_MAX_PURITY) -> bool:
    """主题纯度过低 → 该簇不是研究主题，应显式标注而非混作主题。"""
    return purity < threshold
