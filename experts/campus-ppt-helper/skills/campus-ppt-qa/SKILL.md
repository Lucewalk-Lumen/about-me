---
name: campus-ppt-qa
description: "QA playbook for the Campus PPT Helper Team's inspector. Consult it for four-dimension QA (task completion / instruction compliance / fact discrimination / rule compliance), per-item FAIL/WARN/PASS, the refine-reverify loop, deck gotchas and batch/multi-chapter reconciliation — for teaching / thesis-defense / internship / Party-building decks (教学/答辩/实习/党建党政). Triggers on: 质检, 验收, 四维, 质量, 检查, 合规, 校验, 精修复验, 字号检查, 配图检查, 案例核查, 出处核查, 版式检查, 出片避坑, 批量对账, 多章出片, QA-lite, 轻量质检."
---

# 校园演示帮手团 · 四维质检（Campus PPT QA）

本 Skill 是「校园演示帮手团」**质检员**的专业包。目标只有一个：**逐项验收、不通过就精修复验**——任务完成度 / 指令遵从性 / 事实辨别性 / 规则遵从性四维逐项给 Expectation/Current/Severity（FAIL|WARN|PASS），驱动「fail → refine → re-verify」闭环；**编造数据零容忍**。

## 使用原则

| 原则 | 说明 |
|------|------|
| **先判模式，再选档位** | 轻模式走 **QA-lite**（仅查任务完成度 + 事实辨别性，版式审美判 WARN 不阻塞）；重模式走**四维全检**（保留品牌合规底线） |
| **门禁按时机跑** | 制作员出片后自跑几何 + 字数门（退出码 0 才回传）；QA-lite 以该两门为底线；页型门、视觉门与逐页出图归重模式四维全检；任一断言红 → 定位到页 / 断言编号 → 经主理人回制作员精修 → 复跑全部门禁 |
| **逐项可复算** | 字号层级可追溯模板实测值、配色可追溯真实提取、版式轮换可逐页核对、视觉门禁看退出码；无逐页出图不得声称排版通过 |
| **事实辨别零容忍** | 配图来源可查（P1–P5）、案例出处齐全（L1–L3）、图表数据可回溯；编造主体/模糊来源即 FAIL |
| **复验用全新路径冷加载** | `slidep screenshot` 对同一路径命中缓存，用旧路径复验等于没验 |
| **批量任务必对账** | 多章/批量出片做数量合计 + 产物 md5 对账 + 显式补投样章 |

## 参考索引（先读后用，禁止凭记忆编造）

| 文件 | 何时查阅 |
|------|----------|
| `references/quality-evaluation-standard.md` | **四维质检标准**：任务完成度/指令遵从性/事实辨别性/规则遵从性检查项、阈值与「精修→复验」闭环 |
| `references/runtime-gate-thresholds.md` | **运行时门禁阈值标准**：几何门/字数门判据全文 + 页型门/视觉门交叉引用 + **四门执行时机矩阵与 FAIL 流转入口** + 四门降级人工核对流程 |
| `references/deck-gotchas.md` | **出片避坑清单**：模板沿用、密度/多样性、图片、溢出、预览——出片前后逐项排查；`slidep` 同路径首调必失败须预热等坑位 |
| `references/batch-qa-reconciliation.md` | **多章/批量出片编排与对账**：样章锚点、并行铺开、逐章质检、数量/md5 对账 |

## 与其它 Skill 的衔接

字号层级验收见 `campus-ppt-make` 的 `body-typography-standard.md` §八；版式与视觉美化验收见 `campus-ppt-make` 的 `visual-execution.md` §九（十四条断言）与 `campus-ppt-design` 的 `layout-selection.md`（轮换规则）；配图 / 案例核查见 `campus-ppt-media`；模式档位判定见 `campus-ppt-core` 的 `interaction-protocol.md` §六（轻/重模式分流）。
