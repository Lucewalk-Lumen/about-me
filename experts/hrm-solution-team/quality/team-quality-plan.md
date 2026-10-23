# HRM 智能方案团 · 团队质量改进方案（v1.1.x）

> 本文是 `hrm-solution-team` 在 v1.1.0（已交付，含 `talent-sourcing` 寻访智能体）基础上，
> 对「智能体团队协作与职责划分 / 输出准确性·一致性·可靠性 / 任务分配·状态同步·错误恢复 /
> 可衡量质量指标」四方面的系统性质量改进方案。
>
> 所有结论均基于**实读包内文件**得出，关键判断附 `文件:行号` 证据；新增工具均已运行验证。
> 本轮改动均在**共享基座与文档层**（新增质量工具 + 在主理人 SOP / 共享契约中接入），未改动任何成员的领域逻辑、路由行为与对外数据契约，故不破坏已交付 v1.1.0 的对外行为；zip 重打包待用户确认（"先不打包"）。

---

## 0. 背景与本次改动范围

- **主任务状态**：`talent-sourcing`（邝寻才）已实现并并入，包版本 `v1.1.0`（zip 已交付至工作区发布目录）。
- **本次目标**：在不中断主任务前提下，系统性提升**团队整体质量**。重点四项：
  1. 优化智能体间协作与职责划分，减少重复劳动与冲突；
  2. 提升团队输出的准确性、一致性和可靠性；
  3. 完善任务分配、状态同步与错误恢复机制；
  4. 设定可衡量质量的指标。
- **落地方式**：本轮**新增**两个工具脚本 + 本方案文档（见 §5 P0 清单）。配套的 SOP 接入（P1）与 RACI 固化（P2）列为下一轮，需小幅改 `hrm-solution-team-lead.md` 与 `contracts.md`，待确认后执行、再重打包为 `v1.1.1`。

---

## 1. 质量审计（现状强项 / 缺口）

### 1.1 已具备的强项（实证）

| # | 强项 | 证据（文件:行） | 价值 |
|---|------|----------------|------|
| S1 | 主理人纯编排、职责清晰 | `hrm-solution-team-lead.md:13`（"你是纯编排者，不是任何 HR 领域的专家"）；`:20-30` 成员职责表 | 杜绝主理人越权代写，领域结论 100% 来自成员 |
| S2 | 路由单一基准、确定性三层裁决 | `routing.yaml:12-24`（归一化+子串+三层）；`:61-65` talent_sourcing；`:124-127` sourcing_to_pipeline 跨模块 | 路由可复现、可审计，无"凭感觉分流" |
| S3 | 统一五字段回传契约 | `hrm-solution-team-lead.md:111-118`；各成员 `回传契约` 小节同构 | 跨成员信息结构一致，可机器校验 |
| S4 | 信封 HMAC 鉴权 + 验签 | `security/envelope.py:367`（sign）/`:416` verify（退出码 0/4）/`:432` max-age 防重放 | 防伪造/篡改/重放；跨进程密钥持久化（`:207`） |
| S5 | 合规闸门三级分类 + 终检硬拦截 | `security/compliance_gate.py:299`（enforce_final_gate）/`:309` finalize（BLOCKED 抛 `ComplianceBlocked`） | P0 风险结构上不可被绕过，必转人工 DRI |
| S6 | 结构化错误 + 统一引擎 schema | `scripts/errors.py`（StructuredError 含 code/field/severity）；`engine_service.py:280`（dispatch_envelope 永不抛异常，进 `errors[]`） | 错误可确定性归类、可采集，不泄漏内部栈 |
| S7 | 共享契约（法条出处 + 基准日期） | `contracts.md:14-21`（hard rules）/`:26-64`（输出契约 + 格式） | 合规结论强制可核验，禁止编造 |
| S8 | PII 脱敏 + 同意硬校验 | `security/pii.py:25-59`（mask_* / contains_pii）；`talent_pool.py` consent=false→E060 拒 | 隐私合规前置到接入层 |
| S9 | 寻访侧已有单专家可量化验收标准 | `talent-sourcing/SKILL.md:61-69`（shortlist 命中率≥60% / 复用率≥40% / 字段完整度100% / 合规零违规） | 单专家指标先行，但**未上升为团队级** |

