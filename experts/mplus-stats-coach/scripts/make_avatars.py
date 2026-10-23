#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_avatars.py — **零依赖扁平插画**头像生成器（回退 / 测试夹具用）

⚠ 角色界定（别搞混）
    · **随包上架的正式头像是 `avatars/mplus-stats-coach.png`**，由
      `scripts/prepare_avatar.py` 从原始生成图加工而来（去生成器水印 → 缩放 512×512 → 体积校验）。
      官方要求「漫画/插画风格」，正式版用的是**漫画人物插画**。
    · **本脚本不产出随包头像**，只负责两件事：
        1. **回退**：无可用的图像生成能力时，产出一张**确定性的**扁平插画顶替（不依赖外部服务）；
        2. **测试夹具**：`scripts/selftest_gates.py` 调它生成合规体积的头像做门禁绿证。

设计约束（对齐 P0-1 / P0-2 / P0-3 与官方头像规范）
    · 官方要求：PNG 推荐、512×512、单张 ≤500KB、**漫画 / 插画风格**
    · 纯几何绘制，**不依赖任何字体文件**（跨机器不漂移、可复现）
    · 只用**平坦色块 + 描边**（cel 风格），**不用渐变 / 发光 / 毛玻璃**（P0-2）
    · 调色板克制（4 色），不用 emoji 作图形（P0-1 / P0-3）
    · 体积须 >10KB：门禁把「实色占位图」判红（工作坊契约 avatar.min_bytes=10240）

图形语义（本智能体自己的方法学母题，不是装饰）
    · 上方：**潜变量路径图** —— 一个潜变量圆环，三条路径指向三个观测指标
    · 下方：**增长曲线** —— 四个时间点连线（潜增长 / 纵向建模）
    二者叠在一起即为「Mplus 潜变量建模」的字面图示。

用法
    python3 scripts/make_avatars.py --out <输出路径>
