# 教学风格预设（style-presets · STYLE_PRESETS 四维度范式）

> **STYLE_PRESETS 范式**：每套预设是「规范（spec）」而非仅配色，
> 须实现其 **1. Layout（版式叙述）** + **2. Signature Elements（签名元素）** + **3. Typography（字体栈）** + **4. Colors（调色板）** 四个维度。
>
> **硬约束**（来自原仓库）：
> - 禁止因「加了编辑模式」而废预设撰写——编辑运行时只是叠加层，不得削弱每套预设的版式与签名表达。
> - 禁止跨美学复用同一套「标题 + 副标 + 圆角矩形」几何；标题页与内容页须**因预设而异**。
> - `build_deck.py` 的 `PRESETS` 字典是本文件数值的**单一事实源**；本文件作选型与实现规范参考。
> - **落地状态**：`academic-light`（左 accent 竖条）、`ink`（居中上下发丝线 + 内容页分隔线）、`aurora`（整屏渐变背景 + 冷光分隔线）三套签名元素已由 `build_deck.py` 的 `preset_deco()` 实现为静态装饰（`.deco`，不参与编辑）；其余预设暂以配色 + 字体差异化呈现，后续可逐套补装饰。

## 四维度速查

| id | 名称 | 1. Layout 版式叙述 | 2. Signature 签名元素 | 3. Typography | 4. Colors（主/强调） |
|----|------|------------------|---------------------|-------------|-------------------|
| `academic-light` | 学术·浅 | 左对齐大标题+副标；内容页顶部标题条+左缩进要点，留白克制 | 左侧细 accent 竖条、圆角卡片、淡灰 surface | 黑体/无衬线 | `#1f3a5f` / `#e8833a` |
| `ink` | 纸墨·中文 | 居中竖排感标题+细线分隔；内容页宋体大行距、段落叙述 | 宣纸米底、朱红 accent、发丝级分隔线 | 宋体衬线 | `#23201c` / `#9e2b25` |
| `aurora` | 极光·科技 | 整屏深色+霓虹渐变大字；网格分区、玻璃拟态卡片 | 青紫渐变光晕、玻璃卡片、发光描边 | 无衬线 | `#37e0c8` / `#7c5cff` |
| `lava` | 熔岩·电影 | 电影宽幅字幕式；大图背景+前景文字卡 | 暖黑底、橙红渐变、暗角 | 无衬线/衬线副 | `#ff7a45` / `#b3261e` |
| `sandstone` | 砂岩·温暖 | 暖色大圆角块+居中标题；柔和卡片、低饱和 | 砂岩米色、暖橙主、橄榄点缀、柔阴影 | 圆体/无衬线 | `#c06b4f` / `#6b7a3a` |
| `obsidian` | 玄金·中国漆器 | 漆黑底+鎏金大字+留白；楷体标题、宋体正文、金线分隔 | 玄黑底、鎏金、楷体、漆器描边 | 毛笔行楷/宋体 | `#c9a24b` / `#d9b85a` |
| `concrete` | 混凝土·粗犷 | 粗黑描边大字+网格；高对比硬边卡片、撞色块 | 灰白底、蓝黄撞色、粗黑线、硬阴影 | 粗黑体 | `#2d6cff` / `#ffd23f` |
| `glacier` | 冰川·极简 | 大量留白+小字标签；极简列表、细蓝线、冷灰 | 纯白底、冰蓝、极细线、克制留白 | 细黑体 | `#3a7ca5` / `#9ec5d8` |

## 选择决策树（Phase 2 风格发现用）

### 学科 / 受众视角（教学选型）
```
学科 = 理工/计算机   → aurora（前沿）/ academic-light（严谨）
学科 = 文社科/中文   → ink / obsidian（中国风）
学科 = 经管/商科     → academic-light（深蓝金点缀）或 lava（路演）
受众 = 大一新生       → sandstone（亲切）/ glacier（极简）
场景 = 案例叙事       → lava
场景 = 中国风/历史    → obsidian
场景 = 大阶梯/报告厅  → glacier（少字多图）/ academic-light
无偏好                → academic-light（默认）
```

### 任务视角（汇报 / 分享选型，对齐 html-ppt 生态）
```
管理层汇报 / 周报 / 复盘   → academic-light（严谨）或 glacier（克制）
学术 / 技术报告             → academic-light / ink
工程架构 / 技术分享         → aurora（前沿）或 concrete（硬朗）
路演 / 产品发布             → lava（电影感）或 sandstone（亲和）
竖屏 / 社交媒体图文         → 暂不支持（勿用 16:9 硬裁，标注能力边界）
有逐字稿的正式演讲          → 任意（配合 S 键演讲者模式与 notes）
```

> 两视角可叠加：先按任务定大方向，再按学科 / 受众微调；无偏好一律 academic-light。
> **运行时换肤**：生成后播放中按 **T** 键即可在 13 套预设间循环切换现场定夺，不必重新生成（`build_deck.py` 已打包全部预设为 `html[data-theme]` 作用域）。

## 风格发现三步（Phase 2：show, don't tell）

