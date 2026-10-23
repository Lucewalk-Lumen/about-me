# IMA知识库自动运营团 — 技能手册索引（v4.0）

## 技能结构

```
ima-kb-ops-playbook/
├── SKILL.md                              ← 技能入口（必须）
├── references/                           ← 参考资料（18）
│   ├── prompt-parsing-methodology.md     ← 提示词解析方法论
│   ├── kb-planning-methodology.md        ← 知识库规划方法论
│   ├── multimodal-ingestion.md           ← 多模态入库方法论（视频派生路径）
│   ├── content-production-framework.md   ← 内容生产框架
│   ├── quality-assessment-system.md      ← 质量评估体系
│   ├── skill-generation-guide.md         ← Skill 生成指南
│   ├── auto-sync-design.md               ← 自动更新管道设计
│   ├── retrieval-tuning-methodology.md   ← 检索调优方法论
│   ├── kb-security-compliance.md         ← 合规安全方法论
│   ├── eval-benchmark-methodology.md     ← 评估与基准方法论
│   ├── version-management-protocol.md    ← 版本管理协议
│   ├── ops-monitoring-metrics.md         ← 运营监控指标
│   ├── adoption-training-methodology.md  ← 采纳与培训方法论
│   ├── kb-insight-roi-methodology.md     ← 知识洞察与 ROI 方法论
│   ├── source-channel-methodology.md     ← 采集渠道方法论（v4.0 新增）
│   ├── kb-collab-governance.md          ← 共享协作治理（v4.0 新增）
│   ├── kb-product-generation.md         ← 知识产物生成（v4.0 新增）
│   └── answer-quality-grounding.md      ← 问答质量与溯源（v4.0 新增）
├── templates/                            ← 模板文件（18）
│   ├── prompt-intent-analysis-template.md← 提示词解析报告模板
│   ├── kb-structure-plan-template.md     ← 知识库结构方案模板
│   ├── multimodal-ingest-plan-template.md← 多模态入库方案模板（含 ima 能力核对）
│   ├── content-entry-template.md         ← 内容条目模板
│   ├── quality-audit-report-template.md  ← 质检报告模板
│   ├── skill-config-template.md          ← Skill 配置模板
│   ├── auto-sync-pipeline-template.md    ← 自动更新管道模板
│   ├── retrieval-tuning-plan-template.md ← 检索调优方案模板
│   ├── kb-security-plan-template.md      ← 合规安全方案模板
│   ├── eval-benchmark-plan-template.md   ← 评估与基准方案模板
│   ├── version-management-template.md    ← 版本管理模板
│   ├── ops-monitoring-report-template.md ← 运营报告模板
│   ├── adoption-training-plan-template.md← 采纳与培训方案模板
│   ├── kb-insight-report-template.md     ← 知识洞察与 ROI 报告模板
│   ├── source-channel-plan-template.md   ← 采集渠道方案模板（v4.0 新增）
│   ├── kb-collab-plan-template.md       ← 共享协作方案模板（v4.0 新增）
│   ├── kb-product-plan-template.md      ← 知识产物排产模板（v4.0 新增）
│   └── answer-quality-report-template.md← 问答质量报告模板（v4.0 新增）
└── scripts/                              ← 确定性计算脚本（16，闭式解析公式）
    ├── prompt_intent_calc.py             ← 提示词解析指标（槽位完整度/意图置信度/改写覆盖率/追问判定）
    ├── quality_score_calc.py             ← 质量评分计算器（五维加权）
    ├── capacity_plan_calc.py             ← 容量规划计算器（条目增长预测）
    ├── retrieval_metrics_calc.py         ← 检索效果计算器（Precision/Recall/MRR/NDCG）
    ├── retrieval_tuning_calc.py          ← 检索调优权衡计算器（K_max/P@K衰减/延迟-质量权衡）
    ├── sync_schedule_calc.py             ← 自动更新调度计算器（源分级周期/SLA合规率/峰值批大小）
    ├── ops_health_calc.py                ← 运营健康度计算器（综合健康评分）
    ├── kb_roi_calc.py                    ← 知识库 ROI 计算器（月价值/成本/ROI倍数/回收期/孤儿冷门率）
    ├── kb_security_calc.py               ← 合规安全计算器（数据分级暴露面/合规风险分/高危占比）
    ├── multimodal_ingest_calc.py          ← 多模态入库计算器（各模态条目/分块数/token 预算/视频派生/ima 护栏）
    ├── eval_gate_calc.py                 ← 评估门禁计算器（黄金集置信度/指标达标/发布门禁 P0-P1 判定）
    ├── adoption_calc.py                  ← 采纳率计算器（漏斗转化率/激活率/留存率/使用深度）
    ├── source_channel_calc.py            ← 采集渠道计算器（v4.0：8 渠道分批/预转换/容量护栏）
    ├── collab_conflict_calc.py           ← 共享协作计算器（v4.0：并发冲突概率/评审负载/权限覆盖）
    ├── product_plan_calc.py             ← 知识产物计算器（v4.0：产能/工时/复用系数/可交付性）
    └── answer_quality_calc.py           ← 问答质量计算器（v4.0：溯源命中率/幻觉率/拒答精准率/门禁判定）
```

