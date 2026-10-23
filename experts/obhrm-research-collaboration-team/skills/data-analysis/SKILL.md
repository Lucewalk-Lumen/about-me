---
name: data-analysis
version: 1.0.0
author: "Xing Bu"
description: OBHRM 研究协作团 — 数据分析域（③ 段）。按证据形态分定量·一手（D1-D4）、定量·二手（元分析 M1-M5）、定性·质性（扎根理论 Q1-Q5）三大分支，回答"研究结论怎么证明成立"。
---
> **跨技能引用约定**：本文档以逻辑名形式引用兄弟技能（如 `` `skill:peer-review` ``），不使用逻辑名映射表，重命名或移动技能时按相对路径同步更新。
# 数据分析域 — 怎么证明研究结论成立
数据分析域是套件生命周期第 ③ 段「怎么证明结论成立」的承载域。它把回答"研究结论站不站得住"的多种证据路线收拢在同一父域下，按**证据形态**分为定量 / 定性两大类、三个子分支：
- **定量·一手**：对研究者自己采集的一手调研数据（问卷 / 实验 / 纵向追踪）做从清洗到报告的完整分析。入口：`quantitative/quantitative.md`（D1–D4）。
- **定量·二手**：对已发表研究的效应量做系统聚合。入口：`quantitative/quantitative.md`（第二部分 M1-M5）。
- **定性·质性**：与定量（一手 / 二手）并列，同属数据分析域、共同回答"怎么证明结论成立"。以扎根理论为核心方法，覆盖三大学派（经典 Glaser / 程序化 Strauss / 建构 Charmaz），处理访谈 / 扎根理论 / 案例类**文字证据**。入口：`qualitative/qualitative.md`（Q1–Q5 完整阶段：研究问题与抽样 → 数据收集 → 三级编码 → 理论饱和与持续比较 → 撰写质性研究报告）。方法学依据见 `quantitative/references/methods-knowledge.md` §2.12（王璐/高鹏 2010 + 贾旭东/衡量 2020；该文件现为路由枢纽，§2.12 专节保留于此），配套模板见 `skills/obhrm-methodology/paper-templates/case_study_template.md`。（方法知识唯一正源已统一为 `quantitative/references/r-language-data-analysis-manual.md` 及其按章分布的 19 方法族）
---

## D0 分级试跑（Reality Gate · 三分支共用的强制前置子步骤）

> **强制性**：本步骤是数据分析域**任何分支**（定量·一手 D1–D4、定量·二手 M1–M5、定性·质性 Q1–Q5）在进入正式分析前的**第一个子步骤**。未完成试跑并确认通道走通，不得对全量数据执行分析，也不得产出任何用于成稿的统计结果或编码结论。

### 一、为什么先跑小样

全量分析上的失败，多数不是统计问题而是**通道问题**：编码格式错乱、缺失值标记不统一、反向计分未处理、变量名与量表对不上、文件编码导致中文乱码、分组变量取值超出预期。这类问题在全量运行时往往以"结果看起来算出来了"的形式蒙混过去，直到写作阶段才暴露，返工成本极高。先用小样把通道走通，是把失败提前到最便宜的时刻。

### 二、试跑规格

| 项目 | 要求 |
|------|------|
| **样本规模** | 抽取 50–100 行；质性分支取 2–3 份访谈稿或等量文本片段。数据总量不足 100 行时全量即为试跑，但仍须走完下方全部检查项 |
| **抽样方式** | 优先随机抽取；含分组 / 分层设计时按组各抽若干，确保每个关键取值至少出现一次。**不得只取前 50 行**——前段数据常带录入规律偏差，掩盖后段问题 |
| **执行内容** | 走完与全量分析**完全相同**的处理链路：读取 → 清洗 → 变量构造 → 反向计分 → 信度或编码 → 一个最简版的目标分析（如单个回归、单次开放编码） |
| **产出** | 试跑小结：样本行数、字段清单、每步是否通过、发现的问题与已修正项 |

### 三、试跑必查项（逐条给结论，不得跳过）

1. **读得进**：文件可正常读取，中文无乱码，行列数与预期一致。
2. **认得准**：变量名与量表或编码手册逐一对应，无张冠李戴。
3. **值域对**：各变量取值落在应有范围内（如 5 点量表不应出现 0 或 6），异常值有解释。
4. **缺失清**：缺失值标记方式统一（空白 / 99 / NA 不得混用），缺失比例已知。
5. **反向计分已处理**：需反向的题目确实已反过来，用一两条记录手工核对。
6. **分组对得上**：分组或分层变量的取值与实验设计、抽样框一致，无多余组别。
7. **最简分析跑得通**：目标分析的最小版本能出结果，输出格式符合统计报告规范。

