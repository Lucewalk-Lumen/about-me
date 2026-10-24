---
name: us-market-data
description: 获取美股实时报价与历史 K 线数据（东方财富公开接口，零 API Key），并为美股研究生成可审计的量价事实。用于用户请求美股行情、K 线、技术复盘、实时价格，或提供美股代码/名称（如 AAPL、苹果、特斯拉、英伟达）时。A 股/ETF 请改用 kline-market-data。
description_zh: 获取美股实时报价与历史 K 线数据（东方财富公开接口，零 API Key），并为美股研究生成可审计的量价事实。用于用户请求美股行情、K 线、技术复盘、实时价格，或提供美股代码/名称（如 AAPL、苹果、特斯拉、英伟达）时。A 股/ETF 请改用 kline-market-data。
description_en: Fetch US stock realtime quotes and historical K-line data (Eastmoney public API, zero API key) and generate auditable price-volume facts for US market research. Used for US quote, K-line, technical review or realtime price requests, or when US tickers/names (AAPL, Apple, Tesla, Nvidia) are provided. For A-shares/ETFs use kline-market-data.
version: 1.0.0
author: Xing Bu
---

# US Market Data

## 目标

把美股行情获取做成确定性步骤，让模型只负责解释已知事实。覆盖**实时报价**与**历史 K 线**两个取数脚本；不处理交易账户、持仓、委托、盘口逐笔或需要登录的数据（美股实盘执行本团不支持，EMTL 仅 A 股）。

## 输入判断

1. 用户提供美股代码/名称 + 「实时价/现价/多少钱」→ 走 `fetch_us_quote.py`（报价守门）。
2. 用户提供美股代码 + 「K线/走势/复盘/回测数据」→ 走 `fetch_us_kline.py`（历史 K 线）。
3. 用户粘贴 CSV 或明确说「不要联网」→ 走 CSV fallback（字段口径同 A 股，见 `kline-market-data`）。
4. 信息不足时最多追问 3 个字段：标的、交易所（纳斯达克/纽交所/美交所）、周期/区间。默认纳斯达克、日线、最近 120 根、前复权。

## 实时报价硬规则（与 A 股守门同级）

涉及美股当前价、涨跌幅、成交量、成交额时，必须先调用：

```bash
python3 ./skills/us-market-data/scripts/fetch_us_quote.py AAPL --json 2>/dev/null || python3 ./skills/us-market-data/scripts/fetch_us_quote.py AAPL
```

> Windows 上将 `python3` 换成 `python`。脚本默认输出 JSON 摘要（无需 `--json` 参数，`--strict` 仅在调试时要求非零退出码）。

只有返回 `quality.ok=true` 才能引用确定价格。网页搜索、新闻摘要、示例值和其他技能输出**不得**替代该结果；核验失败时直接说明「暂无可验证实时行情」。报价结果必须连同 `quote_time_et`（美东时间）与 `session_status`（盘中/盘前/盘后/休市）一起呈现——**不得把美东时间当作北京时间误读**。

## 东方财富数据规范（美股）

- secid 前缀：`105.`=纳斯达克、`106.`=纽交所、`107.`=美交所；示例 `105.AAPL`、`106.BABA`、`107.APT`。
- 报价字段精度按 `f59` 小数位动态缩放（美股实测 `f43=345240, f59=3 → 345.24`）；**不得硬编码 ÷100**（那是 A 股口径）。
- K 线字段标准化为：`date, open, close, high, low, volume, amount, amplitude_pct, change_pct, change_amount, turnover_pct`，周期映射同 A 股（`101` 日线 / `102` 周线 / `103` 月线 / 分钟线）。
- K 线日期为**美股交易日期**（美东时间）；A 股与美股交易日历不同，跨市场对比必须分别取数，不得混排。
- 东方财富不可用时，脚本返回 `quality.ok=false` 的软失败 JSON；不得中断主流程，更不得编造价格。

## 溯源四要素（美股取数输出必须带）

| 要素 | 口径 |
|---|---|
| 来源 | `eastmoney-us-quote` / `eastmoney-us` + secid |
| 取数时间 | 报价给美东时间 + UTC 双标注；K 线给区间起止（美股交易日） |
| 校验状态 | `quality.ok`（true/false） |
| 置信度 | `traceability.confidence`（high/medium/low，按时效与盘中状态） |

## 降级协议

- 报价失败 → 说明「暂无可验证实时行情」+ 双选项（重试 / 用最近一根日 K 收盘价并标注为收盘价）。
- K 线失败 → 本地缓存（`--cache-dir`）→ 用户粘贴 CSV 离线解读。
- 富途/盈透等券商级数据、盘口逐笔、期权链：本 skill 不覆盖，如实说明。

## 红线

- 本 skill 只读，**绝不下单、绝不提供实盘执行**（美股无券商 MCP 接入）。
- 输出仅供参考，不构成投资建议；不得使用「必涨/必跌」等确定性表述。
- 不得把东财接口的延时/收盘价表述为「实时价」——以 `session_status` 与 `data_age_hours` 为准。
