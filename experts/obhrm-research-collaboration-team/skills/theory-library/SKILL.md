---
name: theory-library
version: 1.0.1
author: "Xing Bu"
description: OBHRM 研究协作团 — 理论库（理论域资产）。134 个组织行为/人力资源管理理论（中英理论名+构念+内容/作用机制/结构/应用四段正文+参考文献），条目带 verified/draft 生命周期，支持按 construct_id / 关键词 / theory_id 检索，供理论框架构建、假设推导、综述理论增量论证。
---
> **跨技能引用约定**：本文档以逻辑名形式引用兄弟技能（如 `` `skill:peer-review` ``），不使用逻辑名映射表，重命名或移动技能时按相对路径同步更新。
# 理论库（theory-library）— 理论域资产
> 本 skill 是 OBHRM 研究协作团的**理论真源资产**：134 个理论，每条记录含 `theory_id`、`construct_id`（构念归一化标识）、`name`（中英理论名）、`title`、`what/processes/structure/application` 四段正文（**允许为空**：空段须在输出中标注「原文未覆盖」，不得补写）、`references`（参考文献原文块）、`status`、`note`。索引 `_theory_index.json` 的 `nodes` 另给出概览字段 `name_en / name_zh / has_what / has_processes / has_struct / has_app / n_refs / status / note`（`n_refs` 仅存在于索引中）。134 条中 27 条 `verified`（来源已确证）、107 条 `draft`（**正文可用、但来源尚未确证**，见条目 `note`，**可在显著标记「来源未经确证」后引用，本库不保证其真实性，严禁编造出处**）。
---

## 一、资产规模与结构

- **理论数**：134（27 verified / 107 draft；检索脚本每次现算并输出覆盖率，勿沿用本行静态数字）
- **目录**：`knowledge/theories/entities.json`（合并存储全部 134 条记录，键为 `theory_id`，检索内核优先读取）+ `knowledge/_theory_index.json`（概览索引）。调用方无需手动读取 `entities.json`——经 `query_theories.py` 检索即可。
- **检索入口**：`scripts/query_theories.py`（纯标准库，零依赖；检索内核与 `scale-library` / `r-analysis` 共享 `../obhrm-bridge/kernel/library_query.py` 通用模块（匹配、安全边界、JSON 契约、覆盖率面板单点实现，避免多份近重复脚本各自漂移））

```bash
python3 scripts/query_theories.py "stakeholder"          # 关键词(中/英/构念)检索
python3 scripts/query_theories.py "T001" --full          # theory_id 精确 + 完整记录
python3 scripts/query_theories.py "社会交换" --limit 5
python3 scripts/query_theories.py "T001" --json          # 输出原始 JSON
```

> **查询铁律**：134 条记录不可一次载入上下文。任何"查理论/理论内容"需求**必须先经 `query_theories.py` 检索**，按返回结果取用（`--full` 展开完整记录）。禁止凭记忆编造理论内容或归属。

## 二、单条理论记录结构（entities.json 中按键索引）

| 字段 | 含义 |
|------|------|
| `construct_id` | 构念归一化 slug，跨库主键 |
| `has_what` / `has_struct` / `has_app` | 该理论是否具备"内容 / 结构 / 应用"三态（索引标记，便于快速判断可用素材） |
| `what` / `structure` / `application` | 三态详细文本（综述/假设推导的素材真源） |
| `source` | 权威出处与参考文献 |

## 三、跨域联动

- **理论框架构建（A2/A3）→ 本库**：`skill:paper-writing` 建模与假设推导时，先 `query_theories.py` 定位基础理论与机制，确保假设有理论根基；理论增量（重构/解密/边界）须对照本库既有理论。
- **综述理论增量（L 路径）→ 本库**：`skill:literature-review` 的 G1+ 收敛门"理论增量三层次"判定，须基于本库已收录理论的边界与缺口。
- **基金立项依据（B 路径）→ 本库**：`skill:grant-writing` 写 GAP 与理论必要性时引用本库理论出处。
- **审稿理论评估（C 路径）→ 本库**：`skill:peer-review` 核查稿件理论框架自洽性与理论引用准确性。
- **跨库桥接**：`skill:knowledge-graph` 按 `construct_id` 串联"理论↔量表"；R 方法按库语义归类（general / theory / scale）标注适用库，`construct_ids` / `r_methods` 关联待回填，当前不提供构念级 R 方法检索。

## 四、注意事项

- 理论内容/归属须原样引用（四铁律·不归观点/不编引用）；本库 `source` 与 `what/structure/application` 为真源。
- 理论引用须标注原始提出者与原著，不得张冠李戴。
- 新增/修订理论须同步更新 `_theory_index.json` 与 `knowledge/theories/entities.json` 中对应记录，保持索引↔存储双向一致。
