# 主客体互依模型（APIM）  （方法编号 14.1）
# @method   APIM（Actor-Partner Interdependence Model，主客体互依模型）
# @chapter  第14章
# @input    用户提供 LONG 格式 CSV（G3 门禁）：Rscript 14.1.R 数据.csv [sem]
# @use_cond 成对/对偶数据（情侣、师徒、上下级、队友等），研究"自身行为→自身结果"(actor) 与"伴侣行为→自身结果"(partner) 的双向效应；控制对子内非独立性
# @deps     lme4（必需）；lavaan（可选，SEM 版 APIM，传第二参数 sem 启用）
# @output   actor/partner 效应、可区分性检验（LR 检验）、随机效应（对子内相关），输出至控制台
# @example  使用自身数据时按 @input 提供文件，并在 MODEL CONFIG 中确认列名
# 说明：本脚本配套《R 语言数据分析手册》（APIM 章），代码已检验；运行需本机安装 R 与 lme4。

# G4 环境门禁：缺失包则提示安装（不代装）
ensure_pkg <- function(p) {
  if (!requireNamespace(p, quietly = TRUE)) {
    stop(paste0('G4: 未安装 R 包 ', p, '，请先运行 install.packages(\'', p, '\')'))
  }
  library(p, character.only = TRUE)
}
ensure_pkg("lme4")

# [G3] 用户提供数据：Rscript <this>.R 数据.csv [sem]
args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 1) {
  cat("G3 门禁：请提供 LONG 格式数据文件，例如 Rscript 14.1.R mydata.csv\n")
  cat("数据要求（长格式，每行一个人）：\n")
  cat("  dyad   : 对子标识（家庭/情侣/师徒/上下级编号）\n")
  cat("  member : 成员标识（可区分对子用，如 A/B 或 F/M；不可区分对子可省略或填 same）\n")
  cat("  X      : 自变量（该成员自身在焦点变量上的得分）\n")
  cat("  Xp     : 伴侣在该自变量上的得分（partner 的 X）\n")
  cat("  Y      : 因变量（该成员的结果变量）\n")
  cat("第二参数可选 'sem' 启用 lavaan SEM 版 APIM（需安装 lavaan，且数据为宽格式）。\n")
  # 用 sys.nframe() 区分「顶层脚本」与「被 source() 调入」两种情形：
  #   Rscript 运行 → nframe()==0，保持 cat()+quit(status=1) 的原行为（干净输出 + 明确退出码）；
  #   被 source() 时 → nframe()>0，改用 stop()，避免连带终止调用方的整个 R 会话。
  if (sys.nframe() == 0L) {
    quit(status = 1)
  }
  stop("G3 门禁：未提供数据文件（请用 Rscript 运行，或显式传入数据文件路径）", call. = FALSE)
}
dat <- read.csv(args[1], fileEncoding = "UTF-8", stringsAsFactors = FALSE)
use_sem <- length(args) >= 2 && tolower(args[2]) == "sem"

# 检查必需列
req <- c("dyad", "X", "Xp", "Y")
miss <- setdiff(req, names(dat))
if (length(miss) > 0) stop(paste0("G3: 数据缺少必需列：", paste(miss, collapse = ", ")))

# 可区分性：若存在 member 列且取值多于一种，则视为可区分对子
distinguishable <- "member" %in% names(dat) && length(unique(dat$member)) > 1

cat("===== APIM 估计（lme4 MLM 路径）=====\n")
cat("对子数：", length(unique(dat$dyad)), "；个体数：", nrow(dat), "\n")
cat("可区分对子：", distinguishable, "\n")

# 基础 MLM-APIM（控制对子随机截距）
model_base <- lmer(Y ~ X + Xp + (1 | dyad), data = dat, REML = FALSE)
cat("\n--- 总体 actor/partner 效应（控制对子随机截距）---\n")
print(summary(model_base)$coefficients)

# 可区分性检验：加入 member 与 X/Xp 的交互，LR 检验
if (distinguishable) {
  dat$member <- factor(dat$member)
  model_full <- lmer(Y ~ X * member + Xp * member + (1 | dyad), data = dat, REML = FALSE)
  lr  <- as.numeric(2 * (logLik(model_full) - logLik(model_base)))
  df_diff <- attr(logLik(model_full), "df") - attr(logLik(model_base), "df")
  p_val <- pchisq(lr, df_diff, lower.tail = FALSE)
  cat("\n--- 可区分性检验（LR 检验：全模型 vs 基础模型）---\n")
  cat("LR =", round(lr, 3), "，df =", df_diff, "，p =", round(p_val, 4), "\n")
  cat("p < .05 → 对子可区分（需分角色解释效应）；否则可合并为不可区分模型。\n")
  cat("\n--- 分角色 actor/partner 效应（全模型）---\n")
  print(summary(model_full)$coefficients)
  fit <- model_full
} else {
  fit <- model_base
}

cat("\n--- 随机效应（对子内相关 / 组内相依）---\n")
print(VarCorr(fit))

# 可选：lavaan SEM 版 APIM（需宽格式四列 X_A/X_B/Y_A/Y_B）
if (use_sem) {
  cat("\n===== APIM 估计（lavaan SEM 路径）=====\n")
  ensure_pkg("lavaan")
  wide_cols <- c("X_A", "X_B", "Y_A", "Y_B")
  if (all(wide_cols %in% names(dat))) {
    model_lav <- "
      Y_A ~ a * X_A + p * X_B
      Y_B ~ a * X_B + p * X_A
      X_A ~~ X_B
      Y_A ~~ Y_B"
    fit_lav <- sem(model_lav, data = dat)
    print(summary(fit_lav, fit.measures = TRUE, standardized = TRUE))
  } else {
    cat("SEM 版需宽格式数据（每对子一行：X_A/X_B/Y_A/Y_B）。\n")
    cat("请转换为宽格式后重跑并传 'sem' 参数。\n")
  }
}

cat("\n[完成] APIM 分析结束。\n")
