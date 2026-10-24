# R语言数据分析手册

> 从环境配置到高级统计建模的完整指南
>
> 共 68 个方法，20 章结构，按三篇组织

> 递进主线：环境准备 → 数据管理 → 质性探索 → 研究设计 → 测量 → 描述 → 预测 → 机制 → 分型 → 整合 → 嵌套

---

## 目录

**认识篇**

- **第1章 R语言基础**（3 个方法）
- **第2章 数据管理**（7 个方法）
**基础篇**

- **第3章 统计检验力分析**（3 个方法）
- **第4章 文本分析**（5 个方法）
- **第5章 信效度分析**（10 个方法）
- **第6章 回归分析**（12 个方法）
- **第7章 结构方程模型分析**（6 个方法）
**高阶篇**

- **第8章 组态分析**（2 个方法）
- **第9章 剖面分析**（3 个方法）
- **第10章 偏最小二乘结构方程模型**（1 个方法）
- **第11章 非线性结构方程模型**（1 个方法）
- **第12章 交叉滞后模型分析**（1 个方法）
- **第13章 经验取样分析**（1 个方法）
- **第14章 主客体互依模型分析**（1 个方法）
- **第15章 广义线性混合模型分析**（5 个方法）
- **第16章 响应面分析**（1 个方法）
- **第17章 元分析**（3 个方法）
- **第18章 社会网络分析**（1 个方法）
- **第19章 大语言模型分析**（1 个方法）
- **第20章 混合研究方法分析**（1 个方法）

---

## 前言

R语言是一种广泛应用于统计分析、数据挖掘和科学计算的开源编程语言。本手册系统整合了68个R数据分析方法，聚焦组织行为与人力资源管理（OBHRM）研究的常用方法。

### 阅读指南

- 每个方法按「方法论说明 → 使用条件 → 核心R包 → 代码与注释 → 结果解读」组织
- 代码中 `#` 后为注释；代码开头 `# ---- 将 xxx 替换为你的 xxx ----` 标注了需要修改的变量名
- 部分方法使用OBHRM.net的示例数据，实际使用时请替换为自己的数据

### 术语说明

- **有调节的中介**（Moderated Mediation）：中介过程（间接效应a×b）受到调节变量影响
- **有中介的调节**（Mediated Moderation）：交互效应（X×Z）通过中介变量传递
- 两者不同：前者关注"间接效应是否随Z变化"，后者关注"交互效应是否通过M传递"（温忠麟, 2006, 2014）

---

**认识篇**

## 第1章 R语言基础

### 1.1 R语言简介

**方法论说明**：R是免费、开源、跨平台的统计分析软件与编程语言，可从 https://www.r-project.org/ 下载。相比 SPSS/SAS 等商业软件，R 的优势在于：①完全免费开源，分析可复现；②CRAN 上拥有超过 2 万个扩展包，
几乎覆盖所有统计方法；③绘图功能强大（ggplot2）；④脚本化分析保证结果可重复、可追溯。R 已广泛应用于组织行为与人力资源管理（OBHRM）研究，尤其擅长结构方程模型（lavaan）、多层模型（lme4）、元分析（metafor）等。
建议同时安装 RStudio（https://www.rstudio.com/）作为集成开发环境。R 的基本操作模式为命令行交互式：在控制台输入命令并按回车执行。

| 命令 | 功能说明 |
| --- | --- |
| getwd() | 查看当前工作目录 |
| setwd("路径") | 设置工作目录 |
| help(function) | 查看函数帮助文档 |
| ls() | 列出当前环境中的所有变量 |
| rm(var) | 删除指定变量 |

```r
# ---- 无需修改变量，直接运行 ----
# >>> 基本操作 <<<
getwd()                          # 查看当前工作目录
setwd('D:/myproject')            # ---- 将路径替换为你的工作目录 ----
help(lm)                         # 查看函数帮助文档（等价于 ?lm）
ls()                             # 列出当前环境中的所有变量
rm(list=ls())                    # 清空所有变量（谨慎使用）

# >>> 查看已安装的包 <<<
installed.packages()[,1]         # 列出所有已安装的R包名称
.libPaths()                      # 查看R包安装路径
```

### 1.2 R的安装与升级

**方法论说明**：从 https://www.r-project.org/ 下载并安装 R，建议同时安装 RStudio（https://www.rstudio.com/）作为集成开发环境。本节涵盖界面语言切换与 R 的升级。

**使用条件**：需联网下载安装程序
#### 1.2.1 中英文界面切换

**方法论说明**：在中文Windows系统中，R默认界面为中文。如需切换为英文，可通过修改启动参数或配置文件实现。

- 右击R图标 > 属性 > 在【目标】后加空格再添加 lang=en
- 或在R安装目录etc下的Rprofile.site文件中添加 Sys.setenv(LANGUAGE="en")

切换回中文：移除上述设置即可。

```r
# ---- 无需修改变量，直接运行 ----
# >>> 方法1：临时切换（仅当前R会话有效）<<<
Sys.setenv(LANGUAGE='en')  # 切换为英文
Sys.setenv(LANGUAGE='zh')  # 切换回中文

# >>> 方法2：永久切换（修改配置文件）<<<
# 找到R安装目录下的 etc/Rprofile.site 文件
# 在文件末尾添加以下代码（保存后重启R即可生效）：
# Sys.setenv(LANGUAGE='en')  # 设置为英文

# >>> 方法3：快捷方式参数 <<<
# 右击R图标 > 属性 > 在【目标】栏末尾添加空格和 lang=en
# 如：C:/Program Files/R/R-4.3.0/bin/Rgui.exe lang=en
```

**结果解读**：方法1仅对当前R会话有效，重启后恢复系统默认语言。方法2和方法3修改的是配置文件，重启R后仍然生效。如需切换回中文，删除或注释掉对应代码即可。

#### 1.2.2 R的升级

**方法论说明**：R升级后已安装的包不会自动迁移，需手动重新安装。installr包可一键完成升级和包迁移。

**核心R包**：installr

```r
# ---- 无需修改变量，直接运行 ----
install_packages('installr')          # 安装installr包（仅需一次）
library(installr)                     # 加载installr包
updateR()                             # 启动升级向导，按提示操作即可

# >>> 手动迁移已安装包 <<<
oldpackages <- installed.packages()[,1]              # 保存升级前的包列表
save(oldpackages, file='installedPackages.Rdata')    # 保存到文件
# --- 升级R后执行以下代码 ---
load('installedPackages.Rdata')                      # 加载旧包列表
newpackages <- installed.packages()[,1]              # 获取升级后的包列表
for(i in setdiff(oldpackages, newpackages))          # 找出缺失的包
  install_packages(i)                                # 逐个重新安装
```
**结果解读**：升级后运行 R.version 确认新版本号，用 installed.packages() 确认旧包已迁移或重新安装。

### 1.3 R包管理

**方法论说明**：管理R包的使用（安装与加载）、安装目录、引用方式、GitHub安装与下载量查询。

**使用条件**：已安装 R；安装/下载包时需联网
#### 1.3.1 使用R包

```r
# ---- 将 pkg 替换为你要使用的包名 ----
install_packages('psych')        # 从CRAN安装R包（仅需运行一次）
library(psych)                   # 加载已安装的R包到当前会话
installed.packages()[,1]         # 列出所有已安装的R包名称
```
**结果解读**：library() 加载无报错即成功，可用 packageVersion('pkg') 查看已加载包的版本。

#### 1.3.2 R包的安装目录

**方法论说明**：查看默认安装目录：在R控制台输入 .libPaths()。默认在C盘Program Files下。如需修改，编辑R安装目录etc下的Rprofile.site文件，在末尾添加：

```r
# ---- 将路径替换为你的自定义安装目录 ----
# >>> 查看当前安装目录 <<<
.libPaths()  # 显示R包默认安装路径

# >>> 临时修改安装目录（重启R后失效）<<<
.libPaths(new='D:/MyDocuments/R/win-library/4.3')

# >>> 永久修改安装目录 <<<
# 在R安装目录 etc/Rprofile.site 文件末尾添加：
# .libPaths('D:/MyDocuments/R/win-library/4.3')  # 替换为你的目录

# >>> 查看某包的安装位置 <<<
system.file(package='lavaan')  # 查看lavaan包的安装路径
find.package('lavaan')        # 等价写法
```
**结果解读**：.libPaths() 显示当前包的安装路径列表，system.file(package='pkg') 查看具体包的安装位置。

#### 1.3.3 引用R语言或某个具体的包

**方法论说明**：在论文中引用R：输入 citation() 获取引用信息。引用特定包：输入 citation("lavaan")。

*R Core Team (2020). R: A language and environment for statistical computing. R Foundation for Statistical Computing, Vienna, Austria. URL https://www.R-project.org/*

```r
# ---- 将 lavaan/lme4 替换为你要引用的包名 ----
citation()              # 引用R语言本身
citation('lavaan')      # 引用lavaan包
citation('lme4')        # 引用lme4包
citation('psych')       # 引用psych包
# 将输出结果复制到论文参考文献中
# 如需BibTeX格式：
toBibtex(citation('lavaan'))
```
**结果解读**：citation() 输出可直接复制到论文参考文献的引用信息，toBibtex() 可转为 BibTeX 格式。

#### 1.3.4 从GitHub安装R包

**方法论说明**：CRAN上的包可能不是最新版本，从GitHub可安装开发版。

**核心R包**：devtools

```r
# ---- 将 yrosseel/lavaan 替换为你要安装的包的GitHub路径 ----
install_packages('devtools')            # 安装devtools（仅需一次）
library(devtools)                       # 加载devtools
install_github('yrosseel/lavaan')       # 从GitHub安装lavaan包
# 搜索引擎输入'包名 github'即可获取路径
```
**结果解读**：安装成功后 library() 可正常加载开发版包，注意开发版可能不如 CRAN 稳定。

#### 1.3.5 查询R包的下载量

**方法论说明**：cranlogs包可查询CRAN上R包的历史下载数据，用于评估R包的流行度和社区活跃度。

**核心R包**：cranlogs

```r
# ============================================================
# 查询R包下载量 — cranlogs 包
# ============================================================
# 用于查看CRAN上R包的下载量，评估包的流行度和维护活跃度
# 在选择工具包时，下载量可作为参考指标之一
# ============================================================

# ---- 安装并加载包（仅需运行一次） ----
install_packages('cranlogs')  # 安装cranlogs包
library(cranlogs)             # 加载包

# ---- 将 lme4 替换为你要查询的包名 ----

# ============================================================
# 步骤1：查看热门包排行榜
# ============================================================
# 查看过去1个月下载量前100的R包
# when='last-month'：时间范围可选'last-day'/'last-week'/'last-month'
# count=100：返回前100个包
cran_top_downloads(when='last-month', count=100)

# ============================================================
# 步骤2：查看指定包的每日下载量
# ============================================================
# 查看lme4包过去1个月每天的下载量
# 返回数据框：date列和count列
cran_downloads(packages='lme4', when='last-month')

# ============================================================
# 步骤3：计算指定包的总下载量
# ============================================================
# sum()对count列求和，得到该时间段的总下载量
sum(cran_downloads(packages='lme4', when='last-month')$count)

# ============================================================
# 步骤4：可视化下载趋势（可选）
# ============================================================
dl_data <- cran_downloads(packages='lme4', when='last-month')
plot(dl_data$date, dl_data$count, type='l',  # type='l'画线图
     xlab='Date', ylab='Downloads',           # 坐标轴标签
     main='lme4 package downloads (last month)')
```

**结果解读**：cran_top_downloads()返回下载量排名前N的包，通常dplyr/ggplot2/lavaan等热门包居前列。cran_downloads()返回指定包的每日下载量明细，sum()汇总为总下载量。下载量高说明包被广泛使用和维护良好。


## 第2章 数据管理

### 2.1 数据读取

**方法论说明**：R支持从文本文件(.txt/.dat)、CSV、Excel、SPSS(.sav)、SAS(.sas7bdat)、Stata(.dta)等多种格式读取数据。选择读取方式取决于原始数据格式。

**使用条件**：数据文件路径正确、格式受支持（txt/csv/xlsx/sav 等）
**核心R包**：foreign、memisc、xlsx

```r
# ---- 将文件路径替换为你的实际数据路径 ----

# >>> 读取固定格式文本数据（Fortran格式）<<<
mydata <- read.fortran('D:/01a.txt', list(
  c('2F2.0','F3.0','17F1.0'), c('26F1.0'), c('26F1.0'), c('20F1.0','2F2.0')))
names(mydata) <- c('company','group','no',
  paste('item',1:69,sep=''), paste('mbi',1:16,sep=''),
  'sex','age','edu','manager','year','month')

# >>> 读取自由格式文本数据 <<<
mydata <- read.table('ex5.1.dat', sep='')
names(mydata) <- c(paste('item',1:6,sep=''))

# >>> 读取CSV文件 <<<
mydata <- read.csv('data.csv', header=TRUE, encoding='UTF-8')

# >>> 读取Excel文件 <<<
install_packages('xlsx')  # 安装（仅需运行一次）
install_packages('foreign')  # 安装（仅需运行一次）
install_packages('memisc')  # 安装（仅需运行一次）
library(xlsx)
mydata <- read.xlsx('data.xlsx', 1)  # 读取第1个sheet

# >>> 读取SPSS文件 <<<
library(foreign)
mydata <- read.spss('data.sav', use.value.labels=FALSE, to.data.frame=TRUE)

# >>> 用memisc包读取SPSS（标签保留更完整）<<<
library(memisc)
mydata <- data.frame(as.data.set(spss.system.file('data.sav')))
```
**结果解读**：读取后用 str(mydata) 查看数据结构（变量类型、行列数），用 head(mydata) 预览前几行，确认变量名、类型和取值符合预期。

### 2.2 数据转换

**方法论说明**：数据转换指对已读取的数据进行结构变换，包括变量重命名、反向计分重编码、数据类型转换和新变量计算。重编码最常用于反向计分题目的处理——Likert 量表中反向题的分数需要翻转（5变1、4变2、3不变、2变4、1变5），使所有题目方向一致。

**使用条件**：已读取数据；明确需要重命名/重编码/类型转换的变量
**核心R包**：car、plyr

#### 2.2.1 变量重命名

```r
# ---- 将 mydata 替换为你的数据框名，item2/item5 替换为你的变量名 ----
names(mydata)[5] <- 'item5'                    # 将第5个变量改名为item5
install_packages('plyr')  # 安装（仅需运行一次）
library(plyr)
mydata <- rename(mydata, c(item2='y2', item5='y5'))  # 批量重命名
```
**结果解读**：转换后用 str(mydata) 或 table(mydata$变量) 验证变量类型和取值是否正确，确认反向计分后所有题目方向一致。

#### 2.2.2 变量重编码（反向计分）

```r
# ---- 将 mydata/item2 替换为你的数据框名和变量名 ----
install_packages('car')  # 安装（仅需运行一次）
library(car)
mydata$item2 <- recode(mydata$item2, '1=5;2=4;3=3;4=2;5=1;else=NA')
# '1=5'表示将1改为5，以此类推；else=NA表示其他值设为缺失
```
**结果解读**：重编码后用 table(mydata$item2) 检查取值分布，确认反向计分后所有题目方向一致（高分均代表同一含义）。

#### 2.2.3 数据类型转换

```r
# ---- 将 mydata 中的变量名替换为你的实际变量名 ----
mydata$group <- as.factor(mydata$group)       # 数值转因子（分类变量）
mydata$score <- as.numeric(mydata$score)     # 字符转数值
mydata$gender <- as.character(mydata$gender) # 数值转字符
mydata$date <- as.Date(mydata$date, '%Y-%m-%d') # 字符转日期
str(mydata)  # 查看各变量类型
```
**结果解读**：转换后用 str(mydata) 确认各变量类型正确（factor/numeric/character/Date），避免后续分析报错。

#### 2.2.4 简单计算

**方法论说明**：在R中计算新变量时，必须同时指定变量来源（哪个数据框）和保存位置。遗漏任一项都会导致错误。

```r
# ---- 将 mydata 替换为你的数据框名，item1/item2 替换为你的变量名 ----
# >>> 正确写法 <<<
mydata$itemsum <- mydata$item1 + mydata$item2           # 求和
mydata$itemmean <- (mydata$item1 + mydata$item2) / 2     # 求均值

# 使用transform函数（可一次创建多个变量）
mydata <- transform(mydata, itemsum = item1 + item2, itemmean = (item1 + item2) / 2)

# >>> 计算维度得分（多题均值）<<<
# ---- 将 item1/item3/item8/item20 替换为你的题目变量名 ----
mydata$ee <- rowMeans(mydata[, c('item1','item3','item8','item20')], na.rm=TRUE)
```
**结果解读**：计算后检查新变量的取值范围和分布是否符合预期，维度得分用 rowMeans 时注意 na.rm 参数。

### 2.3 数据清洗

**方法论说明**：数据清洗是分析前必不可少的步骤，包括异常值检测、重复值处理、变量标签管理和缺失值处理。脏数据会严重影响后续分析结果的准确性。

**使用条件**：已读取数据；需检查异常值、重复值、缺失值
**核心R包**：Hmisc、mice

#### 2.3.1 异常值检测

```r
# ---- 将 mydata 替换为你的数据框名，score/x1/x2/x3 替换为你的变量名 ----
# >>> 方法1：箱线图法 <<<
boxplot.stats(mydata$score)$out          # 提取异常值（超出1.5倍IQR的值）
boxplot(mydata$score)                    # 可视化查看异常值

# >>> 方法2：Z分数法 <<<
z_scores <- scale(mydata$score)          # 计算Z分数
mydata$score[abs(z_scores) > 3]          # |Z|>3视为异常值
```
**结果解读**：箱线图超出上下须（1.5 倍 IQR）的点与 |Z|>3 的值视为异常值，需结合专业判断决定删除还是保留。

#### 2.3.2 重复值处理

```r
# ---- 将 mydata/caseid 替换为你的数据框名和唯一标识变量 ----
duplicated(mydata)                         # 检查每行是否重复
sum(duplicated(mydata))                    # 统计重复行数
mydata <- mydata[!duplicated(mydata), ]   # 删除完全重复的行
mydata <- mydata[!duplicated(mydata$caseid), ]  # 按关键变量去重
```
**结果解读**：sum(duplicated()) 报告重复行数，去重后数据行数应减少相应数量，按 caseid 去重更精准。

#### 2.3.3 变量标签管理

```r
# ---- 将 mydata/score 替换为你的数据框名和变量名 ----
install_packages('Hmisc')
library(Hmisc)
label(mydata$score) <- '工作满意度得分'       # 设置变量标签
label(mydata)                                  # 查看所有变量标签
```
**结果解读**：label() 查看变量标签是否正确设置，清晰的标签便于后续结果解读与报告。

#### 2.3.4 缺失数据处理

**方法论说明**：数据缺失分为三种机制——MCAR（完全随机缺失）、MAR（随机缺失）、MNAR（非随机缺失）。当缺失比例<5%时直接删除影响不大；当缺失比例>10%时建议使用多重插补（MICE）。

**核心R包**：mice

```r
# ---- 将 mydata 替换为你的数据框名，y/x1/x2 替换为你的变量名 ----
# >>> 检查缺失情况 <<<
colSums(is.na(mydata))      # 每个变量的缺失值数量
mean(is.na(mydata))         # 总体缺失比例

# >>> 删除缺失值（适用于缺失比例<5%）<<<
mydata_complete <- na.omit(mydata)

# >>> 多重插补法 MICE（适用于缺失比例>5%）<<<
install_packages('mice')
library(mice)
imp <- mice(mydata, m=5, method='pmm', seed=123)
# m=5: 生成5个插补数据集，method='pmm': 预测均值匹配
completed_data <- complete(imp, 1)  # 提取第1个完整数据集
fit <- with(imp, lm(y ~ x1 + x2))  # 在5个数据集上分别回归
pooled <- pool(fit)                 # 用Rubin规则合并结果
summary(pooled)
```
**结果解读**：colSums(is.na()) 报告各变量缺失数，插补后 complete() 生成完整数据集，pool() 合并多个插补结果。

#### 2.3.5 样本筛选与抽样

**方法论说明**：样本筛选指从数据集中选择或删除符合特定条件的样本，是数据管理中贯穿多个环节的核心操作——包括条件筛选（按变量取值）、去重（删除重复样本）、删除缺失样本、随机抽样（抽取子集）。注意：去重与缺失处理在 2.3 数据清洗中已涉及，此处聚焦"按条件选择/删除样本"的完整流程。

```r
# ---- 将 mydata 替换为你的数据框名，age/sex 替换为你的筛选变量 ----
# >>> 条件筛选 <<<
newdata <- mydata[mydata$age>=40 & mydata$sex=='M', ]  # 直接索引
newdata <- subset(mydata, age>=40 & sex=='M')            # subset函数
newdata <- subset(mydata, age>=40 | sex=='M')            # 或条件

# >>> 删除重复样本 <<<
newdata <- mydata[!duplicated(mydata$caseid), ]          # 按关键变量去重

# >>> 删除缺失样本 <<<
newdata <- subset(mydata, !is.na(item3))            # 仅删除item3有缺失的样本
newdata <- subset(mydata, complete.cases(mydata))   # 删除任何变量有缺失的样本

# >>> 随机抽样 <<<
set.seed(123)                                         # 设随机种子，保证抽样可重复
newdata <- mydata[sample(1:nrow(mydata), 100, replace=FALSE), ]  # 不放回抽样100个
```

**结果解读**：条件筛选返回满足条件的子集；去重按唯一标识（如 caseid）删除重复记录；缺失删除会损失样本，仅适用于缺失比例 <5% 的情况；随机抽样需设随机种子（set.seed）以保证结果可重复。

### 2.4 数据合并

**方法论说明**：数据合并分两种——"合并变量"是横向扩展（同一批样本增加新变量），使用merge()；"合并样本"是纵向扩展（不同样本追加到末尾），使用rbind()。

**使用条件**：多个数据框需有共同匹配变量（merge）或相同结构（rbind）

**核心R包**：stats（基础）

```r
# ---- 将 mydata1/mydata2 替换为你的数据框名，caseid 替换为匹配变量 ----
# >>> 合并变量（横向）<<<
mydata <- merge(mydata1, mydata2, by='caseid')
mydata <- merge(mydata1, mydata2, by.x='caseid', by.y='sampleid')  # 标识变量名不同时
mydata <- merge(mydata1, mydata2, by='caseid', all=TRUE)  # 保留全部

# >>> 合并样本（纵向）<<<
mydata <- rbind(mydata1, mydata2)
# 注意：合并前必须确保两个数据框的变量数量和名称完全一致
```
**结果解读**：合并后用 dim(mydata) 确认行列数，用 names(mydata) 确认变量名，检查是否有意外丢失的样本或重复记录。

### 2.5 数据中心化

**方法论说明**：中心化是将变量减去其均值，使新均值为0。在调节效应分析中，中心化可减少多重共线性，使交互项系数更易解释。分为总均值中心化（CGM）和分组均值中心化（CWC）。

**使用条件**：变量为连续型；嵌套数据需有分组变量
**核心R包**：misty

```r
# ---- 将 mydata 替换为你的数据框名，Score 替换为你的变量名 ----
# ---- 如有嵌套数据，GroupID 替换为你的分组变量 ----

# >>> 总均值中心化（Grand Mean Centering）<<<
mydata$Score_grand <- mydata$Score - mean(mydata$Score)       # 方法1：手动减均值
mydata$Score_grand <- scale(mydata$Score, scale=FALSE)        # 方法2：scale函数

# >>> 分组均值中心化（Group Mean Centering）<<<
mydata$Score_group <- mydata$Score - ave(mydata$Score, mydata$GroupID)
# ave()按GroupID分组计算各组均值，再用原始值减去组均值

# >>> 使用misty包（推荐用于嵌套数据）<<<
install_packages('misty')
library(misty)
# 注意：center() 第一个参数是数据框（非向量），分组变量用 cluster 指定（字符串）
# type='CGM' 总均值中心化；type='CWC' 分组均值中心化；默认生成新列 Score.c
mydata <- center(mydata, Score, type='CGM', cluster='GroupID')  # 总均值中心化
mydata <- center(mydata, Score, type='CWC', cluster='GroupID')  # 分组均值中心化
```
**结果解读**：中心化后变量均值应接近 0（可用 round(mean(x), 6)==0 验证），分组中心化后各组内均值应接近 0。

### 2.6 数据保存

**方法论说明**：数据分析完成后需保存结果。选择格式取决于后续使用场景：CSV通用性最强；Excel适合查看；SPSS格式适合跨软件协作。

**使用条件**：已完成数据处理；明确输出格式
**核心R包**：foreign、xlsx

```r
# ---- 将 mydata 替换为你的数据框名，文件名替换为你的输出路径 ----
# 保存为CSV（推荐）
write.csv(mydata, 'mydata.csv', row.names=FALSE)
# 保存为Excel
install_packages('xlsx')  # 安装（仅需运行一次）
install_packages('foreign')  # 安装（仅需运行一次）
library(xlsx)
write.xlsx(mydata, 'mydata.xlsx', row.names=FALSE, showNA=FALSE)
# 保存为SPSS格式
library(foreign)
write.foreign(mydata, 'mydata.sav', 'mycode.sps', package='SPSS')
# 保存为R数据文件（加载最快）
saveRDS(mydata, 'mydata.rds')
save(mydata, file='mydata.RData')
```
**结果解读**：保存后用对应的读函数（read.csv/read.spss 等）重新读入，确认数据完整无损（行列数、变量类型一致）。

### 2.7 数据可视化

**方法论说明**：ggplot2基于"图形语法"理论，通过分层叠加图层构建图表。核心组件：数据(aes) + 几何对象(geom) + 标度(scale) + 主题(theme)。数据读取和清洗后即可可视化检查分布和关系。

**使用条件**：已读取并清洗数据；明确要展示的变量关系
**核心R包**：ggplot2

```r
# ---- 将 mydata 替换为你的数据框名，x1/y/group/score 替换为你的变量名 ----
install_packages('ggplot2')  # 安装（仅需运行一次）
library(ggplot2)

# 散点图（含回归线）
ggplot(mydata, aes(x=x1, y=y)) +
  geom_point(aes(color=group)) +
  geom_smooth(method='lm', se=TRUE) +
  labs(title='Scatter Plot', x='X1', y='Y') + theme_minimal()

# 箱线图
ggplot(mydata, aes(x=group, y=score, fill=group)) +
  geom_boxplot() + theme_classic()

# 直方图+密度曲线
ggplot(mydata, aes(x=score)) +
  geom_histogram(aes(y=after_stat(density)), bins=30, fill='steelblue', color='white') +
  geom_density(color='red', size=1) + theme_minimal()
```
**结果解读**：散点图用于观察变量关系与趋势（含回归线），箱线图用于比较组间分布与识别异常值，直方图+密度曲线用于检查变量分布形态（是否近似正态）。


**基础篇**

## 第3章 统计检验力分析

### 3.1 统计检验力与样本量规划

**方法论说明**：统计检验力（Power = 1−β）是正确拒绝原假设的概率；样本量规划需在收集数据前基于预期效应量、α、Power 反推所需 n。分为 a priori（规划样本量）、post hoc（已达检验力）、sensitivity（可检最小效应）。SEM / 纵向研究可用 semPower 做模型级效力分析。

**使用条件**：研究设计阶段（a priori 规划）；投稿时审稿人常要求检验力 / 样本量论证；纵向 / SEM 模型需专门工具。

**核心R包**：`pwr`（基础 t / ANOVA / 相关 / 卡方）、`pwrss`（中介 / 逻辑回归等扩展）、`semPower`（SEM 与纵向效力，见 3.3）。

**R 示例（指向脚本 `../../../r-analysis/scripts/03-power/3.2.R`）**：

```r
# ---- 根据你的研究设计选择对应的函数，替换参数值 ----
library(pwr)

# >>> 基础方法：pwr 包（pwr.t.test/pwr.anova.test/pwr.f2.test/pwr.r.test）<<<
# T 检验（两组均值比较）：d=0.5（中等效应），效力 0.80
pwr.t.test(d=0.5, sig.level=0.05, power=0.80, type='two.sample')
# d: Cohen's d 效应量（0.2小/0.5中/0.8大），sig.level: 显著性水平，power: 统计效力

# 单因素 ANOVA（3 组比较）：f=0.25（中等效应）
pwr.anova.test(k=3, f=0.25, sig.level=0.05, power=0.80)
# k: 组数，f: Cohen's f 效应量（0.1小/0.25中/0.4大）

# 多元回归（2 个预测变量）：f2=0.15（中等效应）
pwr.f2.test(u=2, f2=0.15, sig.level=0.05, power=0.80)
# u: 分子自由度（预测变量数），f2: Cohen's f²（0.02小/0.15中/0.35大）

# 相关分析：r=0.3（中等效应）
pwr.r.test(r=0.3, sig.level=0.05, power=0.80)

# >>> 扩展方法：pwrss 包（中介、逻辑回归等）<<<
library(pwrss)
# 中介效应样本量（间接效应 a*b 的效力检验）
pwrss.z.mediation(a=0.3, b=0.3, cp=0.1, alpha=0.05, power=0.80)
# a: X→M 路径系数，b: M→Y 路径系数，cp: 直接效应 c′

# 逻辑回归样本量
pwrss.z.logreg(p1=.3, p0=.5, alpha=0.05, power=0.80)

# >>> SEM 的效力分析：semPower 包 <<<
library(semPower)
# 先验效力分析（已知效应量和效力，求样本量）
sp <- semPower.aPriori(effect=.10, effect.measure='RMSEA',
                        alpha=.05, power=.80, df=20)
# effect=.10: RMSEA=0.10，effect.measure 指定效应量类型，df: 模型自由度
summary(sp)
plot(sp)  # 可视化效力曲线
```

