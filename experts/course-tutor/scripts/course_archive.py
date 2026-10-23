#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""课程归档 · 学期结束一键打包（材料 + 学情 + 分析结果）。

解决的问题
----------
教师每学期结束要做三件事，本脚本把它们合成**一次命令**：
  1. 课程关闭：把该课`course_versions` 状态改为 `closed`（可选，见 --close-course）
  2. 材料一键下载：把课程材料（config / knowledge_hub / testset / quiz_bank）按课程打包
  3. 数据分析结果导出：把学情聚合、积分排行榜、周报一并放进同一个 zip

与既有 `backup_data_hub.py` 的分工：
- `backup_data_hub.py`：把 8 张子表**原样**归档（JSON+CSV），用于**回装**（防误删）
- 本脚本 `course_archive.py`：按**课程**维度打包（材料 + 学情 + 分析结果 + 清单），
  用于**学期归档 / 留档 / 交接 / 分析**

用法
----
  # 1) 先由 SKILL 经数据通道把该课材料与学情导出到 --src 目录，命名约定：
  #      materials__<course_id>/**      课程材料（任意嵌套）
  #      <course_id>__<子表>.json       学情/名册等子表（与 backup_data_hub.py 同约定）
  #      analysis__<course_id>__*.json  分析结果（积分榜/看板数据/周报，可选）
  # 2) 执行打包：
  python3 "${CODEBUDDY_PLUGIN_ROOT}/scripts/course_archive.py" --course <课程名> --course-id <course_id> --src <目录> \
      [--out <输出目录>] [--close-course] [--close-note<说明>]

  # 3) 只看包里有什么（不打包）：
  python3 "${CODEBUDDY_PLUGIN_ROOT}/scripts/course_archive.py" --course X --course-id Y --src <目录> --dry-run

