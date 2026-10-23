# IMA知识库自动运营团（v4.0）

## 团队定位

覆盖知识库全生命周期（**十八大环节**）的运营专家团：提示词解析 → 规划 → 采集渠道 → 多模态入库 → 生产 → 质检 → Skill 生成 → 自动更新 → 检索调优 → 合规安全 → 评估基准 → 版本 → 监控 → 采纳 → 洞察/ROI → 共享协作 → 知识产物 → 问答溯源，全部指标由闭式解析脚本计算（禁止 LLM 生成假数据）。

> 面向**腾讯 ima 知识库**真实能力边界：视频不支持直接入库，必须走「提取音轨→音频 + 关键帧截图→图片」派生路径；单次批量 ≤50 文件。

## 团队编制（1 主理人 + 18 成员）

| 成员 | 名字 | 职责 | maxTurns |
|------|------|------|----------|
| ima-kb-ops-team-lead | 韩策 | 主理人（知识库运营总监） | 200 |
| prompt-analyst | 顾解 | 用户提示词解析专家 | 50 |
| kb-planner | 林图 | 知识库规划专家 | 50 |
| multimodal-ingest | 陈析 | 多模态入库专家 | 50 |
| content-producer | 陈言 | 内容生产专家 | 50 |
| quality-auditor | 质安 | 知识质量检测师 | 50 |
| skill-engineer | 技匠 | Skill 生成工程师 | 60 |
| auto-sync | 周更 | 自动更新与同步专家 | 50 |
| retrieval-tuner | 寻微 | 检索调优专家 | 50 |
| kb-security | 安澜 | 合规安全专家 | 50 |
| eval-benchmark | 衡准 | 评估与基准专家 | 50 |
| version-manager | 版序 | 版本管理专员 | 40 |
| ops-monitor | 运观 | 运营监控分析师 | 50 |
| adoption-training | 众行 | 采纳与培训专家 | 50 |
| kb-analyst | 见深 | 知识洞察与 ROI 分析师 | 50 |
| **ima-source**（v4） | 顾采 | ima 八大导入渠道规划专家 | 50 |
| **kb-collab**（v4） | 众协 | 共享知识库协作专家 | 50 |
| **kb-product**（v4） | 器成 | 知识产物生成专家 | 50 |
| **answer-quality**（v4） | 答谨 | 问答质量与溯源专家 | 50 |

## 拓扑类型

**串行流水线 + 并行体检支线（W10/W22）**：
- 主链路：规划 → 采集 → 入库 → 生产 → 质检 → 生成 → 自动更新 → 检索 → 合规 → 评估 → 版本 → 监控 → 采纳 → 洞察 → 协作 → 产物 → 问答
- 体检支线：W10 五成员并行 / W22 九成员并行，主理人汇编终稿

## SOP 流程（18 阶段）

Phase 1-14 见 v3.0 基线；**v4.0 新增 Phase 15-18**：
- Phase 15 采集源选型（ima-source）
- Phase 16 共享协作落地（kb-collab）
- Phase 17 知识产物排产（kb-product）
- Phase 18 问答质量门禁（answer-quality）

## 预设 Workflow（W1-W22）

W1-W16 见 v3.0；**v4.0 新增 W17-W22**：
- W17 ima 采集源选型 / W18 共享协作落地 / W19 知识产物排产 / W20 问答质量门禁 / W21 协作+问答联合审计 / **W22 全链路体检（含协作/产物/问答，9 报告并行）**

## 确定性脚本（16 个，全部闭式公式）

原 12 个（quality_score / capacity_plan / retrieval_metrics / retrieval_tuning / ops_health / prompt_intent / sync_schedule / kb_roi / kb_security / multimodal_ingest / eval_gate / adoption）+ **v4.0 新增 4 个**：
- source_channel_calc（8 渠道分批/预转换/容量护栏）
- collab_conflict_calc（并发冲突概率 0-1/评审负载/权限覆盖）
- product_plan_calc（产能/工时/复用系数/可交付性）
- answer_quality_calc（溯源命中率/幻觉率/拒答精准率/门禁判定）

详见 `skills/ima-kb-ops-playbook/INDEX.md`

## 使用方法

1. 用户召唤专家团，输入知识库运营需求（或选 quickPrompt / W1-W22 入口）
2. quickPrompt 三层：新手（从零走流程）/ 提升（检索调优+自动更新）/ 常用（全面体检）
3. 主理人识别意图选 Workflow（不匹配走 Phase 1-18 兜底），按序调度成员
4. 每阶段产出原文传递；数值结论引用 16 脚本输出；最终整合为 `kb-ops-final-report.md`

## 更新记录

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0.0 | 2026-09-07 | 初始版本，1 主理人 + 6 成员 + 6 参考 + 6 模板 + 4 脚本 |
| v2.0.0 | 2026-09-07 | 1+10 编制；参考/模板/脚本 10；W1-W10；SOP 10 阶段；三件套全绿（56 文件） |
| v3.0.0 | 2026-09-07 | 1+14 编制；十四大环节；W1-W16；12 脚本；3 新专家（kb-security/eval-benchmark/adoption-training） |
| v3.1.0 | 2026-09-08 | 视频入库修复：对齐 ima 真实能力（视频走音轨+截图派生路径，非直接入库）；preset 三层（新手/提升/常用） |
| **v4.0.0** | **2026-09-09** | **1+18 编制；十八大环节；W1-W22；16 脚本；4 新专家（ima-source/kb-collab/kb-product/answer-quality）+ 4 脚本 + 4 参考 + 4 模板；SOP 18 阶段；validate/register/package 三件套全绿（99 文件 10.7MB）** |
