#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""课程资产取回（定位 + 导出 / 下载 + 命名修复）：导出下载闭环 + 规范命名落盘。

链路：
  读 data_hub_config.json 定位该课 Hub → course_versions 行取四资产 tdoc: 定位
  → manage.export_file(file_id) → 轮询 manage.export_progress(task_id)（3s 间隔）
  → 取下载 URL **立即下载**（签名 URL 约 30 分钟有效）→ 按资产角色规范命名 + 内容校验
  → 落 <out-dir>/<course_id>/ 下。

规范命名（客户端观感统一，不要求教师端改标题）：
  配置路径 → config.json        知识库路径 → knowledge_hub.json
  题库路径 → quiz_bank.md       题集路径 → socratic_testset.md
  （教师端按端到端管线托管：.md 家族转 txt 上传、.json 原样上传。
   取回后按角色改名，内容字节等价）

内容校验：json 家族必须可 json.loads；md 家族必须非空且不以 '<' 开头（防拿回查看器 HTML）。

用法：
  python3 scripts/fetch_assets.py --course psychology-and-life --out-dir <取回材料目录>
  python3 scripts/fetch_assets.py --resolve-records <records.json>     # 形态②回落·第一步（见下）
  python3 scripts/fetch_assets.py --download-from <plan.json>          # 形态②回落·第二步（见下）

形态②（仅 MCP 通道环境）回落两步——与 Skill 形态共用同一套解析 / 下载 / 校验 / 命名逻辑：
  第一步 --resolve-records：输入 = agent 直接调 MCP smartsheet.list_records 取回的
    course_versions records JSON（{"records":[...]} 或裸 records 数组均可）；
    脚本复用现有行解析 + tdoc: 定位解析，输出到 stdout：
      {"course_id": "...", "assets": {"配置路径": {"file_id": "..."}, "知识库路径": {...},
       "题库路径": {...}, "题集路径": {...}}}
    供 agent 形态②发起 manage.export_file / manage.export_progress 拿下载 URL；
    要求四资产定位齐全：缺列 / 非法定位 → exit 1（与 Skill 形态的「跳过」容忍不同，
    形态②下由 agent 补探测后再跑）。定位 ID 只写配置 / 本地输出，不进对话。
  第二步 --download-from：输入 = {"course_id": "...", "out_dir": "...",
    "assets": {"配置路径": {"url": "..."}, ...}}（url 为 export_progress 返回的下载 URL，
    **签名 URL 约 30 分钟有效，拿到后尽快调用**）；脚本复用「下载 + 内容校验 + ROLE_MAP
    规范命名落盘」，落 <out_dir>/<course_id>/ 下；校验失败按现有语义报错退出。

退出码：0 全部或部分成功（部分资产失败不视为整体失败，汇总行注明成功/失败数）；1 全部失败或结构/数据问题；2 通道问题（--resolve-records / --download-from 不访问通道，不产生 2）。
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
ROLE_MAP = {
    "配置路径": ("config.json", "json"),
    "知识库路径": ("knowledge_hub.json", "json"),
    "题库路径": ("quiz_bank.md", "md"),
    "题集路径": ("socratic_testset.md", "md"),
}
ASSET_COLS = tuple(ROLE_MAP)


def _harden():
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(errors="replace")
        except (AttributeError, ValueError, OSError):
            pass


_harden()


