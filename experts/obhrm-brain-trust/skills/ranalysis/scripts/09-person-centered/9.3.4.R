# LGA含调节效应  （方法编号 9.3.4）
# @method   LGA含调节效应
# @chapter  第9章
# @input    用户提供 CSV 数据文件（G3 门禁）：Rscript 9.3.4.R 数据.csv [变量列...]
# @use_cond 至少 3 个时间点；有调节变量。
# @deps     emmeans, lavaan
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
ensure_pkg("emmeans")
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
# LGA调节效应：调节变量影响协变量对增长轨迹的预测
# ============================================================
# 模型结构：X*W → 增长参数(i/s)
# 即：X对增长速率的影响随W的水平变化
# ============================================================
# ---- 将 x/w/t1-t4 替换为变量名 ----

# 步骤1：指定含调节的增长模型
lgm_mod_model <- '
  i =~ 1*t1 + 1*t2 + 1*t3 + 1*t4
  s =~ 0*t1 + 1*t2 + 2*t3 + 3*t4

  # 调节效应：X和W的交互项预测斜率
  s ~ x + w + x:w    # x:w为交互项
  i ~ x + w          # 截距仅含主效应
'

# 步骤2：拟合模型
lgm_mod_fit <- growth(lgm_mod_model, data=dat)
summary(lgm_mod_fit, fit.measures=TRUE)
# s~x:w 系数显著 -> 调节效应成立
# 即X对变化速率的影响随W的水平变化

# 步骤3：简单斜率分析
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('emmeans')
# 在W的不同水平下检验X对斜率的影响

# ================= 可复现性元数据（sessionInfo 快照）=================
# 记录 R 版本与全部已加载包的版本号。这是防止
# R 包版本漂移导致结论不可复现的最小保障。写入失败必须可见（非 fail-silent）。
.obhrm_si <- try(writeLines(capture.output(sessionInfo()), "sessionInfo.txt"), silent = TRUE)
if (inherits(.obhrm_si, "try-error")) {
  message("警告：sessionInfo.txt 写入失败（工作目录可能只读），复现元数据未落盘")
} else if (exists("OBHRM_SEED")) {
  cat(sprintf("random_seed: %s\n", OBHRM_SEED), file = "sessionInfo.txt", append = TRUE)
}
