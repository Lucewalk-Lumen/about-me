# LPA含协变量（主效应）  （方法编号 9.1.2）
# @method   LPA含协变量（主效应）
# @chapter  第9章
# @input    用户提供 CSV 数据文件（G3 门禁）：Rscript 9.1.2.R 数据.csv [变量列...]
# @use_cond  已完成基础 LPA（剖面识别）并确定剖面数；需具备 tidyLPA 包；用于检验剖面对协变量的主效应，指标变量须为连续型，剖面数需与基础 LPA 结果一致。
# @deps     tidyLPA
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
ensure_pkg("tidyLPA")

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
# LPA含协变量：检验协变量对剖面归属的预测作用
# ============================================================
# ---- 将 cov1/cov2 替换为协变量名（如性别、年龄） ----

# 步骤1：用tidyLPA拟合含协变量的模型
# covariates参数指定预测剖面归属的变量
lpa_cov <- estimate_profiles(
  dat[, c('x1','x2','x3')],
  n_profiles=3,               # 剖面数（基于7.1.1的结果）
  models=6,                   # 模型类型（6=方差自由估计）
  covariates=c('cov1','cov2') # 协变量预测剖面归属
)

# 步骤2：查看协变量对剖面归属的影响
summary(lpa_cov)
# 输出：协变量预测剖面归属的逻辑回归系数
# 系数显著 -> 该协变量影响属于某剖面的概率

# 步骤3：另一种方法 — 增长混合模型（GMM，纵向数据的潜类别）
# 先识别剖面，再分析协变量（避免分类不确定性影响）。
# 备选实现：若已装有 lcmm 包，可用其中的 hlme 函数以 mixture 参数拟合 GMM；
# 本脚本默认不加载 lcmm，以免在未安装该包的环境中中断。

# ================= 可复现性元数据（sessionInfo 快照）=================
# 记录 R 版本与全部已加载包的版本号。这是防止
# R 包版本漂移导致结论不可复现的最小保障。写入失败必须可见（非 fail-silent）。
.obhrm_si <- try(writeLines(capture.output(sessionInfo()), "sessionInfo.txt"), silent = TRUE)
if (inherits(.obhrm_si, "try-error")) {
  message("警告：sessionInfo.txt 写入失败（工作目录可能只读），复现元数据未落盘")
} else if (exists("OBHRM_SEED")) {
  cat(sprintf("random_seed: %s\n", OBHRM_SEED), file = "sessionInfo.txt", append = TRUE)
}
