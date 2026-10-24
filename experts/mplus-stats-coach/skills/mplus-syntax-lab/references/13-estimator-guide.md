# 13 · 估计法与分析类型选型

> 回答「该用哪个 `ESTIMATOR` / `TYPE` / `ALGORITHM`」的唯一依据。
> 语料量口径：官方 **519** 份 `.inp` 逐文件实测（文档级）。

---

## 一、`TYPE=` 分析类型

| 取值 | 含义 | 实测份数 | 何时用 |
|---|---|---:|---|
| `GENERAL` | 通用模型（**默认值，可不写**） | — | 单层 CFA / SEM / 路径 |
| `MIXTURE` | 混合建模 | 91 | LCA / LPA / GMM / LTA / 因子混合 |
| `TWOLEVEL` | 两水平 | 101 | 嵌套数据（学生嵌套于班级） |
| `THREELEVEL` | 三水平 | — | 三层嵌套（学生 ⊂ 班级 ⊂ 学校） |
| `CROSSCLASSIFIED` | 交叉分类 | 13 | 同时归属两个非嵌套维度 |
| `RANDOM` | 随机效应 | 9 | DSEM / RI-CLPM / 随机斜率作为结果 |
| `EFA` | 探索性因子分析 | 12 | 无先验结构，需旋转 |
| `IMPUTATION` | 多重插补 | 6 | 显式插补并保存插补数据 |
| `COMPLEX` | 复杂抽样 | — | 权重 / 分层 / 聚类校正 |
| `BASIC` | 基础描述 | 1 | 仅输出描述统计 |

**可组合**：`TYPE = TWOLEVEL MIXTURE RANDOM;`（实测出现 1 例）、`TYPE = CROSS RANDOM;` 等。
**写法**：`TYPE = TWOLEVEL;` 与 `TYPE IS TWOLEVEL;` **等价**（实测两种都有）。

> ⚠ **`TYPE` 只在 `ANALYSIS` 段取**。`PLOT` 段的 `TYPE = PLOT2;` 是**绘图类型**，
> 若从全文抓 `TYPE` 会被它污染（本轮实测踩过这个坑）。

---

## 二、`ESTIMATOR=` 估计法

| 取值 | 含义 | 实测份数 | 适用 |
|---|---|---:|---|
| `ML` | 极大似然 | 10+ | 连续指标，正态性尚可 |
| **`MLR`** | **稳健极大似然** | 24+ | **连续指标 + 非正态**（最常用，χ² 用 Satorra-Bentler 校正） |
| `MLM` | 稳健 ML | — | 同 `MLR`，χ² 校正方式不同 |
| `MLF` | 含 Fisher 信息的 ML | — | 复杂抽样 |
| **`WLSMV`** | 加权最小二乘（均值方差调整） | 8+ | **分类 / 有序指标**（二分、李克特有序、多分类） |
| `ULSMV` | 非加权最小二乘 | — | 分类指标，大样本 |
| **`BAYES`** | 贝叶斯 | 73 | 小样本 / 复杂模型 / 需先验 |

**选择口诀**：
- 指标**连续** → `ML`（正态）/ **`MLR`（默认推荐）**
- 指标**有序或二分** → **`WLSMV`**
- 样本**小**或模型**复杂** → `BAYES`
- 指数族非正态（计数 / 删截）→ 配 `COUNT` / `CENSORED` + `MLR`

> ⚠ **估算量口径**：上表「份数」为**语法中显式写出**该估计法的文件数。
> 未写 `ESTIMATOR` 时按 `TYPE` 走默认值（如 `TYPE=TWOLEVEL MIXTURE` 默认 `MLR`），
> **不要**因为没写就认为「没有估计法」。

---

## 三、`ALGORITHM=` 与其他

| 选项 | 实测份数 | 说明 |
|---|---:|---|
| `ALGORITHM = INTEGRATION` | 30 | **分类指标 + 潜变量**时必需；也用于 `XWITH` |
| `STARTS = <n> <m>` | 16 | 混合模型随机起点，防局部极大。经验值 ≥ `500 100`，模型复杂时上调 |
| `PROCESSORS = n` | 69 | 并行核数 |
| `BOOTSTRAP = n` | — | 自助抽样次数（配合 `CINTERVAL(BCBOOTSTRAP)`） |
| `MISSING = ALL (-999)` | 13 | 缺失值标记 |
| `AUXILIARY = v(e) v(m)` | 5 | `(e)` 误差校正 / `(m)` 含缺失 |
| `KNOWNCLASS = c (g);` | 7 | 已知类别，用于多组混合 |
| `FBITER = n` | — | 贝叶斯迭代次数 |
| `XWITH` | 4 | 潜变量交互项（`MODEL` 段用，非 `ANALYSIS`） |

---

## 四、`TECH8` 可用性（**最易答错的一条，必须按此回答**）

官方消息原文：

```
TECH8 option is available only with analysis types MIXTURE, RANDOM, or TWOLEVEL
with estimators ML, MLF, or MLR or ALGORITHM=INTEGRATION. Request for TECH8 is ignored.
```

