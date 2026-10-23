# 数据分析域·定量分析（一手 D + 二手元分析 M）

定量分析统一入口，按数据形态自动分流：数字型一手数据 → D1-D4；效应量二手数据 → M1-M5。如从论文路径进入，完成分析后返回 `../../paper-writing/SKILL.md` 继续。

---

# 第一部分：定量一手（D1-D4 原始数据分析）

定量一手分支对研究者自采的一手数字型数据（问卷/实验/纵向追踪）进行从清洗到报告的完整分析。

## 路径概览

| 阶段 | 产出 |
|------|------|
| D1 数据清洗与准备 | 清洗后数据集、缺失值报告、变量转换说明 |
| D2 描述统计与可视化 | 均值/SD表、相关矩阵、图表（条形/箱线/热图/雷达） |
| [注意] D2 图表 → 读取 `skills/obhrm-methodology/domains/visualization/visualization.md` |
| D3 假设检验 | t检验/ANOVA/卡方结果表、效应量（Cohen's d/η²） |
| D4 回归分析与报告 | 回归系数表（含标准化β/SE/t/p）、模型拟合（R²/ΔR²） |
| [注意] D4 图表 → 读取 `skills/obhrm-methodology/domains/visualization/visualization.md`（散点图/条形图+误差） |

## 阶段执行规范

### D1 数据清洗
- 缺失值：报告缺失率 > 5% 的变量，选择删除/插补方法
- 异常值：±3SD 外标记，说明处理方式
- 正态性：报告偏度/峰度，非正态变量选择转换方法
- 共同方法偏差：报告 Harman 单因子检验结果

### D2 描述统计
- 输出 APA 格式表格：变量/均值/SD/1/2/3...（含相关系数）
- 标注 *p<.05 **p<.01 ***p<.001
- 图表调用见 `skills/obhrm-methodology/domains/visualization/visualization.md`

### D3 假设检验
- 分组比较：先报告 Levene 方差齐性检验
- 效应量必报：Cohen's d（t检验）、η²（ANOVA）、Cramer's V（卡方）
- 多重比较：Bonferroni 或 Holm 校正

### D4 回归分析
- 逐层进入，报告 ΔR² 和 F change
- VIF < 5 确认无多重共线性
- 报告非标准化 B + 标准化 β + SE + t + p + CI
- 中介/调节效应：报告间接效应 Bootstrap CI

## 图表需求

D2 箱线图/热图/雷达图、D3 条形图+误差、D4 散点图+回归线 — 全部调用 `skills/obhrm-methodology/domains/visualization/visualization.md`

> **即时登记**：D2-D4 每生成一张图，立刻登记到「图表登记表」（图N/类型/归属 A5 子节/文件），供 A5 收尾逐图核对，避免遗漏。

## 方法族→D 阶段映射

> 本节是数据路径的"方法族路由表"。完整方法文献索引见 `references/methods-knowledge.md`（按 19 个方法族（见 `references/methods-knowledge.md` §1）× 阶段双维组织；本表是入口，本索引是真源）。

| D 阶段 | 优先方法族 | 何时启用 | 关联索引族 |
|------|---------|---------|---------|
| **D1 数据清洗** | 缺失数据（ML/MI） | 缺失率 > 5% 或非常规问卷结构 | §2.13 |
| **D1-D2 之间** | 问卷前传 + 测量评价 | 任何问卷数据 D1 后必做 | §2.2 + §2.13 |
| **D2 描述统计** | 曲线效应（D2 末段决定走曲线/线性） | 见分布与散点图初判 | §2.8 |
| **D3 测量模型** | CFA / EFA / ESEM / 多层 EFA | 量表未定型 / 数据嵌套 | §2.2 |
| **D3 假设检验** | SEM 总体 / 多层 SEM 中介 / 跨滞后 / DSEM / 双过程 | 假设需要潜变量/嵌套/纵向 | §2.1 + §2.3 + §2.4 |
| **D3 检验力** | SEM 检验力（样本量决策） | 任何 SEM 起手前 | §2.14 |
| **D3 PLS 路径** | PLS-SEM 基础 + AIC 模型选择 | 探索性 / 小样本 / 非正态 / 多模型比较 | §2.10 |
| **D4 中介** | 多重中介 / SEM 多重中介 / 多层 SEM 中介 | 假设涉及机制传导 | §2.6 + §2.3 |
| **D4 调节** | 多元回归调节 + 简单斜率（J-N / 选点法） | 假设涉及边界条件 | §2.7 |
| **D4 响应面** | 多项式回归 / 响应面 / 匹配研究 | 假设涉及一致/不一致或 P-E fit | §2.7 |
| **D4 非线性** | 曲线效应（过犹不及 / 居中不良） | 倒U/曲线/非线性假设 | §2.8 |
| **D4 因果推断** | CLPM 批判 / RI-CLPM / DSEM / 双过程理论 | 纵向设计 | §2.4 |
| **D4 多层结构** | 多层 EFA + 多层 SEM | 团队/嵌套/多层数据 | §2.2 + §2.3 |
| **D4 复杂因果** | QCA / 组态（静态 + 动态） | 样本小 + 构型因果 + 充分/必要 | §2.11 |
| **D4 人中心** | LPA / 多层 LPA / PLS-LCA | 以人为中心（补充以变量为中心） | §2.5 + §2.2 |
| **D→M 顶层路径** | 元分析作为多层模型（**元分析路径核心**） | 单研究证据不足 → 切下方 M1-M5 | §2.9 |
| **D-qualitative 工作流** | 扎根理论入门 + 学派选择 | 量化饱和后补质性 | §2.12 |

