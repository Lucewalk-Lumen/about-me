# LGA有中介的调节  （方法编号 9.3.6）
# @method   LGA有中介的调节
# @chapter  第9章
# @input    用户提供 CSV 数据文件（G3 门禁）：Rscript 9.3.6.R 数据.csv [变量列...]
# @use_cond 至少 3 个时间点；有自变量、调节变量、结果。
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
# ================= 可复现性：固定随机种子 =================
# 本脚本含随机过程（bootstrap / 置换检验 / 随机初值 / 多重插补之一或多个）。
# 未固定种子时，同一份数据两次运行可能得出不同结论 —— 学术结论不可复现。
# 种子随结果一并输出（控制台 + sessionInfo.txt），供复核与他人复现。
OBHRM_SEED <- 20260101   # 全局随机种子
set.seed(OBHRM_SEED)
cat(sprintf("seed: %d\n", OBHRM_SEED))


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
# LGA有中介的调节：X与W的交互效应通过增长参数传递
# ============================================================
# 模型结构：
#   X * W ──→ 增长参数(i/s) ──→ Y(结果)
#   交互效应对增长参数的影响 -> 增长参数对结果的影响
# 关注：交互项(x:w)对增长参数的效应(a) * 增长参数对Y的效应(b)
# ============================================================
# ---- 将 x/m/y/w/t1-t4 替换为变量名 ----

# 步骤1：创建交互项
dat$xw <- dat$x * dat$w  # X与W的交互项

# 步骤2：指定有中介的调节增长模型
lgm_medmod_model <- '
  i =~ 1*t1 + 1*t2 + 1*t3 + 1*t4
  s =~ 0*t1 + 1*t2 + 2*t3 + 3*t4

  # a路径：交互项 -> 增长参数
  s ~ a1 * x + a2 * w + a3 * xw     # xw为交互项
  i ~ x + w + xw

  # b路径：增长参数 -> 结果
  y ~ b1 * i + b2 * s

  # 有中介的调节效应定义
  med_mod_s := a3 * b2   # 交互项通过斜率的中介效应
  med_mod_i := a3 * b1   # 交互项通过截距的中介效应
'

# 步骤3：拟合模型（Bootstrap检验）
lgm_medmod_fit <- sem(lgm_medmod_model, data=dat,
                      se='boot', bootstrap=5000)
summary(lgm_medmod_fit, fit.measures=TRUE)
# 查看med_mod_s和med_mod_i的Bootstrap置信区间
# CI不含0 -> 有中介的调节效应显著
# 即X*W交互效应通过改变增长轨迹进而影响结果变量

# ================= 可复现性元数据（sessionInfo 快照）=================
# 记录 R 版本与全部已加载包的版本号。这是防止
# R 包版本漂移导致结论不可复现的最小保障。写入失败必须可见（非 fail-silent）。
.obhrm_si <- try(writeLines(capture.output(sessionInfo()), "sessionInfo.txt"), silent = TRUE)
if (inherits(.obhrm_si, "try-error")) {
  message("警告：sessionInfo.txt 写入失败（工作目录可能只读），复现元数据未落盘")
} else if (exists("OBHRM_SEED")) {
  cat(sprintf("random_seed: %s\n", OBHRM_SEED), file = "sessionInfo.txt", append = TRUE)
}
