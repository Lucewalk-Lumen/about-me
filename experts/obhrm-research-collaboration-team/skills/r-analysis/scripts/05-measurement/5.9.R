# 判别效度检验（HTMT / Fornell-Larcker）  （方法编号 5.9）
# @method   判别效度检验（HTMT / Fornell-Larcker）
# @chapter  第5章
# @input    用户提供 CSV 数据文件（G3 门禁）：Rscript 5.9.R 数据.csv [变量列...]
# @use_cond 已建立 CFA 测量模型；适用于 ≥2 个潜变量的模型。
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
# ---- 将 dat 替换为数据框名，x1-x9 替换为你的量表题目 ----
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('lavaan')
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('semTools')
library(lavaan)
library(semTools)

# 步骤1：拟合多因子CFA模型
cfa_model <- '
  f1 =~ x1 + x2 + x3
  f2 =~ x4 + x5 + x6
  f3 =~ x7 + x8 + x9
'
fit <- cfa(cfa_model, data=dat)

# 步骤2：计算聚合效度（AVE，平均方差抽取量）
AVE(fit)
# 每个构念 AVE > 0.5 → 聚合效度良好
# 组合信度（omega）用 compRelSEM()，> 0.7 信度良好
compRelSEM(fit)

# 步骤3：Fornell-Larcker 准则
# 潜变量相关矩阵
cor_lv <- lavInspect(fit, 'cor.lv')
print(cor_lv)
# 判断：每个构念 sqrt(AVE) 应 > 它与任何其他构念的相关系数
sqrt_ave <- sqrt(AVE(fit))
print(sqrt_ave)
# 若某构念的 sqrt(AVE) < 它与其他构念的相关系数 → 判别效度存疑

# 步骤4：HTMT 比率（推荐，更稳健）
htmt(cfa_model, data=dat)
# HTMT < 0.85（严格）或 < 0.90（宽松）→ 判别效度成立

# ================= 可复现性元数据（sessionInfo 快照）=================
# 记录 R 版本与全部已加载包的版本号。这是防止
# R 包版本漂移导致结论不可复现的最小保障。写入失败必须可见（非 fail-silent）。
.obhrm_si <- try(writeLines(capture.output(sessionInfo()), "sessionInfo.txt"), silent = TRUE)
if (inherits(.obhrm_si, "try-error")) {
  message("警告：sessionInfo.txt 写入失败（工作目录可能只读），复现元数据未落盘")
} else if (exists("OBHRM_SEED")) {
  cat(sprintf("random_seed: %s\n", OBHRM_SEED), file = "sessionInfo.txt", append = TRUE)
}
