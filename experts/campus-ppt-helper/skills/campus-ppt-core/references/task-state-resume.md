# 任务状态与断点续传（Task State & Resume）

> 面向主理人（lead）与全体成员。解决**长链路多智能体协作在会话中断、崩溃、重连后"从头再来"**的问题——
> 把流程状态**外化到可复读的文件**，使任务可在任意阶段**幂等重入**，而非依赖易失的会话上下文。

## 一、为什么需要（本包的固有风险）

本团的标准链路是 `采集 → 结构 → 制作 → 质检`，全链路可能跨 5 个阶段、数十分钟、大量工具调用。
长链路的软肋：

| 风险 | 后果 |
|------|------|
| 会话崩溃 / 意外关闭 / 网络中断 | 已完成的采集、已定稿的大纲全部丢失，重开后主理人"不知道进行到哪" |
| 上下文窗口被挤爆 | 早期阶段产出被截断，后段基于残缺记忆继续 → 内容漂移 |
| 成员并行时某一支失败 | 无法只补跑失败支，只能整条重来 |
| 用户中途离开再回来 | 用户也要重新交代一遍需求 |

**根因**：流程状态只存在于会话内存中。**解法**：状态外化为文件（State Manifest），每阶段结束即落盘。

## 二、状态清单（State Manifest）契约

在**用户工作目录**（非安装包内）建立任务工作区，约定一个状态文件 `CAMPUS_PPT_STATE.md`：

```
<工作目录>/campus-ppt-run-<任务简称>/
├── CAMPUS_PPT_STATE.md          # 状态清单：唯一权威进度真源
├── 01-brief.md            # 需求口径基线（见 interaction-protocol.md）
├── 02-collected.md        # 采集产出（含未验证标注）
├── 03-outline.md          # 结构产出
├── 04-deck.pptx           # 制作产出（+ 04-maker-notes.md 生成指令）
└── 05-qa.md               # 质检报告
```

`CAMPUS_PPT_STATE.md` 最小字段：

| 字段 | 含义 | 示例 |
|------|------|------|
| `task_id` | 任务标识 | `campus-ppt-run-管理学原理串讲` |
| `scenario` | 场景（教学/答辩/实习/党建党政） | `教学` |
| `template` | 选定模板（云端标题 + 本地缓存路径） | `广财-07-绿色极简模板`（缓存 `~/campus-ppt-cache/广财-07-绿色极简模板.pptx`） |
| `route` | 选路（A 风格重绘 / B 模板保真） | `A` |
| `phase_status` | 各阶段状态，取值 `pending / in_progress / done / blocked / skipped` | `collect=done, outline=done, make=in_progress, qa=pending` |
| `artifacts` | 各阶段产物文件路径 | `03-outline.md → …` |
| `open_questions` | 未决问题（用户待答/待补） | `模板待确认` |
| `updated_at` | 最后更新时间（ISO 8601 含时区） | `2026-10-06T18:10:00+08:00` |

> **落盘时机（按模式分级）**：重模式——每完成一个阶段、每发生一次用户口径变更、每次会话即将结束（或用户说"先到这"）时，必须更新 `CAMPUS_PPT_STATE.md`。**轻模式——仅"大纲确认门通过后"与"交付前"两次强制落盘，其余阶段标 `skipped`**（轻模式全链仅 3 次调度、预期 <10 min，落盘 5 次的边际收益趋近于零；大纲已落盘，崩溃重入即走 Workflow B，天然幂等）。并行分支（Workflow C）无论模式都按现行分支登记。

## 二.五、可观测记录（run_metrics）

`CAMPUS_PPT_STATE.md` 内嵌 `run_metrics` 块，**寄生在既有落盘时机上，不产生额外往返**。字段模板：

```yaml
run_metrics:
  schema_version: 1
  task_id: campus-ppt-run-<任务简称>
  mode: light | heavy
  tripwire_reason: <分流理由>
  t0_dispatch_start: <ISO>
  t0_source: reported | restored
  phases:
    collect:  {start: "", end: "", duration_s: 0, skipped: false}
    outline:  {start: "", end: "", duration_s: 0, llm_calls: 0, files_written: 0}
    make:     {start: "", end: "", duration_s: 0, llm_calls: 0, files_written: 0, skill_used: ""}
    qa:       {start: "", end: "", duration_s: 0, llm_calls: 0, files_written: 0}
  totals: {llm_calls: 0, user_confirms: 0, io_writes: 0, wall_time_s: 0}
  tripwire_review: {expected: light, actual: "", verdict: pending}
  alerts: []
```

