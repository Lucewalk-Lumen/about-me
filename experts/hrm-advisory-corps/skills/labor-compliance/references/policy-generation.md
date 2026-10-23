# HR Policy Document Generation

> 标准定义：人事政策文档生成器的输入输出协议。引用方：labor-compliance。

## 六输入

| 名称 | 类型 | 必填 | 说明 |
|------|------|------|------|
| company_size | text | 是 | 员工人数及办公地点分布 |
| work_arrangement | text | 是 | 现场/远程/混合办公 |
| jurisdiction | text | 是 | 适用劳动法律法规（如中国上海） |
| current_policy | text | 否 | 现有考勤与休假政策 |
| employee_feedback | text | 否 | 已知员工意见或诉求 |
| industry_standards | text | 否 | 行业标杆实践 |

## 七输出

| 名称 | 说明 |
|------|------|
| attendance_policy | 完整的考勤与休假政策文档 |
| work_hours_framework | 核心工作时间与弹性安排框架 |
| leave_categories | 年假、病假、育儿假、婚丧假等假别 |
| overtime_policy | 加班认定规则及补偿方式 |
| exception_procedures | 例外情形处理流程（紧急/医疗/特殊需求） |
| compliance_checklist | 劳动法合规性检查清单 |
| communication_plan | 政策发布与员工培训沟通方案 |

## 示例输入

```json
{
  "company_size": "150 人，2 个办公室",
  "work_arrangement": "混合办公 - 每周 3 天办公室，2 天远程",
  "jurisdiction": "中国上海",
  "current_policy": "弹性工时，无限年假（无具体指引）",
  "employee_feedback": "年假申请审批慢；远程办公期间考勤不清晰",
  "industry_standards": "互联网行业普遍采用电子考勤和明确休假指引"
}
```

## 使用纪律

- 政策文档必须包含合规检查清单，且本地化到指定管辖地
- 员工反馈与行业标杆是可选增强输入，缺省时明确标注假设
- 生成的加班/休假规则需转 labor-compliance 复核法定底线