## 快速导航（环节 × 文件 × 脚本）

| 环节 | 需求 | 读取参考 | 使用模板 | 调用脚本 |
|------|------|----------|----------|----------|
| 提示词解析 | 拆解用户提示词 | `prompt-parsing-methodology.md` | `prompt-intent-analysis-template.md` | `prompt_intent_calc.py` |
| 规划 | 设计知识库结构 | `kb-planning-methodology.md` | `kb-structure-plan-template.md` | `capacity_plan_calc.py` |
| 多模态入库 | 文档/图片/音频入库（ima 直接支持）；**视频不支持直接入库，走「音轨转音频 + 截图入图片」派生路径** | `multimodal-ingestion.md` | `multimodal-ingest-plan-template.md` | `multimodal_ingest_calc.py` |
| 生产 | 格式化内容条目 | `content-production-framework.md` | `content-entry-template.md` | — |
| 质检 | 评估内容质量 | `quality-assessment-system.md` | `quality-audit-report-template.md` | `quality_score_calc.py` |
| Skill 生成 | 创建 Skill 配置 | `skill-generation-guide.md` | `skill-config-template.md` | — |
| 自动更新 | 设计同步管道 | `auto-sync-design.md` | `auto-sync-pipeline-template.md` | `sync_schedule_calc.py` |
| 检索调优 | 提升检索精度 | `retrieval-tuning-methodology.md` | `retrieval-tuning-plan-template.md` | `retrieval_metrics_calc.py` + `retrieval_tuning_calc.py` |
| 合规安全 | 分级/权限/PII/审计 | `kb-security-compliance.md` | `kb-security-plan-template.md` | `kb_security_calc.py` |
| 评估基准 | 黄金集/门禁/回归 | `eval-benchmark-methodology.md` | `eval-benchmark-plan-template.md` | `eval_gate_calc.py` |
| 版本 | 管理版本快照 | `version-management-protocol.md` | `version-management-template.md` | — |
| 监控 | 监控运营健康 | `ops-monitoring-metrics.md` | `ops-monitoring-report-template.md` | `ops_health_calc.py` |
| 采纳培训 | 让人用起来 | `adoption-training-methodology.md` | `adoption-training-plan-template.md` | `adoption_calc.py` |
| 洞察/ROI | 判断知识库价值 | `kb-insight-roi-methodology.md` | `kb-insight-report-template.md` | `kb_roi_calc.py` |
| 采集渠道 | 8 渠道选型分批 | `source-channel-methodology.md` | `source-channel-plan-template.md` | `source_channel_calc.py` |
| 共享协作 | 多人协作治理 | `kb-collab-governance.md` | `kb-collab-plan-template.md` | `collab_conflict_calc.py` |
| 知识产物 | 产物排产规划 | `kb-product-generation.md` | `kb-product-plan-template.md` | `product_plan_calc.py` |
| 问答质量 | 溯源/幻觉/拒答门禁 | `answer-quality-grounding.md` | `answer-quality-report-template.md` | `answer_quality_calc.py` |

## 脚本用法

