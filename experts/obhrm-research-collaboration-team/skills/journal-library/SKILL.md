---
name: journal-library
version: 1.0.0
description: "OBHRM 期刊评级库数据资产 — 28,241 刊 / 149,117 评级 / 13 套评级体系，只读真源，由 skills/obhrm-methodology/scripts/query.py 查询。"
---

# journal-library · 期刊评级数据库（数据资产技能）

本技能仅承载期刊/评级综合数据库 `db/journals.db`（整包最大单文件，约 19 MB），是选刊路径的**只读真源**。

## 定位
- 与 `obhrm-research-base` 解耦：查询引擎（`query.py` + `obhrm_research_base` 包）留在 `obhrm-research-base`，期刊数据独立为本技能，便于单独维护与体积管理。
- 查询入口：`skills/obhrm-methodology/scripts/query.py "<keyword>" --json`（由 `obhrm-research-base` 挂载，跨技能读取本库）。
- 规模：28,241 刊 / 149,117 评级 / 6,259 学科分类 / 13 套评级体系（CAS2025、JCR2025、ABS2024、ABDC2025、CSSCI2025、CSCD2026、EI2026、PKU2023、FMS2025、FT50、UTD24 等）。

## 使用纪律
- 期刊评级必须来自本库可查真源，绝不凭空给出分区/影响因子。
- 本库为只读，禁止修改；缺失/损坏时 `query.py` 的 degrade 分支会输出降级提示而非裸错误。
- 读取受 `obhrm-research-base` 的 `safe_path.py` 约束，仅限本技能目录。
