#!/usr/bin/env python3
# 确保套件包可导入（包目录在上级目录）
import os, sys
_skill_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _skill_dir not in sys.path:
    sys.path.append(_skill_dir)


"""
OBHRM 文献综述技能内置图表引擎
自建图表生成模块，覆盖全部学术图表类型，APA7 默认格式

用法：
    python chart_engine.py <图表类型> '<JSON数据>' [--title 图标题] [--output 输出目录]

示例：
    python chart_engine.py 箱线图 '{"data":[[1,2,3],[2,3,4]],"labels":["A组","B组"],"xlabel":"组别","ylabel":"得分"}'
    python chart_engine.py 条形图 '{"categories":["A","B"],"values":[4.2,3.8],"errors":[0.3,0.4],"xlabel":"组别","ylabel":"均值"}'

所有输出为 PDF（矢量）+ PNG（300dpi）
"""

import sys
import json
import os
import re
import warnings
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    # 改用 append 而非 insert(0)，防止 scripts/ 被置于 sys.path 搜索顺序最前，
    # 避免目录内同名模块覆盖标准库/第三方包（shadow injection）。
    sys.path.append(str(_SCRIPTS_DIR))

# resolve_safe_output 必须在 guard 外无条件导入：直接 `python chart_engine.py` 时
# scripts/ 已在 sys.path[0] → guard 为 False，import 若留在 guard 内会被跳过导致 NameError。
from obhrm_research_base.core.safe_path import resolve_safe_output

warnings.filterwarnings("ignore", module=r"^matplotlib\.")
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager as fm
    from matplotlib.patches import FancyArrowPatch, Rectangle
    import numpy as np
except ImportError:
    sys.stderr.write("缺少绘图依赖，请先安装：python3 -m pip install matplotlib numpy\n")
    sys.exit(1)


def _detect_cjk_fonts():
    """Return CJK-capable system fonts known to matplotlib, ordered by preference."""
    candidates = [
        "PingFang SC", "Heiti SC", "Songti SC", "Hiragino Sans GB",
        "STHeiti", "Microsoft YaHei", "SimHei", "Noto Sans CJK SC",
        "Source Han Sans SC", "WenQuanYi Micro Hei", "Arial Unicode MS",
    ]
    available = {f.name for f in fm.fontManager.ttflist}
    return [name for name in candidates if name in available]


# ─── APA7 全局样式 ─────────────────────────────────────────────
# 非侵入式中文字体策略：优先使用用户 matplotlibrc / 系统可用的 CJK 字体，
# 再回退到 Arial / DejaVu Sans 等西文字体。这样既尊重用户级配置，又保证在
# 未配置 CJK 首位的环境中中文标签不出现豆腐块。
_cjk_fonts = _detect_cjk_fonts()
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": _cjk_fonts + ["Arial", "Helvetica", "DejaVu Sans"],
    "axes.unicode_minus": False,
    "font.size": 9,
    "axes.titlesize": 11,
    "axes.labelsize": 10,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "legend.fontsize": 8,
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": False,
})

# Tol 无障碍配色（8类）
TOL_COLORS = ["#0077BB", "#33BBEE", "#009988", "#EE7733", "#CC3311", "#EE3377", "#BBBBBB", "#000000"]

# 流程图专用配色：学术综述论文黑白框线风（无彩色填充、无圆角）。
# 节点：黑色细边框矩形 + 白色填充 + 黑色文字；
# 连线：灰色细线，可带箭头；阶段分组：灰色虚线框。
FLOWCHART_NODE_FC = "white"        # 节点填充：白
FLOWCHART_NODE_EC = "black"        # 节点边框：黑细线
FLOWCHART_NODE_TC = "black"        # 节点文字：黑
FLOWCHART_EDGE_COLOR = "#777777"   # 连线：中灰细线
FLOWCHART_STAGE_EC = "#555555"     # 阶段虚线框：深灰
FLOWCHART_STAGE_LS = "--"          # 阶段框：虚线
FLOWCHART_LABEL_COLOR = "black"    # 图号 / 图注：黑

# 默认输出目录（受信任的内部默认值，由 --output / CHART_OUTPUT 或
# 内部 `_set_output_dir` 覆盖）。注意：CHART_OUTPUT 与 --output 属于
# 用户输入，在 __main__ 入口处经 resolve_safe_output 校验，超出允许范围即拒绝。
_OUTPUT_DIR = Path(os.getcwd())


def _set_output_dir(path):
    """受信任的内部接口：直接设定输出目录（供 selftest 等内部调用使用）。

    注意：本函数不做超出允许范围校验——CLI 的 --output / CHART_OUTPUT 等不可信
    输入必须在 __main__ 入口经 resolve_safe_output 校验后才传入此处。
    """
    global _OUTPUT_DIR
    _OUTPUT_DIR = Path(path)


def _save(fig, name: str) -> dict:
    """保存图表为 PDF + PNG，返回路径

    自动创建 _OUTPUT_DIR 的父目录（如不存在），避免相对界内新目录写盘时
    FileNotFoundError。
    """
    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    pdf_path = _OUTPUT_DIR / f"{name}.pdf"
    png_path = _OUTPUT_DIR / f"{name}.png"
    fig.savefig(pdf_path, format="pdf")
    fig.savefig(png_path, format="png")
    plt.close(fig)
    return {"pdf": str(pdf_path), "png": str(png_path)}


# ═══════════════════════════════════════════════════════════════
#  图表生成函数 — 英文命名（CHART_MAP 保留中文键）
# ═══════════════════════════════════════════════════════════════

def bar_chart(data: dict) -> dict:
    """data: categories, values, errors, xlabel, ylabel, title"""
    categories, values = data["categories"], data["values"]
    errors = data.get("errors")
    fig, ax = plt.subplots(figsize=(6.9, 4.5))
    # 每根柱单独取色，避免类别数 > 调色板长度时颜色静默撞色（原为切片 TOL_COLORS[:n]）
    bar_colors = [TOL_COLORS[i % len(TOL_COLORS)] for i in range(len(categories))]
    ax.bar(categories, values, yerr=errors, capsize=4, color=bar_colors, edgecolor="black", linewidth=0.5)
    ax.set_ylabel(data.get("ylabel", "")); ax.set_xlabel(data.get("xlabel", ""))
    ax.set_ylim(0, max(values) * 1.3 if values else 1)
    ax.set_title(data.get("title", ""), fontsize=11, fontweight="bold", pad=10)
    plt.tight_layout(); return _save(fig, "条形图")


