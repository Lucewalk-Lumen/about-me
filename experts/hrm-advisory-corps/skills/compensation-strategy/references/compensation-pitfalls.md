# Compensation Band Pitfalls

> 与正篇 `compensation-band.md` 配套使用：正篇给四层证据 + 三级置信度 + 11 字段输出协议，本篇给典型踩坑。
> 反例基于公开 HR 案例整理，**禁止编造**。每个反例给出「错点」「后果」「修正方向」。

## 1. 拍脑袋定薪 vs 三档对标定薪

### 1.1 拍脑袋定薪（命中 5 条工作原则违反）

```
"市场行情差不多 25K-30K，那就给 28K 吧。"
```

| 错点 | 违反原则 | 后果 |
|---|---|---|
| 无 band 数据 | 原则 3（不只看一个数字） | 内外倒挂 / 内部公平失控 |
| 无 paid_survey | 4 层证据缺 1 | 置信度降级（仅市场信号判断） |
| 无 internal_company_data | 4 层证据缺 1 | 触发"不得假装完成内部公平判断" |
| 无 budget_range | 缺关键字段 | 触发"不得假装能完成审批级建议" |
| 无 candidate_current_pay | 缺关键字段 | 触发"主动降低结论强度" |

### 1.2 三档对标定薪（正例）

```
1. band：内部 P50 区间 24-30K
2. market_p25/p50/p75：25K / 28K / 32K（paid_survey 2026 Q2）
3. internal_peer_reference：同职级 P50 = 27K
4. candidate_current_pay：23K（外 + 4K，约 17% 涨幅）
5. budget_range：26-30K

→ 正式建议：28K（band 中位 + 市场 P50 + 内部公平 + 17% 涨幅合理）
→ confidence：正式建议（4 层证据全齐）
→ 申报口径：baseSalary=28000，不写"特批"（无政策依据）
```

## 2. 内外倒挂（高发致命错）

### 2.1 错形态

- 内部同岗位 P50 = 20K，新招同岗位给 28K（+40%）
- 原因：拍脑袋 + 急用人

### 2.2 后果

- 内部老员工离职风险骤增（认知："我做了 3 年还不如新人"）
- HR 信任坍塌
- 团队稳定性指标恶化（30/60/90 留存 ↓）

### 2.3 修正方向

- 启动 band 重设（参考 05 主体）
- 给老员工做一次结构性调薪（附政策依据 + 时间表）
- 新人薪资回归 band P50-P75

## 3. 调薪无据（命中「输出协议」缺字段）

### 3.1 错形态

```
"小王今年表现不错，涨薪 3K。"
```

- decision_basis 缺失
- priority_issues 缺失
- next_action 缺失
- record_update 缺失

### 3.2 修正方向

按 11 字段输出协议补全：

```text
decision_summary : 涨薪 3000 元（baseSalary 20K → 23K）
decision_basis : KPI 达成率 132%（5 个核心指标全 A）；
 内部 P50 = 22K，涨后接近 P50 上限；
 budget 余额可承担
missing_information : 跨部门 360 评估未做（建议补）
risk_summary : 调薪后接近 P75，需在 Q4 复盘是否够 P75 水平
priority_issues : 中——需补 360 评估后做最终决定
next_action : HR 准备调薪单 + 部门负责人面谈
message_draft : 已生成给直属上级的草稿
record_update : 更新 HRIS baseSalary 与 effectiveDate
human_confirmation_needed : 直属上级 + 部门负责人
compliance_warning_if_any : 无
confidence : 弱建议（缺 360 评估）
```

## 4. 用市场信号冒充正式调研（致命错）

### 4.1 错形态

```
"招聘网站显示这个岗位 30-50K，我们给 35K 算市场水平。"
```

- 公开网站薪资 = public_market_signal（4 层证据中最弱）
- 缺 internal_company_data + paid_survey + candidate_pay + budget
- 违反正篇"判断规则 2"：只有 public_market_signal 时只能给"市场信号判断"

### 4.2 修正方向

- 明确降级为「市场信号判断」
- 标注「正式建议待补 internal_company_data + paid_survey 后给出」
- 在 message_draft 中向业务负责人说明缺口

## 5. 个税 / 五险一金错算（命中计算引擎 fail-fast）

### 5.1 常见输入错

| 错 | 触发 | 引擎表现 |
|---|---|---|
| `base_salary`（snake_case）| 入参键名校验 | `InputValidationError("必填字段 baseSalary 缺失")` |
| `baseSalary: "25000"`（字符串）| 类型校验 | `InputValidationError("字段 baseSalary 必须是数字")` |
| `baseSalary: -1`（负数）| 值校验 | `InputValidationError("字段 baseSalary 不能为负数")` |
| 累计值部分提供 | 跨字段约束 | `InputValidationError("累计值必须完整提供或不提供")` |

### 5.2 修正方向

- 严格遵循 `payroll_engine.py` 字段表（README 已列）
- 旧调用脚本若用 snake_case 必须先迁移到 camelCase
- 累计值要么三个都给（cumulativeIncome / cumulativeInsurance / cumulativeSpecial），要么都不给

## 使用纪律

- 任何反例命中 1 条即触发回正篇对应规则复核
- 反例库非模板，**禁止把反例当成正确案例照抄**
- 调薪 / 定薪决策必须产 11 字段完整协议，缺字段即降 confidence
