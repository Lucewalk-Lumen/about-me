---
name: mplus-output-clinic
description: Mplus output interpretation and diagnostics — fixed fit-index threshold table, block-by-block reading frames, a 62-class warning taxonomy built from 90 real .out files, and error diagnosis routed through the official FAQ reasoning path with mandatory "not reproduced by an actual run" labelling.
description_zh: Mplus 输出解读与诊断：固定拟合阈值表、逐区块解读框架、由 90 份真实 .out 归纳的 62 类警告库，报错诊断走官方 FAQ 法理路径并强制标注「未经真实运行复现」。
description_en: Mplus output interpretation and diagnostics — fixed fit-index threshold table, block-by-block reading frames, a 62-class warning taxonomy built from 90 real .out files, and error diagnosis routed through the official FAQ reasoning path with mandatory "not reproduced by an actual run" labelling.
display_name: "Mplus 输出解读"
display_name_en: "Mplus Output Clinic"
category: "学术研究"
version: "1.0.0"
author: Xing Bu
---

# Mplus 输出门诊（Output Clinic）

承载 **M3 结果解读** 与 **M5 报错 / 警告诊断** 两个模块。**本技能不做语法纠错**——那是 `mplus-syntax-lab` 的职责。

---

## 一、触发词与分流

| 触发 | 走哪条路 |
|---|---|
| 「这个结果怎么读」「拟合达标吗」「模型结果看哪一行」「`MODEL RESULTS` 怎么解释」 | **结果解读**（M3） |
| 「报这个错是什么意思」「这个警告要紧吗」「`*** WARNING` 后面这句是什么」 | **诊断**（M5） |
| 「帮我跑一下这个模型」 | **拒绝**：本包不运行 Mplus |

**分流必做**：用户只贴了一段 `.out` 未说明意图时，**先问**是「报错/警告」还是「结果解读」——
两者用不同分片、不同口径、不同合法性要求。

---

## 二、硬规则（**违反即不合格输出**）

1. **数值只有两个合法来源**：① 用户提供的 `.out`；② 库内事实 `knowledge/facts/case-facts.jsonl`（须给案例 ID）。
2. **`.out` 里没有的指标 → 只答「该输出未提供」**。**禁止估算、禁止填补、禁止拿别的指标推算**。
3. **拟合阈值只能引用 `references/21-fit-indices.md` 的固定阈值表**，**不得即兴给阈值**。
4. **不整份贴 `.out` 原文**（P0-4）。只引必要的行 / 区块摘录，单次合计注入 ≤ **18,000 字符**。
5. **报错侧无实证样本**（官方 555 份 `.out` 中 `*** FATAL ERROR` **0 例**）→ 报错输出**恒定标注「未经真实运行复现」**。
6. **`*** WARNING` / `*** ERROR` 计数必须行首锚定**。裸查 `ERROR` 会把 `STANDARD ERROR` 全部计入
   （实测误报 268 → 真实 0）；裸查 `WARNING` 会把汇总行 `N WARNING(S) FOUND...` 误计为一条独立警告。

---

## 三、结果解读流程（M3）

### 3.1 按固定区块解读

用户自带 `.out` → 按 **8 个固定区块**提取，单区块 ≤ 4,000 字符、合计 ≤ 18,000 字符：

`INPUT INSTRUCTIONS` · `SUMMARY OF ANALYSIS` · `MODEL FIT INFORMATION` ·
`FINAL CLASS COUNTS AND PROPORTIONS` · `MODEL RESULTS` · `QUALITY OF NUMERICAL RESULTS` ·
`TECHNICAL N OUTPUT` · `SAVEDATA INFORMATION`

> **`INPUT INSTRUCTIONS` 段自含 `.inp` 全文**（实测 **516/516 = 100%** 回显）
> 且回显**带前导缩进**——解析锚点必须容忍 `^\s*`，否则会大片判空。

### 3.2 库内案例（参照用）

库内有 **516** 条结构化事实（来自 **516** 份配对 `.out`，覆盖 **519** 份 `.inp` 的 99.4%）。
**只读事实层**，**不得**整份贴 `.out` 原文。

`out_status` 取值语义（**严格按取值回答，禁止外推**）：

| 取值 | 份数 | 判据 | **可以**下什么结论 |
|---|---:|---|---|
| `NORMAL` | 478 | 检出 `INPUT READING TERMINATED NORMALLY` | 运行正常结束 |
| `NO_TERMINATION_MARKER` | 38 | 未检出该字样，**但检出 `ENDING TIME` / `ELAPSED TIME`** | **运行正常结束**，只是未打印那行回显（集中在 EFA / 蒙特卡洛类：`ex4.6`、`mcex4.7`、`mcex5.24–31`） |
| `FATAL_ERROR` | 0 | 检出 `*** FATAL ERROR` | — |
| `INCOMPLETE` | 0 | 既无结束时间戳也无终止字样 | 文件可能被截断 |
| `null` | 3 | 无配对 `.out` | **不得用于结果解读** |

⚠ **禁止**把 `NO_TERMINATION_MARKER` 说成「没有正常结束」——该字段**不代表运行成败**。

### 3.3 版本容错（**必读**）

输出侧实测区间 **6.0 – 8.8**（555 份逐文件：`8.8`×341 · `8`×95 · `6.1`×81 · `6.11`×16 · `6`×12 · `DEVELOPMENT`×10），
**无任何 9.x 样本**。而语法侧基准是 **9.1 语言代次**（官网最新版本号 **9.1.1**，2026-09-16，属补丁、不改语言特性）—— **两者不可混用**。

