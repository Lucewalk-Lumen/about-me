---
name: obhrm-methodology
version: 1.0.1
author: "Xing Bu"
description: |
  OBHRM 研究协作团 — 共享方法论与资源基座。提供跨 6 条业务路径与薄路由技能 obhrm-research-base 共享的单一方法论知识库、输出工具链与质量闸门。
  # —— 中文触发词（本研究团共享资源层；超通用词不设触发，防跨域误触发）——
  - 研究方法论
  - 质量闸门
  - 引用规范
  - APA7
  - 修辞动作库
  - 图表引擎
  - 审稿报告模板
  - 论文模板
  - PRISMA
  - 证据链
  - 蒸馏沉淀
  # —— English triggers ——
  - research methodology
  - quality gates
  - citation standard
  - rhetorical moves
  - chart engine
  - review report template
---
> **跨技能引用约定**：本技能以相对路径形式被兄弟技能引用——兄弟技能位于 `skills/&lt;业务&gt;/`（较本文件深一层），如从 `skills/literature-review/knowledge/` 引用本基座为 `` `skills/obhrm-methodology/references/methods/&lt;文档&gt;.md` ``；不使用逻辑名映射表，重命名或移动时按相对路径同步更新。本技能为**资源与工具真源**，不承接任何业务路径的编排职责（编排见 obhrm-research-base）。

# OBHRM 共享方法论与资源基座

> 本技能是协作团的"共享层"：所有业务路径（文献综述 / 论文写作 / 基金申报 / 数据分析 / 同行评审 / 选刊投稿）与薄路由技能 `obhrm-research-base` 共享同一套方法论知识库、输出工具链与质量闸门。它**只提供资产与能力**，不做路由或编排——谁来做、按什么顺序，由 `obhrm-research-base` 与各成员 agent 决定。

## 目录速查表

| 类型 | 名称 | 位置 | 用途 |
|------|------|------|------|
| 资源库 | 方法论知识库 | `references/` | 98 篇共享方法论/治理/写作/评审/推理/出版文档（含 governance、methods、writing、review、reasoning、publishing、ethics、templates 等；3 份路由文档 skill_router / skill_refs / skill_rules 由 obhrm-research-base 持有） |
| 工具链 | 输出脚本 | `scripts/` | 24 个脚本：自研图表引擎 `chart_engine.py`（20 种）、Word/PDF 渲染（`obhrm_docx_formatter.py`、`docx_text.py`、`litreview_docx_export.py`、`generate_review_docx.py`）、引用核查（`format_references.py`、`format_citation_report.py`、`format_search_results.py`）、质量门控（`gate_executors.py`、`quality_check.py`、`closed_loop_check.py`、`writing_lint.py`）、PDF 摄取（`ingest_pdfs.py`、`clean_pdf_text.py`）、交付包（`generate_deliverable_pack.py`）、诊断（`diagnosis_report.py`、`selftest.py`）等 |
| Python 包 | 核心工具包 | `obhrm_research_base/` | 跨脚本共享的 core（safe_path / config_manager / logging_manager / audit_log）+ journal（常量/连接/归一化） |
| 通用域 | 可视化 | `domains/visualization/` | 图表引擎（20 种）入口与配置（`matplotlibrc`） |
| 通用域 | 人文化 | `domains/humanize/` | 风格级去 AI 改写（成稿后置） |
| 通用域 | 质量保障 | `domains/quality-assurance/` | 跨路径通用质量评分 |
| 通用域 | 蒸馏沉淀 | `domains/distillation/` | 跨路径方法论沉淀与可回滚机制 |
| 模板 | 论文模板 | `paper-templates/` | 双语摘要 / 案例 / IMRaD / 综述 / 理论论文 五套模板 |
| 门控 | 质量闸门判据 | `quality_gates.json` | 机器可读判据（交付前 0 violations 放行） |

## 与 obhrm-research-base 的切分

- **obhrm-research-base（薄路由）**：仅保留团队概念入口、路由总控与三份路由文档（`skills/obhrm-research-base/references/skill_router.md`、`skills/obhrm-research-base/references/skill_refs.md`、`skills/obhrm-research-base/references/skill_rules.md` 由 base 持有），以及团队哲学（心智模型/生命周期/自治度档位/运行状态契约）。
- **obhrm-methodology（本技能，共享层）**：持有上述全部"方法论文档 + 工具链 + 通用域 + 模板 + 质量闸门"。

> **引用位置无关性提示（下列相对路径请站在"兄弟业务技能"的视角理解）**：业务路径技能文件位于 `skills/&lt;业务&gt;/&lt;子目录&gt;/`（较本基座深一层），引用本基座资源时统一写成 `skills/obhrm-methodology/references/&lt;子目录&gt;/&lt;文档&gt;.md`（示例：`skills/obhrm-methodology/references/methods/research_question_gap.md`）；因本基座与所有业务技能同为 `skills/` 下兄弟，相对深度恒定，迁移安全。**本基座自身内部**引用请用 `references/...`（相对本技能目录），无需 `../../` 前缀。新增/改名资源请同步更新引用处的相对路径。

## 资源按需加载

`references/` 体量较大（98 篇），请按场景**按需加载**而非全量注入上下文。高频核心文档与触发映射见 `skills/obhrm-research-base/references/skill_refs.md` 的"高频核心文档清单"与"触发映射表"段落（该文档由 base 路由层持有，按相对路径 `skills/obhrm-research-base/references/skill_refs.md` 查找）。

## 质量底线（与 base 一致，跨路径恒定）

四条铁律（不编引用 / 不归观点 / 无支撑必标注 / 报告不超范围）与 `quality_gates.json` 判据由本基座提供，任何业务路径、任何自治度档位下均照常执行，不存在"因为赶时间所以免检"的档位。

## 版本

当前版本：**1.0.1**（与包版本 `plugin.json` 的 `version` 保持一致）。版本策略与历史见 `../../CHANGELOG.md`。
