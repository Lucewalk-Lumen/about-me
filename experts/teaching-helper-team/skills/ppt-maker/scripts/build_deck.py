#!/usr/bin/env python3
"""build_deck.py - deterministic single-file HTML slide deck generator (zero third-party deps).

Reads a deck spec JSON (meta + preset + slides[]) and emits one self-contained .html file with:
  * fixed 1920x1080 stage, JS-scaled to any viewport (固定舞台约束)
  * keyboard navigation (arrows / space / Home / End / F fullscreen / E edit / Esc exit)
  * staggered fade-in animations (respects prefers-reduced-motion)
  * a mature in-browser EDITING RUNTIME (浏览器内编辑运行时契约):
      - 每页 <section class="slide" id="slide-N">；可移动内容 <div class="obj" data-slide-object data-oid>
      - 对象选择 / 拖⠿移动 / 角拖缩放 / Ctrl+click 多选 / Delete 删除 / 增元素(文字/图/视频)
      - Pages 侧栏：缩略图拖拽重排 / 复制 / 删除 / +New
      - Undo/Redo (Ctrl+Z / Ctrl+Y)；本地保存 (Ctrl+S → localStorage + 下载便携 HTML)
      - 导出干净 HTML（剥离编辑 UI、媒体转 data URL）
  * zero-dependency SVG charts (bar / pie / line)

Usage:
  python3 build_deck.py --spec deck.json --out deck.html [--preset academic-light]
  python3 build_deck.py --spec deck.json --check              # 验收门禁（密度/字号/对比度/溢出）
  python3 build_deck.py --spec deck.json --out deck.html --dist deck.dist.html  # 双产物：可编辑源 + 剥离编辑 UI 的演示版

Runtime features (single file, zero deps):
  * presenter mode: S 键弹出演讲者控制台（当前页/下一页像素预览 + 讲稿 + 计时器，
    BroadcastChannel 双屏同步）；?presenter=1 控制台视图；?preview=N&ui=0 iframe 像素预览
  * theme switching: T 键在全部预设间无白屏循环切换（html[data-theme] 变量重映射）
  * notes 契约：讲者备注渲染为不可见 div.notes，仅供演讲者模式读取
"""
from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path

# spec 文件所在目录（image 相对路径解析基准；由 main 加载 spec 后设置，供 render_slide 使用）
SPEC_DIR: Path | None = None

# --------------------------------------------------------------------------- #
# Style presets: STYLE_PRESETS 四维度范式
#   layout     —— 版式叙述（标题页 / 内容页如何因预设而异的散文规范）
#   signature  —— 签名元素（该预设独有的视觉标记）
#   vars       —— Colors（调色板，注入 :root CSS 变量）
#   typography —— 字体栈（--font-head / --font-body）
# 每套是「规范」而非仅配色：实现时须落实其 layout + signature，不得跨美学复用同一几何。
# --------------------------------------------------------------------------- #
PRESETS = {
    "academic-light": {
        "name": "学术·浅",
        "layout": "标题页左对齐大字号标题+副标；内容页顶部标题条+左缩进要点，留白克制。",
        "signature": "左侧细 accent 竖条、圆角卡片、淡灰 surface。",
        "typography": {"head": '"PingFang SC","Microsoft YaHei","Source Han Sans SC",sans-serif',
                       "body": '"PingFang SC","Microsoft YaHei","Source Han Sans SC",sans-serif'},
        "vars": {
            "--bg": "#ffffff", "--fg": "#1f2733", "--muted": "#5b6675",
            "--primary": "#1f3a5f", "--accent": "#e8833a",
            "--surface": "#f4f6f9", "--line": "#d7dde6",
        },
    },
    "ink": {
        "name": "纸墨·中文",
        "layout": "标题页居中竖排感标题+细线分隔；内容页宋体大行距，段落式叙述为主。",
        "signature": "宣纸米色底、宋体、朱红 accent、发丝级分隔线。",
        "typography": {"head": '"Songti SC","SimSun","Source Han Serif SC",serif',
                       "body": '"Songti SC","SimSun","Source Han Serif SC",serif'},
        "vars": {
            "--bg": "#f7f3ea", "--fg": "#23201c", "--muted": "#6b6258",
            "--primary": "#23201c", "--accent": "#9e2b25",
            "--surface": "#efe7d6", "--line": "#d8ccb4",
        },
    },
    "aurora": {
        "name": "极光·科技",
        "layout": "标题页整屏深色+霓虹渐变大字；内容页网格分区、半透明 surface 卡片、冷光描边。",
        "signature": "深色底、青紫渐变光晕、玻璃拟态卡片、发光分隔。",
        "typography": {"head": '"PingFang SC","Microsoft YaHei",sans-serif',
                       "body": '"PingFang SC","Microsoft YaHei",sans-serif'},
        "vars": {
            "--bg": "#0c1020", "--fg": "#e8ecf6", "--muted": "#8b93ad",
            "--primary": "#37e0c8", "--accent": "#7c5cff",
            "--surface": "#161c33", "--line": "#2a3354",
        },
    },
    "lava": {
        "name": "熔岩·电影",
        "layout": "标题页电影宽幅字幕式；内容页大图背景+前景文字卡，强对比。",
        "signature": "暖黑底、橙红渐变、衬线标题、暗角。",
        "typography": {"head": '"PingFang SC","Microsoft YaHei",sans-serif',
                       "body": '"Noto Serif SC","Songti SC",serif'},
        "vars": {
            "--bg": "#15100d", "--fg": "#f3e9e2", "--muted": "#b79b8c",
            "--primary": "#ff7a45", "--accent": "#b3261e",
            "--surface": "#241a14", "--line": "#3d2a1f",
        },
    },
    "sandstone": {
        "name": "砂岩·温暖",
        "layout": "标题页暖色大圆角块+居中标题；内容页柔和卡片、低饱和。",
        "signature": "砂岩米色、暖橙主、橄榄点缀、柔和阴影。",
        "typography": {"head": '"PingFang SC","Microsoft YaHei",sans-serif',
                       "body": '"PingFang SC","Microsoft YaHei",sans-serif'},
        "vars": {
            "--bg": "#fbf4ec", "--fg": "#3a2f28", "--muted": "#6b5a49",
            "--primary": "#c06b4f", "--accent": "#6b7a3a",
            "--surface": "#f1e4d6", "--line": "#e0cdb8",
        },
    },
    "obsidian": {
        "name": "玄金·中国漆器",
        "layout": "标题页漆黑底+鎏金大字+留白；内容页楷体标题、宋体正文、金线分隔。",
        "signature": "玄黑底、鎏金、楷体、漆器质感描边。",
        "typography": {"head": '"STKaiti","KaiTi","Ma Shan Zheng",cursive',
                       "body": '"Songti SC","SimSun","Source Han Serif SC",serif'},
        "vars": {
            "--bg": "#0e0e10", "--fg": "#ece3d0", "--muted": "#9a8f76",
            "--primary": "#c9a24b", "--accent": "#d9b85a",
            "--surface": "#1a1814", "--line": "#3a3326",
        },
    },
    "concrete": {
        "name": "混凝土·粗犷",
        "layout": "标题页粗黑描边大字+网格；内容页高对比、硬边卡片、撞色块。",
        "signature": "灰白底、蓝黄撞色、粗黑线、硬阴影。",
        "typography": {"head": '"PingFang SC","Microsoft YaHei",sans-serif',
                       "body": '"PingFang SC","Microsoft YaHei",sans-serif'},
        "vars": {
            "--bg": "#f2f2f0", "--fg": "#161616", "--muted": "#555",
            "--primary": "#2d6cff", "--accent": "#ffd23f",
            "--surface": "#ffffff", "--line": "#161616",
        },
    },
    "glacier": {
        "name": "冰川·极简",
        "layout": "标题页大量留白+小字标签；内容页极简列表、细蓝线、冷灰。",
        "signature": "纯白底、冰蓝、极细线、克制留白。",
        "typography": {"head": '"PingFang SC","Microsoft YaHei",sans-serif',
                       "body": '"PingFang SC","Microsoft YaHei",sans-serif'},
        "vars": {
            "--bg": "#ffffff", "--fg": "#22323d", "--muted": "#5a6b76",
            "--primary": "#3a7ca5", "--accent": "#9ec5d8",
            "--surface": "#eef4f8", "--line": "#cfe0ea",
        },
    },
    # magazine 系（5 套色板，变量映射后并入 SSOT；
    #   ink→fg/primary、paper→bg、paper-tint→surface、ink-tint→muted、accent 为补取并过 --check）
    "magazine-ink": {
        "name": "墨水经典·杂志",
        "layout": "标题页纯墨黑大字+暖米底+衬线标题；内容页杂志式标题条+正文左对齐，kicker 上置。",
        "signature": "暖米纸底、墨黑衬线标题、朱红 accent 点缀、发丝分隔线。",
        "typography": {"head": '"Playfair Display","Songti SC","Source Han Serif SC",serif',
                       "body": '"PingFang SC","Microsoft YaHei",sans-serif'},
        "vars": {
            "--bg": "#f1efea", "--fg": "#0a0a0b", "--muted": "#18181a",
            "--primary": "#0a0a0b", "--accent": "#9e2b25",
            "--surface": "#e8e5de", "--line": "#d8d2c4",
        },
    },
    "magazine-indigo": {
        "name": "靛蓝瓷·科技",
        "layout": "标题页深靛蓝大字+瓷白底；内容页学术期刊式标题、冷静数据区。",
        "signature": "瓷白底、深靛蓝标题、深橙 accent、冷灰分隔。",
        "typography": {"head": '"Noto Serif SC","Songti SC","Source Han Serif SC",serif',
                       "body": '"PingFang SC","Microsoft YaHei",sans-serif'},
        "vars": {
            "--bg": "#f1f3f5", "--fg": "#0a1f3d", "--muted": "#152a4a",
            "--primary": "#0a1f3d", "--accent": "#c2571a",
            "--surface": "#e4e8ec", "--line": "#ccd6e0",
        },
    },
    "magazine-forest": {
        "name": "森林墨·自然",
        "layout": "标题页深森林绿大字+象牙底；内容页沉稳留白、自然叙事。",
        "signature": "象牙底、森林绿标题、陶土 accent、暖色发丝线。",
        "typography": {"head": '"Source Serif 4","Songti SC","Source Han Serif SC",serif',
                       "body": '"PingFang SC","Microsoft YaHei",sans-serif'},
        "vars": {
            "--bg": "#f5f1e8", "--fg": "#1a2e1f", "--muted": "#253d2c",
            "--primary": "#1a2e1f", "--accent": "#b3742f",
            "--surface": "#ece7da", "--line": "#ddd5c3",
        },
    },
    "magazine-kraft": {
        "name": "牛皮纸·人文",
        "layout": "标题页深棕大字+暖米底；内容页怀旧叙事、老笔记本质感。",
        "signature": "牛皮纸底、深棕标题、赭红 accent、暖色粗分隔。",
        "typography": {"head": '"STKaiti","KaiTi","Ma Shan Zheng",cursive',
                       "body": '"PingFang SC","Microsoft YaHei",sans-serif'},
        "vars": {
            "--bg": "#eedfc7", "--fg": "#2a1e13", "--muted": "#3a2a1d",
            "--primary": "#2a1e13", "--accent": "#8a4b2a",
            "--surface": "#e0d0b6", "--line": "#d5c3a6",
        },
    },
    "magazine-dune": {
        "name": "沙丘·创意",
        "layout": "标题页炭灰大字+沙色底；内容页克制高级、画廊手册风。",
        "signature": "沙色底、炭灰标题、暖橙 accent、极细冷灰线。",
        "typography": {"head": '"PingFang SC","Microsoft YaHei",sans-serif',
                       "body": '"PingFang SC","Microsoft YaHei",sans-serif'},
        "vars": {
            "--bg": "#f0e6d2", "--fg": "#1f1a14", "--muted": "#2d2620",
            "--primary": "#1f1a14", "--accent": "#a35f3a",
            "--surface": "#e3d7bf", "--line": "#d6c8ac",
        },
    },
}

