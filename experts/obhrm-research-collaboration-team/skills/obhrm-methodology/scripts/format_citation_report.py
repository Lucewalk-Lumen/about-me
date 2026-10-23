#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""引证验证报告生成工具（离线，不联网）。

本套件脚本不联网，不再内置联网核验脚本：DOI 的 CrossRef 核验数据由 agent
通过平台内置 WebFetch 工具预先获取（`https://api.crossref.org/works/<doi>`），
整理为 JSON 传入本脚本；本脚本只做**DOI 提取、引用解析、三态标注与报告生成**，
本脚本为纯离线处理（DOI 提取、引用解析、三态标注与报告生成）。

功能：
  1. 从草稿中提取所有 DOI（10.xxxx/xxx 格式）
  2. 对照预抓取的 CrossRef 验证结果 JSON，判定三态：已核实 / 不存在 / 无法核实
  3. 比对草稿中的引用信息（作者/年份）与 CrossRef 元数据
  4. 可选：比对 READINGS.md 中的文献列表，做证据链三态标注
     （已核实DOI / 未获取原文 / 未证实归属）

CrossRef 验证结果 JSON 格式（--crossref）
----------------------------------------
一个对象，键为 DOI（小写或原样均可），值三选一：
    "10.1234/abc": {"message": { ...CrossRef works 响应的 message 字段... }}   → 已核实
    "10.9999/xxx": {"status": "not_found"}                                    → 确认不存在
    "10.5555/yyy": {"error": "timeout"}                                       → 无法核实
    "10.7777/zzz": null                                                       → 无法核实（未抓取）

用法
----
    python format_citation_report.py <draft.md> \\
        --crossref crossref.json [--readings READINGS.md] [--out report.md]

退出码
------
    0  全部验证通过
    1  发现验证失败或警告
    2  输入文件错误
