# 数据中心化  （方法编号 2.5）
# @method   数据中心化
# @chapter  第2章
# @input    用户提供 CSV 数据文件（G3 门禁）：Rscript 2.5.R 数据.csv [变量列...]
# @use_cond 变量为连续型；嵌套数据需有分组变量
# @deps     misty
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
# ---- 将 dat 替换为你的数据框名，Score 替换为你的变量名 ----
# ---- 如有嵌套数据，GroupID 替换为你的分组变量 ----

# >>> 总均值中心化（Grand Mean Centering）<<<
dat$Score_grand <- dat$Score - mean(dat$Score)       # 方法1：手动减均值
dat$Score_grand <- scale(dat$Score, scale=FALSE)        # 方法2：scale函数

# >>> 分组均值中心化（Group Mean Centering）<<<
dat$Score_group <- dat$Score - ave(dat$Score, dat$GroupID)
# ave()按GroupID分组计算各组均值，再用原始值减去组均值

# >>> 使用misty包（推荐用于嵌套数据）<<<
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('misty')
# 注意：center() 第一个参数是数据框（非向量），分组变量用 cluster 指定（字符串）
# type='CGM' 总均值中心化；type='CWC' 分组均值中心化；默认生成新列 Score.c
dat <- center(dat, Score, type='CGM', cluster='GroupID')  # 总均值中心化
dat <- center(dat, Score, type='CWC', cluster='GroupID')  # 分组均值中心化

# ================= 可复现性元数据（sessionInfo 快照）=================
# 记录 R 版本与全部已加载包的版本号。这是防止
# R 包版本漂移导致结论不可复现的最小保障。写入失败必须可见（非 fail-silent）。
.obhrm_si <- try(writeLines(capture.output(sessionInfo()), "sessionInfo.txt"), silent = TRUE)
if (inherits(.obhrm_si, "try-error")) {
  message("警告：sessionInfo.txt 写入失败（工作目录可能只读），复现元数据未落盘")
} else if (exists("OBHRM_SEED")) {
  cat(sprintf("random_seed: %s\n", OBHRM_SEED), file = "sessionInfo.txt", append = TRUE)
}
