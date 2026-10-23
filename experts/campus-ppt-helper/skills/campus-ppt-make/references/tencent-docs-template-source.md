# 腾讯文档「演示模板库」调用层（唯一运行时模板源）

> 面向制作员（campus-ppt-maker）。campus-ppt-helper **1.0.0 起**，内置模板的唯一运行时源为**腾讯文档「演示模板库」**（docs.qq.com，`tencentslide` 在线幻灯片格式）；**1.0.1（2026-10-08）起为 15 套全量**（广财-02/03 回归，去重不再生效），并把读取链路升级为**四级自适应取件**（缓存 → 直导 → 克隆导出 → 人工另存），任一级失败自动降下一级。**本机挂载 `~/campus-ppt-templates` / `~/uptt-templates` 与 147MB 配套 zip 已作废**，不得再作为模板来源或保真基准。
> 本文件为唯一权威入口，固化「取件链路 + 选型 + 降级」。所有工具经 `tencent-docs` 连接器（`tencentdocs.py tdoc_call`）调用；**调用前必须 `tdoc_schema` 查参数，严禁凭记忆拼参**。
> 实测基线：2026-10-07 直导链路全链路实跑（含下载保真比对）；2026-10-08 枚举 15/15 + 克隆导出链路全链路实跑（含副本生成、下载、页层保真比对、副本清理），证据见 §六。

## 〇、控制面与数据面（合一体）

控制面（发现/选型/定位）与数据面（二进制取回）统一在腾讯文档一个连接器内；**定位不再依赖搜索**——file_id 内嵌于包内清单，取件按四级自适应：

```
templates/gdufe-template-manifest.json（15 套，内嵌 file_id + url）
  → L1 本地缓存 ~/campus-ppt-cache/<云端标题>.pptx 合法 → 直接消费（零云端调用）
  → L2 export_file(源 file_id) → export_progress → file_url → 下载校验 → 消费
  → L2 权限失败 → L3 copy_file(源 file_id) 在本人云盘生成副本（仅我可查看）
        → export_file(副本 file_id) → …同 L2 → 下载校验 → 删除副本（回收站）→ 消费
  → L3 失败 → L4 引导用户打开清单内 url「另存为副本」到本人云盘
        → search_file 按云端标题检索自有副本 → 走 L2 导出下载
  → 四级全失败 → 暂停回主理人，严禁臆造
```

> 设计要点：L2 直导对所有者 / 已授权账号直达（零副作用）；L3 克隆把「读取他人文件」转化为「读取自己云盘的副本」，副本即用即删不堆积；L4 人工另存是产品级能力兜底。源模板全程只读，**绝不写回「演示模板库」**。

## 一、取件五步（真实工具与参数，已实测）

**Step 0 · 鉴权预检**（每次会话一次）
```bash
python3 tencentdocs.py tdoc_init
# READY → 继续；ERROR:no_token → 暂停，请用户在 WorkBuddy 重连腾讯文档连接器
```

**Step 1 · 定位模板 file_id（清单直读，不走搜索）**
```bash
# file_id 权威来源 = 包内清单 templates/gdufe-template-manifest.json（15 套，id+url 内嵌）
# search_file 仅两个用途：① 枚举完整性交叉校验；② L4 检索用户自有副本
python3 tencentdocs.py tdoc_call tencent-docs manage.search_file '{"search_key":"模板"}'
# 交叉校验判读：命中 ≥15 条 ext=tencentslide（广财-01~10 + 党政-01~05，标题以 §二 清单为准）
```
> 备选枚举：文件夹「演示模板库」（快照 file_id `BvYidikSLXtg`）经 `manage.folder_list` **2026-10-08 实测返回空列表**，**不得作为枚举通道**，一律以 `search_file` 为准。

**Step 2 · 取件（L1 缓存 → L2 直导 → L3 克隆，逐级降级）**
```bash
# L1 · 缓存命中检查（先于一切云端调用）
test -f ~/campus-ppt-cache/<云端标题>.pptx && file ~/campus-ppt-cache/<云端标题>.pptx
#   合法 pptx → 直接跳到 Step 4 消费，不发起任何云端调用

# L2 · 直导（所有者 / 已授权账号直达）
python3 tencentdocs.py tdoc_call tencent-docs manage.export_file '{"file_id":"<清单内源 file_id>"}'
#   → 返回 task_id（如 drivetask_xxx）

# L2 权限失败 → L3 · 克隆：在调用者本人云盘生成副本（官方语义：新文档权限「仅我可查看」）
python3 tencentdocs.py tdoc_call tencent-docs manage.copy_file '{"file_id":"<清单内源 file_id>","title":"<云端标题>"}'
#   → 返回新 file_id（title ≤36 字符，云端标题均满足）→ 对副本 file_id 重复上方 export_file
```

