# 统计可视化标准

学术论文统计可视化参考指南。涵盖 APA 7.0 图件规范、无障碍配色方案、图表类型选择、常见误区和代码模板。

---

**目录**

- [APA 7.0 图件规范（第7章摘要）](#APA-70-图件规范第7章摘要)
  - [通用原则](#通用原则)
  - [图题格式](#图题格式)
  - [字体规范](#字体规范)
  - [必备要素](#必备要素)
- [无障碍配色方案](#无障碍配色方案)
  - [主色：Viridis（感知均匀）](#主色viridis感知均匀)
  - [替代色：Cividis（红绿色盲优化）](#替代色cividis红绿色盲优化)
  - [分类色：Tol 定性配色（最多8类）](#分类色tol-定性配色最多8类)
  - [发散色：蓝-红（用于相关/差异图）](#发散色蓝-红用于相关差异图)
  - [无障碍规则](#无障碍规则)
- [图表类型决策树](#图表类型决策树)
  - [不同数据用什么图？](#不同数据用什么图)
  - [何时不应可视化](#何时不应可视化)
- [常见误区](#常见误区)
  - [严重错误（绝对禁止）](#严重错误绝对禁止)
  - [细微错误（容易忽略）](#细微错误容易忽略)
- [Python matplotlib 代码模板](#python-matplotlib-代码模板)
  - [模板1：条形图](#模板1条形图)
  - [模板2：箱线图](#模板2箱线图)
  - [模板3：折线图（趋势）](#模板3折线图趋势)
  - [模板4：散点图 + 回归线](#模板4散点图--回归线)
  - [模板5：森林图（元分析）](#模板5森林图元分析)
  - [模板6：相关矩阵热图](#模板6相关矩阵热图)
  - [模板7：漏斗图](#模板7漏斗图)
  - [模板8：分组条形图](#模板8分组条形图)
- [R ggplot2 代码模板](#r-ggplot2-代码模板)
  - [模板1：条形图](#模板1条形图)
  - [模板2：箱线图](#模板2箱线图)
  - [模板3：折线图（趋势）](#模板3折线图趋势)
  - [模板4：散点图 + 回归线](#模板4散点图--回归线)
  - [模板5：森林图](#模板5森林图)
  - [模板6：相关矩阵热图](#模板6相关矩阵热图)
  - [模板7：漏斗图](#模板7漏斗图)
  - [模板8：分组条形图](#模板8分组条形图)
  - [单图](#单图)
  - [多子图](#多子图)
  - [全页横排图](#全页横排图)

## APA 7.0 图件规范（第7章摘要）

### 通用原则

1. **每幅图必须有附加价值**——不要用可视化呈现用一句话或表格更能表达的数据
2. **图件按顺序编号**（图1、图2……），按首次提及顺序
3. **每幅图必须在正文中引用**（"如图1所示……"）
4. **图题位于图下方**（与表格注释位于上方不同）
5. **图件必须可独立理解**——在图题中包含全部必要上下文，无需阅读正文

### 图题格式

```
图 [N] ← 加粗，单独一行
[描述性标题] ← 斜体，句首大写，下一行
注。[如需解释] ← 普通字体，以"注。"开头
```

### 字体规范

| 要素 | 字号 | 样式 |
|------|------|------|
| 图标签（"图1"） | 10-12磅 | 加粗 |
| 图标题 | 10-12磅 | 斜体 |
| 坐标轴标签 | 8-10磅 | 普通，句首大写 |
| 坐标轴刻度标签 | 8-9磅 | 普通 |
| 图例文字 | 8-9磅 | 普通 |
| 注释文字 | 8磅 | 普通或斜体 |
| 注记文字 | 8-9磅 | 普通 |

### 必备要素

- [ ] 坐标轴标签（两个轴，描述性，含单位）
- [ ] 刻度线和刻度标签
- [ ] 图例（多组图件）
- [ ] 误差条或置信区间（均值比较）
- [ ] 比例尺（图像/地图）
- [ ] 含图编号+标题的图题
- [ ] 注记（如需解释）

---

## 无障碍配色方案

### 主色：Viridis（感知均匀）

最适合：连续/顺序数据。

| 索引 | 十六进制码 | 用途 |
|-------|----------|------|
| 0 | `#440154` | 最深值 |
| 1 | `#46327E` | |
| 2 | `#365C8D` | |
| 3 | `#277F8E` | |
| 4 | `#1FA187` | |
| 5 | `#4AC16D` | |
| 6 | `#9FDA3A` | |
| 7 | `#FDE725` | 最浅值 |

### 替代色：Cividis（红绿色盲优化）

最适合：色盲无障碍要求高的出版物。

| 索引 | 十六进制码 |
|-------|----------|
| 0 | `#00204D` |
| 1 | `#00336F` |
| 2 | `#39486B` |
| 3 | `#5F5D6A` |
| 4 | `#7B7463` |
| 5 | `#9A8C4F` |
| 6 | `#BBA634` |
| 7 | `#DEC000` |
| 8 | `#FFE945` |

### 分类色：Tol 定性配色（最多8类）

最适合：分类比较、组标签。

| 标签 | 十六进制码 | 示例用途 |
|-------|----------|----------|
| 蓝 | `#0077BB` | 组1 / 基线 |
| 青 | `#33BBEE` | 组2 |
| 茶绿 | `#009988` | 组3 |
| 橙 | `#EE7733` | 组4 / 高亮 |
| 红 | `#CC3311` | 组5 / 警示 |
| 洋红 | `#EE3377` | 组6 |
| 灰 | `#BBBBBB` | 参照 / 不适用 |
| 黑 | `#000000` | 轮廓 / 文字 |

### 发散色：蓝-红（用于相关/差异图）

| 负值 | 零 | 正值 |
|-------|-----|-------|
| `#2166AC` | `#F7F7F7` | `#B2182B` |
| `#4393C3` | | `#D6604D` |
| `#92C5DE` | | `#F4A582` |

### 无障碍规则

1. 永远不要只靠颜色——配合形状、图案或标签
2. 最小对比度：3:1（WCAG AA 非文本要素）
3. 定稿前用色盲模拟器测试
4. 灰度打印时，图案或标签仍须能区分组别

---

## 图表类型决策树

### 不同数据用什么图？

| 你的数据 | 你的问题 | 推荐图表 | 避免 |
|----------|----------|----------|------|
| 类别 + 数值 | 比较大小 | **条形图**（垂直或水平） | 饼图 |
| 类别 + 数值 + 组别 | 跨组比较 | **分组条形图**或**堆叠条形图** | 3D条形图 |
| 连续变量，1组 | 展示分布 | **直方图** + 密度曲线 | |
| 连续变量，2-5组 | 比较分布 | **箱线图**或**小提琴图** | 仅均值条形图 |
| 两个连续变量 | 展示关系 | **散点图** + 回归线 | |
| 时间序列（1-5个序列） | 展示趋势 | **折线图** | 时间序列用条形图 |
| 时间序列（>5个序列） | 展示趋势 | **小倍数图**（分面折线图） | 面条图 |
| 相关矩阵 | 展示多变量关系 | **热图** | 散点图矩阵（过密） |
| 效应量 + 置信区间（元分析） | 汇总元分析 | **森林图** | 条形图 |
| 效应量 + 标准误（元分析） | 检查发表偏差 | **漏斗图** | |
| 概念 + 关系 | 映射理论框架 | **网络图** / **概念图** | |
| 合计为100%的比例 | 展示构成 | **堆叠条形图** | 饼图 |
| 地理数据 | 展示空间模式 | **choropleth地图** | |

### 何时不应可视化

- 少于3个数据点（用文字或表格）
- 单个百分比或均值（在正文中说明）
- 需要超过2句话来解释图表的数字（用表格）
- 与表格中数据重复的可视化

---

## 常见误区

### 严重错误（绝对禁止）

| 误区 | 问题 | 修正 |
|------|------|------|
| **饼图** | 人类感知不擅长比较角度/面积 | 用条形图 |
| **3D图表** | 透视投影扭曲数值 | 用2D |
| **双Y轴** | 暗示虚假相关；尺度选择任意 | 用两个独立面板 |
| **彩虹色图** | 非感知均匀；不安全 for 色盲 | 用viridis/cividis |
| **截断Y轴**（未标记） | 夸大微小差异 | 从0开始或清晰标记断点 |
| **缺失误差条** | 隐藏不确定性；读者无法评估显著性 | 添加标准误、标准差或95%置信区间条 |
| **图表垃圾**（装饰性元素） | 降低数据油墨比；干扰数据 | 删除不必要元素 |

### 细微错误（容易忽略）

| 误区 | 问题 | 修正 |
|------|------|------|
| 直方图组距不等 | 扭曲频率感知 | 用等宽组距 |
| 标签重叠 | 打印尺寸下不可读 | 旋转、缩写或减少类别 |
| 颜色过多（>8种） | 打印尺寸下无法区分 | 合并类别或用分面 |
| 图例远离数据 | 读者必须来回扫视 | 将图例置于绘图区内或用直接标签 |
| 纵横比失真 | 夸大或缩小趋势 | 默认4:3；时间序列用16:9 |

---

## Python matplotlib 代码模板

### 模板1：条形图

```python
import matplotlib.pyplot as plt
import numpy as np

# APA 7.0 设置
plt.rcParams.update({
 'font.family': 'sans-serif',
 'font.sans-serif': ['Arial', 'Helvetica', 'DejaVu Sans'],
 'font.size': 9, 'axes.titlesize': 11, 'axes.labelsize': 10,
 'xtick.labelsize': 8, 'ytick.labelsize': 8, 'legend.fontsize': 8,
 'figure.dpi': 300, 'savefig.dpi': 300, 'savefig.bbox': 'tight',
 'axes.spines.top': False, 'axes.spines.right': False,
})
CB = ['#0077BB', '#33BBEE', '#009988', '#EE7733', '#CC3311', '#EE3377']

# 数据
categories = ['高LMX', '低LMX', '高TFL', '低TFL']
values = [4.2, 3.8, 5.1, 4.5]
errors = [0.3, 0.4, 0.2, 0.5]

fig, ax = plt.subplots(figsize=(6.9, 4.5))
bars = ax.bar(categories, values, yerr=errors, capsize=4,
 color=CB[:len(categories)], edgecolor='black', linewidth=0.5)
ax.set_ylabel('均值 (1-5)')
ax.set_xlabel('组别')
ax.set_ylim(0, max(values) * 1.3)

plt.tight_layout()
plt.savefig('figure_01.pdf', format='pdf')
plt.savefig('figure_01.png', format='png')
plt.show()
```

### 模板2：箱线图

```python
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams.update({
 'font.family': 'sans-serif', 'font.size': 9, 'axes.labelsize': 10,
 'figure.dpi': 300, 'axes.spines.top': False, 'axes.spines.right': False,
})
CB = ['#0077BB', '#33BBEE', '#009988', '#EE7733']

# 数据（替换为实际数据）
np.random.seed(42)
data = [np.random.normal(loc, 1, 50) for loc in [3.5, 4.0, 3.8, 4.5]]
labels = ['国企', '民企', '科技创业公司', '跨国公司']

fig, ax = plt.subplots(figsize=(6.9, 4.5))
bp = ax.boxplot(data, labels=labels, patch_artist=True, widths=0.6,
 medianprops=dict(color='black', linewidth=1.5))
for patch, color in zip(bp['boxes'], CB):
 patch.set_facecolor(color)
 patch.set_alpha(0.7)

ax.set_ylabel('工作满意度 (1-5)')
ax.set_xlabel('组织类型')
plt.tight_layout()
plt.savefig('figure_02.pdf', format='pdf')
plt.show()
```

### 模板3：折线图（趋势）

```python
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams.update({
 'font.family': 'sans-serif', 'font.size': 9, 'axes.labelsize': 10,
 'figure.dpi': 300, 'axes.spines.top': False, 'axes.spines.right': False,
})
CB = ['#0077BB', '#CC3311', '#009988']

years = [2018, 2019, 2020, 2021, 2022, 2023]
series_a = [72, 75, 68, 71, 78, 82]
series_b = [65, 63, 60, 58, 55, 52]

fig, ax = plt.subplots(figsize=(6.9, 4.5))
ax.plot(years, series_a, 'o-', color=CB[0], label='国企员工', linewidth=1.5, markersize=5)
ax.plot(years, series_b, 's--', color=CB[1], label='民企员工', linewidth=1.5, markersize=5)
ax.set_xlabel('年份')
ax.set_ylabel('离职率 (%)')
ax.legend(frameon=False)
ax.set_xlim(min(years) - 0.5, max(years) + 0.5)

plt.tight_layout()
plt.savefig('figure_03.pdf', format='pdf')
plt.show()
```

### 模板4：散点图 + 回归线

```python
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats

plt.rcParams.update({
 'font.family': 'sans-serif', 'font.size': 9, 'axes.labelsize': 10,
 'figure.dpi': 300, 'axes.spines.top': False, 'axes.spines.right': False,
})

# 数据
np.random.seed(42)
x = np.random.uniform(10, 50, 80)
y = 0.6 * x + np.random.normal(0, 5, 80) + 10

slope, intercept, r, p, se = stats.linregress(x, y)
x_line = np.linspace(min(x), max(x), 100)
y_line = slope * x_line + intercept

fig, ax = plt.subplots(figsize=(6.9, 5.5))
ax.scatter(x, y, color='#0077BB', alpha=0.6, edgecolors='black', linewidth=0.3, s=30)
ax.plot(x_line, y_line, color='#CC3311', linewidth=1.5,
 label=f'y = {slope:.2f}x + {intercept:.2f}, r = {r:.2f}, p < .001')
ax.set_xlabel('LMX质量')
ax.set_ylabel('员工投入度')
ax.legend(frameon=False, loc='lower right')

plt.tight_layout()
plt.savefig('figure_04.pdf', format='pdf')
plt.show()
```

### 模板5：森林图（元分析）

```python
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams.update({
 'font.family': 'sans-serif', 'font.size': 9, 'axes.labelsize': 10,
 'figure.dpi': 300,
})

studies = ['研究1', '研究2', '研究3',
 '研究4', '研究5', '总体']
effects = [0.35, 0.42, 0.28, 0.51, 0.38, 0.39]
ci_lower = [0.15, 0.22, 0.08, 0.31, 0.18, 0.27]
ci_upper = [0.55, 0.62, 0.48, 0.71, 0.58, 0.51]

fig, ax = plt.subplots(figsize=(6.9, 4.0))
y_pos = np.arange(len(studies))

for i, study in enumerate(studies):
 color = '#CC3311' if study == '总体' else '#0077BB'
 marker = 'D' if study == '总体' else 'o'
 size = 8 if study == '总体' else 6
 ax.errorbar(effects[i], i, xerr=[[effects[i]-ci_lower[i]], [ci_upper[i]-effects[i]]],
 fmt=marker, color=color, markersize=size, capsize=3, linewidth=1.2)

ax.axvline(x=0, color='grey', linestyle='--', linewidth=0.8)
ax.set_yticks(y_pos)
ax.set_yticklabels(studies)
ax.set_xlabel("效应量 (Cohen's d)")
ax.invert_yaxis()
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

plt.tight_layout()
plt.savefig('figure_05.pdf', format='pdf')
plt.show()
```

### 模板6：相关矩阵热图

```python
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

plt.rcParams.update({
 'font.family': 'sans-serif', 'font.size': 9,
 'figure.dpi': 300,
})

# 相关矩阵
labels = ['变革型领导', '赋能型LMX', '信任', '投入度', '绩效']
corr = np.array([
 [1.00, 0.45, 0.32, 0.67, 0.55],
 [0.45, 1.00, 0.28, 0.38, 0.30],
 [0.32, 0.28, 1.00, 0.41, 0.35],
 [0.67, 0.38, 0.41, 1.00, 0.72],
 [0.55, 0.30, 0.35, 0.72, 1.00],
])

fig, ax = plt.subplots(figsize=(5.5, 5.0))
mask = np.triu(np.ones_like(corr, dtype=bool), k=1)
sns.heatmap(corr, mask=mask, annot=True, fmt='.2f', cmap='RdBu_r',
 center=0, vmin=-1, vmax=1, square=True,
 xticklabels=labels, yticklabels=labels,
 linewidths=0.5, cbar_kws={'shrink': 0.8, 'label': 'r'}, ax=ax)

plt.tight_layout()
plt.savefig('figure_06.pdf', format='pdf')
plt.show()
```

### 模板7：漏斗图

```python
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams.update({
 'font.family': 'sans-serif', 'font.size': 9, 'axes.labelsize': 10,
 'figure.dpi': 300, 'axes.spines.top': False, 'axes.spines.right': False,
})

# 数据
np.random.seed(42)
effects = np.random.normal(0.4, 0.15, 20)
se = np.random.uniform(0.05, 0.25, 20)
mean_effect = np.mean(effects)

fig, ax = plt.subplots(figsize=(6.9, 5.0))
ax.scatter(effects, se, color='#0077BB', edgecolors='black', linewidth=0.3, s=40, alpha=0.7)
ax.axvline(x=mean_effect, color='#CC3311', linestyle='--', linewidth=1, label=f'均值 = {mean_effect:.2f}')

# 漏斗边界（95% CI）
se_range = np.linspace(0.01, max(se) * 1.1, 100)
ax.fill_betweenx(se_range, mean_effect - 1.96 * se_range, mean_effect + 1.96 * se_range,
 alpha=0.1, color='grey', label='95% CI')

ax.set_xlabel("效应量 (Cohen's d)")
ax.set_ylabel('标准误')
ax.invert_yaxis()
ax.legend(frameon=False)

plt.tight_layout()
plt.savefig('figure_07.pdf', format='pdf')
plt.show()
```

### 模板8：分组条形图

```python
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams.update({
 'font.family': 'sans-serif', 'font.size': 9, 'axes.labelsize': 10,
 'figure.dpi': 300, 'axes.spines.top': False, 'axes.spines.right': False,
})
CB = ['#0077BB', '#EE7733', '#009988']

categories = ['培训', '薪酬', '工作设计', '发言权']
group_a = [4.1, 3.5, 3.8, 3.2]
group_b = [3.8, 4.2, 3.5, 3.0]
group_c = [4.3, 3.9, 4.0, 3.5]

x = np.arange(len(categories))
width = 0.25

fig, ax = plt.subplots(figsize=(6.9, 4.5))
ax.bar(x - width, group_a, width, label='国企', color=CB[0], edgecolor='black', linewidth=0.5)
ax.bar(x, group_b, width, label='民企', color=CB[1], edgecolor='black', linewidth=0.5)
ax.bar(x + width, group_c, width, label='跨国公司', color=CB[2], edgecolor='black', linewidth=0.5)

ax.set_xlabel('HR实践')
ax.set_ylabel('均值 (1-5)')
ax.set_xticks(x)
ax.set_xticklabels(categories)
ax.set_ylim(0, 5.5)
ax.legend(frameon=False)

plt.tight_layout()
plt.savefig('figure_08.pdf', format='pdf')
plt.show()
```

---

## R ggplot2 代码模板

### 模板1：条形图

```r
library(ggplot2)

theme_apa <- theme_minimal(base_size = 10, base_family = "Arial") +
 theme(
 plot.title = element_text(size = 11, face = "bold", hjust = 0),
 axis.title = element_text(size = 10),
 axis.text = element_text(size = 8),
 legend.title = element_text(size = 9),
 legend.text = element_text(size = 8),
 panel.grid.minor = element_blank(),
 panel.grid.major.x = element_blank(),
 strip.text = element_text(size = 9, face = "bold")
 )
cb_palette <- c("#0077BB", "#33BBEE", "#009988", "#EE7733", "#CC3311", "#EE3377")

df <- data.frame(
 group = c("高LMX", "低LMX", "高TFL", "低TFL"),
 value = c(4.2, 3.8, 5.1, 4.5),
 se = c(0.3, 0.4, 0.2, 0.5)
)

ggplot(df, aes(x = group, y = value, fill = group)) +
 geom_col(color = "black", linewidth = 0.3, width = 0.7) +
 geom_errorbar(aes(ymin = value - se, ymax = value + se), width = 0.2) +
 scale_fill_manual(values = cb_palette) +
 labs(x = "组别", y = "均值 (1-5)") +
 theme_apa +
 theme(legend.position = "none") +
 coord_cartesian(ylim = c(0, NA))

ggsave("figure_01.pdf", width = 6.9, height = 4.5, units = "in", dpi = 300)
```

### 模板2：箱线图

```r
library(ggplot2)

theme_apa <- theme_minimal(base_size = 10, base_family = "Arial") +
 theme(
 axis.title = element_text(size = 10), axis.text = element_text(size = 8),
 panel.grid.minor = element_blank(), panel.grid.major.x = element_blank()
 )
cb_palette <- c("#0077BB", "#33BBEE", "#009988", "#EE7733")

set.seed(42)
df <- data.frame(
 type = rep(c("国企", "民企", "科技创业公司", "跨国公司"), each = 50),
 score = c(rnorm(50, 3.5, 1), rnorm(50, 4.0, 1), rnorm(50, 3.8, 1), rnorm(50, 4.5, 1))
)

ggplot(df, aes(x = type, y = score, fill = type)) +
 geom_boxplot(alpha = 0.7, outlier.shape = 21, outlier.size = 1.5) +
 scale_fill_manual(values = cb_palette) +
 labs(x = "组织类型", y = "工作满意度 (1-5)") +
 theme_apa +
 theme(legend.position = "none")

ggsave("figure_02.pdf", width = 6.9, height = 4.5, units = "in", dpi = 300)
```

### 模板3：折线图（趋势）

```r
library(ggplot2)

theme_apa <- theme_minimal(base_size = 10, base_family = "Arial") +
 theme(
 axis.title = element_text(size = 10), axis.text = element_text(size = 8),
 legend.text = element_text(size = 8), panel.grid.minor = element_blank()
 )

df <- data.frame(
 year = rep(2018:2023, 2),
 turnover = c(72, 75, 68, 71, 78, 82, 65, 63, 60, 58, 55, 52),
 type = rep(c("国企", "民企"), each = 6)
)

ggplot(df, aes(x = year, y = turnover, color = type, shape = type)) +
 geom_line(linewidth = 1) +
 geom_point(size = 2.5) +
 scale_color_manual(values = c("#0077BB", "#CC3311")) +
 labs(x = "年份", y = "离职率 (%)", color = NULL, shape = NULL) +
 theme_apa

ggsave("figure_03.pdf", width = 6.9, height = 4.5, units = "in", dpi = 300)
```

### 模板4：散点图 + 回归线

```r
library(ggplot2)

theme_apa <- theme_minimal(base_size = 10, base_family = "Arial") +
 theme(
 axis.title = element_text(size = 10), axis.text = element_text(size = 8),
 panel.grid.minor = element_blank()
 )

set.seed(42)
df <- data.frame(ratio = runif(80, 10, 50))
df$satisfaction <- 0.6 * df$ratio + rnorm(80, 0, 5) + 10

ggplot(df, aes(x = ratio, y = satisfaction)) +
 geom_point(color = "#0077BB", alpha = 0.6, size = 1.5) +
 geom_smooth(method = "lm", color = "#CC3311", se = TRUE, linewidth = 1, fill = "#CC3311", alpha = 0.1) +
 labs(x = "LMX质量", y = "员工投入度") +
 theme_apa

ggsave("figure_04.pdf", width = 6.9, height = 5.5, units = "in", dpi = 300)
```

### 模板5：森林图

```r
library(ggplot2)

theme_apa <- theme_minimal(base_size = 10, base_family = "Arial") +
 theme(
 axis.title = element_text(size = 10), axis.text = element_text(size = 8),
 panel.grid.minor = element_blank(), panel.grid.major.y = element_blank()
 )

df <- data.frame(
 study = c("研究1", "研究2", "研究3", "研究4", "研究5", "总体"),
 effect = c(0.35, 0.42, 0.28, 0.51, 0.38, 0.39),
 ci_lower = c(0.15, 0.22, 0.08, 0.31, 0.18, 0.27),
 ci_upper = c(0.55, 0.62, 0.48, 0.71, 0.58, 0.51),
 is_overall = c(FALSE, FALSE, FALSE, FALSE, FALSE, TRUE)
)
df$study <- factor(df$study, levels = rev(df$study))

ggplot(df, aes(x = effect, y = study, xmin = ci_lower, xmax = ci_upper)) +
 geom_vline(xintercept = 0, linetype = "dashed", color = "grey50") +
 geom_errorbarh(height = 0.2, linewidth = 0.8) +
 geom_point(aes(shape = is_overall, color = is_overall), size = 3) +
 scale_color_manual(values = c("FALSE" = "#0077BB", "TRUE" = "#CC3311")) +
 scale_shape_manual(values = c("FALSE" = 16, "TRUE" = 18)) +
 labs(x = "效应量 (Cohen's d)", y = NULL) +
 theme_apa +
 theme(legend.position = "none")

ggsave("figure_05.pdf", width = 6.9, height = 4.0, units = "in", dpi = 300)
```

### 模板6：相关矩阵热图

```r
library(ggplot2)
library(reshape2)

theme_apa <- theme_minimal(base_size = 10, base_family = "Arial") +
 theme(axis.title = element_blank(), axis.text = element_text(size = 8))

labels <- c("变革型领导", "赋能型LMX", "信任", "投入度", "绩效")
corr_matrix <- matrix(c(
 1.00, 0.45, 0.32, 0.67, 0.55,
 0.45, 1.00, 0.28, 0.38, 0.30,
 0.32, 0.28, 1.00, 0.41, 0.35,
 0.67, 0.38, 0.41, 1.00, 0.72,
 0.55, 0.30, 0.35, 0.72, 1.00
), nrow = 5, dimnames = list(labels, labels))

# 仅显示下三角
corr_matrix[upper.tri(corr_matrix)] <- NA
melted <- melt(corr_matrix, na.rm = TRUE)

ggplot(melted, aes(x = Var1, y = Var2, fill = value)) +
 geom_tile(color = "white") +
 geom_text(aes(label = sprintf("%.2f", value)), size = 3) +
 scale_fill_gradient2(low = "#2166AC", mid = "#F7F7F7", high = "#B2182B",
 midpoint = 0, limit = c(-1, 1), name = "r") +
 coord_fixed() +
 theme_apa

ggsave("figure_06.pdf", width = 5.5, height = 5.0, units = "in", dpi = 300)
```

### 模板7：漏斗图

```r
library(ggplot2)

theme_apa <- theme_minimal(base_size = 10, base_family = "Arial") +
 theme(
 axis.title = element_text(size = 10), axis.text = element_text(size = 8),
 panel.grid.minor = element_blank()
 )

set.seed(42)
df <- data.frame(
 effect = rnorm(20, 0.4, 0.15),
 se = runif(20, 0.05, 0.25)
)
mean_effect <- mean(df$effect)

ggplot(df, aes(x = effect, y = se)) +
 geom_point(color = "#0077BB", size = 2, alpha = 0.7) +
 geom_vline(xintercept = mean_effect, linetype = "dashed", color = "#CC3311") +
 geom_ribbon(data = data.frame(
 se = seq(0.01, max(df$se) * 1.1, length.out = 100),
 xmin = mean_effect - 1.96 * seq(0.01, max(df$se) * 1.1, length.out = 100),
 xmax = mean_effect + 1.96 * seq(0.01, max(df$se) * 1.1, length.out = 100)
 ), aes(x = NULL, y = se, xmin = xmin, xmax = xmax), alpha = 0.1, fill = "grey") +
 scale_y_reverse() +
 labs(x = "效应量 (Cohen's d)", y = "标准误") +
 theme_apa

ggsave("figure_07.pdf", width = 6.9, height = 5.0, units = "in", dpi = 300)
```

### 模板8：分组条形图

```r
library(ggplot2)

theme_apa <- theme_minimal(base_size = 10, base_family = "Arial") +
 theme(
 axis.title = element_text(size = 10), axis.text = element_text(size = 8),
 legend.text = element_text(size = 8), panel.grid.minor = element_blank(),
 panel.grid.major.x = element_blank()
 )
cb_palette <- c("#0077BB", "#EE7733", "#009988")

df <- data.frame(
 domain = rep(c("培训", "薪酬", "工作设计", "发言权"), 3),
 type = rep(c("国企", "民企", "跨国公司"), each = 4),
 score = c(4.1, 3.5, 3.8, 3.2, 3.8, 4.2, 3.5, 3.0, 4.3, 3.9, 4.0, 3.5)
)

ggplot(df, aes(x = domain, y = score, fill = type)) +
 geom_col(position = position_dodge(0.8), width = 0.7, color = "black", linewidth = 0.3) +
 scale_fill_manual(values = cb_palette) +
 labs(x = "HR实践", y = "均值 (1-5)", fill = NULL) +
 coord_cartesian(ylim = c(0, 5.5)) +
 theme_apa

ggsave("figure_08.pdf", width = 6.9, height = 4.5, units = "in", dpi = 300)
```

---

