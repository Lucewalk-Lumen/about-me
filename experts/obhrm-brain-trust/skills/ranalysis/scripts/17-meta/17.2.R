# SEM元分析（MASEM：两阶段结构方程建模）  （方法编号 17.2）
# @method   SEM元分析（MASEM：两阶段结构方程建模）
# @chapter  第17章
# @input    用户提供 CSV 数据文件（G3 门禁）：Rscript 17.2.R 数据.csv [变量列...]
# @use_cond 需收集多项研究的相关矩阵或协方差矩阵；至少5项研究；每项研究需报告完整的变量间相关系数或协方差。
# @deps     metaSEM
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
ensure_pkg("metaSEM")

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
# ---- 将 dat 替换为包含各研究相关矩阵的列表 ----
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('metaSEM')

# >>> 数据准备 <<<
# MASEM需要每项研究的相关矩阵（或协方差矩阵）和样本量
# 数据格式：list of matrices + n vector
# 示例数据：Digman97（metaSEM自带，大五人格相关矩阵）
# ---- 如用自己的数据，将 Digman97 替换为你的数据对象 ----
data(Digman97)
head(Digman97$data)  # 查看各研究的相关矩阵
head(Digman97$n)     # 查看各研究的样本量

# >>> 第一阶段：合成相关矩阵 <<<
# 固定效应模型（FEM）- 假设所有研究共享同一相关矩阵
fixed1 <- tssem1(Cov=Digman97$data, n=Digman97$n, method='FEM')
summary(fixed1)
# 查看合并后的相关矩阵
coef(fixed1)  # 合并后的相关系数矩阵

# 随机效应模型（REM）- 允许各研究相关矩阵有变异
random1 <- tssem1(Cov=Digman97$data, n=Digman97$n, method='REM')
summary(random1)
# 检查异质性：Tau2显著表示各研究间有显著变异

# >>> 第二阶段：在合并矩阵上拟合SEM <<<
# 定义SEM模型（使用lavaan语法）
# ---- 将模型定义替换为你的理论模型 ----
model <- '
  # 测量模型：两个高阶因子
  Alpha =~ A + C + ES      # Alpha因子（宜人性、尽责性、情绪稳定性）
  Beta  =~ E + I            # Beta因子（外向性、开放性）
  # 结构模型
  Alpha ~~ Beta            # 两个因子相关
'
# 将lavaan语法转换为RAM格式
RAM1 <- lavaan2RAM(model, obs.variables=c('A','C','ES','E','I'))

# 在第一阶段结果上拟合SEM（第二阶段）
fixed2 <- tssem2(fixed1, RAM=RAM1, intervals='LB',
                 model.name='TSSEM2 Fixed')
summary(fixed2)
# 输出：路径系数（因子载荷和因子间相关）及其置信区间

# 随机效应模型的第二阶段
random2 <- tssem2(random1, RAM=RAM1, intervals='LB',
                  model.name='TSSEM2 Random')
summary(random2)

# >>> 模型比较 <<<
# 比较固定效应和随机效应模型的拟合
# 固定效应：假设所有研究效应同质
# 随机效应：允许研究间变异
# 若随机效应模型的Tau2显著，应使用随机效应结果

# >>> 一阶段法（OSMASEM）<<<
# OSMASEM将两个阶段合并，同时估计合并矩阵和SEM参数
# 优势：可加入研究水平的调节变量
# ---- 将 Nohe15 替换为你的数据，moderator 替换为调节变量名 ----
# data(Nohe15)
# osm <- osmasem(model=model, data=dat,
#                moderator=moderator)  # 研究特征作为调节变量
# summary(osm)

# ================= 可复现性元数据（sessionInfo 快照）=================
# 记录 R 版本与全部已加载包的版本号。这是防止
# R 包版本漂移导致结论不可复现的最小保障。写入失败必须可见（非 fail-silent）。
.obhrm_si <- try(writeLines(capture.output(sessionInfo()), "sessionInfo.txt"), silent = TRUE)
if (inherits(.obhrm_si, "try-error")) {
  message("警告：sessionInfo.txt 写入失败（工作目录可能只读），复现元数据未落盘")
} else if (exists("OBHRM_SEED")) {
  cat(sprintf("random_seed: %s\n", OBHRM_SEED), file = "sessionInfo.txt", append = TRUE)
}
