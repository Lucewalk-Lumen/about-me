# 增长混合模型（GMM，识别不同增长轨迹组）  （方法编号 9.3.7）
# @method   增长混合模型（GMM，识别不同增长轨迹组）
# @chapter  第9章
# @input    用户提供 CSV 数据文件（G3 门禁）：Rscript 9.3.7.R 数据.csv [变量列...]
# @use_cond 至少 3 个时间点的纵向数据；样本量较大（>300，因需估计多个组的增长参数）；建议先做单组 LGA 确认整体增长形态。
# @deps     lcmm, mclust
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
ensure_pkg("lcmm")
ensure_pkg("mclust")
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
# 方法1：lcmm 包的 hlme()（潜类别线性混合模型，最常用）
# 注意：hlme 需长格式数据，每行一个观测，含三列：
#   id（个体标识）、time（时间点 0/1/2...）、y（响应变量）
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('lcmm')
# 单组潜增长模型（基线，先确认整体增长形态）
m1 <- hlme(y ~ time, subject='id', data=dat)
# 2类增长混合模型（用单组结果作初始值 B，避免 ng>1 时无法收敛）
m2 <- hlme(y ~ time, subject='id', data=dat,
           mixture=~time, ng=2, B=m1)  # 2类模型
summary(m1); summary(m2)  # 比较 BIC 判断类别数（BIC 越小越好）
# 提取各样本的轨迹组归属
m2$pprob$class

# 方法2：mclust 包（基于宽格式数据的轨迹聚类）
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('mclust')
wide <- dat[, c('y1','y2','y3')]  # 宽格式：每行一个体，列为时间点
mc <- Mclust(wide, G=1:4)  # 自动选择最优类别数（BIC）
summary(mc)  # 各类别的轨迹均值和比例
plot(mc, what='classification')  # 轨迹分组图

# ================= 可复现性元数据（sessionInfo 快照）=================
# 记录 R 版本与全部已加载包的版本号。这是防止
# R 包版本漂移导致结论不可复现的最小保障。写入失败必须可见（非 fail-silent）。
.obhrm_si <- try(writeLines(capture.output(sessionInfo()), "sessionInfo.txt"), silent = TRUE)
if (inherits(.obhrm_si, "try-error")) {
  message("警告：sessionInfo.txt 写入失败（工作目录可能只读），复现元数据未落盘")
} else if (exists("OBHRM_SEED")) {
  cat(sprintf("random_seed: %s\n", OBHRM_SEED), file = "sessionInfo.txt", append = TRUE)
}
