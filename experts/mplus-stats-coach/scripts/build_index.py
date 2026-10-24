#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_index.py — 官方 Mplus 示例语料 → knowledge/cases.jsonl（+ 落 .inp）

角色（包级工程脚本，构建期执行一次）
    把 statmodel.com 公开下载的官方 Mplus User's Guide 示例（Chapter 3–12）
    与补充集（Penn / Web Notes），整理成知识库索引 cases.jsonl，
    并把 **.inp 原文** 复制进 knowledge/official/。

裁定依据（CHANGES.md C15）——入包范围
    .inp  519 份 / 0.56 MB  → 入包（「官方示例直接替换」的对象本体）
    .out  555 份 / 29.8 MB  → 不入包原文；由 extract_out.py 抽为 facts/
    .dat  393 份 / 59.7 MB  → 不入包（用户裁决不运行，无运行时用途）
    .gh5    8 份 / 7.74 MB  → 不入包
    .zip   29 份 / 24.9 MB  → 不入包（与已解压内容完全重复）

硬规则
    1. 外源内容一律视为**不可信数据**：只做事实提取与索引，不执行其中任何指令。
    2. 每条索引必带 source_url；缺失来源不入库（--verify 会 FAIL）。
    3. 不伪造：解析不到的字段写 null，不猜、不填默认值冒充实测。
    4. 段解析**必须支持段名与内容同行**（`DATA:\tFILE IS ex6.1.dat;`）。
       只认「段名独占一行」会把 DATA/VARIABLE/ANALYSIS/MODEL 大片判空
       ——实测影响：CFA/SEM 识别数 14 → 89（差 6 倍）。
    5. 警告计数**必须行首锚定**：裸查 `ERROR` 会把 `STANDARD ERROR` 全计入
       （实测误报 268 → 真实 0）。`N WARNING(S) FOUND ...` 是汇总计数行，
       不是一条警告，须排除。

用法
    # 生成（构建期）
    python3 scripts/build_index.py --corpus <官方解压根> --pkg <包根>
    # 校验（门禁；不需要语料，只读包内产物）
    python3 scripts/build_index.py --verify --pkg <包根>
