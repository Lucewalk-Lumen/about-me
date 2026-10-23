#!/usr/bin/env node
// Generate .docx from a structured .md file.
// Usage: node generate_docx.js <input.md> [output.docx] [--profile minutes|review]
// If output is omitted, defaults to <input-basename>.docx in same directory.
//
// Profiles:
//   minutes (default) = minutes-organizer layout (Arial, deep-blue titles). Unchanged behaviour.
//   review            = academic review-report layout (SimSun body + SimHei headings,
//                       black titles, first-line indented body paragraphs).

const fs = require("fs");
const path = require("path");
const { execSync } = require("child_process");

// ---------------------------------------------------------------------------
// Robust docx resolution. The library may not be installed in the local
// node_modules, so try several locations before giving up:
//   1. Plain require("docx")            — local / NODE_PATH resolution
//   2. `npm root -g` global modules dir — globally installed copy
//   3. WorkBuddy managed workspace path — bundled runtime copy
// Any success wins; total failure prints an actionable Chinese hint (no stack).
// ---------------------------------------------------------------------------
function loadDocx() {
  const attempts = [];

  // Attempt 1: normal resolution (local node_modules or NODE_PATH).
  try {
    return require("docx");
  } catch (e) {
    attempts.push("require(\"docx\"): " + e.message);
  }

  // Attempt 2: global npm root.
  try {
    const globalRoot = execSync("npm root -g", { encoding: "utf-8" }).trim();
    return require(path.join(globalRoot, "docx"));
  } catch (e) {
    attempts.push("npm root -g: " + e.message);
  }

  // Attempt 3: WorkBuddy managed workspace node_modules (env override for portability).
  try {
    const wbModules = process.env.WORKBUDDY_NODE_MODULES;
    if (wbModules) {
      return require(path.join(wbModules, "docx"));
    }
    // Fall back to a sibling node_modules next to this script.
    return require(path.join(__dirname, "node_modules", "docx"));
  } catch (e) {
    attempts.push("workspace node_modules: " + e.message);
  }

  console.error("未找到 docx 库。请先安装：npm install -g docx （或在脚本同级目录 npm install docx）");
  process.exit(1);
}

const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  BorderStyle, PageBreak
} = loadDocx();

// ---------------------------------------------------------------------------
// Layout profiles. Every value that differs between the two output styles is
// collected here so the parsing logic below stays single-sourced. Fonts use
// the docx object form { ascii, hAnsi, eastAsia } so CJK glyphs map correctly.
// Sizes are docx half-points (1pt = 2).
// ---------------------------------------------------------------------------
const PROFILES = {
  // Profile A — meeting minutes (original behaviour, untouched values).
  minutes: {
    fontBody: { ascii: "Arial", hAnsi: "Arial", eastAsia: "Arial" },
    fontHeading: { ascii: "Arial", hAnsi: "Arial", eastAsia: "Arial" },
    SIZE_TITLE: 36,      // 18pt
    SIZE_SUBTITLE: 22,   // 11pt
    SIZE_H1: 32,         // 16pt
    SIZE_H2: 26,         // 13pt
    SIZE_H3: 24,         // 12pt
    SIZE_BODY: 22,       // 11pt
    SIZE_NOTE: 20,       // 10pt
    SIZE_BLOCKQUOTE: 21, // 10.5pt
    COLOR_BLACK: "000000",
    COLOR_GREY: "666666",
    COLOR_TITLE: "1F4E79", // deep blue main title
    COLOR_H1: "1F4E79",    // deep blue H1
    bodyFirstLineIndent: 0,
  },
  // Profile B — academic review report (measured from a real delivered .docx).
  review: {
    fontBody: { ascii: "Times New Roman", hAnsi: "Times New Roman", eastAsia: "宋体" },
    fontHeading: { ascii: "Times New Roman", hAnsi: "Times New Roman", eastAsia: "黑体" },
    SIZE_TITLE: 36,      // 18pt
    SIZE_SUBTITLE: 26,   // 13pt
    SIZE_H1: 30,         // 15pt
    SIZE_H2: 26,         // 13pt
    SIZE_H3: 24,         // 12pt
    SIZE_BODY: 24,       // 12pt
    SIZE_NOTE: 21,       // 10.5pt
    SIZE_BLOCKQUOTE: 21, // 10.5pt
    COLOR_BLACK: "000000",
    COLOR_GREY: "666666",
    COLOR_TITLE: "000000", // black main title
    COLOR_H1: "000000",    // black H1
    bodyFirstLineIndent: 480, // ≈2 chars, profile-B only
  },
};

