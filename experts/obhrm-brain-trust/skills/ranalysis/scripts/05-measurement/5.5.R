# 二阶验证性因素分析  （方法编号 5.5）
# @method   二阶验证性因素分析
# @chapter  第5章
# @input    用户提供 CSV 数据文件（G3 门禁）：Rscript 5.5.R 数据.csv [变量列...]
# @use_cond 至少有4个一阶因子；一阶CFA拟合良好。
# @deps     lavaan
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
ensure_pkg("lavaan")

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
# 二阶验证性因素分析 — lavaan包
# ============================================================
# 一阶因子之上还存在一个更高阶的因子
# 例如："工作满意度"下有"薪酬满意度""晋升满意度"等一阶因子
#
# 模型结构示意：
#   高阶因子g
#   ├── f1 (一阶因子1) ← y1, y2, y3 (题目)
#   ├── f2 (一阶因子2) ← y4, y5, y6
#   └── f3 (一阶因子3) ← y7, y8, y9
# ============================================================

# ---- 安装并加载包 ----
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('lavaan')

# ---- 将 y1-y12 替换为你的量表题目变量名 ----
# ---- 将 f1-f5 替换为你的因子名 ----

# 步骤1：指定二阶CFA模型
secondorder_model <- '
  # 一阶因子（测量模型）
  f1 =~ y1 + y2 + y3        # 因子f1由y1,y2,y3测量
  f2 =~ y4 + y5 + y6        # 因子f2由y4,y5,y6测量
  f3 =~ y7 + y8 + y9        # 因子f3由y7,y8,y9测量
  f4 =~ y10 + y11 + y12     # 因子f4由y10,y11,y12测量

  # 二阶因子（结构模型）
  g =~ f1 + f2 + f3 + f4    # 高阶因子g由f1-f4测量
'

# 步骤2：拟合模型
fit_second <- cfa(secondorder_model, data=dat)
summary(fit_second, fit.measures=TRUE, standardized=TRUE)
# 拟合指标：CFI/TLI>0.90, RMSEA<0.08, SRMR<0.08

# 步骤3：与一阶CFA比较（卡方差异检验）
# oneorder_model <- 'f1 =~ y1+y2+y3; f2 =~ y4+y5+y6; ...'
# fit_one <- cfa(oneorder_model, data=dat)
# anova(fit_one, fit_second)  # p<0.05说明二阶模型更优

# ================= 可复现性元数据（sessionInfo 快照）=================
# 记录 R 版本与全部已加载包的版本号。这是防止
# R 包版本漂移导致结论不可复现的最小保障。写入失败必须可见（非 fail-silent）。
.obhrm_si <- try(writeLines(capture.output(sessionInfo()), "sessionInfo.txt"), silent = TRUE)
if (inherits(.obhrm_si, "try-error")) {
  message("警告：sessionInfo.txt 写入失败（工作目录可能只读），复现元数据未落盘")
} else if (exists("OBHRM_SEED")) {
  cat(sprintf("random_seed: %s\n", OBHRM_SEED), file = "sessionInfo.txt", append = TRUE)
}
