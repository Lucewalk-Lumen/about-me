# ERP Teaching Team

> **Built for teaching ERP, not for consulting.** Seven specialists teach the same concept at four different levels, set exercises with explicit rubrics, tell you exactly where the learner is stuck, and decide what to study next.

## Language

This package is **bilingual**. Expert card fields (name, description, tags, prompts) ship in both Chinese and English and follow your interface language. **Answers follow the language of your question** — ask in Chinese, get Chinese throughout; ask in English, get English throughout. Course material is written in Chinese, with English terms given on first use.

## Type

Team-type expert (7 members) | Category: `12-IndustryConsultant`

## What makes this a teaching team, not a consulting team

| | Consulting team | **This teaching team** |
|---|---|---|
| Roles | People who do the work | **People who teach** |
| Output | Reports, proposals, plans | **Explanations, analogies, exercises, feedback** |
| Key question | Who should handle this? | **Where is this learner stuck, and how should I explain it?** |
| Knowledge base | Reference manuals | **Textbook + workbook + answer key** |
| Success metric | Did the project meet its targets? | **Can the learner explain it back and make the call themselves?** |

## Members

| Member | Owns | Coverage |
|---|---|---|
| **Chief Instructor** | Lesson design, path planning | Assesses learner level and picks the right coach |
| **Concept Coach** | Concept teaching | Ch.01 panorama, Ch.02 diagnosis method |
| **Domain Coach** | Seven business domains | Ch.07-10 procurement / sales / supply chain / finance / HR / inventory / production |
| **Selection Coach** | Evaluation and arithmetic | Ch.03 investment case, Ch.04 selection |
| **AI & Adoption Coach** | AI and organization | Ch.01 AI readiness, Ch.05 AI integration, Ch.06 adoption, Ch.11 ecosystem |
| **Exercise Coach** | Setting and marking | All chapters + Ch.12 question bank |
| **Progress Coach** | Progress tracking | Path planning, bottleneck diagnosis, assessment schedule |

## Layered teaching (the core mechanism)

**Same concept, four teaching moves. Getting the level wrong is the most expensive waste in teaching.**

| Layer | Approach | Example |
|---|---|---|
| **L1** No background | **Picture before words**, always an analogy | "Breakpoint" → "food left on the counter without telling the cook" |
| **L2** Has IT background | Enter from the system view, trace the data flow | "Master data" → "the data other records reference" |
| **L3** Business specialist | Open with their own pain point | "Is your team still raising POs in Excel…" |
| **L4** Senior practitioner | Go straight to method, provoke debate | "Here is a counter-thesis. Refute it." |

## Four teaching modes

| Mode | Output |
|---|---|
| **Lesson prep** | Lesson plan (objectives / sequence / focus / exercises / answer key) → `templates/lesson-plan.md` |
| **Self-study** | Layered explanation + Q&A + exercise marking |
| **Interactive** | Socratic questioning → wait for the answer → judge → discuss |
| **Assessment** | Exam questions + rubrics + progress record |

## Ten teaching rules

1. **Judge the level first, then decide the depth**
2. **Never just hand over the answer** (in interactive mode, guide with questions)
3. **Every lesson ends with an exercise** — unverified equals untaught
4. **Use the learner's language** — business people hear business language
5. **Analogies must be accurate** — a wrong analogy is worse than none
6. **Say "I'm not sure" when unsure** — tax rates and standards must be verified live
7. **Never invent data**
8. **Every concept gets a "remember this one thing"**
9. **Progress must be visible**
10. **Don't rush progress; understanding first**

**Forbidden phrases**: "this is simple", "obviously", "got it?", "you've passed this before".

> These are the **10 teaching rules**. The package also carries three more sets: 15 knowledge-base rules, 8 technical rules, and 7 routing rules.

## Marking structure

```
1. Score      — the score + which criterion it maps to
2. What's right  — name the specific correct reasoning first
3. What's wrong   — pinpoint the exact step
4. How to fix it  — give the corrected answer
```

**A marking pass that gives only a score is no marking at all.**

## Bottleneck diagnosis

| Bottleneck | What it sounds like | Remedy |
|---|---|---|
| Concept not understood | "I don't know what this is about" | Change the analogy, reteach from the ground up |
| Method not understood | Concept clear, can't apply it | Give steps, walk through one example |
| Not enough practice | Same error on a new question type | Add volume, switch question types |
| No transfer | Can do this, not that | Re-apply to a different scenario |
| Doesn't want to learn | Going through the motions | Tie it to their actual work |

**Three questions to locate it**: ask for a definition (concept) / ask for an application (method) / give a variant (transfer).

## Knowledge base (15 chapters)

**Main chain**: 01 Agentic ERP and the 2026 landscape → 02 Diagnosis method → 04 Selection → 03 Investment case → 05 AI integration → 06 Adoption

**Business domains**: 07 Procurement & Sales / 08 Supply Chain & Inventory / 09 Finance & Internal Control / 10 HR, Materials & Production

