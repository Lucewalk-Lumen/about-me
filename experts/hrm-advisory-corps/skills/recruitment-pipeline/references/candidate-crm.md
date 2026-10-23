# Candidate CRM Profile Standard

> 标准定义：候选人数据模型、双阶段建档、四操作。引用方：recruitment-pipeline。

## 唯一键

**电话号码（phone）是全局唯一键**。兼容三种输入格式：
- `<sample-phone>`
- `<sample-phone>-刘`（手机号-姓名）
- `<sample-phone>-刘.mp3`（通话录音文件名）

不允许用文件名或姓名替代唯一标识。

## 双阶段建档

### 阶段 A：初筛建档（简历画像）

| 字段 | 类型 | 说明 |
|------|------|------|
| phone | string | 唯一键，必填 |
| candidate_name | string | 姓名（可从文件名解析） |
| email | string | 邮箱（简历抽取，用于邀约） |
| gender | string | 男/女/未知 |
| industry | string | 所在行业 |
| current_position | string | 当前职位 |
| years_of_exp | int | 工作年限 |
| project_experience | string | 项目经验总结 |
| technical_capability | string | 技术能力总结 |
| education_level | string | 学历水平 |
| is_qualified | bool | 是否有效候选人 |
| jd_years_match | string | 符合/部分符合/不符合/待确认 |
| jd_match_score | int | 0-100 |
| ai_match_conclusion | string | AI 匹配结论 |
| ai_match_evidence | string | 判断依据（写明来自简历/JD/录音何处） |

### 阶段 B：通话后更新（增量补录）

复用同一 phone，追加：
| 字段 | 说明 |
|------|------|
| transcript_text | 音频转写原文（留存复核） |
| job_switch_intent | 跳槽意向：高/中/低 |
| candidate_focus | 关注重点（薪资涨幅/晋升空间/地点/远程） |
| notes | 备注 |
| final_match_score / final_recommendation | 最终判断 |

## 四操作

| 操作 | 说明 |
|------|------|
| upsert | 新增或更新（按 phone 幂等） |
| query | 查询完整画像 + 转写原文 |
| list | 列表概览 |
| export | Markdown 报表导出 |

## 数据纪律

- 初筛建档只写阶段 A 字段，不提前填最终判断
- 通话后更新必须复用同一 phone，禁止新建重复档案
- ai_match_evidence 必须可追溯（引简历/录音哪一部分）
- 存储位置：本地 `.hr-data/crm/`，不上云