**结果解读**：样本量预估的核心逻辑是：效应量越小、效力要求越高、显著性水平越严格，所需样本量越大。`pwr` 包覆盖基础 T 检验 / ANOVA / 回归 / 相关；`pwrss` 扩展到中介效应、逻辑回归；
`semPower` 专门针对 SEM 与纵向研究的模型级效力。**横向研究**在数据收集前基于预期效应量（小 0.2 / 中 0.5 / 大 0.8，或参考类似研究）反推所需最小 n；
纵向 / SEM 模型需用 `semPower` 考虑模型自由度和 RMSEA。建议在研究设计阶段参考类似已发表研究的效应量进行估计，必要时报告敏感性分析（sensitivity）。
### 3.2 样本量预估（横向研究）

**方法论说明**：样本量预估是研究设计阶段的关键步骤。统计效力=1-β，即正确拒绝错误原假设的概率，通常要求效力≥0.80。pwr包覆盖基础统计方法（T检验/ANOVA/回归/相关）；pwrss包扩展到中介效应、逻辑回归等；semPower包专门针对SEM的效力分析。

**使用条件**：在数据收集前使用；需预先估计效应量（小0.2/中0.5/大0.8，或参考类似研究的效应量）。

**核心R包**：pwr、pwrss、semPower

```r
# ---- 根据你的研究设计选择对应的函数，替换参数值 ----
install_packages('pwr')  # 安装（仅需运行一次）
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
install_packages('pwrss')
library(pwrss)
# 中介效应样本量（间接效应a*b的效力检验）
pwrss.z.mediation(a=0.3, b=0.3, cp=0.1,
                  alpha=0.05, power=0.80)
# a: X->M路径系数，b: M->Y路径系数，cp: 直接效应c'

# 逻辑回归样本量
pwrss.z.logreg(p1=.3, p0=.5, alpha=0.05, power=0.80)
# p1: X=1时的P(Y=1)，p0: X=0时的P(Y=1)

# >>> SEM的效力分析：semPower包 <<<
install_packages('semPower')
library(semPower)
# 先验效力分析（已知效应量和效力，求样本量）
sp <- semPower.aPriori(effect=.10, effect.measure='RMSEA',
                        alpha=.05, power=.80, df=20)
# effect=.10: RMSEA=0.10，effect.measure指定效应量类型
# df: 模型自由度
summary(sp)
plot(sp)  # 可视化效力曲线
```

**结果解读**：样本量预估的核心逻辑是：效应量越小、效力要求越高、显著性水平越严格，所需样本量越大。建议在研究设计阶段参考类似已发表研究的效应量进行估计。

### 3.3 纵向研究的效力分析

**方法论说明**：纵向研究（交叉滞后、潜增长）的样本量预估是研究设计的关键环节。semPower 提供专门的纵向效力函数：powerCLPM 检验交叉滞后效应，powerLGCM 检验潜增长模型的斜率均值等关键参数。与传统"事后检验效力"不同，这些函数用于"先验分析"（a-priori），即在数据收集前根据预期的效应量确定所需最小样本量。

**使用条件**：需预先设定效应量（自回归效应、交叉滞后效应、斜率均值等）、波次数、各潜变量的指标数与因子载荷；若无法确定效应量，可参考同类已发表研究或采用保守（较小）的效应量估计。

**核心R包**：semPower

```r
# ---- 根据你的研究设计设定效应量与波次数 ----
install_packages('semPower')  # 安装（仅需运行一次）
library(semPower)

# >>> 1. 交叉滞后模型（CLPM）效力 <<<
# 检验 X 的交叉滞后效应（X1 → Y2）是否显著异于 0
powerCLPM <- semPower.powerCLPM(
  type='a-priori',
  nWaves=2,                       # 波次（时间点）数
  autoregEffects=c(.8, .7),       # X、Y 的自回归（稳定性）效应
  crossedEffects=c(.2, .1),       # 交叉滞后效应（X1→Y2, Y1→X2）
  rXY=NULL,                       # X 与 Y 的同步相关（NULL=不设定）
  nullEffect='crossedX = 0',      # 检验 X 的交叉滞后效应是否为 0
  nIndicator=c(5, 3, 5, 3),       # 各潜变量（X1,X2,Y1,Y2）的指标数
  loadM=c(.5, .6, .5, .6),        # 各潜变量的因子载荷
  alpha=.05, beta=.05             # 显著性水平与 II 类错误率
)
summary(powerCLPM)                # 查看所需最小样本量

# >>> 2. 潜增长曲线模型（LGCM）效力 <<<
# 检验斜率因子均值（sMean）是否显著异于 0（即是否存在显著增长趋势）
powerLGCM <- semPower.powerLGCM(
  type='a-priori', alpha=.05, power=.80,
  nWaves=3,                       # 波次数
  means=c(.5, .2),                # 截距、斜率因子的均值
  variances=c(1, .5),             # 截距、斜率因子的方差
  covariances=.25,                # 截距-斜率协方差
  nullEffect='sMean = 0',         # 检验斜率均值为 0
  nIndicator=rep(3, 3), loadM=.5, # 各波次指标数与载荷
  autocorResiduals=TRUE           # 假设自相关残差
)
summary(powerLGCM)                # 查看所需最小样本量
```

**结果解读**：powerCLPM 输出检验交叉滞后效应所需的最小样本量；powerLGCM 输出检验斜率均值所需样本量。纵向研究通常需要较大样本——交叉滞后效应越小、波次越多、指标数越少，所需样本量越大。建议在研究设计阶段据此预留足够样本，并在方法部分报告效力分析过程。

```
# 运行：Rscript 3.2.R 你的数据.csv
library(pwr)
pwr.t.test(d = 0.3, power = 0.8, sig.level = 0.05, type = "two.sample")  # a priori：d=0.3 需 n≈176/组
# 纵向 / SEM：library(semPower); semPower.power...（见 3.3.R）
```

**结果解读**：Power≥0.8 为常规阈值；小效应需大样本；纵向 / 多层模型因嵌套结构，所需样本（对子 / 个体数）应按模型层分别论证。


## 第4章 文本分析

### 4.1 扎根理论分析

**方法论说明**：扎根理论由Glaser和Strauss提出，通过系统化的开放式编码、主轴编码和选择性编码，从文本数据中自下而上地构建理论。RQDA是基于R的质性数据分析包，支持文本导入、编码、检索、分类和可视化。

**使用条件**：质性文本数据（访谈记录、田野笔记、文档等）；文本格式为TXT/RTF/PDF；研究者需具备扎根理论方法论基础。

**核心R包**：RQDA

```r
# ---- 将 interview1.txt 等替换为你的文本文件路径 ----
install_packages('RQDA')  # 安装（仅需运行一次）
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

```

**结果解读**：编码表显示每个编码的频次和文本片段。编码共现矩阵揭示哪些编码经常同时出现，帮助识别核心范畴。扎根理论三阶段：开放式编码到主轴编码到选择性编码。RQDA依赖GTK+，Windows需额外安装GTK+运行时。

### 4.2 文本预处理与语料库构建

**方法论说明**：文本分析的第一步是将原始文本转换为结构化数据。quanteda包支持语料库构建、分词、清洗、文档-词矩阵（DFM）创建。中文文本需用jiebaR分词。

**使用条件**：文本数据为字符串向量或文本文件；中文文本需额外分词。

**核心R包**：quanteda、jiebaR

```r
# ---- 将 texts 替换为文本字符向量 ----
install_packages('quanteda')  # 安装（仅需运行一次）
install_packages('jiebaR')    # 安装（仅需运行一次，中文分词用）
library(quanteda)
library(jiebaR)

# >>> 创建语料库 <<<
# texts <- c('text1...', 'text2...', ...)
# 或从文件读取：texts <- readLines('data.txt', encoding='UTF-8')
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

```

**结果解读**：DFM的行=文档，列=词，值=词频。topfeatures()显示高频词。TTR高表示词汇丰富。dfm_trim()去除过于稀少或普遍的词。中文需先用jiebaR分词。

### 4.3 主题模型

**方法论说明**：LDA是无监督文本分析方法，假设每篇文档由多个主题的混合构成，每个主题由词的概率分布表示。LDA自动发现文档集合中的潜在主题结构。

**使用条件**：文档集合（建议>50篇）；每篇文档至少50词；需先完成文本预处理和DFM创建。

**核心R包**：topicmodels、quanteda

```r
# ---- 需先运行4.2创建DFM，将 dfm_text 替换为你的DFM对象 ----
install_packages('topicmodels')  # 安装（仅需运行一次）
install_packages('quanteda')  # 安装（仅需运行一次）
library(topicmodels)
library(quanteda)

# >>> 从DFM创建LDA输入 <<<
dtm <- convert(dfm_text, to='topicmodels')

# >>> 拟合LDA模型 <<<
# ---- 将 k=5 替换为通过比较确定的最优主题数 ----
lda_model <- LDA(dtm, k=5, method='Gibbs',
                control=list(seed=123, burnin=1000, iter=2000, thin=500))
print(lda_model)

# >>> 主题-词分布 <<<
terms(lda_model, 10)  # 每个主题的前10个词
beta <- posterior(lda_model)$terms  # 主题-词概率矩阵
topic_terms <- terms(lda_model, 10)
for (i in 1:nrow(topic_terms)) {
  cat(sprintf('Topic %d: %s\n', i, paste(topic_terms[i,], collapse=', ')))
}

# >>> 文档-主题分布 <<<
gamma <- posterior(lda_model)$topics  # 文档-主题概率矩阵
dominant_topic <- apply(gamma, 1, which.max)
table(dominant_topic)  # 各主题的文档数量

# >>> 可视化 <<<
barplot(beta[1, order(beta[1,], decreasing=TRUE)[1:10]],
       las=2, main='Topic 1 Top Words', col='steelblue')

```

**结果解读**：terms()输出每个主题中概率最高的词，需根据词的内容对主题命名和解释。gamma矩阵显示每篇文档在各主题上的概率分布。主题数k可通过不同k值的模型比较确定。

### 4.4 文本网络分析

**方法论说明**：文本网络分析将文本中的词作为节点，共现关系作为边，构建网络图。可揭示概念关联结构、主题聚类和关键节点。igraph包构建网络，ggraph包实现可视化。

**使用条件**：需先完成分词和词频分析；建议保留前50-200个高频词；共现窗口通常设为5-10词。

**核心R包**：igraph、ggraph

```r
# ============================================================
# 文本网络分析 — igraph + ggraph 包
# ============================================================
# 将文本中词语的共现关系构建为网络图
# 节点=词语，边=词语在同一窗口内共现的次数
# 用途：发现文本中的核心概念和主题社群
#
# 前置条件：需先运行4.2的文本预处理获取分词结果
# ============================================================

# ---- 安装并加载包（仅需运行一次） ----
install_packages('igraph')    # 网络分析核心包
install_packages('ggraph')   # 网络可视化（基于ggplot2）
install_packages('ggplot2')  # 安装（仅需运行一次）
library(igraph)               # 加载igraph
library(ggraph)               # 加载ggraph
library(ggplot2)              # 加载ggplot2

# ---- 将 tokens_result 替换为你的分词结果 ----
# tokens_result 格式：list(c('word1','word2',...), c('word3','word4',...), ...)
# 每个元素是一篇文档的分词向量

# ============================================================
# 步骤1：构建共现矩阵
# ============================================================
# 统计词频，选取高频词构建网络
all_words <- unlist(tokens_result)          # 展开所有词
word_freq <- table(all_words)                 # 统计词频
top_words <- names(sort(word_freq, decreasing=TRUE)[1:100])  # 前100高频词

# 构建共现边：在同一窗口内出现的词对
window_size <- 5  # 共现窗口大小（可调整，通常5-10）
edges <- list()
for (tokens in tokens_result) {
  tokens <- tokens[tokens %in% top_words]    # 仅保留高频词
  for (i in 1:length(tokens)) {
    end_idx <- min(i + window_size, length(tokens))
    for (j in (i+1):end_idx) {
      if (j > length(tokens)) break
      edges[[length(edges)+1]] <- c(tokens[i], tokens[j])  # 记录词对
    }
  }
}
edge_df <- as.data.frame(do.call(rbind, edges))
colnames(edge_df) <- c('from','to')

# 统计每对词的共现次数（边权重）
edge_weight <- as.data.frame(table(edge_df$from, edge_df$to))
edge_weight <- edge_weight[edge_weight$Freq > 0, ]  # 过滤掉0次
colnames(edge_weight) <- c('from','to','weight')

# ============================================================
# 步骤2：创建网络图
# ============================================================
# graph_from_data_frame() 从边列表创建网络
graph_net <- graph_from_data_frame(edge_weight, directed=FALSE)
# simplify() 合并重复边，汇总权重
graph_net <- simplify(graph_net,
                     remove.multiple=TRUE,        # 合并重复边
                     edge.attr.comb='sum')        # 权重求和

# ============================================================
# 步骤3：网络指标计算
# ============================================================
# 度数(Degree)：节点的连接数，越高表示该词越核心
degree_net <- degree(graph_net)
# 介数(Betweenness)：节点作为最短路径桥梁的次数
between_net <- betweenness(graph_net)
# 输出度数最高的20个词（核心概念）
print(sort(degree_net, decreasing=TRUE)[1:20])

# ============================================================
# 步骤4：社区检测（主题发现）
# ============================================================
# Louvain算法：基于模块度优化的社区检测
# 同一社区内的词关联紧密，可理解为一个"主题"
community <- cluster_louvain(graph_net)
for (i in 1:length(community)) {
  cat(sprintf('Community %d: %s\n', i, paste(community[[i]], collapse=', ')))
}
# 每个Community即一个主题词群，可人工解读主题含义

# ============================================================
# 步骤5：可视化
# ============================================================
# ggraph基于ggplot2语法绘制网络图
# layout='fr'：Fruchterman-Reingold力导向布局
ggraph(graph_net, layout='fr') +
  geom_edge_link(alpha=0.3, aes(width=weight)) +           # 边：透明度+权重
  geom_node_point(aes(size=degree(graph_net)),              # 节点大小=度数
                  color='steelblue') +
  geom_node_text(aes(label=name), repel=TRUE, size=3) +     # 节点标签
  theme_void() +                                              # 去除背景
  labs(title='Text Co-occurrence Network')
# 图形解读：
#   - 大节点=核心词（高频/高连接度）
#   - 同色聚类=同一主题社群
#   - 边越粗=两词共现越频繁
```

**结果解读**：度数最高的词是核心概念。介数高的词是连接不同社区的桥梁。社区检测将词聚类为主题。Louvain算法通过最大化模块度发现社区。节点大小反映度数，边宽度反映共现频率。

### 4.5 文档自动分类

**方法论说明**：文档自动分类是监督学习方法，将文本分配到预定义的类别。流程：文本预处理到TF-IDF特征提取到训练分类器（朴素贝叶斯/SVM/随机森林）到评估。text2vec包提供高效TF-IDF计算和分类管道。

**使用条件**：需要标注好的训练数据（每篇文档有已知类别）；每类至少10-20篇文档；需划分训练集和测试集。

**核心R包**：text2vec、glmnet

```r
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

install_packages('text2vec')  # 安装text2vec包（高效文本特征提取）
install_packages('glmnet')    # 安装glmnet包（LASSO/Elastic Net回归）
library(text2vec)             # 加载text2vec
library(glmnet)               # 加载glmnet

# ---- 将 mydata 替换为你的数据框名 ----
# ---- 将 text 替换为文本内容列名（字符型向量） ----
# ---- 将 label 替换为类别标签列名（因子型factor） ----

# ============================================================
# 步骤1：划分训练集与测试集（80/20）
# ============================================================
set.seed(123)  # 设定随机种子，确保结果可复现
# 随机抽取80%的样本作为训练集索引
train_idx <- sample(1:nrow(mydata), 0.8 * nrow(mydata))
data_train <- mydata[train_idx, ]   # 训练集：用于学习词表和训练分类器
data_test  <- mydata[-train_idx, ]  # 测试集：用于评估分类器性能
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

```

**结果解读**：混淆矩阵展示各类别分类情况。F1分数是精确率和召回率的调和均值。LASSO通过L1正则化自动选择特征，非零系数的词为分类贡献词。每类别权重最大的词反映该类别的关键特征。TF-IDF结合词频和逆文档频率。中文文本需将tokenizer替换为jiebaR分词器。

## 第5章 信效度分析

### 5.1 信度分析

**方法论说明**：信度衡量测量的一致性。Cronbach alpha系数是最常用的信度指标，反映量表内部各题目间的一致性程度。OBHRM 中，量表开发与修订时均需报告 Cronbach's α，通常 > 0.7 可接受、> 0.8 良好。

**使用条件**：量表至少包含3个题目，数据为连续型或Likert量表分数。

**核心R包**：psych

```r
# ---- 如用自己的数据，将 q_262 等替换为你的题目变量名 ----
install_packages('psych')  # 安装（仅需运行一次）
library(psych)
data <- read.table('https://personality-project.org/r/datasets/extraversion.items.txt', header=TRUE)
e <- data.frame(data$q_262, data$q_1480, data$q_819, data$q_1180, data$q_1740)
alpha(e, check.keys=TRUE)
# alpha判断标准：>0.9优秀，0.8-0.9良好，0.7-0.8可接受，<0.6需修改量表
```
**结果解读**：alpha() 输出 raw_alpha（原始 α）与 std.alpha（标准化 α）。Cronbach's α > 0.9 优秀、0.8-0.9 良好、0.7-0.8 可接受、< 0.6 需修改或删除题目。item 统计中的 r.drop（删除该题后的 α）用于判断题目质量，若删除某题后 α 明显提升，应考虑删除该题。

### 5.2 探索性因素分析

**方法论说明**：EFA在无预设假设的情况下从数据中探索潜在因子结构。核心步骤：KMO检验 → 确定因子数（平行分析/碎石图）→ 因子提取 → 旋转。EFA 假设存在潜在因子（测量误差被分离），
而 PCA 只是数据降维（不分离误差）——量表开发应优先用 EFA 而非 PCA。旋转分正交（varimax，假设因子不相关）与斜交（promax/oblimin，允许因子相关）；心理构念之间通常相关，斜交旋转更贴合实际。OBHRM 中，
新量表（如新开发的领导力或工作重塑量表）的初始阶段常用 EFA 探索维度结构。

**使用条件**：样本量>题目数的5倍；KMO>0.6；Bartlett检验p<0.05。

**核心R包**：psych

```r
# ---- 如用自己的数据，将 mydata[,1:5] 替换为你的变量列范围 ----
install_packages('psych')  # 安装（仅需运行一次）
library(psych)
mydata <- read.table('https://personality-project.org/r/datasets/maps.mixx.epi.bfi.data', header=TRUE)

# 步骤1：KMO检验和Bartlett球形检验
KMO(mydata[,1:5])                    # KMO>0.6表示适合做因素分析
cortest.bartlett(mydata[,1:5])       # p<0.05表示变量间有共同因素

# 步骤2：确定因子数量（平行分析）
fa.parallel(mydata[,1:5], fa='fa', n.iter=100)

# 步骤3：因子提取与旋转
efa <- fa(mydata[,1:5], nfactors=2, rotate='varimax')
print(efa, sort=TRUE)
# 因子载荷：>0.7优秀，>0.5良好，>0.4可接受

# 步骤4：碎石图（可视化因子特征值，辅助确定因子数）
scree(mydata[,1:5])
```

**结果解读**：① KMO>0.6 且 Bartlett p<0.05 表明数据适合因素分析；② 平行分析（fa.parallel）建议保留特征值大于随机数据特征值的因子数，碎石图在"拐点"处确定因子数；③ 因子载荷 >0.7 优秀、>0.5 良好、
>0.4 可接受，载荷过低（<0.4）或交叉载荷（同一题目在两个因子上都 >0.4）的题目需考虑删除；④ 根据高载荷题目对因子命名（如某因子高载荷题目都反映"工作投入"，则命名为该维度）；⑤ 若因子间理论上相关，
改用斜交旋转（rotate='promax'）并报告因子相关矩阵。

#### 5.2.1 主成分分析

**方法论说明**：PCA通过线性变换将多个相关变量降维为少数几个不相关的主成分，是探索性分析的降维技术。与EFA不同，PCA不假设潜在因子的存在，而是纯粹的数据压缩。

**使用条件**：变量为连续型；变量间存在一定相关性。

**核心R包**：FactoMineR

```r
# ---- 将 mydata 替换为你的数据框名，c('x1','x2','x3','x4','x5') 替换为你的变量名 ----
# 使用基础R函数
pca_result <- prcomp(mydata[, c('x1','x2','x3','x4','x5')], scale=TRUE)
summary(pca_result)  # 各主成分方差贡献比例（累计>80%通常足够）
plot(pca_result, type='l')  # 碎石图
pca_result$rotation         # 载荷矩阵

# 使用FactoMineR包
install_packages('FactoMineR')
library(FactoMineR)
pca <- PCA(mydata[, c('x1','x2','x3','x4','x5')], scale.unit=TRUE, ncp=2, graph=TRUE)
```

### 5.3 探索性结构方程模型

**方法论说明**：ESEM（Exploratory Structural Equation Modeling）是 EFA 与 CFA/SEM 的结合，允许交叉载荷（cross-loadings）存在，同时保留 SEM 的模型检验能力。
传统 CFA 强制"简单结构"（每个题目只负荷一个因子），当量表存在较多交叉载荷时会导致拟合恶化；ESEM 允许题目在多个因子上有载荷，更贴近实际数据。OBHRM 中，当构念边界模糊或量表存在交叉载荷时（如组织公民行为与工作绩效、工作投入与工作满意度），
ESEM 比 CFA 更合适。

**使用条件**：已通过 EFA 初步确定因子结构；怀疑存在交叉载荷；样本量建议 > 200。

**核心R包**：lavaan

```r
# ---- 将 mydata 替换为数据框名，y1-y6 替换为你的量表题目 ----
install_packages('lavaan')  # 安装（仅需运行一次）
library(lavaan)

# 步骤1：指定 ESEM 模型（efa() 语法，2个因子，geomin 旋转）
esem_model <- "efa('efa1')*efa('efa2') =~ y1 + y2 + y3 + y4 + y5 + y6"
fit_esem <- efa(esem_model, data=mydata, nfactors=2, rotation='geomin')

# 步骤2：查看因子载荷（注意存在交叉载荷）
summary(fit_esem, standardized=TRUE)
# 载荷矩阵：每个题目在多个因子上都有载荷（交叉载荷）

# 步骤3：与 CFA 比较拟合
# 传统 CFA（简单结构，无交叉载荷）
cfa_model <- '
  f1 =~ y1 + y2 + y3
  f2 =~ y4 + y5 + y6
'
fit_cfa <- cfa(cfa_model, data=mydata)
# 比较 ESEM 和 CFA 的拟合
anova(fit_esem, fit_cfa)  # 若 ESEM 拟合显著更好，说明交叉载荷不可忽略
fitMeasures(fit_esem, c('cfi','tli','rmsea','srmr'))
fitMeasures(fit_cfa, c('cfi','tli','rmsea','srmr'))
```

**结果解读**：ESEM 的载荷矩阵中，若交叉载荷较大（如 |λ| > 0.30），说明题目在多个因子上有实质负荷，传统 CFA 的简单结构假设不成立，ESEM 更合适。若 ESEM 与 CFA 的拟合差异不大（ΔCFI < 0.01），则可优先选择更简洁的 CFA。ESEM 是 EFA（探索）到 CFA（验证）之间的桥梁，适合量表结构尚不完全确定的阶段。

### 5.4 一阶验证性因素分析

**方法论说明**：CFA根据理论预设的因子结构进行检验，回答"我假设的量表结构是否与实际数据拟合"。需要事先指定哪些题目属于哪个因子。OBHRM 中用于验证成熟量表（如工作满意度、组织承诺）的因子结构是否适用于当前样本，是结构效度的核心证据。

**使用条件**：样本量>200；每个因子至少3个题目；数据近似正态分布。

**核心R包**：lavaan、semPlot、semTools

```r
# ============================================================
# 一阶验证性因素分析（CFA） — lavaan + semPlot + semTools
# ============================================================
# CFA根据理论预设的因子结构进行检验
#
# CFA分析流程：
#   1. 指定模型 -> 2. 拟合模型 -> 3. 评估拟合指标
#   -> 4. 模型比较（模型1/2/3递进） -> 5. 信度效度 -> 6. 路径图
# ============================================================

# ---- 安装并加载包（仅需运行一次） ----
install_packages('lavaan')    # SEM核心包
install_packages('semPlot')   # 路径图可视化
install_packages('semTools')  # SEM辅助工具
library(lavaan)               # 加载lavaan
library(semPlot)              # 加载semPlot
library(semTools)              # 加载semTools

# ---- 将 y1-y6 替换为你的量表题目变量名 ----
# ---- 将 f1/f2 替换为你的因子名 ----

# ============================================================
# 步骤1：准备数据
# ============================================================
cfadata <- read.table('https://www.statmodel.com/usersguide/chap5/ex5.1.dat')
names(cfadata) <- c(paste('y', 1:6, sep=''))

# ============================================================
# 步骤2：模型1 — 单因子模型（所有题目载荷到一个因子）
# ============================================================
model1 <- '
  f1 =~ y1 + y2 + y3 + y4 + y5 + y6
'
fit1 <- cfa(model1, data=cfadata)
summary(fit1, fit.measures=TRUE)

# ============================================================
# 步骤3：模型2 — 两因子模型（理论驱动的因子结构）
# ============================================================
model2 <- '
  f1 =~ y1 + y2 + y3    # 因子f1由y1,y2,y3测量
  f2 =~ y4 + y5 + y6    # 因子f2由y4,y5,y6测量
'
fit2 <- cfa(model2, data=cfadata)
summary(fit2, fit.measures=TRUE, standardized=TRUE)

# ============================================================
# 步骤4：模型3 — 三因子模型（更细分的因子结构）
# ============================================================
model3 <- '
  f1 =~ y1 + y2
  f2 =~ y3 + y4
  f3 =~ y5 + y6
'
fit3 <- cfa(model3, data=cfadata)
summary(fit3, fit.measures=TRUE)

# ============================================================
# 步骤5：模型比较（卡方差异检验）
# ============================================================
# 嵌套模型比较：模型1(最简单) vs 模型2 vs 模型3(最复杂)
anova(fit1, fit2)  # 模型1 vs 模型2: p<0.05说明模型2更优
anova(fit2, fit3)  # 模型2 vs 模型3: p>0.05则模型2足够简洁

# 也可以比较AIC/BIC（越小越好）
print(fitMeasures(fit1, c('aic', 'bic')))
print(fitMeasures(fit2, c('aic', 'bic')))
print(fitMeasures(fit3, c('aic', 'bic')))

# 拟合指标参考标准：
#   CFI/TLI > 0.90（>0.95良好）
#   RMSEA < 0.08（<0.05良好）
#   SRMR < 0.08

# ============================================================
# 步骤6：信度与效度检验
# ============================================================
# 选定最优模型后（通常是模型2）
compRelSEM(fit2)   # 组合信度 omega（原 reliability() 已弃用，CR>0.7 信度良好）
AVE(fit2)          # 平均方差抽取量（AVE>0.5 收敛效度可接受）

# ============================================================
# 步骤7：路径图可视化
# ============================================================
semPaths(fit2, whatLabels='std', layout='tree',
         edge.label.cex=0.8, sizeMan=8, sizeLat=6)

```

**结果解读**：拟合指标：CFI/TLI>0.90（>0.95良好），RMSEA<0.08（<0.05良好），SRMR<0.08。

### 5.5 二阶验证性因素分析

**方法论说明**：当理论认为一阶因子之上还存在一个更高阶的因子时使用。例如"工作满意度"下有"薪酬满意度""晋升满意度"等一阶因子。

**使用条件**：至少有4个一阶因子；一阶CFA拟合良好。

**核心R包**：lavaan

```r
# ============================================================
# 二阶验证性因素分析 — lavaan包
# ============================================================
# 一阶因子之上还存在一个更高阶的因子
# 例如："工作满意度"下有"薪酬满意度""晋升满意度"等一阶因子
#
# 模型结构示意：
#   高阶因子g
#   ├── f1 (一阶因子1) ← y1, y2, y3 (题目)
#   ├── f2 (一阶因子2) ← y4, y5, y6
#   └── f3 (一阶因子3) ← y7, y8, y9
# ============================================================

# ---- 安装并加载包 ----
install_packages('lavaan')  # SEM核心包
library(lavaan)              # 加载lavaan

# ---- 将 y1-y12 替换为你的量表题目变量名 ----
# ---- 将 f1-f5 替换为你的因子名 ----

# 步骤1：指定二阶CFA模型
secondorder_model <- '
  # 一阶因子（测量模型）
  f1 =~ y1 + y2 + y3        # 因子f1由y1,y2,y3测量
  f2 =~ y4 + y5 + y6        # 因子f2由y4,y5,y6测量
  f3 =~ y7 + y8 + y9        # 因子f3由y7,y8,y9测量
  f4 =~ y10 + y11 + y12     # 因子f4由y10,y11,y12测量

  # 二阶因子（结构模型）
  g =~ f1 + f2 + f3 + f4    # 高阶因子g由f1-f4测量
'

# 步骤2：拟合模型
fit_second <- cfa(secondorder_model, data=mydata)
summary(fit_second, fit.measures=TRUE, standardized=TRUE)
# 拟合指标：CFI/TLI>0.90, RMSEA<0.08, SRMR<0.08

# 步骤3：与一阶CFA比较（卡方差异检验）
# oneorder_model <- 'f1 =~ y1+y2+y3; f2 =~ y4+y5+y6; ...'
# fit_one <- cfa(oneorder_model, data=mydata)
# anova(fit_one, fit_second)  # p<0.05说明二阶模型更优
```

