# Recruiting Pipeline & ATS Funnel

> 标准定义：招聘全流程管理、漏斗指标、状态机。引用方：recruitment-pipeline。

## 漏斗阶段

| 阶段 | 说明 | 关键动作 |
|------|------|---------|
| 寻源 | 识别并触达候选人 | 个性化触达、渠道投放 |
| 筛选 | 电话/视频初筛 | 评估基本匹配 |
| 面试 | 结构化面试 | 多轮评估、评分卡 |
| 讨论 | 团队决策 | 校准反馈 |
| Offer | 发出录用通知 | 薪酬包、谈判 |
| 入职 | Offer 已接受 | 转入入职流程 |

## 关键指标

- **阶段速度**：每阶段平均天数（天）
- **转化率**：相邻阶段通过比例（%）
- **渠道效果**：各渠道有效简历量 / Offer 量
- **Offer 接受率**：接受 Offer / 发出 Offer（%）
- **招聘周期**：寻源→入职总天数

## 候选人状态机（ATS 语义）

```
pending -> hr_approved -> [exam_pending -> exam_passed] -> dept_approved -> [面试轮次] -> final_approved
```

每个阶段可 approve（推进）或 reject（终止）。动作：`hr_approve / hr_reject / dept_approve / dept_reject / final_approve / final_reject`。

## 职位生命周期

```
pending -> active -> paused <-> active -> closed
```

## 面试状态机

```
to_be_scheduled -> scheduled -> pending_evaluation -> completed | cancelled
```

## 漏斗诊断输出模板

```markdown
## 招聘漏斗 — [岗位/时间范围]

### 漏斗数据
| 阶段 | 候选人数 | 转化率 | 平均天数 |

### 瓶颈分析
[最大流失点 + 原因假设]

### 优化建议
[可执行动作，按影响排序]
```

## 使用纪律

- 不猜 ID：所有候选人/职位/面试必须先查询再操作
- 破坏性动作（取消、拒绝）执行前必须向用户确认
- 无结果时建议放宽关键词，不编造数据
- 界面语义用中文，状态枚举用英文
