---
name: literature-review
version: 1.0.1
author: "Xing Bu"
description: OBHRM 研究协作团 — 文献综述域（L 路径·路由器）。覆盖选题→收集→阅读分类→方向收敛→论证评估→提纲→综合撰写的七阶段综述成稿流程；含头脑风暴协议、PRISMA 流程图、PDF 资料库总结与中英双语综述。
---
> **跨技能引用约定**：本文档以逻辑名形式引用兄弟技能（如 `` `skill:peer-review` ``），不使用逻辑名映射表，重命名或移动技能时按相对路径同步更新。
## 微技能库（：5 个文献综述微技能）
> 微技能由 `references/micro-skills/` 提供，按综述推进阶段取用，每个微技能可独立触发：
| 微技能 | 阶段 | 作用 | 文件 |
|--------|------|------|------|
| refine-literature-question | 选题 | 宽泛主题压成可检索的研究问题锚（8-10 发散→3 收缩） | `references/micro-skills/refine-literature-question.md` |
| decompose-review-modules | 结构 | 研究问题拆成 3-5 个独立综述模块，检查重叠与漏维度 | `references/micro-skills/decompose-review-modules.md` |
| compare-research-methods | 论证 | 比较各方法能回答/回答不了什么，论证方法选择与混合顺序 | `references/micro-skills/compare-research-methods.md` |
| map-literature-contradictions | 综合 | 拆解文献结论矛盾的分歧来源（梳子法三步） | `references/micro-skills/map-literature-contradictions.md` |
| locate-review-research-gap | 收束 | 研究展望收束成具体可执行 gap（四问校验） | `references/micro-skills/locate-review-research-gap.md` |
| deep-distill | 精读 | 单篇 PDF/在线链接的三层六模块深度蒸馏（M1–M6，M6 衔接 G2 证据映射门），**随本包维护** | `references/micro-skills/deep-distill.md` |
# 文献综述域 — 综述路径（路由器）
> 本文件是套件内「文献综述写作路径」的入口与路由。详尽知识外置于本目录 `knowledge/*.json` 与 `references/*.md`，重活交给 `scripts/*.py`。当任意输入命中「文献综述 / 综述写作 / 综述怎么写 / 综述模板 / 综述范式 / 综述类型 / 选题方向 / PDF 资料库总结 / 中英双语综述 / 综述框架图 / PRISMA 流程图」等意图时，由调度者切入本域。
>
> **与 论文路径的分工**：论文路径负责「完整论文（含引言/方法/结果/讨论）」；本域负责「独立的文献综述成稿（选题→收集→阅读分类→方向收敛→论证评估→提纲→综合撰写）」。若综述只是全文的一个章节，仍走 论文路径，本域仅在用户**单独**要做综述时主导。
---

## 一、七阶段总流程

① 确定选题（宽泛兴趣）→ ② 收集文献 → ③ 阅读与分类（产出 `<输出目录>/READINGS.md`，运行时由 `skills/obhrm-methodology/scripts/build_readings.py` 写入）→【选题方向收敛·门】→ ④ 论证与评估 → ⑤ 拟定提纲 → ⑥ 综合撰写 → ⑦ 成稿自检。

- **阶段门控**：每阶段衔接经三态门控（[绿/通过]/[黄/待优化]/[红/不通过]），AI 获用户确认前先自行通过。规则见 `knowledge/stage_gates.json`（G1–G5）。
- **收敛门（G1+）**：③ 后若用户仍处宽泛主题、未锁定聚焦研究问题，必须先「选题方向收敛」归纳 3–5 方向并选定，方可进入 ④⑤⑥。理论增量（构念重构/机制解密/边界拓展）前置到收敛期。
- **头脑风暴协议（综述专属·硬门）**：写正文前必须先用 `knowledge/brainstorming_protocol.json` 做对话式对齐——一次一问，依次确认综述类型（九类）/学科领域/主题/背景目的/文献基础（含 PDF 目录路径）/输出格式/范式对应的章节结构，汇总后取得用户确认。**未完成对齐禁止输出任何正文段落或创建章节文件**（`hard_gate`）。论文路径的通用 A0 协议（`skills/obhrm-methodology/references/reasoning/thinking_protocols.md`）面向"研究问题+方法设计"，与本协议不可互替，L 路径不得改用。

## 二、四功能维度（各司其职）

| 维度 | 职责 | 作用阶段 |
|------|------|----------|
| 阶段推进 | 定义先后顺序，先读后写、先收敛后展开 | ①–⑥ |
| 质量把关 | 贡献澄清、理论框架自洽、证据充分 | ④ ⑥ |
| 结构对标 | 动机→问题→框架→边界 要素不缺位 | ⑤ ⑥ |
| 安全校验 | 引证完整、不编造、转述保真、客观语调 | ⑥ 后 |

