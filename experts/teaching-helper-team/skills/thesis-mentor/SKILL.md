---
name: thesis-mentor
version: 1.1.1
description: |
  管理学专业本科毕业论文辅导技能。覆盖六阶段全流程：启动诊断 → 选题评估 → 文献综述 → 研究设计 → 论文写作 → 修改定稿，并扩展期刊投稿、peer-review-response-guide与答辩分享三类研究型能力，支持调研型（实践型）与实证型（变量关系）两种论文结构。

  核心能力：五维选题评估、17-23 篇文献综述规范、图尔敏论证框架与证据矩阵、图表引擎（9 种本科常见图）、章节级academic-expression-phrase-bank、64 篇真实文献轻量索引（按需溯源、不内嵌原文）、降重与去AI化辩证处理；journal-matching-and-submission-guide、编辑决定与逐点peer-review-response-guide、答辩 PPT 大纲与讲稿。

  适用场景："论文选题""毕业论文""论文辅导""文献综述""研究设计""论文写作""论文修改""答辩准备""期刊投稿""peer-review-response-guide""选题创新"等需求。
---

# 管理学论文导师
> **归属**：领域技能层——论文辅导专家（thesis-mentor）

> **素材技能化衔接**：若文献综述 / 理论框架所需的教材、专著、PDF 已由 `material-extractor` 技能化，可加载其技能包（SKILL.md + glossary + chapters）作为结构化理论线索；遵循本技能「轻量索引、不内嵌原文」约定，真实文献仍须用户/检索确认。


## 架构

```
thesis-mentor/
├── SKILL.md                    # 本文件：总控与路由规则
├── README.md                   # 项目说明
├── references/                 # 参考资料层（拆 core/extended）
│   ├── core/                   # T1-T6 核心（16 文件）
│   │   ├── thesis-mentor-reasoning-protocol.md     # 深度推理指南
│   │   ├── multi-perspective-review-engine.md   # 多角色交叉验证
│   │   ├── mentoring-example-benchmarks.md     # 优秀范例对标
│   │   ├── mentoring-stage-gates.md     # 六阶段质量关卡
│   │   ├── topic-evaluation-criteria.md         # 选题创新性评估
│   │   ├── management-topic-bank.md         # 选题方向与范例
│   │   ├── literature-review-guide.md         # 文献综述方法论
│   │   ├── thesis-structure-guide.md         # 调研型+实证型结构规范
│   │   ├── writing-pitfalls-and-common-errors.md   # 常见错误检查
│   │   ├── output-templates.md           # 各阶段输出模板
│   │   ├── figure-and-table-embedding-protocol.md         # 图表编号/图注/引用规范
│   │   ├── argumentation-and-cohesion-framework.md       # 图尔敏/文献链/证据矩阵
│   │   ├── academic-expression-phrase-bank.md       # 章节级学术句型库
│   │   ├── academic-citation-standard.md           # 引用格式与来源限定
│   │   ├── thesis-full-workflow-guide.md           # 全流程系统化整理
│   │   └── reference-corpus-index.md             # 64篇真实论文轻量索引（按需溯源）
│   └── extended/               # T7-T9 扩展（3 文件）
│       ├── journal-matching-and-submission-guide.md   # 期刊匹配分析与投稿准备
│       ├── peer-review-response-guide.md             # 编辑决定拆解与逐点回复
│       └── thesis-defense-and-sharing-guide.md           # 答辩 PPT 大纲、讲稿与时间分配
├── scripts/                    # 工具脚本层
│   ├── _bootstrap.py         # 统一引导模块
│   ├── logging_manager.py    # 日志管理器
│   ├── config_manager.py     # 配置管理器
│   ├── audit.py              # 论文审核
│   ├── validate_skill.py     # 技能包完整性验证
│   ├── chart_engine.py      # 图表引擎（可选依赖）
│   └── chart_selftest.py    # 图表引擎冒烟测试
├── templates/                 # 模板目录
```

## 工作流

