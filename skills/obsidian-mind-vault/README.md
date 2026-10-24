# obsidian-mind 知识库专家团

把 Obsidian 知识库变成**给 AI 编码助手用的持久记忆系统**——不是教你记笔记，是给一个知识库装上内容模型、会话生命周期、跨仓检索、绩效证据链、质量门禁和多宿主发布链路。

## 类型

Team 型（多角色协作团队）· 1 名主理人 + 7 名专业成员

## 功能

这套系统解决的是「AI 助手每次都从零开始」的问题。它把知识库拆成四层：**库本体（状态）+ 钩子管道（环境）+ 语义检索层 + 跨仓服务层**，四层之间只有一个协调点（库根的一份机器可读清单）。核心边界是一条：**过程式代码拥有环境，agent 拥有内容。**

专家团能帮你做的事：

- **设计内容模型**：定义每种笔记的路径、命名、必填元数据与生命周期；设计双链图与强制链接规则；写查询视图（数据库式视图、公式列、分组排序）。
- **设计会话生命周期**：五个钩子分别在什么时候做什么；把常驻上下文压在硬上限内；设计渐进披露三层加载；写后校验与卫生漂移扫描（超大笔记 / 主题簇 / 开放循环 / 收件箱压力）。
- **设计跨仓检索与记忆**：让别的项目也能检索、阅读、沿图扩展并回写；设计身份识别、可见性策略、记忆作用域与取代机制、稳定结论的提升路径。
- **编排命令与工作流**：把动作编成命令与子代理；明确每条命令的写入路径；给有副作用的命令配硬护栏；设计交接协议。
- **构建绩效证据链**：让日常产出自动累积成能力证据；维护战功文档与组织记忆；事故复盘；评审季产出三档可见度的材料并逐条核查事实。
- **设质量门禁**：更正扫描（找出所有复述并三分类）、事实核查、结构审计、机械层与判断层分层、以及一道**真能失败**的交付门禁。
- **多宿主与发布**：同一套配置在多个助手平台上等价运行；老库升级迁移；版本指纹、变更日志、从标签树打包的发布流水线。

## 团队构成

| 职能 | Agent ID | 角色 | 职责 |
|------|----------|------|------|
| 持久记忆系统架构师 | `obsidian-mind-vault-team-lead` | 主理人 | 四条核心原则与全部硬规则的唯一持有者；编排七个专业角色、裁定跨层冲突 |
| 知识图谱与内容架构师 | `knowledge-graph-architect` | 成员 | 笔记类型与元数据 schema、双链图、索引与查询视图、超大笔记拆分 |
| 运行时管道工程师 | `runtime-pipeline-engineer` | 成员 | 五个生命周期钩子、注入预算与硬上限、写后校验、卫生漂移扫描、去抖与原子写 |
| 跨仓检索与记忆服务工程师 | `cross-repo-retrieval-engineer` | 成员 | 服务面、身份握手、可见性策略、检索分档、记忆作用域与取代提升 |
| 工作流与命令编排设计师 | `workflow-orchestration-designer` | 成员 | 命令与子代理编排、场景路由、写入路径归属、写权限分层、硬护栏分布 |
| 绩效复盘与职业发展顾问 | `performance-evidence-advisor` | 成员 | 证据链构建、战功文档、组织记忆、事故复盘、评审材料三档可见度 |
| 事实纪律与交付门禁审计师 | `fact-discipline-auditor` | 成员 | 更正扫描三分类、事实核查、结构审计、机械层修复、交付门禁与正负对照 |
| 多宿主适配与发布交付工程师 | `multi-host-release-engineer` | 成员 | 多宿主事件映射、安装侧车、版本指纹与迁移、发布流水线与打包校验 |

## 使用示例

- 「给我的 AI 编码助手加持久记忆。先帮我判断需要哪几层、每层负责什么，再给出落地步骤。」
- 「我的笔记越写越乱、不同笔记之间已经开始互相矛盾，怎么做更正扫描和结构审计？」
- 「评审季要交材料，怎么把日常会话沉淀成一条可辩护的职业证据链？」

## 适用场景

- 你天天用 AI 编码助手，但每次都要重新解释项目背景与历史决策
- 你的 Obsidian / Markdown 笔记越写越多，开始互相矛盾、找不到、没人看
- 你想让别的项目也能查到这套知识，但不想把所有内容对所有人开放
- 评审季到了，你想把日常产出变成说得住的证据，而不是临时回忆
- 你要给一套配置做多平台适配、版本迁移或正式发布

## 交付物示例

