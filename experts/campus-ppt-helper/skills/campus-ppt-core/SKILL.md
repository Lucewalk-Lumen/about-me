---
name: campus-ppt-core
description: "Core shared protocol for the Campus PPT Helper Team. Consult it for PPT triage, light/heavy mode split, outline-confirm gate, skill-routing gate, interaction discipline, task-state resume and school adaptation across teaching / thesis-defense / internship / Party-building (教学/答辩/实习/党建党政) scenarios. Triggers on: PPT, 演示文稿, 分诊, 轻模式, 重模式, 大纲确认, Skill路由, 交互协议, 口径基线, 任务状态, 断点续传, CAMPUS_PPT_STATE, run_metrics, 场景矩阵, 学校适配, 广财, 模板获取, 党政模板, 教学, 答辩, 实习, 党建, 党政."
---

# 校园演示帮手团 · 核心协议层（Campus PPT Core）

本 Skill 是「校园演示帮手团」的**全员共享核心**——无论哪个角色，先按这里的交互协议、模式分流、确认门与学校适配基线对齐口径，再进入各自的专业环节。目标只有一个：**先对齐需求口径，再动手**，避免方向性返工。

## 使用原则

| 原则 | 说明 |
|------|------|
| **先分流，再派单** | 派单前必判轻/重模式（Tripwire 触发信号），轻模式不空转外部采集、不免大纲确认 |
| **口径先于产出** | 需求、受众、平台、模板、页数没对齐前不动手；拿不准就问，不臆造 |
| **大纲确认门（强制）** | 页面清单交付后、制作前必须经用户**显式确认**；"嗯/好"等模糊应答不算确认；轻模式可降级为回读确认 |
| **Skill 路由门（强制）** | 生成路径 B（tencent-local-office-edit 模板保真，**默认**）/ A（tencent-pptx 风格重绘，兜底）/ 用户自带 skill 三态判定；**广财师生 / 党政单位默认套用内置品牌模板；不确定就停下问，禁止默默走默认** |
| **学校适配三分支** | 广财内置 / 自带本校模板 / 中性通用兜底，兜底须明示「未含本校品牌视觉」；不虚构任何学校品牌视觉 |
| **崩了能续** | `CAMPUS_PPT_STATE.md` 外化任务状态，重连后从首个非 done 阶段继续，记忆与文件冲突以文件为准 |

## 参考索引（先读后用，禁止凭记忆编造）

| 文件 | 何时查阅 |
|------|----------|
| `references/interaction-protocol.md` | **交互协议与需求口径基线**：交互止损三原则、`01-brief.md` 基线字段、口径变更协议；**§五 确认门（大纲确认门 + Skill 路由门）** |
| `references/task-state-resume.md` | **任务状态与断点续传**：`CAMPUS_PPT_STATE.md` 状态清单、幂等重入协议、阶段跳过判据；**§二.五 可观测记录 run_metrics**（模式/调度/耗时计数） |
| `references/scenario-templates.md` | 选模板与场景矩阵：教学 / 答辩 / 实习 / 党建党政 四场景 → 模板 / 叙事框架 / 语气 / 密度 速查 |
| `references/school-adaptation.md` | **学校适配与模板获取**：广财内置 / 自带本校模板 / 中性通用兜底 / 党政通用四类路径的决策树、交付声明要求与可直接使用的提示话术 |

## 与其它 Skill 的衔接

本核心层只负责"对齐口径与调度基线"；具体执行交给对应专业包：
- 采集 → `campus-ppt-collect`；配图 / 案例 / 图表 → `campus-ppt-media`
- 结构与版式规划 → `campus-ppt-design`；官方技能制作与依赖预检 → `campus-ppt-make`
- 四维质检 → `campus-ppt-qa`
