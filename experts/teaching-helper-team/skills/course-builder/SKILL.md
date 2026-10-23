---
name: course-builder
version: 1.1.1
description: >
  面向大学/高校教师的课程建设全流程技能，覆盖五大核心能力：知识框架梳理、教学设计（课程大纲/单元设计/课时教案）、教材/讲义编制、教学课件PPT制作、内容质量审校。
  适用于高校教师提出"教学设计""教案""课程大纲""课程规划""知识框架""知识脉络""整理成教材""讲义""课件""课程建设""备课""教学质量"等需求时。
  覆盖本科、研究生、高职等高等教育学段，支持文理工医等各学科。
  内置方法论：UbD逆向设计、OBE成果导向、建构性对齐、ADDIE、布鲁姆分类法、Bloom提问链、学情三维诊断、三档深度知识框架、S/P/C分层质检。
  支持从零散资料（讲义/笔记/论文/扫描件）整理为系统化教材，生成教学课件PPT，并对产出内容进行质量审校。
---

# 课程建设专家
> **归属**：领域技能层——课程建设专家（course-builder）


## 概述

本技能为高校教师提供课程建设全流程支持。与中小学教学设计的核心差异：大学教学强调学科前沿性、研究性学习、学术思维培养、学分制课时规划与多元考核方式。

> 课程素材可来自 `material-extractor` 的提取产物（结构化全文 `full_text.txt` + 元数据 `metadata.json`，落 `data/pipeline/incoming/`，见 `skills/material-extractor`）：据此做知识框架梳理、教材编制与课件制作，避免每次重新解析原书。该产物由主理人经 `data/pipeline/` 总线转发给本技能消费。

五大核心能力形成完整闭环：

| 能力 | 做什么 | 核心产出 |
|------|--------|---------|
| **知识框架梳理** | 把课程主题或教材资料提炼成结构化知识脉络图 | 知识框架图（三档深度）+ 概念依赖关系图 |
| **教学设计** | 课程大纲、单元教学设计、课时教案 | Syllabus + 教案（含Bloom提问链、分层任务） |
| **教材编制** | 从零散资料整理为系统化教材/讲义 | 教材初稿 → 质检 → 终稿 |
| **课件制作** | 生成教学PPT课件 | HTML 单文件课件（.pptx 仅机构强制时备选） |
| **质量审校** | 对产出内容进行分层质量检查 | 质检报告 + 修订建议 |

### 文件间交叉引用体系

6个核心参考文件形成互引网络，每文件首部均标注与其他文件的引用关系（课件设计指南 `ppt-design-guide.md` 已迁至 `ppt-maker` 技能，见其 SKILL.md）：

