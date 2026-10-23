#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_skeleton.py —— EndNote 综述骨架生成器

消费 EndNote 分析包的 JSON 产物（topics / evolution / author_topic / network / age / dup），
套用 OBHRM 文献综述框架，输出一份结构化的 Markdown 综述提纲。

纯标准库实现（json / argparse / pathlib），不依赖 R 或任何第三方包。

重要约束：
    - 本工具**不负责**任何引文 / 参考文献格式化（无 GB/T 7714、APA、参考文献列表、引用管理）。
    - 引用与参考文献的落地交由专用引文工具处理。本骨架仅组织“写什么、按什么逻辑写”。

CLI:
    python3 build_skeleton.py \
        --topics T --evolution E --author-topic A --network N --age G --dup D \
        --out SKELETON.md [--refs DIR] [--title STR] [--library STR]

任一输入 JSON 缺失或不合法时，脚本会健壮跳过该维度并在产物中标注“未提供”，
不会整体失败。
"""

import argparse
import datetime
import json
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# 通用工具
# ---------------------------------------------------------------------------


def load_json(path):
    """读取 JSON；缺失 / 损坏时返回 None（静默降级，不抛异常）。"""
    if not path:
        return None
    p = Path(path)
    if not p.is_file():
        return None
    try:
        with p.open(encoding="utf-8") as fh:
            return json.load(fh)
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return None


def jget(obj, *keys, default=None):
    """多层安全取值。"""
    cur = obj
    for k in keys:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur


def fmt_list(items, limit=None, sep="、"):
    if not items:
        return "（无）"
    items = list(items)
    if limit and len(items) > limit:
        return sep.join(str(x) for x in items[:limit]) + f" 等{len(items)}项"
    return sep.join(str(x) for x in items)


# ---------------------------------------------------------------------------
# 框架加载：从 scripts/../references 读取 OBHRM 抽取框架
# ---------------------------------------------------------------------------


def load_frameworks(refs_dir):
    """返回若干框架对象：JSON 解析为 dict，.md 读取为文本；缺失则为 None。"""
    rd = Path(refs_dir)
    names = {
        "gap_novelty": "gap_novelty.json",
        "argumentation": "argumentation_framework.json",
        "quality": "quality_scoring.json",
        "red_flags": "red_flags.json",
        "templates": "templates.json",
        "amj": "amj_elements.json",
        "paradigms": "paradigms.json",
        "stage_gates": "stage_gates.json",
        "brainstorming": "brainstorming_protocol.json",
        "closed_loop": "closed_loop.json",
        "evidence_claim": "evidence_claim_map.json",
        "reading_codes": "reading_codes.json",
        "journal_standards": "journal_standards.json",
        "bilingual": "bilingual_terms.json",
        "peer_review": "peer_review_framework.md",
        "topic_scoping": "topic_scoping_prompt.md",
        "writing_style": "writing_style_notes.md",
    }
    out = {}
    for key, fname in names.items():
        p = rd / fname
        if not p.is_file():
            out[key] = None
            continue
        if fname.endswith(".md"):
            try:
                out[key] = p.read_text(encoding="utf-8")
            except OSError:
                out[key] = None
        else:
            out[key] = load_json(p)
    return out


# ---------------------------------------------------------------------------
# 各段落渲染
# ---------------------------------------------------------------------------


def render_intro_map(topics, age, network, fw):
    """引言地图：用 AMJ 九要素 + 数据画像，给出引言应覆盖的清单与写作提示。"""
    lines = ["## 一、引言地图（Introduction Map）", ""]
    lines.append("> 目标：在动笔前明确“为什么要写这篇综述、写给谁、卡在哪里”。"
                 "下列清单逐条给出撰写提示，可转化为引言/背景节的子标题。")
    lines.append("")

    # 数据画像（驱动自真实产物）
    lines.append("### 1.1 文献库画像（驱动自分析产物）")
    if topics:
        cov = jget(topics, "coverage", default={}) or {}
        diag = jget(topics, "diagnostics", default={}) or {}
        n_clusters = jget(diag, "nonempty_clusters") or len(jget(topics, "clusters", default=[]) or [])
        lines.append(f"- 文献总量：{cov.get('total', '?')} 篇；主题聚类数：{n_clusters} 个")
        if cov.get("zh_pct") is not None:
            lines.append(f"- 中英分布：中文 {cov.get('zh_pct')}%（{cov.get('zh_docs')} 篇），"
                         f"英文主导占比见各主题")
        if cov.get("year_min") and cov.get("year_max"):
            lines.append(f"- 年份跨度：{cov.get('year_min')}–{cov.get('year_max')}")
        if cov.get("keyword_coverage_pct") is not None:
            lines.append(f"- 关键词覆盖率：{cov.get('keyword_coverage_pct')}%（共现网络仅基于该部分）")
    if age:
        ys = jget(age, "year_stats", default={}) or {}
        rec = jget(age, "recency", default={}) or {}
        st = jget(age, "staleness", default={}) or {}
        if ys.get("median_year"):
            lines.append(f"- 时间中位数：{ys.get('median_year')} 年；均值 {ys.get('mean_year')} 年")
        if rec.get("recent_pct") is not None:
            lines.append(f"- 近窗口（{fmt_list(rec.get('recent_window_years', []))}）占比 {rec.get('recent_pct')}%，"
                         f"反映前沿热度")
        if st.get("old_pct") is not None:
            lines.append(f"- 陈旧文献（早于 {st.get('old_cutoff')}）占比 {st.get('old_pct')}%，"
                         f"提示需补近五年推进")
    lines.append("")

    # AMJ 九要素
    lines.append("### 1.2 必覆盖要素（AMJ 写作九要素 · 驱动自 amj_elements.json）")
    items = jget(fw.get("amj") or {}, "items", default=[]) or []
    if items:
        for it in items:
            q = it.get("core_question", "")
            lines.append(f"- **{it.get('name_zh', '?')}**：{q}")
    else:
        lines.append("- （未加载 amj_elements.json，九要素清单不可用；请检查 references/ 目录）")
    lines.append("")
    lines.append("> 提示：引言末段应落到“研究缺口”（见第三节），形成 动机→定位→问题→框架→边界 的闭环。")
    lines.append("")
    return lines


def _cluster_trend(evo_clusters, cluster_id):
    """根据 evolution 的 counts 推断趋势：上升/平稳/下降 + 峰值年。"""
    if not evo_clusters:
        return None
    match = next((c for c in evo_clusters if c.get("cluster_id") == cluster_id), None)
    if not match:
        return None
    counts = match.get("counts", {}) or {}
    if not counts:
        return None
    try:
        series = sorted(((int(y), n) for y, n in counts.items()))
    except (ValueError, TypeError):
        return None
    years = [y for y, _ in series]
    last5 = [n for y, n in series if y >= years[-1] - 4]
    prev5 = [n for y, n in series if y < years[-1] - 4][-5:]
    s_recent, s_prev = sum(last5), sum(prev5)
    if s_prev == 0:
        trend = "新兴/上升" if s_recent > 0 else "平稳"
    elif s_recent > s_prev * 1.1:
        trend = "上升"
    elif s_recent < s_prev * 0.9:
        trend = "下降"
    else:
        trend = "平稳"
    peak_year = max(series, key=lambda x: x[1])[0]
    return {"trend": trend, "peak_year": peak_year, "recent_sum": s_recent, "prev_sum": s_prev}


def _cluster_authors(at_topics, cluster_id, global_core):
    """取某主题的核心作者（优先该主题内，否则回退全局核心）。"""
    if at_topics:
        m = next((t for t in at_topics if t.get("cluster_id") == cluster_id), None)
        if m:
            authors = m.get("top_authors", []) or []
            return authors[:5], m.get("n_authors_in_topic")
    return None, None


def render_thematic(topics, evolution, author_topic, network):
    """按主题的综合方案：每个 cluster 映射为一个综述主题。"""
    lines = ["## 二、按主题的综合方案（Thematic Synthesis Plan）", ""]
    lines.append("> 以下每个分析聚类映射为一个综述子主题。请围绕其关键词、核心作者与年份趋势组织"
                 "“共同点—分歧—演进”的批判性综合，而非文献罗列。")

    clusters = jget(topics, "clusters", default=[]) or []
    evo_clusters = jget(evolution, "clusters", default=[]) or []
    at_topics = jget(author_topic, "top_per_topic", default=[]) or []
    global_core = jget(author_topic, "global_core_authors", default=[]) or []

    if not clusters:
        lines.append("")
        lines.append("- （未提供 topics.json，无法生成主题级综合方案。请先运行 EndNote 主题聚类。）")
        lines.append("")
        return lines

    # 按规模降序，优先组织大主题
    ordered = sorted(clusters, key=lambda c: c.get("size", 0) or 0, reverse=True)
    for idx, c in enumerate(ordered, 1):
        cid = c.get("cluster_id", "?")
        size = c.get("size", "?")
        pct = c.get("pct", "?")
        terms = c.get("top_terms", []) or []
        lang_dom = c.get("lang_dominant")
        lang_zh = c.get("lang_zh", 0)
        lang_en = c.get("lang_en", 0)
        yr = c.get("year_range", []) or []

        lines.append(f"### 主题 {idx}（cluster_id={cid} · 规模 {size} 篇 / {pct}%）")
        lang_txt = f"主导语言：{lang_dom}" if lang_dom else f"中 {lang_zh} / 英 {lang_en}"
        lines.append(f"- **关键词（top_terms）**：{fmt_list(terms, limit=15)}")
        lines.append(f"- **语言构成**：{lang_txt}")
        if yr and len(yr) == 2:
            lines.append(f"- **年份跨度**：{yr[0]}–{yr[1]}")

        trend = _cluster_trend(evo_clusters, cid)
        if trend:
            lines.append(f"- **年份趋势**：{trend['trend']}（峰值年 {trend['peak_year']}；"
                         f"近5年 {trend['recent_sum']} vs 前5年 {trend['prev_sum']}）")

        authors, n_auth = _cluster_authors(at_topics, cid, global_core)
        if authors:
            al = fmt_list([f"{a.get('name', '?')}({a.get('count', '?')})" for a in authors], limit=5)
            lines.append(f"- **核心作者（本主题）**：{al}（共 {n_auth} 位活跃作者）")
        elif global_core:
            gc = fmt_list([f"{a.get('name', '?')}({a.get('total', '?')})" for a in global_core[:5]], limit=5)
            lines.append(f"- **核心作者（全局，未匹配到本主题）**：{gc}")

        # 综合写作提示（数据驱动）
        lines.append("- **综合提纲建议**：")
        lines.append(f"  1. 界定 `{fmt_list(terms[:4], limit=4)}` 等核心构念的定义与测量演进；")
        if trend and trend["trend"] in ("上升", "新兴/上升"):
            lines.append(f"  2. 解释该主题为何在 {trend['peak_year']} 年前后升温（情境/方法/政策触发）；")
        else:
            lines.append("  2. 比较该主题内部的主要竞争性解释与结论冲突来源；")
        lines.append("  3. 指出该主题的方法局限（如横断面/自评为主）与未决的理论增量；")
        lines.append("  4. 用“文献链四段式”（已有→近五年推进→仍然不足→本研究推进）收束到本综述定位。")
        lines.append("")

    return lines


def render_bridges(network):
    """跨主题桥接词：潜在整合点（驱动自 network.json 的 is_bridge 节点）。"""
    lines = ["### 2.x 跨主题桥接（潜在整合点）", ""]
    nodes = jget(network, "nodes", default=[]) or []
    bridges = [n for n in nodes if n.get("is_bridge")]
    if not bridges:
        lines.append("- （未提供网络或无明显桥接词。）")
        lines.append("")
        return lines
    bridges.sort(key=lambda n: n.get("degree", 0) or 0, reverse=True)
    lines.append("> 下列关键词同时跨多个主题簇出现，是天然的“整合性综述”切入点，"
                 "可用于连接多个子主题、提升综述的系统性。")
    for n in bridges[:12]:
        cids = n.get("cluster_ids", []) or []
        lines.append(f"- **{n.get('id')}**（度 {n.get('degree', '?')}，跨簇 {len(cids)} 个："
                     f"{fmt_list(cids, limit=8)}）")
    lines.append("")
    return lines


def render_gaps(gap_novelty, age, network, topics):
    """研究空白与新颖性：驱动自 gap_novelty.json + 数据信号。"""
    lines = ["## 三、研究空白与新颖性（Research Gaps & Novelty）", ""]
    lines.append("> 本节帮助把“宽泛兴趣”收敛为“可被文献问答的聚焦缺口”。"
                 "每个候选方向须同时标注：① 新颖性等级 ② 缺口类型。")

    gn = gap_novelty or {}
    nov = gn.get("novelty_levels", []) or []
    gaps = gn.get("gap_types", []) or []

    if nov:
        lines.append("### 3.1 新颖性等级（驱动自 gap_novelty.json · 选题收敛必标）")
        for lv in nov:
            lines.append(f"- **{lv.get('level')} {lv.get('name_zh', '')}**：{lv.get('definition', '')}")
            if lv.get("obhrm_example"):
                lines.append(f"  - 例：{lv.get('obhrm_example')}")
            if lv.get("judgement_question"):
                lines.append(f"  - 自问：{lv.get('judgement_question')}")
            if lv.get("signal"):
                lines.append(f"  - 门控信号：{lv.get('signal')}")
    else:
        lines.append("- （未加载 gap_novelty.json，新颖性等级不可用。）")
    lines.append("")

    if gaps:
        lines.append("### 3.2 五类缺口（驱动自 gap_novelty.json）")
        for g in gaps:
            lines.append(f"- **{g.get('name_zh', g.get('id', ''))}**：{g.get('definition', '')}")
            if g.get("judgement_question"):
                lines.append(f"  - 自问：{g.get('judgement_question')}")
    lines.append("")

    # 数据驱动缺口信号
    lines.append("### 3.3 数据信号（驱动自 age / network / topics）")
    signals = []
    if age:
        st = jget(age, "staleness", default={}) or {}
        rec = jget(age, "recency", default={}) or {}
        if st.get("old_pct") is not None and st.get("old_pct") > 10:
            signals.append(f"陈旧文献占比 {st.get('old_pct')}%（早于 {st.get('old_cutoff')}），"
                           f"提示该领域存在“证据未更新”型缺口，需补近五年推进")
        if rec.get("recent_pct") is not None:
            signals.append(f"近窗口占比 {rec.get('recent_pct')}%，可定位前沿快速演进的主题作为综述卖点")
    bridges = [n for n in (jget(network, "nodes", default=[]) or []) if n.get("is_bridge")]
    if bridges:
        signals.append(f"检测到 {len(bridges)} 个跨主题桥接词，可作为“整合多主题”的新颖切入点")
    cov = jget(topics, "coverage", default={}) or {}
    if cov.get("keyword_coverage_pct") is not None and cov.get("keyword_coverage_pct") < 80:
        signals.append(f"关键词覆盖率仅 {cov.get('keyword_coverage_pct')}%，"
                       f"无关键词文献（{cov.get('no_keywords')} 篇）可能含未被主题模型捕捉的缺口")
    if signals:
        for s in signals:
            lines.append(f"- {s}")
    else:
        lines.append("- （无显著数据信号，或对应产物未提供。）")
    lines.append("")
    return lines


def render_argumentation(argumentation):
    """论证脚手架：驱动自 argumentation_framework.json。"""
    lines = ["## 四、论证脚手架（Argumentation Scaffold）", ""]
    lines.append("> 综述不是文献笔记的序列。下列脚手架确保“每个主张有 Warrant、每条文献连到本研究、无孤岛段落”。")
    af = argumentation or {}

    # Toulmin
    tw = jget(af, "toulmin_warrant", default={}) or {}
    if tw:
        lines.append("### 4.1 图尔敏六要素（每段核心主张必含）")
        for e in tw.get("six_elements", []):
            lines.append(f"- {e}")
        if tw.get("rule"):
            lines.append(f"- 规则：{tw.get('rule')}")
        ex = jget(tw, "example")
        if ex:
            lines.append(f"- 示例：{ex}")
    lines.append("")

    # 文献链
    lc = jget(af, "literature_chain", default={}) or {}
    if lc:
        lines.append("### 4.2 文献链四段式（每个子主题收束用）")
        lines.append(f"- 规则：{lc.get('rule', '')}")
        tpl = lc.get("template", "")
        if tpl:
            for ln in tpl.split("\n"):
                if ln.strip():
                    lines.append(f"  {ln}")
    lines.append("")

    # 证据矩阵列
    em = jget(af, "evidence_matrix", default={}) or {}
    if em.get("columns"):
        lines.append("### 4.3 证据矩阵列（每条文献须落到嵌入位置）")
        lines.append(f"- 列：{fmt_list(em.get('columns', []), sep=' / ')}")
        pos = em.get("embedding_positions", []) or []
        if pos:
            lines.append(f"- 嵌入位置示例：{fmt_list(pos, limit=6)}（无嵌入位置 = 未连接，须删除或补连）")
    lines.append("")

    # 认识论匹配
    em_match = jget(af, "epistemic_matching", default={}) or {}
    levels = em_match.get("levels", []) or []
    if levels:
        lines.append("### 4.4 主张强度 × 证据等级（避免过度声称）")
        for lv in levels:
            lines.append(f"- **{lv.get('level', '')}**：可用「{lv.get('language', '')}」"
                         f"（如：{lv.get('example', '')}）")
        if em_match.get("failure_condition"):
            lines.append(f"- 红线：{em_match.get('failure_condition')}")
    lines.append("")

    # 反枚举闸门
    ae = jget(af, "anti_enumeration_gate", default={}) or {}
    if ae:
        lines.append("### 4.5 反“文献罗列”闸门")
        lines.append(f"- 规则：{ae.get('rule', '')}")
        if ae.get("failure_condition"):
            lines.append(f"- 失败判据：{ae.get('failure_condition')}")
    lines.append("")
    return lines


def render_section_order(templates):
    """章节顺序建议：驱动自 templates.json，剔除“参考文献”节（非本工具职责）。"""
    lines = ["## 五、章节顺序建议（Section Order）", ""]
    lines.append("> 基于 OBHRM 综述写作模板，给出推荐章节流。注意：**本骨架不含参考文献/引文格式化**，"
                 "引用落地请交给专用引文工具。")
    tmpl = jget(templates, "universal_template", default={}) or {}
    sections = tmpl.get("sections", []) or []
    if sections:
        lines.append("### 5.1 推荐主干章节")
        order = 1
        for s in sections:
            heading = s.get("heading", "")
            if heading and ("参考文献" in heading or "reference" in heading.lower()):
                continue  # 严格剔除引文/参考文献节
            wl = s.get("word_limit", "")
            gd = s.get("guidance", "")
            line = f"{order}. **{heading}**"
            if wl:
                line += f"（{wl}）"
            lines.append(line)
            if gd:
                lines.append(f"   - 要点：{gd}")
            order += 1
        lines.append(f"{order}. **质量自检**（对照第六节清单）")
    # 双语映射（剔除 References）
    bt = jget(templates, "bilingual_template", default={}) or {}
    bt_secs = bt.get("sections", []) or []
    bt_secs = [s for s in bt_secs if not ("参考文献" in s.get("zh", "") or "reference" in s.get("en", "").lower())]
    if bt_secs:
        lines.append("")
        lines.append("### 5.2 中英章节对照（供双语写作）")
        for s in bt_secs:
            lines.append(f"- {s.get('zh', '')} / {s.get('en', '')}")
    # 结构框架提示
    sf = jget(templates, "structure_framework", default={}) or {}
    if sf:
        lines.append("")
        lines.append("### 5.3 结构组织方式（择一或混合）")
        for m in sf.get("body_modes", []):
            lines.append(f"- {m}")
    lines.append("")
    return lines


def render_quality(quality, red_flags):
    """质量检查清单：驱动自 quality_scoring.json + red_flags.json。"""
    lines = ["## 六、质量检查清单（Quality Checklist）", ""]
    lines.append("> 完稿前逐项核对。标记 [红] 的维度为关键门控：任一 ≤2 分即不通过，须回炉修正。")

    q = quality or {}
    dims = jget(q, "protocol", "dimensions", default=[]) or []
    if dims:
        lines.append("### 6.1 八维度评分（驱动自 quality_scoring.json）")
        gate = jget(q, "gate_interlock", default={}) or {}
        critical = gate.get("critical_dimensions", []) or []
        for d in dims:
            name = d.get("name_zh", d.get("id", ""))
            mark = " [红/关键]" if name in critical else ""
            lines.append(f"- [ ] **{name}**（权重 {d.get('weight', '?')}）：{d.get('desc', '')}{mark}")
    else:
        lines.append("- （未加载 quality_scoring.json，八维度评分不可用。）")
    lines.append("")

    # 红线 / red flags
    rf = red_flags or {}
    rf_block = jget(rf, "red_flags", default={}) or {}
    if rf_block:
        lines.append("### 6.2 红线检查（驱动自 red_flags.json）")
        labels = {
            "process": "流程类",
            "literature": "文献类",
            "verification": "验证类",
        }
        for key, label in labels.items():
            items = rf_block.get(key, []) or []
            if not items:
                continue
            lines.append(f"**{label}**")
            for it in items:
                wrong = it.get("thought", "")
                right = it.get("correct", "")
                if wrong and right:
                    lines.append(f"- ✗「{wrong}」→ ✓ {right}")
    # 借口 vs 事实
    evf = jget(rf, "excuses_vs_facts", default=[]) or []
    if evf:
        lines.append("")
        lines.append("**借口 vs 事实**（写综述时自检）")
        for e in evf:
            lines.append(f"- 「{e.get('excuse', '')}」≠「{e.get('fact', '')}」")
    lines.append("")
    return lines


def render_framework_index(fw):
    """附录：列出本技能可用的抽取框架文件（不含任何引文/参考文献格式文件）。"""
    lines = ["## 附录：可用框架索引（references/）", ""]
    lines.append("下列框架文件位于本技能 `references/` 目录，供撰写时按需调阅。"
                 "**本目录不含任何 GB/T 7714 / APA / 参考文献列表 / 引用格式内容。**")
    label_map = {
        "gap_novelty": "研究缺口与新颖性判据（五类缺口 + 新颖性四等级）",
        "argumentation": "论证连接框架（图尔敏 / 文献链 / 证据矩阵 / 认识论匹配）",
        "quality": "综述写作八维度质量评分协议",
        "red_flags": "Red Flags 停止检查系统 + 验证机制",
        "templates": "写作模板（章节结构 / 双语映射）",
        "amj": "AMJ 写作九要素",
        "paradigms": "九种综述范式",
        "stage_gates": "三态阶段门控引擎（G1–G5）",
        "brainstorming": "对话式头脑风暴协议（选题对齐）",
        "closed_loop": "闭环编辑规则",
        "evidence_claim": "证据-论点映射协议",
        "reading_codes": "LRR 阅读密码（SPL/CPL/GAP/RAT/ROF）",
        "journal_standards": "期刊标准（理论建构三层次 / 创新金字塔）",
        "bilingual": "中英术语对照",
        "peer_review": "同行评审框架",
        "topic_scoping": "选题方向收敛提示词",
        "writing_style": "综述写作风格规范",
    }
    for key, desc in label_map.items():
        present = "✓" if fw.get(key) is not None else "（未加载）"
        lines.append(f"- [{present}] `{key}.json/.md` — {desc}")
    lines.append("")
    return lines


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------


def build_skeleton(topics, evolution, author_topic, network, age, dup, fw,
                   title="文献综述骨架", library=""):
    out = []
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    out.append(f"# {title}")
    out.append("")
    out.append(f"> 生成时间：{now}  ｜  生成器：EndNote 综述骨架生成器（review-skeleton）")
    if library:
        out.append(f"> 文献库：{library}")
    # 数据来源标注
    src = []
    for name, obj in [("topics", topics), ("evolution", evolution),
                      ("author_topic", author_topic), ("network", network),
                      ("age", age), ("dup", dup)]:
        src.append(f"{name}:{'✓' if obj else '✗'}")
    out.append(f"> 数据来源：{fmt_list(src, sep='  ')}")
    out.append("")
    out.append("> ⚠️ **本骨架不含参考文献 / 引文格式化能力**（无 GB/T 7714、APA、参考文献列表、引用管理）。"
               "引用落地请使用专用引文工具。")
    out.append("")

    out += render_intro_map(topics, age, network, fw)
    out += render_thematic(topics, evolution, author_topic, network)
    out += render_bridges(network)
    out += render_gaps(fw.get("gap_novelty"), age, network, topics)
    out += render_argumentation(fw.get("argumentation"))
    out += render_section_order(fw.get("templates"))
    out += render_quality(fw.get("quality"), fw.get("red_flags"))
    out += render_framework_index(fw)
    return "\n".join(out)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="EndNote 综述骨架生成器：消费分析产物，输出结构化 Markdown 综述提纲。")
    parser.add_argument("--topics", help="topics.json 路径（主题聚类）")
    parser.add_argument("--evolution", help="evolution.json 路径（主题×年份演化）")
    parser.add_argument("--author-topic", help="author_topic.json 路径（作者×主题）")
    parser.add_argument("--network", help="network.json 路径（共现网络）")
    parser.add_argument("--age", help="age.json 路径（时效性）")
    parser.add_argument("--dup", help="dup.json 路径（重复检测，可选）")
    parser.add_argument("--refs", default=None,
                        help="references/ 目录（OBHRM 框架）。默认取脚本同级 ../references")
    parser.add_argument("--out", default=None, help="输出 Markdown 文件路径（同时打印到 stdout）")
    parser.add_argument("--title", default="文献综述骨架", help="骨架标题")
    parser.add_argument("--library", default="", help="文献库显示名（脱敏）")
    args = parser.parse_args(argv)

    # 输入 JSON（任一可缺）
    topics = load_json(args.topics)
    evolution = load_json(args.evolution)
    author_topic = load_json(args.author_topic)
    network = load_json(args.network)
    age = load_json(args.age)
    dup = load_json(args.dup)

    # 框架目录
    if args.refs:
        refs_dir = Path(args.refs)
    else:
        refs_dir = Path(__file__).resolve().parent.parent / "references"
    fw = load_frameworks(refs_dir)

    markdown = build_skeleton(topics, evolution, author_topic, network, age, dup,
                              fw, title=args.title, library=args.library)

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(markdown, encoding="utf-8")
        print(f"[ok] 已写入 {out_path}（{len(markdown.splitlines())} 行）", file=sys.stderr)

    print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
