---
name: talent-sourcing
version: 1.0.0
author: "Xing Bu"
description: 人才寻访私有 playbook——招聘管道上游的主动寻访与人才库运营。当任务涉及用人需求解析为寻访画像、人才库定向搜索与匹配、寻访侧初评（触达难度/在职稳定性/薪酬契合度）、A/B/C 分级 shortlist 产出与交接、人才库五库（简历/职位需求/人才画像/人才地图/渠道）运营时加载。引用私有 KB（sourcing-playbook / pii-handling / shortlist-template）与共享引擎 candidate_scorer.py / pii.py / envelope.py。
---

# talent-sourcing 领域 playbook（私有）

本文件是该 specialist 的领域工作流基准，由 `agents/talent-sourcing.md` 加载。共享契约见 `../hrm-solution/contracts.md`；共享引擎见 `../hrm-solution/scripts/`。

## 核心能力
1. **需求解析**：把用人部门的口头/书面需求按 JD 六要素拆解（见下），产出 requisition JSON（J 系列）与寻访画像
2. **人才搜索与匹配**：基于 `sourcing_profile` 在人才简历库/人才地图库中做关键词 + 条件过滤（技能/城市/年限/目标公司），关键词按三级分类展开（标准名/细分赛道专属名/行业通用别名，中英对照），别名类命中权重低于标准名；引擎：`scripts/sourcing_matcher.py`
3. **寻访侧初评**：寻访适配三维评分（触达难度 30% / 在职稳定性 35% / 薪酬契合度 35%）；对 A 级候选与关键岗位复用五维评分（技术25%/专业20%/学习20%/匹配20%/稳定15%）：`python3 ../hrm-solution/scripts/candidate_scorer.py --scores '{"technical":8,"professional":7,"learning":6,"role_fit":8,"stability":7}'`（Windows 用 `python`；必须显式传 `--scores` JSON）
4. **推荐分级与 shortlist 产出**：按 A/B/C 分级规则归入级别，生成推荐理由与触达建议话术（双版本：平台版 ≤200 字 / 电话版 ≤350 字覆盖七要素），模板见 `references/shortlist-template.md`
5. **人才库运营**：五库 CRUD、索引维护、状态与标签回写、删除请求处理；引擎：`scripts/talent_pool.py`
6. **合规寻访**：入库必查同意记录；一切 PII 经 `../hrm-solution/scripts/security/pii.py` 脱敏；触达话术交付前经 `labor-compliance` 审查

## 六步寻访工作流

1. **需求解析**：用人需求 → JD 六要素拆解：① 战略定位与业务目标 ② 核心挑战 ③ 能力权重排序（权重化条目，写入 `capability_weights`） ④ 隐性招聘诉求（写入 `implicit_expectations`） ⑤ 准入门槛分三档——必备项/加分项/红线，红线直接写入 `sourcing_profile.exclude` 做硬过滤 ⑥ 可直接搜索的人才标签组合（`talent_tags`）→ 产出 `requisition` JSON + 寻访画像摘要（详见 `references/sourcing-playbook.md`）
2. **搜索匹配**：`requisition.sourcing_profile` + 五库索引 → 关键词三级展开 + 条件过滤 + tiers 公司清单过滤 → `match_results`（候选人 ID 列表 + 匹配分 + 命中依据）。匹配分 = 技能命中率×50% + 年限契合×20% + 城市匹配×15% + 目标公司/行业契合×15%
3. **初步筛选**：命中档案 → 寻访适配三维评分；A 级候选与关键岗位追加五维评分 → `screened` 列表（每人：三维分 + 可选五维分 + 初评结论）
4. **推荐分级**：按分级规则归 A/B/C 级 → `shortlist` JSON + Markdown 报告（按 `references/shortlist-template.md`）；触达话术双版本产出
5. **跟进交接**：shortlist 经 `pii.py` 脱敏 → 信封封装（`envelope.py` 签名）→ 经主理人中转交 `recruitment-pipeline`；触达话术先经 `labor-compliance` 审查
6. **结果回写**：按交接结果与候选人反馈更新档案 `status` / `last_contacted_at` / 标签；删除请求走 `talent_pool.py delete <candidate_id>`（物理删除 + 索引审计日志）

## JD 六要素拆解（需求解析标准）

| # | 要素 | 落点字段 |
|---|---|---|
| 1 | 战略定位与业务目标 | requisition 顶层语境字段（title/department/level）与寻访画像摘要 |
| 2 | 核心挑战 | 寻访画像摘要 |
| 3 | 能力权重排序 | `sourcing_profile.capability_weights`（权重化条目，权重合计 100） |
| 4 | 隐性招聘诉求 | `sourcing_profile.implicit_expectations`（示例：前任因跨部门推动不力离开，隐含强 stakeholder 管理能力要求） |
| 5 | 准入门槛三档：必备项/加分项/红线 | `must_have` / `nice_to_have` / `sourcing_profile.exclude`（红线做硬过滤） |
| 6 | 可直接搜索的人才标签组合 | `sourcing_profile.talent_tags` + `sourcing_profile.skill_keywords`（三级分类） |

## 寻访适配三维（寻访侧专用，权重 30/35/35）

| 维度 | 权重 | 含义 | 评分要点（0-10） |
|---|---|---|---|
| 触达难度 reachability | 30% | 能否以合规方式联系到人 | 有直接联系方式且已授权=9-10；仅公开渠道可触达=5-7；只能通过中间人=2-4 |
| 在职稳定性 tenure_stability | 35% | 当前在职多久、跳槽节奏 | 现职 ≥3 年且历史稳定=8-10；现职 1-2 年=5-7；3 段均 <1 年=0-3（同时在 J 档 exclude 中硬过滤） |
| 薪酬契合度 comp_fit | 35% | 期望与 J 档 salary_band 的重合度 | 完全落在 band 内=9-10；超出上限 ≤15%=6-8；超出 >30%=0-3（需 compensation-strategy 对标输入时标注来源） |

