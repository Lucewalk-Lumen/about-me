# 学术文献计量分析

**离线只读**分析本地文献集合：主题聚类、发文趋势、共现网络、多维交叉、综述骨架。

## 这个包做什么 / 不做什么

| 做 | 不做 |
|---|---|
| 只读解析本地题录（14 种格式） | 不与文献管理软件对接、不回写 |
| 主题聚类 / 演化 / 突现 / 多维交叉 | 不联网、不抓取外部数据 |
| 生成单文件 HTML 报告 | 不上传任何数据 |
| 综述骨架生成 | 不代写论文正文 |

> **数据源中立**：EndNote / Zotero / NoteExpress / CNKI / WoS / Scopus / BibTeX / RIS 都能分析。
> EndNote 只是最常见的入口，本包不依赖它。

## 先问再算（重要）

拿到文献数据后**先澄清四件事**，再决定跑哪些分析：

1. **数据来源**：EndNote 库路径，还是导出的题录文件？
2. **分析目的**：想回答什么？（研究什么/ 在往哪走 / 关键词怎么关联 / 库有什么问题 / 写综述）
3. **是否要全量**：整库还是只看某个主题（`--topic` 可单主题分析）。
4. **是否读取 PDF 全文**（默认**否**）：仅当摘要/关键词缺失多或用户明确要求「基于全文」时才读
   （`pdf_extract.py`，耗时随库规模线性增长）。**必须显式问，不得默认读取。**

不同目的对应差别很大的分析项，全量跑完用户往往只用到一小部分。

## 快速开始

> [!] **所有命令的前提：在本专家团根目录（即包含 `.codebuddy-plugin/` 的那一层）执行。**
> 下面的命令一律用 `skills/academic-lit-analysis/scripts/...` 全路径书写，
> 这样无论当前工作目录在哪都能直接跑通。若你此刻在别的目录，请先
> `cd` 到本专家团根目录 —— 相对路径写法（`python3 scripts/xxx.py`）
> 会在非根目录下报 `No such file or directory`。

### 情形 A：已有本地题录库（直接分析）

```bash
# 0. 环境自检（必做）
python3 skills/academic-lit-analysis/scripts/doctor.py

# 1. 扫描体检（可传文件夹或 .enl 路径）
python3 skills/academic-lit-analysis/scripts/scan_library.py "~/文稿/文献"

# 2. 主题聚类（必须先跑 —— 共现网络的主题着色依赖它的输出）
#    --k 可省略，按「最小簇占比≥3%」自动判定 K
python3 skills/academic-lit-analysis/scripts/cluster_topics.py "~/文稿/文献" --k 14 --out ./out

# 3. 共现网络（+ 主题着色 + 预计算布局）
python3 skills/academic-lit-analysis/scripts/build_network.py "~/文稿/文献" --node-df 5 --min-edge 2 \
    --topics ./out/topics.json --layout --out ./out

# 4. 扩展分析（4 项本地功能，输出 JSON，均可独立运行）
python3 skills/academic-lit-analysis/scripts/reading_status.py "~/文稿/文献" --workspace ./ws --top 50 > ./out/reading.json
python3 skills/academic-lit-analysis/scripts/dup_check.py      "~/文稿/文献" --workspace ./ws --out ./out
python3 skills/academic-lit-analysis/scripts/age_warning.py    "~/文稿/文献" --workspace ./ws --out ./out
python3 skills/academic-lit-analysis/scripts/author_topic.py   "~/文稿/文献" --topics ./out/topics.json \
    --workspace ./ws --out ./out

# 4.5 发文量趋势 + 多维交叉（可选，但强烈建议 —— 回答"在往哪走"）
python skills/academic-lit-analysis/scripts/publication_stats.py ./out/refs.json --out ./out
python skills/academic-lit-analysis/scripts/cross_matrix.py ./out/refs.json --out ./out
# 单主题分析：只统计某个主题的题录
python skills/academic-lit-analysis/scripts/publication_stats.py ./out/refs.json --topic "工作重塑" --out ./out

# 4.6 PDF 全文提取（可选，补全缺失的摘要与关键词）
python skills/academic-lit-analysis/scripts/pdf_extract.py ./out/refs.json --pdf-dir ~/Downloads/pdfs --out ./out --apply

# 5. 生成报告（最小示例：主题/网络/演化/扩展四项；完整可选输入见 README「快速开始」步骤 6）
python3 skills/academic-lit-analysis/scripts/build_report.py --topics ./out/topics.json \
  --network ./out/network.json --evolution ./out/evolution.json \
  --reading ./out/reading.json --dup ./out/dup.json \
  --age ./out/age.json --author-topic ./out/author_topic.json --out report.html

# 6. 一键导出全套产物（标准收尾 —— 数据表 / 三线表 / VOSviewer 互操作 / 索引）
python3 skills/academic-lit-analysis/scripts/export_all.py --dir ./out            # 产出到 ./out/export
```

### 情形 B：题录来自其他软件（Zotero / NoteExpress / CNKI / WoS / Scopus）—— 先导入

**所有下游命令都接受 `refs.json`**，把 `脚本 "<库路径>"` 换成 `脚本 ./out/refs.json` 即可，
其余参数完全不变。

```bash
# 一次性导入并归一化（可一次给多个文件/目录，自动嗅探格式）
python3 skills/academic-lit-analysis/scripts/import_sources.py ~/Downloads/CNKI-*.net ~/Downloads/CNKI-*.enw \
    --dedup --out ./out/refs.json --csv ./out/refs.csv

# 之后把上面情形 A 的每条命令的 "<库路径>" 换成 ./out/refs.json
python3 skills/academic-lit-analysis/scripts/cluster_topics.py ./out/refs.json --out ./out
python3 skills/academic-lit-analysis/scripts/build_network.py ./out/refs.json --topics ./out/topics.json --out ./out --layout
```


> [!] **SNA（社会网络分析）后端：R + igraph 为必需的标准路径。**
> 共现网络的**布局与渲染**仍是纯 Python（numpy 实现 Fruchterman-Reingold），不依赖 R；
> 但社区发现 / 中心性 / 模块度等计量分析由 `sna_r.py` 调 R + igraph 完成 ——
> 这部分**必须**有 R：缺 R 时脚本**直接失败**并给出安装指引，**不再静默回退纯 Python**。
> 理由：计量分析要有标准工具链（igraph / bibliometrix 生态），结果才可复现、可与他人的
> SNA 结果对话。仅当显式传 `--allow-python-fallback` 才降级，且产物会标为非标准路径。

> [!] **本团聚焦"分析"，不引入引文 / 参考文献格式化。** 从外部技能借鉴能力时
> 已剔除 GB/T 7714、APA、参考文献列表等引用管理功能（综述骨架仅给结构，引文落地请用专用引文工具）。


## 发文量与趋势（`publication_stats.py`）

回答最常被问的三件事：**一共多少篇、逐年多少、在扩张还是收缩**。

```bash
# 整库
python skills/academic-lit-analysis/scripts/publication_stats.py refs.json --out ./out

# 单主题（只看某一个主题的题录）
python skills/academic-lit-analysis/scripts/publication_stats.py refs.json --topic "工作重塑" --out ./out
```

