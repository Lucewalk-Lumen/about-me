#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sync_standards.py — Open WorkBuddy 开发标准「随标准变动自动保持最新」机制

设计目标：
  将 https://open.workbuddy.cn/docs 的最新开发标准嵌入系统，并在标准变动时
  自动检测漂移、备份旧快照、生成 diff，提示主理人复核。不自动覆盖生产规则
  （避免「修扫描器而非内容」的反模式）。

两种运行模式：
  check   只读漂移检测（默认）。抓取线上文档，与本快照做哈希 + 关键标记比对，
          输出 PASS / DRIFT 报告。不写任何文件。
  update  在 check 发现 DRIFT 且用户提供 --apply 后：备份旧快照到
          knowledge/_archive/，把渲染后的新内容写入快照（best-effort），刷新 manifest。

关于 SPA：
  open.workbuddy.cn/docs 是单页应用，静态 urllib GET 常常只拿到外壳。可靠做法是
  用 browser-skill 渲染页面并把完整 HTML 另存为文件，再用 --html <file> 入参
  传给本脚本做比对。**本脚本默认不联网**；联网抓取需显式 `--online`（SPA 下通常只得外壳，
  此时判为 INCONCLUSIVE 而非 DRIFT）。

退出码：0 = 一致（PASS）；1 = WARN（DRIFT 或 INCONCLUSIVE，均需人工复核；与 verify.py/gates.py 的 WARN=1 语义一致）；2 = 入参/用法错误（--html 超限、update 未加 --sandbox-copy）。

