#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""import_refs.py — 导入 EndNote / Zotero 导出的文献库，转为 READINGS 兼容语料。

支持格式（按扩展名 + 内容嗅探自动判定）：
  - EndNote  : .enl（压缩 XML）/ EndNote XML（.xml，含 <record>）/ .ris / .bib
  - Zotero   : .ris / .bib（BibTeX）/ .rdf（Zotero RDF/FOAF）/ Better BibTeX .json

双材料工作流（关键）：
  ① 题录材料  —— 上述任一格式的导出文件，提供「谁写了什么 / 出处 / DOI」等元数据；
  ② 分析总结  —— 用户用 EndNote/Zotero 分析文献内容、撰写综述后导出的总结文档（.md/.txt），
                 或题录内附的 notes/注释字段。由于 EndNote 无法读取本地 PDF，文献「内容层」
                 的分析与总结须由用户单独导出提供，本工具不臆造。

输出：READINGS 兼容 Markdown（「文献条目」块 + 明细表 + 题录内附注释 + 用户分析总结段），
      供文献综述路径 L2-L3 消费。reading code（SPL/CPL/GAP/RAT/ROF）仍由人工标注，不臆造。

纯标准库实现（无第三方依赖），失败明确报错、绝不静默。

用法：
  python import_refs.py <citation_file> [--summary <分析总结.md>] [--out READINGS.imported.md] [--source auto|endnote|zotero]
  python import_refs.py refs.ris --summary 我的文献综述.md        # 题录 + 用户分析总结 双材料