### 四、闸门判定

- **全部通过** → 记录试跑小结，进入对应分支的正式阶段（D1 / M1 / Q1）；全量分析沿用试跑中已确认的处理链路，不另起一套。
- **任一项不通过** → 停在 D0：定位原因、修正处理链路、**重新抽样再跑一次**，直至全部通过。修正内容写入试跑小结，作为方法部分"数据清洗"描述的原始依据。
- **数据本身有硬伤**（关键变量整列缺失、量表题目不全、样本与研究设计不匹配等）→ 不进入正式分析，向用户如实报告问题与可选方案（补采数据 / 调整分析策略 / 缩减假设范围），不得用统计手段掩盖数据缺陷。

> **与稳健性检查的分工**：D0 试跑回答"这条分析通道走不走得通"，稳健性检查回答"这个结论稳不稳"（见 `references/robustness-matrix.md`）。两者都要做，不可互相替代。

---

## 统计数字防编造规则（本域强制 · 与四铁律同源）

> **强制性**：本域是套件中**唯一产出统计数字**的域。本规则对定量·一手（D1–D4）、定量·二手（M1–M5）、定性·质性（Q1–Q5）三个分支**同等适用**，效力高于任何产出格式要求。

本包**不内置统计计算引擎**，也不代用户运行 R / SPSS / Python 统计环境：分析结果必须由用户在本机实际运行后回传。因此：

1. **禁止估算或编造任何统计量**。包括但不限于：均值/标准差、相关系数、回归系数与标准误、t/F/χ² 值、p 值、置信区间、Cohen's d、η²、Cramér's V、VIF、ΔR²、Bootstrap CI、信效度指标（α/CR/AVE）、拟合指数（CFI/TLI/RMSEA/SRMR）、效应量与异质性指标（I²、τ²）、编码频次与饱和度判断。这些数值只能来自**实际运行的输出**，不得依据"典型值""经验判断""大致应该"填写。

2. **无真实计算结果时，必须显式标注**。写成「未计算 — 需在实际统计环境中运行」并给出对应的 R 脚本编号（从 `../r-analysis/scripts/` 的 108 个脚本中指定，含 `method_no`），或给出 SPSS / Mplus 等可执行路径说明。**不得填入任何占位数值**（含 `0.00`、`—`、`N/A`、`待填` 之外的伪装数值），也不得用"显著""中等效应""影响较大"等定性描述替代缺失的真实数值来暗示已算出结果。

3. **引述的统计量必须可追溯到实际运行的输出**。每条数值须能指明来源：用户回传的运行日志/结果文件、用户提供的已发表文献原文，或用户明确给出的已有分析结果。无法指明来源的数值一律不得写入交付物。

4. **D0 试跑的"最简分析跑得通"由用户执行**。本包负责交付方法选型、可运行的脚本与报告框架；"跑通"这一步由用户在本机运行后回传结果，包不代跑、不假设结果。用户未回传结果前，交付物中**不得出现任何统计数值**。

5. **与四铁律的关系**：本规则是四铁律（不编引用 / 不归观点 / 标注无支撑 / 不超范围）在本域的落点——编造统计量等价于编造引用，同属 P0 级学术诚信问题，发现即阻断交付。质性分支同理：不得编造受访者语句、编码条目或理论饱和度结论。

---

## 统计计算辅助（stat_helpers.py）与外部引擎对接

本域不内置统计引擎、不代跑分析（见上「统计数字防编造规则」）。但在**用户已用真实数据跑出真实数值**后，常需轻量换算 / 汇总（如由实测均值标准差求 Cohen's d、由真实 R² 求 ΔR²、由真实作答矩阵求 Cronbach's α）。为此提供两类"计算器/取数器"，二者都不产生任何编造数字。

### 一、stat_helpers.py —— 真实数据上的轻量换算

位置：`skills/data-analysis/scripts/stat_helpers.py`。**只计算、不编造**：每个函数都要求调用方传入真实观测数据或真实运行得到的统计量；缺输入一律报错，绝不回退到 0.00 / 经验值 / 典型值。它是"计算器"，不是"数据来源"。

