# PLS-SEM（偏最小二乘结构方程模型）  （方法编号 10.1）
# @method   PLS-SEM（偏最小二乘结构方程模型）
# @chapter  第10章
# @input    用户提供 CSV 数据文件（G3 门禁）：Rscript 10.1.R 数据.csv
# @use_cond 探索性/预测导向模型、小样本（<200）、非正态数据、含形成型（formative）构念；构念为 composite（复合模型）而非共同因子
# @deps     seminr
# @output   路径系数、outer loading、AVE/CR、HTMT、f²、Q²、Bootstrap 置信区间，输出至控制台 / 工作目录
# @example  使用自身数据时按 @input 提供文件，并在 MODEL CONFIG 中按列名定义构念与路径
# 说明：本脚本配套《R 语言数据分析手册》，代码已检验；运行需本机安装 R 与 seminr。

# G4 环境门禁：缺失包则提示安装（不代装）
ensure_pkg <- function(p) {
  if (!requireNamespace(p, quietly = TRUE)) {
    stop(paste0('G4: 未安装 R 包 ', p, '，请先运行 install.packages(\'', p, '\')'))
  }
  library(p, character.only = TRUE)
}
ensure_pkg("seminr")

# [G3] 用户提供数据：Rscript <this>.R 数据.csv
args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 1) {
  cat("G3 门禁：请提供数据文件，例如 Rscript 10.1.R mydata.csv\n")
  cat("数据要求：宽格式 CSV；每列一个测量题项，首行为变量名；构念由列名前缀分组（见 MODEL CONFIG）。\n")
  # 用 sys.nframe() 区分「顶层脚本」与「被 source() 调入」两种情形：
  #   Rscript 运行 → nframe()==0，保持 cat()+quit(status=1) 的原行为（干净输出 + 明确退出码）；
  #   被 source() 时 → nframe()>0，改用 stop()，避免连带终止调用方的整个 R 会话。
  if (sys.nframe() == 0L) {
    quit(status = 1)
  }
  stop("G3 门禁：未提供数据文件（请用 Rscript 运行，或显式传入数据文件路径）", call. = FALSE)
}
dat <- read.csv(args[1], fileEncoding = "UTF-8", stringsAsFactors = FALSE)

# ============================================================
# MODEL CONFIG —— 按你的数据列名修改构念与路径定义
#   测量模型：composite(构念名, multi_items(前缀, 题项范围))
#   结构模型：relationships(paths(from = ..., to = ...))
#   示例：VIS(vis1-3) -> IMAG(imag1-4) -> LOY(loy1-3)，且 VIS 直接 -> LOY
# ============================================================
measurements <- constructs(
  composite("VIS",  multi_items("vis",  1:3)),
  composite("IMAG", multi_items("imag", 1:4)),
  composite("LOY",  multi_items("loy",  1:3))
)
structure <- relationships(
  paths(from = "VIS",  to = "IMAG"),
  paths(from = c("VIS", "IMAG"), to = "LOY")
)

# ============================================================
# PLS-SEM 估计（seminr，默认 path weighting 内权重）
# ============================================================
seminr_model <- estimate_pls(
  data             = dat,
  measurement_model = measurements,
  structural_model  = structure
)

cat("===== PLS-SEM 估计结果（seminr）=====\n")
print(summary(seminr_model))

# Bootstrap：路径系数显著性（默认 1000 次）
boot <- bootstrap_model(seminr_model, nboot = 1000)
cat("\n===== Bootstrap 路径系数（95% CI）=====\n")
print(summary(boot))

# 测量模型质量：Outer Loadings（取自模型对象；AVE/CR/alpha 见上方 summary 的 Reliability 块）
cat("\n===== 测量模型指标 =====\n")
cat("Outer loadings:\n")
print(round(seminr_model$outer_loadings, 3))
cat("（AVE / CR / Cronbach's alpha 见上方 summary 的 Reliability 块；AVE≥0.5、CR/alpha≥0.7 达标）\n")

# 区别效度：HTMT（按指标相关手动计算；< 0.85 达标，与同方法族 2.1 判据一致）
cat("\n===== HTMT（区别效度，< 0.85 达标）=====\n")
mm <- seminr_model$mmMatrix
cnames <- unique(mm[, "construct"])
blocks <- lapply(cnames, function(cn) mm[mm[, "construct"] == cn, "measurement"])
names(blocks) <- cnames
X <- seminr_model$data
htmt_pair <- function(a, b) {
  ca <- as.matrix(X[, blocks[[a]], drop = FALSE])
  cb <- as.matrix(X[, blocks[[b]], drop = FALSE])
  inter  <- mean(abs(cor(ca, cb)))
  intra_a <- abs(cor(ca)); diag(intra_a) <- NA
  intra_b <- abs(cor(cb)); diag(intra_b) <- NA
  inter / sqrt(mean(intra_a, na.rm = TRUE) * mean(intra_b, na.rm = TRUE))
}
ht <- matrix(NA, length(cnames), length(cnames))
for (i in seq_along(cnames)) for (j in seq_along(cnames)) {
  if (i != j) ht[i, j] <- htmt_pair(cnames[i], cnames[j])
}
dimnames(ht) <- list(cnames, cnames)
print(round(ht, 3))

# 预测相关：Q²（PLS predict；> 0 表示有预测力）
cat("\n===== Q²（预测相关性，> 0 表示有预测力）=====\n")
pp <- predict_pls(seminr_model)
q2 <- tryCatch({
  if (!is.null(pp$q2)) pp$q2
  else if (!is.null(pp$model$q2)) pp$model$q2
  else stop("extract")
}, error = function(e) NULL)
if (!is.null(q2)) print(round(q2, 3)) else print(summary(pp))

# 效应量 f²（对结构模型每条路径：fSquared(model, iv, dv)）
cat("\n===== f²（效应量：>=0.02/0.15/0.35 为小/中/大）=====\n")
sm <- seminr_model$smMatrix
for (k in seq_len(nrow(sm))) {
  iv <- sm[k, "source"]; dv <- sm[k, "target"]
  cat(" ", iv, "->", dv, ":\n")
  print(round(fSquared(seminr_model, iv = iv, dv = dv), 3))
}

cat("\n[完成] PLS-SEM 分析结束。\n")
