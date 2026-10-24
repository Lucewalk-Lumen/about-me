# 一阶验证性因素分析（CFA）  （方法编号 5.4）
# @method   一阶验证性因素分析（CFA）
# @chapter  第5章
# @input    用户提供 CSV 数据文件（G3 门禁）：Rscript 5.4.R 数据.csv [变量列...]
# @use_cond 样本量>200；每个因子至少3个题目；数据近似正态分布。
# @deps     lavaan, semPlot, semTools
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
ensure_pkg("semPlot")
ensure_pkg("semTools")

# ============================================================
# 一阶验证性因素分析（CFA） — lavaan + semPlot + semTools
# ============================================================
# CFA根据理论预设的因子结构进行检验
#
# CFA分析流程：
#   1. 指定模型 -> 2. 拟合模型 -> 3. 评估拟合指标
#   -> 4. 模型比较（模型1/2/3递进） -> 5. 信度效度 -> 6. 路径图
# ============================================================

# ---- 安装并加载包（仅需运行一次） ----
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('lavaan')
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('semPlot')
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('semTools')
library(lavaan)               # 加载lavaan
library(semPlot)              # 加载semPlot
library(semTools)              # 加载semTools

# ---- 将 y1-y6 替换为你的量表题目变量名 ----
# ---- 将 f1/f2 替换为你的因子名 ----

# ============================================================
# 步骤1：准备数据
# ============================================================
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
# 模型语法里的 y1..y6 是题目列的占位名。若你的列名不是 y1..y6，
# 请用 [变量列...] 只选中 6 个题目列，脚本按位置把它们对应为 y1..y6。
if (!identical(names(dat)[seq_len(6)], paste0('y', 1:6))) {
  if (ncol(dat) < 6) {
    stop('G3 门禁：CFA 需要 6 个题目列（y1..y6），当前仅 ', ncol(dat), ' 列。', call. = FALSE)
  }
  names(dat)[seq_len(6)] <- paste0('y', 1:6)
  cat('提示：已将前 6 列按位置重命名为 y1..y6，以匹配模型语法。\n')
}

# ============================================================
# 步骤2：模型1 — 单因子模型（所有题目载荷到一个因子）
# ============================================================
model1 <- '
  f1 =~ y1 + y2 + y3 + y4 + y5 + y6
'
fit1 <- cfa(model1, data=dat)
summary(fit1, fit.measures=TRUE)

# ============================================================
# 步骤3：模型2 — 两因子模型（理论驱动的因子结构）
# ============================================================
model2 <- '
  f1 =~ y1 + y2 + y3    # 因子f1由y1,y2,y3测量
  f2 =~ y4 + y5 + y6    # 因子f2由y4,y5,y6测量
'
fit2 <- cfa(model2, data=dat)
summary(fit2, fit.measures=TRUE, standardized=TRUE)

# ============================================================
# 步骤4：模型3 — 三因子模型（更细分的因子结构）
# ============================================================
model3 <- '
  f1 =~ y1 + y2
  f2 =~ y3 + y4
  f3 =~ y5 + y6
'
fit3 <- cfa(model3, data=dat)
summary(fit3, fit.measures=TRUE)

# ============================================================
# 步骤5：模型比较（卡方差异检验）
# ============================================================
# 嵌套模型比较：模型1(最简单) vs 模型2 vs 模型3(最复杂)
anova(fit1, fit2)  # 模型1 vs 模型2: p<0.05说明模型2更优
anova(fit2, fit3)  # 模型2 vs 模型3: p>0.05则模型2足够简洁

# 也可以比较AIC/BIC（越小越好）
print(fitMeasures(fit1, c('aic', 'bic')))
print(fitMeasures(fit2, c('aic', 'bic')))
print(fitMeasures(fit3, c('aic', 'bic')))

# 拟合指标参考标准：
#   CFI/TLI > 0.90（>0.95良好）
#   RMSEA < 0.08（<0.05良好）
#   SRMR < 0.08

# ============================================================
# 步骤6：信度与效度检验
# ============================================================
# 选定最优模型后（通常是模型2）
compRelSEM(fit2)   # 组合信度 omega（原 reliability() 已弃用，CR>0.7 信度良好）
AVE(fit2)          # 平均方差抽取量（AVE>0.5 收敛效度可接受）

# ============================================================
# 步骤7：路径图可视化
# ============================================================
semPaths(fit2, whatLabels='std', layout='tree',
         edge.label.cex=0.8, sizeMan=8, sizeLat=6)

# ================= 可复现性元数据（sessionInfo 快照）=================
# 记录 R 版本与全部已加载包的版本号。这是防止
# R 包版本漂移导致结论不可复现的最小保障。写入失败必须可见（非 fail-silent）。
.obhrm_si <- try(writeLines(capture.output(sessionInfo()), "sessionInfo.txt"), silent = TRUE)
if (inherits(.obhrm_si, "try-error")) {
  message("警告：sessionInfo.txt 写入失败（工作目录可能只读），复现元数据未落盘")
} else if (exists("OBHRM_SEED")) {
  cat(sprintf("random_seed: %s\n", OBHRM_SEED), file = "sessionInfo.txt", append = TRUE)
}
