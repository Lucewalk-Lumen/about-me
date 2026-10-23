# 可执行交付规范（v4）

> 目标：让日程离开聊天框，落到用户的手机、桌面与日历里，并在关键时刻主动找到用户。
> 交付标准不是"用户看懂了"，而是"**用户不用想起它，它也能准时找到用户**"。
> 归属：`delivery-automator`。

---

## 0. 本版的改动

v3 只覆盖 `.ics` 与表格导出。v4 补三块：

1. **HTML 交付规范**（§3）——5 类可视化产物 + `term-summary`；
2. **禁第三方图表库**升格为 **P0 红线**（§1）；
3. **N2 边界声明**（§4）——明确「不存在可移植的操作系统日历写通道」。

---

## 1. P0 红线（写在最前，无例外）

### P0-1 · 禁止一切第三方图表库

**禁止清单**：Chart.js / ECharts / D3 / Highcharts / Plotly / ApexCharts / Recharts …… 以及任何同类第三方图表库。

**强制替代**：全部图表**手写 SVG + CSS**（环形进度用 `stroke-dasharray`，热力图用 `<rect>` 栅格，条形用 `<rect>` 宽度映射）。

### P0-2 · 禁止 CDN 外链与资源型外引

产物为**单文件 HTML**，下列外引计数必须**全部为 0**：

| 类型 | 计数要求 |
|---|---|
| `<script src=...>` | 0 |
| `<link href=...>`（含字体 / 样式外引） | 0 |
| `<img src=...>`（含外站图片 / data URI 资产） | 0 |
| `<iframe>` | 0 |
| `<a href=...>`（外站跳转） | 0 |
| CSS `url(...)`（含 `@import` 与背景图外引） | 0 |

**三条理由**（写进规范，不是为了凑数）：

1. **离线可用**：用户可能在无网环境（教室、地铁、校园网隔离区）打开；外引资源一断，页面就白屏或降级成不可读。
2. **CSP 限制**：预览面板与企业环境普遍收紧 CSP，外部 `script` / `style` / `font` 会被直接拦掉，产物在别人的机器上是坏的。
3. **可审计**：单文件、零外引 ⇒ 产物内容 = 本次生成的全部内容，可逐行 diff、可离线复核、不随远端资源变化而变化。

### P0-3 · 禁止 emoji 作功能图标

用可矢量缩放的 **inline SVG** 或标准文字字形（如「稳定区 / 弹性区」「安全 / 临界 / 危险」）。

详见 `references/visualization-spec.md` §4。

---

## 2. .ics 生成规范

统一使用 `scripts/generate_ics.py`，标准 iCalendar 2.0：

**必填字段**

- `SUMMARY`：课程/任务名（简短，含周次标记可放描述里）
- `DTSTART` / `DTEND`：`TZID=Asia/Shanghai` 本地时间
- `LOCATION`：**楼栋 + 房号**（这是"走错楼"的直接防线，不能只写课程名）
- `DESCRIPTION`：教师 / 周次规则 / 备注 / 携带物品
- `VALARM`：课前提醒，**默认提前 10 分钟**；跨楼或需更衣的课程提至 20-25 分钟

**周次规则映射表**（最易出错，逐条核对）

| 原始表述 | RRULE |
|---|---|
| 每周（1-16 周） | `FREQ=WEEKLY;BYDAY=MO;COUNT=16` |
| 单周（1,3,5…） | `FREQ=WEEKLY;INTERVAL=2;BYDAY=MO;COUNT=8`（首周为单周） |
| 双周（2,4,6…） | `FREQ=WEEKLY;INTERVAL=2;BYDAY=MO;COUNT=8`（首周为双周） |
| 1-9 周 | `FREQ=WEEKLY;BYDAY=MO;COUNT=9` |
| 18-19 周 | `FREQ=WEEKLY;BYDAY=MO;COUNT=2`（起始落在第 18 周） |
| 空周排除（第 1/17/20 周无课） | `EXDATE` 排除，或确认规则本身不含 |