- 库内容模型表（笔记类型 / 路径 / 命名 / 必填字段 / 生命周期）
- 会话生命周期设计（钩子清单 + 注入预算表 + 漂移扫描规则）
- 跨仓可见性判定顺序与记忆作用域取值表
- 命令 × 子代理 × 脚本调用矩阵 + 每条命令的写入路径
- 更正计划（分类 / 文件行号 / 原文片段 / 处置）
- 评审简报（私有版 / 经理版 / 同伴版）+ 事实核查报告
- 多宿主事件映射对照表 + 迁移计划（源库只读、可试运行）

## 边界与合规

- 本专家团**不做**笔记排版美化、**不生成** Word / PPT 成品、**不做**图片修图。
- 审计类角色**只找不改**：所有修复动作由用户裁定后执行。
- 所有涉及删除、移动、提交的动作默认**只列不做**，除非用户显式确认。
- 迁移类任务**源库只读**，且必须先出计划、支持试运行。

## 关键词

共 **723** 个检索词，分 17 组（覆盖身份、工具链、内容模型、会话自动化、捕获记录、绩效发展、跨仓检索、质量门禁、迁移升级、发布交付、场景意图、英文市场、同义变体、技术同义、命令与代理名、笔记类型与字段名、专家团专属词）。

**核心身份与定位**（52）：obsidian-mind、obsidian mind、持久记忆系统、AI 持久记忆、第二大脑、第二大脑搭建、外脑、个人知识管理、个人知识库、知识管理、知识库、知识中枢、记忆层、记忆系统、知识沉淀、自组织知识库、自组织笔记、智能体记忆库、AI 记忆库、编码助手记忆、编程助手上下文、笔记系统、笔记体系、知识管理体系、AI 外部记忆、agent 记忆、智能体长期记忆、长期记忆方案、记忆基础设施、记忆中间件、AI 上下文持久化、会话记忆持久化、知识资产、个人知识资产、知识复利、经验沉淀、组织记忆、团队知识库、工作知识库、工程师知识库、开发者知识库、技术笔记系统、研发知识沉淀、知识工作者工具、知识管理工具、知识管理系统搭建、个人 wiki、个人维基、数字花园、digital garden、常青笔记、evergreen notes

**宿主与工具链**（53）：Claude Code、claude code 配置、claude code hooks、claude code 子代理、claude code skills、claude code plugin、claude code mod、claude code 插件、Codex CLI、codex cli hooks、codex 配置、Gemini CLI、gemini cli 配置、gemini hooks、Cursor、Cursor 配置、Windsurf、GitHub Copilot、JetBrains AI、Obsidian、Obsidian 1.12、Obsidian CLI、Obsidian 插件、Obsidian 配置、QMD、qmd 语义检索、qmd 索引、MCP、MCP server、MCP 服务、MCP 配置、Model Context Protocol、ShardMind、shardmind install、Node 22、Node 脚本、TypeScript、零依赖、零运行时依赖、纯 Markdown、本地优先、离线优先、git 版本化笔记、SQLite 索引、本地索引、无构建步骤、直接执行 TypeScript、多宿主适配、宿主兼容、AI 编码助手、AI 编程助手、编码 agent、代码助手

**知识图谱与内容模型**（51）：wikilink、双链、双向链接、反向链接、backlink、知识图谱、graph-first、图优先、frontmatter、YAML frontmatter、属性查询、Obsidian Bases、base 文件、Obsidian 数据库视图、MOC、索引笔记、索引文件、原子笔记、卡片盒、Zettelkasten、PARA、笔记类型、笔记模板、callout、笔记嵌入、embed、block id、块引用、别名链接、断链检测、孤儿笔记、笔记命名约定、笔记目录结构、笔记分类体系、标签体系、tags 约定、笔记生命周期、笔记 schema、内容模型、知识模型、图数据库替代、笔记互链、语义链接、自动补链、笔记聚合页、仪表盘笔记、查询视图、视图定义、笔记归档规则、笔记状态字段、笔记元数据

**会话生命周期与自动化**（52）：SessionStart、UserPromptSubmit、PostToolUse、PreCompact、Stop hook、生命周期钩子、hook 管道、hook 脚本、会话上下文注入、上下文注入、上下文预算、字节预算、注入计量表、渐进披露、token 效率、token 优化、上下文工程、context engineering、斜杠命令、slash command、子代理、subagent、standup、每日站会、wrap-up、会话收尾、收尾清单、卫生漂移、hygiene、去抖、debounce、原子写、幂等写入、审计日志、会话记忆、上下文恢复、会话连续性、会话启动注入、写后校验、消息分类路由、提示注入、上下文压缩、压缩前备份、转录备份、提示状态去重、不重复告警、钩子超时、钩子输出上限、会话交接、收尾报告、卫生扫描、漂移检测

