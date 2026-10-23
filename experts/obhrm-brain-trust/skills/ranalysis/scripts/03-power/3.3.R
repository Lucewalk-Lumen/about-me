# 纵向研究的效力分析（Power Analysis for Longitudinal Studies）  （方法编号 3.3）
# @method   纵向研究的效力分析（Power Analysis for Longitudinal Studies）
# @chapter  第3章
# @input    用户提供 CSV 数据文件（G3 门禁）：Rscript 3.3.R 数据.csv [变量列...]
# @use_cond 需预先设定效应量（自回归效应、交叉滞后效应、斜率均值等）、波次数、各潜变量的指标数与因子载荷；若无法确定效应量，可参考同类已发表研究或采用保守（较小）的效应量估计。
# @deps     semPower
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
ensure_pkg("semPower")

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
# ---- 根据你的研究设计设定效应量与波次数 ----
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('semPower')

# >>> 1. 交叉滞后模型（CLPM）效力 <<<
# 检验 X 的交叉滞后效应（X1 → Y2）是否显著异于 0
powerCLPM <- semPower.powerCLPM(
  type='a-priori',
  nWaves=2,                       # 波次（时间点）数
  autoregEffects=c(.8, .7),       # X、Y 的自回归（稳定性）效应
  crossedEffects=c(.2, .1),       # 交叉滞后效应（X1→Y2, Y1→X2）
  rXY=NULL,                       # X 与 Y 的同步相关（NULL=不设定）
  nullEffect='crossedX = 0',      # 检验 X 的交叉滞后效应是否为 0
  nIndicator=c(5, 3, 5, 3),       # 各潜变量（X1,X2,Y1,Y2）的指标数
  loadM=c(.5, .6, .5, .6),        # 各潜变量的因子载荷
  alpha=.05, beta=.05             # 显著性水平与 II 类错误率
)
summary(powerCLPM)                # 查看所需最小样本量

# >>> 2. 潜增长曲线模型（LGCM）效力 <<<
# 检验斜率因子均值（sMean）是否显著异于 0（即是否存在显著增长趋势）
powerLGCM <- semPower.powerLGCM(
  type='a-priori', alpha=.05, power=.80,
  nWaves=3,                       # 波次数
  means=c(.5, .2),                # 截距、斜率因子的均值
  variances=c(1, .5),             # 截距、斜率因子的方差
  covariances=.25,                # 截距-斜率协方差
  nullEffect='sMean = 0',         # 检验斜率均值为 0
  nIndicator=rep(3, 3), loadM=.5, # 各波次指标数与载荷
  autocorResiduals=TRUE           # 假设自相关残差
)
summary(powerLGCM)                # 查看所需最小样本量

# ================= 可复现性元数据（sessionInfo 快照）=================
# 记录 R 版本与全部已加载包的版本号。这是防止
# R 包版本漂移导致结论不可复现的最小保障。写入失败必须可见（非 fail-silent）。
.obhrm_si <- try(writeLines(capture.output(sessionInfo()), "sessionInfo.txt"), silent = TRUE)
if (inherits(.obhrm_si, "try-error")) {
  message("警告：sessionInfo.txt 写入失败（工作目录可能只读），复现元数据未落盘")
} else if (exists("OBHRM_SEED")) {
  cat(sprintf("random_seed: %s\n", OBHRM_SEED), file = "sessionInfo.txt", append = TRUE)
}
