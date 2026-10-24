# HRM Smart Solution Team · Knowledge Base（总索引）

> 本文件为团队知识库**总索引（master map）**，仅指向各模块私有技能内的领域知识。
> 领域知识已按模块归属拆分至 `skills/<id>/references/`，由各 specialist **私有加载**；本 commons 仅保留共享项（knowledge-map / integration-catalog / hr-toolset）。
> 路径相对各 scoped 技能根目录；如 `recruitment-pipeline` 的知识在 `skills/recruitment-pipeline/references/`。

## 共享（commons · 本目录 `skills/hrm-solution/references/`）

| 文件 | 主题 | 引用方 |
|------|------|--------|
| `knowledge-map.md` | 知识库总索引（本文件） | 全部 |
| `integration-catalog.md` | 运行时可选后端目录（数字人面试 / 无代码平台） | recruitment-pipeline / lead |
| `hr-toolset.md` | HR 通用工具集（招聘/入职/离职/制度/手册/模板 6 命令） | 全部 |

### hr-practice-library（实务工具库 · 独立技能 `skills/hr-practice-library/`）
| 资产 | 位置 | 主题 |
|---|------|------|
| 总索引 | `skills/hr-practice-library/knowledge/_practice_index.json` | 199 份 HR 制度/表单模板主索引（模块/类型/归属/引擎/流程）|
| 连接总索引 | `skills/hr-practice-library/knowledge/_solution_links.json` | 每份模板 → 归属技能/agent、主引擎/增强引擎、合规闸门 的总览 |
| 模块映射 | `skills/hr-practice-library/knowledge/_module_map.json` | 7 大模块归属 + 17 条跨模块交接单据（handoffs）|
| 表单记录 | `skills/hr-practice-library/knowledge/forms/Fxxx.json` | 单份模板字段骨架、正文摘要与 `solution_links` 连接 |
| 数据结构契约 | `skills/hr-practice-library/schema.json` | 条目文件 / 索引 / 模块映射的结构定义（已内置）|
| 检索器 | `skills/hr-practice-library/scripts/query_forms.py` | 关键词 / form_id / 模块 / 类型 / 归属技能 / 引擎 / 流程 七种检索入口 |
| 使用指南 | `skills/hr-practice-library/GUIDE.md` | 与专家团协同用法：双入口机制、7 个检索入口、三个照抄场景、handoffs 串 SOP 与合规闸门收口 |
| 原件 | `skills/hr-practice-library/templates/<MODULE_CODE>/<policy\|form>/<Fnnn>.docx` | 199 份制度与表单 .docx 原件（基准，全 ASCII 路径；<MODULE_CODE> ∈ HRP/REC/TRN/PER/COM/ER/ARC）|
| 清单 | `skills/hr-practice-library/templates/INDEX.csv` | 199 条模板清单（form_id / module_code / kind / title，便于按目录浏览与人工核对）|

> 归属：199 份模板按 7 大模块归口至 6 个 scoped 技能 / agent（HRP→org-planning，REC→recruitment-pipeline，TRN→talent-development，PER→performance-management，COM→compensation-strategy，ER/ARC→labor-compliance），经 `compliance_gate.py` 统一终检。详见其 `SKILL.md`。

## 模块私有（scoped · `skills/<id>/references/`）

### recruitment-pipeline（招聘管道）
| 文件 | 主题 |
|------|------|
| `recruiting-pipeline.md` | 招聘管道与 ATS 漏斗 |
| `interview-evaluation.md` | 五维面试评估标准 |
| `candidate-crm.md` | 候选人档案规范（电话唯一键）|
| `resume-quality.md` | 简历质量诊断 R1-R5 |
| `resume-quality-pitfalls.md` | 简历反例库 |
| `resume-guidelines.md` | 简历撰写 7 步法 + 反例 |
| `interview-framework.md` | 行为面试 STAR + 结构化题库 |
| `output-templates.md` | 简历/面试输出模板契约 |
| `workflow-details.md` | 简历/面试端到端工作流 |
| `advanced-screening-and-interview-design.md` | 漏斗式筛选 3 维度 + 4 阶段完整招聘 |
| `boss-zhipin-channel-intel.md` | BOSS直聘招聘渠道情报 |
| `job-seeker-toolkit.md` | 求职者侧工具集 |

### compensation-strategy（薪酬策略）
| 文件 | 主题 |
|------|------|
| `compensation-band.md` | 定薪决策与市场对标 |
| `compensation-pitfalls.md` | 薪酬反例库 |
| `payroll-china.md` | 中国个税 / 五险一金 / 年终奖规则 |

### org-planning（组织规划）
| 文件 | 主题 |
|------|------|
| `org-health.md` | 组织健康度基准 |
| `workforce-planning.md` | 人力规划方法论（8 步 + 3 模型 + 弹性用工 + 接班人）|

### performance-management（绩效管理）
| 文件 | 主题 |
|------|------|
| `performance.md` | 绩效体系设计（KPI/OKR/校准）|
| `okr-template-library.md` | OKR 模板库（季度复盘 / 对齐 / 评分 / 与绩效关系）|

### labor-compliance（劳动合规）
| 文件 | 主题 |
|------|------|
| `policy-generation.md` | 人事政策文档生成 |
| `compliance-baseline.md` | 中国大陆劳动合规基线（25+ 主题）|
| `compliance-pitfalls.md` | 合规反例库 |
| `clause-rewrite.md` | 高风险条款改写 |
| `dispute-handling.md` | 劳动争议处理话术 |

### talent-development（人才发展）
| 文件 | 主题 |
|------|------|
| `talent-development.md` | 人才发展（入职/梯队/职业路径）|
| `training-program-design.md` | 培训计划设计 |

### talent-sourcing（人才寻访）
| 文件 | 主题 |
|------|------|
| `sourcing-playbook.md` | 寻访方法论（六步寻访法，与 SKILL.md 工作流一一对应）|
| `pii-handling.md` | 寻访场景 PII 处理细则（个保法对齐）|
| `shortlist-template.md` | shortlist 交付模板（JSON 契约 + Markdown 报告）|

### personality-assessment（人才测评）
| 资产 | 位置 | 主题 |
|---|------|------|
| 题库/海报 | `skills/personality-assessment/assets/sbti/` | SBTI 人格测评题库与海报（`../personality-assessment/assets/sbti/data/sbti_questions.json` + `images/` 26 张 + `personality_image_map.json`）|

## 维护约定
- 领域知识基准在对应 scoped 技能内；本索引只登记位置，不复制规则。
- 新增领域知识须归入对应 scoped 技能，并在本索引登记。
- 法规/政策类知识（payroll-china / compliance-baseline / compliance-pitfalls）标注「基准版本日期」，地区差异须人工核验后更新。

## 跨脚本统一返回 schema（共享契约）
统一 schema 由 `engine_service.dispatch_envelope()`（Python 函数引用，非 CLI 命令；模块 `scripts/engine_service.py`）提供，顶层结构：
```json
{
 "status": "ok|error",
 "version": "3.3.0",
 "baseline_date": "2026-01-01",
 "payload": { },
 "errors": [{"code": "E001", "message": "...", "field": "baseSalary", "severity": "fatal"}],
 "warnings": []
}
```
错误码字典（详见 `scripts/INDEX.md`）：`E001-E019` 缺必填 / `E020-E039` 类型 / `E040-E059` 值越界 / `E060-E079` 跨字段 / `E080-E099` 内部。

> **向后兼容**：3 个引擎独立 CLI 输出结构保持不变；统一 schema 仅新增在 `engine_service` 层，旧调用方零改动。