**捕获与工作记录**（50）：会议记录、会议纪要、meeting notes、会议纪要自动化、1:1 笔记、一对一记录、one on one notes、事故复盘、incident postmortem、RCA、根因分析、事后分析、故障复盘、决策记录、decision record、ADR、架构决策记录、项目归档、收件箱路由、笔记自动分类、自动归档、自动打标签、工作日志、工作笔记、周报、周度复盘、每日复盘、会议准备、会前简报、Slack 记录整理、Slack 考古、聊天记录归档、笔记自动整理、知识自动整理、收件箱清零、自由捕获、快速捕获、灵感捕获、转录整理、会议导出处理、项目状态更新、阻塞项跟踪、行动项跟踪、待办提取、议题清单、会议议程生成、周会记录、站会记录、迭代记录、项目日志

**绩效与职业发展**（46）：brag doc、战功文档、战功记录、绩效自评、self-review、同事评审、peer review、绩效复盘、review brief、复盘文档、晋升材料、晋升答辩材料、能力地图、competency map、能力项证据、能力评估、PR 深扫、PR 分析、代码评审证据、职业发展、成长计划、360 评审、影响面证据、绩效证据链、职业档案、工作成果归档、个人影响记录、review season、绩效季准备、季度总结、半年总结、年度总结、能力雷达、能力矩阵、评审可见度、评审字数限制、经理版复盘、同事版复盘、对外交付版本、绩效面谈准备、一对一议程、长期未决项检测、职业叙事、影响故事、证据溯源、成果量化

**跨仓检索与记忆服务**（52）：跨仓库记忆、agent memory、AI memory、LLM memory、语义检索、semantic search、向量检索、embedding、BM25、混合检索、可见性范围、memory scope、记忆取代、supersede、记忆置信度、记忆提升、promoted block、检索过滤、RAG 替代、vault as a service、跨仓库上下文、跨项目记忆、项目间知识复用、记忆召回、recall、remember、记录工作、语义索引、本地向量库、索引刷新、嵌入模型、索引与嵌入分离、检索排序、相关性排序、可见性策略、曝光范围、调用方身份、身份握手、协议握手、JSON-RPC、stdio 服务、服务面、工具声明、资源 URI、提示模板、派生会话、推理档位、延迟阶梯、记忆写入、记忆发现、记忆自愈、记忆索引缓存

**质量、事实纪律与门禁**（46）：事实核查、fact check、更正扫描、correction sweep、单一来源、single source of truth、防文档漂移、文档漂移、门禁、delivery gate、交付验证、审计、结构审计、回归测试、棘轮门禁、前端校验、内容校验、笔记体检、知识库体检、知识库审计、机械层与判断层、只找不改、红绿对照、负向对照、防静默失败、幂等、可复现、自检门禁、正负对照、故意损坏测试、文档同步测试、契约测试、用例驱动、测试覆盖率、守卫必须先红、生产验收分离、三分类更正、权威来源、复述改写、历史记录保留、推断标记、日期戳、状态唯一来源、计数不入指令文件、结构校验、链接校验

**迁移与升级**（34）：vault 迁移、vault 迁移工具、知识库迁移、笔记迁移、Obsidian 迁移、存量知识库迁移、版本指纹、升级路径、模板升级、知识库重构、dry-run 迁移、数据保真迁移、幂等迁移、安装向导、旧库导入、PARA 迁移、Zettelkasten 迁移、日记笔记迁移、MOC 迁移、库结构对齐、源库只读迁移、迁移计划先行、迁移日志、内容哈希、冲突处理、二进制附件迁移、链接修复、frontmatter 补齐、脚手架替换策略、用户内容保留、模板基础设施覆盖、版本检测、升级安全性、安装等价性

**发布与交付工程**（32）：CI/CD、GitHub Actions、发布流水线、release pipeline、changelog 自动生成、自动生成变更日志、版本号管理、打包发布、多平台测试、跨平台、Windows 支持、macOS 支持、Linux 支持、残留检查、发布门禁、插件校验、模板发布、可移植性、零构建步骤、版本载体同步、tag 与版本一致、从 tag 树打包、发布说明生成、工作流矩阵、定时巡检、固定版本与最新版、插件清单校验、安装侧车、个性化脚本、增量更新、加法式更新、契约不变式

**场景与意图词**（39）：给 AI 装记忆、让 AI 记住上下文、AI 忘性大、AI 记不住、跨会话记忆、会话上下文丢失、AI 编程助手记忆、代码助手长期记忆、让 AI 读我的笔记、AI 读写 Obsidian、Obsidian 自动化、Obsidian 工作流、Obsidian 智能体、笔记自动化、知识库搭建、搭建第二大脑、个人知识系统、复盘自动化、绩效材料整理、会议纪要自动归档、会议记录自动整理、周报自动生成、让笔记互相链接、笔记自动补链、笔记自动关联、知识自动关联、知识库健康检查、每次都要重新解释背景、重复解释上下文、知识不累积、决定过的事又忘了、让 AI 了解我的项目、AI 懂我的历史决策、给 AI 一个大脑、AI 记忆外挂、记忆不丢失、换电脑也能带走记忆、知识跨项目复用、让笔记活起来