"""

import argparse
import json
import os
import re
import sys
import datetime

# --out 输出路径需落在允许范围内
# 技能根目录（scripts/ 的上级）加入 sys.path，使套件包可导入
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from obhrm_research_base.core.safe_path import resolve_safe_output  # noqa: E402


def extract_dois(text):
    """从文本中提取所有 DOI（标准格式 10.xxxx/xxx）。"""
    # DOI 正则：10. 开头，后跟注册机构代码/后缀
    pattern = r'\b(10\.\d{4,9}/[-._;()/:a-zA-Z0-9]+)'
    matches = re.findall(pattern, text)
    # 清理末尾标点
    cleaned = []
    for m in matches:
        m = m.rstrip('.,;)')
        cleaned.append(m)
    return list(set(cleaned))  # 去重


def extract_citations(text):
    """从文本中提取 in-text 引用。

    覆盖四类形态：
      A 英文括号式  (Wang, 2020) / (Wang & Li, 2020) / (Wang et al., 2020)
      B 中文括号式  （王某，2020）
      C 叙述式·中文作者  王某等（2020） / 王某 等 (2020)
      D 叙述式·拉丁作者  Wang 等（2023） / Wang et al. (2023) / Wang & Li (2023)

    返回的每条形如 {"raw": ..., "author": ..., "year": ...}，按出现位置去重
    （同一片文本被多条正则命中时只保留最长的一条）。
    """
    hits = []  # (start, end, dict)

    # A 英文括号式：(Author, Year) / (Author & Author, Year) / (Author et al., Year)
    pattern_en = r'\(([A-Z][a-z]+(?:\s+(?:&|and|et al\.?)\s+[A-Z]?[a-z]*(?:,\s*)?)+,\s*(\d{4}[a-z]?))\)'
    for m in re.finditer(pattern_en, text):
        hits.append((m.start(), m.end(), {"raw": m.group(0), "year": m.group(2)}))

    # B 中文括号式：（作者，年份）
    pattern_zh = r'[（(]([^）)]+?)[,，]\s*(\d{4})[）)]'
    for m in re.finditer(pattern_zh, text):
        hits.append((m.start(), m.end(),
                     {"raw": m.group(0), "author": m.group(1).strip(), "year": m.group(2)}))

    # C 叙述式·中文作者：王某等（2020） / 王某 等 (2020) / 王某（2020）
    pattern_zh2 = r'([\u4e00-\u9fa5]{2,4})\s*(?:等人|等|和[\u4e00-\u9fa5]{2,4})?\s*[（(]\s*(\d{4}[a-z]?)\s*[）)]'
    for m in re.finditer(pattern_zh2, text):
        hits.append((m.start(), m.end(),
                     {"raw": m.group(0), "author": m.group(1), "year": m.group(2)}))

    # D 叙述式·拉丁作者（必须带合著标记，防误报）：
    #    Wang 等（2023） / Wang et al. (2023) / Wang and Li (2023) / Wang & Li (2023)
    pattern_latin = (
        r"([A-Z][A-Za-z\u00C0-\u024F\-']+)"                       # 姓
        r"\s*(?:等人|等|et\s*al\.?"                                # 合著标记
        r"|[&和]\s*[A-Z\u4e00-\u9fa5][A-Za-z\u4e00-\u9fa5\-']+"
        r"|and\s+[A-Z][A-Za-z\-']+)"
        r"\s*[（(]\s*(\d{4}[a-z]?)\s*[）)]"                        # 年份（全/半角括号皆可）
    )
    for m in re.finditer(pattern_latin, text):
        hits.append((m.start(), m.end(),
                     {"raw": m.group(0), "author": m.group(1), "year": m.group(2)}))

    # 去重：同一处文本被多条正则命中时，保留跨度最长的一条
    hits.sort(key=lambda h: (h[0], -(h[1] - h[0])))
    citations = []
    covered_end = -1
    for start, end, cite in hits:
        if start < covered_end:
            continue
        citations.append(cite)
        covered_end = end
    return citations


def load_crossref_results(path):
    """读取预抓取的 CrossRef 验证结果 JSON，归一化为 {doi_norm: record}。

    record 归一化后形如：
        {"status": "valid"|"invalid"|"unverified", "title":..., "authors":[...],
         "year":..., "journal":..., "error": ...}
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("crossref JSON 必须是 {doi: record} 对象")

    normalized = {}
    for doi, rec in data.items():
        key = doi.strip().lower()
        if rec is None:
            normalized[key] = {"status": "unverified", "title": "", "authors": [],
                               "year": "", "journal": "", "error": "未抓取"}
            continue
        if not isinstance(rec, dict):
            normalized[key] = {"status": "unverified", "title": "", "authors": [],
                               "year": "", "journal": "", "error": "记录格式不识别"}
            continue
        msg = rec.get("message")
        status = (rec.get("status") or "").lower()
        if isinstance(msg, dict) and msg:
            authors = []
            for a in msg.get("author", []):
                name = f"{a.get('family', '')} {a.get('given', '')}".strip()
                if name:
                    authors.append(name)
            year = ""
            published = msg.get("published-print") or msg.get("published-online") or msg.get("created")
            if published and "date-parts" in published:
                parts = published["date-parts"][0]
                if parts:
                    year = str(parts[0])
            normalized[key] = {
                "status": "valid",
                "title": msg.get("title", [""])[0] if msg.get("title") else "",
                "authors": authors,
                "year": year,
                "journal": msg.get("container-title", [""])[0] if msg.get("container-title") else "",
                "error": None,
            }
        elif status in ("not_found", "invalid") or "404" in str(rec.get("error", "")):
            normalized[key] = {"status": "invalid", "title": "", "authors": [],
                               "year": "", "journal": "",
                               "error": f"DOI 不存在 (404): {key}"}
        else:
            err = rec.get("error") or rec.get("status") or "无有效数据"
            normalized[key] = {"status": "unverified", "title": "", "authors": [],
                              "year": "", "journal": "", "error": f"无法核实（{err}）: {key}"}
    return normalized


