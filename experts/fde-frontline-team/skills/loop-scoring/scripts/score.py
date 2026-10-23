#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""loop-scoring: deterministic loop ranking script (stdlib only).

Score = (frequency_per_week * minutes * rule_level) / risk
Stop signals: low-freq-high-risk / unclear rules / irreversible errors.
Output: plain text with [OK]/[FAIL] markers only (no emoji).
"""
import argparse
import json
import sys

# Thresholds kept in sync with ../SKILL.md (stop-signal section).
LOW_FREQ_PER_WEEK = 1.0
HIGH_RISK = 4
UNCLEAR_RULE_LEVEL = 0.5
MAX_RISK = 5

DEMO = [
    {"name": "示例-日报汇总", "freq_per_week": 5, "minutes": 40,
     "rule_level": 0.9, "risk": 2, "irreversible": False},
    {"name": "示例-采购审批初审", "freq_per_week": 12, "minutes": 15,
     "rule_level": 0.6, "risk": 3, "irreversible": False},
    {"name": "示例-危机公关回应", "freq_per_week": 0.2, "minutes": 120,
     "rule_level": 0.3, "risk": 5, "irreversible": True},
]


def fail(msg):
    print("[FAIL] " + msg)
    return 1


def validate(item, idx):
    if not isinstance(item, dict):
        return "第 %d 项不是对象" % idx
    for key in ("name", "freq_per_week", "minutes", "rule_level", "risk"):
        if key not in item:
            return "第 %d 项缺少字段 %s" % (idx, key)
    for key in ("freq_per_week", "minutes", "rule_level", "risk"):
        if not isinstance(item[key], (int, float)) or isinstance(item[key], bool):
            return "第 %d 项字段 %s 必须是数值" % (idx, key)
    if item["freq_per_week"] < 0:
        return "第 %d 项频次不能为负" % idx
    if item["minutes"] <= 0:
        return "第 %d 项耗时必须大于 0" % idx
    if not (0.0 <= item["rule_level"] <= 1.0):
        return "第 %d 项规则化程度须在 0 到 1 之间" % idx
    if not (1 <= item["risk"] <= MAX_RISK):
        return "第 %d 项风险等级须在 1 到 %d 之间" % (idx, MAX_RISK)
    return None


def stop_signals(item):
    signals = []
    if item["freq_per_week"] < LOW_FREQ_PER_WEEK and item["risk"] >= HIGH_RISK:
        signals.append("低频高风险")
    if item["rule_level"] < UNCLEAR_RULE_LEVEL:
        signals.append("规则说不清")
    if item.get("irreversible", False) or item["risk"] >= MAX_RISK:
        signals.append("出错不可逆")
    return signals


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="score.py",
        description="环排序确定性计算：评分=(频次x单次耗时x规则化程度)/风险，并判定停工三信号。")
    parser.add_argument("--input", "-i", help="场景 JSON 文件路径（数组）；省略则从 stdin 读")
    parser.add_argument("--demo", action="store_true", help="使用内置合成示例数据演示")
    args = parser.parse_args(argv)

    if args.demo:
        items = DEMO
        source = "内置示例"
    else:
        try:
            raw = open(args.input, "r", encoding="utf-8").read() if args.input else sys.stdin.read()
        except OSError as exc:
            return fail("无法读取输入: %s" % exc)
        try:
            items = json.loads(raw)
        except ValueError as exc:
            return fail("JSON 解析失败: %s" % exc)
        source = args.input or "stdin"

    if not isinstance(items, list):
        return fail("输入必须是 JSON 数组")
    if not items:
        return fail("输入数组为空")

    for idx, item in enumerate(items, 1):
        err = validate(item, idx)
        if err:
            return fail(err)

    scored = []
    for item in items:
        score = (item["freq_per_week"] * item["minutes"] * item["rule_level"]) / item["risk"]
        scored.append((score, item))

    scored.sort(key=lambda pair: pair[0], reverse=True)

    print("[OK] 环排序评分（数据源: %s，共 %d 个场景）" % (source, len(scored)))
    for rank, (score, item) in enumerate(scored, 1):
        formula = "(%.4g x %.4g x %.4g) / %.4g" % (
            item["freq_per_week"], item["minutes"], item["rule_level"], item["risk"])
        signals = stop_signals(item)
        verdict = " | 先不做: " + "、".join(signals) if signals else ""
        print("  %d. %s  评分=%.2f  代入=%s%s" % (rank, item["name"], score, formula, verdict))
    stopped = sum(1 for _, item in scored if stop_signals(item))
    print("[OK] 汇总: 可推进 %d 个，先不做 %d 个（停工三信号口径见 SKILL.md）" % (len(scored) - stopped, stopped))
    return 0


if __name__ == "__main__":
    sys.exit(main())
