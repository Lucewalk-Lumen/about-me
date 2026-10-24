#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
import_sources.py —— 多来源文献导入器（Zotero / NoteExpress / CNKI / WoS / Scopus）

用法:
    python3 import_sources.py <文件或目录> [更多文件...] [--format auto]
                           [--out refs.json] [--dedup] [--csv out.csv]

为什么需要它
------------
EndNote 无官方 API，本包原本直读 .enl。但**用户未必用 EndNote**：
  · Zotero        → 本机即有 zotero.sqlite（SQLite，可只读直读，无需导出）
  · NoteExpress   → 私有二进制库，**无只读直读方案**，须导出 RIS / EndNote XML
  · CNKI / 万方 / VIP → 无 API，须导出 RIS / EndNote XML / Refworks
  · WoS / Scopus / CSSCI → 须导出 CSV（带表头）或 RIS
本脚本把这些来源统一归一为 `refs.json`（内部 Ref[] 结构），
下游 6 个分析模块经 `load_refs()` 透明读取，**代码零改动**。

零静默丢弃
----------
每条记录必须归入某个 tier（有摘要/仅关键词/仅标题/空），tier 四类和 == 导入总数。
被去重丢弃的记录单独计数并可导出，绝不静默消失。

退出码
------
    0  成功（含"部分来源失败但至少一个成功"）
    1  输入不存在
    2  格式无法识别
    4  参数错误
    5  计算失败
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sqlite3
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from endnote_core import (  # noqa: E402
    EXIT, EnlError, SOURCE_LABELS, coverage_report, emit, esc_csv_cell, make_ref,
    refs_to_json,
)

_YEAR = re.compile(r"(?:19|20)\d{2}")


def _year(v) -> int | None:
    if not v:
        return None
    m = _YEAR.search(str(v))
    return int(m.group(0)) if m else None


def _read_text(path: Path) -> str:
    """按 UTF-8 → GB18030 → GBK → BIG5 顺序解码，errors=replace 兜底。

    CNKI / NoteExpress 的导出**编码不统一**（同一批文件里 UTF-8 与 GBK 混存），
    故必须逐级尝试；实测本批 6 个样本全为 UTF-8，但不能假定。
    """
    b = Path(path).read_bytes()
    for enc in ("utf-8-sig", "utf-8", "gb18030", "gbk", "big5"):
        try:
            return b.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return b.decode("utf-8", errors="replace")


def _norm_title(t: str) -> str:
    """标题归一（用于跨来源去重）：lower + 去标点 + 压缩空白。"""
    t = unicodedata.normalize("NFKC", (t or "")).lower()
    t = re.sub(r"[^\w\s]", " ", t, flags=re.U)
    return re.sub(r"\s+", " ", t).strip()


# ══════════════════════════════════════════════════════════
# 1. Zotero 原生库（zotero.sqlite，只读）
# ══════════════════════════════════════════════════════════
def load_zotero(db: Path) -> list:
    """直读 Zotero 的 zotero.sqlite（只读）。无需 Zotero 导出。

    关键表：items / itemTypes / itemData+fields+itemDataValues /
    itemCreators+creators / itemTags+tags / itemAttachments / deletedItems。
    ⚠️ 必须排除 itemType in (attachment, note, annotation) —— 它们不是文献条目。
    ⚠️ 必须排除 deletedItems —— 回收站条目。
    """
    uri = f"file:{db}?mode=ro"
    con = sqlite3.connect(uri, uri=True)
    con.execute("PRAGMA query_only = 1")
    cur = con.cursor()

    def has_table(t: str) -> bool:
        return bool(cur.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (t,)
        ).fetchone())

    if not has_table("items"):
        con.close()
        raise EnlError(2, f"不是 Zotero 库（缺 items 表）：{db.name}")

    # 仅用户库（libraryID 关联 libraries.type='user'），排除组库重复
    deleted = "d.itemID IS NOT NULL" if has_table("deletedItems") else "0"
    join_del = "LEFT JOIN deletedItems d ON i.itemID=d.itemID" if has_table("deletedItems") else ""
    if has_table("libraries"):
        lib_clause = (" AND i.libraryID IN "
                      "(SELECT libraryID FROM libraries WHERE type='user')")
    else:
        lib_clause = ""

    # 删除项与附件项的排除必须写在 WHERE；若并入 LEFT JOIN 的 ON 子句，
    # 被删条目会以 NULL 行通过而混入结果。
    sql = (f"SELECT i.itemID, it.typeName FROM items i "
           f"JOIN itemTypes it ON i.itemTypeID=it.itemTypeID {join_del} "
           f"WHERE {deleted}=0 {lib_clause} "
           f"AND it.typeName NOT IN ('attachment','note','annotation')")
    items = cur.execute(sql).fetchall()

    out = []
    for item_id, _type in items:
        fmap = {}
        for fname, val in cur.execute(
            "SELECT f.fieldName, v.value FROM itemData id "
            "JOIN fields f ON id.fieldID=f.fieldID "
            "JOIN itemDataValues v ON id.valueID=v.valueID "
            "WHERE id.itemID=?", (item_id,)
        ):
            fmap.setdefault(fname, val)

        authors, author_list = [], []
        for fn, ln in cur.execute(
            "SELECT c.firstName, c.lastName FROM itemCreators ic "
            "JOIN creators c ON ic.creatorID=c.creatorID "
            "WHERE ic.itemID=? ORDER BY ic.orderIndex", (item_id,)
        ):
            nm = f"{ln}, {fn}".strip(", ") if fn else (ln or "")
            if nm:
                authors.append(nm)
                author_list.append(nm)

        kws = [t for (t,) in cur.execute(
            "SELECT t.name FROM itemTags it JOIN tags t ON it.tagID=t.tagID "
            "WHERE it.itemID=?", (item_id,))]

        doi = (fmap.get("DOI") or "").strip()
        if not doi:  # Zotero 常把 DOI 塞在 extra 里
            m = re.search(r"(10\.\d{4,9}/\S+)", fmap.get("extra", "") or "")
            doi = m.group(1) if m else ""

        has_pdf = False
        if has_table("itemAttachments"):
            has_pdf = bool(cur.execute(
                "SELECT 1 FROM itemAttachments WHERE parentItemID=? "
                "AND contentType='application/pdf' LIMIT 1", (item_id,)
            ).fetchone())

        out.append(make_ref(
            rid=item_id,
            title=fmap.get("title", ""),
            abstract=fmap.get("abstractNote", ""),
            keywords=kws,
            year=_year(fmap.get("date")),
            journal=fmap.get("publicationTitle") or fmap.get("bookTitle") or "",
            authors="\r".join(authors),          # parse_authors 期望 \r 分隔
            doi=doi,
            has_pdf=has_pdf,
            author_list=_canon_from_display(authors),
        ))
    con.close()
    return out


def _canon_from_display(names: list[str]) -> list[str]:
    """['Smith, John A.'] → ['smith|ja']，与 EndNote 侧口径一致。"""
    from endnote_core import parse_authors
    return parse_authors("\r".join(names))


