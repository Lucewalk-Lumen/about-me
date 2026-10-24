# HRM Solution · 计算脚本索引

> 计算脚本的入口契约、统一返回 schema 与错误码字典以本文件为**单一基准**。
> 简历/面试辅助知识库与模板不经过 `engine_service`，由 `recruitment-pipeline` 直接引用。

## 1. 入口契约表

### 1.1 `payroll_engine.py` — 薪酬计算引擎

**调用形态**：CLI，参数为 JSON 字符串

| 参数 | 说明 | 必填 | 类型 |
|---|---|---|---|
| `--payroll <JSON>` | 单月薪资计算（camelCase JSON） | 是 | string |
| `--insurance-base <AMOUNT>` | 社保/公积金缴费基数（可选，覆盖默认当月工资基数）| — | decimal string |
| `--bonus <AMOUNT>` | 年终奖单独计税（Decimal 字符串）| — | decimal string |

**JSON 字段**（`--payroll` 入参，camelCase，**起 fail-fast 强校验**）：

| 字段 | 必填 | 类型 | 说明 |
|---|---|---|---|
| `employeeId` | — | string | 员工 ID，默认 `""` |
| `employeeName` | — | string | 员工姓名，默认 `""` |
| `baseSalary` | 是 | number | 基本工资（≥0）|
| `city` | 是 | string | 城市（北上广深杭内置）|
| `year` | — | int | 2000-2100，默认 2026 |
| `month` | — | int | 1-12，默认 1 |
| `positionAllowance` | — | number | 岗位津贴 |
| `performanceBonus` | — | number | 绩效奖金 |
| `overtimePay` | — | number | 加班费 |
| `otherIncome` | — | number | 其他收入 |
| `otherDeductions` | — | number | 其他扣除 |
| `specialDeduction` | — | number | 专项附加扣除 |
| `cumulativeTaxPaid` | — | number | 截至上月累计已缴个税 |
| `cumulativeIncome` | — | number | 累计收入（与下面两键必须三选三或三不传）|
| `cumulativeInsurance` | — | number | 累计五险一金 |
| `cumulativeSpecial` | — | number | 累计专项附加 |

> **数值上限**：所有金额类字段（`baseSalary` 及各可选数值字段）合理上限为 **1e12 元**；超出以 `E040`（值越界）拒绝，避免极端数值触发内部精度/溢出异常。

**输出结构**：

```json
{
 "year": 2026,
 "month": 3,
 "employee_id": "E001",
 "employee_name": "张三",
 "gross_pay": "25000.00",
 "insurance_base": "25000",
 "total_insurance": "5625.00",
 "tax_amount": "592.50",
 "net_pay": "18782.50",
 "employer": { "pension": "4000.00", "medical": "1250.00", "unemployment": "200.00", "injury": "100.00", "maternity": "0.00", "housing_fund": "1250.00", "total": "6800.00" }
}
```

### 1.2 `candidate_scorer.py` — 候选人五维评分引擎

**调用形态**：CLI，参数为 JSON 字符串

| 参数 | 说明 | 必填 |
|---|---|---|
| `--scores <JSON>` | 五维评分 JSON：`{"technical": 8.5, "professional": 8, "learning": 9, "role_fit": 8.5, "stability": 6}` | 是 |
| `--candidate <NAME>` | 候选人姓名（可选，用于报告标题）| — |
| `--format <json|report>` | 输出格式，默认 `json` | — |

**输出结构**：

```json
{
 "dimensions": {
 "technical": 8.5,
 "professional": 8.0,
 "learning": 9.0,
 "role_fit": 8.5,
 "stability": 6.0
 },
 "overall": 8.1,
 "recommendation": "recommend",
 "risk_level": "low",
 "note": "优质候选人，建议录用"
}
```

### 1.3 `org_health.py` — 组织健康度诊断

**调用形态**：CLI，参数为 **JSON 文件路径**（不是 JSON 字符串）

```bash
python3 scripts/org_health.py /path/to/org.json
```

**JSON 文件结构**（顶层必填 `teams` / `total_depth`，不接受未知键）：

```json
{
 "teams": [
 {"name": "研发组", "size": 8, "manager": true, "manager_count": 1, "manager_only": false}
 ],
 "total_depth": 5
}
```

| 顶层字段 | 必填 | 说明 |
|---|---|---|
| `teams` | 是 | 团队列表（≥1）|
| `total_depth` | 是 | 层级深度（int）|

