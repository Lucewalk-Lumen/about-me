#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""使用说明记录（· 使用说明 / 上手引导的「及时、完整」落盘）。

职责：把教师每次触发的动作**逐条记录**到本地日志，并生成可复核的「功能使用说明书」。
定位 ID 等敏感信息**绝不写入**日志（只记功能名 / 时间 / 课程 / 参数轮廓，不记定位 ID）。

两条落点：
  1. 本地：~/.workbuddy/course-tutor/usage_log.md（跨会话留存，教师随时可查）；
  2. 云端（可选）：若教师已建 `usage_log` 子表，主指令 可把同一条记录再写回中枢（本脚本只产出记录对象，
     实际写表由 主指令 负责，避免脚本直接持有 smartsheet 调用）。

用法：
  python3 <本脚本路径> --action <功能名> [--course <课程>] [--detail <一句话>]
  python3 <本脚本路径> --report                    # 打印「功能使用说明书」摘要
  python3 <本脚本路径> --export-json               # 导出全部记录为 JSON（供 主指令 写回中枢）
"""

import argparse
import json
import os
import sys
from datetime import datetime


def _harden_console():
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(errors="replace")
        except (AttributeError, ValueError, OSError):
            pass


_harden_console()

LOG_DIR = os.path.join(os.path.expanduser("~"), ".workbuddy", "course-tutor")
LOG_FILE = os.path.join(LOG_DIR, "usage_log.md")


def _ensure_dir():
    os.makedirs(LOG_DIR, exist_ok=True)


def record(action, course, detail):
    _ensure_dir()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = {"ts": ts, "action": action, "course": course or "",
             "detail": detail or ""}
    line = f"- `{ts}` · **{action}**" + (f" · 课程：{course}" if course else "") \
           + (f" · {detail}" if detail else "") + "\n"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line)
    # 同步一份 JSON，便于机器读取 / 写回中枢
    jf = os.path.join(LOG_DIR, "usage_log.json")
    arr = []
    if os.path.exists(jf):
        try:
            arr = json.load(open(jf, encoding="utf-8"))
        except (OSError, ValueError):
            arr = []
    arr.append(entry)
    with open(jf, "w", encoding="utf-8") as f:
        json.dump(arr, f, ensure_ascii=False, indent=2)
    return entry


def report():
    if not os.path.exists(LOG_FILE):
        print("尚无使用记录。")
        return
    text = open(LOG_FILE, encoding="utf-8").read()
    # 统计各功能触发次数（用于「功能使用说明书」）
    from collections import Counter
    c = Counter()
    for ln in text.splitlines():
        if "**" in ln:
            try:
                act = ln.split("**")[1]
                c[act] += 1
            except IndexError:
                pass
    print("【功能使用说明书 · 触发统计】")
    for act, n in c.most_common():
        print(f"  - {act}: {n} 次")
    print(f"\n完整记录见：{LOG_FILE}")


def auto_record(action, course="", detail=""):
    """架构级自动埋点（的「必然触发」）。

    供各功能脚本在**成功运行后**调用：调用即记录，不依赖智能体「记得」。
    任何异常一律吞掉——记录失败**绝不影响**功能本身（记录是旁路，不是闸门）。
    """
    try:
        return record(action, course, detail)
    except Exception:
        return None


def load_recent(limit=10):
    """读取最近 limit 条记录（供脚本开场自检用；无记录返回空列表）。"""
    jf = os.path.join(LOG_DIR, "usage_log.json")
    try:
        arr = json.load(open(jf, encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return arr[-limit:] if limit else arr


def export_json():
    jf = os.path.join(LOG_DIR, "usage_log.json")
    if not os.path.exists(jf):
        print("[]")
        return
    sys.stdout.write(open(jf, encoding="utf-8").read())


def main():
    ap = argparse.ArgumentParser(description="使用说明记录")
    ap.add_argument("--action", default="")
    ap.add_argument("--course", default="")
    ap.add_argument("--detail", default="")
    ap.add_argument("--report", action="store_true", help="打印功能使用说明书摘要")
    ap.add_argument("--export-json", action="store_true", help="导出全部记录 JSON")
    args = ap.parse_args()

    if args.report:
        report()
        return
    if args.export_json:
        export_json()
        return
    if not args.action:
        print("[FAIL] 请指定 --action <功能名>（或用 --report / --export-json）")
        sys.exit(1)
    entry = record(args.action, args.course, args.detail)
    print(f"[OK] 已记录使用说明：{entry['action']} @ {entry['ts']}（本地：{LOG_FILE}）")


if __name__ == "__main__":
    main()
