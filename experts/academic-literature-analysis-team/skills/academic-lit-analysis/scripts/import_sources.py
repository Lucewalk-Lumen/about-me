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
下游各分析模块经 `load_refs()` 透明读取，**代码零改动**。

零静默丢弃
----------
每条记录必须归入某个 tier（有摘要/仅关键词/仅标题/空），tier 四类和 == 导入总数。
被去重丢弃的记录单独计数并可导出，绝不静默消失。

机构与被引字段（缺口 A 修复）
----------------------------
历史版本**显式丢弃**了源文件里已经存在的机构（AD / C1 / RP / %+ / Author Address /
Addresses / affiliation）与被引（CR / Cited References / 引文列表）字段，
以致下游「机构共现 / 引文共现」永远无米下锅。现在：
  · `affiliations`  每篇可多条，原始串归一（去空白、按 ';'/换行拆、去重保序）；
  · `references`    每篇可多条，语义为「本篇引用的参考文献」的同义清单。
两者**仅在该篇非空时**写入 refs.json 的对应记录，故「本就无此字段的来源」
产出与改动前逐字节一致 —— 既保留字段，又不动既有 500 条的既有字段与统计口径。

[!]  字段采集是**保真采集**，不做机构名深度归一（如「清华大学」↔「Tsinghua Univ」
    合并）；那属于建网层 `build_institution_network.py` 的职责，且不同写法的
    合并需人工词表，误合并会污染结果。各格式能否拿到机构/被引的**实测边界**
    见 `build_institution_network.py` / `build_citation_network.py` 的模块文档。

EndNote .enl 只读某个分类（缺口 B 修复）
--------------------------------------
用户诉求：「从本地文献软件读取时，如果只读某一个分类，当前没有此功能」。
.enl 的分类关系在 SQLite 里，读法**不能臆测**——本仓库 lit_core.parse_refs
已对真实库做过实证：分类定义在 `groups` 表，`spec` 列是内含 name 的 XML/blob，
成员 id 在 `members` 列（二进制 `<magic:u32><count:u32><refs.id:u32 × count>`）。
但不同 EndNote 版本的 schema 可能不同（另有 `Groups(…name…) + GroupRefs(group_id,refs_id)`
形态），故此处**按列名探测**两种 schema，两种都不命中就明确报错，绝不静默给全库。
`--group`（名称或 ID，可多次传以合并）/`--list-groups` 即为此能力；所选分类名写入
refs.json 的 `meta.groups`，供报告标注数据范围。

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
import struct
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lit_core import (  # noqa: E402
    EXIT, EnlError, SOURCE_LABELS, coverage_report, emit, esc_csv_cell, extract_doi,
    find_enl, make_ref, make_shadow, open_enl_readonly, refs_to_json, split_keywords,
)

_YEAR = re.compile(r"(?:19|20)\d{2}")


def _year(v) -> int | None:
    if not v:
        return None
    m = _YEAR.search(str(v))
    return int(m.group(0)) if m else None


def _looks_like_text(s: str) -> float:
    """可打印字符占比，用作 UTF-16 字节序猜测的打分函数（0.0~1.0）。"""
    if not s:
        return 0.0
    ok = sum(1 for c in s if unicodedata.category(c)[0] not in "CcCsCoCn")
    return ok / len(s)


def _read_utf16(b: bytes) -> str | None:
    """仅在**可判定**为 UTF-16 时解码，否则返回 None（交回主链）。

    [!]  不可把 "utf-16" 直接塞进候选表：无 BOM 时 Python 按 LE 猜测，且对几乎
    任何字节都"解码成功"（实测 GBK 的"张伟" → '엕냎'），会**反向遮蔽** GBK 原文。
    故此处只按可判定的字节特征进入：
      1. UTF-16 BOM（FF FE / FE FF）—— 唯一可靠信号，字节序由 BOM 决定；
      2. 含 NUL 字节 —— UTF-8 与 GB18030/GBK/BIG5 的**合法**字节流中不含NUL
         （0x00 不在各自的首/尾字节取值范围内；已穷举 2 字节序列验证），
         故 NUL 出现即可判定为 16 位编码，
         此时按可打印字符占比猜字节序（LE 优先，Windows/EndNote 默认）。
    [!]  真实局限：**无 BOM 且无 NUL 的 UTF-16 无法可靠自动识别**（如纯 ASCII
    恰好字节数为偶数的情形已含 NUL，但内容被换行切碎的边缘情况仍可能漏判）。
    此类文件须由导出方加 BOM 或改存 UTF-8，不在此处假装能覆盖。
    """
    if b[:4] == b"\xff\xfe\x00\x00":
        return None            # UTF-32-LE BOM：不是 UTF-16，交回主链（维持既有行为）
    if b[:2] in (b"\xff\xfe", b"\xfe\xff"):
        try:
            return b.decode("utf-16")           # BOM 定字节序，同时被codec 剥离
        except UnicodeDecodeError:
            return None
    if b"\x00" not in b:
        return None
    try:
        le, be = b.decode("utf-16-le"), b.decode("utf-16-be")
    except UnicodeDecodeError:
        return None
    return le if _looks_like_text(le) >= _looks_like_text(be) else be


def _read_text(path: Path) -> str:
    """按 UTF-8 → UTF-16 → GB18030 → GBK → BIG5 顺序解码，errors=replace 兜底。

    CNKI / NoteExpress 的导出**编码不统一**（同一批文件里 UTF-8 与 GBK 混存），
    故必须逐级尝试；实测本批 6 个样本全为 UTF-8，但不能假定。

    [!]  UTF-16 必须排在 GB18030 **之前**：gb18030 能解码几乎任意字节并被先消费，
    UTF-16 文件会被静默解成乱码（实测 UTF-16 RIS → n=0 条且退出码 0，
    全部数据丢失却报成功）。判定细节与已知局限见 _read_utf16。
    """
    b = Path(path).read_bytes()
    s = _read_utf16(b)
    if s is not None:
        return s
    for enc in ("utf-8-sig", "utf-8", "gb18030", "gbk", "big5"):
        try:
            return b.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    # 欧美单字节编码（西文文献 / EndNote旧版Windows 默认 ANSI）**必须垫底**：
    #   · cp1252/latin-1 对CJK 字节几乎都能"解出"东西，放前面会遮蔽真正的中文；
    #     latin-1 更是全函数（任意字节都不抛），放前面等于把乱码合法化。
    #   · 放最后则只在上列编码全部失败时才生效 —— 即原先errors="replace"
    #     吐U+FFFD 的那种情形，不可能改变任何已能正确解码的文件。
    #   · latin-1 保留全部ASCII 结构，故不影响 detect_and_load 的正则嗅探。
    # 实测：仅含 Müller/Söhne/café 的 CP1252 RIS 之前解析为 'M?ller & S?hne'。
    for enc in ("cp1252", "latin-1"):
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
    [!]  必须排除 itemType in (attachment, note, annotation) —— 它们不是文献条目。
    [!]  必须排除 deletedItems —— 回收站条目。
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

        _r = make_ref(
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
        )
        # 机构：Zotero 常规期刊条目**不存**作者机构；仅 thesis 的 university、
        # 部分类型的 institution 字段可作机构。references：Zotero 不存被引 → 无。
        _aff = _split_multi([fmap.get("university", ""), fmap.get("institution", "")])
        if _aff:
            _r.affiliations = _aff
        out.append(_r)
    con.close()
    return out


