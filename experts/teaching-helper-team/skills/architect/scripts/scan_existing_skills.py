#!/usr/bin/env python3
"""扫描已有 WorkBuddy 技能，按相似度召回候选（通用「先扫描再创建」入口）。

用于在制作新技能/agent 前，复用已有技能或判断是否应修改已有而非新建。
默认扫描 ~/.workbuddy/skills（用户级），可用 --base 追加其他目录
（如项目级 .workbuddy/skills）。

相似度阈值示例（通用，跨宿主可沿用）：
  >= 0.72  高相似：建议修改已有
  0.45-0.72 中相似：展示候选，让用户选修改/新建
  < 0.45   低相似：可直接新建
"""
import argparse
import os
import re
import sys

DEFAULT_BASES = [os.path.expanduser("~/.workbuddy/skills")]


def tokenize(value):
    tokens = set()
    if not value:
        return tokens
    for ch in " /\\-_：:，,。.()（）[]【】\n\t":
        value = value.replace(ch, " ")
    words = re.findall(r"[a-z0-9一-鿿]+", value.lower())
    for w in words:
        tokens.add(w)
        if len(w) >= 4:
            for i in range(len(w) - 3):
                tokens.add(w[i:i + 4])
    return tokens


def load_skill(path):
    md = os.path.join(path, "SKILL.md")
    if not os.path.isfile(md):
        return None
    try:
        with open(md, encoding="utf-8", errors="ignore") as f:
            text = f.read()
    except OSError:
        return None
    fm = {}
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                fm[k.strip()] = v.strip()
    return {
        "dir": os.path.basename(path),
        "name": fm.get("name", ""),
        "description": fm.get("description", ""),
        "path": path,
    }


def score(query_tokens, skill):
    field_tokens = tokenize(f"{skill['name']} {skill['description']}")
    if not query_tokens or not field_tokens:
        return 0.0, []
    overlap = query_tokens & field_tokens
    if not overlap:
        return 0.0, []
    s = sum(1 for t in overlap if len(t) >= 4) + 0.3 * sum(1 for t in overlap if len(t) < 4)
    return min(1.0, s / max(1, len(query_tokens))), sorted(overlap)


def main():
    ap = argparse.ArgumentParser(description="Scan existing WorkBuddy skills for similarity")
    ap.add_argument("query", help="场景关键词 / 自然语言需求")
    ap.add_argument("--limit", type=int, default=3)
    ap.add_argument("--base", action="append", default=[], help="额外技能根目录（可多次）")
    args = ap.parse_args()

    bases = [os.path.expanduser(b) for b in (args.base or DEFAULT_BASES)]
    skills = []
    for base in bases:
        if not os.path.isdir(base):
            continue
        for name in sorted(os.listdir(base)):
            p = os.path.join(base, name)
            if os.path.isdir(p):
                s = load_skill(p)
                if s:
                    skills.append(s)

    q_tokens = tokenize(args.query)
    scored = []
    for s in skills:
        sc, matched = score(q_tokens, s)
        if sc > 0:
            scored.append((sc, matched, s))
    scored.sort(key=lambda x: x[0], reverse=True)

    if not scored:
        print("未找到相似技能，可直接新建。")
        sys.exit(0)

    for sc, matched, s in scored[:args.limit]:
        print(f"- {s['name']}  (相似度 {sc:.2f})")
        print(f"  路径: {s['path']}")
        print(f"  匹配: {', '.join(matched)}")
        print(f"  描述: {s['description'][:80]}")

    top = scored[0][0]
    if top >= 0.72:
        print("\n建议：相似度较高，优先修改已有技能而非新建。")
    elif top >= 0.45:
        print("\n建议：存在候选，请选择修改已有或新建。")
    else:
        print("\n建议：相似度低，可直接新建。")


if __name__ == "__main__":
    main()
