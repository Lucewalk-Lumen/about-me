# 功劳档案规范（logbook-spec）

> **目标**：把"完成任务"变成**可累积、可统计、可迁移**的学期功劳档案。
> **独占读写权**：`review-coach`。其他成员不得直接写档案。
> **唯一落点**：**用户目录**。`data/` 与包内任何路径**一律只读**。

---

## 1. 落盘位置

| 项 | 值 |
|---|---|
| 默认目录 | `%USERPROFILE%/.schedule-planner/`（Unix 下 `~/.schedule-planner/`） |
| 档案文件 | `logbook.jsonl` |
| 交付产物 | `%USERPROFILE%/.schedule-planner/out/` |
| 覆盖方式 | `--dir DATA_DIR`（**不得指向包内**，否则 `assert` 拦截并报错） |

> **包内只读纪律**：任何脚本写入包目录的行为必须被 `assert` 拦住，并**显式报错**。
> 绝不静默改落别处——静默重定向会让"包内只读"这条门禁形同虚设。

---

## 2. 记录 schema（JSONL，一行一条）

### 2.1 字段表

| 字段 | 必填 | 类型 | 说明 |
|---|---|---|---|
| `timestamp` | 是 | string | 写入时刻；缺失时由 `now_timestamp()` 自动补齐 |
| `date` | **是** | date `YYYY-MM-DD` | 任务所属日期 |
| `task_id` | **是** | string | 任务编号，如 `T1.1` |
| `title` | **是** | string | 任务标题 |
| `status` | **是** | enum | `done` / `partial` / `skipped` |
| `minutes` | **是** | int | 实际投入分钟，≥ 0 |
| `week_no` | 是 | int | 由 `week_no_of(date, term_start)` 反推，禁止硬编码 |
| `tags` | 是 | string[] | 标签，如 `["实验","复习"]`；自动归一化 |
| `note` | 是 | string | 备注，可为 `null` |
| `planned_minutes` | **自动** | int | 计划工时；**未显式给则回落到 `minutes`**，因此**恒存在** |
| `actual_minutes` | **自动** | int | 实际工时；同上，**恒存在** |

**必需字段（校验用 `REQUIRED_FIELDS`）**：`date` / `task_id` / `title` / `status` / `minutes`

> **行 schema = 11 字段**（实测确认）：
> `timestamp` / `date` / `task_id` / `title` / `status` / `minutes` / `week_no` / `tags` / `note` / `planned_minutes` / `actual_minutes`
> 即 9 个基础字段 + 2 个自动派生字段；`planned_minutes` / `actual_minutes` 未显式传入时**回落到 `minutes`**，故最小写入记录亦为 11 字段。

### 2.2 可选扩展字段

| 字段 | 说明 |
|---|---|
| `id` | 记录唯一编号 |
| `plan_id` | 所属计划编号 |
| `priority` | `P0` / `P1` / `P2` |
| `attribution` | 归因：**六值**枚举，见 §3 |
| `fact_refs` | 关联事实台账编号（`F-xx` / `H-<年份>-xx` / `HM-<年份>-xx`） |
| `planned_minutes` | 计划工时 |
| `actual_minutes` | 实际工时 |
| `evidence` | 证据 |

> **读时兼容别名**：`term_week` → `week_no`；`minutes` 缺失时回退取 `actual_minutes` → `planned_minutes`。

### 2.3 样例记录

```json
{"timestamp":"2026-10-21T16:40:00+08:00","date":"2026-10-21","task_id":"T1.1",
 "title":"高数作业 P12-15","status":"done","minutes":75,"week_no":7,
 "tags":["复习"],"note":"比预估快 15 分钟"}
```

---

## 3. 归因枚举（六值，含「无偏差」）

| 值 | 含义 |
|---|---|
| `none` | 无偏差（已完成） |
| `overload` | 计划过载 |
| `estimate` | 估算失真 |
| `interrupted` | 外部打断 |
| `motivation` | 动力缺失 |
| `fact_error` | **事实错误**（材料读错 / 地点搞错 / 周次记错，计划前提不成立） |

**`fact_error` 专办**：凡归因于此的项，**不得只做计划层面修正**，必须回退 fact-verifier 重核台账并更新白名单（把错误值加入形近卡控），否则下次还会错。

---

## 4. 接口契约

### 4.1 命令行（`scripts/logbook.py`）

