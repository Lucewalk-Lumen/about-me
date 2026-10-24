# 浏览器采集能力接入（browser-skill 集成标准）

> 面向采集员（campus-ppt-collector）。定义**如何真正调用**官方 `browser-skill`（`bsk` CLI）：
> **可用性预检 → 会话生命周期 → 深链采集 → 收尾归还 → 不可用降级**。
> 与 `crawler-collection-standard.md` 配套：那份讲"采什么、标准是什么"，这份讲"**用什么调、怎么调通、调不通怎么办**"。

## 〇、先分清："点名依赖"不等于"真融入"

本包**不内置** browser-skill（它是独立的官方技能，需在技能中心安装/启用），但采集环节**运行期必须接入**。
判定"真融入"的四条硬指标，缺一即为"只点名、未融入"：

| # | 指标 | 缺失后果 | 本文件位置 |
|---|------|---------|-----------|
| 1 | **有调用契约**：写清用什么命令、按什么顺序 | 采集员不知道 `bsk` 怎么用，只能退回简单搜索 | §二 |
| 2 | **有可用性预检**：采集前先探测 | 命令不存在/守护进程未起时卡死或空转 | §一 |
| 3 | **有降级路径**：不可用时如何交付 | 整条链路阻塞，用户拿不到东西 | §五 |
| 4 | **有前置声明**：用户知道要先装/启用 | 用户以为装完包就能用，实跑即失败 | `README.md §六` |

## 一、可用性预检（采集第 0 步，强制）

**在发出任何采集动作之前**，先探测 browser-skill 是否可用。禁止跳过——跳过会导致空转或误报"站点不可达"。

```sh
# 1. 探测守护进程与浏览器连接状态（不自动拉起）
BSK_AUTO_START=0 bsk status --json
```

判读（**实测口径**，bsk 0.3.2）：
- **可用**：返回体含 `browsers` 数组且非空 → 进入 §二。
- **扩展未连接**：返回体正常但 `browsers` 为空数组 → 提示用户打开浏览器扩展完成配对，或转入 §五 降级。
- **不可用**：**命令退出码 ≠ 0，或返回体只有 `message` / `hint` / `exit_code` 而无 `browsers` 字段** → 转入 §五 降级，**不要反复重启守护进程**。

> **真实失败样本**（实测）：当守护进程未就绪时，`bsk status --json` 返回 `{"code": null, "message": "ensure daemon is running: …", "hint": "…", "exit_code": 2}` 且**进程退出码为 2**。因此**不要只 grep `message` 就判死**——以**退出码**与**是否存在 `browsers` 字段**为准。

```sh
# 稳健写法：先看退出码，再看是否有 browsers
BSK_AUTO_START=0 bsk status --json > /tmp/bsk_status.json 2>&1
rc=$?
# rc != 0 或 JSON 无 browsers 字段 → 不可用 → §五 降级
```

> **沙箱约束**：在逐命令隔离的沙箱中，环境变量不跨调用保持，**每条 `bsk` 命令都要带上同一个 `BSK_HOME` 与 `BSK_AUTO_START=0`**。
> 若宿主在每个 shell 调用后清理后台子进程，需按 browser-skill 官方文档在宿主的持久后台任务中起守护进程；`--foreground` 单独使用无法阻止宿主回收。

## 二、调用契约（会话生命周期）

一次采集任务 = 一个会话，严格按"**起 → 用 → 停**"三段式，**不要跨任务复用会话、不要用别的任务的会话 ID**。

```sh
# ① 起：开一个会话，记下 session_id
bsk session start --json            # 多浏览器时先 bsk browsers，再加 --browser <id-or-label>
                                    # 后台任务加 --no-focus（仅 session start 支持）

# ② 用：所有会话级命令都必须带 --session <id>
bsk navigate "https://…" --session <id>   # 新页面先导航（navigate back/forward 走历史）
bsk observe --session <id>          # 读取页面文本、控件与 @eN 引用（首选）
bsk click @e3 --session <id>        # 点击
bsk fill  @e3 --value "文本" --session <id>
bsk select @e3 --value "option-value" --session <id>   # 用 option 的 value，不是可见文字
bsk press Enter --ref @e3 --session <id>
bsk scroll-to @e3 --session <id>    # 长页面定位；wheel 发滚轮增量
bsk snapshot --session <id>         # 静态可访问性树
bsk get-html --session <id>         # 精确 markup / 隐藏元数据
bsk screenshot --session <id> --full-page --out page.png   # 视觉证据
bsk wait-for-navigation --session <id>   # 等待页面生命周期事件（动态站很有用）
bsk console --session <id>          # 读缓冲的 console/log/异常（诊断用）
bsk network --session <id>          # 读缓冲的网络响应/失败（诊断用）

# ③ 停：成功与失败都要停（同时归还借用的标签页）
bsk session stop <id>               # 查活跃会话：bsk session list --json
```

> **实测子命令集**（bsk 0.3.2，`bsk --help`）：`status` `doctor` `session{start,stop,list,request}` `browsers`
> `tab{list,create,close,select,borrow,return}` `window` `emulate` `screenshot` `snapshot` `observe`
> `console` `network` `debug` `get-html` `navigate[back,forward]` `reload` `click` `hover` `wheel`
> `scroll-to` `focus` `blur` `fill` `press` `select` `upload` `download` `evaluate`
> `wait-for-navigation` `wait-ms` `request-help` `record`。
> 采集常用：`observe` / `navigate` / `get-html` / `screenshot` / `download`；排障：`doctor` / `logs` / `console` / `network`。

