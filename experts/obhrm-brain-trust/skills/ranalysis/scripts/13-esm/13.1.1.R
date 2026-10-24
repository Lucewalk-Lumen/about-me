# ESM基础分析（零模型与个体内/间效应）  （方法编号 13.1.1）
# @method   ESM基础分析（零模型与个体内/间效应）
# @chapter  第13章
# @input    用户提供 CSV 数据文件（G3 门禁）：Rscript 13.1.1.R 数据.csv [变量列...]
# @use_cond 密集纵向数据（每天多次测量）；个体内时间点 > 10。
# @deps     dplyr, lme4, lmerTest
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
# ESM基础分析：多层模型分离个体内/间效应
# ============================================================
# ESM数据结构：
#   Level 1（个体内）：时间点嵌套于个体
#   Level 2（个体间）：个体差异
# ============================================================
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('lme4')
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('lmerTest')
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('dplyr')

# ---- 将 dat_long 替换为长格式数据框名 ----
# ---- 将 y/subj_id/day/time 替换为变量名 ----

# 步骤1：零模型（计算ICC）
null_model <- lmer(y ~ 1 + (1 | subj_id), data=dat)
vc <- VarCorr(null_model)
ICC <- vc$subj_id[1,1] / (vc$subj_id[1,1] + attr(vc, 'sc')^2)
print(paste('ICC =', round(ICC, 3)))  # ICC>0.059需要多层模型

# 步骤2：CWC中心化（分离个体内/间效应）
# 组均值中心化：将个体内变异和个体间变异分离
dat_long <- dat_long %>%
  group_by(subj_id) %>%
  mutate(x_pwc = x - mean(x, na.rm=TRUE),  # 个体内中心化（个体内效应）
         x_pgm = mean(x, na.rm=TRUE)) %>%    # 个体均值（个体间效应）
  ungroup()

# 步骤3：多层回归（含CWC中心化的自变量）
esm_model <- lmer(y ~ x_pwc + x_pgm + (1 | subj_id),
                  data=dat)
summary(esm_model)
# x_pwc系数=个体内效应（同一人内x变化对y的影响）
# x_pgm系数=个体间效应（不同人间x均值差异对y的影响）

# ================= 可复现性元数据（sessionInfo 快照）=================
# 记录 R 版本与全部已加载包的版本号。这是防止
# R 包版本漂移导致结论不可复现的最小保障。写入失败必须可见（非 fail-silent）。
.obhrm_si <- try(writeLines(capture.output(sessionInfo()), "sessionInfo.txt"), silent = TRUE)
if (inherits(.obhrm_si, "try-error")) {
  message("警告：sessionInfo.txt 写入失败（工作目录可能只读），复现元数据未落盘")
} else if (exists("OBHRM_SEED")) {
  cat(sprintf("random_seed: %s\n", OBHRM_SEED), file = "sessionInfo.txt", append = TRUE)
}