| 团队字段 | 必填 | 说明 |
|---|---|---|
| `size` | 是 | 团队规模 |
| `name` | — | 团队名 |
| `manager` | — | 是否经理 |
| `manager_count` | — | 经理数 |
| `manager_only` | — | 是否纯经理团队 |

**输出结构**：

```json
{
 "org_health": {
 "span_of_control": {"min": 8, "max": 8, "avg": 8.0, "status": "healthy"},
 "hierarchy_depth": {"current": 5, "status": "healthy"},
 "ic_manager_ratio": {"current": "7:1", "status": "healthy"},
 "team_size": {"min": 8, "max": 8, "avg": 8.0, "status": "healthy"}
 },
 "risks": []
}
```

### 1.4 `engine_service.py` — 服务化封装

**调用形态**：

```bash
python3 skills/hrm-solution/scripts/engine_service.py
# 输出可用端点列表
```

**可用端点（4 个）**：

| 端点 | 对应引擎 | 入参 |
|---|---|---|
| `payroll.monthly` | `payroll_engine.py --payroll` | 月度薪资 |
| `payroll.bonus` | `payroll_engine.py --bonus` | 年终奖 |
| `candidate.score` | `candidate_scorer.py --scores` | 五维评分 |
| `org.health` | `org_health.py <org.json>` | 组织健康度 |

### 1.5 `sbti_assessment.py` — SBTI 职场人格测评引擎

**调用形态**：CLI，参数为 JSON 字符串

| 参数 | 说明 | 必填 | 类型 |
|---|---|---|---|
| `--answers <JSON>` | 32 题作答（q1–q30 + drink_gate_q1/q2）。键必须与题库一一对应：未知键（如 q31+ / 手误键名）直接拒绝（exit 2），隐藏题缺答同样拒绝；各题取值须在 options 声明范围内（fail-fast，与 org_health.py 严格 schema 风格一致） | 是 | string |

**JSON 作答示例**：

```json
{"q1": 1, "q2": 2, ..., "q30": 3, "drink_gate_q1": 1, "drink_gate_q2": 1}
```

**输出结构**：

```json
{
 "final": {
 "code": "STILL",
 "cn": "抽离者",
 "intro": "我先退出一下，充会儿电。",
 "desc": "...",
 "image": {
 "file_name": "STILL.png",
 "relative_path": "assets/sbti/images/STILL.png"
 }
 },
 "reason": "按 Distance...",
 "user": { "levels": {...}, "pattern": "LLL-LLL-LLL-LLL-LLL" },
 "best_match": { "code": "...", "pattern": "...", "distance": 5, "exact": 11, "similarity": 83 }
}
```

**说明**：
- 计算确定性：相同输入必得相同输出。
- 兜底规则：最高匹配度 < 60% 时兜底为 `HHHH`（当前唯一的非匹配判定）。
- 爱好类隐藏题 `drink_gate_q1` / `drink_gate_q2` 仅作背景采集，不参与人格判定。
- 海报位于 `assets/sbti/images/`（相对 `skills/personality-assessment/` 技能根，与输出 `relative_path` 同一基准），共 26 张，由 `personality_image_map.json` 映射。
- 接受用户直接文本/作答输入。

### 1.6 `compliance_gate.py` — 合规闸门（终检）

**调用形态**：CLI，文本经 `--text` 传入（或 `--text -` / stdin 管道）

| 参数 | 说明 | 必填 |
|---|---|---|
| `--text <TEXT>` | 待分级文本；传 `-` 或省略则从 stdin 读取 | — |

**输出**：`GateDecision.to_dict()` JSON（`gate` / `risk_level` / `dri` / `reasons`）打印到 stdout。

**退出码**：`PASSED` / `FLAGGED` → 0；`BLOCKED` → 3（并向 stderr 写一行 `[BLOCKED] …`）。

```bash
python3 scripts/security/compliance_gate.py --text '少缴社保'             # BLOCKED, exit 3
python3 scripts/security/compliance_gate.py --text '请介绍未缴社保的风险'  # FLAGGED, exit 0
echo '绩效制度' | python3 scripts/security/compliance_gate.py --text -   # PASSED, exit 0
```

> 模块内 `enforce_final_gate()` / `finalize(env, text)` 仍为编排层 API；CLI 与 API 共用同一 `classify()` 分级逻辑。

