# 查询R包的下载量  （方法编号 1.3.5）
# @method   查询R包的下载量
# @chapter  第1章
# @input    用户提供 CSV 数据文件（G3 门禁）：Rscript 1.3.5.R 数据.csv [变量列...]
# @use_cond  本机已安装 R 且具备 cranlogs 包；用于查询 CRAN 包的下载量统计，需联网访问 CRAN 镜像；按 G3 门控需提供宽格式 CSV 数据文件。
# @deps     cranlogs
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
ensure_pkg("cranlogs")

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
# 查询R包下载量 — cranlogs 包
# ============================================================
# 用于查看CRAN上R包的下载量，评估包的流行度和维护活跃度
# 在选择工具包时，下载量可作为参考指标之一
# ============================================================

# ---- 安装并加载包（仅需运行一次） ----
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('cranlogs')

# ---- 将 lme4 替换为你要查询的包名 ----

# ============================================================
# 步骤1：查看热门包排行榜
# ============================================================
# 查看过去1个月下载量前100的R包
# when='last-month'：时间范围可选'last-day'/'last-week'/'last-month'
# count=100：返回前100个包
cran_top_downloads(when='last-month', count=100)

# ============================================================
# 步骤2：查看指定包的每日下载量
# ============================================================
# 查看lme4包过去1个月每天的下载量
# 返回数据框：date列和count列
cran_downloads(packages='lme4', when='last-month')

# ============================================================
# 步骤3：计算指定包的总下载量
# ============================================================
# sum()对count列求和，得到该时间段的总下载量
sum(cran_downloads(packages='lme4', when='last-month')$count)

# ============================================================
# 步骤4：可视化下载趋势（可选）
# ============================================================
dl_data <- cran_downloads(packages='lme4', when='last-month')
plot(dl_data$date, dl_data$count, type='l',  # type='l'画线图
     xlab='Date', ylab='Downloads',           # 坐标轴标签
     main='lme4 package downloads (last month)')

# ================= 可复现性元数据（sessionInfo 快照）=================
# 记录 R 版本与全部已加载包的版本号。这是防止
# R 包版本漂移导致结论不可复现的最小保障。写入失败必须可见（非 fail-silent）。
.obhrm_si <- try(writeLines(capture.output(sessionInfo()), "sessionInfo.txt"), silent = TRUE)
if (inherits(.obhrm_si, "try-error")) {
  message("警告：sessionInfo.txt 写入失败（工作目录可能只读），复现元数据未落盘")
} else if (exists("OBHRM_SEED")) {
  cat(sprintf("random_seed: %s\n", OBHRM_SEED), file = "sessionInfo.txt", append = TRUE)
}