"""
import argparse
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from html import unescape

# ---- 输出路径安全校验（复用套件约定：仅允许工作区内） ----
try:
    _skills_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.path.append(os.path.join(_skills_root, "obhrm-methodology"))
    from obhrm_research_base.core.safe_path import resolve_safe_output  # noqa: E402
    _HAVE_SAFE = True
except Exception:
    _HAVE_SAFE = False


# --------------------------------------------------------------------------- #
# 通用解析工具
# --------------------------------------------------------------------------- #
def _clean(t):
    if not t:
        return ""
    return unescape(re.sub(r"\s+", " ", t)).strip()


def _split_authors(s):
    if not s:
        return []
    # BibTeX: "Last, First and Last2, First2"; RIS: 多行 AU; 其余: "; " 或 ", "
    s = s.strip()
    if " and " in s:
        return [a.strip() for a in s.split(" and ") if a.strip()]
    if ";" in s:
        return [a.strip() for a in s.split(";") if a.strip()]
    if "," in s and " and " not in s:
        # 可能 "Last, First, Last2, First2" 或 "A, B, C"（三人逗号分隔）
        parts = [p.strip() for p in s.split(",")]
        if len(parts) >= 4 and len(parts) % 2 == 0:
            return ["{}, {}".format(parts[i], parts[i + 1]).strip(", ")
                    for i in range(0, len(parts), 2)]
        return [p for p in parts if p]
    return [s]


def _first_authors(authors, n=3):
    if not authors:
        return "Anon"
    if len(authors) <= n:
        return ", ".join(authors)
    return ", ".join(authors[:n]) + " et al."


# --------------------------------------------------------------------------- #
# 格式嗅探
# --------------------------------------------------------------------------- #
def detect_format(text, ext):
    ext = (ext or "").lower()
    if ext == ".enl":
        return "endnote_enl"
    if "TY  -" in text[:4000] or re.search(r"(?m)^[A-Z][A-Z0-9]  - ", text):
        return "ris"
    if ext == ".bib" or text.lstrip().startswith("@"):
        return "bibtex"
    if "<record>" in text or "<records>" in text or "rec_number" in text:
        return "endnote_xml"
    if "xmlns" in text and ("rdf:" in text or "bibo:" in text or "Zotero" in text):
        return "zotero_rdf"
    if ext == ".json" or text.lstrip().startswith("{"):
        try:
            obj = json.loads(text)
            if isinstance(obj, dict) and ("items" in obj or "references" in obj):
                return "betterbibtex_json"
        except Exception:
            pass
    if ext in (".ris",):
        return "ris"
    if ext in (".bib",):
        return "bibtex"
    if ext in (".rdf", ".xml"):
        return "zotero_rdf"
    return "unknown"


# --------------------------------------------------------------------------- #
# RIS 格式
# --------------------------------------------------------------------------- #
def parse_ris(text):
    recs = []
    cur = {}
    tag_re = re.compile(r"^(?P<tag>[A-Z][A-Z0-9]{1,2})\s*-\s*(?P<val>.*)$")
    for line in text.splitlines():
        m = tag_re.match(line.rstrip("\n"))
        if not m:
            continue
        tag, val = m.group("tag"), m.group("val").strip()
        if tag == "ER":  # end of record
            if cur:
                recs.append(cur)
            cur = {}
            continue
        if tag in ("AU", "A1", "A2", "A3", "A4"):
            cur.setdefault("authors", []).append(val)
        elif tag in ("TI", "T1"):
            cur["title"] = (cur.get("title", "") + " " + val).strip()
        elif tag in ("JO", "JF", "JA", "T2"):
            cur["journal"] = val
        elif tag in ("Y1", "PY"):
            cur["year"] = re.sub(r"\s.*", "", val)
        elif tag == "DO":
            cur["doi"] = val
        elif tag == "UR":
            cur["url"] = val
        elif tag in ("AB", "N2"):
            cur["abstract"] = (cur.get("abstract", "") + " " + val).strip()
        elif tag == "N1":
            cur.setdefault("notes", []).append(val)
        elif tag == "KW":
            cur.setdefault("keywords", []).append(val)
        elif tag == "TY":
            cur["type"] = val
        elif tag in ("SP", "EP", "VL", "IS"):
            cur.setdefault("meta", {})[tag] = val
    if cur:
        recs.append(cur)
    return recs


# --------------------------------------------------------------------------- #
# BibTeX 格式
# --------------------------------------------------------------------------- #
_BIB_ENTRY_RE = re.compile(
    r"@(?P<type>\w+)\s*\{\s*(?P<key>[^,]+),", re.IGNORECASE)
_BIB_FIELD_RE = re.compile(
    r"(?P<name>[a-zA-Z_]+)\s*=\s*(?P<val>\{[^{}]*\}|\[[^\]]*\]|\"[^\"]*\"|[^,}\n]+)")


def _strip_braces(v):
    v = v.strip()
    if v.startswith("{") and v.endswith("}"):
        return v[1:-1]
    if v.startswith('"') and v.endswith('"'):
        return v[1:-1]
    if v.startswith("[") and v.endswith("]"):
        return v[1:-1]
    return v.strip()


def parse_bibtex(text):
    recs = []
    pos = 0
    for m in _BIB_ENTRY_RE.finditer(text):
        start = m.end()
        # 查找匹配的右花括号
        depth = 1
        i = start
        while i < len(text) and depth > 0:
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
            i += 1
        body = text[start:i - 1]
        cur = {"type": m.group("type").lower(), "key": m.group("key").strip()}
        for fm in _BIB_FIELD_RE.finditer(body):
            name = fm.group("name").lower()
            val = _strip_braces(fm.group("val"))
            if name in ("author", "editor"):
                cur["authors"] = _split_authors(val)
            elif name == "title":
                cur["title"] = val.replace("{", "").replace("}", "")
            elif name in ("journal", "booktitle"):
                cur["journal"] = val.replace("{", "").replace("}", "")
            elif name == "year":
                cur["year"] = re.sub(r"\D.*", "", val)
            elif name == "doi":
                cur["doi"] = val
            elif name == "url":
                cur["url"] = val
            elif name == "abstract":
                cur["abstract"] = val.replace("{", "").replace("}", "")
            elif name == "keywords":
                cur["keywords"] = [k.strip() for k in val.replace("{", "").replace("}", "").split(",")]
        recs.append(cur)
    return recs


# --------------------------------------------------------------------------- #
# EndNote XML 格式
# --------------------------------------------------------------------------- #
def parse_endnote_xml(text):
    recs = []
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return recs
    records = root.iter("record") if root.tag != "record" else [root]
    for rec in records:
        cur = {}
        # 标题
        titles = rec.find("titles")
        if titles is not None:
            t = titles.findtext("title")
            if t:
                cur["title"] = _clean(t)
        # 作者/贡献者
        contrib = rec.find("contributors")
        if contrib is not None:
            authors = []
            for au in contrib.iter("author"):
                if au.text and au.text.strip():
                    authors.append(_clean(au.text))
            if authors:
                cur["authors"] = authors
        # 日期
        dates = rec.find("dates")
        if dates is not None:
            y = dates.findtext("year")
            if y:
                cur["year"] = _clean(y)
        # 期刊
        per = rec.find("periodical")
        if per is not None:
            jt = per.findtext("full-title") or per.findtext("abbreviated-title")
            if jt:
                cur["journal"] = _clean(jt)
        # DOI / URL / 摘要 / 注释
        for tag in ("doi", "abstract", "notes"):
            v = rec.findtext(tag)
            if v:
                if tag == "notes":
                    cur.setdefault("notes", []).append(_clean(v))
                else:
                    cur[tag] = _clean(v)
        ur = rec.find("urls")
        if ur is not None:
            pdf = ur.findtext("pdf-urls")
            if pdf:
                cur["url"] = _clean(pdf)
        # 类型
        t = rec.findtext("ref-type")
        if t:
            cur["type"] = _clean(t)
        recs.append(cur)
    return recs


# --------------------------------------------------------------------------- #
# Zotero RDF 格式
# --------------------------------------------------------------------------- #
def parse_zotero_rdf(text):
    recs = []
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return recs
    ns = {
        "bibo": "http://purl.org/ontology/bibo/",
        "dc": "http://purl.org/dc/elements/1.1/",
        "prism": "http://prismstandard.org/namespaces/basic/2.0/",
        "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        "foaf": "http://xmlns.com/foaf/0.1/",
    }
    for art in root.findall(".//*[@rdf:about]", ns):
        cur = {}
        title = art.findtext("{%s}title" % ns["dc"])
        if title:
            cur["title"] = _clean(title)
        # 作者（authorList）
    al = art.find("{%(bibo)s}authorList" % ns)
    authors = []
    if al is not None:
        for desc in al.findall(".//{%(rdf)s}Description" % ns):
            fam = desc.findtext("{%(dc)s}familyName" % ns)
            giv = desc.findtext("{%(dc)s}givenName" % ns)
            nm = desc.findtext("{%(foaf)s}name" % ns)
            if fam or giv:
                authors.append(_clean((fam or "").strip() + (", " + (giv or "").strip() if giv else "")))
            elif nm:
                authors.append(_clean(nm))
        if authors:
            cur["authors"] = authors
        j = art.find("{%(bibo)s}Journal" % ns)
        if j is not None:
            jt = j.findtext("{%(dc)s}title" % ns)
            if jt:
                cur["journal"] = _clean(jt)
        yr = art.findtext("{%(dc)s}date" % ns)
        if yr:
            cur["year"] = re.sub(r"\D.*", "", yr)
        doi = art.findtext("{%(prism)s}doi" % ns) or art.findtext("{%(bibo)s}doi" % ns)
        if doi:
            cur["doi"] = _clean(doi)
        desc = art.findtext("{%(dc)s}description" % ns)
        if desc:
            cur.setdefault("notes", []).append(_clean(desc))
        recs.append(cur)
    return recs


# --------------------------------------------------------------------------- #
# Better BibTeX JSON 格式
# --------------------------------------------------------------------------- #
def parse_betterbibtex_json(text):
    recs = []
    obj = json.loads(text)
    items = obj.get("items") or obj.get("references") or []
    for it in items:
        cur = {}
        fields = it.get("fields", {}) if isinstance(it, dict) else {}
        # Zotero BBT 结构：item.fields.{title,date,publicationTitle,doi,...}, item.creators[]
        if "fields" in it:
            f = it["fields"]
            cur["title"] = _clean(f.get("title", ""))
            cur["journal"] = _clean(f.get("publicationTitle", "") or f.get("bookTitle", ""))
            cur["year"] = re.sub(r"\D.*", "", str(f.get("date", "")))
            cur["doi"] = _clean(f.get("doi", ""))
            cur["abstract"] = _clean(f.get("abstractNote", ""))
            cur["url"] = _clean(f.get("url", ""))
        elif "title" in it:
            cur["title"] = _clean(it.get("title", ""))
            cur["journal"] = _clean(it.get("container-title", "") or it.get("publication", ""))
            cur["year"] = re.sub(r"\D.*", "", str(it.get("issued", it.get("year", ""))))
            cur["doi"] = _clean(it.get("DOI", ""))
        creators = it.get("creators", []) if isinstance(it, dict) else []
        authors = []
        for c in creators:
            if isinstance(c, dict):
                nm = c.get("lastName") or c.get("family") or c.get("name")
                if nm:
                    authors.append(_clean(str(nm)))
            elif isinstance(c, str):
                authors.append(_clean(c))
        if authors:
            cur["authors"] = authors
        notes = it.get("notes") or []
        if isinstance(notes, list):
            for nn in notes:
                if isinstance(nn, dict) and nn.get("note"):
                    cur.setdefault("notes", []).append(_clean(nn["note"]))
                elif isinstance(nn, str):
                    cur.setdefault("notes", []).append(_clean(nn))
        if cur.get("title"):
            recs.append(cur)
    return recs


# --------------------------------------------------------------------------- #
# 归一 + 输出
# --------------------------------------------------------------------------- #
def normalize(recs):
    out = []
    for r in recs:
        authors = r.get("authors") or []
        raw_notes = r.get("notes") or []
        notes = [_clean(n) for n in raw_notes if _clean(n)]
        out.append({
            "authors": authors,
            "author_str": _first_authors(authors),
            "year": str(r.get("year", "")).strip(),
            "title": _clean(r.get("title", "")),
            "journal": _clean(r.get("journal", "")),
            "doi": _clean(r.get("doi", "")),
            "url": _clean(r.get("url", "")),
            "type": _clean(r.get("type", "")),
            "notes": notes,
        })
    return [o for o in out if o["title"] or o["author_str"] != "Anon"]


def render_markdown(entries, source, summary_text=None):
    lines = []
    lines.append("# 导入文献库（%s，READINGS 兼容语料）" % source)
    lines.append("")
    lines.append("> 由 `reference-import` 技能解析 EndNote/Zotero 导出生成。**双材料工作流**：本文件含 ① 题录（谁写了什么/出处/DOI）；"
                 "② 题录内附注释（如导出时带 notes）；③ 用户单独提供的文献分析/总结（见文末「用户文献分析 / 总结」段）。"
                 "注意：EndNote 无法读取本地 PDF，文献「内容层」的分析与总结须由用户导出提供，本导入不臆造。"
                 "reading code（SPL/CPL/GAP/RAT/ROF）需由文献综述路径按 `select_deepread.py` 人工标注。")
    lines.append("")
    lines.append("## 文献条目（供闭环引证核验）")
    lines.append("")
    for e in entries:
        y = " (%s)" % e["year"] if e["year"] else ""
        suffix = ""
        if e["journal"]:
            suffix = " *%s*." % e["journal"]
        if e["doi"]:
            suffix += " DOI:%s" % e["doi"]
        lines.append("- %s%s. %s.%s" % (e["author_str"], y, e["title"], suffix))
    lines.append("")
    lines.append("## 明细（导入来源：%s）" % source)
    lines.append("")
    lines.append("| # | 作者 | 年 | 题名 | 出处 | DOI | 类型 |")
    lines.append("|---|------|----|------|------|-----|------|")
    for i, e in enumerate(entries, 1):
        lines.append("| %d | %s | %s | %s | %s | %s | %s |" % (
            i, e["author_str"], e["year"], e["title"], e["journal"],
            e["doi"], e["type"]))
    lines.append("")
    # ② 题录内附注释 / 笔记（来自导出文件的 notes 字段）
    notes_entries = [(i, e) for i, e in enumerate(entries, 1) if e.get("notes")]
    if notes_entries:
        lines.append("## 题录内附注释 / 笔记")
        lines.append("")
        lines.append("> 以下注释提取自题录导出文件的 notes 字段（EndNote/Zotero 中用户添加的批注）。")
        lines.append("")
        for i, e in notes_entries:
            lines.append("**【%d】%s** — %s" % (i, e["title"], e["author_str"]))
            for n in e["notes"]:
                lines.append("- %s" % n)
            lines.append("")
    # ③ 用户单独提供的文献分析 / 总结
    if summary_text and summary_text.strip():
        lines.append("## 用户文献分析 / 总结（由导入者提供）")
        lines.append("")
        lines.append("> 以下内容由用户用 EndNote/Zotero 分析文献后导出，或自行撰写的综述/总结，**原样保留、未改写**。")
        lines.append("> 文献综述路径在引用其中观点时，须显式标注来源并与其题录条目（上文明细）交叉核验，不得凭记忆补文献。")
        lines.append("")
        lines.append(summary_text.strip())
        lines.append("")
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description="导入 EndNote/Zotero 文献库 → READINGS 兼容语料")
    ap.add_argument("file", help="题录输入文件（.enl/.xml/.ris/.bib/.rdf/.json）")
    ap.add_argument("--summary", default=None,
                    help="用户文献分析/总结文档（.md/.txt 等纯文本），与原题录双材料合并导入")
    ap.add_argument("--out", default="READINGS.imported.md", help="输出 Markdown 路径")
    ap.add_argument("--source", default="auto", help="auto|endnote|zotero")
    args = ap.parse_args()

    if not os.path.isfile(args.file):
        sys.stderr.write("[import_refs] 文件不存在: %s\n" % args.file)
        return 2
    summary_text = None
    if args.summary:
        if not os.path.isfile(args.summary):
            sys.stderr.write("[import_refs] 分析总结文件不存在: %s\n" % args.summary)
            return 2
        with open(args.summary, "r", encoding="utf-8", errors="replace") as sfh:
            summary_text = sfh.read()
    with open(args.file, "r", encoding="utf-8", errors="replace") as fh:
        text = fh.read()

    ext = os.path.splitext(args.file)[1].lower()
    fmt = detect_format(text, ext)
    if fmt == "unknown":
        sys.stderr.write("[import_refs] 无法识别格式: %s（支持 EndNote/.enl/.xml/.ris、Zotero/.ris/.bib/.rdf/.json）\n" % args.file)
        return 3

    parsers = {
        "ris": parse_ris,
        "bibtex": parse_bibtex,
        "endnote_xml": parse_endnote_xml,
        "zotero_rdf": parse_zotero_rdf,
        "betterbibtex_json": parse_betterbibtex_json,
    }
    if fmt == "endnote_enl":
        # .enl 是压缩 XML，尝试解压
        try:
            import zlib, base64
            raw = base64.b64decode(text.strip())
            text = zlib.decompress(raw).decode("utf-8", "replace")
            fmt = "endnote_xml"
        except Exception:
            sys.stderr.write("[import_refs] .enl 解压失败，请改从 EndNote 导出 XML 后导入\n")
            return 4

    recs = parsers.get(fmt, lambda t: [])(text)
    entries = normalize(recs)
    if not entries:
        sys.stderr.write("[import_refs] 未解析到任何文献条目（格式=%s），请检查导出设置\n" % fmt)
        return 5

    md = render_markdown(entries, args.source if args.source != "auto" else fmt, summary_text)
    out_path = args.out
    if _HAVE_SAFE:
        try:
            out_path = resolve_safe_output(out_path)
        except ValueError as exc:
            # 越界（`..` 上跳或工作区外绝对路径）一律拒绝写出，绝不静默放行
            sys.stderr.write("[import_refs] 输出路径越界，已拒绝写出: %s\n" % exc)
            return 6
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(md)
    sys.stdout.write("[import_refs] 格式=%s 解析 %d 条 → %s\n" % (fmt, len(entries), out_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
