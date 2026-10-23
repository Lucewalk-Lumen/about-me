# Stage 6 细则（资产持久化与晋升）

> 本文件是 `agents/distill.md` 的**分片正文**，**按需读取**，不要在一开始就读。
> 何时读：用户要求导出 / 恢复 / 分发 / 晋升，或需要 Stage 6 的触发词、执行步骤、
> 前置检查、安全护栏、错误场景、字段映射表时。
>
> 路径解析：以平台注入块给出的 `Expert plugin path:` 为基点拼出绝对路径后直接读取。
>
> 主文件（`agents/distill.md`）里的 Stage 6 摘要与触发词是入口，本文件是细则全文。

---

### Stage 6.1 · EXPORT 导出

#### 触发词
- 「导出蒸馏资产」 / 「备份胶囊」 / 「把胶囊导出」 / 「打包资产库」
- 提示：若「跑一下蒸馏」时顶部出现「备份提醒：」，回复「导出蒸馏资产」即可触发本段

#### 执行步骤
1. **打包**：跑 `bin/export_backup.py`（仅用 Python 标准库，Windows 无 `zip` 命令也能用）。归档顶层固定为 `distill-assets/`（restore_backup.py 依赖读取 `distill-assets/capsules/capsules.json` 并解压该子树），zip **输出到备份目录** `~/Documents/distill-backup/`（与 RESTORE / SHARE 默认读取目录一致，避免"导出即失效"目录错位）：

   ```bash
   python3 bin/export_backup.py            # 默认输出到 ~/Documents/distill-backup/
   python3 bin/export_backup.py --out-dir <目录>   # 用户指定其他备份目录时
   python3 bin/export_backup.py --dry-run  # 只列将打包的内容
   ```

   不把内部散文件打平。版本备份 `配置目录/distill-versions/` 与计数器 `.counter` 位于资产库**之外**，归档只收 `distill-assets/` 子树，因此它们**天然不进备份**（脚本另会跳过临时文件），使文档「不导出」声明与实现一致。若用户指令指定了其他备份目录，则输出到该目录并相应调整 RESTORE 的 `--backup-dir`。
2. **git 提交（可选）**：若备份目录是 git 仓库，自动 `git add -A && git commit -m "导出：N capsules, M events"`
3. **审计链**：`events.jsonl` 追加 `type=export` 事件，记录导出时间、目标目录、zip 大小、SHA-256
4. **回报**：告知用户导出位置、文件数、压缩后大小

> **命名约定**：zip 文件名只用 `backup-` 前缀 + 时间戳（如 `backup-20260804-123305.zip`），不另存 latest 副本——`backup-` 前缀已表明是备份，时间戳最新的就是最新；多一个 `latest` 副本与 git 最新 commit 等价，冗余。

### Stage 6.2 · RESTORE 恢复（agent 触发式）

> 设计哲学：恢复是 EXPORT 的对偶，由用户口头指令触发，agent 完成全部脏活（找最新 zip、解压、验证、复制、写审计）。**用户不需要记任何命令**。

#### 触发词
- 「恢复蒸馏资产」 / 「恢复胶囊」 / 「还原资产」 / 「从备份恢复」

#### 前置检查（必须全过）
1. **备份目录存在**：`~/Documents/distill-backup/`（或用户在指令中指定的目录）—— 不存在则报错「未找到备份目录，请先 EXPORT」
2. **找到 backup-*.zip**：列出该目录所有 `backup-*.zip`，取时间戳最新的—— 不存在则报错「未找到任何 backup zip，请先 EXPORT」
3. **目标目录可写**：`~/.workbuddy/distill-assets/`（或对应宿主路径）—— 不可写则报错
4. **目标目录当前状态**：若已存在 `capsules/capsules.json`，**必须显式询问**用户「当前已有 N 条胶囊，是否覆盖？」，绝不允许静默覆盖

#### 执行步骤
1. **声明计划**：告知用户即将恢复哪个 zip（路径 + 时间戳 + 大小 + 包含 N 条胶囊）
2. **等待确认**（若目标已存在）：用户答「是 / 覆盖 / 确认」才继续
3. **备份当前**：把 `~/.workbuddy/distill-assets/` 当前内容复制到 `~/.workbuddy/distill-assets.pre-restore-YYYYMMDD-HHMMSS/`（以防回滚）
4. **解压**：用 Python `zipfile` 解 `backup-*.zip` 到系统临时目录（`tempfile.mkdtemp()`，跨平台自动解析为 `%TEMP%`/`/tmp` 等，勿硬编码 `/tmp`）
5. **复制**：把临时目录里的 `distill-assets/*` 复制到 `~/.workbuddy/distill-assets/`（不含 `distill-versions/`，避免恢复出嵌套备份）
6. **验证**：对比恢复后的 `capsules/capsules.json` 数量与 zip 内声明的 N 是否一致
7. **审计链**：追加 `type=restore` 事件，记录源 zip、目标路径、capsules 数量、actor
8. **回报**：告知用户恢复结果（X 条胶囊已就位） + 建议立即跑一次蒸馏触发首次双轮对齐基线

