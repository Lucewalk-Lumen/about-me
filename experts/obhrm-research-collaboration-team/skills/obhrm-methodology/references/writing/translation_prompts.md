# 论文翻译规范（中英互译 · APA/SSCI 学术语体）

> 场景触发：用户要求「中转英 / 英转中 / 翻译论文段落 / 保留公式翻译 / 中英双语成稿」。
> 目标语体：国际管理学期刊（AMJ / JAP / JOB / HRMJ 等）与应用心理学期刊（JPSP / PO / JOM 等）学术写作——正式、克制、客观、术语精准。
> 核心原则：**翻译是单任务**，不做润色、缩写、去 AI 味的混合操作；一次只解决一个翻译任务。中英双向并重，双向均须满足本节硬标准。

---

## 一、任务拆分与场景匹配

| 场景 | 用哪个 | 关键约束 |
|------|--------|---------|
| 中文草稿 → 英文论文/摘要 | 中转英（§四 1） | 纯文本输出，避免 Markdown 转义干扰；满足 §二 全部硬标准 |
| 英文稿 → 中文论文/摘要 | 英转中（§四 2） | 还原学术语体，不口语化；术语回查 `bilingual_terms.json` |
| 中英双语成稿（综述/审稿报告） | 双语对照（§四 3） | 先中后英分页；两版术语与数据完全一致，不逐条混杂 |
| 保留公式/变量/统计量翻译 | 任意 + §二.4 | 公式、变量、p 值、CI、β、df 等原样保留，仅翻译 surrounding 文字 |

---

## 二、学术翻译硬标准（中英双向强制适用）

### 2.1 术语一致性管控
- **单一真源**：OBHRM 核心术语译法以 `../../../literature-review/knowledge/bilingual_terms.json` 为准（如 `构念→construct`、`建言→voice`、`边界条件→boundary condition`）；同一概念全文同一译法，禁止近义词漂移（如 construct / concept 混用）。
- **流派敏感术语须标注**：`研究缺口→research gap`、`理论贡献→theoretical contribution（亦可 theoretical implication，按目标期刊惯例）` 等 `note` 字段标注项，译文须与用户目标期刊惯例一致；不确定时保留一字注解（如 "theoretical contribution (implication)"），不擅自二选一。
- **易错词红线**（来自术语表 `note`）：
  - `建言 / 安全建言 / 建言与反馈` → `voice / safety voice / voice and feedback`，**绝不译作"声音 / 安全声音 / 声音与反馈"**。
  - `构念(construct)` ≠ `概念(concept)`，区分使用。
  - `调节效应(moderating effect)` / `调节变量(moderator)` / `中介机制(mediating mechanism)` / `链式中介(chain mediation)` 不得混淆。

### 2.2 时态与语态（英文稿）
- **研究背景/既有文献**：一般现在时或现在完成时（"Prior work *shows*…" / "Studies *have examined*…"）。
- **本文动作（本研究做）**：一般过去时（"We *collected* data…" / "We *found*…"）；方法部分全程过去时。
- **普遍结论/图表陈述**：一般现在时（"Figure 1 *shows*…"）。
- **语态**：方法、结果优先被动（"Data *were analyzed*…"）；引言、讨论可主动以保清晰。避免通篇被动导致的冗长。
- **英转中**：英文时态不直译为"了/过"，按中文叙事习惯处理，但"本文曾做"与"普遍事实"的界限须保留。

### 2.3 客观克制语调（去夸张）
- 探索性发现**禁止** "groundbreaking / pioneering / fill a major gap"；改用 "an understudied boundary / a neglected mechanism / prior work has examined X, yet Z remains unexplored"。
- 断言强度匹配证据等级：相关≠因果，横断≠机制。
- 中文稿同样避免"具有重要的理论和实践意义"等空泛句；改为具体贡献陈述。

### 2.4 公式 / 数据 / 引用保真
- 公式、变量名、方法名、量表名原样保留（如 `SEM`、`CFA`、`MLR`、`Job Crafting Questionnaire`）。
- 统计量原样：`β = .32, p < .05, 95% CI [.18, .46], df = 214`；小数点用点号，千位不空格（英文惯例）。
- 引用保留 `(Author, Year)` 形态；中文稿可用"（作者，年份）"；参考文献格式按 APA 7th（见 `./apa7_guide.md`）。
- 年份、样本量、N、M、SD 原样，绝不"顺手取整"或换算。

### 2.5 句式与衔接
- 英文避免中式英语（Chinglish）结构：见 §三 陷阱清单。
- 长句拆分：中文多短句并列，英译时按主从逻辑重组，不以逗号硬连；英转中时把英文嵌套从句拆为符合中文学术节奏的短句。
- 衔接词精准：因果（therefore / thus / 因此）、转折（however / 然而）、递进（furthermore / 此外）、对比（in contrast / 与之相反）不混用。

