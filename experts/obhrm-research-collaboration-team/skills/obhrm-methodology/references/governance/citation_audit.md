# 引证核对书 — 模板（关卡产物 A6 + quality-assurance 引用验证）

> **本文件性质**：方法论关卡产物模板（运行时由用户在 A6 成稿后 / quality-assurance 阶段复制到工作目录填写，不随技能包直接发布成品）。
> **来源**：强制结构由 `gate_artifact_spec.md` §4 定义。本文件是该模板的工作副本 + 填写指引。
> **触发**：A6 成稿后、导出文档前 / 质量评分阶段（quality-assurance.md）的引用验证步骤。
> **门控**：存在未核验或失效引用 → 阻塞导出 + 触发 R1「不编引用」红线。
> **位置**：本文件位于 `references/governance/`，供 agent 加载引用；运行时由 agent 复制到用户工作目录并按以下结构填入。

---

## 何时填写 / 谁检查

| 项 | 说明 |
|---|------|
| 触发阶段 | A6 成稿后导出前；或 quality-assurance.md 八维诊断第 7 维"写作规范"执行时 |
| 填写人 | 用户（agent 引导 + 通过平台 WebSearch/WebFetch 核验 DOI 后调用 `../../scripts/format_citation_report.py` 生成三态报告） |
| 检查点 | 导出 .docx 前必须存在；逐条核对表每行"状态"必须勾选 `□ OK` 或 `□ 疑` |
| 失败处理 | 存在 `□ 疑` 项 → 阻塞导出，agent 报告"引证未通过：N 条引用 CrossRef 核验失败或 DOI 失效" |
| 引用关系 | 上游：results_validation.md（A4→A5）+ A5 全文；下游：reviewer_audit.md 引用真实项 + 导出 .docx |

---

## 模板（运行时复制本段到工作目录文件）

````markdown
# 引证核对书

## 逐条核对（作者 / 卷 / 页码 / DOI）
| 序号 | 文中引用 | 作者 | 年份 | 卷(期) | 页码 | DOI | CrossRef核验 | 状态 |
|------|----------|------|------|---------|------|-----|--------------|------|
| 1 | (Author, 2020) | | | | | | □ 通过 □ 失效 | □ OK □ 疑 |

## Red Flags 扫描
- 无 DOI 且无法核验的引用：<列出，标注"待用户提供原始文献">
- "看起来像真的"但未核验：<列出>
- 自我引用占比：___%（超出 30% 需说明）

## 结论
- 全部可核验：□ 是 □ 否
- 不可核验项处理方案：<说明>
````

---

## 填写要点（agent 引导用户时使用）

1. **逐条核对**：
   - 序号：与正文中引用出现顺序一致（不要按字母重排）
   - 文中引用：原文中 `(Author, Year)` 形式完整字符串
   - 作者 / 年份 / 卷(期) / 页码：必须与原始文献一致，**不是从 CrossRef 复制就一定对**（CrossRef 有错）
   - DOI：以 `https://doi.org/<DOI>` 形式填入
   - CrossRef 核验：通过平台 WebSearch/WebFetch 逐条查询 DOI 存 crossref.json，再调用 `../../scripts/format_citation_report.py` 生成三态报告
   - 状态：`□ OK` = 三项（作者/年份/DOI）全部一致；`□ 疑` = 任一不一致或 DOI 失效
2. **Red Flags 扫描**：
   - 无 DOI 引用 = 优先核验（部分书籍/灰色文献无 DOI，但需提供 ISBN/URL/原始 PDF）
   - 自我引用占比 >30% = 必须说明（学科差异允许但需写理由）
3. **结论**：
   - 全部可核验 = 仅当 `□ OK` 占 100% 时勾选
   - 不可核验项处理方案 = 列出每条的最终处置（删除 / 替换 / 注明"待用户提供原始文献"）

---

## 不变量

- 三段结构（逐条核对 + Red Flags 扫描 + 结论）必须齐全。
- 逐条核对表每行 9 个单元格必须有内容（"CrossRef核验" 和 "状态" 必勾选）。
- 存在 `□ 疑` 项且"不可核验项处理方案"为空 → 关卡门控拒绝放行。

---

## 相关引用

- 上游规范：`gate_artifact_spec.md` §4
- 上游流程：`../../../paper-writing/SKILL.md` A6 + `../../domains/quality-assurance/quality-assurance.md`
- 工具支持：`../../scripts/format_citation_report.py`（DOI 三态核验报告）+ `../../scripts/format_references.py`（格式整理）
- 关联方法论：`method_accumulation.md`（引用保真四铁律）
- Red Flags 联动：DOI 失效或无核验触发 `../templates/verification_and_failure_modes.md` 的 R1 不编引用 + R2 不归观点