| 阶段 | 名称 | 核心参考 | 说明 |
|------|------|----------|------|
| T1 | 启动诊断 | thesis-mentor-reasoning-protocol、thesis-structure-guide | 评估学生水平、论文要求、时间节点 |
| T2 | 选题评估 | topic-evaluation-criteria、management-topic-bank | 创新点评价、选题生成、题目优化 |
| T3 | 文献综述 | literature-review-guide、thesis-structure-guide | 文献检索、结构化阅读、综述写作 |
| T4 | 研究设计 | thesis-structure-guide、thesis-mentor-reasoning-protocol | 理论框架、假设发展、方法选择 |
| T5 | 论文写作 | thesis-structure-guide、academic-expression-phrase-bank、阶段门控、output-templates | 引言、方法、结果、讨论（含章节级学术句型） |
| T6 | 修改定稿 | writing-pitfalls-and-common-errors、多视角引擎 | 格式检查 |
| T7 | 期刊投稿 | journal-matching-and-submission-guide.md、journal-fit-matrix.md | 期刊匹配分析、投稿准备（不预测录用、不代替编辑判断） |
| T8 | peer-review-response-guide | peer-review-response-guide.md、reviewer-response-tracker.md、revision-brief.md | 编辑决定拆解、逐点回复、修改追踪（AUTHOR_INPUT_NEEDED 显式标注） |
| T9 | 答辩准备 | thesis-defense-and-sharing-guide.md | 答辩 PPT 逐页大纲、讲稿、时间分配；结论必须可追溯到论文章节/表图 |

## 引用保真（跨技能必读）

> **必读**：`skills/citation-integrity/SKILL.md`——引用保真校验清单，全团 L0 权威层，四铁律为：不编引用 / 不归观点 / 标注无支撑 / 不超范围。T3 文献综述、T5 论文写作、T6 修改定稿三阶段强制加载，交付前须过其第四层交付门槛（条目存在率 / 原文落地率 / 归属正确率 / 待核实项清零 / 编号一致性 / deai_preflight 联动）。

本技能 `references/core/academic-citation-standard.md` 是该清单的 L1 派生层（引用格式与来源限定细则），只做增量约束，不得放宽清单要求；两者冲突时以清单为准。学生毕业论文的参考文献批量核验，按清单「批量作业法」五步执行。

> **必读（速查）**：`skills/citation-integrity/SKILL.md`——一页速查卡，写作过程中随手比对。**凡本技能产出中出现文献引用、政策条文或带出处的数字，交付前必须逐条执行引用保真校验，不得跳过**：每条引用同时满足三项硬条件（真实存在 / 可核实 / 引用格式与出处一致），无法核实的条目显式标注〔无可靠来源，待核实〕并在交付前清零，严禁编造作者、年份、期刊、卷期页码与 DOI。速查卡即本文件（citation-integrity/SKILL.md）的一页速查入口，与正文同源；需要完整门槛口径时参见本文件正文『交付门槛』章节。

## 参考资料索引

