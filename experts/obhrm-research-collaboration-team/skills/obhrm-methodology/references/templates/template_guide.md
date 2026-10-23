# 模板与交付指南

> **合并说明**：原 `template_index.md`（模板索引）与 `deliverable_template.md`（交付模板）合并到本文件，分 §1 模板索引 / §2 交付模板。

> 本文件是套件内**所有可复用模板**的统一索引。每个模板**只放指针（位置 + 用途 + 加载时机）**，不复制模板正文——模板正文见 `templates/` 与各域 references。**目的：避免模板散落多处、内容漂移。**
>
> **重构说明**：原 `output_template_library.md` 含大量模板内容复制、桌面路径策略、长输出防中断方案、字数门槛校准等"输出工程"内容，已分裂为：
> - **本文件**：仅做模板位置索引（你正在看的）
> - **`template_guide.md`**：交付物结构（图表登记 / 图注 / 证据矩阵 / 可追溯矩阵 / 收尾判定清单 / 优化建议清单）—— 仍为单点权威
> - **`../governance/gate_artifact_spec.md`**：评分块 schema 规范
> - **`../../../grant-writing/references/goal_hierarchy_rules.md`**：基金路径目标层级规则（B 域内部）
> - **桌面路径 / 长输出策略**：合并到 `../governance/stage_gate.md`（如有）
>
> **使用原则**：
> 1. 找模板 → 查本文件
> 2. 复制模板正文 → 按本文件给的指针到对应文件取
> 3. 模板字段缺失表示该模块信息不足，**应追问补充而非编造填充**

---

## 一、核心交付模板（`templates/` 目录）

| 模板 | 用途 | 加载时机 |
|------|------|----------|
| `../../paper-templates/imrad_template.md` | 实证论文 IMRaD 结构 | 论文路径 A5 论文写作 |
| `../../paper-templates/literature_review_template.md` | 文献综述成稿结构 | 综述路径 L6 综述成稿 |
| `../../paper-templates/bilingual_abstract_template.md` | 中英双语摘要 | 论文路径 A6 / 基金路径 B8 |
| `../../paper-templates/theory_paper_template.md` | 理论/概念性论文结构 | 论文路径（理论类） |
| `../../paper-templates/case_study_template.md` | 质性案例研究 / 扎根理论 | 质性路径 Q5 / 跨方法案例 |

## 二、跨路径通用交付模板（`references/` 目录）

| 模板 | 用途 | 加载时机 |
|------|------|----------|
| `template_guide.md` | 交付物脚手架（图表登记 / 图注 / 文献链 / 证据矩阵 / 可追溯矩阵 / 收尾判定 / 优化建议清单） | A2/A3/A5/B2/B9/M5/D4 任意阶段末 |
| `../governance/gate_artifact_spec.md` | 评分块 schema 规范 | 任何路径输出评分块前 |
| `../writing/apa7_guide.md` | APA7 英文/在线/图表格式细节 | A5/A6 英文稿件 |
| `../writing/apa7_guide.md` | APA7 中文引用规范 | A5/A6 中文稿件 |
| `../writing/apa7_guide.md`（含原 `../writing/apa7_cn_citation_guide.md` 内容） | APA7 双册（CN/EN 分册） | 任意引用校对 |
| `../writing/authorship_spec.md` | 署名 / 作者贡献 / authorship | A6 投稿前 |
| `../writing/abstract_writing_guide.md` | 摘要 / 结构化摘要 / abstract | A6/B8 |
| `../publishing/grant_statement_spec.md` | 基金声明 / Funding Statement / 资助声明 | B8/A6 |

## 三、L 域（文献综述）模板

L 域模板以 `knowledge/*.json`（机器可读）与 `references/*.md`（操作细则）双层组织：