## 6. 评分体系边界：寻访三维 vs 五维（防混用断言，G7）

> 团队存在两套独立的量化评分体系，口径不同、用途不同，**不得交叉替代或混用**。
> 本边界由 `talent-sourcing` 与 `recruitment-pipeline` 的 playbook 共同约束，主理人在交接环节须断言两者未混用。

| 维度 | 体系 | 权重 | 用途 | 产出方 | 依据 |
|---|---|---|---|---|---|
| 寻访适配三维 | 触达难度 / 在职稳定性 / 薪酬契合度 | 30% / 35% / 35% | **寻访排序**（仅用于决定触达优先级与 A/B/C 分级） | `talent-sourcing`（寻访侧初评） | `skills/talent-sourcing/SKILL.md` §寻访适配三维 |
| 五维评估 | 技术 / 专业 / 学习 / 匹配 / 稳定 | 25% / 20% / 20% / 20% / 15% | **正式任命评估**（录用决策矩阵输入） | `candidate_scorer.py`（由 recruitment-pipeline 在管道内重跑） | `skills/recruitment-pipeline/SKILL.md` §录用决策矩阵 |

**硬边界断言（主理人交接环节须核验）**：

1. 三维分**只用于寻访排序**，不得直接映射为录用建议档位；寻访 shortlist 中若并列呈现三维分与五维分，须各自注明口径（来源：`talent-sourcing` SKILL.md「该分只用于寻访排序，不得与五维评分混用或互相替代」）。
2. 五维评分原样复用 `candidate_scorer.py`，**权重不得改动**；寻访侧仅对 A 级候选与关键岗位调用做预筛分，正式评估分由 `recruitment-pipeline` 在管道内重跑，二者数值可不同但口径一致。
3. 任一交付若同时出现两套分数，不得出现「以三维分替代五维分」或「以五维分反推触达优先级」的混用结论；出现即判质量闸门 `field_completeness` 之外的口径冲突，回炉重评。
4. SBTI 人格测评（`personality-assessment` 的 `sbti_assessment.py`）结果**暂不入匹配**：仅当候选人主动授权且已完成测评时，作为 `profile.assessment` 附在档案中；无授权不进入匹配，初评不消费该字段（来源：`talent-sourcing` SKILL.md）。
5. 人才画像（`talent-personas`，群体统计特征，不含个人 PII）与人格测评（个体 `SBTI` 类型码）分属不同口径：画像用于市场/人群侧研判，测评用于个体适配研判，**不得用群体画像替代个体测评结论**。

### 1.7 `envelope.py` — 信封签名 / 验签

**调用形态**：CLI

| 子命令 | 说明 |
|---|---|
| `key-source` | 打印当前签名密钥来源（`env:HRM_ENVELOPE_KEY` / `keyfile:<path>` / `process-random`）|
| `verify <envelope.json> [--max-age SEC]` | 校验信封；打印 `OK`/`INVALID` + 密钥来源；退出 0 / 4 |
| `selftest` | 签名→验签往返自检，打印结果 |

**签名密钥解析顺序**：`HRM_ENVELOPE_KEY` 环境变量 → 持久化密钥文件（`$HRM_ENVELOPE_KEY_FILE`，未设时默认 `<用户数据目录>/hrm-advisory-corps/envelope.key`，首次使用以 `secrets.token_bytes(32)` 生成并以 `0600` 模式写入（POSIX 生效；**Windows 上 `os.open` 模式位与 `os.chmod` 均不改变 ACL**，实测仍为 `0666`，依赖用户数据目录本身的用户级 ACL））→ 进程内随机密钥（仅当密钥文件不可创建，附一次 `RuntimeWarning`）。`HRM_ENVELOPE_STRICT=1` 时无稳定密钥直接抛 `EnvelopeKeyError`。

```bash
python3 scripts/security/envelope.py key-source
python3 scripts/security/envelope.py selftest
python3 scripts/security/envelope.py verify /tmp/env.json --max-age 3600
```

### 1.8 `talent_pool.py` — 人才库 CRUD + 索引维护（talent-sourcing 私有）

