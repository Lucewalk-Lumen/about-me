#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OBHRM 质量闸门程序化执行器（gate_executors）。

对应 `quality_gates.json` 中 8 个可自动化的 gate。每个 gate 提供纯标准库实现的
确定性检查；`severity_p0_p1_p2` 复用 `obhrm_preflight.audit()` 做 P0/P1/P2 文本预检。

设计原则：
- 不替代人工评审：脚本只做"可机器判定"的部分，输出 findings 供主理人/执行 agent 复核。
- 包扫描模式（默认）：仅对**对外交付面**（README / CHANGELOG / agents / SKILL.md /
  plugin.json / settings.json）做静态检查；模板与 references 允许含占位符，不扫描。
- 交付物模式（`--text`）：对已生成文本跑 P0/P1/P2 预检与引用保真检查。

用法：
  python3 gate_executors.py --list
  python3 gate_executors.py --gate citation_fidelity [--root <pkg>] [--text <file>]
  python3 gate_executors.py --all [--root <pkg>]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

# 仅 severity 闸门复用既有预检；其余均为本模块自包含实现（零第三方依赖）。
try:
    from obhrm_preflight import audit as _preflight_audit  # type: ignore
except Exception:  # pragma: no cover - 独立运行兜底
    _preflight_audit = None


# --------------------------------------------------------------------------- #
# 结果结构
# --------------------------------------------------------------------------- #
def _result(gate_id, passed, severity, findings, mode, note=""):
    return {
        "gate": gate_id,
        "passed": bool(passed),
        "severity_if_fail": severity,        # blocker / required
        "mode": mode,
        "findings": findings,                # list[str]
        "note": note,
    }


# --------------------------------------------------------------------------- #
# 通用工具
# --------------------------------------------------------------------------- #
_MD_EXTS = (".md", ".markdown")


def _iter_md(root: str):
    """遍历包内所有 markdown 文档（含 SKILL.md / references / agents 等）。"""
    root = Path(root)
    if not root.exists():
        return
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in _MD_EXTS:
            rel = p.relative_to(root).as_posix()
            if rel.startswith("skills/scale-library/knowledge/scales/"):
                continue
            if rel.startswith("skills/theory-library/knowledge/theories/"):
                continue
            yield p


def _surface_docs(root: str):
    """对外交付面文档（允许含占位符的模板/references 不扫描）。"""
    root = Path(root)
    yield from [root / "README.md", root / "CHANGELOG.md",
               root / "LICENSE", root / "settings.json"]
    pj = root / ".codebuddy-plugin" / "plugin.json"
    if pj.exists():
        yield pj
    for p in (root / "agents").glob("*.md"):
        yield p
    for p in root.rglob("skills/*/SKILL.md"):
        yield p


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _grep_package(root: str, pattern: str, flags=re.IGNORECASE) -> list[str]:
    """返回命中行的 '相对路径:line — 内容' 列表（排除 peer-review 目录可选）。"""
    rx = re.compile(pattern, flags)
    hits = []
    for p in _iter_md(root):
        text = _read(p)
        for i, line in enumerate(text.splitlines(), 1):
            if rx.search(line):
                hits.append(f"{p.relative_to(root).as_posix()}:{i} — {line.strip()[:120]}")
    return hits


def _grep_paths(root: str, paths, pattern: str, flags=re.IGNORECASE) -> list[str]:
    rx = re.compile(pattern, flags)
    hits = []
    for p in paths:
        if not Path(p).exists():
            continue
        for i, line in enumerate(_read(Path(p)).splitlines(), 1):
            if rx.search(line):
                hits.append(f"{Path(p).relative_to(root).as_posix()}:{i} — {line.strip()[:120]}")
    return hits


