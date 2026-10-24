# kb-organizer · 知识库智能整理大师（WorkBuddy 专家包）

> **版本**：v1.0.0 ｜ **生成日期**：2026-09-13 ｜ **作者**：清风明月（809277254@qq.com）
> **平台**：WorkBuddy / CodeBuddy 开放平台 ｜ **专家类型**：agent

## 一、专家简介

知识库智能整理大师——自动分析知识库内容分布，生成个性化分类方案，创建文件夹并批量归类归位。当用户说"整理知识库"、"把知识库分类"、"帮我理一理知识库"、"知识库太乱了"、"清理知识库根目录"、"自动归类"、"建立知识库体系"等意图时触发。融合智能分析、方案生成、自动归类与批量移动能力。不适用于：新建知识库、内容搜索阅读、笔记管理、单篇文档编辑。

## 二、能力概览

- 技能目录：`skills/kb-organizer/`（含 SKILL.md、references×5、scripts×0）
- 定位：知识库智能整理大师
- 触发方式：直接描述你的需求，专家自动匹配工作流

## 三、目录结构

```
kb-organizer/
├── .codebuddy-plugin/
│   └── plugin.json          # 平台元数据（i18n 双语）
├── avatars/
│   └── expert.png           # 512×512 头像
├── agents/
│   └── kb-organizer.md     # 智能体定义（frontmatter 禁 tools）
├── skills/
│   └── kb-organizer/       # 完整技能包
│       ├── SKILL.md
│       ├── references/      # 5 份专家件
│       └── scripts/         # 0 个脚本
└── README.md
```

## 四、上架发布

1. 打开 WorkBuddy【专家中心 → 我的专家】
2. 上传本 zip
3. 检查头像/名称/描述/标签/推荐提示词展示效果
4. 确认无误后点击发布

如遇解析报错，可邮件 `openworkbuddy@tencent.com`。

## 五、版本历史

- **v1.0.0**（2026-09-13）：首次 WorkBuddy 专家包化
