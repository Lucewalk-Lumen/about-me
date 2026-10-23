# 课程伴学精灵 · 参考细则（cache_files.md）

> 引用方式：`${CODEBUDDY_PLUGIN_ROOT}/references/skill/cache_files.md`。下文 `§` 编号沿用学生端 主指令 原有编号。

## 5. 本地缓存文件

| 文件 | 路径 | 作用 |
|---|---|---|
| 学号 + 姓名 | `~/.workbuddy/student_sid.txt` | 两行文本：第 1 行学号、第 2 行姓名（双因子验证用） |
| **云端资产缓存目录** | `~/.workbuddy/course_tutor/assets/<course_id>/` | 学生端 `fetch_assets.py` 取回云端课程资产后的落点；版本更新时旧版改名为 `_prev` 保留一版可回退 |
| **中枢配置路径（旧）** | `~/.workbuddy/course_tutor_hub.txt` | 两行文本：第 1 行 `data_hub_config.json` 的**绝对路径**、第 2 行该文件 sha1 前 12 位。重跑 `discover_hub.py` 重写配置后写入，**再开会话找不到课程中枢时靠它还原**。此为旧版升级遗留的还原兜底，新版正常流程不依赖 |
| 模式（可选） | `~/.workbuddy/student_mode` | 内容 `test` 时走测试模式 |
| 待补传数据（可选） | `~/.workbuddy/usage_pending.jsonl` | 写入失败时的本地兜底队列（每行记录含目标定位，见下） |

> **更新包不会动**学号姓名缓存、待补传队列与`student_mode`——只换课程包内容与指针。

> 以上文件**一律 UTF-8 写入、`\n` 换行、按平台拼路径**（Windows 下不要用 `/` 硬拼，也不要用系统默认编码写中文）。

> 学生端**不保存**角色档案（花名 / 头像）：身份以名册中的学号 + 姓名为准。

> **多包隔离（防跨师数据污染，不可协商）**：
> `usage_pending.jsonl` 是全局路径，但**每行入队记录必须携带目标定位**——
> `usage_file_id` 与目标表名（`usage` / `summaries`），取自**入队当时**该生所属课程条目
> （`courses.<course_id>`，包内 `data_hub_config.json`）。
> 补传时**只处理目标 `usage_file_id` 与当前包定位一致**的记录；不一致的**留在队列**，
> 等学生回到来来源会话的会话再补传。
> 没有这条隔离，A 老师包里补传失败的学情会在 B 老师包启动时被写进 B 的 Usage 文件——
> 学错课、错老师、错学生档案，属于最严重级别的数据污染。
> 学号 + 姓名缓存（`student_sid.txt`）**不隔离**：它缓存的是"人"的身份，跨包复核（§1.1）兜住
> 不同老师学号不同的场景。

