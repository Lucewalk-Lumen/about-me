# PPT 生成增强指南

> 定位：在现有 `generate_deliverable_pack.py`（交付包组织）+ `output_conversion_guide.md`（内容形态转化）基础上，补充 PPT 生成链的版式与校验方法论，提升组会/答辩 PPT 的产出质量。
> 场景触发：论文 → 组会 PPT / 开题答辩 / 中期答辩 / 毕业答辩。
> 说明：本指南为**方法论参考**，不引入 Node 依赖；如需程序化生成可选用下方两种方案之一。

---

## 一、现有能力基线

| 环节 | 现有实现 | 缺口 |
|------|---------|------|
| 内容结构 | `output_conversion_guide.md`（研究问题→证据→设计→样本→结果→局限→下一步） | 无逐页版式规范 |
| 交付组织 | `generate_deliverable_pack.py`（docx/md/zip 打包 + 文件清单） | 不直接产 pptx |
| 数据图表 | `chart_engine.py` / `render_figures.py`（PNG 输出） | 图注/位置规范可增强 |

## 二、要点 1：HTML 幻灯片 → PPTX 转换的版式约束

将 HTML 幻灯片精确转换为 PPTX 时需遵守以下版式规则（AI 直接生成 PPT 内容时同样适用）：

### 版式尺寸
- 16:9（默认）：`width: 720pt; height: 405pt`
- 4:3：`width: 720pt; height: 540pt`

### 文本放置规则（AI 生成 PPT 内容时的硬约束）
- 所有文本必须放在 `<p>` / `<h1>-<h6>` / `<ul>` / `<ol>` 标签内，**不能直接放在 `<div>` 或 `<span>` 里**（否则转换后文本不显示）。
- 列表用 `<ul>/<ol>`，禁止手动输入 `• - *` 符号。
- 行内样式用 `<b>/<i>/<u>/<span style>`，不使用 markdown 语法。
- 图表占位用 `class="placeholder"` 预留空间，避免图表挤占文字。

### 对 OBHRM 场景的落地（AI 生成 PPT 时遵守）
```
每页内容按以下结构组织：
├── 标题（页首，一句话判断）
├── 正文（≤3 个要点，用列表结构）
├── 数据区（预留图表位置，结果页优先复用已有 PNG）
└── 脚注（样本量/统计方法/误差线含义）
```

## 三、要点 2：PptxGenJS 程序化生成（可选方案）

如需程序化生成 PPTX（而非 AI 直接产出），可用 `pptxgenjs`（Node）：

```js
const pptxgen = require("pptxgenjs");
const pptx = new pptxgen();
pptx.defineLayout({ name: "WIDE", width: 13.33, height: 7.5 });
pptx.layout = "WIDE";
const slide = pptx.addSlide();
slide.addText("研究问题", { x: 0.5, y: 0.5, w: 6, h: 0.8, fontSize: 28, bold: true });
slide.addImage({ path: "figures/result1.png", x: 0.5, y: 1.5, w: 6, h: 4 });
pptx.writeFile({ fileName: "group_meeting.pptx" });
```

- 安装：`npm install pptxgenjs`（可选依赖，不随包分发）。
- 适用：批量生成、模板化 PPT；日常组会用 AI 直接产出即可。

## 四、要点 3：OOXML 校验（可选）

PPTX 产物的完整 OOXML schema 校验（unpack/validate）成本较高，OBHRM 场景降级为**人工/轻量检查**：

- [ ] PPTX 打开无损坏提示；
- [ ] 图表 PNG 不模糊（≥150dpi）；
- [ ] 文字无溢出幻灯片边界；
- [ ] 页码与目录一致；
- [ ] 图注包含样本量/统计方法/误差线含义；
- [ ] 文献页保留 DOI。

## 五、与现有流程的衔接

```
论文定稿 → output_conversion_guide.md（内容形态转化）
        → 本指南 §二（逐页版式约束，AI 生成时遵守）
        → generate_deliverable_pack.py（打包交付）
```

**推荐用法**：组会/答辩 PPT 由 AI 按本指南 §二 的版式规则直接生成内容（每页一个判断 + 列表结构 + 图表预留），再复用 `generate_deliverable_pack.py` 打包；仅当需要批量/模板化 PPT 时才引入 PptxGenJS（§三）。
