# 深度蒸馏示例：BERT: Pre-training of Deep Bidirectional Transformers

> [!] **示例说明**：本示例为**通用形态**（NLP 论文演示），用于展示「三层六模块深度蒸馏模型」的输出样式（基础 M1–M3 / 洞察 M4–M5，衔接 M6 在报告生成后执行、不渲染为静态章节）。**OBHRM 语境版列为后续增强**。
>
> 示例内容源自公开论文 BERT（arXiv:1810.04805 / NAACL 2019），其中引用的文献与 DOI 均为真实来源，**未虚构任何文献**。

> 蒸馏日期：2026-05-06 | 原始来源：arXiv:1810.04805

---

## 三层六模块深度蒸馏模型 · 层归属说明

| 层 | 模块 | 对应章节 |
|----|------|----------|
| 基础层 | M1 结构化元数据 / M2 逻辑骨架还原 / M3 引用文献网络 | M1 / M2 / M3 |
| 洞察层 | M4 批判性思考 / M5 知识图谱关联 | M4 / M5 |
| 衔接层 | M6 衔接（报告生成后询问是否衔接至证据-论点映射） | 报告生成后执行，demo 不渲染 |

---

## M1 · 结构化元数据（基础层）

| 字段 | 内容 |
|------|------|
| 标题 | BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding |
| 作者 | Jacob Devlin, Ming-Wei Chang, Kenton Lee, Kristina Toutanova |
| 机构 | Google AI Language |
| 来源 | NAACL 2019 |
| 年份 | 2019 |
| DOI | 10.18653/v1/N19-1423 |
| 标签 | #NLP #预训练 #Transformer #语言模型 |
| 研究方法 | #实证 #实验研究 #消融实验 |

---

## M2 · 逻辑骨架还原（基础层）

### 论证链条

**问题**：已有语言模型（ELMo, GPT）都是单向的，无法同时利用左右上下文信息

**理论**：双向编码应该能学习到更丰富的语义表示

**方法**：
1. Masked Language Model (MLM) — 随机遮蔽 15% 的词，让模型预测
2. Next Sentence Prediction (NSP) — 判断两个句子是否连续

**实验**：在 11 项 NLP 任务上验证，全部达到 SOTA

**结论**：双向预训练显著提升下游任务性能

---

## M3 · 引用文献网络（基础层）

### 核心参考文献
1. Vaswani et al. "Attention Is All You Need." NeurIPS, 2017.
2. Peters et al. "Deep Contextualized Word Representations." NAACL, 2018.
3. Radford et al. "Improving Language Understanding by Generative Pre-Training." 2018.

---

## M4 · 批判性思考（洞察层）

### 研究缺口
- MLM 的遮蔽率（15%）选择缺乏理论依据
- NSP 任务的必要性存疑（后续 RoBERTa 证明可以去掉）

### 局限性
- 预训练和微调之间存在不一致性（MLM 中见过 [MASK] token，微调时没有）
- 大模型训练成本高

### 后续方向
- 探索更高效的预训练目标
- 研究模型压缩方法（蒸馏、剪枝）

---

## M5 · 知识图谱关联（洞察层）

### 前置知识
- Transformer 架构
- 自注意力机制
- 迁移学习概念

### 同类对比
| 模型 | 方向性 | 预训练目标 | 参数量 |
|------|--------|-----------|--------|
| ELMo | 双向浅层 | Language Model | 94M |
| GPT | 单向深层 | Language Model | 117M |
| BERT | 双向深层 | MLM + NSP | 110M/340M |

---

## M6 · 衔接（衔接层）

> 本 demo 为静态示例，不渲染衔接产物。实际使用中，深度蒸馏报告生成后，会询问是否衔接至温书恒 L3 证据-论点映射（`evidence_claim_map.json`，即 G2 证据映射门输入），用户可确认或取消。

---

> [!] **示例说明（重申）**：本示例为**通用形态**（NLP 论文演示），用于演示三层六模块深度蒸馏模型的输出样式；**OBHRM 语境版列为后续增强**。文中所涉文献引用与 DOI 均为真实来源，未虚构任何文献。
