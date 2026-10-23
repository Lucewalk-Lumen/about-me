# 可视化规格与视觉红线（visualization-spec）

> **适用范围**：`delivery-automator` 产出的一切 HTML 视图。
> **统一约束**（写死，无例外）：
> - **仅 Python 标准库**；
> - **禁止任何第三方图表库**（ECharts / Chart.js / D3 / CDN 一律不用）；
> - 图表**手写 SVG + CSS**；
> - 产物为**单文件 HTML**（无外链、无 CDN、离线可开）。

---

## 1. 五类视图与产出

| 脚本 | 产出 | 内容规格 | 对应 AC |
|---|---|---|---|
| `scripts/render_desktop_calendar.py` | `out/desktop-calendar.html` | 月 / 周切换；**本周（第 7 周 = 2026-10-19~10-25）高亮**；节假日底色；调休上班日加边框标记；点选某日显示当日事件（名称 / 时间 / 地点 / 周次规则） | AC5 |
| `scripts/render_week_view.py` | `out/week-view.html` | 周时间轴（节次 × 星期）；稳定区 / 弹性区色块；相邻项之间画转场连线，临界转场用不同描边 | AC6 |
| `scripts/render_term_heatmap.py` | `out/term-heatmap.html` | 20 周 × 7 天热力格；空周 / 缓冲周 / 密集周（18–19 周）标注；色调按每日负载 | AC6 |
| `scripts/render_dashboard.py` | `out/dashboard.html` | 完成度仪表盘（手写 SVG 环形）：任务数完成率 / 工时完成率 / P0 完成率三环；下方五类归因条形 | AC6 |
| `scripts/render_achievements.py` | `out/achievements.html` | N5-b 降级形态：学期进度条 + 连击打卡日历 + 成就徽章（纯前端计算，无后端 / 账号 / 排行） | N5-b |

> 说明：设计稿 §2 文件清单写的是「4 类视图规格」，指**内容型视图**（周视图 / 热力图 / 仪表盘 / 成就页）；`render_desktop_calendar.py` 是 N2 的**容器型**桌面日历，二者不冲突。本文件按**实际落地的 5 个脚本**给规格。

---

## 2. 共同规格

| 项 | 规格 |
|---|---|
| **输入** | `<冻结台账 json>` + `<日程表 json>` + `<term-space.json>` + `<logbook.jsonl>` |
| **输出** | HTML 路径与字节数写入 stdout |
| **非空断言** | 产物字节数 > 0（断言失败即 FAIL） |
| **标记断言** | 产物含约定的 `data-v4-*` 标记，供 AC6 文件非空断言与阶段 4 抽查 |
| **离线性** | 单文件、无外链、无 CDN、无网络请求 |
| **打开纪律** | 产出后必须调 `present_files` **真打开一次**；仅生成文件不算 AC5 通过 |
| **周次反推** | 「第 N 周」一律以 `term-space.json` 的 `term_start=2026-09-07` 反推，**禁止硬编码周次** |

---

## 3. 各视图规格

### 3.1 桌面日历（`render_desktop_calendar.py`）

- 月视图 / 周视图切换。
- **本周高亮**：由 `term_start` 反推当前周（样例锚点：第 7 周 = 2026-10-19 ~ 10-25）。
- **节假日**：底色填充，鼠标悬停显示节日名与依据文号。
- **调休上班日**：边框标记 + 文字提示"要上班"，与节假日视觉上明确区分。
- 点选某日 → 面板显示当日全部事件：名称 / 时间 / 地点 / 周次规则 / 提醒。

### 3.2 周视图（`render_week_view.py`）

- 横轴星期、纵轴节次的时间轴网格。
- **分区色块**：稳定区与弹性区分色，图例说明。
- **转场连线**：相邻两项之间画线；**临界转场用不同描边**（如虚线 + 强调色），与"安全"转场区分。
- 悬停显示：地点、携带物品、降级预案。

### 3.3 学期负载热力图（`render_term_heatmap.py`）

- 网格：20 周 × 7 天。
- 色调：按每日负载强度分级（建议 5 档，仅用明度/饱和度变化，**不用彩虹色阶**）。
- 标注：**空周 / 缓冲周**（如第 1、17、20 周）、**密集周**（18–19 周）。
- 图例：负载档位 + 节假日/调休标记说明。

### 3.4 完成度仪表盘（`render_dashboard.py`）

- **三环仪表**：任务数完成率 / 工时完成率 / P0 完成率；手写 SVG 环形（`stroke-dasharray` 实现，**不用图表库**）。
- **五类归因条形**：计划过载 / 估算失真 / 外部打断 / 动力缺失 / 事实错误。
- 文本区：总体结论 + 最长连击 + 成就徽章摘要。

### 3.5 学期成就页（`render_achievements.py`）

- 学期进度条（已过周次 / 总周次）。
- 连击打卡日历（连续完成天数的可视化）。
- 成就徽章（纯前端计算）。
- **红线**：无后端、无账号、无排行榜、无多人。

---

## 4. P0 视觉红线（明文禁止，跨运行时一致）

### P0-1 · 禁用 emoji 作功能图标

| 禁止 | 替代 |
|---|---|
| 用 emoji 当图标（铃铛、日历、锁、勾、叉等） | 可矢量缩放的 **inline SVG**，或标准文字字形 |
| 依赖 emoji 字体渲染状态色 / 严重度 | CSS 色块 + 文字标签（如「稳定区 / 弹性区」「安全 / 临界 / 危险」） |

> **范围说明（与诊断一致）**：P0-1 针对**交付物**（HTML 产物）的功能图标与视觉资产。
> 成员 md 与 references 内部的状态 / 严重度文本符号，属**方法文献内部状态符号**，不在此列；但 v4 新写章节建议直接用文字，以降低跨终端渲染差异风险。

