---
name: hr-practice-library
version: 1.0.0
author: "Xing Bu"
description: |
  HR 实务工具库——199 份 HR 制度与表单模板（制度 58 / 表格 141），按 7 大模块归口到本团队
  对应的 scoped 技能 / agent（7 模块 → 6 个归属 agent），可连接到对应的 SOP 引擎与统一合规闸门 compliance_gate.py。
  提供关键词 / form_id / 模块 / 类型 / 归属技能 / 引擎 / 流程 七种检索入口；所有连接指向包内
  真实存在的技能、agent、引擎脚本路径，可回原件与磁盘路径核对。
---

# HR 实务工具库（hr-practice-library）

本技能是 hrm-advisory-corps 的**实务落地资产库**：把抽象的人力资源管理动作，落到一张张
可套用、可留痕、可审计的**制度与表单模板**上。它是团队"动手端"——`hrm-solution` 提供
共享契约与计算引擎，`org-planning` 等 6 个归属 specialist 提供领域方法论，本库提供**执行这些
方法论时直接套用的实体模板**。

## 1. 资产规模与模块归属

199 份模板按 HR 职能闭环分段编号 `F001–F199`（段位 = 闭环顺序，删除留空不递补），
通过 `solution_links` 归口到本团队的 scoped 技能 / agent：

| # | 模块 | 编号段 | 制度 | 表格 | 合计 | 归属技能 / agent | 主 SOP 引擎 |
|---|---|---|---|---|---|---|---|
| 1 | 人力资源规划 HRP | F001–F029 | 11 | 18 | 29 | org-planning | org_health.py / workforce_plan_tracker.sh |
| 2 | 招聘与配置 REC | F030–F056 | 8 | 19 | 27 | recruitment-pipeline | candidate_scorer.py |
| 3 | 培训与开发 TRN | F057–F079 | 7 | 16 | 23 | talent-development | （无专属引擎） |
| 4 | 绩效管理 PER | F080–F103 | 8 | 16 | 24 | performance-management | okr_tracker.sh |
| 5 | 薪酬福利 COM | F104–F137 | 9 | 25 | 34 | compensation-strategy | payroll_engine.py |
| 6 | 员工关系 ER | F138–F164 | 7 | 20 | 27 | labor-compliance | compliance_gate.py |
| 7 | 人事档案 ARC | F165–F199 | 8 | 27 | 35 | labor-compliance | compliance_gate.py |

> **ARC 模块说明**：人事档案（收集/借阅/转递/销毁）属行政合规域，归口 `labor-compliance`
> 的记录与合规职责，是团队合规终检链条上的行政底座——与本团队"合规终检"的定位一致。

## 2. 与团队既有内容的可追踪连接（三层）

| 层 | 连接方式 | 存储位置 | 可核对性 |
|---|---|---|---|
| **归属层** | 每份表单按模块归属到 1 个 scoped 技能 + 同名 agent | `forms/Fxxx.json` 的 `solution_links.owner_*` | 技能/agent 目录均真实存在 |
| **引擎层** | 主引擎（模块决定）+ 关键词增强引擎（正文命中才追加） | `solution_links.primary_engines` / `extra_engines` | 引擎脚本路径真实存在 |
| **流程层** | 17 条跨模块交接单据（一张的输出 = 下一张的输入） | `_module_map.json` 的 `handoffs[]` | `form_id` 均存在于 `_practice_index.json` 索引 |

**统一合规闸门**：所有表单输出均经 `labor-compliance` 的 `compliance_gate.py` 终检
（`python3 skills/hrm-solution/scripts/security/compliance_gate.py --text '<文本>'`，退出码 `0` = PASSED/FLAGGED、`3` = BLOCKED；见 `solution_links.gate`），与本团队"统一合规闸门把关"的架构一致。

> 连接一律锚定到本包**既有**内容（8 个 scoped 技能 / agent、SOP 引擎），不引入包外依赖；
> 所有路径均指向包内真实存在的技能 / agent / 引擎，可回原件与磁盘路径核对。

## 3. 检索入口（七种用法）

> 本库经路由 `practice_forms`（`intent: artifact`）进入，**优先于** `compensation` / `performance` 等单模块路由；`digital_build`（无代码搭建）同属该成品意图层。命中后由总调度按 `solution_links.owner_*` 派给归属 specialist。

