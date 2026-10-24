# 基础潜增长模型  （方法编号 9.3.1）
# @method   基础潜增长模型
# @chapter  第9章
# @input    用户提供 CSV 数据文件（G3 门禁）：Rscript 9.3.1.R 数据.csv [变量列...]
# @use_cond 至少 3 个时间点的纵向数据；样本量 > 200。
# @deps     lavaan
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
ensure_pkg("lavaan")

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
# 基础LGA：分析变量随时间的变化轨迹
# ============================================================
# 模型结构示意：
#   时间点:  t1    t2    t3    t4
#   i(截距): 1     1     1     1    ← 起点水平
#   s(斜率): 0     1     2     3    ← 变化速率
# ============================================================
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('lavaan')
library(lavaan)              # 加载lavaan

# ---- 将 t1-t4 替换为你的时间点变量名 ----
# 步骤1：指定潜增长模型
lgm_model <- '
  i =~ 1*t1 + 1*t2 + 1*t3 + 1*t4    # 截距因子（初始水平）
  s =~ 0*t1 + 1*t2 + 2*t3 + 3*t4    # 斜率因子（变化速率）
'

# 步骤2：拟合模型
lgm_fit <- growth(lgm_model, data=dat)
summary(lgm_fit, fit.measures=TRUE, standardized=TRUE)
# i的均值=整体初始水平；s的均值=变化速率（正=增长，负=下降）
# i和s的方差=个体差异；i~~s协方差=初始水平与变化速率的关系

# ================= 可复现性元数据（sessionInfo 快照）=================
# 记录 R 版本与全部已加载包的版本号。这是防止
# R 包版本漂移导致结论不可复现的最小保障。写入失败必须可见（非 fail-silent）。
.obhrm_si <- try(writeLines(capture.output(sessionInfo()), "sessionInfo.txt"), silent = TRUE)
if (inherits(.obhrm_si, "try-error")) {
  message("警告：sessionInfo.txt 写入失败（工作目录可能只读），复现元数据未落盘")
} else if (exists("OBHRM_SEED")) {
  cat(sprintf("random_seed: %s\n", OBHRM_SEED), file = "sessionInfo.txt", append = TRUE)
}
