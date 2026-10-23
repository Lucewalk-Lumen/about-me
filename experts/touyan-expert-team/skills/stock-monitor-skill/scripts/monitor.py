#!/usr/bin/env python3
"""
自选股监控预警工具 - OpenClaw集成版
支持 A股、ETF 及 国际现货黄金 (伦敦金)
"""

import requests
import json
import time
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

# ============ 配置区 ============

# 监控列表由用户或上层运行时注入。模板不内置个人持仓、成本或阈值。

# 标的类型定义
STOCK_TYPE = {
    "INDIVIDUAL": "individual",  # 个股
    "ETF": "etf",                # ETF
    "GOLD": "gold"               # 黄金/贵金属
}

WATCHLIST = []

# 智能频率配置
SMART_SCHEDULE = {
    "market_open": {"hours": [(9, 30), (11, 30), (13, 0), (15, 0)], "interval": 300},  # 交易时间: 5分钟
    "after_hours": {"interval": 1800},  # 收盘后: 30分钟
    "night": {"hours": [(0, 0), (8, 0)], "interval": 3600},  # 凌晨: 1小时(仅伦敦金)
}

# ============ 核心代码 ============

class StockAlert:
    def __init__(self):
        self.prev_data = {}
        self.alert_log = []
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0"})
        
    def should_run_now(self):
        """智能频率控制: 判断当前是否应该执行监控 (基于北京时间)"""
        now = datetime.now(ZoneInfo("Asia/Shanghai"))
        hour, minute = now.hour, now.minute
        time_val = hour * 100 + minute
        weekday = now.weekday()
        
        # 周末只监控伦敦金
        if weekday >= 5:  # 周六日
            return {"run": True, "mode": "weekend", "stocks": [s for s in WATCHLIST if s['market'] == 'fx']}
        
        # 交易时间 (9:30-11:30, 13:00-15:00)
        morning_session = 930 <= time_val <= 1130
        afternoon_session = 1300 <= time_val <= 1500
        
        if morning_session or afternoon_session:
            return {"run": True, "mode": "market", "stocks": WATCHLIST, "interval": 300}
        
        # 午休 (11:30-13:00)
        if 1130 < time_val < 1300:
            return {"run": True, "mode": "lunch", "stocks": WATCHLIST, "interval": 600}  # 10分钟
        
        # 收盘后 (15:00-24:00)
        if 1500 <= time_val <= 2359:
            return {"run": True, "mode": "after_hours", "stocks": WATCHLIST, "interval": 1800}  # 30分钟
        
        # 凌晨 (0:00-9:30)
        if 0 <= time_val < 930:
            return {"run": True, "mode": "night", "stocks": [s for s in WATCHLIST if s['market'] == 'fx'], "interval": 3600}  # 1小时
        
        return {"run": False}

    def _fetch_akshare_hist(self, symbol, days=30):
        """获取 AkShare 日 K，不复权。"""
        try:
            import akshare as ak
            df = ak.stock_zh_a_hist(
                symbol=str(symbol),
                period="daily",
                start_date="19900101",
                end_date="20500101",
                adjust="",
            )
            if df is None or getattr(df, "empty", False):
                return None
            return df.tail(days)
        except Exception as e:
            print(f"AkShare日K获取失败 {symbol}: {e}")
            return None

    def fetch_akshare_kline(self, symbol, market):
        """获取最新日K线数据；保留旧函数名以兼容调用，实际走 AkShare。"""
        df = self._fetch_akshare_hist(symbol, days=2)
        try:
            if df is not None and len(df) >= 1:
                today = df.iloc[-1]
                prev = df.iloc[-2] if len(df) >= 2 else today
                return {
                    'name': str(symbol),
                    'price': float(today['收盘']),
                    'prev_close': float(prev['收盘']),
                    'open': float(today['开盘']),
                    'high': float(today['最高']),
                    'low': float(today['最低']),
                    'volume': int(float(today['成交量'])),
                    'amount': float(today['成交额']),
                    'date': str(today['日期']),
                    'time': '15:00:00',
                    'source': 'AKShare stock_zh_a_hist（日K不复权）',
                    'snapshot_type': 'daily_close',
                    'source_note': 'AkShare 日K收盘快照，仅作实时接口失败后的降级数据，不等同连续竞价实时价',
                    'adjustment': '不复权',
                    'prev_high': float(prev['最高']),
                    'prev_low': float(prev['最低']),
                    'market_fields_verified': True,
                }
        except Exception as e:
            print(f"AkShare日K解析失败 {symbol}: {e}")
        return None

    def fetch_volume_ma5(self, symbol, market):
        """获取5日平均成交量"""
        df = self._fetch_akshare_hist(symbol, days=6)
        try:
            if df is not None and len(df) >= 2:
                volumes = [float(v) for v in df.iloc[:-1]['成交量'].tolist()]
                return sum(volumes) / len(volumes) if volumes else 0
        except Exception as e:
            print(f"获取均量失败 {symbol}: {e}")
        return 0

    def fetch_ma_data(self, symbol, market):
        """获取均线数据 (MA5, MA10, MA20) 和 RSI"""
        df = self._fetch_akshare_hist(symbol, days=30)
        try:
            if df is not None and len(df) >= 20:
                closes = [float(v) for v in df['收盘'].tolist()]
                
                # 计算均线
                ma5 = sum(closes[-5:]) / 5
                ma10 = sum(closes[-10:]) / 10
                ma20 = sum(closes[-20:]) / 20
                
                # 判断均线趋势
                prev_ma5 = sum(closes[-6:-1]) / 5
                prev_ma10 = sum(closes[-11:-1]) / 10
                
                # 计算RSI(14)
                rsi = self._calculate_rsi(closes, 14)
                
                return {
                    'MA5': ma5,
                    'MA10': ma10,
                    'MA20': ma20,
                    'MA5_trend': 'up' if ma5 > prev_ma5 else 'down',
                    'MA10_trend': 'up' if ma10 > prev_ma10 else 'down',
                    'golden_cross': prev_ma5 <= prev_ma10 and ma5 > ma10,
                    'death_cross': prev_ma5 >= prev_ma10 and ma5 < ma10,
                    'RSI': rsi,
                    'RSI_overbought': rsi > 70 if rsi else False,
                    'RSI_oversold': rsi < 30 if rsi else False
                }
        except Exception as e:
            print(f"获取均线失败 {symbol}: {e}")
        return None
    
    def _calculate_rsi(self, closes, period=14):
        """计算RSI指标"""
        if len(closes) < period + 1:
            return None
        
        gains = []
        losses = []
        
        for i in range(1, period + 1):
            change = closes[-i] - closes[-i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return round(rsi, 2)

    def fetch_sina_realtime(self, stocks):
        """获取实时行情 (优先实时，收盘后用日K)"""
        stock_list = [s for s in stocks if s['market'] != 'fx']
        fx_list = [s for s in stocks if s['market'] == 'fx']
        results = {}
        
        # 1. A股/ETF - 先走数据守门脚本，AkShare 主源 + 至少一个核验源
        if stock_list:
            guard_script = Path(__file__).resolve().parents[2] / "astock-report" / "scripts" / "market_data_guard.py"
            for stock in stock_list:
                code = stock['code']
                suffix = stock.get('market', '').upper()
                symbol = f"{code}.{suffix}" if suffix in {"SH", "SZ", "BJ"} else code
                try:
                    proc = subprocess.run(
                        [sys.executable, str(guard_script), "quote", symbol, "--json"],
                        check=False,
                        text=True,
                        capture_output=True,
                        timeout=35,
                    )
                    payload = json.loads(proc.stdout or "{}")
                    quote = payload.get("quote") or {}
                    if payload.get("status") == "ok" and quote.get("price"):
                        price = float(quote["price"])
                        change = quote.get("change")
                        kline_data = self.fetch_akshare_kline(code, 1 if stock['market'] == 'sh' else 0) or {}
                        prev_close = price - float(change) if change is not None else kline_data.get('prev_close', price)
                        market_fields_verified = bool(kline_data)
                        results[code] = {
                            'name': quote.get('name') or stock['name'],
                            'price': price,
                            'prev_close': prev_close,
                            'open': kline_data.get('open'),
                            'high': kline_data.get('high'),
                            'low': kline_data.get('low'),
                            'volume': kline_data.get('volume', 0),
                            'amount': kline_data.get('amount', 0),
                            'date': str(quote.get('time', '')).split(' ')[0],
                            'time': str(quote.get('time', '')).split(' ')[-1],
                            'source': quote.get('primary_source', 'AKShare + verifier'),
                            'snapshot_type': 'realtime_verified',
                            'prev_high': kline_data.get('prev_high'),
                            'prev_low': kline_data.get('prev_low'),
                            'market_fields_verified': market_fields_verified,
                        }
                except Exception as e:
                    print(f"守门行情获取失败 {code}: {e}")
            
            # 2. 如果实时核验失败，用 AkShare 日K线补状态，但明确标为非实时
            for stock in stock_list:
                code = stock['code']
                if code not in results or results[code]['price'] <= 0:
                    kline_data = self.fetch_akshare_kline(code, 1 if stock['market'] == 'sh' else 0)
                    if kline_data:
                        results[code] = kline_data
                        print(f"  {stock['name']}: 使用 AkShare 日K收盘快照 {kline_data['price']}（非实时）")

        # 3. 伦敦金（新浪 hf_XAU，美元/盎司）
        if fx_list:
            url = "https://hq.sinajs.cn/list=hf_XAU"
            try:
                resp = self.session.get(url, headers={'Referer': 'https://finance.sina.com.cn'}, timeout=10)
                line = resp.text.strip()
                if '"' in line:
                    data_str = line[line.index('"')+1 : line.rindex('"')]
                    p = data_str.split(',')
                    if len(p) >= 13:
                        # 新浪 hf_XAU 返回现货黄金美元/盎司报价。
                        price = float(p[0])
                        results['XAU'] = {
                            'name': '伦敦金', 
                            'price': price, 
                            'prev_close': float(p[7]),
                            'volume': 0, 'amount': 0, 
                            'date': p[12] if len(p) > 12 else datetime.now(ZoneInfo("Asia/Shanghai")).strftime('%Y-%m-%d'),
                            'time': p[6],
                            'unit': 'USD/oz',
                            'source': '新浪财经 hf_XAU',
                            'snapshot_type': 'realtime'
                        }
            except Exception as e: 
                print(f"伦敦金获取失败: {e}")
            
        return results
    
    def check_alerts(self, stock_config, data):
        """检查预警条件 (支持成本百分比、单日涨跌幅、分级预警)"""
        alerts = []
        alert_weights = []  # 用于计算预警级别
        code = stock_config['code']
        cfg = stock_config.get('alerts', {})
        cost = stock_config.get('cost', 0)
        stock_type = stock_config.get('type', 'individual')
        price, prev_close = data['price'], data['prev_close']
        change_pct = (price - prev_close) / prev_close * 100 if prev_close else 0
        
        # 1. 基于成本的百分比预警 (权重: 高)
        if cost > 0:
            cost_change_pct = (price - cost) / cost * 100
            
            if 'cost_pct_above' in cfg and cost_change_pct >= cfg['cost_pct_above']:
                target_price = cost * (1 + cfg['cost_pct_above']/100)
                if not self._alerted_recently(code, 'cost_above'):
                    alerts.append(('cost_above', f"🎯 盈利 {cfg['cost_pct_above']:.0f}% (目标价 ¥{target_price:.2f})"))
                    alert_weights.append(3)  # 高权重
            
            if 'cost_pct_below' in cfg and cost_change_pct <= cfg['cost_pct_below']:
                target_price = cost * (1 + cfg['cost_pct_below']/100)
                if not self._alerted_recently(code, 'cost_below'):
                    alerts.append(('cost_below', f"🛑 亏损 {abs(cfg['cost_pct_below']):.0f}% (风险线 ¥{target_price:.2f})"))
                    alert_weights.append(3)  # 高权重
        
        # 2. 基于固定价格的预警 (权重: 中)
        if 'price_above' in cfg and price >= cfg['price_above'] and not self._alerted_recently(code, 'above'):
            alerts.append(('above', f"[突破] 价格突破 ¥{cfg['price_above']}"))
            alert_weights.append(2)
        if 'price_below' in cfg and price <= cfg['price_below'] and not self._alerted_recently(code, 'below'):
            alerts.append(('below', f"📉 价格跌破 ¥{cfg['price_below']}"))
            alert_weights.append(2)
        
        # 3. 单日涨跌幅预警 (权重: 根据幅度)
        if 'change_pct_above' in cfg and change_pct >= cfg['change_pct_above'] and not self._alerted_recently(code, 'pct_up'):
            alerts.append(('pct_up', f"📈 日内大涨 {change_pct:+.2f}%"))
            # 异动越大权重越高
            if change_pct >= 7:
                alert_weights.append(3)  # 涨停附近
            elif change_pct >= 5:
                alert_weights.append(2)  # 大涨
            else:
                alert_weights.append(1)  # 一般异动
                
        if 'change_pct_below' in cfg and change_pct <= cfg['change_pct_below'] and not self._alerted_recently(code, 'pct_down'):
            alerts.append(('pct_down', f"📉 日内大跌 {change_pct:+.2f}%"))
            if change_pct <= -7:
                alert_weights.append(3)  # 跌停附近
            elif change_pct <= -5:
                alert_weights.append(2)  # 大跌
            else:
                alert_weights.append(1)  # 一般异动
        
        # 4. 成交量异动检测 (仅股票和ETF)
        if stock_type != 'gold' and 'volume_surge' in cfg:
            current_volume = data.get('volume', 0)
            if current_volume > 0:
                # 尝试获取5日均量
                ma5_volume = self.fetch_volume_ma5(code, 1 if stock_config['market'] == 'sh' else 0)
                if ma5_volume > 0:
                    volume_ratio = current_volume / ma5_volume
                    threshold = cfg['volume_surge']
                    
                    if volume_ratio >= threshold and not self._alerted_recently(code, 'volume_surge'):
                        alerts.append(('volume_surge', f"📊 放量 {volume_ratio:.1f}倍 (5日均量)"))
                        alert_weights.append(2)  # 中等权重
                    elif volume_ratio <= 0.5 and not self._alerted_recently(code, 'volume_shrink'):
                        alerts.append(('volume_shrink', f"📉 缩量 {volume_ratio:.1f}倍 (5日均量)"))
                        alert_weights.append(1)  # 低权重
        
        # 5. 均线系统 (MA金叉死叉)
        if stock_type != 'gold' and cfg.get('ma_monitor', True):
            ma_data = self.fetch_ma_data(code, 1 if stock_config['market'] == 'sh' else 0)
            if ma_data:
                # 金叉: MA5上穿MA10 (短期转强)
                if ma_data.get('golden_cross') and not self._alerted_recently(code, 'ma_golden'):
                    alerts.append(('ma_golden', f"🌟 均线金叉 (MA5¥{ma_data['MA5']:.2f}上穿MA10¥{ma_data['MA10']:.2f})"))
                    alert_weights.append(3)  # 高权重
                
                # 死叉: MA5下穿MA10 (短期转弱)
                if ma_data.get('death_cross') and not self._alerted_recently(code, 'ma_death'):
                    alerts.append(('ma_death', f"[WARN] 均线死叉 (MA5¥{ma_data['MA5']:.2f}下穿MA10¥{ma_data['MA10']:.2f})"))
                    alert_weights.append(3)  # 高权重
                
                # RSI超买超卖检测
                rsi = ma_data.get('RSI')
                if rsi:
                    if ma_data.get('RSI_overbought') and not self._alerted_recently(code, 'rsi_high'):
                        alerts.append(('rsi_high', f"🔥 RSI超买 ({rsi})，可能回调"))
                        alert_weights.append(2)
                    elif ma_data.get('RSI_oversold') and not self._alerted_recently(code, 'rsi_low'):
                        alerts.append(('rsi_low', f"❄️ RSI超卖 ({rsi})，可能反弹"))
                        alert_weights.append(2)
        
        # 5. 跳空缺口检测 (需要昨日数据)
        if stock_type != 'gold' and data.get('market_fields_verified'):
            prev_high = data.get('prev_high', 0)
            prev_low = data.get('prev_low', 0)
            current_open = data.get('open', price)  # 当前价近似开盘价
            
            # 向上跳空: 今日开盘 > 昨日最高
            if prev_high > 0 and current_open > prev_high * 1.01:  # 1%以上算跳空
                gap_pct = (current_open - prev_high) / prev_high * 100
                if not self._alerted_recently(code, 'gap_up'):
                    alerts.append(('gap_up', f"⬆️ 向上跳空 {gap_pct:.1f}%"))
                    alert_weights.append(2)
            
            # 向下跳空: 今日开盘 < 昨日最低
            elif prev_low > 0 and current_open < prev_low * 0.99:
                gap_pct = (prev_low - current_open) / prev_low * 100
                if not self._alerted_recently(code, 'gap_down'):
                    alerts.append(('gap_down', f"⬇️ 向下跳空 {gap_pct:.1f}%"))
                    alert_weights.append(2)
        
        # 6. 动态回撤风险提示 (当盈利达到一定幅度后启动)
        if cost > 0:
            profit_pct = (price - cost) / cost * 100
            
            # 当盈利 >= 10% 时，启动移动止盈
            if profit_pct >= 10:
                # 计算回撤幅度 (从最高点回撤)
                high_since_cost = data.get('high', price)
                drawdown = (high_since_cost - price) / high_since_cost * 100 if high_since_cost > cost else 0
                
                # 回撤5%风险提示
                if drawdown >= 5 and not self._alerted_recently(code, 'trailing_stop_5'):
                    alerts.append(('trailing_stop_5', f"📉 利润回撤 {drawdown:.1f}%，风险升高"))
                    alert_weights.append(2)
                
                # 回撤10%强风险提示
                elif drawdown >= 10 and not self._alerted_recently(code, 'trailing_stop_10'):
                    alerts.append(('trailing_stop_10', f"🚨 利润回撤 {drawdown:.1f}%，需复核仓位风险"))
                    alert_weights.append(3)
        
        # 6. 计算预警级别
        level = self._calculate_alert_level(alerts, alert_weights, stock_type)
        
        return alerts, level
    
    def _calculate_alert_level(self, alerts, weights, stock_type):
        """计算预警级别: info(提醒) / warning(警告) / critical(紧急)"""
        if not alerts:
            return None
        
        total_weight = sum(weights)
        alert_count = len(alerts)
        
        # 紧急: 多条件共振 或 高权重单一条件
        if total_weight >= 5 or alert_count >= 3:
            return "critical"
        
        # 警告: 中等权重 或 2个条件
        if total_weight >= 3 or alert_count >= 2:
            return "warning"
        
        # 提醒: 单一低权重条件
        return "info"
    
    def _alerted_recently(self, code, atype):
        now = time.time()
        self.alert_log = [l for l in self.alert_log if now - l['t'] < 1800] # 30分钟有效期
        for l in self.alert_log:
            if l['c'] == code and l['a'] == atype: return True
        return False
    
    def record_alert(self, code, atype):
        self.alert_log.append({'c': code, 'a': atype, 't': time.time()})
    
    def fetch_news(self, symbol):
        """新闻必须走可追溯原文来源；这里不再用搜索摘要或个股概况接口补新闻。"""
        return []

    def run_once(self, smart_mode=True):
        """执行监控 (支持智能频率)"""
        if smart_mode:
            schedule = self.should_run_now()
            if not schedule.get("run"):
                return []
            
            stocks_to_check = schedule.get("stocks", WATCHLIST)
            mode = schedule.get("mode", "normal")
            
            # 只在特定模式打印日志
            if mode in ["market", "weekend"]:
                print(f"[{datetime.now().strftime('%H:%M')}] {mode}模式扫描 {len(stocks_to_check)} 只标的...")
        else:
            stocks_to_check = WATCHLIST
        
        data_map = self.fetch_sina_realtime(stocks_to_check)
        triggered = []
        
        for stock in stocks_to_check:
            code = stock['code']
            if code not in data_map: continue
            
            data = data_map[code]
            
            # 数据有效性检查
            if data['price'] <= 0 or data['prev_close'] <= 0:
                continue
            
            alerts, level = self.check_alerts(stock, data)
            
            if alerts:
                change_pct = (data['price'] - data['prev_close']) / data['prev_close'] * 100 if data['prev_close'] else 0
                
                # 中国习惯: 红色=上涨, 绿色=下跌
                if change_pct > 0:
                    color_emoji = "[红涨]"  # 红涨
                elif change_pct < 0:
                    color_emoji = "[绿跌]"  # 绿跌
                else:
                    color_emoji = "⚪"
                
                # 预警级别标识
                level_icons = {
                    "critical": "🚨",  # 紧急
                    "warning": "[WARN]",   # 警告
                    "info": "📢"       # 提醒
                }
                level_icon = level_icons.get(level, "📢")
                level_text = {"critical": "【紧急】", "warning": "【警告】", "info": "【提醒】"}.get(level, "")
                
                msg = f"<b>{level_icon} {level_text}{color_emoji} {stock['name']} ({code})</b>\n"
                msg += "━━━━━━━━━━━━━━━━━━━━\n"
                price_label = "当前价格" if data.get('snapshot_type') in {'realtime', 'realtime_verified'} else "日K快照"
                source_text = data.get('source', '行情源')
                time_text = f"{data.get('date', '')} {data.get('time', '')}".strip()
                msg += f"💰 {price_label}: <b>{data['price']:.2f}</b> ({change_pct:+.2f}%)\n"
                msg += f"🕒 数据来源: {source_text} | {time_text or '时间暂缺'}\n"
                
                # 显示持仓盈亏
                cost = stock.get('cost', 0)
                if cost > 0:
                    cost_change = (data['price'] - cost) / cost * 100
                    profit_icon = "红+" if cost_change > 0 else "绿"
                    msg += f"📊 持仓成本: ¥{cost:.2f} | 盈亏: {profit_icon}{cost_change:.2f}%\n"
                
                msg += f"\n🎯 触发预警 ({len(alerts)}项):\n"
                for _, text in alerts: 
                    msg += f"  • {text}\n"
                    self.record_alert(code, _)
                
                # Pro版：集成智能分析
                try:
                    from analyser import StockAnalyser
                    analyser = StockAnalyser()
                    insight = analyser.generate_insight(stock, {
                        'price': data['price'],
                        'change_pct': change_pct
                    }, alerts)
                    msg += f"\n{insight}"
                except Exception:
                    pass
                
                triggered.append(msg)
        
        return triggered

if __name__ == '__main__':
    monitor = StockAlert()
    for alert in monitor.run_once():
        print(alert)
