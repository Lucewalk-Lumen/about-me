# 多因素方差分析（Factorial ANOVA）  （方法编号 6.5）
# @method   多因素方差分析（Factorial ANOVA）
# @chapter  第6章
# @input    用户提供 CSV 数据文件（G3 门禁）：Rscript 6.5.R 数据.csv [变量列...]
# @use_cond 两个及以上分类自变量；因变量连续；各单元格方差齐性。
# @deps     effectsize, emmeans
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
ensure_pkg("effectsize")
ensure_pkg("emmeans")

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
# 多因素方差分析（Factorial ANOVA） — emmeans + effectsize包
# ============================================================
# 同时检验两个或以上自变量的主效应及交互效应
# 交互效应显著时需进行简单主效应分析
# ============================================================

# ---- 安装并加载包 ----
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('emmeans')
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('effectsize')

# ---- 将 score/teaching_method/study_time 替换为变量名 ----

# 步骤1：拟合多因素ANOVA模型
# * 表示同时检验主效应和交互效应
model <- aov(score ~ teaching_method * study_time, data=dat)
summary(model)  # 输出：主效应、交互效应的F值和p值

# 步骤2：交互效应可视化（交互效应显著时）
interaction.plot(dat$teaching_method, dat$study_time, dat$score)
# interaction.plot 无 data 参数，需用 $ 或 with() 显式指定数据框
# 线条交叉 -> 存在交互效应

# 步骤3：简单主效应分析（交互效应显著时）
emmeans(model, ~ teaching_method | study_time)  # 固定study_time比较teaching_method
pairs(emmeans(model, ~ teaching_method | study_time))  # 两两比较

# 步骤4：效应量
eta_squared(model)  # 偏eta方

# ================= 可复现性元数据（sessionInfo 快照）=================
# 记录 R 版本与全部已加载包的版本号。这是防止
# R 包版本漂移导致结论不可复现的最小保障。写入失败必须可见（非 fail-silent）。
.obhrm_si <- try(writeLines(capture.output(sessionInfo()), "sessionInfo.txt"), silent = TRUE)
if (inherits(.obhrm_si, "try-error")) {
  message("警告：sessionInfo.txt 写入失败（工作目录可能只读），复现元数据未落盘")
} else if (exists("OBHRM_SEED")) {
  cat(sprintf("random_seed: %s\n", OBHRM_SEED), file = "sessionInfo.txt", append = TRUE)
}
