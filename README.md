# WorkBuddy Experts

A collection of **expert teams, agents and skills** built for the [WorkBuddy](https://www.workbuddy.cn) AI assistant platform — OB & HRM research packs, teaching assistants, and productivity tools. Maintained by **Xing Bu** (Guangdong University of Finance & Economics). Each package is independently versioned; grab individual packages from the [Releases](https://github.com/Lucewalk/WorkBuddy-Experts/releases/latest) page.

## Repository Layout

```
├── experts/        # Expert teams & agents (manifests in .codebuddy-plugin/)
├── skills/         # Skills (SKILL.md format)
├── docs/           # Release notes & quality records
├── LICENSE         # MIT
└── CHANGELOG.md    # Cross-package version alignment
```

## Package Index

### Experts (experts/)

| Package | Title | Type | Version |
|---|---|---|---|
| teaching-helper-team | Teaching Helper Team | team | 1.1.2 |
| obhrm-research-collaboration-team | OBHRM Research Collaboration Team | team | 1.0.1 *(closed-source, distributed via WorkBuddy Expert Center)* |
| obhrm-brain-trust | OBHRM Brain Trust | team | 1.0.3 |
| hrm-advisory-corps | HRM Advisory Corps | team | 1.0.1 |
| workbuddy-expert-studio | WorkBuddy Expert Studio | team | 1.0.2 |
| fde-frontline-team | FDE Frontline Deployment Team | team | 1.0.0 |
| course-tutor | Course Companion (Dandelion) | agent | 2.4.0 *(full source)* |
| campus-ppt-helper | Campus PPT Helper | agent | 1.0.3 |
| touyan-expert-team | Touyan Expert Team | team | 1.0.0 |
| mplus-stats-coach | Mplus Stats Coach | agent | 1.0.0 |
| college-competition-coaching-team | College Competition Coaching Team | team | 1.0.0 |
| erp-teaching-team | ERP Teaching Team | team | 1.0.0 |
| academic-literature-analysis-team | Academic Literature Analysis Team | team | 1.0.1 |
| ai-butler | Teacher Workbench | agent | 1.1.4 *(UMAS card format)* |
| distill | Distill | agent | 1.0.3 |
| kb-library-team | KB Library Team | team | 1.0.5 |
| endnote-analysis-expert | EndNote Literature Analysis | agent | 0.3.1 |

### Skills (skills/)

- **ghost-workspace-hunter** — purges stubborn timestamp-named "ghost workspaces" from WorkBuddy (reversible, with DB backup, guards active sessions)

## Downloading a Single Package

1. **Release assets (recommended)** — every package ships as `<name>-<version>.zip` on the [Releases](https://github.com/Lucewalk/WorkBuddy-Experts/releases/latest) page;
2. **Single-directory download** — open the package folder (e.g. `experts/hrm-advisory-corps`) and paste its URL into [download-directory.github.io](https://download-directory.github.io);
3. **Sparse checkout** — for multiple packages:

   ```bash
   git clone --depth 1 --filter=blob:none --sparse git@github.com:Lucewalk/WorkBuddy-Experts.git
   cd WorkBuddy-Experts && git sparse-checkout set experts/hrm-advisory-corps skills/ghost-workspace-hunter
   ```

## Installation

1. Download the zip from Releases (or clone the repo);
2. Unzip **keeping the `.codebuddy-plugin/` manifest structure intact** — note: `ai-butler` uses an `agent-card.json` UMAS manifest instead;
3. Import/register in WorkBuddy (custom connector → trust & enable);
4. A quick security review before use is recommended — see `docs/PRECHECK.md` for the author's own audit record.

## Citation

If any of these expert packs or skills are useful in your research or teaching, please cite the repository — see [CITATION.cff](CITATION.cff).

## Security

See [SECURITY.md](.github/SECURITY.md) for reporting guidelines and the package safety commitments.

## License

MIT — see [LICENSE](LICENSE). Third-party assets are documented in each package's `SOURCES.md` / `references/`.

---

<details>
<summary><strong>📖 中文说明(Chinese README)</strong></summary>

# WorkBuddy Experts

WorkBuddy 平台的专家团(Agent Team)、专家(Agent)与技能(Skill)合集,由 Xing Bu 维护。

**版本真源**:每个包以 `.codebuddy-plugin/plugin.json` 的 `version` 字段为准,跨包对齐见 [CHANGELOG.md](CHANGELOG.md)。

## 包索引(experts/)

| 包 | 名称 | 类型 | 基准版本 |
|---|---|---|---|
| teaching-helper-team | 教学帮帮团 | team | 1.1.2 |
| obhrm-research-collaboration-team | OBHRM 研究协作团 | team | 1.0.1(闭源,经 WorkBuddy 专家中心分发) |
| obhrm-brain-trust | OBHRM 智囊团 | team | 1.0.3 |
| hrm-advisory-corps | HRM 实战参谋团 | team | 1.0.1 |
| workbuddy-expert-studio | WorkBuddy 专家开发工坊 | team | 1.0.2 |
| fde-frontline-team | FDE 前线部署团 | team | 1.0.0 |
| course-tutor | 课程伴学精灵(蒲公英) | agent | 2.4.0(完整源码) |
| campus-ppt-helper | 校园演示帮手团 | agent | 1.0.3 |
| touyan-expert-team | 投研星图团 | team | 1.0.0 |
| mplus-stats-coach | Mplus 统计教练 | agent | 1.0.0 |
| college-competition-coaching-team | 大学生赛事教练团 | team | 1.0.0 |
| erp-teaching-team | ERP 教学团 | team | 1.0.0 |
| academic-literature-analysis-team | 文献计量分析团 | team | 1.0.1 |
| ai-butler | 教师工作台(启明星) | agent | 1.1.4(UMAS 卡片格式) |
| distill | 蒸馏师(甄澄) | agent | 1.0.3 |
| kb-library-team | 智博资料室 | team | 1.0.5 |
| endnote-analysis-expert | EndNote 分析专家 | agent | 0.3.1 |

## 技能(skills/)

- **ghost-workspace-hunter**(幽灵工作空间猎手)——猎除 WorkBuddy 中删不掉的时间戳幽灵工作空间(可逆、带数据库备份、保护活跃会话)

## 下载单个包

1. **Release 附件(推荐)**:每个包都有独立附件 `<包名>-<版本>.zip`;
2. **网页子目录下载**:打开包目录页,把地址粘贴到 download-directory.github.io;
3. **sparse-checkout**:见上方英文命令示例。

## 安装方式

1. 从 Releases 下载对应包的 zip(或克隆仓库取目录);
2. 解压后**保持目录名与包内 `.codebuddy-plugin/` 结构不变**(`ai-butler` 为 agent-card.json UMAS 格式);
3. 在 WorkBuddy 中按平台流程导入/注册(自定义连接器入口 → 信任并启用);
4. 建议导入前对包内容做一次安全审计(`docs/PRECHECK.md` 提供作者自检记录)。

## 许可

MIT。第三方素材授权说明见各包 README 或 `references/`。

</details>
