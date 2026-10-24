#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_inp.py — Mplus `.inp` 静态校验（A 路径：零依赖、不运行 Mplus）

⚠ 覆盖率声明（P0-6，硬约束，**不得删除本段、不得改写为单一百分比**）
    只喂 `.inp` 时，本脚本**仅覆盖语法层**。官方实测警告共 **62 类 / 39 种消息 / 219 条**，
    本脚本已实现的规则覆盖：

        口径            已实现        语法层理论可预判
        ─────────────────────────────────────────────
        类键数（62）      14  (22.6%)   21  (33.9%)
        消息种类（39）     2  ( 5.1%)   11  (28.2%)
        出现条数（219）   30  (13.7%)   —  （未逐条核）

    ⚠ **三个口径差别极大（5.1% ↔ 28.2%），引用时必须写明是哪一口径**，
    只抛一个百分比即为不合格表述。
    另有 **9 种消息**（如 `STANDARDIZED` + `TYPE=EFA`、`TYPE=RANDOM` 无随机效应、
    `Duplicate` / 自指 `WITH`）在语法层**可预判但当前尚未实现**。
    数据层与运行层（其余约 28 种消息）需提供数据字典（`--dict <dict.json>`）
    或真实运行，本脚本**不覆盖**。
    **不得**在只喂 `.inp` 时宣称做了完整警告预判。

实测阈值（**两个阈值的实证性质不同，不得混为一谈**）
    · 变量名长度上限 = **8** 字符 —— **语法约束**
      依据：官方 519 份 `.inp` 全量展开 `NAMES` 后，变量名长度 1–8 字符、**最大恰为 8**、
      **超限 0 个**（约 3,054 个变量名）。正因语料守规，555 份 `.out` 中
      **没有**变量名截断警告样本 → **不得声称"必报截断警告"**，判 BLOCKER 的依据是语法约束本身。
    · 输入行宽上限 = **90** 字符 —— **输出阶段的截断警告**
      依据：官方 `.out` 的 `Input line exceeded 90 characters. Some input may be truncated.`
      （**4 份**报出）。但超限 `.inp` 共 **6** 份 → **仅 4 份报出**，
      `ex5.28`（95 字符）与 `ex5.32`（**131 字符**）均**未报** →
      ⚠ **阈值确证但触发不可预测**，故只判 WARN（命令行）/ INFO（TITLE），**不得承诺必报**。

不做什么（能力边界）
    · 不判断收敛、拟合优度、参数合理性 —— 需真实运行
    · 不做跨软件迁移（R lavaan / AMOS / Stata）

用法
    python3 check_inp.py <file.inp>
    python3 check_inp.py <file.inp> --dict <dict.json>
    python3 check_inp.py <file.inp> --json

退出码
    0  无 BLOCKER 级发现
    1  存在 BLOCKER 级发现（`--strict` 时 WARN 亦致 1）
    2  用法/读取错误
