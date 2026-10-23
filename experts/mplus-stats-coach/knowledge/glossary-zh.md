# glossary-zh.md · Mplus 中英术语对照表（自编）

> 用途：替代原设计的 `knowledge/legacy-cn/`（第三方中文素材层）
> 性质：**本方自编**，不复制任何第三方材料原文
> 版本：v2 · 2026-10-08
> 覆盖来源：本表术语与计数取自官方 UG 示例语料**实测统计**（**519 份 `.inp`** / 10 章 / 21 模型族 /
> 16 类命令段 + 4 类数据子段 + 21 种 `MODEL <标签>` 变体 / 31 项分析选项），非抄录任何中文教材。
> v2 变更：段名计数改为**逐文件实测**口径；新增 §C.1 合法段名变体、§C.2 缩写与单复数、§C.3 实测硬阈值。

## 使用约定

1. **Mplus 语法一律保留英文**（段名、选项、关键字）。本表只解决「**和用户用中文讨论时怎么说**」，不用于生成语法。
2. 中文译名优先采用**中文心理学 / 计量学界通行译法**；存在多个通行译名时全部列出，并在备注中标明常见异译。
3. 标 **〔推荐〕** 的为大量异译时的首选用词；标 **〔异译〕** 的为需向用户澄清以避免误解的用法。
4. 本表**不含**任何第三方教材的原文表述；译名为通用学术用语，不构成对他人作品的复制。

---

## A. 官方 User's Guide 章节名对照（Chapter 3–12）

出自官方 UG 示例页实测（`statmodel.com/usersguide/chapter<N>.shtml`）。

| 章 | 英文（官方原名） | 中文译名 | 语料量（实测） |
|---|---|---|---|
| Ch3 | Regression and Path Analysis | 回归与路径分析 | 19 主示例 |
| Ch4 | Exploratory Factor Analysis | 探索性因子分析（EFA） | 8 主示例 |
| Ch5 | Confirmatory Factor Analysis and Structural Equation Modeling | 验证性因子分析与结构方程模型（CFA/SEM） | 41 主示例 |
| Ch6 | Growth Modeling and Survival Analysis | 增长建模与生存分析 | 30 主示例 |
| Ch7 | Mixture Modeling with Cross-Sectional Data | 横断数据的混合建模 | 29 主示例 |
| Ch8 | Mixture Modeling with Longitudinal Data | 纵向数据的混合建模 | 19 主示例 |
| Ch9 | Multilevel Modeling with Complex Survey Data | 复杂抽样数据的多层建模 | 51 主示例 |
| Ch10 | Multilevel Mixture Modeling | 多层混合建模 | 15 主示例 |
| Ch11 | Missing Data Modeling and Bayesian Analysis | 缺失数据建模与贝叶斯分析 | 15 主示例 |
| Ch12 | Monte Carlo Simulation Studies | 蒙特卡洛模拟研究 | 2 主示例 |

> **注意**：官方示例章**止于 Ch12**。`chapter13.shtml` 会静默回落到 Chapter 3 的内容，**不存在第 13 章**。

---

## B. 模型族对照

### B.1 结构方程族

| 英文 | 缩写 | 中文译名 | 备注 |
|---|---|---|---|
| Confirmatory Factor Analysis | CFA | 验证性因子分析 | — |
| Structural Equation Modeling | SEM | 结构方程模型 | — |
| Exploratory Factor Analysis | EFA | 探索性因子分析 | — |
| Exploratory Structural Equation Modeling | ESEM | 探索性结构方程模型 | — |
| Path Analysis | — | 路径分析 | — |
| Mediation Analysis | — | 中介效应分析 | 语法多用 `MODEL INDIRECT` |
| Moderation Analysis | — | 调节效应分析 | 潜变量交互用 `XWITH` |
| Multiple Group Analysis | — | 多组分析 | — |
| Measurement Invariance | — | 测量不变性 | — |
| Alignment | — | 对齐优化法 | 多组不变性的替代方案，官方专题 |

### B.2 增长与纵向族