- **6 个时间戳**锚定既有状态更新点；`llm_calls` 按成员每动作 +1 心算（±10%，不读 SDK 日志），成员回传消息末尾自报"本次消耗约 N turns"。
- **预警阈值**：轻模式单阶段 >10min（WARN）/ >20min（BLOCK 问用户或升重）；重模式单阶段 >20min（WARN）；QA 进入第 3 轮复验（BLOCK 强制升重）；collect 降级（WARN 滑向重模式）。
- **验收指标（机器可读）**：轻模式 `llm_calls` ≤25、`user_confirms` ≤2、`io_writes` ≤8、`dispatch_count` ≤3。
- **红线**：`run_metrics` 所在状态文件**必须是任务工作区级**（本节目录），**不得写入用户工作目录全局状态文件**——避免同目录串行多任务复用 `task_id` 导致数据写串。重入时读自己任务文件续写，非从 0 累计。

## 三、幂等重入协议（崩溃/重连后怎么做）

会话恢复后，主理人**第一步不是重新提问，而是先找状态文件**：

1. **探测**：查找 `campus-ppt-run-*` 目录与 `CAMPUS_PPT_STATE.md`。
   - 找不到 → 全新任务，走标准分诊（`interaction-protocol.md`）。
   - 找到 → 读出 `phase_status` 与 `open_questions`，**复述进度给用户确认**（"上次做到 X 阶段，还差 Y，是否继续？"），确认后再动手。
2. **重入点判定**：从**首个非 `done` 的阶段**继续，已完成阶段**不重跑**。
   - `collect=done` → 跳过采集，直接读 `02-collected.md` 进入结构。
   - `outline=done` → 跳过结构，直接进入制作。
   - 仅当上游产物**缺失或明显过期**（如模板已更换、口径已变更）时才回退重跑。
3. **幂等要求**：每个阶段重入时必须**覆盖而非追加**其产物文件，避免出现"两份大纲""两个 pptx"造成下游歧义。
4. **禁止**：崩溃恢复后凭记忆重写已完成阶段的内容；**一律以落盘产物为准**，记忆与文件冲突时信文件。

## 四、阶段产物与"可否跳过"判据

| 阶段 | 产物 | 跳过条件（重入时） |
|------|------|------------------|
| Phase 1 采集 | `02-collected.md` | 文件存在且 `phase_status.collect=done`，且本次未新增采集诉求 |
| Phase 2 结构 | `03-outline.md` | 文件存在且 `outline=done`，且口径基线（`01-brief.md`）未变更 |
| Phase 3 制作 | `04-deck.pptx` + `04-maker-notes.md` | 文件存在且 `make=done`，且模板/选路未变更 |
| Phase 4 质检 | `05-qa.md` | 文件存在且 `qa=done`；若上游任一产物被重写，则 `qa` 必须回退为 `pending` |

> **级联失效规则**：任一上游产物重写 ⇒ 其下游状态全部回退为 `pending`（大纲变了，成品与质检都作废）。

## 五、并行分支的断点

Workflow A 的 Phase 2（结构）与 Phase 3 前的模板准备可并行；Workflow C 的多章出片天然多支。
- 每支在 `CAMPUS_PPT_STATE.md` 里登记为独立子项：`branch: ch03=done, ch04=in_progress`。
- 某支失败**只标该支 `blocked`**，其余支照常推进，最后统一对账（见 `batch-qa-reconciliation.md`）。
- **禁止**因单支失败而把整任务标为失败。

## 六、与其它标准的衔接

- 与 `interaction-protocol.md`：`CAMPUS_PPT_STATE.md` 的 `open_questions` 与口径基线 `01-brief.md` 同源，二者必须一致。
- 与 `quality-evaluation-standard.md`：质检"任务完成度"维度应核对 `phase_status` 是否全部 `done`，`blocked/skipped` 项是否已在报告说明。
- 与 `batch-qa-reconciliation.md`：批量任务的数量/md5 对账以 `CAMPUS_PPT_STATE.md` 的分支登记为准。
