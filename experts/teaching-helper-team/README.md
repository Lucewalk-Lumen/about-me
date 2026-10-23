# 教学帮帮团（Teaching Helper Team）

九位成员（1 位主理人 + 8 位领域专家：案例写作、论文辅导、课程建设、课件制作、纪要整理、智能体构建、语音合成、课题申报）构建于五类基础能力（材料提取、爬虫采集、素材总结、知识库、长文整合）之上，以「去AI味 + 引用保真」**交付前统一质检流程**作为所有文本生成产出的最后一道把关，一站式完成教学全流程交付，自然无痕、引用可信。另含 2 项内置扩展能力：教材章节批量扩充（textbook-chapter-expansion，内置 course-builder）、文献深度蒸馏（literature-distiller，内置 thesis-mentor）；教育课题申报由独立领域技能 edu-grant-writer（绑定 grant-writer）提供。

> **运行环境**：本团脚本需 **Python 3.9+**。Node 侧 `minutes-organizer` 依赖 npm 包 `docx`（Node 16+）。首次会话由 `setup` 技能自动安装全部运行时依赖；crawler 前端的 `bsk` 与浏览器扩展由官方腾讯 BrowserSkill 技能（单独安装）提供，`setup` 仅做就绪检测。

> **联网边界（隐私知情）**：本团**非完全离线**，以下能力按设计会发起网络请求——`crawler` 联网检索/抓取网页；`text-to-speech` 经 Edge TTS 合成音频（**待合成文本会发往微软 Edge TTS 服务端点**，敏感内容请勿用该功能，或改用纯本地 TTS 方案）；`setup` 首次装依赖从 PyPI（默认清华镜像）拉取。其余文本生成、素材整理、课件构建等均在本地完成。涉及未公开内容时，请先在工作台/本地处理好再决定是否联网。

## 类型

Team 型（多角色协作团队）

## 成员（9 位：1 位主理人 + 8 位专家，专家按字母序）

| 成员 | 名字 | 领域技能 | 职责 |
|------|------|---------|------|
| lead | 齐帮办（教学编排总监） | —（持有基础能力+质量门禁） | 编排调度、基础能力按需注入、门禁、合稿交付 |
| architect | 安志远（智能体架构专家） | architect | 智能体/Skill 生产级制作（SPEC-01~12 + validate_pack + 从材料生成技能包） |
| case-writer | 陈叙真（案例写作专家） | case-writer | 高校教学/课程思政案例（八要素 + 引用保真 + 去AI味门禁） |
| course-builder | 柯明纲（课程建设专家） | course-builder + textbook-chapter-expansion | 课程建设全流程 + 教材薄弱章节批量扩充（三路扫描→并行扩充→锚点注入→素材回填→一致性验证） |
| grant-writer | 项承文（教育课题申报专家） | edu-grant-writer | 教育课题申报书撰写（Phase -1→0→0.5→1→2 门控；市/省/国家级级别适配；质量检测） |
| minutes-organizer | 闻纪清（纪要整理专家） | minutes-organizer | 会议纪要与学术综述（五路径 + OCR + TEEL + 双档 Word） |
| ppt-maker | 裴演（课件制作专家） | ppt-maker | 独立「做PPT / 演讲文稿」诉求（HTML 单文件为主、python-pptx 离线生成，make/edit 双线） |
| text-to-speech | 声入微（语音合成专家） | text-to-speech | 免费语音合成（Edge TTS，MP3+SRT，课程/汇报/答辩音频） |
| thesis-mentor | 周慎导（论文辅导专家） | thesis-mentor + literature-distiller | 毕业论文 T1~T6 六阶段辅导 + T7~T9 扩展（期刊/审稿/答辩）+ 4+2 学术论文深度蒸馏 |

## 技能结构（18 项 = 16 项顶层技能 + 2 项内置扩展，四层）

### 基础能力层（foundation · 5 项 · 挂主理人按需注入）
| 技能 | 能力 |
|------|------|
| crawler | 爬虫采集（双模式：后端 requests 静态 + 前端 bsk 已登录会话浏览器，lead 按决策树路由） |
| material-extractor | 材料提取（多源文档 → 结构化全文 + 元数据，下游直接消费） |
| content-summary | 素材总结（URL/文件/PDF/音视频/YouTube） |
| knowledge-wiki | 知识库（资料分析后结构化沉淀为可检索 wiki，自动注入） |
| long-manuscript-core | 长文整合（材料启动 / 有界续写改稿 / 成稿收口） |

