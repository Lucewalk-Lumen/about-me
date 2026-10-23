#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""学术文献检索结果整理工具（离线，不联网）。

本套件脚本不联网，不再内置联网检索脚本：检索数据由 agent 通过平台内置
WebSearch / WebFetch 工具获取（CrossRef / Semantic Scholar / PubMed / arXiv 等），
交给本脚本整理输出；本脚本只做**去重、排序与格式化输出**的纯离线处理
（去重逻辑、排序逻辑与输出格式均在本脚本内自洽实现）。

支持的输出格式：
    json    — JSON 格式（默认，附带 dedup_stats）
    bibtex  — BibTeX 格式（用于 LaTeX）
    apa     — APA 7th 引用格式
    mla     — MLA 引用格式
    chicago — Chicago 引用格式

输入格式
--------
`--input` 指向一个 JSON 文件（或 `-` 读 stdin），二选一：
    1. 结果对象数组：[{"title":..., "authors":[...], "year":..., "journal":...,
       "doi":..., "url":..., "citations":..., "_source":...}, ...]
    2. 包装对象：{"results": [ ...同上... ]}

字段尽量宽松：缺 authors/journal/doi/url/citations 均可，仅 title 建议提供。
`_source` 用于跨库来源合并展示，缺省按 "input" 处理。

用法
----
    python format_search_results.py --input raw.json --query "transformational leadership" \\
        --format apa --rank relevance -o results.txt

退出码
------
    0  处理成功（可能结果为空）
    1  输入错误
