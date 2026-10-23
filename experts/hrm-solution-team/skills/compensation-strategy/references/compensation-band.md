# Compensation Band & Market Benchmarking

> 标准定义：薪酬定薪判断、四层证据强度、三级置信度、输出协议。引用方：compensation-strategy。

## 数据来源分层（四层证据强度）

| 层级 | 类型 | 说明 |
|------|------|------|
| 1 | `official_policy` | 官方政策（最强） |
| 2 | `paid_survey_data` | 付费薪酬调研 |
| 3 | `internal_company_data` | 公司内部数据 |
| 4 | `public_market_signal` | 公网市场信号（最弱） |

## 结论置信度分级纪律

| 等级 | 条件 | 行为 |
|------|------|------|
| 正式建议 | internal + paid_survey + candidate_pay + budget **全部满足** | 给出明确定薪建议 |
| 弱建议 | 缺 band 或 internal_data 之一 | 降级表述，注明缺口 |
| 仅市场信号判断 | 仅有 public_market_signal | **禁止冒充正式建议** |

## 抽取字段

```
job_family / job_level / band_min / band_mid / band_max /
market_p25 / market_p50 / market_p75 /
candidate_current_pay / candidate_expected_pay /
internal_peer_reference / budget_range
```

## 判断规则

1. 同时具备 `internal_company_data + paid_survey_data + candidate_current_pay_or_total_comp + budget_range` 才可给正式建议
2. 只有 `public_market_signal` 时只能给"市场信号判断"
3. 缺 `band` 或 `internal_company_data` 时不得假装完成内部公平判断
4. 缺 `budget_range` 时不得假装能完成审批级建议
5. 缺 `candidate_current_pay` 或总包口径时主动降低结论强度

## 输出协议（11 字段）

```text
normalized_data
decision_summary # 先回答"怎么定"或"能不能报"
decision_basis # band/市场/内部参考讲清楚
missing_information # 只写真正影响判断的缺口
risk_summary # 申报失败/内部公平/预算风险
priority_issues # 按高、中、低排序
next_action # HR 今天能做的动作
message_draft # 默认写给业务负责人/薪酬同事
record_update # 需要更新哪些记录
human_confirmation_needed # 还要谁确认什么
compliance_warning_if_any # 合规风险提示
confidence # 正式建议/弱建议/仅市场信号判断
```

## 工作原则

1. 先给结论，再给依据，再给待办
2. 输入默认不干净，先归一化，不要求用户先整理完
3. 定薪判断优先看 band、市场、内部公平，不只看一个数字
4. 缺政策口径或核心字段时明确降置信度，不装确定
5. 对公网职位薪资，只能当市场信号，不能冒充正式薪酬调研

> **参见反例库**：[`compensation-pitfalls.md`](./compensation-pitfalls.md) — 拍脑袋定薪 / 内外倒挂 / 调薪无据 / 用市场信号冒充正式调研 / 个税五险一金错算五类高发反模式。