> 以下为 **talent-sourcing 私有脚本**，物理位置在 `../../talent-sourcing/scripts/`（即 `skills/talent-sourcing/scripts/`），本文件仅登记入口契约与跨技能引用路径。因两脚本受零三方依赖契约约束、禁止跨技能 import，错误码体系采用与本技能 `errors.py` 同构的内置 `StructuredError` 定义（同名/同属性 `code`/`field`/`severity`），脱敏为内置白名单字段输出 + 明文正则兜底扫描（与 `security/pii.py` 口径一致），运行工作目录为 `skills/talent-sourcing/scripts/`。

**跨技能引用路径**：`../../talent-sourcing/scripts/talent_pool.py`（包根视角：`skills/talent-sourcing/scripts/talent_pool.py`）

**调用形态**：CLI，argparse 子命令

```bash
python3 skills/talent-sourcing/scripts/talent_pool.py [--pool <人才库目录>] <子命令>
```

| 子命令 | 说明 | 关键参数 |
|---|---|---|
| `add --file <JSON>` | 新增候选人档案；无 `source.consent` 同意记录拒绝入库（E060） | `--pool` 默认 `../knowledge/resumes` |
| `get <candidate_id>` | 按 ID 读取档案（脱敏视图） | 未找到 E080 |
| `search` | 条件检索 | `--skill` / `--city` / `--years-min` / `--years-max` / `--labels` / `--status` |
| `update <candidate_id> --file <JSON>` | patch 更新（status / labels / last_contacted_at）；禁止写回明文 PII | — |
| `delete <candidate_id> --operator <人> --reason <依据>` | 物理删除（个保法第四十七条删除权），写审计日志；需主理人确认后执行 | 删除不可恢复 |
| `reindex` | 重建库级 `_index.json`，校验全部档案 | 损坏档案列入报告 |

**输入**：候选人档案 JSON，schema=`talent-resume`（见 `skills/talent-sourcing/knowledge/resumes/R000001.json`）。
**输出**：脱敏视图 JSON；所有输出经 `security/pii.py` `redact_pii` 扫描。
**错误码**：E001 缺字段（含 schema 校验失败）/ E020 类型错误 / E040 值越界 / E060 合规拒绝（无同意记录或检出明文 PII）/ E080 未找到。
**当前状态**：已实现（可运行，已通过自检验证）。add 子命令参数为 `--file`（非位置参数）。

### 1.9 `sourcing_matcher.py` — 寻访匹配引擎（talent-sourcing 私有）

**跨技能引用路径**：`../../talent-sourcing/scripts/sourcing_matcher.py`（包根视角：`skills/talent-sourcing/scripts/sourcing_matcher.py`）

**调用形态**：CLI

```bash
python3 skills/talent-sourcing/scripts/sourcing_matcher.py --req <J-id|JSON> [--pool <目录>] [--req-dir <目录>] [--top N] [--envelope]
```

| 参数 | 说明 | 必填 |
|---|---|---|
| `--req <J-id|JSON>` | 职位需求：J 系列 ID 或 requisition JSON 字符串 | 是 |
| `--req-dir <目录>` | 职位需求库目录，默认 `../knowledge/requisitions` | — |
| `--pool <目录>` | 人才简历库目录，默认 `../knowledge/resumes` | — |
| `--top <N>` | 返回前 N 个匹配结果，默认 10 | — |
| `--envelope` | 经 engine_service 输出统一 schema（status/version/payload/errors/warnings） | — |

**匹配口径**：技能命中率×50% + 年限契合×20% + 城市匹配×15% + 目标公司/行业契合×15%（权重可调，与 `skills/talent-sourcing/SKILL.md` 一致）。三级关键词（标准名/细分赛道专属名/行业通用别名）均参与匹配，命中权重依次降权（`standard_terms` 1.0 / `niche_terms` 0.8 / `aliases` 0.5，与 `sourcing_matcher.py` 的 `KEYWORD_TIER_WEIGHT` 常量为同一权威口径）；人才地图 `tiers` 作为目标公司过滤条件（命中即 `tier_hit=true` 且公司分得满分，排序 tier_hit 优先）。

> **`sourcing_profile.exclude` 的处置说明**：exclude 条目为自然语言行为条件（如「频繁跳槽（3段<1年）」），而候选人档案 schema 当前无对应结构化字段可确定性判定，硬编码过滤误伤风险高，故本版**未实现 exclude 硬过滤**，此类条件在入库/建档阶段处理。后续 resume schema 增加结构化字段（如 job_history 段数）后可回补。

