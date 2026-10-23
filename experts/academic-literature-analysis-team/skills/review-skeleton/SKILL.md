# 一键综述骨架生成器（review-skeleton）

把文献计量分析团的**分析产物（JSON）**转化为一份结构化的「文献综述提纲」，套用本技能内置的「文献综述」框架。本技能只回答**写什么、按什么逻辑写**，不做任何引文 / 参考文献格式化。

> [!] **本技能不是引文管理工具。** 严禁 GB/T 7714、APA、参考文献列表、引用管理等能力。引用落地请交给专用引文工具。references/ 目录内**不包含**任何引文格式定义文件。

## 上游输入（六个分析功能产物）

本技能是本分析包的**下游消费者**。以下 JSON 任一可缺，脚本会健壮跳过并标注：

| 产物 | 文件 | 在骨架中的用途 |
|------|------|----------------|
| 主题聚类 | `topics.json` | 每个 cluster → 一个综述主题（关键词 / 语言 / 年份跨度） |
| 主题×年份演化 | `evolution.json` | 每个主题的年份趋势（上升 / 平稳 / 下降 + 峰值年） |
| 作者×主题 | `author_topic.json` | 每个主题的核心作者（及全局核心作者） |
| 共现网络 | `network.json` | 跨主题桥接词（潜在整合点） |
| 时效性 | `age.json` | 陈旧 / 前沿信号，驱动缺口提示 |
| 重复检测 | `dup.json` | 可选，提示数据质量（不影响骨架结构） |

## 一键生成（CLI）

纯标准库 Python，不依赖 R：

```bash
python3 scripts/build_skeleton.py \
  --topics T --evolution E --author-topic A --network N --age G --dup D \
  --out SKELETON.md \
  --docx SKELETON.docx \
  --title "我的综述骨架" --library "库名（脱敏）"

# 任一输入可缺；框架目录默认取 scripts/../references，亦可 --refs 指定
# 不传 --out 则只打印到 stdout
```

输出 Markdown 骨架，含数据来源标注与本技能免责声明。

## 可编辑 Word 与腾讯文档

骨架需以可编辑的 Word 格式交付。落地方式：

1. **`--docx SKELETON.docx`**（默认必带）：`build_skeleton.py` 同步产出
   可编辑 Word（纯标准库 OOXML 实现，见 `scripts/md_to_docx.py`），
   Word / WPS 双击即改。**交付骨架时 .docx 与 .md 必须同时给出。**
2. **腾讯文档在线协作**（需要多人协作 / 云端编辑时）：
   - 首选：把生成的 `SKELETON.docx` 上传到腾讯文档（宿主环境提供
     腾讯文档技能时可直接代传），转为在线文档后即可评论与协作；
   - 包本身**离线运行、不联网**，不直接调用腾讯文档 API —— 上传动作
     由用户或宿主技能完成，这是隐私边界而非功能缺失。

## 骨架结构（六段 + 附录）

脚本生成的骨架严格遵循以下组织，每一段都**驱动自 references/ 下的抽取框架**：

### 1. 引言地图（Introduction Map）
- 驱动：数据画像（`topics`/`age`/`network`）+ `amj_elements.json`（AMJ 写作九要素）。
- 给出"为什么写、写给谁、卡在哪"的要素清单，并提示引言末段落到「研究缺口」。

### 2. 按主题的综合方案（Thematic Synthesis Plan）
- 驱动：`topics` × `evolution` × `author_topic` × `network`。
- 每个分析 cluster 映射为一个综述子主题，含：
  - 关键词（top_terms）、语言构成、年份跨度；
  - 年份趋势（上升 / 平稳 / 下降 + 峰值年，来自 `evolution`）；
  - 核心作者（来自 `author_topic` 的 `top_per_topic`，否则回退 `global_core_authors`）；
  - 4 条数据驱动的综合提纲建议。
- 附「跨主题桥接」小节：列出 `network` 中 `is_bridge` 关键词，作为整合性综述切入点。

### 3. 研究空白与新颖性（Research Gaps & Novelty）
- 驱动：`gap_novelty.json`（五类缺口 + 新颖性四等级）+ 数据信号（`age`/`network`/`topics`）。
- 要求每个候选方向同时标注：① 新颖性等级（N1–N4）② 缺口类型（证据/知识/实践-理论/方法/评价）。
- 给出由实效性、桥接词、关键词覆盖率推导的"数据信号"缺口提示。

### 4. 论证脚手架（Argumentation Scaffold）
- 驱动：`argumentation_framework.json`。
- 输出图尔敏六要素、文献链四段式模板、证据矩阵列、主张强度×证据等级、反"文献罗列"闸门——确保每段有 Warrant、每条文献连到本研究、无孤岛段落。

### 5. 章节顺序建议（Section Order）
- 驱动：`templates.json`（章节结构 / 双语映射 / 组织方式）。
- **严格剔除"参考文献"节**（非本技能职责）；推荐 研究背景 → 研究现状 → 结论(述评) → 质量自检 的章节流，并给出中英对照。
- 引用落地明确指向专用引文工具。

### 6. 质量检查清单（Quality Checklist）
- 驱动：`quality_scoring.json`（八维度评分 + 关键门控）+ `red_flags.json`（红线 / 验证机制 / 借口vs事实）。
- 完稿前逐项核对；标记 [红] 的关键维度（文献覆盖 / 理论深度 / 论证连接）任一 ≤2 分即不通过。

### 附录：可用框架索引
- 列出 `references/` 下全部抽取框架（不含任何引文格式文件），供撰写时按需调阅。

## references/ 目录（抽取框架，已剔除引文格式）

`references/` 收录综述写作所需的非引文知识文件：
`gap_novelty.json`、`argumentation_framework.json`、`quality_scoring.json`、`red_flags.json`、`templates.json`、`amj_elements.json`、`paradigms.json`、`stage_gates.json`、`brainstorming_protocol.json`、`closed_loop.json`、`evidence_claim_map.json`、`reading_codes.json`、`journal_standards.json`、`bilingual_terms.json`、`peer_review_framework.md`、`topic_scoping_prompt.md`、`writing_style_notes.md`。

**以上文件均不含 GB/T 7714 / APA / 参考文献列表 / 引用格式内容。**

## 与本分析包的衔接

- 先由 `academic-lit-analysis-lead` 跑出 6 个分析 JSON；
- 本技能消费这些 JSON，产出可落笔的综述骨架；
- 引用与参考文献由用户另行用专用引文工具处理。

## 铁律

1. 不做任何引文 / 参考文献格式化（无 GB/T 7714、APA、参考文献列表、引用管理）。
2. 不编造文献；所有作者 / 年份 / 关键词均来自分析产物。
3. 任一输入 JSON 缺失时，降级注明"未提供"，不整体失败。