# ══════════════════════════════════════════════════════════
# 2. RIS（CNKI / WoS / Scopus / NoteExpress 通用导出）
# ══════════════════════════════════════════════════════════
_RIS_LINE = re.compile(r"^([A-Z][A-Z0-9])\s{2}-\s?(.*)$")


def load_ris(path: Path) -> list:
    """解析 RIS。记录以 `ER  -` 结束，字段为 `XX  - value`。

    字段映射：TI/T1=标题 AB/N2=摘要 KW=关键词 PY/Y1/DA=年份
              JO/JF/T2=期刊 AU/A1=作者 DO/UR=DOI
    """
    refs, cur = [], {}
    last = None
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = _RIS_LINE.match(raw.rstrip())
        if not m:
            continue
        tag, val = m.group(1), m.group(2).strip()
        if tag == "ER":
            if cur:
                refs.append(_ref_from_fields(cur, path, len(refs) + 1))
            cur, last = {}, None
            continue
        if tag in ("TI", "T1"):
            cur["title"] = val
        elif tag in ("AB", "N2"):
            cur["abstract"] = cur.get("abstract", "") + " " + val
        elif tag == "KW":
            cur.setdefault("keywords", []).append(val)
        elif tag in ("PY", "Y1"):
            # ⚠️ 年份必须以 PY/Y1 为准。实测 WoS RIS 的标签顺序是
            #    DA - FEB 10 → PY - 2025，用 setdefault 会让不含年份的
            #    日期串先占位，导致 PY 被忽略、该记录年份变 None
            #    （实测 .ris 年份区间被压成 2024-2024，直接影响 F3 时效性）。
            cur["year"] = val
        elif tag == "DA":
            cur.setdefault("year", val)
        elif tag in ("JO", "JF", "T2"):
            cur.setdefault("journal", val)
        elif tag in ("AU", "A1"):
            cur.setdefault("authors", []).append(val)
        elif tag in ("DO", "UR"):
            if tag == "DO" or not cur.get("doi"):
                cur["doi"] = val
        last = tag
    if cur:
        refs.append(_ref_from_fields(cur, path, len(refs) + 1))
    return refs


# ══════════════════════════════════════════════════════════
# 3. BibTeX
# ══════════════════════════════════════════════════════════
def _match_braces(s: str, i: int) -> tuple[str, int]:
    """从 s[i]=='{' 起做花括号配平，返回 (含外层花括号的片段, 结束位置)。"""
    depth = 0
    for j in range(i, len(s)):
        if s[j] == "{":
            depth += 1
        elif s[j] == "}":
            depth -= 1
            if depth == 0:
                return s[i:j + 1], j + 1
    return s[i:], len(s)


def _split_top(s: str) -> list[str]:
    """按顶层逗号切分（花括号/引号内的逗号不切）。"""
    out, depth, cur = [], 0, []
    for ch in s:
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        if ch == "," and depth == 0:
            out.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    if cur:
        out.append("".join(cur))
    return out


def _clean_bib_value(v: str) -> str:
    """去掉最外层花括号/引号 + 简单 LaTeX 清理 + 压缩空白。"""
    v = v.strip()
    if len(v) >= 2 and ((v[0] == "{" and v[-1] == "}") or (v[0] == '"' and v[-1] == '"')):
        v = v[1:-1]
    v = v.replace("\\&", "&").replace("\\_", "_").replace("\\%", "%")
    v = re.sub(r"\\[a-zA-Z]+\s*", " ", v)      # \textit{} \newline 等
    v = re.sub(r"[{}]", "", v)
    return re.sub(r"\s+", " ", v).strip()


def load_bibtex(path: Path) -> list:
    """解析 BibTeX。

    实现要点：不能用「按行 + 逗号」切字段（字段值内含逗号与嵌套花括号，
    早期版本实测导致 year/keywords/doi 全部丢失）。改为：
      1. 花括号配平取出整条 entry；
      2. 顶层逗号切分（_split_top）；
      3. 首段为引用键，其余 `key = value`。
    """
    txt = path.read_text(encoding="utf-8", errors="replace")
    out = []
    for m in re.finditer(r"@(\w+)\s*\{", txt):
        etype = m.group(1).lower()
        if etype in ("comment", "string", "preamble"):
            continue
        body, _end = _match_braces(txt, m.end() - 1)
        parts = _split_top(body[1:-1])
        if not parts:
            continue
        fields = {}
        for p in parts[1:]:
            if "=" not in p:
                continue
            k, v = p.split("=", 1)
            k = k.strip().lower()
            if k:
                fields[k] = _clean_bib_value(v)
        d = {
            "title": fields.get("title", ""),
            "abstract": fields.get("abstract", ""),
            "journal": fields.get("journal") or fields.get("booktitle", ""),
            "year": fields.get("year", ""),
            "doi": fields.get("doi", ""),
            "keywords": [k.strip() for k in
                         re.split(r"[;,]", fields.get("keywords", "")) if k.strip()],
            "authors": [a.strip() for a in
                        re.split(r"\s+and\s+", fields.get("author", "")) if a.strip()],
        }
        d["_display"] = d["authors"]
        out.append(_ref_from_fields(d, path, len(out) + 1, multi_author=True))
    return out


# ══════════════════════════════════════════════════════════
# 4. EndNote XML（.enw / .xml）
# ══════════════════════════════════════════════════════════
_RE_EN = re.compile(r"<[^>]+>")


def _xml_text(s: str) -> str:
    """提取 XML 文本。

    必须先保护 CDATA 再去标签：`<[^>]+>` 会把
    `<![CDATA[…正文…]]>` 整段（含正文）匹配掉，导致标题为空。
    """
    if not s:
        return ""
    # 1) CDATA 内容先用占位符保护
    stash: list[str] = []

    def _keep(m):
        stash.append(m.group(1))
        return f"\x00CDATA{len(stash) - 1}\x00"

    s = re.sub(r"<!\[CDATA\[(.*?)\]\]>", _keep, s, flags=re.S)
    # 2) 去其余标签 + 反转义
    s = re.sub(r"<[^>]+>", " ", s)
    s = (s.replace("&lt;", "<").replace("&gt;", ">")
          .replace("&quot;", '"').replace("&apos;", "'")
          .replace("&amp;", "&"))
    # 3) 还原 CDATA（其内容为字面量，不再做实体反转义）
    for i, raw in enumerate(stash):
        s = s.replace(f"\x00CDATA{i}\x00", raw)
    return re.sub(r"\s+", " ", s).strip()