| 核心文件 | 职责 | 被谁引用 |
|---------|------|--------|
| course-design-frameworks.md | 教学设计理论与模板 | 所有其他文件 |
| quality-review.md | 质量审校规范 | textbook-structuring, course-design-frameworks, ppt-maker/references/ppt-design-guide |
| textbook-structuring.md | 教材编制流程 | course-design-frameworks, quality-review |
| knowledge-framework.md | 知识框架梳理 | course-design-frameworks, textbook-structuring |
| workflow-governance.md | 工作流治理（多角色/会话/UX） | textbook-structuring, course-design-frameworks |
| textbook-quality/* (10个文件) | 教材专用详细质检规则 | quality-review.md（通用概要） |

## 触发词与识别信号

### 触发词

教学设计、教案、课程大纲、课程规划、课程建设、备课、课时计划、知识框架、知识脉络、章节脉络、课程梳理、重点提炼、整理成教材、讲义、课件、课件设计、教学质量、教案优化

### 识别信号表

听到以下说法时，直接进入对应动作：

| 用户说法 | 真实诉求 | 立即执行 |
|---------|---------|---------|
| "帮我设计一门课" / "写课程大纲" | 需要完整课程设计 | → Phase 2 教学设计流程 |
| "帮我设计一节课" / "写教案" | 需要课时教案 | → Phase 2 课时教案，启动Bloom提问链 |
| "这门课的知识体系是什么" / "知识太散" | 需要知识框架 | → Phase 1 知识框架梳理 |
| "把这些资料整理成教材" | 需要教材编制 | → Phase 3 教材编制流程 |
| "做个课件" / "做PPT" | 需要教学课件 | → Phase 4 课件制作 |
| "教案写满但说不清学生会啥" | 缺可观测目标 | → 用UbD逆向设计，先写目标再排活动 |
| "基础班和提升班怎么上得不一样" | 需要分层教学 | → 输出基础/标准/挑战三层差异化方案 |
| "这节课有哪些好提问" | 需要提问设计 | → 生成Bloom六层提问链+候场追问 |
| "内容写完了，质量怎么样" | 需要质量审校 | → Phase 5 质量审校 |

## 工作流总览

```
Phase 0  需求确认与信息收集
    ↓
Phase 1  知识框架梳理（可选，但强烈推荐）
    ↓
Phase 2  教学设计（课程大纲 → 单元设计 → 课时教案）
    ↓                         / Phase 4  课件制作
Phase 3  教材编制 ────────────\
    ↓
Phase 5  质量审校
```

Phase 3 与 Phase 4 可并行或按需选择。并非所有任务都需要走完全流程——根据用户需求选择对应阶段进入。

---

## Phase 0：需求确认与信息收集

### 信息收集清单

向用户确认以下关键信息（未提供的项需主动询问）：

| 信息项 | 说明 | 示例 |
|--------|------|------|
| 课程名称 | 课程全称 | 《数据结构与算法》 |
| 学段层次 | 本科/研究生/高职/专升本 | 本科二年级 |
| 学科门类 | 文/理/工/医/农/经管/法学/艺术等 | 工科计算机类 |
| 学时学分 | 总学时、理论/实验学时分配、学分 | 48学时（理论32+实验16），3学分 |
| 先修课程 | 学生已掌握的基础知识 | 程序设计基础、离散数学 |
| 教学对象 | 学生人数、专业背景、能力水平 | 计算机科学专业大二，约60人 |
| 现有资料 | 用户已有的教材、讲义、大纲、参考文献等 | 有参考教材，无现成教案 |
| 素材是否已提取 | 该教材/文档是否已由 `material-extractor` 提取（产物 `full_text.txt` + `metadata.json`，落 `data/pipeline/incoming/`） | 已提取则直接加载其全文+元数据作为知识源，跳过重复解析原书 |
| 输出需求 | 需要哪种产出（框架/大纲/教案/教材/PPT/质检） | 课程大纲+课时教案+课件PPT |
| 特殊要求 | 课程思政、产教融合、双语教学、认证要求等 | 需融入课程思政元素 |

### 学情三维诊断（大学版）

当涉及课时教案或分层教学时，从三个维度分析班级起点：

| 维度 | 诊断内容 | 教学调整方向 |
|------|---------|-------------|
| **知识基础** | 先修课程掌握程度、知识盲区、能力分布 | 基础薄弱→补铺垫；基础扎实→加速推进 |
| **学习动力** | 专业认同感、课程兴趣、学习投入意愿 | 动力弱→增强现实关联与成就感 |
| **学习习惯** | 自主学习能力、文献阅读习惯、协作意识 | 习惯弱→提供方法支架与结构化任务 |

> **卡点**：班情不清
> **自救**：用近期作业/小测/课堂表现抽样估计起点，标注推测项，逐步补全。

---

## Phase 1：知识框架梳理

### 何时使用

- 用户需要了解某门课的知识脉络、核心知识点、概念依赖关系
- 用户提到"知识框架""知识脉络""章节脉络""课程梳理""重点提炼"
- 用户提供了教材/笔记，需要重组成结构化知识体系
- 作为教学设计或教材编制的前置步骤（强烈推荐）

### 三档深度自动切换

根据输入内容自动判断深度，用户也可显式指定：

| 用户输入 | 自动档位 | 输出内容 |
|---------|---------|---------|
| 仅课程主题 | **框架档** | 3-5层知识框架树 + 延伸学习建议 |
| 课程主题 + 重点话题 / 教学目标 | **框架+重点讲解档** | + 5-10个重点节点200-500字讲解 + 核心知识点提炼 + 概念依赖关系图 |
| 任一配置 + 明确要求全讲 | **全节点档** | + 所有叶子节点讲解（分批，每批≤15） |

### 核心设计原则

1. **节点级防幻觉溯源**：含数字/专名/公式/名词的节点，必须标注来源（用户材料原文 或 AI推断）
   - 纯主题模式（无材料）：所有节点标注为AI推断，顶部加警示 banner
   - 材料优先模式：每节点对材料做校验，匹配成功标注来源，失败标注AI推断

2. **概念依赖关系"克制"挖掘**：
   - 限制条数：≤ 总节点数 × 0.3
   - 每条必带置信度（高/中/低）和具体依赖原因
   - 类型限定为6类：前置条件 / 归纳关系 / 细化关系 / 对比关系 / 应用关系 / 工具关系
   - **禁止**生成"A和B有关系"这种空话

3. **重点节点选择可解释**：
   - 中心度策略（默认）：依赖图中入度/出度排名前N
   - 频次策略：用户材料中出现次数≥阈值（仅材料模式有效）
   - 混合策略：两种各取一半

### 关键决策检查点

| 检查点 | 触发条件 | 提供选项 | 默认（用户沉默时） |
|--------|---------|---------|-------------------|
| CP-A 模式确认 | 仅有课程主题且属常见课程 | 继续 / 补充材料 / 取消 | 取消 |
| CP-B 触顶警示 | 节点数≥90 | 继续生成 / 拆分课程 / 收紧到3层 | 拆分课程 |
| CP-C 溯源失配 | 失配率>30% | 补充材料 / 接受AI推断 / 重新选范围 | 补充材料 |

### 输出格式

默认输出 Markdown 知识框架。如用户需要，可额外生成 Mindmap（交互式思维导图）或 Mermaid 图。

详细方法论见 [references/knowledge-framework.md](references/knowledge-framework.md)。

> **卡点**：纯主题模式下生成框架，知识点可能不准
> **自救**：所有节点标注为AI推断，顶部加警示banner，提示用户核对教材后再使用。
>
> **卡点**：节点数膨胀过大（>100）
> **自救**：触发CP-B触顶警示，建议用户拆分课程或收紧到3层。

---

## Phase 2：教学设计

### 设计框架选择

根据课程特点选择主设计框架。详细说明与模板见 [references/course-design-frameworks.md](references/course-design-frameworks.md)。

| 框架 | 适用场景 | 核心逻辑 |
|------|---------|---------|
| **逆向设计（UbD）** | 强调学习成果达成 | 目标→评价→活动（以终为始） |
| **OBE成果导向教育** | 工程教育认证、专业认证 | 毕业要求→课程目标→教学设计 |
| **建构性对齐** | 确保目标-方法-评价一致 | 三要素对齐检查 |
| **ADDIE模型** | 新建课程整体设计 | 分析→设计→开发→实施→评价 |

多数情况混合使用：以 OBE 或 UbD 确定目标与评价框架，用建构性对齐检查一致性，按 ADDIE 组织内容序列。

### 2.1 课程大纲（Syllabus）

标准模块：

1. **课程基本信息**——名称、编码、学时学分、先修课程、适用专业
2. **课程简介**——200-300字概述
3. **课程目标**——3-5条，使用布鲁姆动词，对应毕业要求指标点
4. **教学内容与安排**——按周次/章节列出教学要点、学时分配
5. **教学方法**——讲授、研讨、实验、项目驱动、翻转课堂等
6. **考核方式**——过程性评价与终结性评价结合，明确权重与对应目标
7. **教材与参考书目**
8. **课程思政**（可选）

> **卡点**：课程目标写"理解""掌握"——不可观测不可评价
> **自救**：改写为"能独立完成X""能区分A与B""能用自己的话解释Y"等可观测表述。

> **卡点**：教学目标与评价脱节——写了目标但不知道怎么检测
> **自救**：用逆向设计，先定"怎么证明学会了"再排教学活动；每条目标至少配一种评价方式。

> **卡点**：教案写满环节但经不起教研追问
> **自救**：检查每个活动是否对应一条可观测目标；无法对应的活动是装饰，删掉。

详细模板见 [references/course-design-frameworks.md](references/course-design-frameworks.md)。

### 2.2 单元教学设计

针对某一教学单元（通常2-6学时）：

1. **单元概述**——主题、学时、课程定位
2. **单元目标**——知识/能力/素质三维分解
3. **学情分析**——已有基础、可能困难、认知特点（用学情三维诊断）
4. **教学内容结构**——知识点结构图/思维导图
5. **教学策略**——方法与活动设计
6. **评价方案**——形成性评价方式
7. **教学资源**

### 2.3 课时教案

单次课（通常2学时/90分钟）的详细方案：

1. **课程信息**——课程名称、主题、学时、对象
2. **教学目标**——可观测、可评价（按布鲁姆层次标注）
3. **重点与难点**——标注突破策略
4. **教学过程**——按时间线，每环节标注：时间、内容、教师活动、学生活动、设计意图
5. **Bloom提问链**——6-8个递进提问 + 候场追问
6. **分层任务**——基础/标准/挑战三档
7. **课后作业**
8. **教学反思**（课后填写）

#### Bloom提问链生成器

每节新课至少在4个层次设计提问：

| Bloom层次 | 关键词 | 示例提问（以数据结构为例） |
|-----------|--------|--------------------------|
| 记忆 | 是什么/列举 | 二叉搜索树的定义是什么？ |
| 理解 | 能不能解释/比较 | 为什么二叉搜索树的中序遍历是有序的？ |
| 应用 | 用这个做一下 | 给定序列[7,3,9,1,5]，画出BST的构建过程 |
| 分析 | 为什么/分几类 | BST与平衡二叉树在什么场景下性能差异最大？ |
| 评价 | 哪个好/对不对 | 对比BST和哈希表，哪种更适合数据库索引？为什么？ |
| 创造 | 你能设计 | 设计一个支持快速查找和范围查询的数据结构 |

每个提问配1-2个候场追问，用于冷场或答案偏浅时递进：

```
问：二叉搜索树的定义是什么？
候场1.：左子树和右子树各满足什么条件？
候场2.：如果中序遍历一棵BST，会得到什么序列？
候场3.：你能举一个BST的实际应用例子吗？
```

#### 分层差异化输出

当提供学情信息时，输出三档差异化任务；未提供时只输出标准版并注明"无学情分层"。

| 维度 | 基础层（达标线以下） | 标准层（达标线） | 挑战层（学有余力） |
|------|---------------------|-----------------|-------------------|
| 例题难度 | 课本例题 + 1道变式 | 课本例题 + 2道变式 | 课本例题 + 跨章综合题 |
| 练习题量 | 4道基础 | 6道混合 | 4道拔高 + 1道开放 |
| 提问层次 | 记忆+理解 | 记忆+理解+应用 | 全Bloom覆盖 |
| 作业 | 巩固型 | 巩固+拓展 | 拓展+研究型 |

#### 课堂环节时间矩阵（大学90分钟课时）

| 环节 | 主要任务 | 时间 | 占比 | 失败模式与应对 |
|------|---------|------|------|---------------|
| 导入 | 情境/旧知链接/认知冲突 | 10min | 11% | 学生没进入状态→准备2个备选导入钩子 |
| 新授 | 概念建构/理论讲解/示范 | 35min | 39% | 关键步卡壳→准备"再讲一遍"话术与图示 |
| 实践 | 练习/实验/案例分析 | 25min | 28% | 完成率<60%→立即降级或拆分任务 |
| 深化 | 拓展/前沿/对比讨论 | 10min | 11% | 学生沉默→改为"同桌讨论2分钟" |
| 总结 | 学生自述+教师补充+结构图 | 5min | 6% | 学生沉默→改成"对同桌说一个收获" |
| 作业 | 分层布置+提交标准 | 5min | 6% | 学生记不清→写板书+拍照发群 |

课时伸缩规则：
- 45分钟课时：5/15/12/5/3/5
- 60分钟课时：5/20/18/8/4/5
- 120分钟课时：10/45/35/15/10/5

详细模板与完整示例见 [references/course-design-frameworks.md](references/course-design-frameworks.md)。

---

## Phase 3：教材/讲义编制

### 何时使用

当用户提供了零散资料（讲义、笔记、论文、扫描件等）但缺少系统化教材时。

### 阶段化工作流

```
S0 资料分析 → S1 体系规划 → S2 内容组织 → S3 教学要素补充 → S4 质检 → S5 终稿交付
```

每阶段设推进门禁，不满足前置条件时不推进，向用户说明缺失项。

| 阶段 | 做什么 | 推进条件 |
|------|--------|---------|
| **S0 资料分析** | 盘点资料、提取知识点、生成覆盖度报告 | 核心知识点覆盖度≥60% |
| **S1 体系规划** | 设计章节结构、知识递进逻辑 | 用户确认章节目录 |
| **S2 内容组织** | 按章节填充内容、标注来源与缺口 | 各章具备标题+核心内容 |
| **S3 教学要素** | 添加学习目标、导读、小结、习题 | 每章含目标+小结+习题 |
| **S4 质检** | 分层质量检查（见Phase 5） | S层+P层检查通过 |
| **S5 终稿** | 格式规范化、统一术语编号 | 通过洁净检查 |

### 串行写作约束

- 每轮最多修改2个文件，完成1个→汇报→再进行下一个
- 修改前说明"接下来修改哪个文件、改哪几处"
- 单文件操作超30秒无输出时，输出一行进度提示

> **卡点**：资料覆盖度不足，核心知识点缺失
> **自救**：标注缺口，先完成已覆盖部分，缺口部分标注"待补充"并提示用户提供更多资料。
>
> **卡点**：多份资料间内容矛盾
> **自救**：以权威教材为主参考，标注矛盾点并提示用户裁决；不同版本教材取最新版。
>
> **卡点**：教材内容写完但质量不明
> **自救**：进入Phase 5质量审校，先跑S层（结构层）检查，不通过不交付。

详细方法见 [references/textbook-structuring.md](references/textbook-structuring.md)。

---

## Phase 4：教学课件PPT

### 制作流程

1. **显式加载 ppt-maker 制作技能**：通过 **Skill 工具主动加载技能名 `ppt-maker`**（或在对话中提及「做PPT / 课件生成 / 演讲文稿」触发），再读取其 `SKILL.md` 与 `skills/ppt-maker/references/` 下的 `ppt-design-guide.md`、`html-deck-spec.md`、`style-presets.md` 了解设计规范、技术规范与风格预设。
   > **关键约定（修复「执行任务时无法加载子技能」）**：即便本技能（course-builder）已处于执行中、用户未输入 ppt-maker 触发词，也必须用 Skill 工具**主动拉起 `ppt-maker` 技能**，不能等触发词。加载后按 `ppt-maker` 技能的决策流（HTML 优先 / 传统 .pptx 备选）生成。
   > **契约依据**：该「技能内直连」是 `skills/_shared/DATA-CONTRACT.md`「通信与调用规则」明文允许的唯一例外（课件环节）；除此以外，本技能与其它技能之间仍须经主理人中转交换数据。
2. **理清故事线**：用金字塔原理梳理逻辑主线（结论先行、MECE分组），确定"一页一主题"
3. **确定视觉系统**：按 `ppt-maker` 技能的 `style-presets.md` 选定 1 套风格预设（默认 `academic-light`），统一字体、配色；生成后可按 T 键运行时换肤现场定夺
4. **构建页面**：每页标题即观点（Action Title），内容只支撑标题；讲稿写入各页 `notes` 字段（正文不可见，供 S 键演讲者模式）
5. **数据可视化**：柱状图按数值排序（时间序列除外）、饼图不超过6切片、折线图不超过3-4条线；图表由 `ppt-maker` 生成器以内联 SVG 绘制
6. **验收门禁（必跑）**：`build_deck.py --check` 输出逐页验收报告（信息密度 / 字号 / 对比度 / 溢出），0 FAIL 方进入下一步；必要时拆页 / 换图整改后重跑
7. **校验一致性**：通篇检查配色、字体、间距、术语是否一致；投屏分辨率与离线（断网）实测
8. **交付可编辑文件**：HTML 方案产出 `.html`（可编辑源，推荐配 `--dist` 演示版对外分发；浏览器内可拖拽/改字/保存）；传统方案产出 `.pptx`

### Action Title 原则

每页标题不是"算法复杂度分析"（描述性），而是"快速排序的平均时间复杂度为O(n log n)"（结论性观点）。

### 信息密度控制

| 页面类型 | 文字量上限 | 要点行数 |
|----------|-----------|---------|
| 标题页 | 1行 | 1行 |
| 知识讲解页 | 80字 | 4-6行 |
| 案例展示页 | 60字+图表 | 3-4行 |
| 讨论互动页 | 30字 | 1-2个问题 |
| 小结页 | 100字 | 5-8个要点 |

> **卡点**：课件页面信息过载，每页文字太多
> **自救**：检查信息密度表，超过80字的页面拆分或用图表替代文字。
>
> **卡点**：课件逻辑跳脱，前后页无关联
> **自救**：用金字塔原理梳理逻辑主线，确保每页标题即结论（Action Title），前后页有因果关系。
>
> **卡点**：数据来源不明或可能虚构
> **自救**：所有数据必须标注来源；缺失数据要求用户提供或明确标注"假设数据"。

详细课件设计原则、五种课型模板、内容到幻灯片映射方法见 [ppt-maker 课件设计指南](../ppt-maker/references/ppt-design-guide.md)。

---

## Phase 5：质量审校

### 何时使用

- 内容产出完成后，需要检查质量
- 用户问"内容写得怎么样""有没有问题"
- 教材编制S4阶段、课件制作完成后

### 三层质检体系

| 层级 | 检查内容 | 严重程度 | 处理方式 |
|------|---------|---------|---------|
| **S层（结构层）** | 目标-评价-活动对齐、章节逻辑递进、知识覆盖完整 | 阻断级 | 必须修复后才能交付 |
| **P层（专业层）** | 学术语义准确性、概念定义规范、引用格式、数据可靠性 | 严重 | 应修复，标注待改项 |
| **C层（表达层）** | 语言流畅性、术语一致性、排版格式、可读性 | 建议 | 列出建议，用户决定是否修改 |

**交付前确定性门禁（必跑）**：成稿交付前运行 `python skills/deai-rules/scripts/deai_preflight.py <成稿路径>`，须 PASS；与 `deai-rules` 五维自评（≥45）共同构成 quality 门禁，未 PASS 不得标记为交付物（规则见 `skills/deai-rules/SKILL.md`）。

### S层检查清单

- [ ] 每条课程目标至少对应一种评价方式
- [ ] 每个教学活动标注了对应的目标
- [ ] 章节间有清晰的逻辑递进关系
- [ ] 知识点覆盖了课程目标要求的所有内容
- [ ] 考核方式与目标的认知层次匹配

### P层检查清单

- [ ] 概念定义准确，无歧义
- [ ] 术语全书一致，首次出现标注英文
- [ ] 引用格式统一（GB/T 7714）
- [ ] 数据、公式、图表准确
- [ ] 无过时信息或已废弃理论

### C层检查清单

- [ ] 语言流畅，无口语化或生硬表述
- [ ] 无AI写作痕迹（空洞排比、过度修饰、套话）
- [ ] 图表编号连续、格式统一
- [ ] 排版规范（字体、字号、行距、页边距）

### AI痕迹检测

检查以下AI写作常见特征并标注修改建议：

| 特征 | 示例 | 修改方向 |
|------|------|---------|
| 空洞排比 | "不仅...而且...更..." 三连 | 删除冗余，保留一个 |
| 过度修饰 | "极其重要的""非常关键的" | 改为具体说明为何重要 |
| 万能套话 | "在当今时代背景下" | 直接切入主题 |
| 假设性结尾 | "这值得我们深思" | 改为具体结论或行动建议 |
| 模式化过渡 | "接下来我们来看" | 自然过渡或直接陈述 |

详细质检规范见 [references/quality-review.md](references/quality-review.md)。

---

## 关键设计原则

### 教学目标编写

使用布鲁姆分类法（修订版）的动词来表述目标，确保可观测、可评价：

| 认知层次 | 常用动词 | 目标示例 |
|----------|----------|----------|
| 记忆 | 列举、描述、识别 | 能列举常见排序算法及其时间复杂度 |
| 理解 | 解释、归纳、比较 | 能解释动态规划的基本原理与适用条件 |
| 应用 | 计算、演示、运用 | 能运用Dijkstra算法求解最短路径问题 |
| 分析 | 区分、检验、分解 | 能分析不同数据结构对算法效率的影响 |
| 评价 | 评判、论证、评估 | 能评估给定场景下最优算法选择的合理性 |
| 创造 | 设计、构建、提出 | 能设计一个满足特定需求的完整数据结构方案 |

> **常见错误**：写"理解XX概念"——这是愿望不是目标；改成"能用一句话准确说出概念"。

### 考核评价设计

- **过程性评价**（30-50%）：课堂参与、小组研讨、阶段性测验、实验报告、作业
- **终结性评价**（50-70%）：期末考试、课程论文、项目答辩、作品展示
- **评价与目标对齐**：每条课程目标至少对应一种评价方式，确保"教-学-评"一致性

### 课程思政融入

在专业课程中自然融入思政元素，避免生硬说教：

- 从学科发展史切入科学精神与家国情怀
- 通过工程案例引入职业道德与责任意识
- 在技术讨论中培养辩证思维与系统观念
- 结合行业现状激发创新意识与使命感

---

## 行为准则

| [通过] 应该做 | [不通过] 不能做 |
|---------|----------|
| 先问"想达到什么目标"再设计教学 | 不问目标直接出流程表 |
| 每条目标配可观测的评估证据 | 写"理解""掌握""体会"等空话 |
| 在时间矩阵中标明实际时间并适配课时 | 用90分钟课时但默认45分钟分配 |
| Bloom提问链覆盖至少4层 | 只设计记忆题或只设计开放题 |
| 分层教案必须明确三档差异 | 同一份任务卡给所有学生 |
| 每个提问配1-2个候场追问 | 只给1个问题，课上冷场 |
| 输出后留调整空间让老师确认 | 把AI产出当"必须照做" |
| 在无学情时明确说明并提供降级方案 | 强行编造学情数据 |
| 知识框架节点标注来源（材料/ AI推断） | 静默把AI推断当事实输出 |
| 教材内容写完后跑质检再交付 | 跳过质检直接交付终稿 |
| 课件每页标题即结论（Action Title） | 标题只写"XX分析"等描述性标题 |
| 数据必须标注来源，缺失则明确标注 | 虚构公司数据、市场数据 |

### 学情隐私保护规则

当教案或教学设计中涉及学生个人信息时，遵守以下脱敏规则：

| [通过] 允许 | [不通过] 禁止 |
|---------|---------|
| 使用学号、化名、座位号 | 使用真实姓名 |
| 使用聚合数据（如"近3次测评得分率<60%"） | 单独列出具体学生分数+排名 |
| 使用"基础组/中等组/拔尖组" | 在教案正文中直接点名"某学生退步明显" |
| 课堂记录可用化名或学号 | 写入身份证号、家庭信息等敏感信息 |

---

## 参考文件与资产导航

### 核心参考文件（主文档）

| 文件 | 内容 | 何时读取 |
|------|------|----------|
| [references/course-design-frameworks.md](references/course-design-frameworks.md) | 四大设计理论框架、GRASPS评估框架、WHERETO展开、课程大纲模板、单元设计模板、课时教案模板、Bloom提问链详解、分层输出方法、常见错误对照表、完整实例、考核评价设计模式 | 生成任何教学设计产出物时 |
| [references/knowledge-framework.md](references/knowledge-framework.md) | 三档深度知识框架方法论、节点数指引、输入解析规则、概念依赖关系分类体系、防幻觉溯源规范、多格式输出方法、完整实例 | 用户需要梳理知识框架时 |
| [references/textbook-structuring.md](references/textbook-structuring.md) | 阶段化工作流S0-S5、资料分析方法、章节规划原则、串行写作约束、习题生成策略、字数指引、资料冲突处理、版本管理、教材格式规范 | 用户需要从资料编制教材/讲义时 |
| [../ppt-maker/references/ppt-design-guide.md](../ppt-maker/references/ppt-design-guide.md) | 金字塔原理与Action Title、五种课型PPT模板、内容到幻灯片映射方法、数据可视化规范、视觉设计系统、教室规模字号指引、无障碍设计 | 用户需要制作教学课件PPT时 |
| [references/quality-review.md](references/quality-review.md) | S/P/C三层质检清单、AI痕迹检测概要（完整去AI味规则以 quality/deai-rules 为唯一 SSOT）、内容分类标注体系、修订流程规范 | 产出内容需要质量审校时 |

### 教案设计参考库

| 文件 | 内容 | 何时读取 |
|------|------|----------|
| [references/lesson-planning/core-output-templates.md](references/lesson-planning/core-output-templates.md) | 单课时教案七大板块完整模板、单元整体教案框架 | 需要填写教案模板时 |
| [references/lesson-planning/lesson-plan-template.md](references/lesson-planning/lesson-plan-template.md) | 可直接复制使用的标准教案模板（扩展版） | 需要快速生成教案时 |
| [references/lesson-planning/layered-lesson-example.md](references/lesson-planning/layered-lesson-example.md) | 《一次函数的应用》A/B/C三层任务卡完整示例 | 需要参考分层教案写法时 |

### 知识框架详细参考库

| 文件 | 内容 | 何时读取 |
|------|------|----------|
| [references/knowledge-framework-detail/concept-dependency-taxonomy.md](references/knowledge-framework-detail/concept-dependency-taxonomy.md) | 6类概念依赖关系的详细定义与挖掘规则 | 进行概念依赖分析时 |
| [references/knowledge-framework-detail/framework-rubric.md](references/knowledge-framework-detail/framework-rubric.md) | 框架内容质量自评标准 | 评估框架质量时 |
| [references/knowledge-framework-detail/provenance-spec.md](references/knowledge-framework-detail/provenance-spec.md) | 节点级溯源数据模型与ngram匹配阈值 | 执行防幻觉溯源时 |
| [references/knowledge-framework-detail/prompt-templates.md](references/knowledge-framework-detail/prompt-templates.md) | 框架生成/重点节点/依赖挖掘的Prompt模板 | 需要生成框架内容时 |
| [references/knowledge-framework-detail/outline-parsing-heuristics.md](references/knowledge-framework-detail/outline-parsing-heuristics.md) | 7套材料解析启发式规则 | 解析不同格式资料时 |
| [references/knowledge-framework-detail/input-schema.md](references/knowledge-framework-detail/input-schema.md) | 完整输入JSON Schema | 需要结构化输入时 |
| [references/knowledge-framework-detail/output-schema.md](references/knowledge-framework-detail/output-schema.md) | 完整输出JSON Schema | 需要结构化输出时 |
| [references/knowledge-framework-detail/examples-index.md](references/knowledge-framework-detail/examples-index.md) | few-shot示例索引 | 需要参考示例时 |
| [references/knowledge-framework-detail/cli-usage.md](references/knowledge-framework-detail/cli-usage.md) | Python脚本的CLI调用示例与端到端流程 | 使用脚本工具时 |

### 脚本工具

| 脚本 | 功能 | 使用场景 |
|------|------|----------|
| [scripts/parse_outline.py](scripts/parse_outline.py) | 解析Markdown/DOCX/TXT/PDF等格式的资料大纲 | Phase 1 Step 2 材料解析 |
| [scripts/validate_input.py](scripts/validate_input.py) | 验证输入数据是否符合Schema | Phase 1 Step 1 输入校验 |
| [scripts/verify_provenance.py](scripts/verify_provenance.py) | 节点级溯源审计（ngram匹配） | Phase 1 Step 7 溯源审计 |
| [scripts/render_outputs.py](scripts/render_outputs.py) | 多格式渲染（Markdown/Mindmap/Mermaid/OPML） | Phase 1 Step 8 输出渲染 |
| [scripts/assemble_result.py](scripts/assemble_result.py) | 组装最终结构化结果 | Phase 1 最终汇总 |

### 模板资产

| 文件 | 内容 | 何时使用 |
|------|------|----------|
| [assets/report-template.html](assets/report-template.html) | 知识框架HTML报告模板（占位符替换式） | 生成交互式HTML报告时 |
| [assets/style.css](assets/style.css) | HTML报告/教材排版样式表（含主题色、字体、间距变量） | 生成HTML交付物时 |
| [references/mermaid-templates/](references/mermaid-templates/) | 6种Mermaid图表模板（流程图/甘特图/思维导图/时序图/状态图/时间线） | 需要生成图表时 |

### 教材质量参考库

| 文件 | 内容 | 何时读取 |
|------|------|----------|
| [references/textbook-quality/quality-check.md](references/textbook-quality/quality-check.md) | 质量评分权威标准（S/P/C/B四层） | Phase 5 质检时 |
| [references/textbook-quality/quality-s.md](references/textbook-quality/quality-s.md) | S层（结构层）规则权威 | 检查结构质量时 |
| [references/textbook-quality/quality-plc.md](references/textbook-quality/quality-plc.md) | P/C/B层规则权威 | 检查专业/表达/品牌质量时 |
| [references/textbook-quality/citation-format.md](references/textbook-quality/citation-format.md) | 引用格式规范 | 检查参考文献格式时 |
| [references/textbook-quality/cross-chapter-consistency.md](references/textbook-quality/cross-chapter-consistency.md) | 跨章节一致性检查规则 | 检查全书一致性时 |
| [references/textbook-quality/book-level-consistency.md](references/textbook-quality/book-level-consistency.md) | 全书级别一致性检查 | 终稿检查时 |
| [references/textbook-quality/genre-completion-checklist.md](references/textbook-quality/genre-completion-checklist.md) | 不同体裁的完成度检查清单 | 检查内容完整性时 |
| [references/textbook-quality/metrics.md](references/textbook-quality/metrics.md) | 质量度量指标 | 量化质量评估时 |
| [references/textbook-quality/writing-phase-alert-tiers.md](references/textbook-quality/writing-phase-alert-tiers.md) | 写作阶段告警分级 | 教材编制过程中 |

### 排版参考

| 文件 | 内容 | 何时读取 |
|------|------|----------|
| [references/textbook-typography/templates.md](references/textbook-typography/templates.md) | 排版模板规范 | 教材终稿排版时 |
| [references/textbook-typography/typography.md](references/textbook-typography/typography.md) | 字体与排版规则 | 教材终稿排版时 |

### 教材视觉与UX参考

| 文件 | 内容 | 何时读取 |
|------|------|----------|
| [references/textbook-visual/ux-design.md](references/textbook-visual/ux-design.md) | 对话层防卡顿规范、输出透明度规则、用户引导策略 | 教材编制过程中防卡顿、提升用户体验时 |
| [references/textbook-visual/visual-assets.md](references/textbook-visual/visual-assets.md) | 封面生成策略、插图/Mermaid视觉资产策略、三层路径（位图/SVG设计/SVG文字） | 需要生成教材封面或视觉资产时 |
| [references/textbook-visual/case-library.md](references/textbook-visual/case-library.md) | 案例库索引 | 需要查找教学案例时 |

### 教材交付与运维参考

| 文件 | 内容 | 何时读取 |
|------|------|----------|
| [references/textbook-ops/delivery-guide.md](references/textbook-ops/delivery-guide.md) | 从MD到多格式交付指南（D1完整HTML交付 / D2 Markdown终稿交付） | 教材终稿交付时 |
| [references/textbook-ops/large-scale-book-strategy.md](references/textbook-ops/large-scale-book-strategy.md) | 大规模教材应对策略（M1/M2/M3分级，超10万字处理） | 编制大型教材时 |
| [references/textbook-ops/s3-write-constraints.md](references/textbook-ops/s3-write-constraints.md) | 写作阶段写入约束规范 | 教材内容写入过程中 |
| [references/textbook-ops/anti-stall-guide.md](references/textbook-ops/anti-stall-guide.md) | 防卡顿执行指南 | 教材编制卡顿时 |
| [references/textbook-ops/retrospective-template.md](references/textbook-ops/retrospective-template.md) | 运行复盘报告模板 | 教材编制完成后复盘时 |
| [references/textbook-ops/quality-gates-brief.md](references/textbook-ops/quality-gates-brief.md) | 质量门禁简报（主题锁/VCR/国标） | 教材质检时 |

### 工作流治理参考

| 文件 | 内容 | 何时读取 |
|------|------|----------|
| [references/workflow-governance.md](references/workflow-governance.md) | 多智能体角色与写入边界、横向协同磁盘协议、会话恢复与上下文管理、长会话压缩策略、UX优化规范、信息优先级仲裁 | 多角色协作、跨会话恢复、长会话管理、提升用户体验时 |

### 反蒸馏参考（已移除）

> anti-distill 目录已删除——教学帮帮团无「防 AI 蒸馏抄袭」需求，且其「稀释成正确的废话」手法与全团去AI味门禁方向相反。技能核心知识的脱敏稀释如需，请自行引入独立工具；课程建设产出物（教案/教材/课件）的「AI 语言修改」统一由 `quality/deai-rules` 承担。