退出码：0 成功 / 1 校验失败 / 2 用法错误
"""

import argparse
import csv
import json
import os
import shutil
import sys
import zipfile
from datetime import datetime

ARCHIVE_ROOT = os.path.join(os.path.expanduser("~"), ".workbuddy", "course-tutor", "archives")
SKIP_NAMES = {".DS_Store", "Thumbs.db", "desktop.ini", "__MACOSX", "__pycache__"}
SKIP_EXT = (".pyc", ".pyo")


def _harden_console():
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(errors="replace")
        except (AttributeError, ValueError, OSError):
            pass


_harden_console()


def _emit(prefix, msg):
    tag = {"OK": "[OK]", "FAIL": "[FAIL]", "!": "[!]"}.get(prefix, "[%s]" % prefix)
    sys.stdout.write("%s %s\n" % (tag, msg))


def load_json(path):
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def safe_name(s, fallback="course"):
    bad = '<>:"/\\|?*\r\n\t'
    out = "".join("_" if ch in bad else ch for ch in str(s)).strip().strip(".")
    return out or fallback


def collect_materials(src, course_id):
    """收集课程材料：优先 materials__<course_id>/ ，否则取 src 下任意 materials__* 目录。"""
    cands = []
    exact = os.path.join(src, "materials__%s" % course_id)
    if os.path.isdir(exact):
        cands.append(exact)
    else:
        for name in sorted(os.listdir(src)):
            if name.startswith("materials__") and os.path.isdir(os.path.join(src, name)):
                cands.append(os.path.join(src, name))
    files = []
    for d in cands:
        for dp, dns, fns in os.walk(d):
            dns[:] = [x for x in dns if x not in SKIP_NAMES]
            for fn in sorted(fns):
                if fn in SKIP_NAMES or fn.endswith(SKIP_EXT):
                    continue
                fp = os.path.join(dp, fn)
                rel = os.path.relpath(fp, d).replace(os.sep, "/")
                files.append((fp, rel))
    return files


def collect_tables(src, course_id):
    """收集 <course_id>__<子表>.json 及其他 course_id 前缀的子表文件。"""
    files = []
    pref = "%s__" % course_id
    for name in sorted(os.listdir(src)):
        if not name.endswith(".json"):
            continue
        fp = os.path.join(src, name)
        if not os.path.isfile(fp):
            continue
        if name.startswith(pref) or name.startswith("analysis__" + course_id):
            files.append((fp, name))
    return files


def _rows_of(path):
    """尽力取记录数组：兼容 [..] / {"records":[..]} / {"data":{"records":[..]}}。"""
    try:
        d = load_json(path)
    except (OSError, ValueError):
        return None
    if isinstance(d, list):
        return d
    if isinstance(d, dict):
        for key in ("records", "rows", "data", "items"):
            v = d.get(key)
            if isinstance(v, list):
                return v
            if isinstance(v, dict) and isinstance(v.get("records"), list):
                return v["records"]
    return None


def build_manifest(course_name, course_id, materials, tables, analyses, close_course, note):
    mat_entries = [{"path": rel, "size": os.path.getsize(fp)} for fp, rel in materials]
    tab_entries = []
    for fp, rel in tables:
        rows = _rows_of(fp)
        tab_entries.append({
            "file": rel,
            "size": os.path.getsize(fp),
            "rows": len(rows) if isinstance(rows, list) else None,
        })
    ana_entries = [{"file": rel, "size": os.path.getsize(fp)} for fp, rel in analyses]
    return {
        "type": "course-archive",
        "schema": 1,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "course": {"name": course_name, "course_id": course_id},
        "closed": bool(close_course),
        "close_note": note or "",
        "counts": {
            "materials": len(mat_entries),
            "tables": len(tab_entries),
            "tables_rows": sum(e["rows"] or 0 for e in tab_entries),
            "analyses": len(ana_entries),
        },
        "materials": mat_entries,
        "tables": tab_entries,
        "analyses": ana_entries,
        "_note": "本归档含课程材料与学情数据；定位 ID 不进包（见§1.3 保密铁律）。",
    }


def tables_to_csv(path, out_csv):
    rows = _rows_of(path)
    if not isinstance(rows, list) or not rows:
        return 0
    keys = []
    for r in rows:
        if isinstance(r, dict):
            for k in r.keys():
                if k not in keys:
                    keys.append(k)
    if not keys:
        return 0
    with open(out_csv, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            if isinstance(r, dict):
                w.writerow(r)
    return len(rows)


def main():
    ap = argparse.ArgumentParser(description="课程归档 · 学期结束按课程一键打包")
    ap.add_argument("--course", required=True, help="课程名")
    ap.add_argument("--course-id", required=True, help="课程 ID（与 course_versions / 名册一致）")
    ap.add_argument("--src", required=True, help="SKILL 导出的源目录")
    ap.add_argument("--out", default=ARCHIVE_ROOT, help="归档根目录")
    ap.add_argument("--close-course", action="store_true", help="打包后把 course_versions 状态置closed（需连接器写回，本脚本仅产出待写回清单）")
    ap.add_argument("--close-note", default="", help="结课说明（写入清单，便于日后追溯）")
    ap.add_argument("--dry-run", action="store_true", help="只打印将打包内容，不落盘")
    args = ap.parse_args()

    if not os.path.isdir(args.src):
        _emit("FAIL", "源目录不存在：%s" % args.src)
        return 2
    cid = args.course_id.strip()
    if not cid:
        _emit("FAIL", "course-id 为空")
        return 2

    materials = collect_materials(args.src, cid)
    tables = collect_tables(args.src, cid)
    analyses = [(fp, rel) for fp, rel in tables if rel.startswith("analysis__")]
    plain_tables = [(fp, rel) for fp, rel in tables if not rel.startswith("analysis__")]

    _emit("!", "材料 %d 个· 子表 %d 张 · 分析结果 %d 个" % (len(materials), len(plain_tables), len(analyses)))
    if not materials and not plain_tables:
        _emit("FAIL", "源目录里既没有材料也没有 <course_id>__<子表>.json —— 请确认 SKILL 是否已导出")
        return 1
    if not materials:
        _emit("!", "未找到课程材料（materials__%s/）—— 若该课材料已上云，可只归档学情与分析结果" % cid)
    if not plain_tables:
        _emit("!", "未找到 <course_id>__<子表>.json —— 学情数据将缺失，请确认 SKILL 是否已导出")

    if args.dry_run:
        _emit("OK", "[dry-run] 将打包：")
        for fp, rel in materials:
            _emit("", "材料  %s (%d B)" % (rel, os.path.getsize(fp)))
        for fp, rel in plain_tables:
            r = _rows_of(fp)
            _emit("", "子表  %s (%d 行)" % (rel, len(r) if isinstance(r, list) else -1))
        for fp, rel in analyses:
            _emit("", "分析  %s" % rel)
        _emit("OK", "[dry-run] 结束，未落盘")
        return 0

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    base = "%s__%s__%s" % (safe_name(args.course), safe_name(cid), ts)
    dest_dir = os.path.join(args.out, base)
    os.makedirs(dest_dir, exist_ok=True)

    # 1) 材料
    mat_dir = os.path.join(dest_dir, "materials")
    os.makedirs(mat_dir, exist_ok=True)
    for fp, rel in materials:
        dst = os.path.join(mat_dir, rel.replace("/", os.sep))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(fp, dst)

    # 2) 子表（原样 json + 便于查看的 csv）
    tab_dir = os.path.join(dest_dir, "tables")
    os.makedirs(tab_dir, exist_ok=True)
    for fp, rel in plain_tables:
        shutil.copyfile(fp, os.path.join(tab_dir, os.path.basename(rel)))
        tables_to_csv(fp, os.path.join(tab_dir, os.path.basename(rel).replace(".json", ".csv")))

    # 3) 分析结果（若有）
    ana_dir = os.path.join(dest_dir, "analysis")
    if analyses:
        os.makedirs(ana_dir, exist_ok=True)
        for fp, rel in analyses:
            shutil.copyfile(fp, os.path.join(ana_dir, os.path.basename(rel).replace("analysis__%s__" % cid, "")))

    # 4) 清单
    manifest = build_manifest(args.course, cid, materials, plain_tables, analyses,
                             args.close_course, args.close_note)
    mpath = os.path.join(dest_dir, "manifest.json")
    with open(mpath, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    # 5) 待写回的结课动作（脚本不碰云端，交由 SKILL 经连接器执行）
    if args.close_course:
        with open(os.path.join(dest_dir, "pending_close.json"), "w", encoding="utf-8") as f:
            json.dump({
                "action": "close_course",
                "table": "course_versions",
                "match": {"课程": args.course, "course_id": cid},
                "set": {"状态": "closed"},
                "note": "由 course_archive.py --close-course 产出；请由主理人经连接器确认后写回。",
            }, f, ensure_ascii=False, indent=2)
        _emit("!", "已产出 pending_close.json（结课状态写回需主理人经连接器执行并向教师确认）")

    # 6) 打包为 zip（课程维度）——须在所有文件（含 pending_close.json）落盘之后
    zip_path = os.path.join(args.out, base + ".zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for dp, dns, fns in os.walk(dest_dir):
            dns[:] = [d for d in dns if d not in SKIP_NAMES]
            for fn in sorted(fns):
                fp = os.path.join(dp, fn)
                arc = os.path.join(base, os.path.relpath(fp, dest_dir)).replace(os.sep, "/")
                zf.write(fp, arc)

    _emit("OK", "归档目录：%s" % dest_dir)
    _emit("OK", "归档 zip：%s（%.1f KB）" % (zip_path, os.path.getsize(zip_path) / 1024.0))
    _emit("OK", "清单：材料 %d · 子表 %d（%d 行） · 分析 %d"
         % (manifest["counts"]["materials"], manifest["counts"]["tables"],
            manifest["counts"]["tables_rows"], manifest["counts"]["analyses"]))
    # 自动埋点（）：调用即记录，失败不影响功能
    try:
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        import course_usage_log
        course_usage_log.auto_record("结课归档", args.course, os.path.basename(zip_path))
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
