# references/ 目录触发映射与高频核心文档清单

> 本文件是入口文档 `../SKILL.md` 的**引用子系统（文档级触发）**：把 `references/` 目录的 md 文件按 8 主题子目录分组，按场景/关键词触发加载具体文档。与 `skill_router.md`（路径级路由）分工：**router 管"研究到哪条路径"，本文件管"路径内加载哪些 references 文档"**——两文件职责互补，不重复。
> 路径级路由判定见 `skill_router.md`；通用规则见 `skill_rules.md`。

---

## 高频核心文档（各阶段默认选用）

> 这些文档在对应阶段默认加载，无需触发词。

| 类别 | 关键文件 |
|------|------|
| 写作与格式 | `writing/writing_self_check.md`、`writing/academic_writing_style.md`、`writing/apa7_guide.md`、`methods/statistical_report_standard.md` |
| 评审与投稿 | `review/review_criteria.md`、`review/review_template.md`、`publishing/journal_submission_guide.md`、`review/revision_guide.md` |
| 理论与方法 | `methods/theory_method.md`、`reasoning/argument_frameworks.md` |
| 图表与数据 | `methods/statistical_figure_standard.md`、`templates/template_guide.md`、`reasoning/argument_frameworks.md` |
| 基金与选题 | `../../grant-writing/references/goal_hierarchy_rules.md`、`methods/topic_selection_rules.md`、`reasoning/thinking_protocols.md`、`methods/research_question_gap.md` |
| 学术规范 | `ethics/ethics_guide.md`、`templates/verification_and_failure_modes.md`、`governance/gate_artifact_spec.md` |
| 模板 | `../paper-templates/imrad_template.md`、`../paper-templates/literature_review_template.md`、`../paper-templates/bilingual_abstract_template.md`、`../paper-templates/theory_paper_template.md`、`../paper-templates/case_study_template.md` |
| 模板索引 | `templates/template_guide.md`（全部模板的指针，不复刻内容） |

---

## 触发映射表（按研究生命周期 5 段分组加载）

> 本表按 ① 问题从哪来 → ② 怎么做成研究 → ③ 怎么证明结论成立 → ④ 怎么获得学术认可 → 通用辅助 顺序分组。

### OB 基础教材（ob-textbook · 写论文/基金的概念地基）

> 内置《组织行为学》教材全文（已拆分为独立技能 `obhrm-textbook`，单一真源位于 `skills/obhrm-textbook/ob-textbook/`），作为研究团队写论文/基金时理解 OB 基础概念的底层语料。**先查 `skills/obhrm-textbook/ob-textbook/chapter-index.md` 定位章节，再读对应 `skills/obhrm-textbook/ob-textbook/chXX.md`**；所有概念性论断须标注教材出处（章节+标题），引文锚定、防幻觉。

| 触发场景 / 关键词 | 加载文档 | 阶段 |
|------------------|---------|------|
| OB 概念定义 / 理论基石 / 概念澄清 / "什么是X" | `skills/obhrm-textbook/ob-textbook/chapter-index.md`（先定位）→ `skills/obhrm-textbook/ob-textbook/chXX.md` | 通用 / A1 / B1 |
| 教材章节导航 / 找某主题出处 | `skills/obhrm-textbook/ob-textbook/chapter-index.md` | 通用 |

### ① 问题从哪来（选题 · 综述 · GAP · 头脑风暴 · 理论）

| 触发场景 / 关键词 | 加载文档 | 阶段 |
|------------------|---------|------|
| 头脑风暴 / 7 轮对话式对齐 / A0 前置 | `reasoning/thinking_protocols.md` | L0/A0 |
| 选题评分量表细则 / 7 维评价矩阵 | `review/quality_rubric.md` | L1/A1 |
| 问题卡 / 5W1H / 缺口分析 / A1 前置 | `methods/research_question_gap.md` | L2/A1 |
| 苏格拉底式追问 / 引导用户澄清 | `reasoning/thinking_protocols.md` | L1/A0 |
| 跨学科理论借鉴 / 理论视野拓展 | `publishing/cross_discipline_bridge.md` | L3/A1 |
| 写文献综述 / 述评类文章结构 / 综述模板 | `review/review_writing.md` | L4-L7 |
| 理论选择检查清单 / 理论数量限制 | `methods/theory_method.md` | L3/A1/A3 |
| 论证推理（深度）/ 图尔敏 / 因果 / Bradford Hill | `reasoning/argument_frameworks.md` | L3/A3 |
| 论证与连接强制动作（执行层）/ Warrant | `reasoning/argument_frameworks.md` | A3/A5 |
| 单篇 PDF / 链接速览 · 蒸馏 · 精读 | `../../literature-review/references/micro-skills/deep-distill.md` | L1–L3（精读增强） |

