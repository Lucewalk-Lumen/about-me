#!/usr/bin/env node
/*
 * Teacher Workbench · 本地中继桥 v2 (loopback only, secure)
 * ------------------------------------------------------------
 * 工作台（浏览器）把数据快照经本机回环发给桥，桥落盘供管家(agent)读取/回写。
 * 数据全程仅在用户设备内经 127.0.0.1 / ::1 传输，不上传任何外部服务器。
 *
 * 安全（v2 强化，跨平台）：
 *  - 强随机 token：安装时生成于 ~/.workbuddy/workbench-bridge/.token（可用 WB_BRIDGE_OUT_DIR 覆盖；仅当前用户可读写），
 *    支持 POST /token/rotate 轮换；当经桥同源托管页面时由服务端直接注入，避免跨源 GET /token 暴露。
 *    token 文件权限：macOS/Linux 用 chmod 600；Windows 用 icacls 限制为当前用户(F)，
 *    失败时降级为仅本机回环可用（不阻断启动）。
 *  - HMAC-SHA256 签名 + 时间戳重放窗口（±60s）：所有写请求须携带 {token, ts, sig}，
 *    sig = HMAC(token, ts + ':' + sha256(body))，防篡改与回放。
 *  - 读请求鉴权：GET /latest /inbox /db 须带 Authorization: Bearer <token>（恒定时间比较）；
 *    GET /token 仅作回环引导兜底：入口 isLoopback(remote) 把关（不信任 X-Forwarded-For 等伪造头），
 *    且设「首次引导」闸门（本进程首交付后返回 403）；不校验 Origin / X-Requested-With（理由见 handler 内注释）。
 *  - 仅接受回环来源（IPv4/IPv6），非回环一律 403。
 *  - 输入强校验：/inbox 逐条校验、/db 校验 JSON 结构，非法即 422，不静默放行。
 *  - 速率限制：每来源令牌桶 120 req/min，超限 429，防 loopback 洪泛。
 *  - 原子写：temp + rename；输出目录/文件限当前用户可读写（macOS/Linux chmod 700/600，Windows icacls (F)）。
 *  - 审计日志：~/.workbuddy/workbench-bridge/audit.log（轮转），记录每笔写操作。
 *
 * 零外部依赖：仅用 Node 内置 http / fs / os / path / crypto。
 * 启动：node teacher-workbench-bridge.js
 * 环境变量：WB_BRIDGE_PORT（默认 18765）、WB_BRIDGE_OUT_DIR（默认 ~/.workbuddy/workbench-bridge）、
 *           WB_BRIDGE_TOKEN_FILE（默认 <OUT_DIR>/.token）
 */
'use strict';

const http = require('http');
const fs = require('fs');
const os = require('os');
const path = require('path');
const crypto = require('crypto');
const { execFileSync } = require('child_process');

const _port = process.env.WB_BRIDGE_PORT ? Number(process.env.WB_BRIDGE_PORT) : NaN;
const PORT = (Number.isInteger(_port) && _port >= 1024 && _port <= 65535) ? _port : 18765;
if (process.env.WB_BRIDGE_PORT && PORT !== _port) console.warn('[teacher-workbench-bridge] WB_BRIDGE_PORT 非法（' + process.env.WB_BRIDGE_PORT + '），已回退默认 18765');
const OUT_DIR = process.env.WB_BRIDGE_OUT_DIR
  ? path.resolve(process.env.WB_BRIDGE_OUT_DIR)
  : path.join(os.homedir(), '.workbuddy', 'workbench-bridge');
const TOKEN_FILE = process.env.WB_BRIDGE_TOKEN_FILE || path.join(OUT_DIR, '.token');
const OUT_FILE = path.join(OUT_DIR, 'snapshot.json');
const INBOX_FILE = path.join(OUT_DIR, 'inbox.json');
const DB_FILE = path.join(OUT_DIR, 'db.json');
const AUDIT_FILE = path.join(OUT_DIR, 'audit.log');
const MAX_BODY = 20 * 1024 * 1024; // 20MB 上限
const REPLAY_WINDOW = 60 * 1000;    // 签名时间戳允许窗口 ±60s
const RATE_LIMIT = 120;             // 每来源每分钟请求上限
const MAX_INBOX_ITEMS = 50;         // 单次 POST /inbox 的 items 上限（与文档一致，超出请分批）
const MAX_TAG_LEN = 20;             // 单个 tag 最大字符数（与文档一致）
const RATE_WINDOW = 60 * 1000;      // 速率限制窗口（1 分钟）

