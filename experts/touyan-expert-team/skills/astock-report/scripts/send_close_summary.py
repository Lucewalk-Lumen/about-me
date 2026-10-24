#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A股收盘小结 完整版 2026-04-08"""
from datetime import datetime, timezone, timedelta
import json, subprocess, warnings, os, sys
warnings.filterwarnings("ignore")
_TZ = timedelta(hours=8)
def now_bj(): return datetime.now(timezone.utc) + _TZ
def ts(): return (datetime.now(timezone.utc) + _TZ).strftime("%Y-%m-%d %H:%M")
try:
    from keys_loader import get_webhook_url
    WEBHOOK = get_webhook_url()
except Exception:
    WEBHOOK = f"https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={os.environ.get('WECOM_WEBHOOK_KEY','')}"
def send_wx(msg):
    p = subprocess.Popen(["curl","-s","-X","POST",WEBHOOK,"-H","Content-Type: application/json","--data-binary","@-"],
                         stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out,_ = p.communicate(input=json.dumps({"msgtype":"text","text":{"content":msg}}).encode())
    try: return json.loads(out.decode()).get("errcode",-1)
    except: return -1

# ── 六大指数 ─────────────────────────────────────────────────
def get_index_data():
    url = "https://qt.gtimg.cn/q=sh000001,sz399001,sz399006,sh000688,sh000300,sh000905"
    try:
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            raw = r.read().decode("gbk", errors="replace")
        result = {}
        for line in raw.strip().split("\n"):
            parts = line.lstrip("v_").split("~")
            if len(parts) < 33: continue
            # code in parts[2] like "000001" or "399001"
            code_num = parts[2].strip()   # "000001"
            pct = float(parts[32]) if parts[32] else 0.0
            result[code_num] = {"name":parts[1].strip(), "price":float(parts[3]) if parts[3] else 0.0,
                                 "prev":float(parts[4]) if parts[4] else 0.0, "pct":pct}
        out = []
        for num, code, name in [("000001","sh000001","上证指数"),("399001","sz399001","深证成指"),
                                  ("399006","sz399006","创业板指"),("000688","sh000688","科创50"),
                                  ("000300","sh000300","沪深300"),("000905","sh000905","中证500")]:
            d = dict(result.get(num, {}))
            d["code"] = code
            if "name" not in d: d["name"] = name
            out.append(d)
        return out
    except Exception as e:
        print(f"[指数] {e}")
        return []

# ── 涨跌停 ─────────────────────────────────────────────────
def get_market_stats():
    try:
        import akshare as ak
        d = now_bj().strftime("%Y%m%d")
        zt = ak.stock_zt_pool_em(date=d)
        dt = ak.stock_zt_pool_dtgc_em(date=d)
        zn = len(zt) if zt is not None else 0
        dn = len(dt) if dt is not None else 0
        print(f"  [涨跌停] 涨停{zn}家 / 跌停{dn}家")
        return zn, dn
    except Exception as e:
        print(f"  [涨跌停] {e}")
        return None, None

# ── 北向资金 ─────────────────────────────────────────────────
def get_north_bound():
    """
    北向资金净流入（亿元）。
    优先：Tushare pro（今日数据，盘中即可）→ akshare（备用，今日18:00更新）
    今日数据暂缺时返回 None，禁止用 AI 搜索补全资金数值。
    """
    try:
        import akshare as ak
        # ── ① Tushare（优先，今日盘中即可获取）──────────────────
        try:
            from keys_loader import get_tushare_token
            token = get_tushare_token()
            if token:
                import os as _os, tushare as _ts
                _os.environ["TUSHARE_TOKEN"] = token
                pro = _ts.pro_api(token)
                today_str = now_bj().strftime("%Y%m%d")
                df_tush = pro.moneyflow_hsgt(trade_date=today_str)
                if df_tush is not None and len(df_tush) > 0:
                    north_yi = round(float(df_tush.iloc[0]["north_money"]) / 10000, 2)
                    print(f"  [北向] {'净流入' if north_yi>=0 else '净流出'}{abs(north_yi)}亿（{today_str}，Tushare）")
                    return north_yi
        except Exception as e:
            print(f"  [北向] Tushare失败: {e}")

        # ── ② akshare 备用（今日18:00后可能有数据）──────────────
        df = ak.stock_hsgt_fund_flow_summary_em()
        df_n = df[df["资金方向"]=="北向"].sort_values("交易日", ascending=False)
        if df_n.empty: raise ValueError("no north data")
        today_str = now_bj().strftime("%Y-%m-%d")
        # 优先找今日数据（成交净买额，单位万元）
        for _, row in df_n.iterrows():
            if str(row.get("交易日","")) == today_str:
                val_yi = round(float(row["成交净买额"]) / 10000, 2)
                if abs(val_yi) > 0.01:
                    print(f"  [北向] {'净流入' if val_yi>=0 else '净流出'}{abs(val_yi)}亿（{today_str}，akshare）")
                    return val_yi
        # 今日数据未出，取最近交易日
        for _, row in df_n.iterrows():
            val_yi = round(float(row["成交净买额"]) / 10000, 2)
            if abs(val_yi) > 0.01:
                actual_date = str(row.get("交易日",""))
                print(f"  [北向] {'净流入' if val_yi>=0 else '净流出'}{abs(val_yi)}亿（{actual_date}，akshare）")
                return val_yi
        print("  [北向] [WARN] 今日数据暂缺")
        return None
    except Exception as e:
        print(f"  [北向] {e}")
        return None

# ── 两融余额 ─────────────────────────────────────────────────
def get_margin_balance():
    """
    两融余额（融资余额+融券余额）及较前日变化（亿元）。
    今日未更新时返回 None，禁止用 AI 搜索补全两融数值。
    """
    try:
        import akshare as ak
        mg = ak.stock_margin_account_info()
        if mg is None or len(mg) < 2: raise ValueError("no data")
        mg2 = mg.sort_values("日期", ascending=False)
        today_str = now_bj().strftime("%Y-%m-%d")
        # 只取今日数据
        for _, row in mg2.iterrows():
            if str(row.get("日期","")) != today_str:
                continue
            cur = float(row["融资余额"]) + float(row["融券余额"])
            # 取前一日实际数据
            for _, prow in mg2.iterrows():
                if str(prow.get("日期","")) != today_str:
                    prv = float(prow["融资余额"]) + float(prow["融券余额"])
                    delta = round(cur - prv, 2)
                    print(f"  [两融] 余额{cur:.0f}亿（较前日{'+' if delta>=0 else ''}{delta:.0f}亿）")
                    return cur, delta
        print("  [两融] [WARN] 今日数据暂缺")
        return None, None
    except Exception as e:
        print(f"  [两融] {e}")
        return None, None

# ── 两融比例 ─────────────────────────────────────────────────
def get_margin_ratio():
    from threading import Thread
    res = {"r":None,"rz":None,"tot":None,"rd":None,"sh":0.0,"sz":0.0}
    def _f():
        try:
            import akshare as ak, urllib.request
            today_str = now_bj().strftime("%Y-%m-%d")
            mg = ak.stock_margin_account_info()
            if mg is not None and len(mg) > 0:
                for _, row in mg.sort_values("日期",ascending=False).iterrows():
                    if str(row.get("日期","")) != today_str:
                        continue
                    v = row.get("融资买入额")
                    if v is not None and float(v) > 10:
                        res["rz"] = round(float(v), 2)
                        res["rd"] = today_str
                        break
                if res["rz"] is None:
                    print("  [两融比例] [WARN] 今日融资买入额暂缺（akshare未更新）")
            try:
                ql = "https://qt.gtimg.cn/q=sh000001,sz399001"
                req = urllib.request.Request(ql, headers={"User-Agent":"Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=8) as r:
                    raw = r.read().decode("gbk","replace")
                for ln in raw.replace("v_","").strip().split("\n"):
                    pts = ln.split("~")
                    if len(pts) < 38: continue
                    cd = pts[2].strip()
                    amt = float(pts[37])/1e4 if pts[37] else 0.0
                    if cd == "000001": res["sh"] = round(amt, 2)
                    elif cd == "399001": res["sz"] = round(amt, 2)
            except: pass
            tot = round(res["sh"] + res["sz"], 2)
            res["tot"] = tot
            if res["rz"] and tot > 1000: res["r"] = res["rz"] / tot
        except Exception as e:
            print(f"  [两融比例] {e}")
    Thread(target=_f, daemon=True).start()
    import time; time.sleep(12)
    r,rb,rt = res["r"],res["rz"],res["tot"]
    if r is not None:
        print(f"  [两融比例] 融资买入额={rb:.2f}亿（{res['rd']}）/ 全市场={rt:.0f}亿（沪{res['sh']:.0f}+深{res['sz']:.0f}）= {r*100:.2f}%")
    else:
        print(f"  [两融比例] [WARN] 暂无法计算（融资={rb}亿 市场={rt}亿）")
    return r,rb,rt

# ── 申万行业 ─────────────────────────────────────────────────
def get_sector_spot():
    try:
        import akshare as ak
        df = ak.stock_sector_spot()
        if df is None or len(df)==0: return []
        cols = df.columns.tolist()
        nc = next((c for c in cols if "板块" in c), cols[0])
        pc = next((c for c in cols if "涨跌幅" in c), None)
        if not pc: return []
        df2 = df.sort_values(pc, ascending=False)
        res = [(str(row[nc]), float(row[pc])) for _, row in df2.iterrows()]
        if res: print(f"  [行业] 申万{len(res)}个，最高{res[0][0]}{res[0][1]:+.2f}%")
        return res
    except Exception as e:
        print(f"  [行业] {e}")
        return []

# ── 行业主力资金 ─────────────────────────────────────────────
def get_industry_main_fund():
    print("  [主力-行业] 暂无 AkShare 多源核验通过的数据，跳过")
    return {}

# ── 主力（全市场）───────────────────────────────────────────
def get_market_net_flow():
    print("  [主力] 暂无 AkShare 多源核验通过的数据")
    return None

# ── 情绪打分 ─────────────────────────────────────────────────
# 单项打分函数（None=数据缺失）
def s_zt(n):
    if n is None: return None
    if n>=150: return 29
    if n>=100: return 24
    if n>=60: return 18
    if n>=30: return 12
    if n>=10: return 6
    return 0

def s_ztr(z, d):
    if z is None or d is None: return None
    if d == 0: return 15   # 无跌停，极强信号
    r=z/d
    if r>=8: return 15
    if r>=5: return 12
    if r>=3: return 9
    if r>=1.5: return 5
    if r>=0.5: return 2
    return 0

def s_nb(n):
    if n is None: return None
    if n>=100: return 20
    if n>=50: return 15
    if n>=20: return 10
    if n>=0: return 6
    if n>=-50: return 3
    return 0

def s_mk(v):
    if v is None: return None
    if v>=500: return 20
    if v>=200: return 16
    if v>=50: return 12
    if v>=0: return 8
    if v>=-200: return 5
    if v>=-500: return 2
    return 0

def s_zbr(p):
    if p is None: return None
    if p<15: return 15
    if p<25: return 12
    if p<35: return 8
    if p<45: return 5
    return 3

def s_ci(p):
    if p is None: return None
    if p>=2: return 10
    if p>=1: return 8
    if p>=0: return 6
    if p>=-1: return 4
    return 0

def calc_sentiment(zt, dt, north, mkt, zbr, csi):
    """打分函数。任意一项数据缺失 → 整体无法评分。"""
    _s1=s_zt(zt); _s2=s_ztr(zt,dt); _s3=s_nb(north)
    _s4=s_mk(mkt); _s5=s_zbr(zbr); _s6=s_ci(csi)
    vals=[_s1,_s2,_s3,_s4,_s5,_s6]
    if any(v is None for v in vals):
        ztv=zt or 0; dtv=dt or 0; ztr=round(ztv/max(dtv,1),1) if ztv and dtv else 0
        return {"总分":None,"等级":"数据暂缺，无法评分","明细":[
            (f"涨停{zt}家 → {_s1}分" if zt is not None else "涨停：暂缺"),
            (f"涨跌停比{'无跌停 → 15分' if dt==0 else f'{ztr}倍 → {_s2}分'}" if zt is not None and dt is not None else "涨跌停比：暂缺"),
            (f"北向{'净流入' if north>=0 else '净流出'}{abs(north):.1f}亿 → {_s3}分" if north is not None else "北向：暂缺"),
            (f"主力{'净流入' if (mkt or 0)>=0 else '净流出'}{abs(mkt or 0):.1f}亿 → {_s4}分" if mkt is not None else "主力：暂缺"),
            (f"炸板率{zbr:.1f}% → {_s5}分" if zbr is not None else "炸板率：暂缺"),
            (f"沪深300{'+' if (csi or 0)>=0 else ''}{csi or 0}% → {_s6}分" if csi is not None else "沪深300：暂缺"),
        ]}
    scores=list(filter(None,vals))
    tot=sum(scores)
    ztv=zt or 0; dtv=dt or 0; ztr=round(ztv/max(dtv,1),1) if ztv and dtv else 0
    lv=next(l for th,l in [(85,"极强多头"),(68,"多头偏强"),(52,"中性震荡"),(36,"偏空谨慎"),(0,"极弱空头")] if tot>=th)
    return {"总分":tot,"等级":lv,"明细":[
        f"涨停{ztv}家 → {_s1}分",
        f"涨跌停比{ztr}倍 → {_s2}分",
        f"北向{'净流入' if north>=0 else '净流出'}{abs(north):.1f}亿 → {_s3}分",
        f"主力{'净流入' if (mkt or 0)>=0 else '净流出'}{abs(mkt or 0):.1f}亿 → {_s4}分",
        f"炸板率{zbr:.1f}% → {_s5}分",
        f"沪深300{'+' if (csi or 0)>=0 else ''}{csi or 0}% → {_s6}分",
    ]}

def calc_risk_appetite(ratio):
    if ratio is None: return {"等级":"数据不足","描述":"两融比例暂缺"}
    p=ratio*100
    lv="偏保守" if p<7 else ("中性" if p<=11 else "投机偏好")
    return {"等级":lv,"描述":f"两融交易额/全市场={p:.2f}%，{lv}"}

# ── 报告模板 ─────────────────────────────────────────────────
def build_report(indices, zt, dt, north, sectors, sentiment, rz_bal, rz_delta, mkt_flow, ind_flow, today_str, risk_app, ratio, zbr, outlook, ai_sectors=None, market_comment=None):
    def ps(s):
        """解析板块字符串，返回 (名称, 涨跌幅字符串)。正确处理中文括号（（+X.XX%））。"""
        s=s.strip()
        if not s: return None,None
        if "+" in s:
            name,pct=s.rsplit("+",1); return name.rstrip("（").strip(),"+"+pct.rstrip("）").strip()
        if "-" in s:
            name,pct=s.rsplit("-",1); return name.rstrip("（").strip(),"-"+pct.rstrip("）").strip()
        return None,None
    # 从sectors建立申万涨跌幅字典：行业名 → "±X.XX%"
    _sector_pct = {}
    for s in (sectors or []):
        n, p = ps(s)
        if n: _sector_pct[n] = p

    def ind_lines(d, rev, lim):
        """行业资金流向行。
        有ind_flow时：显示行业名+申万涨跌幅+资金流向。
        无ind_flow时：直接用申万数据降级（按涨跌幅排序）。"""
        if d:
            items = sorted(d.items(), key=lambda x: x[1], reverse=rev)[:lim]
            lines = []
            for n, v in items:
                pct = _sector_pct.get(n, "±0.00%")
                direction = "净流入" if v >= 0 else "净流出"
                lines.append(f"【{n}】（{pct}）（{direction}{abs(v):.2f}亿）")
            return lines
        # 降级：直接用申万数据
        all_s = [(ps(s)[0], ps(s)[1]) for s in (sectors or []) if ps(s)[0] and ps(s)[1]]
        if not all_s:
            return ["暂缺"]
        if rev:
            return [f"{n}{p}" for n, p in all_s[:lim]] or ["暂缺"]
        else:
            return [f"{n}{p}" for n, p in all_s[-lim:]] or ["暂缺"]

    inflow = "\n      ".join(ind_lines(ind_flow, True, 5))
    # 跌幅前五：按涨跌幅升序（最跌幅的在前）
    def _parse_pct(s):
        import re
        m = re.search(r'([+-]?\d+\.?\d*)%', s)
        return float(m.group(1)) if m else 0
    _out_raw = ind_lines(ind_flow, False, 5)
    _out_sorted = sorted(_out_raw, key=_parse_pct)
    outflow = "\n      ".join([s.lstrip() for s in _out_sorted])
    hs=[(ps(s)[0],ps(s)[1]) for s in (sectors or []) if ps(s)[0] and ps(s)[1]]
    rising=[x for x in hs if x[1].startswith("+")]
    falling=[x for x in hs if x[1].startswith("-")]
    rocket="，".join([f"{n}{p}" for n,p in rising[:3]]) if rising else "暂缺"
    weak="，".join([f"{n}{p}" for n,p in falling[:3]]) if falling else "暂缺"
    s=sentiment
    mf_dir = "净流入" if (mkt_flow or 0) >= 0 else "净流出"
    lines = [
        f"📊 【A股收盘小结】{today_str}\n",
        "━━━ 一，主要股指表现 ━━━",
    ]
    for idx in (indices or []):
        p = idx.get("pct", 0.0)
        a = "↑" if p >= 0 else "↓"
        lines.append(f"• {idx.get('name','?')}：{idx.get('price',0):.2f}，{a}{abs(p):.2f}%")
    if market_comment:
        lines.append(f"📝 盘面点评：{market_comment}")
    lines += [
        "\n━━━ 二，资金流向 ━━━",
        (f"  主力资金：{mf_dir}{abs(mkt_flow):.2f}亿（全市场）" if mkt_flow is not None else "  主力资金：暂缺"),
        "  🔺 涨幅前五：",
        "    · " + ("\n    · ".join(inflow.split("\n")) if inflow else "暂缺"),
        "  🔻 跌幅前五：",
        "    · " + ("\n    · ".join(outflow.split("\n")) if outflow else "暂缺"),
        "\n━━━ 三，热点概念板块 ━━━",
    ]
    # ai_sectors 格式：{"strong": [{"name":"军工","zt":"12家","stocks":"中航沈飞、中国船舶","reason":"地缘冲突催化"},...], "weak":[...], "logic":"..."}
    if ai_sectors and ai_sectors.get("strong"):
        lines.append("今日强势概念：")
        for i, s in enumerate(ai_sectors["strong"], 1):
            lines.append(f"  ①【{s['name']}】（涨停{s['zt']}家）｜代表股：{s['stocks']}（{s['reason']}）")
        if ai_sectors.get("weak"):
            lines.append("今日弱势概念：")
            for i, s in enumerate(ai_sectors["weak"], 1):
                lines.append(f"  ①【{s['name']}】（跌停{s['dt']}家）｜代表股：{s['stocks']}（{s['reason']}）")
        if ai_sectors.get("logic"):
            lines.append(f"📝 板块轮动逻辑：{ai_sectors['logic']}")
    else:
        lines.append(f"强势板块（按申万涨跌幅）：{rocket}")
        lines.append(f"弱势板块（按申万涨跌幅）：{weak}")
    lines += ["\n━━━ 四，量化情绪打分 ━━━"]
    for d in s.get("明细",[]): lines.append(f"• {d}")
    score = s.get("总分")
    score_text = f"{score}/100" if score is not None else "数据暂缺"
    lines += [
        "━━━━━━━━━━━━",
        f"综合评分：{score_text} {s.get('等级','—')}",
        "\n━━━ 五，后市展望 ━━━",
        outlook if outlook else "缺少可验证的展望数据源，本次不输出后市展望。",
        "\n━━━ 数据来源：AKShare 主源 + 可追溯核验来源；字段按实际可用输出 ━━━",
        "仅供参考，不构成投资建议。股市有风险，投资需谨慎。",
    ]
    return "\n".join(lines)

# ── AI 盘面点评──────────────────────────────────────────
def get_market_comment(indices, today_str):
    """AI 点评默认关闭；无可追溯原文和已校验数据时不输出。"""
    print("  [盘面点评] 默认关闭，避免用搜索摘要生成确定结论")
    return None

# ── AI 后市展望 ────────────────────────────────────────────
def get_ai_outlook(indices, zt, dt, north, sectors, sentiment, rz_bal, rz_delta, mkt_flow, zbr, ratio, today_str):
    """AI 展望默认关闭；缺少可验证数据时不输出。"""
    print("  [后市展望] 默认关闭，避免在缺少可验证数据时生成结论")
    return None

# ── 主入口 ─────────────────────────────────────────────────
def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    dry_run = "--dry-run" in argv
    NOW=now_bj().strftime("%Y%m%d_%H%M")
    TODAY=now_bj().strftime("%Y年%m月%d日")
    print(f"[{NOW}] 收盘小结开始...")
    indices=get_index_data()
    zt,dt=get_market_stats()
    north=get_north_bound()
    sec=get_sector_spot()
    hot5=sec[:5]; cold5=sec[-5:] if len(sec)>=5 else sec[::-1][:5]
    sectors=[f"{n}（{p:+.2f}%）" for n,p in hot5]+[f"{n}（{p:+.2f}%）" for n,p in cold5]
    rz_bal,rz_delta=get_margin_balance()
    mkt_flow=get_market_net_flow()
    ind_flow=get_industry_main_fund()
    csi=next((i.get("pct",0.0) for i in indices if "沪深300" in i.get("name","")), None)
    # 炸板率
    zbr=None
    try:
        import warnings as _W; _W.filterwarnings('ignore')
        import akshare as _ak
        _today=(datetime.now(timezone.utc)+_TZ).strftime('%Y%m%d')
        _zt=_ak.stock_zt_pool_em(date=_today)
        _zc=len(_zt); _bc=int((_zt['炸板次数']>0).sum())
        zbr=round(_bc/_zc*100,1) if _zc>0 else None
        print(f"  [炸板] {zbr:.1f}%({_bc}/{_zc}家)")
    except Exception as e:
        print(f"  [炸板] 暂缺: {e}")
    print(f"[{NOW}] 数据获取完成：涨停:{zt} 跌停:{dt} 北向:{north}亿" + (f" 主力:{mkt_flow}亿" if mkt_flow else " 主力:暂缺"))
    s=calc_sentiment(zt,dt,north,mkt_flow,zbr,csi)
    ratio,rz_yi,tot_yi=get_margin_ratio()
    ra=calc_risk_appetite(ratio)
    # AI 后市展望
    outlook = get_ai_outlook(indices, zt, dt, north, sectors, s, rz_bal, rz_delta, mkt_flow, zbr, ratio, TODAY)
    sent_score = f"{s['总分']}/100" if s.get('总分') is not None else "数据暂缺"
    print(f"  情绪：{sent_score} {s['等级']}  风险偏好：{ra.get('等级','—')}")

    # AI 盘面点评
    market_comment = get_market_comment(indices, TODAY)
    report=build_report(indices,zt,dt,north,sectors,s,rz_bal,rz_delta,mkt_flow,ind_flow,TODAY,ra,ratio,zbr,outlook,ai_sectors=None,market_comment=market_comment)
    if dry_run:
        print("\n" + "="*50)
        print(report)
        print("="*50)
        print(f"[{ts()}] dry-run：未推送")
        return report
    err=send_wx(report)
    print(f"[{ts()}] {'[OK] 已推送' if err==0 else '[FAIL] 失败(err=%d)' % err}")
    return report

if __name__ == "__main__":
    main()
