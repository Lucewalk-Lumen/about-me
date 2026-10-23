# 02 · 库内容模型

## 1. 目录语义地图

| 路径 | 承载的知识 | 归属类别 |
|------|-----------|---------|
| `brain/` | 跨会话常驻知识（目标、决策、模式、坑、记忆主题索引、命令权威目录） | 用户内容（`brain/Skills.md` 例外，属基础设施） |
| `work/active/` | 当前项目（约定 1–3 篇；>1 篇的工作流放进 `work/active/<Topic>/`） | 用户内容 |
| `work/archive/YYYY/` | 已完工项目，按年份归档，镜像 `<Topic>/` 分组 | 用户内容 |
| `work/incidents/` | 事故文档（主笔记 + 复盘 + 深挖 + 后评估草稿） | 用户内容 |
| `work/1-1/` | 点时刻记录，命名 `<Person> YYYY-MM-DD.md` | 用户内容 |
| `work/meetings/` | **暂存收件箱**（原始导出），非存储；处理后询问是否删除 | 半用户内容（`README.md` 属基础设施） |
| `org/people/` | 每人一篇的原子人物笔记（图节点） | 用户内容 |
| `org/teams/` | 团队笔记（成员、范围、交互） | 用户内容 |
| `perf/brag/` | 季度战功详情，一篇一季 | 用户内容 |
| `perf/competencies/` | 原子能力笔记（链接目标 / 概念节点） | 用户内容（`README.md` 属基础设施） |
| `perf/evidence/` | 代码评审深扫与评审数据摘录 | 用户内容 |
| `perf/<cycle>/` | 评审周期简报（私有版 / 经理版 / 同伴版） | 用户内容（运行时创建） |
| `templates/` | 笔记模板（带元数据骨架） | 基础设施 |
| `bases/` | 查询视图定义 | 基础设施 |
| `thinking/` | **草稿暂存区**（非存储）；`session-logs/` 存压缩前备份 | 半用户内容 |
| `reference/` | 代码库知识、架构图、流程文档、运行手册 | 用户内容 |
| `memories/YYYY/MM/` | **跨仓记忆**（由别的仓库经服务协议写入） | 用户内容 + 记忆根 |

> ⚠️ **三个索引文件（工作索引、组织索引、战功索引）既不在基础设施清单也不在用户内容根里**，只出现在「脚手架」清单中；`work/meetings/` 与 `thinking/` 两个含用户内容的目录同样不在用户内容根里。由于服务暴露范围默认回落到用户内容根，这五个位置**默认不在服务暴露范围内**。

## 2. 笔记类型总表（20 种）

