#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""课程中枢自动发现（自动发现 + 定位注入 + 配置修复）：把「空间发现」手工路径固化为脚本。

背景：通用学生端在「教师以知识库空间共享交付」形态下，会话开场无法自动发现
课程中枢（找不到/读不了 → 直接错误停止）。本脚本固化以下发现路径：

  query_space_list → 按 description 锚文本「课程伴学数据中枢」筛课程空间
    （可再按 --course 关键词过滤 title/description）
  → query_space_node 取空间内 smartsheet 节点
  → smartsheet.list_tables 按表名分类：含 roster+course_versions ⇒ Hub；
    usage 组（usage / usage_records）与 summaries 组（summaries / session_summaries）
    各命中任一 ⇒ Usage（写配置时键仍用标准名 usage / summaries，值取实际命中表）
  → 读 course_versions 的「课程」列取 course_id（权威命名）
  → 生成/合并 data_hub_config.json 的 courses 条目（版本 2 schema）

用法：
  python3 scripts/discover_hub.py --list-only            # 只列候选空间
  python3 scripts/discover_hub.py --course 心理学与生活    # 发现并打印配置
  python3 scripts/discover_hub.py --course 心理学与生活 --out data_hub_config.json
  python3 scripts/discover_hub.py --merge-from probe.json [--out data_hub_config.json]
    # 形态②（仅 MCP 通道环境）回落：agent 直接调 MCP 工具完成 query_space_list /
    # query_space_node / smartsheet.list_tables / smartsheet.list_records 探测后，
    # 按下方结构组装 JSON 交本脚本做结构判定与配置合并（定位 ID 只写配置、不进对话）：
    #   {"hub":   {"file_id": "...", "tables": {"<实际表名>": "<sheet_id>", ...}},
    #    "usage": {"file_id": "...", "tables": {"<实际表名>": "<sheet_id>", ...}},
    #    "course_versions_records": [ ...smartsheet.list_records 的 records 数组... ]}

