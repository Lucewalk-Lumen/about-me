---
name: mplus-syntax-lab
description: Mplus syntax explanation, generation, and .inp code review — command blocks, model skeletons, estimator selection, and a zero-dependency static checker with a 16-rule syntax-layer ruleset and green/red dual-proof self-test.
description_zh: Mplus 语法讲解、语法生成与 .inp 纠错：命令段速查、模型骨架、估计法选型，并配一套零依赖静态校验脚本（16 条语法层规则，含绿/红双向证明自测）。
description_en: Mplus syntax explanation, generation, and .inp code review — command blocks, model skeletons, estimator selection, and a zero-dependency static checker with a 16-rule syntax-layer ruleset and green/red dual-proof self-test.
display_name: "Mplus 语法实验室"
display_name_en: "Mplus Syntax Lab"
category: "学术研究"
version: "1.0.0"
author: Xing Bu
---

# Mplus 语法实验室（Syntax Lab）

承载 **M1 语法讲解与生成** 与 **M2 `.inp` 纠错** 两个模块。所有讲解与范例均为**本方自撰**。

---

## 一、触发词

- 讲解类：「这段语法什么意思」「逐段解释」「`BY` / `ON` / `WITH` 什么区别」「`%WITHIN%` 怎么用」
- 生成类：「帮我写一段语法」「给个 CFA / 中介 / 多层 / LPA 的示例」「这个设计怎么写成 `.inp`」
- 纠错类：「帮我看看哪里写错了」「语法报错了」「检查一下这个 `.inp`」

**不触发本技能**：贴 `.out` 问结果（→ `mplus-output-clinic`）；问「该用什么模型」（→ `mplus-method-advisor`）。

---

## 二、讲法约定（**先读这段**）

1. **按命令段逐段讲，每段注明行号范围**。段序以文件实际顺序为准——**Mplus 不强制段序**，不要按「标准顺序」纠正用户。
2. 段名可以是 `MODEL C1:` `MODEL G2:` `MODEL CB:` `MODEL PRIOR:`（**单数**）等**合法变体**；`MODEL <标签>:` 的标签**不受限**。**不要**把变体判为拼写错误。
3. `TITLE` 是自由文本段：**不需要分号**，可长达数千行（官方最长 2661 行）。**段内出现的 `Sources:` 一类冒号行是正文**，不做段名判定。
4. 段名与内容**可同行**（`DATA:\tFILE IS x.dat;`）——这是正常写法，不是格式问题。
5. 变量清单关键字接受**缩写与单复数**：`USEV`(42 份) · `USEVAR`(4) · `USEVARIABLES`(51) · `USEVARIABLE`(1) 全部合法。**不得**把 `USEV` 说成错别字。
6. **一条语句可跨任意多行**。因此「语句中段漏分号」**在无完整语法分析时不可判定**——这类问题只能提示「请核对分号完整性」，**不得**当确定结论报出。

---

## 三、生成的硬约束

| 项 | 上限 | 说明 |
|---|---|---|
| 骨架行数 | **≤ 120 行 / ≤ 4 KB** | 官方绝大多数示例 ≤ 100 行 |
| **变量名长度** | **≤ 8 字符** | **语法约束**：官方 519 份 `.inp` 展开 `NAMES` 后长度 1–8、**最大恰为 8**、**超限 0 个** |
| **行宽** | **≤ 90 字符** | 超限会被截断。⚠ 官方 6 份超限文件中**只有 4 份报出**该警告 → 只是提示，不承诺必报 |
| 单次引用范例 | **≤ 3 个** | 每个附案例 ID |
| 必需段 | `TITLE` / `DATA` / `VARIABLE` / `ANALYSIS` / `MODEL` / `OUTPUT` | 缺段会报 `BLOCKER` |

**不生成**需真实数据才能定的值：起始值、类别数、`STARTS`。→ **给决策规则，不给唯一值**。

**Tier 降级声明（按实测分层，**不得凭印象表述**）**：参照精度由「带结果的官方 example 份数」决定 ——
**≥25 = Tier A 充足 · 10–24 = B 可用 · 3–9 = C 偏薄 · ≤2 = D 极薄**。

| 本技能常生成的方法 | Tier | 带结果 example | 生成时须说的话 |
|---|:---:|---:|---|
| CFA / SEM / 多层 SEM / 增长 / LPA | **A** | 113 / 32 / 55 / **25** | 无需降级声明 |
| 类别结局、LCA、GMM、缺失、LTA | B | 79 / 24 / 17 / 17 / 16 | 无需降级声明 |
| 已知类别、计数、生存 | C | 9 / 7 / 6 | 附「可对照的官方示例有限」 |
| **`XWITH`（潜变量交互）** | **D** | **2** | **必须明示降级**：`本类带结果的可对照示例仅 2 份（ex5.7 / ex5.13）` |

> ⚠ **LPA 不属降级项**（实测 25 份 example 全部带 `.out`）。请**不要**再对 LPA/LCA/GMM 一律套用降级话术。

全表与案例 ID 见 `../../mplus-method-advisor/references/41-selection-tree.md` §二。

---

## 四、纠错流程

**第一步：跑静态校验**（零依赖，不运行 Mplus）

```bash
python3 scripts/check_inp.py <file.inp>
python3 scripts/check_inp.py <file.inp> --dict <dict.json>   # 扩展数据层
python3 scripts/check_inp.py <file.inp> --json
python3 scripts/check_inp.py <file.inp> --mplus-version 6    # 版本敏感规则
```

