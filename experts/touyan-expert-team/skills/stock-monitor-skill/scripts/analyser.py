#!/usr/bin/env python3
"""
Stock Monitor Pro - 智能分析引擎
集成：新闻、资金流向、龙虎榜、宏观关联分析
"""

import requests
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict

class StockAnalyser:
    """股票智能分析器 - 结合多维度数据给出建议"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
    
    # ========== 1. 新闻舆情 ==========
    
    def fetch_eastmoney_news(self, symbol: str, name: str, limit: int = 5) -> List[Dict]:
        """新闻/公告不再用东方财富搜索摘要补事实。

        这里返回空列表，让上层报告明确“暂无可验证原文线索”，避免把搜索建议当新闻原文。
        """
        return []
    
    def fetch_sina_news(self, symbol: str, name: str) -> List[Dict]:
        """获取新浪财经个股新闻"""
        # 新浪新闻搜索接口
        url = f"https://search.sina.com.cn/?q={name}&c=news&sort=time"
        try:
            self.session.get(url, timeout=10)
            # 这里可以做更精细的HTML解析
            # 简化返回示例
            return [{"title": f"新浪财经-{name}相关新闻", "source": "新浪"}]
        except:
            return []
    
    def analyze_sentiment(self, news_list: List[Dict]) -> Dict:
        """简单情感分析"""
        positive_words = ['利好', '增长', '突破', '买入', '增持', '涨停', '超预期', '业绩大增']
        negative_words = ['利空', '减持', '下跌', '卖出', '亏损', '暴雷', '跌停', '不及预期']
        
        sentiment = {"positive": 0, "negative": 0, "neutral": 0, "summary": []}
        
        for news in news_list:
            title = news.get("title", "")
            p_count = sum(1 for w in positive_words if w in title)
            n_count = sum(1 for w in negative_words if w in title)
            
            if p_count > n_count:
                sentiment["positive"] += 1
            elif n_count > p_count:
                sentiment["negative"] += 1
            else:
                sentiment["neutral"] += 1
        
        # 生成情感摘要
        if sentiment["positive"] > sentiment["negative"]:
            sentiment["overall"] = "偏多"
        elif sentiment["negative"] > sentiment["positive"]:
            sentiment["overall"] = "偏空"
        else:
            sentiment["overall"] = "中性"
            
        return sentiment
    
    # ========== 2. 资金流向 ==========
    
    def fetch_fund_flow(self, symbol: str, market: str = "sz") -> Dict:
        """获取个股资金流向（AkShare 主源）。"""
        try:
            import akshare as ak
            df = ak.stock_individual_fund_flow(stock=symbol, market=market)
            if df is None or getattr(df, "empty", False):
                return {"status": "empty", "reason": "AkShare 未返回个股资金流"}
            row = df.tail(1).to_dict("records")[0]
            return {
                "status": "ok",
                "source": "AKShare stock_individual_fund_flow",
                "date": str(row.get("日期") or row.get("date") or ""),
                "main_net_inflow": row.get("主力净流入-净额"),
                "main_net_inflow_pct": row.get("主力净流入-净占比"),
                "super_large_net_inflow": row.get("超大单净流入-净额"),
                "large_net_inflow": row.get("大单净流入-净额"),
                "unit_note": "按 AkShare 返回列名原样输出；使用前必须确认单位"
            }
        except Exception as exc:
            return {"status": "failed", "reason": str(exc)}
    
    def fetch_northbound_flow(self) -> Dict:
        """北向资金占位。

        这里不能用指数行情字段伪装北向资金。北向资金请走 astock-report
        中的专门函数，并标注成交净买额/余额/最近可得交易日。
        """
        return {
            "status": "unavailable",
            "northbound": None,
            "reason": "未配置可验证北向资金接口；不得用指数行情字段替代北向资金"
        }
    
    # ========== 3. 龙虎榜 ==========
    
    def fetch_dragon_tiger(self, date: str = None) -> List[Dict]:
        """获取龙虎榜数据，统一调用 astock-report 的守门脚本。"""
        def _normalize_date(value: str = None) -> str:
            if not value:
                return datetime.now().strftime("%Y-%m-%d")
            s = str(value).strip()
            for fmt in ("%Y-%m-%d", "%Y%m%d"):
                try:
                    return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
                except ValueError:
                    continue
            raise ValueError("date must be YYYY-MM-DD or YYYYMMDD")

        target_date = _normalize_date(date)
        guard_script = Path(__file__).resolve().parents[2] / "astock-report" / "scripts" / "market_data_guard.py"
        try:
            proc = subprocess.run(
                [sys.executable, str(guard_script), "billboard", "--date", target_date, "--limit", "50", "--json"],
                check=False,
                text=True,
                capture_output=True,
                timeout=30,
            )
            payload = json.loads(proc.stdout or "{}")
            if payload.get("status") != "ok":
                return []
            return payload.get("rows") or []
        except Exception:
            return []
    
    # ========== 4. 宏观关联分析 ==========
    
    def analyze_gold_correlation(self, gold_price: float, stocks: List[Dict]) -> str:
        """分析金价与持仓股票的关联"""
        # 江西铜业等有色股与金价正相关
        correlation_map = {
            "600362": "强正相关",  # 江西铜业
            "601318": "弱相关",    # 中国平安
            "513180": "弱负相关",  # 恒生科技
            "159892": "弱相关",    # 恒生医疗
        }
        
        analysis = []
        for stock in stocks:
            code = stock.get("code")
            corr = correlation_map.get(code, "未知")
            if corr in ["强正相关", "中等正相关"]:
                analysis.append(f"📈 {stock['name']}: 与金价{corr}，金价上涨可能带动该股")
        
        return "\n".join(analysis) if analysis else "暂无强关联标的"
    
    # ========== 5. 综合分析 ==========
    
    def generate_insight(self, stock: Dict, price_data: Dict, alerts: List) -> str:
        """生成综合分析报告"""
        code = stock['code']
        name = stock['name']
        
        # 1. 获取新闻
        news_list = self.fetch_eastmoney_news(code, name)
        sentiment = self.analyze_sentiment(news_list)
        
        # 2. 资金流向
        self.fetch_fund_flow(code, stock.get('market', 'sz'))
        
        # 3. 构建报告
        report = f"""📊 <b>{name} ({code}) 深度分析</b>

