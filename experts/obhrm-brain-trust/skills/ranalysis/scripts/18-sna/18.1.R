# 社会网络分析（SNA）  （方法编号 18.1）
# @method   SNA（Social Network Analysis，社会网络分析）
# @chapter  第18章
# @input    用户提供边表 CSV（G3 门禁）：Rscript 18.1.R 边表.csv [weighted]
# @use_cond 关系/网络数据（团队成员协作、知识扩散、组织沟通、引文网络等）；计算节点中心性、社群结构与关键行动者
# @deps     igraph（必需）
# @output   网络规模、度/介数/接近中心性、社群检测（walktrap）、可选网络图，输出至控制台
# @example  使用自身数据时按 @input 提供文件，并在 MODEL CONFIG 中确认列名
# 说明：本脚本由《R语言数据分析手册》（SNA 章）提取并检验；运行需本机安装 R 与 igraph。
#       注：文本共现网络见 04-text/4.4.R；本脚本面向"行动者—关系"网络（节点为个体/组织，边为关系）。

# G4 环境门禁：缺失包则提示安装（不代装）
ensure_pkg <- function(p) {
  if (!requireNamespace(p, quietly = TRUE)) {
    stop(paste0('G4: 未安装 R 包 ', p, '，请先运行 install.packages(\'', p, '\')'))
  }
  library(p, character.only = TRUE)
}
ensure_pkg("igraph")

# [G3] 用户提供数据：Rscript <this>.R 边表.csv [weighted]
args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 1) {
  cat("G3 门禁：请提供边表 CSV，例如 Rscript 18.1.R edges.csv\n")
  cat("数据要求（边表，每行一条关系）：\n")
  cat("  from  : 关系起点（节点标识，字符或编号）\n")
  cat("  to    : 关系终点（节点标识）\n")
  cat("  weight: 可选，关系权重（如互动频次）；不提供则视为无权网络\n")
  cat("第二参数可选 'plot' 另存网络图 PNG（默认 网络图.png）。\n")
  # 用 sys.nframe() 区分「顶层脚本」与「被 source() 调入」两种情形：
  #   Rscript 运行 → nframe()==0，保持 cat()+quit(status=1) 的原行为（干净输出 + 明确退出码）；
  #   被 source() 时 → nframe()>0，改用 stop()，避免连带终止调用方的整个 R 会话。
  if (sys.nframe() == 0L) {
    quit(status = 1)
  }
  stop("G3 门禁：未提供数据文件（请用 Rscript 运行，或显式传入数据文件路径）", call. = FALSE)
}
dat <- read.csv(args[1], fileEncoding = "UTF-8", stringsAsFactors = FALSE)
use_weight <- "weight" %in% names(dat)
do_plot <- length(args) >= 2 && tolower(args[2]) == "plot"

req <- c("from", "to")
miss <- setdiff(req, names(dat))
if (length(miss) > 0) stop(paste0("G3: 边表缺少必需列：", paste(miss, collapse = ", ")))

# 构建图
if (use_weight) {
  g <- graph_from_data_frame(dat[, c("from", "to", "weight")], directed = TRUE)
} else {
  g <- graph_from_data_frame(dat[, c("from", "to")], directed = TRUE)
}

cat("===== 社会网络分析（igraph）=====\n")
cat("节点数：", vcount(g), "；边数：", ecount(g), "；有向：", is_directed(g), "\n")
cat("加权网络：", use_weight, "\n")

# 中心性
deg <- degree(g, mode = "all")
bet <- betweenness(g, directed = is_directed(g))
clo <- closeness(g, mode = "all")

cat("\n--- 中心性（Top 节点）---\n")
cent <- data.frame(
  node = names(deg),
  degree = as.numeric(deg),
  betweenness = round(as.numeric(bet), 3),
  closeness = round(as.numeric(clo), 4),
  stringsAsFactors = FALSE
)
cent <- cent[order(-cent$degree), ]
print(head(cent, min(10, nrow(cent))))

# 社群检测（walktrap，基于随机游走的模块度优化）
comm <- cluster_walktrap(g)
cat("\n--- 社群检测（walktrap）---\n")
cat("社群数：", length(unique(membership(comm))), "\n")
cat("模块化程度 Q =", round(modularity(comm), 4), "\n")
mem <- data.frame(node = names(membership(comm)), community = as.numeric(membership(comm)), stringsAsFactors = FALSE)
print(table(mem$community))

cat("\n--- 网络密度 / 平均路径 ---\n")
cat("密度：", round(edge_density(g), 4), "\n")
if (is_connected(g)) {
  cat("平均路径长度：", round(mean_distance(g), 4), "\n")
} else {
  cat("图非全连通，平均路径长度略去（存在孤立成分）。\n")
}

# 可选：网络图
if (do_plot) {
  png("网络图.png", width = 800, height = 800)
  plot(comm, g, vertex.size = 8, vertex.label.cex = 0.7, edge.arrow.size = 0.4)
  dev.off()
  cat("\n网络图已保存：网络图.png\n")
}

cat("\n[完成] SNA 分析结束。\n")
