# 多重结果中介  （方法编号 7.2.3）
# @method   多重结果中介
# @chapter  第7章
# @input    用户提供 CSV 数据文件（G3 门禁）：Rscript 7.2.3.R 数据.csv [变量列...]
# @use_cond 自变量X、一个中介变量M、两个或以上因变量(Y1, Y2, ...)均为连续变量；建议Bootstrap检验。
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
# ---- 将 x/m/y1/y2 替换为你的变量名，dat 替换为你的数据框名 ----
# ---- 模型结构：X 通过 M 同时影响 Y1 和 Y2 ----
#
#              +--> Y1
#         |    b1
#    X --> M --+
#         |   b2
#              +--> Y2
#
# 间接效应1 = a * b1  (X->M->Y1)
# 间接效应2 = a * b2  (X->M->Y2)
# ----
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('lavaan')
library(lavaan)

# >>> 第1步：定义多重结果中介模型 <<<
model <- '
  # === a路径：X -> M ===
  m  ~ a * x       # a: X对M的效应（共用）

  # === b路径：M -> Y1 和 M -> Y2 ===
  y1 ~ b1 * m      # b1: M对Y1的效应（如授权->绩效）
  y2 ~ b2 * m      # b2: M对Y2的效应（如授权->创新）

  # === c-prime路径：X -> Y1 和 X -> Y2（直接效应）===
  y1 ~ cp1 * x     # cp1: X对Y1的直接效应（控制M后）
  y2 ~ cp2 * x     # cp2: X对Y2的直接效应（控制M后）

  # === Y1与Y2的残差协方差 ===
  y1 ~~ y2         # 允许两个因变量的残差相关

  # === 定义间接效应 ===
  ind_y1 := a * b1              # X->M->Y1的间接效应
  ind_y2 := a * b2              # X->M->Y2的间接效应
  contrast := ind_y1 - ind_y2   # 两条路径的差异检验
'

# >>> 第2步：Bootstrap检验 <<<
fit <- sem(model, data=dat, se='boot', bootstrap=5000)

# >>> 第3步：查看结果 <<<
summary(fit, fit.measures=TRUE, standardized=TRUE, ci=TRUE)
# ind_y1的CI不含0：X通过M影响Y1的中介效应显著
# ind_y2的CI不含0：X通过M影响Y2的中介效应显著
# contrast的CI不含0：X对Y1和Y2的中介效应有显著差异

# ================= 可复现性元数据（sessionInfo 快照）=================
# 记录 R 版本与全部已加载包的版本号。这是防止
# R 包版本漂移导致结论不可复现的最小保障。写入失败必须可见（非 fail-silent）。
.obhrm_si <- try(writeLines(capture.output(sessionInfo()), "sessionInfo.txt"), silent = TRUE)
if (inherits(.obhrm_si, "try-error")) {
  message("警告：sessionInfo.txt 写入失败（工作目录可能只读），复现元数据未落盘")
} else if (exists("OBHRM_SEED")) {
  cat(sprintf("random_seed: %s\n", OBHRM_SEED), file = "sessionInfo.txt", append = TRUE)
}
