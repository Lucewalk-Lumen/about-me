# TRADER_MCP.md — 交易 / 行情 MCP 接入契约与护栏（包级单一真源）

> 本文档定义投研星图团如何接入「东方财富 EMTL（交易/操盘手）」「东方财富妙想 MCP（数据+模拟交易）」「腾讯自选股 westock-mcp（连接器/行情）」「通达信 tdx-mcp（行情/K线）」四类 MCP。
> 它是继 `DATA_GUARDRAILS.md` / `OUTPUT_CONTRACT.md` / `COVERAGE.md` 之后的第四份包级治理文档，所有 agent 与取数型 skill 均须遵守。
> **铁律：默认全部关闭；任何执行（下单）动作须经双阶段意图 + 人工在环，绝不自主实盘。**

---

## 0. 角色界定（必须分清"数据"与"执行"）

| MCP | 类别 | 是否"操盘手/执行" | 典型工具 | 接入方式 |
|---|---|---|---|---|
| **东方财富 EMTL** | 交易/账户 | ✅ 是（唯一执行类） | `create_order` / `cancel_order` / `query_asset_and_position` / `query_orders` / `query_trades` / `query_history_orders` / `query_history_trades` / `query_funds_flow` / `query_abbrs` | `~/.workbuddy/mcp.json`（stdio, `uvx`） |
| **腾讯自选股 westock-mcp** | 行情/连接器 | ❌ 否（纯数据） | `data_*` 行情/财务/K线/资金/板块/宏观/自选管理 | 包声明 `dependencies.connectors:["westock-mcp"]`，经连接器面板连接 |
| **通达信 tdx-mcp** | 行情/K线 | ❌ 否（纯数据） | `tdx_get_quote` / `tdx_get_kline` / `tdx_get_f10` / `tdx_get_block_info` … | `~/.workbuddy/mcp.json`（stdio, `uvx`，无需 Key） |
| **东方财富妙想 MCP** | 数据 + 模拟交易 | ❌ 否（模拟盘，非实盘） | `mx_search` / `mx_data` / `mx_select_stock` / `mx_selfselect_*` / `mx_stock_simulator_*`（模拟） | `~/.workbuddy/mcp.json`（stdio, `python -m`），env `MX_API_KEY` |

> 结论：本团**唯一的实盘"操盘手"能力来自东方财富 EMTL**；东方财富妙想提供**模拟交易**（模拟盘，无真实资金，fail-closed）；westock / tdx 仅增强研究侧取数（用户可接自己账号查看自选股），不产生任何实盘执行动作。

---

## 1. 协议规范（Protocol）

- **传输**：MCP = Model Context Protocol，即 **JSON-RPC 2.0**，承载于 **stdio**（本地子进程）或 **HTTP/SSE**（远程）。
- **纳管**：WorkBuddy 在 `~/.workbuddy/mcp.json`（用户级）或 `<project>/.workbuddy/mcp.json`（项目级）中按 `mcpServers` 注册 server 并拉起/连接，暴露其 `tools`；agent 经 **tool-call** 使用，**不**把协议细节写进提示词。
- **连接器（Connector）特例**：westock-mcp 属 WorkBuddy 连接器体系，由包在 manifest 声明 `dependencies.connectors`，用户在侧边栏【连接器】面板搜索 `westock-mcp` 完成授权连接；连接状态下 skill 调用其 `data_*` Tool，未连接则按 `DATA_GUARDRAILS.md` 降级。

### 1.1 EMTL 标准接入配置（`~/.workbuddy/mcp.json` 片段）

```json
{
  "mcpServers": {
    "emtl": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/zsmatrix62/emtl-mcp.git", "emtl-mcp"],
      "env": {
        "EMTL_USERNAME": "你的东方财富账号",
        "EMTL_PASSWORD": "你的密码",
        "EMTL_STORAGE_DIR": "./emtl-cache"
      }
    }
  }
}
```

> 凭据仅存于 `env`，**绝不进入 LLM 提示词**（防泄露 / 防提示注入越权）。首次调用自动登录，会话缓存于 `EMTL_STORAGE_DIR`。

### 1.2 通达信 tdx-mcp 标准接入配置

