#!/usr/bin/env python3
"""
A股报告推送公共模块
提供：企业微信推送、时间判断、去重状态管理
"""
import subprocess, json, os, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from keys_loader import get_webhook_url

WEBHOOK_URL = ""

def load_config():
    global WEBHOOK_URL
    try:
        WEBHOOK_URL = get_webhook_url()
    except Exception as e:
        print(f"[FAIL] 读取 Webhook URL 失败: {e}")
        sys.exit(1)

def wx_push(text: str) -> int:
    load_config()
    payload = json.dumps({"msgtype": "text", "text": {"content": text}}, ensure_ascii=False)
    r = subprocess.run(
        ["curl", "-s", "-X", "POST", WEBHOOK_URL,
         "-H", "Content-Type: application/json", "-d", "@-"],
        input=payload.encode("utf-8"), capture_output=True)
    try:
        return json.loads(r.stdout.decode()).get("errcode", -1)
    except Exception:
        return -1

def wx_push_markdown(text: str) -> int:
    load_config()
    payload = json.dumps({"msgtype": "markdown", "markdown": {"content": text}}, ensure_ascii=False)
    r = subprocess.run(
        ["curl", "-s", "-X", "POST", WEBHOOK_URL,
         "-H", "Content-Type: application/json", "-d", "@-"],
        input=payload.encode("utf-8"), capture_output=True)
    try:
        return json.loads(r.stdout.decode()).get("errcode", -1)
    except Exception:
        return -1

def is_trading_day() -> bool:
    now_bj = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=8)))
    return now_bj.weekday() < 5

def is_trading_window():
    now_bj = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=8)))
    w = now_bj.weekday()
    if w >= 5:
        return False
    h, m = now_bj.hour, now_bj.minute
    morning = (h == 9 and m >= 30) or (10 <= h <= 11)
    afternoon = 13 <= h <= 15
    return morning or afternoon

def already_sent(state_file: str) -> bool:
    today = datetime.now(timezone(timedelta(hours=8))).strftime("%Y%m%d")
    f = os.path.join(os.path.dirname(__file__), state_file)
    return os.path.exists(f) and open(f).read().strip() == today

def mark_sent(state_file: str):
    f = os.path.join(os.path.dirname(__file__), state_file)
    with open(f, "w") as fp:
        fp.write(datetime.now(timezone(timedelta(hours=8))).strftime("%Y%m%d"))

def now_bj():
    return datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=8)))

def ts():
    return now_bj().strftime("%Y-%m-%d %H:%M")


def get_ipo_report_period(ref_date=None):
    """
    周期：当前周周三 ~ 下周一（固定6天）。

    找包含 ref_date 的当前周周三作为周期起点：
      offset = 0 if Mon else (weekday - 2) % 7
      Mon=0, Tue=1, Wed=6, Thu=0, Fri=2, Sat=3, Sun=4

    Returns:
        (period_start: datetime, period_end: datetime,
         period_start_str: str, period_end_str: str)
    """
    if ref_date is None:
        ref_date = now_bj()
    w = ref_date.weekday()
    offset = (w - 3) % 7
    period_start = ref_date - timedelta(days=offset)
    period_end   = period_start + timedelta(days=6)
    return period_start, period_end, period_start.strftime("%m月%d日"), period_end.strftime("%m月%d日")
