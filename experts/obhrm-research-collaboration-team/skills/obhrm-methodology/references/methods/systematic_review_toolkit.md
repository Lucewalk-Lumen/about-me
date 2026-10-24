# 系统综述工具包


**目录**

- [Purpose](#Purpose)
- [1. Cochrane 手册 v6.4 — 核心原则](#1-Cochrane-手册-v64--核心原则)
  - [核心方法学阶段](#核心方法学阶段)
  - [基本原则](#基本原则)
- [2. PRISMA 2020 — 27 项检查清单](#2-PRISMA-2020--27-项检查清单)
  - [标题与摘要](#标题与摘要)
  - [引言](#引言)
  - [方法](#方法)
  - [结果](#结果)
  - [讨论](#讨论)
  - [PRISMA 2020 Flow Diagram](#PRISMA-2020-Flow-Diagram)
- [3. RoB 2 工具概要](#3-RoB-2-工具概要)
  - [评估域](#评估域)
  - [判断等级](#判断等级)
  - [总体判断算法](#总体判断算法)
- [4. ROBINS-I 概要](#4-ROBINS-I-概要)
  - [评估域（7域覆盖3个时间点）](#评估域7域覆盖3个时间点)
  - [判断等级](#判断等级)
- [5. I² 异质性解读指南](#5-I²-异质性解读指南)
- [6. GRADE 证据确定性框架](#6-GRADE-证据确定性框架)
  - [起始等级](#起始等级)
  - [降低确定性的因素（降级）](#降低确定性的因素降级)
  - [提升确定性的因素（升级——仅限观察性研究）](#提升确定性的因素升级仅限观察性研究)
  - [确定性等级](#确定性等级)
- [7. 方案预注册指南](#7-方案预注册指南)
  - [何时注册](#何时注册)
  - [注册平台](#注册平台)
  - [方案内容（PRISMA-P 2015）](#方案内容PRISMA-P-2015)
- [8. 软件与工具](#8-软件与工具)
  - [元分析统计软件](#元分析统计软件)
  - [筛选与管理工具](#筛选与管理工具)
- [快速决策指南](#快速决策指南)

## Purpose

系统综述与元分析综合参考指南。涵盖 Cochrane 方法学、PRISMA 2020 报告规范、偏倚风险评估工具、异质性解读、GRADE 证据确定性框架和方案预注册。

---

## 1. Cochrane 手册 v6.4 — 核心原则

Cochrane 系统综述干预手册（v6.4, 2023）是系统综述方法学的金标准参考。

### 核心方法学阶段

| 阶段 | 对应章节 | 关键要求 |
|------|---------|---------|
| 规划 | Ch 1-3 | 方案预注册、明确目标、PICOS |
| 检索 | Ch 4 | 全面检索（≥2个数据库）、文档化策略 |
| 筛选 | Ch 4 | 独立双人筛选、预设标准 |
| 数据提取 | Ch 5 | 标准化表格、试提取、双人提取 |
| 偏倚风险评估 | Ch 8 (RoB 2), Ch 25 (ROBINS-I) | 基于域的评估、信号问题 |
| 综合 | Ch 10-12 | 适当的统计方法、异质性评估 |
| GRADE | Ch 14 | 每个结果的证据确定性 |
| 报告 | Ch 15 | 遵循 PRISMA 2020 |

### 基本原则

1. **先验方案**：在开展综述前预注册方案（PROSPERO、OSF）
2. **全面检索**：检索多个数据库；不可依赖单一来源
3. **双人独立流程**：筛选、提取和偏倚风险评估至少由两名审稿人独立完成
4. **预先指定方法**：在看结果前定义分析计划
5. **透明报告**：记录一切；其他团队应能复现综述

---

## 2. PRISMA 2020 — 27 项检查清单

**中文名称**：系统综述与荟萃分析优先报告条目（PRISMA 2020）

> 27 项条目的官方英文原文、逐条指导语与配套流程图，以 PRISMA 官方网站发布的版本为准（https://www.prisma-statement.org/ ，清单与流程图均可直接下载）。实际写作时请对照官方清单逐项勾选核对，下表仅提供中文条目名速查。

### 条目速查（中文）

| 板块 | 条目序号 | 条目名称与要点（中文速查） |
|------|---------|--------------------------|
| 标题与摘要 | 1–2 | ①标题：明确标识为系统综述/荟萃分析；②摘要：结构式摘要（背景、目的、数据来源、纳入标准、对象与干预、评价与综合方法、结果、局限、结论、注册号） |
| 引言 | 3–4 | ③研究依据（结合已有知识说明缘由）；④研究目的（对应 PICOS 明确表述） |
| 方法 | 5–15 | ⑤纳入排除标准；⑥信息来源（数据库、登记库、网站、参考文献列表及检索日期）；⑦检索策略（至少完整呈现一个数据库的全式，含过滤与限定）；⑧筛选过程（评审人数、共识流程）；⑨数据收集过程（是否独立双人提取）；⑩数据条目（全部结局变量与提取变量）；⑪研究内偏倚风险评估（工具及结果用途）；⑫效应量指标（RR、MD、SMD 等）；⑬综合方法（13a–13f：纳入判定、数据预处理、结果表格与可视化、综合方法与理由、异质性原因探索、敏感性分析）；⑭报告偏倚评估（如发表偏倚）；⑮证据确定性评估（如 GRADE） |
| 结果 | 16–22 | ⑯研究筛选（建议配 PRISMA 流程图；16b 报告符合纳入但被排除的研究及原因）；⑰研究特征；⑱各研究偏倚风险；⑲各研究结果（汇总数据、效应估计与置信区间）；⑳综合结果（20a–20d：纳入研究特征与偏倚、统计综合结果与异质性、异质性探索、敏感性分析）；㉑报告偏倚；㉒各结局的证据确定性 |
| 讨论 | 23–27 | ㉓结果解读（结合其他证据、证据与流程局限、实践意义）；㉔注册与方案（注册库名称、注册号、方案链接）；㉕资助来源与资助方作用；㉖利益冲突声明；㉗数据、代码与其他材料的可获取性 |

### PRISMA 2020 流程图

官方流程图模板（含可填空版本）见 https://www.prisma-statement.org/ 。中文语境下按以下五个阶段逐项记录数量（n）：

1. **识别**：数据库检索获得的记录数（n = ）；其他来源获得的记录数（n = ）
2. **预筛除**：查重后移除的记录数；自动化工具判定不合格移除的记录数；其他原因移除的记录数
3. **筛选**：初筛的记录数与排除数；寻求获取全文的报告数与未获取数
4. **合格性评估**：评估全文的报告数与排除数（排除原因逐条注明数量）
5. **纳入**：纳入综述的研究数与报告数；纳入定量合成（荟萃分析）的研究数

---

## 3. RoB 2 工具概要

**名称**：随机试验偏倚风险评估工具（第 2 版，RoB 2）；官方工具与指导手册见 Cochrane 偏倚方法网站（methods.cochrane.org/bias）

### 评估域

| 域 | 编号 | 关注点 |
|------|------|--------|
| 随机化过程产生的偏倚 | D1 | 序列生成、分配隐藏、基线平衡 |
| 偏离预期干预的偏倚 | D2 | 盲法、方案依从性、意向治疗分析 |
| 缺失结局数据的偏倚 | D3 | 完整性、差异失访、缺失数据处理 |
| 结局测量的偏倚 | D4 | 结局评估方法、评估者盲法 |
| 选择性报告结果的偏倚 | D5 | 预注册、选择性报告 |

### 判断等级

- **低偏倚风险（Low risk）**：该域被判为低偏倚风险
- **部分关注（Some concerns）**：该域存在一些偏倚担忧
- **高偏倚风险（High risk）**：该域被判为高偏倚风险

### 总体判断算法

- 所有域均为低 → 总体**低**
- ≥1个域为部分关注，无高 → 总体**部分关注**
- ≥1个域为高 → 总体**高**

---

## 4. ROBINS-I 概要

**名称**：非随机干预研究偏倚风险评估工具（ROBINS-I）；官方工具与指导手册见 Cochrane 偏倚方法网站（methods.cochrane.org/bias）

### 评估域（7域覆盖3个时间点）

**干预前**：
- D1: 混杂偏倚
- D2: 选择参与者入组的偏倚

**干预时**：
- D3: 干预分类偏倚

**干预后**：
- D4: 偏离预期干预的偏倚
- D5: 缺失数据偏倚
- D6: 结局测量偏倚
- D7: 选择性报告结果偏倚

### 判断等级

- **低风险（Low）**：可与执行良好的 RCT 相比
- **中等风险（Moderate）**：非随机研究中合理但不能等同于 RCT
- **严重风险（Serious）**：存在重要问题
- **极严重风险（Critical）**：问题过多，无法提供有用证据
- **信息不足（No information）**：报告不足

---

## 5. I² 异质性解读指南

| I² 范围 | 等级 | 含义 | 操作 |
|----------|------|------|------|
| 0-40% | 低 | 异质性可能不重要 | 继续合并；报告 I² |
| 30-60% | 中等 | 可能代表中等异质性 | 继续合并；调查来源 |
| 50-90% | 显著 | 显著异质性 | 调查来源；考虑亚组分析；报告预测区间 |
| 75-100% | 极高 | 极大异质性 | 质疑合并是否有意义；考虑叙述性综合 |

**重要注意事项**：
- 各范围区间存在有意重叠
- I² 的解读取决于三件事：效应量大小、Q 检验的 p 值，以及对森林图的目视检查
- 方向一致的高 I²，比方向跨越零值的中等 I² 更不必担忧
- I² 受研究精度影响——研究精度都很高时，即便绝对差异很小也可能得到高 I²
- 报告 I² 时务必同时给出 95% CI（研究数少时该区间可能非常宽）

---

## 6. GRADE 证据确定性框架

**全称**：Grading of Recommendations, Assessment, Development and Evaluations

### 起始等级

| 研究设计 | 起始确定性 |
|---------|-----------|
| 随机试验 | 高（⊕⊕⊕⊕） |
| 非随机研究 | 低（⊕⊕◯◯） |

### 降低确定性的因素（降级）

| 因素 | 降级 | 适用条件 |
|------|------|---------|
| 偏倚风险 | -1 或 -2 | 研究设计/执行存在严重或极严重局限 |
| 不一致性 | -1 或 -2 | 无法解释的异质性（I² > 50%，效应方向不同） |
| 间接性 | -1 或 -2 | 证据不能直接回答综述问题的 PICOS |
| 不精确性 | -1 或 -2 | 置信区间宽、样本量小、CI 跨临床决策阈值 |
| 发表偏倚 | -1 | 漏斗图不对称、小样本效应、已知未发表试验 |

### 提升确定性的因素（升级——仅限观察性研究）

| 因素 | 升级 | 适用条件 |
|------|------|---------|
| 大效应量 | +1 或 +2 | RR > 2 或 < 0.5（大），RR > 5 或 < 0.2（极大），无混杂 |
| 剂量-反应梯度 | +1 | 观察到明确的剂量-反应关系 |
| 合理混杂 | +1 | 所有合理混杂因素都会降低观察到的效应 |

### 确定性等级

| 等级 | 符号 | 含义 |
|------|------|------|
| 高 | ⊕⊕⊕⊕ | 非常确信真实效应接近估计值 |
| 中等 | ⊕⊕⊕◯ | 中等确信；真实效应可能接近但可能有较大差异 |
| 低 | ⊕⊕◯◯ | 有限确信；真实效应可能有较大差异 |
| 极低 | ⊕◯◯◯ | 极少确信；真实效应可能存在很大差异 |

---

## 7. 方案预注册指南

### 何时注册

- 拟发表的**所有**系统综述都应预注册
- 在**开始文献检索之前**注册
- 预注册可防止结局报告偏倚并体现先验规划

### 注册平台

| Platform | Focus | Cost | URL |
|----------|-------|------|-----|
| **PROSPERO** | Health-related systematic reviews | Free | crd.york.ac.uk/prospero |
| **OSF Registries** | Any discipline | Free | osf.io/registries |
| **INPLASY** | Any discipline | ~$40 | inplasy.com |
| **Research Registry** | Any discipline | Free for systematic reviews | researchregistry.com |

### 方案内容（PRISMA-P 2015）

See `../../paper-templates/literature_review_template.md` for the complete protocol template.

关键章节：
1. Title, registration, authors, amendments
2. Rationale, objectives, PICOS eligibility criteria
3. Information sources, search strategy, study records management
4. Data extraction, risk of bias assessment, data synthesis plan
5. Meta-bias assessment, confidence in cumulative evidence

---

## 8. 软件与工具

### 元分析统计软件

| Tool | Language | Best For |
|------|----------|----------|
| **metafor** (R) | R | Comprehensive meta-analysis (all models, diagnostics) |
| **meta** (R) | R | User-friendly standard meta-analyses |
| **dmetar** (R) | R | Companion to "Doing Meta-Analysis in R" textbook |
| **RevMan** | Standalone | Cochrane reviews (required for Cochrane) |
| **robvis** (R) | R | Risk of bias visualization (traffic-light plots) |
| **GRADE pro GDT** | Web-based | GRADE Summary of Findings tables |

### 筛选与管理工具

| Tool | Purpose | Cost |
|------|---------|------|
| **Covidence** | Study screening, data extraction, RoB | Paid (free Cochrane license) |
| **Rayyan** | Abstract screening (AI-assisted) | Free |
| **EPPI-Reviewer** | Full review management | Paid |
| **ASReview** | AI-assisted screening | Free (open source) |
| **Zotero/Mendeley** | Reference management | Free |

---

## 9. 元分析效应量计算与依赖效应量（审稿专项检查）

> 本节约为元分析 / 系统综述稿件的**方法严谨性专项检查项**，对应种子缺陷 **DEF-R06**。常规 PRISMA / RoB / GRADE 见前 8 节。

### 9.1 效应量方差公式须匹配研究设计

| 设计 | 正确方差 / SE 公式 | 常见错用 |
|------|------------------|----------|
| 独立两组（treatment vs control） | 依组间/组内设计选用 Hedges g / Cohen d 标准误（含 J 校正） | — |
| 配对 / 单组前后测（同一批被试 pre→post） | v = 2(1−r)(1/n + d²/2n)，r 为前后测相关 | 误用独立两组公式 SE = √(2/n + d²/4n) |

**诊断签名（命中即判 DEF-R06）**：
- 全部（或多数）效应量来自同一被试的前后测，但稿件未报告前后测相关 r、未做 r 敏感性分析、SE 与独立样本公式吻合却与配对公式不符 → **方差公式错配设计**。
- 数值复核：用稿件自报 M/SD/n 反解 SE，分别与独立公式和配对公式（r = .3/.5/.7）比对，唯一吻合独立公式即坐实。

**后果**：方差错 → 权重错 → 合并 d、CI、Q、I²、τ²、漏斗图、trim-and-fill、fail-safe N、亚组 Q、元回归斜率全部失真；I² 被系统性低估。

### 9.2 依赖效应量（dependent effect sizes）必须处理

当多个效应量来自同一研究 / 同一批被试（共享样本），它们**非独立**，不得当作独立效应量纳入合并。

| 方法 | 适用 | 实现 |
|------|------|------|
| 三水平随机效应模型 | 效应量嵌套于研究、研究嵌套于文献 | `metafor::rma.mv` |
| 稳健方差估计 RVE | 依赖结构复杂 / 嵌套不清晰 | `clubSandwich` 包 |

**诊断签名（命中即判 DEF-R06）**：
- 稿件称 "N independent effect sizes" 但多项效应量来自同一研究（如 "two effect sizes in four studies and three in one study"）→ 自相矛盾。
- 未报告任一三水平 / RVE 模型，且未说明如何处置依赖 → 默认缺陷。
- 合计权重高度集中于少数共享样本研究（如单一研究独占 >10% 全局权重）→ 非独立被当独立，标准误被低估。

### 9.3 配套必检项（元分析方法严谨的完整闭环）

- **发表偏倚**：Egger 回归（截距 + 截距 SE + df + p）+ Begg 秩相关 + PET-PEESE；漏斗图用 contour-enhanced；trim-and-fill 在高 I²（>80%）下功效极低，fail-safe N 只回答「需多少 d=0 研究才压到不显著」，与偏倚存在与否逻辑无关，不得单凭其宣布无偏倚。
- **不确定性**：必须报 95% 预测区间、留一法、极值敏感性。
- **研究层面偏倚风险**：随机 / 非随机分别用 RoB 2 / ROBINS-I，不得仅报发表偏倚（PRISMA item 11/18 声称已报告则正文须确有）。

---

## 快速决策指南

```
Starting a systematic review?
│
├── 1. Register your protocol
│ └── PROSPERO (health) or OSF (any field)
│
├── 2. Write your protocol
│ └── Use PRISMA-P template → ../../paper-templates/literature_review_template.md
│
├── 3. Search systematically
│ └── ≥ 2 databases, document everything, PRISMA flow
│
├── 4. Screen and select
│ └── Dual screening, predefined criteria
│
├── 5. Assess risk of bias
│ └── RCTs → RoB 2 | Non-randomized → ROBINS-I
│
├── 6. Synthesize evidence
│ ├── Quantitative data + comparable studies → Meta-analysis
│ └── Otherwise → Narrative synthesis (SWiM)
│
├── 7. Assess certainty
│ └── GRADE for each outcome
│
└── 8. Report
 └── PRISMA 2020 checklist → ../../paper-templates/literature_review_template.md
```