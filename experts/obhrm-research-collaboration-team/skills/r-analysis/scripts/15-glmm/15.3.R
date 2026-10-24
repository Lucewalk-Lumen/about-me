# 跨水平交互效应与中心化策略  （方法编号 15.3）
# @method   跨水平交互效应与中心化策略
# @chapter  第15章
# @input    用户提供 CSV 数据文件（G3 门禁）：Rscript 15.3.R 数据.csv [变量列...]
# @use_cond 数据为嵌套结构；需区分组内效应和组间效应。
# @deps     dplyr, lme4, lmerTest, misty
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
ensure_pkg("dplyr")
ensure_pkg("lme4")
ensure_pkg("lmerTest")
ensure_pkg("misty")

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
# ---- 将 dat 替换为数据框名，y/x1/x2_group 替换为变量名，group_id 替换为分组变量 ----
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('lme4')
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('lmerTest')
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('misty')
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('dplyr')
library(lme4); library(lmerTest); library(misty); library(dplyr)
# Level-1变量分组均值中心化（CWC）
# center() 第一个参数是数据框，cluster 指定分组变量（字符串），生成新列 x1.c
dat <- center(dat, x1, type='CWC', cluster='group_id')
dat$x1_cwc <- dat$x1.c  # 提取组内中心化列
# 保存组均值作为Level-2变量
gm <- dat %>% group_by(group_id) %>% summarise(x1_gmean = mean(x1, na.rm=TRUE))
dat <- merge(dat, gm, by='group_id')
dat$x1_gmean_cgm <- dat$x1_gmean - mean(dat$x1_gmean, na.rm=TRUE)  # 总均值中心化
# 跨水平交互
dat$cross_int <- dat$x1_cwc * dat$x1_gmean_cgm
model_cross <- lmer(y ~ x1_cwc + x1_gmean_cgm + cross_int + (1 + x1_cwc | group_id), data=dat)
summary(model_cross)
# x1_cwc: 组内效应；x1_gmean_cgm: 组间效应(情境效应)；cross_int: 跨水平交互

# ================= 可复现性元数据（sessionInfo 快照）=================
# 记录 R 版本与全部已加载包的版本号。这是防止
# R 包版本漂移导致结论不可复现的最小保障。写入失败必须可见（非 fail-silent）。
.obhrm_si <- try(writeLines(capture.output(sessionInfo()), "sessionInfo.txt"), silent = TRUE)
if (inherits(.obhrm_si, "try-error")) {
  message("警告：sessionInfo.txt 写入失败（工作目录可能只读），复现元数据未落盘")
} else if (exists("OBHRM_SEED")) {
  cat(sprintf("random_seed: %s\n", OBHRM_SEED), file = "sessionInfo.txt", append = TRUE)
}
