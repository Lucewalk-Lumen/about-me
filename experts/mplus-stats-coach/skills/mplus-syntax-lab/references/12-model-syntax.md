# 12 · 模型语法骨架

> 所有骨架均为**本方自撰**，不复制任何第三方或官方 `.inp` 原文。
> 可直接改用的完整文件见 `../templates/inp-skeletons/`（8 个，全部通过静态校验 0 BLOCKER / 0 WARN）。
> 生成时的硬约束：**变量名 ≤ 8 字符** · **行宽 ≤ 90 字符** · **≤ 120 行 / ≤ 4 KB**。

---

## 一、骨架索引

| 文件 | 模型 | 关键语法 | 对应规则关注点 |
|---|---|---|---|
| `cfa.inp` | 三因子 CFA | `f BY y1-y4;` | L03 / L07 / L15 |
| `mediation.inp` | 中介 | `MODEL INDIRECT:` + `BOOTSTRAP` | L13 |
| `moderation.inp` | 潜变量交互 | `XWITH` + `ALGORITHM=INTEGRATION` | L10 |
| `twolevel.inp` | 两水平 | `CLUSTER` + `%WITHIN%` / `%BETWEEN%` | L05 |
| `lgm.inp` | 潜增长（4 波） | `i s \| y1@0 y2@1 y3@2 y4@3;` | — |
| `lpa.inp` | 潜剖面（连续指标） | `TYPE=MIXTURE` + `CLASSES` | L06 |
| `gmm.inp` | 增长混合 | 增长 + `CLASSES` + `STARTS` | L06 |
| `bayes.inp` | 贝叶斯 SEM | `ESTIMATOR=BAYES` + `MODEL PRIORS` | L11（禁 `MODINDICES`） |

---

## 二、逐类要点

### 2.1 CFA / SEM

```text
MODEL:
    fx BY x1-x4;
    fy BY y1-y4;
    fz BY z1-z4;
```

- `BY` = 测量（载荷）；`ON` = 回归；`WITH` = 协方差；`;` 结束语句。
- 潜变量**首次出现即在 `BY` 左侧**时会被自动定义；因此 **`MODEL` 引用未在 `NAMES` 声明的变量会报 `L07`**。
- 有序 / 二分指标 → `ESTIMATOR=WLSMV`，配 `CATEGORICAL = y1-y4;`。
- 多组：`GROUPING = g;` + `MODEL g1:` / `MODEL g2:`（**标签名自定**）。

### 2.2 中介（`MODEL INDIRECT`）

```text
MODEL INDIRECT:
    y IND m x;
```

- `IND` 的写法：`因变量 IND 中介 自变量`；多个中介用空格并列。
- 非参数区间 → `BOOTSTRAP = 5000;` + `OUTPUT: CINTERVAL(BCBOOTSTRAP);`。
- ⚠ **`OUTPUT` 要 bootstrap 区间但 `ANALYSIS` 无 `BOOTSTRAP` → 报 `L13`**（官方消息：
  `BOOTSTRAP AND BCBOOTSTRAP CI REQUIRE BOOTSTRAP IN ANALYSIS COMMAND`）。
- ⚠ `BOOTSTRAP` 与 `ESTIMATOR=BAYES` 不兼容 → `L13`。

### 2.3 调节（潜变量交互）

```text
MODEL:
    int | fx XWITH fz;
    fy ON fx fz int;
```

- `XWITH` 需 `ALGORITHM=INTEGRATION`；变量数多时计算量显著上升。
- ⚠ **本类带结果的可对照样本极薄**（官方语法样本与结果样本都很少）→ 输出**必须附降级声明**。

### 2.4 多层

```text
VARIABLE:
    CLUSTER = clus;
    WITHIN  = x1-x3;
    BETWEEN = w1 w2;

MODEL:
    %WITHIN%
    yw BY y1-y4;
    %BETWEEN%
    yb BY y1-y4;
```

- `%WITHIN%` / `%BETWEEN%` **必须配对** → 未配对报 `L05`。
- `TYPE = TWOLEVEL;`；复杂抽样另加 `WEIGHT` / `STRATIFICATION`。
- **声明为 y 的变量在 `%WITHIN%` 出现却未在 `%BETWEEN%` 出现**会触发官方警告
  `A y-variable has been declared on the within level but not referred to on the between level`。

### 2.5 增长（LGM / LGCM）

```text
MODEL:
    i s | y1@0 y2@1 y3@2 y4@3;
    [i s];
```

- `|` **左侧**是增长因子（截距 `i`、斜率 `s`），**右侧**是波次与时间载荷。
- 时间载荷用 `@` 固定（`y1@0 y2@1 …`）；不固定则自由估计。
- 随机斜率给定起始值可写成 `s* | y1 ON a1;`（**`*` 在 `|` 左侧**，实测合法）。
- 4 波、线性：至少 3 波才能估斜率；非线性需 ≥ 4 波或改分段增长。

### 2.6 混合（LCA / LPA / GMM / LTA）

