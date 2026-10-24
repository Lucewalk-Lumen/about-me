---
name: hrm-solution
version: 1.0.0
author: "Xing Bu"
description: |
  HRM 团队共享知识库与计算引擎（commons）。本技能仅承载跨模块共享资产：计算引擎入口、共享契约（hard rules + 输出契约，见 contracts.md）、共享知识（`references/integration-catalog.md` / `references/hr-toolset.md` / `references/knowledge-map.md`），以及团队级工具与错误处理。领域知识已拆分至各 scoped 技能（skills/<id>/），由对应 specialist 私有加载；引擎仅用 Python 标准库。
---

# HRM Solution — 共享知识库与计算引擎（commons）

本技能是 HRM 实战参谋团的**共享基座（commons）**，被 lead 与全部 specialist 加载。领域知识基准已下沉至各模块私有技能（见 `skills/<id>/SKILL.md`），本文件仅保留团队级共享内容。

## 共享知识索引（commons only）

| 文件 | 主题 | 引用方 |
|------|------|--------|
| `references/knowledge-map.md` | 知识库总索引（指向各 scoped 位置） | 全部 |
| `references/integration-catalog.md` | 运行时可选后端目录（数字人面试 / 无代码平台） | recruitment-pipeline / lead |
| `references/hr-toolset.md` | HR 通用工具集（招聘/入职/离职/制度/手册/模板 6 命令） | 全部 |

> 完整 29 篇领域知识已按模块归属拆分至 `skills/<id>/references/`，由对应 specialist 私有加载；归属表与路径见 `knowledge-map.md`。

## 计算脚本 `scripts/`（共享引擎库）

| 脚本 | 用途 | 适用 specialist |
|------|------|--------|
| `scripts/payroll_engine.py` | 个税累计预扣/五险一金/年终奖 | compensation-strategy |
| `scripts/candidate_scorer.py` | 候选人五维评分 + 录用决策 | recruitment-pipeline |
| `scripts/org_health.py` | 组织健康度诊断 | org-planning |
| `scripts/sbti_assessment.py` | SBTI 职场人格测评（32 题 → 人格 code + 海报） | personality-assessment |
| `scripts/okr_tracker.sh` | OKR 模板生成 / 评分 / 跟踪 | performance-management |
| `scripts/workforce_plan_tracker.sh` | 人力规划：generate / gap / priority / mix | org-planning |

> 完整入口契约（参数签名 / 返回结构 / 错误码字典 / 调用样例）见 [`scripts/INDEX.md`](./scripts/INDEX.md)。

## 维护约定
- 共享契约（hard rules / 输出契约）单一基准为 `contracts.md`，禁止在别处复制或弱化。
- 领域规则只在对应 scoped 技能内定义 / 修改；修改须同步该 specialist 的私有 KB 与 playbook。
- 法规 / 政策类知识标注「基准版本日期」，使用前核对官方最新数据。
- 知识文件未引用即僵尸文件；新增领域知识须归入对应 scoped 技能并在 `knowledge-map.md` 登记。

## 严格禁止（全团 hard rules · 摘要）
> 完整条款与强制要求见 **`contracts.md`**（单一基准），冲突以 `contracts.md` 为准：
1. 禁止编造法规条文编号 / 官方 URL / 生效日期（无出处须标「需人工核实」）。
2. 禁止主理人代写成员专业产出（PRD/架构/代码/测试须由对应 Agent 输出）。
3. 禁止跳过合规闸门终检（`compliance_gate.py --text`）放行（P0 风险主理人不得自行放行）。
4. 禁止单一 Agent 自填 `compliance: PASSED` 绕过闸门。
5. 禁止在未被授予的 phase 内修改 `envelope.compliance` 字段。

## 工具与命令总览

