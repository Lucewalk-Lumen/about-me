#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""hrm-solution-team 运行前自检（发布门禁）。

覆盖：必需文件、团队清单结构、单一版本真源、成员四方互校、市场字段合规、
文件名全 ASCII、密钥硬编码、以及链接/网络等启发式检查。

退出码：0 = 无 FAIL（可有 WARN）；1 = 存在 FAIL。
仅依赖 Python 标准库；从包根运行：  python3 scripts/verify.py
"""
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FAILS, WARNS, INFOS = [], [], []


def fail(m):
    FAILS.append(m)


def warn(m):
    WARNS.append(m)


def info(m):
    INFOS.append(m)


def rd(p: Path) -> str:
    return p.read_text(encoding="utf-8-sig", errors="replace")


# 官方 15 类 categoryId（来源 open.workbuddy.cn/docs/expert “行业分类”）
CATEGORIES = {
    "01-ProductDesign", "02-Engineering", "03-GameSpatial", "04-DataAI",
    "05-MarketingGrowth", "06-ContentCreative", "07-SalesCommerce",
    "08-FinanceInvestment", "09-OperationsHR", "10-ProjectQuality",
    "11-SecurityCompliance", "12-IndustryConsultant", "13-TencentZone",
    "14-WorldWise", "15-Education",
}
LANG_KEYS = ("en", "zh")


def main() -> int:
    # 1. 必需文件
    for rel in (".codebuddy-plugin/plugin.json", "settings.json", "routing.yaml",
                "agents", "avatars", "skills", "README.md"):
        (ROOT / rel).exists() or fail(f"缺少必需项: {rel}")

    try:
        pj = json.loads(rd(ROOT / ".codebuddy-plugin/plugin.json"))
    except Exception as e:  # noqa: BLE001
        fail(f"plugin.json 解析失败: {e}")
        return report()

    name = pj.get("name")
    ver = pj.get("version")

    # 2. 团队结构
    if pj.get("expertType") != "team":
        fail("expertType 必须为 'team'")
    if pj.get("plugin") != name:
        fail("plugin 字段必须等于 name")
    lead = pj.get("agentName")
    ti = pj.get("teamInfo", {}) or {}
    if ti.get("leadAgent") != lead:
        fail("teamInfo.leadAgent 必须等于 agentName")
    try:
        st = json.loads(rd(ROOT / "settings.json"))
    except Exception as e:  # noqa: BLE001
        st = {}
        fail(f"settings.json 解析失败: {e}")
    if st.get("agent") != lead:
        fail("settings.json.agent 必须等于 lead agentName")
    if lead != f"{name}-lead":
        warn(f"主理人文件名主干 '{lead}' 非约定 '{name}-lead'（团队前缀要求请自查）")
    lead_md = ROOT / "agents" / f"{lead}.md"
    lead_md.exists() or fail(f"主理人 agent 文件缺失: agents/{lead}.md")

    # 3. 市场显示字段
    dn, prof = pj.get("displayName", {}), pj.get("profession", {})
    if prof != dn:
        fail("profession 必须与 displayName 完全一致（团队标准）")
    if len(pj.get("tags", [])) != 3:
        fail("tags 必须固定 3 个")
    if len(pj.get("quickPrompts", [])) != 3:
        fail("quickPrompts 必须固定 3 个")
    if pj.get("defaultInitPrompt") != (pj.get("quickPrompts", [None]) or [None])[0]:
        fail("defaultInitPrompt 必须等于 quickPrompts[0]")
    dd = (pj.get("displayDescription", {}) or {}).get("zh", "")
    cjk_n = len(re.findall(r"[一-鿿]", dd))
    if not (40 <= cjk_n <= 50):
        fail(f"displayDescription 中文字数 {cjk_n} 不在 40-50")
    if not (40 <= len(dd) <= 50):
        warn(f"displayDescription 整串长度 {len(dd)}（含标点）贴近/超出 40-50，建议留余量")
    cid = pj.get("categoryId")
    if cid not in CATEGORIES:
        fail(f"categoryId '{cid}' 不在官方 15 类枚举内")

    # 4. 头像存在
    av = pj.get("avatar")
    if not (av and (ROOT / av).exists()):
        fail(f"团队头像缺失: {av}")

    # 5. 成员四方互校：members / agents / avatars / teamInfo
    members = pj.get("members", [])
    ids = [m.get("id") for m in members]
    leads = [m.get("id") for m in members if m.get("role") == "lead"]
    if len(leads) != 1:
        fail(f"必须恰有一个 role==lead，实际 {leads}")
    if set(ti.get("memberAgents", [])) != set(ids) - {lead}:
        fail("teamInfo.memberAgents 与 members（去 lead）不一致")
    for m in members:
        mid, mav = m.get("id"), m.get("avatar")
        if not (mav and (ROOT / mav).exists()):
            fail(f"成员 {mid} 头像缺失: {mav}")
        if mid != lead and not (ROOT / "agents" / f"{mid}.md").exists():
            fail(f"成员 {mid} 缺 agents/{mid}.md")
        if not (m.get("name") and all(k in (m.get("name") or {}) for k in LANG_KEYS)):
            warn(f"成员 {mid} name 缺 en/zh 双键")

    # 6. agents[] / skills[] 声明路径存在
    for a in pj.get("agents", []):
        (ROOT / a.replace("./", "")).exists() or fail(f"agents[] 路径缺失: {a}")
    for s in pj.get("skills", []):
        (ROOT / s.replace("./", "")).exists() or fail(f"skills[] 路径缺失: {s}")

    # 7. 单一版本真源
    for sk in sorted((ROOT / "skills").glob("*/SKILL.md")):
        m = re.search(r"^version:\s*(\S+)", rd(sk), re.M)
        rel = sk.relative_to(ROOT)
        if not m:
            fail(f"{rel} 缺少 version")
        elif m.group(1) != ver:
            fail(f"{rel} 版本 {m.group(1)} != 包版本 {ver}")
    for kj in (ROOT / "skills").glob("*/knowledge/*.json"):
        try:
            d = json.loads(rd(kj))
        except Exception:  # noqa: BLE001
            continue
        v = d.get("version")
        if v and v != ver:
            warn(f"{kj.relative_to(ROOT)} knowledge 版本 {v} != 包版本 {ver}（若为数据版本可忽略）")

    # 8. 文件名全 ASCII（防解压乱码/断链）
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in ("__pycache__", ".git")]
        for fn in filenames:
            if any(ord(c) > 127 for c in fn):
                fail(f"非 ASCII 文件名（跨平台解压风险）: {fn} @ {dirpath}")

    # 9. 密钥硬编码（启发式，FAIL）
    secret_re = re.compile(
        r"""(?ix)(api[_-]?key|secret|access[_-]?token|password)\s*[:=]\s*["'][A-Za-z0-9_\-]{16,}["']""")
    for p in ROOT.rglob("*"):
        if p.is_file() and p.suffix in (".py", ".js", ".sh", ".json", ".yaml", ".yml"):
            if secret_re.search(rd(p)):
                fail(f"疑似硬编码密钥: {p.relative_to(ROOT)}")

    # 10. 启发式（WARN）：脚本网络外联、markdown 断链、routing agent 取值
    net_re = re.compile(r"(?m)^\s*(?:import|from)\s+(requests|urllib|socket|http\.client|httpx|aiohttp|smtplib|ftplib)\b")
    for p in (ROOT / "skills").rglob("*.py"):
        if net_re.search(rd(p)):
            warn(f"脚本含网络库 import（若刻意离线请复核）: {p.relative_to(ROOT)}")

    valid_agents = set(ids) | {"lead", name + "-lead"}
    ry = ROOT / "routing.yaml"
    if ry.exists():
        for tok in re.findall(r"(?m)^\s*agent:\s*([A-Za-z0-9_-]+)\s*$", rd(ry)):
            if tok not in valid_agents:
                warn(f"routing.yaml agent 取值 '{tok}' 不在成员集合内")

    link = re.compile(r"\[[^\]]*\]\((?!https?:|mailto:|#)([^)]+)\)")
    for md in list((ROOT / "skills").rglob("*.md")) + list((ROOT / "agents").rglob("*.md")):
        for tgt in link.findall(rd(md)):
            head = tgt.split("#")[0].strip()
            # 去掉 markdown 链接的可选标题：path "title" → path（空格前第一段，去引号/尖括号）
            parts = head.split()
            t = parts[0].strip('"\'<>') if parts else ""
            if not t or t.startswith(("[", "<")):
                continue
            if not ((md.parent / t).exists() or (ROOT / t).exists()):
                warn(f"可能断链: {md.relative_to(ROOT)} -> {t}")

    return report()


def report() -> int:
    for m in FAILS:
        print(f"[FAIL] {m}")
    for m in WARNS:
        print(f"[WARN] {m}")
    for m in INFOS:
        print(f"[INFO] {m}")
    print("=" * 50)
    print(f"自检结果：{len(FAILS)} FAIL / {len(WARNS)} WARN")
    if FAILS:
        print("校验未通过：存在 FAIL，不得进入发布/加载流程。")
        return 1
    print("校验通过：0 FAIL。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
