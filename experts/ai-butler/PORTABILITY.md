# PORTABILITY · teacher-workbench

本包遵循 [UNIVERSAL-STANDARD.md](./UNIVERSAL-STANDARD.md) (UMAS v1.0)，
以 WorkBuddy 为已实测运行时；其余运行时为**映射指引**（基于同一份 `agents/*.md`，
未经本包实测，接入时请以目标框架文档为准）。

- 包类型：`agent`
- 形态：单 Agent
- **定位**：教师工作台（`teacher-workbench`）——上课、会议、科研与日常办公事务一屏打理，纯本地离线、数据不出本机

## 1. WorkBuddy（原生兼容）

- 清单：`.codebuddy-plugin/plugin.json` 已声明 agents。
- 单 Agent `agents/ai-butler.md` 直接加载运行，无需建团、无成员调度；用户请求按 agent 提示词路由处理。
- 本地桥（`bridge/teacher-workbench-bridge.js`）与工作台（`assets/teacher-workbench.html`）随包提供，由 agent 按需调用。

## 2. CrewAI

- `agents/ai-butler.md` 映射为一个 `CrewAI Agent`：`role`← 角色定义，`goal`← 擅长领域，`backstory`← 分析框架+数据获取。
- 单 Agent 场景直接以该 Agent 执行任务；如需多角色可后续扩展。

## 3. AutoGen (Microsoft)

- `agents/ai-butler.md` 映射为 `autogen.AssistantAgent(system_message=<md 正文>)`。
- 单 Agent 以直接对话方式运行；工作台交互经本地桥完成。

## 4. LangGraph

- `agents/ai-butler.md` 映射为一个 graph 节点（函数，system prompt = md 正文）。
- 单节点图即完整执行流；本地桥与工作台作为外部工具接入。

## 5. OpenAI Agents SDK

- `agents/ai-butler.md` 映射为 `Agent(name=id, instructions=<md 正文>)`。
- 单 Agent 直接运行；工作台交互经本地桥完成。

## 通用映射要点

- **单 Agent** → 直接以本 agent 为执行主体，无需建团/编排多成员
- **工作台交互** → 经本地桥（127.0.0.1 回环）读写，跨框架一致
- **消息中转** → 本包无成员，不涉及成员间通信
