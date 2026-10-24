---
name: china-stock-analysis
description: A 股、港股、中概股深度分析技能，支持多维度财务指标解读、行业对比和估值判断。提供客观、数据驱动的研究视角，不包含投资诱导。
description_zh: A 股、港股、中概股深度分析技能，支持多维度财务指标解读、行业对比和估值判断。提供客观、数据驱动的研究视角，不包含投资诱导。
description_en: "Deep analysis skill for A-shares, HK stocks and China ADRs: multi-dimensional financial metric interpretation, industry comparison and valuation judgement. Objective, data-driven research perspective with no investment inducement."
version: 1.0.0
author: Community
---

# 中国股票分析

> 跨平台：文中命令统一 `python3`，Windows 上解释器名通常为 `python`。

对 A 股、港股、中概股进行结构化分析，输出客观、数据驱动的研究结果。

## 支持市场

| 市场 | 代码格式 | 示例 |
|------|---------|------|
| A股（上海） | XXXXXX.SH | 600519.SH（贵州茅台） |
| A股（深圳） | XXXXXX.SZ | 000001.SZ（平安银行） |
| 香港 | XXXX.HK | 0700.HK（腾讯） |
| 美国 | TICKER | AAPL, TSLA, NVDA |

## 分析工作流

分析一只股票时按以下步骤：

1. **通过本地行情守门脚本获取 A 股当前价**
   - 在 Agent 工作目录执行：`python3 ./skills/astock-report/scripts/market_data_guard.py quote <股票名或代码> --json`
   - 仅当 `status=ok` 时使用返回的价格和涨跌幅
   - 状态非 `ok` 时，说明没有可验证实时行情；不得用网页搜索摘要、新闻文章、历史收盘价或记忆值替代
   - 港股/美股行情使用有明确时间戳的结构化数据源；网页搜索仅用于新闻和背景信息，不作为实时行情 API

2. **收集补充背景信息**（如可用）
   - 影响该股票的最新新闻
   - 行业趋势
   - 市场情绪

3. **以结构化格式呈现分析**：

```
## 📊 {股票名称}({代码}) 分析

### 📈 核心数据
| 指标 | 数值 | 变化 |
|------|------|------|
| 当前价/最近可得收盘价 | XXX | +XX |
| 涨跌幅 | XX% | 🔴/🟢 |
| 最高/最低 | XX / XX | - |
| 成交量 | XX万手 | - |

### 基本面分析
- 估值水平：...
- 财务健康度：...
- 行业位置：...

### 技术面分析
- 短期趋势：...
- 关键支撑/压力位：...
- 均线状态：...

### ⚠️ 风险提示
- 行业风险：...
- 公司层面风险：...
- 市场风险：...

### 📝 小结
- 核心事实：...
- 需要关注的事项：...
```

## 分析原则

- 所有数据必须标注来源和取数时间
- 数据缺失时标注「暂未获取」或「待核实」，不编造数字
- 不提供买入/持有/卖出的确定性建议
- 不诱导用户进行特定交易操作
- 分析仅供参考，不构成投资建议

## 风险提示

始终在输出末尾附加："分析仅供参考，不构成投资建议。投资有风险，入市需谨慎。"

## 常用股票代码参考

见 [references/china-stocks.md](references/china-stocks.md)。
