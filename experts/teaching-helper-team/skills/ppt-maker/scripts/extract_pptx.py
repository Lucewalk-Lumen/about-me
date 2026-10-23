#!/usr/bin/env python3
"""extract_pptx.py - PPTX → deck spec JSON + assets（用于「PPT·PDF 转换重编辑」场景）。

抽取每页标题 / 要点 / 备注 / 图片，输出可直接交给 build_deck.py 的 deck spec：
  <out_dir>/deck-spec.json  （meta + preset + slides[]）
  <out_dir>/assets/*.png    （幻灯片内嵌图片）

需要 python-pptx：若未安装会提示用 setup 初始化 venv 后通过 $VENV_PY 调用。

可选增强（借鉴 markitdown 思路，未引入依赖）：
  若需「PPT→md→md2spec」链路（保留 md 大纲可审阅性），可用微软 MarkItDown CLI
  （`pip install 'markitdown[pptx]'`，独立于本包零依赖原则）将 pptx 转 md 后，
  再经 `md2spec.py` 生成 spec；本脚本仍是零依赖的确定性抽取路径。

Usage:
  python3 extract_pptx.py <in.pptx> <out_dir> [--preset academic-light]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Extract PPTX into a deck spec JSON.")
    ap.add_argument("pptx", help="Input .pptx path")
    ap.add_argument("out_dir", help="Output directory")
    ap.add_argument("--preset", default="academic-light")
    args = ap.parse_args(argv)

    # 输入存在性检查先于依赖检查（避免缺依赖+路径错时误报「需 python-pptx」）
    p = Path(args.pptx)
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
        from pptx import Presentation
    except ImportError:
        # venv 校验：未用托管 venv 运行时提示更明确的解释器路径
        venv_hint = ""
        if "teaching-helper-team" not in str(sys.executable):
            venv_hint = (f"\n  当前解释器: {sys.executable}\n"
                         "  提示: 请用 setup-status.json 中的 venv_python 运行（禁止裸 python3），"
                         "如: $VENV_PY extract_pptx.py <in.pptx> <out_dir>")
        print("ERROR: 需要 python-pptx。请先经 skills/setup 初始化 venv，再以 $VENV_PY 运行本脚本。"
              + venv_hint, file=sys.stderr)
        return 3

    try:
        prs = Presentation(str(p))
    except Exception as e:
        print(f"ERROR: 无法打开 pptx（文件损坏或格式不支持）: {e}", file=sys.stderr)
        return 2
    slides_spec = []
    img_idx = 0

    def clean(t: str) -> str:
        return re.sub(r"\s+", " ", (t or "")).strip()

    for si, slide in enumerate(prs.slides, 1):
        pics, notes = [], []
        # 备注
        if slide.has_notes_slide:
            nt = slide.notes_slide.notes_text_frame.text
            if nt:
                notes.append(clean(nt))
        # 形状
        title_text = ""
        body_pts = []
        for sh in slide.shapes:
            if sh.shape_type == 13:  # PICTURE
                try:
                    img_idx += 1
                    img_path = assets / f"slide{si}_{img_idx}.png"
                    with open(img_path, "wb") as f:
                        f.write(sh.image.blob)
                    pics.append(str(img_path.relative_to(out)))
                except Exception:
                    pass
                continue
            if not sh.has_text_frame:
                continue
            txt = clean(sh.text_frame.text)
            if not txt:
                continue
            # 标题：第一个较大/靠上的文本框
            if not title_text and sh.top is not None and sh.width:
                title_text = txt
            else:
                body_pts.append(txt)
        if not title_text and body_pts:
            title_text = body_pts.pop(0)

        spec = {"title": title_text or f"第 {si} 页"}
        if pics and not body_pts:
            spec["type"] = "image"
            spec["src"] = pics[0]
            if notes:
                spec["caption"] = "；".join(notes)
        elif body_pts:
            spec["type"] = "bullets"
            spec["points"] = body_pts
            if pics:
                spec["notes"] = "；".join(notes + [f"含图：{pics[0]}"])
            elif notes:
                spec["notes"] = "；".join(notes)
        else:
            spec["type"] = "bullets"
            spec["points"] = []
            if notes:
                spec["notes"] = "；".join(notes)
        slides_spec.append(spec)

    deck = {
        "meta": {"title": p.stem, "course": ""},
        "preset": args.preset,
        "slides": slides_spec,
    }
    # 风格继承：从 PPT 主题部件（theme1.xml）抽取主色/强调色/字体栈 → spec.vars。
    # 正确访问路径：slide_masters[0] 的 theme 部件（RT.THEME）→ part.blob（XML 字节）→ lxml 解析；
    # 主题色取自 theme1.xml（sldMaster 不含主题色）。抽取失败不阻断。
    try:
        from pptx.opc.constants import RELATIONSHIP_TYPE as RT
        from pptx.oxml.ns import qn
        from lxml import etree
        master = prs.slide_masters[0] if prs.slide_masters else None
        theme_part = master.part.part_related_by(RT.THEME) if master is not None else None
        theme_el = None
        if theme_part is not None:
            theme_el = etree.fromstring(theme_part.blob)  # <a:theme> 根
        if theme_el is not None:
            # clrScheme/fontScheme 位于 <a:theme><a:themeElements> 下（非 theme 直接子级）
            theme_els = theme_el.find(qn("a:themeElements"))
            holder = theme_els if theme_els is not None else theme_el
            clr_scheme = holder.find(qn("a:clrScheme"))
            font_scheme = holder.find(qn("a:fontScheme"))
            vars_out = {}
            if clr_scheme is not None:
                def _get_hex(tag):
                    node = clr_scheme.find(qn(f"a:{tag}"))
                    if node is None:
                        return None
                    srgb = node.find(qn("a:srgbClr"))
                    if srgb is not None and srgb.get("val"):
                        return "#" + srgb.get("val")
                    sys_clr = node.find(qn("a:sysClr"))
                    if sys_clr is not None and sys_clr.get("lastClr"):
                        return "#" + sys_clr.get("lastClr")
                    return None
                # dk1 → --primary（标题），dk2 → --fg，lt1 → --bg，accent1 → --accent
                dk1, dk2, lt1, accent1 = (_get_hex(t) for t in
                                          ("dk1", "dk2", "lt1", "accent1"))
                if dk2:
                    vars_out["--fg"] = dk2
                if dk1:
                    vars_out["--primary"] = dk1
                if lt1:
                    vars_out["--bg"] = lt1
                if accent1:
                    vars_out["--accent"] = accent1
            if font_scheme is not None:
                maj = font_scheme.find(qn("a:majorFont"))
                if maj is not None:
                    latin = maj.find(qn("a:latin"))
                    if latin is not None and latin.get("typeface"):
                        vars_out["--font-head"] = f'"{latin.get("typeface")}",sans-serif'
                minor = font_scheme.find(qn("a:minorFont"))
                if minor is not None:
                    latin = minor.find(qn("a:latin"))
                    if latin is not None and latin.get("typeface"):
                        vars_out["--font-body"] = f'"{latin.get("typeface")}",sans-serif'
            if vars_out:
                deck["vars"] = vars_out  # build_deck 消费：spec.vars 覆盖 preset 变量
    except Exception:
        pass  # 主题抽取失败不阻断（部分 pptx 主题 XML 结构差异）
    (out / "deck-spec.json").write_text(json.dumps(deck, ensure_ascii=False, indent=2),
                                        encoding="utf-8")
    print(f"OK 抽取 {len(slides_spec)} 页 → {out/'deck-spec.json'} ，图片 {img_idx} 张 → {assets}"
          + (f" ，主题色 {'[OK]' if deck.get('vars') else '[X]'}" if prs.slide_masters else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