> foundation 有固定上游→下游依赖，由 lead 按用户提示词**按需选取**：
> `crawler（采集，仅无现成材料时）→ material-extractor（提取）→ content-summary（总结）→ knowledge-wiki（入库）→ long-manuscript-core（整合）→ 领域专家消费`

### 质量门禁层（quality · 2 项 · 交付前统一质检流程）
| 技能 | 能力 |
|------|------|
| deai-rules | 去AI味四层规则库（唯一 SSOT）：英文通用 + 中文通用 + 文体专用 + 量化诊断 |
| citation-integrity | 引用保真校验清单（四铁律 + 核验四问 + 三态标注 + 交付门槛，含速查卡） |

### 领域技能层（domain · 8 项 · 与专家一一对应）
architect / case-writer / thesis-mentor / course-builder / ppt-maker / minutes-organizer / text-to-speech / edu-grant-writer（对应 grant-writer）

> 另有 2 项**内置扩展**（与上述 16 项顶层技能合计 18 项）：`textbook-chapter-expansion`（教材章节扩充，归属 course-builder）、`literature-distiller`（文献蒸馏，归属 thesis-mentor）。二者的磁盘布局与归属说明详见 `STRUCTURE.md`（「内置」仅表示能力归属，由对应领域专家编排使用）。

### 初始化（1 项）
`setup`：一键装齐运行时依赖、检测 crawler 前端依赖的官方 BrowserSkill bsk、生成凭证模板。

> 命名口径：专家（Agent ID）与其领域技能（skill 目录名）一一对应（唯一例外：grant-writer 对应 `edu-grant-writer`）；基础能力与质量门禁挂主理人 lead，领域专家的前置基础能力依赖由主理人 lead 在 `agents/teaching-helper-team-lead.md` 的「能力依赖层级」表中统一登记与维护（如 case-writer / thesis-mentor / minutes-organizer 依赖 `crawler` + `knowledge-wiki`）。

### 初始化技能（setup）
**Python / Node 依赖全自动，crawler 前端需一次手动启用**：主理人首次会话检测 `~/.workbuddy/teaching-helper-team/setup-status.json`，未就绪则自动调用 `setup` 创建托管 Python venv 并安装全部 Python 依赖、安装 Node `docx`、检测 crawler 前端依赖的官方 BrowserSkill bsk（本包不再随附二进制）、生成凭证模板。详见 `skills/setup/SKILL.md`。

> [注意] **安装必读（crawler 前端专用，需一次手动操作）**：`setup` 只覆盖 Python / Node 依赖；本团 `crawler` 前端（浏览器自动化）装包 / 更新后**仍需手动启用**——在 Chromium 内核浏览器以「开发者模式 → 加载已解压的扩展」加载官方 BrowserSkill 技能提供的扩展路径，并确认 `bsk` 已在 PATH（由官方 BrowserSkill 技能安装）、已手动执行 `bsk daemon start`。未完成前仅 crawler 前端能力不可用，不影响其余技能（完整边界见下文「外部运行时依赖与降级矩阵」）。

## 使用示例

- 请帮我写一份高校教学案例
- 帮我整理这次研讨会的会议纪要
- 帮我辅导毕业论文选题
- 帮我做一个智能体技能包并校验
- 帮我把这份稿件去AI味（保留全部引用原样）
- 帮我把教材整理成结构化素材再做课件
- 帮我做一份教学PPT课件
- 帮我把这份讲稿合成语音

### 推荐提示词与预期成员链（回归基准）

专家卡片展示的 3 条 `quickPrompts` 均设计为**跨成员 + 门禁**任务型，用以体现团队协同价值（而非单人工具能力）。改版时应按下表核对「提示词是否仍能触发多成员编排」：

| # | 推荐提示词（`quickPrompts`） | 预期被调度成员链 |
|---|---|---|
| 1 | 把这份会议录音整理成纪要，再据此写一份教学案例，最后统一去AI味并核验引用。 | minutes-organizer → case-writer → deai-rules + citation-integrity |
| 2 | 我要申报省级教育课题：先检索政策与文献，再撰写申报书，最后做质量检测。 | crawler → material-extractor → edu-grant-writer（grant-writer）→ 双门禁 |
| 3 | 把这本教材提取成结构化素材，再生成课程大纲与全套课件。 | material-extractor → course-builder（课件环节用 ppt-maker）→ 双门禁 |

> `defaultInitPrompt` 与 `quickPrompts[0]` 保持**逐字一致**（平台校验要求）。

## 铁律