## 三、关键能力指针（详见 knowledge/）

- **范式选择**：九范式 P1–P9（`knowledge/paradigms.json` + `references/paradigms.md`）。
- **理论增量 & 结构完整**：三层次检查 + 五要素，见 `knowledge/journal_standards.json`、`knowledge/amj_elements.json`、`references/hrmr-standards.md`。
- **选题方向收敛**：`knowledge/topic_scoping_prompt.md` + `knowledge/gap_novelty.json`（新颖性 N1–N4 / 五类缺口）。
- **证据-论点映射**：每条文献先建映射再写（Warrant/文献链闭环/综合≥2 要素），见 `knowledge/evidence_claim_map.json`、`knowledge/argumentation_framework.json`。
- **成稿自检（四铁律同源）**：不编引用 / 不归观点 / 标注无支撑 / 不超范围；AI 指纹检测见 `references/ai-fingerprint-guide.md`、`knowledge/closed_loop.json`、`skills/obhrm-methodology/scripts/closed_loop_check.py`。
- **验证铁律**：声称完成必有验证证据；in-text 引用三态标注（已核实DOI / 未获取原文 / 未证实归属），见 `references/verification-protocol.md`、`knowledge/red_flags.json`、`skills/obhrm-methodology/scripts/format_citation_report.py`（CrossRef 结果经 WebFetch 预抓取后传入，离线整理）。
- **中英双语**：模板与术语映射见 `knowledge/templates.json`、`knowledge/bilingual_terms.json`、`references/bilingual-paradigms.md`。
- **PDF 资料库模式**：`skills/obhrm-methodology/scripts/ingest_pdfs.py` + `skills/obhrm-methodology/scripts/build_readings.py --codes`（LRR 阅读密码 SPL/CPL/GAP/RAT/ROF）+ `skills/obhrm-methodology/scripts/select_deepread.py`（阶段③精读候选筛选，支持 `--all` 全量 / `--limit N` 限量 / `--topic` 主题过滤），见 `references/pdf-ingestion.md`。
- **文献调研方法论**：四原型 + Keshav 三遍法 + 防御偏误，见 `knowledge/literature_research_methods.json`、`skills/obhrm-methodology/scripts/format_search_results.py`（检索数据经 WebSearch/WebFetch 获取后做去重/排序/格式化）。

## 三·五、递归追问式检索回环（阶段②↔③ 的循环规则）

> **定位**：本规则把七阶段中「② 收集文献 → ③ 阅读与分类」的单向直线改造为**有界回环**——正文读进去以后必然冒出新线索，这些线索应当回流为下一轮检索词，而不是被丢在阅读笔记里。回环受硬上限约束，不改变 G1+ 收敛门与既有阶段门控（G1–G5）的判定标准。

### 一、回环机制

1. **第 1 轮（种子轮）**：按已确认的选题与范式，用初始检索式完成首轮收集，进入 ③ 阅读与分类。
2. **正文阅读产出下一轮检索词**：读的是**正文**不是摘要——按 Keshav 三遍法的第二、三遍，从以下位置抽取新检索词：
   - 该文献自陈的研究局限与未来研究方向
   - 反复出现但当前检索式未覆盖的构念别名与近义术语（含中英文对照，见 `knowledge/bilingual_terms.json`）
   - 高频被引的上游理论源头与经典文献
   - 与本主题结论相冲突的对立阵营所用术语
   - 情境与方法维度的限定词（行业、样本类型、研究设计类型）
3. **新词去重与筛选**：新检索词先与前轮检索式比对去重；只保留能带来**新增证据**而非同义重复的词，每轮入选**不超过 5 个**，避免检索面无节制膨胀。
4. **补检结果并入证据矩阵**：补检文献按同一纳入排除标准筛选后，与首轮文献**合并进同一份证据矩阵**（见 `knowledge/evidence_claim_map.json`），并在矩阵中标注该条来自第几轮补检。PRISMA 流程图的记录数须同步累加各轮补检的检索数与排除数，不得只报首轮。

### 二、硬上限：3 轮（防跑飞）

- 回环**最多执行 3 轮**（种子轮计为第 1 轮，即最多 2 轮补检）。达到上限即停止扩展，无论是否仍有新线索。
- **提前终止条件**（满足其一即停，不必跑满 3 轮）：新一轮补检所得文献中，能改变已有论点结构的比例低于两成；或新检索词已全部指向既有收录文献。
- **达上限仍有未覆盖线索**：不再扩展检索，而是把剩余线索**如实写入综述的"研究局限与未来方向"**，并注明本综述的检索边界。这是诚实的边界声明，不是缺陷。
- **禁止绕过上限**：不得以"换个说法重启一轮"变相突破 3 轮。轮次以本主题为单位累计计数，跨会话续跑时沿用既有计数，不复位。