**结果解读**：二阶因子模型拟合指标需达到CFI/TLI>0.90,RMSEA<0.08。一阶因子在二阶因子上的载荷>0.5表示一阶因子能有效被高阶因子解释。若二阶模型拟合优于一阶模型，说明高阶因子结构合理。

### 5.6 BiFactor验证性因素分析

**方法论说明**：BiFactor模型假设所有题目在一个一般因子(g)上都有载荷，同时各自在特定群组因子上也有载荷。适用于检验量表是否既有总体维度又有子维度。

**核心R包**：lavaan、semTools

```r
# ============================================================
# BiFactor验证性因素分析 — lavaan + semTools包
# ============================================================
# 所有题目在一个一般因子(g)上都有载荷
# 同时各自在特定群组因子上也有载荷
#
# 模型结构示意：
#   g (一般因子) ← 所有题目(y1-y12)
#   ├── f1 (群组因子1) ← y1, y2, y3
#   ├── f2 (群组因子2) ← y4, y5, y6
#   └── f3 (群组因子3) ← y7, y8, y9
# ============================================================

# ---- 安装并加载包 ----
install_packages('lavaan')     # SEM核心包
install_packages('semTools')   # SEM辅助工具
library(lavaan)                # 加载lavaan
library(semTools)              # 加载semTools

# ---- 将 y1-y12 替换为你的量表题目变量名 ----
# ---- 将 g/f1-f4 替换为因子名 ----

# 步骤1：指定BiFactor模型
bifactor_model <- '
  g =~ y1 + y2 + y3 + y4 + y5 + y6 +      # 一般因子：所有题目
       y7 + y8 + y9 + y10 + y11 + y12
  f1 =~ y1 + y2 + y3                       # 群组因子1
  f2 =~ y4 + y5 + y6                       # 群组因子2
  f3 =~ y7 + y8 + y9                       # 群组因子3
  f4 =~ y10 + y11 + y12                    # 群组因子4
'

# 步骤2：拟合BiFactor模型
# orthogonal=TRUE：一般因子与群组因子正交（不相关）
fit_bi <- cfa(bifactor_model, data=mydata, orthogonal=TRUE)
summary(fit_bi, fit.measures=TRUE, standardized=TRUE)

# 步骤3：计算Omega信度（比Cronbach alpha更适合BiFactor）
# 用 semTools::compRelSEM() 输出模型基础信度（omega）
# 层级信度 omega_h：一般因子解释的方差比例（>0.50为高解释力）
compRelSEM(fit_bi)  # 输出 omega 信度；更高阶因子可用 higher= 参数指定
```
**使用条件**：量表既有总体维度又有子维度；样本量 > 200。

**结果解读**：输出中一般因子(g)的载荷反映各题目对总体构念的贡献，群组因子载荷反映题目对子维度的额外贡献。若一般因子与群组因子载荷均显著，说明量表适合 BiFactor 结构；可用 ωH（一般因子信度）与 ωS（子维度信度）分别判断总体与子维度信度。

### 5.7 测量不变性

**方法论说明**：测量不变性检验量表在不同群体（如性别、文化、年龄组）或不同时间点（纵向追踪）间是否测量相同的心理构念。通过多组CFA（MG-CFA）逐步施加等值约束，包含四个递进层级：
配置不变性（因子结构相同）→弱不变性/载荷不变性（因子载荷相等）→强不变性/截距不变性（截距相等）→严格不变性（残差方差相等）。只有满足强不变性才能安全进行跨组潜伏均值比较或跨时间均值比较。OBHRM 中，
跨组不变性用于比较不同群体（如新老员工、不同部门）的构念均值；纵向不变性则是交叉滞后、潜增长模型等纵向分析的前置步骤——若量表跨时间不等值，纵向比较的差异可能源于测量而非真实变化。

**使用条件**：样本量>200且各组样本量接近；每组至少100；已通过单组CFA确认因子结构拟合良好；分组变量为分类变量（如性别、国别）。

**核心R包**：lavaan、semTools

```r
# ---- 将 y1-y6 替换为你的量表题目变量名，f1/f2 替换为因子名，group 替换为分组变量 ----
install_packages('lavaan')  # 安装（仅需运行一次）
install_packages('semTools')  # 安装（仅需运行一次）
library(lavaan)
library(semTools)

# >>> 方法1：手动逐步检验（推荐，控制更精细）<<<
cfa_model <- '
  f1 =~ y1 + y2 + y3
  f2 =~ y4 + y5 + y6
'
# 第1步：配置不变性（Configural）——各组因子结构相同，无等值约束
fit_config <- cfa(cfa_model, data=mydata, group='group')
summary(fit_config, fit.measures=TRUE)

# 第2步：弱不变性/载荷不变性（Metric）——因子载荷跨组等值
fit_metric <- cfa(cfa_model, data=mydata, group='group',
                  group.equal='loadings')
lavTestLRT(fit_config, fit_metric)  # 似然比检验

# 第3步：强不变性/截距不变性（Scalar）——截距跨组等值
fit_scalar <- cfa(cfa_model, data=mydata, group='group',
                  group.equal=c('loadings','intercepts'))
lavTestLRT(fit_metric, fit_scalar)

# 第4步：严格不变性（Strict）——残差方差跨组等值
fit_strict <- cfa(cfa_model, data=mydata, group='group',
                  group.equal=c('loadings','intercepts','residuals'))
lavTestLRT(fit_scalar, fit_strict)

# >>> 方法2：semTools的measEq.syntax（新版替代已移除的measurementInvariance）<<<
# 生成各步等值约束的模型语法，再逐个用 cfa() 拟合
# meq <- measEq.syntax(configural.model=cfa_model, data=mydata, group='group')
# 返回 meq$model.configural / meq$model.metric / meq$model.scalar 等语法
# 例如：fit_metric <- cfa(meq$model.metric, data=mydata, group='group')
# 实际使用建议直接采用上方"方法1手动逐步检验"，控制更精细

# >>> 拟合指标差异判断标准（Chen, 2007）<<<
# 提取各步拟合指标进行比较
fits <- rbind(
  config = inspect(fit_config, 'fit.measures')[c('cfi','rmsea','srmr')],
  metric = inspect(fit_metric, 'fit.measures')[c('cfi','rmsea','srmr')],
  scalar = inspect(fit_scalar, 'fit.measures')[c('cfi','rmsea','srmr')],
  strict = inspect(fit_strict, 'fit.measures')[c('cfi','rmsea','srmr')]
)
print(fits)
# ΔCFI <= 0.01, ΔRMSEA <= 0.015, ΔSRMR <= 0.03 表示等值约束可接受

# >>> 纵向测量不变性（跨时间，OBHRM纵向研究前置检验）<<<
# 数据为宽格式：每个时间点一套题目（如 y1_t1, y2_t1, y1_t2, y2_t2）
# 核心思想：同一量表在两个时间点的载荷和截距应等值（用相同标签约束）
long_inv_model <- '
  # 时间点1的因子（载荷用 l1/l2/l3 标签）
  f_t1 =~ l1*y1_t1 + l2*y2_t1 + l3*y3_t1
  # 时间点2的因子（载荷约束与时间点1相等，实现载荷不变性）
  f_t2 =~ l1*y1_t2 + l2*y2_t2 + l3*y3_t2
  # 截距约束相等（强不变性）
  y1_t1 ~ i1*1
  y1_t2 ~ i1*1
  y2_t1 ~ i2*1
  y2_t2 ~ i2*1
  y3_t1 ~ i3*1
  y3_t2 ~ i3*1
'
fit_long <- cfa(long_inv_model, data=mydata)
summary(fit_long, fit.measures=TRUE)
# 比较"等值约束模型"与"无约束模型"（去掉 l/i 等值标签）的 ΔCFI
# ΔCFI <= 0.01 表示跨时间不变性成立，可安全进行纵向均值/关系比较
# 若不成立，说明量表在追踪期间测量属性发生变化，纵向结论需谨慎
```

**结果解读**：配置不变性：各组因子结构相同是前提，CFI/TLI>0.90,RMSEA<0.08。弱不变性：ΔCFI≤0.01且ΔSRMR≤0.03表示载荷等值成立，意味着各题目对因子的贡献跨组一致。强不变性：
ΔCFI≤0.01且ΔRMSEA≤0.015表示截距等值成立，此时可安全比较跨组潜伏均值。严格不变性：ΔCFI≤0.01表示残差方差等值成立，要求最严格，实践中常可放宽。若某步不满足，可对部分题目释放约束（partial invariance），
用lavTestScore()识别需释放的参数。纵向不变性：原理同跨组，但"组"变为时间点，要求同一量表在不同时间点载荷与截距等值。若纵向强不变性成立，说明量表的测量属性在追踪期间稳定，
交叉滞后或潜增长模型中观测到的均值/关系变化可归因于真实构念变化而非测量漂移。

### 5.8 共同方法偏差检验

**方法论说明**：共同方法偏差（Common Method Variance/Common Method Bias）指因数据来源相同（同一被试、同一问卷、同一时间自评）导致变量间关系被系统性高估。OBHRM 问卷研究中，
自变量与因变量常由同一被试在同一份问卷中自评，是 CMV 的高风险情境。常用检验方法：(1) Harman 单因子检验——对全部题目做探索性因素分析，看单一因子是否解释绝大部分方差；
(2) 单因子 CFA（共同方法因子法）——在测量模型中加入一个所有题目都负荷的方法因子，比较有无方法因子的拟合差异；(3) 标记变量法——用理论上无关的标记变量估计方法效应。

**使用条件**：核心变量均为同一来源（自评）的横截面数据；通常作为中介/回归分析前的稳健性检验。

**核心R包**：psych、lavaan

```r
# ---- 将 mydata 替换为数据框名，x1-x6 替换为你的全部量表题目 ----
install_packages('psych')   # 安装（仅需运行一次）
install_packages('lavaan')  # 安装（仅需运行一次）
library(psych)
library(lavaan)

# >>> 方法1：Harman单因子检验（最常用、最简单）<<<
# 对所有量表题目做单因子EFA
harman_fa <- fa(mydata[, c('x1','x2','x3','x4','x5','x6')], nfactors=1, rotate='none')
print(harman_fa$Vaccounted)
# 判断：第一个因子解释的方差比例 < 50%（严格标准 40%）→ 无严重CMV
# 若第一个因子解释 > 50% 方差，提示存在明显共同方法偏差

# >>> 方法2：单因子CFA（共同方法因子法，更严格）<<<
# 步骤1：正常的多因子测量模型
model_normal <- '
  f1 =~ x1 + x2 + x3
  f2 =~ x4 + x5 + x6
'
fit_normal <- cfa(model_normal, data=mydata)

# 步骤2：加入共同方法因子（所有题目同时负荷到 cmv）
model_cmv <- '
  f1 =~ x1 + x2 + x3
  f2 =~ x4 + x5 + x6
  cmv =~ x1 + x2 + x3 + x4 + x5 + x6   # 方法因子
  # 方法因子与实质因子正交，保证模型可识别
  cmv ~~ 0*f1
  cmv ~~ 0*f2
'
fit_cmv <- cfa(model_cmv, data=mydata)

# 步骤3：比较两个模型
anova(fit_normal, fit_cmv)  # 卡方差异检验，p<0.05 → 方法因子显著（存在CMV）
# 实际中更常用 ΔCFI 判断：加入方法因子后 CFI 提升 < 0.01 → 无实质CMV
```

**结果解读**：Harman 单因子检验中，若第一个因子解释方差比例 < 50%（部分文献用 40% 更严格标准），说明不存在单一因子主导，CMV 不严重。单因子 CFA 中，加入方法因子后若卡方差异不显著（或 ΔCFI < 0.01），
说明方法因子未实质改善模型，可认为 CMV 不构成威胁。注意：Harman 单因子检验仅作初筛，敏感度较低；期刊审稿人通常要求同时报告更严格的单因子 CFA 或标记变量法结果。

### 5.9 判别效度检验

**方法论说明**：判别效度（Discriminant Validity）指不同构念之间确实可区分、不重叠。OBHRM 研究中构念常高度相关（如工作满意度与组织承诺），需证明它们是不同构念。两种标准：
(1) Fornell-Larcker 准则——每个构念 AVE 的平方根应大于该构念与其他任何构念的相关系数；(2) HTMT 比率（异质-单质相关比）——< 0.85（严格）或 < 0.90（宽松）表示判别效度成立。
HTMT 近年已成为推荐标准（Henseler et al., 2015），比 Fornell-Larcker 更稳健。

**使用条件**：已建立 CFA 测量模型；适用于 ≥2 个潜变量的模型。

**核心R包**：lavaan、semTools

```r
# ---- 将 mydata 替换为数据框名，x1-x9 替换为你的量表题目 ----
install_packages('lavaan')    # 安装（仅需运行一次）
install_packages('semTools')  # 安装（仅需运行一次）
library(lavaan)
library(semTools)

# 步骤1：拟合多因子CFA模型
cfa_model <- '
  f1 =~ x1 + x2 + x3
  f2 =~ x4 + x5 + x6
  f3 =~ x7 + x8 + x9
'
fit <- cfa(cfa_model, data=mydata)

# 步骤2：计算聚合效度（AVE，平均方差抽取量）
AVE(fit)
# 每个构念 AVE > 0.5 → 聚合效度良好
# 组合信度（omega）用 compRelSEM()，> 0.7 信度良好
compRelSEM(fit)

# 步骤3：Fornell-Larcker 准则
# 潜变量相关矩阵
cor_lv <- lavInspect(fit, 'cor.lv')
print(cor_lv)
# 判断：每个构念 sqrt(AVE) 应 > 它与任何其他构念的相关系数
sqrt_ave <- sqrt(AVE(fit))
print(sqrt_ave)
# 若某构念的 sqrt(AVE) < 它与其他构念的相关系数 → 判别效度存疑

# 步骤4：HTMT 比率（推荐，更稳健）
htmt(cfa_model, data=mydata)
# HTMT < 0.85（严格）或 < 0.90（宽松）→ 判别效度成立
```

**结果解读**：AVE > 0.5 表示聚合效度良好（构念能解释其题目的大部分方差）。判别效度：Fornell-Larcker 准则下，若某构念 AVE 的平方根小于它与其他构念的相关系数，说明该构念与另一构念过于重叠；
HTMT 比率 < 0.85（或 0.90）表示两构念可区分。当两个构念高度相关（如相关系数 > 0.8）时，HTMT 更能准确判断判别效度，因此是当前 OBHRM 期刊更推荐的指标。

### 5.10 法则效度检验

**方法论说明**：法则效度（nomological validity）指构念与理论上相关的其他构念（效标构念）之间的关系是否符合理论预期，是构念效度的"终极检验"。一个量表不仅要内部一致（信度）、结构清晰（CFA）、与其他构念可区分（判别效度），
还应与理论上相关的构念呈现预期的正/负相关。OBHRM 中，如工作投入量表应与工作满意度正相关、与离职意愿负相关；若这些关系方向错误或不显著，说明量表可能测错了构念。

**使用条件**：已建立目标构念的测量模型；有理论依据的效标构念（至少1个）；样本量 > 200。

**核心R包**：lavaan

```r
# ---- 将 mydata 替换为数据框名，各变量替换为你的量表题目 ----
library(lavaan)

# 步骤1：建立含效标构念的完整测量模型
# 目标构念 F1 + 效标构念 F2（理论正相关）、F3（理论负相关）
nom_model <- '
  # 测量模型
  F1 =~ x1 + x2 + x3          # 目标构念（如工作投入）
  F2 =~ y1 + y2 + y3          # 效标1（如工作满意度，理论正相关）
  F3 =~ z1 + z2 + z3          # 效标2（如离职意愿，理论负相关）
  # 结构模型（法则网络）
  F2 ~ F1                      # F1对F2应为正
  F3 ~ F1                      # F1对F3应为负
'
fit_nom <- sem(nom_model, data=mydata)
summary(fit_nom, standardized=TRUE)

# 步骤2：检验路径系数的方向和显著性
# F2~F1 应显著为正；F3~F1 应显著为负
# 若方向与理论一致且显著，说明目标构念具有法则效度
```

**结果解读**：检查目标构念与各效标构念的标准化路径系数：方向应与理论一致（如工作投入→工作满意度为正、→离职意愿为负），且统计显著。若所有关键路径都符合理论预期，则目标构念的法则效度成立；若某条路径不显著或方向相反，需反思构念定义或量表测量是否准确。


## 第6章 回归分析

### 6.1 描述性统计

**方法论说明**：描述性统计是数据分析的第一步，用于了解数据的基本分布特征，包括集中趋势（均值/中位数）、离散程度（标准差/极差）、分布形态（偏度/峰度）。

**使用条件**：数据已读入R；变量类型已确认（连续型/分类型）。

**核心R包**：descr、psych

```r
# ============================================================
# 描述性统计 — descr + psych包
# ============================================================
# 数据分析第一步：了解数据的基本分布特征
# 包括：频次、均值、标准差、中位数、偏度、峰度
# ============================================================

# ---- 安装并加载包 ----
install_packages('descr')   # 频次表包
install_packages('psych')   # 描述统计包
library(descr)               # 加载descr
library(psych)               # 加载psych

# ---- 将 mydata 替换为你的数据框名 ----
# ---- 将 sex 替换为你要查看频次的分类变量名 ----

# 步骤1：频次表（分类变量）
freq(mydata$sex)  # 输出各类别的频次和百分比

# 步骤2：描述统计（连续变量）
describe(mydata)
# 输出：n(样本量)、mean(均值)、sd(标准差)、median(中位数)
#       skew(偏度)、kurtosis(峰度)、min/max(范围)

# 步骤3：分组描述统计
describeBy(mydata, group=mydata$sex)  # 按性别分组统计

# 步骤4：相关矩阵（多个连续变量间）
cor(mydata[, c('x1','x2','x3')], use='complete.obs')  # 删除缺失后计算
```

**结果解读**：describe()输出均值、标准差、中位数、trimmed mean（截尾均值）、mad（中位绝对偏差）、min/max、skew（偏度：|偏度|>1为极端偏态）、kurtosis（峰度：>3为尖峰）。describeBy()按分组变量输出各组的描述统计，便于组间比较。

### 6.2 相关分析

**方法论说明**：Pearson相关适用于连续变量且近似正态分布；Spearman秩相关适用于有序变量或不满足正态分布的情况。

**使用条件**：两个或以上连续变量；Pearson需满足正态分布和线性关系假设；Spearman不要求数据为连续型。

**核心R包**：psych

```r
# ============================================================
# 相关分析 — psych包
# ============================================================
# 衡量两个变量间的线性关联程度
# Pearson：连续变量+正态分布
# Spearman：有序变量或不满足正态分布
# ============================================================

# ---- 安装并加载包 ----
install_packages('psych')  # 心理测量包
library(psych)              # 加载psych

# ---- 将 epiE/epiS 等替换为你的变量名 ----

# 步骤1：Pearson相关（默认）
cor_result <- cor(epiE, epiS, method='pearson')
print(cor_result)  # 相关系数r：-1到1，绝对值越大关联越强

# 步骤2：相关矩阵（多变量间）
cor_matrix <- cor(mydata[, c('x1','x2','x3')], method='pearson')
print(cor_matrix)

# 步骤3：带p值的相关检验
corr.test(mydata[, c('x1','x2','x3')], method='pearson')
# 输出：相关系数矩阵和p值矩阵

# 步骤4：Spearman秩相关（非参数）
cor(mydata$x1, mydata$x2, method='spearman')

# 步骤5：可视化相关矩阵
pairs.panels(mydata[, c('x1','x2','x3')])  # 散点图矩阵+相关系数
```

**结果解读**：corr.test()输出相关系数矩阵和p值矩阵。相关系数r：|r|<0.1 negligible，0.1-0.3 small，0.3-0.5 medium，>0.5 large。p<0.05表示相关显著。corr.test()自动进行多重比较校正。

### 6.3 T检验

**方法论说明**：T检验比较两组均值差异。独立样本T检验用于两个独立组别；配对样本T检验用于同一组被试的前后测比较。

**使用条件**：独立样本T检验：两组独立、因变量近似正态、方差齐性（Levene检验p>0.05）。配对T检验：差值近似正态。

**核心R包**：stats（基础）、effsize

```r
# ============================================================
# T检验 — R基础stats包
# ============================================================
# 比较两组均值差异
# 独立样本：两个不同组别（如男vs女）
# 配对样本：同一组被试前后测比较
# ============================================================

# ---- 将 mydata 替换为数据框名 ----
# ---- 将 Ideal 替换为因变量名，Gender 替换为分组变量名 ----

# 步骤1：独立样本T检验（两组独立）
# 原假设H0：两组均值相等
# p<0.05 -> 两组均值有显著差异
t.test(Ideal ~ Gender, data=mydata)

# 步骤2：配对样本T检验（同一组前后测）
# paired=TRUE表示配对设计
t.test(mydata$pre, mydata$post, paired=TRUE)

# 步骤3：检查前提假设
# 正态性检验（Shapiro-Wilk）
shapiro.test(mydata$Ideal)  # p>0.05满足正态
# 方差齐性检验（Levene检验）
install_packages('car')  # 安装（仅需运行一次）
install_packages('effsize')  # 安装（仅需运行一次）
library(car)
leveneTest(Ideal ~ Gender, data=mydata)  # p>0.05方差齐

# 步骤4：效应量（Cohen's d）
library(effsize)
cohen.d(Ideal ~ Gender, data=mydata)
# d=0.2小效应, 0.5中等效应, 0.8大效应
```

**结果解读**：t.test()输出t值、自由度(df)、p值和95%置信区间。p<0.05表示两组均值差异显著。t检验结果中还有mean difference和95% CI，若CI不包含0则差异显著。Welch t检验（默认）不假设方差齐性。

### 6.4 单因素方差分析（ANOVA）

**方法论说明**：ANOVA用于比较三个或以上组的均值差异。如果ANOVA显著（p<0.05），需进行事后多重比较。

**使用条件**：因变量为连续型；各组独立；方差齐性（Levene检验p>0.05）；近似正态分布。

**核心R包**：stats（基础）、multcomp、effectsize

```r
# ============================================================
# 单因素方差分析（ANOVA） — R基础stats包
# ============================================================
# 比较三个或以上组的均值差异
# 如果ANOVA显著(p<0.05)，需进行事后多重比较
# ============================================================

# ---- 将 Alertness/group 替换为你的因变量/分组变量名 ----

# 步骤1：拟合ANOVA模型
aovresult <- aov(Alertness ~ group, data=mydata)
summary(aovresult)  # 输出F值和p值

# 步骤2：前提检验
# 正态性：各组残差正态分布
shapiro.test(resid(aovresult))
# 方差齐性：各组方差相等
install_packages('car')  # 安装（仅需运行一次）
install_packages('effectsize')  # 安装（仅需运行一次）
library(car)
leveneTest(Alertness ~ group, data=mydata)

# 步骤3：事后多重比较（ANOVA显著时）
TukeyHSD(aovresult)  # Tukey HSD检验：各组两两比较

# 步骤4：效应量（偏eta方）
library(effectsize)
eta_squared(aovresult)  # eta^2>0.01小, >0.06中, >0.14大

# 步骤5：可视化
boxplot(Alertness ~ group, data=mydata)  # 箱线图比较各组分布
```

**结果解读**：summary(aovresult)输出F值和p值。F检验p<0.05表示至少有一组与其他组不同。TukeyHSD()进行所有两两比较，输出每对组间差异的均值差、95%CI和调整后p值。p.adj<0.05表示该组对差异显著。

### 6.5 多因素方差分析（Factorial ANOVA）

**方法论说明**：同时检验两个或以上自变量的主效应及交互效应。交互效应显著时需进行简单主效应分析。

**核心R包**：emmeans、effectsize

```r
# ============================================================
# 多因素方差分析（Factorial ANOVA） — emmeans + effectsize包
# ============================================================
# 同时检验两个或以上自变量的主效应及交互效应
# 交互效应显著时需进行简单主效应分析
# ============================================================

# ---- 安装并加载包 ----
install_packages('emmeans')     # 事后比较包
install_packages('effectsize')  # 效应量包
library(emmeans)                 # 加载emmeans
library(effectsize)              # 加载effectsize

# ---- 将 score/teaching_method/study_time 替换为变量名 ----

# 步骤1：拟合多因素ANOVA模型
# * 表示同时检验主效应和交互效应
model <- aov(score ~ teaching_method * study_time, data=mydata)
summary(model)  # 输出：主效应、交互效应的F值和p值

# 步骤2：交互效应可视化（交互效应显著时）
interaction.plot(mydata$teaching_method, mydata$study_time, mydata$score)
# interaction.plot 无 data 参数，需用 $ 或 with() 显式指定数据框
# 线条交叉 -> 存在交互效应

# 步骤3：简单主效应分析（交互效应显著时）
emmeans(model, ~ teaching_method | study_time)  # 固定study_time比较teaching_method
pairs(emmeans(model, ~ teaching_method | study_time))  # 两两比较

# 步骤4：效应量
eta_squared(model)  # 偏eta方
```
**使用条件**：两个及以上分类自变量；因变量连续；各单元格方差齐性。

**结果解读**：关注主效应与交互效应。主效应显著说明某因素单独影响因变量；交互效应显著说明一个因素的效应随另一因素水平变化，此时应做简单效应分析（emmeans）而非只看主效应。

### 6.6 多元方差分析（MANOVA）

**方法论说明**：同时检验自变量对两个或以上连续因变量的影响，控制族系误差率。常用统计量：Pillai Trace、Wilks Lambda。

**使用条件**：因变量为连续型且多元正态分布；协方差矩阵齐性。

**核心R包**：stats（基础）、effectsize

```r
# ---- 将 mydata 替换为数据框名，score1/score2/score3 替换为因变量，group 替换为分组变量 ----
# >>> 多元方差分析（MANOVA）<<<
# 同时检验自变量对多个连续因变量的影响，控制族系误差率
# 结构图示：
#   group --> score1 (因变量1)
#         \-> score2 (因变量2)
#         \-> score3 (因变量3)
# MANOVA将这些因变量作为一个整体来检验组间差异

manova_model <- manova(cbind(score1, score2, score3) ~ group, data=mydata)

# 查看MANOVA结果（多种检验统计量）
summary(manova_model, test='Pillai')   # Pillai Trace（最稳健，推荐）
summary(manova_model, test='Wilks')    # Wilks Lambda（最常用）
summary(manova_model, test='Hotelling-Lawley')  # Hotelling-Lawley Trace
summary(manova_model, test='Roy')     # Roy最大根
# 四种统计量p<0.05均表示组间差异显著

# >>> MANOVA显著后的单变量ANOVA <<<
# 只有当MANOVA整体显著时才进行单变量检验
summary.aov(manova_model)  # 对每个因变量单独做ANOVA
# 注意：单变量ANOVA需Bonferroni校正（alpha = 0.05 / 因变量数）

# >>> 事后检验 <<<
install_packages('multcomp')  # 安装（仅需运行一次）
install_packages('mvnormtest')  # 安装（仅需运行一次）
install_packages('heplots')  # 安装（仅需运行一次）
# library(multcomp)
# 对显著的因变量做事后两两比较
# TukeyHSD(aov(score1 ~ group, data=mydata))  # score1的Tukey事后检验

# >>> 前提检验 <<<
# 多元正态性检验
library(mvnormtest)
# mshapiro.test(t(mydata[, c('score1','score2','score3')]))  # p>0.05为正态
# 协方差矩阵齐性检验
library(heplots)
# boxM(score1 + score2 + score3 ~ group, data=mydata)  # p>0.05为齐性
```

**结果解读**：summary(test="Pillai")输出Pillai Trace、F值、p值。p<0.05表示自变量对因变量组合有显著影响。summary.aov()输出每个因变量的单变量ANOVA结果，需Bonferroni校正（p<0.05/k）。

### 6.7 非参数检验

**方法论说明**：当数据不满足正态分布或为有序分类变量时使用。基于秩次进行比较，不要求数据分布形态。

**使用条件**：数据不满足正态分布或为有序分类变量；独立样本用Mann-Whitney/Wilcoxon，重复测量用Friedman。

**核心R包**：stats（基础）

```r
# ============================================================
# 非参数检验 — R基础stats包
# ============================================================
# 非参数检验不要求数据服从正态分布
# 适用于：小样本、有序分类变量、数据偏态或存在异常值时
#
# 检验选择决策树：
#   两组独立样本 -> Mann-Whitney U检验（wilcox.test）
#   两组配对样本 -> Wilcoxon符号秩检验（wilcox.test, paired=TRUE）
#   三组+独立样本 -> Kruskal-Wallis检验（kruskal.test）
#   三组+重复测量 -> Friedman检验（friedman.test）
# ============================================================

# ---- 将 mydata 替换为你的数据框名 ----
# ---- 将 score 替换为因变量名（连续或有序） ----
# ---- 将 group 替换为分组变量名 ----
# ---- 将 pre/post 替换为配对测量的变量名 ----
# ---- 将 t1/t2/t3 替换为重复测量时间点的变量名 ----

# ============================================================
# 步骤1：Mann-Whitney U检验（两组独立样本）
# ============================================================
# 非参数版的独立样本t检验
# 原假设H0：两组分布相同
# p<0.05 -> 两组得分分布有显著差异
wilcox.test(score ~ group, data=mydata)

# ============================================================
# 步骤2：Wilcoxon符号秩检验（两组配对样本）
# ============================================================
# 非参数版的配对样本t检验
# paired=TRUE表示配对设计（如前测-后测）
# 原假设H0：差值的中位数为0
wilcox.test(mydata$pre, mydata$post, paired=TRUE)

# ============================================================
# 步骤3：Kruskal-Wallis检验（三组及以上独立样本）
# ============================================================
# 非参数版的单因素方差分析
# 原假设H0：所有组分布相同
# p<0.05 -> 至少有一组与其他组不同
kruskal.test(score ~ group, data=mydata)
# 事后检验：pairwise.wilcox.test(score ~ group) 进行两两比较

# ============================================================
# 步骤4：Friedman检验（三组及以上重复测量）
# ============================================================
# 非参数版的重复测量方差分析
# 数据需为宽格式矩阵：每行=一个被试，每列=一个时间点
# 原假设H0：各时间点得分分布相同
friedman.test(as.matrix(mydata[, c('t1','t2','t3')]))
```

