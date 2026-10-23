# ESM链式中介  （方法编号 13.1.4）
# @method   ESM链式中介
# @chapter  第13章
# @input    用户提供 CSV 数据文件（G3 门禁）：Rscript 13.1.4.R 数据.csv [变量列...]
# @use_cond 密集纵向数据；中介变量间有理论上的先后顺序。
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
# ESM链式中介：X→M1→M2→Y 序列传递
# ============================================================
# 模型结构：
#   X ──→ M1 ──→ M2 ──→ Y
#   （三级链式传递）
# ============================================================
# ---- 将 dat_long 替换为长格式数据框名 ----
# ---- 将 x/m1/m2/y/subj_id 替换为变量名 ----

# 步骤1：CWC中心化
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('dplyr')
library(dplyr)
dat_long <- dat_long %>%
  group_by(subj_id) %>%
  mutate(x_cwc = x - mean(x, na.rm=TRUE),
         m1_cwc = m1 - mean(m1, na.rm=TRUE),
         m2_cwc = m2 - mean(m2, na.rm=TRUE)) %>%
  ungroup()

# 步骤2：a路径
# X→M1
model_m1 <- lmer(m1_cwc ~ x_cwc + (1 | subj_id), data=dat)
# X→M2（控制M1，检验M1→M2的路径d21）
model_m2 <- lmer(m2_cwc ~ x_cwc + m1_cwc + (1 | subj_id),
                 data=dat)

# 步骤3：b路径（M2→Y，控制X和M1）
model_y <- lmer(y ~ m2_cwc + m1_cwc + x_cwc + (1 | subj_id),
                data=dat)

# 步骤4：计算链式间接效应
a1 <- fixef(model_m1)['x_cwc']     # X→M1
d21 <- fixef(model_m2)['m1_cwc']   # M1→M2
b2 <- fixef(model_y)['m2_cwc']      # M2→Y
ind_serial <- a1 * d21 * b2  # 链式间接效应=a1*d21*b2
cat(sprintf('Serial indirect effect = %.4f\n', ind_serial))
# 用Bootstrap检验显著性（参考6.12 Bootstrapping方法）

# ================= 可复现性元数据（sessionInfo 快照）=================
# 记录 R 版本与全部已加载包的版本号。这是防止
# R 包版本漂移导致结论不可复现的最小保障。写入失败必须可见（非 fail-silent）。
.obhrm_si <- try(writeLines(capture.output(sessionInfo()), "sessionInfo.txt"), silent = TRUE)
if (inherits(.obhrm_si, "try-error")) {
  message("警告：sessionInfo.txt 写入失败（工作目录可能只读），复现元数据未落盘")
} else if (exists("OBHRM_SEED")) {
  cat(sprintf("random_seed: %s\n", OBHRM_SEED), file = "sessionInfo.txt", append = TRUE)
}
