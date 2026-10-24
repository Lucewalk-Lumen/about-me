# PDF 资料库模式：摄取与全量总结

> 让技能真正"覆盖一级文件夹中的 PDF 文件"（含 `综述/` 子文件夹），并保证全量总结不丢失。
> 成稿自检结构化定义见 `../knowledge/closed_loop.json`；脚本用法见 `skills/obhrm-methodology/scripts/ingest_pdfs.py --help` 与 `skills/obhrm-methodology/scripts/litreview_docx_export.py --help`。

## 一、何时进入本模式

用户给出**文件夹路径**，或说"总结我的文献资料库 / 把 综述 文件夹全部总结 / 不能丢失 / ingestion"。典型输入如 `~/Desktop/文献综述/`（一级若干篇 PDF + 子文件夹若干篇）。边界：只处理用户提供的文件夹内 PDF（含子文件夹递归），不凭训练数据补充未提供的文献（安全原则）。

## 二、标准工作流（推荐：脚本驱动）

1. **摄取**：运行 `skills/obhrm-methodology/scripts/ingest_pdfs.py <文件夹> --out <输出目录>`。递归扫描全部 `.pdf`（含子文件夹），自动跳过 `__MACOSX`。产出 `texts/<name>.txt`（每篇全文提取，磁盘留存）、`notes/<name>.md`（元数据+原文预览+结构化笔记占位）、`<输出目录>/00-MANIFEST.md`（全部 PDF 清单，运行时由 `skills/obhrm-methodology/scripts/ingest_pdfs.py` 生成）、`<输出目录>/00-COVERAGE-CHECKLIST.md`（逐条勾选的覆盖核对表，运行时由 `skills/obhrm-methodology/scripts/ingest_pdfs.py` 生成）。
2. **逐篇总结**：读取 `notes/*.md` 与对应 `texts/*.txt`，为每篇写 1 段摘要（研究问题 / 方法 / 核心结论 / 关联）。**严禁编造原文没有的内容**。
3. **全量整合**：跨 PDF 归纳主题脉络、方法路径、争议焦点、研究空白，输出 `<输出目录>/综述全量总结.md`（整合稿，运行时由用户编辑生成）。
4. **闭环校验**：每条核心论断标注来源 PDF；引用观点须对应该 PDF 原文（呼应引证完整性核查）。

## 三、不丢失的保证（三道防线）

1. **清单对账**：`<输出目录>/00-MANIFEST.md` 列出每一篇 PDF 的路径/页数/字数；总结前先核对总数是否等于源文件夹 PDF 数。
2. **勾选清单**：`<输出目录>/00-COVERAGE-CHECKLIST.md` 逐条 `[ ] 已提取 / [ ] 已总结 / [ ] 已挂载框架`，全部勾完才算完成。
3. **回溯可查**：`texts/*.txt` 磁盘留存全文，任一摘要存疑可回查原文。

## 四、无 PDF 库时的手动回退

若运行环境无 `pdfplumber` / `pypdf`，则对每篇 PDF 用 Read 工具**逐篇读取**（可视化呈现），并**手动维护同一份 MANIFEST 与 CHECKLIST**。逐篇读取同样保证不丢失。

## 五、输出形态（标准交付）

- `<输出目录>/00-MANIFEST.md`（资料库清单，运行时由 `skills/obhrm-methodology/scripts/ingest_pdfs.py` 生成）
- `<输出目录>/00-COVERAGE-CHECKLIST.md`（不丢失证明，运行时由 `skills/obhrm-methodology/scripts/ingest_pdfs.py` 生成）
- `notes/*.md`（逐篇摘要）
- `<输出目录>/综述全量总结.md`（整合稿 → 经 `skills/obhrm-methodology/scripts/litreview_docx_export.py` 导出 Word，运行时由用户编辑生成）

## 六、与成稿自检的衔接

资料库模式各阶段对应成稿自检流程：搭骨架阶段由逐篇摘要→主题聚类，对应文献纳排审计与主题聚类；动外科手术阶段做缺口论证、批判性重构，对应空白论证与批判性重构；终审阶段引证逐条回查 PDF 原文，对应引证完整性核查；成稿阶段中英双语 + 画图，对应双语范式与图表引擎（见 SKILL.md 第十节（画图功能）与第十一节（参考文档索引），以及 `../knowledge/closed_loop.json` 与 `diagram-recipes.md`）。

## 七、阅读密码与精读八问工作流

> 结构化定义见 `../knowledge/reading_codes.json`（5 密码字段 + 精读八问 + 字段映射）；缺口分类见 `../knowledge/gap_novelty.json`。

对每篇精读文献，可用 `skills/obhrm-methodology/scripts/build_readings.py --codes` 为其产出 **5 个空槽**：`SPL`（研究问题）/ `CPL`（核心贡献）/ `GAP`（研究缺口指针）/ `RAT`（论证逻辑）/ `ROF`（研究发现）。

- **脚本只产空槽，不填内容**：`--codes` 开关在 `notes/<name>.md` 中为每篇追加 5 个待填字段，字段留空，不自动编造，遵守安全原则（不凭训练数据补充原文没有的内容）。
- **何时由人工/LLM 填充**：在精读阶段，由研究者或 LLM 依据 `reading_codes.json` 的**精读八问清单**（围绕构念/机制/边界/方法/贡献）逐题作答，再把答案回填到对应密码字段。GAP 字段只填指针（`gap_type_id` + 一句话落点），缺口分类定义不在此展开。
- **填充边界**：`SPL/CPL/RAT/ROF` 必须来自该 PDF 原文；无原文依据的槽位保持空白并标注"待补"，禁止 AI 自行编造。
- **流向下游**：填好的密码字段按 `reading_codes.json` 的 `field_mapping` 汇入 G1+ 选题收敛（SPL/GAP + 新颖性判断）与 G2 证据映射（ROF/RAT → evidence_claim_map）。