> 依赖：需 numpy（`pip install numpy scipy`）；缺失时给出明确报错，提示改用下方 R 脚本路径。

提供函数：

| 函数 | 用途 | 关键参数（均须真实） |
|------|------|----------------------|
| `cohen_d(g1, g2)` | 两组独立样本 Cohen's d（或 Glass's Δ） | 两组真实观测向量 |
| `eta_squared(*groups)` | 单因素 ANOVA 的 η²（效应量） | 各组真实观测向量 |
| `cramers_v(table)` | 列联表 Cramer's V | 二维真实列联表 |
| `vif(design)` | 设计矩阵各列 VIF（>5 提示多重共线性） | 真实设计矩阵（**去掉截距列**，常数列 VIF 为 inf） |
| `delta_r2(r2_full, r2_reduced)` | ΔR² | 两个真实 R² |
| `bootstrap_ci(data, fn, n, α, seed)` | Bootstrap (1-α) 置信区间 | 真实一维数据 + 统计量函数 |
| `cronbach_alpha(matrix)` | Cronbach's α（成对删除缺失） | 真实被试×题项矩阵 |

CLI 示例：

```bash
# 由真实观测求 Cohen's d
python3 skills/data-analysis/scripts/stat_helpers.py cohen_d \
  --g1 3.2,1.1,2.9,3.0,2.8 --g2 2.8,0.9,3.1,2.5,2.2

# 由真实作答 CSV 求 Cronbach's α
python3 skills/data-analysis/scripts/stat_helpers.py cronbach --csv responses.csv

# 由真实列联表求 Cramer's V
python3 skills/data-analysis/scripts/stat_helpers.py cramers_v --table 30,10 20,40
```

### 二、R 脚本对接（主分析路径）

真正的建模 / 检验请走 `skill:r-analysis` 的 108 个已检验 R 脚本：

1. 在 `quantitative/quantitative.md` 的「方法族→D 阶段映射」或 `quantitative/references/methods-knowledge.md` 确定 `method_no`（如 10.1.R = PLS-SEM、14.1.R = APIM、18.1.R = SNA）。
2. 用 `skills/r-analysis/scripts/query_r.py` 按 `method_no` 取可执行脚本路径（权威映射见 `skills/r-analysis/knowledge/_r_index.json`，**勿凭目录号臆测**）：
   ```bash
   python3 skills/r-analysis/scripts/query_r.py 10.1
   ```
3. **用户**把自有数据按脚本要求整理后，在本机 R 环境运行，回传真实输出（系数 / 拟合指数 / 效应量 / 显著性）。
4. 若只需轻量换算（见上），用 `stat_helpers.py` 在真实输出上二次计算。

### 三、回填到交付物

所有真实数值回填时遵守「统计数字防编造规则」第 2、3 条：

- 数值后标注来源（R 运行日志 / 已发表文献 / 用户回传结果），例如「RMSEA = 0.06（R 脚本 10.1.R 输出，2026-09-10 运行）」。
- 凡未经真实计算者，写「未计算 — 需在实际统计环境中运行（脚本编号：…）」，**不得填占位数值**。
- 质性分支同理：编码条目 / 饱和度结论须来自真实编码过程，不得编造。

---

## 方法参考（本域 references/）

- `references/causal-identification.md`：因果识别策略选择决策树（DID / IV / RD / 事件研究），OBHRM 语境下的适用条件、识别假设与常见证伪方式。
- `references/robustness-matrix.md`：稳健性检验矩阵（替换变量 / 安慰剂检验 / 子样本 / 聚类标准误 等），按中文期刊审稿期待编排优先级。
- `references/three-line-table.md`：中文刊三线表规范（表题、栏目结构、数字格式、显著性标记、注释行写法）。

---

## 跨域联动