def _canon_from_display(names: list[str]) -> list[str]:
    """['Smith, John A.'] → ['smith|ja']，与 EndNote 侧口径一致。"""
    from lit_core import parse_authors
    return parse_authors("\r".join(names))


# ══════════════════════════════════════════════════════════
# 1b. EndNote .enl（只读，支持「只读某一个分类」）
# ══════════════════════════════════════════════════════════
def _enl_open(path: Path):
    """只读打开 .enl：优先直连，遇库被 EndNote 持锁（EnlError.code==3）才降级影子副本。

    为什么先直连：影子副本要整库复制，且 immutable=1 在源库被写入时会读到过期快照
    （lit_core 实测结论）。只在真的锁冲突时复制，避免无谓的"可能过期"。
    """
    try:
        return open_enl_readonly(path)
    except EnlError as e:
        if e.code == 3:
            import tempfile
            return open_enl_readonly(
                make_shadow(path, Path(tempfile.gettempdir()) / "endnote_import_work"),
                immutable=True)
        raise


def _enl_tables(con) -> dict:
    """{小写表名: 原始表名}。"""
    return {r[0].lower(): r[0]
            for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def _enl_cols(con, table) -> list:
    return [r[1] for r in con.execute(f"PRAGMA table_info({table})")]


def _enl_members_blob(val) -> list:
    """解析 groups.members 二进制：<magic:u32><count:u32><refs.id:u32 × count>。

    该格式来自 lit_core.parse_refs 对真实库的实测（len == 8 + count*4）。
    不满足则不解析（宁可少读，也不按错误的字节边界臆造 id）。
    """
    if not isinstance(val, (bytes, bytearray)) or len(val) < 8:
        return []
    _magic, count = struct.unpack_from("<II", val, 0)
    if len(val) != 8 + count * 4:
        return []
    return [str(x) for x in struct.unpack_from(f"<{count}I", val, 8)]


def _enl_group_name(spec) -> str:
    """从 spec（内含 name 的 XML/文本 blob）抽分类名；抽不到返回空串。"""
    if isinstance(spec, (bytes, bytearray)):
        spec = spec.decode("utf-8", "replace")
    spec = (spec or "").replace("\x00", "")
    m = (re.search(r"<name>(.*?)</name>", spec, re.I)
         or re.search(r'name="([^"]+)"', spec, re.I))
    if m:
        import html as _html
        return _html.unescape(m.group(1)).strip()
    flat = spec.strip()
    return flat if 0 < len(flat) <= 120 else ""


def list_enl_groups(path: Path) -> list:
    """列出 .enl 全部分类：[{id, name, count, ref_ids}]。

    兼容两种 schema，**按列名探测，不臆测**：
      A) `groups(group_id, spec, members)` —— EndNote 20/21 真实 schema
         （spec 内含 name 的 XML/blob，members 为二进制成员 id）；
      B) `Groups(…含 name 的列…) + GroupRefs(group_id, refs_id)` —— 另一版本可能的形态。
    两者都不命中（或压根没有 groups 表）→ 返回 []，由调用方明确报错。
    """
    enl = find_enl(path)
    con = _enl_open(enl)
    try:
        tabs = _enl_tables(con)
        g_tbl = tabs.get("groups")
        ref_tbl = tabs.get("grouprefs") or tabs.get("group_refs")
        if not g_tbl:
            return []
        g_cols = _enl_cols(con, g_tbl)
        low = {c.lower(): c for c in g_cols}
        id_col = next((low[c] for c in ("group_id", "groupid", "id") if c in low), None)
        name_col = next((low[c] for c in
                         ("name", "group_name", "groupname", "title", "label")
                         if c in low), None)
        # 成员来源 1：GroupRefs 映射表（schema B）
        ref_map: dict[str, list] = {}
        if ref_tbl:
            r_cols = {c.lower(): c for c in _enl_cols(con, ref_tbl)}
            gi = next((r_cols[c] for c in ("group_id", "groupid", "grp_id") if c in r_cols), None)
            ri = next((r_cols[c] for c in
                       ("refs_id", "ref_id", "refid", "reference_id", "refs")
                       if c in r_cols), None)
            if gi and ri:
                for g, r in con.execute(f"SELECT {gi},{ri} FROM {ref_tbl}"):
                    ref_map.setdefault(str(g), []).append(str(r))
        out = []
        for row in con.execute(f"SELECT * FROM {g_tbl}"):
            rec = dict(zip(g_cols, row))
            gid = rec.get(id_col) if id_col else None
            name = str(rec.get(name_col)).strip() if (name_col and rec.get(name_col)) else ""
            if not name and "spec" in rec:                 # schema A：名字藏在 spec 里
                name = _enl_group_name(rec.get("spec"))
            ids = ref_map.get(str(gid)) if id_col else None
            if ids is None and "members" in rec:           # schema A：二进制成员
                ids = _enl_members_blob(rec.get("members"))
            if ids is None:                                # 兜底：逗号/空白分隔的 id 列
                for lc in ("refs_id", "ref_ids", "refid", "refs"):
                    if lc in low:
                        ids = [x for x in re.split(r"[^\d]+", str(rec.get(low[lc]) or "")) if x]
                        break
            ids = ids or []
            out.append({"id": gid, "name": name or f"ID:{gid}",
                        "count": len(set(ids)), "ref_ids": list(dict.fromkeys(ids))})
        return out
    finally:
        con.close()


def load_enl(path: Path, group_ids=None) -> list:
    """只读导入 .enl 为 Ref[]。group_ids 为 None 导全库，否则只导这些 refs.id。"""
    enl = find_enl(path)
    con = _enl_open(enl)
    try:
        avail = _enl_cols(con, "refs")
        want = [c for c in ("id", "title", "abstract", "keywords", "year",
                            "secondary_title", "author", "electronic_resource_number",
                            "read_status") if c in avail]
        idx = {c: i for i, c in enumerate(want)}
        # trash_state=0 排除回收站，与 lit_core.parse_refs 口径一致
        where = " WHERE trash_state=0" if "trash_state" in avail else ""
        rows = con.execute(f"SELECT {','.join(want)} FROM refs{where}").fetchall()
        allow = set(group_ids) if group_ids is not None else None
        out = []
        for row in rows:
            rid = row[idx["id"]]
            if allow is not None and str(rid) not in allow:
                continue
            out.append(make_ref(
                rid=rid,
                title=row[idx["title"]] if "title" in idx else "",
                abstract=row[idx["abstract"]] if "abstract" in idx else "",
                keywords=split_keywords(row[idx["keywords"]]) if "keywords" in idx else [],
                year=_year(row[idx["year"]]) if "year" in idx else None,
                journal=row[idx["secondary_title"]] if "secondary_title" in idx else "",
                authors=row[idx["author"]] if "author" in idx else "",
                doi=extract_doi(row[idx["electronic_resource_number"]])
                    if "electronic_resource_number" in idx else "",
                read_status=row[idx["read_status"]] if "read_status" in idx else "",
            ))
        return out
    finally:
        con.close()


def _resolve_enl_groups(path: Path, group_args) -> tuple:
    """把 --group 的取值解析为 (允许的 refs.id 列表, 已选分组信息)。

    为什么必须硬失败：用户要的是"只读某分类"。若分类名打错却静默导全库，
    报告会给出与标注不符的数据范围——比报错严重得多。故找不到就抛错并列出可用分类。
    """
    if not group_args:
        return None, []
    groups = list_enl_groups(path)
    sel, ids = [], []
    for q in group_args:
        q = (q or "").strip()
        hit = next((g for g in groups if str(g["id"]) == q), None) if q.isdigit() else None
        if hit is None:
            hit = next((g for g in groups if (g["name"] or "").casefold() == q.casefold()), None)
        if hit is None:
            avail = "、".join(f"{g['name']}({g['count']})" for g in groups) or "（无可用分类）"
            raise EnlError(4, f"分类不存在：{q}；可用分类：{avail}")
        sel.append({"name": hit["name"], "id": hit["id"], "count": hit["count"]})
        ids.extend(hit["ref_ids"])
    return list(dict.fromkeys(ids)), sel


# ══════════════════════════════════════════════════════════
# 2. RIS（CNKI / WoS / Scopus / NoteExpress 通用导出）
# ══════════════════════════════════════════════════════════
_RIS_LINE = re.compile(r"^([A-Z][A-Z0-9])\s{2}-\s?(.*)$")


def load_ris(path: Path) -> list:
    """解析 RIS。记录以 `ER  -` 结束，字段为 `XX  - value`。

    字段映射：TI/T1=标题 AB/N2=摘要 KW=关键词 PY/Y1/DA=年份
              JO/JF/T2=期刊 AU/A1=作者 DO/UR=DOI
    机构/被引：AD（Author Address）、C1..C7（地址类自定义标签）、RP（Reprint
              Address）→ affiliations；CR（Cited References，WoS 的 RIS 导出
              每行一条、可重复）→ references。
    """
    refs, cur = [], {}
    last = None
    for raw in _read_text(path).splitlines():
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
            # [!]  年份必须以 PY/Y1 为准。实测 WoS RIS 的标签顺序是
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
        elif tag in ("AD", "C1", "C2", "C3", "C4", "C5", "C6", "C7"):
            # 机构：AD=Author Address；C1..C7 是 RIS 预留的地址类自定义标签
            #（WoS 的 RIS 导出正是用 C1 承载 Author Address）。
            # [!] 不含 RP（Reprint Address）：其格式是「作者姓名, 地址…」，
            # 首个逗号前是**人名**而非机构，采集会造出 "Chen" 之类的伪机构
            #（实测夹具已复现）——而地址本身 C1/AD 已覆盖，故整体不采集。
            cur.setdefault("affiliations", []).append(val)
        elif tag == "CR":
            # 被引：WoS 的 RIS 导出用 CR 承载 Cited References，每行一条、可重复。
            # 普通 RIS（Zotero/CNKI 导出）通常不含 CR —— 此时 references 为空，
            # 属数据源限制，不伪造。
            cur.setdefault("references", []).append(val)
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


# LaTeX 重音命令 → Unicode 组合字符（NFC 合成后即 é/ö/ñ…）。
# 为什么需要：WoS BibTeX 的作者/题名/机构含 \'e、\"o 之类转义；不还原则机构名
# 与题名出现 "Muller"/"Soderberg" 这类丢重音的变体，机构节点会因此分裂。
_BIB_ACCENT = {
    "'": "\u0301", "`": "\u0300", "^": "\u0302", '"': "\u0308",
    "~": "\u0303", "=": "\u0304", ".": "\u0307", "u": "\u0306", "v": "\u030c",
    "H": "\u030b", "c": "\u0327", "k": "\u0328", "r": "\u030a", "b": "\u0331",
}
# 非重音类特殊命令（\ss → ß 等）。用 (?![A-Za-z]) 兜住 \o 不误吞 \oe。
_BIB_SYMBOL = {"ss": "ß", "aa": "å", "AA": "Å", "ae": "æ", "AE": "Æ",
               "oe": "œ", "OE": "Œ", "o": "ø", "O": "Ø", "l": "ł", "L": "Ł"}


def _bib_restore_latex(s: str) -> str:
    """还原 BibTeX/LaTeX 转义：\\& 等符号 + 常见重音。所有字段共用。"""
    s = (s.replace("\\&", "&").replace("\\_", "_").replace("\\%", "%")
         .replace("\\$", "$").replace("\\#", "#"))
    # \'e / \'{e} / \"o / \c{c} …：把变音命令折成组合字符（NFC 合成）
    s = re.sub(r"\\([`'^\"~=\.uvHckrbd])\s*\{?([A-Za-z])\}?",
               lambda m: m.group(2) + _BIB_ACCENT.get(m.group(1), ""), s)
    for cmd, rep in _BIB_SYMBOL.items():
        s = re.sub(r"\\" + cmd + r"(?![A-Za-z])", rep, s)
    return unicodedata.normalize("NFC", s)


# 这些字段是「一行一条」的多行值，必须保留换行做条目边界。
_BIB_MULTILINE = {"affiliation", "affiliations", "cited-references"}

# 判定「某逗号片段是机构」的关键词：无 (Corresponding Author) 标记时用它定位机构起点。
_ORG_KW = re.compile(
    r"\b(?:Univ|University|Inst|Institute|Coll|College|Acad|Academy|Sci|Science|"
    r"Sch|School|Dept|Department|Ctr|Centre|Center|Hosp|Hospital|Fac|Faculty|"
    r"Lab|Laboratory|Med|Medical|Ministry|Ministr|Natl|National|Polytech|Technol|Tech)\b",
    re.I)

# 姓名片段（兜底用）：单个「姓/名/首字母」词，或最多再跟 2 个大写开头的词
#（如 "Sara Maghare"、"Saeid; Rajabi-vardanjani"）。刻意限制词数，避免把
# “Izmir Prov Hlth Directorate”这类多词机构名误当人名吞掉。
_NAME_LIKE = re.compile(r"^[A-Z][A-Za-z'\-\.]*(?:[ ;]+[A-Z][A-Za-z'\-\.]*){0,2}$")


def _strip_affil_authors(line: str) -> str:
    """剔除 WoS Affiliation 行首的作者名前缀，只留机构串。

    行形如 `作者名[, 作者名…][ (Corresponding Author)], 机构, 城市, 国家.`。
    为什么必须在此剔除：下游 build_institution_network 的 normalize_org 只按逗号
    取第一段，若不在这里去掉作者名，机构节点会变成 "Yazdanirad" 之类的人名。
    三条规则按可靠性排序：
      1) 有 (Corresponding Author) 标记 → 标记及其前全是作者名，直接切掉；
      2) 否则找「机构关键词」第一次出现的片段，其前全是作者名；
      3) 整行都没有机构关键词 → 兜底逐段丢弃开头的姓名片段（实测能修掉
         "Bingol, Umran, Izmir Prov Hlth Directorate…" 这类无关键词的机构）。
    """
    m = re.search(r"\(\s*corresponding\s+author\s*\)\s*,?\s*", line, re.I)
    if m:
        return line[m.end():].strip()
    segs = [x.strip() for x in line.split(",")]
    for i, seg in enumerate(segs):
        if _ORG_KW.search(seg):
            return ", ".join(segs[i:]).strip()
    i = 0
    while i < len(segs) - 1 and _NAME_LIKE.match(segs[i]):
        i += 1
    return ", ".join(segs[i:]).strip()


def _bib_join_entries(value: str, terminator: str = ".") -> list:
    """把 WoS 多行字段还原成条目列表：区分「逻辑条目边界」与「物理折行」。

    WoS 的 Affiliation / Cited-References 每行一条、以 '.' 结尾；长条目会被
    **物理换行**（续行不结尾句点）。若把每个换行都当条目边界，一条会被劈成两半
    （实测 Affiliations 字段被拆出 'Sciences'、'Medical Sciences' 之类碎片）。
    规则：仅当上一行以 terminator 结尾时换行才算新条目，否则并入上一条。
    """
    entries = []
    for ln in value.split("\n"):
        ln = ln.strip()
        if not ln:
            continue
        if entries and not entries[-1].rstrip().endswith(terminator):
            entries[-1] = (entries[-1] + " " + ln).strip()
        else:
            entries.append(ln)
    return entries


def _clean_bib_value(v: str, keep_newlines: bool = False) -> str:
    """去掉最外层花括号/引号 + LaTeX 还原 + 压缩空白。

    keep_newlines：Affiliation / Affiliations / Cited-References 是「一行一条」的
    多行值，必须保留 \\n 作为条目边界；否则原实现把换行压成空格，多条机构/被引
    会被粘成一条（这正是之前"读不进来"的根因之一）。
    """
    v = v.strip()
    if len(v) >= 2 and ((v[0] == "{" and v[-1] == "}") or (v[0] == '"' and v[-1] == '"')):
        v = v[1:-1]
    v = _bib_restore_latex(v)                  # 先还原 \& 与重音
    v = re.sub(r"\\[a-zA-Z]+\s*", " ", v)      # 其余 \textit{} \newline 等命令
    v = re.sub(r"[{}]", "", v)
    if keep_newlines:
        lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in v.split("\n")]
        return "\n".join(ln for ln in lines if ln)
    return re.sub(r"\s+", " ", v).strip()


