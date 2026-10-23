# 文本网络分析  （方法编号 4.4）
# @method   文本网络分析
# @chapter  第4章
# @input    用户提供 CSV 数据文件（G3 门禁）：Rscript 4.4.R 数据.csv [变量列...]
# @use_cond 需先完成分词和词频分析（未提供 tokens_result 时，脚本按空白/标点对每行文本切词）；建议保留前50-200个高频词；共现窗口通常设为5-10词。
# @deps     ggplot2, ggraph, igraph
# @output   分析结果输出至控制台 / 工作目录
# @example  使用自身数据时按 @input 提供文件
# 说明：本脚本配套《R 语言数据分析手册》，代码已检验；运行需本机安装 R。

# G4 环境门禁：缺失包则提示安装（不代装）
ensure_pkg <- function(p) {
  if (!requireNamespace(p, quietly=TRUE)) {
    stop(paste0('G4: 未安装 R 包 ', p, '，请先运行 install.packages(\'', p, '\')'))
  }
  library(p, character.only=TRUE)
}
ensure_pkg("ggplot2")
ensure_pkg("ggraph")
ensure_pkg("igraph")

# [G3] 用户提供数据：Rscript <this>.R 数据.csv [变量列...]
args <- commandArgs(trailingOnly=TRUE)
if (length(args) < 1) {
  cat("G3 门禁：请提供数据文件，例如 Rscript this.R mydata.csv\n")
  cat("数据要求：宽格式 CSV，每列一个变量，首行为变量名。\n")
  # 用 sys.nframe() 区分「顶层脚本」与「被 source() 调入」两种情形：
  #   Rscript 运行 → nframe()==0，保持 cat()+quit(status=1) 的原行为（干净输出 + 明确退出码）；
  #   被 source() 时 → nframe()>0，改用 stop()，避免连带终止调用方的整个 R 会话。
  if (sys.nframe() == 0L) {
    quit(status = 1)
  }
  stop("G3 门禁：未提供数据文件（请用 Rscript 运行，或显式传入数据文件路径）", call. = FALSE)
}
dat <- read.csv(args[1], fileEncoding="UTF-8", stringsAsFactors=FALSE)
cols <- if (length(args) >= 2) args[2:length(args)] else names(dat)   # 默认全部列；按方法需要可显式指定列
dat <- dat[, cols, drop=FALSE]   # dat = 待分析数据框（默认全部数值列）
# ============================================================
# 文本网络分析 — igraph + ggraph 包
# ============================================================
# 将文本中词语的共现关系构建为网络图
# 节点=词语，边=词语在同一窗口内共现的次数
# 用途：发现文本中的核心概念和主题社群
#
# 前置条件：需先运行9.5的文本预处理获取分词结果
# ============================================================

# ---- 安装并加载包（仅需运行一次） ----
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('igraph')
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('ggraph')
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('ggplot2')
library(igraph)               # 加载igraph
library(ggraph)               # 加载ggraph
library(ggplot2)              # 加载ggplot2

# ---- 前置对象 tokens_result：分词结果 ----
# tokens_result 格式：list(c('word1','word2',...), c('word3','word4',...), ...)
# 每个元素是一篇文档的分词向量。中文语料请先用 4.2.R 完成分词，
# 或在本会话中直接提供 tokens_result；若当前没有该对象，则由 G3 读入的 dat
# 现场构造：每行 CSV 作为一篇文档，按空白与标点切词（适合英文等空格分词语言）。
if (!exists("tokens_result")) {
  .txt <- apply(dat, 1, function(r) paste(r[!is.na(r)], collapse = " "))
  tokens_result <- strsplit(.txt, "[[:space:][:punct:]]+")
  tokens_result <- lapply(tokens_result, function(v) v[nzchar(v)])
  if (length(tokens_result) == 0 || all(lengths(tokens_result) == 0)) {
    stop("G3 门禁：未能从数据中切分出任何词，请改用分词后的语料（见上方说明）。", call. = FALSE)
  }
}

# ============================================================
# 步骤1：构建共现矩阵
# ============================================================
# 统计词频，选取高频词构建网络
all_words <- unlist(tokens_result)          # 展开所有词
word_freq <- table(all_words)                 # 统计词频
top_words <- names(sort(word_freq, decreasing=TRUE)[1:100])  # 前100高频词

