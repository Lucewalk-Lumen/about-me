---
name: deep-research
version: 1.1.0
description: 学术论文原文级深度调研（Deep Research）能力模块。适用于：用户指定某篇论文要求"读透 + 追踪背景 + 扩展最新相关工作"，或用户给出某个学术 topic 要求系统性深度调研与写作综述。挂靠苏晚晴 paper-writing A2 选题 + 章节契约前置环节。触发词：deep research、深度调研、深度研究、读透论文、主题调研。
---

# Deep Research（论文原文级深度调研）

> **随本包维护**：报告以本地 Markdown 文件交付，在对话中告知路径，结果面板自动呈现。
> 配套包：`obhrm-research-collaboration-team`（位于 `skills/paper-writing/references/micro-skills/deep-research.md`）。
> 上游：可被 `skill:research-collector` Step 4 调研报告（元数据池）+ `skill:literature-review` 的 deep-distill 精读报告喂入；下游：报告生成后默认自动衔接苏晚晴 A2 选题 + 章节契约（主 Agent 询问一次是否衔接，可取消）。

---

## 1) Overview

### 适用场景

- **单篇论文级**：用户指定某篇论文要求"读透 + 追踪背景 + 扩展最新相关工作"
- **Topic 级**：用户给出某个学术 topic 要求系统性深度调研 + 写作综述

### 输出形式（本地交付）

- **主要产物**：本地 Markdown 报告文件（结果面板自动呈现）
- **报告路径**：`audit/paper-deepresearch/<topic-or-paper>-<YYYY-MM-DD>.md`
- **下游衔接**：报告生成后**默认自动衔接**苏晚晴 A2 选题 + 章节契约，传入 Topic 定义 + Primary paper 元数据 + Recent works 卡片；衔接前由主 Agent 询问一次是否衔接（可取消）

### 禁止行为

- [X] 调用任何第三方在线文档 SDK
- [X] 调用任何外部 subagent（如 `task` 工具的 `subagent_type: writer`）
- [X] 写入本机工作区之外的路径

---

## 2) 论文检索与证据构建（主 Agent 执行）

> 核心原则：**只要是"调研论文"，就必须拿到原文并阅读**；只要是"找相关论文"，就必须对每篇候选至少拿到原文并做结构化阅读记录。

### 2.1 Primary paper：定位原文 + 版本确认

1. **定位权威原文来源（按优先级）**
   - arXiv（preprint PDF）
   - 出版社页面（最终版本 / camera-ready）
   - 作者主页 / institutional repository
   - 语义学术索引（如 Semantic Scholar）用于交叉验证元数据与引用链

**WebSearch 查询示例**：
```
- "{论文标题} arxiv PDF"
- "{论文标题} {作者} {年份} conference"
- "DOI:{DOI编号}"
- "{arXivID} paper"
```

**WebFetch 获取原文**：
- URL: `https://arxiv.org/abs/XXXX.XXXXX`
- prompt: "获取该论文的完整元数据：标题、作者、摘要、版本号、提交日期、DOI"

2. **版本一致性检查**
   - 核对：标题、作者、年份、会议/期刊、版本号（arXiv v1/v2...）、DOI
   - 若存在多个版本：明确"以哪一版为主"，并记录差异（新增定理/实验/修订假设）

3. **原文获取失败的降级策略**
   - 若出版社付费墙：尝试 arXiv / 作者公开稿 / accepted version
   - 仍不可得：请求用户上传 PDF（此时停止"深度推导"，改做"可得信息范围内"的有限分析）

**写入本地草稿文件**（使用 `Write` 工具，路径 `audit/paper-deepresearch/draft_<任务标识>_<YYYYMMDD_HHMMSS>.md`）：
```markdown
## Primary Paper 元数据

- **标题**：...
- **作者**：...
- **会议/期刊**：...（年份）
- **arXiv ID**：...（版本 vX）
- **DOI**：...
- **原文来源**：arXiv / 出版社 / 作者主页
- **版本说明**：以 vX 为主，与 camera-ready 差异为...
```

### 2.2 Primary paper：通读与结构化笔记（必须）

对整篇原文做**结构化拆解**，每一项都要能回指到章节/公式编号（证据化）：

