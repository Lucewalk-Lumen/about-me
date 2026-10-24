# 非参数检验  （方法编号 6.7）
# @method   非参数检验
# @chapter  第6章
# @input    用户提供 CSV 数据文件（G3 门禁）：Rscript 6.7.R 数据.csv [变量列...]
# @use_cond 数据不满足正态分布或为有序分类变量；独立样本用Mann-Whitney/Wilcoxon，重复测量用Friedman。
# @deps     base R
# @output   分析结果输出至控制台 / 工作目录
# @example  使用自身数据时按 @input 提供文件
# 说明：本脚本配套《R 语言数据分析手册》，代码已检验；运行需本机安装 R。


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
# 非参数检验 — R基础stats包
# ============================================================
# 非参数检验不要求数据服从正态分布
# 适用于：小样本、有序分类变量、数据偏态或存在异常值时
#
# 检验选择决策树：
#   两组独立样本 -> Mann-Whitney U检验（wilcox.test）
#   两组配对样本 -> Wilcoxon符号秩检验（wilcox.test, paired=TRUE）
#   三组+独立样本 -> Kruskal-Wallis检验（kruskal.test）
#   三组+重复测量 -> Friedman检验（friedman.test）
# ============================================================

# ---- 将 dat 替换为你的数据框名 ----
# ---- 将 score 替换为因变量名（连续或有序） ----
# ---- 将 group 替换为分组变量名 ----
# ---- 将 pre/post 替换为配对测量的变量名 ----
# ---- 将 t1/t2/t3 替换为重复测量时间点的变量名 ----

# ============================================================
# 步骤1：Mann-Whitney U检验（两组独立样本）
# ============================================================
# 非参数版的独立样本t检验
# 原假设H0：两组分布相同
# p<0.05 -> 两组得分分布有显著差异
wilcox.test(score ~ group, data=dat)

# ============================================================
# 步骤2：Wilcoxon符号秩检验（两组配对样本）
# ============================================================
# 非参数版的配对样本t检验
# paired=TRUE表示配对设计（如前测-后测）
# 原假设H0：差值的中位数为0
wilcox.test(dat$pre, dat$post, paired=TRUE)

# ============================================================
# 步骤3：Kruskal-Wallis检验（三组及以上独立样本）
# ============================================================
# 非参数版的单因素方差分析
# 原假设H0：所有组分布相同
# p<0.05 -> 至少有一组与其他组不同
kruskal.test(score ~ group, data=dat)
# 事后检验：pairwise.wilcox.test(score ~ group) 进行两两比较

# ============================================================
# 步骤4：Friedman检验（三组及以上重复测量）
# ============================================================
# 非参数版的重复测量方差分析
# 数据需为宽格式矩阵：每行=一个被试，每列=一个时间点
# 原假设H0：各时间点得分分布相同
friedman.test(as.matrix(dat[, c('t1','t2','t3')]))

# ================= 可复现性元数据（sessionInfo 快照）=================
# 记录 R 版本与全部已加载包的版本号。这是防止
# R 包版本漂移导致结论不可复现的最小保障。写入失败必须可见（非 fail-silent）。
.obhrm_si <- try(writeLines(capture.output(sessionInfo()), "sessionInfo.txt"), silent = TRUE)
if (inherits(.obhrm_si, "try-error")) {
  message("警告：sessionInfo.txt 写入失败（工作目录可能只读），复现元数据未落盘")
} else if (exists("OBHRM_SEED")) {
  cat(sprintf("random_seed: %s\n", OBHRM_SEED), file = "sessionInfo.txt", append = TRUE)
}
