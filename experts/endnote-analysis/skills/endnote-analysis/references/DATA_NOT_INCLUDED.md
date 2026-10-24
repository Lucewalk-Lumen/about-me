# 本包不包含任何用户数据

本专家包**只含代码与配置，不含任何文献数据**。分发给他人时无需担心隐私泄漏。

## 校验方式（可自行复现）

```bash
# 1) 不应存在任何 .enl / .sqlite / refs.json 等库文件
find . -name "*.enl" -o -name "*.sqlite" -o -name "refs.json" | wc -l   # 期望 0

# 2) 不应存在任何 PDF / EPUB 附件
find . -name "*.pdf" -o -name "*.epub" | wc -l                # 期望 0

# 3) 不应出现本机绝对路径（家目录 + /Volumes 卷挂载）
grep -rn "$(printf '\057Users\057')\|$(printf '\057Volumes\057')" --include="*" . | wc -l   # 期望 0
```

## 已验证（v0.3.1 打包时实测）

| 检查项 | 结果 |
|---|---|
| EndNote 库文件（`.enl`） | **0 个** |
| Zotero 库（`.sqlite`） | **0 个** |
| 归一化产物（`refs.json`） | **0 个** |
| PDF / EPUB 附件 | **0 个** |
| 真实文献标题 | **0 处** |
| 本机绝对路径（家目录、外接卷挂载点） | **0 处** |
| 样例输出目录（`samples/`） | **已移除**（v0.3.0 曾包含 277 条真实题录与一份真实报告，见下方说明） |

> ⚠️ **变更说明（v0.3.1）**：v0.3.0 的 `samples/` 目录内含 227 条 CNKI 真实题录
> （题名/作者/DOI/关键词）、50 条 WoS 真实题录，以及一份 692 KB 的真实分析报告
> （内含真实作者名）。这些数据与本文件原先"真实文献标题 0 处"的声明**相互矛盾**，
> 存在隐私泄漏风险，已在 v0.3.1 中整体删除。
> 本包改为**不附带任何样例输出**——所有示例产物均由用户对自己的文献库运行后生成。

## 包内文件清单

| 文件 | 用途 | 含用户数据？ |
|---|---|---|
| `agents/*.md` | 3 个 Agent 定义（主理人 + 2 成员） | 否 |
| `skills/endnote-analysis/scripts/*.py` | 分析脚本（16 个） | 否 |
| `skills/endnote-analysis/references/dict_stopword_seed.csv` | 通用停用词种子表 | 否（通用词表） |
| `skills/endnote-analysis/references/topic_labels.py` | 主题命名术语表 | 否（通用术语） |
| `skills/endnote-analysis/references/palette_*.json` | 网络图配色方案与实测指标 | 否 |
| `skills/endnote-analysis/references/palette_vivid.py` | 色觉安全配色生成器 | 否 |
| `skills/endnote-analysis/references/failure_paths.md` | 失败场景与退出码契约 | 否 |
| `skills/review-skeleton/**` | 综述骨架脚本与抽取框架 | 否 |
| `requirements.txt`、`README.md`、`settings.json` | 依赖与配置 | 否 |

## 历史实测数字的来源

包内文档（SKILL.md / README.md / Agent 定义）出现的"实测"数字均标注为
**v0.3.1 在特定文献库上的实测**，并附参数口径。

**v0.3.1 复测基准库**（仅用于校准，**不含任何数据于本包**）：
5683 篇 EndNote 库，Apple Silicon arm64，Python 3.13.12，R 4.6.1 + igraph 2.3.3。
关键复测值：K=14（簇规模 625→245，最大簇占 11.0%）、共现网络 1081 节点 / 8695 边、
模块度 Q=0.241、ARI=0.198、NMI=0.450、Cramér's V=0.227、η²=0.083、
相邻 K 最小 ARI=0.590。这些与 v0.3.0 文档记载的历史值**高度吻合**，
说明历史实测可信。

> ⚠️ 这些数字**只代表那一份库**。用户在自己的库上运行时，
> 应以实际产物为准，不得引用本包数字冒充自己的结果。
> 任何规模数字脱离参数口径引用即为误导。

## 用户数据存在哪里

运行时数据**全部写在用户自己的工作目录**，绝不写回专家包：

- 影子副本（`.enl` 的临时拷贝）→ `--workspace` 指定目录（默认 `./.endnote_work`）
- 分析产物（JSON/CSV/HTML）→ `--out` 指定目录，默认 `./out/`
- 用户自定义主题命名 → `references/topic_labels.local.csv`（**本包不预置，首次运行自动创建**）

若用户删除产物目录，工具下次运行会重新分析生成。