> **节假日排除**：法定假日区间须用 `EXDATE` 排除；**调休上班日不得排除**（按工作日计容量）。

**生成后自检（必做）**

- [ ] 台账条目数 == 展开后事件数（守恒）
- [ ] 单周课数量 == 台账单周课 × 8（或对应周数），双周同理
- [ ] 抽查 3 个事件的 DTSTART/LOCATION 与台账一致
- [ ] 无 0 条事件、无异常膨胀（典型 bug：单周排成每周，事件数翻倍）

---

## 3. HTML 交付规范（v4 新增）

### 3.1 六类产物（含 `term-summary`）

| 产物文件 | 生成脚本 | 内容 | 对应需求 |
|---|---|---|---|
| `out/desktop-calendar.html` | `scripts/render_desktop_calendar.py` | 整学期桌面日历：按周次铺开、当前周高亮、节假日/调休上班日标注、点某天看当日安排、周次/月历切换 | N2 / AC5 |
| `out/week-view.html` | `scripts/render_week_view.py` | 单周横向时间轴（周一至周日 × 时间），稳定区/弹性区分色，相邻项画转场连线并按「跨楼 ≤15 分钟」标临界 | N3 / AC6 |
| `out/term-heatmap.html` | `scripts/render_term_heatmap.py` | 20 周 × 7 天色阶，标注空周/缓冲周/密集周，节假日与调休上班日加边框 | N3 / AC6 |
| `out/dashboard.html` | `scripts/render_dashboard.py` | 手写 SVG 环形三口径完成率（任务数/工时/P0）+ 连击打卡 + 本周 vs 上周对比 + 归因分布 | N3 / AC6 |
| `out/achievements.html` | `scripts/render_achievements.py` | N5-b **降级形态**：学期进度条 + 连击打卡日历 + 12 枚 SVG 徽章墙（点击看解锁条件）。**不是游戏**：无积分商城、无排行榜、无后端 | N5-b / Q1 裁决 |
| `out/term-summary.md` / `.html` | `scripts/term_summary.py` | N5-c 学期总结：完成率三口径 / 按周 / 按月 / P0 单列 / 归因分布 / 事实错误项清单 | N5-c |

### 3.2 命名与用途约定

| 约定 | 内容 |
|---|---|
| 目录 | 一律落 `%USERPROFILE%/.schedule-planner/out/`（`--dir` 可覆盖，**不得指向包内**） |
| 命名 | 小写 kebab-case，与脚本一一对应（`render_X.py` → `X.html`，`X` 已去 `render_` 前缀） |
| 单文件 | 所有 CSS / JS / SVG **内联**，无外引，离线可开 |
| 用途 | 每份产物须在交付清单中写明「给谁看 / 解决什么」 |

### 3.3 流水线顺序

```bash
python scripts/generate_ics.py timetable.json --out schedule.ics --csv schedule.csv --report
python scripts/render_desktop_calendar.py timetable.json --out desktop-calendar.html --report
python scripts/render_week_view.py timetable.json --out week-view.html --week 7
python scripts/render_term_heatmap.py timetable.json --out term-heatmap.html
python scripts/render_dashboard.py timetable.json --out dashboard.html
python scripts/render_achievements.py timetable.json --out achievements.html
python scripts/term_summary.py timetable.json --out term-summary.md --html term-summary.html
```

> 周次一律由 `term_start` 反推（样例 `2026-09-07`），**禁止硬编码周次**。

### 3.4 产物自检契约

| # | 断言 | 判据 |
|---|---|---|
| 1 | 产物**非空** | 字节数 > 0 |
| 2 | 含约定标记 | 产物含 `data-v4-*` 标记 |
| 3 | 零外引 | §1 P0-2 六类计数全为 0 |
| 4 | 无 emoji 功能图标 / 无 `backdrop-filter` / 无渐变发光描边 | P0-1 / P0-2 / §1 |

