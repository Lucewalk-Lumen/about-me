#!/usr/bin/env python3
"""duplicate_detect.py - 重复/高度相近条目检测（机械层，零三方依赖）。

两档检测：
1. 精确/规整重名：标题归一化（去空白、去常见副本后缀、小写）后完全相同。
2. 高相似标题：基于字符 bigram 的 Jaccard 相似度 >= 阈值（默认 0.80）。

只列疑似对，不删除、不移动任何文件——处置由用户确认后执行。

输入：目录（递归扫描 .md）或若干文件路径。
输出：疑似重复对清单（文本）。退出码：0 无疑似；1 有疑似；2 参数/读取错误。
"""
import argparse
import os
import re
import sys

COPY_SUFFIX_RE = re.compile(
    r"[\s_\-]*(\(\d+\)|（\d+）|-副本|副本|_copy|\scopy|-copy|\s复件)$", re.IGNORECASE)
WS_RE = re.compile(r"\s+")


def normalize_title(name):
    stem = os.path.splitext(os.path.basename(name))[0]
    stem = COPY_SUFFIX_RE.sub("", stem)
    stem = WS_RE.sub("", stem).lower()
    return stem


def bigrams(s):
    if len(s) < 2:
        return {s} if s else set()
    return {s[i:i + 2] for i in range(len(s) - 1)}


def jaccard(a, b):
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    inter = len(a & b)
    return inter / (len(a) + len(b) - inter)


def collect_files(paths):
    files = []
    for p in paths:
        if os.path.isdir(p):
            for root, _dirs, names in os.walk(p):
                for n in sorted(names):
                    if n.lower().endswith(".md"):
                        files.append(os.path.join(root, n))
        elif os.path.isfile(p):
            files.append(p)
        else:
            print("[FAIL] 路径不存在: %s" % p, file=sys.stderr)
            return None
    return files


def main(argv=None):
    p = argparse.ArgumentParser(
        description="重复/高度相近条目检测：只列疑似对，不做任何处置。",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("paths", nargs="+", help="目录（递归扫 .md）或文件路径")
    p.add_argument("--threshold", type=float, default=0.80, help="标题相似度阈值（0-1）")
    args = p.parse_args(argv)

    if not 0.0 < args.threshold <= 1.0:
        print("[FAIL] --threshold 须在 (0, 1] 区间", file=sys.stderr)
        return 2

    files = collect_files(args.paths)
    if files is None:
        return 2
    if len(files) < 2:
        print("[OK] 文件数 %d < 2，无可比对" % len(files))
        return 0

    norms = [(f, normalize_title(f)) for f in files]
    hits = []

    # 第一档：归一化重名
    by_norm = {}
    for f, n in norms:
        by_norm.setdefault(n, []).append(f)
    for n, group in sorted(by_norm.items()):
        if n and len(group) > 1:
            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    hits.append((group[i], group[j], 1.0, "归一化重名"))

    # 第二档：高相似（跳过已命中精确对）
    exact_pairs = {(h[0], h[1]) for h in hits}
    grams = [(f, n, bigrams(n)) for f, n in norms if n]
    for i in range(len(grams)):
        for j in range(i + 1, len(grams)):
            f1, n1, g1 = grams[i]
            f2, n2, g2 = grams[j]
            if (f1, f2) in exact_pairs or n1 == n2:
                continue
            sim = jaccard(g1, g2)
            if sim >= args.threshold:
                hits.append((f1, f2, sim, "标题高相似"))

    if not hits:
        print("[OK] 扫描 %d 个文件，无疑似重复（阈值 %.2f）" % (len(files), args.threshold))
        return 0

    print("[FAIL] 扫描 %d 个文件，发现 %d 对疑似重复（阈值 %.2f）：" % (len(files), len(hits), args.threshold))
    for f1, f2, sim, kind in hits:
        print("  - [%s] 相似度 %.2f" % (kind, sim))
        print("      A: %s" % f1)
        print("      B: %s" % f2)
    print("---")
    print("以上仅为疑似清单；合并/保留处置须用户确认后执行，本脚本不做任何写操作。")
    return 1


if __name__ == "__main__":
    sys.exit(main())