# 模块级 oid 计数器（每次 build 重置）
OID = 0

BASE_CSS = """
:root{ --stage-w:1920px; --stage-h:1080px; }
*{box-sizing:border-box;}
html,body{margin:0;height:100%;background:#0b0b0c;overflow:hidden;
  font-family:var(--font-body);color:var(--fg);}
#viewport{position:fixed;inset:0;}
#stage{position:relative;left:50%;top:50%;width:var(--stage-w);height:var(--stage-h);
  transform:translate(-50%,-50%) scale(var(--s,1));background:var(--bg);overflow:hidden;}
.slide{position:absolute;inset:0;opacity:0;visibility:hidden;
  transition:opacity .45s ease;padding:0;overflow:hidden;}
.slide.active{opacity:1;visibility:visible;}
.obj{position:absolute;z-index:1;}
/* 静态装饰（preset 签名元素）：不参与编辑选择/拖拽，置于内容之下 */
.deco{position:absolute;pointer-events:none;z-index:0;}
/* academic-light 签名：标题页左侧 accent 竖条 */
.dl-academic{left:140px;top:340px;width:8px;height:250px;background:var(--accent);border-radius:4px;}
/* ink 签名：标题页上下发丝线、内容页发丝分隔线 */
.dl-ink-title{left:50%;top:336px;transform:translateX(-50%);width:600px;height:2px;
  background:var(--accent);box-shadow:0 404px 0 var(--accent);opacity:.85;}
.dl-ink-line{left:140px;top:228px;width:1640px;height:1px;background:var(--line);}
/* aurora 签名：标题页霓虹渐变背景+光晕、内容页冷光分隔线 */
.dl-aurora-bg{left:0;top:0;width:1920px;height:1080px;
  background:radial-gradient(circle at 30% 35%,rgba(124,92,255,.38),transparent 55%),
             radial-gradient(circle at 75% 70%,rgba(55,224,200,.32),transparent 55%);}
.dl-aurora-glow{left:100px;top:280px;width:1720px;height:320px;
  background:linear-gradient(90deg,rgba(55,224,200,.14),transparent 60%);filter:blur(46px);}
.dl-aurora-line{left:140px;top:228px;width:1640px;height:1px;
  background:linear-gradient(90deg,rgba(124,92,255,.65),transparent 72%);}
/* magazine 系签名（方案 B）：标题页顶部小标签(kicker)+ 底部细线；内容页左侧 accent 细条 */
.dl-mag-kicker{left:140px;top:96px;width:8px;height:34px;background:var(--accent);border-radius:2px;}
.dl-mag-title-line{left:140px;top:896px;width:360px;height:3px;background:var(--accent);opacity:.8;}
.dl-mag-body-line{left:140px;top:228px;width:1640px;height:1px;background:var(--line);}
/* magazine-indigo 专属：瓷白底 + 左上角冷色小方块（学术期刊感） */
.dl-mag-indigo-block{left:140px;top:96px;width:10px;height:34px;background:var(--accent);border-radius:1px;}
/* magazine-forest 专属：象牙底 + 顶部细绿线 */
.dl-mag-forest-top{left:0;top:0;width:1920px;height:6px;background:var(--primary);opacity:.35;}
/* magazine-kraft 专属：牛皮纸底 + 左上角赭红小三角 */
.dl-mag-kraft-corner{left:0;top:0;width:0;height:0;
  border-top:64px solid var(--accent);border-right:64px solid transparent;opacity:.85;}
/* magazine-dune 专属：沙色底 + 底部中置细暖线 */
.dl-mag-dune-bottom{left:50%;bottom:64px;transform:translateX(-50%);width:240px;height:2px;
  background:var(--accent);opacity:.6;}
[contenteditable]:focus{outline:none;}
.anim{opacity:0;transform:translateY(24px);}
/* 打印/PDF 导出：每页一版、铺满整页、隐藏编辑器 HUD 与装饰动画态 */
@media print{
  html,body{background:#fff;overflow:visible;height:auto;}
  #viewport{position:static;display:block;}
  #stage{transform:none !important;width:1920px;height:1080px;}
  .slide{position:relative;inset:auto;opacity:1 !important;visibility:visible !important;
    width:1920px;height:1080px;page-break-after:always;overflow:hidden;}
  .slide:last-child{page-break-after:auto;}
  .anim{opacity:1 !important;transform:none !important;}
  #hud,#rail,.toast,.laser,.edit-ui,.pages-rail{display:none !important;}
}
.slide.active .anim{animation:rise .55s ease forwards;}
.slide.active .anim.d1{animation-delay:.05s;}
.slide.active .anim.d2{animation-delay:.15s;}
.slide.active .anim.d3{animation-delay:.25s;}
.slide.active .anim.d4{animation-delay:.35s;}
.slide.active .anim.d5{animation-delay:.45s;}
@keyframes rise{to{opacity:1;transform:translateY(0);}}
h1,h2,h3{font-family:var(--font-head);font-weight:800;margin:0;line-height:1.12;
  color:var(--primary);}
.title-xl{font-size:84px;}
.page-title{font-size:52px;}
.lead{font-size:30px;color:var(--muted);line-height:1.5;}
.bullets{font-size:34px;line-height:1.7;}
.bullets li{margin:14px 0;list-style:none;padding-left:34px;position:relative;}
.bullets li::before{content:"";position:absolute;left:0;top:18px;width:14px;height:14px;
  border-radius:50%;background:var(--accent);}
.card{background:var(--surface);border:1px solid var(--line);border-radius:18px;padding:30px 36px;}
.col-accent{border-left:10px solid var(--accent);}
.two-col{display:flex;gap:40px;}
.two-col>div{flex:1;}
.quote{font-family:var(--font-body);font-size:46px;line-height:1.5;font-style:italic;
  border-left:8px solid var(--accent);padding-left:30px;}
.cite{font-size:28px;color:var(--muted);margin-top:18px;}
.steps{counter-reset:s;font-size:32px;line-height:1.6;}
.steps li{list-style:none;margin:16px 0;padding-left:64px;position:relative;}
.steps li::before{counter-increment:s;content:counter(s);position:absolute;left:0;top:0;
  width:46px;height:46px;border-radius:50%;background:var(--primary);color:#fff;
  display:grid;place-items:center;font-weight:800;font-size:24px;}
table{width:100%;border-collapse:collapse;font-size:30px;}
th,td{border:1px solid var(--line);padding:16px 20px;text-align:left;}
th{background:var(--primary);color:#fff;font-family:var(--font-head);}
tr:nth-child(even) td{background:var(--surface);}
.chart-wrap{width:1500px;height:620px;}
.caption{font-size:24px;color:var(--muted);}
.foot{position:absolute;left:60px;bottom:34px;font-size:20px;color:var(--muted);}
.page-no{position:absolute;right:60px;bottom:34px;font-size:20px;color:var(--muted);}
/* 演讲备注契约：notes 绝不在观众视图可见（html-ppt 契约），仅供演讲者模式/N 键抽屉读取 */
.notes{display:none!important;}
@media (prefers-reduced-motion: reduce){
  .slide{transition:none;}
  .anim{animation:none!important;opacity:1!important;transform:none!important;}
}
"""

# 编辑运行时 CSS（浏览器内编辑运行时契约视觉层）
EDITOR_CSS = """
.obj[data-slide-object]{cursor:default;}
.obj.sel{outline:2px solid var(--accent);outline-offset:2px;z-index:20;}
.rz{position:absolute;width:16px;height:16px;background:var(--accent);border:2px solid #fff;
  border-radius:3px;z-index:30;}
.rz.nw{left:-8px;top:-8px;cursor:nwse-resize;}
.rz.ne{right:-8px;top:-8px;cursor:nesw-resize;}
.rz.sw{left:-8px;bottom:-8px;cursor:nesw-resize;}
.rz.se{right:-8px;bottom:-8px;cursor:nwse-resize;}
#hud{position:absolute;left:24px;top:24px;display:none;gap:8px;z-index:90;flex-wrap:wrap;max-width:60vw;}
#hud.show{display:flex;}
#hud button{font:600 16px var(--font-body);padding:8px 12px;border:none;border-radius:10px;
  background:var(--primary);color:#fff;cursor:pointer;}
#hud button.ghost{background:var(--surface);color:var(--fg);border:1px solid var(--line);}
#rail{position:absolute;right:0;top:0;height:100%;width:300px;background:rgba(18,18,22,.94);
  color:#eee;transform:translateX(100%);transition:transform .3s;z-index:95;overflow:auto;padding:14px;}
#rail.show{transform:translateX(0);}
#rail h4{margin:6px 4px 12px;font:700 16px var(--font-body);}
#rail .pg{position:relative;margin:0 0 12px;border:2px solid #333;border-radius:8px;overflow:hidden;
  cursor:grab;background:#000;}
#rail .pg.cur{border-color:var(--accent);}
#rail .pg .thumb{transform-origin:top left;}
#rail .pg .ops{position:absolute;right:4px;top:4px;display:flex;gap:4px;}
#rail .pg .ops button{font:600 12px var(--font-body);padding:3px 7px;border:none;border-radius:6px;
  background:#2d6cff;color:#fff;cursor:pointer;}
#rail .pg .ops button.del{background:#c0392b;}
#rail .pg .ops button.cp{background:#27ae60;}
#toast{position:absolute;left:50%;bottom:80px;transform:translateX(-50%);
  background:#111;color:#fff;padding:12px 22px;border-radius:12px;opacity:0;transition:opacity .3s;z-index:99;}
#toast.show{opacity:1;}
.laser{position:absolute;width:18px;height:18px;border-radius:50%;background:rgba(255,40,40,.85);
  box-shadow:0 0 18px 8px rgba(255,40,40,.55);pointer-events:none;z-index:120;display:none;}
/* 常驻编辑入口按钮(右下角浮岛)—— #hud 隐藏时也能进入编辑模式,解决"编辑按钮没了"的发现性问题 */
.edit-entry{position:fixed;right:18px;bottom:18px;z-index:88;display:inline-flex;align-items:center;gap:6px;
  font:600 14px var(--font-body);padding:9px 14px;border:none;border-radius:22px;
  background:var(--primary);color:#fff;cursor:pointer;box-shadow:0 4px 14px rgba(0,0,0,.28);
  opacity:.88;transition:opacity .2s,transform .2s;}
.edit-entry:hover{opacity:1;transform:translateY(-1px);}
.edit-entry[hidden]{display:none;}
body:not(.ui-preview) .edit-entry{display:inline-flex;}
@media print{.edit-entry{display:none !important;}}
"""

