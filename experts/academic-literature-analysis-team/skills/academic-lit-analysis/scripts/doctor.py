#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
doctor.py —— 环境自检（R10 防护）

为什么必须有这个:
  同机可能存在多个同版本 Python，部分装了 scikit-learn + jieba，
  另一个没有 ——同一句 `python3 xxx.py` 在不同环境下包可用性完全不同。
  且系统 python3.9.6 连 numpy 都没有。
  → 用户按`python3 xxx.py` 会得到误导性的 No module named numpy / sklearn，
  而真正的原因是【解释器选错】，不是【包没装】。

退出码:
    0 = 环境就绪
    8 = 环境不满足（EXIT_ENV_UNMET）
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
# [!]  必须导入：第 107 行要用 EXIT[8] 输出修复指引。缺失时该行抛
#    NameError → 退出码 1，而failure_paths.md 定义 1 = 源库不可用
#    （移动硬盘未连接），与本处「环境不满足」语义完全相反，会误导 Agent。
#    lit_core 不依赖任何第三方包，也不 import 本模块，无循环依赖。
from lit_core import EXIT, find_rscript as _find_rscript  # noqa: E402

REQUIRED = [
    ("numpy", ">=1.24"),
    ("sklearn", ">=1.3"),
    ("jieba", ">=0.42"),
]
OPTIONAL = [
    ("networkx", ">=3.0（本包布局用纯 numpy 实现，非必需）"),
]
MIN_PY = (3, 9)

FIX_HINT = {
    "numpy":   "pip install numpy",
    "sklearn": "pip install scikit-learn",
    "jieba":   "pip install jieba  # 注意：0.42.1 直接 pip 安装可能报 OSError:EEXIST，"
               "需手动解包后 pip install .（见 README 故障排查）",
}


def probe(mod_name: str):
    try:
        mod = __import__(mod_name)
        return True, getattr(mod, "__version__", "?"), None
    except ImportError as e:
        return False, None, str(e)
    except Exception as e:  # noqa: BLE001
        return False, None, f"{type(e).__name__}: {e}"


# ── R + igraph（必需前置条件）─────────────────────
# 为什么必需：计量分析要有标准工具链（igraph / bibliometrix 生态），结果才可复现、
# 才能与他人的 SNA 结果对话。若把 R 当「可选交叉验证」、缺失时 sna_r.py 静默
# 回退纯 Python 并 exit 0 —— 用户会拿到一份"完整报告"却不知道网络部分只是度数排序。
R_INSTALL_GUIDE = (
    "R + igraph 安装指引（必需前置条件）：\n"
    "  1) 下载安装 R（>=4.2）: https://cran.r-project.org/  "
    "（Windows 选 base 包；勾选「Add R to PATH」可避免后续找不到 Rscript）\n"
    "  2) 配置国内镜像（写入 ~/.Rprofile 更持久）:\n"
    "     options(repos = c(CRAN = \"https://mirrors.tuna.tsinghua.edu.cn/CRAN/\"))\n"
    "  3) 安装 igraph（装到用户库，无需管理员权限）:\n"
    "     Rscript -e \"install.packages('igraph', lib=Sys.getenv('R_LIBS_USER'), "
    "repos='https://mirrors.tuna.tsinghua.edu.cn/CRAN/')\"\n"
    "  4) 已装好 R 但本机报「找不到 Rscript」：这是 Windows 版 R 的默认行为"
    "（不写 PATH）。\n"
    "     把 <R安装目录>/bin 加入 PATH，或运行时用完整路径，"
    "例如 C:/Program Files/R/R-<版本>/bin/Rscript.exe"
)


def find_rscript():
    """定位 Rscript，返回 (path | None, source)。

    委托 lit_core.find_rscript —— **唯一实现**。
    此前 doctor.py 自带一套只扫 Windows `C:\\Program Files\\R` 的 glob，
    而 sna_r.py 另扫一套；两处口径不一致会出现「doctor 放行、sna_r 却
    exit 8」的自相矛盾（尤其在 macOS/Linux 上，doctor 那套完全扫不到）。
    门禁与执行层必须用同一个探测实现，否则门禁形同虚设。
    """
    return _find_rscript()


