---
name: scale-library
version: 1.0.3
author: Xing Bu
description: OBHRM 智囊团（obhrm-brain-trust）— 量表知识库（测量域资产）。601 个组织行为/人力资源管理量表（中英变量名+构念+维度+条目+计分方式+取用文献，条目带 verified/draft 生命周期），支持按 construct_id / 关键词 / scale_id 精确检索，供问卷设计、假设变量操作化、量表选型与引用。面向本科生、研究生与学者，检索到的内容直接完整呈现。
description_zh: OBHRM 智囊团的量表知识库。601 个组织行为与人力资源管理量表，含维度、条目、计分方式与出处，供问卷设计与量表选型。
description_en: The scale library of the OBHRM expert team. 601 organizational-behavior and HRM scales with dimensions, items, scoring rules, and sources, supporting questionnaire design and measure selection.
---

> **跨技能引用约定**：本文档以逻辑名形式引用兄弟技能（如 `` `skill:obhrm-bridge` ``），各技能的实际目录与入口脚本即 `skills/` 下的同名目录；正文给出的脚本路径为该技能内部的相对路径。

# 量表知识库（scale-library）— 测量域资产

> 本 skill 是 OBHRM 智囊团（obhrm-brain-trust）的**量表权威资产**：601 个量表，每条含 `variable_en/variable_zh`（中英变量名）、`construct_id`（构念归一化标识）、`dimensions`（维度+题数+计分）、`items`（完整条目文本）、`reference_used`（**条目文本的取用文献**，即本库从哪篇文献录入，**不是量表的原始出处**）。601 条中 587 条 `verified`、14 条 `draft`（来源字段为占位符「（无）」，**资料本身真实、可引用出结果，但输出须显著标记「来源未确证」，严禁编造**，见条目 `note`）。上述 587/14 为当前快照，实际以 `_scale_index.json` 检索脚本即时统计的覆盖率为准。

---

## 一、资产规模与结构

- **量表数**：601（587 verified / 14 draft；每次检索即时统计并输出覆盖率）
- **目录**：`knowledge/scales/entities.json`（601 条合并存储，按 `scale_id` 为键的单一文件）+ `knowledge/_scale_index.json`（索引：`nodes` 含 scale_id/construct_id/variable_en/variable_zh/n_dims/n_items/reference_used/status/note）
- **存储口径**：合并存储 `entities.json` 是量表条目的**唯一来源**。本包不随附逐条单文件（`Sxxx.json`），以避免包内文件数膨胀到审核上限之外；检索脚本与 agent 均自合并存储按 `scale_id` 取正文。
- **检索入口**：`scripts/query_scales.py`（纯标准库，零依赖；检索内核由 `theory-library` / `r-analysis` 共享 `../obhrm-bridge/kernel/library_query.py` 通用模块，匹配 / 安全边界 / JSON 契约 / 覆盖率单点实现）

```bash
python3 scripts/query_scales.py "trust"              # 关键词(中/英/构念)检索
python3 scripts/query_scales.py "S001" --full        # scale_id 精确 + 完整条目(含 items)
python3 scripts/query_scales.py "self determination" # 英文构念词
python3 scripts/query_scales.py "S001" --json        # 输出原始 JSON(供程序消费)
```

> **查询铁律**：601 条量表正文不可一次载入上下文。任何"找量表/查量表条目"需求**必须先经 `query_scales.py` 检索索引**，按返回的 `scale_id` 再按需从合并存储取该条正文。禁止凭记忆编造量表名/条目/计分方式。

## 二、单条量表记录结构（合并存储 `entities.json` 中的单条）

| 字段 | 含义 |
|------|------|
| `construct_id` | 构念归一化 slug（量表侧带 `_scale` / `_questionnaire` 后缀；与理论库的命名体系不同，两库不可直接按标识关联） |
| `dimensions` | 维度列表，每项含 `name_zh/name_en/item_count/item_range/scoring` |
| `items` | 条目列表，每项含 `no/text/dimension/reverse` |
| `reference_used` | **条目文本的取用文献**（作者, 年, 期刊，本库录入所据），**不是量表的原始出处**；量表原始出处见 `background`。**正式引用请核对原始文献，不得直接引用本字段** |
| `status` | 条目生命周期状态（与 `schema.json` 的 `enum` 一致）：`verified`（已核验可用于学术产出）/ `draft`（来源尚未确证，资料本身真实、可引用出结果，但输出须显著标记「来源未确证」，严禁编造）/ `deprecated`（保留但不再推荐）。**本库 601 条当前为 587 `verified` / 14 `draft`** |

## 三、跨域联动

- **问卷设计 → 本库**：设计问卷或操作化变量时，先 `query_scales.py` 定位成熟量表，优先引用已发表量表而非自编；自编须注明与原量表差异。
- **数据分析 → 本库**：进入分析前，变量名与量表条目逐一对应，反向计分题须按本库 `items[].reverse` 标记处理。
- **理论支撑 → 本库**：综述或假设推导中涉及构念测量时，引用本库对应量表出处。
- **跨库桥接**：经 `skill:obhrm-bridge` 的概念词表串联「量表↔理论↔R 方法」；某构念有哪些成熟量表、可由哪个 R 方法检验，统一经 `query_concept.py` 查询。

> **关于 `construct_id`**：量表侧为带 `_scale` / `_questionnaire` 后缀的 slug（如 `emotional_exhaustion_scale`），与理论库的命名体系不同，两库无法按标识直接关联。跨库检索统一经中英双语概念词表作中介，详见 `skill:obhrm-bridge`。

## 四、注意事项

- **`reference_used` 是取用文献，不是原始出处**：`reference_used` 记录本库条目文本从哪篇文献录入，仅作溯源用；量表的原始出处与权威引用见 `background`。**正式引用前须核对原始文献，不得直接引用 `reference_used`。**
- 出处引用须原样保留（四铁律·不编引用）；引用时以 `background` 所载原始文献为准。
- **计分方式缺失时显式标注，不臆造**：部分量表（当前 77 条）的各维度 `scoring` 在原始资料中即缺失，索引中以 `has_scoring: false` 标记，检索输出会显式标注「计分方式:（原文未覆盖）…使用前须回原始文献核对」。**不得据量表惯例推测或补写计分规则**——同名量表未必同源，计分方式也不可直接套用其他条目。
- 量表条目受原量表版权约束，仅供学术研究引用与操作化参考，商用再分发须获原作者授权。
- 新增/修订量表须同步更新 `knowledge/scales/entities.json`（合并存储中该 `scale_id` 对应记录）与 `knowledge/_scale_index.json`，保持索引↔存储双向一致；两处字段名不一致处（如存储用 `variable.{zh,en}`、索引用 `variable_zh/variable_en`）以 schema 为准逐字段核对，不得凭印象填写。