### prompt_intent_calc.py（v2.0 新增）
```bash
# 单项：槽位完整度 + 缺失评分
python scripts/prompt_intent_calc.py --mode single --filled 3 --total 5 --intent-scores '[0.7,0.2,0.1]'
# 追问判定：完整度或置信度 < 0.7 → 必须追问
python scripts/prompt_intent_calc.py --mode clarify --filled 2 --total 6 --intent-scores '[0.5,0.3]'
# 改写覆盖率（实体守恒校验，必须 = 1.0）
python scripts/prompt_intent_calc.py --mode full --filled 4 --total 5 --entities '["固态电池","2026版"]' --rewritten-entities '["固态电池","2026版"]'
```

### sync_schedule_calc.py（v2.0 新增）
```bash
# 全量：源分级周期 + SLA 合规率 + 峰值批大小
python scripts/sync_schedule_calc.py --mode full --sources '[{"name":"法规库","level":"P0","sla_hours":1,"rate_per_day":20},{"name":"技术文档","level":"P1","sla_hours":24,"rate_per_day":50}]'
# 仅合规检查（列出非合规源）
python scripts/sync_schedule_calc.py --mode compliance --sources '[...]'
```

### retrieval_tuning_calc.py（v2.0 新增）
```bash
# K_max（上下文预算约束下的最大 Top-K）
python scripts/retrieval_tuning_calc.py --mode kmax --chunk-size 500 --context-budget 8192
# 推荐方案（P@K 衰减曲线 + 延迟-质量权衡分）
python scripts/retrieval_tuning_calc.py --mode full --chunk-size 500 --context-budget 8192 --relevant 10 --mrr 0.5 --k-list '[1,3,5,10]' --latency-p99-s 1.2 --latency-sla-s 2.0
```

### kb_roi_calc.py（v2.0 新增）
```bash
# 全量：月价值/月成本/ROI 倍数/回收期/冷门率/孤儿率
python scripts/kb_roi_calc.py --mode full --hits-per-month 12000 --minutes-saved 5 --hourly-rate 100 --maintain-hours 40 --storage-fee 500 --token-fee 3000 --capex 50000 --total-entries 800 --zero-hit-entries 200 --orphan-entries 60
```

### quality_score_calc.py
```bash
python scripts/quality_score_calc.py --mode single --accuracy 8 --completeness 7 --consistency 9 --timeliness 8 --retrievability 7
python scripts/quality_score_calc.py --mode batch --entries '[{"accuracy":8,...}, ...]'
python scripts/quality_score_calc.py --mode stats --entries '[...]'
```

### capacity_plan_calc.py
```bash
python scripts/capacity_plan_calc.py --mode full --initial 100 --rate 0.1 --months 12 --entries 500
```

### retrieval_metrics_calc.py
```bash
python scripts/retrieval_metrics_calc.py --mode full --relevant-retrieved 8 --total-relevant 10 --k 5 --rankings '[1,2,1,3]' --relevances '[3,2,3,1,2]'
```

### ops_health_calc.py
```bash
python scripts/ops_health_calc.py --mode health --metrics '{"recall":0.85,"precision":0.72,"response_time_s":2.5,"satisfaction":4.2,"coverage":0.88,"skill_success_rate":0.95,"content_freshness":0.82}'
```

### kb_security_calc.py（v3.0 新增）
```bash
# 全量：数据分级暴露面 + 合规风险分 + 高危占比
python scripts/kb_security_calc.py --mode full --levels '{"public":100,"internal":50,"restricted":20,"confidential":5}' --audit-coverage 0.8 --pii-unhandled 0.3
```

### multimodal_ingest_calc.py（v3.0 新增）
```bash
# 全量：各模态条目/分块数 + token 预算
python scripts/multimodal_ingest_calc.py --mode full --docs 20 --pages-per-file 8 --chunks-per-page 2 --images 15 --audio-seconds 3600 --video-seconds 1800 --fps 0.5 --video-asr-segments 100 --chunk-tokens 500
```

### eval_gate_calc.py（v3.0 新增）
```bash
# 全量：指标达标判定 + 发布门禁 P0/P1 + 黄金集置信度
python scripts/eval_gate_calc.py --mode full --n 60 --metrics '{"accuracy":{"value":0.92,"threshold":0.9},"harmlessness":{"value":0.99,"threshold":0.95},"mrr":{"value":0.68,"threshold":0.6}}' --p0 '["accuracy","harmlessness"]'
```