| 模板 | 用途 | 加载时机 |
|------|------|----------|
| `../../../literature-review/knowledge/templates.json` | 中英双语模板字段 | 综述路径 L5 提纲 |
| `../../../literature-review/knowledge/bilingual_terms.json` | 中英术语映射 | 综述路径全程 |
| `../../../literature-review/knowledge/topic_scoping_prompt.md` | 选题方向收敛提示 | 综述路径 L1 选题 |
| `../../../literature-review/references/writing-templates.md` | 写作模板细则 | 综述路径 L5-L6 |
| `../../../literature-review/references/bilingual-paradigms.md` | 双语综述范式 | 综述路径 L5-L6 双语成稿 |
| `../../../literature-review/references/diagram-recipes.md` | 综述图表配方 | 综述路径 L6 |
| `../../../literature-review/references/paradigms.md` | 综述九范式（P1-P9）补充 | 综述路径 L3 范式选择 |
| `../../../literature-review/references/ai-fingerprint-guide.md` | 综述 AI 指纹检测 + 禁用表达 | 综述路径 L7 成稿自检 |
| `../../../literature-review/references/hrmr-standards.md` | HRMR 理论增量三层次+五要素 | 综述路径 L3 |
| `../../../literature-review/references/closed-loop-editing.md` | 闭环编辑（自检与修订） | 综述路径 L6-L7 |
| `../../../literature-review/references/nature-tips.md` | Nature 风格写作建议（高级） | 综述路径 L6 选读 |
| `../../../literature-review/references/peer_review_framework.md` | 综述同行评审框架 | 综述路径 L7 自评 |
| `../../../literature-review/references/verification-protocol.md` | 引用三态标注协议 | 综述路径 L7 |
| `../../../literature-review/knowledge/literature_research_methods.json` | 文献调研方法学（四原型 / Keshav / 偏误防御） | 综述路径 L2-L3（从根 references 下沉） |
| `../../../literature-review/references/pdf-ingestion.md` | PDF 资料库模式 | 综述路径 L2（PDF 输入场景） |

## 四、写作质量自检模板

**重构说明**：原 `../writing/writing_self_check.md` 与根 `quality_checklist.md` 命名易混，已重命名去歧义，并明确分工：

| 模板 | 用途 | 加载时机 |
|------|------|----------|
| `../writing/writing_self_check.md` | 写作质量自检（AI 高频词 / 标点 / 句长 / 结构模式） | A5/A6/L6 收尾 |
| `quality_checklist.md` | 通用交付检查（论文 / 基金 / 诊断 / 输出前） | 任意阶段交付前 |
| `verification_and_failure_modes.md` | 验证与 RedFlags 系统 | 任意自检 |
| `verification_and_failure_modes.md` | AI 生成内容失败模式 | 任意 |
| `../writing/academic_writing_style.md` | 学术写作风格（含去 AI 化增强） | 写作当时 |
| `../ethics/ethics_guide.md` + `../ethics/academic_integrity_protocol.md` | 伦理与学术不端 | 任意 |

**不重复**：`writing_self_check.md` 专注"写出来"层面（句式 / 标点 / 节奏），`quality_checklist.md` 专注"交付物"层面（结构 / 完整度 / 规范）。

## 五、阶段衔接 / 流程模板

| 模板 | 用途 | 加载时机 |
|------|------|----------|
| `../reasoning/thinking_protocols.md` | 头脑风暴 / 7 轮对话式对齐 | 论文路径 A0 / 综述路径 L1 前置 |
| `../governance/stage_gate.md` | 阶段衔接 / 动态路由 / 门控细则 | 任意阶段过渡 |
| `handoff-protocol.md` | 跨路径任务交接 / 字段级规格 | 跨路径 |
| `../governance/stage_gate.md` | 五步执行细则 / SKILL 执行补充 | 任意 |
| `../reasoning/thinking_protocols.md` | 多视角交叉验证（方法专家/理论专家/领域通才） | 各阶段自审 |
| `../reasoning/exemplar_anchoring.md` | "好长什么样"对标范例 | 任意产出自检 |
| `../reasoning/thinking_protocols.md` | "怎么想"而非"做什么"深度推理 | 任意 |

## 六、图表与统计模板

| 模板 | 用途 | 加载时机 |
|------|------|----------|
| `../methods/statistical_figure_standard.md` | 统计图表标准 / 图注规范 | D4/M5 图表收尾 |
| `../methods/statistical_report_standard.md` | 统计报告标准 / APA 报告格式 | D4/M5 |
| `../reasoning/argument_frameworks.md` | 论证连接示例（好/差对照） | A3/A5 |
| `../reasoning/argument_frameworks.md` | 交接产物示例 | 跨路径 |


---


