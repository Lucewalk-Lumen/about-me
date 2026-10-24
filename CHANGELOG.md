# Cross-package Changelog

> **Version source of truth**: the `version` field in each package's `.codebuddy-plugin/plugin.json`.
> Detailed per-package history lives in each package's own `CHANGELOG.md`.

## 2026-10-24 · kb-library-team structure fix

- Restored the missing `.codebuddy-plugin/plugin.json` (the source zip was shipped incomplete);
- Briefly restructured to a single agent, then **reverted to team structure (7 agents)** after author confirmation — v1.0.5 is team-type;
- Author metadata normalized to `Xing Bu <the author's verified email>`.

## 2026-10-24 · Alignment with the published expert list

- HRM line corrected: removed `hrm-solution-team` 1.1.2; the current package is **`hrm-advisory-corps` (HRM Advisory Corps) v1.0.1** (under review on the platform);
- Added `fde-frontline-team` (FDE Frontline Deployment Team) v1.0.0, `distill` v1.0.3 and `ai-butler` (Teacher Workbench) v1.1.4 (UMAS card format);
- `course-tutor` 2.4.0 confirmed as **full source** (all `course_*.py` scripts, `data_hub_config.json` and the student variant included);
- `kb-library-team` (KB Library Team, team-type) moved from `skills/` to **`experts/`** — 17 published experts / 1 skill in total.

## 2026-10-24 · Closed-source & ownership cleanup

- `obhrm-research-collaboration-team` moved to **closed-source distribution**: directory removed from the public repo, index entry retained, distributed via the WorkBuddy Expert Center only;
- Removed per author decision (non-owned or unneeded): `course-companion`, `enterprise-docs-organizer`, `obsidian-knowledge-governance-team`, `system-setup-team`, `wiki-kb-team`, `workbuddy-universal-mentor`, `brand-knowledge-base`, `kb-organizer`, `personal-knowledge-architect`, `llm-wiki`;
- Authorship normalized to `Xing Bu`: `mplus-stats-coach`, `distill`;
- `course-tutor` upgraded 2.3.1 → **2.4.0** (desktop release).

## 2026-10-23 · Initial baseline

| Package | Baseline | Form | Notes |
|---|---|---|---|
| teaching-helper-team | 1.1.2 | source | zip was stale (1.1.1), source is authoritative |
| obhrm-research-collaboration-team | 1.0.1 | source + zip | version 1.0.0 had been reused; this one is canonical |
| obhrm-brain-trust | 1.0.3 | zip + source | see rename history in README |
| hrm-solution-team | 1.1.2 | source + zip | later replaced by hrm-advisory-corps |
| workbuddy-expert-studio | 1.0.2 | zip | local manifest dir was stale (1.0.0) |
| course-companion | 2.4.0 | zip | desktop copy newer than the drive copy |
| course-tutor | 2.3.1 | zip + src | later upgraded to 2.4.0 |
| others | 1.0.x / 0.3.1 | see README | — |

## Conventions

1. Version numbers only increase and are never reused; the `version` field is the single source of truth;
2. Renamed packages keep one release note "(formerly ...)", then the old name is dropped;
3. Every cross-package release attaches a precheck record in `docs/`.

## 2026-10-24 · Brand & architecture

- The collection split into **per-product repositories** (16 experts + 1 skill), each with an in-depth English README and a collapsible Chinese section;
- This hub was renamed **lucewalk-lumen** (Lumen: the luminous measure — light walked into work) and rebuilt as the brand catalog: three product lines (Research / Teaching / Practice & Tooling);
- Brand narrative formalized: grounded knowledge, compliance-first engineering, one product one repository;
- The old combined release was retired; per-product releases now carry the packages.
