---
name: browser-skill
version: 1.0.0
author: "Xing Bu"
description: |
  当用户要求对已登录浏览器执行自动化任务时使用：访问并读取页面、填写表单、
  采集数据、点击走完流程、回归验证页面 UI、校验已部署页面。
  需要已安装 bsk CLI 并加载 browser-skill 扩展。
---

# browser-skill

> **使用提示**：本技能驱动你**已登录的浏览器**完成页面访问与操作，底层能力由官方
> BrowserSkill 提供的浏览器扩展承担。建议仅在个人可信环境中使用；涉及银行、支付、
> 邮箱等个人账号页面时，请先与用户确认再操作。自动化操作在独立的 Agent Window 内进行，
> 不会主动使用用户日常标签页。

通过 `bsk` CLI 驱动用户**真实的 Chromium 浏览器**（连同其已登录状态）。扩展会开启一个隔离的 **Agent Window（自动化专用窗口）**；除非你显式借用（borrow）某个标签页，用户日常窗口不受影响。

## Security constraints (declared policy + skill-level enforcement)

The sensitive-domain restrictions below are **binding operating rules for this skill** (the `bsk` wrapper and the agent must observe them) and are enforced at skill level. They are **not carried by a `plugin.json` `permissions` field**; treat them as skill-level + policy constraints, not a platform sandbox guarantee.

- Navigation is restricted to the academic-publisher `domainAllowlist` (`*.cnki.net`, `*.webofscience.com`, `*.sciencedirect.com`, `*.springer.com`, `*.wiley.com`, `*.tandfonline.com`, `*.sagepub.com`, `*.emerald.com`).
- `bsk evaluate` (arbitrary JavaScript execution) is **forbidden** on sensitive domains matched by `sensitiveDomainDenyList` (`*bank*`, `sso.*`, `*password*`, `oauth.*`, `accounts.*`, `login.*`); `forbidEvaluateOnSensitive: true`.
- Tab `borrow` is limited to allowlist domains only (`borrowScope: "allowlist-only"`) and is force-released after `maxBorrowMinutes: 5`.

**Important:** Setting `BSK_REQUEST_HELP=off` does **NOT** exempt these restrictions. The agent must still observe the domain allowlist, the sensitive-domain `evaluate` ban, and the borrow scope above even when `BSK_REQUEST_HELP` is off. These are operating rules of this skill; if the platform does not enforce them centrally, the `bsk` wrapper and the agent are responsible for honoring them.

## 安装必读（必装，否则本技能完全不可用）

本技能**以纯文本形态交付**，`bsk` 二进制与扩展一律由官方渠道提供；本包已移除捆绑的 Chrome MV3 扩展目录（assets/extension/），能力完全由官方**腾讯 BrowserSkill 技能**提供（WorkBuddy 中单独安装，跨平台自带 `bsk` CLI 与 Chrome MV3 扩展）。完成后有两项确认步骤，**跳过则本技能不可用**：

1. 确认官方 **BrowserSkill** 技能已安装且 `bsk` 在 PATH：`command -v bsk` 确认有输出；macOS / Windows / Linux 均由其官方安装器自动处理（跨平台，无需本包提供二进制）。如需校验：`bsk --version`。
2. 在 **Chromium 内核浏览器**（Chrome / Edge / Brave）以「开发者模式 → 加载已解压的扩展」加载官方 BrowserSkill 技能提供的 Chrome MV3 扩展；弹出**绿色**即连接成功。

**装包 / 更新后，主理人会主动提醒你完成上述两步；未完成前请勿调用本技能。** Firefox / Safari 非 Chromium 内核，不支持。

**调用前强制预检（P4）**：实际驱动浏览器前，先通过 Bash 运行 `command -v bsk` 确认 `bsk` 已在 PATH——**无输出即停止，禁止跳过**；扩展连接与运行时状态由用户在浏览器确认（popup 显示绿色），或运行 `bsk doctor` 佐证。

## 何时使用

