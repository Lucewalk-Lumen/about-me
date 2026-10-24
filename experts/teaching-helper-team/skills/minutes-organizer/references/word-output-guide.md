# Word 输出指南

> 两套排版档：**A. 会议纪要**（西文 Arial / 深蓝标题，简洁现代）；**B. 学术综述报告**（中文宋体+黑体 / 首行缩进，学术正式）。按产物类型选档。

## 工具

使用 `docx-js` 从 .md 生成 .docx：

```bash
npm install -g docx
```

## 档 A：会议纪要格式规范

- **页面**: A4 (11906 × 16838 DXA)，四边距 1440 DXA (1 inch)
- **字体**: Arial（全局默认）
- **标题**: 18pt 加粗居中，深蓝色 (#1F4E79)
- **副标题**: 11pt 居中灰色 (#666666)
- **H1**: 16pt 加粗，深蓝色
- **H2**: 13pt 加粗，黑色
- **H3**: 12pt 加粗，黑色
- **正文**: 11pt，行高 1.5 倍
- **引用块**: 左侧蓝色竖线缩进（注意类灰色小字）
- **警告类引用块**: 左侧红色竖线缩进（录音乱码/待核实标注）

## 档 B：学术综述报告格式规范

> 来自实际交付的高质量综述报告成品，中文学术论文通行排版。

- **页面**: A4，四边距 1440 DXA
- **中文字体**: 正文宋体（eastAsia="宋体"），各级标题黑体（eastAsia="黑体"）
- **西文/数字字体**: Times New Roman；代码/等宽片段 Courier
- **主标题**: 18pt（sz 36）黑体加粗居中；副标题 13pt 居中
- **H1（一、二…章）**: 15pt（sz 30）黑体加粗
- **H2**: 13pt（sz 26）黑体加粗
- **正文**: 12pt（sz 24）宋体；摘要/附录/注释可用 10.5pt（sz 21）
- **首行缩进**: 正文段落首行缩进 480 DXA（≈2 字符）—— 中文论文标配，**档 A 无此项**
- **行距**: 正文固定行距（line≈360，即 1.5 倍基准）；密排段落 line≈312
- **摘要+关键词**: 置于标题下、正文前，摘要可用小一号字并整体缩进
- **附录**: 报告人索引用表格；数据来源与待核实事项用列表，字号可略小

## 关键约束（两档通用）

- 不使用破折号（——）
- 不使用手动的"(PPT)"标签，PPT 内容已自然融入正文
- 粗体用于演讲人姓名和关键术语
- 斜体用于引用块和附属信息
- 综述报告的证据分级、诚信标注（"未独立核验"等）照常写入正文/附录

## docx-js 生成脚本模板

```javascript
const { Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, BorderStyle } = require("docx");

// 档 A（纪要）：font "Arial"；档 B（综述）：run.font 需分别设 ascii/hAnsi="Times New Roman" 与 eastAsia="宋体"
const doc = new Document({
  styles: {
    default: { document: { run: { font: "Arial", size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", /* 档B: 黑体加粗 sz30 */ },
      { id: "Heading2", name: "Heading 2", /* 档B: 黑体加粗 sz26 */ },
      { id: "Heading3", name: "Heading 3" },
    ]
  },
  sections: [{ properties: { page: { /* A4 */ } }, children }]
});

// 档 B 正文段落首行缩进：new Paragraph({ indent: { firstLine: 480 }, ... })
Packer.toBuffer(doc).then(buffer => fs.writeFileSync(outPath, buffer));
```

完整生成脚本见 `scripts/generate_docx.js`，已内建两档，且**默认自动判别档位**——无需手改脚本，也无需手动传参：

- **自动判档**：脚本通读 md，按内容信号打分（摘要标题 / 关键词行 / 附录 / H1 中文数字章节 ≥3 次 / 首行标题含"综述"或"报告"），命中 ≥2 判为综述型 → 自动套档 B（宋体+黑体+首行缩进），并打印 `Auto-detected profile: review`；否则走档 A。
- **手动覆盖**：判别失误时用 `--profile minutes|review` 强制指定，显式传入优先于自动判别（打印 `Using profile: X (user-specified)`）。支持 `--profile x` 与 `--profile=x` 两种写法，位置无关。
- **依赖健壮化**：脚本按 `require("docx")`（本地/NODE_PATH）→ 全局 `npm root -g` → 环境变量 `WORKBUDDY_NODE_MODULES` / 脚本同级 `node_modules` 三级备选加载 `docx`；三处都缺失时打印中文安装提示（`npm install -g docx`）并退出，不会抛裸异常。
