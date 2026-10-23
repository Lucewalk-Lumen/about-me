---
name: setup
description: "教学帮帮团一键初始化技能：装包后/首次会话/用户说『初始化/装依赖/配置环境/开箱即用』时触发，统一安装全部运行时依赖（Python 托管 venv + Node docx）、检测 crawler 的 bsk CLI、为 content-summary 生成 `.env` 凭证占位模板（仅占位、不含任何真实密钥），并写入初始化状态供主理人幂等判断。确保用户安装后无需手动配环境即可直接使用。"
version: 1.1.1
---

# 教学帮帮团 · 一键初始化（setup）
> **归属**：初始化层——**以「爬虫（crawler / bsk）安装」为首要职责**的一键初始化；同时装载全团 Python / Node 依赖与 LLM 凭证模板。


> 本技能解决「能力整合了但没落地生效」：团队 7 个技能依赖外部运行时（Python 库 / Node 库 / 外部 bsk CLI / LLM 密钥），原需用户首次使用时手动安装。本技能把它们统一在安装/首次会话阶段初始化，逼近「开箱即用」。

## [注意] 安装必读：crawler 必装提醒（装包 / 更新 / 重跑初始化时必看）

> **本团含浏览器自动化技能 `crawler`，它依赖一个「用户侧手动步骤」；装包或更新后若跳过，该技能将完全不可用，且不影响其余 11 项技能，极易被忽略。**
>
> 你（主理人）在**每次装包、更新、或重跑 `setup` 后**，都必须主动、醒目地提醒用户完成下面两件事——**这是必装项，不是可选项**：

1. **加载浏览器扩展（必做，浏览器安全限制无法自动化）**：官方 **BrowserSkill 技能**会提供 Chrome MV3 扩展的本地路径（按其技能说明获取）。用户须在 **Chromium 内核浏览器**（Chrome / Edge / Brave）中以「开发者模式 → 加载已解压的扩展」加载该路径；弹出面板显示**绿色**即连接成功。Firefox / Safari 非 Chromium 内核，不支持。
2. **确认 `bsk` 已在 PATH（必做）**：`bsk` 由官方腾讯 BrowserSkill 技能安装即自带（跨平台）；调用前应先 `export PATH="$HOME/.local/bin:$PATH"` 并用 `command -v bsk` 确认。若未检测到 `bsk`，请先在 WorkBuddy 安装官方「BrowserSkill」技能（本包不再随附二进制）。
3. **启动 daemon（必做）**：`setup` 部署 bsk 后**不会自动启动 daemon**，请手动执行 `bsk daemon start` 后再调用 crawler（或重跑 setup 时加 `--start-daemon`）。

> **未完成上述三步前，不得向用户宣称 crawler 可用。** 仅当扩展弹出绿色、`bsk status` 显示已连接，浏览器自动化才真正就绪。

## [注意] 安全知悉：bsk 由官方 BrowserSkill 提供

> **`crawler` 依赖的 `bsk` 由官方**腾讯 BrowserSkill 技能**提供（跨平台，运行时自带）**：其签名/公证状态以官方发布为准；本包不再随附任何二进制，故不存在本包层面的公证/隔离问题。
> 请知悉并自行评估风险：确认你信任官方来源（Tencent/BrowserSkill）后再安装该技能；若不安装或不加载扩展，crawler 前端浏览器自动化将不可用（不影响其余技能）。

> **[注意] 本包不下载 LibreOffice**：`setup` 仅安装 Python / Node 依赖与检测 `bsk`，**绝不下载** LibreOffice。如需办公文档转换，优先复用用户本机已装的 **WPS / 微软 Office**；仅在**无任何办公二进制可用**时才回退 `python-pptx` / `python-docx` 离线生成或平台内置 `tencent-pptx` / `tencent-docx` 技能。二进制探测见 `skills/ppt-maker/scripts/office_bin.py` 的 `find_office_bin()`（尊重 `OFFICE_BIN` 环境变量，命中即返回，**绝不下载**）。

## 触发条件

满足任一即触发：