def load_endnote_xml(path: Path) -> list:
    """解析 EndNote XML / NoteExpress 导出的 .enw。"""
    txt = path.read_text(encoding="utf-8", errors="replace")
    out = []
    for rec in re.findall(r"<record>(.*?)</record>", txt, re.S | re.I):
        def g(tag, inner=r"(.*?)"):
            m = re.search(rf"<{tag}>{inner}</{tag}>", rec, re.S | re.I)
            return _xml_text(m.group(1)) if m else ""
        titles = re.search(r"<titles>(.*?)</titles>", rec, re.S | re.I)
        t = g("title")
        j = ""
        if titles:
            j = _xml_text(re.search(r"<secondary-title>(.*?)</secondary-title>",
                                    titles.group(1), re.S | re.I).group(1)
                          ) if re.search(r"<secondary-title>", titles.group(1), re.I) else ""
        auths = []
        for a in re.findall(r"<author>(.*?)</author>", rec, re.S | re.I):
            ln = _xml_text(re.search(r"<lastname>(.*?)</lastname>", a, re.S | re.I).group(1)) \
                if re.search(r"<lastname>", a, re.I) else ""
            fn = _xml_text(re.search(r"<first-names>(.*?)</first-names>", a, re.S | re.I).group(1)) \
                if re.search(r"<first-names>", a, re.I) else ""
            if ln:
                auths.append(f"{ln}, {fn}".strip(", "))
        kws = []
        kwblock = re.search(r"<keywords>(.*?)</keywords>", rec, re.S | re.I)
        if kwblock:
            inner = kwblock.group(1)
            if re.search(r"<keyword>", inner, re.I):
                # 真实 .enw 形态：<keywords><keyword>x</keyword>...</keywords>
                kws = [_xml_text(k) for k in
                       re.findall(r"<keyword>(.*?)</keyword>", inner, re.S | re.I)]
            else:
                # 简化形态：<keywords>a; b</keywords>（部分导出工具）
                kws = [k.strip() for k in
                       re.split(r"[;,]", _xml_text(inner)) if k.strip()]
        d = {
            "title": t, "abstract": g("abstract"), "journal": j,
            "year": g("year", r"(\d{4})") or g("year"),
            "doi": g("electronic-resource-num"),
            "keywords": kws, "authors": auths, "_display": auths,
        }
        out.append(_ref_from_fields(d, path, len(out) + 1, multi_author=True))
    return out


# ══════════════════════════════════════════════════════════
# 5. CSV（WoS / Scopus / CNKI 导出，自动识别表头）
# ══════════════════════════════════════════════════════════
CSV_MAP = {
    "title": ["title", "article title", "document title", "标题", "题名", "篇名"],
    "abstract": ["abstract", "摘要", "abstract text"],
    "keywords": ["keywords", "author keywords", "keyword", "关键词", "作者关键词"],
    "year": ["year", "publication year", "pub year", "年份", "出版年", "发表年"],
    "journal": ["journal", "source title", "publication", "periodical",
                "期刊", "来源出版物", "刊物"],
    "authors": ["authors", "author", "作者", "author full names"],
    "doi": ["doi", "digital object identifier", "doi link", "doi号"],
}
_SPLIT_AUTH = re.compile(r"\s*(?:;|\|)\s*")


def _pick(row: dict, keys: list[str]) -> str:
    low = { (k or "").strip().lower(): v for k, v in row.items() }
    for k in keys:
        if k in low and (low[k] or "").strip():
            return low[k].strip()
    return ""


def load_csv(path: Path) -> list:
    """解析带表头的 CSV（WoS 导出常为 tab 分隔 + 3 段式记录，自动嗅探）。"""
    raw = path.read_text(encoding="utf-8-sig", errors="replace")
    sample = raw[:8000]
    delim = ","
    for cand in ("\t", ",", ";"):
        if sample.count(cand) > sample.count(delim):
            delim = cand
    rdr = csv.DictReader(raw.splitlines(), delimiter=delim)
    if not rdr.fieldnames:
        raise EnlError(2, f"CSV 无表头：{path.name}")
    out = []
    for i, row in enumerate(rdr, 1):
        au = _pick(row, CSV_MAP["authors"])
        auths = [a.strip() for a in _SPLIT_AUTH.split(au) if a.strip()]
        # WoS 风格 "Smith, J; Doe, A" → 已是 "姓, 名"；保持原样交给 parse_authors
        d = {
            "title": _pick(row, CSV_MAP["title"]),
            "abstract": _pick(row, CSV_MAP["abstract"]),
            "journal": _pick(row, CSV_MAP["journal"]),
            "year": _pick(row, CSV_MAP["year"]),
            "doi": _pick(row, CSV_MAP["doi"]),
            "keywords": [k.strip() for k in
                         re.split(r"[;,]", _pick(row, CSV_MAP["keywords"])) if k.strip()],
            "authors": auths, "_display": auths,
        }
        out.append(_ref_from_fields(d, path, i, multi_author=True))
    return out


# ══════════════════════════════════════════════════════════
# 统一字段 → Ref
# ══════════════════════════════════════════════════════════
def _ref_from_fields(d: dict, path: Path, seq: int, multi_author: bool = False):
    disp = d.get("_display") or d.get("authors") or []
    if isinstance(disp, str):
        disp = [disp]
    # EndNote 口径：'Last, F. M.' 以 \r 分隔
    authors = "\r".join(x for x in disp if x)
    return make_ref(
        rid=f"{path.stem}:{seq}",
        title=d.get("title", ""), abstract=d.get("abstract", ""),
        keywords=d.get("keywords", []), year=_year(d.get("year")),
        journal=d.get("journal", ""), authors=authors, doi=d.get("doi", ""),
    )


# ══════════════════════════════════════════════════════════
# 6. CNKI XML（.txt / .xml，根节点 <Bibliographies>）
# ══════════════════════════════════════════════════════════
def load_cnki_xml(path: Path) -> list:
    """解析 CNKI 自有 XML 导出：<Bibliographies><Bibliography>…。

    实测字段：Type / PrimaryTitle>Title / Authors>Author>Info>FullName /
    SecondaryResponsibility(Director) / Degree / Medium>Media / Year / Url /
    Abstract / Keywords。 theses 无期刊名，用 Medium（学位授予单位）作来源。
    """
    txt = _read_text(path)
    out = []
    for rec in re.findall(r"<Bibliography>(.*?)</Bibliography>", txt, re.S):
        def g(pat, default=""):
            m = re.search(pat, rec, re.S | re.I)
            return _xml_text(m.group(1)) if m else default
        title = g(r"<PrimaryTitle>.*?<Title[^>]*>(.*?)</Title>") or g(r"<Title[^>]*>(.*?)</Title>")
        authors = [_xml_text(m) for m in
                   re.findall(r"<FullName>(.*?)</FullName>", rec, re.S | re.I)]
        kw = g(r"<Keywords>(.*?)</Keywords>")
        d = {
            "title": title,
            "abstract": g(r"<Abstract>(.*?)</Abstract>") or g(r"<Abstracts>(.*?)</Abstracts>"),
            "keywords": [k.strip() for k in re.split(r"[;；,，]", kw) if k.strip()],
            "journal": g(r"<Medium>.*?<Media[^>]*>(.*?)</Media>")
                       or g(r"<Journal>(.*?)</Journal>") or g(r"<Source>(.*?)</Source>"),
            "year": g(r"<Year>(.*?)</Year>"),
            "doi": g(r"<DOI>(.*?)</DOI>") or _doi_from_url(g(r"<Url>(.*?)</Url>")),
            "authors": authors, "_display": authors,
        }
        out.append(_ref_from_fields(d, path, len(out) + 1, multi_author=True))
    return out