/* ---------------- 跨平台文件/目录权限硬化 ----------------
 * 目标：仅当前用户可读写 token / 数据 / 审计文件（等价于 POSIX 600/700）。
 *  - macOS/Linux：fs.chmodSync 0o600 / 0o700。
 *  - Windows：icacls 移除继承并仅授予当前用户 (F)；icacls 缺失或失败时降级告警，
 *    不阻断启动（数据仍仅经本机回环 127.0.0.1/::1 传输，不对外暴露）。 */
function currentUser() { return process.env.USERNAME || process.env.USER || ''; }
/* 返回 { ok, desc }：ok=true 表示限制已确认生效，false 表示未能施加（调用方据此输出实际状态）。
 * icacls 失败时捕获 stdout/stderr 以便给出可诊断的原因；stdio:'ignore' 会丢掉真实报错，
 * 只剩一句 "Command failed"。判定保守：仅 exit code 为 0 才算生效，宁可少报成功、不误报成功。 */
function winAcl(args, label) {
  try {
    execFileSync('icacls', args, { windowsHide: true, encoding: 'utf8' });
    return { ok: true, desc: 'icacls 仅当前用户 (F)' };
  } catch (e) {
    const raw = String((e && (e.stderr || e.stdout)) || (e && e.message) || e);
    const detail = raw.replace(/\s+/g, ' ').trim().slice(0, 160) || '未知原因';
    console.warn('[teacher-workbench-bridge] Windows ' + label + ' ACL 限制未生效（已降级，数据仍仅本机回环可用）: ' + detail);
    return { ok: false, desc: 'icacls 失败：' + detail };
  }
}
function secureFile(p) {
  if (process.platform === 'win32') {
    const u = currentUser();
    if (!u) return { ok: false, desc: 'icacls 跳过（取不到当前用户名）' };
    return winAcl([p, '/inheritance:r', '/grant:r', u + ':(F)'], '文件');
  }
  try { fs.chmodSync(p, 0o600); return { ok: true, desc: 'chmod 600' }; }
  catch (e) { return { ok: false, desc: 'chmod 失败：' + e.message }; }
}
function secureDir(p) {
  if (process.platform === 'win32') {
    const u = currentUser();
    if (!u) return { ok: false, desc: 'icacls 跳过（取不到当前用户名）' };
    return winAcl([p, '/inheritance:r', '/grant:r', u + ':(OI)(CI)(F)'], '目录');
  }
  try { fs.chmodSync(p, 0o700); return { ok: true, desc: 'chmod 700' }; }
  catch (e) { return { ok: false, desc: 'chmod 失败：' + e.message }; }
}

/* 权限硬化的实际结果（供启动日志输出真实状态） */
let TOKEN_PERMS = { ok: null, desc: '未评估' };
let DIR_PERMS = { ok: null, desc: '未评估' };

/* ---------------- token 管理 ---------------- */
function ensureDir() { try { fs.mkdirSync(OUT_DIR, { recursive: true, mode: 0o700 }); } catch (e) {} return secureDir(OUT_DIR); }
function loadToken() {
  try { return fs.readFileSync(TOKEN_FILE, 'utf8').trim(); } catch (e) { return ''; }
}
function persistToken(t) {
  ensureDir();
  atomicWrite(TOKEN_FILE, t);   // temp + rename，避免半截 token 被读到
  secureFile(TOKEN_FILE);
}
function ensureToken() {
  DIR_PERMS = ensureDir();
  let t = loadToken();
  if (!t || t.length < 16) {
    t = crypto.randomBytes(32).toString('hex');
    try { persistToken(t); console.log('[teacher-workbench-bridge] generated new token -> ' + TOKEN_FILE); }
    catch (e) { console.warn('[teacher-workbench-bridge] token write failed: ' + e.message); }
  }
  // 不论 token 是新建还是复用，都施加一次权限硬化并记录结果：
  // 文件若因复制或继承而权限变宽，此处会纠正，结果反映在启动日志中。
  TOKEN_PERMS = secureFile(TOKEN_FILE);
  return t;
}
let TOKEN = ensureToken();
let tokenDelivered = false; // 首次引导闸门：强 token 仅在本进程首次交付后返回，缩小本机进程抓取窗口

