---
name: grant-writing
version: 1.0.0
author: "Xing Bu"
description: OBHRM 研究协作团 — 基金申报域（B 路径）。覆盖从立项依据 B1 到全文整合 B9 的基金项目书全流程，适用国自科 / 国社科 / 教育部 / 省市各类基金。
---
> **跨技能引用约定**：本文档以逻辑名形式引用兄弟技能（如 `` `skill:peer-review` ``），不使用逻辑名映射表，重命名或移动技能时按相对路径同步更新。
# 基金申报域
基金路径覆盖从立项依据到全文整合的基金项目书全流程。适用于国自科、国社科、教育部、省市各类基金。
> **OB 基础概念 grounding（教材）**：申报书涉及 OB 概念定义、理论基石、概念澄清（如立项依据中解释构念/机制）时，先查 `skills/obhrm-textbook/ob-textbook/chapter-index.md` 定位章节，再读对应 `chXX.md`；概念性论断须标注教材出处（引文锚定、防幻觉）。
---

## 路径概览

| 阶段 | 产出 | 字数 |
|------|------|------|
| B1 选题与立项依据 | 研究背景、立项必要性 | ≥800 |
| B2 国内外研究现状 | 5+文献链，3+/链，缺口矩阵 | ≥1500 |
| [注意] B2 须按 `skills/obhrm-methodology/references/reasoning/argument_frameworks.md` 输出「文献链(已有→推进→缺口→本项目)」+「证据矩阵(含嵌入位置)」，每条文献必须连到本项目缺口，禁止孤立罗列；**直接复制 `skills/obhrm-methodology/references/templates/template_guide.md` 的文献链/证据矩阵空模板填充** |
| [注意] B2 缺口矩阵 → 读取 `skills/obhrm-methodology/domains/visualization/visualization.md` 用韦恩图/热图/思维导图呈现研究空白 |
| **新颖性门控** | 双源定向反查记录 + 已立项课题核查 + 新颖性分级判定 | — |
| 说明：B2 国内外研究现状之后、B3 之前**必过**；CNKI/CSSCI 与 Web of Science 双源定向反查并加查基金已立项项目库，高相似命中则退回 B1/B2 重构选题，详见下方「新颖性门控」节 |
| B3 研究目标与内容 | 3-4项目标、关键科学问题 | ≥300 |
| B4 研究方案与技术路线 | 技术路线图、方法、可行性 | ≥300 |
| [注意] B4 技术路线图 → 读取 `skills/obhrm-methodology/domains/visualization/visualization.md` 用流程图（强制生成并嵌入） |
| B5 创新点与特色 | ≥3创新点 | ≥300 |
| B6 预期成果与考核指标 | 论文/专利/人才/社会效益 | ≥300 |
| [注意] B6 成果维度 → 读取 `skills/obhrm-methodology/domains/visualization/visualization.md` 用雷达图/流程图呈现考核指标 |
| B7 研究基础与条件 | 前期基础、团队 | ≥300 |
| B8 摘要与预算 | ≤400字摘要（国社科申报书摘要按 `references/goal_hierarchy_rules.md` 500字口径）、经费预算表 | ≥300 |
| B9 全文整合与润色 | 去重、术语统一、逻辑连贯 | ≥300 |
| [注意] B9 润色 → 读取 `skills/obhrm-methodology/domains/quality-assurance/quality-assurance.md` 执行高级润色检查 |

---

## 新颖性门控（B2 国内外研究现状之后、B3 研究目标之前）

> **同一门控、同一判据**：本节与论文路径「新颖性门控」采用同一套双源反查逻辑与分级标准（见 `skill:paper-writing` 新颖性门控节），仅落点改为基金语境——基金评审对"选题撞车"的容忍度低于期刊，同类课题已获立项即构成实质性减分。

**规则**：未完成双源定向反查并给出新颖性判定，不得进入 B3；B5 创新点必须建立在本门控的反查结论之上，不得自说自话。

**执行：**