产出`publication_stats.json`：

| 字段 | 含义 |
|---|---|
| `total` / `with_year` / `missing_year` | 总数 / 有年份数 / 缺年份数 |
| `per_year` | 逐年发文量 |
| `peak_year` / `peak_count` | 高峰年及篇数 |
| `trend` / `growth_pct` | 末段较首段的增减（>1.25 倍=上升，<0.8 倍=下降） |
| `turning_years` | 增速方向反转的年份（拐点） |
| `currently_growing` | 近三年是否逐年递增 |

**口径要点**

- 缺年份的题录**计入总数但不计入逐年分布**，故各年之和 ≤ 总数，报告会显式标注差额。
- 趋势用**前后段增长率**而非线性拟合——文献量小、波动大时更稳健。
- **末年数据往往不完整**（当年只过了部分月份），不要把末年下滑当趋势反转。
- `--topic` 用标题/摘要/关键词做包含匹配，能把子集单独拉出来分析。

报告用 `--pub-stats` 接入，生成「发文量与趋势」章节。

## 多维交叉共现（`cross_matrix.py`）

在「关键词共现网络」之外，补上**人—词—时**三个视角。

```bash
python skills/academic-lit-analysis/scripts/cross_matrix.py refs.json --out ./out
```

| 维度对 | 回答的问题 |
|---|---|
| 关键词 × 作者 | 谁在研究什么？（某作者的核心词 = 其研究方向） |
| 关键词 × 年份 | 概念何时兴起？（首现年 = 进入领域的时点） |
| 作者 × 年份 | 谁在何时活跃？（活跃期 = 连续发文区间） |

**关联强度口径（重要）**

- 关键词 × 作者 → **Cramér's V**：0.15 以下弱、0.3 以上较强
- 关键词 × 年份 → **NMI**：接近 0 表示各概念的年代差异不显著

[!] 交叉表只回答"一起出现过多少次"。单个组合的共现数高**不等于**有强关联——
高频词对谁都共现。判断关联必须看V / NMI，不能只看计数。

报告用 `--cross` 接入，生成「多维交叉共现」章节。

## PDF 全文提取（`pdf_extract.py`）

本包分析全部依赖题录字段（标题/摘要/关键词）。PDF 首页往往就有 Abstract 与
Keywords，补上它们等于**在不联网、不换数据源的前提下提升数据质量**。

```bash
# 指定 PDF 目录（按题目标题匹配文件名或首页内容）
python skills/academic-lit-analysis/scripts/pdf_extract.py refs.json --pdf-dir ~/Downloads/pdfs --out ./out

# 顺带把结果写回题录（仅补空缺，不覆盖已有内容）
python skills/academic-lit-analysis/scripts/pdf_extract.py refs.json --pdf-dir ~/Downloads/pdfs --out ./out --apply
```

**匹配优先级**

1. 题录自带的 `pdf_path`（本地题录库解析出的附件路径）
2. **内容级匹配**：读 PDF 首页文本，题目标题的显著片段是否出现
   （实测把 PDF 命名成 `paper_1.pdf` 时，仅靠文件名匹配命中率为 **0**）
3. 文件名模糊匹配（相似度 ≥ 0.55）

**依赖与降级**

| 情况 | 行为 |
|---|---|
| 有 PyMuPDF | 优先使用（**pypdf 读中文 PDF 会乱码**，实测抽出「錜e皥LN:」这类天书） |
| 只有 pypdf | 退回使用，纯英文 PDF 表现良好 |
| 都没有 | **不报错**，产出待安装提示，主流程照常可跑 |
| 无 PDF | 提示用 `--pdf-dir`，其余分析不受影响 |

产出 `pdf_text.json`：`records`（逐条明细）、`backfill`（可直接合并的 `{id:{abstract,keywords}}`）。

**口径**：只回填**原本为空**的字段；文本少于 `--min-chars`（默认 120）视为扫描件跳过。

## 专家团构成（5 名 agent）

| Agent ID | 名字 | 角色 | 何时调度 |
|---|---|---|---|
| `academic-lit-analysis-lead` | 析文 | 文献计量师 | 全程编排；**先问后算** |
| `data-auditor` | 见核 | 数据核查师 | 任何解读之前：字段覆盖 / 重复 / 时效 / 缺年份，判断数据能支撑什么结论 |
| `trend-analyst` | 鉴势 | 趋势分析师 | 用户问"在往哪走"：发文量、趋势方向、拐点、突现词 |
| `network-mapper` | 织网 | 共现解读师 | 四类共现网络（关键词/作者/机构/引文）的布局 / 配色 / 渲染参数与解读 |
| `review-outliner` | 构纲 | 综述提纲师 | 用户要写综述：消费分析 JSON 出骨架 |

> **为什么要有前两位**：文献计量最危险的失败模式**不是算错，而是用残缺数据
> 得出看似笃定的结论**。摘要覆盖率低、大量缺年份、近似重复被当成独立文献——
> 这些不会报错，只会安静地给出错误结论。见核负责拦住它们。

## 依赖

```
numpy>=1.24
scikit-learn>=1.3
jieba>=0.42
xlrd>=2.0        # 仅 .xls（OLE2/BIFF8）；.xlsx 请用 openpyxl 或先另存 .xls
pymupdf>=1.24    # PDF 全文提取（中文 PDF 首选；缺失则 pdf_extract 不支持）
pypdf>=4         # PDF 兜底（仅纯英文 PDF）
```

**必需**：R≥4.2 + igraph≥2.0 —— 社会网络分析（SNA，`sna_r.py`）的标准路径。
缺失时 `sna_r.py` **直接失败**并给出安装指引（不再静默回退纯 Python）；仅当显式传
`--allow-python-fallback` 才降级，且产物会标注为非标准路径。`doctor.py` 已把
R + igraph 当作**必需前置条件**检测。安装见下文「R 增强（标准 SNA 后端）」。

**不需要 networkx** —— 布局用纯 numpy 实现。

### jieba 安装注意事项

`jieba==0.42.1` 直接 `pip install` 可能报 `OSError: EEXIST`（其 sdist 嵌套目录
触发 pip 缺陷）。此时手动解包安装：

```bash
curl -sL https://files.pythonhosted.org/packages/c6/cb/18eeb235f833b726522d7ebed54f2278ce28ba9438e3135ab0278d9792a2/jieba-0.42.1.tar.gz -o jieba.tar.gz
tar xzf jieba.tar.gz && cd jieba-0.42.1 && pip install .
```

## 支持范围

| 项 | 支持 | 说明 |
|---|---|---|
| EndNote 20/21+（SQLite） | Y | 主目标 |
| EndNote 18及以前（文本） | N | 退出码 2 + 指引 |
| macOS APFS | Y | 逐条 `os.path.exists()`，**禁用集合比对** |
| Windows | Y | 占用检测改用 `tasklist` 进程探测（`lsof` 为 Unix专有）；<br>探测能力不可用时报告会显式标注"无法判断是否持锁"，不默认"未占用" |
| Linux | Y（推定） | `lsof` → `fuser` → `pgrep` 三级回退 |
| R/igraph SNA（标准路径，必需） | Y 已实跑 | 标准 R ≥4.2 + igraph ≥2.0（多平台实跑） |