def _tdoc(tool, args):
    cmd = [sys.executable, os.path.join(PKG, "course_tdoc.py"),
           "tdoc_call", "tencent-docs", tool, json.dumps(args, ensure_ascii=False)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120,
                           encoding="utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        print("[FAIL] 通道超时（传输层问题，可重试）")
        sys.exit(2)
    for line in (r.stdout or "").splitlines():
        if line.startswith('{"jsonrpc"'):
            resp = json.loads(line)
            if "error" in resp:
                print(f"[FAIL] {tool} -> {resp['error'].get('message', '')[:120]}")
                sys.exit(2)
            return resp["result"].get("structuredContent", {})
    print(f"[FAIL] {tool} 返回不可解析")
    sys.exit(2)


def _flatten(sc):
    rows = []
    for rec in (sc or {}).get("records", []):
        row = {}
        for fv in rec.get("field_values", []):
            items = (fv.get("text_value") or {}).get("items", [])
            row[fv["field"]] = items[0]["text"] if items else ""
        rows.append(row)
    return rows


def _course_entry(cfg, course):
    courses = (cfg or {}).get("courses", {}) or {}
    if course in courses:
        return course, courses[course]
    hits = [(cid, e) for cid, e in courses.items() if course in cid]
    if len(hits) == 1:
        return hits[0]
    print(f"[FAIL] 课程「{course}」在 data_hub_config.json 中不唯一或不存在（现有：{list(courses)}）")
    sys.exit(1)


def parse_tdoc_loc(loc):
    """解析 tdoc: 云端定位（Skill 形态 main 与 --resolve-records 共用）；非法 / 空返回 None。"""
    m = re.match(r"^tdoc:(.+)$", (loc or "").strip())
    return m.group(1) if m else None


def _download_and_save(url, dest, kind):
    """下载 + 内容校验 + 规范落盘（Skill 形态与 --download-from 共用）。"""
    try:
        with urllib.request.urlopen(url, timeout=120) as resp:
            data = resp.read()
    except OSError as exc:
        print(f"[FAIL] 下载失败（签名 URL 30 分钟有效，勿拖延）：{exc}")
        return False
    # 内容校验
    if kind == "json":
        try:
            json.loads(data.decode("utf-8-sig"))
        except (ValueError, UnicodeDecodeError):
            print(f"[FAIL] 内容不是合法 JSON（{dest}）——疑似拿回查看器页/错误页，不入盘")
            return False
    else:
        head = data[:200].lstrip()
        if not data or head.startswith(b"<"):
            print(f"[FAIL] 内容为空或疑似 HTML 查看器页（{dest}）——不入盘")
            return False
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "wb") as f:
        f.write(data)
    print(f"[OK] {os.path.basename(dest)} {len(data)} 字节")
    return True


def _fetch_one(script_args, file_id, dest, kind):
    sc = _tdoc("manage.export_file", {"file_id": file_id})
    task = (sc or {}).get("task_id", "")
    if not task:
        print(f"[FAIL] export_file 未返回 task_id（{dest}）")
        return False
    url = ""
    for _ in range(40):  # 3s × 40 = 2 分钟上限
        time.sleep(3)
        pr = _tdoc("manage.export_progress", {"task_id": task})
        st = pr or {}
        # 实测返回结构：{file_url, progress}（progress=100 即完成）；无 status/state/download_url 字段
        url = st.get("file_url", st.get("url", st.get("download_url", "")))
        prog = st.get("progress", None)
        if url and (prog is None or int(prog) >= 100):
            break
        err = str(st.get("error", ""))
        if err and err not in ("", "null"):
            print(f"[FAIL] 导出任务报错：{err[:120]}（{dest}）")
            return False
    if not url:
        print(f"[FAIL] 导出超时未取到下载 URL（{dest}）")
        return False
    return _download_and_save(url, dest, kind)


def run_resolve(path):
    """--resolve-records（形态②回落·第一步）：从 agent 取回的 course_versions records
    解析课程与四资产 tdoc: 定位，输出 {"course_id","assets"} 到 stdout（不访问通道）。"""
    try:
        raw = json.load(open(path, encoding="utf-8-sig"))
    except (ValueError, OSError) as e:
        print(f"[FAIL] 输入读取失败：{e}")
        sys.exit(1)
    if isinstance(raw, dict) and "records" in raw:
        rows = _flatten(raw)  # structuredContent 形态（与 Skill 形态 main 同一解析）
    elif isinstance(raw, list):
        rows = _flatten({"records": raw})  # 裸 records 数组形态
    else:
        print('[FAIL] 输入结构不符（需 {"records":[...]} 或 records 数组）')
        sys.exit(1)
    picks = [r for r in rows if (r.get("状态") or "").strip() in ("published", "gray")]
    if not picks:
        print("[FAIL] records 中没有状态为 published/gray 的课程版本行")
        sys.exit(1)
    row = picks[0]
    course_cell = (row.get("课程") or "").strip()
    try:
        parsed = json.loads(course_cell)
        course_id = parsed[0] if isinstance(parsed, list) and parsed else course_cell
    except ValueError:
        course_id = course_cell
    if not course_id:
        print("[FAIL] 行内缺「课程」列，无法确定 course_id")
        sys.exit(1)
    assets = {}
    for col in ASSET_COLS:
        fid = parse_tdoc_loc(row.get(col))
        if not fid:
            print(f'[FAIL] 「{col}」缺列或非法定位（{row.get(col) or "空"}）——形态②下请补探测后再跑')
            sys.exit(1)
        assets[col] = {"file_id": fid}
    print(json.dumps({"course_id": course_id, "assets": assets}, ensure_ascii=False))


