# schedule-planning

日程规划方法论库。为"日程规划专家团"提供**事实核验**、任务拆解、精力管理、排程、执行剧本与**可执行交付**的标准方法，以及中国本地日历规则与真实翻车案例库。

## 使用时机
- 方案依赖外部材料（截图/PDF/表格/他人信息），需要核验事实 → 读 `references/uncertainty-governance.md`
- 需要判定某日是不是法定假日 / 调休上班日 / 教学周第 N 周 → 读 `references/holiday-fact-governance.md`，并调用 `scripts/holiday_lookup.py`
- 需要导入校历 / 换算周次与日期（Term Space） → 读 `references/methodology.md`，并调用 `scripts/import_school_calendar.py`
- 需要把日程导出为日历文件、渲染可视化或配置提醒 → 读 `references/executable-delivery.md` 与 `references/visualization-spec.md`，并调用 `scripts/generate_ics.py` 及各 `scripts/render_*.py`
- 需要记录与汇总学期功劳 → 读 `references/logbook-spec.md`，并调用 `scripts/logbook.py` 与 `scripts/term_summary.py`
- 需要处理转场风险、空周/密集周、临界日执行剧本 → 读 `references/execution-playbook.md`
- 任务拆解需要 WBS/优先级方法 → 读 `references/methodology.md`
- 排程需要中国法定节假日、调休、农历、作息规则 → 读 `references/china-calendar-rules.md`
- 复盘需要归因框架与迭代策略 → 读 `references/methodology.md` 复盘章节
- 想了解本规范为何这样设计 → 读 `references/failure-cases.md`（真实翻车案例库，规范的来源）

## References
- `references/uncertainty-governance.md` — 不确定性治理（A/B 两类事实分域、枚举白名单锚定、双通道交叉校验、置信度四级、排程前闸门、阶段冻结、交叉路由）
- `references/holiday-fact-governance.md` — B 类日历事实分级表 + 数据文件只读纪律（无命中即 unknown）
- `references/visualization-spec.md` — 5 类视图规格、手写 SVG/CSS 约束、配色与图标红线
- `references/logbook-spec.md` — 功劳档案 schema + 落盘位置 + 隐私门禁
- `references/executable-delivery.md` — 可执行交付（.ics 规范、周次→RRULE 映射、周期提醒、跨平台导入、拒绝交付条件）
- `references/execution-playbook.md` — 执行剧本与节奏管理（转场风险矩阵、空周/密集周预警、临界日剧本、易漏项清单）
- `references/failure-cases.md` — 真实翻车案例库（课表截图排程案例：7 项系统漏洞 + 5 项应用隐患 + A-F 对策映射）
- `references/methodology.md` — 拆解/排程/复盘方法论（WBS、艾森豪威尔矩阵、时间盒、缓冲设计、四类偏差归因）
- `references/china-calendar-rules.md` — 中国本地日历规则（法定节假日类型、调休逻辑、午休通勤默认值、农历节日速查）

## Scripts

> 全部脚本**仅依赖 Python 标准库**，**禁止任何第三方图表库**（ECharts / Chart.js / D3 / CDN 一律不用），图表一律**手写 SVG + CSS**；产物为**单文件 HTML**，无外链、离线可开。

| 脚本 | 作用 |
|---|---|
| `scripts/generate_ics.py` | 从结构化课表 JSON 生成标准 `.ics`（含单双周 RRULE、节假日 EXDATE、课前 VALARM）与明细 CSV，输出数量守恒自检报告 |
| `scripts/holiday_lookup.py` | B 类日历事实查表：单日 / 区间 / 整年查询，调休上班日穿透与分级，`--selfcheck` 自检 |
| `scripts/import_school_calendar.py` | N5-a 校历导入器：JSON / CSV 输入，正负例判定，产出 `term-space.json`，`--selftest` 内建断言 |
| `scripts/logbook.py` | N4 功劳档案读写：`--add` / `--list` / `--stats` / `--export` / `--purge`，`--selftest` 自检 |
| `scripts/term_summary.py` | N5-c 学期总结：按周 / 按月 / 按优先级聚合，输出 Markdown，`--html` 附产 HTML 版 |
| `scripts/render_desktop_calendar.py` | N2 桌面日历 HTML：按周次铺开、当前周高亮、节假日 / 调休上班日标注、点某天看当日安排 |
| `scripts/render_week_view.py` | N3 周视图 HTML：单周横向时间轴，稳定区 / 弹性区分色，相邻项画转场连线并标临界 |
| `scripts/render_term_heatmap.py` | N3 学期负载热力图 HTML：20 周 × 7 天色阶，标注空周 / 缓冲周 / 密集周 |
| `scripts/render_dashboard.py` | N3 完成度仪表盘 HTML：手写 SVG 环形三口径完成率 + 连击打卡 + 归因分布 |
| `scripts/render_achievements.py` | N5-b 学期成就页 HTML（游戏化降级形态）：进度条 + 连击日历 + 徽章墙，无后端 / 账号 / 排行 |

**流水线顺序**（与 REQUIREMENTS 一致）：

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
> 产物默认落用户目录 `%USERPROFILE%/.schedule-planner/out/`；任何写入包内目录的尝试会被 `assert` 拒绝。


## 事实管辖权（划线）

> P1 的正解：**按「事实描述的对象」分域，不按「文件格式」分域。**

| 域 | 内容 | 归属 |
|---|---|---|
| **A 类 · 材料事实** | 课程名 / 时间 / 地点 / 周次规则 / 教师 / 人员名单 | fact-verifier（双通道转写 + 枚举白名单） |
| **B 类 · 日历事实** | 法定假日 / 调休上班日 / 普通周末 / 教学周第 N 周 / 考试周 | fact-verifier（查表 + 分级 + 放行签字） |
| **决策**（不是事实） | 这天放不放假 / 排不排课 | schedule-architect（**只引编号，禁自判日期性质**） |

**口诀**：「先问是不是日子，再问是不是从材料里读出来的；两者都是 → 先转写、后比对，两段都过才放行。」

## 铁律速览
1. **先核真后排程**：事实闸门未放行，不得开始排程。
2. **不确定必须可视化**：每条事实带 confidence，low/unknown 一律交用户裁决，禁止猜测填补。
3. **枚举源优先**：材料里的地图/图例/表头就是白名单，先抽出来再读表。
4. **覆盖率优先于正确率**：逐格编号扫读，漏读的格子不会报错，只会安静消失。
5. **交付才算完成**：没有进日历、没有提醒的日程，等于没做。
