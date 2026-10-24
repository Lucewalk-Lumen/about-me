# WorkBuddy Experts

> **Brand hub** — expert teams, agents and skills built for the [WorkBuddy](https://www.workbuddy.cn) AI assistant platform, maintained by [Xing Bu](https://github.com/Lucewalk).
>
> Grounded knowledge · compliance-first engineering · one product, one repository

![WorkBuddy Experts — repository banner](docs/social-preview.png)

## About me

I'm **Xing Bu** — an OB & HRM academic, a journal peer reviewer, and the author of 16+ expert teams and skills published on the WorkBuddy Expert Center.

My products carry the habits of my two trades:

- **From peer review** — the citation discipline. Answers must be *grounded*: every scale points to its source, every theory entry links to its literature, and missing evidence is labeled as missing rather than invented.
- **From engineering** — the compliance discipline. Sensitive-info prechecks before publication, `PRIVACY.md` and `SECURITY.md` in every serious package, reversible operations, and a single version source of truth per package.
- **From teaching** — the product discipline. Each expert is built around a real classroom or research workflow, then sharpened through iteration until it earns its own repository.

## The three product lines

### 🔬 Research line (OB & HRM)

Theory and scale knowledge bases with grounded retrieval, bibliometric analysis, and statistics coaching.

| Product | Focus |
|---|---|
| [obhrm-brain-trust](https://github.com/Lucewalk/obhrm-brain-trust) | Theory & scale knowledge base — grounded, citation-first answers |
| [academic-literature-analysis-team](https://github.com/Lucewalk/academic-literature-analysis-team) | Bibliometric analysis and review workflows |
| [mplus-stats-coach](https://github.com/Lucewalk/mplus-stats-coach) | Guided Mplus syntax, modeling decisions, output reading |
| [endnote-analysis-expert](https://github.com/Lucewalk/endnote-analysis) | EndNote library analysis — citation structures and insights |

### 🎓 Teaching line

Course building, cases, assessment and classroom operations for higher education.

| Product | Focus |
|---|---|
| [teaching-helper-team](https://github.com/Lucewalk/teaching-helper-team) | Nine experts, 18 skills — course building, cases, assessment |
| [course-tutor](https://github.com/Lucewalk/course-tutor) | Course companion (teacher edition) — roster, analytics, weekly reports |
| [campus-ppt-helper](https://github.com/Lucewalk/campus-ppt-helper) | Slide building for teaching and academic settings |
| [erp-teaching-team](https://github.com/Lucewalk/erp-teaching-team) | Course, case and lab design for ERP courses |
| [college-competition-coaching-team](https://github.com/Lucewalk/college-competition-coaching-team) | Mentoring and review for student competitions |

### 🧭 Practice & tooling line

HRM consulting in the field, plus the tooling that builds and maintains the ecosystem itself.

| Product | Focus |
|---|---|
| [hrm-advisory-corps](https://github.com/Lucewalk/hrm-advisory-corps) | China-market HRM consulting — org, recruiting, C&B, compliance |
| [workbuddy-expert-studio](https://github.com/Lucewalk/workbuddy-expert-studio) | The factory: turn an expert idea into a publishable package |
| [kb-library-team](https://github.com/Lucewalk/kb-library-team) | Knowledge-base governance — six internalized domains, one chief officer |
| [ai-butler](https://github.com/Lucewalk/ai-butler) | Teacher workbench — offline-first personal operations |
| [distill](https://github.com/Lucewalk/distill) | Condense long material into structured, citable summaries |
| [ghost-workspace-hunter](https://github.com/Lucewalk/ghost-workspace-hunter) | Skill — reversible cleanup of corrupted WorkBuddy workspaces |

> The flagship of the research line, **obhrm-research-collaboration-team** (full research pipeline: literature review, paper writing, methods, data), is closed-source and distributed via the WorkBuddy Expert Center only.

## Why separate repositories?

These experts and skills solve very different problems and each has real depth — a single combined repo could not do any of them justice. One product, one repository: focused docs, its own issue tracker, its own release cycle. This repository is the catalog and entry point.

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
