---
name: ppt-maker
version: 1.1.1
description: >
  教学课件 / 演讲文稿制作与修改：把教案、大纲或课程内容生成可演示文稿。
  默认零依赖单文件 HTML（自包含、免装 PowerPoint、S 键双屏演讲者模式 + T 键 13 主题换肤、可导出 PDF）；
  需要 .pptx / .pdf 等传统办公格式时，优先委托平台已安装的官方办公技能出片；平台办公技能不可用时可用包内 `build_pptx.py` / `md_to_docx.py` 离线生成。
  Use when 用户要 做PPT / 做课件 / 演讲文稿 / 幻灯片 / slides / HTML 演示 / 带演讲备注 / 上台汇报 / 双屏演示。
---

> **# 课件/演讲文稿生成（ppt-maker）

> **归属**：领域技能层——课件制作专家（ppt-maker）

## [必读] 办公文档出片路由（平台自带技能优先）

WorkBuddy 已内置并启用官方办公技能，凡涉**传统办公格式出片**，一律按下表路由，**不要**自行造轮子：

| 需求 | 首选（平台自带，已安装） | 本包角色 |
|------|------------------------|---------|
| 生成 / 编辑 `.pptx` | `tencent-pptx` 技能 | 只提供教学设计、逐页文案、版式与配色规范；`.pptx` 由自带技能出片 |
| 生成 / 编辑 `.docx` | `tencent-docx` 技能 | 同上 |
| 生成 / 编辑 `.xlsx` | `sheetagent` 技能 | 同上 |
| HTML 单文件课件（演讲、双屏、动画、浏览器内编辑） | **本包 `build_deck.py`（主路径）** | 自带技能无此形态，本包负责 |

**硬规则**：
1. 用户要 `.pptx` / `.docx` / `.xlsx` → 先确认平台自带技能可用，直接委托出片；本包 `build_pptx.py` / `md_to_docx.py` 作为离线生成路径：平台办公技能不可用时使用。
2. 用户只要「演示 / 讲课 / 汇报」未指定格式 → 走本包 HTML 主路径（零依赖、免装 PowerPoint）。
3. **禁止**在自带技能已可用时仍要求用户 `pip install` 办公类依赖；`python-pptx` / `python-docx` 相关依赖**不再纳入 setup 强制安装**，缺依赖时提示委托自带技能即可。

> **[注意] 绝不强制下载 LibreOffice**：本包**不下载** LibreOffice。需要原生 `.pptx` 时，**优先复用用户本机已装的 WPS / 微软 PowerPoint**；仅在**无任何办公二进制可用**时才回退 `build_pptx.py`（python-pptx 离线生成）或委托平台内置 `tencent-pptx` 技能。二进制探测统一走 `skills/ppt-maker/scripts/office_bin.py` 的 `find_office_bin()`（尊重 `OFFICE_BIN` 环境变量，命中即返回，**绝不下载**）。

> 设计采用「制作 make + 修改 edit」双线：
> - **制作线（make）**：从零 / create、PPT 转换 → 单 HTML；**视觉风格发现（3 预览选风格）**、**预设系统（每套含 Layout 散文 + Signature Elements + Typography + Colors）**、零依赖 1920×1080 固定舞台。
> - **修改线（edit）**：**完整浏览器内编辑运行时**；支持增强 / 编辑已有 deck、PPT·PDF 转换重编辑。
> 结论：**HTML 单文件为默认主路径**，传统 `.pptx` 为受控备选。

## 双线总览

| 线 | 来源 | 解决什么 | 触发 |
|----|------|----------|------|
| **make（制作）** | 制作线 | 从零生成 / PPT 转换 → 单 HTML 演示 | "做课件/PPT"、"把大纲做成幻灯片"、"PPT 转网页" |
| **edit（修改）** | 修改线 | 增强 / 编辑已有 deck、PPT·PDF 重编辑 | "改一下这份课件"、"给已有幻灯片加页/改字"、"把 pptx/pdf 变成可编辑网页" |

> 两条线共享：风格预设系统（`references/style-presets.md`）、固定 1920×1080 舞台、编辑运行时底座（`references/editor-runtime.md`）。`ppt-maker` 专家按用户意图选择线；`course-builder` Phase 4 经 Skill 工具显式加载本技能（不依赖触发词）。

## 方案决策流（HTML 优先，传统 .pptx 备选，编辑可选）

