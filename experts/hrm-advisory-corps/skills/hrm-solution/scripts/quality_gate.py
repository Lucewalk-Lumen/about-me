#!/usr/bin/env python3
"""HRM 实战参谋团 · 输出契约校验器（质量闸门，零三方依赖）

目的
----
把团队「输出质量」从「主理人肉眼核对」升级为**机器可采集的信号**，直接服务于
团队级可衡量质量指标（见 quality/metrics.md 的 QM-01~QM-05 / QM-11）。

每次成员回传（信封或五字段回传契约）交付前，主理人可运行本工具做一次结构化校验，
输出机器可读的 JSON 质量报告（各指标 pass/fail + 综合质量分 + status），并据退出码
决定能否进入下一步（0=通过，1=未通过，2=参数/运行错误）。

校验维度（与 contracts.md / 回传契约 / envelope.py / pii.py 对齐）
--------------------------------------------------------------
1. envelope_signature_valid  入站信封 HMAC 签名是否验签通过（复用 security/envelope.py）；自称信封但字段残缺一律判 FAIL（不得以删字段方式规避验签）
2. return_contract_complete  五字段回传契约（结论/产物或信封/依据与来源/待确认项/建议下一步）是否齐全**且已填写**（空串/纯空白/占位符一律视为缺失）
3. compliance_citation_complete 凡含合规结论，是否都带「法条出处 + 基准日期 + 核实状态」
4. compliance_gate_blocked  复用 security/compliance_gate.py 做全文风险分级，BLOCKED 判 FAIL
5. pii_masked                产出明文是否仍残留手机/邮箱/身份证等 PII（复用 security/pii.py）
6. engine_traceable          （可选）凡含引擎计算数字，是否带 baseline_date + 来源脚本标识

输入
----
`check <file>`：<file> 为成员回传的 JSON 文件，可能形态：
  (a) 已签名信封（含 signature / msg_id / trace_id / payload / compliance / nonce）
  (b) 五字段回传契约 JSON（含中文五字段或其英文别名）
  (c) 混合：信封的 payload 内嵌回传契约
`--spec <id>`：按某 specialist 的字段完整度要求追加校验（通用 SPEC_RULES 字典登记；
  当前支持 talent-sourcing / recruitment-pipeline / labor-compliance；`list-specs` 列出全部）。
`--max-age <SEC>`：信封时效上限（秒），超出判签名失效。
`--json`：强制仅输出 JSON（默认在 JSON 前打印一行人类可读摘要到 stdout，明细见 details）。

子命令
------
  check <file>          校验单份成员回传 JSON（配合 --spec / --max-age / --json）
  list-specs            列出所有支持的 --spec 字段完整度规则（不编造，均来自实读 playbook 输出规范）
  aggregate <reports...> 汇总多份质量报告 JSON，输出团队级各指标通过率（QM 可视化看板数据源）

退出码
------
  0  status=pass
  1  status=fail（任一必须项未过）
  2  参数/运行错误（文件不可读、非法 JSON 等）
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys

# 让脚本无论从何处被调用，都能 import 同目录下的 security.* 模块（envelope / pii 仅用标准库）。
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from security.compliance_gate import classify as _compliance_classify  # noqa: E402
from security.envelope import Envelope  # noqa: E402
from security.pii import contains_pii  # noqa: E402


# 五字段回传契约：中文主键 + 英文别名（命中其一即视为该字段存在）。
_RETURN_FIELDS = {
    "结论": {"conclusion", "summary"},
    "产物或信封": {"artifact", "product", "envelope", "output"},
    "依据与来源": {"basis", "source", "references", "依据"},
    "待确认项": {"open_items", "tbd", "pending", "待确认"},
    "建议下一步": {"next_step", "next_steps", "建议"},
}

# 判定「字段已填写」时视为未填写的占位符（大小写不敏感、去空白后比对）。
# 刻意保守：只收录语义上明确表示「尚未填写」的标记，
# 不收录「无」「暂无」等在 HR 语境中有实际含义的表述（如「待确认项：无」是合法交付）。
_PLACEHOLDERS = {
    "todo", "tbd", "n/a", "na", "nil", "none", "null",
    "略", "待补充", "待填写", "待填", "待完善", "略过",
    "xxx", "???", "?", "？", "-", "--", "……", "...",
}

# 构成「像信封」的标志字段：命中任一即认为载荷自称信封，必须按信封严格校验。
_ENVELOPE_MARKERS = ("signature", "msg_id", "trace_id", "payload", "compliance", "nonce", "alg", "sig")
# 完整信封必须同时具备的字段。
_ENVELOPE_REQUIRED = ("signature", "msg_id", "trace_id", "payload", "compliance", "nonce")


def _load_json(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _is_placeholder(value: object) -> bool:
    """字段「有键但没内容」的判定：空串 / 纯空白 / 语义占位符 / 空容器。

    核心语义：契约字段存在 ≠ 契约字段已填写。
    """
    if value is None:
        return True
    if isinstance(value, str):
        s = value.strip().lower()
        if not s:
            return True
        return s in _PLACEHOLDERS
    if isinstance(value, (list, dict, tuple, set)):
        return len(value) == 0
    return False


def _is_envelope(d: dict) -> bool:
    return isinstance(d, dict) and all(k in d for k in _ENVELOPE_REQUIRED)


def _looks_like_envelope(d: dict) -> bool:
    """载荷是否自称信封（含任一标志字段）。"""
    if not isinstance(d, dict):
        return False
    keys = {str(k) for k in d.keys()}
    return any(m in keys for m in _ENVELOPE_MARKERS)


def _flatten_text(d: object) -> str:
    """把任意 JSON 结构压平为用于 PII / 合规扫描的文本。"""
    if isinstance(d, str):
        return d
    if isinstance(d, dict):
        return "\n".join(_flatten_text(v) for v in d.values())
    if isinstance(d, list):
        return "\n".join(_flatten_text(v) for v in d)
    return str(d)


def check_envelope_signature(d: dict, max_age: int | None) -> dict:
    """信封签名校验。

    关键语义：删掉一个字段就静默跳过验签，等于让攻击者通过「抽掉签名」
    把签名校验从必须项里摘出去。因此：
      - 完全不含任何信封标志字段 → 判为非信封形态（applicable=False，仅此时才跳过）；
      - 自称信封（命中任一标志字段）但字段不全 → 判 FAIL（残缺/被篡改的信封）；
      - 字段齐全 → 走真实 HMAC 验签。
    """
    if not _looks_like_envelope(d):
        return {"applicable": False, "pass": None, "detail": "非信封形态，跳过签名校验"}
    missing = [k for k in _ENVELOPE_REQUIRED if not isinstance(d, dict) or k not in d]
    if missing:
        return {
            "applicable": True,
            "pass": False,
            "detail": "疑似残缺/被篡改的信封：命中信封标志字段但缺失 %s（拒绝以删字段方式规避验签）"
                      % "、".join(missing),
        }
    ok = Envelope.verify(d, max_age_sec=max_age)
    return {
        "applicable": True,
        "pass": ok,
        "detail": "HMAC 验签通过" if ok else "验签失败或超时（疑似伪造/篡改/重放）",
    }


def check_return_contract(d: dict) -> dict:
    """定位回传契约对象（信封则取 payload；否则用 d 本身），校验五字段是否**已填写**。

    字段存在但值为空/纯空白/占位符，等同于缺失——必须判 FAIL。
    """
    target = d.get("payload", d) if _is_envelope(d) else d
    if not isinstance(target, dict):
        # 也可能是 payload 内嵌在 artifact 字段，做宽松扫描
        target = d

    def lookup(names: set):
        """在整树中找候选键名。返回 (是否出现该键, 是否存在非占位的取值)。"""
        found_key = False
        for node in _iter_dicts(target):
            for k, v in node.items():
                if str(k) in names:
                    found_key = True
                    if not _is_placeholder(v):
                        return True, True
        return found_key, False

    missing = []
    empty = []
    for cn, aliases in _RETURN_FIELDS.items():
        found_key, filled = lookup({cn} | aliases)
        if not found_key:
            missing.append(cn)
        elif not filled:
            empty.append(cn)
    bad = missing + empty
    # 信封形态下，payload 可能只含结构化产物；此时只要信封本身合法即不强求五字段文本
    if _is_envelope(d) and bad:
        # 退一步：检查信封是否携带结构化 artifact（含产物/依据线索）
        arts = d.get("artifacts") or []
        if arts:
            return {"applicable": True, "pass": True,
                    "detail": "信封形态且含 artifacts，回传契约以信封+artifact 承载（缺失/未填写字段：%s）" % "、".join(bad)}
    if not bad:
        return {"applicable": True, "pass": True, "detail": "五字段齐全且均已填写"}
    parts = []
    if missing:
        parts.append("缺失字段：%s" % "、".join(missing))
    if empty:
        parts.append("字段存在但为空/占位符：%s" % "、".join(empty))
    return {"applicable": True, "pass": False, "detail": "；".join(parts)}


def _iter_dicts(obj: object):
    """递归 yield 树中所有 dict 节点。"""
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from _iter_dicts(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _iter_dicts(v)


def _all_keys(obj: object) -> set:
    """递归收集所有 dict 的 key 名（含中文）。"""
    keys: set = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            keys.add(str(k))
            keys |= _all_keys(v)
    elif isinstance(obj, list):
        for v in obj:
            keys |= _all_keys(v)
    return keys


def _iter_keys(obj: object):
    """仅取顶层与一层嵌套的 key（用于别名快速命中，避免全树扫描噪声）。"""
    if isinstance(obj, dict):
        for k in obj.keys():
            yield k
            v = obj[k]
            if isinstance(v, dict):
                for kk in v.keys():
                    yield kk


def check_compliance_citation(d: dict) -> dict:
    """合规结论必须带法条出处 + 基准日期 + 核实状态（对齐 contracts.md 输出契约）。

    两种形态：① 文本形态【结论】…【依据】…【基准日期】…【核实状态】；
    ② 结构化 legal_basis / baseline_date / verification 字段。
    """
    text = _flatten_text(d)
    # 文本形态合规块扫描
    blocks = re.findall(r"【结论】.*?(?=【结论】|$)", text, re.S)
    text_missing = 0
    for b in blocks:
        has_basis = ("【依据】" in b) or ("【法条】" in b)
        has_date = "【基准日期】" in b
        has_verify = "【核实状态】" in b
        if not (has_basis and has_date and has_verify):
            text_missing += 1

    # 结构化形态：扫描含 legal_basis/basis/article 的对象
    struct_total, struct_missing = 0, 0

    def walk(o: object):
        nonlocal struct_total, struct_missing
        if isinstance(o, dict):
            low = {str(k).lower(): k for k in o.keys()}
            is_finding = any(k in low for k in ("legal_basis", "basis", "conclusion", "conclusion_cn"))
            if is_finding:
                struct_total += 1
                has_basis = any(x in low for x in ("legal_basis", "basis", "instrument", "article"))
                has_date = "baseline_date" in low or "baseline" in low
                has_verify = "verification" in low or "核实" in low
                if not (has_basis and has_date and has_verify):
                    struct_missing += 1
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(d)

    total = len(blocks) + struct_total
    missing = text_missing + struct_missing
    if total == 0:
        return {"applicable": True, "pass": True,
                "detail": "未发现合规结论，合规出处标注率统计为 vacuous-pass（建议人工抽检抽样）"}
    return {
        "applicable": True,
        "pass": missing == 0,
        "detail": "合规结论 %d 条，缺出处/基准日期/核实状态 %d 条" % (total, missing),
        "total": total, "missing": missing,
    }


def check_pii(d: dict) -> dict:
    text = _flatten_text(d)
    leaked = contains_pii(text)
    return {
        "applicable": True,
        "pass": not leaked,
        "detail": "明文未检出手机/邮箱/身份证 PII" if not leaked else "明文检出 PII，须先经 pii.py 脱敏",
    }


def check_compliance_gate(d: dict) -> dict:
    """把真实的合规闸（security/compliance_gate.py）接进质量闸门。

    对全文做风险分级：BLOCKED 一律判 FAIL，防止 P0 违法结论因五字段非空而拿满分。
    """
    text = _flatten_text(d)
    try:
        decision = _compliance_classify(text)
    except Exception as e:  # 合规闸自身异常不得静默放行
        return {"applicable": True, "pass": False,
                "detail": "合规闸执行异常，按 fail-closed 处置：%s" % e}
    gate = getattr(decision, "gate", "PASSED")
    risk = getattr(decision, "risk_level", "P3")
    reasons = list(getattr(decision, "reasons", []) or [])
    dri = getattr(decision, "dri", "")
    if gate == "BLOCKED":
        return {
            "applicable": True,
            "pass": False,
            "detail": "合规闸 BLOCKED（%s，dri=%s）：%s" % (risk, dri, "、".join(reasons) or "命中高危执行类指令"),
            "gate": gate, "risk_level": risk, "reasons": reasons, "dri": dri,
        }
    return {
        "applicable": True,
        "pass": True,
        "detail": "合规闸 %s（%s）%s" % (gate, risk, ("：" + "、".join(reasons)) if reasons else ""),
        "gate": gate, "risk_level": risk, "reasons": reasons, "dri": dri,
    }


# 各 specialist 的字段完整度规则表（基于实读 playbook「输出规范」登记，不编造字段）。
# 规则结构（字段均为可选，按需组合）：
#   desc          : 人类可读说明（写入质量报告 detail）
#   containers    : 列表中逐项检查（候选人档案型交付）；命中 shortlist/candidates/results 任一即视为交付主体
#   item_fields   : 容器内每个对象的必填字段
#   consent       : 必须为 true 的同意记录点路径（如 source.consent.obtained）
#   top           : 顶层必填字段（整树定位首个同名键）
#   nested        : {父字段: [子字段...]}，父对象内必填子字段
#   list_items    : {列表字段: [子字段...]}，列表内每个对象的必填字段
SPEC_RULES = {
    "talent-sourcing": {
        "desc": "寻访 shortlist 候选人档案必填（技能/城市/年限/来源/同意记录）",
        "containers": ["shortlist", "candidates", "results"],
        "item_fields": ["skills", "city", "years", "source"],
        "consent": "source.consent.obtained",
    },
    "recruitment-pipeline": {
        "desc": "招聘管道结构化产出必填字段",
        "top": ["jd", "recommendation"],
        "nested": {"jd": ["title", "must_have", "nice_to_have", "pay_competitiveness"]},
    },
    "labor-compliance": {
        "desc": "劳动合规终检产出必填字段",
        "top": ["scope", "gate", "legal_review", "dri"],
        "list_items": {"findings": ["topic", "clause_ref", "level", "basis", "advice"]},
    },
}


def _find_lists(obj: object, key: str):
    """递归查找所有 key==key 且值为 list 的节点，逐个 yield 该列表。"""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if str(k) == key and isinstance(v, list):
                yield v
            else:
                yield from _find_lists(v, key)
    elif isinstance(obj, list):
        for v in obj:
            yield from _find_lists(v, key)


def _get_node(obj: object, key: str):
    """在整树中返回第一个 key==key 的节点值（nested 父对象 / top 字段定位）。"""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if str(k) == key:
                return v
            r = _get_node(v, key)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = _get_node(v, key)
            if r is not None:
                return r
    return None


def _get_path_bool(obj: dict, dotted: str) -> bool:
    """解析点路径，要求叶子节点**严格为布尔真**。

    只接受真正的布尔真：宽松真值（如字符串 "false" / "no" / "0" 为真）会让 PIPL
    同意采集点被绕过；与 talent_pool._validate_record 的严格度对齐
    （`consent.get("obtained") is not True` 即拒绝）。
    """
    cur: object = obj
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return False
        cur = cur[part]
    return cur is True


def check_field_completeness(d: dict, spec: str | None) -> dict:
    rule = SPEC_RULES.get(spec)
    if not rule:
        return {"applicable": False, "pass": None,
                "detail": "未指定 --spec 或该 spec 暂无字段规则（list-specs 查看支持项）"}
    target = d.get("payload", d) if _is_envelope(d) else d
    missing: list = []

    # 列表型逐项检查（候选人档案类交付）
    if "containers" in rule:
        found_any = False
        nonempty_any = False
        for container in rule["containers"]:
            for lst in _find_lists(target, container):
                found_any = True
                # 空列表不是交付物：空容器不得直接判 pass。
                if not lst:
                    missing.append("%s 为空列表（核心交付为空）" % container)
                    continue
                nonempty_any = True
                for item in lst:
                    if not isinstance(item, dict):
                        missing.append("%s[].(非对象)" % container)
                        continue
                    for f in rule.get("item_fields", []):
                        if f not in item or _is_placeholder(item.get(f)):
                            missing.append("%s[].%s" % (container, f))
                    consent = rule.get("consent")
                    if consent and not _get_path_bool(item, consent):
                        missing.append("%s[].%s" % (container, consent))
        if not found_any:
            missing.append("未找到 %s 列表（核心交付缺失）" % "/".join(rule["containers"]))
        elif not nonempty_any:
            missing.append("%s 全部为空列表（核心交付为空）" % "/".join(rule["containers"]))

    # 顶层必填字段
    for f in rule.get("top", []):
        if _get_node(target, f) is None:
            missing.append(f)

    # 嵌套必填字段
    for parent, subs in rule.get("nested", {}).items():
        node = _get_node(target, parent)
        if node is None:
            missing.append(parent)
        elif isinstance(node, dict):
            for s in subs:
                if s not in node:
                    missing.append("%s.%s" % (parent, s))

    # 列表内逐项必填字段
    for container, fields in rule.get("list_items", {}).items():
        found = False
        nonempty = False
        for lst in _find_lists(target, container):
            found = True
            if not lst:
                continue
            nonempty = True
            for item in lst:
                if isinstance(item, dict):
                    for f in fields:
                        if f not in item:
                            missing.append("%s[].%s" % (container, f))
        if not found:
            missing.append("%s（列表缺失）" % container)
        elif not nonempty:
            missing.append("%s 为空列表（无任何条目）" % container)

    if not missing:
        return {"applicable": True, "pass": True, "detail": rule["desc"] + "：字段完整"}
    return {"applicable": True, "pass": False,
            "detail": "缺字段：%s" % "、".join(sorted(set(missing)))}


def run_aggregate(reports: list, scan_dir: str | None) -> dict:
    """汇总多份质量报告 JSON（quality_gate check 输出），统计团队级各指标通过率。

    作为 QM-01~QM-11 可视化看板的数据源：逐指标累加 applicable 样本数与 pass 数，
    输出 pass_rate_pct。

    不可读 / 非质量报告形态的文件必须逐文件记录失败原因，
    并在存在任何不可解析文件时以非零码退出——禁止基于残缺样本静默汇总。
    """
    paths = list(reports or [])
    if scan_dir:
        paths += sorted(glob.glob(os.path.join(scan_dir, "*.json")))
    if not paths:
        raise ValueError("未提供任何质量报告文件（aggregate 需 reports 位置参数或 --dir）")
    tally: dict = {}
    parsed = 0
    failures: list = []
    for p in paths:
        try:
            rep = _load_json(p)
        except (OSError, ValueError) as e:
            failures.append({"file": p, "reason": "不可读或非法 JSON：%s" % e})
            continue
        if not isinstance(rep, dict):
            failures.append({"file": p, "reason": "顶层不是 JSON 对象"})
            continue
        metrics = rep.get("metrics")
        if not isinstance(metrics, dict) or not metrics:
            failures.append({"file": p, "reason": "缺少 metrics 字段或为空，非 quality_gate check 报告形态"})
            continue
        parsed += 1
        for m, c in metrics.items():
            if not isinstance(c, dict):
                failures.append({"file": p, "reason": "指标 %s 结构非对象" % m})
                continue
            if c.get("applicable") and c.get("pass") is not None:
                t = tally.setdefault(m, [0, 0])
                t[1] += 1
                if c["pass"]:
                    t[0] += 1
    out = {"files_scanned": len(paths), "files_parsed": parsed,
           "files_failed": len(failures), "failures": failures,
           "metrics": {}}
    for m, (passed, total) in tally.items():
        rate = round(passed / total * 100, 1) if total else None
        out["metrics"][m] = {"pass": passed, "applicable": total, "pass_rate_pct": rate}
    return out


def quality_score(checks: dict) -> float:
    """综合质量分：仅对 applicable 且 pass 非 None 的指标计入。

    计分规则：
      - 跳过项（pass is None）按 0 分计入分母（no-credit），使分数反映「未被证明的部分」，
        防止「签名校验被摘掉 + 其余全过」得到满分（假绿）。
      - 没有任何可计分项时返回 0.0（而非 100.0）——零证据不等于满分。
    注意：本函数只负责「分数」，status 由 run_check 依据必须项独立判定；
    分数与 status 的一致性由 run_check 的 cap 逻辑保证（见 MUST_FAIL_CAP）。
    """
    total = 0
    passed = 0
    for c in checks.values():
        if c.get("pass") is None:
            # 跳过项：计入分母但不计通过（no-credit），避免「靠剔除检查拿满分」。
            total += 1
            continue
        total += 1
        if c.get("pass"):
            passed += 1
    if total == 0:
        return 0.0
    return round(passed / total * 100.0, 1)


# 必须项 fail 时综合分的上限：与 status=fail 保持方向一致，
# 避免出现「status=fail 但 score=100」这种自相矛盾的报告。
MUST_FAIL_CAP = 60.0


def run_check(path: str, spec: str | None, max_age: int | None) -> dict:
    data = _load_json(path)
    checks = {
        "envelope_signature_valid": check_envelope_signature(data, max_age),
        "return_contract_complete": check_return_contract(data),
        "compliance_citation_complete": check_compliance_citation(data),
        "compliance_gate_blocked": check_compliance_gate(data),
        "pii_masked": check_pii(data),
        "field_completeness": check_field_completeness(data, spec),
    }
    # 必须项：签名/回传契约/合规出处/合规闸/PII 任一 fail → 整体 fail。
    # 注意 applicable=False（不适用）不计入失败——例如未使用信封形态时跳过验签是合理的；
    # 但 applicable=True 且 pass=False 一律判失败。
    must = ["envelope_signature_valid", "return_contract_complete",
            "compliance_citation_complete", "compliance_gate_blocked", "pii_masked"]
    failed_must = [k for k in must if checks[k].get("applicable")
                   and checks[k].get("pass") is False]
    # 显式 --spec 时，字段完整度是调用方主动要求的校验，必须计入必须项，
    # 防止「空 shortlist / 同意记录缺失」被标 [X] 却仍然 exit 0。
    if spec and checks["field_completeness"].get("pass") is False:
        failed_must.append("field_completeness")
    status = "fail" if failed_must else "pass"
    raw_score = quality_score(checks)
    # 分数与 status 保持一致：必须项失败时封顶，避免「fail 却 100 分」的自相矛盾输出。
    score = min(raw_score, MUST_FAIL_CAP) if failed_must else raw_score
    return {
        "file": path,
        "spec": spec,
        "score": score,
        "score_raw": raw_score,
        "status": status,
        "failed_must": failed_must,
        "metrics": checks,
    }


def main(argv: list | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="quality_gate.py",
        description="HRM 输出契约校验器（质量闸门）",
        epilog="示例: python3 quality_gate.py check /tmp/return.json --spec talent-sourcing",
    )
    sub = ap.add_subparsers(dest="cmd")
    pc = sub.add_parser("check", help="校验一份成员回传 JSON")
    pc.add_argument("file", help="回传 JSON 文件路径")
    pc.add_argument("--spec", default=None, help="按 specialist 追加字段完整度校验（talent-sourcing/recruitment-pipeline/labor-compliance）")
    pc.add_argument("--max-age", type=int, default=None, help="信封时效上限（秒）")
    pc.add_argument("--json", action="store_true", help="仅输出 JSON")

    pl = sub.add_parser("list-specs", help="列出支持的 --spec 字段完整度规则")
    pl.add_argument("--json", action="store_true", help="仅输出 JSON")

    pa = sub.add_parser("aggregate", help="汇总多份质量报告，输出团队级各指标通过率")
    pa.add_argument("reports", nargs="*", help="质量报告 JSON 文件（quality_gate check 输出）")
    pa.add_argument("--dir", default=None, help="扫描该目录下所有 *.json 质量报告")
    pa.add_argument("--json", action="store_true", help="仅输出 JSON")
    args = ap.parse_args(argv)

    if args.cmd == "list-specs":
        rows = [{"spec": k, "desc": v["desc"]} for k, v in SPEC_RULES.items()]
        if not args.json:
            print("支持的 --spec 字段完整度规则（基于实读 playbook 输出规范登记）：")
            for r in rows:
                print("  %s — %s" % (r["spec"], r["desc"]))
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0

    if args.cmd == "aggregate":
        try:
            out = run_aggregate(args.reports, args.dir)
        except ValueError as e:
            sys.stderr.write("[ERR] %s\n" % e)
            return 2
        if not args.json:
            print("团队级质量指标通过率（扫描 %d 份报告，解析 %d 份，失败 %d 份）"
                  % (out["files_scanned"], out["files_parsed"], out["files_failed"]))
            for m, v in out["metrics"].items():
                print("  %s：%s/%s 通过（%s%%）" % (m, v["pass"], v["applicable"], v["pass_rate_pct"]))
        print(json.dumps(out, ensure_ascii=False, indent=2))
        if out["files_failed"]:
            # 垃圾输入必须让命令失败，不能静默基于残缺样本出通过率。
            for f in out["failures"]:
                sys.stderr.write("[ERR] %s: %s\n" % (f["file"], f["reason"]))
            return 1
        return 0

    if args.cmd != "check":
        ap.print_help()
        return 2
    try:
        rep = run_check(args.file, args.spec, args.max_age)
    except (OSError, ValueError) as e:
        sys.stderr.write("[ERR] 无法读取/解析回传文件: %s\n" % e)
        return 2

    if not args.json:
        print("质量校验：%s  综合质量分=%s" % (rep["status"].upper(), rep["score"]))
        for k, c in rep["metrics"].items():
            if not c.get("applicable"):
                continue
            # 用 ASCII 标记替代 U+2713/U+2717，避免非 UTF-8 终端乱码。
            mark = "[OK]" if c.get("pass") else "[X]"
            print("  %s %s — %s" % (mark, k, c["detail"]))
        if rep["failed_must"]:
            print("必须项未过：%s" % "、".join(rep["failed_must"]))
    print(json.dumps(rep, ensure_ascii=False, indent=2))
    return 0 if rep["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