# 演讲者模式 CSS（S 键双屏同步：当前页/下一页/讲稿/计时器 四卡片控制台）
PRESENTER_CSS = """
#presenter{display:none;position:fixed;inset:0;background:#0b0c10;color:#e8ecf6;
  font-family:var(--font-body);padding:22px;overflow:auto;z-index:200;}
#presenter .pc-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;height:100%;min-height:620px;}
#presenter .pc-card{background:#14151d;border:1px solid #2a2c3a;border-radius:14px;padding:14px;
  display:flex;flex-direction:column;min-height:0;}
#presenter .pc-card h4{margin:0 0 10px;font-size:15px;color:#9aa3c2;font-weight:700;letter-spacing:1px;}
#presenter .pc-card iframe{flex:1;width:100%;border:none;border-radius:8px;background:#fff;min-height:0;}
#presenter .pc-notes div{flex:1;overflow:auto;white-space:pre-wrap;font-size:16px;line-height:1.75;color:#d8dcf0;}
#presenter #pc-timer{font-size:54px;font-weight:800;color:#37e0c8;margin:6px 0 14px;font-variant-numeric:tabular-nums;}
#presenter .pc-card button{font:600 14px var(--font-body);padding:8px 18px;border:none;border-radius:8px;
  background:#37e0c8;color:#0b0c10;cursor:pointer;margin-right:8px;}
#presenter .pc-card button.pc-reset{background:#2a2c3a;color:#e8ecf6;}
#presenter .pc-tip{margin-top:12px;font-size:13px;color:#77809e;}
body.ui-preview .foot,body.ui-preview .page-no{display:none;}
"""

TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN" data-theme="__THEME__">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>__META_TITLE__</title>
<style>
__CSS__
</style>
</head>
<body class="__BODY_CLASS__">
<div id="viewport"><div id="stage">
__SLIDES__
<div class="foot">__META_COURSE__</div>
<div class="page-no"><span id="pn">1</span>/__TOTAL__</div>
</div></div>
__EDITOR_HTML__
<div id="presenter">
  <div class="pc-grid">
    <div class="pc-card"><h4>当前页</h4><iframe id="pv-cur" title="当前页预览"></iframe></div>
    <div class="pc-card"><h4>下一页</h4><iframe id="pv-next" title="下一页预览"></iframe></div>
    <div class="pc-card pc-notes"><h4>讲稿</h4><div id="pc-notes"></div></div>
    <div class="pc-card">
      <h4>计时</h4>
      <div id="pc-timer">00:00</div>
      <div><button id="pc-start">开始</button><button id="pc-reset" class="pc-reset">重置</button></div>
    </div>
  </div>
  <div class="pc-tip" id="pc-tip"></div>
