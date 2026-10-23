# shortlist 交付模板

> shortlist 是 talent-sourcing 的主交接物：JSON 为结构化契约（入信封），Markdown 为阅读版报告。两者同源生成，内容一致；一切 PII 须先经 `pii.py` 脱敏。

## 1. shortlist JSON 结构

```json
{
  "schema": "sourcing-shortlist",
  "schema_version": "1.1.0",
  "req_id": "J000001",
  "generated_at": "2026-09-29",
  "candidates": [
    {
      "candidate_id": "R000001",
      "masked_name": "张*",
      "grade": "A",
      "sourcing_fit": {
        "reachability": 8.0,
        "tenure_stability": 8.5,
        "comp_fit": 9.0,
        "overall": 8.5,
        "note": "寻访适配三维，权重 30/35/35，仅用于寻访排序"
      },
      "five_dim": {
        "overall": 7.8,
        "note": "复用 candidate_scorer.py 五维口径（技术25/专业20/学习20/匹配20/稳定15）；仅 A 级候选与关键岗位跑",
        "ran": true
      },
      "match_evidence": ["命中标准名：微服务", "命中专属名：订单中心", "城市匹配：杭州"],
      "recommend_reason": "三句以内，说明为什么是这个级别",
      "outreach_suggestion": {
        "platform_version": "见 §3.1（≤200 字）",
        "phone_version": "见 §3.2（≤350 字，覆盖七要素）"
      },
      "action": "48 小时内触达；shortlist 置顶；附定制话术"
    }
  ],
  "excluded": [
    {"candidate_id": "R000002", "reason": "命中 exclude：3 段经历均 <1 年"}
  ],
  "metrics_snapshot": {
    "pool_reuse_ratio": 0.5,
    "field_completeness": 1.0
  }
}
```

## 2. shortlist Markdown 报告结构

```markdown
# 寻访 shortlist — {req_id} {title}

> 生成时间：{generated_at} | 寻访画像：见 {req_id}.json | 口径：寻访适配三维仅用于寻访排序，五维为复用 candidate_scorer.py 的预筛分

## 候选人卡片（按分级排序，A 级置顶）

### {masked_name}（{candidate_id}）— {grade} 级
- 现职：{current_company} / {current_title} | 城市：{city} | 年限：{years_of_exp} 年
- 匹配依据：{match_evidence 逐条}
- 寻访适配三维：触达 {reachability} / 稳定 {tenure_stability} / 薪酬 {comp_fit} → 综合 {overall}（权重 30/35/35）
- 五维预筛分：{five_dim.overall}（复用 candidate_scorer.py；未跑则写「未跑，理由」）
- 分级：{grade} | 推荐理由：{recommend_reason}
- 触达建议：{action}
- 触达话术：见下方双版本模板（交付前须经 labor-compliance 审查）

## 未入选记录
| 候选人 | 原因 |
|---|---|

## 指标快照
- 人才库复用率：{pool_reuse_ratio}（目标 ≥40%）
- 字段完整度：{field_completeness}（目标 100%，缺一即不出 shortlist）
```

## 3. 触达话术双版本模板

> 两个版本都必须：不含薪酬具体数字承诺（薪酬表述转 compensation-strategy 口径）；不含歧视性内容；交付前经 labor-compliance 审查。

### 3.1 平台版（站内信/私信，≤200 字）

侧重平台、职位权限、前景三要素，语气简短直接：

```
{masked_name}您好，我是{公司}的招聘负责人。看到您在{领域/项目}的经历，我们正在为{业务线}招募{title}：负责{核心挑战一句话}，直接汇报{汇报对象}，团队{团队定位一句话}。业务处于{阶段}，这个岗位有{权限/空间一句话}。方便的话想跟您聊 15 分钟，看是否匹配您下一阶段的规划。期待回复。
```

### 3.2 电话版（≤350 字，覆盖七要素）

七要素：赛道 / 平台 / 挑战 / 权限 / 汇报 / 薪酬 / 发展。逐一覆盖，顺序可按对话调整：

```
{masked_name}您好，我是{公司}招聘负责人{称呼}。

赛道：我们在{赛道}，{一句话说清做什么、市场位置}。
平台：{公司阶段、规模、现金流或增长信号，给确定性}。
挑战：这个岗位要解决的核心问题是{核心挑战}，这正是您{匹配其经历的一句话}能用上的地方。
权限：岗位直接负责{职责范围}，有{决策权/资源}。
汇报：直接汇报给{汇报对象与层级}。
薪酬：整体方案会结合您现有情况做有竞争力的设计，具体数字我们见面后由专人跟您对标确认。
发展：这个位置的下一步是{典型路径}。

您本周哪天方便，我们先约 20 分钟电话细聊？
```

## 4. 交付前检查清单

- [ ] 所有候选人字段完整（技能/城市/年限/来源/同意记录），缺一不出 shortlist
- [ ] PII 全量脱敏（姓名/电话/邮箱为 masked 形态）
- [ ] 分级与分数对应 SKILL.md 分级规则，无分数与档位脱节
- [ ] 话术无双版本缺失、无薪酬承诺、无歧视性表述
- [ ] 已送 labor-compliance 审查并取得结论
- [ ] 信封经 envelope.py 签名后回传主理人