1. **装包后 / 首次会话**：主理人检测到 `~/.workbuddy/teaching-helper-team/setup-status.json` 不存在或 `status != "ok"` 时，主动调用本技能完成初始化（幂等，已就绪则跳过）。
2. **用户明示**：用户说「初始化」「装依赖」「配置环境」「开箱即用」「为什么用不了 / 报错缺模块」等。
3. **运行前自检**：某技能脚本报 `ModuleNotFoundError` / `docx 库未找到` 等依赖缺失错误时，先跑本技能修复，再重试原任务。

## 执行步骤

1. 运行初始化器（用**任意可用 Python**，脚本本身零依赖）。**按需选择粒度，不要一上来就跑全量**：
   - **最快可用（推荐首次）**：`python3 skills/setup/scripts/setup.py --minimal` —— 只装 crawler 组（静态爬虫最小集，冷启动约 1 分钟）
   - 全量（幂等，自动跳过已完成组）：`python3 skills/setup/scripts/setup.py`
   - 按需装指定组：`--only crawler,ppt-maker`
   - 续装（默认行为，显式指定便于脚本化）：`--resume`
   - 强制重装：`--force`
   - 其他开关：`--json` 机器可读输出；`--skip-node` / `--skip-browser` 跳过单项
   - 包装脚本：macOS / Linux `sh skills/setup/scripts/setup.sh`；Windows（PowerShell）`pwsh skills/setup/scripts/setup.ps1`
2. 脚本自动完成：
   - 创建/复用 WorkBuddy 托管 venv：`~/.workbuddy/binaries/python/envs/teaching-helper-team`
   - 安装 Python 依赖（按技能分组，逐包容错）：crawler / text-to-speech / case-writer / ppt-maker / material-extractor / minutes-organizer 的全部库
   - 安装 Node `docx`（会议纪要 Word 输出依赖）
   - 检测 `bsk` 是否在 PATH（由官方腾讯 BrowserSkill 技能提供）；缺失则提示用户先安装该官方技能（本包不再随附二进制）
   - 为 content-summary 生成 `.env.example`（含全部 LLM 密钥占位）+ 创建 `.env`（占位，待用户填真实 key，**绝不硬编码**）
   - 运行 `deai_preflight` 自检，确认交付门禁脚本可用
   - 写入 `~/.workbuddy/teaching-helper-team/setup-status.json`（含 `venv_python` 绝对路径与逐项结果）
3. 读取报告：全 OK → 开箱即用；有 WARN → 按提示排查（多为网络/权限），重跑幂等修复。
4. **必装提醒（不可省略）**：无论全 OK 还是有 WARN，结束前**必须**向用户醒目提示 crawler 的两项必装手动步骤（见上方「[注意] 安装必读」）——明确告知：未加载扩展、`bsk` 未在 PATH 前，浏览器自动化不可用；并提示用户从官方 BrowserSkill 技能获取扩展路径与 `bsk` 路径。若用户尚未安装官方 BrowserSkill 技能，统一引导其从 WorkBuddy「专家中心 / 技能中心」安装。
5. **就绪口径**：`setup-status.json` 的 `status/browser` 字段仅代表**依赖层**就绪；crawler 前端是否真正可用，一律以 `crawler/scripts/verify_deploy.py`（`bsk doctor` 实测）为准（`extension connected` = ok 才算通）。向用户报告前端状态时禁止引用旧字段作放行依据。

## [注意] 关键约定：本团 Python 脚本必须用专用 venv Python 运行

`setup.py` 把所有依赖装进了**专用 venv**，而非系统 Python。因此编排调用本团任意 Python 脚本（路径形如 `skills/<分组>/<技能>/scripts/*.py`，例如
`skills/crawler/scripts/scrape.py`、`skills/case-writer/scripts/md_to_docx.py`、`skills/deai-rules/scripts/deai_preflight.py`）时，
**必须用专用 venv 的解释器**，禁止裸 `python3`。
（`skills/minutes-organizer/scripts/generate_docx.js` 是 Node 脚本，不走 venv Python，用 `node` 执行。）

