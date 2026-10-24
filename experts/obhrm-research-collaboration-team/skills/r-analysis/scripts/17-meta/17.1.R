# 元分析  （方法编号 17.1）
# @method   元分析
# @chapter  第17章
# @input    用户提供 CSV 数据文件（G3 门禁）：Rscript 17.1.R 数据.csv [变量列...]
# @use_cond 至少2个独立研究的效应量数据；效应量可转换为共同指标（SMD/OR/RD等）。
# @deps     metafor
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
ensure_pkg("metafor")

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
# 元分析 — metafor包
# ============================================================
# 定量综合多个独立研究的结果
# 固定效应：所有研究共享同一真实效应
# 随机效应：允许效应在研究间变化（更常用）
# ============================================================

# ---- 安装并加载包 ----
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('metafor')
library(metafor)              # 加载metafor

# ---- 将 mean_treatment/sd_treatment 等替换为变量名 ----

# 步骤1：计算效应量（标准化均数差SMD）
dat <- escalc(measure='SMD',                # 效应量类型
                 m1i=mean_treatment, m2i=mean_control,  # 组1/组2均值
                 sd1i=sd_treatment, sd2i=sd_control,    # 组1/组2标准差
                 n1i=n_treatment, n2i=n_control,         # 组1/组2样本量
                 data=dat)

# 步骤2：拟合随机效应模型
re_model <- rma(yi, vi, data=dat, method='REML')
summary(re_model)  # 输出合并效应量、置信区间、I2（异质性）

# 步骤3：森林图
forest(re_model)  # 各研究效应量和合并效应的可视化

# 步骤4：漏斗图+ Egger检验（发表偏倚检验）
funnel(re_model)                    # 漏斗图（应对称）
regtest(re_model, model='lm')       # Egger检验 p>0.05无发表偏倚

# ================= 可复现性元数据（sessionInfo 快照）=================
# 记录 R 版本与全部已加载包的版本号。这是防止
# R 包版本漂移导致结论不可复现的最小保障。写入失败必须可见（非 fail-silent）。
.obhrm_si <- try(writeLines(capture.output(sessionInfo()), "sessionInfo.txt"), silent = TRUE)
if (inherits(.obhrm_si, "try-error")) {
  message("警告：sessionInfo.txt 写入失败（工作目录可能只读），复现元数据未落盘")
} else if (exists("OBHRM_SEED")) {
  cat(sprintf("random_seed: %s\n", OBHRM_SEED), file = "sessionInfo.txt", append = TRUE)
}
