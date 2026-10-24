# 跨层次有中介的调节（Cross-level Mediated Moderation）  （方法编号 15.4.2）
# @method   跨层次有中介的调节（Cross-level Mediated Moderation）
# @chapter  第15章
# @input    用户提供 CSV 数据文件（G3 门禁）：Rscript 15.4.2.R 数据.csv [变量列...]
# @use_cond 数据具有嵌套结构；交互效应（X×W→Y）显著是前提条件；中介M需要能解释交互效应的传递机制；组数>30。
# @deps     lavaan, misty
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
ensure_pkg("misty")
# ================= 可复现性：固定随机种子 =================
# 本脚本含随机过程（bootstrap / 置换检验 / 随机初值 / 多重插补之一或多个）。
# 未固定种子时，同一份数据两次运行可能得出不同结论 —— 学术结论不可复现。
# 种子随结果一并输出（控制台 + sessionInfo.txt），供复核与他人复现。
OBHRM_SEED <- 20260101   # 全局随机种子
set.seed(OBHRM_SEED)
cat(sprintf("seed: %d\n", OBHRM_SEED))


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
# ---- 将 dat 替换为数据框名，x/y 替换为Level-1变量，w/m 替换为Level-2变量，group_id 替换为分组变量 ----
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('lavaan')
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('misty')
library(lavaan)
library(misty)

# >>> 数据准备 <<<
# Level-1变量组内中心化（CWC）
dat <- center(dat, x, type='CWC', cluster='group_id')
dat <- center(dat, m, type='CWC', cluster='group_id')
dat <- center(dat, y, type='CWC', cluster='group_id')
dat$x_cwc <- dat$x.c; dat$m_cwc <- dat$m.c; dat$y_cwc <- dat$y.c
# 创建跨水平交互项：Level-1的X × Level-2的W
dat$xw <- dat$x_cwc * dat$w

# >>> 模型结构图示 <<<
# Level-2（组层）：
#   W --> M           （W影响中介M）
#   W × X --> M       （交互效应影响M）
# Level-1（个体层）：
#   X --> Y            （X对Y的主效应）
#   M --> Y            （M对Y的中介路径）
#
#   W ~~~~~~> M ~~~~~~> Y
#    \      /
#     X × W            （交互效应被M中介）
#      |
#      v
#      Y

# >>> 跨层次有中介的调节模型 <<<
model_clmm2 <- '
  # Level-1：组内路径
  level: 1
    y_cwc ~ c * x_cwc + b * m_cwc   # c:X的直接效应 + b:M对Y的中介路径
  # Level-2：组间路径
  level: 2
    m_cwc ~ a1 * w + a2 * xw          # a1:W对M的效应 + a2:交互效应(X×W)对M的效应
    y_cwc ~ w + m_cwc                 # W对Y的直接效应 + M对Y的组间效应
  # 间接的交互效应 = a2 × b
  # 即交互效应通过M传递的部分
'
fit_clmm2 <- sem(model_clmm2, data=dat, cluster='group_id',
                 se='boot', bootstrap=1000)
summary(fit_clmm2, fit.measures=TRUE, standardized=TRUE)

# >>> 间接的交互效应检验 <<<
pe2 <- parameterEstimates(fit_clmm2, boot.ci.type='bca.simple')
a2_est <- pe2$est[pe2$label=='a2']    # 交互效应对M的影响
b_est <- pe2$est[pe2$label=='b']      # M对Y的影响
ind_interact <- a2_est * b_est        # 间接的交互效应 = a2 × b
cat('间接的交互效应(a2*b):', ind_interact, '
')

# >>> 完整的交互效应分解 <<<
# 总交互效应 = 直接交互效应(c的交互部分) + 间接交互效应(a2*b)
# 若a2显著且a2*b的CI不含0：交互效应部分通过M传递（有中介的调节成立）
# 若c的交互部分不再显著：完全中介的交互效应
# 若c的交互部分仍显著：部分中介的交互效应

# ================= 可复现性元数据（sessionInfo 快照）=================
# 记录 R 版本与全部已加载包的版本号。这是防止
# R 包版本漂移导致结论不可复现的最小保障。写入失败必须可见（非 fail-silent）。
.obhrm_si <- try(writeLines(capture.output(sessionInfo()), "sessionInfo.txt"), silent = TRUE)
if (inherits(.obhrm_si, "try-error")) {
  message("警告：sessionInfo.txt 写入失败（工作目录可能只读），复现元数据未落盘")
} else if (exists("OBHRM_SEED")) {
  cat(sprintf("random_seed: %s\n", OBHRM_SEED), file = "sessionInfo.txt", append = TRUE)
}
