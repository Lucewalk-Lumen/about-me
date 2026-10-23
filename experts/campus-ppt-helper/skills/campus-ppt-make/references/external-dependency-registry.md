# 外部依赖连接登记（External Dependency Registry）

> 面向主理人 + 制作员 + 质检员。**本表是"引用"与"连接"的分界线**：文档里写了某个外部技能 / 工具 / 资料库的名字，只算**引用**；只有在本表登记了「真实位置 + 可执行预检 + 判读口径 + 缺失降级」四项，才算**已建立连接**。
> 表内"连通核验"列记录各项依赖的连接核验结论，**不含推断**。换机器后须按 §二 各卡片的预检命令重测，不得沿用旧结论。

## 〇、为什么要有这张表

本团正文共有 **349 处**指向包外的引用（1.0.0 发布前清点，覆盖官方技能及其内文件、外部 CLI 与伴生脚本、模板库、外部 URL 与包外路径四类；分项计数为登记时点快照，非实时计数）。逐项核验后发现：

- **只有 `browser-skill` 一项建立了完整连接**（有预检命令、有判读口径、有降级）；
- 其余外部依赖多数只写了名字，**没有可执行的预检命令**，成员在运行时无法判断"它到底在不在"；
- **模板库在本机根本不存在**（`$HOME/campus-ppt-templates` 未创建、`CAMPUS_PPT_TEMPLATE_DIR` 未设置），而正文有 79 处引用它——**引用悬空 = 路径 B 模板保真链路彼时跑不通**（1.0.0 起已切换腾讯文档源、链路已通，此为登记时点结论），且没有任何一处文档会主动提醒。

本表把这三项缺口补上，并交由发布前静态门禁 C8 常态检查（见本表 §五）。

## 一、外部依赖总表