**Step 3 · 轮询进度并下载**（`manage.export_progress`，3–5 秒一询；实测约 5 秒完成）
```bash
python3 tencentdocs.py tdoc_call tencent-docs manage.export_progress '{"task_id":"<task_id>"}'
# progress=100 时返回 file_url（签名临时链接，有效期约 30 分钟），立即下载：
curl -sL -o ~/campus-ppt-cache/<云端标题>.pptx "<file_url>"
file ~/campus-ppt-cache/<云端标题>.pptx   # 须为 "Microsoft PowerPoint 2007+"
```

**Step 4 · 校验后消费 + 克隆路收尾**
```bash
# （仅 L3 克隆路）下载校验通过后删除本人云盘中的模板副本，防副本堆积：
python3 tencentdocs.py tdoc_call tencent-docs manage.delete_file '{"file_id":"<副本 file_id>"}'
```
校验通过后交 `template-application.md` 路径 A/B 消费，**逻辑不变，仅源路径变**（`cp ~/campus-ppt-cache/<云端标题>.pptx <输出>.pptx`）。

**缓存复用**：`~/campus-ppt-cache/<云端标题>.pptx` 已存在且为合法 pptx 时**直接复用，跳过 Step 2–4**（免重复取件，兼作离线韧性）。缓存目录不存在先 `mkdir -p ~/campus-ppt-cache`。

## 二、云端权威清单（15/15，2026-10-08 实测快照）

> **文件名为权威**（云端命名：广财-01~10 全量 + 党政-01~05）。file_id 为快照（2026-10-07 与 2026-10-08 两次实测逐项一致，稳定）；运行时一律以**包内清单内嵌 id** 取件，id 失效时用 `search_file` 按标题动态解析并回填清单。

| 模板标题（云端） | file_id 快照 | url |
|---|---|---|
| 广财-01-红色风景模板 | `BbjJFyIrlKNG` | https://docs.qq.com/slide/DQmJqSkZ5SXJsS05H |
| 广财-02-蓝色风景模板 | `BPLPXylgXZcd` | https://docs.qq.com/slide/DQlBMUFh5bGdYWmNk |
| 广财-03-蓝绿风景模板-1 | `BhYmASalMCFD` | https://docs.qq.com/slide/DQmhZbUFTYWxNQ0ZE |
| 广财-04-蓝绿风景模板-2 | `BxJMUNWtUKqJ` | https://docs.qq.com/slide/DQnhKTVVOV3RVS3FK |
| 广财-05-蓝绿风景模板-3 | `BoKRJPGvlHbr` | https://docs.qq.com/slide/DQm9LUkpQR3ZsSGJy |
| 广财-06-夜景深底白字模板 | `BjuqSKkvqmNy` | https://docs.qq.com/slide/DQmp1cVNLa3ZxbU55 |
| 广财-07-绿色极简模板 | `BTDmAgURNXKu` | https://docs.qq.com/slide/DQlREbUFnVVJOWEt1 |
| 广财-08-蓝灰色调模板 | `BnawAQiuqdzA` | https://docs.qq.com/slide/DQm5hd0FRaXVxZHpB |
| 广财-09-蓝色设计空间模板 | `BoqDtWWskZMk` | https://docs.qq.com/slide/DQm9xRHRXV3NrWk1r |
| 广财-10-蓝色校园科技风模板 | `BHCpvUMdKQhu` | https://docs.qq.com/slide/DQkhDcHZVTWRLUWh1 |
| 党政-01-基层机关党支部工作总结模板 | `BlUCoSibpUrY` | https://docs.qq.com/slide/DQmxVQ29TaWJwVXJZ |
| 党政-02-红色二十届三中全会通用模板 | `BJwKocQmseCF` | https://docs.qq.com/slide/DQkp3S29jUW1zZUNG |
| 党政-03-机关单位年终工作总结模板 | `BMmUKQIzCzFO` | https://docs.qq.com/slide/DQk1tVUtRSXpDekZP |
| 党政-04-党风廉政反腐倡廉主题党课模板 | `BxDpCWEsOCwL` | https://docs.qq.com/slide/DQnhEcENXRXNPQ3dM |
| 党政-05-答好党纪学习教育之卷模板 | `BhRrOSxMkudF` | https://docs.qq.com/slide/DQmhSck9TeE1rdWRG |

