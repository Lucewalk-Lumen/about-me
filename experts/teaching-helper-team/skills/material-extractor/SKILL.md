---
name: material-extractor
version: 1.1.1
description: >
  材料提取基础能力：将教材 / 专著 / PDF / EPUB / DOCX / HTML / RTF / TXT 等多源素材确定性提取为
  结构化全文（full_text.txt）+ 元数据（metadata.json：页数/词数/章节/目录）。
  作为 course-builder（课件/教材）、case-writer（案例理论映射）、thesis-mentor（文献/理论框架）、
  long-manuscript-core（长文稿素材）的上游素材生产器。提取器纯本地、零外部 API、可选依赖由 setup 托管。
---

# 材料提取（material-extractor）

> **归属**：基础能力层（foundation）——第2.位「提取」，挂主理人 lead，专注确定性文档提取。
> 提取器以 vendoring 形式内置于 `scripts/extractor/`（MIT 许可）。

本技能把「多源素材 → 结构化全文 + 元数据」做成独立、可复用模块，供下游领域技能直接消费提取结果。

## 何时使用

- 教材 / 文档 / 专著 / PDF / EPUB / DOCX / HTML / RTF / TXT 需提取为结构化文本
- 下游领域技能（course-builder / case-writer / thesis-mentor / long-manuscript-core）需要「全文 + 元数据」作为素材输入
- 知识入库前（knowledge-wiki）的文档结构化预处理

> 当用户诉求是「直接写课件 / 案例 / 论文」而非「先提取素材」时，由主理人按需调用本技能作为前置，不单独暴露给用户。

## 工作流（Phase 0–1）

### Phase 0 — 输入确认
向用户/主理人确认：
- **素材来源**：本地路径（PDF/EPUB/DOCX/HTML/RTF/TXT）、`data/pipeline/incoming/` 下素材，或先经 `crawler` / `content-summary` 落地的文件。
- **模式**：`technical`（含表格/代码块，优先 Docling；未装时改用 pdftotext/pypdf）或 `text`（pdftotext/pypdf）。

### Phase 1 — 确定性提取
由主理人调用提取器，产出结构化中间物：

```bash
export BOOK_SKILL_WORKDIR="data/pipeline/incoming"   # 输出目录（落数据总线）；省略则写脚本私有临时目录，下游不可依赖
export BOOK_SKILL_INSTALL_MISSING="false"                  # 禁用自动 pip，依赖由 setup 托管
$VENV_PY skills/material-extractor/scripts/extract_entry.py \
    "<文档路径或 glob…>" --mode <technical|text>
```

- **模块入口（备用）**：解释器路径不便时，可改在 `skills/material-extractor/scripts/` 目录下执行 `$VENV_PY -m extractor "<文档路径或 glob…>" --mode <technical|text>`，参数与产物同上。
- 产物：`full_text.txt`（多源合并 + 源标记）、`metadata.json`（页数/词数/token/章节/ToC）。
- 任一批源失败仅告警跳过，其余继续。
- 提取阶段已做**不可见字符净化**（零宽 U+200B/C/D/2060/FEFF、Unicode tag block U+E0000–E007F 剥离并记录计数），阻断文档投毒式隐形指令。

### 下游消费
下游领域技能直接读取提取结果，不再生成中间技能包：

| 下游技能 | 消费方式 |
|---------|---------|
| `course-builder` | full_text.txt + metadata.json → 知识框架 / 教材编制 / 课件 |
| `case-writer` | 理论锚点（遵循引用保真，不内嵌原文） |
| `thesis-mentor` | 文献/理论线索（「轻量索引、不内嵌原文」约定，metadata 仅作线索） |
| `long-manuscript-core` | 大纲/章节草稿作为「素材激活」输入 |
| `knowledge-wiki` | 入库前的结构化预处理 |

## 依赖与运行

- **纯本地、零外部 API、无密钥依赖**。所有解析依赖均**可选**，且各格式有 stdlib 备选解析：

| 格式 | 首选依赖（可选） | 备选解析 |
|------|----------------|------|
| PDF | `pypdf` + `pdfminer.six` | `pdftotext`（系统） |
| EPUB | `ebooklib` + `beautifulsoup4` | stdlib `zipfile` |
| DOCX | `python-docx` | stdlib 解包 + XML 解析 |
| HTML | `beautifulsoup4` | stdlib `html.parser` |
| RTF | `striprtf` | 文本提取 |
| technical | `docling`（可选） | pdftotext/pypdf |
| calibre | 系统 `ebook-convert` | — |

- 依赖由 `setup` 统一装入托管 venv（`$VENV_PY`），禁止裸 `python3` 与单独 `pip install`。

## 最小权限与边界

- 默认只声明文件读取 / 本地脚本执行 / 写 `data/pipeline/incoming/`（提取产物）与脚本私有临时工作区；不联网、不写外部 API、不触碰 `agents/`。
- 明确不做：不替代领域写作；不编造引用；不自动安装依赖。
- 「从提取结果生成技能包」的能力已归位 `architect`（生成规范见 `skills/architect/references/generation-spec.md`；本技能内置 `scripts/tools/validate_skill.py` 与 `scripts/tools/scan_generated_skill.py` 作开放标准前置检查，最终权威校验由 `architect` 完成）。