- **A4 → D1–D4 → A5**（论文方法与数据分析的链路）→ `skill:paper-writing`；完成 D4 后回到 论文路径续写关卡2。
- **论文/综述 → 定量·二手（元分析）**（系统综述/元分析主导）→ `quantitative/quantitative.md`（第二部分 M1-M5）；元分析分支作为综述路径系统综述子集。
- **定量/定性 → 审稿反向诊断**（分析结果送 审稿路径诊断时）→ `skill:peer-review`（量化稿件走默认版，质性稿件走 `path_type="C-qualitative"` 版）。
- **图表需求**（定量/定性全程）→ `skills/obhrm-methodology/domains/visualization/visualization.md`，按「图表嵌入协议」入正文。
- **成稿后的风格级去AI** → `skills/obhrm-methodology/domains/humanize/humanize.md`（后置步骤）。
- **方法层**：`skills/obhrm-methodology/references/methods/theory_method.md`（含质性研究论文）、`skills/obhrm-methodology/references/review/quality_rubric.md`、`skills/obhrm-methodology/references/templates/quality_checklist.md`、`skills/obhrm-methodology/references/methods/statistical_report_standard.md`、`skills/obhrm-methodology/references/methods/statistical_figure_standard.md`、`skills/obhrm-methodology/references/methods/systematic_review_toolkit.md`、`skills/obhrm-methodology/references/templates/handoff-protocol.md`（跨路径字段级规格）、`skills/obhrm-methodology/paper-templates/case_study_template.md`（质性研究模板）、`quantitative/references/methods-knowledge.md` §2.12（质性方法学真源；该文件现为路由枢纽，专节保留于此）。

- **R 实现（定量路径）→ `skill:r-analysis`**：本域判定方法族（D1–D4 定量一手 / M1–M5 元分析 / Q1–Q5 质性）后，按 `method_no` 经 r-analysis 的 `query_r.py` 取可运行脚本；`method_no`↔脚本文件的权威映射见 r-analysis 的 `../r-analysis/knowledge/_r_index.json`（须以该 JSON 为准，勿凭目录号臆测）。脚本须用户传入自有数据并按 G3 门控运行。
  - **方法族闭环**：PLS-SEM（10.1.R / `seminr`）、APIM（14.1.R / `lme4`）、SNA（18.1.R / `igraph`，文件 `../r-analysis/scripts/18-sna/18.1.R`）等脚本已补齐，**19 个方法族均已有 `_r_index.json` 节点与已检验脚本**，不再存在定量方法族缺口。方法知识的唯一正源已统一为 `quantitative/references/r-language-data-analysis-manual.md`（20 章、68 方法、108 脚本节点已全部按章分布：PLS-SEM→§10.1 / 缺失数据→§2.3.4 / 检验力→§3.2 / SNA→§18.1 / APIM→§14.1 / 混合方法→§20）；`methods-knowledge.md` 降级为路由枢纽（保留 §2.12 扎根理论专节）。

## 协作交接

本父域是定量（一手/二手）/ 定性三个子分支的总入口与路由；具体交接字段见各子域文档与 `skills/obhrm-methodology/references/templates/handoff-protocol.md` 链路一/二/三/四/六/七/九/十。

- **论文→定量一手 委托分析 / 定量一手→论文 结果回传**：字段见链路一/二。
- **论文→定量二手（综述主导）/ 写作→审稿**：字段见链路三/七。
- **论文→定性 质性分析 / 定性→论文 回传**：同属 论文路径研究分析延伸，见各子域文档。
- **定量/定性→蒸馏**（浮现可复用教训）：字段见链路六；判层后落点 `skills/obhrm-methodology/references/governance/method_accumulation.md`（方法论层）或对应 reference（操作层）。
- **定量二手（元分析）→论文/基金 结果回传**：字段见链路九。
- **定量一手→定量二手 桥接**：字段见链路十。

> 父域本身不直接消费/产出交接块；其下属分支各自执行交接。

## 域内路由

| 用户要做什么（或上传什么文件） | 进入 | 说明 |
|------|------|------|
| 原始数据分析（t 检验 / ANOVA / 回归 / 调节中介）；**上传数字型数据文件（CSV 等；Excel/SPSS 格式可由 R 读取导入）** | `quantitative/quantitative.md` | **定量·一手**，D1–D4 |
| 元分析 / meta 分析 / 系统综述 / PRISMA；**上传效应量数据文件** | `quantitative/quantitative.md` | **定量·二手**，效应量聚合，M1–M5 |
| 质性研究 / 扎根理论 / 案例 / 访谈编码；**上传访谈稿/田野笔记/文字转录稿** | `qualitative/qualitative.md` | **定性**，三大学派（经典/程序/建构），Q1–Q5 完整阶段 |

> **定量 / 定性不混用**：数字型数据（CSV 等；Excel 可由 R 读取导入，量表得分）→ 定量分支（一手 D 或二手 M）；文字型数据（访谈稿/田野笔记/开放题文本）→ 定性分支（质性 Q）。三者同属数据分析域的子分支，回答"怎么证明结论成立"的 3 条不同证据路线，方法族互不混用。
