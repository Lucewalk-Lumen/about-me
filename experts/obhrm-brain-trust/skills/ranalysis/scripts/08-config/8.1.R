# 模糊集定性比较分析（fsQCA）  （方法编号 8.1）
# @method   模糊集定性比较分析（fsQCA）
# @chapter  第8章
# @input    用户提供 CSV 数据文件（G3 门禁）：Rscript 8.1.R 数据.csv [变量列...]
# @use_cond 样本量10-200；条件变量4-8个和1个结果变量；数据可校准为模糊集；理论驱动的条件选择。
# @deps     QCA
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
ensure_pkg("QCA")

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
# ---- 将 dat 替换为数据框名，条件变量和结果变量替换为你的变量名 ----
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('QCA')

# >>> 步骤1：数据校准（Calibration）<<<
# 将原始变量转换为0-1的模糊集成员分数
# thresholds=c(完全不隶属, 交叉点, 完全隶属)
# ---- 将 cond1/cond2/cond3 替换为条件变量名，outcome 替换为结果变量名 ----
dat$fA <- calibrate(dat$cond1, thresholds=c(3, 5, 7))  # 校准条件A
dat$fB <- calibrate(dat$cond2, thresholds=c(2, 4, 6))  # 校准条件B
dat$fC <- calibrate(dat$cond3, thresholds=c(3, 5, 7))  # 校准条件C
dat$fY <- calibrate(dat$outcome, thresholds=c(3, 5, 7)) # 校准结果变量

# >>> 步骤2：必要性分析 <<<
# 一致性(inclusion) >= 0.9 表示该条件是必要条件
# 方法A：pof() 逐个检验单一条件的必要性（relation="necessity"）
pof(dat$fY, dat$fA, relation='necessity')  # 条件A是否为Y的必要条件
pof(dat$fY, dat$fB, relation='necessity')
pof(dat$fY, dat$fC, relation='necessity')
# 方法B：superSubset() 一次性检验多个条件及其组合的必要性
necessity_result <- superSubset(dat, outcome='fY',
                                conditions=c('fA','fB','fC'), relation='necessity')
print(necessity_result)

# >>> 步骤3：构建真值表（Truth Table）<<<
tt <- truthTable(dat, outcome='fY',
                conditions=c('fA','fB','fC'),
                freq.cut=1, consistency.cut=0.8, sort.by='cons')
print(tt)

# >>> 步骤4：布尔最小化 - 解路径 <<<
# 保守解（Conservative Solution）
sol_cons <- minimize(tt, include='rest')
print(sol_cons)
# 中间解（Intermediate Solution）- 需指定方向性期望
sol_inter <- minimize(tt, include='rest', dir.exp=c(1,1,1))
print(sol_inter)

# >>> 步骤5：可视化 <<<
# XYplot() 绘制条件组合与结果的 XY 散点图（充分性）
# x 为条件组合表达式（* 表示交集），y 为结果变量
XYplot('fA * fB', 'fY', data=dat)  # 条件A与B的组合对Y的充分性
abline(a=0, b=1, col='red')  # 参考线y=x（点位于对角线上方表示该组合是Y的充分条件）

# ================= 可复现性元数据（sessionInfo 快照）=================
# 记录 R 版本与全部已加载包的版本号。这是防止
# R 包版本漂移导致结论不可复现的最小保障。写入失败必须可见（非 fail-silent）。
.obhrm_si <- try(writeLines(capture.output(sessionInfo()), "sessionInfo.txt"), silent = TRUE)
if (inherits(.obhrm_si, "try-error")) {
  message("警告：sessionInfo.txt 写入失败（工作目录可能只读），复现元数据未落盘")
} else if (exists("OBHRM_SEED")) {
  cat(sprintf("random_seed: %s\n", OBHRM_SEED), file = "sessionInfo.txt", append = TRUE)
}
