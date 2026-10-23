---
name: architect
version: 1.1.1
description: 通用 Agent / Skill 生产级制作、校验与交付工作流（平台无关，已对齐 WorkBuddy）。交互式收集需求，设计职责边界、上下文、结构化动作、人类介入与错误恢复；按生产级规范生成并校验技能（SKILL.md）/ agent，复用本宿主原生能力（find-skills 技能发现、SkillManage / 专家中心交付），产出可直接安装的技能包。
---

# Agent / Skill Creator Builder（通用版）
> **归属**：领域技能层——智能体架构专家（architect）


> 本技能是**平台无关**的 agent / skill 制作方法论 + 校验器。一条场景化想法 → 职责清晰、上下文可控、输出可契约、状态可恢复、可校验的技能 / agent 模版。在 WorkBuddy 中开箱即用。

## 使用时机

- “帮我做一个 agent / 技能 / 专家”
- “生成 SKILL.md / 校验项 / 设计文档”
- “按生产级规范优化 agent / skill”
- “设计职责边界、上下文、结构化动作、状态恢复”
- “校验 / 打包这个技能”

## 平台无关核心方法论（主干）

1. **先扫描、少提问**：用 `scripts/scan_existing_skills.py` 扫描本宿主已有技能；相似度 `>= 0.72` 建议修改已有，`0.45–0.72` 给候选让用户选，`< 0.45` 直接新建。每轮最多 3 个阻断问题，其余字段用可审计默认值。
2. **默认值补全**：名称、分类、触发描述、prompts/testCases、最小权限、三段式描述。
3. **生产级设计**：职责边界、上下文工程、结构化动作、状态恢复、人类介入、错误压缩（详见 `references/production_agent_specs.md`）。
4. **校验**：`scripts/validate_pack.py`（通用）。
   `material-extractor` 生成的文档技能包亦统一在此校验（其内置 `validate_skill.py` 仅作开放标准前置检查，最终权威校验仍由本技能完成）。
5. **交付**：产出技能包（`SKILL.md` + `references/`、`scripts/`、`assets/`）；在 WorkBuddy 中由宿主加载即可。

## 本宿主适配：WorkBuddy

- **技能发现**：用 `find-skills` 技能（Skill 工具 `command="find-skills"`）从推荐市场搜索并安装；也可让用户直接提供 slug 或本地技能目录。
- **交付格式**：WorkBuddy 技能 = 目录 + `SKILL.md`（frontmatter 含 `name` / `description`）+ 可选 `references/`、`scripts/`、`assets/`。
- **安装**：把技能目录放到 `~/.workbuddy/skills/`（用户级）或 `<workspace>/.workbuddy/skills/`（项目级）；宿主自动识别加载，无需命令。
- **专家形态**：若目标是专家（Expert Center），改用 `expert-manager` 技能走专家包生命周期。

## 生产级设计要点（通用，详见 `references/production_agent_specs.md`）

- **职责边界**：一句话说明输入、处理、输出；列出明确不做的事、拒绝策略、是否需要拆分 subagent / skill / 确定性步骤。
- **上下文工程**：区分当前任务必需事实、可引用状态、历史审计记录；长历史、tool result、error 必须摘要化 / 结构化后进入模型上下文。
- **结构化动作**：`intent`、参数、风险等级、审批要求、原因、幂等键；模型只产出 action，确定性代码负责校验、权限、审批与执行。
- **状态恢复**：事件日志至少记录 `user_input` / `model_action` / `tool_result` / `human_response` / `error` / `final_output`；暂停点必须可基于 `threadId` / `requestId` / `approvalId` 恢复。
- **人类介入**：澄清、审批、确认、升级人工必须是标准 intent；高风险或不可逆动作不得绕过审批。
- **错误压缩**：只暴露摘要、失败位置、可重试性、失败次数、下一步动作；同类错误连续 2–3 次后停止并升级人工。

## Skill 最佳实践（详见 `references/skill_best_practices.md`）

- frontmatter 必含 `name` 和清晰的 `description`，description 应说明**何时使用**而非泛泛介绍能力。
- 单一职责：围绕明确工作流、检查清单、参考资料、脚本组织目录。
- 不把完整人格、泛化闲聊或一次性项目记录写进 skill；可复用流程、规范、校验规则、工具脚本才适合进入 skill。
- 复杂 skill 输出验收清单：触发场景明确、步骤可执行、引用资料内嵌、反模式已排除、可本地脚本验证。

## 最小权限（通用）

- 默认只声明必需能力；高风险动作（执行、联网、写文件、外部 API、消息、定时任务）必须写明用途与审批路径。

## 通用校验项（详见 `references/skill_checklist.md`）

- `SKILL.md` 存在，frontmatter 含 `name` / `description`。
- `name` 与目录名一致。
- `SKILL.md` 中引用的 `references/`、`scripts/`、`assets/` 路径存在。
- 文本文件中不含敏感信息（`token` / `secret` / `key` / `password` 等）。
- 若含 `prompts` / `testCases`，数量为 3–5，且至少 1 个带 `smoke`。

## 内置脚本

| 脚本 | 用途 |
| --- | --- |
| `scripts/validate_pack.py <pack-dir>` | 通用校验（结构、frontmatter、引用完整性、敏感信息） |
| `scripts/scan_existing_skills.py "<query>" [--limit N] [--base <dir>]` | 扫描本宿主已有技能做相似召回，辅助“先扫描再创建” |
| `scripts/prepare_description_preview.py` | 渲染三段式描述预览（`assets/description-preview.html`） |

## 输出格式

完成制作 / 审查后输出：

- 技能 / agent 名称与（可选）模板 ID。
- 关键文件路径。
- 校验摘要：是否通过；未通过不得宣称可交付。
- 交付物路径 / 安装说明：技能目录放到 `~/.workbuddy/skills/`（或项目级 `.workbuddy/skills/`）即生效，不要求复制执行安装命令。
