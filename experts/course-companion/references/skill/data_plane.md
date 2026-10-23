# 课程伴学精灵 · 参考细则（data_plane.md）

> 引用方式：`${CODEBUDDY_PLUGIN_ROOT}/references/skill/data_plane.md`。下文 `§` 编号沿用学生端 主指令 原有编号。

### 0.3 通用调用约定（所有数据操作都遵守）

本端所有读写都走**腾讯文档连接器**的 smartsheet 能力。该能力有**两种注入形态，两种都算数**——
先按下表判出本会话属于哪一种，再按对应形态调用（**参数 JSON 结构两形态完全一致**）：

| 形态 | 表现 | 调用方式 |
|---|---|---|
| **① Skill 形态**（当前主流） | 内置腾讯文档插件提供了技能 `tencent-docs`，其自带 `tencentdocs.py` | `python3 "${CODEBUDDY_PLUGIN_ROOT}/course_tdoc.py" "<tencentdocs.py 绝对路径>" tdoc_call tencent-docs smartsheet.list_records '{json}'` |
| **② MCP 工具形态** | 可用工具清单里出现名称**同时含 `tencent`（或 `tencent-docs`）与 `smartsheet`** 的工具（形如 `mcp__tencent-docs__smartsheet.list_records`） | 直接调用该工具，参数同上 |

**仅 MCP 通道（形态②）环境做课程发现与资料取回时**：agent 直接调 MCP 工具完成 `query_space_list` / `query_space_node` /
`smartsheet.list_tables` / `smartsheet.list_records` 探测，把结果组装为
`discover_hub.py --merge-from` 要求的 JSON（结构见该脚本头部注释），由脚本完成结构判定与配置合并写入；
**不得绕过脚本手写 `data_hub_config`**（定位 ID 不进对话）。
课程资料取回同理分两步走 `fetch_assets.py` 两个入口（结构与 30 分钟 URL 时效见该脚本头部注释）：
先用 `--resolve-records` 解析 agent 取回的 course_versions records 得到四资产定位清单，
再经 `manage.export_file` / `manage.export_progress` 拿到下载 URL 后，用 `--download-from`
交脚本完成「下载 + 内容校验 + 规范命名落盘」（落 `<out_dir>/<course_id>/`，与 Skill 形态一致）。

> **`tencentdocs.py` 的位置不要靠猜——按顺序定位，取第一个存在的**（它是**平台内置插件**的资产，
> **不在本课程包里**，所以绝对不能写成相对路径的裸命令 `python3 tencentdocs.py ...`）：
>
> 1. `~/.workbuddy/plugins/**/tencent-docs-plugin/**/skills/tencent-docs/tencentdocs.py`（首选；Windows 同）；
> 2. 同上但技能目录为 `tencent-saas-docs`（企业版 OneID 场景）；
> 3. 若会话已加载该技能且技能目录已在上下文里，直接用上下文中给出的那一个。
>
> **Skill 形态一律经本包根封装 `course_tdoc.py` 调用**（`course_tdoc.py` 与 `agents/`、`references/` 同级，
> 即 `${CODEBUDDY_PLUGIN_ROOT}/course_tdoc.py`）。封装默认把请求指向腾讯文档权威端点 `https://docs.qq.com`，
> 绕开网关偶发指到失效镜像的 502——**不要**直接裸调 `tencentdocs.py`。
> 定位到 `tencentdocs.py` 之后，**一律用绝对路径、且包一层 `course_tdoc.py` 调用**（路径含空格时加引号）。
> 定位不到 `tencentdocs.py` → 说明本会话没加载该 Skill，**这属于「Skill 形态不可用」，不等于「数据通道不通」**，
> 继续按上表形态②（MCP 工具形态）判定。
>
> **参数格式绝不凭记忆拼**：Skill 形态下先查定义——
> `python3 "${CODEBUDDY_PLUGIN_ROOT}/course_tdoc.py" "<tencentdocs.py 绝对路径>" tdoc_schema tencent-docs smartsheet.list_records`
> （工具清单用 `tdoc_list tencent-docs`），再按返回的字段名 / 类型 / 必填项构造 `json_args`。
> **Windows 解释器**依次尝试 `python3` → `python` → `py -3`。