**输出结构**：

```json
{
  "req_id": "J000001",
  "total_matched": 1,
  "results": [
    {
      "candidate_id": "R000001",
      "match_score": 0.48,
      "breakdown": {"skill": 0.11, "years": 1.0, "city": 1.0, "company": 0.5},
      "tier_hit": false,
      "labels": ["后端", "高潜", "电商"],
      "evidence": {"skill": ["微服务(standard_terms×1.0)"], "years": "6 年落于区间 [5, 8]", "city": "同城市（杭州）", "company": "行业相邻"}
    }
  ]
}
```

> `match_score` 为 0–1 区间保留两位小数；`evidence` 逐项记录命中依据（含三级关键词权重标记）。`--envelope` 当前为预留参数（argparse 接受但不改输出形态），engine_service 接线待后续版本。

### 1.10 `quality_gate.py` — 输出契约质量闸门

> 协作层硬约束工具。对成员回传 JSON 做机器可采集的结构化校验，输出各指标 pass/fail + 综合质量分 + status，作为团队级 QM-01~QM-11 的采集来源。零三方依赖。

**调用形态**：CLI，argparse 子命令

```bash
python3 skills/hrm-solution/scripts/quality_gate.py check <回传.json> [--spec <id>] [--max-age <秒>] [--json]
python3 skills/hrm-solution/scripts/quality_gate.py list-specs [--json]
python3 skills/hrm-solution/scripts/quality_gate.py aggregate <报告.json...> [--dir <目录>] [--json]
```

| 子命令 / 参数 | 说明 |
|---|---|
| `check <file>` | 校验单份回传（信封形态 / 五字段契约 / 信封内嵌 payload 三种形态均支持） |
| `--spec <id>` | 追加 specialist 字段完整度校验（`talent-sourcing` / `recruitment-pipeline` / `labor-compliance`）；**显式传入时为必须项**，不通过即整体 fail |
| `--max-age <SEC>` | 信封时效上限（秒），超出判签名失效 |
| `list-specs` | 列出全部 `--spec` 规则（不编造，均来自实读 playbook 输出规范） |
| `aggregate` | 汇总多份质量报告，输出团队级各指标通过率；**存在不可解析文件时退出码 1** |

**校验指标**（`metrics` 键）：

| 指标 | 含义 |
|---|---|
| `envelope_signature_valid` | HMAC 验签（复用 `security/envelope.py`）；自称信封但字段残缺一律判 FAIL |
| `return_contract_complete` | 五字段齐全**且已填写**（空串/纯空白/`TODO`/`N/A`/`略`/`待补充` 等占位符一律视为缺失） |
| `compliance_citation_complete` | 合规结论带法条出处 + 基准日期 + 核实状态 |
| `compliance_gate_blocked` | 复用 `security/compliance_gate.py` 全文风险分级；`BLOCKED` 判 FAIL |
| `pii_masked` | 复用 `security/pii.py` 检出明文 PII |
| `field_completeness` | `--spec` 字段完整度（空列表视为无交付，判 FAIL） |

**输出**：`file` / `spec` / `score` / `score_raw` / `status` / `failed_must` / `metrics`。
**退出码**：0=pass / 1=fail（任一必须项未过）/ 2=参数或运行错误。
**必须项**：`envelope_signature_valid`、`return_contract_complete`、`compliance_citation_complete`、`compliance_gate_blocked`、`pii_masked`；显式 `--spec` 时追加 `field_completeness`。
**计分口径**：跳过项（`pass:null`）计入分母但不计通过（no-credit），避免「靠剔除检查拿满分」；必须项失败时总分封顶 60（`MUST_FAIL_CAP`），保证 `score` 与 `status` 不自相矛盾。

### 1.11 `task_ledger.py` — 任务生命周期账本

> 协作层硬约束工具。以单一 JSON 文件为账本，提供跨阶段状态真相源 + 重试预算 + 熔断 + 死信队列，**强制执行**状态机（非法流程直接拒绝）。零三方依赖。

**调用形态**：CLI，argparse 子命令

```bash
python3 skills/hrm-solution/scripts/task_ledger.py [--store <账本.json>] [--max-retries N] [--circuit-threshold N] <子命令>
```

