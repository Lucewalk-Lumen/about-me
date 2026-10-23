#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
chart_engine.py — 管理学论文图表引擎（可选依赖）

聚焦本科管理学论文最常见图表类型，APA7 风格，输出 PDF + PNG。
借鉴通用图表引擎设计思路，按本科论文场景裁剪为聚焦子集。

按派生 fork 去重铁律，应将本文件独有增量回灌单一真源 shared-core 并改为引用，
而非保留多份副本。本会话仅补充依赖守卫注释，未做删除式去重（避免破坏跨包运行时导入）。

 依赖为「可选」：matplotlib / seaborn / numpy / scipy 未安装时，
   运行本脚本会给出明确提示，不影响技能包其他功能（符合 requirements.lock
   中「无必需第三方依赖」的纯净分发承诺）。

用法：
    python scripts/chart_engine.py 条形图 '{"categories":["A","B"],"values":[3,5],"error":[0.4,0.6]}' --output ./产出/
    python scripts/chart_engine.py --list          # 列出支持的图表类型
    python scripts/chart_engine.py 散点图 '{"x":[1,2,3],"y":[2,4,5],"show_regression":true}' --output ./产出/

支持类型（9 种）：条形图 / 饼图 / 直方图 / 箱线图 / 散点图 / 简单斜率图 / 雷达图 / 热图 / 折线图
"""

import argparse
import json
import os
import sys

# ───────────────────────────────────────────────────────────────
#  软依赖声明（未安装时跳过图表功能，不影响技能其余功能）
# ───────────────────────────────────────────────────────────────
_MATPLOTLIB_OK = True
try:
    import matplotlib
    matplotlib.use("Agg")  # 无界面后端，适配服务器/分发环境
    import matplotlib.pyplot as plt
    import numpy as np
    from scipy import stats
except Exception as _imp_err:  # pragma: no cover
    _MATPLOTLIB_OK = False
    _IMP_ERR = _imp_err


# ───────────────────────────────────────────────────────────────
#  中文（CJK）字体适配
# ───────────────────────────────────────────────────────────────
def _setup_cjk_font():
    """尝试设置 CJK 字体；找不到则退回默认并提示。

    旧实现缺陷：用 ``if c in findfont(c)`` 做子串判断，但 findfont 返回的是
    字体**文件路径字符串**（如 ``/System/Library/Fonts/PingFang.ttc``），字族名
    "PingFang SC" 几乎不可能作为子串出现在路径里，因此恒为 False；而 except 兜底
    里的 ``FontProperties(family=c)`` 从不校验字体真实存在，会把未安装的字体
    误判为"已找到"，导致渲染时回落到无 CJK 字形的 DejaVuSans，中文变成方框。

    本实现：以 FontProperties 入参、``fallback_to_default=False`` 调用 findfont——
    找不到会抛 ValueError（不再臆测）；命中则拿到真实路径，再用 ft2font 抽样验证
    该字体确实包含 CJK 字形，避免"字体存在却无中文"的二次误判。
    """
    candidates = [
        "PingFang SC", "Microsoft YaHei", "SimHei",
        "Noto Sans CJK SC", "Source Han Sans SC", "Arial Unicode MS",
    ]
    found = None
    fm = matplotlib.font_manager
    try:
        from matplotlib import ft2font
        _have_ft2 = True
    except Exception:
        _have_ft2 = False

    # 抽样若干高频汉字，验证候选字体真实含有 CJK 字形
    probe_chars = "中文字体测试图表数据样本分析"
    for c in candidates:
        try:
            # 入参须为 FontProperties；fallback_to_default=False 时找不到即抛 ValueError，
            # 绝不会回落到默认字体。
            prop = fm.FontProperties(family=c)
            path = fm.findfont(prop, fallback_to_default=False)
        except Exception:
            # 字体不存在或无法解析 —— 跳过，不臆测"找到了"
            continue
        if not path:
            continue
        # 排除 matplotlib 自带的 DejaVuSans 兜底（不含 CJK 字形）
        if "DejaVuSans" in os.path.basename(path) or "dejavu" in path.lower():
            continue
        # 若可用 ft2font，进一步确认该字体真的包含 CJK 字形
        if _have_ft2:
            try:
                face = ft2font.FT2Font(path)
                if all(face.get_char_index(ord(ch)) > 0 for ch in probe_chars):
                    found = c
                    break
                # 字形不全则继续尝试下一个候选
                continue
            except Exception:
                continue
        found = c
        break
    if found:
        plt.rcParams["font.sans-serif"] = [found]
    else:
        sys.stderr.write(
            "[chart_engine] 警告：未检测到 CJK 字体，中文标签可能显示为方框。"
            "请安装中文字体（如 Noto Sans CJK）或传入英文标签。\n"
        )
    plt.rcParams["axes.unicode_minus"] = False  # 正常显示负号


# ───────────────────────────────────────────────────────────────
#  APA7 通用样式
# ───────────────────────────────────────────────────────────────
def _apa_style(fig):
    """应用 APA7 风格的细节：去上右边框、300dpi、清晰字号。"""
    fig.set_dpi(300)
    for ax in fig.axes:
        for _spine in ("top", "right"):
            if _spine in ax.spines:
                ax.spines[_spine].set_visible(False)
        ax.tick_params(direction="out", length=4)
        if ax.get_title():
            ax.set_title(ax.get_title(), fontsize=12, fontweight="bold", pad=12)
        if ax.xaxis.label.get_text():
            ax.xaxis.label.set_size(11)
        if ax.yaxis.label.get_text():
            ax.yaxis.label.set_size(11)
    fig.tight_layout()
    return fig


def _save(fig, name, output):
    """保存为 PDF + PNG，返回文件列表。"""
    os.makedirs(output, exist_ok=True)
    base = os.path.join(output, name)
    pdf = base + ".pdf"
    png = base + ".png"
    fig.savefig(pdf, format="pdf", bbox_inches="tight")
    fig.savefig(png, format="png", dpi=300, bbox_inches="tight")
    return [pdf, png]


# ───────────────────────────────────────────────────────────────
#  图表函数（每个接收 dict 参数 a，返回 matplotlib Figure）
# ───────────────────────────────────────────────────────────────
def 条形图(a):
    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    cats = a.get("categories", [])
    vals = a.get("values", [])
    err = a.get("error")
    bars = ax.bar(cats, vals, yerr=err, capsize=5,
                  color="#4C72B0", edgecolor="white", alpha=0.9)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v, f"{v:.2f}",
                ha="center", va="bottom", fontsize=9)
    ax.set_title(a.get("title", "条形图"))
    ax.set_xlabel(a.get("xlabel", ""))
    ax.set_ylabel(a.get("ylabel", "均值"))
    return _apa_style(fig)


def 饼图(a):
    fig, ax = plt.subplots(figsize=(5.5, 5.0))
    labels = a.get("labels", [])
    sizes = a.get("sizes", [])
    ax.pie(sizes, labels=labels, autopct="%1.1f%%", startangle=90,
           colors=plt.cm.Set2.colors, textprops={"fontsize": 10})
    ax.set_title(a.get("title", "饼图"))
    ax.axis("equal")
    return _apa_style(fig)


def 直方图(a):
    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    data = a.get("data", [])
    bins = a.get("bins", 10)
    ax.hist(data, bins=bins, color="#55A868", edgecolor="white", alpha=0.9)
    ax.set_title(a.get("title", "直方图"))
    ax.set_xlabel(a.get("xlabel", "数值"))
    ax.set_ylabel(a.get("ylabel", "频次"))
    return _apa_style(fig)


def 箱线图(a):
    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    groups = a.get("groups", {})
    if groups:
        data = list(groups.values())
        labels = list(groups.keys())
    else:
        data = a.get("data", [[]])
        labels = a.get("labels", [f"组{i+1}" for i in range(len(data))])
    bp = ax.boxplot(data, patch_artist=True, medianprops={"color": "black"})
    ax.set_xticks(range(1, len(labels) + 1))
    ax.set_xticklabels(labels)
    for patch in bp["boxes"]:
        patch.set_facecolor("#C44E52")
        patch.set_alpha(0.7)
    ax.set_title(a.get("title", "箱线图"))
    ax.set_ylabel(a.get("ylabel", "数值"))
    return _apa_style(fig)


def 散点图(a):
    fig, ax = plt.subplots(figsize=(6.5, 4.6))
    x = a.get("x", [])
    y = a.get("y", [])
    ax.scatter(x, y, color="#4C72B0", alpha=0.7, edgecolor="white", s=40)
    if a.get("show_regression"):
        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)
        slope, intercept, r, p, se = stats.linregress(x, y)
        xs = np.linspace(min(x), max(x), 100)
        ax.plot(xs, intercept + slope * xs, color="#C44E52", lw=2,
                label=f"y={slope:.2f}x+{intercept:.2f} (r={r:.2f})")
        ax.legend(frameon=False, fontsize=9)
    ax.set_title(a.get("title", "散点图"))
    ax.set_xlabel(a.get("xlabel", "X"))
    ax.set_ylabel(a.get("ylabel", "Y"))
    return _apa_style(fig)


def 简单斜率图(a):
    """调节效应简单斜率图：绘制低/高调节变量水平下的两条回归线。"""
    fig, ax = plt.subplots(figsize=(6.5, 4.6))
    x = np.asarray(a.get("x", []), dtype=float)
    low_y = np.asarray(a.get("low_y", []), dtype=float)
    high_y = np.asarray(a.get("high_y", []), dtype=float)
    legend = a.get("legend", ["低水平", "高水平"])
    ax.plot(x, low_y, color="#4C72B0", lw=2, marker="o", label=legend[0])
    ax.plot(x, high_y, color="#C44E52", lw=2, marker="s", label=legend[1])
    ax.legend(frameon=False, fontsize=9)
    ax.set_title(a.get("title", "调节效应简单斜率图"))
    ax.set_xlabel(a.get("xlabel", "自变量"))
    ax.set_ylabel(a.get("ylabel", "因变量"))
    return _apa_style(fig)


def 雷达图(a):
    fig, ax = plt.subplots(figsize=(5.5, 5.5), subplot_kw={"polar": True})
    cats = a.get("categories", [])
    values = a.get("values", [])
    import math
    N = len(cats)
    if N == 0:
        raise ValueError("雷达图需要非空的 categories")
    angles = [n / float(N) * 2 * math.pi for n in range(N)]
    angles += angles[:1]
    series = values if (values and isinstance(values[0], list)) else [values]
    colors = ["#4C72B0", "#C44E52", "#55A868"]
    for i, ser in enumerate(series):
        vals = ser + ser[:1]
        ax.plot(angles, vals, color=colors[i % len(colors)], lw=2,
                label=a.get("labels", [f"系列{i+1}"])[i] if "labels" in a else f"系列{i+1}")
        ax.fill(angles, vals, color=colors[i % len(colors)], alpha=0.15)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(cats, fontsize=10)
    ax.set_title(a.get("title", "雷达图"), pad=20)
    if len(series) > 1:
        ax.legend(frameon=False, fontsize=9, loc="upper right", bbox_to_anchor=(1.2, 1.1))
    return _apa_style(fig)


def 热图(a):
    fig, ax = plt.subplots(figsize=(6.0, 5.0))
    matrix = a.get("matrix", [])
    xlabels = a.get("xlabels", [])
    ylabels = a.get("ylabels", [])
    im = ax.imshow(matrix, cmap="YlGnBu", aspect="auto")
    ax.set_xticks(range(len(xlabels)))
    ax.set_xticklabels(xlabels, rotation=45, ha="right")
    ax.set_yticks(range(len(ylabels)))
    ax.set_yticklabels(ylabels)
    for i in range(len(matrix)):
        for j in range(len(matrix[i])):
            ax.text(j, i, f"{matrix[i][j]:.2f}", ha="center", va="center",
                    color="white" if matrix[i][j] > 0.5 else "black", fontsize=8)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    ax.set_title(a.get("title", "热图（相关性矩阵）"))
    return _apa_style(fig)


def 折线图(a):
    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    x = a.get("x", [])
    y = a.get("y", [])
    labels = a.get("labels", [])
    series = y if (y and isinstance(y[0], list)) else [y]
    colors = ["#4C72B0", "#C44E52", "#55A868", "#8172B3"]
    for i, ser in enumerate(series):
        ax.plot(x, ser, marker="o", lw=2, color=colors[i % len(colors)],
                label=labels[i] if i < len(labels) else f"系列{i+1}")
    if labels:
        ax.legend(frameon=False, fontsize=9)
    ax.set_title(a.get("title", "折线图"))
    ax.set_xlabel(a.get("xlabel", ""))
    ax.set_ylabel(a.get("ylabel", ""))
    return _apa_style(fig)


# ───────────────────────────────────────────────────────────────
#  路由表
# ───────────────────────────────────────────────────────────────
CHART_MAP = {
    "条形图": 条形图,
    "饼图": 饼图,
    "直方图": 直方图,
    "箱线图": 箱线图,
    "散点图": 散点图,
    "简单斜率图": 简单斜率图,
    "雷达图": 雷达图,
    "热图": 热图,
    "折线图": 折线图,
}


def _print_types():
    print("支持的图表类型（9 种）：")
    for k in CHART_MAP:
        print(f"  - {k}")


def main(argv=None):
    if not _MATPLOTLIB_OK:  # pragma: no cover
        sys.stderr.write(
            "[chart_engine] 错误：未安装可选依赖 matplotlib/seaborn/numpy/scipy。\n"
            "  如需生成图表，请运行：pip install matplotlib seaborn numpy scipy\n"
            "  （未安装时技能包其余功能不受影响。）\n"
        )
        return 2

    _setup_cjk_font()

    parser = argparse.ArgumentParser(description="管理学论文图表引擎")
    parser.add_argument("type", nargs="?", help="图表类型，见 --list")
    parser.add_argument("json", nargs="?", help="JSON 参数字符串")
    parser.add_argument("--output", "-o", default="./产出/", help="输出目录")
    parser.add_argument("--name", "-n", default=None, help="文件名（不含扩展名），默认取类型名")
    parser.add_argument("--list", action="store_true", help="列出支持的图表类型")
    args = parser.parse_args(argv)

    if args.list or not args.type:
        _print_types()
        return 0

    if args.type not in CHART_MAP:
        sys.stderr.write(f"[chart_engine] 未知类型：{args.type}\n")
        _print_types()
        return 2

    try:
        params = json.loads(args.json) if args.json else {}
    except json.JSONDecodeError as e:
        sys.stderr.write(f"[chart_engine] JSON 解析失败：{e}\n")
        return 2

    fig = CHART_MAP[args.type](params)
    name = args.name or args.type
    files = _save(fig, name, args.output)
    plt.close(fig)
    print(f"[chart_engine] 已生成：{', '.join(files)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
