# HR Toolkit — 常用 HR 文档与流程模板库

> 标准定义：HR 常用文档与流程模板的统一协议。引用方：lead（全员工具）+ recruitment-pipeline + talent-development + labor-compliance + performance-management + compensation-strategy。
>
> 适用场景：通用 HR 工具集（招聘 / 入职 / 离职 / 制度 / 手册 / 模板），一站式 prompt 模板生成。

## 1. 概述

HR Toolkit 是一组**命令化 prompt 模板**，覆盖 HR 全流程中最高频的 6 类输出。所有模板以中文为主，支持中英文双语字段。

**核心理念**：把零散的"想写一个制度"需求，转化为可复用的标准结构（6 输入 + N 输出 + 注意事项）。

## 2. 六大命令与输入输出协议

| 命令 | 输入 | 输出 | 主引用 agent |
|------|------|------|--------------|
| `recruit` | 职位名称 + 级别 + 部门 | JD 6 段 + 面试流程表 + 评估表 + 题库 | recruitment-pipeline |
| `onboard` | 员工姓名 + 职位 | 4 阶段入职清单 + 欢迎信模板 | talent-development |
| `offboard` | 员工姓名 + 离职情况 | 离职申请 + 面谈 + 交接 + 行政 + 证明 | labor-compliance |
| `policy` | 制度类型 | 7 类制度文档之一（考勤/休假/报销/行为/绩效/晋升/远程） | labor-compliance |
| `handbook` | 公司类型 + 行业 | 9 章员工手册完整框架 | lead（全员） |
| `template` | 模板名称或编号 | 20 个常用 HR 文档模板 | lead（全员） |

## 3. 共享输入规范

```json
{
 "company_type": "创业公司 | 中型企业 | 大型企业 | 外企",
 "industry": "互联网 | 制造 | 金融 | 教育 | 医疗 | 零售",
 "position_info": {
 "title": "职位名称",
 "level": "P5 / P6 / P7 / M1 / M2",
 "department": "部门",
 "reports_to": "汇报对象"
 },
 "employee_info": {
 "name": "员工姓名",
 "id_number": "身份证号（脱敏处理，模板中以 [XXX] 占位）",
 "hire_date": "入职日期",
 "exit_date": "离职日期"
 }
}
```

## 4. 共享输出规范

- **中文为主**：默认中文，关键字段（中英文职务、英文邮件签名）保留英文
- **占位符统一**：所有未填写字段使用 `[占位内容]` 形式（方括号 + 中文描述）
- **金额处理**：薪资区间必须含 25 分位 / 50 分位 / 75 分位（市场参考）
- **日期处理**：使用 ISO 8601（YYYY-MM-DD），无歧义
- **本地化合规**：所有制度类输出必须经 `compliance-baseline.md` 二次校验（劳动法底线）

## 5. 与现有章节的关系

| 现有笔记 | 关系 | 说明 |
|----------|------|------|
| `recruiting-pipeline.md` | 互补 | 招聘漏斗方法论 vs 具体 JD 模板 |
| `interview-evaluation.md` | 互补 | 5 维评估框架 vs 面试题库 |
| `resume-quality.md` | 互补 | 简历质量评估 vs 简历生成模板 |
| `performance.md` | 互补 | 绩效周期方法论 vs 制度文档模板 |
| `policy-generation.md` | **强补充** | 通用 6 输入协议 vs 7 类具体制度模板 |
| `compliance-baseline.md` | **必经关卡** | 所有模板生成后必须经其合规校验 |
| `clause-rewrite.md` | 互补 | 条款改写 vs 离职证明模板 |
| `talent-development.md` | 互补 | 培训体系方法论 vs 入职清单模板 |
| `output-templates.md` | 互补 | 简历/面试输出格式 vs 通用 HR 文档模板 |

## 6. 命令本地化要点

| 命令 | 通用做法 | 本地化要点 |
|------|-----------|-----------|
| `recruit` | 4 轮面试（HR/直属/部门/VP） | 国内通用 3-4 轮（HR/直属/部门/HRBP），补"背景调查"独立环节 |
| `onboard` | 入职前 1 周准备 | 改 T-3 天准备（符合国内节奏） |
| `offboard` | 离职提前 2 周通知 | 改 **法定提前 30 天**（《劳动合同法》第 37 条） + 试用期 3 天 |
| `policy` | 7 类制度通用 | **必加《劳动合同法》《劳动合同法实施条例》引用 + 当地人社口径** |
| `handbook` | 9 章框架 | 必加 **第 X 章 工会与职代会**（国内 100 人以上企业必备） |
| `template` | 20 个模板 | 必加 **《解除/终止劳动合同证明》**（人社部规定格式） |

## 7. 使用纪律

- **政策/制度类输出**必走 `labor-compliance` 二次校验（不得跳过）
- **离职类输出**涉及《解除/终止劳动合同证明》的必须用 `clause-rewrite.md` 的标准条款改写
- **模板类输出**金额/比例/时间必须明示假设（"基于公开市场 2025 年中位数估算"）
- **不替代专业法律意见**：所有制度类输出明确加 disclaimer 段

## 8. 不适用场景

- **不直接生成劳动合同条款**：条款生成走 `clause-rewrite.md` 专业路径
- **不替代绩效打分**：绩效走 `performance.md` + `okr-template-library.md`
- **不替代薪酬测算**：薪酬区间走 `compensation-band.md` + `payroll_engine.py`
- **不生成 SBTI 测评内容**：测评走 `sbti_assessment.py` + `personality-assessment` agent

## 9. 命令调用模式（bash 工具入口）

```bash
bash hr_toolset.sh <command> [args...]
# 示例
bash hr_toolset.sh recruit "P6 高级后端工程师"
bash hr_toolset.sh onboard "张三 产品经理"
bash hr_toolset.sh policy "考勤"
bash hr_toolset.sh handbook "创业公司 互联网"
bash hr_toolset.sh template "offer letter"
```

## 10. 与 PII 边界

- 模板中所有个人姓名使用 `[姓名]` 占位符（绝不写真名）
- 身份证号使用 `[身份证号 XXX]` 脱敏占位
- 公司名使用 `[公司名]` 占位
- 模板示例数据使用 RFC 2606 邮箱占位（`<sample-email>`）
