---
name: content-summary
description: "总结 URL、本地文件、PDF、图片、音频与 YouTube 内容（多模型 CLI）。用于素材准备阶段的快速总结与要点提取，产出喂给纪要整理专家/案例写作专家/论文辅导专家。"
version: 1.1.1
---

# Summarize 素材总结
> **归属**：基础能力层（foundation）——素材总结，挂主理人 lead 按需注入


> 使用 summarize CLI 总结网页、本地文件、PDF、图片、音频和 YouTube 链接，是教学帮帮团的**素材准备工具**。

##  依赖预装（必读）

- 本技能依赖**外部 CLI `summarize`**（多模型总结工具），**未随包内置、setup 也不会自动安装**。使用前需用户自行安装并在终端确认 `command -v summarize` 可用。
- **未安装时的替代路径**：若 `summarize` 不可用，改用通用能力完成素材准备——网页/本地文件用 Read 直接读取提炼要点，PDF/图片/音频用对应解析能力，YouTube 视频请用户提供文字稿/简介，再按「输出规范」产出总结。**不要假装 summarize 存在或编造总结内容。**
- 密钥管理：macOS 默认经 系统凭据 管理；**Windows / Linux 不支持 系统凭据**，改用环境变量（`OPENAI_API_KEY` / `ANTHROPIC_API_KEY` 等）注入，禁止写入代码或配置明文。

## 快速开始

```bash
# 总结网页
summarize "https://example.com" --model <provider/model>

# 总结本地 PDF/文件
summarize "/path/to/file.pdf" --model <provider/model>

# 总结 YouTube 视频
summarize "https://youtu.be/dQw4w9WgXcQ" --youtube auto
```

## 模型与密钥

设置所选提供商的 API Key（macOS 经 系统凭据 管理；Windows/Linux 用环境变量，禁止写入代码/配置明文）：
- OpenAI: `OPENAI_API_KEY`
- Anthropic: `ANTHROPIC_API_KEY`
- xAI: `XAI_API_KEY`
- Google: `GEMINI_API_KEY`（别名 `GOOGLE_GENERATIVE_AI_API_KEY`、`GOOGLE_API_KEY`）

默认模型：未显式设置时使用技能内置默认（可在配置中覆盖）。

## 常用参数

- `--length short|medium|long|xl|xxl|<chars>`：输出长度
- `--max-output-tokens <count>`：最大输出 token
- `--extract-only`（仅 URL）：只提取不总结
- `--json`：机器可读输出
- `--firecrawl auto|off|always`：封锁站点备选提取
- `--youtube auto`：YouTube（有 APIFY_API_TOKEN 时备选）

## 配置

可选配置文件 `~/.summarize/config.json`：

```json
{ "model": "<provider/model>" }
```

可选服务：
- `FIRECRAWL_API_KEY`：封锁站点
- `APIFY_API_TOKEN`：YouTube 备选

## 输出规范

- 总结结果写入数据总线 `data/pipeline/incoming/`，命名 `{task_id}_summary.{format}`
- 保留原文关键数据（数字、专有名词、引用标记），只做提炼不做编造
- 引用保真：原文中的〔R-xx〕〔综述·X〕等标记原样保留
