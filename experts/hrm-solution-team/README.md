# HRM 智能方案团

面向中国大陆市场的多角色 HR 专家团，覆盖组织规划、招聘管道、人才发展、绩效管理、薪酬策略、劳动合规六大模块，并内置模拟面试、培训体系设计、HR 数字化落地与经营运营简报能力，统一合规闸门把关。

## 结构
- `agents/` — 1 名总调度（`lead`）+ 7 名模块专家（`org-planning` / `recruitment-pipeline` / `talent-development` / `performance-management` / `compensation-strategy` / `labor-compliance` / `personality-assessment`）
- `skills/hrm-solution/`（**行为/契约共享**基座）— `contracts.md`（hard rules + 输出契约单一基准）、`routing.yaml` 指针、引擎入口表、共享知识 `knowledge-map`/`integration-catalog`/`hr-toolset`、跨 Agent 安全脚本 `scripts/security/`
- `skills/<id>/`（7 个 scoped 领域技能，id ∈ org-planning / recruitment-pipeline / talent-development / performance-management / compensation-strategy / labor-compliance / personality-assessment）— 各域私有 playbook（SKILL.md）+ 私有 KB（references/）+ 专属模板/资产
- `skills/hr-practice-library/`（**资产共享**库）— 199 份 HR 制度/表单模板（全 ASCII 路径 `templates/<MODULE_CODE>/<policy|form>/<Fnnn>.docx`，附 `templates/INDEX.csv` 清单）、连接总索引与检索器（`knowledge/` + `scripts/query_forms.py`）、数据契约 `schema.json`、协同指南 `GUIDE.md`；连接数据已内置，按模块归口到 7 个 scoped 技能/agent，经共享基座的 `skills/hrm-solution/scripts/security/compliance_gate.py` 终检
- `routing.yaml` — 意图路由表（外部化单一基准）
- `avatars/` — 团队与成员头像

> **两个「共享」目录的边界**（术语固化，二者不重叠）：
> `skills/hrm-solution/` 是**行为/契约共享**——所有成员 agent 的**必经**加载项，定义「怎么做」（路由语义、契约、引擎入口、安全横切）；
> `skills/hr-practice-library/` 是**资产共享**——模板与检索索引，**按需检索**（artifact 路由），定义「用什么」。

## 能力描述
完整能力体系按模块归属下沉至各 `skills/<id>/`（id ∈ 7 个领域），共享基座 `skills/hrm-solution/` 仅保留契约、路由、引擎入口与共享知识（knowledge-map / integration-catalog / hr-toolset）；领域结论由对应成员 Agent 私有产出，统一合规闸门把关。