- **Problem Setup & Notation**
  - 随机变量/数据分布/样本：\(\xi \sim \mathbb{P}\)，\(\{\xi_i\}_{i=1}^n\)
  - 决策变量：\(x \in \mathcal{X}\)
  - 目标与风险/约束：\(\min_{x \in \mathcal{X}} \mathbb{E}_{\mathbb{P}}[\ell(x;\xi)]\)，或 \(\min f(x)\ \text{s.t.}\ g(x)\le 0\)
- **核心方法/算法**
  - 写出关键优化形式（primal/dual/regularized）
  - 给出算法迭代（如 SGD/PDHG/ADMM/镜像下降）的一般式
- **理论结果**
  - 定理/命题：条件（assumptions）→ 结论（rates/bounds/consistency）
  - 必须明确：依赖常数、光滑性/Lipschitz、强凸性、维度依赖、样本量依赖
- **实验与评估**
  - 数据集、指标、baselines、消融、统计显著性、复杂度与 wall-clock
- **局限性与讨论**
  - 论文自述限制 + 你识别到的隐含限制（假设过强、不可扩展、证据不足等）

> 输出一个"Primary paper evidence table"：Claim → Location（Section/Equation/Theorem）→ Notes（你对其含义/边界的解释）。

**使用 Read 工具解析论文 PDF**（多模态 Read 支持 PDF 文本提取 + 图片型 PDF 公式/定理识别），提取公式、定理、实验表格等关键内容。

**写入草稿文件**：
```markdown
## Primary Paper 结构化笔记

### Problem Setup & Notation
- 问题设定：...（Section X）
- 核心符号：...
- 目标函数：\(\min_{x \in \mathcal{X}} \mathbb{E}_{\mathbb{P}}[\ell(x;\xi)]\)（Eq. X）

### 核心方法/算法
- 关键优化形式：...（Section X）
- 算法迭代式：...（Algorithm X）

### 理论结果
- Theorem X：在假设 A1-A3 下，...（Section X）
- 收敛率：...
- 依赖条件：...

### 实验与评估
- 数据集：...
- 指标：...
- 主要结果：...（Table X / Figure X）

### 局限性与讨论
- 论文自述：...
- 识别到的隐含限制：...

### Evidence Table
| Claim | Location | Notes |
|-------|----------|-------|
| ... | Section X, Eq. Y | ... |
| ... | Theorem Z | ... |
```

### 2.3 Topic background：从"定义 → 范式 → 经典工作"建立脉络

当用户调研的是"论文"也要做 topic 背景（因为需要解释它解决的是什么问题）：

1. 统一定义：写出该 topic 的标准数学表述（至少 1--2 个 canonical forms）
2. 识别主流范式：优化/统计/学习/因果/控制等
3. 定位 3--8 篇奠基/综述/教材级引用，作为"背景锚点"
4. 提取该领域的常见难点与评价标准（例如：泛化、稳健性、可扩展性、可解释性、可复现性）

**WebSearch 查询示例**：
```
- "{topic} survey review tutorial"
- "{topic} canonical formulation mathematical framework"
- "{topic} seminal paper foundational work"
- "{topic} benchmark evaluation metrics"
```

**写入草稿文件**：
```markdown
## Topic Background

### 问题定义
- Canonical form 1：...
- Canonical form 2：...

### 主流范式
- ...

### 奠基工作（背景锚点）
| 论文 | 年份 | 核心贡献 | 与 primary paper 关系 |
|------|------|---------|---------------------|
| ... | ... | ... | ... |

### 领域难点与评价标准
- 泛化：...
- 稳健性：...
- 可扩展性：...
```

### 2.4 Recent related works：搜索"同 topic 最新论文"并原文阅读（必须）

> 用户要求：对**原文同个 topic 最近的相关论文**进行搜索原文并阅读整篇原文。

1. **检索范围建议**
   - 默认：近 24--36 个月（可按用户指定）
   - 目标：5--15 篇"强相关 + 有代表性"论文（宁缺毋滥）

2. **检索策略（组合拳）**
   - 关键词扩展：同义词、缩写、核心术语 + 方法名
   - 会议/期刊定向：该领域顶会顶刊（按 topic 确定）
   - 引用追踪：
     - backward：primary paper 引用的关键前置工作
     - forward：引用 primary paper 的近期论文（尤其最新）
   - 相关性判别：是否共享同一核心建模对象/理论命题/实验设置

