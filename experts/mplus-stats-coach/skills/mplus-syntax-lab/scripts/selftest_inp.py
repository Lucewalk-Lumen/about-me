#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
selftest_inp.py — `check_inp.py` 的**绿/红双向证明**

为什么必须做这个
    519 份官方 `.inp` 上 `check_inp.py` 已经做到 BLOCKER=0 / WARN=0。
    但「全绿」有两种可能：① 真的把假阳性压干净了；② 扫描器其实什么都没查。
    只测绿向**无法区分这两者**。故本脚本做**故障注入**（fault injection）——
    对真实官方文件逐条注入已知缺陷，断言对应规则**必须**命中。这就是红向证明。

两条断言（缺一不可）
    绿向：未改动的官方 `.inp` → 必须 0 BLOCKER、0 WARN（INFO 不算）
    红向：注入故障后 → 目标规则必须出现在结果中
    另有一条**反向**断言：版本敏感规则（L10）在错误版本下必须**不**触发
    —— 防止「规则靠无脑告警来刷召回」。

设计原则
    · 注入都作用在**真实官方 `.inp`** 上，而非手写小样例 —— 语法真实、覆盖面即语料面
    · 不改变文件其余部分；不适用该故障的文件**跳过并计数**（不计入分母）
    · 检出率不足 100% 即判 FAIL —— 不允许「大部分能查出来」这种含糊结论

用法
    python3 selftest_inp.py --pkg <包根目录>            # 全量（519 份 × 注入器）
    python3 selftest_inp.py --pkg <包根目录> --sample 60  # 抽样加速
退出码
    0  绿红双向全部通过
    1  存在未通过的断言