def probe_r():
    """检测 R + igraph。

    返回 (ok, path, detail, r_version, source)：
      ok=True  → detail 为 igraph 版本号；
      ok=False → detail 为可读失败原因（区分「未找到 R」与「R 在但缺 igraph」，
                 后者是两种完全不同的修复动作，不能混为一谈）。
    """
    rs, src = find_rscript()
    if not rs:
        return False, None, "未找到 Rscript（PATH 与常见安装目录都没有）", "", ""
    rver = ""
    try:
        v = subprocess.run([rs, "--version"],
                           capture_output=True, text=True, timeout=30)
        rver = (v.stdout or v.stderr or "").splitlines()[0].strip()
    except Exception:  # noqa: BLE001
        pass
    try:
        out = subprocess.run(
            [rs, "-e", "cat(as.character(packageVersion('igraph')))"],
            capture_output=True, text=True, timeout=60)
        ver = (out.stdout or "").strip().splitlines()[-1] if out.stdout else ""
        if out.returncode != 0 or not ver or "Error" in ver:
            return False, rs, "R 已找到但未安装 igraph 包", rver, src
        return True, rs, ver, rver, src
    except Exception as e:  # noqa: BLE001
        return False, rs, f"调用失败: {str(e)[:60]}", rver, src


def install_igraph(rscript: str) -> bool:
    """经 --install 授权后，把 igraph 装到用户库。

    装到用户库（R_LIBS_USER）而非 R 安装目录：后者在 Windows 上通常需管理员
    权限、会直接失败；用户库无需提权，且默认已在 .libPaths() 中。
    """
    print("[install] 正在安装 R 包 igraph（用户库）…", file=sys.stderr)
    expr = (
        'dir.create(Sys.getenv("R_LIBS_USER"), recursive=TRUE, showWarnings=FALSE); '
        'install.packages("igraph", lib=Sys.getenv("R_LIBS_USER"), '
        'repos="https://mirrors.tuna.tsinghua.edu.cn/CRAN/")'
    )
    try:
        r = subprocess.run([rscript, "-e", expr],
                           capture_output=True, text=True, timeout=900)
    except Exception as e:  # noqa: BLE001
        print(f"[install] 调用 Rscript 失败: {e}", file=sys.stderr)
        return False
    if r.returncode != 0:
        tail = (r.stderr or r.stdout or "").strip().splitlines()[-6:]
        for line in tail:
            print("   " + line, file=sys.stderr)
        return False
    print("[install] igraph 安装完成，请重新运行 doctor.py 确认", file=sys.stderr)
    return True


def do_install(names):
    """经用户授权后安装缺失的必需依赖。返回是否全部成功。"""
    if not names:
        return True
    pkgs = {"sklearn": "scikit-learn"}
    target = [pkgs.get(n, n) for n in names]
    print(f"[install] 正在安装: {' '.join(target)}", file=sys.stderr)
    try:
        r = subprocess.run(
            [sys.executable, "-m", "pip", "install", *target],
            capture_output=True, text=True, timeout=900)
    except Exception as e:  # noqa: BLE001
        print(f"[install] 调用 pip 失败: {e}", file=sys.stderr)
        return False
    if r.returncode != 0:
        print(f"[install] pip 返回 {r.returncode}", file=sys.stderr)
        tail = (r.stderr or r.stdout or "").strip().splitlines()[-6:]
        for line in tail:
            print("   " + line, file=sys.stderr)
        return False
    print("[install] 安装完成，请重新运行 doctor.py 确认", file=sys.stderr)
    return True