**WebSearch 查询示例**：
```
- "{topic} {关键方法} 2024 2025 paper"
- "{primary paper 标题} cited by recent"
- "{topic} {顶会名} 2024 2025"
- "{核心术语} {同义词} new approach"
```

3. **对每篇 recent paper 的"最小原文阅读"标准**
   - 必须下载 PDF 并读：Abstract + Intro + Method + Main Theorem/Key Lemma + Experiments + Limitations/Discussion
   - 输出结构化卡片：
     - Problem / Method / Key result（公式级）/ Empirical setup / Relation to primary paper（替代、改进、互补、否定）

**写入草稿文件**：
```markdown
## Recent Related Works

### 检索策略与范围
- 时间窗口：近 XX 个月
- 检索渠道：arXiv, {顶会}, Semantic Scholar, Google Scholar
- 候选论文数：XX 篇，筛选后：XX 篇

### 结构化卡片

#### Paper R1：{标题}（{作者}, {年份}）
- **Problem**：...
- **Method**：...
- **Key result**：...（公式级）
- **Empirical setup**：...
- **Relation to primary paper**：替代/改进/互补/否定 — 具体说明...

#### Paper R2：{标题}（{作者}, {年份}）
- ...
```

### 2.5 质量控制（Search QA）

- 不允许只读二手解读（博客/短评）就下结论
- 对关键结论必须双重核对：原文公式/定理 + 实验设置
- 若出现矛盾（不同论文结论冲突）：记录冲突点（假设不同？数据不同？指标不同？实现差异？）

---

## 3) 写作规范与论证要求

> 写作总路线（用户要求）：**从 topic 入手 → 介绍 primary paper → 引到 recent papers → 论证关系**。

### 3.1 推荐报告结构（强制层次）

#### 0. TL;DR（不超过 10 行）
- 1--2 句 topic 定义 + 1 句 primary paper 的核心贡献 + 1--3 句近期进展与差异 + 1 句开放问题

#### 1. Topic：问题定义与统一符号（公式优先）
- 给出 canonical objective（示例）：
  \[
  \min_{x\in\mathcal X}\ \mathbb{E}_{\mathbb P}\big[\ell(x;\xi)\big]
  \quad\text{或}\quad
  \min_{x\in\mathcal X}\ f(x)\ \text{s.t.}\ g(x)\le 0
  \]
- 若为稳健/分布鲁棒/正则等主题，写出标准形式（示例）：
  \[
  \min_{x\in\mathcal X}\ \sup_{\mathbb Q\in\mathcal U}\ \mathbb E_{\mathbb Q}[\ell(x;\xi)]
  \]
- 明确：
  - \(\xi\) 的含义、样本如何来、\(\mathcal X\) 的结构
  - 常用假设（Lipschitz/convex/smooth/bounded support...）与其作用

#### 2. Primary paper 深度解构（以"模型--方法--定理--算法--实验"组织）
- **2.1 模型与关键构件**：把论文最核心的 1--3 个公式抄成统一符号体系，并解释每一项的作用
- **2.2 方法与推导主线**：给出从原问题到可解形式的"推导路线图"
  - 例如：primal → dual → regularization → tractable reformulation
- **2.3 理论结果（定理化呈现）**
  - 用"Assumption → Theorem → Interpretation"写法
  - 给出 proof sketch（只抓关键不等式/关键技巧），必要时写：
    \[
    \text{(key inequality)}\quad A \le B + C
    \]
- **2.4 算法细节**
  - 写出迭代更新式与复杂度（示例）：
    \[
    x^{t+1} = \Pi_{\mathcal X}\Big(x^t - \eta_t \nabla \hat f(x^t)\Big)
    \]
- **2.5 实验与结论可信度**
  - baseline 是否合理？指标是否匹配主张？是否有消融与统计检验？

#### 3. Recent related works：归类--对比--关系论证（必须体现"最近"）
- **3.1 归类框架（先给 taxonomy）**
  - 例：A 类（理论强化）、B 类（算法加速/可扩展）、C 类（放松假设/更一般场景）、D 类（应用/系统化）
- **3.2 对比表（强制）**
  - 维度建议：目标/假设/关键公式或界/算法复杂度/实验设置/相对 primary paper 的关系
