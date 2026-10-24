# Universal Multi-Agent Standard (UMAS) v1.0

以业界正在形成的 **Agent2Agent (A2A) Protocol 的 AgentCard** 元数据约定为底座，补充「提示词即产物」类智能体包的通用结构约定。目标：**同一套智能体定义可在多个运行时加载，不必为每个平台重写。**

> **定位声明**：UMAS 是**本专家包自用的元数据组织约定**，未经任何标准化组织批准或注册，
> 也未通过 A2A 一致性测试。「参考 A2A AgentCard」指**字段组织方式对齐**，
> **不等于**「A2A 兼容实现」。各运行时的加载方式与清单优先级见 `PORTABILITY.md`。

## 1. 包结构（通用层，运行时无关）

```
<pack>/
├── agent-card.json        # 通用元数据（必选）
├── UNIVERSAL-STANDARD.md  # 本文件
├── PORTABILITY.md         # 各运行时加载指引（必选）
├── .codebuddy-plugin/     # WorkBuddy 平台清单（随平台提供）
│   └── plugin.json
├── agents/                # 智能体定义（Markdown + frontmatter）
└── skills/                # 能力定义（可选；本包能力经 agent-card.json 的 skills[] 声明）
```

## 2. Agent 定义六要素（每个 agents/*.md 必含）

1. **角色定义** —— 你是谁、服务谁、边界在哪
2. **擅长领域** —— 能力半径，不越界
3. **分析框架** —— 任务的结构化拆解方法
4. **数据获取** —— 取事实的手段，并声明零外部依赖边界
5. **结构化输出模板** —— 交付物形状（markdown / JSON）
6. **回传要求** —— 完成后回传主理人（运行时映射到具体机制）

## 3. 多智能体协作协议（通用）

建团 → 路由 → 中转（成员不直连，消息经主理人） → 回传 → 门控。硬门控（质量 / 合规 / 学术诚信）由主理人统一守住，成员不得擅自放宽。运行时映射见各包 `PORTABILITY.md`。

## 4. agent-card.json 字段

| 字段 | 含义 |
|---|---|
| `schemaVersion` | 固定 `umas-1.0` |
| `id` / `name` / `version` | 包标识 |
| `type` | `agent`（单 Agent）或 `team` |
| `collaboration.topology` | `orchestrator-worker` 或 `single` |
| `agents[]` | 成员清单（id / name / role） |
| `skills[]` | 能力清单（id / description） |
| `ioModes` | 支持的输入输出模态 |
| `runtimeAdapters` | 已实测可加载的运行时（未实测的不得列入） |
| `standard` | 约定自述（写明所采纳的字段组织方式与边界） |
| `runtimeNote` | 本文件的用途与各运行时的加载入口 |
| `compliance` | P0 红线遵守声明 |

## 5. P0 红线（跨运行时一致）

- **P0-1** 禁用 emoji 作功能图标，图标须为可矢量缩放的 SVG / 标准字形
- **P0-2** 禁用「Indigo→Pink 渐变 + 发光边框 + 毛玻璃」AI 模板套路
- **P0-3** 禁用 AI 模板味文案（Lorem ipsum / 硬编码颜色 / 弹跳缓动）

## 6. 合规边界

- 零外部依赖：不引入需 API key / 付费 / 强制联外网的组件
- 门控只增不减
- 不新增智能体：能力增量走 skill / references / 契约层
