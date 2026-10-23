#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
md_to_docx.py —— 把综述骨架 Markdown 转成**可编辑的 .docx**（纯标准库）

背景：综述骨架只产出 Markdown，拿到手「不会显示为
可编辑的 Word」。本模块把骨架 Markdown 转成最小但合法的 WordprocessingML
文档（Word / WPS / 腾讯文档均可直接打开编辑）。

支持语法（骨架实际用到的子集）：
    # / ## / ### / ####   标题（映射 Word 内置 Heading 1-4）
    - / * 开头            项目符号段（以「• 」前缀呈现，编辑无门槛）
    1. 开头               编号段（保留原编号字面量）
    > 开头                引用段（缩进 + 灰色斜体）
    **bold**              段内加粗
    | a | b |             简单表格
    ---                   分隔线（空段落 + 底边框省略，转为一行"─"字符）
    普通行                正文段

设计取舍：
    · 不实现完整 Markdown——骨架是受控生成物，语法子集固定，够用且零依赖；
    · 列表用字符前缀而非 numbering.xml——Word/WPS 打开即可编辑，
      避免手写 numbering 映射出错导致文档打不开（宁可朴素，不可损坏）。
"""
from __future__ import annotations

import re
import zipfile
from pathlib import Path

_CT = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>"""

_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""

_STYLES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:style w:type="paragraph" w:styleId="Normal" w:default="1">
 <w:name w:val="Normal"/><w:pPr><w:spacing w:after="120" w:line="276" w:lineRule="auto"/></w:pPr>
 <w:rPr><w:sz w:val="22"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/>
 <w:basedOn w:val="Normal"/><w:pPr><w:outlineLvl w:val="0"/><w:spacing w:before="360" w:after="160"/></w:pPr>
 <w:rPr><w:b/><w:sz w:val="40"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/>
 <w:basedOn w:val="Normal"/><w:pPr><w:outlineLvl w:val="1"/><w:spacing w:before="280" w:after="140"/></w:pPr>
 <w:rPr><w:b/><w:sz w:val="32"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading3"><w:name w:val="heading 3"/>
 <w:basedOn w:val="Normal"/><w:pPr><w:outlineLvl w:val="2"/><w:spacing w:before="240" w:after="120"/></w:pPr>
 <w:rPr><w:b/><w:sz w:val="26"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading4"><w:name w:val="heading 4"/>
 <w:basedOn w:val="Normal"/><w:pPr><w:outlineLvl w:val="3"/><w:spacing w:before="200" w:after="100"/></w:pPr>
 <w:rPr><w:b/><w:sz w:val="24"/></w:rPr></w:style>
</w:styles>"""


def _esc(s: str) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;"))


def _runs(text: str) -> str:
    """把 **bold** 行内标记拆成 w:r 序列。"""
    out = []
    for i, seg in enumerate(re.split(r"\*\*", text)):
        if not seg:
            continue
        rpr = "<w:rPr><w:b/></w:rPr>" if i % 2 == 1 else ""
        out.append(f'<w:r>{rpr}<w:t xml:space="preserve">{_esc(seg)}</w:t></w:r>')
    return "".join(out) or '<w:r><w:t xml:space="preserve"></w:t></w:r>'


def _p(text: str, style: str | None = None, indent: int = 0,
       italic_gray: bool = False) -> str:
    ppr = ""
    props = []
    if style:
        props.append(f'<w:pStyle w:val="{style}"/>')
    if indent:
        props.append(f'<w:ind w:left="{indent}"/>')
    if props:
        ppr = "<w:pPr>" + "".join(props) + "</w:pPr>"
    if italic_gray:
        return (f'<w:p>{ppr}<w:r><w:rPr><w:i/><w:color w:val="606060"/></w:rPr>'
                f'<w:t xml:space="preserve">{_esc(text)}</w:t></w:r></w:p>')
    return f"<w:p>{ppr}{_runs(text)}</w:p>"


def _table(rows: list[str]) -> str:
    """| a | b | 行序列 → 简单表格（首行按表头加粗，次行是分隔线时跳过）。"""
    parsed = []
    for r in rows:
        cells = [c.strip() for c in r.strip().strip("|").split("|")]
        if cells and all(re.fullmatch(r":?-{3,}:?", c) for c in cells):
            continue                      # 分隔行
        parsed.append(cells)
    if not parsed:
        return ""
    ncol = max(len(r) for r in parsed)
    w = int(9360 / ncol)
    xml = ['<w:tbl><w:tblPr><w:tblW w:w="9360" w:type="dxa"/>'
           '<w:tblBorders>'
           + "".join(f'<w:{b} w:val="single" w:sz="4" w:color="BFBFBF"/>'
                     for b in ("top", "left", "bottom", "right", "insideH", "insideV"))
           + "</w:tblBorders></w:tblPr>"]
    for ri, cells in enumerate(parsed):
        xml.append("<w:tr>")
        for c in cells + [""] * (ncol - len(cells)):
            bold = "<w:rPr><w:b/></w:rPr>" if ri == 0 else ""
            xml.append(
                f'<w:tc><w:tcPr><w:tcW w:w="{w}" w:type="dxa"/></w:tcPr>'
                f'<w:p><w:r>{bold}<w:t xml:space="preserve">{_esc(c)}</w:t></w:r></w:p></w:tc>')
        xml.append("</w:tr>")
    xml.append("</w:tbl>")
    return "".join(xml)


def markdown_to_docx_bytes(md_text: str, title: str | None = None) -> bytes:
    """Markdown 文本 → 合法 .docx 字节流。"""
    body: list[str] = []
    if title:
        body.append(_p(title, "Title" if False else "Heading1"))
    lines = md_text.splitlines()
    i = 0
    while i < len(lines):
        ln = lines[i]
        s = ln.strip()
        if not s:
            i += 1
            continue
        m = re.match(r"^(#{1,4})\s+(.*)$", s)
        if m:
            style = f"Heading{len(m.group(1))}"
            body.append(_p(m.group(2).replace("**", ""), style))
            i += 1
            continue
        if s.startswith("|") and i + 1 < len(lines) and "|" in lines[i + 1]:
            block = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                block.append(lines[i])
                i += 1
            body.append(_table(block))
            body.append("<w:p/>")
            continue
        if s.startswith(">"):
            body.append(_p(s.lstrip("> ").strip(), indent=480, italic_gray=True))
            i += 1
            continue
        if re.fullmatch(r"-{3,}|\*{3,}", s):
            body.append(_p("─" * 32))
            i += 1
            continue
        m = re.match(r"^[-*]\s+(.*)$", s)
        if m:
            body.append(_p("•  " + m.group(1), indent=360))
            i += 1
            continue
        m = re.match(r"^(\d+)[.、)]\s+(.*)$", s)
        if m:
            body.append(_p(f"{m.group(1)}. {m.group(2)}", indent=360))
            i += 1
            continue
        body.append(_p(s))
        i += 1

    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body>" + "".join(body) +
        '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
        '<w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/></w:sectPr>'
        "</w:body></w:document>")

    import io
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", _CT)
        z.writestr("_rels/.rels", _RELS)
        z.writestr("word/document.xml", document)
        z.writestr("word/styles.xml", _STYLES)
    return buf.getvalue()


def write_docx(out_path: str | Path, md_text: str, title: str | None = None) -> Path:
    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(markdown_to_docx_bytes(md_text, title=title))
    return p