**结果解读**：wilcox.test()的W统计量基于秩和，p<0.05表示两组分布不同。kruskal.test()的chi-squared统计量p<0.05表示至少一组与其他不同。Friedman检验的chi-squared p<0.05表示时间点/条件间差异显著。

### 6.8 协方差分析（ANCOVA）

**方法论说明**：在ANOVA基础上加入协变量，控制混淆变量的影响。

**核心R包**：car

```r
# ---- 将 mydata 替换为你的数据框名，score/group/age 替换为因变量/分组变量/协变量 ----
install_packages('car')  # 安装（仅需运行一次）
library(car)
ancova <- aov(score ~ group + age, data=mydata)
summary(ancova)
# 检验斜率齐性假设
Anova(aov(score ~ group * age, data=mydata), type='III')
```
**使用条件**：因变量连续；协变量连续且与因变量线性相关；各组回归斜率同质（平行性假设）。

**结果解读**：协变量调整后，组间效应的 F 值与 p 值反映排除协变量影响后的净组间差异。调整后的边际均值（emmeans）用于报告各组在协变量均值水平上的因变量估计值。

### 6.9 重复测量方差分析

**方法论说明**：用于同一被试在多个时间点或条件下的测量比较。数据需为长格式。

**使用条件**：同一组被试在多个时间点（或条件下）重复测量；因变量连续；各时间点差值满足球形假设（Mauchly 检验）
**核心R包**：ez

```r
# ============================================================
# 重复测量方差分析 — ez包
# ============================================================
# 同一被试在多个时间点/条件下重复测量
# 常见场景：前测-后测-追踪、不同实验条件下的反应
#
# 数据格式要求：长格式（long format）
#   每行=一个观测值，被试ID可重复出现
#   示例：
#   subj_id  time   score
#   001      t1     5.2
#   001      t2     6.8
#   002      t1     4.1
#   002      t2     5.5
# ============================================================

# ---- 安装并加载包（仅需运行一次） ----
install_packages('ez')  # 安装ez包（简化方差分析流程）
library(ez)              # 加载包

# ---- 将 mydata_long 替换为你的长格式数据框名 ----
# ---- 将 score 替换为因变量名 ----
# ---- 将 subj_id 替换为被试ID变量名 ----
# ---- 将 time 替换为重复测量变量名（时间点或条件） ----

# ============================================================
# 步骤1：确保变量类型正确
# ============================================================
# subj_id和time必须是因子型(factor)，否则ezANOVA会报错
mydata_long$subj_id <- as.factor(mydata_long$subj_id)
mydata_long$time    <- as.factor(mydata_long$time)

# ============================================================
# 步骤2：运行重复测量方差分析
# ============================================================
# dv=score：因变量
# wid=subj_id：被试标识变量
# within=time：组内因素（重复测量变量）
# 若有组间因素可加between=group参数
result <- ezANOVA(data=mydata_long,
                  dv=score,          # 因变量
                  wid=subj_id,        # 被试ID
                  within=time)        # 组内因素（重复测量）

# ============================================================
# 步骤3：查看结果
# ============================================================
print(result)
# 输出包含：
#   1. Mauchly球形检验：p>0.05满足球形假设，p<0.05违背
#   2. Greenhouse-Geisser校正：违背球形假设时自动报告校正后的p值
#   3. 方差分析表：SS、df、MS、F、p、偏eta方
# 解读：p<0.05表示不同时间点的得分有显著差异

# ============================================================
# 步骤4：事后两两比较（可选）
# ============================================================
# 用pairwise.t.test进行各时间点之间的两两比较
pairwise.t.test(mydata_long$score, mydata_long$time,
                paired=TRUE,           # 配对比较
                p.adjust.method='bonferroni')  # Bonferroni校正

# ============================================================
# 步骤5：混合设计（组间+组内）
# ============================================================
# 若有组间因素（如实验组/对照组），可同时分析交互效应
# result_mixed <- ezANOVA(data=mydata_long,
#     dv=score, wid=subj_id, within=time, between=group)
# group为分组变量名（组间因素）
```

**结果解读**：ezANOVA()输出Mauchly球形检验，p<0.05时违背球形假设，自动提供Greenhouse-Geisser (GG)和Huynh-Feldt (HF)校正结果。时间主效应p<0.05表示各时间点均值不同。组内*组间交互显著时需做简单效应分析。


### 6.10 多元线性回归

**方法论说明**：检验多个自变量对因变量的预测作用。核心假设：线性关系、独立性、正态性、方差齐性、无多重共线性。

**使用条件**：因变量连续；样本量至少为预测变量数的 10-15 倍；无严重多重共线性（VIF<10）。

**核心R包**：car

```r
# ============================================================
# 多元线性回归 — car包
# ============================================================
# 检验多个自变量对因变量的预测作用
# 核心假设：线性、独立性、正态性、方差齐性、无多重共线性
#
# 模型：Y = b0 + b1*x1 + b2*x2 + b3*x3 + e
# ============================================================

# ---- 安装并加载包 ----
install_packages('car')  # 回归诊断包
library(car)              # 加载car

# ---- 将 mydata 替换为数据框名 ----
# ---- 将 y/x1/x2/x3 替换为因变量/自变量名 ----

# 步骤1：拟合回归模型
model1 <- lm(y ~ x1, data=mydata)             # 一元回归
model2 <- lm(y ~ x1 + x2 + x3, data=mydata)   # 多元回归
summary(model2)  # 输出：回归系数、t值、p值、R方

# 步骤2：回归诊断
# 多重共线性检验（VIF<5为可接受）
vif(model2)
# 残差正态性
qqPlot(model2)
# 方差齐性
plot(model2, 1)  # 残差vs拟合值图
# 独立性检验
durbinWatsonTest(model2)  # DW值接近2为独立

# 步骤3：标准化回归系数（比较自变量相对重要性）
summary(lm(scale(y) ~ scale(x1) + scale(x2) + scale(x3), data=mydata))
```

**结果解读**：summary(model2)输出回归系数(Estimate)、标准误(Std.Error)、t值和p值。p<0.05表示该自变量对因变量有显著预测作用。Multiple R-squared表示模型解释的方差比例（0-1）。
VIF>10表示严重多重共线性，需删除或合并变量。plot(model2)四图分别检查残差正态性(Q-Q图)、方差齐性、 leverage影响点和Cook距离。

### 6.11 多层回归分析（层次回归）

**方法论说明**：逐步加入变量组来检验增量解释力。通过Delta R-squared判断新变量是否显著增加解释力。

**使用条件**：因变量连续；样本量足够；各步骤模型需嵌套可比。

**核心R包**：stats（基础）

```r
# ============================================================
# 多层回归分析（层次回归） — R基础stats包
# ============================================================
# 逐步加入变量组来检验增量解释力
# 通过Delta R-squared判断新变量是否显著增加解释力
# ============================================================

# ---- 将 mydata 替换为数据框名，y/x1-x6 替换为变量名 ----

# 步骤1：逐层加入变量
step1 <- lm(y ~ x1 + x2, data=mydata)                        # 第一层：控制变量
step2 <- lm(y ~ x1 + x2 + x3 + x4, data=mydata)              # 第二层：主效应
step3 <- lm(y ~ x1 + x2 + x3 + x4 + x5*x6, data=mydata)      # 第三层：交互效应

# 步骤2：比较各层模型
anova(step1, step2)  # 检验step2是否显著优于step1
anova(step2, step3)  # 检验step3是否显著优于step2

# 步骤3：查看增量R方
summary(step1)$r.squared  # 第1层R方
summary(step2)$r.squared  # 第2层R方
summary(step3)$r.squared  # 第3层R方
# Delta R^2 = R^2(step2) - R^2(step1)
```

**结果解读**：anova(step1,step2,step3)输出各步的Res.Df、RSS和Delta R-squared的F检验。p<0.05表示新增变量显著增加解释力。Delta R-squared>0.02通常被认为有实际意义。最终报告时展示每步的R-squared变化量。

### 6.12 逻辑回归

**方法论说明**：当因变量为二分类（0/1）时使用，用logit变换将概率映射到(-inf, +inf)。

**核心R包**：MASS、pscl

```r
# ============================================================
# 逻辑回归 — stats包 + pscl + MASS
# ============================================================
# 因变量为二分类（0/1）时使用二元逻辑回归
# 因变量为有序多分类（如：低/中/高）时使用有序逻辑回归
#
# 模型结构示意：
#   logit(P(Y=1)) = b0 + b1*x1 + b2*x2 + b3*x3
#   P(Y=1) = exp(b0+b1*x1+...) / (1 + exp(b0+b1*x1+...))
# ============================================================

# ---- 将 mydata 替换为你的数据框名 ----
# ---- 将 binary_outcome 替换为二分类因变量名（0/1） ----
# ---- 将 x1, x2, x3 替换为自变量名 ----
# ---- 将 ordered_outcome 替换为有序分类因变量名 ----

# ============================================================
# 步骤1：二元逻辑回归
# ============================================================
# glm() 广义线性模型
# family=binomial(link='logit')：指定逻辑回归（logit链接函数）
logit_model <- glm(binary_outcome ~ x1 + x2 + x3,
                   data=mydata,
                   family=binomial(link='logit'))
summary(logit_model)
# 输出解读：
#   Estimate列：回归系数（logit尺度，不直观）
#   z value和Pr(>|z|)：z检验值和p值，p<0.05表示该变量显著

# ============================================================
# 步骤2：计算优势比（OR）及置信区间
# ============================================================
# exp(coef()) 将系数转为优势比(Odds Ratio)
# OR>1 -> 自变量增加1单位时，因变量=1的概率增加
# OR<1 -> 自变量增加1单位时，因变量=1的概率降低
# OR=1 -> 无影响
exp(coef(logit_model))

# 95%置信区间：若区间包含1则不显著
exp(confint(logit_model))

# ============================================================
# 步骤3：预测概率
# ============================================================
# type='response'：输出0~1之间的预测概率值
pred_prob <- predict(logit_model, type='response')
# 可设置阈值：pred_class <- ifelse(pred_prob > 0.5, 1, 0)

# ============================================================
# 步骤4：模型拟合优度（伪R方）
# ============================================================
install_packages('pscl')
install_packages('MASS')  # 安装（仅需运行一次）
library(pscl)
pR2(logit_model)  # McFadden/McKelvey/Cox-Snell等伪R方指标
# McFadden R方：0.2-0.4为良好拟合，>0.4为优秀

# ============================================================
# 步骤5：有序逻辑回归（因变量为有序分类）
# ============================================================
# 当因变量为有序多分类（如1=低,2=中,3=高）时使用polr()
# parallel lines assumption：各自变量的效应在所有切点处相同
library(MASS)
ologit <- polr(ordered_outcome ~ x1 + x2,
               data=mydata,
               Hess=TRUE)  # Hess=TRUE：计算Hessian矩阵用于标准误
summary(ologit)
# 检查比例优势假设：可用brant包的brant_test()
```
**使用条件**：因变量为二分变量（0/1）；自变量连续或分类；样本量至少为预测变量数的 10 倍。

**结果解读**：系数用 OR（odds ratio，exp(B)）解释——OR > 1 表示自变量增加时事件发生概率增大，OR < 1 表示减小。伪 R²（Nagelkerke R²）反映模型解释力，AUC 反映分类预测能力（> 0.8 良好）。


## 第7章 结构方程模型分析

### 7.1 结构方程模型分析

**方法论说明**：SEM同时包含测量模型（=~定义潜变量）和结构模型（~定义因果路径）。

**使用条件**：样本量>200（建议>10倍自由度）；数据近似多元正态；模型可识别（每个潜变量至少3个指标）。

**核心R包**：lavaan

```r
# ============================================================
# 结构方程模型分析（SEM） — lavaan包
# ============================================================
# 同时包含测量模型（=~定义潜变量）和结构模型（~定义因果路径）
#
# 模型结构示意：
#   测量模型：f1 =~ y1+y2+y3,  f2 =~ y4+y5+y6
#   结构模型：f2 ~ f1（f1对f2的因果效应）
# ============================================================

# ---- 安装并加载包 ----
install_packages('lavaan')  # SEM核心包
library(lavaan)              # 加载lavaan

# ---- 将 y1-y12/f1-f4 替换为你的变量名和因子名 ----

# 步骤1：指定SEM模型
sem_model <- '
  # 测量模型（=~定义潜变量）
  f1 =~ y1 + y2 + y3        # 因子f1由y1,y2,y3测量
  f2 =~ y4 + y5 + y6        # 因子f2由y4,y5,y6测量
  f3 =~ y7 + y8 + y9        # 因子f3由y7,y8,y9测量
  f4 =~ y10 + y11 + y12     # 因子f4由y10,y11,y12测量

  # 结构模型（~定义因果路径）
  f3 ~ f1 + f2              # f1和f2预测f3
  f4 ~ f3 + f2              # f3和f2预测f4
'

# 步骤2：拟合SEM模型
sem_fit <- sem(sem_model, data=mydata)
summary(sem_fit, fit.measures=TRUE, standardized=TRUE)
# 拟合指标：CFI/TLI>0.90, RMSEA<0.08, SRMR<0.08
# 路径系数：std.all列（标准化系数，可比较大小）

# 步骤3：路径图可视化
install_packages('semPlot')
library(semPlot)
semPaths(sem_fit, whatLabels='std', layout='tree')  # 标准化系数路径图
```

**结果解读**：测量模型部分：因子载荷>0.5且z值>1.96表示题目有效测量因子。结构模型部分：路径系数显著(p<0.05)表示因果关系成立。拟合指标：CFI/TLI>0.90，RMSEA<0.08，SRMR<0.08。若拟合不达标，可参考修正指数(modindices())释放高MI路径。

```r
# ---- 将 y1-y3/x1-x3 替换为你的变量名 ----
library(lavaan)
# 步骤1：指定路径模型
path_model <- '
  y1 ~ x1 + x2          # x1和x2预测y1
  y2 ~ y1 + x3          # y1和x3预测y2
  y3 ~ y2 + x1          # y2和x1预测y3
  y1 ~~ y3              # y1和y3的残差相关
'
# 步骤2：拟合路径模型
path_fit <- sem(path_model, data=mydata)
summary(path_fit, fit.measures=TRUE, standardized=TRUE)
# 解读：标准化路径系数(Std.all)用于比较路径大小，p<0.05表示路径显著
```

**结果解读**：summary() 输出各路径系数(Estimate)、标准误、z 值和 p 值。标准化路径系数(Std.all)用于比较路径大小，p<0.05 表示该路径显著。fit.measures 中的 CFI/TLI>0.90、RMSEA<0.08 表示模型拟合良好。

### 7.2 中介效应分析

**方法论说明**：检验自变量X是否通过中介变量M影响因变量Y。间接效应=a*b，置信区间不含0则中介效应成立。OBHRM 中最核心的机制检验方法，如领导力(X)→心理授权(M)→工作绩效(Y)。

**使用条件**：自变量、中介变量和因变量均为连续变量；建议使用Bootstrap法检验。

**核心R包**：mediation

```r
# ---- 将 treat/job_seek/depress2 替换为你的自变量/中介变量/因变量 ----
install_packages('mediation')  # 安装（仅需运行一次）
library(mediation)
# a路径：X->M
model_m <- lm(job_seek ~ sex + age + econ_hard + treat, data=jobs)
# b和c'路径：X+M->Y
model_y <- lm(depress2 ~ sex + age + econ_hard + treat + job_seek, data=jobs)
# Bootstrap中介效应检验
med_result <- mediate(model_m, model_y, sims=1000, treat='treat', mediator='job_seek')
summary(med_result)  # ACME=间接效应，ADE=直接效应，Total=总效应
```

#### 7.2.1 并行多重中介

**方法论说明**：当X通过两条或多条独立路径同时影响Y时使用。例如：领导力(X)通过工作投入(M1)和工作满意(M2)两条平行路径影响绩效(Y)。与链式中介不同，并行模型中M1和M2之间没有先后关系，是并列的。核心问题：哪条中介路径显著？哪条贡献更大？

**使用条件**：自变量X、两个或以上中介变量(M1, M2, ...)、一个因变量Y均为连续变量；M1与M2之间无先后因果顺序；建议Bootstrap检验。

**核心R包**：lavaan

```r
# ---- 将 x/m1/m2/y 替换为你的变量名，mydata 替换为你的数据框名 ----
# ---- 模型结构：X 同时通过 M1 和 M2 两条路径到达 Y ----
#
#         +--> M1 --> Y
#         |     a1     b1
#    X ---+
#         |     a2     b2
#         +--> M2 --> Y
#
# 间接效应1 = a1 * b1 (X->M1->Y)
# 间接效应2 = a2 * b2 (X->M2->Y)
# 总间接效应 = 间接效应1 + 间接效应2
# 直接效应 = c' (X->Y控制M1和M2后)
# ----
install_packages('lavaan')  # 安装（仅需运行一次）
library(lavaan)

# >>> 第1步：定义模型 <<<
# 用 lavaan 标签语法给每条路径命名，方便后面计算间接效应
model <- '
  # === a路径：X -> M1 和 X -> M2 ===
  m1 ~ a1 * x    # a1: X对M1的效应（如领导力->工作投入）
  m2 ~ a2 * x    # a2: X对M2的效应（如领导力->工作满意）

  # === b路径：M1 -> Y 和 M2 -> Y（同时放入，控制彼此）===
  y  ~ b1 * m1    # b1: M1对Y的效应（控制M2后）
  y  ~ b2 * m2    # b2: M2对Y的效应（控制M1后）

  # === c-prime路径：X -> Y（直接效应，控制M1和M2后）===
  y  ~ cp * x     # cp: X对Y的直接效应

  # === M1与M2的协方差（允许两个中介变量相关）===
  m1 ~~ m2        # M1和M2之间的残差相关

  # === 定义间接效应 ===
  ind1 := a1 * b1               # 路径1的间接效应：X->M1->Y
  ind2 := a2 * b2               # 路径2的间接效应：X->M2->Y
  ind_total := ind1 + ind2       # 总间接效应
  contrast := ind1 - ind2       # 两条路径的差异检验
'

# >>> 第2步：拟合模型，使用Bootstrap检验间接效应 <<<
fit <- sem(model, data=mydata, se='boot', bootstrap=5000)
# se='boot': 用Bootstrap法计算标准误（比正态假设更准确）
# bootstrap=5000: 重抽样5000次

# >>> 第3步：查看结果 <<<
summary(fit, fit.measures=TRUE, standardized=TRUE, ci=TRUE)
# 关注以下参数的95% Bootstrap CI（ci=TRUE输出）：
#   a1: X对M1的效应是否显著
#   a2: X对M2的效应是否显著
#   b1: M1对Y的效应是否显著（控制M2后）
#   b2: M2对Y的效应是否显著（控制M1后）
#   cp: 直接效应是否显著
#   ind1: 路径1间接效应的CI是否含0（不含0=显著）
#   ind2: 路径2间接效应的CI是否含0
#   contrast: 两条路径差异是否显著（CI不含0=两条路径有显著差异）
#   ind_total: 总间接效应是否显著
```

**结果解读**：ind1的Bootstrap 95%CI不含0：路径1(X->M1->Y)中介效应显著。ind2的CI不含0：路径2(X->M2->Y)显著。对比ind1和ind2的大小判断哪条路径贡献更大。contrast的CI不含0：
两条路径的差异统计显著（如ind1>ind2说明M1的中介作用强于M2）。cp不显著：完全中介（X对Y的影响完全通过M1和M2传递）。ind_total的CI不含0：整体中介效应成立。模型拟合：CFI/TLI>0.90, RMSEA<0.08。

#### 7.2.2 链式/序列中介

**方法论说明**：当中介变量存在先后顺序时使用。例如：领导力(X)先影响工作投入(M1)，工作投入再影响组织认同(M2)，最终影响绩效(Y)。核心路径：X->M1->M2->Y的间接效应=a1*d21*b2。与并行中介不同，链式模型中M1和M2有明确的先后关系。

**使用条件**：自变量X、中介M1和M2、因变量Y均为连续变量；M1理论上先于M2发生；建议Bootstrap检验；样本量>200。

**核心R包**：lavaan

```r
# ---- 将 x/m1/m2/y 替换为你的变量名，mydata 替换为你的数据框名 ----
# ---- 模型结构：X -> M1 -> M2 -> Y（链式传递）----
#
#    X --a1--> M1 --d21--> M2 --b2--> Y
#     \                          /
#      \--a2--> M2 -----b2----/
#       \                       /
#        \------cp------------>Y
#
# 三种间接效应：
#   链式间接效应 = a1 * d21 * b2  (X->M1->M2->Y，三级链)
#   路径1间接效应 = a1 * b1       (X->M1->Y，跳过M2)
#   路径2间接效应 = a2 * b2       (X->M2->Y，跳过M1)
# ----
install_packages('lavaan')
library(lavaan)

# >>> 第1步：定义链式中介模型 <<<
model <- '
  # === 第一阶段：X -> M1 ===
  m1 ~ a1 * x    # a1: X对M1的效应

  # === 第二阶段：X和M1 -> M2 ===
  m2 ~ a2 * x     # a2: X对M2的直接效应
  m2 ~ d21 * m1   # d21: M1对M2的效应（链式关键路径）

  # === 第三阶段：M1和M2 -> Y ===
  y  ~ b1 * m1    # b1: M1对Y的效应（控制M2后）
  y  ~ b2 * m2    # b2: M2对Y的效应（控制M1后）

  # === 直接效应 ===
  y  ~ cp * x     # cp: X->Y的直接效应

  # === 定义间接效应 ===
  # 链式间接效应：X->M1->M2->Y（三级传递）
  ind_serial := a1 * d21 * b2
  # 路径1间接效应：X->M1->Y（跳过M2）
  ind_m1 := a1 * b1
  # 路径2间接效应：X->M2->Y（跳过M1）
  ind_m2 := a2 * b2
  # 总间接效应
  ind_total := ind_serial + ind_m1 + ind_m2
'

# >>> 第2步：Bootstrap检验 <<<
fit <- sem(model, data=mydata, se='boot', bootstrap=5000)

# >>> 第3步：查看结果 <<<
summary(fit, fit.measures=TRUE, standardized=TRUE, ci=TRUE)
# 关注 ind_serial 的Bootstrap 95%CI：
#   CI不含0 = 链式中介效应显著（X->M1->M2->Y传递成立）
#   CI含0 = 链式路径不成立
```

**结果解读**：ind_serial的Bootstrap 95%CI不含0：链式中介效应(X->M1->M2->Y)成立，即X先通过M1影响M2，再通过M2影响Y。ind_m1显著但ind_serial不显著：M1的中介作用不通过M2传递，仅直接到达Y。
ind_m2显著：X也可直接通过M2影响Y（不经过M1）。d21的系数显著：M1对M2有显著预测作用（链式传递的前提）。对比ind_serial和ind_m1/ind_m2的大小判断链式路径是否是主要中介机制。

#### 7.2.3 多重结果中介

**方法论说明**：当一个中介变量M同时传递X对多个因变量Y1和Y2的影响时使用。例如：领导力(X)通过心理授权(M)同时影响工作绩效(Y1)和创新行为(Y2)。核心问题：X通过M对不同结果的影响有多大？各路径是否有差异？

**使用条件**：自变量X、一个中介变量M、两个或以上因变量(Y1, Y2, ...)均为连续变量；建议Bootstrap检验。

**核心R包**：lavaan

```r
# ---- 将 x/m/y1/y2 替换为你的变量名，mydata 替换为你的数据框名 ----
# ---- 模型结构：X 通过 M 同时影响 Y1 和 Y2 ----
#
#              +--> Y1
#         |    b1
#    X --> M --+
#         |   b2
#              +--> Y2
#
# 间接效应1 = a * b1  (X->M->Y1)
# 间接效应2 = a * b2  (X->M->Y2)
# ----
install_packages('lavaan')
library(lavaan)

# >>> 第1步：定义多重结果中介模型 <<<
model <- '
  # === a路径：X -> M ===
  m  ~ a * x       # a: X对M的效应（共用）

  # === b路径：M -> Y1 和 M -> Y2 ===
  y1 ~ b1 * m      # b1: M对Y1的效应（如授权->绩效）
  y2 ~ b2 * m      # b2: M对Y2的效应（如授权->创新）

  # === c-prime路径：X -> Y1 和 X -> Y2（直接效应）===
  y1 ~ cp1 * x     # cp1: X对Y1的直接效应（控制M后）
  y2 ~ cp2 * x     # cp2: X对Y2的直接效应（控制M后）

  # === Y1与Y2的残差协方差 ===
  y1 ~~ y2         # 允许两个因变量的残差相关

  # === 定义间接效应 ===
  ind_y1 := a * b1              # X->M->Y1的间接效应
  ind_y2 := a * b2              # X->M->Y2的间接效应
  contrast := ind_y1 - ind_y2   # 两条路径的差异检验
'

# >>> 第2步：Bootstrap检验 <<<
fit <- sem(model, data=mydata, se='boot', bootstrap=5000)

# >>> 第3步：查看结果 <<<
summary(fit, fit.measures=TRUE, standardized=TRUE, ci=TRUE)
# ind_y1的CI不含0：X通过M影响Y1的中介效应显著
# ind_y2的CI不含0：X通过M影响Y2的中介效应显著
# contrast的CI不含0：X对Y1和Y2的中介效应有显著差异
```

**结果解读**：ind_y1的Bootstrap 95%CI不含0：中介效应在Y1上成立（X->M->Y1）。ind_y2的CI不含0：中介效应在Y2上成立。contrast的CI不含0：
两条路径差异显著（如ind_y1>ind_y2说明M对Y1的中介作用强于对Y2）。a是共用路径（X->M），b1和b2的差异决定了M对不同结果变量的传递效率。y1~~y2允许两个因变量的残差相关，避免因忽略共同变异导致估计偏差。

#### 7.2.4 中介效应量与敏感性分析

**方法论说明**：中介分析除报告间接效应是否显著外，还应报告效应量（effect size）和结果稳健性。(1) 效应量：完全标准化间接效应（completely standardized indirect effect）表示 X 每变化一个标准差，
通过 M 传递到 Y 的间接效应有多少个标准差，是中介效应的标准化度量；(2) 敏感性分析：检验中介结果对"未测量混杂变量"的稳健性——即若存在一个被忽略的混杂变量，中介效应是否会被推翻。后者是近年 OBHRM 审稿对因果推断稳健性的常见要求。

**使用条件**：已完成中介效应检验；敏感性分析需基于 mediation 包的中介模型。

**核心R包**：lavaan、mediation

```r
# ---- 将 mydata 替换为数据框名，X/M/Y 替换为自变量/中介变量/因变量 ----
install_packages('lavaan')      # 安装（仅需运行一次）
install_packages('mediation')   # 安装（仅需运行一次）
library(lavaan)
library(mediation)

# >>> 步骤1：完全标准化间接效应（效应量）<<<
model <- '
  M ~ a*X
  Y ~ b*M + c*X
  indirect := a*b          # 间接效应
  total := c + a*b         # 总效应
'
fit <- sem(model, data=mydata)
summary(fit, standardized=TRUE)
# 查看 indirect 行的 std.all 列 = 完全标准化间接效应
# 判断标准（参照 Cohen）：|std.all| > 0.01 小，> 0.09 中等，> 0.25 大

# >>> 步骤2：敏感性分析（mediation::medsens）<<<
# 先拟合 mediation 包的中介模型
fit_m <- lm(M ~ X, data=mydata)
fit_y <- lm(Y ~ M + X, data=mydata)
med <- mediate(fit_m, fit_y, treat='X', mediator='M', sims=1000, boot=TRUE)

# 敏感性分析：检验未测量混杂（unmeasured confounding）的影响
sens <- medsens(med, rho.by=0.1, sims=1000)
summary(sens)
# 关键指标：
#   rho：假设的"混杂与中介/结果"的相关系数（从 -1 到 1 扫描）
#   R2tilde.thresh：使中介效应恰好变为 0 所需的未测量混杂解释力阈值
#   R2star.thresh：使中介效应显著性改变的阈值
# 判断：若阈值远大于实际可能存在的混杂解释力，则中介结果稳健
```

**结果解读**：完全标准化间接效应给出中介效应的大小，便于跨研究比较。敏感性分析中，若 R2tilde.thresh（使间接效应变为 0 所需的未测量混杂解释力）较大（如 > 0.30），说明即使存在一定程度的未测量混杂，中介效应仍稳健；若阈值很小（如 < 0.05），说明中介结果对混杂敏感，结论需谨慎。敏感性分析是近年 OBHRM 期刊审稿中越来越常见的要求。

#### 7.2.5 多自变量中介

**方法论说明**：多个自变量（X1, X2, ...）通过同一个中介变量 M 影响因变量 Y，用于检验多个前因是否通过共同机制发挥作用。OBHRM 中如：辱虐管理(X1)与组织支持(X2)通过工作不安全感(M)共同影响离职倾向(Y)。核心是估计每个 X 的特定间接效应（Xk→M→Y），并比较各前因的间接效应相对大小。

**使用条件**：多个连续自变量、一个中介变量、一个连续因变量；自变量间不宜高度共线；建议 Bootstrap 检验。

**核心R包**：lavaan

