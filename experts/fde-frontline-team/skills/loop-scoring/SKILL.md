# 环排序评分（loop-scoring）· 确定性计算

> 适用对象：场景诊断师（主用）、环架构师（复算复核）。公式出处：`references/fde-handbook-judgments.md` #3。

## 公式

评分 =（频次 × 单次耗时 × 规则化程度）÷ 风险，分高先做。

## 输入口径

JSON，数组，每个场景一个对象：

```text
{
  "name": "场景名",
  "freq_per_week": 每周发生次数（数值）,
  "minutes": 单次耗时分钟数（数值）,
  "rule_level": 规则化程度 0 到 1（数值，1 表示规则完全写得清）,
  "risk": 风险等级 1 到 5（数值，5 最高）,
  "irreversible": 出错是否不可逆（布尔，可省略，默认 false）
}
```

数据可以是真实采集值，也可以是合成示例值；示例值须在场景名中带「示例」字样。

## 用法

```bash
python3 scripts/score.py --input <场景.json>   # 从文件读
cat <场景.json> | python3 scripts/score.py      # 从 stdin 读
python3 scripts/score.py --demo                 # 内置合成示例数据演示
python3 scripts/score.py --help                 # 用法说明
```

## 输出格式

- 每行一个场景：排名、名称、四维取值、公式代入过程、总分。
- 纯文本，`[OK]` / `[FAIL]` 标记，无 emoji。
- 命中停工三信号的场景标注停工原因：低频高风险（每周不足 1 次且风险不低于 4）/ 规则说不清（规则化程度低于 0.5）/ 出错不可逆（irreversible 为 true 或风险等于 5）。
- 输入不合法（缺字段、类型错误、越界）输出 `[FAIL]` 并指明原因，退出码 1。

## 停工三信号判定（与判据 #4 对应）

1. 低频高风险：freq_per_week < 1 且 risk >= 4。
2. 规则说不清：rule_level < 0.5。
3. 出错不可逆：irreversible 为 true，或 risk >= 5。

命中任一信号的场景，评分排序表上直接判「先不做」并附一句理由；判定口径固定，不由使用者临时调整。

## 纪律

- 评分一律经本脚本计算，不口算。
- 阈值口径如需调整，改本文件并同步改 `scripts/score.py` 内常量，两处保持一致。
