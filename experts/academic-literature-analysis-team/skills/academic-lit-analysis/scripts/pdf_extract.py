#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PDF 全文提取：把 PDF 文本回填到题录的摘要/关键词字段。

## 为什么需要

本包的分析全部依赖题录字段（标题/摘要/关键词）。实测发现两类缺口：

    · 摘要缺失 → 主题聚类退化为只看标题，边界不准
    · 关键词缺失 → 共现网络直接少一批节点

而PDF 里往往就有这两项（首页的 Abstract、Keywords）。补上它们等于
**在不联网、不换数据源的前提下提升数据质量**——这是本包"只读离线"
定位下唯一可行的补救路径。

## PDF 从哪来（按优先级自动定位）

    1. 题录自带的 `pdf_path`（本地题录库解析出的附件路径）
    2. `--pdf-dir` 指定的目录，按**标题模糊匹配**文件名
    3. `--pdf-dir` 下的全部 PDF，按题录顺序对号入座（兜底，会警告）

## 依赖策略

`pypdf` 是**可选依赖**：
    · 已装 → 正常提取
    · 未装 → **不报错**，产出"待安装"清单并给出指引，主流程照常可跑

这是本包的一贯原则：可选能力缺失只降级、不阻断（与 R/igraph 一致）。

## 输出

`pdf_text.json`：
    · `records`：每条含 id / pdf 路径 / 提取到的 abstract / keywords / 字符数
    · `backfill`：可直接合并回题录的 {id: {abstract, keywords}}
报告可用 `--pdf-text` 读取，统计"经 PDF 补全"的字段数量。
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from lit_core import EXIT, load_refs  # noqa: E402

# ── PDF 里的摘要/关键词区段常见标记（中英文）──
_ABSTRACT_PAT = re.compile(
    r"(?:^|\n)\s*(?:abstract|摘\s*要|内容摘要|summary)\s*[:：.．]?\s*(.{80,2200}?)"
    r"(?=\n\s*(?:keywords?|key\s*words|关键词|引言|introduction|1\s*[.．、])"
    r"|\n\s*ABSTRACT\b|\n\s*摘要[:：]|\Z)",
    re.IGNORECASE | re.DOTALL,
)
_KEYWORDS_PAT = re.compile(
    r"(?:^|\n)\s*(?:keywords?|key\s*words|关键词)\s*[:：.．]?\s*(.{3,400}?)"
    r"(?=\n\s*(?:abstract|摘要|引言|introduction|1\s*[.．、])|\Z)",
    re.IGNORECASE | re.DOTALL,
)
# PDF 抽文本常见噪声：断行连字、多余空白、页眉页脚残留
_NOISE_PAT = re.compile(r"[\u00ad\u00a0]|-\n(?=[a-z])|(?<=[a-z])\n(?=[a-z])")
_WS_PAT = re.compile(r"[ \t　]+")


def _pdf_text(path: Path, pages: int = 40) -> tuple[str, str | None]:
    """返回 (文本, 错误信息)。缺依赖时给出明确指引而非抛异常。

    引擎优先级：**PyMuPDF → pypdf**。
    [!] 实测 pypdf 读中文 PDF 会乱码（CID 字体无 ToUnicode 映射时，
    抽出来是「錜e皥LN:」这类天书），PyMuPDF 处理正确得多。
    两个都没有时才算"缺依赖"。
    """
    # ① PyMuPDF：中文 PDF 的首选
    try:
        import pymupdf                      # noqa: PLC0415
        doc = pymupdf.open(str(path))
        try:
            n = min(pages, doc.page_count)
            txt = "\n".join(doc[i].get_text() for i in range(n))
        finally:
            doc.close()
        if txt.strip():
            return txt, None
    except ImportError:
        pass
    except Exception:                        # noqa: BLE001
        pass                                # 引擎异常则退回 pypdf
    # ② pypdf：作为备选（纯英文 PDF 表现良好）
    try:
        from pypdf import PdfReader
    except ImportError:
        return "", ("PDF 提取需要 PyMuPDF 或 pypdf。PDF 提取为可选能力，"
                    "不影响主分析。安装：pip install pymupdf（或 pip install pypdf）")
    try:
        r = PdfReader(str(path))
        parts = [pg.extract_text() or "" for pg in r.pages[:pages]]
        return "\n".join(parts), None
    except Exception as e:  # noqa: BLE001
        return "", f"解析失败: {str(e)[:80]}"