> 枚举断言 = **15/15 命中 `tencentslide`**（search「模板」）。url 的用途：L4 人工另存引导、交付说明回溯。

## 三、选型（文件名 + 真实色板，无 IMA 文本层）

云端文件名自带场景描述词（红色 / 蓝色 / 蓝绿×3 / 夜景深底白字 / 绿色极简 / 蓝灰 / 设计空间 / 科技风 / 党课 / 党纪 …），选型规则：

1. **场景→模板族**：教学/答辩/实习（广财师生）→ `广财族（10 套：01–10 全量）`；党建党政 → `党政-01~05`；其他学校/单位 → 按 `school-adaptation.md` 分支（自备 / 中性兜底）。
2. **族内按基调选**：以用户明示基调优先（如"科技感"→广财-10；"极简"→广财-07；"庄重红"→广财-01 或党政族），辅以 `template-application.md §六` 色板表。广财-02 与 01 同母版、03 与 04 同母版（去重期判定，现全量回归；**旧包编号判定，云端重排后对应关系未验证**，以重测为准，见 §七）——同型场景需要差异化时可分别选用。
3. **歧义即问**：用户未表态或多套等权时，回主理人出 top-3 供用户终选；**严禁凭文件名臆断套型归属**（学习/答辩/实习同池，无唯一正确答案）。
4. 选定后交付说明**必须写明模板云端标题**，便于回溯。

## 四、降级口径（四级取件，不臆造）

| 情形 | 判定 | 处置 |
|---|---|---|
| 鉴权失败 | `tdoc_init` 返回 `ERROR:no_token` 或调用报 400006 | **暂停出片**，请用户在 WorkBuddy 重连腾讯文档连接器 |
| 枚举不足 15 | `search_file` 交叉校验命中 <15 或目标模板缺失 | 先核对 §二 标题拼写；仍无 → **暂停回主理人**，请用户确认「演示模板库」是否完整（15 套） |
| L2 直导权限失败 | `export_file` 对源 file_id 报权限类错误 | **自动转 L3 克隆**（不重试硬撞） |
| L3 克隆失败 | `copy_file` 报错（含权限类） | **转 L4**：引导用户打开清单内 url，本人账号「另存为副本」到自己的云盘 → `search_file` 按云端标题检索自有副本 → 走 L2 导出下载 |
| L4 后检索 0 命中 | 用户未完成另存 / 另存到了其他账号 | 重新引导一次；确认后仍无 → **暂停回主理人** |
| 导出失败 | `export_progress` 长时间非 100 或报错 | 重试 1 次；仍败 → 暂停回主理人 |
| 下载件非法 | `file` 非 PowerPoint 2007+ 或解包失败 | 重试 1 次；仍败 → 暂停回主理人 |
| `file_url` 过期（约 30 分钟） | 下载 403/失效 | 重新 `export_file` 取新链接，**不得沿用旧链接** |
| 缓存缺文件 | `test -f` 失败 | 回到 Step 2 重新取件，**不臆造缓存路径** |
| IMA | 已退出运行时链路 | 不调用、不引用；IMA 侧故障不影响本链路 |

## 五、已知限制（实测）

1. **导出为再序列化件**：md5 与上传原件必然不同——保真判定**严禁用 md5**，以页层 `<p:pic>`/`<p:sp>` 计数 + 逐页目视为准（口径同 `template-application.md`）。
2. **图片落点非标**：导出件图片位于 `ppt/slides/media/`（原件在 `ppt/media/`），两条路径各自自洽、文件合法（与 editor_sdk 落盘行为一致）。
3. **file_url 时效约 30 分钟**：导出后须立即下载。
4. **导出并发/频率**：未见明确限额，建议逐套串行取件（15 套全量约 1–2 分钟量级）。
5. **克隆副本属性（官方语义）**：`copy_file` 生成的副本权限为「仅我可查看」、落在调用者本人云盘；title ≤36 字符；**用后即删**（`manage.delete_file` 入回收站，源模板不动），防副本堆积。
6. **跨账号放行待多账号实测**：非所有者账号对 L2 直导 / L3 克隆的实际放行情况未实测；链路设计已保证任一失败自动降下一级，最坏落 L4 人工另存（产品级能力，实测存在）。
7. **folder_list 对「演示模板库」文件夹快照 id 返回空**（2026-10-08 实测）——枚举一律走 `search_file`，不走文件夹枚举。

## 六、实测证据

### 2026-10-07 · 直导链路（L2，所有者账号）

