# 逻辑回归  （方法编号 6.12）
# @method   逻辑回归
# @chapter  第6章
# @input    用户提供 CSV 数据文件（G3 门禁）：Rscript 6.12.R 数据.csv [变量列...]
# @use_cond 因变量为二分变量（0/1）；自变量连续或分类；样本量至少为预测变量数的 10 倍。
# @deps     MASS, pscl
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
ensure_pkg("MASS")
ensure_pkg("pscl")

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
# 逻辑回归 — stats包 + pscl + MASS
# ============================================================
# 因变量为二分类（0/1）时使用二元逻辑回归
# 因变量为有序多分类（如：低/中/高）时使用有序逻辑回归
#
# 模型结构示意：
#   logit(P(Y=1)) = b0 + b1*x1 + b2*x2 + b3*x3
#   P(Y=1) = exp(b0+b1*x1+...) / (1 + exp(b0+b1*x1+...))
# ============================================================

# ---- 将 dat 替换为你的数据框名 ----
# ---- 将 binary_outcome 替换为二分类因变量名（0/1） ----
# ---- 将 x1, x2, x3 替换为自变量名 ----
# ---- 将 ordered_outcome 替换为有序分类因变量名 ----

# ============================================================
# 步骤1：二元逻辑回归
# ============================================================
# glm() 广义线性模型
# family=binomial(link='logit')：指定逻辑回归（logit链接函数）
logit_model <- glm(binary_outcome ~ x1 + x2 + x3,
                   data=dat,
                   family=binomial(link='logit'))
summary(logit_model)
# 输出解读：
#   Estimate列：回归系数（logit尺度，不直观）
#   z value和Pr(>|z|)：z检验值和p值，p<0.05表示该变量显著

# ============================================================
# 步骤2：计算优势比（OR）及置信区间
# ============================================================
# exp(coef()) 将系数转为优势比(Odds Ratio)
# OR>1 -> 自变量增加1单位时，因变量=1的概率增加
# OR<1 -> 自变量增加1单位时，因变量=1的概率降低
# OR=1 -> 无影响
exp(coef(logit_model))

# 95%置信区间：若区间包含1则不显著
exp(confint(logit_model))

# ============================================================
# 步骤3：预测概率
# ============================================================
# type='response'：输出0~1之间的预测概率值
pred_prob <- predict(logit_model, type='response')
# 可设置阈值：pred_class <- ifelse(pred_prob > 0.5, 1, 0)

# ============================================================
# 步骤4：模型拟合优度（伪R方）
# ============================================================
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('pscl')
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('MASS')
pR2(logit_model)  # McFadden/McKelvey/Cox-Snell等伪R方指标
# McFadden R方：0.2-0.4为良好拟合，>0.4为优秀

# ============================================================
# 步骤5：有序逻辑回归（因变量为有序分类）
# ============================================================
# 当因变量为有序多分类（如1=低,2=中,3=高）时使用polr()
# parallel lines assumption：各自变量的效应在所有切点处相同
ologit <- polr(ordered_outcome ~ x1 + x2,
               data=dat,
               Hess=TRUE)  # Hess=TRUE：计算Hessian矩阵用于标准误
summary(ologit)
# 检查比例优势假设：可用brant包的brant_test()

# ================= 可复现性元数据（sessionInfo 快照）=================
# 记录 R 版本与全部已加载包的版本号。这是防止
# R 包版本漂移导致结论不可复现的最小保障。写入失败必须可见（非 fail-silent）。
.obhrm_si <- try(writeLines(capture.output(sessionInfo()), "sessionInfo.txt"), silent = TRUE)
if (inherits(.obhrm_si, "try-error")) {
  message("警告：sessionInfo.txt 写入失败（工作目录可能只读），复现元数据未落盘")
} else if (exists("OBHRM_SEED")) {
  cat(sprintf("random_seed: %s\n", OBHRM_SEED), file = "sessionInfo.txt", append = TRUE)
}