退出码：0 = 成功；1 = 无候选 / 结构不符（走结构不全分流话术）；2 = 通道不通（走超时话术）。
（--merge-from 模式不访问通道，不产生退出码 2。）
隐私：本脚本只读；输出含 file_id/sheet_id，仅供写包内 data_hub_config.json，不得进对话/日志。
"""

import argparse
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
HUB_ANCHORS = ("课程伴学数据中枢", "课程伴学知识库", "数据中枢", "Hub", "Usage")
HUB_TABLES = {"roster", "course_versions"}
# Usage 两表表名别名组：usage/usage_records、summaries/session_summaries 各命中任一即算齐
# （写配置时键仍用标准名 usage/summaries，值取实际命中的 sheet_id）
USAGE_GROUP = {"usage", "usage_records"}
SUMMARIES_GROUP = {"summaries", "session_summaries"}


def _harden():
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(errors="replace")
        except (AttributeError, ValueError, OSError):
            pass


_harden()


def _load_tdoc_path():
    """复用 course_tdoc.py 的自动定位逻辑（插件缓存最新版 tencentdocs.py）。"""
    sys.path.insert(0, PKG)
    try:
        import course_tdoc  # noqa
        return course_tdoc._autodiscover_tdoc()
    except Exception:
        return None


def _tdoc(script, tool, args):
    """经 course_tdoc.py 封装调用 MCP 工具，返回 structuredContent。"""
    cmd = [sys.executable, os.path.join(PKG, "course_tdoc.py"), script,
           "tdoc_call", "tencent-docs", tool, json.dumps(args, ensure_ascii=False)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120, encoding="utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        print("[FAIL] 通道超时（传输层问题，可重试/换形态，不等于未授权）")
        sys.exit(2)
    for line in (r.stdout or "").splitlines():
        if line.startswith('{"jsonrpc"'):
            resp = json.loads(line)
            if "error" in resp:
                print(f"[FAIL] {tool} -> {resp['error'].get('message', '')[:120]}")
                sys.exit(2)
            return resp["result"].get("structuredContent", {})
    print(f"[FAIL] {tool} 返回不可解析（传输层问题）")
    sys.exit(2)


def _node_rows(sc):
    return (sc or {}).get("children", []) or []


def _tables(script, file_id):
    sc = _tdoc(script, "smartsheet.list_tables", {"file_id": file_id})
    return {s.get("title", ""): s.get("sheet_id", "") for s in (sc or {}).get("sheets", [])}


def classify_tables(names):
    """表名分类判定（Skill 形态与 --merge-from 共用）：返回 "hub" / "usage" / None。

    Hub 判定精确匹配 roster+course_versions；Usage 按别名组判定——
    usage 组与 summaries 组各命中任一表名即算齐。
    """
    names = set(names)
    if HUB_TABLES <= names:
        return "hub"
    if (names & USAGE_GROUP) and (names & SUMMARIES_GROUP):
        return "usage"
    return None


def extract_course_ids(records):
    """从 course_versions 的「课程」列提取 course_id（权威命名；Skill 形态与 --merge-from 共用）。"""
    course_ids = set()
    for rec in (records or []):
        for fv in rec.get("field_values", []):
            if fv.get("field") == "课程":
                for it in (fv.get("text_value", {}) or {}).get("items", []):
                    try:
                        course_ids.update(json.loads(it.get("text", "[]")))
                    except (ValueError, TypeError):
                        continue
    return course_ids


def _merge_into_config(out_path, merged):
    """合并写入 data_hub_config.json（Skill 形态与 --merge-from 共用；缺 --out 时由调用方只打印）。"""
    cfg = {}
    if os.path.exists(out_path):
        try:
            cfg = json.load(open(out_path, encoding="utf-8-sig"))
        except (ValueError, OSError):
            cfg = {}
    cfg.setdefault("version", 2)
    cfg.setdefault("courses", {}).update(merged)
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"[OK] 已合并写入 {out_path}（courses 共 {len(cfg['courses'])} 门）")


def discover(course_kw, tdoc_script):
    sc = _tdoc(tdoc_script, "query_space_list", {})
    spaces = (sc or {}).get("spaces", []) or []
    cands = []
    for sp in spaces:
        desc = sp.get("description", "") or ""
        title = sp.get("title", "") or ""
        if sp.get("space_type") == 3:
            continue
        anchored = any(a in desc for a in HUB_ANCHORS)
        kw_hit = bool(course_kw) and (course_kw in title or course_kw in desc)
        if course_kw:
            if not kw_hit:
                continue
        elif not anchored:
            continue
        cands.append(sp)
    if not cands:
        print("[FAIL] 未发现课程伴学数据中枢空间（未授权 / 教师未共享空间）")
        sys.exit(1)

    results = []
    for sp in cands:
        sc_nodes = _tdoc(tdoc_script, "query_space_node", {"space_id": sp.get("space_id", "")})
        hub_id = usage_id = ""
        hub_sheets = usage_sheets = {}
        for node in _node_rows(sc_nodes):
            fid = node.get("node_id", "")
            if not fid or node.get("doc_type") != "smartsheet":
                continue
            tables = _tables(tdoc_script, fid)
            kind = classify_tables(tables)
            if kind == "hub":
                hub_id, hub_sheets = fid, {
                    "roster": tables["roster"], "course_ver": tables["course_versions"],
                    "agent_profile": tables.get("agent_profiles", ""),
                    "calendar": tables.get("calendar", ""), "term_config": tables.get("term_config", ""),
                }
            elif kind == "usage":
                u_name = "usage" if "usage" in tables else "usage_records"
                s_name = "summaries" if "summaries" in tables else "session_summaries"
                usage_id, usage_sheets = fid, {"usage": tables[u_name], "summaries": tables[s_name]}
        if not (hub_id and usage_id):
            print(f"[!] 空间「{sp.get('title')}」结构不全（Hub={'OK' if hub_id else '缺'} Usage={'OK' if usage_id else '缺'}）——跳过")
            continue
        # course_id 取 course_versions 的「课程」列（权威命名）
        cv = hub_sheets["course_ver"]
        sc_recs = _tdoc(tdoc_script, "smartsheet.list_records",
                        {"file_id": hub_id, "sheet_id": cv, "offset": 0, "limit": 50})
        course_ids = extract_course_ids((sc_recs or {}).get("records", []))
        course_ids = course_ids or {re.sub(r"\s+", "", sp.get("title", ""))}
        for cid in course_ids:
            results.append({
                "course_id": cid,
                "entry": {
                    "hub_file_id": hub_id,
                    "hub_sheets": hub_sheets,
                    "usage_file_id": usage_id,
                    "usage_sheet": usage_sheets,
                },
            })
    return results


def run_merge(payload, out_path):
    """--merge-from 模式（形态②回落）：复用与 Skill 形态同一套表名判定 / course_id 提取 /
    配置合并写入（不访问通道，不产生退出码 2）。"""
    hub = payload.get("hub") or {}
    usage = payload.get("usage") or {}
    hub_ok = classify_tables((hub.get("tables") or {}).keys()) == "hub"
    usage_ok = classify_tables((usage.get("tables") or {}).keys()) == "usage"
    if not (hub_ok and usage_ok):
        print("[FAIL] 结构不符（Hub 需 roster+course_versions；Usage 需 usage/usage_records 与 "
              "summaries/session_summaries 各命中一）——请核对 smartsheet.list_tables 结果")
        sys.exit(1)
    t_hub = hub["tables"]
    t_usage = usage["tables"]
    u_name = "usage" if "usage" in t_usage else "usage_records"
    s_name = "summaries" if "summaries" in t_usage else "session_summaries"
    entry = {
        "hub_file_id": hub.get("file_id", ""),
        "hub_sheets": {
            "roster": t_hub["roster"], "course_ver": t_hub["course_versions"],
            "agent_profile": t_hub.get("agent_profiles", ""),
            "calendar": t_hub.get("calendar", ""), "term_config": t_hub.get("term_config", ""),
        },
        "usage_file_id": usage.get("file_id", ""),
        "usage_sheet": {"usage": t_usage[u_name], "summaries": t_usage[s_name]},
    }
    course_ids = extract_course_ids(payload.get("course_versions_records", []))
    if not course_ids:
        print("[FAIL] course_versions_records 未提取到「课程」列 course_id——请核对 smartsheet.list_records 结果")
        sys.exit(1)
    merged = {cid: entry for cid in course_ids}
    for cid in merged:
        print(f"[OK] 合并课程 {cid}：Hub={entry['hub_file_id']} Usage={entry['usage_file_id']}")
    if out_path:
        _merge_into_config(out_path, merged)


def main():
    ap = argparse.ArgumentParser(description="课程中枢自动发现（通用学生端）")
    ap.add_argument("--course", default="", help="课程名关键词（空间 title/description 匹配；缺省列出全部中枢空间）")
    ap.add_argument("--out", default="", help="写入 data_hub_config.json 路径（合并写入；缺省仅打印）")
    ap.add_argument("--list-only", action="store_true", help="只列候选空间，不做表级探测")
    ap.add_argument("--merge-from", dest="merge_from", default="",
                    help="从 JSON 合并配置（形态② MCP 通道回落：agent 探测后组装，结构见文件头注释；"
                         "可与 --out 组合，缺 --out 仅打印；本模式不访问通道）")
    args = ap.parse_args()

    if args.merge_from:
        try:
            payload = json.load(open(args.merge_from, encoding="utf-8-sig"))
        except (ValueError, OSError) as e:
            print(f"[FAIL] merge 输入读取失败：{e}")
            sys.exit(1)
        run_merge(payload, args.out)
        return

    script = _load_tdoc_path()
    if not script:
        print("[FAIL] 未定位 tencentdocs.py（连接器未安装/未授权）")
        sys.exit(2)

    sc = _tdoc(script, "query_space_list", {})
    spaces = (sc or {}).get("spaces", []) or []
    cands = []
    for sp in spaces:
        title = sp.get("title", "") or ""
        desc = sp.get("description", "") or ""
        if sp.get("space_type") == 3:
            continue  # 个人空间
        anchored = any(a in desc for a in HUB_ANCHORS)
        kw_hit = bool(args.course) and (args.course in title or args.course in desc)
        if args.course:
            if not kw_hit:
                continue
        elif not anchored:
            continue
        cands.append(sp)
    if args.list_only:
        print("[候选空间]", json.dumps([{"title": s.get("title"), "space_id": s.get("space_id")} for s in cands],
                                     ensure_ascii=False))
        sys.exit(0)
    if not cands:
        print("[FAIL] 未发现课程伴学数据中枢空间（未授权 / 教师未共享空间）")
        sys.exit(1)

    found = discover(args.course, script)
    if not found:
        print("[FAIL] 空间存在但结构不符（缺 Hub/Usage 智能表格）——联系老师检查数据中枢")
        sys.exit(1)

    merged = {}
    for f in found:
        merged[f["course_id"]] = f["entry"]
        print(f"[OK] 发现课程 {f['course_id']}：Hub={f['entry']['hub_file_id']} Usage={f['entry']['usage_file_id']}")

    if args.out:
        _merge_into_config(args.out, merged)


if __name__ == "__main__":
    main()
