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
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from endnote_core import EXIT, esc_json  # noqa: E402

# 主题命名：内置 OB/HRM 术语表 + 用户自定义 + 关键词回退
import sys as _sys
_sys.path.insert(0, str(Path(__file__).parent.parent / "references"))
try:
    from topic_labels import label_topic, NON_TOPIC_KEY
except Exception:            # 命名模块缺失不应阻塞报告生成
    def label_topic(top_terms, user_labels=None):
        return "", "none"
    NON_TOPIC_KEY = "其他·未归类文献"

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;
background:#fafafa;color:#2c2c2a;line-height:1.6;padding:24px;font-size:14px}
.wrap{max-width:1180px;margin:0 auto}
h1{font-size:20px;font-weight:500;margin-bottom:6px}
h2{font-size:16px;font-weight:500;margin:28px 0 12px;padding-bottom:6px;border-bottom:1px solid #e5e5e0}
.sub{font-size:13px;color:#6b6b66;margin-bottom:20px}
.card{background:#fff;border:1px solid #e8e8e3;border-radius:10px;padding:16px 18px;margin-bottom:14px}
.notice{background:#fff8e6;border:1px solid #f0d9a0;border-radius:8px;padding:12px 14px;margin-bottom:16px;font-size:13px}
.notice b{color:#8a5a00}
.grid{display:grid;gap:12px}
.g2{grid-template-columns:repeat(auto-fit,minmax(320px,1fr))}
.g3{grid-template-columns:repeat(auto-fit,minmax(240px,1fr))}
.g4{grid-template-columns:repeat(auto-fit,minmax(170px,1fr))}
.kpi{background:#f5f5f2;border-radius:8px;padding:12px 14px}
.kpi .l{font-size:12px;color:#6b6b66}
.kpi .v{font-size:22px;font-weight:500;margin-top:2px}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{text-align:left;padding:7px 8px;border-bottom:1px solid #f0f0ec}
th{color:#6b6b66;font-weight:500;font-size:12px}
tr:hover td{background:#fafaf7}
.tag{display:inline-block;padding:1px 7px;border-radius:10px;font-size:11px;margin-right:4px}
.zh{background:#e6f0fb;color:#185fa5}
.en{background:#eaf3de;color:#3b6d11}
.mixed{background:#fceaea;color:#a32d2d}
.terms{font-size:12px;color:#55554f;margin-top:3px}
.bar{height:6px;background:#eeeae0;border-radius:3px;overflow:hidden;margin-top:5px}
.bar>i{display:block;height:100%;background:#7f77dd}
/* touch-action:pan-y —— 纵向允许页面滚动（手机上能正常阅读报告），
   横向手势才交给画布做平移/缩放。若用 none 会吞掉页面滚动。 */
canvas{width:100%;display:block;background:#fff;border-radius:8px;touch-action:pan-y;}
/* 复位按钮（v0.3.1 节点手动微调配套） */
button.rstbtn{font:inherit;font-size:12px;padding:3px 10px;cursor:pointer;
  background:#fff;color:#3a3a36;border:1px solid #d8d8d2;border-radius:5px;}
button.rstbtn:hover{background:#f2f1ec;border-color:#b9b9b0;}
button.rstbtn:active{background:#e8e7e0;}
/* 视图切换与导出工具栏 */
.netbar,.netrow .toolbar{display:flex;align-items:center;gap:6px;flex-wrap:wrap;}
button.viewbtn{font:inherit;font-size:12px;padding:3px 10px;cursor:pointer;
  background:#fff;color:#3a3a36;border:1px solid #d8d8d2;border-radius:5px;}
button.viewbtn:hover{background:#f2f1ec;}
button.viewbtn.on{background:#3a3a36;color:#fff;border-color:#3a3a36;}
/* 年份色条（蓝→青→黄），与 JS yearColor 端点一致 */
.yrbar{display:inline-block;width:110px;height:10px;border-radius:5px;
  background:linear-gradient(90deg,rgb(43,72,140) 0%,rgb(64,196,164) 50%,rgb(250,232,110) 100%);
  border:1px solid #d8d8d2;vertical-align:middle;}
.yrlab{font-size:11px;color:#55554f;font-variant-numeric:tabular-nums;}
.chips{display:flex;flex-wrap:wrap;gap:4px;margin-top:6px}
.chip{background:#f0f0ec;border-radius:4px;padding:1px 6px;font-size:11px;color:#55554f;cursor:pointer}
.chip:hover{background:#e8e8e3}
.chip.off{opacity:.32;text-decoration:line-through}
.legend{display:flex;gap:14px;flex-wrap:wrap;font-size:12px;color:#6b6b66;margin-top:8px}
.dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:4px;vertical-align:middle}
/* 主题图例：可点击，点击=只看该主题 */
.lg{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}
.lg-item{display:flex;align-items:center;gap:5px;padding:3px 8px;border:1px solid #e3e3dd;
  border-radius:14px;font-size:12px;color:#3a3a36;cursor:pointer;background:#fff;
  user-select:none;transition:background .12s,border-color .12s}
.lg-item:hover{background:#f4f4f0;border-color:#cfcfc7}
.lg-item.on{background:#eceaf7;border-color:#8a80d8;font-weight:500}
.lg-item .sw{width:11px;height:11px;border-radius:3px;flex:none}
.lg-item .n{color:#8a8a84;font-size:11px}
/* 侧栏：该主题关键词列表 */
.side{margin-top:12px;border:1px solid #e8e8e3;border-radius:8px;padding:10px 12px;background:#fdfdfb}
.side h4{font-size:12px;font-weight:500;color:#6b6b66;margin-bottom:7px}
.kws{display:flex;flex-wrap:wrap;gap:4px;max-height:132px;overflow-y:auto}
.kw{display:inline-flex;align-items:center;gap:4px;background:#f4f4f0;border-radius:4px;
  padding:2px 7px;font-size:11.5px;color:#3a3a36;cursor:pointer}
.kw:hover{background:#e9e9e3}
.kw i{width:7px;height:7px;border-radius:2px;flex:none}
.kw small{color:#9a9a92;font-size:10px}
.perf{font-size:11px;color:#9a9a92;margin-left:auto}
.netrow{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap}
.matrix{overflow-x:auto}

table.mx{border-collapse:collapse;font-size:11px}
/* 三线表：顶线(粗) + 栏目线(细) + 底线(粗)，无竖线 —— 中文期刊规范 */
table.sx{border-collapse:collapse;border:none!important;margin:6px 0 2px 0}
table.sx th,table.sx td{border:none!important;padding:5px 10px;text-align:center}
table.sx thead tr:first-child th{border-top:2px solid #000!important}
table.sx thead th{border-bottom:1px solid #000!important}
table.sx tbody tr:last-child td{border-bottom:2px solid #000!important}
table.sx td.num,table.sx th.num{text-align:right;font-variant-numeric:tabular-nums}
div.sxcap{font-weight:600;margin-top:14px}
div.sxnote{font-size:.86em;color:#444;margin-top:2px;line-height:1.5}
table.mx th{background:#f5f5f2;padding:4px 5px;font-size:10px;white-space:nowrap}
table.mx td{text-align:center;padding:0;border:1px solid #fff}
footer{margin-top:32px;padding-top:14px;border-top:1px solid #e5e5e0;font-size:12px;color:#8a8a84}
.hbars{display:flex;align-items:flex-end;gap:1px;height:120px;overflow-x:auto;margin-top:10px}
.hbars .b{flex:0 0 auto;width:8px;background:#7f77dd;border-radius:2px 2px 0 0}
.hbars .b:hover{background:#5a52c4}
.heat td{padding:0;border:1px solid #fff}
.heat td.ht{height:22px;min-width:26px}
.heat th{background:#f5f5f2;font-size:10px;padding:3px 4px;white-space:nowrap}
.heat th.rowh,.heat th.rowname{text-align:right;white-space:nowrap;background:#fafaf7;color:#3a3a36;font-weight:500}
.rowname{font-size:11px}
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

/* ---------- 主题配色 ---------- */
// vivid 14 色：由 references/palette_vivid.py 生成（Oklab 高彩度候选池 +
// Machado 2009 三类色觉缺陷模拟 + CIEDE2000 选色）。
// 目标 = 「在保证色觉安全的前提下尽量鲜艳」：
//   · 平均彩度 0.1916（Oklab），是旧 Okabe-Ito 补色板 0.1216 的 1.58×；
//   · 图例相邻色在 4 种视觉类型下 min ΔE00 = 9.44（可辨）；
//   · 白底对比度 ≥ 2.35:1（配合节点白色光环 + 深色描边，节点在白底上清晰）。
// 对比说明：手工「彩虹」14 色（相邻色相差 ~26°）在色觉模拟下相邻对会完全重合
// （min ΔE00 = 0），故不采用。
// 14 色仍无法在 4 种色觉类型下全部两两可分 → 颜色只是第一通道，
// 图例文字 / 侧栏列表 / 悬停提示 / 跨簇描边构成冗余编码。
const PAL = ['#CC4AD9','#1CBF31','#E97E27','#7290FB','#A30148','#8247EA','#98B222',
             '#D71B0A','#7C0E5F','#6D59FB','#CB163E','#581278','#37830D','#74BC12'];
const NEUTRAL = '#9a9a92';           // 无主题归属（灰，与所有鲜艳色截然区分）
const HL = '#111111';                // 选中节点（近黑描边+白色光环，见节点绘制）
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
      hasXY = true;
    }
  }catch(e){ hasXY = false; }
}
if(!hasXY && N[0] && N[0].x !== undefined && !net.pos_encoded){
  hasXY = true;                       // x/y 已由 build_network 直接写入
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

// 视图变换（缩放/平移）
let vx=0, vy=0, vk=1, vInit=false;
const maxDeg = Math.max(...N.map(d=>d.degree||1));
// 节点半径：按度数开方缩放，并钳制到 [2.2, 11]，保证小节点可读、大 hub 不爆屏
function radiusOf(d){ return Math.max(2.2, Math.min(11,
    2 + Math.sqrt(d.degree||1)/Math.sqrt(maxDeg)*7)); }
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

/* ---------- 节点手动微调（v0.3.1 新增）----------
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
// bounds需含用户偏移，否则拖过的节点可能被 fitView 裁到视口外
function bounds(){
  let x0=1e18,y0=1e18,x1=-1e18,y1=-1e18;
  N.forEach(d=>{
    const X=d.px+(d.ox||0), Y=d.py+(d.oy||0);
    if(X<x0)x0=X; if(X>x1)x1=X; if(Y<y0)y0=Y; if(Y>y1)y1=Y;
  });
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
function fitView(){
  const b = bounds(), w = cv.clientWidth, h = cv.clientHeight;
  const bw = Math.max(1, b.x1-b.x0), bh = Math.max(1, b.y1-b.y0);
  vk = Math.min(w/(bw*1.06), h/(bh*1.06));
  vx = w/2 - (b.x0+b.x1)/2*vk;
  vy = h/2 - (b.y0+b.y1)/2*vk;
  vInit = true;
  vkFit = vk;                            // 记录首屏缩放，作为标签预算基准
}

/* ---------- 标签策略（参考 VOSviewer）----------
   1094 个标签全画必然糊成一团。只给高权重节点画，缩放时才显示更多。
   预算 = f(相对首屏的缩放倍数)：首屏 26 个，放大后最多约 150 个。
   ⚠️ 关键：候选必须取「当前视口内」的节点按 degree 排名，
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
  const w = cv.clientWidth, h = cv.clientHeight;
  const dpr = window.devicePixelRatio || 1;
  if(cv.width !== Math.round(w*dpr) || cv.height !== Math.round(h*dpr)){
    cv.width = Math.round(w*dpr); cv.height = Math.round(h*dpr);
  }
  if(!vInit) fitView();
  ctx.setTransform(dpr,0,0,dpr,0,0);
  if(viewMode==='density'){ drawDensity(); return; }
  ctx.fillStyle = '#ffffff'; ctx.fillRect(0,0,w,h);

  const dimAll = (sel!==null) || (focusTopic!==null);

  /* --- 边：按主题分桶批量 stroke ---
     性能关键：不用 setLineDash 逐条设置（10672 次状态切换极慢），
     而是按「同主题实色 / 跨主题浅灰」分成两桶，每桶一次 beginPath+stroke。 */
  const sameB = [], crossB = [];
  for(let i=0;i<E.length;i++){
    const e = E[i], a = N[idx[e.s]], b = N[idx[e.t]];
    if(!a||!b) continue;
    if(!visible(a)||!visible(b)) continue;
    if(sel!==null && e.s!==sel && e.t!==sel) continue;
    (a.pc!=null && a.pc===b.pc
      ? sameB : crossB).push(a,b);
  }
  // 跨主题边：浅灰实线（不用虚线 —— 10672 条边逐条设 lineDash 会拖垮帧率）
  if(crossB.length){
    ctx.beginPath();
    for(let i=0;i<crossB.length;i+=2){
      const a=crossB[i], b=crossB[i+1];
      ctx.moveTo(sx(a),sy(a)); ctx.lineTo(sx(b),sy(b));
    }
    ctx.strokeStyle = dimAll ? 'rgba(150,150,145,0.10)' : 'rgba(150,150,145,0.20)';
    ctx.lineWidth = 0.5; ctx.stroke();
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
    // 白色光环：在白底上把节点与其下方连线隔开，节点更「跳」出来
    ctx.beginPath(); ctx.arc(X,Y,r+1.1,0,6.2832);
    ctx.fillStyle = 'rgba(255,255,255,0.9)'; ctx.fill();
    // 主体填充（选中时保留主题色，靠描边区分；悬停加深）
    ctx.beginPath(); ctx.arc(X,Y,r,0,6.2832);
    ctx.fillStyle = isHov ? '#00000022' : nodeColor(d);
    if(isHov) ctx.fillStyle = nodeColor(d);
    ctx.fill();
    // 细深色描边：增强边缘锐度（白底上鲜艳色块更立体）
    ctx.lineWidth = 0.7; ctx.strokeStyle = 'rgba(20,20,20,0.35)'; ctx.stroke();
    // 选中 / 悬停：加粗描边环（形状通道，天然色盲可辨）
    if(isSel){
      ctx.lineWidth = 2.6; ctx.strokeStyle = HL; ctx.stroke();
      ctx.lineWidth = 1.0; ctx.strokeStyle = '#ffffff'; ctx.stroke();
    } else if(isHov){
      ctx.lineWidth = 1.6; ctx.strokeStyle = HL; ctx.stroke();
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
      ctx.lineWidth = 3.5; ctx.strokeStyle = 'rgba(255,255,255,0.92)';
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
    // 白描边保证压在边上也读得清
    ctx.lineWidth = 3; ctx.strokeStyle = 'rgba(255,255,255,0.9)';
    ctx.strokeText(d.id, X, ty);
    ctx.fillStyle = isSel ? '#8a2c10' : '#2c2c2a';
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
  /* ⚠️ 安全：这里**不能**用 innerHTML 拼字符串。
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
  ' 边 · 悬停查看详情 · 滚轮缩放 · 拖空白平移 · 拖节点可手动微调位置 · '+
  '点击高亮邻居 · 双击复位'+(moved.size?'（已移动 '+moved.size+' 个节点）':'')+
  ' · 点击图例只看某主题';

/* ---------- 事件 ----------
   三种交互互斥，靠 mousedown 时的命中测试区分：
     · 命中节点 → 拖动该节点（+邻居跟随）
     · 命中空白 → 平移整个视口
     · 滚轮     → 以光标为锚点缩放
   拖动阈值 3px：超过才算拖动，否则算「点击」（保留点击高亮邻居的既有行为）。 */
function nbrsOf(id){
  const s = new Set();
  for(const e2 of E){
    if(e2.s===id) s.add(e2.t);
    else if(e2.t===id) s.add(e2.s);
  }
  return s;
}
/* ---------- 指针交互（鼠标 / 触摸 / 手写笔统一）----------
   为什么改用 Pointer Events（v0.3.1移动端修复）：
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
let pinchDist=0, pinchMidX=0, pinchMidY=0, pinching=false;
let lastTapT=0, lastTapX=0, lastTapY=0;
const activePointers = new Map();   // 多点触控：pointerId -> [x,y]

function canvasXY(e){
  const r = cv.getBoundingClientRect();
  return [e.clientX - r.left, e.clientY - r.top];
}
function applyDrag(dx, dy){
  if(draggingNode){
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
    ptNodeDX = 0; ptNodeDY = 0;
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
  draggingNode = pick(mx,my);
  ptNode = draggingNode;
  if(draggingNode){ ptNodeNbrs = nbrsOf(draggingNode); ptNodeDX=0; ptNodeDY=0; }
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
  if(Math.abs(dx)+Math.abs(dy) > 3) ptMoved = true;
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
cv.addEventListener('wheel', e=>{
  e.preventDefault();
  const r = cv.getBoundingClientRect();
  const mx = e.clientX-r.left, my = e.clientY-r.top;
  const f = e.deltaY<0 ? 1.12 : 1/1.12;
  const nk = Math.max(0.12, Math.min(9, vk*f));
  // 以光标为锚点缩放
  vx = mx - (mx-vx)*(nk/vk); vy = my - (my-vy)*(nk/vk);
  vk = nk; invalidate();
}, {passive:false});
// 双击：优先复位被移动的节点；若无改动则复位视口
cv.addEventListener('dblclick', ()=>{
  if(moved.size){ resetLayout(); }
  else { vInit=false; invalidate(); }
});

/* ---------- 图例：点击只看该主题 ---------- */
/* ---------- 视图模式：主题着色 / 时间叠加 / 密度 ---------- ----------
   v0.3.1 新增。此前只有「按主题着色」一种模式，但文献计量读图常问两类问题：
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
   ⚠️ 口径说明：这是簇级年份分布的加权近似，**不是**该关键词自身的
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
/* 年份 → 颜色（蓝→绿→黄，与 VOSviewer overlay 一致） */
function yearColor(y){
  if(y===null || y===undefined || yrHi<=yrLo) return '#9a9a92';
  const t = Math.max(0, Math.min(1, (y-yrLo)/(yrHi-yrLo)));
  // 三段插值：蓝(0) → 青(0.5) → 黄(1)
  const stops = [[43,72,140],[64,196,164],[250,232,110]];
  const seg = t<0.5 ? 0 : 1;
  const lt = t<0.5 ? t*2 : (t-0.5)*2;
  const a = stops[seg], b = stops[seg+1];
  return `rgb(${Math.round(a[0]+(b[0]-a[0])*lt)},${Math.round(a[1]+(b[1]-a[1])*lt)},${Math.round(a[2]+(b[2]-a[2])*lt)})`;
}
function nodeColor(d){
  if(viewMode==='topic') return colorOf(d);
  if(viewMode==='overlay') return yearColor(meanYear(d));
  return '#8a8a84';         // density 模式不画实心节点
}
function setViewMode(m){
  viewMode = m;
  document.querySelectorAll('.viewbtn').forEach(b=>
    b.classList.toggle('on', b.dataset.view===m));
  const lg = document.getElementById('legendArea');
  if(lg) lg.style.display = (m==='topic') ? '' : 'none';
  const ov = document.getElementById('overlayLegend');
  if(ov) ov.style.display = (m==='overlay') ? '' : 'none';
  vInit = false;              // 切换模式后重新贴合，避免残留旧视口
  invalidate();
}

/* ---------- 密度视图 ----------
   借鉴 VOSviewer 的 density visualization：节点密处形成热区。
   实现：对每个可见节点画径向渐变叠加，additive 混合出连续密度面。
   不用外部库（保持自包含单文件），纯 Canvas，1081 节点实测流畅。 */
function drawDensity(){
  const w = cv.clientWidth, h = cv.clientHeight;
  ctx.globalCompositeOperation = 'source-over';
  ctx.fillStyle = '#fff'; ctx.fillRect(0,0,w,h);
  ctx.globalCompositeOperation = 'lighter';
  for(const d of N){
    if(!visible(d)) continue;
    const X = sx(d), Y = sy(d);
    if(X<-60||X>w+60||Y<-60||Y>h+60) continue;
    const R = 46;
    const g = ctx.createRadialGradient(X,Y,0,X,Y,R);
    const c = colorOf(d);
    g.addColorStop(0, c+'55');
    g.addColorStop(1, c+'00');
    ctx.fillStyle = g;
    ctx.beginPath(); ctx.arc(X,Y,R,0,6.2832); ctx.fill();
  }
  ctx.globalCompositeOperation = 'source-over';
}

/* ---------- 导出（PNG / SVG）—— 论文配图刚需 ----------
   此前报告只能截图，无法直接得到可投稿的图片文件。
   PNG  : 白底、按当前视口与 2x 像素密度导出（线稿清晰，投稿够用）。
   SVG  : 矢量导出，节点=圆、边=线、标签=text，可无限放大不失真，
          直接进Illustrator/Inkscape 排版。默认只导节点与标签，
          避免 8695 条边把文件撑到几十 MB。 */
function exportPNG(scale){
  scale = scale || 2;
  const w = cv.clientWidth, h = cv.clientHeight;
  const oldW = cv.width, oldH = cv.height, oldStyle = cv.style.cssText;
  const ov = document.createElement('canvas');
  ov.width = Math.round(w*scale); ov.height = Math.round(h*scale);
  const o = ov.getContext('2d');
  o.setTransform(scale,0,0,scale,0,0);
  o.fillStyle = '#fff'; o.fillRect(0,0,w,h);
  o.drawImage(cv, 0, 0, w, h);
  ov.toBlob(b=>{
    const a = document.createElement('a');
    a.href = URL.createObjectURL(b);
    a.download = 'cooccurrence-network.png';
    a.click();
    setTimeout(()=>URL.revokeObjectURL(a.href), 1000);
  });
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
      const c = same ? PAL[cidx.get(a.pc) ?? 0] : '#999';
      ln.setAttribute('stroke', c);
      ln.setAttribute('stroke-opacity', same ? '0.35' : '0.15');
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
  const blob = new Blob(
    ['<?xml version="1.0" encoding="UTF-8"?>\n'+new XMLSerializer().serializeToString(svg)],
    {type:'image/svg+xml'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'cooccurrence-network.svg';
  a.click();
  setTimeout(()=>URL.revokeObjectURL(a.href), 1000);
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
  }else if(k==='Escape'){                   // 取消选中/主题聚焦
    sel=null; nbrs=new Set(); focusTopic=null;
    document.querySelectorAll('.lg-item').forEach(x=>x.classList.remove('on'));
    renderSide(); invalidate(); e.preventDefault();
  }
});

/* ---------- 复位按钮 ---------- */
const rst = document.getElementById('resetLayout');
if(rst){ rst.onclick = ()=>{ resetLayout(); tip(null); }; }
document.querySelectorAll('.viewbtn').forEach(b=>{
  b.onclick = ()=> setViewMode(b.dataset.view);
});
const bpng = document.getElementById('exportPNG');
if(bpng){ bpng.onclick = ()=>{ draw(); exportPNG(2); }; }
const bsvg = document.getElementById('exportSVG');
if(bsvg){ bsvg.onclick = ()=>{ draw(); exportSVG(false); }; }

document.querySelectorAll('.lg-item').forEach(el=>{
  el.onclick = ()=>{
    const c = el.dataset.cid;
    const v = c==='__none__' ? null : parseInt(c,10);
    focusTopic = (focusTopic===v && c!=='__none__') ? null : v;
    document.querySelectorAll('.lg-item').forEach(x=>
      x.classList.toggle('on', x.dataset.cid===c && focusTopic!==null));
    sel=null; nbrs=new Set();
    renderSide();
    invalidate();
  };
});

/* ---------- 侧栏：该主题的关键词列表（按 degree 排序） ----------
   ⚠️ 安全：此处**曾**是零点击 DOM XSS —— 用 innerHTML 拼
   `<span class="kw" data-id="${d.id}">${d.id}<small>...`，
   关键词来自外部导入属不可信输入；首屏即执行 renderSide()，
   实测关键词 `<img src=x onerror=alert(1)>` 打开页面立即触发，
   且含引号的关键词会截断 data-id 属性导致节点身份丢失。
   现改为**纯 DOM 构建**：textContent 天然转义，
   data-id 用 setAttribute（浏览器自动转义属性值）。 */
function kwNode(d){
  const s = document.createElement('span');
  s.className = 'kw';
  s.dataset.id = String(d.id);              // setAttribute：属性值自动转义
  const i = document.createElement('i');
  i.style.background = colorOf(d);
  const t = document.createElement('span');  // 关键词文本
  t.textContent = String(d.id);
  const sm = document.createElement('small');
  sm.textContent = String(d.degree);
  s.appendChild(i); s.appendChild(t); s.appendChild(sm);
  return s;
}
function renderSide(){
  const el = document.getElementById('side');
  const head = document.getElementById('sidehead');
  if(!el) return;
  el.textContent = '';                      // 清空，不复用 innerHTML
  let list;
  if(focusTopic===null){
    head.textContent = '全部主题 · Top 40 关键词（按连接数）';
    list = N.filter(d=>d.pc!=null)
             .sort((a,b)=>(b.degree||0)-(a.degree||0)).slice(0,40);
  }else{
    const m = META[focusTopic]||{};
    head.textContent = '主题'+focusTopic+'（'+(m.size||'?')+' 篇）· 关键词 '+
      N.filter(d=>d.pc===focusTopic).length+' 个';
    list = N.filter(d=>d.pc===focusTopic)
              .sort((a,b)=>(b.degree||0)-(a.degree||0)).slice(0,80);
  }
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
document.querySelectorAll('.chip[data-off]').forEach(c=>{
  c.onclick=()=>{ const id=c.dataset.off;
    if(hidden.has(id)){hidden.delete(id);c.classList.remove('off');}
    else{hidden.add(id);c.classList.add('off');}
    invalidate(); };
});

/* ---------- 渲染调度（按需重绘，非常驻 60fps）----------
   ⚠️ 不可写成无条件 rAF 死循环：10672 条边每帧重绘会持续占用 CPU/GPU，
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
dirty.v = true; schedule();          // 首帧
window.addEventListener('resize', ()=>{ vInit=false; invalidate(); });

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
  focus(c){ focusTopic = c; sel=null; nbrs=new Set(); invalidate(); },
  hover(id){ hov = id; tip(id); invalidate(); },
  state(){ return {sel, focusTopic, nbrs:nbrs.size, labels:lastLabels, zoom:vk}; },
  nodeScreenXY(id){ const d=byId[id]; return d?[sx(d),sy(d)]:null; },
  topIds(n){ return byDeg.slice(0,n).map(i=>N[i].id); },
};
})();
"""


def build_html(topics, network=None, evolution=None, reading=None,
               dup=None, age=None, author_topic=None, sna=None,
               bursts=None) -> str:
    d = topics
    cov = d["coverage"]
    diag = d["diagnostics"]
    clusters = d["clusters"]
    g = gini2([c["size"] for c in clusters])
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
    cards = []
    for c in clusters:
        z, e = c["lang_zh"], c["lang_en"]
        tot = z + e or 1
        rp = z / tot
        if rp == 0 or rp == 1:
            cls = "zh" if rp > .5 else "en"
            lbl = "中文" if rp > .5 else "英文"
        else:
            cls, lbl = "mixed", "跨语"
        terms = "".join(f'<span class="chip" style="cursor:default">{esc(t)}</span>'
                        for t in c["top_terms"][:12])
        yr = c.get("year_range")
        tname, tsrc = label_topic(c.get("top_terms", []))
        is_nt = (tname == NON_TOPIC_KEY)
        shown = tname or f"主题 {c['cluster_id']}"
        tag_html = ("" if not tname else
            f' <span class="tag" style="background:#e1f5ee;color:#0f6e56">{shown}</span>'
            + (' <span class="tag" style="background:#f1efe8;color:#5f5e5a">非研究主题</span>'
               if is_nt else ''))
        cards.append(f"""<div class="card">
<div style="display:flex;justify-content:space-between;align-items:baseline;gap:10px">
<div><b>{tag_html}</b>
 <span class="tag {cls}">{lbl}</span>
 <span class="tag" style="background:#f0f0ec;color:#55554f">{c['size']} 篇 · {c['pct']}%</span>
 <span class="tag" style="background:#f0f0ec;color:#55554f">{yr[0]}–{yr[1]}</span></div>
</div>
<div class="terms">中 {z} / 英 {e}</div>
<div class="bar"><i style="width:{c['pct'] * 4:.1f}%;background:#7f77dd"></i></div>
<div class="chips">{terms}</div></div>""")

    # ── 演化矩阵 ──
    matrix_html = ""
    if evolution:
        years = [y for y in evolution.get("years", [])]
        cl = evolution.get("clusters", [])
        keep_years = [y for y in years if y >= max(1968, cov["year_min"])]
        if len(keep_years) > 42:
            keep_years = [y for y in years if y >= max(1970, years[-1] - 32)]
        mx = {c["cluster_id"]: c["counts"] for c in cl}
        vmax = max((mx.get(c["cluster_id"], {}).get(str(y), 0)
                    for c in clusters for y in keep_years), default=1) or 1
        hdr = "".join(f"<th>{y}</th>" for y in keep_years)
        rows = []
        for c in clusters:
            tds = []
            for y in keep_years:
                v = mx.get(c["cluster_id"], {}).get(str(y), 0)
                a = (v / vmax) ** .6 if v else 0
                bg = f"rgba(127,119,221,{a:.3f})" if v else "transparent"
                tds.append(f'<td style="background:{bg}" title="{c["cluster_id"]}·{y}年: {v} 篇"></td>')
            rows.append(f"<tr><th style='text-align:right'>{c['cluster_id']}</th>{''.join(tds)}</tr>")
        matrix_html = f"""<div class="card matrix"><table class="mx"><tr><th></th>{hdr}</tr>
{''.join(rows)}</table>
<div class="legend" style="margin-top:8px">颜色深浅 = 该主题该年文献数（相对最大值）。
**旧年份样本量不足**（2019 年前每年约 85–155 篇），趋势解读需谨慎。</div></div>"""

    # ── 网络数据 ──
    net_js = ""
    net_card = ""
    if network:
        N, E = network["nodes"], network["edges"]
        attr = network.get("stats", {}).get("topic_attribution", {})
        cmeta = network.get("cluster_meta", {}) or {}
        themed = bool(attr.get("enabled"))

        top = sorted(N, key=lambda x: -x["degree"])[:24]
        chips = "".join(
            f'<span class="chip" data-off="{esc(n["id"])}">{esc(n["id"])} '
            f'<small>({n["degree"]})</small></span>' for n in top)

        # 图例：每个主题一个可点击色块，括号内是该主题的关键词数
        if themed:
            cnt = Counter(n.get("primary_cluster") for n in N
                          if n.get("primary_cluster") is not None)
            lg_items, lg_js = [], []
            for cid in sorted(cnt, key=lambda c: -cnt[c]):
                m = cmeta.get(str(cid), cmeta.get(cid, {})) or {}
                terms = "、".join((m.get("top_terms") or [])[:3])
                lg_items.append(
                    f'<span class="lg-item" data-cid="{cid}" title="{esc(terms)}">'
                    f'<span class="sw" data-sw="{cid}"></span>'
                    f'主题{cid}<span class="n">{cnt[cid]}</span></span>')
                lg_js.append({"c": cid, "n": cnt[cid]})
            none_cnt = sum(1 for n in N if n.get("primary_cluster") is None)
            if none_cnt:
                lg_items.append(
                    f'<span class="lg-item" data-cid="__none__">'
                    f'<span class="sw" style="background:#9a9a92"></span>'
                    f'未归属<span class="n">{none_cnt}</span></span>')
            legend_html = "".join(lg_items)

            attr_note = (
                f'<div style="font-size:12px;color:#6b6b66;margin-top:8px">'
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
                         '⚠️ 未接入主题聚类（build_network.py 未传 --topics），'
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
        # 坑（两处）：
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
        # ⚠️ 安全：文献标题/关键词/作者均来自外部导入（不可信输入）。
        # 若用裸 json.dumps 内联，题名中的 "</script>" 可提前闭合 <script> 标签
        # → 任意脚本注入。esc_json 转义 < > & 与 U+2028/9 封死该路径。
        net_js = (
            f"window.__NET__={esc_json(payload)};"
            f"window.__CMETA__={esc_json({str(k): v for k, v in (cmeta or {}).items()})};"
            f"window.__CPAL__={esc_json(lg_js)};")

        net_card = f"""<div class="card">
<div class="netrow"><span id="tinfo" style="font-size:12px;color:#3a3a36"></span>
<span class="perf" id="perf"></span>
<span class="toolbar">
<button class="viewbtn on" data-view="topic" type="button" title="按研究主题着色（快捷键 1）">主题着色</button>
<button class="viewbtn" data-view="overlay" type="button" title="按平均发表年着色，蓝=早 绿=中 黄=晚（快捷键 2）">时间叠加</button>
<button class="viewbtn" data-view="density" type="button" title="密度视图，节点密集处显热区（快捷键 3）">密度视图</button>
<button id="exportPNG" class="rstbtn" type="button" title="按当前视口导出 2x 高清 PNG">导出 PNG</button>
<button id="exportSVG" class="rstbtn" type="button" title="导出矢量 SVG（仅节点与标签，文件小、可无限放大）">导出 SVG</button>
</span></div>
<div class="lg" id="legendArea">{legend_html}</div>
<div class="lg" id="overlayLegend" style="display:none">
<span style="font-size:11px;color:#55554f;align-self:center;margin-right:6px">平均发表年</span>
<span class="yrbar"></span>
<span class="yrlab">{yr_lo if yr_lo is not None else '—'}</span>
<span style="font-size:11px;color:#8a8a84;margin:0 4px">→</span>
<span class="yrlab">{yr_hi if yr_hi is not None else '—'}</span>
<span style="font-size:11px;color:#8a8a84;margin-left:8px">（蓝=早期概念，黄=近期概念；口径为所属主题的年份重心近似）</span>
<span id="overlayWarn" style="font-size:11px;color:#8a6d3b;margin-left:8px">{'' if yr_lo is not None else '⚠️ 未接入演化数据（缺 --evolution），无法按年着色'}</span>
</div>
<canvas id="net" height="520" style="margin-top:10px"></canvas>
{attr_note}
<div class="side"><h4 id="sidehead"></h4><div class="kws" id="side"></div></div>
<div style="margin-top:10px;font-size:12px;color:#6b6b66;display:flex;align-items:center;gap:10px;flex-wrap:wrap">
<span>按度数排序的关键词（点击可灰显/恢复）：</span>
<button id="resetLayout" class="rstbtn" type="button"
 title="清除所有手动拖动的节点位置，回到算法原始布局">复位节点位置</button></div>
<div class="chips">{chips}</div>
<div class="legend">
<span><span class="dot" style="background:#9a9a92"></span>节点大小 = 连接数</span>
<span><span class="dot" style="background:#111111"></span>选中节点</span>
<span>描边 = 桥接词（横跨多个主题）</span>
<span>浅灰连线 = 跨主题边</span></div>
<div class="legend" style="margin-top:4px">
<span>操作：滚轮或 <b>+/-</b> 缩放（0.12×–9×） · 拖空白平移 · <b>拖节点可手动微调位置</b> · 点击高亮邻居 · 双击或 <b>0</b> 复位视口 · <b>R</b> 复位节点 · <b>Esc</b> 取消选中 · <b>1/2/3</b> 切换视图</span></div></div>"""

    # ── R / igraph 交叉验证（可选，sna_r.py 产物）──
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
        for nd_ in (sna.get("top_central") or [])[:12]:
            rows.append(
                f"<tr><td>{esc(str(nd_.get('node','')))}</td>"
                f"<td>{esc(str(nd_.get('degree','')))}</td>"
                f"<td>{esc(str(nd_.get('betweenness','')))}</td>"
                f"<td>{esc(str(nd_.get('closeness','')))}</td>"
                f"<td>{esc(str(nd_.get('eigen','')))}</td></tr>")
        tbl = ("<table class='mx'><tr><th>关键词</th><th>度</th><th>介数</th>"
               "<th>接近</th><th>特征向量</th></tr>" + "".join(rows) + "</table>") if rows else ""
        cv = sna.get("cross_validation") or {}
        ari, nmi = cv.get("ari_vs_nmf"), cv.get("nmi_vs_nmf")
        if is_r and ari is not None:
            def _f(x):
                return f"{x:.3f}" if isinstance(x, (int, float)) else "—"
            judge = ("两种方法**看的是不同结构**（共现图社区 vs 全文词袋主题），"
                     "一致性偏低属预期结果，不应据此否定任一方法。"
                     if (ari < 0.3) else
                     "两种方法给出了大体一致的分组结构，可互为佐证。")
            cv_html = (f"<p>与 NMF 主题簇的一致性：<b>ARI = {_f(ari)}</b>、"
                       f"<b>NMI = {_f(nmi)}</b>。{esc(judge)}</p>")
        else:
            cv_html = ("<p>未做 R↔NMF 一致性比较（R 或 igraph 不可用）。"
                       "启用 R 路径后可获得「共现社群 vs 研究主题」的独立交叉验证。</p>")
        hint = ""
        if not is_r and sna.get("hint"):
            hint = (f"<p>启用 R 路径：<code>{esc(sna['hint'])}</code></p>")
        sna_html = f"""<h2>R / igraph 交叉验证（可选）</h2>
<div class="card"><div class="hd">{badge}
<span class="sub">{ver}</span></div>
<div class="kpis">{kpi_s_html}</div>
{cv_html}{hint}
{tbl}
<p class="note">模块度 Q 越高表示社区结构越清晰；介数高的关键词是跨社群的「桥」，
与共现图中的桥接词（次色描边）互为印证。</p>
</div>"""

    # ── 阅读状态（未读/待读清单）──
    if reading:
        r = reading.get("reading", {})
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
        rows = "".join(
            f"<tr><td>{esc(s.get('title'))}</td><td>{esc(s.get('year') or '')}</td>"
            f"<td>{esc(s.get('journal'))}</td>"
            f"<td>{'✅' if s.get('has_pdf') else '—'}</td></tr>"
            for s in samples)
        reading_html = f"""<h2>阅读状态（未读 / 待读清单）</h2>
<div class="grid g4" style="margin-bottom:12px">{rk}</div>
<div class="card">
<div style="font-size:12px;color:#6b6b66;margin-bottom:10px">
约定：read_status='1' 为已读；'0'/空 计为未读/待读（按 EndNote 默认约定）。{esc(r.get('convention',''))}</div>
<div style="font-size:13px;color:#6b6b66;margin-bottom:8px">待读样本（按年份降序，前 {len(samples)} 篇）：</div>
<table><tr><th>标题</th><th>年份</th><th>期刊</th><th>PDF</th></tr>{rows}</table>
<div style="font-size:12px;color:#8a8a84;margin-top:10px">完整待读清单可经 reading_status.py --csv 导出。</div>
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
            f"<tr><td>{esc(o.get('title'))}</td><td>{esc(o.get('year') or '')}</td>"
            f"<td>{esc(o.get('journal'))}</td></tr>" for o in oldest[:10])
        awarns = "".join(f"<li>{esc(w)}</li>" for w in age.get("warnings", []))
        age_html = f"""<h2>文献时效性预警</h2>
<div class="grid g4" style="margin-bottom:12px">{ak}</div>
<div class="card">
<div style="font-size:13px;color:#6b6b66;margin-bottom:6px">年份分布（柱高=文献数；基准年={ys.get('max_year','?')}）：</div>
<div class="hbars">{bars}</div>
<div style="display:flex;justify-content:space-between;font-size:9px;color:#9a9a92;margin-top:2px">
<span>{ys.get('min_year','')}</span><span>{ys.get('max_year','')}</span></div>
<ul style="margin-top:10px;font-size:13px">{awarns}</ul>
<div style="font-size:13px;color:#6b6b66;margin:10px 0 8px">最旧文献样本（前 10）：</div>
<table><tr><th>标题</th><th>年份</th><th>期刊</th></tr>{orows}</table>
<div style="font-size:12px;color:#8a8a84;margin-top:10px">⚠️ 时效性以库内最新年份为基准，而非系统时钟。</div>
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
        grows = "".join(
            f"<tr><td>{esc(g.get('type'))}</td><td>{g.get('size')}</td>"
            f"<td>{'；'.join(esc(t) for t in g.get('sample_titles', [])[:3])}</td></tr>"
            for g in sg)
        dwarns = "".join(f"<li>{esc(w)}</li>" for w in dup.get("warnings", []))
        dup_html = f"""<h2>重复 / 近似重复检测</h2>
<div class="grid g4" style="margin-bottom:12px">{dk}</div>
<div class="card">
<ul style="font-size:13px;margin-bottom:10px">{dwarns}</ul>
<div style="font-size:13px;color:#6b6b66;margin-bottom:6px">重复组样本（前 {len(sg)} 组）：</div>
<table><tr><th>类型</th><th>篇数</th><th>标题样本</th></tr>{grows}</table>
<div style="font-size:12px;color:#8a8a84;margin-top:10px">⚠️ 近似检测仅基于本地元数据（标题/DOI/期刊/年份），合并前需人工核对是否为版本/预印本差异。</div>
</div>"""

    # ── 主题 × 作者矩阵 / 核心作者 ──
    if author_topic:
        at = author_topic
        cnt = at.get("counts", {})
        cols = at.get("matrix", {}).get("col_cluster_ids", [])
        rows = at.get("matrix", {}).get("rows", [])
        maxv = max((max((row.get(str(c), 0) for c in cols), default=0)
                    for row in rows), default=0) or 1
        head = "".join(f"<th>c{c}</th>" for c in cols)
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
        authormatrix_html = f"""<h2>主题 × 作者矩阵 / 核心作者</h2>
<div class="card">
<div style="font-size:13px;color:#6b6b66;margin-bottom:6px">识别作者 {cnt.get('distinct_authors', 0):,} 位（覆盖 {cnt.get('author_coverage_pct', 0)}% 文献）。
下表为全局出现最多的前 {len(rows)} 位作者在各主题簇的文献数（颜色越深越多）：</div>
<div class="matrix" style="overflow-x:auto"><table class="mx heat">
<tr><th class="rowh rowname"></th>{head}</tr>{body}</table></div>
<div style="font-size:13px;color:#6b6b66;margin:12px 0 6px">全局核心作者（Top 15）：</div>
<ul style="columns:2;font-size:13px;list-style:none;padding:0">{core_li}</ul>
<div style="font-size:12px;color:#8a8a84;margin-top:8px">作者归一为 surname|initials（同名靠缩写区分）；未做跨库消歧。</div>
</div>"""

    # K 判定说明（让 K 的来源可追溯，而非黑盒）
    kdec = diag.get("k_decision")
    kcard = ""
    if kdec:
        curve = kdec.get("curve", [])
        if curve:
            cells = "".join(
                f'<div style="flex:1;min-width:52px;text-align:center">'
                f'<div style="font-size:11px;color:#88887f">K={c["k"]}</div>'
                f'<div style="height:34px;display:flex;align-items:flex-end;justify-content:center">'
                f'<div style="width:70%;background:{"#1D9E75" if c["ok"] else "#D3D1C7"};'
                f'height:{min(34, max(3, c["min_pct"] * 5.5)):.0f}px"></div></div>'
                f'<div style="font-size:10px;color:#6b6b66">{c["min_pct"]}%</div></div>'
                for c in curve)
            src = ("按规则自动判定" if d["params"].get("k_source", "").startswith("auto")
                   else "你手动指定")
            kcard = f"""<div class="card">
<div style="display:flex;justify-content:space-between;align-items:baseline">
<b>主题数 K = {d['params']['k']}</b><span style="font-size:12px;color:#6b6b66">{src}</span></div>
<div style="font-size:12px;color:#6b6b66;margin-top:4px">
判定规则：每个主题至少占全库 <b>{kdec.get('threshold_pct', 3.0)}%</b>，
否则不足以支撑一个可命名、可综述的主题单元。</div>
<div style="display:flex;gap:3px;margin-top:10px;align-items:flex-end">{cells}</div>
{'<div style="font-size:12px;color:#8a6d3b;margin-top:8px">⚠️ ' + esc(kdec["note"]) + '</div>' if kdec.get('note') else ''}
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
            hist = b.get("year_hist", {})
            spark = "".join(
                f'<span class="bar" style="height:{max(1, int(v / max(hist.values()) * 100))}%" '
                f'title="{y}: {v}"></span>' for y, v in hist.items() if v)
            brows.append(
                f"<tr><td>{esc(str(b.get('keyword','')))}</td>"
                f"<td class='num'>{b.get('peak_year')}</td>"
                f"<td class='num'>{b.get('peak_df')}</td>"
                f"<td class='num'>{b.get('baseline_mean')}</td>"
                f"<td class='num'>{b.get('burst_ratio')}</td>"
                f"<td class='num'><b>{b.get('strength')}</b></td>"
                f"<td class='num'>{esc(str(b.get('confidence','')))}</td>"
                f"<td><div class='spark'>{spark}</div></td></tr>")
        tbl = ("<table class='mx'><tr><th>关键词</th><th>峰值年</th><th>峰值 df</th>"
               "<th>基线均值</th><th>突现倍数</th><th>强度</th>"
               "<th>置信</th><th>年度分布</th></tr>"
               + "".join(brows) + "</table>") if brows else ""
        bkpi = "".join(
            f'<div class="kpi"><div class="l">{esc(a)}</div><div class="v">{esc(b)}</div></div>'
            for a, b in [
                ("突现候选词", str(len(bl))),
                ("窗口半径", f"±{par.get('window', '?')} 年"),
                ("最低频次门槛", str(par.get("min_total", "?"))),
                ("缺年份文献", f"{covb.get('missing_year_pct', 0)}%"),
            ])
        bursts_html = f"""<h2>关键词突现检测</h2>
<div class="card"><div class="hd"><span class="tag">keyword burst</span>
<span class="sub">依据关键词出现频次突增</span></div>
<div class="kpis">{bkpi}</div>
{tbl}
<p class="note">⚠️ <b>这是关键词突现（keyword burst），不是引文突现（citation burst）。</b>
CiteSpace 的 citation burst 依赖被引频次突增，需要引文数据；本地 <code>.enl</code> 的
<code>references</code> 字段是占位符，零引文数据，因此本项<b>不可</b>与 CiteSpace 的
citation burst 互相替代。强度 = 突现倍数 × log(1+总频次) 的归一化值，仅用于同库内横向比较。
置信度由基线年份数与词频共同决定；置信度为 <code>low</code> 的条目不应作为结论依据。</p>
</div>"""

    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>EndNote 文献分析报告</title><style>{CSS}</style></head><body><div class="wrap">
<h1>EndNote 文献分析报告</h1>
<div class="sub">{esc(d['library']['name'])} · {cov['total']:,} 篇 · 主题数 {len(clusters)} ·
耗时 {d['timing']['total']}s</div>

{busy_banner}

<div class="notice"><b>这是关键词共现网络，不是引文网络。</b>
本报告的"关系"来自文献关键词的共现，回答"概念之间有什么关联"。
它<b>不是</b>引文网络，无法回答"哪篇文献引用了哪篇"——
因为 EndNote 本地库的引文字段是空占位符，且官方未开放 API，这是物理限制。</div>

<div class="grid g4" style="margin-bottom:16px">{kpi_html}</div>

{kcard}
<h2>数据体检</h2>
<div class="card"><table>
<tr><th>项目</th><th>数量</th><th>说明</th></tr>
<tr><td>有摘要（主语料）</td><td>{cov['tier']['primary_abs']:,}</td><td>参与聚类的首选语料</td></tr>
<tr><td>仅关键词（主语料）</td><td>{cov['tier']['primary_kw']:,}</td><td>关键词网络的独有贡献者</td></tr>
<tr><td>仅标题（降级）</td><td>{cov['tier']['fallback_title']:,}</td><td>用「标题+关键词」兜底参与聚类</td></tr>
<tr><td>零丢弃校验</td><td>{'✅ 成立' if cov['zero_drop_identity'] else '❌ 破裂'}</td>
 <td>主语料 + 降级 = {cov['tier']['primary_abs']+cov['tier']['primary_kw']+cov['tier']['fallback_title']+cov['tier']['empty']:,}
 = {cov['total']:,}</td></tr>
<tr><td>无摘要</td><td>{cov['no_abstract']:,}</td><td>占 {cov['no_abstract']/cov['total']*100:.1f}%</td></tr>
<tr><td>无关键词</td><td>{cov['no_keywords']:,}</td>
 <td>占 {cov['no_keywords']/cov['total']*100:.1f}% —— <b>共现网络只覆盖其余 {cov['keyword_coverage_pct']}% 的文献</b></td></tr>
<tr><td>有 PDF 附件</td><td>{cov['has_pdf']:,}</td><td>用于跳转原文</td></tr>
<tr><td>2015 年前</td><td>{cov['pre_2015']:,}</td>
 <td>演化图已纳入（最早 {cov['year_min']} 年），未做截断</td></tr>
</table>{'<ul style="margin-top:10px;font-size:13px">' + warns + '</ul>' if warns else ''}</div>

{reading_html}{age_html}{dup_html}{bursts_html}

<h2>研究主题（{len(clusters)} 个）</h2>
<div class="legend" style="margin-bottom:10px">
<span><span class="tag zh">中文</span>纯中文主题</span>
<span><span class="tag en">英文</span>纯英文主题</span>
<span><span class="tag mixed">跨语</span>同时含中英文 —— 这是重要发现，非异常</span>
</div>
{''.join(cards)}

<h2>主题 × 年份演化</h2>
{matrix_html}

{authormatrix_html}

<h2>关键词共现网络</h2>
{net_card}

{sna_html}

<footer>
聚类算法 TF-IDF + NMF（init={esc(d['params']['nmf_init'])}，K={d['params']['k']}）；
分词 中英分流（英文按空格、中文 jieba）；停用词 {d['params'].get('stop_words', 376)} 词。<br>
网络口径 normalize_case=lower / df_mode=doc / node_df=5 / min_edge=2 / dedupe=per-doc。<br>
扩展分析：阅读状态（未读清单）/ 重复检测 / 时效性预警 / 主题×作者矩阵 —— 均基于本地元数据，纯 Python 计算。<br>
R 交叉验证为可选路径：R 或 igraph 不可用时自动回退纯 Python，不影响上述结果。<br>
<b>源库全程只读</b>——本工具以SQLite 只读模式访问 .enl，绝不写入。
</footer>
</div>
<script>{net_js}</script>
<script>{JS_NET}</script>
</body></html>"""


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

    规范来源：OBHRM `data-analysis/references/three-line-table.md`
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
        out.append(cap(4, "共现网络社群与主题聚类的一致性（R/igraph 交叉验证）") + f"""
<table class="sx"><thead><tr><th>指标</th><th class="num">数值</th></tr></thead><tbody>
<tr><td>后端</td><td>{esc(str(sna.get('backend')))}</td></tr>
<tr><td>模块度 Q</td><td class="num">{esc(str(sna.get('modularity')))}</td></tr>
<tr><td>社群数</td><td class="num">{len(sna.get('communities') or [])}</td></tr>
<tr><td>ARI（vs 主题簇）</td><td class="num">{esc(str(cv.get('ari_vs_nmf')))}</td></tr>
<tr><td>NMI（vs 主题簇）</td><td class="num">{esc(str(cv.get('nmi_vs_nmf')))}</td></tr>
</tbody></table>""" +
 note("社群由 igraph 的 walktrap 算法在关键词共现图上得到，主题簇由 TF-IDF+NMF 得到，二者方法学不同。",
      "一致性偏低属预期结果，不应据此否定任一方法。",
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
        out.append(cap(5, f"主题 × 时期分布与趋势（分期年份 {trend.get('cut_year')}）") + f"""
<table class="sx"><thead><tr><th>主题</th><th>代表关键词</th>
<th class="num">早期占比(%)</th><th class="num">近期占比(%)</th>
<th class="num">变化(pp)</th><th class="num">近期占比 95%CI</th><th>方向</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table>""" +
 note(f"效应量：Cramér's V = {ef.get('cramers_v')}（{ef.get('cramers_v_level')}），"
      f"η² = {ef.get('eta_squared')}（{ef.get('eta_squared_level')}）。",
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
    ap.add_argument("--sna-r", help="sna_r.py 产出的 sna_r.json（可选，R 交叉验证）")
    ap.add_argument("--sanxian", help="额外输出中文期刊三线表 HTML（可直接粘入 Word）")
    ap.add_argument("--trend", help="trend_effects.py 产出的 trend_effects.json（可选）")
    ap.add_argument("--bursts", help="burst_detection.py 产出的 bursts.json（可选）")
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
        trend = _load(args.trend)
        bursts = _load(args.bursts)
        out = Path(args.out)
        out.write_text(
            build_html(topics, network, evo, reading=reading, dup=dup,
                       age=age, author_topic=author_topic, sna=sna,
                       bursts=bursts),
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