| # | 类型 | 路径模式 | 命名约定 | 关键元数据 | 归档 / 终结 |
|---|------|---------|---------|-----------|------------|
| 1 | 工作笔记（活跃） | `work/active/<Note>.md` 或 `<Topic>/*.md` | **裸标题，不加日期前缀** | `date` `description` `project` `status: active` `tags: [work-note]`（清单另要求 `quarter`） | 移到 `work/archive/YYYY/`，`status` 改 `completed` |
| 2 | 工作笔记（归档） | `work/archive/YYYY/[<Topic>/]<Note>.md` | 同上 | `status: completed` + `quarter` | 终态；名称含 `Archive` 的体积豁免 |
| 3 | 事故笔记 | `work/incidents/<Incident Name>.md` | 工单号或描述性标题 | `date` `quarter` `description` `project` `status` `ticket` `severity` `role` `tags: [work-note, incident]` | 随项目整体搬移 |
| 4 | 1:1 记录 | `work/1-1/<Person> YYYY-MM-DD.md` | **日期后缀**（点时刻） | ⚠️ **两套并存**：一套写 `status: completed`，另一套写 `person` 字段；清单要求 `date` + `quarter` | 点时刻记录，不归档 |
| 5 | 会议收件箱（原始） | `work/meetings/YYYY-MM-DD <Topic or Person>.md` | **日期前缀** | 无要求（暂存） | 处理后**询问后删除** |
| 6 | 决策记录 | `work/` | `Decision: <title>` | `date` `description` `status: proposed/accepted/deprecated` `tags: [decision]` | 收录进主题索引 + 工作索引的决策表 |
| 7 | 思考笔记 | `thinking/YYYY-MM-DD-descriptive-name.md` | 日期前缀 | `date` `description` `context` `tags: [thinking]` | **提升后删除**；推理过程本身有价值则保留并链到被提升的笔记 |
| 8 | 人物笔记 | `org/people/<Full Name>.md` | 全名裸标题 | `date` `title` `description` `team` `tags: [person]` | 长期图节点（接收反链） |
| 9 | 团队笔记 | `org/teams/<Team Name>.md` | 团队名 | `date` + `tags: [team]` | 长期图节点 |
| 10 | 能力笔记 | `perf/competencies/<Competency Name>.md` | 能力名裸标题 | `date` `description` `current-level` `target-level` `tags: [perf, competency]` | 概念节点，永久；**不手工维护证据列表** |
| 11 | 战功笔记 | `perf/brag/QN YYYY.md` | 季度名 | 五节结构：能力证据 / 影响与交付物 / 技术成长 / 协作 / 反馈 | 长期 |
| 12 | 评审简报 | `perf/<cycle>/<Cycle> Review Brief.md` | cycle 名 | 含叙事弧 / 影响 / 能力 / 文档线索 | 按 cycle 归档 |
| 13 | 评审证据 | `perf/evidence/<Person> PRs - <Period>.md` | 人 + 周期 | `person` `cycle` `date` `description` | 长期 |
| 14 | 评审草稿 | `thinking/review-drafts.md` 等 | — | 无 | 复制进评审工具后删除 |
| 15 | 主题笔记 | `brain/<Topic>.md` | 主题名 | `description` `tags: [brain]` | 常驻；由记忆主题索引引用 |
| 16 | 领域笔记 | 家族索引旁 `<Index> - <Domain>.md` | — | 继承 | **永不回并进索引** |
| 17 | 事件日志卫星 | 核心笔记旁 `<Core> — <Event> Log` | — | 继承 | 逐字搬移，核心笔记留一行索引 |
| 18 | 归档笔记 | 活笔记旁 `<Live Name> Archive[ — <window>]` | 名称含 Archive | 继承 | 体积豁免 |
| 19 | 跨仓记忆 | `memories/YYYY/MM/*.md` | 时间即路径 | `source: mcp-capture` `scope` `projects`/`platforms` `confidence` `origin` `date` `superseded_by` `promoted` | 加性提升进主题笔记（**复制，永不移动**） |
| 20 | 索引 / MOC | 入口页、工作索引、记忆索引、命令目录、组织索引、战功索引、各 README | 固定名 | `description` + `tags: [index]`（部分加 `moc`） | 常驻 |

## 3. 元数据 schema

| 类型键 | 必填字段 |
|--------|---------|
| `global` | `date`、`description`、`tags` |
| `work-note` | `date`、`status`、`quarter` |
| `incident` | `date`、`status`、`quarter`、`ticket`、`severity`、`role`（最严，6 个） |
| `person` | `date`、`title` |
| `team` | `date` |
| `1-1` | `date`、`quarter` |

> ⚠️ schema **未覆盖** `decision`、`competency`、`review`、`evidence`、`brain`、`thinking`、`memory` 七类实际存在的笔记类型。不要因为 schema 里没有就认为不需要字段。
>
> ⚠️ `global` 要求的 `date` 在多数脚手架笔记里缺失（入口页、记忆索引、决策索引、模式、坑、工作索引、组织索引、战功索引都没有；目标文档有字段但值为空）。

## 4. 标签与属性约定

- **类型标签**：`work-note`、`decision`、`perf`、`thinking`、`north-star`、`competency`、`person`、`team`、`brain`
- **索引标签**：`index`、`moc`
- **状态取值**：`active`、`completed`、`archived`、`proposed`、`accepted`、`deprecated`
- **查询属性**：`cycle`、`person`、`team`、`status`、`quarter`、`ticket`、`severity`、`role`
- 标签必须写在元数据里，**不使用行内标签**

## 5. 双链图

### 5.1 链接语法（5 种）

| 语法 | 含义 |
|------|------|
| `[[Note Title]]` | 标准链接，**按文件名跨目录解析** |
| `[[Note Title\|display text]]` | 别名链接 |
| `[[Note Title#Heading]]` | 深链到章节 |
| `![[Note Title]]` | 嵌入内容 |
| `[[Note Title#^block-id]]` | 链接到具体块 |

### 5.2 图角色（4 类）

| 角色 | 典型笔记 | 链接行为 |
|------|---------|---------|
| **证据节点** | 工作笔记、1:1 记录、评审证据 | 主动向概念节点发出链接 |
| **概念节点** | 能力笔记、模式 | 保持定义性，**证据靠反链到达，不手工维护列表** |
| **索引节点** | 各类索引 | 主动策展链接，承担导航 |
| **人物节点** | `org/people/` | 链向项目、团队、证据；从工作笔记接收反链 |

### 5.3 强制链接规则（9 条）

