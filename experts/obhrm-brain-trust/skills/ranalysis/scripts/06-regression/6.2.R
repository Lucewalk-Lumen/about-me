# 相关分析  （方法编号 6.2）
# @method   相关分析
# @chapter  第6章
# @input    用户提供 CSV 数据文件（G3 门禁）：Rscript 6.2.R 数据.csv [变量列...]
# @use_cond 两个或以上连续变量；Pearson需满足正态分布和线性关系假设；Spearman不要求数据为连续型。
# @deps     psych
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
ensure_pkg("psych")

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
# 相关分析 — psych包
# ============================================================
# 衡量两个变量间的线性关联程度
# Pearson：连续变量+正态分布
# Spearman：有序变量或不满足正态分布
# ============================================================

# ---- 安装并加载包 ----
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('psych')

# ---- 使用用户提供的数据 dat（列由命令行参数指定，缺省为全部列） ----

# 步骤1：Pearson相关（默认；取前两列作示例）
if (ncol(dat) < 2) stop("G5: 相关分析至少需要 2 个变量列，当前数据仅 ", ncol(dat), " 列")
cat("=== 步骤1：Pearson 相关系数（示例：前两列）===\n")
print(cor(dat[, cols[1]], dat[, cols[2]], method='pearson'))   # r∈[-1,1]，绝对值越大关联越强

# 步骤2：相关矩阵（多变量间）
cat("=== 步骤2：Pearson 相关矩阵 ===\n")
print(cor(dat[, cols], method='pearson'))

# 步骤3：带 p 值的相关检验
cat("=== 步骤3：相关检验（含 p 值矩阵）===\n")
print(corr.test(dat[, cols], method='pearson'))

# 步骤4：Spearman秩相关（非参数；示例：前两列）
cat("=== 步骤4：Spearman 秩相关（示例：前两列）===\n")
print(cor(dat[, cols[1]], dat[, cols[2]], method='spearman'))

# 步骤5：可视化相关矩阵（交互环境绘制散点图矩阵；非交互环境跳过）
if (interactive()) {
  pairs.panels(dat[, cols])   # 散点图矩阵 + 相关系数
} else {
  cat("=== 步骤5：可视化相关矩阵（非交互环境略过；交互运行 R 时执行 pairs.panels）===\n")
}

# ================= 可复现性元数据（sessionInfo 快照）=================
# 记录 R 版本与全部已加载包的版本号。这是防止
# R 包版本漂移导致结论不可复现的最小保障。写入失败必须可见（非 fail-silent）。
.obhrm_si <- try(writeLines(capture.output(sessionInfo()), "sessionInfo.txt"), silent = TRUE)
if (inherits(.obhrm_si, "try-error")) {
  message("警告：sessionInfo.txt 写入失败（工作目录可能只读），复现元数据未落盘")
} else if (exists("OBHRM_SEED")) {
  cat(sprintf("random_seed: %s\n", OBHRM_SEED), file = "sessionInfo.txt", append = TRUE)
}