### 三、留痕要求

每轮记录：轮次序号、本轮新检索词的来源（出自哪篇文献的哪个位置）、检索式、命中与纳入数量、并入证据矩阵的条目编号。留痕缺失的补检结果不得计入综述的证据基础。

## 四、图表（统一用套件图表引擎）

正式综述配图一律用套件 `skills/obhrm-methodology/scripts/chart_engine.py`（20 种 · APA7 · 渲染依赖 requirements.lock 已声明的 matplotlib/numpy/scipy/seaborn · PDF+PNG），CJK 乱码由 `skills/obhrm-methodology/scripts/render_figures.py` 在子进程注册系统字体解决，不修改引擎本身。调用铁律：先有文本化结构，图只是视觉化，且须执行图表嵌入协议（生成→登记→配 APA 图注≥80字→正文≥1 处显式引用）。详见 `references/diagram-recipes.md`。

## 五、脚本用法（均在 `scripts/`）

- 文献检索两步走（本套件脚本不联网）：① 用系统 WebSearch / WebFetch 获取学术 API 数据（CrossRef / Semantic Scholar / PubMed / arXiv）存为 raw.json；② `format_search_results.py --input raw.json --query "<query>" --year 2020-2026 --limit 20 --format apa` 做去重、排序与格式化
- `ingest_pdfs.py "<文件夹>" [--incremental]`：递归提取 PDF 摘要
- `build_readings.py --codes`：产出带 LRR 阅读密码槽位的 READINGS（写入用户工作目录，非技能包文件）
- `format_citation_report.py "<draft.md>" --crossref crossref.json [--readings READINGS.md] [--out report.md]`：DOI 三态验证（先用 WebFetch 逐个抓取 `https://api.crossref.org/works/<doi>` 存为 crossref.json，再传入本脚本离线生成报告）
- `closed_loop_check.py "<draft.md>" --rules knowledge/closed_loop.json [--readings READINGS.md] [--out report.md]`：成稿自检（含 burstiness/AI 指纹）。**`--rules` 是必填项**，缺省会直接报错退出——G5 门控执行时按此完整写法调用
- `select_deepread.py <READINGS.md> [--all | --limit N] [--topic "<关键词>"]`：阶段③精读候选筛选，从 READINGS 中挑出待深读条目
- `render_figures.py <图表类型> <data.json> --output DIR [--title T]`
- `litreview_docx_export.py <input.md> [--out output.docx]`：Markdown→Word

所有脚本纯标准库、零运行时外部依赖；解释器/字体/样式从套件根 `config.json` 读取。

## 跨域联动

- **A ↔ L 综述协作**（用户要单独综述或先搞定文献综述章节）→ `skill:paper-writing`；综述路径消费方式：以 G1+ 收敛门前置理论增量，先读后写、先收敛后展开；论文路径消费方式：沿用 综述路径的证据-论点映射与可追溯矩阵，不重写已核实引用。
- **L → M 综述成系统综述**（独立成稿但实质是系统综述时）→ `../data-analysis/quantitative/quantitative.md`（第二部分 M1-M5）；元分析路径作为综述路径系统综述子集承接。
- **L → C 写作→审稿**（综述成稿后送审稿）→ `skill:peer-review`。
- **L → 蒸馏**（综述路径中浮现可复用教训，如某范式在某子领域更有效）：交接字段见 `skills/obhrm-methodology/references/templates/handoff-protocol.md` 链路六；判层后落点 `skills/obhrm-methodology/references/governance/method_accumulation.md`（方法论层）或对应 reference（操作层）。
- **图表需求**（综述框架图 / PRISMA 流程图）→ `skills/obhrm-methodology/domains/visualization/visualization.md`，按「图表嵌入协议」入正文；CJK 乱码由 `skills/obhrm-methodology/scripts/render_figures.py` 在子进程注册系统字体解决，不修改引擎本身。
- **方法层与判据**：`knowledge/paradigms.json`（九范式 P1–P9）、`knowledge/journal_standards.json` 与 `knowledge/amj_elements.json`（理论增量三层次+五要素）、`knowledge/topic_scoping_prompt.md` + `knowledge/gap_novelty.json`（选题方向收敛 + 五类缺口）、`knowledge/evidence_claim_map.json` + `knowledge/argumentation_framework.json`（证据-论点映射）、`knowledge/stage_gates.json`（G1–G5 阶段门控）、`knowledge/closed_loop.json`（闭环自检）、`knowledge/quality_scoring.json`（8 维评分）、`knowledge/red_flags.json`（RedFlags 系统）、`knowledge/templates.json`（中英双语模板）、`knowledge/bilingual_terms.json`（术语映射）、`knowledge/literature_research_methods.json`（四原型+Keshav 三遍法+偏误防御）、`skills/obhrm-methodology/references/reasoning/thinking_protocols.md`（写前对齐）、`knowledge/reading_codes.json`（LRR 阅读密码 SPL/CPL/GAP/RAT/ROF）。
- **学术不端与信任线**：本域同样受四铁律（不编引用/不归观点/标注无支撑/不超范围）与 审稿路径 Trust Boundary 互补；`references/verification-protocol.md`（三态标注）+ `skills/obhrm-methodology/scripts/format_citation_report.py`（DOI/格式校验，CrossRef 数据预抓取后传入）。
- **综述专项去AI**：`references/ai-fingerprint-guide.md`（综述禁用表达与学术过渡词节制）；用户要求全文级深度改写时切 `skills/obhrm-methodology/domains/humanize/humanize.md`。
- **PDF 资料库模式**：`skills/obhrm-methodology/scripts/ingest_pdfs.py` + `skills/obhrm-methodology/scripts/build_readings.py --codes` + `references/pdf-ingestion.md`。
- **需登录的文献检索（browser-skill）**→ `skill:browser-skill`：驱动用户已登录 Chromium / Edge 浏览器访问 Google Scholar / Web of Science / 期刊官网，抓取登录后限定的 PDF 与引用；与系统 WebSearch/WebFetch 检索 + `skills/obhrm-methodology/scripts/format_search_results.py`（结果整理）定位互补——登录后限定资源走 browser-skill，开放元数据走平台检索工具。

