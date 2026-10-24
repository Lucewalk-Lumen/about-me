> 本文件是用于把 agent / skill 制作从字段合规提升为生产级工程设计的规范沉淀（平台无关）。

# 生产级 Agent / Skill 制作参考 Specs

> 本文用于指导 agent / skill、agent-pack、workspace 与配套 skill 的设计、制作、评审和发布（平台无关）。它不是替代任何宿主的字段协议，而是补充一套面向“做对 Agent / Skill”的工程设计规范。

## 1. 核心定位

### 1.1 Agent 的工程定义

生产级 Agent 不应被设计成“万能聊天机器人”，而应被设计成：

> **确定性软件流程中的一个智能决策节点：读取上下文，产出结构化下一步动作，由代码、工具、网关或人类协作层执行。**

因此，一个合格 Agent 的最小闭环是：

```text
Trigger -> Thread/Event State -> Context Builder -> LLM Decision -> Structured Action -> Deterministic Runtime -> Persisted Result
```

### 1.2 基本设计原则

- **小而聚焦**：一个 agent 只覆盖一个明确职责边界，避免全能型、长链路、跨领域自治。
- **上下文可控**：不要把原始日志、完整历史和无关资料直接塞进模型；上下文应可裁剪、可压缩、可解释。
- **输出契约化**：模型输出必须能被解析、验证、审计和重放，优先输出结构化 intent / tool call / action plan。
- **执行确定性**：模型决定“下一步做什么”，代码或平台决定“是否允许、如何执行、何时暂停、何时恢复”。
- **状态可恢复**：执行状态与业务状态应统一进入 thread / event log / runtime state，避免隐式内存态。
- **人类可介入**：澄清、审批、确认、升级人工都应被建模为标准动作和事件，而不是临时旁路逻辑。
- **发布可验收**：每个 agent 必须有 prompts、testCases、smoke case、README、安装校验和风险扫描。

## 2. Agent 制作分层 Specs

### SPEC-01：职责边界与适用范围

**目标**：先定义 agent 的“窄边界”，再设计 prompt、tools、skills 和 tests。

**必须满足**：

- `displayName`、`role`、`description` 能让用户在 30 秒内理解它解决什么问题。
- agent 只覆盖一个主任务域，例如“会议纪要整理”“代码 Review”“客服工单分流”，不把多个弱相关任务塞进同一 agent。
- 对不适用场景有明确拒绝或转人工策略。
- 复杂流程应拆成多个 agentic node 或 subagent，而不是让一个 agent 承担整条业务链路。

**禁止**：

- “全能助手”“行业专家”“企业智能体专家”等不可辨识定位。
- 既做需求分析、又做编码、又做发布、又做运营的超大 agent。
- 通过堆叠大量 skills 掩盖职责边界不清。

### SPEC-02：Prompt 作为一等资产

**目标**：prompt 必须可见、可版本化、可评审、可测试。

**必须满足**：

- prompt 明确写出：角色、输入范围、处理步骤、输出结构、禁止事项、失败处理。
- prompt 不依赖框架隐藏默认值表达核心行为。
- prompt 与 `testCases.expected` 形成可回归关系；修改 prompt 后必须能解释影响范围。
- 面向用户的快捷 prompts 应是 3-5 个真实场景入口，而不是泛化请求。

**推荐结构**：

```md
你是 {角色}，负责 {窄领域任务}。

输入可能包括：
- {输入类型 1}
- {输入类型 2}

你需要：
1. 判断用户意图是否属于职责范围。
2. 提取完成任务所需的关键事实。
3. 如信息不足，先提出澄清问题。
4. 如需要外部动作，只输出结构化动作建议。
5. 输出必须符合 {格式约束}。

禁止：
- {超范围行为}
- {高风险动作}
- {未确认即执行的动作}
```

### SPEC-03：上下文工程

**目标**：把 context 设计成模型可用的数据产品，而不是历史消息堆积。

**必须满足**：

- 区分三类信息：当前任务必需事实、可引用状态、历史审计记录。
- 只把当前决策需要的信息放入模型上下文，其他信息保存在 state / artifact / 外部引用中。
- tool result、human response、error、approval result 等事件进入统一 thread 后再序列化给模型。
- 长历史必须支持摘要、裁剪或结构化压缩。

**推荐上下文格式**：

