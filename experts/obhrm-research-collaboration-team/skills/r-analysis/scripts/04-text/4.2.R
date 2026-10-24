# 文本预处理与语料库构建  （方法编号 4.2）
# @method   文本预处理与语料库构建
# @chapter  第4章
# @input    用户提供 CSV 数据文件（G3 门禁）：Rscript 4.2.R 数据.csv [变量列...]
# @use_cond 每行 CSV 作为一篇文档（字符字段按空白拼接成文本）；中文文本需额外分词（jiebaR）。
#           注意：jiebaR 已从 CRAN 归档，需按 @deps_note 的方式安装。
# @deps     jiebaR, quanteda
# @deps_note jiebaR 已从 CRAN 归档（当前 CRAN 索引中不存在），install.packages('jiebaR') 会失败；请改用 remotes::install_version('jiebaR', version = '0.11.1') 从 CRAN Archive 安装。quanteda 仍在 CRAN，可正常安装。
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
ensure_pkg("jiebaR", "jiebaR 已从 CRAN 归档，install.packages 会失败；请用 remotes::install_version('jiebaR', version = '0.11.1') 从 CRAN Archive 安装。")
ensure_pkg("quanteda")

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
# ---- 将 texts 替换为文本字符向量 ----
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('quanteda')
# G4 不代装：jiebaR 已归档，请在 R 控制台执行 remotes::install_version('jiebaR', version = '0.11.1')
library(quanteda)
library(jiebaR)

# >>> 创建语料库 <<<
# 文档向量 texts：每行 CSV 作为一篇文档，字符型字段按空白拼接。
# 若已在上一步准备好 texts（例如：texts <- readLines('corpus.txt', encoding='UTF-8')），
# 则直接沿用；否则由 G3 读入的 dat 现场构造（每行 CSV 作为一篇文档）。
if (!exists('texts')) {
  texts <- apply(dat, 1, function(r) paste(r[!is.na(r)], collapse=' '))
}
corpus_text <- corpus(texts)
summary(corpus_text)

# >>> 英文文本清洗与分词 <<<
tokens_en <- tokens(corpus_text, remove_punct=TRUE, remove_numbers=TRUE)
tokens_en <- tokens_tolower(tokens_en)
tokens_en <- tokens_select(tokens_en, pattern=stopwords('en'), selection='remove')

# >>> 中文文本分词（jiebaR）<<<
cutter <- worker()
texts_cn <- sapply(texts, function(x) paste(cutter <= x, collapse=' '))
corpus_cn <- corpus(texts_cn)
tokens_cn <- tokens(corpus_cn, remove_punct=TRUE)
cn_stopwords <- c('的','了','在','是','我','有','和','就','不','人','都','一','一个','上','也','很','到','说','要','去','你','会','着','没有','看','好','自己','这')
tokens_cn <- tokens_select(tokens_cn, pattern=cn_stopwords, selection='remove')

# >>> 创建文档-词矩阵（DFM）<<<
dfm_en <- dfm(tokens_en)
dfm_cn <- dfm(tokens_cn)
topfeatures(dfm_en, 20)  # 前20高频词

# >>> 词汇多样性 TTR <<<
ttr <- ntype(corpus_text) / ntoken(corpus_text)
print(ttr)

# >>> DFM修剪 <<<
dfm_trimmed <- dfm_trim(dfm_en, min_termfreq=5, max_docfreq=0.9, docfreq_type='prop')
print(dfm_trimmed)

# ================= 可复现性元数据（sessionInfo 快照）=================
# 记录 R 版本与全部已加载包的版本号。这是防止
# R 包版本漂移导致结论不可复现的最小保障。写入失败必须可见（非 fail-silent）。
.obhrm_si <- try(writeLines(capture.output(sessionInfo()), "sessionInfo.txt"), silent = TRUE)
if (inherits(.obhrm_si, "try-error")) {
  message("警告：sessionInfo.txt 写入失败（工作目录可能只读），复现元数据未落盘")
} else if (exists("OBHRM_SEED")) {
  cat(sprintf("random_seed: %s\n", OBHRM_SEED), file = "sessionInfo.txt", append = TRUE)
}
