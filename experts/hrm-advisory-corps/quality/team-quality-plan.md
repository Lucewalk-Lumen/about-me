# HRM 实战参谋团 · 团队质量基准

> 本文件是团队协作层的**质量基准**：定义可衡量质量指标（QM-01 ~ QM-13）、职责矩阵（RACI）与状态同步 / 错误恢复机制的设计依据。被主理人加载为协作层硬约束；指标契约见 `skills/hrm-solution/contracts.md`，冲突以 contracts.md 为准。
> 职责矩阵的成文基准为 `quality/RACI.md`（与本文件 §3 同源，冲突以 RACI.md 为准）。

---

## 1. 质量设计基线（缺口 → 对策）

| # | 设计基线（缺口） | 现状依据（文件:行） | 已落地对策 |
|---|------|----------------|------|
| B1 | 团队级可衡量指标缺失（仅 talent-sourcing 有单专家指标） | `talent-sourcing/SKILL.md:61-69` | §2 QM-01 ~ QM-13 指标框架 + `quality_gate.py` / `task_ledger.py` 机器采集 |
| B2 | 职责矩阵未成文（人才画像 vs 人格画像仅靠路由词隐式区分） | `routing.yaml:65` vs `:69` | `quality/RACI.md` 成文（§3 同源） |
| B3 | 跨阶段无持久化状态（主理人重启丢失在途任务） | `envelope.py:372` 仅 `trace_id/phase` | `task_ledger.py` 任务账本（状态持久化 + 断点续跑） |
| B4 | 错误恢复依赖人工两次追问 | `hrm-advisory-corps-lead.md:115-117` | `task_ledger.py` 重试预算 / 熔断 / 死信 + `retry` 自动重发 |
| B5 | 输出契约无自动校验（肉眼核对） | `hrm-advisory-corps-lead.md:99-109` | `quality_gate.py check`（回传契约 / 合规出处 / PII / 合规闸） |
| B6 | 量化可追溯无机器留痕 | `engine_service.py:29-31` 能力已具备未被强制 | `engine_service.dispatch_envelope`（version / baseline_date）+ `Step 6a.3` 强制 |
| B7 | 两评分体系可能混用（三维 30/35/35 vs 五维 25/20/20/20/15） | `talent-sourcing/SKILL.md:40-48`、`candidate_scorer.py:25` | RACI 成文边界（三维仅寻访排序、五维仅正式评估，并列不互替） |

---

## 2. 团队级可衡量质量指标框架（QM-01 ~ QM-13）

> 设计原则：每个指标都有**定义、公式、目标值、采集方式、责任方**；能机器采集的优先机器采集
> （复用 `quality_gate.py` / `task_ledger.py` / `envelope.py` / `compliance_gate.py`）。

| 编号 | 指标 | 口径 / 公式 | 目标值 | 采集方式 | 责任方 |
|------|------|------------|--------|---------|--------|
| **QM-01** | 信封验签通过率 | `verify OK 数 / 入站信封总数` | **100%** | `envelope.py verify`（退出 0/4）；`quality_gate.envelope_signature_valid` | 主理人（Step3） |
| **QM-02** | 合规闸门零逃逸 | `P0 被自动放行次数`（即 BLOCKED 仍进 deliver）= **0** | **0** | `compliance_gate.py` 退出码 3 + `contracts.md:18,20` | labor-compliance + 主理人 |
| **QM-03** | 回传契约完整率 | `含五字段的回传 / 总回传` | **100%** | `quality_gate.return_contract_complete` | 主理人（Step3/6a） |
| **QM-04** | 合规出处标注率 | `带 legal_basis+baseline_date+verification 的合规结论 / 全部合规结论` | **100%** | `quality_gate.compliance_citation_complete` + `Step 6a.1` | 主理人（Step6a） |
| **QM-05** | PII 脱敏覆盖率 | `无明文 PII 的含 PII 产出 / 全部含 PII 产出` | **100%** | `pii.contains_pii` + `quality_gate.pii_masked` | talent-sourcing / pipeline |
| **QM-06** | 路由命中准确率 | `路由正确的请求 / 总路由请求` | **≥95%** | `routing.yaml` + 人工抽检（按意图抽样） | 主理人（Step1） |
| **QM-07** | 跨成员中转率 | `经主理人中转的跨成员流 / 总跨成员流` | **100%**（架构约束） | 架构约束（`lead.md:88,95`）+ ledger | 主理人 |
| **QM-08** | 任务按时交付率 / 超时代写率 | `超时代写任务 / 总任务`（目标 ≤5%）；按时交付率 ≥95% | 代写 ≤5% | `task_ledger.summary`（delivery_rate_pct / agent_error_counts） | 主理人 |
| **QM-09** | 错误恢复成功率 | `自动恢复（进入后续阶段）的失败任务 / 可恢复错误任务` | **≥90%** | `task_ledger.summary`（error_recovery_rate_pct / dead_letter） | 主理人 + ledger |
| **QM-10** | 量化可追溯率 | `带 输入快照+来源脚本+版本号 的引擎数字 / 全部引擎数字` | **100%** | `engine_service.dispatch_envelope`（version/baseline_date）+ `Step 6a.3` | 主理人（Step6a） |
| **QM-11** | 寻访专项 | shortlist 命中率≥60%；复用率≥40%；字段完整度100%；合规零违规=0 | 见本表定义 | `talent-sourcing` 运行统计 + `quality_gate --spec talent-sourcing` | talent-sourcing |

