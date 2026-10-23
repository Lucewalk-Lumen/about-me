---
name: akshare-stock
description: >
  A股量化 AkShare 数据技能。用于通过 AkShare 获取 A 股实时行情、历史 K 线、
  龙虎榜、板块、资金流、融资融券与财务数据。输出确定数字前必须检查代码、
  日期、字段和单位；无法核验时返回“暂无可验证数据”。
description_zh: A股量化 AkShare 数据技能。用于通过 AkShare 获取 A 股实时行情、历史 K 线、龙虎榜、板块、资金流、融资融券与财务数据。输出确定数字前必须检查代码、日期、字段和单位；无法核验时返回“暂无可验证数据”。
description_en: "A-share quantitative data skill powered by AkShare: realtime quotes, historical K-line, dragon-tiger list, sectors, capital flows, margin trading and financials. Validate code, date, fields and units before stating any definite number; return 'no verifiable data' when validation fails."
version: 1.0.0
author: Community / AkShare
source: https://clawhub.ai/skills/akshare-stock
---

# akshare-stock

> 跨平台：文中命令统一 `python3`，Windows 上解释器名通常为 `python`。
本技能把 AkShare 作为 A 股数据主入口。Agent 需要输出行情、龙虎榜、资金流、
财务、板块或融资融券数据时，优先使用本技能和
`./skills/astock-report/scripts/market_data_guard.py`。

## 强制规则

1. 价格、涨跌幅、成交额、资金流、龙虎榜净买入、财务指标等数字不得由模型推断。
2. 输出前必须检查股票代码、数据日期、字段名和单位。
3. 实时行情必须使用 AkShare 主源，并至少通过一个核验源；核验失败则不输出确定价格。
4. 龙虎榜必须使用 `stock_lhb_detail_em(start_date=YYYYMMDD, end_date=YYYYMMDD)`，并校验交易日期。
5. 全市场区间涨幅必须逐只股票计算；`top-gainers` 返回 `partial` 时不得写成全市场 Top N。
6. 分红必须按 `报告时间/报告年度` 过滤，不能按实施年份过滤。
7. 财务字段缺失时保持缺失，不能按 0 填充。
8. 年报核心字段核验必须走 `annual-fields`，不要用普通利润表字段猜营业收入、归母净利润、扣非归母净利润。
9. 日期不一致、字段缺失、单位不明、接口为空或多源冲突时，只输出“暂无可验证数据”。
10. 输出必须标注 AkShare 函数名、取数时间、数据日期和核验状态。

## 常用函数

| 场景 | AkShare 函数 | 关键校验 |
| --- | --- | --- |
| 实时行情 | `stock_zh_a_spot_em` | 代码、名称、最新价、多源价格差 |
| 历史 K 线 | `stock_zh_a_hist` | 代码、起止日期、复权方式 |
| 历史 K 线备用 | `stock_zh_a_hist_tx` | 代码需带市场前缀、起止日期、复权方式 |
| 龙虎榜 | `stock_lhb_detail_em` | `date` 参数、返回交易日期、净买入单位 |
| 板块行情 | `stock_board_industry_name_em` / `stock_board_concept_name_em` | 板块名称、更新时间、成分股 |
| 资金流 | `stock_individual_fund_flow` | 日期、主力/大单口径、单位 |
| 分红 | `stock_dividend_cninfo` | `报告时间`、每 10 股/每股换算、实施日期 |
| 财务指标 | `stock_financial_analysis_indicator` / `stock_financial_report_sina` | 报告期、字段缺失、单位 |
| 年报核心字段 | `stock_profit_sheet_by_report_em` + 内置高风险样本规则 | 报告期、营业收入、归母净利润、扣非归母净利润、口径冲突 |
| 财务摘要 | `stock_financial_abstract` 等 | 报告期、同比/环比口径 |
| 融资融券 | `stock_rzrq_*` / `stock_margin_*` | 交易日期、市场范围、单位 |

## 守门命令

```bash
python3 ./skills/astock-report/scripts/market_data_guard.py quote 600519.SH --json
python3 ./skills/astock-report/scripts/market_data_guard.py billboard --date 2026-06-12 --json
python3 ./skills/astock-report/scripts/market_data_guard.py top-gainers --start 2024-04-01 --end 2024-04-22 --limit 10 --json
python3 ./skills/astock-report/scripts/market_data_guard.py dividend 600519.SH --report-year 2024 --json
python3 ./skills/astock-report/scripts/market_data_guard.py finance-quality 600519.SH --report-year 2024 --json
python3 ./skills/astock-report/scripts/market_data_guard.py annual-fields 601318.SH --report-year 2022 --json
python3 ./skills/astock-report/scripts/market_data_guard.py index-boundary 中证1000 --json
python3 ./skills/astock-report/scripts/market_data_guard.py entity-risk 康美药业 --json
```

## 失败关闭

当 AkShare 或核验源不可用时，任务流程继续运行，但不得编造数据。统一返回：

```text
暂无可验证数据：AkShare/核验源未返回可校验结果。
```
