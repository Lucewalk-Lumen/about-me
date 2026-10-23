# 包结构 · 教学帮帮团

版本 1.0.2｜9 位成员｜18 项技能（16 项顶层技能 + 2 项内置扩展）

## 顶层

```
  .codebuddy-plugin/
CHANGELOG.md
LICENSE
README.md
STRUCTURE.md
  agents/
  avatars/
  scripts/
requirements.lock
settings.json
  skills/
```

## 技能（按层）

全包 18 项技能 = 16 项顶层技能 + 2 项内置扩展（`textbook-chapter-expansion` 内置于 `course-builder`、`literature-distiller` 内置于 `thesis-mentor`）；`skills/_shared` 为共享契约目录，不计入技能数。

> 说明：上述 2 项扩展在**磁盘上是与其余技能并列的顶层目录**，`plugin.json` 的 `skills` 数组亦按顶层声明；「内置」仅表示**能力归属**（分别由 thesis-mentor / course-builder 编排使用），非物理嵌套。

### 基础能力层（5 项）

- `content-summary` — 总结 URL、本地文件、PDF、图片、音频与 YouTube 内容（多模型 CLI）。用于素材准备阶段的快速总结与要点提取，产出喂给纪要整理专家、案例写作专家、论文辅导专家。
- `crawler` — 爬虫采集（双模式：后端 requests 静态采集 + 前端 bsk 已登录会话浏览器采集），由主理人按选型决策树路由。服务案例、论文、课程、纪要等专家的素材采集。
- `knowledge-wiki` — 用 LLM 构建并维护个人知识库：将原始资料增量编译为持久、互链的 Markdown 知识库。适用于创建知识库、搭建个人 wiki、整理研究笔记、导入文档或维护长期演化的知识库。
- `long-manuscript-core` — 将大纲、访谈、笔记、部分草稿与成稿推进为长文档。覆盖资料激活、限定范围续写与修订、成稿收尾三大场景。
- `material-extractor` — 材料提取：将教材、专著、PDF、EPUB、DOCX、HTML、RTF、TXT 等多源素材确定性提取为结构化全文与元数据（页数/词数/章节/目录）。作为 course-builder、case-writer、thesis-mentor、long-manuscript-core 的上游素材生产器。

### 质量门禁层（2 项）

- `citation-integrity` — 引用保真校验清单：规定一条引用怎么算核过、AI 编造引用有哪些特征、核不出来怎么标注处置、整篇论文的参考文献怎么批量走一遍。thesis-mentor 与 case-writer 交付前必读。
- `deai-rules` — 去AI味四层规则库：英文通用层（24 类英文 AI 高频模式）+ 中文通用层（高频词表/四类高频病灶/标点硬约束）+ 文体专用层（案例 L1/L2 门禁、纪要 TEEL）+ 量化诊断层（统计信号/三级词汇/交付门槛）。用于所有交付文档的自然化改写门禁。

### 领域技能层（8 项）

- `architect` — 通用 Agent / Skill 生产级制作、校验与交付工作流（平台无关，已对齐 WorkBuddy）。交互式收集需求，设计职责边界、上下文与错误恢复，产出可直接安装的技能包。
- `case-writer` — 高校教学案例、课程思政案例与工商管理案例写作（四路径：教学案例/课程思政/融入思政/工商管理案例）。含八要素深度标准、思政元素映射、引用保真四铁律、去AI味门禁与 md_to_docx 转换。
- `course-builder` — 面向高校教师的课程建设全流程：知识框架梳理、教学设计（课程大纲/单元设计/课时教案）、教材讲义编制、教学课件制作、内容质量审校。内置 UbD 逆向设计、OBE 成果导向、ADDIE、布鲁姆分类法等方法论。
- `edu-grant-writer` — 教育课题申报助手：帮助学科教师完成市级/省级/国家级教育课题申报书，将教学实践经验转化为评审认可的学术表述，按章节生成草稿并提供质量检测。
- `minutes-organizer` — 学术会议纪要与综述报告智能生成：扫描本地会议文件夹（转录稿/PPT 照片/议程 PDF），完成 OCR 与内容归类，产出会议纪要（按主题-汇报人复述）与学术综述报告（按议题重组、三层评述），先出 Markdown 供确认再生成 Word。
- `ppt-maker` — 教学课件 / 演讲文稿制作与修改：默认零依赖单文件 HTML（自包含、免装 PowerPoint、双屏演讲者模式 + 主题换肤、可导出 PDF）；需要 .pptx / .pdf 等传统格式时优先委托平台官方办公技能出片。
- `text-to-speech` — 免费语音合成：微软 Edge TTS（40+ 语言 300+ 声音），支持 rate/pitch/volume 精细控制，输出 MP3 + SRT 字幕。零成本做课程/汇报/答辩音频。
- `thesis-mentor` — 管理学本科毕业论文六阶段全程辅导：启动诊断、选题评估、文献综述、研究设计、论文写作、修改定稿；扩展期刊投稿、审稿回应与答辩分享；含图表引擎与真实文献轻量索引。

### 初始化层（1 项）

- `setup` — 教学帮帮团一键初始化：装包后/首次会话/用户要求初始化时触发，统一安装全部运行时依赖（Python 托管 venv + Node docx）、检测 crawler 的 bsk CLI、生成 `.env` 凭证占位模板（仅占位、不含任何真实密钥），并写入初始化状态供主理人幂等判断。

### 内置扩展（2 项）

- `literature-distiller` — 论文文献速览与蒸馏：支持本地 PDF，通过 4+2 深度蒸馏模型提取元数据、逻辑骨架、核心发现与批判性洞察，生成结构化 Markdown 报告并归档本地知识库（内置于 thesis-mentor）。
- `textbook-chapter-expansion` — 教材/书籍/长文档薄弱章节的批量补齐：三路并行差距扫描 → 多 Agent 并行扩充 → 锚点注入正文 → 素材分层回填 → 一致性验证 → docx 导出（内置于 course-builder）。

## 共享契约

- `skills/_shared/DATA-CONTRACT.md`：技能间数据交换契约（数据总线目录、流水线顺序、输入输出接口）

> `_shared/` 是**共享契约目录，不是技能**，故不在 `plugin.json` 的 `skills` 数组中声明，也不为其新增 SKILL.md。

## 依赖

统一声明于包根 `requirements.lock`（精确锁定）；可选依赖见文件末尾注释。