零第三方依赖：仅用标准库 urllib / hashlib / json / re / html.parser / datetime。
"""
import argparse
import os, sys, json, hashlib, re, datetime, urllib.request, urllib.error
from html.parser import HTMLParser

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                       # workbuddy-expert-studio/
KNOWLEDGE = os.path.join(ROOT, "knowledge")
SNAPSHOT = os.path.join(KNOWLEDGE, "workbuddy-expert-studio-standards.md")
MANIFEST = os.path.join(KNOWLEDGE, "standards-manifest.json")
DOCS_URL = "https://open.workbuddy.cn/docs"
# --html 单文件上限（bytes）：防超大/畸形输入拖垮脚本（C1；风格参照 crawler 的 from_file_max_bytes）
HTML_MAX_BYTES = 8 * 1024 * 1024        # 8 MB


def cjk_len(s):
    return sum(1 for c in s if "\u4e00" <= c <= "\u9fff")


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


class _VisibleTextStripper(HTMLParser):
    """线性时间抽取可见文本：丢弃 script/style，实体解码后折叠空白。

    C1 修复：旧实现用 `re.sub(r"<[^>]+>", ...)`，当输入含大量 `<` 且其后无 `>`
    时回溯呈 O(n²)（20 万个 `<` 实测 ~11s，2MB 输入近 20 分钟）。改用标准库
    HTMLParser 逐标签解析，复杂度 O(n)，且语义与旧实现等价（去脚本/样式、
    实体反转义、空白折叠）。
    """

    _SKIP = ("script", "style")

    def __init__(self):
        super().__init__(convert_charrefs=True)   # convert_charrefs=True => 自动实体解码
        self._skip = 0
        self._buf = []

    def handle_starttag(self, tag, attrs):
        if tag in self._SKIP:
            self._skip += 1

    def handle_startendtag(self, tag, attrs):
        # 自闭合 <script/> <style/> 不产生 handle_endtag，这里不改变 _skip
        pass

    def handle_endtag(self, tag):
        if tag in self._SKIP and self._skip > 0:
            self._skip -= 1

    def handle_data(self, data):
        if self._skip == 0:
            self._buf.append(data)

    def text(self):
        return re.sub(r"\s+", " ", " ".join(self._buf)).strip()


def strip_html(raw: str) -> str:
    """去标签保留可见文本（供标记比对）。零回溯风险的线性实现（见 _VisibleTextStripper）。"""
    p = _VisibleTextStripper()
    try:
        p.feed(raw)
        p.close()
        return p.text()
    except Exception:
        # HTMLParser 极少抛错；兜底用**非回溯**写法（[^<>]* 不含嵌套回溯），仍保持 O(n)
        return re.sub(r"\s+", " ", re.sub(r"<[^<>]*>", " ", raw)).strip()


def fetch_docs(url=DOCS_URL, timeout=20):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (sync-standards)"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode("utf-8", "ignore")
        return raw, None
    except Exception as e:  # 网络/SPA 限制都归为不可达
        return None, str(e)


def extract_text_from_html_file(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return strip_html(f.read())


def detect_markers(text: str):
    """从可见文本抽取关键合规标记，与 manifest.baseline_markers 比对。"""
    markers = {}
    # 1) displayDescription 40-50 字规则是否仍在
    markers["displayDescription_40_50_rule"] = ("40-50" in text) or ("40 — 50" in text) or ("40–50" in text)
    # 2) tags / quickPrompts 固定 3 个
    markers["tags_fixed_3"] = bool(re.search(r"固定\s*3\s*个", text))
    # 3) defaultInitPrompt == quickPrompts[0]
    markers["defaultInitPrompt_eq_qp0"] = ("defaultInitPrompt" in text and "quickPrompts" in text
                                           and ("保持一致" in text))
    # 4) categoryId 枚举数量（取完整枚举名 NN-Name，与 manifest.baseline_markers 全名口径一致）
    enum_ids = sorted(set(m.group(0) for m in re.finditer(r"\b(0[1-9]|1[0-5])-[A-Za-z]+\b", text)))
    markers["categoryId_enum_count"] = len(enum_ids)
    markers["categoryId_enum"] = enum_ids
    # 5) expertType team / agent
    markers["expertType_team"] = ('"team"' in text) or ("填\"team\"" in text)
    markers["expertType_agent"] = ('"agent"' in text) or ("填\"agent\"" in text)
    return markers


def load_manifest():
    with open(MANIFEST, encoding="utf-8") as f:
        return json.load(f)


MARKER_KEYS = ("displayDescription_40_50_rule", "tags_fixed_3", "defaultInitPrompt_eq_qp0",
               "expertType_team", "expertType_agent")


def build_parser():
    ap = argparse.ArgumentParser(
        prog="sync_standards.py",
        description="Open WorkBuddy 开发标准漂移检测（默认不联网；对比 knowledge/ 快照，发现漂移提示复核）。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=("示例：\n"
                "  python3 scripts/sync_standards.py check\n"
                "  python3 scripts/sync_standards.py check --html=rendered.html   # 或 --html rendered.html\n"
                "  python3 scripts/sync_standards.py check --online               # 显式联网（SPA 可能只得外壳）\n"
                "  python3 scripts/sync_standards.py update --html=rendered.html --apply --sandbox-copy\n"))
    ap.add_argument("mode", nargs="?", choices=["check", "update"], default="check",
                    help="check=只读漂移检测（默认）；update=复核后更新")
    ap.add_argument("--html", default=None, metavar="FILE",
                    help="渲染后的 HTML 文件（--html=<f> 与 --html <f> 均可）")
    ap.add_argument("--online", action="store_true",
                    help="允许联网抓取（默认不联网；SPA 下通常只得外壳）")
    ap.add_argument("--apply", action="store_true", help="update 模式下真正写盘")
    ap.add_argument("--sandbox-copy", action="store_true",
                    help="确认已在沙箱副本运行（update 前置要求）")
    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)
    mode = args.mode
    html_arg = args.html
    apply = args.apply

    manifest = load_manifest()
    baseline = manifest.get("baseline_markers", {})
    snap_hash = sha256_of(SNAPSHOT) if os.path.exists(SNAPSHOT) else None

    print(f"[sync_standards] mode={mode} source={DOCS_URL}")
    print(f"[sync_standards] snapshot={os.path.relpath(SNAPSHOT, ROOT)} sha256={snap_hash[:12] if snap_hash else 'MISSING'}")

    # 获取线上文本：优先用渲染后的 HTML 文件；否则仅在显式 --online 时才联网尽力 GET。
    live_text = None
    src_note = ""
    if html_arg and os.path.exists(html_arg):
        # C1：--html 单文件大小上限，超限直接失败（防超大/畸形输入拖垮脚本）
        try:
            _sz = os.path.getsize(html_arg)
        except OSError as e:
            print(f"[sync_standards] [FAIL] 无法读取 --html 文件属性: {e}")
            return 2
        if _sz > HTML_MAX_BYTES:
            print(f"[sync_standards] [FAIL] --html 文件体积 {_sz}B 超过上限 {HTML_MAX_BYTES}B，拒绝处理（html_too_large）。")
            return 2
        live_text = extract_text_from_html_file(html_arg)
        src_note = f"rendered-html:{html_arg}"
    elif html_arg:
        src_note = f"html-not-found:{html_arg}"
    elif args.online:
        raw, err = fetch_docs()
        if raw:
            live_text = strip_html(raw)
            src_note = f"urllib-get:{DOCS_URL}"
        else:
            src_note = f"UNREACHABLE:{err}"
    else:
        src_note = "skipped:offline(默认不联网；如需抓取请显式 --online 或提供 --html=<file>)"

    report = {
        "checked_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "source": src_note,
        "snapshot_sha256": snap_hash,
        "drift": False,
        "conclusion": "INCONCLUSIVE",
        "marker_diff": [],
        "notes": [],
    }

    if live_text is None:
        report["notes"].append("未取到线上/渲染内容，跳过标记比对（本脚本默认不联网）。请在启用 browser-skill 渲染后保存完整 HTML，再用 `--html=<file>` 传入；或显式 `--online` 做静态尽力抓取（SPA 可能仅得外壳）。")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        print("\n[sync_standards] [WARN] INCONCLUSIVE：未取到可比对内容，无法判定漂移（退出码 1，与 verify.py/gates.py 的 WARN=1 一致）。")
        return 1

    live_markers = detect_markers(live_text)
    # P1：5 个 live 关键标记全为 false → 判 INCONCLUSIVE（疑似 SPA 外壳），不报 DRIFT。
    if not any(live_markers.get(k) for k in MARKER_KEYS):
        report["conclusion"] = "INCONCLUSIVE"
        report["notes"].append("5 个 live 关键标记全为 false，疑似 SPA 外壳（未渲染的静态 HTML）。请用 `--html=<渲染后的 HTML>` 提供浏览器渲染结果后重跑；在拿到渲染内容前不据此判断标准漂移。")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        print("\n[sync_standards] [WARN] INCONCLUSIVE：未取到渲染后内容（疑似 SPA 外壳），不报 DRIFT。")
        return 1

    # 逐标记比对
    for k in MARKER_KEYS:
        exp = baseline.get(k)
        got = live_markers.get(k)
        if exp is not None and bool(exp) != bool(got):
            report["drift"] = True
            report["marker_diff"].append({"marker": k, "baseline": exp, "live": got})

    base_enum = set(baseline.get("categoryId_enum", []))
    live_enum = set(live_markers.get("categoryId_enum", []))
    if base_enum and live_enum and base_enum != live_enum:
        report["drift"] = True
        report["marker_diff"].append({
            "marker": "categoryId_enum",
            "added": sorted(live_enum - base_enum),
            "removed": sorted(base_enum - live_enum),
        })

    # 输出结论
    report["conclusion"] = "DRIFT" if report["drift"] else "PASS"
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["drift"]:
        print("\n[sync_standards] [WARN] 检测到标准漂移（DRIFT）。")
        print("  处理：备份旧快照 → 生成 diff → 主理人复核后更新生产规则。不自动覆盖。")
        if mode == "update" and apply:
            if not args.sandbox_copy:
                print("\n[sync_standards] [FAIL] update 需在沙箱副本运行：请加 `--sandbox-copy` 确认后重试。")
                return 2
            _do_update(SNAPSHOT, MANIFEST, live_text, report)
        else:
            print("  运行 `python3 scripts/sync_standards.py update --html=<渲染后 HTML> --apply --sandbox-copy` 以在复核后更新快照。")
        return 1
    else:
        print("\n[sync_standards] [OK] 与线上标准一致，无需更新。")
        return 0


def _do_update(snapshot, manifest_path, live_text, report):
    """在人工确认后：备份旧快照、刷新 manifest 的哈希与抓取时间。"""
    arc_dir = os.path.join(os.path.dirname(snapshot), "_archive")
    os.makedirs(arc_dir, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = os.path.join(arc_dir, f"workbuddy-expert-studio-standards.{ts}.md.bak")
    import shutil
    shutil.copy2(snapshot, backup)
    # 刷新 manifest 哈希（快照正文由主理人据 live_text 人工润色后写入，这里只更新元信息）
    with open(manifest_path, encoding="utf-8") as fh:
        m = json.load(fh)
    m["content_sha256"] = sha256_of(snapshot)
    m["captured_at"] = ts
    m["doc_version"] = ts[:10]
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(m, fh, ensure_ascii=False, indent=2)
    diff_path = os.path.join(os.path.dirname(snapshot), f"STANDARDS-DIFF-{ts[:8]}.md")
    with open(diff_path, "w", encoding="utf-8") as f:
        f.write(f"# 标准漂移 Diff ({ts})\n\n")
        f.write("```json\n" + json.dumps(report["marker_diff"], ensure_ascii=False, indent=2) + "\n```\n")
    print(f"  已备份旧快照：{backup}")
    print(f"  已生成 diff：{diff_path}")
    print(f"  已刷新 manifest 哈希。快照正文请主理人据渲染内容人工润色后落盘。")


if __name__ == "__main__":
    sys.exit(main())