```
1. 用户是否要「改已有 deck / 编辑现有幻灯片」？
   ├─ 是 → edit 线（edit_deck.py / 浏览器内编辑运行时）
   └─ 否 ↓
2. 用户/上游是否显式要求 .pptx / PowerPoint？或环境强制 .pptx（LMS / 纯 PPT 教室）？
   ├─ 是 → 传统方案（build_pptx.py，python-pptx）
   └─ 否 ↓
3. 默认 → make 线（build_deck.py，零依赖单 HTML）
```

---

## 制作线（make）工作流

制作线（make）工作流（Phase 0–6）：

### Phase 0 — 模式检测
- Mode A 新演示 → Phase 1；Mode B PPT 转换 → `extract_pptx.py` → Phase 1 补风格；Mode C 增强已有 deck → 转 **edit 线**。

### Phase 0 — 快速通道（教案直传，跳过五要素）

> **触发条件**（三选一即生效，跳过 Phase 1 五要素 + Phase 2 风格发现，进入 Phase 3）：
> 1. 用户**粘贴完整大纲 / 教案**（含 `# 标题` 与 `## 内容页` 列表/表格/图片）
> 2. 用户**提供 .md / .txt 文件**作为大纲源
> 3. 用户说「**直接做**」/「**快速出**」/「**按这个大纲**」

- **默认预设**：`academic-light`（生成后按 **T 键** 13 套预设无白屏换肤现场定夺，**不阻断**）
- **默认页数**：由大纲中 `##` 数量自动决定（无需追问）
- **默认风格发现**：跳过 3 预览阶段（运行时换肤已覆盖"现场选型"诉求）
- **必经检查**：Phase 3 后**必跑 `--check`**（输出整改建议，**不阻断 build**——见 Phase 3 第 3 步）
- **何时回到标准 Phase 1**：用户**主动**要求改风格 / 改受众 / 改交付形态时

> 快速通道下完整流程：`md2spec.py 教案.md -o deck.json` → `build_deck.py --spec deck.json --out 课件.html --dist 课件.dist.html --check` → 浏览器内 `T` 键换肤定夺。

### Phase 0b — 主题直传（只给主题，零追问全自动）

> **触发条件**：用户只给一个**主题词**（如「帮我做个关于组织行为学的课件」「介绍马斯洛需求层次」），没有大纲、没有文件、没有页数——连 Phase 0 的「粘贴大纲」都不满足。
> **这是区别于 Phase 0 的第三档快速通道**：Phase 0 仍需用户供大纲/.md；Phase 0b 连大纲都没有，由 LLM 全自动补全。

**执行序列（LLM 自动完成，不追问用户）**：
1. **自建 Action Title 大纲**：基于主题，用金字塔原理生成 8-12 页大纲（首页 title + 2-4 个 section + 内容页 bullets/steps/chart + closing），写入临时 `大纲.md`（每页标题即结论）。
2. **默认参数**：预设 `academic-light`（教学场景默认；汇报/分享场景可改用 magazine-ink）、页数 10±2、受众「高校课堂」〔待确认〕。
3. **md2spec 转 spec**：`md2spec.py 大纲.md -o deck.json --course <主题>`。
4. **build + 门禁**：`build_deck.py --spec deck.json --out 课件.html --dist 课件.dist.html --check`；若 FAIL 按整改建议调整后重跑（不阻断生成，但未达 0 FAIL 不得交付）。
5. **交付标注**：产物内标注〔待确认〕项（受众/页数/风格），用户可一句话改（「换靛蓝瓷」「加到 20 页」）→ 重跑。

**可直接套用的提示词模板**：
```
请用 ppt-maker 为主题「____」制作一份 HTML 教学课件。
要求：先按金字塔原理自建 Action Title 大纲（8-12 页）；默认 academic-light；
生成后跑 --check 验收；交付 deck.html + dist 演示版；缺省参数标注〔待确认〕。
```

> 边界：Phase 0b 适合「快速出初稿」；用户对内容有强要求（指定数据/案例/章节）时降回 Phase 1 五要素确认。

