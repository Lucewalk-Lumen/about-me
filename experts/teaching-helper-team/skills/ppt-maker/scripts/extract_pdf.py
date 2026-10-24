#!/usr/bin/env python3
"""extract_pdf.py - PDF → deck spec JSON + 每页光栅图（用于「PPT·PDF 转换重编辑」场景）。

逐页渲染为 assets/page-N.png，并尽量抽取文本作为备注；输出 deck spec：
  <out_dir>/deck-spec.json  （image 型幻灯片 + 文本备注）
  <out_dir>/assets/page-N.png

需要 pymupdf：若未安装会提示经 setup 初始化 venv 后由 $VENV_PY 调用。
可选 --raster-if-empty：仅当某页无文本时才光栅（默认每页都光栅，保真最高）。

Usage:
  python3 extract_pdf.py <in.pdf> <out_dir> [--preset academic-light] [--raster-if-empty]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Extract PDF into a deck spec (raster pages).")
    ap.add_argument("pdf", help="Input .pdf path")
    ap.add_argument("out_dir", help="Output directory")
    ap.add_argument("--preset", default="academic-light")
    ap.add_argument("--raster-if-empty", action="store_true",
                    help="仅当页面无文本时才光栅该页")
    args = ap.parse_args(argv)

    # 输入存在性检查先于依赖检查（避免缺依赖+路径错时误报「需 pymupdf」）
    p = Path(args.pdf)
    if not p.exists():
        print(f"ERROR: not found: {p}", file=sys.stderr)
        return 2
    if not p.is_file():
        print(f"ERROR: not a file: {p}", file=sys.stderr)
        return 2
    out = Path(args.out_dir)
    assets = out / "assets"
    assets.mkdir(parents=True, exist_ok=True)

    try:
        import fitz  # pymupdf
    except ImportError:
        # venv 校验：未用托管 venv 运行时提示更明确的解释器路径
        venv_hint = ""
        if "teaching-helper-team" not in str(sys.executable):
            venv_hint = (f"\n  当前解释器: {sys.executable}\n"
                         "  提示: 请用 setup-status.json 中的 venv_python 运行（禁止裸 python3），"
                         "如: $VENV_PY extract_pdf.py <in.pdf> <out_dir>")
        print("ERROR: 需要 pymupdf。请先经 skills/setup 初始化 venv，再以 $VENV_PY 运行本脚本。"
              + venv_hint, file=sys.stderr)
        return 3

    try:
        doc = fitz.open(str(p))
    except Exception as e:
        print(f"ERROR: 无法打开 pdf（文件损坏或格式不支持）: {e}", file=sys.stderr)
        return 2
    slides_spec = []
    for pi in range(doc.page_count):
        page = doc[pi]
        text = re.sub(r"\s+", " ", page.get_text().strip())
        raster = not args.raster_if_empty or not text
        if raster:
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img_path = assets / f"page-{pi+1}.png"
            pix.save(str(img_path))
            spec = {
                "type": "image",
                "title": f"第 {pi+1} 页",
                "src": str(img_path.relative_to(out)),
            }
            if text:
                spec["caption"] = text[:200]
        else:
            spec = {
                "type": "bullets",
                "title": f"第 {pi+1} 页",
                "points": [t for t in text.split(". ") if t][:8],
            }
        slides_spec.append(spec)

    deck = {
        "meta": {"title": p.stem, "course": ""},
        "preset": args.preset,
        "slides": slides_spec,
    }
    # 主题色近似：PDF 无主题 XML，用首页（前 2 页）非白像素的主色/次色近似，
    # 写入 spec.vars（--bg/--primary/--accent）供 build_deck 风格继承；失败不阻断。
    try:
        probe_max = min(2, doc.page_count)
        from collections import Counter
        colors = Counter()
        for pi in range(probe_max):
            pix = doc[pi].get_pixmap(matrix=fitz.Matrix(0.5, 0.5))
            n = pix.width * pix.height
            samples = pix.samples
            step = max(1, n // 8000)  # 采样上限 ~8000 像素
            for i in range(0, n * 3, step * 3):
                r, g, b = samples[i], samples[i + 1], samples[i + 2]
                if r > 240 and g > 240 and b > 240:  # 跳过近白背景
                    continue
                colors[(r // 16 * 16, g // 16 * 16, b // 16 * 16)] += 1
        if colors:
            (cr, cg, cb), _ = colors.most_common(1)[0]
            # 背景取近白采样（若存在）
            bg_count = Counter()
            for pi in range(probe_max):
                pix = doc[pi].get_pixmap(matrix=fitz.Matrix(0.5, 0.5))
                n = pix.width * pix.height
                step = max(1, n // 8000)
                samples = pix.samples
                for i in range(0, n * 3, step * 3):
                    r, g, b = samples[i], samples[i + 1], samples[i + 2]
                    if r > 235 and g > 235 and b > 235:
                        bg_count[(r // 16 * 16, g // 16 * 16, b // 16 * 16)] += 1
            vars_out = {}
            if bg_count:
                (br, bgc, bb), _ = bg_count.most_common(1)[0]
                vars_out["--bg"] = f"#{br:02x}{bgc:02x}{bb:02x}"
            vars_out["--primary"] = f"#{cr:02x}{cg:02x}{cb:02x}"
            vars_out["--accent"] = f"#{cr:02x}{cg:02x}{cb:02x}"
            deck["vars"] = vars_out
    except Exception:
        pass  # 主题近似失败不阻断
    (out / "deck-spec.json").write_text(json.dumps(deck, ensure_ascii=False, indent=2),
                                        encoding="utf-8")
    print(f"OK 抽取 {len(slides_spec)} 页 → {out/'deck-spec.json'} （光栅 {sum(1 for s in slides_spec if s.get('type')=='image')} 页"
          + ("，主题色近似 [OK]" if deck.get("vars") else "）"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
