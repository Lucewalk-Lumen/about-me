# 学术文献计量分析团（Academic Literature Analysis Team）

> 版本 1.0.1 · 变更见 `CHANGELOG.md`，能力与安装要点见 `UPGRADE.md`

**离线只读**分析本地文献集合，并基于分析结果一键生成文献综述骨架。

支持 14 种题录来源：EndNote（`.enl` SQLite 直读）/ Zotero（`zotero.sqlite` 直读，
**无需导出**）/ NoteExpress / CNKI（XML·GB7714）/ WoS / Scopus / BibTeX / RIS / CSV 等
（万方 · 维普请先导出为 RIS / EndNote XML）。

**全程只读，绝不修改源库**；不与文献管理软件对接、不回写、不联网。

## 数据源中立

EndNote 只是最常见的入口，**本包不依赖它**。你手上的题录来自哪个软件都能分析——
包括只导出了 RIS/BibTeX 的情况。

## 团队构成（5 名 agent，专家团）

本包为**专家团**（`expertType: "team"`）：主理人 1 名 + 成员 4 名，
主理人由 `settings.json` 指定。

| Agent ID | 名字 | 角色 | 职责 |
|---|---|---|---|
| `academic-lit-analysis-lead` | 析文 | 文献计量师 | 编排全流程；**先问后算**（澄清来源/目的/范围再执行）；汇编交付 |
| `data-auditor` | 见核 | 数据核查师 | 字段覆盖/重复/时效/缺年份核查；判断**这份数据能支撑什么结论、不能支撑什么** |
| `trend-analyst` | 鉴势 | 趋势分析师 | 发文量、逐年趋势、拐点、突现词、概念进入时序 |
| `network-mapper` | 织网 | 共现解读师 | 分簇岛布局、色觉安全配色、Canvas 渲染参数、桥接词与簇结构判读 |
| `review-outliner` | 构纲 | 综述提纲师 | 消费分析 JSON，一键生成结构化文献综述骨架（引言地图、研究空白、论证脚手架、质量清单） |

> 分工理由：文献计量最危险的失败模式**不是算错，而是用残缺数据得出看似笃定的结论**。
> 见核负责拦住这类问题，鉴势负责时间维度，两者职责不重叠。

协作铁律：主理人必须 TeamCreate → Agent 调度 → SendMessage 回传，成员之间不直连。

## 能力一览

| 功能 | 说明 |
|---|---|
| **多来源导入** | Zotero 原生库（`zotero.sqlite` 只读直读，**无需导出**）/ RIS / BibTeX / EndNote tagged / EndNote XML / NoteExpress `.net` / CNKI XML / CNKI GB7714 / WoS·Scopus CSV / WoS HTML·Excel / Zotero RDF / Better BibTeX JSON；跨来源自动去重 |
| 数据体检 | 报告数据质量缺口：多少条无摘要/无关键词/含水印/无 PDF |
| 主题聚类 | TF-IDF + NMF，K 按「最小簇占比≥3%」自动判定，中英分流分词 |
| 主题×年份演化 | 揭示主题热度拐点（不是复刻 EndNote 自带年份统计） |
| 关键词共现网络 | 分簇岛布局 + 色觉安全配色 + Canvas 渲染；节点=关键词，回答"概念之间有什么关联" |
| 作者共现网络 | 节点=作者、边=同篇合作；按**合作群（连通分量）**着色，识别核心作者与合作团队 |
| 机构共现网络 | 节点=机构、边=同篇合作；按**共现社群**着色，中英文同名机构已归一 |
| 引文共现网络 | 共被引 / 文献耦合；节点=参考文献，依赖题录带 references 字段（WoS/Scopus/BibTeX 具备，EndNote .enl 无） |
| 跨语言桥接 | 发现中英文研究同一议题的关联 |
| **F1 阅读状态** | 未读/待读清单：`read_status='1'`=已读，其余计未读；可导出 CSV |
| **F2 重复检测** | 标题精确重复 + DOI 碰撞 + 同刊同年近似重复（difflib，阈值可调） |
| **F3 时效性预警** | 年份分布、近三年占比、早于 2019 占比、缺失年份占比、最旧文献（基准年=库内最新年） |
| **F4 主题×作者矩阵** | 每主题核心作者、全局核心作者、作者×主题热力矩阵 |
| **主题×时期效应量** | Cramér's V + η² 回答「各主题年份分布是否真有差异」，附占比变化与 95% bootstrap CI |
| **关键词突现检测** | 找出「正在快速升温」的概念：峰值年 df 相对基线均值的突现倍数 + 强度 + 置信度（**keyword burst，非 citation burst**） |
| **K 稳健性检验** | 换 K / 换种子 / 换语料三层检验（ARI + Cramér's V），附 95% bootstrap 置信区间 |
| **三线表导出** | `--sanxian` 输出中文期刊三线表（三线无竖线、数字右对齐、注行规范），可粘入 Word |
| **发文量与趋势** | 总发文量、逐年分布、高峰年、趋势方向、拐点年份；支持 `--topic` 只分析单个主题的题录 |
| **多维交叉共现** | 关键词×作者、关键词×年份、作者×年份三个交叉表；用 Cramér's V / NMI 衡量关联强度，避免把高频共现误读成强关联 |
| **PDF 全文提取** | 从 EndNote 附件或指定目录定位 PDF，抽取摘要与关键词回填题录（仅补空缺）；中文 PDF 优先用 PyMuPDF，缺依赖优雅降级 |
| **视图渲染自检** | 自动驱动四个视图并断言"确实画出了东西"+ 来回切换不抛异常，防「切换后整页空白」类问题 |
| **依赖引导** | `doctor.py --install` 授权后自动装依赖（含 R 包 igraph）；R + igraph 是**必需前置条件**，缺失即环境不满足 |
| **导出到 VOSviewer/CiteSpace** | 一键产出 Pajek `.net` + CiteSpace 节点/边 CSV，附建网参数口径，可直接进成熟工具做交互式探索 |
| **一键导出全套产物** | `export_all.py` 把产物目录整套整理成交付物：各网络节点/边表 CSV、主题/发文/突现/SNA/交叉表、三线表 HTML、`summary.json`、每个网络的 VOSviewer/CiteSpace 三件套，并生成 `EXPORT_README.md` 索引；缺产物跳过+记录、幂等可覆盖。**只搬运不重算** |