### Phase 1 — 内容发现（一次性问齐五要素）
- **五要素缺一不可**：1. 受众（授课学生 / 汇报领导 / 同行 / 客户，决定语气与深度）；2. 目标（听完能怎样 / 要决策什么）；3. 页数（或时长）；4. 主题（或「帮我选」，给出 2–3 个候选）；5. 交付形态（教室投影 / 线上分享 / 是否必须 .pptx）。
- 用户已提供大纲 / 资料时跳过重复提问，直接确认缺失要素。
- **澄清上限 2 轮**：仍缺项则按合理假设生成，并在交付物中标注〔待确认〕，不无限追问。
- 密度确认沿用 Purpose / Length / Content / Density 四问；缺内容时与用户共建大纲（Action Title + 要点），遵循 `references/ppt-design-guide.md`。
- 可直接套用提示词模板（受众 / 目标 / 页数 / 主题 / 交付形态 + 大纲）：

```
请使用 ppt-maker，把以下大纲制作成 N 页 HTML Deck。
受众：____；目标：____；风格：____（或「帮我选」）；比例：16:9。
要求：每页只表达一个结论（Action Title）；图表标注口径与单位；
所有讲者补充写入 notes（正文不出现讲者提示）；交付：deck.html + dist 演示版 + 验收报告。
[粘贴大纲]
```

### Phase 2 — 风格发现（show, don't tell）
- 基于目的 / 受众 / 情绪 / 密度，**生成 3 个单页风格预览**（见 `references/style-presets.md` 的 3 预览组合规则：1 安全预设 + 1 大胆模板 + 1 wildcard）。
- 预览须像真实首页（禁渲内部工作流文本），存风格预览目录，自动打开。
- 用户选 A/B/C/Mix；Mix 追问细节。选定后读 `references/style-presets.md` 对应预设的 **Layout 散文 + Signature Elements**（不止 `:root` 颜色），实现标题页与内容页差异化（生成器已按预设输出差异化装饰，见 `build_deck.py` 的 `preset_deco`）。
- **快速换肤**：也可只生成 1 份，播放中按 **T 键**在 13 套预设间无白屏循环切换现场选型（见「运行时能力」）。

### Phase 3 — 生成（零依赖单 HTML）
- 读 `references/html-deck-spec.md` 技术约束（固定 1920×1080 舞台、`.active`/`.visible` 切页禁 `display:none`、prefers-reduced-motion、禁外部 CDN 字体、notes 不可见契约）。
- `$VENV_PY skills/ppt-maker/scripts/build_deck.py --spec deck.json --out 课件.html` —— 单文件自包含，内联 viewport CSS + 编辑运行时。
- **双产物（推荐）**：`--dist 课件.dist.html` 同时产出剥离编辑 UI 的演示版，对外分发用 dist 版，编辑源留档。
- **验收门禁（必跑）**：`--check` 输出逐页验收报告（信息密度 / 字号 / 对比度 / 溢出）。**`--check` 不阻断 HTML 生成**（它只是门禁报告，不改 `build_deck` 行为；失败时按 4 维度分组给出整改建议：密度 / 对比度 / 字号 / 溢出，整改后重跑 `--check`），但**未达 0 FAIL 不得交付**——交付门槛见 Phase 5–6。退出码为 1（脚本侧可被 CI 检测），**用户/Agent 层不需见红就放弃生成**。

**两种内容入口（二选一）**
- **课型骨架（结构优先）**：`build_deck.py --template theory-lecture --duration 90 --spec-out 骨架.json` 展开 6 套课型模板（theory-lecture / seminar-discussion / lab-instruction / project-based / flipped-class / review-summary）的占位页面序列（页数按 90min 基准随 duration 缩放），再按教案逐页填充 Action Title 与要点。
- **Markdown 大纲（内容优先）**：`python3 scripts/md2spec.py 教案.md -o deck.json --course 课程名` 把 md 大纲直接转 spec。映射：`#`=title/section、`##`=内容页、列表=要点/步骤、`>`=notes、表格三行起→table、`![alt](src)`→image、代码块标注 chart→chart、`- 左 || 右`→two-col。
- **合并入口（结构+内容组合）**：`python3 scripts/merge_spec.py 骨架.json 内容.json -o 合并.json` 把 `--template` 骨架与 `md2spec` 内容合并（骨架占位页被内容覆盖，多余内容页追加；`--prefer content` 换优先级）。
- 两者可组合：`--template` 定结构 → `md2spec` 供内容 → 合并到 spec 后 build。

### Phase 4 — PPT 转换（可选）
- `python3 scripts/extract_pptx.py <in.pptx> <out_dir>`（需 python-pptx）→ 抽取文本 / 图 / 备注 → 进 Phase 2 选风格 → Phase 3 生成，保留原文 / 图 / 顺序，备注转 HTML 注释。

