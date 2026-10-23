# 投研星图团（touyan-expert-team）

> 团队型投研专家包，覆盖投研全链路：热点扫描、个股深研、技术复盘、组合策略、事件解读。

- **slug**: `touyan-expert-team`
- **版本**: v1.0.0
- **类型**: 团队型专家（expertType: team）
- **分类**: 08-FinanceInvestment
- **标准**: 团队型专家包，遵循 WorkBuddy 专家团规范（见 open.workbuddy.cn/docs/expert-team）

## 团队定位

投研星图团把三个互补的投研角色整合为一个可协作的整体，覆盖「研究 → 决策 → 执行」的投研全链路：

| 阶段 | 能力 | 负责角色 |
|------|------|---------|
| 研究上游 | 热点扫描、行业/主题研究、深度研报、对比决策、组合策略、事件解读 | 投研总览官（主理人） |
| 机会发现 | 政策/资金/事件三重信号验证，输出值得研究的方向 | 热点扫描官 |
| 研究深水区 | 个股全景研报、盘前/盘后复盘、持仓监控、数据守门 | 个股深研官 |
| 技术验证 | K 线量价结构、多周期复盘、支撑压力、风险边界（含 CSV 离线） | K线技术复盘官 |

## 子角色

| Agent ID | 角色 | 职责 |
|----------|------|------|
| `touyan-expert-team-lead` | 投研总览官（主理人，裴览） | 理解意图、路由子角色、汇编交付 |
| `hotspot` | 热点扫描官（闻烽） | 政策/资金/事件三重信号验证，输出值得深入研究的方向 |
| `stock` | 个股深研官（沈潜） | 个股全景研究、盘前盘后、持仓监控、数据守门 |
| `kline` | K线技术复盘官（秦砺） | K 线技术复盘、多周期、量价、支撑压力、CSV 离线 |

## 内置技能（18 个）

包内置 18 个技能，覆盖热点扫描、公司深研、行业主题研究、对比决策、组合策略、个股监控、A 股/美股实时行情与历史 K 线、策略回测、数据守门等，统一支撑 A / A+HK / A+HK+US 市场：

`hotspot-discovery` · `company-deep-analysis` · `industry-theme-research` · `compare-decide` · `portfolio-strategy` · `claw-stock` · `eastmoney-mx-skills-suite` · `xiaodi-financial-analysis-team` · `akshare-finance-data` · `mx-stocks-screener` · `astock-report` · `china-stock-analysis` · `claw-stock-watcher-pro` · `akshare-stock` · `stock-monitor-skill` · `kline-candlestick-reader`（注册名 `kline-market-data`，含 CSV 离线复盘） · `us-market-data` · `strategy-backtest`

## 数据守门（全团统一硬约束）

涉及 A 股 / A 股 ETF 的实时行情，一律先调用守门脚本核验，`status=ok` 才能输出确定数字：

```bash
python3 ./skills/astock-report/scripts/market_data_guard.py quote <股票名或代码> --json   # Windows 用 python
```

所有带时间属性的数据必须标注「来源 + 取数时间/交易日期」；不可验证时标注「暂未获取 / 待核实」，严禁编造或补数。本团所有输出仅供参考，不构成投资建议。

## 治理文档（包级单一真源）

为把「团队编排 + 数据守门 + 可审计交付 + MCP 安全接入」做成一致的工程纪律，包内置数据/输出/覆盖/接入四份治理文档，所有 agent 与取数型 skill 均须遵守：

- **`DATA_GUARDRAILS.md`** — 数据守门单一真源：七项校验、status 约定、降级协议（主动说明+双选项，禁止静默回退/伪造）、反模式清单。
- **`OUTPUT_CONTRACT.md`** — 输出契约 + 0–100 质量评分 rubric + 溯源四要素（来源/时间/状态/置信度）+ 红线。
- **`COVERAGE.md`** — 各技能市场覆盖范围（A / A+HK / A+HK+US）与降级路径矩阵。
- **`TRADER_MCP.md`** — 交易/行情/妙想 MCP 接入契约与护栏：东方财富 EMTL（唯一执行/操盘手类）、东方财富妙想（数据+模拟盘，非实盘）、腾讯自选股 westock-mcp、通达信 tdx-mcp 的协议、配置、权限与 fail-closed / 双阶段意图护栏；默认全部关闭。

## MCP 接入

本团可接入四类 MCP，**默认全部关闭**（见 `config/feature_flags.yaml` 的 `trader_mcp` 段）：东方财富 EMTL 为唯一执行类（操盘手），东方财富妙想为数据+模拟交易（模拟盘，非实盘），腾讯自选股 westock-mcp / 通达信 tdx-mcp 为数据/行情类（用户可接自己账号查看自选股）：

| MCP | 类别 | 接入方式 | 默认 |
|-----|------|---------|------|
| 东方财富 EMTL | 交易/账户（含 `create_order`/`cancel_order`） | `~/.workbuddy/mcp.json`（stdio, uvx），凭据走 env | 关（observe-only） |
| 东方财富妙想 | 数据 + 模拟交易（`mx_*` / `mx_stock_simulator_*`，模拟盘非实盘） | `~/.workbuddy/mcp.json`（stdio, python -m），env `MX_API_KEY` | 关（模拟盘） |
| 腾讯自选股 westock-mcp | 行情/连接器（数据） | 包声明 `dependencies.connectors`，连接器面板连接 | 关 |
| 通达信 tdx-mcp | 行情/K线（数据，无需 Key） | `~/.workbuddy/mcp.json`（stdio, uvx） | 关 |

接入契约、双阶段意图（`draft`→`confirm`）、人工在环、降级协议详见 **`TRADER_MCP.md`**。所有 MCP 取数须遵守溯源四要素与 `DATA_GUARDRAILS.md`，并遵守 `noInvestmentAdviceGuarantee` / `dataGuardrailsEnabled`。

## 跨平台说明

- 运行脚本时命令为 `python3`；**Windows 上解释器名通常为 `python`**（官方安装器 / Microsoft Store），少数环境才有 `python3`。
- 脚本均为纯 Python 标准库 + AkShare（可选），目标机需安装 **Python 3.7+**（推荐 3.10+）；未安装 AkShare 时脚本返回结构化失败状态而非编造数据。

## 目录结构

```
touyan-expert-team/
├── .codebuddy-plugin/plugin.json   # 团队注册元数据（WorkBuddy 消费方）
├── settings.json                   # Team 型运行时入口（{"agent": "touyan-expert-team-lead"}）
├── routing.yaml                    # 意图路由表（外部化单一真源，lead 编排时加载）
├── config/feature_flags.yaml       # 功能开关（灰度发布与回滚）
├── COPYRIGHT.md / LICENSE          # 版权与许可（MIT）
├── README.md                       # 本文件
├── CHANGELOG.md                    # 变更记录（智能体功能）
├── DATA_GUARDRAILS.md             # 数据守门单一真源（七项校验/status/降级协议）
├── OUTPUT_CONTRACT.md              # 输出契约 + 0–100 质量评分 rubric + 溯源四要素
├── COVERAGE.md                    # 各技能市场覆盖范围与降级路径矩阵
├── TRADER_MCP.md                  # 交易/行情/妙想 MCP 接入契约与护栏
├── agents/                         # 4 个 Agent 定义（主理人 + 3 名成员）
│   ├── touyan-expert-team-lead.md
│   ├── hotspot.md
│   ├── stock.md
│   └── kline.md
└── skills/                         # 18 个技能
```
