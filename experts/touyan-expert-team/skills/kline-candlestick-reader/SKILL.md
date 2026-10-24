---
name: kline-market-data
description: 获取和标准化 A 股/ETF K 线数据，并为 K 线解读助手生成可审计的量价事实。用于用户请求东方财富 K 线数据、A 股或 ETF 技术复盘、多周期 K 线分析、双标的技术结构对比，或用户粘贴 CSV K 线数据并要求离线解读时。
description_zh: 获取和标准化 A 股/ETF K 线数据，并为 K 线解读助手生成可审计的量价事实。用于用户请求东方财富 K 线数据、A 股或 ETF 技术复盘、多周期 K 线分析、双标的技术结构对比，或用户粘贴 CSV K 线数据并要求离线解读时。
description_en: Fetch and standardize A-share/ETF K-line data and generate auditable price-volume facts for the K-line reading assistant. Used for Eastmoney K-line requests, A-share/ETF technical review, multi-timeframe analysis, dual-symbol structure comparison, or offline interpretation of pasted CSV K-line data.
version: 1.0.0
author: Community
---

# Kline Market Data

## 目标

把行情获取和指标计算做成确定性步骤，让模型只负责解释已知事实。优先支持 A 股与 ETF，不处理交易账户、持仓、委托、盘口逐笔或需要登录的数据。

## 输入判断

1. 用户粘贴 CSV 或明确说“不要联网”“只用这些数据”时，走 CSV fallback。
2. 用户提供股票/ETF 代码、名称、周期或区间时，走东方财富公开 K 线数据。
3. 信息不足时，最多追问 3 个字段：标的、周期、区间/根数。默认值为日线、最近 120 根、前复权。

## 东方财富数据规范

- 使用公开 K 线数据，字段标准化为：`date, open, close, high, low, volume, amount, amplitude_pct, change_pct, change_amount, turnover_pct`。
- 常用周期映射：`1` 分钟、`5` 五分钟、`15` 十五分钟、`30` 三十分钟、`60` 六十分钟、`101` 日线、`102` 周线、`103` 月线。
- 常用复权映射：`0` 不复权、`1` 前复权、`2` 后复权。
- 默认使用前复权，除非用户明确要求不复权或后复权。
- 对东方财富访问做轻量限流；不要并发请求大量标的。对比两个标的时串行获取。
- 东方财富不可用时，脚本默认返回 `quality.ok=false` 的 JSON 软失败摘要，不让主流程直接中断；本地调试需要非零退出码时使用 `--strict`。
- 代码自动识别沪深市场：`5/6/9` 前缀按沪市 `1.xxxxxx`，`0/1/2/3` 前缀按深市 `0.xxxxxx`；无法识别时可用 `--secid` 显式指定。

## CSV fallback

接受中文或英文表头。常见字段映射：

- 日期/date/time -> `date`
- 开盘/open -> `open`
- 收盘/close -> `close`
- 最高/high -> `high`
- 最低/low -> `low`
- 成交量/volume -> `volume`
- 成交额/amount -> `amount`
- 振幅/amplitude_pct -> `amplitude_pct`
- 涨跌幅/change_pct -> `change_pct`
- 换手率/turnover_pct -> `turnover_pct`

如果字段缺失，保留可计算部分并在数据质量中说明。少于 20 根 K 线时，必须提示 MA20、区间形态和趋势判断置信度有限。

## 指标与事实摘要

生成解释前先整理：

- 样本数量、起止日期、最后一根 K 线。
- MA5、MA10、MA20、MA60；样本不足则标为不可计算。
- 最新收盘价相对 MA5/10/20/60 的位置。
- 最近 20/60 根最高价、最低价和对应日期。
- 最近 5 根均量、20 根均量和最新量能相对倍数。
- 最新 K 线实体、上下影线、振幅和涨跌幅。
- 是否出现放量突破、缩量回踩、长上影、长下影、跳空、均线多头/空头排列等可验证现象。

## 输出给主 Agent 的结构

```json
{
  "source": "eastmoney | csv",
  "symbol": "string",
  "name": "string",
  "period": "day | week | month | 5m | 15m | 30m | 60m",
  "adjust": "none | qfq | hfq | unknown",
  "range": { "start": "YYYY-MM-DD", "end": "YYYY-MM-DD", "bars": 120 },
  "quality": {
    "ok": true,
    "warnings": []
  },
  "last_bar": {},
  "moving_averages": {},
  "price_position": {},
  "volume_profile": {},
  "key_levels": {},
  "candlestick_notes": [],
  "raw_sample_tail": []
}
```

## 解释边界

- 不输出买入、卖出、加仓、减仓、仓位比例、目标价或收益承诺。
- 不把技术形态称为确定性预测。
- 不编造基本面、公告、资金流、北向资金、龙虎榜或盘口信息。
- 数据失败时返回失败摘要和 fallback 建议，不继续生成伪复盘。

## 可用脚本

- `scripts/fetch_eastmoney_kline.py`：获取东方财富 A 股/ETF K 线，标准化字段，并输出摘要 JSON 或 CSV。仅串行请求，适合单标的或双标的对比；失败时默认输出可解析的降级 JSON。
- `scripts/analyze_kline_csv.py`：解析 CSV 文本或 CSV 文件，输出指标摘要 JSON。适合用户粘贴数据或东方财富数据已被保存为 CSV 的场景。
- `scripts/render_kline_report.py`：把指标摘要 JSON 渲染成符合输出契约的 Markdown 复盘报告，适合 smoke、离线评测或需要稳定基线输出的场景。
- `references/sample-kline.csv`：离线 smoke fixture，用于评测 CSV fallback 与输出契约，不代表真实行情。

## 缓存兜底

实时数据失败时，优先使用同一 `secid + period + adjust + beg + end + limit` 的本地缓存。缓存命中必须在报告中展示 `source=eastmoney-cache` 和缓存年龄。缓存只是兜底，不代表最新行情；若用户需要当日盘后复盘，应提醒恢复实时数据或粘贴最新 CSV。