- **3.3 关系论证（不是罗列）**
  - 用明确语义连接：
    - "该工作在 primary 的 Assumption X 上做了放松..."
    - "该工作把 primary 的目标 \(\ell\) 替换为 \(\tilde \ell\)，得到更强/更弱的界..."
    - "该工作在同一 benchmark 上显示...，但其优势来自...（更强的模型容量/更大的算力预算/不同预处理）"

#### 4. 综合结论与开放问题（研究导向）
- 你认为"已解决/基本共识"的部分是什么？
- 哪些是"理论空白/实验不足/工程不可落地"的部分？
- 给出 3--6 条明确可执行的后续研究问题（尽量写成数学问题或可验证命题）

#### 5. 附录（可选但推荐）
- 符号表（Notation table）
- BibTeX 列表
- 复现清单（数据、代码、超参、随机种子、算力、环境）

### 3.2 公式化写作规范（必须遵守）
- 每次引入符号必须定义（第一次出现就定义）
- 每个"关键结论"尽量落到可检查的对象：公式编号/定理编号/实验表格
- 避免空泛形容词（"很有效""很先进"），改为可验证表述（"在设置 S 下，相比 baseline 提升 X%/界从 \(O(1/\sqrt n)\) 改为 \(O(1/n)\)")

### 3.3 深度标准（反浅层检查）
若报告缺少以下任一项，则视为"浅层"，需要补齐：
- 至少 3 个关键公式（topic/primary/method 或 theorem）
- 至少 1 个推导路线（哪怕是 proof sketch）
- 至少 1 张系统对比表（primary vs recent）
- 至少 3 条"关系论证句"（说明为什么相关、改进在哪里、代价是什么）

---

## 4) 报告生成（本地交付）

### 执行流程

主 Agent 完成素材收集和分析后，**自行**按以下步骤生成报告（由主 Agent 自行完成）：

1. **Write**：将草稿文件写入 `audit/paper-deepresearch/draft_<任务标识>_<YYYYMMDD_HHMMSS>.md`
   - 包含：Primary paper 结构化笔记、Topic background、Recent works 结构化卡片、Evidence table
2. **报告大纲生成**：基于素材和文档模板（见 §5），生成结构化大纲
   - 大纲必须覆盖 3.1 中所有强制层次（TL;DR → Topic → Primary → Recent → Conclusion）
   - 每个章节标注预估字数
   - 确认公式数量、对比表数量、定理数量
3. **Write 写盘**：根据大纲逐章生成完整 Markdown 报告
   - 报告路径：`audit/paper-deepresearch/<论文标题或 Topic>-<YYYY-MM-DD>.md`
   - LaTeX 公式使用 `$...$`（行内）和 `$$...$$`（独立）
   - 对比表使用 Markdown 原生表格
   - 核心定理使用 Assumption → Theorem → Interpretation 格式
4. **路径告知**：在对话中告知用户报告文件路径（WorkBuddy 结果面板会自动呈现生成的交付文件）
5. **（默认自动衔接，可取消）** 报告生成后由主 Agent 询问一次是否衔接；确认后调用苏晚晴 A2 选题 + 章节契约子模块，传入 Topic 定义 + Primary paper 元数据 + Recent works 卡片

### 后续研究任务（可选）

报告生成后，**询问用户**是否需要将"综合结论与开放问题"章节中的 3-6 条后续研究问题转化为本地待办列表：

```
主 Agent 询问用户：
"报告中识别了以下后续研究方向，是否需要创建待办任务？
1. 调研开放问题1：{具体问题描述}
2. 复现 primary paper 实验
3. 精读 Paper R2 的方法细节"

用户确认后：
- 在对话中输出待办列表（**不**调用任何外部待办 SDK）
- 用户可手动复制到自己的任务管理工具
```
- [X] 取消"通知相关人员"环节

---

## 5) 文档模板

