# 使用说明记录（让「上手引导 / 使用说明」及时且完整）

> 本文件是 `agents/course-tutor.md` §0 的子流程（**先 Read 再操作**）。
> 痛点：旧版仅把功能清单打印在首条消息，但**没有可追溯的记录**，且完整性依赖人工复述。
> 本特性把「使用说明」做成**可落盘、可复核**的机制。

## 一、两条纪律

1. **及时**：每次教师触发任一功能（含首次引导语本身的展示），立即调用记录器，
 不等会话结束、不被任何分支吞掉；
2. **完整**：记录含「功能名 + 时间 + 课程 + 一句话说明」，**绝不记录定位 ID / token**（§1.3 铁律）。

## 二、记录器（本地优先，云端可选）

```bash
# 触发任一功能后，立即记录一条
python3 "${CODEBUDDY_PLUGIN_ROOT}/course_usage_log.py" \
 --action "学情可视化看板" --course "<课程名>" --detail "生成自包含 HTML 看板"

# 教师想看「功能使用说明书」时
python3 "${CODEBUDDY_PLUGIN_ROOT}/course_usage_log.py" --report

# 若教师已建 usage_log 子表，把本地记录同步回中枢（主指令 调用，脚本只产出 JSON）
python3 "${CODEBUDDY_PLUGIN_ROOT}/course_usage_log.py" --export-json
```

- 本地落点：`~/.workbuddy/course-tutor/usage_log.md`（跨会话留存）+ `usage_log.json`（机器可读）；
- 云端（可选）：把 `usage_log.json` 的条目写回中枢 `usage_log` 子表（需教师先建，不与 7 核心键冲突）。

### 二·补　调用即记录（架构级自动埋点，v2.0.1 起）

**可靠性不再依赖「智能体记得调」**：以下功能脚本在**成功运行后自动**写一条使用记录
（内置 `course_usage_log.auto_record`，记录失败绝不影响功能本身）：

| 脚本 | 自动记录的动作名 |
|---|---|
| `course_viz.py` | 学情看板 |
| `course_points.py` | 积分计算 |
| `course_warn.py`（check/review/goal） | 学习预警·<子命令> |
| `course_datakit.py`（7 个子命令） | 数据分析·<子命令> |
| `scripts/course_archive.py` | 结课归档 |

> 注：`course_report.py`（教师周报）**未内置自动埋点**——周报由教师端按需触发生成、不在学生侧自动运行，
> 教师侧查看周报属于会话级行为，按本文 §一 `--action` 手动方式记录即可。
>
> 注：教师端一律使用**包根**的 `course_points.py` / `course_usage_log.py`（教师端包内 `scripts/` 下无这两个文件，勿引用 `scripts/` 同名路径）。

因此：**功能被真实执行 = 记录必然产生**。上面 `--action` 手动方式保留给
脚本之外的动作（首次引导语展示、菜单跳转等会话级行为）。
完整性自检（§四）时，先用 `--report` 看自动埋点统计，再补查手动项。

## 三、首次引导语必须「完整 + 记录」

`references/first_session_greeting.md` 的版式已覆盖全部功能；输出引导语后**立即记录一条**
`--action "首次引导语"`，确保「使用说明」本身也被记录为一次完整的上手引导。

## 四、完整性自检（防「结果不好」复发）

每次输出引导语前，对照主菜单 1–16 项逐条确认均在引导语中出现；缺任一项即补，不靠记忆。
记录器若写失败**不阻塞**主流程（下次会话仍会补记）。