| 子命令 | 说明 | 关键参数 |
|---|---|---|
| `spawn <task_id> <agent>` | 登记任务；agent 熔断 open 时拒绝 | `--intent` |
| `dispatch <task_id>` | 派单；**先查熔断**，open 状态拒绝（exit 2） | — |
| `return <task_id>` | 记录回传；带 `--envelope` 时实时验签 | `--envelope` |
| `verified <task_id>` | 记录校验结论；**`--ok` 默认 false（fail-closed）** | `--ok true\|false` |
| `gate <task_id> <PASSED\|BLOCKED>` | 记录合规闸结论；`BLOCKED` 落盘 `blocked` 标志 | — |
| `deliver <task_id>` | 交付；**BLOCKED 任务硬拒**（E030），阶段非法迁移亦拒（E099） | — |
| `fail <task_id>` | 记一次失败；超重试预算进死信 | `--reason` / `--code` |
| `retry <task_id>` | 预算内重发；已交付/死信/熔断中均拒绝 | — |
| `can-dispatch <agent>` | 查询熔断状态 | — |
| `status` / `summary` / `dashboard` | 单任务状态 / 团队汇总 / QM-08~09 看板 | — |

**阶段状态机**：`spawned → dispatched → returned → verified → gated → delivered`；失败可回退 `returned` 或进 `dead_letter`；`delivered` 为终态。合法迁移表见 `LEGAL_TRANSITIONS`，非法跳跃以 exit 2 + 结构化错误 `illegal_transition` 拒绝。
**持久化**：原子写（同目录临时文件 + `os.replace` + `fsync`）；账本损坏时隔离为 `<store>.corrupt` 并告警，不静默沿用。
**错误码**：见 §3 的 E030 / E041 / E099。

**错误码**：E001 缺字段（如 capability_weights 权重合计不为 100）/ E020 类型错误 / E040 值越界 / E080 未找到（req_id 或 pool 目录不存在）。
**当前状态**：已实现（可运行，已通过自检验证）。

## 2. 跨脚本统一返回 schema

统一 schema 由 `engine_service.py` 提供——`dispatch_envelope(endpoint, payload)` 返回：

```json
{
 "status": "ok|error",
 "version": "3.3.0",
 "baseline_date": "2026-01-01",
 "payload": { ... },
 "errors": [{"code": "E001", "message": "...", "field": "baseSalary", "severity": "fatal"}],
 "warnings": [{"code": "W001", "message": "...", "field": "bonusAmount", "severity": "warning"}]
}
```

| 字段 | 类型 | 含义 |
|---|---|---|
| `status` | enum | `ok`=成功；`error`=任一 fatal |
| `version` | semver | 引擎 schema 版本 |
| `baseline_date` | ISO date | 法规 / 政策类数据基准日期 |
| `payload` | object | 引擎专属结果 |
| `errors[]` | array | 致命错误对象（`code` / `message` / `field` / `severity`）|
| `warnings[]` | array | 警告对象（不影响 `status`，码表见 §3）|

**调用入口**：

```python
from engine_service import dispatch_envelope
env = dispatch_envelope("payroll.monthly", {"baseSalary": 25000, "city": "深圳"})
# env["status"] == "ok"; env["payload"]["net_pay"] == "18943.75"
```

或 CLI：

```bash
python3 engine_service.py --envelope payroll.monthly '{"baseSalary":25000,"city":"深圳"}'
```

> **向后兼容**：3 个引擎的**独立 CLI 输出结构保持不变**（`payroll_engine.py` 等旧调用方零改动）；统一 schema 仅新增在 `engine_service` 层。旧 `dispatch` / `dispatch_json` 仍可用。

### 2.1 三引擎独立 CLI `--envelope`

三引擎各新增 `--envelope` 开关，命中时经 `engine_service.dispatch_envelope_json` 输出统一 schema；**不传时字节级保持旧输出**（向后兼容硬约束）。

| 引擎 | 命令 | 端点映射 |
|---|---|---|
| `payroll_engine.py` | `python3 payroll_engine.py --envelope --payroll '<JSON>'` | `payroll.monthly` |
| `payroll_engine.py` | `python3 payroll_engine.py --envelope --bonus 36000` | `payroll.bonus`（body=`{"bonusAmount":36000}`）|
| `candidate_scorer.py` | `python3 candidate_scorer.py --envelope --scores '<JSON>'` | `candidate.score` |
| `org_health.py` | `python3 org_health.py --envelope <org.json>` | `org.health` |