# --------------------------------------------------------------------------- #
# 8 个可自动化 gate 检查
# --------------------------------------------------------------------------- #
def check_citation_fidelity(root: str, text: str | None = None) -> dict:
    """引用保真：包扫描仅查空引用槽；交付物模式查占位伪装统计量。"""
    if text is not None:
        mode = "text"
        # 仅当统计量后紧跟明确占位符才算伪装；真实数值（如 RMSEA=0.10）不误报
        placeholder = re.compile(
            r"(均值|标准差|相关系数|回归系数|p\s*值|置信区间|Cohen'?s?\s*d|η²|VIF|"
            r"ΔR²|Bootstrap\s*CI|α|CR|AVE|CFI|TLI|RMSEA|SRMR|I²|τ²)\s*[:：=]?\s*"
            r"(待填|未填|暂无|N/A|无数据|未提供|×)",
            re.IGNORECASE)
        ctx_placeholder = re.compile(r"未计算|需在实际统计环境中运行|未运行|尚未运行",
                                     re.IGNORECASE)
        findings = []
        for m in placeholder.finditer(text):
            s, e = max(0, m.start() - 30), m.end() + 30
            if not ctx_placeholder.search(text[max(0, s - 80):s]):
                findings.append(f"疑似占位伪装统计量：…{text[s:e].strip()}…")
        if re.search(r"(Cohen'?s?\s*d|η²|VIF|ΔR²|Bootstrap\s*CI)", text) and \
           not ctx_placeholder.search(text):
            findings.append("正文含统计量但未附'未计算'声明，请确认数值来自真实运行输出"
                            "（四铁律·不编引用）。")
        return _result("citation_fidelity", len(findings) == 0, "blocker", findings, mode)

    mode = "package-scan"
    # 包内仅查空引用槽 / 显式待补引用。
    # 注意：仅匹配真正的空括号引用标记（〔〕），**不**匹配 markdown 任务清单
    # 的 `[ ]` 勾选框（如 SKILL.md 中的「图表嵌入/论证连接」清单），避免误报。
    findings = _grep_paths(root, _surface_docs(root), r"〔\s*〕|引用待补|待补引用|（待补引用）")
    return _result("citation_fidelity", len(findings) == 0, "blocker", findings, mode)


def check_methodology_single_source(root: str, text: str | None = None) -> dict:
    """方法论唯一真源：包内不得指向包外第二处方法论标准 / 回退分支。"""
    mode = "text" if text is not None else "package-scan"
    if text is not None:
        hits = []
        if re.search(r"obhrm-methodology\.md|外部.*方法论真源|包外.*方法论|"
                     r"第二处.*方法论", text, re.IGNORECASE):
            hits.append("文本引用了包外方法论真源")
    else:
        # 仅匹配明确的『包外/外部方法论真源』，不匹配内部分享文件名
        hits = _grep_package(
            root, r"obhrm-methodology\.md|外部.*方法论真源|包外.*方法论标准|"
                   r"第二处.*方法论真源|方法论.*回退分支")
    return _result("methodology_single_source", len(hits) == 0, "blocker", hits, mode)


def check_review_single_source(root: str, text: str | None = None) -> dict:
    """审稿唯一真源：除 peer-review 外不得有第二处外部审稿标准。"""
    mode = "text" if text is not None else "package-scan"
    # 仅匹配指向「外部/第二处审稿标准」的正向引用；排除包自身的自我声明（见下）。
    # 检测词用「独立审稿.*(标准|模块)」而非「独立审稿 技能包」式字面，避免与外部
    # 来源标识串冲突，同时保持对外部审稿包的检出能力。
    rx = re.compile(r"第二处审稿|第二份审稿\s*SOP|外部.*审稿标准|"
                    r"第二套审稿|另一套审稿|独立审稿.*(标准|模块)", re.IGNORECASE)
    if text is not None:
        # 用 finditer 取完整匹配（rx 含捕获组，findall 只会返回捕获组而非整段匹配）
        hits = [f"文本疑似引用外部审稿标准：{m.group(0)}" for m in rx.finditer(text)]
    else:
        hits = []
        # 排除包自身的自我声明行：如「零外部审稿包 / 评审标准唯一出处 / 只此一处」
        # 这些是否定式断言（声称自己是唯一真源），并非引用了某个外部第二处审稿标准。
        _self_assert = re.compile(
            r"零\s*(外部|第二)|无\s*(外部|第二)|不设\s*(第二|外部)|不另设|不再设|"
            r"唯一真源|唯一出处|只此一处|唯一",
            re.IGNORECASE)
        for p in _iter_md(root):
            rel = p.relative_to(root).as_posix()
            if rel.startswith("skills/peer-review/"):
                continue
            for i, line in enumerate(_read(p).splitlines(), 1):
                if not rx.search(line):
                    continue
                if _self_assert.search(line):
                    continue
                hits.append(f"{rel}:{i} — {line.strip()[:120]}")
    return _result("review_single_source", len(hits) == 0, "blocker", hits, mode)


def check_no_role_persona(root: str, text: str | None = None) -> dict:
    """无角色人设：agent 不得用研究者人设 / 帽子驱动交互（用户扮演不计入）。"""
    mode = "text" if text is not None else "package-scan"
    # agent 自述人设式表述；排除『让用户扮演』（用户侧角色扮演，合规）
    rx = re.compile(r"五顶帽子|换帽子不换人格|此刻我是|此刻角色|帽子.*人格|"
                    r"角色扮演.*(辅助|服务|体系)|我是.*(专家|顾问).*（负责|，负责）",
                    re.IGNORECASE)
    if text is not None:
        hits = [f"文本含人设表述：{m}" for m in rx.findall(text)]
    else:
        hits = []
        for p in _iter_md(root):
            for i, line in enumerate(_read(p).splitlines(), 1):
                if "让用户扮演" in line or "请用户扮演" in line:
                    continue
                if rx.search(line):
                    hits.append(f"{p.relative_to(root).as_posix()}:{i} — {line.strip()[:120]}")
    return _result("no_role_persona", len(hits) == 0, "required", hits, mode)


