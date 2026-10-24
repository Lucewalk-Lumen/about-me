# examples-index.md —— 端到端样例索引

> 本 Skill 的端到端样例(含 input.json / result.json / provenance-audit.json + 4-5 渲染产物 + 各档 README)
> 样例数据存放于开发期项目根的 `demos/` 目录,
> 本文件保持精简，避免占用 LLM 的 references 上下文。


> 本包内不存在 `demos/` 目录。凡本文引用 fixture 文件(`input.json` / `result.json` / `dependencies.json` /
> `explanations.json` / `provenance-audit.json` / `textbook.md` 等)之处,一律按「规格描述」而非「可打开的文件」理解:
> 字段契约见 `prompt-templates.md`(schema + 各 Step 模板)、质量标准见 `framework-rubric.md`、
> 溯源判定见 `provenance-spec.md`。不要尝试读取这些路径,也不要因读取失败而中断流程。

## 完整样例位置

| 类型 | 位置 |
|---|---|
| input + result + 渲染 + audit | `demos/knowledge-framework-builder/result-fixtures/` |
| (规划)HTML 报告 demo | `demos/knowledge-framework-builder/html-demos/`(Step 9 主动询问后才生成)|

## 已落地样例

| 样例 | 模式 | 深度 | 数据源 | 节点 | 讲解 | 依赖 | 渲染 | 验证亮点 |
|---|---|---|---|---:|---:|---:|---:|---|
| `topic-only-cet/` | `topic_only` | skim | `course_topic` | 94 | 0 | 0 | 4 | 最小 dogfood:纯主题输入 + 全 ai_inference + 顶部 [注意] banner |
| `compact-cet/` | `topic_only` | skim | `course_topic` | 22 | 0 | 0 | 4 | 紧凑模板:小尺寸 fixture 用于回归验证 |
| `topic-with-focus-cet/` | `topic_only` | skim + **guided** | `course_topic + focus_topics + user_level` | 94 | **8** | 0 | 4 | 跨子树 8 个 200-500 字讲解 + `<details>` 折叠块 |
| `topic-deep-with-deps-cet/` | `topic_only` | skim + guided + **deep** | + `deep_explain + concept_dep=aggressive` | 94 | **13** | **12** | **5** | 子树 deep + 6 类依赖 + DEEP_BATCH_TRUNCATED warning + Mermaid flowchart |
| `material-markdown-ml/` [关键] | **`hybrid`** | skim + guided | + `markdown_path`(真实教材) | 38 | 6 | 5 | 5 | **真实 N-gram 闭环:32 high / 1 故意 failed / 5 ai_inference skipped** |

## LLM 使用建议

> 以下建议以**已挂载 `demos/` 样例数据**为前提。在本发布包内 fixture 不可读,
> 请改走「本包内等效路径」一栏:契约与 schema 读 `prompt-templates.md`、
> few-shot 示例直接用 `prompt-templates.md` 各 Step 模板内的内联样例、
> 质量自检读 `framework-rubric.md`、溯源阈值读 `provenance-spec.md`。

- **了解输入输出契约** → 直接读示例的 input.json + result.json 是最快路径(覆盖最多字段)
- **写 few-shot prompt 出讲解** → 用示例的 explanations.json 的 1-2 条做 in-context 示例
- **写 few-shot prompt 出依赖** → 用示例的 dependencies.json(conservative 与 aggressive 两版)
- **debug 渲染** → 让 `scripts/render_outputs.py` 跑任一 fixture 的 `result.json` 重出 5 格式,对比 fixture 确认
- **样例一致性校验** → 跑 `assemble_result.py` 重组装 + diff 校验
- **不要做的事** → 不要把 fixture 全文塞进 LLM Prompt,会浪费 ~5-30KB token;改用本 Skill 的 `framework-rubric.md` + `prompt-templates.md` 提供 schema + checklist

## Provenance verdict 命中分布(用于教学 / 对外宣传)

示例 fixture 的 `provenance-audit.json` 是本 Skill「核心原则 4」的最佳展示样本:

```json
{
  "verdict_counts": { "high": 32, "medium": 0, "low": 0, "failed": 1, "skipped": 5 },
  "high_ratio": 0.97
}
```

含义:
- **high (32)**:LLM 生成的 evidence_locator.excerpt 在原文 N-gram 上 ≥ 0.85 命中 → 用户可放心
- **failed (1)**:`n4.5 留出法 vs 交叉验证选择` —— 我们故意伪造的 excerpt 被脚本抓住 [通过]
- **skipped (5)**:LLM 自加的概括节点(`n2.3.3` `n4.4` `n6` `n6.1` `n6.2`)诚实标 ai_inference,不冒充教材

## 与本 Skill 其它文档的关系

- 各样例的设计取自 `concept-dependency-taxonomy.md` §8 的依赖图规划
- Provenance 状态(skipped / high / low / failed)的实例分别由不同样例验证(详见每个 fixture 的 README §"本例验证了 SKILL.md 的哪些契约")
- `prompt-templates.md` §8 给出了"哪个 Step 的模板对应哪个样例"的映射表
- `outline-parsing-heuristics.md` §3 的启发式样例 == 示例 textbook.md 的真实 markdown ATX 命中
