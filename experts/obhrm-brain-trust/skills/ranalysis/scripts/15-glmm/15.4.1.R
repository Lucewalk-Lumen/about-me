# 跨层次有调节的中介（Cross-level Moderated Mediation）  （方法编号 15.4.1）
# @method   跨层次有调节的中介（Cross-level Moderated Mediation）
# @chapter  第15章
# @input    用户提供 CSV 数据文件（G3 门禁）：Rscript 15.4.1.R 数据.csv [变量列...]
# @use_cond 数据具有嵌套结构（个体嵌套于组）；自变量X和中介M、因变量Y在Level-1测量；调节变量W在Level-2测量（组水平）；ICC>0.059；组数>30。
# @deps     lavaan, misty
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
ensure_pkg("misty")
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
# ---- 将 dat 替换为数据框名，x/m/y 替换为Level-1变量，w 替换为Level-2变量，group_id 替换为分组变量 ----
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('lavaan')
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('misty')

# >>> 数据准备：组均值中心化分离组内/组间效应 <<<
# 对Level-1变量做CWC(M)，生成组内成分和组间成分
dat <- center(dat, x, type='CWC', cluster='group_id')  # X组内中心化
dat <- center(dat, m, type='CWC', cluster='group_id')  # M组内中心化
dat <- center(dat, y, type='CWC', cluster='group_id')  # Y组内中心化
dat$x_cwc <- dat$x.c; dat$m_cwc <- dat$m.c; dat$y_cwc <- dat$y.c
# 组均值（Level-2组间成分）
dat$x_between <- ave(dat$x, dat$group_id)
# 创建Level-2交互项：W × X_between
dat$w_x_bet <- dat$w * dat$x_between  # 调节交互项

# >>> 模型结构图示 <<<
# Level-1（个体层）：
#   X_within --> M_within --> Y_within
#   (a路径)     (b路径)
# Level-2（组层）：
#   W 调节 a路径 或 b路径
#
#   W ~~~~~~> (a路径)
#            /
#   X --> M --> Y
#         ^
#   W ~~~~> (b路径)

# >>> 跨层次有调节的中介模型（W调节a路径）<<<
model_clmm <- '
  # Level-1：组内中介路径
  level: 1
    m_cwc ~ a * x_cwc             # a路径：X对M的效应（组内）
    y_cwc ~ b * m_cwc + x_cwc     # b路径：M对Y的效应 + X的直接效应
  # Level-2：组间调节
  level: 2
    m_cwc ~ a2 * w + w_x_bet      # W调节a路径：W对M的组间效应 + 交互项
    y_cwc ~ b2 * w + m_cwc         # W对Y的直接效应
  # 间接效应标签
  # 当W=低时：ind_low = a * b
  # 当W=高时：ind_high = (a + a2) * b
'
fit_clmm <- sem(model_clmm, data=dat, cluster='group_id',
                se='boot', bootstrap=1000)  # Bootstrap检验间接效应
summary(fit_clmm, fit.measures=TRUE, standardized=TRUE)

# >>> 条件间接效应计算 <<<
# 提取参数
pe <- parameterEstimates(fit_clmm, boot.ci.type='bca.simple')
a_val <- pe$est[pe$label=='a']         # a路径系数
a2_val <- pe$est[pe$label=='a2']      # W对a路径的调节系数
b_val <- pe$est[pe$label=='b']        # b路径系数
# W=均值-1SD（低W）时的间接效应
ind_low <- a_val * b_val              # 低W条件下的间接效应
# W=均值+1SD（高W）时的间接效应
ind_high <- (a_val + a2_val) * b_val  # 高W条件下的间接效应
cat('W=低时间接效应:', ind_low, '
')
cat('W=高时间接效应:', ind_high, '
')
cat('差异:', ind_high - ind_low, '
')

# >>> 简单斜率分析：检验不同W水平下的a路径 <<<
# W=低（均值-1SD）时a路径是否显著
# W=高（均值+1SD）时a路径是否显著
# 若差异显著，说明W调节了中介过程（有调节的中介成立）

# ================= 可复现性元数据（sessionInfo 快照）=================
# 记录 R 版本与全部已加载包的版本号。这是防止
# R 包版本漂移导致结论不可复现的最小保障。写入失败必须可见（非 fail-silent）。
.obhrm_si <- try(writeLines(capture.output(sessionInfo()), "sessionInfo.txt"), silent = TRUE)
if (inherits(.obhrm_si, "try-error")) {
  message("警告：sessionInfo.txt 写入失败（工作目录可能只读），复现元数据未落盘")
} else if (exists("OBHRM_SEED")) {
  cat(sprintf("random_seed: %s\n", OBHRM_SEED), file = "sessionInfo.txt", append = TRUE)
}
