# Open WorkBuddy 开发标准（官方权威快照）

> 抓取方式：经 Edge 浏览器（browser-skill）实测渲染，于 2026-10-06 抓取并核对
> 性质：官方文档快照，作为本专家团内置「开发标准知识库」的单一权威来源
> 更新机制：见 `scripts/sync_standards.py` —— 每次运行对线上文档做哈希比对，发现标准变动即产出 diff 并提示复核

本文件覆盖三类可交付形态（技能 / 专家 / 专家团）的官方目录结构、plugin.json / SKILL.md 字段规范、行业分类枚举与协作铁律。本专家团（workbuddy-expert-studio）本身是一个**专家团（team）**形态包，其打包规则以「专家团」一节为准。

---

## 0. 三类形态速查

| 形态 | plugin.json.expertType | 最小结构 | 适用 |
|------|------------------------|----------|------|
| 技能 Skill | （无 plugin.json，独立 SKILL.md） | `{skill}/SKILL.md` + references/scripts/templates | 把一段可复用工作流封装成能力，AI 自动或手动触发 |
| 专家 Expert | `agent` | `.codebuddy-plugin/plugin.json` + `agents/*.md` + `avatars/` | 单人格角色切换，一个 Agent 扛全部职责 |
| 专家团 Expert-Team | `team` | 同专家 + `teamInfo`/`members` + 多 `agents/` | 多角色协作执行，主理人编排、成员各司其职 |

> 选型原则：流程短、单人可闭环 → 技能或专家；需要多视角辩论 / 分阶段协作 / 硬门控统一把守 → 专家团。本专家团即采用专家团，因为「诊断→设计→实现→审计→打包→放行」天然是多角色分阶段协作。

---

## 1. 专家团（team）官方规范

### 1.1 目录结构（必须项标 ★）

```text
my-team/
├── .codebuddy-plugin/
│   └── plugin.json          # ★ 配置文件（必须）
├── avatars/                 # ★ 头像目录（必须）
│   ├── team.png             # 团队头像
│   ├── team-lead.png        # 主理人头像
│   ├── member-a.png         # 成员头像
│   └── member-b.png
├── agents/                  # ★ Agent 定义（必须）
│   ├── {team}-team-lead.md  # 主理人（名称须加专家团前缀，不可用通用 team-lead）
│   ├── member-a.md
│   └── member-b.md
├── skills/                  # 共享技能（可选）
│   └── {skill-name}/
│       ├── SKILL.md
│       ├── references/
│       ├── scripts/
│       └── templates/
├── .mcp.json                # 内置 MCP / 连接器依赖声明（可选）
├── bin/                     # 可执行文件（可选）
├── settings.json            # ★ 设置主理人（必须）
└── README.md                # 说明文档（推荐）
```

### 1.2 plugin.json 字段规范

**基础字段（必填）**

| 字段 | 必填 | 类型 | 说明 |
|------|------|------|------|
| name | ✅ | string | 专家唯一标识（小写字母 + 连字符，如 `"design-experts"`） |
| expertType | ✅ | string | 填 `"team"` |
| version | ✅ | string | 语义化版本，如 `"1.0.0"` |
| description | ✅ | string | 英文简短描述（一句话） |
| author | ✅ | object | `{name, email}` 作者信息 |
| agents | ✅ | string[] | Agent 定义文件路径列表，如 `["./agents/trading-team-lead.md"]` |
| agentName | ✅ | string | 主 Agent 名称（对应 agents/ 下 MD 文件名，不含 .md） |
| teamInfo | ✅ | object | `{leadAgent, memberAgents[]}` |

**可选字段**

| 字段 | 必填 | 类型 | 说明 |
|------|------|------|------|
| skills | — | string[] | 技能目录路径列表（如 `["./skills/my-skill"]`） |
| homepage | — | string | 项目主页 URL |
| license | — | string | 许可证（建议填 SPDX 标识符，如 `"MIT"`） |
| keywords | — | string[] | 搜索标签 |
| dependencies | — | object | 运行时依赖的 MCP / 连接器（`{mcpServers, connectors}`；亦可放插件根 `.mcp.json` 兜底） |

> 注：`skills` 在 plugin.json 里填**技能目录路径**（`./skills/<name>`），与 Agent frontmatter 的同名 `skills`（填**技能名称**，见 1.3）语义不同，勿混用。

**teamInfo 结构**
```json
{ "leadAgent": "主 Agent 名称", "memberAgents": ["成员A名称", "成员B名称", "..."] }
```

**展示字段（必填）**

