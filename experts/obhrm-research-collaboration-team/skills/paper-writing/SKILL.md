---
name: paper-writing
version: 1.0.0
author: "Xing Bu"
description: OBHRM 研究协作团 — 论文写作域（A 路径）。覆盖从头脑风暴 A0 到答辩 A7 的完整论文写作生命周期（期刊/会议论文走 A6 投稿、学位论文走 A7 答辩），含贡献为先、理论建构与假设发展、IMRaD 成稿、图表嵌入与可追溯矩阵、答辩准备。
---
> **跨技能引用约定**：本文档以逻辑名形式引用兄弟技能（如 `` `skill:peer-review` ``），不使用逻辑名映射表，重命名或移动技能时按相对路径同步更新。
# 论文写作域
论文路径覆盖从头脑风暴到投稿的完整论文写作流程，含三大方法论关卡。
> **OB 基础概念 grounding（教材）**：写作中涉及 OB 概念定义、理论基石、概念澄清时，先查 `skills/obhrm-textbook/ob-textbook/chapter-index.md` 定位章节，再读对应 `chXX.md`；概念性论断须标注教材出处（引文锚定、防幻觉）。
---

## 路径概览

| 阶段 | 产出 | 字数 |
|------|------|------|
| **A0 头脑风暴** | 论文类型、学科、题目、背景、方法、结构（对话式对齐） | — |
| [注意] A0 为写前对齐阶段：通过 7 轮对话式问答对齐目标。A0 未确认前不得进入 A1。详见 `skills/obhrm-methodology/references/reasoning/thinking_protocols.md`（详细执行见下方「A0 头脑风暴」节） |
| A1 选题与问题界定 | 研究问题、理论缺口、创新点、研究问题卡 | ≥300 |
| [注意] A1 须产出 `研究问题卡`（5W1H 收敛 + 五类缺口归类 + 含证伪标准的 RQ 卡 + 提案就绪门控），模板与门控见 `skills/obhrm-methodology/references/methods/research_question_gap.md` |
| [注意] A1 确认后、A2 前，须为全部章节起草「章节契约」（每章核心问题+必覆盖要点+证据要求+衔接+验收标准），模板见 `skills/obhrm-methodology/references/templates/section-contract-template.md`；契约未立不得进入 A2 |
| **新颖性门控** | 双源定向反查记录 + 新颖性分级判定（通过 / 打回重构） | — |
| 说明：A1 研究问题确认之后、关卡1「贡献为先」之前**必过**；CNKI/CSSCI 与 Web of Science 双源定向反查，高相似命中则退回 A1 重构，详见下方「新颖性门控」节 |
| **[门控] 贡献为先** | `skills/obhrm-methodology/references/governance/confirmed_contribution.md` | — |
| A2 文献检索与研究空白 | 文献链、证据矩阵、框架图、不变量矩阵 | ≥300 |
| [注意] A2 须按 `skills/obhrm-methodology/references/reasoning/argument_frameworks.md` 输出「文献链(已有→推进→缺口→本研究)」+「证据矩阵(含嵌入位置)」，每条文献必须连到本研究；**直接复制 `skills/obhrm-methodology/references/templates/template_guide.md` 的文献链/证据矩阵空模板填充** |
| A3 理论建构与假设发展 | 假设+竞争假设、理论模型 | ≥300 |
| [注意] A3 每个假设 Hx 须用图尔敏 Warrant 给出「理论→假设」机制解释（读 `skills/obhrm-methodology/references/governance/argument_connection_framework.md`），不得只写"基于X理论提出H1" |
| [注意] A2 框架图 / A3 理论模型 → 读取 `skills/obhrm-methodology/domains/visualization/visualization.md` 生成并登记入「图表登记表」，A5 直接引用 |
| A4 研究方法与设计 | 样本论证、量表来源 | ≥300 |
| [注意] A4 完成后 → 读取 `../data-analysis/quantitative/quantitative.md` 执行 D1-D4 |
| D1-D4 数据分析 | (见数据分析域) | — |
| [注意] D4 完成后 → 回到本文件继续关卡2 |
| A5 论文写作与逻辑打磨 | 完整草稿（IMRaD）+ 图表嵌入 + 可追溯矩阵 | ≥300 |
| **[门控] 结果即验证** | `skills/obhrm-methodology/references/governance/results_validation.md` | — |
| **[门控] 面向审稿人** | `skills/obhrm-methodology/references/governance/reviewer_audit.md` | — |
| A6 投稿准备 | 投稿信、摘要优化、引用验证 | ≥300 |
| [注意] 三个关卡产物（`skills/obhrm-methodology/references/governance/confirmed_contribution.md` / `skills/obhrm-methodology/references/governance/results_validation.md` / `skills/obhrm-methodology/references/governance/reviewer_audit.md`）的**强制结构模板**见 `skills/obhrm-methodology/references/governance/gate_artifact_spec.md`，门控未产出或结构不全则不放行 |
| **A7 答辩准备（仅学位论文）** | 答辩 PPT、委员提问预判、陷阱题应答模板、自检清单 | ≥300 |
| [注意] A7 仅适用于本/硕/博**开题·中期·预答辩·正式答辩**；期刊/会议论文无答辩环节，走 A6 投稿。复用贡献声明/可追溯矩阵/稳定 ID，详见 `references/defense-preparation.md` |