def box_plot(data: dict) -> dict:
    """data: data[[...],...], labels, xlabel, ylabel, title"""
    series, labels = data["data"], data.get("labels", [f"组{i+1}" for i in range(len(data["data"]))])
    fig, ax = plt.subplots(figsize=(6.9, 4.5))
    bp = ax.boxplot(series, patch_artist=True, widths=0.6, medianprops=dict(color="black", linewidth=1.5))
    for patch, i in zip(bp["boxes"], range(len(series))):
        patch.set_facecolor(TOL_COLORS[i % len(TOL_COLORS)]); patch.set_alpha(0.7)
    ax.set_xticklabels(labels)
    ax.set_ylabel(data.get("ylabel", "")); ax.set_xlabel(data.get("xlabel", ""))
    ax.set_title(data.get("title", ""), fontsize=11, fontweight="bold", pad=10)
    plt.tight_layout(); return _save(fig, "箱线图")


def violin_plot(data: dict) -> dict:
    """data: data[[...],...], labels, xlabel, ylabel, title"""
    series, labels = data["data"], data.get("labels", [f"组{i+1}" for i in range(len(data["data"]))])
    fig, ax = plt.subplots(figsize=(6.9, 4.5))
    vp = ax.violinplot(series, showmeans=True, showmedians=True)
    for i, body in enumerate(vp.get("bodies", [])):
        body.set_facecolor(TOL_COLORS[i % len(TOL_COLORS)]); body.set_alpha(0.7)
    ax.set_xticks(range(1, len(labels) + 1)); ax.set_xticklabels(labels)
    ax.set_ylabel(data.get("ylabel", "")); ax.set_xlabel(data.get("xlabel", ""))
    ax.set_title(data.get("title", ""), fontsize=11, fontweight="bold", pad=10)
    plt.tight_layout(); return _save(fig, "小提琴图")


def line_chart(data: dict) -> dict:
    """data: x, series[{label, values, style}], xlabel, ylabel, title"""
    x, series_list = data["x"], data["series"]
    fig, ax = plt.subplots(figsize=(6.9, 4.5))
    for i, s in enumerate(series_list):
        ax.plot(x, s["values"], s.get("style", "o-"), color=TOL_COLORS[i % len(TOL_COLORS)],
                label=s.get("label", f"系列{i+1}"), linewidth=1.5, markersize=5)
    ax.set_xlabel(data.get("xlabel", "")); ax.set_ylabel(data.get("ylabel", ""))
    ax.set_title(data.get("title", ""), fontsize=11, fontweight="bold", pad=10)
    ax.legend(frameon=False); plt.tight_layout(); return _save(fig, "折线图")


def scatter_plot(data: dict) -> dict:
    """data: x, y, xlabel, ylabel, title, show_regression"""
    x, y = np.array(data["x"]), np.array(data["y"])
    fig, ax = plt.subplots(figsize=(6.9, 5.5))
    ax.scatter(x, y, color="#0077BB", alpha=0.6, edgecolors="black", linewidth=0.3, s=30)
    if data.get("show_regression", True) and len(x) > 2:
        from scipy import stats  # 惰性导入：仅在本函数需要回归线时才依赖 scipy
        slope, intercept, r, p, _ = stats.linregress(x, y)
        xl = np.linspace(x.min(), x.max(), 100)
        ax.plot(xl, slope * xl + intercept, color="#CC3311", linewidth=1.5, label=f"y={slope:.2f}x+{intercept:.2f}, r={r:.2f}")
        ax.legend(frameon=False, loc="lower right")
    ax.set_xlabel(data.get("xlabel", "")); ax.set_ylabel(data.get("ylabel", ""))
    ax.set_title(data.get("title", ""), fontsize=11, fontweight="bold", pad=10)
    plt.tight_layout(); return _save(fig, "散点图")


def forest_plot(data: dict) -> dict:
    """data: studies, effects, ci_lower, ci_upper, xlabel, title"""
    studies, effects = data["studies"], data["effects"]
    ci_lower, ci_upper = data["ci_lower"], data["ci_upper"]
    fig, ax = plt.subplots(figsize=(6.9, max(4.0, len(studies) * 0.55)))
    for i, study in enumerate(studies):
        is_overall = study.replace(" ", "") in ("总体", "Overall", "Summary") or study.startswith("总体")
        c, m, sz = ("#CC3311", "D", 8) if is_overall else ("#0077BB", "o", 6)
        ax.errorbar(effects[i], i, xerr=[[effects[i]-ci_lower[i]], [ci_upper[i]-effects[i]]],
                    fmt=m, color=c, markersize=sz, capsize=3, linewidth=1.2)
    ax.axvline(x=0, color="grey", linestyle="--", linewidth=0.8)
    ax.set_yticks(range(len(studies))); ax.set_yticklabels(studies)
    ax.set_xlabel(data.get("xlabel", "效应量 (Cohen's d)"))
    ax.set_title(data.get("title", ""), fontsize=11, fontweight="bold", pad=10)
    ax.invert_yaxis(); plt.tight_layout(); return _save(fig, "森林图")


def heatmap(data: dict) -> dict:
    """data: matrix[[...],...], labels, title, cmap, annot"""
    matrix, labels = np.array(data["matrix"]), data.get("labels", [])
    n = len(labels)
    fig, ax = plt.subplots(figsize=(max(5.0, n*1.1), max(4.5, n*1.0)))
    try:
        import seaborn as sns  # 可选依赖：提供带三角遮罩/批注的精美热力图
        mask = np.triu(np.ones_like(matrix, dtype=bool), k=1)
        sns.heatmap(matrix, mask=mask, annot=data.get("annot", True), fmt=".2f", cmap=data.get("cmap", "RdBu_r"),
                    center=0, vmin=-1, vmax=1, square=True, xticklabels=labels, yticklabels=labels,
                    linewidths=0.5, cbar_kws={"shrink": 0.8, "label": "r"}, ax=ax)
    except ImportError:
        # 优雅降级：seaborn 缺失时回退到 matplotlib imshow（保留矩阵与标签，无三角遮罩/批注）
        im = ax.imshow(matrix, cmap=data.get("cmap", "RdBu_r"), vmin=-1, vmax=1, aspect="auto")
        ax.set_xticks(range(n)); ax.set_yticks(range(n))
        if labels:
            ax.set_xticklabels(labels, rotation=45, ha="right"); ax.set_yticklabels(labels)
        fig.colorbar(im, ax=ax, shrink=0.8, label="r")
    ax.set_title(data.get("title", ""), fontsize=11, fontweight="bold", pad=10)
    plt.tight_layout(); return _save(fig, "热图")


