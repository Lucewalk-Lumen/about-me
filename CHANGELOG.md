# 跨包版本对齐表(CHANGELOG)

> 每个包的详细变更见各包内 `CHANGELOG.md`。本表记录**入库基准**与跨包发布事件。

## 2026-10-23 · 建仓基准

| 包 | 入库基准版本 | 来源形态 | 备注 |
|---|---|---|---|
| teaching-helper-team | 1.1.2 | 源码 | zip 落后(仅 1.1.1),以源码为准 |
| obhrm-research-collaboration-team | 1.0.1 | 源码+zip | 1.0.0 版本号曾被复用,以此版为准 |
| obhrm-brain-trust | 1.0.3 | zip+源码 | 曾用名见 README 历史说明 |
| hrm-solution-team | 1.1.2 | 源码+zip | — |
| workbuddy-expert-studio | 1.0.2 | zip | 本地主目录为 1.0.0,以 1.0.2 为准 |
| obsidian-knowledge-governance-team | 2.0.0 | 源码 | — |
| workbuddy-universal-mentor | 1.2.1 | 源码 | 入库前清理 README 第三方路径 |
| course-companion | 2.4.0 | zip | 桌面版新于移动硬盘版 |
| course-tutor | 2.3.1 | zip+src | — |
| 其余 | 1.0.x/0.3.1 | 见总表 | — |

## 约定

1. 版本号只增不复用;包内 `plugin.json` 的 `version` 为唯一真源;
2. 更名包在旧名后括注「(原 xxx)」保留一个版本的说明,之后不再保留旧名目录;
3. 每次跨包发布在 `docs/` 附当次预检记录。

## 2026-10-24 · 归属清理与版本修正

- 移除 10 个非本人署名/不需要的包(experts 6 + skills 4),依据 `plugin.json` 的 author 字段判定;
- mplus-stats-coach 署名统一为 `Xing Bu`(原为 "Xing");
- course-tutor 升级 2.3.1 → **2.4.0**(桌面交付版);
- obhrm-research-collaboration-team 对齐交付版 **1.0.1**(仓库曾误用 1.0.0 源码)。

## 2026-10-24 · 对齐线上专家列表

- HRM 线更正:移除 hrm-solution-team 1.1.2,现役为 **hrm-advisory-corps(HRM 实战参谋团)v1.0.1**(线上审核中版);
- 新增 fde-frontline-team(FDE 前线部署团)v1.0.0、distill(蒸馏师·甄澄)v1.0.3、ai-butler(教师工作台·启明星)v1.1.4(UMAS 通用卡片格式);
- course-tutor 2.4.0 确认为源码形态(已含全部 course_*.py 与 data_hub_config.json)。

## 2026-10-24 · 闭源与归属清理

- obhrm-research-collaboration-team 改为**闭源分发**(目录移出公开仓,索引保留,仅经 WorkBuddy 专家中心获取);
- 移除 3 个非本人署名的技能(ima-kb-ops-team / obsidian-mind-vault / schedule-planner,署名为工具默认值)。
