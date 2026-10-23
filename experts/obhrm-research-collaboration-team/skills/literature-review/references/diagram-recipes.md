# 画图功能配方（轻量内联 Mermaid 备选）

> [注意] **正式综述配图请使用本技能内置 skills/obhrm-methodology/scripts/chart_engine.py（经 skills/obhrm-methodology/scripts/render_figures.py 封装）**：20 种图表、APA7、PDF+PNG 双输出，配套图表嵌入协议见 SKILL.md 第十节（画图功能）。本文件仅作为**快速内联预览**的 Mermaid 备选方案（即内联预览工具 Visualizer / `show_widget`，仅作快速预览，非正式交付配图）。
>
> 调用方式：先 `read_me(modules=["diagram"])` 加载样式，再用 `show_widget` 输出 Mermaid/SVG。
> 正式入口脚本见 `skills/obhrm-methodology/scripts/render_figures.py`；调用规范见 SKILL.md 第十节（画图功能）。
> 铁律：图是结构的视觉化，**须先有文本结构再画图**，不得用图替代论证。

## 一、理论框架图（构念–关系–机制）

```mermaid
graph LR
  A[远程办公 Remote Work] --> B[autonomy 自主性]
  A --> C[boundary blurring 边界模糊]
  B --> D[创造力 Creativity]
  C --> E[情绪耗竭 Exhaustion]
  E -->|负向| D
  F[领导赋能 Leadership] -->|调节| B
```

## 二、概念关系图（变量网络）

```mermaid
graph TD
  X[前因: 数字化HRM] --> M[中介: 员工韧性]
  M --> Y[结果: 绩效]
  Z[调节: 组织支持] -->|强化| M
```

## 三、PRISMA 流程图（纳排漏斗，呼应文献纳排审计）

```mermaid
flowchart TD
  A[数据库检索 n=1200] --> B[去重后 n=980]
  B --> C[标题摘要筛查 排除 n=700]
  C --> D[全文评估 排除 n=180]
  D --> E[纳入综述 n=100]
  F[手工补充 n=12] --> E
```

## 四、演化时间线（经典回顾 / 扎根，范式五、二）

```mermaid
timeline
  title OBHRM 综述范式演进
  2000s : 系统梳理 : 经典模型回顾
  2010s : 扎根理论 : 元分析
  2020s : 新兴主题 : 建构式 : 本土理论
```

## 五、思维导图（主题聚类 ≤5主类×3子类，主题聚类审计）

```mermaid
mindmap
  root((员工韧性))
    前因
      领导支持
      心理安全
    机制
      认知重评
      资源获取
    结果
      绩效
      创新
    边界
      文化
      远程情境
```

## 六、OBHRM 综述实战集成图（建议默认产出）

把"九种范式 × 成稿自检十步 × 画图 × 双语"集成一张总览图，作为每次综述启动的导航。

```mermaid
graph TD
  S[选题] --> T[九种范式选择]
  T --> R[PDF 资料库摄取]
  R --> C[成稿自检十步]
  C --> D[画图可视化]
  D --> O[中英双语成稿]
```