- 打开页面、读取标题/正文，从用户本就有权访问的站点采集结构化数据
- 填写表单、点击走完多步流程、对 UI 改动做冒烟测试
- 先用 `bsk snapshot` 理解页面；仅当 snapshot 不够时才用 `bsk get-html` 或 `bsk screenshot`
- 操作用户指定的某个标签页（先 `bsk tab borrow`）

## 何时不使用

- 任务**完全不涉及浏览器**（仅文件、API、数据库）
- 安装或配置扩展（应引导用户查看 setup 文档，而非代劳）
- **读取账号信息**——不在银行、SSO、密码管理器页面运行 `bsk evaluate` 读取本地存储或账号信息
- 长时间占用用户的个人登录窗口——只借当前步骤所需，用完即 `bsk tab return` 或结束会话
- 用户只想让你解释页面时，替用户进行人工浏览操作

## 前置条件

1. `bsk` 在 `PATH` 上——由**官方腾讯 BrowserSkill 技能**提供（跨平台 `bsk` Rust CLI，安装即自带，本包不再内置）。用 `bsk --version` 校验，再用 `bsk doctor` 做完整检查。**若 `bsk` 不在 PATH，不要硬跑 `bsk …` 指望侥幸——必然报 "command not found"。** 应告知用户安装官方 BrowserSkill 技能（或说明当前环境无浏览器自动化能力）并停止，而不是默默假设它可用。
2. browser-skill **扩展**已在 Chromium 加载并连接成功（popup 显示绿色）
3. 任意 `bsk` 命令会按需自动启动后台服务；失败时用 `bsk doctor` 诊断

## 强制工作流

每个自动化任务**必须**遵循以下生命周期。**不要**依赖空闲超时（会话默认空闲 5 分钟即回收）。

```
1. bsk session start              → 捕获 stdout 打印的 4 位会话 id
2. … 后续每条工具命令 …          → 一律携带 --session <id>
3. bsk session stop <id>          → 结束时必调（错误路径也不例外）
```

可选：连接了多个浏览器时用 `bsk session start --browser <实例id或标签>`（`bsk browsers` / 报错输出会列出）。

紧急清理：`bsk session stop --all`，或点 Agent Window 遮罩面板上的 **Stop all**。

## 达成目标即停止

每个任务都是**有界目标**，不是开放式浏览。目标可能来自用户的请求、已录制的 trace.json（由 bsk record 在运行时写出的操作轨迹文件），或两者兼有。

1. **先定义成功**——从用户原话、`purpose` 或 trace 最后一个有效步骤中提炼一条具体、可观察的达成条件（如"表单已提交""已加入购物车""开始播放"）。
2. **走最短路径**——snapshot → 操作 → 至多一次核验。不要游走、重试无关动作或堆叠探索步骤。
3. **达成即停**——成功条件满足后立即 `bsk session stop <id>`，除非用户明确要求保持会话（如"先别关""继续逛"）。
4. **成功后不动作**——目标达成后不再点击、刷新、跳转、重搜、切换标签页，也不做"再确认一下"。进一步验证属于新任务。
5. **受阻即暂停，不硬闯**——页面需要人工输入（登录、验证码、OTP、支付确认）或同一动作两次失败无进展时，调用 `bsk request-help`，不要盲目重试。见下文「请求人工协助」。
6. **拿不准时**——至多再做一次 `bsk snapshot`。看起来已达成即停；未达成就问用户，不要继续乱点。

**有 trace 时**：按序回放步骤，使用 `target` 的 role/name/tag 与原始 `value`/`selection` 字段。最后一步完成（或 `effect.navigated_to` / 成功提示满足）后，立即执行规则 3–4。trace 指导执行，但不会把控制权扩展到目标之外。

**无 trace 时**：用户的请求本身就是成功条件。满足即结束——停止规则同样适用。

## 核心交互循环

写操作只作用于 **Agent Window** 中的标签页（或你**借入**的标签页）。

