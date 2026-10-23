# B 类日历事实治理规范（holiday-fact-governance）

> **判据**：诊断报告 P1 —— 「事实部分我可以理解，但这个事实管哪部分」。
> **本文件的存在意义**：把"某天是什么日子"这一类事实从**排程者自证**手里收回来，统一交给 fact-verifier 查表 + 分级 + 签字。
> **唯一放行权**：fact-verifier。**消费者**：schedule-architect（只引编号，禁自判）。

---

## 1. 定义：什么是 B 类日历事实

**判定问句**：这条事实描述的是**某个日期的性质**吗？

| 是（B 类） | 不是（另归他类） |
|---|---|
| 2026-10-01 是法定假日 | 周一 1-2 节上高等数学（A 类材料事实） |
| 2026-10-10 是调休上班日 | 高数比英语难（主观判断，非事实） |
| 2026-10-19 是第 7 周周一 | 周四是"地狱日"（评价，非事实） |
| 第 18-19 周是考试周 | 建议把重任务排上午（决策，非事实） |

**边界提醒**：教学周次（"第 N 周"）属 B 类，但它由 `term-space.json` 反推得出，**不硬编码**。

---

## 2. 权威来源与只读纪律（写死）

| 项 | 规则 |
|---|---|
| **唯一事实来源** | `data/holidays-<year>.json` |
| **访问方式** | 只能经 `scripts/holiday_lookup.py` 查表，**成员不直接读 `data/`** |
| **可写性** | `data/` 为**只读基线**；文件内 `read_only: true` |
| **脚本写入包内** | 一律 `assert` 拦截（含 `python -O` 兜底抛错），**绝不静默改落别处** |
| **联网抓取** | **禁止**作为唯一数据源（不可复现、不可审计） |
| **数据更新** | 走「**新增来源条目 + 留痕**」，不就地改写既有条目 |

> **为什么禁联网**：诊断已实测，节假日的采集件自身声明「基于搜索结果页，未逐条核验原文」。若再允许运行期联网抓取，错误将不可追溯。故：数据落文件、带 `source_url` + `fetched_at` + `confidence` + `status`，每次引用可指到具体条目。

**通用规则文件的地位**：`references/china-calendar-rules.md` 提供**通用口径**（法定节假日有哪些、调休逻辑、农历速查、作息默认值），**已废止其作为事实来源的资格**，仅为提示口径。

---

## 3. 台账条目 schema（数据文件）

`data/holidays-<year>.json` 顶层字段：

```text
schema_version / year / data_kind / read_only
participates_in_scheduling_default
source : {authority, document_id, source_url, fetched_at, fetched_by,
          collection_channel, originally_verified, verification_note}
governance : {grading_and_release_owner, consumer, consumer_rule, write_rule}
counts : {holiday_entries, make_up_workday_entries, entries_total, holiday_days_total}
confidence_rationale : {level, reason}
entries[] : 见下
limits
```

`entries[]` 单条字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | string | 编号。假期区间 `H-<年份>-xx`；调休上班日 `HM-<年份>-xx` |
| `name` | string | 节假日名称 |
| `type` | enum | `holiday` ／ `make_up_workday` |
| `start` / `end` | date | 区间起止 `YYYY-MM-DD` |
| `days` | int | 天数 |
| `dates[]` | date[] | 展开后的具体日期 |
| `start_weekday` / `end_weekday` | string | 周几（中文） |
| `make_up_workdays[]` | object[] | 关联的调休上班日 `{date, weekday, note}` |
| `source_url` | string | 来源 |
| `fetched_at` | date | 抓取日期 |
| `confidence` | enum | `high` / `medium` / `low` / `unknown` |
| `status` | enum | `official` / `predicted` |
| `official_basis` | string | 官宣依据 |
| `official_basis_document` | string | 依据文号 |
| `originally_verified` | bool | 是否逐条核验过原文 |
| `note` | string | 备注 |