| 参数 | 作用 |
|---|---|
| `--add` | 追加一条记录 |
| `--list` | 列出记录（可按 `--week` / `--from --to` / `--range` 过滤） |
| `--stats` | 统计（三口径完成率 + 归因分布 + 最长连击） |
| `--export` | 导出（`--fmt json|csv|md`，`--out` 指定路径） |
| `--purge` | 清空档案（**须 `--yes` 二次确认**） |
| `--selftest` | 内建自检 |
| `--dir` | 覆盖档案目录（不得指向包内） |
| `--term-start` | 第 1 周周一，默认 `2026-09-07` |
| `--json-out` | `list` / `stats` 以 JSON 输出，供下游脚本消费 |

**写入入参**（`--add` 时用）：

| 参数 | 说明 |
|---|---|
| `--date` | 任务日期 `YYYY-MM-DD`（必需） |
| `--task-id` | 任务编号，如 `T1.1`（必需） |
| `--title` | 任务标题（必需） |
| `--status` | `done` / `partial` / `skipped`（必需） |
| `--minutes` | 实际投入分钟，≥ 0（必需） |
| `--tags` | 标签，逗号分隔，如 `实验,复习` |
| `--note` | 备注 |
| `--priority` | 优先级 `P0` / `P1` / `P2` |
| `--attribution` | 归因六值：`none` / `overload` / `estimate` / `interrupted` / `motivation` / `fact_error` |
| `--plan-id` | 所属计划编号，如 `P-2026-W07` |
| `--planned-minutes` | 计划工时（不给则回落到 `minutes`） |
| `--actual-minutes` | 实际工时（不给则回落到 `minutes`） |
| `--fact-refs` | 关联台账编号，逗号分隔，如 `F-01,H-2026-03` |
| `--json` | 整条记录的 JSON 字符串（替代上述分散入参） |

> **注意**：`--priority` 与 `--attribution` 是 `--stats` 输出 P0 完成率与归因分布的依赖字段；若省略，统计口径会缺失对应维度。

### 4.2 Python API

```text
Logbook(data_dir=None, term_start=DEFAULT_TERM_START)
    .add(date, task_id, title, status, minutes, tags, note, record=None, **extra)
    .purge(confirm=False)
    .load()
    .list_entries(week=None, date_from=None, date_to=None)
    .by_week(week)                 # 单参：第 week 周
    .by_term()
    .by_range(date_from, date_to)
    .stats()

load_entries(path=None, term_start=DEFAULT_TERM_START)   # 模块级
```

> **提示**：`by_week` 是**单参**签名 `by_week(week)`，不是 `(start, end)`。区间查询请用 `by_range(a, b)`。
>
> **周次换算口径**：`week_no` 由模块级函数 `week_no_of(day, term_start)` 反推得出，**不是 `Logbook` 的方法**。
> 调用方如需自行换算周次，应 `from logbook import week_no_of`，且 `term_start` 一律取 `term-space.json` 的值（样例 `2026-09-07`），**禁止硬编码周次**。

### 4.3 校验与异常

- 缺必需字段 → 抛 `ValidationError`
- 写入目标落在包内 → `assert` 拦截 + 显式抛错（含 `python -O` 兜底），**不静默重定向**

---

## 5. 隐私门禁

| 规则 | 内容 |
|---|---|
| **不外发** | 不联网上传、不写任何远端 |
| **不落包内** | 档案与产物只落用户目录；包内 `data/` 只读 |
| **可导出** | `--export --fmt json|csv|md` 开放格式，随时迁移 |
| **可清除** | `--purge --yes` 一键清空 |
| **敏感路径拦截** | 目标路径含 `.workbuddy` / `.claude` / `.codebuddy` / `marketplaces` 片段时拒绝写入 |
| **数据最小化** | 仅记录排程与复盘必需字段；`note` 由用户自主填写 |

---

## 6. 与 Term Space 的关系

`week_no` 一律由**模块级函数** `week_no_of(day, term_start)` 按 `term_start=2026-09-07` 反推，**禁止硬编码周次**。

> **口径澄清（易错点）**：`week_no_of` 是 `logbook` 模块的**模块级函数**，**不是 `Logbook` 类的方法**。
> 调用方应 `from logbook import week_no_of`，而 `Logbook().week_no_of(...)` 会抛 `AttributeError`。

`scripts/term_summary.py` 消费 `logbook.jsonl` + `term-space.json` 做学期聚合，其周次同样按 `term_start` 反推。

样例锚点：

| 日期 | 周次 |
|---|---|
| 2026-09-07 | 第 1 周 |
| 2026-10-19 | 第 7 周 |
| 2026-10-25 | 第 7 周 |
| 2027-01-04 | 第 18 周 |
| 2027-01-11 | 第 19 周 |
