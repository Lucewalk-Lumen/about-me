#!/usr/bin/env python3
# Copyright (c) 2026 ByteDance
# Licensed under the MIT License. See LICENSE file in the project root for details.
"""
Retrieve structured A-share market data with AKShare.

This module provides command handlers for leaderboard data, limit-up and
sentiment data, capital-flow data, and report-oriented scheduled workflows.
"""

import argparse
import importlib
import json
import os
import sys
import time
from datetime import datetime, timedelta

ak = None
pd = None


# ==================== 工具函数 ====================

DEFAULT_SOURCE = "AKShare/东方财富"


class DependencyError(RuntimeError):
    """Raised when a required runtime dependency is unavailable."""

    def __init__(self, package_name):
        self.package_name = package_name
        super().__init__(
            f"Missing dependency: {package_name}. Install dependencies with `pip install -r requirements.txt`."
        )


def current_timestamp():
    """统一的当前时间格式"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def ensure_runtime_dependencies():
    """Load runtime dependencies only when a command is executed."""
    global ak, pd

    if ak is None:
        try:
            ak = importlib.import_module("akshare")
        except ModuleNotFoundError as exc:
            raise DependencyError("akshare") from exc

    if pd is None:
        try:
            pd = importlib.import_module("pandas")
        except ModuleNotFoundError as exc:
            raise DependencyError("pandas") from exc


def get_latest_trade_date(date_str=None):
    """获取最近交易日，如果传入日期则直接使用"""
    if date_str:
        return date_str
    today = datetime.now()
    # 周末回退到周五
    if today.weekday() == 5:
        today -= timedelta(days=1)
    elif today.weekday() == 6:
        today -= timedelta(days=2)
    return today.strftime("%Y%m%d")


def retry_call(func, max_retries=3, delay=2, **kwargs):
    """带重试的接口调用，应对东方财富偶发连接重置"""
    for i in range(max_retries):
        try:
            return func(**kwargs)
        except Exception as e:
            if i < max_retries - 1 and (
                "RemoteDisconnected" in str(e) or "Connection" in str(e)
            ):
                time.sleep(delay * (i + 1))
                continue
            raise e


def format_output(data, source=DEFAULT_SOURCE, extra_info=None):
    """统一输出格式"""
    result = {
        "success": True,
        "source": source,
        "update_time": current_timestamp(),
        "data": data,
        "disclaimer": "数据来自AKShare（东方财富），可能延迟15分钟，仅供参考，不构成投资建议。",
    }
    if extra_info:
        result["info"] = extra_info
    return result


def format_error(msg, command, suggestion=None, error_type="data_error"):
    """统一错误输出"""
    return {
        "success": False,
        "error": msg,
        "error_type": error_type,
        "command": command,
        "suggestion": suggestion or "请检查日期是否为交易日，或稍后重试",
    }


def format_dependency_error(package_name, command):
    """Return a friendly CLI error for missing runtime dependencies."""
    result = format_error(
        f"Missing required dependency `{package_name}`.",
        command,
        suggestion="Run `pip install -r requirements.txt` and retry the command.",
        error_type="missing_dependency",
    )
    result["details"] = {"missing_package": package_name, "cwd": os.getcwd()}
    return result


def normalize_value(value):
    """清洗 DataFrame 中不可直接序列化或语义不明确的值"""
    if hasattr(value, "item") and not isinstance(
        value, (str, bytes, dict, list, tuple, set)
    ):
        try:
            value = value.item()
        except Exception:
            pass

    try:
        if pd.isna(value):
            return None
    except Exception:
        pass

    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")

    if pd is not None and isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d %H:%M:%S")

    return value


def df_to_records(df, limit=None):
    """DataFrame 转 records，可选限制条数"""
    if df is None or df.empty:
        return []
    records = []
    for row in df.to_dict(orient="records"):
        records.append({key: normalize_value(value) for key, value in row.items()})
    if limit:
        return records[:limit]
    return records


def build_section(
    data=None, status="ok", source=DEFAULT_SOURCE, error_message=None, extra_info=None
):
    """统一 section 输出结构，便于上层任务判断是否可继续分析"""
    section = {
        "status": status,
        "source": source,
        "fetched_at": current_timestamp(),
        "data": data if data is not None else [],
    }
    if error_message:
        section["error_message"] = error_message
    if extra_info:
        section["info"] = extra_info
    return section


def build_report_payload(task_type, trade_date, sections, facts=None):
    """统一 report 输出结构，强调 section 级状态与准确性边界"""
    status_map = {
        name: section.get("status", "unknown") for name, section in sections.items()
    }
    failed_sections = [
        name for name, status in status_map.items() if status == "failed"
    ]
    partial_sections = [
        name for name, status in status_map.items() if status == "partial"
    ]
    empty_sections = [name for name, status in status_map.items() if status == "empty"]

    if failed_sections and len(failed_sections) == len(sections):
        overall_status = "failed"
    elif failed_sections or partial_sections:
        overall_status = "partial"
    else:
        overall_status = "ok"

    return {
        "task_type": task_type,
        "trade_date": trade_date,
        "generated_at": current_timestamp(),
        "overall_status": overall_status,
        "section_status": status_map,
        "failed_sections": failed_sections,
        "partial_sections": partial_sections,
        "empty_sections": empty_sections,
        "facts": facts or {},
        "analysis_constraints": [
            "仅允许基于 sections 中 status=ok 或 partial 且 data 非空的数据进行分析",
            "若某 section 为 empty 或 failed，后续任务必须明确告知用户暂无数据或取数失败",
            "禁止使用历史数据冒充当日数据，禁止编造金额、席位或股票名称",
        ],
        "sections": sections,
    }


# ==================== 龙虎榜模块 ====================


def cmd_lhb(args):
    """Fetch leaderboard detail for a trading date."""
    date = get_latest_trade_date(args.date)
    try:
        df = ak.stock_lhb_detail_em(start_date=date, end_date=date)
        if df.empty:
            return format_error(
                f"日期 {date} 无龙虎榜数据（可能非交易日或数据未更新）", "lhb"
            )

        records = df_to_records(df, limit=50)
        summary = {
            "date": date,
            "total_stocks": len(df["代码"].unique())
            if "代码" in df.columns
            else len(df),
            "total_records": len(df),
            "records": records,
        }
        return format_output(summary, extra_info=f"龙虎榜详情 - {date}")
    except Exception as e:
        return format_error(str(e), "lhb")


def cmd_lhb_inst(args):
    """Fetch leaderboard institution activity."""
    date = get_latest_trade_date(args.date)
    try:
        df = ak.stock_lhb_jgmmtj_em(start_date=date, end_date=date)
        if df.empty:
            return format_error(f"日期 {date} 无机构交易数据", "lhb-inst")

        return format_output(
            {"date": date, "total": len(df), "records": df_to_records(df, limit=30)},
            extra_info=f"龙虎榜机构席位 - {date}",
        )
    except Exception as e:
        return format_error(str(e), "lhb-inst")


def cmd_lhb_trader(args):
    """Fetch leaderboard trader statistics."""
    date = get_latest_trade_date(args.date)
    days = args.days or 5
    try:
        end_date = date
        start_date = (
            datetime.strptime(date, "%Y%m%d") - timedelta(days=days)
        ).strftime("%Y%m%d")
        df = ak.stock_lhb_hyyyb_em(start_date=start_date, end_date=end_date)
        if df.empty:
            return format_error(f"近{days}日无营业部数据", "lhb-trader")

        return format_output(
            {
                "period": f"{start_date} ~ {end_date}",
                "total_traders": len(df),
                "records": df_to_records(df, limit=30),
            },
            extra_info=f"龙虎榜营业部排行 - 近{days}日",
        )
    except Exception as e:
        return format_error(str(e), "lhb-trader")


# ==================== 涨停/情绪模块 ====================


def cmd_zt_pool(args):
    """Fetch limit-up pool data."""
    date = get_latest_trade_date(args.date)
    try:
        df = ak.stock_zt_pool_em(date=date)
        if df.empty:
            return format_error(f"日期 {date} 无涨停数据", "zt-pool")

        records = df_to_records(df)
        return format_output(
            {"date": date, "zt_count": len(records), "records": records},
            extra_info=f"涨停池 - {date}，共{len(records)}只",
        )
    except Exception as e:
        return format_error(str(e), "zt-pool")


def cmd_dt_pool(args):
    """Fetch limit-down pool data."""
    date = get_latest_trade_date(args.date)
    try:
        df = ak.stock_zt_pool_dtgc_em(date=date)
        if df.empty:
            return format_output(
                {"date": date, "dt_count": 0, "records": []},
                extra_info=f"跌停池 - {date}，今日无跌停",
            )

        records = df_to_records(df)
        return format_output(
            {"date": date, "dt_count": len(records), "records": records},
            extra_info=f"跌停池 - {date}，共{len(records)}只",
        )
    except Exception as e:
        return format_error(str(e), "dt-pool")


def cmd_zb_pool(args):
    """Fetch broken-board pool data."""
    date = get_latest_trade_date(args.date)
    try:
        df = ak.stock_zt_pool_zbgc_em(date=date)
        if df.empty:
            return format_output(
                {"date": date, "zb_count": 0, "records": []},
                extra_info=f"炸板池 - {date}，今日无炸板",
            )

        records = df_to_records(df)
        return format_output(
            {"date": date, "zb_count": len(records), "records": records},
            extra_info=f"炸板池 - {date}，共{len(records)}只",
        )
    except Exception as e:
        return format_error(str(e), "zb-pool")


def cmd_strong_pool(args):
    """Fetch momentum pool data."""
    date = get_latest_trade_date(args.date)
    try:
        df = ak.stock_zt_pool_strong_em(date=date)
        if df.empty:
            return format_error(f"日期 {date} 无连板数据", "strong-pool")

        records = df_to_records(df)
        return format_output(
            {"date": date, "strong_count": len(records), "records": records},
            extra_info=f"强势连板 - {date}，共{len(records)}只",
        )
    except Exception as e:
        return format_error(str(e), "strong-pool")


def cmd_zt_previous(args):
    """Fetch previous limit-up follow-through data."""
    date = get_latest_trade_date(args.date)
    try:
        df = ak.stock_zt_pool_previous_em(date=date)
        if df.empty:
            return format_error(f"日期 {date} 无昨日涨停表现数据", "zt-previous")

        records = df_to_records(df)
        return format_output(
            {"date": date, "total": len(records), "records": records},
            extra_info=f"昨日涨停今日表现 - {date}",
        )
    except Exception as e:
        return format_error(str(e), "zt-previous")


def cmd_zt_summary(args):
    """Fetch limit-up summary data."""
    date = get_latest_trade_date(args.date)
    sections = {}
    counts = {
        "zt_count": 0,
        "dt_count": 0,
        "zb_count": 0,
        "strong_count": 0,
        "previous_count": 0,
    }

    # 涨停
    try:
        zt_df = ak.stock_zt_pool_em(date=date)
        if zt_df.empty:
            sections["zt_pool"] = build_section(
                {"count": 0, "records": []},
                status="empty",
                error_message=f"日期 {date} 暂无涨停数据",
            )
        else:
            counts["zt_count"] = len(zt_df)
            sections["zt_pool"] = build_section(
                {"count": counts["zt_count"], "records": df_to_records(zt_df)}
            )
    except Exception as e:
        sections["zt_pool"] = build_section(
            {"count": 0, "records": []}, status="failed", error_message=str(e)
        )

    # 跌停（正确接口名：stock_zt_pool_dtgc_em）
    try:
        dt_df = ak.stock_zt_pool_dtgc_em(date=date)
        if dt_df.empty:
            sections["dt_pool"] = build_section(
                {"count": 0, "records": []},
                status="empty",
                error_message=f"日期 {date} 暂无跌停数据",
            )
        else:
            counts["dt_count"] = len(dt_df)
            sections["dt_pool"] = build_section(
                {"count": counts["dt_count"], "records": df_to_records(dt_df)}
            )
    except Exception as e:
        sections["dt_pool"] = build_section(
            {"count": 0, "records": []}, status="failed", error_message=str(e)
        )

    # 炸板
    try:
        zb_df = ak.stock_zt_pool_zbgc_em(date=date)
        if zb_df.empty:
            sections["zb_pool"] = build_section(
                {"count": 0, "records": []},
                status="empty",
                error_message=f"日期 {date} 暂无炸板数据",
            )
        else:
            counts["zb_count"] = len(zb_df)
            sections["zb_pool"] = build_section(
                {"count": counts["zb_count"], "records": df_to_records(zb_df)}
            )
    except Exception as e:
        sections["zb_pool"] = build_section(
            {"count": 0, "records": []}, status="failed", error_message=str(e)
        )

    # 连板
    try:
        strong_df = ak.stock_zt_pool_strong_em(date=date)
        if strong_df.empty:
            sections["strong_pool"] = build_section(
                {"count": 0, "records": []},
                status="empty",
                error_message=f"日期 {date} 暂无连板数据",
            )
        else:
            counts["strong_count"] = len(strong_df)
            sections["strong_pool"] = build_section(
                {"count": counts["strong_count"], "records": df_to_records(strong_df)}
            )
    except Exception as e:
        sections["strong_pool"] = build_section(
            {"count": 0, "records": []}, status="failed", error_message=str(e)
        )

    # 昨日涨停今日表现
    try:
        prev_df = ak.stock_zt_pool_previous_em(date=date)
        if prev_df.empty:
            sections["zt_previous"] = build_section(
                {"count": 0, "records": []},
                status="empty",
                error_message=f"日期 {date} 暂无昨日涨停今日表现数据",
            )
        else:
            counts["previous_count"] = len(prev_df)
            sections["zt_previous"] = build_section(
                {"count": counts["previous_count"], "records": df_to_records(prev_df)}
            )
    except Exception as e:
        sections["zt_previous"] = build_section(
            {"count": 0, "records": []}, status="failed", error_message=str(e)
        )

    # 计算情绪指标
    zt_count = counts["zt_count"]
    zb_count = counts["zb_count"]
    dt_count = counts["dt_count"]
    failed_inputs = [
        name
        for name in ["zt_pool", "dt_pool", "zb_pool", "strong_pool", "zt_previous"]
        if sections[name]["status"] == "failed"
    ]
    zb_rate = (
        round(zb_count / (zt_count + zb_count) * 100, 2)
        if (zt_count + zb_count) > 0
        else 0
    )

    sections["sentiment_summary"] = build_section(
        {
            "涨停数": zt_count,
            "跌停数": dt_count,
            "炸板数": zb_count,
            "炸板率": f"{zb_rate}%",
            "连板数": counts["strong_count"],
            "昨涨停今表现": counts["previous_count"],
        },
        status="partial" if failed_inputs else "ok",
        error_message=f"以下 section 取数失败，情绪汇总仅基于已获取数据计算: {', '.join(failed_inputs)}"
        if failed_inputs
        else None,
    )

    payload = build_report_payload(
        "zt_summary",
        date,
        sections,
        facts={"summary_date": date, "available_counts": counts},
    )
    return format_output(payload, extra_info=f"涨停全景 - {date}")


# ==================== 资金流向模块 ====================


def cmd_north_flow(args):
    """Fetch northbound capital-flow data."""
    days = args.days or 10
    try:
        # 当日汇总（实时）
        summary_df = ak.stock_hsgt_fund_flow_summary_em()
        today_summary = df_to_records(summary_df)

        # 历史数据（用北向资金历史）
        hist_df = ak.stock_hsgt_hist_em(symbol="沪股通")
        sh_recent = df_to_records(hist_df.tail(days)) if not hist_df.empty else []

        hist_df_sz = ak.stock_hsgt_hist_em(symbol="深股通")
        sz_recent = df_to_records(hist_df_sz.tail(days)) if not hist_df_sz.empty else []

        return format_output(
            {
                "days": days,
                "today_summary": today_summary,
                "沪股通_历史": sh_recent,
                "深股通_历史": sz_recent,
            },
            extra_info=f"北向资金 - 当日汇总 + 近{days}日历史",
        )
    except Exception as e:
        return format_error(str(e), "north-flow")


def cmd_north_stock(args):
    """Fetch northbound holding data for a stock."""
    symbol = args.symbol or "002008"
    try:
        df = ak.stock_hsgt_individual_em(symbol=symbol)
        if df.empty:
            return format_error(f"个股 {symbol} 北向持仓数据为空", "north-stock")

        records = df_to_records(df.tail(10))
        return format_output(
            {"symbol": symbol, "recent_10days": records},
            extra_info=f"北向个股持仓 - {symbol}",
        )
    except Exception as e:
        return format_error(str(e), "north-stock")


def cmd_sector_flow(args):
    """Fetch sector capital-flow ranking."""
    sector_type = args.sector_type or "industry"
    top = args.top or 20
    try:
        if sector_type == "industry":
            df = retry_call(
                ak.stock_sector_fund_flow_rank,
                indicator="今日",
                sector_type="行业资金流",
            )
        else:
            df = retry_call(
                ak.stock_sector_fund_flow_rank,
                indicator="今日",
                sector_type="概念资金流",
            )

        if df is None or df.empty:
            return format_error("行业资金流数据为空", "sector-flow")

        records = df_to_records(df, limit=top)
        return format_output(
            {
                "sector_type": sector_type,
                "top": top,
                "total_sectors": len(df),
                "records": records,
            },
            extra_info=f"{'行业' if sector_type == 'industry' else '概念'}资金流排名 - Top{top}",
        )
    except Exception as e:
        return format_error(str(e), "sector-flow")


def cmd_stock_flow(args):
    """Fetch capital-flow data for a stock."""
    symbol = args.symbol
    market = args.market or "sh"
    try:
        df = retry_call(ak.stock_individual_fund_flow, stock=symbol, market=market)
        if df is None or df.empty:
            return format_error(f"个股 {symbol} 资金流向数据为空", "stock-flow")

        records = df_to_records(df.tail(5))
        return format_output(
            {"symbol": symbol, "market": market, "recent_5days": records},
            extra_info=f"个股资金流向 - {symbol}",
        )
    except Exception as e:
        return format_error(str(e), "stock-flow")


def cmd_margin(args):
    """Fetch SSE margin trading data."""
    days = args.days or 5
    try:
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
        df = ak.stock_margin_sse(start_date=start_date, end_date=end_date)
        if df.empty:
            return format_error("融资融券数据为空", "margin")

        records = df_to_records(df.tail(days))
        return format_output(
            {"days": days, "records": records},
            extra_info=f"融资融券汇总（沪市）- 近{days}日",
        )
    except Exception as e:
        return format_error(str(e), "margin")


# ==================== 综合报告模块 ====================


def cmd_report_lhb(args):
    """Fetch leaderboard report inputs."""
    date = get_latest_trade_date(args.date)
    sections = {}
    facts = {"summary_date": date}

    # 1. 龙虎榜详情
    try:
        df = ak.stock_lhb_detail_em(start_date=date, end_date=date)
        if df.empty:
            sections["detail"] = build_section(
                {"total_records": 0, "total_stocks": 0, "records": []},
                status="empty",
                error_message=f"日期 {date} 无龙虎榜详情数据",
            )
        else:
            total_stocks = len(df["代码"].unique()) if "代码" in df.columns else len(df)
            sections["detail"] = build_section(
                {
                    "total_records": len(df),
                    "total_stocks": total_stocks,
                    "records": df_to_records(df, limit=50),
                }
            )
            facts["detail_total_records"] = len(df)
            facts["detail_total_stocks"] = total_stocks
    except Exception as e:
        sections["detail"] = build_section(
            {"total_records": 0, "total_stocks": 0, "records": []},
            status="failed",
            error_message=str(e),
        )

    # 2. 机构席位
    try:
        df = ak.stock_lhb_jgmmtj_em(start_date=date, end_date=date)
        if df.empty:
            sections["institution"] = build_section(
                {"total_records": 0, "records": []},
                status="empty",
                error_message=f"日期 {date} 无机构席位数据",
            )
        else:
            sections["institution"] = build_section(
                {"total_records": len(df), "records": df_to_records(df, limit=20)}
            )
            facts["institution_total_records"] = len(df)
    except Exception as e:
        sections["institution"] = build_section(
            {"total_records": 0, "records": []}, status="failed", error_message=str(e)
        )

    # 3. 营业部统计（近5日，用于游资辨识）
    try:
        start = (datetime.strptime(date, "%Y%m%d") - timedelta(days=5)).strftime(
            "%Y%m%d"
        )
        df = ak.stock_lhb_hyyyb_em(start_date=start, end_date=date)
        if df.empty:
            sections["traders"] = build_section(
                {"period": f"{start} ~ {date}", "total_records": 0, "records": []},
                status="empty",
                error_message="近5日无营业部统计数据",
            )
        else:
            sections["traders"] = build_section(
                {
                    "period": f"{start} ~ {date}",
                    "total_records": len(df),
                    "records": df_to_records(df, limit=20),
                }
            )
            facts["traders_total_records"] = len(df)
    except Exception as e:
        sections["traders"] = build_section(
            {
                "period": f"{(datetime.strptime(date, '%Y%m%d') - timedelta(days=5)).strftime('%Y%m%d')} ~ {date}",
                "total_records": 0,
                "records": [],
            },
            status="failed",
            error_message=str(e),
        )

    payload = build_report_payload("report_lhb", date, sections, facts=facts)
    return format_output(payload, extra_info=f"龙虎榜综合报告 - {date}")


def cmd_report_zt(args):
    """Fetch limit-up review report inputs."""
    date = get_latest_trade_date(args.date)
    sections = {}
    counts = {
        "zt_count": 0,
        "dt_count": 0,
        "zb_count": 0,
        "strong_count": 0,
        "previous_count": 0,
    }

    # 1. 涨停池
    try:
        df = ak.stock_zt_pool_em(date=date)
        if df.empty:
            sections["zt_pool"] = build_section(
                {"count": 0, "records": []},
                status="empty",
                error_message=f"日期 {date} 无涨停池数据",
            )
        else:
            counts["zt_count"] = len(df)
            sections["zt_pool"] = build_section(
                {"count": counts["zt_count"], "records": df_to_records(df)}
            )
    except Exception as e:
        sections["zt_pool"] = build_section(
            {"count": 0, "records": []}, status="failed", error_message=str(e)
        )

    # 2. 跌停池
    try:
        df = ak.stock_zt_pool_dtgc_em(date=date)
        if df.empty:
            sections["dt_pool"] = build_section(
                {"count": 0, "records": []},
                status="empty",
                error_message=f"日期 {date} 无跌停池数据",
            )
        else:
            counts["dt_count"] = len(df)
            sections["dt_pool"] = build_section(
                {"count": counts["dt_count"], "records": df_to_records(df)}
            )
    except Exception as e:
        sections["dt_pool"] = build_section(
            {"count": 0, "records": []}, status="failed", error_message=str(e)
        )

    # 3. 炸板池
    try:
        df = ak.stock_zt_pool_zbgc_em(date=date)
        if df.empty:
            sections["zb_pool"] = build_section(
                {"count": 0, "records": []},
                status="empty",
                error_message=f"日期 {date} 无炸板池数据",
            )
        else:
            counts["zb_count"] = len(df)
            sections["zb_pool"] = build_section(
                {"count": counts["zb_count"], "records": df_to_records(df)}
            )
    except Exception as e:
        sections["zb_pool"] = build_section(
            {"count": 0, "records": []}, status="failed", error_message=str(e)
        )

    # 4. 连板梯队
    try:
        df = ak.stock_zt_pool_strong_em(date=date)
        if df.empty:
            sections["strong_pool"] = build_section(
                {"count": 0, "records": []},
                status="empty",
                error_message=f"日期 {date} 无连板梯队数据",
            )
        else:
            counts["strong_count"] = len(df)
            sections["strong_pool"] = build_section(
                {"count": counts["strong_count"], "records": df_to_records(df)}
            )
    except Exception as e:
        sections["strong_pool"] = build_section(
            {"count": 0, "records": []}, status="failed", error_message=str(e)
        )

    # 5. 昨日涨停今日表现
    try:
        df = ak.stock_zt_pool_previous_em(date=date)
        if df.empty:
            sections["zt_previous"] = build_section(
                {"count": 0, "records": []},
                status="empty",
                error_message=f"日期 {date} 无昨日涨停今日表现数据",
            )
        else:
            counts["previous_count"] = len(df)
            sections["zt_previous"] = build_section(
                {"count": counts["previous_count"], "records": df_to_records(df)}
            )
    except Exception as e:
        sections["zt_previous"] = build_section(
            {"count": 0, "records": []}, status="failed", error_message=str(e)
        )

    # 6. 计算情绪指标
    zt = counts["zt_count"]
    dt = counts["dt_count"]
    zb = counts["zb_count"]
    zb_rate = round(zb / (zt + zb) * 100, 2) if (zt + zb) > 0 else 0
    failed_inputs = [
        name
        for name in ["zt_pool", "dt_pool", "zb_pool", "strong_pool", "zt_previous"]
        if sections[name]["status"] == "failed"
    ]
    sections["sentiment"] = build_section(
        {
            "涨停数": zt,
            "跌停数": dt,
            "炸板数": zb,
            "炸板率": f"{zb_rate}%",
            "连板数": counts["strong_count"],
            "昨涨停今表现数": counts["previous_count"],
        },
        status="partial" if failed_inputs else "ok",
        error_message=f"以下 section 取数失败，情绪指标仅基于已获取数据计算: {', '.join(failed_inputs)}"
        if failed_inputs
        else None,
    )

    payload = build_report_payload(
        "report_zt",
        date,
        sections,
        facts={"summary_date": date, "available_counts": counts},
    )
    return format_output(payload, extra_info=f"涨停复盘综合报告 - {date}")


def _filter_hist_by_date(df, date_str, window=10):
    """按交易日过滤北向历史数据，并返回截至该日的最近 window 条记录"""
    if df is None or df.empty:
        return df, None

    date_col = None
    for candidate in ("日期", "date", "交易日期"):
        if candidate in df.columns:
            date_col = candidate
            break
    if date_col is None:
        return df.tail(window), None

    try:
        target = pd.to_datetime(date_str, format="%Y%m%d")
    except Exception:
        return df.tail(window), None

    parsed = pd.to_datetime(df[date_col], errors="coerce")
    mask = parsed <= target
    filtered = df[mask]
    if filtered.empty:
        return filtered, date_col
    return filtered.tail(window), date_col


def cmd_report_capital(args):
    """Fetch capital-flow report inputs."""
    date = get_latest_trade_date(args.date)
    latest_trade_date = get_latest_trade_date()
    is_historical = bool(args.date) and date != latest_trade_date

    sections = {}

    # 1. 北向资金当日汇总（仅支持最新交易日）
    if is_historical:
        sections["north_today"] = build_section(
            {"records": []},
            status="empty",
            error_message=f"北向资金当日汇总接口仅提供最新交易日数据，无法回放 {date}",
        )
    else:
        try:
            df = ak.stock_hsgt_fund_flow_summary_em()
            if df.empty:
                sections["north_today"] = build_section(
                    {"records": []},
                    status="empty",
                    error_message="北向资金当日汇总暂无数据",
                )
            else:
                sections["north_today"] = build_section({"records": df_to_records(df)})
        except Exception as e:
            sections["north_today"] = build_section(
                {"records": []}, status="failed", error_message=str(e)
            )

    # 2. 北向历史（沪股通 + 深股通 近10日，截至指定日期）
    try:
        df_sh = ak.stock_hsgt_hist_em(symbol="沪股通")
        filtered_sh, _ = _filter_hist_by_date(df_sh, date, window=10)
        if filtered_sh is None or filtered_sh.empty:
            sections["north_hist_sh"] = build_section(
                {"records": []},
                status="empty",
                error_message=f"沪股通截至 {date} 的近10日历史暂无数据",
            )
        else:
            sections["north_hist_sh"] = build_section(
                {"records": df_to_records(filtered_sh)}
            )
    except Exception as e:
        sections["north_hist_sh"] = build_section(
            {"records": []}, status="failed", error_message=str(e)
        )

    try:
        df_sz = ak.stock_hsgt_hist_em(symbol="深股通")
        filtered_sz, _ = _filter_hist_by_date(df_sz, date, window=10)
        if filtered_sz is None or filtered_sz.empty:
            sections["north_hist_sz"] = build_section(
                {"records": []},
                status="empty",
                error_message=f"深股通截至 {date} 的近10日历史暂无数据",
            )
        else:
            sections["north_hist_sz"] = build_section(
                {"records": df_to_records(filtered_sz)}
            )
    except Exception as e:
        sections["north_hist_sz"] = build_section(
            {"records": []}, status="failed", error_message=str(e)
        )

    # 3. 行业资金流（仅支持最新交易日）
    if is_historical:
        sections["sector_flow"] = build_section(
            {"records": []},
            status="empty",
            error_message=f"行业资金流排名接口仅提供最新交易日数据，无法回放 {date}",
        )
    else:
        try:
            df = retry_call(
                ak.stock_sector_fund_flow_rank,
                indicator="今日",
                sector_type="行业资金流",
            )
            if df is None or df.empty:
                sections["sector_flow"] = build_section(
                    {"records": []},
                    status="empty",
                    error_message="行业资金流排名暂无数据",
                )
            else:
                sections["sector_flow"] = build_section(
                    {"records": df_to_records(df, limit=20)}
                )
        except Exception as e:
            sections["sector_flow"] = build_section(
                {"records": []}, status="failed", error_message=str(e)
            )

    # 4. 融资融券（截至指定日期的近5个交易日）
    try:
        end_date = date
        start_date = (datetime.strptime(date, "%Y%m%d") - timedelta(days=30)).strftime(
            "%Y%m%d"
        )
        df = ak.stock_margin_sse(start_date=start_date, end_date=end_date)
        if df.empty:
            sections["margin"] = build_section(
                {"records": []},
                status="empty",
                error_message=f"融资融券截至 {end_date} 的近5日暂无数据",
            )
        else:
            sections["margin"] = build_section({"records": df_to_records(df.tail(5))})
    except Exception as e:
        sections["margin"] = build_section(
            {"records": []}, status="failed", error_message=str(e)
        )

    facts = {
        "summary_date": date,
        "date_scope": "历史交易日" if is_historical else "最新交易日",
        "is_historical": is_historical,
        "note": (
            f"指定历史日期 {date} 时，仅历史类接口（北向历史、融资融券）按日期过滤；"
            "实时类接口（北向当日汇总、行业资金流）只提供最新交易日数据，将以 empty 返回"
        )
        if is_historical
        else "资金流向日报中的实时汇总类接口仅保证最新交易日数据准确",
    }

    payload = build_report_payload("report_capital", date, sections, facts=facts)
    return format_output(payload, extra_info=f"资金流向综合报告 - {date}")


# ==================== 主入口 ====================


def main():
    parser = argparse.ArgumentParser(
        description="Retrieve structured A-share market data with AKShare. 获取 A 股结构化市场数据。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 scripts/main.py lhb --date 20260515
  python3 scripts/main.py zt-summary --date 20260515
  python3 scripts/main.py report-lhb --date 20260515
  python3 scripts/main.py report-zt --date 20260515
  python3 scripts/main.py report-capital
  python3 scripts/main.py north-flow --days 10
  python3 scripts/main.py margin --days 5
        """,
    )
    subparsers = parser.add_subparsers(
        dest="command", help="Available commands / 可用命令"
    )

    # ===== 龙虎榜 =====
    p = subparsers.add_parser(
        "lhb", help="Fetch leaderboard detail for a trading date / 获取龙虎榜明细"
    )
    p.add_argument("--date", type=str, help="Trading date in YYYYMMDD format / 交易日")

    p = subparsers.add_parser(
        "lhb-inst", help="Fetch leaderboard institution activity / 获取机构席位数据"
    )
    p.add_argument("--date", type=str, help="Trading date in YYYYMMDD format / 交易日")

    p = subparsers.add_parser(
        "lhb-trader", help="Fetch leaderboard trader statistics / 获取营业部统计"
    )
    p.add_argument("--date", type=str, help="Trading date in YYYYMMDD format / 交易日")
    p.add_argument(
        "--days", type=int, default=5, help="Lookback window in days / 回看天数"
    )

    # ===== 涨停/情绪 =====
    p = subparsers.add_parser("zt-pool", help="Fetch limit-up pool data / 获取涨停池")
    p.add_argument("--date", type=str, help="Trading date in YYYYMMDD format / 交易日")

    p = subparsers.add_parser("dt-pool", help="Fetch limit-down pool data / 获取跌停池")
    p.add_argument("--date", type=str, help="Trading date in YYYYMMDD format / 交易日")

    p = subparsers.add_parser(
        "zb-pool", help="Fetch broken-board pool data / 获取炸板池"
    )
    p.add_argument("--date", type=str, help="Trading date in YYYYMMDD format / 交易日")

    p = subparsers.add_parser(
        "strong-pool", help="Fetch momentum pool data / 获取强势股池"
    )
    p.add_argument("--date", type=str, help="Trading date in YYYYMMDD format / 交易日")

    p = subparsers.add_parser(
        "zt-previous",
        help="Fetch previous limit-up follow-through data / 获取昨涨停今表现",
    )
    p.add_argument("--date", type=str, help="Trading date in YYYYMMDD format / 交易日")

    p = subparsers.add_parser(
        "zt-summary", help="Fetch limit-up summary data / 获取涨停汇总"
    )
    p.add_argument("--date", type=str, help="Trading date in YYYYMMDD format / 交易日")

    # ===== 资金流向 =====
    p = subparsers.add_parser(
        "north-flow", help="Fetch northbound capital-flow data / 获取北向资金"
    )
    p.add_argument(
        "--days", type=int, default=10, help="Number of recent trading days / 近期天数"
    )

    p = subparsers.add_parser(
        "north-stock",
        help="Fetch northbound holding data for a stock / 获取个股北向持仓",
    )
    p.add_argument(
        "--symbol", type=str, default="600519", help="Stock symbol / 股票代码"
    )

    p = subparsers.add_parser(
        "sector-flow",
        help="Fetch sector capital-flow ranking / 获取行业或概念资金流排名",
    )
    p.add_argument(
        "--sector_type",
        type=str,
        default="industry",
        help="Sector type: industry or concept / 类型",
    )
    p.add_argument(
        "--top", type=int, default=20, help="Number of rows to return / 返回条数"
    )

    p = subparsers.add_parser(
        "stock-flow", help="Fetch capital-flow data for a stock / 获取个股资金流"
    )
    p.add_argument("--symbol", type=str, required=True, help="Stock symbol / 股票代码")
    p.add_argument(
        "--market", type=str, default="sh", help="Market code: sh or sz / 市场代码"
    )

    p = subparsers.add_parser(
        "margin", help="Fetch SSE margin trading data / 获取沪市融资融券数据"
    )
    p.add_argument(
        "--days", type=int, default=5, help="Number of recent rows to return / 返回行数"
    )

    # ===== 综合报告 =====
    p = subparsers.add_parser(
        "report-lhb", help="Fetch leaderboard report inputs / 获取龙虎榜报告输入"
    )
    p.add_argument("--date", type=str, help="Trading date in YYYYMMDD format / 交易日")

    p = subparsers.add_parser(
        "report-zt", help="Fetch limit-up review report inputs / 获取涨停复盘报告输入"
    )
    p.add_argument("--date", type=str, help="Trading date in YYYYMMDD format / 交易日")

    p = subparsers.add_parser(
        "report-capital", help="Fetch capital-flow report inputs / 获取资金流报告输入"
    )
    p.add_argument(
        "--date",
        type=str,
        help="Trading date in YYYYMMDD format; real-time sections only support the latest date / 交易日，实时类 section 仅支持最新交易日",
    )

    args = parser.parse_args()

    # 命令路由
    cmd_map = {
        "lhb": cmd_lhb,
        "lhb-inst": cmd_lhb_inst,
        "lhb-trader": cmd_lhb_trader,
        "zt-pool": cmd_zt_pool,
        "dt-pool": cmd_dt_pool,
        "zb-pool": cmd_zb_pool,
        "strong-pool": cmd_strong_pool,
        "zt-previous": cmd_zt_previous,
        "zt-summary": cmd_zt_summary,
        "north-flow": cmd_north_flow,
        "north-stock": cmd_north_stock,
        "sector-flow": cmd_sector_flow,
        "stock-flow": cmd_stock_flow,
        "margin": cmd_margin,
        "report-lhb": cmd_report_lhb,
        "report-zt": cmd_report_zt,
        "report-capital": cmd_report_capital,
    }

    if args.command in cmd_map:
        try:
            ensure_runtime_dependencies()
            result = cmd_map[args.command](args)
        except DependencyError as exc:
            result = format_dependency_error(exc.package_name, args.command)
    else:
        parser.print_help()
        sys.exit(1)

    # 输出 JSON
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
