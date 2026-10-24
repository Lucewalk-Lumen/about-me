# 中英文界面切换  （方法编号 1.2.1）
# @method   中英文界面切换
# @chapter  第1章
# @input    用户提供 CSV 数据文件（G3 门禁）：Rscript 1.2.1.R 数据.csv [变量列...]
# @use_cond  本机已安装 R；用于切换 R 界面语言显示（改 LANGUAGE 环境变量），不影响统计流程；按 G3 门控需提供宽格式 CSV 数据文件。
# @deps     base R
# @output   分析结果输出至控制台 / 工作目录
# @example  使用自身数据时按 @input 提供文件
# 说明：本脚本由《R语言数据分析手册-已检验.md》提取，代码已检验；运行需本机安装 R。


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
# >>> 方法1：临时切换（仅当前R会话有效）<<<
.lang_bak <- Sys.getenv("LANGUAGE", unset = "")   # 先记住原值，避免污染调用方环境
Sys.setenv(LANGUAGE='en')  # 切换为英文
Sys.setenv(LANGUAGE='zh')  # 切换回中文
if (nzchar(.lang_bak)) Sys.setenv(LANGUAGE = .lang_bak) else Sys.unsetenv("LANGUAGE")
rm(.lang_bak)                                          # 复原原值（全局状态不残留）

# >>> 方法2：永久切换（修改配置文件）<<<
# 找到R安装目录下的 etc/Rprofile.site 文件
# 在文件末尾添加以下代码（保存后重启R即可生效）：
# Sys.setenv(LANGUAGE='en')  # 设置为英文

# >>> 方法3：快捷方式参数 <<<
# 右击R图标 > 属性 > 在【目标】栏末尾添加空格和 lang=en
# 如：C:/Program Files/R/<本机 R 版本目录>/bin/Rgui.exe lang=en
#     （版本目录形如 R-4.3.0，请按本机实际安装的版本替换，不要照抄示例版本号）

# ================= 可复现性元数据（sessionInfo 快照）=================
# 记录 R 版本与全部已加载包的版本号。这是防止
# R 包版本漂移导致结论不可复现的最小保障。写入失败必须可见（非 fail-silent）。
.obhrm_si <- try(writeLines(capture.output(sessionInfo()), "sessionInfo.txt"), silent = TRUE)
if (inherits(.obhrm_si, "try-error")) {
  message("警告：sessionInfo.txt 写入失败（工作目录可能只读），复现元数据未落盘")
} else if (exists("OBHRM_SEED")) {
  cat(sprintf("random_seed: %s\n", OBHRM_SEED), file = "sessionInfo.txt", append = TRUE)
}