```xml
<thread>
  <user_request>...</user_request>
  <known_facts>...</known_facts>
  <constraints>...</constraints>
  <previous_actions>...</previous_actions>
  <pending_human_inputs>...</pending_human_inputs>
  <recent_errors>...</recent_errors>
</thread>
```

**禁止**：

- 将完整日志、完整 stack trace、大量无关检索结果直接塞入上下文。
- 让模型从散乱上下文中猜测当前状态。
- 把敏感信息、凭证、会话凭证、真实客户数据放入 prompt 或 workspace 文档。

### SPEC-04：结构化动作与工具调用

**目标**：把 tool call 理解为模型输出的结构化 intent，而不是直接执行副作用。

**必须满足**：

- 每个工具动作有明确 schema：`intent/type`、参数、风险等级、是否需要审批、幂等键或 trace id。
- 模型只负责产出 action；执行前由确定性代码完成 schema 校验、权限校验、风控和审批判断。
- 高风险动作必须允许停在“动作已选择但尚未执行”的窗口。
- tool result 必须写回 thread，供下一轮决策或最终答复使用。

**推荐 action schema**：

```json
{
  "intent": "request_approval | call_tool | ask_human | final_answer",
  "toolName": "string",
  "arguments": {},
  "riskLevel": "low | medium | high | critical",
  "requiresApproval": true,
  "reason": "为什么需要这个动作",
  "idempotencyKey": "optional-stable-key"
}
```

### SPEC-05：统一执行态与业务态

**目标**：让 agent 可重放、可恢复、可审计。

**必须满足**：

- thread / event log 是核心状态载体，至少记录 user input、model action、tool result、human response、error、final output。
- runtime state 记录 templateId、templateVersion、agentId、validation、安装来源、执行摘要。
- 任何暂停点都必须能从持久化状态恢复，不依赖进程内变量。
- 状态中如有大对象、敏感对象或不可序列化对象，应存引用和摘要，不直接内嵌。

**推荐事件模型**：

```json
{
  "threadId": "thread-<id>",
  "events": [
    { "type": "user_input", "content": "...", "createdAt": "..." },
    { "type": "model_action", "action": {}, "createdAt": "..." },
    { "type": "tool_result", "toolName": "...", "result": {}, "createdAt": "..." },
    { "type": "human_response", "content": "...", "createdAt": "..." },
    { "type": "error", "summary": "...", "retryable": true, "createdAt": "..." }
  ]
}
```

### SPEC-06：Launch / Pause / Resume 生命周期

**目标**：agent 应能被外部系统稳定启动、暂停、恢复和查询。

**必须满足**：

- 启动入口接受用户消息、事件、webhook、cron 或系统触发。
- 恢复入口基于稳定 `threadId` / `requestId` / `approvalId`，而不是临时内存对象。
- 暂停原因必须明确：等待澄清、等待审批、等待外部回调、达到失败阈值、任务完成。
- 恢复后继续读取持久化 thread，并追加新事件，而不是重跑全流程。

**推荐 API 语义**：

```text
POST /agents/{agentId}/threads              # launch
POST /agents/{agentId}/threads/{threadId}/events  # resume by external event
GET  /agents/{agentId}/threads/{threadId}   # inspect state
```

### SPEC-07：Human-in-the-loop 规范

**目标**：把人类交互纳入标准工作流。

**必须满足**：

- 澄清信息、审批请求、人工确认、任务升级分别有独立 intent。
- 人类回复进入 thread 后作为普通事件继续驱动模型决策。
- 审批类动作必须展示：动作摘要、参数、风险、执行后果、可拒绝选项。
- 高风险或不可逆动作不得绕过人类审批。

**推荐人类动作类型**：

- `ask_clarification`：信息不足，需要用户补充。
- `request_approval`：模型已选择高风险动作，需要授权。
- `escalate_to_human`：连续失败、超范围或低置信度时交给人工。
- `done_for_now`：当前阶段完成，等待用户下一步输入。

### SPEC-08：显式控制流

**目标**：控制流由确定性代码掌控，而不是交给黑盒 agent loop。

**必须满足**：

- runtime 能清楚解释 agent 为什么继续、暂停、失败或完成。
- 同步工具、异步工具、人工审批、外部 webhook、最终输出分支分别处理。
- 失败重试、限流、审批、降级、超时、幂等都在确定性控制流中实现。
- subagent 调用必须受 `allowAgents` 控制，并记录调用原因和结果。

**推荐控制流骨架**：