> CLI 顶层惰性 `from engine_service import dispatch_envelope_json`，`engine_service` 顶层导入三引擎但三引擎顶层不导入 `engine_service`（仅导入共享 `errors`），无循环导入。

## 3. 错误码字典

> 错误码由各引擎 raise 站点显式给定 `code` / `field`（异常继承 `scripts/errors.py` 的 `StructuredError`）。`engine_service._classify_error` 按优先级读取：`_NotFound`→`E080`；直抛 `_BadRequest`→读自身 `.code`（默认 `E020`）；包装异常→读 `exc.__cause__.code`；均未命中才回退关键词启发式 `_classify_error_legacy`。下面字典为**单一基准**。

| 范围 | 类别 | 严重度 |
|---|---|---|
| `E001-E019` | 缺必填字段 | fatal |
| `E020-E039` | 类型错误 | fatal |
| `E040-E059` | 值越界 | fatal |
| `E060-E079` | 跨字段约束违反 | fatal |
| `E080-E099` | 内部错误 | fatal |
| `W001-W019` | 警告（不影响 `status=ok`）| warning |
| `W020-W099` | 建议性警告 | warning |

**错误码**：

| 错误码 | 来源 | 触发 | field |
|---|---|---|---|
| `E001` | `payroll_engine.py` | 必填字段缺失（如 `baseSalary` 缺失或写成 `base_salary`）/ `city` 缺失 | `baseSalary` / `city` |
| `E020` | `payroll_engine.py` | 字段类型错误（如 `baseSalary: "25000"` 字符串）/ year/month 越界 / 可选数值非数字 / 记录非对象 | `<key>` / `year` / `month` / `null` |
| `E040` | `payroll_engine.py` | 字段值越界（`baseSalary: -1` 负数）/ 可选数值负数 / 超出合理上限（1e12）| `baseSalary` / `<key>` |
| `E060` | `payroll_engine.py` | 跨字段约束（累计值部分提供）| `null` |
| `E001` | `org_health.py` | 缺 `teams` / `total_depth` 或 `teams` 空 / 全员 `manager_only` / 无管理者 | `total_depth` / `teams` |
| `E020` | `org_health.py` | 未知顶层键 / 团队缺 `size` 或类型错 / 类型范围错 | `foo`（首个未知键）/ `teams[i].size` / `<scope>` |
| `E001` | `candidate_scorer.py` | 缺评分维度（可多维度）| `", ".join(missing)` |
| `E020` | `candidate_scorer.py` | 维度非数字 | `<dim>` |
| `E040` | `candidate_scorer.py` | 维度越界（非 0-10）| `<dim>` |
| `E080` | `engine_service.py` | 未知端点（`_NotFound`）| `null` |
| `E020` | `engine_service.py` | `bonusAmount` 非数字 / `payload` 非对象（直抛 `_BadRequest`）| `bonusAmount` / `null` |
| `E030` | `task_ledger.py` | 任务处于 BLOCKED 状态仍试图 `deliver`（合规闸硬规则：BLOCKED 不得进 deliver）| `task_id` |
| `E041` | `task_ledger.py` | 回传信封验签失败 / 不可读，或 `verified --ok false` 校验未过 | `task_id` |
| `E099` | `task_ledger.py` | 非法阶段迁移（如 `spawn → deliver` 跳步）；亦为 `fail` / `retry` 的默认错误码 | `task_id` |

> `task_ledger.py` 的三类拒绝以 exit 2 + 结构化 JSON（`{"error": "...", "code": "...", "task_id": "...", "reason": "..."}`）输出到 stdout，错误摘要同时写 stderr。

**警告码**：

| 警告码 | 端点 | 触发 | field |
|---|---|---|---|
| `W001` | `payroll.bonus` | 输出 `in_trap_range is True`（年终奖跳档陷阱）| `bonusAmount` |
| `W002` | `payroll.monthly` | 未提供任一累计值且 `month > 1` | `cumulativeIncome` |
| `W003` | `org.health` | 输出 `risks[]` 中 `severity == "WARNING"` 的软风险（逐条投影）| `null` |


## 4. 调用样例

### 4.1 薪酬计算

```bash
python3 scripts/payroll_engine.py --payroll '{
 "employeeId":"E001",
 "employeeName":"张三",
 "baseSalary":25000,
 "city":"深圳",
 "year":2026,
 "month":3,
 "cumulativeTaxPaid":1200
}' # Windows 解释器为 python
```