---

## A0 头脑风暴（写前对齐 · 必须执行）

> **硬门控**：A0 未完成（用户未最终确认）时，禁止进入 A1 及后续任何阶段。无论任务看起来多简单，都必须经过此流程。

**核心原则**：一次只问一个问题，等待用户回答后再继续。提供推荐方案，让用户确认而非让用户设计。

**7 轮对话**：
1. 探索上下文 + 确认论文类型（本/硕/博/期刊/会议/课程）
2. 确认学科领域（OBHRM/管理心理学/战略管理等）
3. 确认论文题目（可暂定）
4. 确认研究背景与目的
5. 确认研究方法（按学科调整问法）
6. 确认输出格式（默认 Markdown；Word/PPTX/XLSX 经平台腾讯文档技能链 `tencent-docx` / `tencent-pptx` / 腾讯文档表格 产出，按期刊要求调整；本地 python-docx 仅作离线兜底）
7. 推荐章节结构并确认（根据论文类型自动推荐 IMRaD/理论/案例/综述结构）

**语言默认规则**：本硕博论文默认中文（除非明确要求英文），SCI/SSCI 默认英文。不主动询问语言。

**汇总确认**：7 轮结束后展示汇总，等待用户明确确认（"对""可以""确认"）。确认后输出进度条进入 A1。

> 完整交互协议、示例对话、反模式见 `skills/obhrm-methodology/references/reasoning/thinking_protocols.md`。

---

## 新颖性门控（A1 研究问题确认之后、关卡1 贡献为先之前）

> **位置不可颠倒**：先证明"别人没做过、或没这么做过"，再谈"我的贡献是什么"。若先写贡献声明再补查新颖性，等于给既定结论找证据，本身就是确认偏倚。

**规则**：未完成双源定向反查并给出新颖性判定，不得进入关卡1，更不得进入 A2 及以后。

**执行：**

1. **拆解反查靶点**：把 A1 研究问题卡拆成三个可检索的靶点——核心构念对（自变量-因变量）、理论机制（中介 / 调节）、情境与样本边界。三个靶点分别检索，不能只搜一个大词就下结论。
2. **双源定向反查（两侧都要做，缺一侧即未完成）**：
   - **中文侧**：CNKI / CSSCI（必要时并行万方、维普），覆盖中文管理学与应用心理学核心期刊。中文的重复选题常常不出现在英文库中，漏检即漏判。
   - **英文侧**：Web of Science（必要时并行 Scopus）。可用系统 WebSearch/WebFetch 检索 + `skills/obhrm-methodology/scripts/format_search_results.py`（结果整理）做初筛，但初筛不替代人工核验原文。
   - 检索式、来源、时间窗、命中数逐项记录，留痕规范见 `skills/obhrm-methodology/references/methods/evidence_retrieval_protocol.md`。