- 去AI味不等于压缩：数据口径/样本量/方法条件/专有名词/引用标记一律保留
- 引用保真：原样保留〔R-xx〕〔综述·X〕等标记，不编引用/不归观点/标注无支撑/不超范围
- 门禁：交付前过 quality 双门禁——deai-rules（五维自评 ≥45 且 deai_preflight.py PASS）+ citation-integrity（引用核验清零）

## 分发与兼容

本团的 `crawler` / `content-summary` / `text-to-speech` / `architect` / `knowledge-wiki` 是领域定制封装，底层复用通用引擎：

- `crawler` → requests + BeautifulSoup4（后端）+ bsk CLI（前端）
- `text-to-speech` → 微软 edge-tts（开源库）
- `content-summary` → 通用多模型 summarizer CLI
- `architect` → 平台无关的构建方法论 + validate_pack.py 校验器
- `knowledge-wiki` → 通用增量编译知识库模式（Karpathy Wiki）

**兼容原则**：作用域隔离（技能名为团队内作用域）；复用通用引擎（宿主已具备则优先复用）；运行时隔离（依赖装进 WorkBuddy 托管运行时）；同名共存（lead 统一编排，不超范围改写宿主技能）。

## 分发与合规声明

- **专家类型**：Team 型（`expertType: team`）。按平台《专家团开发标准》，Team 型 `profession`（职业头衔）必须与 `displayName`（展示名）取值一致——本包二者均为 **教学帮帮团 / Teaching Helper Team**。
- **行业分类**：`categoryId` 取 **`12-IndustryConsultant`**。判定依据：经核对平台官方 `validate_expert.py` 校验器（最新版）的 `VALID_CATEGORY_IDS`，官方行业分类**始终为 12 类**，**并不包含此前误用的 `15-Education`**（该值系本包旧版对官方枚举的误读，官方从未将分类扩充至 15 类；使用它会触发平台官方校验器报错、包无法加载）。在 12 类合法枚举中，`12-IndustryConsultant`（行业咨询 / 专业顾问）最贴合本团「九位教学专家对外提供专业咨询与交付」的定位，且与同系列 `course-tutor` 包保持一致；早期采用的 `09-OperationsHR` 语义域为运营 / 人力 / 行政，与本团业务已不匹配。
- **权威门禁**：平台官方 validate_expert.py 校验器与打包脚本 package_expert.py 为**唯一权威合规口径**；本包根 `scripts/verify.py` 仅为**补充自检**，覆盖面不等于官方合规全集（官方校验器的 categoryId 枚举、tags / quickPrompts 数量、agentName 前缀、agent 无 tools 等硬规则已在本包自检中对齐，但最终判定仍以官方校验器为准）。
- **自检用法**：在包根执行 `python3 scripts/verify.py`（纯标准库，任意 Python 均可）——退出码 **0 = 通过 / 1 = 存在 FAIL（阻断加载）**；可直接嵌入 CI：非 0 即失败。脚本会输出**受检项计数**，便于区分「确实全部通过」与「断言根本没有执行」。
- **本版改进摘要**：1.0.2 为**可用性与协同**改进版本。合规底线字段中 `expertType` / `displayName` / `profession` / tags 数量 / `agentName` 前缀均保持 1.0.1 口径，**仅 `categoryId` 由 `09-OperationsHR` 修正为 `15-Education`**（原因见上一条「行业分类」；注意该 15 类枚举系对官方清单的误读，已于 1.1.1 修正回官方 12 类枚举的 `12-IndustryConsultant`）。改进内容详见 `CHANGELOG.md` 的「[1.0.2] - 2026-09-25」条目。
- **合规结论沿用**：1.0.1 的合规修复（行业分类调整、团队展示名与职业头衔对齐并移除旧别称、主理人头像更名、自检脚本跨平台修复并补齐官方硬规则）在本版**全部保留**，详见 `CHANGELOG.md` 的「[1.0.1] - 2026-09-19」条目。

## 外部运行时依赖与降级矩阵