| # | 依赖 | 类型 | 真实位置 | 预检 | 连通核验 | 缺失降级 |
|---|---|---|---|---|---|---|
| 1 | `tencent-pptx` | 官方技能（风格重绘 + 视觉设计系统） | 市场缓存 `$HOME/.workbuddy/plugins/cache/workbuddy-builtin/tencent-pptx/<版本>/skills/tencent-pptx` | `ls -d` 该目录 | **在** · v5.6.2 · references 22 份 | 改走 WPS / 本地 Office，并**如实告知未继承模板视觉** |
| 2 | `tencent-local-office-edit` | 官方技能（模板保真 editor_sdk） | **App 内置** `<WorkBuddy.app>/Contents/Resources/app.asar.unpacked/resources/plugins/workbuddy-builtin/skills/tencent-local-office-edit` | `python3 <该目录>/edsdk.py list` | **在**（随 App 分发，非市场安装） | 退回路径 A，并**如实告知"未继承模板视觉"** |
| 3 | `browser-skill` | 官方技能（采集） | 用户级 `$HOME/.workbuddy/skills/browser-skill` | `BSK_AUTO_START=0 bsk status --json` | **在** · v1.0.5 · `bsk` 0.3.2 | 四级降级，见 `browser-skill-integration.md §五` |
| 4 | `story-principle.md` | 官方设计文件（版式骨架） | `tencent-pptx/references/story-principle.md` | 见 §二 卡 1 | **在** · 13,023 B | 无此文件则**不得声称已调用视觉美化**，判 FAIL |
| 5 | `design-principle.md` | 官方设计文件（三区母版） | `tencent-pptx/references/design-principle.md` | 见 §二 卡 1 | **在** · 16,028 B | 同上 |
| 6 | `create-from-scratch.md` | 官方设计文件（生成流程） | `tencent-pptx/references/create-from-scratch.md` | 见 §二 卡 1 | **在** · 10,462 B | 同上 |
| 7 | `create-from-material.md` | 官方设计文件（读图提风格） | `tencent-pptx/references/create-from-material.md` | 见 §二 卡 1 | **在** · 1,839 B | 同上 |
| 8 | `designs/design-principle.academic.md` | 设计分支（学术） | `tencent-pptx/references/designs/` 下 | 见 §二 卡 1 | **在** · 9,062 B | 回落 universal-only，并**在 `DESIGN.md` 标注未命中分支** |
| 9 | `designs/design-principle.consulting.md` | 设计分支（职场咨询） | 同上 | 见 §二 卡 1 | **在** · 15,997 B | 同上 |
| 10 | `designs/design-principle.redgold.md` | 设计分支（红金政务） | 同上 | 见 §二 卡 1 | **在** · 10,058 B | 同上 |
| 11 | `bsk` | 外部 CLI（采集会话） | `$HOME/.local/bin/bsk` | `command -v bsk` | **在** · 0.3.2 | 同 #3 |
| 12 | `slidep` | 外部 CLI（保真出图） | `$HOME/.workbuddy/binaries/node/versions/<ver>/bin/slidep` | `command -v slidep` | **在** · 子命令 `create`/`upsert-dsl`/`validate`/`screenshot`/`lint` | 改用 `Spire.Presentation` 离线渲染；**两者都无则"逐页目视"无法完成，须标"未验证"** |
| 13 | `edsdk.py` | 官方技能内脚本（editor_sdk 客户端） | 随 #2 同目录 | 见 §二 卡 2 | **在** | 无 #2 即无路径 B |
| 14 | `pptx2image.py` | 官方技能内脚本（模板转图） | `tencent-pptx/scripts/pptx2image.py` | `command -v soffice` | **脚本在，但 LibreOffice 未安装 → 实际不可用** | **不得作为主路径**；改用直读 `theme1.xml` 取色（`template-application.md` 方案 B）或 `slidep`（方案 C） |
| 15 | `Spire.Presentation` | 外部渲染库（离线兜底） | 需自行 `pip install` | `python3 -c "import spire"` | **未安装** | 同 #12 |
| 16 | 腾讯文档「演示模板库」 | 配套资源（15 套模板，**唯一运行时模板源，1.0.0 起；1.0.1 起 15 套全量**） | docs.qq.com，`tencentslide` 在线幻灯片 15 套；云端权威清单与内嵌 file_id 见 `templates/gdufe-template-manifest.json` 与 `tencent-docs-template-source.md §二`（**文件名即权威**） | 见 §二 卡 4（四级取件） | **已连接** · 15/15 可枚举 · 直导与克隆导出下载均实测通过（2026-10-07 直导 / 2026-10-08 克隆） | 按 `tencent-docs-template-source.md §四` 四级降级（缓存 → 直导 → 克隆 → 人工另存），四级全败**暂停并回主理人**，不得臆造路径 |
| 17 | `tencentdocs.py` | 官方技能内脚本（腾讯文档 MCP 客户端） | 市场缓存 `$HOME/.workbuddy/plugins/cache/workbuddy-builtin/tencent-docs-plugin/<版本>/skills/tencent-docs/tencentdocs.py`（本机实测在 5.6.2 / 5.7.6 两个版本目录下均存在；多版本时取最新） | `python3 tencentdocs.py tdoc_init` | **READY**（票据由宿主 WorkBuddy 注入，不落盘） | 返回 `ERROR:no_token` / 报 400006 → 请用户重连连接器，暂停出片 |
| 18 | `~/campus-ppt-cache/` | 本地缓存（导出落盘消费点，非事实源） | 调用方 `mkdir -p` 创建 | `test -d ~/campus-ppt-cache` | 可自动创建 | 缺文件 → 重新走导出下载，不臆造路径 |
| 19 | `ai-writing` | 外部技能（**方法论来源**，非运行时依赖） | 用户提供的包 `ai-writing-1.0.1.zip`（罗斯蒙德智能写作与文档交付）；**2026-10-14 复核 zip 原件已不在 ~/Downloads**，溯源以工作区抽取件 `$HOME/WorkBuddy/工具开发/_aiwriting_extract/` 为准（SKILL.md + references 5 + scripts 5 + templates 2 + _meta.json） | 见 §二 卡 5 | **已引入** · v1.0.1 · 三条业务流；门禁原文 9 项逐条比对通过（2026-10-14，留证见 `dependency-verification-log.md` §四） | **无降级必要**：本团不调用其脚本，仅移植其「风格与字数确认门」；不可得时按 `content-condensation-standard.md` 正文执行即可 |
| 20 | `check_content_scope.py` | 伴生脚本（**页型契约运行时门**） | `$HOME/WorkBuddy/工具开发/outputs/_contentfix/check_content_scope.py`（**不入安装包**；他机不存在即走降级列） | `test -f "$HOME/WorkBuddy/工具开发/outputs/_contentfix/check_content_scope.py"` | **在且可执行**（2026-10-07 实跑，对内置样片输出完整页型断言；当前版本检测对象内置、未走 CLI 入参，对任意产出件断言按降级列人工核对） | **须人工核对**并按 `page-content-contract.md §五` 断言表标记「未验证」，**不得标"通过"** |
| 21 | `check_visual.py` | 伴生脚本（**视觉优化运行时门**） | `$HOME/WorkBuddy/工具开发/outputs/_visopt/check_visual.py`（**不入安装包**；他机不存在即走降级列） | `test -f "$HOME/WorkBuddy/工具开发/outputs/_visopt/check_visual.py"` | **在且可执行**（2026-10-07 实跑，A1–A13 + AN 断言正常出报告；2026-10-14 升级 A1–A14 + AN——新增 A14 内容区填充度，合规与违规两向验证通过；检测对象内置同 #20） | **须人工核对**并按本表 §七 + `visual-execution.md §1.2` 阈值表逐页核对，标「未验证」 |
| 22 | `preflight_scanner.py` | 伴生脚本（**发布前静态门禁 C8/C9/C10**） | `$HOME/WorkBuddy/工具开发/preflight_scanner.py` + `preflight-profiles/campus-ppt-helper.json`（**不入安装包**，安装包禁含 `.py`） | `test -f "$HOME/WorkBuddy/工具开发/preflight_scanner.py"` | **在且可执行**：对本包 32 项检查全绿；对陌生包首跑即抓出断链 / 超限 / 脚本残留等真实缺陷 | 缺则按 §五–§七 检查清单**人工逐项核对**，不得默认通过 |
| 23 | `measure.py` | 伴生脚本（**字数门：正文页信息量下限**） | `$HOME/WorkBuddy/工具开发/outputs/_contentfix/measure.py`（同 #20，不入包） | `test -f "$HOME/WorkBuddy/工具开发/outputs/_contentfix/measure.py"` | **在且可执行**（v3：正文页 200–260 字，索引页不设下限；阈值见 `runtime-gate-thresholds.md` §二） | **须人工核对**并按 `runtime-gate-thresholds.md` §二 逐页核对，标「未验证」 |
| 24 | `check_geom.py` | 伴生脚本（**几何门：重叠 / 出界 / 贴边**） | `$HOME/WorkBuddy/工具开发/outputs/_contentfix/check_geom.py`（同 #20，不入包） | `test -f "$HOME/WorkBuddy/工具开发/outputs/_contentfix/check_geom.py"` | **在且可执行**（GAP 15 / TOL 6 / EDGE 10pt，画布随模板传参；阈值见 `runtime-gate-thresholds.md` §三） | **须人工核对**并按 `runtime-gate-thresholds.md` §三 逐页核对，标「未验证」 |

