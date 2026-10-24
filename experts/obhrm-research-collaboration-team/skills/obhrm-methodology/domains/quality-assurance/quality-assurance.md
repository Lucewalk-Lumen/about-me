# 质量保障域（quality_assurance · 跨路径通用质量评分）

跨路径通用的质量评分与高级输出规范（"评分 + 输出规范 + 闸门"三位一体的质量保障定位）。

---

## 阶段质量评分

每个阶段结束时，在回复末尾输出结构化 JSON：

```json
{
  "stage": "A3",
  "path_type": "A",
  "stage_scores": {
    "选题质量": 4.0, "文献覆盖": 3.5, "理论深度": 4.0,
    "方法严谨": 3.5, "写作质量": 4.0, "创新程度": 3.5, "发表潜力": 4.0,
    "图表嵌入": 4.0, "交叉引用": 4.0, "论证连接": 4.0
  },
  "发现缺陷": [
    {"描述": "假设缺乏竞争解释", "严重性": "高", "确定性": 0.9, "编号": "DEF-001"},
    {"描述": "结果节未嵌入图表/无正文引用", "严重性": "高", "确定性": 0.95, "编号": "DEF-CHART-001"},
    {"描述": "贡献-假设-结果-图表未形成可追溯链", "严重性": "中", "确定性": 0.9, "编号": "DEF-LINK-001"},
    {"描述": "论证断裂：主张缺Warrant/无支撑文献(悬空主张)", "严重性": "高", "确定性": 0.95, "编号": "DEF-LINK-002"},
    {"描述": "文献链未闭环到本研究/证据矩阵嵌入位为空", "严重性": "中", "确定性": 0.85, "编号": "DEF-LINK-003"}
  ],
  "备注": "A3理论建构完成，竞争假设覆盖不足"
}
```

**字段说明：**
- `stage`：当前阶段。审稿路径诊断时 `"C3/A3"`
- `stage_scores`：10 维度，1-5 分（含 `图表嵌入` / `交叉引用` / `论证连接`）
- `发现缺陷`：具体缺陷，`编号` 用已有或 null
- `备注`：≤100 字

> **图表嵌入 / 交叉引用 / 论证连接 评分标准**：
> - `图表嵌入`：含数据子节是否都有图/表、是否编号+图注(≥80字)+正文引用。缺失 → ≤2 分
> - `交叉引用`：贡献→假设→结果→图表是否形成可追溯链；章节/图/表/文献是否显式互引。孤岛段落多 → ≤2 分
> - `论证连接`：主张-证据-文献三元是否齐备；图尔敏 Warrant 是否给出机制解释；文献链是否闭环到本研究；是否存悬空主张/逻辑断链。任一存在 → ≤2 分，阻断确认点（详见 `../../references/reasoning/argument_frameworks.md`）

---

## 高级输出规范

### 润色标准
- 结论前置：段首给核心结论
- 精确限定：定量替代模糊（"提升23%"非"显著提升"）
- 主动语态：We found... 非 It was found...
- 去AI腔调：清除 clearly/obviously/notably

### 引用验证
- 作者/卷/页码/DOI 逐一核对
- 输出 `../../references/governance/citation_audit.md`（强制结构见 `../../references/governance/gate_artifact_spec.md` 第 4 节）

### 去AI痕迹（投稿前按需，light/medium/heavy）
> 编号用 ①-⑤ 以区别于数据分析路径的 D1-D4 阶段，避免命名空间冲突。
- ① 句式多样性 · ② 过渡自然度 · ③ 术语一致性
- ④ 论证密度 · ⑤ 学术语气

## 跨域联动

- **适用全路径**：A/B/D/M/L/C/J 七条路径的每一阶段末均可输出评分块（10 维 1-5 分），作为交付前的统一判据。
- **与去 AI 深度改写分工**：本域的「AI痕迹①-⑤ 轻量自检」是投稿前的快速扫描与点状修复；用户明确要求全文级改写时切 `../humanize/humanize.md`（深度改写管线）。二者为**同一去AI关切的两档强度**，标准一致、不互斥、不重复（详见 SKILL.md「去AI 一致性」段）。
- **图表/论证三维度**（`图表嵌入` / `交叉引用` / `论证连接`）：评分依据来自 `../visualization/visualization.md` 的「图表嵌入协议」+ `../../references/reasoning/argument_frameworks.md` 的完成判定；任一缺失即 ≤2 分、阻断确认点。
- **方法层**：`../../../peer-review/references/feedback_loop.md`（质量反馈闭环）、`../../references/writing/academic_writing_style.md`（含去AI化增强）、`../../references/templates/verification_and_failure_modes.md`（声称验证门控）。
- **与其他去AI资源的分工**：套件内共有四层去AI相关资源（起草期学术文风 / 综述专项去AI / 投稿前轻量自检 / 成稿深度去AI），完整分工见 `../humanize/humanize.md` §〇。

## 协作交接

评分块作为各阶段末的强制产物，是跨路径交接的通用判据：

- 论文 A5/A6 / 基金 B9 / 元分析 M5 收尾时，评分块随链路三交接块送 审稿路径诊断。
- 论文返修后 W→C9 链路五，评分块作为「自检未过项」字段的依据。
- 选刊 J→C 反向适配时，评分块中的「写作质量」与「图表嵌入」可作为微调优先级的输入。

> 字段级规格见 `../../references/templates/handoff-protocol.md` 各链路；判据与 scoring 详细规范见本文件「阶段质量评分」。

## 参考

`../../../peer-review/references/feedback_loop.md`、`../../references/writing/academic_writing_style.md`（含去AI化增强）、`../../references/templates/verification_and_failure_modes.md`（声称验证门控）、`../../references/reasoning/argument_frameworks.md`（论证连接判据）、`../../references/templates/handoff-protocol.md`（跨路径字段级规格）。
