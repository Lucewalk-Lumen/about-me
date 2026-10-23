# 多层验证性因素分析（MCFA）  （方法编号 7.6）
# @method   多层验证性因素分析（MCFA）
# @chapter  第7章
# @input    用户提供 CSV 数据文件（G3 门禁）：Rscript 7.6.R 数据.csv [变量列...]
# @use_cond 数据具有嵌套结构；ICC>0.10。
# @deps     lavaan
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
ensure_pkg("lavaan")

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
# 多层验证性因素分析（MCFA） — lavaan包
# ============================================================
# 在嵌套数据中检验因子结构
# 区分组内（within）和组间（between）的因子结构
# ============================================================

# ---- 安装并加载包 ----
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('lavaan')
library(lavaan)              # 加载lavaan

# ---- 将 y1-y6/group_id 替换为变量名 ----

# 步骤1：指定双层CFA模型
# level: 1 = 组内结构（个体差异）
# level: 2 = 组间结构（组间差异）
mcfa_model <- '
  level: 1
    fw1 =~ y1 + y2 + y3     # 组内因子1
    fw2 =~ y4 + y5 + y6     # 组内因子2
  level: 2
    fb1 =~ y1 + y2 + y3     # 组间因子1
    fb2 =~ y4 + y5 + y6     # 组间因子2
'

# 步骤2：拟合MCFA模型
mcfa_fit <- cfa(mcfa_model, data=dat,
                cluster='group_id')  # 指定聚类变量
summary(mcfa_fit, fit.measures=TRUE, standardized=TRUE)
# 解读：组内因子结构和组间因子结构可以不同
# 比较与普通CFA的拟合差异

# ================= 可复现性元数据（sessionInfo 快照）=================
# 记录 R 版本与全部已加载包的版本号。这是防止
# R 包版本漂移导致结论不可复现的最小保障。写入失败必须可见（非 fail-silent）。
.obhrm_si <- try(writeLines(capture.output(sessionInfo()), "sessionInfo.txt"), silent = TRUE)
if (inherits(.obhrm_si, "try-error")) {
  message("警告：sessionInfo.txt 写入失败（工作目录可能只读），复现元数据未落盘")
} else if (exists("OBHRM_SEED")) {
  cat(sprintf("random_seed: %s\n", OBHRM_SEED), file = "sessionInfo.txt", append = TRUE)
}
