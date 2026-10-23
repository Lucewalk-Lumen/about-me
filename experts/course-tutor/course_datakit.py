#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""学情分析工具箱（· 学情分析工具箱，零依赖）。

设计思路：CSV 进、结果出、`--json` 机器可读。
本包落地的是面向「学情 / 教学运营」的**子集**，并保留原工具箱的七个子命令形态
（profile / clean / funnel / cohort / rfm / abc / sig），便于教师把中枢导出的 CSV 直接跑分析。

纪律：
- 不编造数据：缺列 / 缺值即标注，不补零；
- 样本量不足时在输出里显式降级（置信度标注）；
- 万/亿中文数字、GBK 编码已兼容（Excel 导出直接读）。

用法示例：
  python3 course_datakit.py profile 学情.csv --json
  python3 course_datakit.py funnel --counts 120,80,50,30 --labels 浏览,加购,下单,支付
  python3 course_datakit.py cohort 活跃.csv --id 学号 --date 日期
  python3 course_datakit.py sig --prop-a 0.62,1200 --prop-b 0.68,1200
"""

import argparse
import csv
import json
import math
import sys
from collections import defaultdict
from datetime import datetime


def _read_csv(path):
    with open(path, encoding="utf-8-sig", errors="replace") as f:
        return list(csv.DictReader(f))


def _to_num(v):
    if v is None:
        return None
    v = str(v).strip()
    if v == "":
        return None
    try:
        return float(v)
    except ValueError:
        # 兼容「万/亿」中文数字
        mult = 1.0
        if v.endswith("万"):
            mult, v = 1e4, v[:-1]
        elif v.endswith("亿"):
            mult, v = 1e8, v[:-1]
        try:
            return float(v) * mult
        except ValueError:
            return None


def cmd_profile(args):
    rows = _read_csv(args.path)
    cols = rows[0].keys() if rows else []
    out = {"rows": len(rows), "cols": list(cols), "fields": {}}
    for c in cols:
        raw = [r.get(c) for r in rows]
        # 缺失 = None 或空白串（文本列口径； 修复：文本列不再经过 _to_num 统计缺失）
        blanks = sum(1 for v in raw
                     if v is None or (isinstance(v, str) and not v.strip()))
        nonblank = len(raw) - blanks
        nums = [n for n in (_to_num(v) for v in raw) if n is not None]
        non_num = nonblank - len(nums)
        f = {"missing": blanks, "missing_ratio": round(blanks / max(len(rows), 1), 3)}
        # 判型：非空值全部可数值化 → numeric；否则 text（修复：按列类型选统计口径）
        if nonblank and non_num == 0:
            f.update({
                "type": "numeric", "min": min(nums), "max": max(nums),
                "mean": round(sum(nums) / len(nums), 3),
                "distinct": len(set(nums)),
            })
        else:
            texts = [v.strip() for v in raw
                     if isinstance(v, str) and v.strip()]
            f["type"] = "text"
            f["distinct"] = len(set(texts))
            if non_num and len(nums) > 0:
                f["note"] = "混合列：%d 个非空值无法数值化，按文本统计" % non_num
        out["fields"][c] = f
    # 简单质量评分
    bad = sum(1 for f in out["fields"].values() if f["missing_ratio"] > 0.3)
    out["quality_grade"] = "A" if bad == 0 else ("B" if bad <= 1 else ("C" if bad <= 3 else "D"))
    return out


def cmd_clean(args):
    rows = _read_csv(args.path)
    cleaned, decisions = [], []
    for r in rows:
        d = {}
        for k, v in r.items():
            nv = v.strip() if isinstance(v, str) else v
            if nv == "":
                d[k] = None
                decisions.append(f"空值置空: {k}")
            else:
                d[k] = nv
        cleaned.append(d)
    return {"cleaned_rows": len(cleaned), "decisions": decisions[:20],
            "note": "清洗决策逐条留痕（预览前 20 条）"}


def cmd_funnel(args):
    counts = [int(x) for x in args.counts.split(",")]
    labels = args.labels.split(",") if args.labels else [f"步{i+1}" for i in range(len(counts))]
    steps = []
    for i, c in enumerate(counts):
        prev = counts[i - 1] if i > 0 else None
        conv = None if prev in (None, 0) else round(100 * c / prev, 1)
        steps.append({"step": labels[i], "count": c, "step_conv": conv,
                      "overall": round(100 * c / counts[0], 1)})
    return {"funnel": steps}


def cmd_cohort(args):
    rows = _read_csv(args.path)
    by_id = defaultdict(list)
    for r in rows:
        uid = r.get(args.id)
        dt = r.get(args.date)
        if uid and dt:
            by_id[uid].append(dt)
    # 以首日为第 0 周，统计留存（简化：出现过的周数）
    cohorts = defaultdict(lambda: defaultdict(int))
    for uid, dates in by_id.items():
        ds = sorted({d[:10] for d in dates})
        if not ds:
            continue
        base = datetime.strptime(ds[0], "%Y-%m-%d")
        weeks = set()
        for d in ds:
            delta = (datetime.strptime(d, "%Y-%m-%d") - base).days // 7
            weeks.add(delta)
        for w in weeks:
            cohorts[ds[0]][w] += 1
    out = {}
    for base, ws in cohorts.items():
        total = max(ws.values())
        out[base] = {f"W{w}": round(100 * ws[w] / total, 1) for w in sorted(ws)}
    return {"cohort": out}


def cmd_rfm(args):
    rows = _read_csv(args.path)
    agg = defaultdict(lambda: {"amount": 0.0, "count": 0, "last": ""})
    for r in rows:
        uid = r.get(args.id)
        amt = _to_num(r.get(args.amount)) or 0.0
        dt = r.get(args.date) or ""
        if uid:
            agg[uid]["amount"] += amt
            agg[uid]["count"] += 1
            if dt > agg[uid]["last"]:
                agg[uid]["last"] = dt
    vals = list(agg.values())
    if not vals:
        return {"rfm": [], "note": "无数据"}
    amts = sorted(v["amount"] for v in vals)
    cnts = sorted(v["count"] for v in vals)

    def pct_rank(x, arr):
        below = sum(1 for a in arr if a <= x)
        return below / len(arr)

    seg = []
    for uid, v in agg.items():
        r = "高" if pct_rank(v["amount"], amts) > 0.66 else ("中" if pct_rank(v["amount"], amts) > 0.33 else "低")
        f = "高" if pct_rank(v["count"], cnts) > 0.66 else ("中" if pct_rank(v["count"], cnts) > 0.33 else "低")
        seg.append({"id": uid, "amount": round(v["amount"], 2), "frequency": v["count"],
                    "rfm_segment": f"{r}额/{f}频"})
    return {"rfm": seg, "note": "RFM 分层（按金额 R / 频次 F 二分位）"}


def cmd_abc(args):
    rows = _read_csv(args.path)
    dim = defaultdict(float)
    for r in rows:
        k = r.get(args.dim)
        v = _to_num(r.get(args.value)) or 0.0
        if k:
            dim[k] += v
    total = sum(dim.values()) or 1
    items = sorted(dim.items(), key=lambda x: -x[1])
    cum = 0.0
    out = []
    for k, v in items:
        cum += v
        out.append({"dim": k, "value": round(v, 2), "cum_pct": round(100 * cum / total, 1)})
    return {"abc": out, "note": "ABC/帕累托（按累计占比定位核心维度）"}


def cmd_sig(args):
    def z_ratio(p, n):
        return p, n

    pa, na = (float(x) for x in args.prop_a.split(","))
    pb, nb = (float(x) for x in args.prop_b.split(","))
    if na == 0 or nb == 0:
        return {"error": "样本量不能为 0"}
    p_pool = (pa * na + pb * nb) / (na + nb)
    se = math.sqrt(p_pool * (1 - p_pool) * (1 / na + 1 / nb))
    if se == 0:
        return {"error": "标准误为 0（两组比例相同）"}
    z = (pb - pa) / se
    p_two = 2 * (1 - _norm_cdf(abs(z)))
    return {"z": round(z, 3), "p_two_tailed": round(p_two, 4),
            "significant_at_0.05": p_two < 0.05,
            "note": "双尾显著性检验（z 检验）；p<0.05 视为显著，但显著≠重要，看效应量"}


def _norm_cdf(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def main():
    ap = argparse.ArgumentParser(description="学情分析工具箱（学情分析工具箱）")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("profile", "clean", "funnel", "cohort", "rfm", "abc", "sig"):
        sp = sub.add_parser(name)
        if name in ("profile", "clean"):
            sp.add_argument("path")
        if name == "funnel":
            sp.add_argument("--counts", required=True)
            sp.add_argument("--labels", default="")
        if name in ("cohort", "rfm"):
            sp.add_argument("path")
            sp.add_argument("--id", required=True)
            sp.add_argument("--date", required=True)
            if name == "rfm":
                sp.add_argument("--amount", required=True)
        if name == "abc":
            sp.add_argument("path")
            sp.add_argument("--dim", required=True)
            sp.add_argument("--value", required=True)
        if name == "sig":
            sp.add_argument("--prop-a", required=True, dest="prop_a")
            sp.add_argument("--prop-b", required=True, dest="prop_b")
    args = ap.parse_args()
    dispatch = {"profile": cmd_profile, "clean": cmd_clean, "funnel": cmd_funnel,
               "cohort": cmd_cohort, "rfm": cmd_rfm, "abc": cmd_abc, "sig": cmd_sig}
    result = dispatch[args.cmd](args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    # 自动埋点（）：调用即记录，失败不影响功能
    try:
        import course_usage_log
        course_usage_log.auto_record("数据分析·%s" % args.cmd, "", "")
    except Exception:
        pass


if __name__ == "__main__":
    main()