1. **三靶点拆解**：核心构念对 / 理论机制 / 情境与研究对象，三者分别检索，不以一个大词代替。
2. **双源定向反查（两侧都要做）**：中文侧 CNKI / CSSCI（必要时并行万方、维普）+ 英文侧 Web of Science（必要时并行 Scopus）；检索式、时间窗与命中数逐项留痕，规范见 `skills/obhrm-methodology/references/methods/evidence_retrieval_protocol.md`。
3. **基金专项加查（基金路径特有）**：并行核查国家自然科学基金、国家社会科学基金**已立项项目库**中的同类课题，重点看近五年是否已有同构念同机制课题获批；已立项同类课题一律按高相似处理。
4. **分级判定与处置**：
   - **高相似（红）**：同构念对 + 同机制 + 同类情境已被研究或已获立项 → **打回 B1/B2 重构选题**，不得进入 B3。
   - **中相似（黄）**：构念对或机制之一已被研究，差异点未说清 → 补写差异化论证；论证不成立按红级处理。
   - **低相似（绿）**：未见同构念同机制研究，或已有结论存在冲突、边界未明 → 通过，反查结论写入 B2 缺口矩阵与 B5 创新点。
5. **回扣要求**：B5 每个创新点须能指回本门控的某条反查结论（"已有研究做到 X，本项目推进 Y"）。无反查支撑的创新点视为空话，B9 收尾时按逻辑断裂处理。

> **诚实边界**：反查结论只在所检索来源与时间窗内成立，不得写成无限定的"国内外首次"（四铁律：无支撑必标注）。

---

## 关键规则

- B2 是整个项目书的根：≥5 条脉络，≥3 篇/条，附缺口矩阵
- B4 技术路线图用 `skills/obhrm-methodology/domains/visualization/visualization.md` 的流程图
- B8 摘要 ≤400 字（国社科申报书摘要按 `references/goal_hierarchy_rules.md` 500 字口径），含研究背景+问题+内容+方法+意义
- B9 检查：术语一致性、段落衔接、参考文献格式、无重复内容

## 确认点

B1 / B2 / B8 / B9 等用户确认后推进，其余自动。

## 图表嵌入与交叉引用（基金路径必做 — 解决"结果呈现缺图、连接弱"）

> 项目书同样需要图表说话，更需要论证彼此咬合。所有图表遵循 `skills/obhrm-methodology/domains/visualization/visualization.md` 的「图表嵌入协议」；所有论证连接遵循 `skills/obhrm-methodology/references/reasoning/argument_frameworks.md`（图尔敏 Warrant / 文献链闭环 / 逻辑断裂检查）。

### 各阶段图表要求
- **B2 缺口矩阵** → 韦恩图 / 热图 / 思维导图：直观呈现"已有研究 vs 本研究空白"，正文引用「如图1所示，现有文献集中于A、B，缺口在C」
- **B4 技术路线图** → 流程图：强制生成并嵌入，分阶段（年度/任务）节点，正文逐节点说明
- **B6 预期成果** → 雷达图（成果维度：论文/专利/人才/转化）或流程图（年度里程碑），让考核指标可视化

### 交叉引用（强制）
- B4 技术路线**回扣 B3 目标**：「针对目标1-3，技术路线采用……」逐条对应，禁止目标与路线脱节
- B7 研究基础**回扣 B1/B2 缺口**：「前期已解决 B2 缺口中的X，剩余Y由本项目攻克」
- B5 创新点**回扣 B2 缺口 + B3 目标**：说明每个创新点对应哪个空白、服务哪个目标
- B2 文献链**闭环到本项目**：每条脉络「已有→推进→缺口→本项目推进」，缺口须与 B1 立项依据、B3 目标一一对应，禁止文献与项目脱节
- 全局「图表登记表」在 B9 收尾时核对：每张图已生成+编号+图注+正文引用
- **逻辑断裂检查**：以最苛刻评审视角逐节查"断链"（目标↔路线↔基础↔创新点），发现断链→补 Warrant 或重述，不得带断链进入 B9 确认

### B9 收尾核对清单（交付前必过）

> 直接复制 `skills/obhrm-methodology/references/templates/template_guide.md` 的「连接完成判定清单」勾选。完整条目见 `skills/obhrm-methodology/domains/visualization/visualization.md` 图表嵌入协议 + `skills/obhrm-methodology/references/reasoning/argument_frameworks.md` 完成判定。