## 参数口径（引用规模数字时必须连带标注）

共现网络五参数：

| 参数 | 默认 | 影响 |
|---|---|---|
| `normalize_case` | `lower` | 1094 vs 1061 节点 |
| `df_mode` | `doc` | 1094 vs 1108 节点 |
| `node_df` | `5` | df≥6→845；df≥8→593 |
| `min_edge_count` | `2` | 10672 vs 38051 边（**跨数量级**） |
| `keyword_dedupe` | `per-doc` | 10672 vs 11809 边 |

**放宽口径实测**（`node_df=5` / `min_edge_count=1`，**1094 节点 / 10672 边**）——
上表逐项对比即以此为基准；**默认口径**（`min_edge_count=2`）实测为
**1081 节点 / 8695 边**，见下文主题着色一节。引用规模数字时必须连带口径。

## 共现网络的主题着色

> 报告共渲染**四类共现网络**：关键词共现、作者共现、机构共现、引文共现。仅关键词网络按主题簇着色；
> 作者网络按**合作群（连通分量 component）**着色、机构与引文网络按**共现社群（community）**着色，
> 三类网络主题色取自同一 `_PAL` 的不同起点以互相区分，避免被误读成同一张图。

`build_network.py --topics <topics.json>` 为每个关键词节点计算主题归属：

| 字段 | 含义 |
|---|---|
| `cluster_ids` | 该关键词出现过的所有主题簇（按占比降序） |
| `primary_cluster` | 占比最高的簇 —— **报告按此字段着色** |
| `primary_share` | 最高占比 0–1 |
| `n_clusters` | 出现过的簇数 |
| `is_bridge` | `primary_share < --bridge-share`（默认 0.5），即桥接词 |

口径：`count(关键词w, 簇c) = w 出现在多少篇 c 簇文献的关键词里`，
占比 = `count(w,c) / Σ_c count(w,c)`。分母只算**已归入某簇**的文献
（未参与聚类的文献不计入），故占比之和与 `df` 不必相等。

**默认口径实测**（`node_df=5` / `min_edge_count=2`，**1081 节点 / 8695 边** / 14 簇）：
跨簇节点占多数，桥接词过半；主簇分布均匀（最大簇仅占 11.0% 节点），
故着色有真实区分度。另在放宽口径（`node_df=5` / `min_edge=1`）下实测
**1094 节点 / 10672 边** —— 引用规模数字时必须连带口径，两者不可混用。

> [!] **桥接词不能用「出现簇数 > 1」判定**：本数据集 94.8% 的节点都满足该条件，
> 信号失去区分度。故按 `primary_share < 0.5` 判定「归属是否集中」。

### 报告内的交互

- **布局：分簇岛（cluster-island），几何保证零重叠**。单一力场方案下
  （FR 斥力 + 边引力 + 向心力），簇间无硬约束 → 实测 **71.88% 的节点离别的簇
  质心比离自己的更近**，渲染即「彩色毛球」。本包采用：每簇独立跑 FR（只用簇内边）
  → 按 √簇大小分配半径做行式 packing（相邻岛心距 ≥ r_i+r_j+gap）→ 平移合成；
  **跨簇边不参与布局**。实测同一份库：重叠错分 **71.88% → 0.00%**，
  簇对圆盘交叠 **0/190**，且更快（2.44s → 0.97s）。
  [!] `build_network.py` 中 `nodes.sort(-degree)` 必须在 `layout()` **之前** ——
  否则 `pos_encoded[i]` 与 `nodes[i]` 错位，而报告 JS 优先读 `pos_encoded`
  → 整张图渲染错乱。**要求：`nodes.sort(-degree)` 必须位于 `layout()` 之前。**
- **配色：鲜明且色觉安全**。14 色已**固化**在 `build_report.py` 的 `_PAL`（设计期用
  Oklab 高彩度候选池 + Machado 2009 三类色觉缺陷模拟 + CIEDE2000 选出；生成器不随包提供，
  由 `run_checks.py` 的色板项对 `_PAL` 做自包含区分度校验），目标为
  「**在保证色觉安全的前提下尽量鲜艳**」：
  - 平均彩度 0.1916（Oklab），是旧 Okabe-Ito 补色板 0.1216 的 **1.58×**；
  - 图例相邻色在 4 种视觉类型下 min ΔE00 = **9.44**（可辨）；
  - 白底对比度 ≥ **2.35:1**（配合节点白色光环 + 深色描边，节点在白底上清晰）。
  [!] 手工「彩虹 14 色」实测**相邻对在色觉模拟下 min ΔE00 = 0.0**（相邻两色完全重合），
  故不采用。14 色仍无法在 4 种色觉类型下全部两两可分 → 颜色只是第一通道，
  另叠加冗余编码：图例文字、侧栏关键词列表、悬停提示、桥接词次色描边。
- 悬停显示关键词 / 所属主题 / df / degree；点击高亮邻居并淡化无关节点。
- 点击图例色块 = 只看该主题；再次点击取消。
- 边按主题着色：同主题实色、跨主题浅灰。**不用虚线** —— 10672 条边逐条
  设 `lineDash` 会严重拖垮帧率。
- 标签分级显示（参考 VOSviewer）：只给高权重节点画标签，缩放时才显示更多，
  并做矩形避让。1094 个标签全画必然糊成一团。
- 滚轮缩放 / 拖拽平移 / 双击复位。

### 体积与性能

- `--layout` 把坐标编码为 int16+base64（1094 节点约 5.8KB），
  换取跳过首屏 O(n²) FR 计算。
- 节点字段内联时瘦身为 `pc/ps/ci/br`，边瘦身为 `s/t/w`。
- 画布边必须批量 stroke（按主题分桶，每桶一次 `beginPath`）——
  10672 条边用 SVG 会明显卡顿。

## 多来源导入（其他来源用户的通路）

`import_sources.py` 把任意来源归一为内部 `Ref[]`，写成 `refs.json`；
下游各模块经 `lit_core.load_refs()` 透明读取 `.enl` 或 `refs.json`，**代码零分叉**。

```bash
python3 skills/academic-lit-analysis/scripts/import_sources.py <文件或目录…> [--format auto] [--dedup]
                                 [--out refs.json] [--csv refs.csv]
```

### 支持格式（均为实测，格式按**内容**嗅探，扩展名会骗人）