def load_bibtex(path: Path) -> list:
    """解析 BibTeX。

    实现要点：不能用「按行 + 逗号」切字段（字段值内含逗号与嵌套花括号，
    实测会导致 year/keywords/doi 全部丢失）。改为：
      1. 花括号配平取出整条 entry；
      2. 顶层逗号切分（_split_top）；
      3. 首段为引用键，其余 `key = value`。
    """
    txt = _read_text(path)
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
                # 多行字段（Affiliation/Affiliations/Cited-References）保换行，
                # 其余字段压成单行 —— 见 _clean_bib_value 的 keep_newlines 说明。
                fields[k] = _clean_bib_value(v, keep_newlines=(k in _BIB_MULTILINE))
        # 机构：WoS BibTeX 用 Affiliation（每行一条、含作者名前缀）与
        # Affiliations（';' 分隔的机构全名清单）承载作者机构；另有 techreport/thesis
        # 的 institution/school/organization。三者合并后由 _split_multi 归一条目。
        # [!] 不用 Address：那是**出版者**地址（如 "CAMPUS, 4 CRINAN ST, LONDON…"），
        #     当机构用会造出伪机构。
        affs = []
        for ent in _bib_join_entries(fields.get("affiliation") or "", "."):
            ent = _strip_affil_authors(ent).strip().rstrip(".").strip()
            if ent:
                affs.append(ent)
        # Affiliations：';' 分隔的机构全名清单，换行只是物理折行 → 先拼平再按 ';' 切
        flat_affi = " ".join((fields.get("affiliations") or "").split("\n"))
        for piece in flat_affi.split(";"):
            piece = piece.strip().rstrip(".").strip()
            if piece:
                affs.append(piece)
        affs += [fields[k] for k in ("institution", "school", "organization")
                 if fields.get(k)]
        # 被引：WoS BibTeX 的 Cited-References 每行一条紧凑串（含 DOI 或 作者,年,刊）。
        creds = [ent for ent in _bib_join_entries(fields.get("cited-references") or "", ".")
                 if ent]
        # 关键词：Keywords（作者关键词）+ Keywords-Plus（WoS 主题词）合并去重保序。
        kws, _seen = [], set()
        for chunk in (fields.get("keywords", ""), fields.get("keywords-plus", "")):
            for term in re.split(r";", chunk):
                t = term.strip()
                if t and t.casefold() not in _seen:
                    _seen.add(t.casefold())
                    kws.append(t)
        d = {
            "title": fields.get("title", ""),
            "abstract": fields.get("abstract", ""),
            "journal": fields.get("journal") or fields.get("booktitle", ""),
            "year": fields.get("year", ""),
            "doi": fields.get("doi", ""),
            "keywords": kws,
            "authors": [a.strip() for a in
                        re.split(r"\s+and\s+", fields.get("author", "")) if a.strip()],
            "affiliations": affs,
            "references": creds,
            # 保留 WoS 记录号与被引频次（供报告溯源与"高被引"标注；空则不写盘）
            "unique_id": fields.get("unique-id", ""),
            "times_cited": fields.get("times-cited", ""),
        }
        d["_display"] = d["authors"]
        out.append(_ref_from_fields(d, path, len(out) + 1, multi_author=True))
    return out


