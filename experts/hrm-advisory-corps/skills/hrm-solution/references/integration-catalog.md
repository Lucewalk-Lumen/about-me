# Integration Catalog — Optional Runtime Backends

> 本文件为**中立的运行时集成参考**，不将专家团绑定到任何单一产品。
> 本包**不声明**任何 MCP / 连接器依赖；下列后端均为可选能力，由用户在会话中自行连接后启用。
> 涉及"数字人面试运营"与"无代码平台搭建"两类能力时，agent **先询问用户选用哪家后端**，再加载对应后端档案落地执行；用户未连接时引导连接，拒绝连接时退化为咨询模式（仅产出可移植方案与搭建规格）。

## 连接器适配接口（统一抽象）

所有可选后端遵循统一的「连接器适配接口」（连接 / 预检 / 落地 / 验证四步；凭证来自环境变量或 Secret Manager，绝不硬编码）：

**通用 HTTP 后端（可选，用户连接后启用）**：仅当用户明确选择并连接某 REST 后端时，才按该后端契约执行；凭证一律来自环境变量或 Secret Manager，绝不硬编码；默认 dry-run 预览、真实副作用前需用户在环确认；未连接任何后端时由 `NullAdapter` 退化为纯咨询模式（仅产出可移植方案）。

- `connect()`：建立/校验连接（凭证来自环境变量/Secret Manager，**绝不硬编码**）
- `preflight(spec)`：连接预检 + 平台无关规格可行性检查
- `deploy(spec, dry_run=True)`：执行落地（默认 dry-run，需显式确认才有真实副作用）
- `verify(result)`：三路径验证（正常/边界/异常）

凭证一律来自环境变量或机密管理服务，不落盘、不入库、不硬编码。未连接任何后端时退化为纯咨询模式。

---

## 统一选择协议（两类能力通用）

1. **识别意图**：请求属于"数字人面试"或"无代码搭建"之一。
2. **询问后端**：用提问或选项列出本节"可选后端"，请用户选择。
3. **加载档案**：选定后加载对应后端档案的"执行层"步骤。
4. **设计层先行（平台无关，始终执行）**：
   - 数字人面试：岗位画像 → 4–6 评价维度（含权重）→ 6–10 道面试题 → 评分 rubric → 复盘框架。
   - 无代码搭建：需求四要素（使用者/数据/流转/输出）→ 表单结构 → 字段清单 → 流程设计 → 权限矩阵 → 视图/看板/门户草图。
5. **执行层落地（平台相关）**：按所选后端档案调用其工具/命令；未连接则引导连接/安装后再执行；用户拒绝连接则转咨询模式（输出可导入任意平台的规格文档）。
6. **人在环**：真实副作用动作（发起面试、发布模板、写数据、配置流程）前必须显式确认；不确定时先用 dry-run / 预览。

---

## A. 数字人面试运营 · 可选后端

### A-1. 利唐 i 人事 / iHR360（ihr-cli）— 可执行

**前置（仅首次 / 未就绪时）**
- 安装并校验 `ihr-cli`；初始化 `ihr-cli config init --env work100-prod`；`ihr-cli auth login` 完成授权。
- 仅当真实业务动作前自检；纯咨询/方案草拟不需要阻塞。

**设计层（平台无关，照常产出）**
- 岗位画像、4–6 评价维度（权重 1–5）、6–10 道正式题（自我介绍/开放/客观/深挖/结束语）、计分与追问策略、反作弊建议。

**执行层（按 ihr-cli 契约）**
1. 模板：`ihr-cli conference +search-avatar-template`（按岗位/模板名搜）；无合适模板时用 `+create-avatar-template --dry-run` 校验，用户明确同意后才真实创建（会直接发布）。返回的 `templateId` 仅用作后续 `--interviewCode`。
2. 发起：`ihr-cli conference +launch`
   ```bash
   ihr-cli conference +launch \
     --title "候选人A 数字人初面" \
     --purposeId purpose_002 \
     --startTime "2026-05-28T15:00:00+08:00" \
     --thirdPartyPlatform DIGITAL_AVATAR \
     --interviewCode "<avatar-template-Id>" \
     --interviewers '[{"staffId":"1","name":"数字人面谈官","sourceType":"DIGITAL_HUMAN"}]' \
     --interviewees '[{"name":"候选人A","sourceType":"EXTERNAL","phone":"<sample-phone>","email":"<示例邮箱·请替换为真实候选人邮箱>"}]' \
     --dry-run
   ```
   - 关键约束：数字人面谈通过 `thirdPartyPlatform=DIGITAL_AVATAR` 或 `interviewMode=DIGITAL_AVATAR` 表达；必须传 `--interviewCode`；候选人为唯一 `interviewees[0]`，必须有 `name` + `phone` 或 `email`；不支持 `others`；真人监考官仅在 `allowObserverIntervention=true` 时作为唯一非 `DIGITAL_HUMAN` 面谈官传入。`startTime` 用 `Asia/Shanghai` 的 ISO-8601 offset（`+08:00`）。