1. 基于目的/受众/情绪/密度，生成 **3 个单页风格预览**：1 个安全预设（上表默认或学科匹配）+ 1 个大但模板（如 concrete/lava）+ 1 个 wildcard（如 obsidian/aurora）。
2. 预览须**像真实首页**（禁渲内部工作流文本），存入风格预览目录，自动打开让用户看。
3. 用户选 A/B/C/Mix；选定后读本表对应预设的 **Layout + Signature**（不止 `:root` 颜色），实现标题页与内容页差异化。

## 预设变量示例（供 build_deck.py 展开）

每个预设在生成器中展开为如下 CSS 变量（节选自 `academic-light`）：

```css
:root{
  --bg: #ffffff;            /* 幻灯片背景 */
  --fg: #1f2733;            /* 正文文字 */
  --muted: #5b6675;         /* 次要文字 */
  --primary: #1f3a5f;       /* 主色（标题/强调块） */
  --accent: #e8833a;        /* 强调色（点睛/数据高亮） */
  --surface: #f4f6f9;       /* 卡片/代码块底 */
  --line: #d7dde6;          /* 分割线 */
  --font-head: "PingFang SC","Microsoft YaHei","Source Han Sans SC",sans-serif;
  --font-body: "PingFang SC","Microsoft YaHei","Source Han Sans SC",sans-serif;
}
```

深色预设（aurora/lava/obsidian）反转 `--bg`/`--fg` 并调高对比；具体数值以 `build_deck.py` 的 `PRESETS` 字典为准。

---

## magazine 色板体系

> 原则：**色板是规范不是可自由组合的调色盘**——用户不允许自定义颜色（配色错了画面瞬间变丑），只从预设中挑。
> 落地状态：**已正式并入 `build_deck.py` PRESETS（SSOT）**——预设 id `magazine-ink / magazine-indigo / magazine-forest / magazine-kraft / magazine-dune`，T 键换肤 13 套循环；全 13 套通过 `--check` 对比度门禁（0 FAIL）。

| id | 名称 | 调性 | --fg（ink） | --bg（paper） | --muted（ink-tint） | --accent（补取） |
|---|---|---|---|---|---|---|
| `magazine-ink` | 墨水经典（Monocle 默认） | 纯墨黑 + 暖米白，杂志感最强，通用安全 | `#0a0a0b` | `#f1efea` | `#18181a` | `#9e2b25`（朱红） |
| `magazine-indigo` | 靛蓝瓷 | 深靛蓝 + 瓷白，冷静理性，科技/研究/数据 | `#0a1f3d` | `#f1f3f5` | `#152a4a` | `#c2571a`（深橙，4.0:1 合格） |
| `magazine-forest` | 森林墨 | 深森林绿 + 象牙，沉稳，自然/文化/非虚构 | `#1a2e1f` | `#f5f1e8` | `#253d2c` | `#b3742f`（陶土） |
| `magazine-kraft` | 牛皮纸 | 暖牛皮纸底，人文/文创/手作 | `#2a1e13` | `#eedfc7` | `#3a2a1d` | `#8a4b2a`（赭红） |
| `magazine-dune` | 沙丘 | 沙漠暖沙色，克制留白，创意/品牌 | `#1f1a14` | `#f0e6d2` | `#2d2620` | `#a35f3a`（暖橙） |

> **变量映射规则**（guizang 4 维 → ppt-maker 7 维）：`--ink`→`--fg`/`--primary`、`--paper`→`--bg`、`--paper-tint`→`--surface`、`--ink-tint`→`--muted`/`--line`（偏深作 muted，配 paper-tint 派生 line）；`--accent` 为补取（每套按美学推导 + `--check` 对比度 ≥3:1 验证；magazine-indigo 原 #e8833a 仅 2.4:1 不合格，改 #c2571a 4.0:1）。
> **附**：全部 13 套预设均通过 `--check` 对比度门禁（0 FAIL）。

**纪律**：
1. **类名/变量必须来自 template/PRESETS**，禁止自创类名——对应 ppt-maker「语义 class + CSS 变量」约束（html-deck-spec.md 第 9 条）。
2. **图片永远用标准比例**（16:10 / 4:3 / 1:1 / 3:2 / 16:9），不用原图奇葩比例——对应 `ppt-design-guide.md` 图片规范（已并入）。
3. **标题衬线、正文非衬线**的字体分工（guizang 风格 A）——magazine 系 typography 已落地（head 衬线 + body 无衬线）。
4. **不用 emoji 作功能图标**（guizang P0 第 1 条）——与 ppt-maker「无 emoji 功能图标」门禁一致（release_pack 已强制）。
5. **视觉 + 代码双核对**（guizang 0-F）：验收不只靠肉眼，跑 `build_deck.py --check` + 产物断言。

**与现有 8 套的关系**：magazine 系列为「杂志/发布/分享」场景补充，现有 academic-light/ink/aurora 等为「教学/课堂」场景；两者按 `学科 × 任务` 选型表（见上）分流，不冲突。T 键换肤 13 套循环顺序：academic-light → ink → aurora → lava → sandstone → obsidian → concrete → glacier → magazine-ink → magazine-indigo → magazine-forest → magazine-kraft → magazine-dune。
