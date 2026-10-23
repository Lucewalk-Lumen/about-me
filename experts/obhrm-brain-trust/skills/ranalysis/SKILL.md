---
name: r-analysis
version: 1.0.3
author: Xing Bu
description: OBHRM 智囊团（obhrm-brain-trust）— R 分析方法库（实证域资产）。108 个 R 分析脚本（01-env 环境 → 19-llm 大语言模型，覆盖描述/相关/回归/SEM/剖面/元分析/多层等方法族；其中 106 个依赖可从 CRAN 标准安装，2 个依赖已归档、需从 CRAN Archive 安装，详见 §五），每脚本遵循 G3 数据前置 / G4 环境探测(ensure_pkg 不代装) / G5 真实输出 三门禁，脚本正文按模型角色书写变量名（运行前须使数据列名与之一致），支持按 method_no / 关键词检索。面向本科生、研究生与学者，检索到的内容直接完整呈现。
description_zh: OBHRM 智囊团的 R 分析方法库。108 个可直接运行的 R 分析脚本，覆盖描述统计、回归、SEM、多层与元分析等方法族，每脚本含数据前置与环境探测门禁。
description_en: The R analysis library of the OBHRM expert team. 108 runnable R scripts covering descriptive statistics, regression, SEM, multilevel, and meta-analysis, each with data-precondition and environment-detection gates.
---

> **跨技能引用约定**：本文档以逻辑名形式引用兄弟技能（如 `` `skill:obhrm-bridge` ``），各技能的实际目录与入口脚本即 `skills/` 下的同名目录；正文给出的脚本路径为该技能内部的相对路径。

# R 分析方法库（r-analysis）— 实证域资产

> 本 skill 是 OBHRM 智囊团（obhrm-brain-trust）的**R 代码权威资产**：108 个 R 分析脚本，按方法族分 19 个目录（01-env → 19-llm），每个脚本含方法编号（`@method`）、数据前置说明（`@use_cond`）、G3/G4/G5 门禁。其中 106 个脚本的依赖可从 CRAN 标准安装，2 个（4.1.R / 4.2.R）依赖 `RQDA` / `jiebaR` 已从 CRAN 归档、需从 CRAN Archive 安装（见 §五）。纯 R 实现，不依赖 Excel / Mplus / SPSS 等任何外部分析软件。

---

## 一、资产规模与结构

- **脚本数**：108（每个脚本均含 G3 数据前置 / G4 环境探测 / G5 真实输出 三门禁）
- **目录**：`scripts/01-env/ … scripts/19-llm/`（108 个 `*.R`）+ `knowledge/_r_index.json`（索引：`nodes` 含 method_no/title/stage/deps/file/use_condition）
- **检索入口**：`scripts/query_r.py`（纯标准库，零依赖；检索内核由 `theory-library` / `scale-library` 共享 `../obhrm-bridge/kernel/library_query.py` 通用模块，匹配 / 安全边界 / JSON 契约 / 覆盖率单点实现）

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
| **G5 真实输出** | 脚本须产出真实分析结果（效应量与检验结果，非骨架、非占位） | 禁止交付无输出的占位脚本 |

### 状态口径：本库不设 verified / draft 标记

量表库与理论库为条目正文设置 `status`（`verified` / `draft`）并附出处锚点，**R 库没有这项字段，也不应补设**。原因是两者的质量承载方式不同：

- 量表 / 理论条目的正文是**文字陈述**，可能被臆造，因此需要 `status` 标记其是否已经原始文献核验；
- R 库的条目实体是**脚本本体**，正文即代码——它可被直接审阅、运行、执行门禁，不存在"文字可信度待核验"这一层不确定性。

本库的质量门控由 §二 的 **G3 / G4 / G5** 承担（G3 数据前置、G4 环境探测、G5 真实输出），以及 `04-门禁` 的实跑校验，**而非状态标记**。