def run_download(path):
    """--download-from（形态②回落·第二步）：按 plan JSON 下载 + 内容校验 + 规范命名落盘
    （不访问通道；url 为 agent 经 manage.export_progress 拿到的下载 URL，约 30 分钟有效）。"""
    try:
        payload = json.load(open(path, encoding="utf-8-sig"))
    except (ValueError, OSError) as e:
        print(f"[FAIL] 输入读取失败：{e}")
        sys.exit(1)
    course_id = str(payload.get("course_id") or "").strip()
    out_dir = str(payload.get("out_dir") or "").strip()
    assets = payload.get("assets") or {}
    if not (course_id and out_dir and isinstance(assets, dict) and assets):
        print('[FAIL] 输入结构不符（需 {"course_id","out_dir","assets":{列:{"url":...}}} 且 assets 非空）')
        sys.exit(1)
    for col in assets:
        if col not in ROLE_MAP:
            print(f'[FAIL] 未知资产列「{col}」（合法：{list(ROLE_MAP)}）')
            sys.exit(1)
    base = os.path.join(out_dir, os.path.basename(course_id))
    ok = fail = 0
    for col, spec in assets.items():
        name, kind = ROLE_MAP[col]
        url = str((spec or {}).get("url") or "").strip()
        if not url:
            print(f"[FAIL] 「{col}」缺 url")
            sys.exit(1)
        if _download_and_save(url, os.path.join(base, name), kind):
            ok += 1
        else:
            fail += 1
    print(f"[SUMMARY] {course_id}: 成功 {ok} / 失败 {fail} → {base}")
    sys.exit(0 if ok and not fail else (0 if ok else 1))


def main():
    ap = argparse.ArgumentParser(description="课程资产取回：导出下载闭环 + 规范命名")
    ap.add_argument("--course", default="", help="course_id 或其关键词（Skill 形态必填）")
    ap.add_argument("--out-dir", default="", help="取回材料根目录（脚本会建 <out>/<course_id>/）；缺省用 ~/.workbuddy/course_materials（与各端约定的缓存落点一致）")
    ap.add_argument("--config", default=os.path.join(PKG, "data_hub_config.json"),
                    help="data_hub_config.json 路径（默认包内）")
    ap.add_argument("--resolve-records", dest="resolve_records", default="",
                    help="形态②回落·第一步：读取 agent 经 MCP smartsheet.list_records 取回的 course_versions records JSON，输出四资产定位清单到 stdout（结构见文件头注释）")
    ap.add_argument("--download-from", dest="download_from", default="",
                    help="形态②回落·第二步：读取下载计划 JSON（course_id/out_dir/assets.url），下载+校验+规范命名落盘（签名 URL 约 30 分钟有效，拿到后尽快调用）")
    args = ap.parse_args()

    if args.resolve_records:
        run_resolve(args.resolve_records)
        return
    if args.download_from:
        run_download(args.download_from)
        return
    if not args.course:
        ap.error("the following arguments are required: --course")
    if not os.path.isfile(args.config):
        print(f"[FAIL] 找不到 {args.config}（先完成授权/发现）")
        sys.exit(1)
    cfg = json.load(open(args.config, encoding="utf-8-sig"))
    course_id, entry = _course_entry(cfg, args.course)

    hub_id = entry.get("hub_file_id", "")
    cv_sheet = (entry.get("hub_sheets") or {}).get("course_ver", "")
    if not (hub_id and cv_sheet):
        print("[FAIL] 配置缺 hub_file_id / course_ver（重跑 discover_hub.py）")
        sys.exit(1)
    rows = _flatten(_tdoc("smartsheet.list_records",
                          {"file_id": hub_id, "sheet_id": cv_sheet, "offset": 0, "limit": 100}))
    picks = [r for r in rows if course_id in (r.get("课程") or "")]
    if not picks:
        print(f"[FAIL] course_versions 中没有课程 {course_id} 的行")
        sys.exit(1)
    row = picks[0]
    status = (row.get("状态") or "").strip()
    if status not in ("published", "gray"):
        print(f"[FAIL] 版本状态为「{status or '空'}」（非 published/gray）——教师端未发布或已下线")
        sys.exit(1)

    out_dir = os.path.join(args.out_dir, os.path.basename(course_id))
    ok = fail = 0
    for col, (name, kind) in ROLE_MAP.items():
        fid = parse_tdoc_loc(row.get(col))
        if not fid:
            print(f"[!] {col} 未登记云端定位（{(row.get(col) or '').strip() or '空'}）——跳过")
            fail += 1
            continue
        if _fetch_one(None, fid, os.path.join(out_dir, name), kind):
            ok += 1
        else:
            fail += 1
    print(f"[SUMMARY] {course_id}: 成功 {ok} / 失败 {fail} → {out_dir}")
    sys.exit(0 if ok and not fail else (0 if ok else 1))


if __name__ == "__main__":
    main()
