# 链式/序列中介  （方法编号 7.2.2）
# @method   链式/序列中介
# @chapter  第7章
# @input    用户提供 CSV 数据文件（G3 门禁）：Rscript 7.2.2.R 数据.csv [变量列...]
# @use_cond 自变量X、中介M1和M2、因变量Y均为连续变量；M1理论上先于M2发生；建议Bootstrap检验；样本量>200。
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
# ---- 将 x/m1/m2/y 替换为你的变量名，dat 替换为你的数据框名 ----
# ---- 模型结构：X -> M1 -> M2 -> Y（链式传递）----
#
#    X --a1--> M1 --d21--> M2 --b2--> Y
#     \                          /
#      \--a2--> M2 -----b2----/
#       \                       /
#        \------cp------------>Y
#
# 三种间接效应：
#   链式间接效应 = a1 * d21 * b2  (X->M1->M2->Y，三级链)
#   路径1间接效应 = a1 * b1       (X->M1->Y，跳过M2)
#   路径2间接效应 = a2 * b2       (X->M2->Y，跳过M1)
# ----
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('lavaan')
library(lavaan)

# >>> 第1步：定义链式中介模型 <<<
model <- '
  # === 第一阶段：X -> M1 ===
  m1 ~ a1 * x    # a1: X对M1的效应

  # === 第二阶段：X和M1 -> M2 ===
  m2 ~ a2 * x     # a2: X对M2的直接效应
  m2 ~ d21 * m1   # d21: M1对M2的效应（链式关键路径）

  # === 第三阶段：M1和M2 -> Y ===
  y  ~ b1 * m1    # b1: M1对Y的效应（控制M2后）
  y  ~ b2 * m2    # b2: M2对Y的效应（控制M1后）

  # === 直接效应 ===
  y  ~ cp * x     # cp: X->Y的直接效应

  # === 定义间接效应 ===
  # 链式间接效应：X->M1->M2->Y（三级传递）
  ind_serial := a1 * d21 * b2
  # 路径1间接效应：X->M1->Y（跳过M2）
  ind_m1 := a1 * b1
  # 路径2间接效应：X->M2->Y（跳过M1）
  ind_m2 := a2 * b2
  # 总间接效应
  ind_total := ind_serial + ind_m1 + ind_m2
'

# >>> 第2步：Bootstrap检验 <<<
fit <- sem(model, data=dat, se='boot', bootstrap=5000)

# >>> 第3步：查看结果 <<<
summary(fit, fit.measures=TRUE, standardized=TRUE, ci=TRUE)
# 关注 ind_serial 的Bootstrap 95%CI：
#   CI不含0 = 链式中介效应显著（X->M1->M2->Y传递成立）
#   CI含0 = 链式路径不成立

# ================= 可复现性元数据（sessionInfo 快照）=================
# 记录 R 版本与全部已加载包的版本号。这是防止
# R 包版本漂移导致结论不可复现的最小保障。写入失败必须可见（非 fail-silent）。
.obhrm_si <- try(writeLines(capture.output(sessionInfo()), "sessionInfo.txt"), silent = TRUE)
if (inherits(.obhrm_si, "try-error")) {
  message("警告：sessionInfo.txt 写入失败（工作目录可能只读），复现元数据未落盘")
} else if (exists("OBHRM_SEED")) {
  cat(sprintf("random_seed: %s\n", OBHRM_SEED), file = "sessionInfo.txt", append = TRUE)
}