### Phase 5–6 — 交付 / 导出
- **验收门禁（交付门槛）**：跑 `build_deck.py --check` 并随交付物给出报告（密度 / 字号 / 对比度 / 溢出逐项）；**0 FAIL 方可交付**（`--check` 不阻断生成，只作交付门槛，与 Phase 3 的说明一致）。

  **交付前确定性门禁（必跑）**：成稿交付前运行 `python skills/deai-rules/scripts/deai_preflight.py <成稿路径>`，须 PASS；与 `deai-rules` 五维自评（≥45）共同构成 quality 门禁，未 PASS 不得标记为交付物（规则见 `skills/deai-rules/SKILL.md`）。
- 浏览器打开走查：逐页检查 16:9 下截断 / 重叠 / 小字号 / 图例 / 数字精度 / 页面密度；试 ←/→/Space、F 全屏、S 演讲者模式、T 换肤、E 编辑、P Pages；投屏分辨率与离线（断网）实测。
- 对外分享前脱敏：移除客户名称、样本明细、账号、Token、内部 URL 与截图敏感信息。
- 可选无头浏览器导出 PDF：打开 `课件.html` 后按 `Cmd/Ctrl+P` →「另存为 PDF」（保留 T/S 键运行时能力；打印样式已内联 `@media print`，无需外部工具），或部署为在线链接。

---

## 修改线（edit）工作流

修改线（edit）运行时与三条场景：

### 场景 A — 新建可编辑 deck
同 make 线 Phase 1–3，但生成物内嵌完整编辑运行时（默认可编辑）。

### 场景 B — 增强 / 编辑已有 deck（Mode C）
- 读取已有 HTML deck，**先数元素、对照密度限制**再改；加图 `max-height: min(50vh,400px)` 满则拆页；加文 ≤4–6 点超则拆续页；改后验证 `.slide` 的 `overflow:hidden`、新元素 `clamp()`、视口适配。
- 用 `edit_deck.py` 或直接浏览器内编辑（见运行时）：拖拽 / 缩放 / 增删对象、Pages 侧栏重排删页、+New Page 插空白页。

### 场景 C — PPT·PDF 转换重编辑（Mode B）
- PPTX：`extract_pptx.py`；PDF：`extract_pdf.py`（需 pymupdf，可选 `--raster-if-empty`）→ 均出 `extracted-slides.json` + `assets/` → 补风格 / 编辑范围 → 生成可编辑 HTML。

### 编辑运行时契约（必读 `references/editor-runtime.md`）
- 每页 `section.slide` 具稳定 `id`；可移动内容置于 `.slide-edit-layer`，标记 `[data-slide-object][data-oid]`；静态装饰（背景 / 固定导航）置于层外。
- 浏览器内能力：对象拖 **⠿** 移动、角拖缩放、Ctrl+click 多选、Delete 删除、Add element（Text / Image / Video）；**Pages 侧栏**缩略图拖拽重排 / 复制 / 删除 / +New；**Undo / Redo**（Ctrl+Z/Y）；**本地保存**（Ctrl+S → localStorage 草稿 + 下载便携 HTML）；**导出干净 HTML**（剥离编辑 UI、媒体转 data URL）；演示工具 Laser / Fullscreen；`E` 进编辑、`Esc` 退出。

---

## 运行时能力（生成物内置，单文件零依赖）

> 全部能力内嵌于生成的 HTML，双击即用，无需任何运行时。

### 演讲者模式（S 键双屏同步）
- 播放中按 **S** 弹出演讲者控制台（`window.open`，首次使用需允许弹窗；被拦截时按提示在地址栏放行）。
- 控制台四卡片：**当前页像素预览 / 下一页预览**（`?preview=N&ui=0` iframe 复用同一 HTML，样式与观众屏物理一致）、**讲稿面板**（读本页不可见 `div.notes`）、**毫秒计时器**（开始/暂停/重置）。
- 同步：观众窗口与演讲者控制台经 `BroadcastChannel('ppt_sync_channel')` 零延迟广播，控制台键盘 ←/→ 翻页同样驱动观众屏。
- 讲稿契约：每页 `notes` 字段渲染为不可见 `div.notes`，正文绝不出现讲者提示；预览 iframe 内禁用翻页键。

