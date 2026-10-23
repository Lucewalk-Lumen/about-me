# 多元线性回归  （方法编号 6.10）
# @method   多元线性回归
# @chapter  第6章
# @input    用户提供 CSV 数据文件（G3 门禁）：Rscript 6.10.R 数据.csv [变量列...]
# @use_cond 因变量连续；样本量至少为预测变量数的 10-15 倍；无严重多重共线性（VIF<10）。
# @deps     car
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
ensure_pkg("car")

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
# 多元线性回归 — car包
# ============================================================
# 检验多个自变量对因变量的预测作用
# 核心假设：线性、独立性、正态性、方差齐性、无多重共线性
#
# 模型：Y = b0 + b1*x1 + b2*x2 + b3*x3 + e
# ============================================================

# ---- 安装并加载包 ----
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('car')

# ---- 将 dat 替换为数据框名 ----
# ---- 将 y/x1/x2/x3 替换为因变量/自变量名 ----

# 步骤1：拟合回归模型
model1 <- lm(y ~ x1, data=dat)             # 一元回归
model2 <- lm(y ~ x1 + x2 + x3, data=dat)   # 多元回归
summary(model2)  # 输出：回归系数、t值、p值、R方

# 步骤2：回归诊断
# 多重共线性检验（VIF<5为可接受）
vif(model2)
# 残差正态性
qqPlot(model2)
# 方差齐性
plot(model2, 1)  # 残差vs拟合值图
# 独立性检验
durbinWatsonTest(model2)  # DW值接近2为独立

# 步骤3：标准化回归系数（比较自变量相对重要性）
summary(lm(scale(y) ~ scale(x1) + scale(x2) + scale(x3), data=dat))

# ================= 可复现性元数据（sessionInfo 快照）=================
# 记录 R 版本与全部已加载包的版本号。这是防止
# R 包版本漂移导致结论不可复现的最小保障。写入失败必须可见（非 fail-silent）。
.obhrm_si <- try(writeLines(capture.output(sessionInfo()), "sessionInfo.txt"), silent = TRUE)
if (inherits(.obhrm_si, "try-error")) {
  message("警告：sessionInfo.txt 写入失败（工作目录可能只读），复现元数据未落盘")
} else if (exists("OBHRM_SEED")) {
  cat(sprintf("random_seed: %s\n", OBHRM_SEED), file = "sessionInfo.txt", append = TRUE)
}