| 工具 | 用途 | 适用对象 |
|---|---|---|
| `Read` | 读取共享知识库与 references/ | 全部成员 |
| `Bash` + `python3 scripts/payroll_engine.py --payroll '<JSON>'` | 个税 / 五险一金 / 年终奖计算 | compensation-strategy |
| `Bash` + `python3 scripts/candidate_scorer.py` | 候选人五维评分 + 录用决策 | recruitment-pipeline |
| `Bash` + `python3 scripts/org_health.py` | 组织健康度诊断 | org-planning |
| `Bash` + `python3 scripts/security/compliance_gate.py --text '<TEXT>'` | 合规闸门 P0-P3 分级（输出 JSON `{gate,risk_level,dri,reasons}`；退出码 `0`=PASSED/FLAGGED、`3`=BLOCKED） | labor-compliance（终检）/ 主理人（强制调用） |
| `Bash` + `python3 scripts/security/envelope.py key-source\|verify <envelope.json> [--max-age SEC]\|selftest` | 跨 Agent 信封 HMAC 签名 / 验签（`verify` 退出码 `0`=通过、`4`=失败） | 主理人 + 全部成员 |
| `Edit` / `Write` | 修改知识库或脚本 | 成员**禁止**修改（仅包作者在发布流程中修改；修改须同步更新引用方） |
| `SendMessage` | 跨 Agent 消息传递（必须经主理人中转，禁直连） | 全部成员 |
| `present_files` | 把产出（报告 / zip / 模板）呈现给用户 | 主理人（终交付节点） |

## 意图路由（单一基准 = routing.yaml）

> 路由表已外部化为 **`routing.yaml`**（包根目录），是意图分发的唯一基准。lead 编排时**必须** `Read routing.yaml` 按 `keywords` 匹配；本文件与 `agents/hrm-advisory-corps-lead.md` 均**不复述**裁决细节，冲突一律以 `routing.yaml` 为准。
> 匹配语义以 **`routing.yaml` 头部「匹配规则」章节为单一基准**，逐字执行。

## 错误处理

| 错误类型 | 处理方式 | 责任人 |
|---|---|---|
| 用户信息不足 | 不静默回退默认值；必填字段缺失直接抛 `InputValidationError` | 引擎层 |
| 法规出处缺失 | 标注「需人工核实」+ `verification: manual_review_required` | labor-compliance |
| `final_gate` 命中 P0 | 立即拦截，转人工 DRI；主理人不得自行放行 | 闸门 + 主理人 |
| `final_gate` 命中 P1/P2 | 提示用户并建议人工复核后交付 | 闸门 + 主理人 |
| 信封 HMAC 验签失败 | `envelope.py verify` 退出码 `4` → 视为伪造/篡改，丢弃并重新索取；禁止以自由文本直接传递专业产出。跨进程验签默认可用（密钥持久化于用户数据目录，`HRM_ENVELOPE_KEY` 优先） | 主理人 |
| 路由命中 `confirm_backend: true`（`digital_interview` / `digital_build`） | **必须先询问后端平台**，禁止跳过 | 主理人 |
| 知识文件未引用 | 在 `knowledge-map.md` 索引中显式列出，禁僵尸文件 | 包作者（发布流程） |
| 计算引擎跨字段约束违反 | 抛 `E060-E079` 错误码（详见 `scripts/INDEX.md`） | 引擎层 |

## 详细参考

| 主题 | 路径 |
|---|---|
| 团队级共享契约（hard rules + 输出契约） | `contracts.md` |
| 意图路由（单一基准） | `routing.yaml` |
| 知识库总索引（指向各 scoped 位置） | `references/knowledge-map.md` |
| 计算脚本入口契约 | `scripts/INDEX.md` |
| 安全子包（信封 / 闸门 / 审计 / PII） | `scripts/security/` |
| 各模块私有知识 / playbook | `skills/<id>/SKILL.md`（id ∈ org-planning, recruitment-pipeline, talent-development, performance-management, compensation-strategy, labor-compliance, personality-assessment, talent-sourcing） |

## 交付物产出（调用 WorkBuddy 文档技能 · 零环境安装）

本包**不捆绑、不要求**任何办公软件（MS Office / WPS）或本地运行环境；最终交付物由 WorkBuddy 在会话内直接生成，终端用户无需安装或配置任何环境。

- **默认产出**：Markdown / 文本 / JSON，可直接阅读、复制与归档。
- **正式文档需求**：当用户要求或场景需要 Word / PPT / Excel 等正式格式时，**直接调用 WorkBuddy 内置文档技能**在会话内生成（文档技能为 WorkBuddy 原生能力，运行时不依赖本机 Office）：
  - Word 文档（.docx）→ `tencent-docx` 技能（生成 / 排版美化）
  - 演示文稿（.pptx）→ `tencent-pptx` 技能
  - 表格 / 数据表（.xlsx）→ `tencent-docs-sheet-generation` 技能
  - 编辑本地已有 Office 文件 → `tencent-local-office-edit` 技能
- **调用位置**：主理人在终交付节点（Step 6，且 Step 5 合规闸门为 PASSED/FLAGGED 之后）将已通过合规校验的文本内容交给对应文档技能；文档技能产出经 `present_files` 呈现。
