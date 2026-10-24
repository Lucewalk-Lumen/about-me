#!/usr/bin/env node
/**
 * view_smoke.js —— 报告可视化的视图渲染自检（零依赖）。
 *
 * 为什么需要数值断言而不是调用计数：画布缺陷（NaN 坐标、单区 alpha
 * 过低、密度亮度累积不足）的共同表现是"页面空白但不报错"——
 * 只统计 ctx.arc / fill 的调用次数会把全 NaN 的空白画布判为 PASS。
 *
 * 本测试做**数值断言**：
 *   1) 布局体检：所有节点坐标必须有限（badXY === 0）；
 *   2) 密度视图：真实 putImageData 的像素必须与画布底色形成可辨对比；
 *   3) 年轮视图：必须真的画出年轮圆弧（ringArcs > 0），而不是只画了背景；
 *   4) 任一视图抛异常即 FAIL（异常会中断整段脚本，导致所有视图失效）。
 *
 * 用法：node view_smoke.js <report.html>
 * 退出码：0 = 全部通过；1 = 有视图无法渲染
 */
'use strict';
const fs = require('fs');
const vm = require('vm');

const htmlPath = process.argv[2];
if (!htmlPath) {
  console.error('用法: node view_smoke.js <report.html>');
  process.exit(1);
}
const html = fs.readFileSync(htmlPath, 'utf8');
const blocks = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
if (blocks.length < 2) {
  console.error('报告结构异常：未找到预期的 script 块');
  process.exit(1);
}

/* ── 底色对比阈值的依据 ──
   人眼在正常显示器上大致能分辨 8/255 以上的相邻色块，但把 8/255 当阈值
   等于放过"勉强可见"。这里取 40/255：既能让"深色热核"成立，又不苛求
   色带端点。 */
const MIN_CONTRAST = 40;

/* ---- canvas 桩：记录绘制调用次数 + 捕获真实像素 ---- */
const calls = {};
const touch = k => { calls[k] = (calls[k] || 0) + 1; };
/* 已知的绘制方法：显式列出以保证"被统计到"。
   [!] 但**不能只靠这张表** —— 画布新增一个方法（如 strokeRect）时，
   旧写法会直接抛 "not a function"，把一次正常的功能升级误报成视图失效。
   所以下面用 Proxy 兜底：调用未列出的方法不再抛错，而是记进 unknownCalls，
   测试结束时提示出来（提醒补表），但不判失败。 */
const PAINT = [
  'arc', 'stroke', 'fill', 'beginPath', 'moveTo', 'lineTo', 'closePath',
  'save', 'restore', 'translate', 'scale', 'rotate', 'transform',
  'setTransform', 'resetTransform', 'clip', 'rect', 'setLineDash', 'clearRect',
  'quadraticCurveTo', 'bezierCurveTo', 'ellipse', 'arcTo', 'strokeText',
  'fillText', 'fillRect', 'measureText', 'drawImage', 'strokeRect',
  'roundRect', 'getTransform', 'isPointInPath', 'isPointInStroke',
];
const unknownCalls = new Set();
const rawCtx = {};
for (const k of PAINT) {
  if (k === 'measureText') rawCtx[k] = () => ({ width: 10 });
  else rawCtx[k] = () => touch(k);
}
/* createImageData / putImageData 必须"真"实现：密度图的可见性只能从
   实际写入的像素里验出来，不能靠数调用次数。 */
