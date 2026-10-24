#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""课程伴学 · 整库数据导出备份与回装规划器（backup_data_hub.py）

教师端「整库数据导出备份」的本地归档与回装规划器。

数据读取由主理人（agent）经腾讯文档连接器完成——本脚本**不直接持有任何凭据**，
也不调用连接器。流程分工：

1. 主理人用 `smartsheet.list_records` 把每门课的子表读出（子表清单以 `data_hub_config.json` 的 `courses.<course_id>.hub_sheets` / `.usage_sheet` 为准）：
   Hub 文件 3 张：roster / course_versions / agent_profiles
   Usage 文件 2 张：usage / summaries
   每张落为一个 `<课程>__<子表>.json`（记录数组，原样保留连接器返回结构）。
2. 主理人调用本脚本 `assemble`，把上述 json 归档成带清单 / CSV / 配置快照的
   时间戳备份目录，并打印摘要。
3. （可选回装）`restore --plan <备份目录>` 读备份产出 smartsheet 回装载荷（JSON），
   由主理人向教师确认后经连接器写回——回装是非幂等的，必须先确认。

子命令
------
  assemble  把若干 `<课程>__<子表>.json` 归档成时间戳备份
  list      列出已存在的备份（含每备份的表数 / 行数 / 时间）
  restore   读备份产出回装载荷（仅规划，不执行；执行由主理人经连接器完成）