**Teaching tools**: 11 Vendor ecosystem / 12 21-day bootcamp + 40-question self-test / 13 Red-team drills / **14 Live verification of time-sensitive content** / 15 Consolidation into practice

> The teaching methodology is a **separate skill** (`skills/erp-teaching-method/`) and is **not counted among the 15 chapters**.

**Two living mechanisms**:
- **14 — live verification**: even a textbook must not hard-code stale standards or tax rates
- **15 — consolidation**: notes nobody practices are notes nobody learned

## Bundled assets

| Asset | Path | Purpose |
|---|---|---|
| Teaching methodology | `skills/erp-teaching-method/` | Layering, explanation structure, marking rubric, bottleneck diagnosis, forbidden phrases |
| ERP knowledge base | `skills/erp-knowledge-base/` | 15 chapters |
| AI integration assets | `skills/erp-ai-integration/` | Integration architecture, tool-function spec, RAG chunking, private deployment |
| Asset routing | `skills/erp-asset-routing/` | Ecosystem package boundaries |
| Pain diagnosis | `skills/erp-pain-diagnosis/` | Per-domain breakpoint checklists |
| Lesson plan template | `templates/lesson-plan.md` | Includes a complete worked example |
| Progress ledger | `templates/progress-ledger.md` | Mastery tracking, assessment schedule |
| Selection matrix | `templates/selection-matrix.md` | Requirements, comparison, five-year TCO, roadmap |
| Acceptance checklist | `templates/acceptance-checklist.md` | Baseline, 30/60/90-day review |
| Pitfalls | `references/pitfalls.md` | Teaching scenarios (not real failure cases) |
| Tech stack | `references/tech-stack.md` | Reference stack for L2+ learners |

## Directory structure

```
erp-teaching-team/
├── README.md / README.en.md
├── CHANGELOG.md · LICENSE · settings.json
├── .codebuddy-plugin/plugin.json   # version source of truth
├── agents/                         # 7 roles (1 lead + 6 coaches)
├── skills/                         # 5 skills
├── templates/                      # 4 templates
├── references/                     # 2 reference lists
└── avatars/                        # 8 avatars
```

## Install and uninstall

**Install**: search "ERP 教学团 / ERP Teaching Team" in the WorkBuddy plugin market. Then find it under 【Expert Center → My Experts】.

**Manual install**: place the package directory under the plugin market directory. **The directory name must match the `name` field in `plugin.json`** (`erp-teaching-team`).

**Uninstall**: remove it from 【Expert Center → My Experts】, or delete the package directory.

## Version and license

- **Version**: 1.0.0 (source of truth: `version` in `.codebuddy-plugin/plugin.json`)
- **Changelog**: [`CHANGELOG.md`](./CHANGELOG.md)
- **License**: MIT — [`LICENSE`](./LICENSE)

## FAQ

**Will it do my tax filing or accounting judgment for me?**
No. See "Content boundaries" below; such requests are routed to a specialist package.

**Can I study just one business domain?**
Yes. Tell the coach which domain. You don't have to walk the full 21-day path.

**Can I use its numbers (ratios, tax rates, costs) directly?**
No. All teaching reference values must be verified against official sources — see Ch.14 `skills/erp-knowledge-base/14-时效内容实时核验.md`.

**Will it answer in English if I ask in English?**
Yes. Answers follow the language of your question.

## Content boundaries

This team does **not** provide: tax filing computation, accounting treatment judgment, labor-law conclusions, legal advice, live system operation, or cross-border multi-jurisdiction compliance. Time-sensitive content must be verified live; standards and tax rates are never hard-coded.

## Bilingual term glossary

| Chinese | English |
|---|---|
| 教学团 | ERP Teaching Team |
| 主讲人 / 课程主教习 | Chief Instructor |
| 概念教练 | Concept Coach |
| 业务域教练 | Domain Coach |
| 选型与论证教练 | Selection Coach |
| AI 与落地教练 | AI & Adoption Coach |
| 练习与评卷教练 | Exercise Coach |
| 进度与路径教练 | Progress Coach |
| 流程断点 | Process Breakpoint |
| 真痛 / 不习惯 | Real Pain / Unfamiliarity |
| 主数据 | Master Data |
| 总拥有成本 | Total Cost of Ownership (TCO) |
| 采购到付款 / 订单到收款 | Procure-to-Pay (P2P) / Order-to-Cash (O2C) |
| 记录到报告 | Record-to-Report (R2R) |
| 销售与运营计划 | Sales & Operations Planning (S&OP) |
| 可承诺量 | Available to Promise (ATP) |
| 物料清单 | Bill of Materials (BOM) |
| 企业资源计划 | Enterprise Resource Planning (ERP) |
| 制造执行系统 | Manufacturing Execution System (MES) |
| 职责分离 | Separation of Duties (SoD) |
| 检索增强生成 | Retrieval-Augmented Generation (RAG) |