3. **相似度分级判定**（对最相近的若干篇逐篇实质比对，看构念与机制，不看题目字面）：

| 级别 | 判定标准 | 处置 |
|------|---------|------|
| **高相似（红）** | 已有同构念对 + 同机制 + 同类情境的已发表研究，本研究仅换样本、换行业、换地区 | **打回 A1 重构研究问题**，不得进入关卡1 |
| **中相似（黄）** | 构念对或机制之一已被研究，本研究的差异点尚未说清 | 补写差异化论证：明确"已有做到哪一步、本研究向前推进什么"；论证不成立则按红级处理 |
| **低相似（绿）** | 未见同构念同机制研究，或已有研究结论相互冲突、边界条件未明 | 通过；反查结论写入 A2 文献链，并作为关卡1 贡献声明"新颖性"要素的支撑 |

4. **红级打回后的重构方向**（回 A1 时至少认真尝试一条，换个题目名字不算重构）：换理论视角重新解释同一现象；从主效应转向边界条件与作用机制；引入被忽略的中国情境制度性变量；用不同证据形态回应已有研究的冲突结论；把已有研究的隐含假设显性化并加以检验。
5. **产出**：新颖性反查记录（三靶点检索式 + 双源命中情况 + 最相近 3–5 篇的实质比对 + 分级判定 + 处置结论）。该记录直接供 A2 文献链与关卡1 复用，不重复劳动。

> **诚实边界**：反查未命中不等于"国际首创"。判定只写"在所检索来源与时间窗内未见同构念同机制研究"，不得升级为无限定的首创声称（四铁律：无支撑必标注）。

---

## 三大方法论关卡

### 关卡1 [门控] 贡献为先 — A1 后、A3 前

**规则：** 未确认核心贡献声明，不得进入理论建构和写作。

**执行：**
1. 用一句话写出：「本文首次发现/证明了______，贡献在于______」
2. 确认满足三要素：新颖性、可验证性、重要性
3. 输出 `skills/obhrm-methodology/references/governance/confirmed_contribution.md`，未确认则阻塞 A3-A6

### 关卡2 [门控] 结果即验证 — D4 后、A5 前

**规则：** 每个 Results 子节必须验证至少一条贡献承诺。

**执行：**
1. 列出关卡1的所有贡献声明
2. 逐条检查 D4 产出（及 D2-D4 图表）是否支撑每条声明
3. 有指标无贡献映射 → 失败
4. 输出 `skills/obhrm-methodology/references/governance/results_validation.md`，并附**贡献-假设-结果-图表 可追溯矩阵**（见 A5），每张支撑图标注编号（图N）与关键统计量
5. 任一贡献无对应图表/结果支撑 → 回 A5 补图或重述贡献，不得进入 A6

### 关卡3 [门控] 面向审稿人 — A5 后、A6 前

**规则：** 投稿前以三个审稿人视角预审。

**执行：**
1. 分别以「方法专家」「理论专家」「领域通才」审视
2. 每视角输出：价值判断 + 最大弱点 + 是否接收
3. 汇总 `skills/obhrm-methodology/references/governance/reviewer_audit.md`。任一拒稿 → 回修正

---

## A2 文献调研增强

- **四种原型**（探索者/调查者/验证者/考核者）：A2 启动时确认原型 → 详见 `../literature-review/knowledge/literature_research_methods.json`
- **Keshav 三遍法** + **偏误防御**（WYSIATI/锚定/可用性/效度）+ **不变量矩阵**：详见 `../literature-review/knowledge/literature_research_methods.json`
- **英文文献搜索**：两步走——① 系统 WebSearch/WebFetch 获取学术 API 数据（CrossRef / Semantic Scholar 等）存为 raw.json；② `python skills/obhrm-methodology/scripts/format_search_results.py --input raw.json --query "<query>" --year 2020-2026 --format json` 去重排序

---