| 来源 | 扩展名 | 实测记录数 | 备注 |
|---|---|---|---|
| Zotero 原生库 | `zotero.sqlite` | 2/2 Y | **无需导出**，`mode=ro` 直读；自动排除 attachment/note/回收站 |
| RIS | `.ris` | 2/2 Y | CNKI / WoS / Scopus / NoteExpress 通用 |
| BibTeX | `.bib` | 206/206 Y | CNKI 206 条实测；花括号配平切字段 |
| EndNote tagged | `.enw` | 206/206 Y | `%T/%A/%K/%X`，**CNKI 的 .enw 实际是这种**，非 EndNote XML |
| EndNote XML | `.xml` | 2/2 Y | `<record>` 形态，与 tagged 是两种格式 |
| NoteExpress 原生 | `.net` | 206/206 Y | `{字段}: 值`，含 Abstract/Keywords |
| CNKI XML | `.txt`/`.xml` | 206/206 Y | `<Bibliographies>`，CDATA 内容需先提取 |
| CNKI GB7714 引文列表 | `.txt` | 206/206 Y | [!] **无摘要无关键词**，全落 `fallback_title` 降级层 |
| CSV（WoS/Scopus） | `.csv` | 2/2 Y | 自动嗅探 tab/逗号/分号 + 中英文表头别名 |
| WoS 纯文本 tagged | `.txt` | 50/50 Y | 两字母标签 + **三空格续行**；`ER` 结束记录（无尾随空格） |
| WoS HTML | `.html` | 50/50 Y | **多个 `<b>Label:</b>` 挤同一 `<td>`（`&nbsp;` 分隔）**，且标签与值各占一行；无 `Publication Year`，年份取 `Published Date`/`Early Access Date` |
| WoS Excel | `.xls` | 50/50 Y | 真·OLE2 BIFF8，需 `xlrd`；51 行×72 列，列名复用 CSV_MAP |
| Zotero RDF | `.rdf` | — | 兼容 `reference-import` |
| Better BibTeX JSON | `.json` | — | 兼容 `reference-import` |
| **CNKI 加密导出** | `.es6` | N | `XCNKI_ENCRYPT_1.0` 无密钥不可解析，**明确报错**并指引改用 RIS/EndNote XML/BibTeX |

### 关键设计

- **零静默丢弃跨来源同样成立**：`tier` 判定抽成 `lit_core.assign_tier()` 单一事实源，
  `.enl` 直读与所有导入器共用；四类之和 == 导入总数，不等即 exit 5。
- **跨来源去重**（`--dedup`）：DOI 优先，其次归一化标题（lower + 去标点 + 压缩空白）。
  实测把 CNKI 同批 5 个格式的 1030 条合并为 227 条唯一记录（丢弃 803 条重复）。
  [!] 去重后仍可能残留**近似重复**（各源标题写法细微差异导致 DOI/标题都匹配不上），
  须再跑 `dup_check.py` 复核。
- **来源如实标注**：`refs.json` 与各模块产物都带 `source` / `source_label`，
  报告必须显示「本结果来自 CNKI XML」而非含糊说「文献库」——不可把 Zotero 库说成 .enl 库。
- **等价性已验证**：同一份真实 EndNote 库走 `.enl` 直读与 `refs.json` 两条路径，
  簇签名全等、网络 1081 节点/8695 边全等。

## R 增强（标准 SNA 后端）

共现网络的**布局与渲染**仍是纯 Python（numpy 布局 + Canvas 渲染，无需 R）。
但**社会网络分析（SNA）**—— 中心性、社群发现、模块度 —— 由 R + igraph 完成，
这是本包**必需的标准路径**：计量分析要有标准工具链，结果才可复现、才能与他人的
bibliometrix / igraph 结果对话。缺 R 时**直接失败**，不再静默回退。

> [!] **口径说明**：R 缺失时 `sna_r.py` 不得静默回退纯 Python 并 `exit 0`——
> 那样用户会拿到一份「完整报告」，却不知道其中的网络部分
> 既无独立社群划分、也无 ARI/NMI 交叉验证，只是度数排序。这种静默降级必须消除。

脚本：
- `scripts/sna_r.R` —— R 端（必需 `igraph`）：度 / 介数 / 接近 / 特征向量中心性、
  `cluster_walktrap` 社群发现、模块度 Q、边密度；并尝试 `cluster_louvain` 对比模块度。
- `scripts/sna_r.py` —— Python 封装层：探测 R / `igraph` → 写边表 CSV → 调 R → 解析
  → 用 `sklearn` 计算「R 社群 vs NMF 主题簇」的 **ARI / NMI 一致性**。

CLI：
```bash
python3 skills/academic-lit-analysis/scripts/sna_r.py --network ./out/network.json --out ./out \
    [--topics ./out/topics.json] [--rscript /path/to/Rscript] [--allow-python-fallback]
```

设计铁律：**R + igraph 为标准路径；缺 R 默认硬失败，绝不静默回退。**
- R / igraph 不可用 → 打印可复制的安装指引（R 下载、镜像配置、
  `install.packages('igraph')`）并 **`exit 8`（环境不满足）**，不产出任何降级产物。
- **唯一**允许的降级入口是用户显式传 `--allow-python-fallback`；此时 `exit 0`，
  产物写 `backend="python-fallback"`、`is_standard_path=false` 并带 `warning` 字段，
  经报告标为「非标准路径」。
- Windows 上 R 默认不写入 PATH：`sna_r.py` / `doctor.py` 会在 PATH 之外按常见安装目录兜底探测，并单独提示「找到了 R 但没在 PATH」。探测逻辑为**两处共用同一实现**（`lit_core.find_rscript`），覆盖 Windows（`C:/Program Files/R/R-*/bin/`）、macOS（`R.framework`）与 Linux（`/usr/lib/R` 等），并同时匹配带 `.exe` 与不带 `.exe` 的可执行文件 —— 门禁与实际分析必须用同一套探测，否则会出现「环境自检说 OK、实际分析却 exit 8」的自相矛盾。

启用 R 路径（一次性；装到用户库无需管理员权限）：
```bash
Rscript -e 'install.packages("igraph", lib=Sys.getenv("R_LIBS_USER"),
    repos="https://mirrors.tuna.tsinghua.edu.cn/CRAN/")'
```

交叉验证怎么读：ARI / NMI 衡量 R 的 walktrap 社群与 NMF 主题簇的一致程度。二者方法学不同
（一个看「关键词共现的图社区」、一个看「全文词袋主题」），**低一致性恰恰是交叉验证的价值**——
它提示网络社群 ≠ 研究主题，避免把共现簇直接误读为学术主题。**只有 R 标准路径才产出这组指标**；
`python-fallback` 下 ARI/NMI 如实置 `null`（拿伪社群与自身比较会恒得 1.0，属伪造结论）。

**真实库实测**（标准 R + igraph 路径）：

| 指标 | 实测值 |
|---|---|
| R walktrap 社群数 | 170（最大连通分量 990 节点 / 8695 边） |
| 模块度 Q | **0.241** |
| 边密度 | 0.0178 |
| ARI（R 社群 vs NMF 主题） | **0.198** |
| NMI | **0.450** |
| 耗时 | 约 2.1 s |

> ARI 偏低属预期 —— 两者看的本就是不同结构。

> **Windows 实测**（本机 `Rscript` 不在 PATH）：
> `sna_r.py` 经 glob 兜底找到 `C:/Program Files/R/R-<版本>/bin/Rscript.exe`，
> 跑出 `backend="R"` 并如实给出实际 R / igraph 版本号（57 节点 / 103 边，
> Q=0.171232）。负向：`--rscript` 指向不存在路径 → `exit 8` 且不产出任何产物
> （证明门禁生效，不再静默回退）。

报告集成：`build_report.py` 接受可选 `--sna-r ./out/sna_r.json`，在共现网络章节后追加
「R 交叉验证」小节（模块度、社群数、Top 中心性关键词、ARI/NMI 一致性）。

