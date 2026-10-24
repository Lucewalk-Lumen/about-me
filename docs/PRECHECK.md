# 专家包 GitHub 发布预检报告

> 扫描日期:2026-10-23 | 扫描器:Python 3.13 正则批量扫描(4 类规则 + 残留文件检测)
> 范围:28 个基准资产(源码目录 16 + zip 安装包 12),共约 3,400 文件
> 明细数据:`expert-precheck-report.json`(同目录)

## 一、结果总览

| 结论 | 数量 | 说明 |
|---|---|---|
| ✅ 直接可发布 | 12 | enterprise-docs-organizer、obsidian-knowledge-governance-team、system-setup-team、wiki-kb-team、brand-knowledge-base、ima-kb-ops-team、kb-organizer、llm-wiki、personal-knowledge-architect、obsidian-mind-vault、schedule-planner、obhrm-research-collaboration-team(仅 1 处 .DS_Store) |
| ⚠️ 统一决策后可发布 | 15 | 仅含 `plugin.json` 作者邮箱(见三.1),无其他问题 |
| 🔧 需清理后发布 | 3 | teaching-helper-team、workbuddy-universal-mentor、endnote-analysis-expert |

## 二、需处理问题明细(按优先级)

### P1 · 必须清理(公开仓库硬伤)

| 资产 | 问题 | 位置 | 处理建议 |
|---|---|---|---|
| workbuddy-universal-mentor | **他人用户名路径** `/Users/oumingzhi/...` | `README.md` | 泄漏第三方机器信息,删除或泛化 |
| endnote-analysis-expert | 本机 EndNote 库默认值 `/Users/buxing/Desktop/EndNote/My EndNote Library.enl` | `skills/endnote-analysis/scripts/run_checks.py` | 改为空默认 + `--library` 参数说明 |
| teaching-helper-team | `IDENTITY = "Xing Bu <Lucewalk@users.noreply.github.com>"` 硬编码**身份锁** | `skills/architect/scripts/validate_pack.py`(多处) | 功能性校验逻辑,发布前决策:改用 GitHub noreply 则同步改锁;保持原样则接受邮箱公开 |
| teaching-helper-team | 脚本注释引用 `.created-by-session` 机制 | `scripts/verify.py` | 视平台机制而定,建议注释泛化 |
| obhrm-research-collaboration-team | `.DS_Store` | `skills/grant-writing/.DS_Store` | 删除 + .gitignore 兜底 |

### P2 · 建议清理(低风险)

| 资产 | 问题 | 位置 |
|---|---|---|
| hrm-solution-team | 质量计划文档含交付 zip 绝对路径(已知项) | `quality/team-quality-plan.md:14` |
| kb-library-optimize | `obhrm-ref/`、`kb-current/` 为内部参考结构,含参考副本;`environment-setup.md`、`obsidian-host.md` 2 处待人工复核 | 入库前拆分:技能本体与参考材料分离 |

### 误报说明(无需处理)

- teaching-helper-team `skills/course-builder/assets/mermaid.min.js` 13 条"疑似凭据"为 min.js 字符串拼接误匹配;
- touyan-expert-team `MX_APIKEY = "你的API_KEY"` 为使用文档中的占位符示例;
- kb-library-optimize 2 条"绝对路径"命中为环境说明文字,建议人工复核后放行。

## 三、统一决策点

1. **作者邮箱** `Lucewalk@users.noreply.github.com` 出现在全部 15 个 zip/源码的 `plugin.json`(及 touyan 的 COPYRIGHT.md)。公开 GitHub 即公开单位邮箱。可选:① 接受公开(学术署名惯例);② 批量替换为 GitHub noreply(`Xing Bu <xxx@users.noreply.github.com>`)——注意 teaching-helper 的身份锁、verify.py 联动。
2. **`.codebuddy-plugin` 目录名**:全部包一致,README 安装说明需写清宿主识别方式。
3. **teaching-helper-team 源码 vs zip**:以 1.1.2 源码为准(已确认),入库前跑一次包校验。

## 四、发布顺序建议

1. 用户对三.P1 决策 → 执行清理(可逆操作,清理前备份);
2. 迁入仓库骨架(见 `workbuddy-experts-repo/`),12 个干净资产先入库;
3. 15 个"仅邮箱"资产按决策批量处理后入库;
4. 3 个需清理资产修完复扫,通过后入库。
