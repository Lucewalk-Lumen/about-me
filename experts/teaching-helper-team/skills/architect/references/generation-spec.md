# 生成规范（spec-driven generation）

> 本文件是 `material-extractor` 的生成器行为契约，由 Agent 在 Phase 2 严格遵循。
> 适配 WorkBuddy 技能布局（目录 + `SKILL.md` frontmatter）。
> 提取阶段产物为 `data/pipeline/incoming/full_text.txt` + `metadata.json`（见 `SKILL.md` Phase 1）。

## 0. 设计原则（不可违背）

1. **提取结构，不提取原文**——提炼命名框架、决策规则、反模式；绝不要照搬整段。
2. **编译时优于运行时**——导航/结构化只做一次；查询时仅加载相关章节文件。
3. **按需章节**——`SKILL.md` 保持精简；`chapters/*.md` 仅在被索引引用时读取。
4. **前置加载**——最重要的内容（核心心智模型、索引）放在 `SKILL.md` 前部，压缩从末尾截断。
5. **容错继续**——单源失败仅跳过；生成不确定处显式标注，不臆造。

## 1. 产物结构（WorkBuddy 适配）

生成的技能包写入 `skills/<slug>/`：

```
skills/<slug>/
  SKILL.md        核心框架 + 章节&主题索引（~4K token，前置加载）
  chapters/*.md   按需加载，仅在被索引引用时读取
  glossary.md     术语表
  patterns.md     方法 / 技术模式
  cheatsheet.md   决策规则 / 决策树 / 权衡 / 提示（decision layer）
```

`SKILL.md` frontmatter（与现有技能一致）：

```yaml
---
name: <slug>            # 与目录名一致，kebab-case
version: 1.1.1
description: >
  一句话说明该技能包从哪本书/文档沉淀而来、覆盖什么主题、何时被调用
  （说明「何时使用」而非泛泛介绍能力）。
---
```

> 说明：产物可安装到宿主技能的对应目录；
> 在本团队统一收敛到 WorkBuddy 的 `skills/<slug>/` 目录，由 `.codebuddy-plugin/plugin.json` 注册。

## 2. 生成步骤（Steps 0–10）

| Step | 动作 | 要点 |
|------|------|------|
| 0 | 确认目标与下游用途 | 课件 / 案例 / 论文教材 / 长文稿（决定侧重） |
| 1.5 | 判定内容类型 → `BOOK_TYPE` | `technical`（表格/代码块，优先 Docling，未安装时改用 pdftotext/pypdf）/ `text`（pdftotext/pypdf，即时） |
| 2 / 2.5 | 提取 + 成本估算 + 确认 | 读取 `metadata.json` 给出 token/章节数估算，确认后继续 |
| 2.6 | 大书 REPL 式探测 | 用 grep/sed 定位章节，不全量重读 |
| 3 | 结构分析 | 标题、作者、章节、目录（可跨多源聚合） |
| 4 | 目的 → `DEPTH` | `reference`（速查型，低预算）/ `study`（研读型，高预算） |
| 7 | 每章摘要 | 预算 = `BOOK_TYPE × DEPTH`（见 §3）；technical 含 Code Examples + Reference Tables |
| 8 | 术语 / 模式 / 备忘 | 决策层内容（cheatsheet 为重点） |
| 9 / 9.5 | `SKILL.md` 核心 + 索引 | 写核心心智模型；章节&主题索引指向 `chapters/*.md`；随后跑 prompt-injection 扫描 |
| 10 | 落盘 + 校验交接 | 产物交 `architect/scripts/validate_pack.py` 权威校验 |

## 3. 章节预算公式

`每章摘要 token ≈ BOOK_TYPE 系数 × DEPTH 系数`：

| | `reference`（速查） | `study`（研读） |
|---|---|---|
| `text` | 800 | 1,200 |
| `technical` | 1,000（+代码/表） | 1,500（+代码/表） |

- `SKILL.md` 自身控制在 ~4K token，核心框架 + 索引在前。
- `chapters/*.md` 单章独立成文件，便于按需加载（符合「编译时优于运行时」）。

## 4. 安全（继承上游分层 + 团队门禁）

- **提取净化**：`skills/material-extractor/scripts/extractor/sanitize.py` 已剥离零宽字符与 Unicode tag block，阻断文档投毒式隐形指令进入上下文。
- **DOCX XXE / Billion-Laughs 防护**：`skills/material-extractor/scripts/extractor/parsers/docx.py` 拒绝声明 DTD/实体的 XML。
- **子进程参数注入防护**：文件路径在到达 `pdftotext`/`ebook-convert` 前被绝对化，防 `-` 开头文件名被当作 flag。
- **生成技能扫描**：Step 9.5 跑 `skills/material-extractor/scripts/tools/scan_generated_skill.py`（开放标准前置扫描，位于 material-extractor 的 scripts/tools/），标记指令覆写措辞、模型控制标签、残留隐形 Unicode、权限扩大 frontmatter、外泄形内容；**仅告警、不自动拦截**，供人工研判。
- **团队门禁衔接**：若生成的技能包对外发布，最终成稿须过 `deai-rules` 去AI味门禁；含理论/数字须过 `skills/citation-integrity/SKILL.md` 引用保真校验。

## 5. 与 WorkBuddy 校验的对接

- 本规范生成的 `skills/<slug>/` 即为标准 WorkBuddy 技能目录，可直接被 `architect/scripts/validate_pack.py` 校验。
- 本技能调用 `skills/material-extractor/scripts/tools/validate_skill.py`（WorkBuddy 规则）仅作开放标准**前置**检查（该脚本物理位于 material-extractor 的 scripts/tools/，作为共享前置工具调用）；最终权威校验仍由 `architect/scripts/validate_pack.py` 完成（见 `SKILL.md` Phase 3）。
