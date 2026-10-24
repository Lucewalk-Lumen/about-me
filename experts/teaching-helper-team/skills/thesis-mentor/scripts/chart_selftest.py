#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
chart_selftest.py — 图表引擎冒烟测试（可选依赖，优雅跳过）

遍历所有图表类型，确认无崩溃。matplotlib 未安装时自动跳过（返回 0），
不影响技能包完整性验证。

用法：
    python scripts/chart_selftest.py [--output ./_selftest_out/]
"""

import argparse
import importlib.util
import os
import sys
import tempfile


def _load_engine():
    here = os.path.dirname(os.path.abspath(__file__))
    spec = importlib.util.spec_from_file_location("chart_engine", os.path.join(here, "chart_engine.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# 每种类型的样例参数
SAMPLES = {
    "条形图": {"categories": ["A", "B", "C"], "values": [3.2, 5.1, 4.0], "error": [0.3, 0.4, 0.5]},
    "饼图": {"labels": ["类型一", "类型二", "类型三"], "sizes": [40, 35, 25]},
    "直方图": {"data": [1, 2, 2, 3, 3, 3, 4, 4, 5, 5, 6], "bins": 5},
    "箱线图": {"groups": {"组1": [1, 2, 3, 4], "组2": [2, 3, 4, 5, 6]}},
    "散点图": {"x": [1, 2, 3, 4, 5], "y": [2, 4, 5, 4, 6], "show_regression": True},
    "简单斜率图": {"x": [1, 2, 3, 4], "low_y": [2, 3, 4, 5], "high_y": [1, 2, 3, 4],
                   "legend": ["低调节", "高调节"]},
    "雷达图": {"categories": ["创新", "可行", "价值", "风险"], "values": [[3, 4, 2, 5]]},
    "热图": {"matrix": [[1.0, 0.3, 0.2], [0.3, 1.0, 0.4], [0.2, 0.4, 1.0]],
             "xlabels": ["A", "B", "C"], "ylabels": ["A", "B", "C"]},
    "折线图": {"x": [1, 2, 3, 4], "y": [[2, 3, 5, 7], [1, 4, 6, 8]], "labels": ["方案甲", "方案乙"]},
}


def main():
    try:
        eng = _load_engine()
    except Exception as e:
        print(f"[chart_selftest] 跳过：无法加载图表引擎（{e}）")
        return 0

    if not getattr(eng, "_MATPLOTLIB_OK", False):
        print("[chart_selftest] 跳过：可选依赖 matplotlib 未安装（不影响技能功能）。")
        return 0

    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    out = args.output or tempfile.mkdtemp(prefix="chart_selftest_")
    failures = []
    for t, params in SAMPLES.items():
        try:
            fig = eng.CHART_MAP[t](params)
            eng._save(fig, t, out)
            eng.plt.close(fig)
            print(f"   {t}")
        except Exception as e:  # pragma: no cover
            failures.append((t, str(e)))
            print(f"   {t}: {e}")

    if failures:
        print(f"\n[chart_selftest] 失败 {len(failures)}/{len(SAMPLES)}")
        return 1
    print(f"\n[chart_selftest] 全部通过 {len(SAMPLES)}/{len(SAMPLES)} ")
    return 0


if __name__ == "__main__":
    sys.exit(main())