### 1.2 待改进缺口（对应四项请求）

| # | 缺口 | 证据 / 现状 | 对应请求 |
|---|------|------------|---------|
| G1 | **团队级可衡量指标缺失** | 仅 `talent-sourcing` 有单专家指标（S9）；其余成员与协作层无指标、无采集机制 | 请求④ |
| G2 | **职责矩阵未成文** | 寻访 `人才画像库` 与测评 `SBTI 人格画像` 边界仅靠路由词隐式区分（`routing.yaml:65` 人才画像库 vs `:69` 人格画像）；无一份 RACI 说明"歧义时谁裁决" | 请求① |
| G3 | **跨阶段无持久化状态** | 信封仅携带 `trace_id/phase/from/to/nonce`（`envelope.py:372`），无跨阶段共享状态/blackboard；主理人重启即丢失在途任务 | 请求③ |
| G4 | **错误恢复靠人工两次追问** | `hrm-solution-team-lead.md:115-117`（超时先问进度→二次无回传才可代写）；无重试预算/熔断/死信 | 请求③ |
| G5 | **输出契约无自动校验** | `contracts.md` 与回传契约靠 prompt 约束，主理人肉眼核对（`:99-109` 可观测性三列表），无机器校验 | 请求② |
| G6 | **量化可追溯无机器留痕** | `Step 6a.3` 要求附输入快照+来源脚本，但汇编稿无结构化版本/基线号钩子（`engine_service.py:29` SCHEMA_VERSION / `:31` baseline_date 已具备，未被强制记录） | 请求② |
| G7 | **两评分体系可能混用** | 寻访三维（30/35/35，`SKILL.md:40-48`）与五维评分（25/20/20/20/15，`candidate_scorer.py:25`）权重不同，仅 prompt 声明"不混用" | 请求② |

---

## 2. 团队级可衡量质量指标框架（QM-01 ~ QM-11）

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
| **QM-11** | 寻访专项（沿用蓝图 §3.3） | shortlist 命中率≥60%；复用率≥40%；字段完整度100%；合规零违规=0 | 见蓝图 | `talent-sourcing` 运行统计 + `quality_gate --spec talent-sourcing` | talent-sourcing |

**可靠性 / 安全附加指标**
- **QM-12 信封密钥保护率**：`key-protect` 退出 0（POSIX 0600 / Windows ACL 加固）= 100%；来源 `envelope.py key-protect`。
- **QM-13 引擎错误率**：`dispatch_envelope status=error` 比例（越低越好，目标 <5%）；来源 `engine_service.py:280`。

**采集机制**：`quality_gate.py` 每次成员回传产出一份机器可读质量报告（各指标 pass/fail + 综合分 + 退出码），`task_ledger.py summary` 产出协作层聚合指标；两者共同构成团队质量月报的数据底座（见 §4 P2 看板）。

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

## 4. 状态同步与错误恢复增强设计（对应请求③）

### 4.1 现状

- 状态随信封传递（`trace_id/phase`），但**无跨阶段持久化状态**；主理人中断即在途任务丢失（G3）。
- 错误恢复为人工两次追问（`lead.md:115-117`），无重试预算/熔断/死信（G4）。

### 4.2 新增机制（已落地，见 §5 P0）

**`task_ledger.py`**——基于 JSON 文件的轻量任务生命周期账本：
- 状态机：`spawned → dispatched → returned → verified → gated → delivered`（失败/验签失败/熔断 → `dead_letter`）。
- **状态同步**：账本落用户数据目录（或 `--store` 指定），主理人重启可 `status <id>` 查询恢复 → 支持断点续跑（补 G3）。
- **错误恢复**：
  - 重试预算：每任务允许 `max_retries` 次重试（`fail` 自动判定 retryable，超限进死信）；
  - 熔断：某 agent 连续失败达 `circuit_threshold` → 临时停用（`can_dispatch` 返回 False），主理人改派替代 specialist 或转人工 DRI；
  - 死信队列：超限任务集中留痕，转人工 DRI（补 G4）。