def _clean(s: str) -> str:
    s = _NOISE_PAT.sub("", s)
    s = _WS_PAT.sub(" ", s)
    return re.sub(r"\n{2,}", "\n", s).strip()


def _parse_fields(text: str) -> tuple[str, list[str]]:
    """从 PDF 文本里抽摘要与关键词。抽不到就返回空，由调用方决定回填策略。"""
    ab = _ABSTRACT_PAT.search(text)
    abstract = _clean(ab.group(1)) if ab else ""
    # 摘要里混入参考文献列表等噪声时截断
    if len(abstract) > 1200:
        cut = abstract.find("参考文献")
        if cut > 100:
            abstract = abstract[:cut]
        else:
            abstract = abstract[:1200]
    kw = _KEYWORDS_PAT.search(text)
    keywords = []
    if kw:
        raw = _clean(kw.group(1))
        keywords = [k.strip(" .。;；,，、") for k in re.split(r"[;；,，、]", raw)]
        keywords = [k for k in keywords if 1 < len(k) <= 40][:12]
    return abstract, keywords


def _index_pdfs(pdf_dir: Path) -> list[Path]:
    out = []
    for pat in ("*.pdf", "*.PDF"):
        out.extend(sorted(pdf_dir.rglob(pat)))
    # 去重（大小写不敏感的路径）
    seen, uniq = set(), []
    for p in out:
        k = str(p).lower()
        if k not in seen:
            seen.add(k)
            uniq.append(p)
    return uniq


def _match_by_title(pdf: Path, title: str) -> float:
    """文件名与标题的相似度（0–1）。"""
    stem = re.sub(r"\.pdf$", "", pdf.stem, flags=re.IGNORECASE)
    stem = re.sub(r"[^0-9A-Za-z一-鿿]+", "", stem)
    t = re.sub(r"[^0-9A-Za-z一-鿿]+", "", title or "")
    if not stem or not t:
        return 0.0
    return difflib.SequenceMatcher(None, stem[:80], t[:80]).ratio()