## 协作交接

本路径产出的可交接对象与字段级规格见 `skills/obhrm-methodology/references/templates/handoff-protocol.md`：

- **A→L 综述主导**（用户要单独综述或先搞定文献综述章节）：交接块字段见链路七的 A→L 块（含研究问题/宽泛主题、已有文献清单、目标形态、边界、关联全文）。
- **L→A 综述回灌**（成稿后回灌论文引言/相关工作）：交接块字段见链路七的 L→A 块（含综述成稿、文献地图、证据-论点映射、三态标注结果、理论增量声明、回灌位置建议）。论文路径消费方式：沿用 综述路径的证据-论点映射与可追溯矩阵，不重写已核实引用；若综述范围窄于全文，明确边界以免过度 generalization。
- **L→M 综述成系统综述**（独立成稿但实质是系统综述时）：交接块字段见链路七的 A→L 块，目标形态标「系统综述」。
- **L→C 写作→审稿**（综述成稿后送审稿）：交接块字段见链路三（含稿件、目标期刊/层级、可追溯矩阵、自检结果、已知薄弱点、产出形态）。
- **L→蒸馏**（综述路径中浮现可复用教训）：交接块字段见链路六；判层后落点 `skills/obhrm-methodology/references/governance/method_accumulation.md`（方法论层）或对应 reference（操作层）。

## 七、质量评分（每阶段末）

8 维度 1–5 分结构化 JSON（选题质量/文献覆盖/理论深度/论证连接/结构完整/写作质量/图表嵌入/创新程度）；文献覆盖/理论深度/论证连接 ≤2 视为 [红/不通过] 门控不通过。标准见 `knowledge/quality_scoring.json`（源自套件 `skills/obhrm-methodology/domains/quality-assurance/`）。

## 八、参考

方法层与判据见上方「跨域联动」段；字段级规格见 `skills/obhrm-methodology/references/templates/handoff-protocol.md`（链路六/七/三）。支撑清单：

- **knowledge/**：`paradigms.json` / `journal_standards.json` / `amj_elements.json` / `topic_scoping_prompt.md` / `gap_novelty.json` / `evidence_claim_map.json` / `argumentation_framework.json` / `stage_gates.json` / `closed_loop.json` / `quality_scoring.json` / `red_flags.json` / `templates.json` / `bilingual_terms.json` / `literature_research_methods.json` / `reading_codes.json` / `_domain_index.json` / `_index.json`
- **references/**：九范式 → `paradigms.md`；HRMR 标准 → `hrmr-standards.md`；PDF → `pdf-ingestion.md`；图表 → `diagram-recipes.md`；双语 → `bilingual-paradigms.md`；闭环 → `closed-loop-editing.md`；Nature → `nature-tips.md`；同行评审 → `peer_review_framework.md`；模板 → `writing-templates.md`；验证 → `verification-protocol.md`；去AI → `ai-fingerprint-guide.md`
- **scripts/**：`format_search_results.py` / `ingest_pdfs.py` / `build_readings.py` / `select_deepread.py` / `format_citation_report.py` / `closed_loop_check.py` / `render_figures.py` / `litreview_docx_export.py`
- **上游域**：`skill:peer-review`（审稿路径）、`skill:journal-selection`（选刊路径）、`skill:paper-writing`（论文路径）、`skills/obhrm-methodology/domains/humanize/humanize.md`（深度去AI）
