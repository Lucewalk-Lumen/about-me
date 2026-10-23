# 共同方法偏差检验（CMV）  （方法编号 5.8）
# @method   共同方法偏差检验（CMV）
# @chapter  第5章
# @input    用户提供 CSV 数据文件（G3 门禁）：Rscript 5.8.R 数据.csv [变量列...]
# @use_cond 核心变量均为同一来源（自评）的横截面数据；通常作为中介/回归分析前的稳健性检验。
# @deps     lavaan, psych
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
ensure_pkg("psych")

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
# ---- 将 dat 替换为数据框名，x1-x6 替换为你的全部量表题目 ----
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('psych')
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('lavaan')

# >>> 方法1：Harman单因子检验（最常用、最简单）<<<
# 对所有量表题目做单因子EFA
harman_fa <- fa(dat[, c('x1','x2','x3','x4','x5','x6')], nfactors=1, rotate='none')
print(harman_fa$Vaccounted)
# 判断：第一个因子解释的方差比例 < 50%（严格标准 40%）→ 无严重CMV
# 若第一个因子解释 > 50% 方差，提示存在明显共同方法偏差

# >>> 方法2：单因子CFA（共同方法因子法，更严格）<<<
# 步骤1：正常的多因子测量模型
model_normal <- '
  f1 =~ x1 + x2 + x3
  f2 =~ x4 + x5 + x6
'
fit_normal <- cfa(model_normal, data=dat)

# 步骤2：加入共同方法因子（所有题目同时负荷到 cmv）
model_cmv <- '
  f1 =~ x1 + x2 + x3
  f2 =~ x4 + x5 + x6
  cmv =~ x1 + x2 + x3 + x4 + x5 + x6   # 方法因子
  # 方法因子与实质因子正交，保证模型可识别
  cmv ~~ 0*f1
  cmv ~~ 0*f2
'
fit_cmv <- cfa(model_cmv, data=dat)

# 步骤3：比较两个模型
anova(fit_normal, fit_cmv)  # 卡方差异检验，p<0.05 → 方法因子显著（存在CMV）
# 实际中更常用 ΔCFI 判断：加入方法因子后 CFI 提升 < 0.01 → 无实质CMV

# ================= 可复现性元数据（sessionInfo 快照）=================
# 记录 R 版本与全部已加载包的版本号。这是防止
# R 包版本漂移导致结论不可复现的最小保障。写入失败必须可见（非 fail-silent）。
.obhrm_si <- try(writeLines(capture.output(sessionInfo()), "sessionInfo.txt"), silent = TRUE)
if (inherits(.obhrm_si, "try-error")) {
  message("警告：sessionInfo.txt 写入失败（工作目录可能只读），复现元数据未落盘")
} else if (exists("OBHRM_SEED")) {
  cat(sprintf("random_seed: %s\n", OBHRM_SEED), file = "sessionInfo.txt", append = TRUE)
}