"""
import argparse
import json
import os
import re
import sys

VARNAME_MAX = 8      # 官方实测阈值
LINEWIDTH_MAX = 90   # 官方实测阈值

SECTIONS = [
    "TITLE", "DATA MISSING", "DATA IMPUTATION", "DATA TWOPART", "DATA",
    "VARIABLE", "DEFINE", "ANALYSIS", "MODEL",
    "MODEL INDIRECT", "MODEL CONSTRAINT", "MODEL PRIORS", "MODEL POPULATION",
    "MODEL MISSING", "MODEL TEST", "MODEL MONTECARLO", "MONTECARLO",
    "OUTPUT", "SAVEDATA", "PLOT", "COVERAGE", "RELIABILITY",
]
# ⚠ 实测坑：Mplus 还允许**带标签的变体**段名，见官方示例：
#     `MODEL C1:` `MODEL G2:` `MODEL CB:`（多组 / 多类别分别建模）
#     `DATA MISSING:` `DATA IMPUTATION:` `DATA TWOPART:`（数据的附加说明段）
#   若不接受这些变体，会把大量**合法**官方示例误判为「段名拼写错误」（实测 16 例误报）。
SECTION_ALT = ("(?:" + "|".join(sorted(SECTIONS, key=len, reverse=True)) + "|"
               r"MODEL\s+[A-Za-z0-9_]{1,8}|DATA\s+[A-Za-z]{3,14})")
SEC_RE = re.compile(r"^\s*(" + SECTION_ALT + r")\s*:\s*(.*)$", re.I)
ANY_SEC_RE = re.compile(r"^\s*([A-Za-z][A-Za-z0-9 ]{1,24}?)\s*:\s*(.*)$")
BASE_SEC = {s.upper() for s in SECTIONS}
PROSE_SAFE = {"TITLE"}          # 自由文本段：其中任何「词:」都可能是正文，不做段名判定

# 语法层规则表：id -> 说明（与 references/12-model-syntax.md 的规则编号对齐）
RULES = {
    "L01": "未知命令段名（拼写错误）",
    "L02": "语句缺分号",
    "L03": "变量名超过 8 字符（输出将被截断）",
    "L04": "输入行宽超过 90 字符（阈值已确证；命令行超限=WARN，TITLE 超限=INFO）",
    "L05": "%WITHIN% / %BETWEEN% 未配对",
    "L06": "CLASSES 与 TYPE=MIXTURE 不一致",
    "L07": "MODEL 引用未在 NAMES 声明的变量",
    "L08": "NAMES 缺失",
    "L09": "DATA 段缺 FILE IS",
    "L10": "TECH8 与 TYPE / ESTIMATOR / ALGORITHM 组合不可用（对应官方 W08）",
    "L11": "MODINDICES 与 ESTIMATOR=BAYES 冲突",
    "L12": "SAMPSTAT 与全类别结局冲突",
    "L13": "BOOTSTRAP 与 ESTIMATOR 组合不可用",
    "L14": "MODEL INDIRECT / CONSTRAINT / PRIORS 段为空（**合法**，仅 INFO 提示）",
    "L15": "USEVARIABLES 与 NAMES 冲突（引用未声明变量）",
    "L16": "段序罕见反序（**仅 INFO**：Mplus 不强制段序；只报官方语料仅 1/519 例的三对反序）",
}
# ⚠ 曾列过一条 L15「声明了 CATEGORICAL 但未声明 ESTIMATOR 兼容项」，**已删除**：
#   它没有任何实现代码，且在官方 62 类警告库（全部来自真实 `.out`）中找不到对应依据。
#   规则表必须与实现严格一一对应，不允许出现「列了但从不触发」的条目。
#   删除后再把原 L16 / L17 上移为 L15 / L16，保持编号连续、无空号。

# 数据层规则（仅在 --dict 下启用）
DATA_RULES = {
    "D01": "簇内无变异（每簇该变量为常数）",
    "D02": "全部变量缺失的观测被剔除",
    "D03": "分组变量存在缺失",
    "D04": "声明为连续型的变量实为常数",
    "D05": "NAMES 变量数与数据列数不符",
}


class Finding:
    def __init__(self, rid, level, line, msg, fix=""):
        self.rid = rid
        self.level = level      # BLOCKER / WARN / INFO
        self.line = line
        self.msg = msg
        self.fix = fix

    def __str__(self):
        loc = "L%-4d" % self.line if self.line else "L-   "
        s = "[%-7s] %s %s %s" % (self.level, self.rid, loc, self.msg)
        if self.fix:
            s += "\n          修法：%s" % self.fix
        return s


def strip_comments(raw):
    """剥离 `!` 行注释（保留行号：注释替换为等长空白，避免行号漂移）。"""
    out = []
    for line in raw.splitlines():
        i = line.find("!")
        out.append(line if i < 0 else line[:i])
    return out


def parse(raw):
    """切段。**支持段名与内容同行**（`DATA:\\tFILE IS x.dat;`）——只认独占行会大片判空。"""
    lines = strip_comments(raw)
    secs = []           # [(name, start_line_idx, [content lines])]
    cur = None
    for i, line in enumerate(lines):
        m = SEC_RE.match(line)
        if m:
            cur = [m.group(1).strip().upper(), i, []]
            secs.append(cur)
            rest = m.group(2)
            if rest.strip():
                cur[2].append(rest)
        elif cur is not None:
            cur[2].append(line)
    return lines, secs


# 模型子命令段的**词干**（stem）。凡是 `MODEL <X>` 且 X 以此开头，即为子命令段而非模型主段。
# ⚠ 实测坑（严重）：必须以**词干前缀**判定，不能用精确名集合。官方 `mcex5.5part4.inp`
#   写的是**单数** `MODEL PRIOR:`，而集合若只收复数 `MODEL PRIORS`，该段的先验语句
#   （`a1-a20~N(1.386,1);`）就会漏进 MODEL 正文被当变量引用扫描，`a1`/`b1` 被判「未声明」
#   （实测：2 例误报的根因）。用词干前缀可同时覆盖单复数与将来可能出现的其它写法。
MODEL_SUB_STEMS = ("INDIRECT", "CONSTRAINT", "PRIOR", "POPULATION",
                   "MISSING", "TEST", "MONTECARLO")


def is_model_sublock(name):
    """`MODEL <X>` 是否为子命令段（而非模型主段）。

    模型主段的标签是**用户自定义的组名 / 类别名**，官方语料实测包括
    `MODEL C` / `MODEL C1` / `MODEL C2` / `MODEL CG` / `MODEL CB` / `MODEL CU` /
    `MODEL CW` / `MODEL CY` / `MODEL G1`–`G3` / `MODEL DZ` / `MODEL FEMALE`，
    以及**纯数字组标签** `MODEL 1989` / `MODEL 1988`（来自 `GROUPING = g (1=1990 2=1989 3=1988)`）。
    这些都必须当主段处理，否则会漏检真正的未声明变量。
    """
    if not name.startswith("MODEL "):
        return False
    tail = name[6:].strip().upper()
    return any(tail.startswith(s) for s in MODEL_SUB_STEMS)


def sec_body(secs, name):
    """取指定段的正文（精确名）。同名多段（如多个 `MODEL G1/G2`）会拼接。"""
    name = name.upper()
    return "\n".join("\n".join(b) for n, _i, b in secs if n == name)


def model_body(secs):
    """取**所有** MODEL 主段正文：含 `MODEL:` 与 `MODEL C1:` / `MODEL G2:` / `MODEL 1989:` 等
    组标签变体，但**排除** `MODEL INDIRECT` / `CONSTRAINT` / `PRIOR(S)` / `POPULATION` /
    `MISSING` / `TEST` / `MONTECARLO` 这些子命令段（语义不同，混入会造成误判）。"""
    out = []
    for n, _i, b in secs:
        if n == "MODEL" or (n.startswith("MODEL ") and not is_model_sublock(n)):
            out.append("\n".join(b))
    return "\n".join(out)


def levenshtein(a, b, cap=3):
    """带上限的编辑距离，用于「段名疑似拼写错误」判定。"""
    if abs(len(a) - len(b)) > cap:
        return cap + 1
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
        if min(prev) > cap:
            return cap + 1
    return prev[-1]


def near_known_section(word):
    """单词是否「疑似某个已知段名的拼写错误」（编辑距离 ≤2）。"""
    w = word.upper().strip()
    if w in BASE_SEC:
        return None
    for s in BASE_SEC:
        if abs(len(s) - len(w)) <= 2 and levenshtein(w, s) <= 2:
            return s
    return None


def without_prose(secs):
    """返回**剥离自由文本段（TITLE）后**的全文，供正则类规则扫描。

    ⚠ 实测坑（严重）：TITLE 是自由文本，官方补充集里一个 TITLE 可长达 2000+ 行，
    其中的普通英文单词（如 "missing"、"sources"）会被变量清单正则
    `\\b(MISSING|...)\\s*=?\\s*([^;]*);` 误当语句起点，
    再由贪婪 `[^;]*` **横跨多个段**吞掉后面的 `usev = ...;`，
    导致后续变量全部被判「未声明」（实测：单个文件 2 例误报的根因）。
    """
    return "\n".join("\n".join(b) for n, _i, b in secs if n not in PROSE_SAFE)


def prose_flags(lines):
    """一次遍历算出「每一行是否处于自由文本段（TITLE）内」的布尔数组。

    ⚠ 性能坑（实测）：若改成对每一行都调用 `in_prose_section(lines, i)`，
    整体是 **O(n²)**。官方补充集里单个 TITLE 可长达 2661 行，
    于是 519 份语料 × 17 个注入器的自测会直接跑到进程被 SIGKILL（已踩到）。
    故统一改为**单遍预计算 + 查表**。
    """
    out = []
    cur = None
    for ln in lines:
        m = SEC_RE.match(ln)
        if m:
            cur = m.group(1).strip().upper()
        out.append(cur in PROSE_SAFE)
    return out


def in_prose_section(lines, idx):
    """判断第 idx 行是否处于自由文本段（TITLE）内 —— 用于抑制段名误判。

    ⚠ 实测坑：必须扫到 **idx 本身**（`range(idx + 1)`）。若写成 `range(idx)`，
    当 idx == 0（文件第 1 行）时循环体不执行、`cur` 恒为 None → 恒返回 False，
    于是**第 1 行永远被判为「非自由文本」**。官方 ex5.28 / ex5.32 / ex9.37 / mcex9.37
    的超限行恰好都在第 1 行，导致它们被误升为 WARN（实测踩到）。
    段名行本身属于它**自己**开启的段，故包含 idx 才是正确语义。

    ⚠ 性能：本函数是 O(idx)，仅供小规模/单点调用；批量判定请用 `prose_flags()` 查表。
    """
    return prose_flags(lines[:idx + 1])[idx]


def listed_names(text):
    """从 `NAMES ARE a b c;` 取变量名列表，**并展开 Mplus 区间语法** `y1-y12` → y1..y12。

    ⚠ 实测坑：官方示例大量使用 `NAMES ARE y1-y12;`。不展开区间会导致
    后续所有 `y1..y12` 被误判为「未声明变量」（实测误报源头之一）。
    """
    m = re.search(r"\bNAMES\s*(?:ARE|=)\s*([^;]*);", text, re.I | re.S)
    if not m:
        return []
    toks = [t for t in re.split(r"[\s,]+", m.group(1).strip()) if t]
    return expand_ranges(toks)


# Mplus 区间语法：`y1-y15` / `u1a-u1c` / `hd82-hd89` / `bin1-bin5`
# ⚠ 实测坑：**不能用正则的「贪婪前缀 + 后缀」写法**——
#   `^([A-Za-z_]+\d*)(\d+|...)` 对 `y1-y15` 会回溯成 `(y)(1)-(y1)(5)`，
#   即把 y1-y15 误读为 y1-y5（前缀不等 → 干脆不展开）。必须改用**最长公共前缀**判定。
LETTERS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _split_pair(tok):
    """把 `A-B` 拆成 (prefix, ra, rb)；不可解析返回 None。

    取**最短可行**的公共前缀：`y1` vs `y15` 必须拆成 ('y','1','15')，
    若贪心取最长公共前缀会得到 ('y1','','5') 而判为不可展开。
    """
    if tok.count("-") != 1:
        return None
    a, b = tok.split("-")
    if not a or not b:
        return None
    for i in range(0, min(len(a), len(b))):
        if a[:i] != b[:i]:
            break
        ra, rb = a[i:], b[i:]
        if not ra or not rb:
            continue
        digits = ra.isdigit() and rb.isdigit()
        letters = (len(ra) == 1 and len(rb) == 1 and ra.isalpha() and rb.isalpha()
                   and ra.isupper() == rb.isupper())
        if digits or letters:
            return a[:i], ra, rb
    return None


def expand_ranges(toks):
    """展开 Mplus 变量区间。数字后缀与**单字母后缀**两种形态都支持。"""
    out = []
    for t in toks:
        pair = _split_pair(t)
        if not pair:
            out.append(t)
            continue
        p, ra, rb = pair
        if ra.isdigit() and rb.isdigit():
            ia, ib = int(ra), int(rb)
            pad = len(ra)
            if ia <= ib and ib - ia <= 999:
                out.extend("%s%0*d" % (p, pad, i) for i in range(ia, ib + 1))
                continue
        else:
            if ord(ra) <= ord(rb) and ord(rb) - ord(ra) <= 26:
                out.extend(p + chr(c) for c in range(ord(ra), ord(rb) + 1))
                continue
        out.append(t)
    return out


def declared_vars(joined, names, secs, usevar=True):
    """模型内「已声明」变量集合 = NAMES ∪ 潜变量（`BY` 左侧）∪ 增长因子 ∪ CLASSES
    ∪ DEFINE 新建 ∪ `NEW(...)` 新参数 ∪ 内部变量（c#1 / g#1 / 单字母虚变量）。

    ⚠ 实测坑：潜变量（`f1 BY y1-y3;` 的 `f1`）**不在 NAMES 里**，这是 Mplus 的正常写法。
    若把「不在 NAMES」一律判为未声明，会大面积误报官方示例。

    `usevar=False` 时把 `USEVARIABLE*` / `USEV` / `USEVAR` 排除出声明来源（供 L15 用）。
    """
    d = {n.upper() for n in names}
    d |= decl_from_var_lists(joined, usevar)
    # ① 剥掉 `%WITHIN%` / `%BETWEEN%` / `%c#1%` 这些**区块标记**（它们由换行终止，不带 `;`）
    model = re.sub(r"%[^%\n]*%", " ", model_body(secs))
    # ② 按 `;` 切语句，**不能按 `\n` 切**——Mplus 允许一条语句跨行，
    #    按行切会把 `s1-s4 |\n f BY y1-y4;` 切成两条残句而双双失配。
    for stmt in model.split(";"):
        # ③ 用 `re.search` 而**非** `re.match`：区块标记被剥掉后语句仍可能以空白/残字打头，
        #    锚定匹配会整条失配（实测：改用 `;` 切分后若仍行首锚定，误报从 11 例反弹到 136 例）。
        # 增长因子 / 随机斜率：`i s | y1@0 y2@1;`、`s* | y1 ON a1;`
        m = re.search(r"([A-Za-z_]\w*(?:[\s\-]+[A-Za-z_]\w*)*)\s*[*@]?\s*\|", stmt)
        if m:
            # ⚠ 实测坑：`|` 的**右侧仍是一条完整模型语句**，它同样可以定义潜变量：
            #   官方 ex9.19part1 `s1-s4 | f BY y1-y4;`、ex9.26 `s | f BY u;` ——
            #   `f` 只出现在 `|` 右侧的 `BY` 左侧。若只取 `|` 左侧，
            #   后续 `f ON x1 x2;` / `f ON w;` 全被判「未声明变量」（实测 9 例误报的根因）。
            for v in expand_ranges(m.group(1).split()):
                d.add(v.upper())
            stmt = stmt[m.end():]
        # 潜变量定义：`BY` 左侧（可多个、可为区间）
        m = re.search(r"([A-Za-z_]\w*(?:[\s\-]+[A-Za-z_]\w*)*)\s+BY\b", stmt, re.I)
        if m:
            for v in expand_ranges(m.group(1).split()):
                d.add(v.upper())
    # CLASSES 里的类别变量：CLASSES = c1(2) c2(3);
    m = re.search(r"\bCLASSES\s*=\s*([^;]*);", joined, re.I | re.S)
    if m:
        for v in re.findall(r"([A-Za-z_]\w*)\s*\(", m.group(1)):
            d.add(v.upper())
    # NEW(a b) / DEFINE 新建
    for v in re.findall(r"\bNEW\s*\(([^)]*)\)", joined, re.I):
        for x in re.split(r"[\s,]+", v):
            if x:
                d.add(x.upper())
    # DEFINE 新建：**不能用行首锚定**。
    # ⚠ 实测坑：官方 penn__shortform_run7 用**条件赋值**创建变量：
    #     `if(desgn11s eq 4)then tx=1;  if(...)then tx=0;  xm = tx*agg5;`
    #   `tx` 只在 `then tx=1` 处出现，行首 `^\s*(\w+)\s*=` 完全匹配不到
    #   → `tx` 被判「未声明」，L15 / L07 双双误报（该文件 `.out` 实测 0 ERROR）。
    #   改为收集 DEFINE 段内**任意位置**的 `名字 =`（Mplus 的条件运算符是 eq/ne/gt，
    #   不会与赋值号混淆）。
    for v in re.findall(r"\b([A-Za-z_]\w*)\s*=(?!=)", sec_body(secs, "DEFINE")):
        d.add(v.upper())
    # NAMES 展开
    for n in names:
        d.add(n.upper())
    return d


# 语句关键词：出现这些词的行不是变量名引用（避免把关键词当变量）
STMT_KW = {
    "BY", "ON", "WITH", "ARE", "IS", "AND", "OR", "NOT", "NEW", "DEFINE",
    "MODEL", "INDIRECT", "CONSTRAINT", "PRIORS", "POPULATION", "MISSING", "TEST",
    "WITHIN", "BETWEEN", "OVERALL", "CLASS", "GENERAL", "CUTPOINT", "CUTOFF",
    "SUBPOPULATION", "NAMES", "USEVARIABLES", "CATEGORICAL", "NOMINAL", "COUNT",
    "CENSORED", "SURVIVAL", "KNOWNCLASS", "WEIGHT", "CLUSTER", "STRATIFICATION",
    "AUXILIARY", "IDVARIABLE", "TSCORES", "LAGGED", "RANDOM", "TYPE",
    "ESTIMATOR", "ALGORITHM", "INTEGRATION", "STARTS", "PROCESSORS", "BOOTSTRAP",
    "SAMPSTAT", "TECH1", "TECH3", "TECH4", "TECH8", "TECH11", "TECH14",
    "STANDARDIZED", "CINTERVAL", "MODINDICES", "RESIDUAL", "PLOT", "SAVEDATA",
    "UBOOTSTRAP", "CONFIDENCE", "REPARAMETERIZATION", "BASEHAZARD", "TINTERVAL",
    "GAP", "COVERAGE", "USEVAR", "LISTWISE", "CLASSIFICATION", "OUTFILE", "FSCORES",
    "SVALUES", "SAVE", "RESULTS", "IIS", "IGH", "TITLE", "DATA", "FILE",
    "VARIABLE", "ANALYSIS", "OUTPUT", "KNOTS", "POINT", "ANTITHETIC", "NREPS",
    "SEED", "GENERATE", "MODELPOPULATION", "RELIABILITY", "ALIGN", "FLARE",
    "PREAMBLE", "XWITH", "AT", "CUT", "FORMAT", "USE", "SQRT", "LOG", "EXP",
    "ON", "MONTECARLO", "OBSERVED", "BINARY", "CONTINUOUS", "DESCRIPTIVE",
    "PWITH", "PBWITH", "BY", "WITH", "TO", "THEN", "DO", "IF", "ON",
}
# 已知的 Mplus 内部生成变量形式（c#1 / g#1 / 裸数字）
INTERNAL_VAR = re.compile(r"^(?:[A-Za-z_]+)?#\d+$|^\d+$", re.I)


def extract_refs(body):
    """从一段 MODEL / USEVARIABLES 文本中取出被引用的变量名。

    ⚠ 实测坑：Mplus 用**圆括号给参数贴标签**（`y ON x (a);`），
    若不先剥掉括号内容，标签 `a` 会被当成「未声明变量」（实测误报源头之一）。
    """
    body = re.sub(r"\([^)]*\)", " ", body)     # 剥参数标签 / 类别数 / NEW(...) 的一元算子
    body = re.sub(r"[A-Za-z_]*#\d+[A-Za-z0-9_]*", " ", body)   # 内部类别变量 c#1 g#1
    out = []
    # `~`（先验分布运算符，如 `a1-a20~N(1.386,1)`）必须作分隔符，否则 `a20~N` 会粘成一个词
    for tok in re.split(r"[\s,;()|@*:\[\]<>/+\-~=]+", body):
        t = tok.strip()
        if not t or not re.match(r"^[A-Za-z_]\w*$", t):
            continue
        if t.upper() in STMT_KW or INTERNAL_VAR.match(t):
            continue
        out.append(t)
    return out


# 所有「变量清单式」赋值：出现在任意段中都视为**声明**
# ⚠ 实测坑（严重）：`WITHIN` / `BETWEEN` 这两个名字**同时**是
#   ① VARIABLE 段的变量清单关键字（`WITHIN = x a1-a4;`），
#   ② MODEL 段的两层区块定界符（`%WITHIN%` / `%BETWEEN%`）。
#   若不加左侧 `(?<!%)` 约束，`%WITHIN%` 会被当成清单关键字，把该块**第一条语句**
#   整体吞成「声明」——这会让块内的真实未声明变量被静默放过（漏检，属**假绿**）。
# 词干一律用**单数**写法，正则统一补 `S?`：
#   · `USEVARIABLE` / `USEVARIABLES` —— 官方 ex9.16 用**单数** `USEVARIABLE = x1 x2 y a3 person time;`，
#     只列复数会整条漏配（实测误报根因）；
#   · `USEV` / `USEVAR` —— 官方 ex8.10 等 42 份用 `USEV`（`.out` 实测 0 错误）；
#   · `CUTPOINT` / `CUTPOINTS`；`CLASS` / `CLASSES`。
# `WIDE` / `LONG` / `REPETITION` 是 `DATA WIDETOLONG:` 段用来声明**长格式变量名**的关键字（官方 ex9.16）。
VARLIST_STEMS = ("NAME", "USEVARIABLE", "USEV", "USEVAR", "CATEGORICAL", "NOMINAL", "COUNT",
                 "CENSORED", "SURVIVAL", "BINARY", "DESCRIPTIVE", "WITHIN", "BETWEEN",
                 "CLUSTER", "STRATIFICATION", "AUXILIARY", "KNOWNCLASS", "IDVARIABLE",
                 "TSCORE", "WEIGHT", "SUBPOPULATION", "MISSING", "LAGGED", "ALIGN",
                 "CONTINUOUS", "OBSERVED", "CUTPOINT", "GROUPING", "CLASS",
                 "WIDE", "LONG", "REPETITION")
VARLIST_ALT = "|".join(s + "S?" for s in VARLIST_STEMS)
VARLIST_RE = re.compile(r"(?<!%)\b(" + VARLIST_ALT + r")\b(?!\s*%)\s*=?\s*([^;]*);", re.I)

# ⚠ 实测缺口（故障注入自测抓到）：L15 校验「USEVARIABLES 里的变量是否在别处声明」，
#   但 `decl_from_var_lists()` 会把 **USEVARIABLES 自己列的名字**也算成「已声明」，
#   于是 `declared` 恒 ⊇ USEVARIABLES 的引用集 → **L15 永远不可能触发（死代码）**。
#   故另建一个**排除 USEVARIABLE*/USEV/USEVAR** 的清单正则，专供 L15 使用。
USEVAR_STEMS = ("USEVARIABLE", "USEV", "USEVAR")
VARLIST_CORE_ALT = "|".join(s + "S?" for s in VARLIST_STEMS if s not in USEVAR_STEMS)
VARLIST_CORE_RE = re.compile(r"(?<!%)\b(" + VARLIST_CORE_ALT + r")\b(?!\s*%)\s*=?\s*([^;]*);", re.I)


def decl_from_var_lists(joined, usevar=True):
    """把全部「变量清单式赋值」里的名字收进声明集。

    ⚠ 实测坑：官方 ex11.2 的 `USEVARIABLES = z1-z5 y0-y5 d1-d5;` 中 d1-d5
    **不在 NAMES 里**（它们在 `DATA MISSING:` 段的 `BINARY = d1-d5;` 声明）。
    只用 NAMES 判定「未声明」会误报。

    `usevar=False` 时**跳过** `USEVARIABLE*` / `USEV` / `USEVAR` 三类语句 ——
    专供 L15 使用：校验 USEVARIABLES 的引用时，不能把它自身当成声明来源。
    """
    d = set()
    for _kw, val in (VARLIST_RE if usevar else VARLIST_CORE_RE).findall(joined):
        v = re.sub(r"\([^)]*\)", " ", val)
        v = re.sub(r"[*|]", " ", v)
        for t in expand_ranges([x for x in re.split(r"[\s,]+", v) if x]):
            if re.match(r"^[A-Za-z_]\w*$", t):
                d.add(t.upper())
    return d


def check(lines, secs, dict_data=None, mplus_version=8):
    F = []
    joined = without_prose(secs)      # 正则类规则一律在**无自由文本段**的文本上跑
    names = listed_names(joined)
    names_upper = {n.upper() for n in names}
    declared = declared_vars(joined, names, secs)
    # TITLE 段是**自由文本**，由下一个命令终止，**不需要分号**（实测：官方示例全部如此）
    NO_SEMICOLON_SECTIONS = {"TITLE"}

    # L01 未知命令段名。
    # ⚠ 实测坑：不能把「任何词 + 冒号」都当段名——TITLE 是**自由文本**段，
    #   官方示例中 `A STUDY IN FACTOR ANALYSIS:` / `STEP 1:` / `PRCID:` / `SOURCES:`
    #   全是正文，误报率曾达 30%。改为**只判「疑似已知段名的拼写错误」**（编辑距离 ≤2）。
    known = {s.upper() for s in SECTIONS}
    prose = prose_flags(lines)          # 单遍预计算，避免 O(n²)
    for i, line in enumerate(lines):
        m = ANY_SEC_RE.match(line)
        if not m:
            continue
        w = m.group(1).strip().upper()
        if w in known or w in ("NAMES", "ARE", "FILE", "IS"):
            continue
        # `MODEL C:` / `MODEL G2:` / `DATA MISSING:` 等带标签变体是**合法**的，不参与拼写判定
        if re.match(r"^(MODEL|DATA)\s+[A-Za-z0-9_]{1,8}$", w):
            continue
        # ⚠ 实测缺口（故障注入自测抓到）：原先整条 L01 都被 `prose` 守卫跳过，
        #   于是当**拼错的段名紧跟在 TITLE 之后**时（官方 webnote 系列即
        #   `TITLE > VARIABLE > DATA > ...`），拼错行仍被判定「在 TITLE 自由文本内」→
        #   恰好在本规则最该发挥作用的位置失效（519 份里漏 13 份）。
        #   修法：把「疑似拼写错误」（编辑距离 ≤2）的判定**移到守卫之外**，
        #   只让噪声较大的 INFO 分支继续受守卫保护。
        near = near_known_section(w)
        if near:
            F.append(Finding("L01", "BLOCKER", i + 1,
                             "段名 `%s:` 疑似拼写错误（最接近的合法段名是 `%s:`）" % (w, near),
                             "改为 `%s:`；合法段名见 references/11-command-blocks.md" % near))
            continue
        if i > 0 and prose[i]:
            continue
        if not w.startswith(("MODEL ", "DATA ")) and len(w) <= 20:
            F.append(Finding("L01", "INFO", i + 1,
                             "`%s:` 不是标准顶层命令段（若在 TITLE 正文中可忽略）" % w,
                             "确认是否应为某个命令段"))

    # L08 NAMES 缺失
    if not names:
        F.append(Finding("L08", "BLOCKER", 0, "VARIABLE 段未找到 `NAMES`，无法解析变量",
                         "在 VARIABLE 段加 `NAMES ARE v1 v2 ...;`"))

    # L03 变量名超 8 字符（官方实测阈值）
    long_names = [n for n in names if len(n) > VARNAME_MAX]
    if long_names:
        F.append(Finding("L03", "WARN", 0,
                         "变量名超过 %d 字符：%s（官方输出只打印前 %d 字符，可能与他人结果对不上）"
                         % (VARNAME_MAX, ", ".join(long_names[:6]), VARNAME_MAX),
                         "改名为不超过 %d 字符" % VARNAME_MAX))

    # L04 行宽超 90 字符（官方实测阈值）。
    # ⚠ 阈值确证：官方 `.out` 原文 `*** WARNING Input line exceeded 90 characters.
    #   Some input may be truncated.`（警告库 W28/W30–W39/W47 共 13 类均为此句）。
    # ⚠ 但「是否触发该警告」**无法静态预测**：官方 516 份 `.out` 中有超限行的仅 6 份，
    #   其中 4 份确实告警、2 份**未**告警（ex5.28 的 95 字符 TITLE 行、ex5.32 的 131 字符
    #   TITLE 行实测均未告警），而 ex9.37 同为 95 字符 TITLE 行却告警。
    #   → 故按**风险**分级：命令行超限 = WARN（截断会改变语义）；仅 TITLE 自由文本超限 = INFO。
    over_cmd = []      # 非自由文本段的超限行
    over_prose = []    # 自由文本段（TITLE）的超限行
    for i, line in enumerate(lines):
        if len(line) > LINEWIDTH_MAX:
            (over_prose if prose[i] else over_cmd).append((i + 1, len(line)))
    if over_cmd:
        ln, w = over_cmd[0]
        F.append(Finding("L04", "WARN", ln,
                         "命令行宽 %d > %d 字符（Mplus 会截断输入行，可能改变语义；"
                         "官方同款警告：`Input line exceeded 90 characters`）" % (w, LINEWIDTH_MAX),
                         "在 %d 字符内换行" % LINEWIDTH_MAX))
    elif over_prose:
        ln, w = over_prose[0]
        F.append(Finding("L04", "INFO", ln,
                         "TITLE 自由文本行宽 %d > %d 字符。阈值已确证，但**是否触发 Mplus 的"
                         " 90 字符警告无法静态预测**（官方实测：6 份超限文件中 4 份告警、2 份不告警，"
                         "同为 95 字符的 TITLE 行结果相反）——TITLE 被截断通常无害，请以实跑为准"
                         % (w, LINEWIDTH_MAX),
                         "如追求与官方示例一致可换行；否则可忽略"))

    # L02 缺分号。⚠ 诚实边界：Mplus 允许一条语句跨任意多行，
    #     故「语句中段漏一个 `;`」在**不做完整语法分析**时不可判定；
    #     本规则只覆盖**可判定**的两类：① 整段无 `;`；② 段末语句未以 `;` 收尾。
    for n, i0, body in secs:
        if n in NO_SEMICOLON_SECTIONS:
            continue
        txt = "\n".join(body)
        if txt.strip() and ";" not in txt:
            F.append(Finding("L02", "BLOCKER", i0 + 1,
                             "`%s` 段疑似缺分号（段内无任何 `;`）" % n,
                             "Mplus 每条语句以 `;` 结束"))
    for n, i0, body in secs:
        if n in NO_SEMICOLON_SECTIONS:
            continue
        nb = [b for b in body if b.strip()]
        if nb and not nb[-1].rstrip().endswith(";"):
            F.append(Finding("L02", "BLOCKER", i0 + 1 + len(body) - 1,
                             "`%s` 段末语句未以 `;` 结束（段无法闭合）" % n,
                             "在段末补 `;`"))

    # L05 %WITHIN% / %BETWEEN% 配对。
    # ⚠ 实测坑：① 段名可带标签（`%BETWEEN level2%`），只用 `%BETWEEN%` 会漏；
    #   ② 多层模型**允许只给一层**（官方 ex9.20 即 `%WITHIN%` + `%BETWEEN level2%`），
    #      故「未成对」定为 WARN 而非 BLOCKER。
    has_w = bool(re.search(r"%WITHIN[^%]*%", joined, re.I))
    has_b = bool(re.search(r"%BETWEEN[^%]*%", joined, re.I))
    a_body = analysis_body(secs)
    is_two = bool(re.search(r"TYPE\s*(?:IS|=)\s*[^;]*(TWOLEVEL|THREELEVEL|CROSSCLASSIFIED)",
                            a_body, re.I))
    if has_w != has_b:
        F.append(Finding("L05", "WARN", 0,
                         "`%%WITHIN%%` 与 `%%BETWEEN%%` 只出现了一侧（缺 %s）——若另一层无模型设定可忽略"
                         % ("%BETWEEN%" if has_w else "%WITHIN%"),
                         "确认是否漏写另一层"))
    elif is_two and not (has_w or has_b):
        # ⚠ 实测坑：两种情形**不需要** `%WITHIN%` / `%BETWEEN%`，报了就是假阳性：
        #   ① **无 MODEL 主段** —— 官方 ex4.5 的 `TYPE = TWOLEVEL EFA 1 2 UW 1 1 UB;`
        #      把因子结构完整写在 TYPE 里，干脆没有 MODEL 段（`.out` 实测 0 ERROR / 0 WARNING）；
        #   ② **TYPE 含 EFA** —— 同上，探索性因子结构由 TYPE 指定。
        has_model = bool(model_body(secs).strip())
        is_efa = bool(re.search(r"TYPE\s*(?:IS|=)\s*[^;]*EFA", a_body, re.I))
        if has_model and not is_efa:
            F.append(Finding("L05", "WARN", 0,
                             "`TYPE` 为多层模型，但 MODEL 段无 `%%WITHIN%%` / `%%BETWEEN%%`",
                             "补两层区块（可用 `%OVERALL%` 写共同部分）"))

    # L06 CLASSES 与 TYPE=MIXTURE
    # ⚠ 实测坑：`CLASSES` 常与 `CATEGORICAL` **同行**（`CATEGORICAL = u1-u6; CLASSES = cb(2);`），
    #   故不能用行首锚定 `^\s*CLASSES`。
    has_classes = bool(re.search(r"\bCLASSES\s*=", joined, re.I))
    has_knownclass = bool(re.search(r"\bKNOWNCLASS\s*=", joined, re.I))
    is_mix = bool(re.search(r"TYPE\s*(?:IS|=)\s*[^;]*MIXTURE", a_body, re.I))
    if has_classes and not is_mix:
        F.append(Finding("L06", "BLOCKER", 0,
                         "声明了 `CLASSES` 但 `ANALYSIS` 未设 `TYPE=MIXTURE`",
                         "在 ANALYSIS 段加 `TYPE = MIXTURE;`"))
    if is_mix and not (has_classes or has_knownclass) and not has_b:
        # ⚠ 实测坑：`TYPE=MIXTURE` 下**可以**不写 `CLASSES`，只要 MODEL 段里直接出现
        #   `%c#1%` / `%c#2%` 这类**类别区块**——Mplus 由区块反推类别数并正常运行。
        #   官方 mcex7.30 / mcex8.17 即此写法，`.out` 实测 0 ERROR / 0 WARNING。
        #   有 %BETWEEN% 块时也可能是 only-within 的混合物写法，同样降为不报。
        has_classblock = bool(re.search(r"%[A-Za-z_]*#\d+%", joined, re.I))
        if not has_classblock:
            F.append(Finding("L06", "WARN", 0,
                             "`TYPE=MIXTURE` 但未声明 `CLASSES` / `KNOWNCLASS`，"
                             "MODEL 段也没有 `%c#n%` 类别区块",
                             "在 VARIABLE 段加 `CLASSES = c(2);`"))

    # L07 / L15 MODEL / USEVARIABLES 引用未声明变量
    if names_upper or declared:
        # L15 专用：声明集**必须排除 USEVARIABLES 自身**，否则该规则恒不触发（死代码）。
        declared_core = declared_vars(joined, names, secs, usevar=False)
        targets = []
        mb = model_body(secs)
        if mb:
            targets.append(("L07", "MODEL", mb, declared))
        m = re.search(r"\b(USEVARIABLES?|USEVAR|USEV)\b\s*=?\s*([^;]*);", joined, re.I)
        if m:
            # ⚠ 实测缺口：这里原先只认复数 `USEVARIABLES`，于是官方写成
            #   `USEVAR = property-gambling;`（penn__baysem_run22）、
            #   `Usevar = stub1f-tease7s male;`（penn__bayesian_run14）时
            #   **整条语句取不到**，L15 对这两类写法永久失效（故障注入自测抓到的）。
            #   → 与 VARLIST_STEMS 保持一致，三种写法全收。
            targets.append(("L15", "USEVARIABLES", m.group(2), declared_core))
        for rid, label, body, scope in targets:
            for t in extract_refs(body):
                if t.upper() not in scope:
                    F.append(Finding(rid, "BLOCKER", 0,
                                     "%s 引用了未声明变量 `%s`（既不在任何变量清单，也非 BY 定义的潜变量）"
                                     % (label, t),
                                     "补入 NAMES，或先在 MODEL 用 BY 定义该潜变量"))
                    break

    # L09 DATA 缺 FILE IS
    # ⚠ 实测缺口（故障注入自测抓到）：原实现用 `re.search(r"\bFILE\s*(?:IS|=)", joined)`
    #   在**全文**找 `FILE`，于是 `SAVEDATA: FILE = ...;` 会被误当 DATA 段的 `FILE IS`，
    #   删掉 DATA 的 FILE IS 后 L09 依然不报警（官方 mcex9.30step2 就写了 SAVEDATA FILE）。
    #   → 必须把搜索面**限定在 DATA 段正文内**。
    if sec_has(secs, "DATA") and not re.search(r"\bFILE\s*(?:IS|=)\s*\S",
                                              sec_body(secs, "DATA"), re.I):
        F.append(Finding("L09", "BLOCKER", 0, "DATA 段未给出 `FILE IS`",
                         "加 `FILE IS <数据文件名>;`"))

    # L10 TECH8 组合 —— 依据官方 `.out` 实证的 W08 原文逐字对齐：
    #   `TECH8 option is available only with analysis types MIXTURE, RANDOM, or TWOLEVEL
    #    with estimators ML, MLF, or MLR or ALGORITHM=INTEGRATION. Request for TECH8 is ignored.`
    # ⚠ 实测坑（三处，均已用 `.out` 反证）：
    #   ① 原实现漏掉 `ALGORITHM=INTEGRATION`（官方允许该写法启用 TECH8）；
    #   ② 原实现漏掉 `ESTIMATOR=BAYES` —— 贝叶斯下 TECH8 输出的是 **PSR 收敛判据**
    #      （官方 ex9.26 / ex9.27 / ex9.32 / ex9.40part2 的 `.out` 均含
    #      `PSR VALUE DOES NOT INCREASE` 且 **0 ERROR / 0 WARNING**），是标准用法；
    #   ③ 原实现默认该规则在所有版本成立 —— **错**。官方 `.out` 按版本交叉实测：
    #      口径 = **只统计「输入回显中请求了 TECH8」的 `.out`**（而非全部文件）；
    #      分母 = **全部 555 份官方 `.out`**（含 39 份未入索引者）：
    #        · Mplus **6.1**：请求 TECH8 **27** 份 → **6** 份报 W08（22%）；
    #        · Mplus **6.11**：请求 **4** 份 → **0** 份报；
    #        · Mplus **8**：请求 **67** 份 → **0** 份报；
    #        · Mplus **8.8**：请求 **188** 份 → **0** 份报
    #          （含 `TYPE` 缺省 + `MLR` 的普通 SEM，如 `ex6.2`）；
    #        · Mplus **DEVELOPMENT**：请求 **5** 份 → **1** 份报（`penn__shortform_run10`）；
    #        · 合计 **291** 份 → 报出 **7** 份；
    #        · 语料**无 Mplus 7 输出** → 7 的边界属「未验证」。
    #      ⚠ 口径注记：若收窄到**包内已索引的 516 份配对输出**，6.1 为 26、合计为 290，报出仍 7。
    #        差额来自 `penn__stard_run13`（v6.1，请求了 TECH8，但无配对 `.inp`）。
    #        引用这两个数字时**必须写明是 555 口径还是 516 口径**。
    #      → 该规则**必须带版本口径**，否则在 8.x 上全是假阳性。
    if re.search(r"\bTECH8\b", joined, re.I):
        is_random = bool(re.search(r"TYPE\s*(?:IS|=)\s*[^;]*RANDOM", a_body, re.I))
        est_bayes = bool(re.search(r"ESTIMATOR\s*=\s*BAYES", a_body, re.I))
        alg_int = bool(re.search(r"ALGORITHM\s*=\s*[^;]*INTEGRATION", a_body, re.I))
        ok = is_mix or is_random or is_two or est_bayes or alg_int
        if not ok:
            # 在「不满足豁免条件」的集合里，官方 6.x 语料实测再分两档：
            #   · **无 ANALYSIS TYPE 声明**（且非 BAYES、无 `INTEGRATION =`）→ 2/2 全部报 W08
            #     → 可判定，给 WARN；
            #   · **有 TYPE 但取值不是 MIXTURE/RANDOM/TWOLEVEL**（如 `TYPE = EFA`、`BASIC`）
            #     → 官方 v6.1 语料共 **6** 份：`TYPE = EFA 4 4` ×4 **报**；
            #       `TYPE = EFA 3 3` ×1、`TYPE = BASIC` ×1 **不报**
            #     → **不可静态判定**（同为 EFA，3 3 与 4 4 结果相反），只给 INFO，
            #       绝不冒充确定结论。
            atype_declared = bool(re.search(r"\bTYPE\s*(?:IS|=)", a_body, re.I))
            int_set = bool(re.search(r"\bINTEGRATION\s*=", a_body, re.I))
            cond = ("`TECH8` 在该版本下仅允许 `TYPE=MIXTURE / RANDOM / TWOLEVEL`（配 ML/MLF/MLR）、"
                    "`ESTIMATOR=BAYES`，或 `ALGORITHM=INTEGRATION`")
            if mplus_version == 6:
                if not atype_declared and not int_set:
                    F.append(Finding("L10", "WARN", 0,
                                     "Mplus 6.x：" + cond + "。当前 ANALYSIS **未声明任何 `TYPE`**，"
                                     "该组合官方 `.out` 实证**必报** W08"
                                     "「Request for TECH8 is ignored」（2/2）",
                                     "补 `TYPE=`，或加 `ALGORITHM = INTEGRATION;`，或删掉 TECH8"))
                else:
                    F.append(Finding("L10", "INFO", 0,
                                     "Mplus 6.x：" + cond + "。当前 TYPE 取值不在豁免之列，"
                                     "但**是否报 W08 无法静态判定**——官方 v6.1 同写法 6 份中 4 份报、2 份未报"
                                     "（`TYPE = EFA 4 4` 报，`TYPE = EFA 3 3` 与 `TYPE = BASIC` 未报），"
                                     "请以实跑为准",
                                     "建议改为 `TYPE = MIXTURE / RANDOM / TWOLEVEL` 之一"))
            elif mplus_version == 7:
                F.append(Finding("L10", "INFO", 0,
                                 "Mplus 7：" + cond
                                 + "。**边界未验证**：官方语料无 Mplus 7 输出，"
                                   "已知 6.1 有该约束、8/8.8 已放宽",
                                 "在 Mplus 7 上实跑确认；或按 8.x 写法使用"))
            # mplus_version == 8：官方 436 份 8.x 输出实测 0 份报 W08，不再提示

    # L11 MODINDICES + BAYES
    if re.search(r"\bMODINDICES\b", joined, re.I) and re.search(r"ESTIMATOR\s*=\s*BAYES", joined, re.I):
        F.append(Finding("L11", "BLOCKER", 0, "`MODINDICES` 不与 `ESTIMATOR=BAYES` 兼容",
                         "删除 MODINDICES，或改用 ML/MLR"))

    # L12 SAMPSTAT + 全类别结局
    if re.search(r"\bSAMPSTAT\b", joined, re.I) and names_upper:
        cat = re.search(r"\bCATEGORICAL\s*=?\s*([^;]*);", joined, re.I)
        if cat:
            catset = {t.upper() for t in re.split(r"[\s,]+", cat.group(1)) if t}
            if catset and catset >= names_upper:
                F.append(Finding("L12", "WARN", 0,
                                 "全部结局均为类别型时 `SAMPSTAT` 不可用",
                                 "移除 SAMPSTAT"))

    # L13 BOOTSTRAP + ESTIMATOR=BAYES
    if re.search(r"^\s*BOOTSTRAP\s*=", joined, re.I | re.M) and \
       re.search(r"ESTIMATOR\s*=\s*BAYES", joined, re.I):
        F.append(Finding("L13", "BLOCKER", 0, "`BOOTSTRAP` 不与 `ESTIMATOR=BAYES` 兼容",
                         "删除 BOOTSTRAP（贝叶斯用可信区间，无需 bootstrap）"))
    if re.search(r" CINTERVAL\s*\(\s*(BC)?BOOTSTRAP", joined, re.I) and \
       not re.search(r"^\s*BOOTSTRAP\s*=", joined, re.I | re.M):
        F.append(Finding("L13", "BLOCKER", 0,
                         "OUTPUT 请求了 bootstrap 置信区间，但 ANALYSIS 未设 `BOOTSTRAP`",
                         "在 ANALYSIS 段加 `BOOTSTRAP = 1000;`"))

    # L14 特殊 MODEL 段为空 —— **降为 INFO**。
    # ⚠ 实测：官方 `penn__bayesian_run12.inp` 的 `MODEL PRIORS:` 段只有一个空行，
    #   其 `.out` 实测 **0 ERROR / 0 WARNING**。即空段是**合法**的（Mplus 静默忽略），
    #   不构成错误，故不能作为 WARN 输出。
    for n in ("MODEL INDIRECT", "MODEL CONSTRAINT", "MODEL PRIORS"):
        for sn, i0, body in secs:
            if sn == n and not "\n".join(body).strip():
                F.append(Finding("L14", "INFO", i0 + 1,
                                 "`%s` 段为空（Mplus 会静默忽略，**不是错误**；"
                                 "官方实测存在同样写法且 0 警告）" % n,
                                 "如需保留可删除该段"))

    # L16 段序 —— **原实现的前提已被官方语料证伪，本轮重写**。
    # 原实现做法：拿 SECTIONS 的**列表顺序当"标准段序"**，只要实际顺序与它不同就报 INFO。
    # 实测反证（519 份官方 `.inp` 逐文件跑该规则）：**命中 267 份 = 51.4%**。
    #   过半官方示例"违规"，说明被证伪的是**规则前提**，不是这些文件：
    #   · 蒙特卡洛输入**必然**先写 `MODEL POPULATION` 再写 `MODEL`（总体模型在前），
    #     而 SECTIONS 把 `MODEL` 排在 `MODEL POPULATION` 之前 → 系统性误报；
    #   · 官方 62 类警告库（全部来自真实 `.out`）中**没有任何一类与段序有关**。
    # 结论：**不存在"标准段序"**。Mplus 不强制段序，任何顺序都合法。
    # → 因此不再做"整体顺序比对"，只保留确有信息量的部分：
    #   **只报官方语料中实测极罕见的三对反序**（各 1/519 ≈ 0.2%），其余一律沉默。
    #   这三对反序本身**也是合法的**，故只给 INFO，绝不当错误。
    RARE_REVERSALS = [("MODEL", "ANALYSIS"), ("VARIABLE", "DATA"), ("PLOT", "OUTPUT")]
    pos = {}
    for i, (n, _i2, _b) in enumerate(secs):
        pos.setdefault(n, i)
    for hi, lo in RARE_REVERSALS:
        if hi in pos and lo in pos and pos[hi] < pos[lo]:
            F.append(Finding("L16", "INFO", 0,
                             "`%s` 排在 `%s` 之前 —— **Mplus 不强制段序，此写法合法**；"
                             "但官方 519 份示例中该顺序仅 1 例（0.2%%），非常罕见，"
                             "建议核对是否笔误" % (hi, lo),
                             "仅风格建议，无需修改"))

    # ---- 数据层（仅 --dict）----
    if dict_data:
        F.extend(check_data(joined, names, dict_data))

    return F, bool(dict_data)


def sec_has(secs, name):
    return any(n == name.upper() for n, _i, _b in secs)


def analysis_body(secs):
    """ANALYSIS 段正文。

    ⚠ 实测坑：`TYPE` 这个关键字**同时**属于 ANALYSIS（`TYPE = TWOLEVEL RANDOM;`）
    与 PLOT（`TYPE = PLOT2;`）。若在**全文**上找 `TYPE`，PLOT 的取值会污染
    ANALYSIS 的判定（官方 ex9.37 等即 `TYPE = PLOT3`）。
    `TYPE` / `ESTIMATOR` / `ALGORITHM` 一律只在 ANALYSIS 段内取。
    """
    return sec_body(secs, "ANALYSIS")


def check_data(joined, names, d):
    """数据层规则。dict 结构：{n_rows, n_cols, columns:{name:{missing,n_unique,is_constant}},
    cluster_var, cluster_stats:{var:{n_clusters_no_variation}}}"""
    F = []
    cols = d.get("columns") or {}
    if d.get("n_cols") and names and d["n_cols"] != len(names):
        F.append(Finding("D05", "BLOCKER", 0,
                         "NAMES 声明 %d 个变量，数据实际 %d 列" % (len(names), d["n_cols"]),
                         "对齐 NAMES 与数据列"))
    for nm, c in cols.items():
        if c.get("n_unique") == 1:
            F.append(Finding("D04", "WARN", 0, "变量 `%s` 在数据中为常数（方差为 0）" % nm,
                             "移除该变量或核对数据"))
    cl = d.get("cluster_var")
    if cl and d.get("cluster_stats"):
        for var, k in (d["cluster_stats"] or {}).items():
            if k:
                F.append(Finding("D01", "WARN", 0,
                                 "变量 `%s` 在 %d 个簇内无变异" % (var, k),
                                 "Mplus 会给出 no variation within a cluster 警告"))
    if d.get("n_missing_all_vars"):
        F.append(Finding("D02", "WARN", 0,
                         "%d 条观测在所有变量上缺失，将被剔除" % d["n_missing_all_vars"],
                         "核对数据读入方式与 MISSING 声明"))
    if cl and cols.get(cl, {}).get("missing"):
        F.append(Finding("D03", "BLOCKER", 0, "分组/聚类变量 `%s` 存在缺失值" % cl,
                         "剔除或在 DEFINE 段处理"))
    return F


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inp")
    ap.add_argument("--dict", dest="dict_path")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--mplus-version", dest="mplus_version", type=int, default=8,
                    choices=(6, 7, 8),
                    help="目标 Mplus 大版本（默认 8，与所附官方语料主流一致）。"
                         "仅影响版本敏感的规则（目前为 L10 / TECH8）。"
                         "官方 .out 实证：6.1 有 TECH8 约束、8/8.8 已放宽、7 未覆盖。")
    args = ap.parse_args()

    if not os.path.exists(args.inp):
        print("ERROR: 文件不存在：%s" % args.inp, file=sys.stderr)
        return 2
    raw = open(args.inp, encoding="utf-8", errors="replace").read()
    dict_data = None
    if args.dict_path:
        try:
            dict_data = json.load(open(args.dict_path, encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            print("ERROR: 数据字典读取失败：%s" % e, file=sys.stderr)
            return 2

    lines, secs = parse(raw)
    findings, used_dict = check(lines, secs, dict_data, args.mplus_version)

    nb = sum(1 for f in findings if f.level == "BLOCKER")
    nw = sum(1 for f in findings if f.level == "WARN")

    if args.json:
        print(json.dumps({
            "file": args.inp,
            "dict_used": bool(used_dict),
            "mplus_version": args.mplus_version,
            "coverage": "data_layer_extension" if used_dict else "syntax_layer_only",
            "coverage_note": ("已启用数据层扩展（--dict）" if used_dict
                              else "**仅覆盖语法层**：已实现规则覆盖警告库 14/62 类、"
                                   "2/39 种消息（按出现条数 30/219 = 13.7%）；"
                                   "另有 9 种消息语法层可预判但尚未实现；"
                                   "数据层与运行层未检查（28/39 种消息），提供 --dict 可扩展至数据层"),
            "counts": {"BLOCKER": nb, "WARN": nw},
            "findings": [{"rule": f.rid, "level": f.level, "line": f.line,
                          "msg": f.msg, "fix": f.fix} for f in findings],
        }, ensure_ascii=False, indent=2))
    else:
        print("=== check_inp.py · %s ===" % os.path.basename(args.inp))
        print("覆盖范围：%s" % ("语法层 + 数据层（已提供 --dict）" if used_dict
                              else "**仅覆盖语法层**（见文末覆盖率声明）"))
        print("实测阈值：变量名 ≤ %d 字符 · 行宽 ≤ %d 字符 · 目标 Mplus 大版本 %d"
              % (VARNAME_MAX, LINEWIDTH_MAX, args.mplus_version))
        print("-" * 62)
        if not findings:
            print("未发现语法层问题。（注意：本结果**不包括**数据层与运行期问题）")
        for f in sorted(findings, key=lambda x: (x.level != "BLOCKER", x.line or 0)):
            print(f)
        print("-" * 62)
        print("BLOCKER=%d  WARN=%d  |  规则表：%s" % (
            nb, nw, " ".join(sorted(RULES)[:6]) + " … 共 %d 条" % len(RULES)))
        if not used_dict:
            print("⚠ 仅覆盖语法层：已实现规则覆盖警告库 **14/62 类 · 2/39 种消息**"
                  "（按出现条数 30/219 = 13.7%）。")
            print("   另有 **9 种消息**语法层可预判但尚未实现；数据层与运行层"
                  "（约 28/39 种消息）需 --dict 或实跑，本脚本不覆盖。")
            print("   引用覆盖率时必须写明口径：类键 22.6% / 消息种类 5.1% / 出现条数 13.7%。")

    rc = 1 if nb else (1 if (args.strict and nw) else 0)
    return rc


if __name__ == "__main__":
    sys.exit(main())
