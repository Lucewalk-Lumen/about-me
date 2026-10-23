# 教材质量指标体系与评分系统

> 本文档定义当前用户侧脚本的**四层等权 10 分制**、JSON 输出结构、Panorama 结果口径以及与旧文档的迁移说明。

---

## 1. 评分体系总览

### 1.1 四层等权 10 分制

| 层级 | 当前规则数 | 层内满分 | 计算方式 | 说明 |
|---|---:|---:|---|---|
| S层 | 6 | 10 | `通过条数 ÷ 6 × 10` | 句级扫描 |
| P层 | 4 | 10 | `通过条数 ÷ 4 × 10` | 段级检测 |
| C层 | 4 | 10 | `通过条数 ÷ 4 × 10` | 章级审查 |
| B层 | 6 | 10 | `通过条数 ÷ 6 × 10` | 当前脚本含 `B0 / B1 / B2_1 / B2_2 / B2_C / B3` |

```text
综合分 = (S + P + C + B) ÷ 4
```

### 1.2 V1 / G / C0 的位置

| 项目 | 当前角色 | 是否并入综合分 | 说明 |
|---|---|---|---|
| V1 | 附加观测项 | 否 | 视觉密度 / 图文支撑度，单独输出 |
| G | 门禁 | 否 | pass / fail，与综合分并列展示 |
| C0 | 全书终审 | 否 | 全书一致性、去重、术语、交付门禁 |

### 1.3 通过阈值

| 等级 | 条件 | 含义 |
|---|---|---|
| 通过 | `overall >= 7.5` 且 G 全绿 | 允许进入下一阶段 |
| 弱通过 | `7.0 <= overall < 7.5` 且 G 全绿 | 建议润色 |
| 不通过 | `overall < 7.0` 或 G 有红灯 | 必须修改 |

### 1.4 与旧口径的差异

- 不再使用 “20 分原始分 → ÷2 → 10 分” 的折算模型。
- 不再用规则条数隐式决定层间权重；四层统一等权。
- V1 与 G 不再和 S/P/C/B 混算。
- B 层当前脚本包含 `B0`，用于避免编号混乱导致的假高分。

---

## 2. 脚本输出结构

### 2.1 轻量评分输出结构

```json
{
  "timestamp": "2026-04-11T02:30:00.000Z",
  "scoringVersion": "10-point-equal-layers-v1",
  "minScore": 7.5,
  "total": 2,
  "passed": 1,
  "failed": 1,
  "avgScore": 7.85,
  "results": [
    {
      "filePath": "<workspace>/book/ch01.md",
      "profile": "standard",
      "scores": {
        "S": 8.3,
        "P": 7.5,
        "C": 7.5,
        "B": 8.3,
        "V1": 2.0,
        "overall": 7.9
      },
      "threshold": {
        "min": 7.5,
        "passed": true
      },
      "details": {
        "S": {},
        "P": {},
        "C": {},
        "B": {}
      }
    }
  ]
}
```

字段说明：

| 字段 | 说明 |
|---|---|
| `scores.S/P/C/B` | 四层 10 分制层分 |
| `scores.V1` | 附加观测项，不并入 `overall` |
| `scores.overall` | 当前综合分 |
| `threshold.passed` | 是否达到当前 `minScore` |
| `details.*` | 规则级明细，含 `passed` 与上下文数据 |

### 2.2 机器扫描输出结构

```json
{
  "timestamp": "2026-04-11T02:31:00.000Z",
  "standalone": true,
  "bookRoot": "<workspace>/book",
  "total": 12,
  "issueCount": 3,
  "warningCount": 18,
  "issues": ["[编号重复] ch03.md: 2.1"],
  "warnings": ["[破折号] ch05.md: 1.6/千字 > 1（警告阈值）"],
  "autoFix": {
    "diffPath": "<workspace>/book/qc-output/auto-fix-diff.md",
    "changedFiles": 4,
    "write": false
  },
  "results": [
    {
      "filePath": "<workspace>/book/ch05.md",
      "metrics": {
        "chars": 5240,
        "dashDensity": 1.6,
        "connectorDensity": 0.9,
        "adverbDensity": 0.5,
        "buzz": ["赋能"]
      },
      "issues": [],
      "warnings": []
    }
  ]
}
```

### 2.3 全景/深度总控输出结构