**英文市场词**（46）：persistent memory for AI agents、agent memory system、ai coding agent memory、knowledge vault、second brain for developers、obsidian vault template、obsidian vault for work、cross-repo memory、note automation、pkm automation、knowledge graph notes、engineering brag doc、career evidence、performance review prep、review evidence、obsidian automation、obsidian workflow、obsidian ai agent、note taking automation、knowledge management system、ai memory layer、llm memory system、session continuity、personal knowledge management、developer knowledge base、engineering journal、work notes automation、incident postmortem notes、one on one notes template、brag document、ai agent memory、memory for coding agents、claude code memory、codex memory、gemini cli memory、mcp memory server、semantic vault search、local first knowledge base、markdown knowledge base、git backed notes、obsidian mcp、agent context persistence、knowledge compounding、engineering career tracking、self review automation、peer review writing

**同义与近义变体**（28）：知识管理智能体、笔记智能体、记忆智能体、知识库智能体、笔记系统专家、知识库专家、知识管理专家、Obsidian 专家、PKM 专家、第二大脑专家、记忆系统专家、笔记自动化专家、AI 记忆专家、上下文管理专家、智能体基础设施、AI 助手记忆方案、知识资产化、经验沉淀系统、团队知识沉淀、知识系统顾问、知识架构师、信息架构师、记忆架构师、工作流架构师、复盘方法论顾问、职业发展顾问、绩效顾问、证据分析师

**技术同义词**（29）：TypeScript 项目、MCP 服务端、本地模型、embedding 模型、图遍历、沿链扩展、曝光策略、权限范围、调用方识别、审计追踪、可观测性、测试用例、零外部测试依赖、无环依赖图、单向分层、扇入扇出、模块化设计、依赖注入、纯函数、数据驱动配置、声明式规则、事件驱动、幂等操作、原子操作、文件锁、竞态防护、预算裁剪、输出截断、状态剪枝

**具体命令与代理名**（39）：om-standup、om-wrap-up、om-dump、om-intake、om-correct、om-tidy、om-vault-audit、om-vault-upgrade、om-weekly、om-humanize、om-meeting、om-prep-1on1、om-capture-1on1、om-incident-capture、om-slack-scan、om-peer-scan、om-review-brief、om-self-review、om-review-peer、om-project-archive、brag-spotter、context-loader、correction-sweep、cross-linker、people-profiler、review-fact-checker、review-prep、slack-archaeologist、vault-librarian、vault-migrator、/om-standup、/om-wrap-up、/om-tidy、/om-correct、站会命令、收尾命令、复盘命令、审计命令、更正命令

**笔记类型与字段名**（44）：work-note、incident note、person note、team note、competency note、PR evidence、brain topic note、thinking note、domain note、event-log satellite、archive note、memory capture、index note、MOC note、工作笔记类型、事故笔记类型、决策记录类型、人物笔记类型、团队笔记类型、能力笔记类型、战功文档类型、复盘简报类型、自评类型、同事评审类型、PR 证据类型、大脑主题笔记、思考笔记、领域笔记、事件日志卫星、归档笔记、记忆捕获、索引笔记类型、笔记字段 date、笔记字段 description、笔记字段 tags、笔记字段 status、笔记字段 quarter、笔记字段 ticket、笔记字段 severity、笔记字段 role、笔记字段 person、笔记字段 cycle、笔记字段 confidence、笔记字段 scope

**专家团专属词**（30）：obsidian-mind-vault、知识库专家团、持久记忆知识库、智能体记忆系统搭建、知识库自动化运维、笔记系统体检、知识库防漂移、记忆可见性策略、跨会话上下文保持、知识库工作流设计、绩效证据链构建、会话钩子管道、vault 内容模型设计、知识图谱信息架构、交付门禁与审计、多宿主知识库、obsidian-mind 专家团、obsidian-mind 知识库专家团、AI 助手记忆方案设计、给编码助手加记忆、知识库结构审计、笔记一致性维护、评审材料自动化、知识库迁移与升级、会话生命周期设计、知识库健康度、记忆作用域设计、第二大脑工作流、知识管理系统架构、PKM 系统设计

## 头像

`avatars/` 目录下为团队与每个角色的职能徽记（512×512 PNG，非人型抽象几何隐喻，程序化绘制）。
如需替换：PNG 或 JPG、512×512、单张不超过 500KB。

## 安装

将专家包放入 WorkBuddy 的专家目录：

```
C:\Users\<用户名>\.workbuddy\plugins\marketplaces\my-experts\plugins\obsidian-mind-vault\
```

或直接导入打包好的 zip。
