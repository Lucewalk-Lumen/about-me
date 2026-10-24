#!/usr/bin/env python3
"""apply_noreply.py — 将仓库内作者邮箱批量替换为 GitHub noreply。

用法:python3 apply_noreply.py <github-username>
替换范围:experts/、skills/、docs/、*.md 内所有 `buxing@gdufe.edu.cn`
同步动作:写入本仓库 git 提交身份(name=Xing Bu, email=noreply)
"""
import os, re, sys

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OLD = "buxing@gdufe.edu.cn"
TEXT_EXT = {".md", ".json", ".py", ".sh", ".txt", ".yaml", ".yml", ".html", ".js", ".ts", ".toml"}

def main():
    if len(sys.argv) != 2:
        sys.exit("用法:python3 apply_noreply.py <github-username>")
    user = sys.argv[1].strip()
    if not re.fullmatch(r"[A-Za-z0-9-]{1,39}", user):
        sys.exit(f"非法 GitHub 用户名: {user}")
    new = f"{user}@users.noreply.github.com"
    changed = []
    for sub in ("experts", "skills", "docs"):
        root = os.path.join(R, sub)
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in ("node_modules", ".git")]
            for fn in filenames:
                p = os.path.join(dirpath, fn)
                if os.path.splitext(fn)[1].lower() not in TEXT_EXT:
                    continue
                try:
                    with open(p, encoding="utf-8") as f: text = f.read()
                except Exception:
                    continue
                if OLD in text:
                    with open(p, "w", encoding="utf-8") as f: f.write(text.replace(OLD, new))
                    changed.append(os.path.relpath(p, R))
    for fn in ("README.md", "CHANGELOG.md"):
        p = os.path.join(R, fn)
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f: text = f.read()
            if OLD in text:
                with open(p, "w", encoding="utf-8") as f: f.write(text.replace(OLD, new))
                changed.append(fn)
    # git 提交身份(仓库级)
    os.system(f'git -C "{R}" config user.name "Xing Bu"')
    os.system(f'git -C "{R}" config user.email "{new}"')
    print(f"替换完成:{len(changed)} 个文件")
    for c in changed: print("  -", c)
    print(f"git 提交身份已设为 Xing Bu <{new}>")

if __name__ == "__main__":
    main()