rawCtx.createRadialGradient = () => { touch('gradient'); return { addColorStop() {} }; };
rawCtx.createLinearGradient = () => { touch('gradient'); return { addColorStop() {} }; };
rawCtx.createConicGradient = () => { touch('gradient'); return { addColorStop() {} }; };
rawCtx.createPattern = () => null;
let lastImage = null;                       // 最近一次 putImageData 的像素
rawCtx.createImageData = (w, h) => ({
  width: w, height: h, data: new Uint8ClampedArray(w * h * 4),
});
rawCtx.putImageData = img => { lastImage = img; touch('putImageData'); };
rawCtx.getImageData = (x, y, w, h) => (lastImage || {
  width: w, height: h, data: new Uint8ClampedArray(w * h * 4),
});
const ctx = new Proxy(rawCtx, {
  get(t, k) {
    if (k in t) return t[k];
    if (typeof k !== 'string') return undefined;
    // 读写属性（fillStyle / font / lineWidth …）走普通属性，不 stub
    if (/^(fillStyle|strokeStyle|lineWidth|lineCap|lineJoin|globalAlpha|font|textAlign|textBaseline|miterLimit|shadowBlur|shadowColor|shadowOffsetX|shadowOffsetY|globalCompositeOperation|imageSmoothingEnabled|imageSmoothingQuality|filter|direction|letterSpacing|fontKerning)$/.test(k)) {
      return t[k];
    }
    unknownCalls.add(k);
    return () => touch(k);
  },
  set(t, k, v) { t[k] = v; return true; },
});
ctx.imageSmoothingEnabled = true;
ctx.imageSmoothingQuality = 'high';

/* ---- 最小 DOM 桩 ---- */
const holder = { style: {}, dataset: {},
  classList: { add(){}, remove(){}, toggle(){} },
  appendChild(){}, setAttribute(){}, addEventListener(){},
  getBoundingClientRect: () => ({ left:0, top:0, width:900, height:620 }) };
const cv = {
  clientWidth: 900, clientHeight: 620, width: 900, height: 620,
  getContext: () => ctx, addEventListener() {}, style: {},
  parentElement: holder,
  getBoundingClientRect: () => ({ left: 0, top: 0, width: 900, height: 620 }),
};
const mkBtn = (view) => ({
  dataset: { view }, style: {},
  classList: { add(){}, remove(){}, toggle(){}, contains: () => false },
  setAttribute(){}, addEventListener(){}, remove(){},
  getBoundingClientRect: () => ({ left:0, top:0, width:80, height:24 }),
  onclick: null,
  click(){ if (typeof this.onclick === 'function') this.onclick({}); },
});
const BTNS = ['topic','overlay','density','yearring'].map(mkBtn);

const el = () => ({
  style: {}, dataset: {},
  classList: { add() {}, remove() {}, toggle() {}, contains: () => false },
  appendChild() {}, setAttribute() {}, addEventListener() {}, remove() {},
  querySelectorAll: () => [], querySelector: () => null,
  closest: () => null, contains: () => false,
  insertBefore() {}, replaceChild() {}, cloneNode: () => el(),
  children: [], childNodes: [], firstChild: null,
  getBoundingClientRect: () => ({ left: 0, top: 0, width: 900, height: 620 }),
  getContext: () => ctx,
  focus() {}, blur() {}, click() {},
});
const sandbox = {
  cv, ctx, console,
  performance: { now: () => 0 },
  requestAnimationFrame: f => f(),
  cancelAnimationFrame: () => {},
  devicePixelRatio: 1,
  Math, JSON, Object, Array, Set, Map, String, Number, Boolean, Date, RegExp,
  parseInt, parseFloat, isNaN, Infinity, undefined, NaN, isFinite,
  Promise, Symbol, Error, TypeError, RangeError, ReferenceError, SyntaxError,
  ArrayBuffer, Int16Array, Uint8Array, Uint8ClampedArray, Float32Array, DataView,
  // atob：报告用 base64 int16 内联坐标（pos_encoded），vm 沙箱不带该 web 全局
  atob: s => Buffer.from(s, 'base64').toString('binary'),
  // ResizeObserver：新版用它兜住"容器由 0 宽变有宽"的情况
  ResizeObserver: class { observe() {} disconnect() {} },
};
sandbox.window = sandbox;
sandbox.globalThis = sandbox;
sandbox.self = sandbox;
sandbox.addEventListener = () => {};
sandbox.getComputedStyle = () => ({ getPropertyValue: () => '' });
sandbox.document = {
  querySelectorAll: sel => (sel === '.viewbtn' ? BTNS : []),
  querySelector: () => null,
  createElement: el,
  createDocumentFragment() { return el(); },
  getElementById: id => (id === 'net' ? cv : el()),
  body: el(),
  addEventListener() {},
};