/* ---------------- 回环校验 ---------------- */
function isLoopback(addr) {
  if (!addr) return false;
  addr = addr.replace(/^::ffff:/, ''); // IPv4-mapped IPv6
  return addr === '127.0.0.1' || addr === '::1' || addr === 'localhost';
}

/* ---------------- 签名校验 ----------------
 * 统一规则：客户端对「信封(去 sig 字段)的规范 JSON」签名；服务端用同样规则重建并校验。
 * 规范 JSON = 递归键排序后序列化（canon）。sig = HMAC(token, ts + ':' + sha256(canon(env-no-sig)))。
 * 该规则对所有端点一致，避免「信封含 sig 导致循环依赖」。 */
function hmac(msg) { return crypto.createHmac('sha256', TOKEN).update(msg).digest('hex'); }
function sha256(str) { return crypto.createHash('sha256').update(str).digest('hex'); }
function canon(o) {
  if (Array.isArray(o)) return '[' + o.map(canon).join(',') + ']';
  if (o && typeof o === 'object') {
    const ks = Object.keys(o).sort();
    return '{' + ks.map((k) => JSON.stringify(k) + ':' + canon(o[k])).join(',') + '}';
  }
  return JSON.stringify(o);
}
function verifySig(ts, sig, contentStr) {
  if (!ts || !sig || contentStr === undefined || contentStr === null) return false;
  const n = Number(ts);
  if (!Number.isFinite(n)) return false;
  if (Math.abs(Date.now() - n) > REPLAY_WINDOW) return false; // 重放窗口外
  const expect = hmac(String(ts) + ':' + sha256(contentStr));
  const a = Buffer.from(expect), b = Buffer.from(String(sig));
  if (a.length !== b.length) return false;
  return crypto.timingSafeEqual(a, b);
}

/* ---------------- 速率限制（令牌桶，按来源） ---------------- */
const buckets = new Map();
setInterval(() => buckets.forEach((v, k) => { if (Date.now() - v.t > RATE_WINDOW) buckets.delete(k); }), RATE_WINDOW);
function rateOK(remote) {
  const now = Date.now();
  let b = buckets.get(remote);
  if (!b || now - b.t > RATE_WINDOW) { b = { tokens: RATE_LIMIT, t: now }; buckets.set(remote, b); }
  if (b.tokens <= 0) return false;
  b.tokens -= 1;
  return true;
}

/* CORS：仅允许同源托管主机（127.0.0.1 / localhost / [::1]）；跨站源与 file://(null) 一律不回 ACAO → 无法读取本地数据
 * 注意：不设 Access-Control-Allow-Credentials（与多源 ACAO 并用有风险，本地桥不需要 credentials）。 */
function setCors(res, req) {
  var o = req && req.headers && req.headers.origin;
  var allowed = [ 'http://127.0.0.1:' + PORT, 'http://localhost:' + PORT, 'http://[::1]:' + PORT ];
  if (o && allowed.indexOf(o) !== -1) {
    res.setHeader('Access-Control-Allow-Origin', o);
  }
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With');
}

/* ---------------- 审计日志（轮转：>5MB 截断） ----------------
 * 每笔请求（读 / 写 / 拒绝 / token 引导与轮换）均落审计，便于排查本机异常访问。
 * 权限只在首次创建时施加一次（_auditSecured）：避免每个请求都调 secureFile()
 * （Windows 下会为每次 append 额外 fork 一次 icacls，属无谓热路径开销）。 */
let _auditSecured = false;
function audit(action, remote, ok, detail) {
  try {
    let size = 0; try { size = fs.statSync(AUDIT_FILE).size; } catch (e) {}
    if (size > 5 * 1024 * 1024) { try { fs.writeFileSync(AUDIT_FILE, ''); } catch (e) {} _auditSecured = false; }
    const line = JSON.stringify({ ts: Date.now(), action, remote, ok, detail: detail || '' }) + '\n';
    fs.appendFileSync(AUDIT_FILE, line);
    if (!_auditSecured) { const r = secureFile(AUDIT_FILE); _auditSecured = (r && r.ok === true); }
  } catch (e) {}
}

