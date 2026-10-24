"""
盘中预警脚本专用 — 聚合所有需要的工具函数
"""
import os, json, subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ── 读取 Webhook URL（优先 env.vars，回退 .ini 文件）───────────
_SCRIPT_DIR = Path(__file__).resolve().parent
_WORKSPACE_DIR = _SCRIPT_DIR.parents[2]
KEYS_DIR = os.environ.get("AGENT_KEYS_DIR", str(_WORKSPACE_DIR / "keys"))

def load_key(section: str, option: str) -> str:
    """优先从 env.vars 读取，回退到 .ini 文件"""
    # env.vars 映射
    env_map = {
        ("wecom_webhook", "key"): "WECOM_WEBHOOK_KEY",
        ("tushare", "token"): "TUSHARE_TOKEN",
    }
    env_var = env_map.get((section, option))
    if env_var:
        val = os.environ.get(env_var)
        if val:
            return val.strip()
    # 回退 .ini
    import configparser as cp
    path = os.path.join(KEYS_DIR, f"{section}.ini")
    cfg = cp.ConfigParser(delimiters=("=",), comment_prefixes=("#"))
    cfg.read(path, encoding="utf-8")
    try:
        return cfg.get(section, option).strip()
    except Exception:
        return ""

def get_webhook_url() -> str:
    key = load_key("wecom_webhook", "key")
    return f"https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={key}"

def get_tushare_token() -> str:
    """读取 Tushare token，优先 env.vars"""
    return os.environ.get("TUSHARE_TOKEN", "") or load_key("tushare", "token")

# ── Webhook 推送 ────────────────────────────────────────────────
def wx_push(text: str) -> int:
    payload = json.dumps({"msgtype": "text", "text": {"content": text}}, ensure_ascii=False)
    r = subprocess.run(
        ["curl", "-s", "-X", "POST", get_webhook_url(),
         "-H", "Content-Type: application/json", "-d", "@-"],
        input=payload.encode("utf-8"), capture_output=True
    )
    try:
        return json.loads(r.stdout.decode()).get("errcode", -1)
    except Exception:
        return -1

# ── 时间工具 ───────────────────────────────────────────────────
_TZ_OFFSET = timedelta(hours=8)  # 北京时区偏移

def now_bj():
    """北京时间（固定加8小时，不依赖系统timezone配置）"""
    return datetime.now(timezone.utc) + _TZ_OFFSET

def ts():
    """格式化的北京时间字符串"""
    return (datetime.now(timezone.utc) + _TZ_OFFSET).strftime("%Y-%m-%d %H:%M")

def is_trading_window():
    bj = now_bj()
    w = bj.weekday()
    if w >= 5:
        return False
    h, m = bj.hour, bj.minute
    morning = (h == 9 and m >= 30) or (10 <= h <= 11)
    afternoon = 13 <= h <= 15
    return morning or afternoon

# ── 去重状态 ───────────────────────────────────────────────────

def already_sent(state_file: str) -> bool:
    today = now_bj().strftime("%Y%m%d")
    f = os.path.join(str(_SCRIPT_DIR), state_file)
    return os.path.exists(f) and open(f).read().strip() == today

def mark_sent(state_file: str):
    f = os.path.join(str(_SCRIPT_DIR), state_file)
    with open(f, "w") as fp:
        fp.write(now_bj().strftime("%Y%m%d"))
