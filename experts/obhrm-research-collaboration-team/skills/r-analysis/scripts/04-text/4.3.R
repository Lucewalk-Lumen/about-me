# 主题模型（LDA）  （方法编号 4.3）
# @method   主题模型（LDA）
# @chapter  第4章
# @input    用户提供 CSV 数据文件（G3 门禁）：Rscript 4.3.R 数据.csv [变量列...]
# @use_cond 文档集合（建议>50篇）；每篇文档至少50词；未提供 dfm_text 时脚本会由输入数据现场构建 DFM。
# @deps     quanteda, topicmodels
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
ensure_pkg("quanteda")
ensure_pkg("topicmodels")

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
# ---- 需先运行9.5创建DFM，将 dfm_text 替换为你的DFM对象 ----
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('topicmodels')
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('quanteda')
library(topicmodels)
library(quanteda)

# >>> 从DFM创建LDA输入 <<<
# 前置对象 dfm_text：文档-词矩阵。若已在上一步（4.2.R）生成则直接沿用；
# 否则由 G3 读入的 dat 现场构造：每行 CSV 作为一篇文档，按标点与空白切词。
if (!exists('dfm_text')) {
  texts <- apply(dat, 1, function(r) paste(r[!is.na(r)], collapse=' '))
  dfm_text <- dfm(tokens(corpus(texts), remove_punct=TRUE))
}
dtm <- convert(dfm_text, to='topicmodels')

# >>> 拟合LDA模型 <<<
# ---- 将 k=5 替换为通过比较确定的最优主题数 ----
lda_model <- LDA(dtm, k=5, method='Gibbs',
                control=list(seed=123, burnin=1000, iter=2000, thin=500))
print(lda_model)

# >>> 主题-词分布 <<<
terms(lda_model, 10)  # 每个主题的前10个词
beta <- posterior(lda_model)$terms  # 主题-词概率矩阵
topic_terms <- terms(lda_model, 10)
for (i in 1:nrow(topic_terms)) {
  cat(sprintf('Topic %d: %s\n', i, paste(topic_terms[i,], collapse=', ')))
}

# >>> 文档-主题分布 <<<
gamma <- posterior(lda_model)$topics  # 文档-主题概率矩阵
dominant_topic <- apply(gamma, 1, which.max)
table(dominant_topic)  # 各主题的文档数量

# >>> 可视化 <<<
barplot(beta[1, order(beta[1,], decreasing=TRUE)[1:10]],
       las=2, main='Topic 1 Top Words', col='steelblue')

# ================= 可复现性元数据（sessionInfo 快照）=================
# 记录 R 版本与全部已加载包的版本号。这是防止
# R 包版本漂移导致结论不可复现的最小保障。写入失败必须可见（非 fail-silent）。
.obhrm_si <- try(writeLines(capture.output(sessionInfo()), "sessionInfo.txt"), silent = TRUE)
if (inherits(.obhrm_si, "try-error")) {
  message("警告：sessionInfo.txt 写入失败（工作目录可能只读），复现元数据未落盘")
} else if (exists("OBHRM_SEED")) {
  cat(sprintf("random_seed: %s\n", OBHRM_SEED), file = "sessionInfo.txt", append = TRUE)
}