```
bsk navigate <url> --session <id>
bsk snapshot --session <id>          → 无障碍树，含 @e1、@e2… 元素引用
bsk observe --session <id>           → 语义 VOM 视图；可能暴露 hover/focus 表面
bsk click @e3 --session <id>          → 或 bsk fill、bsk select、bsk press
bsk snapshot --session <id>            → 导航 / DOM 变化后再次执行
```

**元素引用在导航后失效**——新页面上点击、填写、选择前必须重新 snapshot。

优先使用最新 snapshot 给出的 `@eN` 引用，而非裸 CSS 选择器。语义有歧义时用 `--ref` / `--selector`（见 `bsk click --help`）。

## 观察优先级

先用 `bsk snapshot` 理解页面结构、正文、控件与元素引用。当语义 VOM 输出或条件性 hover/focus 表面确有帮助时使用 `bsk observe`。只有当最新观察回答不了问题时才升级到原始 HTML 或截图：

1. `bsk snapshot` —— 严格的静态页面理解与交互规划
2. `bsk observe` —— 语义 VOM 观察；可对条件性表面做有界感知探测
3. `bsk get-html` —— 需要隐藏 DOM、元数据或标记细节时
4. `bsk screenshot` —— 视觉布局、画布/图片内容或样式无法从观察推断时。用 `--ref @eN`（取自最新 snapshot/observe）裁剪到单个元素；省略 `--ref` 则截取整个可视标签页。

**不要**一上来就用 `bsk get-html` 或 `bsk screenshot` 看页面。

## 标签页归属规则

| 规则 | 说明 |
|------|--------|
| Agent Window | `bsk tab create`、`bsk navigate`、`bsk click` 等默认作用于 agent 标签页 |
| 用户标签页 | 借用前只读：`bsk tab list --session <id> --scope user` 后 `bsk tab borrow <tab-id> --session <id>` |
| 归还借用的标签页 | 用完调用 `bsk tab return <tab-id> --session <id>`；未归还的标签页会在 `bsk session stop` 时**自动归还** |
| 非 agent 写操作 | 标签页不在 Agent Window 内时，改动页面的命令会失败——先借用或新建标签页 |

## 全局参数

| 参数 | 用途 |
|------|---------|
| `--json` | stdout 输出机器可读 JSON（错误同样如此） |
| `--quiet` | 抑制提示性 stderr |
| `-v` / `-vv` | 更详细的日志 |

命令专属参数（超时、`--tab-id`、`--wait-until` 等）：**`bsk <cmd> --help`**

## CLI 命令速查（每条一行）

细节与参数：**`bsk <cmd> --help`**

### 诊断

| 命令 | 说明 |
|---------|---------|
| `bsk status` | 连接健康度、已连接浏览器、活动会话 |
| `bsk doctor` | 深度诊断与修复建议 |
| `bsk browsers` | 列出已连接浏览器实例（id、标签、版本） |

### 会话

| 命令 | 说明 |
|---------|---------|
| `bsk session start` | 打开 Agent Window；打印 **4 位会话 id** |
| `bsk session stop <id>` | 结束会话、关闭 Agent Window、自动归还借用标签页 |
| `bsk session stop --all` | 停止所有活动会话 |
| `bsk session list` | 列出活动会话 |

### 标签页（需 `--session <id>`）

| 命令 | 说明 |
|---------|---------|
| `bsk tab list` | 列出标签页（`--scope user\|agent\|all`，默认 `all`） |
| `bsk tab create` | 在 Agent Window 新建标签页（`--url`、`--no-active`、`--index`） |
| `bsk tab close <tab-id>` | 关闭 agent 标签页 |
| `bsk tab select <tab-id>` | 聚焦某个 agent 标签页 |
| `bsk tab borrow <tab-id>` | 把用户标签页移入 Agent Window |
| `bsk tab return <tab-id>` | 把借用的标签页还原到原窗口 |

### 观察（除注明外需 `--session`）

| 命令 | 说明 |
|---------|---------|
| `bsk snapshot` | 首选静态页面理解：无障碍树 + `@eN` 元素引用 |
| `bsk observe` | 语义 VOM 观察，可对条件性表面做有界感知探测 |
| `bsk get-html` | snapshot 不够时导出原始 HTML（token 成本高） |
| `bsk screenshot` | snapshot 不够时截 PNG：整个可视标签页，或 `--ref @eN` 裁剪到单个元素（`--out` 可选） |

