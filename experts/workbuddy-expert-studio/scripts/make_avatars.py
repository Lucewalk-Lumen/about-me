#!/usr/bin/env python3
"""make_avatars.py — 生成**占位**头像（零第三方依赖，仅标准库 zlib/struct）。

用途：开发新包时快速产出 512×512 占位头像（扁平实色 + 白色环形 + 角色字母），
让流水线先跑通；符合 P0-1（禁 emoji 图标）与 P0-2（禁渐变 / 发光 / 毛玻璃）。

[注意] 平台头像规范要求「风格统一的**漫画 / 插画风格**，专业自然」——占位图形**不满足**该风格要求。
正式交付前必须替换为插画风格头像（本团自身头像即为插画风格），再跑打包前门禁复核尺寸与体积。

护栏（R4，防误覆盖正式头像）：
  - 默认输出到占位目录 `avatars/_placeholder/`，**绝不**默认写 `avatars/`；
  - 仅当显式 `--out avatars/` **且** `--force` 才允许写入正式目录；
  - 覆盖前若目标文件 > 50KB（视为插画风格正式图，非占位图），需再给一次 `--force`（即两次）。

用法：
  python3 scripts/make_avatars.py                       # 生成到 avatars/_placeholder/
  python3 scripts/make_avatars.py --out avatars/ --force        # 显式覆盖正式目录
  python3 scripts/make_avatars.py -h                    # 帮助
"""
import argparse
import os
import struct
import zlib

SIZE = 512
PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OFFICIAL_DIR = os.path.join(PKG, "avatars")
DEFAULT_OUT = os.path.join(PKG, "avatars", "_placeholder")
# 目标文件体积 > 50KB 视为非占位图（正式插画头像），覆盖需二次 --force
NON_PLACEHOLDER_MIN_BYTES = 50 * 1024

# role -> (背景实色 RGB, 字母)
ROLES = {
    "team": ((37, 56, 88), "A"),
    "team-lead": ((30, 41, 59), "Q"),
    "agent-diagnostician": ((15, 118, 110), "S"),
    "agent-architect": ((37, 99, 165), "G"),
    "agent-engineer": ((124, 58, 173), "K"),
    "agent-auditor": ((194, 65, 12), "Y"),
    "agent-packager": ((21, 128, 61), "B"),
    "agent-release-chronicler": ((161, 98, 7), "H"),
}

FONT = {
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "B": ["11110", "10001", "10001", "11110", "10001", "10001", "11110"],
    "G": ["01110", "10001", "10000", "10111", "10001", "10001", "01110"],
    "H": ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
    "K": ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
    "Q": ["01110", "10001", "10001", "10001", "10101", "10010", "01101"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "Y": ["10001", "10001", "01010", "00100", "00100", "00100", "00100"],
}


def chunk(typ, data):
    return struct.pack(">I", len(data)) + typ + data + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)


def make_png(path, bg, letter, size=SIZE):
    k = size / float(SIZE)
    s = max(6, int(round(46 * k)))
    gw, gh = 5 * s, 7 * s
    ox, oy = (size - gw) // 2, (size - gh) // 2
    ring_r = 200 * k
    ring_w = max(1.0, 5 * k)
    glyph = FONT[letter]
    rows = []
    for y in range(size):
        row = bytearray([0])  # filter type 0
        dy = y - size // 2
        for x in range(size):
            r, g, b = bg
            # 白色环形
            dist = ((x - size // 2) ** 2 + dy ** 2) ** 0.5
            if abs(dist - ring_r) < ring_w:
                r, g, b = (255, 255, 255)
            # 字母（覆盖在环上）
            if ox <= x < ox + gw and oy <= y < oy + gh:
                cx, cy = (x - ox) // s, (y - oy) // s
                if glyph[cy][cx] == "1":
                    r, g, b = (255, 255, 255)
            row += bytes((r, g, b))
        rows.append(bytes(row))
    raw = b"".join(rows)
    comp = zlib.compress(raw, 9)
    png = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)
    png += chunk(b"IHDR", ihdr) + chunk(b"IDAT", comp) + chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)


def build_parser():
    ap = argparse.ArgumentParser(
        prog="make_avatars.py",
        description="生成 512×512 占位头像（扁平实色 + 白环 + 角色字母）。默认写入 avatars/_placeholder/。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="护栏：默认绝不写 avatars/；仅 `--out avatars/ --force` 才可；覆盖 >50KB 的非占位图需两次 --force。")
    ap.add_argument("--out", default=None,
                    help="输出目录（默认 %s）" % os.path.relpath(DEFAULT_OUT, PKG))
    ap.add_argument("--force", action="count", default=0,
                    help="允许覆盖正式头像目录；对已存在的 >50KB 非占位图需给出两次")
    ap.add_argument("--size", type=int, default=SIZE, help="边长像素（默认 512）")
    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)
    out = os.path.abspath(args.out) if args.out else DEFAULT_OUT
    official = os.path.abspath(OFFICIAL_DIR)
    out_is_official = (out == official)

    if out_is_official and args.force == 0:
        print("[FAIL] make_avatars: 拒绝写入正式头像目录 avatars/ —— 需显式 `--out avatars/ --force`。")
        print("       默认输出占位目录 avatars/_placeholder/，避免误覆盖正式插画头像。")
        return 2

    os.makedirs(out, exist_ok=True)
    blocked = []
    for name, (bg, ch) in ROLES.items():
        fp = os.path.join(out, name + ".png")
        if os.path.exists(fp) and os.path.getsize(fp) > NON_PLACEHOLDER_MIN_BYTES and args.force < 2:
            blocked.append(fp)
            print(f"[WARN] 跳过 {fp}（{os.path.getsize(fp)}B > 50KB，疑似正式插画图；如确要覆盖请再加一次 --force）")
            continue
        make_png(fp, bg, ch, args.size)
        print(f"[OK] 生成占位头像: {fp} ({os.path.getsize(fp)} bytes)")

    if blocked:
        print(f"[FAIL] {len(blocked)} 个疑似正式头像未被覆盖（>50KB，需两次 --force 确认）")
        return 2
    if out_is_official:
        print("[WARN] 已写入正式头像目录 avatars/ —— 请确认随后替换为插画风格头像并重跑门禁。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
