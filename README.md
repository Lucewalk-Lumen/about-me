# WorkBuddy Experts

> **Brand hub** — expert teams, agents and skills built for the [WorkBuddy](https://www.workbuddy.cn) AI assistant platform, maintained by [Xing Bu](https://github.com/Lucewalk).
>
> OB & HRM research · teaching assistants · productivity tools

![WorkBuddy Experts — repository banner](docs/social-preview.png)

## About me

I'm **Xing Bu** — an OB & HRM academic at Guangdong University of Finance & Economics, building expert teams, agents and skills on the WorkBuddy platform. My focus spans knowledge-base governance, academic literature analysis, scale & theory knowledge bases, and AI teaching assistants — 16+ experts published on the WorkBuddy Expert Center, with the open-source collection cataloged here.

Each product lives in **its own repository** for focused documentation, issues and releases. This repository is the catalog and entry point.

## Why separate repositories?

These experts and skills solve very different problems and each has real depth — a single combined repo could not do any of them justice. One product, one repository: focused docs, its own issue tracker, its own release cycle.

## Product catalog

### Expert teams & agents

| Product | What it does | Version |
|---|---|---|
| [hrm-advisory-corps](https://github.com/Lucewalk/hrm-advisory-corps) | China-market HRM team — one orchestrator plus eight specialists (org, recruiting, C&B, compliance) | 1.0.1 |
| [teaching-helper-team](https://github.com/Lucewalk/teaching-helper-team) | Nine teaching experts and 18 skills covering course building, case writing and assessment | 1.1.2 |
| [obhrm-brain-trust](https://github.com/Lucewalk/obhrm-brain-trust) | OBHRM Brain Trust — theory & scale knowledge base with grounded retrieval | 1.0.3 |
| [obhrm-research-collaboration-team](https://github.com/Lucewalk/WorkBuddy-Experts#closed-source) | OBHRM Research Collaboration Team | 1.0.1 — **closed-source**, distributed via the WorkBuddy Expert Center only |
| [workbuddy-expert-studio](https://github.com/Lucewalk/workbuddy-expert-studio) | Turn an expert idea into a publishable package, step by step | 1.0.2 |
| [kb-library-team](https://github.com/Lucewalk/kb-library-team) | A chief knowledge officer with six internalized domains — turns scattered files into a query-ready knowledge base | 1.0.5 |
| [fde-frontline-team](https://github.com/Lucewalk/fde-frontline-team) | FDE (Frontline Deployment) team — scenario diagnostics, coaching and workshop mentoring | 1.0.0 |
| [touyan-expert-team](https://github.com/Lucewalk/touyan-expert-team) | Investment-research expert team — multi-role analysis pipeline | 1.0.0 |
| [college-competition-coaching-team](https://github.com/Lucewalk/college-competition-coaching-team) | Coaching team for college student competitions — mentoring, planning and review | 1.0.0 |
| [academic-literature-analysis-team](https://github.com/Lucewalk/academic-literature-analysis-team) | Academic literature analysis for bibliometrics and review workflows | 1.0.1 |
| [erp-teaching-team](https://github.com/Lucewalk/erp-teaching-team) | ERP teaching team — course, case and lab design for ERP courses | 1.0.0 |
| [endnote-analysis-expert](https://github.com/Lucewalk/endnote-analysis) | EndNote library analysis — bibliometric and citation-structure insights | 0.3.1 |

### Agents & skills

| Product | What it does | Version |
|---|---|---|
| [course-tutor](https://github.com/Lucewalk/course-tutor) | Course companion agent (teacher edition) with full build source — roster, analytics, weekly reports | 2.4.0 |
| [ai-butler](https://github.com/Lucewalk/ai-butler) | Teacher workbench — teaching, meetings, research and admin in one screen (offline-first) | 1.1.4 |
| [distill](https://github.com/Lucewalk/distill) | Condense long material into structured, citable summaries | 1.0.3 |
| [mplus-stats-coach](https://github.com/Lucewalk/mplus-stats-coach) | Guided Mplus syntax, modeling decisions and output reading | 1.0.0 |
| [campus-ppt-helper](https://github.com/Lucewalk/campus-ppt-helper) | Slide building for teaching and academic settings | 1.0.3 |
| [ghost-workspace-hunter](https://github.com/Lucewalk/ghost-workspace-hunter) | Skill — purge stubborn timestamp-named "ghost workspaces" (reversible, with DB backup) | 1.0.0 |

## Install (any product)

1. Download the package zip from the product's **Releases** page (or clone its repo);
2. Unzip keeping the internal manifest structure intact (`.codebuddy-plugin/`; `ai-butler` uses an `agent-card.json` UMAS manifest);
3. Import/register in WorkBuddy (custom connector → trust & enable).

## Quality & security

- Every package passed a sensitive-info & ownership precheck before publication — see [docs/PRECHECK.md](docs/PRECHECK.md);
- Version source of truth: the `version` field in each package's `.codebuddy-plugin/plugin.json`;
- Cross-package version alignment history: [CHANGELOG.md](CHANGELOG.md);
- Found a problem? Open an issue on the product's own repository, or start a [Discussion](https://github.com/Lucewalk/lucewalk-experts/discussions).

## Citation

If any of these expert packs or skills are useful in your research or teaching, please cite the repository — see [CITATION.cff](CITATION.cff).

## License

MIT — see [LICENSE](LICENSE). Third-party assets are documented in each product's `SOURCES.md` / `references/`.