**图表嵌入（每张图）**：[ ] 已生成 PDF+PNG [ ] 已编号登记（缺口图/技术路线图/成果图）[ ] ≥80字图注 [ ] 正文≥1处引用
**论证连接**：[ ] B4↔B3 目标逐条对应 [ ] B7↔B1/B2 缺口回扣 [ ] B5↔B2+B3 创新点对应 [ ] 文献链闭环到本项目缺口 [ ] 证据矩阵嵌入位非空 [ ] 无逻辑断链（目标↔路线↔基础↔创新点）

### B9 主动优化建议（收尾勾选通过后输出，前向增值）

> 直接复制 `skills/obhrm-methodology/references/templates/template_guide.md` 的「优化建议清单」。聚焦可加强处，给 2-4 条可操作建议，例如：
> - **[高] 补图**：B6 预期成果仅文字，建议补雷达图呈现论文/专利/人才/转化四维
> - **[中] 补连接**：B4 技术路线第3阶段未回扣 B3 目标2，建议逐节点标注对应目标
> - **[中] 强缺口**：B2 缺口矩阵未落到 B1 立项依据，建议明说"本项目专攻缺口X"
> 若已很强：明确写"无需重大优化，仅建议…"。禁止空话。

## 跨域联动

- **图表需求**（B2 缺口矩阵 / B4 技术路线图 / B6 雷达图）→ `skills/obhrm-methodology/domains/visualization/visualization.md`，按「图表嵌入协议」入正文。
- **联读数据分析路径**（B 线预研数据需一手数据支撑时）→ `../data-analysis/quantitative/quantitative.md`（D1–D4），完成 D4 后回 基金路径续写。
- **写完送审稿**（B9 完成后需预审）→ `skill:peer-review`（审稿路径），按关卡3同等标准过一遍。
- **配套方法层**：`references/goal_hierarchy_rules.md`（B1–B3 目标层级）、`skills/obhrm-methodology/references/methods/topic_selection_rules.md`（B1 选题）、`skills/obhrm-methodology/references/reasoning/argument_frameworks.md`（B2/B5 文献链与论证连接）、`skills/obhrm-methodology/references/reasoning/argument_frameworks.md`（B2/B3 论证逻辑）、`skills/obhrm-methodology/references/writing/writing_self_check.md` + `skills/obhrm-methodology/references/writing/academic_writing_style.md`（B9 写作质量与去AI化增强）。

- **需登录的文献检索（browser-skill）**→ `skill:browser-skill`：B 线研究现状（B2）如需登录后访问的学术库 PDF/引用抓取，经 `skill:browser-skill` 驱动已登录浏览器，与系统 WebSearch/WebFetch 检索（+ `skills/obhrm-methodology/scripts/format_search_results.py` 整理）互补。

## 协作交接

本路径产出的可交接对象与字段级规格见 `skills/obhrm-methodology/references/templates/handoff-protocol.md`：

- **B→D 委托分析**（B 线预研数据时）：交接块字段见链路一。
- **D→B 结果回传**（B 线预研数据后）：交接块字段见链路二；基金路径沿用 数据路径的可追溯矩阵。
- **B→C 写作→审稿**（B9 完成后送审稿）：交接块字段见链路三；目标期刊/层级字段填「项目书 / 国自科/国社科层级」。
- **C→B 审稿→返修**（审稿后按返修对照表处理）：交接块字段见链路四。
- **B→D再→B 返修重数据**（审稿要求重跑数据时）：先走链路四，再走链路一。
- **B→蒸馏**（基金路径中浮现可复用教训）：交接块字段见链路六；判层后落点 `skills/obhrm-methodology/references/governance/method_accumulation.md`（方法论层）或对应 reference（操作层）。

## 参考

- **方法层**：`references/goal_hierarchy_rules.md`（B 域 references/ 内部）、`skills/obhrm-methodology/references/methods/topic_selection_rules.md`、`skills/obhrm-methodology/references/reasoning/argument_frameworks.md`、`skills/obhrm-methodology/references/reasoning/argument_frameworks.md`、`skills/obhrm-methodology/references/writing/writing_self_check.md`、`skills/obhrm-methodology/references/writing/academic_writing_style.md`。
- **联读域**：`skills/obhrm-methodology/domains/visualization/visualization.md`、`../data-analysis/quantitative/quantitative.md`、`skill:peer-review`、`skills/obhrm-methodology/domains/quality-assurance/quality-assurance.md`。
- **跨路径字段**：`skills/obhrm-methodology/references/templates/handoff-protocol.md`（链路一/二/三/四/六）。
