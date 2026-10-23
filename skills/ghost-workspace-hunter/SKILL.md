---
name: ghost-workspace-hunter
display_name: 幽灵工作空间猎手
display_name_en: Ghost Workspace Hunter
description: 猎除 WorkBuddy 中删不掉、反复出现的「时间戳幽灵工作空间」。当侧边栏浮现 YYYY-MM-DD-HH-MM-SS 格式的残留条目、或 workspaces 表被写入时间戳路径时召唤；跨平台（macOS / Windows）、可逆（进回收站）、自带数据库备份与活跃会话保护，绝不误伤命名真实工作空间。
description_zh: 幽灵工作空间猎手——专清 WorkBuddy 时间戳命名的幽灵工作空间：跨平台、可逆、带备份，护住在跑会话，绝不误伤真实项目。
description_en: Ghost Workspace Hunter — purge residual timestamp-named "ghost workspaces" from WorkBuddy. Cross-platform, reversible (Recycle Bin/Trash), with DB backup and active-session guard. Never touches real named workspaces.
category: productivity
version: 1.0.0
author: Xing Bu
allowed-tools: Bash
icon: icon.png
---

# 幽灵工作空间猎手

## 这是什么

WorkBuddy 有时会在侧边栏留下**删不掉、反复出现**的幽灵条目——名字是一串时间戳
（`YYYY-MM-DD-HH-MM-SS`），磁盘目录早已清空，记录却死死挂在列表里。

**成因**：你从首页直接开启专家 / 数字分身任务（未先选定工作空间）时，应用会自动新建一个
时间戳工作空间；任务结束后磁盘目录可能消失，但 `workspaces` 表记录因删除入口不对称
未能同步清除——于是"删了会话、条目还在"。

幽灵工作空间猎手把这批残留一次清干净：**定位 → 删记录 → 目录进回收站 → 刷新列表**，
全程可逆、可回退。

## 何时召唤

- 侧边栏出现 `YYYY-MM-DD-HH-MM-SS` 格式、删不掉的条目；
- 清理后条目仍反复回流；
- 你明确要求清理工作空间残留；
- agent 自检发现 `workspaces` 表存在时间戳命名路径。

## 试试这样问我

- “我的 WorkBuddy 侧边栏一直出现 `2026-10-12-23-38-53` 这种时间戳条目，删不掉，帮我清掉”
- “清理一下残留的数字任务空间 / 幽灵工作空间”
- “`workspaces` 表里有一堆时间戳命名的路径，怎么净化？”
- “为什么工作空间删了还在、还反复出现？顺便帮我处理掉”

## 出招（按序执行）

1. **先侦察**（可选）：列出 `workspaces` 表路径，确认哪些 basename 是时间戳。
   ```bash
   sqlite3 ~/.workbuddy/workbuddy.db "SELECT path FROM workspaces;"
   ```
2. **一击净化**：运行跨平台脚本（幂等，已内置备份与安全逻辑）。
   - macOS：
     ```bash
     /usr/bin/python3 ~/.workbuddy/skills/ghost-workspace-hunter/scripts/cleanup.py
     ```
   - Windows：
     ```bat
     py "%USERPROFILE%\.workbuddy\skills\ghost-workspace-hunter\scripts\cleanup.py"
     ```
   若 `py` 不可用，改用 `python` / `python3`；若技能装在别处，按本 SKILL.md 所在目录解析
   `scripts/cleanup.py` 的绝对路径。
3. **回报战果**：清掉几条、哪些进了回收站、命名真实工作空间是否完好。

## 三道防线

1. **备份先行**：动库前自动生成 `workbuddy.db.backup-<时间戳>`。
2. **可逆删除**：一切删除走回收站 / 废纸篓，随时可捞回。
3. **护住活跃会话**：工作空间只要还有未删会话，就整目录保留——不删记录、不移磁盘、不动缓存。

另有两条铁律：**只碰时间戳命名的空间**，命名真实工作空间一律不碰；**禁止手动 `rm` / `del`**
数据库或目录。清理后请**重启 WorkBuddy**，让它重新读取列表。

## 平台速查

| 平台 | 数据库 | 工作空间根 | 回收站 |
|---|---|---|---|
| macOS | `~/.workbuddy/workbuddy.db` | `~/WorkBuddy` | `~/.Trash` |
| Windows | `%USERPROFILE%\.workbuddy\workbuddy.db` | `%USERPROFILE%\WorkBuddy` | 回收站（`SendToRecycleBin`） |

两处路径均可用环境变量 `WORKBUDDY_DB` / `WORKBUDDY_ROOT` 覆盖。Windows 路径已据本机实测文档
核实（`WorkBuddy工作空间清理指南-Windows.md`，2026-10-12）。

## 平台注意事项

- **优先应用内清理**：幽灵条目也可右键 →「从列表中移除」直接清掉；本脚本做的是等效的库记录删除，二者择一即可。
- **勿删当前会话目录**：Windows 的 `WorkBuddy\` 下含在跑的会话目录，删它等于删本次对话全部文件；脚本已按规则规避。
- **清理前关闭 WorkBuddy**，避免文件占用或写坏状态。
- **中文路径**：不要在 Windows 写 `.ps1` / `.bat` 处理中文路径（编码会乱文件名）。本工具是 `.py`，
  实际传入回收站的均为 ASCII 时间戳目录与 `.json` 缓存，不受此约束影响。
