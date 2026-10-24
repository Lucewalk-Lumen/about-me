---
name: obsidian-mind-vault-knowledge
description: "Component-level knowledge base for designing and operating a persistent-memory knowledge vault for AI coding agents — four-layer architecture, vault content model, session hook pipeline, cross-repo memory service, command orchestration, performance-evidence chains, quality gates and multi-host release. Load when a question needs exact contracts, thresholds, file-level ownership or failure modes."
---

# obsidian-mind 知识库索引

本知识库描述一套**给 AI 编码助手提供持久记忆的自组织知识库系统**。它的表象是一个 Obsidian 库，实质是四层系统叠在一起。

## 命名约定

| 写法 | 含义 |
|------|------|
| `<vault>` | 用户自己的知识库根目录 |
| `<root>` | 仓库根（模板分发形态下的目录） |
| `brain/`、`work/`、`perf/`、`org/`、`memories/` | 库内固定目录，属**领域语义**，非项目名 |
| `obsidian-mind` | 模板产品名（本知识库统一以此称呼，不再附带任何仓库地址或作者信息） |
| `om` | 跨仓记忆服务的名称前缀（工具名、脚本名前缀） |

**本知识库刻意不含任何仓库 URL、作者标识、下载地址、星标数或许可注记。** 需要获取模板本体时，由用户自行从其已知来源取得。

## 目录结构

```
references/
├── 01-architecture-and-contracts.md   四层模型、唯一协调点、设计原则、扩展接缝、稳定保证
├── 02-vault-content-model.md          笔记类型、frontmatter schema、图角色、链接规则、查询视图、拆分语义
├── 03-runtime-hook-pipeline.md        五个生命周期钩子、注入预算、卫生扫描、去抖、原子写
├── 04-cross-repo-memory-service.md    服务面、身份握手、可见性策略、检索分档、记忆作用域与提升
├── 05-commands-and-workflows.md       命令聚类、调用矩阵、写入路径、写权限分层、硬护栏
├── 06-performance-and-evidence.md     证据链、战功文档、组织记忆、事故复盘、评审材料
└── 07-quality-gates-and-release.md    事实纪律、更正三分类、门禁设计、多宿主映射、版本迁移、发布
```

## 处理链一句话地图

```
会话开始 ──注入上下文(受字节预算约束)──▶ 会话进行 ──每条消息分类路由──▶ 内容捕获
   │                                                                      │
   └──◀── 收尾清单 + 卫生漂移发现 ◀── 每轮回复后 ◀── 写后校验 ◀───────────┘
                                                                          │
        落盘(笔记类型+frontmatter+wikilink) ──▶ 索引更新 ──▶ 沉淀进主题笔记/证据链
                                                                          │
        归档 ──▶ 发布交付 ──▶ 跨仓复用(别的仓库经服务协议读写) ◀───────────┘
```

## 跨模块数据契约红线

1. **唯一协调点**：库根的一份机器可读清单文件是所有层的共同契约。任何一层绕过它自行推断，都会造成静默不一致。
2. **笔记的身份是文件名**（不含扩展名）。链接按文件名跨目录解析，因此移动文件不会断链——但重命名会。
3. **元数据未闭合即视为私有**：头部读取窗口内无法完整解析的元数据，一律不对外服务。
4. **记忆的触达范围由写入方声明，读取方不得放宽。**
5. **索引是派生视图**：可以由内容重建，不得反向当作内容来源。

## 三层事实来源优先级

1. **源码与测试**（最高）——数字、路径、阈值以实际实现与断言为准
2. **机器可读契约文件**（库根清单）——版本、边界、字段 schema
3. **叙述性文档**（README / 操作手册）——最低，**已知与实现存在多处不一致**

> ⚠️ 本系统已知存在 **25 处文档与实现不一致**。典型：叙述文档写「18 个斜杠命令」实为 20；写「9 个子代理」实为 10；某个笔记模板缺清单里声明为必填的字段；同一类笔记存在两套互不相同的元数据；查询视图声明里没有排序而文档称已排序；版本指纹表中若干路径与实际文件名不符。
> **凡涉及「有没有 / 多少个 / 路径是什么」的结论，必须回源码或测试复核，不得引用叙述性文档。**

## 全库红线

- ❌ 不得把持久知识存到库之外
- ❌ 不得绕过库根清单自行推断版本或边界
- ❌ 不得在脚本里硬编码宿主专有的事件名或字段
- ❌ 不得按调用仓给同一篇笔记切分作用域（会切断最有价值的跨项目连接）
- ❌ 不得为同一问题新增第二条读取路径（历史上两次重新推导都放行了本该被扣留的笔记）
- ❌ 不得在指令文件里写会腐烂的计数
- ❌ 不得让生产者兼任自己作品的验收者