> **连通总览**：24 项中 **22 项已连接**；未连通 2 项——`soffice` 落空（#14 `pptx2image.py` 因此实际不可用）与 `Spire.Presentation`（#15）未安装，**两者都只是「模板转图 / 离线出图」备选，均有 #12 `slidep` 兜底，不影响出片**。其中模板源（#16）已于 2026-10-07 切换为**腾讯文档「演示模板库」**并于 2026-10-08 升级为 **15 套全量 + 四级自适应取件链路**（缓存 → 直导 → 克隆导出 → 人工另存；克隆链路全链路实测通过，见卡 4 与 `tencent-docs-template-source.md §六`）；旧本机挂载（`~/campus-ppt-templates` / `~/uptt-templates`）与 147 MB 配套 zip **于 1.0.0 作废**，不再作为模板来源或保真比对基准。
>
> **#19 / #20 / #21 是 1.0.2 新增的三项**：#19 `ai-writing` 为**方法论来源**（非运行时依赖，移植「动笔前确认风格与字数」门至 `content-condensation-standard.md`）；#20 / #21 把页型断言与 A1–A12+AN 视觉断言变为可执行门禁，**均不入包**（S1 禁 `.py`），走伴生位置 + 人工核对降级。
>
> **#23 / #24 是 1.0.3 补登的两项**：运行时门禁实为四道，1.0.2 只登记页型门（#20）与视觉门（#21），字数门与几何门此前未进入登记表、换机后无预检与降级覆盖；本次补登 `measure.py` 与 `check_geom.py` 为伴生脚本，判据阈值全文同步固化进 `runtime-gate-thresholds.md`（campus-ppt-qa），四门降级核对流程见该文 §一 与卡 5 第 3 步。
>
> **四张预检卡已实跑验证**：卡 1 输出 7 行全 `OK`、卡 2 `edsdk.py list` 退出码 0、卡 3 判读口径来自 `bsk 0.3.2` 实测、卡 4 实测通过（2026-10-07 直导链路：鉴权 READY → 枚举 → 导出下载校验；2026-10-08 克隆链路：枚举 15/15 → copy_file → 导出下载 → 页层保真比对 → 副本清理）。