### 导航

| 命令 | 说明 |
|---------|---------|
| `bsk navigate <url>` | 在 agent 标签页打开 URL（`--wait-until`、`--timeout`） |
| `bsk navigate-back` | 历史后退一步 |
| `bsk navigate-forward` | 历史前进一步 |
| `bsk reload` | 刷新当前标签页（`--hard` 绕过缓存） |

（`bsk navigate back` / `bsk navigate forward` 是等价子命令。）

### 交互

| 命令 | 说明 |
|---------|---------|
| `bsk click <ref或选择器>` | 点击元素（`--button`、`--click-count`、`--modifiers`） |
| `bsk fill <ref或选择器> --value <text>` | 清空并输入 |
| `bsk select <ref或选择器> --value <v>` | 按 `value` 设置 `<select>` 选项（多选时重复 `--value`） |
| `bsk press <key>` | 按键/组合键（`Enter`、`Ctrl+A` 等；可选 `--ref` 先聚焦） |

### 脚本与计时

| 命令 | 说明 |
|---------|---------|
| `bsk evaluate <expression>` | 在 agent 标签页执行 JS（见红线）；JS 抛错 → stderr，但**退出码 0** |
| `bsk wait-for-navigation` | 阻塞至 load/DOM 空闲等（`--wait-until`、`--timeout`） |
| `bsk wait-ms <duration>` | 睡眠（`500ms`、`2s`、`1m`；**无** `--session`） |

### 请求人工协助 —— `bsk request-help`

某一步需要人工（验证码、登录、OTP），或需要用户确认重要操作时，暂停并请求：

    bsk request-help --session <id> --prompt "解决验证码，待站点接受后再点 Done" \
      --title "需要验证码" --target @e7 --target "#submit" --timeout 5m

- `--prompt`（必填）：告诉用户要做什么。
- `--title`（可选）：遮罩面板的自定义标题；省略时扩展显示默认本地化标题。
- `--target`（可重复）：snapshot 引用（`@e7`）或 CSS 选择器（`#submit`），用于滚动定位并闪烁高亮。**强烈建议**——只要 prompt 涉及具体元素（要点的按钮、要填的输入框、要勾的复选框），就传入对应 `@eN` 引用/选择器，让用户直接定位而不是到处找。交互场景务必带上相关 target；无 `--target` 的请求仅用于确实没有具体元素可指的场景（如"等页面加载完成"）。
- `--timeout`（默认 `5m`）：等待时长。
- `--completion-criteria`（可选）：JSON 成功判据。仅当帮助完成后有明确成功信号时使用，如
  `{"any":[{"url_contains":"/dashboard"},{"selector_exists":"[data-testid='account-menu']"}],"stable_for_ms":1000}`。

目标标签页会被带到前台；用户操作期间隐藏 agent 控制遮罩，页面保持可交互。调用会阻塞，直到用户显式操作、超时、取消或显式完成判据命中。页面刷新、SPA 路由变化与验证码刷新本身不会交还控制权。返回的 `outcome` 取值之一：

- `continued` —— 用户完成并点了 Done / 交还控制（按确认处理）。
- `cancelled` —— 用户点了取消（按拒绝/中止处理）。
- `timed_out` —— 超时内无人操作。
- `completed` —— 用户操作期间显式 `--completion-criteria` 命中。
- `navigated` —— 仅表示发生过导航，不是完成信号。

`note` 携带用户回填的文本；`resolved_targets` 报告哪些引用/选择器命中了存活元素。

`request-help` 在交还控制后**不会**自动刷新页面模型。得到 `continued` 或 `completed` 后，先单独调用观察命令（通常是 `bsk snapshot --session <id>`），再使用新引用或推断帮助后的页面状态。
#### 关闭 request-help（无人值守模式）
无人值守服务器上可设 `BSK_REQUEST_HELP=off`：`bsk request-help` 将立即返回 `outcome="disabled"`（无遮罩、不等待、退出码 0）。其他取值保持启用。收到 `disabled` 不要重试——自主完成任务或体面收尾。