#### 安全护栏
- **不可逆操作前必问**：覆盖已有胶囊库是"全或无"操作，必须显式确认
- **回滚机制**：先备份当前到 `.pre-restore-XXX/`，出问题时 `cp -r` 回去即可
- **不写回 .git**：RESTORE 不动 backup 仓库的 git 历史（git 是只读消费者，只接受 EXPORT 写入）
- **恢复后不立即跑 Stage 0 守卫**：避免"刚恢复又被提醒备份"循环

#### 错误场景
| 情况 | 行为 |
|---|---|
| 备份目录不存在 | 报错 + 建议「先 EXPORT」 |
| 无 backup-*.zip | 报错 + 建议「先 EXPORT」 |
| zip 解压失败（损坏） | 报错 + 保留 `.pre-restore-XXX/` 备份不动 |
| 验证失败（capsules 数量不一致） | 报错 + 保留 `.pre-restore-XXX/` + 不写入审计链 |
| 用户拒绝确认 | 取消 + 不写入审计链 |

### Stage 6.3 · SHARE 分发（给别人用的胶囊包）

> 与 EXPORT（个人备份）和 RESTORE（个人恢复）不同，SHARE 产出**可移植的胶囊包**——把胶囊给别人用，或换到新环境用。**默认净化**：去掉个人操作记录。

#### 触发词
- 「打包胶囊分发」 / 「分享胶囊」 / 「导出 capsule pack」 / 「生成胶囊包」
- 加 `原状打包` / `含审计链` → 走非净化版（与 backup-*.zip 等价）

#### 与 EXPORT 的区别

| 维度 | EXPORT (本地备份) | SHARE (分发包) |
|---|---|---|
| 目标用户 | 自己 | 别人 / 另一台机器 |
| 落点 | `~/Documents/distill-backup/backup-*.zip` | `~/Documents/distill-backup/capsule-pack-*.zip` |
| 文件名 | `backup-YYYYMMDD-HHMMSS.zip` | `capsule-pack-YYYYMMDD-HHMMSS.zip`（原状版带 `-含个人数据` 后缀：`capsule-pack-20260804-130211-含个人数据.zip`） |
| 默认净化 | 是（不含 events/genes/rejected） | **是**（更严格，不含 events/genes/rejected） |
| 接收方用法 | 仅自己恢复 | 解压复制到对方 `~/.workbuddy/distill-assets/` |
| 审计链记录 | `type=export` | `type=share` |

#### 默认净化：包含什么 / 不含什么

**包含**（接收方需要的）：
- `capsules/capsules.json` — N 条胶囊主库（N = 当前资产库胶囊数）
- `capsules/index.md` — 检索索引（SHARE 快照；权威索引在 `distill-assets/index.md`。此快照由净化后的胶囊**现场重新生成**，不复制源索引；带「出处」列，接收方一眼看到资产来自谁）
- `README.md` — 接收方使用说明（自动生成，含来源、用法、引用方式）

**不包含**（个人操作记录，净化掉）：
- `events.jsonl` — 个人操作审计链（SHA-256 链含个人时间戳，不应外传）
- `genes.json` — 个人操作模式库（可能含个人习惯）
- `rejected.json` — 被拒候选（含个人判断上下文）
- `distill-versions/` — 写前版本备份（个人用途）
- `.counter` — 内部计数器

**接收方补齐**：自己的 `events.jsonl` / `genes.json` / `rejected.json` 在第一次跑蒸馏时会自动重建（如果不存在就当空库起步），无副作用。

#### 执行步骤
1. **净化打包**：把 `配置目录/distill-assets/capsules/capsules.json` 与**现场生成的** `capsules/index.md` 打包成 `capsule-pack-YYYYMMDD-HHMMSS.zip`（不复制源索引，避免索引里的指针随包外传）
2. **自动生成 README.md**（接收方说明）：含来源（Xing Bu）、日期、capsule 数、接收方安装 3 步指引
3. **不写 git 提交**：分发包不污染备份仓库的 git 历史（除非用户说「同步到 git」才提交）
4. **审计链**：`events.jsonl` 追加 `type=share` 事件，记录分发包路径、capsule 数、是否净化版
5. **回报**：告知用户分发包位置、含 N 条胶囊、净化状态

#### 接收方使用（写在自动生成的 README.md 里）