# ══════════════════════════════════════════════════════════
# 4. EndNote XML（.enw / .xml）
# ══════════════════════════════════════════════════════════


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


def load_enl_xml(path: Path) -> list:
    """解析 EndNote XML / NoteExpress 导出的 .enw。"""
    txt = _read_text(path)
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
        # 机构：EndNote XML 的地址可能落在 <addresses><address>…（可多条）
        # 或 <author-address>。best-effort，未在真实含地址的样本上验证；
        # references 在 EndNote XML 中无标准字段 → 不采集。
        addr = [_xml_text(a) for a in
                re.findall(r"<address[^>]*>(.*?)</address>", rec, re.S | re.I)]
        if not addr:
            m_aa = re.search(r"<author-address>(.*?)</author-address>", rec, re.S | re.I)
            if m_aa:
                addr = [_xml_text(m_aa.group(1))]
        d = {
            "title": t, "abstract": g("abstract"), "journal": j,
            "year": g("year", r"(\d{4})") or g("year"),
            "doi": g("electronic-resource-num"),
            "keywords": kws, "authors": auths, "_display": auths,
            "affiliations": addr,
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
    # 机构 / 被引：WoS CSV 有 Addresses / Affiliations / Reprint Addresses /
    # Cited References 列；Scopus CSV 有 Affiliations 列；CNKI CSV 有「机构」。
    # 未在真实 CSV 机构样本上逐列验证，但列名按各平台导出规范给出（非臆造）。
    "affiliations": ["affiliations", "addresses",
                     "authors with affiliations",
                     "机构", "作者单位", "单位", "机构名称"],
    "references": ["cited references", "references", "参考文献", "引文"],
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
    raw = _read_text(path)
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
            "affiliations": [_pick(row, CSV_MAP["affiliations"])],
            "references": [_pick(row, CSV_MAP["references"])],
        }
        out.append(_ref_from_fields(d, path, i, multi_author=True))
    return out


# ══════════════════════════════════════════════════════════
# 统一字段 → Ref
# ══════════════════════════════════════════════════════════
_MULTI_SPLIT = re.compile(r"[;\n]+")


def _split_multi(vals) -> list:
    """把机构 / 被引类多值字段归一为「去重保序」的条目列表。

    分隔约定：'半角分号' 与 '换行' 均视为条目边界（WoS 的 C1/CR、CSV 的
    Addresses/Cited References 单元格都用 ';' 分隔多条），并做 NFKC + 压缩空白。

    [!]  已知限制（如实标注，不假装完美）：若**单条**被引正文自身含分号
    （罕见，如部分中文题录），会被过度拆分。宁可多拆也不漏采，且共被引口径
    取 DOI 优先，过度拆分通常只影响无 DOI 的边，不影响可核对的 DOI 主边。
    """
    out, seen = [], set()
    for v in (vals if isinstance(vals, (list, tuple)) else [vals]):
        s = unicodedata.normalize("NFKC", str(v or ""))
        for piece in _MULTI_SPLIT.split(s):
            piece = re.sub(r"\s+", " ", piece).strip().strip(".,;|").strip()
            if not piece:
                continue
            k = piece.casefold()
            if k in seen:
                continue
            seen.add(k)
            out.append(piece)
    return out