> [!] **R 路径为空时不得谎报成功**（缺 R 即 `exit 8` 硬失败，不静默回退）：若共现网络被
> `--min-edge` 过滤后无剩余边，边表为空。此时 `sna_r.R` 以**内部信号 3** 退出、
> `sna_r.py` 也会拒绝接受 `n_nodes=0` 的结果 —— 现在这是**失败**（`exit 8`，
> 除非显式 `--allow-python-fallback`），不再自动落入 fallback —— 否则会出现
> `backend="R"` 却 `n_nodes=0`，让用户以为拿到了交叉验证结果，实际什么也没有。

## 稳健性检验与论文用表（投稿向）

### K 值稳健性检验（审稿最常问的一句）

```bash
python3 skills/academic-lit-analysis/scripts/robust_k.py "<库路径或 refs.json>" --k 14 --ladder 8,12,14,16,20 --out ./out
```

三层检验，兼容外部方法规范（`robustness-matrix`：检验类别 / 做法 / 回应的质疑 / 结果 / 判定）：

| 优先级 | 检验类别 | 具体做法 | 回应的质疑 |
|---|---|---|---|
| 必做 | 替换主题数 K | 在一组 K 上重跑 NMF，比较同一批文献的簇归属（ARI + Cramér's V） | 「换个 K 就没了」 |
| 必做 | 替换随机种子 | 同 K、换 random_state | 「只是某个初始化的产物」 |
| 高 | 替换语料口径 | hybrid / keyword / title | 「只是语料构造方式的产物」 |

判定阈值（所选 K 与相邻 K 的最小 ARI）：≥0.60 稳定 / 0.40–0.60 中等 / <0.40 不稳定。
**只提供描述性一致性与效应量，不给 p 值**（文献聚类非抽样调查，p 值易被误读）。

**真实库复测**（K=14）：
相邻 K 最小 ARI **0.590**、Cramér's V **0.812** → 判定「中等」；换种子 ARI 1.0 / 0.741 / 0.692；
换语料 ARI 0.156（hybrid vs keyword，差异最大 → 语料口径是最敏感因素，须在方法章节声明）。

[!] `init='nndsvda'` 的可复现性**仅在固定 `random_state` 下成立**。
sklearn 的 nndsvda 内部走 randomized SVD，换 random_state 会改变初始化
（实测 ARI 0.69~0.74）。故 `random_state=42` 必须固定并写进方法章节。

### 三线表导出（`--sanxian`）

```bash
python3 skills/academic-lit-analysis/scripts/build_report.py --topics ./out/topics.json --network ./out/network.json \
    --evolution ./out/evolution.json --author-topic ./out/author_topic.json \
    --sna-r ./out/sna_r.json --out report.html --sanxian ./out/sanxian.html
```

按外部三线表规范（`three-line-table`）生成 4 张表（主题分布 / 主题×年份 / 核心作者 /
R 交叉验证），可直接粘入 Word：**只保留三条横线（顶线粗、栏目线细、底线粗）、不画竖线**、
数字列右对齐并按小数点对齐、注释行在底线之下且以「注：」起首、字号更小。
每张表注均声明"未做推断检验，不标注 p 值"，避免被误读为显著性检验结果。

### 主题 × 时期的效应量（`trend_effects.py`）

```bash
python3 skills/academic-lit-analysis/scripts/trend_effects.py "<库路径或 refs.json>" --topics ./out/topics.json
                                  [--cut 2022] [--out ./out]
```
回答「各主题的年份分布**真的**有差异吗，差异多大」：
· Cramér's V（主题 × 时期列联表的关联强度，0.1/0.3/0.5 为小/中/大）
· η²（主题解释了出版年份方差的多大比例，0.01/0.06/0.14 为小/中/大）
· 每个主题「早期→近期」占比变化 + 近期占比的 95% bootstrap CI

**真实库复测**（分期 2022）：Cramér's V = **0.227（小）**、
η² = **0.083（中，主题解释 8.3% 的年份方差）**，
缺年份文献仅 1.4%。
[!] 关联强度偏小时，不宜把个别主题的占比变化直接当趋势结论 —— 脚本会明示该提醒。

结果可接入三线表：`build_report.py --trend ./out/trend_effects.json` → 输出「表 5」。

## 回归测试（改代码后必跑）

```bash
python3 skills/academic-lit-analysis/scripts/run_checks.py                 # 快速（约 2 分钟，不需真实库）
python3 skills/academic-lit-analysis/scripts/run_checks.py --full          # 追加真实库全链路检查
python3 skills/academic-lit-analysis/scripts/run_checks.py --full --json checks.json
```

**每条检查守护一项需要长期保持的行为**；改动布局 / 配色 / 导入器 /
统计量 / 新模块后务必重跑（当前实测 **234 项**；条目数会随环境分支小幅浮动，以运行输出为准，约 2 分钟，不需真实库）：

| 检查组 | 保证的行为 |
|---|---|
| gini2 边界 | 报告"均衡度 gini"返回 -0.997（完全均衡时应为 0） |
| `_xml_text` CDATA | CNKI XML 源 206 条里 204 条标题变空 |
| Zotero 过滤 | attachment 与回收站条目漏进结果（2 条变 4 条） |
| RIS/WoS 年份优先级 | 在线优先年覆盖正式出版年；`DA` 挡住 `PY` |
| WoS 含冒号题名 | 被误判成标签 → 整条记录丢失（42→50） |
| 色板 ΔE00 / 对比度 | 手工彩虹色板相邻对在色觉模拟下 ΔE00 = 0 |
| sna_r 标准路径门禁 | R 缺失时必须**失败**（exit 8）并给出安装命令，不得静默回退；`--allow-python-fallback` 才降级且须标注非标准路径 |
| 零丢弃恒等式 | 四类 tier 之和必须等于总数 |
| **排序错位（行为断言）** | 真跑建网校验 `pos_encoded[i]` 与 `nodes[i].x/y` 对齐；并**先自检语料能否触发错位**，不能则判 FAIL 而非静默通过 |
| **格式自动嗅探（11 陷阱）** | `.enw` 装 XML/装 tagged、`.txt` 装 6 种格式、CNKI 加密须报错、不可识别须报错、RDF 无作者时字段不得丢 |
| **DOM XSS 防护** | `tip()` / `renderSide()` / `kwNode()` 均无 innerHTML，文本走 textContent；jsdom 实测恶意关键词零点击零触发 |
| **CSV 加固全覆盖** | 穷举全部 `csv.writer` 数据行，凡含外部文本字段者必须已过 `esc_csv_cell` |
| **topics.params 如实** | 写实际生效的 min_df/max_df，降级须落盘并在 warnings 提示可比性下降 |
| **R 端版本探测** | 用版本对象比较（非 as.numeric 强转），实跑 stderr 无弃用警告 |
| **异常退出码契约** | 异常不得返回 1（会被误读为源库不可用），须带 `[hint]` |
| **锁探测提示兑现** | 统一走 `lock_status()`，notice 真正进入各模块产物字段 |
| **导入完整性** | 每个脚本 `--help` 探测，捕捉「改了代码没同步改 import」 |
| **移动端交互** | 四个 pointer 事件齐备、无 mouse* 残留、touch-action=pan-y、双指捏合、触摸双击复位 |
| **突现折扣因子** | 短时新概念不被打折（span_factor=1.0）、置信度 high、strength = strength_raw |
| **网络交互能力** | 节点拖拽偏移、bounds 含偏移、复位、PNG/SVG 导出、四种视图、快捷键 |
| **报告双函数可执行** | `build_html` 与 `sanxian_tables` 均能跑通（防代码块移动） |
| **tagged 年份标签** | `%Y`（CNKI .enw）与 `%D`（原生）都能解析，否则 year 全 None |
| **小库 df 守卫** | `df_bounds` + `fit_vectorizer` 逐级放宽，不因 min_df/max_df 冲突而崩 |
| **K 越界守卫** | `--k > min(n_samples, n_features)` 时报参数错误而非 ValueError |
| **refs.json 统一入口** | 8 个下游模块全部走 `load_refs`，体检链路不断 |
| **包完整性** | 无 `setting.json` 重复、无孤儿头像、成员 ID 有业务语义 |
| **无用户数据** | 无库文件、无样例数据、无本机绝对路径 |
| **输出加固** | `esc_json` 防 `</script>` 注入、`esc_csv_cell` 防 Excel 公式注入 |
| **新模块正确性** | 突现词识别正确、Pajek 1-based 序号、悬空边计数 |
| **一键导出落实** | `export_all.py` 真实可跑：网络落 CSV、复用 export_vosviewer 出 `.net`、产三线表与 summary、README 清单与落盘逐一对齐；缺产物/空网络记录跳过而非崩溃（脚本缺失须 FAIL 而非 skip） |
| **边界声明硬编码** | 「非引文网络」「keyword burst ≠ citation burst」写在代码里 |

