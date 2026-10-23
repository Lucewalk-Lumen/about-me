---
name: workbuddy-expert-studio-toolkit
description: Reusable gates and validators for the WorkBuddy 专家开发工坊 (workbuddy-expert-studio) team — package manifest checks, length caliber, shard integrity, avatar reachability, script executability, three-baseline dead links, path-traversal test, zip structure, and green/red dual-proof. Zero third-party dependencies.
description_zh: WorkBuddy 专家开发工坊的自动质检工具包：核对包结构、清单字段、文档篇幅、成员构成、头像与链接可达性、脚本可运行性，并对打包结果做结构自查（确保校验既会正确拦截、也不误伤），零第三方依赖。
description_en: Deterministic gates and validators for the WorkBuddy 专家开发工坊 (workbuddy-expert-studio) team — manifest checks, length caliber, shard integrity, avatar reachability, script executability, three-baseline dead links, path-traversal test, zip structure, and green/red dual-proof. Zero third-party dependencies.
version: "1.0.2"
author: Xing Bu
---

# WorkBuddy 专家开发工坊 · 确定性门禁工具包（Toolkit）

本技能是 `workbuddy-expert-studio` 专家团内嵌的**确定性门禁工具包**，把可复用的开发纪律（规则编号注册表见同目录 `contract.yaml` 的 `rule_registry`）落成可运行的脚本。所有脚本仅用 Python 标准库，无第三方依赖。

> 位置说明（本包脚本布局约定，见 `references/workbuddy-expert-studio-pkg-ops.md`「一·附 脚本布局约定」）：本技能是**包级门禁能力的门面**，技能目录仅含 `SKILL.md` 与 `contract.yaml`；下表所列脚本文件位于**包根 `scripts/`**，从包根调用（见「调用方式」）。**包级工程脚本置包根、技能自带能力脚本置 `skills/<skill>/scripts/`** 属已声明约定，非布局不一致。`verify.py` 直接从 `contract.yaml` 读取 categoryId 枚举与合规硬指标阈值，不硬编码。

## 何时调用

- 成员落盘前 / 打包前：主理人或工程师跑 `verify.py` 做包级门禁（判据：知识库第 5 节合规硬指标）。
- 结构设计后：跑 `scripts/gates.py` 确认成员 agent 结构六要素齐全、清单条目全部存在。
- 实现分片后：跑 `scripts/gates.py` 确认主文件未超平台注入上限。
- 审计阶段：跑 `scripts/gates.py` 做链接三基准死链与路径穿越安全实测。
- 写任何新门禁时：用 `dual_proof.py` 证明它绿红双证。

## 文件清单

| 脚本 | 作用 | 对应纪律 |
|---|---|---|
| `scripts/verify.py` | 包级门禁：plugin.json 字段 + 顶层未知字段提示 + 版本真源 + frontmatter 一致 + G004 + zip 结构判据（`--zip`）+ 调用子门禁。退出码 **0 = 无 WARN 且无 FAIL；1 = 仅 WARN；2 = 有 FAIL**。**放行须以 `python3 scripts/verify.py --zip <包>.zip` 复核**——无 `--zip` 时 zip 结构未验证，会固定 exit 1（属预期，**不**作为放行依据） | contract.yaml / 知识库第 5 节 |
| `scripts/gates.py` | 统一子门禁：成员结构六要素 / 主文件长度 / 清单条目 / 头像可达性与体积 / 死链三基准 / 路径安全 / 脚本可执行性（py_compile + `--help` 冒烟） | 结构六要素 / C001·G005 / C005 / 知识库第 9 条 / pkg-ops ②质量 / pkg-ops 七维①安全 / R2 |
| `scripts/dual_proof.py` | 绿红双证自检（好输入过 + 坏输入拦；直接调用 gates.py 真实门禁函数） | G003 |
| `scripts/quality_eval.py` | 五维质量评估（体验层门禁：构成完整性 / 任务完成度 / 指令遵从性 / 事实辨别性 / 规则遵从性） | quality-eval |
| `scripts/sync_standards.py` | 官方标准漂移检测（默认**不联网**；对比 `knowledge/` 快照，发现漂移提示复核；SPA 外壳判 INCONCLUSIVE） | 知识库 |
| `scripts/make_avatars.py` | 生成**占位**头像（512×512 扁平字形，默认写 `avatars/_placeholder/`，**不**覆盖正式头像；见护栏） | 头像规范 |
| `scripts/render_flow_html.py` | 生成九阶段流程可视化 HTML（`assets/flow-report.html`，数据驱动、可嵌入交付物 / 二次优化） | flow-9stage |

## 外源资料采集伴侣

抓取官方文档或联网检索时，调用同包 `web-crawler` 技能（零依赖稳健抓取 / 尽力式检索），修复简单搜索的超时 / 编码 / 异常裸奔缺陷；JS 重度页面由 `web-crawler` 自动经本机 Edge 渲染，登录态 / 交互页优先用平台 browser-skill；不要在本工具包内重复造轮子。

## 包根解析范式（跨运行时一致，消除「平台根变量 vs 相对路径」冲突）

代理运行时指自身文件**用平台提供的根目录变量**（如 `${CODEBUDDY_PLUGIN_ROOT}`，见 `agents/agent-architect.md`）；但脚本经 Bash 执行时该变量不一定注入子进程。二者**指向同一目录**，脚本内用「由脚本自身位置解析包根」的范式等价获得，避免相对路径随工作目录漂移：

```bash
# 各脚本均可自解析包根；从包根调用时用法不变
PKG_ROOT=$(cd "$(dirname "$0")/../.." && pwd)   # scripts/ 的上一级即包根
python3 "$PKG_ROOT/scripts/verify.py"
```

> 一致性纪律：平台变量 `${CODEBUDDY_PLUGIN_ROOT}` 与 `$(dirname "$0")/../..` 必须解析到同一包根；脚本不得假定「当前工作目录 == 包根」。

## 调用方式

```bash
cd <包根>
python3 scripts/verify.py                      # 包级总门禁（含 gates.py 子门禁）；无 zip 参时跳过 zip 判据并提示
python3 scripts/verify.py --zip <包>.zip       # 附加 zip 条目结构判据（顶层前缀须唯一 == 包名；防目录改名绕过）
python3 scripts/gates.py <包根>                # 统一子门禁（构成/长度/清单/头像/死链/路径安全/脚本可执行性）
python3 scripts/dual_proof.py                  # 门禁绿红双证自检（调用 gates.py 真实门禁函数）
python3 scripts/sync_standards.py check        # 标准漂移检测（默认不联网；渲染后 HTML 用 --html=<file> 传入）
```

## 合同唯一事实源

规则与阈值定义见同目录 `contract.yaml`：`verify.py` 从中读取 categoryId 枚举、合规硬指标阈值与 `members_allowed_fields`；`gates.py` 从中读取长度 `warn_limit`、头像 `min_bytes` 等阈值——脚本内不再各写一份硬编码（仅保留文件缺失时的内置兜底）。改规则 = 改 `contract.yaml` + 重跑 `dual_proof.py` + 重跑 `verify.py`。