**可靠性 / 安全附加指标**
- **QM-12 信封密钥保护率**：`key-protect` 退出 0（POSIX 0600 / Windows ACL 加固）= 100%；来源 `envelope.py key-protect`。
- **QM-13 引擎错误率**：`dispatch_envelope status=error` 比例（越低越好，目标 <5%）；来源 `engine_service.py:280`。

**采集机制**：`quality_gate.py` 每次成员回传产出一份机器可读质量报告（各指标 pass/fail + 综合分 + 退出码），`task_ledger.py summary` 产出协作层聚合指标；两者共同构成团队质量月报的数据底座（见 §4 看板）。

---

## 3. 职责矩阵 RACI（减少重复劳动与冲突）

> R=负责执行 / A=最终 accountable / C=被咨询 / I=被告知。本表把"隐性边界"显式化，歧义时由主理人按 `routing.yaml` 单一基准裁决。

### 3.1 招聘生命周期（上游 vs 下游）

| 活动 | talent-sourcing（上游） | recruitment-pipeline（下游） | 边界裁决 |
|------|------------------------|------------------------------|---------|
| 主动寻访 / 人才库匹配 | **R/A** | I | 来源状态：sourcing 处理"主动寻访 + 人才库存量" |
| 候选人主动投递 / ATS / 简历初筛 | I | **R/A** | pipeline 处理"主动投递入口"（`talent-sourcing.md:21` 不处理主动投递） |
| 寻访侧初评（三维）+ shortlist | **R/A** | C（接收交接） | shortlist 经主理人中转交 pipeline（`routing.yaml:124-127` sourcing_to_pipeline） |
| 面试评估 / 录用决策 | I | **R/A** | sourcing 不做面试评估与录用（`SKILL.md:95`） |
| 触达话术合规审查 | C | I | 由 labor-compliance 终检（`SKILL.md:18,94`） |

### 3.2 人才画像 vs 人格测评（易混点，重点澄清）

| 维度 | talent-sourcing · 行业人才画像库（P 前缀） | personality-assessment · SBTI 人格画像 |
|------|----------------------------------------|----------------------------------------|
| 对象 | **群体/市场/岗位**（统计特征，**不含个人 PII**） | **个体**（职场人格类型码） |
| 用途 | 寻访定向（对标公司梯队、人才地图） | 人才评估 / 发展 / 测评报告 |
| 路由词 | `人才画像库`/`寻访画像`（`routing.yaml:65`） | `人格画像`/`SBTI`（`routing.yaml:69`） |
| 交互 | SBTI 结果仅预留接口，**不进匹配**（`SKILL.md:50`）；无授权不消费 | 禁止跨模块（`personality-assessment.md:20`） |
| **冲突裁决** | 用户说"人才画像"→ sourcing；说"人格/性格画像"→ personality。**两者不交叉产出** | |