```json
{
  "mcpServers": {
    "tdx": {
      "command": "uvx",
      "args": ["--from", "tdx-mcp", "tdx-mcp"]
    }
  }
}
```

> 直连通达信公开行情服务器（TCP 7709/7727），**无需 API Key**；为数据类 MCP，仅取行情/K线/F10，无执行能力。

### 1.3 腾讯自选股 westock-mcp 连接器声明（包 manifest）

```json
{
  "dependencies": {
    "connectors": ["westock-mcp"]
  }
}
```

> 连接状态下取数必须且只能调用 `data_*` Tool；未连接时降级到 AkShare / 公开接口 / 联网搜索（详见 `westock-data` 技能约束）。

### 1.4 东方财富妙想 MCP（数据 + 模拟交易）标准接入配置

```json
{
  "mcpServers": {
    "eastmoney-mx": {
      "command": "python",
      "args": ["-m", "eastmoney_mx_finance_mcp_server"],
      "env": {
        "MX_API_KEY": "你的东方财富妙想 API Key"
      }
    }
  }
}
```

> 基于妙想（MX）API 的金融 MCP 服务端（`eastmoney-mx-finance-mcp-server`），提供资讯搜索、金融数据查询、智能选股、自选股管理与**模拟交易**（模拟盘，无真实资金）。`MX_API_KEY` 变量名以官方 server 文档为准（包内既有 `eastmoney-mx-skills-suite` 使用 `MX_APIKEY`，接入时请对齐）。

---

## 2. 权限要求（Permissions / Credentials）

1. **凭据隔离**：API Key / 账号 / 密码写入 `env`（EMTL）或连接器授权（westock），**严禁写入提示词或日志明文**。
2. **交易专属权限最小化**：EMTL 仅授予"查询 + 拟单"能力；实盘下发默认**关闭**，由 feature_flag 控制。
3. **授权模型（仅 EMTL 适用）**：
   - **fail-closed 默认**：启动即 `observe-only`（仅查询），**不自动实盘**。
   - **双阶段交易意图**：`draft`（生成拟单/预览）→ `confirm`（用户显式确认后下发），**禁止单一动作直接实盘**。
   - **人工在环（human-in-loop）**：任何 `create_order` / `cancel_order` 必须由用户显式确认；agent 仅可"建议/拟单"，不可"自裁决执行"。
4. **妙想模拟交易边界**：东方财富妙想 `mx_stock_simulator_*` 为**模拟盘**（无真实资金），可在 `mx_mcp_enabled:true` 下使用，但仍须遵守溯源四要素与 `DATA_GUARDRAILS.md`，不构成实盘执行。
5. **降级一致**：MCP 不可达 / 登录失败 / 超时，按 `DATA_GUARDRAILS.md` 降级协议主动说明 + 双选项，**不得静默伪造**。

---

## 3. 接入护栏（Guardrails，硬约束）

| 护栏 | 规则 |
|---|---|
| 默认关闭 | `config/feature_flags.yaml` 中 `trader_mcp.enabled: false`、`emtl_enabled: false`、`mx_mcp_enabled: false`、`westock_connector_enabled: false`、`tdx_enabled: false`；未显式开启不得暴露任何交易/连接 tool |
| 执行禁区 | 仅 EMTL 含执行工具；调用 `create_order`/`cancel_order` 前必须 `draft`→`confirm` 双阶段且人工确认 |
| 非建议边界 | 遵守 `compliance.noInvestmentAdviceGuarantee`：输出仍只作研究参考，禁止"必涨/必跌/满仓买入"等确定性诱导 |
| 溯源四要素 | 所有经 MCP 取数须标注 来源 + 取数时间 + 校验状态(status) + 置信度（见 `OUTPUT_CONTRACT.md`） |
| 合规约束 | 必须保留 `dataGuardrailsEnabled` 与 `noInvestmentAdviceGuarantee`；过 `guardrail_gate.py` |
| 跨成员中继 | 与既有 `through-lead` 拓扑一致：worker 不直连 MCP 执行；所有 MCP 取数/拟单经主理人（lead）中转汇编 |

---

## 4. 工具清单（Tool Inventory）

### 4.1 东方财富 EMTL（执行类，默认关）
`query_asset_and_position` · `query_orders` · `query_trades` · `query_history_orders` · `query_history_trades` · `query_funds_flow` · `query_abbrs` · `create_order` · `cancel_order`