### adoption_calc.py（v3.0 新增）
```bash
# 全量：采纳漏斗转化率 + 激活率 + 周留存 + 使用深度 + 最大卡点
python scripts/adoption_calc.py --mode full --counts '{"aware":1000,"signup":400,"first_use":180,"weekly_active":120,"power":45}' --week1-active 120 --week2-active 72 --power-users 45
```

### source_channel_calc.py（v4.0 新增）
```bash
# 全量：8 渠道分批 + 预转换 + 容量护栏（含视频派生路径）
python scripts/source_channel_calc.py --mode full --docs 150 --images 30 --audio-files 20 --videos 30 --over-spec-pdfs 4 --channels '["local_file","wechat_file","web_link"]'
# 单渠道容量护栏（≤50 文件/批）
python scripts/source_channel_calc.py --mode guardrails --batch-files 80
```

### collab_conflict_calc.py（v4.0 新增）
```bash
# 全量：并发冲突概率（0-1）+ 评审负载 + 权限覆盖
python scripts/collab_conflict_calc.py --mode full --month-changes 500 --roles 5 --overlap-rate 0.3 --minutes-per-conflict 10 --reviewers 2 --reviewer-hours 20 --granted-ops 18 --expected-ops 24
# 仅冲突概率（单角色 → 0）
python scripts/collab_conflict_calc.py --mode conflict --month-changes 200 --roles 10 --overlap-rate 0.6
```

### product_plan_calc.py（v4.0 新增）
```bash
# 全量：产物产能 + 工时预算 + 复用系数 + 可交付性
python scripts/product_plan_calc.py --mode full --frequencies '{"podcast":4,"mindmap":8,"report":2,"ai_note":6}' --available-hours 60 --minutes-per-product 30 --high-reuse-topics 12 --total-topics 30 --total-entries 800 --passing-entries 600
```

### answer_quality_calc.py（v4.0 新增）
```bash
# 全量：溯源命中率 + 幻觉率 + 拒答精准率 + 门禁判定
python scripts/answer_quality_calc.py --mode full --total-answers 200 --sourced 184 --hallucinations 6 --should-refuse 40 --refused-correctly 35 --should-answer 160 --wrongly-refused 8
```

## 交叉校验规则（全环节，与 SKILL.md 一致）

- 提示词：意图置信度低 且 缺失槽位 ≥2 → 必须追问；改写覆盖率必须 = 1.0；追问 ≤3 项
- 自动更新：TTL 逐内容类型绑定（禁止全库统一）；单源故障影响面 < 全库 20%；水位线重放必须幂等；周期/合规率引用 sync_schedule_calc
- 检索调优：单变量（一轮只改一个维度）；调优前后同一 bad-case 集（≥10 条）重测；P99 超 SLA 直接回退；指标引用 retrieval_metrics_calc / retrieval_tuning_calc
- 知识洞察：冷门率 30 天口径、归档 60 天口径；缺口主题必须有 bad-case 原文佐证（≥2 条）；ROI 三项输入必须标来源，含假设估算则结论降级为"参考值"
- 采集渠道（v4.0）：单次批量 ≤50 文件（ima 护栏，超限必拆批）；渠道-格式匹配矩阵禁混用；预转换产物必须可溯源回原始渠道；分批/预转换/护栏引用 source_channel_calc
- 共享协作（v4.0）：权限矩阵 deny-by-default（禁止默认全开）；同名条目必须仲裁归属；冲突概率 0-1 越界视为模型输入错误；并发冲突/评审负载引用 collab_conflict_calc
- 知识产物（v4.0）：单件产物必须绑定 ≥1 个 KB 来源条目（可溯源）；高复用主题须先质检通过再排产；产能/工时/复用系数引用 product_plan_calc
- 问答质量（v4.0）：溯源命中率 / 幻觉率 / 拒答精准率三指标缺一即门禁 fail；bad-case 须原文佐证；门禁 verdict 引用 answer_quality_calc，P0（幻觉率 / 溯源）任一不过 → block 阻断
- 全部指标数字必须引用 scripts/ 输出，禁止手写估算；报告落款标注"有来源/用户提供/假设估算"三态
