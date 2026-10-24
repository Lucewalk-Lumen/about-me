---
name: r-analysis
version: 1.0.0
author: "Xing Bu"
description: OBHRM 研究协作团 — R 分析方法库（实证域资产）。108 个可运行的 R 分析脚本（01-env 环境 → 19-llm 大语言模型，覆盖描述/相关/回归/SEM/剖面/元分析/多层等方法族），每脚本遵循 G3 数据前置 / G4 环境探测(ensure_pkg 不代装) / G5 真实输出 三门禁，脚本正文按模型角色书写变量名（运行前须使数据列名与之一致），支持按 method_no / 关键词精确检索。
---
> **跨技能引用约定**：本文档以逻辑名形式引用兄弟技能（如 `` `skill:peer-review` ``），不使用逻辑名映射表，重命名或移动技能时按相对路径同步更新。
# R 分析方法库（r-analysis）— 实证域资产
> 本 skill 是 OBHRM 研究协作团的**R 代码真源资产**：108 个可运行的 R 分析脚本，按方法族分 19 个目录（01-env → 19-llm），每个脚本含方法编号（`@method`）、数据前置说明（`@use_cond`）、G3/G4/G5 门禁。纯 R 实现，不依赖 Excel / Mplus / SPSS 等任何外部分析软件。
---

## 一、资产规模与结构

- **脚本数**：108（每个脚本均含 G3 数据前置 / G4 环境探测 / G5 真实输出 三门禁）
- **目录**：`scripts/01-env/ … scripts/19-llm/`（108 个 `*.R`）+ `knowledge/_r_index.json`（索引：`nodes` 含 method_no/title/stage/deps/file/use_condition）
- **检索入口**：`scripts/query_r.py`（纯标准库，零依赖；检索内核由 `theory-library` / `scale-library` 共享 `../obhrm-bridge/kernel/library_query.py` 通用模块，匹配 / 安全边界 / JSON 契约单点实现）

```bash
python3 scripts/query_r.py "regression"          # 关键词(中/英)检索方法
python3 scripts/query_r.py "6.1" --full          # method_no 精确 + 脚本路径与门控
python3 scripts/query_r.py "中介" --limit 5
python3 scripts/query_r.py "1.1" --json          # 输出原始 JSON
```

## 二、R 脚本三门禁（强制）

| 门禁 | 规则 | 违反后果 |
|------|------|----------|
| **G3 数据前置** | 脚本首行读 `commandArgs`，无数据文件即 `stop()` 提示用法（如 `Rscript 6.1.R 数据.csv [变量列...]`） | 禁止在裸脚本上硬跑 |
| **G4 环境探测** | `ensure_pkg()` 检测缺失包时 `stop()` 提示 `install.packages(...)`，**绝不自动安装** | 用户须显式安装依赖 |
| **G5 真实输出** | 脚本须产出真实分析结果（非骨架），经合成数据实跑验证 | 禁止交付无输出的占位脚本 |

## 三、与 data-analysis 域的关系

- `skill:data-analysis` 是**方法学路由**（D1-D4 定量一手 / M1-M5 元分析 / Q1-Q5 质性），讲"研究结论怎么证明成立"；本库是其中**定量路径的具体 R 实现**，按 `method_no` 对应 D/M 方法族（如 6.x=描述统计与回归、7.x=SEM、9.x=剖面分析、17.x=元分析、15.x=多层）。
- 工作流：data-analysis 域判定方法 → 本库 `query_r.py` 取可运行脚本 → 用户按 G3 门控传入自有数据 → 产出 APA 结果回传写作方。


**依赖可用性（已核实）**：`RQDA` 与 `jiebaR` 已从 CRAN 归档，当前 CRAN 索引中已不存在，`install.packages()` 对二者会失败；受影响脚本为 `scripts/04-text/4.1.R`（RQDA）与 `scripts/04-text/4.2.R`（jiebaR）。如需运行，请改用 `remotes::install_version("RQDA", version = "0.3-1")` / `remotes::install_version("jiebaR", version = "0.11.1")` 从 CRAN Archive 安装。其余包均可从 CRAN 正常安装。

## 四、跨域联动

- **问卷数据分析（D0/D1 → 本库）**：`skill:data-analysis` 的 D0 试跑确认通道后，调用本库对应脚本（变量名须与 `skill:scale-library` 量表条目一致）。
- **论文结果回传（D→A5）**：本库产出 APA 统计结果 + 假设裁决，经 `skill:paper-writing` 入正文。
- **审稿反向诊断（C→本库）**：`skill:peer-review` 评估稿件分析严谨性时，对照本库方法门禁核查复现可行性。
- **跨库桥接**：`skill:knowledge-graph` 的 `r_applicability` 按库语义归类（general / theory / scale）标注每个 R 方法适用的库；`construct_ids` 关联待回填，当前不提供"某构念可由哪些 R 方法检验"的构念级检索。

## 五、注意事项

- 运行 R 脚本须本机已装 R 及所需包（G4 不代装）；缺包按脚本提示用 R 的包安装函数安装所需依赖。
- 脚本仅作方法实现参考，实际分析须按用户数据特征与期刊报告规范调整。
- 新增/修订脚本须同步 `_r_index.json` 的 `file/stage/deps/use_condition`。
- **脚本输出落当前工作目录（CWD）防覆盖**：`write.csv` / `saveRDS` / `save` 等写出 `dat.csv` / `dat.rds` / `dat.RData` / `sessionInfo.txt` 至运行命令所在目录；运行前务必 `cd` 到专用结果目录，避免覆盖已有同名文件或误写入工程根。
- 依赖固化：本库聚合依赖以各脚本的 `@deps` 字段声明，并由 `_r_index.json` 汇总（G4 门禁仅探测、绝不代装）；本包不随附 renv.lock，如需可复现环境请用户自行 `renv::init()`。
