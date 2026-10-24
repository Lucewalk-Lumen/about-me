# Lucewalk Lumen · 沐光行客

> **Brand hub** for the open expert packages by [沐光行客](https://github.com/Lucewalk-Lumen) — an OBHRM academic, university lecturer and journal peer reviewer. They run on the [WorkBuddy](https://www.workbuddy.cn) AI assistant platform.
>
> Grounded knowledge · compliance-first engineering · one product, one repository
>
> 📌 This is the **full product catalog**. The profile page ([Lucewalk-Lumen](https://github.com/Lucewalk-Lumen/Lucewalk-Lumen)) is a short intro that links here — product details live only on this page.

![Lucewalk Experts — repository banner](docs/social-preview.png)

## About me

I'm **沐光行客** — an OBHRM academic at a Guangdong university, a peer reviewer for management journals, and the lecturer behind a generative-AI literacy course. The expert packages on this page are the toolkit I built for my own research, teaching and HR practice, then published as open packages; they run on the WorkBuddy AI assistant platform.

Every product here is shaped by three disciplines I bring from my daily work:

- **From peer review — the grounding discipline.** I review manuscripts for a living, so my agents are built to answer the way a reviewer reads: every scale points to its source publication, every theory entry carries its literature trail, and when evidence is missing the agent says *so* instead of improvising. Several packages ship with dedicated citation-integrity and de-AI-flavor rules.
- **From engineering — the compliance discipline.** Packages go through a sensitive-info and ownership precheck before publication; the ones that touch personal data ship with `PRIVACY.md`, encrypted PII handling and desensitized archives; operations are reversible by design; and every package has exactly one version source of truth.
- **From teaching — the workflow discipline.** Each expert is modeled on a real course, research project or consulting engagement, then iterated across semesters of actual use until it earns its own repository. Sixteen of them made it to the platform.

## The three product lines

### 🔬 Research line — knowledge that shows its sources

| Product | What makes it different |
|---|---|
| [obhrm-brain-trust](https://github.com/Lucewalk-Lumen/obhrm-brain-trust) | A theory & scale knowledge base with **grounded, citation-first answers** — fuzzy word-form matching that still respects exact provenance, explicit "not covered by source" labels, maturity-gated entries (idea → draft → official → archive), and coverage tracking across 130+ theory entries and curated scales (from Hawthorne studies to the burnout three-dimensional model). |
| [academic-literature-analysis-team](https://github.com/Lucewalk-Lumen/academic-literature-analysis-team) | Bibliometric analysis over your own library — from raw exports to a **review skeleton** you can actually write against. |
| [mplus-stats-coach](https://github.com/Lucewalk-Lumen/mplus-stats-coach) | Statistics coaching for Mplus — syntax guidance, modeling decisions and output interpretation, tuned for students who need to defend their choices. |
| [endnote-analysis](https://github.com/Lucewalk-Lumen/endnote-analysis) | Turns an EndNote library into citation-structure and research-profile insights — built on the author's own daily literature-management workflow. |

> **obhrm-research-collaboration-team** (closed-source · WorkBuddy Expert Center only)
> The full OBHRM research pipeline, run by **seven agents** across the whole lifecycle: topic modeling → literature review → paper writing → grant proposals → data analysis → journal selection & submission → revision / response to reviewers (with EndNote/Zotero library import throughout). Built on a private grounded asset library (closed-source, not publicly browsable) and a security baseline: no hardcoded keys, least-privilege, input-bounds checks, operation audit. Not open-source; install it from the WorkBuddy Expert Center.

### 🎓 Teaching line — built on real classrooms, semester after semester

| Product | What makes it different |
|---|---|
| [teaching-helper-team](https://github.com/Lucewalk-Lumen/teaching-helper-team) | The deepest teaching pack — **nine experts and 18 skills** covering course architecture, case writing, material extraction, knowledge wikis, plus built-in citation-integrity and de-AI-flavor rules for classroom deliverables. |
| [course-tutor](https://github.com/Lucewalk-Lumen/course-tutor) | Course companion for teachers (v2.4.0, full build source): roster import, learning analytics, participation scoring, weekly teaching briefings — nine Python modules and a data-hub config you can audit and extend. Ships with a student-edition build pipeline. |
| [campus-ppt-helper](https://github.com/Lucewalk-Lumen/campus-ppt-helper) | A six-member team for teaching and academic slide decks — from outline to speaker-ready pages. |
| [erp-teaching-team](https://github.com/Lucewalk-Lumen/erp-teaching-team) | Seven experts for ERP courses — course design, cases and lab setups grounded in real enterprise processes. |
| [college-competition-coaching-team](https://github.com/Lucewalk-Lumen/college-competition-coaching-team) | Competition coaching for student teams — planning, mentoring and stage-gate review. |

### 🧭 Practice & tooling line — consulting discipline and the factory that builds the ecosystem

| Product | What makes it different |
|---|---|
| [hrm-advisory-corps](https://github.com/Lucewalk-Lumen/hrm-advisory-corps) | China-market HRM consulting — one orchestrator plus eight specialists across org planning, recruiting pipeline, talent development, performance, compensation and **labor compliance**. Handles candidate PII the compliant way: desensitized archives, encrypted PII vault, plaintext never touching ordinary files. |
| [workbuddy-expert-studio](https://github.com/Lucewalk-Lumen/workbuddy-expert-studio) | **The factory behind this whole catalog** — a team that takes an expert idea through alignment, drafting, quality gates and packaging until it is publishable. Every product listed on this page was produced with it. |
| [kb-library-team](https://github.com/Lucewalk-Lumen/kb-library-team) | Knowledge-base governance — one chief knowledge officer with six internalized domains (ingest, classify, promote, index, grounded Q&A, archive), four-pool maturity gates and hard ingestion guardrails (≤50 files per batch). |
| [ai-butler](https://github.com/Lucewalk-Lumen/ai-butler) | Teacher workbench (offline-first): todos, schedule, teaching calendar with `.ics` import, morning/weekly briefings — single-file HTML plus a local bridge, your data never leaves the machine; optional end-to-end encrypted sync. |
| [distill](https://github.com/Lucewalk-Lumen/distill) | Condense long material into structured, citable summaries — reading time in, reference-ready out. |
| [ghost-workspace-hunter](https://github.com/Lucewalk-Lumen/ghost-workspace-hunter) | Skill — reversible cleanup of corrupted WorkBuddy workspaces: database backup first, active-session guard, trash instead of delete. |
| [fde-frontline-team](https://github.com/Lucewalk-Lumen/fde-frontline-team) | FDE frontline deployment — scenario diagnostics, loop redesign and workshop mentoring for frontline delivery loops. |
| [touyan-expert-team](https://github.com/Lucewalk-Lumen/touyan-expert-team) | Investment-research expert team — multi-role pipeline over A-share & US market data, company deep-dives and backtesting; informational, not financial advice. |



## How to use (any product)

These are **expert packages / skills for the WorkBuddy AI assistant**. The quick path:

1. **Get the package** — download the zip from the product's **Releases** page, or clone its repo. Keep the internal manifest intact (`.codebuddy-plugin/`; `ai-butler` uses an `agent-card.json` UMAS manifest).
2. **Import / enable** — in WorkBuddy, open *custom connector → trust & enable* (or import the expert / enable the skill from the skill center).
3. **Start small** — run one minimal example (see each product's README) to confirm the output matches your standards before scaling up.

**Prerequisites:** WorkBuddy installed and signed in (latest version recommended, for the built-in quality gates & connectors). Some products need your own materials ready first (a literature library, a course outline, etc.) — the agent works under a "stay faithful to the source, cite the page" rule.


**Platform portability** — These packages are delivered for the WorkBuddy AI assistant and won't run as-is on another platform. But every repository documents its methodology, prompts and structure in plain text, so the approach can be re-implemented on another agent framework if you migrate. The knowledge (scales, theories, workflows) is portable even if the runtime isn't.

**Need help?** Open an issue on the product's own repository, or start a [Discussion](https://github.com/Lucewalk-Lumen/about-me/discussions).

## Quality & security

- Every package passed a sensitive-info & ownership precheck before publication — see [docs/PRECHECK.md](docs/PRECHECK.md);
- Version source of truth: the `version` field in each package's `.codebuddy-plugin/plugin.json`;
- Cross-package version alignment history: [CHANGELOG.md](CHANGELOG.md);
- Found a problem? Open an issue on the product's own repository, or start a [Discussion](https://github.com/Lucewalk-Lumen/about-me/discussions).

## Citation

If any of these expert packs or skills are useful in your research or teaching, please cite the repository — see [CITATION.cff](CITATION.cff).

## License

MIT — see [LICENSE](LICENSE). Third-party assets are documented in each product's `SOURCES.md` / `references/`.

---

<details>
<summary><strong>📖 中文说明(Chinese README)</strong></summary>

# Lucewalk Lumen

**Lucewalk Lumen(沐光行客)**——沐光而行,以光为伴——是我为 WorkBuddy AI 助手平台打造的专家团、专家与技能合集的品牌门户。

## 品牌逻辑

- **Grounded knowledge(有据可依)**——审稿人职业习惯的产品化:量表指向来源、理论链接文献、缺失证据标注缺失;
- **Compliance-first engineering(合规优先)**——发布前敏感信息预检、PRIVACY/SECURITY 文档、可逆操作、每包单一版本真源;
- **One product, one repository(一产品一仓库)**——每个产品独立成仓,拥有自己的文档、Issue 与发布周期。

## 产品目录(三条产品线)

### 🔬 研究线(OB & HRM)
- [obhrm-brain-trust](https://github.com/Lucewalk-Lumen/obhrm-brain-trust):12 章教材 × 145 理论 × 601 量表 × 108 R 方法的四库溯源问答
- [academic-literature-analysis-team](https://github.com/Lucewalk-Lumen/academic-literature-analysis-team):学术文献计量分析,从题录到综述骨架
- [mplus-stats-coach](https://github.com/Lucewalk-Lumen/mplus-stats-coach):语法实验室、方法顾问与输出门诊三环辅导
- [endnote-analysis](https://github.com/Lucewalk-Lumen/endnote-analysis):EndNote 引用结构与综述骨架

### 🎓 教学线
- [teaching-helper-team](https://github.com/Lucewalk-Lumen/teaching-helper-team):九专家十八技能,三层架构,六大预设工作流
- [course-tutor](https://github.com/Lucewalk-Lumen/course-tutor):课程伴学精灵·教师版(含完整源码与学生版构建线)
- [campus-ppt-helper](https://github.com/Lucewalk-Lumen/campus-ppt-helper):六成员流水线的教学课件制作
- [erp-teaching-team](https://github.com/Lucewalk-Lumen/erp-teaching-team):五教练覆盖选型、概念、练习、进度全周期
- [college-competition-coaching-team](https://github.com/Lucewalk-Lumen/college-competition-coaching-team):大学生赛事教练团

### 🧭 实践与工具线
- [hrm-advisory-corps](https://github.com/Lucewalk-Lumen/hrm-advisory-corps):一主理人八专家的 HRM 实战咨询,PII 加密处理
- [workbuddy-expert-studio](https://github.com/Lucewalk-Lumen/workbuddy-expert-studio):本合集所有产品的诞生地
- [ai-butler](https://github.com/Lucewalk-Lumen/ai-butler):教师工作台(离线优先)
- [distill](https://github.com/Lucewalk-Lumen/distill):蒸馏师——长文进、可引用摘要出
- [ghost-workspace-hunter](https://github.com/Lucewalk-Lumen/ghost-workspace-hunter):幽灵工作空间猎手(技能)
- [fde-frontline-team](https://github.com/Lucewalk-Lumen/fde-frontline-team):FDE 前线部署团——场景诊断、闭环重设计与工作坊辅导
- [touyan-expert-team](https://github.com/Lucewalk-Lumen/touyan-expert-team):投研星图团——多角色投研流水线(A股/美股数据、公司深研、回测),内容仅供信息参考非投资建议

> **obhrm-research-collaboration-team**（闭源 · 仅经 WorkBuddy 专家中心分发）
> OBHRM 全流程研究流水线,由**七位智能体**覆盖研究全生命周期:选题建模 → 文献综述 → 论文写作 → 基金申报 → 数据分析 → 选刊投稿 → 返修回应(全程支持 EndNote/Zotero 题录导入)。内置私有溯源资产库(闭源,不公开可浏览)——与安全基线:无硬编码密钥、最小权限、输入越界校验、操作审计。不开源,请从 WorkBuddy 专家中心安装。

## 如何使用(任一产品)

这些都是 **WorkBuddy AI 助理** 平台的专家包 / 技能。快速上手:

1. **取包** —— 从产品仓库的 Releases 页下载 zip(或克隆仓库),保持内部清单结构不变(`.codebuddy-plugin/`)；
2. **导入 / 启用** —— 在 WorkBuddy 中「自定义连接器 → 信任并启用」,或在技能中心导入专家 / 启用技能；
3. **先小后大** —— 先跑一个最小示例(见各产品 README),确认输出符合你的口径再规模化使用。

**前置条件:** 已安装并登录 WorkBuddy(建议最新版,以兼容内置质量门禁与连接器)。部分产品需要你先准备好自己的资料(文献库、课程大纲等),专家包在「忠于源文本、标注出处」约束下工作。


**平台可移植性** —— 这些包目前以 WorkBuddy AI 助理格式交付,换到其他平台无法直接运行。但每个仓库都以纯文本记录了方法、提示词与结构,迁移时可作为参考设计在另一套智能体框架上重建。知识(量表、理论、工作流)可移植,运行时不可移植。

**需要帮助?** 在各产品仓库提 `Issues`,或发起 [Discussion](https://github.com/Lucewalk-Lumen/about-me/discussions)。

## 许可

MIT——详见 [LICENSE](LICENSE)。

</details>
