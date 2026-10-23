# 大学生赛事教练团（college-competition-coaching-team）v1.0.0

面向大学生双创与学术科技赛事的**多智能体教练专家包**（team 型）。由主理教练程衡统一编排，四名专职成员按「选题 → 资料 → 文本 → 评审」流水线协作。

## 团队成员

| ID | 名字 | 职责 |
|---|---|---|
| ccc-team-lead | 程衡 | 主理教练：编排、中转、门控 |
| ccc-planner | 苏理 | 选题规划师 |
| ccc-collator | 路衡 | 资料整合师 |
| ccc-optimizer | 计程 | 文本打磨师 |
| ccc-reviewer | 优然 | 评审答辩教练 |

## 目录结构

```
.codebuddy-plugin/plugin.json   包清单
agents/                         5 个成员 agent
knowledge/                      知识库（templates/cases/reviews/tracks/_index/ocr_corpus）
skills/competition-kb/          知识库挂载技能
avatars/                        6 个 3D 角色人物头像（512×512，≤500KB）
scripts/gates.py                质量自检脚本
```

## 知识底座

- `knowledge/templates.md`：TM1–TM9 九套文档模板（商业计划/红旅/创业计划书12表/答辩50问/写作注意/学术科技类/备赛工具9大类/职业规划/新文科）。
- `knowledge/cases.md`：双百工程真实项目语料（60 项可用清单 + 要点案例）。
- `knowledge/ocr_corpus.md`：50 个图像型项目 PDF 的本地离线 OCR 全文语料。
- `knowledge/reviews.md`：各赛道评分维度与答辩采分/失分点。
- `knowledge/tracks.md`：涵盖双创、学术科技、职业规划、新文科等多赛道的图谱与选题匹配速查。

## 四态标注

`已验证(本地)` / `已验证(外源)` / `未验证` / `缺失`。外源条目必附 URL，不编造。