// ---------------------------------------------------------------------------
// Argument parsing. `--profile` may appear anywhere and be written either as
// `--profile review` or `--profile=review`. All other non-flag tokens are
// treated as positional args in order (input, output).
// ---------------------------------------------------------------------------
const argv = process.argv.slice(2);
const positional = [];
let profile = null;          // null = not explicitly specified → auto-detect later
let profileExplicit = false; // true once the user passes --profile in any form

for (let k = 0; k < argv.length; k++) {
  const a = argv[k];
  if (a === "--profile") {
    profile = argv[k + 1];
    profileExplicit = true;
    k++; // consume the value token
    continue;
  }
  if (a.startsWith("--profile=")) {
    profile = a.slice("--profile=".length);
    profileExplicit = true;
    continue;
  }
  if (a.startsWith("--")) {
    // Unknown flag — ignore rather than mistaking it for a positional arg.
    continue;
  }
  positional.push(a);
}

if (positional.length < 1) {
  console.error("Usage: node generate_docx.js <input.md> [output.docx] [--profile minutes|review]");
  process.exit(1);
}

if (profileExplicit && !Object.prototype.hasOwnProperty.call(PROFILES, profile)) {
  console.error("Invalid --profile value: " + profile + " (expected 'minutes' or 'review')");
  process.exit(1);
}

// ---------------------------------------------------------------------------
// detectProfile — infer the layout profile from the markdown content when the
// user did NOT pass --profile. Uses a weighted signal count: any strong signal
// below adds one point, and >= 2 points classifies the document as a review
// report. Otherwise it defaults to meeting minutes.
//
// Strong signals (review):
//   1. A "摘要" heading line (摘要 / ## 摘要 / **摘要**)
//   2. A "关键词" line
//   3. An "附录" reference (附录一/二… or ## 附录)
//   4. >= 3 H1 lines using Chinese-numeral + 、 style (# 一、…)
//   5. The first title line contains "综述" or "报告"
// Returns 'review' or 'minutes', plus the matched signal labels for logging.
// ---------------------------------------------------------------------------
function detectProfile(lines) {
  const matched = [];

  // Signal 1: 摘要 heading.
  const hasAbstract = lines.some(function (l) {
    const t = l.trim();
    return t === "摘要" || /^#{1,6}\s*摘要\s*$/.test(t) || /^\*\*摘要\*\*$/.test(t);
  });
  if (hasAbstract) matched.push("摘要");

  // Signal 2: 关键词 line.
  const hasKeywords = lines.some(function (l) {
    return /关键词/.test(l.trim());
  });
  if (hasKeywords) matched.push("关键词");

  // Signal 3: 附录 reference.
  const hasAppendix = lines.some(function (l) {
    const t = l.trim();
    return /附录/.test(t);
  });
  if (hasAppendix) matched.push("附录");

  // Signal 4: >= 3 Chinese-numeral H1 headings.
  let h1Count = 0;
  for (const l of lines) {
    if (/^# (?:[一二三四五六七八九十]+|末章|附录[一二三四五六七八九十]+)、/.test(l.trim())) {
      h1Count++;
    }
  }
  if (h1Count >= 3) matched.push("多章H1(" + h1Count + ")");

  // Signal 5: first non-empty title line contains 综述 / 报告.
  const firstTitle = lines.find(function (l) { return l.trim() !== ""; }) || "";
  if (/综述|报告/.test(firstTitle)) matched.push("标题含综述/报告");

  const isReview = matched.length >= 2;
  return { profile: isReview ? "review" : "minutes", matched };
}

const mdPath = path.resolve(positional[0]);
const outPath = positional[1]
  ? path.resolve(positional[1])
  : path.join(path.dirname(mdPath), path.basename(mdPath, ".md") + ".docx");

