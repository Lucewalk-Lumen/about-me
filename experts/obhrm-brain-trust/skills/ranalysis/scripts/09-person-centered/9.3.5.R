# LGA有调节的中介  （方法编号 9.3.5）
# @method   LGA有调节的中介
# @chapter  第9章
# @input    用户提供 CSV 数据文件（G3 门禁）：Rscript 9.3.5.R 数据.csv [变量列...]
# @use_cond 至少 3 个时间点；有自变量、中介（增长参数）、调节变量和结果。
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
# ============================================================
# LGA有调节的中介：增长参数的中介路径受调节变量W影响
# ============================================================
# 模型结构：
#   X ──a──→ 增长参数(i/s) ──b──→ Y(结果)
#         ↑
#    W调节a路径（X对增长参数的影响随W变化）
# 间接效应 = a(W) * b，在不同W水平下大小不同
# ============================================================
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('lavaan')

# ---- 将 x/m/y/w/t1-t4 替换为变量名 ----

# 步骤1：指定有调节的中介增长模型
lgm_modmed_model <- '
  # 潜增长因子
  i =~ 1*t1 + 1*t2 + 1*t3 + 1*t4
  s =~ 0*t1 + 1*t2 + 2*t3 + 3*t4

  # a路径含交互项（X*W -> 增长参数）
  s ~ a1 * x + a2 * w + a3 * x:w    # x:w为交互项
  i ~ x + w                         # 截距仅含主效应

  # b路径（增长参数 -> 结果）
  y ~ b1 * i + b2 * s

  # 条件间接效应定义
  ind_s := (a1 + a3 * w_mean) * b2   # 通过斜率的中介效应
  # w_mean需替换为W的均值或特定值
'

# 步骤2：拟合模型
lgm_modmed_fit <- sem(lgm_modmed_model, data=dat,
                      se='boot', bootstrap=5000)
summary(lgm_modmed_fit, fit.measures=TRUE)
# 查看ind_s的Bootstrap置信区间
# CI不含0 -> 有调节的中介效应显著

# 步骤3：在不同W水平下计算条件间接效应
# W低（均值-1SD）：ind_low = (a1 + a3*W_low) * b2
# W高（均值+1SD）：ind_high = (a1 + a3*W_high) * b2

# ================= 可复现性元数据（sessionInfo 快照）=================
# 记录 R 版本与全部已加载包的版本号。这是防止
# R 包版本漂移导致结论不可复现的最小保障。写入失败必须可见（非 fail-silent）。
.obhrm_si <- try(writeLines(capture.output(sessionInfo()), "sessionInfo.txt"), silent = TRUE)
if (inherits(.obhrm_si, "try-error")) {
  message("警告：sessionInfo.txt 写入失败（工作目录可能只读），复现元数据未落盘")
} else if (exists("OBHRM_SEED")) {
  cat(sprintf("random_seed: %s\n", OBHRM_SEED), file = "sessionInfo.txt", append = TRUE)
}
