---
name: data-contract
version: 1.1.1
description: 技能间数据连接契约。定义全团共享的数据总线目录、foundation 基础能力流水线顺序、各技能输入输出接口、命名规范与主理人中转职责，确保基础能力与领域技能之间能够正常通信与调用。
---

# 技能间数据连接契约

本契约是教学帮帮团所有技能之间数据交换的单一事实来源。基础能力（foundation）的产出必须能被领域技能（domain）消费，领域技能的中间产物必须能在阶段间流转，交付物必须可追溯。

## 数据总线目录

所有技能的数据交换统一落在工作空间下的 `data/pipeline/` 三段式目录：

```
data/pipeline/
├── incoming/      # 基础能力产出（素材层）：crawler / material-extractor / content-summary 的原始与结构化素材
├── working/       # 领域技能中间产物（加工层）：各专家阶段产出的草稿、证据表、章节契约等
└── outgoing/      # 交付物（交付层）：经 quality 门禁后的最终成稿
```

> `material-extractor` 的对外交付物（`full_text.txt` / `metadata.json`）与其他基础能力一致，统一发布到 `incoming/`；脚本可用 `BOOK_SKILL_WORKDIR` 指定私有临时工作区，但**下游一律从 `incoming/` 读取**，不得依赖私有工作区路径。

## foundation 流水线顺序（按需截取，非线性必经）

基础能力层有固定上游→下游依赖，由主理人 lead 按用户需求（提示词）**按需选取**：

```
1. crawler（采集原始材料，仅用户未提供现成材料时启用）
   → 2. material-extractor（材料→结构化全文+元数据）
   → 3. content-summary（要点总结）
   → 4. knowledge-wiki（知识入库沉淀）
   → 5. long-manuscript-core（长文整合）
   → domain 专家消费（案例/论文/课程/课件/纪要）
```

用户已提供材料时跳过 1.，直接进入 2. 或 3.。并非所有任务走全流程，按需截取。

> **knowledge-wiki 位置说明**：`knowledge-wiki` 产出 wiki 页面落「wiki 根目录」，**不进入 `data/pipeline/incoming/` 数据总线**；领域专家仅在用户要求参考既往成果 / 本地知识库时，按需经 `knowledge-wiki` 查询综合，而非从 `incoming/` 读取。其为可选能力，无则跳过，不阻塞主流程。

## 命名规范

所有数据文件统一命名：`{task_id}_{stage}_{skill}.{format}`

- `task_id`：主理人在建团时分配的任务编号，如 `t01`
- `stage`：流水线阶段标签，取值 `raw` / `summary` / `scrape` / `draft` / `revise` / `final`
- `skill`：产出该文件的技能名，如 `crawler` / `content-summary` / `thesis-mentor` / `minutes-organizer` / `text-to-speech` / `architect`
- `format`：`md` / `json` / `csv` / `docx` / `png` / `mp3`

示例：`t01_summary_content-summary.md`、`t01_scrape_crawler.json`、`t01_draft_thesis-mentor.md`、`t01_final_minutes-organizer.docx`

## 技能输入输出接口

| 技能 | 层 | 输入 | 输出 | 输出目录 |
|------|----|------|------|---------|
| crawler | foundation | 网页 URL（公开或已登录会话） | 结构化数据 json/csv/md | incoming/ |
| material-extractor | foundation | 用户文档 / incoming/ 素材 | 结构化全文 full_text.txt + 元数据 metadata.json | incoming/ |
| content-summary | foundation | URL/文件/PDF/音视频 | 浓缩摘要 md | incoming/ |
| knowledge-wiki | foundation | incoming/ 任意资料 | wiki 页面 md | wiki 根目录 |
| long-manuscript-core | foundation | 用户材料 + incoming/ 摘要 | 长文草稿/修订 md | working/ |
| deai-rules | quality | working/ 或 outgoing/ 成稿 | 门禁报告 + 修订稿 | 原文件位 |
| citation-integrity | quality | 含引用/数据的成稿 | 引用核验结论 | 原文件位 |
| architect | domain | 用户需求 | 技能包文件（默认命名 `{task_id}_{stage}_architect.{format}`） | `data/pipeline/outgoing/`（用户可另行指定落盘目录） |
| case-writer | domain | incoming/ 政策检索 + 用户素材 | 案例 md | working/→outgoing/ |
| thesis-mentor | domain | incoming/ 摘要 + working/ 草稿 | 论文阶段产物 md | working/ |
| course-builder | domain | incoming/ 资料 + 用户主题 | 框架/大纲/教材/PPT | working/→outgoing/ |
| ppt-maker | domain | 教案/大纲/内容（.md / spec.json / .pptx / .pdf） | 课件 html + dist.html（可选 .pptx 备选） | working/→outgoing/ |
| minutes-organizer | domain | incoming/ 转录稿/OCR + 素材 | 纪要/综述 md+docx | working/→outgoing/ |
| text-to-speech | domain | 文本（讲稿/旁白） | 语音 mp3+srt | outgoing/ |
| edu-grant-writer | domain | 选题方向/级别 + incoming/ 政策/文献 | 申报书草稿 md/docx + 质量检测报告 | working/→outgoing/ |
| textbook-chapter-expansion | domain | 目标 md + 素材库目录 | 补齐后 md + 扩充报告 + 备份文件 | working/→outgoing/ |
| literature-distiller | domain | PDF/URL | 蒸馏报告 md + 元数据 json | working/→outgoing/ |

