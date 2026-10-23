---
name: campus-ppt-media
description: "Media & case standard shared across the Campus PPT Helper Team (collector / architect / maker / qa). Consult it for image / chart / table sourcing tiers, placement, provenance, and real-traceable case structure — for teaching / thesis-defense / internship / Party-building decks (教学/答辩/实习/党建党政). Triggers on: 配图, 插图, 图片, 图像, 图表, 表格, 数据来源, 图注, 署名, 落位, slide_add_image, slide_add_chart, 案例, 实例, 五要素, 出处, 可溯源, AI生成图."
---

# 校园演示帮手团 · 媒体与案例标准（Campus PPT Media）

本 Skill 是「校园演示帮手团」**采集员 / 设计师 / 制作员 / 质检员四角色共享**的媒体包。目标只有一个：**图与案例只讲真的**——配图优先真实来源、案例只允许可溯源真实案例，缺失标「待补充」，绝不编造。

## 使用原则

| 原则 | 说明 |
|------|------|
| **图像来源分级 P1–P5** | 用户提供 > 官方公开 > 模板自带 > 授权图库 > AI 生成兜底（P5 须标注「AI 生成·非实拍」） |
| **图文匹配 + 落位规范** | 等比缩放、安全边距、避让模板页层装饰；每页图数 ≤ 2，数据类必须配图表 |
| **案例五要素 + 出处硬要求** | 背景/冲突/做法/结果/启示；只允许 L1–L3 可溯源真实案例，**无 AI 生成兜底档** |
| **采不到标「待补充」** | 图像或案例缺失时如实标注，绝不自行填充或虚构主体 |

## 参考索引（先读后用，禁止凭记忆编造）

| 文件 | 何时查阅 |
|------|----------|
| `references/media-standard.md` | **配图、图表与表格**：图像来源分级 P1–P5（真实来源优先、AI 生成须标注）、图文匹配、图注/署名、落位规范（避让页层装饰）、`slide_add_image` 契约（**不支持远程 URL**）、`slide_add_chart` / `slide_add_table` 一族工具清单 |
| `references/case-standard.md` | **案例标准**：五要素结构模板、整页案例 vs 内嵌框选择规则、数量与篇幅、**出处硬要求**（只允许可溯源真实案例，缺失标「待补充」）、四场景差异、页面清单 `案例` 列填写规则（§八） |

## 与其它 Skill 的衔接

素材来源与出处由 `campus-ppt-collect` 采回；页面清单的 `配图`/`案例` 两列由 `campus-ppt-design` 标定；落位与工具调用由 `campus-ppt-make` 执行；来源核查由 `campus-ppt-qa` 验收。
