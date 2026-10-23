# CiteSpace / VOSviewer 方法论吸收说明

> 本文记录从 CiteSpace（官方 FAQ，v7.0.x）与 VOSviewer（官方手册 1.6.21）中
> 筛选并吸收进本包的方法，以及**明确不吸收**的部分与理由。
> 目的：让"本工具借鉴了什么、没借鉴什么、为什么"可核查，而不是笼统致谢。

---

## 一、CiteSpace 能做什么、不能做什么（本工具的对照基线）

### 1.1 依赖引文数据的能力 —— 本工具全部不可用

| CiteSpace 能力 | 依赖 | 本地 `.enl` 是否有| 本工具结论 |
|---|---|---|---|
| 共被引分析（co-citation） | `references` 字段 | **无**（长度恒为 10 的占位符，distinct=1） | ❌ 不做，且报告须显式声明 |
| 文献耦合（bibliometric coupling） | `references` 字段 | **无** | ❌ 不做 |
| 引文网络（citation network） | 被引/施引数据 | **无** | ❌ 不做 |
| **citation burst**（引文突现） | 被引频次突增 | **无** | ❌ 不做，**不得**用 keyword burst 冒充 |
| 中心性（介数/接近/特征向量） | 引文网络 | **无** | ⚠️ 只能在共现图上算，语义不同 |

**这是本包最重要的边界**：EndNote 无官方 API，本地库的引文数据物理上不存在。
任何声称做了共被引/引文突现的工具都在编造。本包明确不做，并在报告与Agent 提示词中
三处重申（SKILL.md 铁律、主理人约束 5、network-mapper 铁律 1）。

### 1.2 不依赖引文数据的能力 —— 本工具可做且已做

| CiteSpace 能力 | 本工具对应实现 | 状态 |
|---|---|---|
| 关键词共现（co-occurrence） | `build_network.py` | ✅ 已做 |
| 聚类识别 + 标签 | NMF 主题聚类 + `references/topic_labels.py` 术语表 | ✅ 已做 |
| 突现检测（关键词节点） | `burst_detection.py`（keyword burst） | ✅ v0.3.1 新增 |
| 时间演化 | `cluster_topics.py` 的 evolution + `trend_effects.py` 效应量 | ✅ 已做（且更严：给效应量与 CI，不只给曲线） |
| 聚类质量指标 | Silhouette / Modularity（`sna_r.py` 输出 Q、ARI、NMI） | ✅ 已做 |
| 主题×作者矩阵 | `author_topic.py` | ✅ 已做 |
| GPT 自动聚类标签 | ❌ **不吸收** | 见§三 |

---

## 二、吸收的具体方法（4 项）

### 2.1 Keyword burst ← CiteSpace burst detection 的关键词分支

**CiteSpace 的做法**：节点的 citation burst 用 Kleinberg 型突发检测，
在**时间切片**上比较当前频次与历史基线，红色树环标识突现节点。

**本包的适配**：本地无引文，但关键词的**出现年份**完整。故将 burst 的
"频次"从"被引频次"换成"关键词出现频次"，即 keyword burst。

**实现差异（必须在报告中说明，不得混同）**：

| 维度 | CiteSpace citation burst | 本包 keyword burst |
|---|---|---|
| 频次来源 | 被引频次 | 关键词出现频次（df） |
| 回答的问题 | 某篇文献/某被引概念**受关注度**突增 | 某概念**在文献中出现**频次突增 |
| 基线 | 前后时间切片均值 | 峰值年前后 ±window 年均值（Laplace 平滑） |
| 强度 | Kleinberg 强度参数 | `突现倍数 × log(1+总频次)`，仅用于**同库内横向比较** |
| 置信度 | 未显式给出 | `high/medium/low`（由基线年份数 + 词频决定） |

**不可跨越的红线**：报告中必须写明"这是 keyword burst，不是 citation burst"，
两者结论**不可互相替代**。该声明已硬编码进 `build_report.py` 的突现章节。

**为什么仍然有价值**："哪些概念正在快速升温"是综述选题的核心信号，
描述性占比变化（`trend_effects.py`）只能告诉你"占比涨了"，
burst 告诉你"相对于该词自身的历史基线，这是异常升温"。

### 2.2 PMI / cosine / MST ← CiteSpace 的链接选择与剪枝

**CiteSpace 的做法**：关键词网络中推荐用 `PMI` 或 `cosine` 作为链接强度，
再用 `MST`（最小生成树）剪枝，减少冗余连接。

**本包的吸收**：网络仍以共现次数为原始权重（保持可解释性），
但**在报告中显式给出"跨簇边占比"这一对应指标** —— CiteSpace 用 MST 剪枝
解决"边太多看不出结构"，本包用"跨簇边占比高"如实告知用户
"关键词共现本就大量跨主题，不要据此判定主题划分失败"。

**未吸收 MST 剪枝的理由**：MST 会丢弃大量真实共现边，
使"这个概念与哪些概念共现"这一直接问题失真。本包选择**保留全边+ 显式提示**，
把剪枝决策权交给用户（`--min-edge` 参数）。

### 2.3 聚类质量三指标 ← CiteSpace 的 Silhouette / Modularity / 群落结构

