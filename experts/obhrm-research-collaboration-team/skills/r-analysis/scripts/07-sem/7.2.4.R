# 中介效应量与敏感性分析  （方法编号 7.2.4）
# @method   中介效应量与敏感性分析
# @chapter  第7章
# @input    用户提供 CSV 数据文件（G3 门禁）：Rscript 7.2.4.R 数据.csv [变量列...]
# @use_cond 已完成中介效应检验；敏感性分析需基于 mediation 包的中介模型。
# @deps     lavaan, mediation
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
ensure_pkg("mediation")
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
# ---- 将 dat 替换为数据框名，X/M/Y 替换为自变量/中介变量/因变量 ----
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('lavaan')
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('mediation')
library(lavaan)
library(mediation)

# >>> 步骤1：完全标准化间接效应（效应量）<<<
model <- '
  M ~ a*X
  Y ~ b*M + c*X
  indirect := a*b          # 间接效应
  total := c + a*b         # 总效应
'
fit <- sem(model, data=dat)
summary(fit, standardized=TRUE)
# 查看 indirect 行的 std.all 列 = 完全标准化间接效应
# 判断标准（参照 Cohen）：|std.all| > 0.01 小，> 0.09 中等，> 0.25 大

# >>> 步骤2：敏感性分析（mediation::medsens）<<<
# 先拟合 mediation 包的中介模型
fit_m <- lm(M ~ X, data=dat)
fit_y <- lm(Y ~ M + X, data=dat)
med <- mediate(fit_m, fit_y, treat='X', mediator='M', sims=1000, boot=TRUE)

# 敏感性分析：检验未测量混杂（unmeasured confounding）的影响
sens <- medsens(med, rho.by=0.1, sims=1000)
summary(sens)
# 关键指标：
#   rho：假设的"混杂与中介/结果"的相关系数（从 -1 到 1 扫描）
#   R2tilde.thresh：使中介效应恰好变为 0 所需的未测量混杂解释力阈值
#   R2star.thresh：使中介效应显著性改变的阈值
# 判断：若阈值远大于实际可能存在的混杂解释力，则中介结果稳健

# ================= 可复现性元数据（sessionInfo 快照）=================
# 记录 R 版本与全部已加载包的版本号。这是防止
# R 包版本漂移导致结论不可复现的最小保障。写入失败必须可见（非 fail-silent）。
.obhrm_si <- try(writeLines(capture.output(sessionInfo()), "sessionInfo.txt"), silent = TRUE)
if (inherits(.obhrm_si, "try-error")) {
  message("警告：sessionInfo.txt 写入失败（工作目录可能只读），复现元数据未落盘")
} else if (exists("OBHRM_SEED")) {
  cat(sprintf("random_seed: %s\n", OBHRM_SEED), file = "sessionInfo.txt", append = TRUE)
}