**它看起来是组合规则，实测却不完全如此。** 口径：**只统计「输入回显中请求了 `TECH8`」的 `.out`**。

| 版本 | 请求 `TECH8` | 实际报「不可用」 |
|---|---:|---:|
| `6.1` | 27 | **6** |
| `6.11` | 4 | 0 |
| `8` | 67 | 0 |
| `8.8` | 188 | 0 |
| `DEVELOPMENT` | 5 | 1 |
| **Mplus 7** | **无样本** → 【缺失】 | — |

**两个结论**：
1. **不是版本开关**：v6.1 里也有 21/27 份**不报**。
2. **组合条件本身也没被完全解出**：按消息文本反推的规则（`TYPE ∈ {MIXTURE, RANDOM, TWOLEVEL}`
   或 `ESTIMATOR=BAYES` 或 `ALGORITHM=INTEGRATION`）在 v6.1 上 25/27 = 92.6% 吻合，**2 例反例**：

| 反例写法 | 实测 |
|---|---|
| `TYPE = EFA 3 3` + `ML` | **未报** |
| `TYPE = EFA 4 4` + `ML` | **报出** |
| `TYPE = BASIC` | **未报** |

> 同为 EFA，`3 3` 与 `4 4` 结果相反 → **不可静态判定**。

**因此本包的规定动作**：

| 场景 | 动作 |
|---|---|
| 版本 ≥ 8 且写 `TECH8` | **不提示**（v8/v8.8 请求 `TECH8` 的 255 份中 0 份报出） |
| 版本 = 6 且 `TECH8` + **无 `TYPE`** + 非 BAYES + 无 `INTEGRATION=` | **`WARN`**（该写法 2/2 全报） |
| 版本 = 6 且 `TECH8` + **有 `TYPE` 但取值非豁免** | **`INFO`** + 写明「6 份中 4 报、2 未报，请以实跑为准」 |
| 版本 = 7 | **`INFO`** + 标【缺失】 |
| 版本未知 | 按 9.1（语言代次）讲语法，但**不承诺**是否报警告 |

**禁止表述**：「写 `TECH8` 一定会报警告」——此话在 291 份样本中**错 284 次**。

> ✓ **一个正向例外**：`ESTIMATOR = BAYES` 下 `TECH8` 输出 **PSR 收敛判据**，是**标准用法**，
> 官方 `ex9.26 / ex9.27 / ex9.32 / ex9.40part2` 等 `.out` 含 `PSR VALUE DOES NOT INCREASE`
> 且 **0 错误 0 警告**。**不要**把贝叶斯下的 `TECH8` 当成错误。

---

## 五、兼容矩阵（本包已实现的静态规则）

| 组合 | 结论 | 规则 |
|---|---|---|
| `MODINDICES` + `ESTIMATOR=BAYES` | ✗ 不兼容 | `L11` `BLOCKER` |
| `OUTPUT` 要 bootstrap 区间 + `ANALYSIS` 无 `BOOTSTRAP` | ✗ 不兼容 | `L13` `BLOCKER` |
| `BOOTSTRAP` + `ESTIMATOR=BAYES` | ✗ 不兼容 | `L13` `BLOCKER` |
| `SAMPSTAT` + 全部结局为类别型 | ✗ 不兼容 | `L12` `WARN` |
| `CLASSES` 无 `TYPE=MIXTURE` | ✗ 不一致 | `L06` `BLOCKER` |
| `TECH8` + 不兼容组合 | ⚠ 见 §四 | `L10` `WARN`/`INFO` |
| `XWITH` 无 `ALGORITHM=INTEGRATION` | ⚠ 需积分 | 未见对应警告类 → 只给提示 |
| 分类指标 + `ESTIMATOR=ML` | ⚠ 口径不当 | 建议 `WLSMV`；**无官方警告类佐证**，按方法学建议给出 |

> **纪律**：矩阵中标 ✗ 的必须有**官方警告类或消息原文**支撑；
> 无佐证的只能给「方法学建议」，**不得**包装成 `BLOCKER`。

---

## 六、尚未实现的语法层检查（**下版候选，不得声称已覆盖**）

| 消息 | 可判据 |
|---|---|
| `STANDARDIZED (STD, STDY, STDYX) options are not available for TYPE=EFA` | `TYPE=EFA` + `OUTPUT` 要 STD* |
| `PATTERNS option is available only when there are missing data` | `OUTPUT PATTERNS` 但无缺失处理 |
| `TYPE=RANDOM … No random effect variables were found` | `TYPE=RANDOM` 但 MODEL 无 `\|` |
| `AUXILIARY (E) CAN GIVE BIASED RESULTS…` | `AUXILIARY = x(e)` |
| `Duplicate: Y2 WITH Y1` | MODEL 段重复协方差 |
| `Y1 WITH Y1 has no effect` | MODEL 段自指 `WITH` |
| `TECH1 option is the default for multiple imputation` | `TYPE=IMPUTATION` + `TECH1` |
| `Values given in the MODEL command for EFA factors…` | EFA/ESEM + MODEL 段写值 |
| `Starting with Version 5, TYPE=MISSING is the default…` | 版本信息类 |
