# 文档自动分类  （方法编号 4.5）
# @method   文档自动分类
# @chapter  第4章
# @input    用户提供 CSV 数据文件（G3 门禁）：Rscript 4.5.R 数据.csv [变量列...]
# @use_cond 需要标注好的训练数据（每篇文档有已知类别）；每类至少10-20篇文档；需划分训练集和测试集。
# @deps     glmnet, text2vec
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
ensure_pkg("glmnet")
ensure_pkg("text2vec")

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
# 文档自动分类 — text2vec + glmnet 包
# ============================================================
# 监督学习：用已标注类别的训练文档，训练分类模型，自动预测新文档类别
#
# 完整流程：
#   1. 数据准备：划分训练集(80%)和测试集(20%)
#   2. 文本预处理：小写化 → 分词 → 构建词表
#   3. 特征提取：TF-IDF将文本转为数值向量（文档-词项矩阵DTM）
#   4. 模型训练：LASSO逻辑回归（多分类，自动特征选择）
#   5. 预测评估：混淆矩阵、准确率、精确率/召回率/F1
#   6. 特征解读：提取各类别最重要的词汇特征
#
# 模型结构示意：
#   文本 → [预处理] → [TF-IDF特征] → [LASSO分类器] → 类别标签
#                训练集学习词表和权重    用测试集评估
# ============================================================

# ---- 安装并加载包（仅需运行一次） ----


# G4 不代装：如需安装，请在 R 控制台执行 install.packages('text2vec')
# G4 不代装：如需安装，请在 R 控制台执行 install.packages('glmnet')

# ---- 将 dat 替换为你的数据框名 ----
# ---- 将 text 替换为文本内容列名（字符型向量） ----
# ---- 将 label 替换为类别标签列名（因子型factor） ----

# ============================================================
# 步骤1：划分训练集与测试集（80/20）
# ============================================================
set.seed(123)  # 设定随机种子，确保结果可复现
# 随机抽取80%的样本作为训练集索引
train_idx <- sample(1:nrow(dat), 0.8 * nrow(dat))
data_train <- dat[train_idx, ]   # 训练集：用于学习词表和训练分类器
data_test  <- dat[-train_idx, ]  # 测试集：用于评估分类器性能
# 注意：训练集和测试集必须完全独立，测试集不参与任何训练步骤

# ============================================================
# 步骤2：文本预处理与词表构建
# ============================================================
# itoken() 将文本字符串切分为词元（token）序列
# preprocessor=tolower：将所有文本转为小写（统一大小写）
# tokenizer=word_tokenizer：按空格/标点分词（英文适用）
# 中文需替换为 jiebaR::jieba_tokenizer
it_train <- itoken(data_train$text,        # 输入：训练集文本列
                   preprocessor=tolower,    # 预处理：转小写
                   tokenizer=word_tokenizer,# 分词器：英文按空格分词
                   progressbar=FALSE)       # 不显示进度条

# create_vocabulary() 统计训练集中所有词元的词频和文档频率
vocab <- create_vocabulary(it_train)

# prune_vocabulary() 过滤词表，去除噪声词
# term_count_min=5：词频<5的词被删除（去除低频词/拼写错误）
# doc_proportion_max=0.5：出现在>50%文档中的词被删除（去除通用词）
vocab <- prune_vocabulary(vocab,
                          term_count_min=5,       # 最低词频阈值
                          doc_proportion_max=0.5) # 最高文档比例阈值

# ============================================================
# 步骤3：构建文档-词项矩阵（DTM）并计算TF-IDF
# ============================================================
# vocab_vectorizer() 将词表转为向量化器
# 用于将文本转为数值矩阵（每行=一篇文档，每列=一个词）
vectorizer <- vocab_vectorizer(vocab)

# create_dtm() 生成文档-词项矩阵（稀疏矩阵格式）
# 矩阵元素为词频（TF）：文档中该词出现的次数
dtm_train <- create_dtm(it_train, vectorizer)

# TfIdf$new() 创建TF-IDF转换器
# TF-IDF = 词频(TF) × 逆文档频率(IDF)
# IDF = log(总文档数 / 包含该词的文档数)
# 效果：提高区分性强的词的权重，降低通用词的权重
tfidf <- TfIdf$new()

# fit_transform() 在训练集上拟合TF-IDF权重并转换
dtm_train_tfidf <- fit_transform(dtm_train, tfidf)
# 此时dtm_train_tfidf是一个稀疏矩阵：行=文档，列=词，值=TF-IDF权重

