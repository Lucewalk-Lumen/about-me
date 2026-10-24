# HRM 实战参谋团 · 职责矩阵 RACI

> 本文件是团队**职责划分的成文基准**，用于减少重复劳动与冲突；歧义时由主理人按
> `routing.yaml` 单一基准裁决。R=负责执行 / A=最终 accountable / C=被咨询 / I=被告知。
> 与 `quality/team-quality-plan.md` §3 同源，冲突以本文件为准。

## 1. 招聘生命周期（上游 vs 下游）

| 活动 | talent-sourcing（上游） | recruitment-pipeline（下游） | 边界裁决 |
|------|------------------------|------------------------------|---------|
| 主动寻访 / 人才库匹配 | **R/A** | I | 来源状态：sourcing 处理"主动寻访 + 人才库存量" |
| 候选人主动投递 / ATS / 简历初筛 | I | **R/A** | pipeline 处理"主动投递入口"（`talent-sourcing.md` 不处理主动投递） |
| 寻访侧初评（三维）+ shortlist | **R/A** | C（接收交接） | shortlist 经主理人中转交 pipeline（`routing.yaml` sourcing_to_pipeline 跨模块） |
| 面试评估 / 录用决策 | I | **R/A** | sourcing 不做面试评估与录用 |
| 触达话术合规审查 | C | I | 由 labor-compliance 终检 |

## 2. 人才画像 vs 人格测评（易混点，重点澄清）

| 维度 | talent-sourcing · 行业人才画像库（P 前缀） | personality-assessment · SBTI 人格画像 |
|------|----------------------------------------|----------------------------------------|
| 对象 | **群体/市场/岗位**（统计特征，**不含个人 PII**） | **个体**（职场人格类型码） |
| 用途 | 寻访定向（对标公司梯队、人才地图） | 人才评估 / 发展 / 测评报告 |
| 路由词 | `人才画像库` / `寻访画像`（`routing.yaml` talent_sourcing） | `人格画像` / `SBTI`（`routing.yaml` personality_assessment） |
| 交互 | SBTI 结果仅预留接口，**不进匹配**；无授权不消费 | 禁止跨模块（独立处理） |
| **冲突裁决** | 用户说"人才画像"→ sourcing；说"人格/性格画像"→ personality。**两者不交叉产出** | |

## 3. 薪酬 / 合规 / 测评的权威归属

- **薪酬数字**：仅 `compensation-strategy` 权威；talent-sourcing 与 recruitment-pipeline 均"不承诺薪酬范围、不写具体数字"。
- **合规结论**：仅 `labor-compliance` 终检权威；任何成员不得自填 `compliance: PASSED`（`contracts.md` hard rule 4）。
- **测评**：`personality-assessment` 独立处理、不跨模块。
- **五维评分**：由 `recruitment-pipeline` 在管道内重跑为正式评估分；sourcing 仅对 A 级/关键岗位预筛复用。
- **两评分体系防混用**：寻访适配三维（30/35/35）只用于寻访排序，五维评分（25/20/20/20/15）用于正式评估，并列呈现、互不替代（`talent-sourcing/SKILL.md` 寻访适配三维章节）。

## 4. 跨模块编排职责（routing.yaml cross_module）

| 跨模块 id | 触发 | 序列 | 终检 |
|----------|------|------|------|
| comp_perf_linkage | compensation + performance | compensation-strategy → performance-management | labor-compliance |
| recruit_onboard | recruitment + talent_dev | recruitment-pipeline → talent-development | labor-compliance |
| org_health_brief | org_planning + ops_brief | org-planning | labor-compliance |
| sourcing_to_pipeline | talent_sourcing + recruitment | talent-sourcing → recruitment-pipeline | labor-compliance |

> 所有跨模块产出均经主理人中转，禁止成员直连（`hrm-advisory-corps-lead.md` 协作规则第 3 条）。

## 5. 求职侧 vs 组织侧「职业」类请求（易混点）

| 关键词 | 归属 | 裁决 |
|--------|------|------|
| 职业规划 / 跳槽 / 找工作 / 简历 / 面试（个人视角） | recruitment-pipeline（`routing.yaml` job_seeker） | 个人求职侧诉求，含个人职业规划建议 |
| 职业发展 / 梯队 / 继任 / 晋升通道（组织视角） | talent-development（`routing.yaml` talent_dev） | 组织侧人才发展体系建设 |

> 两者同为单模块路由命中时，按 `routing.yaml` 三层裁决的 tiebreak（最长关键词 → priority → 文件顺序）执行；语义含糊时由主理人请求用户澄清（lead 护栏：不确定意图先澄清，不猜测）。
