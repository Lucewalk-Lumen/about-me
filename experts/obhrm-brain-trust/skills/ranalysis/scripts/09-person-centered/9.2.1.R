# 基础LCA（类别识别）  （方法编号 9.2.1）
# @method   基础LCA（类别识别）
# @chapter  第9章
# @input    用户提供 CSV 数据文件（G3 门禁）：Rscript 9.2.1.R 数据.csv [变量列...]
# @use_cond 分类指标变量（二分或有序）；每类至少 10-20 个样本。
# @deps     poLCA
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
ensure_pkg("poLCA")

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
# 基础LCA：基于分类变量识别质性不同的亚组
# ============================================================
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('poLCA')

# ---- 将 dat 替换为数据框名，i1-i4 替换为分类变量名 ----
# 步骤1：指定LCA模型公式
lca_formula <- cbind(i1, i2, i3, i4) ~ 1

# 步骤2：拟合不同类别数，比较BIC（选最小BIC）
for (k in 2:5) {
  set.seed(123)
  lca_model <- poLCA(lca_formula, data=dat,
                     nclass=k, maxiter=1000, nrep=10)
  cat(sprintf('Classes=%d, BIC=%.1f\n', k, lca_model$bic))
}

# 步骤3：拟合最优模型
set.seed(123)
lca_final <- poLCA(lca_formula, data=dat, nclass=3, nrep=10)
lca_classes <- lca_final$predclass  # 每个样本的类别编号
table(lca_classes)                    # 各类别样本量
# 各类别在各题目上的条件概率 -> 描述类别特征

# ================= 可复现性元数据（sessionInfo 快照）=================
# 记录 R 版本与全部已加载包的版本号。这是防止
# R 包版本漂移导致结论不可复现的最小保障。写入失败必须可见（非 fail-silent）。
.obhrm_si <- try(writeLines(capture.output(sessionInfo()), "sessionInfo.txt"), silent = TRUE)
if (inherits(.obhrm_si, "try-error")) {
  message("警告：sessionInfo.txt 写入失败（工作目录可能只读），复现元数据未落盘")
} else if (exists("OBHRM_SEED")) {
  cat(sprintf("random_seed: %s\n", OBHRM_SEED), file = "sessionInfo.txt", append = TRUE)
}