const context = vm.createContext(sandbox);
try {
  // 逐个执行每个 script 块（数据块 + 画布主脚本 + 侧栏导航脚本），
  // 不能只跑前两个：新增脚本一旦有语法错，页面上会是"整块功能静默失效"。
  for (let bi = 0; bi < blocks.length; bi++) {
    try {
      vm.runInContext(blocks[bi], context);
    } catch (e) {
      const m = (e.stack || '').match(/evalmachine[^:]*:(\d+):(\d+)/);
      let ctxInfo = '';
      if (m) {
        const ln = +m[1];
        const src = blocks[bi].split('\n');
        ctxInfo = '\n  第 ' + (bi + 1) + ' 个 script 块，出错行 ' + ln + ': '
                + String(src[ln - 1] || '').trim().slice(0, 120);
      }
      throw Object.assign(e, { __ctx: ctxInfo });
    }
  }
} catch (e) {
  console.error('[FAIL] 报告脚本初始化异常：' + e.message + (e.__ctx || ''));
  process.exit(1);
}

const T = sandbox.__TEST__;
if (!T || typeof T.setView !== 'function') {
  console.error('[FAIL] 未找到 window.__TEST__.setView —— 报告缺少可测试出口');
  process.exit(1);
}

function probe(label, fn) {
  try { fn(); return true; }
  catch (e) {
    console.log(`  [FAIL] ${label} 抛异常：${e.message}`);
    console.log('         这会让整段脚本中断，**所有**视图失效且页面无任何提示');
    return false;
  }
}

/* ── 断言 0：布局本身必须健康 ──
   badXY > 0 意味着"画了，但画在 NaN 坐标上"——页面上表现为整片空白，
   而调用计数器完全正常。这是本套测试存在的首要理由。 */
let fail = 0;
console.log('视图渲染自检：' + htmlPath.split(/[\\/]/).pop());
if (typeof T.layoutSanity === 'function') {
  const L = T.layoutSanity();
  if (L.badXY > 0) {
    console.log(`  [FAIL] 布局体检 有 ${L.badXY}/${L.total} 个节点坐标非有限值 ` +
                `→ 画布将整片空白（控制台无报错）`);
    fail++;
  } else if (!(L.spanX > 0) || !(L.spanY > 0)) {
    console.log(`  [FAIL] 布局体检 节点坐标跨度为 0（spanX=${L.spanX}, ` +
                `spanY=${L.spanY}）→ 所有节点重叠在同一点，等于看不见`);
    fail++;
  } else {
    console.log(`  [PASS] 布局体检 ${L.total} 个节点坐标全部有限，` +
                `跨度 ${L.spanX.toFixed(0)}×${L.spanY.toFixed(0)}`);
  }
} else {
  console.log('  [FAIL] 缺少 window.__TEST__.layoutSanity —— 无法验证坐标有效性');
  fail++;
}

if (typeof T.hasKeywordNet === 'function') {
  console.log('  关键词共现网：' + (T.hasKeywordNet() ? '已提供' : '未提供（年轮将回落主网络）'));
}