| 字段 | 必填 | 类型 | 说明 |
|------|------|------|------|
| displayName | ✅ | {en, zh} | 市场展示名称 |
| profession | ✅ | {en, zh} | 职业头衔：**必须与 displayName 保持一致** |
| displayDescription | ✅ | {en, zh} | 市场展示描述：**中文字数须在 40–50 字之间**，突出核心能力 |
| avatar | ✅ | string | 头像路径（相对路径，如 `"avatars/expert.png"`） |
| categoryId | ✅ | string | 行业分类（见第 4 节枚举） |
| defaultInitPrompt | ✅ | {en, zh} | 首次对话默认提示语：**必须与 quickPrompts 第一条保持一致** |
| plugin | ✅ | string | 关联 Plugin 名称（**与 name 字段值一致**） |
| tags | ✅ | {en, zh}[] | 擅长领域标签（**固定 3 个**） |
| quickPrompts | ✅ | {en, zh}[] | 推荐提示词（**固定 3 个**），展示在专家卡片 |

**成员字段（必填）**：`members`(array) 所有团队成员列表（含主理人）。每个成员对象：

| 字段 | 必填 | 类型 | 说明 |
|------|------|------|------|
| id | ✅ | string | 成员标识（对应 Agent MD 文件名，不含 .md） |
| name | ✅ | {en, zh} | 成员名称 |
| profession | ✅ | {en, zh} | 成员职业头衔 |
| avatar | ✅ | string | 成员头像路径 |
| role | ✅ | string | `"lead"`（主理人）或 `"member"`（成员） |

### 1.3 Agent 定义文件 frontmatter

| 字段 | 必填 | 说明 |
|------|------|------|
| name | ✅ | Agent 标识（与文件名一致，不含 `.md`） |
| description | ✅ | Agent 功能描述（英文，AI 用来判断何时激活） |
| displayName | ✅ | 显示名称，含 en / zh 两个子字段 |
| profession | ✅ | 职业头衔，含 en / zh 两个子字段 |
| maxTurns | — | 最大对话轮数（默认 50） |
| skills | — | 预加载的技能名称列表 |

```yaml
---
name: trading-team-lead
description: Trading analysis team lead - orchestrates 5-phase investment analysis workflow
displayName:
  en: "He"
  zh: "何执舟"
profession:
  en: "Chief Strategist"
  zh: "首席策略官"
maxTurns: 200
skills:
  - my-skill
---
```

> 注：`skills` 官方为**可选**，此处填**技能名称**（如 `workbuddy-expert-studio-toolkit`），声明后该 Agent 预加载对应技能；与 plugin.json 的同名 `skills`（填**技能目录路径**，见 1.2）语义不同，勿混用。

### 1.4 协作铁律（官方 + 本团强化）

1. **建立团队**：任务开始时由主理人亲自创建本次任务的团队（建议命名 `{team}-<任务简称>`），明确边界与上下文。**TeamCreate 必须且只能由主理人执行，严禁委派成员创建团队**。
2. **调度成员**：按 SOP 阶段将成员拉入协作、下发独立任务；成员作为独立协作方输出专业产出，**不得由主理人代写**。
3. **消息中转**：成员产出回传主理人，由主理人汇总、转交下一阶段；**所有跨成员信息流经主理人中转，不得互相直连**。
4. **成员结论为准**：任何专业产出必须由对应成员输出后再采信，主理人只做编排与汇编。
5. **硬门控不下移**：质量 / 合规 / 安全类门控由主理人统一把守，成员不得擅自放宽。

### 1.5 工具权限（官方约束）

> 开发者**不可自行添加 tools**：所有工具权限由系统统一分配。
> 系统内置工具（仅供了解）：Read / Write / Grep / Glob / Bash / WebSearch / WebFetch / AgentTool（主 Agent 可用）/ SendMessage（主 Agent 可用）。

---

## 2. 专家（agent）官方规范

### 2.1 目录结构
```text
my-expert/
├── .codebuddy-plugin/plugin.json
├── avatars/expert.png
├── agents/my-expert.md
└── README.md
```

### 2.2 plugin.json（agent 型）

与专家团基础字段一致，差异：
- `expertType` 填 `"agent"`
- `teamInfo` 仅 `expertType=team` 时需要
- 展示字段与专家团完全一致（displayDescription 40–50 字、tags/quickPrompts 固定 3 个、defaultInitPrompt==quickPrompts[0]、plugin==name）

Agent frontmatter 同 1.3（name / description / displayName / profession / maxTurns；可选 `skills`）。

---

## 3. 技能（skill）官方规范

