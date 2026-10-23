# 问答质量与溯源报告模板（Answer Quality & Grounding Report）

> 产出成员：answer-quality（答谨）| 配套脚本：answer_quality_calc.py
> 平台前提：ima 基于知识库精准问答 + 原文溯源；库外问题必须拒答而非编造

## 填写说明
- 第 1-4 节三项指标必须引用 answer_quality_calc.py 输出，禁止 LLM 直接估算。
- 幻觉统计必须走黄金集双盲标注（两名标注员一致才计数），单人标注作废。
- P0 门禁任一不过 → 结论必须写"阻断发布"，不得降级为"建议"。

---

# 问答质量与溯源报告 — <项目名>

## 1. 溯源命中率
| 指标 | 值 |
|------|-----|
| 总回答数 total_answers | |
| 带有效溯源数 sourced | |
| 溯源命中率 source_hit_rate | |
| 断链条目清单（定位到 source_file + locator） | |

## 2. 幻觉审计（黄金集双盲标注）
| 指标 | 值 |
|------|-----|
| 黄金集样本数（≥30，不足降级参考值） | |
| 幻觉回答数 hallucinations | |
| 幻觉率 hallucination_rate | |
| 严重度分布 | |
| 库外问题被回答数 out_of_kb_answered（高危，单独计数） | |

## 3. 拒答纪律
| 指标 | 值 |
|------|-----|
| 应拒答样本数 should_refuse | |
| 应拒且实拒数 refused_correctly | |
| 拒答精准率 refusal_precision | |
| 误拒率 false_refusal_rate | |

## 4. 质量门禁判定（脚本 gate 模式）
| 指标 | 实测 | 阈值 | 级别 | 判定 |
|------|------|------|------|------|
| 溯源命中率 | | ≥0.90 | P0 | |
| 幻觉率 | | ≤0.05 | P0 | |
| 拒答精准率 | | ≥0.80 | P1 | |
- 门禁裁决 verdict：pass / fix / **block**
- 库外被回答 >0 → 强制 block
- 与 eval-benchmark 联合裁决（W21 共享库发布门禁）

## 5. bad-case 回流清单
| 类型 | 定位（source_file + locator） | 回流成员 |
|------|-------------------------------|----------|
| 幻觉/断链 | | quality-auditor（修条目）/ retrieval-tuner（修召回） |

## 6. 数据来源三态
| 数据 | 状态 |
|------|------|
| 问答评估样本集 | 用户提供 |
| 门禁阈值口径 | 有来源（本方法论） |
| 双盲标注结果 | 有来源（标注记录） |
