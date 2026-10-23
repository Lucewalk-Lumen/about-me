#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""任务积分与游戏化（）。

输入：已从数据中枢取出并本地聚合的学情 JSON（积分与看板共用同一份聚合口径）。
输出：按课程的**积分排行榜**，前三名标注「奖励」；可写回 `points` 子表（若已建）。

积分口径（游戏化、正向激励，与平时分口径解耦，便于教师另行调整）：
  points = 10 * 收敛KP + 4 * 部分收敛KP + 2 * 伴学会话 + 1 * 覆盖知识点数
  （卡住不计分，但在看板/预警里单列，不惩罚、只引导补练）
若聚合数据带了 `bonus`（如题目生成 / 间隔复习额外加分），一并累加。

纪律：不编造——缺字段按 0 计并标注；样本不足时仍排名但附置信度提示。
用法（本脚本在教师端包根、在学生端包内 scripts/ 下，按所在位置调用即可）：
  python3 <本脚本路径> <聚合json> --course <名> --out <排行榜json>
  python3 <本脚本路径> <聚合json> --top-n 3        # 仅看前三（奖励名单）
"""

import argparse
import json
import os
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


def _read_csv(path):
    """读CSV（自动处理 UTF-8 BOM / GBK）。返回 (fieldnames, rows)。"""
    import csv
    for enc in ("utf-8-sig", "gbk", "utf-8"):
        try:
            with open(path, encoding=enc, newline="") as f:
                r = csv.DictReader(f)
                return list(r.fieldnames or []), list(r)
        except (UnicodeDecodeError, LookupError):
            continue
    raise OSError("CSV 编码无法识别（试过 utf-8-sig / gbk / utf-8）")


def _pick(fieldnames, *cands):
    """按候选名（子串匹配）挑第一个真实存在的列名。"""
    low = {f.lower(): f for f in fieldnames}
    for c in cands:
        if c in low:
            return low[c]
        for k, orig in low.items():
            if c in k:
                return orig
    return None


def aggregate_from_csv(path, exclude_test=True):
    """从 Usage 表导出的原始 CSV 直接聚合成学生列表（口径同 agents/course-tutor.md §4.1）。

    期望列（缺列则该指标按 0 计并标注，**不编造**）：
      学号 / 姓名 / 时间 / 知识点 / 结果（可选：环节）
    - sessions  = 去重 (学号, 日期) 组合数——按 ISO 日期前缀聚合，
                  秒级递进的多条记录同日只算 1 个会话（修复）
    - converged / partial / stuck = 按「知识点」去重后的**最高结果**计数
                  （同一 KP 多环节重复记录只计一次，防重复计分—— 修复①）
    - 题目生成环节：只计 bonus（+1/条），**不作为 KP 收敛证据**（防刷题库—— 修复③；
                  与 socratic_agent_prompt.md §3.2「权重很低」的承诺对齐）
    - kp_distinct = 该生去重知识点数
    """
    fieldnames, rows = _read_csv(path)
    if not rows:
        return [], {"fieldnames": fieldnames, "rows": 0, "notes": ["CSV 无数据行"]}

    f_sid = _pick(fieldnames, "学号", "sid", "student_id")
    f_name = _pick(fieldnames, "姓名", "name")
    f_time = _pick(fieldnames, "时间", "time", "date")
    f_kp = _pick(fieldnames, "知识点", "kp", "kp_id")
    f_res = _pick(fieldnames, "结果", "result")
    f_stage = _pick(fieldnames, "环节", "stage", "phase")

    notes = []
    if not f_sid:
        raise ValueError("CSV 缺「学号」列，无法聚合（期望列：学号/姓名/时间/知识点/结果）")
    for label, col in (("姓名", f_name), ("时间", f_time), ("知识点", f_kp), ("结果", f_res)):
        if not col:
            notes.append(f"CSV 缺「{label}」列 → 相关指标按 0 计（不编造）")
    if not f_stage:
        notes.append("CSV 缺「环节」列 → 无法识别题目生成环节，全部结果行按 KP 收敛证据计（旧口径）")

    def _res_rank(res):
        """结果 → 去重排序值：已收敛 2 > 部分收敛 1 > 卡住 0；非法值 -1（不计）。"""
        res = (res or "").strip()
        if "已收敛" in res or res == "收敛":
            return 2
        if "部分" in res:
            return 1
        if "卡住" in res:
            return 0
        return -1

    def _ok(sid):
        sid = (sid or "").strip()
        if not sid:
            return False
        if exclude_test and sid in ("0000", "0"):
            return False
        return True

    acc = {}
    for r in rows:
        sid = (r.get(f_sid) or "").strip()
        if not _ok(sid):
            continue
        a = acc.setdefault(sid, {
            "sid": sid,
            "name": (r.get(f_name) or "").strip() if f_name else sid,
            "converged": 0, "partial": 0, "stuck": 0,
            "_sessions": set(), "_kps": set(),
            "_best": {},   # kp -> 最高结果 rank（2/1/0）
            "_bonus": 0,   # 题目生成条数（每条 +1 分 bonus）
        })
        if f_time:
            # ：按日期聚合会话（YYYY-MM-DD 前缀），秒级递进不再虚增
            a["_sessions"].add(((r.get(f_time) or "").strip())[:10])
        kp = (r.get(f_kp) or "").strip() if f_kp else ""
        # ：章 / 节级行（CH-1、SEC-1-2）只计会话与活跃度，不计知识点收敛，
        # 否则一整章的努力会被错误归因到一个知识点上、并虚增覆盖率
        chapter_level = kp.startswith(("CH-", "SEC-"))
        if kp and not chapter_level:
            a["_kps"].add(kp)
        if f_res:
            res = (r.get(f_res) or "").strip()
            rank = _res_rank(res)
            stage = (r.get(f_stage) or "").strip() if f_stage else ""
            if "题目生成" in stage:
                # ：题目生成只计 bonus，不做 KP 收敛证据
                a["_bonus"] += 1
            elif rank >= 0 and not chapter_level:
                if kp:
                    a["_best"][kp] = max(a["_best"].get(kp, -1), rank)
                else:
                    # 无知识点列时的兜底：退化为按行计数（无法去重，如实标注）
                    if rank == 2:
                        a["converged"] += 1
                    elif rank == 1:
                        a["partial"] += 1
                    else:
                        a["stuck"] += 1

    students = []
    for a in acc.values():
        best = a["_best"]
        students.append({
            "sid": a["sid"],
            "name": a["name"] or a["sid"],
            "converged": a["converged"] + sum(1 for v in best.values() if v == 2),
            "partial": a["partial"] + sum(1 for v in best.values() if v == 1),
            "stuck": a["stuck"] + sum(1 for v in best.values() if v == 0),
            "sessions": len(a["_sessions"]),
            "kp_distinct": len([k for k in a["_kps"] if k]),
            "bonus": a["_bonus"],
        })
    meta = {"fieldnames": fieldnames, "rows": len(rows), "notes": notes}
    return students, meta


def _usage(course, detail):
    """自动埋点（）：调用即记录，失败不影响功能。"""
    try:
        import course_usage_log
        course_usage_log.auto_record("积分计算", course, detail)
    except Exception:
        pass


def compute(students):
    board = []
    for st in students:
        conv = st.get("converged", 0) or 0
        part = st.get("partial", 0) or 0
        sess = st.get("sessions", 0) or 0
        kp = st.get("kp_distinct", st.get("kp_records", 0)) or 0
        bonus = st.get("bonus", 0) or 0
        pts = 10 * conv + 4 * part + 2 * sess + 1 * kp + bonus
        board.append({
            "sid": st.get("sid", "?"),
            "name": st.get("name", st.get("sid", "?")),
            "points": pts,
            "converged": conv, "partial": part,
            "sessions": sess, "kp": kp, "bonus": bonus,
        })
    board.sort(key=lambda x: x["points"], reverse=True)
    for i, r in enumerate(board):
        r["rank"] = i + 1
        r["reward"] = i < 3
    return board


def main():
    ap = argparse.ArgumentParser(description="任务积分与游戏化排行榜（）")
    ap.add_argument("data_json", nargs="?", default="", help="聚合后的学情 JSON（与 --from-csv 二选一）")
    ap.add_argument("--from-csv", default="", help="Usage 表导出的原始 CSV（推荐：直接吃原始数据自动聚合）")
    ap.add_argument("--course", default="")
    ap.add_argument("--out", default="", help="输出排行榜 JSON 路径")
    ap.add_argument("--top-n", type=int, default=0, help="仅输出前 N 名（奖励名单）")
    ap.add_argument("--include-test", action="store_true", help="保留测试号 0000（默认剔除）")
    ap.add_argument("--student", default="",
                    help="个人模式：只输出该生（学号或姓名）自己的积分与排名，不显示他人明细")
    args = ap.parse_args()

    meta = {}
    if args.from_csv:
        try:
            students, meta = aggregate_from_csv(args.from_csv, exclude_test=not args.include_test)
        except (OSError, ValueError) as exc:
            print(f"[FAIL] 无法从 CSV 聚合：{exc}")
            sys.exit(1)
        data = {"students": students, "course_name": args.course}
        print(f"[OK] 已从 CSV 聚合：{meta.get('rows', 0)} 行 → {len(students)} 名学生")
        for n in meta.get("notes", []) or []:
            print(f"[!] {n}")
    elif args.data_json:
        try:
            data = load_json(args.data_json)
        except (OSError, ValueError) as exc:
            print(f"[FAIL] 无法读取聚合 JSON：{exc}")
            sys.exit(1)
    else:
        print("[FAIL] 请提供聚合 JSON 路径，或用 --from-csv <Usage导出的csv>")
        sys.exit(1)

    board = compute(data.get("students", []) or [])

    if not board:
        print("[!] 没有可用学情数据：学生可能尚未写入记录，或全部行被聚合前过滤剔除"
              "（测试号 0000 / 空学号 / 教师端行）——请先确认数据中枢已有学情写入。")
        _usage(args.course, "空数据（无可用学情）")
        sys.exit(0)

    cname = args.course or data.get("course_name", "") or ""

    # ── 个人模式（学生端「我的积分」）：只显示自己，不显示他人明细 ──
    if args.student:
        mine = [r for r in board
                if r.get("sid") == args.student or r.get("name") == args.student]
        if not mine:
            print(f"[!] 未找到「{args.student}」的积分记录（数据中没有该学号/姓名）——不编造。")
            _usage(cname, f"个人模式未命中：{args.student}")
            sys.exit(0)
        r = mine[0]
        print("【我的积分】" + (f"课程：{cname}" if cname else ""))
        print(f"  姓名：{r['name']}（{r['sid']}）    积分：{r['points']} 分")
        print(f"  明细：收敛 {r['converged']}×10 · 部分 {r['partial']}×4 · "
              f"会话 {r['sessions']}×2 · 知识点 {r['kp']}×1"
              + (f" · 奖励加分 {r['bonus']}" if r.get("bonus") else ""))
        if len(board) == 1:
            print("  班级排名：—（当前仅本人数据；班级排名由教师统计或期末发布）")
        else:
            print(f"  班级排名：第 {r['rank']} / {len(board)} 名"
                  + ("　🏆 前三名" if r.get("reward") else ""))
        print("\n  （只显示你自己的积分与排名，不包含其他同学明细）")
        _usage(cname, f"个人积分：{r['sid']} = {r['points']} 分")
        if args.out:
            with open(args.out, "w", encoding="utf-8") as f:
                json.dump({"course": cname, "student": r,
                           "class_size": len(board)}, f, ensure_ascii=False, indent=2)
        return

    shown = board[:args.top_n] if args.top_n else board

    print(f"【积分排行榜】课程：{args.course or data.get('course_name','')}  共 {len(board)} 人")
    print(f"{'排名':<4}{'学生':<12}{'积分':<8}{'收敛':<6}{'部分':<6}{'会话':<6}{'奖励'}")
    for r in shown:
        print(f"{r['rank']:<4}{r['name']:<12}{r['points']:<8}{r['converged']:<6}"
              f"{r['partial']:<6}{r['sessions']:<6}{'🏆' if r['reward'] else ''}")
    if not args.top_n:
        tops = board[:3]
        if tops:
            print("\n🏆 前三名奖励名单：" + "、".join(f"{r['name']}({r['points']})" for r in tops))

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump({"course": args.course, "leaderboard": board}, f,
                      ensure_ascii=False, indent=2)
        print(f"\n[OK] 排行榜已写出: {args.out}")
    _usage(cname, f"排行榜：{len(board)} 人")


if __name__ == "__main__":
    main()