```bash
# 1) 装 distill 专家包
# 2) 解压 capsule-pack-YYYYMMDD-HHMMSS.zip 到临时目录
#    （跨平台：Windows 用 PowerShell Expand-Archive；macOS/Linux 用 unzip -d /tmp/capsules-in）
#    PowerShell: Expand-Archive capsule-pack-20260804-130211.zip -DestinationPath $env:TEMP\capsules-in
#    macOS/Linux: unzip capsule-pack-20260804-130211.zip -d /tmp/capsules-in
# 3) 复制到自己的资产库（首次跑蒸馏前）
mkdir -p ~/.workbuddy/distill-assets/capsules
cp /tmp/capsules-in/capsules/capsules.json ~/.workbuddy/distill-assets/capsules/
cp /tmp/capsules-in/capsules/index.md ~/.workbuddy/distill-assets/capsules/
#    （Windows 等价：copy $env:TEMP\capsules-in\capsules\capsules.json $HOME\.workbuddy\distill-assets\capsules\ 等）
# 4) 首次运行检测到已有 capsules（无 .first_run 哨兵但胶囊库非空），跳过历史补齐，直接进入日常
```

#### 加 `原状打包` / `含审计链` 指令

用户说「含审计链打包胶囊分发」→ 跳过净化，走与 EXPORT 等价的全量打包（**文件名加 `-含个人数据` 后缀**：`capsule-pack-20260804-130211-含个人数据.zip`，与本段 §6.3 命名约定表一致），方便接收方一眼区分净化版与原状版。

#### 命名 vs EXPORT 的边界

- **`backup-*.zip`**：个人本地备份，**永远不全给**
- **`capsule-pack-*.zip`**：分发包，**永远可以给**

这两个 zip 类别**不能混用**——文件名就是防火墙。误把 `backup-*.zip` 发给同事会泄露个人审计链，误把 `capsule-pack-*.zip` 用作自己恢复会缺失审计链。

### Stage 6.4 · PROMOTE 晋升为技能（单向，可选）

> 蒸馏资产（capsule）是"知识体"；WorkBuddy 技能（SKILL.md）是"可经 Skill 工具加载的动作体"。二者同源：capsule 是单一事实源，技能是其**可加载投影**。**单向**：capsule → SKILL.md，不反向改写 capsule。

#### 触发词
- 「把这个 capsule 晋升成技能」 / 「转成 SKILL.md」 / 「晋升：<capsule id>」

#### 晋升条件（满足其一）
- 该流程被判定"需被机器自动执行"：高价值 / ≥2 次复用 / 用户明示"以后都这样"且动作可机械化（无需要人工判断的模糊分支）。
- 不满足则保持 capsule 文本，不晋升——避免技能泛滥。

#### 固定字段映射（capsule → SKILL.md）
| capsule 段 | SKILL.md 字段 | 规则 |
|---|---|---|
| `id` | 技能目录名 / `name` | kebab-case，作为 `~/.workbuddy/skills/<name>/` 目录名 |
| `R` | `description`（首句） | 精炼原文定位，保留 source 引用 |
| `A2` | 触发条件 / 触发词 | 情境 + 语言信号（≥3 用户原话示例） |
| `E` | 步骤正文 | 每步保留"完成标准："，祈使语气，≤7 步 |
| `B` | "何时不用 / 边界"段 | 原样迁移，作为技能的使用护栏 |
| `src` | 顶部 `src_capsule` 注记 | 回指来源 capsule id，保持溯源链 |

#### 落点与护栏
- 落点：`~/.workbuddy/skills/<name>/SKILL.md`（用户级）或 `<workspace>/.workbuddy/skills/<name>/`（项目级）。
- **危险命令门控保留**：E 段含 `rm -rf` / `curl 管道接 sh` / `eval` 等 → 技能内显式保留"复用需人工确认"提示，**绝不自动执行**。
- **互链**：SKILL.md 顶部注明 `src_capsule: <id>`；蒸馏 `index.md` 同步回链该 SKILL.md 路径。
- **不破坏只读红线**：PROMOTE 仅由用户显式指令触发（"晋升..."），蒸馏运行时**绝不自发**改写技能文件；技能文件亦不回写蒸馏资产。
- **审计**：`events.jsonl` 追加 `type=promote` 事件，记录 capsule id → skill 路径，纳入防篡改链。

### 不导出（设计权衡）
- **版本备份目录 `配置目录/distill-versions/`**：写前版本化备份是日常蒸馏的产物，对**个人用户备份场景无价值**——git 历史 + 最新 zip 已能完整恢复，旧版本还原靠 `git checkout` 而不是靠 vN 目录，且体积占比极高。该目录位于资产库之外，因此**不会**进入任何备份或分发件。
- 临时文件：`.DS_Store` / `__pycache__/` / `*.pyc` / `*.swp` / `*~`
- 本专家包自身（plugin.json / agents/*.md / README 等）：属宿主应用文件，不属用户资产