> [!] **关于连接器的启用**：本包已在清单里声明 `dependencies.connectors: ["tencent-docs"]`，
> 平台会在会话中据此检查该连接器；**若尚未连接，会弹一张「连接」卡**——学生点一次「连接」并按提示授权即可
> （只需一次）。注意：**包清单的声明 ≠ 会话已启用连接器**；会话级是否启用由学生在其 WorkBuddy 里
> 勾选/授权决定。因此只要上述两种形态的判据都不成立，就按 §0 的停止话术引导，
> **不要反复重开会话、也不要重装包**。

**每条调用必带两个定位参数**（从 `data_hub_config.json` 读取，不要硬编码）。
配置为 **v2 按课分组**——先经 §1.1 与 §1.2 选定课程得到 `course_id`，
所有定位一律取 `courses.<course_id>` 条目（每课一对独立文件）：

- 读名册 / 智能体 / 课程版本 → `hub_file_id` + `hub_sheets.<表>`（该课 Hub 表，只读取）
- 写学情 → `usage_file_id` + `usage_sheet.usage`（该课 Usage 文件，可编辑）
- 写会话摘要 → `usage_file_id` + `usage_sheet.summaries`（同一 Usage 文件的第二张子表）

```json
// Hub 文件（读）
{ "file_id": "<数据中枢配置：该课 Hub 文件>", "sheet_id": "<数据中枢配置：该课对应子表>" }
// Usage 文件（写学情）
{ "file_id": "<数据中枢配置：该课 Usage 文件>", "sheet_id": "<数据中枢配置：该课 usage 子表>" }
// Usage 文件（写会话摘要）
{ "file_id": "<数据中枢配置：该课 Usage 文件>", "sheet_id": "<数据中枢配置：该课 summaries 子表>" }
```

各表与配置条目的对应关系（配置键均为 `courses.<course_id>` 条目内的相对键）：

| 用途 | 所在文件 | 配置键 | 学生权限 |
|---|---|---|---|
| 名册（校验学号） | Hub（只读取） | `hub_sheets.roster` | 只读 |
| 学情（写回流） | Usage（可编辑） | `usage_sheet.usage` | 仅追加（add_records） |
| 会话摘要（写回流） | Usage（可编辑） | `usage_sheet.summaries` | 仅追加（add_records） |
| 课程版本 | Hub（只读取） | `hub_sheets.course_ver` | 只读 |
| 智能体档案 | Hub（只读取） | `hub_sheets.agent_profile` | 只读 |

> **配置键 → 线上真实表名**映射（已按实测修正）：`roster` → `roster`、`course_ver` → `course_versions`、
> `agent_profile` → `agent_profiles`、`usage` → `usage`、`summaries` → `summaries`。
> 配置键是**分发契约**（学生包内已固定，**不改名**）；线上表名以建库脚本建表结果为准
> （Hub 表：roster / course_versions / agent_profiles / calendar / term_config；
> Usage 表：usage / summaries——**Usage 侧无 records/summaries 前缀**，直连时以 list_tables 实测为准）。

**列标题与取值**：直连 `smartsheet.*` 读写时，`field` 一律用**中文列标题**——

