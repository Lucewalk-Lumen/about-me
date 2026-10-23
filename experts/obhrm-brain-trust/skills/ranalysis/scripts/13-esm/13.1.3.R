# ESM双中介（并行多重中介）  （方法编号 13.1.3）
# @method   ESM双中介（并行多重中介）
# @chapter  第13章
# @input    用户提供 CSV 数据文件（G3 门禁）：Rscript 13.1.3.R 数据.csv [变量列...]
# @use_cond 密集纵向数据；两个中介均为个体内变量。
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
# ============================================================
# ESM双中介：X通过M1和M2两条平行路径影响Y
# ============================================================
# 模型结构：
#   X ──→ M1 ──→ Y  （间接效应1）
#    \               ↑
#     ──→ M2 ────────┘  （间接效应2）
# ============================================================
# ---- 将 dat_long 替换为长格式数据框名 ----
# ---- 将 x/m1/m2/y/subj_id 替换为变量名 ----

# 步骤1：CWC中心化所有Level 1变量
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('dplyr')
dat_long <- dat_long %>%
  group_by(subj_id) %>%
  mutate(x_cwc = x - mean(x, na.rm=TRUE),
         m1_cwc = m1 - mean(m1, na.rm=TRUE),
         m2_cwc = m2 - mean(m2, na.rm=TRUE)) %>%
  ungroup()

# 步骤2：a路径（X→M1和X→M2）
model_m1 <- lmer(m1_cwc ~ x_cwc + (1 | subj_id), data=dat)
model_m2 <- lmer(m2_cwc ~ x_cwc + (1 | subj_id), data=dat)

# 步骤3：b路径（M1和M2同时预测Y）
model_y <- lmer(y ~ m1_cwc + m2_cwc + x_cwc + (1 | subj_id),
                data=dat)

# 步骤4：计算双中介效应
a1 <- fixef(model_m1)['x_cwc']  # X→M1的a1系数
a2 <- fixef(model_m2)['x_cwc']  # X→M2的a2系数
b1 <- fixef(model_y)['m1_cwc']  # M1→Y的b1系数
b2 <- fixef(model_y)['m2_cwc']  # M2→Y的b2系数
ind1 <- a1 * b1  # 通过M1的间接效应
ind2 <- a2 * b2  # 通过M2的间接效应
contrast <- ind1 - ind2  # 两条路径的差异
cat(sprintf('Ind1=%.4f, Ind2=%.4f, Contrast=%.4f\n', ind1, ind2, contrast))

# ================= 可复现性元数据（sessionInfo 快照）=================
# 记录 R 版本与全部已加载包的版本号。这是防止
# R 包版本漂移导致结论不可复现的最小保障。写入失败必须可见（非 fail-silent）。
.obhrm_si <- try(writeLines(capture.output(sessionInfo()), "sessionInfo.txt"), silent = TRUE)
if (inherits(.obhrm_si, "try-error")) {
  message("警告：sessionInfo.txt 写入失败（工作目录可能只读），复现元数据未落盘")
} else if (exists("OBHRM_SEED")) {
  cat(sprintf("random_seed: %s\n", OBHRM_SEED), file = "sessionInfo.txt", append = TRUE)
}
