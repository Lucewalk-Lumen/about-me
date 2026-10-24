# WorkBuddy Experts Collection

WorkBuddy 平台的专家团(Agent Team)、专家(Agent)与技能(Skill)合集,由 [Xing Bu](mailto: REPLACE_WITH_YOUR_EMAIL) 维护。

> **版本真源**:每个包以 `.codebuddy-plugin/plugin.json` 的 `version` 字段为准,各包 CHANGELOG 记录变更历史。

## 目录结构

```
├── experts/        # 专家团与专家(team / agent 型,含 .codebuddy-plugin/plugin.json)
├── skills/         # 技能包(SKILL.md 形态)
├── docs/           # 发布说明与质量记录
├── LICENSE
└── CHANGELOG.md    # 跨包版本对齐表
```

## 产品线索引

### 专家团 / 专家(experts/)

| 包名 | 名称 | 类型 | 基准版本 |
|---|---|---|---|
| teaching-helper-team | 教学帮帮团 | team | 1.1.2 |
| obhrm-research-collaboration-team | OBHRM 研究协作团 | team | 1.0.1 |
| obhrm-brain-trust | OBHRM 智囊团 | team | 1.0.3 |
| hrm-solution-team | HRM 智能方案团 | team | 1.1.2 |
| workbuddy-expert-studio | WorkBuddy 专家开发工坊 | team | 1.0.2 |
| enterprise-docs-organizer | 企业资料整理专家 | team | 1.0.0 |
| obsidian-knowledge-governance-team | Obsidian 知识库治理专家团 | team | 2.0.0 |
| system-setup-team | 体系搭建专家团 | team | 1.0.1 |
| wiki-kb-team | Wiki 知识库管理团 | team | 1.0.0 |
| workbuddy-universal-mentor | 全能导师 | agent | 1.2.1 |
| course-companion | 耘知(课程伴学专家) | agent | 2.4.0 |
| course-tutor | 蒲公英(课程导师) | agent | 2.3.1 |
| campus-ppt-helper | 校园 PPT 助手 | agent | 1.0.3 |
| touyan-expert-team | 投产专家团 | team | 1.0.0 |
| mplus-stats-coach | Mplus 统计教练 | — | 1.0.0 |
| college-competition-coaching-team | 大创竞赛辅导团 | team | 1.0.0 |
| erp-teaching-team | ERP 教学团 | team | 1.0.0 |
| academic-literature-analysis-team | 文献计量分析团 | team | 1.0.1 |
| endnote-analysis-expert | EndNote 分析专家 | agent | 0.3.1 |

### 技能(skills/)

brand-knowledge-base · ima-kb-ops-team · kb-organizer · llm-wiki · personal-knowledge-architect · obsidian-mind-vault · schedule-planner · kb-library-team(1.0.5)

## 安装方式

1. 从 Release 下载对应包的 zip(或直接克隆本仓库取 `experts/`、`skills/` 下的目录);
2. 解压后**保持目录名与包内 `.codebuddy-plugin/` 结构不变**;
3. 在 WorkBuddy 中按平台流程导入/注册(自定义连接器入口 → 信任并启用);
4. 建议导入前对包内容做一次安全审计(本仓库各包的 `docs/PRECHECK.md` 提供作者自检记录)。

## 历史/更名说明

- `obhrm-knowledge-compass` → `obhrm-research-brain-trust` → `obhrm-hub-team` → **`obhrm-brain-trust`**
- `obhrm-research-think-tank` → **`obhrm-research-collaboration-team`**
- `course-tutor-student` → **`course-companion`**
- `hrm-advisory-corps` 为一次未采用的更名尝试,归档不发布

旧命名安装包不提供,请以本表基准版本为准。

## 许可

MIT License,详见 [LICENSE](LICENSE)。包内第三方素材(图片/最小化 JS)的授权说明见各包 README 或 docs/。
