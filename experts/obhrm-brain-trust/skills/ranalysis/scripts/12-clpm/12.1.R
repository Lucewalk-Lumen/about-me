# 交叉滞后模型（CLPM）  （方法编号 12.1）
# @method   交叉滞后模型（CLPM）
# @chapter  第12章
# @input    用户提供 CSV 数据文件（G3 门禁）：Rscript 12.1.R 数据.csv [变量列...]
# @use_cond 至少两个时间点的面板数据；样本量>200。
# @deps     lavaan
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
# 交叉滞后模型（CLPM） — lavaan包
# ============================================================
# 用于纵向数据检验两个变量的双向因果关系
# X是否预测Y的变化？Y是否预测X的变化？
# RI-CLPM进一步区分个体间和个体内效应
# ============================================================

# ---- 安装并加载包 ----
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('lavaan')

# ---- 将 dat_long 替换为面板数据框名 ----
# ---- 将 x1-x3/y1-y3 替换为三个时间点的变量名 ----

# 步骤1：指定CLPM模型
clpm_model <- '
  # 自回归路径（稳定性）
  x2 ~ x1    # x的稳定性
  x3 ~ x2
  y2 ~ y1    # y的稳定性
  y3 ~ y2

  # 交叉滞后路径（因果方向）
  y2 ~ x1    # x预测后续y
  y3 ~ x2
  x2 ~ y1    # y预测后续x
  x3 ~ y2

  # 同期相关
  x1 ~~ y1
  x2 ~~ y2
  x3 ~~ y3
'

# 步骤2：拟合CLPM模型
clpm_fit <- sem(clpm_model, data=dat)
summary(clpm_fit, fit.measures=TRUE, standardized=TRUE)
# 解读：交叉滞后路径系数显著 -> 存在因果预测关系

# >>> 纵向中介（半纵向中介，Cole & Maxwell, 2003）<<<
# 检验 X1 → M2 → Y3 的纵向机制（X 通过 M 的纵向变化影响 Y）
long_med_model <- '
  # 自回归（控制前一时间点的水平）
  M2 ~ s1*M1
  Y3 ~ s2*Y2
  # 纵向中介路径
  M2 ~ a*X1
  Y3 ~ b*M2 + c*X1
  # 纵向间接效应
  ind := a*b
'
fit_long_med <- sem(long_med_model, data=dat, se='boot', bootstrap=5000)
summary(fit_long_med, standardized=TRUE, ci=TRUE)
# 解读：ind 的 Bootstrap CI 不含 0 → 纵向中介成立

# ================= 可复现性元数据（sessionInfo 快照）=================
# 记录 R 版本与全部已加载包的版本号。这是防止
# R 包版本漂移导致结论不可复现的最小保障。写入失败必须可见（非 fail-silent）。
.obhrm_si <- try(writeLines(capture.output(sessionInfo()), "sessionInfo.txt"), silent = TRUE)
if (inherits(.obhrm_si, "try-error")) {
  message("警告：sessionInfo.txt 写入失败（工作目录可能只读），复现元数据未落盘")
} else if (exists("OBHRM_SEED")) {
  cat(sprintf("random_seed: %s\n", OBHRM_SEED), file = "sessionInfo.txt", append = TRUE)
}