## A5 写作阶段：图表嵌入 + 论证连接

> 遵循 SKILL.md 全局规则「图表必嵌入 + 交叉引用 + 论证连接」。本段仅列 A5 特有落地动作，通用规则不重述。

### A5 必做动作
1. **图表嵌入**：D2-D4 所有图表按 `skills/obhrm-methodology/domains/visualization/visualization.md` 图表嵌入协议编号、配图注(≥80字)、正文引用。维护全局登记表。
2. **可追溯矩阵**：复制 `skills/obhrm-methodology/references/templates/template_guide.md` 空模板，填贡献→假设→图表→结果四列，关卡2必过。
3. **论证连接**：读 `skills/obhrm-methodology/references/reasoning/argument_frameworks.md`，写后对照 `skills/obhrm-methodology/references/reasoning/argument_frameworks.md` 好/差样例自检。
4. **润色**：结论前置 / 精确限定 / 主动语态 / 去ai腔调 / 章节图表明示互引。口语化、感受性、经验性表达升级为学术严谨表述，按 `skills/obhrm-methodology/references/writing/academicization.md` 三条底线（去感受化补证据 / 去绝对化加限定 / 去车轱辘话加深度）处理——与去 AI 痕（humanize）区分。
5. **逆向提纲 + 论断-证据对齐**：成稿后执行逆向提纲（写中心论点→每段主题句→证据点→映射校验），并对摘要/引言每项论断用 `Claim | Evidence | Status` 格式核验证据；方法见 `skills/obhrm-methodology/references/writing/reverse_outlining.md`，论断-证据结构化映射亦可在关卡2 `results_validation.md`「论断–证据结构化映射」一节落地。

### A5 收尾核对清单（进入 A6 前必过）
> 完整条目见 `skills/obhrm-methodology/domains/visualization/visualization.md` 图表嵌入协议 + `skills/obhrm-methodology/references/reasoning/argument_frameworks.md` 完成判定。

**图表嵌入**：[ ] 已生成+编号+图注+正文引用
**论证连接**：[ ] 主张-证据-文献齐备 [ ] Warrant清晰 [ ] 文献链闭环 [ ] Discussion回应≥2替代解释 [ ] 无逻辑断链
**稳定 ID 闭环**：[ ] 主张 C / 证据 D·F·T·L（按载体）/ 文献 L / 图 F / 表 T 已赋编号并登记可追溯矩阵（见 `skills/obhrm-methodology/references/governance/stable_id_system.md`）
**术语账本**：[ ] 全文术语一致性检查通过（见 `skills/obhrm-methodology/references/templates/terminology-ledger-template.md`）

### A5 主动优化建议
> 收尾通过后，复制 `skills/obhrm-methodology/references/templates/template_guide.md`「优化建议清单」，给 2-4 条可操作建议（补图/补连接/强因果/补替代解释）。禁止空话。未输出此清单不得结束 A5。

## A6 投稿前：引用验证 + 去AI检查

- 引用验证：作者/卷/页码/DOI 逐一核对，输出 `skills/obhrm-methodology/references/governance/citation_audit.md`
- 去AI痕迹（light/medium/heavy）：①句式/②过渡/③术语/④论证密度/⑤语气（编号用①-⑤，区别于数据分析 D1-D4）

## A7 答辩准备（仅学位论文 · 成稿后）

> **适用边界**：本/硕/博的开题、中期、预答辩、正式答辩。**期刊/会议论文无答辩环节，不进入 A7**。A7 不是写作步骤，而是把 A5 已沉淀的资产"讲出来、答得住"。