"""


# 确保套件包可导入（包目录在上级目录）
import os, sys
_skill_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _skill_dir not in sys.path:
    sys.path.append(_skill_dir)
import argparse
import hashlib
import json
import os
import sys
from datetime import datetime

try:
    from obhrm_research_base.core.safe_path import resolve_safe_output, safe_open_for_write
    _HAVE_SAFE_PATH = True
except ImportError:
    _HAVE_SAFE_PATH = False


# ---------------------------------------------------------------------------
# 输入载入
# ---------------------------------------------------------------------------

def load_results(path):
    """读取 JSON 输入（文件或 stdin），返回结果列表。

    兼容三种形态：裸数组 / {"results": [...]} / 单对象（按 1 条处理）。
    """
    if path == "-":
        raw = sys.stdin.read()
    else:
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read()
    data = json.loads(raw)
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and isinstance(data.get("results"), list):
        return data["results"]
    if isinstance(data, dict):
        return [data]
    raise ValueError("输入 JSON 既不是数组也不是对象")


def filter_year(results, year_range):
    """按年份范围本地过滤（year 形如 "2021" 或 "2021-05"）。"""
    if not year_range:
        return results
    start, end = year_range
    kept = []
    for r in results:
        y = str(r.get("year", "")).strip()[:4]
        if not y.isdigit():
            kept.append(r)  # 无年份不过滤，交由人工判断
            continue
        yi = int(y)
        if start <= yi <= end:
            kept.append(r)
    return kept


# ---------------------------------------------------------------------------
# 输出格式化
# ---------------------------------------------------------------------------

def format_json(results):
    return json.dumps(results, ensure_ascii=False, indent=2)


def format_bibtex(results):
    lines = []
    for r in results:
        key = ""
        if r["authors"]:
            last = r["authors"][0].split()[-1].lower()
            key = f"{last}{r['year']}"
        else:
            key = f"untitled{r['year']}"
        entry_type = "article" if r.get("journal") else "misc"
        lines.append(f"@{entry_type}{{{key},")
        lines.append(f"  title = {{{r['title']}}},")
        if r["authors"]:
            lines.append(f"  author = {{{' and '.join(r['authors'])}}},")
        lines.append(f"  year = {{{r['year']}}},")
        if r.get("journal"):
            lines.append(f"  journal = {{{r['journal']}}},")
        if r.get("doi"):
            lines.append(f"  doi = {{{r['doi']}}},")
        if r.get("url"):
            lines.append(f"  url = {{{r['url']}}},")
        lines.append("}")
        lines.append("")
    return "\n".join(lines)


def format_apa(results):
    lines = []
    for r in results:
        authors = r["authors"]
        if len(authors) >= 3:
            auth_str = f"{authors[0]} et al."
        elif len(authors) == 2:
            auth_str = " & ".join(authors)
        elif len(authors) == 1:
            auth_str = authors[0]
        else:
            auth_str = "Unknown"

        doi_str = f" doi:{r['doi']}" if r.get("doi") else ""
        lines.append(f"{auth_str} ({r['year']}). {r['title']}. {r.get('journal', '')}.{doi_str}")
    return "\n\n".join(lines)


def format_mla(results):
    lines = []
    for r in results:
        authors = r["authors"]
        if authors:
            auth_str = authors[0]
            if len(authors) > 1:
                auth_str += ", et al"
        else:
            auth_str = "Unknown"

        lines.append(f'{auth_str}. "{r["title"]}." {r.get("journal", "")}, {r["year"]}.')
    return "\n\n".join(lines)


def format_chicago(results):
    lines = []
    for r in results:
        authors = r["authors"]
        if len(authors) <= 3:
            auth_str = ", ".join(authors)
        else:
            auth_str = f"{authors[0]} et al."

        lines.append(f'{auth_str}. "{r["title"]}." {r.get("journal", "")}, {r["year"]}.')
    return "\n\n".join(lines)


FORMATTERS = {
    "json": format_json,
    "bibtex": format_bibtex,
    "apa": format_apa,
    "mla": format_mla,
    "chicago": format_chicago,
}


# ---------------------------------------------------------------------------
# 跨库去重与排序
# ---------------------------------------------------------------------------

def _norm_title(title):
    """标题归一化：小写 + 去标点 + 压空格。"""
    import re as _re
    t = (title or "").lower()
    t = _re.sub(r"[^\w\s]", " ", t, flags=_re.UNICODE)
    t = _re.sub(r"\s+", " ", t).strip()
    return t


def _first_author_surname(authors):
    """取首作者姓，归一化小写；无作者返回空串。

    兼容两种常见格式：
      - "Family, Given"（含逗号，姓在逗号前）
      - "Given Family" / "Family Given"（无逗号，取末段作为启发式姓）
    """
    if not authors:
        return ""
    first = authors[0].strip()
    if not first:
        return ""
    import re as _re
    if "," in first:
        surname = first.split(",")[0].strip()
    else:
        parts = [p for p in _re.split(r"\s+", first) if p]
        surname = parts[-1] if parts else first
    return _re.sub(r"[^\w]", "", surname, flags=_re.UNICODE).lower()


def _dedup_key(r):
    """生成去重键：有 DOI 用 DOI；否则用 (标题归一化, 首作者姓, 年份) 三元组。"""
    doi = (r.get("doi") or "").strip().lower()
    if doi:
        return ("doi", doi)
    return ("meta", _norm_title(r.get("title", "")),
            _first_author_surname(r.get("authors", [])),
            str(r.get("year", "")).strip())


def dedup_results(results):
    """跨库去重。

    - 按 DOI 优先去重；无 DOI 时按「标题归一化 + 首作者姓 + 年份」三元组去重。
    - 合并重复项：保留 citations 最大值；来源合并为 `sources: [...]` 列表。

    Returns:
        List[dict]: 去重后的结果列表（保留首次出现顺序）。
    """
    merged = {}
    order = []
    for r in results:
        key = _dedup_key(r)
        src = r.get("_source", "")
        if key not in merged:
            item = dict(r)
            item["sources"] = [src] if src else []
            merged[key] = item
            order.append(key)
        else:
            item = merged[key]
            # 保留 citations 最大值
            if r.get("citations", 0) > item.get("citations", 0):
                item["citations"] = r.get("citations", 0)
            # 合并来源
            if src and src not in item["sources"]:
                item["sources"].append(src)
    return [merged[k] for k in order]


def rank_results(results, mode="citations"):
    """按指定模式排序。

    - citations（默认，向后兼容）：按 citations 降序。
    - relevance：计算加权综合分 score 并写入每条结果，按 score 降序。
      score = 归一化引用数*0.5 + 年份新近度*0.3 + 标题/查询词命中率*0.2。
    """
    if mode != "relevance":
        results.sort(key=lambda x: x.get("citations", 0), reverse=True)
        return results
    # relevance 模式：score 已在 compute_scores 内计算完毕
    results.sort(key=lambda x: x.get("score", 0.0), reverse=True)
    return results


def compute_scores(results, query):
    """为 relevance 模式计算每条结果的加权综合分 score（原地写入）。

    score = 归一化引用数*0.5 + 年份新近度*0.3 + 标题命中率*0.2
    - 归一化引用数：citations / max_citations（max 为 0 时取 0）。
    - 年份新近度：(year - min_year) / (max_year - min_year)，无年份按 0。
    - 标题命中率：查询词在标题中命中的比例。
    """
    if not results:
        return results

    max_cite = max((r.get("citations", 0) or 0) for r in results)

    years = []
    for r in results:
        y = str(r.get("year", "")).strip()
        if y.isdigit():
            years.append(int(y))
    min_year = min(years) if years else 0
    max_year = max(years) if years else 0
    year_span = (max_year - min_year) if max_year > min_year else 0

    query_terms = [t for t in _norm_title(query).split() if t]

    for r in results:
        cite = r.get("citations", 0) or 0
        cite_norm = (cite / max_cite) if max_cite else 0.0

        y = str(r.get("year", "")).strip()
        if y.isdigit() and year_span:
            year_recency = (int(y) - min_year) / year_span
        else:
            year_recency = 0.0

        if query_terms:
            title_words = set(_norm_title(r.get("title", "")).split())
            hits = sum(1 for t in query_terms if t in title_words)
            title_hit = hits / len(query_terms)
        else:
            title_hit = 0.0

        r["score"] = round(cite_norm * 0.5 + year_recency * 0.3 + title_hit * 0.2, 4)
    return results


# ---------------------------------------------------------------------------
# 检索留痕（可选，默认关闭；纯本地写文件，不联网）
# ---------------------------------------------------------------------------

def _write_readonly_json(path, payload):
    """将 payload 以 JSON 写入 path（使用默认文件权限）。"""
    with safe_open_for_write(path, base=os.getcwd(), encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def save_search_trace(save_dir, query, raw_results, dedup_stats, rank):
    """把去重前的原始检索结果落为只读快照，并记录/追加检索日志。

    - raw_<时间戳>_<query哈希>.json：去重前 raw 结果，写后设为只读（raw 源不可变）。
    - search_log.json：追加一条记录，含 query/raw_count/deduped_count/rank/timestamp。
    """
    os.makedirs(save_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    query_hash = hashlib.sha1((query or "").encode("utf-8")).hexdigest()[:8]

    raw_filename = f"raw_{timestamp}_{query_hash}.json"
    raw_path = os.path.join(save_dir, raw_filename)
    _write_readonly_json(raw_path, {
        "query": query or "",
        "timestamp": timestamp,
        "raw_count": dedup_stats.get("raw", len(raw_results)),
        "results": raw_results,
    })

    log_entry = {
        "query": query or "",
        "raw_count": dedup_stats.get("raw", len(raw_results)),
        "deduped_count": dedup_stats.get("deduped", 0),
        "rank": rank,
        "timestamp": timestamp,
        "raw_file": raw_filename,
    }

    log_path = os.path.join(save_dir, "search_log.json")
    log_data = []
    if os.path.exists(log_path):
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
            if isinstance(existing, list):
                log_data = existing
        except (OSError, json.JSONDecodeError):
            log_data = []
    log_data.append(log_entry)
    _write_readonly_json(log_path, log_data)

    print(f"  检索留痕已保存：{raw_path}", file=sys.stderr)
    return raw_path, log_path


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def parse_year_range(s):
    if not s:
        return None
    if "-" in s:
        parts = s.split("-")
        return (int(parts[0]), int(parts[1]))
    year = int(s)
    return (year, datetime.now().year)


def main():
    parser = argparse.ArgumentParser(
        description="学术文献检索结果整理（离线：去重 / 排序 / 格式化；检索数据由 agent 经 WebSearch/WebFetch 预先获取）"
    )
    parser.add_argument("--input", default="-", metavar="FILE",
                        help="检索结果 JSON 文件（默认 '-' 读 stdin）")
    parser.add_argument("--query", default="",
                        help="原检索式（用于 relevance 打分与留痕）")
    parser.add_argument("--year", default=None,
                        help="年份范围过滤（本地），如 2020-2026 或 2024")
    parser.add_argument("--limit", type=int, default=100,
                        help="输出条数上限（默认100）")
    parser.add_argument("--format", default="json",
                        choices=["json", "bibtex", "apa", "mla", "chicago"],
                        help="输出格式（默认json）")
    parser.add_argument("--rank", default="citations",
                        choices=["relevance", "citations"],
                        help="排序方式：citations（默认，按引用数）或 relevance（加权综合分）")
    parser.add_argument("-o", "--output", default=None,
                        help="输出文件路径（不指定则输出到stdout）")
    parser.add_argument("--save-raw", default=None, metavar="DIR",
                        help="检索留痕目录（默认不启用）：保存去重前的只读 raw 快照与 search_log.json")
    args = parser.parse_args()

    try:
        raw_results = load_results(args.input)
    except (OSError, ValueError, json.JSONDecodeError) as e:
        print(f"  [ERROR] 读取输入失败：{e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(raw_results, list) or not all(isinstance(r, dict) for r in raw_results):
        print("  [ERROR] 输入必须是结果对象数组（或 {\"results\": [...]}）", file=sys.stderr)
        sys.exit(1)

    # 年份本地过滤
    year_range = parse_year_range(args.year)
    if year_range:
        before = len(raw_results)
        raw_results = filter_year(raw_results, year_range)
        print(f"  年份过滤 [{year_range[0]}-{year_range[1]}]：{before} → {len(raw_results)} 条", file=sys.stderr)

    # 跨库去重
    raw_count = len(raw_results)
    results = dedup_results(raw_results)
    dedup_stats = {"raw": raw_count, "deduped": len(results)}
    print(f"  去重：{raw_count} → {len(results)} 条", file=sys.stderr)

    # 检索留痕（仅在显式提供 --save-raw 时启用）
    if args.save_raw:
        if not _HAVE_SAFE_PATH:
            print("  错误：路径校验模块(safe_path)不可用，拒绝写出。", file=sys.stderr)
            sys.exit(1)
        try:
            safe_save_raw = resolve_safe_output(args.save_raw, base=os.getcwd())
        except ValueError as e:
            print(f"  错误(--save-raw)：{e}", file=sys.stderr)
            sys.exit(1)
        save_search_trace(str(safe_save_raw), args.query, raw_results,
                          dedup_stats, args.rank)

    # 排序（relevance 模式先计算 score）
    if args.rank == "relevance":
        compute_scores(results, args.query)
    results = rank_results(results, args.rank)

    # 输出上限
    limit = max(1, min(1000, args.limit))
    results = results[:limit]

    # 格式化输出
    if args.format == "json":
        # JSON 输出附带 dedup_stats（结构化，便于下游读取）
        output = json.dumps(
            {"dedup_stats": dedup_stats, "results": results},
            ensure_ascii=False, indent=2)
    else:
        formatter = FORMATTERS.get(args.format)
        output = formatter(results)

    if args.output:
        if not _HAVE_SAFE_PATH:
            # 路径校验模块不可用：拒绝写出，避免在缺少范围校验的情况下落盘
            print("  错误：路径校验模块(safe_path)不可用，拒绝写出。", file=sys.stderr)
            sys.exit(1)
        try:
            safe_output = resolve_safe_output(args.output, base=os.getcwd())
        except ValueError as e:
            print(f"  错误：{e}", file=sys.stderr)
            sys.exit(1)
        with open(str(safe_output), "w", encoding="utf-8") as f:
            f.write(output)
        print(f"  结果已写入 {safe_output}（{len(results)} 条）", file=sys.stderr)
    else:
        print(output)

    print(f"\n整理完成：共 {len(results)} 条结果（raw {raw_count} 条，去重后 {dedup_stats['deduped']} 条）", file=sys.stderr)


if __name__ == "__main__":
    main()
