# T检验  （方法编号 6.3）
# @method   T检验
# @chapter  第6章
# @input    用户提供 CSV 数据文件（G3 门禁）：Rscript 6.3.R 数据.csv [变量列...]
# @use_cond 独立样本T检验：两组独立、因变量近似正态、方差齐性（Levene检验p>0.05）。配对T检验：差值近似正态。
# @deps     car, effsize
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
ensure_pkg("car")
ensure_pkg("effsize")

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
# T检验 — R基础stats包
# ============================================================
# 比较两组均值差异
# 独立样本：两个不同组别（如男vs女）
# 配对样本：同一组被试前后测比较
# ============================================================

# ---- 将 dat 替换为数据框名 ----
# ---- 将 Ideal 替换为因变量名，Gender 替换为分组变量名 ----

# 步骤1：独立样本T检验（两组独立）
# 原假设H0：两组均值相等
# p<0.05 -> 两组均值有显著差异
t.test(Ideal ~ Gender, data=dat)

# 步骤2：配对样本T检验（同一组前后测）
# paired=TRUE表示配对设计
t.test(dat$pre, dat$post, paired=TRUE)

# 步骤3：检查前提假设
# 正态性检验（Shapiro-Wilk）
shapiro.test(dat$Ideal)  # p>0.05满足正态
# 方差齐性检验（Levene检验）
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('car')
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('effsize')
library(car)
leveneTest(Ideal ~ Gender, data=dat)  # p>0.05方差齐

# 步骤4：效应量（Cohen's d）
library(effsize)
cohen.d(Ideal ~ Gender, data=dat)
# d=0.2小效应, 0.5中等效应, 0.8大效应

# ================= 可复现性元数据（sessionInfo 快照）=================
# 记录 R 版本与全部已加载包的版本号。这是防止
# R 包版本漂移导致结论不可复现的最小保障。写入失败必须可见（非 fail-silent）。
.obhrm_si <- try(writeLines(capture.output(sessionInfo()), "sessionInfo.txt"), silent = TRUE)
if (inherits(.obhrm_si, "try-error")) {
  message("警告：sessionInfo.txt 写入失败（工作目录可能只读），复现元数据未落盘")
} else if (exists("OBHRM_SEED")) {
  cat(sprintf("random_seed: %s\n", OBHRM_SEED), file = "sessionInfo.txt", append = TRUE)
}
