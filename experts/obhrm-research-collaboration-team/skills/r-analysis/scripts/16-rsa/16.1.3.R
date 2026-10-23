# 响应面分析的中介效应  （方法编号 16.1.3）
# @method   响应面分析的中介效应
# @chapter  第16章
# @input    用户提供 CSV 数据文件（G3 门禁）：Rscript 16.1.3.R 数据.csv [变量列...]
# @use_cond
# @deps     boot, lavaan
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
ensure_pkg("boot")
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
# ---- 将 z 替换为最终因变量，x/y 替换为两个预测变量，m 替换为中介变量，dat 替换为数据框名 ----
# RSA中介：一致性效应(X与Y的一致性)通过中介M影响Z
# 方法：多项式回归预测M，M再预测Z，形成间接效应
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('lavaan')
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('boot')
library(lavaan)
library(boot)

# >>> 步骤1：构建多项式项 <<<
dat$x_c <- scale(dat$x, scale=FALSE)
dat$y_c <- scale(dat$y, scale=FALSE)
dat$x_sq <- dat$x_c^2
dat$y_sq <- dat$y_c^2
dat$xy <- dat$x_c * dat$y_c

# >>> 步骤2：计算一致性/不一致性指标 <<<
# |X-Y|表示一致性程度（绝对差异）
dat$congruence <- abs(dat$x_c - dat$y_c)
# 也可用 (X-Y)^2 表示不一致性
dat$discrepancy <- (dat$x_c - dat$y_c)^2

# >>> 方法A：间接效应 = a(b1+4b2) ， a为X对M的效应，b1为M对Z的效应 <<<
# 使用lavaan路径分析
rsa_med_model <- '
  # a路径：多项式项预测中介M
  m ~ a1 * x_c + a2 * y_c + a3 * x_sq + a4 * xy + a5 * y_sq
  # b和c-prime路径：M和多项式项预测Z
  z ~ cp1 * x_c + cp2 * y_c + cp3 * x_sq + cp4 * xy + cp5 * y_sq
  z ~ b * m
  # 间接效应（一致性效应通过M传递）
  # 一致线上的间接效应 = (a1+a2) * b
  ind_congruence := (a1 + a2) * b
  # 不一致线上的间接效应 = (a1-a2) * b
  ind_discrepancy := (a1 - a2) * b
  # 总间接效应
  ind_total := ind_congruence + ind_discrepancy
'
fit_med <- sem(rsa_med_model, data=dat, se='boot', bootstrap=1000)
summary(fit_med, fit.measures=TRUE, standardized=TRUE, ci=TRUE)

# >>> 方法B：Bootstrap中介效应检验（更灵活）<<<
rsa_med_boot <- function(data, indices) {
  d <- data[indices, ]
  d$x_c <- scale(d$x, scale=FALSE)
  d$y_c <- scale(d$y, scale=FALSE)
  d$x_sq <- d$x_c^2; d$y_sq <- d$y_c^2; d$xy <- d$x_c * d$y_c
  # a路径：多项式预测M
  a_fit <- lm(m ~ x_c + y_c + x_sq + xy + y_sq, data=dat)
  a1 <- coef(a_fit)['x_c']; a2 <- coef(a_fit)['y_c']
  # b路径：M预测Z（控制多项式）
  b_fit <- lm(z ~ x_c + y_c + x_sq + xy + y_sq + m, data=dat)
  b <- coef(b_fit)['m']
  # 一致线间接效应 = (a1+a2)*b
  return((a1 + a2) * b)
}
boot_result <- boot(data=dat, statistic=rsa_med_boot, R=5000)
boot.ci(boot_result, type='bca')
# BCa区间不含0表示RSA中介效应显著

# ================= 可复现性元数据（sessionInfo 快照）=================
# 记录 R 版本与全部已加载包的版本号。这是防止
# R 包版本漂移导致结论不可复现的最小保障。写入失败必须可见（非 fail-silent）。
.obhrm_si <- try(writeLines(capture.output(sessionInfo()), "sessionInfo.txt"), silent = TRUE)
if (inherits(.obhrm_si, "try-error")) {
  message("警告：sessionInfo.txt 写入失败（工作目录可能只读），复现元数据未落盘")
} else if (exists("OBHRM_SEED")) {
  cat(sprintf("random_seed: %s\n", OBHRM_SEED), file = "sessionInfo.txt", append = TRUE)
}