def _doi_from_url(u: str) -> str:
    m = re.search(r"(10\.\d{4,9}/[^\s\"<>?]+)", u or "")
    return m.group(1) if m else ""


# ══════════════════════════════════════════════════════════
# 7. NoteExpress 原生 tagged（.net）
# ══════════════════════════════════════════════════════════
_NE_FIELD = re.compile(r"^\{([A-Za-z][A-Za-z ]*)\}\s*:\s*(.*)$")


def load_noteexpress(path: Path) -> list:
    """解析 NoteExpress 原生导出（.net）：`{字段名}: 值`，空行分隔记录。

    实测字段：Reference Type / Title / Author / Tertiary Author / Publisher /
    Journal / Year / Volume / Issue / Pages / Abstract / Keywords / DOI / URL /
    Type of Work / Notes / Database Provider / Author Address。

    ⚠️ `{Author}` 可能有多个（多作者），需累积而非覆盖 —— 故用 append。
    """
    txt = _read_text(path)
    out, cur, in_rec = [], {}, False
    def flush():
        nonlocal cur, in_rec
        if cur and cur.get("Title"):
            d = {
                "title": cur.get("Title", ""),
                "abstract": cur.get("Abstract", ""),
                "keywords": [k.strip() for k in
                             re.split(r"[;；,，]", cur.get("Keywords", "")) if k.strip()],
                "journal": cur.get("Journal") or cur.get("Publisher", ""),
                "year": cur.get("Year", ""),
                "doi": cur.get("DOI", ""),
                "authors": cur.get("__authors", []),
                "_display": cur.get("__authors", []),
            }
            out.append(_ref_from_fields(d, path, len(out) + 1, multi_author=True))
        cur, in_rec = {}, False
    for line in txt.splitlines():
        if not line.strip():
            if in_rec:
                flush()
            continue
        m = _NE_FIELD.match(line.strip())
        if m:
            key, val = m.group(1).strip(), m.group(2).strip()
            in_rec = True
            if key == "Author":
                cur.setdefault("__authors", []).append(val)
            else:
                cur.setdefault(key, val)
        # 非字段行：并入上一个字段的续行（如长摘要换行）
        elif in_rec and cur:
            last = list(cur.keys())[-1]
            if last != "__authors":
                cur[last] = (cur[last] + " " + line.strip()).strip()
    if in_rec:
        flush()
    return out


# ══════════════════════════════════════════════════════════
# 8. EndNote tagged（%0 / %A / %T …，CNKI 的 .enw 实际是这种）
# ══════════════════════════════════════════════════════════
_EN_TAGGED = re.compile(r"^%([0-9A-Za-z])[ \t]+(.*)$")


def load_endnote_tagged(path: Path) -> list:
    """解析 EndNote「Refer/BibIX」tagged 导出（`%X ` 形式）。

    ⚠️ 与 EndNote XML（<record>…</record>）是**两种不同格式**。
       CNKI 导出的 .enw 是本格式；文件名相同极易误判，故按内容嗅探。

    标签：%0 类型 / %T 题名 / %A 作者(可多个) / %D 年份 / %Y 年份 / %K 关键词(;) /
          %X 摘要 / %I 出版者/期刊 / %J 期刊 / %V 卷 / %N 期 / %P 页 / %U URL /
          %W 数据库 / %9 文献类型 / %R 备注

    ⚠️ 年份标签 %D 与 %Y 并存：EndNote 原生 Refer/BibIX 用 %D（常为
       "YYYY/MM/DD" 或 "MM/DD/YYYY"），而 CNKI 等平台的 .enw 导出用 %Y。
       只认 %D 会让后者 year 全为 None → 时效性分析直接报"无任何可用年份"，
       且属静默数据丢失（违反零静默丢弃铁律）。故两者都收，最终由 _year() 抽取。
    """
    txt = _read_text(path)
    out, cur = [], {}
    def flush():
        nonlocal cur
        if cur.get("T"):
            # %Y 优先于 %D：CNKI 的 %D 常是空串或非年份串
            year_raw = cur.get("Y") or cur.get("D") or ""
            d = {
                "title": cur.get("T", ""), "abstract": cur.get("X", ""),
                "keywords": [k.strip() for k in re.split(r"[;；]", cur.get("K", "")) if k.strip()],
                "journal": cur.get("J") or cur.get("I", ""),
                "year": year_raw,
                "doi": _doi_from_url(cur.get("U", "")) or cur.get("R", ""),
                "authors": cur.get("__A", []), "_display": cur.get("__A", []),
            }
            out.append(_ref_from_fields(d, path, len(out) + 1, multi_author=True))
        cur = {}
    for line in txt.splitlines():
        m = _EN_TAGGED.match(line)
        if m:
            tag, val = m.group(1), m.group(2).strip()
            if tag == "0":
                flush()
                cur = {"0": val}
            elif tag == "A":
                cur.setdefault("__A", []).append(val)
            else:
                cur.setdefault(tag, val)
        elif line.strip() and cur:
            last = list(cur.keys())[-1]
            if last != "__A":
                cur[last] = (cur[last] + " " + line.strip()).strip()
    flush()
    return out


# ══════════════════════════════════════════════════════════
# 9. CNKI GB7714 引用列表（纯文本 .txt）
# ══════════════════════════════════════════════════════════
def load_cnki_gb7714(path: Path) -> list:
    """解析 CNKI「引文列表」纯文本：`[1]作者.题名[D].来源,年份.DOI:xxx.`

    ⚠️ 这类导出**只有题录、没有摘要与关键词**，故几乎全落入 fallback_title 降级层。
       仍必须导入（零静默丢弃），但报告须提示「该来源无摘要，正文分析不可用」。
    """
    txt = _read_text(path)
    out = []
    for line in txt.splitlines():
        m = re.match(r"\s*\[(\d+)\]\s*(.+)", line)
        if not m:
            continue
        body = m.group(2).strip()
        # 去掉尾部 DOI
        doi = ""
        dm = re.search(r"DOI:\s*(10\.\d{4,9}/\S+?)\.?\s*$", body, re.I)
        if dm:
            doi = dm.group(1)
            body = body[: dm.start()].strip()
        # 题名与作者：以第一个 '.' 为界（作者含空格，题名一般不含句点）
        parts = body.split(".", 1)
        authors = [a.strip() for a in re.split(r"[;；,，]", parts[0]) if a.strip()] \
            if parts else []
        rest = parts[1] if len(parts) > 1 else ""
        title = rest
        year = journal = ""
        ym = re.search(r",\s*((?:19|20)\d{2})\s*\.?\s*$", rest)
        if ym:
            year = ym.group(1)
            before = rest[: ym.start()]
            seg = before.rsplit("[", 1)
            if len(seg) == 2:
                title = seg[0]
                journal = seg[1].strip("].。 ")
            else:
                title = before
        else:
            seg = rest.split("[", 1)
            if len(seg) == 2:
                title, journal = seg[0], seg[1].strip("].。 ")
        d = {"title": title.strip(), "abstract": "", "keywords": [],
             "journal": journal.strip(), "year": year, "doi": doi,
             "authors": authors, "_display": authors}
        out.append(_ref_from_fields(d, path, len(out) + 1, multi_author=True))
    return out


