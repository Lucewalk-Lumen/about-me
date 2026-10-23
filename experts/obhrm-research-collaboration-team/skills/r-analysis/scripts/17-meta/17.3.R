# 三层元分析  （方法编号 17.3）
# @method   三层元分析
# @chapter  第17章
# @input    用户提供 CSV 数据文件（G3 门禁）：Rscript 17.3.R 数据.csv [变量列...]
# @use_cond 效应量具有三层嵌套结构（效应量嵌套于研究）；同一研究中有多个效应量；需区分研究内和研究间异质性。
# @deps     metaSEM, metafor
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
ensure_pkg("metaSEM")
ensure_pkg("metafor")

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
# ---- 将 dat 替换为数据框名，y/v/study_id 替换为变量名 ----
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('metafor')
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('metaSEM')
library(metafor)
library(metaSEM)

# >>> 方法1：metafor的rma.mv() <<<
# 三层结构：效应量(y)嵌套于研究(study_id)
# ---- 将 y 替换为效应量列，v 替换为方差列，study_id 替换为研究ID列 ----
# 设置三层结构：Level 1=抽样误差(隐含), Level 2=研究内, Level 3=研究间
model_3level <- rma.mv(y=y, V=v,                  # 效应量和方差
                       random=list(~1 | study_id,  # Level 3: 研究间随机效应
                                  ~1 | effect_id), # Level 2: 研究内随机效应
                       data=dat)
summary(model_3level)
# 输出： Intercept(合并效应量), sigma2.1(研究间方差), sigma2.2(研究内方差)

# 计算各层I2（异质性比例）
W <- diag(1/dat$v)  # 权重矩阵
X <- model.matrix(model_3level)
P <- W - W %*% X %*% solve(t(X) %*% W %*% X) %*% t(X) %*% W
# 总变异
total_var <- sum(model_3level$sigma2)
# I2 Level 2 (研究内)
I2_level2 <- 100 * model_3level$sigma2[2] /
             (model_3level$sigma2[1] + model_3level$sigma2[2] +
              sum(diag(P))/(nrow(dat) - ncol(X)))
# I2 Level 3 (研究间)
I2_level3 <- 100 * model_3level$sigma2[1] /
             (model_3level$sigma2[1] + model_3level$sigma2[2] +
              sum(diag(P))/(nrow(dat) - ncol(X)))
cat(sprintf('I2 Level 2 (within): %.2f%%\n', I2_level2))
cat(sprintf('I2 Level 3 (between): %.2f%%\n', I2_level3))

# 加入调节变量（元回归）
# ---- 将 moderator 替换为你的调节变量名 ----
model_mod <- rma.mv(y=y, V=v, mods=~moderator,
                    random=list(~1 | study_id, ~1 | effect_id),
                    data=dat)
summary(model_mod)  # moderator系数p<0.05表示调节效应显著

# >>> 方法2：metaSEM的meta3L() <<<
# 使用metaSEM内置数据Cooper03（三层结构）
# ---- 如用自己的数据，替换 Cooper03 ----
data(Cooper03)
head(Cooper03)
# 三层元分析：y=效应量, v=方差, cluster=研究聚类
model_meta3L <- meta3L(y=y, v=v, cluster=District, data=dat)
summary(model_meta3L)
# 输出：Intercept(合并效应量), Tau2_2(研究内方差), Tau2_3(研究间方差)
# I2_2: 研究内异质性比例; I2_3: 研究间异质性比例

# 加入协变量
model_meta3L_cov <- meta3L(y=y, v=v, cluster=District,
                           x=scale(Year, scale=FALSE), data=dat)
summary(model_meta3L_cov)
# R2: 协变量解释的各层异质性比例

# >>> 模型比较：两层 vs 三层 <<<
model_2level <- meta(y=y, v=v, data=dat,
                     model.name='2 level', silent=TRUE)
model_3level_m <- meta3L(y=y, v=v, cluster=District, data=dat,
                        model.name='3 level', silent=TRUE)
anova(model_3level_m, model_2level)  # 显著表示三层模型更优

# >>> 森林图 <<<
# forest(model_3level)  # 按研究分层的森林图

# ================= 可复现性元数据（sessionInfo 快照）=================
# 记录 R 版本与全部已加载包的版本号。这是防止
# R 包版本漂移导致结论不可复现的最小保障。写入失败必须可见（非 fail-silent）。
.obhrm_si <- try(writeLines(capture.output(sessionInfo()), "sessionInfo.txt"), silent = TRUE)
if (inherits(.obhrm_si, "try-error")) {
  message("警告：sessionInfo.txt 写入失败（工作目录可能只读），复现元数据未落盘")
} else if (exists("OBHRM_SEED")) {
  cat(sprintf("random_seed: %s\n", OBHRM_SEED), file = "sessionInfo.txt", append = TRUE)
}
