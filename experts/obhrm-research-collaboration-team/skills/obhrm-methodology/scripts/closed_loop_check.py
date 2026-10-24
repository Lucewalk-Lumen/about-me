#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""成稿自检违规检查器：基于 closed_loop.json 的审计步骤，对草稿做标红报告。

读取草稿 Markdown / 纯文本与 closed_loop.json（安全原则 + 审计步骤定义），可选提供已读
文献清单（readings）用于引证核验，输出四类违规的标红报告：

  ① 引用无对应（审计7 引证完整性核查）
  ② 连续 ≥8 字原文重合（审计6 转述保真度）
  ③ 夸张表述（审计10 客观语调过滤）
  ④ 超范围段落 / 无支撑论断（R3 标注无支撑 / R4 不超范围）

仅依赖 Python 标准库。检查为启发式（无 NLP 模型），结果供研究者裁决，不自动改写。

用法
----
    python closed_loop_check.py <draft.md> --rules ../../literature-review/knowledge/closed_loop.json
                           [--readings READINGS.md] [--out report.md]

退出码
------
    0  未发现违规
    1  发现违规（报告已生成）
    2  输入 / 规则文件错误
"""


# 确保套件包可导入（包目录在上级目录）
import os, sys
_skill_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _skill_dir not in sys.path:
    sys.path.append(_skill_dir)
import argparse
import json
import os
import re
import sys

# --out 输出路径强制 范围校验
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from obhrm_research_base.core.safe_path import resolve_safe_output  # noqa: E402

# 引用（括号内）：(Author, 2020) 或 （作者，2020）
CITATION_RE = re.compile(r"[（(]([^（）()]{1,60}?)(?:,|，)\s*((?:19|20)\d{2}[a-z]?)[）)]")
# 引用（叙述式）：作者（2020）/ Author (2020)，作者段在括号之外
NARRATIVE_RE = re.compile(
    r"([A-Za-z一-龥][A-Za-z一-龥\s,.\-]{1,40}?)\s*[（(]((?:19|20)\d{2}[a-z]?)[）)]")
# 作者段连接符（用于切分多位作者）
# 'and' 必须加词边界 \b，否则会误切姓名内部字母（如 Sandberg→S/berg、Fernandez→Fern/ez）
_AUTHOR_SEP = re.compile(r"\s*(?:&|与|和|\band\b|,|，)\s*")
# 叙述式引用尾部的常见动词，避免把"研究表明（2020）"误判为作者
_NARRATIVE_VERB_TAILS = (
    "表明", "显示", "指出", "认为", "发现", "说明", "揭示", "预示", "研究",
    "综述", "分析", "提出", "强调", "总结", "探讨", "考察", "刻画", "关注",
    "呼吁", "描述", "界定", "区分", "揭示", "主张", "建议", "说明",
)

# 夸张表述关键词（Skill10）
EXAGGERATION_KEYWORDS = [
    "开创性", "革命性", "填补了重大空白", "填补重大空白", "巨大空白",
    "完全空缺", "重大突破", "前所未有", "首次提出", "里程碑式",
    "颠覆性", "业界领先", "提供重要参考", "划时代",
]

# 论断动词（用于"无支撑论断"启发式判定）
ASSERTION_RE = re.compile(r"(表明|证明|发现|显示|指出|认为|揭示|说明|预示)")

# 引用标记：括号（中/英）内含 4 位年份（如 （Smith, 2020）/（张三，2019））
# 或含"见"（如 （见 …）），或方括号数字上标（如 [1] / [12] / [1, 2]），
# 满足任一即视为已有文献支撑，豁免"无支撑论断"的误报。
CITATION_MARKER_RE = re.compile(
    r"[（(]"               # 左括号（中文或英文）
    r"[^）)]*?"            # 括号内的非贪婪内容
    r"(?:"                 # 满足以下任一即视为引用标记：
    r"(?:19|20)\d{2}"      #   含 4 位年份
    r"|见"                 #   或含"见"（如 （见 …））
    r")"
    r"[^）)]*?"            # 继续消费括号内容
    r"[）)]"               # 右括号（中文或英文）
    r"|\[\d[\d, ]*\]"      #   或方括号数字引用，如 [1] / [12] / [1, 2]
)


def load_rules(path):
    """加载 closed_loop.json 规则文件。

    Args:
        path: closed_loop.json 路径。

    Returns:
        dict: 解析后的规则字典。

    Raises:
        FileNotFoundError: 文件不存在。
        ValueError: JSON 解析失败或缺少 skills 字段。
    """
    if not os.path.isfile(path):
        raise FileNotFoundError("规则文件未找到: %s" % path)
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict) or "skills" not in data:
        raise ValueError("规则文件缺少 skills 字段: %s" % path)
    return data


def load_readings(path):
    """加载已读文献清单，返回规范化条目列表与 8-gram 集合。

    Args:
        path: readings 文件路径；为 None 时返回空。

    Returns:
        Tuple[List[str], set]: (规范化条目列表, 来自条目的 CJK 8-gram 集合)。
    """
    if not path or not os.path.isfile(path):
        return [], set()
    with open(path, encoding="utf-8") as fh:
        raw_lines = [ln.strip() for ln in fh if ln.strip()]
    entries = [re.sub(r"\s+", " ", ln).lower() for ln in raw_lines]
    grams = set()
    for entry in entries:
        cjk = "".join(ch for ch in entry if "\u4e00" <= ch <= "\u9fff")
        for i in range(len(cjk) - 7):
            grams.add(cjk[i:i + 8])
    return entries, grams


def _author_norm(author):
    """从引用作者段提取归一化姓名（去标点，仅留字母与汉字）。"""
    return re.sub(r"[^A-Za-z一-龥]", "", author).strip()


def _strip_etal(author):
    """去除 '等' / 'et al.' 等表示多作者的省略词。"""
    return re.sub(r"等\.?|et\s+al\.?", "", author, flags=re.IGNORECASE)


def _strip_initials(chunk):
    """去除英文姓名中的名缩写（如 'A.'、'K.'），保留姓。

    - "Last, F. M." → "Last"
    - "F. M. Last" → "Last"（去孤立单字母后取最后一段）
    """
    if "," in chunk:
        chunk = chunk.split(",")[0]
    else:
        chunk = re.sub(r"(?<![A-Za-z])\b[A-Za-z]\b\.?", " ", chunk)
        parts = [p for p in chunk.split() if p]
        if parts:
            chunk = parts[-1]
    return chunk


def extract_surname_tokens(author):
    """从作者段提取姓氏 token 列表（归一化小写）。

    支持中英文、'等'/'et al.'、'&'/'与'/'和'/'and' 连接、名缩写。
    用于跨条目稳定匹配，消除格式噪声带来的误报。
    """
    author = _strip_etal(author)
    author = author.replace("与", "&").replace("和", "&")
    tokens = []
    for chunk in _AUTHOR_SEP.split(author):
        chunk = chunk.strip()
        if not chunk:
            continue
        chunk = _strip_initials(chunk)
        norm = _author_norm(chunk).lower()
        if norm:
            tokens.append(norm)
    return tokens


def _entry_author_part(entry):
    """从文献条目中提取作者段（年份括号之前的部分）。"""
    m = re.match(r"^\s*(.*?)\s*[（(](?:19|20)\d{2}", entry)
    return m.group(1) if m else ""


def citation_supported(author, year, readings_entries):
    """启发式判断引用是否在已读文献中可对应。

    按姓氏 token 集合匹配：引用的全部姓氏 token 都出现在某条同年文献的
    作者姓氏集合中，即视为可对应。可正确处理名缩写（Keegan, A.）、
    '等'/'et al.' 省略、叙述式与括号式混用。

    Args:
        author: 引用中的作者段（如 "Smith" / "Keegan & Meijerink" / "裴嘉良等"）。
        year: 引用中的年份（如 "2020"）。
        readings_entries: 规范化文献条目列表。

    Returns:
        bool: True 表示存在可对应的已读文献。
    """
    cite_tokens = extract_surname_tokens(author)
    if not cite_tokens:
        return False
    for entry in readings_entries:
        if year not in entry:
            continue
        entry_tokens = extract_surname_tokens(_entry_author_part(entry))
        if not entry_tokens:
            continue
        if all(ct in entry_tokens for ct in cite_tokens):
            return True
    return False


def _record_citation(issues, seen, lineno, cite, author, year,
                     has_readings, readings_entries):
    """去重后登记一条引用（括号式与叙述式可能指向同一引用）。"""
    key = (lineno, year, tuple(sorted(extract_surname_tokens(author))))
    if key in seen:
        return
    seen.add(key)
    if not has_readings:
        issues.append({"lineno": lineno, "cite": cite,
                       "supported": None, "unverifiable": True})
    else:
        ok = citation_supported(author, year, readings_entries)
        issues.append({"lineno": lineno, "cite": cite,
                       "supported": ok, "unverifiable": False})


def check_citations(lines, readings_entries):
    """提取草稿中所有引用（括号式 + 叙述式）并判定是否可对应已读文献。

    Returns:
        List[dict]: 每条含 lineno / cite / supported / unverifiable。
    """
    issues = []
    seen = set()
    has_readings = bool(readings_entries)
    for i, line in enumerate(lines, 1):
        for m in CITATION_RE.finditer(line):
            _record_citation(issues, seen, i, m.group(0), m.group(1),
                             m.group(2), has_readings, readings_entries)
        for m in NARRATIVE_RE.finditer(line):
            author = m.group(1).strip()
            if author.endswith(_NARRATIVE_VERB_TAILS):
                continue  # 形如"研究表明（2020）"，非作者引用
            _record_citation(issues, seen, i, m.group(0), author,
                             m.group(2), has_readings, readings_entries)
    return issues


def check_verbatim_overlap(lines, readings_grams):
    """检测草稿中与已读文献连续 ≥8 字原文重合。

    Returns:
        List[dict]: 每条含 lineno / snippet。
    """
    issues = []
    if not readings_grams:
        return issues
    for i, line in enumerate(lines, 1):
        for run in re.findall(r"[一-鿿]{8,}", line):
            matched = None
            for j in range(len(run) - 7):
                g = run[j:j + 8]
                if g in readings_grams:
                    matched = g
                    break
            if matched:
                issues.append({"lineno": i, "snippet": matched})
                break  # 每行至多报一处，降低噪声
    return issues


def check_exaggeration(lines):
    """扫描夸张表述关键词（Skill10）。

    Returns:
        List[dict]: 每条含 lineno / phrase。
    """
    issues = []
    for i, line in enumerate(lines, 1):
        for ph in EXAGGERATION_KEYWORDS:
            if ph in line:
                issues.append({"lineno": i, "phrase": ph})
    return issues


def check_unsupported(lines):
    """标记无引用支撑的强论断（R3 标注无支撑 / R4 不超范围）。

    启发式：含论断动词但本行无年份引用，且无连续 ≥8 字与已读文献重合，
    视为"无支撑论断"，强制要求标注「无文献支撑」。

    Returns:
        List[dict]: 每条含 lineno / text。
    """
    issues = []
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped:
            continue
        # 白名单豁免：自述性陈述（以"本文"开头）或已带引用标记，
        # 视为已有文献支撑，不计入无支撑论断。
        if stripped.startswith("本文") or CITATION_MARKER_RE.search(line):
            continue
        if ASSERTION_RE.search(line) and not re.search(r"(?:19|20)\d{2}", line):
            issues.append({"lineno": i, "text": stripped[:120]})
    return issues


def check_burstiness(draft_text):
    """句长均匀度（burstiness）启发式检测，仅作风格提示，绝不阻断/计入违规。

    统计草稿各句字符长度，若出现「连续 ≥5 句，句长两两之差均 < 3 字」，
    则给出一条 AI 指纹疑似提示。刻意保守（阈值宽松）以避免误杀正常中文综述。

    Returns:
        List[dict]: 每条含 start / end（句序号，1 起）/ lengths。
    """
    # 中英文句子切分：以句末标点断句
    sentences = [s.strip() for s in re.split(r"[。！？!?；;\n]+", draft_text) if s.strip()]
    lengths = [len(s) for s in sentences]
    hints = []
    n = len(lengths)
    i = 0
    while i < n:
        j = i
        # 向后扩展：只要相邻句长差 < 3 就并入同一段
        while j + 1 < n and abs(lengths[j + 1] - lengths[j]) < 3:
            j += 1
        run_len = j - i + 1
        if run_len >= 5:
            hints.append({"start": i + 1, "end": j + 1,
                          "lengths": lengths[i:j + 1]})
        i = j + 1
    return hints


def generate_report(draft_path, rules_path, readings_path, citations,
                    verbatim, exaggeration, unsupported, style_hints=None,
                    rules=None):
    """生成标红报告 Markdown 文本。"""
    has_readings = readings_path is not None
    violation_count = (
        sum(1 for c in citations if c.get("supported") is False)
        + len(verbatim) + len(exaggeration) + len(unsupported)
    )

    lines = []
    lines.append("# 成稿自检违规检查报告")
    lines.append("")
    lines.append("- 检查草稿: `%s`" % draft_path)
    lines.append("- 规则: `%s`" % rules_path)
    if has_readings:
        lines.append("- 已读文献: `%s`" % readings_path)
    else:
        lines.append("- 已读文献: 未提供（引用核验标记为“无法核验”，需人工确认）")
    lines.append("- 发现问题: **%d** 处" % violation_count)
    lines.append("")
    if rules is not None:
        _iron = rules.get("iron_rules", [])
        _skl = rules.get("skills", [])
        lines.append("- 审计依据: `closed_loop.json`（铁律 %d 条；审计技能 %d 个）"
                     % (len(_iron), len(_skl)))
    else:
        lines.append("- 审计依据: 内置启发式（未加载 closed_loop.json）")
    lines.append("")
    lines.append("> 本报告由启发式检查生成（无 NLP 模型），所有标记供研究者裁决，不自动改写。")
    lines.append("")

    # 跳过检查提示（未提供已读文献清单）——明确“未检查”而非“通过”，避免误判为通过
    if not has_readings:
        lines.append("> [!] **跳过检查（未提供已读文献清单 `--readings`）**：下列承重墙检查"
                     "因缺少已读文献而未运行，相关项结果为“未检查”而非“通过”，"
                     "必须由研究者人工确认：")
        lines.append("> - S6 转述保真度（连续 ≥8 字原文重合）")
        lines.append("> - S7 引证完整性（引用是否在已读文献中可对应）")
        lines.append("")

    # ① 引用无对应
    lines.append("## 一、引用无对应（Skill7 引证完整性核查 · 承重墙）")
    cite_v = [c for c in citations if c.get("supported") is False]
    if not citations:
        lines.append("- 未发现引用标记。")
    elif cite_v:
        for c in cite_v:
            lines.append("- L%d: 引用 `%s` 在已读文献中**无对应** → [!] 标红，需补文献或删除引用"
                         % (c["lineno"], c["cite"]))
    else:
        if has_readings:
            lines.append("- 所有引用均可在已读文献中对应。[OK]")
        else:
            lines.append("- 发现 %d 处引用，但**未提供已读文献清单**，无法核验，需人工确认："
                         % len(citations))
            for c in citations:
                lines.append("  - L%d: `%s`" % (c["lineno"], c["cite"]))
    lines.append("")

    # ② 原文重合
    lines.append("## 二、连续≥8字原文重合（Skill6 转述保真度）")
    if verbatim:
        for v in verbatim:
            lines.append("- L%d: 与已读文献重合「%s」 → [!] 需转述或加引号并标注出处"
                         % (v["lineno"], v["snippet"]))
    else:
        if has_readings:
            lines.append("- 未发现与已读文献连续≥8字原文重合。[OK]")
        else:
            lines.append("- [!] 已跳过：未提供已读文献清单（`--readings`），无法执行连续≥8字"
                         "原文重合核查（审计步骤 S6）。该检查未运行，不代表无重合，"
                         "需人工确认或补 `--readings`。")
    lines.append("")

    # ③ 夸张表述
    lines.append("## 三、夸张表述（Skill10 客观语调过滤）")
    if exaggeration:
        for e in exaggeration:
            lines.append("- L%d: 发现「%s」 → [!] 替换为客观、与证据强度匹配的陈述"
                         % (e["lineno"], e["phrase"]))
    else:
        lines.append("- 未发现夸张表述关键词。[OK]")
    lines.append("")

    # ④ 超范围 / 无支撑
    lines.append("## 四、超范围段落 / 无支撑论断（R3 标注无支撑 / R4 不超范围）")
    if unsupported:
        for u in unsupported:
            lines.append("- L%d: 含论断但无引用支撑 → [!] 必须标注「无文献支撑」或补引"
                         % u["lineno"])
            lines.append("  > %s" % u["text"])
    else:
        lines.append("- 未发现无支撑论断。[OK]")
    lines.append("")

    lines.append("---")
    # 风格提示（非阻断）：不计入违规数，仅供参考，避免误杀正常长句中文综述。
    lines.append("")
    lines.append("## 风格提示（非阻断，不计入违规）")
    if style_hints:
        for h in style_hints:
            lines.append("- 疑似 AI 指纹：句长过于均匀（burstiness 低），"
                         "建议增加长短句变化 —— 第 %d–%d 句句长接近（%s）"
                         % (h["start"], h["end"],
                            ", ".join(str(x) for x in h["lengths"])))
        lines.append("")
        lines.append("> 以上仅为写作风格建议，**不是违规、不阻断、不计入违规数**。")
    else:
        lines.append("- 未发现句长过于均匀的段落。[OK]")
    lines.append("")

    lines.append("---")
    lines.append("安全原则提醒：不编引用 / 不归观点 / 标注无支撑 / 不超范围。")
    return "\n".join(lines)


def main(argv):
    """命令行入口。"""
    ap = argparse.ArgumentParser(description="成稿自检违规标红检查（读 closed_loop.json）")
    ap.add_argument("draft", help="待检查的草稿 Markdown / 纯文本")
    ap.add_argument("--rules", required=True, help="closed_loop.json 规则文件路径")
    ap.add_argument("--readings", default=None, help="已读文献清单（用于引证核验）")
    ap.add_argument("--out", default=None, help="报告输出路径（默认 <draft>.closed_loop_report.md）")
    args = ap.parse_args(argv)

    if not os.path.isfile(args.draft):
        print("错误: 草稿文件未找到: %s" % args.draft, file=sys.stderr)
        return 2
    try:
        rules = load_rules(args.rules)
    except (FileNotFoundError, ValueError) as exc:
        print("错误: %s" % exc, file=sys.stderr)
        return 2

    with open(args.draft, encoding="utf-8") as fh:
        draft_text = fh.read()
    lines = draft_text.splitlines()

    readings_entries, readings_grams = load_readings(args.readings)

    citations = check_citations(lines, readings_entries)
    verbatim = check_verbatim_overlap(lines, readings_grams)
    exaggeration = check_exaggeration(lines)
    unsupported = check_unsupported(lines)
    style_hints = check_burstiness(draft_text)

    report = generate_report(args.draft, args.rules, args.readings,
                              citations, verbatim, exaggeration, unsupported,
                              style_hints=style_hints, rules=rules)

    out_path = args.out
    if out_path is None:
        base, _ = os.path.splitext(args.draft)
        out_path = base + ".closed_loop_report.md"
    # 强制 范围校验，防止 --out 写出允许范围
    try:
        out_path = str(resolve_safe_output(out_path, base=os.getcwd()))
    except ValueError as exc:
        print("错误(--out): %s" % exc, file=sys.stderr)
        return 2
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(report)

    cite_v = sum(1 for c in citations if c.get("supported") is False)
    total = cite_v + len(verbatim) + len(exaggeration) + len(unsupported)
    print("报告已生成: %s" % out_path)
    print("违规统计: 引用无对应=%d, 原文重合=%d, 夸张表述=%d, 无支撑=%d"
          % (cite_v, len(verbatim), len(exaggeration), len(unsupported)))
    return 1 if total > 0 else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