# ── C3：机构名当作者检测（net-new）──────────────────────────────
# 真实库里作者字段被手滑写成机构名（如 "Tsinghua University" / "清华大学"）的情况存在；
# 若不处理，该机构会被当合作者污染作者共现网络（作者网络出现伪机构节点）。
# 此处仅在导入汇聚点做检测：把机构串从 authors 移出，并打 author_org_warnings 标记；
# 同时保证该机构在机构网络中仍出现（补进 affiliations，去重），不被误删。
# 检测方法：机构关键词命中（多语种）OR 与 affiliations 归一后子串交叉比对。
# [C3] 机构关键词（多语种 + 常见英文机构后缀）。子串匹配，故 "laborator" 覆盖
# laboratory/laboratories，"academ" 覆盖 academy/academic，"institut" 覆盖 institute。
# 补充 clinic / research / centre / center / univ 以覆盖 "Mayo Clinic" / "IBM Research"
# 等常见写法；research/clinic 几乎不会出现在人名中，误报风险可忽略。
_ORG_KEYWORDS = (
    "university", "univ", "college", "institute", "institut", "laborator",
    "hospital", "clinic", "school", "academ", "faculty", "department",
    "research", "centre", "center", "ltd", "inc", "corp", "co.", "gmbh",
    "有限", "大学", "学院", "研究所", "研究院", "学校", "医院", "实验室",
    "公司", "系", "中心", "委员会", "协会", "局", "署", "政府", "agency",
    "association", "bureau", "ministry", "foundation", "government",
    "commission", "authority", "council",
)


def _norm_org_token(s: str) -> str:
    return re.sub(r"[\s,.;:()\[\]（）—\-]+", "",
                  unicodedata.normalize("NFKC", (s or "")).lower())


def _looks_like_org(name: str, affiliations: list[str]) -> bool:
    n = _norm_org_token(name)
    if len(n) < 2:
        return False
    if any(k in n for k in _ORG_KEYWORDS):
        return True
    # 交叉比对：归一后作者串作为子串出现在任一机构名中（如作者 "tsinghuauniversity"
    # 出现在 affiliation "tsinghuauniversitybeijingchina"）。限长 ≥4 降误报。
    if len(n) >= 4:
        for aff in affiliations:
            a = _norm_org_token(aff)
            if a and (n in a or a in n):
                return True
    return False


