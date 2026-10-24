# 重复测量方差分析  （方法编号 6.9）
# @method   重复测量方差分析
# @chapter  第6章
# @input    用户提供 CSV 数据文件（G3 门禁）：Rscript 6.9.R 数据.csv [变量列...]
# @use_cond 同一组被试在多个时间点（或条件下）重复测量；因变量连续；各时间点差值满足球形假设（Mauchly 检验）
# @deps     ez
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
ensure_pkg("ez")

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
# 重复测量方差分析 — ez包
# ============================================================
# 同一被试在多个时间点/条件下重复测量
# 常见场景：前测-后测-追踪、不同实验条件下的反应
#
# 数据格式要求：长格式（long format）
#   每行=一个观测值，被试ID可重复出现
#   示例：
#   subj_id  time   score
#   001      t1     5.2
#   001      t2     6.8
#   002      t1     4.1
#   002      t2     5.5
# ============================================================

# ---- 安装并加载包（仅需运行一次） ----
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('ez')

# ---- 将 dat_long 替换为你的长格式数据框名 ----
# ---- 将 score 替换为因变量名 ----
# ---- 将 subj_id 替换为被试ID变量名 ----
# ---- 将 time 替换为重复测量变量名（时间点或条件） ----

# ============================================================
# 步骤1：确保变量类型正确
# ============================================================
# subj_id和time必须是因子型(factor)，否则ezANOVA会报错
dat_long$subj_id <- as.factor(dat_long$subj_id)
dat_long$time    <- as.factor(dat_long$time)

# ============================================================
# 步骤2：运行重复测量方差分析
# ============================================================
# dv=score：因变量
# wid=subj_id：被试标识变量
# within=time：组内因素（重复测量变量）
# 若有组间因素可加between=group参数
result <- ezANOVA(data=dat,
                  dv=score,          # 因变量
                  wid=subj_id,        # 被试ID
                  within=time)        # 组内因素（重复测量）

# ============================================================
# 步骤3：查看结果
# ============================================================
print(result)
# 输出包含：
#   1. Mauchly球形检验：p>0.05满足球形假设，p<0.05违背
#   2. Greenhouse-Geisser校正：违背球形假设时自动报告校正后的p值
#   3. 方差分析表：SS、df、MS、F、p、偏eta方
# 解读：p<0.05表示不同时间点的得分有显著差异

# ============================================================
# 步骤4：事后两两比较（可选）
# ============================================================
# 用pairwise.t.test进行各时间点之间的两两比较
pairwise.t.test(dat_long$score, dat_long$time,
                paired=TRUE,           # 配对比较
                p.adjust.method='bonferroni')  # Bonferroni校正

# ============================================================
# 步骤5：混合设计（组间+组内）
# ============================================================
# 若有组间因素（如实验组/对照组），可同时分析交互效应
# result_mixed <- ezANOVA(data=dat,
#     dv=score, wid=subj_id, within=time, between=group)
# group为分组变量名（组间因素）

# ================= 可复现性元数据（sessionInfo 快照）=================
# 记录 R 版本与全部已加载包的版本号。这是防止
# R 包版本漂移导致结论不可复现的最小保障。写入失败必须可见（非 fail-silent）。
.obhrm_si <- try(writeLines(capture.output(sessionInfo()), "sessionInfo.txt"), silent = TRUE)
if (inherits(.obhrm_si, "try-error")) {
  message("警告：sessionInfo.txt 写入失败（工作目录可能只读），复现元数据未落盘")
} else if (exists("OBHRM_SEED")) {
  cat(sprintf("random_seed: %s\n", OBHRM_SEED), file = "sessionInfo.txt", append = TRUE)
}