```bash
# 1) 关键词（标题/字段/条款/正文）
python3 skills/hr-practice-library/scripts/query_forms.py "绩效"
# 2) form_id 精确 + 字段骨架与正文
python3 skills/hr-practice-library/scripts/query_forms.py "F096" --full
# 3) 限定模块
python3 skills/hr-practice-library/scripts/query_forms.py "离职" --module ER
# 4) 限定类型（关键词可空，须配 --module/--kind）
python3 skills/hr-practice-library/scripts/query_forms.py "" --kind 表格 --limit 5
# 5) 反查：某 scoped 技能/agent 负责哪些表单
python3 skills/hr-practice-library/scripts/query_forms.py --skill recruitment-pipeline
# 6) 反查：哪些表单用到某 SOP 引擎
python3 skills/hr-practice-library/scripts/query_forms.py --engine payroll_engine.py
# 7) 流程关联 + 列出模块
python3 skills/hr-practice-library/scripts/query_forms.py --flow F034
python3 skills/hr-practice-library/scripts/query_forms.py --modules
```

> 路径约定：本文件内 `scripts/…` / `knowledge/…` 均相对于本 skill 根目录
> （`skills/hr-practice-library/…`）。跨 skill 引用一律写包根相对路径。

> 附带校验开关（不属于上表七种检索入口）：`query_forms.py --verify-files` 自检全部条目 `file` 字段在磁盘上真实存在，用于发布前一致性核对。

> **与专家团怎么一起用**：双入口机制、7 个检索入口、三个照抄场景、handoffs 串 SOP 与合规闸门收口，详见同级文档 **`GUIDE.md`**。

## 4. 与 hr-toolset.md 的关系（互补，非替代）

`hrm-solution` 共享技能下的 `hr-toolset.md` 是**命令化 prompt 模板**（recruit/onboard/
offboard/policy/handbook/template 6 命令，运行时生成文档）；本库是**已成型的可编辑
.docx 实体模板**（199 份制度与表单原件）。二者互补：

- 想要"按场景生成一份新制度" → 用 `hr-toolset.md` 的 `policy`/`template` 命令；
- 想要"直接套用行业既有的成熟制度/表单" → 用本库的 `query_forms.py` 检索并打开 `.docx` 原件。

## 5. 索引与连接（内置，开箱即用）

- **基准**：`templates/<MODULE_CODE>/<policy|form>/<Fnnn>.docx`（199 份原件，全 ASCII 路径；`<MODULE_CODE>` ∈ HRP/REC/TRN/PER/COM/ER/ARC，`制度 → policy`、`表格 → form`）。
- **随包数据**（无需运行时重建）：
  - `knowledge/_practice_index.json` —— 199 条模板主索引（模块 / 类型 / 归属 / 引擎 / 流程）；
  - `knowledge/_solution_links.json` —— 模板 → 技能 / agent / SOP 引擎 / 合规闸门的连接总览；
  - `knowledge/forms/Fxxx.json` —— 单份条目的字段骨架、正文摘要与 `solution_links`；
  - `templates/INDEX.csv` —— 199 条模板清单（`form_id,module_code,kind,title`），便于按目录浏览与人工核对；
  - `schema.json` —— 上述数据的结构契约（位于本 skill 根目录）。
- 所有连接均锚定本包既有 7 技能 / 7 agent / SOP 引擎，可回原件与磁盘路径核对；调整归属或新增引擎连接须同步修改映射数据。

## 6. 权属与合规边界（必须前置告知）

- 模板原件来源为公开渠道资料，入库仅作结构参考；原件未标注作者或出版信息，商用或对外发布前须自行确认授权（详见 LICENSE 第 4 条）。
- 本库内置的**抽取文本、字段骨架与索引**由本包维护、受 MIT 覆盖；上列 `.docx` 模板原件**不在 MIT 授权范围内**（见 `LICENSE` 第 4 条除外条款），再分发须另行取得权利人许可；
- 模板含个人信息栏位（身份证号、薪资等），**仅作字段结构示意，禁止采集真实个人信息**；
- 制度类模板输出须与本团队 `compliance_gate.py` 终检 + `labor-compliance` 的 `compliance-baseline.md` 二次校验联动，守住劳动法底线。
