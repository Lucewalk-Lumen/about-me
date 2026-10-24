# 测量不变性（跨组与纵向 Measurement Invariance）  （方法编号 5.7）
# @method   测量不变性（跨组与纵向 Measurement Invariance）
# @chapter  第5章
# @input    用户提供 CSV 数据文件（G3 门禁）：Rscript 5.7.R 数据.csv [变量列...]
# @use_cond 样本量>200且各组样本量接近；每组至少100；已通过单组CFA确认因子结构拟合良好；分组变量为分类变量（如性别、国别）。
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
# ---- 将 y1-y6 替换为你的量表题目变量名，f1/f2 替换为因子名，group 替换为分组变量 ----
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('lavaan')
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('semTools')
library(lavaan)
library(semTools)

# >>> 方法1：手动逐步检验（推荐，控制更精细）<<<
cfa_model <- '
  f1 =~ y1 + y2 + y3
  f2 =~ y4 + y5 + y6
'
# 第1步：配置不变性（Configural）——各组因子结构相同，无等值约束
fit_config <- cfa(cfa_model, data=dat, group='group')
summary(fit_config, fit.measures=TRUE)

# 第2步：弱不变性/载荷不变性（Metric）——因子载荷跨组等值
fit_metric <- cfa(cfa_model, data=dat, group='group',
                  group.equal='loadings')
lavTestLRT(fit_config, fit_metric)  # 似然比检验

# 第3步：强不变性/截距不变性（Scalar）——截距跨组等值
fit_scalar <- cfa(cfa_model, data=dat, group='group',
                  group.equal=c('loadings','intercepts'))
lavTestLRT(fit_metric, fit_scalar)

# 第4步：严格不变性（Strict）——残差方差跨组等值
fit_strict <- cfa(cfa_model, data=dat, group='group',
                  group.equal=c('loadings','intercepts','residuals'))
lavTestLRT(fit_scalar, fit_strict)

# >>> 方法2：semTools 的 measEq.syntax（semTools 已弃用旧函数 measurementInvariance）<<<
# 生成各步等值约束的模型语法，再逐个用 cfa() 拟合
# meq <- measEq.syntax(configural.model=cfa_model, data=dat, group='group')
# 返回 meq$model.configural / meq$model.metric / meq$model.scalar 等语法
# 例如：fit_metric <- cfa(meq$model.metric, data=dat, group='group')
# 实际使用建议直接采用上方"方法1手动逐步检验"，控制更精细

# >>> 拟合指标差异判断标准（Chen, 2007）<<<
# 提取各步拟合指标进行比较
fits <- rbind(
  config = inspect(fit_config, 'fit.measures')[c('cfi','rmsea','srmr')],
  metric = inspect(fit_metric, 'fit.measures')[c('cfi','rmsea','srmr')],
  scalar = inspect(fit_scalar, 'fit.measures')[c('cfi','rmsea','srmr')],
  strict = inspect(fit_strict, 'fit.measures')[c('cfi','rmsea','srmr')]
)
print(fits)
# ΔCFI <= 0.01, ΔRMSEA <= 0.015, ΔSRMR <= 0.03 表示等值约束可接受

# >>> 纵向测量不变性（跨时间，OBHRM纵向研究前置检验）<<<
# 数据为宽格式：每个时间点一套题目（如 y1_t1, y2_t1, y1_t2, y2_t2）
# 核心思想：同一量表在两个时间点的载荷和截距应等值（用相同标签约束）
long_inv_model <- '
  # 时间点1的因子（载荷用 l1/l2/l3 标签）
  f_t1 =~ l1*y1_t1 + l2*y2_t1 + l3*y3_t1
  # 时间点2的因子（载荷约束与时间点1相等，实现载荷不变性）
  f_t2 =~ l1*y1_t2 + l2*y2_t2 + l3*y3_t2
  # 截距约束相等（强不变性）
  y1_t1 ~ i1*1
  y1_t2 ~ i1*1
  y2_t1 ~ i2*1
  y2_t2 ~ i2*1
  y3_t1 ~ i3*1
  y3_t2 ~ i3*1
'
fit_long <- cfa(long_inv_model, data=dat)
summary(fit_long, fit.measures=TRUE)
# 比较"等值约束模型"与"无约束模型"（去掉 l/i 等值标签）的 ΔCFI
# ΔCFI <= 0.01 表示跨时间不变性成立，可安全进行纵向均值/关系比较
# 若不成立，说明量表在追踪期间测量属性发生变化，纵向结论需谨慎

# ================= 可复现性元数据（sessionInfo 快照）=================
# 记录 R 版本与全部已加载包的版本号。这是防止
# R 包版本漂移导致结论不可复现的最小保障。写入失败必须可见（非 fail-silent）。
.obhrm_si <- try(writeLines(capture.output(sessionInfo()), "sessionInfo.txt"), silent = TRUE)
if (inherits(.obhrm_si, "try-error")) {
  message("警告：sessionInfo.txt 写入失败（工作目录可能只读），复现元数据未落盘")
} else if (exists("OBHRM_SEED")) {
  cat(sprintf("random_seed: %s\n", OBHRM_SEED), file = "sessionInfo.txt", append = TRUE)
}
