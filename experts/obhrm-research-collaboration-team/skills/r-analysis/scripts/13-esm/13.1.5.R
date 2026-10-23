# ESM有调节的多层中介  （方法编号 13.1.5）
# @method   ESM有调节的多层中介
# @chapter  第13章
# @input    用户提供 CSV 数据文件（G3 门禁）：Rscript 13.1.5.R 数据.csv [变量列...]
# @use_cond 密集纵向数据；有个体间调节变量。
# @deps     dplyr, lme4, lmerTest
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
# ESM有调节的中介：调节变量W影响中介路径的强度
# ============================================================
# 模型结构：
#   Level 2: W(个体间调节变量)
#   Level 1: X→M→Y（个体内中介路径）
#   W调节a路径（X→M的强度随W变化）
# ============================================================
# ---- 将 dat_long 替换为长格式数据框名 ----
# ---- 将 x/m/y/w/subj_id 替换为变量名 ----
# ---- W为个体间变量（如人格特质），不随时间变化 ----

# 步骤1：CWC中心化Level 1变量
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('dplyr')
library(dplyr)
dat_long <- dat_long %>%
  group_by(subj_id) %>%
  mutate(x_cwc = x - mean(x, na.rm=TRUE),
         m_cwc = m - mean(m, na.rm=TRUE)) %>%
  ungroup()

# 步骤2：a路径含交互项（X*W→M）
model_a <- lmer(m_cwc ~ x_cwc * w + (1 | subj_id),
                data=dat)
# x_cwc:w 交互项显著 -> W调节X→M路径

# 步骤3：b路径（M→Y）
model_b <- lmer(y ~ m_cwc + x_cwc + w + (1 | subj_id),
                data=dat)

# 步骤4：条件间接效应（在不同W水平下）
# W低时：ind_low = (a1 + a3*W_low) * b
# W高时：ind_high = (a1 + a3*W_high) * b
# a1 = X→M的主效应，a3 = 交互项系数
a1 <- fixef(model_a)['x_cwc']
a3 <- fixef(model_a)['x_cwc:w']
b <- fixef(model_b)['m_cwc']

W_low <- mean(dat_long$w) - sd(dat_long$w)  # W低于均值1SD
W_high <- mean(dat_long$w) + sd(dat_long$w)  # W高于均值1SD
ind_low <- (a1 + a3 * W_low) * b     # W低时的间接效应
ind_high <- (a1 + a3 * W_high) * b   # W高时的间接效应
cat(sprintf('W低: ind=%.4f, W高: ind=%.4f\n', ind_low, ind_high))
# 若ind_low和ind_high符号或大小不同 -> 有调节的中介效应

# ================= 可复现性元数据（sessionInfo 快照）=================
# 记录 R 版本与全部已加载包的版本号。这是防止
# R 包版本漂移导致结论不可复现的最小保障。写入失败必须可见（非 fail-silent）。
.obhrm_si <- try(writeLines(capture.output(sessionInfo()), "sessionInfo.txt"), silent = TRUE)
if (inherits(.obhrm_si, "try-error")) {
  message("警告：sessionInfo.txt 写入失败（工作目录可能只读），复现元数据未落盘")
} else if (exists("OBHRM_SEED")) {
  cat(sprintf("random_seed: %s\n", OBHRM_SEED), file = "sessionInfo.txt", append = TRUE)
}