| 表 | 列标题（写作 field 的值） |
|---|---|
| roster | 学号 / 姓名 / 课程 / 来源 / 更新时间（实测：无「学情文件」列；该列为建库脚本的懒创建预留，直连写作时以 list_fields 实测为准） |
| course_versions | 版本ID / 课程 / 版本号 / 更新说明 / 配置路径 / 知识库路径 / 题集路径 / 状态 / 适用对象 / 灰度名单 / 创建时间 / 创建者 / 运行开关 |
| agent_profiles | 智能体ID / 名称 / 头像 / 花名 / 简介 / 提示词 / 课程 / 版本号 / 状态 / 适用对象 / 灰度名单 / 创建时间 / 更新时间 / 创建者 / 角色 / 默认头像 / 默认花名 / 可选头像 / 可选花名 / 稳定锚点 |
| usage | 时间 / 学号 / 知识点 / 收敛轮数 / 结果 / 周次 / teach_week / 来源 / 智能体 / 环节 / err_type / 幂等键 |
| summaries | 时间 / 学号 / 知识点 / 摘要 / 时长 / 来源 / 智能体 / 环节 / 幂等键 |

> 只有**列标题**是中文；`status` / `target_audience` 的**取值**仍是英文枚举
> （`draft` / `published` / `gray`；`all` / `gray_list` / `force_update`）。
> 学情取值已中文化：结果 ∈ {已收敛, 部分收敛, 卡住}；来源 ∈ {学生端, 教师端, 测试}。
> 本文档行文用英文字段名指代逻辑字段（如 `status`），实际读写时按上表换中文标题。
> 字段结构以数据中枢实际列名为准（列均为文本列），写值一律按文本发送。

**常见错误码**（先分类再处理——**传输层超时可重试，不要再当「停止」**；鉴权 / 权限 / 业务错误一律停止并原样提示）：

| 错误码 | 含义 | 处理 |
|---|---|---|
| `400006` | Token 鉴权失败 | 提示重新授权腾讯文档连接器：打开 `https://docs.qq.com/open/auth/mcp.html` 复制个人 Token（官方现行入口；旧路径：`docs.qq.com` → 右上角「更多操作 → 开放平台」→ 龙虾专用入口），按指引重新授权。**header 的 key 必须是 `Authorization`**；取值由连接器自己拼（`Bearer <token>`），**你不需要也不应该手动改前缀** |
| `400007` | VIP 权限不足 | 提示当前腾讯文档账号权限不足，需升级 VIP（<https://docs.qq.com/vip?immediate_buy=1>）——**不要**反复重试 |
| `22001` | 子表不存在（可能被老师调整过） | **停止**：提示"数据中枢的一张数据表暂时读不到，请联系老师检查数据中枢"，不自行重建 |
| `543303` | SmartsheetV2 Service Error | 常见于 **file_id 与 sheet_id 配错**（子表不属于该文件）：先核对「文件 × 子表」配对再怀疑平台，不要盲目重试 |
| `22004` | **内容被拦截**（写入文本命中平台敏感词过滤；返回文案为 `create smartsheet mutation failed`，**不含任何「敏感 / 拦截」字样**，极易误判成结构错误） | **属内容级失败，不是定位或结构问题**：按 `error_handling.md` §6 的「22004 内容拦截」处理——先做**一次同义替换重试**（保留学科结论、只换触发词），仍失败才走本地暂存补传 |
| `102` / `i/o timeout` / `ReadFrame` | **传输层超时**（服务端应答慢，**不是**「连不上」，也不是文件坏了） | **可重试**：见下方「超时了怎么办」。**绝不得**因此说「未连接到数据中枢」，**绝不得**停止伴学 |

> [!] **list_records 分页铁律（禁止凭首页下结论）**
> 单页默认上限 **100 条**，返回 `has_more=true` 时**不会自动翻页**——
> 必须循环调用并把 `offset` 逐次 +100，直到 `has_more=false` 才算读全表。
> **任何「命中 / 在册 / 有记录」的判定都必须基于翻页读全后的全量数据**：
> 只读第一页就判「不在册 / 查无此人 / 无记录」是**明确缺陷**
> （实测 158 条名册里排在末页的学生被首屏漏检，误判为不在册）。