**输出**：`gross_pay=25000.00 / net_pay=18782.50 / tax_amount=592.50`

### 4.2 候选人评分

```bash
python3 scripts/candidate_scorer.py --scores '{
 "technical": 8.5, "professional": 8, "learning": 9, "role_fit": 8.5, "stability": 6
}' --candidate "李四"
```

**输出**：`overall=8.1 / recommendation=recommend / risk_level=low`

### 4.3 组织健康度

```bash
# 准备文件
cat > /tmp/org.json <<'JSON'
{
 "teams": [
 {"name": "研发组", "size": 8, "manager": true, "manager_count": 1, "manager_only": false}
 ],
 "total_depth": 5
}
JSON

python3 scripts/org_health.py /tmp/org.json
```

**输出**：4 项指标全 `healthy`，无 risks

### 4.4 错误触发示例

```bash
# 缺必填 → E001
python3 scripts/payroll_engine.py --payroll '{"city":"北京","year":2026,"month":3}'
# → "薪资计算失败：必填字段 `baseSalary` 缺失（注意：入参键名为 camelCase，传成 snake_case 如 base_salary 会被视为缺失）"

# snake_case → E001
python3 scripts/payroll_engine.py --payroll '{"base_salary":25000,"city":"北京"}'
# → 同上（base_salary 不会被识别为 baseSalary）

# org_health 未知键 → E001
python3 scripts/org_health.py /tmp/bad.json # 含 teams 之外的未知键
# → OrgSchemaError
```

## 5. 使用注意

1. **独立 CLI 与统一 schema 的输出结构不同**——`payroll_engine.py --payroll` 等独立调用**不传 `--envelope` 时**输出引擎原生结构（向后兼容）；传 `--envelope` 时经 `engine_service.dispatch_envelope_json` 输出统一 schema（见 §2.1）。
2. **跨进程信封验签默认可用**——签名密钥按 `HRM_ENVELOPE_KEY` 环境变量 → 持久化密钥文件（`$HRM_ENVELOPE_KEY_FILE`，未设时默认 `<用户数据目录>/hrm-advisory-corps/envelope.key`，首次自动生成并以 `0600` 模式写入；**Windows 上权限位不生效**，依赖用户数据目录 ACL）→ 进程内随机密钥的顺序解析。未注入环境变量时，同一用户下的不同进程**默认共享密钥文件、可互验**；仅当密钥文件不可创建时才降级为进程内随机密钥（此时跨进程互验失败）。生产环境建议显式注入 `HRM_ENVELOPE_KEY`，并设 `HRM_ENVELOPE_STRICT=1` 让缺失稳定密钥直接失败。可用 `key_source()` 或 `python3 envelope.py key-source` 查询当前来源。
3. **`--envelope` 的退出码与输出流（四入口统一）**——`payroll_engine.py` / `candidate_scorer.py` / `org_health.py` / `engine_service.py` 四个入口在 `--envelope` 下语义一致：**信封构造成功后（派发级错误）**，`status:"ok"` → 退出 **0**，`status:"error"` → 退出 **2**，且完整统一 schema JSON **一律打印到 stdout**（便于 `| jq` / `> file` 消费），stderr 不另写内容。**信封构造之前的错误不受本约定覆盖**：CLI 参数解析级（如 `--envelope --bonus abc`）与文件 IO 级（如 `org_health.py --envelope /不存在.json`）错误仍按各入口既有方式报错、退出码非 0、**不产出信封**（stdout 为空）。本约定**仅作用于 `--envelope` 分支**；非 `--envelope` 路径的退出码不受影响（保持各自既有的向后兼容语义）。
4. **错误码为结构化确定值**——错误码由各引擎 raise 站点显式给定 `code` / `field`，`engine_service` 确定性读取；未显式给定的部分回退关键词启发式 `_classify_error_legacy`。
5. **合规闸门 CLI 与 API 同源**——`compliance_gate.py --text '<TEXT>'` 的输出/退出码语义为：JSON 分级结果打印到 stdout，`PASSED`/`FLAGGED` 退出 0、`BLOCKED` 退出 3（另写 stderr）。编排层 `finalize()` 与 CLI 共用同一 `classify()`；CLI 结果不得替代 `finalize()` 对信封合规字段的写入。