## 二、逐项连接卡（预检可直接复制执行）

### 卡 1 · 官方 `tencent-pptx` 与其设计文件

```bash
# 1) 技能是否在（两条安装路径都要试：市场缓存 / 用户级）
ls -d $HOME/.workbuddy/plugins/cache/workbuddy-builtin/tencent-pptx/*/skills/tencent-pptx 2>/dev/null \
  || ls -d $HOME/.workbuddy/skills/tencent-pptx 2>/dev/null \
  || echo "MISS: tencent-pptx 未安装"

# 2) 视觉美化依赖的 4+3 份设计文件是否齐（缺任一份即不得声称已调用视觉美化）
BASE=$(ls -d $HOME/.workbuddy/plugins/cache/workbuddy-builtin/tencent-pptx/*/skills/tencent-pptx 2>/dev/null | head -1)
for f in story-principle design-principle create-from-scratch create-from-material; do
  [ -f "$BASE/references/$f.md" ] && echo "OK   $f.md" || echo "MISS $f.md"
done
for b in academic consulting redgold; do
  [ -f "$BASE/references/designs/design-principle.$b.md" ] && echo "OK   $b" || echo "MISS $b"
done
```

**判读**：技能目录不存在 → 退回 WPS / 本地 Office，**交付说明须写明"未使用官方风格重绘"**。设计文件缺失 → **不得产出 `DESIGN.md`**，按"未调用视觉美化"判 FAIL（见 `visual-execution.md §一`）。

### 卡 2 · 官方 `tencent-local-office-edit`（路径 B）

该技能**随 App 内置分发，不在技能市场**，路径随 App 版本变化，**不要硬编码绝对路径**：

```bash
SKILL=$(ls -d /Applications/WorkBuddy.app/Contents/Resources/app.asar.unpacked/resources/plugins/workbuddy-builtin/skills/tencent-local-office-edit 2>/dev/null)
[ -n "$SKILL" ] && echo "OK  $SKILL" || echo "MISS: tencent-local-office-edit 不可用 → 退回路径 A"

# 验通编辑器（监听 39099–39108 端口区间；list 为空也属正常，关键是无报错）
python3 "$SKILL/edsdk.py" list
```

**判读**：`edsdk.py list` 能正常返回即连接成立（编辑器可能未启动，属正常，后续 `open_file` 会拉起）。**无报错但 `list` 为空 ≠ 失败**；若 `python3` 报找不到文件或端口无法建立 → 路径 B 不可用，退回路径 A 并**如实告知"未继承模板视觉"**。

### 卡 3 · 官方 `browser-skill`（采集）

```bash
BSK_AUTO_START=0 bsk status --json; echo "exit=$?"
```

