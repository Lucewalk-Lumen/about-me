#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
prepare_avatar.py — 把「原始生成图」加工成**合规头像**（包内可复现的资产准备步骤）

为什么单独一步
    官方头像规范：PNG（推荐）· **512×512 px（正方形）** · **单张 ≤500KB** · **漫画/插画风格**、专业自然。
    原始生成图是 1024×1024 且**右下角带生成器水印**，两者都不能直接上架。
    故本脚本把「去水印 → 缩放到 512×512 → 体积校验」固化成可复跑的步骤，
    使最终头像的来历可追溯，而不是靠手工修图。

去水印原理（**不是**模糊／涂抹）
    水印是**半透明浅色叠字**，落在画面右下角一片**平坦底色**上（背景亮度约 70、水印约 150–175）。
    故按**行**处理：在每行水印区的左右各找**最近的一个干净像素**作锚点，区间内做**线性插值**填充。
    平坦或缓变底色下插值结果与真实背景无可见接缝；不使用任何涂抹／中值滤波，避免糊掉细节。

依赖
    Pillow（仅本资产准备脚本使用；包内运行期脚本仍为零依赖）

用法
    python3 scripts/prepare_avatar.py --src <原始生成图> --out avatars/mplus-stats-coach.png
"""
import argparse
import os
import sys

SIZE = 512
MIN_BYTES = 10240          # 与 verify.py A7 一致：低于此判为占位实色图
MAX_BYTES = 512000         # 官方：单张不超过 500KB
COMFORT_BYTES = 380000     # 超过此值就做调色板量化，给自己留出余量（不要贴着 500KB 上限）
PALETTE_COLORS = 256       # 赛璐璐平涂插画量化到 256 色无可见损失（实测 389KB -> 204KB）
WATERMARK_LUM_MIN = 118    # 判定「疑似水印」的亮度下界（实测背景 ≈70，水印 ≈150–175）
SEARCH_RIGHT = 0.78        # 只在右下角此比例之外搜索水印
SEARCH_BOTTOM = 0.86


def _lum(c):
    return (c[0] * 299 + c[1] * 587 + c[2] * 114) // 1000


def find_watermark(px, W, H):
    """返回右下角疑似水印的包围盒；找不到返回 None。"""
    minx, miny, maxx, maxy = W, H, -1, -1
    for y in range(int(H * SEARCH_BOTTOM), H):
        for x in range(int(W * SEARCH_RIGHT), W):
            if _lum(px[x, y]) > WATERMARK_LUM_MIN:
                if x < minx:
                    minx = x
                if x > maxx:
                    maxx = x
                if y < miny:
                    miny = y
                if y > maxy:
                    maxy = y
    if maxx < 0:
        return None
    return (minx, miny, maxx, maxy)


def erase(px, W, H, box, pad=5):
    """按行左右干净锚点线性插值填充水印区。"""
    x0, y0, x1, y1 = box
    x0, y0 = max(0, x0 - pad), max(0, y0 - pad)
    x1, y1 = min(W - 1, x1 + pad), min(H - 1, y1 + pad)
    for y in range(y0, y1 + 1):
        xl = None
        for x in range(x0 - 1, -1, -1):                    # 向左找干净锚点
            if _lum(px[x, y]) <= WATERMARK_LUM_MIN:
                xl = x
                break
        xr = None
        for x in range(x1 + 1, W):                         # 向右找干净锚点
            if _lum(px[x, y]) <= WATERMARK_LUM_MIN:
                xr = x
                break
        if xl is None and xr is None:
            continue
        cL = px[xl, y] if xl is not None else px[xr, y]
        cR = px[xr, y] if xr is not None else px[xl, y]
        span = (xr if xr is not None else xl) - (xl if xl is not None else xr)
        for x in range(x0, x1 + 1):
            if span > 0:
                t = (x - xl) / float(span)
                t = 0.0 if t < 0 else (1.0 if t > 1 else t)
            else:
                t = 0.0
            px[x, y] = tuple(int(cL[k] + (cR[k] - cL[k]) * t + 0.5) for k in range(3))
    return (x0, y0, x1, y1)


def main():
    ap = argparse.ArgumentParser(
        prog="prepare_avatar.py",
        description="原始生成图 -> 合规头像：去生成器水印 + 缩放 512x512 + 体积校验。",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", required=True, help="原始生成图（PNG/JPG）")
    ap.add_argument("--out", required=True, help="输出头像路径（建议 avatars/<name>.png）")
    ap.add_argument("--no-erase", action="store_true", help="跳过去水印（源图本就无水印时用）")
    args = ap.parse_args()

    try:
        from PIL import Image
    except ImportError:
        print("[FAIL] 需要 Pillow：pip install Pillow")
        return 2

    src = os.path.abspath(args.src)
    if not os.path.exists(src):
        print("[FAIL] 源图不存在：%s" % src)
        return 2

    im = Image.open(src).convert("RGB")
    W, H = im.size
    print("[OK] 读入 %s（%dx%d）" % (os.path.basename(src), W, H))

    if not args.no_erase:
        px = im.load()
        box = find_watermark(px, W, H)
        if box is None:
            print("[WARN] 右下角未检出疑似水印 —— 原样继续（请人工确认）")
        else:
            filled = erase(px, W, H, box)
            print("[OK] 水印区 %s -> 已按行插值填充为 %s" % (box, filled))

    out_im = im.resize((SIZE, SIZE), Image.LANCZOS)
    out = os.path.abspath(args.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    out_im.save(out, "PNG", optimize=True)
    raw_bytes = os.path.getsize(out)
    print("[OK] 先出真彩 PNG：%d 字节" % raw_bytes)

    # 贴上 500KB 上限时给自己留余量：赛璐璐平涂插画量化到 256 色观感无损（实测已验证）
    if raw_bytes > COMFORT_BYTES:
        q = out_im.quantize(colors=PALETTE_COLORS, method=Image.MEDIANCUT, dither=Image.NONE)
        q.save(out, "PNG", optimize=True)
        print("[OK] 超 %d 字节 -> 已量化至 %d 色：%d -> %d 字节"
              % (COMFORT_BYTES, PALETTE_COLORS, raw_bytes, os.path.getsize(out)))

    nb = os.path.getsize(out)
    ok = MIN_BYTES <= nb <= MAX_BYTES
    print("[%s] 输出 %s：%dx%d，%d 字节（要求 %d–%d）"
          % ("OK" if ok else "FAIL", args.out, SIZE, SIZE, nb, MIN_BYTES, MAX_BYTES))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
