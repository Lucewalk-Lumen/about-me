# Obsidian 宿主特例（obsidian-host）

> 适用成员：林归类（四阶段文件夹）、苏航（MOC/双链/标签）
>
> **WorkBuddy 访问方式**：Obsidian Vault 是本地 Markdown 文件夹，WorkBuddy 通过本地文件系统直接读写，**无需安装连接器**。用户只需提供 Vault 的本地路径（如 `/Users/you/Documents/MyVault`）。

## 1. 双链语法与链接规则

- 双链写法 `[[note-name]]`、别名 `[[note-name|别名]]`、标题级 `[[note-name#标题]]`、嵌入 `![[note-name]]`。
- 反向链接（backlinks）作为「被谁引用」的巡检输入；孤儿条目 = 无任何入链且未挂索引的笔记。
- 链接方向表达关系：父子、兄弟、因果、引用——建边必须附关系类型，避免机械式滥链。

## 2. MOC 分层

- 总览 MOC（库一张）→ 主题 MOC（每主题一张）→ 条目。
- MOC 只挂链接与一句话导读，不复制正文内容。
- 条目可同时挂多个 MOC；正文不复制，只增索引关系。

## 3. 四阶段文件夹（形态落地）

四池在 Obsidian 的物理落位建议：`01-ideas/` `02-drafts/` `03-official/` `04-archive/`。文件夹是阶段的主依据，frontmatter `status:` 只做辅助校验；两者不一致列为待确认，不擅自改阶段。

## 4. frontmatter 基线

```yaml
---
created: YYYY-MM-DD
updated: YYYY-MM-DD
source: <来源>
status: idea|draft|official|archive
owner: <负责人，official 必填>
valid_for: <适用范围>
tags: [type/..., source/..., topic/..., action/...]
---
```

## 5. 标签体系

四类前缀（type/ source/ topic/ action/），命名成惯例后保持住；同义/重复标签列进巡检收敛建议。不用标签搭多级体系。

## 6. 巡检与机械层

- 死链扫描：link_integrity_scan.py 支持 `[[wiki-link]]` 语法解析。
- 机械层问题（条目已完结却仍留在活跃目录、文件位置错误）的识别可脚本化，且默认先试运行再执行；判断层问题（聚类/拆分/补链）只列清单不代做。