def check_severity_p0_p1_p2(root: str, text: str | None = None) -> dict:
    """全局 P0/P1/P2 严重度分级：P0（占位符/编造引用/缺参考文献）须 0。"""
    mode = "text" if text is not None else "package-scan(surface)"
    findings = []
    p0 = p1 = p2 = 0
    if text is not None:
        if _preflight_audit is None:
            return _result("severity_p0_p1_p2", False, "blocker",
                           ["obhrm_preflight 不可用，跳过自动预检（转人工）"], mode)
        r = _preflight_audit(text)
        p0, p1, p2 = (r["summary"].get(k, 0) for k in ("P0", "P1", "P2"))
        findings = [f"[{it['severity']}] {it['code']}: {it['message']}" for it in r["issues"]]
    else:
        if _preflight_audit is None:
            return _result("severity_p0_p1_p2", False, "blocker",
                           ["obhrm_preflight 不可用，跳过自动预检（转人工）"], mode)
        for p in _surface_docs(root):
            if not Path(p).exists():
                continue
            r = _preflight_audit(_read(Path(p)))
            p0 += r["summary"].get("P0", 0)
            p1 += r["summary"].get("P1", 0)
            p2 += r["summary"].get("P2", 0)
            for it in r["issues"]:
                if it["severity"] == "P0":
                    findings.append(f"{Path(p).relative_to(root).as_posix()}: {it['message']}")
    return _result("severity_p0_p1_p2", p0 == 0, "blocker", findings, mode,
                   f"P0={p0} P1={p1} P2={p2}")


def check_review_stage_gates(root: str, text: str | None = None) -> dict:
    """L 路径综述门控（G1+~G5）：stage_gates.json 须含 5 道门且各有 checks。"""
    mode = "package-scan"
    sg = Path(root) / "skills" / "literature-review" / "knowledge" / "stage_gates.json"
    findings = []
    if not sg.exists():
        return _result("review_stage_gates", False, "blocker",
                       [f"缺失门控真源：{sg}"], mode)
    try:
        data = json.loads(_read(sg))
    except Exception as e:
        return _result("review_stage_gates", False, "blocker",
                       [f"stage_gates.json 解析失败：{e}"], mode)
    gates = (data.get("review_gates") or {}).get("gates", [])
    if not isinstance(gates, list):
        return _result("review_stage_gates", False, "blocker",
                       ["review_gates.gates 结构异常（非列表）"], mode)
    ids = [g.get("id", "") for g in gates if isinstance(g, dict)]
    required = ["G1", "G2", "G3", "G4", "G5"]
    missing = [g for g in required if not any(g in i for i in ids)]
    for g in gates:
        if not isinstance(g, dict):
            continue
        cid = g.get("id", "?")
        if any(cid.startswith(r) for r in required) and not g.get("checks"):
            findings.append(f"{cid} 缺少 checks 判据")
    if missing:
        findings.append(f"缺失门控：{', '.join(missing)}")
    for dep in ("closed_loop_check.py", "format_citation_report.py"):
        if not (Path(root) / "skills" / "obhrm-methodology" / "scripts" / dep).exists():
            findings.append(f"G5 依赖脚本缺失：{dep}")
    passed = not missing and not findings
    return _result("review_stage_gates", passed, "blocker", findings, mode)