/* ---------------- 原子写（temp + rename） ---------------- */
function atomicWrite(file, data) {
  ensureDir();
  const tmp = file + '.tmp.' + process.pid + '.' + Date.now();
  fs.writeFileSync(tmp, data);
  fs.renameSync(tmp, file);   // rename 会继承 tmp 的权限位；这里再对最终文件显式硬化，兼容 Windows ACL
  secureFile(file);
}

/* ---------------- 同源静态托管（工作台 + 资源） ----------------
 * 桥在 http://127.0.0.1:PORT/ 同源提供工作台 HTML；localhost 属安全上下文，
 * 浏览器 crypto.subtle 可用（file:// 直开时 Chrome 下可能为 undefined）。
 * 服务端把占位符 __WB_INJECTED_TOKEN__ 替换为真实 token 注入页面，避免使用 GET /token 跨源暴露。 */
const ASSETS_DIR = path.join(__dirname, '..', 'assets');
const MIME = { '.html':'text/html; charset=utf-8', '.js':'text/javascript; charset=utf-8', '.css':'text/css; charset=utf-8', '.json':'application/json; charset=utf-8', '.webmanifest':'application/manifest+json', '.png':'image/png', '.svg':'image/svg+xml', '.ico':'image/x-icon', '.txt':'text/plain; charset=utf-8' };
function safeJoin(name) {
  if (!name || name === '..' || name === '.' || /[\/\\]/.test(name)) return null;
  var p = path.join(ASSETS_DIR, name);
  if (p !== ASSETS_DIR && p.indexOf(ASSETS_DIR + path.sep) !== 0) return null; // 防目录穿越
  return p;
}
function serveAsset(res, name) {
  var p = safeJoin(name);
  if (!p) { res.writeHead(403, { 'Content-Type':'text/plain; charset=utf-8' }); res.end('forbidden'); return; }
  fs.readFile(p, function(err, buf) {
    if (err) { res.writeHead(404, { 'Content-Type':'text/plain; charset=utf-8' }); res.end('not found'); return; }
    res.writeHead(200, {
      'Content-Type': MIME[path.extname(p).toLowerCase()] || 'application/octet-stream',
      'X-Content-Type-Options': 'nosniff'
    });
    res.end(buf);
  });
}
/* 桥同源托管工作台时的 CSP：作为 XSS 的第二道防线。
 * 逐条对照工作台真实发出的请求与渲染方式设定，避免「策略本身先打断功能」：
 * - script-src 需 'unsafe-inline'（单文件、内联脚本）；放开 https: 是为可选云同步——
 *   loadSDK() 以 <script src> 加载用户自配的 CDN 地址（加载脚本归 script-src，不归 connect-src）。
 * - style-src 需 'unsafe-inline'（大量内联样式）。
 * - img-src 放开 data:（图标与校历图片为 data: URI）。
 * - frame-src 放开 data:——校历 PDF 预览走 <iframe src="data:application/pdf...">，
 *   缺此项会被 default-src 'self' 拦掉（'self' 不匹配 data:）。
 * - connect-src 放开 https: 供云同步 SDK 传输密文；同时显式放行本机回环端口。
 * - object-src 'none'、base-uri 'none'、frame-ancestors 'self'（与 X-Frame-Options 呼应）。 */
const CSP = [
  "default-src 'self'",
  "script-src 'self' 'unsafe-inline' https:",
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data:",
  "frame-src 'self' data:",
  "connect-src 'self' http://127.0.0.1:" + PORT + " http://localhost:" + PORT + " https:",
  "font-src 'self' data:",
  "object-src 'none'",
  "base-uri 'none'",
  "frame-ancestors 'self'"
].join('; ');
function serveWorkbench(res) {
  var p = path.join(ASSETS_DIR, 'teacher-workbench.html');
  fs.readFile(p, 'utf8', function(err, html) {
    if (err) { res.writeHead(404, { 'Content-Type':'text/plain; charset=utf-8' }); res.end('workbench not found'); return; }
    /* 注入当前强 token。token 为 crypto.randomBytes(32).toString('hex')（恒为十六进制），
       额外用 JSON.stringify 兜底：即使将来 token 来源变化，也不可能跳出 JS 字符串字面量。 */
    html = html.split('__WB_INJECTED_TOKEN__').join(JSON.stringify(TOKEN).slice(1, -1));
    res.writeHead(200, {
      'Content-Type':'text/html; charset=utf-8',
      'Cache-Control':'no-store',
      'X-Content-Type-Options':'nosniff',
      'X-Frame-Options':'SAMEORIGIN',
      'Content-Security-Policy': CSP
    });
    res.end(html);
  });
}