### 3.3 薪酬 / 合规 / 测评的权威归属

- **薪酬数字**：仅 `compensation-strategy` 权威；talent-sourcing 与 recruitment-pipeline 均"不承诺薪酬范围、不写具体数字"（`SKILL.md:93`）。
- **合规结论**：仅 `labor-compliance` 终检权威；任何成员不得自填 `compliance: PASSED`（`contracts.md:20`）。
- **测评**：`personality-assessment` 独立处理、不跨模块（`personality-assessment.md:20`）。
- **五维评分**：由 `recruitment-pipeline` 在管道内重跑为正式评估分；sourcing 仅对 A 级/关键岗位预筛复用（`SKILL.md:87`）。

---

## 4. 状态同步与错误恢复机制

### 4.1 设计动因

- 状态随信封传递（`trace_id/phase`），但**无跨阶段持久化状态**；主理人中断即在途任务丢失（B3）。
- 错误恢复为人工两次追问（`lead.md:115-117`），无重试预算/熔断/死信（B4）。

### 4.2 机制（已落地）

**`task_ledger.py`**——基于 JSON 文件的轻量任务生命周期账本：
- 状态机：`spawned → dispatched → returned → verified → gated → delivered`（失败/验签失败/熔断 → `dead_letter`）。
- **状态同步**：账本落用户数据目录（或 `--store` 指定），主理人重启可 `status <id>` 查询恢复 → 支持断点续跑（补 B3）。
- **错误恢复**：
  - 重试预算：每任务允许 `max_retries` 次重试（`fail` 自动判定 retryable，超限进死信）；
  - 熔断：某 agent 连续失败达 `circuit_threshold` → 临时停用（`can_dispatch` 返回 False），主理人改派替代 specialist 或转人工 DRI；
  - 死信队列：超限任务集中留痕，转人工 DRI（补 B4）。
- 采集：`.summary()` 输出 `delivery_rate_pct / error_recovery_rate_pct / dead_letter / open_circuits / agent_error_counts` → 直接喂 QM-08/09。

**`quality_gate.py`**——输出契约校验器（补 B5/B6）：
- 校验信封签名（QM-01）、五字段回传契约（QM-03）、合规出处标注（QM-04）、PII 脱敏（QM-05）、spec 字段完整度（QM-11）；
- 输出机器可读质量报告 JSON + 综合分 + 退出码（0 通过 / 1 未过）→ 把"肉眼核对"升级为"机器采集"（补 B5）。

### 4.3 主理人 SOP 接入（已生效）

| SOP 步骤 | 接入点 |
|---------|--------|
| Step 2 调度 | 先 `ledger.spawn` + `can_dispatch`（熔断检查）；再 `ledger.dispatch` |
| Step 3 中转 | 验签后 `ledger.record_return` + `quality_gate.check`；未过则 `ledger.fail`（重试预算） |
| Step 5 终检 | `ledger.record_gate`（BLOCKED → 转人工，不进 deliver） |
| Step 6 交付 | `ledger.record_deliver`；交付摘要附 `quality_gate` 质量分与 `ledger.summary` 指标 |

---

## 5. 能力清单

**已落地**：
- `skills/hrm-solution/scripts/quality_gate.py` —— 输出契约校验器（QM-01/03/04/05/11 采集）；经合规 / 缺陷样例双向验证（合格样例 PASS、缺陷样例精准 FAIL）
- `skills/hrm-solution/scripts/task_ledger.py` —— 任务生命周期账本 + 重试 / 熔断 / 死信（QM-08/09）；全生命周期冒烟通过（spawn→deliver 与 fail→熔断→死信）
- `quality/team-quality-plan.md`（本基准）与 `quality/RACI.md`
- 主理人 SOP 接入（`hrm-advisory-corps-lead.md` Step 2/3/5/6）与 `contracts.md` 质量指标契约章节

---

## 6. 边界说明

- `task_ledger.py` / `quality_gate.py` 为**机制层工具**，需主理人在 SOP 中显式调用方能全自动生效；在 SOP 接入之外，它们亦支持手动 / 按需调用做质量采样与审计。
- 所有指标目标值为**初始基线**，运行 4–12 周后按实际数据校准。