退出码：0 成功 / 1 校验失败 / 2 用法错误
"""

import argparse
import csv
import json
import os
import shutil
import sys
from datetime import datetime, timezone

SCRIPT_NAME = "backup_data_hub.py"
DEFAULT_BACKUP_ROOT = os.path.join(
    os.path.expanduser("~"), ".workbuddy", "course-tutor", "backups"
)

# 一张记录可能的两种形态：扁平 {列: 值} 或 {record_id, fields: {列: 值}}
RESERVED_NAMES = {"index.json", "manifest.json", "data_hub_config.snapshot.json"}


def _emit(tag, msg):
    print("[%s] %s" % (tag, msg))


def _is_reserved(name):
    base = os.path.basename(name)
    return base in RESERVED_NAMES or base.startswith("manifest")


def _split_course_sheet(filename):
    """<课程>__<子表>.json → (课程, 子表)。取最后一个 '__' 之前为课程、之后为子表。

    课程 id 在本包约定里使用连字符（如 sample-course），不用下划线，故以 '__' 切分安全。
    """
    base = os.path.basename(filename)
    if not base.endswith(".json"):
        return None, None
    stem = base[:-len(".json")]
    if "__" not in stem:
        return None, None
    course, _, sheet = stem.rpartition("__")
    return course, sheet


def _flatten(record):
    """把一条记录归一成 {列: 值} 的扁平 dict。"""
    if isinstance(record, dict):
        if isinstance(record.get("fields"), dict):
            return record["fields"]
        return {k: v for k, v in record.items() if k != "record_id"}
    return {}


def _records_of(payload):
    """从 <课程>__<子表>.json 里取出记录数组（兼容 直接数组 / {records: [...]} / {data: [...]}）。"""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("records", "data", "rows", "items"):
            if isinstance(payload.get(key), list):
                return payload[key]
    return []


def cmd_assemble(args):
    src = os.path.abspath(args.src)
    if not os.path.isdir(src):
        _emit("FAIL", "源目录不存在：%s" % src)
        return 1
    backup_root = os.path.abspath(args.dest)
    os.makedirs(backup_root, exist_ok=True)

    # 收集待归档的表文件
    table_files = []
    for name in sorted(os.listdir(src)):
        if not name.endswith(".json") or _is_reserved(name):
            continue
        course, sheet = _split_course_sheet(name)
        if not course or not sheet:
            _emit("!", "跳过无法识别的文件（需 <课程>__<子表>.json）：%s" % name)
            continue
        table_files.append((name, course, sheet))

    if not table_files:
        _emit("FAIL", "源目录里没有任何 <课程>__<子表>.json，未执行备份。")
        return 1

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if args.label:
        run_id = "%s_%s" % (run_id, args.label)
    archive = os.path.join(backup_root, run_id)
    os.makedirs(archive, exist_ok=True)

    manifest_tables = []
    total_rows = 0
    for name, course, sheet in table_files:
        try:
            with open(os.path.join(src, name), encoding="utf-8-sig") as fh:
                payload = json.load(fh)
        except (OSError, ValueError) as exc:
            _emit("!", "读失败，跳过：%s（%s）" % (name, exc))
            continue
        records = _records_of(payload)
        course_dir = os.path.join(archive, course)
        os.makedirs(course_dir, exist_ok=True)
        # 1) 原样保留 json
        shutil.copyfile(os.path.join(src, name), os.path.join(course_dir, sheet + ".json"))
        # 2) 额外写一份 CSV（便于人读 / 表格软件打开）
        _write_csv(os.path.join(course_dir, sheet + ".csv"), records)
        manifest_tables.append({
            "course": course,
            "sheet": sheet,
            "rows": len(records),
            "bytes": os.path.getsize(os.path.join(course_dir, sheet + ".json")),
        })
        total_rows += len(records)
        _emit("OK", "已归档 %s / %s（%d 行）" % (course, sheet, len(records)))

    # 3) 配置快照（含各子表定位，便于回装映射）
    config_snapshot = None
    cfg_src = args.config
    if cfg_src and os.path.isfile(cfg_src):
        try:
            with open(cfg_src, encoding="utf-8-sig") as fh:
                config_snapshot = json.load(fh)
            shutil.copyfile(cfg_src, os.path.join(archive, "data_hub_config.snapshot.json"))
            _emit("OK", "已快照 data_hub_config.json（回装映射用）")
        except (OSError, ValueError) as exc:
            _emit("!", "配置快照读失败（不影响数据归档）：%s" % exc)

    manifest = {
        "generator": SCRIPT_NAME,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "run_id": run_id,
        "config_version": (config_snapshot or {}).get("version"),
        "tables": manifest_tables,
        "total_tables": len(manifest_tables),
        "total_rows": total_rows,
        "has_config_snapshot": config_snapshot is not None,
    }
    with open(os.path.join(archive, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    _emit("OK", "备份完成：%s" % archive)
    _emit("OK", "共 %d 张子表 / %d 行" % (manifest["total_tables"], total_rows))
    print("BACKUP_DIR=%s" % archive)
    return 0


def _write_csv(path, records):
    rows = [_flatten(r) for r in records]
    cols = []
    seen = set()
    for r in rows:
        for k in r.keys():
            if k not in seen:
                seen.add(k)
                cols.append(k)
    try:
        with open(path, "w", encoding="utf-8-sig", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols)
            w.writeheader()
            for r in rows:
                w.writerow({c: r.get(c, "") for c in cols})
    except (OSError, ValueError):
        # CSV 写出失败不应阻断备份主流程（json 已保留）
        _emit("!", "CSV 写出失败（json 仍保留）：%s" % path)


def cmd_list(args):
    backup_root = os.path.abspath(args.dest)
    if not os.path.isdir(backup_root):
        _emit("OK", "还没有任何备份目录：%s" % backup_root)
        return 0
    entries = sorted(
        (e for e in os.listdir(backup_root) if os.path.isdir(os.path.join(backup_root, e))),
        reverse=True,
    )
    if not entries:
        _emit("OK", "还没有任何备份。")
        return 0
    for e in entries:
        mpath = os.path.join(backup_root, e, "manifest.json")
        if os.path.isfile(mpath):
            try:
                m = json.load(open(mpath, encoding="utf-8-sig"))
                print("- %s | 表 %d / 行 %d | %s" % (
                    e, m.get("total_tables", 0), m.get("total_rows", 0), m.get("created_at", "")))
                continue
            except (OSError, ValueError):
                pass
        print("- %s （无清单）" % e)
    return 0


def cmd_restore(args):
    archive = os.path.abspath(args.archive)
    mpath = os.path.join(archive, "manifest.json")
    if not os.path.isfile(mpath):
        _emit("FAIL", "不是有效备份目录（缺 manifest.json）：%s" % archive)
        return 1
    manifest = json.load(open(mpath, encoding="utf-8-sig"))
    snap_path = os.path.join(archive, "data_hub_config.snapshot.json")
    config = None
    if os.path.isfile(snap_path):
        config = json.load(open(snap_path, encoding="utf-8-sig"))

    plan = {"archive": archive, "actions": []}
    # 用配置快照把 (课程, 子表) 映射到 (file_id, sheet_id)
    for t in manifest.get("tables", []):
        course, sheet = t["course"], t["sheet"]
        fid, sid = _resolve_target(config, course, sheet)
        if not fid or not sid:
            _emit("!", "无法定位回装目标（缺配置快照或子表未登记）：%s / %s —— 将跳过" % (course, sheet))
            continue
        plan["actions"].append({
            "course": course, "sheet": sheet,
            "file_id": fid, "sheet_id": sid,
            "source_json": os.path.join(archive, course, sheet + ".json"),
        })
    _emit("OK", "回装规划：%d 张子表（需主理人确认后经连接器写回）" % len(plan["actions"]))
    print(json.dumps(plan, ensure_ascii=False, indent=2))
    return 0


def _resolve_target(config, course, sheet):
    if not isinstance(config, dict):
        return None, None
    c = (config.get("courses") or {}).get(course)
    if not isinstance(c, dict):
        return None, None
    if sheet in ("usage", "summaries", "report"):
        node = c.get("usage_sheet") or {}
        return c.get("usage_file_id"), node.get(sheet)
    node = c.get("hub_sheets") or {}
    return c.get("hub_file_id"), node.get(sheet)


def main():
    ap = argparse.ArgumentParser(description="课程伴学 · 整库数据导出备份与回装规划器")
    sub = ap.add_subparsers(dest="cmd")

    pa = sub.add_parser("assemble", help="归档 <课程>__<子表>.json 为时间戳备份")
    pa.add_argument("--src", required=True, help="含 <课程>__<子表>.json 的源目录")
    pa.add_argument("--dest", default=DEFAULT_BACKUP_ROOT, help="备份根目录（默认 ~/.workbuddy/course-tutor/backups）")
    pa.add_argument("--config", default=None, help="data_hub_config.json 路径（写入快照，便于回装）")
    pa.add_argument("--label", default=None, help="备份目录附加标签")

    pl = sub.add_parser("list", help="列出已有备份")
    pl.add_argument("--dest", default=DEFAULT_BACKUP_ROOT, help="备份根目录")

    pr = sub.add_parser("restore", help="读备份产出回装载荷（仅规划）")
    pr.add_argument("--archive", required=True, help="备份目录（含 manifest.json）")

    args = ap.parse_args()
    if args.cmd == "assemble":
        return cmd_assemble(args)
    if args.cmd == "list":
        return cmd_list(args)
    if args.cmd == "restore":
        return cmd_restore(args)
    ap.print_usage()
    return 2


if __name__ == "__main__":
    sys.exit(main())