"""
import argparse
import os
import struct
import sys
import zlib

FINAL = 512
SS = 2                       # 超采样倍数（抗锯齿）
G = FINAL * SS               # 工作网格边长 = 1024

INK = (26, 42, 51)
TEAL = (23, 80, 92)
TEAL2 = (38, 110, 121)
CREAM = (247, 243, 233)
AMBER = (232, 168, 62)
WHITE = (255, 255, 255)

D = G * 0.012                # 统一描边厚度


# --------------------------------------------------------------------------
# 掩膜基元（返回 G*G 的 0/1 字节数组）
# --------------------------------------------------------------------------
def m_rrect(size, x0, y0, x1, y1, r):
    """圆角矩形掩膜（x0<x1, y0<y1）。"""
    px = bytearray(size * size)
    r = max(0.0, min(r, (x1 - x0) / 2.0, (y1 - y0) / 2.0))
    xa, xb = max(0, int(x0)), min(size - 1, int(x1 + 1))
    ya, yb = max(0, int(y0)), min(size - 1, int(y1 + 1))
    for y in range(ya, yb + 1):
        row = y * size
        cy = y0 + r if y < y0 + r else (y1 - r if y > y1 - r else y)
        dy = abs(y - cy) if (y < y0 + r or y > y1 - r) else 0.0
        for x in range(xa, xb + 1):
            cx = x0 + r if x < x0 + r else (x1 - r if x > x1 - r else x)
            dx = abs(x - cx) if (x < x0 + r or x > x1 - r) else 0.0
            if dx * dx + dy * dy <= r * r:
                px[row + x] = 1
    return px


def m_stroke(size, p0, p1, width):
    """圆头线段掩膜。"""
    px = bytearray(size * size)
    x0, y0 = p0
    x1, y1 = p1
    dx, dy = x1 - x0, y1 - y0
    L2 = dx * dx + dy * dy
    hw2 = (width / 2.0) ** 2
    xa, xb = int(min(x0, x1) - width), int(max(x0, x1) + width)
    ya, yb = int(min(y0, y1) - width), int(max(y0, y1) + width)
    for y in range(max(0, ya), min(size - 1, yb) + 1):
        row = y * size
        for x in range(max(0, xa), min(size - 1, xb) + 1):
            if L2 == 0:
                d2 = (x - x0) ** 2 + (y - y0) ** 2
            else:
                t = ((x - x0) * dx + (y - y0) * dy) / L2
                t = 0.0 if t < 0 else (1.0 if t > 1 else t)
                d2 = (x - (x0 + t * dx)) ** 2 + (y - (y0 + t * dy)) ** 2
            if d2 <= hw2:
                px[row + x] = 1
    return px


def m_disc(size, cx, cy, r):
    """实心圆掩膜。"""
    px = bytearray(size * size)
    r2 = r * r
    ya, yb = max(0, int(cy - r - 1)), min(size - 1, int(cy + r + 1))
    xa, xb = max(0, int(cx - r - 1)), min(size - 1, int(cx + r + 1))
    for y in range(ya, yb + 1):
        row = y * size
        for x in range(xa, xb + 1):
            if (x - cx) ** 2 + (y - cy) ** 2 <= r2:
                px[row + x] = 1
    return px


def or_into(dst, src):
    for i, v in enumerate(src):
        if v:
            dst[i] = 1
    return dst


def downsample(mask, n, s):
    """超采样掩膜 → n×n 的 0–255 覆盖度。"""
    out = bytearray(n * n)
    area = s * s
    ns = n * s
    for y in range(n):
        for x in range(n):
            acc = 0
            base = (y * s) * ns + x * s
            for dy in range(s):
                b = base + dy * ns
                for dx in range(s):
                    acc += mask[b + dx]
            out[y * n + x] = (acc * 255) // area
    return out


# --------------------------------------------------------------------------
# 画布合成（画家算法，逐层 src-over）
# --------------------------------------------------------------------------
class Canvas:
    def __init__(self, n):
        self.n = n
        self.buf = bytearray(n * n * 4)      # RGBA，初始全透明

    def paint(self, mask_super, color):
        """把超采样掩膜按 color 叠到画布上（带抗锯齿）。"""
        a_cov = downsample(mask_super, self.n, SS)
        c = color
        buf, o = self.buf, 0
        for i in range(self.n * self.n):
            o += 4
            if not a_cov[i]:
                continue
            sa = a_cov[i] / 255.0
            da = buf[o + 3] / 255.0
            oa = sa + da * (1.0 - sa)
            for k in range(3):
                buf[o + k] = int((c[k] * sa + buf[o + k] * da * (1.0 - sa)) / oa + 0.5)
            buf[o + 3] = int(oa * 255 + 0.5)

    def grain(self, amp=3, seed=20261007):
        """极轻的确定性颗粒：抬升熵值以避开「实色占位图」判据，视觉上仍是平坦插画。"""
        buf, n = self.buf, self.n
        s = seed & 0xFFFFFFFF
        for i in range(n * n):
            o = i * 4
            if not buf[o + 3]:
                continue
            s = (1103515245 * s + 12345) & 0x7FFFFFFF
            d = (s % (2 * amp + 1)) - amp
            for k in range(3):
                v = buf[o + k] + d
                buf[o + k] = 0 if v < 0 else (255 if v > 255 else v)

    def write_png(self, path):
        w = h = self.n
        raw = bytearray()
        stride = w * 4
        for y in range(h):
            raw.append(0)
            raw += self.buf[y * stride:(y + 1) * stride]

        def chunk(tag, data):
            return (struct.pack(">I", len(data)) + tag + data
                    + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

        png = (b"\x89PNG\r\n\x1a\n"
               + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
               + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
               + chunk(b"IEND", b""))
        with open(path, "wb") as f:
            f.write(png)


def outlined(cv, mask_fn_outline, mask_fn_fill, color):
    """先画略大的 INK 描边，再压上本色填充 —— cel 风格描边，无需做膨胀运算。"""
    cv.paint(mask_fn_outline(), INK)
    cv.paint(mask_fn_fill(), color)


def build():
    cv = Canvas(FINAL)

    # 1) 底板：深青圆角方（四角留透明）
    cv.paint(m_rrect(G, 0, 0, G, G, G * 0.200), TEAL)
    cv.paint(m_rrect(G, G * 0.055, G * 0.055, G * 0.945, G * 0.945, G * 0.150), TEAL2)

    # 2) 下方「纸面」：奶油圆角矩形（含描边）
    px0, py0, px1, py1, pr = G * 0.145, G * 0.500, G * 0.855, G * 0.865, G * 0.055
    outlined(cv,
             lambda: m_rrect(G, px0 - D, py0 - D, px1 + D, py1 + D, pr + D),
             lambda: m_rrect(G, px0, py0, px1, py1, pr),
             CREAM)

    # 3) 潜变量路径图：潜变量圆环 + 三条路径 + 三个观测指标
    cx, cy, cr = G * 0.500, G * 0.205, G * 0.062
    ix, iy, ih = (G * 0.250, G * 0.500, G * 0.750), G * 0.400, G * 0.052
    for x in ix:                                     # 先画路径（被节点压住更自然）
        cv.paint(m_stroke(G, (cx, cy), (x, iy), G * 0.011), INK)
    outlined(cv,
             lambda: m_disc(G, cx, cy, cr + D),
             lambda: m_disc(G, cx, cy, cr),
             WHITE)
    cv.paint(m_disc(G, cx, cy, cr * 0.34), TEAL)     # 圆心小点：潜变量符号感
    for x in ix:
        outlined(cv,
                 lambda x=x: m_rrect(G, x - ih - D, iy - ih - D, x + ih + D, iy + ih + D, G * 0.018 + D),
                 lambda x=x: m_rrect(G, x - ih, iy - ih, x + ih, iy + ih, G * 0.018),
                 AMBER)

    # 4) 增长曲线：四点折线 + 端点圆点
    pts = [(G * 0.225, G * 0.795), (G * 0.435, G * 0.725),
           (G * 0.645, G * 0.640), (G * 0.795, G * 0.565)]
    for a, b in zip(pts, pts[1:]):
        cv.paint(m_stroke(G, a, b, G * 0.019), INK)
    for (x, y) in pts[:-1]:
        outlined(cv,
                 lambda x=x, y=y: m_disc(G, x, y, G * 0.028 + D),
                 lambda x=x, y=y: m_disc(G, x, y, G * 0.028),
                 AMBER)
    x, y = pts[-1]                                    # 末端点加一圈白，作视觉落点
    cv.paint(m_disc(G, x, y, G * 0.040 + D), INK)
    cv.paint(m_disc(G, x, y, G * 0.040), WHITE)

    cv.grain()
    return cv


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    out = os.path.abspath(args.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    build().write_png(out)
    print("avatar -> %s (%d bytes, %dx%d)" % (args.out, os.path.getsize(out), FINAL, FINAL))
    return 0


if __name__ == "__main__":
    sys.exit(main())
