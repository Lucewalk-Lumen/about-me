# 本地大语言模型分析（Ollama）  （方法编号 19.1）
# @method   本地大语言模型分析（Ollama）
# @chapter  第19章
# @input    用户提供 CSV 数据文件（G3 门禁）：Rscript 19.1.R 数据.csv [文本列名] [--online]
# @use_cond 默认离线安全（不加 --online）：脚本加载期不发起任何网络请求。联网用法：Rscript 19.1.R 数据.csv 文本列名 --online（触发方法3 真实分析）。启用联网前需安装并启动 Ollama 应用、下载模型；本地硬件需足够（建议8GB+内存）。方法1/2/4 为手册原文示例，置于 if (FALSE) 中默认不执行。
# @deps     httr, jsonlite
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
ensure_pkg("httr")
ensure_pkg("jsonlite")

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
# 本地大语言模型分析 — httr + Ollama
# ============================================================
# 通过Ollama在本地运行大语言模型（如Llama3.2）
# 优势：数据不离开本地、免费、可定制
#
# 前置安装：
#   1. 安装Ollama：https://ollama.com/download
#   2. 在终端下载模型：ollama pull llama3.2
#   3. 启动Ollama服务：ollama serve（默认端口11434）
#
# 功能模块：
#   方法1：文本生成（单次问答）    —— 联网示例
#   方法2：对话模式（多轮对话）    —— 联网示例
#   方法3：批量文本分析（批量情感分析）—— 真实实现（文本取自用户数据列；联网须加 --online）
#   方法4：嵌入向量生成（文本向量化）—— 联网示例
#
# 【注意】联网与离线约定：
#   默认（不加 --online）**不发起任何网络请求**，可安全在无 Ollama 的离线机器上加载/运行，
#   不会因缺少本地服务而报错中断。方法3 的联网分析由命令行开关 --online 显式触发
#   （Rscript 19.1.R 数据.csv 文本列名 --online）；方法1/2/4 为手册原文示例，仍包在
#   `if (FALSE) { ... }` 内，须把其中的 `FALSE` 改为 `TRUE` 才会执行。
# ============================================================

# ---- 安装并加载包（仅需运行一次） ----
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('httr')
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('jsonlite')

# ============================================================
# 配置连接
# ============================================================
# Ollama默认运行在本地11434端口
ollama_url <- 'http://localhost:11434'

# ---- 将 llama3.2 替换为已下载的模型名 ----
# ---- 将 prompt_text 替换为你的提示文本 ----

# ============================================================
# 方法1：文本生成（单次问答）  —— 联网示例（默认不执行）
# ============================================================
# POST /api/generate：向模型发送提示，获取生成结果
# stream=FALSE：等待完整响应（非流式）
if (FALSE) {
  prompt_text <- '请总结以下文本的主要观点：...'
  response <- POST(
    paste0(ollama_url, '/api/generate'),      # API端点
    body=toJSON(list(
      model='llama3.2',        # 指定模型名
      prompt=prompt_text,     # 提示文本
      stream=FALSE),           # 非流式输出
      auto_unbox=TRUE),
    content_type_json())
  result <- fromJSON(content(response, 'text'))  # 解析JSON响应
  cat(result$response)  # 输出模型生成的文本
}

# ============================================================
# 方法2：对话模式（多轮对话）  —— 联网示例（默认不执行）
# ============================================================
# POST /api/chat：支持system/user/assistant多角色对话
# system角色：设定模型行为（如"你是文本分析助手"）
# user角色：用户输入
if (FALSE) {
  chat_response <- POST(
    paste0(ollama_url, '/api/chat'),
    body=toJSON(list(
      model='llama3.2',
      messages=list(
        list(role='system',   content='你是文本分析助手'),   # 系统设定
        list(role='user',     content='请对以下文本进行情感分析：...')  # 用户输入
      ),
      stream=FALSE),
      auto_unbox=TRUE),
    content_type_json())
  chat_result <- fromJSON(content(chat_response, 'text'))
  cat(chat_result$message$content)  # 输出模型回复
}

# ============================================================
# 方法3：批量文本分析  —— 真实实现（显式开关；联网须加 --online）
# ============================================================
# 对多段文本逐一调用模型进行分析。
# 文本列取自用户数据（G3）：args[2] 指定列则用该列，否则取首列。
texts <- if (length(args) >= 2) as.character(dat[[args[2]]]) else as.character(dat[[1]])

# 显式开关：仅当传入第 3 个参数 --online 时才联网；否则保持离线安全（给出 G5 提示，不发请求）。
online <- length(args) >= 3 && args[3] == "--online"
if (online) {
  results <- lapply(texts, function(txt) {
    resp <- POST(paste0(ollama_url, '/api/generate'),
      body=toJSON(list(
        model='llama3.2',
        prompt=paste('分析以下文本的情感(积极/消极/中性):', txt),
        stream=FALSE),
        auto_unbox=TRUE),
      content_type_json())
    fromJSON(content(resp, 'text'))$response  # 提取模型回复
  })
  analysis_df <- data.frame(text=texts, analysis=unlist(results))  # 真实分析结果（文本→情感）
  print(analysis_df)  # 输出每段文本的分析结果
} else {
  cat("G5 提示：本方法需连接本机 Ollama 服务。\n")
  cat("  启用方式：Rscript 19.1.R <数据.csv> <文本列名> --online\n")
  cat("  未启用时脚本保持离线安全，不发起任何网络请求。\n")
  cat(sprintf("  已就绪的待分析文本数：%d 列：%s\n", length(texts), args[2]))
}

# ============================================================
# 方法4：嵌入向量生成（文本向量化）  —— 联网示例（默认不执行）
# ============================================================
# POST /api/embeddings：将文本转为高维数值向量
# 用途：文本相似度计算、聚类、分类的特征输入
if (FALSE) {
  embed_response <- POST(
    paste0(ollama_url, '/api/embeddings'),
    body=toJSON(list(
      model='llama3.2',
      prompt='需要生成嵌入向量的文本'),
      auto_unbox=TRUE),
    content_type_json())
  embedding <- fromJSON(content(embed_response, 'text'))$embedding
  # embedding是一个高维数值向量（如4096维）
  # 可用于：cosine相似度、K-means聚类、分类模型输入
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