```r
# ---- 将 x1/x2/m/y 替换为变量名，mydata 替换为数据框名 ----
library(lavaan)
multi_x_model <- '
  # a路径：多个X预测中介M
  M ~ a1*x1 + a2*x2
  # b和c-prime路径：M和多个X预测Y
  Y ~ b*M + c1*x1 + c2*x2
  # 各X的特定间接效应
  ind_x1 := a1 * b     # X1 通过 M 的间接效应
  ind_x2 := a2 * b     # X2 通过 M 的间接效应
  # 间接效应差异（比较哪个前因的机制更强）
  ind_diff := ind_x1 - ind_x2
'
fit <- sem(multi_x_model, data=mydata, se='boot', bootstrap=5000)
summary(fit, standardized=TRUE, ci=TRUE)
```

**结果解读**：ind_x1 和 ind_x2 分别是 X1、X2 的特定间接效应，其 Bootstrap 置信区间不含 0 表示该前因的中介成立。ind_diff 检验两个前因的间接效应是否显著不同，用于判断"哪个前因的机制更强"。注意：多自变量中介要求各 X 的间接效应可分离，若 X1 与 X2 高度相关，特定间接效应可能不稳定。

### 7.3 调节效应分析

**方法论说明**：检验调节变量Z是否影响X与Y的关系。通过检验交互项(X*Z)是否显著实现。建议先中心化。OBHRM 中用于检验边界条件，如主动性人格(Z)调节工作压力(X)与职业倦怠(Y)的关系。

**核心R包**：car、pequod

**使用条件**：自变量与调节变量为连续或分类变量；建议先中心化以减少多重共线性。

```r
# ============================================================
# 调节效应分析 — car + pequod包
# ============================================================
# 检验调节变量Z是否影响X与Y的关系
# 通过检验交互项(X*Z)是否显著实现
# 建议先中心化以减少多重共线性
#
# 模型：Y = b0 + b1*X + b2*Z + b3*(X*Z) + e
# b3显著 -> 存在调节效应
# ============================================================

# ---- 安装并加载包 ----
install_packages('car')      # 回归诊断包
install_packages('pequod')   # 调节效应分析包
install_packages('effects')  # 安装（仅需运行一次）
library(car)                  # 加载car
library(pequod)               # 加载pequod

# ---- 将 adjdep/adjsimp/adjfatal 替换为因变量/自变量/调节变量 ----

# 步骤1：拟合调节效应模型（含交互项）
# * 表示同时包含主效应和交互效应
mod_model <- lm(adjdep ~ adjsimp * adjfatal, data=Ginzberg)
summary(mod_model)  # 查看交互项adjsimp:adjfatal的系数和p值

# 步骤2：简单斜率分析（交互效应显著时）
# 在调节变量高/低水平下检验X对Y的效应
simp_slopes <- lmSlopes(mod_model, pred='adjsimp', mod='adjfatal')
summary(simp_slopes)

# 步骤3：交互效应可视化
library(effects)
eff <- effect('adjsimp * adjfatal', mod_model)
plot(eff)  # 绘制调节效应图（高/低调节变量下的回归线）

# 步骤4：多重调节（三重交互，多个调节变量）
# 检验 X 的效应是否同时受两个调节变量 Z1、Z2 影响
mydata$XZ1 <- mydata$X * mydata$Z1
mydata$XZ2 <- mydata$X * mydata$Z2
mydata$Z1Z2 <- mydata$Z1 * mydata$Z2
mydata$XZ1Z2 <- mydata$X * mydata$Z1 * mydata$Z2
triple_model <- lm(Y ~ X + Z1 + Z2 + XZ1 + XZ2 + Z1Z2 + XZ1Z2, data=mydata)
summary(triple_model)
# 三重交互项 XZ1Z2 显著：X 的调节效应随另一个调节变量的水平变化
# （即调节的调节，需进一步做条件交互的简单斜率分析）
```

**结果解读**：交互项（X×Z）系数显著说明调节效应存在。简单斜率分析（emmeans）展示不同 Z 水平（如 ±1 SD）下 X 对 Y 的效应，若高低水平的简单斜率差异显著则调节成立。

### 7.4 有调节的中介

**方法论说明**：有调节的中介（Moderated Mediation）指中介过程（间接效应 a×b）受到调节变量 Z 的影响。Edwards & Lambert (2007) 按"调节发生的位置"将之分为五类：①第一阶段调节（Z 调节 X→M）；
②第二阶段调节（Z 调节 M→Y）；③两阶段调节（Z 同时调节 X→M 和 M→Y）；④直接效应调节（Z 调节 X→Y）；⑤总效应调节。OBHRM 中最常见的是第一阶段和第二阶段调节。检验时需报告不同 Z 水平下的条件间接效应。

**使用条件**：包含自变量、中介变量、因变量和调节变量；建议用 Bootstrap 检验条件间接效应的置信区间。

**核心R包**：lavaan

```r
# ---- 将 X/Z/M/Y 替换为自变量/调节变量/中介变量/因变量 ----
install_packages('lavaan')
library(lavaan)
# 中心化 X 和 Z（减少共线性，便于解释交互项）
mydata$Xc <- scale(mydata$X, scale=FALSE)
mydata$Zc <- scale(mydata$Z, scale=FALSE)
mydata$XZ <- mydata$Xc * mydata$Zc

# ============ 类型1：第一阶段调节（Z 调节 X→M，Hayes Model 7）============
m1 <- '
  M ~ a1*Xc + a2*Zc + a3*XZ     # a 路径含调节
  Y ~ b*M + c*Xc + d*Zc          # b 路径 + 直接效应
  # 条件间接效应：在 Z 高低水平下的 (a1 + a3*Z) * b
  ind_low  := (a1 + a3*(-1)) * b    # Z = -1 SD
  ind_high := (a1 + a3*( 1)) * b    # Z = +1 SD
  ind_diff := ind_high - ind_low    # 高低水平的间接效应差
'
fit1 <- sem(m1, data=mydata, se='boot', bootstrap=5000)
summary(fit1, standardized=TRUE, ci=TRUE)
# 解读：ind_diff 的 CI 不含 0 → 第一阶段有调节的中介成立

# ============ 类型2：第二阶段调节（Z 调节 M→Y，Hayes Model 14）============
m2 <- '
  M ~ a1*Xc
  Y ~ b1*M + b2*Zc + b3*M:Zc + c*Xc   # b 路径含调节
  # 条件间接效应：a * (b1 + b3*Z)
  ind_low  := a1 * (b1 + b3*(-1))
  ind_high := a1 * (b1 + b3*( 1))
  ind_diff := ind_high - ind_low
'
fit2 <- sem(m2, data=mydata, se='boot', bootstrap=5000)
summary(fit2, standardized=TRUE, ci=TRUE)

# ============ 类型3：两阶段调节（Z 同时调节 X→M 和 M→Y）============
m3 <- '
  M ~ a1*Xc + a2*Zc + a3*XZ
  Y ~ b1*M + b2*Zc + b3*M:Zc + c*Xc
  ind_low  := (a1 + a3*(-1)) * (b1 + b3*(-1))
  ind_high := (a1 + a3*( 1)) * (b1 + b3*( 1))
  ind_diff := ind_high - ind_low
'
fit3 <- sem(m3, data=mydata, se='boot', bootstrap=5000)
summary(fit3, standardized=TRUE, ci=TRUE)

# ============ 类型4：直接效应调节（Z 调节 X→Y 直接路径）============
m4 <- '
  M ~ a1*Xc
  Y ~ b*M + c1*Xc + c2*Zc + c3*XZ   # 直接效应含调节
  ind := a1 * b                        # 间接效应（不受 Z 调节）
'
fit4 <- sem(m4, data=mydata, se='boot', bootstrap=5000)
summary(fit4, standardized=TRUE, ci=TRUE)
```

**结果解读**：五类有调节的中介中，前四类较常用（第五类"总效应调节"较少单独检验）。核心判断标准：**条件间接效应的差异（ind_diff）的 Bootstrap 置信区间不含 0**，即说明间接效应随 Z 显著变化，有调节的中介成立。注意区分：
类型1 检验 a 路径的调节（a3 显著），说明"Z 影响 X 对 M 的作用"；类型2 检验 b 路径的调节（b3 显著），说明"Z 影响 M 对 Y 的作用"。两者含义不同，实际研究需先有理论依据判断调节发生在哪个阶段，再选择对应模型。

### 7.5 有中介的调节

**方法论说明**：有中介的调节（Mediated Moderation）指交互效应(X*Z)通过中介变量M传递。与"有调节的中介"关注点不同——有调节的中介关注"间接效应是否随Z变化"，有中介的调节关注"交互效应是否通过M传递"。统计上检验：
(1)X*Z对M有显著效应(a3)；(2)M对Y有显著效应(cp)；(3)X*Z对Y的直接效应(b3)在纳入M后减弱。OBHRM 典型例子：领导-成员交换(X)与角色清晰度(Z)的交互效应通过工作投入(M)传递到工作绩效(Y)。

**使用条件**：包含自变量、调节变量、中介变量和因变量。

**核心R包**：lavaan

```r
# ---- 将 y/m/x/z 替换为因变量/中介变量/自变量/调节变量，mydata替换为数据框名 ----
install_packages('lavaan')  # 安装（仅需运行一次）
library(lavaan)
mydata$x_c <- scale(mydata$x, scale=FALSE)
mydata$z_c <- scale(mydata$z, scale=FALSE)
mydata$xz <- mydata$x_c * mydata$z_c
model <- '
  # a路径：交互项对中介变量的效应
  m ~ a1 * x_c + a2 * z_c + a3 * xz
  # b和c-prime路径：中介变量和交互项对因变量的效应
  y ~ b1 * x_c + b2 * z_c + b3 * xz + cp * m
  # 效应分解
  indirect := a3 * cp       # 间接效应 = 交互项对M的效应 * M对Y的效应
  direct := b3              # 直接效应 = 交互项对Y的直接效应（控制M后）
  total := indirect + direct
'
fit <- sem(model, data=mydata, se='boot', bootstrap=1000)
summary(fit, fit.measures=TRUE, standardized=TRUE, ci=TRUE)
# a3显著: 交互项对M有影响；indirect显著: 交互效应通过M传递
# direct不显著或减弱: 完全或部分有中介的调节
```
**结果解读**：关注调节效应是否通过中介传递。若 X×Z 对 M 的路径显著且 M 对 Y 的路径显著，则调节效应被分解为直接调节与间接调节；间接调节（通过 M）的置信区间不含 0 即有中介的调节成立。

### 7.6 多层验证性因素分析（MCFA）

**方法论说明**：用于嵌套数据的测量模型检验。将因子结构分解为组内（Level-1: within）和组间（Level-2: between），分别检验因子结构在个体层和组织层的适配性。

**使用条件**：数据具有嵌套结构；ICC>0.10。

**核心R包**：lavaan

```r
# ============================================================
# 多层验证性因素分析（MCFA） — lavaan包
# ============================================================
# 在嵌套数据中检验因子结构
# 区分组内（within）和组间（between）的因子结构
# ============================================================

# ---- 安装并加载包 ----
install_packages('lavaan')  # SEM核心包
library(lavaan)              # 加载lavaan

# ---- 将 y1-y6/group_id 替换为变量名 ----

# 步骤1：指定双层CFA模型
# level: 1 = 组内结构（个体差异）
# level: 2 = 组间结构（组间差异）
mcfa_model <- '
  level: 1
    fw1 =~ y1 + y2 + y3     # 组内因子1
    fw2 =~ y4 + y5 + y6     # 组内因子2
  level: 2
    fb1 =~ y1 + y2 + y3     # 组间因子1
    fb2 =~ y4 + y5 + y6     # 组间因子2
'

# 步骤2：拟合MCFA模型
mcfa_fit <- cfa(mcfa_model, data=mydata,
                cluster='group_id')  # 指定聚类变量
summary(mcfa_fit, fit.measures=TRUE, standardized=TRUE)
# 解读：组内因子结构和组间因子结构可以不同
# 比较与普通CFA的拟合差异
```
**结果解读**：关注组内（within）与组间（between）两层的因子结构与拟合指标（CFI/TLI/RMSEA）。ICC 反映各题目组间方差占比，若组间 ICC 过低，组间因子可能不成立。


**高阶篇**

## 第8章 组态分析

### 8.1 模糊集定性比较分析

**方法论说明**：fsQCA基于集合论和布尔代数，适用于中小样本（10-200案例）。核心思想：结果由多个条件的组合（组态）导致，而非单一变量的净效应。通过校准将原始数据转换为模糊集成员分数（0-1），构建真值表，分析必要性和充分性，最终得到解路径。QCA包支持清晰集、模糊集和多值集。

**使用条件**：样本量10-200；条件变量4-8个和1个结果变量；数据可校准为模糊集；理论驱动的条件选择。

**核心R包**：QCA

```r
# ---- 将 mydata 替换为数据框名，条件变量和结果变量替换为你的变量名 ----
install_packages('QCA')  # 安装（仅需运行一次）
library(QCA)

# >>> 步骤1：数据校准（Calibration）<<<
# 将原始变量转换为0-1的模糊集成员分数
# thresholds=c(完全不隶属, 交叉点, 完全隶属)
# ---- 将 cond1/cond2/cond3 替换为条件变量名，outcome 替换为结果变量名 ----
mydata$fA <- calibrate(mydata$cond1, thresholds=c(3, 5, 7))  # 校准条件A
mydata$fB <- calibrate(mydata$cond2, thresholds=c(2, 4, 6))  # 校准条件B
mydata$fC <- calibrate(mydata$cond3, thresholds=c(3, 5, 7))  # 校准条件C
mydata$fY <- calibrate(mydata$outcome, thresholds=c(3, 5, 7)) # 校准结果变量

# >>> 步骤2：必要性分析 <<<
# 一致性(inclusion) >= 0.9 表示该条件是必要条件
# 方法A：pof() 逐个检验单一条件的必要性（relation="necessity"）
pof(mydata$fY, mydata$fA, relation='necessity')  # 条件A是否为Y的必要条件
pof(mydata$fY, mydata$fB, relation='necessity')
pof(mydata$fY, mydata$fC, relation='necessity')
# 方法B：superSubset() 一次性检验多个条件及其组合的必要性
necessity_result <- superSubset(mydata, outcome='fY',
                                conditions=c('fA','fB','fC'), relation='necessity')
print(necessity_result)

# >>> 步骤3：构建真值表（Truth Table）<<<
tt <- truthTable(mydata, outcome='fY',
                conditions=c('fA','fB','fC'),
                freq.cut=1, consistency.cut=0.8, sort.by='cons')
print(tt)

# >>> 步骤4：布尔最小化 - 解路径 <<<
# 保守解（Conservative Solution）
sol_cons <- minimize(tt, include='rest')
print(sol_cons)
# 中间解（Intermediate Solution）- 需指定方向性期望
sol_inter <- minimize(tt, include='rest', dir.exp=c(1,1,1))
print(sol_inter)

# >>> 步骤5：可视化 <<<
# XYplot() 绘制条件组合与结果的 XY 散点图（充分性）
# x 为条件组合表达式（* 表示交集），y 为结果变量
XYplot('fA * fB', 'fY', data=mydata)  # 条件A与B的组合对Y的充分性
abline(a=0, b=1, col='red')  # 参考线y=x（点位于对角线上方表示该组合是Y的充分条件）

```

**结果解读**：必要性分析中一致性>=0.9的条件为必要条件。解路径中每条路径表示一个充分条件组合：总体一致性>=0.75表示解整体可靠；总体覆盖度表示解能解释的案例比例；原始覆盖度表示该路径单独解释的案例比例；唯一覆盖度表示该路径独有解释力。核心条件（在简约解和中间解中都出现）vs辅助条件（仅在中间解中出现）。

### 8.2 必要条件分析

**方法论说明**：NCA由Dul(2016)提出，用于识别结果变量的必要条件。与回归关注平均效应不同，NCA关注没有X就不能有Y的瓶颈约束。通过上限回归（CE回归）估计效应量d，d>0表示X对Y有瓶颈约束。NCA与fsQCA互补：fsQCA关注充分条件组合，NCA关注单一必要条件。

**使用条件**：自变量X和因变量Y均为连续或有序变量；关注瓶颈关系而非平均效应；样本量建议>30。

**核心R包**：NCA

```r
# ---- 将 mydata 替换为数据框名，x1 替换为自变量名，y 替换为因变量名 ----
install_packages('NCA')  # 安装（仅需运行一次）
library(NCA)

# >>> 单变量必要条件检验 <<<
# ---- 将 x1 替换为自变量名，y 替换为因变量名 ----
model_nca <- nca_analysis(mydata, x='x1', y='y')
print(model_nca)
summary(model_nca)
# 上限回归方法：CE-FDH(非参数,小样本), CR-FDH(参数化), CE-LP(大样本)

# >>> 多变量必要条件分析 <<<
model_multi <- nca_analysis(mydata, x=c('x1','x2','x3'), y='y', ceilings='ce_fdh')
print(model_multi)
# 效应量d：0<d<=0.1小, 0.1<d<=0.3中, 0.3<d<=0.5较大, d>0.5大

# >>> 瓶颈分析 <<<
# 用 nca_output() 的 bottlenecks 参数生成瓶颈表
nca_output(model_multi, bottlenecks=TRUE, plots=FALSE)
# 行=Y的不同水平(0%-100%), 列=各X的必要水平, NN=不构成瓶颈

# >>> 可视化 <<<
plot(model_nca)  # 散点图+CE上限回归线

# >>> 统计显著性检验（置换检验）<<<
# test.rep 指定置换检验次数（>0 时启用）
model_test <- nca_analysis(mydata, x='x1', y='y', test.rep=10000)
print(model_test)  # p<0.05显著

# >>> 效力分析 <<<
power_result <- nca_power(effect=0.1, n=c(50,100,200))
print(power_result)

```

**结果解读**：效应量d表示瓶颈约束大小。d>0表示X是Y的必要条件。瓶颈分析表显示Y每增加10%所需各X的最低水平。与回归的区别：回归关注平均影响(OLS线)，NCA关注上限约束(CE线)。与fsQCA互补：fsQCA一致性>=0.9确认必要条件后，NCA可量化瓶颈效应大小。


## 第9章 剖面分析

### 9.1 潜剖面分析

**方法论说明**：以人为中心的分析方法，基于连续变量将样本识别为若干质性不同的亚组（剖面）。LPA可进一步扩展：纳入协变量预测剖面归属（主效应）、检验剖面间的中介路径（中介效应）、检验调节变量对剖面归属的影响（调节效应）。OBHRM 典型应用：
基于大五人格识别人格剖面、基于情绪耗竭/去个性化/低成就感识别倦怠类型、基于三种承诺识别承诺剖面；识别出剖面后可进一步检验各剖面在离职、绩效、幸福感等结果上的差异。

**使用条件**：连续变量；样本量>各组变量数×10；各组正态分布。

**核心R包**：mclust、tidyLPA

#### 9.1.1 基础LPA
**方法论说明**：基于连续指标变量将样本识别为若干质性不同的亚组（剖面），是 person-centered 分析的基础。

**使用条件**：连续指标变量；样本量 > 300；建议先标准化变量。

**核心R包**：mclust、tidyLPA

```r
# ============================================================
# 基础LPA：基于连续变量识别质性不同的亚组（剖面）
# ============================================================
# ---- 安装并加载包 ----
install_packages('mclust')     # 潜剖面分析包
install_packages('tidyLPA')    # LPA辅助包
install_packages('psych')  # 安装（仅需运行一次）
library(mclust)                 # 加载mclust
library(tidyLPA)                # 加载tidyLPA

# ---- 将 mydata[,c('x1','x2','x3')] 替换为你的连续变量列 ----

# 步骤1：确定最佳剖面数（比较1-6个剖面的BIC）
lpa_fit <- Mclust(mydata[, c('x1','x2','x3')], G=1:6)
summary(lpa_fit)  # 输出最优模型参数和BIC

# 步骤2：可视化剖面分类结果
plot(lpa_fit, what='classification')  # 分类散点图

# 步骤3：提取剖面归属和描述
lpa_groups <- lpa_fit$classification  # 每个样本的剖面编号
table(lpa_groups)                       # 各剖面样本量

# 步骤4：各剖面特征描述
library(psych)
mydata$lpa_group <- lpa_groups
describeBy(mydata[, c('x1','x2','x3')], group=mydata$lpa_group)
# 各剖面在各变量上的均值 -> 描述剖面特征（如"高焦虑高回避组"）

```
**结果解读**：BIC/ABIC 越小、Entropy 越接近 1、BLRT p<0.05 表示分类质量好。各剖面的均值模式用于命名（如"高投入-高满意"剖面），各剖面的样本比例反映人群分布。

#### 9.1.2 LPA含协变量

```r
# ============================================================
# LPA含协变量：检验协变量对剖面归属的预测作用
# ============================================================
# ---- 将 cov1/cov2 替换为协变量名（如性别、年龄） ----

# 步骤1：用tidyLPA拟合含协变量的模型
# covariates参数指定预测剖面归属的变量
lpa_cov <- estimate_profiles(
  mydata[, c('x1','x2','x3')],
  n_profiles=3,               # 剖面数（基于7.1.1的结果）
  models=6,                   # 模型类型（6=方差自由估计）
  covariates=c('cov1','cov2') # 协变量预测剖面归属
)

# 步骤2：查看协变量对剖面归属的影响
summary(lpa_cov)
# 输出：协变量预测剖面归属的逻辑回归系数
# 系数显著 -> 该协变量影响属于某剖面的概率

# 步骤3：另一种方法 — 增长混合模型（GMM，纵向数据的潜类别）
# 先识别剖面，再分析协变量（避免分类不确定性影响）
# install_packages('lcmm')
# library(lcmm)
# hc_model <- hlme(x1 ~ time, subject='id', mixture=~1, data=mydata)

```
**结果解读**：协变量预测剖面归属的逻辑回归系数显著，说明该协变量影响个体属于某剖面的概率（如男性更可能属于"高投入剖面"）。

#### 9.1.3 LPA含远端结果

**方法论说明**：检验识别出的剖面是否预测远端结果变量（如工作满意度、绩效、离职意愿）。常用三步法：先识别剖面，再提取各样本的剖面归属，最后用归属作为预测变量分析远端结果。OBHRM 应用：识别"高投入-低投入"等剖面后，检验不同剖面是否预测不同的绩效或离职倾向。

**使用条件**：已通过 LPA 识别剖面；有远端结果变量（连续或分类）；注意三步法忽略分类不确定性，分类质量低（Entropy<0.7）时结论可能偏误。

**核心R包**：mclust、emmeans

```r
# ---- 将 x1-x5 替换为剖面指标变量，outcome 替换为远端结果 ----
library(mclust)
# 步骤1：识别剖面
lpam <- Mclust(mydata[, c('x1','x2','x3','x4','x5')], G=1:4)
mydata$profile <- lpam$classification  # 提取剖面归属
# 步骤2：剖面预测远端结果（ANOVA）
aov_out <- aov(outcome ~ factor(profile), data=mydata)
summary(aov_out)
# 步骤3：各剖面的远端结果均值与两两比较
library(emmeans)
em <- emmeans(aov_out, ~ profile)
pairs(em)
```

**结果解读**：ANOVA 的 F 值显著说明不同剖面的远端结果有差异；emmeans 事后比较展示哪些剖面间差异显著（如"高投入剖面"的绩效显著高于"低投入剖面"）。注意三步法将剖面归属视为确定值，忽略分类不确定性，建议报告 Entropy 并谨慎解释。

#### 9.1.4 LPA含中介效应

**方法论说明**：检验剖面是否通过中介变量 M 影响远端结果 Y。OBHRM 应用：不同承诺剖面通过心理授权(M)影响绩效(Y)。三步法：识别剖面 → 提取归属 → 用归属（虚拟变量）作为自变量做中介分析。

**使用条件**：已识别剖面；有中介变量和结果变量；注意分类不确定性可能低估间接效应。

**核心R包**：mclust、lavaan

```r
# ---- 将 x1-x5 替换为指标变量，m/y 替换为中介/结果变量 ----
library(mclust); library(lavaan)
lpam <- Mclust(mydata[, c('x1','x2','x3','x4','x5')], G=1:4)
mydata$profile <- lpam$classification  # 剖面归属
# 以剖面1为参照，构造虚拟变量
mydata$p2 <- ifelse(mydata$profile==2, 1, 0)
mydata$p3 <- ifelse(mydata$profile==3, 1, 0)
mydata$p4 <- ifelse(mydata$profile==4, 1, 0)
med_model <- '
  M ~ a1*p2 + a2*p3 + a3*p4
  Y ~ b*M + c1*p2 + c2*p3 + c3*p4
  ind_p2 := a1*b   # 剖面2（vs 剖面1）通过 M 的间接效应
  ind_p3 := a2*b
  ind_p4 := a3*b
'
fit <- sem(med_model, data=mydata, se='boot', bootstrap=5000)
summary(fit, standardized=TRUE, ci=TRUE)
```

**结果解读**：ind_p2/ind_p3/ind_p4 分别是各剖面（相对参照剖面）通过 M 的间接效应，Bootstrap CI 不含 0 表示该剖面通过 M 影响 Y 的机制成立。注意分类不确定性可能低估间接效应，建议报告 Entropy 并谨慎解释。

#### 9.1.5 LPA含调节效应

**方法论说明**：检验剖面与结果的关系是否受调节变量 Z 影响（剖面 × Z 交互）。OBHRM 应用：承诺剖面与离职倾向的关系是否受组织支持(Z)调节。

**使用条件**：已识别剖面；有调节变量和结果变量。

**核心R包**：mclust、car

```r
library(mclust); library(car)
lpam <- Mclust(mydata[, c('x1','x2','x3','x4','x5')], G=1:4)
mydata$profile <- lpam$classification
mod_model <- lm(y ~ factor(profile) * z, data=mydata)
summary(mod_model)  # 交互项显著 → 剖面与结果的关系受 Z 调节
Anova(mod_model, type=3)  # 类型III方差分析
```

**结果解读**：交互项显著说明剖面对结果的影响随 Z 变化，可进一步用 emmeans 做简单斜率分析，展示不同 Z 水平下各剖面的结果差异。

### 9.2 潜类别分析

**方法论说明**：以人为中心，基于分类变量将样本识别为若干质性不同的亚组（类别）。LCA可扩展为含协变量（预测类别归属）、中介效应（类别通过中介变量影响结果）和调节效应（类别与结果的关系受调节变量影响）。OBHRM 典型应用：基于分类应对策略（问题导向/情绪导向/回避）识别应对模式、基于多种离职原因识别离职类型、基于工作特征组合识别岗位类型。

**使用条件**：分类变量（二分或有序）；每类至少10-20个样本。

**核心R包**：poLCA

#### 9.2.1 基础LCA
**方法论说明**：基于分类指标变量将样本识别为若干潜在类别，是 person-centered 分析中处理类别数据的方法。

**使用条件**：分类指标变量（二分或有序）；每类至少 10-20 个样本。

**核心R包**：poLCA

```r
# ============================================================
# 基础LCA：基于分类变量识别质性不同的亚组
# ============================================================
install_packages('poLCA')  # 潜类别分析包
library(poLCA)              # 加载poLCA

# ---- 将 mydata 替换为数据框名，i1-i4 替换为分类变量名 ----
# 步骤1：指定LCA模型公式
lca_formula <- cbind(i1, i2, i3, i4) ~ 1

# 步骤2：拟合不同类别数，比较BIC（选最小BIC）
for (k in 2:5) {
  set.seed(123)
  lca_model <- poLCA(lca_formula, data=mydata,
                     nclass=k, maxiter=1000, nrep=10)
  cat(sprintf('Classes=%d, BIC=%.1f\n', k, lca_model$bic))
}

# 步骤3：拟合最优模型
set.seed(123)
lca_final <- poLCA(lca_formula, data=mydata, nclass=3, nrep=10)
lca_classes <- lca_final$predclass  # 每个样本的类别编号
table(lca_classes)                    # 各类别样本量
# 各类别在各题目上的条件概率 -> 描述类别特征

```
**结果解读**：类别概率矩阵展示每个类别在各题目选项上的响应概率，据此命名类别（如"高认可型""低认可型"）。BIC/Entropy/BLRT 用于判断类别数与分类质量。

#### 9.2.2 LCA含协变量

```r
# ============================================================
# LCA含协变量：检验协变量对类别归属的预测作用
# ============================================================
# ---- 将 cov1/cov2 替换为协变量名 ----

# 步骤1：在公式中加入协变量
# cbind(i1, i2, i3, i4) ~ cov1 + cov2
# 协变量预测类别归属（多项逻辑回归）
lca_cov_formula <- cbind(i1, i2, i3, i4) ~ cov1 + cov2
set.seed(123)
lca_cov <- poLCA(lca_cov_formula, data=mydata, nclass=3, nrep=10)

# 步骤2：查看协变量系数
summary(lca_cov)
# 系数显著 -> 该协变量影响属于某类别的概率
# 正系数 -> covariate增加时更可能属于该类别

```
**结果解读**：协变量预测类别归属的系数显著，说明该协变量影响个体属于某类别的概率。

#### 9.2.3 LCA含远端结果

**方法论说明**：检验识别出的潜在类别是否预测远端结果变量。三步法：先用 poLCA 识别类别，提取归属，再用归属预测远端结果。OBHRM 应用：识别不同离职原因类型后，检验各类型是否预测不同的离职时间或离职后去向。

**使用条件**：已通过 LCA 识别类别；有远端结果变量；注意分类不确定性。

**核心R包**：poLCA、emmeans

