#!/usr/bin/env python3
"""merge_spec.py - 合并两个 deck spec（纯标准库，零依赖）。

解决「课型骨架（--template）定结构 + md2spec 供内容」的合并场景：
  merge_spec.py 骨架.json 内容.json -o 合并.json [--prefer content]

规则：
- meta.title / meta.course 取第一个非空；preset 取骨架的（若内容有 vars 则合并）
- slides 按「骨架为底、内容覆盖」合并：
  - 骨架页无标题填充时（[占位] 开头）被内容页覆盖（按序）
  - 内容页多于骨架页时，多余内容页追加到末尾
- --prefer content：内容页优先（骨架仅当内容不足时补充占位页）

Usage:
  python3 merge_spec.py skeleton.json content.json -o merged.json [--prefer content]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _load(p: str) -> dict:
    path = Path(p)
    if not path.is_file():
        print(f"ERROR: 文件不存在: {p}", file=sys.stderr)
        sys.exit(2)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"ERROR: 不是合法 JSON: {p} ({e})", file=sys.stderr)
        sys.exit(2)


def _is_placeholder(s: dict) -> bool:
    """骨架占位页判定：标题含 [占位] 前缀。"""
    title = str(s.get("title", ""))
    return title.startswith("[占位") or title.startswith("[占位]")


def merge(skel: dict, content: dict, prefer_content: bool = False) -> dict:
    skel_slides = list(skel.get("slides", []))
    content_slides = list(content.get("slides", []))

    if prefer_content:
        # 内容优先：内容不足骨架页数时用骨架占位页补齐
        out = [dict(s) for s in content_slides]
        need = max(0, len(skel_slides) - len(out))
        for s in skel_slides[len(skel_slides) - need:] if need else []:
            out.append(dict(s))
    else:
        # 骨架为底：按序覆盖，内容多余页追加
        out = []
        ci = 0
        for s in skel_slides:
            if ci < len(content_slides):
                # 骨架占位页 → 内容页覆盖；骨架非占位页 → 保留骨架
                if _is_placeholder(s):
                    out.append(dict(content_slides[ci]))
                    ci += 1
                else:
                    out.append(dict(s))
            else:
                out.append(dict(s))
        for s in content_slides[ci:]:
            out.append(dict(s))

    meta = {}
    for k in ("title", "course"):
        v = skel.get("meta", {}).get(k) or content.get("meta", {}).get(k)
        if v:
            meta[k] = v
    merged = {
        "meta": meta or skel.get("meta", {}),
        "preset": skel.get("preset") or content.get("preset") or "academic-light",
        "slides": out,
    }
    vars_out = dict(content.get("vars") or {})
    vars_out.update(skel.get("vars") or {})
    if vars_out:
        merged["vars"] = vars_out
    return merged


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Merge two deck specs (skeleton + content).")
    ap.add_argument("skeleton", help="Skeleton spec (--template output)")
    ap.add_argument("content", help="Content spec (md2spec output)")
    ap.add_argument("-o", "--out", required=True, help="Output merged spec json")
    ap.add_argument("--prefer", choices=["content", "skeleton"], default="skeleton",
                    help="Which spec takes priority (default: skeleton)")
    args = ap.parse_args(argv)

    skel = _load(args.skeleton)
    content = _load(args.content)
    merged = merge(skel, content, prefer_content=(args.prefer == "content"))
    Path(args.out).write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK merged -> {args.out} ({len(merged['slides'])} slides, preset={merged['preset']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