```text
VARIABLE:
    CLASSES = c (2);

ANALYSIS:
    TYPE = MIXTURE;
    STARTS = 500 100;

MODEL:
    %OVERALL%
    [y1-y6];
```

- **`CLASSES` 与 `TYPE=MIXTURE` 必须一致** → 有 `CLASSES` 无 `TYPE=MIXTURE` 报 `L06`。
- **指标类型决定名称**：指标为**分类** → LCA；指标为**连续** → LPA。中文常混用，**先确认指标类型**。
- 类别数由 `AIC / BIC / aBIC / LMR-LRT / BLRT / 熵值` 逐次枚举后决定 → **骨架不预设最终类数**。
- `STARTS` 防局部极大；**`BEST LOGLIKELIHOOD VALUE WAS NOT REPLICATED`** 警告即局部极大信号。
- 类别数 ≥ 2 时，`%c#1%` 等区块用于**按类别分别建模**。

### 2.7 贝叶斯

```text
ANALYSIS:
    ESTIMATOR = BAYES;

MODEL PRIORS:
    f1-f2 ~ N(0,1);
```

- 先验写法：`参数 ~ 分布(参数)`，如 `~ N(0,1)`、`~ IG(.001,.001)`。
- ⚠ **`MODINDICES` 与 `ESTIMATOR=BAYES` 不兼容** → 报 `L11`。
- ✓ **贝叶斯下 `TECH8` 是标准用法**：输出 PSR 收敛判据（官方 `ex9.26` 等 `.out` 含
  `PSR VALUE DOES NOT INCREASE` 且 **0 错误 0 警告**）。
- **空 `MODEL PRIORS` 段合法**（官方 `penn__bayesian_run12` 实测，0 错误 0 警告）→ 只给 `INFO`。

### 2.8 蒙特卡洛 / 检验力规划

```text
MONTECARLO:
    NAMES ARE y x;
    NOBS = 500;
    NREP = 500;

MODEL POPULATION:
    %WITHIN%
    y ON x*0.3;

MODEL:
    %WITHIN%
    y ON x*0.3;
```

- `MODEL POPULATION` 是**总体（生成）模型**，`MODEL` 是**被检验模型**；两者不同即估检验力。
- 官方各章自带大量 `mcex*.inp`（**236 份**）→ 做样本量 / 检验力规划时的**一手参照**。

---

## 三、规则编号 ↔ 写法对照（生成后自检）

| 规则 | 触发写法 | 修法 |
|---|---|---|
| L01 | 段名拼写错（如 `VARIABLES:` 当段名） | 改回合法段名；注意 `MODEL <标签>:` 与 `DATA <单词>:` **是合法的** |
| L02 | 语句缺分号 | 补 `;`；注意语句可跨多行 |
| L03 | 变量名 > 8 字符 | 缩短到 ≤ 8 |
| L04 | 行宽 > 90 字符 | 换行（`TITLE` 内可忽略，仅为 `INFO`） |
| L05 | `%WITHIN%` / `%BETWEEN%` 未配对 | 补齐配对 |
| L06 | `CLASSES` 无 `TYPE=MIXTURE`（或反之） | 二者对齐 |
| L07 | `MODEL` 用了 `NAMES` 未声明的变量 | 补进 `NAMES` |
| L08 | 无 `NAMES` | 补 `NAMES ARE …;` |
| L09 | `DATA` 无 `FILE IS` | 补 `FILE IS <文件名>;`（注意 `SAVEDATA: FILE=` 不算） |
| L10 | `TECH8` + 不兼容组合 | 见 `13-estimator-guide.md` §四（**版本敏感，勿绝对化**） |
| L11 | `MODINDICES` + `ESTIMATOR=BAYES` | 删 `MODINDICES` 或改 `ML/MLR` |
| L12 | `SAMPSTAT` + 全类别结局 | 删 `SAMPSTAT` 或保留部分连续结局 |
| L13 | bootstrap 区间无 `BOOTSTRAP`；`BOOTSTRAP` + `BAYES` | 补 `BOOTSTRAP = n;` 或改用 `BAYES` 的区间 |
| L14 | `MODEL INDIRECT` / `CONSTRAINT` / `PRIORS` 为空 | **合法**，仅提醒；确认不是漏写内容 |
| L15 | `USEVARIABLES` 引用未声明变量 | 补进 `NAMES` |
| L16 | 极罕见段序反序 | **合法**，仅风格提示 |

---

## 四、生成后的自检动作（**必做**）

```bash
python3 ../scripts/check_inp.py <生成的.inp>
```

并把覆盖率声明原样转述（**三口径并列**）：
官方实测警告 **62 类 / 39 种消息 / 219 条**；本脚本已实现覆盖
**14/62 类（22.6%）· 2/39 种消息（5.1%）· 30/219 条（13.7%）**。

**禁止**把静态检查通过表述为「能跑通」——收敛性、拟合优度、参数合理性**均不在覆盖内**。