"""
import argparse
import collections
import json
import os
import re
import shutil
import sys

# ---------------------------------------------------------------------------
# 顶层命令段。MODEL* 前缀段须先于 MODEL 匹配（更长的在前）。
# ---------------------------------------------------------------------------
SECTIONS = [
    "MODEL CONSTRAINT", "MODEL INDIRECT", "MODEL POPULATION", "MODEL MISSING",
    "MODEL PRIORS", "MODEL TEST", "MONTECARLO", "SAVEDATA", "ANALYSIS",
    "VARIABLE", "OUTPUT", "PLOT", "DEFINE", "COVERAGE", "TITLE", "DATA",
    "MODEL", "RELIABILITY",
]
SEC_RE = re.compile(r"^\s*(" + "|".join(SECTIONS) + r")\s*:\s*(.*)$", re.I)

CHAPTER_NAMES = {
    3: "Regression and Path Analysis",
    4: "Exploratory Factor Analysis",
    5: "Confirmatory Factor Analysis and Structural Equation Modeling",
    6: "Growth Modeling and Survival Analysis",
    7: "Mixture Modeling with Cross-Sectional Data",
    8: "Mixture Modeling with Longitudinal Data",
    9: "Multilevel Modeling with Complex Survey Data",
    10: "Multilevel Mixture Modeling",
    11: "Missing Data Modeling and Bayesian Analysis",
    12: "Monte Carlo Simulation Studies",
}
BASE_URL = "https://www.statmodel.com/usersguide/chapter{n}.shtml"
SUPP_URL = "https://www.statmodel.com/download/{n}"

# .out **结构性大段**（仅存在性判定，抽正文归 extract_out.py）。
# 这些段名是 Mplus 固定表头，全大写、独占一行，裸子串匹配无假阳性风险。
OUT_BLOCKS = {
    "input_instructions": "INPUT INSTRUCTIONS",
    "summary_of_analysis": "SUMMARY OF ANALYSIS",
    "model_fit": "MODEL FIT INFORMATION",
    "class_counts": "FINAL CLASS COUNTS AND PROPORTIONS",
    "model_results": "MODEL RESULTS",
    "quality_numerical": "QUALITY OF NUMERICAL RESULTS",
    "technical1": "TECHNICAL 1 OUTPUT",
}

# ⚠ 口径纪律（硬约束）：`warnings` / `errors` / `terminated_normally` 三个语义键
#   **禁止使用裸子串匹配**，必须走下方锚定口径。理由是实测出来的，不是风格偏好 ——
#
#   · `errors`：裸 "ERROR" 在官方 555 份 .out 中命中 **312 份（56%）**，
#     而行首锚定的 `*** ERROR` 命中 **0 份**。即 **100% 是假阳性**。
#     成因（含 `ERROR` 但无致命标记的首个命中行，按频次）：
#       `RMSEA (Root Mean Square Error Of Approximation)`  ×168
#       `Error messages for each replication (if any)`     ×112   （蒙特卡洛输出）
#       `CORRELATIONS AND MEAN SQUARE ERROR OF THE TRUE…`  ×20
#       `THE STANDARD ERRORS OF THE MODEL PARAMETER…`      ×6
#     若沿用裸子串，`cases.jsonl` 里 `out_blocks.errors=true` 会被下游
#     读成「这份输出报了错」—— 与证据相反，属 **P0-0a 编造统计结果** 风险。
#
#   · `warnings`：裸 "WARNING" 命中 117 份，行首锚定亦 117 份，**数值一致**
#     （`WARNING(S) FOUND IN THE INPUT INSTRUCTIONS` 也只出现在真有警告的文件里）。
#     即当前无偏差，但**仍统一改用锚定口径** —— 语料一旦扩充，裸匹配随时可能
#     吃进正文里的 "warning" 字样而造成口径分裂。
#
#   · `terminated_normally`：本就直接复用 `terminated` 变量，与下文字段同源，
#     不存在分裂；显式写出是为了让三个键出现在同一处、便于审阅。
#
# 行首锚定的警告标记（排除 "N WARNING(S) FOUND IN THE INPUT INSTRUCTIONS"）
WARN_MARK = re.compile(r"^\s*(?:\*{3}\s*WARNING|WARNING\s*:)", re.I)
# 行首锚定的致命错误标记。实测官方 555 份 .out 中 0 例命中。
FATAL_MARK = re.compile(r"^\s*\*{3}\s*ERROR", re.I)

VERSION_RE = re.compile(r"^\s*(Mplus\s+VERSION\s+([0-9][0-9.]*)|Mplus\s+(DEVELOPMENT))", re.I)
DATE_RE = re.compile(r"^\s*(\d{2}/\d{2}/\d{4})\s")


def strip_comments(raw):
    """剥离 `!` 行注释（Mplus 注释自 `!` 起至行尾，不做引号内豁免）。"""
    return "\n".join(re.sub(r"!.*$", "", line) for line in raw.splitlines())


def parse_sections(text):
    """切顶层段。支持段名与内容同行，也支持段名独占一行后跟多行内容。"""
    out = collections.OrderedDict()
    cur = None
    for line in text.splitlines():
        m = SEC_RE.match(line)
        if m:
            cur = m.group(1).strip().upper()
            rest = m.group(2)
            out[cur] = [rest] if rest.strip() else []
        elif cur is not None:
            out[cur].append(line)
    return {k: "\n".join(v) for k, v in out.items()}


def detect_families(text, sec):
    """基于已剥注释、已切段文本判定模型族。词边界敏感，避免子串误命中。"""
    A = sec.get("ANALYSIS", "")
    M = sec.get("MODEL", "")
    V = sec.get("VARIABLE", "")
    U = text.upper()
    types = " ".join(re.findall(r"TYPE\s*=\s*([A-Z0-9 ]+)", A, re.I)).upper()
    fams = set()

    classes = re.findall(r"^\s*CLASSES\s*=\s*([^;]+);", text, re.I | re.M)
    if classes:
        fams.add("MIXTURE")
        for c in classes:
            # 两个及以上潜类别变量（`c1(n) c2(n)`）= 潜在转变分析
            if len(re.findall(r"([A-Za-z_]\w*)\s*\(", c)) >= 2:
                fams.add("LTA")
    if re.search(r"%WITHIN%|%BETWEEN%", U) or "TWOLEVEL" in types:
        fams.add("MULTILEVEL")
    if "CROSSCLASSIFIED" in types:
        fams.add("CROSS_CLASSIFIED")
    if "EFA" in types:
        fams.add("EFA_ESEM")
    if "BAYES" in types or re.search(r"ESTIMATOR\s*=\s*BAYES", U):
        fams.add("BAYES")
    if "RANDOM" in types:
        fams.add("DSEM_RI")
    if re.search(r"^\s*[A-Za-z]\w*\s+[A-Za-z]\w*\s*\|", M, re.I | re.M) or re.search(r"\|\s*[A-Za-z]\w*@", M):
        fams.add("GROWTH")
    if re.search(r"\bBY\b", M, re.I):
        fams.add("CFA_SEM")
    if re.search(r"^\s*CLASSES\s*=\s*\w+\s*\(\s*\d", text, re.I | re.M) and "LTA" not in fams:
        fams.add("LCA_LPA")
    if re.search(r"\bXWITH\b", U):
        fams.add("MODERATION")
    if re.search(r"MODEL\s+INDIRECT", U):
        fams.add("MEDIATION")
    if re.search(r"MODEL\s+CONSTRAINT", U):
        fams.add("CONSTRAINT")
    if re.search(r"\bSURVIVAL\s*=", V, re.I):
        fams.add("SURVIVAL")
    if re.search(r"\bCENSORED\w*\s*=", V, re.I):
        fams.add("CENSORED")
    if re.search(r"\bCATEGORICAL\s*=", V, re.I):
        fams.add("CATEGORICAL")
    if re.search(r"\bCOUNT\s*=", V, re.I):
        fams.add("COUNT")
    if re.search(r"\bMISSING\s*=", V, re.I):
        fams.add("MISSING")
    if re.search(r"\bAUXILIARY\s*=", V, re.I):
        fams.add("AUXILIARY")
    if re.search(r"^\s*MONTECARLO\s*:", text, re.I | re.M):
        fams.add("MONTECARLO")
    if re.search(r"\bKNOWNCLASS\b", V, re.I):
        fams.add("KNOWNCLASS")
    return sorted(fams)


KEYWORD_PATS = {
    "TYPE=GENERAL": r"TYPE\s*=\s*GENERAL",
    "TYPE=MIXTURE": r"TYPE\s*=\s*MIXTURE",
    "TYPE=TWOLEVEL": r"TYPE\s*=\s*TWOLEVEL",
    "TYPE=RANDOM": r"TYPE\s*=\s*RANDOM",
    "TYPE=EFA": r"TYPE\s*=\s*EFA",
    "TYPE=IMPUTATION": r"TYPE\s*=\s*IMPUTATION",
    "ESTIMATOR=ML": r"ESTIMATOR\s*=\s*ML\b",
    "ESTIMATOR=MLR": r"ESTIMATOR\s*=\s*MLR",
    "ESTIMATOR=MLF": r"ESTIMATOR\s*=\s*MLF",
    "ESTIMATOR=WLSMV": r"ESTIMATOR\s*=\s*WLSMV",
    "ESTIMATOR=BAYES": r"ESTIMATOR\s*=\s*BAYES",
    "ESTIMATOR=MLM": r"ESTIMATOR\s*=\s*MLM\b",
    "ALGORITHM=INTEGRATION": r"ALGORITHM\s*=\s*INTEGRATION",
    "STARTS": r"^\s*STARTS\s*=",
    "PROCESSORS": r"PROCESSORS\s*=",
    "BOOTSTRAP": r"^\s*BOOTSTRAP\s*=",
    "TECH1": r"TECH1\b",
    "TECH8": r"TECH8\b",
    "TECH11": r"TECH11\b",
    "TECH14": r"TECH14\b",
    "MODINDICES": r"MODINDICES",
    "STANDARDIZED": r"STANDARDIZED",
    "CINTERVAL": r"CINTERVAL",
    "SAMPSTAT": r"SAMPSTAT",
    "MISSING=ALL": r"MISSING\s*=\s*ALL",
    "MISSING=MCAR": r"MISSING\s*=\s*MCAR",
    "USEVARIABLES": r"USEVARIABLES\s*=",
    "AUXILIARY": r"AUXILIARY\s*=",
    "DEFINE": r"^\s*DEFINE\s*:",
    "SAVEDATA": r"^\s*SAVEDATA\s*:",
    "PLOT": r"^\s*PLOT\s*:",
    "XWITH": r"\bXWITH\b",
    "CONSTRAINT": r"MODEL\s+CONSTRAINT",
    "INDIRECT": r"MODEL\s+INDIRECT",
    "PRIORS": r"MODEL\s+PRIORS",
    "LTA": r"\bLTA\b",
    "SURVIVAL": r"SURVIVAL",
    "KNOWNCLASS": r"KNOWNCLASS",
}


def detect_keywords(text):
    return sorted(k for k, p in KEYWORD_PATS.items() if re.search(p, text, re.I | re.M))


def read_title(sec):
    t = sec.get("TITLE", "")
    t = re.sub(r"\s+", " ", t).strip().rstrip(";")
    return t or None


def scan_out(path):
    """读 .out 的版本 / 日期 / 区块存在性 / 警告与致命错误计数。只做事实判定，不抽正文。"""
    txt = open(path, encoding="utf-8", errors="replace").read()
    lines = txt.splitlines()
    ver = dev = date = None
    for l in lines[:8]:
        m = VERSION_RE.match(l)
        if m:
            ver = m.group(2) or "DEVELOPMENT"
        if date is None:
            d = DATE_RE.match(l)
            if d:
                date = d.group(1)
    up = txt.upper()
    # 结构性大段的键序与 OUT_BLOCKS 定义序一致，三个语义键接在其后 —— 与旧版键序完全相同。
    blocks = {k: (v in up) for k, v in OUT_BLOCKS.items()}
    n_warn = sum(1 for l in lines if WARN_MARK.match(l))
    n_fatal = sum(1 for l in lines if FATAL_MARK.match(l))
    terminated = "TERMINATED NORMALLY" in up
    # 语义键走锚定口径（见 OUT_BLOCKS 上方口径纪律），不得回退为裸子串。
    blocks["warnings"] = n_warn > 0
    blocks["errors"] = n_fatal > 0
    blocks["terminated_normally"] = terminated
    # ⚠ 命名纪律（本轮实测修正）：此字段只表示**是否检出 `TERMINATED NORMALLY` 字样**，
    #   **不代表运行是否成功**。原先把「未检出」命名为 `NOT_TERMINATED_NORMALLY`，
    #   会让下游得出「这次运行没有正常结束」的结论 —— 与证据不符，属 P0-0a 风险。
    #   实测反证：38 份「未检出」文件**全部**含 `Ending Time` / `Elapsed Time` /
    #   `Elapsed Time` 与授权页脚，即**运行正常完成**；它们只是不打印那行回显
    #   （集中在 EFA / 蒙特卡洛类分析：`ex4.6`、`mcex4.7`、`mcex5.24-31`、`mcex6.7/6.16` …）。
    #   → 改名为中性的 `NO_TERMINATION_MARKER`，禁止再从该值推断运行成败。
    completed = ("ENDING TIME" in up) or ("ELAPSED TIME" in up)
    if n_fatal:
        status = "FATAL_ERROR"
    elif terminated:
        status = "NORMAL"
    elif completed:
        status = "NO_TERMINATION_MARKER"      # 跑完了，只是没打印那行
    else:
        status = "INCOMPLETE"                 # 无结束时间戳 → 文件可能被截断
    return {
        "version": ver,
        "date": date,
        "out_blocks": blocks,
        "warning_records": n_warn,
        "fatal_records": n_fatal,
        "out_status": status,
        "terminated_normally": terminated,
    }


def iter_inp(corpus):
    """产出 (source_set, chapter, group, abspath)。UG: ch3..ch12/chapterN/；补充集: supp/files/。"""
    for ch in range(3, 13):
        base = os.path.join(corpus, "ch%d" % ch)
        if not os.path.isdir(base):
            continue
        for root, _d, files in os.walk(base):
            for fn in sorted(files):
                if fn.lower().endswith(".inp"):
                    yield "ug", ch, None, os.path.join(root, fn)
    supp = os.path.join(corpus, "supp", "files")
    if os.path.isdir(supp):
        for fn in sorted(os.listdir(supp)):
            if fn.lower().endswith(".inp"):
                group = fn.split("__", 1)[0] if "__" in fn else "misc"
                yield "supp", None, group, os.path.join(supp, fn)


def build(corpus, pkg):
    cases = []
    copied = 0
    for source_set, ch, group, inp_path in iter_inp(corpus):
        fn = os.path.basename(inp_path)
        stem = os.path.splitext(fn)[0]
        root = os.path.dirname(inp_path)

        raw = open(inp_path, encoding="utf-8", errors="replace").read()
        text = strip_comments(raw)
        sec = parse_sections(text)
        is_mc = stem.lower().startswith("mcex") or "MONTECARLO" in sec

        # .inp 落盘（唯一入包的语料形态）
        if source_set == "ug":
            rel = "knowledge/official/ug/ch%d/%s" % (ch, fn)
            cid = "ug-ch%d-%s" % (ch, stem)
            ch_name = CHAPTER_NAMES.get(ch)
            url = BASE_URL.format(n=ch)
        else:
            rel = "knowledge/official/supp/%s" % fn
            cid = "supp-%s-%s" % (group, stem)
            ch_name = None
            url = SUPP_URL.format(n=fn.split("__", 1)[-1])
        dst = os.path.join(pkg, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(inp_path, dst)
        copied += 1

        out_path = os.path.join(root, stem + ".out")
        out_info = scan_out(out_path) if os.path.exists(out_path) else None

        # 数据文件以 .inp 的 DATA 段为准（不按文件名猜测）
        m = re.search(r"FILE\s*(?:IS|=)\s*([^;\s]+)", sec.get("DATA", ""), re.I)
        data_file = m.group(1).strip("\"'") if m else None
        if data_file and not os.path.exists(os.path.join(root, data_file)):
            data_file = None

        cases.append({
            "id": cid,
            "source_set": source_set,
            "kind": "montecarlo" if is_mc else "example",
            "chapter": ch,
            "chapter_name": ch_name,
            "group": group,
            "stem": stem,
            "title": read_title(sec),
            "model_families": detect_families(text, sec),
            "sections_used": sorted(sec.keys()),
            "keywords": detect_keywords(text),
            "inp_path": rel,
            "data_file": data_file,
            "out_version": out_info["version"] if out_info else None,
            "out_date": out_info["date"] if out_info else None,
            "out_blocks": out_info["out_blocks"] if out_info else {},
            "out_status": out_info["out_status"] if out_info else None,
            "warning_records": out_info["warning_records"] if out_info else None,
            "has_warning": bool(out_info and out_info["warning_records"]),
            "facts_id": cid if out_info else None,
            "source_url": url,
            "license_note": ("Official Mplus User's Guide example (publicly downloadable); "
                             "cited by source_url."),
            "content_trust": "untrusted-data",
        })

    idx_path = os.path.join(pkg, "knowledge", "cases.jsonl")
    os.makedirs(os.path.dirname(idx_path), exist_ok=True)
    with open(idx_path, "w", encoding="utf-8") as f:
        for c in cases:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    return cases, copied, idx_path


def verify(pkg):
    """门禁：只读包内产物，不需要语料。返回 (n_fail, lines)。"""
    fails, notes = [], []
    idx_path = os.path.join(pkg, "knowledge", "cases.jsonl")
    if not os.path.exists(idx_path):
        return 1, ["FAIL cases.jsonl 不存在"]
    rows = []
    with open(idx_path, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as e:
                fails.append("FAIL cases.jsonl 第 %d 行非法 JSON：%s" % (n, e))

    # 1) 每条必有 source_url
    no_url = [r["id"] for r in rows if not r.get("source_url")]
    if no_url:
        fails.append("FAIL 缺 source_url：%d 条（%s）" % (len(no_url), no_url[:3]))
    # 2) 每条 in p_path 必须真实存在且落在 knowledge/official/ 内
    missing, outside = [], []
    for r in rows:
        p = r.get("inp_path") or ""
        if not p.startswith("knowledge/official/"):
            outside.append(r["id"])
        elif not os.path.exists(os.path.join(pkg, p)):
            missing.append(r["id"])
    if outside:
        fails.append("FAIL inp_path 越界（必须落在 knowledge/official/）：%d 条" % len(outside))
    if missing:
        fails.append("FAIL inp_path 指向的文件不存在：%d 条（%s）" % (len(missing), missing[:3]))
    # 3) id 唯一
    dup = [k for k, v in collections.Counter(r["id"] for r in rows).items() if v > 1]
    if dup:
        fails.append("FAIL id 重复：%s" % dup[:3])
    # 4) facts_id 必须与 id 自洽（有 .out 才给 facts_id）
    bad_facts = [r["id"] for r in rows if r.get("facts_id") and r["facts_id"] != r["id"]]
    if bad_facts:
        fails.append("FAIL facts_id 与 id 不自洽：%d 条" % len(bad_facts))

    n = len(rows)
    notes.append("cases=%d  ug=%d  supp=%d  example=%d  montecarlo=%d  with_out=%d  with_warning=%d"
                 % (n,
                    sum(1 for r in rows if r["source_set"] == "ug"),
                    sum(1 for r in rows if r["source_set"] == "supp"),
                    sum(1 for r in rows if r["kind"] == "example"),
                    sum(1 for r in rows if r["kind"] == "montecarlo"),
                    sum(1 for r in rows if r["facts_id"]),
                    sum(1 for r in rows if r.get("has_warning"))))
    return len(fails), fails + notes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", help="官方解压根（构建期）")
    ap.add_argument("--pkg", required=True, help="包根目录")
    ap.add_argument("--verify", action="store_true", help="只校验包内产物，不需要 --corpus")
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
    cases, copied, idx = build(os.path.abspath(args.corpus), pkg)
    ex = sum(1 for c in cases if c["kind"] == "example")
    mc = sum(1 for c in cases if c["kind"] == "montecarlo")
    wo = sum(1 for c in cases if c["facts_id"])
    hw = sum(1 for c in cases if c["has_warning"])
    fam = collections.Counter()
    for c in cases:
        fam.update(c["model_families"])
    print("copied .inp = %d" % copied)
    print("cases.jsonl -> %s" % idx)
    print("  total=%d example=%d montecarlo=%d with_out=%d with_warning=%d"
          % (len(cases), ex, mc, wo, hw))
    print("  families: " + ", ".join("%s:%d" % kv for kv in fam.most_common()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
