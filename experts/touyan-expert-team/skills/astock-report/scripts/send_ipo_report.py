#!/usr/bin/env python3
"""A股IPO周报 - 微信友好版（周三~下周二自动周期）"""
import json, subprocess
import pandas as pd
from datetime import timedelta
import sys
from pathlib import Path

# ── 周期计算 ──────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from common import get_ipo_report_period, now_bj

NOW = now_bj()
_period_start_dt, _period_end_dt, REPORT_START, TODAY_STR = get_ipo_report_period(NOW)
# 周期：当前周周三 ～ 下周二
PERIOD_START = _period_start_dt
PERIOD_END   = _period_end_dt
# 本周上会计划：当前周期的下周二 = today + (weekday+1)%7 + 6
# 下周上会计划：再往后推7天
# THIS_WEEK_END：下一个周二（本期周期结束日的下一天）
# NEXT_WEEK_END：再下一个周二
_w = NOW.weekday()
_days_to_tue = 1 if _w == 1 else (_w + 1) % 7
THIS_WEEK_END = (NOW + timedelta(days=_days_to_tue + 6)).strftime("%m/%d")
NEXT_WEEK_END = (NOW + timedelta(days=_days_to_tue + 13)).strftime("%m/%d")
QUEUE_DATE    = NOW.strftime("%Y年%m月%d日")

# ── Webhook ───────────────────────────────────────────────
from keys_loader import get_webhook_url

def wx(text):
    d = {"msgtype": "text", "text": {"content": text}}
    p = json.dumps(d, ensure_ascii=False)
    r = subprocess.run(
        ["curl", "-s", "-X", "POST", get_webhook_url(),
         "-H", "Content-Type: application/json", "-d", "@-"],
        input=p.encode("utf-8"), capture_output=True)
    try:
        return json.loads(r.stdout.decode()).get("errcode", -1)
    except:
        return -1

def shname(name, n=12):
    return name[:n] + ".." if len(name) > n else name

def sdate(dt):
    return str(dt)[5:7] + "/" + str(dt)[8:10]

def board_alias(b):
    return {"上交所科创板": "科创板", "深交所创业板": "创业板",
            "深交所主板": "深主板", "上交所主板": "沪主板",
            "北交所": "北交所"}.get(b, b)

# ── 已知上市新股涨幅（Period 内实测）────────────────────────
LISTINGS_GAIN = {
    "301683": {"name": "慧谷新材", "date": "04/01", "price": 78.38, "gain": "61.66%"},
    "001257": {"name": "盛龙股份", "date": "03/31", "price": 7.82,  "gain": "254.0%"},
    "688813": {"name": "泰金新能", "date": "03/31", "price": 26.28, "gain": "88.24%"},
    "920055": {"name": "隆源股份", "date": "03/31", "price": 24.70, "gain": "53.04%"},
    "920188": {"name": "悦龙科技", "date": "03/30", "price": 14.04, "gain": "184.0%"},
}

def fmt_price(v):
    if pd.isna(v): return "N/A"
    return f"{v:.2f}元"

# ── 数据拉取（AKShare）─────────────────────────────────────
import akshare as ak

_pstart_str = PERIOD_START.strftime("%Y-%m-%d")
_pend_str   = PERIOD_END.strftime("%Y-%m-%d")
_pnext_fri = (_period_end_dt + timedelta(days=7)).strftime("%Y-%m-%d")

review = ak.stock_ipo_review_em()
review["上会日期"] = pd.to_datetime(review["上会日期"], errors="coerce").dt.tz_localize(None)
recent_r = (review
    .loc[review["上会日期"].between(pd.Timestamp(_pstart_str), pd.Timestamp(_pend_str))]
    .dropna(subset=["上会日期"])
    .sort_values("上会日期"))
next_r = (review
    .loc[review["上会日期"].between(pd.Timestamp(_pend_str) + pd.Timedelta(days=1),
                                    pd.Timestamp(_pnext_fri))]
    .dropna(subset=["上会日期"])
    .sort_values("上会日期"))

df = ak.stock_new_ipo_cninfo()
df["申购_dt"] = pd.to_datetime(df["申购日期"], errors="coerce").dt.tz_localize(None)
df["上市_dt"] = pd.to_datetime(df["上市日期"], errors="coerce").dt.tz_localize(None)
recent_a = (df
    .loc[df["申购_dt"].between(pd.Timestamp(_pstart_str), pd.Timestamp(_pend_str))]
    .dropna(subset=["申购_dt"])
    .sort_values("申购_dt"))
next_a = (df
    .loc[df["申购_dt"].between(pd.Timestamp(_pend_str) + pd.Timedelta(days=1),
                               pd.Timestamp(_pnext_fri))]
    .dropna(subset=["申购_dt"])
    .sort_values("申购_dt"))
recent_l = (df
    .loc[df["上市_dt"].between(pd.Timestamp(_pstart_str), pd.Timestamp(_pend_str))]
    .dropna(subset=["上市_dt"])
    .sort_values("上市_dt"))

queue = ak.stock_ipo_declare_em()
queue["更新日期"] = pd.to_datetime(queue["更新日期"], errors="coerce").dt.tz_localize(None)
recent_up = queue[queue["更新日期"].between(pd.Timestamp(_pstart_str), pd.Timestamp(_pend_str))]
reg_up    = recent_up[recent_up["最新状态"].isin(["注册", "核准"])].dropna(subset=["企业名称"])

