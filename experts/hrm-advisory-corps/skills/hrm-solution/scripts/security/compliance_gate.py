#!/usr/bin/env python3
"""HRM 实战参谋团 · 合规闸门（强制终检，零三方依赖）

对任一专业产出做风险定级，作为跨模块/合规审查流程的必经终检。
返回 (gate, risk_level, dri)，由总调度在汇编前强制消费：
  - gate=BLOCKED 且 risk_level=P0 → 自动拦截并转人工 DRI，不可被绕过
  - gate=FLAGGED           → 提示用户并建议人工复核
  - gate=PASSED            → 可汇编交付

分级规则（简洁关键词/正则 + 句子级否定语境过滤，无复杂 NLP）：
  - 执行类高风险指令（主动规避/违法操作，见 EXECUTION_TERMS / EXECUTION_PATTERNS）
    → BLOCKED。若该指令所在句子含否定/禁止表达（如"不得规避社保"的教育语境），
    降级为 FLAGGED。
  - 指令前缀 + P0 高危执行词（见 INSTRUCTION_PREFIXES / P0_EXECUTION_WORDS）
    → BLOCKED（如「建议违法辞退该员工」）；同句含否定警示词或信息咨询框架词
    （介绍/流程/风险等）时视为咨询/教育语境，不拦截。
  - 主题词（仲裁/诉讼/未缴社保等，见 P0/P1/P2_TERMS）仅 FLAGGED，不自动 BLOCKED，
    以保障本技能「劳动合规教育 + 条款改写」类交付物不被误拦。
  - 子串护栏：主题词与常见中性词形成**子串巧合**时不算命中
    （如「符合规定 / 符合规范 / 符合规则」内含「合规」），见 _TERM_GUARDS。
  - 匹配前统一归一化（见 _normalize_for_matching）：NFKC 折叠全角、转小写、
    剔除空白/零宽字符/分隔符标点。否则「少缴 社保」「少缴\n社保」「规避。社保。」
    这类在词条内部插入分隔符的写法会因连续子串匹配失败而从 BLOCKED 降为 FLAGGED
    （= 自动放行），构成绕过分级的手法。词表与分级语义不变，仍偏保守、宁可多拦。

风险词典以劳动合规基线（compliance-baseline）为参照；本模块只做轻量关键词分级，
最终专业判断仍由 labor-compliance Agent 给出。

BLOCKED 时的「教育式改写引导」（``GateDecision.guidance``）：
  ``classify()`` 的判定结果（gate/risk_level/dri/reasons）是唯一的分级事实；当且仅当
  ``gate == "BLOCKED"`` 时，``GateDecision.guidance`` 会被填充为一组字符串，给出
  **如何把被拦截的执行类表述改写为合规的教育/咨询式表达**的示例（例如把「不支付
  经济补偿的风险」改写为「用人单位依法应支付经济补偿的情形、以及未支付的法定责任」）。
  ``guidance`` 只为用户提供可行的下一步，**不构成放行、不降低风险等级、不改变任何分级
  判定**——改写后仍须重新提交本闸终检，是否放行以重新分级结果为准。``PASSED`` /
  ``FLAGGED`` 决策的 ``guidance`` 恒为空列表。

CLI（``python3 compliance_gate.py --text '<TEXT>'``）：
  对文本做风险分级并将 ``GateDecision.to_dict()`` 的 JSON（``gate`` / ``risk_level``
  / ``dri`` / ``reasons``，**``guidance`` 仅在 BLOCKED 时出现**）打印到 stdout；
  **PASSED / FLAGGED 退出 0，BLOCKED 退出 3**（BLOCKED 时另向 stderr 写一行 ``[BLOCKED] …``）。
  ``--text -`` 或省略 ``--text`` 时从 stdin 读取，便于管道调用。

示例：
  python3 compliance_gate.py --text '请介绍未缴社保的风险'   # FLAGGED（教育语境），exit 0
  python3 compliance_gate.py --text '少缴社保'               # BLOCKED，exit 3
  echo '绩效制度' | python3 compliance_gate.py --text -     # PASSED，exit 0
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

# 执行类高风险指令词：主动规避法律义务 / 违法操作步骤，命中即 BLOCKED。
# 覆盖社保/公积金/个税规避、伪造材料、违法辞退方案、规避补偿等主动行为。
EXECUTION_TERMS: List[str] = [
    # 社保 / 公积金 / 个税 规避
    "规避社保", "少缴社保", "不缴社保", "规避公积金", "少缴公积金", "不缴公积金",
    "规避个税", "少缴个税", "不缴个税", "偷逃税", "偷税", "逃税", "漏税",
    "避税方案",
    # 伪造 / 虚列材料
    "虚报工资", "虚列工资", "伪造考勤", "伪造工资", "伪造劳动合同", "代签劳动合同",
    "阴阳合同", "两套账",
    # 违法辞退 / 规避法定补偿
    "违法辞退方案", "违法解除方案", "强制辞退方案",
    "规避经济补偿", "规避赔偿", "不给补偿", "不给赔偿",
    "规避加班费", "逃避加班费",
    # 拒付 / 不支付法定给付项（主动拒绝履行法定给付义务）
    # 覆盖说明：「不支付补偿 / 拒付经济补偿」等与「不给补偿 / 规避经济补偿」同义的表述
    # 若缺失会漏到 P1（FLAGGED 且 allowed=True，即允许自动交付），故同组登记，属召回补全。
    "不支付补偿", "不支付赔偿", "不支付赔偿金", "不支付经济补偿", "不支付加班费",
    "拒付补偿", "拒付赔偿", "拒付赔偿金", "拒付经济补偿",
    "不予补偿", "不予赔偿",
]
# 执行类高风险指令正则：捕捉「少缴/不缴/规避 + 插词 + 社保/公积金/个税」等变体。
# 采用 re.search（子串级），与 EXECUTION_TERMS 精确匹配互补。
#
# 【已知召回缺口 · 需语义判断，不宜用正则硬补】
# 「经第三方/个人账户代发工资以隐匿用工关系、从而回避社保」这类**间接**规避表述，
# 例如「用第三方账户发工资，避免社保」，因不含任何已登记执行词，会落到 P2/P3
# （allowed=True，允许自动交付）。同族的分隔符绕过已由 _normalize_for_matching 关闭，
# 但该类表述**不能**靠补词表或正则关闭，原因有二：
#   1) 判别依据是「意图」而非字面——「用第三方账户发工资」本身是中性的，
#      合法代发与借代发逃社保字面完全相同；
#   2) 任何以「第三方+代发+工资」为触发词的规则，都会把
#      「第三方代发工资如何缴社保」「代发工资是否合法」这类**合规咨询**一并拦下，
#      实测 10 条合法提问中 3 条被误判 BLOCKED。对以「宁可多拦」为取向的合规产品，
#      误拦咨询同样是有害缺陷。
# 因此本版**有意不补**该词条，改为：交由主理人在语义层判断（SOP 中已要求对
# 「第三方代发工资」类方案做人工复核），或由上层模型判定后再调 classify()。
# 若后续要收紧，应引入语义判定或结构化字段（如方案是否声明了代发主体），
# 而非继续加字面关键词。
EXECUTION_PATTERNS: List[re.Pattern] = [
    re.compile(r"(少缴|不缴|规避|逃缴|欠缴)\S{0,4}(社保|公积金|个税|五险一金)"),
]
# 指令前缀：将 P0 高危执行词由「主题陈述」转为「执行指令」的标记。
# 同句命中指令前缀 + P0_EXECUTION_WORDS 且无否定警示/咨询框架时 → BLOCKED。
INSTRUCTION_PREFIXES: List[str] = [
    "建议", "请", "帮我", "帮我做", "务必", "需要", "要求", "给我",
]
# 信息咨询框架词：句子含这些词视为「咨询/教育」而非「执行指令」，不触发指令级 BLOCKED，
# 避免「请介绍未缴社保风险」这类合规教育提问被误拦。
INFO_REQUEST_FRAMING: List[str] = [
    "介绍", "说明", "分析", "讲解", "科普", "讲讲", "解释", "了解",
    "流程", "风险", "后果", "含义", "是什么", "有哪些", "怎么办", "为何", "为什么",
    "注意", "提示",
]
# P0 高危执行词：仅当与指令前缀组合（执行指令）时才 BLOCKED；单独出现走主题词 FLAGGED。
P0_EXECUTION_WORDS: List[str] = [
    "违法辞退", "违法解除", "强制辞退", "随意辞退", "逼迫离职", "强迫离职",
    "伪造考勤", "伪造工资", "伪造劳动合同", "阴阳合同", "两套账",
    "未缴社保", "未缴公积金", "未签合同",
]
# 否定/禁止表达：命中所在句含这些词视为教育/警示语境，BLOCKED 降级为 FLAGGED
NEGATION_MARKERS: List[str] = [
    "不应", "不应该", "不得", "不能", "不可", "不要", "切勿", "禁止", "严禁",
    "切忌", "勿",
]
# 覆盖不变式：「随意辞退 / 逼迫离职 / 强迫离职」3 词同步登记于 P0_EXECUTION_WORDS 与
# 本表，保证 P0_EXECUTION_WORDS ⊆ EXECUTION_TERMS ∪ P0_TERMS，避免部分执行式请求逃脱拦截。
# P0 主题词：高风险主题（教育/文档语境仅 FLAGGED，建议人工复核，不自动 BLOCKED）
P0_TERMS: List[str] = [
    "违法解除", "违法辞退", "强制辞退", "随意辞退", "逼迫离职", "强迫离职",
    "未签合同", "未缴社保", "未缴公积金",
    "童工", "强迫劳动", "竞业限制违约", "集体裁员", "罢工", "仲裁", "诉讼",
]
# P1：需谨慎、建议人工复核
P1_TERMS: List[str] = [
    "解除合同", "辞退", "经济补偿", "赔偿金", "竞业", "调岗", "降薪",
    "试用期解除", "绩效不合格解除", "员工手册", "规章制度", "加班费争议",
]
# P2：一般合规注意
P2_TERMS: List[str] = [
    "合同", "条款", "合规", "劳动法", "社保", "公积金", "年休假", "病假", "产假",
]

# 子串护栏：个别主题词会与常见中性词形成**子串巧合**，命中它并不代表真实语义。
# 典型：「符合规定 / 符合规范 / 符合规则」中都内含「合规」二字，但整句语义是中性的。
# 对该类词改用正则护栏匹配（负向后顾 = 该「合」字之前不是「符」）。
# 护栏只影响「某词是否算命中」，不改变任何分级规则。
_TERM_GUARDS: Dict[str, "re.Pattern[str]"] = {
    "合规": re.compile(r"(?<!符)合规"),
}

# ---------------------------------------------------------------------------
# 匹配用归一化（防「分隔符插入」绕过）
# ---------------------------------------------------------------------------
# 问题：执行词/主题词一律按**连续子串**匹配，故在词条内部插入空白、换行、
# 零宽字符或标点即可让匹配失败（实测「少缴 社保」「少缴\n社保」由 BLOCKED 降为
# FLAGGED/P2，即自动放行）。
# 修法：匹配前统一归一化 —— NFKC 折叠（`１３８`→`138`、全角标点→半角）、
# 转小写、剔除一切非字母数字字符（ASCII/Unicode 空白、零宽字符 U+200B-200D /
# U+FEFF、ASCII 与全角分隔符标点）。词表全为中文词条、不含标点，故该归一化
# 不改变任何词的语义，只是让「插入了分隔符的同一个词」重新变回连续子串。
# 词表本身与分级语义均不变（仍偏保守、宁可多拦）。
def _normalize_for_matching(s: str) -> str:
    """返回用于词条匹配的归一化文本：NFKC + 小写 + 剔除分隔符/空白/零宽字符。"""
    return "".join(ch for ch in unicodedata.normalize("NFKC", s).lower() if ch.isalnum())


# 否定词同样按归一化形式比对（当前词表归一化后为恒等，预留后续词表扩展）。
_NEGATION_MARKERS_NORM: Tuple[str, ...] = tuple(
    _normalize_for_matching(m) for m in NEGATION_MARKERS)

# ---------------------------------------------------------------------------
# 教育式改写引导（仅用于 BLOCKED 决策的 guidance 字段）
# ---------------------------------------------------------------------------
# 说明：以下内容**只影响 BLOCKED 决策的 guidance 输出文本**，绝不参与、也绝不改变
# 任何分级判定（gate / risk_level / dri / reasons 完全不受其影响）。
# 每条为 (命中词标记, 合规改写示例)，按命中词匹配第一条即收录其示例。
_REWRITE_HINTS: List[Tuple[Tuple[str, ...], str]] = [
    (("经济补偿", "赔偿金", "赔偿", "补偿"),
     "把「不支付经济补偿（赔偿金）的风险」改为客观陈述「用人单位依法应支付经济补偿"
     "（赔偿金）的情形，以及未依法支付的法定责任」。"),
    (("加班费",),
     "把「规避/不支付加班费」改为陈述「加班费支付的法定标准与计算口径，以及未依法支付"
     "的法律后果」。"),
    (("社保",),
     "把「不缴/少缴社保」改为陈述「用人单位依法缴纳社会保险的义务、缴费基数规则，以及"
     "未依法缴纳的法律责任」。"),
    (("公积金",),
     "把「不缴/少缴公积金」改为陈述「住房公积金的法定缴存义务及未依法缴存的责任」。"),
    (("个税", "偷税", "逃税", "漏税", "避税", "阴阳合同", "两套账"),
     "把「规避个税/避税方案」改为陈述「代扣代缴个人所得税的法定义务与税务合规要点」。"),
    (("伪造", "虚报", "虚列", "代签"),
     "把「伪造/虚列材料」改为陈述「合法用工文书与凭证管理要求，以及伪造材料的法律后果」。"),
    (("违法辞退", "违法解除", "强制辞退", "辞退"),
     "把「违法辞退方案」改为陈述「合法解除劳动合同的法定情形与程序，以及违法解除的法律"
     "风险」。"),
]

# 声明的固定后缀：显式否定「构成放行」。
_GUIDANCE_NOT_CLEARANCE = (
    "以上仅为合规改写方向，不构成本次放行，也不降低本决策（BLOCKED/P0）的风险等级；"
    "改写后须重新提交本闸终检，是否放行以重新分级结果为准。"
)


def _build_guidance(hits: List[str]) -> List[str]:
    """为 BLOCKED 决策生成「教育式改写引导」（纯输出文本，不参与分级）。

    返回一组字符串：说明拦截的是执行类表述、给出合规改写示例、并显式声明**不构成放行**。
    本函数对 gate/risk_level/dri/reasons 无任何写入，故不会改变任何分级结果。
    """
    g: List[str] = []
    g.append(
        "本条被拦截的是「主动规避法律义务 / 违法操作」类表述，命中：%s。"
        % "、".join(hits)
    )
    g.append("可改写为合规的教育/咨询式表述（保留信息价值，去掉执行指令）：")
    matched = False
    for markers, tip in _REWRITE_HINTS:
        if any(any(m in h for m in markers) for h in hits):
            g.append("  - " + tip)
            matched = True
    if not matched:
        g.append(
            "  - 将「如何规避/不支付某项法定义务」改写为「该项法定义务的适用情形、法定标准"
            "与未依法履行的法律责任」。"
        )
    g.append(_GUIDANCE_NOT_CLEARANCE)
    return g


def _term_hits(s: str, terms: List[str]) -> List[str]:
    """统计主题词命中（对 _TERM_GUARDS 中登记的词走正则护栏，其余保持子串匹配）。"""
    out: List[str] = []
    for t in terms:
        g = _TERM_GUARDS.get(t)
        if g is not None:
            if g.search(s):
                out.append(t)
        elif t in s:
            out.append(t)
    return out


def _split_normalized_sentences(s: str) -> List[str]:
    """按句末标点切句并逐句归一化（保留原始分句边界，只在句内做匹配归一化）。"""
    out: List[str] = []
    for seg in re.split(r"[。！？!?；;\n]", s):
        norm = _normalize_for_matching(seg)
        if norm:
            out.append(norm)
    return out


def _all_execution_hits_negated(s: str, hits: List[str]) -> bool:
    """教育语境判定：所有命中执行词的句子均含否定/禁止表达时返回 True。

    例如「企业不得规避社保缴纳」→ True（教育警示），降级为 FLAGGED；
    「建议规避社保缴纳」→ False，保持 BLOCKED。

    命中词与否定词均在归一化文本上比对（见 _normalize_for_matching），
    故「不 得规避」这类插入分隔符的写法不会被误判为「无否定」。
    若命中词因跨句/跨分隔符而无法定位于任何单句（如「规避。社保。」），
    则无法确认其否定语境，一律返回 False（不降级）——宁可多拦。
    """
    sentences = _split_normalized_sentences(s)
    if not sentences:
        return False
    hit_sentences = [sent for sent in sentences if any(t in sent for t in hits)]
    if not hit_sentences:
        return False
    return all(any(m in sent for m in _NEGATION_MARKERS_NORM) for sent in hit_sentences)


def _instruction_execution_hits(s: str) -> List[str]:
    """指令前缀 + P0 高危执行词 同句命中，且无否定警示/咨询框架时返回命中词，否则空列表。

    例：「建议违法辞退该员工且未缴社保」→ ["违法辞退", "未缴社保"] → BLOCKED；
    「请介绍未缴社保的风险」「不得违法辞退员工」→ []（咨询/教育语境，不拦截）。
    """
    hits: List[str] = []
    for sent in _split_normalized_sentences(s):
        if not any(p in sent for p in INSTRUCTION_PREFIXES):
            continue
        ws = [w for w in P0_EXECUTION_WORDS if w in sent]
        if not ws:
            continue
        if any(m in sent for m in _NEGATION_MARKERS_NORM):
            continue  # 教育/警示语境，不按指令拦截
        if any(f in sent for f in INFO_REQUEST_FRAMING):
            continue  # 咨询/信息类提问，不按指令拦截
        for w in ws:
            if w not in hits:
                hits.append(w)
    return hits


@dataclass
class GateDecision:
    gate: str           # PASSED | FLAGGED | BLOCKED
    risk_level: str     # P0 | P1 | P2 | P3
    dri: str            # agent_id 或 人工
    reasons: List[str]
    # 仅 gate=="BLOCKED" 时填充的教育式改写引导；PASSED/FLAGGED 恒为空列表。
    # guidance 是「可行的下一步」提示，不构成放行，也不改变任何分级判定。
    guidance: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = {
            "gate": self.gate, "risk_level": self.risk_level,
            "dri": self.dri, "reasons": self.reasons,
        }
        # 仅 BLOCKED（guidance 非空）时输出，保证 PASSED/FLAGGED 的 JSON 与既有基线逐字节一致。
        if self.guidance:
            d["guidance"] = self.guidance
        return d


def classify(text: str) -> GateDecision:
    """对文本做风险分级（输入为产出摘要/原文，大小写不敏感）。

    优先级：执行类指令（EXECUTION_TERMS/PATTERNS，BLOCKED）>
    指令前缀+P0 执行词（BLOCKED）> P0 主题词（FLAGGED）> P1 > P2。
    执行词所在句全为否定/教育语境时降级为 FLAGGED（P0），避免误拦合规教育产出。
    """
    if not text:
        return GateDecision("PASSED", "P3", "labor-compliance", [])
    s = _normalize_for_matching(text)
    hits_exe = [t for t in EXECUTION_TERMS if t in s]
    hits_exe += [m.group(0) for p in EXECUTION_PATTERNS for m in p.finditer(s)]
    hits_exe = list(dict.fromkeys(hits_exe))  # 去重
    hits_p0 = _term_hits(s, P0_TERMS)
    hits_p1 = _term_hits(s, P1_TERMS)
    hits_p2 = _term_hits(s, P2_TERMS)

    if hits_exe:
        # 否定语境按**原文**分句判断（内部逐句归一化）：命中词在归一化全文上求得，
        # 而「该命中词所在句是否被否定」需保留原始分句边界。
        if _all_execution_hits_negated(text, hits_exe):
            # 教育/警示语境（如「不得规避社保」）→ 降级为 FLAGGED，可交付
            return GateDecision("FLAGGED", "P0", "labor-compliance", hits_exe)
        return GateDecision("BLOCKED", "P0", "人工 DRI", hits_exe,
                            _build_guidance(hits_exe))
    inst_hits = _instruction_execution_hits(text)
    if inst_hits:
        # 指令前缀 + P0 高危执行词（如「建议违法辞退该员工」）→ 执行类指令，BLOCKED
        return GateDecision("BLOCKED", "P0", "人工 DRI", inst_hits,
                            _build_guidance(inst_hits))
    if hits_p0:
        return GateDecision("FLAGGED", "P0", "labor-compliance", hits_p0)
    if hits_p1:
        return GateDecision("FLAGGED", "P1", "labor-compliance", hits_p1)
    if hits_p2:
        return GateDecision("FLAGGED", "P2", "labor-compliance", hits_p2)
    return GateDecision("PASSED", "P3", "labor-compliance", [])


def enforce_final_gate(text: str) -> Tuple[GateDecision, bool]:
    """强制终检：返回决策与是否允许自动交付（BLOCKED 不允许）。"""
    d = classify(text)
    return d, d.gate != "BLOCKED"


class ComplianceBlocked(RuntimeError):
    """产出被合规闸 BLOCKED，禁止签名放行（需转人工 DRI）。"""


def finalize(env, output_text: str) -> GateDecision:
    """终检并据结果设定信封合规字段；BLOCKED 时抛 ComplianceBlocked，阻止签名放行。

    编排层在汇编最终产出前必须调用本函数：只有非 BLOCKED 的产出才能被签名并放行，
    从而从结构上杜绝「自填 PASSED 使合规闸失效」的风险。
    """
    from .envelope import Envelope  # 延迟导入，避免循环依赖

    if not isinstance(env, Envelope):
        raise TypeError("finalize 需要 Envelope 实例")
    d, allowed = enforce_final_gate(output_text)
    env.compliance = {
        "gate": d.gate, "risk_level": d.risk_level,
        "dri": d.dri, "reasons": d.reasons,
    }
    # 仅 BLOCKED（guidance 非空）时带上引导；PASSED/FLAGGED 的 compliance 键集保持 4 个不变。
    if d.guidance:
        env.compliance["guidance"] = d.guidance
    if not allowed:
        raise ComplianceBlocked(
            f"产出被合规闸 BLOCKED（{d.risk_level}）：{d.reasons}；"
            f"禁止签名放行，需转人工 DRI。"
        )
    return d


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI：对 --text（或 stdin）做分级并输出 JSON；BLOCKED 退出码为 3。"""
    ap = argparse.ArgumentParser(
        prog="compliance_gate.py",
        description="HRM 合规闸门 · 文本风险分级（PASSED/FLAGGED → 0；BLOCKED → 3）",
        epilog="示例: python3 compliance_gate.py --text '少缴社保'",
    )
    ap.add_argument(
        "--text",
        default=None,
        help="待分级文本；传 '-' 或省略则从 stdin 读取",
    )
    args = ap.parse_args(argv)

    text = args.text
    if text is None or text == "-":
        text = sys.stdin.read()

    decision = classify(text)
    print(json.dumps(decision.to_dict(), ensure_ascii=False))
    if decision.gate == "BLOCKED":
        sys.stderr.write("[BLOCKED] %s\n" % "；".join(decision.reasons or []))
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