| 英文 | 缩写 | 中文译名 | 备注 |
|---|---|---|---|
| Latent Growth Curve Modeling | LGCM | 潜变量增长曲线模型 | 语法形如 `i s \| y1@0 y2@1 …;` |
| Latent Growth Model | LGM | 潜变量增长模型 | 〔异译〕「潜变量成长模型」亦常见 |
| Growth Mixture Modeling | GMM | 增长混合模型 | 〔异译〕「潜变量增长混合模型」 |
| Latent Change Score | LCS | 潜变量变化分数模型 | — |
| Cross-Lagged Panel Model | CLPM | 交叉滞后面板模型 | — |
| Random Intercept Cross-Lagged Panel Model | RI-CLPM | 随机截距交叉滞后面板模型 | 官方专题页 |
| Latent Transition Analysis | LTA | 潜在转变分析 | 〔异译〕「潜在转换分析」「潜在状态转移分析」 |
| Latent Class Growth Analysis | LCGA | 潜在类别增长分析 | — |
| Piecewise Growth | — | 分段增长模型 | — |

### B.3 混合（分类）模型族

| 英文 | 缩写 | 中文译名 | 备注 |
|---|---|---|---|
| Latent Class Analysis | LCA | 潜在类别分析 | 指标为**分类**变量 |
| Latent Profile Analysis | LPA | 潜在剖面分析 | 指标为**连续**变量；〔异译〕「潜在轮廓分析」 |
| Latent Class Cluster Analysis | LCCA | 潜在类别聚类分析 | — |
| Factor Mixture Modeling | FMM | 因子混合模型 | — |
| Mixture Regression | — | 混合回归 | — |
| Known Class | — | 已知类别 | `KNOWNCLASS` 指定，用于多组混合模型 |
| Mover-Stayer Model | — | 流动-稳定模型 | LTA 常用设定 |

> **LCA 与 LPA 的区分（最常被问错的一处）**：
> 同一套混合建模语法，差别**只在于指标变量是分类还是连续**——分类指标 → LCA，连续指标 → LPA。
> 中文语境下两者常被混用，回答时须先确认指标类型。

### B.4 多层与时序族

| 英文 | 缩写 | 中文译名 | 备注 |
|---|---|---|---|
| Multilevel Modeling | MLM | 多层模型 | 〔异译〕「多层次模型」「层级模型」 |
| Multilevel Mixture Modeling | — | 多层混合模型 | 官方 Ch10 |
| Cross-Classified Model | — | 交叉分类模型 | — |
| Complex Survey Data | — | 复杂抽样数据 | 官方 Ch9；需权重与分层 |
| Dynamic Structural Equation Modeling | DSEM | 动态结构方程模型 | — |
| Residual Dynamic SEM | RDSEM | 残差动态结构方程模型 | — |
| Intensive Longitudinal Data | ILD | 密集纵向数据 | 经验取样 / 日记法数据 |
| Multilevel Time Series | — | 多层时间序列 | — |

### B.5 数据与估计族

| 英文 | 缩写 | 中文译名 | 备注 |
|---|---|---|---|
| Bayesian Analysis | — | 贝叶斯分析 | `ESTIMATOR=BAYES` |
| Missing Data Modeling | — | 缺失数据建模 | — |
| Full Information Maximum Likelihood | FIML | 全息极大似然 | 〔异译〕「完全信息极大似然」 |
| Multiple Imputation | MI | 多重插补 | `TYPE=IMPUTATION` |
| Monte Carlo Simulation | MC | 蒙特卡洛模拟 | 用于检验力 / 样本量规划 |
| Survival Analysis | — | 生存分析 | 〔异译〕「事件史分析」 |
| Censored Regression | — | 删截回归 | 亦称 Tobit 模型 |
| Count Regression | — | 计数回归 | 泊松 / 负二项 |
| Penalized SEM | PSEM | 惩罚结构方程模型 | LASSO / GEOMIN，官方专题 |

---

## C. 命令段名（**保留英文，不翻译**）

Mplus 语法中段名必须拼写英文原文，本表仅说明其作用。
「出现份数」为 **519 份官方 `.inp` 逐文件实测**（文档级：只要该文件出现该段即计 1 次）。

