# 本地桥接口与安全契约（分片）

> 本文件是管家指令（`agents/ai-butler.md`）的分片，按需读取；未读本文件不得执行桥写操作。

## B.2 本地桥服务参数

| 参数 | 取值 | 说明 |
|------|------|------|
| host | `127.0.0.1`（`::1` 亦接受） | 非回环来源一律 403 拒绝 |
| port | 默认 `18765`；`WB_BRIDGE_PORT` 可覆盖，须 ∈ `[1024, 65535]` | 每次探测后按需自启 |
| token | 安装时生成的强随机值，存于 `~/.workbuddy/workbench-bridge/.token`（`600`）；工作台经桥同源托管时由服务端直接注入页面（`__WB_INJECTED_TOKEN__` 占位符），不通过 HTTP 暴露给跨源；`GET /token` 仅作回环兜底、返回当前 token（详见下方安全契约）；管家需 token 时直接读该 `.token` 文件（**只可赋值给变量，禁止回显到对话/日志**） | 所有写请求须携带 `token`+`ts`+`sig`，缺失/错误 → 401/403；读请求（`/latest` `/inbox` `/db`）须带 `Authorization: Bearer <token>` |
| body 上限 | `20MB`（由桥强制） | 超出 → 413 |
| 输出文件 | `~/.workbuddy/workbench-bridge/snapshot.json` / `inbox.json` | 仅本机，无外传 |

## 本地桥（让管家真正读到工作台数据）

工作台是纯本地 HTML，数据在浏览器 localStorage；管家运行在后端沙箱，二者天然隔离。一条**本机回环桥**打通这条隔离——数据仅在用户设备上经 `127.0.0.1` 传输，不上传任何外部服务器。

- **前置条件**：本地桥依赖 **Node ≥ 18**（`node -v` 可查）；环境不满足时须明确告知用户，不可静默跳过。
- **桥组成**：随包附带 `bridge/teacher-workbench-bridge.js`（零依赖 Node 服务，v2），监听 `127.0.0.1` / `::1`，仅接受回环来源 + HMAC 签名 + 强随机 token，收到快照写入 `~/.workbuddy/workbench-bridge/snapshot.json`；并提供 `/inbox` 的 GET/POST/DELETE，供管家把口述的任务 / 灵感回写、工作台自动拉取入账。
- **工作台侧**：「设置 → 连接管家（本地桥）」开启后，点「立即同步给管家」即把脱敏后的 `DB`（`meta.sync` 的云凭证 `env` / `code` 与 `meta.bridge` 的桥 token 均已被剔除，仅保留开关等非敏感字段）POST 给桥；另有「复制快照」作手动兜底（同一套脱敏，用户可安全地把结果贴进对话）。
- **管家侧**：需要数据时，先确保桥在跑（下文），再用 Read 工具读取 `~/.workbuddy/workbench-bridge/snapshot.json` 解析 `db`（todos / notes / projects / meta）即可分析——**无需用户导出再上传**。
- **首次提醒（开启桥接）**：用户首次对话、或首次打开工作台时，主动提示其去「设置 → 连接管家（本地桥）」打开开关——这是管家能读到 / 写回真实数据的前提。工作台首次打开的引导向导也已新增「连接管家（本地桥）」一步说明此事，二者互为补充。

## 本地桥 v2 安全契约（与桥、工作台前端完全一致）