| 文件 | 用途 | 加载时机 |
|------|------|----------|
| `skills/citation-integrity/SKILL.md` | 引用保真校验清单：四铁律 + 核验四问 + AI 编造引用九特征 + 三态标注与处置 + 交付门槛 | T3、T5、T6 强制加载 |
| `skills/citation-integrity/SKILL.md` | 引用保真速查卡：三项硬条件 + 四铁律落地口径 + 待核实标注 + 严禁编造清单 | 凡产出含引用即加载 |
| `references/thesis-mentor-reasoning-protocol.md` | 论文辅导深度推理指南 | T1、T4 自动加载 |
| `references/core/multi-perspective-review-engine.md` | 多角色交叉验证 | T6 自动加载 |
| `references/core/mentoring-example-benchmarks.md` | 优秀论文范例对标 | T5 按需加载 |
| `references/core/mentoring-stage-gates.md` | 六阶段质量关卡 | T5 自动加载 |
| `references/core/topic-evaluation-criteria.md` | 选题创新性评估标准 | T2 自动加载 |
| `references/core/management-topic-bank.md` | 管理学选题方向与范例 | T2 自动加载 |
| `references/core/literature-review-guide.md` | 文献检索、结构化阅读、综述写作 | T3 自动加载 |
| `references/core/thesis-structure-guide.md` | 调研型+实证型结构规范、各章节写作规范 | T1-T5 多个阶段 |
| `references/core/writing-pitfalls-and-common-errors.md` | 常见写作错误与修改指南 | T6 自动加载 |
| `references/core/output-templates.md` | 各阶段输出格式模板 | T5 按需加载 |
| `references/core/figure-and-table-embedding-protocol.md` | 图表编号/图注≥80字/正文引用规范 | T4、T5 自动加载 |
| `references/core/argumentation-and-cohesion-framework.md` | 图尔敏/文献链/证据矩阵，解决连接弱 | T4、T5、T6 自动加载 |
| `references/core/academic-expression-phrase-bank.md` | 章节级学术句型库（连接/引用/数据/原因/对策/结论） | T5 自动加载、T4 按需 |
| `references/core/reference-corpus-index.md` | 64篇真实参考文献标题/专业/类型/页数索引，按需检索原文 | T2/T3/T5 按需加载 |
| `references/extended/journal-matching-and-submission-guide.md` | 期刊匹配分析与投稿准备，不预测录用、不代替编辑判断 | T7 按需加载 |
| `references/extended/peer-review-response-guide.md` | 编辑决定拆解、意见编号、逐点回复、修改映射 | T8 按需加载 |
| `references/extended/thesis-defense-and-sharing-guide.md` | 答辩 PPT 大纲、讲稿、时间分配，结论追溯到论文证据 | T9 按需加载 |
| `references/core/academic-citation-standard.md` | 学术引用格式、来源限定、检索核验流程、一致性校验 | T3、T5、T6 按需加载 |
| `references/core/thesis-full-workflow-guide.md` | 管理学论文写作全流程系统化整理：七环节方法论工具与常见问题对照 | T1-T6 全阶段参考 |

## 图表引擎（可选依赖）

自研图表引擎 `scripts/chart_engine.py`，覆盖本科管理学论文最常见的 9 种图（详见 `references/core/figure-and-table-embedding-protocol.md` 与 `scripts/chart_engine.py --list`）。

```bash
# 需在含 matplotlib 的环境中运行（可选依赖，未装则脚本提示，不影响其余功能）
python scripts/chart_engine.py 简单斜率图 '{"x":[1,2,3,4],"low_y":[2,3,4,5],"high_y":[1,2,3,4]}' --output ./产出/
python scripts/chart_engine.py --list
```

> **依赖说明**：matplotlib/seaborn/numpy/scipy 为**可选**依赖，随 `setup` 技能按需安装，不在必需之列，保持"无必需第三方依赖"的纯净分发承诺。未安装时，论文辅导的其余功能完全不受影响，仅不能使用自动出图。

## 论文结构与字数口径（调研型）

- 一、绪论（约 1500-2000 字）
- 二、现状分析（约 2000-2500 字）
- 三、问题影响（约 1000-1500 字）
- 四、对策研究（约 2000-2500 字）
- 五、结论和展望（约 800-1000 字）

> 实证型（变量关系）论文结构见 `references/core/thesis-structure-guide.md`；调研型与实证型各章字数口径以该文件为准。

## 文献溯源（按需检索原文）

本技能**不内嵌** 64 篇参考文献的 PDF 原文（避免版权风险与技能包加载负担）。当需要引用某篇论文的原始表述、数据或章节结构时，按 `references/core/reference-corpus-index.md` 的「源文件名」列，在用户的参考文献目录（默认 `~/Desktop/参考文献/`）读取对应 PDF；若该目录已抽取为 `.txt` 语料，则读取同名文本文件。

> 索引仅含标题 / 专业 / 类型 / 页数 / 摘要，用于**定位与溯源**；具体论证细节仍以原文为准。
