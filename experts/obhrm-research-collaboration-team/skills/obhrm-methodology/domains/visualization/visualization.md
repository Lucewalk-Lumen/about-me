# 图表引擎域

自研 Python 图表引擎，20 种图表类型，APA7 规范；渲染依赖 `requirements.lock` 中已声明并过 CVE 扫描的 matplotlib/numpy/scipy/seaborn（缺失时脚本会打印安装提示并以退出码 1 终止）。

---

## 引擎调用

```bash
python ../../scripts/chart_engine.py <类型> '<JSON>' --output ./产出/

# 返回: {"pdf": "./产出/图名.pdf", "png": "./产出/图名.png"}
```

> Python：运行环境内置解释器（路径视部署而定，需展开~为绝对路径；或直接使用 `python`/`python3`）。需含 matplotlib（3.5+）、seaborn（0.12+）、numpy（1.23+）、scipy（1.9+）；具体可用版本以实际运行环境为准，缺失时脚本会给出安装提示

---

## 图表选择表（20种）

| 数据类型 | 目的 | 函数 | JSON关键字段 |
|---------|------|------|------------|
| 类别+数值 | 组间比较 | **条形图** | `categories, values, errors` |
| 类别+数值 | 横向比较 | **分组条形图** | `categories, groups[{label,values}]` |
| 连续1组 | 分布 | **直方图** | `values, bins` |
| 连续2-5组 | 分布比较 | **箱线图 / 小提琴图** | `data[[...]], labels` |
| 时间序列 | 趋势 | **折线图** | `x, series[{label,values}]` |
| 时间序列堆叠 | 构成 | **面积图** | `x, series[{label,values}]` |
| 两连续变量 | 关系 | **散点图** | `x, y, show_regression` |
| 调节+两连续 | 简单斜率 | **简单斜率图** | `x[min,max], groups[{label,intercept,slope}], highlight` |
| 多变量 | 矩阵 | **热图** | `matrix, labels` |
| 效应量+SE | 偏倚 | **漏斗图** | `effects, se` |
| 效应量+CI | 汇总 | **森林图** | `studies, effects, ci_lower, ci_upper` |
| 多维 | 评估 | **雷达图** | `labels, series[{label,values}]` |
| 概念 | 框架 | **网络图** | `nodes[{id,label}], edges` |
| 问题 | 诊断 | **鱼骨图** | `problem, causes[{label,sub_causes}]` |
| 流程 | 步骤 | **流程图** | `steps[{text,type}]` |
| 数据流 | 流向 | **桑基图** | `flows[{source,target,value}]` |
| 集合 | 交叉 | **韦恩图** | `sets[{label,size}]` |
| 知识 | 结构 | **思维导图** | `root, children[{text,children}]` |
| 占比 | 构成 | **饼图**（APA不推荐） | `labels, values` |

---

## 分阶段图表指引

| 阶段 | 图表 | 命令 |
|------|------|------|
| D2 | 箱线图/热图/雷达图 | `../../scripts/chart_engine.py 箱线图 '...' --output ./产出/` |
| D3 | 条形图+误差 | `../../scripts/chart_engine.py 条形图 '{"errors":[...],...}'` |
| D4 | 散点图+回归线 | `../../scripts/chart_engine.py 散点图 '{"show_regression":true,...}'` |
| D4 | 调节效应简单斜率图 | `../../scripts/chart_engine.py 简单斜率图 '{"x":[-2,2],"groups":[{"label":"高调节","intercept":2.1,"slope":0.8},{"label":"低调节","intercept":2.1,"slope":-0.3}],"highlight":true}' --output ./产出/` |
| M3 | 森林图/雷达图 | `../../scripts/chart_engine.py 森林图 '...' --output ./产出/` |
| M4 | 漏斗图 | `../../scripts/chart_engine.py 漏斗图 '...' --output ./产出/` |
| M2 | PRISMA桑基图 | `../../scripts/chart_engine.py 桑基图 '...' --output ./产出/` |
| A2 | 文献网络图 | `../../scripts/chart_engine.py 网络图 '...' --output ./产出/` |
| A3 | 理论框架图 | `../../scripts/chart_engine.py 流程图 '...' --output ./产出/` |
| B4 | 技术路线图 | `../../scripts/chart_engine.py 流程图 '...' --output ./产出/` |
| C3 | 鱼骨图 | `../../scripts/chart_engine.py 鱼骨图 '...' --output ./产出/` |
| 全局 | 韦恩图/思维导图 | `../../scripts/chart_engine.py 韦恩图 '...' --output ./产出/` |

---

## 图表规范

### APA7（引擎内置）
- Tol 无障碍配色（`#0077BB` `#33BBEE` `#009988` `#EE7733` `#CC3311` `#EE3377`）
- 300dpi、PDF+PNG 双输出、去顶右轴、8-10pt字号

### 高级增强
- 一图一主张：每图只传达一个核心发现
- 多面板角色：A建立上下文 → B展示主结果 → C排除替代解释
- 图注 ≥80 字：做了什么 + 发现了什么 + 为什么重要