def _ref_from_fields(d: dict, path: Path, seq: int, multi_author: bool = False):
    disp = d.get("_display") or d.get("authors") or []
    if isinstance(disp, str):
        disp = [disp]
    disp = [x for x in disp if x]
    aff = _split_multi(d.get("affiliations") or [])
    # C3：机构名当作者检测（net-new）——作者字段被写成机构名时，若不处理会污染
    # 作者共现网络。此处把机构串移出 authors，并打 author_org_warnings 标记；
    # 同时保证该机构在机构网络中仍出现（补进 affiliations，去重），不被误删。
    _persons, _orgs = [], []
    for nm in disp:
        (_orgs if _looks_like_org(nm, aff) else _persons).append(nm)
    # EndNote 口径：'Last, F. M.' 以 \r 分隔
    authors = "\r".join(_persons)
    ref = make_ref(
        rid=f"{path.stem}:{seq}",
        title=d.get("title", ""), abstract=d.get("abstract", ""),
        keywords=d.get("keywords", []), year=_year(d.get("year")),
        journal=d.get("journal", ""), authors=authors, doi=d.get("doi", ""),
    )
    if _orgs:
        ref.author_org_warnings = _orgs
        _aff_norm = {_norm_org_token(a) for a in aff}
        for o in _orgs:
            if _norm_org_token(o) not in _aff_norm:
                aff.append(o)
                _aff_norm.add(_norm_org_token(o))
    # 机构 / 被引：Ref 数据类未声明这两个字段（不得改动 lit_core），
    # 但 dataclass 默认非 slots，可动态挂载；序列化由 main() 补进 refs.json。
    # 仅非空才挂载 —— 保证"无此字段"的来源产出与改动前逐字节一致。
    if aff:
        ref.affiliations = aff
    cred = _split_multi(d.get("references") or [])
    if cred:
        ref.references = cred
    # WoS 溯源字段：记录号（Unique-ID）与被引频次（Times-Cited）。同样仅非空才挂载，
    # 保证无此字段的来源（RIS / CSV 等）产出不变。
    uid = str(d.get("unique_id") or "").strip()
    if uid:
        ref.unique_id = uid
    tc = str(d.get("times_cited") or "").strip()
    if tc.isdigit():
        ref.times_cited = int(tc)
    return ref


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
        # 机构：CNKI XML 无稳定公开字段表，按候选元素 best-effort 采集
        #（Organization/Institution/DegreeGrantor/AuthorAddress）。**未在真实样本
        # 上验证**（仓库内无 CNKI XML 样本），无命中则空，绝不臆造。
        # references：CNKI 不含 cited references（CiteSpace 官方 FAQ 亦如此），
        # 故不采集。
        aff = [g(p) for p in (
            r"<Organization>(.*?)</Organization>",
            r"<Institution>(.*?)</Institution>",
            r"<DegreeGrantor>(.*?)</DegreeGrantor>",
            r"<AuthorAddress>(.*?)</AuthorAddress>",
        ) if g(p)]
        d = {
            "title": title,
            "abstract": g(r"<Abstract>(.*?)</Abstract>") or g(r"<Abstracts>(.*?)</Abstracts>"),
            "keywords": [k.strip() for k in re.split(r"[;；,，]", kw) if k.strip()],
            "journal": g(r"<Medium>.*?<Media[^>]*>(.*?)</Media>")
                       or g(r"<Journal>(.*?)</Journal>") or g(r"<Source>(.*?)</Source>"),
            "year": g(r"<Year>(.*?)</Year>"),
            "doi": g(r"<DOI>(.*?)</DOI>") or _doi_from_url(g(r"<Url>(.*?)</Url>")),
            "authors": authors, "_display": authors,
            "affiliations": aff,
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

    [!]  `{Author}` 可能有多个（多作者），需累积而非覆盖 —— 故用 append。
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
                # 机构：NoteExpress 原生导出用 {Author Address}（可含 ';' 多条）。
                # 被引：NoteExpress 无公开稳定字段，按候选键 best-effort；
                # **未在真实样本上验证**（仓库内无 .net 样本），无命中则空。
                "affiliations": [cur.get("Author Address", "")],
                "references": [cur.get("Cited References", ""),
                               cur.get("References", ""),
                               cur.get("Reference List", "")],
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
_EN_TAGGED = re.compile(r"^%([0-9A-Za-z+])[ \t]+(.*)$")


def load_enl_tagged(path: Path) -> list:
    """解析 EndNote「Refer/BibIX」tagged 导出（`%X ` 形式）。

    [!]  与 EndNote XML（<record>…</record>）是**两种不同格式**。
       CNKI 导出的 .enw 是本格式；文件名相同极易误判，故按内容嗅探。

    标签：%0 类型 / %T 题名 / %A 作者(可多个) / %D 年份 / %Y 年份 / %K 关键词(;) /
          %X 摘要 / %I 出版者/期刊 / %J 期刊 / %V 卷 / %N 期 / %P 页 / %U URL /
          %W 数据库 / %9 文献类型 / %R 备注 / %+ 作者地址(机构，可多个)

    [!]  年份标签 %D 与 %Y 并存：EndNote 原生 Refer/BibIX 用 %D（常为
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
                # 机构：EndNote Refer 的 %+ 即 Author Address（可多个）。
                # 被引：tagged 格式无标准被引标签；CNKI 的 .enw 本身不含引文
                #（CiteSpace FAQ），故不采集，避免臆造。
                "affiliations": cur.get("affiliations", []),
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
            elif tag == "+":
                cur.setdefault("affiliations", []).append(val)
            else:
                cur.setdefault(tag, val)
        elif line.strip() and cur:
            last = list(cur.keys())[-1]
            # 续行只并入**字符串**字段；列表字段（__A/affiliations）不接受续行，
            # 否则 (list + str) 会抛 TypeError 导致整批静默失败。
            if last != "__A" and isinstance(cur.get(last), str):
                cur[last] = (cur[last] + " " + line.strip()).strip()
    flush()
    return out


# ══════════════════════════════════════════════════════════
# 9. CNKI GB7714 引用列表（纯文本 .txt）
# ══════════════════════════════════════════════════════════
def load_cnki_gb7714(path: Path) -> list:
    """解析 CNKI「引文列表」纯文本：`[1]作者.题名[D].来源,年份.DOI:xxx.`

    [!]  这类导出**只有题录、没有摘要与关键词**，故几乎全落入 fallback_title 降级层。
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
# 10. Zotero RDF（.rdf）
# ══════════════════════════════════════════════════════════
def load_zotero_rdf(path: Path) -> list:
    """解析 Zotero RDF（bibo/dc/prism/foaf 命名空间）。

    命名空间以Zotero 官方导出（dcterms/bib）为主，兼容 bibo/prism/foaf 风格。
    注意：journal / year / doi / abstract 的抽取必须在作者分支之外，
    否则无作者记录会静默丢失这些字段。
    """
    import xml.etree.ElementTree as ET
    txt = _read_text(path)
    # Zotero 官方导出用 dcterms/bib，另有bibo/prism/foaf 风格。
    # 两种都要认——否则用户从 Zotero「导出文献」得到的官方 .rdf 会被识别为
    # Zotero RDF 却抽不出任何字段（实测：标题之外全空）。
    ns = {
        "bibo": "http://purl.org/ontology/bibo/",
        "dc": "http://purl.org/dc/elements/1.1/",
        "dcterms": "http://purl.org/dc/terms/",
        "bib": "http://purl.org/net/biblio#",
        "z": "http://www.zotero.org/namespaces/export/#",
        "prism": "http://prismstandard.org/namespaces/basic/2.0/",
        "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        "foaf": "http://xmlns.com/foaf/0.1/",
        "link": "http://www.w3.org/2005/Atom/",
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
        if not journal:
            # Zotero 官方导出：期刊名直接放在 dc:source
            journal = (art.findtext("{%(dc)s}source" % ns) or "").strip()
        if not authors:
            # Zotero 官方导出：<dc:creator><bib:Author><bib:lastname>…</bib:Author></dc:creator>
            for cr in art.findall("{%(dc)s}creator" % ns):
                au = cr.find("{%(bib)s}Author" % ns)
                if au is None:
                    if (cr.text or "").strip():
                        authors.append((cr.text or "").strip())
                    continue
                last = (au.findtext("{%(bib)s}lastname" % ns) or "").strip()
                first = (au.findtext("{%(bib)s}firstname" % ns) or "").strip()
                nm = (last + (", " + first if first else "")).strip(", ")
                if nm:
                    authors.append(nm)
        kw = [k.strip() for k in
              re.split(r"[;；,，]", art.findtext("{%(dc)s}subject" % ns) or "") if k.strip()]
        # 年份：dc:date 或 <dcterms:issued><dcterms:date>
        year_raw = (art.findtext("{%(dc)s}date" % ns)
                    or art.findtext("{%(dcterms)s}issued/{%(dcterms)s}date" % ns)
                    or art.findtext("{%(dcterms)s}date" % ns) or "")
        # 摘要：用 dc:description；Zotero 官方用 dcterms:abstract
        abstract = (art.findtext("{%(dc)s}description" % ns)
                    or art.findtext("{%(dcterms)s}abstract" % ns) or "")
        # DOI：官方导出常写成 <dc:identifier>DOI 10.xxxx/yyy</dc:identifier>
        # Zotero 官方把 DOI 放在 <dc:identifier>DOI 10.xxxx/…</dc:identifier>
        doi = (art.findtext("{%(prism)s}doi" % ns)
               or art.findtext("{%(bibo)s}doi" % ns) or "")
        if not doi:
            for ident in art.findall("{%(dc)s}identifier" % ns):
                if re.search(r"10\.\d{4,9}/", ident.text or ""):
                    doi = ident.text
                    break
        m = re.search(r"(10\.\d{4,9}/\S+)", doi)
        if m:
            doi = m.group(1)
        elif doi and not doi.lower().startswith("doi"):
            doi = ""
        # 机构：Zotero RDF 官方导出只有 dc:creator（无机构）与 dc:source/identifier，
        # 实测样本（zotero_test.rdf，80 条）无任何机构类标签 → 不采集。
        # 被引：Zotero 不存参考文献 → 不采集。二者均为数据源限制，非解析缺失。
        d = {
            "title": title.strip(), "abstract": abstract,
            "journal": journal,
            "year": re.sub(r"\D.*", "", year_raw),
            "doi": doi,
            "keywords": kw, "authors": authors, "_display": authors,
        }
        out.append(_ref_from_fields(d, path, len(out) + 1, multi_author=True))
    return out


# ══════════════════════════════════════════════════════════
# 11. Better BibTeX JSON（.json）—— reference-import
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
            # 机构：Better BibTeX 的 fields 里可能带 institution/university/
            # organization（依条目类型而定）→ best-effort。被引：无对应字段。
            "affiliations": [f.get(k, "") for k in
                             ("institution", "university", "organization")
                             if f.get(k)],
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
                # 机构：C1=Addresses（可重复，形如 "[作者] 机构, 城市, 国家"）；
                #       RP=Reprint Addresses。
                # 被引：CR=Cited References（每行一条、可重复）。
                # 二者此前在 build_report 白名单里被显式忽略（缺口 A）。
                "affiliations": cur.get("affiliations", []),
                "references": cur.get("references", []),
            }
            out.append(_ref_from_fields(d, path, len(out) + 1, multi_author=True))
        cur, last = {}, None

    for line in txt.splitlines():
        if not line.strip():
            continue
        if line.startswith("   "):                     # 续行
            # 只并入字符串字段；C1/RP/CR 等列表字段不接受续行（否则 list+str 报错）
            if last and isinstance(cur.get(last), str):
                cur[last] = (cur[last] + " " + line[3:].strip()).strip()
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
        elif tag == "C1":
            # 机构：C1=Addresses，形如 "[作者, 作者] 机构, 城市, 邮编, 国家"；
            # 方括号作者前缀由建网层 normalize_org 剥离。
            # [!] 不含 RP（Reprint Addresses）：前缀是人名，会造成伪机构。
            cur.setdefault("affiliations", []).append(val)
        elif tag == "CR":
            cur.setdefault("references", []).append(val)
        else:
            cur.setdefault(tag, val)
    flush()
    return out


# ══════════════════════════════════════════════════════════
# 13. Web of Science HTML 导出（.html）
# ══════════════════════════════════════════════════════════
# 已知标签白名单。[!]  必需：题名/摘要本身可能含冒号
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


def load_wos_html(path: Path) -> list:
    """解析 WoS HTML 导出（实测 50 条 / 10051 个展平行）。

    [!]  两个结构陷阱（都会静默丢数据）：
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
    LIST_FIELDS = {"affiliations", "references"}     # 多值：逐行/逐段累积为列表
    ACC |= LIST_FIELDS                                # 列表字段同样接受续行
    out, cur, pending = [], {}, None

    def put(field, val):
        if not field or not val:
            return
        if field in LIST_FIELDS:
            cur.setdefault(field, []).append(val)
        elif field in ACC and cur.get(field):
            cur[field] = (cur[field] + " " + val).strip()
        else:
            cur[field] = val.strip()

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
            # [!]  正式出版年优先于在线优先年。WoS HTML 的标签顺序是
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
        elif low in ("addresses", "affiliations"):
            # 机构：Addresses / Affiliations（缺口 A 曾整体丢弃）
            # [!] 不含 "reprint addresses"/"publisher address"：前者前缀是作者
            # 姓名（会造成伪机构），后者是**出版者**地址而非作者机构。
            put("affiliations", val)
        elif low == "cited references":
            # 被引：Cited References（WoS HTML 的一大段，' ; ' 分隔多条）
            put("references", val)
        # 其余标签（Times Cited / Usage Count / Funding …）不参与分析

    def build(n):
        kws = [k.strip() for k in re.split(r"[;；]", cur.get("keywords", "")) if k.strip()]
        au = cur.get("__AU", [])
        d = {"title": cur.get("title", ""), "abstract": cur.get("abstract", ""),
             "journal": cur.get("journal", ""), "year": cur.get("year", ""),
             "doi": cur.get("doi", ""), "keywords": kws, "authors": au, "_display": au,
             "affiliations": cur.get("affiliations", []),
             "references": cur.get("references", [])}
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
                    # 列表字段初始化为 []，字符串字段初始化为 ""
                    cur.setdefault(pending, [] if pending in LIST_FIELDS else "")
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
    [!]  xlrd 2.x **只读 .xls**；.xlsx 请改用 openpyxl 或先转 .xls。
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
    # 机构 / 被引：WoS .xls 导出含 Addresses / Affiliations / Reprint Addresses /
    # Cited References 列（列名按 WoS 导出规范；本仓库无 .xls 真实样本，属规范实现）
    c_addr = col("addresses", "affiliations",
                 "机构", "作者单位")
    c_cr   = col("cited references", "references", "参考文献")
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
             "authors": authors, "_display": authors,
             "affiliations": [g(c_addr)], "references": [g(c_cr)]}
        out.append(_ref_from_fields(d, path, len(out) + 1, multi_author=True))
    return out



# ══════════════════════════════════════════════════════════
# 格式自动识别
# ══════════════════════════════════════════════════════════
ADAPTERS = {
    "zotero": load_zotero, "ris": load_ris, "bibtex": load_bibtex,
    "enl_xml": load_enl_xml, "enl_tagged": load_enl_tagged,
    "noteexpress": load_noteexpress, "cnki_xml": load_cnki_xml,
    "cnki_gb7714": load_cnki_gb7714, "csv": load_csv,
    "zotero_rdf": load_zotero_rdf, "betterbibtex_json": load_betterbibtex_json,
    "wos_tagged": load_wos_tagged, "wos_html": load_wos_html, "wos_xls": load_wos_xls,
    # EndNote .enl 只读链路（load_enl 的第二参数默认 None = 全库）
    "enl": load_enl,
}


def detect_key(p: Path) -> str:
    """**内容优先**嗅探，只返回适配器 key（不加载），供 main 先判定再决定是否带分类过滤。

    为什么把"判定"与"加载"拆开：`--group` 需要按分类过滤 .enl，过滤参数必须在加载
    前传给 EndNote 适配器；若沿用旧的 detect_and_load 一步到位，就再也插不进参数。
    拆分后 `detect_and_load(p)` 仍保持旧的单参签名（run_checks 依赖它）。

    实测教训（CNKI 真实样本）：
      · `.enw` 既可能是 EndNote XML（<record>），也可能是 tagged（%T/%A）—— 两者不同格式；
      · `.txt` 可能是 CNKI XML（<Bibliographies>）、RIS、或 GB7714 引文列表；
      · `.es6` 是 CNKI 客户端的**加密导出**（头部 `XCNKI_ENCRYPT_1.0`），
        无密钥不可解析 —— 必须明确报错并指引改用 RIS/EndNote XML/BibTeX 导出，
        绝不能静默返回 0 条。
    """
    name = p.name.lower()
    if name == "zotero.sqlite" or p.suffix.lower() == ".sqlite":
        return "zotero"

    ext = p.suffix.lower()
    # [!]  .enl 必须在读文本 head 之前判定：它是 SQLite 二进制，走 _read_text 只会
    #    得到乱码而落进"无法识别格式"。且旧版 .enl 是文本格式，需明确报错而非假装能读。
    if ext == ".enl":
        if p.read_bytes()[:16].startswith(b"SQLite format 3"):
            return "enl"
        raise EnlError(2, f"{p.name} 不是 SQLite 格式的 .enl（旧版 EndNote 库）；"
                          f"本工具只读 EndNote 20+ 的 SQLite 库，请在 EndNote 中"
                          f"升级/另存为该格式后重试")

    # [!]  嗅探窗口必须够大：实测 WoS HTML 的 "Web of Science" 标记在 4KB 之后，
    #    窗口过小会把 .html 误判为"无法识别格式"。
    # [!]  文本类扩展名必须走 _read_text：UTF-16 的 `TY  - ` 在字节层面是
    #    `T\x00Y\x00 \x00 \x00-\x00`，用 utf-8+replace 切片后正则 ^TY\s{2}- 永不匹配
    #    → UTF-16 RIS 明明有记录却被判"无法识别格式"（exit 2，数据全丢）。
    #    .xls/.xlsx 等二进制**不能**走 _read_text：OLE2 魔数 \xd0\xcf\x11\xe0
    #    依赖字节级判断，故保留原else 分支。
    if ext in (".txt", ".html", ".htm", ".xml", ".rdf", ".enw", ".net", "",
               ".ris", ".bib", ".csv", ".tsv"):
        head = _read_text(p)[:20000]
    else:
        head = p.read_bytes()[:20000].decode("utf-8", errors="replace")

    if "XCNKI_ENCRYPT" in head:
        raise EnlError(2, f"{p.name} 是 CNKI 客户端加密导出（XCNKI_ENCRYPT），"
                          f"无密钥不可解析。请在 CNKI 客户端改用「引文 → 导出 → "
                          f"RIS / EndNote XML / BibTeX」后重新导入")

    if "<Bibliographies" in head or "<Bibliography>" in head:
        return "cnki_xml"
    if _EN_TAGGED.match(head.lstrip()[:4] or " ") or re.search(r"^%0\s", head, re.M):
        return "enl_tagged"
    if re.search(r"^\{Reference Type\}\s*:", head, re.M) or _NE_FIELD.match(head.strip()[:40] or " "):
        return "noteexpress"
    if re.search(r"^\[\d+\]", head, re.M):
        return "cnki_gb7714"
    # ── Web of Science 系列 ──
    if ext == ".xls" or head.startswith("\xd0\xcf\x11\xe0"):
        return "wos_xls"
    if ext in (".html", ".htm") and "Web of Science" in head:
        return "wos_html"
    if re.search(r"(?m)^FN\s+.*Web of Science", head) or (
            re.search(r"(?m)^VR\s+1\.0", head) and re.search(r"(?m)^ER\s*$", head)):
        return "wos_tagged"
    if "<record>" in head or re.search(r"<EndNote|\bREFER\b", head):
        return "enl_xml"
    if ext == ".rdf" or ("xmlns" in head and re.search(r"rdf:|bibo:", head)):
        return "zotero_rdf"
    if ext == ".json" or head.lstrip().startswith("{"):
        obj = json.loads(_read_text(p)) if head.lstrip().startswith("{") else {}
        if obj.get("format") == "academic-lit-analysis/refs@1":
            raise EnlError(2, f"{p.name} 已是本工具的 refs.json 产物，无需再导入")
        return "betterbibtex_json"
    if re.search(r"^@\w+\s*\{", head, re.M):
        return "bibtex"
    if re.search(r"^(TY|ER)\s{2}-", head, re.M):
        return "ris"
    if ext == ".csv":
        return "csv"
    raise EnlError(2, f"无法识别格式：{p.name}（支持 zotero.sqlite / EndNote .enl / RIS / "
                      f"BibTeX / EndNote XML / EndNote tagged / NoteExpress .net / CNKI XML / "
                      f"CNKI GB7714 / CSV / Zotero RDF / Better BibTeX JSON）")


def detect_and_load(p: Path) -> tuple[str, list]:
    """嗅探并加载（保持旧单参签名：run_checks 及既有调用方依赖它）。"""
    key = detect_key(p)
    return key, ADAPTERS[key](p)


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
    ap = argparse.ArgumentParser(description="多来源文献导入（EndNote .enl/Zotero/RIS/BibTeX/EN-XML/CSV）")
    ap.add_argument("paths", nargs="+", help="一个或多个文件/目录")
    ap.add_argument("--format", default="auto",
                    choices=["auto", "zotero", "ris", "bibtex", "enl_xml",
                             "enl_tagged", "noteexpress", "cnki_xml",
                             "cnki_gb7714", "csv", "zotero_rdf", "betterbibtex_json",
                             "wos_tagged", "wos_html", "wos_xls", "enl"])
    ap.add_argument("--out", help="写出 refs.json")
    ap.add_argument("--dedup", action="store_true", help="跨来源按 DOI/标题去重")
    ap.add_argument("--csv", help="额外导出扁平 CSV（便于人工核对）")
    # EndNote 分类过滤（仅对 .enl 生效）。可多次传以合并多个分类。
    ap.add_argument("--group", action="append", default=None, metavar="名称或ID",
                    help="只导出 EndNote .enl 中该分类的文献（名称或数字 ID），"
                         "可多次传以合并多个分类；分类不存在会报错并列出可用分类")
    ap.add_argument("--list-groups", action="store_true",
                    help="列出 .enl 库中全部分类（名称/ID/条数）后退出")
    a = ap.parse_args()

    files: list[Path] = []
    for raw in a.paths:
        p = Path(raw).expanduser()
        if p.is_dir():
            files += [f for f in sorted(p.rglob("*"))
                      if f.is_file() and f.suffix.lower() in
                      (".ris", ".enw", ".xml", ".bib", ".csv", ".txt",
                       ".net", ".rdf", ".es6", ".html", ".htm", ".xls", ".enl")
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

    enl_files = [f for f in files if f.suffix.lower() == ".enl"]

    # ── --list-groups：列出分类后退出（不导入）──
    if a.list_groups:
        if not enl_files:
            print("[error] --list-groups 仅适用于 EndNote .enl 库；本批输入中没有 .enl",
                  file=sys.stderr)
            print(f"[hint] {EXIT[4]}", file=sys.stderr)
            return 4
        libs = []
        for f in enl_files:
            groups = list_enl_groups(f)
            print(f"[info] {f.name} 共 {len(groups)} 个分类：", file=sys.stderr)
            for g in groups:
                print(f"    {g['id']}\t{g['name']}\t{g['count']} 条", file=sys.stderr)
            libs.append({"library": f.name,
                         "groups": [{"id": g["id"], "name": g["name"], "count": g["count"]}
                                    for g in groups]})
        emit({"ok": True, "exit_code": 0, "libraries": libs})
        return 0

    # ── 预解析 .enl 分类：必须**硬失败**（分类名打错绝不能静默导全库）。故放在
    #    per-file try 之外，让 EnlError(4) 直接冒泡成参数错误。──
    if a.group and not enl_files:
        print("[error] --group 仅适用于 EndNote .enl 库；本批输入中没有 .enl",
              file=sys.stderr)
        print(f"[hint] {EXIT[4]}", file=sys.stderr)
        return 4
    enl_selection: dict = {}
    enl_group_meta: list = []
    for f in enl_files:
        gids, sel = _resolve_enl_groups(f, a.group)
        enl_selection[f] = gids
        enl_group_meta.extend(sel)

    all_refs: list = []
    per_source, failures = [], []
    for f in files:
        try:
            key = detect_key(f) if a.format == "auto" else a.format
            if key == "enl":
                # .enl 走带分类过滤的加载；其余来源照旧
                refs = load_enl(f, enl_selection.get(f))
            else:
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
    # 数据范围标注：用 --group 时把所选分类名写进 meta，供报告如实标注"本次只分析了哪一类"。
    if enl_group_meta:
        payload["meta"]["groups"] = enl_group_meta

    # ── 机构 / 被引字段补入 refs.json（缺口 A 修复，见模块头说明）──
    # Ref 数据类未声明这两个字段（不得改动 lit_core）→ asdict()
    # 不会序列化它们，故按 list_refs 的同序 zip 补写。仅非空才写：这样
    # "本就无机构/被引的来源"产出与改动前**逐字节一致**，不动既有 500 条的
    # 既有字段与统计口径。meta.field_coverage 记录覆盖率，供空态判定与报告使用。
    _n_aff = _n_cred = 0
    for _rd, _r in zip(payload["refs"], all_refs):
        _aff = getattr(_r, "affiliations", None)
        _cred = getattr(_r, "references", None)
        if _aff:
            _rd["affiliations"] = _aff
            _n_aff += 1
        if _cred:
            _rd["references"] = _cred
            _n_cred += 1
        # WoS 溯源字段（仅 BibTeX 通路会挂载）：同样仅非空才写，保持兼容
        _uid = getattr(_r, "unique_id", None)
        if _uid:
            _rd["unique_id"] = _uid
        _tc = getattr(_r, "times_cited", None)
        if _tc is not None:
            _rd["times_cited"] = _tc
    payload["meta"]["field_coverage"] = {
        "affiliations_docs": _n_aff, "references_docs": _n_cred,
        "total": len(all_refs),
        "affiliations_sources": "RIS AD/C1..C7、WoS tagged C1、WoS HTML/CSV/xls 的 "
                                "Addresses/Affiliations、WoS BibTeX Affiliation/"
                                "Affiliations、EndNote tagged %+、"
                                "NoteExpress {Author Address}、Zotero university/"
                                "institution、BibTeX institution（Best-effort）",
        "references_sources": "RIS CR、WoS tagged CR、WoS HTML/CSV 的 Cited References、"
                              "WoS BibTeX Cited-References",
    }

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