# ── 排队数据 ───────────────────────────────────────────────
# 旧版本这里使用固定值，容易让用户误以为是实时统计。
# 未接入可追溯实时来源前，不输出排队总量和板块明细。
QUEUE = {}
QUEUE_TOTALS = {}

# ── 组装报告 ───────────────────────────────────────────────
lines = [f"📋 A股IPO周报 {REPORT_START}～{TODAY_STR}", ""]

lines += ["━━━━━━━━━━", f"📊 一、排队情况（截止{QUEUE_DATE}）", ""]
if QUEUE_TOTALS:
    lines.append(f"全市场共{QUEUE_TOTALS['全市场']}家：问询{QUEUE_TOTALS['问询中']}家 | "
                  f"已过会待发行{QUEUE_TOTALS['已过会']}家 | 提交注册{QUEUE_TOTALS['提交注册']}家")
    lines.append("")
    for board, items in QUEUE.items():
        parts = " | ".join(f"{k}{v}" for k, v in items)
        lines.append(f"【{board}】{sum(v for _, v in items)}家  {parts}")
else:
    lines.append("排队总量与板块明细：暂未获取（未使用历史固定值替代实时统计）")

passed_r = recent_r[recent_r["审核状态"] == "上会通过"]
failed_r = recent_r[recent_r["审核状态"].isin(["上会未通过", "取消审核"])]
lines += ["", "━━━━━━━━━━", f"📋 二、上周上会（{REPORT_START}～{TODAY_STR}）", "",
          f"[OK] 通过：{len(passed_r)}家"]
for _, r in passed_r.iterrows():
    lines.append(f"  · {shname(r.get('企业名称', r.get('股票简称','?')))} | "
                 f"{board_alias(r.get('上市板块',''))} | {sdate(r['上会日期'])}")
if len(failed_r) > 0:
    lines.append(f"[FAIL] 否决：{len(failed_r)}家")
    for _, r in failed_r.iterrows():
        lines.append(f"  · {shname(r.get('企业名称', r.get('股票简称','?')))} | "
                     f"{board_alias(r.get('上市板块',''))}")

reg_up2 = recent_up[recent_up["最新状态"].isin(["注册", "核准"])].dropna(subset=["企业名称"])
lines += ["", "━━━━━━━━━━", f"📋 三、上周拿文（{REPORT_START}～{TODAY_STR}）", ""]
if len(reg_up2) > 0:
    lines.append(f"📄 获发行批文：{len(reg_up2)}家")
    for _, r in reg_up2.iterrows():
        lines.append(f"  · {shname(r.get('企业名称',''))} | "
                     f"{board_alias(r.get('拟上市地点',''))} | "
                     f"{str(r['更新日期'])[:10]}")
else:
    lines.append("  （暂无数据）")

term_up = recent_up[recent_up["最新状态"].isin(["终止"])].dropna(subset=["企业名称"])
lines += ["", "━━━━━━━━━━", f"📋 四、上周终止/撤回（{REPORT_START}～{TODAY_STR}）", ""]
if len(term_up) > 0:
    for _, r in term_up.iterrows():
        lines.append(f"  · {shname(r.get('企业名称',''))} | "
                     f"{board_alias(r.get('拟上市地点',''))}")
else:
    lines.append("  本周无终止撤回记录")

lines += ["", "━━━━━━━━━━", f"📋 五、本周上会计划（{THIS_WEEK_END}～{NEXT_WEEK_END}）", ""]
if len(next_r) > 0:
    for _, r in next_r.iterrows():
        lines.append(f"  · {shname(r.get('企业名称', r.get('股票简称','?')))} | "
                     f"{board_alias(r.get('上市板块',''))} | "
                     f"计划{sdate(r['上会日期'])}")
else:
    lines.append("  本周暂无上会安排")

lines += ["", "━━━━━━━━━━", f"📋 六、本周新股上市（{REPORT_START}～{TODAY_STR}）", ""]
if len(recent_l) > 0:
    for _, r in recent_l.iterrows():
        cd = str(r.get("证劵代码", ""))
        info = LISTINGS_GAIN.get(cd, {})
        if info:
            nm, dt, gain = info["name"], info["date"], info["gain"]
            pr = f"{info['price']:.2f}元"
        else:
            nm = r.get("证券简称", "?")
            dt = sdate(r["上市_dt"]) if pd.notna(r.get("上市_dt")) else "?"
            gain = "-"
            pr = fmt_price(r.get("发行价"))
        lines.append(f"  · {nm}（{cd}）| 上市:{dt} | 发行:{pr} | 涨幅:{gain}")
else:
    lines.append("  （无）")

lines += ["", "━━━━━━━━━━",
          f"📌 数据来源：新浪财经/AKShare公开接口（统计截至{QUEUE_DATE}；缺失字段不使用历史固定值补齐）",
          "仅供参考，不构成投资建议。"]

report = "\n".join(lines)
err = wx(report)
print(report)
print("\n" + ("[OK] 已推送" if err == 0 else f"[FAIL] err={err}"))
