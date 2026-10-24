---
name: case-writer
description: "高校教学案例、课程思政案例与工商管理案例写作（四路径：教学案例/课程思政/融入思政/工商管理案例）。案例写作专家陈叙真的主技能包，含八要素深度标准、思政元素映射、引用保真四铁律、deai-rules 去AI味门禁与 md_to_docx 转换。"
version: 1.1.1
---

# 案例写作技能包（case-writer）
> **归属**：领域技能层——案例写作专家（case-writer）


> 本技能包供教学帮帮团案例写作专家（陈叙真）使用。含四路径写作、八要素深度、思政映射、引用保真与去AI味门禁。

## [必读] 文档出片路由（平台自带技能优先）

WorkBuddy 已内置并启用官方办公技能，`.docx` / `.pptx` / `.xlsx` **一律优先委托**：

| 需求 | 首选 | 本包角色 |
|------|------|---------|
| Word 交付 | `tencent-docx` 技能 | 本包负责内容、结构、引用与去AI味门禁；排版出片交自带技能 |
| PPT / 表格 | `tencent-pptx` / `sheetagent` 技能 | 同上 |

`scripts/md_to_docx.py` 作为离线生成路径：平台办公技能不可用时使用；**禁止**在自带技能可用时要求用户 `pip install python-docx`。

## 使用时机

- 写高校教学案例（路径 A）
- 写课程思政案例（路径 B）
- 教学中融入思政（路径 C）
- 写高校工商管理案例 / MBA 案例 / 组织行为与人力资源教学案例（路径 D）
- 案例的 md → Word 排版转换
- 从 `material-extractor` 技能包（如某教材/专著转成的技能）取真实理论/框架锚点（遵循引用保真，不内嵌原文）

## 四路径映射（config/case-config.json 单一真源）

| 路径 | 模板 | 路径专属规约（结构骨架） | 共用质量底座 |
|------|------|--------------------------|--------------|
| A 教学案例 | assets/teaching-case-template.md | references/teaching-case-spec.md | references/case-quality-base.md |
| B 课程思政案例 | assets/sizheng-case-template.md | references/sizheng-case-spec.md + references/sizheng-elements.md | references/case-quality-base.md |
| C 融入思政（轻量模式） | 复用 A 或 B 模板 | 不建独立 spec，= 选用 A/B 模板 + references/sizheng-elements.md 思政映射 | references/case-quality-base.md |
| D 工商管理案例 | assets/management-case-template.md | references/management-case-spec.md | references/case-quality-base.md |

> **分层原则**：质量门禁（九特性 / 八要素 / 四特质含单一中心问题 / 四避坑 / 自查 / 中立 / 篇幅 / 理论锚点）全部集中在 **`references/case-quality-base.md`**（单一事实来源）；各路径 `*‑spec.md` 只定义结构骨架与命名规则，不重复质量条款。

## 写作流程（五阶段）

1. **选路径**：按诉求选 A/B/C/D，读取对应 template + `*‑spec.md`（C 走轻量模式）。
2. **检索锚点**：联网检索顶层政策（立德树人/三全育人/课程思政/教育强国建设规划纲要 2024-2035）、精神谱系（工匠/科学家/企业家/教育家精神）、学科前沿数据；来源标注规范见 `references/case-reference-standard.md`，采集与检索指引见 `references/source-integrity.md`。路径 D 以管理理论框架、行业基准数据、权威案例库为锚点，同样遵循引用保真，不内嵌原文。
3. **撰写正文**：按所选 `*‑spec.md` 的结构骨架落地，并满足 `references/case-quality-base.md` 的八要素 / 四特质（聚焦单一中心问题）/ 理论锚点。
4. **去AI味门禁**：`deai-rules` L1 硬性（一级禁用词零命中/无套话开头/无公式化结尾/无连续三段排比）+ L2 风格（具体事件切入/长短句交替/关键引语/矛盾两难）。

   **交付前确定性门禁（必跑）**：成稿交付前运行 `python skills/deai-rules/scripts/deai_preflight.py <成稿路径>`，须 PASS；与 `deai-rules` 五维自评（≥45）共同构成 quality 门禁，未 PASS 不得标记为交付物（规则见 `skills/deai-rules/SKILL.md`）。
5. **转换输出**：`$VENV_PY skills/case-writer/scripts/md_to_docx.py src.md [out.docx]`（正文 `[N]`→上标、`参考文献` 后悬挂缩进、宋体+Times New Roman）。依赖 `python-docx` 由 `setup` 技能装入专用 venv（`$VENV_PY` 取值见 `skills/setup/SKILL.md`），禁止裸 `python3` 与单独 pip install。

## 引用保真（四铁律 · 要点）

> **必读**：`skills/citation-integrity/SKILL.md`——引用保真校验清单，全团 L0 权威层。凡产出中出现政策条文、行业数据、获奖记录或任何带出处的数字，交付前必须逐条执行引用保真校验：每条来源同时满足三项硬条件（真实存在 / 可核实 / 引用格式与出处一致），无法核实的条目显式标注〔无可靠来源，待核实〕并在交付前清零。
> 文内标记四式、统一 `## 参考文献` 著录与跨模板一致性规则见 **`references/case-reference-standard.md`**；资料采集与检索见 **`references/source-integrity.md`**。

- 不编引用 / 不归观点 / 标注无支撑〔无可靠来源，待核实〕/ 不超范围
- 行业政策宏观数据必须带〔来源〕；主角企业内部数字属案例情境不杜撰来源
- 禁止虚构数字/政策条文/文件名/获奖记录/文献出处；禁止把检索不到写成据研究表明；禁止模糊断言（大量/显著/普遍）替代可标注来源

## 思政元素（默认映射 · 详见 `references/sizheng-elements.md`）

- 领导力→责任担当/家国情怀/以身作则；团队协作→集体观念；组织文化变革→改革创新；人力资源→公平公正/职业伦理/诚信；创新创业→企业家精神/社会责任；激励沟通→以人为本/工匠精神
- 两段式命名 ≤25 字（思政价值要义+知识点）；三维目标（知识/能力/价值，价值为核心须对应知识点）

## 输出规范

- A 教学案例：五模块（背景/目标/实施/成效/反思评析），3000–8000 字
- B 课程思政案例：四部分（基本信息/目标/主要内容/教学设计）+ 教学反思，3000–8000 字
- D 工商管理案例：四模块（背景/描述/成效/反思评析）+ 反思评析并入正文末段（不再另交教学说明），编号中文数字式（一、二、三…）与 A/B 一致，5000–8000 字（中国工商管理案例库 ≤8000）；主标题「主体名：核心定位」，封面元信息（机构/编号/作者/日期/版权/掩饰声明）已去除

## 注意事项

- 禁止整段照搬知识库案例（只借结构不抄内容）；禁止只写成功/流水账（须有冲突两难）
- 口吻分层：案例正文中立客观叙述，反思/思政融入用教师视角（详见 `references/role-persona.md`）
- 门禁不通过（L1 任一项）必须改，改完再交付