**回传要求**：向主理人或用户回传 R 方法时，须给出 `method_no` 与脚本路径，并说明该脚本的 `use_condition`（数据前置）；**不得**为 R 脚本标注 `verified` / `draft`，也不得在缺失时自行编造该状态。若用户要求核验某个 R 脚本的可运行性，应实跑 G3/G4/G5 门禁并如实报告结果，而非援引状态标记。

## 三、方法族与工作流

- 本库按方法族分 19 个目录（01-env → 19-llm），每个脚本以 `method_no` 对应方法族（如 6.x=描述统计与回归、7.x=SEM、9.x=剖面分析、17.x=元分析、15.x=多层）。
- 工作流：判定方法 → `query_r.py` 取可运行脚本 → 用户按 G3 门控传入自有数据 → 产出 APA 结果。

## 四、跨域联动

- **问卷数据分析**：确认数据通道后再调用本库脚本（变量名须与 `skill:scale-library` 量表条目一致）。
- **结果回传**：本库产出 APA 统计结果，供写作环节直接取用。
- **跨库桥接**：本库 `_r_index.json` 的节点字段为 `method_no/title/stage/deps/file/use_condition`，**不含 `construct_id`**；「某构念可由哪些 R 方法检验」经 `skill:obhrm-bridge` 的**概念词表 → 方法族（`stage`）**映射实现，检索入口为 `query_concept.py`。

## 五、R 包依赖清单

108 个脚本去重后共涉及 58 个 CRAN 包（以本文件下方依赖清单为准，随脚本修订可能变动）。脚本**不代装**：缺包时按脚本提示手动安装。

```
"FactoMineR", "Hmisc", "MASS", "NCA", "QCA", "RQDA",
"RSA", "boot", "car", "cranlogs", "descr", "devtools",
"dplyr", "dsem", "effects", "effectsize", "effsize", "emmeans",
"ez", "ggplot2", "ggraph", "glmmTMB", "glmnet", "heplots",
"httr", "igraph", "installr", "jiebaR", "jsonlite", "lavaan",
"lcmm", "lme4", "lmerTest", "mclust", "mediation", "metaSEM",
"metafor", "mice", "misty", "modsem", "multcomp", "mvnormtest",
"pequod", "performance", "plyr", "poLCA", "pscl", "psych",
"pwr", "pwrss", "quanteda", "semPlot", "semPower", "semTools",
"seminr", "text2vec", "tidyLPA", "topicmodels"
```

**依赖可用性（已核实）**：上述 58 个包中，`RQDA` 与 `jiebaR` 已从 CRAN 归档，当前 CRAN 索引中已不存在，`install.packages()` 对二者会失败；受影响脚本为 `scripts/04-text/4.1.R`（RQDA）与 `scripts/04-text/4.2.R`（jiebaR）。如需运行这两个脚本，请改用 `remotes::install_version("RQDA", version = "0.3-1")` / `remotes::install_version("jiebaR", version = "0.11.1")` 从 CRAN Archive 安装。其余 56 个包均可从 CRAN 正常安装。

## 六、注意事项

- 运行 R 脚本须本机已装 R 及所需包；缺包按脚本提示手动 `install.packages()`（G4：只提示、不自动安装）。
- 脚本仅作方法实现参考，实际分析须按用户数据特征与期刊报告规范调整。
- 新增/修订脚本须同步 `_r_index.json` 的 `file/stage/deps/use_condition`。
- **脚本输出落当前工作目录（CWD）防覆盖**：`write.csv` / `saveRDS` / `save` 等写出 `dat.csv` / `dat.rds` / `dat.RData` / `sessionInfo.txt` 至运行命令所在目录；运行前务必 `cd` 到专用结果目录，避免覆盖已有同名文件或误写入工程根。
- **变量名须与脚本一致**：脚本正文按模型角色书写变量名（如 `Y` / `X` / `M` / `Z` / `W`，或手册示例列名 `sex` / `x1` 等）。运行前请确认数据列名与之一致，或按脚本内注释（「将 … 替换为 …」）把变量名改为自己的列名。G3 的 `[变量列...]` 只用于筛选参与分析的列，不做角色映射。
