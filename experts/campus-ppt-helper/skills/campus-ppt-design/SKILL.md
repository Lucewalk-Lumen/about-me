---
name: campus-ppt-design
description: "Structure & layout-planning playbook for the Campus PPT Helper Team's content architect. Consult it for page-type contract, content condensation, layout library, layout rotation, per-page role/rhythm/visual_role/anti_pattern and template layout-pool inventory — for teaching / thesis-defense / internship / Party-building decks (教学/答辩/实习/党建党政). Triggers on: 结构, 大纲, 目录, 标题, 叙事, 页型, 页型契约, 封面, 目录页, 章节页, 内容凝练, 凝练, 字数限制, 版式, 排版, 版式轮换, 每页不同版式, 视觉节奏, 视觉锚点, 非对称, 卡片横排, 页面清单, layout, role, rhythm, anti_pattern."
---

# 校园演示帮手团 · 结构与版式规划（Campus PPT Design）

本 Skill 是「校园演示帮手团」**设计师**的专业包。目标只有一个：**先定页型与字数上限、再定逐页版式与节奏**——未定页型就写文案，会让封面/目录/章节页失去页型；未定版式就排内容，是给错误结构化妆。

## 使用原则

| 原则 | 说明 |
|------|------|
| **页型先于文案** | 每页先定页型（封面/目录/章节过渡/正文/结尾）**再**写文案；**索引页不承载内容**——封面只放主讲人与联系方式、目录只放条目、章节过渡页只放章节号与标题 |
| **字数上限不是下限** | 内容凝练：压成一句主张、支撑点封顶、同质去重、长句拆成结论句；正文页扩充保留、索引页扩充撤销 |
| **版式每页可不同** | 11 种版式库（5 对称 + 6 非对称），**非对称 ≥40%**、相邻不重复、`N卡片横排` ≤2 页等七条轮换规则 |
| **版式与内容必须匹配** | 禁"想用某版式就硬凑内容"；`anti_pattern` 逐页必填具体禁止项，写空话视为未做 |
| **路径 B 版式池硬约束** | 模板版式族实测 1–14 种、平均 7.6 种；种数不足时换模板 / 改路径 A / 明示会重复三选一，**不许沉默重复** |

## 参考索引（先读后用，禁止凭记忆编造）

| 文件 | 何时查阅 |
|------|----------|
| `references/page-content-contract.md` | **页面内容类型契约（页型门）**：七类页型的「允许内容 / 禁止内容 / 字数上限 / 必填元信息」；封面必填主讲人 + 联系方式；**索引页不承载内容**；缺陷台账 D1–D6；`check_content_scope.py` 断言表 |
| `references/content-condensation-standard.md` | **内容凝练标准**：移植外部技能 `ai-writing` 1.0.1 业务流 C 的「动笔前必确认风格与字数」确认门 → 课件版五步法；凝练四条操作定义；与"内容太少"的关系 |
| `references/layout-selection.md` | **版式选择（规划侧）**：11 种版式库、七条版式轮换规则、版式与内容匹配 + `anti_pattern` 逐页必填、页面角色与叙事节奏（role/rhythm/visual_role）、视觉锚点 L1/L2/L3、路径 B 版式族清点和三选一、15 套版式族实测表（附录 A） |

## 与其它 Skill 的衔接

页面清单的 `配图`/`案例` 需求交 `campus-ppt-media`；页内排版（A/B/C 三区）与视觉门禁见 `campus-ppt-make` 的 `visual-execution.md`；字号层级见 `campus-ppt-make` 的 `body-typography-standard.md`；口径基线以 `campus-ppt-core` 为准。