- **唯一实现**：桥只有 `bridge/teacher-workbench-bridge.js` 一处实现，不随包分发任何副本。
- **回环隔离**：仅监听 `127.0.0.1` / `::1`，非回环来源一律 `403`。
- **强随机 token**：安装时生成于 `~/.workbuddy/workbench-bridge/.token`（权限 `600`）；当工作台经桥同源托管（`http://127.0.0.1:18765/`）时，强 token 由服务端直接注入页面（无跨源暴露）；`GET /token` 仅作回环引导兜底——仅接受 `127.0.0.1` / `::1` 回环来源（入口 `isLoopback(remote)` 把关，不信任 `X-Forwarded-For` 等伪造头），返回当前强 token 供同源托管页或本机进程引导；不强制校验 `Origin` / `X-Requested-With`（浏览器因 CORS 无法读取非同源响应，但本机任意进程可经回环取走 token，故 token 视为本机秘密、勿外泄）；管家取 token 一律**读取 `.token` 文件**（`TOK=$(cat ~/.workbuddy/workbench-bridge/.token)`，只赋值、不回显），不走 HTTP；`GET /token` 另设「首次引导」闸门——仅本进程首次交付后返回 token，之后请求返回 `403`，缩小本机进程抓取窗口（工作台前端已把 token 持久化进 localStorage，重启桥即可重新引导）。
- **凭证禁止回显（硬规则）**：本机桥 token（`.token` 文件内容）与云同步凭证（`meta.sync.env` / `meta.sync.code`）视为本机秘密，**只可赋值给变量后直接用于签名或请求头**，**禁止输出到对话、日志、报错信息或任何面向用户的文本**；确需向用户提示时一律脱敏（如仅显示前 4 位、其余以 `****` 代替）。「复制快照」路径同样只输出已脱敏的 `DB`。
- **签名防重放**：所有写请求须携带 `{token, ts, sig}`，`sig = HMAC-SHA256(token, ts + ':' + SHA256(canon(信封去 sig)))`，含 ±60s 重放窗口；缺失 / 错误 → `401 / 403`。
- **接口**：`GET /health`、`POST /token/rotate`、`GET /latest`、`POST /sync`、`GET/POST/DELETE /inbox`、`GET/POST /db`；`GET /latest` / `GET /inbox` / `GET /db` 须带 `Authorization: Bearer <token>`（缺失 → `401`），`GET /token` 仅作回环引导兜底、首次请求返回强 token（之后 `403`，需重启桥重新引导）；`/inbox` 逐条字段校验、`/db` 结构校验，非法即 `422`；每来源限流 `120 req/min`；落盘原子写 + 目录 `700` / 文件 `600` + 审计日志。
- **CSP（内容安全策略）**：桥在同源托管工作台（`http://127.0.0.1:PORT/`）时下发严格 CSP，作为 XSS 的第二道防线——外链脚本限定为同源（`script-src 'self' 'unsafe-inline'`，内联脚本所需）、`object-src 'none'`、`base-uri 'none'`、`frame-ancestors 'self'`；`connect-src` 仅放行本机回环与（可选的）https 云端，未配置云同步时不产生任何跨域请求。
- **云同步**（加密版）：工作台上传前用 Web Crypto（PBKDF2 + AES-GCM）对数据做**端到端加密**，口令仅驻本机内存、不上传不落盘；云端仅存密文。PBKDF2 迭代次数为 600000（OWASP 对 PBKDF2-HMAC-SHA256 的建议下限），旧密文按其随包记录的 `iter` 值解密，升级不影响既有数据。集合权限建议在 CloudBase 侧设为「仅创建者可读写」。
- **云同步的配置面只信任本机**（重要）：从云端拉取数据时，`meta` 仅按**白名单**接受纯展示/偏好类字段；`meta.sync.sdkUrl`（会被当作 `<script src>` 加载）、`meta.calAttach`（会被内嵌渲染）与云端凭据 `env`/`code` **一律只取本机值、不从云端继承**。否则任一持有同步口令的设备即可在密文包裹中投毒，受害者下次保存即执行攻击者脚本，且该页与桥同源、可读到桥凭据。校历附件的内嵌页使用 `sandbox` 隔离且只接受图片 MIME。
- **云端凭据本地存储**：工作台把 `meta.sync` 的云凭据以混淆方式（XOR + 局部混淆）存入 localStorage，注意这**不是**密码学保密——它只防「肉眼在 DevTools 里瞥见」，不能防御能读取 localStorage 的本机攻击者。真正的机密性由端到端加密（口令不落盘）保证。
