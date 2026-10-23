# 多元方差分析（MANOVA）  （方法编号 6.6）
# @method   多元方差分析（MANOVA）
# @chapter  第6章
# @input    用户提供 CSV 数据文件（G3 门禁）：Rscript 6.6.R 数据.csv [变量列...]
# @use_cond 因变量为连续型且多元正态分布；协方差矩阵齐性。
# @deps     effectsize, heplots, multcomp, mvnormtest
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
ensure_pkg("effectsize")
ensure_pkg("heplots")
ensure_pkg("multcomp")
ensure_pkg("mvnormtest")

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
# ---- 将 dat 替换为数据框名，score1/score2/score3 替换为因变量，group 替换为分组变量 ----
# >>> 多元方差分析（MANOVA）<<<
# 同时检验自变量对多个连续因变量的影响，控制族系误差率
# 结构图示：
#   group --> score1 (因变量1)
#         \-> score2 (因变量2)
#         \-> score3 (因变量3)
# MANOVA将这些因变量作为一个整体来检验组间差异

manova_model <- manova(cbind(score1, score2, score3) ~ group, data=dat)

# 查看MANOVA结果（多种检验统计量）
summary(manova_model, test='Pillai')   # Pillai Trace（最稳健，推荐）
summary(manova_model, test='Wilks')    # Wilks Lambda（最常用）
summary(manova_model, test='Hotelling-Lawley')  # Hotelling-Lawley Trace
summary(manova_model, test='Roy')     # Roy最大根
# 四种统计量p<0.05均表示组间差异显著

# >>> MANOVA显著后的单变量ANOVA <<<
# 只有当MANOVA整体显著时才进行单变量检验
summary.aov(manova_model)  # 对每个因变量单独做ANOVA
# 注意：单变量ANOVA需Bonferroni校正（alpha = 0.05 / 因变量数）

# >>> 事后检验 <<<
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('multcomp')
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('mvnormtest')
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('heplots')
# 事后两两比较：先按上方提示安装 multcomp，再对显著的因变量逐个做单变量事后检验
# （本脚本默认不代装、不自动执行，仅给出后续分析路径）。

# >>> 前提检验 <<<
# 多元正态性检验
library(mvnormtest)
# mshapiro.test(t(dat[, c('score1','score2','score3')]))  # p>0.05为正态
# 协方差矩阵齐性检验
library(heplots)
# boxM(score1 + score2 + score3 ~ group, data=dat)  # p>0.05为齐性

# ================= 可复现性元数据（sessionInfo 快照）=================
# 记录 R 版本与全部已加载包的版本号。这是防止
# R 包版本漂移导致结论不可复现的最小保障。写入失败必须可见（非 fail-silent）。
.obhrm_si <- try(writeLines(capture.output(sessionInfo()), "sessionInfo.txt"), silent = TRUE)
if (inherits(.obhrm_si, "try-error")) {
  message("警告：sessionInfo.txt 写入失败（工作目录可能只读），复现元数据未落盘")
} else if (exists("OBHRM_SEED")) {
  cat(sprintf("random_seed: %s\n", OBHRM_SEED), file = "sessionInfo.txt", append = TRUE)
}