---

## 三、中式英语（Chinglish）高频陷阱清单

| 中文原意 | 错误译法（避免） | 学术正确译法 |
|---------|----------------|-------------|
| 具有重要的意义 | has important significance | is of theoretical/practical importance（或具体到贡献） |
| 起到了积极作用 | played a positive role | was positively associated with / enhanced |
| 越来越多的研究 | more and more studies | a growing body of research |
| 随着…的发展 | with the development of… | as X has advanced / driven by X |
| 据我们所知 | as far as we know | to our knowledge |
| 本文研究了 | this paper studies | this study examines / we investigated |
| 取得了进展 | made progress | advanced the literature on |
| 在很大程度上 | in a large degree | to a large extent |
| 引起了广泛关注 | aroused wide attention | has attracted considerable scholarly attention |
| 导致 | lead to（滥用） | predicted / elicited / resulted in（按机制选词） |
| 相关关系 | correlation relationship | association（或 correlation，二选一不叠用） |
| 基于以上分析 | based on above analysis | building on this analysis |

> 英转中反向陷阱：勿把 "we" 一律译"我们"带情绪；勿把被动句硬加"被"字（"数据被收集"→"本研究收集数据"更自然）；勿直译 "the present study" 为"目前的研究"（应为"本研究"）。

---

## 四、可直接使用的模板（中英双向）

### 4.1 中转英（学术语体 · Word/纯文本）
```
你是学术写作编辑，精通 APA/SSCI 管理学期刊写作规范。
请将以下中文草稿译为英文论文章节。
硬性要求（逐条满足）：
1. 纯文本输出，不使用 Markdown 标记。
2. 术语以 bilingual_terms.json 为单一真源，同一概念全文一致；流派敏感术语按目标期刊惯例。
3. 时态：背景/文献用现在时或现在完成时，本文动作与方法用过去时，图表陈述用现在时。
4. 保留所有公式、变量、统计量（β/p/CI/df 原样）、引用 (Author, Year) 与年份/样本量。
5. 客观克制：禁止 groundbreaking/fill a major gap 等夸张语；断言强度匹配证据。
6. 规避第三节中式英语陷阱清单。
输出：Part 1 [English] / Part 2 [中文直译对照] / Part 3 [术语与译法说明]
输入：[中文草稿]
```

### 4.2 英转中（学术语体 · Word/纯文本）
```
你是中文学术论文编辑，精通组织行为/人力资源管理领域术语。
请将以下英文草稿译为中文论文章节。
硬性要求：
1. 还原学术语体，不口语化、不添加"被"字冗余被动。
2. 术语回查 bilingual_terms.json（construct→构念、voice→建言、boundary condition→边界条件）；易错词按红线。
3. 引用转为（作者，年份）；统计量原样（β = .32, p < .05）。
4. 英文嵌套从句拆为符合中文学术节奏的短句，保留"本文动作"与"普遍事实"界限。
5. 不新增观点/数据/引用；不擅自把 exploratory 表述译为确定性结论。
输出：Part 1 [中文] / Part 2 [英文回照] / Part 3 [译法说明]
输入：[英文草稿]
```

### 4.3 中英双语成稿（先中后英分页）
```
你是中英双语学术编辑。就同一主题产出完整中文版 + 完整英文版，先后排列、分页，不逐条混杂。
要求：
1. 两版术语映射一致（以 bilingual_terms.json 为准），数据/统计量/引用完全一致。
2. 中文版符合中文学术规范；英文版满足 §二 全部硬标准与 §三 陷阱规避。
3. 过渡语参考 bilingual-paradigms.md 第三节；英文版断言强度匹配证据。
输出：Part 1 [中文全文] / Part 2 [English Full Text] / Part 3 [术语对照表]
输入：[主题/草稿]
```

---

## 五、译后强制自检表（翻译完成后必查，中英双向）

- [ ] 中译直译与原文逐句对照，确认无改意、无遗漏、无新增结论/数据/引用；
- [ ] 术语全文一致，且符合 `bilingual_terms.json`；易错词（voice/construct/moderator）无红线违例；
- [ ] 数据、年份、样本量、统计量（β/p/CI/df）原样保留，未取整或换算；
- [ ] 公式与数学符号未被破坏；变量/方法/量表名原样；
- [ ] 英文稿时态正确（背景现在/本文过去/图表现在），语态不过度被动；
- [ ] 无 §三 中式英语陷阱；无 groundbreaking/fill a major gap 等夸张语；
- [ ] 引用形态统一 (Author, Year) / （作者，年份），APA 7th 合规；
- [ ] 未引入"具有重要的理论和实践意义"类空泛句；
- [ ] 双语成稿两版数据/术语完全一致，无逐条混杂。
```