1. 工作笔记 ↔ 决策记录：**双向**
2. 工作笔记 → 能力笔记：写在 `## Related`
3. 工作笔记 → 团队
4. 工作笔记 → 人物（1:1 记录尤其）
5. 人物 → 评审证据
6. 战功索引 → 工作笔记：每条战功都链到证据
7. 记忆索引 → 来源：每条记忆链到它被学到的地方
8. 工作索引 → 全部工作笔记
9. 目标文档 → 当前焦点项目

### 5.4 硬断言

> 「**没有链接的笔记是 bug。**」「孤儿是 bug。」「每篇新笔记必须至少链到一篇既有笔记。」「优先双向链接。」「文件夹按用途分组，链接按含义分组。」

### 5.5 断链门禁

存在一份基线文件把**允许的坏链数固定为零**，形成棘轮：任何新增断链都会让门禁失败。

## 6. 查询视图（9 个）

共同骨架：顶层 `filters` → `formulas` → `properties` → `views`（每个视图可带 `filters` / `order` / `sort` / `groupBy` / `limit`）。**视图名是稳定接口**——入口页用嵌入语法引用它，改名会打断。

| 视图文件 | 选择器类型 | 过滤根 | 视图数 | 特殊点 |
|---------|-----------|--------|--------|--------|
| 1:1 历史 | 目录 | `work/1-1` | 1 | 无默认排序（叙述文档称「可按人排序」与实现不符） |
| 能力地图 | 标签 | `competency` | 1 | **唯一直接消费图结构**：证据数 = 反链数 |
| 事故总览 | 标签 | `incident` | 1 | 无排序；事故笔记同时出现在工作看板里（双标签） |
| 记忆浏览 | 属性 | `source == "mcp-capture"` | **5** | 唯一按置信度与取代状态做质量分层；唯一以运行时目录为数据源 |
| 人员目录 | 标签 | `person` | 2 | 按团队分组；用标签而非目录作选择器 |
| 最近动过 | 全库 | 全部 md（排除模板与草稿区） | 3 | **「最近动过什么」的权威答案**——按真实修改时间，**绝不按文件名日期** |
| 评审证据 | 目录 | `perf/evidence` | 2 | 按周期 / 按人分组 |
| 模板速查 | 目录 | `templates` | 1 | — |
| 工作看板 | 标签 | `work-note` | **4** | 从 `date` **推导**季度而非读 `quarter` 属性；含「活跃但 14 天未动」的陈旧检测 |

> ⚠️ **`quarter` 属性被清单列为必填，但 9 个视图里没有任何一个读取它**——工作看板改为从 `date` 推导。改字段前先确认谁真的在读。

## 7. 拆分语义（超大笔记）

- **阈值约 25 KB（字节，非行数）**——巨型单行条目会藏在低行数里
- **触发点**：写入时 + 会话边界
- **三种拆分产物**：
  - **领域笔记**：`<Index> - <Domain>`
  - **事件日志卫星**：`<Core> — <Event> Log`
  - **归档笔记**：`<Live Name> Archive[ — <window>]`
- **硬规则**：内容**逐字搬移**、原笔记留一行索引、重定向入站链接、**永不裁剪内容**、名称含 `Archive` 的豁免
- 拆分是**判断类**动作，由人工通道执行，不由确定性脚本执行

## 8. 索引维护规则

| 索引 | 索引什么 | 维护规则 |
|------|---------|---------|
| 入口页 | 库入口；嵌入 5 个查询视图 + 1 个段落 + 6 条快捷链接 | 模板脚手架；会话开始第一个读它 |
| 工作索引 | 全部工作笔记；含决策表与开放问题 | 创建或归档笔记时更新；审计会检查「活跃/归档目录里有没有没被索引链到的笔记」 |
| 记忆主题索引 | 记忆**主题**（不是具体记忆） | 新记忆写进对应主题笔记，**不写在这里**；只有新建主题笔记时才更新本索引 |
| 命令权威目录 | 命令 / 子代理 / 钩子 / 检索用法 / 服务工具表 / 工作流序列 | 面向**没有技能注入的宿主**；命令变化时必须同步（操作手册刻意不维护命令表） |
| 组织索引 | 角色与组织 / 团队 / 绩效回顾 / 经理时间线 / 人员 / 回顾目标 / 复现成长主题 | 组织知识变化时更新 |
| 战功索引 | 季度战功表 | 有战功时更新并链到证据 |
| 收件箱说明 | 路由表 + 命名约定 | 说明「这是暂存区不是存储」 |
| 能力目录说明 | 五步工作法 + 字段说明 | 明确「不要手工维护证据列表，让反链干活」 |
| 草稿区说明 | 草稿契约 + 「流向」链接约定 | 明确「结论落地后草稿删除」 |
