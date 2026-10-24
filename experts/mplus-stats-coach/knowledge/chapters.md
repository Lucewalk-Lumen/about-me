# 官方章节映射表 · chapters.md

> 生成源：`knowledge/cases.jsonl`（**519 条**，逐条实测）
> 索引构建脚本：`scripts/build_index.py`（构建期）
> ⚠ 本表所有数字均为**实测**，非估计。任何数字与本表冲突时以本表为准。

## 一、按章实测分布

| 章 | 章名（官方原文） | `.inp` | example | montecarlo | 带 `.out` | 带警告 | 有拟合/信息指标 | 主要模型族 |
|---|---|---:|---:|---:|---:|---:|---:|---|
| Ch3 | Regression and Path Analysis | 37 | 19 | 18 | 37 | 0 | 18 | MONTECARLO, CONSTRAINT, DSEM_RI, MEDIATION |
| Ch4 | Exploratory Factor Analysis | 16 | 8 | 8 | 16 | 3 | 8 | CFA_SEM, MONTECARLO, EFA_ESEM, MULTILEVEL |
| Ch5 | Confirmatory Factor Analysis and Structural Equation Modeling | 77 | 41 | 36 | 77 | 12 | 41 | CFA_SEM, MONTECARLO, CONSTRAINT, DSEM_RI |
| Ch6 | Growth Modeling and Survival Analysis | 59 | 30 | 29 | 59 | 7 | 22 | GROWTH, MONTECARLO, CFA_SEM, BAYES |
| Ch7 | Mixture Modeling with Cross-Sectional Data | 58 | 29 | 29 | 58 | 13 | 29 | MIXTURE, LCA_LPA, MONTECARLO, CATEGORICAL |
| Ch8 | Mixture Modeling with Longitudinal Data | 36 | 19 | 17 | 35 | 3 | 18 | MIXTURE, GROWTH, LCA_LPA, MONTECARLO |
| Ch9 | Multilevel Modeling with Complex Survey Data | 94 | 51 | 43 | 94 | 20 | 24 | MULTILEVEL, DSEM_RI, BAYES, MONTECARLO |
| Ch10 | Multilevel Mixture Modeling | 28 | 15 | 13 | 28 | 5 | 15 | MULTILEVEL, MIXTURE, LCA_LPA, MONTECARLO |
| Ch11 | Missing Data Modeling and Bayesian Analysis | 25 | 15 | 10 | 23 | 7 | 5 | GROWTH, CFA_SEM, MONTECARLO, MISSING |
| Ch12 | Monte Carlo Simulation Studies | 14 | 2 | 12 | 14 | 4 | 1 | MONTECARLO, CFA_SEM, GROWTH, MULTILEVEL |
| **UG 小计** | — | **444** | **229** | **215** | **441** | **74** | **181** | — |
| supp | 补充集（Penn 63 + Web Notes 12） | 75 | 53 | 22 | 75 | 16 | — | CONSTRAINT, CFA_SEM, BAYES, MONTECARLO |
| **合计** | — | **519** | **282** | **237** | **516** | **90** | — | — |

**要点**
- **Ch9 最大**（94 例）——多层 + 复杂抽样，也是警告最集中的一章（20 例带警告）。
- **Ch5 是 CFA/SEM 主战场**（77 例，41 例给出拟合指标）。
- **Ch7/Ch8/Ch10 是混合建模三章**——合计 122 例，内含 `LCA_LPA` 96 + `LTA` 31，**这是用户点名能力（潜类别/潜剖面）的官方一手来源**。
- **Ch12 是蒙特卡洛专章**（12/14 为 `mcex*`），对应「研究设计 / 检验力规划」能力。
- **Ch11 是唯一版本混杂章**：输出中 5 份产自 `Mplus 6.1`（2010），其余产自 `8.8`（2022）。

## 二、逐章 URL（`source_url` 生成规则）

```
UG 章 N  →  https://www.statmodel.com/usersguide/chapter<N>.shtml
补充集   →  https://www.statmodel.com/download/<原始文件名>
```

> ⚠ **Ch13 不存在**：`chapter13.shtml` 会**静默回落到 Chapter 3**。
> 若按 3–13 抓取会**重复计数**并污染索引。官方示例章**止于 Ch12**（实测）。

## 三、目录布局（包内）

```
knowledge/official/
├── ug/ch<N>/<stem>.inp        444 份（Ch3–12）
└── supp/<文件名>.inp           75 份（penn__* 63 / webnote__* 12）
```

命名约定：
- UG 的 `id` = `ug-ch<N>-<stem>`，例：`ug-ch5-ex5.11`
- 补充集 `id` = `supp-<group>-<stem>`，组名取文件名 `__` 前缀（`penn` / `webnote`）

## 四、章内配对情况

| 项 | 数 | 说明 |
|---|---:|---|
| `.inp` 总数 | 519 | 全部入包 |
| 有配对 `.out` | 516 | **99.4%** |
| 无配对 | 3 | Ch8 ×1、Ch11 ×2（`.out` 未随章发布） |
| `.out` 原文入包 | **0** | 见 `license-register.md`：只抽事实入 `facts/case-facts.jsonl` |

> **`.out` 自含输入全文**：官方 `.out` 的 `INPUT INSTRUCTIONS` 段回显 `.inp` 原文（实测 441/441 = 100%），
> 因此「一取二」成立。但本包**只把 `.out` 抽成结构化事实**（`facts/case-facts.jsonl`），不内置其原文。