```text
while not terminal:
  context = buildContext(thread)
  action = llm.decide(context)
  validate(action)
  switch action.intent:
    call_tool -> maybe approve -> execute -> append result
    ask_human -> persist pause -> notify human -> return
    request_approval -> persist pause -> request approval -> return
    final_answer -> append final -> return
    error -> compact -> retry or escalate
```

### SPEC-09：错误压缩与自恢复

**目标**：允许模型基于压缩错误进行有限自恢复，同时防止错误自旋。

**必须满足**：

- tool failure 写回 thread 时应包含错误摘要、失败位置、可重试性、建议修正方向。
- 连续失败必须有阈值，例如同类错误 2-3 次后停止并升级人工。
- 不向模型暴露完整敏感 stack trace、凭证、内部路径或大量无关日志。
- 重试必须有变化：参数修正、上下文补充、降级策略或人工确认。

**推荐错误事件**：

```json
{
  "type": "error",
  "source": "tool:<name>",
  "summary": "参数缺失：projectId 为空",
  "retryable": true,
  "failureCount": 1,
  "nextAllowedActions": ["ask_clarification", "retry_with_fixed_args", "escalate_to_human"]
}
```

### SPEC-10：触发入口与用户渠道

**目标**：agent 能工作在用户原有渠道中，而不是只能在聊天框中使用。

**必须满足**：

- 明确支持哪些触发入口：Chat、CLI、Webhook、Cron、IM、邮件、告警、审批流等。
- 每种入口都要解决身份、权限、幂等、审计和去重问题。
- 输出尽量回到触发来源所在渠道，避免强迫用户切换上下文。
- 定时任务应优先使用隔离会话，避免污染主会话上下文。

### SPEC-11：Stateless Reducer 设计

**目标**：agent 逻辑尽量写成 `(state, event) -> next state/action`。

**必须满足**：

- 同一 thread 状态在同一版本 prompt / schema 下可重放。
- reducer 外部只保留可替换的运行时依赖，例如 LLM client、tool executor、state store。
- 不依赖隐藏单例、进程内缓存或全局可变状态决定业务结果。
- agent 版本升级、回滚、迁移时能基于状态文件解释历史行为。

### SPEC-12：预取与上下文补全

**目标**：确定性可获取的信息由代码预取，减少模型无意义 tool roundtrip。

**必须满足**：

- 对高命中、低成本、强相关数据做预取，例如用户 profile、项目配置、当前工单状态、常用枚举。
- 预取结果要摘要化进入 context，不应造成上下文污染。
- 低命中或高成本数据不应盲目预取，应由模型提出结构化动作后再获取。

## 3. Agent-Pack 制作落地要求

### 3.1 必备交付物

每个可发布 agent 至少包含：

- `manifest.json`：pack 身份、版本、兼容性、agent 清单。
- `agents/{agent}/config.json`：agent 身份、描述、prompts、testCases、skills、tools、cron 等。
- `agents/{agent}/workspace/IDENTITY.md`：模板 ID 与 agent 名称锚点。
- `agents/{agent}/workspace/AGENTS.md` 或等价运行说明：核心行为、边界、工具使用方式。
- `agents/{agent}/workspace/skills/{skill}/SKILL.md`：仅当使用本地 skill 时必须存在。
- `README.md`：安装前可理解用途、边界、快捷 Prompt、验收用例和安装方式。

### 3.2 config 描述文案

`config.json.description` 必须继续遵循三段式：

```md
## 我的介绍
{1 个自然段说明角色、领域、输入、处理能力、输出价值}

## 能帮你做什么
• {能力项} — {具体说明}

## 内置技能
• **{skill-name}**：{skill 在工作流中的职责}
```

三段式文案必须同时满足：功能可辨识、中文可读、无客户/人员/Owner/PDSA 等来源追踪信息、与 README 口径一致。

### 3.3 prompts 与 testCases

- 每个 agent 必须有 3-5 个 `prompts`。
- 每个 agent 必须有 3-5 个 `testCases`。
- 至少 1 个 testCase 包含 `smoke` 标签。
- testCases 应覆盖：happy path、edge case、integration / skill / subagent 场景。
- `expected` 应写可验收断言，不写完整期望输出。

### 3.4 skills 与 tools