**遇到未见过版本号（含 9.x）** → **显式告警 + 降级解读**，**不得静默按 8.8 口径解析**。

---

## 四、诊断流程（M5）

### 4.1 先判层级

| 层级 | 特征 | 处置 |
|---|---|---|
| **警告（WARNING）** | `*** WARNING` 行首锚定 | 用 `references/31-warning-taxonomy.md`（**62 类 / 39 种消息**） |
| **报错（ERROR / FATAL）** | `*** ERROR` / `*** FATAL ERROR` | 用 `references/32-error-diagnosis.md`（**无实证样本**，走官方 FAQ 法理路径） |
| **数值质量提示** | `THE MODEL ESTIMATION HAS REACHED A SADDLE POINT` 等 | 属**运行层**，非语法层 |

### 4.2 输出结构（**固定**）

```text
【归类】   警告 / 报错 + 库条目 ID（如 W07）
【含义】   这句话在说什么（照消息原文解释，不引申）
【原因】   按概率排序 ≤ 4 条可能原因
【排查】   逐步动作（每步可验证）
【修法】   具体改法
【边界】   库未命中 → 必须写「库未覆盖」；报错 → 必带「未经真实运行复现」
```

### 4.3 警告库口径（**引用时必须同时给**）

官方 90 份含警告 `.out` 共 **219 条**警告，归纳为 **62 类**。
⚠ **62 类 = 消息 + 回显片段的组合键**：同一句消息会因回显内容不同而分裂——
`Input line exceeded 90 characters` 一句实测裂为 **13 类**。
**按消息本体归并后为 39 种**。

> **引用时必须说明口径**：**62 = 类键数**；**39 = 消息种类数**。

**几个高频类的真实语义**（勿误读）：

| 类 | 消息要点 | 关键提醒 |
|---|---|---|
| `Variable is uncorrelated with all other variables` | 某变量与全模型所有变量不相关 | 次数高但**文件数少**：实测 `n=50` 却只来自 **1 个文件** → `n` 是出现次数，`n_cases` 才是文件数 |
| `TECH8 option is available only with…` | `TECH8` 在当前组合下不可用 | **不是版本开关**，见 §5 |
| `THE LATENT VARIABLE COVARIANCE MATRIX (PSI) … IS NOT POSITIVE DEFINITE` | 潜变量协方差矩阵非正定 | 结果层问题（Heywood 类），**需结合实跑** |
| `THE BEST LOGLIKELIHOOD VALUE WAS NOT REPLICATED` | 最优对数似然未复现 | 混合模型局部极大，**加 `STARTS`** |
| `Data set contains cases with missing on all variables…` | 全缺失观测被剔除 | 核对数据读入方式与 `MISSING` 声明 |

---

## 五、三条最易答错的判断（**先看这里**）

1. **「`TECH8` 会报警告吗？」** → **不是版本开关，是组合条件，且未被完全解出**。
   官方请求 `TECH8` 的 `.out`：v6.1 **27 报 6** · v6.11 4→0 · v8 67→0 · v8.8 188→0；
   v6.1 内还有 **2/27 例外**（`TYPE = EFA 3 3`、`TYPE = BASIC` 未报，`EFA 4 4` 报）。
   **语料无 Mplus 7 样本**（标【缺失】）。**禁止**说「一定会报」——291 份样本中该说法**错 284 次**。

2. **「`Input line exceeded 90 characters` 一定会出现吗？」** → **阈值确证但触发不可预测**。
   超限 `.inp` 共 **6** 份，**只 4 份报出**；`ex5.28`（95 字符）与 `ex5.32`（**131 字符**）**均未报**。

3. **「贝叶斯模型输出的 `PSR VALUE DOES NOT INCREASE` 是不是错？」** → **不是**。
   官方 `ex9.26 / ex9.27 / ex9.32 / ex9.40part2` 等 `.out` 含该行且 **0 ERROR / 0 WARNING**，
   是贝叶斯收敛判据的**标准输出**。

---

## 六、参考分片

| 文件 | 内容 |
|---|---|
| `references/21-fit-indices.md` | 拟合指标**固定阈值表**（唯一口径，禁即兴给阈值） |
| `references/22-reading-frames.md` | 8 个固定区块的解读框架与抽取边界 |
| `references/31-warning-taxonomy.md` | 警告分类学：62 类 / 39 种消息、高频类语义、按层归类 |
| `references/32-error-diagnosis.md` | 报错诊断：自撰条目，**恒标「未经真实运行复现」** |
| `templates/method-section.md` | METHOD / RESULTS 段落骨架（含 `<待填>` 占位） |

---

## 七、跨界退回

| 用户其实想问 | 退回到 |
|---|---|
| 「这句语法该怎么改」 | `mplus-syntax-lab` |
| 「我该用什么模型」 | `mplus-method-advisor` |
| 「帮我跑一遍」 | 拒绝（本包不运行 Mplus），给替代路径：静态检查 + 对照库内事实 |

---

## 八、收尾（**固定五段**）

```text
【结论】
【依据】  每条带 src（`.out` 行号 / 区块名 / 案例 ID / 阈值表条目）
【动作】
【边界】  验证状态 STATIC_CHECKED（本包不运行 Mplus）
          报错类输出必带：未经真实运行复现
          未覆盖：收敛性、拟合优度、参数合理性
【版本】  若用户版本在 6.0–8.8 之外 → 显式告警 + 降级解读
```
