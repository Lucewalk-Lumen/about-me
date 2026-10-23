# 本包不包含任何用户数据

本专家包**只含代码与配置，不含任何文献数据**。分发给他人时无需担心隐私泄漏。

## 校验方式（可自行复现）

```bash
# 1) 不应存在任何 .enl / .sqlite / refs.json 等库文件
find . -name "*.enl" -o -name "*.sqlite" -o -name "refs.json" | wc -l   # 期望 0

# 2) 不应存在任何 PDF / EPUB 附件
find . -name "*.pdf" -o -name "*.epub" | wc -l                # 期望 0

# 3) 不应出现本机绝对路径（家目录 + 卷挂载点）
#    用 -E 保证 macOS / GNU grep 行为一致；路径字面量用 printf 拼出，避免本文件
#    自身被判为"含绝对路径"；run_checks.py 内含检测器正则字面量，一并排除。
grep -rnE "$(printf '\057Users\057')[A-Za-z]|$(printf '\057Volumes\057')" --include="*" . \
  | grep -v "scripts/run_checks.py" | wc -l                       # 期望 0
```

## 已验证（1.0.0 实测）

| 检查项 | 结果 |
|---|---|
| EndNote 库文件（`.enl`） | **0 个** |
| Zotero 库（`.sqlite`） | **0 个** |
| 归一化产物（`refs.json`） | **0 个** |
| PDF / EPUB 附件 | **0 个** |
| 真实文献标题 | **0 处** |
| 本机绝对路径（家目录、外接卷挂载点） | **0 处** |
| 样例输出目录（`samples/`） | **不含**（本包不附带任何样例数据；示例产物均由用户对自己的文献库运行后生成） |



## 包内文件清单

| 文件 | 用途 | 含用户数据？ |
|---|---|---|
| `agents/*.md` | 5 个 Agent 定义（主理人 + 4 成员） | 否 |
| `.codebuddy-plugin/plugin.json`、`settings.json` | 专家包清单与默认 agent 配置 | 否 |
| `references/upgrade_broadcast.md` | 版本播报子流程说明（包根） | 否 |
| `skills/academic-lit-analysis/scripts/*.py` | 分析脚本（约 29 个 Python 模块 + R 封装 + 1 个 JS） | 否 |
| `skills/academic-lit-analysis/scripts/topic_labels.py` | 主题命名术语表（含 OB/HRM 概念词典） | 否（通用术语） |
| `skills/academic-lit-analysis/references/dict_stopword_seed.csv` | 通用停用词种子表 | 否（通用词表） |
| `skills/academic-lit-analysis/references/org_aliases.csv` | 机构同义词表 | 否（通用词表） |
| `skills/academic-lit-analysis/references/term_aliases.csv` | 术语同义词种子表 | 否（通用词表） |
| `skills/academic-lit-analysis/references/*.md` | 方法论 / 失败路径 / 本文件等说明 | 否 |
| `skills/review-skeleton/**` | 综述骨架脚本与抽取框架 | 否 |
| `requirements.txt`、`README.md`、`CHANGELOG.md`、`UPGRADE.md`、`settings.json`、`avatars/*.png` | 依赖、文档与配置 | 否 |

## 校准基准与口径

包内文档（SKILL.md / README.md / Agent 定义）出现的"实测"数字均标注为
**在特定文献库上的实测**，并附参数口径。

**校准用基准库**（仅用于校准，**不含任何数据于本包**）。
关键校准值：K=14（簇规模 625→245，最大簇占 11.0%）、共现网络 1081 节点 / 8695 边、
模块度 Q=0.241、ARI=0.198、NMI=0.450、Cramér's V=0.227、η²=0.083、
相邻 K 最小 ARI=0.590。

> [!] 这些数字**只代表那一份库**。用户在自己的库上运行时，
> 应以实际产物为准，不得引用本包数字冒充自己的结果。
> 任何规模数字脱离参数口径引用即为误导。

## 用户数据存在哪里

运行时数据**全部写在用户自己的工作目录**，绝不写回专家包：

- 影子副本（`.enl` 的临时拷贝）→ `--workspace` 指定目录（默认 `./.lit_work`）
- 分析产物（JSON/CSV/HTML）→ `--out` 指定目录，默认 `./out/`
- 用户自定义主题命名 → `references/topic_labels.local.csv`（**本包不预置，首次运行自动创建**）

若用户删除产物目录，工具下次运行会重新分析生成。
