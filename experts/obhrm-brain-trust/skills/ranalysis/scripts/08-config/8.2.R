# 必要条件分析（NCA）  （方法编号 8.2）
# @method   必要条件分析（NCA）
# @chapter  第8章
# @input    用户提供 CSV 数据文件（G3 门禁）：Rscript 8.2.R 数据.csv [变量列...]
# @use_cond 自变量X和因变量Y均为连续或有序变量；关注瓶颈关系而非平均效应；样本量建议>30。
# @deps     NCA
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
ensure_pkg("NCA")

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
# ---- 将 dat 替换为数据框名，x1 替换为自变量名，y 替换为因变量名 ----
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('NCA')

# >>> 单变量必要条件检验 <<<
# ---- 将 x1 替换为自变量名，y 替换为因变量名 ----
model_nca <- nca_analysis(dat, x='x1', y='y')
print(model_nca)
summary(model_nca)
# 上限回归方法：CE-FDH(非参数,小样本), CR-FDH(参数化), CE-LP(大样本)

# >>> 多变量必要条件分析 <<<
model_multi <- nca_analysis(dat, x=c('x1','x2','x3'), y='y', ceilings='ce_fdh')
print(model_multi)
# 效应量d：0<d<=0.1小, 0.1<d<=0.3中, 0.3<d<=0.5较大, d>0.5大

# >>> 瓶颈分析 <<<
# 用 nca_output() 的 bottlenecks 参数生成瓶颈表
nca_output(model_multi, bottlenecks=TRUE, plots=FALSE)
# 行=Y的不同水平(0%-100%), 列=各X的必要水平, NN=不构成瓶颈

# >>> 可视化 <<<
plot(model_nca)  # 散点图+CE上限回归线

# >>> 统计显著性检验（置换检验）<<<
# test.rep 指定置换检验次数（>0 时启用）
model_test <- nca_analysis(dat, x='x1', y='y', test.rep=10000)
print(model_test)  # p<0.05显著

# >>> 效力分析 <<<
power_result <- nca_power(effect=0.1, n=c(50,100,200))
print(power_result)

# ================= 可复现性元数据（sessionInfo 快照）=================
# 记录 R 版本与全部已加载包的版本号。这是防止
# R 包版本漂移导致结论不可复现的最小保障。写入失败必须可见（非 fail-silent）。
.obhrm_si <- try(writeLines(capture.output(sessionInfo()), "sessionInfo.txt"), silent = TRUE)
if (inherits(.obhrm_si, "try-error")) {
  message("警告：sessionInfo.txt 写入失败（工作目录可能只读），复现元数据未落盘")
} else if (exists("OBHRM_SEED")) {
  cat(sprintf("random_seed: %s\n", OBHRM_SEED), file = "sessionInfo.txt", append = TRUE)
}
