# 覆盖范围矩阵（包级单一真源）

> 明确每个技能覆盖的市场范围、数据依赖与降级路径，避免用户把「仅 A 股」技能误用于港美股。
> 制定依据：阶段 1 调研发现 G6（覆盖范围不透明，A/港/美股易混用）。
> 数据守门与降级纪律见 `DATA_GUARDRAILS.md`。

## 技能覆盖范围

| 技能 | 覆盖市场 | 数据依赖 | 降级路径（依赖缺失时） |
|------|----------|----------|------------------------|
| `hotspot-discovery` | A 股（政策/资金/事件三重信号） | 联网搜索 + `akshare-finance-data` | 联网搜索降级，标注来源为「摘要/待核实」 |
| `company-deep-analysis` | A 股为主（5 年长周期财报） | AkShare / 公开财报 | 公开接口缺失 → 标注「部分维度暂缺」 |
| `industry-theme-research` | A 股行业/主题 | `akshare-finance-data` + 联网 | 同 hotspot |
| `compare-decide` | A 股同行业/同概念 | 多技能取数 | 按可用数据分维度对比，缺项标「暂缺」 |
| `portfolio-strategy` | A 股组合（风险画像→配置→标的→节奏→红线） | 用户风险偏好 + 市场数据 | 不取实时价，仅给框架与风控红线 |
| `claw-stock` | **A / 港股 / 美股**（林奇分类 + 6 因素评分） | 行情接口 + 守门脚本 | 实时价走 `market_data_guard.py`，缺失标「待核实」 |
| `eastmoney-mx-skills-suite` | A / 港 / 美 / 基金 / 债券（东方财富妙想） | 环境变量 `MX_APIKEY` | 未配置 → 主动说明 + 双选项降级（见 DATA_GUARDRAILS §4） |
| `xiaodi-financial-analysis-team` | 多视角分析（投顾/行业/投行/市值/财富/交易/舆情） | 多源 | 单角色不可用时跳过该视角并说明 |
| `akshare-finance-data` | **A 股**（龙虎榜/涨停/北向/行业资金/两融） | `pip install akshare` | 未安装 → 结构化失败状态，不编造 |
| `mx-stocks-screener` | **A / 港 / 美 / 基金 / 债券**（自然语言筛选） | `MX_APIKEY` | 同 eastmoney-mx-skills-suite |
| `astock-report` | **A 股 / A 股 ETF** | `market_data_guard.py`（AkShare 主源） | 守门脚本返回非 ok → 标「暂无可验证数据」 |
| `china-stock-analysis` | A 股 / 港股 / 中概股 | 多源 | 缺项标「暂缺」 |
| `claw-stock-watcher-pro` | A 股自选股管理 + 行情摘要 | 守门脚本 + 本地存储 | 存储/推送缺失 → 降级，不影响分析 |
| `akshare-stock` | **A 股**（行情/资金流/龙虎榜/板块/两融/分红/财务） | AkShare | 未安装 → 结构化失败 |
| `stock-monitor-skill` | A 股 7×24 持仓监控 | 守门脚本 + 调度 | 依赖缺失 → 定时任务不触发，不伪造预警 |
| `kline-market-data` | **A 股 / ETF** + 用户粘贴 CSV 离线 | 东方财富公开接口 / 本地 CSV | 接口失败 → 缓存 → CSV 离线兜底 |
| `us-market-data` | **美股**（纳斯达克/纽交所/美交所，secid 105/106/107） | 东方财富公开接口（零 Key） | 报价失败 → 标「暂无可验证实时行情」；K 线失败 → 缓存 → CSV 离线兜底 |
| `strategy-backtest` | A 股 / 美股 / ETF（吃 K 线 CSV，不限定市场） | 上游 K 线取数脚本或用户粘贴 CSV | 取数失败 → 提示粘贴 CSV（`date,close` 两列即可） |

## 使用须知

- **港美股用户**：优先用 `claw-stock` / `mx-stocks-screener` / `eastmoney-mx-skills-suite`；`astock-report`、`akshare-*`、`kline-market-data` 仅覆盖 A 股。
- **美股取数路由**：实时报价与 K 线一律走 `us-market-data`（status=ok 守门 + 美东时间标注，见 `DATA_GUARDRAILS.md` §7）；`claw-stock` 的美股分析必须经 `us-market-data` 取数，不得用网页搜索价格冒充实时价。
- **凭证依赖**：`MX_APIKEY` 缺失时相关技能一律走 §4 降级协议，不会静默回退或伪造。
- **跨市场对比**：如对比 A 股与港股/美股，须分别调用对应市场技能，不得用 A 股技能套港股/美股代码；A 股与美股交易日历不同，时间轴不得混排。
- **实盘执行边界**：EMTL 实盘仅 A 股；美股无执行能力，相关请求须明确拒绝。
