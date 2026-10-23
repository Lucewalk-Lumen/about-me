---
name: campus-ppt-make
description: "Official-skill build playbook for the Campus PPT Helper Team's maker. Consult it for tencent-pptx / tencent-local-office-edit / WPS routing, template sourcing from Tencent Docs, template color/typography extraction, body typography T1-T7, in-page A/B/C layout, visual-assertion gate and external-dependency precheck — for teaching / thesis-defense / internship / Party-building decks (教学/答辩/实习/党建党政). Triggers on: 制作, 生成, 出片, tencent-pptx, WPS, tencent-local-office-edit, 模板, 广财模板, 党政模板, 套模板, 模板保真, 母版保真, 字号, 字号层级, 正文样式, DESIGN.md, STORY.md, 视觉美化, 依赖预检, 连接登记, 外部依赖, 腾讯文档模板源, 模板库导出, check_visual."
---

# 校园演示帮手团 · 官方技能制作（Campus PPT Make）

本 Skill 是「校园演示帮手团」**制作员**的专业包。目标只有一个：**委托官方技能真实出片**——本团不写 Python/JS 生成脚本，PPT 一律由官方 `tencent-pptx`（风格重绘）或 `tencent-local-office-edit`（模板保真，`slide_duplicate_slide` 深拷贝模板页）生成；**出片第 0 步先过依赖预检，未过不得出片**。

## 使用原则

| 原则 | 说明 |
|------|------|
| **依赖预检第 0 步（强制）** | 按四张连接卡逐项预检官方技能 / 编辑器 / browser-skill / 腾讯文档模板库，**四卡未全过不得开始出片**（轻模式按 L0 豁免部分卡） |
| **两条路径分清（默认 B）** | 路径 B 模板保真（深拷贝模板页、继承母版视觉，**默认**）vs 路径 A 风格重绘（tencent-pptx 提取风格、空白稿重画，兜底）；不确定走哪条 → 回主理人过 Skill 路由门 |
| **视觉美化必须真调用** | 交付物须含 `STORY.md`（逐页五字段）+ `DESIGN.md`（设计分支 + A/B/C 三区 px + 密度/留白/配色硬指标），缺任一份 = 未调用 = FAIL |
| **配色 / 字号不拍脑袋** | 色板读模板 `theme1.xml` 真实提取、禁编造 hex；字号按 T1–T7 取该模板实测值（附录 A） |
| **版面须过可复算门禁** | 十四条视觉断言 A1–A14 + 备注门 AN 逐页通过（伴生 `check_visual.py` 退出码 0）；留痕 ≠ 合规 |
| **出片后自跑两道门** | 几何门 + 字数门退出码 0 才回传主理人（建造侧自检，不是四维质检）；判据全文与执行时机矩阵见 `campus-ppt-qa` 的 `runtime-gate-thresholds.md` §〇/§二/§三 |
| **模板唯一运行时源** | 15 套模板经腾讯文档「演示模板库」四级自适应取件（缓存 → 直导 → 克隆导出 → 人工另存），不臆造路径 |

## 参考索引（先读后用，禁止凭记忆编造）

| 文件 | 何时查阅 |
|------|----------|
| `references/official-skill-routing.md` | 制作员如何路由到 tencent-pptx / WPS / 本地 office，交给官方技能的精确指令清单；区分风格重绘（路径 A）与模板保真（路径 B）；**§二 Skill 路由门三态判定** |
| `references/tencent-docs-template-source.md` | **内置模板唯一运行时源**：腾讯文档「演示模板库」四级自适应取件、15 套云端权威清单与 file_id 快照、选型规则、降级口径 |
| `references/template-application.md` | 选模板后如何**真实取色**：读 `theme1.xml` 提取真实色板/字体/版式；含路径 A / 路径 B 两条出片口径的最小可执行步骤；**§六 色板速查** |
| `references/body-typography-standard.md` | **正文样式与字号层级**：T1–T7 七级规范、**实测字号表（附录 A，15 套内置）**、行距/段距、中英混排字族、容量与换行预算、`slide_set_text_property` 回填规范 |
| `references/visual-execution.md` | **视觉执行（执行侧）**：视觉美化真调用与分支路由（academic/consulting/redgold）、A/B/C 三区页内排版、**十四条视觉断言 A1–A14 + 备注门 AN**、伴生门禁 `check_visual.py`、质检清单 |
| `references/external-dependency-registry.md` | **外部依赖连接登记**：24 项外部依赖总表 + **五张预检连接卡** + 模板获取流程、未连接引用定级 P0–P3、门禁 C8/C9/C10 判据 |
| `references/dependency-verification-log.md` | **连接核验留证日志**：2026-10-07/08 全链实测记录 + 2026-10-13 发布前门禁补记；换机重测后在此追加 |

## 与其它 Skill 的衔接

版式规划（11 种版式库 / 轮换规则 / 逐页角色节奏）见 `campus-ppt-design` 的 `layout-selection.md`；配图 / 案例落位标准见 `campus-ppt-media`；页型契约见 `campus-ppt-design` 的 `page-content-contract.md`；口径基线以 `campus-ppt-core` 为准。