> **加载纪律**：三步顺序不可颠倒——**先看本表定方法族 → 查 `methods-knowledge.md` 锁定具体文献 → 走下节「检验决策树」定统计量**。
>
> **不重复造方法学**：本表与 `methods-knowledge.md` 只解决"用哪种方法、查哪一篇"；具体公式、判定阈值、APA 报告模板仍以 `skills/obhrm-methodology/references/methods/statistical_report_standard.md` + `statistical_figure_standard.md` 为执行依据。

## 检验决策树与前提检查

### 何时用何检验

| 研究问题 | 数据形态 | 推荐检验 | 必报统计量 |
|---------|---------|---------|-----------|
| 两组均值比较 | 连续、独立、近似正态 | 独立样本 t 检验 | t, df, p, Cohen's d, 95%CI |
| 配对 / 前后测 | 连续、配对 | 配对 t 检验 | t, p, d |
| ≥3 组均值比较 | 连续、独立、近似正态 | 单因素 ANOVA + 事后(Bonferroni/Holm) | F, η², 事后 p |
| 两类别关联 | 名义 | 卡方独立性检验 | χ², Cramer's V |
| 预测 / 解释变异 | 连续因变量 | 分层回归 | β, SE, t, p, R², ΔR² |
| 中介机制 | 连续 | Bootstrap 中介(5000 次) | 间接效应, BCa CI |
| 调节边界 | 连续调节变量 | 含交互项回归 + **简单斜率图** | 交互项 β, p, 简单斜率图 |

### 前提假设检查清单

| 前提 | 检查方法 | 违反时的处理 |
|------|---------|-------------|
| 正态性 | 偏度/峰度(\|值\|<2 / <7)、小样本 Shapiro-Wilk | 非正态 → Bootstrap / 稳健估计 / 变量转换 |
| 方差齐性(t/ANOVA) | Levene 检验 | 违反 → Welch 校正 |
| 独立性 | 研究设计 / 回归 Durbin-Watson | 不独立 → 混合模型 / 聚类稳健 SE |
| 线性 & 同方差(回归) | 残差图、Breusch-Pagan | 违反 → 变换 / WLS / 稳健 SE |
| 无多重共线 | VIF<5、Tolerance>0.2 | 违反 → 删/并变量 / 主成分 |
| 无自相关(回归) | Durbin-Watson≈2 | 违反 → Newey-West / 序列模型 |

> 每条前提不达标，都要在 D4 方法或 A5 局限里说明，不得假装满足。

---

# 第二部分：定量二手（M1-M5 元分析）

二手效应量聚合分析（PRISMA/森林图/漏斗图/异质性）。

## 路径概览

| 阶段 | 产出 |
|------|------|
| M1 研究问题与检索 | PICO框架、检索策略、数据库清单 |
| M2 文献筛选与编码 | PRISMA流程图、编码表、纳入排除标准 |
| [注意] M2 图表 → 读取 `skills/obhrm-methodology/domains/visualization/visualization.md`（桑基图） |
| M3 效应量与主效应 | 效应量汇总表、异质性（Q/I²）、森林图 |
| [注意] M3 图表 → 读取 `skills/obhrm-methodology/domains/visualization/visualization.md`（森林图/雷达图） |
| M4 偏倚与调节分析 | 漏斗图、Egger检验、亚组分析、元回归 |
| [注意] M4 图表 → 读取 `skills/obhrm-methodology/domains/visualization/visualization.md`（漏斗图） |
| M5 撰写元分析报告 | PRISMA声明、综合报告 |

## 阶段执行规范

### M1 研究问题
- PICO 框架：Population/Intervention/Comparison/Outcome
- 检索数据库 ≥ 3 个（CNKI + WoS + PsycINFO 等）
- 记录检索式、日期、命中数

### M2 文献筛选
- PRISMA 流程图（调用 `skills/obhrm-methodology/domains/visualization/visualization.md` 桑基图）
- 编码表：研究ID/作者/年份/N/效应量类型/r或d值/调节变量
- 双人编码，报告一致性 Kappa > 0.80

### M3 效应量
- 转换：r→Fisher's Z 或 d→Hedges' g
- 异质性：Q 检验 + I²（25/50/75 低中高）
- 模型选择：I²>50% 用随机效应，否则固定效应
- 输出森林图（`skills/obhrm-methodology/domains/visualization/visualization.md`）

