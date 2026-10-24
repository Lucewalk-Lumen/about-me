#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""学生智能体 · 自动同步（客户端）。

职责：比对教师中枢文档里的「材料版本戳」与本地缓存，算出需要更新的文件清单，
并在 `--apply` 时把新文件落到本地包目录（只复制、绝不执行包内脚本）。

实际「从中枢文档取材料」由 主指令 经数据通道完成（本脚本不持有 smartsheet 调用）；
主指令 把取回的「材料清单 + 版本戳」写成 JSON 传给本脚本做**对账与落地**。

契约：
  sync_state.json（**包外**本地状态）：{"stamp": "<版本戳>", "manifest": {相对路径: 校验值}}
  传入的 materials JSON：             {"stamp": "<新版本戳>", "manifest": {相对路径: 校验值}}

状态存放位置：**必须在包外** `~/.workbuddy/course_tutor_student/sync_state.json`。
原因（实证）：放在包内时，学生端包更新会清空包目录，状态随之丢失，
导致「首次接入」被反复判定、真实版本变化被吞掉一次不播报。
包内若存在旧状态文件，本脚本会**自动迁移**到包外一次。

用法：
  python3 sync_assets.py --hub-doc <文档定位> --pkg-dir <本地包目录> --manifest <材料清单json>
  python3 sync_assets.py ... --apply --source-dir <取回材料目录>   # 落地更新
"""

import argparse
import json
import os
import shutil
import sys


def _harden_console():
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(errors="replace")
        except (AttributeError, ValueError, OSError):
            pass


_harden_console()


def load_json(path):
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def state_path(pkg_dir):
    """状态文件路径：一律在**包外**（包更新会清空包目录，状态放包内必丢——）。

    包内若存在旧状态文件（旧版本遗留），自动迁移到包外一次。
    """
    udir = os.path.join(os.path.expanduser("~"), ".workbuddy", "course_tutor_student")
    sp = os.path.join(udir, "sync_state.json")
    legacy = os.path.join(pkg_dir, "sync_state.json")
    if not os.path.exists(sp) and os.path.exists(legacy):
        try:
            os.makedirs(udir, exist_ok=True)
            shutil.copyfile(legacy, sp)
            print(f"[OK] 已把包内旧状态迁到包外（此后包更新不会丢）：{sp}")
        except OSError:
            pass
    return sp


def save_state(pkg_dir, manifest):
    """写状态（包外）。目录不存在时创建。"""
    sp = state_path(pkg_dir)
    os.makedirs(os.path.dirname(sp), exist_ok=True)
    with open(sp, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return sp


def reconcile(pkg_dir, manifest):
    sp = state_path(pkg_dir)
    old = load_json(sp) if os.path.exists(sp) else {"stamp": "", "manifest": {}}
    new_stamp = manifest.get("stamp", "")
    new_manifest = manifest.get("manifest", {})
    old_manifest = old.get("manifest", {})
    updates = []
    for rel, val in new_manifest.items():
        if old_manifest.get(rel) != val:
            updates.append(rel)
    removed = [rel for rel in old_manifest if rel not in new_manifest]
    return {
        "stamp_changed": old.get("stamp") != new_stamp,
        # ：基线 manifest 为空 = 还没建过基线，不是「材料有变化」
        "baseline_empty": not old_manifest and bool(new_manifest),
        "old_stamp": old.get("stamp"),
        "new_stamp": new_stamp,
        "to_update": updates,
        "to_remove": removed,
        "up_to_date": not updates and not removed and old.get("stamp") == new_stamp,
    }


def apply_sync(pkg_dir, manifest, source_dir):
    new_manifest = manifest.get("manifest", {})
    for rel in new_manifest:
        if not source_dir:
            continue
        src = os.path.join(source_dir, rel)
        dst = os.path.join(pkg_dir, rel)
        if os.path.exists(src):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(src, dst)
    # 写回状态（包外）
    save_state(pkg_dir, manifest)


def main():
    ap = argparse.ArgumentParser(description="学生智能体 · 自动同步对账")
    ap.add_argument("--hub-doc", required=True, help="中枢文档定位（仅记录，不下发）")
    ap.add_argument("--pkg-dir", required=True)
    ap.add_argument("--manifest", required=True, help="取回的材料清单 JSON")
    ap.add_argument("--apply", action="store_true", help="落地更新（复制文件）")
    ap.add_argument("--source-dir", default="", help="取回材料目录（--apply 时复制来源）")
    args = ap.parse_args()

    if not os.path.exists(args.manifest):
        print(f"[FAIL] 材料清单不存在：{args.manifest}")
        sys.exit(1)
    manifest = load_json(args.manifest)
    sp = state_path(args.pkg_dir)
    # 首次接入（包外无状态）→ **立即播种**当前版本戳，保证下一次真实变化能被检出
    # （注：不播种的话，每次都被当成首次接入，真实版本变化会一直被吞掉不播报）
    if not os.path.exists(sp):
        save_state(args.pkg_dir, manifest)
        print("[OK] 首次接入：已把当前版本戳写入包外状态（不播报历史版本），"
              "此后版本变化即可正常播报。")
        return
    res = reconcile(args.pkg_dir, manifest)

    print(f"[OK] 同步对账（中枢文档 {args.hub_doc}）")
    print(f"   旧版本戳：{res['old_stamp'] or '(无)'}")
    print(f"   新版本戳：{res['new_stamp']}")
    # 自动埋点（使用记录）：调用即记录，失败不影响功能
    try:
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        import course_usage_log
        course_usage_log.auto_record("云端同步", "", "apply" if args.apply else "对账")
    except Exception:
        pass
    if res["up_to_date"]:
        print("   已是最新，无需更新。")
        return
    if res.get("baseline_empty"):
        print("   本地还没有材料基线，本次为**首次建立基线**（不是材料有变化）。")
    print(f"   需更新 {len(res['to_update'])} 个文件：{res['to_update']}")
    if res["to_remove"]:
        print(f"   需移除 {len(res['to_remove'])} 个文件：{res['to_remove']}")
    if args.apply:
        apply_sync(args.pkg_dir, manifest, args.source_dir)
        print(f"[OK] 已落地更新到：{args.pkg_dir}（仅复制，未执行任何包内脚本）")


if __name__ == "__main__":
    main()