# ══════════════════════════════════════════════════════════
# 10. Zotero RDF（.rdf）—— 借鉴自 OBHRM reference-import
# ══════════════════════════════════════════════════════════
def load_zotero_rdf(path: Path) -> list:
    """解析 Zotero RDF（bibo/dc/prism/foaf 命名空间）。

    借鉴 OBHRM `reference-import/scripts/import_refs.py` 的 parse_zotero_rdf，
    并**修正其一处缩进缺陷**：原实现把 journal / year / doi / description
    的抽取写在 `if 作者列表存在:` 块内，导致无作者记录静默丢失这些字段。
    本实现把这些抽取移到块外。
    """
    import xml.etree.ElementTree as ET
    txt = _read_text(path)
    ns = {
        "bibo": "http://purl.org/ontology/bibo/",
        "dc": "http://purl.org/dc/elements/1.1/",
        "prism": "http://prismstandard.org/namespaces/basic/2.0/",
        "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        "foaf": "http://xmlns.com/foaf/0.1/",
    }
    try:
        root = ET.fromstring(txt)
    except ET.ParseError as e:
        raise EnlError(2, f"RDF 解析失败：{e}")
    out = []
    for art in root.findall(".//*[@rdf:about]", ns):
        title = art.findtext("{%s}title" % ns["dc"])
        if not title:
            continue
        authors = []
        al = art.find("{%(bibo)s}authorList" % ns)
        if al is not None:
            for desc in al.findall(".//{%(rdf)s}Description" % ns):
                fam = desc.findtext("{%(dc)s}familyName" % ns)
                giv = desc.findtext("{%(dc)s}givenName" % ns)
                nm = desc.findtext("{%(foaf)s}name" % ns)
                if fam or giv:
                    authors.append(((fam or "").strip() + (", " + (giv or "").strip() if giv else "")).strip())
                elif nm:
                    authors.append(nm.strip())
        journal = ""
        j = art.find("{%(bibo)s}Journal" % ns)
        if j is not None:
            journal = (j.findtext("{%(dc)s}title" % ns) or "").strip()
        kw = [k.strip() for k in
              re.split(r"[;；,，]", art.findtext("{%(dc)s}subject" % ns) or "") if k.strip()]
        d = {
            "title": title.strip(), "abstract": art.findtext("{%(dc)s}description" % ns) or "",
            "journal": journal,
            "year": re.sub(r"\D.*", "", art.findtext("{%(dc)s}date" % ns) or ""),
            "doi": art.findtext("{%(prism)s}doi" % ns) or art.findtext("{%(bibo)s}doi" % ns) or "",
            "keywords": kw, "authors": authors, "_display": authors,
        }
        out.append(_ref_from_fields(d, path, len(out) + 1, multi_author=True))
    return out


# ══════════════════════════════════════════════════════════
# 11. Better BibTeX JSON（.json）—— 借鉴自 OBHRM reference-import
# ══════════════════════════════════════════════════════════
def load_betterbibtex_json(path: Path) -> list:
    """解析 Zotero Better BibTeX 导出的 JSON（items[] / references[]）。"""
    txt = _read_text(path)
    obj = json.loads(txt)
    items = obj.get("items") or obj.get("references") or []
    out = []
    for it in items:
        if not isinstance(it, dict):
            continue
        f = it.get("fields") if isinstance(it.get("fields"), dict) else it
        authors = []
        for c in (it.get("creators") or []):
            if isinstance(c, dict):
                nm = c.get("lastName") or c.get("family") or c.get("name")
                if nm:
                    giv = (c.get("firstName") or c.get("given") or "").strip()
                    authors.append(f"{nm}, {giv}".strip(", "))
            elif isinstance(c, str):
                authors.append(c)
        kw = []
        for t in (it.get("tags") or []):
            if isinstance(t, dict):
                v = t.get("tag") or t.get("name")
                if v:
                    kw.append(str(v))
            elif isinstance(t, str):
                kw.append(t)
        d = {
            "title": f.get("title", "") or it.get("title", ""),
            "abstract": f.get("abstractNote", "") or it.get("abstract", "") or "",
            "journal": (f.get("publicationTitle") or f.get("bookTitle")
                        or it.get("container-title") or ""),
            "year": str(f.get("date") or it.get("issued") or it.get("year") or ""),
            "doi": f.get("DOI") or f.get("doi") or it.get("DOI") or "",
            "keywords": kw, "authors": authors, "_display": authors,
        }
        out.append(_ref_from_fields(d, path, len(out) + 1, multi_author=True))
    return out



# ══════════════════════════════════════════════════════════
# 12. Web of Science 纯文本 tagged（.txt，FN/VR/PT…ER）
# ══════════════════════════════════════════════════════════
_WOS_TAG = re.compile(r"^([A-Z][A-Z0-9])\s*(.*)$")


def load_wos_tagged(path: Path) -> list:
    """解析 WoS「纯文本」导出（.txt）：两字母标签 + **三空格续行**。

    实测结构：FN/VR/PT/AU/AF/TI/SO/LA/DT/DE/ID/AB/C1…/ER，共 50 条/文件。
    三条硬规则（缺任一则整批解析错乱）：
      1. 续行 = 以三个空格开头，归属**上一个标签**（摘要、作者、地址都靠它）；
      2. 同一标签可出现多次（AU/AF/C1/RE），须**累加**而非覆盖；
      3. `ER` 结束一条记录（行尾无空格）。
    字段语义：DE = Author Keywords（作者关键词），ID = Keywords Plus（WoS 主题词）。
    """
    txt = _read_text(path)
    out, cur, last = [], {}, None

    def flush():
        nonlocal cur, last
        if cur.get("TI"):
            kw = [k.strip() for k in re.split(r"[;；]", cur.get("DE", "")) if k.strip()]
            d = {
                "title": cur.get("TI", ""), "abstract": cur.get("AB", ""),
                "journal": cur.get("SO", ""), "year": cur.get("PY", ""),
                "doi": cur.get("DI", "") or _doi_from_url(cur.get("UR", "")),
                "keywords": kw, "authors": cur.get("__AU", []),
                "_display": cur.get("__AU", []),
            }
            out.append(_ref_from_fields(d, path, len(out) + 1, multi_author=True))
        cur, last = {}, None

    for line in txt.splitlines():
        if not line.strip():
            continue
        if line.startswith("   "):                     # 续行
            if last:
                cur[last] = (cur.get(last, "") + " " + line[3:].strip()).strip()
            continue
        m = _WOS_TAG.match(line)
        if not m:
            continue
        tag, val = m.group(1), m.group(2).strip()
        if tag == "ER":          # 记录结束（ER 行无尾随空格，故正则须允许空值）
            flush()
            continue
        last = tag
        if tag == "AU":
            cur.setdefault("__AU", []).append(val)
        elif tag in ("DE", "ID"):
            cur[tag] = (cur.get(tag, "") + "; " + val).strip() if cur.get(tag) else val
        else:
            cur.setdefault(tag, val)
    flush()
    return out