- 采集：`.summary()` 输出 `delivery_rate_pct / error_recovery_rate_pct / dead_letter / open_circuits / agent_error_counts` → 直接喂 QM-08/09。

**`quality_gate.py`**——输出契约校验器（补 G5/G6）：
- 校验信封签名（QM-01）、五字段回传契约（QM-03）、合规出处标注（QM-04）、PII 脱敏（QM-05）、spec 字段完整度（QM-11）；
- 输出机器可读质量报告 JSON + 综合分 + 退出码（0 通过 / 1 未过）→ 把"肉眼核对"升级为"机器采集"（补 G5）。

### 4.3 主理人 SOP 接入建议（P1，待确认后改 `hrm-solution-team-lead.md`）

| SOP 步骤 | 现状 | 增强（接 ledger / quality_gate） |
|---------|------|-------------------------------|
| Step 2 调度 | `SendMessage` 下发 | 先 `ledger.spawn` + `can_dispatch`（熔断检查）；再 `ledger.dispatch` |
| Step 3 中转 | 验签 + 肉眼核对三列表 | 验签后 `ledger.record_return` + `quality_gate.check`；未过则 `ledger.fail`（重试预算） |
| Step 5 终检 | `compliance_gate` 退出码 | `ledger.record_gate`（BLOCKED→转人工，不进 deliver） |
| Step 6 交付 | `present_files` | `ledger.record_deliver`；交付摘要附 `quality_gate` 质量分与 `ledger.summary` 指标 |

---

## 5. v1.1.x 改造清单与优先级

### P0 · 本轮已落地（新增，不破坏 v1.1.0；待打包为 v1.1.1）
- [x] `skills/hrm-solution/scripts/quality_gate.py` —— 输出契约校验器（QM-01/03/04/05/11 采集）
- [x] `skills/hrm-solution/scripts/task_ledger.py` —— 任务生命周期账本 + 重试/熔断/死信（QM-08/09 + 状态同步 + 错误恢复）
- [x] `quality/team-quality-plan.md` —— 本方案（审计 + 指标框架 + RACI + 路线图）
- [x] 两脚本已运行验证：合规样例 `PASS`、缺陷样例精准 `FAIL`；账本跑通 spawn→deliver 与 fail→熔断→死信

### P1 · 本轮已落地（SOP 与契约接入；未重打包）
- [x] 在 `hrm-solution-team-lead.md` Step 2/3/5/6 显式接入 `ledger` 调用（G3/G4 机制化）
- [x] 在 `hrm-solution-team-lead.md` Step 3/6a 把 `quality_gate.check` 列为强制前置（G5）
- [x] 在 `contracts.md` 增「质量指标契约」章节，引用本方案 §2（把指标变成团队硬约束）
- [ ] 重打包为 `v1.1.1`（zip）并交付 —— **待用户确认**（用户明确"先不打包"）

### P2 · 后续增强（部分已落地）
- [x] 把本 RACI（§3）固化为 `quality/RACI.md`，由主理人加载（G2 成文）
- [ ] 为每个 specialist 定义 `--spec` 字段完整度规则（当前仅 `talent-sourcing`）
- [ ] 信封验签失败自动重发（在 lead 中接 `ledger` 重试，闭环 G4）
- [ ] 指标看板：定期 `ledger.summary` + `quality_gate` 汇总 → 自动产出团队质量月报（QM 可视化）
- [ ] 两评分体系防混用：在 `INDEX.md` 登记"三维 vs 五维"调用边界与断言（G7）

---

## 6. 风险与边界说明

- 本轮 P0 改动**全部为新增文件**，未修改任何既有成员 Agent、契约、路由或脚本逻辑；已交付 `v1.1.0.zip` 不受影响。
- `task_ledger.py` / `quality_gate.py` 为**机制层工具**，需主理人在 SOP 中显式调用方能全自动生效（P1）。在 P1 落地前，它们已可**手动/按需**调用做质量采样与审计。
- 重打包为 `v1.1.1` 属对交付物的结构性变更，**需用户确认**后再执行（不擅自覆盖 v1.1.0）。
- 所有指标目标值为**初始基线**，运行 4–12 周后按实际数据校准（参照蓝图 §5 第 6 条"试运行校准"思路）。
