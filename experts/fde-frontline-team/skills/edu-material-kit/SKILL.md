# 教育专场材料模板包（edu-material-kit）

> 适用对象：教育工作坊导师（师阅）主用。功能：模块③教育专场材料的唯一起草底稿库。

## 何时用本技能

高校专场任务（课程方案、能力地图）进入材料生产阶段时，先取模板，不另起炉灶。

## 模板清单

| 模板 | 用途 |
|---|---|
| `templates/course-blueprint.md` | 课程智造工作流模板：课程定位 / 三段式内容主线 / 课堂成品清单 / 教学提示 / 溯源清单 |
| `templates/capability-map-template.md` | 新文科生 FDE 能力地图模板：维度 3 至 6 个，每维度带行为化描述与出处 |

## 使用纪律

1. 模板中的每处「出处」占位须填入 `references/fde-talent-judgments.md` 或 `references/fde-handbook-judgments.md` 条目号，可经 `references/source-mapping.md` 回溯。
2. 能力地图默认口径为三能力（懂业务 / 会动手 / 能交付）；引入政策十二字表述时须保留「复合型应用人才」原语境（见 `references/policy-snapshot-L1.md`）。
3. 示例数据一律标注「示例」，禁用任何未核验的作者内部数字（见 `references/banned-content-list.md`）。
4. 交付时模板自带的溯源清单随材料一并交付，不得删除。

## 政策输出格式

模板材料中涉及政策口径时：先答 `references/policy-snapshot-L1.md` 快照（带 `快照截至 <snapshot_date>` 与三态标注 `<verified|unverified|missing>`），再走 skills/policy-radar 做 L2 核验；缺快照日期或三态标注的内容不进材料。
