# 有调节的中介  （方法编号 7.4）
# @method   有调节的中介
# @chapter  第7章
# @input    用户提供 CSV 数据文件（G3 门禁）：Rscript 7.4.R 数据.csv [变量列...]
# @use_cond 包含自变量、中介变量、因变量和调节变量；建议用 Bootstrap 检验条件间接效应的置信区间。
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
# ---- 将 X/Z/M/Y 替换为自变量/调节变量/中介变量/因变量 ----
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('lavaan')
library(lavaan)
# 中心化 X 和 Z（减少共线性，便于解释交互项）
dat$Xc <- scale(dat$X, scale=FALSE)
dat$Zc <- scale(dat$Z, scale=FALSE)
dat$XZ <- dat$Xc * dat$Zc

# ============ 类型1：第一阶段调节（Z 调节 X→M，Hayes Model 7）============
m1 <- '
  M ~ a1*Xc + a2*Zc + a3*XZ     # a 路径含调节
  Y ~ b*M + c*Xc + d*Zc          # b 路径 + 直接效应
  # 条件间接效应：在 Z 高低水平下的 (a1 + a3*Z) * b
  ind_low  := (a1 + a3*(-1)) * b    # Z = -1 SD
  ind_high := (a1 + a3*( 1)) * b    # Z = +1 SD
  ind_diff := ind_high - ind_low    # 高低水平的间接效应差
'
fit1 <- sem(m1, data=dat, se='boot', bootstrap=5000)
summary(fit1, standardized=TRUE, ci=TRUE)
# 解读：ind_diff 的 CI 不含 0 → 第一阶段有调节的中介成立

# ============ 类型2：第二阶段调节（Z 调节 M→Y，Hayes Model 14）============
m2 <- '
  M ~ a1*Xc
  Y ~ b1*M + b2*Zc + b3*M:Zc + c*Xc   # b 路径含调节
  # 条件间接效应：a * (b1 + b3*Z)
  ind_low  := a1 * (b1 + b3*(-1))
  ind_high := a1 * (b1 + b3*( 1))
  ind_diff := ind_high - ind_low
'
fit2 <- sem(m2, data=dat, se='boot', bootstrap=5000)
summary(fit2, standardized=TRUE, ci=TRUE)

# ============ 类型3：两阶段调节（Z 同时调节 X→M 和 M→Y）============
m3 <- '
  M ~ a1*Xc + a2*Zc + a3*XZ
  Y ~ b1*M + b2*Zc + b3*M:Zc + c*Xc
  ind_low  := (a1 + a3*(-1)) * (b1 + b3*(-1))
  ind_high := (a1 + a3*( 1)) * (b1 + b3*( 1))
  ind_diff := ind_high - ind_low
'
fit3 <- sem(m3, data=dat, se='boot', bootstrap=5000)
summary(fit3, standardized=TRUE, ci=TRUE)

# ============ 类型4：直接效应调节（Z 调节 X→Y 直接路径）============
m4 <- '
  M ~ a1*Xc
  Y ~ b*M + c1*Xc + c2*Zc + c3*XZ   # 直接效应含调节
  ind := a1 * b                        # 间接效应（不受 Z 调节）
'
fit4 <- sem(m4, data=dat, se='boot', bootstrap=5000)
summary(fit4, standardized=TRUE, ci=TRUE)

# ================= 可复现性元数据（sessionInfo 快照）=================
# 记录 R 版本与全部已加载包的版本号。这是防止
# R 包版本漂移导致结论不可复现的最小保障。写入失败必须可见（非 fail-silent）。
.obhrm_si <- try(writeLines(capture.output(sessionInfo()), "sessionInfo.txt"), silent = TRUE)
if (inherits(.obhrm_si, "try-error")) {
  message("警告：sessionInfo.txt 写入失败（工作目录可能只读），复现元数据未落盘")
} else if (exists("OBHRM_SEED")) {
  cat(sprintf("random_seed: %s\n", OBHRM_SEED), file = "sessionInfo.txt", append = TRUE)
}