| 段名（英文原文） | 出现份数 | 作用 |
|---|---:|---|
| `TITLE` | 518 | 标题（**自由文本，无语法作用，不需分号**） |
| `MODEL` | 501 | 模型设定主体 |
| `ANALYSIS` | 412 | 模型类型、估计法、算法、收敛设定 |
| `OUTPUT` | 407 | 额外输出（TECH 系列、标准化、修饰指数等） |
| `DATA` | 283 | 数据文件与格式声明 |
| `VARIABLE` | 283 | 变量名、类型、用法声明 |
| `MONTECARLO` | 236 | 蒙特卡洛模拟设定 |
| `MODEL POPULATION` | 219 | 蒙特卡洛的总体模型设定 |
| `PLOT` | 74 | 绘图输出 |
| `MODEL CONSTRAINT` | 66 | 参数约束、自定义参数、非线性约束 |
| `DEFINE` | 44 | 派生变量、变量变换 |
| `MODEL PRIORS` | 23 | 贝叶斯先验 |
| `MODEL MISSING` | 19 | 缺失数据模型设定 |
| `MODEL MONTECARLO` | 17 | 蒙特卡洛的**生成模型**设定（与 `MODEL POPULATION` 相对） |
| `SAVEDATA` | 8 | 保存结果（因子得分、分类结果、插补数据） |
| `MODEL INDIRECT` | 2 | 间接效应（中介）声明 |

### C.1 合法段名变体（**实测 · 519 份逐文件**）

以下写法**全部合法**，解析器若只认规范段名，会把大量官方示例误判为「段名拼写错误」。

| 变体 | 例数 | 说明 |
|---|---:|---|
| `MODEL C1:` `MODEL C2:` `MODEL C3:` `MODEL C4:` `MODEL C:` | 19 / 19 / 6 / 2 / 8 | 多类别（mixture）**按类别分别建模** |
| `MODEL G1:` `MODEL G2:` `MODEL G3:` | 3 / 19 / 1 | 多组（`GROUPING`）**按组分别建模** |
| `MODEL CB:` `MODEL CG:` `MODEL CW:` `MODEL CU:` `MODEL CY:` `MODEL DZ:` `MODEL FEMALE:` | 4 / 5 / 2 / 2 / 2 / 4 / 4 | 以上均为**类别或组的标签名**，标签由用户自定，非固定清单 |
| `MODEL 1988:` `MODEL 1989:` | 1 / 1 | 标签可为**纯数字**（历史口径命名） |
| **`MODEL PRIOR:`（单数）** | **1** | 与 `MODEL PRIORS` 等价，**单数亦合法**（`ug/ch5/mcex5.5part4.inp`） |
| `DATA IMPUTATION:` | 6 | 插补设定（与 `TYPE=IMPUTATION` 配套） |
| `DATA MISSING:` | 3 | 缺失模型设定 |
| `DATA TWOPART:` | 2 | 两部分（零膨胀）设定 |
| `DATA WIDETOLONG:` | 1 | **宽→长**数据重塑（`ug/ch9/ex9.16.inp`） |

> **归纳**：`MODEL <任意标签>:` 中的标签**不受限**（类别号 / 组名 / 数字 / 单词均可）；
> `DATA <任意单词>:` 亦为合法的**数据附加说明段**。解析器应写成
> `MODEL\s+[A-Za-z0-9_]{1,8}` / `DATA\s+[A-Za-z]{3,14}` 这种**宽松形态**，
> 而不是穷举清单——**穷举必然漏项**（本轮实测即因穷举清单漏掉 `MODEL PRIOR:` 单数而误报）。

> 段名可写作 `MODEL: i s | y1@0 y2@1;`，**也可段名与内容同行**（`DATA:\tFILE IS x.dat;`）。
> 这是 Mplus 的真实语法形态，解析器必须支持，否则会把段判空。
>
> **`TITLE` 是自由文本段**：由下一命令终止，**不需要分号**；官方补充集里 `TITLE` 可长达 **2661 行**
> （回显整段研究背景、文献出处、变量说明）。**在 `TITLE` 段内不得做任何段名判定**——
> 其中出现的 `Sources:`、`Holzinger, K. J. & Swineford, F. (1939).` 等冒号行都是**正文**。

### C.2 变量清单关键字的**缩写与单复数**（**实测 · 全部合法**）