# 构建共现边：在同一窗口内出现的词对
window_size <- 5  # 共现窗口大小（可调整，通常5-10）
edges <- list()
for (tokens in tokens_result) {
  tokens <- tokens[tokens %in% top_words]    # 仅保留高频词
  for (i in 1:length(tokens)) {
    end_idx <- min(i + window_size, length(tokens))
    for (j in (i+1):end_idx) {
      if (j > length(tokens)) break
      edges[[length(edges)+1]] <- c(tokens[i], tokens[j])  # 记录词对
    }
  }
}
# 把循环累积的词对列表转成两列边表（from / to）
if (length(edges) == 0) {
  stop("未生成任何共现词对：请确认 tokens_result 非空、且 top_words 与语料有交集。", call. = FALSE)
}
edge_df <- as.data.frame(do.call(rbind, edges), stringsAsFactors = FALSE)
colnames(edge_df) <- c('from','to')

# 统计每对词的共现次数（边权重）
edge_weight <- as.data.frame(table(from = edge_df$from, to = edge_df$to),
                             stringsAsFactors = FALSE)
colnames(edge_weight) <- c('from','to','weight')
edge_weight <- edge_weight[edge_weight$weight > 0, ]  # 过滤掉共现 0 次的词对

# ============================================================
# 步骤2：创建网络图
# ============================================================
# graph_from_data_frame() 从边列表创建网络（weight 作为边属性）
graph_net <- igraph::graph_from_data_frame(edge_weight, directed = FALSE)
# simplify() 合并重复边，汇总权重
graph_net <- simplify(graph_net,
                     remove.multiple=TRUE,        # 合并重复边
                     edge.attr.comb='sum')        # 权重求和

# ============================================================
# 步骤3：网络指标计算
# ============================================================
# 度数(Degree)：节点的连接数，越高表示该词越核心
degree_net <- degree(graph_net)
# 介数(Betweenness)：节点作为最短路径桥梁的次数
between_net <- betweenness(graph_net)
# 输出度数最高的20个词（核心概念）
print(sort(degree_net, decreasing=TRUE)[1:20])

# ============================================================
# 步骤4：社区检测（主题发现）
# ============================================================
# Louvain算法：基于模块度优化的社区检测
# 同一社区内的词关联紧密，可理解为一个"主题"
community <- cluster_louvain(graph_net)
for (i in 1:length(community)) {
  cat(sprintf('Community %d: %s\n', i, paste(community[[i]], collapse=', ')))
}
# 每个Community即一个主题词群，可人工解读主题含义

# ============================================================
# 步骤5：可视化
# ============================================================
# ggraph基于ggplot2语法绘制网络图
# layout='fr'：Fruchterman-Reingold力导向布局
ggraph(graph_net, layout='fr') +
  geom_edge_link(alpha=0.3, aes(width=weight)) +           # 边：透明度+权重
  geom_node_point(aes(size=degree(graph_net)),              # 节点大小=度数
                  color='steelblue') +
  geom_node_text(aes(label=name), repel=TRUE, size=3) +     # 节点标签
  theme_void() +                                              # 去除背景
  labs(title='Text Co-occurrence Network')
# 图形解读：
#   - 大节点=核心词（高频/高连接度）
#   - 同色聚类=同一主题社群
#   - 边越粗=两词共现越频繁

# ================= 可复现性元数据（sessionInfo 快照）=================
# 记录 R 版本与全部已加载包的版本号。这是防止
# R 包版本漂移导致结论不可复现的最小保障。写入失败必须可见（非 fail-silent）。
.obhrm_si <- try(writeLines(capture.output(sessionInfo()), "sessionInfo.txt"), silent = TRUE)
if (inherits(.obhrm_si, "try-error")) {
  message("警告：sessionInfo.txt 写入失败（工作目录可能只读），复现元数据未落盘")
} else if (exists("OBHRM_SEED")) {
  cat(sprintf("random_seed: %s\n", OBHRM_SEED), file = "sessionInfo.txt", append = TRUE)
}
