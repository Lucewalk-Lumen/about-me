# WorkBuddy Experts

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
| obhrm-research-collaboration-team | OBHRM 研究协作团 | team | 1.0.1(闭源,仅经 WorkBuddy 专家中心分发) |
| obhrm-brain-trust | OBHRM 智囊团 | team | 1.0.3 |
| hrm-advisory-corps | HRM 实战参谋团 | team | 1.0.1 |
| workbuddy-expert-studio | WorkBuddy 专家开发工坊 | team | 1.0.2 |
| course-tutor | 课程伴学精灵(蒲公英) | agent | 2.4.0 |
| campus-ppt-helper | 校园 PPT 助手 | agent | 1.0.3 |
| touyan-expert-team | 投产专家团 | team | 1.0.0 |
| mplus-stats-coach | Mplus 统计教练 | agent | 1.0.0 |
| college-competition-coaching-team | 大创竞赛辅导团 | team | 1.0.0 |
| erp-teaching-team | ERP 教学团 | team | 1.0.0 |
| academic-literature-analysis-team | 文献计量分析团 | team | 1.0.1 |
| fde-frontline-team | FDE 前线部署团 | team | 1.0.0 |
| distill | 蒸馏师(甄澄) | agent | 1.0.3 |
| ai-butler | 教师工作台(启明星) | agent(UMAS) | 1.1.4 |
| endnote-analysis-expert | EndNote 分析专家 | agent | 0.3.1 |

### 技能(skills/)

kb-library-team(1.0.5,智博资料室,team 型) · ghost-workspace-hunter(幽灵工作空间猎手)

## 如何只下载一个智能体 / 技能

1. **Release 附件(推荐)**:进入 [Releases](https://github.com/Lucewalk/WorkBuddy-Experts/releases) 页,每个包都有独立附件 `<包名>-<版本>.zip`(版本号即该包 `plugin.json` 的 `version`),按需下载即可;
2. **网页子目录下载**:打开对应包目录页(如 `experts/hrm-solution-team`),把浏览器地址粘贴到 <https://download-directory.github.io>,即可只下载该子目录;
3. **命令行 sparse-checkout**(需要多个包时):

   ```bash
   git clone --depth 1 --filter=blob:none --sparse git@github.com:Lucewalk/WorkBuddy-Experts.git
   cd WorkBuddy-Experts && git sparse-checkout set experts/hrm-solution-team skills/kb-library-team
   ```

## 安装方式

1. 从 Release 下载对应包的 zip(或直接克隆本仓库取 `experts/`、`skills/` 下的目录);
2. 解压后**保持目录名与包内 `.codebuddy-plugin/` 结构不变**;
3. 在 WorkBuddy 中按平台流程导入/注册(自定义连接器入口 → 信任并启用);注:`ai-butler` 为 UMAS v1.0 通用卡片格式,其余包均为 `.codebuddy-plugin` 清单;
4. 建议导入前对包内容做一次安全审计(本仓库各包的 `docs/PRECHECK.md` 提供作者自检记录)。

## 历史/更名说明

- `obhrm-knowledge-compass` → `obhrm-research-brain-trust` → `obhrm-hub-team` → **`obhrm-brain-trust`**
- `obhrm-research-think-tank` → **`obhrm-research-collaboration-team`**
- `course-tutor-student` → **`course-companion`**
- `knowledge-management-studio` → **`kb-library-team`**(智博资料室)
- `hrm-solution-team` → **`hrm-advisory-corps`**(HRM 实战参谋团,现役)

旧命名安装包不提供,请以本表基准版本为准。

## 许可

MIT License,详见 [LICENSE](LICENSE)。包内第三方素材(图片/最小化 JS)的授权说明见各包 README 或 docs/。
