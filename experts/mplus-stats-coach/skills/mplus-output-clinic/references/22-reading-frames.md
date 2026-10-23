# 22 · `.out` 判读框架（M3 的骨架）

> 依据：`scripts/extract_out.py` 的区块切分 + 官方 555 份 `.out` 实测顺序。
> 本文件只给**读的顺序与锚点**；指标阈值见 `21-fit-indices.md`，警告见 `31-warning-taxonomy.md`。

---

## 一、读 `.out` 的第一原则：**不要顺读**

新手按行号从上往下读，会在 `INPUT INSTRUCTIONS`（几十行复述你的输入）里耗掉大半注意力，
等读到 `MODEL RESULTS` 时已经没有配额分辨数字可信与否。

**正确顺序是按证据强度倒着读**——先确认「这个解能不能信」，再谈「数字是多少」：

| 步 | 锚点行 | 一句话判据 | 不通过怎么办 |
|---|---|---|---|
| 1 | `INPUT READING TERMINATED NORMALLY` **与** `THE MODEL ESTIMATION TERMINATED NORMALLY` | 两行**都在**才算跑完 | 缺任一 → 停止解读，先查输入/报错 |
| 2 | `QUALITY OF NUMERICAL RESULTS` | 迭代是否收敛、有无「未收敛」提示 | 未收敛 → **所有后续数字都不可引用** |
| 3 | `RANDOM STARTS RESULTS`（仅混合模型） | 最佳对数似然是否**被复制** | 未复制 → 局部极大，须增随机起点重跑 |
| 4 | `MODEL FIT INFORMATION` | 拟合是否可接受（阈值见 21） | — |
| 5 | `MODEL RESULTS` | 参数点估计 / 标准误 / 显著性 | 必须先过第 2 步 |

> ⚠ **两个终止符不是一回事，别混。**
> `INPUT READING TERMINATED NORMALLY` = **读输入**成功了；`THE MODEL ESTIMATION TERMINATED NORMALLY` = **估计**成功了。
> 语料实测有 `NO_TERMINATION_MARKER`（38 份，见 `knowledge/INDEX.md` §5.1）—— 那些文件**跑完了**但没打印那行回显，
> **不得据此说运行失败**。

---

## 二、五种分析类型的区块顺序（实测锚点）

区块是**分层出现**的：上层分析全有，下层分析逐级追加。用「是否出现某锚点」判定类型，比读 `.inp` 更快。

### 2.1 基准层 —— 任何分析都有

```
INPUT INSTRUCTIONS            ← 含你的输入回显 + 输入层 WARNING 汇总行
INPUT READING TERMINATED NORMALLY
SUMMARY OF ANALYSIS           ← 关键：样本量、估计器、类型、缺失处理
UNIVARIATE SAMPLE STATISTICS  ← 关键：各变量 N / 均值 / 标准差 / 极值
THE MODEL ESTIMATION TERMINATED NORMALLY
MODEL FIT INFORMATION         ← 拟合（见 21）
MODEL RESULTS                 ← 参数
QUALITY OF NUMERICAL RESULTS  ← 解的可信度
```

实例：`ex5.1`（CFA/SEM）9 个表头、`ex6.1`（增长）9 个、`ex11.1`（贝叶斯）12 个。

### 2.2 多层层 —— 追加 `SUMMARY OF DATA`

```
… UNIVARIATE SAMPLE STATISTICS
SUMMARY OF DATA               ← 追加：簇数 / 簇内样本量分布 / 层间变量清单
THE MODEL ESTIMATION TERMINATED NORMALLY …
```

多层专属**警告高发区**：`W03`（簇内无变异）、`W13`（跨层未引用）、`W23` 族（预测变量指整体观测变量而非潜变量）。

### 2.3 混合层 —— 追加随机起点 + 类别计数 + 分类质量

```
… UNIVARIATE SAMPLE STATISTICS
RANDOM STARTS RESULTS RANKED FROM THE BEST TO THE WORST LOGLIKELIHOOD
  THE BEST LOGLIKELIHOOD VALUE HAS BEEN REPLICATED.   ← 这行是成败锚点
THE MODEL ESTIMATION TERMINATED NORMALLY
MODEL FIT INFORMATION
FINAL CLASS COUNTS AND PROPORTIONS FOR THE LATENT CLASSES
  BASED ON THE ESTIMATED MODEL
  BASED ON ESTIMATED POSTERIOR PROBABILITIES
  BASED ON THEIR MOST LIKELY LATENT CLASS MEMBERSHIP
CLASSIFICATION QUALITY        ← 关键：熵 / 平均后验概率
MODEL RESULTS
LOGISTIC REGRESSION ODDS RATIO RESULTS
QUALITY OF NUMERICAL RESULTS
TECHNICAL 1 OUTPUT
TECHNICAL 8 OUTPUT            ← 仅特定 TYPE 组合才有（见 13-estimator-guide.md）
```

