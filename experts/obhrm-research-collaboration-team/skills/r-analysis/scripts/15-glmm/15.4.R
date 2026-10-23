# 多层中介效应模型  （方法编号 15.4）
# @method   多层中介效应模型
# @chapter  第15章
# @input    用户提供 CSV 数据文件（G3 门禁）：Rscript 15.4.R 数据.csv [变量列...]
# @use_cond 数据具有嵌套结构；总组数>20。
# @deps     dplyr, lavaan, lme4, lmerTest, mediation, misty
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
ensure_pkg("lavaan")
ensure_pkg("lme4")
ensure_pkg("lmerTest")
ensure_pkg("mediation")
ensure_pkg("misty")

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
# 多层中介效应模型 — lme4 + lmerTest + mediation包
# ============================================================
# 在嵌套数据中检验中介效应
# 常见类型：
#   1-1-1：X,M,Y均在Level 1（需CWC中心化分离组内/组间效应）
#   2-1-1：X在Level 2，M,Y在Level 1（最常见）
#   2-2-1：X,M在Level 2，Y在Level 1
#
# 模型结构示意（2-1-1）：
#   Level 2: group_id → X(组级变量)
#   Level 1: M → Y (个体级)
#   X → M → Y（跨层中介）
# ============================================================

# ---- 安装并加载包 ----
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('lme4')
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('lmerTest')
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('mediation')
library(lme4)                    # 加载lme4
library(lmerTest)                # 加载lmerTest
library(mediation)               # 加载mediation

# ---- 将 X/M/Y 替换为自变量/中介变量/因变量，group_id 替换为分组变量（注意与数据列名一致）----

# 步骤1：a路径模型（X→M）
model_a <- lmer(M ~ X + (1 | group_id), data=dat)
# 步骤2：b路径模型（M→Y，控制X）
model_b <- lmer(Y ~ M + X + (1 | group_id), data=dat)

# 步骤3：中介效应检验（Bootstrap）
set.seed(123)
med_result <- mediate(model_a, model_b,
                      treat='X',          # 自变量
                      mediator='M',       # 中介变量
                      sims=500)           # Bootstrap次数
summary(med_result)
# ACME(平均因果中介效应)：间接效应，p<0.05则中介显著
# ADE(平均直接效应)：直接效应
# Total Effect：总效应=ACME+ADE

# ================= 可复现性元数据（sessionInfo 快照）=================
# 记录 R 版本与全部已加载包的版本号。这是防止
# R 包版本漂移导致结论不可复现的最小保障。写入失败必须可见（非 fail-silent）。
.obhrm_si <- try(writeLines(capture.output(sessionInfo()), "sessionInfo.txt"), silent = TRUE)
if (inherits(.obhrm_si, "try-error")) {
  message("警告：sessionInfo.txt 写入失败（工作目录可能只读），复现元数据未落盘")
} else if (exists("OBHRM_SEED")) {
  cat(sprintf("random_seed: %s\n", OBHRM_SEED), file = "sessionInfo.txt", append = TRUE)
}