# ══════════════════════════════════════════════════════════
# 13. Web of Science HTML 导出（.html）
# ══════════════════════════════════════════════════════════
_WOS_HTML_LABEL = {
    "title": ("title",),
    "author(s)": ("__AU",),
    "source": ("journal",), "source title": ("journal",),
    "journal": ("journal",),
    "abstract": ("abstract",),
    "author keywords": ("keywords",),
    "keywords plus": ("__kp",),
    "publication year": ("year",), "year": ("year",),
    "early access date": ("__ead",),
    "doi": ("doi",), "doi link": ("__url",),
    "volume": ("__vol",), "issue": ("__iss",),
    "start page": ("__sp",), "ending page": ("__ep",),
    "page count": ("__pc",),
}
# 已知标签白名单。⚠️ 必需：题名/摘要本身可能含冒号
#（如 "A study on X: Y"），若无白名单会被误判成标签 → 该记录标题丢失。
_WOS_KNOWN_LABELS = {
    "title", "author(s)", "source", "source title", "journal", "abstract",
    "author keywords", "keywords plus", "doi", "doi link",
    "published date", "publication date", "early access date", "pub. date",
    "volume", "issue", "article number", "start page", "ending page", "page count",
    "language", "document type", "issn", "eissn", "publisher", "publisher address",
    "publisher city", "addresses", "affiliations", "reprint addresses",
    "e-mail addresses", "researcher ids", "orcids", "funding", "funding orgs",
    "funding text", "open access", "open access designations",
    "times cited in web of science core collection", "total times cited",
    "cited references", "cited reference count", "pubmed id", "accession number",
    "author identifiers", "web of science index", "web of science categories",
    "research areas", "ids number", "iso source abbrev.", "29-char source abbrev.",
    "source item page count", "esi highly cited paper", "esi hot paper",
    "highly cited status", "hot paper status", "output date", "ut (unique wos id)",
    "web of science record", "journal abbreviation", "journal iso abbreviation",
    "publication date", "meeting abstract", "special issue", "supplement",
    "part number", "book series title", "book series subtitle", "conference title",
    "conference date", "conference location", "conference sponsor", "conference host",
}
_WOS_REC_SPLIT = re.compile(r"^Record\s+\d+\s+of\s+\d+", re.I)


