---
name: strategy-backtest
description: 对 K 线数据运行简单策略回测（纯标准库，零依赖）：双均线交叉、买入持有、定投分批；输出总收益/年化/夏普/最大回撤/胜率/交易明细与净值曲线尾部。用于用户要求回测策略、验证均线策略、对比参数组合，或评估某策略在 A 股/美股标的历史表现时。
description_zh: 对 K 线数据运行简单策略回测（纯标准库，零依赖）：双均线交叉、买入持有、定投分批；输出总收益/年化/夏普/最大回撤/胜率/交易明细与净值曲线尾部。用于用户要求回测策略、验证均线策略、对比参数组合，或评估某策略在 A 股/美股标的历史表现时。
description_en: "Run simple strategy backtests on K-line data (pure standard library, zero dependencies): dual moving-average crossover, buy-and-hold and DCA; outputs total return, annualized return, Sharpe, max drawdown, win rate, trade details and net-value curve tail. Used for backtest requests, MA strategy validation, parameter grid comparison, or evaluating a strategy's historical performance on A-share/US instruments."
version: 1.0.0
author: Xing Bu
---

# Strategy Backtest

## 目标

把「策略在历史数据上表现如何」做成确定性、可复算的步骤。输入为 K 线 CSV（来自 `us-market-data` / `kline-market-data` 的取数脚本，或用户粘贴），输出结构化指标与交易明细。**回测是研究工具，不是收益承诺。**

## 输入契约

- CSV 需含 `date` 与 `close` 两列（取数脚本标准输出的其他列可忽略）。
- 先取数再回测：美股经 `us-market-data/scripts/fetch_us_kline.py`，A 股/ETF 经 `kline-market-data` 对应脚本，均加 `--format csv`。
- 单次最多 5 个标的；每个标的默认取最近 500 根（`--bar-cap` 可调，上限 2000）。

## 策略与参数

| 策略 | 说明 | 参数 |
|---|---|---|
| `ma_cross` | 双均线交叉：快线上穿慢线买入，下穿卖出 | `--fast`（默认 5）、`--slow`（默认 20） |
| `buy_hold` | 首根收盘价买入、末根收盘价卖出（基准） | 无 |
| `dca` | 每 N 根定额买入，期末整体结算 | `--interval`（默认 20） |

参数网格：`--grid "fast=5,10,20;slow=20,60"`，自动跑遍 fast<slow 组合并按夏普比率降序输出前 10。

## 指标口径

- **总收益 / 年化收益**：按 1 单位资金的近似净值（均线策略满仓轮动；定推按定额分批）。
- **夏普**：日收益均值/标准差 × √252，无风险利率取 0。
- **最大回撤**：净值相对历史峰值的最大跌幅。
- **胜率**：已平仓交易中盈利交易占比。
- 期末仍持仓的均线交易按最后收盘价强平计入，并在交易明细标注「期末强平」。

## 输出结构（JSON）

```json
{
  "source": "strategy-backtest",
  "strategy": "ma_cross",
  "results": [
    {
      "symbol": "AAPL",
      "range": { "start": "2025-10-15", "end": "2026-10-15", "bars": 252 },
      "metrics": { "total_return_pct": 0, "annualized_return_pct": 0, "sharpe": 0, "max_drawdown_pct": 0, "trades": 0, "win_rate_pct": 0 },
      "trades": [],
      "equity_curve_tail": [],
      "quality": { "ok": true, "warnings": [] }
    }
  ],
  "disclaimer": "回测基于历史数据与简化假设，仅供研究参考，不代表未来收益，不构成投资建议。"
}
```

## 红线

- **不得**把回测结果表述为「预期收益」「稳赚」「策略保证」——输出必须带 disclaimer。
- 简化假设必须随结果披露：不含交易成本、滑点、涨跌停/做空限制、资金费率、分红再投资细节。
- 样本不足（K 线少于策略所需）时 `quality.ok=false` 并说明，**不得**用更短样本硬算后当作有效结论。
- 回测数据本身必须经取数脚本获得并满足溯源四要素；不得使用来源不明的 CSV。

## 降级

- 取数失败（东财不可达）→ 提示用户粘贴 CSV 走本地回测（`date,close` 两列即可）。
- 纯标准库实现，**无第三方依赖**；不引入 vectorbt/pandas（保打包零依赖纪律）。
