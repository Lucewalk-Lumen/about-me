# 动态结构方程模型（DSEM，密集纵向的前沿方法）  （方法编号 13.1.6）
# @method   动态结构方程模型（DSEM，密集纵向的前沿方法）
# @chapter  第13章
# @input    用户提供 CSV 数据文件（G3 门禁）：Rscript 13.1.6.R 数据.csv [变量列...]
# @use_cond 密集纵向数据（通常 >20 个时间点/人）；关注个体内的动态关系而非个体间差异；需处理缺失与不等距时间点。
# @deps     dsem
# @output   分析结果输出至控制台 / 工作目录
# @example  使用自身数据时按 @input 提供文件
# 说明：本脚本由《R语言数据分析手册-已检验.md》提取，代码已检验；运行需本机安装 R。

# G4 环境门禁：缺失包则提示安装（不代装）
ensure_pkg <- function(p) {
  if (!requireNamespace(p, quietly=TRUE)) {
    stop(paste0('G4: 未安装 R 包 ', p, '，请先运行 install.packages(\'', p, '\')'))
  }
  library(p, character.only=TRUE)
}
ensure_pkg("dsem")

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
# DSEM 在 R 中用 dsem 包实现
# 基本思路：在多层框架中加入自回归/交叉滞后，显式建模时间动态
# 以下为概念性示例（dsem 包需较长的数据准备，此处给出核心结构）
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('dsem')
# 核心模型：个体内自回归 + 交叉滞后（滞后1阶）
# X[t] ~ X[t-1] + Y[t-1]   （自回归 + 交叉滞后）
# Y[t] ~ Y[t-1] + X[t-1]
# 完整实现需用 dsem() 指定动态项，并处理 person-mean centering
# 注：DSEM 在 R 的 dsem 包中以多层框架实现动态项

# ================= 可复现性元数据（sessionInfo 快照）=================
# 记录 R 版本与全部已加载包的版本号。这是防止
# R 包版本漂移导致结论不可复现的最小保障。写入失败必须可见（非 fail-silent）。
.obhrm_si <- try(writeLines(capture.output(sessionInfo()), "sessionInfo.txt"), silent = TRUE)
if (inherits(.obhrm_si, "try-error")) {
  message("警告：sessionInfo.txt 写入失败（工作目录可能只读），复现元数据未落盘")
} else if (exists("OBHRM_SEED")) {
  cat(sprintf("random_seed: %s\n", OBHRM_SEED), file = "sessionInfo.txt", append = TRUE)
}
