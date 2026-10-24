#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
render_selection_svg.py — 自绘「方法选型决策路径图」（M4 的可视化底图）

为什么自绘
    官方手册里的方法选型内容**不提供**可复用的路径图（且官方 PDF 判 `INDEX_ONLY`，不得收录原文）。
    故本图**由本包自己绘制**：内容取自 `skills/mplus-method-advisor/references/41-selection-tree.md`
    的实测结论（Tier 分层、六条分流、三道输出闸、硬否定场景），**不引任何第三方图**。

视觉纪律（对齐 P0-1 / P0-2 / P0-3）
    · 只用**平涂色块 + 描边**，**无渐变 / 无发光 / 无毛玻璃**
    · 调色板克制（5 色），**不用 emoji**，图形语义与文字一致
    · 纯标准库生成（字符串拼 SVG），**零第三方依赖**、可复现

用法
    python3 scripts/render_selection_svg.py --out skills/mplus-method-advisor/templates/selection-path.svg
"""
import argparse
import os
import sys
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape as _xesc

W, H = 1120, 664

PAGE = "rgb(247,243,233)"     # 奶油底
INK = "rgb(26,42,51)"         # 墨色描边与主文字
TEAL = "rgb(23,80,92)"        # 深青（主色）
TEAL2 = "rgb(38,110,121)"     # 次青
AMBER = "rgb(232,168,62)"     # 琥珀（强调）
WHITE = "rgb(255,255,255)"
MUTED = "rgb(96,116,122)"

FONT = ("PingFang SC, Hiragino Sans GB, Microsoft YaHei, Noto Sans CJK SC, "
        "Source Han Sans SC, sans-serif")

S = []                        # SVG 片段
TEXTS = []                    # 版式断言用：每条文字的估算包围盒


def _est_w(s, size):
    """估算文字宽度：CJK / 全角按 1.0 em，常见符号 0.9 em，其余 0.56 em。

    仅为**版式自检**服务（判断溢出与重叠），不追求与渲染器逐像素一致，
    故按偏保守取值 —— 宁可多报，也不放过真实的压字。
    """
    w = 0.0
    for ch in s:
        o = ord(ch)
        if o > 0x2E80 and o not in (0x3001, 0x3002):      # CJK / 全角
            w += 1.0
        elif ch in "·—→←×≈≤≥":
            w += 0.9
        else:
            w += 0.56
    return w * size


def esc(s):
    """XML 转义。**必须**用于所有文本与属性值。

    ⚠ 实测踩过（几何断言查不出的真 bug）：正文里的「纵向波数 < 3」含裸 `<`，
      会让整个 SVG **不是合法 XML** → 渲染器直接报错或空白。
      故此处统一转义，并在 `xml_check()` 里把「合法性」变成每次生成的必过断言。
    """
    return _xesc(str(s))


def rect(x, y, w, h, r=8, fill=WHITE, stroke=INK, sw=1.6):
    S.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="%.1f" '
             'fill="%s" stroke="%s" stroke-width="%.1f"/>'
             % (x, y, w, h, r, esc(fill), esc(stroke), sw))


def text(x, y, s, size=13, fill=INK, weight="normal", anchor="start", op=1.0):
    S.append('<text x="%.1f" y="%.1f" font-family="%s" font-size="%.1f" fill="%s" '
             'font-weight="%s" text-anchor="%s" opacity="%.2f">%s</text>'
             % (x, y, esc(FONT), size, esc(fill), weight, anchor, op, esc(s)))
    w = _est_w(s, size)
    x0 = x if anchor == "start" else (x - w if anchor == "end" else x - w / 2.0)
    TEXTS.append({"s": s, "x0": x0, "x1": x0 + w, "y0": y - size * 0.82, "y1": y + size * 0.26})


def line(x1, y1, x2, y2, stroke=INK, sw=1.6, dash=None):
    d = ' stroke-dasharray="%s"' % esc(dash) if dash else ""
    S.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" '
             'stroke-width="%.1f"%s/>' % (x1, y1, x2, y2, esc(stroke), sw, d))


def arrow(x1, y1, x2, y2, stroke=INK, sw=1.6):
    """直线 + 末端实心三角箭头（自己画三角，不依赖 <marker>，避免渲染器差异）。"""
    line(x1, y1, x2, y2, stroke, sw)
    a = 7.0
    S.append('<path d="M %.1f %.1f L %.1f %.1f L %.1f %.1f Z" fill="%s"/>'
             % (x2, y2, x2 - a, y2 - a * 0.62, x2 - a, y2 + a * 0.62, esc(stroke)))


def build():
    del S[:]                  # 幂等：重复调用不累加（自测会调多次）
    del TEXTS[:]
    S.append('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
             'viewBox="0 0 %d %d" role="img" '
             'aria-label="Mplus 方法选型决策路径图">' % (W, H, W, H))
    S.append('<title>Mplus 方法选型决策路径</title>')
    rect(0, 0, W, H, 0, PAGE, PAGE, 0)

    # ---------- 标题 ----------
    text(36, 44, "Mplus 方法选型决策路径", 22, TEAL, "bold")
    text(36, 68, "先用四类信息定位研究对象，再按问题 × 结构分流，最后过三道输出闸 —— 单次最多 3 个候选",
         12.5, MUTED)

    # ---------- 阶段一：四类必问信息 ----------
    x1, w1 = 36, 250
    rect(x1, 96, w1, 336, 12, WHITE, TEAL, 2)
    text(x1 + 16, 122, "① 四类必问信息", 14.5, TEAL, "bold")
    text(x1 + 16, 140, "缺一不可", 11.5, AMBER, "bold")
    rows1 = [("研究问题", "估关系 / 分类型 / 建轨迹 / 验机制"),
             ("数据结构", "横断 or 纵向（几波）；是否嵌套"),
             ("样本量", "总 N；嵌套另给簇数（更关键）"),
             ("测量尺度", "连续 / 二分 / 有序 / 计数 / 名义")]
    y = 152
    for name, desc in rows1:
        rect(x1 + 14, y, w1 - 28, 52, 7, PAGE, INK, 1.2)
        text(x1 + 26, y + 21, name, 12.5, TEAL, "bold")
        text(x1 + 26, y + 39, desc, 10.2, INK)
        y += 60
    text(x1 + 16, 420, "信息不全 → 先问｜不得用「常见做法」补全", 10.8, MUTED, "bold")

    # ---------- 阶段二：分流 ----------
    x2, w2 = 320, 470
    rect(x2, 96, w2, 336, 12, WHITE, TEAL, 2)
    text(x2 + 16, 122, "② 按 问题 × 结构 分流", 14.5, TEAL, "bold")
    text(x2 + 16, 140, "Tier = 带结果的官方可对照示例数", 11, MUTED)
    rows2 = [
        ("横断 · 连续指标潜变量", "CFA / SEM / 路径分析　Tier A（113 例）"),
        ("横断 · 指标为分类变量", "LCA / LPA　Tier A·B（25 / 24 例）"),
        ("横断 · 检验中介机制", "MODEL INDIRECT / MODEL CONSTRAINT　Tier D（仅 2 例）"),
        ("纵向 · 轨迹或状态转移", "LGCM / GMM / LCGA / LTA　Tier B（17 / 16 例）"),
        ("嵌套（簇 / 层）· 簇数够", "多层 / 多层 SEM / 多层混合　Tier A·B（75 / 32 / 14）"),
        ("小样本 / 缺失 / 生存 / 交互", "贝叶斯 · FIML · 生存分析 · XWITH　C–D 居多"),
    ]
    y = 156
    for cond, meth in rows2:
        rect(x2 + 14, y, w2 - 28, 44, 7, PAGE, INK, 1.2)
        text(x2 + 26, y + 18, cond, 11.6, TEAL, "bold")
        text(x2 + 26, y + 35, meth, 10.6, INK)
        y += 48

    # ---------- 阶段三：三道输出闸 ----------
    x3, w3 = 824, 260
    rect(x3, 96, w3, 336, 12, WHITE, TEAL, 2)
    text(x3 + 16, 122, "③ 三道输出闸", 14.5, TEAL, "bold")
    text(x3 + 16, 140, "任一道不过 → 不出结论", 11, MUTED)
    gates = [("闸 1 · 前提检查", "不满足 → 明写「不建议做 X」"),
             ("闸 2 · 参照精度", "Tier C / D → 附降级声明 + 全部样本 ID"),
             ("闸 3 · 固定五段", "候选 / 理由 / 前提 / 实例 / 否定")]
    y = 158
    for name, desc in gates:
        rect(x3 + 14, y, w3 - 28, 76, 8, PAGE, TEAL2, 1.6)
        text(x3 + 26, y + 26, name, 12.5, TEAL2, "bold")
        text(x3 + 26, y + 48, desc, 10.6, INK)
        y += 84
    text(x3 + 16, 420, "单次最多 3 个候选", 10.8, INK, "bold")

    # ---------- 阶段间箭头 ----------
    arrow(x1 + w1 + 4, 264, x2 - 6, 264)
    arrow(x2 + w2 + 4, 264, x3 - 6, 264)

    # ---------- 底部：硬否定场景 ----------
    rect(36, 456, W - 72, 118, 12, WHITE, AMBER, 2)
    text(52, 484, "必须先给否定建议的三种情形", 14, INK, "bold")
    items = [("簇数只有个位数", "不建议做多层模型 —— 方差成分估计不可靠"),
             ("纵向波数 < 3", "不建议做潜增长；改横断设计或换问题"),
             ("「帮我跑一下看拟合」", "拒绝：本包不运行 Mplus，只给语法骨架与静态检查")]
    y = 500
    for a, b in items:
        text(52, y + 20, "·", 15, AMBER, "bold")
        text(70, y + 20, a, 11.6, TEAL, "bold")
        text(266, y + 20, b, 11, INK)
        y += 26

    text(36, 598, "口径与实测数字见 references/capability-boundary.md（冲突时以它为准）；"
                  "分流依据见 41-selection-tree.md。", 11, MUTED)
    text(36, 618, "本图由 scripts/render_selection_svg.py 自绘生成，不含任何第三方图源；"
                  "生成时自带版式断言（越界 / 压字）。", 11, MUTED)
    text(36, 640, "验证状态：STATIC_CHECKED（本包不运行 Mplus）", 11, TEAL, "bold")

    S.append("</svg>")
    return "\n".join(S) + "\n"


def layout_check():
    """版式自检：① 越出画布 ② 两段文字压字。返回问题列表。

    这类约束写成断言而不是文档 —— 否则每改一次图都要靠肉眼重看一遍。
    """
    bad = []
    for t in TEXTS:
        if t["x0"] < -0.5 or t["x1"] > W + 0.5 or t["y0"] < 0 or t["y1"] > H:
            bad.append("越界：%r  x=[%.0f,%.0f] y=[%.0f,%.0f]"
                       % (t["s"][:26], t["x0"], t["x1"], t["y0"], t["y1"]))
    for i in range(len(TEXTS)):
        for j in range(i + 1, len(TEXTS)):
            a, b = TEXTS[i], TEXTS[j]
            ox = min(a["x1"], b["x1"]) - max(a["x0"], b["x0"])
            oy = min(a["y1"], b["y1"]) - max(a["y0"], b["y0"])
            if ox > 1.0 and oy > 1.0:
                bad.append("压字：%r <-> %r（重叠 %.0fx%.0f）"
                           % (a["s"][:22], b["s"][:22], ox, oy))
    return bad


def xml_check(svg):
    """断言产物是**合法 XML** —— 否则渲染器会报错或渲染空白。返回问题列表。

    这条断言是实测补上的：正文里的裸 `<`（如「波数 < 3」）不会被几何断言发现，
    但会让整个 SVG 报废。故每次生成都必须过。
    """
    try:
        ET.fromstring(svg)
        return []
    except ET.ParseError as e:
        return ["SVG 不是合法 XML：%s" % e]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--no-check", action="store_true", help="跳过版式/XML 自检（仅调试用）")
    args = ap.parse_args()
    out = os.path.abspath(args.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    svg = build()

    if not args.no_check:
        bad = layout_check() + xml_check(svg)
        if bad:
            print("[FAIL] 自检未通过（%d 项）：" % len(bad))
            for b in bad:
                print("   -", b)
            return 1
        print("[OK] 版式自检通过：%d 条文字无越界、无压字" % len(TEXTS))
        print("[OK] XML 自检通过：产物为合法 XML")

    with open(out, "w", encoding="utf-8") as f:
        f.write(svg)
    print("[OK] svg -> %s (%d bytes, %d chars)" % (args.out, os.path.getsize(out), len(svg)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