```markdown
# {论文标题 / Topic} 深度解读报告

> 调研范围：{topic 关键词} | 时间窗口：近 {N} 个月
> Primary paper：{标题}（{作者}, {会议/期刊}, {年份}）
> 生成时间：YYYY-MM-DD

---

## TL;DR

{1–2 句 topic 定义}。{1 句 primary paper 的核心贡献}。{1–3 句近期进展与差异}。{1 句开放问题}。

---

## 1. Topic：问题定义与统一符号

### 1.1 问题定义
- Canonical objective：
  \[
  \min_{x\in\mathcal X}\ \mathbb{E}_{\mathbb P}\big[\ell(x;\xi)\big]
  \]
- 符号说明：\(\xi\) 表示...，\(\mathcal X\) 表示...，\(\ell\) 表示...

### 1.2 主流范式与假设
- 范式 A：...
- 范式 B：...
- 常用假设：Lipschitz / convex / smooth / bounded support...

### 1.3 奠基工作（背景锚点）

| 论文 | 年份 | 核心贡献 |
|------|------|---------|
| {经典工作1} | YYYY | ... |
| {经典工作2} | YYYY | ... |
| {经典工作3} | YYYY | ... |

---

## 2. Primary Paper 深度解构

### 2.1 模型与关键构件
- 核心公式 1：（Eq. X）
  \[
  ...
  \]
  解释：每一项的作用...

### 2.2 方法与推导主线
- 推导路线图：primal → dual → regularization → tractable reformulation
- 关键步骤说明：...

### 2.3 理论结果
> **Assumption A1**：...
> **Theorem 1**（{论文} Theorem X）：在 A1–A3 下，...
> **Interpretation**：该定理表明...

- Proof sketch：
  1. ...
  2. Key inequality：\(A \le B + C\)
  3. ...

### 2.4 算法细节
- 迭代更新式：
  \[
  x^{t+1} = \Pi_{\mathcal X}\Big(x^t - \eta_t \nabla \hat f(x^t)\Big)
  \]
- 复杂度：\(O(...)\)

### 2.5 实验与结论可信度

| 维度 | 评估 |
|------|------|
| Baseline 合理性 | ... |
| 指标匹配度 | ... |
| 消融实验 | 有/无 |
| 统计检验 | 有/无 |

- 主要实验结论：...

---

## 3. Recent Related Works

### 3.1 归类框架（Taxonomy）
- A 类（理论强化）：...
- B 类（算法加速/可扩展）：...
- C 类（放松假设/更一般场景）：...
- D 类（应用/系统化）：...

### 3.2 系统对比表

| 论文 | 类别 | 目标/假设 | 关键公式或界 | 算法复杂度 | 实验设置 | 相对 Primary 的关系 |
|------|------|---------|-------------|-----------|---------|-------------------|
| Paper R1 | A | ... | ... | ... | ... | 改进了假设 X |
| Paper R2 | B | ... | ... | ... | ... | 加速了算法至... |
| Paper R3 | C | ... | ... | ... | ... | 放松了条件... |
| ... | ... | ... | ... | ... | ... | ... |

### 3.3 关系论证
- Paper R1 vs Primary：...
- Paper R2 vs Primary：...
- Paper R3 vs Primary：...

---

## 4. 综合结论与开放问题

### 已解决/基本共识
- ...

### 理论空白/实验不足/工程不可落地
- ...

### 后续研究问题（3–6 条）
1. （数学问题/可验证命题）...
2. ...
3. ...

---

## 附录

### A. 符号表（Notation Table）

| 符号 | 含义 |
|------|------|
| \(\xi\) | ... |
| \(x\) | ... |
| \(\mathcal X\) | ... |

### B. BibTeX 列表
{BibTeX 条目}

### C. 复现清单
- 数据集：...
- 代码：...
- 超参数：...
- 随机种子：...
- 算力：...
- 环境：...
```

---

## 6) 苏晚晴 A2 选题 + 章节契约 衔接钩子

> 报告生成后**默认自动衔接**苏晚晴 paper-writing 的 A2 选题 + 章节契约环节（衔接前由主 Agent 询问一次是否衔接，可取消）

| 本 micro-skill 字段 | 苏晚晴 A2 选题 + 章节契约 字段 | 说明 |
|---|---|---|
| Topic 定义 | A2 选题范围 | 收敛的研究问题 |
| Primary paper 元数据 | A2 primary citation | 主文献引用 |
| Recent works 卡片 | 章节契约-相关工作输入（支撑 A2 文献链） | 文献综述章节输入 |
| 开放问题列表 | A2 选题 GAP 候选项 | 后续研究候选 |
| 公式化符号表 | 章节契约-符号约定 | 全文统一符号 |

