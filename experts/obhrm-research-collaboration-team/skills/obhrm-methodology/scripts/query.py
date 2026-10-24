#!/usr/bin/env python3
"""选刊助手查询引擎 + CLI（v4）。

核心函数 ``search(keyword) -> list[dict]``：
- 先按 norm_issn 精确（输入像 ISSN 时）；
- 否则按 norm_title 前缀/包含模糊 + 原始 title 包含模糊；
- 返回命中期刊列表，每项为期刊核心字段 + ``ratings`` 分组
  （按 10 个 standard 分组，组内按 attr 列出 value；缺失标准显式 ``null``）；
- 支持多面过滤：``area``（学科域）/ ``subfield``（规范子领域）/
  ``tier``（顶级榜）/ ``cas``（中科院分区）/ ``jcr``（JCR 分区）/
  ``lang``（语种）/ ``country``（国家），全部 AND 叠加。

CLI：
    python query.py "Academy of Management Journal"
    python query.py --issn 0001-4273
    python query.py "管理世界" --json
    python query.py "leadership" --subfield 组织行为 --tier ft50 --cas 1
    python query.py "marketing" --subfield 市场营销 --jcr Q1

Skill 调用约定：``python query.py "<keyword>" --json`` 读取返回的 JSON 数组。
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

# 确保套件包可被导入（独立运行 python query.py 时）
_SKILL_DIR = Path(__file__).resolve().parent.parent
if str(_SKILL_DIR) not in sys.path:
    sys.path.append(str(_SKILL_DIR))

from obhrm_research_base.journal.constants import ALL_STANDARDS, STANDARD_LABELS
from obhrm_research_base.journal.db import SchemaError, get_conn
from obhrm_research_base.journal.normalize import (
    is_issn_like,
    norm_issn,
    norm_query_title,
    norm_title,
)

# 顶级榜过滤子查询（与 journals 表通过 journal_id 关联）
TIER_SUBQUERY: dict[str, str] = {
    "ft50": "EXISTS(SELECT 1 FROM ratings r WHERE r.journal_id=journals.id AND r.standard='FT50')",
    "utd24": "EXISTS(SELECT 1 FROM ratings r WHERE r.journal_id=journals.id AND r.standard='UTD24')",
    "abs4": "EXISTS(SELECT 1 FROM ratings r WHERE r.journal_id=journals.id AND r.standard='ABS2024' AND r.value IN ('4','4*'))",
    "fms_t1": "EXISTS(SELECT 1 FROM ratings r WHERE r.journal_id=journals.id AND r.standard IN ('FMS2025_GLOBAL','FMS2025_CN') AND r.attr='tier' AND r.value='T1')",
}


def _build_ratings(conn: sqlite3.Connection, journal_id: int) -> dict[str, dict[str, str] | None]:
    """聚合某期刊的全部评级为 standard -> {attr: value} 结构（缺失为 None）。"""
    ratings: dict[str, dict[str, str] | None] = {s: None for s in ALL_STANDARDS}
    rows = conn.execute(
        "SELECT standard, attr, value FROM ratings WHERE journal_id = ?",
        (journal_id,),
    ).fetchall()
    for r in rows:
        std = r["standard"]
        if ratings.get(std) is None:
            ratings[std] = {}
        ratings[std][r["attr"]] = r["value"]
    return ratings


def _journal_dict(row: sqlite3.Row, ratings: dict) -> dict[str, Any]:
    return {
        "id": row["id"],
        "title": row["title"],
        "title_cn": row["title_cn"],
        "issn_print": row["issn_print"],
        "issn_e": row["issn_e"],
        "publisher": row["publisher"],
        "country": row["country"],
        "language": row["language"],
        "subject_area": row["subject_area"],
        "subfields": row["subfields"],
        "data_version": row["data_version"],
        "ratings": ratings,
    }


def search(keyword: str, issn: str | None = None, limit: int = 10,
           area: str | None = None, subfield: str | None = None,
           tier: str | None = None, cas: str | None = None,
           jcr: str | None = None, lang: str | None = None,
           country: str | None = None,
           pku: str | None = None, cscd: str | None = None,
           ei: str | None = None) -> list[dict[str, Any]]:
    """按刊名 / ISSN 查询，返回聚合全部评级的期刊字典列表。

    多结果时返回列表由调用方选择（建议取第一条或提示用户选择）。

    匹配规则：
    - 输入像 ISSN（或显式传入 ``issn``）时，按 ISSN 精确检索，同时匹配
      ``issn_print`` 与 ``issn_e``，忽略大小写、连字符与空格。
    - 否则按刊名模糊检索：大小写不敏感、首尾去空格、折叠多余空白，
      并额外做 ``&``↔``and``、``-``↔空格 的等价归一（见 ``norm_query_title``）。

    多面过滤（全部 AND 叠加，可单独或组合使用）：
    - ``area``：``subject_area`` 含该词（如 管理科学 / 心理学 / 商科与管理）。
    - ``subfield``：``subfields`` 含该规范子领域（如 组织行为 / 人力资源管理 /
      战略管理 / 市场营销 / 会计 / 金融），精确匹配规范标签。
    - ``tier``：``ft50``(命中FT50) / ``utd24``(命中UTD24) /
      ``abs4``(ABS 2024 评级 4 或 4*) / ``fms_t1``(FMS 评级 T1)。
    - ``cas``：中科院分区 1–4（``CAS2025.zone``）。
    - ``jcr``：JCR 2025 分区 Q1–Q4（``JCR2025.quartile``）。
    - ``pku``：``1`` 仅列出北大核心 2023 收录刊。
    - ``cscd``：``core`` 核心库 / ``ext`` 扩展库。
    - ``ei``：``1`` 仅列出 EI 2026 收录刊。
    - ``lang``：``zh``(语言=中文) / ``en``(非中文，多为英文；英文刊该列常为 NULL)。
    - ``country``：出版国家/地区模糊匹配。

    函数签名保持向后兼容：新增行为不改变既有调用方的结果结构。
    """
    if tier is not None and tier not in TIER_SUBQUERY:
        raise ValueError(f"未知 tier：{tier}（可选 {list(TIER_SUBQUERY)}）")
    has_facet = any(x is not None for x in (area, subfield, tier, cas, jcr, lang, country, pku, cscd, ei))
    if not keyword and not issn and not has_facet:
        return []
    conn = get_conn()
    try:
        nissn = norm_issn(issn) if issn else (
            norm_issn(keyword) if (keyword and is_issn_like(keyword)) else None
        )
        if nissn:
            # 同时匹配 print / eISSN，忽略大小写、连字符、空格
            # 注意：用括号把 OR 组合成一组，确保后续 AND 过滤作用于整体而非仅末项
            sql = (
                "SELECT * FROM journals "
                "WHERE (lower(replace(replace(coalesce(issn_print,''),'-',''),' ','')) = ? "
                "   OR lower(replace(replace(coalesce(issn_e,''),'-',''),' ','')) = ?)"
            )
            params: list[Any] = [nissn, nissn]
        elif keyword:
            # 刊名模糊：DB 对齐归一 + 用户友好等价归一，二者择一即可命中
            # OR 组用括号包裹，使多面过滤（AND）作用于整个匹配条件
            nt = norm_title(keyword)
            nt_loose = norm_query_title(keyword, loose=True)
            _esc = lambda s: s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            like_nt = f"%{_esc(nt)}%" if nt else "%"
            like_nt_loose = f"%{_esc(nt_loose)}%" if nt_loose else "%"
            like_raw = f"%{_esc(keyword)}%"
            sql = (
                "SELECT * FROM journals "
                "WHERE (norm_title LIKE ? ESCAPE '\\' OR norm_title LIKE ? ESCAPE '\\' "
                "   OR title LIKE ? ESCAPE '\\' OR title_cn LIKE ? ESCAPE '\\')"
            )
            params = [like_nt, like_nt_loose, like_raw, like_raw]
        else:
            # 纯 facet 浏览：无关键词，仅按过滤条件全表筛选
            sql = "SELECT * FROM journals WHERE 1=1"
            params = []
        # 多面过滤（AND 叠加）
        if area:
            sql += " AND subject_area LIKE ?"
            params.append(f"%{area}%")
        if subfield:
            sql += " AND ','||COALESCE(subfields,'')||',' LIKE '%,'||?||',%'"
            params.append(subfield)
        if tier:
            sql += " AND " + TIER_SUBQUERY[tier]
        if cas:
            sql += (" AND EXISTS(SELECT 1 FROM ratings r WHERE r.journal_id=journals.id "
                    "AND r.standard='CAS2025' AND r.attr='zone' AND r.value=?)")
            params.append(str(cas))
        if jcr:
            sql += (" AND EXISTS(SELECT 1 FROM ratings r WHERE r.journal_id=journals.id "
                    "AND r.standard='JCR2025' AND r.attr='quartile' AND r.value=?)")
            params.append(jcr)
        if pku:
            sql += (" AND EXISTS(SELECT 1 FROM ratings r WHERE r.journal_id=journals.id "
                    "AND r.standard='PKU2023' AND r.attr='in_list')")
        if cscd:
            sql += (" AND EXISTS(SELECT 1 FROM ratings r WHERE r.journal_id=journals.id "
                    "AND r.standard='CSCD2026' AND r.attr='library' AND r.value=?)")
            params.append('核心库' if cscd == 'core' else '扩展库')
        if ei:
            sql += (" AND EXISTS(SELECT 1 FROM ratings r WHERE r.journal_id=journals.id "
                    "AND r.standard='EI2026' AND r.attr='in_list')")
        if lang == "zh":
            sql += " AND language='中文'"
        elif lang == "en":
            sql += " AND (language IS NULL OR language<>'中文')"
        if country:
            sql += " AND country LIKE ?"
            params.append(f"%{country}%")
        order = "length(norm_title) ASC, id ASC" if keyword else "id ASC"
        sql += f" ORDER BY {order} LIMIT ?"
        params.append(limit)
        jrows = conn.execute(sql, params).fetchall()
        results: list[dict[str, Any]] = []
        for r in jrows:
            ratings = _build_ratings(conn, int(r["id"]))
            results.append(_journal_dict(r, ratings))
        return results
    finally:
        conn.close()


def recommend_by_category(
    conn: sqlite3.Connection, journal_id: int, limit: int = 5
) -> list[dict[str, Any]]:
    """返回与指定期刊同 ``subject_area`` 的相似期刊（不含自身）。

    用于 SKILL 工作流第 6 步「相似期刊推荐」。匹配基于归类后的
    ``subject_area`` 字段（管理科学 / 心理学 / 社会学 / 商科与管理 …），
    覆盖全部保留刊，而非仅 CAS 大类。若目标期刊无 ``subject_area``，返回空列表。
    """
    cat_row = conn.execute(
        "SELECT subject_area FROM journals WHERE id = ?",
        (journal_id,),
    ).fetchone()
    if not cat_row or not cat_row["subject_area"]:
        return []
    category = cat_row["subject_area"]
    # 取目标刊的「主领域」（逗号分隔中的第一个桶）做同领域推荐
    primary = category.split(",")[0]
    rows = conn.execute(
        """
        SELECT id, title, issn_print, subject_area
        FROM journals
        WHERE subject_area LIKE ? AND id != ?
        ORDER BY id ASC
        LIMIT ?
        """,
        (f"%{primary}%", journal_id, limit),
    ).fetchall()
    return [
        {"id": r["id"], "title": r["title"],
         "issn_print": r["issn_print"], "subject_area": r["subject_area"]}
        for r in rows
    ]


# ---------------------------------------------------------------------------
# 文本渲染（CLI 默认输出）
# ---------------------------------------------------------------------------

def _cas_zone_change(zone: str | None, zone_2023: str | None) -> str | None:
    """计算中科院分区 2023→2025 变化（分区数字越小越好）。无 2023 数据返回 None。"""
    if not zone or not zone_2023:
        return None
    try:
        z25, z23 = int(zone), int(zone_2023)
    except (TypeError, ValueError):
        return None
    if z25 < z23:
        return f" 分区变化：{z23}区 → {z25}区（升级 ↑）"
    if z25 > z23:
        return f" 分区变化：{z23}区 → {z25}区（降级 ↓）"
    return f"- 分区变化：{z23}区 → {z25}区（持平）"


def _render_rating_group(std: str, grp: dict | None) -> str:
    """渲染单个 standard 的字段（无则标注未收录）。"""
    label = STANDARD_LABELS.get(std, std)
    if not grp:
        return f"  · {label}：未收录"
    change_line = None
    parts = []
    for attr, val in grp.items():
        if std == "CAS2025" and attr == "zone_2023":
            continue  # zone_2023 转为友好的分区变化行，不列裸字段
        parts.append(f"{attr}={val}")
    if std == "CAS2025":
        change_line = _cas_zone_change(grp.get("zone"), grp.get("zone_2023"))
    base = f"  · {label}：{'; '.join(parts)}"
    if change_line:
        base += f"\n    {change_line}"
    return base


def render_text(results: list[dict]) -> str:
    """把查询列表渲染为可读文本。"""
    if not results:
        return "未找到匹配的期刊。"
    lines: list[str] = []
    for j in results:
        lines.append("=" * 60)
        lines.append(f"期刊：{j['title']}")
        if j.get("title_cn"):
            lines.append(f"中文名：{j['title_cn']}")
        lines.append(f"ISSN(print)：{j.get('issn_print') or '—'}")
        lines.append(f"ISSN(e)    ：{j.get('issn_e') or '—'}")
        lines.append(f"出版社    ：{j.get('publisher') or '—'}")
        if j.get("subject_area"):
            lines.append(f"学科领域  ：{j['subject_area']}")
        if j.get("subfields"):
            lines.append(f"子领域    ：{j['subfields']}")
        lines.append("-" * 60)
        lines.append("评级：")
        for std in ALL_STANDARDS:
            lines.append(_render_rating_group(std, j["ratings"].get(std)))
    lines.append("=" * 60)
    return "\n".join(lines)


def _degrade_message(exc: sqlite3.OperationalError) -> str:
    """把 sqlite 底层异常翻译为 SKILL.md 约定的友好降级话术。"""
    msg = str(exc).lower()
    if "no such table" in msg:
        return ("数据库表缺失，可能文件损坏。"
                "请重新获取完整的 skills/journal-library/db/journals.db 后重试。")
    if "unable to open" in msg or "no such file" in msg:
        return "无法打开数据库文件，请确认 skills/journal-library/db/journals.db 存在且有读取权限。"
    return (f"数据库读取异常：{exc}。"
            "请确认技能目录下的 skills/journal-library/db/journals.db 完整可用后重试。")


def _emit_degrade(as_json: bool, text: str) -> None:
    """按输出格式打印降级提示，并以非零码退出。"""
    if as_json:
        print(json.dumps({"error": "database_unavailable", "message": text},
                         ensure_ascii=False, indent=2))
    else:
        print(f"[!] {text}")
    sys.exit(2)


def _run() -> None:
    ap = argparse.ArgumentParser(description="期刊分区查询引擎")
    ap.add_argument("keyword", nargs="?", help="刊名 / 关键词")
    ap.add_argument("--issn", help="按 ISSN 精确查询")
    ap.add_argument("--similar", type=int, metavar="JOURNAL_ID",
                    help="按期刊 id 推荐同学科领域相似期刊")
    ap.add_argument("--area", help="按学科领域过滤（如 管理科学 / 心理学 / 商科与管理）")
    ap.add_argument("--subfield", help="按规范子领域过滤（如 组织行为 / 人力资源管理 / 战略管理 / 市场营销 / 会计 / 金融）")
    ap.add_argument("--tier", choices=list(TIER_SUBQUERY),
                    help="按顶级榜过滤：ft50 / utd24 / abs4(ABS 2024 4或4*) / fms_t1(FMS T1)")
    ap.add_argument("--cas", choices=["1", "2", "3", "4"], help="按中科院分区过滤（1–4 区）")
    ap.add_argument("--jcr", choices=["Q1", "Q2", "Q3", "Q4"], help="按 JCR 2025 分区过滤")
    ap.add_argument("--lang", choices=["zh", "en"], help="按语种过滤：zh=中文；en=非中文（多为英文）")
    ap.add_argument("--pku", choices=["1"], help="仅列出北大核心 2023 收录刊")
    ap.add_argument("--cscd", choices=["core", "ext"], help="按 CSCD 库别过滤：core=核心库；ext=扩展库")
    ap.add_argument("--ei", choices=["1"], help="仅列出 EI 2026 收录刊")
    ap.add_argument("--country", help="按出版国家/地区过滤（模糊匹配）")
    ap.add_argument("--json", action="store_true", help="输出 JSON 数组")
    ap.add_argument("--limit", type=int, default=10, help="返回条数上限")
    args = ap.parse_args()

    if args.similar is not None:
        conn = get_conn()
        try:
            recs = recommend_by_category(conn, args.similar, limit=args.limit)
        finally:
            conn.close()
        if args.json:
            print(json.dumps(recs, ensure_ascii=False, indent=2))
        else:
            if not recs:
                print("无同学科领域推荐。")
            else:
                for r in recs:
                    print(f"- {r['title']}（{r['issn_print']}）[{r['subject_area']}]")
        return

    has_facet = any(getattr(args, k) is not None for k in
                    ("area", "subfield", "tier", "cas", "jcr", "lang", "country", "pku", "cscd", "ei"))
    if not args.keyword and not args.issn and not has_facet:
        ap.error("请提供 keyword 或 --issn，或用 --similar <id> 获取相似期刊推荐")

    results = search(
        args.keyword or "", issn=args.issn, limit=args.limit,
        area=args.area, subfield=args.subfield, tier=args.tier,
        cas=args.cas, jcr=args.jcr, lang=args.lang, country=args.country,
        pku=args.pku, cscd=args.cscd, ei=args.ei,
    )

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print(render_text(results))
        if has_facet:
            print(f"\n[共命中 {len(results)} 本，已应用多面过滤]")


def main() -> None:
    """入口：捕获数据库类异常，按 SKILL.md 约定输出友好降级提示。"""
    # 先解析出是否 --json，保证降级提示与用户期望的输出格式一致
    as_json = "--json" in sys.argv
    try:
        _run()
    except SchemaError as exc:
        #  结构断言失败（如缺失 ratings / journal_disciplines 表）：
        # 属「库文件存在但结构不完整」，同样走降级话术而非裸 traceback。
        _emit_degrade(
            as_json,
            f"数据库结构不完整：{str(exc).rstrip('。')}。请重新获取完整的 "
            "skills/journal-library/db/journals.db，或运行迁移脚本补齐评级/学科数据后重试。",
        )
    except sqlite3.OperationalError as exc:
        _emit_degrade(as_json, _degrade_message(exc))
    except sqlite3.DatabaseError as exc:
        _emit_degrade(as_json, f"数据库文件异常：{exc}。请重新获取完整的 skills/journal-library/db/journals.db。")


if __name__ == "__main__":
    main()