### ② 怎么做成研究（论文 A · 基金 B）

| 触发场景 / 关键词 | 加载文档 | 阶段 |
|------------------|---------|------|
| 基金声明 / Funding Statement / 资助声明 | `publishing/grant_statement_spec.md` | B8/A6 |
| 写摘要 / 结构化摘要 / abstract | `writing/abstract_writing_guide.md` | A6/B8 |
| 署名 / 作者贡献 / authorship | `writing/authorship_spec.md` | A6 |
| APA7 英文/在线/图表格式细节 | `writing/apa7_guide.md` | A5/A6 |
| APA7 中文引用规范 | `writing/apa7_guide.md` | A5/A6 |
| 预注册 / 方法论预登记 / OSF 注册 | `methods/preregistration_guide.md` | A4 |
| 问卷设计 / 量表 / 反向计分 / 心理测量术语 | `methods/psychometric_glossary.md` | A4/设计问卷 |
| 跨学科理论借鉴 / 理论视野拓展 | `publishing/cross_discipline_bridge.md` | A1/A3（与 ① 共享） |
| 论证连接强制动作 | `reasoning/argument_frameworks.md` | A3/A5（与 ① 共享） |
| 论文翻译 / 中转英 / 英转中 / 保留公式翻译 | `writing/translation_prompts.md` | A0-A7 任一段落 |
| 起标题 / 标题方案 / 标题优化 | `writing/title_generation.md` | A1/A6 |
| deep research / 深度调研 topic / 读透+追踪相关工作 | `../../paper-writing/references/micro-skills/deep-research.md` | A2 选题 + 章节契约前置 |

### ③ 怎么证明结论成立（一手 D · 二手 M · 质性 Q）

| 触发场景 / 关键词 | 加载文档 | 阶段 |
|------------------|---------|------|
| 系统综述 / PRISMA / Cochrane / RoB2 | `methods/systematic_review_toolkit.md` | M1-M5 |
| 证据检索 / 文献筛选流程 / PDF 清理 | `methods/evidence_retrieval_protocol.md` | A2/M2 |
| 统计图表标准 / 图注规范 | `methods/statistical_figure_standard.md` | D4/M5 |
| 统计报告标准 / APA 报告格式 | `methods/statistical_report_standard.md` | D4/M5 |
| 数据交付模板 / 可追溯矩阵 | `templates/template_guide.md` | A2/A3/A5/B2/B9/M5 |
| 质性研究论文 / 案例 / 扎根理论 | `methods/theory_method.md` | A0/A1/Q1-Q5（与 ① 共享） |
| 方法族知识库 | `../../data-analysis/quantitative/references/methods-knowledge.md` | D1-D4/M1-M5/Q1-Q5 |

### ④ 怎么获得学术认可（评审 C · 选刊 J · 投稿返修）

| 触发场景 / 关键词 | 加载文档 | 阶段 |
|------------------|---------|------|
| 评审判断标准 / 8 维诊断 | `review/review_criteria.md` | C0-C10 |
| 评审意见模板 / 可复用语句 | `review/review_template.md` | C5/C8 |
| 评审意见写作规范 | `review/review_writing.md` | C8 |
| 返修再评审 / 核实修改稿是否回应评审意见 | `review/revision_guide.md` | C9 |
| 领域期刊选择 / 目标期刊清单 | `publishing/field_journal_catalog.md` | A6/投稿/选刊（精确模式） |
| 期刊投稿指南 / 期刊格式要求 | `publishing/journal_submission_guide.md` | A6/选刊 |
| 论文后持续追踪文献 / 撤稿追踪 / 引用监控 | `publishing/literature_monitoring.md` | A6 后 |