Mplus 的变量清单关键字接受**词干 + 可选复数 `S`** 的缩写。实测分布：

| 写法 | 出现份数 | 说明 |
|---|---:|---|
| `NAMES` / `NAMES ARE` | 519 | **唯一不带缩写**的关键字（`NAME` 不合法） |
| `USEVARIABLES` | 51 | 完整复数形 |
| **`USEVAR`** | 4 | 缩写 |
| **`USEV`** | 42 | **最短缩写**（42 份，比完整形更常见） |
| **`USEVARIABLE`（单数）** | 1 | 单数亦合法（`ug/ch9/ex9.16.inp`） |
| `CATEGORICAL` | 209 | — |
| `CLUSTER` | 78 | — |
| `KNOWNCLASS` | 5→9 | 与 `CLASSES` 配套 |
| `AUXILIARY` | 5 | 可带 `(e)` 误差校正 / `(m)` 含缺失 |

> **实现约定**：变量清单关键字一律按**单数词干 + `S?`** 收录，不得只认复数形。
> 本轮实测的坑：早期实现只匹配 `USEVARIABLES` / `USEVAR`，
> **漏掉 `USEV`（42 份，最长用的写法）与 `USEVARIABLE`（单数）**，
> 导致「MODEL 引用未声明变量」规则在这些文件上**假绿**（漏报真实缺口而非误报）。

### C.3 两个**实测硬阈值**（**不得凭印象改**）

| 阈值 | 值 | 实证依据 | 触发可靠性 |
|---|---:|---|---|
| 变量名长度上限 | **8** 字符 | **官方 519 份 `.inp` 全量展开 `NAMES` 后实测**：变量名长度分布 1–8 字符，**最大恰为 8**、**超过 8 的 0 个**（共约 3,054 个变量名） | **上限确证**。⚠ 正因语料本身守规，555 份 `.out` 中**没有**变量名截断警告样本（0 例）→ 该警告**无 `.out` 实证**，不得声称"必报" |
| 输入行宽上限 | **90** 字符 | 官方 `.out` 的 `Input line exceeded 90 characters. Some input may be truncated.`（**4 份**报出） | ⚠ **阈值确证，但触发不可预测**：超限 `.inp` 共 **6** 份，**报出该警告仅 4 份**；`ex5.28`（95 字符）与 `ex5.32`（**131 字符**）均**未报** → 只作提示，**不得承诺必报** |

> **两个阈值的实证性质不同，不可混为一谈**：
> · **8 字符**是**语法约束**（由"官方语料 0 例超限"反证上限）——写超了在 Mplus 里就是错的；
> · **90 字符**是**输出阶段的截断警告**（由 4 份 `.out` 观测到）——写超了**不一定**被报出来。
> 因此 `check_inp.py` 中 8 字符判 `BLOCKER` 级依据（语法约束），90 字符判 `WARN`/`INFO` 级提示。

### C.4 模型语句中的两处**实测写法**（解析器必守）

| 写法 | 含义 | 实测例 | 若不支持会怎样 |
|---|---|---|---|
| `s* \| y1 ON a1;` | **`*`/`@` 起始值写在 `\|` 左侧**：随机斜率给定起始值 | `ug/ch9/ex9.14.inp`、`mcex9.14.inp`，共 12 处 | 把 `s*` 当作未声明变量，误报「引用未声明变量」 |
| `s1-s4 \| f BY y1-y4;` | **`\|` 右侧可直接 `BY` 定义潜变量**（不需要另一条 `f BY …`） | 8 处，全在 Ch9（`ex9.19part1/2/3`、`ex9.26`、`ex9.27`、`ex9.40part2`、`mcex9.26`×2） | 把 `f` 判为未声明（实测 9 例误报） |