**引用（ref）铁律**：
- 导航会**作废全部 ref**；较大的 DOM 变化也会让 ref 失效。**每次交互前重新 `observe`**，绝不复用上一页的 ref。
- 大页面用 `observe --max-tokens <n>`，返回 `next_cursor` 时用 `bsk observe --cursor <token> --session <id>` 续读；**续读期间不要刷新、不要 hover 探测**，也不要与深度变更混用。
- CSS 选择器只在主文档搜索；iframe / shadow-root 内必须用 ref。

**借用用户标签页（仅当采集需要用户已登录的页面时）**：
```sh
bsk tab list --scope user --session <id>
bsk tab borrow <tab-id> --session <id>     # 相关步骤一结束立即归还
bsk tab return <tab-id> --session <id>
```
- 不臆造 tab ID、不跨任务长期占用用户标签页、不重复已 pending / denied / timed_out 的借用。
- 远程内容的读取与操作**必须**基于本任务创建或借用的标签页；页面自身弹出的窗口不会自动获得控制权。

## 三、人在环（登录 / 验证码 / 授权）

遇到登录、CAPTCHA、短信验证码、支付确认、授权同意，或**连续两次尝试无进展**时：

```sh
bsk request-help --session <id> --prompt "请完成登录" --target @e3
```

- `prompt` 要具体，`--target` 用新鲜 ref；无合适控件时省略 `--target`。
- 返回 `continued` / `completed` → 重新 `observe`，用新 ref 继续。
- 返回 `cancelled` / `timed_out` → **尊重拒绝，不要重复请求**。
- 帮助被禁用（`disabled`）时：**不得自行开启或绕过**。改用既有登录态、用户已授权输入与可行替代；仅验证码/人脸等无替代项的，如实报告具体阻塞点，然后**继续完成不依赖它的独立部分**，不要原地死循环。

## 四、安全红线（不得触碰）

- **绝不**提取、打印、外传凭据、Cookie、Token 或任何密钥。
- **绝不**通过改动浏览器存储/设置来绕过借用确认或人工帮助开关。
- 远程上传/下载不受支持；需截图时截图可用。
- 站点不可达、内容受限、需权限——一律**如实标注**，不绕过鉴权、不伪造原文。

## 五、降级路径（browser-skill 不可用时照常交付）

预检（§一）判定不可用、或采集途中会话反复失败时，**不阻塞链路**，按序降级并在报告中如实声明：

| 情形 | 降级动作 |
|------|---------|
| 扩展未连接 | 提示用户在浏览器扩展中完成配对；先做不依赖浏览器的资料整理 |
| 守护进程/CLI 不可用 | 提示用户在技能中心确认 browser-skill 已安装/启用；本轮改为"基于用户已提供资料 + 可用检索"整理 |
| 目标站点受限（登录/权限/反爬） | 标注"受限未获取"，列入待核实清单交用户补充，**不绕过、不编造** |
| 环境完全无浏览器能力 | 输出**降级版采集报告**：仅整理用户已提供的材料与可得信息，明确标注"以下内容未经在线交叉验证" |

**降级 ≠ 免责**：降级时必须写清"哪一步没做、为什么、用户可如何补齐"，并在产物中把未经交叉验证的条目标记为**未验证**（对应质检"事实辨别性"维度），不得冒充已核验资料。

## 六、与采集标准的衔接

- `crawler-collection-standard.md` 的六项必备检查（C1–C6）中，C5「站点可用性探测」与 C6「失败重试」由本文件的预检与降级机制落地。
- 每次采集报告末尾的"边界声明"应写明：**本次是否使用 browser-skill、是否发生降级、降级原因**。
- 若发生降级，采集报告须在来源表增加一列标注每条资料的获取方式（浏览器在线 / 用户提供 / 未验证）。

## 七、实测记录（bsk 0.3.2）

**环境实况**：`bsk status --json` 返回 `daemon_version 0.3.2` / `protocol_version 1.3` / 1 个已连接浏览器（Edge 154，扩展 0.3.2，`version_skew=false`）/ `sessions=[]`。

**契约实跑（真实会话）**：
```sh
bsk session start --json                 # → session_id="frun"；interaction: borrow_confirmation=always, request_help=enabled
bsk navigate "https://example.com" --session frun --json   # → {tab_id, url, final_url, reached:"load"}
bsk observe --session frun --max-tokens 400                # → VOM 树 + 结尾 "@more observe --cursor <uuid>"
bsk observe --cursor <uuid> --session frun                  # → "@continued same observation; only refs in this response are current." + @eN 引用
bsk session list --json                                    # → 活跃会话 1 条
bsk session stop frun --json                               # → {"stopped":["frun"], "failed":[], "return_failures":[], "returned_tab_ids":[]}
```
**结论**：`start → navigate → observe → cursor 续读 → list → stop` **全链路真实跑通**；本文件 §二 记录的调用契约与真实命令一致。

**降级触发实测**：将 `BSK_HOME` 指向空白目录（等价守护进程未就绪）后，`bsk status --json` 返回
`{"code":null,"message":"ensure daemon is running: …","hint":"…","exit_code":2}`，**进程退出码 = 2**。
→ 判定规则以**退出码 ≠ 0 或 缺 `browsers` 字段**为准（见 §一），可稳定触发 §五 降级。

**已知限制**：① `bsk` 版本演进快（实测 0.3.2），新增/改名子命令以 `bsk --help` 为准，本文件的命令集需随版本复核（衔接 `standards-watch.md`）；② 借用用户标签页受扩展 `borrow_confirmation=always` 约束，需用户在浏览器内确认；③ 本文件不覆盖 `record` / `emulate` / `debug` 等高级命令的用法。
