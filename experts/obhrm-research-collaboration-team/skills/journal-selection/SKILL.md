---
name: journal-selection
version: 1.0.1
author: "Xing Bu"
description: OBHRM 研究协作团 — 选刊助手域（J 路径）。基于本地期刊库（28,241 刊 / 149,117 条评级 / 13 套标准体系）做稿件→候选刊的匹配与 13 项评级画像，纯标准库零外部依赖。
---
> **跨技能引用约定**：本文档以逻辑名形式引用兄弟技能（如 `` `skill:peer-review` ``），不使用逻辑名映射表，重命名或移动技能时按相对路径同步更新。
# 选刊助手（J 域 · 路由器）
> 本文件是套件内「选刊助手」的入口与路由。底层引擎为 `skills/obhrm-methodology/scripts/query.py` + `skills/journal-library/db/journals.db`（28,241 刊 / 149,117 条评级 / 13 套标准体系），纯标准库、零运行时外部依赖。当任意输入命中「选刊 / 投稿 / 期刊推荐 / 分区查询 / 影响因子 / 中科院分区 / JCR / ABS / ABDC / FMS / CSSCI / 北大核心 / CSCD / EI / FT50 / UTD24 / 经管期刊」等意图时，由调度者切入本域。
>
> **与套件其他路径的衔接**：须在**写作/审稿成稿之后**使用——典型触发点是 A6 投稿（论文写完要选刊）、C 审稿后（按适配度反查目标刊）。选刊不替代审稿，只做「稿件→候选刊」的匹配与评级画像。
---

## 一、双模式工作流

收到查询后先判模式：

- **[目标] 精确模式**：含 `--issn` 或明确刊名（如 "Academy of Management Journal"）→ 输出该刊 13 项评级全画像。
- **[检索] 粗略模式**：含「推荐 / 选刊 / 投稿 / 投哪个 / 有什么期刊」或仅领域词/关键词 → 同类期刊排行 + 百度投稿经验补充。

## 二、调用（须在 workspace 根目录运行）

```bash
cd <workspace 根>
PY=${JOURNAL_PYTHON:-python3}

# 精确：刊名 / ISSN
$PY skills/obhrm-methodology/scripts/query.py "Academy of Management Journal" --json --limit 1
$PY skills/obhrm-methodology/scripts/query.py --issn 0001-4273 --json

# 粗略：关键词 + facet 过滤
$PY skills/obhrm-methodology/scripts/query.py "leadership" --subfield 组织行为 --cas 1 --json --limit 10
$PY skills/obhrm-methodology/scripts/query.py --subfield 人力资源管理 --tier abs4 --cas 1 --json --limit 10
```

facet 旗标：`--area` / `--subfield` / `--tier`(ft50|utd24|abs4|fms_t1) / `--cas`(1–4) / `--jcr`(Q1–Q4) / `--pku` / `--cscd`(core|ext) / `--ei` / `--lang` / `--country`；`--similar <id>` 取同学科候选刊；`--limit N` 控制条数。

## 三、评级标准（13 项）

中科院 2025（大类 1–4 + Top + OA + 2023→2025 升降级）· JCR 2025（JIF/Quartile/JCI/被引）· ABS 2024 · ABDC 2025 · FMS 2025 全球版 · FMS 2025 中文版 · CSSCI 2025-2026 来源 · CSSCI 2025-2026 扩展 · FT50 · UTD24 · 北大核心 2023 · CSCD 2026 · EI 2026。

## 四、输出规范（铁律）

- 未收录标准写「未收录」，不隐藏；ABS/ABDC 须附体系说明；emoji 不省略。
- 粗略模式对 TOP 3 期刊各调一次 WebSearch（`"{刊名} 投稿经验 审稿周期 接收率"`），结果 ≤3 行且标注「[检索] 来源: 百度搜索」；超时/失败降级为本地推荐，不阻断。
- **禁止编造**：无公开经验数据时说「暂无公开投稿经验数据」。

