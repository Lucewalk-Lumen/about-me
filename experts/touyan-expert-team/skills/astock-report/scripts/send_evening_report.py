#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A股收盘晚报生成脚本
触发：python3 send_evening_report.py [--dry-run]

数据一致性原则：
  两融余额、两融交易额 → 取最新可用日期（通常为 T-1）
  流通市值、成交额        → 必须与两融余额为同一日期
  两融交易额 = 融资买入额 + 融券卖出额
  流通市值 = 沪市流通市值 + 深市流通市值（沪深北三所合计）
"""
from __future__ import annotations
import sys, os, warnings, json, subprocess
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple
from pathlib import Path

warnings.filterwarnings('ignore')

SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = SCRIPT_DIR.parents[2]

_TZ  = timedelta(hours=8)
NOW  = datetime.now(timezone.utc) + _TZ
TODAY_STR  = NOW.strftime("%Y年%m月%d日")
TODAY_DATE = NOW.strftime("%Y%m%d")
TS         = NOW.strftime("%m/%d %H:%M")

def prev_trading_day(date_str: str) -> str:
    dt = datetime.strptime(date_str, "%Y%m%d")
    for i in range(1, 8):
        d = (dt - timedelta(days=i)).strftime("%Y%m%d")
        if datetime.strptime(d, "%Y%m%d").weekday() < 5:
            return d
    return date_str

YESTERDAY = prev_trading_day((NOW - timedelta(days=1)).strftime("%Y%m%d"))

def get_webhook_url() -> str:
    keys_dir = Path(os.environ.get('AGENT_KEYS_DIR', str(WORKSPACE_DIR / 'keys')))
    ini = keys_dir / 'wecom_webhook.ini'
    if os.path.exists(ini):
        with open(ini) as f:
            return f.read().strip()
    raise FileNotFoundError(f'Webhook配置不存在: {ini}')

def wx_push(text: str) -> int:
    payload = json.dumps({"msgtype": "text", "text": {"content": text}}, ensure_ascii=False)
    r = subprocess.run(['curl', '-s', '-X', 'POST', get_webhook_url(),
                        '-H', 'Content-Type: application/json', '-d', '@-'],
                       input=payload.encode('utf-8'), capture_output=True)
    try:
        return json.loads(r.stdout.decode()).get('errcode', -1)
    except Exception:
        return -1

def ai_supplement(data: dict) -> dict:
    missing = [k for k, v in data.items() if v is None]
    if missing:
        print(f"[数据兜底] 以下字段暂缺，不做AI补数：{', '.join(missing)}")
    return data

# ── 六大指数 ────────────────────────────────────────────────
def get_index_data():
    imap = {"上证指数":"sh000001","深证成指":"sz399001","创业板指":"sz399006",
            "科创50":"sh000688","沪深300":"sh000300","中证500":"sh000905"}
    try:
        import urllib.request
        req = urllib.request.Request(
            f"https://qt.gtimg.cn/q={','.join(imap.values())}",
            headers={"User-Agent":"Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            raw = r.read().decode("gbk", errors="replace")
        result = []
        for line in raw.strip().split("\n"):
            fields = line.lstrip("v_").split("~")
            if len(fields) < 33: continue
            code_num = fields[2].strip()
            pct = float(fields[32]) if fields[32] else 0.0
            for name, c in imap.items():
                if c.replace("sh","").replace("sz","") in code_num:
                    result.append({"name": name,
                                   "price": float(fields[3]) if fields[3] else 0.0,
                                   "pct": pct})
                    break
        return result
    except Exception as e:
        print(f"[指数] {e}"); return []

# ── PE与风险溢价 ─────────────────────────────────────────
def get_hs300_pe() -> Tuple[Optional[float], Optional[float]]:
    """
    沪深300 PE及近5年历史分位点。
    PE来源：腾讯 qt.gtimg.cn field[39]（sh000300）
    分位点：akshare stock_index_pe_lg（近5年历史分位）
    返回: (PE, 分位点%) 或 None
    """
    pe = None
    try:
        import urllib.request
        req = urllib.request.Request(
            "https://qt.gtimg.cn/q=sh000300",
            headers={"User-Agent":"Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as r:
            raw = r.read().decode("gbk", errors="replace")
        for line in raw.strip().split("\n"):
            f = line.lstrip("v_").split("~")
            if len(f) < 50 or '000300' not in f[2]: continue
            pe = float(f[39]) if f[39] else None
            if pe:
                print(f"  [沪深300PE] {pe:.2f}")
    except Exception as e:
        print(f"  [沪深300PE] [WARN] {e}")

    pct = None
    try:
        import akshare as ak
        df = ak.stock_index_pe_lg(symbol="沪深300")
        if df is not None and not df.empty:
            pct = float(df.iloc[0]['滚动市盈率分位点'] if '滚动市盈率分位点' in df.columns
                        else df.iloc[0].get('分位点', 0))
            print(f"  [沪深300PE分位] {pct:.1f}%")
    except Exception as e:
        print(f"  [沪深300PE分位] [WARN] {e}")

    return pe, pct

# ── PE + 国债收益率 ───────────────────────────────────────
# ── 核心数据获取 ──────────────────────────────────────────

def get_margin_balance_effective() -> Tuple[Optional[float], Optional[float], Optional[str]]:
    """
    两融余额（亿元）+ 较前日变化。
    两融余额 = 融资余额 + 融券余额（单位：亿元）。
    数据源：akshare stock_margin_account_info（无参数，全市场合计，列单位=亿元）。
    """
    try:
        import akshare as ak
        mg = ak.stock_margin_account_info()
        if mg is None or mg.empty:
            raise ValueError("empty")
        mg2 = mg.sort_values('日期', ascending=False).reset_index(drop=True)
        row = mg2.iloc[0]
        d   = str(row.get('日期', ''))  # YYYY-MM-DD
        cur = float(row.get('融资余额', 0) or 0) + float(row.get('融券余额', 0) or 0)
        pre_row = mg2.iloc[1] if len(mg2) > 1 else None
        pre = (float(pre_row['融资余额']) + float(pre_row['融券余额'])) if pre_row is not None else None
        delta = round(cur - pre, 0) if pre is not None else None
        ed = (datetime.strptime(d, "%Y-%m-%d") + _TZ).strftime("%Y年%m月%d日")
        print(f"  [两融余额] {ed}={cur:.0f}亿，较前日{'+' if (delta or 0)>=0 else ''}{delta:.0f}亿")
        return cur, delta, ed
    except Exception as e:
        print(f"  [两融余额] {e}"); return None, None, None

def get_margin_buy_effective(effective_date: str) -> Tuple[Optional[float], Optional[str]]:
    """
    两融交易额（亿元）= 融资买入额 + 融券卖出额。
    数据源：akshare stock_margin_account_info（无参数，全市场合计，列单位=亿元）。
    """
    try:
        import akshare as ak
        mg = ak.stock_margin_account_info()
        if mg is None or mg.empty:
            raise ValueError("empty")
        mg2 = mg.sort_values('日期', ascending=False).reset_index(drop=True)
        target = f"{effective_date[:4]}-{effective_date[4:6]}-{effective_date[6:8]}"
        row = next((r for _, r in mg2.iterrows()
                     if str(r.get('日期','')) == target), mg2.iloc[0])
        rz_buy  = float(row.get('融资买入额', 0) or 0)
        rz_sell = float(row.get('融券卖出额', 0) or 0)
        total = round(rz_buy + rz_sell, 1)
        d  = str(row.get('日期', ''))
        ed = (datetime.strptime(d, "%Y-%m-%d") + _TZ).strftime("%Y年%m月%d日")
        print(f"  [两融交易额] {ed}=融资{rz_buy:.1f}+融券{rz_sell:.1f}={total:.1f}亿")
        return total, ed
    except Exception as e:
        print(f"  [两融交易额] {e}"); return None, None

def _get_bse_turnover(effective_date: str) -> float:
    """
    北交所成交额（亿元）。
    数据源：akshare stock_bse_summary（单位：元 → ÷1e8）。
    北交所无独立接口时返回0（占比极小，不影响主逻辑）。
    """
    try:
        import akshare as ak
        df = ak.stock_bse_summary(date=effective_date)
        if df is None or df.empty:
            return 0.0
        bj_row = df[df['证券类别'] == '股票'].iloc[0]
        amt = float(bj_row.iloc[1]) / 1e8  # 元→亿
        print(f"  [北交所成交额] {amt:.1f}亿")
        return amt
    except Exception as e:
        print(f"  [北交所成交额] [WARN] {e}"); return 0.0

def get_turnover_effective(effective_date: str) -> Tuple[Optional[float], Optional[str]]:
    """
    A股成交额（亿元）。沪深北三所合计。

    逻辑：
    1. 当日(T日)：腾讯实时 API（沪+深，不含北交所，实时行情不含BSE）
    2. 历史：依次取沪市 + 深市 + 北交所 → 三所加总
       - 沪市：stock_sse_deal_daily['成交金额']，单位=万元 → ÷10000 = 亿
       - 深市：stock_szse_summary['成交金额']，单位=元   → ÷1e8  = 亿
       - 北交所：stock_bse_summary，单位=元              → ÷1e8  = 亿
    """
    if effective_date == TODAY_DATE:
        try:
            import urllib.request
            req = urllib.request.Request(
                "https://qt.gtimg.cn/q=sh000001,sz399001",
                headers={"User-Agent":"Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as r:
                raw = r.read().decode("gbk", errors="replace")
            sh = sz = 0.0
            for line in raw.strip().split("\n"):
                parts = line.split("~")
                if len(parts) < 38: continue
                amt = float(parts[37]) / 1e4  # 万元→亿
                if "000001" in parts[2]: sh = amt
                elif "399001" in parts[2]: sz = amt
            total = round(sh + sz, 0)
            ed = NOW.strftime("%Y年%m月%d日")
            print(f"  [成交额] {ed}（T日实时）=沪{sh:.0f}+深{sz:.0f}={total:.0f}亿={total/10000:.2f}万亿")
            return total, ed
        except Exception as e:
            print(f"  [成交额] 腾讯实时失败: {e}")

    try:
        import akshare as ak
        # 沪市：数据列单位=亿，直接使用（无需换算）
        df_sh = ak.stock_sse_deal_daily(date=effective_date)
        sh_row = df_sh[df_sh['单日情况'] == '成交金额']
        sh_turn = float(sh_row.iloc[0].get('股票', 0))  # 亿

        # 深市：元 ÷ 1e8 = 亿元
        df_sz = ak.stock_szse_summary(date=effective_date)
        sz_row = df_sz[df_sz['证券类别'] == '股票']
        sz_turn = float(sz_row.iloc[0].get('成交金额', 0)) / 1e8  # 元→亿

        # 北交所：元 ÷ 1e8 = 亿元
        bj_turn = _get_bse_turnover(effective_date)

        total = round(sh_turn + sz_turn + bj_turn, 0)
        ed = (datetime.strptime(effective_date, "%Y%m%d") + _TZ).strftime("%Y年%m月%d日")
        print(f"  [成交额] {ed}=沪{sh_turn:.0f}+深{sz_turn:.0f}+北交所{bj_turn:.0f}={total:.0f}亿={total/10000:.2f}万亿")
        return total, ed
    except Exception as e:
        print(f"  [成交额] [WARN] {effective_date}: {e}"); return None, None

def get_market_cap_effective(effective_date: str) -> Tuple[Optional[float], Optional[str]]:
    """
    A股流通市值（亿元）。沪深北三所合计。
    沪市：数据列单位=亿，直接使用（已包含主板A+科创板）
    深市：元 ÷ 1e8 = 亿元（已包含主板+创业板）
    """
    try:
        import akshare as ak
        # 沪市：数据列单位=亿，直接使用
        df_sh = ak.stock_sse_deal_daily(date=effective_date)
        sh_row = df_sh[df_sh['单日情况'] == '流通市值']
        sh_cap = float(sh_row.iloc[0].get('股票', 0))  # 亿

        # 深市：元 ÷ 1e8 = 亿元
        df_sz = ak.stock_szse_summary(date=effective_date)
        sz_row = df_sz[df_sz['证券类别'] == '股票']
        sz_cap = float(sz_row.iloc[0].get('流通市值', 0)) / 1e8  # 元→亿

        total = round(sh_cap + sz_cap, 0)
        ed = (datetime.strptime(effective_date, "%Y%m%d") + _TZ).strftime("%Y年%m月%d日")
        print(f"  [流通市值] {ed}=沪{sh_cap:.0f}+深{sz_cap:.0f}={total:.0f}亿={total/10000:.2f}万亿")
        return total, ed
    except Exception as e:
        print(f"  [流通市值] [WARN] {effective_date}: {e}"); return None, None

def get_north_bound():
    try:
        import akshare as ak
        df = ak.stock_hsgt_fund_flow_summary_em()
        nb = df[df['资金方向']=='北向'].sort_values('交易日', ascending=False)
        for _, row in nb.head(3).iterrows():
            val = row.get('今日净买入额-万元', 0)
            if val and val != 0:
                v = round(float(val) / 10000, 2)
                print(f"  [北向] {'净流入' if v>=0 else '净流出'}{abs(v)}亿")
                return v
        return None
    except Exception as e:
        print(f"  [北向] {e}"); return None

def get_market_stats():
    try:
        import akshare as ak
        for d in range(8):
            trade = (NOW - timedelta(days=d)).strftime('%Y%m%d')
            try:
                zt = len(ak.stock_zt_pool_em(date=trade))
                dt = len(ak.stock_zt_pool_dtgc_em(date=trade))
                if zt > 0 or dt > 0:
                    print(f"  [涨跌停] {trade} 涨停{zt} / 跌停{dt}")
                    return zt, dt
            except Exception:
                continue
        return None, None
    except Exception as e:
        print(f"  [涨跌停] {e}"); return None, None

def get_sector_flow():
    try:
        import akshare as ak
        df = ak.stock_sector_fund_flow_rank(indicator="今日")
        if df is None or df.empty: return []
        result = []
        for _, r in df.head(10).iterrows():
            try:
                name = str(r.get('名称', ''))
                flow = float(str(r.get('今日主力净流入', 0)).replace(',', ''))
                pct  = float(str(r.get('涨跌幅', 0)).replace('%', ''))
                if name and '连停' not in name:
                    result.append((name, pct, flow))
            except Exception:
                continue
        return result
    except Exception as e:
        print(f"  [行业资金] {e}"); return []

# ── 情绪参考 ──────────────────────────────────────────────

# ── PE + 国债收益率 + 风险溢价 ─────────────────────────────
def get_pe_and_bond() -> dict:
    """
    返回 {
        'hs300_pe': float,      # 沪深300 PE-TTM
        'hs300_pct5y': float,   # 沪深300 近5年历史分位（%）
        'zzqz_pe': float,       # 中证全指 PE-TTM
        'bond10y': float,      # 10年国债收益率（%）
        'rep_date': str,        # 国债收益率日期 YYYY-MM-DD
        'risk_premium': float,  # 股市风险溢价 = 1/中证全指PE - 10年国债收益率
    }
    数据源：
    - 沪深300 PE：中证指数 field[39]（腾讯 sh000300）
    - 中证全指 PE：中证指数 field[39]（腾讯 sh000985）
    - 沪深300 5年分位：akshare stock_index_pe_lg(symbol='沪深300')
    - 10年国债收益率：akshare bond_china_yield（曲线名称='中债国债收益率曲线'，10年列）
    """
    result = {'hs300_pe': None, 'hs300_pct5y': None,
              'zzqz_pe': None, 'bond10y': None,
              'rep_date': None, 'risk_premium': None}

    # 1. 国债收益率
    try:
        import akshare as ak
        for days_back in range(5):
            d = (datetime.now() - timedelta(days=days_back)).strftime('%Y%m%d')
            try:
                df = ak.bond_china_yield(start_date=d, end_date=d)
                if df is not None and not df.empty:
                    gov = df[df['曲线名称'] == '中债国债收益率曲线']
                    if not gov.empty:
                        row = gov.iloc[0]
                        col_10y = None
                        for c in ['10年', '10Y']:
                            if c in gov.columns:
                                try:
                                    v = float(str(row[c]))
                                    if v > 0: col_10y = v; break
                                except Exception: pass
                        if col_10y is not None:
                            result['bond10y'] = round(col_10y, 4)
                            result['rep_date'] = str(row['日期'])[:10]
                            break
            except Exception: continue
    except Exception as e:
        print(f"  [国债] {e}")

    # 2. 指数 PE（腾讯 field[39]）
    try:
        import urllib.request
        req = urllib.request.Request(
            'https://qt.gtimg.cn/q=sh000300,sh000985',
            headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=8) as r:
            raw = r.read().decode('gbk', errors='replace')
        for line in raw.strip().split('\n'):
            flds = line.lstrip('v_').split('~')
            if len(flds) < 50: continue
            code = flds[2].replace('sh', '').replace('sz', '')
            if code == '000300' and flds[39]:
                result['hs300_pe'] = round(float(flds[39]), 2)
            elif code == '000985' and flds[39]:
                result['zzqz_pe'] = round(float(flds[39]), 2)
    except Exception as e:
        print(f"  [PE] {e}")

    # 3. 沪深300 5年分位
    try:
        import akshare as ak
        df_pe = ak.stock_index_pe_lg(symbol='沪深300')
        if df_pe is not None and len(df_pe) >= 20:
            pe_col = None
            for c in df_pe.columns:
                if '滚动市盈率' in c and '等权' not in c:
                    pe_col = c; break
            if pe_col is None:
                for c in df_pe.columns:
                    if '市盈率' in c and '等权' not in c and '中位' not in c:
                        pe_col = c; break
            if pe_col:
                vals = df_pe[pe_col].astype(float).dropna()
                cur = result.get('hs300_pe')
                if cur and len(vals) >= 20:
                    pct = round((vals < cur).sum() / len(vals) * 100, 1)
                    result['hs300_pct5y'] = pct
    except Exception as e:
        print(f"  [分位] {e}")

    # 4. 风险溢价 = 1/中证全指PE - 10年国债收益率
    zz = result.get('zzqz_pe'); bond = result.get('bond10y')
    if zz and bond and zz > 0 and bond > 0:
        result['risk_premium'] = round((1 / zz - bond / 100) * 100, 2)

    if result.get('bond10y'):
        print(f"  [股市风险溢价] 中证全指PE={result['zzqz_pe']}, 10年国债={result['bond10y']}%, "
              f"风险溢价={result.get('risk_premium')}%")

    return result



def calc_mood(zt, north):
    sc = []
    if zt is not None:
        sc.append(15 if zt>=150 else 12 if zt>=100 else 9 if zt>=60 else 5 if zt>=30 else 2 if zt>=10 else 0)
    if north is not None:
        sc.append(20 if north>=100 else 15 if north>=50 else 10 if north>=20 else 6 if north>=0 else 3 if north>=-50 else 0)
    if not sc: return "数据暂缺"
    avg = sum(sc) / len(sc)
    return f"{'[热]' if avg>=12 else '[温]' if avg>=8 else '[平]' if avg>=5 else '[冷]'} 情绪初估"

# ── PE + 国债收益率 + 风险溢价 ──────────────────────────────
def build_report(indices, data, today_str, ai_news=None, ai_action=None):
    rz_ed = data.get('rz_bal_date'); mc_ed = data.get('mkt_cap_date')
    to_ed = data.get('turnover_date')
    lines = [f"📋 【A股晚报】{today_str}\n"]

    if indices:
        lines.append("━━━ A股收盘 ━━━")
        for x in indices:
            p = x.get('pct', 0)
            lines.append(f"• {x['name']}：{x['price']:.1f}，{'↑' if p>=0 else '↓'}{abs(p):.2f}%")
        if to_ed and data.get('turnover'):
            lines.append(f"• 成交额（{to_ed}）：{data['turnover']/10000:.2f}万亿元")

    lines += ["\n━━━ 亚太股市 ━━━",
               "• 恒生指数：暂未获取",
               "• 日经225：暂未获取",
               "• 韩国综合：暂未获取"]

    rz = data.get('rz_bal'); rb = data.get('rz_buy')
    mc = data.get('mkt_cap'); to = data.get('turnover')
    delta = data.get('rz_delta')
    lines.append("\n━━━ 市场风险偏好 ━━━")
    if rz is not None and rz_ed:
        delta_str = f"，较前日{'+' if (delta or 0)>=0 else ''}{delta:.0f}亿" if delta is not None else ""
        lines.append(f"• 两融余额（{rz_ed}）：{rz:.0f}亿{delta_str}")
    else:
        lines.append("• 两融余额：暂缺")

    if rz is not None and mc is not None and mc > 0 and mc_ed:
        ratio1 = rz / mc * 100
        alert = ">3.2% 预警区 | >3.5% 高危区" if ratio1 > 3.2 else ""
        lines.append(f"• 两融余额/A股流通市值（{rz_ed}）= {rz:.0f}亿 / {mc:.0f}亿 = {ratio1:.2f}%")
        if alert:
            lines.append(f"  {alert}")
    else:
        lines.append("• 两融余额/A股流通市值：数据暂缺")

    if rb is not None and to is not None and to > 0 and to_ed:
        ratio2 = rb / to * 100
        judgement = "保守" if ratio2 < 7 else ("中性" if ratio2 <= 11 else "过热")
        lines += [
            f"• 两融交易额/A股成交额（{to_ed}）= {rb:.1f}亿 / {to:.0f}亿 = {ratio2:.1f}%",
            "  阈值：<7%保守 | 7-11%中性 | >11%过热",
            f"  → 比例={ratio2:.1f}% → {judgement}",
        ]
    else:
        lines.append("• 两融交易额/A股成交额：数据暂缺")

    # PE + 国债收益率 + 风险溢价
    pe = data.get('pe_data', {})
    if pe.get('risk_premium') is not None:
        rp_judge = "高估" if pe['risk_premium'] < 3 else ("中性" if pe['risk_premium'] <= 6 else "低估")
        rep_dt = pe.get('rep_date') or ''
        if rep_dt and len(rep_dt) == 10:
            y, m, d = rep_dt.split('-')
            rep_dt_fmt = f"{y}年{m}月{d}日"
        else:
            rep_dt_fmt = rep_dt

        zz = pe.get('zzqz_pe'); bond = pe.get('bond10y'); rp = pe['risk_premium']
        lines += [
            f"• 股市风险溢价=1/中证全指PE-{rep_dt_fmt}10年国债收益率=1/{zz:.1f}-{bond:.2f}%={rp:.2f}%",
            "  阈值：<3%高估 | 3-6%中性 |>6%低估",
            f"  → 溢价率={rp:.2f}% → {rp_judge}",
        ]
    else:
        lines.append("• 股市风险溢价：数据暂缺")

    hs300_pe = pe.get('hs300_pe')
    hs300_pct = pe.get('hs300_pct5y')
    if hs300_pe:
        pct_str = f"{hs300_pct:.1f}%" if hs300_pct else "N/A"
        lines.append(f"• 沪深300PE={hs300_pe:.1f}（近5年历史分位点={pct_str}）")
    else:
        lines.append("• 沪深300PE：数据暂缺")

    if ai_news:
        lines.append("\n━━━ 财经要闻 ━━━"); lines.extend(ai_news)
    else:
        lines += ["\n━━━ 财经要闻 ━━━", "暂未获取可追溯新闻来源，本段不输出推断内容。"]
    if ai_action:
        lines.append("\n━━━ 明日操作建议 ━━━"); lines.extend(ai_action)
    else:
        lines += ["\n━━━ 明日操作建议 ━━━",
                   "缺少可验证新闻和资金面数据，本次不输出具体操作建议。"]
    lines.append("\n免责声明：仅供参考，不构成投资建议。股市有风险，投资需谨慎。")
    return "\n".join(lines)

# ── 主流程 ───────────────────────────────────────────────
def main(ai_fill: bool = False):
    print(f"\n[{TS}] 晚报数据获取开始...")
    rz_bal, rz_delta, rz_bal_date = get_margin_balance_effective()
    effective_date = (rz_bal_date.replace('年','').replace('月','').replace('日','')
                      if rz_bal_date else YESTERDAY)
    rz_buy,  rz_buy_date  = get_margin_buy_effective(effective_date)
    turnover, to_date       = get_turnover_effective(effective_date)
    mkt_cap, mc_date       = get_market_cap_effective(effective_date)
    indices = get_index_data()
    north   = get_north_bound()
    zt, dt  = get_market_stats()
    sectors = get_sector_flow()
    pe_data = get_pe_and_bond()
    data = {
        'north': north, 'zt_count': zt, 'dt_count': dt,
        'rz_bal': rz_bal, 'rz_delta': rz_delta, 'rz_bal_date': rz_bal_date,
        'rz_buy': rz_buy, 'rz_buy_date': rz_buy_date,
        'turnover': turnover, 'turnover_date': to_date,
        'mkt_cap': mkt_cap, 'mkt_cap_date': mc_date,
        'sectors': sectors,
        'pe_data': pe_data,
    }
    if ai_fill and any(v is None for k, v in data.items()
                       if k not in ('north','zt_count','dt_count','sectors','rz_delta')):
        data = ai_supplement(data)
    print(f"\n[{TS}] 数据汇总:")
    for k, v in [('两融余额',data['rz_bal']),('两融交易额',data['rz_buy']),
                  ('流通市值',data['mkt_cap']),('成交额',data['turnover'])]:
        print(f"  {k}：{v}")
    report = build_report(indices, data, TODAY_STR)
    print("\n" + "=" * 50); print(report); print("=" * 50)
    return report

if __name__ == "__main__":
    dry_run = '--dry-run' in sys.argv
    if '--ai-fill' in sys.argv:
        print(f"[{TS}] --ai-fill 已禁用：数值字段不得由AI搜索补齐")
    report  = main(ai_fill=False)
    if not dry_run and report:
        err = wx_push(report)
        print(f"\n[{TS}] {'[OK] 已推送' if err == 0 else f'[FAIL] 失败(err={err})'}")