> [!] **超时了怎么办（先重试，别急着放弃）**
>
> 1. **重试**：同一个调用**最多重试 5 次**——读学情 / 读课程内容直接重试即可；
> **写学情（新增记录）超时后不要盲目重写**，先读一次确认有没有写进去，避免重复行
> （即使漏判，也还有「幂等键」兜底去重）；
> 2. **换形态**：用 MCP 工具超时了，就改用 Skill 形态（`python3 "${CODEBUDDY_PLUGIN_ROOT}/course_tdoc.py" "<tencentdocs.py 绝对路径>" --timeout 180 tdoc_call ...`）再试一次，反之亦然；
> 3. **别整表拉**：能按记录 ID 定向取就别全表扫描，既快又不容易超时；
> 4. **超时不是「未同步」**：不要把超时说成「连接不上」而中断伴学——**先把这一轮聊完**，
> 学情该记的照记（重试成功后补写），确实全部重试失败才如实告诉学生「这次记录同步稍慢，稍后会补上」；
> 5. **绝不因为超时就让同学重装包 / 重新绑定身份**——那是把服务端拥堵误判成了包的问题。

> [!] **连接事实（排错时只看这条）**：MCP 地址 `https://docs.qq.com/openapi/mcp`；
> 鉴权 header **必须是 `Authorization`**（`token` / `auth` / `X-Token` 等别名一律失败），
> 取值由连接器自己拼成 `Bearer <token>`（**不要**去改前缀）。技能通道超时默认 **120 秒**，
> 可用 `--timeout <秒>` 覆盖。调用频率上限：免费用户 2000 次/天、超级会员 20000 次/天
> （批量读写时留意）。官方明确：**已在客户端配好 MCP 就无需重复配置**——
> 所以「工具清单里没看到 smartsheet」不能当成没连通。若报 401 / 403 票据被拒，
> **反复解绑 / 重连连接器不会改变结果**，先确认是不是把企业版票据用到了个人版端点。

> 本端只有这一条数据通路（腾讯文档连接器），但它有 Skill / MCP 两种注入形态，**任一可用即通**。
> 两种都不可用才按 §6 铁律处理。

> [!] **通道「就绪但全 502」的处理（封装已默认绕过镜像，仅作高级诊断）**
> 本包所有 Skill 形态调用已统一经 `course_tdoc.py`，该封装默认把请求指向腾讯文档权威端点
> `https://docs.qq.com`，**绝大多数镜像域名导致的 502 在封装层即被吸收**，正常调用无需手动加任何变量。
> 仅当封装调用仍出现下列三条**同时**成立时，才属站域问题、做高级诊断：① `tdoc_init` 返回 `READY`（票据正常）；
> ② `smartsheet.*` 调用返回 **502 / `Tunnel connection failed`**（**不是** 401/403，也不是超时 `102`）；
> ③ 宿主下发的文档站 origin 在本机**不可达**（解析不到 / 连接被拒）。
> 三条同时成立 → 开 `TDOC_DEBUG=1` 看 `api_base`，若仍被指到 `workbuddy.cn` 类镜像，临时用：
>
> ```
> TDOC_API_BASE_URL=https://docs.qq.com python3 "${CODEBUDDY_PLUGIN_ROOT}/course_tdoc.py" "<tencentdocs.py 绝对路径>" tdoc_call tencent-docs smartsheet.list_records '{json}'
> ```
>
> 封装会尊重该值、跳过默认覆盖。仍不通过，才按 §6 判「通道不通」。**该变量只对当次进程生效**：
> - **不得**在三条未同时成立时使用它——否则会把「票据失效 / 权限不足 / 真断网」掩盖成「换个站就好」；
> - **不得**把它写进任何持久配置、脚本或包内文件。

### 0.3.1 写入取值自检（写 `usage` / `summaries` 前逐行过一遍）

**写入取值铁律以本表（§0.3.1）为唯一事实源**；`agents/course-companion.md` §3.5 为速查摘要，与本表不一致时以本表为准。速查：