## 扩展分析功能（F1–F4，均为本地、只读）

在 M1–M4 之上，新增 4 项可直接服务于"文献综述前处理"的功能。它们只读取
`parse_refs()` 已解析的字段（`read_status` / `author_list` / `year` / `keywords`），
全部复用影子副本 + `mode=ro` 接入，**不写入源库**。

| 功能 | 脚本 | 输出 JSON | 说明 |
|---|---|---|---|
| F1 阅读状态 | `reading_status.py` | `reading.json` | 统计已读/未读（约定 `read_status='1'` 为已读），按年份降序列出待读样本，可 `--csv` 全量导出 |
| F2 重复检测 | `dup_check.py` | `dup.json` | 三重口径：标题精确重复 + DOI 碰撞 + 同刊同年标题相似度≥阈值（`--near-threshold`，排序邻域+difflib）；输出重复组与合并提示 |
| F3 时效性预警 | `age_warning.py` | `age.json` | 年份分布、近三年占比、早于 2019 占比、缺失年份占比、最旧 N 篇；基准年取库内最新年（非系统时钟） |
| F4 主题×作者 | `author_topic.py` | `author_topic.json` | 依赖 `topics.json`；输出每主题 Top 作者、全局核心作者、作者×主题矩阵（行=核心作者，列=主题簇） |

### 关键口径（引用数字须连带标注）

- **阅读约定**：EndNote `read` 字段取值 `'1'`=已读，其余（`'0'`/空）按"未读/待读"处理。
  若你的库约定不同，请在报告中明示并请用户确认。
- **作者归一**：`surname\|initials`（同名靠缩写区分），缩写取每个词首字母
  （`Burke, Ronald J.` → `burke|rj`），**未做跨库消歧**。
- **近似重复**：同 `journal + year` 桶内、归一化标题相似度 ≥ 阈值（默认 0.85）。
  归一化 = lower + 去标点 + 压缩空白。仅基于本地元数据，合并前需人工核对是否为版本/预印本差异。
- **时效基准**：以库内最大年份为"最新年"，近三年窗口 = `[max-2, max]`。

### 与报告集成

`build_report.py` 已接受 `--reading / --dup / --age / --author-topic` 四个可选输入，
缺失则对应章节不渲染。

报告章节顺序（由 `build_html()` 内的 `SECTION_ORDER` 统一驱动，
目录、正文章节号、章节标题三处都取自它，保持一致）：

| 章节 | 说明 |
|---|---|
| 数据体检 | 先交代数据本身可不可信（覆盖、缺口、零丢弃校验） |
| 发文量与趋势 | 这个领域多大、在往哪走（双轴折线：逐年 / 累计 / 趋势） |
| 研究主题 | 在各个研究什么（每主题一色 + 真实关键词） |
| 主题 × 年份演化 | 主题随时间的消长 |
| 主题 × 作者矩阵 | 每主题核心作者、全局核心作者、作者×主题热力矩阵 |
| 关键词年份图 | 关键词 × 年份，含活跃区间与突现标注 |
| 关键词共现网络 | 概念之间什么关系（四视图：按主题 / 时间叠加 / 密度图 / 时间线·年轮） |
| 作者共现网络 | 谁和谁合作（合作群着色） |
| 机构共现网络 | 跨机构合作结构（共现社群着色） |
| 引文网络（共被引 / 耦合） | 仅当题录带 references 字段时出现 |
| 关键词突现检测 | 近期升温的词 |
| 多维交叉共现 | 关键词×作者 / 关键词×年份 / 作者×年份 |
| 文献时效性预警 / 阅读状态 / 重复检测 / 方法与口径 | 数据质量补充与口径说明（R/igraph 交叉验证并入对应网络节） |

**报告交付后**，主理人须**主动询问一次**是否继续产出计量综述骨架；
用户答"不用"后不再追问（详见 `agents/academic-lit-analysis-lead.md` 阶段 4 与步骤 5）。

> [!] **SNA 用 R 标准路径（必需）**：共现网络（M4）的**布局与渲染**仍全部纯 Python、
> 不依赖 R；但**中心性 / 社区发现 / 模块度**等 SNA 由 R + igraph 完成，是必需的标准路径 ——
> 缺 R 时 `sna_r.py` 直接失败（`exit 8`）并给安装指引，不再静默回退纯 Python。
> [!] **剔除引文信息**：本团从 Zotero / 知识图谱等外部技能借鉴设计时，
> 已剥离 GB/T 7714、APA、参考文献列表等**引文格式化与引用管理**能力——
> 综述骨架只给结构，引文落地请用专用引文工具。

## 常见问题

**Q: 报 `No module named sklearn` 但我装过了**
A: 本机可能存在多个 Python 3.13 环境，依赖不同。运行 `doctor.py` 查看当前解释器
   与缺失包列表。同一句 `python3` 在不同 PATH 下解析到不同环境。

**Q: 报 `no such collation sequence`**
A: 未注册自定义排序规则。必须调用 `create_collation` 注册 `ENCI_Base` 与
   `ENCIN_zh_CN`。`lit_core.open_enl_readonly()` 已处理。

**Q: EndNote 正在运行，工具会报错吗？**
A: 不会。检测到文件占用时工具自动切影子副本继续分析（`exit 0`，报告标注
   `busy_detected: true`），**不返回退出码 3**。若需最新数据，请关闭 EndNote 后重新扫描。