**判读（实测口径，bsk 0.3.2）**：
- **退出码 0 且返回体有 `browsers` 字段** → 可用；若 `browsers` 为空数组 → 提示用户打开浏览器扩展完成配对，或转降级。
- **退出码 ≠ 0**，或返回体只有 `message` / `hint` / `exit_code` 而无 `browsers` → **不可用**，转 `browser-skill-integration.md §五` 降级，**不要反复重启守护进程**。
- 真实失败样本：`{"code": null, "message": "ensure daemon is running: …", "hint": "…", "exit_code": 2}`，**进程退出码为 2**——**不要只 grep `message` 就判死**。
- 沙箱约束：逐命令隔离的沙箱中环境变量不跨调用保持，**每条 `bsk` 命令都要带同一个 `BSK_HOME` 与 `BSK_AUTO_START=0`**。

### 卡 4 · 腾讯文档「演示模板库」（唯一运行时模板源，最高频引用）

> **依赖声明**：本连接器已在 `plugin.json` 的 `dependencies.connectors` 中声明——用户首次召唤本团时，WorkBuddy 会自动弹出连接引导卡，引导完成后才进入对话；本卡预检用于会话内复核授权仍有效。

四级取件：① 鉴权 → ② 枚举 → ③ 取件（缓存 / 直导 / 克隆） → ④ 校验与收尾。任一环节不过 → 按 `tencent-docs-template-source.md §四` 逐级降级，**严禁臆造模板**：

```bash
# ① 鉴权预检
python3 tencentdocs.py tdoc_init
#   READY → 继续；ERROR:no_token → 请用户在 WorkBuddy 重连腾讯文档连接器

# ② 枚举断言（15/15 tencentslide）
python3 tencentdocs.py tdoc_call tencent-docs manage.search_file '{"search_key":"模板"}'
#   判读：命中 ≥15 条 ext=tencentslide（广财族 10 套：01–10 全量 + 党政-01~05，
#   标题以 tencent-docs-template-source.md §二 云端清单为准）
#   注：folder_list 对文件夹快照 id 实测返回空，枚举一律走 search_file

# ③ 取件（file_id 从包内清单 templates/gdufe-template-manifest.json 直读，不走搜索定位）
#   L1 缓存：test -f ~/campus-ppt-cache/<云端标题>.pptx 且 file 校验合法 → 直接复用
#   L2 直导：
python3 tencentdocs.py tdoc_call tencent-docs manage.export_file '{"file_id":"<清单内源 file_id>"}'
#   L2 权限失败 → L3 克隆：copy_file 在调用者本人云盘生成副本（仅我可查看），对副本再 export_file
python3 tencentdocs.py tdoc_call tencent-docs manage.copy_file '{"file_id":"<清单内源 file_id>","title":"<云端标题>"}'
#   L3 失败 → L4：引导用户打开清单内 url「另存为副本」→ search_file 检索自有副本 → 走 L2

# ④ 导出下载与收尾
python3 tencentdocs.py tdoc_call tencent-docs manage.export_progress '{"task_id":"<task_id>"}'
#   progress=100 → file_url（签名临时链接，约 30 分钟时效，过期须重新 export_file）
curl -sL -o ~/campus-ppt-cache/<云端标题>.pptx "<file_url>"
file ~/campus-ppt-cache/<云端标题>.pptx   # 须为 "Microsoft PowerPoint 2007+"
#   （仅克隆路）下载校验通过后删除本人云盘副本：
python3 tencentdocs.py tdoc_call tencent-docs manage.delete_file '{"file_id":"<副本 file_id>"}'
```

**判读**：① 非 READY → **暂停出片**，请用户重连连接器；② 命中 <15 或目标模板缺失 → **暂停回主理人**，请用户核对「演示模板库」完整性（15 套）；③ L2 权限失败自动转 L3、L3 失败转 L4，**不得对失败环节反复重试硬撞**；④ 导出失败 / 下载件非法 → 重试 1 次后暂停，**不得沿用过期 file_url**；四级全败 → 暂停回主理人。

### 卡 5 · 外部技能 `ai-writing`（方法论来源）与伴生页型门禁

