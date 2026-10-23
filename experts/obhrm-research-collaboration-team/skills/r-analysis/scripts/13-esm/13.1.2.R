# ESM多层中介（1-1-1模型）  （方法编号 13.1.2）
# @method   ESM多层中介（1-1-1模型）
# @chapter  第13章
# @input    用户提供 CSV 数据文件（G3 门禁）：Rscript 13.1.2.R 数据.csv [变量列...]
# @use_cond 密集纵向数据；X、M、Y 均为个体内变量。
# @deps     dplyr, lme4, lmerTest, mediation
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
ensure_pkg("mediation")

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
# ESM多层中介：X→M→Y 均在个体内水平（1-1-1模型）
# ============================================================
# 需对X和M都做CWC中心化，分离个体内/间效应
# 只关注个体内的中介路径（同一时间点内X→M→Y）
# ============================================================
# ---- 将 dat_long 替换为长格式数据框名 ----
# ---- 将 x/m/y/subj_id 替换为变量名 ----

# 步骤1：CWC中心化X和M
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('dplyr')
library(dplyr)
dat_long <- dat_long %>%
  group_by(subj_id) %>%
  mutate(x_cwc = x - mean(x, na.rm=TRUE),   # X的个体内中心化
         m_cwc = m - mean(m, na.rm=TRUE)) %>% # M的个体内中心化
  ungroup()

# 步骤2：a路径（X→M）
model_a <- lmer(m_cwc ~ x_cwc + (1 | subj_id), data=dat)

# 步骤3：b路径（M→Y，控制X）
model_b <- lmer(y ~ m_cwc + x_cwc + (1 | subj_id), data=dat)

# 步骤4：中介效应检验（Bootstrap）
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('mediation')
library(mediation)
set.seed(123)
med_result <- mediate(model_a, model_b,
                      treat='x_cwc',       # 自变量（个体内X）
                      mediator='m_cwc',     # 中介变量（个体内M）
                      sims=500)
summary(med_result)
# ACME=间接效应（个体内X→M→Y），p<0.05则中介显著

# ================= 可复现性元数据（sessionInfo 快照）=================
# 记录 R 版本与全部已加载包的版本号。这是防止
# R 包版本漂移导致结论不可复现的最小保障。写入失败必须可见（非 fail-silent）。
.obhrm_si <- try(writeLines(capture.output(sessionInfo()), "sessionInfo.txt"), silent = TRUE)
if (inherits(.obhrm_si, "try-error")) {
  message("警告：sessionInfo.txt 写入失败（工作目录可能只读），复现元数据未落盘")
} else if (exists("OBHRM_SEED")) {
  cat(sprintf("random_seed: %s\n", OBHRM_SEED), file = "sessionInfo.txt", append = TRUE)
}