**取解释器走三级探测**（任一命中即用）。**不要**用 `python3 -c` 去解析状态文件取路径——那要求先有一个可用的 python，未初始化时本身就会变成死循环：

- **L1 · 文本旁路（首选，免解析）**：`~/.workbuddy/teaching-helper-team/venv_python.txt` 的**首行**即解释器绝对路径；
- **L2 · 状态文件**：`setup-status.json` 的 `venv_python` 字段（需已有可用 python 才用）；
- **L3 · 目录候选**：`~/.workbuddy/binaries/python/envs/teaching-helper-team/Scripts/python.exe`（Windows）或 `.../bin/python`（POSIX）——直接可执行，不依赖任何解释器。

```bash
# L1 文本旁路（read 是 shell 内建，最稳）
IFS= read -r VENV_PY < "$HOME/.workbuddy/teaching-helper-team/venv_python.txt" 2>/dev/null
# L3 目录候选兜底
if [ ! -x "$VENV_PY" ]; then
  for c in "$HOME/.workbuddy/binaries/python/envs/teaching-helper-team/Scripts/python.exe" "$HOME/.workbuddy/binaries/python/envs/teaching-helper-team/bin/python"; do
    [ -x "$c" ] && VENV_PY="$c" && break
  done
fi
"$VENV_PY" skills/crawler/scripts/scrape.py "<url>"
```

> 三级全未命中 ⇒ 视为未初始化：先跑 `setup.py --minimal`（只装静态爬虫依赖，冷启动约 1 分钟）再取解释器。

> **耗时参考（区间口径，非通用常数）**：Python 3.13 冷启动 `--minimal` **端到端 54–62 s**
> （两次独立读数：**53.9 s** 与 **62.4 s**，差异主要来自 pip 网络抖动），其中 venv 创建约占 **17 s**。
> 注意**分项之和**（建 venv + 依赖安装）**低于**端到端读数，故一律以**端到端读数**为准。
> 幂等复跑（各组已就绪）**1.1–1.9 s**（直接跳过）；被中断后的 `--resume` 续装 **48.5 s**。
> 较低 Python 版本（如 3.9）因 `lxml` 等需编译或选旧 wheel，耗时可能不同。
> 因此包内统一使用「**冷启动约 1 分钟**」这一区间口径，**不再写秒级常数**。
> 这样做保证了「依赖隔离、不污染用户全局环境」，同时让现有脚本无需逐处改造即可开箱运行。

## 凭证处理（安全底线）

- content-summary 的 LLM API key **只生成占位模板**（`.env.example` / `.env`），真实值由用户自行填写，密钥**绝不写入代码、配置或提交明文**（与 content-summary SKILL 的 Keychain 原则一致）。
- `crawler` 依赖官方腾讯 BrowserSkill 技能提供的 `bsk` 与 Chrome MV3 扩展（本包不再随附二进制），`setup` 仅检测 `bsk` 是否就位；但浏览器扩展**须用户手动加载**（见上方「[注意] 安装必读」），这一步无法自动化。

## 退出码

- `0` = 全部就绪
- `1` = 部分完成（有可恢复 WARN，如 bsk 未装、某依赖网络失败）
- `2` = 环境不支持（无任何可用 Python）

## 已初始化状态判定（供主理人）

- 文件 `~/.workbuddy/teaching-helper-team/setup-status.json` 存在且 `status == "ok"` → 视为已初始化，跳过。
- 文件缺失 / `status == "partial"` / `status == "in_progress"` → 在首次会话主动触发本技能（但**不阻塞**用户任务：若用户已明确要求干活，**先应答并推进任务**，同时以 `--minimal` 起手，后续按需补装）。
- **逐组进度**：状态文件的 `groups` 字段记录每个组的 `ok` / `failed`，`details` 保留各组明细。据此可精确知道「已装哪些 / 还差哪些」——中途中断后用 `--resume` 续装即可，不必全量重来。
- **解释器旁路**：`venv_python.txt`（单行纯文本）与 `setup-status.json` 同时写入；前者供**免解析**读取解释器路径。
