#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""综述配图封装器：单一入口调用 visualization 域图表引擎（chart_engine.py）。

将 visualization 域图表引擎封装为稳定的脚本入口：图表引擎 ``chart_engine.py`` 已随技能
内置（``chart_engine.py``），路径默认相对本脚本目录解析，``config.json`` 的
``chart_engine_path`` 可覆盖；图表引擎与字体注册均在本进程内完成，不启动子进程、不生成临时脚本（已消除动态代码执行面）。
读图数据 JSON，调用图表引擎生成 PDF + PNG，并把结果透传回调用方，同时向输出目录写入一行
图表登记表（提示图注≥80字、正文需显式引用待补）。

中文乱码修复（关键）
--------------------
受管 Python 环境未挂载字体服务（fontconfig 为空），matplotlib 仅自带 DejaVu，
无法定位 ``PingFang SC`` 等系统 CJK 字体，导致图中中文显示为方块。本脚本在调用
visualization 域图表引擎之前，于本进程内通过 ``matplotlib.font_manager.addfont`` 显式注册一个
系统 CJK 字体（STHeiti / Hiragino Sans GB / Arial Unicode 等），再运行图表引擎，
从而零污染、不修改 chart_engine.py 本身即解决乱码。

除绘图依赖（matplotlib / numpy）外，仅依赖 Python 标准库。

用法
----
    python render_figures.py <chart_type> <data.json> --output DIR
                           [--title T] [--config config.json]

退出码
------
    0  成功
    1  缺少绘图依赖（matplotlib / numpy 未安装）—— 打印安装提示后终止
    2  config / 输入错误（文件缺失、JSON 非法、字段不全）
    3  图表引擎执行失败（非 0 退出或结果无法解析）
