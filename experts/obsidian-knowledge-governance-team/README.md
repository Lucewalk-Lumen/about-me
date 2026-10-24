# Obsidian 知识库治理专家团

由七名角色协作的 Obsidian 知识库治理团队：先做只读盘点，再基于主流知识管理理论设计行动层、知识层、导航层与治理规则，最终以可核验的变更清单分批交付，适配复杂、多年积累、结构混杂的 Vault。

## 类型

Team 型（多角色协作团队）

## 行业分类

`12-IndustryConsultant`（行业顾问）：主要产出是跨领域的知识治理方案、信息架构、方法论选型与长期维护机制，属于综合咨询与结构优化，而非单一技术实现。

## 理论基础

| 理论 | 来源 | 在本团中的用途 |
|---|---|---|
| PARA | Tiago Forte《Building a Second Brain》 | 按行动性组织 Projects / Areas / Resources / Archives |
| CODE | Tiago Forte | Capture → Organize → Distill → Express 的信息流转 |
| 渐进式总结 | Tiago Forte | 分层提炼，避免一次性过度加工 |
| Zettelkasten | Niklas Luhmann；Sönke Ahrens《How to Take Smart Notes》 | 原子笔记、自有语言、显式链接 |
| 常青笔记 | Andy Matuschak | 概念导向、密集链接、可长期演进 |
| MOC / IMF | Obsidian 社区；Nick Milo | 索引层、内容地图、导航框架 |
| LATCH | Richard Saul Wurman | 位置/字母/时间/类别/层级五种组织维度 |
| Johnny.Decimal | Johnny Noble | 需要稳定编号体系时的编号化目录方案 |
| GTD | David Allen | 收件箱与回顾节奏的补充 |

## 团队成员

| Agent ID | 角色 | 职责 |
|---|---|---|
| `obsidian-knowledge-governance-team-team-lead` | 知识库治理主理人 | 建团、编排、冲突协调、最终交付 |
| `vault-auditor` | Vault盘点审计师 | 文件/链接/元数据只读盘点与变更风险评估 |
| `para-lifecycle-manager` | PARA生命周期管理员 | 行动性分类与项目/领域/资源/归档流转 |
| `zettelkasten-curator` | 原子笔记策展师 | 文献/原子/常青笔记拆分与渐进取舍 |
| `metadata-taxonomist` | 元数据分类师 | Frontmatter、标签、别名、命名与迁移映射 |
| `link-moc-architect` | 双链与MOC架构师 | 双链策略、MOC层级、索引与查询视图 |
| `content-quality-reviewer` | 内容质量审校师 | 重复、过期、来源与冲突审查 |

## 使用示例

- 请对我的 Obsidian 知识库做一次全面审计，基于知识管理理论输出治理方案、MOC、元数据规则和安全变更清单。
- 我的知识库有数千篇混杂笔记，请设计分阶段迁移方案，避免丢失链接、来源和历史记录。
- 请为我的知识库融合 PARA、Zettelkasten、渐进式总结与 MOC 导航，建立可长期维护的体系。

## 安全边界

- 扫描阶段只读，不移动、重命名、删除或覆盖任何个人文件。
- 任何不可逆操作前必须列出逐项路径、风险、备份方案并取得明确确认。
- 每批最多处理 10 个文件；删除仅进入回收站或待删除区。
- 不编造来源、日期、标签或结论；不确定内容标记为待核验。

## 头像

头像位于 `avatars/`，团队与各成员风格统一。如需替换：
- 格式：PNG 或 JPG
- 尺寸：512×512 px
- 大小：单张不超过 500KB

## 安装

将专家包目录放到专家目录下，然后运行注册命令：

```bash
python3 scripts/register_expert.py <expert-dir>
```

## 打包分享

```bash
python3 scripts/package_expert.py <expert-dir> <output-dir>
```
