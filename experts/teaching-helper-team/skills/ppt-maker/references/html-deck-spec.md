# HTML 文稿架构规范与方案评估

> 本文件定义 `build_deck.py` 产出的 HTML 演示文稿的技术约束，并给出「传统 vs HTML」的方案评估依据。

## 一、方案评估（决策依据）

| 方案类型 | 核心能力 | 优点 | 风险/不足 | 教学适配 |
|------|---------|-----------|-----------|---------|
| 成熟 HTML 单文件 | 12 套风格预设、行内编辑(E)、PPT→HTML、PDF 导出、固定 16:9 舞台 | 成熟、教学友好、动画丰富 | 预设数偏少 |  |
| 功能全 HTML | 36 主题/15 模板/47 动画、演讲者模式、Canvas FX | 功能极全 | **依赖 CDN**（字体/高亮），离线教室不可用；无 .pptx 导出 |  |
| 零依赖 HTML | 34 模板、视觉风格发现、PPT 转换 | 零依赖、无-dep | 生态适配有限 |  |
| 可编辑 HTML | **46 预设、浏览器内拖拽/缩放/重排/本地保存导出、PPTX-to-Web** | **生成后仍可编辑**（教学刚需）、零依赖、可导入 .pptx | — |  |

**评估结论**：主流方案均为 HTML 路线，无传统 PPTX 生成器进入候选——说明 HTML 更适合 AI 生成演示。
本技能采用 HTML 为主路径，并吸收「可编辑」内核（生成后仍可改）与固定舞台/风格预设思路；
**刻意规避 CDN 依赖**，改用系统字体栈保证离线教室可用。

**与传统方案（python-pptx）的对比**：

| 维度 | HTML（默认） | 传统 .pptx（备选） |
|------|-------------|-------------------|
| 播放环境 | 任意浏览器，免装软件 | 需 PowerPoint/WPS |
| 动画 | 丰富（淡入/缩放/交错） | 有限 |
| 生成后可编辑 |  浏览器内拖拽/改字/保存 | 需打开 PowerPoint 改 |
| 离线 |  默认系统字体 |  |
| 机构合规/LMS | 多数支持，但部分只收 .pptx |  强制场景唯一解 |
| 部署/分享 | 可部署链接/导出 PDF | 文件传输 |
| 与既有模板耦合 | 弱 |  强（需合并已有 .pptx） |

## 二、HTML 文稿技术约束（build_deck.py 必须遵守）

1. **固定舞台**：幻灯片画布固定 `1920×1080`（16:9），通过 JS `transform: scale()` 整体缩放适配任意视口，移动端不重排。
2. **可见性控制**：幻灯片用 `.active`（opacity/visibility 过渡）切换，**禁止对整页用 `display:none/block` 切换动画元素**；单页内元素出现用 `.active .anim` 交错动画。
3. **离线字体**：默认 `font-family` 用系统栈（如 `"PingFang SC","Microsoft YaHei","Source Han Sans SC",sans-serif`），**不引用外部 CDN 字体**，保证离线教室可用；预设仅改字体栈变量。
4. **键盘导航**：`→`/`Space` 下一页，`←` 上一页，`Home`/`End` 首尾，`F` 全屏，`E` 进入/退出编辑，`S` 演讲者模式，`T` 循环切换主题（13 套），`P` Pages 侧栏，`L` 激光笔。
5. **无障碍**：必须支持 `prefers-reduced-motion`（关闭动画）；正文/背景对比度 ≥ 4.5:1；不只用颜色区分信息。
6. **单文件**：CSS/JS 全部内联，产物为单个 `.html`，可双击打开、可转发。
7. **内嵌编辑器**（差异化能力）：浏览器内对文本 `contenteditable`、对对象拖拽/缩放、幻灯片重排、`Ctrl+S` 存 `localStorage`、「导出」按钮产出**剥离编辑器 UI 的干净 HTML**；`?preview=N` / `?presenter=1` 模式下编辑运行时不初始化（`__QS_EDIT` 守卫）。
8. **图表零依赖**：`chart` 类型用内联 SVG 绘制（柱状/饼/折线），不引图表库。
9. **语义 class**：风格差异仅通过 CSS 变量（调色板/字体）实现，HTML 结构保持语义化，便于风格迁移；预设签名元素以静态 `.deco` 装饰落地（不参与编辑、`pointer-events:none`、z-index 低于内容层）。
10. **notes 不可见契约**：讲者备注（`notes` 字段）一律渲染为 `<div class="notes" style="display:none">…</div>` 内嵌于对应 `section.slide` 尾部，**绝不在观众视图可见**（遵循 html-ppt 备注契约）；仅供演讲者模式 / 备注抽屉读取，导出干净 HTML 时保留但保持不可见。
11. **主题切换**：全部预设打包为 `html[data-theme="…"]` CSS 变量作用域，T 键循环切换（无白屏），模板 `<html data-theme="默认预设">` 指定初始主题。
12. **演讲者模式契约**：S 键 `window.open(?presenter=1)` 弹出控制台（首次需允许弹窗）；控制台四卡片为当前页 / 下一页（`?preview=N&ui=0` iframe 复用同一 HTML，像素级一致）、讲稿（读本页 `.notes`）、计时器；`BroadcastChannel('ppt_sync_channel')` 广播 `{type:'SYNC_SLIDE',index}` 双屏同步；预览 iframe（`body.ui-preview`）禁用翻页键。

