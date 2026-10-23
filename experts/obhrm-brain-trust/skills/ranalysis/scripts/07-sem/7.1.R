# 结构方程模型分析（SEM）  （方法编号 7.1）
# @method   结构方程模型分析（SEM）
# @chapter  第7章
# @input    用户提供 CSV 数据文件（G3 门禁）：Rscript 7.1.R 数据.csv [变量列...]
# @use_cond 样本量>200（建议>10倍自由度）；数据近似多元正态；模型可识别（每个潜变量至少3个指标）。
# @deps     lavaan, semPlot
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
ensure_pkg("lavaan")
ensure_pkg("semPlot")

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
# 结构方程模型分析（SEM） — lavaan包
# ============================================================
# 同时包含测量模型（=~定义潜变量）和结构模型（~定义因果路径）
#
# 模型结构示意：
#   测量模型：f1 =~ y1+y2+y3,  f2 =~ y4+y5+y6
#   结构模型：f2 ~ f1（f1对f2的因果效应）
# ============================================================

# ---- 安装并加载包 ----
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('lavaan')

# ---- 将 y1-y12/f1-f4 替换为你的变量名和因子名 ----

# 步骤1：指定SEM模型
sem_model <- '
  # 测量模型（=~定义潜变量）
  f1 =~ y1 + y2 + y3        # 因子f1由y1,y2,y3测量
  f2 =~ y4 + y5 + y6        # 因子f2由y4,y5,y6测量
  f3 =~ y7 + y8 + y9        # 因子f3由y7,y8,y9测量
  f4 =~ y10 + y11 + y12     # 因子f4由y10,y11,y12测量

  # 结构模型（~定义因果路径）
  f3 ~ f1 + f2              # f1和f2预测f3
  f4 ~ f3 + f2              # f3和f2预测f4
'

# 步骤2：拟合SEM模型
sem_fit <- sem(sem_model, data=dat)
summary(sem_fit, fit.measures=TRUE, standardized=TRUE)
# 拟合指标：CFI/TLI>0.90, RMSEA<0.08, SRMR<0.08
# 路径系数：std.all列（标准化系数，可比较大小）

# 步骤3：路径图可视化
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('semPlot')
semPaths(sem_fit, whatLabels='std', layout='tree')  # 标准化系数路径图
# ---- 将 y1-y3/x1-x3 替换为你的变量名 ----
# 步骤1：指定路径模型
path_model <- '
  y1 ~ x1 + x2          # x1和x2预测y1
  y2 ~ y1 + x3          # y1和x3预测y2
  y3 ~ y2 + x1          # y2和x1预测y3
  y1 ~~ y3              # y1和y3的残差相关
'
# 步骤2：拟合路径模型
path_fit <- sem(path_model, data=dat)
summary(path_fit, fit.measures=TRUE, standardized=TRUE)
# 解读：标准化路径系数(Std.all)用于比较路径大小，p<0.05表示路径显著

# ================= 可复现性元数据（sessionInfo 快照）=================
# 记录 R 版本与全部已加载包的版本号。这是防止
# R 包版本漂移导致结论不可复现的最小保障。写入失败必须可见（非 fail-silent）。
.obhrm_si <- try(writeLines(capture.output(sessionInfo()), "sessionInfo.txt"), silent = TRUE)
if (inherits(.obhrm_si, "try-error")) {
  message("警告：sessionInfo.txt 写入失败（工作目录可能只读），复现元数据未落盘")
} else if (exists("OBHRM_SEED")) {
  cat(sprintf("random_seed: %s\n", OBHRM_SEED), file = "sessionInfo.txt", append = TRUE)
}