/* ---------------- 输入校验 ---------------- */
function validDate(s) { return typeof s === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(s); }
function validPri(p) { return p === 'P0' || p === 'P1' || p === 'P2' || p === 'P3'; }
function validRepeat(r) { return r === 'none' || r === 'daily' || r === 'weekly' || r === 'monthly'; }
function validItem(it) {
  if (!it || (it.type !== 'todo' && it.type !== 'note')) return 'type 须为 todo|note';
  if (typeof it.text !== 'string' || !it.text.trim()) return 'text 必填且非空';
  if (it.text.length > 500) return 'text 超长(>500)';
  if (it.pri !== undefined && !validPri(it.pri)) return 'pri 非法';
  if (it.due !== undefined && it.due !== '' && !validDate(it.due)) return 'due 日期格式应为 YYYY-MM-DD';
  if (it.repeat !== undefined && !validRepeat(it.repeat)) return 'repeat 非法';
  if (it.tags !== undefined) {
    if (!Array.isArray(it.tags) || it.tags.length > 8) return 'tags 须为≤8 的数组';
    for (let i = 0; i < it.tags.length; i++) {
      const tg = it.tags[i];
      if (typeof tg !== 'string' || !tg.trim()) return 'tags[' + i + '] 须为非空字符串';
      if (tg.length > MAX_TAG_LEN) return 'tags[' + i + '] 超长(>' + MAX_TAG_LEN + ')';
    }
  }
  if (it.cat !== undefined && (typeof it.cat !== 'string' || it.cat.length > 30)) return 'cat 超长';
  if (it.proj !== undefined && (typeof it.proj !== 'string' || it.proj.length > 50)) return 'proj 超长';
  if (it.extId !== undefined && (typeof it.extId !== 'string' || it.extId.length > 64)) return 'extId 超长';
  return null;
}
/* tag 归一化：trim + 自动去重（保持原有顺序），与文档「tag 自动去重」一致 */
function sanitizeItems(items) {
  for (let i = 0; i < items.length; i++) {
    const it = items[i];
    if (!it || !Array.isArray(it.tags)) continue;
    const seen = Object.create(null);
    const out = [];
    for (let j = 0; j < it.tags.length; j++) {
      const tg = String(it.tags[j]).trim();
      if (!tg || seen[tg]) continue;
      seen[tg] = 1;
      out.push(tg);
    }
    it.tags = out;
  }
  return items;
}
function validDB(obj) {
  if (!obj || typeof obj !== 'object') return 'db 须为对象';
  if (!Array.isArray(obj.todos) || !Array.isArray(obj.notes) || !Array.isArray(obj.projects)) return '须含 todos/notes/projects 数组';
  if (typeof obj.meta !== 'object' || !obj.meta) return '须含 meta 对象';
  return null;
}

/* ---------------- 请求体读取 ---------------- */
function readBody(req, res, cb) {
  let body = '', aborted = false;
  req.on('data', (c) => {
    body += c;
    if (body.length > MAX_BODY) { aborted = true; resJson(res, 413, { ok: false, error: 'payload too large' }); req.destroy(); }
  });
  req.on('end', () => { if (!aborted) cb(body); });
}
function resJson(res, code, obj) {
  res.writeHead(code, {
    'Content-Type': 'application/json',
    'X-Content-Type-Options': 'nosniff',
    'Cache-Control': 'no-store'
  });
  res.end(JSON.stringify(obj));
}

/* ---------------- 写请求鉴权：token + 签名（统一对「去 sig 信封」规范 JSON 校验） ---------------- */
function authWrite(parsed) {
  if (!parsed || typeof parsed.token !== 'string') return 'bad token';
  const a = Buffer.from(parsed.token), b = Buffer.from(TOKEN);
  if (a.length !== b.length || !crypto.timingSafeEqual(a, b)) return 'bad token'; // 恒定时间比较，避免计时侧信道
  const p = Object.assign({}, parsed); delete p.sig;
  if (!verifySig(parsed.ts, parsed.sig, canon(p))) return 'bad signature or replay';
  return null;
}