**Q: 报告里为什么说"不是引文网络" / 引文网络从哪来**
A: 关键词 / 作者 / 机构**共现网络都不需要引文数据**，始终可构建。
   **引文网络（共被引 / 文献耦合）**依赖题录带参考文献（references / Cited-References）字段：
   WoS / Scopus / 含参考文献的 BibTeX 具备 → 报告出现「引文网络」一节；
   EndNote 本地库（`.enl`）的 `references` 是长度恒为 10 的占位符（distinct=1），
   不具备 → 不构建引文网络。无论哪种源，本工具都**不做"文献级引用追踪"**
   （哪篇引了哪篇），那是引文索引数据库的能力。共现网络回答"概念 / 作者 / 机构 / 文献之间
   有什么关联"，不回答"哪篇文献引用了哪篇"。

## 关键词突现检测（keyword burst）

```bash
python3 skills/academic-lit-analysis/scripts/burst_detection.py "<库路径或 refs.json>" --window 3 --min-total 3 --out ./out
```

回答「**哪个概念正在快速升温**」——这是 `trend_effects.py` 做不到的：
后者只给描述性占比变化（"占比涨了 5.3pp"），burst 给的是
"相对于该词自身的历史基线，这是异常升温"。

| 参数 | 默认 | 说明 |
|---|---|---|
| `--window` | 3 | 基线窗口半径（峰值年前后各 N 年） |
| `--min-total` | 3 | 关键词最小总频次门槛，低于此不检测 |
| `--min-years` | 3 | 关键词至少出现的年份数，低于此**不检测** |
| `--top` | 40 | 输出前 N 个突现词 |

**方法**：对每个关键词按年切分 df，令峰值年 df 相对基线均值的超出倍数为
`burst_ratio`，强度 `= burst_ratio × log(1+总频次) × span_factor / log 11`，
其中 `span_factor` 按「基线可比性」取 1.0 / 0.85 / 0.70（见下文修正说明）。
Laplace 平滑避免基线为 0 时除零。置信度三级：基线可比（≥2 个对照年份）且
频次达标 → `high`（**不再要求 n_years ≥ 4**，见下文置信度判据同步调整）。

> [!] **`--min-years` 为什么必需**（实测）：
> 只在**单一年份**出现过的关键词（实测多为 MeSH 索引词，如
> `history, 20th century` 全部集中在 2017）基线必然为空 →
> `base_mean=0` → Laplace 平滑后 `ratio=20/0.5=40` → 强度 50.79 **直接霸榜第一**。
> 但「只出现一年」意味着**没有历史基线**，其"突现"是数据伪影而非真实升温 ——
> 把噪声推成"最重要的前沿概念"是严重的事实性错误。
> 修正后实测排除 **10508 个**此类词，Top 词变为
> `middle aged` / `adult` / `young adult`（峰值 2025、25–30 年跨度、置信 high），
> 与该库主题（人口老龄化）吻合。排除数量在 `params.n_excluded_single_year` 中如实上报。

### `span_factor`：按「基线可比性」打折，而非「年份跨度」

**`span_factor` 取值依据（按基线可比性分档）**：

| 判据 | 基线 ≥2 年 | 基线 1 年 | 基线 0 年 |
|---|---|---|---|
| `span_factor` | **1.0**（不折） | 0.85 | 0.70 |

按年份跨度线性打折会把 2 年新概念打到 0.46、3 年打到 0.58 —— 短时但基线扎实的新概念会被误压。
但**突现检测的目的恰恰是发现新概念** —— 一个只出现 2 年的词，若基线扎实
（另一年 df=30、峰值 50 → ratio 1.67，本就不虚高）却被无差别打折，是明显误伤。

真正该折的是「基线不可靠导致倍数虚高」：分母趋近 0 时 ratio 天然爆表。
单年份伪突现已由 `min_years` 准入挡住，无需在强度里再折一次。

置信度判据同步调整：`high` 不再要求 `n_years >= 4`，只看基线可比性与频次 ——
否则"基线扎实的 2~3 年新概念"会被降级，而那正是要找的对象。

`bursts.json` 同时落盘 `span_factor` 与 `strength_raw`（未打折值），
用户可自行还原，不必依赖默认口径。

### `--min-years` 取值建议（真实库实证）

| 取值 | 排除词数 | Top3 结果 | high 置信 | 评价 |
|---|---|---|---|---|
| 2（**下限**） | 9039 | middle aged / adult / male | 38 | Y 与 3 档Top40 **完全相同**（差异词 0） |
| **3（默认，推荐）** | 10508 | 同上 | 38 | Y 平衡：滤掉双年伪信号，又不漏真突现 |
| 4 | 11117 | 同上 | 38 | 可用，略保守 |
| 5 | 11483 | 同上 | 39 | 偏严，会开始漏掉短时新概念 |

**结论**：
- **推荐值3**（默认）。它滤掉"只在 1–2 年集中出现"的伪信号，同时保留跨年趋势。
- **最小可用值 2**。实测与 3 档结果**完全一致** —— 现在 `span_factor`
  按「基线可比性」取值（基线 ≥2 年 → 1.0，1 年 → 0.85，0 年 → 0.70），
  双点词的倍数由基线本身而非年份跨度约束，无需靠参数硬拦。
  **低于 2 无意义**：1 年即"无历史"，且脚本会报错（退出码 4）。
- **什么时候该调大（4–5）**：怀疑某个概念只是**一次性事件**（某次会议、某个特殊项目）
  造成的单年高峰，而非持续升温。此时调大可滤除。
- **什么时候该调小（2）**：研究**新兴技术**（如某AI 工具去年才出现），
  担心默认 3 把仅 2 年的真新概念滤掉。此时设2，并**只采信high 置信条目**。

> `min_years` 与置信度是两道独立防线：前者控制准入，后者标注可信度。
> 调低参数不会让噪声"看起来更可信" —— 置信度判定同时检查年份数与基线年份数。

> [!] **这是 keyword burst，不是 citation burst。**
> CiteSpace 的 citation burst 依据**被引频次**突增，需要引文数据；
> 本地 `.enl` 的 `references` 是占位符，零引文数据，**做不了** citation burst。
> 两者回答不同问题（概念升温 vs 文献受关注），**结论不可互相替代**。
> 报告中的突现章节已硬编码此声明，不得删除。

## 一键导出全套产物（`export_all.py` —— 标准收尾步骤）

分析跑完后，**收尾的统一动作**是这一条命令：把产物目录里的所有分析产物
一次性整理成一套带索引的交付物，用户不必再逐个脚本去刨。

```bash
python3 skills/academic-lit-analysis/scripts/export_all.py --dir ./out                # 导出到 ./out/export
python3 skills/academic-lit-analysis/scripts/export_all.py --dir ./out --out ./deliver # 指定导出目录
```

**它只搬运与格式转换，不重算分析** —— 所有数值直接来自各脚本的既有产物，
导出不会改变任何口径或结果。产出结构：