**执行**（完整方法见 `references/defense-preparation.md`）：
1. **答辩 PPT**：按 12–15 页骨架（封面→背景问题→文献缺口→RQ→框架→方法→发现→贡献→局限→Q&A），一页一主张、图表大于文字、结论前置。
2. **委员提问预判**：按主席/方法派/理论派/应用派/挑刺派分配准备权重，给每位拟任委员写 ≥3 个预设问题。
3. **陷阱题应答**：用「承认→定位→证据→边界」四步框架，复用可追溯矩阵与稳定 ID 秒级回指证据（C/D/F/T/L/R/V）。
4. **冷场/不会答兜底**：诚实说"暂无充分证据，初步想法是…后续验证"，**绝不编造数据/文献/结论**（学术诚信红线）。
5. **答辩前自检**：过 `references/defense-preparation.md` 第八节清单（脱稿演练、贡献 30 秒说清、核心图表可离稿解释、局限已主动暴露）。

**复用资产（不重做）**：贡献声明（`confirmed_contribution.md`）→ 开场/总结；A5 可追溯矩阵 → 被问"证据在哪"秒级定位；稳定 ID → 问答中回指主张与证据。

## 跨域联动

- **A4 → 数据路径**（一手数据分析）→ `../data-analysis/quantitative/quantitative.md`（D1–D4），完成 D4 后回 论文路径续写 A5 与关卡2。
- **A6 → 选刊路径**（投稿前选刊匹配）→ `skill:journal-selection`，13 标准画像+粗略推荐。
- **A5 → A7 答辩路径**（学位论文成稿后准备答辩）→ `references/defense-preparation.md`：PPT 结构、委员提问预判、陷阱题应答模板、冷场兜底、自检清单；复用贡献声明/可追溯矩阵/稳定 ID。
- **A5 → 学术化转换**（口语/经验性表达升级为学术严谨）→ `skills/obhrm-methodology/references/writing/academicization.md`：三条底线（去感受化补证据 / 去绝对化加限定 / 去车轱辘话加深度）+ 转换对照表；与去 AI 痕（humanize）区分，二者并行不替代。
- **A5/A6 → 审稿路径**（成稿后送诊断审稿）→ `skill:peer-review`（C0–C10），按八维+偏倚+种子缺陷+Trust Boundary 独立诊断。
- **A2 / 综述联动**（论文引言/相关工作需独立综述支撑时）→ `skill:literature-review`（综述路径七阶段）。
- **图表需求**（A2 框架图 / A3 理论模型 / A5 全程图表）→ `skills/obhrm-methodology/domains/visualization/visualization.md`，按「图表嵌入协议」入正文。
- **写作质量与去AI**（A5/A6 收尾）→ `skills/obhrm-methodology/references/writing/writing_self_check.md` + `skills/obhrm-methodology/references/writing/academic_writing_style.md`（含去AI化增强）；用户明确要求深度去AI时切 `skills/obhrm-methodology/domains/humanize/humanize.md`。
- **方法层与论证**：`skills/obhrm-methodology/references/methods/research_question_gap.md`（A1：5W1H+五类缺口+RQ卡+提案门控）、`skills/obhrm-methodology/references/methods/topic_selection_rules.md`（A1 选题）、`../literature-review/knowledge/literature_research_methods.json`（A2：四原型/Keshav/偏误防御/不变量矩阵）、`skills/obhrm-methodology/references/reasoning/argument_frameworks.md`（A2/A3 论证逻辑）、`skills/obhrm-methodology/references/reasoning/argument_frameworks.md`（A3/A5：Warrant/文献链闭环/逻辑断裂）、`skills/obhrm-methodology/references/review/review_criteria.md`（A6/关卡3 自检标准）、`skills/obhrm-methodology/references/reasoning/thinking_protocols.md`（A0 协议）。

- **需登录的文献检索（browser-skill）**→ `skill:browser-skill`：A2 背景调研如需登录后访问的学术库（Google Scholar / Web of Science）的 PDF 与引用抓取，经 `skill:browser-skill` 驱动已登录浏览器，与系统 WebSearch/WebFetch 检索（+ `skills/obhrm-methodology/scripts/format_search_results.py` 整理）互补。

## 学科分流参考

OBHRM 论文写作可能跨学科视角，按论文定位选择学科写作规范：