**调用方式**：
- 报告生成后**默认自动衔接**苏晚晴 paper-writing 的 A2 选题 + 章节契约子模块（`skill:paper-writing` 中 A2 选题与章节契约段落）
- 章节契约模板见 `skill:obhrm-methodology/references/templates/section-contract-template.md`（A1 确认后、A2 前为全部章节起草契约）
- 衔接前由主 Agent 向用户询问一次是否衔接（可取消）；用户选择"否"则仅保留本地报告，不做衔接

---

## 7) 质量检查清单

### 主 Agent — 检索质量检查
- [ ] Primary paper 原文 PDF 已获取并通读（含 method + main results + experiments）
- [ ] Primary paper 结构化卡片 + Evidence Table 已完成
- [ ] Topic 的 canonical form 与关键术语已统一
- [ ] 奠基/综述工作已定位（3--8 篇），背景脉络已建立
- [ ] 近 2--3 年 strong-related 论文已找到并逐篇原文阅读（至少核心章节）
- [ ] 每篇 recent paper 输出了结构化卡片（Problem/Method/Key result/Relation）
- [ ] 引用链（forward/backward）完成，矛盾点已记录
- [ ] 所有论文引用包含：作者、标题、会议/期刊、年份
- [ ] 草稿文件内容完整，可直接生成报告

### 主 Agent — 写作质量检查
- [ ] 结构符合：TL;DR → Topic → Primary → Recent → Relation → Conclusion
- [ ] 关键公式/定理/迭代式齐全且符号一致（至少 3 个关键公式）
- [ ] 至少 1 个推导路线（proof sketch）
- [ ] 对比表完成（至少 1 张，维度统一）
- [ ] 关系论证充分（至少 3 条，非罗列）
- [ ] 局限性与开放问题具体可执行（3--6 条后续研究问题）
- [ ] 避免空泛形容词，所有结论可验证

### 报告生成检查
- [ ] TL;DR 完整且不超过 10 行
- [ ] 报告结构严格遵循文档模板
- [ ] LaTeX 公式格式正确，行内/独立公式区分清晰（`$...$` / `$$...$$`）
- [ ] 对比表维度统一、横向可比
- [ ] 核心定理使用 Assumption → Theorem → Interpretation 格式
- [ ] 所有引用标注来源
- [ ] 已成功生成本地 Markdown 报告文件并在对话中告知路径
- [ ] 已询问用户是否创建后续研究待办任务

---

## 8) 常见问题排查

| 失败模式 | 典型表现 | 根因分析 | 修复方法 |
|---------|---------|---------|---------|
| 只看摘要/博客 | 报告缺少公式和定理细节，结论空泛 | 未获取原文 PDF 或未通读 | 立即回到原文，补齐 method/assumption/theorem/experiment 的证据链；使用 Read 工具多模态解析全文 |
| 相关工作堆砌 | 列出 10+ 篇论文但无分类、无对比、无关系论证 | 未做 taxonomy，直接罗列 | 必须先给 taxonomy，再用对比表与关系论证串起来；每篇必须说明与 primary paper 的关系 |
| 公式堆砌无解释 | 贴了大量公式但读者无法理解含义 | 缺少符号定义和直觉解释 | 每个公式都要解释"每一项是什么、为什么这样建、它带来什么性质"；首次引入符号必须定义 |
| 忽略假设边界 | 定理结论写了但未交代成立条件 | 跳过 assumptions 直接写结论 | 把所有定理的关键假设列出来，并讨论能否放松/代价是什么；使用 Assumption → Theorem → Interpretation 格式 |
| 符号不一致 | 不同章节用不同符号表示同一概念 | 未在开头建立统一符号体系 | Topic 章节必须建立统一符号表，后续所有章节严格遵循；附录提供 Notation Table |
| 深度不足 | 报告看起来像"摘要集合"，无推导、无 proof sketch | 未执行 3.3 深度标准检查 | 对照 3.3 四项标准逐一检查：公式>=3、推导路线>=1、对比表>=1、关系论证>=3 |
| 时间窗口失焦 | Recent works 包含 5 年前的论文，不够"recent" | 检索时未限定时间范围 | 严格执行 2.4 中的时间窗口（默认 24--36 个月），超出范围的论文仅在 Topic background 中引用 |
| 版本混淆 | 引用的定理/实验结果与原文不一致 | 引用了 arXiv 旧版本而非 camera-ready | 2.1 阶段必须核对版本一致性，明确以哪一版为主，记录版本差异 |

---
