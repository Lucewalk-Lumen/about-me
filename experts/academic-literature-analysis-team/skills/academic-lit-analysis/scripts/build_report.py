#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_report.py —— 生成自包含静态 HTML 报告

用法:
    python3 build_report.py --topics topics.json [--network network.json] \
        --evolution evolution.json --out report.html

设计约束（均来自实测）:
  - `file://` 下 fetch() 被Fetch 标准拒绝（scheme 无定义 → network error），
    ES Module 亦被 CORS 拦截 → 报告必须自包含单文件，图表库源码内联。
  - 摘要截断会让 HTML 变大（实测 1240KB → 截断 200 字后 2772KB，净增 1532KB），
    因截断破坏 JSON 结构相似性 → 控制体积应"不进 HTML"而非"截断后进"。
  - 报告必须明示"这是关键词共现网络，非引文网络"（P0 阻断项 T-71）。
  - 不得以警告色呈现纯语言簇——那是算法的正确行为，不是异常。
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from collections import Counter

from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lit_core import EXIT, esc_json  # noqa: E402

# 主题命名：内置 OB/HRM 术语表 + 用户自定义 + 关键词回退
try:
    from topic_labels import (label_topic, NON_TOPIC_KEY, dedupe_labels,
                              detect_non_topic, disambiguate_concept_names)
except Exception:            # 命名模块缺失不应阻塞报告生成
    def label_topic(top_terms, user_labels=None):
        return "", "none"
    def dedupe_labels(names, top_terms_list):
        return list(names)
    def detect_non_topic(top_terms):
        return None
    def disambiguate_concept_names(names, top_terms_list):
        return list(names)
    NON_TOPIC_KEY = "其他·未归类文献"

CSS = """/* ══════════════════════════════════════════════════════════
   设计令牌
   ══════════════════════════════════════════════════════════ */
:root{
  /* 深色底 */
  --bg:#FFFFFF; --bg-2:#FAFAF8; --surface:#FFFFFF; --surface-2:#F7F7F4;
  --surface-3:#EFEFEA; --border:#E4E4DE; --border-2:#D2D2C9;
  /* 文字 */
  --tx:#1A1D21; --tx-2:#5A6169; --tx-3:#8A9099;
  /* 主色与强调（科技感：青蓝 + 品红双主色） */
  --ac:#0F7B8A; --ac-2:#5B4BC4; --ac-ink:#FFFFFF;
  --ac-soft:rgba(15,123,138,.09); --ac-line:rgba(15,123,138,.28);
  --mag:#D6336C; --amber:#B26B00; --lime:#2F7D32; --sky:#1C6FB8;
  /* 语义 */
  --ok:#1A7F5A; --warn:#B26B00; --dan:#C0392B;
  --ok-bg:rgba(26,127,90,.07); --warn-bg:rgba(178,107,0,.08);
  --dan-bg:rgba(192,57,43,.07);
  /* 间距与圆角 */
  --s1:4px; --s2:8px; --s3:12px; --s4:16px; --s5:22px; --s6:32px;
  --r1:6px; --r2:10px; --r3:16px;
  --sh:0 1px 2px rgba(20,25,35,.05), 0 4px 14px rgba(20,25,35,.06);
  --sh-sm:0 1px 2px rgba(20,25,35,.05);
  /* 高度：移动端优先给中等高度，桌面端由媒体查询放大。
     [!] 已知失效模式「共现网络画布太小，节点最后挤在一起」。根因：节点圆是**固定像素半径**
     （radiusOf 不乘 vk），而坐标随 fitView 的缩放 vk 走；画布越矮 → vk 越小 → 圆心越挤 →
     大节点互相压盖。故整体抬高画布高度（尤其上限），把 vk 抬起来即可显著拉开点距。
     本行是 v1 兜底令牌，v2 会在下方（约 553 行）再次覆盖，两者必须对齐，否则改了不生效。 */
  --canvas-h:clamp(460px, 62vh, 800px);
  --font:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",
         "Segoe UI",Roboto,sans-serif;
  --mono:ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,monospace;
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{
  margin:0;background:var(--bg);color:var(--tx);
  font-family:var(--font);font-size:15px;line-height:1.7;
  -webkit-font-smoothing:antialiased;
}

/* ── 排版 ── */
h1{
  font-size:clamp(21px,4.6vw,28px);font-weight:700;letter-spacing:-.02em;
  margin:0 0 var(--s2);line-height:1.3;color:var(--tx);
}
h2{
  font-size:clamp(16px,3.4vw,20px);font-weight:680;letter-spacing:-.01em;
  margin:var(--s6) 0 var(--s3);padding-bottom:var(--s2);
  border-bottom:1px solid var(--border);
  display:flex;align-items:center;gap:var(--s2);flex-wrap:wrap;
}
h2 .n{
  font-size:11px;font-weight:700;letter-spacing:.04em;
  color:var(--ac);background:var(--ac-soft);
  border:1px solid var(--ac-line);border-radius:20px;
  padding:2px 9px;flex:none;font-family:var(--mono);
}
h3{font-size:15px;font-weight:640;margin:var(--s4) 0 var(--s2)}
.sub{
  color:var(--tx-2);font-size:13px;margin-bottom:var(--s4);
  display:flex;flex-wrap:wrap;gap:var(--s1) var(--s3);align-items:baseline;
}
.sub code{font-family:var(--mono);font-size:12px;background:var(--surface-2);
  border:1px solid var(--border);border-radius:var(--r1);padding:1px 5px}
.note{font-size:12.5px;color:var(--tx-2);line-height:1.65;margin:var(--s2) 0}
.note code{font-family:var(--mono);font-size:11.5px;background:var(--surface-2);
  padding:0 4px;border-radius:3px;border:1px solid var(--border)}
a{color:var(--ac)}

/* ── 目录 ── */
.toc{
  background:var(--surface-2);
  border:1px solid var(--border);border-radius:var(--r2);
  padding:var(--s3) var(--s4);margin:0 0 var(--s5);
}
/* [!]「目录」小标题必须与全站令牌体系一致：若沿用旧的灰令牌与偏小字号，
   会成为全站「颜色不跟队、字号偏小」的孤立标题，目录观感与正文脱节。
   现统一到 v2 令牌：
   颜色取正文本色（与 .brand 同族），字号提到 13px，去掉多余的字母间距。 */
.toc-t{font-size:13px;font-weight:700;color:var(--tx);
  letter-spacing:.06em;margin-bottom:var(--s2)}
.toc ol{margin:0;padding:0;list-style:none;columns:2;column-gap:var(--s4)}
@media(min-width:860px){.toc ol{columns:3}
}
.toc li{margin:0 0 2px;font-size:13px;break-inside:avoid}
.toc a{color:var(--tx-2);text-decoration:none;display:flex;gap:7px;
  align-items:baseline;padding:4px 6px;border-radius:var(--r1);
  min-height:28px;transition:background .12s,color .12s}
.toc a:hover{color:var(--ac);background:var(--ac-soft)}
.toc a .n{color:var(--tx-3);font-family:var(--mono);font-size:11px;flex:none}
.toc li.g a{font-weight:660;color:var(--tx)}

/* ── 卡片与网格 ── */
.card{
  background:var(--surface);
  border:1px solid var(--border);border-radius:var(--r2);
  padding:var(--s4);margin-bottom:var(--s3);
  box-shadow:var(--sh-sm);transition:border-color .14s;
}
.card:hover{border-color:var(--border-2)}
.grid{display:grid;gap:var(--s3)}
.g4{grid-template-columns:repeat(2,1fr)}
@media(min-width:720px){.g4{grid-template-columns:repeat(4,1fr)}
}
.kpis{display:grid;gap:var(--s2);grid-template-columns:repeat(2,1fr);
  margin:0 0 var(--s3)}
.kpis.k3{grid-template-columns:repeat(2,1fr)}
@media(min-width:720px){.kpis.k3{grid-template-columns:repeat(3,1fr)}
}
@media(min-width:720px){.kpis{grid-template-columns:repeat(4,1fr)}
}

/* ── KPI ── */
.kpi{
  background:var(--surface-2);
  border:1px solid var(--border);border-radius:var(--r2);
  padding:var(--s3);position:relative;overflow:hidden;
}
.kpi::before{content:"";position:absolute;inset:0 auto 0 0;width:3px;
  background:linear-gradient(180deg,var(--ac),var(--ac-2));opacity:.75}
.kpi .l{font-size:11.5px;color:var(--tx-2);margin-bottom:3px;line-height:1.4}
.kpi .v{font-size:clamp(18px,4vw,24px);font-weight:700;line-height:1.15;
  font-family:var(--mono);letter-spacing:-.02em;
  overflow-wrap:anywhere}
.kpi.ok::before{background:var(--ok)}
.kpi.warn::before{background:var(--warn)}
.kpi.danger::before{background:var(--dan)}
.kpi.ok .v{color:var(--ok)}
.kpi.warn .v{color:var(--warn)}
.kpi.danger .v{color:var(--dan)}

/* ── 标签 ── */
.tag{display:inline-flex;align-items:center;padding:2px 9px;border-radius:20px;
  font-size:11.5px;font-weight:500;line-height:1.6;
  background:var(--surface-2);color:var(--tx-2);
  border:1px solid var(--border);white-space:nowrap}
.tag.zh{background:var(--ac-soft);color:var(--ac);border-color:var(--ac-line)}
.tag.en{background:rgba(91,75,196,.08);color:#4C3EB0;
  border-color:rgba(91,75,196,.24)}
.tag.mixed{background:var(--warn-bg);color:var(--warn);
  border-color:rgba(178,107,0,.26)}

/* ── 提示条 ── */
.notice{
  background:var(--ac-soft);border:1px solid var(--ac-line);
  border-left:3px solid var(--ac);border-radius:var(--r1);
  padding:var(--s3) var(--s4);margin:0 0 var(--s4);
  font-size:13.5px;color:var(--tx-2);line-height:1.65;
}
.notice.warn{background:var(--warn-bg);border-color:rgba(255,180,84,.3);
  border-left-color:var(--warn)}
.notice.danger{background:var(--dan-bg);border-color:rgba(255,107,122,.3);
  border-left-color:var(--dan)}
.notice b{color:var(--tx)}
.readout{
  background:var(--ok-bg);border:1px solid rgba(26,127,90,.2);
  border-left:3px solid var(--ok);border-radius:var(--r1);
  padding:var(--s3) var(--s4);margin:0 0 var(--s3);
  font-size:13px;line-height:1.7;color:var(--tx-2);
}
.readout b{color:var(--tx)}
.readout ul{margin:0;padding-left:18px}
.readout li{margin:5px 0}
.readout li::marker{color:var(--ok)}

/* ── 结论摘要 ── */
.summary{
  background:var(--ac-soft);
  border:1px solid var(--ac-line);border-left:3px solid var(--ac);
  border-radius:var(--r2);padding:var(--s4);margin:0 0 var(--s5);
  box-shadow:var(--sh-sm);
}
/* [!] 这里曾写 `padding:0`。它特异性(.class h2)高于通用 `h2`，
   把 v2 的 `h2{padding-left:14px}` 覆盖回 0 —— 而 `h2::before` 那根
   青→靛渐变竖条仍绝对定位在 left:0，于是直接压在「结」字上。
   修法：保留左侧 14px 内边距，竖条与文字重新错开；
   其余（去下边框、改字号/颜色）保持不变。 */
.summary h2{margin:0 0 var(--s3);border:0;padding:0 0 0 14px;font-size:16px;
  -webkit-text-fill-color:var(--tx);background:none;color:var(--ac)}
.summary ul{margin:0;padding-left:20px}
.summary li{margin:7px 0;line-height:1.75;font-size:14px}
.summary li::marker{color:var(--ac)}

/* ── 图表区：canvas + 工具条 ── */
.toolbar{
  display:flex;align-items:center;flex-wrap:wrap;gap:var(--s2);
  padding:var(--s2);background:var(--surface-2);
  border:1px solid var(--border);border-radius:var(--r2);
  margin:0 0 var(--s3);font-size:12.5px;
}
@media(min-width:760px){.toolbar{padding:var(--s2) var(--s3)}
}
.viewlbl{font-size:11px;color:var(--tx-3);margin:0 2px 0 var(--s2);
  letter-spacing:.06em;white-space:nowrap}

/* 触摸目标不小于 36px，同时兼顾鼠标端的紧凑 */
button.viewbtn,button.rstbtn{
  font:inherit;font-size:12.5px;font-weight:520;
  min-height:34px;padding:5px 12px;cursor:pointer;
  background:var(--surface-3);color:var(--tx-2);
  border:1px solid var(--border-2);border-radius:var(--r1);
  transition:all .12s ease;white-space:nowrap;
}
button.viewbtn:hover,button.rstbtn:hover{
  background:var(--ac-soft);border-color:var(--ac-line);color:var(--ac);
}
button.viewbtn.on{
  background:var(--ac);color:var(--ac-ink);
  border-color:var(--ac);font-weight:660;
}
button.rstbtn{background:transparent}
button:focus-visible{outline:2px solid var(--ac);outline-offset:2px}
.viewtune{display:inline-flex;align-items:center;gap:6px;font-size:12px;
  color:var(--tx-2);margin:0 2px 0 var(--s2);white-space:nowrap;
  min-height:34px}
.viewtune input{width:82px;accent-color:var(--ac)}

/* 画布容器：相对定位，图例/提示叠在画布内 */
.canvaswrap{position:relative;background:#FFFFFF;
  border:1px solid var(--border);border-radius:var(--r2);
  overflow:hidden}
canvas{display:block;width:100%;
  height:var(--canvas-h, 400px);   /* 变量缺失时回退，避免画布高度为 0 */
  min-height:280px;
  touch-action:pan-y pinch-zoom}
@media(min-width:900px){:root{--canvas-h:clamp(560px,76vh,880px)}
}

/* 叠加在画布上的图例与操作提示 */
.overlay-ui{position:absolute;left:0;right:0;pointer-events:none;
  font-size:11px;line-height:1.6;color:var(--tx-2)}
.overlay-ui.top{top:0;padding:8px 10px;
  background:linear-gradient(180deg,rgba(255,255,255,.94),transparent)}
.overlay-ui.bottom{bottom:0;padding:20px 10px 8px;
  background:linear-gradient(0deg,rgba(255,255,255,.96),transparent)}
.overlay-ui .it{display:inline-flex;align-items:center;gap:5px;
  margin-right:8px;margin-bottom:2px;white-space:nowrap;
  background:rgba(255,255,255,.9);border:1px solid var(--border);
  border-radius:20px;padding:2px 9px}
.overlay-ui .sw{width:9px;height:9px;border-radius:50%;flex:none;
  box-shadow:0 0 0 1px rgba(0,0,0,.1)}
.overlay-ui .keys{margin-top:4px;color:var(--tx-3);font-size:10.5px;
  font-family:var(--mono)}
.overlay-ui .keys b{color:var(--ac);font-weight:600}
.overlay-ui .it.clickable{pointer-events:auto;cursor:pointer}
.overlay-ui .it.clickable:hover{border-color:var(--ac-line);color:var(--ac)}

/* 密度视图的竖向色标（放在画布右侧独立条带，绝不压在热区之上）。
   采用竖向而非横向：横向色带贴着画布底边，会与底部快捷键提示条
   争同一条底边、且直接叠在热区之上，遮挡密度内容。
   竖向放在右缘后，drawDensity 通过 overlayInsets() 给绘图区让出等宽条带，
   色标与图形各占其位、互不遮挡。上下留 44px 是为了避开 .overlay-ui 两条覆盖层。 */
.dens-legend{position:absolute;right:8px;top:44px;bottom:44px;
  display:flex;flex-direction:column;align-items:center;justify-content:center;
  gap:4px;pointer-events:none;z-index:2}
.dens-legend .dl-bar{flex:1 1 auto;width:12px;min-height:56px;max-height:200px;
  border-radius:3px;border:1px solid var(--border);
  box-shadow:0 0 0 1px rgba(0,0,0,.06)}
.dens-legend .dl-top,.dens-legend .dl-bot{font-size:10px;line-height:1;
  color:var(--tx-3);font-weight:600}
.dens-legend .dl-cap{font-size:10px;line-height:1.2;color:var(--tx-3);
  writing-mode:vertical-rl;letter-spacing:1px}

/* 画布外的图例（主题色） */
.legend{display:flex;flex-wrap:wrap;gap:5px 6px;margin:var(--s2) 0}
.lg-item{
  display:inline-flex;align-items:center;gap:6px;font-size:12px;
  color:var(--tx-2);cursor:pointer;padding:4px 9px;border-radius:20px;
  border:1px solid var(--border);background:var(--surface-2);
  min-height:30px;transition:all .12s;
}
.lg-item:hover{border-color:var(--ac-line);color:var(--ac)}
.lg-item.on{background:var(--ac-soft);border-color:var(--ac-line);
  color:var(--ac);font-weight:600}
.lg-item .sw{width:11px;height:11px;border-radius:3px;flex:none;
  box-shadow:0 0 0 1px rgba(0,0,0,.1)}

/* 侧栏（悬停详情） */
.side{margin-top:var(--s3);background:var(--surface-2);
  border:1px solid var(--border);border-radius:var(--r2);
  padding:var(--s3);min-height:52px}
.side h4{margin:0 0 6px;font-size:13px;color:var(--ac);font-weight:640}
.kws{display:flex;flex-wrap:wrap;gap:5px}
.kws .k{display:grid;grid-template-columns:auto 1fr auto;gap:2px 6px;
  align-items:center;font-size:11.5px;padding:4px 8px;
  border-radius:var(--r1);background:var(--surface-3);
  border:1px solid var(--border);color:var(--tx-2);
  cursor:pointer;min-width:0}
.kws .k:hover{border-color:var(--ac-line);color:var(--ac);
  background:var(--ac-soft)}
.kws .k i{width:8px;height:8px;border-radius:2px;flex:none;
  grid-row:span 2}
.kws .k .kt{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
  min-width:0}
.kws .k .kd{font-family:var(--mono);font-size:9.5px;opacity:.7;flex:none}
.kws .k .kb{grid-column:2/4;font-size:10.5px;color:var(--tx-3);
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap}

/* 侧栏操作提示 */
.hint{font-size:11.5px;color:var(--tx-3);padding:7px 10px;
  background:var(--surface-2);border:1px solid var(--border);
  border-radius:var(--r1);margin:var(--s2) 0 0;line-height:1.6}

/* ── 关键词：网格布局，避免平铺拥挤 ── */
.kwcloud{display:grid;gap:var(--s2);margin:var(--s2) 0}
@media(min-width:860px){.kwcloud{grid-template-columns:1fr}
}
.kwcloud .k{
  display:inline-flex;align-items:baseline;gap:4px;
  padding:4px 11px;border-radius:20px;font-size:12px;
  background:var(--surface-2);border:1px solid var(--border);
  color:var(--tx-2);cursor:pointer;min-height:30px;
  transition:all .12s ease;
}
.kwcloud .k:hover{border-color:var(--ac-line);color:var(--ac);
  background:var(--ac-soft)}
.kwcloud .k em{font-style:normal;font-size:9.5px;opacity:.6;
  font-family:var(--mono)}
.kwcloud .k.t1{font-size:14px;font-weight:680;color:var(--ac);
  background:var(--ac-soft);border-color:var(--ac-line)}
.kwcloud .k.t2{font-size:12.5px;color:var(--tx)}
.kwcloud .k.t3{font-size:11.5px}
.kwcloud .k.off{opacity:.3;text-decoration:line-through}

/* ── 表格：统一 .tw 容器 + 移动端横向滚动 ── */

/* 关键：窄屏下表格必须**在自己的容器内**滚动，
   否则会把整页撑宽、出现表格跨页面。 */
.tw{
  overflow-x:auto;-webkit-overflow-scrolling:touch;
  border:1px solid var(--border);border-radius:var(--r2);
  margin:var(--s2) 0;background:var(--surface);
  max-width:100%;
}
table.mx{width:100%;max-width:100%;border-collapse:separate;
  border-spacing:0;font-size:12.5px;table-layout:fixed;min-width:0}
table.mx.cols-auto{table-layout:auto;min-width:min(100%,460px)}

/* 单元格内容过长时按比例截断而非撑宽表格 */
table.mx td,table.mx th{overflow:hidden;text-overflow:ellipsis}
table.mx td.wrap-cell{white-space:normal;overflow:visible}
table.mx th{
  background:var(--surface-2);color:var(--tx-2);font-weight:640;
  text-align:left;padding:9px 11px;white-space:nowrap;
  border-bottom:1px solid var(--border);font-size:12px;
  position:sticky;top:0;z-index:2;
}
table.mx td{padding:8px 11px;border-bottom:1px solid var(--surface-2);
  vertical-align:top}
table.mx tbody tr:last-child td{border-bottom:0}
table.mx tbody tr:hover{background:var(--surface-2)}
table.mx td:first-child{color:var(--tx)}
table.mx .num,table.mx th.num{text-align:right;font-family:var(--mono);
  font-size:11.5px;white-space:nowrap}
/* ── 全文对齐规范（文本列与数值列必须统一区分对齐）──
   ① 文本列（主题/关键词/作者/机构/说明）→ 左（默认，无需类）
   ② 数值列（篇数/占比/年份/度数/中心性/Q 值）→ 右（.num，等宽 + tabular-nums）
   ③ 分类/状态/标签列（语种/达标状态/是否桥接词）→ 中（.ctr）
   关键约束：**同一列的 th 与 td 必须同对齐**。故生成 HTML 时数值列的 th 与 td
   都要带 .num、分类列的 th 与 td 都要带 .ctr；只要有一侧漏写，表头与数据就会错位。
   例外（刻意不统一）：热力图/矩阵的格子数值保持居中 —— 那是"色块"语义，右对齐
   会让数字脱离色块中心，反而更难读（见下方 .hm/.ht 规则）。 */
table.mx .ctr,table.mx th.ctr{text-align:center}

/* 首列在窄屏允许换行，避免整表被撑宽 */
@media(max-width:560px){table.mx th,table.mx td{padding:7px 9px}
table.mx td:first-child,table.mx th:first-child{white-space:normal}
}
table.mx.nopad td{border:0;padding:6px 9px 6px 0;
  border-bottom:1px solid var(--surface-2);vertical-align:top}
table.mx.nopad td:first-child{font-weight:640;width:76px;
  color:var(--tx);white-space:nowrap}
table.mx.nopad td:nth-child(2){color:var(--ac);font-weight:520;
  width:118px;white-space:normal}
table.mx .thn{display:block;font-family:var(--mono);font-size:10px;
  color:var(--tx-3);letter-spacing:.04em}
table.mx .tht{display:block;font-size:11.5px;font-weight:660;color:var(--tx);
  max-width:96px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
table.mx.heat td{text-align:center;font-family:var(--mono);font-size:11.5px}

/* ── 时间线 ── */

/* 窄屏时年份轴退化为纯记录 */

@media(min-width:780px){/*宽屏：词名右对齐贴近年份轴（与坐标刻度的视觉起点一致） */
}
.burst-mark{color:var(--mag);font-size:9px;margin-left:3px}

/* ── 柱状图（发文量） ── */
.pline-wrap{margin:0 0 var(--s3);padding:var(--s2) 0 0;
  background:var(--surface-2);border:1px solid var(--border);
  border-radius:var(--r2);overflow:hidden}
.pline{display:block;width:100%;height:auto}
/* 窄屏下的最小宽度统一在文件末尾「窄屏 / 移动端」段落里定义，
   避免同一属性在两个断点里各写一次、互相覆盖。 */
.yrbar{display:inline-block;width:min(120px,40vw);height:7px;
  border-radius:4px;vertical-align:middle;
  /* 时间色带统一到报告设计语言：青（早）→ 靛（中）→ 品红（晚）。
     与画布上 yearColor()/时间线 timeColor() 完全同源（见 JS_NET）。 */
  background:linear-gradient(90deg,#06B6D4,#4F46E5,#D6336C)}

/* 横向柱（时效分布） */
.hbars{display:flex;align-items:flex-end;gap:3px;height:110px;
  padding:6px 0 0;border-bottom:1px solid var(--border);overflow-x:auto}
.hbars .b{flex:1 1 0;min-width:5px;
  background:linear-gradient(180deg,var(--amber),#E07A3C);
  border-radius:3px 3px 0 0;opacity:.85;min-height:3px}
.hbars .b:hover{opacity:1}

/* ── 参数块 / 小标签 ── */
.params{display:grid;gap:var(--s2);
  grid-template-columns:repeat(2,1fr);
  background:var(--surface-2);border:1px solid var(--border);
  border-radius:var(--r2);padding:var(--s3);margin:0 0 var(--s3)}
@media(min-width:720px){.params{grid-template-columns:repeat(5,1fr)}
}
.params .p{display:flex;flex-direction:column;gap:2px;min-width:0}
.params .p .k{font-size:11px;color:var(--tx-3)}
.params .p .v{font-size:13.5px;font-weight:660;color:var(--ac);
  font-family:var(--mono);overflow-wrap:anywhere;
  /* 对齐规范：数值用等宽数字，纵向逐位对齐，避免"1 与 8"宽度不同造成参差 */
  font-variant-numeric:tabular-nums}
.sublab{font-size:12.5px;color:var(--tx-2);margin:0 0 var(--s2);
  display:flex;align-items:baseline;gap:6px;flex-wrap:wrap}
.sublab b{color:var(--tx);font-weight:640}
.hintline{font-size:11.5px;color:var(--tx-3);line-height:1.55;margin:4px 0 0}

/* ── 主题卡 ── */
.tname{font-size:15.5px;font-weight:680;color:var(--tx);line-height:1.4;
  margin-bottom:6px;letter-spacing:-.01em}
.terms{font-size:11.5px;color:var(--tx-3);margin-bottom:6px}


/* 年度分布迷你条形图（突现检测表用）。
   [!] 这里必须给 .spark 一个**显式高度**：此前容器没有高度，
   而条用 height:%，父高 auto → 百分比无参照、条全部塌成 0，
   表格看上去就是"没有内容"。 */
.spark{display:flex;align-items:flex-end;gap:2px;height:26px;min-width:96px}
.spark .sb{flex:1 1 0;min-width:2px;border-radius:1.5px 1.5px 0 0;
  background:linear-gradient(180deg,var(--in),var(--cy));opacity:.85}
.spark .sb.zero{height:1px!important;background:var(--border-2);opacity:.5}
.spark .sb:hover{opacity:1}

/* 突现检测表：列宽由 colgroup 固定，表头与数据必然同列同宽。
   自动列宽下中文表头（「峰值 df」「基线均值」）会把列撑开，
   内容却比表头窄，看上去就像数据没对齐表头。 */
table.mx.bstab{table-layout:fixed;width:100%;min-width:748px}
table.mx.bstab td,table.mx.bstab th{padding:8px 9px}
table.mx.bstab .cft{text-align:center;font-size:var(--fs-xs);color:var(--ink-2)}
table.mx.bstab .spkcell{padding-left:10px;overflow:visible}
table.mx.bstab td.kwc{font-weight:560;overflow-wrap:anywhere;white-space:normal}
table.mx.bstab th:nth-child(n+2),table.mx.bstab td:nth-child(n+2){text-align:right}
table.mx.bstab th:nth-child(7),table.mx.bstab td:nth-child(7),
table.mx.bstab th:nth-child(8),table.mx.bstab td:nth-child(8){text-align:center}
.chips{display:flex;flex-wrap:wrap;gap:5px}
.chip{display:inline-block;padding:2px 9px;border-radius:var(--r1);
  font-size:11.5px;color:var(--tx-2);background:var(--surface-2);
  border:1px solid var(--border);white-space:nowrap}
.chip:hover{background:var(--ac-soft);border-color:var(--ac-line);
  color:var(--ac)}

/* ── 可折叠方法说明 ── */

/* 图表区左右分栏：图表占主区，侧栏放悬停详情与解读 */
@media(min-width:1000px){/* 宽屏：图与侧栏并排，图占约 78% */
}

/* 表格：统一行高与间距，消除"有的宽有的窄" */
table.mx{table-layout:auto;width:100%}
table.mx th,table.mx td{height:34px}
table.mx th{line-height:1.45}
table.mx td{line-height:1.5}
table.mx th + th, table.mx td + td{white-space:normal}
.tw + .tw{margin-top:0}
.card > .tw:last-child{margin-bottom:0}
.methodbox{background:var(--surface-2);border:1px solid var(--border);
  border-radius:var(--r2);padding:0 var(--s3);margin:0 0 var(--s4);
  font-size:12.5px}
.methodbox summary{cursor:pointer;padding:10px 0;color:var(--tx-2);
  font-weight:560;list-style:none;min-height:36px;align-items:center;
  display:flex}
.methodbox summary::-webkit-details-marker{display:none}
.methodbox summary::before{content:"▸";color:var(--ac);margin-right:8px;
  display:inline-block;transition:transform .15s}
.methodbox[open] summary::before{transform:rotate(90deg)}
.methodbox summary:hover{color:var(--ac)}
.methodbody{padding:2px 0 12px;color:var(--tx-2);line-height:1.7;
  border-top:1px solid var(--border)}

/* ══════════════════════════════════════════════════════════
   v2 视觉体系：白底科技感 + 左侧导航 + 右侧内容
   ──────────────────────────────────────────────────────────
   设计目标（全部来自用户明确要求）：
     · 白底为背景的科技感，不要深色；
     · 左右分栏：左导航常驻，右侧给图表更大的显示空间；
     · 字号随内容与视口自适应，不再出现「小字撑不满、大字挤成柱」。
   实现取舍：
     · 所有尺寸走 clamp()/minmax()，不写死像素，窄屏自动降级为单列；
     · 「科技感」由**克制的三件套**给出——极淡网格底、渐变强调色、
       玻璃卡+发丝边框，而不是加满发光特效（那会牺牲可读性与打印质量）。
   ══════════════════════════════════════════════════════════ */
:root{
  /* 白底分层：底 < 卡 < 卡内浮层 */
  --w0:#FFFFFF; --w1:#FCFCFE; --w2:#F7F8FC; --w3:#EFF1F8;
  --line:rgba(15,23,42,.085); --line-2:rgba(15,23,42,.16);
  --ink:#0F172A; --ink-2:#475569; --ink-3:#8B96A8;
  /* 科技感强调色：青 → 靛 → 品红 */
  --cy:#06B6D4; --in:#4F46E5; --mg:#D6336C;
  --grad:linear-gradient(135deg,#06B6D4 0%,#4F46E5 52%,#D6336C 100%);
  --grad-soft:linear-gradient(135deg,rgba(6,182,212,.10),rgba(79,70,229,.10) 52%,rgba(214,51,108,.10));
  --glow:0 0 0 1px rgba(79,70,229,.10), 0 18px 40px -22px rgba(79,70,229,.35);
  --shell-max:1560px;
  /* 版式尺度：全部 clamp，随视口平滑变化 */
  --fs-base:clamp(14px, .34vw + 13.1px, 15.5px);
  --fs-h1:clamp(21px, 1.5vw + 15px, 30px);
  --fs-h2:clamp(16.5px, .62vw + 14.3px, 20.5px);
  --fs-h3:clamp(14.5px, .30vw + 13.6px, 16.5px);
  --fs-sm:clamp(12px, .20vw + 11.4px, 13px);
  --fs-xs:clamp(11px, .18vw + 10.5px, 12px);
  /* 图表高度也随视口走 —— 这是"图表要有更大显示空间"的直接落点。
     [!] 这一处在**源序上晚于**上面的 v1 令牌与 900px 媒体查询，同特异度下由它生效，
     即桌面端的真实取值就在这里。为避免网络节点拥挤，上限从 640px 抬到 880px、
     下限抬到 560px（≥ 任务要求的 520px 下限）：57+ 节点的网络在大屏上能铺得更开。 */
  --canvas-h:clamp(560px, 76vh, 880px);
  /* 页头基线：左品牌栏与右「标题+副标题」共用同一高度，桌面端两块底边对齐 */
  --head-h:90px;
}

/* 极淡点阵网格 + 两团极低透明度辉光：科技感来源，打印时会被移除 */
body{
  background:var(--w0);
  background-image:
    radial-gradient(760px 420px at 12% -6%, rgba(6,182,212,.055), transparent 62%),
    radial-gradient(680px 380px at 92% 2%, rgba(79,70,229,.05), transparent 60%),
    radial-gradient(circle at 1px 1px, rgba(15,23,42,.045) 1px, transparent 0);
  background-size:auto, auto, 22px 22px;
  background-attachment:fixed, fixed, scroll;
  font-size:var(--fs-base);
}
h1{font-size:var(--fs-h1)}
h2{font-size:var(--fs-h2)}
h3{font-size:var(--fs-h3)}
.note,.hintline{font-size:var(--fs-sm)}

/* 标题左边加一条渐变竖条 —— 比整块底色更轻，也更像工具而非宣传页 */
h2{position:relative;padding-left:14px}
h2::before{content:"";position:absolute;left:0;top:.18em;bottom:.42em;width:3px;
  border-radius:2px;background:var(--grad)}
h2 .n{background:var(--grad);color:#fff;border:0;font-weight:700;
  box-shadow:0 4px 12px -6px rgba(79,70,229,.75)}

/* ── 分栏骨架：左导航 + 右内容 ── */
.shell{display:grid;grid-template-columns:266px minmax(0,1fr);gap:var(--s5);
  max-width:var(--shell-max);margin:0 auto;padding:var(--s4) var(--s4) 40px;
  align-items:start}
.main{min-width:0}

/* 关键：允许内部 SVG/表格收缩，否则会撑破栅格 */
.side{position:sticky;top:var(--s3);align-self:start;
  max-height:calc(100vh - 2 * var(--s3));overflow:auto;overscroll-behavior:contain;
  scrollbar-width:thin}
/* [!] 左品牌栏与右侧「h1 + 副标题」块此前**高度不等**——
   两块内容行数不同（左 2 行 / 右 2 行但字号差一截），又没有共用高度，
   于是各自贴着顶部排版，下边框一高一低，视觉基线错位。
   修法：给两块同一个 min-height、内容底对齐、同一条下边框，
   桌面端（≥1080px，两栏并排）两块的底边因此落在同一条水平线上。
   窄屏退化为单栏堆叠，min-height 归零，不留下无谓空档。 */
.brand{display:flex;flex-direction:column;justify-content:flex-end;gap:3px;
  margin:0 0 var(--s3);padding:0 0 var(--s3);border-bottom:1px solid var(--line);
  min-height:var(--head-h)}
.head{display:flex;flex-direction:column;justify-content:flex-end;
  margin:0 0 var(--s3);padding:0 0 var(--s3);border-bottom:1px solid var(--line);
  min-height:var(--head-h)}
.head h1{margin:0}
.head .sub{margin:var(--s2) 0 0}
.brand b{font-size:15px;letter-spacing:-.01em}
.brand span{color:var(--ink-3);font-size:var(--fs-xs);font-family:var(--mono)}

/* 侧栏目录：单列竖排 + 当前项高亮 */
.side .toc{position:static;margin:0;padding:0;background:none;border:0}
.side .toc ol{columns:1!important}
.side .toc li a{padding:5px 9px;border-radius:8px;font-size:var(--fs-sm)}
.side .toc a:hover{background:var(--grad-soft);color:var(--in)}
.side .toc li.on a{background:var(--grad-soft);color:var(--in);font-weight:650}
@media(max-width:1080px){.shell{grid-template-columns:1fr;padding:var(--s3)}
.side{position:static;max-height:none;margin-bottom:var(--s4)}
/* 单栏堆叠时两块页头不再需要共用高度（见 .brand 注释） */
.brand,.head{min-height:0}
.side .toc{background:var(--w2);border:1px solid var(--line);
    border-radius:14px;padding:var(--s3) var(--s4)}
.side .toc ol{columns:2!important}
}
@media(max-width:560px){.side .toc ol{columns:1!important}
}

/* ── 卡片：玻璃感（发丝边框 + 双层柔和阴影），白底上不糊 ── */
.card{background:var(--w0);border:1px solid var(--line);border-radius:16px;
  box-shadow:0 1px 2px rgba(15,23,42,.035), 0 14px 34px -26px rgba(15,23,42,.35);
  transition:border-color .18s ease, box-shadow .18s ease}
.card:hover{border-color:var(--line-2);box-shadow:var(--glow)}
.kpi{background:var(--w0);border:1px solid var(--line);border-radius:14px;
  box-shadow:0 1px 2px rgba(15,23,42,.035)}
.kpi .l{color:var(--ink-3);font-size:var(--fs-xs);letter-spacing:.02em}
.kpi .v{font-family:var(--mono);font-size:clamp(15px,1.1vw + 12px,20px);
  font-variant-numeric:tabular-nums}

/* ── 主题卡：每条主题有自己的颜色（与画布节点同源） ── */
.tcard{position:relative;overflow:hidden}
.tcard::before{content:"";position:absolute;inset:0 auto 0 0;width:4px;
  background:var(--tc,var(--in));opacity:.9}
.tcard .tname{font-size:var(--fs-h3);font-weight:660;display:flex;
  align-items:center;gap:8px;margin:0 0 6px}
.tdot{width:10px;height:10px;border-radius:3px;flex:none;
  box-shadow:0 0 0 3px rgba(15,23,42,.05)}

/* 百分比条：数字直接写在条尾，颜色 = 主题色。
   [!] 百分比条不可过高：height:26px + 上下 margin(2/8) 竖向占比过大，
   把主题卡的标题/标签挤成一条细缝。现收窄到 18px 并把上下间距收到 1/6，
   同时保留条内数字（.pbar b 仍 12px mono）—— 条变矮但数字仍清晰可读。 */
.pbar{position:relative;display:flex;align-items:center;gap:9px;
  height:18px;margin:1px 0 6px;border-radius:6px;background:var(--w3);
  padding:0 9px 0 0;overflow:hidden}
.pbar i{height:100%;border-radius:6px;min-width:4px;
  transition:width .35s cubic-bezier(.4,0,.2,1)}
.pbar b{font-family:var(--mono);font-size:var(--fs-xs);
  font-variant-numeric:tabular-nums;margin-left:auto;z-index:1}
/* 主题卡的标签行（语种/篇数/年份）：抽成 .tmeta 以便窄屏统一收紧纵向间距
   （此前是内联样式，媒体查询无从覆盖）。 */
.tmeta{display:flex;gap:6px;flex-wrap:wrap;align-items:center;margin:2px 0 8px}
.chipnote{font-size:var(--fs-xs);color:var(--ink-3);margin:0 0 5px}
.chips{gap:6px}
.chip{background:var(--w2);border:1px solid var(--line);border-radius:999px;
  font-size:var(--fs-sm);padding:3px 10px;white-space:normal}

/* ── 主题总览表：卡前列出全部主题，一屏扫完「有几个、哪个大、哪个新」 ──
   宽表靠外层 .tw 横向滚动（_wrap_tables 自动套），页面本身不被撑宽。 */
.tovcap{font-size:var(--fs-sm);font-weight:640;color:var(--ink);margin:0 0 6px;
  display:flex;gap:8px;align-items:baseline;flex-wrap:wrap}
table.tov td{vertical-align:middle}
table.tov .tovlink{display:inline-flex;align-items:center;gap:6px;max-width:100%;
  color:var(--tx);text-decoration:none}
table.tov .tovlink:hover .tovw{color:var(--ac);text-decoration:underline}
.tovn{font-family:var(--mono);font-size:10.5px;color:var(--tx-3);flex:none}
.tovw{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:200px;
  font-weight:600}
.tovb{display:inline-block;vertical-align:middle;width:56px;height:8px;margin-right:6px;
  border-radius:6px;background:var(--w3);overflow:hidden}
.tovb i{display:block;height:100%;border-radius:6px;min-width:3px}
.tovp{font-family:var(--mono);font-size:var(--fs-xs);color:var(--tx-2)}
.tovkw{color:var(--ink-2);white-space:normal;max-width:280px}
.tovlang{font-size:10.5px;padding:1px 7px}
/* 代表词 chip：强调（更大更深、描边取主题色 --tc，与卡片/画布同源） */
.tcard .chiprep{font-size:var(--fs-sm);padding:4px 11px;font-weight:640;
  border-color:var(--tc,var(--ac-line));color:var(--tx);background:var(--w2)}
.chips.crep{gap:6px;margin-bottom:6px}
/* 长尾词 chip：弱化；网格均分列宽，消除长短词参差错乱 */
.chiptail{font-size:11.5px;padding:2px 8px;color:var(--ink-3)}
.chips.ctail{display:grid;grid-template-columns:repeat(auto-fill,minmax(84px,1fr));gap:5px}
/* 卡内关键词折叠面板：默认收起，展开不改动卡片配色 */
.tfold{margin:2px 0 0;border-top:1px dashed var(--line)}
.tfold>summary{cursor:pointer;list-style:none;font-size:var(--fs-xs);color:var(--ac);
  padding:6px 0}
.tfold>summary::-webkit-details-marker{display:none}
.tfold>summary::after{content:" ▾"}
.tfold[open]>summary::after{content:" ▴"}
.tfold[open]>summary{margin-bottom:4px}
/* 锚点跳转留出余量，避免落到卡片顶边 */
.tcard[id]{scroll-margin-top:var(--s3)}

/* ── 关键词全景（分档分组）──
   [!] 这一组类名此前**完全没有样式**：脚本在生成 .kwgroup/.kwhead/
   .kwtitle/.kwcount/.kwhint/.kwgrid/.kwcell/.kt/.kd，而 CSS 里只有
   .kwcloud .k 的规则 —— 若不补齐，「枢纽词 1 个…」那段会退回浏览器
   默认外观、和全文风格脱节。此处补齐，并与设计令牌统一。 */
.kwgroup{background:var(--w1);border:1px solid var(--line);border-radius:12px;
  padding:10px 12px;margin:0 0 8px}
.kwgroup:last-child{margin-bottom:0}
.kwhead{display:flex;flex-wrap:wrap;align-items:baseline;gap:4px 10px;
  margin:0 0 8px;padding:0 0 7px;border-bottom:1px dashed var(--line)}
.kwtitle{font-size:var(--fs-sm);font-weight:660;color:var(--ink);
  display:inline-flex;align-items:center;gap:7px}
.kwtitle::before{content:"";width:3px;height:13px;border-radius:2px;
  background:var(--grad);flex:none}
.kwcount{font-family:var(--mono);font-size:var(--fs-xs);color:var(--ink-3);
  background:var(--w3);border-radius:999px;padding:1px 8px}
.kwhint{font-size:var(--fs-xs);color:var(--ink-3)}
.kwgrid{display:flex;flex-wrap:wrap;gap:6px}
.kwcell{display:inline-flex;align-items:baseline;gap:6px;cursor:pointer;
  font:inherit;font-size:var(--fs-sm);color:var(--ink-2);
  background:var(--w0);border:1px solid var(--line);border-radius:999px;
  padding:4px 11px;transition:border-color .14s ease,background .14s ease,color .14s ease}
.kwcell:hover{border-color:var(--in);color:var(--in);background:var(--grad-soft)}
.kwcell .kt{overflow-wrap:anywhere}
.kwcell .kd{font-family:var(--mono);font-size:var(--fs-xs);color:var(--ink-3)}
.kwcell.t1{font-size:var(--fs-base);font-weight:660;color:var(--in);
  border-color:var(--in);background:var(--grad-soft)}
.kwcell.t2{font-size:var(--fs-sm);color:var(--ink)}
.kwcell.t3{font-size:var(--fs-xs)}
.kwcell.off{opacity:.32;text-decoration:line-through}

/* ── 主题 × 年份 热力图 ──
   行=主题、列=年份、格=该年文献数。行标签吸左，宽表在 .tw 里横向滚动。 */
.hmcard{padding:var(--s3) var(--s4)}
/* [!] 表格宽度修复（左空白 → 右留白 → 铺满）。
   只用 `width:max-content` 时左侧空白消失，但表格宽度=各列内容之和
   < 卡片宽，副作用是**右侧留白**——用户要的是"不空"，左右都不空。
   现改为**确定性**的 fixed 布局 + 每个表动态生成的 <colgroup>：
     ① table-layout:fixed + width:100% —— 表格宽度恒等于容器宽，左右都不留白；
     ② 首列（行标签）在 colgroup 里给定固定像素宽（由最长标签估算），
        fixed 布局下该列宽就是这个固定值，**不吸收富余宽度**；
     ③ 数据列在 colgroup 里不设宽（<col>）→ fixed 布局把「容器宽 − 标签列宽」
        **均分**给各数据列，确定性、不依赖任何内容启发式；
     ④ 窄屏：表格带内联 min-width（按列数算，见 matrix_html），超出时由外层
        .tw 横向滚动（项目既有约定），不会撑破页面。
   稳定性依据：fixed 布局的列宽完全由 colgroup 声明决定，与内容宽度、
     浏览器启发式都无关；列数变了 colgroup 列数同步变（Python 动态生成），
     所以任何数据规模下结论都成立。 */
table.mx.hmtable{border-collapse:separate;border-spacing:2px;
  width:100%;min-width:0;max-width:none;table-layout:fixed}
table.mx.hmtable thead th{position:static;background:none;border:0;
  padding:0 3px 5px;color:var(--ink-3);font-weight:600;font-size:var(--fs-xs);
  font-family:var(--mono);text-align:center}
/* 行标签列（主题名）是**文本列** → 左对齐。
   取内容宽（nowrap），不再写 width:1px。 */
table.mx.hmtable th.hmrow,table.mx.hmtable td.hmrow{
  position:sticky;left:0;z-index:1;background:var(--w0);
  text-align:left;white-space:nowrap;border:0;
  padding:0 12px 0 0;font-family:var(--font);font-size:var(--fs-sm);
  font-weight:560;color:var(--ink-2)}
table.mx.hmtable td.hm{width:36px;min-width:36px;height:28px;border:0;
  border-radius:5px;text-align:center;vertical-align:middle;
  font-family:var(--mono);font-size:10.5px;color:var(--ink);
  overflow:visible;transition:outline-color .12s}
table.mx.hmtable td.hm:hover{outline:1.5px solid var(--in);outline-offset:-1px}
.hmlegend{display:flex;align-items:center;flex-wrap:wrap;gap:8px;
  margin-top:12px;font-size:var(--fs-xs);color:var(--ink-3)}
.hmbar{display:inline-block;width:118px;height:9px;border-radius:5px;
  background:linear-gradient(90deg,rgba(79,70,229,.05),rgba(79,70,229,.9))}

/* ── 图表通用：三线图例 + 时间线 ── */
.chart-legend{display:flex;flex-wrap:wrap;gap:6px 18px;align-items:center;
  padding:10px 14px 2px;color:var(--ink-2);font-size:var(--fs-sm)}
.chart-legend span{display:inline-flex;align-items:center;gap:7px}.chart-legend i.sw{width:14px;height:10px;border-radius:3px;flex:none}
.chart-legend i.sw.dash{height:0;border-top:2px dashed currentColor;
  background:none!important;border-radius:0}
.pline-wrap{padding:6px 10px 0}
.pline{display:block;width:100%;height:auto}
.tlcard{padding:10px 12px}
.tlsvg{display:block;width:100%;height:auto}
.tlcard .tlsvg text{font-family:var(--font)}

/* ── 图表保存条（任务 B）──
   报告里所有"图"的保存入口都放在本节 .figbar 里、且都在各自卡片的顶部同一
   位置（右对齐一行），避免"东一个按钮西一个按钮"；下载文件名由按钮的
   data-name 决定，带图表名，避免一串 download.png 互相覆盖。 */
.figbar{display:flex;flex-wrap:wrap;gap:6px;justify-content:flex-end;align-items:center;margin:0 0 8px}
.figbar .fbtn{font:inherit;font-size:var(--fs-sm);color:var(--ink-2);
  background:var(--w0);border:1px solid var(--line);border-radius:999px;
  padding:4px 12px;cursor:pointer;
  transition:border-color .14s ease,color .14s ease,background .14s ease}
.figbar .fbtn:hover{border-color:var(--ac);color:var(--ac);background:var(--ac-soft)}

/* ── 保存反馈与移动端兜底通道 ──
   「手机点保存没反应」是移动端导出的已知失效模式。除逻辑修复外，这里补齐三样用户可见的东西：
   按钮忙碌态、全局提示条、移动端图片覆盖层。状态色刻意避开警告红 ——
   导出既非错误也非告警（与"不要把正常行为当异常"的一贯主张一致）。 */
.figbar .fbtn.is-busy{opacity:.6;cursor:progress}
.figbar .fbtn[disabled]{cursor:progress}
.figtoast{position:fixed;left:50%;bottom:calc(16px + env(safe-area-inset-bottom,0px));
  transform:translate(-50%,12px);z-index:9999;max-width:min(92vw,520px);
  background:var(--ink);color:#fff;font-size:var(--fs-sm);line-height:1.5;
  padding:9px 14px;border-radius:10px;box-shadow:var(--sh);
  opacity:0;pointer-events:none;transition:opacity .18s ease,transform .18s ease}
.figtoast.is-show{opacity:1;transform:translate(-50%,0)}
.figtoast.is-err{background:var(--dan)}
.figtoast-msg{display:block}
.figoverlay{position:fixed;inset:0;z-index:10000;display:flex;align-items:center;
  justify-content:center;padding:16px;background:rgba(15,23,42,.62)}
.figoverlay-box{background:var(--w0);border-radius:14px;max-width:min(94vw,720px);
  max-height:92vh;overflow:auto;padding:12px;box-shadow:var(--sh);
  display:flex;flex-direction:column;gap:10px}
.figoverlay-hd{display:flex;align-items:center;gap:10px}
.figoverlay-title{flex:1 1 auto;min-width:0;font-weight:640;font-size:var(--fs-sm);color:var(--ink)}
.figoverlay-close{font:inherit;font-size:var(--fs-sm);color:var(--ink-2);background:var(--w1);
  border:1px solid var(--line);border-radius:999px;padding:6px 14px;cursor:pointer;min-height:36px}
.figoverlay-img{display:block;width:100%;height:auto;background:#fff;
  border:1px solid var(--line);border-radius:10px}
.figoverlay-hint{margin:0;font-size:var(--fs-sm);color:var(--ink-2);text-align:center}
/* 浮层按钮区：把"分享 / 保存"（Web Share，通道1）与"在新标签页打开"（通道3）
   并排放在图片下方，文案直接告诉用户该做什么。触屏下按钮 ≥40px 便于点按。 */
.figoverlay-actions{display:flex;flex-wrap:wrap;gap:8px;justify-content:center}
.figoverlay-act{font:inherit;font-size:var(--fs-sm);color:var(--ink);background:var(--w1);
  border:1px solid var(--line);border-radius:999px;padding:8px 16px;cursor:pointer;min-height:40px}
.figoverlay-act.is-primary{color:#fff;background:var(--ac);border-color:var(--ac)}

/* ── 计量标准达标判定表 ──
   三档状态色。**刻意不用警告红**：Q 偏低 / ARI 偏低是算法的正常行为，
   这份代码的历史审阅意见明确反对把正常结果渲染成"异常 / 错误"，
   故「未达标」用琥珀（提示）而非红（告警）。 */
.std-badge{display:inline-flex;align-items:center;font-size:var(--fs-xs);
  font-weight:640;border-radius:999px;padding:2px 10px;white-space:nowrap}
.std-ok{background:var(--ok-bg);color:var(--ok)}
.std-warn{background:var(--warn-bg);color:var(--warn)}
.std-na{background:var(--surface-3);color:var(--ink-2)}
.std-def{font-size:var(--fs-xs);color:var(--ink-2);line-height:1.6}
table.mx td.std-def{text-align:left;max-width:520px}
.figbar .fbtn::before{content:"↓";margin-right:5px;font-weight:700;font-size:11px}

/* 时间线行悬停：整行提亮，便于对位阅读 */
.tlsvg g:hover rect[fill="transparent"]{fill:rgba(79,70,229,.05)}
.burst-mark{color:var(--mg);font-weight:700}

/* ── 共现网络卡：文字在上、画布在下 ── */
/* ── 共现网络：分区（nsec）──
   若不分区，工具栏、主题图例、
   关键词全景、画布、详情全部平铺在一条竖列里，读者看到的是一大块。
   现按用途切成 5 个带小标题的分区，彼此有分隔线；关键词全景可折叠
   （最长的那块），默认展开但随时可收起，页面高度立刻降下来。 */
.netcard{padding:0}
.nsec{padding:var(--s3) var(--s4);border-bottom:1px solid var(--line)}
.nsec:last-child{border-bottom:0}

/* ── 视图与导出：控件收进默认收起的折叠面板 ──
   [!] 这一区块此前把「着色/图法」4 个按钮 + 2 个下拉 + 2 个滑杆 +
   2 个导出按钮一次性平铺，读者点完选择还得往下滚才能看到画布。
   现改为默认收起的 <details>：折叠态只留一行摘要（当前生效的视角 / 连线 /
   线宽），点开才出现全部控件，画布因此上移到首屏附近。
   「悬停详情 #tinfo」与「性能读数 #perf」留在折叠之外（见 .ctrl-live），
   保证鼠标划过画布时的反馈不因收起而消失。 */
.fold{margin:0;border:1px solid var(--line);border-radius:10px;
  background:var(--w1);overflow:hidden}
.fold>summary{list-style:none;cursor:pointer;display:flex;align-items:center;
  gap:8px;flex-wrap:wrap;padding:8px 11px;min-height:38px;
  font-size:var(--fs-sm);color:var(--ink-2)}
.fold>summary::-webkit-details-marker{display:none}
.fold>summary::after{content:"展开 ▾";margin-left:auto;font-size:var(--fs-xs);
  color:var(--ink-3);white-space:nowrap}
.fold[open]>summary::after{content:"收起 ▴"}
.fold>summary:hover{background:var(--grad-soft);color:var(--in)}
.foldh-lbl{font-weight:600;color:var(--ink)}
.foldh-val{font-family:var(--mono);font-size:var(--fs-xs);color:var(--in);
  background:var(--grad-soft);border-radius:999px;padding:2px 9px}
/* 折叠面板里的工具条不再自带一层边框，避免"框中框" */
.fold>.toolbar{border:0;border-radius:0;margin:0;background:transparent;
  padding:2px 11px 11px}
.fold>.topicmap{padding:2px 11px 11px}
/* 悬停详情 / 性能读数：常驻一行，始终可见 */
.ctrl-live{display:flex;flex-wrap:wrap;align-items:baseline;gap:4px 10px;
  margin:0 0 8px;min-height:18px}
.ctrl-live>#tinfo{flex:1 1 240px;min-width:0;font-size:var(--fs-sm);
  color:var(--ink-2)}
.ctrl-live>.perf{flex:none;margin-left:auto}
.nsec-h{margin:0 0 10px;font-size:var(--fs-sm);font-weight:660;
  color:var(--ink);display:flex;align-items:baseline;gap:8px;flex-wrap:wrap;
  line-height:1.5}
.nsec-h::before{content:"";width:3px;height:13px;border-radius:2px;
  background:var(--grad);flex:none;align-self:center}
summary.nsec-h{cursor:pointer;list-style:none;margin:0}
summary.nsec-h::-webkit-details-marker{display:none}
summary.nsec-h::after{content:"展开 ▾";margin-left:auto;font-weight:500;
  font-size:var(--fs-xs);color:var(--ink-3);white-space:nowrap}
details[open]>summary.nsec-h::after{content:"收起 ▴"}
.nsec-canvas{padding:var(--s3) var(--s4) var(--s4)}
.netrow{margin:0 0 8px}
.netrow:last-child{margin-bottom:0}
.topicmap{display:flex;flex-wrap:wrap;gap:8px}
.tmap-item{display:flex;align-items:flex-start;gap:8px;background:var(--w2);
  border:1px solid var(--line);border-radius:10px;padding:7px 11px;
  max-width:min(330px,100%);cursor:pointer;transition:.16s;
  font:inherit;text-align:left}
.tmap-item:hover{border-color:var(--line-2);background:var(--w0);box-shadow:var(--glow)}
.tmap-item .tmk{width:9px;height:9px;border-radius:3px;flex:none;margin-top:5px}
.tmap-item .tmn{font-weight:640;font-size:var(--fs-sm);color:var(--ink)}
.tmap-item .tmk2{font-size:var(--fs-xs);color:var(--ink-2);line-height:1.5;
  overflow-wrap:anywhere}
.tmap-item .tmid{font-family:var(--mono);font-size:var(--fs-xs);color:var(--ink-3)}
.net-canvas{padding:0}
.canvaswrap{border-radius:12px;overflow:hidden;background:var(--w0);
  border:1px solid var(--line)}
.net-foot{padding:0}
.lgcap{font-size:var(--fs-xs);color:var(--ink-2);align-self:center}
.lgwarn{font-size:var(--fs-xs);color:var(--amber);margin-left:8px}
.nsec .lg{display:flex;flex-wrap:wrap;gap:6px 10px;align-items:center;margin:0}
.tmap-item.on{border-color:var(--in);background:var(--grad-soft);box-shadow:var(--glow)}
.sidehint{margin:6px 0 0;font-size:var(--fs-sm);color:var(--ink-2);line-height:1.75}
.net-foot .side{margin:0}
.net-foot .side h4{margin:0 0 6px;font-size:var(--fs-sm);color:var(--ink-2);
  font-weight:640}

/* ── 每类网络的"主题色" ──
   作者 / 机构 / 引文三类网络此前共用同一个青色，读者无法从颜色上区分"这是哪张网"。
   现为每类网络指定一个取自 _PAL 的主题色（--net-c），并让**区块标题竖条 / KPI 数值 /
   保存按钮悬停 / 主色说明点**四处同源 —— 颜色不是装饰，而是"这张图属于哪类网络"的
   冗余编码。**节点颜色按"群"分区着色**（同色 = 同一群，见 AUTH_JS / NETVIEW_JS 的
   colorOf）：作者画布按 component（连通分量）= 合作群；机构 / 引文画布优先按
   community（加权标签传播社群发现）—— 引文网络近乎全连通，按连通分量上色会退化成
   单色，故改用社群；无 community 时退回 component、再退回 JS 并查集兜底。
   --net-c 仅作本节"卡片主色"，回答"这是哪张网络"，与节点颜色语义已分离。 */
.net-accent{--net-c:var(--in)}
.net-accent .nsec-h::before{background:var(--net-c)}
.net-accent .kpi .v{color:var(--net-c)}
.net-accent .figbar .fbtn:hover{border-color:var(--net-c);color:var(--net-c);
  background:transparent}
.net-key{display:inline-flex;align-items:center;gap:6px;font-size:var(--fs-xs);
  color:var(--ink-2)}
.net-key .dot{background:var(--net-c)}

/* 页脚：宽度由 .main 决定（写死像素值放进分栏会与内容列错位）。
   [!] 此处是**唯一**的 footer 宽度定义，不设第二份宽度规则，
   避免更靠后的规则覆盖分栏版本。 */
footer{max-width:none;margin:var(--s6) 0 0;padding:var(--s4) 0 0;
  border-top:1px solid var(--line);color:var(--ink-3);font-size:var(--fs-xs);
  line-height:1.75}

/* ── 表格：窄屏不撑破布局 ──
   宽表一律由 _wrap_tables() 套进 .tw（overflow-x:auto），
   只有表格自身滚动，页面不会被撑宽。 */
td,th{font-variant-numeric:tabular-nums}

.keys{font-size:10.5px;color:var(--tx-3);line-height:1.7}
/* 触摸 / 键盘两套操作说明，按输入方式二选一显示 */
.touchnote{display:none}
@media(hover:none) and (pointer:coarse){
  .touchnote{display:inline}
  .kbdonly{display:none}
}

/* ══════════════════════════════════════════════════════════
   窄屏 / 移动端
   ──────────────────────────────────────────────────────────
   三条硬约束：
     1) 不遮挡：触屏上「Ctrl/⌘+滚轮」这类键盘说明毫无意义，改为隐藏，
        画布底部只留触摸手势说明（见上 .touchnote / .kbdonly）。
     2) 不跨页：所有固定宽度的图表（双轴折线图 / 时间线 / 突现表）
        各自在容器内横向滚动，绝不撑宽整页。
     3) 可读：字号与画布高度随视口收缩，但都设下限，不缩到看不清。
   ══════════════════════════════════════════════════════════ */
@media(max-width:1080px){
  /* 单列布局下侧栏不再吸顶，否则会吃掉半屏高度 */
  .side{position:static;max-height:none}
}
@media(max-width:760px){
  :root{
    --s4:12px; --s5:16px; --s6:22px;
    /* 手机端画布适当加高（371→约 420px）以拉开点距，但仍压在一屏内：
       50vh 在 844px 高的手机上约 422px，加上说明条仍在单屏可视范围内。 */
    --canvas-h:clamp(320px, 52vh, 470px);
  }
  .shell{padding:10px 10px 32px}
  h1{letter-spacing:0}
  /* [!] 窄屏下不再把视图说明/快捷键**浮在画布上**：
     手机画布只有 300px 上下，两条覆盖层会直接压住图、
     与布图区重叠。改为静态流式，说明落在画布上方/下方。 */
  .overlay-ui{position:static;padding:8px 10px;background:var(--w2);
    border-radius:10px;margin:0 0 8px}
  .overlay-ui.bottom{margin:8px 0 0;padding-top:8px}
  .overlay-ui .it{display:inline-flex;margin:0 8px 4px 0}
  .canvaswrap{overflow:visible}
  .nsec{padding:10px 12px}
  .nsec-h{margin-bottom:8px}
  /* 图表保持可读宽度 + 容器内横向滚动 —— 页面本身不被撑宽 */
  .pline-wrap{overflow-x:auto;-webkit-overflow-scrolling:touch}
  .pline{min-width:560px}
  .tlcard{overflow-x:auto;-webkit-overflow-scrolling:touch;padding:8px}
  .tlsvg{min-width:660px}
  .kwcell{padding:4px 9px}
  .toolbar{gap:4px}
  .toolbar .viewbtn,.toolbar .rstbtn{min-height:32px;padding:4px 8px}
  .netrow{gap:6px}
  .tmap-item{max-width:100%}
  .kpi .v{font-size:16px}
  .pbar{height:16px}
  .pbar b{font-size:11px}
  /* [!] 纵向留白再逐项收紧一档 ——
     卡片内边距、标题行高/下边距、标签行间距、占比条、代表词 chip、
     折叠相关间距；并新增 `.tmeta .tag` 行高压缩：语种/篇数/年份三个 .tag 原本靠
     line-height:1.6 撑到约 24px，收成 1.3 后整行少占约 6px。
     [!] 只压「空白与行盒」，不缩小正文/关键词的可读字号；.fbtn 触摸高度 44px 保持不变；
     `.tfold>summary` 是整行可点，其 29px 高度维持不变（不再往下压，避免手机上点不中）。 */
  .tcard{padding:6px 9px}
  .tcard .tname{font-size:14px;line-height:1.25;margin:0 0 2px;gap:5px}
  .tmeta{gap:3px;margin:0 0 3px}
  .tmeta .tag{font-size:11px;line-height:1.3;padding:1px 7px}
  .tcard .chiprep{font-size:11px;padding:2px 8px}
  .chips.crep{gap:3px;margin-bottom:3px}
  .chiptail{font-size:10.5px;padding:2px 7px}
  .chips.ctail{grid-template-columns:repeat(auto-fill,minmax(72px,1fr));gap:3px}
  .chipnote{margin:0 0 2px}
  .tcard .pbar{height:12px;margin:0 0 4px}
  .tcard .pbar b{font-size:10.5px;line-height:1}
  .tcard .tfold>summary{padding:5px 0}
  .tovw{max-width:150px}
  .tovkw{max-width:220px}
  /* [!] 窄屏触摸目标 ≥44px：按钮高度低于约 30px 时手机上极易点不中；
       并左对齐，避免一排按钮挤在右侧被裁切。 */
  .figbar .fbtn{min-height:44px;padding:8px 14px;font-size:14px}
  .figbar{justify-content:flex-start}
}
@media(max-width:420px){
  .pline{min-width:520px}
  .tlsvg{min-width:580px}
  .shell{padding:8px 8px 26px}
  .kwgroup{padding:8px 9px}
}

/* ══════════════════════════════════════════════════════════
   补齐"从未定义过样式"的类
   ──────────────────────────────────────────────────────────
   这几个类一直在产出标记，却**从来没有对应的 CSS 规则**，
   浏览器按默认外观渲染（无间距、无边框、字体不统一）。
   这正是"有些窗口不够现代""风格不统一"的直接来源 ——
   不是样式写得不好，而是根本没写。此处统一到设计令牌。
   ══════════════════════════════════════════════════════════ */
/* 图例色点 */
.dot{display:inline-block;width:9px;height:9px;border-radius:3px;
  margin-right:5px;vertical-align:-1px;flex:none}
/* 卡片内小节标题行（突现检测、K 值判定等卡片共用） */
.hd{display:flex;align-items:center;gap:10px;flex-wrap:wrap;
  margin:0 0 10px;padding:0 0 9px;border-bottom:1px solid var(--line)}
/* 画布性能读数 */
.perf{font-family:var(--mono);font-size:var(--fs-xs);color:var(--ink-3)}
/* 按年份着色图例两端的年份标签 */
.yrlab{font-family:var(--mono);font-size:var(--fs-sm);color:var(--ink-2)}
/* 选中详情区的关键词胶囊（由 JS 的 kwNode 逐项构建） */
.kws{display:flex;flex-wrap:wrap;gap:6px;max-height:280px;overflow:auto;
  padding-right:2px}
.kw{display:inline-flex;align-items:center;gap:6px;cursor:pointer;
  background:var(--w2);border:1px solid var(--line);border-radius:999px;
  padding:4px 10px;font-size:var(--fs-sm);color:var(--ink-2);
  transition:border-color .14s ease,background .14s ease,color .14s ease}
.kw:hover{border-color:var(--in);color:var(--in);background:var(--grad-soft)}
.kw>i{width:8px;height:8px;border-radius:50%;flex:none}
.kw .kt{color:var(--ink)}
.kw .kd{font-family:var(--mono);font-size:var(--fs-xs);color:var(--ink-3)}
.kw .kb{font-style:normal;font-size:var(--fs-xs);color:var(--ink-3);
  border-left:1px solid var(--line);padding-left:6px}
/* 主题×作者 / 多维交叉 的热力表。
   [!] 与热力表**同一根因与同一修法**（另一张热力表）。
   与 .hmtable 一样改为 fixed 布局 + 动态 <colgroup>：首列固定像素宽、数据列
   `<col>` 不设宽 → 均分剩余；表格 width:100% 铺满卡片，左右都不留白。
   colgroup 由 authormatrix_html 按主题列数动态生成（见该函数）。 */
.matrix{overflow-x:auto;-webkit-overflow-scrolling:touch;
  border:1px solid var(--line);border-radius:12px;background:var(--w0)}
table.mx.heat{border-collapse:separate;border-spacing:2px;
  width:100%;min-width:0;max-width:none;table-layout:fixed}
table.mx.heat th{position:static;background:none;border:0;color:var(--ink-3);
  font-weight:600;font-size:var(--fs-xs);padding:3px 7px;text-align:center;
  font-family:var(--mono)}
/* 行标签（作者/主题名）是文本列 → 左对齐 */
table.mx.heat th.rowh,table.mx.heat th.rowname,
table.mx.heat td.rowh,table.mx.heat td.rowname{
  position:sticky;left:0;z-index:1;
  background:var(--w0);text-align:left;white-space:nowrap;border:0;
  font-family:var(--font);font-size:var(--fs-sm);color:var(--ink-2);
  font-weight:560;padding:0 12px 0 0}
table.mx.heat td.ht{width:40px;min-width:40px;height:26px;border:0;
  border-radius:4px;text-align:center;vertical-align:middle;
  font-family:var(--mono);font-size:10px;color:var(--ink)}

/* ── 打印：切回浅色，避免整页深色浪费墨 ── */
@media print{:root{--bg:#fff;--bg-2:#fff;--surface:#fff;--surface-2:#fafafa;
        --surface-3:#f2f2f2;--border:#ddd;--border-2:#ccc;
        --tx:#111;--tx-2:#444;--tx-3:#777;--sh:none;--sh-sm:none}
body{background:#fff;background-image:none}
h1{-webkit-text-fill-color:#111;color:#111;background:none}
.canvaswrap{background:#fff}
}
@media(prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}
}

"""


def esc(s) -> str:
    return html.escape(str(s if s is not None else ""))


def gini2(counts):
    """基尼系数（失衡度），取值 [0,1]：0=完全均衡，越大越集中。

    按标准式：G = 2·Σ(i+1)·x_i / (n·Σx_i) − (n+1)/n，且以**升序**排序
    （降序会使符号翻转）。本库 14 簇实测 G = 0.159。
    """
    s = sorted(counts)
    n = len(s)
    tot = sum(s)
    if n == 0 or tot == 0:
        return 0.0
    idx = sum((i + 1) * x for i, x in enumerate(s))
    return (2 * idx) / (n * tot) - (n + 1) / n


JS_NET = r"""
(function(){
const net = window.__NET__;
const cv = document.getElementById('net');
if(!net || !net.nodes || !net.edges || !cv) return;
const ctx = cv.getContext('2d', {alpha:false});
const N = net.nodes, E = net.edges, META = window.__CMETA__ || {};
const KW = window.__KW__ || null;   // 关键词共现网络（时间线视图数据源）

/* ---------- 主题配色 ---------- */
// [!] 旧色板是硬编码的 Tableau/Vega 风格（#4C78A8 #F58518 #54A24B…），
// 与报告 v2 的「青→靛→品红」设计语言（--cy #06B6D4 / --in #4F46E5 /
// --mg #D6336C）完全脱节——画布像贴上去的外挂图，而不是这份报告的一部分。
//
// 新色板两条原则：
//   1) **与页面同源**：整条色板落在与 --grad 同一明度/彩度区间，首位即品牌青
//      #0891B2，靛 / 品红也在列；图例、主题卡、百分比条与画布节点因此是
//      「一种语言的彩色」。
//   2) **相邻簇色相相隔最远**：ci 升序即相邻簇，故按「贪心链」排序（每步取与
//      上一色在最差色觉视图下 CIEDE2000 最大的未用色）。实测相邻 min ΔE00 =
//      29.8(normal)/18.9(protan)/20.6(deutan)/3.1(tritan)，优于旧色板的
//      19.9/13.3/12.5/4.3。颜色仍只是第一通道，另有图例文字 / 侧栏列表 /
//      悬停提示 / 跨簇描边做冗余编码。
//   [!] 必须与 Python 侧 build_html 的 _PAL **逐位一致**（顺序也一致）。
const PAL = ['#0891B2','#EA580C','#4F46E5','#B45309','#2563EB','#E11D48',
             '#0E7490','#DB2777','#0D9488','#D6336C','#7C3AED','#16A34A',
             '#64748B','#65A30D'];
// 导出给「作者共现网络」画布复用同一色板 —— 只新增一个全局，不改任何既有行为。
// 作者网络与关键词网络必须同源配色，否则同一份报告里两套颜色对不上。
window.__PAL__ = PAL;
const NEUTRAL = '#94A3B8';           // 无主题归属（中性石板灰，与所有彩色截然区分）
// 选中 / 悬停的强调描边改用皮肤令牌 sk.selStroke / sk.selInner（浅深两套各自可读），
// 强调描边不用固定深色常量——深色画布下几乎不可见，统一走皮肤令牌。
const hex2rgb = h => [parseInt(h.slice(1,3),16),parseInt(h.slice(3,5),16),
                      parseInt(h.slice(5,7),16)];
const cidx = new Map();             // cluster_id -> 调色板下标
(function(){
  const ids = [...new Set(N.map(d=>d.pc).filter(v=>v!=null))]
                .sort((a,b)=>a-b);
  ids.forEach((id,i)=>cidx.set(id, i % PAL.length));
})();
const colorOf = d => d.pc==null ? NEUTRAL
                        : PAL[cidx.get(d.pc) ?? 0];
// 桥接节点的次色（描边用）：主簇之外占比第二的簇
const secondOf = d => (d.br && d.ci && d.ci.length>1 &&
                       d.ci[1]!=null && cidx.has(d.ci[1]))
                      ? PAL[cidx.get(d.ci[1])] : null;
// 图例色块上色（与节点用同一套映射，保证图例↔节点严格一致）
document.querySelectorAll('.lg-item .sw[data-sw]').forEach(el=>{
  const c = parseInt(el.dataset.sw,10);
  el.style.background = PAL[cidx.get(c) ?? 0];
});

/* ---------- 索引与布局 ---------- */
const idx = {}; N.forEach((d,i)=>idx[d.id]=i);
const byId = {}; N.forEach(d=>byId[d.id]=d);

// 坐标优先级：pos_encoded（后端预计算，base64 int16）> x/y 明文 > 现场 FR
//
// [!]  判定必须用 Number.isFinite，绝不能用 `x !== undefined`。
//   Python 的 json.dumps 会把 float('nan') 写成 NaN 字面量，而 JS 里
//   NaN 是合法字面量、且 NaN !== undefined 为**真** —— 于是「有 x/y」
//   会被误判成立，FR 兜底被跳过，可 px/py 从头到尾没有任何赋值路径，
//   结果所有坐标为 NaN：整张网络图一片空白，控制台**不报任何错**。
//   （_view_fixture.json 就含 x/y=NaN 且无 pos_encoded 的退化样本：
//    若自检只数绘制调用次数，NaN 照样计数 → 判 PASS，
//    「密度图/年轮图不显示」就会长期抓不到。）
let hasXY = false;
if(net.pos_encoded && net.pos_encoded.pos_b64){
  try{
    const bin = atob(net.pos_encoded.pos_b64);
    const buf = new ArrayBuffer(bin.length);
    const u8 = new Uint8Array(buf);
    for(let i=0;i<bin.length;i++) u8[i]=bin.charCodeAt(i);
    const q = new Int16Array(buf), sc = net.pos_encoded.scale||1;
    if(q.length >= 2*N.length){
      N.forEach((d,i)=>{ d.px = q[2*i]/sc; d.py = q[2*i+1]/sc; });
      hasXY = N.length>0 && N.every(d=>Number.isFinite(d.px)&&Number.isFinite(d.py));
    }
  }catch(e){ hasXY = false; }
}
// 明文 x/y 兜底：必须**显式拷进 px/py** —— 渲染链路只认 px/py。
if(!hasXY && N.length && Number.isFinite(N[0].x) && Number.isFinite(N[0].y)){
  N.forEach(d=>{ d.px = +d.x; d.py = +d.y; });
  hasXY = N.length>0 && N.every(d=>Number.isFinite(d.px)&&Number.isFinite(d.py));
}

if(!hasXY){
  // 兜底：纯 JS FR（O(n²)，1094 节点尚可；>3000 需 Barnes-Hut）
  let s=42; const rnd=()=>((s=s*16807%2147483647)/2147483647-.5);
  N.forEach(d=>{d.px=400+rnd()*800; d.py=300+rnd()*600;});
  for(let it=0; it<80; it++){
    for(let i=0;i<N.length;i++)
      for(let j=i+1;j<N.length;j++){
        let dx=N[i].px-N[j].px, dy=N[i].py-N[j].py;
        let f=3000/(dx*dx+dy*dy+0.01);
        N[i].px+=dx*f; N[i].py+=dy*f; N[j].px-=dx*f; N[j].py-=dy*f;
      }
    E.forEach(e=>{
      const a=N[idx[e.s]], b=N[idx[e.t]];
      if(!a||!b) return;
      let dx=b.px-a.px, dy=b.py-a.py, d=Math.sqrt(dx*dx+dy*dy)||1, f=(d-60)*0.02;
      a.px+=dx/d*f; a.py+=dy/d*f; b.px-=dx/d*f; b.py-=dy/d*f;
    });
  }
}

/* 最后一道防线：无论上面走哪条分支，都不允许 NaN/Inf 进入渲染链路。
   一旦发生（数据源给了半截坐标、量化越界、FR 未收敛……），
   就地退化为确定性网格，保证「图一定有东西，且一定看得见」——
   而不是静默画出一张空白画布。 */
(function sanitizeLayout(){
  const bad = d => !Number.isFinite(d.px) || !Number.isFinite(d.py);
  if(N.length && !N.some(bad)) return;
  const cols = Math.max(1, Math.ceil(Math.sqrt(N.length)));
  N.forEach((d,i)=>{
    d.px = 120 + (i % cols) * 60;
    d.py = 120 + Math.floor(i / cols) * 60;
  });
  if(window.console) console.warn(
    '[net] 节点坐标含非有限值，已退化为网格布局（请检查 network.json 的 x/y 或 pos_encoded）');
})();

// 可视化调节参数（由页面上的滑杆控制）
let EDGE_W_SCALE = 1.0;   // 连线粗细倍率
let WMAX = 0;             // 全网最大边权（懒计算；供无主题归属时的权重梯度用）
let WSORT = null;         // 全网边权升序数组（懒计算；权重分位数梯度用）
let EDGE_STYLE = 'curve'; // line | curve —— 曲线更美观，直线更省
// 画布配色：页面整体深色，但图面提供浅/深两套由用户切换。
// 深色适合长时间看图、浅色适合投影与打印快照，故做成可选而非写死。
let CANVAS_THEME = 'light';
const CANVAS_SKIN = {
  light:{
    bg:'#FFFFFF', label:'rgba(26,29,33,.92)', halo:'rgba(255,255,255,.92)',
    cross:'rgba(120,120,114,0.34)', crossDim:'rgba(120,120,114,0.12)',
    ringA:'#FAFAF8', ringB:'#FFFFFF', ringLine:'#E4E4DE', ringOuter:'#C8C8C0',
    tick:'#8A9099', core:'#D8D8D2', coreEdge:'rgba(15,123,138,.5)',
    note:'#5A6169', noteDim:'#8A9099',
    /* 节点描边 / 选中环 / 标签选中色：与主题视图同语言，深浅两套各自可读 */
    nodeEdge:'rgba(15,23,42,.40)', selStroke:'#111111', selInner:'#FFFFFF',
    hlText:'#B0205A',
    /* [!] 密度色带不用 CiteSpace 的蓝→绿→黄→红（与页面设计语言无关），
       统一到「青→靛→品红」（--grad 同源），并在最密端压到深品红，
       保证密度 1.0 处与白底对比远超人眼可辨阈值（可见性由色带端点保证）。 */
    densRamp:[[0.00,[247,249,254]],[0.22,[13,168,198]],[0.50,[79,70,229]],
              [0.76,[203,48,120]],[0.90,[214,51,108]],[1.00,[122,15,72]]],
    densDot:'rgba(255,255,255,.85)', densInk:'#1A1D21', densIso:'rgba(255,255,255,.55)',
  },
  dark:{
    bg:'#0E1117', label:'rgba(232,237,244,.94)', halo:'rgba(14,17,23,.9)',
    cross:'rgba(110,126,144,0.34)', crossDim:'rgba(110,126,144,0.12)',
    ringA:'#141922', ringB:'#0E1117', ringLine:'#2C3644', ringOuter:'#3A4757',
    tick:'#6E7E90', core:'#28323F', coreEdge:'rgba(61,214,208,.5)',
    note:'#A7B4C4', noteDim:'#6E7E90',
    nodeEdge:'rgba(226,232,240,.50)', selStroke:'#F1F5F9', selInner:'#0E1117',
    hlText:'#FF9EC4',
    /* 深色底反向：疏处近黑，密处沿「青→靛→品红」提亮到浅粉，保证对比 */
    densRamp:[[0.00,[12,16,24]],[0.24,[12,150,176]],[0.52,[120,110,240]],
              [0.78,[226,86,158]],[0.92,[214,51,108]],[1.00,[252,205,230]]],
    densDot:'rgba(14,17,23,.75)', densInk:'#E8EDF4', densIso:'rgba(255,255,255,.22)',
  },
};
// 导出给「作者共现网络」画布复用皮肤令牌（浅/深两套同一来源）。
// 作者画布自管主题，不读关键词画布的 CANVAS_THEME —— 但令牌值必须同源，
// 否则两张图在同一屏里底色/标签色不一致，像两张拼凑的图。
window.__CANVAS_SKIN__ = CANVAS_SKIN;
const SKIN = () => CANVAS_SKIN[CANVAS_THEME];
let NODE_S_SCALE = 1.0;   // 节点大小倍率

// 视图变换（缩放/平移）
let vx=0, vy=0, vk=1, vInit=false;
// 空网络时 Math.max() 返回 -Infinity，会让所有半径/热区变 NaN —— 显式兜底到 1
const maxDeg = N.length ? Math.max(...N.map(d=>d.degree||1)) : 1;
// 节点半径：按度数开方缩放，实际落在 [3.5, 15] 区间（上限 26 仅在极端度数时才触及）。
// [!] 节点半径过大会导致「节点挤在一起」：小画布假设下的旧系数（上限 17px、
// 后放宽到 30px）在放大画布后大节点仍相互压盖 —— 故系数定为 11、上限 26，适度收敛；
// 下限仍保 3px 以上，保证「每个节点都看得见、点得到」这一既有能力不退。
// 注意：节点半径是**固定屏幕像素**（draw 里 r 不乘 vk），而坐标随 vk 缩放 ——
// 这正是"画布越大越不挤"的机制，也是下面 relaxNodeOverlap 需要做像素→单位换算的原因。
function radiusOf(d){ return Math.max(3, Math.min(26,
    (4 + Math.sqrt(d.degree||1)/Math.sqrt(maxDeg)*11) * NODE_S_SCALE)); }

/* ---------- 节点去重叠松弛（缓解"节点挤在一起"）----------
   [!] 桌面坐标来自上游预计算的 pos_encoded（CiteSpace 风格分簇岛），其中若干
   低度数词圆心几乎重合 —— 实测最近的一对圆心屏幕距仅约 4.6px。这类"圆心贴合"
   无论把画布放大多少倍都无法只靠缩放分开：只有当半径小于圆心距的一半时才不重叠，
   而 radiusOf 的下限保证小节点也有约 4px 半径。故在**布局阶段**做一次轻量松弛：
   把重叠对沿圆心连线推开，位移按半径反比分配（小节点让位多、大 hub 基本不动，
   以保持原有簇结构不被破坏）。位移量仅几像素，纯"散开"微调，
   不触碰任何统计口径，也不改密度/时间线/年轮视图的绘制逻辑（它们共用这份坐标，
   反而一并受益）。坐标换算用桌面首屏量级 REF 作参照，确保桌面端能真正分开。 */
(function relaxNodeOverlap(){
  if(!N.length) return;
  const REF = 240;                          // 参照缩放（≈桌面首屏 vk 量级）
  const ur = d => radiusOf(d) / REF;         // 单位空间半径
  const maxRounds = N.length > 400 ? 30 : 90;
  for(let round=0; round<maxRounds; round++){
    let hits = 0;
    for(let i=0;i<N.length;i++){
      const a = N[i];
      for(let j=i+1;j<N.length;j++){
        const b = N[j];
        const need = (ur(a)+ur(b)) * 1.08 + 0.004;   // 半径和 + 8% 余量 + 极小间隙
        let dx = b.px-a.px, dy = b.py-a.py, d2 = dx*dx + dy*dy;
        if(d2 >= need*need) continue;
        let d = Math.sqrt(d2);
        if(d < 1e-6){                        // 完全重合：给确定性分离方向，避免除零
          const ang = ((i*12.9898 + j*78.233) % 6.2832);
          dx = Math.cos(ang); dy = Math.sin(ang); d = 1;
        }
        const ux = dx/d, uy = dy/d, push = (need - d);
        const ra = ur(a), rb = ur(b), tot = (ra+rb) || 1;
        const wa = (rb/tot) * push, wb = (ra/tot) * push;  // 半径大者位移小
        a.px -= ux*wa; a.py -= uy*wa;
        b.px += ux*wb; b.py += uy*wb;
        hits++;
      }
    }
    if(!hits) break;                          // 没有任何重叠对即收敛，提前退出
  }
})();
// bounds() 定义见下方「节点手动微调」段（需含用户偏移 ox/oy）
// sx/sy 计入用户偏移：屏幕坐标 = (算法坐标 + 用户偏移) * 缩放 + 平移
const sx = d => (d.px + (d.ox||0))*vk + vx;
const sy = d => (d.py + (d.oy||0))*vk + vy;

/* ---------- 交互状态 ---------- */
const hidden = new Set();      // 手动灰显的词
let focusTopic = null;         // 仅看该主题（null=全部）
let sel = null, hov = null;
let nbrs = new Set();          // 选中节点的邻居
// 重绘脏标记：置脏后由 schedule() 在下一帧合并执行（见文件末尾渲染调度）
const dirty = {v:false};

/* ---------- 节点手动微调 ----------
   动机：分簇岛布局是几何打包的结果，簇内相对位置由FR 决定。
   用户读图时常有「这几个词明明该靠得更近」/「这个标签压到边了」的判断，
   工具应允许直接拖动修正，而不是让用户无从下手。
   实现要点：
     1)偏移存在 ox/oy（用户偏移），**不改 px/py**（算法原坐标）——
        这样「复位」能一键回到原始布局，且 bounds() 需含偏移才能正确 fitView。
     2)拖动节点时其邻居跟随（保持局部结构），而非孤立移动——
        否则拖走一个 hub 会让它的边全部拉成长线，视觉上更乱。
     3) 拖拽阈值 3px：小于则判定为「点击」而非「拖动」，
        避免误伤既有的点击高亮邻居行为。 */
const moved = new Set();       // 被用户移动过的节点 id
let draggingNode = null;       // 当前被拖动的节点（pointer 版共用）

function nodeOffset(d){ return (d.ox||0) + (d.oy||0); }
// bounds 必须只统计**当前可见**的节点，而不是全量 N。
//
// [!]  这正是「点任一主题只看该主题时，网络缩小成一团看不清」的根因：
//   聚焦主题后只画该主题的节点，但 fitView 仍按**全库**包围盒缩放，
//   于是子集被压成画布中间的一小块 —— 密度视图同样走这套变换，一并受害。
//   改为按可见节点求包围盒后，聚焦 = 自动放大到该主题，两个视图同时修好。
function bounds(){
  let x0=1e18,y0=1e18,x1=-1e18,y1=-1e18, any=false;
  N.forEach(d=>{
    if(!visible(d)) return;
    const X=d.px+(d.ox||0), Y=d.py+(d.oy||0);
    if(!Number.isFinite(X) || !Number.isFinite(Y)) return;
    any = true;
    if(X<x0)x0=X; if(X>x1)x1=X; if(Y<y0)y0=Y; if(Y>y1)y1=Y;
  });
  if(!any) return {x0:-1, y0:-1, x1:1, y1:1};   // 全部被隐藏时给个单位盒
  return {x0,y0,x1,y1};
}
/* 复位：清空所有用户偏移，回到算法原始布局 */
function resetLayout(){
  for(const d of N){ d.ox = 0; d.oy = 0; }
  moved.clear();
  vInit = false;                // 触发 fitView重新贴合
  invalidate();
}

/* ---------- 可见性 ---------- */
function visible(d){
  if(hidden.has(d.id)) return false;
  if(focusTopic!==null){
    if(d.pc!==focusTopic) return false;
  }
  return true;
}

/* ---------- 缩放 ---------- */
/* 画布上/下各有一条**绝对定位**的覆盖层（视图说明、快捷键提示）。
   任何"自己排版"的视图都必须避开这两条带子，否则文字会压住图形
   （否则会出现大标题文字与图形重叠）。
   这里统一实测两条覆盖层的高度，供 fitView 与密度/时间线视图共用。 */
function overlayInsets(){
  const h = cv.clientHeight || 1;
  let t = Math.min(38, Math.max(20, h * 0.10));
  let b = Math.min(34, Math.max(18, h * 0.09));
  let r = 0;                       // 右侧预留（仅密度视图用，见下）
  try{
    const _t = document.getElementById('ovTop');
    const _b = document.querySelector('.canvaswrap .overlay-ui.bottom');
    const _th = _t ? _t.getBoundingClientRect().height : 0;
    const _bh = _b ? _b.getBoundingClientRect().height : 0;
    // 上限校验：布局未完成时会测到 0 或异常大值，此时退回默认比例
    if(Number.isFinite(_th) && _th > 0 && _th < h * 0.4) t = _th + 10;
    if(Number.isFinite(_bh) && _bh > 0 && _bh < h * 0.4) b = _bh + 8;
    /* 密度视图右侧的竖向色标（DOM：#densLegend）需要一条独立条带。
       量不到宽度时（jsdom 无布局引擎 / 首帧未布局）退回常量 60，
       保证绘图区一定避开它 —— 色标只占留白，不压任何图形。 */
    if(viewMode === 'density'){
      const _lg = document.getElementById('densLegend');
      const _lw = _lg ? _lg.getBoundingClientRect().width : 0;
      const w = cv.clientWidth || 1;
      r = (Number.isFinite(_lw) && _lw > 0 && _lw < w * 0.4) ? _lw + 14 : 60;
    }
  }catch(e){ r = (viewMode === 'density') ? 60 : 0; }
  return [t, b, r, 0];
}

function fitView(){
  const b = bounds(), w = cv.clientWidth, h = cv.clientHeight;
  const bw = Math.max(1, b.x1-b.x0), bh = Math.max(1, b.y1-b.y0);
  const ins = overlayInsets();
  const availH = Math.max(40, h - ins[0] - ins[1]);
  // 左右内边距：密度视图为右侧竖向色标让出条带（其他视图 ins[2]=0，行为不变）
  const availW = Math.max(40, w - ins[2] - ins[3]);
  /* [!] 留白从「固定 6% 相对比例」改为「按最大节点半径预留的像素边距」。
     相对比例（*1.06）有两个问题：① 画布放大后会白扔掉几十像素可视面积，
     网络仍缩在中间一小团；② 包围盒若只取**节点圆心**、不计半径（最大约 17px），
     边距小到一定程度时最外圈的圆会被画布边缘切掉。
     故取 pad = max(3% 的相对呼吸位, 最大半径+6px)：
     既让网络更充分铺满，又保证任何可见节点的圆都不会被裁。 */
  let maxR = 0;
  for(const d of N){ if(visible(d)){ const r = radiusOf(d); if(r > maxR) maxR = r; } }
  const padX = Math.max(bw*0.03, maxR + 6);
  const padY = Math.max(bh*0.03, maxR + 6);
  vk = Math.min(Math.max(1, availW - 2*padX)/bw,
                Math.max(1, availH - 2*padY)/bh);
  vx = ins[3] + availW/2 - (b.x0+b.x1)/2*vk;
  vy = ins[0] + availH/2 - (b.y0+b.y1)/2*vk;
  vInit = true;
  vkFit = vk;                            // 记录首屏缩放，作为标签预算基准
}

/* ---------- 标签策略（参考 VOSviewer）----------
   1094 个标签全画必然糊成一团。只给高权重节点画，缩放时才显示更多。
   预算 = f(相对首屏的缩放倍数)：首屏 26 个，放大后最多约 150 个。
   [!]  关键：候选必须取「当前视口内」的节点按 degree 排名，
      不能取全局 top-N —— 放大后全局 hub 往往已在视口外，
      会导致「越放大标签越少」的反直觉行为（实测 zoom4.7x 时标签降到 0）。
   用预排序数组 byDeg 顺序遍历，天然按 degree 降序，无需每帧排序。 */
const byDeg = N.map((d,i)=>i).sort((a,b)=>(N[b].degree||0)-(N[a].degree||0));
let vkFit = 1;                            // 首屏 fitView 后的缩放，作为基准
function labelBudget(){
  if(vkFit <= 0) return 26;               // 尚未 fitView
  const r = vk / vkFit;                   // 相对首屏的缩放倍数
  return Math.round(26 + 124*Math.min(1.0, Math.max(0, (r-1)/2.5)));
}

/* ---------- 绘制 ---------- */
let lastMs = 0, lastLabels = 0;
function draw(){
  const t0 = performance.now();
  const w = Math.round(cv.clientWidth), h = Math.round(cv.clientHeight);
  /* [!] 尺寸未就绪时必须直接放弃本帧。
     祖先 display:none / 首帧尚未布局 / 折叠面板未展开时，clientWidth 为 0。
     若此时照样往下走：fitView() 把 vk 算成 0（坐标 → NaN），
     并置 vInit=true —— 之后**永久**不再重算，图就一直空白，
     只有用户手动滚轮缩放才会偶然恢复。这正是「不显示」的第二种成因。
     现在：跳过 + 保持 vInit=false，由 ResizeObserver / resize 事件补画。 */
  if(w < 2 || h < 2) return;
  const dpr = window.devicePixelRatio || 1;
  if(cv.width !== Math.round(w*dpr) || cv.height !== Math.round(h*dpr)){
    cv.width = Math.round(w*dpr); cv.height = Math.round(h*dpr);
  }
  if(!vInit) fitView();
  ctx.setTransform(dpr,0,0,dpr,0,0);
  if(viewMode==='density'){ drawDensity(); return; }
  if(viewMode==='yearring'){ drawYearRing(w,h); return; }
  const sk = SKIN();                 // 主题视图统一取皮肤令牌（浅/深两套都照顾到）
  ctx.fillStyle = sk.bg; ctx.fillRect(0,0,w,h);

  const dimAll = (sel!==null) || (focusTopic!==null);

  /* --- 边：按主题分桶批量 stroke ---
     性能关键：不用 setLineDash 逐条设置（10672 次状态切换极慢），
     而是按「同主题实色 / 跨主题浅灰」分成两桶，每桶一次 beginPath+stroke。
     v1.0.0：新增第三桶 wB —— 两端都无主题归属（作者/机构网络、或未传
     --topics）时按**权重梯度**上色（越深=共现越强），修复「连接线没有颜色」。 */
  const sameB = [], crossB = [], wB = [];
  for(let i=0;i<E.length;i++){
    const e = E[i], a = N[idx[e.s]], b = N[idx[e.t]];
    if(!a||!b) continue;
    if(!visible(a)||!visible(b)) continue;
    if(sel!==null && e.s!==sel && e.t!==sel) continue;
    if(a.pc!=null && a.pc===b.pc) sameB.push(a,b);
    else if(a.pc==null && b.pc==null) wB.push(a,b,e);
    else crossB.push(a,b,e);
  }
  // 跨主题边：浅灰实线（不用虚线 —— 10672 条边逐条设 lineDash 会拖垮帧率）
  const CURVE = EDGE_STYLE==='curve';
  // 曲线版：边在两点之间走二次贝塞尔，微微下垂 —— 密集区更易分辨走向。
  // 下垂幅度按连线两端 x 距离的 12% 封顶，避免长边弯得过度。
  const edgeSeg = (a,b)=>{
    const x1=sx(a), y1=sy(a), x2=sx(b), y2=sy(b);
    if(!CURVE){ ctx.moveTo(x1,y1); ctx.lineTo(x2,y2); return; }
    const mx=(x1+x2)/2, my=(y1+y2)/2 + Math.min(26, Math.abs(x2-x1)*0.12);
    ctx.moveTo(x1,y1); ctx.quadraticCurveTo(mx,my,x2,y2);
  };
  if(crossB.length){
    // v1.0.0：跨主题边不再一律浅灰 —— 实测 72.8% 的边跨主题，
    // 全灰会让画布像「没颜色」。改为按权重分位数 4 级中性蓝灰阶
    // （浅→深 = 弱→强），既区别于同主题边的彩色、又能看出强弱。
    if(!WSORT){ WSORT = E.map(e=>e.w||1).slice().sort((a,b)=>a-b); }
    const q = p => WSORT[Math.min(WSORT.length-1,
      Math.floor(p*WSORT.length))] || 1;
    const thr = [q(0.25), q(0.50), q(0.75)];
    const ramp = ['#CBD5E1','#94A3B8','#64748B','#334155']; // 蓝灰阶
    const tiers = new Map();
    for(let i=0;i<crossB.length;i+=3){
      const a=crossB[i], b=crossB[i+1], e=crossB[i+2];
      const w=(e&&e.w)||1;
      const k=(w>thr[2])?3:(w>thr[1])?2:(w>thr[0])?1:0;
      let arr=tiers.get(k); if(!arr){arr=[];tiers.set(k,arr);}
      arr.push(a,b);
    }
    ctx.lineWidth = 0.5*EDGE_W_SCALE;
    tiers.forEach((arr,k)=>{
      ctx.beginPath();
      for(let i=0;i<arr.length;i+=2){ edgeSeg(arr[i],arr[i+1]); }
      ctx.strokeStyle = dimAll ? SKIN().crossDim : (ramp[k]||ramp[3]);
      ctx.stroke();
    });
  }
  // 同主题边：按主题色分桶，每桶一次 stroke
  if(sameB.length){
    const byC = new Map();
    for(let i=0;i<sameB.length;i+=2){
      const a=sameB[i], b=sameB[i+1];
      const c = a.pc;
      let arr = byC.get(c); if(!arr){arr=[]; byC.set(c,arr);}
      arr.push(a,b);
    }
    ctx.lineWidth = 0.6;
    byC.forEach((arr,c)=>{
      ctx.beginPath();
      for(let i=0;i<arr.length;i+=2){
        const a=arr[i], b=arr[i+1];
        ctx.moveTo(sx(a),sy(a)); ctx.lineTo(sx(b),sy(b));
      }
      const rgb = hex2rgb(PAL[cidx.get(c) ?? 0]);
      ctx.strokeStyle = dimAll
        ? `rgba(${rgb[0]},${rgb[1]},${rgb[2]},0.13)`
        : `rgba(${rgb[0]},${rgb[1]},${rgb[2]},0.30)`;
      ctx.stroke();
    });
  }
  // 无主题归属边：按权重分位数 4 级蓝色梯度（浅→深 = 弱→强），批量 stroke
  // v1.0.0：分位数分档（非 log）——实测工作重塑库权重 1–10，log 压缩后
  // 大多挤在最低档、几乎看不见；分位数保证每档约 25% 的边、深浅拉开。
  if(wB.length){
    if(!WMAX) WMAX = Math.max(1, Math.max.apply(null,
      E.map(e=>e.w||1)));
    if(!WSORT){ WSORT = E.map(e=>e.w||1).slice().sort((a,b)=>a-b); }
    const q = p => WSORT[Math.min(WSORT.length-1,
      Math.floor(p*WSORT.length))] || 1;
    const thr = [q(0.25), q(0.50), q(0.75)];   // 分位阈值
    const tiers = new Map();
    for(let i=0;i<wB.length;i+=3){
      const a=wB[i], b=wB[i+1], e=wB[i+2];
      const w = e.w||1;
      const k = (w>thr[2])?3:(w>thr[1])?2:(w>thr[0])?1:0;
      let arr = tiers.get(k); if(!arr){arr=[]; tiers.set(k,arr);}
      arr.push(a,b);
    }
    const ramp = ['#93C5FD','#60A5FA','#3B82F6','#1D4ED8'];
    ctx.lineWidth = 0.6*EDGE_W_SCALE;
    tiers.forEach((arr,k)=>{
      ctx.beginPath();
      for(let i=0;i<arr.length;i+=2){ edgeSeg(arr[i],arr[i+1]); }
      ctx.strokeStyle = dimAll ? 'rgba(96,165,250,0.12)' : (ramp[k]||ramp[3]);
      ctx.stroke();
    });
  }

  /* --- 节点 --- */
  N.forEach(d=>{
    if(!visible(d)) return;
    const isSel = d.id===sel, isHov = d.id===hov;
    const fade = dimAll && !isSel && !isHov &&
                 !(sel!==null && nbrs.has(d.id)) &&
                 !(focusTopic!==null && d.pc===focusTopic);
    let r = radiusOf(d);
    if(isSel) r *= 1.45; else if(isHov) r *= 1.2;
    if(fade) r *= 0.75;
    const X = sx(d), Y = sy(d);
    if(X<-20||X>w+20||Y<-20||Y>h+20) return;
    ctx.globalAlpha = fade ? 0.16 : 1;
    // 光环：把节点与其下方连线隔开，节点更「跳」出来。
    // [!] 光环色不能硬编码白色——深色画布下会在节点外圈套一层白边，假白、刺眼。
    //     走皮肤令牌（sk.halo），浅底=白、深底=近黑，两套主题都干净。
    ctx.beginPath(); ctx.arc(X,Y,r+1.1,0,6.2832);
    ctx.fillStyle = sk.halo; ctx.fill();
    // 主体填充（选中时保留主题色，靠描边区分；悬停加深）
    ctx.beginPath(); ctx.arc(X,Y,r,0,6.2832);
    ctx.fillStyle = nodeColor(d);
    ctx.fill();
    // 细描边：增强边缘锐度（固定深色在深底上几乎不可见 → 走皮肤令牌）
    ctx.lineWidth = 0.7; ctx.strokeStyle = sk.nodeEdge; ctx.stroke();
    // 选中 / 悬停：加粗描边环（形状通道，天然色盲可辨）
    if(isSel){
      ctx.lineWidth = 2.6; ctx.strokeStyle = sk.selStroke; ctx.stroke();
      ctx.lineWidth = 1.0; ctx.strokeStyle = sk.selInner; ctx.stroke();
    } else if(isHov){
      ctx.lineWidth = 1.6; ctx.strokeStyle = sk.selStroke; ctx.stroke();
    }
    // 跨簇节点：次色描边（形状通道，色盲/黑白打印下仍可辨）
    const sec = (!isSel && !isHov) ? secondOf(d) : null;
    if(sec && r>=3){
      ctx.lineWidth = 1.4; ctx.strokeStyle = sec; ctx.stroke();
    }
  });
  ctx.globalAlpha = 1;

  /* --- 簇质心标签（仅放大到一定程度时显示，避免首屏拥挤）---
     帮助快速定位「这是哪个主题岛」。只在 vk/vkFit>1.7（用户主动放大）时出现，
     用主题色 + 白色描边，叠在岛屿上方，不干扰默认视图。 */
  if(vkFit > 0 && vk / vkFit > 1.7){
    const cm = {};
    for(const d of N){
      if(d.pc==null || !visible(d)) continue;
      const a = cm[d.pc] || (cm[d.pc] = {x:0,y:0,n:0});
      a.x += d.px; a.y += d.py; a.n++;
    }
    ctx.font = 'bold 12px -apple-system,"PingFang SC",sans-serif';
    ctx.textAlign = 'center';
    for(const c in cm){
      const m = cm[c];
      const X = m.x/m.n*vk + vx, Y = m.y/m.n*vk + vy;
      if(X<-40||X>w+40||Y<-40||Y>h+40) continue;
      const col = PAL[cidx.get(parseInt(c,10)) ?? 0];
      const txt = '主题'+c;
      ctx.lineWidth = 3.5; ctx.strokeStyle = sk.halo;
      ctx.strokeText(txt, X, Y);
      ctx.fillStyle = col; ctx.fillText(txt, X, Y);
    }
  }

  /* --- 标签（分级：只看高权重，缩放时更多） --- */
  const minDeg = 0;
  ctx.font = '11px -apple-system,"PingFang SC",sans-serif';
  ctx.textAlign = 'center';
  const placed = [];
  // 候选：视口内 + 可见，按 degree 降序（byDeg 已预排序），截到预算上限
  const budget = labelBudget();
  const cands = [];
  for(let i=0;i<byDeg.length && cands.length<budget;i++){
    const d = N[byDeg[i]];
    if(!visible(d)) continue;
    const X = sx(d), Y = sy(d);
    if(X<-40||X>w+40||Y<-20||Y>h+20) continue;   // 视口外不画标签
    cands.push(d);
  }
  // 选中/邻居的标签必须显示，即便超出预算或已避让失败
  if(sel!==null){
    if(!cands.some(d=>d.id===sel)){ const d=byId[sel]; if(d) cands.push(d); }
    for(const id of nbrs){
      if(cands.length>=budget+60) break;
      const d = byId[id];
      if(d && visible(d) && !cands.some(x=>x.id===id)) cands.push(d);
    }
  }
  const maxLabels = budget + 8;
  let drawn = 0;
  for(const d of cands){
    if(drawn>=maxLabels) break;
    const isSel=d.id===sel, isHov=d.id===hov;
    const X = sx(d), Y = sy(d);
    if(X<0||X>w||Y<0||Y>h) continue;
    const r = radiusOf(d);
    const ty = Y - r - 3;
    const tw = ctx.measureText(d.id).width;
    const box = [X-tw/2-1, ty-9, tw+2, 11];
    let hit = false;
    for(const p of placed){
      if(box[0]<p[0]+p[2] && box[0]+box[2]>p[0] &&
         box[1]<p[1]+p[3] && box[1]+box[3]>p[1]){ hit=true; break; }
    }
    if(hit && !isSel && !isHov) continue;
    placed.push(box);
    // 白描边保证压在边上也读得清（深底用皮肤 halo，避免白字白边糊在一起）
    ctx.lineWidth = 3; ctx.strokeStyle = sk.halo;
    ctx.strokeText(d.id, X, ty);
    ctx.fillStyle = isSel ? sk.hlText : sk.label;
    ctx.fillText(d.id, X, ty);
    drawn++;
  }
  lastMs = performance.now() - t0;
  lastLabels = drawn;
  const perf = document.getElementById('perf');
  if(perf) perf.textContent = '帧耗时 '+lastMs.toFixed(1)+' ms · 标签 '+drawn;
}

/* ---------- 命中测试 ---------- */
function pick(mx,my){
  let best=null, bd=1e9;
  for(const d of N){
    if(!visible(d)) continue;
    const r = radiusOf(d);
    const dd = (sx(d)-mx)**2 + (sy(d)-my)**2;
    const rr = Math.max(r+3, 6)**2;
    if(dd<rr && dd<bd){ bd=dd; best=d.id; }
  }
  return best;
}

/* ---------- 提示 ---------- */
function tip(id){
  const el = document.getElementById('tinfo');
  if(!el) return;
  if(!id){ el.textContent = defaultHint(); return; }
  const d = byId[id];
  if(!d){ el.textContent = defaultHint(); return; }
  const cs = (d.ci||[]).map(c=>'主题'+c).join('、');
  /* [!]  安全：这里**不能**用 innerHTML 拼字符串。
     关键词来自外部导入（CNKI/WoS/Zotero），属不可信输入；
     esc_json() 只挡 <script> 边界，值被 JSON.parse 还原成原始字符串后
     会原样进入 innerHTML → **零点击 DOM XSS**（实测关键词
     `<img src=x onerror=alert(1)>` 开页面即触发）。
     故全部改用 textContent 逐项 append，静态样式用 createElement 设置。 */
  el.textContent = '';
  const b = document.createElement('b');
  b.textContent = String(d.id);                 // textContent 天然转义
  el.appendChild(b);
  el.appendChild(document.createTextNode(
    ' · 文献数 ' + d.df + ' · 连接数 ' + d.degree +
    (d.weight ? ' · 边权 ' + d.weight : '')));
  if(cs){
    el.appendChild(document.createTextNode(' · 所属 ' + cs));
  }else{
    const sp = document.createElement('span');
    sp.style.color = '#8a8a84';
    sp.textContent = '未归入任何主题';
    el.appendChild(document.createTextNode(' · '));
    el.appendChild(sp);
  }
  if(d.br){
    const sp = document.createElement('span');
    sp.style.color = '#8a6d3b';
    sp.textContent = '（桥接词，主簇占比仅 ' +
      Math.round((d.ps||0)*100) + '%）';
    el.appendChild(document.createTextNode(' '));
    el.appendChild(sp);
  }
}
const defaultHint = () => '共 '+N.length+' 节点 / '+E.length+
  ' 边 · 悬停查看详情 · 拖空白平移 · 拖节点可手动微调位置 · '+
  '点击高亮邻居 · Ctrl/⌘+滚轮缩放 · Ctrl/⌘+双击复位'+
  (moved.size?'（已移动 '+moved.size+' 个节点）':'')+
  ' · 点击图例只看某主题 · 滚轮与双击默认行为已让给页面滚动与文字选择';

/* ---------- 事件 ----------
   三种交互互斥，靠 mousedown 时的命中测试区分：
     · 命中节点 → 拖动该节点（+邻居跟随）
     · 命中空白 → 平移整个视口
     · Ctrl/⌘+滚轮 → 以光标为锚点缩放（裸滚轮交还页面滚动）
     · Ctrl/⌘+双击 → 复位（裸双击交还浏览器文字选择）
   拖动阈值 3px：超过才算拖动，否则算「点击」（保留点击高亮邻居的既有行为）。

   [交互冲突的处理原则] 凡是会与浏览器默认手势冲突的操作
   （滚轮=页面滚动、双击=选中文字、单击=选中/拖文本），
   一律把裸事件交还浏览器，精细操作移到 Ctrl/⌘ 修饰键之后，
   并在提示条中明示。用户不需要猜，也不需要牺牲任何一种能力。 */
function nbrsOf(id){
  const s = new Set();
  for(const e2 of E){
    if(e2.s===id) s.add(e2.t);
    else if(e2.t===id) s.add(e2.s);
  }
  return s;
}
/* ---------- 指针交互（鼠标 / 触摸 / 手写笔统一）----------
   为什么改用 Pointer Events（移动端修复）：
   此前只有 mouse* 监听 + CSS `touch-action:none`，导致手机上
     · 完全无法拖动/缩放（touch 事件不触发 mouse 模拟）
     · 且 touch-action:none 会**吞掉页面滚动**，用户看报告时想下滑都做不到。
   现在：
     · 用 pointerdown/move/up 统一处理三类输入，逻辑只写一份
     · touch-action 改为 `pan-y`：纵向允许页面滚动（阅读不受阻），
       横向手势才用于平移/缩放画布 —— 两者不冲突
     · 双指捏合 = 缩放；单指拖节点 = 微调；单指拖空白 = 平移
     · 触摸没有 hover，故用 pointerdown 时的命中结果做提示
   保留 wheel（桌面滚轮缩放）与 dblclick（桌面双击复位）。 */
let ptActive=false, ptMoved=false, ptNode=null, ptLX=0, ptLY=0;
let ptNodeNbrs=new Set(), ptNodeDX=0, ptNodeDY=0;
// 自 pointerdown 起的光标累计位移：拖拽阈值必须按累计量判定（见 pointermove 注释）
let ptStartX=0, ptStartY=0;
let pinchDist=0, pinchMidX=0, pinchMidY=0, pinching=false;
let lastTapT=0, lastTapX=0, lastTapY=0;
const activePointers = new Map();   // 多点触控：pointerId -> [x,y]

function canvasXY(e){
  const r = cv.getBoundingClientRect();
  return [e.clientX - r.left, e.clientY - r.top];
}
function applyDrag(dx, dy){
  if(draggingNode){
    /* 累计自按下起的总位移，再换算成用户偏移 ox/oy。
       [!] 若在函数末尾把 ptNodeDX/DY 归零，每帧都会用"这一次的增量"去
           **覆盖** ox/oy（ox = 单帧位移/vk ≈ 0）：节点看着跟手、实际几乎不动
           —— 表现为「拖节点能拖，但拉不动」。
       改为累计后，ox/oy = 总位移/vk，位置稳定保持，且"复位"仍能一键清零。 */
    ptNodeDX += dx; ptNodeDY += dy;
    const ux = ptNodeDX/vk, uy = ptNodeDY/vk;
    const d0 = byId[draggingNode];
    d0.ox = ux; d0.oy = uy;
    for(const id of ptNodeNbrs){
      const dn = byId[id];
      if(!dn) continue;
      dn.ox = (dn.ox||0)*0.65 + ux*0.35;
      dn.oy = (dn.oy||0)*0.65 + uy*0.35;
      moved.add(id);
    }
    moved.add(draggingNode);
    return true;
  }
  vx += dx; vy += dy;
  return false;
}
cv.addEventListener('pointerdown', e=>{
  if(e.pointerType === 'mouse' && e.button !== 0) return;
  cv.setPointerCapture && cv.setPointerCapture(e.pointerId);
  const [mx,my] = canvasXY(e);
  const ids = [e.pointerId];
  if(e.pointerType === 'touch'){
    activePointers.set(e.pointerId, [mx,my]);
    if(activePointers.size === 2){
      // 第二指落下 → 进入双指缩放，取消单指拖动
      pinching = true; ptActive=false; draggingNode=null;
      const [p1,p2] = [...activePointers.values()];
      pinchDist = Math.hypot(p1[0]-p2[0], p1[1]-p2[1]);
      pinchMidX = (p1[0]+p2[0])/2; pinchMidY = (p1[1]+p2[1])/2;
      return;
    }
  }
  ptActive = true; ptMoved = false;
  ptLX = e.clientX; ptLY = e.clientY;
  ptStartX = e.clientX; ptStartY = e.clientY;
  draggingNode = pick(mx,my);
  ptNode = draggingNode;
  if(draggingNode){
    ptNodeNbrs = nbrsOf(draggingNode);
    /* 用节点**当前偏移**给累计量播种（而不是从 0 起算）。
       [!] 否则对同一节点第二次拖拽时：ptNodeDX 从 0 起算，而 applyDrag 又把
       ox 直接设成"本次拖拽量/vk"，于是节点先跳回近原点再跟随 —— 实测
       "连拖两次的屏幕位移 = 第二次拖拽量 − 第一次"，手感像掉了一下。 */
    const _d0 = byId[draggingNode];
    ptNodeDX = (_d0 ? (_d0.ox||0) : 0) * vk;
    ptNodeDY = (_d0 ? (_d0.oy||0) : 0) * vk;
  }
  invalidate();
});
cv.addEventListener('pointermove', e=>{
  const [mx,my] = canvasXY(e);
  if(e.pointerType === 'touch' && activePointers.has(e.pointerId)){
    activePointers.set(e.pointerId, [mx,my]);
    if(pinching && activePointers.size >= 2){
      const [p1,p2] = [...activePointers.values()];
      const d = Math.hypot(p1[0]-p2[0], p1[1]-p2[1]);
      const midX = (p1[0]+p2[0])/2, midY = (p1[1]+p2[1])/2;
      if(pinchDist > 0){
        const nk = Math.max(0.12, Math.min(9, vk * (d/pinchDist)));
        vx = midX - (midX-vx)*(nk/vk); vy = midY - (midY-vy)*(nk/vk);
        vk = nk;
      }
      pinchDist = d; pinchMidX = midX; pinchMidY = midY;
      invalidate(); return;
    }
  }
  if(!ptActive) return;
  const dx = e.clientX-ptLX, dy = e.clientY-ptLY;
  /* 阈值必须按「自按下起的累计位移」判定，不能用单次事件位移：
     慢拖时每帧只移动 1–2px，单次位移永远不超过 3px → ptMoved 永不置真 →
     节点与画面都完全不动（"能拖但拉不动"的成因之一）。
     累计判定后，只有真正的手势位移才越过点击/拖拽分界。 */
  if(!ptMoved && Math.abs(e.clientX-ptStartX)+Math.abs(e.clientY-ptStartY) > 3) ptMoved = true;
  if(ptMoved) applyDrag(dx, dy);
  ptLX = e.clientX; ptLY = e.clientY;
  invalidate();
});
function endPointer(e){
  if(e.pointerType === 'touch'){
    activePointers.delete(e.pointerId);
    if(activePointers.size < 2) pinching = false;
  }
  if(!ptActive) return;
  // 未移动的短按= 点击选中（触摸无 hover，必须这样才能看到详情）
  if(!ptMoved && ptNode){
    if(ptNode===sel){ sel=null; nbrs=new Set(); }
    else { sel=ptNode; nbrs=new Set(ptNodeNbrs); }
    tip(sel);
  }else if(!ptMoved && !ptNode){
    // 触摸双击 = 桌面双击（复位）
    const now = performance.now();
    const [mx,my] = canvasXY(e);
    if(now - lastTapT < 320 && Math.abs(mx-lastTapX)<28 && Math.abs(my-lastTapY)<28){
      if(moved.size) resetLayout(); else vInit=false;
      lastTapT = 0;
    }else{ lastTapT=now; lastTapX=mx; lastTapY=my; }
  }
  ptActive=false; ptMoved=false; ptNode=null; draggingNode=null;
  ptNodeNbrs=new Set();
  invalidate();
}
cv.addEventListener('pointerup', endPointer);
cv.addEventListener('pointercancel', e=>{
  activePointers.delete(e.pointerId);
  pinching=false; ptActive=false; ptMoved=false;
  ptNode=null; draggingNode=null; ptNodeNbrs=new Set();
  invalidate();
});
// 触摸时显示提示（触摸无 hover）
cv.addEventListener('pointerdown', e=>{
  if(e.pointerType !== 'touch') return;
  const [mx,my] = canvasXY(e);
  const id = pick(mx,my);
  if(id){ hov = id; tip(id); invalidate(); }
}, true);
/* 桌面滚轮缩放（触摸走上面的双指捏合） */
/* 滚轮：不拦截页面滚动。
   此前无条件 e.preventDefault() + 缩放，导致鼠标悬停在图上滚动时
   整个页面不动、只有图在缩放——用户想往下看报告内容却滚不动，
   极易误以为页面卡住。
   现改为：滚轮一律让页面正常滚动；缩放改由 Ctrl/⌘ + 滚轮触发。
   这样「滑动=读报告」「组合键=缩放图」两套意图互不干扰。 */
cv.addEventListener('wheel', e=>{
  if(!(e.ctrlKey || e.metaKey)) return;   // 不按 Ctrl/⌘ → 交还页面滚动
  e.preventDefault();
  const r = cv.getBoundingClientRect();
  const mx = e.clientX-r.left, my = e.clientY-r.top;
  const f = e.deltaY<0 ? 1.12 : 1/1.12;
  const nk = Math.max(0.12, Math.min(9, vk*f));
  // 以光标为锚点缩放
  vx = mx - (mx-vx)*(nk/vk); vy = my - (my-vy)*(nk/vk);
  vk = nk; invalidate();
}, {passive:false});
/* 双击复位：同样避开与「选中文字」的冲突。
   双击最常见的意图是选中一段文字，若直接吞掉会让人无法复制报告里的
   术语与数字。现改为：Ctrl/⌘ + 双击才复位（与缩放共用同一组修饰键，
   构成统一的「精细操作」模式），裸双击交还浏览器默认的文字选择。 */
cv.addEventListener('dblclick', e=>{
  if(!(e.ctrlKey || e.metaKey)) return;
  e.preventDefault();
  if(moved.size){ resetLayout(); }
  else { vInit=false; invalidate(); }
});

/* ---------- 图例：点击只看该主题 ---------- */
/* ---------- 视图模式：主题着色 / 时间叠加 / 密度 ---------- ----------
   此前只有「按主题着色」一种模式，但文献计量读图常问两类问题：
     · 空间结构问题：哪些概念抱团、哪些是桥接→ 主题着色（原有）
     · 时间问题：哪些区域是近期新出现的、哪些是老概念→ 时间叠加（新增）
   时间叠加按「节点加权平均发表年」着色，蓝(早)→ 绿→ 黄(晚)，
   与 VOSviewer 的 overlay visualization 同义，是其三大视图之一。
   数据来源：build_network 已按主题×年份给出 counts，节点自身年份分布
   不在 network.json 里，故用「该节点所在各簇的年份分布」做近似，
   并在图例中明示口径 —— 不精确就说精确的假象。 */
let viewMode = 'topic';         // topic | overlay | density
let yrLo = null, yrHi = null;   // 年份色标范围

function computeYearRange(){
  let lo=1e18, hi=-1e18;
  for(const d of N){
    const cs = (d.ci||[]);
    for(const c of cs){
      const m = META[c];
      if(!m || !m.counts) continue;
      for(const y in m.counts){
        const yy = +y;
        if(yy<lo) lo=yy; if(yy>hi) hi=yy;
      }
    }
  }
  if(lo>hi){ lo=0; hi=0; }
  yrLo = lo; yrHi = hi;
}
computeYearRange();

/* 节点加权平均年：以该节点出现的各簇的年份重心近似。
   [!]  口径说明：这是簇级年份分布的加权近似，**不是**该关键词自身的
      首次/末次出现年。精确值需回原始库查询，报告图例已注明。 */
function meanYear(d){
  if(d.my !== undefined) return d.my;
  const cs = d.ci||[];
  let num=0, den=0;
  for(const c of cs){
    const m = META[c];
    if(!m || !m.counts) continue;
    let s=0, n=0;
    for(const y in m.counts){ s += (+y)*m.counts[y]; n += m.counts[y]; }
    if(n>0){ num += s; den += n; }
  }
  d.my = den>0 ? num/den : null;
  return d.my;
}
/* 年份 → 颜色（青→靛→品红，与页面 --grad 同源）。
   不用 VOSviewer overlay 的蓝→绿→黄（与报告设计语言不搭）；
   统一到品牌渐变，图例 / 时间线与画布三处同色。 */
function yearColor(y){
  if(y===null || y===undefined || yrHi<=yrLo) return NEUTRAL;
  const t = Math.max(0, Math.min(1, (y-yrLo)/(yrHi-yrLo)));
  // 三段插值：青(0) → 靛(0.5) → 品红(1)
  const stops = [[6,182,212],[79,70,229],[214,51,108]];
  const seg = t<0.5 ? 0 : 1;
  const lt = t<0.5 ? t*2 : (t-0.5)*2;
  const a = stops[seg], b = stops[seg+1];
  return `rgb(${Math.round(a[0]+(b[0]-a[0])*lt)},${Math.round(a[1]+(b[1]-a[1])*lt)},${Math.round(a[2]+(b[2]-a[2])*lt)})`;
}
function nodeColor(d){
  if(viewMode==='topic') return colorOf(d);
  if(viewMode==='overlay') return yearColor(meanYear(d));
  // density：热区之上仍要画出每个词 —— 用主题色（与主题视图同源），
  // 让读者既看得到"哪里密"，也看得出"哪些词聚在那里"。此处若返回灰色，
  // 灰点压在彩色热区上几乎不可辨，全图可辨标签只剩少数几个。
  return colorOf(d);
}
/* 密度竖向色标的渐变：与画布皮肤 densRamp 同源（浅/深两套各自正确）。
   竖向约定：底部=疏(0)，顶部=密(1)，故 CSS 用 to top。 */
function densLegendGradient(){
  const bar = document.getElementById('densLegendBar');
  if(!bar) return;
  const rmp = (CANVAS_SKIN[CANVAS_THEME] || {}).densRamp || [];
  if(!rmp.length) return;
  bar.style.background = 'linear-gradient(to top,' +
    rmp.map(st => 'rgb(' + st[1].join(',') + ') ' + Math.round(st[0]*100) + '%').join(',') + ')';
}
function setViewMode(m){
  // 年轮视图会改写节点坐标，离开时必须还原原始力导向布局，
  // 否则切回主题着色/密度视图会看到年轮位置（明显的功能退化）。
  if(viewMode==='yearring' && m!=='yearring') restoreBaseLayout();
  viewMode = m;
  document.querySelectorAll('.viewbtn').forEach(b=>
    b.classList.toggle('on', b.dataset.view===m));
  updateViewSummary();        // 折叠态摘要随视角同步
  const lg = document.getElementById('legendArea');
  if(lg) lg.style.display = (m==='topic') ? '' : 'none';
  // 竖向密度色标只在密度视图出现；渐变随深浅主题重绘
  const dl = document.getElementById('densLegend');
  if(dl) dl.style.display = (m==='density') ? '' : 'none';
  densLegendGradient();
  // 按视图切换说明：让"三条线"这类读图要点始终可见，
  // 且随视图变化（图内说明已移除，改为这里统一呈现）。
  const VIEW_HINT = {
    topic:  ['节点大小 = 连接数','描边 = 桥接词（横跨多主题）','浅灰连线 = 跨主题边'],
    overlay:['颜色 = 平均发表年（青=早 → 品红=晚）','描边 = 桥接词','浅灰连线 = 跨主题边'],
    density:['热区越深（青→靛→品红）= 该处关键词越密集','右侧竖向色标 = 由疏到密',
             '圆点与标签 = 各词实际位置（按主题着色）'],
    yearring:['纵轴 = 聚类（泳道），横轴 = 发表年份','节点落在 (聚类, 首现年份) 交点',
              '连线颜色 青→靛→品红 = 时间（两端首现年份中值）· 粗细 = 共现次数'],
  };
  const _ovb = document.getElementById('ovBottom');
  if(_ovb){
    // 用 textContent 逐条 append：视图名来自内部常量，但仍不拼 HTML 字符串
    _ovb.textContent = '';
    for(const _x of (VIEW_HINT[m] || [])){
      const _sp = document.createElement('span');
      _sp.className = 'it';
      _sp.textContent = _x;
      _ovb.appendChild(_sp);
    }
  }
  const ov = document.getElementById('overlayLegend');
  if(ov) ov.style.display = (m==='overlay') ? '' : 'none';
  vInit = false;              // 切换模式后重新贴合，避免残留旧视口
  invalidate();
}

/* ---------- 折叠面板摘要 ----------
   控件收进 <details> 后，折叠态必须能一眼看出「当前是什么视角」，
   否则读者每次都得点开确认。摘要 = 视角 + 连线样式 + 线宽 + 节点大小。 */
const VIEW_NAME = {topic:'按主题着色', overlay:'按年份着色',
                   density:'密度图', yearring:'时间线图'};
function updateViewSummary(){
  const el = document.getElementById('viewSummary');
  if(!el) return;
  const ew = document.getElementById('edgeW');
  const ns = document.getElementById('nodeS');
  const parts = [VIEW_NAME[viewMode] || viewMode,
                 EDGE_STYLE==='curve' ? '曲线' : '直线'];
  if(ew) parts.push('线宽 ' + ew.value);
  if(ns) parts.push('节点 ' + ns.value);
  el.textContent = parts.join(' · ');
}

/* ---------- 密度视图 ----------
   借鉴 VOSviewer 的 density visualization：节点密处形成热区。
   实现：对每个可见节点画径向渐变叠加，additive 混合出连续密度面。
   不用外部库（保持自包含单文件），纯 Canvas，1081 节点实测流畅。 */
/* ---------- 时间线图（原「年轮」）----------
   数据源必须是「关键词共现网络」（其节点带 years / first_year 逐年频次）；
   聚类成员关系网没有逐年数据，画不出时间线。若只提供聚类网络，
   切到该视图会给出「改用关键词共现网络」的空态提示，而不是画一张空图。
   布局细节见下方 drawYearRing 的函数头注释。 */
/* 早前版本的时间线视图会就地改写节点坐标，故离开时需还原原始力导向布局；
   现版本改用局部坐标（不改 N.px/py），但仍保留这对函数以防回归。 */
let BASE_LAYOUT = null;
function stashBaseLayout(){
  if(BASE_LAYOUT) return;
  BASE_LAYOUT = N.map(d => ({id:d.id, px:d.px, py:d.py}));
}
function restoreBaseLayout(){
  if(!BASE_LAYOUT) return;
  const m = new Map(BASE_LAYOUT.map(p=>[p.id,p]));
  N.forEach(d=>{ const p=m.get(d.id); if(p){ d.px=p.px; d.py=p.py; } });
  BASE_LAYOUT = null;
}

function drawYearRing(w,h){
  /* 时间线图（timeline view）—— 聚类泳道 × 发表年份。
   *
   * 原始需求：「年轮图其实想用将聚类编号作为 Y 轴，引文发表年份作为 X 轴，
   * 就可以布局得到共被引网络的时间线图谱。」——这正是 CiteSpace 的
   * **timeline view** 语义，而「时区视图」一类方案达不到它：
   *   · 网络节点外圈的装饰色带：与时间无关；
   *   · 同心圆年轮：能表达时间，但属自创图形，读者迁移不过来；
   *   · 时区视图（横轴年份、节点按年份竖向堆叠）：**没有聚类维度**，
   *     读不出「哪个主题是哪几年在做」。
   *
   * 本实现按 timeline view 绘制：
   *   · Y 轴 = 聚类（每个聚类一条泳道，行标签「聚类 N · 主题名」）；
   *   · X 轴 = 年份，保留时间切片刻度线；
   *   · 节点落在 (其所属聚类, 其首现年份) 的交点，大小 = 文献量；
   *   · 颜色 = 首现年份（青=早 → 靛 → 品红=晚），底部配同源时间色标；
   *   · 边 = 关键词共现，曲线，粗细随共现次数；
   *   · 上/下内边距由 overlayInsets() 给出，避开两条覆盖层。
   *
   * 聚类归属来源（按优先级）：KW 节点自带 primary_cluster → 主网络 N 按 id 反查
   *   （关键词网络与主网络节点同 id）→ 归入「未归属」泳道。
   * 若无逐年词频数据，则给出「改用关键词共现网络」的空态提示，而不是画一张空图。
   */
  const SK = SKIN();
  const hasKW = !!(KW && KW.nodes && KW.nodes.length);
  const nodeHasYears = N.length > 0 &&
        N.some(d => d.years && Object.keys(d.years).length);
  const srcNodes = hasKW ? KW.nodes : (nodeHasYears ? N : null);
  const srcEdges = hasKW ? (KW.edges || []) : E;

  ctx.globalCompositeOperation = 'source-over';
  ctx.globalAlpha = 1;
  ctx.fillStyle = SK.bg; ctx.fillRect(0, 0, w, h);

  if(!srcNodes){
    ctx.fillStyle = SK.noteDim; ctx.font = '13px ui-sans-serif,system-ui,sans-serif';
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillText('题录里没有可用的逐年词频，无法绘制时间线图', w/2, h/2);
    ctx.font = '11px ui-sans-serif,system-ui,sans-serif';
    ctx.fillText('时间线图需要每个关键词的首现年份（first_year / years 字段）', w/2, h/2 + 22);
    return;
  }

  // 年份跨度
  let lo = hasKW ? ((KW.year_range && KW.year_range[0]) ?? null) : null;
  let hi = hasKW ? ((KW.year_range && KW.year_range[1]) ?? null) : null;
  if(lo === null || hi === null){
    const all = [];
    for(const n of srcNodes){
      const ys = n.years || {};
      for(const k in ys){ const v = +k; if(Number.isFinite(v)) all.push(v); }
    }
    if(all.length){ lo = Math.min.apply(null, all); hi = Math.max.apply(null, all); }
  }
  if(lo === null || hi === null || !Number.isFinite(lo) || !Number.isFinite(hi) || hi < lo){
    ctx.fillStyle = SK.noteDim; ctx.font = '13px ui-sans-serif,system-ui,sans-serif';
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillText('题录缺少可用年份，无法绘制时间线图', w/2, h/2);
    return;
  }
  lo = Math.round(lo); hi = Math.round(hi);

  const firstYear = n => {
    const fy = n.first_year;
    if(Number.isFinite(+fy)) return Math.round(+fy);
    const ys = n.years || {};
    let best = null;
    for(const k in ys){ const v = +k; if(ys[k] > 0 && (best === null || v < best)) best = v; }
    return best === null ? lo : best;
  };

  // 年份过多时只保留近段，否则切片挤成一条线（与 CiteSpace 取 time slice 同理）
  const MAXY = 18;
  let yLo = lo;
  if(hi - lo + 1 > MAXY) yLo = hi - MAXY + 1;
  const usedYears = hi - yLo + 1;

  // 聚类归属（见函数头注释）
  const baseById = new Map(N.map(d => [d.id, d]));
  const clusterOf = n => {
    const pc = n.primary_cluster;
    if(pc !== undefined && pc !== null) return pc;
    const b = baseById.get(n.id);
    return (b && b.pc !== undefined && b.pc !== null) ? b.pc : null;
  };

  /* 选点：按泳道**轮转**取样，保证每个聚类都有代表。
     [!] 纯全局 top-N（旧做法）会把只占少量关键词的小簇整条抹掉 ——
     时间线图恰恰最需要「各主题都在场」，否则等于只画了最大的一两个主题。 */
  const MAXN = 48;
  const cand = srcNodes
    .filter(n => n.years && Object.keys(n.years).length)
    .map(n => Object.assign({}, n, {__fy: firstYear(n), __cl: clusterOf(n)}))
    .filter(n => n.__fy >= yLo);
  const emptyMid = msg => {
    ctx.fillStyle = SK.noteDim; ctx.font = '13px ui-sans-serif,system-ui,sans-serif';
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillText(msg, w/2, h/2);
    window.__YEARRING__ = {source: hasKW ? 'keyword-network' : 'main-network',
                           mode: 'timeline', years: [yLo, hi], lanes: 0,
                           ringNodes: 0, ringArcs: 0, keywords: 0, edgeColorN: 0};
  };
  if(!cand.length){ emptyMid('没有落在时间区间内的关键词'); return; }

  const laneMap = new Map();
  for(const n of cand){
    if(!laneMap.has(n.__cl)) laneMap.set(n.__cl, []);
    laneMap.get(n.__cl).push(n);
  }
  // 泳道排序：有编号按编号升序；未归属(null)排在最后
  const laneKeys = [...laneMap.keys()].sort((a, b) => {
    if(a === null) return 1; if(b === null) return -1;
    return a - b;
  });
  laneKeys.forEach(k => laneMap.get(k).sort((a, b) => (b.df || 0) - (a.df || 0)));
  const picked = [];
  for(let pass = 0; picked.length < MAXN; pass++){
    let added = false;
    for(const k of laneKeys){
      const arr = laneMap.get(k);
      if(pass < arr.length && picked.length < MAXN){ picked.push(arr[pass]); added = true; }
    }
    if(!added) break;
  }
  if(!picked.length){ emptyMid('没有可绘制的关键词节点'); return; }
  const nLanes = laneKeys.length;

  // 绘图区：避开上下覆盖层；右侧留少量边距给最靠右的标签
  const _ins = overlayInsets();
  const R = 18;
  const T = _ins[0] + 20, B = _ins[1] + 34;
  const plotH = Math.max(60, h - T - B);

  // 行标签文案 + 左侧边距（宽度随最长标签自适应，过长则截断加省略号）
  const topicNameOfCluster = c => {
    if(c === null) return '未归属';
    const m = META[c] || {};
    const nm = m.label || m.name || '';
    return nm ? ('聚类 ' + c + ' · ' + nm) : ('聚类 ' + c);
  };
  const rawLabels = laneKeys.map(k => topicNameOfCluster(k));
  ctx.font = '11px ui-sans-serif,system-ui,sans-serif';
  let labW = 0;
  for(const s of rawLabels) labW = Math.max(labW, ctx.measureText(s).width);
  const L = Math.min(190, Math.max(72, Math.round(labW + 18)));
  const laneLabels = rawLabels.map(s => {
    const maxW = L - 30;
    if(ctx.measureText(s).width <= maxW) return s;
    let t = s;
    while(t.length > 2 && ctx.measureText(t + '…').width > maxW) t = t.slice(0, -1);
    return t + '…';
  });
  const plotW = Math.max(60, w - L - R);
  const colW = plotW / usedYears;
  const X = yy => L + (yy - yLo + 0.5) * colW;
  const laneH = plotH / nLanes;
  const laneTop = i => T + i * laneH;
  const laneIdx = new Map(laneKeys.map((k, i) => [k, i]));

  // 泳道底纹（隔行交替）：让「哪一行对应哪个主题」一眼可辨
  for(let i = 1; i < nLanes; i += 2){
    ctx.fillStyle = (CANVAS_THEME === 'light')
      ? 'rgba(15,23,42,.030)' : 'rgba(226,232,240,.055)';
    ctx.fillRect(L, laneTop(i), plotW, laneH);
  }

  // 时间切片：竖向网格线 + 顶部年份标签（CiteSpace 的 time slice）
  ctx.font = '10px ui-monospace,SFMono-Regular,Menlo,monospace';
  for(let i = 0; i < usedYears; i++){
    const yy = yLo + i;
    const x = L + i * colW;
    ctx.beginPath();
    ctx.moveTo(x, T - 12); ctx.lineTo(x, T + plotH + 4);
    ctx.strokeStyle = SK.ringLine; ctx.globalAlpha = .5; ctx.lineWidth = 1;
    ctx.stroke();
    if(colW > 26 || i % 2 === 0){
      ctx.globalAlpha = 1;
      ctx.fillStyle = SK.tick; ctx.textAlign = 'center'; ctx.textBaseline = 'bottom';
      ctx.fillText(String(yy), x + colW / 2, T - 16);
    }
  }
  ctx.globalAlpha = 1;
  ctx.beginPath();
  ctx.moveTo(L, T + plotH + 4); ctx.lineTo(L + plotW, T + plotH + 4);
  ctx.strokeStyle = SK.ringOuter; ctx.lineWidth = 1.2; ctx.stroke();

  // 时间色标：青（早）→ 靛 → 品红（晚），与页面 --grad / 密度色带同源
  const CSP = [[6,182,212],[79,70,229],[214,51,108]];
  const timeColor = yy => {
    const t = usedYears <= 1 ? 0 : (yy - yLo) / (usedYears - 1);
    const f = t * (CSP.length - 1);
    const i = Math.min(CSP.length - 2, Math.floor(f));
    const u = f - i, a = CSP[i], b = CSP[i + 1];
    return 'rgb(' + Math.round(a[0]+(b[0]-a[0])*u) + ','
                  + Math.round(a[1]+(b[1]-a[1])*u) + ','
                  + Math.round(a[2]+(b[2]-a[2])*u) + ')';
  };

  // 节点落点：同 (泳道, 首现年) 单元内竖向错开，并夹在该泳道高度之内
  const pos = new Map();
  const maxDeg = Math.max.apply(null, picked.map(n => n.degree || 1).concat([1]));
  const rad = n => Math.max(3.5, Math.min(16,
    3.5 + Math.sqrt(n.degree || 1) / Math.sqrt(maxDeg) * 10));
  const cell = new Map();
  for(const n of picked){
    const key = n.__cl + '@' + n.__fy;
    if(!cell.has(key)) cell.set(key, []);
    cell.get(key).push(n);
  }
  const rowGap = Math.max(8, Math.min(15, laneH * 0.42));
  const laneClamp = Math.max(0, laneH / 2 - 4);
  cell.forEach(arr => {
    arr.sort((a, b) => (b.degree || 0) - (a.degree || 0));
    const li = laneIdx.get(arr[0].__cl);
    const cy = laneTop(li) + laneH / 2;
    arr.forEach((n, k) => {
      let off = (k - (arr.length - 1) / 2) * rowGap;
      off = Math.max(-laneClamp, Math.min(laneClamp, off));
      pos.set(n.id, [X(n.__fy), cy + off]);
    });
  });

  // 泳道行标签：主题色点 + 右对齐文字，紧贴绘图区左侧
  ctx.font = '11px ui-sans-serif,system-ui,sans-serif';
  ctx.textAlign = 'right'; ctx.textBaseline = 'middle';
  for(let i = 0; i < nLanes; i++){
    const k = laneKeys[i];
    const cy = laneTop(i) + laneH / 2;
    const txt = laneLabels[i];
    const tw = ctx.measureText(txt).width;
    ctx.beginPath();
    ctx.arc(L - 10 - tw - 8, cy, 3.2, 0, Math.PI * 2);
    ctx.fillStyle = (k === null) ? NEUTRAL : PAL[cidx.get(k) ?? 0];
    ctx.fill();
    ctx.fillStyle = SK.note;
    ctx.fillText(txt, L - 8, cy);
  }

  // 边：共现关系，曲线，粗细随次数（CiteSpace 的连线形态）
  // 颜色 = 时间：用两端关键词首现年份的**中值**映射到时间色带（青→靛→品红），
  // 读者可直接从连线颜色读出"这条共现大致发生在哪一年"，与节点同一条色带。
  // [!] 连线不能是固定灰 SK.cross——那样时间信息只落在节点上，
  //     与"时间线"的语义不符；连线应按年份着色。
  //     取值用中值而非较早/较晚：中值更贴合连线在时间轴上的实际位置，
  //     避免读者把线的颜色误读成某一端节点的年份。
  //     （曾考虑两端各取一色做 canvas 线性渐变，信息量更高，但每条边一个
  //      渐变对象、边数多时每帧创建上百个，收益不抵开销；本视图实测量级
  //      ~200 条边，纯色 + 透明度已足够清晰。）
  const wmax = Math.max.apply(null, (srcEdges || []).map(e => e.weight || 1).concat([1]));
  const fyById = new Map(picked.map(n => [n.id, n.__fy]));
  ctx.lineCap = 'round';
  let ringArcs = 0;
  const edgeCols = new Set();
  for(const e of (srcEdges || [])){
    const a = pos.get(e.source), b = pos.get(e.target);
    if(!a || !b) continue;
    const mid = (a[0] + b[0]) / 2;
    const sag = 10 + Math.min(34, Math.abs(b[0] - a[0]) * 0.08);
    ctx.beginPath();
    ctx.moveTo(a[0], a[1]);
    ctx.quadraticCurveTo(mid, (a[1] + b[1]) / 2 + sag, b[0], b[1]);
    const yA = fyById.has(e.source) ? fyById.get(e.source) : yLo;
    const yB = fyById.has(e.target) ? fyById.get(e.target) : yLo;
    const col = timeColor((yA + yB) / 2);
    edgeCols.add(col);
    ctx.strokeStyle = col;
    ctx.globalAlpha = 0.14 + 0.42 * ((e.weight || 1) / wmax);
    ctx.lineWidth = Math.max(0.5, (e.weight || 1) / wmax * 2.0 * EDGE_W_SCALE);
    ctx.stroke();
    ringArcs++;
  }
  ctx.globalAlpha = 1;

  // 节点（先全部画完，避免标签被后画的节点盖住）
  ctx.textBaseline = 'middle';
  let ringNodes = 0;
  const labelOrder = picked.slice().sort((a, b) => (b.degree || 0) - (a.degree || 0));
  for(const n of labelOrder){
    const p = pos.get(n.id);
    if(!p) continue;
    const r = rad(n);
    ctx.beginPath(); ctx.arc(p[0], p[1], r + 1.1, 0, Math.PI * 2);
    ctx.fillStyle = SK.halo; ctx.fill();
    ctx.beginPath(); ctx.arc(p[0], p[1], r, 0, Math.PI * 2);
    ctx.fillStyle = timeColor(n.__fy); ctx.fill();
    ctx.lineWidth = 0.8; ctx.strokeStyle = SK.nodeEdge; ctx.stroke();
    ringNodes++;
  }
  // 标签：排右；靠近右边界改排左；简单矩形避让防重叠
  ctx.font = '10.5px ui-sans-serif,system-ui,sans-serif';
  const placed = [];
  for(const n of labelOrder){
    const p = pos.get(n.id);
    if(!p) continue;
    const r = rad(n);
    const label = String(n.id);
    const tw = Math.min(ctx.measureText(label).width, 96);
    const right = p[0] + r + 4;
    const left = p[0] - r - 4 - tw;
    const canRight = right + tw <= w - 6;
    const lx = canRight ? right : (left >= L ? left : p[0] + r + 4);
    const box = [lx - 1, p[1] - 7, tw + 2, 13];
    let hit = false;
    for(const q of placed){
      if(box[0] < q[0]+q[2] && box[0]+box[2] > q[0] &&
         box[1] < q[1]+q[3] && box[1]+box[3] > q[1]){ hit = true; break; }
    }
    if(hit) continue;
    placed.push(box);
    ctx.textAlign = 'left';
    ctx.lineWidth = 2.6; ctx.strokeStyle = SK.halo;
    ctx.strokeText(label, lx, p[1]);
    ctx.fillStyle = SK.label;
    ctx.fillText(label, lx, p[1]);
  }

  // 底部时间方向色标（避开底部覆盖层；避免读者把颜色读反）
  {
    const bw = Math.min(300, Math.max(140, plotW * 0.5));
    const bx = L + Math.max(0, (plotW - bw) / 2);
    const by = h - _ins[1] - 12;
    const grd = ctx.createLinearGradient(bx, 0, bx + bw, 0);
    grd.addColorStop(0, timeColor(yLo));
    grd.addColorStop(1, timeColor(hi));
    ctx.fillStyle = grd;
    ctx.fillRect(bx, by, bw, 7);
    ctx.strokeStyle = SK.ringOuter; ctx.lineWidth = 1;
    ctx.strokeRect(bx + 0.5, by + 0.5, bw - 1, 6);
    ctx.font = '9.5px ui-sans-serif,system-ui,sans-serif';
    ctx.fillStyle = SK.noteDim; ctx.textBaseline = 'middle';
    ctx.textAlign = 'right'; ctx.fillText('早', bx - 6, by + 3.5);
    ctx.textAlign = 'left'; ctx.fillText('晚', bx + bw + 6, by + 3.5);
    ctx.textAlign = 'center'; ctx.fillText('首现年份', bx + bw / 2, by - 8);
  }

  window.__YEARRING__ = {source: hasKW ? 'keyword-network' : 'main-network',
                         mode: 'timeline', years: [yLo, hi], lanes: nLanes,
                         ringNodes, ringArcs, keywords: picked.length,
                         edgeColorN: edgeCols.size,
                         edgeSample: [...edgeCols].slice(0, 6)};
}

function drawDensity(){
  /* 密度热区视图 —— 按「色带保证可见性」重写。
   *
   * 用叠加透明度去"攒"亮度的做法都失败在同一个根本错误：
   *   · 固定半径 + 'lighter' 叠加 → 稀疏图过曝、密集图糊成一片；
   *   · 把单区 alpha 压到 0x14（7.8%）怕"朦胧" —— 结果更糟：
   *     单个热核叠在白底上只有 rgb(241,244,248)，与纯白相差 14/255，
   *     **数学上就不可见**；要叠到能看见得十几个热核压在同一像素上，
   *     而真实的共现网络节点是散开的，于是整幅图恒为白色。
   *     这就是「密度图不显示」的真正根因——它不是渲染失败，是渲染了但看不见。
   *
   * 本实现把可见性从"叠加运气"改成"色带保证"：
   *   1) 在 6px 低分辨率网格上累积 **归一化密度场**（抛物核平方，更锐的亮核）；
   *   2) 按全局峰值归一化，再线性拉伸到 [0,1]，映射到固定色带
   *      （白/近黑 → 青 → 靛 → 品红，见 CANVAS_SKIN.densRamp，与页面 --grad 同源）；
   *   3) 色带端点由设计给定：密度 1.0 必然是深品红，与节点多寡无关。
   *      → 只要图里还有节点，就一定存在肉眼可辨的深色区；
   *   4) 低分辨率像素图用 drawImage 放大 → 天然平滑，代价与节点数无关；
   *   5) 叠等密度线 + 主题色小点 + 最密 3 词标注，兼顾"科技感"与可读性。
   *
   * 结束时复位 globalCompositeOperation / globalAlpha，不污染其他视图。 */
  const w = Math.round(cv.clientWidth), h = Math.round(cv.clientHeight);
  if(w < 2 || h < 2) return;
  ctx.globalCompositeOperation = 'source-over';
  ctx.globalAlpha = 1;
  const sk = SKIN();
  ctx.fillStyle = sk.bg; ctx.fillRect(0, 0, w, h);

  const vis = N.filter(d => visible(d));
  if(!vis.length){
    ctx.fillStyle = sk.noteDim; ctx.font = '12px ui-sans-serif,system-ui,sans-serif';
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillText('当前筛选条件下没有可显示的节点', w/2, h/2);
    return;
  }
  // 热区半径 = 节点半径 × 3.2（与节点大小同源：hub 的热区更大）
  const radOf = d => Math.max(16, Math.min(96, radiusOf(d) * 3.2));

  /* ── 1) 低分辨率密度累积 ── */
  const CELL = 6;
  const gw = Math.max(2, Math.ceil(w / CELL));
  const gh = Math.max(2, Math.ceil(h / CELL));
  const grid = new Float32Array(gw * gh);
  let gmax = 0, drawn = 0;
  for(const d of vis){
    const X = sx(d), Y = sy(d);
    if(!Number.isFinite(X) || !Number.isFinite(Y)) continue;
    const r = radOf(d);
    if(X < -r || X > w + r || Y < -r || Y > h + r) continue;
    drawn++;
    const i0 = Math.max(0, Math.floor((X - r) / CELL));
    const i1 = Math.min(gw - 1, Math.ceil((X + r) / CELL));
    const j0 = Math.max(0, Math.floor((Y - r) / CELL));
    const j1 = Math.min(gh - 1, Math.ceil((Y + r) / CELL));
    const inv = 1 / r;
    for(let j = j0; j <= j1; j++){
      const dy = (j * CELL + CELL / 2 - Y) * inv;
      const dy2 = dy * dy;
      for(let i = i0; i <= i1; i++){
        const dx = (i * CELL + CELL / 2 - X) * inv;
        const t = dx * dx + dy2;
        if(t >= 1) continue;
        const v = (1 - t) * (1 - t);          // 抛物核平方 → 亮核更锐
        const o = j * gw + i;
        const nv = grid[o] + v;
        grid[o] = nv;
        if(nv > gmax) gmax = nv;
      }
    }
  }
  if(!drawn || gmax <= 0){
    ctx.fillStyle = sk.noteDim; ctx.font = '12px ui-sans-serif,system-ui,sans-serif';
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillText('当前视口内没有可显示的节点', w/2, h/2);
    return;
  }

  /* ── 2) 归一化 + 色带映射 → 低分辨率像素图 ── */
  const ramp = sk.densRamp || [[0,[255,255,255]],[1,[208,40,104]]];
  const rampCol = t => {
    if(t <= ramp[0][0]) return ramp[0][1];
    for(let i = 0; i < ramp.length - 1; i++){
      const p0 = ramp[i][0], c0 = ramp[i][1];
      const p1 = ramp[i + 1][0], c1 = ramp[i + 1][1];
      if(t <= p1){
        const u = (t - p0) / Math.max(1e-6, p1 - p0);
        return [c0[0] + (c1[0] - c0[0]) * u,
                c0[1] + (c1[1] - c0[1]) * u,
                c0[2] + (c1[2] - c0[2]) * u];
      }
    }
    return ramp[ramp.length - 1][1];
  };

  const FLOOR = 0.045;                 // 低于此密度完全留白，避免整幅蒙雾
  const off = document.createElement('canvas');
  off.width = gw; off.height = gh;
  let octx = null, img = null;
  try{
    octx = off.getContext('2d');
    img = octx.createImageData(gw, gh);
  }catch(e){ octx = null; }
  let peak = null, peakT = -1;
  if(octx && img){
    for(let k = 0; k < gw * gh; k++){
      const raw = grid[k] / gmax;
      if(raw <= FLOOR) continue;
      // 把可见区间重新铺满整条色带 → 对比度拉到最大
      const t = Math.min(1, Math.max(0, (raw - FLOOR) / (1 - FLOOR)));
      const c = rampCol(t);
      img.data[4*k]     = c[0] | 0;
      img.data[4*k + 1] = c[1] | 0;
      img.data[4*k + 2] = c[2] | 0;
      img.data[4*k + 3] = Math.round(255 * Math.min(1, 0.10 + t * 0.95));
      // 记录"最密处"的颜色。不能用 `raw >= 1` 判定：grid 是 Float32Array，
      // 而 gmax 是 double（grid[o] + v 提升而来），回写 Float32 会损失精度，
      // 峰值格读回来常是 0.99999997 → 判等失败 → peak 恒为 null。
      if(t > peakT){ peakT = t; peak = c; }
    }
    octx.putImageData(img, 0, 0);
    ctx.imageSmoothingEnabled = true;
    if('imageSmoothingQuality' in ctx) ctx.imageSmoothingQuality = 'high';
    ctx.drawImage(off, 0, 0, gw, gh, 0, 0, gw * CELL, gh * CELL);
  }else{
    // 离屏像素图不可用（极老的实现）：退回"按格点直接填色"，
    // **仍然走色带**，所以可见性不受影响，只是边缘略硬。
    for(let j = 0; j < gh; j++){
      for(let i = 0; i < gw; i++){
        const raw = grid[j * gw + i] / gmax;
        if(raw <= FLOOR) continue;
        const t = Math.min(1, Math.max(0, (raw - FLOOR) / (1 - FLOOR)));
        const c = rampCol(t);
        ctx.fillStyle = `rgba(${c[0]|0},${c[1]|0},${c[2]|0},${(0.10 + t*0.95).toFixed(3)})`;
        ctx.fillRect(i * CELL, j * CELL, CELL, CELL);
        if(t > peakT){ peakT = t; peak = c; }
      }
    }
  }

  /* ── 3) 等密度线：科技感 + 让读者看出密度层级 ── */
  if(gw > 2 && gh > 2){
    ctx.lineWidth = 1;
    ctx.strokeStyle = sk.densIso;
    for(const lv of [0.30, 0.58, 0.84]){
      const thr = lv * gmax;
      ctx.beginPath();
      for(let j = 0; j < gh - 1; j++){
        for(let i = 0; i < gw - 1; i++){
          const o = j * gw + i;
          if(grid[o] < thr) continue;
          if(grid[o + 1] < thr){
            ctx.moveTo((i + 1) * CELL, j * CELL);
            ctx.lineTo((i + 1) * CELL, (j + 1) * CELL);
          }
          if(grid[o + gw] < thr){
            ctx.moveTo(i * CELL, (j + 1) * CELL);
            ctx.lineTo((i + 1) * CELL, (j + 1) * CELL);
          }
        }
      }
      ctx.stroke();
    }
  }

  /* ── 4) 热区之上把每个词画出来（半透明 + halo + 描边：看得见又不糊热区）──
     [!] 已知失效模式："密度图只显示 3 个内容，其他点没显示"。
     成因：若此处只画 r≈1.5–4px 的**灰色**小点（nodeColor 对 density 返回灰），
     压在彩色热区上几乎不可辨；且下方只标注最密的 3 个词 —— 全图能看清的
     就只有那 3 个白底标签，于是被读成"只显示 3 个内容"。
     现改为：按主题色（colorOf，与主题视图同源）画实心圆，半径取节点半径的
     0.85、下限 2.2px，外圈加皮肤 halo 光环 + 细描边；半透明保留热区读法。 */
  const NR = d => Math.max(2.2, Math.min(14, radiusOf(d) * 0.85));
  let nodeArcs = 0;
  ctx.globalAlpha = 0.88;
  for(const d of vis){
    const X = sx(d), Y = sy(d);
    if(!Number.isFinite(X) || !Number.isFinite(Y)) continue;
    if(X < -8 || X > w + 8 || Y < -8 || Y > h + 8) continue;
    const r = NR(d);
    ctx.beginPath(); ctx.arc(X, Y, r + 1.0, 0, 6.2832);
    ctx.fillStyle = sk.halo; ctx.fill();
    ctx.beginPath(); ctx.arc(X, Y, r, 0, 6.2832);
    ctx.fillStyle = colorOf(d); ctx.fill();
    ctx.lineWidth = 0.7; ctx.strokeStyle = sk.nodeEdge; ctx.stroke();
    nodeArcs++;
  }
  ctx.globalAlpha = 1;

  /* ── 5) 标签：沿用 labelBudget() 的缩放策略，而不是只标最密的 3 个 ──
     与主题视图同一套预算（首屏 ~26、随缩放最多 ~150）与矩形避让，
     使读者能看出"哪些词聚在哪里"——这正是密度视图的读图目的。 */
  ctx.font = '11px -apple-system,"PingFang SC",sans-serif';
  ctx.textAlign = 'center'; ctx.textBaseline = 'alphabetic';
  const budget = labelBudget();
  const placed = [];
  const cands = [];
  for(let i = 0; i < byDeg.length && cands.length < budget; i++){
    const d = N[byDeg[i]];
    if(!visible(d)) continue;
    const X = sx(d), Y = sy(d);
    if(X < -40 || X > w + 40 || Y < -20 || Y > h + 20) continue;
    cands.push(d);
  }
  if(sel !== null){
    const d = byId[sel];
    if(d && !cands.some(x => x.id === d.id)) cands.push(d);
    for(const id of nbrs){
      if(cands.length >= budget + 60) break;
      const dn = byId[id];
      if(dn && visible(dn) && !cands.some(x => x.id === id)) cands.push(dn);
    }
  }
  let labels = 0;
  for(const d of cands){
    const isSel = d.id === sel, isHov = d.id === hov;
    const X = sx(d), Y = sy(d);
    if(X < 0 || X > w || Y < 0 || Y > h) continue;
    const ty = Y - NR(d) - 3;
    const tw = ctx.measureText(d.id).width;
    const box = [X - tw/2 - 1, ty - 9, tw + 2, 11];
    let hit = false;
    for(const p of placed){
      if(box[0] < p[0]+p[2] && box[0]+box[2] > p[0] &&
         box[1] < p[1]+p[3] && box[1]+box[3] > p[1]){ hit = true; break; }
    }
    if(hit && !isSel && !isHov) continue;
    placed.push(box);
    ctx.lineWidth = 3; ctx.strokeStyle = sk.halo;
    ctx.strokeText(d.id, X, ty);
    ctx.fillStyle = isSel ? sk.hlText : sk.label;
    ctx.fillText(d.id, X, ty);
    labels++;
  }

  /* 供回归测试读取：可见性必须由数值断言守住，而不是靠人眼看截图。
     contrast = 最密处颜色与画布底色的最大通道差，低于约 30/255 即不可辨。
     密度色标为画布右侧的 DOM 竖向色标（.dens-legend），画布内不再绘制——
     底部横条会叠在热区上、还与快捷键提示争同一条底边。 */
  window.__DENSITY__ = {
    drawn, cells: gw * gh, gmax,
    bg: sk.bg, peak: peak ? `rgb(${peak[0]|0},${peak[1]|0},${peak[2]|0})` : null,
    contrast: peak ? Math.round(Math.max(
      Math.abs(peak[0] - hex2rgb(sk.bg)[0]),
      Math.abs(peak[1] - hex2rgb(sk.bg)[1]),
      Math.abs(peak[2] - hex2rgb(sk.bg)[2]))) : 0,
    nodeArcs, labels, budget,
  };

  ctx.globalCompositeOperation = 'source-over';
  ctx.globalAlpha = 1;

  ctx.globalCompositeOperation = 'source-over';
}

/* ---------- 导出（PNG / SVG）—— 论文配图刚需 ----------
   此前报告只能截图，无法直接得到可投稿的图片文件。
   PNG  : 白底、按当前视口与 2x 像素密度导出（线稿清晰，投稿够用）。
   SVG  : 矢量导出，节点=圆、边=线、标签=text，可无限放大不失真，
          直接进Illustrator/Inkscape 排版。默认只导节点与标签，
          避免 8695 条边把文件撑到几十 MB。 */
function exportPNG(scale){
  // 下载收尾已抽到通用函数 __dlPNG（DL_JS，见文件更下方），供作者画布复用。
  // 本函数保留原函数名与调用契约，绘制/离屏放大逻辑与其保持一致。
  window.__dlPNG(cv, scale || 2, 'cooccurrence-network.png');
}
function exportSVG(includeEdges){
  const w = cv.clientWidth, h = cv.clientHeight;
  const ns = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(ns,'svg');
  svg.setAttribute('xmlns', ns);
  svg.setAttribute('width', w); svg.setAttribute('height', h);
  svg.setAttribute('viewBox', `0 0 ${w} ${h}`);
  const bg = document.createElementNS(ns,'rect');
  bg.setAttribute('width', w); bg.setAttribute('height', h);
  bg.setAttribute('fill', '#ffffff');
  svg.appendChild(bg);
  // 边（可选）
  if(includeEdges){
    const g = document.createElementNS(ns,'g');
    g.setAttribute('stroke-width','0.5');
    for(const e of E){
      const a = N[idx[e.s]], b = N[idx[e.t]];
      if(!a||!b||!visible(a)||!visible(b)) continue;
      if(sel!==null && e.s!==sel && e.t!==sel) continue;
      const ln = document.createElementNS(ns,'line');
      ln.setAttribute('x1', sx(a).toFixed(1)); ln.setAttribute('y1', sy(a).toFixed(1));
      ln.setAttribute('x2', sx(b).toFixed(1)); ln.setAttribute('y2', sy(b).toFixed(1));
      const same = (a.pc!=null && a.pc===b.pc);
      const noPc = (a.pc==null && b.pc==null);
      // v1.0.0：无主题归属时按权重上蓝色（梯度中档），不再一律灰
      const c = same ? PAL[cidx.get(a.pc) ?? 0]
                     : (noPc ? '#60A5FA' : '#999');
      ln.setAttribute('stroke', c);
      ln.setAttribute('stroke-opacity', same ? '0.35' : (noPc ? '0.35' : '0.15'));
      g.appendChild(ln);
    }
    svg.appendChild(g);
  }
  // 节点
  const gn = document.createElementNS(ns,'g');
  for(const d of N){
    if(!visible(d)) continue;
    const X = sx(d), Y = sy(d), r = radiusOf(d);
    if(X<-20||X>w+20||Y<-20||Y>h+20) continue;
    const c = document.createElementNS(ns,'circle');
    c.setAttribute('cx', X.toFixed(1)); c.setAttribute('cy', Y.toFixed(1));
    c.setAttribute('r', r.toFixed(1));
    c.setAttribute('fill', colorOf(d));
    c.setAttribute('stroke', 'rgba(20,20,20,0.35)');
    c.setAttribute('stroke-width','0.7');
    gn.appendChild(c);
  }
  svg.appendChild(gn);
  // 标签：复用当前帧已避让的逻辑重跑一遍，保证与屏幕一致
  const gt = document.createElementNS(ns,'g');
  gt.setAttribute('font-family','-apple-system,"PingFang SC",sans-serif');
  gt.setAttribute('font-size','11'); gt.setAttribute('text-anchor','middle');
  const budget = labelBudget();
  const cands = [];
  for(const i of byDeg){
    if(cands.length>=budget) break;
    const d = N[i];
    if(!visible(d)) continue;
    const X = sx(d), Y = sy(d);
    if(X<0||X>w||Y<0||Y>h) continue;
    cands.push(d);
  }
  for(const d of cands){
    const X = sx(d), Y = sy(d), r = radiusOf(d);
    const t = document.createElementNS(ns,'text');
    t.setAttribute('x', X.toFixed(1));
    t.setAttribute('y', (Y-r-3).toFixed(1));
    t.setAttribute('fill', '#2c2c2a');
    t.textContent = d.id;
    gt.appendChild(t);
  }
  svg.appendChild(gt);
  // 序列化与下载收尾抽到通用函数 __dlSVG（DL_JS），供作者画布复用
  window.__dlSVG(svg, 'cooccurrence-network.svg');
}

/* ---------- 键盘快捷键 ---------- */
window.addEventListener('keydown', e=>{
  if(e.target && /^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName)) return;
  const cx = cv.clientWidth/2, cy = cv.clientHeight/2;
  const k = e.key;
  if(k==='='||k==='+'){                    // 放大 1.25x（以视口中心为锚）
    const nk=Math.min(9, vk*1.25);
    vx = cx-(cx-vx)*(nk/vk); vy = cy-(cy-vy)*(nk/vk); vk=nk; invalidate(); e.preventDefault();
  }else if(k==='-'||k==='_'){              // 缩小
    const nk=Math.max(0.12, vk/1.25);
    vx = cx-(cx-vx)*(nk/vk); vy = cy-(cy-vy)*(nk/vk); vk=nk; invalidate(); e.preventDefault();
  }else if(k==='0'){                // 复位视口
    vInit=false; invalidate(); e.preventDefault();
  }else if(k==='r'||k==='R'){              // 复位节点位置
    resetLayout(); e.preventDefault();
  }else if(k==='1'){ setViewMode('topic'); e.preventDefault();
  }else if(k==='2'){ setViewMode('overlay'); e.preventDefault();
  }else if(k==='3'){ setViewMode('density'); e.preventDefault();
  }else if(k==='4'){ setViewMode('yearring'); e.preventDefault();
  }else if(k==='Escape'){                   // 取消选中/主题聚焦
    sel=null; nbrs=new Set(); focusTopic=null;
    document.querySelectorAll('.lg-item,.tmap-item').forEach(x=>x.classList.remove('on'));
    renderSide(); invalidate(); e.preventDefault();
  }
});

/* ---------- 复位按钮 ---------- */
const rst = document.getElementById('resetLayout');
if(rst){ rst.onclick = ()=>{ resetLayout(); tip(null); }; }
document.querySelectorAll('.viewbtn').forEach(b=>{
  b.onclick = ()=> setViewMode(b.dataset.view);
});
// 线宽/ 节点大小滑杆：改全局倍率后重绘（不需要重算布局，代价极低）
const _ct=document.getElementById('canvasTheme');
if(_ct){ _ct.onchange = ()=>{
  CANVAS_THEME = _ct.value;
  const wr=document.querySelector('.canvaswrap');
  if(wr) wr.style.background = (CANVAS_THEME==='dark') ? '#0B0E13' : '#FFFFFF';
  densLegendGradient();               // 竖向色标随深浅主题换梯度
  invalidate(); }; }
const _es=document.getElementById('edgeStyle');
if(_es){ _es.onchange = ()=>{ EDGE_STYLE = _es.value; updateViewSummary(); invalidate(); }; }
const _ew=document.getElementById('edgeW'), _ns=document.getElementById('nodeS');
if(_ew){ _ew.oninput = ()=>{ EDGE_W_SCALE = _ew.value/38; updateViewSummary(); invalidate(); }; }
if(_ns){ _ns.oninput = ()=>{ NODE_S_SCALE = _ns.value/100; updateViewSummary(); invalidate(); }; }
const bpng = document.getElementById('exportPNG');
if(bpng){ bpng.onclick = ()=>{ draw(); exportPNG(2); }; }
const bsvg = document.getElementById('exportSVG');
if(bsvg){ bsvg.onclick = ()=>{ draw(); exportSVG(false); }; }
/* 供"图表保存"统一分发器（FIGSAVE_JS 的 __NET_EXPORTS 契约）转发。
   保留上面的直接绑定：即使 FIGSAVE 未加载/被禁用，按钮自身也能导出。 */
window.__NET_EXPORTS = window.__NET_EXPORTS || {};
window.__NET_EXPORTS.kwnet = { png: function(){ draw(); exportPNG(2); },
                               svg: function(){ draw(); exportSVG(false); } };

/* 主题聚焦：画布上方的「主题 ↔ Top 关键词」对照条与图例走同一套逻辑。
   两处都必须绑，否则上方对照条点了没反应。 */
document.querySelectorAll('.lg-item,.tmap-item').forEach(el=>{
  if(el.dataset.cid === undefined) return;
  el.onclick = ()=>{
    const c = el.dataset.cid;
    const v = c==='__none__' ? null : parseInt(c,10);
    focusTopic = (focusTopic===v && c!=='__none__') ? null : v;
    document.querySelectorAll('.lg-item,.tmap-item').forEach(x=>
      x.classList.toggle('on', x.dataset.cid===c && focusTopic!==null));
    sel=null; nbrs=new Set();
    // 聚焦 / 取消聚焦后必须重新贴合视口：只画一个主题的节点，
    // 却仍按全库包围盒缩放 → 子集被压成一小团。
    vInit = false;
    renderSide();
    invalidate();
  };
});

/* ---------- 侧栏：该主题的关键词列表（按 degree 排序） ----------
   [!]  安全：此处**曾**是零点击 DOM XSS —— 用 innerHTML 拼
   `<span class="kw" data-id="${d.id}">${d.id}<small>...`，
   关键词来自外部导入属不可信输入；首屏即执行 renderSide()，
   实测关键词 `<img src=x onerror=alert(1)>` 打开页面立即触发，
   且含引号的关键词会截断 data-id 属性导致节点身份丢失。
   现改为**纯 DOM 构建**：textContent 天然转义，
   data-id 用 setAttribute（浏览器自动转义属性值）。 */
function kwNode(d){
  // [结构] 色点 + 关键词 + 连接数 + 主题名
  // [!] 主题名是必需项：此前只有色点，用户无法从颜色反查归属，
  //     必须点进图例才知道这个词属于哪个主题。
  const s = document.createElement('span');
  s.className = 'kw';
  s.dataset.id = String(d.id);
  s.title = String(d.id) + '｜连接数 ' + (d.degree||0) +
            '｜主题 ' + (topicNameOf(d) || '未知') + '（点击高亮）';
  const i = document.createElement('i');          // 主题色点
  i.style.background = colorOf(d);
  const t = document.createElement('span');// 关键词文本
  t.className = 'kt';
  t.textContent = String(d.id);
  const sm = document.createElement('small');     // 连接数
  sm.className = 'kd';
  sm.textContent = String(d.degree||0);
  const tn = document.createElement('em');        // 主题名
  tn.className = 'kb';
  const _n = topicNameOf(d);
  tn.textContent = _n || '未归类';
  if(_n) tn.title = '所属主题：' + _n;
  s.appendChild(i); s.appendChild(t); s.appendChild(sm); s.appendChild(tn);
  return s;
}

/* 节点 → 主题名。数据侧已有命名结果时直接取，避免前端重复实现 */
function topicNameOf(d){
  const m = META[d.pc] || {};
  return m.label || m.name || '';
}
function renderSide(){
  const el = document.getElementById('side');
  const head = document.getElementById('sidehead');
  if(!el) return;
  el.textContent = '';                      // 清空，不复用 innerHTML
  /* 未聚焦任何主题时，**不再**在画布下方重复铺一份 Top 40 关键词清单。
     画布上方已有按连接数分档的「关键词全景」，同一屏出现两份同样的清单
     既是冗余、也把读者的注意力从图上拉走。这里改为给操作引导。 */
  if(focusTopic===null){
    head.textContent = '怎么看这张图';
    const p = document.createElement('p');
    p.className = 'sidehint';
    p.textContent = '把鼠标移到画布上任意节点：工具栏会显示该关键词的文献数、'
      + '连接数与所属主题。点击节点可高亮它的邻居，点击上方任一主题可只看该主题。'
      + '完整关键词清单见画布上方的「关键词全景」。';
    el.appendChild(p);
    return;
  }
  const m = META[focusTopic]||{};
  head.textContent = '主题'+focusTopic+'（'+(m.size||'?')+' 篇）· 关键词 '+
    N.filter(d=>d.pc===focusTopic).length+' 个';
  const list = N.filter(d=>d.pc===focusTopic)
            .sort((a,b)=>(b.degree||0)-(a.degree||0)).slice(0,80);
  const frag = document.createDocumentFragment();
  for(const d of list) frag.appendChild(kwNode(d));
  el.appendChild(frag);
  el.querySelectorAll('.kw').forEach(s=>{
    s.onmouseenter = ()=>{ hov = s.dataset.id; invalidate(); tip(hov); };
    s.onmouseleave = ()=>{ hov = null; invalidate(); tip(null); };
    s.onclick = ()=>{
      sel = (sel===s.dataset.id) ? null : s.dataset.id;
      nbrs = new Set();
      if(sel) for(const e2 of E){
        if(e2.s===sel) nbrs.add(e2.t);
        else if(e2.t===sel) nbrs.add(e2.s);
      }
      invalidate();
    };
  });
}

/* ---------- 灰显开关（保留原功能） ---------- */
document.querySelectorAll('.k[data-off], .chip[data-off]').forEach(c=>{
  c.onclick=()=>{ const id=c.dataset.off;
    if(hidden.has(id)){hidden.delete(id);c.classList.remove('off');}
    else{hidden.add(id);c.classList.add('off');}
    invalidate(); };
});

/* ---------- 渲染调度（按需重绘，非常驻 60fps）----------
   [!]  不可写成无条件 rAF 死循环：10672 条边每帧重绘会持续占用 CPU/GPU，
   页面即使静止也在满载耗电。这里用 dirty 标志做「脏才重绘」——
   交互（hover/点击/缩放/图例）置脏，下一帧才画；静止时 0 开销。 */
let raf = null;
function schedule(){
  if(raf) return;                 // 同一帧内合并多次 invalidate
  raf = requestAnimationFrame(()=>{ raf = null; if(dirty.v){ dirty.v = false; draw(); } });
}
function invalidate(){ dirty.v = true; schedule(); }
cv.parentElement.style.position='relative';
renderSide();
tip(null);
updateViewSummary();                 // 折叠态摘要与初始视角（按主题）保持一致
densLegendGradient();                // 初始化竖向密度色标的梯度（默认视图下隐藏）
dirty.v = true; schedule();          // 首帧
window.addEventListener('resize', ()=>{ vInit=false; invalidate(); });
/* 尺寸变化必须重新 fitView。
   window.resize 只在**窗口**变化时触发；左栏折叠、卡片展开、
   手机端旋转、容器由 0 宽变有宽……这些都不会触发它，
   画布却已经换了尺寸 —— 旧视口残留会让图跑到画布外（表现为"空白"）。
   ResizeObserver 覆盖全部这些情况，并在首次 observe 时补一帧。 */
if(window.ResizeObserver){
  let lw = -1, lh = -1;
  new ResizeObserver(()=>{
    const w = cv.clientWidth, h = cv.clientHeight;
    if(w === lw && h === lh) return;         // 过滤亚像素抖动
    lw = w; lh = h;
    if(w < 2 || h < 2) return;
    vInit = false; invalidate();
  }).observe(cv);
}

// 暴露给性能实测（浏览器控制台 / 自动化脚本可读）
window.__NETPERF__ = () => ({frameMs:lastMs, nodes:N.length, edges:E.length,
                             zoom:vk, focusTopic, selected:sel,
                             labels:lastLabels, visible:N.length,
                             posDecoded:hasXY,
                             // 交互状态：供自动化验证触摸/鼠标手势是否生效
                             panX:vx, panY:vy, movedNodes:moved.size,
                             viewMode, touchPointers:activePointers.size,
                             panning:ptActive, pinching});
// 手动重绘一帧（供 Node 侧性能实测脚本驱动，避免依赖 rAF）
window.__PUMP__ = () => draw();
// 测试钩子：直接按 id 选中 / 聚焦主题，不依赖鼠标命中测试
// （自动化验证交互时，合成点击常因坐标取整而命不中，属测试假阴性）
window.__TEST__ = {
  select(id){ sel = id; nbrs = new Set();
    for(const e of E){ if(e.s===sel) nbrs.add(e.t); else if(e.t===sel) nbrs.add(e.s); }
    invalidate(); },
  focus(c){ focusTopic = c; sel=null; nbrs=new Set();
            vInit=false; invalidate(); },
  hover(id){ hov = id; tip(id); invalidate(); },
  state(){ return {sel, focusTopic, nbrs:nbrs.size, labels:lastLabels, zoom:vk}; },
  nodeScreenXY(id){ const d=byId[id]; return d?[sx(d),sy(d)]:null; },
  /* 用户偏移读取：拖拽回归用它断言"拖后 ox/oy 确实变了、且重绘后仍保持、
     复位后归零"。直接读 ox/oy 比读屏幕坐标可靠 —— 屏幕坐标还含视口缩放/平移，
     复位视口也会改动它，无法把"节点被拖动"与"视口被重置"区分开。 */
  nodeOffset(id){ const d=byId[id]; return d?{ox:d.ox||0,oy:d.oy||0,moved:moved.has(id)}:null; },
  topIds(n){ return byDeg.slice(0,n).map(i=>N[i].id); },
  /* 视图切换出口：供 run_checks.py 回归断言"每个视图都能无异常渲染"，
     也供自动化测试直接驱动，无需人工点按钮。 */
  setView(m){ setViewMode(m); draw(); return viewMode; },
  view(){ return viewMode; },
  hasKeywordNet(){ return !!(KW && KW.nodes && KW.nodes.length); },
  /* 布局体检：回归测试用它断言「没有任何节点的坐标是 NaN/Inf」。
     自检不能只数绘制调用次数——ctx.arc(NaN,NaN,...) 照样计数，
     「整张图全 NaN、页面一片空白」也能判 PASS；必须把布局本身
     暴露成数值断言才守得住。 */
  layoutSanity(){
    let bad = 0, minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    for(const d of N){
      if(!Number.isFinite(d.px) || !Number.isFinite(d.py)){ bad++; continue; }
      if(d.px < minX) minX = d.px; if(d.px > maxX) maxX = d.px;
      if(d.py < minY) minY = d.py; if(d.py > maxY) maxY = d.py;
    }
    return {total:N.length, badXY:bad, spanX:maxX-minX, spanY:maxY-minY,
            maxDeg, zoom:vk};
  },
  /* 各视图的渲染证据：由 drawDensity / drawYearRing 写入。
     contrast = 最密处颜色相对画布底色的最大通道差（低于约 30/255 即不可辨）。 */
  renderEvidence(){
    return {density: window.__DENSITY__ || null,
            yearring: window.__YEARRING__ || null};
  },
};
})();
"""

# 图像导出的「下载收尾」抽成通用函数，供**两张画布**（关键词共现 / 作者共现）共用。
# 为什么只抽收尾、不动绘制：作者网络是独立 canvas，但必须产出与关键词网络同格式的
# PNG/SVG，否则同一份报告里会出现两套下载行为。收尾逻辑（离屏放大、blob→a.click）
# 两张图完全一致，故抽到这里；各画布自己的绘制/序列化仍留在各自 IIFE 内，
# 从而**逐行不改**关键词画布既有的 exportPNG/exportSVG 中间逻辑。
DL_JS = r"""
(function(){
  /* ── 保存通道与可见反馈（手机点保存没反应）───────────────
     失效表现：手机上点「保存」毫无反应。根因论证（不是猜，是技术事实）：
       ① 移动端虽已走「页内浮层 + 长按保存」，但浮层 <img> 用的是
          **blob: URL**。iOS Safari 对 blob: 图片的长按菜单**不提供**「存储图像」，
          只有 data: URL 才给出「存储到照片」—— 即"分支走对了，图源选错了"；
       ② 若整段逻辑抛异常（toBlob 不受支持 / URL.createObjectURL 被 WebView 限制），
          catch 后若只给含糊提示，用户观感仍是"点了没反应"；
       ③ 微信 / 企业微信等内置 WebView 拦截下载、也未必给长按图片菜单，
          但通常支持 navigator.share()。
     故改为「能力探测前置 + 多通道降级 + 每步可见反馈」。通道与触发条件：
       通道1 Web Share 分享文件 —— 移动端且 navigator.canShare({files:[f]}) 为真；
       通道2 页内浮层 + **data: URL** 图片 —— 长按存相册（iOS 能走通的关键）；
       通道3 新标签页打开 —— 浮层里的兜底按钮；
       通道4 直接下载 —— 桌面（**桌面优先下载**：不因 canShare 存在就弹分享面板，
              否则会抢走桌面用户的直接落盘，属行为退化）。
     9 类图的 __dlPNG / __dlSVG / __dlSVGx / __dlSVGpng 全部经由 __deliverBlob，
     故只在此处实现一次，不在 9 个调用点各改一遍。 */

  function el(tag, cls, txt){
    var e = document.createElement(tag);
    if(cls) e.className = cls;
    if(txt != null) e.textContent = txt;
    return e;
  }

  /* ── 通道判定 ──
     为什么不是单看 maxTouchPoints：带触摸屏的笔记本（Surface 等）download
     完全可用，一律改走覆盖层会白白夺走桌面用户的直接下载。故取：
       iOS（含 iPadOS 伪装成 MacIntel）→ 覆盖层；
       无 <a download> 支持 → 覆盖层；
       粗指针 + 无 hover（手机 / 平板的典型特征）→ 覆盖层；
       触摸设备且视口窄（≤820px）→ 覆盖层；其余一律走下载。 */
  function isIOS(){
    try{
      if(/iPad|iPhone|iPod/.test(navigator.userAgent || '')) return true;
      if(navigator.platform === 'MacIntel' && (navigator.maxTouchPoints || 0) > 1) return true;
    }catch(e){}
    return false;
  }
  function canDownload(){
    try{ return typeof document.createElement('a').download !== 'undefined'; }
    catch(e){ return false; }
  }
  function isCoarse(){
    try{
      if(window.matchMedia){
        if(window.matchMedia('(hover:none)').matches) return true;
        if(window.matchMedia('(pointer:coarse)').matches) return true;
      }
    }catch(e){}
    return false;
  }
  function useOverlay(){
    try{
      if(isIOS()) return true;
      if(!canDownload()) return true;
      if(isCoarse()) return true;
      var mtp = 0; try{ mtp = navigator.maxTouchPoints || 0; }catch(e){}
      if(mtp > 0 && (window.innerWidth || 9999) <= 820) return true;
    }catch(e){}
    return false;
  }
  window.__useOverlay = useOverlay;     // 供探针 / 调试断言通道选择

  /* ── 能力探测：必须在真实调用前做，不允许在 try 里撞运气 ──
     canShareFiles 直接问浏览器"这个文件你能不能通过系统分享出去"，返回 false 时
     就绝不调 navigator.share（否则在部分 WebView 上会抛错或静默失败）。
     注意 canShare 存在 ≠ 支持 files：必须用 {files:[file]} 实探。 */
  function canShareFiles(file){
    try{
      return !!(navigator.canShare && typeof navigator.share === 'function'
                && navigator.canShare({files:[file]}));
    }catch(e){ return false; }
  }
  // 构造分享 / 保存用的 File（带正确 MIME）。旧内核可能没有 File 构造器 → 返回
  // null，调用方据此降级到浮层，绝不因"造 File 失败"而整体静默。
  function makeFile(blob, name, kind){
    try{
      var type = (blob && blob.type) || (kind === 'svg' ? 'image/svg+xml' : 'image/png');
      return new File([blob], name || 'figure', {type:type});
    }catch(e){ return null; }
  }

  /* ── 提示条：任何一次保存（成功或失败）都不允许静默 ── */
  var _toast = null, _toastMsg = null, _toastT = null;
  function toast(msg, kind){
    try{
      if(!_toast){
        _toast = el('div', 'figtoast');
        _toast.setAttribute('role', 'status');
        _toast.setAttribute('aria-live', 'polite');
        _toastMsg = el('span', 'figtoast-msg', '');
        _toast.appendChild(_toastMsg);
        document.body.appendChild(_toast);
      }
      _toast.className = 'figtoast is-show' + (kind === 'err' ? ' is-err' : '');
      // 直接持有文本节点引用，不靠 querySelector —— 最小 DOM 环境（探针沙箱）
      // 下 querySelector 可能返回 null，会让提示本身抛错，反而变成"静默失败"。
      _toastMsg.textContent = String(msg);
      if(_toastT) clearTimeout(_toastT);
      // 失败信息留久一点，用户需要看清原因
      _toastT = setTimeout(function(){ try{ _toast.className = 'figtoast'; }catch(e){} },
                           kind === 'err' ? 6000 : 3600);
    }catch(e){ if(window.console) console.warn('[figsave]', e); }
  }
  window.__figToast = toast;

  /* ── 按钮忙碌态 ──
     用 document 捕获阶段委托，而不是逐个改各图自身的 onclick：15 个保存入口的
     onclick 分散在 JS_NET / AUTH_JS / FIGSAVE_JS 三段里且互相覆盖，逐个包一层
     既易漏又脆弱。委托与它们完全解耦，并且能覆盖真实点按（含直接绑定 onclick
     的路径）。已在生成中的按钮：吞掉重复点击（除 disabled 外再加一道，
     因为部分浏览器对 disabled 元素 in-flight click 的处理并不一致）。 */
  var _busyBtn = null;
  try{
    document.addEventListener('click', function(ev){
      var t = ev.target;
      while(t && t.classList){
        if(t.classList.contains('fbtn')){
          if(t.__figBusy){                       // 生成中：吞掉这一次重复点击
            if(ev.stopPropagation) ev.stopPropagation();
            if(ev.preventDefault) ev.preventDefault();
            return;
          }
          setBusy(t);
          break;
        }
        t = t.parentNode;
      }
    }, true);
  }catch(e){}
  function setBusy(btn){
    _busyBtn = btn;
    try{
      if(btn.__figOrig == null) btn.__figOrig = btn.textContent;
      btn.__figBusy = true;
      btn.disabled = true;
      if(btn.classList && btn.classList.add) btn.classList.add('is-busy');
      btn.textContent = '生成中…';
    }catch(e){}
  }
  // 收尾：恢复按钮 + 弹提示。btn 为 null（探针直接调用）时只弹提示。
  function finish(btn, ok, msg){
    try{
      if(btn){
        btn.disabled = false;
        btn.__figBusy = false;
        if(btn.classList && btn.classList.remove) btn.classList.remove('is-busy');
        if(btn.__figOrig != null) btn.textContent = btn.__figOrig;
      }
    }catch(e){}
    toast(msg, ok ? 'ok' : 'err');
  }
  // 同步失败（图元素缺失 / 未注册导出 / 抛异常）也必须解掉忙碌态并给出原因，
  // 否则按钮会永远停在「生成中…」。
  window.__figAbort = function(msg){
    var btn = _busyBtn; _busyBtn = null;
    finish(btn, false, msg || '保存失败');
  };

  /* ── 移动端覆盖层：展示图片 + 长按保存引导 ──
     图源必须是 data: URL（见文件头注 ①；blob: 在 iOS 长按不出「存储图像」）。
     blob → dataURL 走 FileReader，异步且失败必须 catch 并降级，绝不静默。 */
  var _ovl = null;
  function closeOverlay(){
    try{ if(_ovl && _ovl.parentNode) _ovl.parentNode.removeChild(_ovl); }catch(e){}
    _ovl = null;
  }
  window.__figCloseOverlay = closeOverlay;
  // 写进新标签页 / HTML 文本时的最小转义（命名可能带引号或尖括号）
  function escHtml(s){
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
  function blobToDataURL(blob, cb){
    try{
      if(typeof FileReader === 'undefined'){
        cb(null, new Error('当前环境不支持 FileReader')); return;
      }
      var fr = new FileReader();
      fr.onload = function(){ cb(String(fr.result || ''), null); };
      fr.onerror = function(){ cb(null, (fr && fr.error) || new Error('读取图片数据失败')); };
      fr.readAsDataURL(blob);
    }catch(e){ cb(null, e); }
  }
  /* 通道3：新标签页打开。不直接导航到 data: URL（被多数浏览器拦截），而是
     window.open('') 拿到同源空白页后写入 <img>，用户可在新页长按 / 用浏览器菜单存。 */
  function openInNewTab(dataUrl, name){
    try{
      var w = window.open('', '_blank');
      if(w && w.document){
        w.document.write(
          '<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1">'
          + '<title>' + escHtml(name) + '</title>'
          + '<body style="margin:0;background:#fff">'
          + '<img src="' + dataUrl + '" style="max-width:100%;display:block;margin:0 auto">');
        try{ w.document.close(); }catch(e){}
        toast('已在新标签页打开，可长按图片或用浏览器菜单保存');
        return true;
      }
    }catch(e){}
    toast('无法打开新标签页：请改用长按图片保存', 'err');
    return false;
  }
  /* 通道1：分享文件。share 可能**同步 throw**，也可能返回 **rejected promise**；
     两种都要走同一个 fallback 降级（交给调用方决定降到浮层还是下载）。 */
  function shareFile(file, btn, name, kind, fallback){
    var p = null;
    try{
      p = navigator.share({files:[file], title:name});
    }catch(e){
      if(fallback) fallback(e);
      else finish(btn, false, '分享失败：' + (e && e.message || e));
      return;
    }
    if(p && typeof p.then === 'function'){
      p.then(function(){
        finish(btn, true, '已打开系统分享，选择「存储到照片」即可保存');
      }, function(err){
        if(fallback) fallback(err);
        else finish(btn, false, '分享未完成：' + (err && err.message || err || '已取消'));
      });
    }else{
      finish(btn, true, '已打开系统分享');
    }
  }
  function showOverlay(imgUrl, file, name, kind){
    closeOverlay();                 // 同一时刻只留一个覆盖层
    var ov = el('div', 'figoverlay');
    ov.setAttribute('role', 'dialog');
    ov.setAttribute('aria-modal', 'true');
    var box = el('div', 'figoverlay-box');
    var hd = el('div', 'figoverlay-hd');
    hd.appendChild(el('span', 'figoverlay-title', name || '图片已生成'));
    var x = el('button', 'figoverlay-close', '关闭');
    x.setAttribute('type', 'button');
    x.onclick = closeOverlay;
    hd.appendChild(x);
    box.appendChild(hd);
    var img = el('img', 'figoverlay-img');
    img.setAttribute('alt', name || '导出的图片');
    img.src = imgUrl;               // data: URL —— iOS 长按才会出现「存储到照片」
    box.appendChild(img);
    // SVG 在 iOS 上常常长按也存不进相册 → 明确引导改存 PNG，不让用户干瞪眼
    box.appendChild(el('p', 'figoverlay-hint',
      kind === 'svg'
        ? '长按图片可保存到相册；若系统不支持保存 SVG，请改用本图卡片里的「保存 PNG」。'
        : '长按图片保存到相册'));
    // 按钮区：分享/保存（通道1，仅当实探支持分享文件）+ 在新标签页打开（通道3）
    var acts = el('div', 'figoverlay-actions');
    if(file && canShareFiles(file)){
      var bShare = el('button', 'figoverlay-act is-primary', '分享 / 保存');
      bShare.setAttribute('type', 'button');
      bShare.onclick = function(){
        // 这里由**用户手势**直接触发 share，避免了 toBlob 回调里丢手势的问题
        shareFile(file, null, name, kind, function(err2){
          toast('分享未完成：' + (err2 && err2.message || err2 || '已取消')
                + '，可长按图片保存', 'err');
        });
      };
      acts.appendChild(bShare);
    }
    var bOpen = el('button', 'figoverlay-act', '在新标签页打开');
    bOpen.setAttribute('type', 'button');
    bOpen.onclick = function(){ openInNewTab(imgUrl, name); };
    acts.appendChild(bOpen);
    box.appendChild(acts);
    ov.appendChild(box);
    // 点背景也关闭（手机上关闭按钮可能被系统手势挡住）
    ov.onclick = function(ev){ if(ev.target === ov) closeOverlay(); };
    document.body.appendChild(ov);
    _ovl = ov;
  }

  /* SVG → PNG 的 best-effort 转换：iOS 对 SVG 支持最差，转成 PNG 再长按成功率高。
     任一步失败都回 cb(null)，由调用方退回"显示 SVG 原图 + 引导点保存 PNG"。 */
  function svgDataUrlToPng(svgUrl, cb){
    try{
      if(typeof Image === 'undefined'){ cb(null); return; }
      var img = new Image();
      img.onload = function(){
        try{
          var cv = document.createElement('canvas');
          var w = img.width || 880, h = img.height || 420;
          cv.width = w; cv.height = h;
          var o = cv.getContext('2d');
          if(!o){ cb(null); return; }
          o.fillStyle = '#fff'; o.fillRect(0, 0, w, h);
          o.drawImage(img, 0, 0, w, h);
          cb(cv.toDataURL ? cv.toDataURL('image/png') : null);
        }catch(e){ cb(null); }
      };
      img.onerror = function(){ cb(null); };
      img.src = svgUrl;
    }catch(e){ cb(null); }
  }

  /* ── 通道2 交付：blob → data: URL → 浮层（+SVG 尝试转 PNG）── */
  function deliverOverlay(blob, file, name, kind, btn){
    blobToDataURL(blob, function(dataUrl, err){
      if(!dataUrl){
        // 转换失败：必须给出**具体原因**（is-err 可见错误），并尝试降级
        // （能下载就下载），不允许静默。
        if(canDownload()){
          try{
            var u = URL.createObjectURL(blob);
            download(u, name);
            setTimeout(function(){ try{ URL.revokeObjectURL(u); }catch(e){} }, 30000);
            finish(btn, false, '当前浏览器无法把图片转成可长按保存的格式，已改为直接下载 '
                   + (name || '') + '（原因：' + (err && err.message || err || '未知') + '）');
          }catch(e){
            finish(btn, false, '保存失败：' + (err && err.message || err || e));
          }
        }else{
          finish(btn, false, '保存失败：无法转换为可长按保存的图片（'
                 + (err && err.message || err || '未知原因') + '）');
        }
        return;
      }
      if(kind === 'svg'){
        svgDataUrlToPng(dataUrl, function(pngUrl){
          if(pngUrl){
            showOverlay(pngUrl, file, name, 'png');
            finish(btn, true, '已自动转为 PNG，长按图片即可保存到相册');
          }else{
            showOverlay(dataUrl, file, name, 'svg');
            finish(btn, true, '图片已生成，长按图片即可保存；若系统不支持保存 SVG，请改用「保存 PNG」');
          }
        });
      }else{
        showOverlay(dataUrl, file, name, kind);
        finish(btn, true, '图片已生成，长按图片即可保存到相册');
      }
    });
  }

  /* ── 桌面下载：<a> 必须挂进文档再 click ── */
  function download(url, name){
    var a = document.createElement('a');
    a.href = url;
    if(name) a.download = name;
    a.rel = 'noopener';
    a.style.display = 'none';
    document.body.appendChild(a);
    a.click();
    // 用完立刻移除，避免每次保存都往 DOM 里堆一个隐藏节点
    setTimeout(function(){ try{ if(a.parentNode) a.parentNode.removeChild(a); }catch(e){} }, 0);
  }

  /* ── 统一收尾：blob → 通道（桌面下载 / 移动分享 / 浮层长按）──
     通道选择（能力探测前置）：
       · 桌面（useOverlay()===false）→ 通道4 直接下载；
       · 移动端且实探 canShare({files}) 为真 → 通道1 分享，失败自动降级浮层；
       · 其余移动端 → 通道2 浮层（data: URL + 长按）。 */
  window.__deliverBlob = function(blob, name, kind){
    var btn = _busyBtn; _busyBtn = null;
    if(!blob || (typeof blob.size === 'number' && blob.size === 0)){
      finish(btn, false, '生成失败：图片数据为空（该图在当前浏览器可能无法渲染）');
      return;
    }
    var file = makeFile(blob, name, kind);
    if(!useOverlay()){
      // 通道4：桌面直接下载（保持既有行为：先 appendChild 再 click、文件名带图表名）
      var url;
      try{ url = URL.createObjectURL(blob); }
      catch(e){ finish(btn, false, '保存失败：无法创建下载地址（' + (e && e.message || e) + '）'); return; }
      try{
        download(url, name);
        finish(btn, true, '已保存 ' + (name || '图片'));
        /* 延迟释放：慢设备上文件可能还没真正写盘就失效（表现仍是"点了没反应"）。
           30s 足够；浮层通道用 dataURL，不涉及 objectURL 释放。 */
        setTimeout(function(){ try{ URL.revokeObjectURL(url); }catch(e){} }, 30000);
      }catch(e){
        try{ URL.revokeObjectURL(url); }catch(e2){}
        finish(btn, false, '保存失败：' + (e && e.message ? e.message : e));
      }
      return;
    }
    // 移动端：能分享文件就先分享；同步 throw / reject 都降级到浮层
    if(file && canShareFiles(file)){
      shareFile(file, btn, name, kind, function(){
        deliverOverlay(blob, file, name, kind, btn);
      });
      return;
    }
    deliverOverlay(blob, file, name, kind, btn);
  };

  // 按 scale 倍离屏放大后导出**白底** PNG（投稿/打印用白底，与屏幕观感无关）
  // [!]  宽度必须 clientWidth 回落到 .width：HTML 表格 / 柱条类图没有现成画布，
  //   它们是"先用 canvas 重绘、再导出"的 —— 那块画布是离屏创建的，clientWidth=0。
  //   若只读 clientWidth，导出会得到 0×0 的空白图且**不报错**（静默失败）。
  window.__dlPNG = function(canvasEl, scale, name){
    scale = scale || 2;
    const w = canvasEl.clientWidth || canvasEl.width || 0;
    const h = canvasEl.clientHeight || canvasEl.height || 0;
    if(!w || !h){
      // 尺寸为 0 时不画空白图充数：明确报失败，杜绝静默 0×0 空白图
      window.__figAbort('导出失败：该图当前尺寸为 0（可能尚未完成渲染）');
      return;
    }
    const ov = document.createElement('canvas');
    ov.width = Math.round(w*scale); ov.height = Math.round(h*scale);
    const o = ov.getContext('2d');
    o.setTransform(scale,0,0,scale,0,0);
    o.fillStyle = '#fff'; o.fillRect(0,0,w,h);
    o.drawImage(canvasEl, 0, 0, w, h);
    try{
      // toBlob 失败会回调 null —— 直接 createObjectURL(null) 会抛错并被吞掉；
      // 现在走 __deliverBlob 的"数据为空"显式失败分支。
      ov.toBlob(function(b){ window.__deliverBlob(b, name, 'png'); }, 'image/png');
    }catch(e){
      window.__figAbort('导出失败：本浏览器不支持 canvas 导出（' + (e && e.message || e) + '）');
    }
  };
  // 序列化 + 交付 SVG（节点/边/标签由调用方自建 DOM）
  window.__dlSVG = function(svgEl, name){
    try{
      const blob = new Blob(
        ['<?xml version="1.0" encoding="UTF-8"?>\n'+new XMLSerializer().serializeToString(svgEl)],
        {type:'image/svg+xml'});
      window.__deliverBlob(blob, name, 'svg');
    }catch(e){
      window.__figAbort('导出 SVG 失败：' + (e && e.message || e));
    }
  };

  /* ── 内联 SVG 的「自包含化」──
     报告内联的 SVG（发文量折线 .pline、关键词时间线 .tlsvg）取色用的是页面
     CSS 变量（fill="var(--ac)"）与 <style> 里的类。一旦把 SVG 单独存成 .svg，
     或塞进 <img> 光栅化，**页面样式不再作用**：var() 解析失败 → 图形退化成
     黑色/透明，导出的图与屏幕根本不是一张（这是"图能存但不能用"的隐藏坑）。
     故导出前用 getComputedStyle 把可视样式固化成元素内联 style —— 内联声明
     优先级最高，且值已是解析后的 rgb()，产物可独立渲染。 */
  const SVG_STYLE_PROPS = ['fill','fill-opacity','stroke','stroke-width','stroke-opacity',
    'stroke-dasharray','stroke-linecap','stroke-linejoin','opacity','font-family','font-size',
    'font-weight','font-style','text-anchor','dominant-baseline','letter-spacing','visibility'];
  window.__svgInline = function(svgEl){
    const clone = svgEl.cloneNode(true);
    if(!window.getComputedStyle) return clone;
    const src = [svgEl].concat(Array.prototype.slice.call(svgEl.querySelectorAll('*')));
    const dst = [clone].concat(Array.prototype.slice.call(clone.querySelectorAll('*')));
    for(let i=0;i<src.length && i<dst.length;i++){
      let cs = null;
      try{ cs = window.getComputedStyle(src[i]); }catch(e){ cs = null; }
      if(!cs) continue;
      let decl = '';
      for(const p of SVG_STYLE_PROPS){
        let v = '';
        try{ v = cs.getPropertyValue(p); }catch(e){ v = ''; }
        if(v) decl += p+':'+v+';';
      }
      if(decl) dst[i].setAttribute('style', decl);
    }
    // 保证能被 <img> / 其它软件加载
    clone.setAttribute('xmlns','http://www.w3.org/2000/svg');
    return clone;
  };
  // 导出"自包含 SVG"（SVG 类图的矢量保存通道，图表 1/3 用）
  window.__dlSVGx = function(svgEl, name){ window.__dlSVG(window.__svgInline(svgEl), name); };
  // 把 SVG 光栅化成 PNG：自包含化 → data URL → Image → 离屏 canvas → 统一收尾。
  // 为什么不用 foreignObject 包 HTML：见 FIGSAVE_JS 头注。
  window.__dlSVGpng = function(svgEl, scale, name){
    scale = scale || 2;
    const inline = window.__svgInline(svgEl);
    const xml = new XMLSerializer().serializeToString(inline);
    let w = svgEl.clientWidth, h = svgEl.clientHeight;
    if(!w || !h){
      const vb = (svgEl.getAttribute('viewBox')||'').split(/[\s,]+/).map(Number);
      if(vb.length === 4){ w = vb[2]; h = vb[3]; }
    }
    if(!w || !h){ w = 880; h = 420; }
    if(typeof Image === 'undefined'){
      // 无 Image（无头/自动化环境）→ 退化为交付 SVG，绝不静默丢图；
      // 同时明确告知"你要的是 PNG，但当前环境给不出"，而不是悄悄换格式。
      window.__figToast('当前环境无法把 SVG 转成 PNG，已改为提供 SVG 源图', 'err');
      window.__dlSVG(inline, String(name).replace(/\.png$/,'.svg')); return;
    }
    const img = new Image();
    img.onload = function(){
      const cv = document.createElement('canvas');
      cv.width = Math.round(w*scale); cv.height = Math.round(h*scale);
      const o = cv.getContext('2d');
      o.fillStyle = '#fff'; o.fillRect(0,0,cv.width,cv.height);
      o.drawImage(img, 0, 0, cv.width, cv.height);
      window.__dlPNG(cv, 1, name);   // 已在目标分辨率绘制，scale=1 不再二次放大
    };
    img.onerror = function(){
      // Safari 对部分内联 SVG 不兼容 → 光栅化失败。明确提示并回退为 SVG 源图，
      // 明确提示改供 SVG 源图，不"悄悄改成 SVG、让用户以为存的是 PNG"。
      window.__figToast('该浏览器无法把此 SVG 渲染为 PNG，已改为提供 SVG 源图', 'err');
      window.__dlSVG(inline, String(name).replace(/\.png$/,'.svg'));
    };
    img.src = 'data:image/svg+xml;charset=utf-8,'+encodeURIComponent(xml);
  };
})();
"""

# ── 图表保存（任务 B）──────────────────────────────────────────────
# 为什么单独一段 + 统一入口：
#   报告里有三种"图"：① 内联 SVG（发文量折线 / 关键词时间线）；② HTML 表格或
#   条块（主题×年份热力图 / 突现迷你条 / 时效横条）；③ canvas 画布（四张共现网络）。
#   三者底层完全不同，但用户要的是同一件事 —— "点一下把这张图存下来"。故用一个
#   声明式（data-fig / data-save）的小分发器统一绑定，按钮样式与位置也统一，
#   下载文件名带图表名，避免一串 download.png 互相覆盖。
#   [!]  HTML 表格 / 条块类图**不能**用 canvas.toDataURL 直接导出 —— 它们不是
#   canvas。方案是"用 canvas 重绘它们"（读 DOM 里真实渲染出的背景色字符串、
#   条的像素高度、文本），再复用 __dlPNG 收尾。**不**用 foreignObject 把整段
#   HTML 塞进 SVG：多数浏览器会因未实现/跨源而渲染为空或污染画布，得到的正是
#   本任务要避免的"空白图"。
#   [!]  画布网络（关键词/作者/机构/引文）不在这里重绘 —— 它们各自有 exportPNG/
#   exportSVG，本器只做转发（__NET_EXPORTS），底层仍是同一套 __dlPNG/__dlSVG。
FIGSAVE_JS = r"""
(function(){
  function q(s, r){ try{ return (r||document).querySelector(s); }catch(e){ return null; } }
  function newCanvas(w, h){
    const cv = document.createElement('canvas');
    cv.width = w; cv.height = h;
    return cv;
  }
  // 按像素宽度截断文本（canvas 不会自动省略，超出会压到邻列）
  function fitText(o, text, maxW){
    text = String(text == null ? '' : text);
    if(o.measureText(text).width <= maxW) return text;
    let t = text;
    while(t.length > 1 && o.measureText(t+'…').width > maxW) t = t.slice(0,-1);
    return t+'…';
  }

  /* 2｜主题 × 年份热力图：重绘为网格（行标签 + 带背景色的年份格 + 数字）。
     读 td.style.background（内联 rgba，屏幕所见即所得），而不是重算颜色。 */
  function drawHeatmap(table){
    if(!table || !table.rows || !table.rows.length) return null;
    const rows = Array.prototype.slice.call(table.rows);
    const S = 2, LH = 30, PAD = 12, CW = 34;
    let labelW = 100;
    for(const r of rows){
      const th = r.querySelector('th.hmrow');
      if(th) labelW = Math.max(labelW, Math.min(240, (th.textContent||'').length*13 + 16));
    }
    const head = Array.prototype.slice.call(rows[0].cells);
    const yearN = Math.max(0, head.length - 1);
    const W = PAD*2 + labelW + yearN*CW;
    const H = PAD*2 + rows.length*LH + 22;
    const cv = newCanvas(W*S, H*S);
    const o = cv.getContext('2d'); o.scale(S, S);
    o.fillStyle='#fff'; o.fillRect(0,0,W,H); o.textBaseline='middle';
    o.fillStyle='#8A9099'; o.font='11px sans-serif'; o.textAlign='center';
    for(let c=1;c<head.length;c++){
      o.fillText(String(head[c].textContent||''), PAD+labelW+(c-1)*CW+CW/2, PAD+LH/2);
    }
    for(let ri=1; ri<rows.length; ri++){
      const r = rows[ri], cells = Array.prototype.slice.call(r.cells);
      const y = PAD + (ri+0.5)*LH;
      const lab = r.querySelector('th.hmrow');
      o.fillStyle='#5A6169'; o.font='12px sans-serif'; o.textAlign='right';
      o.fillText(fitText(o, lab?lab.textContent:'', labelW-12), PAD+labelW-8, y);
      for(let c=0;c<cells.length;c++){
        const td = cells[c];
        let bg = (td.style && td.style.background) || '';
        if(!bg || bg === 'transparent' || bg === 'none') bg = '';
        const x = PAD+labelW+c*CW;
        if(bg){ o.fillStyle = bg; o.fillRect(x+1, y-(LH-6)/2, CW-2, LH-6); }
        const txt = (td.textContent||'').trim();
        if(txt){ o.fillStyle='#1A1D21'; o.font='10.5px monospace'; o.textAlign='center';
          o.fillText(txt, x+CW/2, y); }
      }
    }
    o.fillStyle='#8A9099'; o.font='11px sans-serif'; o.textAlign='left';
    o.fillText('主题 × 年份（颜色越深 = 该年文献越多）', PAD, H-PAD-4);
    return cv;
  }

  /* 5｜时效性分布横条：读每个 .b 的真实像素高度重绘 */
  function drawBars(box){
    if(!box) return null;
    const bars = Array.prototype.slice.call(box.querySelectorAll('.b'));
    if(!bars.length) return null;
    const S = 2, BH = 150, PAD = 14, gap = 8, bw = 6;
    const W = PAD*2 + bars.length*gap;
    const H = BH + PAD*2 + 18;
    const cv = newCanvas(W*S, H*S);
    const o = cv.getContext('2d'); o.scale(S, S);
    o.fillStyle='#fff'; o.fillRect(0,0,W,H);
    let maxH = 1;
    for(const b of bars) maxH = Math.max(maxH, parseFloat(b.style.height)||0);
    for(let i=0;i<bars.length;i++){
      const h = Math.max(2, (parseFloat(bars[i].style.height)||0)/maxH*BH);
      o.fillStyle='#C9761F';
      o.fillRect(PAD + i*gap, PAD+BH-h, bw, h);
    }
    o.fillStyle='#8A9099'; o.font='11px sans-serif'; o.textAlign='left';
    o.fillText('文献年份分布（柱高 = 文献数）', PAD, H-PAD-4);
    return cv;
  }

  /* 4｜突现检测的年度迷你条：把每行的 spark 重绘成小多图（一行一个词） */
  function drawSpark(table){
    if(!table) return null;
    const rows = Array.prototype.slice.call(table.querySelectorAll('tbody tr'));
    if(!rows.length) return null;
    const S=2, LH=30, LABW=190, PAD=12, CW=6;
    let maxSpans = 1;
    for(const r of rows) maxSpans = Math.max(maxSpans, r.querySelectorAll('.spark .sb').length);
    const W = PAD*2 + LABW + maxSpans*CW + 24;
    const H = PAD*2 + rows.length*LH + 20;
    const cv = newCanvas(W*S, H*S); const o = cv.getContext('2d'); o.scale(S, S);
    o.fillStyle='#fff'; o.fillRect(0,0,W,H); o.textBaseline='middle';
    for(let i=0;i<rows.length;i++){
      const r = rows[i], y = PAD + i*LH + LH/2;
      const kw = r.querySelector('td,th');
      o.fillStyle='#1A1D21'; o.font='12px sans-serif'; o.textAlign='right';
      o.fillText(fitText(o, kw?kw.textContent:'', LABW-12), PAD+LABW-8, y);
      const spans = Array.prototype.slice.call(r.querySelectorAll('.spark .sb'));
      const base = PAD+LABW;
      for(let j=0;j<spans.length;j++){
        const pct = parseFloat(spans[j].style.height)||0;        // 0..100
        const bh = Math.max(1, pct/100*18);
        o.fillStyle = /zero/.test(spans[j].className||'') ? '#D2D2C9' : '#4F46E5';
        o.fillRect(base + j*CW, y-bh/2, CW-2, bh);
      }
    }
    o.fillStyle='#8A9099'; o.font='11px sans-serif'; o.textAlign='left';
    o.fillText('关键词突现的年度分布（每行一个词，横轴为年份先后）', PAD, H-PAD-4);
    return cv;
  }

  // 键 = FIGS 里的 kind（不是 slug）：save() 用 cfg.kind 取重绘器
  const DRAWERS = {
    table: function(el){ return drawHeatmap(el); },
    bars:  function(el){ return drawBars(el); },
    spark: function(el){ return drawSpark(el); }
  };
  // 图类型登记：slug → {kind, sel}。slug 同时用于按钮 data-fig。
  // 注意 .pline / .tlsvg / table.hmtable / table.bstab / .hbars 在报告里各自唯一，
  // 故可用类选择器直接命中（新增同类图时才需要改成 id）。
  const FIGS = {
    pubtrend:{kind:'svg',   sel:'.pline'},
    timeline:{kind:'svg',   sel:'.tlsvg'},
    heatmap: {kind:'table', sel:'table.hmtable'},
    burst:   {kind:'spark', sel:'table.bstab'},
    age:     {kind:'bars',  sel:'.hbars'}
  };
  // 画布网络：转发给各画布自己注册的导出口（__NET_EXPORTS）
  const CANVAS_FIGS = ['kwnet','authnet','instnet','citnet'];

  function save(slug, mode, name){
    if(CANVAS_FIGS.indexOf(slug) >= 0){
      const ex = (window.__NET_EXPORTS || {})[slug] || {};
      const fn = (mode === 'svg') ? ex.svg : ex.png;
      if(typeof fn === 'function'){ fn(); return; }
      if(window.console) console.warn('[figsave] 该网络图未注册导出：'+slug);
      // 未注册导出属于同步失败：必须解掉按钮忙碌态并给出可见原因，
      // 否则按钮会永远停在「生成中…」（不允许任何静默失败）。
      if(window.__figAbort) window.__figAbort('该图未注册保存通道：' + slug);
      return;
    }
    const cfg = FIGS[slug];
    if(!cfg) throw new Error('未登记图类型: '+slug);
    const el = q(cfg.sel);
    if(!el) throw new Error('图上元素缺失: '+cfg.sel);
    if(cfg.kind === 'svg'){
      if(mode === 'svg') window.__dlSVGx(el, name+'.svg');
      else window.__dlSVGpng(el, 2, name+'.png');
      return;
    }
    const cv = DRAWERS[cfg.kind](el);
    if(!cv) throw new Error('重绘失败（图上无可绘制内容）');
    window.__dlPNG(cv, 1, name+'.png');   // 重绘已是 2x 像素，scale=1 不再放大
  }
  window.__figSave = save;

  const btns = document.querySelectorAll('.figbar .fbtn');
  Array.prototype.forEach.call(btns, function(b){
    b.onclick = function(){
      const slug = b.getAttribute('data-fig'), mode = b.getAttribute('data-save') || 'png';
      const name = b.getAttribute('data-name') || slug;
      try{ save(slug, mode, name); }
      catch(e){
        if(window.console) console.warn('[figsave]', e);
        // 同步异常路径也要有可见反馈，并解掉忙碌态
        if(window.__figAbort) window.__figAbort('保存失败：' + (e && e.message ? e.message : e));
      }
      if(b.blur) b.blur();
    };
  });
})();
"""

# ── 作者共现网络画布（独立于关键词画布）──────────────────────────────
# [!]  为什么不塞进关键词画布的 viewMode：
#   两套图的**语义完全不同** —— 关键词网络的节点是「概念」、边是「同篇共现」，
#   且带主题归属（pc/ci/桥接）；作者网络的节点是「作者」、边是「同篇合作」，
#   没有主题维度。硬塞进同一个 viewMode 会让 contextmenu/图例/侧栏的语义
#   互相污染，也极易踩坏既有交互。故独立成章、独立 canvas、独立 IIFE。
#   但**视觉令牌必须同源**：配色取 window.__PAL__、皮肤取 window.__CANVAS_SKIN__.light，
#   导出复用 window.__dlPNG/__dlSVG —— 保证两张图看起来是同一份报告的一部分。
AUTH_JS = r"""
(function(){
const A = window.__AUTHNET__;
const cv = document.getElementById('authnet');
if(!A || !A.nodes || !A.nodes.length || !cv) return;
const ctx = cv.getContext('2d', {alpha:false});
const N = A.nodes;
// 边字段兼容 source/target/weight 与瘦身后的 s/t/w 两种写法（报告端用后者省字节）
const E = (A.edges||[]).map(function(e){
  return {s:(e.s!=null?e.s:e.source), t:(e.t!=null?e.t:e.target),
          w:(e.w!=null?e.w:e.weight)}; });

/* ---------- 视觉令牌：全部复用关键词画布的来源 ---------- */
const PAL = window.__PAL__ || ['#0891B2','#EA580C','#4F46E5','#B45309','#2563EB',
  '#E11D48','#0E7490','#DB2777','#0D9488','#D6336C','#7C3AED','#16A34A','#64748B','#65A30D'];
const sk = (window.__CANVAS_SKIN__ && window.__CANVAS_SKIN__.light) || {
  bg:'#FFFFFF', label:'rgba(26,29,33,.92)', halo:'rgba(255,255,255,.92)',
  cross:'rgba(120,120,114,0.34)', note:'#5A6169',
  nodeEdge:'rgba(15,23,42,.40)', selStroke:'#111111', selInner:'#FFFFFF'};
/* ---------- 合作群（连通分量）着色 ----------
   同一合作群（作者及其合作者）= 同一种颜色，按网络连通分量划分 —— 这正是用户
   要的「一个作者及合作者应该是一个颜色」（统一常量会给全图同色）。
   数据侧已在每个节点写入 component（按规模降序编号，最大群 id=0），故直接对
   PAL 取模即可让大群优先拿到最区分度最高的颜色；合作群多于色数时颜色循环复用。
   旧产物若无 component 字段 → 用并查集自算兜底（编号规则与数据侧逐条一致：按
   分量规模降序、规模相同按最小成员名升序），绝不因此退回单色。
   [!] 颜色池复用 window.__PAL__（与关键词画布逐位一致），不引入体系外新颜色。 */
const compId = (function(){
  if(!N.some(function(d){ return d.component==null; })){
    const m={}; N.forEach(function(d){ m[d.id]=d.component|0; }); return m;
  }
  const p={}; N.forEach(function(d){ p[d.id]=d.id; });
  function find(x){ while(p[x]!==x){ p[x]=p[p[x]]; x=p[x]; } return x; }
  E.forEach(function(e){
    if(e.s!=null && e.t!=null && p[e.s]!=null && p[e.t]!=null){
      const ra=find(e.s), rb=find(e.t); if(ra!==rb) p[ra]=rb;
    }
  });
  const grp=new Map();
  N.forEach(function(d){ const r=find(d.id); if(!grp.has(r)) grp.set(r,[]); grp.get(r).push(d.id); });
  const groups=[]; grp.forEach(function(a){ groups.push(a.slice().sort()); });
  groups.sort(function(a,b){ return (b.length-a.length) || (a[0]<b[0]?-1:(a[0]>b[0]?1:0)); });
  const m={}; groups.forEach(function(g,i){ g.forEach(function(id){ m[id]=i; }); });
  return m;
})();
function colorOf(d){
  const c=compId[d.id];
  const i=(((c==null?0:c) % PAL.length) + PAL.length) % PAL.length;
  return PAL[i];
}

/* ---------- 坐标解码（与关键词画布同一套 pos_encoded 契约）---------- */
const byId = {}; N.forEach(function(d){ byId[d.id]=d; });
let hasXY = false;
if(A.pos_encoded && A.pos_encoded.pos_b64){
  try{
    const bin = atob(A.pos_encoded.pos_b64);
    const buf = new ArrayBuffer(bin.length);
    const u8 = new Uint8Array(buf);
    for(let i=0;i<bin.length;i++) u8[i]=bin.charCodeAt(i);
    const q = new Int16Array(buf), sc = A.pos_encoded.scale||1;
    if(q.length >= 2*N.length){
      N.forEach(function(d,i){ d.px=q[2*i]/sc; d.py=q[2*i+1]/sc; });
      hasXY = N.every(function(d){return Number.isFinite(d.px)&&Number.isFinite(d.py);});
    }
  }catch(e){ hasXY = false; }
}
// 明文 x/y 兜底：必须显式拷进 px/py（渲染只认 px/py）
if(!hasXY && Number.isFinite(N[0].x) && Number.isFinite(N[0].y)){
  N.forEach(function(d){ d.px=+d.x; d.py=+d.y; });
  hasXY = N.every(function(d){return Number.isFinite(d.px)&&Number.isFinite(d.py);});
}
// 最后防线：非有限坐标 → 确定性网格，绝不静默画空白
(function(){
  const bad = function(d){ return !Number.isFinite(d.px) || !Number.isFinite(d.py); };
  if(N.length && !N.some(bad)) return;
  const cols = Math.max(1, Math.ceil(Math.sqrt(N.length)));
  N.forEach(function(d,i){ d.px = 120+(i%cols)*60; d.py = 120+Math.floor(i/cols)*60; });
  if(window.console) console.warn('[authnet] 坐标含非有限值，已退化为网格布局');
})();

/* ---------- 视图变换 ---------- */
let vx=0, vy=0, vk=1, vInit=false, vkFit=1;
const maxDf = N.length ? Math.max.apply(null, N.map(function(d){return d.df||1;})) : 1;
// 半径 ∝ √df，钳制 [4,22]：下限保证每个作者都看得见、点得到；上限避免 hub 遮住邻点
function radiusOf(d){ return Math.max(4, Math.min(22, 4 + Math.sqrt(d.df||1)/Math.sqrt(maxDf)*14)); }
const sx = function(d){ return (d.px + (d.ox||0))*vk + vx; };
const sy = function(d){ return (d.py + (d.oy||0))*vk + vy; };
function bounds(){
  let x0=1e18,y0=1e18,x1=-1e18,y1=-1e18;
  N.forEach(function(d){ const X=d.px+(d.ox||0), Y=d.py+(d.oy||0);
    if(!Number.isFinite(X)||!Number.isFinite(Y)) return;
    if(X<x0)x0=X; if(X>x1)x1=X; if(Y<y0)y0=Y; if(Y>y1)y1=Y; });
  if(x0>x1) return {x0:-1,y0:-1,x1:1,y1:1};
  return {x0:x0,y0:y0,x1:x1,y1:y1};
}
function fitView(){
  const b=bounds(), w=cv.clientWidth, h=cv.clientHeight;
  const bw=Math.max(1,b.x1-b.x0), bh=Math.max(1,b.y1-b.y0);
  const t=28, bt=28, availH=Math.max(40, h-t-bt);
  vk=Math.min(w/(bw*1.06), availH/(bh*1.06));
  vx=w/2-(b.x0+b.x1)/2*vk;
  vy=t+availH/2-(b.y0+b.y1)/2*vk;
  vInit=true; vkFit=vk;
}

/* ---------- 标签预算（参考关键词画布 labelBudget 思路）----------
   作者多达几十上百，全画必糊。首屏画 df 最高的一批，放大后逐步显示更多。
   首屏标签预算从 18 提高到 40，保证姓名可读性；
   放大后上限也由 64 提到 140，基本能覆盖主要合作群的姓名。 */
const byDf = N.map(function(d,i){return i;}).sort(function(a,b){return (N[b].df||0)-(N[a].df||0);});
function labelBudget(){
  if(vkFit<=0) return 40;
  const r = vk/vkFit;
  return Math.round(40 + 100*Math.min(1, Math.max(0, (r-1)/2.0)));
}

/* ---------- 交互状态 ---------- */
let sel=null, hov=null, dragging=null, panning=false;
let lastX=0, lastY=0, downX=0, downY=0, movedFar=false;
let nbrs = new Set();
let drawnNodes=0, drawnEdges=0, lastLabels=0;
const dirty={v:false};
function neighbors(id){ const s=new Set(); for(const e of E){ if(e.s===id)s.add(e.t); else if(e.t===id)s.add(e.s); } return s; }
function invalidate(){ dirty.v=true; schedule(); }

/* ---------- 绘制 ---------- */
function draw(){
  const w=Math.round(cv.clientWidth), h=Math.round(cv.clientHeight);
  // 尺寸未就绪直接放弃本帧、保持 vInit=false（由 ResizeObserver 补画）——
  // 否则 fitView 会把 vk 算成 0、坐标全 NaN 且永久不再重算（关键词画布的教训）
  if(w<2||h<2) return;
  const dpr=window.devicePixelRatio||1;
  if(cv.width!==Math.round(w*dpr)||cv.height!==Math.round(h*dpr)){
    cv.width=Math.round(w*dpr); cv.height=Math.round(h*dpr);
  }
  if(!vInit) fitView();
  ctx.setTransform(dpr,0,0,dpr,0,0);
  ctx.fillStyle=sk.bg; ctx.fillRect(0,0,w,h);
  drawnNodes=0; drawnEdges=0; lastLabels=0;

  // 边：线宽随共现次数（合作越多越粗），选中时只留关联边
  // v1.0.0：连接线随合作群上色（两端同群=群色；跨群=浅灰）。
  // 实测结论：最大合作群 193 人（87% 节点）的同群边全用 PAL[0] 品牌青，
  // 整张图被绿色淹没，无法分辨个体连接。修复：
  //   · 同群边**降低饱和度+提高透明度**（混 50% 灰），保留群归属暗示但不主导；
  //   · 边透明度从 0.62 降到 0.34，叠加后不再糊成色块；
  //   · 节点本身仍用饱和群色（不受影响），视觉重心回到节点。
  function _desat(col){
    // 把 hex 颜色与灰色 50:50 混合，降低饱和度
    const m=/^#?([0-9a-f]{6})$/i.exec(col||''); if(!m) return col;
    const v=parseInt(m[1],16);
    const r=(v>>16)&255, g=(v>>8)&255, b=v&255;
    const grey=Math.round(0.299*r+0.587*g+0.114*b);
    const mix=function(c){ return Math.round(0.5*c + 0.5*grey); };
    return '#'+((1<<24)+(mix(r)<<16)+(mix(g)<<8)+mix(b)).toString(16).slice(1);
  }
  ctx.globalAlpha = 0.34;
  for(const e of E){
    const a=byId[e.s], b=byId[e.t];
    if(!a||!b) continue;
    if(sel!==null && e.s!==sel && e.t!==sel) continue;
    const X1=sx(a), Y1=sy(a), X2=sx(b), Y2=sy(b);
    ctx.beginPath(); ctx.moveTo(X1,Y1); ctx.lineTo(X2,Y2);
    const sameGrp = colorOf(a)===colorOf(b);
    ctx.strokeStyle = (sel!==null) ? 'rgba(15,123,138,.55)'
                    : (sameGrp ? _desat(colorOf(a)) : sk.cross);
    ctx.lineWidth = Math.min(3.2, 0.7 + (e.w||1)*0.55);
    ctx.stroke(); drawnEdges++;
  }
  ctx.globalAlpha = 1;

  // 节点
  for(const d of N){
    const X=sx(d), Y=sy(d), r=radiusOf(d);
    if(X<-30||X>w+30||Y<-30||Y>h+30) continue;
    const isSel=(sel===d.id), isNbr=nbrs.has(d.id);
    const dim = (sel!==null) && !isSel && !isNbr;
    ctx.globalAlpha = dim ? 0.25 : 1;
    ctx.beginPath(); ctx.arc(X,Y,r,0,Math.PI*2);
    ctx.fillStyle = colorOf(d); ctx.fill();
    ctx.lineWidth = isSel ? 2.6 : 1;
    ctx.strokeStyle = isSel ? sk.selStroke : ((hov===d.id) ? sk.selStroke : sk.nodeEdge);
    ctx.stroke();
    ctx.globalAlpha = 1;
    drawnNodes++;
  }

  // 标签：只给「当前视口内 df 最高」的 budget 个节点画，缩放时逐步显示更多
  // v1.0.0 修：按 df 全局排序时，小分量的
  // 作者 df 天然低、标签全被大群挤掉——紫/橙/蓝小群整群无名。
  // 改为「分量保底」：每个连通分量先保底 2 个标签（该群 df 最高者），
  // 剩余预算再按全局 df 分配。分量归属用 compId（并查集结果）。
  const budget = labelBudget();
  const _compOf = compId;   // id -> 分量序号
  const _compBest = new Map(); // 分量 -> [作者id 按 df 降序]
  for(const i of byDf){
    const d=N[i];
    const c=_compOf[d.id]||0;
    if(!_compBest.has(c)) _compBest.set(c,[]);
    if(_compBest.get(c).length<2) _compBest.get(c).push(i);
  }
  const _picked=new Set();
  for(const arr of _compBest.values()) arr.forEach(function(i){_picked.add(i);});
  const cands=[]; let count=0;
  // 第一轮：分量保底标签（不受预算上限约束的小额保底，最多分量数×2）
  for(const i of byDf){
    if(!_picked.has(i)) continue;
    const d=N[i]; const X=sx(d), Y=sy(d);
    if(X<0||X>w||Y<0||Y>h) continue;
    cands.push([d,X,Y]); count++;
  }
  // 第二轮：剩余预算按全局 df
  for(const i of byDf){
    if(count>=budget) break;
    if(_picked.has(i)) continue;
    const d=N[i]; const X=sx(d), Y=sy(d);
    if(X<0||X>w||Y<0||Y>h) continue;
    cands.push([d,X,Y]); count++;
  }
  ctx.font='600 11px -apple-system,"PingFang SC",sans-serif';
  ctx.textAlign='center'; ctx.textBaseline='bottom';
  // v1.0.0：标签数提到 40 后需去重叠 —— 已占矩形（文字宽×高）相交就跳过，
  // 保证显示出来的姓名都读得清，而不是糊成一团。
  const placed=[];
  const LW=7.2, LH=14;   // 每字约 7.2px 宽、行高 14
  for(const c of cands){
    const d=c[0], X=c[1], Y=c[2], r=radiusOf(d);
    const tw=(d.id||'').length*LW, ty=Y-r-3;
    const box=[X-tw/2, ty-LH, X+tw/2, ty];
    let hit=false;
    for(const p of placed){
      if(!(box[2]<p[0]||box[0]>p[2]||box[3]<p[1]||box[1]>p[3])){ hit=true; break; }
    }
    if(hit) continue;
    placed.push(box);
    // 白色描边光晕 + 深色文字：任何底色上都读得清（浅色底尤其）
    ctx.lineWidth=3; ctx.strokeStyle=sk.halo;
    ctx.strokeText(d.id, X, ty);
    ctx.fillStyle=sk.label;
    ctx.fillText(d.id, X, ty);
    lastLabels++;
  }
}

/* ---------- 调度（脏才重绘，静止零开销）---------- */
let raf=null;
function schedule(){ if(raf) return; raf=requestAnimationFrame(function(){ raf=null; if(dirty.v){ dirty.v=false; draw(); } }); }

/* ---------- 悬停信息条 ---------- */
function renderInfo(id){
  const el=document.getElementById('authInfo');
  if(!el) return;
  if(!id){ el.textContent='把鼠标移到节点上查看作者与其出现篇数、合作者数；点击节点高亮其合作者；拖动节点可微调位置。'; return; }
  const d=byId[id];
  if(!d){ el.textContent=''; return; }
  el.textContent = d.id + '｜出现 ' + (d.df||0) + ' 篇｜合作者 ' + (d.degree||0) + ' 人'
    + (d.isolated ? '｜孤立作者（无同库合作者）' : '');
}

/* ---------- 命中测试（屏幕坐标 → 最近节点）---------- */
function hitTest(mx,my){
  let best=null, bestD=1e18;
  for(const d of N){
    const X=sx(d), Y=sy(d), r=radiusOf(d);
    const dx=mx-X, dy=my-Y, dd=dx*dx+dy*dy;
    const rr=(r+5)*(r+5);
    if(dd<=rr && dd<bestD){ bestD=dd; best=d; }
  }
  return best;
}

/* ---------- 指针交互：拖节点 / 拖空白平移 / 点击高亮 ---------- */
cv.addEventListener('pointerdown', function(ev){
  const rc=cv.getBoundingClientRect();
  const mx=ev.clientX-rc.left, my=ev.clientY-rc.top;
  const d=hitTest(mx,my);
  downX=mx; downY=my; movedFar=false;
  if(d){ dragging=d; cv.setPointerCapture && cv.setPointerCapture(ev.pointerId); }
  else { panning=true; }
  lastX=mx; lastY=my;
});
cv.addEventListener('pointermove', function(ev){
  const rc=cv.getBoundingClientRect();
  const mx=ev.clientX-rc.left, my=ev.clientY-rc.top;
  if(dragging){
    const dx=mx-lastX, dy=my-lastY;
    if(Math.abs(mx-downX)+Math.abs(my-downY)>3) movedFar=true;
    // 拖拽改**用户偏移 ox/oy**，不碰算法坐标 px/py —— 这样"复位"能一键还原
    dragging.ox=(dragging.ox||0)+dx/vk; dragging.oy=(dragging.oy||0)+dy/vk;
    lastX=mx; lastY=my; invalidate(); return;
  }
  if(panning){ vx+=mx-lastX; vy+=my-lastY; lastX=mx; lastY=my; invalidate(); return; }
  // 悬停
  const d=hitTest(mx,my);
  const nid = d ? d.id : null;
  if(nid!==hov){ hov=nid; renderInfo(nid); invalidate(); }
  cv.style.cursor = d ? 'pointer' : 'grab';
});
function endPointer(ev){
  if(dragging){
    if(!movedFar){   // 位移小于阈值 → 判为点击，高亮邻居
      sel = (sel===dragging.id) ? null : dragging.id;
      nbrs = sel ? neighbors(sel) : new Set();
      renderInfo(sel);
      invalidate();
    }
  }
  dragging=null; panning=false;
}
cv.addEventListener('pointerup', endPointer);
cv.addEventListener('pointercancel', endPointer);
cv.addEventListener('pointerleave', function(){ if(!dragging && !panning){ hov=null; renderInfo(null); invalidate(); } });
cv.addEventListener('dblclick', function(){ vInit=false; invalidate(); });
cv.addEventListener('wheel', function(ev){
  // 仅 Ctrl/⌘+滚轮缩放，普通滚轮留给页面滚动（与关键词画布一致）；
  // 拖动节点时框选/缩放的锚点取指针位置，符合直觉
  if(!(ev.ctrlKey||ev.metaKey)) return;
  ev.preventDefault();
  const rc=cv.getBoundingClientRect();
  const mx=ev.clientX-rc.left, my=ev.clientY-rc.top;
  const nk=Math.max(0.15, Math.min(9, vk*(ev.deltaY<0?1.15:1/1.15)));
  vx=mx-(mx-vx)*(nk/vk); vy=my-(my-vy)*(nk/vk); vk=nk;
  invalidate();
}, {passive:false});

/* ---------- 导出：复用通用下载收尾 __dlPNG / __dlSVG ---------- */
function exportSVG(){
  const w=cv.clientWidth, h=cv.clientHeight, ns='http://www.w3.org/2000/svg';
  const svg=document.createElementNS(ns,'svg');
  svg.setAttribute('xmlns',ns);
  svg.setAttribute('width',w); svg.setAttribute('height',h);
  svg.setAttribute('viewBox','0 0 '+w+' '+h);
  const bg=document.createElementNS(ns,'rect');
  bg.setAttribute('width',w); bg.setAttribute('height',h); bg.setAttribute('fill','#ffffff');
  svg.appendChild(bg);
  const ge=document.createElementNS(ns,'g');
  for(const e of E){
    const a=byId[e.s], b=byId[e.t];
    if(!a||!b) continue;
    const ln=document.createElementNS(ns,'line');
    ln.setAttribute('x1',sx(a).toFixed(1)); ln.setAttribute('y1',sy(a).toFixed(1));
    ln.setAttribute('x2',sx(b).toFixed(1)); ln.setAttribute('y2',sy(b).toFixed(1));
    ln.setAttribute('stroke','#999'); ln.setAttribute('stroke-opacity','0.4');
    ln.setAttribute('stroke-width', Math.min(3, 0.7+(e.w||1)*0.5).toFixed(1));
    ge.appendChild(ln);
  }
  svg.appendChild(ge);
  const gn=document.createElementNS(ns,'g');
  for(const d of N){
    const X=sx(d), Y=sy(d), r=radiusOf(d);
    if(X<-20||X>w+20||Y<-20||Y>h+20) continue;
    const c=document.createElementNS(ns,'circle');
    c.setAttribute('cx',X.toFixed(1)); c.setAttribute('cy',Y.toFixed(1));
    c.setAttribute('r',r.toFixed(1)); c.setAttribute('fill',colorOf(d));
    c.setAttribute('stroke','rgba(20,20,20,0.35)'); c.setAttribute('stroke-width','0.7');
    gn.appendChild(c);
  }
  svg.appendChild(gn);
  const gt=document.createElementNS(ns,'g');
  gt.setAttribute('font-family','-apple-system,"PingFang SC",sans-serif');
  gt.setAttribute('font-size','11'); gt.setAttribute('text-anchor','middle');
  const budget=labelBudget(); let cnt=0;
  for(const i of byDf){
    if(cnt>=budget) break;
    const d=N[i]; const X=sx(d), Y=sy(d);
    if(X<0||X>w||Y<0||Y>h) continue;
    const t=document.createElementNS(ns,'text');
    t.setAttribute('x',X.toFixed(1)); t.setAttribute('y',(Y-radiusOf(d)-3).toFixed(1));
    t.setAttribute('fill','#2c2c2a'); t.textContent=d.id;
    gt.appendChild(t); cnt++;
  }
  svg.appendChild(gt);
  window.__dlSVG(svg,'author-network.svg');
}
const bp=document.getElementById('authExportPNG');
if(bp){ bp.onclick=function(){ draw(); window.__dlPNG(cv,2,'author-network.png'); }; }
const bs=document.getElementById('authExportSVG');
if(bs){ bs.onclick=function(){ draw(); exportSVG(); }; }
/* 供"图表保存"统一分发器转发（与关键词画布同一 __NET_EXPORTS 契约） */
window.__NET_EXPORTS = window.__NET_EXPORTS || {};
window.__NET_EXPORTS.authnet = { png:function(){ draw(); window.__dlPNG(cv,2,'author-network.png'); },
                                 svg:function(){ draw(); exportSVG(); } };

/* ---------- 尺寸变化补画 ---------- */
window.addEventListener('resize', function(){ vInit=false; invalidate(); });
if(window.ResizeObserver){
  let lw=-1, lh=-1;
  new ResizeObserver(function(){
    const w=cv.clientWidth, h=cv.clientHeight;
    if(w===lw && h===lh) return;
    lw=w; lh=h;
    if(w<2||h<2) return;
    vInit=false; invalidate();
  }).observe(cv);
}

renderInfo(null);
// 测试钩子：供 Node 侧探针断言「确实画了节点与边、坐标有限」（不是空白）
window.__AUTHNET_TEST__ = {
  pump: function(){ draw(); },
  counts: function(){ return {nodes:N.length, edges:E.length,
    drawnNodes:drawnNodes, drawnEdges:drawnEdges, labels:lastLabels, zoom:vk}; },
  layoutSanity: function(){
    let bad=0, minX=Infinity, maxX=-Infinity, minY=Infinity, maxY=-Infinity;
    for(const d of N){
      if(!Number.isFinite(d.px)||!Number.isFinite(d.py)){ bad++; continue; }
      if(d.px<minX)minX=d.px; if(d.px>maxX)maxX=d.px;
      if(d.py<minY)minY=d.py; if(d.py>maxY)maxY=d.py;
    }
    return {total:N.length, badXY:bad, spanX:maxX-minX, spanY:maxY-minY,
            drawnNodes:drawnNodes, posDecoded:hasXY};
  },
  nodeScreenXY: function(id){ const d=byId[id]; return d?[sx(d),sy(d)]:null; },
  select: function(id){ sel=id; nbrs=id?neighbors(id):new Set(); invalidate(); },
  hasCanvas: function(){ return !!cv; }
};
dirty.v=true; schedule();      // 首帧
})();
"""

# 侧栏导航联动：滚动时高亮当前章节。
# 分栏之后左导航常驻，若与正文不联动，读者会失去「我在哪一段」的定位，
# 反而比单栏更难用 —— 这是分栏必须配的能力，不是装饰。
# ── 通用共现网络画布工厂（机构共现 / 引文共被引·耦合）────────────────────
# 为什么是"工厂"而不是再抄一份作者画布：机构与引文两张图在报告侧完全同构
# （节点=实体、边=共现次数），差异只有数据与标题。作者画布早于本工厂存在，
# 其交互已被 _probe_authnet.js 锁定，重构它是无收益的风险 → **不动作者画布**，
# 新增两张图统一走这里。视觉令牌（__PAL__ / __CANVAS_SKIN__）与下载
# （__dlPNG / __dlSVG）与其它画布同源，保证"看起来是同一份报告的一部分"。
# 坐标契约同关键词/作者画布：pos_encoded(pos_b64, int16) → 明文 x/y →
# 确定性网格兜底；绝不静默画空白（关键词画布在这上面栽过，见文件顶部教训）。
NETVIEW_JS = r"""
(function(){
  if(typeof window.__makeNetView === 'function') return;
  window.__makeNetView = function(cfg){
    const cv = document.getElementById(cfg.canvasId);
    const A = cfg.data;
    if(!A || !A.nodes || !A.nodes.length || !cv) return null;
    const slug = cfg.slug;
    // 下载文件名用图表名（cfg.name），不是内部 slug —— 否则用户拿到 instnet.png
    // 这种无法辨识的名字，多张图也容易互相覆盖。
    const fname = cfg.name || slug;
    const ctx = cv.getContext('2d', {alpha:false});
    const N = A.nodes;
    const E = (A.edges||[]).map(function(e){
      return {s:(e.s!=null?e.s:e.source), t:(e.t!=null?e.t:e.target),
              w:(e.w!=null?e.w:e.weight)}; });
    // 默认色池与作者画布的 PAL 逐位一致（14 色）：报告里 window.__PAL__ 会覆盖它，
    // 这里保持同源，避免"色数不足导致分量颜色过早循环"。
    const PAL = window.__PAL__ || ['#0891B2','#EA580C','#4F46E5','#B45309','#2563EB',
      '#E11D48','#0E7490','#DB2777','#0D9488','#D6336C','#7C3AED','#16A34A','#64748B','#65A30D'];
    const sk = (window.__CANVAS_SKIN__ && window.__CANVAS_SKIN__.light) || {
      bg:'#FFFFFF', label:'rgba(26,29,33,.92)', halo:'rgba(255,255,255,.92)',
      cross:'rgba(120,120,114,0.34)', note:'#5A6169',
      nodeEdge:'rgba(15,23,42,.40)', selStroke:'#111111', selInner:'#FFFFFF'};
    // [!] 主题色（机构=靛 / 引文=玫红）由生成端经 cfg.color 注入，
    //   它现在**只服务卡片层**（--net-c 标题竖条 / KPI / 图例主色点），**不再给节点上色**
    //   —— 节点若用它就会"全图一个色，看不出共现群"。JS 侧留 CASE_COL 供"选中节点"高亮。
    const CASE_COL = cfg.color || PAL[2] || PAL[0];
    // ── 节点按「共现社群」着色（着色维度）──
    //   取色优先级：community（社群发现）> component（连通分量）> 并查集兜底。
    //   为什么优先 community：引文网络常是"几乎全连通"的图 —— WoS 共被引最大
    //   连通分量占 92.1%，若按 component 上色，一张图基本只剩一个颜色，
    //   "引文网络看上去还是一个色"。社群发现把大分量拆成若干内部更紧密的群体
    //   （实测 6 个分量/最大 92.1% → 18 个社群/最大 21.2%），颜色才真正分得开。
    //   规则：PAL[群 id % PAL.length]，群 id 已按规模降序编号（最大群=0），故大群
    //   优先拿到区分度最高的颜色；群多于色数时循环复用。卡片主色 = 这是哪张网络。
    //   [!] 旧产物若无 community 也无 component → 在 JS 里用并查集自算兜底，编号
    //   规则逐条一致（规模降序、同规模按最小成员名升序），**绝不因此回落成单色**。
    const groupId = (function(){
      if(N.length && !N.some(function(d){ return d.community==null; })){
        const m={}; N.forEach(function(d){ m[d.id]=d.community|0; }); return m;
      }
      if(N.length && !N.some(function(d){ return d.component==null; })){
        const m={}; N.forEach(function(d){ m[d.id]=d.component|0; }); return m;
      }
      const p={}; N.forEach(function(d){ p[d.id]=d.id; });
      function find(x){ while(p[x]!==x){ p[x]=p[p[x]]; x=p[x]; } return x; }
      E.forEach(function(e){
        if(e.s!=null && e.t!=null && p[e.s]!=null && p[e.t]!=null){
          const ra=find(e.s), rb=find(e.t); if(ra!==rb) p[ra]=rb;
        }
      });
      const grp=new Map();
      N.forEach(function(d){ const r=find(d.id); if(!grp.has(r)) grp.set(r,[]); grp.get(r).push(d.id); });
      const groups=[]; grp.forEach(function(a){ groups.push(a.slice().sort()); });
      groups.sort(function(a,b){ return (b.length-a.length) || (a[0]<b[0]?-1:(a[0]>b[0]?1:0)); });
      const m={}; groups.forEach(function(g,i){ g.forEach(function(id){ m[id]=i; }); });
      return m;
    })();
    function colorOf(d){
      const c=groupId[d.id];
      const i=(((c==null?0:c) % PAL.length) + PAL.length) % PAL.length;
      return PAL[i];
    }

    const byId = {};
    N.forEach(function(d){ byId[d.id]=d; });
    // ── 坐标解码（与关键词/作者画布同一 pos_encoded 契约）──
    let hasXY = false;
    if(A.pos_encoded && A.pos_encoded.pos_b64){
      try{
        const bin = atob(A.pos_encoded.pos_b64);
        const buf = new ArrayBuffer(bin.length), u8 = new Uint8Array(buf);
        for(let i=0;i<bin.length;i++) u8[i]=bin.charCodeAt(i);
        const qq = new Int16Array(buf), sc = A.pos_encoded.scale||1;
        if(qq.length >= 2*N.length){
          N.forEach(function(d,i){ d.px=qq[2*i]/sc; d.py=qq[2*i+1]/sc; });
          hasXY = N.every(function(d){return Number.isFinite(d.px)&&Number.isFinite(d.py);});
        }
      }catch(e){ hasXY=false; }
    }
    if(!hasXY && Number.isFinite(N[0].x) && Number.isFinite(N[0].y)){
      N.forEach(function(d){ d.px=+d.x; d.py=+d.y; });
      hasXY = N.every(function(d){return Number.isFinite(d.px)&&Number.isFinite(d.py);});
    }
    (function(){   // 最后防线：非有限坐标 → 确定性**环形**布局，绝不静默画空白
      // [!] 兜底布局不得用规则网格——视觉上所有节点排在一起、
      //   直接来源（网格看起来像表格不像网络）。改成单圈均匀铺开 —— 虽非力导向，
      //   但一眼是"连成环的网络"，且确定性（同输入同输出）、绝不空白、console 有警告。
      const bad = function(d){ return !Number.isFinite(d.px) || !Number.isFinite(d.py); };
      if(N.length && !N.some(bad)) return;
      const n = N.length, R = Math.max(80, n * 6), step = 2*Math.PI/Math.max(1,n);
      N.forEach(function(d,i){ d.px = Math.cos(i*step)*R; d.py = Math.sin(i*step)*R; });
      if(window.console) console.warn('['+slug+']坐标含非有限值，已退化为环形布局');
    })();

    let vx=0, vy=0, vk=1, vInit=false, vkFit=1;
    const maxDf = N.length ? Math.max.apply(null, N.map(function(d){return d.df||1;})) : 1;
    // 半径是**屏幕空间恒定像素**（∝√df，钳制 [4,22]），**不乘 vk** —— 与作者画布
    // （radiusOf 同公式、同用法）逐字一致。这是"点大小稳定、不随缩放忽大忽小"的关键。
    function radiusOf(d){ return Math.max(4, Math.min(22, 4 + Math.sqrt(d.df||1)/Math.sqrt(maxDf)*14)); }
    const sx = function(d){ return (d.px + (d.ox||0))*vk + vx; };
    const sy = function(d){ return (d.py + (d.oy||0))*vk + vy; };
    function bounds(){
      let x0=1e18,y0=1e18,x1=-1e18,y1=-1e18;
      N.forEach(function(d){ const X=d.px+(d.ox||0), Y=d.py+(d.oy||0);
        if(!Number.isFinite(X)||!Number.isFinite(Y)) return;
        if(X<x0)x0=X; if(X>x1)x1=X; if(Y<y0)y0=Y; if(Y>y1)y1=Y; });
      if(x0>x1) return {x0:-1,y0:-1,x1:1,y1:1};
      return {x0:x0,y0:y0,x1:x1,y1:y1};
    }
    function fitView(){
      const b=bounds(), w=(cv.clientWidth||900), h=(cv.clientHeight||620);
      const bw=Math.max(1,b.x1-b.x0), bh=Math.max(1,b.y1-b.y0);
      // [!] 去掉 `Math.min(4, ...)` 上限钳制。本画布的坐标是**归一化坐标**
      //   （span≈1.5，与关键词/作者画布同一 pos_encoded 契约），把它撑满画布需要
      //   vk≈数百；旧代码把 vk 硬钳在 4 → 圆心全挤在画布正中一小团，正是用户
      //   "所有节点排在一起"的直接元凶之一（另一处是兜底网格布局）。
      //   pad 预留 34px 给固定像素半径的节点，避免边缘大节点的圆/描边被裁掉。
      //   缩放上下限由 vkFit 相对控制（见 wheel），故此处绝对值不再需要钳制。
      const pad=34;
      vk=Math.max(0.1, Math.min((w-2*pad)/bw, (h-2*pad)/bh));
      vkFit=vk;
      vx=w/2-(b.x0+b.x1)/2*vk; vy=h/2-(b.y0+b.y1)/2*vk;
    }
    const byDeg = N.map(function(_,i){ return i; })
      .sort(function(a,b){ return (N[b].degree||N[b].df||0)-(N[a].degree||N[a].df||0); });
    function labelBudget(){ return Math.max(6, Math.min(28, Math.round((cv.clientWidth||900)/38))); }

    let hov=null, sel=null, nbrs=new Set();
    const lastCounts = {nodes:N.length, drawnNodes:0, drawnEdges:0, labels:0};

    function draw(){
      const w=cv.clientWidth||900, h=cv.clientHeight||620;
      const dpr=Math.max(1, Math.min(2, window.devicePixelRatio||1));
      if(cv.width !== Math.round(w*dpr)){ cv.width=Math.round(w*dpr); cv.height=Math.round(h*dpr); }
      if(!vInit){ fitView(); vInit=true; }
      ctx.setTransform(dpr,0,0,dpr,0,0);
      ctx.fillStyle=sk.bg; ctx.fillRect(0,0,w,h);
      const maxW = Math.max(1, E.reduce(function(m,e){ return Math.max(m, e.w||1); }, 1));
      ctx.lineCap='round';
      let de=0;
      // v1.0.0：边随社群上色（两端同群=群色半透明；跨群=浅灰）——修复「连线无色」
      ctx.globalAlpha = 1;
      for(const e of E){
        const a=byId[e.s], b=byId[e.t];
        if(!a||!b) continue;
        const sameGrp = colorOf(a)===colorOf(b);
        if(sel!=null){
          ctx.strokeStyle = (e.s===sel||e.t===sel) ? colorOf(a) : 'rgba(100,116,139,0.12)';
        }else{
          ctx.globalAlpha = sameGrp ? 0.55 : 0.9;
          ctx.strokeStyle = sameGrp ? colorOf(a) : 'rgba(100,116,139,0.28)';
        }
        // 线宽是屏幕空间恒定值（随共现次数变粗），**不乘 vk** —— 与作者画布一致；
        // 旧代码 `* vk` 在 vk≈数百时会画出几十像素宽的巨线，糊满整张图。
        ctx.lineWidth = 0.6 + (e.w||1)/maxW*3.4;
        ctx.beginPath(); ctx.moveTo(sx(a),sy(a)); ctx.lineTo(sx(b),sy(b)); ctx.stroke();
        de++;
      }
      ctx.globalAlpha = 1;
      lastCounts.drawnEdges=de;
      let dn=0;
      for(const d of N){
        // 半径不乘 vk：屏幕空间恒定像素（与作者画布一致），缩放时点大小稳定
        const r=radiusOf(d), X=sx(d), Y=sy(d);
        if(X<-30||X>w+30||Y<-30||Y>h+30) continue;
        ctx.beginPath(); ctx.arc(X,Y,r,0,Math.PI*2);
        // 节点底色 = 按共现社群取色（同色 = 同社群）；选中/邻居用高亮色覆盖以便定位
        ctx.fillStyle = (sel===d.id || (sel!=null && nbrs.has(d.id))) ? PAL[0] : colorOf(d);
        ctx.fill();
        // 描边：选中节点额外用**卡片身份色**加一圈（强化"这是哪张网络"的身份感，
        // 与卡片层 --net-c 同源），其余用常规描边
        ctx.lineWidth = (sel===d.id?2:1);
        ctx.strokeStyle = (sel===d.id) ? CASE_COL : sk.nodeEdge;
        ctx.stroke();
        dn++;
      }
      lastCounts.drawnNodes=dn;
      // 标签：预算内按 degree 降序；v1.0.0 修——
      // 小共现群（灰色/绿色孤群）的节点 degree 天然低、标签全被大群挤掉。
      // 先给每个社群保底 1 个标签（该群 degree 最高者），剩余预算再全局分配。
      const budget=labelBudget(); let li=0, drawn=0;
      ctx.textAlign='center'; ctx.textBaseline='alphabetic';
      ctx.font='11px -apple-system,"PingFang SC",sans-serif';
      const _gBest=new Map();
      for(const i of byDeg){
        const g=groupId[N[i].id]||0;
        if(!_gBest.has(g)) _gBest.set(g,i);
      }
      const _gPicked=new Set(_gBest.values());
      for(const i of _gPicked){
        const d=N[i]; const X=sx(d), Y=sy(d), r=radiusOf(d);
        if(X<6||X>w-6||Y<14||Y>h-6) continue;
        const t=String(d.label||d.id);
        ctx.lineWidth=3; ctx.strokeStyle=sk.halo; ctx.strokeText(t, X, Y-r-3);
        ctx.fillStyle=sk.label; ctx.fillText(t, X, Y-r-3);
        li++; drawn++;
      }
      for(const i of byDeg){
        if(li>=budget) break;
        if(_gPicked.has(i)) continue;
        const d=N[i]; const X=sx(d), Y=sy(d), r=radiusOf(d);
        if(X<6||X>w-6||Y<14||Y>h-6) continue;
        const t=String(d.label||d.id);
        ctx.lineWidth=3; ctx.strokeStyle=sk.halo; ctx.strokeText(t, X, Y-r-3);
        ctx.fillStyle=sk.label; ctx.fillText(t, X, Y-r-3);
        li++; drawn++;
      }
      lastCounts.labels=drawn;
      if(hov!=null){
        const d=byId[hov];
        if(d){ const X=sx(d), Y=sy(d);
          ctx.font='12px -apple-system,"PingFang SC",sans-serif'; ctx.textAlign='left';
          const t=String(d.label||d.id)+'　篇数 '+(d.df!=null?d.df:'—')+'　连接 '+(d.degree!=null?d.degree:'—');
          const tw=ctx.measureText(t).width;
          ctx.fillStyle='rgba(20,20,20,.86)'; ctx.fillRect(X+8, Y-24, tw+14, 20);
          ctx.fillStyle='#fff'; ctx.fillText(t, X+15, Y-9);
        }
      }
    }

    let raf=null;
    function invalidate(){
      if(raf) return;
      raf = requestAnimationFrame(function(){ raf=null; draw(); });
    }
    function hit(mx,my){
      let best=null, bd=1e9;
      for(const d of N){ const X=sx(d), Y=sy(d), r=radiusOf(d)+3;
        const dd=(X-mx)*(X-mx)+(Y-my)*(Y-my);
        if(dd<=r*r && dd<bd){ bd=dd; best=d.id; } }
      return best;
    }
    let panning=false, px0=0, py0=0;
    if(cv.addEventListener){
      cv.addEventListener('pointermove', function(ev){
        const rc=cv.getBoundingClientRect(); const mx=ev.clientX-rc.left, my=ev.clientY-rc.top;
        if(panning){ vx+=mx-px0; vy+=my-py0; px0=mx; py0=my; invalidate(); return; }
        const hid=hit(mx,my);
        if(hid!==hov){ hov=hid; invalidate(); }
      });
      cv.addEventListener('pointerdown', function(ev){
        const rc=cv.getBoundingClientRect(); px0=ev.clientX-rc.left; py0=ev.clientY-rc.top;
        const h2=hit(px0,py0);
        if(h2){ sel=h2; nbrs=new Set();
          for(const e of E){ if(e.s===sel) nbrs.add(e.t); else if(e.t===sel) nbrs.add(e.s); }
          invalidate();
        } else { panning=true;
          if(cv.setPointerCapture){ try{ cv.setPointerCapture(ev.pointerId); }catch(e){} } }
      });
      cv.addEventListener('pointerup', function(){ panning=false; });
      cv.addEventListener('pointerleave', function(){ hov=null; panning=false; invalidate(); });
      cv.addEventListener('dblclick', function(){ sel=null; nbrs=new Set(); vInit=false; invalidate(); });
      cv.addEventListener('wheel', function(ev){
        if(!(ev.ctrlKey||ev.metaKey)) return; ev.preventDefault();
        const rc=cv.getBoundingClientRect(); const mx=ev.clientX-rc.left, my=ev.clientY-rc.top;
        // 缩放上下限相对 fit 视图（vkFit）计算：vk 的绝对值量级取决于坐标跨度（归一化
        // 坐标下可达数百），写死绝对值（旧代码 0.15~9）会把 fit 值本身排除在范围外。
        const nk=Math.max(vkFit*0.15, Math.min(vkFit*9, vk*(ev.deltaY<0?1.15:1/1.15)));
        vx=mx-(mx-vx)*(nk/vk); vy=my-(my-vy)*(nk/vk); vk=nk; invalidate();
      }, {passive:false});
    }

    function exportPNG(){ draw(); window.__dlPNG(cv, 2, fname+'.png'); }
    function exportSVG(){
      const w=(cv.clientWidth||900), h=(cv.clientHeight||620), ns='http://www.w3.org/2000/svg';
      const svg=document.createElementNS(ns,'svg');
      svg.setAttribute('xmlns',ns); svg.setAttribute('width',w); svg.setAttribute('height',h);
      svg.setAttribute('viewBox','0 0 '+w+' '+h);
      const bg=document.createElementNS(ns,'rect');
      bg.setAttribute('width',w); bg.setAttribute('height',h); bg.setAttribute('fill','#fff');
      svg.appendChild(bg);
      const ge=document.createElementNS(ns,'g');
      for(const e of E){ const a=byId[e.s], b=byId[e.t]; if(!a||!b) continue;
        const ln=document.createElementNS(ns,'line');
        ln.setAttribute('x1',sx(a).toFixed(1)); ln.setAttribute('y1',sy(a).toFixed(1));
        ln.setAttribute('x2',sx(b).toFixed(1)); ln.setAttribute('y2',sy(b).toFixed(1));
        ln.setAttribute('stroke','#94A3B8'); ln.setAttribute('stroke-opacity','0.5');
        ln.setAttribute('stroke-width','1'); ge.appendChild(ln); }
      svg.appendChild(ge);
      const gn=document.createElementNS(ns,'g');
      for(const d of N){ const X=sx(d), Y=sy(d), r=radiusOf(d);
        if(X<-20||X>w+20||Y<-20||Y>h+20) continue;
        const c=document.createElementNS(ns,'circle');
        c.setAttribute('cx',X.toFixed(1)); c.setAttribute('cy',Y.toFixed(1)); c.setAttribute('r',r.toFixed(1));
        // SVG 导出与画布口径一致：节点 fill = 共现社群色（同色 = 同社群）
        c.setAttribute('fill',colorOf(d)); c.setAttribute('stroke','rgba(20,20,20,0.35)'); c.setAttribute('stroke-width','0.7');
        gn.appendChild(c); }
      svg.appendChild(gn);
      const gt=document.createElementNS(ns,'g');
      gt.setAttribute('font-family','-apple-system,"PingFang SC",sans-serif');
      gt.setAttribute('font-size','11'); gt.setAttribute('text-anchor','middle');
      const budget=labelBudget(); let cnt=0;
      for(const i of byDeg){ if(cnt>=budget) break; const d=N[i]; const X=sx(d), Y=sy(d);
        if(X<0||X>w||Y<0||Y>h) continue;
        const t=document.createElementNS(ns,'text');
        t.setAttribute('x',X.toFixed(1)); t.setAttribute('y',(Y-radiusOf(d)-3).toFixed(1));
        t.setAttribute('fill','#2c2c2a'); t.textContent=String(d.label||d.id); gt.appendChild(t); cnt++; }
      svg.appendChild(gt);
      window.__dlSVG(svg, fname+'.svg');
    }
    window.__NET_EXPORTS = window.__NET_EXPORTS || {};
    window.__NET_EXPORTS[slug] = {png:exportPNG, svg:exportSVG};

    if(window.addEventListener) window.addEventListener('resize', function(){ vInit=false; invalidate(); });
    if(window.ResizeObserver){ let lw=-1, lh=-1;
      new ResizeObserver(function(){ const w=cv.clientWidth, h=cv.clientHeight;
        if(w===lw&&h===lh) return; lw=w; lh=h; if(!w||!h||w<2||h<2) return; vInit=false; invalidate(); }).observe(cv); }
    if(cv.parentElement && cv.parentElement.style) cv.parentElement.style.position='relative';

    vInit=false; draw();

    // 测试钩子：供回归探针驱动一帧并做数值断言（对齐 _probe_authnet.js 的用法）
    window[cfg.testGlobal] = {
      pump: function(){ draw(); return {nodes:N.length, drawnNodes:lastCounts.drawnNodes,
                                        drawnEdges:lastCounts.drawnEdges, labels:lastCounts.labels}; },
      counts: function(){ return {nodes:N.length, edges:E.length, drawnNodes:lastCounts.drawnNodes,
                                  drawnEdges:lastCounts.drawnEdges, labels:lastCounts.labels}; },
      layoutSanity: function(){
        let bad=0, minX=Infinity, maxX=-Infinity, minY=Infinity, maxY=-Infinity;
        for(const d of N){ if(!Number.isFinite(d.px)||!Number.isFinite(d.py)){ bad++; continue; }
          if(d.px<minX)minX=d.px; if(d.px>maxX)maxX=d.px;
          if(d.py<minY)minY=d.py; if(d.py>maxY)maxY=d.py; }
        return {total:N.length, badXY:bad, spanX:maxX-minX, spanY:maxY-minY};
      },
      // 暴露每个节点的屏幕坐标/半径/填充色/所属群（仍在 NETVIEW_JS 段内），
      // 供真实浏览器做像素级验证（截图采样圆心像素）与"颜色种类数"断言 —— 否则
      // "同色 = 同群"只能靠肉眼看图，无法给出量化证据。data-space 坐标另由
      // layoutSanity + 节点 px/py 提供。
      nodeDump: function(){
        // r 报屏幕半径（radiusOf 不乘 vk，即真实像素半径）——探针据此判断节点是否被
        // 缩放异常放大（修复前 r 会被 vk 放大到数十像素，是"挤成一团"的旁证）。
        // group 报**实际用于着色**的群 id（community 优先，无则 component，再兜底），
        // community/component 两字段原样带出，便于核对"颜色 == PAL[group % 14]"。
        return N.map(function(d){ return {id:d.id, x:sx(d), y:sy(d), r:radiusOf(d),
          color:colorOf(d), group:(groupId[d.id]==null?0:groupId[d.id]),
          community:(d.community==null?null:d.community),
          component:(d.component==null?null:d.component)}; });
      },
      colorCount: function(){
        const s=new Set(); N.forEach(function(d){ s.add(colorOf(d)); }); return s.size;
      }
    };
    return window[cfg.testGlobal];
  };
  // 初始化：有哪个全局载荷就画哪张。name 决定下载文件名（图表名）。
  // 机构名固定；引文图名按模式区分（与正文标题保持一致），由 Python 端的
  // 按钮 data-name 也能对照，但文件名以这里的 name 为准。
  if(window.__INSTNET__) window.__makeNetView({canvasId:'instnet', data:window.__INSTNET__, slug:'instnet', name:'机构共现网络', color:window.__INSTNET_COLOR__, testGlobal:'__INSTNET_TEST__'});
  if(window.__CITNET__) window.__makeNetView({canvasId:'citnet', data:window.__CITNET__, slug:'citnet', name:(window.__CITNET_NAME__||'引文网络'), color:window.__CITNET_COLOR__, testGlobal:'__CITNET_TEST__'});
})();
"""

NAV_JS = r"""
(function(){
  var links = Array.prototype.slice.call(
    document.querySelectorAll('.side .toc a'));
  if(!links.length) return;
  var pairs = [];
  links.forEach(function(a){
    var id = (a.getAttribute('href')||'').replace('#','');
    var el = id ? document.getElementById(id) : null;
    if(el) pairs.push([el, a]);
  });
  if(!pairs.length) return;
  var ticking = false;
  function sync(){
    ticking = false;
    var y = window.pageYOffset + 140;
    var cur = pairs[0][0];
    for(var i=0;i<pairs.length;i++){ if(pairs[i][0].offsetTop <= y) cur = pairs[i][0]; }
    pairs.forEach(function(p){
      var li = p[1].closest ? p[1].closest('li') : null;
      if(li) li.classList.toggle('on', p[0] === cur);
    });
  }
  window.addEventListener('scroll', function(){
    if(ticking) return; ticking = true;
    requestAnimationFrame(sync);
  }, {passive:true});
  window.addEventListener('resize', sync, {passive:true});
  sync();
})();
"""




def _summary_html(d, clusters, kw_net=None, bursts=None):
    """结论摘要：把最该先看到的几件事压缩成 3–5 句。

    此前报告开篇是「数据体检」（缺关键词多少、有无重复），这些是过程信息；
    用户最先想知道的是「这个领域在研究什么、有几个主题、近年在往哪走」。
    故新增本节置于标题之后。
    """
    cov = d.get("coverage") or {}
    total = cov.get("total", 0)
    if not clusters:
        return ""
    sizes = sorted((c.get("size", 0) for c in clusters), reverse=True)
    top1 = max(clusters, key=lambda c: c.get("size", 0))
    # 主题名在卡片渲染时才算出来，这里复用同一套命名逻辑
    top1_name, _ = label_topic(top1.get("top_terms", []))
    if top1_name == NON_TOPIC_KEY:
        top1_name = ""
    n_nt = sum(1 for c in clusters
               if label_topic(c.get("top_terms", []))[0] == NON_TOPIC_KEY)
    span_years = [c.get("year_range") for c in clusters if c.get("year_range")]
    lo = min(y[0] for y in span_years) if span_years else None
    hi = max(y[1] for y in span_years) if span_years else None

    pts = []
    pts.append(f"本报告基于 <b>{total:,}</b> 篇题录，"
               f"自动识别出 <b>{len(clusters)}</b> 个研究主题，"
               f"覆盖 {lo}–{hi} 年。")
    if top1_name:
        pts.append(f"篇幅最大的主题是<b>{esc(top1_name)}</b>"
                   f"（{top1.get('size',0)} 篇，占 {top1.get('pct',0)}%），"
                   f"关键词集中在 "
                   f"{esc('、'.join((top1.get('top_terms') or [])[:4]))}。")
    if len(sizes) > 1 and sizes[0] > 0:
        pts.append(f"主题分布"
                   f"{'较均衡' if sizes[0] / max(1, sizes[1]) < 1.8 else '不均衡，头部主题明显占优'}"
                   f"（最大/次大 = {sizes[0]}:{sizes[1]}）。")
    bl = _burst_list(bursts)
    if bl:
        kw = [b.get("keyword") for b in bl[:5] if b.get("keyword")]
        if kw:
            pts.append(f"突现词（近期升温方向）：{esc('、'.join(kw))}。")
    if n_nt:
        pts.append(f"其中 {n_nt} 个主题经算法判定为<b>非研究主题</b>"
                   f"（多为通用词构成），解读时应跳过。")
    if cov.get("keyword_coverage_pct") is not None:
        kc = cov["keyword_coverage_pct"]
        if kc < 90:
            pts.append(f"注意：仅 {kc}% 的题录带关键词字段，"
                       f"其余主题边界由标题与摘要推断，解读需谨慎。")
    return ('<div class="summary"><h2>结论摘要</h2><ul>'
            + "".join(f"<li>{x}</li>" for x in pts)
            + '</ul><p class="note">以上为算法自动归纳，'
              '数值口径见下方各章；主题命名来自内置术语表与关键词回退，'
              '建议你按自己的判断调整。</p></div>')


def _collect_present_sections(frags):
    """扫描最终 HTML 片段里实际出现的章节 id，供目录过滤。

    frags 由调用方传入（build_html 的局部变量）——不能在此直接引用
    那些局部名，模块级函数看不到它们。

    [!] 这里**只能**把「无条件拼接进 html_out」的章节列为恒存在。
    若把 s03（主题 × 年份演化）写进恒存在名单，而该章节的 HTML
    只在 `--evolution` 有数据时才生成 —— 没传演化数据时，目录里
    就会照样列着「主题 × 年份演化」，点进去一片空白。
    有没有内容，必须由**产物本身**说了算，不能靠白名单。
    """
    ids = set()
    for frag in frags:
        if not frag:
            continue
        for m in re.finditer(r'id="(s\d+)"', frag):
            ids.add(m.group(1))
    for sid in ("s01", "s02", "s04"):     # 这三个直接写在 html_out 里，恒存在
        ids.add(sid)
    return ids


def _toc_html(sections, present=None):
    """章节目录。章节数多，读者需要一个跳转入口。

    sections: [(anchor, 标题, 是否核心章节)]
    present: 实际生成的章节 id 集合。为 None 时不过滤。
             某些章节会因数据缺失被整节略去（如阅读状态仅在题录
             确含已读记录时出现），目录里留死链会让读者点了没内容。
    """
    if present is not None:
        sections = [(a, t, k) for a, t, k in sections if a in present]
    if not sections:
        return ""
    items = []
    for i, (aid, title, key) in enumerate(sections, 1):
        cls = ' class="g"' if key else ''
        items.append(f'<li{cls}><a href="#{aid}">'
                     f'<span class="n">{i:02d}</span>'
                     f'<span>{esc(title)}</span></a></li>')
    return ('<nav class="toc"><div class="toc-t">目录</div><ol>'
            + "".join(items) + '</ol></nav>')


def _renumber_sections(html_str: str, order) -> str:
    """把正文各 <h2 id="sXX"> 后面的编号胶囊，改写成它在最终顺序里的序号。

    为什么需要：章节编号此前是**手写**在每段 f-string 里的（S13、04、03…），
    而目录用的是遍历序号。两者本来就不一致（读者看到「目录 03 / 正文 S13」），
    章节一重排就更是彻底打架。这里以 order 为唯一事实来源统一回填。

    [!] 编号只发给**实际渲染出来**的章节，缺席章节不占号。
    否则没传演化数据时，正文会从 01、02、03 直接跳到 05，
    而目录是 01…04 连续 —— 又变成"目录与正文对不上"。
    """
    rank = {sid: i for i, (sid, _t, _k) in enumerate(order)}
    pat = re.compile(r'<h2\s+id="(?P<sid>s\d+)"\s*>\s*<span class="n">[^<]*</span>')
    found = [mm.group("sid") for mm in pat.finditer(html_str)]
    present = sorted({s for s in found if s in rank}, key=lambda s: rank[s])
    num = {sid: i for i, sid in enumerate(present, 1)}

    def _sub(mm):
        sid = mm.group("sid")
        n = num.get(sid)
        if not n:
            return mm.group(0)
        return '<h2 id="' + sid + '"><span class="n">' + format(n, "02d") + '</span>'

    return pat.sub(_sub, html_str)


def _pubstats_html(pub):
    """发文量与趋势章节。

    回答用户最常问的三件事：一共多少篇、逐年多少、是在扩张还是收缩。
    数据源可以是整库，也可以是 `--topic` 筛出的单个主题子集。
    """
    if not pub or not pub.get("total"):
        return ""
    py = pub.get("per_year") or {}
    if not py:
        return ""
    lab = pub.get("label", "全库")
    mx = max(py.values()) or 1
    # 三条序列必须同时在场，否则读不出「量」与「向」的区别：
    #   ① 逐年发文（线·左轴）—— 当年产出，看波动；
    #   ② 累计发文（线·右轴）—— 存量积累速度，判断领域是否在持续吸纳；
    #   ③ 趋势线（虚线·左轴）—— 逐年发文的**居中移动平均**，把噪声与方向分开。
    # 此前只有①，用户无法判断"是在扩张还是见顶"。
    _pts = sorted((int(k), v) for k, v in py.items())
    _ys = [y for y, _ in _pts]
    _vs = [v for _, v in _pts]
    _n = len(_vs)

    _cum, _acc = [], 0
    for _v in _vs:
        _acc += _v
        _cum.append(_acc)
    _cumax = _acc or 1

    # [!] 口径：趋势线用曲线，不用直线拟合。
    #   最小二乘线性拟合（一条直线）在"先升后降 / 后段见顶"这类
    #   真实曲线上严重失真 —— 直线只反映全局平均斜率，看不到拐点，把"见顶回落"
    #   画成"持续上升"。故用**居中移动平均**：对每个年份取以它为中心、半径 half
    #   的窗口内年均值。窗口**可配**（pub.trend_window，默认 3 年）。
    #   边缘自动收缩窗口（不填充 0、也不丢弃首尾年），避免造出假的 V 形；
    #   年份数不足一个窗口时退化为原始值（平滑会凭空造出趋势，此时不作平滑）。
    try:
        _win = int(pub.get("trend_window") or 3)
    except (TypeError, ValueError):
        _win = 3
    if _win < 3:
        _win = 3
    if _win % 2 == 0:          # 居中窗口必须为奇数，否则"中心"有歧义
        _win += 1
    if _n >= _win:
        _half = _win // 2
        _tv = []
        for _i in range(_n):
            _lo, _hi = max(0, _i - _half), min(_n, _i + _half + 1)
            _w = _vs[_lo:_hi]
            _tv.append(sum(_w) / len(_w))
    else:
        _tv = [float(v) for v in _vs]

    # ── 双轴坐标系（Excel 风格）──
    # 坐标系要求：双轴标注齐全、像 Excel 一样清清楚楚。
    # 只画两条虚线网格 + 两个数字（没有轴线、没有刻度线、没有轴标题）时，
    # 读者无法把柱高对应到具体数值。这里补齐：左轴（逐年发文）、
    # 右轴（累计）、底部 X 轴（年份，带刻度线）、水平网格、轴标题与单位。
    def _nice(v, ticks=5):
        """把量程抬到「好看」的刻度（1/2/2.5/5 × 10^k），Excel 的做法。"""
        try:
            v = float(v)
        except (TypeError, ValueError):
            v = 0.0
        if v <= 0:
            return float(ticks), 1.0
        raw = v / ticks
        mag = 1.0
        while mag * 10 <= raw:
            mag *= 10
        step = mag * 10
        for m in (1.0, 2.0, 2.5, 5.0):
            if mag * m >= raw:
                step = mag * m
                break
        top = step * ticks
        while top < v:
            top += step
        return top, step

    _lmax, _lstep = _nice(mx)
    _rmax, _rstep = _nice(_cumax)
    _W, _H, _PL, _PR, _PT, _PB = 780, 306, 74, 78, 32, 58
    _iw, _ih = _W - _PL - _PR, _H - _PT - _PB
    _AX = _PL + _iw          # 右轴 x
    _AY = _PT + _ih          # X 轴 y

    # X 坐标按**发文密度**映射：
    # 若按真实年份等距（2 年占 2 年宽）——但实测 OB/HRM 库 1968-1999 占
    # 37% 年份宽度只贡献 0.9% 发文，2020-2026 占 16% 宽度却贡献 82.6% 发文，
    # 导致高发文年的细节被压缩、低发文年占据大片空白。
    # 现在改为「宽度按累积发文占比分配」：
    #   · 每年占的宽度 ∝ 该年发文量占总发文的比例（82.6% 发文就占 82.6% 宽度）；
    #   · 低发文年被压缩到几乎不可见，高发文年充分展开；
    #   · 年份顺序保持真实（不按量排序），保证曲线仍按时间推进。
    # 坐标映射：year → 累积到该年的发文占比 × 总宽。
    _y_min, _y_max = (_ys[0], _ys[-1]) if _n > 0 else (0, 1)
    _y_span = max(1, _y_max - _y_min)
    # 预计算：每年起始的累积发文占比（含本年一半，让点落年中央）
    _cum_at: dict[int, float] = {}
    _acc = 0
    _total = sum(_vs) or 1
    for _i, _y in enumerate(_ys):
        _cum_at[_y] = (_acc + _vs[_i] / 2) / _total  # 年中点
        _acc += _vs[_i]
    def _sx_year(y):
        # 已知年份用累积占比；未知年份（如刻度线上的空年）按真实年份线性插值
        if y in _cum_at:
            return _PL + _cum_at[y] * _iw
        return _PL + (y - _y_min) / _y_span * _iw
    def _sx(i): return _sx_year(_ys[i])
    def _syL(v): return _AY - (v / _lmax * _ih if _lmax else 0)
    def _syR(v): return _AY - (v / _rmax * _ih if _rmax else 0)

    # ① 水平网格线 + 左轴刻度线/数字
    _grid, _ltick = [], []
    _k = 0
    while _k * _lstep <= _lmax + 1e-9:
        _yy = _syL(_k * _lstep)
        _grid.append(f'<line x1="{_PL}" y1="{_yy:.1f}" x2="{_AX}" y2="{_yy:.1f}" '
                     f'stroke="var(--border)" stroke-width="1" stroke-dasharray="3 4"/>')
        _ltick.append(f'<line x1="{_PL-5:.1f}" y1="{_yy:.1f}" x2="{_PL}" y2="{_yy:.1f}" '
                      f'stroke="var(--border-2)" stroke-width="1"/>'
                      f'<text x="{_PL-9:.1f}" y="{_yy+3.6:.1f}" text-anchor="end" '
                      f'font-size="10.5" font-family="var(--mono)" '
                      f'fill="var(--tx-3)">{_k*_lstep:g}</text>')
        _k += 1
    # ② 右轴刻度线/数字（累计）
    _rtick = []
    _k = 0
    while _k * _rstep <= _rmax + 1e-9:
        _yy = _syR(_k * _rstep)
        _rtick.append(f'<line x1="{_AX}" y1="{_yy:.1f}" x2="{_AX+5}" y2="{_yy:.1f}" '
                      f'stroke="var(--ac-2)" stroke-width="1" opacity=".55"/>'
                      f'<text x="{_AX+9}" y="{_yy+3.6:.1f}" text-anchor="start" '
                      f'font-size="10.5" font-family="var(--mono)" '
                      f'fill="var(--ac-2)">{_k*_rstep:g}</text>')
        _k += 1
    # ③ 坐标轴本体 + ④ X 轴刻度线与年份
    _axes = (f'<line x1="{_PL}" y1="{_PT}" x2="{_PL}" y2="{_AY}" '
             f'stroke="var(--border-2)" stroke-width="1.3"/>'
             f'<line x1="{_AX}" y1="{_PT}" x2="{_AX}" y2="{_AY}" '
             f'stroke="var(--ac-2)" stroke-width="1.3" opacity=".6"/>'
             f'<line x1="{_PL}" y1="{_AY}" x2="{_AX}" y2="{_AY}" '
             f'stroke="var(--border-2)" stroke-width="1.3"/>')
    _xtick = []
    # 年份刻度：按发文密度映射后，均匀间隔的年份刻度在低发文区会挤在一起。
    # 改为「每个刻度年真实存在 + 相邻刻度在画布上至少间隔 32px」：
    #   · 候选刻度 = _ys 里实际有数据的年份（不画无数据年）；
    #   · 从右往左（新→旧）贪心选取：保证最新的年份一定标出，向左逐步放宽；
    #   · 这样低发文区只标 1-2 个关键年（如首篇年），高发文区密集标注。
    _min_gap = 32  # 像素
    _cands = sorted(_ys, reverse=True)
    _picked: list[int] = []
    _last_x = float("inf")
    for _yr in _cands:
        _x = _sx_year(_yr)
        if _last_x - _x >= _min_gap:
            _picked.append(_yr)
            _last_x = _x
    _picked.reverse()
    for _yr in _picked:
        _x = _sx_year(_yr)
        _xtick.append(f'<line x1="{_x:.1f}" y1="{_AY}" x2="{_x:.1f}" y2="{_AY+5}" '
                      f'stroke="var(--border-2)" stroke-width="1"/>'
                      f'<text x="{_x:.1f}" y="{_AY+19:.1f}" text-anchor="middle" '
                      f'font-size="10.5" font-family="var(--mono)" '
                      f'fill="var(--tx-2)">{_yr}</text>')
    # ⑤ 轴标题与单位（含口径提示，避免读者把"累计"误读为"总量"）
    _titles = (
        f'<text x="{_PL-9:.1f}" y="{_PT-12:.1f}" text-anchor="end" font-size="10.5" '
        f'font-weight="640" fill="var(--ac)">篇 / 年</text>'
        f'<text x="{_AX+9:.1f}" y="{_PT-12:.1f}" text-anchor="start" font-size="10.5" '
        f'font-weight="640" fill="var(--ac-2)">累计（篇）</text>'
        f'<text x="{_AX:.1f}" y="{_AY+38:.1f}" text-anchor="end" font-size="10.5" '
        f'font-weight="640" fill="var(--tx-2)">年份</text>'
        f'<text x="{_PL-9:.1f}" y="{_AY+38:.1f}" text-anchor="end" font-size="10" '
        f'fill="var(--tx-3)">X 轴 = 题录发表年</text>')
    # ⑥ 逐年发文（折线 + 圆点，左轴）
    # 需求：都改为折线」：三条序列统一为折线，避免柱+线混排时
    # 柱宽随年份数变化带来的视觉跳动，也更便于比较斜率（趋势）。
    _year_path = " ".join(
        f'{"M" if i==0 else "L"}{_sx(i):.1f},{_syL(v):.1f}'
        for i, v in enumerate(_vs))
    _year_area = (_year_path + f' L{_sx(_n-1):.1f},{_AY:.1f} L{_PL:.1f},{_AY:.1f} Z'
                  if _n else "")
    _year_dots = "".join(
        f'<circle cx="{_sx(i):.1f}" cy="{_syL(v):.1f}" r="{3.6 if v==mx else 2.9}" '
        f'fill="var(--ac)" stroke="var(--surface)" stroke-width="1.6">'
        f'<title>{_ys[i]} 年：逐年 {v} 篇 · 累计 {_cum[i]} 篇</title></circle>'
        for i, v in enumerate(_vs))
    # ⑦ 趋势线（虚线，左轴）—— 平滑曲线。
    #   仅把相邻点直连仍是折线，故用"中点二次贝塞尔"圆滑化：以相邻两点的中点为锚点、
    #   以真实数据点为控制点。曲线贴近数据点、但不引入虚假极值（比 Catmull-Rom 更克制）。
    def _curvy(points):
        if not points:
            return ""
        if len(points) == 1:
            _x, _y = points[0]
            return f"M{_x:.1f},{_y:.1f}"
        d = f"M{points[0][0]:.1f},{points[0][1]:.1f}"
        for _j in range(len(points) - 1):
            _x0, _y0 = points[_j]
            _x1, _y1 = points[_j + 1]
            _mx, _my = (_x0 + _x1) / 2.0, (_y0 + _y1) / 2.0
            if _j == 0:
                d += f" L{_mx:.1f},{_my:.1f}"
            else:
                d += f" Q{_x0:.1f},{_y0:.1f} {_mx:.1f},{_my:.1f}"
        _xl, _yl = points[-1]
        d += f" L{_xl:.1f},{_yl:.1f}"
        return d
    _trend_path = _curvy([(_sx(i), _syL(v)) for i, v in enumerate(_tv)])
    # ⑧ 累计线 + 圆点（右轴）
    _cum_path = " ".join(
        f'{"M" if i==0 else "L"}{_sx(i):.1f},{_syR(v):.1f}'
        for i, v in enumerate(_cum))
    _cum_dots = "".join(
        f'<circle cx="{_sx(i):.1f}" cy="{_syR(v):.1f}" r="3.2" '
        f'fill="var(--surface)" stroke="var(--ac-2)" stroke-width="2">'
        f'<title>{_ys[i]} 年累计：{v} 篇</title></circle>'
        for i, v in enumerate(_cum))
    # ⑨ 峰值标注（逐年）
    _pk_i = max(range(_n), key=lambda i: _vs[i]) if _n else -1
    _peak = (f'<circle cx="{_sx(_pk_i):.1f}" cy="{_syL(_vs[_pk_i]):.1f}" r="4.8" '
             f'fill="var(--mag)"/>'
             f'<text x="{_sx(_pk_i):.1f}" y="{_syL(_vs[_pk_i])-13:.1f}" '
             f'text-anchor="middle" font-size="11" font-weight="640" '
             f'fill="var(--mag)">峰值 {_vs[_pk_i]} 篇</text>') if _pk_i >= 0 else ""
    # ⑩ 趋势方向角标
    _dirdelta = (_tv[-1] - _tv[0]) if _n >= 2 else 0.0
    _dir = "上升" if _dirdelta > 0 else ("下降" if _dirdelta < 0 else "持平")
    _dir_col = ("var(--lime)" if _dir == "上升"
                else ("var(--dan)" if _dir == "下降" else "var(--tx-3)"))
    _dirtag = (f'<text x="{_PL:.1f}" y="{_PT-12:.1f}" font-size="11" '
               f'font-weight="640" fill="{_dir_col}">趋势{_dir}</text>')

    line_chart = (
        f'<svg class="pline" viewBox="0 0 {_W} {_H}" width="100%" '
        f'preserveAspectRatio="xMidYMid meet" role="img" '
        f'aria-label="发文量双轴折线图：逐年发文（左轴）、累计发文（右轴）、'
        f'{_win} 年移动平均趋势线（左轴）">'
        f'<defs><linearGradient id="pubArea" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0%" stop-color="var(--ac)" stop-opacity=".22"/>'
        f'<stop offset="100%" stop-color="var(--ac)" stop-opacity="0"/>'
        f'</linearGradient></defs>'
        f'{"".join(_grid)}{"".join(_ltick)}{"".join(_rtick)}{_axes}'
        f'{"".join(_xtick)}'
        f'<path d="{_year_area}" fill="url(#pubArea)"/>'
        f'<path d="{_year_path}" fill="none" stroke="var(--ac)" stroke-width="2.4" '
        f'stroke-linejoin="round" stroke-linecap="round"/>'
        f'<path d="{_trend_path}" fill="none" stroke="var(--amber)" '
        f'stroke-width="2" stroke-dasharray="6 4" stroke-linecap="round"/>'
        f'<path d="{_cum_path}" fill="none" stroke="var(--ac-2)" stroke-width="2.3" '
        f'stroke-linejoin="round" stroke-linecap="round"/>'
        f'{_year_dots}{_cum_dots}{_peak}{_titles}{_dirtag}'
        f'</svg>')
    # 图例：三个序列都必须有名字，否则读者不知道虚线是什么
    _chart_legend = (
        '<div class="chart-legend">'
        '<span><i class="sw" style="background:var(--ac)"></i>逐年发文（线·左轴）</span>'
        '<span><i class="sw" style="background:var(--ac-2)"></i>累计发文（线·右轴）</span>'
        f'<span><i class="sw dash" style="background:var(--amber)"></i>'
        f'趋势线（{_win} 年移动平均·左轴）</span>'
        '</div>')

    y0, y1 = (pub.get("year_range") or [None, None])[:2]
    kpi = [
        ("总发文量", f"{pub['total']:,} 篇"),
        ("时间跨度", f"{y0}–{y1}（{pub.get('span_years', 0)} 年）" if y0 else "—"),
        ("年均发文", f"{pub.get('mean_per_year', 0)} 篇"),
        ("发文高峰", f"{pub.get('peak_year')} 年 · {pub.get('peak_count')} 篇"),
        ("整体趋势", f"{pub.get('trend', '—')}"),
        ("末段较首段", (f"{pub['growth_pct']:+.0f}%"
                    if pub.get("growth_pct") is not None else "—")),
    ]
    kpi_html = "".join(
        f'<div class="kpi"><div class="l">{esc(l)}</div>'
        f'<div class="v">{esc(str(v))}</div></div>' for l, v in kpi)
    trend_cls = {"上升": "ok", "下降": "danger"}.get(pub.get("trend"), "warn")
    bits = [f'<b>{esc(str(pub.get("trend", "—")))}</b>']
    if pub.get("growth_pct") is not None:
        bits.append(f"（末段较首段 {pub['growth_pct']:+.0f}%）")
    if pub.get("currently_growing") is True:
        bits.append("，近三年逐年递增，仍在扩张期")
    elif pub.get("currently_growing") is False:
        bits.append("，最近一年较上年回落，可能进入平台期")
    if pub.get("turning_years"):
        bits.append("；增速反转年份："
                    + "、".join(str(x) for x in pub["turning_years"]))
    readout = "".join(
        f"<li>{x}</li>" for x in (pub.get("readout") or []) if x)

    miss = ""
    if pub.get("missing_year"):
        miss = (f'<p class="hintline">注：{pub["missing_year"]} 篇'
                f'（{pub["missing_year_pct"]}%）题录缺年份，未计入逐年分布，'
                f'但计入总发文量 —— 故各年之和小于总数。</p>')
    return f"""<section>
<h2 id="s13"><span class="n">02</span>发文量与趋势</h2>
<div class="sublab">统计范围：<b>{esc(lab)}</b>
 <span class="hintline">折线=逐年发文量（左轴）· 实线=累计发文（右轴）·
 虚线={_win} 年移动平均趋势（左轴）。三条一起看，才能区分「产出波动」与「真实方向」。</span></div>
<div class="kpis k3">{kpi_html}</div>
<div class="card">
<div class="figbar">
<button class="fbtn" type="button" data-fig="pubtrend" data-save="png" data-name="发文量趋势图" title="把这张折线图保存为 PNG">保存 PNG</button>
<button class="fbtn" type="button" data-fig="pubtrend" data-save="svg" data-name="发文量趋势图" title="保存为矢量 SVG（可无限放大、可再编辑）">保存 SVG</button>
</div>
{_chart_legend}
<div class="pline-wrap">{line_chart}</div>
<div class="readout"><ul>{readout}</ul>
<p class="note" style="margin:6px 0 0">趋势判定：{''.join(bits)}</p></div>
{miss}
</div></section>"""

def _label_col_px(names, lo=96, hi=240):
    """行标签列宽（像素）：按最长标签估算（CJK≈13px/字，ASCII≈7px/字），夹在 [lo,hi]。

    为什么按内容估算而不是写死：fixed 布局下首列宽就是这个固定像素值，给太小会把
    主题/作者名截断；给太大会挤占数据列。取"最长标签 + 18px 余量"再夹到 [96,240]，
    与 JS 导出器 drawHeatmap 的 labelW 估算口径一致（保证屏幕与导出图观感接近）。
    """
    best = 0
    for s in names:
        w = 0
        for ch in str(s or ""):
            w += 13 if ord(ch) > 0x2E7F else 7      # CJK 全角 / ASCII
        best = max(best, w)
    return max(lo, min(hi, best + 18))


def _mx_colgroup(n_data, label_px):
    """fixed 布局用 <colgroup>：首列固定像素宽，数据列不设宽（`<col>`）。

    为什么这样能"铺满且左右不空"：table-layout:fixed 下，声明了宽度的列取声明值
    （首列 = label_px，不吸收富余），未声明宽度的 `<col>` 均分"容器宽 − 首列宽"。
    列数随数据变化，故由调用方按实际列数动态生成，不写死。
    """
    return ('<colgroup><col style="width:%dpx">' % int(label_px)
            + '<col>' * max(0, int(n_data)) + '</colgroup>')


def _mx_minw(label_px, n_data, cell_px):
    """窄屏横向滚动阈值（像素）：标签列 + 数据列最小宽之和（含 border-spacing 余量）。

    宽屏时该值 < 容器宽，width:100% 生效、表格铺满；窄屏（列多）时表格按此 min-width
    溢出，由外层 .tw / .matrix 横向滚动，不撑破整页（项目既有窄屏约定）。
    """
    return int(label_px) + int(n_data) * int(cell_px) + 8


def _cross_html(cross):
    """多维交叉共现章节：关键词×作者、关键词×年份、作者×年份。

    与既有章节的分工：
        关键词共现网络  → 词与词（结构）
        主题 × 作者矩阵→ 主题（聚类结果）与作者
        本章节          → 原始关键词与作者/年份的直接交叉（人—词—时）
    """
    if not cross or not cross.get("kw_author"):
        return ""
    ka, ky, ay = cross["kw_author"], cross["kw_year"], cross["author_year"]

    # ① 关键词 × 作者：取共现最高的若干对
    pairs = []
    for k, row in (ka.get("matrix") or {}).items():
        for a, n in row.items():
            if n >= 2:
                pairs.append((n, k, a))
    pairs.sort(reverse=True)
    top_pairs = pairs[:12]
    p_rows = "".join(
        f'<tr><td>{esc(k)}</td><td>{esc(a)}</td>'
        f'<td class="num">{n}</td></tr>' for n, k, a in top_pairs)

    # ② 作者核心词
    core_rows = "".join(
        f'<tr><td>{esc(a)}</td><td>{esc(" / ".join(ws))}</td></tr>'
        for a, ws in list((ka.get("author_core") or {}).items())[:10])

    # ③ 关键词首现年（年代进入序列）
    fs = ky.get("first_seen") or {}
    pk = ky.get("peak_year") or {}
    yr_rows = "".join(
        f'<tr><td>{esc(k)}</td><td class="num">{fs.get(k, "—")}</td>'
        f'<td class="num">{pk.get(k, "—")}</td></tr>'
        for k in (ky.get("keywords") or [])[:12])

    v = ka.get("cramers_v")
    nmi = ky.get("nmi")
    readout = "".join(f"<li>{esc(x)}</li>" for x in (cross.get("readout") or []))

    def tbl(title, head, body, note=""):
        if not body:
            return ""
        n = f'<p class="hintline">{note}</p>' if note else ""
        return (f'<div class="card"><div class="sublab">{title}</div>'
                f'<table class="mx cols-auto"><thead><tr>{head}</tr></thead>'
                f'<tbody>{body}</tbody></table>{n}</div>')

    # [!] 此处此前写作 `<section id="s14">` 里套一个**没有 id** 的 <h2>：
    #   _renumber_sections() 的正则只认 `<h2 id="sXX">`，于是本节永远拿不到
    #   回填编号（正文本节停留在手写的 "S14"），而它又占着 SECTION_ORDER 里的
    #   一个位置 —— 结果本节之后的所有章节，正文号都比目录号少 1（用户可见的
    #   "目录写 10、正文写 09"）。现在把 id 落到 h2 上，外层换成无样式语义的 div。
    #   章节登记不受影响：_collect_present_sections 扫的是片段里任意 id="sXX"。
    return f"""<div id="s14-sect">
<h2 id="s14"><span class="n">00</span>多维交叉共现</h2>
<p class="note">在「关键词共现网络」之外，补上<b>人—词—时</b>三个视角的交叉。
关联强度用 Cramér's V（关键词×作者）与 NMI（关键词×年份）衡量，
避免把"高频共现"误读成"强关联"。</p>
<div class="readout"><ul>{readout}</ul></div>
{tbl("关键词 × 作者：共现最密的组合", "<th>关键词</th><th>作者</th><th class=\"num\">共现文献数</th>", p_rows,
     "仅列出共现≥2 篇的组合；单个组合的共现数高不等于有强关联，需结合 Cramér's V 一起看。")}
{tbl("高产作者的核心关键词", "<th>作者</th><th>核心词</th>", core_rows,
     "每位作者出现频次最高的 3 个关键词，可视为其研究方向标签。")}
{tbl("关键词进入领域的时间", "<th>关键词</th><th class=\"num\">首现年</th><th class=\"num\">峰值年</th>", yr_rows,
     f"首现年 = 该词首次出现的年份；峰值年 = 出现最多的年份。（NMI = {nmi}）")}
</div>"""

# 重复类型：把英文枚举译成中文，并说明"哪里重复了"。
# [!] 此前直接输出 exact_title 等英文枚举，读者无法判断重复的依据，
#     也不知道该不该合并。
DUP_TYPE_ZH = {
    "exact_doi": ("DOI 完全相同", "两篇 DOI 一致 —— 几乎确定是同一篇"),
    "exact_title": ("标题完全相同", "题名字符串逐字一致"),
    "near_title": ("标题高度相似", "题名有编辑差异（大小写/标点/卷期前缀）"),
    "near_author_year": ("同作者同年份", "作者与年份相同、题名不同 —— 可能是同一研究的不同版本"),
    "exact_author_year_title": ("作者+年份+标题均一致", "三个字段全部相同"),
    "exact": ("完全重复", "多个字段完全一致"),
    "near": ("近似重复", "字段高度相似"),
}


def _dup_zh(t):
    """重复类型 →（中文名, 判断依据）的 HTML。"""
    v = DUP_TYPE_ZH.get(str(t or "").lower())
    if not v:
        return esc(str(t or ""))
    return ('<b>' + esc(v[0]) + '</b><br><span style="color:var(--tx-3);'
            'font-size:11.5px">' + esc(v[1]) + '</span>')



def _wrap_tables(html: str) -> str:
    """把所有 <table class="mx…"> 包进 .tw 横向滚动容器。

    [!] 移动端"表格跨页面"的根因修复：窄屏下表格比视口宽，
    若不套容器，浏览器会让**整页**横向溢出；套上 overflow-x:auto
    后只有表格自身滚动，页面布局不受影响。
    """
    if not html:
        return html
    out, i = [], 0
    # [!] 属性引号两种都要认。此前只匹配 class="mx…"，
    #   而突现检测表是用单引号拼的 class='mx bstab' → 逃过包装，
    #   窄屏下它会撑宽整页（正是"表格跨页面"的复现路径）。
    # [!] 再放宽：class 不再是**最后一个属性**。热力表(hmtable/heat)为窄屏滚动
    #   加了内联 style="min-width:…"，若仍要求 class 紧贴 '>'，它们就会逃过包装
    #   → 窄屏撑宽整页。故允许 <table ... class="mx…" ... 其它属性>，只要求含
    #   class="mx…"。匹配仍限定在单个开标签内（[^>]*），不会跨到嵌套。
    pat = re.compile(r"<table[^>]*class=[\"']mx[^\"']*[\"'][^>]*>", re.S)
    while True:
        m = pat.search(html, i)
        if not m:
            out.append(html[i:])
            break
        out.append(html[i:m.start()])
        # 找配对的 </table>（表格内不含嵌套 table）
        end = html.find("</table>", m.end())
        if end < 0:
            out.append(html[m.start():])
            break
        end += len("</table>")
        frag = html[m.start():end]
        # 已是方法说明表（nopad）则不套滚动容器——它本身自适应
        if "nopad" not in frag:
            out.append('<div class="tw">' + frag + "</div>")
        else:
            out.append(frag)
        i = end
    return "".join(out)


def _report_title(d):
    """报告标题按数据来源自适应。

    数据源可能是本地题录库，也可能是用户导入的题录文件
    （RIS/BibTeX/CNKI/WoS 等），标题按来源自适应，不写死某一种。
    """
    lib = d.get("library") or {}
    src = (lib.get("source") or "").strip()
    if src:
        return f"文献计量分析报告 · {src}"
    return "文献计量分析报告"


def _burst_list(bursts):
    """兼容两种入参：bursts 传dict（含 bursts 键）或直接传列表。"""
    if not bursts:
        return []
    if isinstance(bursts, dict):
        return bursts.get("bursts") or []
    if isinstance(bursts, list):
        return bursts
    return []


def _fy_of(n, lo, hi):
    """关键词首次出现年（缺失时从 years 逐年频次推算），并夹到 [lo, hi]。"""
    fy = n.get("first_year")
    if fy is None:
        ys = n.get("years") or {}
        try:
            fy = min(int(k) for k in ys) if ys else None
        except (TypeError, ValueError):
            fy = None
    if fy is None:
        fy = lo
    try:
        return max(lo, min(hi, int(fy)))
    except (TypeError, ValueError):
        return lo


def _ly_of(n, lo, hi):
    """关键词末次出现年。

    时间线若只标「首次出现年」——读者据此无法判断一个词是仍在延续
    还是早已退场，而「退场」恰恰是选题时最该避开的信号。故补上末次出现年，
    由它构成每行的活跃区间。
    """
    ly = n.get("last_year")
    if ly is None:
        ys = n.get("years") or {}
        try:
            ly = max(int(k) for k in ys) if ys else None
        except (TypeError, ValueError):
            ly = None
    if ly is None:
        ly = hi
    try:
        return max(lo, min(hi, int(ly)))
    except (TypeError, ValueError):
        return hi


def _timeline_html(kw_net, bursts=None):
    """关键词年份图（Timeline）—— 重写为 SVG。

    CSS 两列栅格 + 百分比 left 定位有三个硬伤，读者一眼就看出「完全错误」：
      1) 左右两列的定位基准不同（左列走文档流、右列走百分比 left），
         换字号或窄屏下标签与年份轴必然错位；
      2) 位置标记的透明度只有 --a≈0.16–0.34，肉眼几乎看不见，
         而且只是一个点 —— 看不出一个词的**活跃区间**；
      3) 只标「首次出现年」，读者无法判断该词是兴起、延续还是已经退场。

    本版直接画 SVG，几何全部显式计算，对齐由坐标保证（不再依赖 CSS 碰运气）：
      · 横轴 = 年份；纵轴 = 关键词（一行一个词）；
      · 每行一条「活跃区间」横条 = 首次出现年 → 末次出现年；
      · 条的深浅 = 该词文献量（df），一眼分出主次；
      · 峰值年画实心点，条末标出总文献量；
      · 突现词（burst）行首加 ▲、整行用强调色；
      · 每若干年一条竖向参考线，底部为年份刻度。
    """
    if not kw_net or not kw_net.get("nodes"):
        return ""
    nodes = kw_net["nodes"]
    yr = kw_net.get("year_range") or []
    if not yr or yr[0] is None or yr[1] is None or yr[1] <= yr[0]:
        return ""
    lo, hi = int(yr[0]), int(yr[1])
    span = max(1, hi - lo)

    # 先按文献量取前 N，再按首现年排序 —— 时间线上呈阶梯状，比按词频排更易读
    top = sorted(nodes, key=lambda n: -(n.get("df") or 0))[:22]
    top.sort(key=lambda n: (_fy_of(n, lo, hi), -(n.get("df") or 0)))
    n = len(top)
    if not n:
        return ""

    burst_words = {b.get("keyword") for b in _burst_list(bursts) if b.get("keyword")}
    max_df = max((t.get("df") or 1) for t in top) or 1

    LH, LABW, W, PT, PB = 22, 170, 880, 30, 34
    H = PT + n * LH + PB
    X0, X1 = LABW, W - 26
    PW = X1 - X0

    def X(y):
        return X0 + (float(y) - lo) / span * PW

    step = max(1, (hi - lo + 1) // 10)
    grid, ticks = [], []
    for y in range(lo, hi + 1):
        if (y - lo) % step and y != hi:
            continue
        x = X(y)
        grid.append(
            f'<line x1="{x:.1f}" y1="{PT - 12}" x2="{x:.1f}" '
            f'y2="{PT + n * LH:.1f}" stroke="var(--border)" '
            f'stroke-width="1" stroke-dasharray="3 4"/>')
        ticks.append(
            f'<text x="{x:.1f}" y="{PT + n * LH + 16}" text-anchor="middle" '
            f'font-size="10.5" fill="var(--tx-3)">{y}</text>')

    rows, mark_rows = [], 0
    for i, t in enumerate(top):
        name = str(t["id"])
        fy = _fy_of(t, lo, hi)
        ly = _ly_of(t, lo, hi)
        df = t.get("df") or 0
        try:
            peak = int(t.get("peak_year")) if t.get("peak_year") is not None else fy
        except (TypeError, ValueError):
            peak = fy
        peak = max(lo, min(hi, peak))
        is_b = name in burst_words
        if is_b:
            mark_rows += 1
        col = "var(--mag)" if is_b else "var(--ac)"
        # 深浅按文献量线性映射：主词饱和、边缘词淡，层次由数据决定
        op = 0.34 + 0.56 * (df / max_df)
        yc = PT + i * LH
        xa, xb = X(fy), X(ly)
        tip = f"{name}｜文献 {df}｜活跃 {fy}–{ly}｜峰值 {peak}"
        if is_b:
            tip += "｜突现词"
        fw = ' font-weight="600"' if is_b else ""
        left_mark = (f'<rect x="0" y="{yc:.1f}" width="3" height="{LH}" '
                     f'fill="{col}"/>') if is_b else ""
        tri = (f'<text x="{LABW - 4}" y="{yc + LH / 2 + 4:.1f}" '
               f'text-anchor="end" font-size="10" fill="var(--mag)">▲</text>'
               ) if is_b else ""
        rows.append(
            f'<g><title>{esc(tip)}</title>'
            f'<rect x="0" y="{yc:.1f}" width="{W}" height="{LH}" fill="transparent"/>'
            f'{left_mark}'
            f'<text x="{LABW - 16}" y="{yc + LH / 2 + 4:.1f}" text-anchor="end" '
            f'font-size="12" fill="{col if is_b else "var(--tx)"}"{fw}>'
            f'{esc(name)}</text>'
            f'{tri}'
            f'<rect x="{xa:.1f}" y="{yc + 6:.1f}" width="{max(3.0, xb - xa):.1f}" '
            f'height="{LH - 12}" rx="3" fill="{col}" opacity="{op:.2f}"/>'
            f'<circle cx="{X(peak):.1f}" cy="{yc + LH / 2:.1f}" r="3.4" '
            f'fill="{col}" stroke="var(--surface)" stroke-width="1.4"/>'
            f'<text x="{xb + 7:.1f}" y="{yc + LH / 2 + 3.6:.1f}" font-size="10" '
            f'fill="var(--tx-3)">{df}</text>'
            f'</g>')

    return f"""
<h2 id="s07"><span class="n">03</span>关键词年份图（Timeline）</h2>
<p class="note">横轴为年份，纵轴为关键词（一行一个词）。每行的横条是该词的
<b>活跃区间</b>（首次出现 → 末次出现），颜色越深表示该词文献量越大；
实心点为峰值年，条末数字为总文献量。<span class="burst-mark">▲</span>
标记突现词。用于判断各主题的兴起、延续与退场。</p>
<div class="card tlcard">
<div class="figbar">
<button class="fbtn" type="button" data-fig="timeline" data-save="png" data-name="关键词年份时间线" title="把这张时间线图保存为 PNG">保存 PNG</button>
<button class="fbtn" type="button" data-fig="timeline" data-save="svg" data-name="关键词年份时间线" title="保存为矢量 SVG（可无限放大、可再编辑）">保存 SVG</button>
</div>
<svg class="tlsvg" viewBox="0 0 {W} {H}" width="100%"
 preserveAspectRatio="xMinYMin meet" role="img"
 aria-label="关键词年份图：横轴年份，纵轴关键词，含活跃区间与突现标记">
<text x="0" y="14" font-size="11" fill="var(--tx-3)">关键词 \\ 年份</text>
<text x="{X1}" y="14" text-anchor="end" font-size="11"
 fill="var(--tx-3)">→ 时间</text>
{"".join(grid)}
{"".join(rows)}
{"".join(ticks)}
</svg></div>
<p class="note">统计口径：按文献量降序取前 {n} 个词，覆盖 {lo}–{hi} 年；
其中 {mark_rows} 个为突现词（Burstness）。▲ 行表示该词在峰值年显著升温。</p>
"""


def _net_slim(data):
    """把机构 / 引文网络产物瘦身为前端渲染真正用到的字段。

    与作者网络同一做法：只给 id/label/df/degree/weight 与边的 s/t/w；若产物已
    用 base64 int16 内联坐标（pos_encoded），原样带上，省掉首屏现场布局。
    """
    node = data.get("nodes") or []
    edge = data.get("edges") or []
    # community/community_size：节点按「共现社群」（加权标签传播）着色用（同色 = 同社群）。
    #   这是渲染端**优先**使用的着色维度：引文网络几乎全连通，按连通分量上色会退化成单色。
    # component/component_size：保留（连通分量语义，旧产物/下游依赖；community 缺失时兜底）。
    # x/y 明文坐标：pos_encoded 缺失时的兜底。旧产物无这些字段 → .get 返回 None
    # → JSON 里是 null → NETVIEW_JS 依次退回 component、再用并查集自算，绝不回落成单色。
    slim = [{"id": n.get("id"), "label": n.get("label", n.get("id")),
             "df": n.get("df", 0), "degree": n.get("degree", 0),
             "weight": n.get("weight", 0),
             "community": n.get("community"),
             "community_size": n.get("community_size"),
             "component": n.get("component"),
             "component_size": n.get("component_size"),
             "x": n.get("x"), "y": n.get("y")} for n in node]
    es = [{"s": e.get("source"), "t": e.get("target"), "w": e.get("weight", 1)}
          for e in edge]
    payload = {"nodes": slim, "edges": es}
    pe = data.get("pos_encoded")
    if (pe or {}).get("pos_b64"):
        payload["pos_encoded"] = pe
    return payload


def _network_section(sid, title, intro, data, js_global, canvas_id,
                     empty_lead, formats, fig_slug, color="#4F46E5", ncolor=14):
    """构造「机构共现 / 引文网络」章节，返回 (html, js)。

    为什么抽成公共函数：机构共现与引文（共被引 / 耦合）在报告侧完全同构
    （KPI + 一块画布 + 图注），差异只有标题、数据来源与空态措辞。若各写一份
    f-string，日后改动必然分叉，最终出现"两张图两套行为"。作者网络不并入本
    函数：它早于本函数存在、交互已被 _probe_authnet.js 锁定，重构无收益且高风险。

    [!] 硬规则（见 _collect_present_sections 注释里记录的 s03 空白死链坑）：
      · data 为空 / empty_state / nodes 或 edges 为空 → **一律返回 ("","")，整节不出现**
        （不进目录、正文也不留空壳）。
        用户明确要求："作者、引文或机构共线，如果没有，我觉得没必要在图上"。
        此前空态只渲染一张说明卡片、仍占目录一项 —— 读者点进去看到的是一个"说明页"，
        与"分析结果"混在一起，反而误导。现在改为：**明确没有的就不出现**，
        并在「数据体检」章里用一行如实交代"本数据源不含 XX 字段，故未生成 XX 网络"
        （由 build_html 汇总，见 net_notes_html）—— 既如实、又不拉出空章节。
      · 绝不画一张空网络冒充"有结果"；数字全部来自产物，不编造。
    """
    if not data:
        return "", ""
    node = data.get("nodes") or []
    edge = data.get("edges") or []

    # ── 空态：整节略去（说明文字改由「数据体检」统一交代）──
    if bool(data.get("empty_state")) or (not node) or (not edge):
        return "", ""

    st = data.get("stats") or {}

    # ── 非空 ──
    mn = st.get("nodes", len(node))
    me = st.get("edges", len(edge))
    dens = st.get("density", "—")
    iso = st.get("isolated", 0)
    kpi = "".join(
        f'<div class="kpi"><div class="l">{esc(l)}</div><div class="v">{esc(str(v))}</div></div>'
        for l, v in [
            ("节点数", f"{mn:,}"),
            ("连线数", f"{me:,}"),
            ("网络密度", f"{dens}"),
            ("孤立节点", f"{iso}"),
        ])
    # 网络主题色：随载荷一起注入（__INSTNET_COLOR__ / __CITNET_COLOR__）。
    # [!] 语义分工：主题色**只服务"卡片层"** —— --net-c 着色的标题竖条 /
    #   KPI 数值 / 图例色点，回答"这是哪张网络"；**节点颜色改由 community（社群）决定**
    #   （同色 = 同一个共现社群，见 NETVIEW_JS 的 colorOf；无 community 时退回
    #   component）。二者不再混用（改前节点也吃这个单色 → 全图一个色）。
    _cglobal = js_global[:-2] + "_COLOR__"
    js = (f"window.{js_global}={esc_json(_net_slim(data))};"
          f"window.{_cglobal}={esc_json(color)};")
    # 图例：把"卡片主色 vs 节点颜色"的语义分工写清楚（用户明确要求），并如实交代
    # 社群数与最大社群占比（判断"是否还显单色"的关键数字）、孤立节点剔除。
    _nc = st.get("communities")
    _ncomp = st.get("components")
    if _nc is not None:
        _lcp = st.get("largest_community_pct")
        _grp_note = (f"共 {_nc} 个，最大社群占 {_lcp}%；" if _lcp is not None
                     else f"共 {_nc} 个；")
        _grp_kind, _grp_how = "共现社群", "按加权标签传播做社群发现，社群内关系更紧密"
    elif _ncomp is not None:
        _grp_note = f"共 {_ncomp} 个；"
        _grp_kind, _grp_how = "共现群", "按网络连通分量划分"
    else:
        _grp_note = ""
        _grp_kind, _grp_how = "共现社群", "按加权标签传播做社群发现"
    _drop = st.get("isolated_dropped", 0) or 0
    if _drop:
        _iso_note = f"已剔除 {_drop} 个孤立节点（本库内无共现，未画入图中）；"
    elif iso:
        _iso_note = f"当前图中 {iso} 个孤立节点；"
    else:
        _iso_note = ""
    _legend = (
        f"<b>节点颜色 = {_grp_kind}</b>：同色 = 同一个{_grp_kind}（{_grp_how}，"
        + _grp_note +
        f"调色板共 {ncolor} 色，群多于色数时颜色循环复用）；"
        "<b>卡片主色</b>（标题竖条 / KPI / 图例色点）只标识“这是哪张网络”，"
        "与节点归属无关。" + _iso_note)
    html = f"""<h2 id="{sid}"><span class="n">00</span>{esc(title)}</h2>
<p class="note">{intro}</p>
<div class="card netcard net-accent" style="--net-c:{color}">
<div class="nsec">
<h4 class="nsec-h">{esc(title)}概览
 <span class="hintline">节点大小 ∝ 出现篇数；连线越粗 = 共现次数越多</span>
 <span class="net-key"><i class="dot"></i>卡片主色 = 本网络</span></h4>
<div class="figbar">
<button class="fbtn" type="button" data-fig="{fig_slug}" data-save="png"
 data-name="{esc(title)}" title="把当前视图保存为 2x 高清 PNG（白底，可直接投稿）">保存此图</button>
<button class="fbtn" type="button" data-fig="{fig_slug}" data-save="svg"
 data-name="{esc(title)}" title="保存为矢量 SVG（可无限放大、可再编辑）">保存 SVG</button>
</div>
<div class="kpis">{kpi}</div>
<div class="netrow" style="margin-top:6px"><span class="hintline">{_legend}</span></div>
</div>
<div class="nsec nsec-canvas">
<div class="net-canvas"><div class="canvaswrap">
<canvas id="{canvas_id}"></canvas>
<div class="overlay-ui bottom"><div class="keys">
<span class="touchnote"><b>拖节点</b> 微调 · <b>拖空白</b> 平移 · <b>点节点</b> 高亮 · <b>双击</b> 复位</span>
<span class="kbdonly"><b>Ctrl/⌘+滚轮</b> 缩放 · <b>拖空白</b> 平移 · <b>点节点</b> 高亮 · <b>双击</b> 复位视口</span>
</div></div>
</div><!-- /canvaswrap -->
</div></div>
</div>"""
    return html, js


def build_html(topics, network=None, evolution=None, reading=None,
               dup=None, age=None, author_topic=None, sna=None,
               bursts=None, kw_net=None, pub=None, cross=None,
               auth_net=None, inst_net=None, cit_net=None) -> str:
    d = topics
    cov = d["coverage"]
    diag = d["diagnostics"]
    clusters = d["clusters"]
    g = gini2([c["size"] for c in clusters])
    # [!] 「零丢弃校验」的数量列此前写的是结论文字（"[OK] 成立"），
    #   与同列其它行（都是数字）口径不一致 —— 数量列应显示**被丢弃的条数**
    #   （= 总数 − 四类已归档之和；本库为 0），校验结论归入右侧「说明」列。
    _tier = cov.get("tier") or {}
    _dropped = cov.get("total", 0) - sum(
        int(_tier.get(_k, 0) or 0)
        for _k in ("primary_abs", "primary_kw", "fallback_title", "empty"))
    reading_html = dup_html = age_html = authormatrix_html = sna_html = ""
    trend_html = bursts_html = ""

    # ── KPI ──
    warn = d["mode"] if "mode" in d else None
    busy = any("EndNote 正在运行" in w for w in diag.get("warnings", []))
    kpis = [
        ("文献总数", f"{cov['total']:,}"),
        ("识别主题", f"{len(clusters)}"),
        ("关键词覆盖", f"{cov['keyword_coverage_pct']}%"),
        ("中文文献", f"{cov['zh_pct']}%"),
        ("年份跨度", f"{cov['year_min']}–{cov['year_max']}"),
        ("均衡度 gini", f"{g:.3f}"),
    ]
    kpi_html = "".join(
        f'<div class="kpi"><div class="l">{esc(l)}</div><div class="v">{esc(v)}</div></div>'
        for l, v in kpis)

    # ── 主题卡 ──
    # 主题配色必须与画布节点**同一套映射**，否则图例色块与图中节点对不上。
    # JS 侧：cluster_id 升序去重后取 PAL[i % len]，这里照搬同一规则。
    #
    # [!] 旧色板是硬编码的 Tableau/Vega 风格（#4C78A8 #F58518 #54A24B…），
    #   与报告 v2 的「青→靛→品红」设计语言（--cy/--in/--mg）完全脱节，观感廉价。
    #   新色板按两条原则重排：
    #     1) **与页面同源**：整条色板落在与 --grad 同一明度/彩度区间，
    #        首位即品牌青 #0891B2，靛/品红也在列，整页因此是「一种语言的彩色」；
    #     2) **相邻簇色相相隔最远**：ci 升序即相邻簇，故按「贪心链」排序 ——
    #        每步选与上一色在最差色觉视图下 CIEDE2000 最大的未用色。
    #        实测（设计期用 Oklab+CIEDE2000+CVD 模块选出，生成器不随包提供）：
    #        相邻 min ΔE00 = 29.8(normal)/18.9(protan)/20.6(deutan)/3.1(tritan)，
    #        全面优于旧色板的 19.9/13.3/12.5/4.3；颜色仍只是第一通道，
    #        另有图例文字/侧栏/悬停/跨簇描边做冗余编码。
    #   三处复用同一常量：主题卡色点、百分比条、主题分布图例、对照条与画布节点。
    #   [!] 与 JS_NET 里的 const PAL 必须**逐位一致**（顺序也一致），改一处要同步改另一处。
    _PAL = ['#0891B2', '#EA580C', '#4F46E5', '#B45309', '#2563EB', '#E11D48',
            '#0E7490', '#DB2777', '#0D9488', '#D6336C', '#7C3AED', '#16A34A',
            '#64748B', '#65A30D']
    # 无主题归属 / 未归类的统一中性色（画布、图例、对照条三处同源）
    _NEUTRAL = '#94A3B8'
    _ids = sorted(x["cluster_id"] for x in clusters)
    _cidx = {cid: i % len(_PAL) for i, cid in enumerate(_ids)}
    _maxpct = max((x.get("pct") or 0) for x in clusters) or 1.0

    # ── 主题卡 + 主题总览 ──
    # 为什么这么改：12 张卡各自平铺 ~12 个 chip，手机上折行极多、一屏放不下，
    # 也看不出"有几个主题、哪几个大"。改为：卡前先放一张「主题总览」表一屏扫完；
    # 卡内只留 3 个代表词，其余收进默认收起的 <details>。
    # 口径不变：size/pct/year_range/语种判定与关键词来源（kw_top→top_terms）全部沿用。
    # 顺序显式按篇数降序（cluster_topics.py 已如此排，这里表意化），
    # 使「总览行号 = 卡片 id(#topic-N) = 画布色」三者对齐。
    _ordered = sorted(clusters, key=lambda x: -(x.get("size") or 0))
    # ── 主题名全局去重（v1.0.0）──
    # 实测：主题 11/12/13/14 名称完全一样、关键词不一样 —— 兜底命名对多簇
    # 取到了同一个最特征词。两遍法：先给全部簇取原始名，再按「区分性关键词」
    # 拉开（dedupe_labels），绝不允许报告里出现同名主题。
    _names_raw, _terms_all = [], []
    for _c0 in _ordered:
        _kw0 = ([w for w in (_c0.get("kw_top") or []) if w]
                or [t for t in (_c0.get("top_terms") or []) if t])
        # 非主题检测必须用**纯 top_terms**：label_topic 收到 kw_top+top_terms
        # 混合池时，kw_top 打头会把 MeSH 人口词稀释到阈值以下——实测主题 13
        # （humans/female/male/adult 为主）因此漏判、拼出了「工作成瘾、工作
        # 满意度与工作投入研究」这种假主题名。
        _nt0 = detect_non_topic(list(_c0.get("top_terms") or []))
        if _nt0:
            _n0, _s0 = _nt0, "non_topic"
        else:
            _n0, _s0 = label_topic(_kw0 + list(_c0.get("top_terms") or []))
        _names_raw.append(_n0)
        # 区分词池把「真实关键词 kw_top」放前、「分词 top_terms」放后：
        # dedupe_labels 取第一个可用词，放前才能保证挑到「员工创新行为」
        # 而不是 top_terms 里的泛词碎片（员工/management/work）。
        _terms_all.append(_kw0 + list(_c0.get("top_terms") or []))
    # 概念概括名的跨簇消歧（v1.0.0）：两名共享 ≥2 个概念 → 后者换独有概念
    # 重组，修「工作满意度、工作投入与工作重塑」/「工作成瘾、工作满意度与
    # 工作投入」这类排列组合式近名。
    _names_final = disambiguate_concept_names(_names_raw, _terms_all)
    _names_final = dedupe_labels(_names_final, _terms_all)
    _name_by_id = {c["cluster_id"]: _names_final[i]
                   for i, c in enumerate(_ordered)}
    cards, tov_rows = [], []
    for _tno, c in enumerate(_ordered, 1):
        z, e = c["lang_zh"], c["lang_en"]
        tot = z + e or 1
        rp = z / tot
        if rp == 0 or rp == 1:
            cls = "zh" if rp > .5 else "en"
            lbl = "中文" if rp > .5 else "英文"
        else:
            cls, lbl = "mixed", "跨语"
        # 关键词展示：优先「真实关键词」（完整短语），无关键词的簇回落分词结果。
        # 这修掉了「下方关键词大部分是 2 个字」—— 那些是 jieba 切碎的片段
        # （「组织」「工作」「数字」），不是文献真正标注的关键词。
        _kw = [w for w in (c.get("kw_top") or []) if w]
        _src = "keyword"
        if len(_kw) < 3:
            _kw = [t for t in (c.get("top_terms") or []) if t]
            _src = "term"
        # 代表词 = 主题内权重最高的 3 个。kw_top 来自 most_common（频次降序）、
        # top_terms 来自 TF-IDF 降序（见 cluster_topics.py），列表头部即权重最高，
        # 故取前 3 即「权重最高」，无需另算权重；展示上限仍沿用改动前的 12。
        _shown = _kw[:12]
        _rep, _tail = _shown[:3], _shown[3:]
        yr = c.get("year_range")
        tname, tsrc = label_topic(_kw + list(c.get("top_terms") or []))
        is_nt = (tname == NON_TOPIC_KEY)
        shown = (_name_by_id.get(c["cluster_id"]) or tname
                 or f"主题 {c['cluster_id']}")
        col = _PAL[_cidx[c["cluster_id"]]]
        pct = c.get("pct") or 0
        # 百分比条：宽度按「占最大主题的比例」归一，颜色=该主题在画布上的颜色。
        # 不能写死单一色值并按同一系数缩放，否则读者分不出主题优先级。
        barw = min(100.0, (pct / _maxpct) * 100.0)
        head = shown if shown else f"主题 {c['cluster_id']}"
        kw_note = ('' if _src == 'keyword' else
                   '<span class="hintline">（该主题含关键词的文献不足，以下为分词高频词）</span>')
        # 代表词（强调样式）与长尾词（弱化样式）分两级，长尾词收进默认收起的折叠面板。
        _rep_html = "".join(
            f'<span class="chip chiprep" title="该主题内 {esc(t)} 的出现篇数">{esc(t)}</span>'
            for t in _rep)
        _tail_html = "".join(
            f'<span class="chip chiptail" title="该主题内 {esc(t)} 的出现篇数">{esc(t)}</span>'
            for t in _tail)
        _tail_block = (f'<details class="tfold"><summary>展开全部关键词（{len(_shown)}）</summary>'
                       f'<div class="chips ctail">{_tail_html}</div></details>') if _tail else ''
        cards.append(f"""<div class="card tcard" id="topic-{_tno}" style="--tc:{col}">
<div class="tname"><span class="tdot" style="background:{col}"></span>{esc(head)}</div>
<div class="tmeta">
 <span class="tag {cls}">{lbl}</span>
 <span class="tag" style="background:var(--w2);color:var(--ink-2)">{c['size']} 篇</span>
 <span class="tag" style="background:var(--w2);color:var(--ink-2)">{yr[0]}–{yr[1]}</span>
 {('<span class="tag" style="background:var(--w2);color:var(--ink-2)">非研究主题</span>') if is_nt else ''}
</div>
<div class="pbar" title="占全库 {pct}%（相对最大主题 {barw:.0f}%）">
 <i style="width:{barw:.1f}%;background:{col}"></i><b style="color:{col}">{pct}%</b></div>
<div class="chipnote">主题关键词{kw_note}</div>
<div class="chips crep">{_rep_html}</div>
{_tail_block}</div>""")
        # 总览行：色点/编号/主题名（锚点跳卡片）、篇数、占比条+数字、年份、代表词、语种。
        # 色点与占比条颜色 = col，与卡片、画布节点、图例同源。
        tov_rows.append(
            f'<tr><td><a class="tovlink" href="#topic-{_tno}">'
            f'<span class="tdot" style="background:{col}"></span>'
            f'<span class="tovn">{_tno:02d}</span>'
            f'<span class="tovw" title="{esc(head)}">{esc(head)}</span></a></td>'
            f'<td class="num">{c["size"]}</td>'
            f'<td class="num"><span class="tovb"><i style="width:{barw:.1f}%;background:{col}"></i></span>'
            f'<span class="tovp">{pct}%</span></td>'
            f'<td class="num">{yr[0]}–{yr[1]}</td>'
            f'<td class="tovkw">{"、".join(esc(t) for t in _rep)}{"…" if _tail else ""}</td>'
            f'<td class="ctr"><span class="tag tovlang {cls}">{lbl}</span>'
            f'{" 非研究主题" if is_nt else ""}</td></tr>')

    # 主题总览表：一屏看清全部主题（规模/占比/年份/代表词/语种），
    # 主题名可点击跳到下方对应主题卡（卡片已加 id="topic-N"）。
    # 用 class="mx cols-auto" —— 结尾的 _wrap_tables() 会自动套 .tw
    # （overflow-x:auto），窄屏只有表格自身滚动，绝不撑宽整页。
    topic_overview = ""
    if cards:
        topic_overview = (
            '<div class="tovcap">主题总览'
            ' <span class="hintline">按篇数降序 · 点主题名跳到下方对应主题卡</span></div>'
            '<table class="mx cols-auto tov"><thead><tr>'
            '<th>主题</th><th class="num">篇数</th><th class="num">占比</th>'
            '<th class="num">年份</th><th>代表关键词</th><th class="ctr">语种</th>'
            f'</tr></thead><tbody>{"".join(tov_rows)}</tbody></table>')


    # ── 演化矩阵 ──
    matrix_html = ""
    # 目录在所有章节 html 就绪后再生成（见文件末尾）
    timeline_html = _timeline_html(kw_net, bursts)
    pub_html = _pubstats_html(pub)
    cross_html = _cross_html(cross)
    summary_html = _summary_html(d, clusters, kw_net, bursts)

    if evolution:
        years = [y for y in evolution.get("years", [])]
        cl = evolution.get("clusters", [])
        keep_years = [y for y in years if y >= max(1968, cov["year_min"])]
        if len(keep_years) > 42:
            keep_years = [y for y in years if y >= max(1970, years[-1] - 32)]
        mx = {c["cluster_id"]: c["counts"] for c in cl}
        vmax = max((mx.get(c["cluster_id"], {}).get(str(y), 0)
                    for c in clusters for y in keep_years), default=1) or 1
        # 行标签必须是**主题名**。此前只印 cluster_id（0/1/2…），
        # 读者对着一列数字编号完全不知道是哪几个主题，热力图等于白画。
        _cmap2 = {c["cluster_id"]: c for c in clusters}
        hdr = "".join(f"<th>{y}</th>" for y in keep_years)
        rows = []
        _labels = []                 # 行标签名，用于估算首列宽度
        for c in clusters:
            _c = _cmap2.get(c["cluster_id"]) or {}
            _nm, _ = label_topic([w for w in (_c.get("kw_top") or [])]
                                 + list(_c.get("top_terms") or []))
            _nm = _nm or f"主题 {c['cluster_id']}"
            _labels.append(_nm)
            tds = []
            for y in keep_years:
                v = mx.get(c["cluster_id"], {}).get(str(y), 0)
                a = (v / vmax) ** .6 if v else 0
                bg = f"rgba(79,70,229,{a:.3f})" if v else "transparent"
                tds.append(f'<td class="hm" style="background:{bg}" '
                           f'title="{esc(_nm)} · {y} 年：{v} 篇">{v or ""}</td>')
            rows.append(f'<tr><th class="hmrow">{esc(_nm)}</th>'
                        f'{"".join(tds)}</tr>')
        # fixed 布局 + colgroup：首列(主题名)固定像素宽、年份列均分剩余宽度。
        # 首列宽取「主题名 + 表头『主题 \ 年份』」中较长者，避免表头被截断。
        _lab_px = _label_col_px(_labels + ["主题 \\ 年份"])
        _cg = _mx_colgroup(len(keep_years), _lab_px)
        _minw = _mx_minw(_lab_px, len(keep_years), 40)
        # [!] 这里曾写成 Markdown 的 `**重点**`，但产物是 HTML ——
        #   页面上会原样显示两个星号。正文里的强调一律用 <b>。
        matrix_html = f"""<h2 id="s03"><span class="n">04</span>主题 × 年份演化</h2>
<p class="note">行 = 研究主题，列 = 年份，单元格的深浅与数字 = 该主题当年的文献数。
用于判断每个主题是<b>正在升温、平稳延续</b>，还是<b>已经退场</b>。</p>
<div class="card hmcard">
<div class="figbar">
<button class="fbtn" type="button" data-fig="heatmap" data-save="png" data-name="主题年份热力图" title="把这张热力图保存为 PNG（用 canvas 重绘，非截图）">保存 PNG</button>
</div>
<table class="mx hmtable" style="min-width:{_minw}px">{_cg}<thead><tr>
<th class="hmrow">主题 \\ 年份</th>{hdr}</tr></thead><tbody>
{''.join(rows)}</tbody></table>
<div class="hmlegend"><span>少</span><i class="hmbar"></i><span>多</span>
<span class="hintline">颜色 = 相对最大值（{vmax} 篇）的强度；
早年样本量偏小，趋势解读需谨慎。</span></div>
</div>"""

    # ── 网络数据 ──
    net_js = ""
    net_card = ""
    if network:
        N, E = network["nodes"], network["edges"]
        attr = network.get("stats", {}).get("topic_attribution", {})
        cmeta = dict(network.get("cluster_meta", {}) or {})
        themed = bool(attr.get("enabled"))
        # [!] 前端需要主题名来显示"该关键词属于哪个主题"（侧栏与提示都要用）。
        #此前 cmeta 里只有 id/颜色，主题名只存在于 HTML 卡片里，前端取不到。
        try:
            _cmeta_by_id = {c.get("cluster_id"): c for c in clusters}
            for _cid, _cm in cmeta.items():
                _c = _cmeta_by_id.get(_cid) or _cmeta_by_id.get(int(_cid)
                                if str(_cid).isdigit() else None)
                if not _c:
                    continue
                _nm, _ = label_topic(_c.get("top_terms", []))
                if _nm and _nm != NON_TOPIC_KEY:
                    _cm["label"] = _nm
        except Exception:  # noqa: BLE001
            pass          # 命名失败不影响图，只是侧栏少了主题名

        top = sorted(N, key=lambda x: -x["degree"])[:24]
        # 关键词按连接数分三档字号：一眼看出哪些是枢纽词、哪些是长尾。
        # 全部同字号 + 括号数字时，40 个词排在一起看不出主次。
        _dmax = max([n.get("degree") or 0 for n in top] or [1]) or 1
        def _kw_tier(n):
            r = (n.get("degree") or 0) / _dmax
            return "t1" if r >= 0.66 else ("t2" if r >= 0.33 else "t3")
        # 按档位分组渲染：每档一行，行间有标题（"枢纽词/常用词/长尾词"）。
        # 此前 40 个词平铺成一段连排，读者分不出主次（实测"工作重塑51 护士13
        # 创新行为7…"挤成一团）。
        _tiers = [("t1", "枢纽词", "连接数最高，是网络骨架"),
                  ("t2", "常用词", "中间层，连接数中等"),
                  ("t3", "长尾词", "仅 1–2 条连接，多为专有名词")]
        # 关键词区重设计：每一档是**独立卡片**，档内用自适应网格排列。
        # 若把 40 个词按档位挤进三行 flex，档内词数一多就视觉拥挤、
        # 密度不均。现在每档独立成块，档内 grid 自动均分宽度。
        _rows_html = []
        for _cls, _lab, _hint in _tiers:
            _items = [n for n in top if _kw_tier(n) == _cls]
            if not _items:
                continue
            _cells = "".join(
                f'<button type="button" class="kwcell {_cls}" '
                f'data-off="{esc(n["id"])}" '
                f'title="{esc(str(n["id"]))}｜连接数 {n.get("degree", 0)}'
                f'｜点击可灰显/恢复">'
                f'<span class="kt">{esc(n["id"])}</span>'
                f'<span class="kd">{n.get("degree", 0)}</span></button>'
                for n in _items)
            _rows_html.append(
                f'<div class="kwgroup"><div class="kwhead">'
                f'<span class="kwtitle">{_lab}</span>'
                f'<span class="kwcount">{len(_items)} 个</span>'
                f'<span class="kwhint">{_hint}</span></div>'
                f'<div class="kwgrid">{_cells}</div></div>')
        chips = "".join(_rows_html)

        # 图例：每个主题一个可点击色块，括号内是该主题的关键词数
        if themed:
            cnt = Counter(n.get("primary_cluster") for n in N
                          if n.get("primary_cluster") is not None)
            lg_items, lg_js = [], []
            for cid in sorted(cnt, key=lambda c: -cnt[c]):
                m = cmeta.get(str(cid), cmeta.get(cid, {})) or {}
                terms = "、".join((m.get("top_terms") or [])[:3])
                # 主题名后并列两个裸数字（如「主题1 57」——编号与词数）读者无从分辨，
                # 第二个数字必须带自解释量词「个词」，
                # 并在区块顶部加一行说明两者各是什么（取值口径不变，只补标签）。
                lg_items.append(
                    f'<span class="lg-item" data-cid="{cid}" title="{esc(terms)}">'
                    f'<span class="sw" data-sw="{cid}"></span>'
                    f'主题{cid}<span class="n">{cnt[cid]} 个词</span></span>')
                lg_js.append({"c": cid, "n": cnt[cid]})
            none_cnt = sum(1 for n in N if n.get("primary_cluster") is None)
            if none_cnt:
                lg_items.append(
                    f'<span class="lg-item" data-cid="__none__">'
                    f'<span class="sw" style="background:{_NEUTRAL}"></span>'
                    f'未归属<span class="n">{none_cnt} 个词</span></span>')
            legend_html = "".join(lg_items)

            attr_note = (
                f'<div style="font-size:12px;color:var(--ink-2);margin-top:8px">'
                f'主题归属：纯单簇 {attr.get("single_cluster", 0)} 个'
                f'（{attr.get("single_pct", 0)}%）· '
                f'跨簇 {attr.get("multi_cluster", 0)} 个'
                f'（{attr.get("multi_pct", 0)}%）· '
                f'未归属 {attr.get("unattributed", 0)} 个。'
                f'<b>带描边的节点</b>是桥接词（主簇占比 &lt; '
                f'{attr.get("bridge_threshold", 0.5):.0%}，'
                f'共 {attr.get("bridge", 0)} 个）——它们连接多个主题，'
                f'是跨主题研究的枢纽。</div>')
        else:
            legend_html = ""
            attr_note = ('<div style="font-size:12px;color:#8a6d3b;margin-top:8px">'
                         '[!]  未接入主题聚类（build_network.py 未传 --topics），'
                         '节点无主题归属，故全部同色。</div>')
            lg_js = []

        # 传 JS 的字段做瘦身：只给渲染真正用到的，减少内联体积
        slim = [{"id": n["id"], "df": n["df"], "degree": n["degree"],
                 "weight": n.get("weight", 0),
                 "pc": n.get("primary_cluster"),
                 "ps": n.get("primary_share", 0),
                 "ci": n.get("cluster_ids", []),
                 "br": bool(n.get("is_bridge"))}
                for n in N]
        edges_slim = [{"s": e["source"], "t": e["target"], "w": e["weight"]}
                      for e in E]
        # 图例年份范围 + 把主题×年份分布注入 cluster_meta。
        # 注意（两处）：
        #  1) cluster_meta 原本只有 size/pct/top_terms，**没有 counts**；
        #  2) topics.json 的 cluster 也**没有 counts**（只有 year_range 起止年）——
        #     逐年分布在 **evolution.json** 的 clusters[].counts 里。
        # 早先版本两处都取错 → yearColor 全拿不到值，时间叠加视图整片灰掉，
        # 看着像功能坏了。故此处从 evolution 取数，使 JS 与 Python 两侧同口径。
        evo_counts = {}
        if evolution:
            for ce in evolution.get("clusters", []) or []:
                evo_counts[str(ce.get("cluster_id"))] = ce.get("counts", {}) or {}
        for c_ in clusters:
            cid_ = str(c_["cluster_id"])
            if cid_ in cmeta and "counts" not in cmeta[cid_]:
                cmeta[cid_]["counts"] = evo_counts.get(cid_, {})
        yr_lo = yr_hi = None
        for cnts in evo_counts.values():
            for y_ in cnts:
                yy = int(y_)
                yr_lo = yy if yr_lo is None else min(yr_lo, yy)
                yr_hi = yy if yr_hi is None else max(yr_hi, yy)
        payload = {"nodes": slim, "edges": edges_slim}
        pe = network.get("pos_encoded")
        if pe and pe.get("pos_b64"):
            # 坐标走 base64 int16 内联，体积约 5.8KB/1094 节点，
            # 换取跳过首屏 O(n²) FR —— 不把 x/y 明文写进 JSON（那会大一个量级）
            payload["pos_encoded"] = pe
        # [!]  安全：文献标题/关键词/作者均来自外部导入（不可信输入）。
        # 若用裸 json.dumps 内联，题名中的 "</script>" 可提前闭合 <script> 标签
        # → 任意脚本注入。esc_json 转义 < > & 与 U+2028/9 封死该路径。
        net_js = (
            f"window.__NET__={esc_json(payload)};"
            f"window.__CMETA__={esc_json({str(k): v for k, v in (cmeta or {}).items()})};"
            f"window.__CPAL__={esc_json(lg_js)};"
            f"window.__KW__={esc_json(kw_net)};")

        # ── 主题 ↔ Top 关键词 对照（置于画布**之上**）──
        # 主题与关键词必须建立显式链接——画布上的色块若无文字对照，读者只能靠猜。
        # 这里把「主题N（颜色）
        # = 该主题的 top 关键词」直接写在画布上方，并支持点击聚焦该主题。
        # 同时把长尾词（低连接数）也放在上方，让读者先建立"有哪些词"的认知，
        # 再去看网络结构 —— 这正是「文字在上、画布在下」的用意。
        _cmap = dict((c["cluster_id"], c) for c in clusters)
        _tm_items = []
        for _cid in sorted({n.get("primary_cluster") for n in N
                            if n.get("primary_cluster") is not None}):
            _col = _PAL[_cidx.get(_cid, 0)]
            _c = _cmap.get(_cid) or dict()
            _kw = [w for w in (_c.get("kw_top") or []) if w]
            if len(_kw) < 3:
                # 回落顺序必须与「研究主题」卡内的关键词一致：
                # kw_top（真实关键词）→ 该簇 top_terms（分词高频词）→ cmeta。
                # 此前这里直接跳到 cmeta，而 cmeta 多数情况下不存在，
                # 于是对照条写着「该主题暂无关键词」，可点进去网络里明明有词 ——
                # 标签与事实不符。三处必须同源。
                _kw = [t for t in (_c.get("top_terms") or []) if t]
            if len(_kw) < 3:
                _m = cmeta.get(str(_cid), cmeta.get(_cid, dict())) or dict()
                _kw = [t for t in (_m.get("top_terms") or []) if t]
            _nm, _ = label_topic([w for w in (_c.get("kw_top") or [])]
                                 + list(_c.get("top_terms") or []))
            _nm = _nm or ("主题 " + str(_cid))
            _nkw = sum(1 for n in N if n.get("primary_cluster") == _cid)
            _kwtxt = "、".join(_kw[:10]) if _kw else "（该主题暂无关键词）"
            _tm_items.append(
                f'<button type="button" class="tmap-item" data-cid="{_cid}" '
                f'title="点击只看该主题（再点一次取消）">'
                f'<span class="tmk" style="background:{_col}"></span>'
                f'<span><span class="tmid">主题{_cid} · {_nkw} 个词</span>'
                f'<span class="tmn">{esc(_nm)}</span>'
                f'<span class="tmk2">{esc(_kwtxt)}</span></span></button>')
        _none_cnt2 = sum(1 for n in N if n.get("primary_cluster") is None)
        if _none_cnt2:
            _tm_items.append(
                f'<span class="tmap-item" style="cursor:default">'
                f'<span class="tmk" style="background:{_NEUTRAL}"></span>'
                f'<span><span class="tmid">未归属 · {_none_cnt2} 个词</span>'
                f'<span class="tmk2">未通过主题归属阈值的边缘词</span></span></span>')
        topicmap_html = "".join(_tm_items)

        net_card = f"""<div class="card netcard">
<div class="nsec">
<h4 class="nsec-h">视图与导出
 <span class="hintline">着色方式、图法、连线与节点微调、导出图片</span></h4>
<div class="figbar">
<button id="exportPNG" class="fbtn" type="button" data-fig="kwnet" data-save="png" data-name="关键词共现网络" title="按当前视口导出 2x 高清 PNG（白底，可直接投稿）">保存此图</button>
<button id="exportSVG" class="fbtn" type="button" data-fig="kwnet" data-save="svg" data-name="关键词共现网络" title="导出矢量 SVG（仅节点与标签，文件小、可无限放大）">保存 SVG</button>
</div>
<div class="ctrl-live"><span id="tinfo"></span>
<span class="perf" id="perf"></span></div>
<details class="fold">
<summary><span class="foldh-lbl">调整视图与图法</span>
 <span class="foldh-val" id="viewSummary">按主题着色 · 曲线 · 线宽 38 · 节点 100</span></summary>
<span class="toolbar">
<span class="viewlbl">着色：</span><button class="viewbtn on" data-view="topic" type="button" title="按研究主题着色，每个主题一个颜色（快捷键 1）">按主题</button><button class="viewbtn" data-view="overlay" type="button" title="按平均发表年着色，青=早 靛=中 品红=晚（快捷键 2）">按年份</button><span class="viewlbl">图法：</span><button class="viewbtn" data-view="density" type="button" title="密度图：按关键词聚集程度着色（青→靛→品红，越深越密），底部附色标（快捷键 3）">密度图</button><button class="viewbtn" data-view="yearring" type="button" title="时间线图（CiteSpace 风格）：纵轴为聚类、横轴为发表年份，节点落在 (聚类, 首现年份) 交点，颜色由青到品红表示由早到晚（快捷键 4）">时间线</button><span class="viewlbl">调节：</span>
<label class="viewtune" title="画布配色">画布
<select id="canvasTheme">
<option value="light" selected>浅色</option>
<option value="dark">深色</option>
</select></label><label class="viewtune" title="连接线样式">连线
<select id="edgeStyle">
<option value="line">直线</option>
<option value="curve" selected>曲线</option>
</select></label>
<label class="viewtune" title="拖动调整连接线的粗细">线宽<input id="edgeW" type="range" min="0" max="100" value="38"></label><label class="viewtune" title="拖动调整节点大小">节点<input id="nodeS" type="range" min="60" max="220" value="100"></label>
</span>
</details>
</div><!-- /nsec 1 -->

<div class="nsec">
<h4 class="nsec-h">主题分布
 <span class="hintline">颜色与画布上的节点完全一致；点击任一主题即可只看该主题（再点一次取消）</span></h4>
<p class="hintline" style="margin:0 0 8px">每项两段数字的含义：<b>「主题 N」的 N = 主题编号</b>（与画布、卡片、下表一致）；<b>后面徽标里的数 = 该主题包含的关键词个数</b>。</p>
<div class="lg" id="legendArea">{legend_html}</div>
<div class="lg" id="overlayLegend" style="display:none">
<span class="lgcap">平均发表年</span>
<span class="yrbar"></span>
<span class="yrlab">{yr_lo if yr_lo is not None else '—'}</span>
<span class="lgcap">→</span>
<span class="yrlab">{yr_hi if yr_hi is not None else '—'}</span>
<span class="lgcap">（青=早期概念，品红=近期概念；口径为所属主题的年份重心近似）</span>
<span id="overlayWarn" class="lgwarn">{'' if yr_lo is not None else '[!]  未接入演化数据（缺 --evolution），无法按年着色'}</span>
</div>
<details class="fold" style="margin-top:8px">
<summary><span class="foldh-lbl">主题 ↔ Top 关键词对照</span>
 <span class="foldh-val">点开可只看某主题</span></summary>
<div class="topicmap">{topicmap_html}</div>
</details>
</div><!-- /nsec 2 -->

<details class="nsec">
<summary class="nsec-h">关键词全景（含长尾词）
 <span class="hintline">按连接数分档 · 数字为连接数 · 点击可灰显 / 恢复</span></summary>
<div class="kwcloud" id="kwcloud">{chips}</div>
<div class="legend"><span>节点大小 = 连接数</span>
<span><span class="dot" style="background:{_NEUTRAL}"></span>未归属主题</span>
<span>描边 = 桥接词（横跨多个主题）</span>
<span>浅灰连线 = 跨主题边</span></div>
</details><!-- /nsec 3 -->

<div class="nsec nsec-canvas">
<h4 class="nsec-h">共现网络
 <span class="hintline">可用上方折叠面板切换「按主题 / 按年份 / 密度图 / 时间线」四种图法</span></h4>
<div class="net-canvas">
<div class="canvaswrap">
<canvas id="net"></canvas>
<div class="overlay-ui top" id="ovTop"></div>
<div class="overlay-ui bottom">
    <div class="keys">
    <span class="touchnote"><b>单指拖</b> 平移 · <b>拖节点</b> 微调 ·
    <b>点节点</b> 高亮邻居 · <b>双指</b> 缩放 · <b>双击</b> 复位</span>
    <span class="kbdonly"><b>Ctrl/⌘+滚轮</b> 缩放 · <b>拖空白</b> 平移 ·
    <b>拖节点</b> 微调 · <b>点击</b> 高亮邻居 · <b>Ctrl/⌘+双击</b> 复位视口 ·
    <b>R</b> 复位节点 · <b>Esc</b> 取消选中 · <b>1/2/3/4</b> 切换视图</span>
  </div>
</div>
<!-- 密度视图竖向色标：仅密度视图显示（JS 切视图时 toggle），
     放在画布右侧独立条带，不参与 .overlay-ui，避免与底部提示争位、压图。 -->
<div class="dens-legend" id="densLegend" aria-hidden="true" style="display:none">
  <span class="dl-top">密</span>
  <span class="dl-bar" id="densLegendBar"></span>
  <span class="dl-bot">疏</span>
  <span class="dl-cap">关键词密度</span>
</div>
</div><!-- /canvaswrap -->
{attr_note}
</div><!-- /net-canvas -->
</div><!-- /nsec 4 -->

<div class="nsec">
<h4 class="nsec-h">操作与选中详情</h4>
<div class="net-foot">
  <div class="side"><h4 id="sidehead">怎么看这张图</h4>
  <div class="kws" id="side"></div></div>
  <div class="netrow" style="margin-top:8px">
  <span class="hintline">按度数排序的关键词（点击可灰显 / 恢复）</span>
  <button id="resetLayout" class="rstbtn" type="button"
   title="清除所有手动拖动的节点位置，回到算法原始布局">复位节点位置</button></div>
</div>
</div><!-- /nsec 5 -->
</div>"""

    # ── 作者共现网络（可选，build_author_network.py 产物）──
    # 独立画布：与关键词网络语义不同（节点=作者、边=同篇合作），故不共用 viewMode，
    # 避免两套语义（主题着色/桥接/侧栏）互相污染、也避免踩坏既有交互。
    # [!]  硬规则：没有内容就返回空串。_collect_present_sections 靠"产物本身"
    #   判断章节是否存在（见该函数注释里记录过的 s03 空白死链坑）——
    #   若在这里无条件渲染，目录会出现一个点进去空白的「作者共现网络」。
    authnet_html = ""
    authnet_js = ""
    if auth_net:
        _an_node = auth_net.get("nodes") or []
        _an_edge = auth_net.get("edges") or []
        _an_stats = auth_net.get("stats") or {}
        # 节点或边任一为空 → 视为无内容，整节略去（不进目录）
        if _an_node and _an_edge:
            mn = _an_stats.get("nodes", len(_an_node))
            me = _an_stats.get("edges", len(_an_edge))
            lc = _an_stats.get("largest_component", "—")
            lcp = _an_stats.get("largest_component_pct", "—")
            dens = _an_stats.get("density", "—")
            iso = _an_stats.get("isolated", 0)
            mg = (_an_stats.get("merge") or {}).get("merged_groups", 0)
            par = _an_stats.get("params") or {}
            akpi = "".join(
                f'<div class="kpi"><div class="l">{esc(l)}</div>'
                f'<div class="v">{esc(v)}</div></div>'
                for l, v in [
                    ("作者数（节点）", f"{mn:,}"),
                    ("合作关系（边）", f"{me:,}"),
                    ("最大合作团队", f"{lc}（{lcp}%）"),
                    ("网络密度", f"{dens}"),
                ])
            # 传 JS 的瘦身载荷：只给渲染真正用到的字段
            # component/component_size：合作群（连通分量）着色用。旧产物无此字段 →
            # .get 返回 None → JSON 里是 null → AUTH_JS 用并查集自算兜底，不退化为单色。
            an_slim = [{"id": n.get("id"), "df": n.get("df", 0),
                        "degree": n.get("degree", 0), "weight": n.get("weight", 0),
                        "isolated": bool(n.get("isolated")),
                        "component": n.get("component"),
                        "component_size": n.get("component_size"),
                        "x": n.get("x"), "y": n.get("y")} for n in _an_node]
            an_edges = [{"s": e.get("source"), "t": e.get("target"),
                         "w": e.get("weight", 1)} for e in _an_edge]
            an_payload = {"nodes": an_slim, "edges": an_edges}
            # 坐标走 base64 int16 内联（与关键词画布同一契约），省掉首屏现场布局
            if (auth_net.get("pos_encoded") or {}).get("pos_b64"):
                an_payload["pos_encoded"] = auth_net["pos_encoded"]
            # esc_json：作者名来自外部导入（CNKI/WoS），属不可信输入，
            # 裸 json.dumps 内联会被 "</script>" 提前闭合 <script> → 必须转义
            # 作者网络主题色：与机构/引文三类**互相区分**。取 _PAL[0] 品牌青，
            # 用于 HTML 侧 --net-c（标题竖条/KPI/按钮）。注意：节点底色**不再**用这个
            # 单色，而是由 AUTH_JS 的 colorOf 按节点 component 取色（同色 = 同一合作群），
            # 主题色只作本节强调色，与节点颜色语义已分离。
            _auth_color = _PAL[0]
            authnet_js = (f"window.__AUTHNET_COLOR__={esc_json(_auth_color)};"
                          f"window.__AUTHNET__={esc_json(an_payload)};")
            merge_note = (f'名字归一合并了 {mg} 组同义写法；' if mg else '')
            # 合作群数量 & 调色板色数：图例据此如实说明"颜色有限时会循环复用"；
            # 孤立作者剔除数一并交代（数据侧默认剔除，不能让读者对着节点数发懵）。
            ncomp = _an_stats.get("components", "—")
            ncolor = len(_PAL)
            _dropped = _an_stats.get("isolated_dropped", 0) or 0
            iso_note = (f"已剔除 {_dropped} 位孤立作者（本库内无合作者，未画入图中）；"
                        if _dropped else f"共 {iso} 位孤立作者（本库内无合作者）；")
            authnet_html = f"""<h2 id="s15"><span class="n">00</span>作者共现网络</h2>
<p class="note">节点 = 作者，边 = 两位作者<b>出现在同一篇文献</b>里（同篇共现一次算一条边，
权重 = 共同署名篇数）。用于识别核心作者与合作团队。<b>这与上方「关键词共现网络」是两种
不同的网络</b>：关键词网络回答「概念之间有什么关联」，作者网络回答「谁和谁合作」——
两者不可互相替代，本图也<b>不是</b>引文网络（数据源不含引文信息）。</p>
<div class="card netcard net-accent" style="--net-c:{_auth_color}">
<div class="nsec">
<h4 class="nsec-h">作者网络概览
 <span class="hintline">节点大小 ∝ 该作者出现篇数；连线越粗 = 合作篇数越多</span>
 <span class="net-key"><i class="dot"></i>合作群着色</span></h4>
<div class="figbar">
<button id="authExportPNG" class="fbtn" type="button" data-fig="authnet" data-save="png"
 data-name="作者共现网络" title="把当前作者网络保存为 2x 高清 PNG（白底，可直接投稿）">保存此图</button>
<button id="authExportSVG" class="fbtn" type="button" data-fig="authnet" data-save="svg"
 data-name="作者共现网络" title="导出矢量 SVG（可无限放大、可再编辑）">保存 SVG</button>
</div>
<div class="kpis">{akpi}</div>
<div class="ctrl-live"><span id="authInfo"></span></div>
<div class="netrow" style="margin-top:6px">
<span class="hintline">同色 = 同一合作群（作者与其合作者），按网络连通分量划分，共 {ncomp} 个合作群；调色板共 {ncolor} 色，合作群多于色数时颜色循环复用。{iso_note}{merge_note}口径：{esc(par.get('cooccurrence', ''))}，最少出现 {esc(par.get('min_docs', '?'))} 篇，边阈值 {esc(par.get('min_edge', '?'))}</span>
</div>
</div>
<div class="nsec nsec-canvas">
<div class="net-canvas">
<div class="canvaswrap" id="authCanvasWrap">
<canvas id="authnet"></canvas>
<div class="overlay-ui bottom"><div class="keys">
<span class="touchnote"><b>拖节点</b> 微调 · <b>拖空白</b> 平移 · <b>点节点</b> 高亮合作者 · <b>双击</b> 复位</span>
<span class="kbdonly"><b>Ctrl/⌘+滚轮</b> 缩放 · <b>拖节点</b> 微调 · <b>拖空白</b> 平移 · <b>双击</b> 复位视口</span>
</div></div>
</div>
</div>
</div>
</div>"""

    # ── 机构共现网络（可选，build_institution_network.py 产物）──
    # 与作者网络同样的硬规则：没有数据就不渲染（不进目录）；空态只给说明卡片。
    # 是否进目录由 _collect_present_sections 依据"是否真的渲染出内容"判定。
    _inst_intro = (
        "节点 = 机构，边 = 两个机构<b>出现在同一篇文献</b>里（同篇共现一次算一条边，"
        "权重 = 共同署名篇数）。用于识别跨机构合作关系。本图<b>不是</b>引文网络"
        "（数据源不含引文信息）。")
    instnet_html, instnet_js = _network_section(
        "s16", "机构共现网络", _inst_intro, inst_net,
        "__INSTNET__", "instnet",
        "本数据源不含机构（作者单位）字段，无法构建机构共现网络。",
        "要支持本图，导出文件需包含机构字段：RIS 的 AD / C1、WoS 的 C1、"
        "EndNote tagged 的 %+、NoteExpress 的 Author Address、CSV 的 Addresses / Affiliations。"
        "CNKI .enw/.enl 与 Zotero 导出通常不含机构。",
        "instnet", color=_PAL[2], ncolor=len(_PAL))   # 机构网络主题色 = 靛 #4F46E5

    # ── 引文网络（可选，build_citation_network.py 产物）──
    # 引文侧有两种**方向相反**的度量，标题与图注必须如实区分，不能含糊：
    #   共被引(co-citation)：两篇参考文献被同一篇施引文献同时引用 → 看被引端相似；
    #   文献耦合(coupling)：两篇施引文献共同引用同一批参考文献 → 看施引端相似。
    _cit_par = ((cit_net or {}).get("stats") or {}).get("params") or {}
    _cit_mode = _cit_par.get("mode") or ""
    _cit_type = (cit_net or {}).get("type") or ""
    _is_coupling = (_cit_mode == "coupling" or _cit_type == "bibliographic-coupling")
    if _is_coupling:
        _cit_title = "引文耦合网络"
        _cit_lead = "本数据源不含被引 / 参考文献字段，无法构建引文耦合网络。"
        _cit_way = "两篇<b>施引</b>文献共同引用同一批参考文献 → 看的是<b>施引端</b>相似。"
        _cit_kind = "文献耦合（bibliographic coupling）"
    else:
        _cit_title = "引文共被引网络"
        _cit_lead = "本数据源不含被引 / 参考文献字段，无法构建引文共被引网络。"
        _cit_way = "两篇<b>参考文献</b>被同一篇施引文献同时引用 → 看的是<b>被引端</b>相似。"
        _cit_kind = "共被引（co-citation）"
    _cit_intro = ("节点 = 参考文献，边 = 共现关系。<b>本图是「" + _cit_kind + "」</b>："
                  + _cit_way + "共被引与耦合方向相反，不可互相替代；本图也<b>不是</b>"
                  "关键词共现网络。")
    citnet_html, citnet_js = _network_section(
        "s17", _cit_title, _cit_intro, cit_net,
        "__CITNET__", "citnet", _cit_lead,
        "要支持本图，导出文件需包含被引 / 参考文献字段：WoS 的 CR（Cited References）、"
        "RIS 的 CR。CNKI 与 Zotero 导出通常不含被引（CiteSpace 官方 FAQ 亦确认 "
        "CNKI 无 cited references）。",
        "citnet", color=_PAL[5], ncolor=len(_PAL))   # 引文网络主题色 = 玫红 #E11D48（与作者青/机构靛区分）
    # 引文图的下载文件名要跟着模式走（共被引 / 耦合），故把标题也内联给前端。
    if citnet_js:
        citnet_js = f"window.__CITNET_NAME__={esc_json(_cit_title)};" + citnet_js

    # ── 三类网络"没有就不出现"，改在「数据体检」如实交代 ──
    # 判据与 _network_section 完全一致（data 缺失 / empty_state / nodes 或 edges 为空），
    # 保证"正文不出图"与"此处说明"永远同步，不会出现"图没了却没说为什么"。
    def _net_missing(_data):
        return (not _data) or bool(_data.get("empty_state")) \
            or not (_data.get("nodes") and _data.get("edges"))

    _net_notes = []
    if _net_missing(auth_net):
        _net_notes.append("作者共现网络：本数据源不含可用的作者字段，故未生成作者共现网络。")
    for _nt, _nd, _ndef in (
            ("机构共现网络", inst_net,
             "本数据源不含机构（作者单位）字段，故未生成机构共现网络。"),
            (_cit_title, cit_net,
             "本数据源不含被引 / 参考文献字段，故未生成引文网络。")):
        if _net_missing(_nd):
            # 优先用产物自带的 notice（它可能写明"500 篇中 0 篇含该字段"等真实计数），
            # 没有才回落到口径固定的默认说明 —— 数字一律来自产物，不编造。
            _nn = ((_nd or {}).get("notice") or "").strip()
            _net_notes.append(_nt + "：" + (_nn or _ndef))
    net_notes_html = ""
    if _net_notes:
        net_notes_html = (
            '<p class="note" style="margin:12px 0 0">'
            '<b>未生成的关系网络（数据源不含相应字段）</b></p>'
            '<ul style="margin:2px 0 0;font-size:13px;color:var(--ink-2)">'
            + "".join(f"<li>{esc(x)}</li>" for x in _net_notes) + "</ul>")

    # ── R / igraph 交叉验证（sna_r.py 产物；R 为标准路径）──
    if sna:
        backend = sna.get("backend", "?")
        is_r = backend == "R"
        badge = ('<span class="tag" style="background:#0a7d33;color:#fff">R 实际路径</span>'
                 if is_r else
                 '<span class="tag" style="background:#8a7320;color:#fff">纯 Python 兜底</span>')
        ver = ""
        if is_r:
            ver = (f"R {esc(str(sna.get('r_version', ''))[:40])} · "
                   f"igraph {esc(str(sna.get('igraph_version', ''))[:20])}")
        else:
            ver = esc(str(sna.get("reason", ""))[:120])
        ncomm = len(sna.get("communities") or [])
        kpi_s = [("后端", "R" if is_r else "Python 兜底"),
                 ("模块度 Q", f"{sna.get('modularity')}" if sna.get("modularity") is not None else "—"),
                 ("社群数", f"{ncomm}"),
                 ("边密度", f"{sna.get('density')}" if sna.get("density") is not None else "—")]
        kpi_s_html = "".join(
            f'<div class="kpi"><div class="l">{esc(l)}</div><div class="v">{esc(v)}</div></div>'
            for l, v in kpi_s)
        rows = []
        # 循环变量不可命名为 d：外层 d 指向 topics，遮蔽会导致 footer 读取失败。
        # 对齐规范：关键词=文本列（左），四个中心性=数值列（右）。th 与 td 必须同对齐，
        # 否则表头与数据错位（表头居中而数据右对齐即属此类）。
        for nd_ in (sna.get("top_central") or [])[:12]:
            rows.append(
                f"<tr><td>{esc(str(nd_.get('node','')))}</td>"
                f"<td class='num'>{esc(str(nd_.get('degree','')))}</td>"
                f"<td class='num'>{esc(str(nd_.get('betweenness','')))}</td>"
                f"<td class='num'>{esc(str(nd_.get('closeness','')))}</td>"
                f"<td class='num'>{esc(str(nd_.get('eigen','')))}</td></tr>")
        tbl = ("<table class='mx'><tr><th>关键词</th>"
               "<th class='num'>度</th><th class='num'>介数</th>"
               "<th class='num'>接近</th><th class='num'>特征向量</th></tr>"
               + "".join(rows) + "</table>") if rows else ""
        cv = sna.get("cross_validation") or {}
        ari, nmi = cv.get("ari_vs_nmf"), cv.get("nmi_vs_nmf")
        if is_r and ari is not None:
            def _f(x):
                return f"{x:.3f}" if isinstance(x, (int, float)) else "—"
            # [!] 这句此前写成 Markdown 的 **强调**，但产物是 HTML —— 页面上会
            #   原样露出两个星号。修的时候注意：不能只把 `**` 换成 <b>，因为下面
            #   的 esc(judge) 会把 <b> 一并转义成可见字符。正确的切分是——
            #   硬编码字面量（无注入面）直接内联标记，外部数据才走 esc()。
            judge = ("两种方法<b>看的是不同结构</b>（共现图社区 vs 全文词袋主题），"
                     "一致性偏低属预期结果，不应据此否定任一方法。"
                     if (ari < 0.3) else
                     "两种方法给出了大体一致的分组结构，可互为佐证。")
            cv_html = (f"<p>与 NMF 主题簇的一致性：<b>ARI = {_f(ari)}</b>、"
                       f"<b>NMI = {_f(nmi)}</b>。{judge}</p>")
        else:
            cv_html = ("<p>未做 R↔NMF 一致性比较（R 或 igraph 不可用）。"
                       "启用 R 路径后可获得「共现社群 vs 研究主题」的独立交叉验证。</p>")
        hint = ""
        if not is_r and sna.get("hint"):
            hint = (f"<p>启用 R 路径：<code>{esc(sna['hint'])}</code></p>")

        # ── 计量标准达标判定 ───────────────────────────────────────
        # 需求：：R 分析得出的指标必须标明是否满足"计量标准"。判据一律取学术
        # 通行惯例，并**明确声明这是学科经验惯例、不是统计显著性检验**。没有任何
        # 绝对阈值的指标（边密度、平均度、社群数、中心性）如实判为"无绝对阈值
        # （需对照）"，绝不为凑结论而编造一个阈值。结论用三档状态标签，且刻意
        # 避开警告红 —— Q 偏低 / ARI 偏低都是算法的正常行为，本文件的历史审阅
        # 意见明确反对把正常结果渲染成"异常"。所有数值均由数据驱动计算。
        q = sna.get("modularity")
        dens = sna.get("density")
        n_nod = sna.get("n_nodes")
        n_edg = sna.get("n_edges")
        cv_ = sna.get("cross_validation") or {}
        ari_v, nmi_v = cv_.get("ari_vs_nmf"), cv_.get("nmi_vs_nmf")

        def _fmt(x):
            if isinstance(x, bool) or x is None:
                return "—"
            if isinstance(x, float):
                return f"{x:.4f}".rstrip("0").rstrip(".")
            return str(x)

        # 平均度 k = 2m/n：规模的"可比"量。边密度随 n 天然下降，单看密度无法
        # 跨研究比较，故必须补报平均度作为对照（用户明确要求）。
        avg_deg = None
        if isinstance(n_edg, (int, float)) and isinstance(n_nod, (int, float)) and n_nod:
            avg_deg = round(2.0 * n_edg / n_nod, 3)

        def _ari_band(v):
            if not isinstance(v, (int, float)) or isinstance(v, bool):
                return ""
            if v < 0.2:
                return "极弱·接近随机"
            if v < 0.4:
                return "弱"
            if v < 0.6:
                return "中等"
            if v < 0.8:
                return "强"
            return "极强"

        def _nmi_band(v):
            if not isinstance(v, (int, float)) or isinstance(v, bool):
                return ""
            if v < 0.3:
                return "弱"
            if v < 0.6:
                return "中等"
            return "强"

        # 社群检测算法：优先读产物显式字段；否则从 cross_validation.note / reason
        # 里识别 igraph 算法名（本仓 scripts/sna_r.R:146 用 cluster_walktrap，
        # 该 note 会写明 "walktrap"）。不猜、不硬写算法名。
        _algo = ""
        for _k in ("algorithm", "community_algorithm", "cluster_algorithm"):
            if sna.get(_k):
                _algo = str(sna[_k])
                break
        if not _algo:
            _hay = (" ".join(str(sna.get(_k, "")) for _k in ("reason", "note"))
                    + " " + str(cv_.get("note", "")))
            for _pat, _disp in (("walktrap", "walktrap"),
                                ("louvain", "Louvain"),
                                ("fast_greedy", "fast greedy"),
                                ("label_prop", "标签传播"),
                                ("edge_betweenness", "边介数"),
                                ("leading_eigen", "特征向量")):
                if _pat in _hay.lower():
                    _algo = _disp
                    break
        _algo_txt = _algo or "未在产物中标注"

        _NA = "无绝对阈值（需对照）"

        def _verdict_badge(verdict):
            _cls = {"达标": "std-ok", "未达标": "std-warn",
                    "数据不可用": "std-warn"}.get(verdict, "std-na")
            return f'<span class="std-badge {_cls}">{esc(verdict)}</span>'

        def _std_row(metric, obs, rule, verdict):
            # 对齐规范：指标/判据=文本列（左），观测值=数值列（右），结论=状态标签列（中）。
            return (f"<tr><td>{esc(metric)}</td>"
                    f"<td class='num'>{obs}</td>"
                    f"<td class='std-def'>{rule}</td>"
                    f"<td class='ctr'>{_verdict_badge(verdict)}</td></tr>")

        if is_r:
            _q_ok = (isinstance(q, (int, float)) and not isinstance(q, bool) and q > 0.3)
            std_rows = [
                _std_row("模块度 Q", _fmt(q),
                         "经验门槛 Q &gt; 0.3：Newman–Girvan 以来判定「网络存在显著"
                         "社群结构」的惯用门槛，0.3–0.7 为常见有效区间。此系学科经验"
                         "惯例，<b>不是</b>统计显著性检验。",
                         "达标" if _q_ok else "未达标"),
                _std_row("社群数", _fmt(ncomm),
                         f"由 <b>{esc(_algo_txt)}</b> 算法检出；社群数无绝对阈值，"
                         "须与算法、分辨率参数一并解读。", _NA),
                _std_row("边密度", _fmt(dens),
                         "无绝对阈值：密度随节点数 n 天然下降，须与同规模随机图或"
                         "同领域研究对照。", _NA),
                _std_row("平均度 2m/n",
                         _fmt(avg_deg) if avg_deg is not None else "—",
                         "无绝对阈值，但 <b>规模可比</b>（不随 n 稀释），是密度最好的"
                         "对照量。", _NA),
                _std_row("ARI（vs NMF 主题簇）",
                         _fmt(ari_v) + (f"（{_ari_band(ari_v)}）" if _ari_band(ari_v) else ""),
                         "分级惯例：&lt;0.2 极弱/接近随机；0.2–0.4 弱；0.4–0.6 中等；"
                         "0.6–0.8 强；&gt;0.8 极强。跨方法一致性为描述性指标，无通行"
                         "「合格线」，故不作达标/未达标判定。", _NA),
                _std_row("NMI（vs NMF 主题簇）",
                         _fmt(nmi_v) + (f"（{_nmi_band(nmi_v)}）" if _nmi_band(nmi_v) else ""),
                         "分级惯例：0 表示彼此独立、1 表示完全一致；&lt;0.3 弱、"
                         "0.3–0.6 中等、&gt;0.6 强。为描述性一致性指标，无绝对阈值。",
                         _NA),
                _std_row("中心性（度/介数/接近/特征向量）", "见下表",
                         "描述性指标、无阈值：用于刻画节点在网络中的位置"
                         "（介数高 = 跨社群「桥」），不用于达标判定。", _NA),
            ]
            std_notice = ("<p class='note std-def'>判定说明：本表判据均为学科经验惯例，"
                          "<b>不是统计显著性检验</b>；仅「模块度 Q」存在通行绝对门槛，"
                          "其余指标只报观测量与相对分级，供与同规模随机图 / 同领域研究"
                          "对照。</p>")
            std_caption = "计量标准达标判定"
        else:
            # 未走 R 标准路径：判定表"不可用"本身就是必须显示的结论。
            # R 已是本技能的计量分析标准路径，缺 R 判为「数据不可用」而非静默降级。
            std_rows = [
                _std_row("模块度 Q", _fmt(q),
                         "需 R + igraph 计算；Python 兜底不提供可信的社群结构判定。",
                         "数据不可用"),
                _std_row("社群数 / 社群检测算法", _fmt(ncomm) + " / " + esc(_algo_txt),
                         "Python 兜底不做与 R 同口径的社群检测，数值不可比。",
                         "数据不可用"),
                _std_row("边密度 / 平均度 2m/n",
                         _fmt(dens) + " / " + (_fmt(avg_deg) if avg_deg is not None else "—"),
                         "需与 R 路径下的同一网络对象对照才具可比性。", "数据不可用"),
                _std_row("ARI / NMI（vs NMF 主题簇）", "—",
                         "交叉验证依赖 R 产出的独立社群划分作为比较对象（系数本身由 "
                         "Python 计算）；缺 R 时不存在独立划分，故无值。若拿 Python 兜底"
                         "的伪社群与自身比较，ARI/NMI 恒得 1.0，属伪造结论，故此处如实"
                         "标注为未做。", "数据不可用"),
            ]
            std_notice = ("<p class='note std-def'><b>数据不可靠：本次未走 R 标准路径"
                          "（后端 = Python 兜底）。</b>R 已是本技能的计量分析标准路径，"
                          "缺失时应判为「不可用」，而非静默降级。请安装 R 并确保 igraph "
                          "可用后重跑 <code>sna_r.py</code>，再生成报告以取得可信的"
                          "计量标准判定。</p>")
            std_caption = "计量标准达标判定（不可用）"

        std_html = (f"<h3>{esc(std_caption)}</h3>"
                    "<div class='matrix' style='margin:0 0 10px'><table class='mx'>"
                    "<thead><tr><th>指标</th><th class='num'>观测值</th>"
                    "<th>判据（学科经验惯例）</th><th class='ctr'>结论</th></tr></thead>"
                    f"<tbody>{''.join(std_rows)}</tbody></table></div>"
                    f"{std_notice}")
        sna_html = f"""<h2 id="s12"><span class="n">06</span>R / igraph 交叉验证</h2>
<div class="card"><div class="hd">{badge}
<span class="sub">{ver}</span></div>
<div class="kpis">{kpi_s_html}</div>
{std_html}
{cv_html}{hint}
{tbl}
<p class="note">模块度 Q 越高表示社区结构越清晰；介数高的关键词是跨社群的「桥」，
与共现图中的桥接词（次色描边）互为印证。</p>
</div>"""

    # ── 阅读状态（未读/待读清单）──
    # [!] 判据是**数据能力**，不是来源名称。
    # 原因：CNKI 导出的 .enw 走 EndNote 格式链路，来源名里带 "EndNote"，
    # 但题录里**根本没有 read 字段**（实测 read=0 / unread=500 / 100% 未读）。
    # 此时列「未读清单」是零信息量的伪指标，会让用户误以为自己的库全是未读。
    # 故判据改为：确有非"未知"的已读/未读数据才显示。
    _r_raw = (reading or {}).get("reading") or {}
    _read_n = _r_raw.get("read") or 0
    _unread_n = _r_raw.get("unread") or 0
    # 判据：必须**确有已读记录**。若 100% 未读，说明题录里根本没有 read
    # 字段（题录文件导出即如此），此时"未读清单"= 整份库，无信息量。
    _has_read_state = _read_n > 0
    if reading and not _has_read_state:
        reading = None      # 伪指标：整节略去
    if reading:
        r = _r_raw
        rkpi = [
            ("文献总数", f"{r.get('total', 0):,}"),
            ("已读", f"{r.get('read', 0):,}"),
            ("未读/待读", f"{r.get('unread', 0):,}"),
            ("未读占比", f"{r.get('pct_unread', 0)}%"),
        ]
        rk = "".join(
            f'<div class="kpi"><div class="l">{esc(l)}</div><div class="v">{esc(v)}</div></div>'
            for l, v in rkpi)
        samples = r.get("samples", [])
        # 对齐规范：年份=数值列（右），PDF=状态列（中），其余文本列左。
        rows = "".join(
            f"<tr><td>{esc(s.get('title'))}</td><td class='num'>{esc(s.get('year') or '')}</td>"
            f"<td>{esc(s.get('journal'))}</td>"
            f"<td class='ctr'>{'[OK]' if s.get('has_pdf') else '—'}</td></tr>"
            for s in samples)
        reading_html = f"""<h2 id="s05"><span class="n">05</span>阅读状态（未读 / 待读清单）</h2>
<div class="grid g4" style="margin-bottom:12px">{rk}</div>
<div class="card">
<div style="font-size:12px;color:var(--ink-2);margin-bottom:10px">
约定：read_status='1' 为已读；'0'/空 计为未读/待读（按题录库默认约定）。{esc(r.get('convention',''))}</div>
<div style="font-size:13px;color:var(--ink-2);margin-bottom:8px">待读样本（按年份降序，前 {len(samples)} 篇）：</div>
<table class="mx"><thead><tr><th>标题</th><th class="num">年份</th><th>期刊</th><th class="ctr">PDF</th></tr></thead><tbody>{rows}</tbody></table>
<div style="font-size:12px;color:var(--ink-2);margin-top:10px">完整待读清单可经 reading_status.py --csv 导出。</div>
</div>"""

    # ── 文献时效性预警 ──
    if age:
        ys = age.get("year_stats", {})
        rec = age.get("recency", {})
        st = age.get("staleness", {})
        akpi = [
            ("年份跨度", f"{ys.get('min_year','?')}–{ys.get('max_year','?')}"),
            ("中位数年份", f"{ys.get('median_year','?')}"),
            ("近三年占比", f"{rec.get('recent_pct', 0)}%"),
            (f"早于 {st.get('old_cutoff','?')} 年", f"{st.get('old_pct', 0)}%"),
            ("缺失年份", f"{ys.get('missing_pct', 0)}%"),
        ]
        ak = "".join(
            f'<div class="kpi"><div class="l">{esc(l)}</div><div class="v">{esc(v)}</div></div>'
            for l, v in akpi)
        hist = age.get("year_histogram", {})
        maxc = max(hist.values()) if hist else 1
        bars = "".join(
            f'<div class="b" title="{y}年: {c} 篇" style="height:{max(2, c / maxc * 120):.0f}px"></div>'
            for y, c in sorted(((int(y), c) for y, c in hist.items()))
            if y != "null") if hist else ""
        oldest = age.get("oldest_samples", [])
        orows = "".join(
            f"<tr><td>{esc(o.get('title'))}</td><td class='num'>{esc(o.get('year') or '')}</td>"
            f"<td>{esc(o.get('journal'))}</td></tr>" for o in oldest[:10])
        awarns = "".join(f"<li>{esc(w)}</li>" for w in age.get("warnings", []))
        age_html = f"""<h2 id="s06"><span class="n">05</span>文献时效性预警</h2>
<div class="grid g4" style="margin-bottom:12px">{ak}</div>
<div class="card">
<div class="figbar">
<button class="fbtn" type="button" data-fig="age" data-save="png" data-name="文献年份分布" title="把年份分布柱条保存为 PNG（canvas 重绘，非截图）">保存 PNG</button>
</div>
<div style="font-size:13px;color:var(--ink-2);margin-bottom:6px">年份分布（柱高=文献数；基准年={ys.get('max_year','?')}）：</div>
<div class="hbars">{bars}</div>
<div style="display:flex;justify-content:space-between;font-size:9px;color:var(--ink-3);margin-top:2px">
<span>{ys.get('min_year','')}</span><span>{ys.get('max_year','')}</span></div>
<ul style="margin-top:10px;font-size:13px">{awarns}</ul>
<div style="font-size:13px;color:var(--ink-2);margin:10px 0 8px">最旧文献样本（前 10）：</div>
<table class="mx"><thead><tr><th>标题</th><th class="num">年份</th><th>期刊</th></tr></thead><tbody>{orows}</tbody></table>
<div style="font-size:12px;color:var(--ink-2);margin-top:10px">[!]  时效性以库内最新年份为基准，而非系统时钟。</div>
</div>"""

    # ── 重复 / 近似重复检测 ──
    if dup:
        c = dup.get("counts", {})
        dkpi = [
            ("标题精确重复", f"{c.get('exact_title_refs', 0)} 篇 / {c.get('exact_title_groups', 0)} 组"),
            ("DOI 碰撞", f"{c.get('exact_doi_refs', 0)} 篇 / {c.get('exact_doi_groups', 0)} 组"),
            ("近似重复", f"{c.get('near_refs', 0)} 篇 / {c.get('near_groups', 0)} 组"),
            ("合计标记", f"{c.get('total_flagged_refs', 0)} 篇 ({c.get('pct_flagged', 0)}%)"),
        ]
        dk = "".join(
            f'<div class="kpi"><div class="l">{esc(l)}</div><div class="v">{esc(v)}</div></div>'
            for l, v in dkpi)
        sg = dup.get("groups", [])[:8]
        # 对齐规范：类型=分类列（中），篇数=数值列（右），标题样本=文本列（左）。
        grows = "".join(
            f"<tr><td class='ctr'>{_dup_zh(g.get('type'))}</td>"
            f"<td class='num'>{g.get('size')}</td>"
            f"<td>{'；'.join(esc(t) for t in g.get('sample_titles', [])[:3])}</td></tr>"
            for g in sg)
        dwarns = "".join(f"<li>{esc(w)}</li>" for w in dup.get("warnings", []))
        dup_html = f"""<h2 id="s08"><span class="n">05</span>重复 / 近似重复检测</h2>
<div class="grid g4" style="margin-bottom:12px">{dk}</div>
<div class="card">
<ul style="font-size:13px;margin-bottom:10px">{dwarns}</ul>
<div style="font-size:13px;color:var(--ink-2);margin-bottom:6px">重复组样本（前 {len(sg)} 组）：</div>
<table class="mx"><thead><tr><th class="ctr">类型</th><th class="num">篇数</th><th>标题样本</th></tr></thead><tbody>{grows}</tbody></table>
<div style="font-size:12px;color:var(--ink-2);margin-top:10px">[!]  近似检测仅基于本地元数据（标题/DOI/期刊/年份），合并前需人工核对是否为版本/预印本差异。</div>
</div>"""

    # ── 主题 × 作者矩阵 / 核心作者 ──
    if author_topic:
        at = author_topic
        cnt = at.get("counts", {})
        cols = at.get("matrix", {}).get("col_cluster_ids", [])
        rows = at.get("matrix", {}).get("rows", [])
        maxv = max((max((row.get(str(c), 0) for c in cols), default=0)
                    for row in rows), default=0) or 1
        # 表头此前是内部变量名 c0/c1/c2。
        # 改为「主题N + 主题名」，并在title 里给完整称谓。
        # v1.0.0：直接复用主题总览段算好的 _name_by_id（概念概括名 + 全局
        # 去重）——此前这里只传 top_terms 分词碎片给 label_topic，表头变成
        # 「员工 / 理论构建 / two / emotions」这类碎片。
        _cname = {}
        for _c in clusters:
            _cid = _c.get("cluster_id")
            _nm = _name_by_id.get(_cid) if _name_by_id else None
            if not _nm:
                _kw0 = [w for w in (_c.get("kw_top") or []) if w]
                _nm, _ = label_topic(_kw0 + list(_c.get("top_terms") or []))
            if _nm == NON_TOPIC_KEY:
                _nm = ""
            _cname[_cid] = (_nm or f"主题 {_cid}")
        # [!] 列顺序改为**按主题规模降序**并重新编号 1..N。
        # 此前直接用 cluster_id 内部顺序，显示为"主题0, 主题3, 主题1…"，
        # 用户看到的是内部标识而非有序列表。
        _csizes = {}
        for _c in clusters:
            _csizes[_c.get("cluster_id")] = _c.get("size", 0)
        cols = sorted(cols, key=lambda c: -(_csizes.get(c, 0)))
        head = "".join(
            f'<th title="第 {i} 大主题（{_csizes.get(c, 0)} 篇）：'
            f'{esc(_cname.get(c, ""))}">'
            f'<span class="thn">#{i}</span>'
            f'<span class="tht">{esc(_cname.get(c, ""))}</span></th>'
            for i, c in enumerate(cols, 1))
        body = ""
        for row in rows:
            cells = ""
            for c in cols:
                v = row.get(str(c), 0)
                a = (v / maxv) ** 0.6 if v else 0
                bg = f"rgba(127,119,221,{a:.3f})" if v else "transparent"
                cells += (f'<td class="ht" style="background:{bg}" '
                          f'title="{esc(row.get("name",""))}·c{c}: {v}">{v if v else ""}</td>')
            body += f'<tr><th class="rowh rowname">{esc(row.get("name", ""))}</th>{cells}</tr>'
        core = at.get("global_core_authors", [])[:15]
        core_li = "".join(f"<li>{esc(a.get('name', ''))} — {a.get('total', 0)} 篇</li>"
                          for a in core)
        # fixed 布局 + colgroup：首列(作者名)固定像素宽、主题列均分剩余宽度。
        # 列数随主题数变化，故 colgroup 动态生成（不写死）。
        _lab_px = _label_col_px([str(r.get("name", "")) for r in rows])
        _cg = _mx_colgroup(len(cols), _lab_px)
        _minw = _mx_minw(_lab_px, len(cols), 42)
        authormatrix_html = f"""<h2 id="s11"><span class="n">03</span>主题 × 作者矩阵 / 核心作者</h2>
<div class="card">
<div style="font-size:13px;color:var(--ink-2);margin-bottom:6px">识别作者 {cnt.get('distinct_authors', 0):,} 位（覆盖 {cnt.get('author_coverage_pct', 0)}% 文献）。
下表为全局出现最多的前 {len(rows)} 位作者在各主题簇的文献数（颜色越深越多）。列按主题规模降序排列，#1 为文献最多的主题：</div>
<div class="matrix" style="overflow-x:auto"><table class="mx heat" style="min-width:{_minw}px">
{_cg}<tr><th class="rowh rowname"></th>{head}</tr>{body}</table></div>
<div style="font-size:13px;color:var(--ink-2);margin:12px 0 6px">全局核心作者（Top 15）：</div>
<ul style="columns:2;font-size:13px;list-style:none;padding:0">{core_li}</ul>
<div style="font-size:12px;color:var(--ink-2);margin-top:8px">作者归一为 surname|initials（同名靠缩写区分）；未做跨库消歧。</div>
</div>"""

    # K 判定说明（让 K 的来源可追溯，而非黑盒）
    kdec = diag.get("k_decision")
    kcard = ""
    if kdec:
        curve = kdec.get("curve", [])
        if curve:
            cells = "".join(
                f'<div style="flex:1;min-width:52px;text-align:center">'
                f'<div style="font-size:11px;color:var(--ink-3)">K={c["k"]}</div>'
                f'<div style="height:34px;display:flex;align-items:flex-end;justify-content:center">'
                f'<div style="width:70%;background:{"#1D9E75" if c["ok"] else "#D3D1C7"};'
                f'height:{min(34, max(3, c["min_pct"] * 5.5)):.0f}px"></div></div>'
                f'<div style="font-size:10px;color:var(--ink-2)">{c["min_pct"]}%</div></div>'
                for c in curve)
            src = ("按规则自动判定" if d["params"].get("k_source", "").startswith("auto")
                   else "你手动指定")
            kcard = f"""<div class="card">
<div style="display:flex;justify-content:space-between;align-items:baseline">
<b>主题数 K = {d['params']['k']}</b><span style="font-size:12px;color:var(--ink-2)">{src}</span></div>
<div style="font-size:12px;color:var(--ink-2);margin-top:4px">
判定规则：每个主题至少占全库 <b>{kdec.get('threshold_pct', 3.0)}%</b>，
否则不足以支撑一个可命名、可综述的主题单元。</div>
<div style="display:flex;gap:3px;margin-top:10px;align-items:flex-end">{cells}</div>
{'<div style="font-size:12px;color:#8a6d3b;margin-top:8px">[!]  ' + esc(kdec["note"]) + '</div>' if kdec.get('note') else ''}
</div>"""

    warns = "".join(f"<li>{esc(w)}</li>" for w in diag.get("warnings", []))
    busy_banner = (
        '<div class="notice"><b>检测到 EndNote 正在运行</b>——'
        "本次结果基于只读快照，若你刚修改过文献库请关闭 EndNote 后重新扫描。"
        "</div>") if busy else ""


    # ── 关键词突现（burst_detection.py 产物，可选）──
    if bursts:
        bl = (bursts.get("bursts") or [])[:30]
        covb = bursts.get("coverage", {})
        par = bursts.get("params", {})
        brows = []
        for b in bl:
            hist = b.get("year_hist") or {}
            # [!] 必须先过滤再取 max：hist 全为 0 或为空时 max() 会 ValueError，
            #   而异常发生在 build_html 里 → **整份报告生成失败**，不是少一张图。
            _hv = [v for v in hist.values() if v]
            _hm = max(_hv) if _hv else 0
            spark = "".join(
                f'<span class="sb{" zero" if not v else ""}" '
                f'style="height:{max(1, int(v / _hm * 100)) if _hm else 1}%" '
                f'title="{esc(str(y))} 年：{v} 篇"></span>'
                for y, v in sorted(hist.items()))
            brows.append(
                f"<tr><td class='kwc'>{esc(str(b.get('keyword','')))}</td>"
                f"<td class='num'>{b.get('peak_year')}</td>"
                f"<td class='num'>{b.get('peak_df')}</td>"
                f"<td class='num'>{b.get('baseline_mean')}</td>"
                f"<td class='num'>{b.get('burst_ratio')}</td>"
                f"<td class='num'><b>{b.get('strength')}</b></td>"
                f"<td class='cft'>{esc(str(b.get('confidence','')))}</td>"
                f"<td class='spkcell'><div class='spark'>{spark}</div></td></tr>")
        # 数字列的 th 必须与 td 同步加 .num，否则表头左对齐、数据右对齐 → 错位。
        # 仅靠 .num 仍不够稳：自动列宽下，「峰值 df」这类较宽的中文表头会把
        # 列撑开，而内容比表头窄，视觉上就像"数据没跟表头对齐"。
        # 故用 colgroup 把每列宽度写死 + table-layout:fixed —— 对齐由结构保证。
        tbl = ("<table class='mx bstab'><colgroup>"
               "<col><col style='width:76px'><col style='width:76px'>"
               "<col style='width:88px'><col style='width:88px'>"
               "<col style='width:66px'><col style='width:72px'>"
               "<col style='width:184px'></colgroup>"
               "<thead><tr>"
               "<th>关键词</th>"
               "<th class='num'>峰值年</th><th class='num'>峰值 df</th>"
               "<th class='num'>基线均值</th><th class='num'>突现倍数</th>"
               "<th class='num'>强度</th>"
               "<th>置信</th><th>年度分布</th></tr></thead><tbody>"
               + "".join(brows) + "</tbody></table>") if brows else ""
        # 列义说明：这几个量是自造的（非 Kleinberg），必须逐列讲清口径，
        # 否则读者只能靠猜「突现倍数 2.4 到底算高还是低」。
        col_note = ("<p class='note'><b>列义：</b>"
                    "<b>峰值年</b>=该词频次最高的一年；"
                    "<b>峰值 df</b>=峰值年的文献数；"
                    "<b>基线均值</b>=窗口内其余年份的均值；"
                    "<b>突现倍数</b>=峰值 df ÷ 基线均值（&lt;1.5 已在计算阶段剔除）；"
                    "<b>强度</b>=突现倍数 × log(1+总频次) 的归一化值，只可同库内横向比；"
                    "<b>年度分布</b>=各年词频的迷你条形图（横轴为年份先后）。</p>")

        bkpi = "".join(
            f'<div class="kpi"><div class="l">{esc(a)}</div><div class="v">{esc(b)}</div></div>'
            for a, b in [
                ("突现候选词", str(len(bl))),
                ("窗口半径", f"±{par.get('window', '?')} 年"),
                ("最低频次门槛", str(par.get("min_total", "?"))),
                ("缺年份文献", f"{covb.get('missing_year_pct', 0)}%"),
            ])
        bursts_html = f"""<h2 id="s09"><span class="n">04</span>关键词突现检测</h2>
<div class="card"><div class="hd"><span class="tag">keyword burst</span>
<span class="sub">依据关键词出现频次突增</span></div>
<div class="kpis">{bkpi}</div>
<div class="figbar">
<button class="fbtn" type="button" data-fig="burst" data-save="png" data-name="关键词突现年度分布" title="把突现词的年度分布（迷你条）保存为 PNG（canvas 重绘，非截图）">保存 PNG</button>
</div>
{col_note}
{tbl}
<p class="note">[!]  <b>这是关键词突现（keyword burst），不是引文突现（citation burst）。</b>
关键词突现依据题录的关键词词频变化；引文突现则依赖被引频次突增，需要引文数据。
本报告的数据源<b>不含引文信息</b>——文献管理软件不提供被引频次，题录导出文件同样不含，
因此本项<b>不可</b>与引文突现互相替代。强度 = 突现倍数 × log(1+总频次) 的归一化值，
仅用于同库内横向比较。置信度由基线年份数与词频共同决定；置信度为 <code>low</code> 的条目不应作为结论依据。</p>
</div>"""

    _present_sections = _collect_present_sections(
        (reading_html, age_html, dup_html, bursts_html, sna_html,
         pub_html, cross_html, authormatrix_html, timeline_html, matrix_html,
         authnet_html, instnet_html, citnet_html))
    # 章节顺序按用户明确要求重排（原始需求："发文量与趋势之后，我觉得是作者、机构和
    # 年份贡献，接着是关键词，最后交叉。还有文献时效和重复检测，应该属于数据体检中"）：
    #   数据体检（含时效/重复/阅读状态）→ 发文量与趋势 → 作者/机构/引文网络
    #   → 研究主题 → 年份贡献（主题×年份 + 关键词年份图）→ 关键词（共现 + 突现）
    #   → 交叉（主题×作者 / 多维交叉）→ R 交叉验证
    # 这段顺序是**唯一事实来源**：目录顺序、正文拼接顺序、章节编号胶囊（见
    # _renumber_sections）三处都对齐它，才不会出现「目录 03 / 正文 S13」这类编号打架。
    # 注意：只是顺序重排，章节归属集合不变；编号一律由 _renumber_sections 回填，
    # 且只发给**实际渲染出来**的章节（缺数据的章节不占号）。
    SECTION_ORDER = [
        ("s01", "数据体检", False),
        ("s06", "文献时效性预警", False),
        ("s08", "重复 / 近似重复检测", False),
        ("s05", "阅读状态", False),
        ("s13", "发文量与趋势", True),
        ("s15", "作者共现网络", True),
        ("s16", "机构共现网络", True),
        # s17 的正文标题会按产物自动写成「引文共被引网络」或「引文耦合网络」；
        # 目录这里给稳定标签，避免同一份报告里目录名与正文名因模式而不同步。
        ("s17", "引文网络（共被引 / 耦合）", True),
        ("s02", "研究主题", True),
        ("s03", "主题 × 年份演化", True),
        # [!] s11（主题 × 作者矩阵）按需求：排在「关键词年份图」之前。
        #   理由：它属于「主题 × 什么」这一族（主题×年份 / 主题×作者），
        #   紧跟主题演化读下来更顺；原先混在末尾的交叉分析里，与多维交叉
        #   挤在一起，反而看不出它其实是主题维度分析。
        ("s11", "主题 × 作者矩阵", False),
        ("s07", "关键词年份图", True),
        ("s04", "关键词共现网络", True),
        ("s09", "关键词突现检测", True),
        ("s14", "多维交叉共现", False),
        ("s12", "R / igraph 交叉验证", False),
    ]

    # 网络口径说明：关键词共现网络始终存在；引文网络（s17）仅在题录带参考文献字段时出现。
    # 原硬写"数据源本身不含引文信息"在 WoS/Scopus 等带 Cited-References 的源上不成立，
    # 会与 s17 引文网络一节自相矛盾，故按实际产物动态措辞。
    if cit_net:
        _net_notice = ('这是<b>关键词共现网络</b>，不是引文网络——它回答"概念之间有什么关联"，'
                       '不回答"哪篇文献引用了哪篇"。本报告另含「引文网络」一节，'
                       '基于题录自带的参考文献（Cited-References）字段构建共被引 / 文献耦合网络，'
                       '与上方关键词共现网络是两种不同网络，结论不可互相替代。')
    else:
        _net_notice = ('这是<b>关键词共现网络</b>，不是引文网络——它回答"概念之间有什么关联"，'
                       '不回答"哪篇文献引用了哪篇"。本数据源的题录未提供参考文献（Cited-References）字段，'
                       '故不构建引文网络；如需引文分析，请改用带 Cited-References 的导出'
                       '（WoS / Scopus / 含参考文献的 BibTeX）。')

    toc_html = _toc_html(SECTION_ORDER, _present_sections)
    html_out = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(_report_title(d))}</title><style>{CSS}</style></head><body>
<div class="shell">
<aside class="side">
<div class="brand"><b>学术文献计量分析</b>
<span>离线计算 · 无网络请求</span></div>
{toc_html}
</aside>
<main class="main">
<div class="head">
<h1>{esc(_report_title(d))}</h1>
<div class="sub">{esc(d['library']['name'])} · {cov['total']:,} 篇 · 主题数 {len(clusters)} ·
耗时 {d['timing']['total']}s</div>
</div>

{busy_banner}
{summary_html}

<div class="notice"><b>关系网络口径说明</b><br>{_net_notice}</div>

<div class="grid g4" style="margin-bottom:16px">{kpi_html}</div>

{kcard}

<!-- ═══ 01 数据体检：先交代"数据本身可不可信"，再谈发现了什么 ═══ -->
<h2 id="s01"><span class="n">01</span>数据体检</h2>
<div class="card"><table class="mx"><thead><tr><th>项目</th><th class="num">数量</th><th>说明</th></tr></thead><tbody>
<tr><td>有摘要（主语料）</td><td class="num">{cov['tier']['primary_abs']:,}</td><td>参与聚类的首选语料</td></tr>
<tr><td>仅关键词（主语料）</td><td class="num">{cov['tier']['primary_kw']:,}</td><td>关键词网络的独有贡献者</td></tr>
<tr><td>仅标题（降级）</td><td class="num">{cov['tier']['fallback_title']:,}</td><td>用「标题+关键词」兜底参与聚类</td></tr>
<tr><td>零丢弃校验</td><td class="num">{_dropped:,}</td>
 <td>丢弃 {_dropped:,} 条。主语料 + 降级 = {cov['tier']['primary_abs']+cov['tier']['primary_kw']+cov['tier']['fallback_title']+cov['tier']['empty']:,}
 = {cov['total']:,}，{'[OK] 约束成立（无文献被丢弃）' if cov['zero_drop_identity'] else '[X] 约束破裂（存在未归档文献）'}</td></tr>
<tr><td>无摘要</td><td class="num">{cov['no_abstract']:,}</td><td>占 {cov['no_abstract']/cov['total']*100:.1f}%</td></tr>
<tr><td>无关键词</td><td class="num">{cov['no_keywords']:,}</td>
 <td>占 {cov['no_keywords']/cov['total']*100:.1f}% —— <b>共现网络只覆盖其余 {cov['keyword_coverage_pct']}% 的文献</b></td></tr>
<tr><td>有 PDF 附件</td><td class="num">{cov['has_pdf']:,}</td><td>用于跳转原文</td></tr>
<tr><td>2015 年前</td><td class="num">{cov['pre_2015']:,}</td>
 <td>演化图已纳入（最早 {cov['year_min']} 年），未做截断</td></tr>
</tbody></table>{'<ul style="margin-top:10px;font-size:13px">' + warns + '</ul>' if warns else ''}{net_notes_html}</div>

<!-- ═══ 数据质量补充：时效 / 重复 / 阅读状态（用户明确要求归入"数据体检"层）═══ -->
{age_html}
{dup_html}
{reading_html}

<!-- ═══ 发文量与趋势：这个领域多大、在往哪走 ═══ -->
{pub_html}

<!-- ═══ 关系网络：作者 / 机构 / 引文（有数据才出现，无则整节略去）═══ -->
{authnet_html}
{instnet_html}
{citnet_html}

<!-- ═══ 研究主题：在研究什么 ═══ -->
<h2 id="s02"><span class="n">03</span>研究主题（{len(clusters)} 个）</h2>
<div class="legend" style="margin-bottom:10px">
<span><span class="tag zh">中文</span>纯中文主题</span>
<span><span class="tag en">英文</span>纯英文主题</span>
<span><span class="tag mixed">跨语</span>同时含中英文 —— 这是重要发现，非异常</span>
</div>
{topic_overview}
{''.join(cards)}

<!-- ═══ 主题维度：主题 × 年份演化 + 主题 × 作者矩阵 ═══ -->
{matrix_html}
{authormatrix_html}

<!-- ═══ 关键词年份图 ═══ -->
{timeline_html}

<!-- ═══ 关键词：共现网络 + 突现检测 ═══ -->
<h2 id="s04"><span class="n">06</span>关键词共现网络</h2>
{net_card}

{bursts_html}

<!-- ═══ 交叉分析：多维交叉共现 ═══ -->
{cross_html}

<!-- ═══ R / igraph 交叉验证 ═══ -->
{sna_html}

<details class="methodbox">
<summary>方法与口径（点击展开）</summary>
<div class="methodbody">
<table class="mx nopad"><tbody>
<tr><td>主题聚类</td><td>TF-IDF + NMF</td>
    <td>初始化 {esc(str(d['params'].get('nmf_init', '—')))}，
        主题数 K={esc(str(d['params'].get('k', '—')))}</td></tr>
<tr><td>分词</td><td>中英分流</td>
    <td>英文按空格切分；中文 jieba + 领域术语词典；
        停用词 {esc(str(d['params'].get('stop_words', 376)))} 个</td></tr>
<tr><td>共现网络</td><td>关键词共现</td>
    <td>大小写归一 lower；文档级词频；节点最少出现
        {esc(str(d['params'].get('node_df', 5)))} 次；边权阈值
        {esc(str(d['params'].get('min_edge', 2)))}；篇内去重</td></tr>
<tr><td>扩展分析</td><td>纯 Python</td>
    <td>重复检测 / 时效性预警 / 主题×作者矩阵 —— 均只读题录元数据计算</td></tr>
<tr><td>交叉验证</td><td>R + igraph（必需）</td>
    <td>必需标准路径；缺失且未显式传 --allow-python-fallback 时脚本硬失败（退出码 8，环境不满足），须先安装 R + igraph 再运行。显式回退时产物标注为非标准路径</td></tr>
<tr><td>数据安全</td><td>只读</td>
    <td>以 SQLite 只读模式访问题录库，<b>全程不写入任何数据</b>；
        不联网、不回写文献管理软件</td></tr>
</tbody></table>
</div>
</details>
<footer>本报告由本地题录离线计算生成，不含任何网络请求；数值口径见上方「方法与口径」。</footer>
</main>
</div>
<script>{net_js}</script>
<script>{DL_JS}</script>
<script>{JS_NET}</script>
<script>{authnet_js}</script>
<script>{AUTH_JS}</script>
<script>{instnet_js}</script>
<script>{citnet_js}</script>
<script>{NETVIEW_JS}</script>
<script>{NAV_JS}</script>
<script>{FIGSAVE_JS}</script>
</body></html>"""

    # 章节编号统一回填：正文里各 <h2 id="sXX"> 的编号胶囊历史上是手写的
    # （S13 / 04 / 03 …），与目录的顺序编号各说各话。重排后更会明显打架，
    # 故按 SECTION_ORDER 统一覆写为真实序号。
    html_out = _renumber_sections(html_out, SECTION_ORDER)
    # 窄屏防溢出：所有宽表统一包进横向滚动容器
    return _wrap_tables(html_out)


TBL_CSS = """
body{font-family:'Songti SC','SimSun',serif;font-size:10.5pt;color:#000}
table.sx{border-collapse:collapse;border:none;margin:4px 0 0 0}
table.sx th,table.sx td{border:none;padding:4px 9px;text-align:center}
table.sx thead th{border-top:2px solid #000;border-bottom:1px solid #000}
table.sx tbody tr:last-child td{border-bottom:2px solid #000}
table.sx td.num,table.sx th.num{text-align:right;font-variant-numeric:tabular-nums}
div.sxcap{font-weight:600;margin-top:18px}
div.sxnote{font-size:9pt;color:#333;margin-top:3px;line-height:1.5}
/* 突现检测的年度分布迷你柱图（sparkline） */
div.spark{display:flex;align-items:flex-end;gap:1px;height:22px;min-width:120px}
div.spark .bar{display:inline-block;width:4px;background:#8a7f5c;border-radius:1px 1px 0 0}
div.spark .bar:hover{background:#3a3a36}
"""

def sanxian_tables(topics, author_topic=None, evolution=None, sna=None,
                  trend=None) -> str:
    """生成中文期刊三线表（可直接粘入 Word 的独立 HTML）。

    规范：中文期刊三线表通行格式
      · 只保留三条横线（顶线粗 / 栏目线细 / 底线粗），**不画竖线**；
      · 数字列右对齐并按小数点对齐（tabular-nums）；
      · 注释行在底线之下、字号更小，以「注：」起首；
      · 不做推断检验，故表注显式声明无 p 值（避免被误读为显著性检验结果）。
    """
    cl = topics.get("clusters", [])
    def cap(n, name):
        return f'<div class="sxcap">表 {n}&nbsp;&nbsp;{esc(name)}</div>'
    def note(*lines):
        body = "<br>".join(esc(x) for x in lines)
        return f'<div class="sxnote">注：{body}</div>'
    out = []
    # 表 1：主题分布
    if cl:
        rows = []
        for i, c in enumerate(sorted(cl, key=lambda x: -x["size"]), 1):
            rows.append(
                f"<tr><td>{i}</td>"
                f"<td class='num'>{c['size']}</td>"
                f"<td class='num'>{c['pct']:.1f}</td>"
                f"<td>{esc(c.get('lang_dominant','') == 'zh' and '中文' or '英文')}</td>"
                f"<td>{esc(', '.join(c['top_terms'][:5]))}</td></tr>")
        out.append(cap(1, "文献库主题聚类分布") + f"""
<table class="sx"><thead><tr><th>主题</th><th class="num">文献数</th>
<th class="num">占比(%)</th><th>主导语言</th><th>代表关键词（前 5）</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table>""" +
 note(f"主题数 K={topics.get('params',{}).get('k','—')}，算法 TF-IDF + NMF（init=nndsvda，random_state=42）。",
      "占比按全库文献数计算；代表关键词为各簇 NMF 成分权重最高的 5 个词。",
      "本表为描述性统计，未做推断检验，故不标注 p 值与显著性。"))
    # 表 2：主题 × 年份
    if evolution:
        years = (evolution.get("years") or topics.get("years") or [])[:12]
        if years:
            hdr = "".join(f"<th class='num'>{esc(str(y))}</th>" for y in years)
            rows = []
            for c in sorted(cl, key=lambda x: -x["size"])[:10]:
                row = evolution.get("matrix", {}).get(str(c["cluster_id"]), {})                     or evolution.get("matrix", {}).get(c["cluster_id"], {})
                tds = "".join(f"<td class='num'>{int(row.get(str(y), 0))}</td>" for y in years)
                rows.append(f"<tr><td>{c['cluster_id']}</td>{tds}</tr>")
            out.append(cap(2, "主题 × 年份分布（近 12 年）") + f"""
<table class="sx"><thead><tr><th>主题</th>{hdr}</tr></thead>
<tbody>{''.join(rows)}</tbody></table>""" +
 note("单元格为该主题在该年份的文献篇数。", "早期年份样本量较小，趋势解读需谨慎。",
      "本表为描述性统计，未做推断检验。"))
    # 表 3：核心作者
    if author_topic:
        core = author_topic.get("global_core_authors", [])[:15]
        if core:
            rows = []
            for i, a in enumerate(core, 1):
                nm = a.get("name") or a.get("pretty") or a.get("author") or "—"
                rows.append(f"<tr><td class='num'>{i}</td><td>{esc(str(nm))}</td>"
                            f"<td class='num'>{a.get('n_docs', a.get('count','—'))}</td>"
                            f"<td>{esc(', '.join(str(x) for x in (a.get('topics') or a.get('clusters') or [])[:3]))}</td></tr>")
            out.append(cap(3, "核心作者分布（前 15）") + f"""
<table class="sx"><thead><tr><th class="num">序</th><th>作者</th>
<th class="num">文献数</th><th>主要所属主题</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table>""" +
 note("作者归一口径为“姓|名缩写”，未做跨库消歧，同名作者可能被合并或拆分。",
      "本表为描述性统计，未做推断检验。"))
    # 表 4：R 交叉验证
    if sna:
        cv = sna.get("cross_validation") or {}
        ari4, nmi4 = cv.get("ari_vs_nmf"), cv.get("nmi_vs_nmf")
        # [!]  ARI/NMI 必须与「后端真的是 R」一起判定。
        #    无 R 时不存在独立社群划分，任何 ARI/NMI 都无意义；打印数字
        #    （尤其是 1.0）会被读成"社群与主题高度一致"的方法学验证结论。
        t4_is_r = sna.get("backend") == "R"
        if t4_is_r and ari4 is not None and nmi4 is not None:
            cv_rows = (
                f"<tr><td>ARI（vs 主题簇）</td><td class='num'>{ari4:.3f}</td></tr>"
                f"<tr><td>NMI（vs 主题簇）</td><td class='num'>{nmi4:.3f}</td></tr>")
            cv_note = ("社群由 igraph 的 walktrap 算法在关键词共现图上得到，"
                       "主题簇由 TF-IDF+NMF 得到，二者方法学不同。",
                       "一致性偏低属预期结果，不应据此否定任一方法。")
        else:
            cv_rows = ("<tr><td>ARI（vs 主题簇）</td><td class='num'>未做交叉验证"
                       "（R/igraph 不可用）</td></tr>"
                       "<tr><td>NMI（vs 主题簇）</td><td class='num'>未做交叉验证"
                       "（R/igraph 不可用）</td></tr>")
            cv_note = ("未做 R↔NMF 一致性比较：本机R 或 igraph 不可用，"
                       "不存在独立于 NMF 的社群划分可比。",
                       "此处不报数字——用兜底伪社群与自身比较会恒得 1.0，"
                       "那是自我比对而非独立验证。",
                       "安装 R + igraph 后重跑即可获得真实交叉验证。")
        out.append(cap(4, "共现网络社群与主题聚类的一致性（R/igraph 交叉验证）") + f"""
<table class="sx"><thead><tr><th>指标</th><th class="num">数值</th></tr></thead><tbody>
<tr><td>后端</td><td>{esc(str(sna.get('backend')))}</td></tr>
<tr><td>模块度 Q</td><td class="num">{esc(str(sna.get('modularity')))}</td></tr>
<tr><td>社群数</td><td class="num">{len(sna.get('communities') or [])}</td></tr>
{cv_rows}
</tbody></table>""" +
         note(*cv_note,
              "本表为描述性统计，未做推断检验。"))
    # 表 5：主题 × 时期趋势（含效应量）
    if trend:
        ef = trend.get("effects", {})
        rows = []
        for r in trend.get("by_cluster", [])[:12]:
            ci = r.get("recent_share_ci95", ["—", "—"])
            rows.append(
                f"<tr><td>{esc(str(r.get('cluster_id')))}</td>"
                f"<td>{esc(str(r.get('label',''))[:34])}</td>"
                f"<td class='num'>{r.get('share_early_pct')}</td>"
                f"<td class='num'>{r.get('share_recent_pct')}</td>"
                f"<td class='num'>{r.get('delta_pp'):+.1f}</td>"
                f"<td class='num'>[{ci[0]}, {ci[1]}]</td>"
                f"<td>{esc(str(r.get('direction')))}</td></tr>")
# [!]  η² 在"分组变量无组内变异"时是 0/0，stat_helpers 现返回 nan。
        #    nan 是浮点里的"无法计算"，直接印出去会显示成 "η² = nan"，
        #    而 level 也会退化成"可忽略"，看起来像"实测为0" ——
        #    两者都不是真相。故此处显式渲染为「无法计算」并说明原因。
        _eta = ef.get("eta_squared")
        try:
            _eta_bad = _eta is None or _eta != _eta  # NaN != NaN
        except TypeError:
            _eta_bad = True
        _eta_txt = (f"η² = 无法计算（所有文献年份相同 → η² = 0/0 无定义，"
                    f"不是「解释力为零」）" if _eta_bad
                    else f"η² = {_eta}（{ef.get('eta_squared_level')}）")
        out.append(cap(5, f"主题 × 时期分布与趋势（分期年份 {trend.get('cut_year')}）") + f"""
<table class="sx"><thead><tr><th>主题</th><th>代表关键词</th>
<th class="num">早期占比(%)</th><th class="num">近期占比(%)</th>
<th class="num">变化(pp)</th><th class="num">近期占比 95%CI</th><th>方向</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table>""" +
         note(f"效应量：Cramér's V = {ef.get('cramers_v')}（{ef.get('cramers_v_level')}），"
              f"{_eta_txt}。",
              f"早期 < {trend.get('cut_year')} 年（{trend.get('n_early')} 篇），"
              f"近期 >= {trend.get('cut_year')} 年（{trend.get('n_recent')} 篇）。",
              esc(str(ef.get('caveat',''))),
              "置信区间为百分位 bootstrap（1000 次）；本表为描述性统计，未做推断检验。"))
    body = "".join(out)
    return ('<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">'
            f'<style>{TBL_CSS}</style></head><body>{body}</body></html>')


def main() -> int:
    ap = argparse.ArgumentParser(description="生成自包含 HTML 报告")
    ap.add_argument("--topics", required=True)
    ap.add_argument("--network")
    ap.add_argument("--evolution")
    ap.add_argument("--reading")
    ap.add_argument("--dup")
    ap.add_argument("--age")
    ap.add_argument("--author-topic")
    ap.add_argument("--sna-r", help="sna_r.py 产出的 sna_r.json（R 标准路径；计量分析要求 R+igraph 交叉验证）")
    ap.add_argument("--cross",
                    help="cross_matrix.py 产出的 cross_matrix.json（可选）")
    ap.add_argument("--pub-stats",
                    help="publication_stats.py 产出的 publication_stats.json（可选）")
    ap.add_argument("--keyword-network",
                    help="build_keyword_network.py 产出的 keyword_network.json"
                         "（可选，年轮视图的数据源）")
    ap.add_argument("--sanxian", help="额外输出中文期刊三线表 HTML（可直接粘入 Word）")
    ap.add_argument("--trend", help="trend_effects.py 产出的 trend_effects.json（可选）")
    ap.add_argument("--bursts", help="burst_detection.py 产出的 bursts.json（可选）")
    ap.add_argument("--author-network",
                    help="build_author_network.py 产出的 author_network.json"
                         "（可选，作者共现网络；缺失时该章节整节略去，不进目录）")
    ap.add_argument("--institution-network",
                    help="build_institution_network.py 产出的 institution_network.json"
                         "（可选，机构共现网络；缺失时该章节整节略去，不进目录）")
    ap.add_argument("--citation-network",
                    help="build_citation_network.py 产出的 citation_network.json"
                         "（可选，引文共被引 / 耦合网络；模式由产物自动识别）")
    ap.add_argument("--out", default="report.html")
    args = ap.parse_args()

    def _load(p):
        if not p or not Path(p).exists():
            return None
        return json.loads(Path(p).read_text(encoding="utf-8"))

    try:
        topics = json.loads(Path(args.topics).read_text(encoding="utf-8"))
        network = _load(args.network)
        evo = _load(args.evolution)
        if evo is not None:
            evo["years"] = topics.get("years", [])
        reading = _load(args.reading)
        dup = _load(args.dup)
        age = _load(args.age)
        author_topic = _load(args.author_topic)
        sna = _load(args.sna_r)
        kw_net = _load(args.keyword_network)
        pub = _load(args.pub_stats)
        cross = _load(args.cross)
        trend = _load(args.trend)
        bursts = _load(args.bursts)
        auth_net = _load(args.author_network)
        inst_net = _load(args.institution_network)
        cit_net = _load(args.citation_network)
        out = Path(args.out)
        out.write_text(
            build_html(topics, network, evo, reading=reading, dup=dup,
                       age=age, author_topic=author_topic, sna=sna, kw_net=kw_net, pub=pub, cross=cross,
                       bursts=bursts, auth_net=auth_net, inst_net=inst_net, cit_net=cit_net),
            encoding="utf-8")
        print(f"[ok] 报告已生成: {out}  ({out.stat().st_size/1024:.0f} KB)", file=sys.stderr)
        if args.sanxian:
            tp = Path(args.sanxian)
            tp.write_text(sanxian_tables(topics, author_topic, evo, sna, trend), encoding="utf-8")
            print(f"[ok] 三线表已生成: {tp}  ({tp.stat().st_size/1024:.0f} KB)", file=sys.stderr)
        return 0
    except Exception as e:  # noqa: BLE001
        print(f"[error] {type(e).__name__}: {e}", file=sys.stderr)
        print(f"[hint] {EXIT[5]}", file=sys.stderr)
        return 5


if __name__ == "__main__":
    sys.exit(main())