### 通用辅助（贯穿各阶段）

| 触发场景 / 关键词 | 加载文档 | 阶段 |
|------------------|---------|------|
| 质量检查清单 / 通用交付检查 / 引用保真 | `templates/quality_checklist.md` | 任意（投稿前） |
| 可追溯账本 / 稳定 ID / 工作状态机 / 就绪状态 | `templates/traceability-ledger.md` | 任意（跨路径/长周期） |
| 来源可信分级 / M1·M2·F·U / 内容层级 | `governance/source_trust_tiers.md` | 任意（引用核验/文献检索） |
| 质量反馈闭环 / 诊断反哺生产 | `../../peer-review/references/feedback_loop.md` | C→A/B 闭环 |
| 写作质量检查 / AI 模式识别 / 学术表达 | `writing/writing_self_check.md` | 任意（成稿后） |
| 阶段衔接 / 动态路由 / 门控细则 | `governance/stage_gate.md` | 阶段过渡 |
| 跨路径任务交接 / 字段级规格 | `templates/handoff-protocol.md` | 跨路径 |
| 需要更深推理 / "怎么想"而非"做什么" | `reasoning/thinking_protocols.md` | 任意 |
| 输出需三视角交叉验证 | `reasoning/thinking_protocols.md` | 各阶段自审 |
| 学术写作 30 条原则（结构/语言/数学/图表/引用/流程） | `review/academic-writing-principles.md` | A0-A7 全程 |
| 论文转 PPT / 答辩 / 成果转化 | `publishing/output_conversion_guide.md` | A6 后转化 |
| PPT 逐页版式 / 组会答辩 PPT 生成 | `publishing/pptx-generation-guide.md` | A6 后转化 |
| 需要"好长什么样"对标范例 | `reasoning/exemplar_anchoring.md` | 任意产出自检 |
| 五步执行细则 / SKILL 执行补充 | `governance/stage_gate.md` | 任意 |
| 学术规范 / 伦理 / 学术不端 | `ethics/ethics_guide.md` | 任意 |
| 验证与 RedFlags / 错误模式识别 | `templates/verification_and_failure_modes.md` | 任意自检 |
| 引用验证流程 / 引用审计 | `methods/citation-workflow.md` + `methods/citation-checklist.md` | A5/A6 引用核验 |
| 分场景检索（学术/中文/通用/调试） | `methods/web-search-modules/` | A2 文献搜索 |
| AI 生成内容失败模式 / 低质量识别 | `templates/verification_and_failure_modes.md` | 任意 |
| 闸门产物规范 / 评分块格式 | `governance/gate_artifact_spec.md` | 任意评分点 |
| 论证连接示例 | `reasoning/argument_frameworks.md` | A3/A5 |
| 输出模板库 / 通用模板 | `templates/template_guide.md` | 任意（索引） |
| 全局方法论教训沉淀入口 | `governance/method_accumulation.md` | 蒸馏后 |

---

## 路由硬约束

> **去 AI 触发词的路由硬约束**：用户说"**改自然 / 像人话 / 去 AI 味 / 降 AI 味**" → 走 `../domains/humanize/humanize.md`（深度改写）；用户说"**查一下 AI 味 / AI 痕迹**" → 走 `../domains/quality-assurance/quality-assurance.md` 轻量评分 + `writing/writing_self_check.md`。**两档不同强度路径不互替**（humanize = 深度改写，quality-assurance = 轻量扫描；分属两种动作，分属两种强度）。

> **低频引用**：以下文档按需加载：`abstract_writing_guide.md` / `cross_discipline_bridge.md` / `exemplar_anchoring.md` / `grant_statement_spec.md` / `literature_monitoring.md` / `preregistration_guide.md` / `review_writing.md` / `revision_guide.md` / `stage_gate.md`。如常驻使用，建议在阶段确认点后调出。

---