// F-05 (security hardening): contain the output path within the input file's
// directory. The documented contract is "output defaults beside the input", and
// we must not let a crafted/erroneous output argument write a .docx outside the
// source tree (path-traversal / arbitrary-write). Reject anything that escapes.
const safeBase = path.dirname(mdPath);
const outRel = path.relative(safeBase, outPath);
if (outRel === "" || outRel.startsWith("..") || path.isAbsolute(outRel)) {
  console.error(
    "输出路径越界：outPath 必须位于输入文件所在目录内（" + safeBase + "）→ " + outPath
  );
  process.exit(2);
}

if (!fs.existsSync(mdPath)) {
  console.error("Input file not found: " + mdPath);
  process.exit(1);
}

const lines = fs.readFileSync(mdPath, "utf-8").split("\n");

// Resolve the effective profile: explicit --profile wins (override priority);
// otherwise auto-detect from content.
let activeProfile;
if (profileExplicit) {
  activeProfile = profile;
  console.log("Using profile: " + activeProfile + " (user-specified)");
} else {
  const detected = detectProfile(lines);
  activeProfile = detected.profile;
  if (detected.matched.length > 0) {
    console.log("Auto-detected profile: " + activeProfile + " (matched: " + detected.matched.join(", ") + ")");
  } else {
    console.log("Auto-detected profile: " + activeProfile);
  }
}

const P = PROFILES[activeProfile];

const children = [];

function addSpacer(size = 120) {
  children.push(new Paragraph({ spacing: { before: size, after: 0 }, children: [] }));
}

let i = 0;
let blockquoteLines = [];

function flushBlockquote() {
  if (blockquoteLines.length === 0) return;
  // 多行 blockquote：按行剥离前导 "> "（及可选空白）再拼接，避免仅首行去前缀
  const text = blockquoteLines
    .map((l) => l.replace(/^\s*>\s?/, ""))
    .join(" ")
    .trim();
  const isNote = text.includes("说明") || text.includes("待核实") || text.includes("复核");
  children.push(new Paragraph({
    spacing: { before: 60, after: 60 },
    indent: { left: 720 },
    border: isNote
      ? { left: { style: BorderStyle.SINGLE, size: 6, color: "C00000", space: 8 } }
      : { left: { style: BorderStyle.SINGLE, size: 6, color: "2E75B6", space: 8 } },
    children: [new TextRun({
      text, font: P.fontBody, size: P.SIZE_BLOCKQUOTE,
      italics: !isNote,
      color: isNote ? P.COLOR_BLACK : P.COLOR_GREY
    })]
  }));
  blockquoteLines = [];
}