def parse_readings(readings_path):
    """从 READINGS.md 中提取已读文献列表。"""
    try:
        with open(readings_path, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        return []

    # 匹配 READINGS.md 中的文献条目（通常是 ## 标题 或 - 列表项）
    # 一篇文献对应一条记录，DOI 作为该条目的字段挂上去；
    # READINGS 里出现但没归到任何条目名下的游离 DOI，另作 doi-only 条目补录，
    # 保证下游 `readings_dois` 集合语义不变。
    entries = []
    claimed_dois = set()
    doi_re = re.compile(r'(10\.\d{4,9}/[-._;()/:a-zA-Z0-9]+)')

    matches = list(re.finditer(
        r'(?:##\s+|-\s+\*\*)(.+?)(?:\*\*)?(?:\s*[（(](\d{4})[）)])?\s*\n', content))
    for i, m in enumerate(matches):
        # 该条目的正文范围 = 本次匹配结束 → 下一条目开始
        seg_end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        segment = content[m.end():seg_end]
        dois = doi_re.findall(segment)
        claimed_dois.update(dois)
        entries.append({
            "title": m.group(1).strip(),
            "year": m.group(2) or "",
            "doi": dois[0] if dois else "",
            "dois": dois,
        })

    # 游离 DOI（不在任何条目段落内，例如文件头部的汇总表）
    for m in doi_re.finditer(content):
        if m.group(1) not in claimed_dois:
            claimed_dois.add(m.group(1))
            entries.append({"doi": m.group(1), "dois": [m.group(1)]})

    return entries


def read_readings_blocks(readings_path):
    """把 READINGS.md 切成「一篇文献 = 一个文本块」，供三态归属匹配（纯离线）。

    按条目块匹配（关键）：若按**单行**匹配「作者 token + 年份」，READINGS 的
    标准写法把作者与年份分列两行（`- 作者: ...` / `- 年份: ...`），于是没有任何
    一行同时含两者——真实存在的文献也会被判成「未证实归属」，报告一片红。
    这种 100% 假阳性比不检查更糟：用户会学会忽略这个警告，编造引用就此穿过 G5。
    改为按条目块匹配后，只有块内同时出现作者与年份才算命中。

    切块规则：遇到 Markdown 标题（#/##/###）或加粗列表项（- **）即开新块；
    标题前的序言归入第 0 块（通常是文件头，命中概率低，无害）。
    """
    if not readings_path:
        return []
    try:
        with open(readings_path, "r", encoding="utf-8") as f:
            raw = f.read()
    except FileNotFoundError:
        return []

    boundary = re.compile(r'^(?:#{1,6}\s+|-\s+\*\*)')
    blocks, cur = [], []
    for line in raw.splitlines():
        if boundary.match(line) and cur:
            blocks.append("\n".join(cur))
            cur = []
        cur.append(line)
    if cur:
        blocks.append("\n".join(cur))
    return [b for b in (b.strip() for b in blocks) if b]


def _cite_author_text(cite):
    """取引用中用于匹配的作者文本：优先 author 字段，否则用 raw。"""
    return cite.get("author") or cite.get("raw", "")


def _extract_name_tokens(text):
    """从引用/条目文本抽取姓名 token：中文名（2-4字）+ 英文姓（大写词）。"""
    zh = re.findall(r'[\u4e00-\u9fa5]{2,4}', text or "")
    en = [w.lower() for w in re.findall(r'[A-Z][a-zA-Z]+', text or "")
          if w.lower() not in ("et", "al", "and")]
    return zh + en


def _readings_line_has_verified_doi(line, verified_dois):
    """判断某条 READINGS 原始行是否含有一个已验证通过的 DOI。"""
    for m in re.finditer(r'(10\.\d{4,9}/[-._;()/:a-zA-Z0-9]+)', line):
        doi = m.group(1).rstrip('.,;)')
        if doi in verified_dois:
            return True
    return False


def classify_citation(cite, readings_units, verified_dois):
    """证据链三态判定，返回三态之一（纯离线）。

    - `已核实DOI`：能关联到一条 READINGS 条目，且该条目含已在 CrossRef 验证
      通过的 DOI。
    - `未获取原文`：READINGS 中有对应条目，但无（已验证）DOI。
    - `未证实归属`：草稿引用了，但 READINGS 中根本找不到对应文献（最高风险）。

    `readings_units` 为 `read_readings_blocks()` 产出的**条目块**；
    传入逐行列表亦可运行，但会产生较高的假阳性。
    DOI 验证结果由调用方以 verified_dois 集合传入，不额外发起网络请求。
    """
    year = cite.get("year", "")
    tokens = _extract_name_tokens(_cite_author_text(cite))
    if not readings_units or not tokens:
        return "未证实归属"

    matched = None
    for unit in readings_units:
        if year and year not in unit:
            continue
        low = unit.lower()
        if any((t in unit) or (t in low) for t in tokens):
            matched = unit
            break

    if matched is None:
        return "未证实归属"
    if _readings_line_has_verified_doi(matched, verified_dois):
        return "已核实DOI"
    return "未获取原文"


def main():

    parser = argparse.ArgumentParser(
        description="引证验证报告生成（离线：CrossRef 结果由 agent 经 WebFetch 预先获取后传入）")
    parser.add_argument("draft", help="草稿文件路径（Markdown 或纯文本）")
    parser.add_argument("--crossref", default=None,
                         help="CrossRef 验证结果 JSON 路径（{doi: record}；不提供则 DOI 均按无法核实处理）")
    parser.add_argument("--readings", default=None, help="已读文献清单 READINGS.md 路径")
    parser.add_argument("--out", default=None, help="报告输出路径（不指定则输出到stdout）")
    args = parser.parse_args()

    # 读取草稿
    try:
        with open(args.draft, "r", encoding="utf-8") as f:
            draft_text = f.read()
    except FileNotFoundError:
        print(f"错误：文件不存在 {args.draft}", file=sys.stderr)
        sys.exit(2)

    # 读取预抓取的 CrossRef 验证结果
    crossref_results = {}
    if args.crossref:
        try:
            crossref_results = load_crossref_results(args.crossref)
        except (OSError, ValueError, json.JSONDecodeError) as e:
            print(f"错误：读取 CrossRef 验证结果失败：{e}", file=sys.stderr)
            sys.exit(2)

    print("引证验证开始（离线模式：基于预抓取数据）...", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    # 提取 DOI
    dois = extract_dois(draft_text)
    print(f"\n提取到 {len(dois)} 个唯一 DOI", file=sys.stderr)

    # 提取引用
    citations = extract_citations(draft_text)
    print(f"提取到 {len(citations)} 个引用标注", file=sys.stderr)

    # 判定 DOI 三态（对照预抓取结果，无网络请求）
    doi_results = []
    if dois:
        print("\n判定 DOI 三态...", file=sys.stderr)
        for i, doi in enumerate(sorted(dois), 1):
            rec = crossref_results.get(doi.lower())
            if rec is None:
                r = {"valid": False, "status": "unverified", "title": "", "authors": [],
                     "year": "", "journal": "",
                     "error": f"未提供 CrossRef 数据（未执行 WebFetch 预抓取）: {doi}"}
            else:
                r = dict(rec)
                r["valid"] = (rec["status"] == "valid")
            r["doi"] = doi
            doi_results.append(r)
            if r["valid"]:
                print(f"  [{i}/{len(dois)}] {r['doi']}... [OK] {r['title'][:50]}", file=sys.stderr)
            elif r["status"] == "unverified":
                print(f"  [{i}/{len(dois)}] {r['doi']}... [!]  {r['error']}", file=sys.stderr)
            else:
                print(f"  [{i}/{len(dois)}] {r['doi']}... [X] {r['error']}", file=sys.stderr)

    # 比对 READINGS.md
    readings_entries = []
    readings_lines = []
    if args.readings:
        readings_entries = parse_readings(args.readings)
        readings_lines = read_readings_blocks(args.readings)
        print(f"\nREADINGS.md 中有 {len(readings_entries)} 条文献记录", file=sys.stderr)

    # 证据链三态标注（纯离线：基于 READINGS 匹配 + 已验证 DOI 集合）
    verified_dois = {r["doi"] for r in doi_results if r.get("valid")}
    tri_state = []
    for cite in citations:
        state = classify_citation(cite, readings_lines, verified_dois)
        tri_state.append({"cite": cite.get("raw", ""), "state": state})
    unattributed = [t for t in tri_state if t["state"] == "未证实归属"]

    # 生成报告
    report_lines = ["# 引证验证报告", ""]
    report_lines.append(f"验证时间：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
    report_lines.append(f"草稿文件：{args.draft}")
    report_lines.append("数据来源：CrossRef 验证结果由 agent 预先获取（离线整理，未发起网络请求）")
    report_lines.append("")

    # 顶部醒目区块：未证实归属（最高风险，强制置顶）
    report_lines.append("##  最高风险：未证实归属引用（需立即核实）")
    report_lines.append("")
    if unattributed:
        report_lines.append(f"> 以下 **{len(unattributed)}** 条引用在 READINGS 中找不到对应文献，"
                            "存在编造/张冠李戴风险，必须优先人工核实：")
        report_lines.append("")
        for t in unattributed:
            report_lines.append(f"-  `{t['cite']}` → **未证实归属**")
    else:
        report_lines.append("> [OK] 未发现「未证实归属」引用。")
    report_lines.append("")

    # 证据链三态标注明细
    report_lines.append("## 证据链三态标注")
    report_lines.append("")
    if not tri_state:
        report_lines.append("草稿中未检测到 in-text 引用。")
    else:
        report_lines.append("| # | 引用 | 三态标注 |")
        report_lines.append("|---|------|----------|")
        _icon = {"已核实DOI": "[OK] 已核实DOI",
                 "未获取原文": "[!] 未获取原文",
                 "未证实归属": " 未证实归属"}
        for i, t in enumerate(tri_state, 1):
            report_lines.append(f"| {i} | {t['cite']} | {_icon.get(t['state'], t['state'])} |")
        n_verified = sum(1 for t in tri_state if t["state"] == "已核实DOI")
        n_notext = sum(1 for t in tri_state if t["state"] == "未获取原文")
        report_lines.append("")
        report_lines.append(f"**三态统计**：已核实DOI {n_verified} / 未获取原文 {n_notext} / "
                            f"未证实归属 {len(unattributed)} / 共 {len(tri_state)} 条")
    report_lines.append("")

    # DOI 验证结果
    report_lines.append("## DOI 验证结果")
    report_lines.append("")
    if not doi_results:
        report_lines.append("草稿中未检测到 DOI。")
    else:
        report_lines.append("| # | DOI | 状态 | 标题 | 作者 | 年份 |")
        report_lines.append("|---|-----|------|------|------|------|")
        for i, r in enumerate(doi_results, 1):
            # 三态：已核实 / 不存在(404) / 无法核实(未抓取/抓取失败)
            if r["status"] == "valid":
                status = "[OK] 已核实"
            elif r["status"] == "unverified":
                status = "[!] 无法核实"
            else:
                status = "[X] 不存在"
            title = r.get("title", "")[:40] if r["valid"] else r.get("error", "")[:40]
            authors = ", ".join(r.get("authors", [])[:2]) if r["valid"] else "-"
            year = r.get("year", "-") if r["valid"] else "-"
            report_lines.append(f"| {i} | {r['doi']} | {status} | {title} | {authors} | {year} |")

    # 统计（三态分别计数，避免把「无法核实」误判为「不存在」）
    valid_count = sum(1 for r in doi_results if r["status"] == "valid")
    invalid_count = sum(1 for r in doi_results if r["status"] == "invalid")
    unverified_count = sum(1 for r in doi_results if r["status"] == "unverified")
    report_lines.append("")
    report_lines.append(
        f"**DOI 验证统计**：{valid_count} 已核实 / {invalid_count} 不存在 / "
        f"{unverified_count} 无法核实 / 共 {len(doi_results)} 个"
    )

    # 引用统计
    report_lines.append("")
    report_lines.append("## 引用标注统计")
    report_lines.append(f"- 检测到 {len(citations)} 个引用标注")
    report_lines.append(f"- 其中 {len(dois)} 个有 DOI（可经预抓取数据自动验证）")
    report_lines.append(f"- {len(citations) - len(dois)} 个仅有作者+年份（需人工核实）")

    # READINGS.md 比对
    if readings_entries:
        report_lines.append("")
        report_lines.append("## READINGS.md 比对")
        report_lines.append(f"- 已读文献清单中有 {len(readings_entries)} 条记录")
        readings_dois = {d for e in readings_entries for d in e.get("dois", []) if d}
        draft_dois = set(dois)
        unmatched = draft_dois - readings_dois
        if unmatched:
            report_lines.append(f"- [!] 草稿中有 {len(unmatched)} 个 DOI 不在 READINGS.md 中：")
            for d in unmatched:
                report_lines.append(f"  - {d}")
        else:
            report_lines.append("- [OK] 所有 DOI 均在 READINGS.md 中有记录")

    # 结论
    report_lines.append("")
    report_lines.append("## 验证结论")
    if invalid_count == 0 and unverified_count == 0:
        report_lines.append("[OK] 所有 DOI 均已核实存在。")
    else:
        if invalid_count > 0:
            report_lines.append(f"[!] {invalid_count} 个 DOI 经 CrossRef 确认不存在，须立即修正引用。")
        if unverified_count > 0:
            report_lines.append(
                f"[!] {unverified_count} 个 DOI 未提供 CrossRef 数据或抓取失败，"
                f"非「不存在」，请用 WebFetch 补抓（https://api.crossref.org/works/<doi>）"
                f"后重跑，或人工复核。"
            )
    if len(citations) - len(dois) > 0:
        report_lines.append(f"[!] {len(citations) - len(dois)} 个引用无 DOI，建议补充 DOI 以便自动验证。")

    report = "\n".join(report_lines)

    if args.out:
        # 强制 范围校验，防止 --out 写出允许范围
        try:
            safe_out = str(resolve_safe_output(args.out, base=os.getcwd()))
        except ValueError as exc:
            print("错误(--out): %s" % exc, file=sys.stderr)
            sys.exit(2)
        with open(safe_out, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"\n报告已写入 {safe_out}", file=sys.stderr)
    else:
        print(report)

    # 未证实归属(编造/张冠李戴) 与 DOI 验证失败 同属高风险，均令退出码为 1，
    # 使自动化流程能据此拦截（与脚本 docstring「发现验证失败或警告 → 1」一致）。
    sys.exit(1 if (invalid_count > 0 or unattributed) else 0)


if __name__ == "__main__":
    main()