寻访适配综合分 = 三维加权（保留 1 位）。**该分只用于寻访排序**，不得与五维评分混用或互相替代；shortlist 中两者并列呈现并各自注明口径。五维评分（技术25%/专业20%/学习20%/匹配20%/稳定15%）原样复用 `candidate_scorer.py`，不改权重。

**SBTI 测评结果暂不入匹配**：仅预留接口——当候选人主动授权且已完成测评时，SBTI 类型码可作为 `profile.assessment` 字段附在档案中（`assessment_result` JSON：type_code + 授权标记）；无授权则不进入匹配，本版本初评不消费该字段。

## 候选人分级规则

| 级别 | 判定条件（同时满足） | 动作 |
|---|---|---|
| A 级（Strong） | 寻访适配 ≥8.0；硬门槛全中；若跑五维评分则 ≥7.0 | 48 小时内触达；shortlist 置顶；附定制话术 |
| B 级（Qualified） | 寻访适配 6.0-7.9；硬门槛全中或仅 1 项边缘 | 本周期触达；标准话术 |
| C 级（Potential） | 寻访适配 5.0-5.9，或有明显短板但属稀缺方向 | 入人才库培育池，打标签，暂不主动触达 |
| 不推荐 | 寻访适配 <5.0 或硬门槛不满足或命中 exclude | 不进 shortlist；档案保留（依合规规则）并记录原因 |

## 输出质量验收标准（可量化）

| 指标 | 口径 | 目标值 |
|---|---|---|
| shortlist 命中率 | 进入 shortlist 的候选人中，经 recruitment-pipeline 初筛通过的比例 | ≥ 60%（运行 3 个月后按实际校准） |
| 推荐响应率 | A/B 级候选人触达后有实质回复的比例 | ≥ 30%（按渠道分开统计） |
| 字段完整度 | shortlist 中候选人档案必填字段（技能/城市/年限/来源/同意记录）完整率 | 100%（缺一即不出 shortlist，fail-fast） |
| 合规零违规 | 交付经 `compliance_gate.py` 终检 BLOCKED 次数 | 0；同意记录缺失入库次数 0 |
| 复用率 | shortlist 中来自人才库存量（而非新寻访）的占比 | ≥ 40%（人才库运营成效指标） |

## 五库结构（knowledge/）

每库一个目录，库内每份档案一个 JSON 文件，库级一份 `_index.json` 汇总索引。数据文件是结构示例与空库骨架，真实候选人数据由使用方部署后按合规来源灌入（禁止爬虫违规采集）。

| 库 | 目录 | 档案 schema | 说明 |
|---|---|---|---|
| 人才简历库 | `knowledge/resumes/` | talent-resume（R 前缀） | PII 受限：只存脱敏视图，须含 `source.consent` 同意记录 |
| 职位需求库 | `knowledge/requisitions/` | job-requisition（J 前缀） | 含六要素字段与关键词三级分类 |
| 行业人才画像库 | `knowledge/talent-personas/` | talent-persona（P 前缀） | 群体统计特征，不含个人 PII；市场数据须标「需人工核实」 |
| 人才地图库 | `knowledge/talent-maps/` | talent-map（M 前缀） | 只收职业公开信息；含 tiers 梯队与 red_lines 三条红线 |
| 渠道资源库 | `knowledge/channels/` | sourcing-channel（C 前缀） | 渠道合规要点、产出与负责人 |

## 与共享引擎的复用关系

| 引擎 | 复用方式 | 说明 |
|---|---|---|
| `../hrm-solution/scripts/candidate_scorer.py` | 直接复用调用（CLI `--scores '<JSON>'`） | 只对 A 级候选与关键岗位调用，产出预筛分；正式评估分由 recruitment-pipeline 在管道内重跑 |
| `../hrm-solution/scripts/security/pii.py` | 直接复用 | 档案入库、日志、信封、shortlist 报告全部经其脱敏（`mask_phone` / `mask_email` / `redact_pii`） |
| `../hrm-solution/scripts/security/envelope.py` | 直接复用 | 回传主理人的信封签名与验签 |
| `../hrm-solution/scripts/security/compliance_gate.py` | 复用（由主理人在交接环节调用） | shortlist 报告与触达话术交付前终检 |

## 护栏
- 不承诺薪酬范围（转交 `compensation-strategy`）；薪酬表述不写具体数字承诺
- 不出具任何合规结论（寻访话术、信息处理授权文本由 `labor-compliance` 终检）
- 不做最终录用决策、不做面试评估（仅输出寻访侧建议）
- 不处理候选人主动投递的简历（那是 recruitment-pipeline 的入口）
- 无同意记录（`source.consent.obtained=true`）的候选人档案不得入库
- 严禁就业歧视（性别/年龄/婚育/民族/宗教）；不采集身份证号、婚育、家庭信息；不收集敏感个人信息（生物识别、宗教信仰、医疗健康等），意外获得即删除
- 严禁编造候选人档案、公司名或虚假量化数据；画像库市场数据一律标注「需人工核实」与基准日期
- DRI：寻访拓展总监

## 回传要求
分析完成后，必须通过 SendMessage 将完整产出（含 shortlist JSON 结构化数据）回传给主理人，并以信封封装（`../hrm-solution/scripts/security/envelope.py`）。
