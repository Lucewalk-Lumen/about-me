---
name: hrm-solution-contracts
description: HRM 团队共享契约单一基准——全团 hard rules（严格禁止项）与合规类输出契约（法条出处 + 基准日期）。被 lead 与全部 specialist 加载，冲突以本文为准。
---

# HRM 团队共享契约（commons · 单一基准）

本文件是团队级契约的**唯一基准**，包含：
- 全团必须遵守的 hard rules（严格禁止项）
- 合规类结论的强制输出契约（法条出处 + 基准日期）

任何成员 / 主理人不得以任何理由违反或绕过；其他文件（含各 scoped SKILL.md）如与本文冲突，一律以本文为准。

## 严格禁止（hard rules）

1. **禁止编造法规条文编号 / 官方 URL / 生效日期** —— 无可核验出处的合规结论必须标注「需人工核实」，不得以无出处形式呈现为确定结论。
2. **禁止主理人代写成员专业产出** —— PRD / 架构设计 / 代码 / 测试必须由对应成员 Agent 输出后再采信，主理人只做编排与汇编。
3. **禁止跳过合规闸门 `finalize()` 签名放行** —— 所有交付（含单一模块咨询）必经合规闸门终检：编排层调用 `skills/hrm-solution/scripts/security/compliance_gate.py` 的 `enforce_final_gate()` / `finalize()`；命令行等价形态为 `python3 skills/hrm-solution/scripts/security/compliance_gate.py --text '<TEXT>'`（`BLOCKED` 退出码为 3）。主理人不得自行放行 P0 风险，亦不得以任何形式绕过闸门。
4. **禁止单一 Agent 自填 `compliance: PASSED` 绕过闸门** —— 任何 Agent 不得在自身产出中预设 `compliance.gate = PASSED`；该字段必须由闸门在最终签名时填入。
5. **禁止在未被授予的 phase 内修改 `envelope.compliance` 字段** —— 跨 Agent 信息流以 `scripts/security/envelope.py` 签名为准；信封字段禁止运行时篡改。

## 输出契约

适用于引用本知识库产出任何合规判断的 Agent（劳动合规、薪酬策略、绩效管理及主理人终审）。

### 强制标注规则

**每一条合规结论都必须同时携带「法条出处」与「基准日期」，二者缺一不可。** 无法给出可核验出处的结论，必须显式标注「需人工核实」，不得以无出处形式呈现为确定结论。

| 要素 | 要求 | 示例形态 |
|------|------|---------|
| 法条出处 | 法律/法规/规章/地方政策的**名称 + 条款号**，地方政策另附发文机关与文号 | `《中华人民共和国劳动合同法》第八十二条` |
| 基准日期 | 该条款所依据版本的**生效日期或数据基准日**，地方社保/公积金费率标注适用年度 | `基准日期：2013-07-01 修正版` |
| 核实状态 | `已核实`（出处可定位）或 `需人工核实`（出处缺失、存疑或时效不确定） | `需人工核实` |

### 输出格式

文本交付中，每条结论按以下形态成文：

```
【结论】未在用工之日起一个月内订立书面劳动合同的，需向劳动者每月支付二倍工资。
【依据】《中华人民共和国劳动合同法》第八十二条
【基准日期】2013-07-01 修正版
【核实状态】已核实
```

结构化交付中，`findings` / `basis` 类字段按以下形状扩展：

```json
{
  "conclusion": "...",
  "legal_basis": { "instrument": "《中华人民共和国劳动合同法》", "article": "第八十二条", "issuer": "全国人大常委会", "doc_no": null },
  "baseline_date": "2013-07-01",
  "verification": "verified|manual_review_required",
  "note": "verification 为 manual_review_required 时必须在此写明缺口：出处未定位 / 版本时效存疑 / 地方口径差异"
}
```

### 判定与禁止事项

- 出处、条款号、发文字号、官方 URL、生效日期**一律不得编造或凭格式推导拼接**；记不准即置 `manual_review_required`。
- 地方性政策（社保基数、公积金比例、最低工资、高温津贴等）必须标注适用城市与适用年度，跨年度沿用前须提示核对当年官方发布。
- `verification: manual_review_required` 的条目不得计入「已通过合规审查」的结论集，需在交付摘要中单列清单。
- 本契约为**增量约束**：不替代、不放宽各 Agent 既有护栏与合规闸门（P0 拦截、`legal_review: required` 触发条件等），两者同时生效。

## 质量指标契约（v1.1.1 起生效）

团队级可衡量质量指标（QM 系列）是共享基座的**第二层硬约束**，与上文 hard rules / 输出契约并列，被主理人与全部 specialist 加载；冲突以本文为准。指标定义、公式、目标值、采集方式与责任方以 `quality/team-quality-plan.md` §2 为单一基准。

### 协作层硬目标（必须达成）

| 编号 | 指标 | 目标值 | 采集来源 |
|------|------|--------|---------|
| QM-01 | 信封验签通过率 | **100%** | `envelope.py verify`（退出 0/4）+ `quality_gate.envelope_signature_valid` |
| QM-02 | 合规闸门零逃逸（P0 被自动放行次数） | **0** | `compliance_gate.py` 退出码 3 + hard rule 3/4 |
| QM-03 | 回传契约完整率 | **100%** | `quality_gate.return_contract_complete` |
| QM-04 | 合规出处标注率 | **100%** | `quality_gate.compliance_citation_complete` + Step 6a.1 |
| QM-05 | PII 脱敏覆盖率 | **100%** | `pii.contains_pii` + `quality_gate.pii_masked` |
| QM-07 | 跨成员信息流经主理人中转率 | **100%**（架构约束） | 协作规则第 3 条 + `task_ledger` |

### 协作层软目标（持续改进，运行 4–12 周后校准）

| 编号 | 指标 | 初始目标值 | 采集来源 |
|------|------|-----------|---------|
| QM-06 | 路由命中准确率 | ≥ 95% | `routing.yaml` + 人工抽检 |
| QM-08 | 任务按时交付率 / 超时代写率 | 代写 ≤ 5% | `task_ledger.summary`（delivery_rate_pct / agent_error_counts） |
| QM-09 | 错误恢复成功率 | ≥ 90% | `task_ledger.summary`（error_recovery_rate_pct / dead_letter） |
| QM-10 | 量化可追溯率 | 100% | `engine_service.dispatch_envelope`（version/baseline_date）+ Step 6a.3 |
| QM-12 | 信封密钥保护率 | 100% | `envelope.py key-protect`（退出 0） |
| QM-13 | 引擎错误率 | < 5% | `engine_service.dispatch_envelope`（status=error） |
| QM-11 | 寻访专项（沿用蓝图 §3.3） | 命中率≥60% / 复用率≥40% / 字段完整度100% / 合规零违规0 | `talent-sourcing` 运行统计 + `quality_gate --spec talent-sourcing` |

### 强制动作（与 SOP 绑定）

- 主理人 Step 3 中转后**必须**运行 `quality_gate.py check`；任一必须项（QM-01/03/04/05）未过不得进入汇编。
- 主理人 Step 2/3/5/6 **必须**经 `task_ledger.py` 登记任务生命周期；`BLOCKED` 不得进 `deliver`。
- 交付摘要**必须**附质量快照（`quality_gate` 综合分 + `task_ledger.summary` 协作层指标）。