### 主题切换（T 键）
- 播放中按 **T** 在 13 套预设间循环切换（`html[data-theme]` CSS 变量重映射，无白屏），用于现场选型 / 观众口味适配。
- 低性能投屏环境：T 键换肤与动画均轻量，`prefers-reduced-motion` 自动关闭动画。

### 键位总表
```
→ / Space / PageDown  下一页        ← / PageUp  上一页
Home / End             首 / 末页     F  全屏
S                     演讲者模式     T  循环切换主题（13 套）
E                     编辑开/关     P  Pages 侧栏
L                     激光笔        Ctrl+S  保存草稿（编辑模式）
Ctrl+Z / Ctrl+Y        撤销 / 重做   Delete  删除选中对象（编辑模式）
```

### 双产物交付
- `课件.html`：可编辑源（含浏览器内编辑内核）。
- `课件.dist.html`（`--dist` 生成）：剥离编辑 UI 的演示版，对外分发用；两版均含演讲者模式与 T 键换肤。

---

## STYLE_PRESETS 范式（每套含四维度）
见 `references/style-presets.md`：每套预设是**规范（spec）**而非仅配色——须实现其 **Layout 散文 + Signature Elements**（标题页与内容页因预设而异），配合 Typography（字体栈）与 Colors（调色板）。禁止因加编辑模式废预设撰写、禁止跨美学复用同一「标题+副标+圆角矩形」几何。

## 引用保真与去 AI 味
- 数据 / 理论遵循 `skills/citation-integrity/SKILL.md`——真实可核实，缺失标注〔假设数据〕，严禁虚构。
- 对外发布前可过 `deai-rules` 门禁。

## 依赖与运行
- make / edit / md2spec HTML 方案：`build_deck.py` / `edit_deck.py` / `md2spec.py` 纯标准库，零外部依赖。
- 传统方案：`build_pptx.py` 需 `python-pptx`；PPT 转换 `extract_pptx.py` 需 `python-pptx`；PDF 转换 `extract_pdf.py` 需 `pymupdf`（均登记于 `setup` 的 `PY_DEPS`，一键初始化自动装入 venv）。
- 办公二进制探测：`office_bin.py` 的 `find_office_bin()` 负责定位本机 WPS / 微软 Office / LibreOffice（优先本机、绝不下载）；需要调用 soffice 等做转换时统一走它，并设置 `OFFICE_BIN` 可手动指定。
- 始终经 `$VENV_PY` 调用（见 `skills/setup/SKILL.md`）。

## 内置脚本与参考

| 路径 | 用途 |
|------|------|
| `scripts/build_deck.py` | make 线：HTML 单文件生成器（含编辑运行时 + 演讲者模式 + 13 主题换肤 + `--check` 验收门禁 + `--dist` 双产物 + `--template` 课型骨架 + `--split N` 长 deck 拆分 / `--batch` 目录批量 build） |
| `scripts/md2spec.py` | Markdown 大纲 → deck.spec.json（纯标准库；`#`=title/section、`##`=内容页、列表=要点/步骤、表格→table、图片→image、代码块标注 chart→chart、`左 \|\| 右`→two-col、`>`=notes） |
| `scripts/merge_spec.py` | 合并两个 spec（骨架定结构 + 内容供内容，`--prefer content` 可换优先级） |
| `scripts/edit_deck.py` | edit 线：增强 / 编辑已有 deck（读 → 改 → 导出） |
| `scripts/build_pptx.py` | 传统 .pptx 生成器（python-pptx 离线生成） |
| `scripts/extract_pptx.py` | PPT 转换抽取（python-pptx；抽取主题色/字体到 spec.vars，供风格继承） |
| `scripts/extract_pdf.py` | PDF 转换抽取（pymupdf，可选） |
| `references/html-deck-spec.md` | HTML 文稿架构与方案评估 |
| `references/style-presets.md` | 教学风格预设（Layout + Signature + Typography + Colors 范式） |
| `references/editor-runtime.md` | 编辑运行时契约（DOM / JS / CSS 模式） |
| `references/ppt-design-guide.md` | 课件设计指南 |
| `skills/setup/scripts/setup.py` | 可选依赖（python-pptx / pymupdf，见 `PY_DEPS["ppt-maker"]`） |

## 边界
- 不替代 `course-builder` 的教学设计（结构 / Action Title / 信息密度由其负责）；不编造数据；不自动安装依赖；不联网 / 不写外部 API / 不触碰 `agents/`。

---
