---
name: scale-library
version: 1.0.1
author: "Xing Bu"
description: OBHRM 研究协作团 — 量表知识库（测量域资产）。599 个组织行为/人力资源管理量表（中英变量名+构念+维度+条目+计分方式+取用文献，条目带 verified/draft 生命周期），支持按 construct_id / 关键词 / scale_id 精确检索，供问卷设计、假设变量操作化、量表选型与引用。
---
> **跨技能引用约定**：本文档以逻辑名形式引用兄弟技能（如 `` `skill:peer-review` ``），不使用逻辑名映射表，重命名或移动技能时按相对路径同步更新。
# 量表知识库（scale-library）— 测量域资产
> 本 skill 是 OBHRM 研究协作团的**量表真源资产**：599 个量表，每条含 `variable_en/variable_zh`（中英变量名）、`construct_id`（构念归一化标识）、`dimensions`（维度+题数+计分）、`items`（完整条目文本）、`reference_used`（**条目文本的取用文献**，即本库从哪篇文献录入，**不是量表的原始出处**）。599 条中 587 条 `verified`、12 条 `draft`（来源尚未确证，**可在显著标记「来源未经确证」后引用，本库不保证其真实性，严禁编造出处**）。
---

## 一、资产规模与结构

- **量表数**：599（587 verified / 12 draft；检索脚本每次现算并输出覆盖率）
- **目录**：`knowledge/scales/entities.json`（合并存储全部 599 条记录，键为 `scale_id`，检索内核优先读取）+ `knowledge/_scale_index.json`（概览索引）。调用方无需手动读取 `entities.json`——经 `query_scales.py` 检索即可。
- **检索入口**：`scripts/query_scales.py`（纯标准库，零依赖；检索内核与 `theory-library` / `r-analysis` 共享 `../obhrm-bridge/kernel/library_query.py` 通用模块（匹配、安全边界、JSON 契约、覆盖率面板单点实现，避免多份近重复脚本各自漂移））

```bash
python3 scripts/query_scales.py "trust"              # 关键词(中/英/构念)检索
python3 scripts/query_scales.py "S001" --full        # scale_id 精确 + 完整条目(含 items)
python3 scripts/query_scales.py "self determination" # 英文构念词
python3 scripts/query_scales.py "S001" --json        # 输出原始 JSON(供程序消费)
```

> **查询铁律**：599 条记录不可一次载入上下文。任何"找量表/查量表条目"需求**必须先经 `query_scales.py` 检索**，按返回结果取用（`--full` 展开完整条目含 items）。禁止凭记忆编造量表名/条目/计分方式。

## 二、单条量表记录结构（entities.json 中按键索引）

| 字段 | 含义 |
|------|------|
| `construct_id` | 构念归一化 slug，跨库主键（与理论库/交叉索引同源） |
| `dimensions` | 维度列表，每项含 `name_zh/name_en/item_count/item_range/scoring` |
| `items` | 条目列表，每项含 `no/text/dimension/reverse` |
| `reference_used` | 条目文本的取用文献（作者, 年, 期刊，本库录入所据）；非量表原始出处，正式引用须核对原始文献 |
| `status` | 条目生命周期状态：`verified`（已核验可用于学术产出）/ `draft`（来源尚未确证，可在显著标记「来源未经确证」后引用，本库不保证其真实性，严禁编造出处）/ `deprecated`（保留但不再推荐） |

## 三、跨域联动

- **问卷设计（A0/A4）→ 本库**：`skill:paper-writing` 设计问卷/量表时，先 `query_scales.py` 定位成熟量表，优先引用已发表量表而非自编；自编须注明与原量表差异。
- **测量/数据分析（D0/D1 数据清洗）→ 本库**：`skill:data-analysis` 的 D0 试跑"认得准"步骤——变量名与量表条目逐一对应，反向计分题须按本库 `items[].reverse` 标记处理。
- **审稿评估（C 路径）→ 本库**：`skill:peer-review` 评估稿件测量质量时，核查所用量表是否在本库、计分/反向计分是否与源一致。
- **理论支撑（L 路径）→ 本库**：`skill:literature-review` 综述中涉及构念测量时，引用本库对应量表出处。
- **跨库桥接**：`skill:knowledge-graph` 按 `construct_id` 串联"量表↔理论"；R 方法按库语义归类（general / theory / scale）标注适用库，`construct_ids` / `r_methods` 关联待回填，当前不提供构念级 R 方法检索。

## 四、注意事项

- 出处引用须原样保留（四铁律·不编引用）；本库 `reference_used` 字段为条目文本取用文献真源。
- 量表条目文本受原量表版权约束，本库仅供学术研究引用与操作化参考，商用再分发须获原作者授权。
- 新增/修订量表须同步更新 `_scale_index.json` 与 `knowledge/scales/entities.json` 中对应记录，保持索引↔存储双向一致。
