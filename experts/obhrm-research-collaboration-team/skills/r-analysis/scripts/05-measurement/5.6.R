# BiFactor验证性因素分析  （方法编号 5.6）
# @method   BiFactor验证性因素分析
# @chapter  第5章
# @input    用户提供 CSV 数据文件（G3 门禁）：Rscript 5.6.R 数据.csv [变量列...]
# @use_cond 量表既有总体维度又有子维度；样本量 > 200。
# @deps     lavaan, semTools
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
ensure_pkg("semTools")

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
# BiFactor验证性因素分析 — lavaan + semTools包
# ============================================================
# 所有题目在一个一般因子(g)上都有载荷
# 同时各自在特定群组因子上也有载荷
#
# 模型结构示意：
#   g (一般因子) ← 所有题目(y1-y12)
#   ├── f1 (群组因子1) ← y1, y2, y3
#   ├── f2 (群组因子2) ← y4, y5, y6
#   └── f3 (群组因子3) ← y7, y8, y9
# ============================================================

# ---- 安装并加载包 ----
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('lavaan')
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('semTools')
library(lavaan)                # 加载lavaan
library(semTools)              # 加载semTools

# ---- 将 y1-y12 替换为你的量表题目变量名 ----
# ---- 将 g/f1-f4 替换为因子名 ----

# 步骤1：指定BiFactor模型
bifactor_model <- '
  g =~ y1 + y2 + y3 + y4 + y5 + y6 +      # 一般因子：所有题目
       y7 + y8 + y9 + y10 + y11 + y12
  f1 =~ y1 + y2 + y3                       # 群组因子1
  f2 =~ y4 + y5 + y6                       # 群组因子2
  f3 =~ y7 + y8 + y9                       # 群组因子3
  f4 =~ y10 + y11 + y12                    # 群组因子4
'

# 步骤2：拟合BiFactor模型
# orthogonal=TRUE：一般因子与群组因子正交（不相关）
fit_bi <- cfa(bifactor_model, data=dat, orthogonal=TRUE)
summary(fit_bi, fit.measures=TRUE, standardized=TRUE)

# 步骤3：计算Omega信度（比Cronbach alpha更适合BiFactor）
# 用 semTools::compRelSEM() 输出模型基础信度（omega）
# 层级信度 omega_h：一般因子解释的方差比例（>0.50为高解释力）
compRelSEM(fit_bi)  # 输出 omega 信度；更高阶因子可用 higher= 参数指定

# ================= 可复现性元数据（sessionInfo 快照）=================
# 记录 R 版本与全部已加载包的版本号。这是防止
# R 包版本漂移导致结论不可复现的最小保障。写入失败必须可见（非 fail-silent）。
.obhrm_si <- try(writeLines(capture.output(sessionInfo()), "sessionInfo.txt"), silent = TRUE)
if (inherits(.obhrm_si, "try-error")) {
  message("警告：sessionInfo.txt 写入失败（工作目录可能只读），复现元数据未落盘")
} else if (exists("OBHRM_SEED")) {
  cat(sprintf("random_seed: %s\n", OBHRM_SEED), file = "sessionInfo.txt", append = TRUE)
}