**CiteSpace 的做法**：用 Modularity 与 Silhouette 评估聚类质量，
并提供 `All-in-One` 一键优化布局。

**本包的吸收**：`sna_r.py` 已输出模块度 Q、ARI、NMF。
v0.3.1 起，突现与网络章节的**解释纪律**与之对齐：
低一致性（ARI 低）不等于分析失败，而是提示"共现图社区 ≠ 词袋主题"。

**未吸收 All-in-One 的理由**：本包布局是纯 numpy 的分簇岛算法，
已在几何上保证零重叠，交互式布局优化无对应场景。

### 2.4 参数口径随产物落盘 ← VOSviewer 的"分析即配置"理念

**VOSviewer 的做法**（手册 §3.5.3–3.5.4）：创建映射时必须显式选择
归一化方法（No / **Association strength**（默认）/ Fractionalization /
LinLog-modularity）、计数方式（Full / **Fractional**）、聚类 Resolution
与 Min. cluster size。参数不同，结果不可比。

**本包的吸收**：`export_vosviewer.py` 在导出元信息 `vosviewer_export.json`
中写入建网时的完整参数口径（`node_df` / `min_edge_count` / `df_mode` /
`normalize_case` / `keyword_dedupe`），并附VOSviewer 侧的参数建议与
"不可用 co-citation"的说明。

**为什么这条最重要**：本包的历史实测数字（如"1094 节点/10672 边"）
若脱离参数口径引用，就是误导。VOSviewer 的参数强制选择机制提醒我们：
**任何规模数字必须与参数同现**。这条已写入 SKILL.md 与三个 Agent 的铁律。

### 2.5 引用格式与标签生成 ← VOSviewer 的 thesaurus（部分吸收）

**VOSviewer 的做法**（手册 §4.3）：用 thesaurus 文件合并同义词与拼写差异
（`behavior`/`behaviour`、`JIF`/`journal impact factor`），也可忽略泛化词
（`conclusion`/`method`/`result`）。

**本包的吸收**：`references/dict_stopword_seed.csv` 已承担"忽略泛化词"职能；
用户可通过 `references/topic_labels.local.csv` 自定义主题命名。
**未内置同义词合并**：中英文同义词映射需领域知识，内置通用表会引入错误合并，
反而污染结果 —— 故留空由用户按需提供，不预置。

---

## 三、明确不吸收的部分（及理由）

| CiteSpace / VOSviewer 能力 | 不吸收理由 |
|---|---|
| GPT / OpenAI 自动聚类标签 | 需外部 API key 与费用，且会产生不可核查的标签。本包坚持**术语表 + 用户确认**，标签必须可追溯到 top_terms。 |
| Times Cited 指标 | 依赖引文数据，本地库无。 |
| 共被引簇 / 引文耦合 | 依赖引文数据，本地库无。 |
| Tree map / 密度图叠加 | VOSviewer 的核心优势，但本包是**自包含单文件HTML**（`file://` 下无 fetch），复现需引入 JS 库，破坏"离线单文件"这一硬约束。 |
| MCP / 云端 API 查询（OpenAlex、Semantic Scholar 等） | 违反本包"全程离线、只读本地"的根本定位。 |
| CNKI 数据直接做共被引 | CiteSpace 官方 FAQ 明确指出 CNKI 不含 cited references；本包同样不提供此路径。 |
| Scopus RIS 导入 | CiteSpace FAQ 指出 Scopus RIS 可能缺失 references。本包的 CSV 路径已覆盖 WoS/Scopus CSV 导出，故不额外支持 RIS。 |

---

## 四、边界声明模板（报告与对话中必须原样出现）

> **这是关键词共现网络，不是引文网络。** 本地 `.enl` 的 `references` 字段是
> 长度恒为 10 的占位符（distinct=1），零引文数据 —— 这是 EndNote 无 API 下的物理限制。
>
> **突现检测是 keyword burst（关键词出现频次突增），不是 citation burst（引文被引频次突增）。**
> CiteSpace 的 citation burst 需要引文数据，本工具不具备；两者结论不可互相替代。
>
> **共现簇 ≠ 研究主题。** 共现簇是图社区（基于关键词共现），主题是词袋聚类
> （基于 TF-IDF/NMF）。二者方法学不同，低一致性属预期。
> R walktrap 交叉验证的 ARI/NMI 就是为量化这一差异而存在。

---

## 五、来源与版本

| 来源 | 版本/地址 | 用途 |
|---|---|---|
| VOSviewer 官方手册 | `Manual_VOSviewer_1.6.21.pdf`（55 页） | 归一化方法、计数方式、聚类参数、thesaurus、文件格式 |
| VOSviewer 官网 Features 页 | vosviewer.com/features.html | 网络类型、fractional counting、密度/叠加可视化 |
| CiteSpace 官方 FAQ | citespace.podia.com/faq | 数据源限制、共被引的引文依赖、CNKI 限制、聚类标签机制、导出格式 |
| Clarivate EndNote 发布说明 | support.clarivate.com（2025 / 2025.1 / 2025.3） | 确认 EndNote 内置 AI 功能均为单文档级，无库级聚类 |

> ⚠️ 上述内容用于**方法论借鉴与边界界定**。本包未复制任何受版权保护的
> 源码、界面文案或数据文件；所有实现均为独立编写。
