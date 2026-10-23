---
name: reference-import
version: 1.0.1
description: "Import literature libraries exported from EndNote or Zotero (reviews / supplementary materials) and convert them into READINGS-compatible corpus for the literature-review workflow."
---

# reference-import — 外部文献库导入（EndNote / Zotero）

把用户在 EndNote 或 Zotero 中**已经分析、整理好的文献综述与补充材料**导入本套件，转为文献综述路径（温书恒）可直接消费的 READINGS 兼容语料，避免重复手工录入。

## 支持的导入来源

| 来源 | 格式 | 扩展名 | 解析器 |
|------|------|--------|--------|
| EndNote | 库导出（压缩 XML） | `.enl` | 解压后按 EndNote XML 解析 |
| EndNote | 纯 XML 导出 | `.xml` | EndNote XML |
| EndNote | RIS 导出 | `.ris` | RIS |
| EndNote | BibTeX 导出 | `.bib` | BibTeX |
| Zotero | RIS 导出 | `.ris` | RIS |
| Zotero | BibTeX 导出 | `.bib` | BibTeX |
| Zotero | RDF 导出 | `.rdf` | Zotero RDF（bibo/dc/prism） |
| Zotero | Better BibTeX JSON | `.json` | Better BibTeX JSON |

> 格式按「扩展名 + 内容嗅探」自动判定；同一文件扩展名歧义时（如 `.xml` 也可能是 EndNote XML）以内容为准。

## 用法

```
# 单材料：仅题录
python ${CODEBUDDY_PLUGIN_ROOT}/skills/reference-import/scripts/import_refs.py <题录文件> --out READINGS.imported.md [--source endnote|zotero|auto]

# 双材料：题录 + 用户分析总结（推荐）
python ${CODEBUDDY_PLUGIN_ROOT}/skills/reference-import/scripts/import_refs.py <题录文件> --summary <分析总结.md> --out READINGS.imported.md
```

- 纯标准库实现（无第三方依赖），失败明确报错、绝不静默。
- 输出 `READINGS.imported.md` 含三段素材：
  1. **文献条目块**（供 `closed_loop_check.py` 引证核验，每行 `Author (Year). Title.`）＋ **明细表**（作者/年/题名/出处/DOI/类型）；
  2. **题录内附注释/笔记**（导出文件 notes 字段自动提取，如 EndNote/Zotero 中用户批注）；
  3. **用户文献分析 / 总结**（由 `--summary` 提供的文档，原样保留）。

## 双材料工作流（关键）

> **为什么需要「分析总结」单独提供？** EndNote / Zotero **无法读取本地 PDF 全文**，因此「文献内容层」的分析、归纳、综述总结并不在题录导出里。如果小伙伴用它们做了内容分析、写了综述，请让其**另行导出/提供**那份总结文档（`.md` / `.txt` 等纯文本），与本技能的题录导入**双材料合并**。本工具只负责搬运，不替用户写总结、不臆造观点。

| 材料 | 提供方 | 内容 | 导入方式 |
|------|--------|------|----------|
| ① 题录 | EndNote/Zotero 导出 | 作者/年/题名/出处/DOI/notes | 位置参数 `<题录文件>` |
| ② 分析总结 | 用户另行导出 | 文献内容分析、综述、批注汇总 | `--summary <文件>` |

- 题录里的 notes 字段会自动并入「题录内附注释」段；用户单独写的总结进「用户文献分析 / 总结」段。
- 综述路径引用总结中观点时，须显式标注来源并与其题录条目交叉核验，不得凭记忆补文献。

## 与文献综述路径衔接

1. 用户上传 EndNote/Zotero 导出的文献库（或综述补充材料）→ 主理人 Phase 1.5 本地文件 intake 识别为文献库文件 → 调度本技能解析为 `READINGS.imported.md`（若用户同时给了分析总结，附 `--summary`）。
2. 该语料**并入**综述路径的文献池：与 PDF 摄取产物（`ingest_pdfs.py` + `build_readings.py`）汇流后，统一进入 L2–L3 检索与批判分析。
3. **reading code 不臆造**：导入仅提供书目元数据与用户原样总结，SPL/CPL/GAP/RAT/ROF 编码由文献综述路径按 `select_deepread.py` 在 L3 阶段人工标注；导入产出中相关列留空待填。
4. 引用保真：导入的 DOI / 作者 / 年 原样保留，门控 `closed_loop_check.py` 仍可核验；不得改写或编造。

## 边界

- 仅导入「元数据 + 用户提供的总结」，不导入 PDF 全文——如需全文，请同时提供 PDF（走 PDF 资料库模式）。
- `.enl` 为压缩格式，若本环境解压失败，请改从 EndNote 导出 XML 后导入（脚本会明确报错并提示）。
- 大库（数千条）解析无误，但 `READINGS.imported.md` 仅作语料索引；实际批判阅读仍按 L3 选精读候选，不全量逐篇。
- `--summary` 内容**原样保留、不改写**；若用户未提供总结，该段留空，不编造。