主题数 K 不硬编码：按「每个主题至少占全库 3%」规则扫描 K=4..40 判定。
K 值调整是用户的学术判断，工具只显示失衡指标、不自动改。

## 与官方工具的差异

截至 EndNote 2025.3（Clarivate 官方发布说明），EndNote 内置的 Research Assistant
与 AI 功能集中在**单文档级**：Chat with your document、Translate your document、
Key Takeaways（摘要）、结构化提纲，以及 Cite from a PDF、Find a Journal。
**没有任何库级聚类、主题网络、共现分析**。本工具专注这一层。

报告提供四类共现网络：**关键词共现**（概念怎么关联）、**作者共现**（谁和谁合作）、
**机构共现**（跨机构合作结构）、**引文共现**（共被引 / 文献耦合，知识基础聚类）。
前三类只需题录本身（关键词 / 作者 / 机构字段），**不需要**引文数据；
**引文网络依赖题录带参考文献（references / Cited-References）字段**——WoS / Scopus / 含参考文献的
BibTeX 具备，EndNote 本地库（`.enl`）的 `references` 是占位符故不构建。因无 API，本工具
**不能做"文献级引用追踪"**（哪篇引了哪篇），那是引文索引数据库的能力。

## 设计原则（两条铁律 + 三条边界）

1. **源库绝对只读** —— `mode=ro` + `query_only`；写源库需绕过 3 道锁 + 13 个依赖私有函数的触发器 → 结构性不可能。
2. **零静默丢弃** —— 每条记录归入某个 tier，四类之和 == 记录总数。
3. **SNA 用 R 标准路径（必需）** —— 共现网络布局与渲染纯 Python（numpy FR），不依赖 R；但中心性 / 社区发现 / 模块度等社会网络分析（SNA）由 R + igraph 完成，是**必需的标准路径**：计量分析要有标准工具链，结果才可复现。缺失时 `sna_r.py` 直接失败并给出安装指引，不再静默回退纯 Python。
4. **剔除引文信息** —— 从外部技能借鉴能力时，已剥离 GB/T 7714 / APA / 参考文献列表等引文格式化与引用管理；综述骨架仅给结构，引文落地请用专用引文工具。
5. **不编造** —— 所有作者、年份、关键词、趋势均来自分析产物；缺失维度标注"未提供"，绝不用记忆或常识补齐。

## 快速开始

