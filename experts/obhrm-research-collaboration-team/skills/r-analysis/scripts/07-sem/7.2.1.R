# 并行多重中介  （方法编号 7.2.1）
# @method   并行多重中介
# @chapter  第7章
# @input    用户提供 CSV 数据文件（G3 门禁）：Rscript 7.2.1.R 数据.csv [变量列...]
# @use_cond 自变量X、两个或以上中介变量(M1, M2, ...)、一个因变量Y均为连续变量；M1与M2之间无先后因果顺序；建议Bootstrap检验。
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
# ---- 模型结构：X 同时通过 M1 和 M2 两条路径到达 Y ----
#
#         +--> M1 --> Y
#         |     a1     b1
#    X ---+
#         |     a2     b2
#         +--> M2 --> Y
#
# 间接效应1 = a1 * b1 (X->M1->Y)
# 间接效应2 = a2 * b2 (X->M2->Y)
# 总间接效应 = 间接效应1 + 间接效应2
# 直接效应 = c' (X->Y控制M1和M2后)
# ----
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('lavaan')
library(lavaan)

# >>> 第1步：定义模型 <<<
# 用 lavaan 标签语法给每条路径命名，方便后面计算间接效应
model <- '
  # === a路径：X -> M1 和 X -> M2 ===
  m1 ~ a1 * x    # a1: X对M1的效应（如领导力->工作投入）
  m2 ~ a2 * x    # a2: X对M2的效应（如领导力->工作满意）

  # === b路径：M1 -> Y 和 M2 -> Y（同时放入，控制彼此）===
  y  ~ b1 * m1    # b1: M1对Y的效应（控制M2后）
  y  ~ b2 * m2    # b2: M2对Y的效应（控制M1后）

  # === c-prime路径：X -> Y（直接效应，控制M1和M2后）===
  y  ~ cp * x     # cp: X对Y的直接效应

  # === M1与M2的协方差（允许两个中介变量相关）===
  m1 ~~ m2        # M1和M2之间的残差相关

  # === 定义间接效应 ===
  ind1 := a1 * b1               # 路径1的间接效应：X->M1->Y
  ind2 := a2 * b2               # 路径2的间接效应：X->M2->Y
  ind_total := ind1 + ind2       # 总间接效应
  contrast := ind1 - ind2       # 两条路径的差异检验
'

# >>> 第2步：拟合模型，使用Bootstrap检验间接效应 <<<
fit <- sem(model, data=dat, se='boot', bootstrap=5000)
# se='boot': 用Bootstrap法计算标准误（比正态假设更准确）
# bootstrap=5000: 重抽样5000次

# >>> 第3步：查看结果 <<<
summary(fit, fit.measures=TRUE, standardized=TRUE, ci=TRUE)
# 关注以下参数的95% Bootstrap CI（ci=TRUE输出）：
#   a1: X对M1的效应是否显著
#   a2: X对M2的效应是否显著
#   b1: M1对Y的效应是否显著（控制M2后）
#   b2: M2对Y的效应是否显著（控制M1后）
#   cp: 直接效应是否显著
#   ind1: 路径1间接效应的CI是否含0（不含0=显著）
#   ind2: 路径2间接效应的CI是否含0
#   contrast: 两条路径差异是否显著（CI不含0=两条路径有显著差异）
#   ind_total: 总间接效应是否显著

# ================= 可复现性元数据（sessionInfo 快照）=================
# 记录 R 版本与全部已加载包的版本号。这是防止
# R 包版本漂移导致结论不可复现的最小保障。写入失败必须可见（非 fail-silent）。
.obhrm_si <- try(writeLines(capture.output(sessionInfo()), "sessionInfo.txt"), silent = TRUE)
if (inherits(.obhrm_si, "try-error")) {
  message("警告：sessionInfo.txt 写入失败（工作目录可能只读），复现元数据未落盘")
} else if (exists("OBHRM_SEED")) {
  cat(sprintf("random_seed: %s\n", OBHRM_SEED), file = "sessionInfo.txt", append = TRUE)
}