## 五、降级与排障

唯一数据源 `skills/journal-library/db/journals.db` 缺失/损坏时，输出降级提示而非裸错误（话术见 `skills/obhrm-methodology/scripts/query.py` 的 degrade 分支）。

## 跨域联动

- **A6 → J 选刊匹配**（论文进入投稿阶段）→ `skill:paper-writing`。
- **C → J 反向适配**（审稿后按适配度反查候选刊）→ `skill:peer-review`。
- **J → C 反向适配**（候选刊对方法/报告格式有特殊要求）→ `skill:peer-review`，按刊微调稿件。
- **L → J 综述投稿**（综述成稿后选刊）→ `skill:literature-review`。
- **数据来源**：`skills/journal-library/db/journals.db`（28,241 刊 / 149,117 评级 / 13 套标准体系），只读真源。
- **13 标准**（覆盖官方体系）：中科院 2025、JCR 2025、ABS 2024、ABDC 2025、FMS 2025（全球/中文双版）、CSSCI 2025-2026 来源、CSSCI 2025-2026 扩展、FT50、UTD24、北大核心 2023、CSCD 2026、EI 2026。
- **降级与排障**：唯一数据源 `skills/journal-library/db/journals.db` 缺失/损坏时，输出降级提示而非裸错误（话术见 `skills/obhrm-methodology/scripts/query.py` 的 degrade 分支）。
- **方法层**：`skills/obhrm-methodology/references/publishing/journal_submission_guide.md`（投稿规范）、`skills/obhrm-methodology/references/publishing/field_journal_catalog.md`（领域期刊清单）。
- **需登录的期刊/文献检索（browser-skill）**→ `skill:browser-skill`：驱动已登录浏览器抓取期刊官网/数据库的登录后可见页面（最新卷期、APC、投稿指南、文献全文），与 `skill:literature-review` 的检索回环互补。

## 协作交接

本路径产出的可交接对象与字段级规格见 `skills/obhrm-methodology/references/templates/handoff-protocol.md`：

- **A6→J 投稿选刊**（论文进入投稿阶段）：交接块字段见链路八的 A6→J 块（含稿件摘要/要点、目标层级、学科与子领域、约束）。
- **C→J 反向适配**（审稿后按适配度反查候选刊）：交接块字段见链路八的 A6→J 块，目标层级与约束字段按审稿意见填写。
- **J→C 反向适配**（候选刊对方法/报告格式有特殊要求）：交接块字段见链路八的 J→C 块（含候选刊清单、投稿经验、适配提示、待决）。审稿路径消费方式：以 选刊路径适配提示为输入之一，独立形成八维诊断或返修建议；选刊路径不替代审稿，只做匹配。
- **J→蒸馏**（选刊过程中浮现可复用教训，如「某子领域投稿 X 刊命中率更高」）：交接块字段见链路六；判层后落点 `skills/obhrm-methodology/references/governance/method_accumulation.md`（方法论层）或对应 reference（操作层）。

## 七、数据版本与免责

数据版本 2025-2026（第 5 版数据）：中科院 2025 完整版 + JCR 2025 双骨干，全学科覆盖；OBHRM 及管理相邻子领域密度最高。分区每年更新，以各官方平台最新数据为准。百度补充经验仅供参考，不代表官方意见。

> 期刊库规模：**28,241 刊 / 149,117 条评级 / 13 套标准体系**（CAS2025、JCR2025、ABS2024、ABDC2025、CSSCI2025、CSCD2026、EI2026、PKU2023、FMS2025、FT50、UTD24 等），全表 ISSN / 刊名已归一化。只读真源：`skills/journal-library/db/journals.db`（查询见 `skills/obhrm-methodology/scripts/query.py`）。

## 按刊退稿点

投稿前加载目标刊退稿点清单：`references/per_venue_rejection_points.md`，作为投稿前置门控之一（与 stage gate 并行）。