3. 复盘：`ihr-cli conference +search`（候选场次+预览）→ 锁定场次 → `conference +documents`（纪要/摘要/待办/转写；仅按需开启 `fullDetail`）。权限为 `DENIED` 的字段不猜测、不补写。

**铁律**：内部人员 `staffId` 必须来自 `ihr-cli base +selectStaffs` 或用户确认值，禁止凭姓名猜；不外泄 `roleCode`/`DA_*`/`REGULAR_*` 等后端字段；不硬编码 Token/密码。

### A-2. 其他数字人面试系统（通用适配）

- 设计层与 A-1 完全一致（岗位画像/维度/题/评分/复盘框架），产出**平台无关的面试方案规格**。
- 执行层：请用户提供该系统的接入方式（开放 API / SDK / 手动后台）。agent 将其字段语义映射到本方案的维度与题目（如"评价维度→系统评分项""面试题→系统题目库""候选人→系统候选人档案"），并给出该系统的发起/复盘操作要点。
- 若系统完全未知，先交付规格文档，待用户补充接入信息后再落地。

---

## B. 无代码平台搭建 · 可选后端

### B-1. 轻流（qingflow）— 可执行（提供开放 API）

**前置**
- 引导用户在轻流开放平台完成连接认证：无账号则先在轻流官网注册；用轻流个人设置 → OpenAPI 生成的 Token 完成认证。以 `workspace_list` 验证可用后进入搭建。
- 用户拒绝连接 → 咨询模式（Phase 0 跳过，止于方案设计）。

**搭建流程（Phase 0–4）**
- Phase 0 连接预检 → Phase 1 需求分析（使用者/数据/流转/输出）→ Phase 2 方案设计（表单/字段/流程/权限矩阵）→ Phase 3 搭建实施 → Phase 4 验证测试（正常/边界/异常三路径）。

**轻流 API 操作速查**
| 操作 | 工具 |
|------|------|
| 应用结构 | `app_schema_apply` / `app_get_fields` |
| 流程 | `app_flow_apply` / `app_flow_get` / `app_flow_get_schema` |
| 视图/图表/布局/门户 | `app_views_apply` / `app_charts_apply` / `app_layout_apply` / `portal_apply` |
| 数据 | `record_insert` / `record_list` / `record_get` / `record_update` / `record_import_start` / `record_export_start` |
| 流程任务 | `task_action_execute` |
| 工作区 | `workspace_list` |

**5 个 HR 场景**：智能招聘引擎 / 培训设计师 / 绩效管理助手 / 入职流程搭建器 / 人力数据看板。可单独用，也可串成"招聘→入职→培训→绩效→看板"闭环；数据经轻流应用中转，契约字段需带"状态"字段，回写前按业务键查重（幂等）。

**常用公式**：自动编号 `CONCAT("QJ-", YEAR(NOW()), "-", LPAD(ROW_NUMBER(),4,"0"))`；请假天数 `DATEDIFF({结束日期},{开始日期})+1`；金额大写 `RMB({金额})`；条件求和 `SUMV({子表单}-{金额}, WHERE({子表单}-{状态}="已确认"))`。

### B-2. 钉钉宜搭 / 飞书多维表格·低代码 / 明道云 等（通用适配）

- 设计层与 B-1 的 Phase 1–2 完全一致（需求四要素 → 表单/字段/流程/权限/视图草图），产出**平台无关的搭建规格**。
- 执行层：请用户提供对应平台的 API/SDK 接入方式。agent 将规格映射到该平台的构件语义（表单→数据表/表单设计器，流程→审批流/自动化，看板→仪表盘/视图，门户→工作台/空间），并给出该平台的创建/配置操作要点。
- 平台未知时，先交付可导入任意平台的规格文档（含字段类型、流程节点、权限矩阵、计算公式）。

### B-3. 不连接任何平台（纯咨询）

- 仅执行设计层，输出结构化方案与可移植搭建规格（字段表/流程图/权限矩阵/公式），供用户在自有平台手动落地。

---

## C. 选择时的呈现建议

- 数字人面试可选后端举例：`利唐 i 人事（ihr-cli）` / `其他数字人系统（提供接入方式）`。
- 无代码平台可选后端举例：`轻流` / `钉钉宜搭` / `飞书低代码` / `明道云` / `暂不连接（仅出方案）`。
- 呈现时保持中立，不默认推荐某一家；用户选定后才加载对应档案，确保"无来源依赖 + 运行时可用"。