"""


# 确保套件包可导入（包目录在上级目录）
import os, sys
_skill_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _skill_dir not in sys.path:
    sys.path.append(_skill_dir)
import argparse
import copy
import importlib.util
import json
import os
import re
import sys

try:
    import matplotlib
    import matplotlib.font_manager as fm
except ImportError:
    # 缺可选绘图依赖：打印明确安装提示并以退出码 1 终止，绝不静默失败
    sys.stderr.write("缺少绘图依赖，请先安装：python3 -m pip install matplotlib numpy\n")
    sys.exit(1)

# 确保 scripts/ 在路径中（便于以脚本方式直接运行 / 被导入），再导入同目录工具
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from obhrm_research_base.core.safe_path import resolve_config_path, resolve_safe_output  # noqa: E402
from obhrm_research_base.core.audit_log import log_event  # noqa: E402

REGISTER_FILE = "图表登记表.md"

# 系统 CJK 字体候选（按优先级）。读取系统公开字体，路径为良性硬编码，直接写明即可。
CJK_FONT_CANDIDATES = [
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/System/Library/Fonts/STHeiti Light.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/Library/Fonts/Arial Unicode.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/chinese/msyh.ttc",
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/simhei.ttf",
]

# 注：字体注册与图表出图均在本进程内完成（直接 import 内置 chart_engine 并调用），
# 不写临时脚本、不启动子进程，因而不存在动态代码执行面与越界执行问题。


# --------------------------------------------------------------------------- #
# 配置加载
# --------------------------------------------------------------------------- #
def _resolve_chart_engine_path(cfg, script_dir):
    """解析 chart_engine.py 的绝对路径。

    严格只使用随技能内置的 ``chart_engine.py``（与 render_figures.py 同级），
    不接受外部覆盖——图表引擎与解释器路径一律使用内置值。

    Args:
        cfg: 已加载的 config 字典（此处仅占位以保持接口稳定）。
        script_dir: 本脚本所在目录（用于定位内置副本）。

    Returns:
        str: 内置 chart_engine.py 的绝对路径。

    Raises:
        ValueError: 内置副本缺失时。
    """
    internal = os.path.join(script_dir, "chart_engine.py")
    if not os.path.isfile(internal):
        raise ValueError(
            "内置图表引擎缺失: %s\n"
            "请确认 chart_engine.py 已随技能一同复制（本脚本不依赖外部技能）。"
            % internal)
    return internal


def load_config(config_path=None):
    """加载 ../config.json，校验并解析图表引擎路径。

    配置约束：
    1. ../config.json 路径必须落在 base（CWD）的子目录内；
    2. 图表引擎与字体注册在本进程内完成，不启动子进程、不生成临时脚本（防动态代码执行）。

    Args:
        config_path: 显式 ../config.json 路径；None 时回退脚本上级目录的 ../config.json。

    Returns:
        dict: 含 chart_engine_path（已解析为内置副本）的配置字典。

    Raises:
        FileNotFoundError: ../config.json 不存在。
        ValueError: 路径超出允许范围 / JSON 非法 / 内置图表引擎不可用。
    """
    user_provided = config_path is not None
    if config_path is None:
        config_path = resolve_config_path(config_path, __file__)
    # (1) 路径范围校验：用户显式提供的 config 须落在 CWD 内；技能包内部默认
    #     config（../config.json）以技能根目录为允许基，避免把受信任的内部路径
    #     误判为越界。
    try:
        from obhrm_research_base.core.safe_path import resolve_safe_output  # 局部导入便于单测 mock
        _base = os.getcwd() if user_provided else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_path = str(resolve_safe_output(config_path, base=_base))
    except ValueError as exc:
        raise ValueError("../config.json 路径超出允许范围: %s" % exc) from exc
    config_path = os.path.abspath(config_path)
    if not os.path.isfile(config_path):
        raise FileNotFoundError("../config.json 未找到: %s" % config_path)
    with open(config_path, encoding="utf-8") as fh:
        cfg = json.load(fh)
    # (2) 图表引擎路径：仅使用内置副本（本进程内调用，无需解释器字段）
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cfg["chart_engine_path"] = _resolve_chart_engine_path(cfg, script_dir)
    return cfg


def detect_cjk_font(config):
    """确定用于渲染中文的 CJK 字体路径。

    优先级：../config.json 的 ``cjk_font_path``（若存在且文件存在）> 候选列表自动探测。

    Args:
        config: load_config 返回的配置字典。

    Returns:
        str: CJK 字体路径；找不到时返回空字符串（chart_engine 退回自身字体列表）。
    """
    explicit = (config.get("cjk_font_path") or "").strip()
    if explicit and os.path.isfile(explicit):
        # 范围校验（轻量、非破坏）：仅当 explicit 落在允许基目录
        # （cwd 或候选字体所在目录）之内才接受；否则忽略并退回自动探测。
        allowed = [os.getcwd()] + [os.path.dirname(c) for c in CJK_FONT_CANDIDATES]
        _explicit_ok = False
        for b in allowed:
            try:
                resolve_safe_output(explicit, base=b)
                _explicit_ok = True
                break
            except ValueError:
                continue
        if _explicit_ok:
            return explicit
    for cand in CJK_FONT_CANDIDATES:
        if os.path.isfile(cand):
            return cand
    return ""


# --------------------------------------------------------------------------- #
# 调用组装与执行
# --------------------------------------------------------------------------- #
def run_chart_engine(chart_type, data_obj, output_dir, cjk_font_path, chart_engine_path):
    """进程内加载 chart_engine 并出图：注册 CJK 字体、写审计留痕。

    不再生成临时脚本、不再启动子进程——直接在本进程 import 内置 chart_engine
    并调用，不产生动态代码执行面与越界执行问题。

    Returns:
        Tuple[int, str, str]: (returncode, stdout_json, stderr)。
    """
    # 审计：执行前记录图表引擎路径（本进程内执行，无外部解释器）。
    log_event("script_executed", path="render_figures.py",
              detail="in-process chart_engine=%s" % chart_engine_path)
    # 注册 CJK 字体（本进程内，不启动子进程、不写临时文件）。
    if cjk_font_path and os.path.isfile(cjk_font_path):
        try:
            fm.fontManager.addfont(cjk_font_path)
            name = fm.FontProperties(fname=cjk_font_path).get_name()
            sans = list(matplotlib.rcParams.get("font.sans-serif", []))
            if name and name not in sans:
                sans.insert(0, name)
            matplotlib.rcParams["font.sans-serif"] = sans
            matplotlib.rcParams["font.family"] = "sans-serif"
            matplotlib.rcParams["axes.unicode_minus"] = False
        except Exception as exc:
            sys.stderr.write("CJK font warning: %s\n" % exc)
    # 进程内导入内置图表引擎（路径已锁死为内置副本）。
    try:
        spec = importlib.util.spec_from_file_location("chart_engine_mod", chart_engine_path)
        ce = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ce)
    except Exception as exc:
        log_event("script_completed", path="render_figures.py",
                  detail="rc=1 chart_engine=%s" % chart_engine_path)
        return 1, "", "图表引擎加载失败: %s" % exc
    # 设置输出目录（范围校验）。
    try:
        safe = ce.resolve_safe_output(output_dir, base=os.getcwd())
        ce._set_output_dir(str(safe))
    except ValueError as exc:
        return 1, "", "错误: 输出目录超出允许范围 — %s" % exc
    if chart_type not in ce.CHART_MAP:
        return 1, "", "未知图表类型: %s" % chart_type
    try:
        result = ce.CHART_MAP[chart_type](copy.deepcopy(data_obj))
    except Exception as exc:
        return 1, "", "图表引擎执行异常: %s" % exc
    log_event("script_completed", path="render_figures.py",
              detail="rc=0 chart_engine=%s" % chart_engine_path)
    return 0, json.dumps(result, ensure_ascii=False), ""


def parse_result(stdout):
    """从 bootstrap stdout 解析 {"pdf":..., "png":...} 结果。"""
    match = re.search(r"\{.*\}", stdout, re.DOTALL)
    if not match:
        raise ValueError("图表引擎未返回可解析的 JSON 结果")
    result = json.loads(match.group(0))
    if not isinstance(result, dict) or "pdf" not in result or "png" not in result:
        raise ValueError("图表引擎结果缺少 pdf/png 字段")
    return result


# --------------------------------------------------------------------------- #
# 图表登记表
# --------------------------------------------------------------------------- #
def _register_next_number(register_path):
    """读取已有登记表中已用的最大图号，返回下一个编号。"""
    if not os.path.isfile(register_path):
        return 1
    with open(register_path, encoding="utf-8") as fh:
        text = fh.read()
    nums = [int(m.group(1)) for m in re.finditer(r"\|\s*图(\d+)", text)]
    return (max(nums) + 1) if nums else 1


def _parse_register_rows(register_path):
    """解析已有登记表，返回数据行列表（dict）。忽略表头行与分隔行。"""
    rows = []
    if not os.path.isfile(register_path):
        return rows
    with open(register_path, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line.startswith("|"):
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            if not cells:
                continue
            # 表头行（首格为「编号」）或分隔行（仅由 - : 空格 组成）跳过
            if cells[0] == "编号":
                continue
            if all(set(c) <= set("-: ") for c in cells):
                continue
            rows.append({
                "编号": cells[0] if len(cells) > 0 else "",
                "类型": cells[1] if len(cells) > 1 else "",
                "标题": cells[2] if len(cells) > 2 else "",
                "png": cells[3] if len(cells) > 3 else "",
                "pdf": cells[4] if len(cells) > 4 else "",
                "图注": cells[5] if len(cells) > 5 else "",
                "正文引用": cells[6] if len(cells) > 6 else "",
            })
    return rows


def _ref_from_label(figure_label, fallback_num):
    """由 figure_label（如 '图1'）生成正文引用文本（如 '如图1'）。"""
    m = re.search(r"(\d+)", figure_label or "")
    num = m.group(1) if m else str(fallback_num)
    return "如图%s" % num


def _cell(text):
    """转义登记表单元格：去除换行、把竖线替换为斜杠，避免破坏 Markdown 表格。"""
    return (text or "").replace("\n", " ").replace("|", "/")


def write_register(output_dir, chart_type, title, result, caption=None, figure_label=None):
    """重写图表登记表：按 PNG 路径去重（删除所有同 PNG 路径的旧行），
    重新编号 图1..图N 后整体重写整张表。

    去重逻辑说明
    ------------
    以「追加」模式登记时，同一 PNG 被多次登记（重复运行 / 重渲染）会产生重复行。
    本实现采用「解析 → 去重 → 重编号 → 整体重写」：
    1. 解析已有表中所有数据行；
    2. 删除 png 字段等于本次结果 PNG 路径的全部旧行（含历史重复行）；
    3. 追加本次新行（图注列填 caption，正文引用列由 figure_label 推导为「如图N」）；
    4. 按 图1..图N 顺序重编号所有行（不重排顺序，仅补连续编号）；
    5. 以「w」模式整体重写表（表头一并重写，保证结构一致）。

    Args:
        output_dir: 输出目录。
        chart_type: 图类型。
        title: 图标题。
        result: 图表引擎返回的 {"pdf":.., "png":..}。
        caption: 图注文本（可选；None 时写待补提示）。
        figure_label: 图号标签（如 "图1"，可选），用于正文引用列。
    """
    register_path = os.path.join(output_dir, REGISTER_FILE)
    png = result["png"]
    pdf = result["pdf"]

    # 1) 解析已有数据行
    rows = _parse_register_rows(register_path)

    # 2) 去重：记录所有与本图 PNG 路径相同的旧行位置，删除这些旧行
    #    （含历史重复行），并保留首个旧行的位置，使重渲染后本图编号不挪动、
    #    后续图的编号保持稳定（仅重排被删除行造成的空缺）。
    dup_indices = [i for i, r in enumerate(rows) if r.get("png") == png]
    insert_at = min(dup_indices) if dup_indices else len(rows)
    rows = [r for i, r in enumerate(rows) if i not in dup_indices]

    # 3) 组装本次新行
    if caption:
        cap_cell = _cell(caption)
    else:
        cap_cell = "[!] 待补：图注需≥80字（做了什么+发现什么+为何重要）"
    num_for_ref = insert_at + 1
    if figure_label:
        ref_cell = _ref_from_label(figure_label, num_for_ref)
    else:
        ref_cell = "[!] 待补：正文需≥1处显式引用（如图%d）" % num_for_ref
    new_row = {
        "编号": "",  # 重编号时填充
        "类型": chart_type,
        "标题": _cell(title) or "—",
        "png": png,
        "pdf": pdf,
        "图注": cap_cell,
        "正文引用": ref_cell,
    }
    rows.insert(insert_at, new_row)

    # 4) 重新编号 图1..图N
    for j, r in enumerate(rows):
        r["编号"] = "图%d" % (j + 1)

    # 5) 整体重写表（含表头）
    lines = []
    lines.append("# 图表登记表（Figure Register）")
    lines.append("")
    lines.append("> 每张图生成后立即登记。图注需≥80字（做了什么+发现什么+为何重要），")
    lines.append("> 正文需≥1处显式引用（如图N）。图、表分开连续编号。")
    lines.append("")
    lines.append("| 编号 | 类型 | 标题 | 文件(PNG) | 文件(PDF) | 图注 | 正文引用 |")
    lines.append("|------|------|------|-----------|-----------|------|----------|")
    for r in rows:
        lines.append("| %s | %s | %s | %s | %s | %s | %s |" % (
            r["编号"], r["类型"], r["标题"], r["png"], r["pdf"],
            r["图注"], r["正文引用"]))
    with open(register_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


# --------------------------------------------------------------------------- #
# 主流程
# --------------------------------------------------------------------------- #
def main(argv):
    """命令行入口。"""
    ap = argparse.ArgumentParser(description="综述配图封装（调用 OBHRM 图表引擎 chart_engine）")
    ap.add_argument("chart_type", help="图类型（如 流程图 / 网络图 / 桑基图 / 思维导图）")
    ap.add_argument("data_json", help="图数据 JSON 文件路径")
    ap.add_argument("--out", "--output", dest="output", required=True, help="输出目录（PDF+PNG 写入此处）")
    ap.add_argument("--title", default=None, help="图标题")
    ap.add_argument("--caption", default=None, help="图注文本（合并进图数据，并写入登记表图注列）")
    ap.add_argument("--figure-label", default=None, dest="figure_label",
                    help="图号标签（如 图1；合并进图数据，并用于登记表正文引用列，如 '如图1'）")
    ap.add_argument("--config", default=None, help="../config.json 路径（默认脚本上级目录）")
    args = ap.parse_args(argv)

    # --output 必须落在 cwd 之内；在读取任何数据前快速失败
    try:
        args.output = str(resolve_safe_output(args.output, base=os.getcwd()))
    except ValueError as exc:
        print("错误(--output): %s" % exc, file=sys.stderr)
        return 2

    # 配置
    try:
        config = load_config(args.config)
    except (FileNotFoundError, ValueError) as exc:
        print("错误(config): %s" % exc, file=sys.stderr)
        return 2

    # 数据文件
    data_path = os.path.abspath(args.data_json)
    if not os.path.isfile(data_path):
        print("错误: 图数据文件未找到: %s" % data_path, file=sys.stderr)
        return 2
    try:
        with open(data_path, encoding="utf-8") as fh:
            data_obj = json.load(fh)
    except (ValueError, OSError) as exc:
        print("错误: 图数据 JSON 解析失败: %s" % exc, file=sys.stderr)
        return 2

    # 将 CLI 传入的图注 / 图号合并进图数据，透传给图表引擎（用于图下方渲染）
    if args.caption:
        data_obj["caption"] = args.caption
    if args.figure_label:
        data_obj["figure_label"] = args.figure_label

    # 登记时优先用 CLI，未提供则回退到图数据里的 caption/figure_label
    if not args.caption and data_obj.get("caption"):
        args.caption = data_obj["caption"]
    if not args.figure_label and data_obj.get("figure_label"):
        args.figure_label = data_obj["figure_label"]

    # 输出目录（已在上方经 resolve_safe_output 校验并解析为绝对路径）
    output_dir = args.output
    os.makedirs(output_dir, exist_ok=True)

    # CJK 字体探测 + 进程内出图（不再写临时脚本、不再启动子进程）。
    cjk_font_path = detect_cjk_font(config)
    rc, out, err = run_chart_engine(
        args.chart_type, data_obj, output_dir, cjk_font_path, config["chart_engine_path"])

    if rc != 0:
        print("错误: 图表引擎执行失败 (returncode=%d)" % rc, file=sys.stderr)
        if err.strip():
            print(err.strip(), file=sys.stderr)
        return 3
    try:
        result = parse_result(out)
    except ValueError as exc:
        print("错误: %s" % exc, file=sys.stderr)
        if out.strip():
            print("stdout: %s" % out.strip(), file=sys.stderr)
        return 3

    write_register(output_dir, args.chart_type, args.title, result,
                   caption=args.caption, figure_label=args.figure_label)

    print(json.dumps(result, ensure_ascii=False))
    if cjk_font_path:
        print("CJK 字体已注入: %s" % cjk_font_path)
    else:
        print("提示: 未探测到系统 CJK 字体，图表引擎退回自身字体列表（中文可能仍为方块）。")
    print("图表登记表已更新: %s" % os.path.join(output_dir, REGISTER_FILE))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