`ai-writing` 与本团的关系**只有一条**：本团移植了它业务流 C 的「动笔前必确认写作风格与字数」确认门，落点为 `content-condensation-standard.md`。**本团不调用它的脚本**（它的 `check_doc.py` / `check_report.py` 面向 docx 与日报周报，与 pptx 管线不同构）。

```bash
# 1) ai-writing 方法论来源是否可得（只用于溯源与复核其门禁原文，不参与出片）
#    zip 原件 2026-10-14 复核已不在 ~/Downloads；以工作区抽取件为溯源凭据
ls "$HOME/WorkBuddy/工具开发/_aiwriting_extract/SKILL.md" >/dev/null 2>&1 \
  && echo "OK   ai-writing 抽取件在（v1.0.1 · 2026-09-16 发布）" \
  || { ls -l ~/Downloads/ai-writing-1.0.1.zip >/dev/null 2>&1 \
       && echo "OK   ai-writing zip 在" \
       || echo "MISS: ai-writing 不可得（不影响出片，纪律已入包内标准）"; }

# 2) 移植成果是否在包内（这才是真正影响行为的东西）
PKG=./campus-ppt-helper
for f in content-condensation-standard page-content-contract; do
  [ -f "$PKG/skills/campus-ppt-design/references/$f.md" ] \
    && echo "OK   references/$f.md" || echo "MISS references/$f.md"
done

# 3) 四道运行时门禁伴生脚本（均不入包；缺则须人工核对并标「未验证」）
GATE_DIR="$HOME/WorkBuddy/工具开发/outputs"
for g in "_contentfix/check_geom.py|几何门|runtime-gate-thresholds.md§三" \
         "_contentfix/measure.py|字数门|runtime-gate-thresholds.md§二" \
         "_contentfix/check_content_scope.py|页型门|page-content-contract.md§五" \
         "_visopt/check_visual.py|视觉门|visual-execution.md§1.2"; do
  p="${g%%|*}"; r="${g#*|}"; n="${r%%|*}"; ref="${r#*|}"
  [ -f "$GATE_DIR/$p" ] && echo "OK   $n $p" \
    || echo "MISS: $n 不可得 → 按 $ref 人工核对，标「未验证」"
done
```

**判读三态**：

| 状态 | 条件 | 处置 |
|---|---|---|
| **已连接** | 第 2 项两份 `.md` 均在、第 3 项四门脚本齐 → 允许走五步法 | 正常出片 |
| **部分可用** | 两份 `.md` 在、第 3 项任一门脚本缺 | 出片照常，但**该门验收须人工核对并标「未验证」**，不得标"通过" |
| **未连接** | 第 2 项任一 `.md` 缺 | **治本依据缺失**：暂停进入第 ④ 步（凝练），回主理人补齐契约后再动笔 |

> **不得声称"已调用 ai-writing 技能生成课件"**。正确表述是"内容凝练纪律参照 `ai-writing` 1.0.1 业务流 C 的确认门"。超出这个范围的引用即属过度引用（`content-condensation-standard.md §六`）。

## 三、模板获取流程（1.0.1 起：四级自适应取件，定位不走搜索）

1. 按卡 4：鉴权 READY → 枚举 15/15（`tencentslide`）；
2. **file_id 从包内清单 `templates/gdufe-template-manifest.json` 直读**（15 套 id+url 内嵌；**文件名权威 = `tencent-docs-template-source.md §二` 云端清单**；search_file 只做枚举校验与 L4 副本检索，不用于定位）；
3. **四级取件**：L1 本地缓存合法 → 直接复用；L2 `export_file(源 file_id)` 直导；L2 权限失败 → L3 `copy_file` 生成副本（仅我可查看）→ 对副本导出，下载校验通过后删副本（回收站）；L3 失败 → L4 引导用户「另存为副本」到本人云盘后检索自有副本再导出；
4. `file` 校验为合法 pptx 后交 `template-application.md` 路径 A/B 消费。

> 旧流程（下载 147 MB 配套 zip 解压到 `~/campus-ppt-templates` / `~/uptt-templates`、`CAMPUS_PPT_TEMPLATE_DIR` 环境变量、卡 4 四级解析）**于 1.0.0 全部作废**；旧目录残留不再被识别，也不得作为保真比对基准。