---

## 4. 分级表（fact-verifier 判定用，写死）

| # | 情形 | `confidence` | `status` | `计入` | 处置 |
|---|---|---|---|---|---|
| 1 | 官方已发布 + 数据命中 + 多源一致 | `high` | `official` | 按休息日 | 直接采用 |
| 2 | 官方已发布，仅单源或未逐条核验原文 | `medium` | `official` | 按休息日 | 采用 + 写入假设声明 |
| 3 | 未官宣（如 2027）+ 多源一致 | `medium` | `predicted` | **默认不计** | 写入假设声明，**默认不参与排程** |
| 4 | 未官宣 + 来源互斥（如春节三套预测） | `low` ／ `unknown` | `predicted` | 不可计 | 进待确认清单，用户拍板 |
| 5 | **数据文件无命中** | `unknown` | — | 不可计 | **禁止推断**，标注未知 |
| 6 | **校历声明与国家安排冲突** | `low` | — | 不可计 | 进待确认清单，**用户三选一** |

**调休上班日穿透**（诊断点名的两个最易错点）：

- `HM-2026-05` = 2026-09-20（周日）→ 国庆**节前**调休上班
- `HM-2026-06` = 2026-10-10（周六）→ 国庆**节后**调休上班

两者**均按工作日计容量**，且必须在排程输出中显式提示"本周六/周日要上班"。**禁止被"周末即休息"的默认逻辑吞掉。**

---

## 5. 交叉路由（A→B 两段串行）

见 `references/uncertainty-governance.md` §7。要点复述：

1. 先走 **A 类双通道转写**拿到校历原文条目（含 `term_start`、周次、节假日声明、调休声明）。
2. 再走 **B 类查表比对**：调 `scripts/holiday_lookup.py` 对 `data/holidays-<year>.json` 逐条比对。
3. **两段都过才放行**；冲突一律降 `low`，交用户三选一（以校历为准 / 以国家安排为准 / 两者都记并分别标注），**禁止成员自行择一**。

---

## 6. 查表接口（`scripts/holiday_lookup.py`）

| 参数 | 作用 |
|---|---|
| `--date YYYY-MM-DD` | 单日性质查询 |
| `--range START END` | 区间查询 |
| `--year YYYY` | 列出该年份全部条目 |
| `--selfcheck` | 双向索引 / 重叠 / 未官宣年隔离 / `unknown` 自检 |
| `--data-dir PATH` | 数据目录（默认包内 `data/`；负向对照时指向副本） |
| `--years YYYY ...` | 加载哪些年份文件 |
| `--include-predicted` | 显式开启 `predicted` 年份参与查询（**默认关闭**） |
| `--with-weekday-baseline` | 附一列纯日历算术基线（周六 / 周日），**明确标注非放行结论** |
| `--only-hits` / `--json` | 过滤与机器可读输出 |

**输出字段**：`日期 / 星期 / 性质 / 置信度 / 状态 / 来源编号 / 所属节假日 / 计入 / 说明`。

**关键行为**（实测确认）：

```text
2026-10-10  周六  调休上班日  high  official  HM-2026-06  H-2026-07  工作日
2026-10-01  周四  法定假日    high  official  H-2026-07   -           休息
2026-03-02  周一  unknown     -     -         -           -           不可计
   └─ [WARN] 未命中任何条目；不按「周末即休息」填充，须 fact-verifier 放行
```

---

## 7. 三条不可绕过的硬约束

1. **成员不手算**——日期性质必须由脚本查表得出，成员只分级签字。
2. **通用规则不当时实**——`china-calendar-rules.md` 是提示口径，不是数据源。
3. **无命中不脑补**——一律 `unknown`，进待确认清单，交用户裁决。

> **一句话口诀**：「先问是不是日子，再问是不是从材料里读出来的；两者都是 → 先转写、后比对，两段都过才放行。」
