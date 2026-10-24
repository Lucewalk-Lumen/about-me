#!/usr/bin/env python3
"""edit_deck.py - 把编辑运行时注入已有 HTML deck（「增强/编辑已有 deck」场景）。

输入任意 HTML（最好是本技能 build_deck 生成的 deck；也支持含 <section class="slide"> 的文稿，
或普通 HTML——后者会被包成单页可编辑 deck）。输出内嵌编辑运行时（对象拖⠿/缩放/多选/增删、
Pages 侧栏重排复制删除、+New、Undo/Redo、本地保存、导出干净 HTML）的可编辑 HTML。

零第三方依赖，纯标准库字符串操作。

Usage:
  python3 edit_deck.py --in existing.html --out editable.html [--title "我的课件"]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# 复用 build_deck 的运行时契约（CSS / NAV / EDITOR / HUD 结构）
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_deck import RUNTIME_BLOCK  # noqa: E402


def backfill_slides_and_objects(html_text: str) -> str:
    """为缺失稳定 id 的 slide、缺失 data-oid 的 .obj 补标（满足运行时契约）。"""
    # 1) section.slide 稳定 id
    idx = [0]

    def slide_id(m):
        idx[0] += 1
        if re.search(r'\bid="[^"]+"', m.group(0)):
            return m.group(0)
        return m.group(0).replace("<section", f'<section id="slide-{idx[0]}"', 1)

    html_text = re.sub(r'<section\b[^>]*\bclass="[^"]*\bslide\b[^"]*"[^>]*>',
                       slide_id, html_text, flags=re.S)
    # 3) .obj 补 data-slide-object + data-oid
    oid = [0]

    def obj_mark(m):
        tag = m.group(0)
        if 'data-slide-object' in tag:
            return tag
        oid[0] += 1
        # 在 class 之后插入属性
        return re.sub(r'(<div\b[^>]*\bclass="[^"]*\bobj\b[^"]*"[^>]*?)>',
                      lambda x: x.group(1) + f' data-slide-object data-oid="o{oid[0]}">',
                      tag, count=1)

    html_text = re.sub(r'<div\b[^>]*\bclass="[^"]*\bobj\b[^"]*"[^>]*>', obj_mark, html_text)
    return html_text


# 哨兵注释：包裹 edit_deck 注入的编辑运行时，保证重复运行 edit_deck 永不复制运行时
RUNTIME_START = "<!--EDIT_DECK_RUNTIME_START-->"
RUNTIME_END = "<!--EDIT_DECK_RUNTIME_END-->"


def inject_runtime(html_text: str, title: str) -> str:
    # 标题（幂等：已存在则覆盖，不存在则补）
    if '<title>' not in html_text:
        html_text = html_text.replace('<head>', f'<head>\n<title>{title}</title>', 1)
    else:
        html_text = re.sub(r'<title>.*?</title>', f'<title>{title}</title>', html_text, flags=re.S)

    # 构造带哨兵的运行时整块（CSS + HUD + NAV/EDITOR 脚本），单一连续块，置于 </body> 前。
    # CSS 以独立 <style> 落到 </body> 前（样式全局生效），HUD 为 fixed 定位不依赖位置。
    editor_css = RUNTIME_BLOCK["css"]
    hud = RUNTIME_BLOCK["hud_html"]
    nav = RUNTIME_BLOCK["nav"]
    editor = RUNTIME_BLOCK["editor"]
    script = (f'<script>\nvar NAV_JS_SRC = {json.dumps(nav)};\nvar EDITOR_JS_SRC = {json.dumps(editor)};\n'
              f'{nav}\n{editor}\n</script>')
    block = (f'\n{RUNTIME_START}\n<style>\n{editor_css}\n</style>\n{hud}\n{script}\n{RUNTIME_END}\n')

    # 1) 先剥离任何已存在的哨兵运行时块（无论几份，保证最终唯一实例，消除历史重复注入残留）
    html_text = re.sub(re.escape(RUNTIME_START) + r".*?" + re.escape(RUNTIME_END),
                       "", html_text, flags=re.S)
    # 2) build_deck 等已注入过运行时（无哨兵、hud 已存在）则不重复注入
    if 'id="hud"' in html_text:
        return html_text
    # 3) 全新注入：在 </body> 前插入带哨兵的整块（无 </body> 则追加到文件末尾）
    if '</body>' in html_text:
        html_text = html_text.replace('</body>', f'{block}\n</body>', 1)
    else:
        html_text = html_text + block
    return html_text


def ensure_stage(html_text: str) -> str:
    """若原 HTML 没有 #viewport>#stage 结构（非本技能生成的普通 HTML），
    将其 <body> 内容包成单页可编辑 deck。"""
    if 'id="stage"' in html_text:
        return html_text
    m = re.search(r'<body[^>]*>(.*)</body>', html_text, flags=re.S)
    if not m:
        return html_text
    inner = m.group(1)
    wrapped = (f'<body>\n<div id="viewport"><div id="stage">\n'
               f'<section class="slide" id="slide-1" data-idx="0">\n'
               f'<div class="obj" data-slide-object data-oid="o1" '
               f'style="left:140px;top:110px;width:1640px;">{inner}</div>\n'
               f'</section>\n</div></div>')
    html_text = html_text[:m.start()] + wrapped + html_text[m.end():]
    return html_text


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Inject editing runtime into an existing HTML deck.")
    ap.add_argument("--in", dest="inp", required=True, help="Existing HTML deck path")
    ap.add_argument("--out", required=True, help="Output editable .html path")
    ap.add_argument("--title", default="可编辑演示文稿", help="Document title")
    args = ap.parse_args(argv)

    src = Path(args.inp)
    if not src.exists():
        print(f"ERROR: input not found: {args.inp}", file=sys.stderr)
        return 2
    text = src.read_text(encoding="utf-8")
    text = ensure_stage(text)
    text = backfill_slides_and_objects(text)
    text = inject_runtime(text, args.title)
    Path(args.out).write_text(text, encoding="utf-8")
    print(f"OK injected runtime -> {args.out} ({len(text)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
