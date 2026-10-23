---
name: campus-ppt-collect
description: "Collection playbook for the Campus PPT Helper Team's collector. Consult it for browser-skill web crawling, multi-source cross-verified gathering, deep-linked cited materials, source hygiene and pollution isolation — for teaching / thesis-defense / internship / Party-building decks (教学/答辩/实习/党建党政). Triggers on: 采集, 爬虫, 资料, 找素材, browser-skill, bsk, 深链, 原文摘录, 多源交叉, 来源分级, 来源卫生, 污染隔离, 出处, 政策原文, 行业报告, 经营数据, 教务通知, 答辩资料, 课题数据."
---

# 校园演示帮手团 · 采集标准（Campus PPT Collect）

本 Skill 是「校园演示帮手团」**采集员**的专业包——只在**含外部 URL / 明确指定外部来源**时才调度（轻模式用户自带资料不进入本包）。目标只有一个：**采回的资料可溯源、可交叉验证**，绝不"仅简单关键词搜索即交付"。

## 使用原则

| 原则 | 说明 |
|------|------|
| **采集前先预检** | browser-skill 可用性预检是第 0 步，不可用不空转，直接走降级路径 |
| **深链原文，不抄摘要** | 必须进页面、点深链、读动态内容、下载官方文档；只取搜索引擎摘要 = 不合格交付 |
| **多源交叉 + 来源分级** | 关键事实至少 2 个独立来源交叉验证；逐条标注来源级别 L1–L4 |
| **污染隔离** | 与主线无关 / 非权威 / 已过期 / 用户已否决的条目移入「污染隔离区」，不得进入下游结构 |
| **不编造** | 采不到就标「待补充」，绝不臆造数据或出处 |

## 参考索引（先读后用，禁止凭记忆编造）

| 文件 | 何时查阅 |
|------|----------|
| `references/crawler-collection-standard.md` | 采集员爬虫必备标准、禁止"仅简单搜索即交付"、采集产物模板（来源表） |
| `references/browser-skill-integration.md` | **browser-skill 如何真正接入**：可用性预检、`bsk` 会话生命周期与调用契约、人在环、安全红线、不可用时的降级路径 |
| `references/source-hygiene.md` | **来源卫生与污染隔离**：L1–L4 来源分级、相关性闸门、污染隔离区、口径变更时的旧产物隔离 |

## 与其它 Skill 的衔接

采集产物（文字 / 配图 / 案例 / 图表数据的来源与出处）交 `campus-ppt-media` 落实配图与案例标准；结构对接交 `campus-ppt-design`；口径基线以 `campus-ppt-core` 为准。