### 模板渠道定性结论（登记防重查）

| 渠道 | 结论 | 依据（实测 / 已查证） |
|---|---|---|
| 腾讯文档「演示模板库」 | **唯一运行时模板源（已连接，实测通过）** | 2026-10-07 实测（所有者账号，直导）：全链路下载成功（合法 PowerPoint 2007+，约 5 秒/套），导出件页层 `<p:pic>`/`<p:sp>` 计数与原件一致、图片 7/7 保留；2026-10-08 实测：枚举 15/15 + **克隆导出链路全通**（copy_file 生成副本 → 对副本导出下载 3,390,960 B 合法 pptx → 页层 6 页/media 7 与直导基线一致 → 副本入回收站）。证据见 `tencent-docs-template-source.md §六` |
| IMA「演示模版库」 | **已退出运行时链路（1.0.0 起不调用）** | ima-mcp 仅返解析文本、无二进制下载工具（2026-10-07 实测 `fetch_media_content`）；原"三步验证协议"作废 |
| WorkBuddy 资料库「演示模板库」 | 仍非运行时源（1.0.0 结论沿用） | 作者个人空间，其他用户智能体不可枚举；仅人工下载渠道 |

## 四、未建立连接的引用（定级与处置）

> 表中「N 处」为**登记时点统计快照**，非实时计数；引用总数口径见 §〇。

| 编号 | 问题 | 定级 | 处置 | 状态 |
|---|---|---|---|---|
| E1 | 模板库 79 处引用，但无任何可执行检查命令 | **P0** | 新增本表 §一 #16–18、卡 4、§三 模板获取流程 | 已补建（1.0.0 起经腾讯文档源实测复验） |
| E2 | `tencent-local-office-edit` 仅 17 处提及工具名，**未登记"随 App 内置"的真实位置**（易被误判为未安装） | **P0** | 本表卡 2 给出"不硬编码绝对路径"的定位命令 | 已补建 |
| E3 | 路径 B 强制三步流程（`list` → `schema` → `call`）**只散落在 2 份 reference**，制作员无单一权威入口 | **P1** | 本表卡 2 + `official-skill-routing.md` 交叉引用 | 已补建 |
| E4 | `tencent-pptx` 64 处引用，**无预检命令**，只写"已安装/可调用" | **P1** | 本表卡 1 给出双路径定位 + 设计文件齐备性检查 | 已补建 |
| E5 | 视觉美化 7 份设计文件未做**齐备性校验**，缺 1 份仍可能声称"已调用" | **P1** | 本表卡 1 循环校验 + 缺任一份判 FAIL | 已补建 |
| E6 | `slidep` 20 处引用（质检必做出图），**未登记位置与子命令集合** | **P2** | 本表 #12 登记位置 + 5 个子命令 + 缺失降级 | 已补建 |
| E7 | `pptx2image.py` 6 处引用，**依赖 LibreOffice 但未在引用处就地标注"本机不可用"** | **P2** | 本表 #14 标注不可用 + 指定替代（方案 B/C） | 已补建 |
| E8 | `bsk` 53 处引用，仅 `browser-skill-integration.md` 有契约，**其余 52 处无判读口径** | **P2** | 本表卡 3 给出判读三态，成员一律以卡 3 为准 | 已补建 |
| E9 | 外部 URL 仅 5 个，**未标注可达性** | **P3** | 属文档规范链接，不影响运行；本表登记备查 | 登记备查 |
| E10 | 正文页被"扩写"填充的同时，**封面 / 目录 / 章节过渡页也被同一条"字数越多越好"指标推着塞满正文**，页面失去页型；原有几何门 + 字数门**结构上无法发现**此类缺陷 | **P0** | 新增 `page-content-contract.md`（七类页型契约）+ `content-condensation-standard.md`（凝练标准，移自 `ai-writing` 1.0.1）+ 本表 #20 伴生门禁 + 门禁 C9；缺陷台账见 `page-content-contract.md §六` | 已补建（2026-10-06） |
| E11 | "是否真调用了视觉美化"**只有一句文档声明**（产出 `STORY.md` + `DESIGN.md`，缺任一份 = FAIL），**没有任何可复算判据**——而留痕解决的只是"有没有读官方设计系统"，**不解决"版面算不算合规"**。典型情形是"两份留痕齐备 + 几何门/字数门/页型门三关全绿 + 版面仍然难看"，即留痕齐备但版面仍不合规 | **P0** | `layout-selection.md` 新增 **§1.2 可复算断言与伴生门禁登记**（首发 A1–A9，1.0.0 定稿为 A1–A13 + 备注门 AN）+ 本表 #21 + 门禁 C10；同时修掉 A6 的"完全包含"过宽豁免（曾放行两个完全重合的文本框） | 已补建（2026-10-06） |