"""
import argparse
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_inp as ci  # noqa: E402


# ---------------------------------------------------------------- 注入器
# 每个注入器：(id, 目标规则, 说明, 适用判定+改写函数)
# 改写函数返回 (新文本, 是否适用)。不适用返回 (原文本, False)。

def _sections(text):
    lines, secs = ci.parse(text)
    return lines, secs


def _hdr_line(secs, name):
    """取某段段名所在的原始行号（0-based）。"""
    for n, i, _b in secs:
        if n == name:
            return i
    return None


def _line_sections(text):
    """返回「每个原始行号 → 所属段名」，供注入器精确定位。

    ⚠ 注入器**不能**用 `段头行号 + 序号` 去推正文行号：`parse()` 会剥掉注释行、
    且段头与正文可同行，映射不是简单加一（实测 I05 因此偏了一行，检出率只有 5%）。
    """
    out = []
    cur = None
    for ln in text.splitlines():
        m = ci.SEC_RE.match(ln)
        if m:
            cur = m.group(1).strip().upper()
        out.append(cur)
    return out


def inj_undeclared_in_model(text):
    """MODEL 段引用未声明变量 → L07。"""
    lines, secs = _sections(text)
    i = _hdr_line(secs, "MODEL")
    if i is None:
        return text, False
    ls = text.splitlines()
    ls.insert(i + 1, "    zzundec1 ON zzundec2;")
    return "\n".join(ls) + "\n", True


def inj_long_varname(text):
    """NAMES 里出现 >8 字符变量名 → L03。

    不用行首锚定：官方常写成 `VARIABLE:  NAMES ARE ...`（同一行既有段名又有正文）。
    """
    m = re.search(r"\bNAMES\b(\s*(?:ARE|=)\s*)([^;]*);", text, re.I)
    if not m:
        return text, False
    new = m.group(0).replace(m.group(2), m.group(2).rstrip() + " zzverylongname")
    return text[:m.start()] + new + text[m.end():], True


def inj_long_command_line(text):
    """命令行宽 >90 字符（非 TITLE 段）→ L04 WARN。"""
    lines, secs = _sections(text)
    i = _hdr_line(secs, "VARIABLE")
    if i is None:
        return text, False
    ls = text.splitlines()
    ls.insert(i + 1, "    AUXILIARY = " + " ".join("v%02d" % k for k in range(20)) + ";")
    return "\n".join(ls) + "\n", True


def inj_no_semicolon_in_section(text):
    """整段无分号 → L02。"""
    lines, secs = _sections(text)
    i = _hdr_line(secs, "OUTPUT")
    if i is None:
        return text, False
    # 把 OUTPUT 段的 `;` 全部去掉
    ls = text.splitlines()
    j = i + 1
    touched = False
    while j < len(ls):
        if ci.SEC_RE.match(ls[j]) and j > i:
            break
        if ";" in ls[j]:
            ls[j] = ls[j].replace(";", " ")
            touched = True
        j += 1
    if not touched:
        return text, False
    return "\n".join(ls) + "\n", True


def inj_no_final_semicolon(text):
    """段末语句未以 `;` 收尾 → L02。

    ⚠ 两个坑（都实测踩到）：
    ① 不能用「段头行号 + 偏移」推正文行号（会偏位）；
    ② 必须看**剥掉 `!` 注释之后**的行 —— 官方 `penn__bayesian_run15` 文末是
       `!   type = plot2;`，原始行以 `;` 结尾，但注释剥掉后其实是个空行，
       改它毫无作用（实测唯一漏检例即此）。
    """
    stripped = ci.strip_comments(text)
    secs_of = _line_sections(text)
    lines = text.splitlines()
    for k in range(len(stripped) - 1, -1, -1):
        s = secs_of[k]
        if s is None or s in ci.PROSE_SAFE:
            continue
        if not stripped[k].strip():
            continue
        if not stripped[k].rstrip().endswith(";"):
            continue
        cut = stripped[k].rstrip()
        lines[k] = lines[k].replace(cut, cut[:-1], 1)
        return "\n".join(lines) + "\n", True
    return text, False


def inj_section_typo(text):
    """段名拼写错误（编辑距离 ≤2）→ L01。"""
    for wrong, right in (("VARIBLE", "VARIABLE"), ("ANALYIS", "ANALYSIS"),
                         ("MODLE", "MODEL")):
        m = re.search(r"(?mi)^(\s*)" + right + r"(\s*:)", text)
        if m:
            return text[:m.start()] + m.group(1) + wrong + m.group(2) + \
                text[m.end():], True
    return text, False


def inj_drop_names(text):
    """删除**全部** NAMES 语句 → L08。

    ⚠ 官方有文件写了**两条** NAMES（如 `penn__bayesian_run13` 在 `DATA TWOPART:` 段
    另有 `names = hd82-hd89;`）。只删第一条时第二条仍能声明变量，L08 不会触发，
    看起来像扫描器漏检，其实是注入不彻底（实测踩到）。
    同时**不能加行首锚定**：官方常写 `VARIABLE:  NAMES ARE y1-y50 ...;`，
    `^\\s*NAMES` 会整条漏配（实测 penn__baysem_run14/15 即此写法）。
    """
    new, n = re.subn(r"\bNAMES\b\s*(?:ARE|=)\s*[^;]*;[ \t]*\n?", "", text, flags=re.I)
    return (new, True) if n else (text, False)


def inj_drop_file_is(text):
    """DATA 段去掉 FILE IS → L09。"""
    m = re.search(r"(?mi)^\s*FILE\s*(?:IS|=)[^;]*;[ \t]*", text)
    if not m:
        return text, False
    return text[:m.start()] + text[m.end():], True


def inj_classes_without_mixture(text):
    """有 CLASSES 但 ANALYSIS 无 TYPE=MIXTURE → L06。"""
    lines, secs = _sections(text)
    if _hdr_line(secs, "VARIABLE") is None:
        return text, False
    if re.search(r"(?i)TYPE\s*(?:IS|=)\s*[^;]*MIXTURE", ci.sec_body(secs, "ANALYSIS")):
        return text, False
    ls = text.splitlines()
    ls.append("VARIABLE: CLASSES = zzc(2);")
    return "\n".join(ls) + "\n", True


def inj_within_without_between(text):
    """多层模型去掉 %BETWEEN% → L05。"""
    if "%WITHIN" not in text.upper() or "%BETWEEN" not in text.upper():
        return text, False
    lines, secs = _sections(text)
    a = ci.sec_body(secs, "ANALYSIS")
    if not re.search(r"(?i)TYPE\s*(?:IS|=)\s*[^;]*(TWOLEVEL|THREELEVEL|CROSSCLASSIFIED)", a):
        return text, False
    ls = [l for l in text.splitlines() if not re.match(r"^\s*%BETWEEN[^%]*%", l, re.I)]
    if len(ls) == len(text.splitlines()):
        return text, False
    return "\n".join(ls) + "\n", True


def inj_modindices_with_bayes(text):
    """MODINDICES + ESTIMATOR=BAYES → L11。"""
    lines, secs = _sections(text)
    if _hdr_line(secs, "OUTPUT") is None:
        return text, False
    ls = text.splitlines()
    # 在 ANALYSIS 段插入 ESTIMATOR = BAYES
    i = _hdr_line(secs, "ANALYSIS")
    if i is not None:
        ls.insert(i + 1, "    ESTIMATOR = BAYES;")
    else:
        ls.append("ANALYSIS: ESTIMATOR = BAYES;")
    ls.append("OUTPUT: MODINDICES(3.84);")
    return "\n".join(ls) + "\n", True


def inj_bootstrap_with_bayes(text):
    """BOOTSTRAP + ESTIMATOR=BAYES → L13。"""
    lines, secs = _sections(text)
    if _hdr_line(secs, "ANALYSIS") is None:
        return text, False
    ls = text.splitlines()
    i = _hdr_line(secs, "ANALYSIS")
    ls.insert(i + 1, "    ESTIMATOR = BAYES;")
    ls.insert(i + 2, "    BOOTSTRAP = 1000;")
    return "\n".join(ls) + "\n", True


def inj_boot_ci_without_bootstrap(text):
    """OUTPUT 请求 bootstrap 置信区间但 ANALYSIS 无 BOOTSTRAP → L13。"""
    lines, secs = _sections(text)
    if _hdr_line(secs, "OUTPUT") is None:
        return text, False
    if re.search(r"(?im)^\s*BOOTSTRAP\s*=", ci.sec_body(secs, "ANALYSIS")):
        return text, False
    ls = text.splitlines()
    i = _hdr_line(secs, "OUTPUT")
    ls.insert(i + 1, "    CINTERVAL(BOOTSTRAP);")
    return "\n".join(ls) + "\n", True


def _section_end(text, name):
    """返回段 `name` 的**结束行号**（下一个段头所在行，或文件末）。

    注入器必须在**段末**插入语句，不能插在段头之后 —— 官方常写成
    `VARIABLE: NAMES =` 换行接变量表，插在段头之后会**插进 NAMES 语句中途**，
    把后续 token 污染成变量名（实测 I14 在 penn__baysem_run14 上因此漏检）。
    """
    lines = text.splitlines()
    start = None
    for k, l in enumerate(lines):
        m = ci.SEC_RE.match(l)
        if not m:
            continue
        n = m.group(1).strip().upper()
        if start is None:
            if n == name:
                start = k
        else:
            return k
    return len(lines) if start is not None else None


def inj_sampstat_all_categorical(text):
    """SAMPSTAT + 全部结局为类别型 → L12。

    ⚠ 必须先**删掉原有的 CATEGORICAL 语句**再插入新的：L12 用 `re.search` 只取
    第一条 CATEGORICAL，原语句在前时集合不等于 NAMES，规则不会触发 ——
    那是注入不彻底，不是扫描器漏检（实测 penn__baysem_run14/15）。
    """
    lines, secs = _sections(text)
    if _hdr_line(secs, "VARIABLE") is None:
        return text, False
    names = ci.listed_names(ci.without_prose(secs))
    if len(names) < 2:
        return text, False
    txt = re.sub(r"\bCATEGORICAL\b\s*=?\s*[^;]*;[ \t]*\n?", "", text, flags=re.I)
    end = _section_end(txt, "VARIABLE")
    if end is None:
        return text, False
    ls = txt.splitlines()
    ls.insert(end, "    CATEGORICAL = " + " ".join(names) + ";")
    oend = _section_end("\n".join(ls), "OUTPUT")
    if oend is not None:
        ls.insert(oend, "    SAMPSTAT;")
    else:
        ls.append("OUTPUT: SAMPSTAT;")
    return "\n".join(ls) + "\n", True


def inj_usevar_undeclared(text):
    """USEVARIABLES / USEVAR / USEV 追加未声明变量 → L15。

    三种写法都要覆盖：官方实测存在 `USEVAR = property-gambling;`（baysem_run22）与
    `Usevar = stub1f-tease7s male;`（bayesian_run14）。故不能用行首锚定。
    """
    m = re.search(r"\b(USEVARIABLES?|USEVAR|USEV)\b\s*=?\s*([^;]*);", text, re.I)
    if not m:
        return text, False
    new = m.group(0).rstrip().rstrip(";") + " zzundecl;"
    return text[:m.start()] + new + text[m.end():], True


def inj_empty_model_priors(text):
    """空 MODEL PRIORS 段 → L14（INFO）。"""
    lines, secs = _sections(text)
    if _hdr_line(secs, "OUTPUT") is None:
        return text, False
    ls = text.splitlines()
    i = _hdr_line(secs, "OUTPUT")
    ls.insert(i, "MODEL PRIORS:")
    ls.insert(i + 1, "")
    return "\n".join(ls) + "\n", True


def inj_tech8_no_type(text):
    """TECH8 且 ANALYSIS 无任何 TYPE → v6 必报 L10；v8 必不报（反向断言）。

    ⚠ 必须用**全局替换**剔除 `TYPE` / `ALGORITHM` / `INTEGRATION` 设置，不能只删
    「行首是 TYPE 的行」：官方常写成 `ANALYSIS: TYPE = TWOLEVEL;`（段名与正文同行），
    行首锚定删不掉，会让 `atype_declared` 仍为真 → 规则降级为 INFO（实测 147 例）。
    """
    txt = re.sub(r"\bTYPE\s*(?:IS|=)\s*[^;]*;", " ", text, flags=re.I)
    txt = re.sub(r"\b(?:ALGORITHM|INTEGRATION)\s*=\s*[^;]*;", " ", txt, flags=re.I)
    txt = re.sub(r"\bESTIMATOR\s*=\s*BAYES\s*;", " ", txt, flags=re.I)
    if re.search(r"(?i)\bTYPE\s*(?:IS|=)", txt):
        return text, False
    if not re.search(r"(?i)\bOUTPUT\b\s*:", txt):
        return text, False
    txt = re.sub(r"(?i)^(\s*OUTPUT\s*:\s*)", r"\1TECH8; ", txt, flags=re.M)
    if not re.search(r"(?i)\bTECH8\b", txt):
        txt += "\nOUTPUT: TECH8;\n"
    return txt, True


# id, 目标规则, 期望级别, 说明, 函数
INJECTORS = [
    ("I01", "L07", "BLOCKER", "MODEL 段引用未声明变量", inj_undeclared_in_model),
    ("I02", "L03", "WARN", "NAMES 含 >8 字符变量名", inj_long_varname),
    ("I03", "L04", "WARN", "命令行宽 >90 字符", inj_long_command_line),
    ("I04", "L02", "BLOCKER", "整段无分号", inj_no_semicolon_in_section),
    ("I05", "L02", "BLOCKER", "段末语句缺分号", inj_no_final_semicolon),
    ("I06", "L01", "BLOCKER", "段名拼写错误", inj_section_typo),
    ("I07", "L08", "BLOCKER", "删除 NAMES", inj_drop_names),
    ("I08", "L09", "BLOCKER", "DATA 缺 FILE IS", inj_drop_file_is),
    ("I09", "L06", "BLOCKER", "CLASSES 无 TYPE=MIXTURE", inj_classes_without_mixture),
    ("I10", "L05", "WARN", "多层模型缺 %BETWEEN%", inj_within_without_between),
    ("I11", "L11", "BLOCKER", "MODINDICES + BAYES", inj_modindices_with_bayes),
    ("I12", "L13", "BLOCKER", "BOOTSTRAP + BAYES", inj_bootstrap_with_bayes),
    ("I13", "L13", "BLOCKER", "boot CI 无 BOOTSTRAP", inj_boot_ci_without_bootstrap),
    ("I14", "L12", "WARN", "SAMPSTAT + 全类别结局", inj_sampstat_all_categorical),
    ("I15", "L15", "BLOCKER", "USEVARIABLES 引用未声明变量", inj_usevar_undeclared),
    ("I16", "L14", "INFO", "空 MODEL PRIORS 段", inj_empty_model_priors),
    ("I17", "L10", "WARN", "TECH8 无 TYPE（仅 v6 应报）", inj_tech8_no_type),
]


def run_one(text, version=8):
    lines, secs = ci.parse(text)
    return ci.check(lines, secs, None, version)[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pkg", required=True)
    ap.add_argument("--sample", type=int, default=0,
                    help="只取前 N 份（0 = 全量）")
    args = ap.parse_args()
    pkg = os.path.abspath(args.pkg)

    files = sorted(glob.glob(os.path.join(pkg, "knowledge", "official", "**", "*.inp"),
                             recursive=True))
    if not files:
        print("FAIL 找不到官方 .inp（%s/knowledge/official/）" % pkg, file=sys.stderr)
        return 2
    if args.sample:
        files = files[:args.sample]
    print("=" * 72)
    print("check_inp.py 绿/红双向证明 —— 语料 %d 份官方 .inp" % len(files))
    print("=" * 72)

    # ---------- 绿向 ----------
    green_bad = []
    for p in files:
        f = run_one(open(p, encoding="utf-8", errors="replace").read(), 8)
        hits = [x for x in f if x.level in ("BLOCKER", "WARN")]
        if hits:
            green_bad.append((os.path.relpath(p, pkg), [x.rid for x in hits]))
    print("\n[绿向] 未改动官方文件必须 0 BLOCKER / 0 WARN")
    if green_bad:
        print("  FAIL  %d / %d 份出现 BLOCKER 或 WARN：" % (len(green_bad), len(files)))
        for n, r in green_bad[:10]:
            print("        %-52s %s" % (n, r))
    else:
        print("  PASS  %d / %d 份全部为 0 BLOCKER / 0 WARN" % (len(files), len(files)))

    # ---------- 红向 ----------
    print("\n[红向] 注入故障后目标规则必须命中")
    print("  %-5s %-5s %-8s %-30s %s" % ("inj", "rule", "期望级别", "说明", "命中/适用"))
    red_fail = []
    for iid, rid, want_level, desc, fn in INJECTORS:
        applicable = detected = 0
        missed = []
        for p in files:
            raw = open(p, encoding="utf-8", errors="replace").read()
            txt, ok = fn(raw)
            if not ok or txt == raw:
                continue
            applicable += 1
            findings = run_one(txt, 6 if rid == "L10" else 8)
            got = [x for x in findings if x.rid == rid]
            if any(x.level == want_level for x in got):
                detected += 1
            elif got:
                detected += 1        # 命中了但级别不同 → 记为未通过
                red_fail.append("%s @ %s：级别不符（期望 %s，实得 %s）"
                                % (iid, os.path.basename(p), want_level, got[0].level))
            elif missed is not None and len(missed) < 3:
                missed.append(os.path.basename(p))
        rate = 100.0 * detected / applicable if applicable else 0.0
        flag = "PASS" if applicable and detected == applicable else "FAIL"
        if flag == "FAIL":
            red_fail.append("%s(%s)：%d/%d 命中，漏检例 %s" % (iid, rid, detected, applicable, missed))
        print("  %-5s %-5s %-8s %-30s %s %s %s"
              % (iid, rid, want_level, desc[:28], "%d/%d" % (detected, applicable),
                 "%.0f%%" % rate, flag))

    # ---------- 反向断言：L10 在 v8 下必须不触发 ----------
    # 口径注记（本处的「255」不是随手取的数）：
    #   255 = 全部 555 份官方 .out 中「输入回显请求了 TECH8」且版本为 8.x 者
    #       = v8 的 67 份 + v8.8 的 188 份；这 255 份里报出 W07 的有 0 份。
    #   ⚠ 该数字**在 555 与 516 两个口径下相同**：两个口径的差额 1 份是 v6.1
    #     （`penn__stard_run13`），不落在 8.x 里。故此处引用无需另标口径；
    #     但 §2.1 那类**涉及 v6.1 的数字**必须写明是 555 口径还是 516 口径。
    print("\n[反向] 版本敏感规则不得靠无脑告警刷召回")
    v8_hits = 0
    for p in files:
        raw = open(p, encoding="utf-8", errors="replace").read()
        txt, ok = inj_tech8_no_type(raw)
        if not ok:
            continue
        if any(x.rid == "L10" for x in run_one(txt, 8)):
            v8_hits += 1
    if v8_hits == 0:
        print("  PASS  注入 TECH8-无TYPE 后，--mplus-version 8 下 L10 触发 0 次"
              "（与官方 8.x 中请求 TECH8 的 255 份输出实测 0 次一致）")
    else:
        print("  FAIL  --mplus-version 8 下仍触发 L10 %d 次" % v8_hits)
        red_fail.append("L10 在 v8 下不应触发")

    print("\n" + "=" * 72)
    if green_bad or red_fail:
        print("结果：FAIL（绿向问题 %d，红向问题 %d）" % (len(green_bad), len(red_fail)))
        for x in red_fail[:20]:
            print("   -", x)
        return 1
    print("结果：PASS —— 绿向全清、红向 17 个注入器全部命中、反向断言通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
