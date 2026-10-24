# EndNote 文献分析团（EndNote Literature Analysis Team）

在**无官方 API** 的约束下分析本地文献库，并基于分析结果一键生成文献综述骨架。
EndNote 未开放开发者 API，本工具通过直接读取 `.enl`（SQLite 格式）与常见文献导出格式
实现库级知识发现，**全程只读，绝不修改源库**。

## 团队构成（3 名 agent，专家团）

本包为**专家团**（`expertType: "team"`）：主理人 1 名 + 成员 2 名，
主理人由 `settings.json` 指定。

| Agent ID | 名字 | 角色 | 职责 |
|---|---|---|---|
| `endnote-analysis-team-lead` | 析文 | 文献计量分析负责人 | 编排全流程：来源判定、数据体检、主题聚类与演化、共现网络构建、F1–F4 扩展分析、稳健性与效应量检验、汇编交付 |
| `network-mapper` | 织网 | 共现网络解读师 | 分簇岛布局、色觉安全配色、Canvas 渲染参数、桥接词与簇结构判读、R 交叉验证结果解读 |
| `review-outliner` | 构纲 | 文献综述提纲设计师 | 消费分析 JSON，一键生成结构化文献综述骨架（引言地图、按主题综合、研究空白与新颖性、论证脚手架、质量清单） |

协作铁律：主理人必须 TeamCreate → Agent 调度 → SendMessage 回传，成员之间不直连。

## 能力一览

| 功能 | 说明 |
|---|---|
| **多来源导入** | Zotero 原生库（`zotero.sqlite` 只读直读，**无需导出**）/ RIS / BibTeX / EndNote tagged / EndNote XML / NoteExpress `.net` / CNKI XML / CNKI GB7714 / WoS·Scopus CSV / WoS HTML·Excel / Zotero RDF / Better BibTeX JSON；跨来源自动去重 |
| 数据体检 | 报告数据质量缺口：多少条无摘要/无关键词/含水印/无 PDF |
| 主题聚类 | TF-IDF + NMF，K 按「最小簇占比≥3%」自动判定，中英分流分词 |
| 主题×年份演化 | 揭示主题热度拐点（不是复刻 EndNote 自带年份统计） |
| 关键词共现网络 | 分簇岛布局 + 色觉安全配色 + Canvas 渲染（**注意：非引文网络**） |
| 跨语言桥接 | 发现中英文研究同一议题的关联 |
| **F1 阅读状态** | 未读/待读清单：`read_status='1'`=已读，其余计未读；可导出 CSV |
| **F2 重复检测** | 标题精确重复 + DOI 碰撞 + 同刊同年近似重复（difflib，阈值可调） |
| **F3 时效性预警** | 年份分布、近三年占比、早于 2019 占比、缺失年份占比、最旧文献（基准年=库内最新年） |
| **F4 主题×作者矩阵** | 每主题核心作者、全局核心作者、作者×主题热力矩阵 |
| **主题×时期效应量** | Cramér's V + η² 回答「各主题年份分布是否真有差异」，附占比变化与 95% bootstrap CI |
| **关键词突现检测** | 找出「正在快速升温」的概念：峰值年 df 相对基线均值的突现倍数 + 强度 + 置信度（**keyword burst，非 citation burst**） |
| **K 稳健性检验** | 换 K / 换种子 / 换语料三层检验（ARI + Cramér's V），附 95% bootstrap 置信区间 |
| **三线表导出** | `--sanxian` 输出中文期刊三线表（三线无竖线、数字右对齐、注行规范），可粘入 Word |
| **导出到 VOSviewer/CiteSpace** | 一键产出 Pajek `.net` + CiteSpace 节点/边 CSV，附建网参数口径，可直接进成熟工具做交互式探索 |

主题数 K 不硬编码：按「每个主题至少占全库 3%」规则扫描 K=4..40 判定。
K 值调整是用户的学术判断，工具只显示失衡指标、不自动改。

## 与官方工具的差异

截至 EndNote 2025.3（Clarivate 官方发布说明），EndNote 内置的 Research Assistant
与 AI 功能集中在**单文档级**：Chat with your document、Translate your document、
Key Takeaways（摘要）、结构化提纲，以及 Cite from a PDF、Find a Journal。
**没有任何库级聚类、主题网络、共现分析**。本工具专注这一层。

因无 API，无法做**引文网络 / 共被引图** —— 本地 `references` 字段是空占位符。
报告提供的是**关键词共现网络**，回答"概念之间有什么关联"。

## 设计原则（两条铁律 + 三条边界）