> **定级口径**：P0 = 直接导致链路跑不通或误判依赖缺失；P1 = 导致"无法判断是否已调用"；P2 = 影响排查效率；P3 = 仅备查。

## 五、门禁（C8：外部依赖连接完整性）

`preflight_scanner.py` 的 **C8** 项检查：包内出现的每个外部依赖名，必须在本表 §一总表中登记，且**至少 3 个官方技能各带一条可执行预检命令**。C8 判 FAIL 的两种情形：

1. 正文出现外部依赖名，但本表 §一未登记 → **连接缺失**；
2. 本表登记了依赖，但 §二缺该依赖的预检命令 → **登记不完整**。

> 新增外部依赖时，**必须同批更新**：本表 §一总表 → §二连接卡 → `README.md` 前置依赖清单 → `CHANGELOG.md`。四处不同步即视为未建立连接。

## 六、门禁（C9：页面内容类型契约完整性）

`preflight_scanner.py` 的 **C9** 项检查（治本项，与 C8 并列）：

1. `page-content-contract.md` 是否存在；
2. 是否被 `SKILL.md` 参考索引收录（防契约失联）；
3. 七类页型（封面 / 目录 / 章节过渡 / 正文-案例 / 正文-证据 / 正文-并列 / 结尾）是否齐备；
4. 同批的 `content-condensation-standard.md` 是否存在；
5. 契约内是否登记了运行时门禁脚本 `check_content_scope.py`。

任一项不满足 → **C9 FAIL**。C9 与 C8 的分工：**C8 管"外部依赖连没连上"，C9 管"页面内容有没有页型约束"**——两者此前都是缺口，均已补建。

## 七、门禁（C10：视觉优化可执行性）

`preflight_scanner.py` 的 **C10** 项检查（治本项，与 C8/C9 并列）：

1. `visual-execution.md` 是否存在（视觉断言与门禁在执行侧；版式规划见 `layout-selection.md`）；
2. 是否被 `SKILL.md` 参考索引收录（防标准失联）；
3. **十四条视觉断言 A1–A14 + 备注门 AN** 是否齐备（缺任一 = 视觉优化无判据）；
4. 标准内是否登记了运行时门禁脚本 `check_visual.py`；
5. 是否保留 `STORY.md` / `DESIGN.md` 留痕判据（"缺任一份 = FAIL"）；
6. 是否声明三态分支路由（完全命中 / **软降级命中** / 多行命中）。

任一项不满足 → **C10 FAIL**。C10 与 C8/C9 的分工：**C8 管"外部依赖连没连上"，C9 管"页面内容有没有页型约束"，C10 管"版面有没有可复算的合规判据"**。
> C10 的判据是**"标准齐备"**，不是**"某一册产出件已通过"**——单册产出件是否通过由运行时门禁 `check_visual.py` 退出码判定（见 `visual-execution.md §1.2`）。二者缺一不可：没有 C10，标准会被删空而无人察觉；没有运行时门禁，标准再全也只是文档。

## 八、功能执行验证记录

全链核验的动作与结果留证已独立成文：**`dependency-verification-log.md`**（同目录）。登记表本体（本文）与核验日志的分工：本文管「依赖是什么、怎么预检、缺了怎么降级」，日志管「上次真跑是什么时候、结果如何」。换机或升级官方技能后按 §二 各卡预检重测并**在日志追加新记录**，不得沿用旧结论。