```r
# ---- 将 x1-x5 替换为分类指标变量，outcome 替换为远端结果 ----
library(poLCA)
f <- cbind(x1, x2, x3, x4, x5) ~ 1
lca_model <- poLCA(f, data=mydata, nclass=3, nrep=10)
mydata$class <- lca_model$predclass  # 提取类别归属
aov_out <- aov(outcome ~ factor(class), data=mydata)
summary(aov_out)
library(emmeans)
em <- emmeans(aov_out, ~ class)
pairs(em)
```

**结果解读**：ANOVA F 值显著说明不同类别的远端结果有差异；emmeans 事后比较展示哪些类别间差异显著。注意三步法忽略分类不确定性，建议报告分类质量并谨慎解释。

#### 9.2.4 LCA含中介效应

**方法论说明**：检验潜在类别是否通过中介变量 M 影响远端结果 Y。三步法：识别类别 → 提取归属 → 用类别（虚拟变量）做中介分析。

**使用条件**：已识别类别；有中介变量和结果变量；注意分类不确定性。

**核心R包**：poLCA、lavaan

```r
library(poLCA); library(lavaan)
f <- cbind(x1, x2, x3, x4, x5) ~ 1
lca_model <- poLCA(f, data=mydata, nclass=3, nrep=10)
mydata$class <- lca_model$predclass
# 以类别1为参照，构造虚拟变量
mydata$c2 <- ifelse(mydata$class==2, 1, 0)
mydata$c3 <- ifelse(mydata$class==3, 1, 0)
med_model <- '
  M ~ a1*c2 + a2*c3
  Y ~ b*M + c1*c2 + c2*c3
  ind_c2 := a1*b   # 类别2（vs 类别1）通过 M 的间接效应
  ind_c3 := a2*b
'
fit <- sem(med_model, data=mydata, se='boot', bootstrap=5000)
summary(fit, standardized=TRUE, ci=TRUE)
```

**结果解读**：ind_c2/ind_c3 是各类别（相对参照类别）通过 M 的间接效应，CI 不含 0 表示该类别通过 M 影响 Y 的机制成立。

#### 9.2.5 LCA含调节效应

**方法论说明**：检验类别与结果的关系是否受调节变量 Z 影响（类别 × Z 交互）。

**使用条件**：已识别类别；有调节变量和结果变量。

**核心R包**：poLCA、car

```r
library(poLCA); library(car)
f <- cbind(x1, x2, x3, x4, x5) ~ 1
lca_model <- poLCA(f, data=mydata, nclass=3, nrep=10)
mydata$class <- lca_model$predclass
mod_model <- lm(y ~ factor(class) * z, data=mydata)
summary(mod_model)  # 交互项显著 → 类别与结果的关系受 Z 调节
Anova(mod_model, type=3)
```

**结果解读**：交互项显著说明类别对结果的影响随 Z 变化，可进一步用 emmeans 做简单斜率分析。

### 9.3 潜增长模型

**方法论说明**：分析变量随时间的变化轨迹，识别不同增长模式。LGA可扩展为增长混合模型（GMM）：纳入协变量预测初始水平和变化速率、检验增长参数的中介效应、检验调节变量对增长轨迹的影响。OBHRM 典型应用：新员工组织社会化的适应轨迹、离职意愿随时间的增长轨迹、工作投入或倦怠的发展轨迹；识别出不同轨迹亚组后，可检验前因（如入职培训、领导支持）对不同轨迹的预测作用。

**使用条件**：至少3个时间点的纵向数据；样本量>200。

**核心R包**：lavaan、lcmm

#### 9.3.1 基础潜增长模型
**方法论说明**：分析变量随时间的变化轨迹，估计初始水平（截距 i）和变化速率（斜率 s），检验整体增长趋势。

**使用条件**：至少 3 个时间点的纵向数据；样本量 > 200。

**核心R包**：lavaan

```r
# 基础LGA：分析变量随时间的变化轨迹
# ============================================================
# 模型结构示意：
#   时间点:  t1    t2    t3    t4
#   i(截距): 1     1     1     1    ← 起点水平
#   s(斜率): 0     1     2     3    ← 变化速率
# ============================================================
install_packages('lavaan')  # SEM核心包
library(lavaan)              # 加载lavaan

# ---- 将 t1-t4 替换为你的时间点变量名 ----
# 步骤1：指定潜增长模型
lgm_model <- '
  i =~ 1*t1 + 1*t2 + 1*t3 + 1*t4    # 截距因子（初始水平）
  s =~ 0*t1 + 1*t2 + 2*t3 + 3*t4    # 斜率因子（变化速率）
'

# 步骤2：拟合模型
lgm_fit <- growth(lgm_model, data=mydata)
summary(lgm_fit, fit.measures=TRUE, standardized=TRUE)
# i的均值=整体初始水平；s的均值=变化速率（正=增长，负=下降）
# i和s的方差=个体差异；i~~s协方差=初始水平与变化速率的关系

```
**结果解读**：i 的均值表示整体初始水平，s 的均值表示变化速率（正=增长，负=下降）。s 均值显著说明存在整体增长/下降趋势。

#### 9.3.2 LGA含协变量
**方法论说明**：纳入协变量（如性别、人格）预测增长参数（截距和斜率），检验谁的增长轨迹更高或变化更快。

**使用条件**：至少 3 个时间点；有基线协变量。

**核心R包**：lavaan

```r
# ============================================================
# LGA含协变量：检验协变量对初始水平和变化速率的预测
# ============================================================
# ---- 将 x1/x2 替换为协变量名 ----

# 步骤1：指定含协变量的潜增长模型
lgm_cov_model <- '
  i =~ 1*t1 + 1*t2 + 1*t3 + 1*t4
  s =~ 0*t1 + 1*t2 + 2*t3 + 3*t4

  # 协变量预测初始水平和变化速率
  i ~ x1 + x2   # x1,x2预测起点水平
  s ~ x1 + x2   # x1,x2预测变化速率
'

# 步骤2：拟合模型
lgm_cov_fit <- growth(lgm_cov_model, data=mydata)
summary(lgm_cov_fit, fit.measures=TRUE)
# 解读：i~x1系数 -> x1对初始水平的影响
#       s~x1系数 -> x1对变化速率的影响

```
**结果解读**：协变量预测 i 和 s 的系数反映其对起点水平和变化速率的影响，显著说明该协变量影响增长轨迹。

#### 9.3.3 LGA含中介效应
**方法论说明**：检验自变量通过增长参数（截距/斜率）影响远端结果的纵向中介机制。

**使用条件**：至少 3 个时间点；有基线自变量和远端结果。

**核心R包**：lavaan

```r
# ============================================================
# LGA中介效应：协变量通过增长参数（i/s）影响结果变量
# ============================================================
# 模型结构：X → 增长参数(i/s) → Y(结果)
# 即：协变量影响增长轨迹，增长轨迹影响最终结果
# ============================================================
# ---- 将 x/m/y/t1-t4 替换为变量名 ----

# 步骤1：指定中介增长模型
lgm_med_model <- '
  i =~ 1*t1 + 1*t2 + 1*t3 + 1*t4
  s =~ 0*t1 + 1*t2 + 2*t3 + 3*t4

  # a路径：X → 增长参数
  i ~ a1 * x
  s ~ a2 * x

  # b路径：增长参数 → 结果
  y ~ b1 * i + b2 * s

  # 间接效应定义
  ind_i := a1 * b1   # 通过初始水平的中介
  ind_s := a2 * b2   # 通过变化速率的中介
'

# 步骤2：拟合模型（Bootstrap检验间接效应）
lgm_med_fit <- sem(lgm_med_model, data=mydata,
                   se='boot', bootstrap=5000)
summary(lgm_med_fit, fit.measures=TRUE)
# 查看ind_i和ind_s的Bootstrap置信区间
# CI不含0 -> 中介效应显著

```
**结果解读**：间接效应通过增长参数（i/s）传递，CI 不含 0 说明纵向中介成立。

#### 9.3.4 LGA含调节效应
**方法论说明**：检验调节变量对增长轨迹（截距/斜率）的影响，即增长轨迹是否随调节变量水平变化。

**使用条件**：至少 3 个时间点；有调节变量。

**核心R包**：lavaan

```r
# ============================================================
# LGA调节效应：调节变量影响协变量对增长轨迹的预测
# ============================================================
# 模型结构：X*W → 增长参数(i/s)
# 即：X对增长速率的影响随W的水平变化
# ============================================================
# ---- 将 x/w/t1-t4 替换为变量名 ----

# 步骤1：指定含调节的增长模型
lgm_mod_model <- '
  i =~ 1*t1 + 1*t2 + 1*t3 + 1*t4
  s =~ 0*t1 + 1*t2 + 2*t3 + 3*t4

  # 调节效应：X和W的交互项预测斜率
  s ~ x + w + x:w    # x:w为交互项
  i ~ x + w          # 截距仅含主效应
'

# 步骤2：拟合模型
lgm_mod_fit <- growth(lgm_mod_model, data=mydata)
summary(lgm_mod_fit, fit.measures=TRUE)
# s~x:w 系数显著 -> 调节效应成立
# 即X对变化速率的影响随W的水平变化

# 步骤3：简单斜率分析
install_packages('emmeans')  # 安装（仅需运行一次）
library(emmeans)
# 在W的不同水平下检验X对斜率的影响

```
**结果解读**：调节体现为 X 对增长轨迹（i/s）的影响随调节变量水平变化，交互项显著即存在调节。

#### 9.3.5 LGA有调节的中介
**方法论说明**：检验增长参数的中介效应是否受调节变量影响（有调节的纵向中介）。

**使用条件**：至少 3 个时间点；有自变量、中介（增长参数）、调节变量和结果。

**核心R包**：lavaan

```r
# ============================================================
# LGA有调节的中介：增长参数的中介路径受调节变量W影响
# ============================================================
# 模型结构：
#   X ──a──→ 增长参数(i/s) ──b──→ Y(结果)
#         ↑
#    W调节a路径（X对增长参数的影响随W变化）
# 间接效应 = a(W) * b，在不同W水平下大小不同
# ============================================================
install_packages('lavaan')
library(lavaan)

# ---- 将 x/m/y/w/t1-t4 替换为变量名 ----

# 步骤1：指定有调节的中介增长模型
lgm_modmed_model <- '
  # 潜增长因子
  i =~ 1*t1 + 1*t2 + 1*t3 + 1*t4
  s =~ 0*t1 + 1*t2 + 2*t3 + 3*t4

  # a路径含交互项（X*W -> 增长参数）
  s ~ a1 * x + a2 * w + a3 * x:w    # x:w为交互项
  i ~ x + w                         # 截距仅含主效应

  # b路径（增长参数 -> 结果）
  y ~ b1 * i + b2 * s

  # 条件间接效应定义
  ind_s := (a1 + a3 * w_mean) * b2   # 通过斜率的中介效应
  # w_mean需替换为W的均值或特定值
'

# 步骤2：拟合模型
lgm_modmed_fit <- sem(lgm_modmed_model, data=mydata,
                      se='boot', bootstrap=5000)
summary(lgm_modmed_fit, fit.measures=TRUE)
# 查看ind_s的Bootstrap置信区间
# CI不含0 -> 有调节的中介效应显著

# 步骤3：在不同W水平下计算条件间接效应
# W低（均值-1SD）：ind_low = (a1 + a3*W_low) * b2
# W高（均值+1SD）：ind_high = (a1 + a3*W_high) * b2

```
**结果解读**：条件间接效应随调节变量水平变化，差异的 CI 不含 0 说明有调节的纵向中介成立。

#### 9.3.6 LGA有中介的调节
**方法论说明**：检验调节效应（交互项对增长参数的影响）是否通过增长参数传递到结果。

**使用条件**：至少 3 个时间点；有自变量、调节变量、结果。

**核心R包**：lavaan

```r
# ============================================================
# LGA有中介的调节：X与W的交互效应通过增长参数传递
# ============================================================
# 模型结构：
#   X * W ──→ 增长参数(i/s) ──→ Y(结果)
#   交互效应对增长参数的影响 -> 增长参数对结果的影响
# 关注：交互项(x:w)对增长参数的效应(a) * 增长参数对Y的效应(b)
# ============================================================
# ---- 将 x/m/y/w/t1-t4 替换为变量名 ----

# 步骤1：创建交互项
mydata$xw <- mydata$x * mydata$w  # X与W的交互项

# 步骤2：指定有中介的调节增长模型
lgm_medmod_model <- '
  i =~ 1*t1 + 1*t2 + 1*t3 + 1*t4
  s =~ 0*t1 + 1*t2 + 2*t3 + 3*t4

  # a路径：交互项 -> 增长参数
  s ~ a1 * x + a2 * w + a3 * xw     # xw为交互项
  i ~ x + w + xw

  # b路径：增长参数 -> 结果
  y ~ b1 * i + b2 * s

  # 有中介的调节效应定义
  med_mod_s := a3 * b2   # 交互项通过斜率的中介效应
  med_mod_i := a3 * b1   # 交互项通过截距的中介效应
'

# 步骤3：拟合模型（Bootstrap检验）
lgm_medmod_fit <- sem(lgm_medmod_model, data=mydata,
                      se='boot', bootstrap=5000)
summary(lgm_medmod_fit, fit.measures=TRUE)
# 查看med_mod_s和med_mod_i的Bootstrap置信区间
# CI不含0 -> 有中介的调节效应显著
# 即X*W交互效应通过改变增长轨迹进而影响结果变量

```

**结果解读**：i的均值表示整体初始水平，s的均值表示变化速率（正=增长，负=下降）。协变量预测i和s的系数反映其对起点和变化的影响。中介效应通过增长参数传递（如X通过影响变化速率进而影响最终结果）。调节效应体现为X对增长轨迹的影响随调节变量水平变化。

#### 9.3.7 增长混合模型（GMM，识别不同增长轨迹组）

**方法论说明**：增长混合模型（Growth Mixture Model, GMM）是潜增长模型（LGA）的混合扩展，假设样本中存在多个不可观测的增长轨迹组（如"稳定高""逐渐上升""逐渐下降"），每组有不同的截距与斜率。与 LGA 假设所有个体共享同一轨迹不同，GMM 识别异质性增长模式，是 person-centered 视角下的纵向方法。OBHRM 应用：识别员工敬业度/满意度随时间变化的不同轨迹组，进而检验哪些前因预测不同轨迹组归属。

**使用条件**：至少 3 个时间点的纵向数据；样本量较大（>300，因需估计多个组的增长参数）；建议先做单组 LGA 确认整体增长形态。

**核心R包**：lcmm、mclust

```r
# 方法1：lcmm 包的 hlme()（潜类别线性混合模型，最常用）
# 注意：hlme 需长格式数据，每行一个观测，含三列：
#   id（个体标识）、time（时间点 0/1/2...）、y（响应变量）
install_packages('lcmm')
library(lcmm)
# 单组潜增长模型（基线，先确认整体增长形态）
m1 <- hlme(y ~ time, subject='id', data=mydata_long)
# 2类增长混合模型（用单组结果作初始值 B，避免 ng>1 时无法收敛）
m2 <- hlme(y ~ time, subject='id', data=mydata_long,
           mixture=~time, ng=2, B=m1)  # 2类模型
summary(m1); summary(m2)  # 比较 BIC 判断类别数（BIC 越小越好）
# 提取各样本的轨迹组归属
m2$pprob$class

# 方法2：mclust 包（基于宽格式数据的轨迹聚类）
install_packages('mclust')
library(mclust)
wide <- mydata[, c('y1','y2','y3')]  # 宽格式：每行一个体，列为时间点
mc <- Mclust(wide, G=1:4)  # 自动选择最优类别数（BIC）
summary(mc)  # 各类别的轨迹均值和比例
plot(mc, what='classification')  # 轨迹分组图
```

**结果解读**：BIC 越小越好（或 BLRT p<0.05）用于确定轨迹组数。各组的截距/斜率均值模式用于命名轨迹组（如"高稳定组""上升组""下降组"）。各组样本比例反映人群分布。进一步可纳入协变量预测轨迹组归属（用三步法或 BCH 法避免分类不确定性）。

#### 9.3.8 潜增长中介（Latent Growth Mediation，纵向机制的完整形式）

**方法论说明**：潜增长中介（Cheong, MacKinnon & Khoo, 2003）在潜增长模型（LGM）框架下检验纵向中介，即自变量 X 通过影响增长轨迹（截距 i 与斜率 s）进而影响远端结果 Y。与 12.1 的半纵向中介（只取两个时间点）不同，潜增长中介利用全部时间点信息，分别估计"X 通过初始水平（截距）影响 Y"和"X 通过变化速率（斜率）影响 Y"两条纵向机制。OBHRM 应用：领导力培训(X)通过提升工作投入的增长轨迹（斜率）进而影响长期绩效(Y)。

**使用条件**：至少 3 个时间点的纵向数据；X 为基线变量，Y 为远端结果；建议 Bootstrap 检验。

**核心R包**：lavaan

```r
# ---- 将 y1-y3 替换为三个时间点的变量名，x/outcome 替换为自变量/远端结果 ----
library(lavaan)
lgm_med_model <- '
  # 潜增长因子（截距 i 和斜率 s）
  i =~ 1*y1 + 1*y2 + 1*y3
  s =~ 0*y1 + 1*y2 + 2*y3
  # 自变量 X 预测增长参数
  i ~ a1*x
  s ~ a2*x
  # 增长参数预测远端结果 Y
  outcome ~ b1*i + b2*s + c*x
  # 纵向间接效应
  ind_i := a1*b1   # X 通过初始水平（截距）影响 Y
  ind_s := a2*b2   # X 通过变化速率（斜率）影响 Y
  ind_total := ind_i + ind_s
'
fit <- sem(lgm_med_model, data=mydata, se='boot', bootstrap=5000)
summary(fit, standardized=TRUE, ci=TRUE)
```

**结果解读**：ind_i 表示 X 通过"初始水平"影响 Y 的纵向机制，ind_s 表示 X 通过"变化速率"影响 Y 的纵向机制，两者 Bootstrap CI 不含 0 即对应机制成立。相比半纵向中介，潜增长中介能区分"起点效应"（截距）与"变化效应"（斜率），对机制的刻画更精细。

## 第10章 偏最小二乘结构方程模型

### 10.1 PLS-SEM

**方法论说明**：PLS-SEM 与本章的协方差结构方程模型（CB-SEM，lavaan）是 SEM 的两大范式。PLS-SEM 采用方差分解（基于 composite / 构成型构念）而非协方差拟合，适合**探索性 / 预测导向**模型、
小样本（n<200）、非正态数据，以及含**形成型（formative）构念**的理论。它不要求多元正态、对样本量更宽容，但参数估计略有偏、重在预测而非严格拟合优度。

**使用条件**：探索性 / 预测模型；小样本或非正态；构念为 composite（复合指标）而非共同因子；研究问题偏"预测哪些前因影响结果"而非"验证理论拟合"。

**核心R包**：`seminr`（推荐，语法简洁）、`plspm`（经典）。

**R 示例（指向脚本 `../../../r-analysis/scripts/10-pls-sem/10.1.R`）**：

```r
# ---- 按你的数据列名修改 MODEL CONFIG：composite(构念, 题项范围) + relationships(路径) ----
library(seminr)

# 测量模型：3 个 composite（VIS / IMAG / LOY），各由多题项构成
measurements <- constructs(
  composite("VIS",  multi_items("vis",  1:3)),
  composite("IMAG", multi_items("imag", 1:4)),
  composite("LOY",  multi_items("loy",  1:3))
)
# 结构模型：VIS → IMAG → LOY，且 VIS 直接 → LOY
structure <- relationships(
  paths(from = "VIS",  to = "IMAG"),
  paths(from = c("VIS", "IMAG"), to = "LOY")
)

# PLS-SEM 估计（默认 path weighting 内权重）
seminr_model <- estimate_pls(
  data              = dat,
  measurement_model = measurements,
  structural_model  = structure
)
summary(seminr_model)  # 路径系数 + 测量模型质量（Outer Loadings、AVE、CR、alpha）

# Bootstrap：路径系数显著性（默认 1000 次）
boot <- bootstrap_model(seminr_model, nboot = 1000)
summary(boot)  # 95% CI

# HTMT 区别效度（< 0.85 达标）
print(seminr_model)

# Q² 预测相关性（> 0 表示有预测力）
predict_pls(seminr_model)

# f² 效应量（小/中/大：0.02 / 0.15 / 0.35）
# fSquared(seminr_model, iv, dv)
```

**结果解读**：PLS-SEM 与 CB-SEM（lavaan）是 SEM 的两大范式。**PLS-SEM 采用方差分解**（基于 composite / 构成型构念）而非协方差拟合，适合**探索性 / 预测导向**模型、小样本（n<200）、非正态数据，
以及含**形成型（formative）构念**的理论。**seminr** 是 R 推荐实现（语法简洁），**plspm** 是经典实现。**关键指标**：①路径系数及其 Bootstrap 95% CI（CI 不含 0 表示显著）；
②Outer Loadings（≥0.7 达标）；③AVE（≥0.5 收敛效度）、CR / Cronbach's α（≥0.7 信度）；④HTMT（< 0.85 区别效度）；⑤Q²（> 0 预测相关性）；
⑥f²（0.02/0.15/0.35 为小/中/大效应）。
## 第11章 非线性结构方程模型

### 11.1 非线性SEM

**方法论说明**：传统SEM假设潜变量间关系为线性。非线性SEM允许潜变量间的交互效应（调节）和二次效应（曲线关系）。modsem包提供LMS(Latent Moderated Structural Equations)和QML(Quasi-Maximum Likelihood)两种方法估计潜变量交互，无需创建乘积指标。lavaan也可通过定义乘积指标实现观测变量的非线性效应。

**使用条件**：潜变量至少3个指标；样本量>200（LMS法建议>500）；正态性假设（LMS对非正态敏感）；模型需收敛。

**核心R包**：modsem、lavaan

```r
# ---- 将 mydata 替换为数据框名，x1-x3/z1-z3/y1-y3 替换为指标变量名 ----
install_packages('modsem')  # 安装（仅需运行一次）
install_packages('lavaan')   # 安装（仅需运行一次）
library(modsem)
library(lavaan)

# >>> 方法1：modsem潜变量交互（LMS法）<<<
# X与Z的交互影响Y（潜变量层面的调节）
# 结构图示：
#   X ~~~> Y
#     \  /
#      Z  （X×Z → Y 潜变量交互项）
#
model_int <- '
  # 测量模型
  X =~ x1 + x2 + x3      # 自变量潜变量
  Z =~ z1 + z2 + z3      # 调节变量潜变量
  Y =~ y1 + y2 + y3      # 因变量潜变量
  # 结构模型（含交互项）
  Y ~ X + Z + X:Z        # X:Z为潜变量交互项
'
fit_int <- modsem(model_int, data=mydata, method='lms')
summary(fit_int)

# >>> 方法2：modsem二次效应（Quadratic Effect）<<<
# 检验X对Y是否存在倒U型关系
# 结构图示：
#   X ~~~> Y
#   X² ~> Y  （二次项检验曲线关系）
#
model_quad <- '
  X =~ x1 + x2 + x3
  Y =~ y1 + y2 + y3
  Y ~ X + X:X            # X:X为X的二次效应项
'
fit_quad <- modsem(model_quad, data=mydata, method='qml')
summary(fit_quad)

# >>> 方法3：lavaan观测变量交互（乘积指标法）<<<
# 先创建乘积指标，再用lavaan估计
mydata$xz <- mydata$x1 * mydata$z1  # 用第一对指标创建乘积项
model_prod <- '
  X =~ x1 + x2 + x3
  Z =~ z1 + z2 + z3
  Y =~ y1 + y2 + y3
  XZ =~ xz               # 乘积指标作为潜变量
  Y ~ X + Z + XZ
'
fit_prod <- sem(model_prod, data=mydata)
summary(fit_prod, fit.measures=TRUE, standardized=TRUE)
```

**结果解读**：modsem的LMS法输出中，X:Z的系数显著（p<0.05）表示潜变量交互效应成立，即X对Y的影响随Z水平变化。QML法更适合大模型或非正态数据。二次效应X:X的系数显著为负表示倒U型关系（适度水平最优），显著为正表示U型关系。
乘积指标法中XZ的路径系数解释为调节效应大小。三种方法中，LMS统计效力最高但对样本量和正态性要求也最高；QML是折中方案；乘积指标法最简单但需要手动创建交互项。

## 第12章 交叉滞后模型分析

### 12.1 交叉滞后模型

**方法论说明**：用于纵向数据检验两个变量的双向因果关系。RI-CLPM进一步区分个体间和个体内效应。OBHRM 中用于检验工作满意度与工作绩效的双向因果、组织承诺与离职意愿的相互预测等纵向关系。

**使用条件**：至少两个时间点的面板数据；样本量>200。

**核心R包**：lavaan

```r
# 交叉滞后模型（CLPM） — lavaan包
# ============================================================
# 用于纵向数据检验两个变量的双向因果关系
# X是否预测Y的变化？Y是否预测X的变化？
# RI-CLPM进一步区分个体间和个体内效应
# ============================================================

# ---- 安装并加载包 ----
install_packages('lavaan')  # SEM核心包
library(lavaan)              # 加载lavaan

# ---- 将 mydata_long 替换为面板数据框名 ----
# ---- 将 x1-x3/y1-y3 替换为三个时间点的变量名 ----

# 步骤1：指定CLPM模型
clpm_model <- '
  # 自回归路径（稳定性）
  x2 ~ x1    # x的稳定性
  x3 ~ x2
  y2 ~ y1    # y的稳定性
  y3 ~ y2

  # 交叉滞后路径（因果方向）
  y2 ~ x1    # x预测后续y
  y3 ~ x2
  x2 ~ y1    # y预测后续x
  x3 ~ y2

  # 同期相关
  x1 ~~ y1
  x2 ~~ y2
  x3 ~~ y3
'

# 步骤2：拟合CLPM模型
clpm_fit <- sem(clpm_model, data=mydata_long)
summary(clpm_fit, fit.measures=TRUE, standardized=TRUE)
# 解读：交叉滞后路径系数显著 -> 存在因果预测关系

# >>> 纵向中介（半纵向中介，Cole & Maxwell, 2003）<<<
# 检验 X1 → M2 → Y3 的纵向机制（X 通过 M 的纵向变化影响 Y）
long_med_model <- '
  # 自回归（控制前一时间点的水平）
  M2 ~ s1*M1
  Y3 ~ s2*Y2
  # 纵向中介路径
  M2 ~ a*X1
  Y3 ~ b*M2 + c*X1
  # 纵向间接效应
  ind := a*b
'
fit_long_med <- sem(long_med_model, data=mydata_long, se='boot', bootstrap=5000)
summary(fit_long_med, standardized=TRUE, ci=TRUE)
# 解读：ind 的 Bootstrap CI 不含 0 → 纵向中介成立
```
**结果解读**：交叉滞后系数（X1→Y2 与 Y1→X2）是核心。若 X1→Y2 显著而 Y1→X2 不显著，支持 X 是 Y 的先行因素（单向因果）；两者都显著则存在双向关系。自回归系数反映变量跨时间的稳定性。

## 第13章 经验取样分析

### 13.1 经验取样法数据分析

**方法论说明**：ESM是密集纵向数据（每天多次测量），本质是多层结构（观测嵌套于个体）。基础分析用多层模型分离个体内/间效应。复杂扩展包括：多层中介（1-1-1模型）、双中介、链式中介、有调节的中介等——都是多层次结构模型的应用。OBHRM 中用于日记法/瞬时评估研究，如每日工作压力对当日情绪、次日恢复及工作投入的动态影响。

**使用条件**：至少30个被试，每人至少5个时间点；数据为长格式（每行一个观测）。

**核心R包**：lme4、lmerTest、mediation

#### 13.1.1 ESM基础分析
**方法论说明**：用多层模型分离 ESM 数据的个体内（within-person）与个体间（between-person）效应，是 ESM 分析的基础。

**使用条件**：密集纵向数据（每天多次测量）；个体内时间点 > 10。

**核心R包**：lme4、lmerTest

```r
# ESM基础分析：多层模型分离个体内/间效应
# ============================================================
# ESM数据结构：
#   Level 1（个体内）：时间点嵌套于个体
#   Level 2（个体间）：个体差异
# ============================================================
install_packages('lme4')       # 多层模型包
install_packages('lmerTest')    # 提供p值
install_packages('dplyr')  # 安装（仅需运行一次）
library(lme4)                   # 加载lme4
library(lmerTest)                # 加载lmerTest

# ---- 将 mydata_long 替换为长格式数据框名 ----
# ---- 将 y/subj_id/day/time 替换为变量名 ----

# 步骤1：零模型（计算ICC）
null_model <- lmer(y ~ 1 + (1 | subj_id), data=mydata_long)
vc <- VarCorr(null_model)
ICC <- vc$subj_id[1,1] / (vc$subj_id[1,1] + attr(vc, 'sc')^2)
print(paste('ICC =', round(ICC, 3)))  # ICC>0.059需要多层模型

# 步骤2：CWC中心化（分离个体内/间效应）
# 组均值中心化：将个体内变异和个体间变异分离
library(dplyr)
mydata_long <- mydata_long %>%
  group_by(subj_id) %>%
  mutate(x_pwc = x - mean(x, na.rm=TRUE),  # 个体内中心化（个体内效应）
         x_pgm = mean(x, na.rm=TRUE)) %>%    # 个体均值（个体间效应）
  ungroup()

# 步骤3：多层回归（含CWC中心化的自变量）
esm_model <- lmer(y ~ x_pwc + x_pgm + (1 | subj_id),
                  data=mydata_long)
summary(esm_model)
# x_pwc系数=个体内效应（同一人内x变化对y的影响）
# x_pgm系数=个体间效应（不同人间x均值差异对y的影响）

```
**结果解读**：ICC 反映个体间方差占比，个体内效应（within）与个体间效应（between）的系数分开报告，两者的含义不同。