def main() -> int:
    ap = argparse.ArgumentParser(
        description="PDF 全文提取：回填摘要与关键词（可选能力，缺依赖不阻断）")
    ap.add_argument("target", help="题录：.json 产物 / 题录库 / 题录文件")
    ap.add_argument("--workspace", default="./.lit_work")
    ap.add_argument("--out", default="./out")
    ap.add_argument("--pdf-dir", help="PDF 所在目录（题录无 pdf_path 时用）")
    ap.add_argument("--max-files", type=int, default=300,
                    help="最多处理多少个 PDF（默认 300，防误扫大目录）")
    ap.add_argument("--min-chars", type=int, default=120,
                    help="抽出的文本少于该字符数视为扫描件/无效（默认120，"
                         "实测短篇论文首页可能仅 150–200 字符）")
    ap.add_argument("--json-out", default="pdf_text.json")
    ap.add_argument("--apply", action="store_true",
                    help="把提取结果写回 refs.json（会修改该文件）")
    args = ap.parse_args()

    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)

    try:
        refs, meta = load_refs(args.target, args.workspace)
    except Exception as e:  # noqa: BLE001
        print(f"[error] 题录装载失败: {e}", file=sys.stderr)
        print(f"[hint] {EXIT[1]}", file=sys.stderr)
        return 1
    if not refs:
        print("[error] 题录为空", file=sys.stderr)
        return 4

    # ── 定位 PDF ──
    pdfs: list[Path] = []
    if args.pdf_dir:
        d = Path(args.pdf_dir).expanduser()
        if not d.is_dir():
            print(f"[error] --pdf-dir 不存在: {d}", file=sys.stderr)
            return 4
        pdfs = _index_pdfs(d)[: args.max_files]
    else:
        pdfs = [Path(r.pdf_path) for r in refs
                if getattr(r, "pdf_path", None)
                and Path(r.pdf_path).is_file()]
    if args.pdf_dir:
        print(f"[info] 在 {args.pdf_dir} 找到 {len(pdfs)} 个 PDF", file=sys.stderr)
    else:
        print(f"[info] 题录自带路径命中 {len(pdfs)} 个 PDF", file=sys.stderr)
    if not pdfs:
        msg = ("题录里没有 PDF 路径。可用 --pdf-dir 指向存放 PDF 的目录"
               "（本包会按标题模糊匹配文件名）。")
        print(f"[warn] {msg}", file=sys.stderr)
        print("[info] 这是可选能力，未提供 PDF 不影响其余分析。", file=sys.stderr)
        (outdir / args.json_out).write_text(json.dumps(
            {"ok": True, "enabled": False, "reason": msg,
             "records": [], "backfill": {}, "stats": {}}, ensure_ascii=False,
            indent=2), encoding="utf-8")
        return 0

    # ── 建立 PDF 索引：先读每个 PDF 的首页文本，用于**内容级**匹配 ──
    # 只靠文件名匹配不够：实测把 PDF 命名成 paper_1.pdf 时命中率≈ 0。
    # 做法：抽首页文本→ 若包含题目标题的显著片段，视为同一条。
    pdf_first_page: dict[str, str] = {}
    if args.pdf_dir:
        for p in pdfs:
            t, e = _pdf_text(p, pages=1)
            if t and not e:
                pdf_first_page[str(p.resolve())] = _WS_PAT.sub("", t)[:1500]
        print(f"[info] 已索引 {len(pdf_first_page)} 个 PDF 首页文本用于标题匹配",
              file=sys.stderr)

    def _title_in_pdf(title: str, text: str) -> bool:
        """题目标题的显著片段是否出现在 PDF 首页。

        [C1 修复] 标题与 PDF 文本做**同一套**归一（剥除非 [0-9A-Za-z一-鿿]），
        否则带标点英文标题（如 "A Study of X: A Method"）因标题被剥标点、
        而 PDF 文本保留标点，永远匹配不上。
        修复前该不匹配已用 C-fix-1 夹具复现（B0），修复后同一夹具内容级命中率
        应 ≥ B0 且不下降。
        """
        t = re.sub(r"[^0-9A-Za-z一-鿿]+", "", title or "")
        if len(t) < 8:
            return False
        # PDF 首页文本同样归一，消除标点不对称
        txt = re.sub(r"[^0-9A-Za-z一-鿿]+", "", text or "")
        # 取标题前 12 字与后 12 字，两段都命中才算同一条（避免短词误配）
        head, tail = t[:12], t[-12:]
        return head in txt and (tail in txt or len(t) <= 14)

    # ── 逐条匹配并提取 ──
    by_path = {str(p.resolve()): p for p in pdfs}
    used: set[str] = set()
    records, backfill = [], {}
    no_pypdf_msg = None
    scanned = invalid = matched_by_title = matched_by_content = matched_by_filename = 0

    # [C11] 规模化优化：原实现为 O(题录数 × 索引PDF数)（5683 × P），
    # --max-files 2000 真实运行超时（Exit 137）。改为预构建索引，把逐条全扫描降为
    # O(1) 候选查找 + 小候选集校验：
    #   · content_win_index ：PDF 首页归一文本前 240 字的所有 12 字滑窗 → 候选 PDF 键
    #                         （保留「标题任意位置出现在首页文字」的子串语义，仅限前 240 字以控内存）
    #   · name_exact_index  ：PDF 文件名归一全文 → PDF 键（精确 文件名=标题）
    #   · name_prefix_index ：PDF 文件名归一前 6 字 → 候选 PDF 键（模糊回退的有界候选集）
    _norm_key = lambda s: re.sub(r"[^0-9A-Za-z一-鿿]+", "", s or "")
    content_win_index: dict[str, list[str]] = {}
    name_exact_index: dict[str, str] = {}
    name_prefix_index: dict[str, list[str]] = {}
    for p in pdfs:
        k = str(p.resolve())
        fp = pdf_first_page.get(k, "")
        if fp:
            nt = _norm_key(fp)[:240]
            for j in range(0, max(0, len(nt) - 11)):
                content_win_index.setdefault(nt[j:j + 12], []).append(k)
        stem = _norm_key(p.stem)
        if stem:
            name_exact_index.setdefault(stem, k)          # 首出现优先
            name_prefix_index.setdefault(stem[:6], []).append(k)

    for i, r in enumerate(refs):
        cand: Path | None = None
        pp = getattr(r, "pdf_path", None)
        if pp and str(Path(pp).resolve()) in by_path:
            cand = by_path[str(Path(pp).resolve())]
        if cand is None and args.pdf_dir:
            t = getattr(r, "title", "") or ""
            t_head = _norm_key(t)[:12]
            t_norm = _norm_key(t)
            # ① 内容级：用滑窗索引把候选收窄到「首页文字含标题前 12 字」的 PDF，再校验 tail
            for k in content_win_index.get(t_head, []):
                if k in used:
                    continue
                if _title_in_pdf(t, pdf_first_page.get(k, "")):
                    cand = by_path[k]
                    matched_by_title += 1
                    matched_by_content += 1
                    break
            # ② 文件名级：先精确归一匹配，再在「前 6 字同前缀」的有界候选集里跑 difflib
            if cand is None:
                ke = name_exact_index.get(t_norm)
                if ke and ke not in used:
                    cand = by_path[ke]
                    matched_by_title += 1
                    matched_by_filename += 1
                else:
                    best, score = None, 0.0
                    for k in name_prefix_index.get(t_norm[:6], []):
                        if k in used:
                            continue
                        s2 = _match_by_title(by_path[k], t)
                        if s2 > score:
                            best, score = k, s2
                    if best is not None and score >= 0.55:
                        cand = by_path[best]
                        matched_by_title += 1
                        matched_by_filename += 1
        if cand is None:
            continue
        used.add(str(cand.resolve()))

        text, err = _pdf_text(cand)
        if err:
            if "pypdf" in err and no_pypdf_msg is None:
                no_pypdf_msg = err
                break
            invalid += 1
            continue
        if len(text.strip()) < args.min_chars:
            scanned += 1
            continue
        ab, kws = _parse_fields(text)
        if not ab and not kws:
            invalid += 1
            continue
        rid = getattr(r, "id", None) or i
        records.append({
            "id": rid,
            "title": (getattr(r, "title", "") or "")[:120],
            "pdf": str(cand),
            "chars": len(text),
            "abstract": ab,
            "keywords": kws,
        })
        # 只回填「原来没有」的字段，不覆盖用户已有内容
        upd = {}
        if ab and not (getattr(r, "abstract", "") or "").strip():
            upd["abstract"] = ab
        if kws and not (getattr(r, "keywords", None) or []):
            upd["keywords"] = kws
        if upd:
            backfill[str(rid)] = upd
        del i

    stats = {
        "refs_total": len(refs),
        "pdf_available": len(pdfs),
        "matched": len(records),
        "matched_by_title": matched_by_title,
        "matched_by_content": matched_by_content,
        "matched_by_filename": matched_by_filename,
        "scanned_or_short": scanned,
        "no_field_found": invalid,
        "backfilled_records": len(backfill),
        "abstract_filled": sum(1 for v in backfill.values() if "abstract" in v),
        "keywords_filled": sum(1 for v in backfill.values() if "keywords" in v),
    }
    payload = {
        "ok": True,
        "type": "pdf_text",
        "enabled": True,
        "library": meta.get("display_path"),
        "note": ("PDF 提取为可选能力：仅回填题录中原本缺失的字段，"
                 "不覆盖已有内容；pypdf 缺失时本项自动跳过，不影响其余分析。"),
        "stats": stats,
        "records": records,
        "backfill": backfill,
    }
    if no_pypdf_msg:
        payload["enabled"] = False
        payload["reason"] = no_pypdf_msg
    (outdir / args.json_out).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # ── 可选：写回 refs.json ──
    if args.apply and backfill:
        tp = Path(args.target)
        if tp.suffix.lower() != ".json":
            print("[warn] --apply 仅支持 .json 题录产物，已跳过写回", file=sys.stderr)
        else:
            data = json.loads(tp.read_text(encoding="utf-8"))
            items = data if isinstance(data, list) else data.get("refs", [])
            n = 0
            for it in items:
                upd = backfill.get(str(it.get("id")))
                if not upd:
                    continue
                for k, v in upd.items():
                    it[k] = v
                    n += 1
            tp.write_text(json.dumps(data, ensure_ascii=False, indent=1),
                         encoding="utf-8")
            print(f"[ok] 已回填 {n} 个字段到 {tp.name}", file=sys.stderr)

    print(json.dumps(stats, ensure_ascii=False))
    if no_pypdf_msg:
        print(f"[warn] {no_pypdf_msg}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())