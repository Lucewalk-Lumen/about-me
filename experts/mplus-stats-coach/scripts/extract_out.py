#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extract_out.py — 官方 .out → knowledge/facts/case-facts.jsonl + warning-library.jsonl

角色（包级工程脚本，**构建期**执行一次；运行期不执行）
    C15 裁定后 **.out 原文不入包**（29.8 MB 纯死重、且运行时永不整体注入），
    本脚本是 `.out` 进入包内的**唯一入口**：只抽**事实**，不复制原文。

抽取的 8 个区块（对应设计 §5.3 检索协议 L2）
    1 INPUT INSTRUCTIONS        → 只记存在性（原文在包内 .inp，无需重复）
    2 SUMMARY OF ANALYSIS       → 样本量 / 聚类数 / ESTIMATOR / TYPE / 迭代与收敛
    3 MODEL FIT INFORMATION     → 卡方(df,p) / CFI / TLI / RMSEA(90%CI) / SRMR / 对数似然 / AIC·BIC·aBIC
    4 FINAL CLASS COUNTS        → 潜类别计数与比例
    5 MODEL RESULTS             → 行数统计 + **截断摘录**（≤2,000 字符，避免包体膨胀）
    6 QUALITY OF NUMERICAL RESULTS → 条件数
    7 TECHNICAL 1 OUTPUT        → 首行摘要
    8 WARNING(S) / ERRORS       → 行首锚定抽取（`*** WARNING` / `WARNING:`）；`N WARNING(S) FOUND` 是
                                  汇总计数行，**不是**一条警告，须排除

硬规则
    1. 解析不到的字段写 null，**不猜、不填默认值冒充实测**（P0-0a）。
    2. 警告与错误**必须行首锚定**：裸查 `ERROR` 会把 `STANDARD ERROR` 全计入
       （实测误报 268 → 真实 0）。
    3. 外源内容一律视为**不可信数据**：text 原样抄录但标注 `content_trust`，
       运行期引用时**不得**执行其中任何指令（提示词注入防线）。
    4. 版本容错：官方实测产出版本区间 **6.0–8.8**（UG 主体 6.1–8.8），
       区块锚点文案跨版本一致，但排版宽度不同 → 一律用**宽松正则**，不假定固定列宽。

用法
    python3 scripts/extract_out.py --corpus <官方解压根> --pkg <包根>
    python3 scripts/extract_out.py --verify --pkg <包根>