**「三类计数」必须一起看**：同一批数据在三套依据下会给出**三个不同的人数分配**。
只报其中一个（尤其只报「基于估计模型」那个）是不完整的表述。熵与平均后验概率在 `CLASSIFICATION QUALITY`。

实例：`ex7.1` 20 个表头、`ex8.1` 21 个。

### 2.4 蒙特卡洛层 —— 追加 `FOR THE FIRST REPLICATION` 与 `TECHNICAL 9`

```
INPUT INSTRUCTIONS
INPUT READING TERMINATED NORMALLY
SUMMARY OF ANALYSIS
SUMMARY OF DATA FOR THE FIRST REPLICATION
SUMMARY OF MISSING DATA PATTERNS FOR THE FIRST REPLICATION
COVARIANCE COVERAGE OF DATA FOR THE FIRST REPLICATION
SAMPLE STATISTICS FOR THE FIRST REPLICATION
MODEL FIT INFORMATION
MODEL RESULTS
QUALITY OF NUMERICAL RESULTS
TECHNICAL OUTPUT
TECHNICAL 9 OUTPUT            ← 覆盖率表：真值 vs 估计、95% 覆盖率
```

**读蒙特卡洛输出的误区**：上半部分是**第一次复制**的常规输出，容易被误当研究结论。
真正要读的是 `TECHNICAL 9 OUTPUT` 的**覆盖率**（名义 95% 区间实际覆盖多少）。
另注：蒙特卡洛输出常**不打印** `THE MODEL ESTIMATION TERMINATED NORMALLY`（见 §一 注）。

### 2.5 贝叶斯层 —— 拟合块位置不变，但内容不同

顺序与 2.1 相同，但 `MODEL FIT INFORMATION` 内是 **PPP / BIC / DIC**（而非 CFI/RMSEA），
`MODEL RESULTS` 给的是**后验**（均值 / 中位数 / 95% 可信区间 / 单尾 p），**不是** 标准误与 z 值。
**不得用频数派的「p < .05」口径去读贝叶斯输出的 `P-value`**（那是单尾后验概率）。

实例：`ex11.1`。

---

## 三、每个区块「看什么 / 不看什么」

| 区块 | 要看 | 不要用来 |
|---|---|---|
| `INPUT INSTRUCTIONS` | 确认 Mplus 收到的输入与你写的一致；输入层 WARNING 汇总 | 谈结果 |
| `SUMMARY OF ANALYSIS` | **样本量 / 估计器 / TYPE / 缺失处理** —— 判断数字可比性的唯一依据 | 谈模型好坏 |
| `UNIVARIATE SAMPLE STATISTICS` | 变量描述、极端值、编码范围 | 谈效应 |
| `MODEL FIT INFORMATION` | 拟合（阈值见 21）；**注意是否给出稳健校正版** | 跨样本比信息准则 |
| `FINAL CLASS COUNTS` | 三套计数 + 最小类占比 | 只用其中一套下结论 |
| `CLASSIFICATION QUALITY` | 熵 / 平均后验 | 当拟合指标用 |
| `MODEL RESULTS` | 点估计 + 标准误 + 显著性 | 在未收敛时引用 |
| `QUALITY OF NUMERICAL RESULTS` | 收敛状态、迭代数、对数似然 | 当拟合指标 |
| `TECHNICAL n OUTPUT` | 按需（TECH1 初始值、TECH8 优化史、TECH9 覆盖率） | 整段复述给用户 |

---

## 四、六条常见误读

1. **把 `SUMMARY OF ANALYSIS` 的样本量当最终 N。** 若存在缺失且用 `TYPE=MISSING`，实际进入分析的 N 见 `SUMMARY OF DATA` / 各变量 `NUMBER OF OBSERVATIONS`。
2. **把「没打印 NORMALLY」当失败。** 见 §一 注。
3. **只报一套类别计数。** 见 §2.3。
4. **蒙特卡洛只看第一复制。** 见 §2.4。
5. **用频率派口径读贝叶斯 `P-value`。** 见 §2.5。
6. **忽略 `QUALITY OF NUMERICAL RESULTS` 直接引数字。** 未收敛的估计值在语法上完全合法，肉眼看不出来——**必须靠这一步拦住**。

---

## 五、与结构化层的映射

本文件描述的区块，在 `cases.jsonl` 中以 `out_blocks` 布尔标记存在（10 个键，语义见 `knowledge/INDEX.md` §5.2）。
**注意**：`out_blocks.errors` 表示「存在行首 `*** ERROR`」，官方 555 份 **0 例**；
它**不是**「文中出现过 error 字样」。`out_status` 表示运行完成情况（§5.1）。两者都**不是质量判断**。

逐条数值一律走 L2：`grep '"id": "<case-id>"' knowledge/facts/case-facts.jsonl`，**不读整个 facts 文件**。
