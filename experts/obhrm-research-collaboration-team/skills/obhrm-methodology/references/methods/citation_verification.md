# 引用核验协议（Crossref + Retraction Watch）

## 目的

在「不编引用 / 不归观点 / 标注无支撑 / 不超范围」四铁律之外，增加一道**可机检的出处真实性闸门**：任何进入证据矩阵的文献，必须先通过外部注册库核验，再写入正文或参考文献表。

## 三步核验

1. **Crossref 核验（DOI 级）**：凡带 DOI 的文献，用 Crossref API（`https://api.crossref.org/works/<doi>`）回查标题 / 作者 / 年 / 期刊是否一致；不一致即标注「出处待核」，不写入定稿。
2. **Retraction Watch 核验（撤稿级）**：将 DOI / 标题送入 Retraction Watch 数据集（`https://api.retractionwatch.com` 或开放 CSV），命中即标「已撤稿 / 表达式关注」，一律剔除并提示用户。
3. **一致性裁定**：① 通过 ①② → 可引用；② 仅 ① 通过、② 未命中 → 可引用但保留「已查撤稿库」记录；③ 任一失败 → 按四铁律三态标注处置（不编 / 不归 / 待核 / 超范围）。

## 与既有流程的衔接

- 本闸门前置在 `literature-review` 的「补检」环节与 `paper-writing` 的「参考文献生成」环节之前。
- 与 `evidence_retrieval_protocol.md` 并行：evidence_retrieval 管「证据是否真支持主张」，本文件管「出处是否真实存在且未被撤稿」。
- 中文刊（CSSCI / 核心）无 DOI 时，改走 `source-integrity` 的「机构 + 年 + 卷期」人工核验路径，不强行机检。

## 红线

- 机检失败不得静默通过；必须显式标注，交付前由主理人复核。
- 撤稿文献即使曾被高引，也不得作为正面证据。