### P0-2 · 禁用「Indigo→Pink 渐变 + 发光边框 + 毛玻璃」AI 模板套路

| 禁用项 | 具体要求 |
|---|---|
| Indigo→Pink 渐变 | 禁止把该渐变用于按钮 / 卡片 / 背景 / 标题 |
| 发光边框（glow） | 禁止 `box-shadow` 发光描边作为主要强调手段 |
| 毛玻璃 | 禁止 `backdrop-filter: blur(...)` |

**替代配色方案**：**单色系 + 中性灰阶 + 1 个强调色**。

### 变量契约（机器可解析，`04-门禁/gate_color_sync.py` 逐字比对）

> **纪律**：下列色值**全部逐字取自** `scripts/` 下 6 个 HTML 产出脚本的 CSS 变量定义，**不是设计稿推断**。
> 改脚本颜色**必须同步改本块**；若只改脚本不改本块，门禁判红。

```text
[中性灰阶]
--bg:#f6f7f9
--panel:#ffffff
--line:#e3e6ea
--line2:#eef0f3
--ink:#1f2328
--muted:#5b6470
--faint:#8b949e

[强调色（全站仅 1 个色相）]
--accent:#2f6feb
--accent-soft:#e8f0fe
--accent-ink:#1b4bb8

[事实语义色（绑定 data/holidays-*.json 的 entries[].type）]
--hol-bg:#fdeceb
--hol-ink:#a5231b
--hol-line:#f3c7c2
--mk-bg:#fdf3e2
--mk-ink:#8a5300
--mk-line:#f0d9ac
--hol:#a5231b
--mk:#8a5300

[状态色]
--warn:#8a5300
--warn-bg:#fdf3e2
--warn-line:#f0d9ac
--crit:#c0392b
--tight:#b7791f
POS:#1a7f52
NEG:#b42318

[热力图 5 档（单色系明度递进，禁彩虹色阶）]
LEVEL_BG:#f2f4f7 #dce8fd #b9d2fb #8bb6f8 #5b95f2
LEVEL_INK:#8b949e #2b3440 #163a7a #ffffff

[弹性区（与稳定区靠「实线/虚线 + 实心/浅底」区分，不靠第二色相）]
ELASTIC_BG:#dfe5ee
ELASTIC_INK:#2b3440
ELASTIC_LINE:#9aa4b0

[派生 / 内联合法色值]
#f7d4d0 #f6e2be #f9edcf #fbdedb
#f4f8ff #fafcff #fbfbfc #fafbfc #e8ebef
#cfe0fb #c8ced6 #aeb6c0 #b9c0c9 #7a8a99
#4a8bf0 #c7dbfb
```

> **复核办法**（任何改动后跑一次即可，不必等作者通知；引自 engineer-render）：
> ```bash
> cd <包根>/skills/schedule-planning/scripts
> python render_desktop_calendar.py <任意课表.json> --out /tmp/x.html
> grep -o '#[0-9a-f]\{6\}' /tmp/x.html | sort -u
> ```
> 产物色值全集即为本块应声明的全集；两者不一致时以**脚本**为准并回改本块。

**排版与形状**：无衬线字体栈；圆角统一（建议 6–8 px）；间距走 4 px 栅格；**图标一律 inline SVG**（`currentColor` 描边，随字号缩放）。

---

## 4.3 语义色约束（不可当普通装饰改）

以下色值带**事实语义**，改色即改语义，不是视觉偏好问题：

| 色值 | 语义 | 绑定 | 改动的后果 |
|---|---|---|---|
| `#a5231b` | 法定节假日 | `data/holidays-2026.json` 中 `entries[].type == "holiday"`，2026 年共 **7** 条 | 用户分不清「放假」与「补班」 |
| `#8a5300` | 调休上班日 | 同上 `entries[].type == "make_up_workday"`，2026 年共 **6** 条 | 同上 |

> 2026 年数据共 **13** 条 entries = 7 holiday + 6 make_up_workday；2027 年仅 **2** 条 holiday、0 条 make_up_workday（预测态，见 `executable-delivery.md` §6）。

**强调色 `#2f6feb` 全站仅 1 个**，不得引入第二色相作同级强调。稳定区 / 弹性区**不靠第二色相区分**，靠两重冗余：

| 区 | 填充 | 描边 |
|---|---|---|
| 稳定区（每周固定） | 实心 `#2f6feb` | 实线 |
| 弹性区（单双周 / 指定周次） | 浅底 `#dfe5ee` | `1px dashed #9aa4b0` |

> **理由**（刻意设计，非权宜）：色觉障碍用户在**纯色相区分**下会失效；形状 + 明度的冗余是唯一对所有用户都成立的通道。
> 同类规则见周视图转场连线：临界 `#c0392b` 实线 / 紧张 `#b7791f` 虚线 / 宽松 `#b9c0c9` 虚线。

---

## 5. 自检契约

每个 `render_*.py` 须满足：

1. `--help` 退出码 0（由 `gates.py` 的 `exec` 门禁冒烟）。
2. 产物字节数 > 0 且含 `data-v4-*` 标记。
3. 产物中不出现：emoji 功能图标、`backdrop-filter`、Indigo→Pink 渐变。
4. stdout 输出产物绝对路径与字节数。

---

## 6. 落点与隐私

产物一律落用户目录 `%USERPROFILE%/.schedule-planner/out/`（支持 `--dir` 覆盖），**禁止写入包内任何目录**；任何指向包内路径的写入必须被 `assert` 拦住并报错，绝不静默改落别处。
