# 通用技能 / Agent 校验清单（SKILL_CHECKLIST）

> 与 `scripts/validate_pack.py` 对应，用于制作 / 审查技能或 agent 时的自检。
> 平台无关，与 `scripts/validate_pack.py` 对应。

## 准入结构（Structure）

- [ ] 技能包根目录含 `SKILL.md`；若为目标宿主 agent-pack，另含 `manifest` / `config` / `workspace`。
- [ ] 目录名、frontmatter `name` 完全一致。
- [ ] frontmatter 至少含 `name` 与 `description`。
- [ ] `description` 说明**何时使用**，而非泛泛能力介绍。

## 引用完整性（References）

- [ ] `SKILL.md` 中引用的 `references/`、`scripts/`、`assets/` 路径真实存在。
- [ ] 脚本可执行（语法 / 依赖自洽），不依赖未声明的外部二进制。

## 内容与设计（Design）

- [ ] 职责边界清晰：输入 / 处理 / 输出 + 明确不做的事。
- [ ] 触发时机明确（场景化，而非“智能”“强大”等空泛词）。
- [ ] 单一职责；未混入完整人格 / 泛化闲聊 / 一次性项目记录。
- [ ] 生产级要素可辨认：上下文裁剪、结构化动作、状态恢复、人类介入、错误压缩（见 `production_agent_specs.md`）。

## 安全与合规（Security）

- [ ] 不含真实 `token` / `access_token` / `api_key` / `secret` / `password` / 私钥 / 连接串。
- [ ] 不含客户归属、人员归属、真实凭证、运行时状态。
- [ ] 高风险动作（执行 / 联网 / 写文件 / 外部 API / 消息 / 定时）写明用途与审批，不默认绕过。
- [ ] 不残留未固化的第三方技能来源（发布态应 `source: "local"` 或等价本宿主内嵌）。

## 验收用例（TestCases，可选但推荐）

- [ ] `prompts` / `testCases` 数量为 3–5。
- [ ] 至少 1 个 `testCases` 含 `smoke` 标签。
- [ ] 用例覆盖 happy-path、边界 / 澄清、校验 / 集成。

## 打包与交付（Deliver）

- [ ] 通过 `validate_pack.py`（通用）。
- [ ] 交付物路径明确；WorkBuddy 下放置到 `~/.workbuddy/skills/` 即生效，不要求复制执行安装命令。
- [ ] 包内不含 `.git` / `sessions` / `凭据` / `memory` / 私钥 / 机器运行状态 / `__pycache__` / 临时抓取文件。

## 风险分级

- **Critical / High**：敏感信息命中、缺失 `SKILL.md`、目录名与 `name` 不一致、阻断项未修复 → 禁止交付。
- **Medium**：引用路径缺失、description 含糊、缺 smoke、权限未最小化 → 应修复。
- **Low**：措辞 / 展示优化 → 可后补。