def funnel_plot(data: dict) -> dict:
    """data: effects, se, xlabel, title"""
    effects, se = np.array(data["effects"]), np.array(data["se"])
    mean_effect = np.mean(effects)
    fig, ax = plt.subplots(figsize=(6.9, 5.0))
    ax.scatter(effects, se, color="#0077BB", edgecolors="black", linewidth=0.3, s=40, alpha=0.7)
    ax.axvline(x=mean_effect, color="#CC3311", linestyle="--", linewidth=1, label=f"均值={mean_effect:.2f}")
    ser = np.linspace(0.01, max(se)*1.1, 100)
    ax.fill_betweenx(ser, mean_effect-1.96*ser, mean_effect+1.96*ser, alpha=0.1, color="grey", label="95% CI")
    ax.set_xlabel(data.get("xlabel", "效应量")); ax.set_ylabel("标准误")
    ax.set_title(data.get("title", ""), fontsize=11, fontweight="bold", pad=10)
    ax.invert_yaxis(); ax.legend(frameon=False); plt.tight_layout(); return _save(fig, "漏斗图")


def grouped_bar_chart(data: dict) -> dict:
    """data: categories, groups[{label, values}], xlabel, ylabel, title"""
    categories, groups = data["categories"], data["groups"]
    fig, ax = plt.subplots(figsize=(6.9, 4.5))
    x, width = np.arange(len(categories)), 0.8 / len(groups)
    for i, g in enumerate(groups):
        offset = (i - (len(groups)-1)/2) * width
        ax.bar(x + offset, g["values"], width, label=g.get("label", f"组{i+1}"),
               color=TOL_COLORS[i % len(TOL_COLORS)], edgecolor="black", linewidth=0.5)
    ax.set_xlabel(data.get("xlabel", "")); ax.set_ylabel(data.get("ylabel", ""))
    ax.set_xticks(x); ax.set_xticklabels(categories)
    ax.set_title(data.get("title", ""), fontsize=11, fontweight="bold", pad=10)
    ax.legend(frameon=False)
    ax.set_ylim(0, max(max(g["values"]) for g in groups) * 1.3)
    plt.tight_layout(); return _save(fig, "分组条形图")


def radar_chart(data: dict) -> dict:
    """data: labels, series[{label, values}], title"""
    labels, series_list = data["labels"], data["series"]
    n = len(labels)
    angles = np.linspace(0, 2*np.pi, n, endpoint=False).tolist() + [0]
    fig, ax = plt.subplots(figsize=(6.0, 6.0), subplot_kw=dict(polar=True))
    for i, s in enumerate(series_list):
        vs = s["values"] + [s["values"][0]]
        ax.fill(angles, vs, alpha=0.1, color=TOL_COLORS[i % len(TOL_COLORS)])
        ax.plot(angles, vs, "o-", linewidth=1.5, color=TOL_COLORS[i % len(TOL_COLORS)], label=s.get("label", f"系列{i+1}"), markersize=4)
    ax.set_xticks(angles[:-1]); ax.set_xticklabels(labels)
    ax.set_title(data.get("title", ""), fontsize=11, fontweight="bold", pad=20)
    ax.legend(frameon=False, loc="upper right", bbox_to_anchor=(1.3, 1.1))
    plt.tight_layout(); return _save(fig, "雷达图")


