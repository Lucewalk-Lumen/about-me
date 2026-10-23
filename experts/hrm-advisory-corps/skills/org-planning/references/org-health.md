# Organization Health Baseline

> 标准定义：组织架构诊断指标、Headcount 预测、架构模型比选。引用方：org-planning。配套脚本：`../hrm-solution/scripts/org_health.py`。

## 健康度指标

| 指标 | 健康区间 | 警告阈值 |
|------|---------|---------|
| 管理幅度 span_of_control | 5-8 人 | <3 或 >12 |
| 管理层级 hierarchy_depth | 4-6 层 | >6 决策慢 |
| IC:经理比 ic_manager_ratio | 6:1 到 10:1 | <4:1 头重脚轻 |
| 团队规模 team_size | 5-9 人 | <4 孤立，>12 难管 |

## 风险类型

- 头重脚轻（管理岗占比过高）
- 管理裂化（幅度过小导致层叠冗余）
- 决策链过长（层级过多）
- 团队孤立（规模过小）

## Headcount 需求预测字段

```
岗位名称 / 层级 / 数量 / 优先级(P0/P1/P2) / 预估人力成本 / 建议入职时间
```

## 架构模型比选

| 模型 | 适用场景 | 备注 |
|------|---------|------|
| 职能型 functional | 稳定业务 | 专业分工明确 |
| 事业部型 divisional | 多产品线 | 独立核算 |
| 矩阵型 matrix | 项目制 | 双线汇报，需协调机制 |
| 扁平型 flat | 创业初期 | 决策快，幅度大 |

## 输入结构（org.json，键名严格校验）

```json
{
  "teams": [
    {"name": "研发组", "size": 8, "manager": true, "manager_count": 1, "manager_only": false}
  ],
  "total_depth": 5
}
```

| 位置 | 键 | 必填 | 约束 |
|------|----|:----:|------|
| 顶层 | `teams` | 是 | 非空数组，不接受未知顶层键 |
| 顶层 | `total_depth` | 是 | ≥1 的整数（组织层级数） |
| team | `size` | 是 | ≥1 的整数（团队人数） |
| team | `name` | — | 字符串 |
| team | `manager` | — | 布尔，该团队是否配管理者 |
| team | `manager_count` | — | ≥0 的整数。**参与 IC:经理比计算**：给出且 >0 时按真实管理者人数计入 `total_managers` 并从 `size` 中扣除得出 IC；未给出时回退为 `manager` 布尔（计 1 或 0） |
| team | `manager_only` | — | 布尔，纯管理团队不计入管理幅度（`spans`），且该团队全员计为管理者、IC 计 0 |

**fail-fast 约定**：键名拼写错误（如误用 `departments` / `totalHeadcount`）、类型错误、缺失必填键、
teams 全为 `manager_only`、或无任何 `manager: true`，脚本一律抛 `OrgSchemaError`、
stderr 输出可操作提示并以退出码 **2** 结束。**不允许**静默产出全空指标的"看似成功"报告。

## 输出结构

```json
{
  "org_health": { "span_of_control": {"min":N,"max":N,"avg":N,"status":"healthy|warning|critical"}, "hierarchy_depth": {...}, "ic_manager_ratio": {...}, "team_size": {...} },
  "risks": [{"type":"头重脚轻|管理裂化|决策链过长|团队孤立","severity":"P0|P1|P2","detail":"..."}],
  "headcount_plan": [{"role":"...","level":"P5|P6|P7","qty":N,"priority":"P0|P1|P2","cost_estimate":N,"target_quarter":"Q1-Q4"}],
  "architecture_recommendation": {"model":"functional|divisional|matrix|flat","rationale":"...","alternatives_considered":[...]},
  "hiring_roadmap": [{"phase":"Q1-Q4","roles":[...],"total_headcount":N,"milestone":"..."}]
}
```

## 使用纪律

- 不输出未经健康度诊断的 Headcount 建议
- 无业务战略输入时先请求澄清，不凭空预测
- 不对具体个人做晋升/调岗决定
- 薪酬预算审批转交 compensation-strategy