```json
{
  "status": "completed",
  "modeUsed": "panorama",
  "generatedAt": "2026-04-11T02:33:50.481Z",
  "bookRoot": "<workspace>/book",
  "totalFiles": 94,
  "totalChars": 525871,
  "heatmap": [
    {
      "group": "references",
      "fileCount": 67,
      "s2Density": 0.62,
      "s4Density": 0.16,
      "s5Hits": 186,
      "s6Density": 0.22,
      "sampleOverall": 7.7,
      "risk": "[黄/待优化]"
    }
  ],
  "machineScan": {
    "total": 94,
    "issueCount": 0,
    "warningCount": 278,
    "reportPath": "<workspace>/book/qc-output/panorama-machine-scan.json"
  },
  "sampleAudit": {
    "total": 10,
    "avgScore": 7.81,
    "reportPath": "<workspace>/book/qc-output/panorama-lite-audit.json"
  }
}
```

### 2.4 快速扫描输出结构

```json
{
  "generatedAt": "2026-04-11T10:40:00+08:00",
  "bookRoot": "<workspace>/book",
  "totalFiles": 8,
  "summary": {
    "s2Hits": 12,
    "s4Hits": 5,
    "s5Hits": 9,
    "duplicateSectionIds": 1
  },
  "files": [
    {
      "filePath": "<workspace>/book/ch01.md",
      "chars": 4100,
      "s2Density": 0.49,
      "s4Density": 0.24,
      "s5Hits": 2,
      "s6Density": 0.0,
      "intPercentDensity": 0.24,
      "sectionIdIssues": {
        "missing": 0,
        "duplicates": []
      }
    }
  ]
}
```

---

## 3. 指标与阈值

### 3.1 关键机读指标

| 指标 | 来源脚本 | 含义 | 典型阈值 |
|---|---|---|---|
| `adverbDensity` / `s2Density` | Machine / Panorama / Quick Scan | 冗余修饰词密度 | 越低越好 |
| `connectorDensity` / `s4Density` | Machine / Panorama / Quick Scan | 连接词密度 | `< 2/千字` |
| `buzz.length` / `s5Hits` | Machine / Panorama / Quick Scan | Buzzword 命中数 | `= 0` 更佳 |
| `dashDensity` / `s6Density` | Machine / Panorama / Quick Scan | 破折号密度 | `<= 1/千字` |
| `longSentenceRatio` | Machine | 超长句占比 | `< 10%` |
| `details.B.B2_1.cv` | Lite | 段落节奏 CV | `>= 0.3` |
| `details.B.B3.cv` | Lite | 全局节奏 CV | `>= 0.4`（经验线） |
| `scores.V1` | Lite | 视觉密度 / 图文支撑度 | `>= 10` 为达标图文书口径 |

### 3.2 风险等级建议

| 条件 | 风险 |
|---|---|
| 机器指标低、抽样分 ≥ 7.5 | [绿/通过] |
| 机器指标有明显尖峰，或抽样分 < 7.5 | [黄/待优化] |
| 多个机读指标同时偏高，或抽样分明显偏低 | [红/不通过] |

---

## 4. 运行与验收建议

### 4.1 执行方式

机器可检项按 S/P/C/B 分层执行；按书稿规模选择「增量」或「全景 / 深度」两种粒度（见 §4.2）。裸书稿直接按分层规则逐项扫描；机器可修项以候选 diff 形式给出后再复核。

### 4.2 验收顺序

1. 先确认环境：有无 Node、有无 `.fbs/`、是否进入存量模式。
2. 文件数超过 10 时先跑 Panorama，再决定 Deep 范围。
3. 机器可修项优先走 `--auto-fix` 生成候选 diff。
4. G 门禁与 C0 终审必须单独记录，不能只看 `overall`。

---

## 5. 兼容与保留字段说明

### 5.1 旧口径迁移

| 旧字段 / 口径 | 当前建议 |
|---|---|
| `total_raw` / `total_converted` | 迁移到 `scores.S/P/C/B/V1/overall` |
| `20分 → ÷2` | 改为四层等权平均 |
| `±G分` | 改为 `G = pass / fail` |

### 5.2 关于质量仪表盘

当前用户侧脚本**默认不会**自动写入 `.fbs/quality-dashboard.json`。稳定真值请以以下文件为准：

- `qc-output/quality-audit-lite.json`
- `qc-output/quality-audit-machine.json`
- `qc-output/panorama-report.json`
- `.fbs/quality-panorama-partial.json` 与 `.fbs/quality-panorama-stages/*.json`（若存在）

如需质量仪表盘，应基于上述 JSON 二次汇总后再展示，不应在用户侧文档中提前宣称“已自动落盘”。
