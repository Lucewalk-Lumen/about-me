# 调节效应分析  （方法编号 7.3）
# @method   调节效应分析
# @chapter  第7章
# @input    用户提供 CSV 数据文件（G3 门禁）：Rscript 7.3.R 数据.csv [变量列...]
# @use_cond 自变量与调节变量为连续或分类变量；建议先中心化以减少多重共线性。
# @deps     car, effects, pequod
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
ensure_pkg("effects")
ensure_pkg("pequod")

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
# 调节效应分析 — car + pequod包
# ============================================================
# 检验调节变量Z是否影响X与Y的关系
# 通过检验交互项(X*Z)是否显著实现
# 建议先中心化以减少多重共线性
#
# 模型：Y = b0 + b1*X + b2*Z + b3*(X*Z) + e
# b3显著 -> 存在调节效应
# ============================================================

# ---- 安装并加载包 ----
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('car')
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('pequod')
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('effects')
library(car)                  # 加载car
library(pequod)               # 加载pequod

# ---- 将 adjdep/adjsimp/adjfatal 替换为因变量/自变量/调节变量 ----

# 步骤1：拟合调节效应模型（含交互项）
# * 表示同时包含主效应和交互效应
mod_model <- lm(adjdep ~ adjsimp * adjfatal, data=dat)
summary(mod_model)  # 查看交互项adjsimp:adjfatal的系数和p值

# 步骤2：简单斜率分析（交互效应显著时）
# 在调节变量高/低水平下检验X对Y的效应
simp_slopes <- lmSlopes(mod_model, pred='adjsimp', mod='adjfatal')
summary(simp_slopes)

# 步骤3：交互效应可视化
library(effects)
eff <- effect('adjsimp * adjfatal', mod_model)
plot(eff)  # 绘制调节效应图（高/低调节变量下的回归线）

# 步骤4：多重调节（三重交互，多个调节变量）
# 检验 X 的效应是否同时受两个调节变量 Z1、Z2 影响
# 注：以下 X / Z1 / Z2 / Y 为模型角色名，运行前请替换为数据中的实际列名
dat$XZ1 <- dat$X * dat$Z1
dat$XZ2 <- dat$X * dat$Z2
dat$Z1Z2 <- dat$Z1 * dat$Z2
dat$XZ1Z2 <- dat$X * dat$Z1 * dat$Z2
triple_model <- lm(Y ~ X + Z1 + Z2 + XZ1 + XZ2 + Z1Z2 + XZ1Z2, data=dat)
summary(triple_model)
# 三重交互项 XZ1Z2 显著：X 的调节效应随另一个调节变量的水平变化
# （即调节的调节，需进一步做条件交互的简单斜率分析）

# ================= 可复现性元数据（sessionInfo 快照）=================
# 记录 R 版本与全部已加载包的版本号。这是防止
# R 包版本漂移导致结论不可复现的最小保障。写入失败必须可见（非 fail-silent）。
.obhrm_si <- try(writeLines(capture.output(sessionInfo()), "sessionInfo.txt"), silent = TRUE)
if (inherits(.obhrm_si, "try-error")) {
  message("警告：sessionInfo.txt 写入失败（工作目录可能只读），复现元数据未落盘")
} else if (exists("OBHRM_SEED")) {
  cat(sprintf("random_seed: %s\n", OBHRM_SEED), file = "sessionInfo.txt", append = TRUE)
}
