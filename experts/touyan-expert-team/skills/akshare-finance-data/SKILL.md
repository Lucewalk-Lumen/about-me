---
name: akshare-finance-data
description: Retrieve structured A-share market data with AKShare, including leaderboard data, limit-up review data, and capital-flow data. Use this skill when workflows need factual market inputs, explicit fallback status, and no fabricated values. It works especially well in scheduled-task setups such as arkclaw templates.
description_zh: 用 AkShare 获取 A 股结构化行情数据（龙虎榜、涨停复盘、资金流等）。适用于需要事实性市场输入、明确降级状态、不编造数值的工作流，尤其适合定时任务场景。
description_en: Retrieve structured A-share market data with AKShare, including leaderboard data, limit-up review data, and capital-flow data. Use this skill when workflows need factual market inputs, explicit fallback status, and no fabricated values. It works especially well in scheduled-task setups such as arkclaw templates.
author: Community
version: 0.1.0
---

# byted-util-akshare-finance-data

A-share market data skill built on AKShare.

> 跨平台：文中命令统一 `python3`，Windows 上解释器名通常为 `python`。

It supports three primary data families:

- leaderboard data, including detail, institution activity, and trader statistics
- limit-up and sentiment data, including limit-up, limit-down, broken-board, momentum, and previous limit-up follow-through
- capital-flow data, including northbound flow, sector flow, stock flow, and margin trading data

Use this skill when an agent needs factual, structured A-share market data for scheduled workflows, especially for leaderboard review, limit-up review, and capital-flow reporting.

支持 A 股结构化市场数据，包括龙虎榜数据、涨停复盘数据和资金流向数据。

This skill is designed as a structured data provider. It can be used in many workflows, and works especially well in scheduled-task setups for recurring report generation, post-close review, card delivery, and structured archival.

这是一个结构化数据获取 Skill；接入 arkclaw 等定时任务模版会更顺手。

## When To Use

Use this skill when the task requires:

- leaderboard data for a trading date（指定交易日龙虎榜数据）
- limit-up, limit-down, broken-board, or momentum pool data（涨停、跌停、炸板或强势股池数据）
- northbound flow, sector flow, stock flow, or margin data（北向资金、行业资金流、个股资金流或融资融券数据）
- structured report inputs for scheduled workflows（定时任务需要的结构化报告输入）
- explicit section-level status for downstream analysis（用于下游分析的 section 级状态）

## When Not To Use

Do not use this skill when the task requires:

- free-form commentary without data retrieval（不取数直接输出分析）
- fabricated conclusions when data is missing（数据缺失时编造结论）
- strict historical replay of real-time interfaces inside `report-capital`（对 `report-capital` 中实时类接口做严格历史回放）
- announcement or news analysis not covered by current commands（当前命令未覆盖的公告或新闻分析）

## Installation

Install dependencies before running commands:

```bash
pip install -r requirements.txt
```

## Usage

```bash
python3 scripts/main.py <command> [options]
```

## Command Groups

### Leaderboard Data

```bash
python3 scripts/main.py lhb --date 20260516
python3 scripts/main.py lhb-inst --date 20260516
python3 scripts/main.py lhb-trader --date 20260516 --days 5
```

用于龙虎榜明细、机构席位和营业部统计。

### Limit-Up And Sentiment Data

```bash
python3 scripts/main.py zt-pool --date 20260516
python3 scripts/main.py dt-pool --date 20260516
python3 scripts/main.py zb-pool --date 20260516
python3 scripts/main.py strong-pool --date 20260516
python3 scripts/main.py zt-previous --date 20260516
python3 scripts/main.py zt-summary --date 20260516
```

用于涨停复盘和情绪数据。

### Capital-Flow Data

```bash
python3 scripts/main.py north-flow --days 10
python3 scripts/main.py north-stock --symbol 600519
python3 scripts/main.py sector-flow --sector_type industry --top 20
python3 scripts/main.py stock-flow --symbol 600519 --market sh
python3 scripts/main.py margin --days 5
```

用于北向资金、行业资金流、个股资金流和融资融券数据。

### Report Commands

```bash
python3 scripts/main.py report-lhb --date 20260516
python3 scripts/main.py report-zt --date 20260516
python3 scripts/main.py report-capital
```

用于获取报告类输入；接入 arkclaw 模版时会更方便。

## How To Use This Skill

1. Select the command group that matches the task.
2. Run a command to fetch structured JSON.
3. If the command is a report or summary command, inspect section-level status before further analysis.
4. Only generate downstream interpretation from available facts.
5. If a section is empty or failed, report that explicitly instead of filling gaps.

可按以下方式使用：

1. 先选对应的命令组，再执行命令取数。
2. 如果使用 `report-*` 或 `zt-summary`，先检查 `overall_status` 和 `section_status`。
3. 只有 `ok` 或边界明确的 `partial` section 才进入后续分析。
4. 如果状态是 `empty` 或 `failed`，直接输出“暂无数据”或“取数失败”。

## Output

All commands return structured JSON with:

- `success`
- `data`
- `source`
- `update_time`
- `disclaimer`

### Report And Summary Structure

`report-lhb`, `report-zt`, `report-capital`, and `zt-summary` also return:

- `task_type`
- `trade_date`
- `overall_status`
- `section_status`
- `failed_sections`
- `empty_sections`
- `facts`
- `analysis_constraints`
- `sections`

### Section Status Rules

- `ok`: data is available and can be used
- `empty`: the fetch succeeded but returned no data
- `partial`: only part of the required data is available
- `failed`: the fetch failed and must not be treated as factual absence

状态含义如下：

- `ok`：数据可用
- `empty`：接口调用成功，但当前没有返回数据
- `partial`：部分数据可用
- `failed`：接口获取失败，不能视为无数据

## Rules

- Never fabricate stock names, trader names, prices, or amounts.
- Never treat historical data as same-day data.
- If a section is `empty` or `failed`, say so explicitly.
- Only use `ok`, or carefully bounded `partial`, sections in downstream analysis.
- `report-capital` accepts an optional `--date` for historical replay; only history-based sections are replayed, while real-time sections (`north_today`, `sector_flow`) return `empty` for non-latest dates.

## Best Practices

- Prefer `report-*` and `zt-summary` for scheduled workflows.
- Treat `facts` as the objective layer.
- Keep narrative generation separate from raw facts.
- Do not infer unavailable values from adjacent sections.
- Surface fallback status directly to users or downstream systems.

## Notes

- Data is sourced from AKShare / Eastmoney.
- Market data may be delayed.
- Non-trading days fall back to the latest trading date for supported commands.
- This skill fits well into scheduled-task systems such as arkclaw templates.
- Investment risk disclaimer: data is for reference only and does not constitute investment advice; investment decisions are at the user's own discretion.

请注意：

- 数据源为 AKShare / 东方财富，可能延迟
- 非交易日会回退到最近交易日，仅适用于已支持的命令
- 适合作为数据获取层使用
- 接入 arkclaw 等定时任务系统时使用更顺手
- 投资风险提示：数据仅供参考，投资决策请自行判断，不构成投资建议