> **两条实现约定（由上述实测倒逼）**：
> 1. **语句按 `;` 切分，不按换行切分**——Mplus 允许一条语句跨任意多行
>    （官方常见 `s1-s4 \|\n f BY y1-y4;`）。按 `\n` 切会把一条语句劈成两句。
> 2. **先剥 `%…%` 区块标记（`%WITHIN%` / `%BETWEEN%` / `%OVERALL%` / `%c#1%`）再解析**，
>    并**用 `re.search` 而非行首锚定 `re.match`**——语句常以区块标记打头
>    （`%WITHIN%` 开头时行首锚定匹配不到，实测误报从 11 涨到 136）。
>    同时变量清单正则必须加 `(?<!%)…(?!\s*%)` 约束，否则 `%WITHIN%` 会被当成变量清单关键字、
>    把块内首条语句吞成「声明」，形成**假绿**（掩盖真实缺口，比误报更危险）。

---

## D. 关键分析选项对照

### D.1 `TYPE=` 分析类型

| 选项值 | 中文说明 | 语料量 |
|---|---|---:|
| `TYPE=GENERAL` | 通用模型（**默认值**，可不写） | — |
| `TYPE=MIXTURE` | 混合建模（LCA / LPA / GMM / LTA 等） | 99 |
| `TYPE=TWOLEVEL` | 两水平模型 | 101 |
| `TYPE=THREELEVEL` | 三水平模型 | — |
| `TYPE=CROSSCLASSIFIED` | 交叉分类模型 | — |
| `TYPE=RANDOM` | 随机效应（DSEM / RI-CLPM 等） | 9 |
| `TYPE=EFA` | 探索性因子分析 | 4 |
| `TYPE=IMPUTATION` | 多重插补 | 5 |
| `TYPE=COMPLEX` | 复杂抽样（权重 / 分层 / 聚类） | — |
| `TYPE=PLOT2` / `PLOT3` | 绘图专用 | — |

### D.2 `ESTIMATOR=` 估计法

| 选项值 | 中文说明 | 适用 | 语料量 |
|---|---|---|---:|
| `ESTIMATOR=ML` | 极大似然 | 连续指标 | 10 |
| `ESTIMATOR=MLR` | **稳健**极大似然 | 连续指标 + 非正态稳健标准误 | 24 |
| `ESTIMATOR=MLM` | 稳健极大似然（Satorra-Bentler） | 同 MLR，χ² 校正方式不同 | — |
| `ESTIMATOR=MLF` | 极大似然（含 Fisher 信息） | 复杂抽样 | — |
| `ESTIMATOR=WLSMV` | 加权最小二乘（均值方差调整） | **分类 / 有序指标** | 8 |
| `ESTIMATOR=ULSMV` | 非加权最小二乘 | 分类指标，大样本 | — |
| `ESTIMATOR=BAYES` | 贝叶斯估计 | 小样本 / 复杂模型 | 73 |

### D.3 `ALGORITHM=` 与其他

| 选项 | 中文说明 | 语料量 |
|---|---|---:|
| `ALGORITHM=INTEGRATION` | 数值积分（分类指标 + 潜变量时必需） | 30 |
| `STARTS=` | 随机起始值次数（混合模型收敛关键） | 16 |
| `PROCESSORS=` | 并行核数 | 69 |
| `BOOTSTRAP=` | 自助法抽样次数 | — |
| `MISSING=ALL (值)` | 缺失值标记 | 13 |
| `AUXILIARY=` | 辅助变量（可 `(e)` 误差校正 / `(m)` 含缺失） | 4 |
| `KNOWNCLASS=` | 已知类别指定 | 7 |
| `XWITH` | 潜变量交互项 | 4 |

---

## E. 输出段与拟合指标

### E.1 输出文件（`.out`）的主要区块

| 英文区块名 | 中文说明 |
|---|---|
| `INPUT INSTRUCTIONS` | 输入回显（**自含原始 `.inp` 全文**，实测自含率 100%） |
| `SUMMARY OF ANALYSIS` | 分析概要（样本量、变量数、估计法、缺失处理） |
| `MODEL FIT INFORMATION` | 模型拟合信息 |
| `FINAL CLASS COUNTS AND PROPORTIONS` | 最终类别计数与比例（混合模型） |
| `MODEL RESULTS` | 模型参数结果 |
| `QUALITY OF NUMERICAL RESULTS` | 数值结果质量（**警告高频出现处**） |
| `TECHNICAL N OUTPUT` | 技术附录输出（TECH1–TECH16） |

### E.2 常用拟合指标

