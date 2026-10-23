# 样本量预估（横向研究）  （方法编号 3.2）
# @method   样本量预估（横向研究）
# @chapter  第3章
# @input    用户提供 CSV 数据文件（G3 门禁）：Rscript 3.2.R 数据.csv [变量列...]
# @use_cond 在数据收集前使用；需预先估计效应量（小0.2/中0.5/大0.8，或参考类似研究的效应量）。
# @deps     pwr, pwrss, semPower
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
ensure_pkg("pwr")
ensure_pkg("pwrss")
ensure_pkg("semPower")

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
# ---- 根据你的研究设计选择对应的函数，替换参数值 ----
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('pwr')
library(pwr)

# >>> 基础方法：pwr包 <<<
# T检验（两组均值比较）：d=0.5(中等效应)，效力0.80
pwr.t.test(d=0.5, sig.level=0.05, power=0.80, type='two.sample')
# d: Cohen's d效应量(0.2小/0.5中/0.8大)，sig.level: 显著性水平，power: 统计效力

# 单因素ANOVA（3组比较）：f=0.25(中等效应)
pwr.anova.test(k=3, f=0.25, sig.level=0.05, power=0.80)
# k: 组数，f: Cohen's f效应量(0.1小/0.25中/0.4大)

# 多元回归（2个预测变量）：f2=0.15(中等效应)
pwr.f2.test(u=2, f2=0.15, sig.level=0.05, power=0.80)
# u: 分子自由度(预测变量数)，f2: Cohen's f2(0.02小/0.15中/0.35大)

# 相关分析：r=0.3(中等效应)
pwr.r.test(r=0.3, sig.level=0.05, power=0.80)

# >>> 扩展方法：pwrss包（中介效应等）<<<
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('pwrss')
library(pwrss)
# 中介效应样本量（间接效应a*b的效力检验）
pwrss.z.mediation(a=0.3, b=0.3, cp=0.1,
                  alpha=0.05, power=0.80)
# a: X->M路径系数，b: M->Y路径系数，cp: 直接效应c'

# 逻辑回归样本量
pwrss.z.logreg(p1=.3, p0=.5, alpha=0.05, power=0.80)
# p1: X=1时的P(Y=1)，p0: X=0时的P(Y=1)

# >>> SEM的效力分析：semPower包 <<<
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('semPower')
library(semPower)
# 先验效力分析（已知效应量和效力，求样本量）
sp <- semPower.aPriori(effect=.10, effect.measure='RMSEA',
                        alpha=.05, power=.80, df=20)
# effect=.10: RMSEA=0.10，effect.measure指定效应量类型
# df: 模型自由度
summary(sp)
plot(sp)  # 可视化效力曲线

# ================= 可复现性元数据（sessionInfo 快照）=================
# 记录 R 版本与全部已加载包的版本号。这是防止
# R 包版本漂移导致结论不可复现的最小保障。写入失败必须可见（非 fail-silent）。
.obhrm_si <- try(writeLines(capture.output(sessionInfo()), "sessionInfo.txt"), silent = TRUE)
if (inherits(.obhrm_si, "try-error")) {
  message("警告：sessionInfo.txt 写入失败（工作目录可能只读），复现元数据未落盘")
} else if (exists("OBHRM_SEED")) {
  cat(sprintf("random_seed: %s\n", OBHRM_SEED), file = "sessionInfo.txt", append = TRUE)
}