/* ── 逐视图渲染 ── */
const VIEWS = ['topic', 'overlay', 'density', 'yearring'];
for (const v of VIEWS) {
  for (const k in calls) delete calls[k];
  lastImage = null;
  try {
    const btn = BTNS.find(b => b.dataset.view === v);
    let got;
    if (btn && typeof btn.onclick === 'function') { btn.click(); got = btn.dataset.view; }
    else { got = T.setView(v); }
    const paints = (calls.arc || 0) + (calls.fill || 0) + (calls.gradient || 0)
                 + (calls.fillRect || 0) + (calls.drawImage || 0);
    if (paints === 0) {
      console.log(`  [FAIL] ${v.padEnd(9)} 渲染调用为 0 —— 切换后会是空白`);
      fail++;
      continue;
    }
    const detail = [
      'arc=' + (calls.arc || 0),
      'fill=' + (calls.fill || 0),
      calls.gradient ? 'gradient=' + calls.gradient : '',
      calls.drawImage ? 'image=' + calls.drawImage : '',
      calls.fillText ? 'text=' + calls.fillText : '',
    ].filter(Boolean).join(' ');

    // 视图专属的"看得见"证据
    let evidence = '';
    let ok = true;
    if (v === 'density') {
      const info = typeof T.renderEvidence === 'function'
        ? (T.renderEvidence() || {}).density : null;
      if (!info || !info.drawn) {
        console.log(`  [FAIL] ${v.padEnd(9)} 没有可绘制节点（drawn=0）`);
        ok = false;
      } else if (!(info.contrast >= MIN_CONTRAST)) {
        console.log(`  [FAIL] ${v.padEnd(9)} 热区与底色对比仅 ${info.contrast}/255 ` +
                    `（阈值 ${MIN_CONTRAST}）—— 画了但肉眼看不见`);
        console.log(`         peak=${info.peak} bg=${info.bg}`);
        ok = false;
      } else {
        evidence = `contrast=${info.contrast}/255 peak=${info.peak}`;
      }
    }
    if (v === 'yearring') {
      const info = typeof T.renderEvidence === 'function'
        ? (T.renderEvidence() || {}).yearring : null;
      if (!info || !(info.ringArcs > 0)) {
        console.log(`  [FAIL] ${v.padEnd(9)} 没有画出任何年轮圆弧（ringArcs=0）` +
                    ` —— 只剩背景色，等同空白`);
        ok = false;
      } else {
        evidence = `ringArcs=${info.ringArcs} 年=${info.years.join('–')} ` +
                   `源=${info.source}`;
      }
    }
    if (!ok) { fail++; continue; }
    console.log(`  [PASS] ${String(got).padEnd(9)} ${detail}${evidence ? '  ' + evidence : ''}`);
  } catch (e) {
    console.log(`  [FAIL] ${v.padEnd(9)} 抛异常：${e.message}`);
    fail++;
  }
}

/* 往返回证：年轮会改写坐标，离开时必须能还原。
   只测"进入"不测"离开"会漏掉 restoreBaseLayout 这类只在切走时调用的缺陷。 */
const totalBefore = typeof T.layoutSanity === 'function'
  ? T.layoutSanity().total : -1;
for (const v of ['topic', 'yearring', 'density', 'topic', 'yearring', 'topic']) {
  const okv = probe(`来回切换 ${v}`, () => T.setView(v));
  if (!okv) { fail++; break; }
}
/* 切回主题视图后，节点顺序与坐标必须仍然健康：
   年轮若就地 sort(N)，byDeg/idx 会全部错位，节点与边张冠李戴。 */
if (typeof T.layoutSanity === 'function') {
  const L2 = T.layoutSanity();
  if (L2.badXY > 0) {
    console.log(`  [FAIL] 往返回证 切回后出现 ${L2.badXY} 个非有限坐标`);
    fail++;
  } else if (L2.total !== totalBefore) {
    console.log(`  [FAIL] 往返回证 节点数由 ${totalBefore} 变为 ${L2.total}（数组被就地改动）`);
    fail++;
  } else {
    console.log(`  [PASS] 往返回证 切回主题视图后坐标仍全部有限`);
  }
}
if (unknownCalls.size) {
  console.log('  注：桩未显式实现的方法已自动兜底（建议补进 PAINT 表）：'
              + [...unknownCalls].join('、'));
}
console.log(fail ? `\n结果：${fail} 项未通过` : '\n结果：全部视图通过 + 来回切换正常');
process.exit(fail ? 1 : 0);