---

## 图表嵌入协议（结果呈现必做 — 解决"图表没进正文"）

> **核心原则：生成图表 ≠ 完成。** 图表必须进入正文、连续编号、配 APA 图注、并被正文显式引用，才算交付。
> **执行脚手架**：直接复制 `../../references/templates/template_guide.md` 的「图表登记表」「图注模板」空模板填充，降低遗漏与格式漂移。

### 1. 图表登记表（Figure Register）— 每次生成立即登记

在产出目录维护一张全局登记表，正文按序引用，编号全局连续：

| 编号 | 类型 | 归属阶段 | 标题 | 文件(PNG/PDF) | 图注 | 正文引用 |
|------|------|----------|------|---------------|------|----------|
| 图1 | 条形图 | A5 §3.1 | 三组均值比较 | ./产出/条形图.png | [通过] | [通过] |
| 图2 | 网络图 | A2 | 文献网络结构 | `./产出/network-graph.png` | [通过] | [通过] |

- 图、表分开编号：图1/图2… 与 表1/表2… 各自连续
- 同一文件同时产出 PDF（投稿矢量）与 PNG（预览/Word 嵌入）
- A5 / 基金路径收尾时，逐行核对：是否已生成 + 已登记 + 有图注 + 正文≥1 处引用

### 2. 图注规范（≥80 字，APA7）

每张图下方输出（表格同理用「表N.」）：

```
图N. [图题]. [基于什么数据/样本/方法]. [核心发现一句话，含关键统计量].
[为何重要 / 对假设 Hx 的支持或否定 / 与既有文献的呼应].
```

示例：
```
图3. 变革型领导对创造力影响的回归拟合散点图。基于研究1的412名员工配对数据，
横轴为变革型领导评分、纵轴为创造力评分。回归线斜率显著为正（β=.34, p<.001, r=.41），
表明变革型领导越强员工创造力越高，支持假设H1，并与既有研究的结论一致。
```

### 3. 正文引用（强制 — 每段含图必引 ≥1 次）

在叙述该结果/方法的位置，至少一次显式引用，禁止"详见下图"后无正文承接：

- 中文：「如图3所示，变革型领导评分与创造力呈显著正相关（β=.34, p<.001）……」
- 英文：「As shown in Figure 3, transformational leadership was positively…」
- 表格：「表2 显示三组在创造力上的均值差异显著（F(2,409)=12.7, p<.001）」

### 4. 嵌入模板（直接粘进 Markdown / Word）

```markdown
!图N 图题（示例输出：图N.png）

**图N.** 图题。图注内容（≥80字，含数据来源、关键发现、理论含义）。
```

### 5. 完成判定（任一不满足则该阶段视为未完成）

- [ ] 每个含数据的 Results/方法子节 ≥1 张图或表
- [ ] 每张图/表已生成 PDF+PNG 并登记在「图表登记表」
- [ ] 每张图/表有 ≥80 字 APA 图注
- [ ] 每张图/表在正文 ≥1 处显式引用（含"图N/表N"字样）

## 跨域联动

- **论文路径**（A2 框架图 / A3 理论模型 / A5 全文图表）→ `../../../paper-writing/SKILL.md`。
- **基金路径**（B2 缺口矩阵 / B4 技术路线图 / B6 雷达图）→ `../../../grant-writing/SKILL.md`。
- **审稿路径**（C3 鱼骨图）→ `../../../peer-review/SKILL.md`。
- **数据路径**（D2 箱线图/热图/雷达图、D3 条形图+误差、D4 散点图+回归线/简单斜率图）→ `../../../data-analysis/quantitative/quantitative.md`。
- **元分析路径**（M2 PRISMA 桑基图、M3 森林图/雷达图、M4 漏斗图）→ `../../../data-analysis/quantitative/quantitative.md`。
- **综述路径**（综述框架图 / PRISMA 流程图）→ `../../../literature-review/SKILL.md`。
- **方法层**：`../../references/methods/statistical_figure_standard.md`（图表规范）、`../../references/methods/statistical_report_standard.md`（统计报告标准）、`../../references/reasoning/argument_frameworks.md`（图表与论证连接）。

## 协作交接

图表生成结果进入「图表登记表」后，**属于交接块的强制字段**：

- 论文 A5 完成后送 审稿路径诊断时，图表登记表作为可追溯矩阵的子项随链路三交接块一同移交。
- 数据路径 D2–D4 完成后，图表登记表随链路二交接块回传 论文路径。
- 元分析路径 M2–M5 图表自管，不回 论文路径，但登记作为论文送审稿链路三的强制子项。

> 字段级规格见 `../../references/templates/handoff-protocol.md` 链路一/二/三；图表登记与嵌入的判定标准见本文件「图表嵌入协议」。

## 参考

`../../references/methods/statistical_figure_standard.md`、`../../references/methods/statistical_report_standard.md`、`../../references/reasoning/argument_frameworks.md`、`../../references/templates/handoff-protocol.md`（跨路径字段级规格）。