/* ---------------- 读请求鉴权：Authorization: Bearer <token>（恒定时间比较） ----------------
 * GET 无写/重放风险，仅需 token 一致即可；与写请求共用同一强随机 token。 */
function authRead(req) {
  const m = /^Bearer\s+(.+)$/.exec((req.headers.authorization || '').trim());
  if (!m) return 'missing bearer token';
  const a = Buffer.from(TOKEN), b = Buffer.from(m[1].trim());
  if (a.length !== b.length) return 'bad token';
  return crypto.timingSafeEqual(a, b) ? null : 'bad token';
}

/* ---------------- 主处理 ---------------- */
function handler(req, res) {
  setCors(res, req);
  if (req.method === 'OPTIONS') { res.writeHead(204); res.end(); return; }
  const remote = (req.socket.remoteAddress || '').replace(/^::ffff:/, '');

  if (!isLoopback(remote)) {
    audit('forbidden', remote, false, req.method + ' ' + req.url);
    resJson(res, 403, { ok: false, error: 'forbidden: not loopback' });
    return;
  }
  if (!rateOK(remote)) { resJson(res, 429, { ok: false, error: 'rate limited' }); return; }

  const url = req.url.split('?')[0];

  /* 同源托管工作台与静态资源（安全上下文 → crypto.subtle 可用；消除跨源 GET /token 暴露） */
  if (req.method === 'GET' && (url === '/' || url === '/index.html' || url === '/teacher-workbench.html')) { serveWorkbench(res); return; }
  if (req.method === 'GET' && (url === '/sw.js' || url === '/manifest.webmanifest' || url === '/icon-192.png' || url === '/icon-512.png' || url === '/icon-maskable-512.png' || url === '/icon.svg' || url === '/apple-touch-icon.png')) { serveAsset(res, url.slice(1)); return; }
  if (req.method === 'GET' && url.indexOf('/assets/') === 0) { serveAsset(res, url.slice('/assets/'.length)); return; }

  if (req.method === 'GET' && url === '/health') {
    resJson(res, 200, { ok: true, uptime: Math.round(process.uptime()), pid: process.pid, tokenSet: !!TOKEN });
    return;
  }
  if (req.method === 'GET' && url === '/token') {
    /* GET /token 仅作回环引导兜底：强 token 仅限「首次引导」返回。
     * 一旦本进程已交付过 token（或经同源托管注入），后续请求返回 403，
     * 缩小「本机任意进程可随时抓取强 token」的暴露窗口；需要重新引导请重启桥。 */
    if (tokenDelivered) {
      audit('token-bootstrap', remote, false, 'already delivered');
      resJson(res, 403, { ok: false, error: 'token already bootstrapped; restart bridge to re-bootstrap' });
      return;
    }
    tokenDelivered = true;
    audit('token-bootstrap', remote, true, '');
    resJson(res, 200, { ok: true, token: TOKEN });
    return;
  }
  if (req.method === 'POST' && url === '/token/rotate') {
    readBody(req, res, (body) => {
      let p; try { p = JSON.parse(body); } catch (e) { resJson(res, 400, { ok: false, error: 'invalid json' }); return; }
      const err = authWrite(p);
      if (err) { audit('token-rotate', remote, false, err); resJson(res, err === 'bad token' ? 401 : 403, { ok: false, error: err }); return; }
      const nt = crypto.randomBytes(32).toString('hex');
      try { persistToken(nt); TOKEN = nt; } catch (e) { resJson(res, 500, { ok: false, error: 'token write failed' }); return; }
      audit('token-rotate', remote, true, '');
      resJson(res, 200, { ok: true, token: nt });
    });
    return;
  }
  if (req.method === 'GET' && url === '/latest') {
    const rerr = authRead(req);
    if (rerr) { audit('latest', remote, false, rerr); resJson(res, rerr === 'bad token' || rerr === 'missing bearer token' ? 401 : 403, { ok: false, error: rerr }); return; }
    fs.readFile(OUT_FILE, 'utf8', (e2, data) => {
      if (e2) { resJson(res, 404, { ok: false, error: 'no snapshot yet' }); return; }
      try { resJson(res, 200, JSON.parse(data)); }
      catch (e) { audit('latest', remote, false, 'snapshot parse failed'); resJson(res, 500, { ok: false, error: 'snapshot 文件损坏' }); }
    });
    return;
  }
  if (req.method === 'POST' && url === '/sync') {
    readBody(req, res, (body) => {
      let p; try { p = JSON.parse(body); } catch (e) { resJson(res, 400, { ok: false, error: 'invalid json' }); return; }
      const err = authWrite(p);
      if (err) { audit('sync', remote, false, err); resJson(res, err === 'bad token' ? 401 : 403, { ok: false, error: err }); return; }
      const dbErr = validDB(p.db);
      if (dbErr) { audit('sync', remote, false, dbErr); resJson(res, 422, { ok: false, error: dbErr }); return; }
      const snapshot = { receivedAt: Date.now(), source: p.source || 'teacher-workbench', db: p.db || null };
      try { atomicWrite(OUT_FILE, JSON.stringify(snapshot)); audit('sync', remote, true, body.length + 'B'); resJson(res, 200, { ok: true, receivedAt: snapshot.receivedAt }); }
      catch (e) { audit('sync', remote, false, e.message); resJson(res, 500, { ok: false, error: String(e && e.message || e) }); }
    });
    return;
  }
  if (url === '/inbox') {
    if (req.method === 'GET') {
      const rerr = authRead(req);
      if (rerr) { audit('inbox-read', remote, false, rerr); resJson(res, rerr === 'bad token' || rerr === 'missing bearer token' ? 401 : 403, { ok: false, error: rerr }); return; }
      fs.readFile(INBOX_FILE, 'utf8', (err, data) => {
        if (err) { resJson(res, 200, []); return; }
        try { resJson(res, 200, JSON.parse(data)); }
        catch (e) { audit('inbox-read', remote, false, 'parse failed'); resJson(res, 500, { ok: false, error: '收件箱文件损坏，请检查 ' + INBOX_FILE }); }
      });
      return;
    }
    if (req.method === 'DELETE') {
      readBody(req, res, (body) => {
        let p; try { p = JSON.parse(body || '{}'); } catch (e) { p = {}; }
        const err = authWrite(p);
        if (err) { audit('inbox-del', remote, false, err); resJson(res, err === 'bad token' ? 401 : 403, { ok: false, error: err }); return; }
        try { atomicWrite(INBOX_FILE, '[]'); audit('inbox-del', remote, true, ''); resJson(res, 200, { ok: true }); }
        catch (e) { resJson(res, 500, { ok: false, error: String(e && e.message || e) }); }
      });
      return;
    }
    if (req.method === 'POST') {
      readBody(req, res, (body) => {
        let p; try { p = JSON.parse(body); } catch (e) { resJson(res, 400, { ok: false, error: 'invalid json' }); return; }
        const err = authWrite(p);
        if (err) { audit('inbox', remote, false, err); resJson(res, err === 'bad token' ? 401 : 403, { ok: false, error: err }); return; }
        const items = Array.isArray(p.items) ? p.items : [];
        if (items.length > MAX_INBOX_ITEMS) {
          audit('inbox', remote, false, 'too many items: ' + items.length);
          resJson(res, 422, { ok: false, error: 'items 数量超限（' + items.length + ' > ' + MAX_INBOX_ITEMS + '），请分批发送' });
          return;
        }
        for (let i = 0; i < items.length; i++) {
          const ve = validItem(items[i]);
          if (ve) { audit('inbox', remote, false, 'item#' + i + ' ' + ve); resJson(res, 422, { ok: false, error: 'item#' + i + ' ' + ve }); return; }
        }
        sanitizeItems(items); // tag trim + 去重（在校验通过之后、落盘之前）
        let arr = [];
        let raw = '';
        try { raw = fs.readFileSync(INBOX_FILE, 'utf8'); }
        catch (e) { raw = ''; } // 文件不存在（首次入账）→ 视为空收件箱
        if (raw && raw.trim()) {
          try { arr = JSON.parse(raw); }
          catch (e) { audit('inbox', remote, false, 'inbox parse failed'); resJson(res, 500, { ok: false, error: '收件箱文件损坏，已保留原文件未写入，请检查 ' + INBOX_FILE }); return; }
          if (!Array.isArray(arr)) { audit('inbox', remote, false, 'inbox not array'); resJson(res, 500, { ok: false, error: '收件箱数据损坏，已保留原文件未写入，请检查 ' + INBOX_FILE }); return; }
        }
        /* 幂等 upsert：extId 相同的条目视为同一条（覆盖更新，不重复追加）；
           无 extId 的条目按原语义追加。避免管家重复执行同一句「加任务」导致重复入账。 */
        const idxById = Object.create(null);
        for (let i = 0; i < arr.length; i++) {
          const old = arr[i];
          if (old && typeof old.extId === 'string' && old.extId && !(old.extId in idxById)) idxById[old.extId] = i;
        }
        let appended = 0, updated = 0;
        for (let i = 0; i < items.length; i++) {
          const it = items[i];
          const id = (it && typeof it.extId === 'string') ? it.extId : '';
          if (id && (id in idxById)) { arr[idxById[id]] = it; updated++; continue; }
          if (id) idxById[id] = arr.length;
          arr.push(it);
          appended++;
        }
        try { atomicWrite(INBOX_FILE, JSON.stringify(arr)); audit('inbox', remote, true, '+' + appended + ' updated:' + updated); resJson(res, 200, { ok: true, count: arr.length, appended: appended, updated: updated }); }
        catch (e) { resJson(res, 500, { ok: false, error: String(e && e.message || e) }); }
      });
      return;
    }
  }
  if (url === '/db') {
    if (req.method === 'GET') {
      const rerr = authRead(req);
      if (rerr) { audit('db-read', remote, false, rerr); resJson(res, rerr === 'bad token' || rerr === 'missing bearer token' ? 401 : 403, { ok: false, error: rerr }); return; }
      fs.readFile(DB_FILE, 'utf8', (err, data) => {
        if (err) { resJson(res, 200, { ok: true, data: null }); return; }
        resJson(res, 200, { ok: true, data: data });
      });
      return;
    }
    if (req.method === 'POST') {
      readBody(req, res, (body) => {
        let p; try { p = JSON.parse(body); } catch (e) { resJson(res, 400, { ok: false, error: 'invalid json' }); return; }
        const err = authWrite(p);
        if (err) { audit('db', remote, false, err); resJson(res, err === 'bad token' ? 401 : 403, { ok: false, error: err }); return; }
        if (typeof p.data !== 'string') { resJson(res, 422, { ok: false, error: 'data 须为字符串' }); return; }
        try { atomicWrite(DB_FILE, String(p.data)); audit('db', remote, true, (p.data || '').length + 'B'); resJson(res, 200, { ok: true, bytes: (p.data || '').length }); }
        catch (e) { resJson(res, 500, { ok: false, error: String(e && e.message || e) }); }
      });
      return;
    }
  }
  resJson(res, 404, { ok: false, error: 'not found' });
}