## 通信与调用规则

1. **主理人中转**：技能间不直接调用。基础能力产出由主理人读取后，以文件路径或内容摘要下发给领域技能；领域技能产出由主理人回收并转交下一阶段。**唯一例外**：课程建设的课件环节（`course-builder` 的 Phase 4）由 `course-builder` 在本技能内以 Skill 工具加载 `ppt-maker` 子技能完成——此为契约允许的「技能内直连」，不属于「技能间直连」；主理人只需在路由层把课件环节判定给 `course-builder`，不向 `ppt-maker` 重复接单。
2. **文件即接口**：技能间通过 `data/pipeline/` 下的文件交换数据，不依赖内存状态。下游技能读取上游技能的输出文件作为输入。
3. **幂等可恢复**：每个阶段产物落盘，任务中断后可从最近 stage 恢复。`working/` 保留中间产物供回溯。
4. **门禁拦截**：`outgoing/` 的文件必须先过 quality 层门禁（`deai-rules` 五维自评 ≥45 且 deai_preflight.py PASS + `citation-integrity` 引用核验清零）才能标记为交付物。
5. **素材溯源**：`incoming/` 文件命名含来源技能，`working/` 文件命名含加工技能，保证任一交付物可回溯到原始素材。

## 与主理人 SOP 的衔接

主理人在 Workflow 各阶段的 Phase 之间，按本契约执行数据流转：

- Phase 1（素材准备）：按需调用 foundation 能力（crawler → material-extractor → content-summary）→ 产出落 `incoming/`
- Phase 2（专家加工）：领域技能读取 `incoming/` → 产出落 `working/`
- Phase 3（门禁交付）：`working/` 成稿过 quality 门禁（deai-rules + citation-integrity）→ 落 `outgoing/` 交付

多专家协作时，主理人负责把上一专家的 `working/` 产物作为下一专家的输入传递，并在 SendMessage 中注明文件路径。

> **ppt-maker 中间契约**：`deck.spec.json` 为 md2spec / extract_pptx / extract_pdf / build_deck / build_pptx / merge_spec 共享的中间格式——`meta{title,course}` + `preset` + `slides[{type,title,…}]` + 可选 `vars`（`--bg/--fg/--primary/--accent/--surface/--line/--muted/--font-head/--font-body`，由 extract_* 从源文件抽取，build_deck 以 CSS 后定义覆盖 preset）。流水线：`md/pptx/pdf → (md2spec / extract_*) → deck.json → (build_deck / build_pptx) → html/pptx`；长 deck 可 `--split` 拆分子 spec，`merge_spec.py` 合并骨架与内容。

## 新增产物（课题申报 / 教材扩充 / 文献蒸馏）

三个新能力（edu-grant-writer / textbook-chapter-expansion / literature-distiller）的产出同样落 `data/pipeline/incoming|outgoing/`，遵循数据总线，命名规范 `{task_id}_{stage}_{skill}.{format}`：

| 新技能 | 新增产物 | 说明 |
|--------|---------|------|
| edu-grant-writer | `proposal_draft.md` | 申报书草稿（七章制或用户自定义模板） |
| edu-grant-writer | `proposal_state.json` | 跨对话进度状态（Phase -1/0/0.5/1/2 + 素材清单 + 已完成章节） |
| edu-grant-writer | `quality_report.md` | 申报书质量检测报告（反模式/AI 痕迹/政策匹配/级别适配/结构完整性） |
| textbook-chapter-expansion | `expansion_plan.json` | 扩充方案（三路扫描结果 + 章节补齐优先级） |
| textbook-chapter-expansion | `injections.json` | 注入点清单（锚点 + 行号范围 + 内容文件） |
| textbook-chapter-expansion | `expansion_report.md` | 扩充总结报告（补齐前/后对比 + 验证结果） |
| textbook-chapter-expansion | `*.v{version}.bak` | **强制备份先行**——编辑前必须复制原文件为 `.bak` |
| literature-distiller | `distilled_{paper_id}.md` | 蒸馏报告（4+2 模块：M1 元数据→M2 逻辑骨架→M3 引文网络→M4 批判性洞察→M5 知识关联） |
| literature-distiller | `distilled_metadata.json` | 结构化元数据（M1 字段：标题/作者/机构/来源/年份/DOI/页数/语言/快速标签） |
