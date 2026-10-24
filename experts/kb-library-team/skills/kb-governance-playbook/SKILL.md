---
name: kb-governance-playbook
description: "知识库治理方法论库：八域模型、四池成熟度、grounding 纪律、三级巡检、归档协议、价值度量与冷启动能力地图，附 4 个确定性脚本与 5 份产出模板。形态中立，宿主特例（Obsidian/IMA/LLM Wiki/乐享）见 references/hosts。当智博资料室成员执行采集、分类、晋级、索引、问答、巡检、归档、度量任务时按域引用。"
description_zh: "知识库治理方法论库：八域模型、四池成熟度、grounding 纪律、三级巡检、归档协议、价值度量与冷启动能力地图，附确定性脚本与产出模板，形态中立。"
description_en: "Methodology library for knowledge-base governance: eight-domain model, four-pool maturity, grounding discipline, three-level inspection, archive protocol, metrics and cold-start capacity mapping, with deterministic scripts and output templates. Host-neutral."
version: "1.0.5"
author: "Xing Bu"
---

# 知识库治理方法论库（kb-governance-playbook）

本技能是智博资料室的共享方法论库，承载 references（方法论）、scripts（确定性计算）、templates（产出模板）三类资产。各成员按域引用，不整本通读。

## 一句话主线

四池管成熟度，索引管主题，链接管关系，标签管检索，巡检管质量；答问先 grounding、后引用、再推理，标置信度与出处；缺信息就追问，正式改动一律用户确认。

## 成员引用路由表

| 成员 | 主读 references | 用 scripts | 用 templates |
|---|---|---|---|
| 库正（主理人） | eight-domain-model.md、capacity-map-bootstrap.md、environment-setup.md | — | — |
| 罗采（采集入库） | four-pool-maturity.md、hosts/ 对应宿主篇 | — | — |
| 林归类（分类组织） | four-pool-maturity.md、hosts/obsidian-host.md | — | — |
| 关晋（晋级评审） | four-pool-maturity.md | promotion_gate_check.py | maturity-review-report.md |
| 苏航（索引导航） | hosts/obsidian-host.md（及其他宿主篇） | link_integrity_scan.py | moc-index-template.md |
| 齐证（问答质量） | grounding-discipline.md、inspection-checklist.md | duplicate_detect.py、health_score_calc.py | inspection-report.md、qa-grounding-template.md |
| 安档（归档度量） | archive-protocol.md、metrics-methodology.md | health_score_calc.py | archive-log-template.md |

## references 索引

- `references/eight-domain-model.md` — 八域主线模型与路由判据
- `references/four-pool-maturity.md` — 四池成熟度：池定义、晋级门槛三档、拒绝话术、候选清单
- `references/grounding-discipline.md` — 问答 grounding 纪律：九条可靠性规则、三态标注、事实纪律六律
- `references/inspection-checklist.md` — 三级巡检清单（周/双周/月）与严重度分档
- `references/archive-protocol.md` — 归档协议：替代关系、只追加日志、回滚路径、快照
- `references/metrics-methodology.md` — 价值度量：核心指标口径、健康分维度、趋势判断
- `references/capacity-map-bootstrap.md` — 冷启动能力地图三步法（工作地图→技能地图→融合）
- `references/environment-setup.md` — 环境前置准备：装工具/建库/最小闭环，四宿主（Obsidian/IMA/LLM Wiki/乐享）上手路径与就绪检查清单
- `references/hosts/obsidian-host.md` — Obsidian 宿主特例（MOC/双链/标签/四阶段文件夹）
- `references/hosts/ima-host.md` — IMA 宿主特例（平台护栏/接口分页/派生路径）
- `references/hosts/llm-wiki-host.md` — LLM Wiki 宿主特例（raw+sidecar/实体页概念页/交叉引用）
- `references/hosts/lexiang-host.md` — 乐享宿主特例（企业平台护栏/智能表格/四池落位/索引落地）
- `references/demo-vault/` — 内置示例库（小型客户运营知识库，四池 7 条目 + 99-meta 2 条目 + 根级 MOC，共 10 个条目文件，已治理干净）：无用户库时的演示素材，主理人降级演示与脚本实测专用，只读；附 `run-monthly-checkup.sh` 一键体检脚本

## scripts 索引（确定性计算，零三方依赖，数字以脚本输出为准）

- `scripts/health_score_calc.py` — 健康分闭式计算
- `scripts/promotion_gate_check.py` — 晋级门槛元数据预检
- `scripts/duplicate_detect.py` — 重复/高度相近条目检测
- `scripts/link_integrity_scan.py` — 死链与孤儿条目扫描

## templates 索引

- `templates/moc-index-template.md` — MOC 总索引/主题索引
- `templates/maturity-review-report.md` — 晋级评审报告
- `templates/inspection-report.md` — 巡检报告
- `templates/archive-log-template.md` — 归档日志（只追加）
- `templates/qa-grounding-template.md` — 带引用的问答产出

## 横切纪律（全成员共用）

1. 确认权在用户：一切写操作先列清单、确认后执行。
2. 只归档不删除：日志只追加，附回滚路径。
3. 机械层脚本、判断层人工：可确定性计算项必须走 scripts/ 产出数字，成员不得口算替代；脚本结论是输入，最终判断由成员+用户做出。