---

## 4. N2 边界声明（不许含糊）

> **桌面日历的可落地形态 = 本地 HTML 应用 + WorkBuddy 预览面板打开。**
> **不存在可移植的操作系统日历写通道。**

**本机实测证据（三条，均为运行期真实返回）**：

| 通道 | 实测结果 |
|---|---|
| Outlook COM（`New-Object -ComObject Outlook.Application`） | `UNAVAILABLE → 80040154 没有注册类 (REGDB_E_CLASSNOTREG)` |
| Windows 日历 AppX（`Get-AppxPackage *WindowsCalendar*`） | **无结果**（未安装） |
| `.ics` 文件关联处理器 | `HKCU\...\FileExts\.ics\UserChoice` → `AppX18q1gk8kdws5gt2g5c62cxc6cqydq7tsw`（UWP 处理器）；本机仅装 `Microsoft.OutlookForWindows`（UWP 版，**不暴露 COM 自动化接口**） |
| OS | Windows 11 家庭版中文版 |

**结论**：Windows 侧没有可从脚本稳定调用、且跨机器可移植的日历写入通道。

**两条硬纪律**：

1. **`.ics` 导出保留**为「用户自行导入系统日历」的**备份路径**——这是合规且有用的，不算越界。
2. **不得声称**能「直接调用」「写入」「同步」操作系统日历。文案里出现这类表述即为违规（对应 P3「日历功能大家都有」的病根之一：承诺了做不到的能力，反而把真差异化淹没）。

---

## 5. 跨平台导入指引

| 平台 | 路径 |
|---|---|
| iOS 日历 | 打开 `.ics` → 选「加入日历」；或 设置 → 日历 → 账户 → 添加已订阅日历 |
| Android（Google 日历） | 日历 → 设置 → 导入和导出 → 导入 |
| Android（系统日历） | 文件管理器打开 `.ics` → 选择日历应用 |
| Outlook | 文件 → 打开和导出 → 导入/导出 → 从另一程序或文件导入 → iCalendar |
| 飞书日历 | 日历 → 设置 → 导入日程 → 上传 `.ics` |
| 企业微信/钉钉日历 | 日历 → 导入日程 |

**最后一道校验**：导入后请抽查 2-3 个事件，确认时间与地点无误。**首次导入的人工抽查不可替代**——这是发现系统性错误（如整体偏移一天、地点全错）的最快方式。

---

## 6. 数据来源声明（防编造三层 · B 层告知）

> `data/holidays-2026.json` 自带 **`originally_verified=false`**——该文件源自采集件，**未逐条核验 gov.cn 原文**。

**硬纪律**：

1. 在该数据**未以 gov.cn 原文逐条核验之前**，**不得**将其作为「已核验基线」对外呈现。
2. 消费该数据的产物（含 `desktop-calendar.html` / `week-view.html` / `term-heatmap.html`）须在**页面顶部渲染琥珀色告警条**，标明数据来源、抓取日期与未核验状态。
3. 2027 年数据为国家**尚未发布**内容，一律标 `status=predicted` + 「预测 · 待官宣」，**默认不参与排程**。

> **口径一致性**：本声明与 `skills/schedule-planning/SKILL.md`、`references/holiday-fact-governance.md` 保持一致。

---

## 7. 拒绝交付的条件

出现以下任一情况，必须拒绝导出并退回主理人：

- 台账存在未确认的 `low` / `unknown` 项
- 周次规则无法唯一确定（如"单周"未说明起始周）
- 事件数与台账条目数不守恒且无法解释
- 关键地点缺失（提醒里没有楼栋房号 = 防走错楼的功能失效）
- 产物为空（字节数 = 0）或缺 `data-v4-*` 标记
- 产物含任何外引资源（§1 P0-2 任一计数 ≠ 0）