1. **源库绝对只读** —— `mode=ro` + `query_only`；写源库需绕过 3 道锁 + 13 个依赖私有函数的触发器 → 结构性不可能。
2. **零静默丢弃** —— 每条记录归入某个 tier，四类之和 == 记录总数。
3. **网络后端 Python 优先、R 可选** —— 共现网络布局与渲染纯 Python（numpy FR），不依赖 R；R 仅在用户已安装时作可选交叉验证，缺失时自动兜底并 exit 0。
4. **剔除引文信息** —— 从外部技能借鉴能力时，已剥离 GB/T 7714 / APA / 参考文献列表等引文格式化与引用管理；综述骨架仅给结构，引文落地请用专用引文工具。
5. **不编造** —— 所有作者、年份、关键词、趋势均来自分析产物；缺失维度标注"未提供"，绝不用记忆或常识补齐。

## 快速开始

```bash
S=skills/endnote-analysis/scripts     # 脚本目录
R=skills/review-skeleton/scripts     # 综述骨架脚本目录

# 0. 环境自检（必做；退出码 8 = 环境不满足）
python3 $S/doctor.py

# 1. 扫描体检（可传文件夹或 .enl 路径）
python3 $S/scan_library.py "你的文献库目录"

# 2. 主题聚类 + 演化（--k 可省略，按「最小簇占比≥3%」自动判定）
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
    --sanxian ./out/sanxian.html --out report.html

# 7. 导出到 VOSviewer / CiteSpace（可选，用于交互式探索）
python3 $S/export_vosviewer.py --network ./out/network.json --format all --out ./out

# 8. 一键综述骨架（由成员 review-outliner 调用）
python3 $R/build_skeleton.py --topics ./out/topics.json \
    --evolution ./out/evolution.json --author-topic ./out/author_topic.json \
    --network ./out/network.json --age ./out/age.json --dup ./out/dup.json --out skeleton.md
```

### 没有 EndNote？先导入

```bash
# 支持 Zotero 原生库 / RIS / BibTeX / EndNote tagged+XML / NoteExpress .net /
#      CNKI XML / CNKI GB7714 / WoS·Scopus CSV·HTML·Excel / Zotero RDF / Better BibTeX JSON
python3 skills/endnote-analysis/scripts/import_sources.py <文件或目录…> \
    --dedup --out ./out/refs.json --csv ./out/refs.csv

# 之后把上面每条命令的 "你的文献库目录" 换成 ./out/refs.json，其余参数不变
```

下游 6 个模块经 `endnote_core.load_refs()` 透明接受 `.enl` 或 `refs.json`，**代码零分叉**。
⚠️ CNKI 的 `.es6` 是客户端加密导出（`XCNKI_ENCRYPT`），无密钥不可解析 ——
工具会明确报错并指引改用 RIS / EndNote XML / BibTeX，绝不静默返回 0 条。

详见 `skills/endnote-analysis/SKILL.md` 与 `skills/review-skeleton/SKILL.md`。

## 报告里的网络图怎么用

报告的共现网络图是自包含的 Canvas，无需联网，直接双击 HTML 即可打开。

**三种视图**（快捷键 `1`/`2`/`3` 或工具栏按钮）：

| 视图 | 回答什么问题 |
|---|---|
| **主题着色**（默认） | 哪些概念抱团、哪些是跨主题的桥接词 |
| **时间叠加** | 哪些区域是近期新出现的（黄）vs 长期存在的（蓝） |
| **密度视图** | 整体结构与核心聚集区在哪 |

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
     ⚠️ 第 1 层挡不住这一层：`JSON.parse` 会把 `\u003c` 还原回 `<`。
     独立复审实测关键词 `<img src=x onerror=alert(1)>` 曾**首屏零点击**触发。
  3. **CSV** —— 全部导出点对 `=`/`+`/`-`/`@` 开头（含前导空白）的文本前置单引号（`esc_csv_cell`）
- **本包不含任何用户文献数据**（详见 `skills/endnote-analysis/references/DATA_NOT_INCLUDED.md`）

## 回归测试

```bash
python3 skills/endnote-analysis/scripts/run_checks.py            # 138 项，约 40 秒，不需真实库
python3 skills/endnote-analysis/scripts/run_checks.py --full     # 含真实库全链路
```

每条检查对应一项必须长期保持的行为约束（详见 `SKILL.md`）；调整布局、配色、导入器或统计量后请重跑。

## 安装

```
numpy>=1.24  scipy>=1.10  scikit-learn>=1.3  jieba>=0.42  xlrd>=2.0
```

- `xlrd` 仅 `.xls`（OLE2/BIFF8）需要；`.xlsx` 请用 `openpyxl` 或先另存 `.xls`
- **不需要 networkx** —— 布局用纯 numpy 实现
- **可选 R ≥4.2 + igraph ≥2.0**（仅用于交叉验证）。v0.3.1 已在
  R 4.6.1 + igraph 2.3.3 上实跑通过；R 缺失时自动回退纯 Python 并 exit 0
- 本机可能存在多个 Python 3.13 环境但依赖不同，请先运行 `doctor.py` 确认解释器

安装问题见 `skills/endnote-analysis/SKILL.md`。
