#!/usr/bin/env python3
"""
OBHRM 研究协作团 — 图表引擎冒烟测试 (smoke test)
一键生成全部图表类型，确认每种都不崩、都产出 PDF + PNG。

用法（在技能目录或其父目录下）：
    python selftest.py

退出码：全部通过=0，任一失败=1。新增/修改图表类型后务必先跑本测试。
"""

import os
import sys
import tempfile
import importlib.util

# 固定 matplotlib 缓存目录，避免缓存目录不可写导致报错
os.environ.setdefault("MPLCONFIGDIR", tempfile.mkdtemp(prefix="mplcache_"))

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENGINE_PATH = os.path.join(SKILL_DIR, "scripts", "chart_engine.py")

try:
    spec = importlib.util.spec_from_file_location("chart_engine", ENGINE_PATH)
    engine = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(engine)
except Exception as e:  # noqa: BLE001
    print(f"[X] 图表引擎导入失败：{type(e).__name__}: {e}")
    sys.exit(1)

# 每种图表的最小可用样例（字段名与图表引擎函数签名一致）
SAMPLES = {
    "条形图": {"categories": ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"], "values": [4.2, 3.8, 4.0, 3.5, 4.5, 3.9, 4.1, 3.7, 4.3, 3.6], "errors": [0.3, 0.4, 0.3, 0.4, 0.3, 0.4, 0.3, 0.4, 0.3, 0.4], "xlabel": "组别", "ylabel": "均值"},
    "箱线图": {"data": [[1, 2, 3, 4], [2, 3, 4, 5]], "labels": ["A组", "B组"]},
    "小提琴图": {"data": [[1, 2, 3, 4], [2, 3, 4, 5]], "labels": ["A组", "B组"]},
    "折线图": {"x": [1, 2, 3], "series": [{"label": "系列1", "values": [1, 2, 3]}]},
    "散点图": {"x": [1, 2, 3, 4], "y": [2, 3, 4, 5], "show_regression": True},
    "森林图": {"studies": ["研究1", "研究2", "总体"], "effects": [0.3, 0.5, 0.4],
               "ci_lower": [0.1, 0.3, 0.25], "ci_upper": [0.5, 0.7, 0.55]},
    "热图": {"matrix": [[1, 0.2, -0.3], [0.2, 1, 0.4], [-0.3, 0.4, 1]], "labels": ["X", "Y", "Z"]},
    "漏斗图": {"effects": [0.2, 0.3, 0.4, 0.35], "se": [0.05, 0.06, 0.04, 0.05]},
    "分组条形图": {"categories": ["A", "B"], "groups": [{"label": "男", "values": [4, 5]}, {"label": "女", "values": [3, 4]}]},
    "雷达图": {"labels": ["沟通", "创新", "执行"], "series": [{"label": "团队1", "values": [3, 4, 5]}]},
    "鱼骨图": {"problem": "绩效低", "causes": [{"label": "领导", "sub_causes": ["风格", "支持"]},
                                            {"label": "资源", "sub_causes": ["时间"]}]},
    "桑基图": {"flows": [{"source": "检索", "target": "纳入", "value": 30},
                       {"source": "纳入", "target": "分析", "value": 20}]},
    "韦恩图": {"sets": [{"label": "A", "size": 10}, {"label": "B", "size": 8}]},
    "网络图": {"nodes": [{"id": "n1", "label": "理论", "size": 2}, {"id": "n2", "label": "方法", "size": 1}],
               "edges": [{"source": "n1", "target": "n2", "weight": 1}]},
    "思维导图": {"root": "主题", "children": [{"text": "分支1", "children": ["子1", "子2"]},
                                           {"text": "分支2", "children": ["子3"]}]},
    "流程图": {"steps": [{"text": "开始", "type": "start"}, {"text": "分析", "type": "process"},
                       {"text": "是否显著", "type": "decision"}, {"text": "结束", "type": "end"}]},
    "直方图": {"values": [1, 2, 2, 3, 3, 3, 4, 4, 5], "bins": 5},
    "饼图": {"labels": ["A", "B"], "values": [60, 40]},
    "面积图": {"x": [1, 2, 3], "series": [{"label": "系列1", "values": [1, 2, 3]}]},
    "简单斜率图": {"x": [-2, 2], "groups": [{"label": "高调节", "intercept": 2.1, "slope": 0.8},
                                          {"label": "低调节", "intercept": 2.1, "slope": -0.3}], "highlight": True},
}


# 已知可选依赖：缺失时相关图表应优雅降级或跳过，不应导致整套测试失败（CI 健壮性）。
OPTIONAL_DEPS = {"seaborn"}


def _is_optional_dep_missing(e: Exception) -> "str | None":
    if isinstance(e, ModuleNotFoundError):
        mod = getattr(e, "name", None)
        if mod in OPTIONAL_DEPS:
            return mod
    msg = str(e)
    for mod in OPTIONAL_DEPS:
        if f"No module named '{mod}'" in msg or f"nomodule named {mod}" in msg:
            return mod
    return None


def main():
    out = tempfile.mkdtemp(prefix="chart_selftest_")
    engine._set_output_dir(out)
    total = len(engine.CHART_MAP)
    # 图表映射表为空时不应算“全部通过”（防止空表误判为通过）。
    if total == 0:
        print("图表引擎冒烟测试：CHART_MAP 为空，无图表可测 —— 视为失败（防止空表误判为通过）。")
        sys.exit(1)
    ok, fail, skip = [], [], []

    for name, fn in engine.CHART_MAP.items():
        try:
            payload = SAMPLES.get(name, {})
            res = fn(payload)
            pdf = res.get("pdf")
            png = res.get("png")
            # F4：不仅检查文件存在，还要非空且为合法 PDF（避免产出空/损坏文件仍算通过）。
            if (pdf and png and os.path.exists(pdf) and os.path.exists(png)
                    and os.path.getsize(pdf) > 0 and os.path.getsize(png) > 0):
                with open(pdf, "rb") as _fh:
                    is_pdf = _fh.read(5) == b"%PDF-"
                if is_pdf:
                    ok.append(name)
                else:
                    fail.append((name, "PDF 文件头非法（非 %PDF-）"))
            else:
                fail.append((name, "输出文件缺失或为空"))
        except Exception as e:  # noqa: BLE001
            mod = _is_optional_dep_missing(e)
            if mod:
                skip.append((name, f"跳过：可选依赖 '{mod}' 未安装；pip install {mod} 后可完整校验"))
            else:
                fail.append((name, f"{type(e).__name__}: {e}"))

    print(f"图表引擎冒烟测试：共 {total} 种，通过 {len(ok)}，失败 {len(fail)}，跳过 {len(skip)}")
    if ok:
        print("[OK] 通过:", "、".join(ok))
    if skip:
        print("[~] 跳过（可选依赖缺失，非缺陷）:")
        for n, msg in skip:
            print(f"  - {n}: {msg}")
    if fail:
        print("[X] 失败:")
        for n, msg in fail:
            print(f"  - {n}: {msg}")
        sys.exit(1)
    if skip and not fail:
        print("核心图表全部通过；可选依赖缺失项已跳过（安装对应依赖后复跑可清零）。")
    elif not skip and not fail:
        print("全部通过，无崩溃。")


if __name__ == "__main__":
    main()
