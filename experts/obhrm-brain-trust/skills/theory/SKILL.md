---
name: theory-library
version: 1.0.3
author: Xing Bu
description: OBHRM 智囊团（obhrm-brain-trust）— 理论库（理论域资产）。145 个组织行为/人力资源管理理论（中英理论名+构念+内容/作用机制/结构/应用四段正文+参考文献），支持按 construct_id / 关键词 / theory_id 检索，供理论框架构建、假设推导、综述理论增量论证。面向本科生、研究生与学者，检索到的内容直接完整呈现。
description_zh: OBHRM 智囊团的理论库。145 个组织行为与人力资源管理理论，含内容、作用机制、结构、应用四段正文与参考文献，供理论框架构建与假设推导。
description_en: The theory library of the OBHRM expert team. 145 organizational-behavior and HRM theories with four-part exposition and references, supporting theoretical framing and hypothesis derivation.
---

> **跨技能引用约定**：本文档以逻辑名形式引用兄弟技能（如 `` `skill:obhrm-bridge` ``），各技能的实际目录与入口脚本即 `skills/` 下的同名目录；正文给出的脚本路径为该技能内部的相对路径。

# 理论库（theory-library）— 理论域资产

> 本 skill 是 OBHRM 智囊团（obhrm-brain-trust）的**理论权威资产**：145 个理论，每条记录含 `theory_id`、`construct_id`（构念归一化标识）、`name`（中英理论名）、`title`、`what/processes/structure/application` 四段正文（**允许为空**：structure 空 87/145、processes 空 109/145、what 空 18、application 空 10；空段须在输出中标注「原文未覆盖」）、`references`（参考文献原文块）、`status`、`note`。索引 `_theory_index.json` 的 `nodes` 另给出概览字段 `name_en / name_zh / has_what / has_processes / has_struct / has_app / n_refs / status / note`（`n_refs` 仅存在于索引中，其口径为 `references` 的**非空行数**——「文献未登记」说明段记 0 篇；此口径经全量 145 条实测与索引零不符，勿改用「`[n]` 编号条目数」，后者有 25 条对不上）。145 条中 **27 条状态为 `verified`（来源已确证）、118 条为 `draft`（约 81.4%；正文可用、但来源尚未确证，见条目 `note`，引用前须核对原始出处）**。

---

## 一、资产规模与结构

- **理论数**：145（27 verified / 118 draft，约 81.4% 为 draft）
- **四段覆盖率**：内容（`what`）127/145、作用机制（`processes`）36/145、结构（`structure`）58/145、应用（`application`）135/145；四段齐备 23/145。结构段缺失最普遍（空 87 条），其次为作用机制段（空 109 条）；任一段库内为空时输出须标注「（原文未覆盖）」，不补写。
- **统计口径说明**：上表为 1.0.3 当前快照；语料变动后由检索脚本实时计算覆盖率，引用时以脚本输出为准，不依赖本文档的静态数字。
- **目录**：`knowledge/theories/entities.json`（145 条合并存储，按 `theory_id` 为键的单一文件）+ `knowledge/_theory_index.json`（索引：`nodes` 含 theory_id/construct_id/name_en/name_zh/has_what/has_processes/has_struct/has_app/n_refs/status/note）
- **存储口径**：合并存储 `entities.json` 是理论条目的**唯一来源**。本包不随附逐条单文件（`Txxx.json`），以避免包内文件数膨胀到审核上限之外；检索脚本与 agent 均自合并存储按 `theory_id` 取正文。
- **检索入口**：`scripts/query_theories.py`（纯标准库，零依赖；检索内核由 `scale-library` / `r-analysis` 共享 `../obhrm-bridge/kernel/library_query.py` 通用模块，匹配 / 安全边界 / JSON 契约 / 覆盖率单点实现）

```bash
python3 scripts/query_theories.py "stakeholder"          # 关键词(中/英/构念)检索
python3 scripts/query_theories.py "T001" --full          # theory_id 精确 + 四段正文(what/processes/structure/application)
python3 scripts/query_theories.py "社会交换" --limit 5
python3 scripts/query_theories.py "T001" --json          # 输出原始 JSON（references 参考文献原文块全文在此）
```

> **查询铁律**：145 条理论正文不可一次载入上下文。任何"查理论/理论内容"需求**必须先经 `query_theories.py` 检索索引**，按 theory_id 再从合并存储取该条正文。禁止凭记忆编造理论内容或归属。

## 二、单条理论记录结构（合并存储 `entities.json` 中的单条）

| 字段 | 含义 |
|------|------|
| `theory_id` | 稳定主键，形如 `T001`，为合并存储中的键 |
| `construct_id` | 构念归一化 slug，跨库主键 |
| `name` / `title` | 中英理论名（`en` / `zh`）与展示标题 |
| `what` / `processes` / `structure` / `application` | 内容 / 作用机制 / 结构 / 应用 四段正文（综述与假设推导的素材依据；原始文献未覆盖的段落允许为空字符串） |
| `references` | 参考文献原文块（出处追溯依据） |
| `status` | 条目状态：`verified`（已核验可用于学术产出）/ `draft`（来源尚未确证的可用正文，**资料本身真实、可引用出结果，但输出须显著标记「来源未确证」，严禁编造**，详见该条 `note`）/ `deprecated`（保留但不再推荐） |
| `note` | 备注（如 `draft` 条目来源未确证的具体说明） |
| `has_what` / `has_processes` / `has_struct` / `has_app` | 索引标记：四段正文（what / processes / structure / application）是否非空，便于快速判断可用素材 |

## 三、跨域联动

- **理论框架构建 → 本库**：建模与假设推导时，先 `query_theories.py` 定位基础理论与机制，确保假设有理论根基；理论增量（重构/解密/边界）须对照本库既有理论。
- **综述理论增量 → 本库**：判定理论增量层次须基于本库已收录理论的边界与缺口。
- **跨库桥接**：经 `skill:obhrm-bridge` 的概念词表串联「理论↔量表↔R 方法」；某构念的理论基础、配套量表、可检验 R 方法统一经 `query_concept.py` 查询。

> **关于 `construct_id`**：理论侧为无后缀 slug（如 `affective_events_theory`），与量表库的命名体系不同，两库无法按标识直接关联。跨库检索统一经中英双语概念词表作中介，详见 `skill:obhrm-bridge`。

## 四、注意事项

- 理论内容/归属须原样引用（四铁律·不归观点/不编引用）；本库 `references` 与 `what/processes/structure/application` 为权威依据。
- 理论引用须标注原始提出者与原著，不得张冠李戴。
- 新增/修订理论须同步更新 `knowledge/theories/entities.json`（合并存储中该 `theory_id` 对应记录）与 `knowledge/_theory_index.json`，保持索引↔存储双向一致；两处字段名不一致处（存储用嵌套 `name.{zh,en}`、索引用扁平 `name_zh/name_en`；`n_refs` 仅存于索引，口径为 `references` 的非空行数，「文献未登记」说明段记 0 篇）以 schema 为准逐字段核对，不得凭印象填写。
