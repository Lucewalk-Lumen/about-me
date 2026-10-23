# 中英双语写作范式

> 原生支持 **中文范式 / 英文范式 / 中英双语对照** 三种输出。术语保持中英对应（呼应术语标准化审计）。
> 结构化数据（中英术语映射，以 `../knowledge/bilingual_terms.json` 为单一真源，标注 `needs_human_review` 的条目按目标期刊惯例取舍）见该文件；双语模板（研究背景/现状/缺口/述评/参考文献 的 zh-en 对照）见 `../knowledge/templates.json`。
> **学术翻译硬标准（时态/语态/术语一致性/客观语调/中式英语陷阱/译后自检）统一见 `skills/obhrm-methodology/references/writing/translation_prompts.md`，本范式与之配套使用，不重复定义。**

## 一、三种输出模式

- **中文范式**：触发语"用中文写""中文综述"，结构采用万能模板（见 `../knowledge/templates.json`）与质量标准。
- **英文范式**：触发语"in English""英文综述"，结构为 Background–Themes–Gaps–Synthesis–References，引用用 (Author, Year)、参考文献 APA 7th。
- **双语对照**：触发语"中英对照""bilingual""双语范式"，同主题段落上下/左右对照，术语保持双语。

## 二、通用双语结构（推荐骨架）

```
研究背景 / Background
研究现状 / Current State of Research
  子主题1 / Theme 1
  子主题2 / Theme 2
研究缺口 / Research Gaps
述评与展望 / Synthesis and Future Directions
参考文献 / References
```

## 三、中英过渡语（常用，可扩展）

常用中英过渡语包括：引出背景"近年来，关于 X 的研究……" / "In recent years, research on X has…"；指出共识"学界普遍认同……" / "There is a broad consensus that…"；呈现分歧"然而，关于 X 存在争议" / "However, the literature remains divided on X"；比较视角"与 A 不同，B 认为……" / "In contrast to A, B argues that…"；指出不足"现有研究在 Y 方面存在局限" / "Existing studies are limited in Y"；缺口论证"现有研究已考察 X，但未涉及 Z" / "Prior work has examined X, yet Z remains unexplored"；过渡递进"在此基础上……" / "Building on this…"；总结展望"综上，未来应关注……" / "In sum, future research should…"。

## 四、双语范例（同一论点，中英对照）

**中文**：远程办公对员工创造力的研究呈现方法分裂。多数横断研究（如 Smith, 2020）依赖自评量表，难以捕捉创造过程的动态性；而少数日记研究（Lee & Kim, 2022）显示日级自主性正向预测创意产出。这一矛盾提示：未来需采用经验取样法解构"远程–创造"的日内机制。

**English**: Research on the impact of remote work on employee creativity exhibits a methodological divide. Most cross-sectional studies (e.g., Smith, 2020) rely on self-reported scales, failing to capture the dynamics of the creative process; whereas a handful of diary studies (Lee & Kim, 2022) show that daily autonomy positively predicts creative output. This tension suggests that future work should adopt experience-sampling methods to unpack the within-day mechanisms linking remote work and creativity.

## 五、英文范式特别提示

- 引用用 (Author, Year)；参考文献 APA 7th。
- 断言强度匹配证据（呼应客观语调自检）：探索性发现勿写 "groundbreaking"。
- 避免 "fill a major gap" 等夸张语；用 "an understudied boundary" 等克制表述。
- 理论贡献三层级（构念重构 / 机制解密 / 边界拓展）同样适用英文稿。

## 六、双语术语表

> 完整术语映射（含研究缺口/理论贡献/调节效应/经验取样法/扎根理论/构念/中介机制/边界条件等）见 `../knowledge/bilingual_terms.json`。该表为术语单一真源，`needs_human_review: true` 的条目已在内联 `note` 标注流派敏感点（如 theoretical contribution vs. implication、voice 绝不译"声音"），译者按目标期刊惯例取舍即可，无需等待整表审校。术语一致性管控与易错词红线详见 `skills/obhrm-methodology/references/writing/translation_prompts.md` §2.1。
