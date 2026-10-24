# 探索性因素分析（EFA）  （方法编号 5.2）
# @method   探索性因素分析（EFA）
# @chapter  第5章
# @input    用户提供 CSV 数据文件（G3 门禁）：Rscript 5.2.R 数据.csv [变量列...]
# @use_cond 样本量>题目数的5倍；KMO>0.6；Bartlett检验p<0.05。
# @deps     psych
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
ensure_pkg("psych")

# ---- 如用自己的数据，将 dat[,1:5] 替换为你的变量列范围 ----
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('psych')
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

# 步骤1：KMO检验和Bartlett球形检验
KMO(dat[,1:5])                    # KMO>0.6表示适合做因素分析
cortest.bartlett(dat[,1:5])       # p<0.05表示变量间有共同因素

# 步骤2：确定因子数量（平行分析）
fa.parallel(dat[,1:5], fa='fa', n.iter=100)

# 步骤3：因子提取与旋转
efa <- fa(dat[,1:5], nfactors=2, rotate='varimax')
print(efa, sort=TRUE)
# 因子载荷：>0.7优秀，>0.5良好，>0.4可接受

# 步骤4：碎石图（可视化因子特征值，辅助确定因子数）
scree(dat[,1:5])

# ================= 可复现性元数据（sessionInfo 快照）=================
# 记录 R 版本与全部已加载包的版本号。这是防止
# R 包版本漂移导致结论不可复现的最小保障。写入失败必须可见（非 fail-silent）。
.obhrm_si <- try(writeLines(capture.output(sessionInfo()), "sessionInfo.txt"), silent = TRUE)
if (inherits(.obhrm_si, "try-error")) {
  message("警告：sessionInfo.txt 写入失败（工作目录可能只读），复现元数据未落盘")
} else if (exists("OBHRM_SEED")) {
  cat(sprintf("random_seed: %s\n", OBHRM_SEED), file = "sessionInfo.txt", append = TRUE)
}
