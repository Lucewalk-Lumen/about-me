# 多层回归分析（层次回归）  （方法编号 6.11）
# @method   多层回归分析（层次回归）
# @chapter  第6章
# @input    用户提供 CSV 数据文件（G3 门禁）：Rscript 6.11.R 数据.csv [变量列...]
# @use_cond 因变量连续；样本量足够；各步骤模型需嵌套可比。
# @deps     base R
# @output   分析结果输出至控制台 / 工作目录
# @example  使用自身数据时按 @input 提供文件
# 说明：本脚本由《R语言数据分析手册-已检验.md》提取，代码已检验；运行需本机安装 R。


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
# 多层回归分析（层次回归） — R基础stats包
# ============================================================
# 逐步加入变量组来检验增量解释力
# 通过Delta R-squared判断新变量是否显著增加解释力
# ============================================================

# ---- 将 dat 替换为数据框名，y/x1-x6 替换为变量名 ----

# 步骤1：逐层加入变量
step1 <- lm(y ~ x1 + x2, data=dat)                        # 第一层：控制变量
step2 <- lm(y ~ x1 + x2 + x3 + x4, data=dat)              # 第二层：主效应
step3 <- lm(y ~ x1 + x2 + x3 + x4 + x5*x6, data=dat)      # 第三层：交互效应

# 步骤2：比较各层模型
anova(step1, step2)  # 检验step2是否显著优于step1
anova(step2, step3)  # 检验step3是否显著优于step2

# 步骤3：查看增量R方
summary(step1)$r.squared  # 第1层R方
summary(step2)$r.squared  # 第2层R方
summary(step3)$r.squared  # 第3层R方
# Delta R^2 = R^2(step2) - R^2(step1)

# ================= 可复现性元数据（sessionInfo 快照）=================
# 记录 R 版本与全部已加载包的版本号。这是防止
# R 包版本漂移导致结论不可复现的最小保障。写入失败必须可见（非 fail-silent）。
.obhrm_si <- try(writeLines(capture.output(sessionInfo()), "sessionInfo.txt"), silent = TRUE)
if (inherits(.obhrm_si, "try-error")) {
  message("警告：sessionInfo.txt 写入失败（工作目录可能只读），复现元数据未落盘")
} else if (exists("OBHRM_SEED")) {
  cat(sprintf("random_seed: %s\n", OBHRM_SEED), file = "sessionInfo.txt", append = TRUE)
}