| 依赖 | 前置 | 失败时的降级行为 | 影响范围 | 是否阻断 |
|------|------|-----------------|---------|---------|
| Python 托管 venv（按 `requirements.lock` 声明的依赖） | Python 3.9+；首次会话由 `setup` 自动创建并安装（支持 `--minimal` / `--only` 分批与 `--resume` 续装） | 未就绪时，依赖 venv 的技能不可运行；可用 `--minimal` 先只装静态爬虫最小集（冷启动约 1 分钟） | crawler 静态模式、material-extractor、thesis-mentor 图表、text-to-speech 等 | 否（crawler 前端与纯 LLM 技能不受影响） |
| Node `docx`（minutes-organizer） | Node 16+；由 `setup` 安装 npm 包 `docx` | 缺 Node 时纪要先出 Markdown、Word 延后生成 | 仅 minutes-organizer 的 Word 产出 | 否 |
| `bsk` CLI + Chromium 扩展（crawler 前端） | 手动加载扩展 + `bsk daemon start` | 未启用则 crawler 前端不可用 | 仅 crawler 前端（已登录会话 / 动态渲染） | 否（可用 crawler 静态模式兜底） |
| 平台官方办公技能（.pptx / .docx / .xlsx 出片） | 宿主已安装平台官方办公技能 | 未安装则回退到本包自带路径（HTML 单文件课件 / python-pptx / md_to_docx 脚本） | 传统 Office 格式出片的版式保真度 | 否 |
| 微软 Edge TTS 在线服务（text-to-speech） | 需联网访问微软服务 | 网络不可达时无法合成音频 | 仅 text-to-speech | 否 |
| `requirements.lock` 所列 PyPI 依赖 | 能访问 PyPI 且所列版本存在 | 单包安装失败会中断 `setup` 对应项 | Python 依赖层对应技能 | 视技能而定 |

## 已知限制

- **crawler 前端需手动启用**：`setup` 不代为安装 / 加载浏览器扩展，装包后须按「安装必读」手动完成；未完成前 crawler 前端能力不可用。
- **语音合成依赖微软在线服务**：`text-to-speech` 走微软 Edge TTS，需联网；离线环境不可用。
- **传统 Office 出片依赖平台官方技能**：.pptx / .docx / .xlsx 传统格式优先委托宿主平台官方办公技能；未安装时本包自带路径（HTML 单文件课件 / 脚本转换）在版式保真度上弱于平台官方技能。
- **文献蒸馏批处理已跨平台**：`literature-distiller` 的 `distill_batch.py` 只做批量提取编排，Linux / macOS / Windows 原生环境均可直接运行（`python distill_batch.py --help`）；同目录的 `distill_batch.sh` 仅为 POSIX 便捷入口，内部转发到 `.py`。PDF 解析依赖缺失时，改走 `material-extractor` 单篇提取流程。
- **材料提取的署名横幅**：`material-extractor` 的第三方来源 banner 优先读取包内资源 `banner.txt`；该文件未随包时，运行时**回退输出一行文字署名**（上游 virgiliojr94，MIT），不再静默跳过。署名与完整许可全文另见 `skills/material-extractor/LICENSE.md`，不影响正文提取结果。
- **依赖版本需可安装**：`requirements.lock` 为**精确锁定声明**（每行 `==`），安装期要求所 pin 版本在 PyPI 可用；`setup.py` 按分组区间安装并对单包失败容错重试。二者**包集合**由 `scripts/verify.py` 的「依赖口径一致」节机器校验（lock 须覆盖 `setup.py` 的全部安装项），防止两处清单各自漂移。

## 术语与命名表

| 名称 | 用途 | 取值 |
|------|------|------|
| `teaching-helper-team` | 插件唯一标识（`plugin.json` 的 `name` / `plugin` / 目录名） | kebab-case ID，勿改 |
| 教学帮帮团 · Teaching Helper Team | 团队展示名（`displayName`）与职业头衔（`profession`）**二者取值一致** | 平台 Team 型要求 profession == displayName |
| 齐帮办 / Qi Bangban | 主理人花名（`agentName` = teaching-helper-team-lead） | 教学编排总监 |
| 安志远 / 陈叙真 / 柯明纲 / 项承文 / 闻纪清 / 裴演 / 声入微 / 周慎导 | 8 位领域专家花名（对应 `agents/` 目录的成员定义文件） | 卡片昵称 ≤15 字符 |
| 康乃馨 / Carnation Tutor | **1.0.0 之前的弃用别称** | 已按官方 Team 型规范移除；勿再作为并列正式名 |

> 命名口径：专家（Agent ID）与领域技能目录名一一对应，唯一例外为 `grant-writer` 对应 `edu-grant-writer`。

## 版权与使用规范

本专家包以 **MIT 许可证**发布（全文见 `LICENSE`）。MIT 允许自由使用、复制、修改、合并、发布、分发、再许可与销售，**唯一条件**是在软件的所有副本或实质性部分中保留原始版权声明与本许可声明。个人教学与科研使用可直接安装；商业使用、二次分发与衍生作品**无需另行授权**，但须保留上述版权与许可声明。
