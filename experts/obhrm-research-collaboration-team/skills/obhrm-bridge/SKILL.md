---
name: obhrm-bridge
version: 1.0.0
description: OBHRM 概念桥接层（obhrm-bridge）— 四库联动中枢。以「中英双语概念词表」把教材章节、134 理论、599 量表、108 个 R 方法串联成一张网；输入任意组织行为学概念（如「情感」「领导力」），一次返回该概念的教材锚点与定义、理论依据、可用量表与可行的分析方法，供本科生、研究生与学者各取所需。四库各自独立编制，本层以概念为中介实现联动。
---

> **跨技能引用约定**：本文档以逻辑名形式引用兄弟技能（如 `` `skill:obhrm-bridge` ``），各技能的实际目录与入口脚本即 `skills/` 下的同名目录；正文给出的脚本路径为该技能内部的相对路径。

# 概念桥接层（obhrm-bridge）— 四库联动中枢

> 本 skill 是四库联动的**调度中枢**。量表、理论、R 方法三库各自独立，本层以概念为枢纽把它们串成可联动的知识网：**谈任何一个组织行为学概念，都能同时给出"教材怎么讲 / 理论怎么解释 / 量表怎么测 / 数据怎么验"四重视角。**

---

## 一、为什么需要桥接层

教材、理论、量表、R 方法四路知识**各自独立编制**，构念标识体系并不统一——理论侧形如 `affective_events_theory`，量表侧形如 `emotional_exhaustion_scale`，两者无法按标识直接互相关联。

因此本 skill 以**中英双语概念词表**作中介：用户输入一个概念词，先由词表映射到四库中的真实节点，再把教材章节、理论、量表、R 方法一次返回——这正是本 skill 的存在理由。

## 二、资产规模与结构

- **概念数**：107（内容域 91 + 方法域 16）；其中 86 个锚定教材 D1 的章节，方法域概念不设教材锚点
- **目录**：
  - `knowledge/_concept_index.json` — 概念词表（**检索基准**）
  - `knowledge/_bridge.json` — 桥接索引：概念 → 教材章节 / 理论 / 量表 / R 方法
  - `scripts/query_concept.py` — 统一检索入口
- **检索入口**：`scripts/query_concept.py`（纯标准库，零依赖，可从任意工作目录运行）

```bash
python3 scripts/query_concept.py "情感"                  # L1 概念桥接（推荐入口）
python3 scripts/query_concept.py "情感" --full           # 展开：理论四段正文与文献 / 量表条目 / 脚本用法
python3 scripts/query_concept.py "T033"                  # L2 ID 透传
python3 scripts/query_concept.py "领导力" --limit 5
python3 scripts/query_concept.py "正念"                  # L3 未收录 → 全库回退检索
python3 scripts/query_concept.py "情感" --json           # 输出 JSON（供程序消费）
```

## 三、三级检索策略

| 级别 | 触发条件 | 行为 |
|------|----------|------|
| **L1 概念桥接** | 输入命中概念词表 | 一次返回「教材章节 + 理论 + 量表 + R 方法」四库联动结果（首选路径） |
| **L2 ID 透传** | 输入 `S001` / `T033` / `6.1` 等 ID | 直接定位单条记录，`--full` 读全文 |
| **L3 全库回退** | 概念词表未收录 | 并行在理论/量表/R 三库做关键词检索，如实标注为回退结果 |

## 四、匹配规则

- **中文**：关键词子串匹配 `name_zh` / `variable_zh`
- **英文**：词首边界匹配（`\b` + kw）`name_en` / `variable_en` / `construct_id`（下划线按空格处理）
  - `affect` 命中 `affective`、`affect-based`；**不**命中 `disaffect`
- **R 方法**：先取 `r_stages` 指定方法族内标题命中者，不足再补该族代表脚本；方法域概念整族纳入但关键词命中者优先

## 五、与四库的协同关系

```
                    ┌──────────────────────────┐
   用户概念词 ──────▶│  obhrm-bridge（本 skill） │
   （如「情感」）     │   概念词表 → 四库映射     │
                    └────────────┬─────────────┘
         ┌──────────────┬───────┴────────┬──────────────┐
         ▼              ▼                ▼              ▼
 教材（本包上游真源）  theory-library    scale-library   r-analysis
 skills/obhrm-textbook/ob-textbook/  （134 理论）  （599 量表）  （108 R 脚本）
   ch05 情绪与压力    T033 情感事件理论   S015 情感承诺     13.x ESM
   【D1,§5.x】        T034 情感信息理论   S109 情绪耗竭     15.x 多层
```

- **`skill:scale-library`** — 桥接层给出 scale_id 后，用 `query_scales.py <id> --full` 读维度与条目
- **`skill:theory-library`** — 桥接层给出 theory_id 后，用 `query_theories.py <id> --full` 读四段正文与文献
- **`skill:r-analysis`** — 桥接层给出 method_no 后，用 `query_r.py <no> --full` 读脚本门控与用法
- **教材 `skills/obhrm-textbook/ob-textbook/chXX.md`** — 桥接层给出章节锚点后，读原文核对小节编号，标注【出处：D1,§X.Y】（教材已去重，单一真源位于上游 `obhrm-research-base`）

## 六、注意事项

- **词表为准**：概念词表以 `_concept_index.json` 为基准；`_bridge.json` 承载同一份词表并给出其到四库的映射，检索脚本读取此文件。两者词表保持一致。
- **不臆造 ID**：所有桥接出的 `Txxx` / `Sxxx` / `method_no` 均取自各库真实节点。
- **未命中如实报告**：库内无匹配时明确说明"无匹配条目"，**禁止**凭记忆补写量表条目、理论内容或文献出处。
- **教材锚点须核对**：桥接层只给出章节（`ch05`），具体小节编号 `§X.Y` 必须读取 `skills/obhrm-textbook/ob-textbook/chXX.md` 原文确认后方可标注，不得以章节关键词代替。