/* ---------------- 同时监听 IPv4 与 IPv6 回环 ---------------- */
function boot(host) {
  const server = http.createServer(handler);
  // 系统禁用 IPv6 或端口被占用时捕获 error，避免未处理异常导致进程崩溃；
  // 双栈中至少一个成功即可工作（IPv4 通常总是可用）。
  server.on('error', (err) => {
    console.warn('[teacher-workbench-bridge] listen error on ' + host + ': ' + (err && err.code || err));
  });
  server.listen(PORT, host, () => {
    console.log('[teacher-workbench-bridge] listening on http://' + host + ':' + PORT);
  });
}
ensureDir();  // 先建输出目录再 listen，消除启动瞬间 token 写入 ENOENT
boot('127.0.0.1');
boot('::1');
// 权限状态按实际结果输出：Windows 走 icacls，失败时标注为已降级。
const permsText = (r) => r.ok === true ? ('OK (' + r.desc + ')')
  : r.ok === false ? ('已降级：' + r.desc + '，仅依赖 127.0.0.1 回环隔离')
  : '未评估';
console.log('[teacher-workbench-bridge] token file: ' + TOKEN_FILE + ' [perms ' + permsText(TOKEN_PERMS) + ']');
console.log('[teacher-workbench-bridge] data dir:  ' + OUT_DIR + ' [perms ' + permsText(DIR_PERMS) + ']');
console.log('[teacher-workbench-bridge] snapshot file: ' + OUT_FILE);