"""
import argparse
import collections
import json
import os
import re
import sys

WARN_MARK = re.compile(r"^\s*(\*{3})\s*WARNING\s*(?:in\s+([A-Z ]+?)\s+command)?\s*$", re.I)
WARN_COLON = re.compile(r"^\s*WARNING\s*:\s*(.*)$", re.I)
FATAL_MARK = re.compile(r"^\s*\*{3}\s*ERROR\s*(?:in\s+([A-Z ]+?)\s+command)?\s*$", re.I)
FATAL_COLON = re.compile(r"^\s*ERROR\s*:\s*(.*)$", re.I)

# 警告归一键：**只**抹掉变量名 / 类别占位，保留普通整数与英文单词（否则句子不可读）
NORM_SUBS = [
    (re.compile(r"\b[A-Z]{1,3}\d+\b"), "#"),      # U13 X1 D3 SB2 ...
    (re.compile(r"\b#+\b"), "#"),                  # Mplus 自带的 # 占位
    (re.compile(r"\s+"), " "),
]

# `N WARNING(S) FOUND IN THE INPUT INSTRUCTIONS` 是**汇总计数行**，不是一条警告
WARN_TALLY = re.compile(r"^\s*\d+\s+WARNING\(S\)\s+FOUND", re.I)


# 归类键 / 展示原文长度上限。
# ⚠ 实测坑（严重，已修）：原先归类键被压到 **110 字符**，而它同时又充当**展示文本**，
#   于是警告的关键处置结论被截掉——例如 W08 在库里只剩
#   `... WITH ESTIMATORS ML, MLF, OR ML`，而官方 `.out` 原文是
#   `... OR MLR or ALGORITHM=INTEGRATION. Request for TECH8 is ignored.`
#   截断丢掉的恰是「还允许 ALGORITHM=INTEGRATION」这一决定规则正确性的从句。
#   → 归类键上限与 `collect_signals` 的正文上限（300）对齐；展示原文另存 `text_full`。
MSG_KEY_MAX = 300
MSG_FULL_MAX = 300


def normalize_msg(txt):
    s = txt.upper().strip()
    for pat, rep in NORM_SUBS:
        s = pat.sub(rep, s)
    return re.sub(r"\s+", " ", s).strip(" #.")[:MSG_KEY_MAX]


def block(text, start_pat, end_pats, limit=None):
    """截取 [start, 最近的一个 end) 区间；找不到返回 None。"""
    m = re.search(start_pat, text, re.I | re.M)
    if not m:
        return None
    s = m.end()
    e = len(text)
    for ep in end_pats:
        m2 = re.search(ep, text[s:], re.I | re.M)
        if m2 and s + m2.start() < e:
            e = s + m2.start()
    seg = text[s:e]
    return seg[:limit] if limit else seg


def num(pattern, text, group=1, cast=float):
    """取第 group 个捕获组并转型；不匹配返回 None（**绝不填默认值**）。group 可用命名组名。"""
    m = re.search(pattern, text, re.I | re.M)
    if not m:
        return None
    try:
        v = m.group(group)
    except IndexError:
        return None
    if v is None:
        return None
    try:
        return cast(v)
    except (TypeError, ValueError):
        return None


def parse_fit(text):
    """从 MODEL FIT INFORMATION 区块抽拟合指标。缺项一律 null，不猜。

    ⚠ 实现级坑（已实测）：Mplus 在子标题与数值之间**夹空行**
    （`RMSEA (...)` \\n \\n `          Estimate   0.012`），
    故所有模式一律用 `\\s+`（可跨行、跨空行），**不得**用 `\\n\\s*` 或先切块再匹配。
    """
    seg = block(text, r"^MODEL FIT INFORMATION",
                [r"^MODEL RESULTS", r"^FINAL CLASS COUNTS", r"^TECHNICAL \d", r"^QUALITY OF"])
    if seg is None:
        seg = text  # 少数输出无该段（如纯 MONTECARLO），退化为全文宽松匹配
    fit = {
        "chi2": None, "df": None, "p": None,
        "chi2_corrected": None, "scaling_correction_factor": None,
        "cfi": None, "tli": None,
        "rmsea": None, "rmsea_ci90": None, "rmsea_pclose": None,
        "srmr": None, "wrmr": None,
        "loglik_h0": None, "loglik_h1": None,
        "aic": None, "bic": None, "abic": None,
        "n_free_params": None,
    }
    # 卡方：**必须排除** "Chi-Square Test of Model Fit for the Baseline Model"。
    # ⚠ 实测坑：MLM/MLR/WLSMV 的卡方值**带 `*` 后缀**（`Value  69.697*`），
    #    正则若不吞掉该星号，后续 Degrees of Freedom 就匹配不上（实测漏失 36 份）。
    #    星号本身有语义：表示该卡方**需用 Scaling Correction Factor 校正**。
    # ⚠ 用**命名组**而非序号组：本模式会被反复拼接，序号组一改就取错值（实测踩过）。
    CHI = (r"Chi-Square Test of Model Fit(?!\s+for)\s+Value\s+"
           r"(?P<chi2>-?[0-9.]+)\s*(?P<corr>\*?)")
    m = re.search(CHI, seg, re.I)
    if m:
        fit["chi2"] = float(m.group("chi2"))
        fit["chi2_corrected"] = bool(m.group("corr"))
    fit["df"] = num(CHI + r"\s+Degrees of Freedom\s+(?P<df>[0-9]+)", seg, group="df", cast=int)
    fit["p"] = num(CHI + r"\s+Degrees of Freedom\s+[0-9]+\s+P-Value\s+(?P<pval>-?[0-9.]+)",
                  seg, group="pval")
    fit["scaling_correction_factor"] = num(
        CHI + r"\s+Degrees of Freedom\s+[0-9]+\s+P-Value\s+-?[0-9.]+\s+"
              r"Scaling Correction Factor\s+(?P<scf>-?[0-9.]+)", seg, group="scf")
    fit["loglik_h0"] = num(r"H0 Value\s+(-?[0-9.]+)", seg)
    fit["loglik_h1"] = num(r"H1 Value\s+(-?[0-9.]+)", seg)
    fit["aic"] = num(r"Akaike \(AIC\)\s+(-?[0-9.]+)", seg)
    fit["bic"] = num(r"Bayesian \(BIC\)\s+(-?[0-9.]+)", seg)
    fit["abic"] = num(r"Sample-Size Adjusted BIC\s+(-?[0-9.]+)", seg)
    fit["rmsea"] = num(r"RMSEA[^\n]*\s+Estimate\s+(-?[0-9.]+)", seg)
    m = re.search(r"90 Percent C\.?I\.?\s+(-?[0-9.]+)\s+(-?[0-9.]+)", seg, re.I)
    if m:
        fit["rmsea_ci90"] = [float(m.group(1)), float(m.group(2))]
    fit["rmsea_pclose"] = num(r"Probability RMSEA <= \.05\s+(-?[0-9.]+)", seg)
    fit["srmr"] = num(r"SRMR[^\n]*\s+Value\s+(-?[0-9.]+)", seg)
    fit["wrmr"] = num(r"WRMR[^\n]*\s+Value\s+(-?[0-9.]+)", seg)
    # CFI/TLI 是同行成对表头，用行首锚定
    fit["cfi"] = num(r"^\s*CFI\s+(-?[0-9.]+)\s*$", seg)
    fit["tli"] = num(r"^\s*TLI\s+(-?[0-9.]+)\s*$", seg)
    fit["n_free_params"] = num(r"Number of Free Parameters\s+([0-9]+)", seg, cast=int)
    return fit


def parse_summary(text):
    seg = block(text, r"^SUMMARY OF ANALYSIS",
                [r"^SUMMARY OF DATA", r"^SUMMARY OF CATEGORICAL", r"^UNIVARIATE", r"^MODEL FIT",
                 r"^MODEL RESULTS", r"^THE MODEL ESTIMATION", r"^INPUT INSTRUCTIONS"])
    src = seg if seg is not None else text
    return {
        "observations": num(r"Number of observations\s+([0-9]+)", src, cast=int),
        "clusters": num(r"Number of clusters\s+([0-9]+)", src, cast=int),
        "groups": num(r"Number of groups\s+([0-9]+)", src, cast=int),
        "estimator": (re.search(r"^\s*Estimator\s+(\S+)", src, re.I | re.M).group(1)
                      if re.search(r"^\s*Estimator\s+(\S+)", src, re.I | re.M) else None),
        "type_of_analysis": (re.search(r"^\s*Type of Analysis\s+(.+)$", src, re.I | re.M).group(1).strip()
                             if re.search(r"^\s*Type of Analysis\s+(.+)$", src, re.I | re.M) else None),
        "n_free_params": num(r"Number of Free Parameters\s+([0-9]+)", src, cast=int),
        "iterations": num(r"Number of Iterations\s+([0-9]+)", src, cast=int),
    }


def parse_class_counts(text):
    """FINAL CLASS COUNTS AND PROPORTIONS ... ;返回 [{class, count, proportion}] 或 null。"""
    seg = block(text, r"^FINAL CLASS COUNTS AND PROPORTIONS",
                [r"^CLASSIFICATION", r"^MODEL RESULTS", r"^TECHNICAL \d", r"^QUALITY OF",
                 r"^FINAL CLASS COUNTS AND PROPORTIONS FOR THE LATENT CLASS INDICATOR", r"\Z"])
    if not seg:
        return None
    rows = []
    for line in seg.splitlines():
        m = re.match(r"^\s*(\d+)\s+([0-9.]+)\s+([0-9.]+)\s*$", line)
        if m:
            rows.append({"class": int(m.group(1)), "count": float(m.group(2)),
                         "proportion": float(m.group(3))})
    return rows or None


def parse_qnr(text):
    seg = block(text, r"^QUALITY OF NUMERICAL RESULTS",
                [r"^TECHNICAL \d", r"^MODEL RESULTS", r"^WARNING", r"\Z"])
    if not seg:
        return None
    return {
        "condition_number": num(r"Condition Number for the Information Matrix\s+([0-9.eE+-]+)", seg),
    }


def parse_tech1(text):
    seg = block(text, r"^TECHNICAL 1 OUTPUT",
                [r"^TECHNICAL 2 OUTPUT", r"^WARNING", r"^QUALITY OF", r"^MODEL RESULTS", r"\Z"], limit=400)
    if not seg:
        return None
    head = next((l.strip() for l in seg.splitlines() if l.strip()), None)
    return {"head": head}


def parse_results(text, limit=2000):
    seg = block(text, r"^MODEL RESULTS(?:\s+FOR\s+)?(?=.*$)",
                [r"^TECHNICAL \d", r"^QUALITY OF", r"^WARNING", r"^SAVEDATA", r"^PLOT", r"\Z"])
    if not seg:
        return None, None
    lines = [l.rstrip() for l in seg.splitlines()]
    rows = sum(1 for l in lines if re.match(r"^\s*\S+\s+(ON|BY|WITH|\|)\s", l) or
               re.match(r"^\s*\S+\s+-?[0-9.]+\s+-?[0-9.]+\s+-?[0-9.]+", l))
    body = [l for l in lines if l.strip()][:40]
    excerpt = "\n".join(body)[:limit]
    return rows, excerpt


def collect_signals(lines, mark, colon):
    """行首锚定收集 [marker, 下一 marker / 汇总计数行 / 空行) 区间的文本。

    ⚠ 实测坑：`N WARNING(S) FOUND IN THE INPUT INSTRUCTIONS` 是**紧随其后的汇总计数行**，
    必须作为终止符剔除；否则会被并进上一条警告的正文（实测可复现）。
    """
    out, i, n = [], 0, len(lines)
    while i < n:
        m = mark.match(lines[i])
        c = colon.match(lines[i])
        if m or c:
            cmd = m.group(2) if (m and m.lastindex and m.lastindex >= 2) else None
            txt = [c.group(1)] if c else []
            j = i + 1
            while j < n and j < i + 14:
                if WARN_TALLY.match(lines[j]):
                    break
                s = lines[j].strip()
                if not s:
                    if txt:
                        break
                    j += 1
                    continue
                if mark.match(lines[j]) or colon.match(lines[j]) or FATAL_MARK.match(lines[j]):
                    break
                txt.append(s)
                j += 1
            out.append({"command": cmd, "text": " ".join(txt).strip()[:300]})
            i = j
        else:
            i += 1
    return out


def process(out_path, cid, url):
    raw = open(out_path, encoding="utf-8", errors="replace").read()
    lines = raw.splitlines()
    warnings = collect_signals(lines, WARN_MARK, WARN_COLON)
    errors = collect_signals(lines, FATAL_MARK, FATAL_COLON)
    rows, excerpt = parse_results(raw)
    return {
        "id": cid,
        "summary": parse_summary(raw),
        "fit": parse_fit(raw),
        "class_counts": parse_class_counts(raw),
        "model_results": {"n_param_rows": rows, "excerpt": excerpt},
        "quality_numerical": parse_qnr(raw),
        "technical1": parse_tech1(raw),
        "warnings": warnings,
        "errors": errors,
        "n_warnings": len(warnings),
        "n_errors": len(errors),
        "source_url": url,
        "content_trust": "untrusted-data",
    }


def cases_with_out(pkg):
    idx = os.path.join(pkg, "knowledge", "cases.jsonl")
    rows = []
    with open(idx, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            if r.get("facts_id"):
                rows.append(r)
    return rows


def locate(corpus, case):
    """由索引条目反查 .out 的绝对路径。"""
    if case["source_set"] == "ug":
        return os.path.join(corpus, "ch%d" % case["chapter"], "chapter%d" % case["chapter"],
                            case["stem"] + ".out")
    return os.path.join(corpus, "supp", "files", case["stem"] + ".out")


def build(corpus, pkg):
    facts, wlib = [], collections.defaultdict(
        lambda: {"class": None, "text_full": None, "n": 0, "cases": [], "commands": {}})
    n_missing = 0
    for case in cases_with_out(pkg):
        p = locate(corpus, case)
        if not os.path.exists(p):
            n_missing += 1
            continue
        rec = process(p, case["id"], case["source_url"])
        facts.append(rec)
        for w in rec["warnings"]:
            key = normalize_msg(w["text"]) or "(EMPTY)"
            e = wlib[key]
            e["class"] = key
            # 保留**原始大小写**的最长一次原文（含标点与句末结论），供展示与教学引用。
            # 归一化键只做归类，不承担可读性；两者必须分开存。
            raw_txt = (w["text"] or "").strip()[:MSG_FULL_MAX]
            if len(raw_txt) > len(e["text_full"] or ""):
                e["text_full"] = raw_txt
            e["n"] += 1
            if case["id"] not in e["cases"]:
                e["cases"].append(case["id"])
            cmd = w["command"] or "(none)"
            e["commands"][cmd] = e["commands"].get(cmd, 0) + 1

    fdir = os.path.join(pkg, "knowledge", "facts")
    os.makedirs(fdir, exist_ok=True)
    with open(os.path.join(fdir, "case-facts.jsonl"), "w", encoding="utf-8") as f:
        for r in facts:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    lib = sorted(wlib.values(), key=lambda e: -e["n"])
    with open(os.path.join(fdir, "warning-library.jsonl"), "w", encoding="utf-8") as f:
        for i, e in enumerate(lib, 1):
            e["wclass_id"] = "W%02d" % i
            e["cases"] = sorted(set(e["cases"]))
            e["n_cases"] = len(e["cases"])
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    return facts, lib, n_missing


def verify(pkg):
    fdir = os.path.join(pkg, "knowledge", "facts")
    fails, notes = [], []
    for name in ("case-facts.jsonl", "warning-library.jsonl"):
        p = os.path.join(fdir, name)
        if not os.path.exists(p):
            fails.append("FAIL 缺 %s" % name)
            continue
        n = 0
        with open(p, encoding="utf-8") as f:
            for i, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    json.loads(line)
                    n += 1
                except json.JSONDecodeError as e:
                    fails.append("FAIL %s 第 %d 行非法 JSON：%s" % (name, i, e))
        notes.append("%s = %d 条" % (name, n))

    cf = os.path.join(fdir, "case-facts.jsonl")
    idx = os.path.join(pkg, "knowledge", "cases.jsonl")
    if os.path.exists(cf) and os.path.exists(idx):
        with open(idx, encoding="utf-8") as f:
            want = {json.loads(l)["id"] for l in f if l.strip() and json.loads(l).get("facts_id")}
        with open(cf, encoding="utf-8") as f:
            got = {json.loads(l)["id"] for l in f if l.strip()}
        miss = want - got
        extra = got - want
        if miss:
            fails.append("FAIL case-facts 缺少 %d 条（例：%s）" % (len(miss), sorted(miss)[:3]))
        if extra:
            fails.append("FAIL case-facts 多出 %d 条（索引里没有 facts_id）" % len(extra))
        if not miss and not extra:
            notes.append("case-facts 与索引 facts_id 集合一致（%d 条）" % len(got))
    # 反编造：任一条目若声称有 .out 则 source_url 必须非空
    if os.path.exists(cf):
        bad = []
        with open(cf, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                r = json.loads(line)
                if not r.get("source_url"):
                    bad.append(r["id"])
        if bad:
            fails.append("FAIL 缺 source_url：%d 条" % len(bad))

    # 警告库门禁：① 长度**恰好等于**上限 = 已被截断（本次修复的缺陷，必须能被检出）；
    #            ② `text_full` 必须存在且非空（承接展示职责）。
    wl = os.path.join(fdir, "warning-library.jsonl")
    if os.path.exists(wl):
        trunc, nofull = [], []
        with open(wl, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                r = json.loads(line)
                if len(r.get("class") or "") >= MSG_KEY_MAX:
                    trunc.append(r.get("wclass_id"))
                if not (r.get("text_full") or "").strip():
                    nofull.append(r.get("wclass_id"))
        if trunc:
            fails.append("FAIL 警告类文本疑似截断（长度达上限 %d）：%s" % (MSG_KEY_MAX, trunc[:5]))
        if nofull:
            fails.append("FAIL 警告类缺 text_full 原文：%s" % nofull[:5])
        if not trunc and not nofull:
            notes.append("警告库无截断、text_full 齐备")
    return len(fails), fails + notes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus")
    ap.add_argument("--pkg", required=True)
    ap.add_argument("--verify", action="store_true")
    args = ap.parse_args()
    pkg = os.path.abspath(args.pkg)

    if args.verify:
        rc, lines = verify(pkg)
        for l in lines:
            print(l)
        print("VERIFY %s" % ("OK" if rc == 0 else "FAILED"))
        return 1 if rc else 0
    if not args.corpus:
        print("ERROR: 非 --verify 模式必须给 --corpus", file=sys.stderr)
        return 2

    facts, lib, n_missing = build(os.path.abspath(args.corpus), pkg)
    n_fit = sum(1 for r in facts if r["fit"]["cfi"] is not None or r["fit"]["rmsea"] is not None)
    n_warn = sum(1 for r in facts if r["n_warnings"])
    n_err = sum(1 for r in facts if r["n_errors"])
    n_obs = sum(1 for r in facts if r["summary"]["observations"] is not None)
    print("case-facts.jsonl = %d 条（.out 缺失 %d 条）" % (len(facts), n_missing))
    print("  with_fit_indices=%d  with_observations=%d  with_warning=%d  with_error=%d"
          % (n_fit, n_obs, n_warn, n_err))
    print("warning-library.jsonl = %d 类" % len(lib))
    print("  top: " + " | ".join("%s:%d/%dc" % (e["wclass_id"], e["n"], e["n_cases"]) for e in lib[:6]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