> 本文件提供"建立连接"所需的**空白脚手架**。执行 A2/A3/A5/B2/B9/M5 时，**直接复制对应模板、填内容**，避免遗漏图表登记表 / 文献链 / 证据矩阵 / 可追溯矩阵。
> 规则与判定详见 `../governance/argument_connection_framework.md` 与 `visualization.md` 图表嵌入协议；本文件只给可填的空壳。

---

## 1. 图表登记表（每张图生成后立即登记）

| 编号 | 类型 | 归属阶段/子节 | 标题 | 文件(PNG/PDF) | 图注(≥80字) | 正文引用 |
|------|------|--------------|------|---------------|------------|----------|
| 图1 |  |  |  |  | [ ] 已完成 | [ ] 已引用 |
| 图2 |  |  |  |  | [ ] 已完成 | [ ] 已引用 |
| 表1 |  |  |  |  | [ ] 已完成 | [ ] 已引用 |

## 2. 图注模板（≥80字，APA7）

```
图N. [图题]。基于[数据/样本/方法]，[核心发现一句话，含关键统计量]。
[为何重要 / 对假设 Hx 的支持或否定 / 与既有文献的呼应]。
```

## 3. 文献链（每条脉络一套）

```
### 文献链N：[主题]
- 已有研究：
- 近五年推进：
- 仍然不足（缺口）：
- 本研究推进：
- 可引用核心证据：【等级】作者(年)；【等级】作者(年)
```

## 4. 证据矩阵（每条文献一行，嵌入位置必填）

| 编号 | 等级 | 类型 | 作者/年 | 关键发现 | 不足/边界 | 嵌入位置 | DOI |
|------|------|------|---------|----------|-----------|---------|-----|
| E1 |  |  |  |  |  |  |  |
| E2 |  |  |  |  |  |  |  |

## 5. 贡献-假设-结果-图表 可追溯矩阵（论文 A5）

| 贡献声明(关卡1) | 对应假设(A3) | 验证图表(A5) | 关键结果 | 是否支撑 |
|----------------|-------------|-------------|----------|----------|
| C1： | H1, H2 | 图3、表2 |  | [通过]/[不通过] |
| C2： | H3 | 图4 |  | [通过]/[不通过] |

## 6. 连接完成判定清单（收尾勾选，A5/B9/M5 通用）

**图表嵌入（每张图）**：[ ] 已生成 PDF+PNG [ ] 已编号登记 [ ] ≥80字图注 [ ] 正文≥1处引用
**论证连接**：[ ] 主张-证据-文献三元齐备（无悬空主张）[ ] 图尔敏 Warrant 机制解释 [ ] 认识论地位匹配 [ ] 文献链闭环到本研究 [ ] 证据矩阵嵌入位非空 [ ] 章节回扣上文 [ ] Discussion/讨论回应≥2 替代解释 [ ] 无逻辑断链
**主动优化建议（§7，前向增值）**：[ ] 已输出优化建议清单（A5/B9/M5 收尾勾选通过后必做，未输出不得结束交付）

## 7. 优化建议清单（收尾勾选通过后，前向增值）

> 来源：SKILL.md 全局规则 §7。A5/B9/M5 收尾「连接完成判定清单」勾选通过后输出。性质=前向增值层，区别于 审稿路径（诊断外部文档）与收尾判定清单（及格线）。直接复制下表填充。

| 优先级 | 位置 | 建议（可操作 + 改法） | 类型 |
|--------|------|---------------------|------|
| 高 | §3.2 | 补一张调节效应简单斜率图，交互效应更直观 | 补图 |
| 中 | §4 | 讨论未回扣 A3 的 H2，加一句"与 H2 预期一致……" | 补连接 |
| 中 | §5 | 因果主张仅满足 Bradford Hill 3 条，补时间性/剂量反应或限定为相关 | 强因果 |
| 低 | Discussion | 再回应一个竞争机制（如 LMX）作为替代解释 | 补替代解释 |

> **类型取值**：补图 / 补连接 / 强因果(Bradford Hill) / 补替代解释 / 强缺口 / 强结论 / 其他。
> **已很强时写**："无需重大优化，仅建议……"。**禁止空话**（"建议进一步提升""注意加强"类无效表述）。
> 每条建议必须带「位置 + 可操作改法」，不能只给方向不给落点。