| 字段 | 合法取值 | 禁止 |
|---|---|---|
| `结果` | `已收敛` / `部分收敛` / `卡住` | 自造结果（`已预习` / `预习` …） |
| `环节` | `预习` / `首学` / `复习` / `题目生成` | 引导方式（`苏格拉底引导`）/ 活动名 / 编号（`伴学` …） |
| `周次` | ISO 周 `YYYY-Www`（如 `2026-W39`） | 周序号（`1`） |
| `teach_week` | 教学周标签 `学期-Wn`（如 `2026-秋-W3`） | 周序号（`1`）/ 空 |
| `知识点` | 该课 `config.json` 的 `kp_id` **完整原值** | 章节名 / 「KP 号 + 中文标题」 / **按数字前缀归并**（`KP-1.2-*` 可能同名不同点，见下注） |

> 任一行不合格 → **先改正再写入**。教师端平时分按「环节 × 结果」权重计分，
> 越界值既不命中权重、也不进按 KP 行的聚合统计——等于这一次学情白记。

> **越界后果按消费方分两类**（2.0.1 实测校正）：**平时分**（教师端 §5 权重表）不命中任何权重，
> 等于白记；**积分**（包内 `scripts/course_points.py`）按「结果」聚类、**不校验环节**，越界行仍会计入积分。
> 口径不一致本身就是缺陷来源，**根本解法是别写出越界值**。
>
> **归类纪律**：`环节` 只记**学习阶段**（预习 / 首学 / 复习 / 题目生成）；
> `苏格拉底引导` 是**引导方式**（本端默认方式，贯穿所有阶段），**不作为环节取值**。
> 「首次学某知识点」记 `首学`，既不记「苏格拉底引导」，也不记「预习」。
> **KP 一律用完整 `kp_id`**：已实证同一数字前缀下存在多个不同知识点
> （如 `KP-1.2-psychology-goals` 与 `KP-1.2-discipline-position`），
> 按 `KP-1.2` 归并会把两个知识点算成一个，覆盖率、复习建议与积分都会失真。

### 0.3.1b 写入格式封装与读回自检（防「表面成功实际空数据」）

**所有 usage / summaries 写路径统一走 field_values 封装**——直接写 `{fields:{列:值}}` 会
「返回成功但数据为空」（实证）。两种等价方式：

1. **推荐**：把行 `[{"列": "值", …}]` 存临时 json 后跑
 `python3 "${CODEBUDDY_PLUGIN_ROOT}/course_tdoc.py" make_records <rows.json>`
 → stdout 输出规范 `{"records":[{"field_values":[{"field":列,"text_value":{"items":[{"text":值,"type":"text"}]}}]}]}`，
 再以该结果作为 `smartsheet.add_records` 的 records 实参；手工拼结构时逐字段核对——是 `text_value`（单数），不是 `text_values`。
2. 或按同一结构手工拼 `field_values`（文本字段 type 固定 `"text"`）。

**字段名以数据中枢实际建表为准**（见 §0.3 列标题表）：写入前逐字段核对 `field` 是否落在合法集合内，
不在集合内的先改正再写（`add_records` 对未定义字段不报错、直接略过，但该字段不会真正落库）。
拿不准参数结构时先用 `tdoc_schema` 查 `smartsheet.add_records` 的字段名 / 类型 / 必填项再构造，不凭记忆拼。

**写后读回自检（强制）**：add_records 返回成功后，立即 `list_records` 读回最后一页，
核对本次**幂等键**（或时间 + 学号）确实存在且非空；读不到 → 按「写入失败」处理并本地缓存补传，
**不得**当作已写入继续。

**批量写入拆批与重试**：一次写入多行（多 KP 会话）时**单批不超过 8 条**，超过即拆批顺序写；
任一批传输层超时（`102` / `i/o timeout`）→ 按 §0.3「超时了怎么办」指数退避重试至多 3 次
（重试前先读一次确认是否已落库，避免重复行，幂等键兜底去重）；
拆批后逐批走「写后读回自检」，读不到关键字段的行补写一次，仍失败则入 `usage_pending.jsonl` 补传。