| 位置 | 内容 | 打开方式 |
|---|---|---|
| `data/` | 各网络节点/边表 CSV（关键词/关键词年轮/作者/机构/引文/共被引/耦合）、主题清单、主题×年份矩阵、主题×作者矩阵、发文量/年份、突现检测表、SNA 中心性表、三个交叉矩阵 | Excel / pandas / Gephi |
| `results/` | `sanxian.html`（三线表，复用 `sanxian_tables()`）、`summary.json`（关键指标汇总，machine-readable） | 浏览器 / Word / 程序读取 |
| `interop/<网络>/` | 每个网络各一套 `vosviewer_network.net` + `citespace_nodes.csv` + `citespace_edges.csv` + `vosviewer_export.json`（复用 `export_vosviewer.py`） | VOSviewer / CiteSpace / Pajek |
| `EXPORT_README.md` | 索引：每个文件是什么、口径、用什么软件打开 | 文本编辑器 |

健壮性约定：某产物**缺失或为空网络时跳过并记录**（写进 `summary.json` 的
`skipped` 与 README 的「跳过项」），**不整体失败**；重复运行覆盖同一导出目录
（幂等，且只清理由本工具生成的目录）。

## 导出到 VOSviewer / CiteSpace

```bash
python3 skills/academic-lit-analysis/scripts/export_vosviewer.py --network ./out/network.json --format all --out ./out
```

本包的 `network.json` 是自造 schema，VOSviewer 与 CiteSpace 都读不了。
本脚本补齐"分析产物 → 可继续加工"这一跳：

| 输出 | 用途 |
|---|---|
| `vosviewer_network.net` | Pajek 网络格式，VOSviewer 可直接 `File > Open` |
| `citespace_nodes.csv` | CiteSpace 关键词节点表（id / label / df / degree / primary_cluster） |
| `citespace_edges.csv` | CiteSpace 边表（source / target / weight） |
| `vosviewer_export.json` | 导出元信息：**建网参数口径** + VOSviewer 侧参数建议 + 边界声明 |

**在 VOSviewer 中的用法**：
`File > Open` 选 `.net` → `Create Map` 选 Network data →
归一化方法选 **Association strength**（默认）→ Analysis 面板调
Resolution 与 Min. cluster size。

> [!] VOSviewer 的 **co-citation 功能在本包数据上不可用** —— 那需要引文数据。
> 本工具产出的是**关键词共现网络**，只能做共现/共作者类分析。

**参数口径必须随产物落盘**（借鉴 VOSviewer"分析即配置"理念）：
任何规模数字若脱离 `node_df` / `min_edge_count` / `df_mode` /
`normalize_case` / `keyword_dedupe` 引用，即为误导。

## 方法论借鉴与边界

`references/methods_borrowed.md` 完整记录从 CiteSpace（v7.0.x FAQ）与
VOSviewer（1.6.21手册）吸收了哪4 项方法、**明确不吸收**哪 7 项及理由。
吸收项：keyword burst、跨簇边占比提示、聚类质量三指标纪律、参数口径随产物落盘。
不吸收项：GPT 标签、Times Cited、共被引、Tree map/密度图、云端 API 等。

## 目录

```
skills/academic-lit-analysis/
├── SKILL.md
├── scripts/
│   ├── lit_core.py       核心库（只读接入 / 规范化 / 分词 / 诊断 / assign_tier / load_refs 统一装载 / 输出加固 esc_json·esc_csv_cell·esc_html）
│   ├── _netutil.py       网络共享工具（FR 布局 / 坐标与边编码 / 社群发现；作者·机构·引文三网络共用）
│   ├── import_sources.py     多来源导入（Zotero SQL / RIS / BibTeX / EndNote tagged+XML /
│   │                         NoteExpress .net / CNKI XML / CNKI GB7714 / CSV / Zotero RDF / BBT JSON）
│   ├── doctor.py             环境自检（--install 授权装依赖含 igraph / R+igraph 为必需前置条件）
│   ├── scan_library.py       M1 数据体检（.enl 与 refs.json 双通路）
│   ├── cluster_topics.py     M2 主题聚类 + M3 演化（df_bounds 自适应 + K 越界守卫）
│   ├── build_network.py     M4 关键词共现网络（分簇岛布局；布局/渲染纯 Python）
│   ├── build_keyword_network.py 关键词共现网 + 逐年频次（时区图与突现检测的数据源）
│   ├── build_author_network.py 作者共现网络（co-authorship，篇内作者两两配对）
│   ├── build_institution_network.py 机构共现网络（篇内机构两两配对）
│   ├── build_citation_network.py 引文网络（共被引 co-citation / 文献耦合 coupling，需引文字段）
│   ├── domain_dict.py       领域术语词典加载（按主题域注册专有词，避免被切碎）
│   ├── topic_labels.py      主题命名术语表（含 OB/HRM 概念词典；用户可建 references/topic_labels.local.csv 扩展）
│   ├── sna_r.py             R/igraph SNA 封装层（标准路径；缺 R 默认失败，--allow-python-fallback 才降级）
│   ├── sna_r.R              R 端 SNA（walktrap 社群 / 中心性 / 模块度）
│   ├── robust_k.py          主题数 K 稳健性检验（换 K / 换种子 / 换语料 + bootstrap CI）
│   ├── trend_effects.py     主题 × 时期的效应量与趋势强度（Cramér's V / η² + CI）
│   ├── burst_detection.py   关键词突现检测（keyword burst，非 citation burst）
│   ├── publication_stats.py 发文量统计与趋势（整库或 --topic 单主题；逐年分布/拐点/趋势方向）
│   ├── cross_matrix.py      多维交叉共现（关键词×作者 / 关键词×年份 / 作者×年份 + Cramér's V / NMI）
│   ├── pdf_extract.py       PDF 全文提取（回填缺失的摘要与关键词；PyMuPDF 优先，缺依赖降级）
│   ├── view_smoke.js        视图渲染自检（四视图必须真的画出东西 + 来回切换不抛异常）
│   ├── _view_fixture.json   报告视图/版式自检夹具（合成退化样本：NaN 坐标、缺 pos_encoded）
│   ├── export_vosviewer.py  导出 VOSviewer/Pajek .net 与 CiteSpace 节点边表
│   ├── export_all.py        一键导出：把产物目录整套整理成带索引的交付物
│   ├── run_checks.py        回归测试（每项保证一条长期行为约束）
│   ├── stat_helpers.py      轻量统计量（Cramér's V / η² / bootstrap CI / 超几何检验 / BH-FDR）
│   ├── reading_status.py     F1 阅读状态（未读/待读清单）
│   ├── dup_check.py          F2 重复 / 近似重复检测
│   ├── age_warning.py        F3 文献时效性预警
│   ├── author_topic.py       F4 主题 × 作者矩阵 / 核心作者
│   └── build_report.py      静态 HTML 报告（集成全部模块）
├── references/
│   ├── DATA_NOT_INCLUDED.md 本包不含用户数据的声明与可复现校验命令
│   ├── methods_borrowed.md  CiteSpace / VOSviewer 方法论吸收与边界（含不吸收清单）
│   ├── failure_paths.md      失败场景与降级策略（兼容；含退出码速查）
│   ├── dict_stopword_seed.csv 通用停用词种子表（参考来源；运行期停用词见 lit_core 内置表）
│   ├── org_aliases.csv        机构同义词表（中英文规范名 ↔ 各缩写写法）
│   │                           ← build_institution_network.py 默认加载，可直接追加
│   └── term_aliases.csv       术语同义词种子表（别名 → 规范名；可建 term_aliases.local.csv 覆盖）
```
