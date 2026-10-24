# R的升级  （方法编号 1.2.2）
# @method   R的升级
# @chapter  第1章
# @input    用户提供 CSV 数据文件（G3 门禁）：Rscript 1.2.2.R 数据.csv [变量列...]
# @use_cond
# @deps     installr
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
ensure_pkg("installr")

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
# ---- 无需修改变量，直接运行 ----
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('installr')
library(installr)                     # 加载installr包
updateR()                             # 启动升级向导，按提示操作即可

# >>> 手动迁移已安装包 <<<
oldpackages <- installed.packages()[,1]              # 保存升级前的包列表
save(oldpackages, file='installedPackages.Rdata')    # 保存到文件
# --- 升级R后执行以下代码 ---
load('installedPackages.Rdata')                      # 加载旧包列表
newpackages <- installed.packages()[,1]              # 获取升级后的包列表
for (i in setdiff(oldpackages, newpackages)) {       # 找出缺失的包
  # G4 不代装：脚本不自动安装依赖，只逐条提示（避免静默改动用户环境）
  message("G4 提示：升级后缺失的包 ", i, "；如需安装请在控制台执行 install.packages('", i, "')")
}
# ================= 可复现性元数据（sessionInfo 快照）=================
# 记录 R 版本与全部已加载包的版本号。这是防止
# R 包版本漂移导致结论不可复现的最小保障。写入失败必须可见（非 fail-silent）。
.obhrm_si <- try(writeLines(capture.output(sessionInfo()), "sessionInfo.txt"), silent = TRUE)
if (inherits(.obhrm_si, "try-error")) {
  message("警告：sessionInfo.txt 写入失败（工作目录可能只读），复现元数据未落盘")
} else if (exists("OBHRM_SEED")) {
  cat(sprintf("random_seed: %s\n", OBHRM_SEED), file = "sessionInfo.txt", append = TRUE)
}
