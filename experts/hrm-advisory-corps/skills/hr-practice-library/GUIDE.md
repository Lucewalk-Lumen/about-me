# 实务库使用指南（与 hrm-advisory-corps 专家团协同）

> 本文档讲清楚：**你和团队里的 7 个专家怎么一起用这 199 份实务模板**。
> 所有连接锚定包内既有技能/agent/引擎，可回 `query_forms.py` 与 `.docx` 原件核对。

## 0. 一句话定位

**实务库是团队的「动手端」**——199 份现成 HR 制度/表单模板；**7 个 scoped specialist 是「动脑端」**——各自持有领域方法论；**lead（韩明轩）当总调度**，把两边串起来。**全程不新增 agent。**

## 1. 双入口机制：lead 统一收口

| 你的问法 | 路由去向 | 谁干活 |
|---|---|---|
| 方法论：「怎么设计 / 怎么算 / 合不合规」 | `routing.yaml` 直接路由 | 对应 7 个 specialist（如 `compensation-strategy` 周予安） |
| 落地：「用什么表 / 怎么落地 / 制度模板」 | 命中 `practice_forms`（`intent: artifact`，**优先于**领域方法论与跨模块联动）→ `lead` | `lead` 调 `query_forms.py` 定位模板，再按 `solution_links.owner_*` 派给**归属 specialist** 填/改/适配 |

落点是 `skills/hr-practice-library` 这个技能；每份表单的归属关系写死在 `solution_links` 里，例如：

- `F096 绩效奖金考核表` → 归属 `performance-management` + 主引擎 `okr_tracker.sh` + 终检 `compliance_gate.py`
- `F104 员工出差管理制度` → 归属 `compensation-strategy` + 主引擎 `payroll_engine.py`

> 为什么落地问法也走 lead 而不直接进领域技能：实务库是方法论的「执行载体」而非独立知识源；由 lead 统一收口，既守住编排边界，又不增加 agent、不多一次无谓跳转。

## 2. 七种检索入口（速查）

> **命令行的单一基准是同目录 [`SKILL.md`](./SKILL.md) §3「检索入口（七种用法）」**——本文件不重复维护命令，
> 以免两处副本各自漂移。
>
> 七种入口速览：① 关键词（标题/字段/条款/正文）② `form_id` 精确（`--full`）③ 限定模块（`--module`）
> ④ 限定类型（`--kind`，关键词可空）⑤ 反查技能/agent 归属（`--skill`）⑥ 反查 SOP 引擎（`--engine`）
> ⑦ 流程关联（`--flow`）／列出模块（`--modules`）。

> 路径约定：本文与 `SKILL.md` 内的相对路径均以本 skill 根目录（`skills/hr-practice-library/…`）为基准；
> 跨 skill 引用一律写包根相对路径。

> 附带校验开关（不属于上列七种检索入口）：`query_forms.py --verify-files` 自检全部条目 `file` 字段在磁盘上真实存在。

## 3. 三个典型用法（照抄）

### 3.1 单专家取模板（最常见）

> 你：「帮我找一份现成的新员工试用表和请假表。」
> → `practice_forms` → `lead` → 命中 F 系列 → 派 `recruitment-pipeline`（试用/转正：`F050 新员工试用表`，REC 段）与 `compensation-strategy`（`F124 员工请假申请表`，COM 段）→ 返回 `.docx` 原件路径，specialist 顺手说明字段怎么填。
> （注：库内**没有**标题含「入职」的模板；入职/试用类请用 `F032 员工试用期管理办法`、`F041 员工试用期考核表`、`F050 新员工试用表`，入职培训类请用 `F059 员工职前培训管理制度`。）

### 3.2 专家出方案 + 模板落地（方法论 + 载体）

> 你：「我们 200 人技术公司想做薪酬绩效联动，给个方案。」
> → 路由到 `compensation-strategy`（周予安）+ `performance-management`（宋雨薇）→ 俩专家产出方案 → `lead` 顺带从实务库拉 `F104–F137`（薪酬表单）当执行载体，方案直接「可填表」。

### 3.3 跨专家串 SOP（handoffs 自动衔接）

> 你：「走一遍新员工入职全流程。」
> → `lead` 沿 17 条 `handoffs` 编排：
> `REC`（`F044 应聘人员登记表`）→ `TRN`（`F059 员工职前培训管理制度`）→ `PER` → `COM` → `ER`（`F152 员工离职交接单`）→ `ARC`（`F196 档案移交（接收）登记表`）。
> 每张单的「输出 = 下一张的输入」在 `knowledge/_module_map.json` 的 `handoffs[]` 中已衔接，**全程过 `compliance_gate.py` 终检**（`--text` 退出码 `0` = 可交付、`3` = 拦截转人工），P0 风险直接拦截转人工。

## 4. 底层衔接

- **handoffs（17 条）** 把零散表单拼成可执行的 HR 闭环 SOP，不是静态资产；
- **合规闸门统一收口**——任何制度类模板产出必须过 `labor-compliance` 的 `compliance_gate.py` + `compliance-baseline.md` 二次校验，守住劳动法底线；
- **ARC（人事档案 F165–F199）** 归口 `labor-compliance` 的合规职责，是团队合规终检链条上的行政底座；使用时应分清「方法论应用场景」与「行政合规底座」的边界。

## 5. 权属与合规边界（前置告知）

- 模板原件来源为公开渠道资料，入库仅作结构参考；原件未标注作者或出版信息，商用或对外发布前须自行确认授权（详见 LICENSE 第 4 条）。
- 本库内置的**抽取文本、字段骨架与索引**由本包维护、受 MIT 覆盖；`.docx` 模板原件**不在 MIT 授权范围内**（见 `LICENSE` 第 4 条），再分发须另行取得权利人许可；
- 模板含个人信息栏位（身份证号、薪资等），**仅作字段结构示意，禁止采集真实个人信息**；
- 制度类模板输出须与本团队 `compliance_gate.py` 终检 + `labor-compliance` 的 `compliance-baseline.md` 二次校验联动，守住劳动法底线。