### 录制 —— `bsk record`

把用户在 Agent Window 中的实际操作录制为 trace.json（运行时写出的操作轨迹文件），供后续 LLM 驱动的自动化使用：

```bash
bsk record start --browser <实例id或标签> [--url https://…] [--purpose "发布一篇 wiki 文档"] [--output trace.json]
# `--url` 可选；省略时默认 https://example.com/（必须为 http(s)）。
# 阻塞直到用户在录制面板点击 Finish，随后写出 ./trace.json 并关闭窗口。

bsk record stop [--output trace.json]   # 浏览器面板不可用时的终端兜底
```

- trace 是**只记录的动作日志**（`pages[]` 字典 + `navigate`/`click`/`fill`/`select`/`press` 步骤及 `target` 描述符）。它记录*用户做了什么*；哪些输入是变量，由执行 agent 自行判断。
- `--purpose` 是可选的上下文元数据，**不会**改变录制内容。
- **没有** `bsk replay`——要重跑某流程，请读取 trace 并复用现有 `session` / `snapshot` / `@eN` / `click` / `fill` 工具，遵循「达成目标即停止」。
- **不要**在银行/SSO/密码管理器页面录制；密码会被脱敏，但 trace 仍可能含敏感文本。

## 错误处理

### 退出码（`bsk …` 之后 `echo $?`）

| 码 | 含义 | 处置 |
|------|---------|------------|
| `0` | 成功（含 `evaluate` 中 JS 抛错但 RPC 成功的情况） | 继续 |
| `1` | 用户错误——参数错误、会话不存在、标签页不在 Agent Window、引用过期 | 修正参数；`bsk session list`；重新 snapshot |
| `2` | 协议/传输——服务不可达、IPC 失败 | `bsk doctor`；检查扩展已连接；重试命令 |
| `3` | 浏览器 / CDP 执行失败 | 重试；简化选择器；确认标签页仍打开 |
| `4` | 超时 | 增大 `--timeout`；尝试 `--wait-until domcontentloaded` |
| `5` | 版本不匹配（CLI 与扩展） | 升级/重装配对版本 |

人为错误在 stderr 打印 `error:` + `hint:`；`--json` 则包含 `code`、`message`、`hint`、`exit_code`。

### 何时运行诊断

| 情形 | 命令 |
|-----------|---------|
| 会话内首个任务前 | `bsk status` —— 扩展已连接？ |
| 一次重试修不好的任何失败 | `bsk doctor` |
| 多浏览器 / 目标浏览器不对 | 先 `bsk browsers`，再 `bsk session start --browser <id>` |

务必在 `finally` 式路径中**`bsk session stop <id>`**，确保 Agent Window 关闭、借用标签页归还。

## 操作边界

1. **不读取账号信息** —— 不在个人账号页面用 `bsk evaluate` 读取 `localStorage` 或账号信息。
2. **禁止长期借用** —— 不得让用户的个人标签页在 Agent Window 里跨任务滞留。
3. **禁止跳过 stop** —— 必须 `bsk session stop <id>`；绝不指望空闲超时替你清理。
4. **禁止成功后继续操控** —— 用户目标（或 trace 最后一步）达成后不得继续操作页面；除非用户要求保持会话，立即停止。
5. **禁止跳过观察直接升级** —— 先 `bsk snapshot`；VOM 语义或条件性表面有帮助时用 `bsk observe`。仅当 snapshot/observe 不够时才用 `bsk get-html` 或 `bsk screenshot`。元素截图（`--ref @eN`）同样要求新鲜的观察引用——绝不为了抓图跳过观察。
6. **`evaluate` 为兜底手段** —— 仅当 snapshot + click/fill/select 均无法满足时使用；个人账号页面一律不用。

---

**任意命令的更多细节：** `bsk <cmd> --help`