def load_wos_html(path: Path) -> list:
    """解析 WoS HTML 导出（实测 50 条 / 10051 个展平行）。

    ⚠️ 两个结构陷阱（都会静默丢数据）：
      1. **多个 `<b>Label:</b> <value>` 挤在同一个 `<td>` 里**，用 `&nbsp;` 分隔。
         按「一 td 一标签」解析只能拿到每格第一个（Source），
         DOI / Published Date / Volume 会整段丢失（实测 DOI=0、年份=None）。
      2. 展平后**标签与值各占一行**：先 `Source:`（空值），下一行才是 `BMC PUBLIC HEALTH`。
         故必须支持「空值标签 → 后续行归属该标签」，题名/摘要还会跨多行。

    另：WoS HTML **没有** `Publication Year` 标签，年份取自
    `Published Date`（如 `2025 FEB 10`）或 `Early Access Date`（如 `JUN 2025`）。
    """
    txt = _read_text(path)
    t = re.sub(r"<b>", "\n<b>", txt, flags=re.I)      # 标签前强制换行
    t = re.sub(r"<br\s*/?>", "\n", t, flags=re.I)
    t = re.sub(r"&nbsp;", "\n", t, flags=re.I)
    t = re.sub(r"</?value>", " ", t, flags=re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    t = (t.replace("&lt;", "<").replace("&gt;", ">")
          .replace("&quot;", '"').replace("&amp;", "&"))

    rec_re = re.compile(r"^Record\s+\d+\s+of\s+\d+$", re.I)
    label_re = re.compile(r"^([A-Za-z][A-Za-z0-9 ()/,.\-]{0,58}?):\s*(.*)$")
    ACC = {"title", "abstract", "keywords"}          # 可多行/多次出现
    out, cur, pending = [], {}, None

    def put(field, val):
        if not field or not val:
            return
        if field in ACC and cur.get(field):
            cur[field] = (cur[field] + " " + val).strip()
        else:
            cur[field] = val.strip() if field not in ACC else val.strip()

    def apply(low, val):
        """把一个 (标签, 值) 对落到字段上。"""
        if low == "author(s)":
            for piece in re.split(r";\s*", val):
                nm = re.split(r"\s*\(", piece)[0].strip()
                if nm:
                    cur.setdefault("__AU", []).append(nm)
        elif low in ("source", "source title", "journal"):
            cur.setdefault("journal", val)
        elif low == "author keywords":
            put("keywords", val)
        elif low in ("published date", "publication date", "pub. date"):
            # ⚠️ 正式出版年优先于在线优先年。WoS HTML 的标签顺序是
            #    DOI → Early Access Date → Published Date，若用 setdefault
            #    会让「在线优先年」覆盖「正式出版年」（实测 2026 被记成 2025），
            #    直接影响 F3 时效性分析与「近三年占比」。
            y = _year(val)
            if y:
                cur["year"] = y
        elif low == "early access date":
            cur.setdefault("year", _year(val) or "")
        elif low == "doi":
            cur.setdefault("doi", val)
        elif low in ("title", "abstract"):
            put(low, val)
        # 其余标签（Times Cited / Usage Count / Addresses / Funding …）不参与分析

    def build(n):
        kws = [k.strip() for k in re.split(r"[;；]", cur.get("keywords", "")) if k.strip()]
        au = cur.get("__AU", [])
        d = {"title": cur.get("title", ""), "abstract": cur.get("abstract", ""),
             "journal": cur.get("journal", ""), "year": cur.get("year", ""),
             "doi": cur.get("doi", ""), "keywords": kws, "authors": au, "_display": au}
        return _ref_from_fields(d, path, n, multi_author=True)

    for raw in t.splitlines():
        line = re.sub(r"[ \t\xa0]+", " ", raw).strip()
        if not line:
            continue
        if rec_re.match(line):                        # 记录边界
            if cur.get("title"):
                out.append(build(len(out) + 1))
            cur, pending = {}, None
            continue
        m = label_re.match(line)
        if m and m.group(1).strip().lower() in _WOS_KNOWN_LABELS:
            label, val = m.group(1).strip(), m.group(2).strip()
            if val:                                   # 标签与值同行
                apply(label.lower(), val)
                pending = None
            else:                                      # 空值标签 → 值在后续行
                pending = label.lower()
                if pending in ACC:
                    cur.setdefault(pending, "")
            continue
        if pending:                                   # 续行 → 归属上一个标签
            apply(pending, line)
            if pending not in ACC:
                pending = None                        # 单值标签取到值即止
    if cur.get("title"):                              # 末条记录后无 Record 标记
        out.append(build(len(out) + 1))
    return out


# ══════════════════════════════════════════════════════════
# 14. Web of Science Excel（.xls，OLE2/BIFF8，需 xlrd）
# ══════════════════════════════════════════════════════════
def load_wos_xls(path: Path) -> list:
    """解析 WoS 的 `.xls` 导出（真·OLE2 老式 Excel，需 `xlrd`，仅支持 .xls）。

    实测 51 行 × 72 列，第 0 行为表头（`Article Title` / `Source Title` /
    `Author Keywords` / `Keywords Plus` / `Publication Year` / `DOI` …）。
    列名解析复用 CSV_MAP（大小写无关），故 Scopus/CNKI 的 .xls 也能走这条路。
    ⚠️ xlrd 2.x **只读 .xls**；.xlsx 请改用 openpyxl 或先转 .xls。
    """
    try:
        import xlrd
    except ImportError:
        raise EnlError(8, "解析 .xls 需要 xlrd：pip install 'xlrd>=2.0'（xlrd 只支持 .xls）")
    book = xlrd.open_workbook(str(path))
    sheet = book.sheet_by_index(0)
    headers = [str(h).strip() for h in sheet.row_values(0)]
    low = {h.lower(): i for i, h in enumerate(headers)}   # 值必须是列号，不是表头文本
    def col(*keys):
        for k in keys:
            if k in low:
                return low[k]          # 列号 int
        return None
    c_title = col("article title", "title")
    c_jour = col("source title", "journal", "publication title")
    c_abst = col("abstract")
    c_kw   = col("author keywords", "keywords")
    c_kp   = col("keywords plus")
    c_year = col("publication year", "year")
    c_doi  = col("doi", "book doi")
    c_auth = col("authors", "author")
    if c_title is None:
        raise EnlError(2, f"{path.name} 表头未找到「Article Title/Title」列（实际表头前 5：{headers[:5]}）")
    out = []
    for r in range(1, sheet.nrows):
        row = sheet.row_values(r)
        def g(idx):
            if idx is None or idx >= len(row):
                return ""
            v = row[idx]
            return "" if v is None else re.sub(r"\s+", " ", str(v)).strip()
        title = g(c_title)
        if not title:
            continue
        kw = [k.strip() for k in re.split(r"[;；]", (g(c_kw) + "; " + g(c_kp))) if k.strip()]
        authors = [a.strip() for a in re.split(r";\s*", g(c_auth)) if a.strip()]
        d = {"title": title, "abstract": g(c_abst), "journal": g(c_jour),
             "year": g(c_year), "doi": g(c_doi), "keywords": kw,
             "authors": authors, "_display": authors}
        out.append(_ref_from_fields(d, path, len(out) + 1, multi_author=True))
    return out



# ══════════════════════════════════════════════════════════
# 格式自动识别
# ══════════════════════════════════════════════════════════
ADAPTERS = {
    "zotero": load_zotero, "ris": load_ris, "bibtex": load_bibtex,
    "endnote_xml": load_endnote_xml, "endnote_tagged": load_endnote_tagged,
    "noteexpress": load_noteexpress, "cnki_xml": load_cnki_xml,
    "cnki_gb7714": load_cnki_gb7714, "csv": load_csv,
    "zotero_rdf": load_zotero_rdf, "betterbibtex_json": load_betterbibtex_json,
    "wos_tagged": load_wos_tagged, "wos_html": load_wos_html, "wos_xls": load_wos_xls,
}


def detect_and_load(p: Path) -> tuple[str, list]:
    """**内容优先**嗅探选择适配器（扩展名会骗人，必须看内容）。

    实测教训（CNKI 真实样本）：
      · `.enw` 既可能是 EndNote XML（<record>），也可能是 tagged（%T/%A）—— 两者不同格式；
      · `.txt` 可能是 CNKI XML（<Bibliographies>）、RIS、或 GB7714 引文列表；
      · `.es6` 是 CNKI 客户端的**加密导出**（头部 `XCNKI_ENCRYPT_1.0`），
        无密钥不可解析 —— 必须明确报错并指引改用 RIS/EndNote XML/BibTeX 导出，
        绝不能静默返回 0 条。
    """
    name = p.name.lower()
    if name == "zotero.sqlite" or p.suffix.lower() == ".sqlite":
        return "zotero", load_zotero(p)

    ext = p.suffix.lower()
    # ⚠️ 嗅探窗口必须够大：实测 WoS HTML 的 "Web of Science" 标记在 4KB 之后，
    #    窗口过小会把 .html 误判为"无法识别格式"。
    if ext in (".txt", ".html", ".htm", ".xml", ".rdf", ".enw", ".net", ""):
        head = _read_text(p)[:20000]
    else:
        head = p.read_bytes()[:20000].decode("utf-8", errors="replace")

    if "XCNKI_ENCRYPT" in head:
        raise EnlError(2, f"{p.name} 是 CNKI 客户端加密导出（XCNKI_ENCRYPT），"
                          f"无密钥不可解析。请在 CNKI 客户端改用「引文 → 导出 → "
                          f"RIS / EndNote XML / BibTeX」后重新导入")

    if "<Bibliographies" in head or "<Bibliography>" in head:
        return "cnki_xml", load_cnki_xml(p)
    if _EN_TAGGED.match(head.lstrip()[:4] or " ") or re.search(r"^%0\s", head, re.M):
        return "endnote_tagged", load_endnote_tagged(p)
    if re.search(r"^\{Reference Type\}\s*:", head, re.M) or _NE_FIELD.match(head.strip()[:40] or " "):
        return "noteexpress", load_noteexpress(p)
    if re.search(r"^\[\d+\]", head, re.M):
        return "cnki_gb7714", load_cnki_gb7714(p)
    # ── Web of Science 系列 ──
    if ext == ".xls" or head.startswith("\xd0\xcf\x11\xe0"):
        return "wos_xls", load_wos_xls(p)
    if ext in (".html", ".htm") and "Web of Science" in head:
        return "wos_html", load_wos_html(p)
    if re.search(r"(?m)^FN\s+.*Web of Science", head) or (
            re.search(r"(?m)^VR\s+1\.0", head) and re.search(r"(?m)^ER\s*$", head)):
        return "wos_tagged", load_wos_tagged(p)
    if "<record>" in head or re.search(r"<EndNote|\bREFER\b", head):
        return "endnote_xml", load_endnote_xml(p)
    if ext == ".rdf" or ("xmlns" in head and re.search(r"rdf:|bibo:", head)):
        return "zotero_rdf", load_zotero_rdf(p)
    if ext == ".json" or head.lstrip().startswith("{"):
        obj = json.loads(_read_text(p)) if head.lstrip().startswith("{") else {}
        if obj.get("format") == "endnote-analysis/refs@1":
            raise EnlError(2, f"{p.name} 已是本工具的 refs.json 产物，无需再导入")
        return "betterbibtex_json", load_betterbibtex_json(p)
    if re.search(r"^@\w+\s*\{", head, re.M):
        return "bibtex", load_bibtex(p)
    if re.search(r"^(TY|ER)\s{2}-", head, re.M):
        return "ris", load_ris(p)
    if ext == ".csv":
        return "csv", load_csv(p)
    raise EnlError(2, f"无法识别格式：{p.name}（支持 zotero.sqlite / RIS / BibTeX / "
                      f"EndNote XML / EndNote tagged / NoteExpress .net / CNKI XML / "
                      f"CNKI GB7714 / CSV / Zotero RDF / Better BibTeX JSON）")


def dedup(refs: list) -> tuple[list, int]:
    """跨来源去重：DOI 优先，其次归一化标题。返回 (保留, 丢弃数)。"""
    seen_doi, seen_title, out, dropped = set(), set(), [], 0
    for r in refs:
        key_doi = (r.doi or "").lower().strip()
        key_ti = _norm_title(r.title)
        if (key_doi and key_doi in seen_doi) or (key_ti and key_ti in seen_title):
            dropped += 1
            continue
        if key_doi:
            seen_doi.add(key_doi)
        if key_ti:
            seen_title.add(key_ti)
        out.append(r)
    return out, dropped


def main() -> int:
    ap = argparse.ArgumentParser(description="多来源文献导入（Zotero/RIS/BibTeX/EN-XML/CSV）")
    ap.add_argument("paths", nargs="+", help="一个或多个文件/目录")
    ap.add_argument("--format", default="auto",
                    choices=["auto", "zotero", "ris", "bibtex", "endnote_xml",
                             "endnote_tagged", "noteexpress", "cnki_xml",
                             "cnki_gb7714", "csv", "zotero_rdf", "betterbibtex_json",
                             "wos_tagged", "wos_html", "wos_xls"])
    ap.add_argument("--out", help="写出 refs.json")
    ap.add_argument("--dedup", action="store_true", help="跨来源按 DOI/标题去重")
    ap.add_argument("--csv", help="额外导出扁平 CSV（便于人工核对）")
    a = ap.parse_args()

    files: list[Path] = []
    for raw in a.paths:
        p = Path(raw).expanduser()
        if p.is_dir():
            files += [f for f in sorted(p.rglob("*"))
                      if f.is_file() and f.suffix.lower() in
                      (".ris", ".enw", ".xml", ".bib", ".csv", ".txt",
                       ".net", ".rdf", ".es6", ".html", ".htm", ".xls")
                      and not f.name.startswith("._")]
            if (p / "zotero.sqlite").exists():
                files.append(p / "zotero.sqlite")
        elif p.is_file():
            files.append(p)
        else:
            print(f"[error] 路径不存在：{p}", file=sys.stderr)
            print(f"[hint] {EXIT[1]}", file=sys.stderr)
            return 1
    if not files:
        print("[error] 未找到可导入的文件", file=sys.stderr)
        print(f"[hint] {EXIT[1]}", file=sys.stderr)
        return 1

    all_refs: list = []
    per_source, failures = [], []
    for f in files:
        try:
            if a.format == "auto":
                key, refs = detect_and_load(f)
            else:
                key = a.format
                refs = ADAPTERS[key](f)
            all_refs.extend(refs)
            per_source.append({"file": f.name, "source": key,
                               "source_label": SOURCE_LABELS[key], "count": len(refs)})
            print(f"[ok] {f.name} → {SOURCE_LABELS[key]}：{len(refs)} 条", file=sys.stderr)
        except EnlError as e:
            failures.append({"file": f.name, "error": str(e)})
            print(f"[warn] {f.name} 导入失败：{e}", file=sys.stderr)
        except Exception as e:  # noqa: BLE001
            failures.append({"file": f.name, "error": f"{type(e).__name__}: {e}"})
            print(f"[warn] {f.name} 导入失败：{type(e).__name__}: {e}", file=sys.stderr)

    if not all_refs:
        print("[error] 所有来源均未成功导入", file=sys.stderr)
        print(f"[hint] {EXIT[2]}", file=sys.stderr)
        return 2

    before = len(all_refs)
    dropped = 0
    if a.dedup:
        all_refs, dropped = dedup(all_refs)

    # 重新编号，保证 rid 唯一（去重后原 rid 可能重复）
    for i, r in enumerate(all_refs, 1):
        r.id = i

    src = (per_source[0]["source"] if len({s["source"] for s in per_source}) == 1
           else "multi")
    cov = coverage_report(all_refs)
    if not cov["zero_drop_identity"]:
        print("[error] tier 恒等式被破坏（导入器缺陷）", file=sys.stderr)
        print(f"[hint] {EXIT[5]}", file=sys.stderr)
        return 5

    payload = refs_to_json(all_refs, src, {
        "per_source": per_source, "failures": failures,
        "imported_before_dedup": before, "dropped_by_dedup": dropped,
        "dedup_enabled": bool(a.dedup),
    })

    if a.out:
        outp = Path(a.out).expanduser()
        outp.parent.mkdir(parents=True, exist_ok=True)
        outp.write_text(json.dumps(payload, ensure_ascii=False, indent=1),
                        encoding="utf-8")
    if a.csv:
        cp = Path(a.csv).expanduser()
        cp.parent.mkdir(parents=True, exist_ok=True)
        with open(cp, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["id", "title", "year", "journal", "authors",
                        "doi", "keywords", "tier"])
            # 题名/期刊/作者来自外部导入（不可信输入）：以 = + - @ 开头的文本
            # 会被 Excel/LibreOffice 当公式执行（DDE 注入）→ 统一加固。
            for r in all_refs:
                w.writerow([r.id, esc_csv_cell(r.title), r.year or "",
                            esc_csv_cell(r.journal), esc_csv_cell(r.authors),
                            esc_csv_cell(r.doi), esc_csv_cell(";".join(r.keywords)),
                            r.tier])

    emit({
        "ok": True, "source": src,
        "source_label": SOURCE_LABELS.get(src, "多来源合并"),
        "imported": len(all_refs), "dropped_by_dedup": dropped,
        "per_source": per_source, "failures": failures,
        "coverage": cov, "out": a.out,
    })
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except EnlError as e:
        print(f"[error] {e}", file=sys.stderr)
        print(f"[hint] {EXIT[e.code]}", file=sys.stderr)
        sys.exit(e.code)