def fishbone_diagram(data: dict) -> dict:
    """data: problem, causes[{label, sub_causes}], title"""
    problem, causes = data.get("problem", "核心问题"), data.get("causes", [])
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.set_xlim(-10, 10); ax.set_ylim(-8, 8); ax.axis("off")
    ax.annotate("", xy=(0, 0), xytext=(-8, 0), arrowprops=dict(arrowstyle="->", color="black", lw=3))
    ax.text(-8.5, 0.3, problem, fontsize=12, fontweight="bold", ha="left", color="#CC3311")
    n = len(causes)
    for i, cause in enumerate(causes):
        dy_sign = 1 if i < n/2 else -1
        angle = 20 + 35 * (i % max(1, n//2 + n%2)) / max(1, n//2 + n%2)
        rad = np.radians(angle)
        dx, dy = np.cos(rad), np.sin(rad) * dy_sign
        ex, ey = -4 * dx, 4.5 * dy
        ax.annotate("", xy=(ex, ey), xytext=(-0.5, dy*0.3),
                    arrowprops=dict(arrowstyle="->", color=TOL_COLORS[i % len(TOL_COLORS)], lw=2))
        ax.text(ex + dx*0.8, ey + dy*0.3, cause["label"], fontsize=9, fontweight="bold",
                color=TOL_COLORS[i % len(TOL_COLORS)], ha="center")
        for j, sub in enumerate(cause.get("sub_causes", [])):
            sx, sy = ex + dx*(1.5+j*1.5), ey + dy*(0.5+j*0.8)
            ax.plot([ex, sx], [ey, sy], color="grey", lw=0.8)
            ax.text(sx + dx*0.3, sy, sub, fontsize=7, color="grey")
    ax.set_title(data.get("title", ""), fontsize=11, fontweight="bold", pad=5)
    return _save(fig, "鱼骨图")


def sankey_diagram(data: dict) -> dict:
    """data: flows[{source, target, value}], title"""
    flows = data.get("flows", [])
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    nodes = {}
    for f in flows:
        for n in [f["source"], f["target"]]:
            if n not in nodes: nodes[n] = len(nodes)
    n_nodes = len(nodes)
    for name, idx in nodes.items():
        y = 0.85 - idx * 0.7 / max(1, n_nodes - 1)
        ax.text(0.05, y, name, fontsize=8, ha="right", va="center")
        ax.plot([0.08, 0.12], [y, y], "k-", lw=2); ax.plot([0.88, 0.92], [y, y], "k-", lw=2)
    for j, f in enumerate(flows):
        sy = 0.85 - nodes[f["source"]] * 0.7 / max(1, n_nodes - 1)
        ty = 0.85 - nodes[f["target"]] * 0.7 / max(1, n_nodes - 1)
        c = TOL_COLORS[j % len(TOL_COLORS)]
        ax.annotate("", xy=(0.88, ty), xytext=(0.12, sy),
                    arrowprops=dict(arrowstyle="->", color=c, lw=max(1, f["value"]/5), connectionstyle="arc3,rad=0.2"))
        ax.text(0.50, (sy+ty)/2, str(f["value"]), fontsize=7, ha="center", color=c)
    ax.set_title(data.get("title", ""), fontsize=11, fontweight="bold", pad=5)
    return _save(fig, "桑基图")


def venn_diagram(data: dict) -> dict:
    """data: sets[{label, size}], title"""
    sets = data.get("sets", [])
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.set_xlim(-4, 4); ax.set_ylim(-4, 4); ax.axis("off")
    n = len(sets)
    positions = {2: [(-1, 0), (1, 0)], 3: [(0, 1.2), (-1.2, -0.8), (1.2, -0.8)]}.get(
        n, [(np.cos(2*np.pi*i/n)*2, np.sin(2*np.pi*i/n)*2) for i in range(n)])
    for i, (s, (cx, cy)) in enumerate(zip(sets, positions)):
        r = np.sqrt(s.get("size", 10)) / 2 + 1
        ax.add_patch(plt.Circle((cx, cy), r, color=TOL_COLORS[i%len(TOL_COLORS)], alpha=0.3, ec="black", lw=1))
        ax.text(cx, cy, f"{s.get('label','')}\n({s.get('size','')})", fontsize=8, ha="center", va="center")
    ax.set_title(data.get("title", ""), fontsize=11, fontweight="bold", pad=10)
    ax.set_aspect("equal"); return _save(fig, "韦恩图")


def network_graph(data: dict) -> dict:
    """data: nodes[{id, label, size}], edges[{source, target, weight}], title"""
    nodes, edges = data.get("nodes", []), data.get("edges", [])
    np.random.seed(42)
    pos = {n["id"]: np.random.uniform(-3, 3, 2) for n in nodes}
    for _ in range(50):
        forces = {nid: np.zeros(2) for nid in pos}
        for e in edges:
            vec = pos[e["target"]] - pos[e["source"]]
            dist = np.linalg.norm(vec)
            if dist > 0:
                f = vec / dist * (dist - 1.5) * 0.1
                forces[e["source"]] += f; forces[e["target"]] -= f
        for nid in pos: forces[nid] -= pos[nid] * 0.01
        for nid in pos: pos[nid] += forces[nid]
    fig, ax = plt.subplots(figsize=(8, 7))
    for e in edges:
        ax.plot([pos[e["source"]][0], pos[e["target"]][0]], [pos[e["source"]][1], pos[e["target"]][1]],
                color="grey", lw=0.5 + e.get("weight", 1)*0.5, alpha=0.6)
    for i, node in enumerate(nodes):
        x, y = pos[node["id"]]
        ax.scatter(x, y, s=node.get("size", 1)*80, color=TOL_COLORS[i%len(TOL_COLORS)], alpha=0.8, ec="black", lw=1, zorder=5)
        ax.text(x, y+0.15, node.get("label", node["id"]), fontsize=7, ha="center", va="bottom")
    ax.axis("off"); ax.set_title(data.get("title", ""), fontsize=11, fontweight="bold", pad=10)
    return _save(fig, "网络图")


def mind_map(data: dict) -> dict:
    """data: root, children[{text, children}], title"""
    root, children = data.get("root", "主题"), data.get("children", [])
    fig, ax = plt.subplots(figsize=(12, max(6, len(children)*1.5)))
    ax.set_xlim(-1, 14); ax.set_ylim(-len(children)*1.5, len(children)*1.5); ax.axis("off")
    ax.text(0, 0, root, fontsize=14, fontweight="bold", ha="center", va="center",
            bbox=dict(boxstyle="round,pad=0.4", fc=TOL_COLORS[0], ec="white", alpha=0.9), color="white")
    for i, child in enumerate(children):
        y = (i - (len(children)-1)/2) * 2.8
        ax.annotate("", xy=(3, y), xytext=(1, 0),
                    arrowprops=dict(arrowstyle="->", color=TOL_COLORS[(i+1)%len(TOL_COLORS)], lw=1.5, connectionstyle="arc3,rad=0.1"))
        ax.text(3, y, child["text"], fontsize=10, fontweight="bold", ha="left", va="center",
                bbox=dict(boxstyle="round,pad=0.3", fc=TOL_COLORS[(i+1)%len(TOL_COLORS)], ec="white", alpha=0.15))
        for j, sub in enumerate(child.get("children", [])):
            sx, sy = 6 + j*2.8, y + (j - len(child.get("children",[]))/2 + 0.5) * 0.8
            ax.annotate("", xy=(sx, sy), xytext=(4.5, y), arrowprops=dict(arrowstyle="->", color="grey", lw=0.8))
            ax.text(sx, sy, sub, fontsize=8, ha="left", va="center", color="grey")
    ax.set_title(data.get("title", ""), fontsize=11, fontweight="bold", pad=10)
    plt.tight_layout(); return _save(fig, "思维导图")


def _effective_char_count(text):
    """估算文字视觉宽度（等效字符数）。

    中文/全角字符记 1.0，英文/数字按字母记 0.55，标点/空格记 0.3，
    用于初步估算节点框宽与单行折行宽度。
    """
    if not text:
        return 0.0
    count = 0.0
    for ch in text:
        code = ord(ch)
        if code > 0x2E7F:           # CJK 及全角符号（粗略范围）
            count += 1.0
        elif ch.isalnum():
            count += 0.55
        elif ch in " .,;:!?()[]{}'\"-/":
            count += 0.3
        else:
            count += 0.5
    return count


def _wrap_flowchart_text(text, max_chars):
    """按最大等效字符数折行：中文逐字、英文按词断行，保留单词间空格。

    Args:
        text: 原始节点文字。
        max_chars: 单行最大等效字符数（中文按 1 计）。

    Returns:
        list[str]: 折行后的各行文字。
    """
    if not text:
        return [""]
    tokens = re.findall(r"[A-Za-z0-9]+|\s+|\S", text)
    lines = []
    cur = ""
    for tok in tokens:
        if tok.isspace():
            if cur and not cur.endswith(" "):
                cur += " "
            continue
        if cur and len(cur.rstrip()) + len(tok) > max_chars:
            lines.append(cur.rstrip())
            cur = tok
        else:
            cur += tok
    if cur.strip():
        lines.append(cur.rstrip())
    return lines if lines else [""]


def _measure_text_extent(ax, renderer, text, font_size_pt):
    """测量多行文字在数据坐标系下的宽高（data units）。

    通过临时渲染文字并用 renderer 计算其窗口包围盒，再经 transData 反变换
    得到数据单位尺寸，作为节点框自适应尺寸的依据。
    """
    tmp = ax.text(0.0, 0.0, text, fontsize=font_size_pt,
                  ha="center", va="center")
    bbox = tmp.get_window_extent(renderer)
    inv = ax.transData.inverted()
    p0 = inv.transform((bbox.x0, bbox.y0))
    p1 = inv.transform((bbox.x1, bbox.y1))
    tmp.remove()
    return abs(p1[0] - p0[0]), abs(p1[1] - p0[1])


def _flow_rect_border(cx: float, cy: float, w: float, h: float,
                      tx: float, ty: float):
    """返回以 (cx,cy) 为中心、尺寸 w×h 的矩形、朝向 (tx,ty) 方向的边框交点。

    用于在节点框边缘（而非中心）起止箭头，避免箭头插入框内或被遮挡。
    """
    dx, dy = tx - cx, ty - cy
    if dx == 0 and dy == 0:
        return (cx, cy)
    sx = (w / 2.0) / abs(dx) if dx != 0 else float("inf")
    sy = (h / 2.0) / abs(dy) if dy != 0 else float("inf")
    s = min(sx, sy)
    return (cx + dx * s, cy + dy * s)


def _draw_flow_arrow(ax, src: dict, dst: dict, label: str, style: str):
    """在横向流程图中绘制 src 节点到 dst 节点的箭头（在框边缘起止，不穿框）。

    style:
      - "normal"     ：中灰细实线（#777）
      - "constraint" ：深灰实线（#555），用于「约束路径」上泳道
      - "enablement" ：中灰虚线（#777，--），用于「赋能路径」下泳道
    箭头文字以白底衬底，保证在细灰线上清晰可读；所有元素关闭裁剪以防被 bbox 裁掉。
    """
    scx, scy, sw, sh = src["cx"], src["cy"], src["box_w"], src["box_h"]
    tcx, tcy, tw, th = dst["cx"], dst["cy"], dst["box_w"], dst["box_h"]
    sx, sy = _flow_rect_border(scx, scy, sw, sh, tcx, tcy)
    tx, ty = _flow_rect_border(tcx, tcy, tw, th, scx, scy)
    if style == "enablement":
        color, ls, lw = FLOWCHART_EDGE_COLOR, "--", 1.1
    elif style == "constraint":
        color, ls, lw = "#555555", "-", 1.2
    else:
        color, ls, lw = FLOWCHART_EDGE_COLOR, "-", 0.9
    arrow = FancyArrowPatch((sx, sy), (tx, ty), arrowstyle="-|>",
                            color=color, lw=lw, linestyle=ls,
                            mutation_scale=10, zorder=1)
    arrow.set_clip_on(False)
    ax.add_patch(arrow)
    if label:
        mx, my = (sx + tx) / 2.0, (sy + ty) / 2.0
        lab = ax.text(mx, my, label, ha="center", va="center", fontsize=8,
                      color="black",
                      bbox=dict(boxstyle="square,pad=0.15", fc="white", ec="none", lw=0),
                      zorder=5)
        lab.set_clip_on(False)


def flow_chart(data: dict) -> dict:
    """data: steps[{text, type}], stages?[{name, steps:[idx...]}],
                edges?[{from, to, label?}], figure_label?("图1"), caption?(""), title?("")

    学术综述论文风格（横向 landscape、黑白灰、无圆角、黑色矩形框 + 细灰箭头）：
    - 整体为左→右宽幅横向流程（图宽 > 图高，比例约 3:1~4:1）；
    - 各 stage 沿水平方向排列为若干列，节点框之间、框与文字之间互不重叠；
    - 节点：黑色细边框矩形 + 白色填充 + 黑色文字；文字超宽按字符数折行，
      框尺寸随文字自适应，保证不裁切；
    - 箭头：灰色细线（可虚线），可带文字（理论名 / 路径名），以白底衬底；
    - 双路径：当某 stage 同时含 risk 与 benefit 节点（如「心理机制」）时判为
      「双泳道」stage——risk 节点置于上泳道、benefit 节点置于下泳道（同列、上下并行），
      二者均从上一 stage 末节点分出、汇入该 stage 的收敛节点（如 mechanism）；
      上泳道（约束路径）= 浅灰底纹 + 深灰实线，下泳道（赋能路径）= 更浅灰底纹 + 灰色
      虚线，双刃剑效应一目了然；
    - 阶段分组：data["stages"] 为 [{name, steps:[节点索引...]}]；同一 stage 的节点
      用灰色虚线框围起并标注 stage 名；无 stages 时退化为线性横向流程；
    - 图号 + 图注：data["figure_label"]（默认 "图1"）与 data["caption"]（≥80字，可选），
      在图下方居中渲染「图号 标题」、再左对齐渲染图注（按图宽折行，行距≥1.25×字号），
      并纳入 bbox 防裁切。

    防裁切逻辑：_wrap_flowchart_text / _measure_text_extent / 自适应框尺寸 /
    set_clip_on(False) / savefig(bbox="tight") 均保留。
    """
    steps = data.get("steps", [])
    n = len(steps)
    stages = data.get("stages") or []
    figure_label = data.get("figure_label", "图1")
    caption = data.get("caption", "") or ""
    figure_name = data.get("title", "") or ""
    edges = data.get("edges") or []

    # ── 横向布局常量（数据单位）──
    CHAR_W = 0.37         # 每等效字符宽度（数据单位，~9pt@SCALE），用于图注折行
    MAX_FONT = 10.0
    MIN_FONT = 8.0
    PAD_D = 0.35          # 框内留白（数据单位）
    TARGET_BOX_W = 4.5    # 目标节点框内文字宽度（数据单位），框尺寸随文字自适应
    COL_W = 6.0           # 水平列间距（数据单位）
    ROW_H = 3.2           # 双泳道上/下泳道垂直半距（数据单位）
    STAGE_PAD = 0.3       # 阶段虚线框相对节点组的留白
    LANE_LABEL_FS = 8     # 泳道标签字号
    SCALE = 0.32          # 数据单位→英寸比例（测量与出图保持一致，避免文字/框比例失真）

    # 初始化每个节点的布局字典
    layout = [{"text": s.get("text", ""), "type": s.get("type", "process"),
               "wrapped": "", "cx": 0.0, "cy": 0.0,
               "box_w": 0.0, "box_h": 0.0, "font": MAX_FONT} for s in steps]

    # 第二遍：结构布局（位置只依赖 stage 结构与行列常量，与文字尺寸无关）
    dl_stage = None
    for si, st in enumerate(stages):
        types = [steps[i].get("type", "") for i in st.get("steps", [])]
        if "risk" in types and "benefit" in types:
            dl_stage = si
            break

    col_cursor = 0
    for si, st in enumerate(stages):
        members = st.get("steps", [])
        if not members:
            continue
        if si == dl_stage:
            types = [steps[i].get("type", "") for i in members]
            risk_i = members[types.index("risk")]
            benefit_i = members[types.index("benefit")]
            converge = [i for i in members if i not in (risk_i, benefit_i)]
            layout[risk_i]["cx"] = col_cursor * COL_W
            layout[risk_i]["cy"] = ROW_H
            layout[benefit_i]["cx"] = col_cursor * COL_W
            layout[benefit_i]["cy"] = -ROW_H
            for c in converge:
                layout[c]["cx"] = (col_cursor + 1) * COL_W
                layout[c]["cy"] = 0.0
            col_cursor += 2
        else:
            for m in members:
                layout[m]["cx"] = col_cursor * COL_W
                layout[m]["cy"] = 0.0
                col_cursor += 1

    # 无 stages 时的退化处理：所有节点排成一行（线性横向流程）
    if not stages:
        for i, item in enumerate(layout):
            item["cx"] = i * COL_W
            item["cy"] = 0.0
        col_cursor = max(1, n)

    # 第三遍：自适应字号 + 测量，确定最终框尺寸（框=文字+留白，保证不裁切）
    prov_x_min, prov_x_max = -COL_W, col_cursor * COL_W + COL_W
    prov_y_min, prov_y_max = -ROW_H - 1.5, ROW_H + 1.5
    prov_xr = prov_x_max - prov_x_min
    prov_yr = prov_y_max - prov_y_min
    fig, ax = plt.subplots(figsize=(prov_xr * SCALE, prov_yr * SCALE))
    ax.set_axis_off()
    ax.set_xlim(prov_x_min, prov_x_max)
    ax.set_ylim(prov_y_min, prov_y_max)
    fig.canvas.draw()  # 实例化 renderer，供测量文字 extent
    renderer = fig.canvas.get_renderer()

    # 依据当前比例测量单个 CJK 字符宽度，推导单行折行字符数（与目标框宽一致）
    wc_w, _ = _measure_text_extent(ax, renderer, "测", MAX_FONT)
    max_chars = max(4, int((TARGET_BOX_W - 2 * PAD_D) / wc_w)) if wc_w > 0 else 16

    for item in layout:
        font = MAX_FONT
        wrapped = "\n".join(_wrap_flowchart_text(item["text"], max_chars))
        tw, th = _measure_text_extent(ax, renderer, wrapped, font)
        while font > MIN_FONT and tw > TARGET_BOX_W:
            font -= 0.5
            tw, th = _measure_text_extent(ax, renderer, wrapped, font)
        item["font"] = font
        item["wrapped"] = wrapped
        item["box_w"] = tw + 2 * PAD_D
        item["box_h"] = th + 2 * PAD_D

    # ── 绘制双泳道底纹（置于最底层 zorder=0）──
    if dl_stage is not None:
        st = stages[dl_stage]
        members = st.get("steps", [])
        types = [steps[i].get("type", "") for i in members]
        risk_i = members[types.index("risk")]
        benefit_i = members[types.index("benefit")]
        converge = [i for i in members if i not in (risk_i, benefit_i)]
        conv_i = converge[-1] if converge else risk_i
        # 分支节点 = 上一 stage 末节点（无则取 risk 自身）
        prev_members = stages[dl_stage - 1].get("steps", []) if dl_stage > 0 else []
        branch_i = prev_members[-1] if prev_members else risk_i
        x0b = layout[branch_i]["cx"] + layout[branch_i]["box_w"] / 2.0 + 0.3
        x1b = layout[conv_i]["cx"] - layout[conv_i]["box_w"] / 2.0 - 0.3
        bh = max(layout[risk_i]["box_h"], layout[conv_i]["box_h"]) + 0.6
        # 上泳道：约束路径（浅灰底纹）
        band_top = Rectangle((x0b, ROW_H - bh / 2.0), x1b - x0b, bh,
                             fc="#ECECEC", ec="none", zorder=0)
        band_top.set_clip_on(False)
        ax.add_patch(band_top)
        # 下泳道：赋能路径（更浅灰底纹）
        band_bot = Rectangle((x0b, -ROW_H - bh / 2.0), x1b - x0b, bh,
                             fc="#F7F7F7", ec="none", zorder=0)
        band_bot.set_clip_on(False)
        ax.add_patch(band_bot)
        ax.text(x0b + 0.15, ROW_H + bh / 2.0 - 0.12, "约束路径（阻碍型要求）",
                ha="left", va="top", fontsize=LANE_LABEL_FS, color="#555555",
                zorder=1).set_clip_on(False)
        ax.text(x0b + 0.15, -ROW_H - bh / 2.0 + 0.12, "赋能路径（挑战型资源）",
                ha="left", va="bottom", fontsize=LANE_LABEL_FS, color="#555555",
                zorder=1).set_clip_on(False)

    # ── 绘制阶段虚线分组框 + stage 名（置于底层，节点之前）──
    stage_box = []  # 每个元素 (x0, y1, x1, y0)
    for si, st in enumerate(stages):
        members = [i for i in st.get("steps", []) if 0 <= i < n]
        if not members:
            continue
        max_bw = max(layout[i]["box_w"] for i in members)
        xs = [layout[i]["cx"] for i in members]
        tops = [layout[i]["cy"] + layout[i]["box_h"] / 2.0 for i in members]
        bots = [layout[i]["cy"] - layout[i]["box_h"] / 2.0 for i in members]
        x0 = min(xs) - max_bw / 2.0 - STAGE_PAD
        x1 = max(xs) + max_bw / 2.0 + STAGE_PAD
        y0 = max(tops) + STAGE_PAD
        y1 = min(bots) - STAGE_PAD
        rect = Rectangle((x0, y1), x1 - x0, y0 - y1, fill=False,
                         ec=FLOWCHART_STAGE_EC, ls=FLOWCHART_STAGE_LS, lw=0.9, zorder=1)
        rect.set_clip_on(False)
        ax.add_patch(rect)
        ax.text((x0 + x1) / 2.0, y0 + 0.18, st.get("name", ""),
                ha="center", va="bottom", fontsize=9, fontweight="bold",
                color=FLOWCHART_LABEL_COLOR, zorder=2).set_clip_on(False)
        stage_box.append((x0, y1, x1, y0))

    # ── 绘制节点（黑框 + 白底 + 黑字矩形，无圆角）──
    for item in layout:
        cy = item["cy"]
        bw, bh = item["box_w"], item["box_h"]
        rect = Rectangle((item["cx"] - bw / 2.0, cy - bh / 2.0), bw, bh,
                         fc=FLOWCHART_NODE_FC, ec=FLOWCHART_NODE_EC, lw=0.9, zorder=2)
        rect.set_clip_on(False)
        ax.add_patch(rect)
        txt = ax.text(item["cx"], cy, item["wrapped"], fontsize=item["font"],
                      ha="center", va="center", color=FLOWCHART_NODE_TC, zorder=3)
        txt.set_clip_on(False)

    # ── 箭头：根据 stages 结构推导（双泳道 stage 重写为「分出→并行→汇入」）──
    label_map = {(e.get("from"), e.get("to")): e.get("label", "") for e in edges}
    arrows = []
    prev_last = None
    for si, st in enumerate(stages):
        members = st.get("steps", [])
        if not members:
            continue
        if si == dl_stage:
            types = [steps[i].get("type", "") for i in members]
            risk_i = members[types.index("risk")]
            benefit_i = members[types.index("benefit")]
            converge = [i for i in members if i not in (risk_i, benefit_i)]
            if prev_last is not None:
                arrows.append((prev_last, risk_i,
                               label_map.get((prev_last, risk_i)) or "约束路径", "constraint"))
                arrows.append((prev_last, benefit_i,
                               label_map.get((prev_last, benefit_i)) or "赋能路径", "enablement"))
            for c in converge:
                arrows.append((risk_i, c, "自主性中介", "constraint"))
                arrows.append((benefit_i, c, "自主性中介", "enablement"))
            prev_last = converge[-1] if converge else risk_i
        else:
            for k, m in enumerate(members):
                if prev_last is not None and k == 0:
                    arrows.append((prev_last, m, label_map.get((prev_last, m), ""), "normal"))
                if k > 0:
                    arrows.append((members[k - 1], m, label_map.get((members[k - 1], m), ""), "normal"))
            prev_last = members[-1]
    # 无 stages 退化：线性连接
    if not stages:
        for i in range(n - 1):
            arrows.append((i, i + 1, label_map.get((i, i + 1), ""), "normal"))

    for (f, t, lab, style) in arrows:
        if 0 <= f < n and 0 <= t < n:
            _draw_flow_arrow(ax, layout[f], layout[t], lab, style)

    # ── 图号 + 图注（纳入 bbox，防裁切）──
    node_lefts = [item["cx"] - item["box_w"] / 2.0 for item in layout]
    node_rights = [item["cx"] + item["box_w"] / 2.0 for item in layout]
    node_tops = [item["cy"] + item["box_h"] / 2.0 for item in layout]
    node_bots = [item["cy"] - item["box_h"] / 2.0 for item in layout]
    sb_lefts = [b[0] for b in stage_box]
    sb_rights = [b[2] for b in stage_box]
    sb_tops = [b[3] for b in stage_box]
    sb_bots = [b[1] for b in stage_box]
    content_left = min(node_lefts + sb_lefts) if (node_lefts or sb_lefts) else -1.0
    content_right = max(node_rights + sb_rights) if (node_rights or sb_rights) else 1.0
    content_top = max(node_tops + sb_tops) if (node_tops or sb_tops) else 1.0
    content_bottom = min(node_bots + sb_bots) if (node_bots or sb_bots) else -1.0

    center_x = (content_left + content_right) / 2.0
    label_text = (figure_label + " " + figure_name).strip() if figure_name else figure_label
    label_y = content_bottom - 0.4
    ax.text(center_x, label_y, label_text, ha="center", va="top",
            fontsize=10, fontweight="bold", color=FLOWCHART_LABEL_COLOR, zorder=4).set_clip_on(False)

    # 图注（左对齐，按图宽折行；每行行距 = 1.35×行高 ≥ 1.25×字号，确保不重叠）
    caption_bottom_y = label_y
    if caption:
        usable_w = (content_right - content_left) - 0.2
        cap_max_chars = max(12, int(usable_w / CHAR_W * 0.95))
        cap_lines = _wrap_flowchart_text(caption, cap_max_chars)
        sample = cap_lines[0] if cap_lines else "图"
        _, lh = _measure_text_extent(ax, renderer, sample, 8.5)
        step = lh * 1.35
        cap_y = label_y - 0.6
        for i, ln in enumerate(cap_lines):
            ax.text(content_left, cap_y - i * step, ln, ha="left", va="top",
                    fontsize=8.5, color=FLOWCHART_LABEL_COLOR, zorder=4).set_clip_on(False)
        caption_bottom_y = cap_y - len(cap_lines) * step

    # ── 坐标范围纳入全部内容（SCALE 与测量一致，避免文字/框比例失真）──
    cx_min = content_left - 0.4
    cx_max = content_right + 0.4
    cy_min = caption_bottom_y - 0.4
    cy_max = content_top + 0.4
    ax.set_xlim(cx_min, cx_max)
    ax.set_ylim(cy_min, cy_max)
    fig.set_size_inches((cx_max - cx_min) * SCALE, (cy_max - cy_min) * SCALE)
    return _save(fig, "流程图")


def histogram(data: dict) -> dict:
    """data: values, bins, xlabel, ylabel, title"""
    fig, ax = plt.subplots(figsize=(6.9, 4.5))
    ax.hist(data["values"], bins=data.get("bins", 20), color="#0077BB", alpha=0.7, edgecolor="black", linewidth=0.5)
    ax.set_xlabel(data.get("xlabel", "")); ax.set_ylabel(data.get("ylabel", "频数"))
    ax.set_title(data.get("title", ""), fontsize=11, fontweight="bold", pad=10)
    plt.tight_layout(); return _save(fig, "直方图")


def pie_chart(data: dict) -> dict:
    """data: labels, values, title (注意：APA7不推荐饼图)"""
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.pie(data["values"], labels=data["labels"], autopct="%1.1f%%", colors=TOL_COLORS[:len(data["labels"])], startangle=90, textprops={"fontsize": 8})
    ax.set_title(data.get("title", ""), fontsize=11, fontweight="bold", pad=10)
    return _save(fig, "饼图")


def area_chart(data: dict) -> dict:
    """data: x, series[{label, values}], xlabel, ylabel, title"""
    x, series_list = data["x"], data["series"]
    fig, ax = plt.subplots(figsize=(6.9, 4.5))
    for i, s in enumerate(series_list):
        ax.fill_between(x, s["values"], alpha=0.3, color=TOL_COLORS[i%len(TOL_COLORS)], label=s.get("label", f"系列{i+1}"))
        ax.plot(x, s["values"], color=TOL_COLORS[i%len(TOL_COLORS)], linewidth=1.5)
    ax.set_xlabel(data.get("xlabel", "")); ax.set_ylabel(data.get("ylabel", ""))
    ax.set_title(data.get("title", ""), fontsize=11, fontweight="bold", pad=10)
    ax.legend(frameon=False); plt.tight_layout(); return _save(fig, "面积图")


def simple_slope_plot(data: dict) -> dict:
    """调节效应简单斜率图。data: x[min,max], groups[{label, intercept, slope}], xlabel, ylabel, title, highlight(可选bool高亮交互区)"""
    x = np.array(data["x"], dtype=float)
    groups = data["groups"]
    fig, ax = plt.subplots(figsize=(6.9, 5.0))
    for i, g in enumerate(groups):
        y = float(g["intercept"]) + float(g["slope"]) * x
        ax.plot(x, y, "-", color=TOL_COLORS[i % len(TOL_COLORS)],
                label=g.get("label", f"组{i+1}"), linewidth=2)
    # 可选：高亮两组分叉的交互区（视觉上直观呈现调节效应）
    if data.get("highlight") and len(groups) >= 2:
        y0 = float(groups[0]["intercept"]) + float(groups[0]["slope"]) * x
        y1 = float(groups[1]["intercept"]) + float(groups[1]["slope"]) * x
        ax.fill_between(x, y0, y1, color=TOL_COLORS[1], alpha=0.12)
    ax.set_xlabel(data.get("xlabel", "")); ax.set_ylabel(data.get("ylabel", ""))
    ax.set_title(data.get("title", ""), fontsize=11, fontweight="bold", pad=10)
    ax.legend(frameon=False); plt.tight_layout(); return _save(fig, "简单斜率图")


# ═══════════════════════════════════════════════════════════════
#  命令行入口
# ═══════════════════════════════════════════════════════════════

CHART_MAP = {
    "条形图": bar_chart, "箱线图": box_plot, "小提琴图": violin_plot, "折线图": line_chart,
    "散点图": scatter_plot, "森林图": forest_plot, "热图": heatmap, "漏斗图": funnel_plot,
    "分组条形图": grouped_bar_chart, "雷达图": radar_chart, "鱼骨图": fishbone_diagram, "桑基图": sankey_diagram,
    "韦恩图": venn_diagram, "网络图": network_graph, "思维导图": mind_map, "流程图": flow_chart,
    "直方图": histogram, "饼图": pie_chart, "面积图": area_chart, "简单斜率图": simple_slope_plot,
}

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python chart_engine.py <图表类型> '<JSON数据>' [--title 标题] [--output 输出目录]")
        print(f"\n支持图表类型: {', '.join(CHART_MAP.keys())}")
        sys.exit(1)

    chart_type, raw_data = sys.argv[1], sys.argv[2]
    extra = {}
    explicit_out = None

    # CHART_OUTPUT 属于用户输入，先校验（base 默认为 cwd）
    env_out = os.environ.get("CHART_OUTPUT")
    if env_out:
        try:
            explicit_out = resolve_safe_output(env_out, base=os.getcwd())
        except ValueError as e:
            print(f"错误：CHART_OUTPUT 输出目录超出允许范围，拒绝写入 — {e}", file=sys.stderr)
            sys.exit(1)

    for i in range(3, len(sys.argv)):
        if sys.argv[i] == "--title" and i + 1 < len(sys.argv):
            extra["title"] = sys.argv[i + 1]
        elif sys.argv[i] == "--output" and i + 1 < len(sys.argv):
            try:
                explicit_out = resolve_safe_output(sys.argv[i + 1], base=os.getcwd())
            except ValueError as e:
                print(f"错误：--output 输出目录超出允许范围，拒绝写入 — {e}", file=sys.stderr)
                sys.exit(1)

    if explicit_out is not None:
        _set_output_dir(str(explicit_out))

    if chart_type not in CHART_MAP:
        print(f"未知图表类型: {chart_type}"); print(f"支持: {', '.join(CHART_MAP.keys())}"); sys.exit(1)

    data = json.loads(raw_data)
    if "title" in extra and "title" not in data:
        data["title"] = extra["title"]
    result = CHART_MAP[chart_type](data)
    print(json.dumps(result, ensure_ascii=False))