> [!] 以下命令均用**相对专家团根目录**的路径书写。请先 `cd` 到包含
> `.codebuddy-plugin/` 的那一层再执行，否则会报 `No such file or directory`。

```bash
S=skills/academic-lit-analysis/scripts     # 脚本目录
R=skills/review-skeleton/scripts     # 综述骨架脚本目录

# 0. 环境自检（必做；退出码 8 = 环境不满足）
python3 $S/doctor.py

# 1. 扫描体检（可传文件夹或 .enl 路径）
python3 $S/scan_library.py "你的文献库目录"

# 2. 主题聚类 + 演化（--k 可省略，按「最小簇占比≥3%」自动判定）
#    （命令省略，后续步骤同）
python3 $S/cluster_topics.py "你的文献库目录" --k 14 --out ./out

# 3. 共现网络（+ 主题着色 + 预计算布局）
python3 $S/build_network.py "你的文献库目录" --node-df 5 --min-edge 2 \
    --topics ./out/topics.json --layout --out ./out

# 4. 扩展分析（4 项本地功能，输出 JSON，均可独立运行）
python3 $S/reading_status.py "你的文献库目录" --workspace ./ws --top 50 > ./out/reading.json
python3 $S/dup_check.py      "你的文献库目录" --workspace ./ws --out ./out
python3 $S/age_warning.py    "你的文献库目录" --workspace ./ws --out ./out
python3 $S/author_topic.py   "你的文献库目录" --topics ./out/topics.json --workspace ./ws --out ./out

# 5. 稳健性、效应量与突现（投稿向）
python3 $S/robust_k.py      "你的文献库目录" --ladder 8,12,14,16,20 --out ./out
python3 $S/trend_effects.py "你的文献库目录" --topics ./out/topics.json --out ./out
python3 $S/burst_detection.py "你的文献库目录" --window 3 --min-total 3 --out ./out

# 6. 生成报告（集成全部产物）
python3 $S/build_report.py --topics ./out/topics.json \
    --network ./out/network.json --evolution ./out/evolution.json \
    --reading ./out/reading.json --dup ./out/dup.json --age ./out/age.json \
    --author-topic ./out/author_topic.json --sna-r ./out/sna_r.json \
    --trend ./out/trend_effects.json --bursts ./out/bursts.json \
    --pub-stats ./out/publication_stats.json --cross ./out/cross_matrix.json \
    --keyword-network ./out/keyword_network.json \
    --author-network ./out/author_network.json \
    --institution-network ./out/institution_network.json \
    --citation-network ./out/citation_network.json \
    --sanxian ./out/sanxian.html --out report.html

# 7. 导出到 VOSviewer / CiteSpace（可选，用于交互式探索）
python3 $S/export_vosviewer.py --network ./out/network.json --format all --out ./out

# 8. 一键导出全套产物（标准收尾：把所有产物整理成带索引的交付物）
python3 $S/export_all.py --dir ./out          # 产出到 ./out/export

# 9. 一键综述骨架（由成员 review-outliner 调用）
python3 $R/build_skeleton.py --topics ./out/topics.json \
    --evolution ./out/evolution.json --author-topic ./out/author_topic.json \
    --network ./out/network.json --age ./out/age.json --dup ./out/dup.json \
    --out skeleton.md --docx skeleton.docx
```

### 题录来自其他软件？先导入

```bash
# 支持 Zotero 原生库 / RIS / BibTeX / EndNote tagged+XML / NoteExpress .net /
#      CNKI XML / CNKI GB7714 / WoS·Scopus CSV·HTML·Excel / Zotero RDF / Better BibTeX JSON
python3 skills/academic-lit-analysis/scripts/import_sources.py <文件或目录…> \
    --dedup --out ./out/refs.json --csv ./out/refs.csv

# 之后把上面每条命令的 "你的文献库目录" 换成 ./out/refs.json，其余参数不变
```

下游各模块经 `lit_core.load_refs()` 透明接受 `.enl` 或 `refs.json`，**代码零分叉**。
[!] CNKI 的 `.es6` 是客户端加密导出（`XCNKI_ENCRYPT`），无密钥不可解析 ——
工具会明确报错并指引改用 RIS / EndNote XML / BibTeX，绝不静默返回 0 条。

详见 `skills/academic-lit-analysis/SKILL.md` 与 `skills/review-skeleton/SKILL.md`。

## 报告里的网络图怎么用

报告的共现网络图是自包含的 Canvas，无需联网，直接双击 HTML 即可打开。