### M4 偏倚与调节
- 发表偏倚：漏斗图 + Egger回归 + 失安全系数
- 亚组分析：按调节变量分组比较效应量
- 元回归：连续调节变量分析

### M5 报告
- PRISMA 2020 检查清单逐项对照
- 讨论：效应量大小解释（Cohen 标准）、异质性来源、局限性
- **连接强制**：M5 须回扣 M1 研究问题（PICO）——主效应量如何回答研究问题、异质性/调节结果如何限定结论

### M5 收尾核对清单

**图表嵌入**：[ ] 森林图/漏斗图/PRISMA桑基图已生成 [ ] 已编号登记 [ ] ≥80字图注 [ ] 正文≥1处引用
**结果-问题连接**：[ ] M5 每段对应 M1 一个 PICO 子问题 [ ] 效应量均有结论解读 [ ] 异质性/调节结果限定结论边界 [ ] 无逻辑断链

## 图表嵌入（元分析路径）

- **M3 森林图/雷达图**、**M4 漏斗图**：生成后连续编号，配 ≥80 字 APA 图注，正文显式引用
- **M2 PRISMA 桑基图**：作为筛选流程核心图嵌入 M2/M5
- **全局图表登记表**：元分析路径收尾时逐图核对

---

## 统计计算辅助与外部引擎对接

> 完整规则与函数清单见 `../SKILL.md`「统计计算辅助（stat_helpers.py）与外部引擎对接」。此处给出本路径的取用要点。

本路径**不内置统计引擎、不代跑分析**（见 `../SKILL.md` 统计数字防编造规则）。真实分析走两条路：

1. **主分析 → R 脚本**：在上方「方法族→D 阶段映射」或 `references/methods-knowledge.md` 确定 `method_no`（如 10.1.R / 14.1.R / 18.1.R），用 `../../r-analysis/scripts/query_r.py` 取脚本路径，由**用户**在本机 R 环境运行并回传真实输出。权威映射见 `../../r-analysis/knowledge/_r_index.json`。
2. **轻量换算 → stat_helpers.py**：已取得真实数值后做效应量/信度换算（Cohen's d、η²、Cramér's V、VIF、ΔR²、Bootstrap CI、Cronbach's α）。它**只计算、不编造**，缺真实输入即报错。需 numpy（`pip install numpy scipy`）。
   ```bash
   python3 ../scripts/stat_helpers.py cohen_d --g1 3.2,1.1,2.9 --g2 2.8,0.9,3.1
   python3 ../scripts/stat_helpers.py cronbach --csv responses.csv
   ```
3. **回填交付物**：所有数值标来源（R 输出 / 文献 / 用户回传）；未计算者写「未计算 — 需在实际统计环境中运行（脚本编号：…）」，**不填占位数值**。

---

# 定量分析通用：跨域联动与协作交接

## 跨域联动

- **A4 → 定量**（论文写作到达方法阶段后委托分析）→ `../../paper-writing/SKILL.md`
- **定量 → A/B**（完成后结果回传）→ 论文路径续写 A5、基金路径用于预研数据。回传字段见 `skills/obhrm-methodology/references/templates/handoff-protocol.md` 链路二
- **D → M**（一手完成后单研究证据不足）→ 同文件 M1-M5 部分。字段级规格见 `skills/obhrm-methodology/references/templates/handoff-protocol.md` §链路十
- **图表需求**（D2-D4 / M2-M4）→ `skills/obhrm-methodology/domains/visualization/visualization.md`，按「图表嵌入协议」入正文
- **方法层**：`skills/obhrm-methodology/references/methods/statistical_report_standard.md`（APA 报告）、`skills/obhrm-methodology/references/methods/statistical_figure_standard.md`（图表规范）、`skills/obhrm-methodology/references/methods/systematic_review_toolkit.md`（系统综述/PRISMA）、`skills/obhrm-methodology/references/methods/evidence_retrieval_protocol.md`（文献筛选）、`references/methods-knowledge.md`（D 域方法族真源）

## 协作交接

- **A→定量 / B→定量 委托分析**：交接块字段见 `skills/obhrm-methodology/references/templates/handoff-protocol.md` 链路一
- **定量→A / 定量→B 结果回传**：交接块字段见链路二
- **定量→C 反向诊断**：`../../peer-review/SKILL.md`
- **定量→蒸馏**：交接块字段见链路六；判层后落点 `skills/obhrm-methodology/references/governance/method_accumulation.md`

## 参考

`skills/obhrm-methodology/references/methods/statistical_report_standard.md`、`skills/obhrm-methodology/references/methods/statistical_figure_standard.md`、`skills/obhrm-methodology/references/methods/systematic_review_toolkit.md`、`skills/obhrm-methodology/references/methods/evidence_retrieval_protocol.md`、`skills/obhrm-methodology/references/templates/handoff-protocol.md`（跨路径字段级规格）。