**第二步：把发现按四要素整理** —— 每条含 **行号 + 问题类型 + 原因 + 修法**，并给改正后 diff。

**第三步：把脚本给不出的说清楚**。校验器**只覆盖语法层**，必须原样转述覆盖率：

> 官方实测警告共 **62 类 / 39 种消息 / 219 条**。本脚本已实现规则覆盖
> **14/62 类（22.6%）· 2/39 种消息（5.1%）· 30/219 条（13.7%）**；
> 另有 **9 种消息**语法层可预判但尚未实现；数据层与运行层（约 28 种消息）**未覆盖**。

> ⚠ **三个口径差别极大（5.1% ↔ 28.2%），引用时必须写明口径**，只抛一个百分比即为不合格表述。
> **禁止**把静态检查通过说成「能跑通」——收敛性、拟合优度、参数合理性**均不在覆盖内**。

**第四步（可选）：让扫描器自证有效**

```bash
python3 scripts/selftest_inp.py --pkg <包根>
```

绿向：519 份未改动官方 `.inp` 必须 **0 BLOCKER / 0 WARN**；
红向：17 个故障注入器必须 **100% 命中**；反向：版本敏感规则在错版本下**不得触发**。
> **全绿 ≠ 有效**：必须绿向通过**且**红向命中，才能说明扫描器真的会报警。

---

## 五、规则表（16 条语法层）

| ID | 级别 | 规则 |
|---|---|---|
| L01 | BLOCKER | 未知命令段名（拼写错误） |
| L02 | BLOCKER | 语句缺分号（整段无分号 / 段末语句缺分号） |
| L03 | WARN | 变量名超过 8 字符 |
| L04 | WARN / INFO | 行宽超过 90 字符（命令行超限 = WARN；`TITLE` 超限 = INFO，因触发不可预测） |
| L05 | WARN | `%WITHIN%` / `%BETWEEN%` 未配对 |
| L06 | BLOCKER | `CLASSES` 与 `TYPE=MIXTURE` 不一致 |
| L07 | BLOCKER | `MODEL` 引用未在 `NAMES` 声明的变量 |
| L08 | BLOCKER | `NAMES` 缺失 |
| L09 | BLOCKER | `DATA` 段缺 `FILE IS` |
| L10 | WARN / INFO | `TECH8` 与 `TYPE` / `ESTIMATOR` / `ALGORITHM` 组合不可用（**版本敏感**） |
| L11 | BLOCKER | `MODINDICES` 与 `ESTIMATOR=BAYES` 冲突 |
| L12 | WARN | `SAMPSTAT` 与全类别结局冲突 |
| L13 | BLOCKER | `BOOTSTRAP` 与 `ESTIMATOR` 组合不可用 |
| L14 | INFO | `MODEL INDIRECT` / `CONSTRAINT` / `PRIORS` 段为空（**合法**，仅提醒） |
| L15 | BLOCKER | `USEVARIABLES` 与 `NAMES` 冲突（引用未声明变量） |
| L16 | INFO | 段序罕见反序（**Mplus 不强制段序**；只报官方语料仅 1/519 例的三对反序） |

**数据层（仅 `--dict` 启用）**：D01 簇内无变异 · D02 全变量缺失观测 · D03 分组变量缺失 ·
D04 连续变量实为常数 · D05 `NAMES` 变量数与数据列数不符。

### L10 的版本口径（**最容易被答错，必须按此回答**）

`TECH8` 可用性**不是版本开关，而是组合条件，且未被完全解出**。官方请求 `TECH8` 的 `.out` 实测：

| 版本 | 请求 | 实际报「不可用」 |
|---|---:|---:|
| `6.1` | 27 | **6** |
| `6.11` | 4 | 0 |
| `8` | 67 | 0 |
| `8.8` | 188 | 0 |

**v6.1 内还有 2/27 例外**：`TYPE = EFA 3 3` 与 `TYPE = BASIC` **未报**，而 `EFA 4 4` **报**。
**语料无 Mplus 7 样本** → 标 **【缺失】**。

**禁止表述**：「写 `TECH8` 一定会报警告」——此话在 291 份样本中**错 284 次**。

---

## 六、参考分片

| 文件 | 内容 |
|---|---|
| `references/11-command-blocks.md` | 命令段速查：段名全家（含合法变体）、缩写、同行写法、`TITLE` 特性、数据子段 |
| `references/12-model-syntax.md` | 各模型语法骨架（CFA / 中介 / 调节 / 多层 / 增长 / 混合 / 贝叶斯 / 蒙特卡洛）+ 规则编号对应的写法要点 |
| `references/13-estimator-guide.md` | `ESTIMATOR` / `TYPE` / `ALGORITHM` 选择口径与兼容矩阵 |
| `templates/inp-skeletons/` | 可直接改用的 `.inp` 骨架（`cfa` / `mediation` / `twolevel` / `lpa` / `lgm` / `gmm` / `bayes`） |
| `scripts/check_inp.py` · `selftest_inp.py` | 静态校验与双向证明自测 |

---

## 七、收尾（**固定五段**）

```text
【结论】
【依据】  每条带 src（案例 ID / 语料口径 / 手册锚点）
【动作】  可执行、可验证的下一步
【边界】  验证状态 STATIC_CHECKED（本包不运行 Mplus）+ 未覆盖：收敛 / 拟合 / 参数合理性
【覆盖】  62 类 / 39 种消息 / 219 条；已实现 14 类 · 2 种消息 · 30 条（三口径并列）
```

**禁止**在本技能输出「已运行验证」类表述。