def check_coherence_gates(root: str, text: str | None = None) -> dict:
    """连贯性闸门（轻量 lint）：图/表题注编号与正文「如图N/如表N」交叉引用一致。"""
    mode = "text" if text is not None else "package-scan"
    targets = []
    if text is not None:
        targets = [("text", text)]
    else:
        for p in _surface_docs(root):
            if Path(p).exists():
                targets.append((Path(p).relative_to(root).as_posix(), _read(Path(p))))
    findings = []
    cap_rx = re.compile(r"(?:图|表|Figure|Fig\.?|Table)\s*([A-Za-z]?\d+)\s*[:：]")   # 仅题注标签（数字后接冒号）
    ref_rx = re.compile(r"(?:如图|见图|如表|见表|see\s+(?:Figure|Fig\.?|Table)|(?:Figure|Fig\.?|Table))\s*([A-Za-z]?\d+)", re.IGNORECASE)
    for name, blob in targets:
        if not blob:
            continue
        caps = set(cap_rx.findall(blob))
        ref_ids = set()
        for m in ref_rx.finditer(blob):
            # 若匹配后紧跟 ":" 或 "：" 则跳过（那是题注本身，非正文引用）
            if blob[m.end():m.end() + 1] in (":", "："):
                continue
            ref_ids.add(m.group(1))
        if caps:
            orphan = sorted(caps - ref_ids)
            if orphan:
                findings.append(f"{name}: 题注编号 {', '.join(orphan)} 未在正文被引用"
                                f"（可能孤岛图表，需人工确认）")
    return _result("coherence_gates", len(findings) == 0, "blocker", findings, mode,
                   "轻量 lint：仅比对编号存在性，不验证语义对齐")


def check_trust_boundary(root: str, text: str | None = None) -> dict:
    """Trust Boundary 硬约束：审计日志模块（落点）须存在，且无人声明绕过边界。

    判据：
    - 阻断项①：obhrm_research_base/core/audit_log.py 模块缺失（边界落点不存在）。
    - 阻断项②：包内文档出现「绕过/覆盖/忽略 Trust Boundary」的声明。
    - 软提示（不阻断）：包内文档未引用审计日志——仅提示补充 C 路径引用说明，
      不因此误报阻断（避免把"未显式引用"当成边界被破坏）。
    """
    mode = "package-scan"
    audit_log = (Path(root) / "skills" / "obhrm-methodology" /
                 "obhrm_research_base" / "core" / "audit_log.py")
    findings = []
    if not audit_log.exists():
        findings.append(f"审计日志模块缺失：{audit_log}（Trust Boundary 落点不存在）")
    c_ref = _grep_package(root, r"audit_log|audit log|审计日志")
    if not c_ref:
        findings.append("提示：包内文档未发现对审计日志的引用（非阻断，建议补充 C 路径引用说明）")
    bypass = _grep_package(root, r"绕过.*(Trust Boundary|信任边界)|Trust Boundary.*(绕过|覆盖|忽略)")
    findings.extend(bypass)
    # 仅模块缺失 / 绕过声明 为阻断项；软提示不影响放行
    blocking = [f for f in findings if not f.startswith("提示：")]
    return _result("trust_boundary", len(blocking) == 0, "blocker", findings, mode)


# gate_id -> 检查函数
GATES = {
    "citation_fidelity": check_citation_fidelity,
    "methodology_single_source": check_methodology_single_source,
    "review_single_source": check_review_single_source,
    "no_role_persona": check_no_role_persona,
    "severity_p0_p1_p2": check_severity_p0_p1_p2,
    "review_stage_gates": check_review_stage_gates,
    "coherence_gates": check_coherence_gates,
    "trust_boundary": check_trust_boundary,
}


# --------------------------------------------------------------------------- #
# 调度 / CLI
# --------------------------------------------------------------------------- #
def run_gate(gate_id: str, root: str, text: str | None = None) -> dict:
    fn = GATES.get(gate_id)
    if fn is None:
        return _result(gate_id, False, "required",
                       [f"未知 gate：{gate_id}（可选：{', '.join(GATES)}）"], "error")
    return fn(root, text)


def _default_root() -> str:
    return os.path.normpath(os.path.join(HERE, "..", "..", ".."))


def main() -> int:
    ap = argparse.ArgumentParser(description="OBHRM 质量闸门程序化执行器")
    ap.add_argument("--list", action="store_true", help="列出可执行的 gate")
    ap.add_argument("--gate", help="指定 gate id 运行")
    ap.add_argument("--all", action="store_true", help="运行全部 8 个 gate")
    ap.add_argument("--root", default=None, help="包根目录（默认脚本上三级）")
    ap.add_argument("--text", help="对单段交付文本运行（覆盖包扫描）")
    args = ap.parse_args()

    if args.list:
        for gid in GATES:
            print(f"  {gid}")
        return 0

    root = os.path.abspath(args.root) if args.root else _default_root()
    text = _read(Path(args.text)) if args.text else None

    if args.gate:
        res = run_gate(args.gate, root, text)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0 if res["passed"] else 1

    if args.all:
        any_fail = False
        for gid in GATES:
            res = run_gate(gid, root, text)
            flag = "PASS" if res["passed"] else "FAIL"
            print(f"[{flag}] {gid} ({res['mode']}) — {res['note']}")
            for f in res["findings"]:
                print(f"      - {f}")
            if not res["passed"]:
                any_fail = True
        return 1 if any_fail else 0

    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