# ============================================================
# 步骤4：测试集特征提取（复用训练集的配置）
# ============================================================
# 重要：测试集必须使用与训练集相同的vectorizer和tfidf权重
# 不能重新拟合，否则会导致信息泄露（data leakage）
it_test <- itoken(data_test$text,           # 输入：测试集文本列
                 preprocessor=tolower,       # 同样的预处理
                 tokenizer=word_tokenizer,    # 同样的分词器
                 progressbar=FALSE)

# 用训练集的vectorizer生成测试集DTM
dtm_test <- create_dtm(it_test, vectorizer)

# 用训练集的tfidf权重转换测试集DTM（transform，不是fit_transform）
dtm_test_tfidf <- transform(dtm_test, tfidf)

# ============================================================
# 步骤5：训练LASSO多分类逻辑回归
# ============================================================
# cv.glmnet() 使用交叉验证选择最优正则化参数lambda
# x=dtm_train_tfidf：特征矩阵（TF-IDF文档-词项矩阵）
# y=data_train$label：类别标签（因子型）
# family='multinomial'：多分类逻辑回归
# alpha=1：LASSO正则化（L1惩罚，使部分词的系数为0，实现特征选择）
# nfolds=5：5折交叉验证
# type.measure='class'：用分类错误率作为选择标准
classifier <- cv.glmnet(x=dtm_train_tfidf,       # 特征矩阵
                         y=data_train$label,      # 类别标签
                         family='multinomial',    # 多分类
                         alpha=1,                 # LASSO（L1正则化）
                         nfolds=5,                # 5折交叉验证
                         type.measure='class')    # 评估指标：分类错误率

# ============================================================
# 步骤6：预测与评估
# ============================================================
# predict() 对测试集进行分类预测
# type='class'：输出类别标签（而非概率）
# s='lambda.min'：使用交叉验证选出的最优lambda（最小错误率）
pred <- predict(classifier, dtm_test_tfidf,      # 测试集特征矩阵
                type='class',                      # 输出类别标签
                s='lambda.min')                    # 使用最优lambda
pred_labels <- as.factor(pred[, 1])              # 转为因子型

# 混淆矩阵：行=预测类别，列=实际类别
# 对角线=正确分类数，非对角线=误分类数
conf_matrix <- table(Predicted=pred_labels,       # 预测标签
                     Actual=data_test$label)      # 实际标签
print(conf_matrix)

# 整体准确率 = 正确预测数 / 总预测数
accuracy <- mean(pred_labels == data_test$label)  # 逐条比较
print(paste('Accuracy:', round(accuracy, 4)))     # 输出4位小数

# ============================================================
# 步骤7：各类别的精确率、召回率、F1分数
# ============================================================
# 精确率(Precision)：预测为该类的样本中实际为该类的比例
# 召回率(Recall)：实际为该类的样本中被正确预测的比例
# F1 = 2*P*R/(P+R)：精确率和召回率的调和平均
for (cls in levels(data_test$label)) {       # 遍历每个类别
  tp <- sum(pred_labels == cls & data_test$label == cls)   # True Positive
  fp <- sum(pred_labels == cls & data_test$label != cls)   # False Positive
  fn <- sum(pred_labels != cls & data_test$label == cls)   # False Negative
  precision <- tp / (tp + fp)  # 精确率 = TP/(TP+FP)
  recall    <- tp / (tp + fn)  # 召回率 = TP/(TP+FN)
  f1 <- 2 * precision * recall / (precision + recall)  # F1分数
  cat(sprintf('%s: P=%.3f R=%.3f F1=%.3f\n', cls, precision, recall, f1))
}

# ============================================================
# 步骤8：查看各类别最重要的特征词
# ============================================================
# coef() 提取LASSO模型的回归系数（非零系数=被选中的特征词）
# 系数为正 → 该词增加属于该类别的概率
# 系数为负 → 该词降低属于该类别的概率
# 系数为0 → 该词被LASSO正则化剔除（不参与分类）
coef_matrix <- as.matrix(coef(classifier, s='lambda.min'))  # 提取系数矩阵

for (cls in colnames(coef_matrix)) {              # 遍历每个类别
  top_features <- sort(coef_matrix[, cls],         # 按系数值排序
                       decreasing=TRUE)[1:10]       # 取前10个最大系数
  cat(sprintf('\n%s - Top features:\n', cls))       # 打印类别名
  for (word in names(top_features)) {                # 遍历前10个词
    cat(sprintf('  %s: %.4f\n', word, top_features[word]))  # 打印词和系数
  }
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