**四种视图**（快捷键 `1`/`2`/`3`/`4` 或工具栏按钮）：

| 视图 | 回答什么问题 |
|---|---|
| **主题着色**（默认） | 哪些概念抱团、哪些是跨主题的桥接词 |
| **时间叠加** | 哪些区域是近期新出现的（黄）vs 长期存在的（蓝） |
| **密度视图** | 整体结构与核心聚集区在哪 |
| **时间线**（CiteSpace 风格年轮） | 概念的时空分布：哪个主题在哪几年集中出现 |

> 报告含**四类网络**：关键词共现、作者共现、机构共现、引文共现（后三类仅当数据源支持时出现）。
> 每类都是独立 Canvas，操作（拖动/缩放/导出 PNG·SVG）通用；**只有关键词共现网络**带
> 「主题着色 / 时间叠加 / 密度 / 时间线」四种视图切换，其余三类按各自语义着色（合作群 / 共现社群）。

**操作**（桌面与手机通用，均已实测）：

- **手机**：单指拖动平移或微调节点 · **双指捏合缩放** · 点按看详情 · 双击复位
  （页面纵向滑动仍可正常滚动阅读，横向手势才作用于画布）
- 滚轮或 `+` `-` 缩放（0.12×–9×）· 拖空白平移
- **拖动节点可手动微调位置**（邻居跟随 35%，保持局部结构），随时按 `R` 或点「复位节点位置」回到原始布局
- 点击节点高亮其邻居 · 双击或 `0` 复位视口 · `Esc` 取消选中
- **导出 PNG**（2x 高清）/ **导出 SVG**（矢量，可无限放大）—— 直接用于论文配图

> 手动调整只改显示偏移，不改算法布局，因此导出的图与你看到的完全一致，且可随时复位。

## 数据安全

- 以 SQLite `mode=ro` + `query_only` 打开，源库**零写入**
- 分析在影子副本上进行，规避可移动硬盘掉盘与文件锁
- 报告输出路径脱敏（仅显示文件名）
- `notes`（私人笔记）与 `author_address`（含邮箱）默认不导出
- **输出加固（三层，缺一层即失效）**：
  1. **`<script>` 边界** —— HTML 报告内联 JSON 转义 `<`/`>`/`&` 与 U+2028/9（`esc_json`）
  2. **DOM sink** —— JS 侧凡把外部数据写进页面处一律用 `textContent` /
     `createElement` / `setAttribute`，**禁止 innerHTML 拼字符串**。
     [!] 第 1 层挡不住这一层：`JSON.parse` 会把 `\u003c` 还原回 `<`。
     实测关键词 `<img src=x onerror=alert(1)>` 会**首屏零点击**触发。
  3. **CSV** —— 全部导出点对 `=`/`+`/`-`/`@` 开头（含前导空白）的文本前置单引号（`esc_csv_cell`）
- **本包不含任何用户文献数据**（详见 `skills/academic-lit-analysis/references/DATA_NOT_INCLUDED.md`）

## 回归测试

```bash
python3 skills/academic-lit-analysis/scripts/run_checks.py            # 实测 234 项，约 2 分钟，不需真实库
python3 skills/academic-lit-analysis/scripts/run_checks.py --full     # 含真实库全链路
```

每条检查对应一项必须长期保持的行为约束（详见 `SKILL.md`）；调整布局、配色、导入器或统计量后请重跑。

## 安装

```
numpy>=1.24  scikit-learn>=1.3  jieba>=0.42  xlrd>=2.0  pymupdf>=1.24  pypdf>=4
```

- `xlrd` 仅 `.xls`（OLE2/BIFF8）需要；当前版本不支持 `.xlsx`，请先另存为 `.xls` / `.csv`
- **不需要 networkx** —— 布局用纯 numpy 实现
- **必需 R ≥4.2 + igraph ≥2.0** —— 社会网络分析（SNA）的标准路径。已在
  标准 R + igraph 环境实跑通过；缺失时 `sna_r.py` 直接失败并给出安装指引
  （Windows 下 R 默认不写 PATH，工具会按常见安装目录兜底探测）；
  仅当显式传 `--allow-python-fallback` 才降级为纯 Python，且产物标注为非标准路径
- 本机可能存在多个 Python 3.13 环境但依赖不同，请先运行 `doctor.py` 确认解释器

安装问题见 `skills/academic-lit-analysis/SKILL.md`。
