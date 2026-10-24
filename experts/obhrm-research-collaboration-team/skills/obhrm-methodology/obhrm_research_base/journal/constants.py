"""全局常量：标准枚举、数据版本等（13 项评级标准）。
集中维护，避免散落各处造成不一致。
"""

from __future__ import annotations

# 13 项评级标准（standard 键），集中维护，避免散落各处造成不一致。
ALL_STANDARDS: list[str] = [
    "CAS2025",
    "JCR2025",
    "ABS2024",
    "ABDC2025",
    "FMS2025_CN",
    "FMS2025_GLOBAL",
    "CSSCI2025",
    "CSSCI2025_EXT",
    "FT50",
    "UTD24",
    "PKU2023",
    "CSCD2026",
    "EI2026",
]

# 各标准中文展示名（供渲染）
STANDARD_LABELS: dict[str, str] = {
    "CAS2025": "中科院 2025",
    "JCR2025": "JCR 2025",
    "ABS2024": "ABS 2024（英国商学院协会 AJG）",
    "ABDC2025": "ABDC 2025（澳大利亚商学院院长理事会）",
    "FMS2025_CN": "FMS 2025 中文版",
    "FMS2025_GLOBAL": "FMS 2025 全球版",
    "CSSCI2025": "CSSCI 2025-2026 来源",
    "CSSCI2025_EXT": "CSSCI 2025-2026 扩展",
    "FT50": "FT50 顶级榜",
    "UTD24": "UTD24 顶级榜",
    "PKU2023": "北大核心 2023",
    "CSCD2026": "CSCD 2026",
    "EI2026": "EI 2026",
}

# 数据版本
DATA_VERSION = "2025-2026"

# CAS2025：无「大类」列的 sheet 按 sheet 名映射大类（构建用，已不再需要）
CAS_SHEET_CATEGORY: dict[str, str | None] = {
    "综合": "综合性期刊",
    "巨型期刊": None,
    "IF＜20": None,
    "化学": "化学",
    "生物": "生物",
    "医学": "医学",
    "农林科学": "农林科学",
    "计算机科学": "计算机科学",
    "工程技术": "工程技术",
    "材料科学": "材料科学",
    "环境科学与生态学": "环境科学与生态学",
    "地球科学": "地球科学",
    "物理与天体物理": "物理与天体物理",
    "管理": "管理科学",
}
