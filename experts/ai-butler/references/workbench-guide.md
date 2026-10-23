# 工作台使用细则（分片）

> 本文件是管家指令（`agents/ai-butler.md`）的分片，按需读取；未读本文件不得执行相关写操作。

### 2. 工作台操作向导

四大栏目与核心交互：

| 栏目 | 功能 | 管家协助方式 |
|------|------|-------------|
| **今天待办** | 逾期顺延标红、一键处理/推明天、卡点项目、今日紧急、进度环+本周热力 | 播报今日焦点、提醒逾期 |
| **灵感速记** | 标签筛选、**一键转任务** | 帮用户整理灵感、转为 actionable 任务 |
| **项目跟进** | 进度环、卡点标红、关联任务统计 | 汇总项目进度、预警卡点 |
| **每周复盘** | KPI/优先级环形图、精力分布、14 天堆叠图、**一键周报** | 基于真实数据生成叙事型周报 |

通用能力：任务全字段编辑、全局搜索、深色模式（浅色/深色/跟随系统）。

### 3. 首次引导（Onboarding）
新用户首次打开看到 5 步向导（认识栏目 → 学期设置 → 连接本地桥 → 自动化），可跳过；老用户自动跳过。引导完成后 `meta.onboarded=true`。

### 4. 数据安全
- 导出 JSON 备份（数据满 20 条且距上次导出新增 ≥20 时提示）
- 导入恢复（覆盖/合并双模式，兼容 v1 备份）
- 容量预警（localStorage ≥3MB 提示导出、≥5MB 强制提醒）
- v1→v2 无损迁移（升级前自动留一份 v1 快照备份，供需要时手工取回；不承诺自动保留期限）

### 5. 教学日历
设置学期起始日后任务显示「第 N 周」；支持文本粘贴批量生成教学待办、上传图片/PDF 作参考、上传 .ics 解析。

### 6. 个性化
8 渐变主题、8 侧栏图标、10 页面背景、8 页头装饰风格、分类管理（12 色板）。

## 设计语言（视觉规范）

图标语义为「胶囊 + 记忆」：胶囊象征任务与数据的封装容器，中央青绿书签象征 AI 的记忆与召回；
整体沿用青绿→蓝渐变、圆角、柔和层次的视觉系统。
品牌描述与各尺寸图标清单见包根 `README.md`「设计语言」一节。

## 包结构

```
ai-butler/
├── .codebuddy-plugin/
│   └── plugin.json          # WorkBuddy 专家包清单（类目/标签/快捷提示词/头像）
├── package.json             # Node 侧运行时清单（version 与 HTML 的 WB_VER 常量对齐，供桥与文档引用）
├── agents/
│   └── ai-butler.md         # 管家行为定义（含本地桥自启逻辑与 v2 安全契约）
├── avatars/
│   └── expert.png           # 专家头像（已重压缩 ≤500KB）
├── assets/
│   ├── teacher-workbench.html    # 单文件工作台（本地+可选云同步一体，默认离线；端到端加密 + 本地桥 UI）
│   ├── icon.svg                 # 矢量图标（胶囊+记忆语义，favicon 源）
│   ├── icon-192.png             # PWA 图标 192px（胶囊+记忆）
│   ├── icon-512.png             # PWA 图标 512px（胶囊+记忆）
│   ├── icon-maskable-512.png    # PWA maskable 图标（全幅背景+中央安全区）
│   ├── apple-touch-icon.png     # iOS 添加到主屏幕图标 180px（胶囊+记忆）
│   ├── manifest.webmanifest     # PWA 清单
│   └── sw.js                    # Service Worker（离线缓存）
├── bridge/
│   └── teacher-workbench-bridge.js  # 本地中继桥 v2（零依赖 Node，回环+HMAC签名+强随机token；桥的唯一实现）
├── references/              # 管家指令分片（按需读取：本指南 / 桥接口 / 桥恢复）
│   ├── workbench-guide.md   # 本文件（使用细则、设计语言、包结构、安装说明）
│   ├── bridge-api.md        # 桥参数表与 v2 安全契约
│   └── bridge-recovery.md   # 桥故障恢复流程（探测未返回 200 时读取）
├── agent-card.json          # 跨运行时通用元数据（UMAS v1.0）
├── UNIVERSAL-STANDARD.md    # 通用元数据组织约定（UMAS）说明
├── PORTABILITY.md           # 各运行时加载映射指引
├── SOURCES.md               # 技术来源与许可标注
├── CHANGELOG.md             # 变更日志
├── COPYRIGHT.md             # 版权声明
├── LICENSE                  # MIT 许可全文
└── README.md                # 产品说明
```

## 与桌面安装包的关系

本专家包即**唯一交付物**（标准 WorkBuddy agent 型专家包，含 `.codebuddy-plugin/plugin.json` 清单，直接载入即可用）；工作台的本地能力与可选云同步均整合在同一包内：

| 形态 | 内容 | 适用场景 |
|------|------|---------|
| 通用专家（本包） | 单 Agent + 内嵌单文件工作台 | 对话内唤起、集成使用 |
| 单文件工作台（`assets/teacher-workbench.html`） | 默认纯本地离线；可选云同步 | 浏览器直接打开 / 静态托管 /「添加到主屏幕」 |

云同步无需独立安装包：在工作台「设置 → 云同步」填写 CDN/SDK 地址与环境 ID 即激活；未配置时完全离线、零网络请求。

### 安装与跨平台

- **标准 agent 型专家包**：本包含 `.codebuddy-plugin/plugin.json` 插件清单，承载专家元数据（类目 / 标签 / 快捷提示词 / 头像等）供 WorkBuddy 载入与校验；同时保留 `package.json` 作为 Node 侧运行时清单（版本以 `version` 为准，其余清单与 HTML 的 `WB_VER` 常量与之对齐）。二者职责不同、互不替代。
- **跨平台运行**：工作台为单文件 HTML（任意浏览器）；本地桥为零依赖 Node 脚本（**须 Node ≥ 18**），macOS / Linux 可直接运行，Windows 需 WSL / Git-Bash 等 POSIX 兼容环境运行管家自启脚本（或手动执行 `node bridge/teacher-workbench-bridge.js`）。桥自身路径统一用 `os.homedir()` + `path.join()`，日志与临时文件走系统临时目录（Node `os.tmpdir()` / POSIX `$TMPDIR` / Windows `%TEMP%`），无硬编码 POSIX 路径。
- **文件权限硬化（跨平台）**：token / 数据 / 审计文件默认仅当前用户可读写——macOS / Linux 用 `chmod 600/700`，Windows 用 `icacls` 移除继承并仅授予当前用户 `(F)`；任一平台失败时降级告警、不阻断启动（数据仍仅经本机回环 `127.0.0.1` / `::1` 传输）。
- **包 ID 不变**：本包平台注册 ID 始终为 `ai-butler`（不可变），更新仅涉及显示名（花名「启明星」/ `Lucian`、职称「教师工作台」）或内部修复；平台不会将其识别为新专家包，老用户直接覆盖更新即可；更新前建议先在工作台「设置 → 导出 JSON」备份。