</div>
<script>
window.__THEMES__ = __THEMES_JSON__;
var NAV_JS_SRC = __NAV_JS_SRC__;
var EDITOR_JS_SRC = __EDITOR_JS_SRC__;
var PRESENTER_JS_SRC = __PRESENTER_JS_SRC__;
__NAV_JS__
__EDITOR_JS__
__PRESENTER_JS__
</script>
</body>
</html>
"""


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def preset_css(pid: str) -> str:
    p = PRESETS.get(pid, PRESETS["academic-light"])
    lines = [":root{"]
    for k, v in p["vars"].items():
        lines.append(f"  {k}:{v};")
    lines.append(f"  --font-head:{p['typography']['head']};")
    lines.append(f"  --font-body:{p['typography']['body']};")
    lines.append("}")
    return "\n".join(lines)


def themes_css() -> str:
    """全部预设打包为 html[data-theme=...] 作用域，T 键运行时无白屏切换。

    每套预设四维度（Layout 散文 / Signature 元素见 PRESETS 与 variant 装饰、
    Typography / Colors 在此展开为 CSS 变量）；默认作用域由模板 data-theme 指定。
    """
    blocks = []
    for pid, p in PRESETS.items():
        lines = [f'html[data-theme="{pid}"]{{']
        for k, v in p["vars"].items():
            lines.append(f"  {k}:{v};")
        lines.append(f"  --font-head:{p['typography']['head']};")
        lines.append(f"  --font-body:{p['typography']['body']};")
        lines.append("}")
        blocks.append("\n".join(lines))
    return "\n".join(blocks)


THEME_ORDER = list(PRESETS.keys())


def render_chart(slide: dict) -> str:
    ct = slide.get("chart", "bar")
    data = slide.get("data") or {}
    labels = data.get("labels", [])
    try:
        values = [float(v) for v in data.get("values", [])]
    except (TypeError, ValueError):
        # 防护：非法数值不再 traceback，给出「图表数据缺失」提示
        return '<div class="caption">（图表数据缺失：values 含非数值）</div>'
    unit = data.get("unit", "")
    W, H = 1500, 620
    if ct == "bar" and values:
        mx = max(values) or 1
        n = len(values)
        bw = W / n * 0.6
        gap = W / n
        parts = [f'<svg class="chart-wrap" viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">']
        base = H - 60
        for i, v in enumerate(values):
            x = gap * i + (gap - bw) / 2
            hgt = base * (v / mx)
            y = base - hgt
            parts.append(
                f'<rect x="{x:.0f}" y="{y:.0f}" width="{bw:.0f}" height="{hgt:.0f}" '
                f'rx="8" fill="var(--primary)"/>'
            )
            parts.append(
                f'<text x="{x+bw/2:.0f}" y="{y-14:.0f}" text-anchor="middle" '
                f'font-size="34" fill="var(--fg)">{esc(v)}{esc(unit)}</text>'
            )
            ly = base + 38
            parts.append(
                f'<text x="{x+bw/2:.0f}" y="{ly:.0f}" text-anchor="middle" '
                f'font-size="28" fill="var(--muted)">{esc(labels[i]) if i < len(labels) else ""}</text>'
            )
        parts.append("</svg>")
        return "".join(parts)
    if ct == "pie" and values:
        total = sum(values) or 1
        cx, cy, r = W / 2, H / 2, 240
        ang = 0.0
        parts = [f'<svg class="chart-wrap" viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">']
        cols = ["var(--primary)", "var(--accent)", "#7c5cff", "#37e0c8", "#e8833a", "#9e2b25"]
        for i, v in enumerate(values):
            a0 = ang
            a1 = ang + 360 * v / total
            ang = a1
            import math
            x0 = cx + r * math.cos(math.radians(a0))
            y0 = cy + r * math.sin(math.radians(a0))
            x1 = cx + r * math.cos(math.radians(a1))
            y1 = cy + r * math.sin(math.radians(a1))
            large = 1 if (a1 - a0) > 180 else 0
            parts.append(
                f'<path d="M{cx} {cy} L{x0:.1f} {y0:.1f} A{r} {r} 0 {large} 1 {x1:.1f} {y1:.1f} Z" '
                f'fill="{cols[i % len(cols)]}"/>'
            )
            lx = cx + (r + 40) * math.cos(math.radians((a0 + a1) / 2))
            ly = cy + (r + 40) * math.sin(math.radians((a0 + a1) / 2))
            parts.append(
                f'<text x="{lx:.0f}" y="{ly:.0f}" text-anchor="middle" font-size="26" fill="var(--fg)">'
                f'{esc(labels[i]) if i < len(labels) else ""} {v/total*100:.0f}%</text>'
            )
        parts.append("</svg>")
        return "".join(parts)
    if ct == "line" and values:
        mx = max(values) or 1
        n = len(values)
        pad = 60
        bw = (W - pad * 2) / max(n - 1, 1)
        pts = []
        for i, v in enumerate(values):
            x = pad + bw * i
            y = (H - pad * 2) * (1 - v / mx) + pad
            pts.append((x, y))
        poly = " ".join(f"{x:.0f},{y:.0f}" for x, y in pts)
        parts = [f'<svg class="chart-wrap" viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">']
        parts.append(f'<polyline points="{poly}" fill="none" stroke="var(--primary)" stroke-width="6"/>')
        for (x, y), v in zip(pts, values):
            parts.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="10" fill="var(--accent)"/>')
            parts.append(f'<text x="{x:.0f}" y="{y-18:.0f}" text-anchor="middle" font-size="28" fill="var(--fg)">{esc(v)}{esc(unit)}</text>')
        parts.append("</svg>")
        return "".join(parts)
    return '<div class="caption">（图表数据缺失）</div>'


def obj(left, top, width, inner, edit=False, cls="", delay="", oid=None):
    global OID
    OID += 1
    oid_attr = f' data-slide-object data-oid="o{OID}"'
    e = ' data-edit' if edit else ""
    return (f'<div class="obj anim {delay} {cls}" style="left:{left}px;top:{top}px;'
            f'width:{width}px"{oid_attr}{e}>{inner}</div>')


def preset_deco(pid: str, t: str) -> str:
    """该预设独有的静态装饰（签名元素落地，非配色差）。

    对应 PRESETS 的 layout/signature 散文：三套样板（academic-light / ink / aurora）
    输出差异化几何；其余预设暂以默认几何 + 配色差异呈现。
    """
    if pid == "academic-light" and t == "title":
        return '<div class="deco dl-academic"></div>'
    if pid == "ink":
        if t == "title":
            return '<div class="deco dl-ink-title"></div>'
        if t in ("bullets", "two-col", "steps"):
            return '<div class="deco dl-ink-line"></div>'
    if pid == "aurora":
        if t == "title":
            return ('<div class="deco dl-aurora-bg"></div>'
                    '<div class="deco dl-aurora-glow"></div>')
        if t in ("bullets", "two-col", "steps"):
            return '<div class="deco dl-aurora-line"></div>'
    # magazine 系签名装饰落地（5 套差异化几何）
    if pid in ("magazine-ink", "magazine-forest", "magazine-dune"):
        if t == "title":
            return ('<div class="deco dl-mag-kicker"></div>'
                    '<div class="deco dl-mag-title-line"></div>')
        if t in ("bullets", "two-col", "steps", "section"):
            return '<div class="deco dl-mag-body-line"></div>'
    if pid == "magazine-indigo":
        if t == "title":
            return ('<div class="deco dl-mag-indigo-block"></div>'
                    '<div class="deco dl-mag-title-line"></div>')
        if t in ("bullets", "two-col", "steps", "section"):
            return '<div class="deco dl-mag-body-line"></div>'
    if pid == "magazine-kraft":
        if t == "title":
            return '<div class="deco dl-mag-kraft-corner"></div>'
        if t in ("bullets", "two-col", "steps", "section"):
            return '<div class="deco dl-mag-body-line"></div>'
    return ""


def render_slide(slide: dict, idx: int, pid: str = "academic-light") -> str:
    t = slide.get("type", "bullets")
    title = esc(slide.get("title", ""))
    if t == "title":
        sub = esc(slide.get("subtitle", ""))
        blocks = [
            obj(140, 380, 1640, f'<h1 class="title-xl" data-edit>{title}</h1>', edit=True, delay="d1"),
            obj(140, 560, 1640, f'<div class="lead" data-edit>{sub}</div>', edit=True, delay="d2"),
        ]
    elif t == "section":
        lead = esc(slide.get("lead", ""))
        blocks = [
            obj(140, 420, 1640, f'<h1 class="page-title" data-edit>{title}</h1>', edit=True, delay="d1"),
            obj(140, 540, 1640, f'<div class="lead" data-edit>{lead}</div>', edit=True, delay="d2"),
        ]
    elif t == "bullets":
        pts = "".join(f"<li data-edit>{esc(p)}</li>" for p in slide.get("points", []))
        blocks = [
            obj(140, 110, 1640, f'<h2 class="page-title" data-edit>{title}</h2>', edit=True, delay="d1"),
            obj(180, 260, 1560, f'<ul class="bullets">{pts}</ul>', edit=True, delay="d2"),
        ]
        # notes 不再渲染为可见对象；统一由函数尾部以不可见 div.notes 注入（见 return 前注释）。
    elif t == "two-col":
        left = esc(slide.get("left", ""))
        right = esc(slide.get("right", ""))
        blocks = [
            obj(140, 110, 1640, f'<h2 class="page-title" data-edit>{title}</h2>', edit=True, delay="d1"),
            obj(150, 280, 1560,
                f'<div class="two-col"><div class="card col-accent" data-edit>{left}</div>'
                f'<div class="card" data-edit>{right}</div></div>', edit=True, delay="d2"),
        ]
    elif t == "quote":
        text = esc(slide.get("text", ""))
        cite = esc(slide.get("cite", ""))
        blocks = [
            obj(220, 360, 1480, f'<div class="quote" data-edit>{text}</div>', edit=True, delay="d1"),
            obj(260, 720, 1400, f'<div class="cite" data-edit>— {cite}</div>', edit=True, delay="d2"),
        ]
    elif t == "steps":
        items = "".join(f"<li data-edit><b>{esc(s.get('t',''))}</b>　{esc(s.get('d',''))}</li>"
                        for s in slide.get("steps", []))
        blocks = [
            obj(140, 110, 1640, f'<h2 class="page-title" data-edit>{title}</h2>', edit=True, delay="d1"),
            obj(200, 280, 1500, f'<ol class="steps">{items}</ol>', edit=True, delay="d2"),
        ]
    elif t == "chart":
        blocks = [
            obj(140, 110, 1640, f'<h2 class="page-title" data-edit>{title}</h2>', edit=True, delay="d1"),
            obj(210, 250, 1500, render_chart(slide), delay="d2"),
        ]
    elif t == "table":
        headers = "".join(f"<th data-edit>{esc(h)}</th>" for h in slide.get("headers", []))
        rows = "".join(
            "<tr>" + "".join(f"<td data-edit>{esc(c)}</td>" for c in row) + "</tr>"
            for row in slide.get("rows", [])
        )
        blocks = [
            obj(140, 110, 1640, f'<h2 class="page-title" data-edit>{title}</h2>', edit=True, delay="d1"),
            obj(140, 260, 1640, f'<table><thead><tr>{headers}</tr></thead><tbody>{rows}</tbody></table>',
                edit=True, delay="d2"),
        ]
    elif t == "image":
        raw_src = slide.get("src", "")
        cap = esc(slide.get("caption", ""))
        # 本地相对路径（assets/...）base64 内联为 data URL，保证单文件自包含；
        # 相对路径优先相对 spec 文件所在目录解析（SPEC_DIR），其次相对当前工作目录。
        # http(s) 远程图保留原样。文件缺失/读取失败 → 输出占位提示而非死链。
        if raw_src and not raw_src.startswith(("http://", "https://", "data:")):
            try:
                img_path = Path(raw_src)
                if not img_path.is_absolute() and SPEC_DIR:
                    img_path = SPEC_DIR / img_path
                if img_path.is_file():
                    import base64, mimetypes
                    mime = mimetypes.guess_type(str(img_path))[0] or "image/png"
                    b64 = base64.b64encode(img_path.read_bytes()).decode("ascii")
                    src = f"data:{mime};base64,{b64}"
                else:
                    src = ""
                    cap = (cap + "；" if cap else "") + f"[图片缺失: {raw_src}]"
            except OSError:
                src = ""
                cap = (cap + "；" if cap else "") + "[图片读取失败]"
        else:
            src = esc(raw_src)
        blocks = [
            obj(140, 110, 1640, f'<h2 class="page-title" data-edit>{title}</h2>', edit=True, delay="d1"),
            obj(360, 260, 1200, f'<img src="{src}" style="max-width:100%;max-height:620px;display:block;margin:0 auto;">', delay="d2"),
        ]
        if cap:
            blocks.append(obj(360, 900, 1200, f'<div class="caption" data-edit>{cap}</div>', edit=True))
    elif t == "closing":
        blocks = [
            obj(140, 440, 1640, f'<h1 class="page-title" data-edit>{title}</h1>', edit=True, delay="d1"),
        ]
    else:
        blocks = [obj(140, 200, 1640, f'<h2 class="page-title" data-edit>{title}</h2>', edit=True)]
    # 演讲备注契约：notes 以不可见 div.notes 内嵌（观众视图绝不可见），
    # 供演讲者模式 / N 键备注抽屉读取；导出干净 HTML 时同样保留（display:none 不影响演示）。
    notes_txt = esc(slide.get("notes", ""))
    notes_html = f'<div class="notes">{notes_txt}</div>' if notes_txt else ""
    deco = preset_deco(pid, t)
    return (f'<section class="slide" id="slide-{idx}" data-idx="{idx}">'
            f'{"".join(blocks)}{deco}{notes_html}</section>')


NAV_JS = """
var stage=document.getElementById('stage');
var slides=[].slice.call(document.querySelectorAll('.slide'));
var cur=0;
var THEMES=window.__THEMES__||['academic-light'];
function themeIdx(){var d=document.documentElement.dataset.theme||'academic-light';return Math.max(0,THEMES.indexOf(d));}
function nextTheme(){var n=(themeIdx()+1)%THEMES.length;document.documentElement.dataset.theme=THEMES[n];if(typeof toast!=='undefined')toast('主题：'+THEMES[n]);}
var BC=(typeof BroadcastChannel!=='undefined')?new BroadcastChannel('ppt_sync_channel'):null;
function bcSend(i){if(BC)try{BC.postMessage({type:'SYNC_SLIDE',index:i});}catch(e){}}
function fit(){var s=Math.min(innerWidth/1920,innerHeight/1080);stage.style.setProperty('--s',s);}
function show(i){i=Math.max(0,Math.min(slides.length-1,i));if(slides[cur])slides[cur].classList.remove('active');cur=i;if(slides[cur])slides[cur].classList.add('active');var pn=document.getElementById('pn');if(pn)pn.textContent=(cur+1);try{syncRail();}catch(e){}}
function key(e){
  if(e.target.isContentEditable) return;
  if(document.body.classList.contains('ui-preview'))return;   /* 预览 iframe 内部不响应翻页 */
  if(e.key==='ArrowRight'||e.key===' '||e.key==='PageDown'){show(cur+1);bcSend(cur);e.preventDefault();}
  else if(e.key==='ArrowLeft'||e.key==='PageUp'){show(cur-1);bcSend(cur);e.preventDefault();}
  else if(e.key==='Home'){show(0);bcSend(cur);}
  else if(e.key==='End'){show(slides.length-1);bcSend(cur);}
  else if(e.key==='t'||e.key==='T'){nextTheme();}
  else if(e.key==='s'||e.key==='S'){openPresenter();}
}
function openPresenter(){
  var u=new URL(location.href);u.searchParams.set('presenter','1');
  var w=null;try{w=window.open(u.toString(),'_blank');}catch(err){}
  if(!w&&typeof toast!=='undefined'){toast('弹窗被拦截：请在地址栏允许本站弹窗后重按 S');}
}
addEventListener('keydown',key);
addEventListener('resize',fit);
fit();show(0);
"""

# 成熟编辑运行时（浏览器内编辑运行时契约）：
# 对象选择 / 拖⠿移动 / 角拖缩放 / Ctrl+click 多选 / Delete 删除 / 增元素(文字/图/视频)
# Pages 侧栏缩略图重排 / 复制 / 删除 / +New；Undo/Redo；本地保存；导出干净 HTML；Laser/Fullscreen
EDITOR_JS = """
/* 编辑运行时仅在观众/编辑视图初始化；?preview=?presenter= 模式跳过（iframe/控制台不加载编辑器） */
var __QS_EDIT=new URLSearchParams(location.search);
if(!(__QS_EDIT.has('preview')||__QS_EDIT.get('presenter')==='1')){
var editMode=false;
var hud=document.getElementById('hud');
var rail=document.getElementById('rail');
var DRAFT_KEY='ppt-maker-draft::'+document.title;
var SEL=[];                     // 当前选中对象
var HIST=[];var HPTR=-1;        // 撤销/重做栈
function toast(msg){var t=document.getElementById('toast');t.textContent=msg;t.classList.add('show');setTimeout(function(){t.classList.remove('show');},1600);}
var HIST_BYTES=0;var HIST_MAX_BYTES=50*1024*1024;var HIST_MAX_SINGLE=1500000;
function snapshot(){return stage.innerHTML;}
function pushHist(){var s=snapshot();if(s.length>HIST_MAX_SINGLE)return;HIST=HIST.slice(0,HPTR+1);HIST.push(s);if(HIST.length>60){HIST_BYTES-=HIST[0].length;HIST.shift();}HIST_BYTES+=s.length;while(HIST_BYTES>HIST_MAX_BYTES&&HIST.length>1){HIST_BYTES-=HIST[0].length;HIST.shift();}HPTR=HIST.length-1;}
function applyHist(h){stage.innerHTML=h;refresh();}
function undo(){if(HPTR>0){HPTR--;applyHist(HIST[HPTR]);toast('已撤销');}}
function redo(){if(HPTR<HIST.length-1){HPTR++;applyHist(HIST[HPTR]);toast('已重做');}}
function refresh(){slides=[].slice.call(document.querySelectorAll('.slide'));clearSel();syncRail();}
function setEdit(on){
  editMode=on;hud.classList.toggle('show',on);
  var ee=document.getElementById('bEditEntry');if(ee)ee.hidden=on;
  document.querySelectorAll('[data-edit]').forEach(function(el){el.contentEditable=on;});
  if(!on)clearSel();
  toast(on?'编辑模式：可拖⠿/缩放/增删，Ctrl+S 保存':'已退出编辑');
}
function clearSel(){SEL.forEach(function(o){o.classList.remove('sel');removeHandles(o);});SEL=[];}
function removeHandles(o){[].slice.call(o.querySelectorAll('.rz')).forEach(function(h){h.remove();});}
function addHandles(o){removeHandles(o);['nw','ne','sw','se'].forEach(function(c){var h=document.createElement('div');h.className='rz '+c;h.dataset.corner=c;o.appendChild(h);});}
function selectObj(o,multi){if(!editMode)return;if(multi){var i=SEL.indexOf(o);if(i>=0){SEL.splice(i,1);o.classList.remove('sel');removeHandles(o);}else{SEL.push(o);o.classList.add('sel');addHandles(o);}}else{clearSel();SEL=[o];o.classList.add('sel');addHandles(o);}}
/* drag move */
var dragEl=null,dx=0,dy=0;
stage.addEventListener('pointerdown',function(e){
  if(!editMode)return;
  var h=e.target.closest('.rz');
  if(h){startResize(h,e);return;}
  var o=e.target.closest('.obj');
  if(o){var sc=stage.getBoundingClientRect().width/1920;
    if(e.target.isContentEditable){return;}
    selectObj(o,e.ctrlKey||e.metaKey||e.shiftKey);
    dragEl=o;var r=o.getBoundingClientRect();dx=(e.clientX-r.left)/sc;dy=(e.clientY-r.top)/sc;
    o.setPointerCapture(e.pointerId);e.preventDefault();
  } else { if(!e.target.isContentEditable)clearSel(); }
});
stage.addEventListener('pointermove',function(e){
  if(!dragEl)return;var sc=stage.getBoundingClientRect().width/1920;
  var pr=stage.getBoundingClientRect();var x=(e.clientX-pr.left)/sc-dx,y=(e.clientY-pr.top)/sc-dy;
  dragEl.style.left=Math.round(x)+'px';dragEl.style.top=Math.round(y)+'px';
});
stage.addEventListener('pointerup',function(){if(dragEl){dragEl=null;pushHist();}});
/* resize */
function startResize(h,e){e.stopPropagation();var o=h.parentElement;var sc=stage.getBoundingClientRect().width/1920;
  var r=o.getBoundingClientRect();var corner=h.dataset.corner;var sx=o.offsetLeft,sy=o.offsetTop,sw=o.offsetWidth,sh=o.offsetHeight;
  var moved=false;
  function mv(ev){moved=true;var pr=stage.getBoundingClientRect();var x=(ev.clientX-pr.left)/sc,y=(ev.clientY-pr.top)/sc;
    if(corner==='se'){o.style.width=Math.max(40,Math.round(x-sx))+'px';o.style.height=Math.max(40,Math.round(y-sy))+'px';}
    else if(corner==='ne'){var nh=Math.max(40,Math.round(sy+sh-y));o.style.top=Math.round(y)+'px';o.style.height=nh+'px';o.style.width=Math.max(40,Math.round(x-sx))+'px';}
    else if(corner==='sw'){var nw=Math.max(40,Math.round(sx+sw-x));o.style.left=Math.round(x)+'px';o.style.width=nw+'px';o.style.height=Math.max(40,Math.round(y-sy))+'px';}
    else if(corner==='nw'){var nw2=Math.max(40,Math.round(sx+sw-x));var nh2=Math.max(40,Math.round(sy+sh-y));o.style.left=Math.round(x)+'px';o.style.top=Math.round(y)+'px';o.style.width=nw2+'px';o.style.height=nh2+'px';}
  }
  function up(){document.removeEventListener('pointermove',mv);document.removeEventListener('pointerup',up);if(moved)pushHist();}
  document.addEventListener('pointermove',mv);document.addEventListener('pointerup',up);
}
/* delete / add */
function deleteSel(){if(!SEL.length)return;pushHist();SEL.forEach(function(o){var s=o.closest('.slide');o.remove();});clearSel();refresh();toast('已删除');}
function addEl(kind){pushHist();var o=document.createElement('div');o.className='obj';o.setAttribute('data-slide-object','');o.setAttribute('data-oid','o'+Date.now());
  if(kind==='text'){o.innerHTML='<div data-edit style="font-size:34px;color:var(--fg);">双击编辑文字</div>';}
  else if(kind==='image'){o.innerHTML='<img data-edit src="" style="max-width:100%;max-height:600px;" alt="图片">';}
  else if(kind==='video'){o.innerHTML='<video data-edit src="" controls style="max-width:100%;max-height:600px;"></video>';}
  o.style.left='700px';o.style.top='420px';o.style.width='500px';
  slides[cur].appendChild(o);selectObj(o,false);toast('已添加'+(kind==='text'?'文字':kind==='image'?'图片':'视频'));}
/* Pages 侧栏 */
function buildRail(){
  [].slice.call(rail.querySelectorAll('.pg')).forEach(function(n){n.remove();});
  slides.forEach(function(s,i){
    var box=document.createElement('div');box.className='pg'+(i===cur?' cur':'');box.draggable=true;box.dataset.idx=i;
    var th=document.createElement('div');th.className='thumb';th.style.transform='scale(0.135)';th.style.width='1920px';th.style.height='1080px';
    th.innerHTML=s.innerHTML.replace(/contenteditable="true"/g,'');
    box.appendChild(th);
    var ops=document.createElement('div');ops.className='ops';
    var bCp=document.createElement('button');bCp.textContent='复制';bCp.className='cp';bCp.onclick=function(e){e.stopPropagation();copyPage(i);};
    var bDel=document.createElement('button');bDel.textContent='删';bDel.className='del';bDel.onclick=function(e){e.stopPropagation();delPage(i);};
    ops.appendChild(bCp);ops.appendChild(bDel);box.appendChild(ops);
    box.onclick=function(){show(i);};
    box.addEventListener('dragstart',function(e){e.dataTransfer.setData('text/plain',i);});
    box.addEventListener('dragover',function(e){e.preventDefault();});
    box.addEventListener('drop',function(e){e.preventDefault();var from=+e.dataTransfer.getData('text/plain');reorderPage(from,i);});
    rail.appendChild(box);
  });
}
function syncRail(){if(rail.classList.contains('show'))buildRail();
  [].slice.call(rail.querySelectorAll('.pg')).forEach(function(c,i){c.classList.toggle('cur',i===cur);});}
function reorderPage(from,to){if(from===to)return;pushHist();var arr=slides.slice();var m=arr.splice(from,1)[0];arr.splice(to,0,m);
  arr.forEach(function(s){stage.appendChild(s);});refresh();show(to);}
function copyPage(i){pushHist();var c=slides[i].cloneNode(true);c.id='slide-'+Date.now();stage.insertBefore(c,slides[i+1]);refresh();show(i+1);}
function delPage(i){if(slides.length<=1){toast('至少保留一页');return;}pushHist();slides[i].remove();refresh();show(Math.min(i,slides.length-1));}
function newPage(){pushHist();var s=document.createElement('section');s.className='slide';s.id='slide-'+Date.now();
  s.innerHTML='<div class="obj" data-slide-object data-oid="o'+Date.now()+'" style="left:140px;top:110px;width:1640px;"><h2 class="page-title" data-edit>新页面标题</h2></div>';
  stage.appendChild(s);refresh();show(slides.length-1);}
/* save / export */
/* 防御：localStorage 在 iframe(如内置预览)可能被禁用，直接访问会抛 SecurityError
   导致后续 wire 绑定中断、按钮全部失效；改用 safeStore 包装，禁用时改为内存对象。 */
var _store=null;
function _safeStore(){if(_store)return _store;try{var t=window.localStorage;t.setItem('__ppt_t','1');t.removeItem('__ppt_t');_store=t;}catch(e){_store={getItem:function(){return null;},setItem:function(){},removeItem:function(){}};}return _store;}
function saveDraft(){var st=_safeStore();try{st.setItem(DRAFT_KEY,stage.innerHTML);toast('已存本地（localStorage）');}catch(e){toast('存储不可用，跳过保存');}}
function download(name,content,mime){var b=new Blob([content],{type:mime||'text/html'});var a=document.createElement('a');a.href=URL.createObjectURL(b);a.download=name;a.click();}
async function exportClean(){
  pushHist();
  var clone=stage.cloneNode(true);
  clone.querySelectorAll('[data-edit]').forEach(function(el){el.removeAttribute('contenteditable');});
  clone.querySelectorAll('.rz').forEach(function(el){el.remove();});
  clone.querySelectorAll('img').forEach(async function(im){try{if(im.src&&im.src.startsWith('http')){var r=await fetch(im.src);var b=await r.blob();var u=await new Promise(function(res){var fr=new FileReader();fr.onload=function(){res(fr.result);};fr.readAsDataURL(b);});im.src=u;}}catch(e){}});
  await new Promise(function(r){setTimeout(r,300);});
  var css=document.querySelector('style').textContent;
  var html='\\x3C!DOCTYPE html>\\x3Chtml lang="zh-CN">\\x3Chead>\\x3Cmeta charset="utf-8">\\x3Ctitle>'+document.title+
    '\\x3C/title>\\x3Cstyle>'+css+'\\x3C/style>\\x3C/head>\\x3Cbody>\\x3Cdiv id="viewport">\\x3Cdiv id="stage">'+clone.innerHTML+
    '\\x3C/div>\\x3C/div>\\x3Cscript>' + NAV_JS_SRC + '\\x3C/script>\\x3C/body>\\x3C/html>';
  // 剥离 edit_deck 注入的运行时哨兵注释，避免泄漏到导出文件
  html=html.split('<!--EDIT_DECK_RUNTIME_START-->').join('').split('<!--EDIT_DECK_RUNTIME_END-->').join('');
  download(document.title+'-clean.html',html);toast('已导出干净 HTML');
}
/* laser */
var laser=document.getElementById('laser');var laserOn=false;
function laserMove(e){if(!laserOn)return;var pr=stage.getBoundingClientRect();var sc=pr.width/1920;
  laser.style.display='block';laser.style.left=(e.clientX-pr.left)+'px';laser.style.top=(e.clientY-pr.top)+'px';}
stage.addEventListener('pointermove',laserMove);
/* wire */
document.getElementById('bEdit').onclick=function(){setEdit(!editMode);};
document.getElementById('bEditEntry').onclick=function(){setEdit(true);};
document.getElementById('bAddText').onclick=function(){addEl('text');};
document.getElementById('bAddImg').onclick=function(){addEl('image');};
document.getElementById('bAddVid').onclick=function(){addEl('video');};
document.getElementById('bRail').onclick=function(){rail.classList.toggle('show');buildRail();};
document.getElementById('bUndo').onclick=undo;
document.getElementById('bRedo').onclick=redo;
document.getElementById('bSave').onclick=saveDraft;
document.getElementById('bExport').onclick=exportClean;
document.getElementById('bLaser').onclick=function(){laserOn=!laserOn;toast(laserOn?'激光开':'激光关');};
document.getElementById('bFs').onclick=function(){if(!document.fullscreenElement)stage.requestFullscreen();else document.exitFullscreen();};
addEventListener('keydown',function(e){
  if(e.target.isContentEditable)return;
  if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='s'){e.preventDefault();saveDraft();}
  else if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='z'){e.preventDefault();undo();}
  else if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='y'){e.preventDefault();redo();}
  else if(e.key==='Delete'||e.key==='Backspace'){if(SEL.length){e.preventDefault();deleteSel();}}
  else if(e.key==='e'||e.key==='E'){setEdit(!editMode);}
  else if(e.key==='p'||e.key==='P'){rail.classList.toggle('show');buildRail();}
  else if(e.key==='l'||e.key==='L'){laserOn=!laserOn;toast(laserOn?'激光开':'激光关');}
  else if(e.key==='f'||e.key==='F'){if(!document.fullscreenElement)stage.requestFullscreen();else document.exitFullscreen();}
  else if(e.key==='Escape'){if(editMode)setEdit(false);}
});
buildRail();pushHist();
if(_safeStore().getItem(DRAFT_KEY)){setTimeout(function(){try{if(confirm('检测到本地草稿，是否恢复？')){stage.innerHTML=_safeStore().getItem(DRAFT_KEY);refresh();toast('已恢复本地草稿');}}catch(e){}},300);}
}/* end editor-guard */
"""

# 演讲者模式运行时（G2 补齐：S 键双屏同步 / ?presenter=1 控制台 / ?preview=N&ui=0 像素预览）
# 四卡片：当前页 / 下一页（?preview=N iframe 复用同一 HTML 保证像素级一致）、
# 讲稿（读本页 .notes 不可见 div）、计时器；BroadcastChannel('ppt_sync_channel') 零延迟广播。
PRESENTER_JS = """
function initPreview(n){
  document.body.classList.add('ui-preview');
  try{show(n);}catch(e){}
  ['hud','rail','toast','laser'].forEach(function(id){var el=document.getElementById(id);if(el)el.style.display='none';});
  document.getElementById('viewport').style.display='block';
}
function initPresenter(){
  document.getElementById('viewport').style.display='none';
  var pv=document.getElementById('presenter');pv.style.display='block';
  var curFrame=document.getElementById('pv-cur'),nextFrame=document.getElementById('pv-next');
  var notesEl=document.getElementById('pc-notes'),tipEl=document.getElementById('pc-tip');
  var base=new URL(location.href);base.searchParams.delete('presenter');base.searchParams.set('ui','0');
  function noteHTML(i){var s=slides[i];var n=s?s.querySelector('.notes'):null;return n&&n.textContent.trim()?n.textContent:'（本页无讲稿）';}
  function pageTitle(i){var s=slides[i];if(!s)return '';var h=s.querySelector('.page-title,.title-xl');return h?h.textContent.trim():'';}
  function sync(i){
    var c=Math.max(0,Math.min(slides.length-1,i));
    var u1=new URL(base.toString());u1.searchParams.set('preview',c);
    var u2=new URL(base.toString());u2.searchParams.set('preview',Math.min(c+1,slides.length-1));
    curFrame.src=u1.toString();nextFrame.src=u2.toString();
    notesEl.textContent='【第 '+(c+1)+' 页 / '+slides.length+'】'+pageTitle(c)+'\\n\\n'+noteHTML(c);
    tipEl.textContent='演示者模式 · ←/→ 翻页并同步观众屏 · S 重新打开 · F 全屏';
    return c;
  }
  var curIdx=0;
  if(BC)BC.onmessage=function(ev){if(ev.data&&ev.data.type==='SYNC_SLIDE'){curIdx=sync(ev.data.index);}};
  var sec=0,timer=null,tOn=false;
  var tEl=document.getElementById('pc-timer');
  function tick(){sec++;var m=('0'+Math.floor(sec/60)).slice(-2),s2=('0'+(sec%60)).slice(-2);tEl.textContent=m+':'+s2;}
  document.getElementById('pc-start').onclick=function(){if(!tOn){tOn=true;timer=setInterval(tick,1000);this.textContent='暂停';}else{tOn=false;clearInterval(timer);timer=null;this.textContent='继续';}};
  document.getElementById('pc-reset').onclick=function(){sec=0;tEl.textContent='00:00';};
  curIdx=sync(0);
}
var __QS=new URLSearchParams(location.search);
if(__QS.get('presenter')==='1'){initPresenter();}
else if(__QS.has('preview')){initPreview(parseInt(__QS.get('preview'),10)||0);}
"""

# 供 edit_deck.py 复用（注入已有 deck 时导入）
RUNTIME_BLOCK = {
    "css": EDITOR_CSS,
    "nav": NAV_JS,
    "editor": EDITOR_JS,
    "hud_html": (
        # 常驻编辑入口(#hud 隐藏时也能一键进编辑),避免"编辑按钮没了"的发现性问题
        '<button id="bEditEntry" class="edit-entry" type="button" title="进入编辑模式 (E)">\u270e 编辑</button>'
        '<div id="hud">'
        '<button id="bEdit">编辑 (E)</button>'
        '<button id="bAddText" class="ghost">+文字</button>'
        '<button id="bAddImg" class="ghost">+图片</button>'
        '<button id="bAddVid" class="ghost">+视频</button>'
        '<button id="bRail" class="ghost">Pages (P)</button>'
        '<button id="bUndo" class="ghost">撤销 (Ctrl+Z)</button>'
        '<button id="bRedo" class="ghost">重做 (Ctrl+Y)</button>'
        '<button id="bSave" class="ghost">保存 (Ctrl+S)</button>'
        '<button id="bExport" class="ghost">导出干净</button>'
        '<button id="bLaser" class="ghost">激光 (L)</button>'
        '<button id="bFs" class="ghost">全屏 (F)</button>'
        '</div>'
        '<div id="rail"><h4>Pages · 缩略图</h4></div>'
        '<div id="toast"></div>'
        '<div class="laser" id="laser"></div>'
    ),
}


def build(spec: dict, preset_id: str, include_editor: bool = True) -> str:
    global OID
    OID = 0
    slides = spec.get("slides", [])
    slides_html = "".join(render_slide(s, i, preset_id) for i, s in enumerate(slides))
    meta = spec.get("meta", {})
    css = BASE_CSS + "\n" + themes_css() + "\n" + PRESENTER_CSS
    # 风格继承：spec.vars（extract_pptx 从 PPT 主题抽取）覆盖预设变量，
    # 追加为 :root 覆盖块（CSS 后定义者胜，覆盖 themes_css 的预设值）
    spec_vars = spec.get("vars") or {}
    if spec_vars:
        over = ["/* 风格继承：spec.vars 覆盖（来源 PPT 主题抽取） */", ":root{"]
        for k, v in spec_vars.items():
            over.append(f"  {k}:{v};")
        over.append("}")
        css += "\n" + "\n".join(over)
    if include_editor:
        css += "\n" + EDITOR_CSS
    editor_html = RUNTIME_BLOCK["hud_html"] if include_editor else ""
    editor_js = EDITOR_JS if include_editor else ""
    doc = (
        TEMPLATE.replace("__CSS__", css)
        .replace("__SLIDES__", slides_html)
        .replace("__META_TITLE__", esc(meta.get("title", "演示文稿")))
        .replace("__META_COURSE__", esc(meta.get("course", "")))
        .replace("__TOTAL__", str(len(slides)))
        .replace("__THEME__", preset_id)
        .replace("__BODY_CLASS__", "")
        .replace("__EDITOR_HTML__", editor_html)
        .replace("__NAV_JS__", NAV_JS)
        .replace("__NAV_JS_SRC__", json.dumps(NAV_JS))
        .replace("__THEMES_JSON__", json.dumps(THEME_ORDER))
        .replace("__EDITOR_JS__", editor_js)
        .replace("__EDITOR_JS_SRC__", json.dumps(editor_js))
        .replace("__PRESENTER_JS__", PRESENTER_JS)
        .replace("__PRESENTER_JS_SRC__", json.dumps(PRESENTER_JS))
    )
    return doc


# --------------------------------------------------------------------------- #
# 课型骨架模板（G10：Deck 骨架 --template）
# 每套 = 固定页序列 + 可选 repeat 可变段 + tail 收尾；duration 按 90min 基准比例推算页数。
# 展开产物为「占位 Action Title」的 spec JSON，供 agent 按教案填充后 build。
# --------------------------------------------------------------------------- #
DECK_TEMPLATES = {
    "theory-lecture": {
        "name": "理论讲授型", "base": 24, "min": 20, "max": 40,
        "pages": [
            ("title", "课程名称：本章主题", "[占位副标题]"),
            ("bullets", "[占位] 本讲学习目标（3-5 条）", 4),
            ("bullets", "[占位] 导入：问题 / 情境 / 案例", 2),
            ("bullets", "[占位] 本节知识结构地图", 3),
        ],
        "repeat": ("bullets", "[占位] 知识点讲解：概念 → 图示 → 示例", 3),
        "tail": [
            ("two-col", "[占位] 新旧知识对比", None),
            ("bullets", "[占位] 应用案例", 2),
            ("bullets", "[占位] 课堂讨论问题（1-2 个）", 2),
            ("bullets", "[占位] 本节小结", 4),
            ("closing", "[占位] 课后作业与下讲预告", None),
        ],
    },
    "seminar-discussion": {
        "name": "研讨讨论型", "base": 18, "min": 15, "max": 25,
        "pages": [
            ("title", "研讨主题", "[占位副标题]"),
            ("bullets", "[占位] 背景介绍（案例 / 问题背景）", 3),
            ("bullets", "[占位] 讨论问题（3-5 个递进）", 4),
            ("bullets", "[占位] 分组安排与讨论要求", 3),
            ("bullets", "[占位] 各组汇报模板", 3),
        ],
        "repeat": ("bullets", "[占位] 理论支撑：研讨所需知识", 3),
        "tail": [
            ("two-col", "[占位] 多视角对比（观点 / 方案）", None),
            ("bullets", "[占位] 教师点评与深化", 3),
            ("closing", "[占位] 拓展思考与下讲预告", None),
        ],
    },
    "lab-instruction": {
        "name": "实验指导型", "base": 15, "min": 10, "max": 20,
        "pages": [
            ("title", "实验名称", "[占位副标题]"),
            ("bullets", "[占位] 实验目的", 3),
            ("bullets", "[占位] 实验环境 / 工具（器材 / 软件 / 数据）", 3),
            ("bullets", "[占位] 实验原理（简明）", 2),
            ("steps", "[占位] 实验步骤（关键操作标注）", 5),
            ("bullets", "[占位] 注意事项（安全 / 易错点）", 3),
        ],
        "repeat": ("image", "[占位] 操作演示（关键步骤截图 / 视频）", None),
        "tail": [
            ("table", "[占位] 记录要求（数据表格 / 报告要求）", None),
            ("bullets", "[占位] 拓展实验（选做）", 2),
            ("closing", "[占位] 实验总结", None),
        ],
    },
    "project-based": {
        "name": "项目驱动型", "base": 30, "min": 25, "max": 45,
        "pages": [
            ("title", "项目名称", "[占位副标题]"),
            ("bullets", "[占位] 项目背景与目标", 3),
            ("bullets", "[占位] 项目要求（功能需求 / 技术指标 / 交付物）", 4),
            ("steps", "[占位] 项目流程（阶段划分与时间节点）", 5),
            ("bullets", "[占位] 团队组建（分组与角色分工）", 3),
            ("two-col", "[占位] 技术路线（推荐 vs 备选）", None),
            ("table", "[占位] 评价标准（评分细则 rubric）", None),
        ],
        "repeat": ("bullets", "[占位] 阶段任务与里程碑", 3),
        "tail": [
            ("bullets", "[占位] 阶段汇报模板", 3),
            ("bullets", "[占位] 常见问题与资源", 3),
            ("closing", "[占位] 项目启动 / 阶段性安排", None),
        ],
    },
    "flipped-class": {
        "name": "翻转课堂型", "base": 20, "min": 15, "max": 30,
        "pages": [
            ("title", "翻转课堂主题", "[占位副标题]"),
            ("bullets", "[占位] 课前学习任务（视频 / 阅读 + 目标）", 3),
            ("bullets", "[占位] 知识检测（课前小测 3-5 题）", 3),
            ("bullets", "[占位] 答疑解惑（集中解答课前问题）", 3),
            ("bullets", "[占位] 深化讨论（基于课前知识的进阶问题）", 3),
        ],
        "repeat": ("bullets", "[占位] 应用实践（案例 / 问题解决 / 项目实践）", 3),
        "tail": [
            ("bullets", "[占位] 成果展示", 3),
            ("closing", "[占位] 反思总结", None),
        ],
    },
    "review-summary": {
        "name": "复习总结型", "base": 15, "min": 10, "max": 20,
        "pages": [
            ("title", "复习主题", "[占位副标题]"),
            ("bullets", "[占位] 知识全景地图", 4),
            ("bullets", "[占位] 核心概念回顾（考点）", 4),
        ],
        "repeat": ("bullets", "[占位] 重点专题回顾", 4),
        "tail": [
            ("table", "[占位] 易错对比（常见误区）", None),
            ("bullets", "[占位] 典型题型与解题思路", 3),
            ("closing", "[占位] 考前提示", None),
        ],
    },
}


def _item_slide(item: tuple) -> dict:
    """(type, title, payload) → slide dict（占位字段）。"""
    t, title, payload = item
    if t == "title":
        return {"type": "title", "title": title, "subtitle": payload or "[占位副标题]"}
    if t == "section":
        return {"type": "section", "title": title, "lead": payload or ""}
    if t == "closing":
        return {"type": "closing", "title": title}
    if t == "two-col":
        return {"type": "two-col", "title": title, "left": "[占位 左栏]", "right": "[占位 右栏]"}
    if t == "table":
        return {"type": "table", "title": title, "headers": ["[占位列1]", "[占位列2]"],
                "rows": [["[占位]", "[占位]"]]}
    if t == "image":
        return {"type": "image", "title": title, "src": "", "caption": "[占位 图注]"}
    if t == "steps":
        n = int(payload or 4)
        return {"type": "steps", "title": title,
                "steps": [{"t": f"[占位步骤 {k}]", "d": ""} for k in range(1, n + 1)]}
    n = int(payload or 3)  # bullets
    return {"type": "bullets", "title": title,
            "points": [f"[占位要点 {k}]" for k in range(1, n + 1)]}


def template_spec(tid: str, duration: int) -> dict:
    """课型骨架 → spec（占位 Action Title），页数按 duration/90min 基准缩放。"""
    t = DECK_TEMPLATES[tid]
    target = max(t["min"], min(t["max"], round(t["base"] * duration / 90.0)))
    slides = [_item_slide(it) for it in t["pages"]]
    tail_n = len(t.get("tail", []))
    if t.get("repeat"):
        n = max(1, target - len(slides) - tail_n)
        for _ in range(n):
            slides.append(_item_slide(t["repeat"]))
    for it in t.get("tail", []):
        slides.append(_item_slide(it))
    return {"meta": {"title": f"{t['name']}课件骨架（{duration} 分钟）"},
            "preset": "academic-light", "slides": slides}


def _luminance(hexc: str) -> float:
    hexc = hexc.strip().lstrip("#")
    if len(hexc) != 6:
        return 0.0
    try:
        r, g, b = (int(hexc[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    except ValueError:
        return 0.0
    def f(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = f(r), f(g), f(b)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast(a: str, b: str) -> float:
    la, lb = _luminance(a), _luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


# 字号 px → pt（96dpi 下 1pt = 1.333px）；对照 ppt-design-guide 教室字号下限
FONT_PT = {"title-xl": 63.0, "page-title": 39.0, "lead": 22.5, "bullets": 25.5,
           "quote": 34.5, "steps": 24.0, "table": 22.5, "caption": 18.0}

# spec schema 白名单（validate_spec 用）
KNOWN_TYPES = {"title", "section", "bullets", "two-col", "quote", "steps",
               "chart", "table", "image", "closing"}


def validate_spec(spec: dict) -> list[str]:
    """spec 前置校验：返回错误列表（空 = 通过）。

    - meta.preset 必须是已知预设（未知 → 错误，不再静默采用 academic-light）
    - slides 非空且为 list
    - 每页：type 必须在白名单、title 非空
    - chart 页：data.values 必须存在且可转 float（render_chart 防护的前置校验）
    - 返回错误而非抛异常，供 main 统一输出 + 退出码 2
    """
    errs: list[str] = []
    if not isinstance(spec, dict):
        return ["spec 必须是 JSON 对象"]
    pid = spec.get("preset") or "academic-light"
    if pid not in PRESETS:
        errs.append(f"未知预设 '{pid}'（白名单: {', '.join(sorted(PRESETS))}）")
    slides = spec.get("slides")
    if not isinstance(slides, list) or len(slides) == 0:
        errs.append("slides 必须是非空数组")
        return errs
    for i, s in enumerate(slides, 1):
        if not isinstance(s, dict):
            errs.append(f"第{i}页不是对象")
            continue
        t = s.get("type", "bullets")
        if t not in KNOWN_TYPES:
            errs.append(f"第{i}页未知页型 '{t}'（白名单: {', '.join(sorted(KNOWN_TYPES))}）")
        if not str(s.get("title", "")).strip():
            errs.append(f"第{i}页缺少标题（Action Title 原则）")
        if t == "chart":
            data = s.get("data") or {}
            vals = data.get("values")
            if not isinstance(vals, list) or not vals:
                errs.append(f"第{i}页(chart) 缺少 data.values")
            else:
                try:
                    [float(v) for v in vals]
                except (TypeError, ValueError):
                    errs.append(f"第{i}页(chart) data.values 含非数值: {vals!r}")
    return errs


def check_deck(spec: dict, preset_id: str) -> tuple[list[str], int, int]:
    """验收门禁（G5）：密度 / 字号 / 对比度 / 溢出 四维启发式检查。

    返回 (报告行, fail 数, warn 数)；任何 FAIL 时调用方应令进程退出码非 0。
    """
    lines = []
    fails = warns = 0
    p = PRESETS.get(preset_id, PRESETS["academic-light"])
    slides = spec.get("slides", [])

    lines.append("== 验收报告（--check）==")
    lines.append(f"主题: {preset_id}（{p['name']}）| 页数: {len(slides)}")

    # 1) 对比度（bg/fg、bg/muted 按正文 4.5:1；accent 为装饰点缀色，按非文本 3:1，
    #    若 accent 用于正文文字须人工复核 4.5:1）
    bg, fg, mute = p["vars"]["--bg"], p["vars"]["--fg"], p["vars"]["--muted"]
    accent = p["vars"]["--accent"]
    for label, c, thr in (("正文/背景", fg, 4.5), ("次要/背景", mute, 4.5),
                          ("强调/背景(非文本)", accent, 3.0)):
        cr = _contrast(c, bg)
        ok = cr >= thr
        if not ok:
            if label.startswith("强调"):
                warns += 1
                lines.append(f"[WARN] 对比度 {label} {cr:.1f}:1 (<{thr:.1f}:1)；accent 用于正文文字时须人工复核 ≥4.5:1  {c} on {bg}")
            else:
                fails += 1
                lines.append(f"[FAIL] 对比度 {label} {cr:.1f}:1 (≥{thr:.1f}:1)  {c} on {bg}")

    # 2) 字号下限（正文类）
    for cls, pt in FONT_PT.items():
        if pt < 20.0:
            lines.append(f"[WARN] 字号 {cls} {pt:.0f}pt < 20pt 下限（仅限备注/页脚类，正文禁用）")
            warns += 1

    # 3) 逐页密度与溢出（title/section/closing 为标题类页，只校验标题存在，不按字数限）
    DENSITY = {"title": (1, 1), "section": (1, 1), "bullets": (80, 6),
               "two-col": (60, 6), "quote": (80, 2), "steps": (60, 7),
               "chart": (60, 2), "table": (60, 9), "image": (40, 2), "closing": (1, 1)}
    TITLE_ONLY = {"title", "section", "closing"}
    for i, s in enumerate(slides, 1):
        t = s.get("type", "bullets")
        title = s.get("title", "")
        if t in TITLE_ONLY:
            if not title:
                warns += 1
                lines.append(f"[WARN] 第{i}页({t}) 缺少标题")
            continue
        texts = " ".join(str(s.get(k, "")) for k in
                         ("subtitle", "lead", "points", "left", "right", "text", "cite", "caption"))
        char_n = len(title) + len(texts)
        maxc, maxrow = DENSITY.get(t, (80, 6))
        rows = len(s.get("points", [])) if t == "bullets" else len(s.get("steps", [])) if t == "steps" \
            else len(s.get("rows", [])) if t == "table" else 0
        if char_n > maxc:
            fails += 1
            lines.append(f"[FAIL] 第{i}页({t}) 约{char_n}字，超密度上限{maxc}字")
        if rows > maxrow:
            fails += 1
            lines.append(f"[FAIL] 第{i}页({t}) 内容{rows}行，超上限{maxrow}行（溢出风险）")
        elif rows > 0 and rows > maxrow - 2:
            warns += 1
            lines.append(f"[WARN] 第{i}页({t}) {rows}行接近上限{maxrow}，建议拆页")
        if not title:
            warns += 1
            lines.append(f"[WARN] 第{i}页({t}) 缺少标题（Action Title 原则）")

    lines.append(f"结论: {fails} FAIL / {warns} WARN（FAIL 存在时验收不通过）")

    # 5) 整改建议（按 4 维度分组，给出可执行 fix-it 清单；不改退出码与 spec，
    #    仅作为"红色就放弃"场景的引导——上游 LLM / 用户据此可一次性改造 spec 后重跑）
    if fails or warns:
        lines.append("")
        lines.append("== 整改建议（按 4 维度分组，可复制到下轮迭代）==")
        # 5.1 密度
        density_fails = [ln for ln in lines if "超密度上限" in ln or "超上限" in ln]
        if density_fails:
            lines.append("【密度】拆页 / 图表替代文字（按 DENSITY 上限 80/60 字）：")
            for ln in density_fails:
                lines.append("  - " + ln)
            lines.append("  建议：超字数页 → 拆为两页；或 chart/table 类型承载；或精简到 ≤6 个 bullet")
        # 5.2 对比度
        contrast_fails = [ln for ln in lines if "对比度" in ln]
        if contrast_fails:
            lines.append("【对比度】换预设或微调 --fg/--muted/--accent（WCAG 4.5:1 正文 / 3:1 accent）：")
            for ln in contrast_fails:
                lines.append("  - " + ln)
            lines.append("  建议：换 academic-light → ink（#23201c on #f7f3ea 7.0:1）；或拉低 accent 饱和度")
        # 5.3 字号
        font_warns = [ln for ln in lines if "字号" in ln and "WARN" in ln]
        if font_warns:
            lines.append("【字号】正文类 ≥ 20pt（20px = 15pt 临界，须确保正文页 20pt 起）：")
            for ln in font_warns:
                lines.append("  - " + ln)
            lines.append("  建议：调整 FONT_PT 字典或在 spec.css/preset 中加大 --font-body 派生")
        # 5.4 溢出 / Action Title
        overflow_warns = [ln for ln in lines if "接近上限" in ln or "Action Title" in ln]
        if overflow_warns:
            lines.append("【溢出 / Action Title】标题即结论（动作标题原则）：")
            for ln in overflow_warns:
                lines.append("  - " + ln)
            lines.append("  建议：标题改为「动词+对象+结论」（例：算法平均时间复杂度为 O(n log n)）")
        # 5.5 生成建议（fail 时给"可继续生成"提示，避免用户直接放弃）
        if fails:
            lines.append("")
            lines.append("== 生成建议（不阻断生成；--check 仅校验用）==")
            lines.append("  - 业务上可继续生成 HTML（--check 仅是门禁报告，不改 build 行为）")
            lines.append("  - 整改优先级：密度 FAIL > 对比度 FAIL > 字号 WARN > 溢出 WARN")
            lines.append("  - 整改后重跑：build_deck.py --spec deck.json --check（仅门禁）")
            lines.append("  - 不愿整改可保留产物：build_deck.py --spec deck.json --out deck.html --dist deck.dist.html")

    return lines, fails, warns


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Generate a self-contained HTML slide deck.")
    ap.add_argument("--spec", help="Path to deck spec JSON")
    ap.add_argument("--out", help="Output .html path")
    ap.add_argument("--preset", default=None, help="Preset id (overrides spec)")
    ap.add_argument("--check", action="store_true", help="Run acceptance checks (density/typeface/contrast/overflow) and exit")
    ap.add_argument("--dist", help="Also write a stripped presentation-only copy (no editing UI) to this path")
    ap.add_argument("--template", default=None, choices=sorted(DECK_TEMPLATES),
                    help=f"Emit a course-type skeleton spec: {', '.join(sorted(DECK_TEMPLATES))}")
    ap.add_argument("--duration", type=int, default=90, help="Class minutes for --template sizing (base 90)")
    ap.add_argument("--spec-out", help="Output skeleton spec json path (with --template)")
    ap.add_argument("--split", type=int, default=0, metavar="N",
                    help="长 deck 拆分——每 N 页拆为一份子 spec（<spec_stem>_partK.json），不生成 HTML")
    ap.add_argument("--batch", action="store_true",
                    help="批量模式——--spec 指向一个目录，目录内每个 *.json spec 各自 build 到同名 .html（.dist 同名 .dist.html）")
    args = ap.parse_args(argv)

    # 骨架模式：--template 展开占位 spec，不生成 HTML
    if args.template:
        if not args.spec_out:
            print("ERROR: --template requires --spec-out", file=sys.stderr)
            return 2
        spec = template_spec(args.template, args.duration)
        Path(args.spec_out).write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"OK wrote skeleton spec {args.spec_out} "
              f"({len(spec['slides'])} slides, template={args.template}, duration={args.duration}min, "
              f"preset={spec['preset']})")
        return 0
    if not args.spec:
        print("ERROR: --spec required (or --template)", file=sys.stderr)
        return 2

    # 批量模式：--spec 为目录，逐个 *.json spec build 到同名 .html + .dist.html
    if args.batch:
        spec_dir = Path(args.spec)
        if not spec_dir.is_dir():
            print(f"ERROR: --batch 模式下 --spec 必须是目录: {args.spec}", file=sys.stderr)
            return 2
        specs = sorted(spec_dir.glob("*.json"))
        if not specs:
            print(f"ERROR: 目录内无 *.json spec: {spec_dir}", file=sys.stderr)
            return 2
        fails = 0
        for sp in specs:
            try:
                sub = json.loads(sp.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as e:
                print(f"[batch] SKIP {sp.name}: {e}", file=sys.stderr)
                fails += 1
                continue
            sub_pid = args.preset or sub.get("preset") or "academic-light"
            if sub_pid not in PRESETS:
                sub_pid = "academic-light"
            if validate_spec(sub):
                print(f"[batch] SKIP {sp.name}: spec 校验失败", file=sys.stderr)
                fails += 1
                continue
            html_out = sp.with_suffix(".html")
            html_out.write_text(build(sub, sub_pid, include_editor=True), encoding="utf-8")
            dist_out = sp.with_suffix(".dist.html")
            dist_out.write_text(build(sub, sub_pid, include_editor=False), encoding="utf-8")
            print(f"[batch] OK {sp.name} -> {html_out.name} + {dist_out.name} ({len(sub['slides'])} slides)")
        return 1 if fails else 0

    # 长 deck 拆分：--split N 输出子 spec 文件（不生成 HTML）
    if args.split and args.split > 0:
        try:
            spec_path = Path(args.spec)
            spec = json.loads(spec_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"ERROR: 读 spec 失败: {args.spec} ({e})", file=sys.stderr)
            return 2
        if validate_spec(spec):
            print("ERROR: spec 校验失败（拆分前）", file=sys.stderr)
            return 2
        slides = spec.get("slides", [])
        n = args.split
        parts = [slides[i:i + n] for i in range(0, len(slides), n)] or [[]]
        stem = spec_path.stem
        for k, part in enumerate(parts, 1):
            sub = {"meta": dict(spec.get("meta", {})), "preset": spec.get("preset", "academic-light"),
                   "slides": part}
            if spec.get("vars"):
                sub["vars"] = spec["vars"]
            out_p = spec_path.with_name(f"{stem}_part{k}.json")
            out_p.write_text(json.dumps(sub, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"[split] OK {out_p.name} ({len(part)} slides)")
        return 0

    # 读 spec：文件缺失/坏 JSON → ERROR + exit 2（不再 traceback）
    try:
        spec_path = Path(args.spec)
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"ERROR: spec 文件不存在: {args.spec}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as e:
        print(f"ERROR: spec 不是合法 JSON: {args.spec} ({e})", file=sys.stderr)
        return 2
    global SPEC_DIR
    SPEC_DIR = spec_path.resolve().parent
    pid = args.preset or spec.get("preset") or "academic-light"
    if pid not in PRESETS:
        print(f"WARN: unknown preset '{pid}', using default academic-light", file=sys.stderr)
        pid = "academic-light"

    # spec schema 前置校验：未知页型/缺标题/空 slides/非法 chart values → ERROR + exit 2
    spec_errs = validate_spec(spec)
    if spec_errs:
        print("ERROR: spec 校验失败:", file=sys.stderr)
        for e in spec_errs:
            print(f"  - {e}", file=sys.stderr)
        return 2

    if args.check:
        lines, fails, warns = check_deck(spec, pid)
        # 空 deck 防御：validate_spec 已拦截空 slides，此处双保险
        if not spec.get("slides"):
            fails += 1
            lines.append("[FAIL] 空 spec（无幻灯片）")
        print("\n".join(lines))
        return 1 if fails else 0

    doc = build(spec, pid, include_editor=True)
    out = args.out
    if not out:
        print("ERROR: --out required unless --check", file=sys.stderr)
        return 2
    Path(out).write_text(doc, encoding="utf-8")
    print(f"OK wrote {out} ({len(doc)} bytes, {len(spec.get('slides', []))} slides, preset={pid})")
    if args.dist:
        dist = build(spec, pid, include_editor=False)
        Path(args.dist).write_text(dist, encoding="utf-8")
        print(f"OK wrote {args.dist} (dist, no editing UI, {len(dist)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