### 3.1 目录结构
```text
{skill-name}/
├── SKILL.md          # ★ 技能定义（必须）
├── references/       # 参考资料（可选），AI 执行时读取作为上下文，用 @references/xxx.md 引用
├── scripts/          # 可执行脚本（可选），AI 通过 Bash 执行
└── templates/        # 模板文件（可选）
```

### 3.2 SKILL.md frontmatter

| 字段 | 必填 | 说明 |
|------|------|------|
| name | 否 | 技能标识 |
| description | 是 | 写清用途和触发词 |
| description_zh | 是 | 简短中文介绍 |
| description_en | 是 | 简短英文介绍 |
| display_name | 否 | 展示名称 |
| display_name_en | 否 | 展示名称（英） |
| category | 否 | 分类之一 |
| version | 是 | 版本号 |
| author | 是 | 合作方名称 |
| allowed-tools | 否 | 工具白名单（逗号分隔） |
| disable-model-invocation | 否 | true 则 AI 不会自动触发，仅用户手动调用 |
| user-invocable | 否 | false 则隐藏菜单，仅供 AI 内部使用 |

> 注意：技能 frontmatter 与 plugin.json 字段体系不同（技能用 `description_zh`/`description_en`/`display_name`/`category`，专家/专家团用 `displayDescription`/`displayName`/`categoryId`）。混用会导致解析失败。

---

## 4. 行业分类枚举（categoryId，15 类）

| categoryId | 分类名称 | 覆盖范围 |
|------------|----------|----------|
| 01-ProductDesign | 产品设计 | 产品管理、UI/UX、品牌设计、需求分析 |
| 02-Engineering | 技术工程 | 前后端开发、架构、DevOps、安全 |
| 03-GameSpatial | 游戏空间 | 游戏设计与开发、VR/AR/MR、空间计算 |
| 04-DataAI | 数据智能 | 数据分析、机器学习、知识管理、AI 应用 |
| 05-MarketingGrowth | 营销增长 | 广告投放、SEO/SEM、增长黑客、内容营销 |
| 06-ContentCreative | 内容创作 | 文案写作、视频制作、设计创意、多媒体 |
| 07-SalesCommerce | 销售商务 | 客户开发、销售策略、电商运营、BD |
| 08-FinanceInvestment | 金融投资 | 投资分析、风险管理、量化交易、财务 |
| 09-OperationsHR | 运营人力 | 运营策略、人力资源、行政管理、培训 |
| 10-ProjectQuality | 项目质量 | 项目管理、质量保证、测试、流程优化 |
| 11-SecurityCompliance | 法务安全 | 信息安全、合规审计、法律咨询、风控 |
| 12-IndustryConsultant | 行业顾问 | 行业咨询、战略规划、专业服务、供应链 |
| 13-TencentZone | 腾讯专家 | 腾讯内部部门提供，腾讯云/微信小程序/企业微信等 |
| 14-WorldWise | 全球发展 | 国际化业务、跨境贸易、全球市场洞察、海外拓展 |
| 15-Education | 教育学习 | 教育培训、在线学习、课程设计、学术研究、知识传播 |

> 选型：本专家团（专家开发）归入 **02-Engineering**；教学场景用例可挂 **15-Education**；企业专业开发用例归 **02-Engineering** 或 **12-IndustryConsultant**。

---

## 5. 合规硬指标清单（打包前自校验）

以下指标由本专家团 `scripts/verify.py` 门禁自动核对（来源：字段规范 + 团队包运维经验）：

1. `name` == 顶层目录名 == `plugin` 字段值（三方一致）
2. `expertType` 取值 `agent` / `team`；`team` 时 `teamInfo` 齐全且 `members` 仅含 `id/name/profession/avatar/role`
3. `displayDescription.zh` 中文字数 **40–50**
4. `tags` 与 `quickPrompts` 各 **固定 3 个**
5. `defaultInitPrompt` 与 `quickPrompts[0]` 文本一致
6. `categoryId` 属于第 4 节 15 类枚举
7. `profession` 与 `displayName` 保持一致
8. `agents[]` 每一项路径真实存在；主 Agent 名 == `agentName` == `teamInfo.leadAgent`
9. 头像文件全部可达，无断链
10. `settings.json` 的 `agent` 指向主理人

---

## 6. 标准漂移处理

当 `scripts/sync_standards.py` 检测到线上文档与本节快照哈希不一致时：
- 自动备份当前快照到 `knowledge/_archive/`
- 生成 `knowledge/STANDARDS-DIFF-<YYYYMMDD>.md` 列出变动字段
- 提示主理人复核并更新本文件与被影响的门禁脚本
- 不自动覆盖生产规则，避免「修扫描器而非内容」的反模式