#### 13.1.2 ESM多层中介
**方法论说明**：在 ESM 数据中检验 1-1-1 多层中介（X、M、Y 均在个体内水平），分离组内与组间中介。

**使用条件**：密集纵向数据；X、M、Y 均为个体内变量。

**核心R包**：lme4、lmerTest、mediation

```r
# ============================================================
# ESM多层中介：X→M→Y 均在个体内水平（1-1-1模型）
# ============================================================
# 需对X和M都做CWC中心化，分离个体内/间效应
# 只关注个体内的中介路径（同一时间点内X→M→Y）
# ============================================================
# ---- 将 x/m/y/subj_id 替换为变量名 ----

# 步骤1：CWC中心化X和M
install_packages('dplyr')  # 安装（仅需运行一次）
library(dplyr)
mydata_long <- mydata_long %>%
  group_by(subj_id) %>%
  mutate(x_cwc = x - mean(x, na.rm=TRUE),   # X的个体内中心化
         m_cwc = m - mean(m, na.rm=TRUE)) %>% # M的个体内中心化
  ungroup()

# 步骤2：a路径（X→M）
model_a <- lmer(m_cwc ~ x_cwc + (1 | subj_id), data=mydata_long)

# 步骤3：b路径（M→Y，控制X）
model_b <- lmer(y ~ m_cwc + x_cwc + (1 | subj_id), data=mydata_long)

# 步骤4：中介效应检验（Bootstrap）
install_packages('mediation')
library(mediation)
set.seed(123)
med_result <- mediate(model_a, model_b,
                      treat='x_cwc',       # 自变量（个体内X）
                      mediator='m_cwc',     # 中介变量（个体内M）
                      sims=500)
summary(med_result)
# ACME=间接效应（个体内X→M→Y），p<0.05则中介显著

```
**结果解读**：组内（within）间接效应的 CI 不含 0 说明个体内中介成立，注意与组间中介区分。

#### 13.1.3 ESM双中介
**方法论说明**：在 ESM 数据中检验两个并行中介（M1、M2）同时传递 X 对 Y 的个体内效应。

**使用条件**：密集纵向数据；两个中介均为个体内变量。

**核心R包**：lme4、lmerTest

```r
# ============================================================
# ESM双中介：X通过M1和M2两条平行路径影响Y
# ============================================================
# 模型结构：
#   X ──→ M1 ──→ Y  （间接效应1）
#    \               ↑
#     ──→ M2 ────────┘  （间接效应2）
# ============================================================
# ---- 将 x/m1/m2/y/subj_id 替换为变量名 ----

# 步骤1：CWC中心化所有Level 1变量
install_packages('dplyr')  # 安装（仅需运行一次）
library(dplyr)
mydata_long <- mydata_long %>%
  group_by(subj_id) %>%
  mutate(x_cwc = x - mean(x, na.rm=TRUE),
         m1_cwc = m1 - mean(m1, na.rm=TRUE),
         m2_cwc = m2 - mean(m2, na.rm=TRUE)) %>%
  ungroup()

# 步骤2：a路径（X→M1和X→M2）
model_m1 <- lmer(m1_cwc ~ x_cwc + (1 | subj_id), data=mydata_long)
model_m2 <- lmer(m2_cwc ~ x_cwc + (1 | subj_id), data=mydata_long)

# 步骤3：b路径（M1和M2同时预测Y）
model_y <- lmer(y ~ m1_cwc + m2_cwc + x_cwc + (1 | subj_id),
                data=mydata_long)

# 步骤4：计算双中介效应
a1 <- fixef(model_m1)['x_cwc']  # X→M1的a1系数
a2 <- fixef(model_m2)['x_cwc']  # X→M2的a2系数
b1 <- fixef(model_y)['m1_cwc']  # M1→Y的b1系数
b2 <- fixef(model_y)['m2_cwc']  # M2→Y的b2系数
ind1 <- a1 * b1  # 通过M1的间接效应
ind2 <- a2 * b2  # 通过M2的间接效应
contrast <- ind1 - ind2  # 两条路径的差异
cat(sprintf('Ind1=%.4f, Ind2=%.4f, Contrast=%.4f\n', ind1, ind2, contrast))

```
**结果解读**：两个中介各自的组内间接效应 CI 不含 0 即成立，可比较两个中介的相对大小。

#### 13.1.4 ESM链式中介
**方法论说明**：在 ESM 数据中检验链式中介（X → M1 → M2 → Y），中介变量间有顺序。

**使用条件**：密集纵向数据；中介变量间有理论上的先后顺序。

**核心R包**：lme4、lmerTest

```r
# ============================================================
# ESM链式中介：X→M1→M2→Y 序列传递
# ============================================================
# 模型结构：
#   X ──→ M1 ──→ M2 ──→ Y
#   （三级链式传递）
# ============================================================
# ---- 将 x/m1/m2/y/subj_id 替换为变量名 ----

# 步骤1：CWC中心化
install_packages('dplyr')  # 安装（仅需运行一次）
library(dplyr)
mydata_long <- mydata_long %>%
  group_by(subj_id) %>%
  mutate(x_cwc = x - mean(x, na.rm=TRUE),
         m1_cwc = m1 - mean(m1, na.rm=TRUE),
         m2_cwc = m2 - mean(m2, na.rm=TRUE)) %>%
  ungroup()

# 步骤2：a路径
# X→M1
model_m1 <- lmer(m1_cwc ~ x_cwc + (1 | subj_id), data=mydata_long)
# X→M2（控制M1，检验M1→M2的路径d21）
model_m2 <- lmer(m2_cwc ~ x_cwc + m1_cwc + (1 | subj_id),
                 data=mydata_long)

# 步骤3：b路径（M2→Y，控制X和M1）
model_y <- lmer(y ~ m2_cwc + m1_cwc + x_cwc + (1 | subj_id),
                data=mydata_long)

# 步骤4：计算链式间接效应
a1 <- fixef(model_m1)['x_cwc']     # X→M1
d21 <- fixef(model_m2)['m1_cwc']   # M1→M2
b2 <- fixef(model_y)['m2_cwc']      # M2→Y
ind_serial <- a1 * d21 * b2  # 链式间接效应=a1*d21*b2
cat(sprintf('Serial indirect effect = %.4f\n', ind_serial))
# 用Bootstrap检验显著性（参考6.12 Bootstrapping方法）

```
**结果解读**：链式间接效应（X→M1→M2→Y）的 CI 不含 0 说明链式中介成立，注意与并行中介区分。

#### 13.1.5 ESM有调节的多层中介
**方法论说明**：在 ESM 数据中检验有调节的多层中介（个体间变量调节个体内中介）。

**使用条件**：密集纵向数据；有个体间调节变量。

**核心R包**：lme4、lmerTest

```r
# ============================================================
# ESM有调节的中介：调节变量W影响中介路径的强度
# ============================================================
# 模型结构：
#   Level 2: W(个体间调节变量)
#   Level 1: X→M→Y（个体内中介路径）
#   W调节a路径（X→M的强度随W变化）
# ============================================================
# ---- 将 x/m/y/w/subj_id 替换为变量名 ----
# ---- W为个体间变量（如人格特质），不随时间变化 ----

# 步骤1：CWC中心化Level 1变量
install_packages('dplyr')  # 安装（仅需运行一次）
library(dplyr)
mydata_long <- mydata_long %>%
  group_by(subj_id) %>%
  mutate(x_cwc = x - mean(x, na.rm=TRUE),
         m_cwc = m - mean(m, na.rm=TRUE)) %>%
  ungroup()

# 步骤2：a路径含交互项（X*W→M）
model_a <- lmer(m_cwc ~ x_cwc * w + (1 | subj_id),
                data=mydata_long)
# x_cwc:w 交互项显著 -> W调节X→M路径

# 步骤3：b路径（M→Y）
model_b <- lmer(y ~ m_cwc + x_cwc + w + (1 | subj_id),
                data=mydata_long)

# 步骤4：条件间接效应（在不同W水平下）
# W低时：ind_low = (a1 + a3*W_low) * b
# W高时：ind_high = (a1 + a3*W_high) * b
# a1 = X→M的主效应，a3 = 交互项系数
a1 <- fixef(model_a)['x_cwc']
a3 <- fixef(model_a)['x_cwc:w']
b <- fixef(model_b)['m_cwc']

W_low <- mean(mydata_long$w) - sd(mydata_long$w)  # W低于均值1SD
W_high <- mean(mydata_long$w) + sd(mydata_long$w)  # W高于均值1SD
ind_low <- (a1 + a3 * W_low) * b     # W低时的间接效应
ind_high <- (a1 + a3 * W_high) * b   # W高时的间接效应
cat(sprintf('W低: ind=%.4f, W高: ind=%.4f\n', ind_low, ind_high))
# 若ind_low和ind_high符号或大小不同 -> 有调节的中介效应

```

**结果解读**：ESM数据本质是多层结构（观测嵌套于个体）。ICC>0.059说明需要多层模型。CWC中心化后可分离个体内效应（同一人内变化）和个体间效应（人与人差异）。1-1-1多层中介检验个体内的X→M→Y路径。双中介检验两条平行路径的差异。链式中介检验X→M1→M2→Y的序列传递。有调节的中介检验W是否影响个体内中介路径的强度。

#### 13.1.6 动态结构方程模型

**方法论说明**：动态结构方程模型（Dynamic Structural Equation Modeling, DSEM）是分析密集纵向数据（ESM、日记法，每天多次测量）的前沿方法。与传统的多层模型（将重复测量嵌套于个体）不同，
DSEM 显式建模个体内的**时间动态依赖**：自回归效应（当前状态受前一时刻状态影响）、交叉滞后效应（X 的波动预测后续 Y 的波动）、以及动态中介。DSEM 用贝叶斯估计（Mplus 为主流，R 有 dsem 包），
能分离个体内（within-person）的动态过程。OBHRM 应用：每日工作压力→每日情绪耗竭的动态中介、情绪状态的自回归与相互影响。

**使用条件**：密集纵向数据（通常 >20 个时间点/人）；关注个体内的动态关系而非个体间差异；需处理缺失与不等距时间点。

**核心R包**：dsem（R 实现，较新）、Mplus（主流）

```r
# DSEM 在 R 中用 dsem 包实现（较新，主流仍用 Mplus）
# 基本思路：在多层框架中加入自回归/交叉滞后，显式建模时间动态
# 以下为概念性示例（dsem 包需较长的数据准备，此处给出核心结构）
install_packages('dsem')
library(dsem)
# 核心模型：个体内自回归 + 交叉滞后（滞后1阶）
# X[t] ~ X[t-1] + Y[t-1]   （自回归 + 交叉滞后）
# Y[t] ~ Y[t-1] + X[t-1]
# 完整实现需用 dsem() 指定动态项，并处理 person-mean centering
# 注：DSEM 主流在 Mplus 中用 %WITHIN% 和 ON 语句实现
```

**结果解读**：DSEM 的核心输出是个体内自回归系数（状态的稳定性/惯性）与交叉滞后系数（变量间的动态预测关系）。自回归系数高（如 0.5）说明状态有较强惯性；交叉滞后系数显著说明一个变量的波动能在时间上预测另一变量的后续波动。与 CLPM（面板数据，少量时间点）相比，DSEM 适用于大量时间点的密集数据，能更精确地刻画个体内动态过程。这是 ESM 研究的前沿方向，建议关注但注意其实现复杂度。

## 第14章 主客体互依模型分析

### 14.1 主客体互依模型

**方法论说明**：APIM 专用于**成对 / 对偶数据**（情侣、师徒、上下级、队友）。它同时估计两种效应：actor 效应（自身 X→自身 Y）与 partner 效应（伴侣 X→自身 Y），从而控制"对子内非独立性"。
可区分对子（如按性别 / 角色）需做可区分性检验（LR 检验）；不可区分对子可合并建模。实现有两条路径：MLM 路径（lme4，适用广）与 SEM 路径（lavaan，可区分对子、宽格式）。

**使用条件**：成对 / 对偶数据；关注双向互依效应；需处理对子内相关（ICC）。

**核心R包**：`lme4`（MLM 路径，必需）、`lavaan`（SEM 路径，可选）。

**R 示例（指向脚本 `../../../r-analysis/scripts/14-apim/14.1.R`）**：

```r
# ---- 数据要求：LONG 格式，每行一个成员（dyad / member / X / Xp / Y）----
library(lme4)

# 基线 MLM-APIM：对子内嵌套结构（1 | dyad）控制非独立性
model_apim <- lmer(Y ~ X + Xp + (1 | dyad), data = dat)
summary(model_apim)
# 固定效应：X → actor 效应（自身 X 对自身 Y），Xp → partner 效应（伴侣 X 对自身 Y）

# 可区分性检验：LR 检验（仅 member 列存在且取值 > 1 时启用）
if (distinguishable) {
  model_dist <- lmer(Y ~ X * member + Xp * member + (1 | dyad), data = dat)
  cat("可区分 APIM（actor/partner 效应按 member 分层）\n")
  print(summary(model_dist))
  cat("LR 检验：anova(model_apim, model_dist)\n")
  anova(model_apim, model_dist)
}

# 配对数据变体（同一 dyad 内两个成员配对）：
# 可用 t 检验或配对回归比较 actor 效应与 partner 效应是否对称
# 详见 @manual 段
```

**结果解读**：APIM 专用于**成对 / 对偶数据**（情侣、师徒、上下级、队友），同时估计两种效应：actor 效应（自身 X→自身 Y）与 partner 效应（伴侣 X→自身 Y），从而控制"对子内非独立性"。**实现路径**：
①MLM 路径（lme4，适用广）—— `lmer(Y ~ X + Xp + (1 | dyad))`；②SEM 路径（lavaan，可区分对子、宽格式）—— 见同方法族。**可区分性**：若对子可区分（按性别 / 角色），
需用 `Y ~ X * member + Xp * member` 区分 actor/partner 效应是否对称；不可区分对子用基线模型即可。**关键指标**：①固定效应 X 系数（actor）、Xp 系数（partner）及其显著性；
②ICC（对子内相关，由 (1|dyad) 随机效应给出）；③LR 检验（基线 vs 可区分模型，p<.05 说明需可区分建模）。
## 第15章 广义线性混合模型分析

### 15.1 多层线性模型：零模型与方差分解

**方法论说明**：当数据存在嵌套结构时，传统回归假设观测独立会被违反。零模型将总方差分解为组间方差(τ00)和组内方差(σ²)，计算ICC判断是否需要多层分析。ICC = τ00 / (τ00 + σ²)，ICC>0.059时需使用多层模型。OBHRM 中，个体嵌套于团队/组织是常态，零模型用于判断组间差异占比，ICC 显著（>0.05）即提示应采用多层模型而非普通回归。

**使用条件**：数据具有嵌套结构（至少2层）；每组样本量>5；总组数>20。

**核心R包**：lme4、lmerTest、performance

```r
# ============================================================
# 多层线性模型：零模型与方差分解 — lme4 + lmerTest包
# ============================================================
# 零模型（Null Model）：无自变量，仅估计组间和组内方差
# 用于计算ICC（组内相关系数），判断是否需要多层模型
# ICC > 0.059 -> 需要多层模型
# ============================================================

# ---- 安装并加载包 ----
install_packages('lme4')       # 多层模型核心包
install_packages('lmerTest')   # 提供p值
library(lme4)                   # 加载lme4
library(lmerTest)                # 加载lmerTest

# ---- 将 mydata 替换为数据框名 ----
# ---- 将 y 替换为因变量名 ----
# ---- 将 group_id 替换为组ID变量名 ----

# 步骤1：拟合零模型（无预测变量）
null_model <- lmer(y ~ 1 + (1 | group_id), data=mydata)
summary(null_model)

# 步骤2：计算ICC（组内相关系数）
# ICC = 组间方差 / (组间方差 + 组内方差)
vc <- VarCorr(null_model)           # 提取方差成分
tau00 <- vc$group_id[1,1]           # 组间方差（Level 2）
sigma2 <- attr(vc, 'sc')^2          # 组内方差（Level 1）
ICC <- tau00 / (tau00 + sigma2)     # ICC计算
print(paste('ICC =', round(ICC, 3)))
# ICC > 0.059 -> 组间变异显著，需要多层模型

# 步骤3：方差分解比例
print(paste('组间变异比例:', round(tau00/(tau00+sigma2)*100, 1), '%'))
print(paste('组内变异比例:', round(sigma2/(tau00+sigma2)*100, 1), '%'))
```

**结果解读**：VarCorr()输出随机效应的方差成分。tau00（组间方差）和sigma2（组内方差）计算ICC=tau00/(tau00+sigma2)。ICC<0.059可考虑传统回归（组间差异很小），0.059-0.138中等程度需要多层，>0.138必须使用多层模型。ICC的经济含义为同一组内两个个体因相似环境导致的相似程度。

### 15.2 随机截距模型与随机斜率模型

**方法论说明**：零模型确认后逐步加入预测变量。随机截距模型允许各组有不同的截距；随机斜率模型允许自变量效应在各组间变化。通过似然比检验比较嵌套模型。OBHRM 典型应用：员工绩效(Y)受个人努力(X)影响，但不同团队基线绩效不同（随机截距），且努力对绩效的影响强度在不同团队有差异（随机斜率）。

**核心R包**：lme4、lmerTest

```r
# ---- 将 mydata 替换为数据框名，y/x1 替换为因变量和自变量，group_id 替换为分组变量 ----
install_packages('lme4')  # 安装（仅需运行一次）
install_packages('lmerTest')  # 安装（仅需运行一次）
library(lme4); library(lmerTest)
# 随机截距模型
model_ri <- lmer(y ~ x1 + (1 | group_id), data=mydata)
# 随机斜率模型
model_rs <- lmer(y ~ x1 + (1 + x1 | group_id), data=mydata)
anova(model_ri, model_rs)  # p<0.05说明随机斜率必要
# 加入Level-2变量（组层变量）
model_l2 <- lmer(y ~ x1 + x2_group + (1 | group_id), data=mydata)
```
**使用条件**：数据具有嵌套结构；每组样本量 > 5；总组数 > 20。

**结果解读**：随机截距方差（τ00）反映组间差异，随机斜率方差反映自变量效应在组间的变异。anova(model_ri, model_rs) 的 p<0.05 说明随机斜率有必要保留。

### 15.3 跨水平交互效应与中心化策略

**方法论说明**：检验组层变量是否调节个体层变量对因变量的效应。Enders & Tofighi (2007)建议：检验Level-1主效应用CWC（分组均值中心化）；检验Level-2主效应用CGM（总均值中心化）。

**使用条件**：数据为嵌套结构；需区分组内效应和组间效应。

**核心R包**：lme4、lmerTest、misty、dplyr

```r
# ---- 将 mydata 替换为数据框名，y/x1/x2_group 替换为变量名，group_id 替换为分组变量 ----
install_packages('lme4')  # 安装（仅需运行一次）
install_packages('lmerTest')  # 安装（仅需运行一次）
install_packages('misty')  # 安装（仅需运行一次）
install_packages('dplyr')  # 安装（仅需运行一次）
library(lme4); library(lmerTest); library(misty); library(dplyr)
# Level-1变量分组均值中心化（CWC）
# center() 第一个参数是数据框，cluster 指定分组变量（字符串），生成新列 x1.c
mydata <- center(mydata, x1, type='CWC', cluster='group_id')
mydata$x1_cwc <- mydata$x1.c  # 提取组内中心化列
# 保存组均值作为Level-2变量
gm <- mydata %>% group_by(group_id) %>% summarise(x1_gmean = mean(x1, na.rm=TRUE))
mydata <- merge(mydata, gm, by='group_id')
mydata$x1_gmean_cgm <- mydata$x1_gmean - mean(mydata$x1_gmean, na.rm=TRUE)  # 总均值中心化
# 跨水平交互
mydata$cross_int <- mydata$x1_cwc * mydata$x1_gmean_cgm
model_cross <- lmer(y ~ x1_cwc + x1_gmean_cgm + cross_int + (1 + x1_cwc | group_id), data=mydata)
summary(model_cross)
# x1_cwc: 组内效应；x1_gmean_cgm: 组间效应(情境效应)；cross_int: 跨水平交互
```
**结果解读**：跨层交互项（Level-2 变量 × Level-1 变量）系数显著说明组层变量调节了个体层变量的效应。中心化策略影响系数解释：CWC（组均值中心化）分离组内/组间效应，CGM（总均值中心化）保留组间效应。

### 15.4 多层中介效应模型

**方法论说明**：根据X/M/Y所在层级分为不同类型：1-1-1（三个变量均在Level-1，需区分组内和组间中介）、2-1-1（X在Level-2，最常见，中介效应仅在Level-2）、2-2-1（X和M在Level-2）。OBHRM 典型应用：2-1-1 模型如团队领导力(X, Level-2)→团队氛围(M, Level-2)→员工绩效(Y, Level-1)。

**使用条件**：数据具有嵌套结构；总组数>20。

**核心R包**：lavaan、misty、dplyr

```r
# ============================================================
# 多层中介效应模型 — lme4 + lmerTest + mediation包
# ============================================================
# 在嵌套数据中检验中介效应
# 常见类型：
#   1-1-1：X,M,Y均在Level 1（需CWC中心化分离组内/组间效应）
#   2-1-1：X在Level 2，M,Y在Level 1（最常见）
#   2-2-1：X,M在Level 2，Y在Level 1
#
# 模型结构示意（2-1-1）：
#   Level 2: group_id → X(组级变量)
#   Level 1: M → Y (个体级)
#   X → M → Y（跨层中介）
# ============================================================

# ---- 安装并加载包 ----
install_packages('lme4')        # 多层模型包
install_packages('lmerTest')    # p值
install_packages('mediation')   # 中介检验
library(lme4)                    # 加载lme4
library(lmerTest)                # 加载lmerTest
library(mediation)               # 加载mediation

# ---- 将 X/M/Y 替换为自变量/中介变量/因变量，group_id 替换为分组变量（注意与数据列名一致）----

# 步骤1：a路径模型（X→M）
model_a <- lmer(M ~ X + (1 | group_id), data=mydata)
# 步骤2：b路径模型（M→Y，控制X）
model_b <- lmer(Y ~ M + X + (1 | group_id), data=mydata)

# 步骤3：中介效应检验（Bootstrap）
set.seed(123)
med_result <- mediate(model_a, model_b,
                      treat='X',          # 自变量
                      mediator='M',       # 中介变量
                      sims=500)           # Bootstrap次数
summary(med_result)
# ACME(平均因果中介效应)：间接效应，p<0.05则中介显著
# ADE(平均直接效应)：直接效应
# Total Effect：总效应=ACME+ADE
```

#### 15.4.1 跨层次有调节的中介

**方法论说明**：跨层次有调节的中介指在嵌套数据结构中，Level-2变量调节Level-1的中介路径。常见类型：(1)2-1-1模型中Level-2的W调节a路径(X->M)；(2)2-1-1模型中Level-2的W调节b路径(M->Y)；
(3)2-1-1模型中Level-2的W同时调节a和b路径。在MSEM框架中(Preacher et al., 2010)，通过lavaan的level:1/level:2语法分解组内/组间效应，在Level-2构建调节交互项，
用Bootstrap检验条件间接效应。

**使用条件**：数据具有嵌套结构（个体嵌套于组）；自变量X和中介M、因变量Y在Level-1测量；调节变量W在Level-2测量（组水平）；ICC>0.059；组数>30。

**核心R包**：lavaan、misty

```r
# ---- 将 mydata 替换为数据框名，x/m/y 替换为Level-1变量，w 替换为Level-2变量，group_id 替换为分组变量 ----
install_packages('lavaan')  # 安装（仅需运行一次）
install_packages('misty')   # 安装（仅需运行一次）
library(lavaan)
library(misty)

# >>> 数据准备：组均值中心化分离组内/组间效应 <<<
# 对Level-1变量做CWC(M)，生成组内成分和组间成分
mydata <- center(mydata, x, type='CWC', cluster='group_id')  # X组内中心化
mydata <- center(mydata, m, type='CWC', cluster='group_id')  # M组内中心化
mydata <- center(mydata, y, type='CWC', cluster='group_id')  # Y组内中心化
mydata$x_cwc <- mydata$x.c; mydata$m_cwc <- mydata$m.c; mydata$y_cwc <- mydata$y.c
# 组均值（Level-2组间成分）
mydata$x_between <- ave(mydata$x, mydata$group_id)
# 创建Level-2交互项：W × X_between
mydata$w_x_bet <- mydata$w * mydata$x_between  # 调节交互项

# >>> 模型结构图示 <<<
# Level-1（个体层）：
#   X_within --> M_within --> Y_within
#   (a路径)     (b路径)
# Level-2（组层）：
#   W 调节 a路径 或 b路径
#
#   W ~~~~~~> (a路径)
#            /
#   X --> M --> Y
#         ^
#   W ~~~~> (b路径)

# >>> 跨层次有调节的中介模型（W调节a路径）<<<
model_clmm <- '
  # Level-1：组内中介路径
  level: 1
    m_cwc ~ a * x_cwc             # a路径：X对M的效应（组内）
    y_cwc ~ b * m_cwc + x_cwc     # b路径：M对Y的效应 + X的直接效应
  # Level-2：组间调节
  level: 2
    m_cwc ~ a2 * w + w_x_bet      # W调节a路径：W对M的组间效应 + 交互项
    y_cwc ~ b2 * w + m_cwc         # W对Y的直接效应
  # 间接效应标签
  # 当W=低时：ind_low = a * b
  # 当W=高时：ind_high = (a + a2) * b
'
fit_clmm <- sem(model_clmm, data=mydata, cluster='group_id',
                se='boot', bootstrap=1000)  # Bootstrap检验间接效应
summary(fit_clmm, fit.measures=TRUE, standardized=TRUE)

# >>> 条件间接效应计算 <<<
# 提取参数
pe <- parameterEstimates(fit_clmm, boot.ci.type='bca.simple')
a_val <- pe$est[pe$label=='a']         # a路径系数
a2_val <- pe$est[pe$label=='a2']      # W对a路径的调节系数
b_val <- pe$est[pe$label=='b']        # b路径系数
# W=均值-1SD（低W）时的间接效应
ind_low <- a_val * b_val              # 低W条件下的间接效应
# W=均值+1SD（高W）时的间接效应
ind_high <- (a_val + a2_val) * b_val  # 高W条件下的间接效应
cat('W=低时间接效应:', ind_low, '
')
cat('W=高时间接效应:', ind_high, '
')
cat('差异:', ind_high - ind_low, '
')

# >>> 简单斜率分析：检验不同W水平下的a路径 <<<
# W=低（均值-1SD）时a路径是否显著
# W=高（均值+1SD）时a路径是否显著
# 若差异显著，说明W调节了中介过程（有调节的中介成立）
```

**结果解读**：参数估计中a2（W对a路径的调节系数）显著（p<0.05）表示调节效应成立。条件间接效应ind_low和ind_high的差异表示调节效应的方向：若ind_high>ind_low且差异显著，说明W增强了中介效应（正向调节）；反之则削弱。
Bootstrap 95%CI不含0表示该条件下的间接效应显著。注意：跨层次有调节的中介关注的是Level-2变量如何改变Level-1中介过程的强度，而非组间中介。Preacher等(2010)建议组数>50时MSEM方法更可靠，组数较少时可考虑MLM方法。

#### 15.4.2 跨层次有中介的调节

**方法论说明**：跨层次有中介的调节指跨水平交互效应（X×W对Y的影响）通过中介变量M传递。模型逻辑：Level-2变量W与Level-1变量X的交互项（X×W）影响中介M，M再影响Y。即交互效应本身被中介了。在MSEM框架中，W和M通常在Level-2测量，X和Y在Level-1测量，通过lavaan的level:1/level:2语法构建跨水平交互项并检验中介路径。

**使用条件**：数据具有嵌套结构；交互效应（X×W→Y）显著是前提条件；中介M需要能解释交互效应的传递机制；组数>30。

**核心R包**：lavaan、misty

```r
# ---- 将 mydata 替换为数据框名，x/y 替换为Level-1变量，w/m 替换为Level-2变量，group_id 替换为分组变量 ----
install_packages('lavaan')  # 安装（仅需运行一次）
install_packages('misty')   # 安装（仅需运行一次）
library(lavaan)
library(misty)

# >>> 数据准备 <<<
# Level-1变量组内中心化（CWC）
mydata <- center(mydata, x, type='CWC', cluster='group_id')
mydata <- center(mydata, m, type='CWC', cluster='group_id')
mydata <- center(mydata, y, type='CWC', cluster='group_id')
mydata$x_cwc <- mydata$x.c; mydata$m_cwc <- mydata$m.c; mydata$y_cwc <- mydata$y.c
# 创建跨水平交互项：Level-1的X × Level-2的W
mydata$xw <- mydata$x_cwc * mydata$w

# >>> 模型结构图示 <<<
# Level-2（组层）：
#   W --> M           （W影响中介M）
#   W × X --> M       （交互效应影响M）
# Level-1（个体层）：
#   X --> Y            （X对Y的主效应）
#   M --> Y            （M对Y的中介路径）
#
#   W ~~~~~~> M ~~~~~~> Y
#    \      /
#     X × W            （交互效应被M中介）
#      |
#      v
#      Y

# >>> 跨层次有中介的调节模型 <<<
model_clmm2 <- '
  # Level-1：组内路径
  level: 1
    y_cwc ~ c * x_cwc + b * m_cwc   # c:X的直接效应 + b:M对Y的中介路径
  # Level-2：组间路径
  level: 2
    m_cwc ~ a1 * w + a2 * xw          # a1:W对M的效应 + a2:交互效应(X×W)对M的效应
    y_cwc ~ w + m_cwc                 # W对Y的直接效应 + M对Y的组间效应
  # 间接的交互效应 = a2 × b
  # 即交互效应通过M传递的部分
'
fit_clmm2 <- sem(model_clmm2, data=mydata, cluster='group_id',
                 se='boot', bootstrap=1000)
summary(fit_clmm2, fit.measures=TRUE, standardized=TRUE)

# >>> 间接的交互效应检验 <<<
pe2 <- parameterEstimates(fit_clmm2, boot.ci.type='bca.simple')
a2_est <- pe2$est[pe2$label=='a2']    # 交互效应对M的影响
b_est <- pe2$est[pe2$label=='b']      # M对Y的影响
ind_interact <- a2_est * b_est        # 间接的交互效应 = a2 × b
cat('间接的交互效应(a2*b):', ind_interact, '
')

# >>> 完整的交互效应分解 <<<
# 总交互效应 = 直接交互效应(c的交互部分) + 间接交互效应(a2*b)
# 若a2显著且a2*b的CI不含0：交互效应部分通过M传递（有中介的调节成立）
# 若c的交互部分不再显著：完全中介的交互效应
# 若c的交互部分仍显著：部分中介的交互效应
```