| 英文 | 中文译名 | 备注 |
|---|---|---|
| Chi-Square (χ²) | 卡方统计量 | 对样本量敏感 |
| Degrees of Freedom | 自由度 | — |
| CFI | 比较拟合指数 | 常用参考 ≥ .90 / ≥ .95 |
| TLI | Tucker-Lewis 指数 | 〔异译〕「非规准拟合指数 NNFI」 |
| RMSEA | 近似误差均方根 | 〔异译〕「近似均方根误差」 |
| SRMR | 标准化残差均方根 | — |
| WRMR | 加权残差均方根 | 多用于分类指标 |
| AIC / BIC / aBIC | 赤池 / 贝叶斯信息准则 | 混合模型定类数常用 |
| LMR-LRT | Lo-Mendell-Rubin 似然比检验 | 混合模型定类数 |
| BLRT | 自助似然比检验 | 混合模型定类数 |
| Entropy | 分类熵 | 混合模型分类质量（→1 越好） |
| Loglikelihood | 对数似然 | — |
| BIC 差值 | BIC difference | 常用参考 > 10 为强证据 |

---

## F. 混合建模专有术语

| 英文 | 中文译名 | 说明 |
|---|---|---|
| 3-Step Approach | 三步法 | 混合模型加入协变量 / 结果变量 |
| BCH Method | BCH 法 | 加权多组法，处理分类误差 |
| DCAT | DCAT 法 | 分类结果变量的距离法 |
| ML Three-Step | 极大似然三步法 | 官方推荐 |
| Posterior Probability | 后验概率 | — |
| Most Likely Class Membership | 最可能类别归属 | — |
| Class Enumeration | 类别数枚举 | 试 1…k 类模型 |
| Local Maximum | 局部极大 | 警告「BEST LOGLIKELIHOOD NOT REPLICATED」相关 |
| Random Starts | 随机起始值 | `STARTS=`，防局部极大 |
| Label Switching | 类别标签互换 | 多起点结果的类别顺序不稳定 |
| Saddle Point | 鞍点 | 官方 FAQ 有专条 |
| Not Positive Definite | 非正定 | 协方差矩阵异常，官方语料中 PSI 非正定 4 例 |

---

## G. 需向用户澄清的高频歧义

回答时若遇到下列用词，**先确认再作答**，不要默认。

| 用户可能说 | 可能指 | 澄清方式 |
|---|---|---|
| 「潜类别」「潜剖面」混用 | LCA（分类指标）/ LPA（连续指标） | 先问指标变量是分类还是连续 |
| 「成长模型」「增长模型」 | 同一概念（LGM / LGCM） | 两词等价，可直接作答 |
| 「多层次」「多层」「层级」 | 同一概念（Multilevel） | 等价 |
| 「潜在转变」「潜在转换」「状态转移」 | 同一概念（LTA） | 等价；注意与 LTA 的「流动-稳定」设定区分 |
| 「中介」「间接效应」 | 同一概念（Mediation） | 等价 |
| 「调节」「交互」 | 同一概念（Moderation / Interaction） | 等价 |
| 「拟合好」 | 未指定指标 | 追问以哪个指标为准，勿替用户下结论 |
| 「结果显著」 | 可能混淆 p 值与效应量 | 提示两者不同，均需报告 |

---

## H. 本表维护约定

1. **新增术语须在官方语料或官方文档中有出处**；无出处者标 **〔待核〕** 并挂待办。
2. **不得从第三方中文教材抄录表述**——译名为通用学术用语，可自由使用；教材的**解释性文字**不行。
3. 每次官方 UG 升版后复核 A 节章节名。
4. 本表**不用于生成 Mplus 语法**；语法一律英文原文。

---

> 本表由本方自编，术语为学术通用用语，不复制任何第三方作品原文。
> 覆盖统计来自 `knowledge/cases.jsonl`（**519 条**官方示例，逐文件实测）。
> ⚠ 本表**只解决「和用户用中文讨论时怎么说」**，不用于生成语法；语法一律英文原文。
> ⚠ 本表**不翻译官方手册**——翻译属演绎作品、翻译权是著作权的一项；
> 正确解法是**自编中文讲解 + 自编通用术语对照**（见 §H 维护约定第 2 条）。
