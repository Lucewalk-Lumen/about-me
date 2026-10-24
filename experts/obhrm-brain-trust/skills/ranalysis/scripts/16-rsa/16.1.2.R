# 响应面分析的调节效应  （方法编号 16.1.2）
# @method   响应面分析的调节效应
# @chapter  第16章
# @input    用户提供 CSV 数据文件（G3 门禁）：Rscript 16.1.2.R 数据.csv [变量列...]
# @use_cond  已完成基础响应面分析；需具备 RSA 与 dplyr 包；用于检验响应面关系的调节效应，x、y 须已中心化，调节变量与因变量的变量名须替换为实际列名。
# @deps     RSA, dplyr
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
ensure_pkg("RSA")
ensure_pkg("dplyr")

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
# ---- 将 z 替换为因变量，x/y 替换为两个预测变量，w 替换为调节变量，dat 替换为数据框名 ----
# 调节RSA：检验响应面形状是否随调节变量W变化
# 方法：将W与多项式各项交互，构建含调节项的多项式回归
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('RSA')
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('dplyr')

# >>> 步骤1：中心化所有变量 <<<
dat$x_c <- scale(dat$x, scale=FALSE)
dat$y_c <- scale(dat$y, scale=FALSE)
dat$w_c <- scale(dat$w, scale=FALSE)

# >>> 步骤2：构建多项式项 <<<
dat$x_sq <- dat$x_c^2
dat$y_sq <- dat$y_c^2
dat$xy <- dat$x_c * dat$y_c

# >>> 步骤3：构建调节交互项（W与多项式各项交互）<<<
dat$xw  <- dat$x_c * dat$w_c
dat$yw  <- dat$y_c * dat$w_c
dat$xw_sq <- dat$x_sq * dat$w_c
dat$xyw   <- dat$xy * dat$w_c
dat$yw_sq <- dat$y_sq * dat$w_c

# >>> 步骤4：拟合含调节的多项式回归 <<<
# 基础模型（无调节）
model_base <- lm(z ~ x_c + y_c + x_sq + xy + y_sq,
                 data=dat)
# 全调节模型（所有多项式项与W交互）
model_mod <- lm(z ~ x_c + y_c + x_sq + xy + y_sq +
                  w_c + xw + yw + xw_sq + xyw + yw_sq,
                data=dat)
summary(model_mod)

# >>> 步骤5：模型比较（Delta R-squared检验）<<<
anova(model_base, model_mod)
# p<0.05表示调节效应显著，响应面形状随W变化

# >>> 步骤6：不同W水平下的响应面参数 <<<
# 在W=+1SD和W=-1SD水平下分别计算RSA参数
sd_w <- sd(dat$w, na.rm=TRUE)
for (w_val in c(-sd_w, 0, sd_w)) {
  # 将W固定在特定水平，计算对应的响应面参数
  b1 <- coef(model_mod)['x_c'] + coef(model_mod)['xw'] * w_val
  b2 <- coef(model_mod)['y_c'] + coef(model_mod)['yw'] * w_val
  b3 <- coef(model_mod)['x_sq'] + coef(model_mod)['xw_sq'] * w_val
  b4 <- coef(model_mod)['xy'] + coef(model_mod)['xyw'] * w_val
  b5 <- coef(model_mod)['y_sq'] + coef(model_mod)['yw_sq'] * w_val
  # 响应面参数
  a1 <- b1 + b2           # 一致线斜率
  a2 <- b3 + b4 + b5      # 一致线曲率
  a3 <- b1 - b2           # 不一致线斜率
  a4 <- b3 - b4 + b5      # 不一致线曲率
  cat(sprintf('W=%.2f: a1=%.3f, a2=%.3f, a3=%.3f, a4=%.3f
',
              w_val, a1, a2, a3, a4))
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
