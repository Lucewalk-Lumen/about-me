# 扎根理论分析（RQDA）  （方法编号 4.1）
# @method   扎根理论分析（RQDA）
# @chapter  第4章
# @input    用户提供 CSV 数据文件（G3 门禁）：Rscript 4.1.R 数据.csv [变量列...]
# @use_cond 质性文本数据（访谈记录、田野笔记、文档等）；文本格式为TXT/RTF/PDF；研究者需具备扎根理论方法论基础。
#           注意：RQDA 已从 CRAN 归档，需按 @deps_note 的方式安装。
# @deps     RQDA
# @deps_note RQDA 已从 CRAN 归档（当前 CRAN 索引中不存在），install.packages('RQDA') 会失败；请改用 remotes::install_version('RQDA', version = '0.3-1') 从 CRAN Archive 安装。
# @output   分析结果输出至控制台 / 工作目录
# @example  使用自身数据时按 @input 提供文件
# 说明：本脚本配套《R 语言数据分析手册》，代码已检验；运行需本机安装 R。

# G4 环境门禁：缺失包则提示安装（不代装）
ensure_pkg <- function(p, hint = "") {
  if (!requireNamespace(p, quietly=TRUE)) {
    stop(paste0('G4: 未安装 R 包 ', p,
                if (nzchar(hint)) paste0('。', hint)
                else paste0('，请先运行 install.packages(\'', p, '\')')))
  }
  library(p, character.only=TRUE)
}
ensure_pkg("RQDA", "RQDA 已从 CRAN 归档，install.packages 会失败；请用 remotes::install_version('RQDA', version = '0.3-1') 从 CRAN Archive 安装。")

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
# ---- 将 interview1.txt 等替换为你的文本文件路径 ----
# G4 不代装：RQDA 已归档，请在 R 控制台执行 remotes::install_version('RQDA', version = '0.3-1')
library(RQDA)

# >>> 启动RQDA图形界面 <<<
RQDA()  # 启动GTK+图形界面
# 在GUI中：File -> New Project -> 创建.rqda文件

# >>> 命令行操作（项目打开后执行）<<<
# filepaths <- c('interview1.txt', 'interview2.txt')
# for (f in filepaths) { addFile(f, encoding='UTF-8') }

# >>> 开放式编码（Open Coding）<<<
# GUI中：选中文本 -> 右键 -> Mark -> 输入编码名称
# 命令行自动编码：codingBySearch('keyword', fid=1, coding='code_name')

# >>> 查看编码频率 <<<
# getCodingTable()  # 所有编码记录表
# summaryCode()      # 各编码频次

# >>> 主轴编码（Axial Coding）<<<
# CodeCategories('parent', 'child1', 'child2')
# retrieval('code_name')  # 检索编码下的文本片段

# >>> 选择性编码（Selective Coding）<<<
# codingMatrix()  # 编码共现矩阵

# >>> 编码可靠性 <<<
# exports_of_coding('coder1.csv')
# Cohen kappa > 0.70 表示编码者间一致性可接受

# ================= 可复现性元数据（sessionInfo 快照）=================
# 记录 R 版本与全部已加载包的版本号。这是防止
# R 包版本漂移导致结论不可复现的最小保障。写入失败必须可见（非 fail-silent）。
.obhrm_si <- try(writeLines(capture.output(sessionInfo()), "sessionInfo.txt"), silent = TRUE)
if (inherits(.obhrm_si, "try-error")) {
  message("警告：sessionInfo.txt 写入失败（工作目录可能只读），复现元数据未落盘")
} else if (exists("OBHRM_SEED")) {
  cat(sprintf("random_seed: %s\n", OBHRM_SEED), file = "sessionInfo.txt", append = TRUE)
}
