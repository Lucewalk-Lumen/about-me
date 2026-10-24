# 标准自动更新机制（Standards Watch）

> 设计约束：因安装包不得含开发脚本，本机制 = **文档化流程 + 检查清单**，而非内置爬虫/定时任务。目标是让本团持续对齐 `open.workbuddy.cn/docs` 的最新 schema 与规范。

## 一、关键文档页面（open.workbuddy.cn/docs）

> 下列为公开平台文档入口，实际 URL 以官网导航为准；发现变动时以官网最新页面为准。

| 页面 | 用途 | 关注点 |
|------|------|--------|
| 开放平台概述 | 了解 Expert / Skill / Expert Team 定位 | 三类资产的定位与差异是否调整 |
| 技能（Skill）开发文档 | SKILL.md 规范、触发词、references | frontmatter 字段、触发词写法 |
| 专家（Expert）开发文档 | 单 agent 规范、plugin.json(expert) | agent 字段、expertType |
| 专家团（Expert Team）开发文档 | 多 agent 协作、plugin.json(team) | teamInfo / members / expertType:"team" |
| 插件 schema 文档 | plugin.json 完整字段 | 字段增删、必填/可选变化 |
| Changelog 规范 | 三段式写法 | 标题格式、分组、版本语义 |

## 二、标准变动自检步骤

建议**人工定期**（或借助 WorkBuddy 的 automation 定时拉取文档页）执行：

1. **拉取文档**：访问上述页面，记录关键字段与示例。
2. **比对 schema 字段**：将官网 `plugin.json` 字段清单与本团 `.codebuddy-plugin/plugin.json` 逐字段比对，标记新增/弃用/改名。
3. **比对展示规范**：核对 `displayDescription` 字数限制、`tags` / `quickPrompts` 数量与格式是否与官网一致。
4. **比对 CHANGELOG 规范**：核对标题、分组（新增/优化/修复）、版本语义是否与 codebuddy.cn/docs 一致。
5. **比对 references 内容**：确认本团 references 中引用的字段名/路径未过时。

## 三、发现变动 → 回灌版本 流程

```
发现文档变动
  └─> 改 plugin.json / references（按变动内容）
       └─> 升版本号（语义见下）
            └─> 更 CHANGELOG（三段式，按 changelog-convention.md）
                 └─> 重测官方校验（tencent-pptx / WPS 可打开、plugin.json 通过平台校验）
                      └─> 提交分发
```

**版本号语义**（与 plugin.json 真源一致）：
- MAJOR：不兼容变更（如 expertType 结构大改、必填字段移除）。
- MINOR：向下兼容新增（如新增可选字段、新增成员）。
- PATCH：向下兼容修复（如字段值修正、文案勘误）。

> 版本唯一真源 = `plugin.json.version`；CHANGELOG 仅记录，不另立版本。

## 四、版本钉与待复核项表

| 版本钉 | 当前值 | 来源 | 状态 |
|--------|--------|------|------|
| plugin.json.version | 1.0.1 | 本团定义 | 已钉 |
| expertType | "team" | open.workbuddy.cn/docs 专家团规范 | 待复核 |
| teamInfo 结构 | {leadAgent, memberAgents} | 同上 | 待复核 |
| displayDescription.zh 字数 | 40–50 汉字 | 本团约定 + 平台限制 | 待复核 |
| tags / quickPrompts 数量 | 3 / 3 | 本团约定 | 待复核 |
| CHANGELOG 三段式 | 标题含版本号与日期 + 新增/优化/修复 | codebuddy.cn/docs | 待复核 |

**待复核项（人工/automation 定期核对）**：
- [ ] open.workbuddy.cn/docs 是否新增 plugin.json 必填字段（如 categoryId 枚举变化）
- [ ] 专家团 members 字段是否调整（avatar / role 取值）
- [ ] Changelog 规范是否调整标题 emoji 或分组名
- [ ] 官方技能 tencent-pptx 的参数/调用方式是否更新（见 official-skill-routing.md）

> 任何"待复核"项一旦在官网确认变动，立即走"改 → 升版本 → 更 CHANGELOG → 重测"流程，并在下一版 CHANGELOG 记录。
