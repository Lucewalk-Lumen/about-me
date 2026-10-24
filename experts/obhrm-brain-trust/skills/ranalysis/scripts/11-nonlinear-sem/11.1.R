# 非线性SEM（潜变量交互与二次效应）  （方法编号 11.1）
# @method   非线性SEM（潜变量交互与二次效应）
# @chapter  第11章
# @input    用户提供 CSV 数据文件（G3 门禁）：Rscript 11.1.R 数据.csv [变量列...]
# @use_cond 潜变量至少3个指标；样本量>200（LMS法建议>500）；正态性假设（LMS对非正态敏感）；模型需收敛。
# @deps     lavaan, modsem
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
ensure_pkg("lavaan")
ensure_pkg("modsem")

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
# ---- 将 dat 替换为数据框名，x1-x3/z1-z3/y1-y3 替换为指标变量名 ----
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('modsem')
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('lavaan')

# >>> 方法1：modsem潜变量交互（LMS法）<<<
# X与Z的交互影响Y（潜变量层面的调节）
# 结构图示：
#   X ~~~> Y
#     \  /
#      Z  （X×Z → Y 潜变量交互项）
#
model_int <- '
  # 测量模型
  X =~ x1 + x2 + x3      # 自变量潜变量
  Z =~ z1 + z2 + z3      # 调节变量潜变量
  Y =~ y1 + y2 + y3      # 因变量潜变量
  # 结构模型（含交互项）
  Y ~ X + Z + X:Z        # X:Z为潜变量交互项
'
fit_int <- modsem(model_int, data=dat, method='lms')
summary(fit_int)

# >>> 方法2：modsem二次效应（Quadratic Effect）<<<
# 检验X对Y是否存在倒U型关系
# 结构图示：
#   X ~~~> Y
#   X² ~> Y  （二次项检验曲线关系）
#
model_quad <- '
  X =~ x1 + x2 + x3
  Y =~ y1 + y2 + y3
  Y ~ X + X:X            # X:X为X的二次效应项
'
fit_quad <- modsem(model_quad, data=dat, method='qml')
summary(fit_quad)

# >>> 方法3：lavaan观测变量交互（乘积指标法）<<<
# 先创建乘积指标，再用lavaan估计
dat$xz <- dat$x1 * dat$z1  # 用第一对指标创建乘积项
model_prod <- '
  X =~ x1 + x2 + x3
  Z =~ z1 + z2 + z3
  Y =~ y1 + y2 + y3
  XZ =~ xz               # 乘积指标作为潜变量
  Y ~ X + Z + XZ
'
fit_prod <- sem(model_prod, data=dat)
summary(fit_prod, fit.measures=TRUE, standardized=TRUE)

# ================= 可复现性元数据（sessionInfo 快照）=================
# 记录 R 版本与全部已加载包的版本号。这是防止
# R 包版本漂移导致结论不可复现的最小保障。写入失败必须可见（非 fail-silent）。
.obhrm_si <- try(writeLines(capture.output(sessionInfo()), "sessionInfo.txt"), silent = TRUE)
if (inherits(.obhrm_si, "try-error")) {
  message("警告：sessionInfo.txt 写入失败（工作目录可能只读），复现元数据未落盘")
} else if (exists("OBHRM_SEED")) {
  cat(sprintf("random_seed: %s\n", OBHRM_SEED), file = "sessionInfo.txt", append = TRUE)
}
