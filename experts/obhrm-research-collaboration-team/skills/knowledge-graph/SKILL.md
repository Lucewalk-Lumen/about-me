---
name: knowledge-graph
version: 1.0.0
author: "Xing Bu"
description: OBHRM 研究协作团 — 跨库索引（桥接层资产）。以 construct_id 为跨库主键，串联 量表库(599)/理论库(134)/R方法库(108) 三库：scale→theory 62 条（58 个量表）、theory→scale 7 条（6 个理论）、134 个构念聚合节点，悬空=0。支持按 construct_id / scale_id / theory_id / method_no / 关键词查询关联。
---
> **跨技能引用约定**：本文档以逻辑名形式引用兄弟技能（如 `` `skill:peer-review` ``），不使用逻辑名映射表，重命名或移动技能时按相对路径同步更新。
# 跨库索引（knowledge-graph）— 桥接层资产
> 本 skill 是三库（量表/理论/R）的**关联桥接层**：以 `construct_id`（构念归一化 slug）为统一主键，把分散在三库的资产连成可导航网络。所有关联边经源文档审计为真实引用（非编造），悬空=0、边缺 construct_id=0。
---

## 一、资产结构与规模

- **交叉索引**：`knowledge/cross-library-index.json` + `knowledge/CROSS_LIBRARY.md`（人工可读说明）
- **规模**：
  - `scale_to_theory`：58 个量表关联 62 条边（量表→理论，含 `via` 媒介词）
  - `theory_to_scale`：6 个理论关联 7 条边（理论→量表）
  - `construct_index`：134 个构念聚合节点（每节点含 `theory_ids / scale_ids / r_methods`；`scale_ids` / `r_methods` 允许为空——空表示源文档中尚无真实匹配，**不得为凑数编造关联**）
  - `r_applicability`：108 个 R 方法，按库语义归类（general / theory / scale）标注适用库；`construct_ids` 关联待回填，当前不提供构念级 R 方法检索
- **检索入口**：`scripts/query_graph.py`（纯标准库，零依赖）

```bash
python3 scripts/query_graph.py "self determination"  # 按构念查关联的量表/理论/R方法
python3 scripts/query_graph.py "S347"                # 查某量表的关联理论(via)
python3 scripts/query_graph.py "T003"                # 查某理论的关联量表(via)
python3 scripts/query_graph.py "8.1"                 # 查某 R 方法的适用库（general/theory/scale）
python3 scripts/query_graph.py "社会交换" --json     # 输出原始 JSON
```

## 二、跨库主键：construct_id

三库通过 `construct_id` 同源归一化：
- 量表 `Sxxx.json.construct_id` ↔ 理论 `Txxx.json.construct_id` 已填充；`r_applicability[method_no].construct_ids` 关联待回填（当前按库语义归类 general/theory/scale）
- 例：构念 `social_identity_theory` 同时出现在某量表、理论 T063、相关 R 方法节点。

## 三、跨域联动

- **总路由（lead）→ 本库**：`skill:obhrm-research-base`（主理人）在判定"查某构念的测量/理论/方法"时，先经 `query_graph.py` 定位三库资产，再下发对应团员消费。
- **量表↔理论（paper-writing / literature-review）→ 本库**：假设推导时，经本库确认"该构念已有成熟量表 + 理论根基"，避免自造构念。
- **理论↔R方法（data-analysis）→ 本库**：选分析方法时，经 `r_applicability` 确认方法适用的库语义归类（general/theory/scale）。
- **三库资产查询**：`skill:scale-library`（量表）、`skill:theory-library`（理论）、`skill:r-analysis`（R 脚本）的具体检索，经本库定位 construct_id 后调用。

## 四、注意事项

- 关联边为**真实引用**审计结果；新增关联须基于源文档证据，禁止臆造边（四铁律·不编引用）。
- 修改任一库（增删量表/理论/R方法）后，须同步重跑交叉索引构建，保持 `construct_index` 与三库一致、悬空=0。
- 本库为只读桥接层，不存储条目原文，仅持有索引与关联边。
