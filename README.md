# WorkBuddy Experts

![WorkBuddy Experts — repository banner](docs/social-preview.png)

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