def install_hint() -> str:
    return (FIX_HINT.get("jieba", "")
            + "  （若 jieba 报 OSError，请按 README「故障排查」手动解包安装）")


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="环境自检 / 依赖引导")
    ap.add_argument("--install", action="store_true",
                    help="经授权后自动安装缺失的必需依赖（pip）")
    ap.add_argument("--check-r", action="store_true",
                    help="[已废弃] R + igraph 现为必需前置条件，始终检测；"
                         "此开关仅为兼容旧命令而保留")
    a = ap.parse_args()

    print("=" * 56, file=sys.stderr)
    print("文献计量分析 · 环境自检", file=sys.stderr)
    print("=" * 56, file=sys.stderr)
    print(f"\n当前解释器: {sys.executable}", file=sys.stderr)
    print(f"Python 版本: {sys.version.split()[0]}", file=sys.stderr)
    print(f"脚本位置  : {Path(__file__).resolve().parent}", file=sys.stderr)

    problems: list[str] = []

    if sys.version_info[:2] < MIN_PY:
        problems.append(
            f"Python 版本过低：{sys.version.split()[0]} < "
            f"{MIN_PY[0]}.{MIN_PY[1]}")

    print("\n[必需依赖]", file=sys.stderr)
    for name, spec in REQUIRED:
        ok, ver, err = probe(name)
        mark = "✓" if ok else "✗"
        line = f"  {mark} {name:12s} {ver or '缺失'}"
        if not ok:
            line += f"  ({err})"
            problems.append(f"{name} 缺失或不可导入")
        print(line + f"   要求 {spec}", file=sys.stderr)

    print("\n[可选依赖]", file=sys.stderr)
    for name, note in OPTIONAL:
        ok, ver, _ = probe(name)
        mark = "✓" if ok else "—"
        print(f"  {mark} {name:12s} {ver or '未安装'}   {note}", file=sys.stderr)

    # 解释器歧义提示 —— 同机多个同版本 Python 可能依赖不同
    if sys.version_info[:2] >= (3, 13):
        print(
            "\n[提示] 本机可能存在多个 Python 3.13 环境，依赖不同。\n"
            "      若上面某项显示「缺失」但你确信装过，请改用包完整的解释器：\n"
            "        <该环境>/bin/python scan_library.py ...",
            file=sys.stderr,
        )

    # ── 必需前置条件：R + igraph（标准路径，缺失即环境不满足）──
    r_ok, r_path, r_detail, r_version, r_src = probe_r()
    print("\n[必需前置条件] R + igraph（计量分析标准路径）", file=sys.stderr)
    print(f"  {'✓' if r_ok else '✗'} Rscript: {r_path or '未找到'}"
          + (f"    {r_version}" if r_version else ""), file=sys.stderr)
    if r_path and r_src == "glob":
        # 「装好了但没在 PATH」是 Windows 的常见坑，单独点明 ——
        # 否则用户会以为工具没找到 R，跑去重装。
        print("      [注意] R 已安装但未写进 PATH（Windows 版 R 的默认行为）；"
              "已按常见安装目录找到。\n"
              "             建议把该 bin 目录加入 PATH，避免其它 R 工具找不到。",
              file=sys.stderr)
    print(f"  {'✓' if r_ok else '✗'} igraph : {r_detail}", file=sys.stderr)
    if not r_ok:
        problems.append(f"R/igraph 不可用：{r_detail}")

    # ── 依赖引导：经授权后自动安装 ──
    if a.install:
        if problems:
            missing = [n for n, _ in REQUIRED if not probe(n)[0]]
            if missing:
                print(f"\n[install] 缺失: {', '.join(missing)}", file=sys.stderr)
                print(f"        {install_hint()}", file=sys.stderr)
                do_install(missing)
        # R 缺失时：能自动装的（R 在但缺 igraph）就装；R 本身没装只能给指引。
        if not r_ok:
            if r_path and r_src != "":
                install_igraph(r_path)
            else:
                print("\n[install] 未找到 Rscript，无法自动安装 igraph。"
                      "请先安装 R，再重跑 doctor.py --install。", file=sys.stderr)

    if problems:
        print(f"\n[结论] 环境不满足，共{len(problems)} 项问题：", file=sys.stderr)
        for p in problems:
            print(f"  · {p}", file=sys.stderr)
        print("\n[修复建议]", file=sys.stderr)
        _hinted = False
        for name, _ in REQUIRED:
            if any(name in p for p in problems) and name in FIX_HINT:
                print(f"  {name}: {FIX_HINT[name]}", file=sys.stderr)
                _hinted = True
        # 兜底：新增依赖时若忘了写 FIX_HINT，上面的循环会一条都不打印，
        # 用户只看到「[修复建议]」这个空标题 —— 比不给建议更糟（像是没有问题）。
        if not _hinted and not r_ok:
            print("  R + igraph: 见下方安装指引", file=sys.stderr)
            _hinted = True
        if not _hinted:
            print("  请按 requirements.txt 安装依赖："
                  "pip install -r requirements.txt", file=sys.stderr)
        if not r_ok:
            print("\n  R + igraph（必需前置条件）：", file=sys.stderr)
            print("    " + R_INSTALL_GUIDE.replace("\n", "\n    "), file=sys.stderr)
        print(
            "\n  若你不确定该用哪个解释器，可查找可用环境：\n"
            "    ls -d /path/to/*/bin/python3  && 逐个运行 doctor.py",
            file=sys.stderr,
        )
        # [hint] 是 Agent 唯一会读的单行摘要，必须与**本次真实病因**相符。
        # EXIT[8] 的默认文案是「改用 Python 3.11+」，那是缺 numpy 时的病因；
        # 若 exit 8 是因为缺 R / 缺 igraph 而发，直接复用会把 Agent 引向
        # 完全无关的方向（改 Python 版本解决不了缺 R）。故按实际病因分文案。
        if not r_ok:
            _why = ("R + igraph 是计量分析的标准路径，当前不可用："
                    "请安装 R 并执行 install.packages('igraph') 后重跑"
                    "（完整步骤见上方 R + igraph 段）")
        else:
            _why = EXIT[8]
        print(f"[hint] {_why}", file=sys.stderr)
        return 8

    print("\n[结论] 环境就绪（含 R + igraph 标准路径），"
          "可以运行 scan_library.py / cluster_topics.py / sna_r.py",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
