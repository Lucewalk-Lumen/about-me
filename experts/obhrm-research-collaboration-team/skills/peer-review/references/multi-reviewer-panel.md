# 五视角审稿人体系（multi-reviewer-panel）

> 定位：peer-review 域的多视角评审扩展。采用**五视角不重叠评审 + 主编决策汇总**的核心结构，适配 OBHRM 单包轻量结构。
> 触发：需要多视角评审、模拟期刊同行评审、审稿人视角压力测试时，在 C3 八维诊断基础上叠加本面板。
---

## 一、五人评审面板（5 个不重叠视角）

| 槽位 | 角色 | 评审视角（不重叠） | 不负责什么 |
|------|------|------------------|-----------|
| Journal-Fit | 期刊契合审稿人 | 稿件与目标期刊范围/层级/读者群的匹配度 | 方法细节、领域深度 |
| Reviewer 1 | 方法学审稿人（methodology） | 研究设计有效性、数据采集适当性、统计严谨性、结论是否被数据支撑、可复现性 | 文献综述完整性、跨学科影响 |
| Reviewer 2 | 领域审稿人（domain） | 领域专业性、实质准确性、OBHRM 领域充分性、文献对话深度 | 统计细节、跨学科 |
| Reviewer 3 | 视角审稿人（perspective） | 跨学科相关性、更广泛影响、替代解释 | 方法学、领域细节 |
| Devil's Advocate | 反对者 | 挑战核心论证、识别逻辑谬误、找最强反例 | 常规评分 |

> **核心纪律**：五人视角**互不重叠**——每人只对自己的视角负责，不越界替其他角色打分；评审结论由主编（Editorial Synthesizer）统一合成，避免"每人评一遍全文"的冗余。

---

## 二、执行流程

1. **定场**：根据稿件领域与目标期刊，动态配置 5 位审稿人的具体身份与专长（field configuration）。
2. **并行评审**：5 人分别产出独立评审卡（Peer Review Report，见 §三），互不参考。
3. **主编合成**：Editorial Synthesizer 汇总 5 份报告 → 统一 Editorial Decision + Revision Roadmap（见 §四）。
4. **交叉一致性**：检查 5 份报告的建议是否一致；分歧点列入 Roadmap 优先级。

---

## 三、Peer Review Report 模板（每人一份）

```
# Peer Review Report

## Reviewer Role *
[Journal-Fit / Reviewer 1 (Methodology) / Reviewer 2 (Domain) / Reviewer 3 (Perspective) / Devil's Advocate]

## Review Focus *
[本视角的评审焦点，2-3 句]

## Overall Assessment *
### Recommendation *
- [ ] Accept — 可直接发表，仅格式微调
- [ ] Minor Revision — 小修，无需再审
- [ ] Major Revision — 大修，需复审
- [ ] Reject — 不适合本期刊

## Strengths *
[本视角看到的真实贡献，2-5 条]

## Major Issues *
[按重要性排序，每条含：问题描述 / 严重程度（统一 4 级：必须修改/强烈建议修改/建议修改/可选改进；别名 致命/重大/中等 ↔ 必须修改/强烈建议修改/建议修改）/ 为什么是问题 / 修改建议]

## Minor Issues
[格式、措辞、图表标注等细节]

## Detailed Comments
[仅评论与本视角相关的章节]
```

---

## 四、Editorial Decision 模板（主编合成）

```
# Editorial Decision

## Decision *
[Accept / Minor Revision / Major Revision / Reject]

## Panel Summary
[5 人建议汇总表：角色 | 建议 | 关键理由]

## Editor's Synthesis
[综合 5 视角后的总体判断：核心贡献是否成立、最严重问题、录用可能性]

## Revision Roadmap *
| 优先级 | 任务 | 负责视角 | 预计工作量 | 完成后提升 |
|--------|------|---------|-----------|-----------|
|  必须 | … | Reviewer 1（方法） | … | … |
|  建议 | … | Reviewer 2（领域） | … | … |
|  可选 | … | … | … | … |

## Remaining Risks
[分歧点、未解决争议、作者需注意的边界]
```

---

## 五、与现有 peer-review 的关系

| 现有能力 | 本模板补充 |
|---------|-----------|
| C3 八维诊断（单角色全面诊断） | **五视角并行**——从 5 个不重叠角度各自聚焦，避免单角色面面俱到但深度不足 |
| 三角色交叉复核（审稿人/方法审计师/主编） | 扩展为 **5 审稿人 + 主编**，增加 Devil's Advocate（逻辑挑战）与 Journal-Fit（期刊契合）两个视角 |
| C4 成稿报告 | 提供 Peer Review Report 结构化模板与 Editorial Decision 合成模板 |

**使用建议**：
- 常规审稿 → 八维诊断（C3）即可，成本低。
- 投稿前压力测试 / 重要稿件再审 → 叠加本五视角面板，获取多角度不重叠意见。
- Devil's Advocate 视角尤其适合自查"论证是否被最强反例击穿"。
