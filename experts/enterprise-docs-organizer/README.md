# Enterprise Document Organizer (企业资料整理专家)

把散乱的企业文件分类归档，沉淀为可检索知识库、FAQ 与操作手册，让员工不再为一个问题反复打扰同事。

## 类型

Team 型（多角色协作团队）

## 功能

1. **资料体检**（主理人 归有章）：摸清有哪些文件、格式来源、谁在用、最痛的点
2. **分类体系设计**（主理人）：输出目录结构树、命名规范、标签与权限建议（知识库蓝图）
3. **并行产出**：
   - 档案分类师 **罗致** — 逐文件归类、命名规范、去重与迁移指引
   - 手册撰写师 **舒卷** — 员工 FAQ、操作手册、新人上手指南、维护机制
4. **一致性校验与交付**：手册引用的路径与分类结构互相校验，输出「知识库交付包」

## 使用示例

- 帮我把这些散乱文件分类并建立目录结构
- 根据这些资料生成一份员工常见问题 FAQ
- 把这份流程整理成标准操作手册

## 头像

头像已自动生成在 `avatars/` 目录下。如需替换为自定义头像，要求：
- 格式：PNG（推荐）或 JPG
- 尺寸：512×512 px
- 大小：单张不超过 500KB

## 安装

将专家包目录放到专家目录下：

```
C:\Users\pc\.workbuddy\plugins\marketplaces\my-experts\plugins\enterprise-docs-organizer\
```

然后运行注册命令使其可见：

```bash
python3 scripts/register_expert.py <expert-dir>
```

## 打包分享

```bash
zip -r enterprise-docs-organizer.zip enterprise-docs-organizer/
```