- **人文/社科导向**（社会现象分析、质性论证、理论建构）→ `references/disciplines/humanities-writing.md`（文科写作专项：论证结构/写作风格/引用格式/章节指南/质量检查清单）。
- **实证/量化导向**（问卷、横断面、面板数据）→ `references/disciplines/empirical-reporting.md`（实证研究报告规范：STROBE/PRISMA 选择、伦理声明、统计描述与 P 值报告、结果表格规范）。
- 法学等不匹配学科规范不采用；OBHRM 主路径仍以本技能 A0-A7 为准，学科规范仅作章节级补充。

## 微技能

> 微技能由 `references/micro-skills/` 提供，作为苏晚晴 A0-A7 主路径的前置/后置增强模块。每个微技能可独立触发。

| 微技能 | 阶段 | 作用 | 文件 |
|--------|------|------|------|
| deep-research | A2 选题 + 章节契约前置 | 论文原文级深度调研（Topic + Primary + Recent works 结构化），**随本包维护** | `references/micro-skills/deep-research.md` |

## 协作交接

本路径产出的可交接对象与字段级规格见 `skills/obhrm-methodology/references/templates/handoff-protocol.md`：

- **A→D 委托分析**（A4 到达后）：交接块字段见链路一（含假设清单、变量表、数据文件、委托范围、目标呈现）。
- **D→A 结果回传**（D4 完成后）：交接块字段见链路二（含检验决策、APA 结果、假设裁决、稳健性、图表登记、分析师警告）；论文路径消费方式：原样进可追溯矩阵，不支持的假设不得改写。
- **W→C 写作→审稿**（A5 完成后送审稿）：交接块字段见链路三（含稿件、目标期刊/层级、可追溯矩阵、自检结果、已知薄弱点、产出形态）。
- **C→W 审稿→返修**（审稿路径诊断后）：交接块字段见链路四；建返修对照表逐条处理。
- **W→C9 返修→再审**（修改稿与回应函）：交接块字段见链路五。
- **A↔L 综述协作**（用户要单独综述或先搞定文献综述章节）：交接块字段见链路七；综述路径主导七阶段，成稿后回灌 论文路径。
- **A6→J 投稿选刊**：交接块字段见链路八。
- **A→蒸馏**（论文路径中浮现可复用教训）：交接块字段见链路六；判层后落点 `skills/obhrm-methodology/references/governance/method_accumulation.md`（方法论层）或对应 reference（操作层）。

## 参考

需细节时读取 `skills/obhrm-methodology/references/reasoning/thinking_protocols.md`（A0）、`skills/obhrm-methodology/references/methods/research_question_gap.md`（A1：5W1H+五类缺口+RQ卡+提案门控）、`skills/obhrm-methodology/references/methods/topic_selection_rules.md`（A1）、`../literature-review/knowledge/literature_research_methods.json`（A2，含四种原型/Keshav三遍法/偏误防御/不变量矩阵）、`skills/obhrm-methodology/references/reasoning/argument_frameworks.md`、`skills/obhrm-methodology/references/reasoning/argument_frameworks.md`（A3）、`skills/obhrm-methodology/references/writing/writing_self_check.md`、`skills/obhrm-methodology/references/writing/academic_writing_style.md`（A5/A6，含去AI化增强）、`skills/obhrm-methodology/references/writing/academicization.md`（A5 学术化转换：三条底线+对照表，与去AI区分）、`skills/obhrm-methodology/references/review/review_criteria.md`（A6/关卡3）、`references/defense-preparation.md`（A7 答辩准备：PPT结构/委员预判/陷阱题应答/冷场兜底/自检清单）。学术检索结果整理脚本见 `skills/obhrm-methodology/scripts/format_search_results.py`（A2 英文文献搜索，检索数据由平台 WebSearch/WebFetch 预先获取）。图表需求见 `skills/obhrm-methodology/domains/visualization/visualization.md`。跨路径交接字段见 `skills/obhrm-methodology/references/templates/handoff-protocol.md`。

## 引用核验

投稿前文献须过 `skills/obhrm-methodology/references/methods/citation_verification.md` 的 Crossref + Retraction Watch 闸门，与引用保真四铁律并行。
