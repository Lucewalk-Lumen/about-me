# 官方手册锚点索引 · official-doc-index.md

> **写法约束（硬规则）**：本文件**只写**「章节号 / 页码 / 主题 / 关键词 + **请查阅自持手册**」，
> **不放任何摘录正文**（沈证判决：官方 UG 判 `INDEX_ONLY`）。
> 页码锚点来自素材盘内 PDF 实测；用户应查阅**自持**的官方手册核对。

## 一、页码锚点（实测）

| 素材盘文件 | 对应官方文档 | 锚点 | 请查阅 |
|---|---|---|---|
| `Guide/Mplus User Guide.pdf` | Mplus **User's Guide** 第 8 版（Version 8, April 2017） | 全书 **950 页** | 自持手册全书 |
| `Guide/Chi-square…` | UG「ANALYSIS Command」章节 | **p.603** 起 | 自持手册 p.603 |
| `Guide/Tech1-Tech16…` | UG「OUTPUT, SAVEDATA, And PLOT Commands」章节 | **p.733** 起 | 自持手册 p.733 |
| `…（进阶篇）Examples Multilevel…` | UG **Chapter 9** | **p.261** 起（PDF 内 134 页） | 自持手册 p.261 |

## 二、命令段 ↔ 官方章节对照

| 命令段 | 官方主题 | 请查阅 |
|---|---|---|
| `TITLE` / `DATA` / `VARIABLE` / `DEFINE` | 输入语法总览 | 自持 UG 相应章 |
| `ANALYSIS` | 分析设定（`TYPE` / `ESTIMATOR` / `ALGORITHM`） | 自持 UG「ANALYSIS Command」（p.603 起） |
| `MODEL` | 模型陈述 | 自持 UG「MODEL Command」 |
| `MODEL INDIRECT` | 间接效应 | 自持 UG「MODEL INDIRECT Command」 |
| `MODEL CONSTRAINT` | 参数约束与定义新参数 | 自持 UG「MODEL CONSTRAINT Command」 |
| `MODEL PRIORS` / `MODEL POPULATION` / `MODEL MISSING` | 贝叶斯先验 / 蒙特卡洛总体 / 缺失模型 | 自持 UG 相应 Command 节 |
| `OUTPUT` / `SAVEDATA` / `PLOT` | 输出、保存、绘图 | 自持 UG「OUTPUT, SAVEDATA, And PLOT Commands」（p.733 起） |
| `MONTECARLO` | 蒙特卡洛模拟研究 | 自持 UG「MONTECARLO Command」 |

## 三、技术附录（TECH 输出）对照

| TECH 号 | 主题 | 请查阅 |
|---|---|---|
| `TECH1` | 模型各矩阵（参数化） | 自持 UG 技术附录 |
| `TECH8` | 迭代记录 | 自持 UG 技术附录 |
| `TECH11` | 似然比检验（LRT） | 自持 UG 技术附录 |
| `TECH14` | 标准化残差相关 | 自持 UG 技术附录 |
| `Tech1–Tech16` 合计 | 输出扩展 | `Guide/Tech1-Tech16…`（UG「OUTPUT, SAVEDATA, And PLOT Commands」p.733 起） |

## 四、版本与勘误

| 文档 | 用途 | 版本口径 |
|---|---|---|
| UG 第 8 版（April 2017） | 语法与命令段权威 | 语法侧（官方指引中与 9.1 Addendum **并列**） |
| `AddendumV9.pdf` / `Addendum 9.1.pdf` | 9.0 / 9.1 新增特性 | **语法侧基准 = 9.1 语言代次** |
| 9.1.1 补丁（2026-09-16） | 修 9.1 的问题（**不改语言特性**） | **官网当前最新版本号** |
| 官方 FAQ（145 条条目） | 常见问题**条目标题**索引 | 报错诊断法理路径（M5-b） |

> ⚠ **版本不可混用**：语法侧用 **9.1 语言代次**（官网最新版本号 **9.1.1**），
> 输出解析侧实证区间为 **6.0–8.8**。详见 `INDEX.md` §六 与 `../references/version-notes.md` §1.1。

## 五、获取途径（供用户自行核对）

- User's Guide 与各章示例：`https://www.statmodel.com/usersguide/`
- 版本历史（核对最新版本号）：`https://www.statmodel.com/verhistory.shtml`
- 版本 Addendum：`https://www.statmodel.com/`（Download 区）
- 官方 FAQ：`https://www.statmodel.com/faq.shtml`

> 本包**不内置**上述 PDF / FAQ 原文，仅登记锚点。请以**自持**版本为准。
