---
name: crawler
version: 1.1.1
description: >
  爬虫采集基础能力：后端静态采集（requests + BeautifulSoup4，CSS 选择器 + 表格/列表检测 → JSON/CSV/MD，分页跟随）
  与前端已登录会话浏览器采集（官方 Chrome MV3 扩展由腾讯 BrowserSkill 技能提供，bsk 驱动用户已登录的真实 Chromium）双模式，
  由主理人 lead 按选型决策树统一路由。服务案例/论文/课程/纪要等专家采集政策、案例素材、文献数据。
---

# 爬虫采集（crawler）

> **归属**：基础能力层（foundation）——第1.位「采集」，挂主理人 lead，按需路由；领域专家的 crawler 前置依赖由主理人 lead 在「能力依赖层级」表中统一登记与维护。

本技能把「网页 → 结构化数据」的采集能力收敛为单一入口，内部含**双模式**：

| 模式 | 引擎 | 适用场景 | 详见 |
|------|------|---------|------|
| **后端静态采集** | requests + BeautifulSoup4（动态页可选 Playwright） | 公开静态页轻量批量结构化提取（JSON / CSV / MD） | `references/static-scraper.md` |
| **前端已登录会话采集** | bsk 驱动真实浏览器（Chrome MV3 扩展由官方 BrowserSkill 技能提供） | 需已登录会话 / 会话凭证 / 鉴权、复杂交互、真实渲染 | `references/browser-automation.md` |

## 选型决策树（路由约定）

1. 目标需已登录会话 / 鉴权 / 会员内容？ → **前端（browser-automation）**
2. 否则公开静态页结构化提取？ → **后端（static-scraper）**（先 `structure` 探测，取不到再加 `--js`）
3. 重度 JS 渲染且 `--js` 仍取不到？ → **前端（browser-automation）**
4. 动态 / 反爬严、需人工过验证码？ → **前端（browser-automation）**（`request-help`）

> **前端路由闸门（脚本化强制）**：决策树路由到**前端**后、执行任何 `bsk` 命令前，**必须先运行部署预检脚本，退出码 0 才放行**：
>
> ```bash
> "$VENV_PY" skills/crawler/scripts/verify_deploy.py            # 前端闸门
> "$VENV_PY" skills/crawler/scripts/verify_deploy.py --doctor   # 环境总览：一条命令回答「爬虫到底能不能用」
> ```
>
> （脚本零第三方依赖，任意 Python 均可运行。）
>
> 退出码语义：`0` 就绪可调用 / `1` 官方 BrowserSkill 未安装（`BSK_MISSING`）/ `2` daemon 未运行 / `3` 扩展未连接 / `4` bsk 异常或输出不可解析 / **`5` bsk 无响应（已超时终止，不再挂起）**。脚本 stdout 自带对应处置引导（含从「专家中心 / 技能中心」安装官方 BrowserSkill、手动加载扩展的具体步骤）。
>
> `--doctor` 会额外报告**解释器**与**静态依赖**两项，便于一次看清「静态采集 / 前端采集」各自是否可用。
>
> - **非零退出 → 中止前端分支**，按提示处置后重跑脚本；**不得按历史部署记录或 setup-status 旧状态放行**。
> - 未就绪期间：任务若可静态完成 → 改用**后端静态模式**并在交付时注明覆盖缺口；任务必须已登录会话 → 如实告知用户前端能力暂不可用及补齐步骤，**禁止伪造采集结果**。
> - 脚本缺失或不可执行时的处置：手工执行 `browser-automation.md` 的「调用前运行时检测」（`bsk doctor` 实测），判定标准与脚本一致。

## 共用合规基线（两模式均须遵守）

- 默认遵守 robots.txt（`--ignore-robots` 需显式授权并留痕）
- 默认 1 req/s（`--delay` 可覆盖）
- SSRF 防护：拦截私网 / 回环地址（10/8、172.16/12、192.168/16、127/8、169.254/16）
- 敏感数据（PII / 凭证）不入库，仅留元信息
- 采集内容须遵守目标站点版权与 robots

## 部署与依赖

- **后端**：`requests` / `beautifulsoup4` / `lxml` 由 `setup` 装入托管 venv（`$VENV_PY`），`--js` 动态渲染可选 Playwright（不默认装）。
- **前端**：依赖**官方腾讯 BrowserSkill 技能**提供的 `bsk` CLI 与 Chrome MV3 扩展（本技能不再随附二进制，扩展目录亦已随安全门禁移除，不随包分发）。安装该官方技能后，`setup` 首次会话会检测 `bsk` 是否已在 PATH；扩展加载与 `bsk daemon start` 为必做手动步骤（见 setup「安装必读」）。
- **版本/来源**：`bsk` 由官方 Tencent/BrowserSkill 提供（跨平台，运行时自带，版本随官方技能更新）。本技能不再随附二进制，亦不再维护本地 SHA256 基线；请以官方技能的安装/更新为准。
- 运行解释器统一 `$VENV_PY`（**三级探测**取值，见 `skills/setup/SKILL.md`），禁止裸 `python3`。

## 输出与数据契约

采集产物落数据总线 `data/pipeline/incoming/`，命名 `{task_id}_scrape_crawler.{format}`（见 `skills/_shared/DATA-CONTRACT.md`），由主理人 lead 读取后转发给下游领域专家。

## 与 foundation 流水线的位置

crawler 是 foundation 的**按需入口**——仅当用户未提供现成材料、需在线采集时才启用；用户已提供材料时跳过本步，直接进入 `material-extractor` 或 `content-summary`。