💰 <b>价格异动:</b>
• 当前: {price_data.get('price', 'N/A')} ({price_data.get('change_pct', 0):+.2f}%)
• 触发: {', '.join([a[1] for a in alerts])}

📰 <b>舆情线索 ({sentiment.get('overall', '未知')}):</b>
• 可验证原文线索: {len(news_list)} 条
• 正面: {sentiment.get('positive', 0)} | 负面: {sentiment.get('negative', 0)}
"""
        
        # 添加最新新闻标题
        if news_list:
            report += "\n<b>待核实动态:</b>\n"
            for n in news_list[:2]:
                report += f"• {n.get('title', '无标题')[:30]}...\n"
        
        # 4. 给出风险提示
        suggestion = self._generate_suggestion(sentiment, alerts)
        report += f"\n💡 <b>风险提示:</b>\n{suggestion}"
        
        return report
    
    def _generate_suggestion(self, sentiment: Dict, alerts: List) -> str:
        """基于数据生成风险提示，避免输出交易动作。"""
        alert_types = [a[0] for a in alerts]
        overall = sentiment.get("overall", "中性")
        
        # 价格下跌 + 舆情偏空 = 谨慎
        if "below" in alert_types and overall == "偏空":
            return "[WARN] 价格跌破支撑位，且舆情偏空，短线风险偏高。"
        
        # 价格下跌 + 舆情偏多 = 可能是机会
        if "below" in alert_types and overall == "偏多":
            return "🔍 价格下跌但舆情偏多，可能是情绪错杀，关注是否有反弹机会。"
        
        # 价格突破 + 舆情偏多 = 确认趋势
        if "above" in alert_types and overall == "偏多":
            return "[提示] 价格突破且舆情配合，趋势可能延续，但需警惕追高波动。"
        
        # 大涨
        if "pct_up" in alert_types:
            return "📈 短期涨幅较大，注意获利了结风险。"
        
        # 大跌
        if "pct_down" in alert_types:
            return "📉 短期跌幅较大，波动风险上升。"
        
        return "⏳ 信号仍不充分，保持观察。"


# ========== 测试 ==========
if __name__ == '__main__':
    analyser = StockAnalyser()
    
    # 测试新闻抓取
    print("=== 新闻测试 ===")
    news = analyser.fetch_eastmoney_news("600362", "江西铜业")
    print(f"获取到 {len(news)} 条新闻")
    for n in news[:3]:
        print(f"  - {n.get('title', 'N/A')[:40]}...")
    
    # 测试情感分析
    print("\n=== 情感分析测试 ===")
    sentiment = analyser.analyze_sentiment(news)
    print(f"整体情绪: {sentiment.get('overall')}")
    print(f"正面: {sentiment.get('positive')}, 负面: {sentiment.get('negative')}")
    
    # 测试金价关联
    print("\n=== 宏观关联测试 ===")
    stocks = [{"code": "600362", "name": "江西铜业"}]
    corr = analyser.analyze_gold_correlation(2743, stocks)
    print(corr)