> 以上工具清单经官方 README 核验（https://github.com/zsmatrix62/emtl-mcp，2026-10-15 crawler 直取）：`query_abbrs` 用于查询 API 响应中缩写字段的中文名与英文描述（如 `Zqdm`=证券代码）；历史版本曾误列 `get_last_price`（官方无此工具），已于 v0.1.7 修正。

### 4.2 腾讯自选股 westock-mcp（数据/连接器）
`data_*` 系列：行情 / K线 / 财报 / 资金 / 技术指标 / 板块成份 / 宏观 / 新闻公告 / 自选管理（`portfolio_*`）。

### 4.3 通达信 tdx-mcp（数据）
`tdx_get_quote` · `tdx_get_kline` · `tdx_get_kline_all` · `tdx_get_minute` · `tdx_get_trades` · `tdx_get_auction` · `tdx_get_unusual` · `tdx_get_f10` · `tdx_get_block_info` · `tdx_get_finance` · `indicator_*`（MA/EMA/MACD/RSI/KDJ/BOLL/ATR）等。

### 4.4 东方财富妙想 MCP（数据 + 模拟交易）
`mx_search`（资讯搜索）· `mx_data`（金融数据）· `mx_select_stock`（智能选股）· `mx_selfselect_get` / `mx_selfselect_manage`（自选股管理）· `mx_stock_simulator_balance` / `mx_stock_simulator_positions` / `mx_stock_simulator_trade` / `mx_stock_simulator_cancel` / `mx_stock_simulator_orders` / `mx_stock_simulator_summary`（**模拟交易**，仅模拟盘）· `mx_amount_li_to_yuan` / `mx_price_restore`（辅助换算）。

> 妙想 MCP 的 `mx_stock_simulator_*` 为**模拟盘**下单/撤单/查询，不发生真实资金变动；本团不将其视为实盘执行，仍受 fail-closed 与溯源四要素约束。

---

## 5. Agent 接线规范（与三 agent 治理章节对应）

- **`touyan-expert-team-lead`（主理人）**：唯一可开启/编排 MCP 调用的角色；负责**双阶段意图**的 `draft` 生成与 `confirm` 汇总，跨成员信息经其**中转**（relay-through-lead）；EMTL 执行动作须由其提示用户确认。
- **`stock`（个股深研官）**：可经 EMTL **仅查询**账户/持仓/资金流水（默认关）；**不得**自行调用 `create_order`/`cancel_order`。
- **`kline`（K线技术复盘官）**：保持"拒绝交易指令输出"；westock / tdx / 妙想连接器连通时优先用其 `data_*` / `tdx_*` / `mx_*` 取行情与 K 线，遵守溯源四要素。

---

## 6. 降级协议（Degradation）

| 情形 | 处理 |
|---|---|
| EMTL 未配置 / `emtl_enabled:false` | 不暴露执行 tool；研究侧照常；主理人提示"交易 MCP 未启用" |
| EMTL 登录失败 / 超时 | 主动说明 + 双选项（重试 / 降级只读查询），**不伪造订单状态** |
| westock 连接器未连接 | 降级到 AkShare / 公开接口 / WebSearch，主理人单独提示"腾讯自选股连接器未连接" |
| tdx-mcp 未安装 | 行情/K线回退东方财富公开接口或 CSV 离线复盘 |
| 妙想 MCP 未配置 / `mx_mcp_enabled:false` | 不暴露 `mx_*` tool；数据取数回退既有 `eastmoney-mx-skills-suite`（需 `MX_APIKEY`）或公开接口 |

---

## 7. 启用前置检查（Checklist）

1. 用户已在 `~/.workbuddy/mcp.json` 按 §1.1 / §1.2 / §1.4 写入 server（EMTL / tdx / 妙想，凭据走 `env`）。
2. 若为 westock，已在连接器面板连接 `westock-mcp`。
3. `config/feature_flags.yaml` 对应开关置 `true`（生产默认 `false`）。
4. 已向用户明确：EMTL 执行动作需其逐笔人工确认；本团不提供 autonomous 实盘。

> 本文件为“如何安全接入 MCP”的可验证契约；任何 MCP 状态变更须在 `CHANGELOG.md` 显式记录。