- skill 是工作流能力，不是职责边界的替代品。
- 外部技能市场 / 第三方来源的 skill 只能作为导入阶段临时来源，发布前必须内联固化到本地 `skills/`。
- 本地 skill 目录名、`config.json.skills[].name`、`path` 最后一段、`SKILL.md` frontmatter `name` 必须一致。
- `tools.allow` 默认应保持最小化；确需开放时必须说明原因与风险。
- 高风险工具必须通过审批或在隔离环境中执行。

### 3.5 cron / webhook / 外部触发

若 agent 声明后台或定时能力：

- `cron.jobs[].payload.message` 必须明确具体任务，不得是泛化“开始工作”。
- 周期任务推荐 `sessionTarget: isolated`。
- webhook 入口必须有幂等、签名或来源校验设计。
- 触发结果必须可追踪到 thread / task / run id。

## 4. 设计评审 Checklist

### 4.1 立项前

- [ ] agent 职责是否足够窄？
- [ ] 是否能用一句话说明输入、处理、输出？
- [ ] 是否存在应拆分为多个 agent / skill / deterministic step 的部分？
- [ ] 是否有高风险动作、人类审批或权限边界？

### 4.2 制作中

- [ ] prompt 是否显式描述角色、步骤、输出格式和禁止事项？
- [ ] context 是否只包含当前决策必要信息？
- [ ] tools 是否是结构化 intent，而不是模型直接执行副作用？
- [ ] thread / event / state 是否可恢复、可重放？
- [ ] 错误是否有压缩、阈值和升级策略？
- [ ] human-in-the-loop 是否作为标准事件建模？

### 4.3 发布前

- [ ] manifest/config/workspace/README 路径一致。
- [ ] `IDENTITY.md` 中模板 ID 与 agent 名称一致。
- [ ] prompts/testCases 数量合规，且至少一个 smoke。
- [ ] description 三段式合规，README 与 description 口径一致。
- [ ] 本地 skill 已固化，`SKILL.md` 存在且命名一致。
- [ ] 未包含真实密钥、会话凭证、Token、私钥、客户/人员/Owner/PDSA 信息。
- [ ] 安装脚本或标准安装入口在副作用前完成兼容性校验。
- [ ] smoke validation 或等价测试已通过。

## 5. 常见反模式

| 反模式 | 风险 | 修正方式 |
| --- | --- | --- |
| 万能型 Agent | 上下文膨胀、行为不可预测、测试不可覆盖 | 拆成小 agent + 确定性编排 |
| prompt 外包给框架 | 无法调试、无法回归、质量退化难定位 | prompt 入库、版本化、配 testCases |
| 原始日志直接进上下文 | token 浪费、注意力稀释、敏感信息外露 | 摘要化、结构化、只保留当前必要事实 |
| tool call 直接执行 | 超范围、不可审计、高风险动作无拦截 | schema 校验 + 权限 + 审批 + 幂等 |
| 进程内状态驱动流程 | 重启丢失、无法恢复、无法 replay | thread/event/state 持久化 |
| 错误无限重试 | 自旋、成本失控、用户体验差 | 错误压缩 + 失败阈值 + 升级人工 |
| skills 堆叠替代设计 | 能力看似丰富但主线不清 | 先定义主工作流，再选择必要 skill |
| 只写 demo prompts | 用户不会用，验收不可自动化 | prompts/testCases 覆盖真实业务与边界 |

## 6. 推荐制作流程

1. **定义窄职责**：写清楚 agent 的输入、处理、输出、边界和拒绝场景。
2. **设计状态与事件**：确定 thread 中记录哪些事件，哪些信息进入 context，哪些留在 state。
3. **设计结构化动作**：列出 action/tool/human intent schema 和风险等级。
4. **编写 prompt**：把角色、步骤、输出格式、禁止事项和错误处理写清楚。
5. **选择 skills/tools**：只引入完成该职责必需的能力，发布前固化本地 skill。
6. **补齐 agent-pack 元数据**：manifest、config、IDENTITY、README、三段式 description。
7. **编写 prompts/testCases**：覆盖 happy path、edge case、integration，至少一个 smoke。
8. **执行校验**：结构、兼容、敏感信息、skill、安装、smoke validation 全部通过。
9. **发布与回归**：生成不可变版本产物，记录版本、sha256、安装测试指令和变更说明。

## 7. 一句话总纲

> **做 Agent，不是把模型权限做大，而是把职责做窄、上下文做准、输出做稳、执行做可控、状态做可恢复。**