## 三、内容类型 → 渲染映射

| type | 渲染 | 字段 |
|------|------|------|
| `title` | 标题页（大标题+副标题） | `title`,`subtitle` |
| `section` | 章节分隔页 | `title`,`lead` |
| `bullets` | 要点页（Action Title + 要点列表） | `title`,`points[]`,`notes?` |
| `two-col` | 双栏对比页 | `title`,`left`,`right` |
| `quote` | 引述页 | `text`,`cite?` |
| `steps` | 步骤分解页 | `title`,`steps[{t,d}]` |
| `chart` | 图表页（SVG） | `title`,`chart∈{bar,pie,line}`,`data` |
| `table` | 表格页 | `title`,`headers[]`,`rows[][]` |
| `image` | 图文页 | `title`,`src`,`caption?` |
| `closing` | 结束/过渡页 | `title` |

> **notes 字段（全页型通用）**：所有页型均接受可选 `notes` 字段（讲者备注/逐字稿），渲染为不可见 `div.notes`（见技术约束第 10 条），写入讲稿时正文不得出现讲者提示。

## 四、生成器调用契约

- 输入：`--spec deck.json`（`meta` + `preset` + `slides[]` + 可选 `vars`）；`--preset` 可覆盖；`--out 课件.html`。
- 输出：单文件 HTML，含舞台、导航、动画、内嵌编辑器、演讲者模式与 13 主题切换。
- 双产物：`--dist 课件.dist.html` 另产剥离编辑 UI 的演示版（保留导航 / 演讲者模式 / 主题切换）。
- 验收门禁：`--check` 输出逐页验收报告（信息密度 / 字号下限 / WCAG 对比度 / 溢出风险），存在 FAIL 时退出码非 0（见 `check_deck()`）；accent 为装饰点缀色按非文本 3:1 评估，用于正文文字须人工复核 4.5:1。
- 课型骨架：`--template {6 套课型} --duration N --spec-out 骨架.json` 展开占位页面序列（页数按 90min 基准随 duration 缩放，夹在模板 min/max 间）；骨架 spec 可直接被 build 渲染或供 agent 填充。
- Markdown 入口：`scripts/md2spec.py 大纲.md -o deck.json` 内容驱动直转 spec（`#`=title/section、`##`=内容页、列表=要点/步骤、`>`=notes；表格→table、图片→image、代码块标注 chart→chart、`左 || 右`→two-col），`--check` 预览映射。
- 风格继承：spec 可选 `vars` 字段（`extract_pptx`/`extract_pdf` 从源文件抽取的主题色/字体）以 CSS 后定义覆盖 preset 变量，实现「PPT/PDF 原主题 → HTML」延续。
- 长 deck 拆分：`--split N` 按每 N 页输出多份子 spec（`<stem>_partK.json`，保留 meta/preset/vars），供分批编辑。
- 批量 build：`--batch` 以目录为 `--spec`，对目录内每个 *.json 产出同名 `.html` + `.dist.html`（双产物）。
- 骨架+内容合并：`scripts/merge_spec.py 骨架.json 内容.json -o 合并.json` 合并 `--template` 骨架与 md2spec 内容（占位页被覆盖、多余内容追加、`--prefer content` 换优先级）。
- 确定性：相同 spec + preset → 相同 HTML（无随机），便于 `architect` 校验与回归。
- 纯标准库：不 `import` 任何第三方包，规避依赖缺失导致「执行任务时脚本跑不起来」。
