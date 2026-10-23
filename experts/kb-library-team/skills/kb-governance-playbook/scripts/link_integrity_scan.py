#!/usr/bin/env python3
"""link_integrity_scan.py - 死链与孤儿条目扫描（机械层，零三方依赖）。

支持两种链接语法：
- wiki:   [[note-name]] / [[note-name|alias]] / [[note-name#heading]]（Obsidian）
- markdown: [text](relative/path.md)（LLM Wiki 及通用 Markdown）

判定：
- 死链：链接目标文件不存在（wiki 链接按文件名全库匹配；markdown 链接按相对路径解析）。
- 孤儿：无任何入链且文件名不含 moc/index 的 .md 文件（启发式，供人工复核）。

输出：死链清单 + 孤儿清单（文本）。退出码：0 均无；1 有死链或孤儿；2 参数错误。
"""
import argparse
import os
import re
import sys

WIKI_LINK_RE = re.compile(r"\[\[([^\]\|#]+)(?:#[^\]\|]+)?(?:\|[^\]]+)?\]\]")
MD_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
EXTERNAL_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")


def collect_md(root):
    files = []
    for dirpath, _dirs, names in os.walk(root):
        for n in sorted(names):
            if n.lower().endswith(".md"):
                files.append(os.path.join(dirpath, n))
    return files


def stem(path):
    return os.path.splitext(os.path.basename(path))[0]


def main(argv=None):
    p = argparse.ArgumentParser(
        description="死链与孤儿条目扫描（只报告，不修复）。",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("root", help="库根目录（递归扫描 .md）")
    p.add_argument("--link-style", choices=["wiki", "markdown", "both"], default="both",
                   help="解析的链接语法")
    p.add_argument("--orphan-exclude", default="moc,index,readme",
                   help="逗号分隔的文件名关键词，命中则不计为孤儿（不区分大小写）")
    args = p.parse_args(argv)

    if not os.path.isdir(args.root):
        print("[FAIL] 库根目录不存在: %s" % args.root, file=sys.stderr)
        return 2

    files = collect_md(args.root)
    if not files:
        print("[OK] 库内无 .md 文件")
        return 0

    by_stem = {}
    for f in files:
        by_stem.setdefault(stem(f).lower(), f)
    file_set = set(os.path.abspath(f) for f in files)

    inbound = {os.path.abspath(f): 0 for f in files}
    broken = []

    for f in files:
        try:
            with open(f, "r", encoding="utf-8") as fh:
                text = fh.read()
        except (OSError, UnicodeDecodeError) as e:
            print("[FAIL] 读取失败: %s (%s)" % (f, e), file=sys.stderr)
            return 2

        targets = []  # (raw, resolved_abs_or_None)
        if args.link_style in ("wiki", "both"):
            for m in WIKI_LINK_RE.finditer(text):
                name = m.group(1).strip()
                if not name:
                    continue
                hit = by_stem.get(name.lower())
                targets.append(("[[%s]]" % name, os.path.abspath(hit) if hit else None))
        if args.link_style in ("markdown", "both"):
            for m in MD_LINK_RE.finditer(text):
                url = m.group(1).strip().split("#")[0]
                if not url or EXTERNAL_RE.match(url) or url.startswith("#"):
                    continue
                resolved = os.path.abspath(os.path.join(os.path.dirname(f), url))
                targets.append((url, resolved if os.path.isfile(resolved) else None))

        for raw, resolved in targets:
            if resolved is None:
                broken.append((f, raw))
            elif resolved in file_set and resolved != os.path.abspath(f):
                inbound[resolved] += 1

    exclude_keys = [k.strip().lower() for k in args.orphan_exclude.split(",") if k.strip()]
    orphans = []
    for f in files:
        name = os.path.basename(f).lower()
        if any(k in name for k in exclude_keys):
            continue
        if inbound[os.path.abspath(f)] == 0:
            orphans.append(f)

    exit_code = 0
    print("扫描 %d 个 .md 文件（link-style=%s）" % (len(files), args.link_style))
    if broken:
        exit_code = 1
        print("[FAIL] 死链 %d 处：" % len(broken))
        for src, raw in broken:
            print("  - %s -> %s" % (src, raw))
    else:
        print("[OK] 无死链")
    if orphans:
        exit_code = 1
        print("[FAIL] 孤儿条目 %d 个（无入链，启发式，供人工复核）：" % len(orphans))
        for f in orphans:
            print("  - %s" % f)
    else:
        print("[OK] 无孤儿条目")
    print("---")
    print("以上仅为报告；建链/修链建议由索引导航官产出，写入前须用户确认。")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