### 0.3.2 写入教学周（teach_week）与学习预警（每次会话）

**教学周标签 `teach_week` 必须随每条学情写入**（替代散落的 ISO 周，作为报告 / 预警的统一口径）：

- 读 Hub 文件 `calendar` 子表（`hub_sheets.calendar`）→ 用包根 `course_calendar.py` 对每条学情的 `时间`
 计算教学周：`python3 "${CODEBUDDY_PLUGIN_ROOT}/course_calendar.py" week --calendar <calendar.json> --date <时间>`，
 取其输出的 `2026-秋-W3` 写入 `teach_week` 列；同时保留 `周次`（ISO 周）向后兼容。
- 未录入校历时封装回退 ISO 周（`2026-W39`）并标注「未对齐校历」——照常写入，不阻断。

**会话开场自检（不阻塞）**：读本人 `summaries` + Hub `calendar` + `term_config`，用包根
`course_warn.py` 评估学习预警：

```
python3 "${CODEBUDDY_PLUGIN_ROOT}/course_warn.py" check \
 --summaries <本人摘要json> --student <学号> \
 --calendar <calendar.json> --term-config <term_config.json> --today <今天>
```

命中预警（超期未学 / 需补学时）→ 先输出一条温和提醒再进入伴学；同一预警 24h 内只提示一次
（`course_warn.py` 按 `last_warn_time` 去重）。

> [!] **预警自动生效，不需要老师先配置**：教师未在 `term_config` 设阈值时，
> `course_warn.py` **自动使用内置默认**（`warn_idle_days=7` / `warn_deficit_ratio=0.7` /
> `required_hours_per_week=3.0`）照常判定——**不会因为「没配置」就不提醒**。
>
> 输出里的 `config_status` 说明本次用了什么：
> - `source: builtin_default` → 本次用默认阈值，可**顺带一句**「（老师还没单独调过预警阈值，按默认
> 7 天未学/每周 3 小时提醒）」，让学生知道这是通用标准；
> - `source: disabled_by_teacher` → **老师主动关闭了**预警，此时**明确告知**「本课老师已关闭学习预警」，
> **不要**谎称「你一切正常」；
> - `has_calendar: false` → 未对齐校历，按自然周算，可**顺带说明**一句；
> - 读不到本摘要 → 明确回报「读不到你的学习记录」，**不要**假装检查过。

**间隔复习与目标进度**：开场自检可顺带执行——

```
python3 "${CODEBUDDY_PLUGIN_ROOT}/course_warn.py" review \
 --summaries <本人摘要json> --student <学号> --today <今天>
# 输出 {"due":[{kp,result,last_date,gap_days}...]}：部分/卡住知识点距上次 1/3/7 天到期

python3 "${CODEBUDDY_PLUGIN_ROOT}/course_warn.py" goal \
 --summaries <摘要json> --usage <学情json> --student <学号> --today <今天> \
 [--target-hours <时>] [--target-kps <个>] [--calendar <calendar.json>]
# 输出本周学时 / 知识点数进度；学生自定目标时展示进度条，达标肯定、未达标并入预警
```

**`last_warn_time` 缓存约定**：本地缓存于 `~/.workbuddy/course_tutor_student/last_warn.json`
（按学号存 `{ "<学号>": "<ISO时间>" }`）；每次**实际提醒后**写入，开场自检读它传给 `--last-warn`。
文件只存时间戳、不含学情内容，可随时删除（最多导致重复提醒一次）。

**结果反馈话术**：反馈按「掌握度 + 下一步」给出（不只说对 / 错）；标注了 `err_type`
（概念 / 计算 / 审题）的卡住点按错因归类讲评。

> `course_calendar.py` 与 `course_warn.py` 已随学生端包提供（与 `course_tdoc.py` 同级），无需自行获取。