## 架构要点
- **契约化**：路由表 `routing.yaml` 为单一基准（匹配语义见其文件头：归一化 + 三层裁决）；跨 Agent 用结构化消息信封（实现见 `skills/hrm-solution/scripts/security/envelope.py`）。
- **服务化**：计算引擎经 `engine_service.py` 进程内注册调度，例如 `python3 skills/hrm-solution/scripts/engine_service.py payroll.bonus '{"bonusAmount":37000}'`（Windows 上解释器名为 `python`）。
- **安全横切**：PII 脱敏、append-only 审计、合规闸门 P0-P3 强制终检、信封 HMAC 签名。
- **隐私声明**：个人数据的存储位置、同意前置、脱敏与删除权、以及「本包脚本不发起任何出站网络请求」的完整说明见 `PRIVACY.md`。
- **信封密钥**：签名密钥持久化在用户数据目录，跨进程验签**默认可用**；可用环境变量 `HRM_ENVELOPE_KEY` 覆盖，`envelope.py key-source` 查询当前密钥来源，`envelope.py key-protect` 查询密钥文件保护状态（退出码 0=已保护 / 1=未保护）。
  文件权限的**平台差异与加固**：脚本以 `0600` 模式创建（POSIX 上生效）；**Windows 上 `os.open` 的模式位与 `os.chmod` 均不改变 ACL**（实测权限位仍为 `0666`），因此在创建/读取密钥文件后会**主动调用 `icacls`**（`/inheritance:r /grant:r "<USER>:F"`，`<USER>` 取 `USERDOMAIN\USERNAME`）关闭继承并仅授予当前用户，随后回读 `icacls` 输出**校验**「继承已关闭且仅当前用户被授权」。
  **降级边界（如实说明，不承诺过头）**：若 `icacls` 不存在 / 被安全策略拦截 / 返回非 0 / 校验不通过，主流程**不中断**，仅发告警并降级为「保密性依赖 `%APPDATA%\hrm-solution-team\` 目录本身的用户级 ACL」；开启 `HRM_ENVELOPE_STRICT=1` 时该情形改为**直接报错**。此外，**当 `APPDATA` 与 `LOCALAPPDATA` 均不可用时不再回退到系统临时目录**（世界可写），而是视为「无安全位置」、降级为进程内随机密钥（`HRM_ENVELOPE_STRICT=1` 下报错）。需要强隔离时请显式设置 `HRM_ENVELOPE_KEY`。

## 安装
将本目录（目录名即 `hrm-solution-team`，与 `plugin.json.name` 一致）整体放入运行环境的扩展目录并启用即可；`name` 与 `source` 严格对齐，无注册隐患。默认零容器、零三方依赖。

## 跨平台说明
- 纯 Python 标准库实现，零三方依赖，跨 Windows / macOS / Linux；目标机需安装 **Python 3.7+**（脚本使用惰性类型注解，3.7 起可运行，推荐 3.10+）。
- 运行脚本时命令为 `python3`；**Windows 上解释器名通常为 `python`**（官方安装器 / Microsoft Store），少数环境才有 `python3`。
- **Shell 脚本的平台限制**：`skills/hrm-solution/scripts/hr_toolset.sh`、`skills/hrm-solution/scripts/okr_tracker.sh`、`skills/hrm-solution/scripts/workforce_plan_tracker.sh` 为 POSIX shell 脚本，需在 Git Bash / WSL / macOS / Linux 下运行；Windows 原生 CMD / PowerShell 无法直接执行。**三个 Python 计算引擎（`skills/hrm-solution/scripts/payroll_engine.py`、`skills/hrm-solution/scripts/org_health.py`、`skills/hrm-solution/scripts/candidate_scorer.py`）为纯标准库实现，全平台可用，不依赖上述 shell 脚本。**
- 审计日志（`audit.log`）默认写在用户级数据目录（`~/.local/share/hrm-solution-team/audit.log`；Windows 为 `%APPDATA%/hrm-solution-team/audit.log`，并遵循 `XDG_DATA_HOME`），**不写入脚本/插件安装目录**；若用户目录不可写（如受限账户或只读家目录），回退到系统临时目录下的 `hrm-solution-team/audit.log` 并显式告警；路径为首次写入时惰性解析，仅做可写性判定、不创建任何文件，也不因此中断主流程。
- 所有中文 I/O 均显式 `utf-8`，路径用 `os.path` 解析，无 Unix 专属假设。

## 使用提醒（脚本 JSON 入参为 camelCase，且已 fail-fast 校验）

三个 Python 引擎从 JSON 读入参数，键名均为 **camelCase**。引擎已做 fail-fast 强校验：**必填字段缺失**、传成 snake_case（如 `base_salary`）、或类型不符（如工资传字符串）会直接抛错并退出，**不会静默回退默认值**（`baseSalary` / `city` 缺失时报 `E001`）。

下表中的「默认」列仅对**可选字段**生效：必填字段不参与默认值回退。

`skills/hrm-solution/scripts/payroll_engine.py` 单月计算（`--payroll`）的 JSON 字段：

| 字段 | 含义 | 必填 | 默认（仅可选字段生效） |
|------|------|------|------------------------|
| `employeeId` | 员工 ID | 否 | `""` |
| `employeeName` | 员工姓名 | 否 | `""` |
| `baseSalary` | 基本工资 | **是** | —（缺失报 `E001`） |
| `city` | 城市（北上广深杭） | **是** | —（缺失报 `E001`） |
| `year` / `month` | 计算年月 | 否 | `2026` / `1` |
| `positionAllowance` | 岗位津贴 | 否 | `0` |
| `performanceBonus` | 绩效奖金 | 否 | `0` |
| `overtimePay` | 加班费 | 否 | `0` |
| `otherIncome` | 其他收入 | 否 | `0` |
| `otherDeductions` | 其他扣除 | 否 | `0` |
| `specialDeduction` | 专项附加扣除 | 否 | `0` |
| `cumulativeTaxPaid` | 截至上月累计已缴个税 | 否 | `0` |
| `insuranceBase` | 社保公积金缴费基数（不传则按应发工资） | 否 | 不传则按应发工资 |
| `cumulativeIncome` / `cumulativeInsurance` / `cumulativeSpecial` | 真实累计值（可选，支持变额月薪） | 否 | 不传则退化为每月恒定 |

调用示例：

```bash
python3 payroll_engine.py --payroll '{"employeeId":"E001","employeeName":"张三","baseSalary":25000,"city":"深圳","year":2026,"month":3,"cumulativeTaxPaid":1200}' # Windows 用 python
```

## 版本演进
版本迭代记录见 [CHANGELOG.md](./CHANGELOG.md)（CodeBuddy 官方更新日志格式）。

## 提交前自检（维护者）

本包是 WorkBuddy 专家团资产，**上线分发前必须走官方工具链**，不要手写 zip。以下流程已在修复发布驳回问题时实证有效：

1. **门禁以官方校验器 `validate_expert.py` 为权威**——平台 `expert-manager` 自带的该脚本返回码即最终判据，须为 0。
   **注意**：不要以「注册脚本 `register_expert.py` 返回成功」当作通过依据：它走的是**弱校验**，对存在 error 的包同样返回成功并提示「已注册可见」（**假绿**），这正是本地看起来全绿、线上却被驳回的根因。三个官方脚本角色务必分清：`validate_expert.py` = 权威判据；`package_expert.py` = 出包；`register_expert.py` = 弱校验、**不可作为通过依据**。
2. **出包只允许用官方打包器 `package_expert.py`**——其 output-dir 是**位置参数**（误传 `-o` 会在当前目录建出名为 `-o` 的目录）。产物顶层必须带 `<包名>/` 包裹层，且**包裹层名 == `.codebuddy-plugin/plugin.json` 的 `name`**。
3. **纯净性**——包内不得含 `__pycache__` / `.pyc` / `.bak` / `.orig` / `.tmp` / `~` / `.DS_Store` / `Thumbs.db` / `.gitkeep`，也不得放入任何自检/审计脚本。
   注意官方打包器**只**过滤 `.` 前缀目录（`.codebuddy-plugin` 除外）、`__pycache__`、`node_modules` 与上述三个系统文件，**其余须自行保证**。
4. **硬规则一致性**——`.codebuddy-plugin/plugin.json` 中 team 型要求 `profession.zh == displayName.zh`；`agents/*.md` frontmatter **不得**含 `tools:`；团队配置文件名必须是 `settings.json`。
5. **版本一致性**——全包版本号一致（`plugin.json` + 各 `SKILL.md` + 实务工具库的三个索引 JSON（模块映射 / 实践索引 / 连接总览）+ shell 脚本），且 `CHANGELOG.md` 有对应条目。
6. **资源对应**——`templates/**/Fnnn.docx` 与 `knowledge/forms/Fnnn.json` 必须**编号一一对应**（当前 199 ↔ 199，缺口 / 重号 / 单边存在均为 0）。
7. **产物核对**——条目数、junk 数、zip 内版本 == 源版本、关键文件与源逐位一致。
8. **改动后必须重跑**——任何内容改动都会使上一次的放行结论失效；尤其注意**打包暂存缓存**若未按内容指纹失效，可能用旧内容出包而门禁仍报「一致」。
9. **占位符使用规范**——`[XXX]` / `[待补充]` / `[占位内容]` 这类占位标记用于**PII 脱敏、输出格式模板、字段示意**时属**合规用法**，与「未完成 TODO」区别对待：前者是产品设计的一部分（`skills/hrm-solution/references/hr-toolset.md` 即专门定义了占位符写法），后者才是需要清理的未竟事项。**注意误报**：若自检工具不区分上下文，会对**模板型占位**产生误报 —— 处于`引用块 / 代码块 / JSON 示例 / 表格字段示意`中的占位标记，以及自然语言中的普通名词 `todo`，均不应计为未完成项。

## 合规与可依据
- **法规依据**：《劳动法》《劳动合同法》《社会保险法》、个人所得税累计预扣法及配套规定；具体条款适用以最新官方文本为准，本包不构成法律意见。
- **技术栈**：Python 3.7+ 标准库（零三方依赖）；配置用 YAML/JSON；跨 Agent 消息采用 HMAC 信封签名（见 `skills/hrm-solution/scripts/security/envelope.py`）。
- **许可**：MIT（见 `LICENSE`）；作者：Xing Bu。
- **模板权属**：`skills/hr-practice-library/templates/` 下的 199 份 `.docx` 模板原件为第三方材料，**不在 MIT 授权范围内**（见 `LICENSE` 第 4 条）；再分发须另行取得权利人许可。

## 作者与版权

> 作者：Xing Bu
>
> 本方案团（HRM 智能方案团）由 Xing Bu 设计、整合与维护。能力体系遵循中国大陆劳动法规与 HR 专业标准；引用法规条文与税率表以官方最新发布为准。
