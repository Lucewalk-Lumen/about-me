#!/usr/bin/env python3
"""md2spec.py - Markdown 大纲 → deck.spec.json（纯标准库，零依赖）。

承接「Markdown 即源」的薄层：把 .md 教案 / 大纲直接转为 build_deck.py 的输入 spec，
免去手写 JSON；md 纯文本便于 git diff 与协作审阅。

映射规则
--------
- 文件首个 `# 标题`        → title 页；紧随的 `> 引用` 行作为 subtitle
- 其余 `# 标题`            → section 页；紧随的 `> 引用` 行作为 lead
- `## 标题`                → 内容页；标题含 小结/总结/谢谢/致谢/Q&A/问答/作业/预告/结语 → closing
- 内容页内的首个列表决定页型：
    有序列表（1. ）→ steps；无序列表（- / *）→ bullets
- 连续三行起以 | 分隔的 markdown 表格（`| a | b |` / `|---|` / `| 1 | 2 |`）→ table 页型
- 行内独立图片 `![alt](src "caption")` → image 页型（src + 可选 caption）
- ```chart bar/pie/line 代码块（每行 `标签 数值`）→ chart 页型（data.labels/values）
- 无序列表项含 `||` 分隔（`- 左 || 右`）→ two-col 页型（left/right 收集）
- 页面内 `> 引用` 行        → 该页 notes（多行合并，正文不可见，供演讲者模式）
- `### ` / `---` / 普通代码块 → 忽略
- 普通段落                 → 忽略（大纲按标题+列表组织）

Usage:
  python3 md2spec.py 教案.md -o deck.json [--title 课件标题] [--preset academic-light] [--course 课程名]
  python3 md2spec.py 教案.md --check   # 只打印映射预览，不写文件
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# 「小结/总结」属内容页（需展示要点，由列表推断 bullets）；closing 仅用于无内容列表的收束页
CLOSING_KEYWORDS = ("谢谢", "致谢", "q&a", "问答", "作业", "思考题", "预告", "结语", "结尾", "结束")

H_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
QUOTE_RE = re.compile(r"^\s*>\s?(.*)$")
UL_RE = re.compile(r"^\s*[-*+]\s+(.+?)\s*$")
OL_RE = re.compile(r"^\s*\d+[.、)]\s+(.+?)\s*$")
CODE_FENCE = re.compile(r"^\s*```")
IMG_RE = re.compile(r"^!\[([^\]]*)\]\(([^)]+?)(?:\s+\"([^\"]*)\")?\)\s*$")
TABLE_SEP_RE = re.compile(r"^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?\s*$")
TABLE_ROW_RE = re.compile(r"^\s*\|?(.*?)\|?\s*$")
CHART_FENCE = re.compile(r"^\s*```\s*chart\s*([a-z]+)\s*$")
CHART_ROW_RE = re.compile(r"^\s*(.+?)\s+(-?\d+(?:\.\d+)?)\s*$")
TWO_COL_SEP = "||"


def parse_md(text: str) -> list[dict]:
    """逐行状态机解析为 slides 列表。

    扩展映射：
    - 连续三行起以 | 分隔的 markdown 表格 → table 页型（headers + rows）
    - 行内独立图片 ![alt](src "caption") → image 页型（src + caption）
    - ```chart bar/pie/line 代码块（每行 `标签 数值`）→ chart 页型（data.labels/values/unit）
    - 无序列表项含 `||` 分隔（左 || 右）→ two-col 页型（left/right 收集）
    - 有序/无序列表与表格/图片混用时，以先出现的为准；后续追加按原页型继续
    """
    slides: list[dict] = []
    cur: dict | None = None
    pending_quote: list[str] = []      # 标题行之后紧跟的引用（subtitle/lead）
    in_code = False
    in_chart = False                   # chart 代码块采集态
    chart_kind = "bar"
    chart_lines: list[str] = []
    seen_h1 = False
    # 表格识别：连续三行（表头|分隔|首行数据），分隔行匹配 :?-+:?
    tbl_buf: list[list[str]] = []      # 累积的表格行（每行 = [cells]）

    def _flush_table():
        """把 tbl_buf 转为当前页的 table 字段（如有）。"""
        nonlocal tbl_buf
        if not tbl_buf or cur is None:
            tbl_buf = []
            return
        # 三行模式：header / sep / 至少 1 行 data
        if len(tbl_buf) >= 3 and all(len(r) >= 2 for r in tbl_buf[:2]):
            headers = [c.strip() for c in tbl_buf[0]]
            rows = [[c.strip() for c in r] for r in tbl_buf[2:]]
            cur["type"] = "table"
            cur["headers"] = headers
            cur["rows"] = rows
            for k in ("points", "steps"):
                cur.pop(k, None)
        tbl_buf = []

    def _flush_chart():
        """把 chart_lines 转为当前页的 chart 字段（如有）。"""
        nonlocal chart_lines, in_chart
        if not in_chart or cur is None:
            chart_lines = []
            in_chart = False
            return
        labels, values = [], []
        for cl in chart_lines:
            mr = CHART_ROW_RE.match(cl)
            if mr:
                labels.append(mr.group(1).strip())
                values.append(float(mr.group(2)))
        if labels:
            cur["type"] = "chart"
            cur["chart"] = chart_kind if chart_kind in ("bar", "pie", "line") else "bar"
            cur["data"] = {"labels": labels, "values": values}
            for k in ("points", "steps"):
                cur.pop(k, None)
        chart_lines = []
        in_chart = False

    def close_current():
        nonlocal cur, pending_quote, tbl_buf
        _flush_table()
        _flush_chart()
        if cur is not None:
            if pending_quote:
                cur["notes"] = "\n".join(pending_quote).strip()
            slides.append(cur)
        cur = None
        pending_quote = []
        tbl_buf = []

    for raw in text.splitlines():
        line = raw.rstrip()
        cm = CHART_FENCE.match(line)
        if cm:
            # 进入 chart 代码块采集态（仅当当前页可承载 chart）
            if cur is not None and "points" not in cur and "steps" not in cur \
                    and cur["type"] in ("bullets", "section"):
                in_chart = True
                chart_kind = cm.group(1)
                chart_lines = []
            continue
        if in_chart:
            if CODE_FENCE.match(line):  # 结束代码块
                _flush_chart()
            else:
                chart_lines.append(line)
            continue
        if CODE_FENCE.match(line):
            in_code = not in_code
            continue
        if in_code:
            continue
        m = H_RE.match(line)
        if m:
            level, title = len(m.group(1)), m.group(2).strip()
            close_current()
            if level == 1:
                if not seen_h1:
                    cur = {"type": "title", "title": title}
                    seen_h1 = True
                else:
                    cur = {"type": "section", "title": title}
            else:  # level >= 2 → 内容页
                cur = {"type": "closing", "title": title} \
                    if any(k in title.lower() for k in CLOSING_KEYWORDS) \
                    else {"type": "bullets", "title": title}
            pending_quote = []
            continue
        if cur is None:
            continue
        q = QUOTE_RE.match(line)
        if q:
            if q.group(1).strip():
                pending_quote.append(q.group(1).strip())
            continue
        # 图片行：仅当 cur 还没确定列表类型时识别为 image
        img = IMG_RE.match(line)
        if img and "points" not in cur and "steps" not in cur \
                and cur["type"] in ("bullets", "section", "title"):
            caption = (img.group(3) or img.group(1) or "").strip()
            cur["type"] = "image"
            cur["src"] = img.group(2).strip()
            if caption:
                cur["caption"] = caption
            if pending_quote:
                cur["notes"] = "\n".join(pending_quote).strip()
                pending_quote = []
            continue
        # 表格行：以 | 起始（| a | b |）或含 ≥2 个独立 | 分隔，且当 cur 还未有列表时。
        # 排除：列表项（-/*/+ 开头）、two-col 分隔符 ||（连续竖线）
        is_list_line = UL_RE.match(line) or OL_RE.match(line)
        tbl_candidate = not is_list_line and ("|" in line) and \
            "points" not in cur and "steps" not in cur and cur["type"] == "bullets"
        if tbl_candidate:
            tr = TABLE_ROW_RE.match(line)
            if tr:
                cells = [c.strip() for c in tr.group(1).split("|")]
                tbl_buf.append(cells)
                continue
            elif tbl_buf:
                # 非 | 结尾：flush 已有表格
                _flush_table()
        elif TABLE_SEP_RE.match(line) and tbl_buf:
            # 分隔行（如 |---|---|）累积后等待下一行
            tbl_buf.append([c.strip() for c in TABLE_ROW_RE.match(line).group(1).split("|")])
            continue
        elif tbl_buf:
            # 表格行流中断：flush
            _flush_table()
        if "points" not in cur and "steps" not in cur and cur["type"] == "bullets":
            u = UL_RE.match(line)
            o = OL_RE.match(line)
            if u:
                item = u.group(1)
                if TWO_COL_SEP in item:
                    # two-col 页型：`左 || 右`（首次识别）
                    l, r = item.split(TWO_COL_SEP, 1)
                    cur["type"] = "two-col"
                    cur["left"] = [l.strip()]
                    cur["right"] = [r.strip()]
                else:
                    cur["points"] = [item]
                if pending_quote:
                    cur["notes"] = "\n".join(pending_quote).strip()
                    pending_quote = []
                continue
            if o:
                cur["type"] = "steps"
                cur["steps"] = [{"t": o.group(1), "d": ""}]
                if pending_quote:
                    cur["notes"] = "\n".join(pending_quote).strip()
                    pending_quote = []
                continue
            if cur["type"] in ("bullets", "closing") and pending_quote:
                cur["notes"] = "\n".join(pending_quote).strip()
                pending_quote = []
            continue
        if cur.get("type") == "bullets":
            u = UL_RE.match(line)
            if u:
                item = u.group(1)
                if TWO_COL_SEP in item:
                    # two-col 页型：`左 || 右`
                    l, r = item.split(TWO_COL_SEP, 1)
                    cur["type"] = "two-col"
                    cur["left"] = [l.strip()]
                    cur["right"] = [r.strip()]
                    cur.pop("points", None)
                else:
                    cur["points"].append(item)
                continue
            o = OL_RE.match(line)
            if o:
                cur["points"].append(o.group(1))
                continue
        elif cur.get("type") == "two-col":
            u = UL_RE.match(line)
            if u and TWO_COL_SEP in u.group(1):
                l, r = u.group(1).split(TWO_COL_SEP, 1)
                cur["left"].append(l.strip())
                cur["right"].append(r.strip())
                continue
        elif cur.get("type") == "steps":
            o = OL_RE.match(line)
            if o:
                cur["steps"].append({"t": o.group(1), "d": ""})
                continue
    close_current()
    return slides


def build_spec(args) -> dict:
    md_path = Path(args.md)
    if not md_path.is_file():  # 输入存在性检查（避免 FileNotFoundError traceback）
        print(f"ERROR: markdown 文件不存在: {args.md}", file=sys.stderr)
        sys.exit(2)
    md = md_path.read_text(encoding="utf-8")
    slides = parse_md(md)
    if not slides:
        print("ERROR: no slides parsed from markdown", file=sys.stderr)
        sys.exit(2)
    title = args.title or (slides[0].get("title") if slides[0].get("type") == "title" else "演示文稿")
    meta = {"title": title}
    if args.course:
        meta["course"] = args.course
    return {"meta": meta, "preset": args.preset, "slides": slides}


def preview(spec: dict) -> None:
    print("== md2spec 映射预览 ==")
    print(f"标题: {spec['meta']['title']} | 预设: {spec['preset']} | 页数: {len(spec['slides'])}")
    for i, s in enumerate(spec["slides"], 1):
        t = s["type"]
        if t == "bullets":
            detail = f"{len(s.get('points', []))} 要点"
        elif t == "steps":
            detail = f"{len(s.get('steps', []))} 步骤"
        elif t == "table":
            detail = f"table {len(s.get('headers', []))}×{len(s.get('rows', []))}"
        elif t == "image":
            detail = f"image {s.get('src','')[:30]}"
        elif t == "chart":
            detail = f"chart {s.get('chart','bar')} {len((s.get('data') or {}).get('values', []))} 点"
        elif t == "two-col":
            detail = f"two-col {len(s.get('left', []))} 组"
        else:
            detail = ""
        notes = " [notes]" if s.get("notes") else ""
        print(f"  {i:>2}. [{t:<8}] {s.get('title','')[:40]}{' …' if len(s.get('title',''))>40 else ''}  {detail}{notes}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Markdown outline -> deck.spec.json (zero deps).")
    ap.add_argument("md", help="Path to markdown outline")
    ap.add_argument("-o", "--out", help="Output spec json path")
    ap.add_argument("--title", default=None, help="Deck title (default: first H1)")
    ap.add_argument("--preset", default="academic-light", help="Preset id")
    ap.add_argument("--course", default=None, help="Course name (meta.course, shown in footer)")
    ap.add_argument("--check", action="store_true", help="Print mapping preview only")
    args = ap.parse_args(argv)

    spec = build_spec(args)
    if args.check or not args.out:
        preview(spec)
        return 0
    Path(args.out).write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK wrote {args.out} ({len(spec['slides'])} slides, preset={spec['preset']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