**结果解读**：a2（交互项X×W对M的效应）显著表示交互效应影响中介变量。a2*b（间接的交互效应）的Bootstrap 95%CI不含0表示跨水平交互效应通过M传递，即有中介的调节成立。与8.7的区别：有调节的中介关注"中介过程被谁调节"，
有中介的调节关注"交互效应通过谁传递"。需先确认跨水平交互效应（X×W→Y）存在，再检验中介路径。方杰和温忠麟(2018)建议报告间接交互效应和直接交互效应的置信区间，明确交互效应中被中介的比例。


### 15.5 广义线性混合模型

**方法论说明**：多层模型和广义线性模型的结合，用于嵌套结构下的非正态因变量（二分类/计数）。

**使用条件**：因变量为非正态；数据具有嵌套结构。

**核心R包**：lme4、glmmTMB

```r
# ---- 将 mydata/pass/count/score 替换为变量名，school_id/group_id 替换为分组变量 ----
install_packages('lme4')  # 安装（仅需运行一次）
install_packages('glmmTMB')  # 安装（仅需运行一次）
library(lme4)
# 二分类因变量（逻辑混合模型）
glmm_logit <- glmer(pass ~ score + (1 | school_id), data=mydata, family=binomial)
# 计数因变量（泊松混合模型）
glmm_poisson <- glmer(count ~ x1 + (1 | group_id), data=mydata, family=poisson)
# 过度离散计数（负二项GLMM）
library(glmmTMB)
glmm_nb <- glmmTMB(count ~ x1 + (1 | group_id), data=mydata, family=nbinom2())
# ICC_logit = tau00 / (tau00 + pi^2/3)，pi^2/3约等于3.29
```
**结果解读**：固定效应系数（β 或 exp(B)）解释与普通回归类似，随机效应方差反映组间变异。GLMM 用于计数/二分等非正态因变量，拟合时需检查过离散（overdispersion）。

## 第16章 响应面分析

### 16.1 响应面分析

**方法论说明**：基于多项式回归，检验两个预测变量(X和Y)对结果变量Z的联合效应。相比差异分数法，能同时检验一致性效应和差异性效应，通过3D响应面可视化。RSA还可扩展为包含调节效应（响应面形状随调节变量变化）和中介效应（一致性效应通过中介变量传递）的复杂模型。

**使用条件**：两个连续预测变量和一个连续因变量；样本量建议>150；进行调节/中介扩展时需额外纳入调节变量或中介变量。

**核心R包**：RSA、lavaan、boot

**响应面四参数**：多项式回归的系数组合出四个关键响应面参数，用于解读匹配/不匹配效应：

| 参数 | 定义 | 含义 |
| --- | --- | --- |
| a1 = b1+b2 | 一致线斜率 | X=Y 时，匹配水平高低对 Z 的线性效应（高水平匹配 vs 低水平匹配） |
| a2 = b3+b4+b5 | 一致线曲率 | X=Y 时，匹配对 Z 的非线性（曲率）效应 |
| a3 = b1-b2 | 不一致线斜率 | X≠Y 时，"谁高谁低"的方向性效应（X>Y 与 X<Y 哪个更好） |
| a4 = b3-b4+b5 | 不一致线曲率 | X≠Y 时，不一致程度的非线性效应 |

**一致性 vs 差异性效应判断**：
- **一致性效应**（congruence）：a2 显著为负 → X 与 Y 越一致，结果越有利（倒 U 形，符合人-环境匹配 P-E fit 的核心假设）；a2 显著为正 → 越一致结果越差（U 形）
- **差异性效应**（incongruence/directional）：a3 显著 → "X 高于 Y"与"Y 高于 X"的结果不同，方向性有实质意义（如"期望高于现实"比"现实高于期望"更差）

> OBHRM 典型应用：人-组织匹配（P-O fit）、人-工作匹配（P-J fit）、领导-下属对偶匹配、工作-家庭一致性。RSA 取代了传统差异分数法（X-Y），能同时区分"匹配程度"与"差异方向"两个维度。

#### 16.1.1 基础响应面分析

```r
# ---- 将 z 替换为因变量名，x/y 替换为两个预测变量名，mydata 替换为数据框名 ----
install_packages('RSA')
library(RSA)
rsa_model <- RSA(z ~ x * y, data=mydata)
summary(rsa_model)
compare(rsa_model)  # 比较嵌套模型
RSA.ST(rsa_model)   # 响应面参数：a1(一致线斜率), a2(一致线曲率), a3(不一致线斜率), a4(不一致线曲率)
plot(rsa_model)      # 3D响应面图
# 手动构建多项式回归
mydata$x_sq <- mydata$x^2; mydata$y_sq <- mydata$y^2; mydata$xy <- mydata$x * mydata$y
poly_model <- lm(z ~ x + y + x_sq + xy + y_sq, data=mydata)
```

**结果解读**：RSA.ST() 输出四个响应面参数。解读步骤：① 先看 a2（一致线曲率）——显著为负说明匹配程度越高、结果越有利（P-E fit 的倒 U 假设得到支持）；
② 再看 a3（不一致线斜率）——显著说明方向性差异存在（如"个人期望 > 组织供给"与"组织供给 > 个人期望"结果不同）；③ a1 反映匹配水平高低的线性效应，a4 反映不一致程度的曲率效应。3D 响应面图中，
沿 X=Y 对角线（一致线）的曲线形状对应 a1/a2，沿 X=-Y 对角线（不一致线）对应 a3/a4。

#### 16.1.2 响应面分析的调节效应

```r
# ---- 将 z 替换为因变量，x/y 替换为两个预测变量，w 替换为调节变量，mydata 替换为数据框名 ----
# 调节RSA：检验响应面形状是否随调节变量W变化
# 方法：将W与多项式各项交互，构建含调节项的多项式回归
install_packages('RSA')
install_packages('dplyr')  # 安装（仅需运行一次）
library(RSA)

# >>> 步骤1：中心化所有变量 <<<
mydata$x_c <- scale(mydata$x, scale=FALSE)
mydata$y_c <- scale(mydata$y, scale=FALSE)
mydata$w_c <- scale(mydata$w, scale=FALSE)

# >>> 步骤2：构建多项式项 <<<
mydata$x_sq <- mydata$x_c^2
mydata$y_sq <- mydata$y_c^2
mydata$xy <- mydata$x_c * mydata$y_c

# >>> 步骤3：构建调节交互项（W与多项式各项交互）<<<
mydata$xw  <- mydata$x_c * mydata$w_c
mydata$yw  <- mydata$y_c * mydata$w_c
mydata$xw_sq <- mydata$x_sq * mydata$w_c
mydata$xyw   <- mydata$xy * mydata$w_c
mydata$yw_sq <- mydata$y_sq * mydata$w_c

# >>> 步骤4：拟合含调节的多项式回归 <<<
# 基础模型（无调节）
model_base <- lm(z ~ x_c + y_c + x_sq + xy + y_sq,
                 data=mydata)
# 全调节模型（所有多项式项与W交互）
model_mod <- lm(z ~ x_c + y_c + x_sq + xy + y_sq +
                  w_c + xw + yw + xw_sq + xyw + yw_sq,
                data=mydata)
summary(model_mod)

# >>> 步骤5：模型比较（Delta R-squared检验）<<<
anova(model_base, model_mod)
# p<0.05表示调节效应显著，响应面形状随W变化

# >>> 步骤6：不同W水平下的响应面参数 <<<
# 在W=+1SD和W=-1SD水平下分别计算RSA参数
library(dplyr)
sd_w <- sd(mydata$w, na.rm=TRUE)
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
```
**结果解读**：调节项（W 与多项式项交互）显著说明响应面形状随 W 变化，需在 W 高低水平下分别解读 a1-a4 四个参数。

#### 16.1.3 响应面分析的中介效应

```r
# ---- 将 z 替换为最终因变量，x/y 替换为两个预测变量，m 替换为中介变量，mydata 替换为数据框名 ----
# RSA中介：一致性效应(X与Y的一致性)通过中介M影响Z
# 方法：多项式回归预测M，M再预测Z，形成间接效应
install_packages('lavaan')
install_packages('boot')
library(lavaan)
library(boot)

# >>> 步骤1：构建多项式项 <<<
mydata$x_c <- scale(mydata$x, scale=FALSE)
mydata$y_c <- scale(mydata$y, scale=FALSE)
mydata$x_sq <- mydata$x_c^2
mydata$y_sq <- mydata$y_c^2
mydata$xy <- mydata$x_c * mydata$y_c

# >>> 步骤2：计算一致性/不一致性指标 <<<
# |X-Y|表示一致性程度（绝对差异）
mydata$congruence <- abs(mydata$x_c - mydata$y_c)
# 也可用 (X-Y)^2 表示不一致性
mydata$discrepancy <- (mydata$x_c - mydata$y_c)^2

# >>> 方法A：间接效应 = a(b1+4b2) ， a为X对M的效应，b1为M对Z的效应 <<<
# 使用lavaan路径分析
rsa_med_model <- '
  # a路径：多项式项预测中介M
  m ~ a1 * x_c + a2 * y_c + a3 * x_sq + a4 * xy + a5 * y_sq
  # b和c-prime路径：M和多项式项预测Z
  z ~ cp1 * x_c + cp2 * y_c + cp3 * x_sq + cp4 * xy + cp5 * y_sq
  z ~ b * m
  # 间接效应（一致性效应通过M传递）
  # 一致线上的间接效应 = (a1+a2) * b
  ind_congruence := (a1 + a2) * b
  # 不一致线上的间接效应 = (a1-a2) * b
  ind_discrepancy := (a1 - a2) * b
  # 总间接效应
  ind_total := ind_congruence + ind_discrepancy
'
fit_med <- sem(rsa_med_model, data=mydata, se='boot', bootstrap=1000)
summary(fit_med, fit.measures=TRUE, standardized=TRUE, ci=TRUE)

# >>> 方法B：Bootstrap中介效应检验（更灵活）<<<
rsa_med_boot <- function(data, indices) {
  d <- data[indices, ]
  d$x_c <- scale(d$x, scale=FALSE)
  d$y_c <- scale(d$y, scale=FALSE)
  d$x_sq <- d$x_c^2; d$y_sq <- d$y_c^2; d$xy <- d$x_c * d$y_c
  # a路径：多项式预测M
  a_fit <- lm(m ~ x_c + y_c + x_sq + xy + y_sq, data=d)
  a1 <- coef(a_fit)['x_c']; a2 <- coef(a_fit)['y_c']
  # b路径：M预测Z（控制多项式）
  b_fit <- lm(z ~ x_c + y_c + x_sq + xy + y_sq + m, data=d)
  b <- coef(b_fit)['m']
  # 一致线间接效应 = (a1+a2)*b
  return((a1 + a2) * b)
}
boot_result <- boot(data=mydata, statistic=rsa_med_boot, R=5000)
boot.ci(boot_result, type='bca')
# BCa区间不含0表示RSA中介效应显著
```
**结果解读**：间接效应（一致性通过 M 传递）的 Bootstrap CI 不含 0 说明 RSA 中介成立，即 X-Y 的一致性通过 M 影响 Z。

## 第17章 元分析

### 17.1 元分析

**方法论说明**：定量综合多个独立研究的结果。固定效应模型假设所有研究共享同一真实效应；随机效应模型允许效应在研究间变化（更常用）。OBHRM 中用于整合某一关系（如领导力与绩效、工作满意度与离职）的跨研究证据，估计总体效应并检验潜在调节变量。

**使用条件**：至少2个独立研究的效应量数据；效应量可转换为共同指标（SMD/OR/RD等）。

**核心R包**：metafor

```r
# ============================================================
# 元分析 — metafor包
# ============================================================
# 定量综合多个独立研究的结果
# 固定效应：所有研究共享同一真实效应
# 随机效应：允许效应在研究间变化（更常用）
# ============================================================

# ---- 安装并加载包 ----
install_packages('metafor')  # 元分析包
library(metafor)              # 加载metafor

# ---- 将 mean_treatment/sd_treatment 等替换为变量名 ----

# 步骤1：计算效应量（标准化均数差SMD）
mydata <- escalc(measure='SMD',                # 效应量类型
                 m1i=mean_treatment, m2i=mean_control,  # 组1/组2均值
                 sd1i=sd_treatment, sd2i=sd_control,    # 组1/组2标准差
                 n1i=n_treatment, n2i=n_control,         # 组1/组2样本量
                 data=mydata)

# 步骤2：拟合随机效应模型
re_model <- rma(yi, vi, data=mydata, method='REML')
summary(re_model)  # 输出合并效应量、置信区间、I2（异质性）

# 步骤3：森林图
forest(re_model)  # 各研究效应量和合并效应的可视化

# 步骤4：漏斗图+ Egger检验（发表偏倚检验）
funnel(re_model)                    # 漏斗图（应对称）
regtest(re_model, model='lm')       # Egger检验 p>0.05无发表偏倚
```

**结果解读**：re_model的p值表示合并效应量是否显著。Q检验p<0.05表示存在异质性（各研究效应不同质）。I-squared：25%低/50%中/75%高异质性。I-squared高时应使用随机效应模型并探索调节变量。
funnel()对称表示无发表偏倚，regtest()的Egger检验p<0.05提示存在偏倚。subgroup分析的mods系数p<0.05表示该调节变量显著解释异质性来源。

### 17.2 SEM元分析

**方法论说明**：SEM元分析（Meta-Analytic Structural Equation Modeling, MASEM）将元分析与结构方程模型结合，用于综合多项研究所报告的相关矩阵或协方差矩阵，拟合统一的SEM模型。
两阶段法（TSSEM）由Cheung & Chan(2005)提出：第一阶段（tssem1）合成各研究的相关/协方差矩阵（固定效应或随机效应），第二阶段（tssem2）在合并后的矩阵上拟合SEM模型。metaSEM包是R中MASEM的标准工具。

**使用条件**：需收集多项研究的相关矩阵或协方差矩阵；至少5项研究；每项研究需报告完整的变量间相关系数或协方差。

**核心R包**：metaSEM

```r
# ---- 将 mydata 替换为包含各研究相关矩阵的列表 ----
install_packages('metaSEM')  # 安装（仅需运行一次）
library(metaSEM)

# >>> 数据准备 <<<
# MASEM需要每项研究的相关矩阵（或协方差矩阵）和样本量
# 数据格式：list of matrices + n vector
# 示例数据：Digman97（metaSEM自带，大五人格相关矩阵）
# ---- 如用自己的数据，将 Digman97 替换为你的数据对象 ----
data(Digman97)
head(Digman97$data)  # 查看各研究的相关矩阵
head(Digman97$n)     # 查看各研究的样本量

# >>> 第一阶段：合成相关矩阵 <<<
# 固定效应模型（FEM）- 假设所有研究共享同一相关矩阵
fixed1 <- tssem1(Cov=Digman97$data, n=Digman97$n, method='FEM')
summary(fixed1)
# 查看合并后的相关矩阵
coef(fixed1)  # 合并后的相关系数矩阵

# 随机效应模型（REM）- 允许各研究相关矩阵有变异
random1 <- tssem1(Cov=Digman97$data, n=Digman97$n, method='REM')
summary(random1)
# 检查异质性：Tau2显著表示各研究间有显著变异

# >>> 第二阶段：在合并矩阵上拟合SEM <<<
# 定义SEM模型（使用lavaan语法）
# ---- 将模型定义替换为你的理论模型 ----
model <- '
  # 测量模型：两个高阶因子
  Alpha =~ A + C + ES      # Alpha因子（宜人性、尽责性、情绪稳定性）
  Beta  =~ E + I            # Beta因子（外向性、开放性）
  # 结构模型
  Alpha ~~ Beta            # 两个因子相关
'
# 将lavaan语法转换为RAM格式
RAM1 <- lavaan2RAM(model, obs.variables=c('A','C','ES','E','I'))

# 在第一阶段结果上拟合SEM（第二阶段）
fixed2 <- tssem2(fixed1, RAM=RAM1, intervals='LB',
                 model.name='TSSEM2 Fixed')
summary(fixed2)
# 输出：路径系数（因子载荷和因子间相关）及其置信区间

# 随机效应模型的第二阶段
random2 <- tssem2(random1, RAM=RAM1, intervals='LB',
                  model.name='TSSEM2 Random')
summary(random2)

# >>> 模型比较 <<<
# 比较固定效应和随机效应模型的拟合
# 固定效应：假设所有研究效应同质
# 随机效应：允许研究间变异
# 若随机效应模型的Tau2显著，应使用随机效应结果

# >>> 一阶段法（OSMASEM）<<<
# OSMASEM将两个阶段合并，同时估计合并矩阵和SEM参数
# 优势：可加入研究水平的调节变量
# ---- 将 Nohe15 替换为你的数据，moderator 替换为调节变量名 ----
# data(Nohe15)
# osm <- osmasem(model=model, data=Nohe15,
#                moderator=moderator)  # 研究特征作为调节变量
# summary(osm)
```

**结果解读**：第一阶段tssem1输出合并后的相关矩阵。固定效应模型假设各研究同质，随机效应模型允许变异（Tau2显著表示异质性）。第二阶段tssem2输出SEM路径系数：因子载荷表示指标与潜变量的关系强度，因子间相关表示两个构念的关联度。
置信区间(LB法)不含0表示参数显著。OSMASEM一阶段法的优势在于可加入研究特征（如发表年份、样本来源文化）作为调节变量，检验这些特征是否影响SEM路径。Cheung & Chan(2005)建议当研究数>10时使用随机效应TSSEM。

### 17.3 三层元分析

**方法论说明**：三层元分析（Three-Level Meta-Analysis）处理效应量嵌套结构：Level 1=抽样误差，Level 2=研究内效应量变异（同一研究多个效应量），Level 3=研究间变异。传统两层元分析（随机效应模型）忽略了一个研究内多个效应量的依赖性，三层模型显式建模这种嵌套结构。metafor包用rma.mv()实现，metaSEM包用meta3L()实现。

**使用条件**：效应量具有三层嵌套结构（效应量嵌套于研究）；同一研究中有多个效应量；需区分研究内和研究间异质性。

**核心R包**：metafor、metaSEM

```r
# ---- 将 mydata 替换为数据框名，y/v/study_id 替换为变量名 ----
install_packages('metafor')   # 安装（仅需运行一次）
install_packages('metaSEM')   # 安装（仅需运行一次）
library(metafor)
library(metaSEM)

# >>> 方法1：metafor的rma.mv() <<<
# 三层结构：效应量(y)嵌套于研究(study_id)
# ---- 将 y 替换为效应量列，v 替换为方差列，study_id 替换为研究ID列 ----
# 设置三层结构：Level 1=抽样误差(隐含), Level 2=研究内, Level 3=研究间
model_3level <- rma.mv(y=y, V=v,                  # 效应量和方差
                       random=list(~1 | study_id,  # Level 3: 研究间随机效应
                                  ~1 | effect_id), # Level 2: 研究内随机效应
                       data=mydata)
summary(model_3level)
# 输出： Intercept(合并效应量), sigma2.1(研究间方差), sigma2.2(研究内方差)

# 计算各层I2（异质性比例）
W <- diag(1/mydata$v)  # 权重矩阵
X <- model.matrix(model_3level)
P <- W - W %*% X %*% solve(t(X) %*% W %*% X) %*% t(X) %*% W
# 总变异
total_var <- sum(model_3level$sigma2)
# I2 Level 2 (研究内)
I2_level2 <- 100 * model_3level$sigma2[2] / 
             (model_3level$sigma2[1] + model_3level$sigma2[2] + 
              sum(diag(P))/(nrow(mydata) - ncol(X)))
# I2 Level 3 (研究间)
I2_level3 <- 100 * model_3level$sigma2[1] / 
             (model_3level$sigma2[1] + model_3level$sigma2[2] + 
              sum(diag(P))/(nrow(mydata) - ncol(X)))
cat(sprintf('I2 Level 2 (within): %.2f%%\n', I2_level2))
cat(sprintf('I2 Level 3 (between): %.2f%%\n', I2_level3))

# 加入调节变量（元回归）
# ---- 将 moderator 替换为你的调节变量名 ----
model_mod <- rma.mv(y=y, V=v, mods=~moderator,
                    random=list(~1 | study_id, ~1 | effect_id),
                    data=mydata)
summary(model_mod)  # moderator系数p<0.05表示调节效应显著

# >>> 方法2：metaSEM的meta3L() <<<
# 使用metaSEM内置数据Cooper03（三层结构）
# ---- 如用自己的数据，替换 Cooper03 ----
data(Cooper03)
head(Cooper03)
# 三层元分析：y=效应量, v=方差, cluster=研究聚类
model_meta3L <- meta3L(y=y, v=v, cluster=District, data=Cooper03)
summary(model_meta3L)
# 输出：Intercept(合并效应量), Tau2_2(研究内方差), Tau2_3(研究间方差)
# I2_2: 研究内异质性比例; I2_3: 研究间异质性比例

# 加入协变量
model_meta3L_cov <- meta3L(y=y, v=v, cluster=District,
                           x=scale(Year, scale=FALSE), data=Cooper03)
summary(model_meta3L_cov)
# R2: 协变量解释的各层异质性比例

# >>> 模型比较：两层 vs 三层 <<<
model_2level <- meta(y=y, v=v, data=Cooper03, 
                     model.name='2 level', silent=TRUE)
model_3level_m <- meta3L(y=y, v=v, cluster=District, data=Cooper03,
                        model.name='3 level', silent=TRUE)
anova(model_3level_m, model_2level)  # 显著表示三层模型更优

# >>> 森林图 <<<
# forest(model_3level)  # 按研究分层的森林图
```

**结果解读**：rma.mv()输出中sigma2.1为研究间方差（Level 3），sigma2.2为研究内方差（Level 2）。I2 Level 2表示研究内效应量异质性占比，I2 Level 3表示研究间异质性占比。
meta3L()输出Tau2_2(研究内)和Tau2_3(研究间)，I2_2和I2_3为对应异质性比例。模型比较：anova()显著（p<0.05）表示三层模型优于两层模型，即研究内效应量间确实存在依赖性需要建模。调节变量系数显著表示该变量解释了部分异质性。
Assink & Wibbelink(2016)建议当同一研究有多个效应量时必须使用三层模型。

## 第18章 社会网络分析

### 18.1 社会网络分析

**方法论说明**：SNA 把分析单元从"个体属性"转向"关系结构"。输入为**行动者—关系**数据（边表：from→to，可选 weight）。核心指标：度中心性（直接联系数，越核心越枢纽）、介数中心性（作为最短路径桥梁的次数，控制信息流）、接近中心性（到其余节点的平均距离）；社群检测（walktrap）揭示潜在派系；密度与平均路径刻画整体连通性。

**使用条件**：关系 / 网络数据（团队沟通、知识扩散、组织建言网络、引文网络等）；研究"位置 / 结构"而非仅"属性"。

**核心R包**：`igraph`（网络构建与指标）、`ggraph`（可视化）。

**R 示例（指向脚本 `../../../r-analysis/scripts/18-sna/18.1.R`）**：

```r
# ---- 数据要求：边表（from / to / 可选 weight）----
library(igraph)

# 读边表（CSV：from,to,weight）→ 构网
edges <- read.csv("edges.csv", fileEncoding="UTF-8", stringsAsFactors=FALSE)
g <- graph_from_data_frame(edges, directed = FALSE)  # 无向网络示例

# 中心性指标
V(g)$degree  <- degree(g)            # 度中心性：直接联系数（越核心越枢纽）
V(g)$between <- betweenness(g)       # 介数中心性：作为最短路径桥梁的次数
V(g)$close   <- closeness(g)         # 接近中心性：到其余节点平均距离的倒数

# 社群检测（walktrap）
set.seed(42)
wc <- cluster_walktrap(g)
V(g)$community <- membership(wc)

# 整体连通性
cat("密度:", edge_density(g), "\n")
cat("平均路径长度:", mean_distance(g), "\n")
cat("直径:", diameter(g), "\n")

# 可视化（ggraph 或 igraph 自带）
# library(ggraph); ggraph(g, layout='fr') + geom_edge_link() + geom_node_point()
plot(g, vertex.size=8, vertex.color=V(g)$community, edge.width=E(g)$weight)
```

**结果解读**：SNA 把分析单元从"个体属性"转向"关系结构"。输入为**行动者—关系**数据（边表：from→to，可选 weight）。**核心指标**：①度中心性（degree，直接联系数，越核心越枢纽）；
②介数中心性（betweenness，作为最短路径桥梁的次数，控制信息流）；③接近中心性（closeness，到其余节点平均距离的倒数）。**社群检测**（walktrap 是一种基于随机游走的算法）揭示潜在派系；
**密度**（实际边数 / 最大可能边数）与**平均路径长度**刻画整体连通性。**R 实现**：`igraph`（网络构建与指标） + `ggraph`（可视化）。**应用场景**：团队沟通网络、知识扩散、组织建言网络、引文网络。**结果关注**：
谁是枢纽（高介数）、谁在边缘（低度）、是否存在派系结构（社群检测模块度）、整体连通密度。
## 第19章 大语言模型分析

### 19.1 本地大语言模型分析

**方法论说明（可选功能，默认不启用）**：Ollama是本地运行大语言模型的工具，支持llama3.2、qwen2.5、mistral等开源模型。R通过httr包调用Ollama REST API实现文本生成、对话、情感分析、摘要等NLP任务，数据不离开本机，适合隐私敏感研究。需用户在本机自行安装并启动 Ollama 后方可使用。

**使用条件**：需安装Ollama应用并下载模型；本地硬件需足够（建议8GB+内存）。

**核心R包**：httr、jsonlite

```r
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
#   方法1：文本生成（单次问答）
#   方法2：对话模式（多轮对话）
#   方法3：批量文本分析（批量情感分析）
#   方法4：嵌入向量生成（文本向量化）
# ============================================================

# ---- 安装并加载包（仅需运行一次） ----
install_packages('httr')      # HTTP请求包
install_packages('jsonlite')   # JSON解析包
library(httr)                  # 加载httr
library(jsonlite)              # 加载jsonlite

# ============================================================
# 配置连接
# ============================================================
# Ollama默认运行在本地11434端口
ollama_url <- 'http://127.0.0.1:11434'

# ---- 将 llama3.2 替换为已下载的模型名 ----
# ---- 将 prompt_text 替换为你的提示文本 ----

# ============================================================
# 方法1：文本生成（单次问答）
# ============================================================
# POST /api/generate：向模型发送提示，获取生成结果
# stream=FALSE：等待完整响应（非流式）
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

# ============================================================
# 方法2：对话模式（多轮对话）
# ============================================================
# POST /api/chat：支持system/user/assistant多角色对话
# system角色：设定模型行为（如"你是文本分析助手"）
# user角色：用户输入
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

# ============================================================
# 方法3：批量文本分析
# ============================================================
# 对多段文本逐一调用模型进行分析
# ---- 将 texts 替换为你的文本向量（字符型） ----
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
analysis_df <- data.frame(text=texts, analysis=unlist(results))
print(analysis_df)  # 输出每段文本的分析结果

# ============================================================
# 方法4：嵌入向量生成（文本向量化）
# ============================================================
# POST /api/embeddings：将文本转为高维数值向量
# 用途：文本相似度计算、聚类、分类的特征输入
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
```

**结果解读**：generate API的response字段包含模型生成的文本。chat API支持多轮对话。嵌入向量将文本映射为高维数值向量，可用于相似度计算、聚类或ML模型输入。本地LLM优势：数据不离开本机、无API费用。模型选择：llama3.2通用，qwen2.5中文优秀，mistral轻量。


## 第20章 混合研究方法分析

### 20.1 混合方法

**方法论说明**：混合方法是**研究设计范式**而非单一统计技术，核心是用"量化铺面 + 质性深挖"或"算法与人工互补"来抵消单一方法的局限。常见设计：探索性序列（先质后量）、解释性序列（先量后质）、并行三角（同时收集）。在 OBHRM 中常用于：量表开发（量化验证 + 质性题项生成）、机制解释（量化显著效应再用访谈解释"为何"）、跨文化适配。

**使用条件**：单一方法不足以回答研究问题；需同时获得广度（代表性）与深度（机制 / 意义）；资源允许双轨收集。

**R 衔接**：量化侧使用本手册各章（描述 / 回归 / SEM / 多层等）；质性侧使用本章 4.1 `RQDA`（扎根理论）以及定性研究路径（`../../qualitative/qualitative.md`，Q1–Q5 三级编码→理论饱和）。二者通过"研究问题—抽样—数据—结论"的对接表衔接，无单一 R 脚本，按设计分别调用对应模块。

**结果解读**：混合方法的价值在于"互补与三角验证"，报告须说明设计类型、量化与质性各自的抽样与效度、以及二者如何整合（衔接 / 解释 / 扩证）。