while (i < lines.length) {
  const raw = lines[i];
  const line = raw.trimEnd();

  // Blockquote (handle both "> " and "> " with possible leading whitespace)
  if (/^>\s/.test(line)) {
    blockquoteLines.push(line);
    i++;
    continue;
  }
  // Infer continuation of multi-line blockquote
  if (blockquoteLines.length > 0 && line === "") {
    flushBlockquote();
    i++;
    continue;
  }

  flushBlockquote();

  if (line === "") {
    addSpacer(60);
    i++;
    continue;
  }

  // Title line: **bold text**
  if (i === 0 && line.startsWith("**") && line.endsWith("**")) {
    children.push(new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 0, after: 60 },
      children: [new TextRun({ text: line.replace(/\*\*/g, ""), bold: true, font: P.fontHeading, size: P.SIZE_TITLE, color: P.COLOR_TITLE })]
    }));
    i++;
    continue;
  }

  // Subtitle: （...）
  if (i === 1 && line.startsWith("（") && line.endsWith("）")) {
    children.push(new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 0, after: 120 },
      children: [new TextRun({ text: line, font: P.fontBody, size: P.SIZE_SUBTITLE, color: P.COLOR_GREY })]
    }));
    i++;
    continue;
  }

  // H1: # 一、... plus 六~十、末章、附录一/二/三 etc.
  if (/^# (?:[一二三四五六七八九十]+|末章|附录[一二三四五六七八九十]+)、/.test(line)) {
    children.push(new Paragraph({
      heading: HeadingLevel.HEADING_1,
      spacing: { before: 480, after: 240 },
      children: [new TextRun({ text: line.replace(/^# /, ""), bold: true, font: P.fontHeading, size: P.SIZE_H1, color: P.COLOR_H1 })]
    }));
    i++;
    continue;
  }

  // H2: ## Name
  if (line.startsWith("## ")) {
    children.push(new Paragraph({
      heading: HeadingLevel.HEADING_2,
      spacing: { before: 360, after: 120 },
      children: [new TextRun({ text: line.replace(/^## /, ""), bold: true, font: P.fontHeading, size: P.SIZE_H2, color: P.COLOR_BLACK })]
    }));
    // Affiliation line in parens immediately after H2. A line that opens with
    // "（" followed by a 4-digit year (e.g. （2026… / （2027…) is a date line,
    // not an affiliation, so it must NOT be swallowed here.
    if (i + 1 < lines.length && lines[i + 1].trim().startsWith("（") && !/^（\d{4}/.test(lines[i + 1].trim())) {
      i++;
      children.push(new Paragraph({
        spacing: { before: 0, after: 120 },
        children: [new TextRun({ text: lines[i].trim(), font: P.fontBody, size: P.SIZE_NOTE, color: P.COLOR_GREY, italics: true })]
      }));
    }
    i++;
    continue;
  }

  // H3: ### text
  if (line.startsWith("### ")) {
    children.push(new Paragraph({
      heading: HeadingLevel.HEADING_3,
      spacing: { before: 240, after: 80 },
      children: [new TextRun({ text: line.replace(/^### /, ""), bold: true, font: P.fontHeading, size: P.SIZE_H3, color: P.COLOR_BLACK })]
    }));
    i++;
    continue;
  }

  // Horizontal rule
  if (line === "---") {
    addSpacer(120);
    children.push(new Paragraph({
      border: { bottom: { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC", space: 1 } },
      spacing: { before: 0, after: 120 },
      children: []
    }));
    i++;
    continue;
  }

  // Inline bold section headers like **0. 开场与定位**
  if (/^\*\*.*\*\*$/.test(line) && line.length < 60) {
    children.push(new Paragraph({
      spacing: { before: 200, after: 60 },
      children: [new TextRun({ text: line.replace(/\*\*/g, ""), bold: true, font: P.fontHeading, size: P.SIZE_BODY, color: P.COLOR_BLACK })]
    }));
    i++;
    continue;
  }

  // Regular paragraph with inline bold
  const parts = line.split(/(\*\*.*?\*\*)/g);
  const runs = [];
  for (const part of parts) {
    if (part.startsWith("**") && part.endsWith("**")) {
      runs.push(new TextRun({ text: part.slice(2, -2), bold: true, font: P.fontBody, size: P.SIZE_BODY }));
    } else if (part) {
      runs.push(new TextRun({ text: part, font: P.fontBody, size: P.SIZE_BODY }));
    }
  }
  const bodyParagraph = {
    spacing: { before: 40, after: 40, line: 360 },
    children: runs
  };
  // First-line indent is a profile-B (review) feature only. Profile A leaves it at 0.
  if (P.bodyFirstLineIndent) {
    bodyParagraph.indent = { firstLine: P.bodyFirstLineIndent };
  }
  children.push(new Paragraph(bodyParagraph));
  i++;
}

flushBlockquote();

const doc = new Document({
  styles: {
    default: { document: { run: { font: P.fontBody, size: P.SIZE_BODY } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: P.SIZE_H1, bold: true, font: P.fontHeading, color: P.COLOR_H1 },
        paragraph: { spacing: { before: 480, after: 240 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: P.SIZE_H2, bold: true, font: P.fontHeading, color: P.COLOR_BLACK },
        paragraph: { spacing: { before: 360, after: 120 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: P.SIZE_H3, bold: true, font: P.fontHeading, color: P.COLOR_BLACK },
        paragraph: { spacing: { before: 240, after: 80 }, outlineLevel: 2 } },
    ]
  },
  sections: [{
    properties: {
      page: {
        size: { width: 11906, height: 16838 }, // A4
        margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 }
      }
    },
    children
  }]
});

Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync(outPath, buffer);
  console.log("DOCX written: " + outPath + " (profile: " + activeProfile + ")");
}).catch(err => {
  console.error("Error:", err);
  process.exit(1);
});