- 全链路：`search_file(广财-01)` → `BbjJFyIrlKNG` → `export_file` → task `drivetask_f3722d56…` → 首次轮询（5 秒）progress=100 → `file_url` 下载 → **3,390,958 B，`Microsoft PowerPoint 2007+`**。
- 保真结构比对（导出件 vs 原件）：6/6 页 `<p:pic>`/`<p:sp>` 计数完全一致；图片 7/7 保留（`ppt/slides/media/`）。
- 广财-07 同批实测：导出下载 142,856 B，合法 pptx。
- 逐页目视（官方渲染器）与全 15 套逐套校验列入验收清单（qa 方案 §五），不在本文件重复。

### 2026-10-08 · 枚举 + 克隆导出链路（L3，所有者账号）

- **枚举 15/15**：`search_file("模板")` 命中 15 条 `ext=tencentslide`，file_id / 标题 / url 与 §二 快照逐项一致（含回归的广财-02 `BPLPXylgXZcd`、广财-03 `BhYmASalMCFD`）。
- **克隆导出全链路**：`copy_file(广财-01 BbjJFyIrlKNG, title=广财-01-链路实测副本)` → 副本 `BrTyjvAqsjFU`（仅我可查看）→ `export_file(副本)` → task `drivetask_72802fc7…` → 5 秒 progress=100 → 下载 **3,390,960 B，`Microsoft PowerPoint 2007+`**。
- **页层保真比对**：副本导出件 6 页 / media 7（`ppt/slides/media/`），与 2026-10-07 直导基线逐项一致（字节数差 2 B 属重序列化正常波动）。
- **副本清理**：`delete_file(副本)` 成功入回收站，源模板无任何改动。

## 七、基线重测触发机制（模板数据管线）

包内模板数据管线由四处组成：`body-typography-standard.md` 附录 A（字阶）与 §5.0（画布）、`template-application.md` §六（色板）、`layout-selection.md` 附录 A（版式族）、`templates/gdufe-template-manifest.json`（云端清单）。管线数据来自 2026-10-06~08 实测；**云端库会变、换机会缺工具**，命中下列任一条件必须重测，不得沿用旧基线：

| 触发条件 | 判定动作 | 重测范围 |
|---|---|---|
| 模板库清单变更 | `search_file("模板")` 枚举 ≠15，或标题 / file_id 与 §二 快照不一致 | 全量 15 套 |
| 模板更新 | 缓存件页数 / 媒体数与基线表不一致（**页数是最快的核对依据**） | 该套 |
| 换机 / 新环境 | 首次出片前 | 全量（至少先测 1 套确认流程可用） |
| 官方技能 / 连接器升级 | edsdk / tencent-pptx 版本变化 | 全量 |

**重测前置（工具链探测纪律）**：重测依赖 `tencent-local-office-edit`（edsdk）与解包读取——先按登记表卡 2 预检（`edsdk.py list` 退出码 0；**随 App 内置，勿硬编码路径**）。工具链不齐时，重测结论只能标「未验证」，**不得拿旧表冒充新测**。

**重测动作**（逐套）：① 按 §一 四级链路取最新件到 `~/campus-ppt-cache/<云端标题>.pptx`；② 读 `p:sldSz` 记画布；③ `typescale_scan.py` 直读字号频次 + edsdk `slide_get_page_info` 补母版继承值（封面 / 章节页）；④ 解包统计 slideMaster / slideLayouts / slides 显式 `srgbClr` 频次；⑤ 按结构桶数内容页可深拷贝版式种数。

**数据回写位置（四处，缺一处则各处数据对不上）**：字阶 / 画布 → `body-typography-standard.md` 附录 A 与 §5.0；色板 → `template-application.md` §六；版式族 → `layout-selection.md` 附录 A；清单与 `enumeratedAt` → `templates/gdufe-template-manifest.json`。

**留证**：每次重测在 `dependency-verification-log.md` 追加一节（只追加、不改写历史），记录日期 / 触发条件 / 工具链预检 / 逐套数据 / 与旧基线差异；数据按「已验证 / 未验证 / 缺失」三态标注，不允许无标注混用。

**查表后的页数核对**（低成本防错）：查表取到某行数据后，用所选框件的实际页数与该行页数比对——不一致即该行映射存疑，回退运行时实测，不得照抄。

**当前管线状态（2026-10-14）**：广财-04/05/06/07 行标签已按云端命名重打，但旧包行 ↔ 云端 file 的对应关系**未经重测确认（未验证）**；云端 05=蓝绿风景模板-3 **无实测数据（缺失）**；旧「蓝色校园模板-3」**云端已下线**（数据仅存旧包基线）。下次触发条件命中时优先补齐这三格。
