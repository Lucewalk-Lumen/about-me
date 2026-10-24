---
name: crawler-static
description: "智能网页采集：CSS 选择器 + 表格/列表自动检测 → JSON/CSV/Markdown，支持分页跟随。用于案例写作专家/论文辅导专家的行业政策、案例素材、文献数据采集。"
version: 1.1.1
---

# Smart Web Scraper 数据采集
> **归属**：基础能力层（foundation）· crawler **后端静态采集模式**——与前端 bsk 模式互补；由 `setup` 安装、主理人 `lead` 按选型决策树统一路由。
>
> 选型路由与共用合规见 `../SKILL.md` 的「选型决策树」。


> 从任意网页提取结构化数据，是教学帮帮团的**数据采集工具**（服务案例写作专家与论文辅导专家）。实现见 `scripts/scrape.py`（WorkBuddy 托管 Python 运行时运行），静态用 requests+BeautifulSoup4，动态 JS 页可选 Playwright。

## 前置条件（必须先完成，否则无法运行）

1. **初始化环境**：首次使用前由主理人调用 `setup` 技能一键初始化（幂等）——本技能的 requests/bs4 依赖装入**专用 venv**（`~/.workbuddy/binaries/python/envs/teaching-helper-team`），**禁止单独裸 `pip install`**（会装错 Python 环境）。Playwright（`--js` 动态渲染）为可选，setup 不默认安装，需要时按「动态页面」节补装到同一 venv。
2. **运行解释器**：本团 Python 脚本必须用**专用解释器**（见 `skills/setup/SKILL.md` 的关键约定），**禁止裸 `python3`**。
   取解释器走**三级探测**（任一命中即用）。**不要**用 `python3 -c` 去解析状态文件——那要求先有一个可用的 python，未初始化时本身就会变成死循环：

```bash
# L1 文本旁路（首选，免解析）：首行即解释器绝对路径
IFS= read -r VENV_PY < "$HOME/.workbuddy/teaching-helper-team/venv_python.txt" 2>/dev/null
# L3 目录候选（直接可执行，不依赖任何解释器）
if [ ! -x "$VENV_PY" ]; then
  for c in "$HOME/.workbuddy/binaries/python/envs/teaching-helper-team/Scripts/python.exe" "$HOME/.workbuddy/binaries/python/envs/teaching-helper-team/bin/python"; do
    [ -x "$c" ] && VENV_PY="$c" && break
  done
fi
```

> 三级全未命中 ⇒ 视为未初始化：先跑 `setup.py --minimal`（冷启动约 1 分钟）再取解释器。

## 命令（scripts/scrape.py，用 `$VENV_PY` 运行）

```bash
$VENV_PY skills/crawler/scripts/scrape.py extract <url> --selector "<css>" --format json
$VENV_PY skills/crawler/scripts/scrape.py tables <url> --format csv
$VENV_PY skills/crawler/scripts/scrape.py links  <url>
$VENV_PY skills/crawler/scripts/scrape.py structure <url>
$VENV_PY skills/crawler/scripts/scrape.py crawl  <start-url> --pages 5 --format md
```

- 各子命令支持 `--format text|json|csv|md`（默认 text）
- 动态页加 `--js` 走 Playwright 渲染路径（见下方「动态页面（JS 渲染）」）
- `--ignore-robots` 显式忽略 robots.txt（需授权留痕）；`--delay` 调整请求间隔（默认 1s）
- 分页爬取 `crawl` 仅跟随同域链接，最多 `--pages N` 页

## 输出

结果输出到标准输出，支持 `--format text|json|csv|md`（见上方命令说明）；建议重定向至**数据总线目录**（由 setup 初始化时创建）：`$VENV_PY skills/crawler/scripts/scrape.py ... > ~/.workbuddy/teaching-helper-team/data/pipeline/incoming/{task_id}_scrape_{skill}.md`（命名规范见 `skills/_shared/DATA-CONTRACT.md`）

## 合规与限速（强制）

- **默认遵守 robots.txt**（`--ignore-robots` 需显式授权且留痕）
- **默认 1 req/s**（`--delay` 可覆盖）
- 采集前 robots 预检：目标 Disallow → BLOCKED，不重试
- 采集 URL 经 SSRF 防护（拦截私网/回环地址 10/8、172.16/12、192.168/16、127/8、169.254/16）、遵守目标站点 robots.txt、限速 1 req/s；禁止采集内网/回环地址。
- 敏感数据判定（SD-01~04）：命中个人身份信息/凭证 → 不入库，仅留元信息

## 使用场景

- 电商价格/库存
- 金融财务数据（研究分析用）
- 博客/新闻归档（分页）
- 站点架构映射（内外部链接网络）

## 注意事项

- 目标站点内容须遵守 robots 与版权；敏感数据（个人身份信息 / 凭证）不入库

## 动态页面（JS 渲染）

默认采集器基于静态 HTML（BeautifulSoup4）。遇到 SPA / 重度 JS 渲染页面（内容由前端脚本异步加载，`structure` 检测到空 body 或目标数据缺失）时，加 `--js` 走 Playwright 渲染路径：启动无头 Chromium，待网络空闲后提取。

- 浏览器引擎依赖通过 WorkBuddy 托管的 Python 运行时安装与运行（与团队其余 Python 脚本一致），不在技能包内捆绑二进制。
- 动态采集同样受上方「合规与限速」约束：遵守 robots.txt、默认 1 req/s、SSRF 防护、敏感数据不入库；无头浏览器不得绕过站点明确禁止的访问。

> 判断准则：先用 `structure <url>` 确认能否取到目标数据；取不到再加 `--js` 升级到 Playwright 渲染路径，避免在静态页上无谓启动浏览器。

## 与 crawler 前端模式（bsk）的分工与衔接

本模式（crawler 静态采集）面向**公开、无需已登录会话**的网页，做轻量批量结构化采集（CSS 选择器 + 表格/列表自动检测 → JSON/CSV/MD，分页跟随）。

遇到以下情况**不要硬用本技能**，应改由 crawler 前端模式（bsk 驱动用户已登录的真实浏览器）处理：
- 目标站点需已登录会话 / 会话凭证 / 鉴权（学术库、需登录的检索页、会员内容）
- 需要复杂交互（多步表单、点击展开、滚动加载、验证码绕过）才能拿到数据
- 重度 JS 渲染且 Playwright 无头路径仍取不到（交由真实浏览器更稳）

两模式由主理人（`agents/teaching-helper-team-lead.md` 的「素材工具职责边界 / 路由约定」）统一路由；crawler 静态模式产出结构化数据落数据总线 `~/.workbuddy/teaching-helper-team/data/pipeline/incoming/`，crawler 前端模式产出由主理人收口后同样入数据总线。完整浏览器自动化能力见 `skills/crawler/references/browser-automation.md`。

**路由前检查 crawler 前端 bsk 是否已部署**（未部署会直接失败）：`bsk --version` 可执行 + Chrome/Edge 已加载扩展（绿色连接）。未部署时先让主理人调 `setup` 技能（含 bsk 部署 + 手动加载扩展步骤），或用 crawler 静态模式 `--js` Playwright 路径临时切换。
