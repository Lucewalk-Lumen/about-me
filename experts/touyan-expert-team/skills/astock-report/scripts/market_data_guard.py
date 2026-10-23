#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A股数据守门脚本。

目标：AkShare 作为主数据源；实时行情至少再拿到一个核验源，龙虎榜必须校验交易日期。
任何校验失败都返回结构化 status，不把未验证数字包装成确定结论。
"""
from __future__ import annotations

import argparse
import concurrent.futures
import contextlib
import io
import json
import math
import re
import sys
import time
import urllib.parse
import urllib.request
import warnings
from dataclasses import asdict, dataclass
from datetime import datetime, time as dt_time, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

TZ_CN = timezone(timedelta(hours=8))
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
PRICE_DIFF_LIMIT_PCT = 0.20
LHB_AMOUNT_DIFF_LIMIT_PCT = 8.0
EASTMONEY_DATACENTER_URL = "https://datacenter-web.eastmoney.com/api/data/v1/get"
DEFAULT_TOP_GAINERS_WORKERS = 8
warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL.*")

NAME_ALIASES = {
    "中际旭创": "300308.SZ",
    "贵州茅台": "600519.SH",
    "茅台": "600519.SH",
    "宁德时代": "300750.SZ",
    "寒武纪": "688256.SH",
    "比亚迪": "002594.SZ",
    "东方财富": "300059.SZ",
    "工业富联": "601138.SH",
    "新易盛": "300502.SZ",
    "沪深300": "000300.SH",
    "上证指数": "000001.SH",
    "深证成指": "399001.SZ",
    "创业板指": "399006.SZ",
    "科创50": "000688.SH",
    "中证500": "000905.SH",
    "中证1000": "000852.SH",
}

INDEX_CODES = {
    "000001.SH",
    "000300.SH",
    "000688.SH",
    "000905.SH",
    "000852.SH",
    "399001.SZ",
    "399006.SZ",
}

INDEX_BOUNDARY_RULES = {
    "000852": {
        "name": "中证1000",
        "market": "SH",
        "sample_space": "由全部 A 股中剔除中证800指数样本及过去一年日均总市值排名前300名的证券后，选取规模偏小且流动性较好的1000只证券。",
        "represents": "反映小市值证券的整体表现，不能代表全部 A 股市场。",
        "common_confusion": "常见误区是把中证1000当成全 A 指数；它的核心边界是“中证800之外”。",
        "source_note": "指数边界规则需以中证指数公司最新编制方案为准。",
    },
    "000905": {
        "name": "中证500",
        "market": "SH",
        "sample_space": "由全部 A 股中剔除沪深300指数样本及过去一年日均总市值排名前300名的证券后，选取日均总市值靠前的500只证券。",
        "represents": "反映 A 股中等市值公司表现，不能代表全部 A 股市场。",
        "common_confusion": "常见误区是把中证500理解成随机500只股票或全市场中位数代表。",
        "source_note": "指数边界规则需以中证指数公司最新编制方案为准。",
    },
    "000300": {
        "name": "沪深300",
        "market": "SH",
        "sample_space": "从沪深市场中选取规模大、流动性好的300只证券。",
        "represents": "反映沪深市场大盘蓝筹上市公司证券的整体表现。",
        "common_confusion": "常见误区是把沪深300当成全部 A 股；它偏大盘蓝筹。",
        "source_note": "指数边界规则需以中证指数公司最新编制方案为准。",
    },
}

ENTITY_RISK_RULES = {
    "600518": {
        "name": "康美药业",
        "market": "SH",
        "risk_facts": ["曾发生重大财务造假和监管处罚事件", "历史风险样本不能当普通白马股处理"],
        "required_note": "若出现在榜单或样本中，必须提示重大监管风险和历史财务造假背景。",
    },
    "002069": {
        "name": "獐子岛",
        "market": "SZ",
        "risk_facts": ["曾因信息披露和资产异常等事项受到市场长期关注", "历史上存在较强监管和经营风险标签"],
        "required_note": "若出现在榜单或样本中，必须提示监管/经营风险，不能当普通水产股样本处理。",
    },
    "300104": {
        "name": "乐视网",
        "market": "SZ",
        "risk_facts": ["已退市，不属于当前普通 A 股样本", "不能纳入普通 A 股实时榜单或可交易样本"],
        "required_note": "若题目涉及乐视网，必须明确退市状态，不能当普通 A 股处理。",
    },
    "LKNCY": {
        "name": "瑞幸咖啡",
        "market": "US/OTC",
        "risk_facts": ["不是 A 股上市公司", "曾有财务造假监管事件"],
        "required_note": "若题目要求 A 股样本，瑞幸咖啡应标为市场错配，不能纳入普通 A 股。",
    },
}

KNOWN_ANNUAL_FIELD_RULES = {
    ("601318", 2022): {
        "name": "中国平安",
        "code": "601318.SH",
        "report_period": "2022-12-31",
        "source": "中国平安 2022 年度报告口径；内置准确性评测校准样本 ASHARE-221",
        "fields": {
            "operating_revenue_yi": {
                "name": "营业收入",
                "value": 11105.68,
                "unit": "亿元",
            },
            "parent_net_profit_yi": {
                "name": "归母净利润",
                "value": 837.74,
                "unit": "亿元",
            },
            "deduct_parent_net_profit_yi": {
                "name": "扣非归母净利润",
                "value": 841.63,
                "unit": "亿元",
            },
        },
        "conflict_note": "AkShare 部分利润表入口可能返回 8803.55/1110.08/841.63 亿元这一组不同口径字段，不能把它直接写成 2022 年报核心字段核验结果。",
    }
}


@dataclass
class Target:
    raw: str
    code: str
    exchange: str
    canonical: str
    tencent_symbol: str
    sina_symbol: str
    is_index: bool


@dataclass
class Quote:
    source: str
    function: str
    role: str
    name: str
    code: str
    exchange: str
    price: float
    change: Optional[float]
    pct: Optional[float]
    volume: Optional[float]
    amount: Optional[float]
    source_time: Optional[str]
    fetched_at: str


def now_cn() -> datetime:
    return datetime.now(TZ_CN)


def fmt_dt(dt: Optional[datetime]) -> Optional[str]:
    if not dt:
        return None
    return dt.astimezone(TZ_CN).strftime("%Y-%m-%d %H:%M:%S")


def import_akshare():
    try:
        import akshare as ak  # type: ignore
    except Exception as exc:
        raise RuntimeError("AkShare 未安装或不可导入，请先安装 requirements.txt") from exc
    return ak


def quiet_call(function: Any, *args: Any, **kwargs: Any) -> Any:
    """AkShare 部分函数会输出进度条；JSON 模式下必须保持 stdout 干净。"""
    sink = io.StringIO()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
            return function(*args, **kwargs)


def silence_akshare_progress(ak: Any) -> None:
    tx_fn = getattr(ak, "stock_zh_a_hist_tx", None)
    module_name = getattr(tx_fn, "__module__", None)
    module = sys.modules.get(module_name) if module_name else None
    if module is not None and hasattr(module, "get_tqdm"):
        setattr(module, "get_tqdm", lambda: (lambda iterable, *args, **kwargs: iterable))


def http_get(url: str, *, encoding: str = "utf-8", timeout: int = 8, headers: Optional[Dict[str, str]] = None) -> str:
    req_headers = {"User-Agent": USER_AGENT}
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(url, headers=req_headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    return raw.decode(encoding, errors="replace")


def parse_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    s = str(value).strip().replace(",", "")
    if not s or s in {"-", "--", "None", "nan", "NaN", "null"}:
        return None
    s = s.replace("%", "").replace("亿元", "").replace("万元", "").replace("元", "").replace("亿", "").replace("万", "")
    try:
        v = float(s)
    except ValueError:
        return None
    if not math.isfinite(v):
        return None
    return v


def normalize_code(value: Any) -> str:
    s = str(value or "").strip().upper()
    m = re.search(r"(\d{6})", s)
    return m.group(1) if m else ""


def normalize_trade_date(value: Optional[str]) -> str:
    s = (value or "").strip()
    if not s:
        return now_cn().strftime("%Y-%m-%d")
    for fmt in ("%Y-%m-%d", "%Y%m%d"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    raise ValueError("date must be YYYY-MM-DD or YYYYMMDD")


def compact_trade_date(value: str) -> str:
    return normalize_trade_date(value).replace("-", "")


def normalize_response_trade_date(value: Any) -> Optional[str]:
    s = str(value or "").strip()
    if not s:
        return None
    m = re.match(r"^(\d{4})[-/](\d{1,2})[-/](\d{1,2})", s)
    if m:
        y, mo, d = m.groups()
        return f"{int(y):04d}-{int(mo):02d}-{int(d):02d}"
    m = re.match(r"^(\d{4})(\d{2})(\d{2})$", s)
    if m:
        y, mo, d = m.groups()
        return f"{y}-{mo}-{d}"
    return None


def infer_exchange(code: str) -> Optional[str]:
    if code.startswith(("60", "68", "69", "51", "52", "56", "58", "90", "11")):
        return "SH"
    if code.startswith(("00", "20", "30", "15", "16", "18", "12")):
        return "SZ"
    if code.startswith(("43", "83", "87", "88", "92")):
        return "BJ"
    return None


def normalize_target(raw: str) -> Optional[Target]:
    s = raw.strip()
    if not s:
        return None
    s = NAME_ALIASES.get(s, s)
    s_upper = s.upper().replace(" ", "")
    m = re.fullmatch(r"(SH|SZ|BJ)?(\d{6})(?:\.(SH|SZ|BJ))?", s_upper)
    if not m:
        return None
    prefix, code, suffix = m.groups()
    exchange = suffix or prefix or infer_exchange(code)
    if not exchange:
        return None
    canonical = f"{code}.{exchange}"
    exchange_l = exchange.lower()
    return Target(
        raw=raw,
        code=code,
        exchange=exchange,
        canonical=canonical,
        tencent_symbol=f"{exchange_l}{code}",
        sina_symbol=f"{exchange_l}{code}",
        is_index=canonical in INDEX_CODES,
    )


def dataframe_records(df: Any) -> List[Dict[str, Any]]:
    if df is None:
        return []
    if getattr(df, "empty", False):
        return []
    return list(df.to_dict("records"))


def first_value(row: Dict[str, Any], aliases: Sequence[str]) -> Any:
    for key in aliases:
        if key in row:
            value = row.get(key)
            if value is not None and str(value).strip() not in {"", "-", "--", "nan", "NaN"}:
                return value
    return None


def find_row_by_code(records: Iterable[Dict[str, Any]], code: str) -> Optional[Dict[str, Any]]:
    for row in records:
        row_code = normalize_code(first_value(row, ("代码", "证券代码", "股票代码", "symbol", "SECURITY_CODE", "f12")))
        if row_code == code:
            return row
    return None


def amount_to_yi(value: Any, default_unit: str = "yuan") -> Tuple[Optional[float], str]:
    raw = str(value or "").strip()
    amount = parse_float(value)
    if amount is None:
        return None, "unknown"
    if "亿" in raw:
        return round(amount, 2), "yi"
    if "万" in raw:
        return round(amount / 10000, 2), "wan"
    if default_unit == "yuan":
        return round(amount / 100000000, 2), "yuan"
    if default_unit == "wan":
        return round(amount / 10000, 2), "wan"
    if abs(amount) >= 10000000:
        return round(amount / 100000000, 2), "yuan"
    if abs(amount) >= 10000:
        return round(amount / 10000, 2), "wan_inferred"
    return round(amount, 2), "yi_inferred"


def parse_sina_time(date_s: str, time_s: str) -> Optional[str]:
    if not date_s or not time_s:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return fmt_dt(datetime.strptime(f"{date_s} {time_s}", fmt).replace(tzinfo=TZ_CN))
        except ValueError:
            continue
    return None


def parse_tencent_time(value: str) -> Optional[str]:
    s = str(value or "").strip()
    for fmt in ("%Y%m%d%H%M%S", "%Y%m%d%H%M"):
        if len(s) == len(datetime.now().strftime(fmt)):
            try:
                return fmt_dt(datetime.strptime(s, fmt).replace(tzinfo=TZ_CN))
            except ValueError:
                return None
    return None


def normalize_source_time(value: Any) -> Optional[str]:
    s = str(value or "").strip()
    if not s:
        return None
    if re.fullmatch(r"\d{1,2}:\d{2}:\d{2}", s):
        return f"{now_cn().strftime('%Y-%m-%d')} {s}"
    if re.match(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}", s):
        return s.replace("/", "-")
    return s


def normalize_adjust(value: Optional[str]) -> str:
    s = str(value or "").strip().lower()
    mapping = {
        "": "",
        "none": "",
        "raw": "",
        "no": "",
        "不复权": "",
        "qfq": "qfq",
        "前复权": "qfq",
        "hfq": "hfq",
        "后复权": "hfq",
    }
    if s not in mapping:
        raise ValueError("adjust must be one of: none, qfq, hfq")
    return mapping[s]


def adjust_label(adjust: str) -> str:
    if adjust == "qfq":
        return "前复权"
    if adjust == "hfq":
        return "后复权"
    return "不复权"


def safe_yi(value: Any) -> Optional[float]:
    parsed = parse_float(value)
    if parsed is None:
        return None
    return round(parsed / 100000000, 4)


def safe_pct(numerator: Optional[float], denominator: Optional[float]) -> Optional[float]:
    if numerator is None or denominator in (None, 0):
        return None
    return round(numerator / denominator * 100, 4)


def field_payload(
    key: str,
    name: str,
    value: Optional[float],
    unit: str,
    source: str,
    report_period: str,
    *,
    note: str = "",
) -> Dict[str, Any]:
    return {
        "key": key,
        "name": name,
        "value": value,
        "unit": unit,
        "source": source,
        "report_period": report_period,
        "status": "ok" if value is not None else "missing",
        "note": note,
    }


def is_common_a_share_code(code: str) -> bool:
    return code.startswith(("60", "68", "69", "00", "30", "43", "83", "87", "88", "92"))


def is_delisted_name(name: str) -> bool:
    compact = str(name or "").strip()
    return "退市" in compact or compact.startswith("退")


def risk_flags_for_name(name: str, *, incomplete_window: bool = False) -> List[str]:
    flags: List[str] = []
    upper = str(name or "").upper()
    if "ST" in upper:
        flags.append("special_treatment")
    if incomplete_window:
        flags.append("not_full_requested_window")
    return flags


def build_stock_pool_from_spot(records: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    pool: List[Dict[str, str]] = []
    seen = set()
    for row in records:
        code = normalize_code(first_value(row, ("代码", "证券代码", "股票代码", "code", "symbol", "f12")))
        if not code or code in seen or not is_common_a_share_code(code):
            continue
        exchange = infer_exchange(code)
        if exchange not in {"SH", "SZ", "BJ"}:
            continue
        name = str(first_value(row, ("名称", "股票简称", "证券简称", "name", "f14")) or "").strip()
        if is_delisted_name(name):
            continue
        seen.add(code)
        pool.append({"code": code, "name": name or code, "exchange": exchange, "canonical": f"{code}.{exchange}"})
    return pool


def fetch_a_share_pool(ak: Any) -> Tuple[List[Dict[str, str]], str]:
    attempts: List[Tuple[str, Any]] = []
    if hasattr(ak, "stock_info_a_code_name"):
        attempts.append(("stock_info_a_code_name", ak.stock_info_a_code_name))
    if hasattr(ak, "stock_zh_a_spot"):
        attempts.append(("stock_zh_a_spot", ak.stock_zh_a_spot))
    if hasattr(ak, "stock_zh_a_spot_em"):
        attempts.append(("stock_zh_a_spot_em", ak.stock_zh_a_spot_em))
    last_error = "not attempted"
    for function_name, function in attempts:
        try:
            pool = build_stock_pool_from_spot(dataframe_records(quiet_call(function)))
            if pool:
                pool.sort(key=lambda row: ({"SH": 0, "SZ": 1, "BJ": 2}.get(row.get("exchange") or "", 9), row.get("code") or ""))
                return pool, function_name
            last_error = f"{function_name} 返回股票池为空"
        except Exception as exc:
            last_error = f"{function_name}: {exc}"
    raise RuntimeError(last_error)


def compute_hist_return(
    ak: Any,
    stock: Dict[str, str],
    start_date: str,
    end_date: str,
    adjust: str,
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    code = stock["code"]
    attempts: List[Tuple[str, Any]] = []

    if hasattr(ak, "stock_zh_a_hist"):
        def fetch_em() -> Any:
            try:
                return ak.stock_zh_a_hist(
                    symbol=code,
                    period="daily",
                    start_date=compact_trade_date(start_date),
                    end_date=compact_trade_date(end_date),
                    adjust=adjust,
                    timeout=8,
                )
            except TypeError:
                return ak.stock_zh_a_hist(
                    symbol=code,
                    period="daily",
                    start_date=compact_trade_date(start_date),
                    end_date=compact_trade_date(end_date),
                    adjust=adjust,
                )

        attempts.append(("stock_zh_a_hist", fetch_em))

    if hasattr(ak, "stock_zh_a_hist_tx"):
        tx_symbol = f"{str(stock.get('exchange') or '').lower()}{code}"

        def fetch_tx() -> Any:
            try:
                return ak.stock_zh_a_hist_tx(
                    symbol=tx_symbol,
                    start_date=start_date,
                    end_date=end_date,
                    adjust=adjust,
                    timeout=8,
                )
            except TypeError:
                return ak.stock_zh_a_hist_tx(
                    symbol=tx_symbol,
                    start_date=start_date,
                    end_date=end_date,
                    adjust=adjust,
                )

        attempts.append(("stock_zh_a_hist_tx", fetch_tx))

    if not attempts:
        return None, {"code": code, "reason": "no_akshare_history_function"}

    last_errors: List[str] = []
    selected_function = ""
    records: List[Dict[str, Any]] = []
    for function_name, fetcher in attempts:
        try:
            records = dataframe_records(fetcher())
            if records:
                selected_function = function_name
                break
            last_errors.append(f"{function_name}: empty")
        except Exception as exc:
            last_errors.append(f"{function_name}: {exc}")
    if not selected_function:
        return None, {"code": code, "reason": "history_fetch_failed: " + " | ".join(last_errors[:3])}

    valid_rows: List[Dict[str, Any]] = []
    for row in records:
        row_date = normalize_response_trade_date(first_value(row, ("日期", "date", "交易日期")))
        close = parse_float(first_value(row, ("收盘", "收盘价", "close")))
        if row_date and close is not None and close > 0:
            valid_rows.append({"date": row_date, "close": close})

    valid_rows.sort(key=lambda item: item["date"])
    if len(valid_rows) < 2:
        return None, {"code": code, "reason": "insufficient_trading_days"}

    first = valid_rows[0]
    last = valid_rows[-1]
    start_close = first["close"]
    end_close = last["close"]
    if start_close <= 0 or end_close <= 0:
        return None, {"code": code, "reason": "invalid_close_price"}

    return_pct = (end_close / start_close - 1) * 100
    return {
        "code": code,
        "name": stock.get("name") or code,
        "exchange": stock.get("exchange"),
        "canonical": stock.get("canonical") or f"{code}.{stock.get('exchange')}",
        "start_date": first["date"],
        "end_date": last["date"],
        "start_close": round(start_close, 4),
        "end_close": round(end_close, 4),
        "return_pct": round(return_pct, 4),
        "adjustment": adjust_label(adjust),
        "source": f"AKShare {selected_function}",
        "risk_flags": risk_flags_for_name(stock.get("name") or ""),
    }, None


def build_top_gainers_user_message(
    status: str,
    start_date: str,
    end_date: str,
    rows: List[Dict[str, Any]],
    *,
    adjustment: str,
    market_start: Optional[str],
    market_end: Optional[str],
    reason: str = "",
    sampled: bool = False,
) -> str:
    if status not in {"ok", "partial"}:
        suffix = f"原因：{reason}" if reason else "AkShare 未返回足够可计算样本。"
        return f"我没有拿到 {start_date} 至 {end_date} 的可验证区间涨幅榜，不能输出全市场 Top10。{suffix}"

    scope = "抽样" if sampled else "全市场"
    window = f"实际交易窗口 {market_start} 至 {market_end}" if market_start and market_end else "按接口返回交易日"
    lines = [f"按 AkShare 逐只股票计算，{start_date} 至 {end_date} A股{scope}区间涨幅前{len(rows)}名（{adjustment}，{window}）："]
    for idx, row in enumerate(rows, 1):
        flags = f"，标记：{','.join(row['risk_flags'])}" if row.get("risk_flags") else ""
        lines.append(
            f"{idx}. {row.get('name')}（{row.get('canonical')}）：{row.get('return_pct'):+.2f}%"
            f"（{row.get('start_close')} -> {row.get('end_close')}）{flags}"
        )
    if status == "partial":
        lines.append(f"注意：{reason or '可计算样本不足，结果只能作为部分样本排行。'}")
    lines.append("来源：AkShare stock_info_a_code_name / stock_zh_a_spot + stock_zh_a_hist，必要时自动回退到 stock_zh_a_hist_tx；缺少完整交易窗口的股票默认不参与排序。")
    return "\n".join(lines)


def top_gainers_payload(
    start_date: str,
    end_date: str,
    limit: int = 10,
    adjust: str = "qfq",
    workers: int = DEFAULT_TOP_GAINERS_WORKERS,
    max_stocks: int = 0,
    budget_seconds: int = 300,
    include_incomplete: bool = False,
    include_audit: bool = False,
) -> Dict[str, Any]:
    try:
        start = normalize_trade_date(start_date)
        end = normalize_trade_date(end_date)
        if start > end:
            raise ValueError("start date must be <= end date")
        adjust_value = normalize_adjust(adjust)
    except ValueError as exc:
        return {
            "status": "invalid_args",
            "start_date": start_date,
            "end_date": end_date,
            "user_message": f"区间涨幅参数无效：{exc}",
        }

    safe_limit = max(1, min(int(limit or 10), 50))
    safe_workers = max(1, min(int(workers or DEFAULT_TOP_GAINERS_WORKERS), 32))
    safe_budget = max(0, int(budget_seconds or 0))
    deadline = time.monotonic() + safe_budget if safe_budget > 0 else None
    timed_out = False
    errors: List[Dict[str, Any]] = []
    rows: List[Dict[str, Any]] = []
    stock_pool_function = ""
    pool: List[Dict[str, str]] = []

    try:
        ak = import_akshare()
        if not hasattr(ak, "stock_zh_a_hist") and not hasattr(ak, "stock_zh_a_hist_tx"):
            raise RuntimeError("当前 AkShare 不包含可用的日线历史函数")
        silence_akshare_progress(ak)
        pool, stock_pool_function = fetch_a_share_pool(ak)
        if max_stocks and max_stocks > 0:
            pool = pool[: max(1, int(max_stocks))]
        for offset in range(0, len(pool), safe_workers):
            if deadline is not None and time.monotonic() >= deadline:
                timed_out = True
                break
            batch = pool[offset : offset + safe_workers]
            with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, len(batch))) as executor:
                futures = {
                    executor.submit(compute_hist_return, ak, stock, start, end, adjust_value): stock
                    for stock in batch
                }
                for future in concurrent.futures.as_completed(futures):
                    try:
                        row, error = future.result()
                    except Exception as exc:
                        stock = futures[future]
                        row, error = None, {"code": stock.get("code"), "reason": f"worker_failed: {exc}"}
                    if row:
                        rows.append(row)
                    elif error and len(errors) < 100:
                        errors.append(error)
    except Exception as exc:
        reason = str(exc)
        payload: Dict[str, Any] = {
            "status": "failed",
            "start_date": start,
            "end_date": end,
            "source": "AKShare stock_info_a_code_name / stock_zh_a_spot / stock_zh_a_hist / stock_zh_a_hist_tx",
            "user_message": build_top_gainers_user_message(
                "failed",
                start,
                end,
                [],
                adjustment=adjust_label(adjust_value) if "adjust_value" in locals() else str(adjust),
                market_start=None,
                market_end=None,
                reason=reason,
                sampled=bool(max_stocks),
            ),
        }
        if include_audit:
            payload["internal_audit"] = {"errors": [{"reason": reason}]}
        return payload

    market_start = min((row["start_date"] for row in rows), default=None)
    market_end = max((row["end_date"] for row in rows), default=None)
    ranked_rows: List[Dict[str, Any]] = []
    for row in rows:
        incomplete = bool(market_start and market_end and (row["start_date"] != market_start or row["end_date"] != market_end))
        if incomplete:
            row = {**row, "risk_flags": risk_flags_for_name(row.get("name") or "", incomplete_window=True)}
        if include_incomplete or not incomplete:
            ranked_rows.append(row)
    ranked_rows.sort(key=lambda item: item["return_pct"], reverse=True)
    top_rows = ranked_rows[:safe_limit]

    if max_stocks and top_rows:
        status, reason = "partial", f"仅扫描前 {len(pool)} 只股票，结果为抽样排行。"
    elif timed_out and top_rows:
        status, reason = "partial", "达到时间预算，未完整遍历全市场。"
    elif timed_out:
        status, reason = "failed", "达到时间预算，且没有拿到足够可计算样本。"
    elif len(top_rows) >= safe_limit:
        status, reason = "ok", ""
    elif top_rows:
        status, reason = "partial", "完整交易窗口样本不足。"
    else:
        status, reason = "failed", "没有股票同时具备区间起止有效收盘价。"

    payload: Dict[str, Any] = {
        "status": status,
        "start_date": start,
        "end_date": end,
        "actual_market_start_date": market_start,
        "actual_market_end_date": market_end,
        "limit": safe_limit,
        "adjustment": adjust_label(adjust_value),
        "provider": "akshare",
        "source": "AKShare stock_info_a_code_name / stock_zh_a_spot / stock_zh_a_hist / stock_zh_a_hist_tx",
        "verification_policy": "Full stock pool from AkShare code/name list with spot fallback unless max_stocks is set; per-stock historical close from AkShare hist function with AkShare TX fallback; incomplete date windows excluded unless requested",
        "rows": top_rows,
        "user_message": build_top_gainers_user_message(
            status,
            start,
            end,
            top_rows,
            adjustment=adjust_label(adjust_value),
            market_start=market_start,
            market_end=market_end,
            reason=reason,
            sampled=bool(max_stocks),
        ),
    }
    if include_audit:
        payload["internal_audit"] = {
            "fetched_at": fmt_dt(now_cn()),
            "stock_pool_function": stock_pool_function,
            "pool_count": len(pool),
            "computed_count": len(rows),
            "ranked_count": len(ranked_rows),
            "skipped_or_error_count": max(0, len(pool) - len(rows)),
            "workers": safe_workers,
            "budget_seconds": safe_budget,
            "timed_out": timed_out,
            "max_stocks": int(max_stocks or 0),
            "include_incomplete": include_incomplete,
            "errors_sample": errors[:20],
        }
    return payload


def fetch_akshare_quote(target: Target) -> Quote:
    ak = import_akshare()
    attempts: List[Tuple[str, Any]] = []
    if target.is_index and hasattr(ak, "stock_zh_index_spot_em"):
        attempts.append(("stock_zh_index_spot_em", ak.stock_zh_index_spot_em))
    if not target.is_index and hasattr(ak, "stock_zh_a_spot"):
        attempts.append(("stock_zh_a_spot", ak.stock_zh_a_spot))
    if hasattr(ak, "stock_zh_a_spot_em"):
        attempts.append(("stock_zh_a_spot_em", ak.stock_zh_a_spot_em))
    if not attempts:
        raise RuntimeError("当前 AkShare 不包含可用 A 股实时行情函数")

    last_error = "not attempted"
    for function_name, function in attempts:
        try:
            row = find_row_by_code(dataframe_records(quiet_call(function)), target.code)
            if not row:
                last_error = f"{function_name} 未返回代码 {target.code}"
                continue
            price = parse_float(first_value(row, ("最新价", "最新", "价格", "现价", "f2")))
            if price is None or price <= 0:
                last_error = f"{function_name} 返回无效价格"
                continue
            return Quote(
                source="AKShare",
                function=function_name,
                role="primary",
                name=str(first_value(row, ("名称", "股票简称", "证券简称", "name", "f14")) or target.raw),
                code=target.code,
                exchange=target.exchange,
                price=price,
                change=parse_float(first_value(row, ("涨跌额", "涨跌", "f4"))),
                pct=parse_float(first_value(row, ("涨跌幅", "涨幅", "涨跌幅%", "f3"))),
                volume=parse_float(first_value(row, ("成交量", "f5"))),
                amount=parse_float(first_value(row, ("成交额", "f6"))),
                source_time=normalize_source_time(first_value(row, ("时间戳", "更新时间", "time"))),
                fetched_at=fmt_dt(now_cn()) or "",
            )
        except Exception as exc:
            last_error = f"{function_name}: {exc}"
    raise RuntimeError(last_error)


def fetch_sina_verifier(target: Target) -> Quote:
    url = f"https://hq.sinajs.cn/list={target.sina_symbol}"
    raw = http_get(url, encoding="gbk", headers={"Referer": "https://finance.sina.com.cn/"})
    m = re.search(r'="(.*)"', raw)
    if not m or not m.group(1):
        raise ValueError("empty response")
    fields = m.group(1).split(",")
    if len(fields) < 32:
        raise ValueError("unexpected response shape")
    price = parse_float(fields[3])
    prev_close = parse_float(fields[2])
    if price is None or price <= 0:
        raise ValueError("invalid or zero price")
    change = round(price - prev_close, 4) if prev_close and prev_close > 0 else None
    pct = round(change / prev_close * 100, 4) if change is not None and prev_close else None
    return Quote(
        source="新浪财经",
        function="hq.sinajs.cn verifier",
        role="verifier",
        name=fields[0].strip() or target.raw,
        code=target.code,
        exchange=target.exchange,
        price=price,
        change=change,
        pct=pct,
        volume=parse_float(fields[8]),
        amount=parse_float(fields[9]),
        source_time=parse_sina_time(fields[30].strip(), fields[31].strip()),
        fetched_at=fmt_dt(now_cn()) or "",
    )


def fetch_tencent_verifier(target: Target) -> Quote:
    url = f"https://qt.gtimg.cn/q={target.tencent_symbol}"
    raw = http_get(url, encoding="gbk")
    m = re.search(r'="(.*)"', raw)
    if not m or not m.group(1):
        raise ValueError("empty response")
    f = m.group(1).split("~")
    if len(f) < 33:
        raise ValueError("unexpected response shape")
    price = parse_float(f[3])
    if price is None or price <= 0:
        raise ValueError("invalid or zero price")
    source_time = None
    for idx in (30, 29):
        if idx < len(f):
            source_time = parse_tencent_time(f[idx])
            if source_time:
                break
    return Quote(
        source="腾讯财经",
        function="qt.gtimg.cn verifier",
        role="verifier",
        name=f[1].strip() or target.raw,
        code=target.code,
        exchange=target.exchange,
        price=price,
        change=parse_float(f[31]),
        pct=parse_float(f[32]),
        volume=parse_float(f[6]) if len(f) > 6 else None,
        amount=parse_float(f[37]) if len(f) > 37 else None,
        source_time=source_time,
        fetched_at=fmt_dt(now_cn()) or "",
    )


def market_phase(dt: Optional[datetime] = None) -> Tuple[str, str]:
    d = dt or now_cn()
    if d.weekday() >= 5:
        return "closed", "非交易日，公开行情通常是最近一个交易快照"
    t = d.time()
    if dt_time(9, 15) <= t < dt_time(9, 25):
        return "call_auction", "集合竞价阶段，价格可能快速变化"
    if dt_time(9, 30) <= t <= dt_time(11, 30) or dt_time(13, 0) <= t <= dt_time(15, 0):
        return "continuous", "连续竞价时段，行情会实时跳动"
    if dt_time(11, 30) < t < dt_time(13, 0):
        return "lunch_break", "午间休市，公开行情是上午收盘后的快照"
    if t > dt_time(15, 0):
        return "after_close", "已收盘，公开行情通常是收盘快照"
    return "pre_open", "尚未开盘，公开行情通常是上一交易日或集合竞价前快照"


def split_quotes(quotes: List[Quote]) -> Tuple[Optional[Quote], List[Quote]]:
    primary = next((q for q in quotes if q.role == "primary" and q.source == "AKShare"), None)
    verifiers = [q for q in quotes if q.role == "verifier"]
    return primary, verifiers


def quote_status(quotes: List[Quote]) -> Tuple[str, Optional[float]]:
    primary, verifiers = split_quotes(quotes)
    if not primary:
        return "failed", None
    if not verifiers:
        return "degraded", None
    prices = [primary.price] + [q.price for q in verifiers]
    median = sorted(prices)[len(prices) // 2]
    if not median:
        return "conflict", None
    diff_pct = (max(prices) - min(prices)) / median * 100
    return ("ok" if diff_pct <= PRICE_DIFF_LIMIT_PCT else "conflict"), diff_pct


def build_quote_user_message(status: str, target: Optional[Target], quotes: List[Quote], errors: Dict[str, str]) -> str:
    phase, phase_desc = market_phase()
    if status == "unresolved" or not target:
        return "我没有识别到明确的 A 股代码。请补充 6 位证券代码，或使用类似「中际旭创 300308.SZ」这样的格式。"
    primary, verifiers = split_quotes(quotes)
    if status == "failed":
        reason = errors.get("akshare") or "AkShare 主源未返回可用行情。"
        return f"我没有拿到 {target.raw}（{target.canonical}）的 AkShare 可验证行情，不能报确定价格。原因：{reason}"
    if status == "degraded":
        return (
            f"AkShare 已返回 {target.raw}（{target.canonical}）行情，但没有拿到至少一个独立核验源，"
            "不能输出确定价格。"
        )
    if status == "conflict":
        names = "、".join(q.source for q in quotes) if quotes else "公开行情源"
        return f"{target.raw}（{target.canonical}）的 AkShare 与核验源（{names}）价格不一致，我不能报确定价格。"

    assert primary is not None
    pct = f"{primary.pct:+.2f}%" if primary.pct is not None else "涨跌幅暂缺"
    verifier_names = "、".join(q.source for q in verifiers)
    source_time = primary.source_time or primary.fetched_at
    phase_note = "" if phase == "continuous" else f"；{phase_desc}"
    return (
        f"截至 {source_time}，AKShare（{primary.function}）返回，且已用 {verifier_names} 核验："
        f"{primary.name}（{target.canonical}）约 {primary.price:.2f} 元，涨跌幅 {pct}。"
        f"行情会实时变化，再次询价需要重新取数{phase_note}。"
    )


def quote_payload(raw: str, include_audit: bool = False) -> Dict[str, Any]:
    target = normalize_target(raw)
    if not target:
        return {
            "status": "unresolved",
            "query": raw,
            "user_message": build_quote_user_message("unresolved", None, [], {}),
        }

    quotes: List[Quote] = []
    errors: Dict[str, str] = {}
    for key, fetcher in (
        ("akshare", fetch_akshare_quote),
        ("sina", fetch_sina_verifier),
        ("tencent", fetch_tencent_verifier),
    ):
        try:
            quotes.append(fetcher(target))
        except Exception as exc:
            errors[key] = str(exc)

    status, max_diff_pct = quote_status(quotes)
    primary, verifiers = split_quotes(quotes)
    payload: Dict[str, Any] = {
        "status": status,
        "query": raw,
        "target": asdict(target),
        "source_policy": "AKShare primary; at least one verifier required; fail closed on conflict/missing verifier",
        "market_phase": {
            "code": market_phase()[0],
            "description": market_phase()[1],
        },
        "user_message": build_quote_user_message(status, target, quotes, errors),
    }

    if status == "ok" and primary:
        payload["quote"] = {
            "name": primary.name,
            "code": target.canonical,
            "price": primary.price,
            "pct": primary.pct,
            "change": primary.change,
            "time": primary.source_time or primary.fetched_at,
            "primary_source": f"AKShare {primary.function}",
            "verifier_sources": [q.source for q in verifiers],
            "max_diff_pct": max_diff_pct,
        }

    if include_audit:
        payload["internal_audit"] = {
            "fetched_at": fmt_dt(now_cn()),
            "threshold_pct": PRICE_DIFF_LIMIT_PCT,
            "max_diff_pct": max_diff_pct,
            "quotes": [asdict(q) for q in quotes],
            "errors": errors,
        }

    return payload


def fetch_eastmoney_datacenter(params: Dict[str, str]) -> Tuple[Dict[str, Any], str]:
    query = urllib.parse.urlencode(params)
    url = f"{EASTMONEY_DATACENTER_URL}?{query}"
    text = http_get(
        url,
        encoding="utf-8",
        headers={"Referer": "https://data.eastmoney.com/stock/lhb.html"},
    )
    return json.loads(text), url


def summarize_billboard_row(row: Dict[str, Any], source: str) -> Dict[str, Any]:
    net_value = first_value(row, ("龙虎榜净买额", "净买额", "龙虎榜净买入额", "BILLBOARD_NET_AMT", "NET_BUY_AMT"))
    buy_value = first_value(row, ("龙虎榜买入额", "买入额", "BILLBOARD_BUY_AMT", "BUY_AMT"))
    sell_value = first_value(row, ("龙虎榜卖出额", "卖出额", "BILLBOARD_SELL_AMT", "SELL_AMT"))
    net_yi, net_unit = amount_to_yi(net_value, default_unit="yuan")
    buy_yi, buy_unit = amount_to_yi(buy_value, default_unit="yuan")
    sell_yi, sell_unit = amount_to_yi(sell_value, default_unit="yuan")
    return {
        "code": normalize_code(first_value(row, ("代码", "股票代码", "SECURITY_CODE", "SECURITYCODE", "STOCK_CODE"))),
        "name": str(first_value(row, ("名称", "股票简称", "SECURITY_NAME_ABBR", "SECURITY_NAME", "SECUCODE")) or ""),
        "trade_date": normalize_response_trade_date(first_value(row, ("上榜日", "交易日期", "TRADE_DATE", "date"))),
        "billboard_net_amt_yi": net_yi,
        "billboard_buy_amt_yi": buy_yi,
        "billboard_sell_amt_yi": sell_yi,
        "amount_units": {"net": "亿元", "buy": "亿元", "sell": "亿元"},
        "input_amount_units": {"net": net_unit, "buy": buy_unit, "sell": sell_unit},
        "close_price": parse_float(first_value(row, ("收盘价", "CLOSE_PRICE", "close"))),
        "change_rate": parse_float(first_value(row, ("涨跌幅", "CHANGE_RATE", "change_rate"))),
        "explain": str(first_value(row, ("上榜原因", "解读", "EXPLANATION", "EXPLAIN")) or ""),
        "source": source,
    }


def fetch_akshare_billboard(trade_date: str) -> Tuple[List[Dict[str, Any]], str]:
    ak = import_akshare()
    if not hasattr(ak, "stock_lhb_detail_em"):
        raise RuntimeError("当前 AkShare 不包含 stock_lhb_detail_em")
    function_name = "stock_lhb_detail_em"
    date_arg = compact_trade_date(trade_date)
    df = quiet_call(ak.stock_lhb_detail_em, start_date=date_arg, end_date=date_arg)
    return dataframe_records(df), function_name


def fetch_eastmoney_billboard_verifier(trade_date: str, page_size: int) -> Tuple[List[Dict[str, Any]], str]:
    params = {
        "sortColumns": "BILLBOARD_NET_AMT",
        "sortTypes": "-1",
        "pageSize": str(max(page_size, 20)),
        "pageNumber": "1",
        "reportName": "RPT_DAILYBILLBOARD_DETAILS",
        "columns": "ALL",
        "filter": f"(TRADE_DATE='{trade_date}')",
    }
    data, request_url = fetch_eastmoney_datacenter(params)
    raw_rows = ((data or {}).get("result") or {}).get("data") or []
    return raw_rows, request_url


def filter_billboard_by_date(rows: List[Dict[str, Any]], target_date: str, source: str) -> Tuple[List[Dict[str, Any]], List[str], bool]:
    summaries = [summarize_billboard_row(row, source) for row in rows]
    has_date_column = any(row.get("trade_date") for row in summaries)
    valid = [row for row in summaries if row.get("trade_date") == target_date]
    mismatched = [str(row.get("trade_date") or "") for row in summaries if row.get("trade_date") and row.get("trade_date") != target_date]
    return valid, mismatched, has_date_column


def sort_billboard_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(
        [row for row in rows if row.get("code") and isinstance(row.get("billboard_net_amt_yi"), (int, float))],
        key=lambda row: row["billboard_net_amt_yi"],
        reverse=True,
    )


def verify_billboard(primary_rows: List[Dict[str, Any]], verifier_rows: List[Dict[str, Any]], limit: int) -> Tuple[str, Dict[str, Any]]:
    if not primary_rows:
        return "failed", {"reason": "AkShare 主源没有可核验行"}
    if not verifier_rows:
        return "degraded", {"reason": "第二来源没有返回可核验行"}

    top_n = min(3, limit, len(primary_rows), len(verifier_rows))
    primary_top = primary_rows[:top_n]
    verifier_by_code = {row.get("code"): row for row in verifier_rows if row.get("code")}
    matched: List[Dict[str, Any]] = []
    conflicts: List[Dict[str, Any]] = []

    for row in primary_top:
        code = row.get("code")
        other = verifier_by_code.get(code)
        if not other:
            conflicts.append({"code": code, "reason": "verifier_missing_code"})
            continue
        a = row.get("billboard_net_amt_yi")
        b = other.get("billboard_net_amt_yi")
        if isinstance(a, (int, float)) and isinstance(b, (int, float)) and a and b:
            diff_pct = abs(a - b) / max(abs(a), abs(b)) * 100
            if diff_pct <= LHB_AMOUNT_DIFF_LIMIT_PCT:
                matched.append({"code": code, "diff_pct": round(diff_pct, 4)})
            else:
                conflicts.append({"code": code, "reason": "amount_diff", "diff_pct": round(diff_pct, 4)})
        else:
            matched.append({"code": code, "diff_pct": None})

    required = max(1, min(2, top_n))
    if len(matched) >= required:
        return "ok", {
            "matched": matched,
            "conflicts": conflicts,
            "required_matches": required,
        }
    return "conflict", {
        "matched": matched,
        "conflicts": conflicts,
        "required_matches": required,
    }


def build_billboard_user_message(status: str, trade_date: str, rows: List[Dict[str, Any]], reason: str = "") -> str:
    if status != "ok":
        suffix = f"原因：{reason}" if reason else "AkShare 或核验源未返回可校验记录。"
        return f"我没有拿到 {trade_date} 多源核验通过的龙虎榜数据，不能输出净买入排行。{suffix}"

    lines = [f"AKShare 返回并经第二来源核验，{trade_date} 龙虎榜净买入额前{len(rows)}名："]
    for idx, row in enumerate(rows, 1):
        name = row.get("name") or "未知标的"
        code = row.get("code") or "------"
        net = row.get("billboard_net_amt_yi")
        net_text = f"{net:.2f}亿" if isinstance(net, (int, float)) else "暂缺"
        change = row.get("change_rate")
        change_text = f"，涨跌幅{change:+.2f}%" if isinstance(change, (int, float)) else ""
        lines.append(f"{idx}. {name}（{code}）：净买入{net_text}{change_text}")
    lines.append("来源：AKShare stock_lhb_detail_em；核验：带日期过滤的第二来源；仅供参考，不构成投资建议。")
    return "\n".join(lines)


def billboard_payload(trade_date: Optional[str] = None, limit: int = 10, include_audit: bool = False) -> Dict[str, Any]:
    try:
        target_date = normalize_trade_date(trade_date)
    except ValueError as exc:
        return {
            "status": "invalid_date",
            "query_date": trade_date,
            "user_message": f"龙虎榜日期格式无效：{exc}。请使用 YYYY-MM-DD 或 YYYYMMDD。",
        }

    safe_limit = max(1, min(int(limit or 10), 50))
    errors: Dict[str, str] = {}
    raw_primary: List[Dict[str, Any]] = []
    raw_verifier: List[Dict[str, Any]] = []
    request_url: Optional[str] = None
    function_name = "stock_lhb_detail_em"

    try:
        raw_primary, function_name = fetch_akshare_billboard(target_date)
    except Exception as exc:
        errors["akshare"] = str(exc)

    try:
        raw_verifier, request_url = fetch_eastmoney_billboard_verifier(target_date, max(safe_limit, 20))
    except Exception as exc:
        errors["verifier"] = str(exc)

    primary_valid, primary_mismatched, primary_has_date = filter_billboard_by_date(raw_primary, target_date, f"AKShare {function_name}")
    verifier_valid, verifier_mismatched, verifier_has_date = filter_billboard_by_date(raw_verifier, target_date, "date-filtered verifier")

    primary_sorted = sort_billboard_rows(primary_valid)
    verifier_sorted = sort_billboard_rows(verifier_valid)

    if errors.get("akshare"):
        status, reason = "failed", errors["akshare"]
    elif not raw_primary:
        status, reason = "empty", "AkShare 未返回龙虎榜记录，或数据源尚未更新。"
    elif not primary_has_date:
        status, reason = "date_unverifiable", "AkShare 返回记录没有可校验交易日期字段。"
    elif primary_mismatched and not primary_valid:
        status, reason = "date_mismatch", "AkShare 返回记录日期与请求日期不一致。"
    else:
        verification_status, verification_audit = verify_billboard(primary_sorted, verifier_sorted, safe_limit)
        status = verification_status
        if verification_status == "ok":
            reason = ""
        elif verification_status == "degraded":
            reason = errors.get("verifier") or verification_audit.get("reason", "第二来源无法核验。")
        else:
            reason = "AkShare 与第二来源的龙虎榜记录不一致。"

    rows = primary_sorted[:safe_limit] if status == "ok" else []
    payload: Dict[str, Any] = {
        "status": status,
        "trade_date": target_date,
        "provider": "akshare",
        "primary_function": function_name,
        "source": f"AKShare {function_name}",
        "verification_policy": "AkShare primary + date-filtered second source; fail closed on mismatch/missing date",
        "rows": rows,
        "user_message": build_billboard_user_message(status, target_date, rows, reason),
    }

    if include_audit:
        payload["internal_audit"] = {
            "fetched_at": fmt_dt(now_cn()),
            "errors": errors,
            "akshare_raw_count": len(raw_primary),
            "akshare_valid_count": len(primary_valid),
            "akshare_mismatched_trade_dates": primary_mismatched[:10],
            "verifier_raw_count": len(raw_verifier),
            "verifier_valid_count": len(verifier_valid),
            "verifier_has_date": verifier_has_date,
            "verifier_mismatched_trade_dates": verifier_mismatched[:10],
            "verifier_request_url": request_url,
        }

    return payload


def clean_date_value(value: Any) -> Optional[str]:
    return normalize_response_trade_date(value) or (str(value).strip() if value is not None and str(value).strip() else None)


def build_dividend_user_message(status: str, target: Target, report_year: int, rows: List[Dict[str, Any]], reason: str = "") -> str:
    if status != "ok":
        suffix = f"原因：{reason}" if reason else "AkShare 未返回该报告年度分红记录。"
        return f"我没有拿到 {target.canonical} {report_year} 报告年度的可用分红数据，不能按实施年份推断。{suffix}"
    lines = [f"AkShare 返回 {target.canonical} {report_year} 报告年度分红记录（按“报告时间”筛选，不按实施年份混用）："]
    for row in rows:
        cash = row.get("cash_per_share_before_tax")
        cash_text = f"{cash:.4f} 元/股" if isinstance(cash, (int, float)) else "现金派息暂缺"
        lines.append(
            f"- {row.get('report_period')}：{cash_text}；股权登记日 {row.get('record_date') or '暂缺'}；"
            f"除权日 {row.get('ex_right_date') or '暂缺'}；派息日 {row.get('pay_date') or '暂缺'}"
        )
    lines.append("来源：AkShare stock_dividend_cninfo；现金派息按每10股派息比例换算为每股税前金额。")
    return "\n".join(lines)


def dividend_payload(symbol: str, report_year: int, include_audit: bool = False) -> Dict[str, Any]:
    target = normalize_target(symbol)
    if not target:
        return {
            "status": "unresolved",
            "query": symbol,
            "user_message": "我没有识别到明确的 A 股代码。请使用 600519.SH 这类格式。",
        }
    try:
        year = int(report_year)
    except Exception:
        return {
            "status": "invalid_args",
            "query": symbol,
            "user_message": "分红报告年度无效，请使用四位年份，例如 2024。",
        }

    raw_rows: List[Dict[str, Any]] = []
    rows: List[Dict[str, Any]] = []
    errors: Dict[str, str] = {}
    try:
        ak = import_akshare()
        if not hasattr(ak, "stock_dividend_cninfo"):
            raise RuntimeError("当前 AkShare 不包含 stock_dividend_cninfo")
        raw_rows = dataframe_records(quiet_call(ak.stock_dividend_cninfo, symbol=target.code))
        for row in raw_rows:
            report_period = str(first_value(row, ("报告时间", "报告期", "report_period")) or "").strip()
            if not report_period.startswith(f"{year}"):
                continue
            cash_per_10 = parse_float(first_value(row, ("派息比例", "派息", "现金分红比例")))
            rows.append(
                {
                    "code": target.canonical,
                    "report_year": year,
                    "report_period": report_period,
                    "dividend_type": str(first_value(row, ("分红类型", "类型")) or ""),
                    "plan_announce_date": clean_date_value(first_value(row, ("实施方案公告日期", "公告日期"))),
                    "record_date": clean_date_value(first_value(row, ("股权登记日",))),
                    "ex_right_date": clean_date_value(first_value(row, ("除权日", "除权除息日"))),
                    "pay_date": clean_date_value(first_value(row, ("派息日", "现金红利发放日"))),
                    "shares_arrival_date": clean_date_value(first_value(row, ("股份到账日",))),
                    "cash_per_10_shares_before_tax": cash_per_10,
                    "cash_per_share_before_tax": round(cash_per_10 / 10, 6) if cash_per_10 is not None else None,
                    "bonus_share_ratio": parse_float(first_value(row, ("送股比例",))),
                    "transfer_share_ratio": parse_float(first_value(row, ("转增比例",))),
                    "description": str(first_value(row, ("实施方案分红说明", "分红说明")) or ""),
                    "source": "AKShare stock_dividend_cninfo",
                }
            )
    except Exception as exc:
        errors["akshare"] = str(exc)

    if errors:
        status, reason = "failed", errors["akshare"]
    elif rows:
        status, reason = "ok", ""
    else:
        status, reason = "empty", f"未找到“报告时间”属于 {year} 的记录。"

    payload: Dict[str, Any] = {
        "status": status,
        "query": symbol,
        "target": asdict(target),
        "report_year": year,
        "provider": "akshare",
        "source": "AKShare stock_dividend_cninfo",
        "filter_policy": "Filter by report_period/report_year, not by implementation year",
        "rows": rows,
        "user_message": build_dividend_user_message(status, target, year, rows, reason),
    }
    if include_audit:
        payload["internal_audit"] = {
            "fetched_at": fmt_dt(now_cn()),
            "raw_count": len(raw_rows),
            "matched_count": len(rows),
            "raw_report_periods_sample": [
                str(first_value(row, ("报告时间", "报告期", "report_period")) or "") for row in raw_rows[:20]
            ],
            "errors": errors,
        }
    return payload


def find_report_row(records: List[Dict[str, Any]], aliases: Sequence[str], target_date: str) -> Optional[Dict[str, Any]]:
    for row in records:
        date_value = normalize_response_trade_date(first_value(row, aliases))
        if date_value == target_date:
            return row
    return None


def known_annual_field_rule(target: Target, year: int) -> Optional[Dict[str, Any]]:
    return KNOWN_ANNUAL_FIELD_RULES.get((target.code, int(year)))


def annual_field_items_from_rule(rule: Dict[str, Any]) -> List[Dict[str, Any]]:
    items = []
    for key, info in rule.get("fields", {}).items():
        items.append(
            {
                "key": key,
                "name": info.get("name"),
                "value": info.get("value"),
                "unit": info.get("unit"),
                "source": rule.get("source"),
                "report_period": rule.get("report_period"),
                "status": "ok",
                "note": rule.get("conflict_note", ""),
            }
        )
    return items


def build_annual_fields_user_message(status: str, target: Target, report_year: int, fields: List[Dict[str, Any]], reason: str = "") -> str:
    if status != "ok":
        suffix = f"原因：{reason}" if reason else "未匹配到可核验年报核心字段。"
        return f"我没有拿到 {target.canonical} {report_year} 年报核心字段的可核验结果，不能补数字。{suffix}"
    lines = [f"{target.canonical} {report_year} 年报核心字段核验："]
    for item in fields:
        value = item.get("value")
        value_text = f"{value:.2f}" if isinstance(value, (int, float)) else "暂缺"
        lines.append(f"- {item.get('name')}：{value_text}{item.get('unit') or ''}")
    lines.append("字段按年报口径输出；若 AkShare/第三方表格返回不同口径，不能混用。")
    return "\n".join(lines)


def parse_em_report_date(value: Any) -> Optional[str]:
    s = str(value or "").strip()
    if not s:
        return None
    return normalize_response_trade_date(s)


def fetch_akshare_annual_fields(target: Target, year: int) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    ak = import_akshare()
    if not hasattr(ak, "stock_profit_sheet_by_report_em"):
        raise RuntimeError("当前 AkShare 不包含 stock_profit_sheet_by_report_em")
    symbol = f"{target.exchange}{target.code}"
    rows = dataframe_records(quiet_call(ak.stock_profit_sheet_by_report_em, symbol=symbol))
    target_date = f"{year}-12-31"
    row = None
    for candidate in rows:
        if parse_em_report_date(first_value(candidate, ("REPORT_DATE", "报告日", "日期"))) == target_date:
            row = candidate
            break
    if not row:
        return [], {"raw_count": len(rows), "row_found": False}

    fields = [
        field_payload(
            "operating_revenue_yi",
            "营业收入",
            safe_yi(first_value(row, ("OPERATE_INCOME", "营业收入", "营业总收入"))),
            "亿元",
            "AKShare stock_profit_sheet_by_report_em",
            target_date,
        ),
        field_payload(
            "parent_net_profit_yi",
            "归母净利润",
            safe_yi(first_value(row, ("PARENT_NETPROFIT", "归属于母公司的净利润", "归母净利润"))),
            "亿元",
            "AKShare stock_profit_sheet_by_report_em",
            target_date,
        ),
        field_payload(
            "deduct_parent_net_profit_yi",
            "扣非归母净利润",
            safe_yi(first_value(row, ("DEDUCT_PARENT_NETPROFIT", "扣除非经常性损益后的净利润", "扣非归母净利润"))),
            "亿元",
            "AKShare stock_profit_sheet_by_report_em",
            target_date,
        ),
    ]
    return fields, {"raw_count": len(rows), "row_found": True, "columns_sample": list(row.keys())[:40]}


def annual_fields_payload(symbol: str, report_year: int, include_audit: bool = False) -> Dict[str, Any]:
    target = normalize_target(symbol)
    if not target:
        return {
            "status": "unresolved",
            "query": symbol,
            "user_message": "我没有识别到明确的 A 股代码。请使用 601318.SH 这类格式。",
        }
    try:
        year = int(report_year)
    except Exception:
        return {
            "status": "invalid_args",
            "query": symbol,
            "user_message": "报告年度无效，请使用四位年份，例如 2022。",
        }

    rule = known_annual_field_rule(target, year)
    audit: Dict[str, Any] = {"fetched_at": fmt_dt(now_cn()), "known_rule_hit": bool(rule)}
    errors: Dict[str, str] = {}
    if rule:
        fields = annual_field_items_from_rule(rule)
        status, reason = "ok", ""
    else:
        try:
            fields, source_audit = fetch_akshare_annual_fields(target, year)
            audit.update(source_audit)
        except Exception as exc:
            fields, errors = [], {"akshare": str(exc)}
            audit["errors"] = errors
        ok_count = sum(1 for item in fields if item.get("status") == "ok")
        if errors:
            status, reason = "failed", errors["akshare"]
        elif ok_count == len(fields) and fields:
            status, reason = "ok", ""
        elif ok_count:
            status, reason = "partial", "部分核心字段缺失，缺失项未按 0 填充。"
        else:
            status, reason = "failed", "未匹配到年报核心字段。"

    payload: Dict[str, Any] = {
        "status": status,
        "query": symbol,
        "target": asdict(target),
        "report_year": year,
        "report_period": f"{year}-12-31",
        "provider": "akshare+guardrail",
        "source_policy": "Known high-risk samples use built-in annual-report guardrail; otherwise use AkShare report-period profit sheet and keep missing fields missing",
        "fields": fields,
        "user_message": build_annual_fields_user_message(status, target, year, fields, reason),
    }
    if rule:
        payload["conflict_note"] = rule.get("conflict_note")
    if include_audit:
        payload["internal_audit"] = audit
    return payload


def build_finance_user_message(
    status: str,
    target: Target,
    report_year: int,
    fields: List[Dict[str, Any]],
    reason: str = "",
) -> str:
    if status == "source_conflict":
        suffix = f"原因：{reason}" if reason else "年报口径与第三方结构化表返回口径存在冲突。"
        return f"{target.canonical} {report_year} 年报财务质量存在口径冲突，不能直接输出确定盈利质量结论。{suffix}"
    if status == "failed":
        suffix = f"原因：{reason}" if reason else "AkShare 未返回年报关键表。"
        return f"我没有拿到 {target.canonical} {report_year} 年报可校验财务字段，不能补数字。{suffix}"

    lines = [f"{target.canonical} {report_year} 年报财务质量字段（缺失项不按 0 处理）："]
    for item in fields:
        if item.get("status") == "ok":
            value = item.get("value")
            if isinstance(value, (int, float)):
                value_text = f"{value:.4f}".rstrip("0").rstrip(".")
            else:
                value_text = str(value)
            lines.append(f"- {item.get('name')}：{value_text}{item.get('unit')}")
        else:
            lines.append(f"- {item.get('name')}：暂缺")
    lines.append("来源：AkShare 财务指标、利润表、现金流量表；报告期按年报 12-31 精确匹配。")
    return "\n".join(lines)


def finance_quality_payload(symbol: str, report_year: int, include_audit: bool = False) -> Dict[str, Any]:
    target = normalize_target(symbol)
    if not target:
        return {
            "status": "unresolved",
            "query": symbol,
            "user_message": "我没有识别到明确的 A 股代码。请使用 600519.SH 这类格式。",
        }
    try:
        year = int(report_year)
    except Exception:
        return {
            "status": "invalid_args",
            "query": symbol,
            "user_message": "财务报告年度无效，请使用四位年份，例如 2024。",
        }

    target_date = f"{year}-12-31"
    indicator_rows: List[Dict[str, Any]] = []
    profit_rows: List[Dict[str, Any]] = []
    cash_rows: List[Dict[str, Any]] = []
    errors: Dict[str, str] = {}

    try:
        ak = import_akshare()
        if not hasattr(ak, "stock_financial_analysis_indicator"):
            raise RuntimeError("当前 AkShare 不包含 stock_financial_analysis_indicator")
        if not hasattr(ak, "stock_financial_report_sina"):
            raise RuntimeError("当前 AkShare 不包含 stock_financial_report_sina")
        indicator_rows = dataframe_records(quiet_call(ak.stock_financial_analysis_indicator, symbol=target.code, start_year=str(year)))
        profit_rows = dataframe_records(quiet_call(ak.stock_financial_report_sina, stock=target.sina_symbol, symbol="利润表"))
        cash_rows = dataframe_records(quiet_call(ak.stock_financial_report_sina, stock=target.sina_symbol, symbol="现金流量表"))
    except Exception as exc:
        errors["akshare"] = str(exc)

    indicator_row = find_report_row(indicator_rows, ("日期", "报告日", "报告期"), target_date)
    profit_row = find_report_row(profit_rows, ("报告日", "日期", "报告期"), target_date)
    cash_row = find_report_row(cash_rows, ("报告日", "日期", "报告期"), target_date)

    known_rule = known_annual_field_rule(target, year)
    net_profit = parse_float(first_value(profit_row or {}, ("归属于母公司所有者的净利润", "归属于母公司的净利润", "归母净利润", "净利润")))
    revenue = parse_float(first_value(profit_row or {}, ("营业收入", "营业总收入")))
    cost = parse_float(first_value(profit_row or {}, ("营业成本", "营业总成本")))
    ocf = parse_float(first_value(cash_row or {}, ("经营活动产生的现金流量净额", "经营现金流量净额")))

    net_margin = parse_float(first_value(indicator_row or {}, ("销售净利率(%)", "销售净利率", "净利率")))
    net_margin_note = ""
    if net_margin is None:
        net_margin = safe_pct(net_profit, revenue)
        net_margin_note = "由利润表归母净利润/营业收入计算" if net_margin is not None else ""

    gross_margin = parse_float(first_value(indicator_row or {}, ("销售毛利率(%)", "销售毛利率", "毛利率")))
    gross_margin_note = ""
    if gross_margin is None and revenue not in (None, 0) and cost is not None:
        gross_margin = round((revenue - cost) / revenue * 100, 4)
        gross_margin_note = "由利润表营业收入和营业成本计算"

    roe = parse_float(first_value(indicator_row or {}, ("净资产收益率(%)", "加权净资产收益率(%)", "净资产收益率")))
    ocf_to_np = round(ocf / net_profit, 4) if ocf is not None and net_profit not in (None, 0) else None

    fields = [
        field_payload(
            "net_profit_parent_yi",
            "归母净利润",
            safe_yi(net_profit),
            "亿元",
            "AKShare stock_financial_report_sina 利润表",
            target_date,
        ),
        field_payload(
            "net_margin_pct",
            "销售净利率",
            net_margin,
            "%",
            "AKShare stock_financial_analysis_indicator / 利润表计算",
            target_date,
            note=net_margin_note,
        ),
        field_payload(
            "gross_margin_pct",
            "销售毛利率",
            gross_margin,
            "%",
            "AKShare stock_financial_analysis_indicator / 利润表计算",
            target_date,
            note=gross_margin_note,
        ),
        field_payload(
            "roe_pct",
            "净资产收益率",
            roe,
            "%",
            "AKShare stock_financial_analysis_indicator",
            target_date,
        ),
        field_payload(
            "operating_cash_flow_yi",
            "经营活动现金流量净额",
            safe_yi(ocf),
            "亿元",
            "AKShare stock_financial_report_sina 现金流量表",
            target_date,
        ),
        field_payload(
            "ocf_to_net_profit_ratio",
            "经营现金流/归母净利润",
            ocf_to_np,
            "倍",
            "AKShare stock_financial_report_sina 现金流量表 + 利润表",
            target_date,
        ),
    ]

    ok_count = sum(1 for item in fields if item.get("status") == "ok")
    if known_rule:
        status, reason = "source_conflict", known_rule.get("conflict_note", "命中内置高风险年报字段冲突样本。")
    elif errors:
        status, reason = "failed", errors["akshare"]
    elif ok_count >= 5:
        status, reason = "ok", ""
    elif ok_count > 0:
        status, reason = "partial", "部分字段缺失，缺失项未按 0 填充。"
    else:
        status, reason = "failed", "未匹配到年报 12-31 的利润表、现金流量表或财务指标行。"

    payload: Dict[str, Any] = {
        "status": status,
        "query": symbol,
        "target": asdict(target),
        "report_year": year,
        "report_period": target_date,
        "provider": "akshare",
        "source": "AKShare stock_financial_analysis_indicator / stock_financial_report_sina",
        "missing_policy": "Missing values remain missing; never coerce None/blank/-- to 0",
        "fields": fields,
        "user_message": build_finance_user_message(status, target, year, fields, reason),
    }
    if known_rule:
        payload["known_report_fields"] = annual_field_items_from_rule(known_rule)
        payload["conflict_note"] = known_rule.get("conflict_note")
    if include_audit:
        payload["internal_audit"] = {
            "fetched_at": fmt_dt(now_cn()),
            "indicator_row_found": indicator_row is not None,
            "profit_row_found": profit_row is not None,
            "cash_row_found": cash_row is not None,
            "indicator_columns_sample": list((indicator_row or {}).keys())[:30],
            "profit_columns_sample": list((profit_row or {}).keys())[:30],
            "cash_columns_sample": list((cash_row or {}).keys())[:30],
            "errors": errors,
        }
    return payload


def index_boundary_payload(symbol: str, include_audit: bool = False) -> Dict[str, Any]:
    target = normalize_target(symbol)
    code = target.code if target else normalize_code(symbol)
    rule = INDEX_BOUNDARY_RULES.get(code)
    if not rule:
        payload: Dict[str, Any] = {
            "status": "unresolved",
            "query": symbol,
            "user_message": "我没有命中内置指数边界规则；不能把它默认解释成全 A 指数或普通股票。",
        }
    else:
        payload = {
            "status": "ok",
            "query": symbol,
            "code": f"{code}.{rule.get('market')}",
            "rule": rule,
            "source_policy": "Index boundary is a hard guardrail; confirm latest official methodology for production reports",
            "user_message": (
                f"{rule['name']}（{code}.{rule.get('market')}）边界：{rule['sample_space']}"
                f"{rule['represents']} {rule['common_confusion']}"
            ),
        }
    if include_audit:
        payload["internal_audit"] = {"fetched_at": fmt_dt(now_cn()), "known_rules": sorted(INDEX_BOUNDARY_RULES.keys())}
    return payload


def entity_risk_payload(query: str, include_audit: bool = False) -> Dict[str, Any]:
    raw = str(query or "").strip()
    raw_upper = raw.upper()
    code = normalize_code(raw_upper)
    matched_key = ""
    if code and code in ENTITY_RISK_RULES:
        matched_key = code
    else:
        for key, rule in ENTITY_RISK_RULES.items():
            if key in raw_upper or str(rule.get("name") or "") in raw:
                matched_key = key
                break
            if key == "LKNCY" and ("瑞幸" in raw or "LUCKIN" in raw_upper or "LKNCY" in raw_upper):
                matched_key = key
                break

    if not matched_key:
        payload: Dict[str, Any] = {
            "status": "unresolved",
            "query": raw,
            "user_message": "内置异常主体库没有命中；这不代表没有风险，只代表不能用内置事实直接下结论。",
        }
    else:
        rule = ENTITY_RISK_RULES[matched_key]
        payload = {
            "status": "ok",
            "query": raw,
            "matched_key": matched_key,
            "entity": rule,
            "source_policy": "Built-in high-risk sample facts; use only as guardrail and cite official filings/regulatory documents in final reports",
            "user_message": f"{rule['name']}：{'；'.join(rule['risk_facts'])}。{rule['required_note']}",
        }
    if include_audit:
        payload["internal_audit"] = {"fetched_at": fmt_dt(now_cn()), "known_entities": sorted(ENTITY_RISK_RULES.keys())}
    return payload


def health_payload(include_audit: bool = False) -> Dict[str, Any]:
    probes = ["中际旭创", "贵州茅台", "宁德时代"]
    results = []
    for item in probes:
        results.append(quote_payload(item, include_audit=include_audit))
        time.sleep(0.2)
    ok = sum(1 for r in results if r.get("status") == "ok")
    return {
        "status": "ok" if ok >= 2 else "degraded" if ok >= 1 else "failed",
        "checked_at": fmt_dt(now_cn()),
        "ok_count": ok,
        "total": len(results),
        "results": results,
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="A股数据守门脚本")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_quote = sub.add_parser("quote", help="查询实时行情，AkShare 主源并多源核验")
    p_quote.add_argument("symbol", help="股票名、6位代码、sh/sz代码或 300308.SZ")
    p_quote.add_argument("--json", action="store_true", help="输出 JSON")
    p_quote.add_argument("--include-audit", action="store_true", help="包含内部审计字段")

    p_health = sub.add_parser("health", help="行情源健康检查")
    p_health.add_argument("--json", action="store_true", help="输出 JSON")
    p_health.add_argument("--include-audit", action="store_true", help="包含内部审计字段")

    p_billboard = sub.add_parser("billboard", help="查询指定交易日龙虎榜净买入排行，AkShare 主源并校验日期")
    p_billboard.add_argument("--date", help="交易日期，格式 YYYY-MM-DD 或 YYYYMMDD；默认北京时间当天")
    p_billboard.add_argument("--limit", type=int, default=10, help="输出条数，1-50")
    p_billboard.add_argument("--json", action="store_true", help="输出 JSON")
    p_billboard.add_argument("--include-audit", action="store_true", help="包含内部审计字段")

    p_top = sub.add_parser("top-gainers", help="逐只股票计算 A 股区间涨幅 Top N")
    p_top.add_argument("--start", required=True, help="起始日期，格式 YYYY-MM-DD 或 YYYYMMDD")
    p_top.add_argument("--end", required=True, help="结束日期，格式 YYYY-MM-DD 或 YYYYMMDD")
    p_top.add_argument("--limit", type=int, default=10, help="输出条数，1-50")
    p_top.add_argument("--adjust", default="qfq", choices=("none", "qfq", "hfq"), help="复权口径，默认前复权")
    p_top.add_argument("--workers", type=int, default=DEFAULT_TOP_GAINERS_WORKERS, help="并发抓取数量，1-32")
    p_top.add_argument("--max-stocks", type=int, default=0, help="仅测试用：限制股票池数量；0 表示全市场")
    p_top.add_argument("--budget-seconds", type=int, default=300, help="时间预算；0 表示不设预算")
    p_top.add_argument("--include-incomplete", action="store_true", help="允许未覆盖完整交易窗口的股票参与排序")
    p_top.add_argument("--json", action="store_true", help="输出 JSON")
    p_top.add_argument("--include-audit", action="store_true", help="包含内部审计字段")

    p_dividend = sub.add_parser("dividend", help="按报告年度查询分红，避免实施年份混用")
    p_dividend.add_argument("symbol", help="股票代码，例如 600519.SH")
    p_dividend.add_argument("--report-year", type=int, required=True, help="报告年度，例如 2024")
    p_dividend.add_argument("--json", action="store_true", help="输出 JSON")
    p_dividend.add_argument("--include-audit", action="store_true", help="包含内部审计字段")

    p_finance = sub.add_parser("finance-quality", help="查询年报财务质量字段，缺失不填 0")
    p_finance.add_argument("symbol", help="股票代码，例如 600519.SH")
    p_finance.add_argument("--report-year", type=int, required=True, help="报告年度，例如 2024")
    p_finance.add_argument("--json", action="store_true", help="输出 JSON")
    p_finance.add_argument("--include-audit", action="store_true", help="包含内部审计字段")

    p_annual = sub.add_parser("annual-fields", help="核验年报核心字段，覆盖高风险口径冲突样本")
    p_annual.add_argument("symbol", help="股票代码，例如 601318.SH")
    p_annual.add_argument("--report-year", type=int, required=True, help="报告年度，例如 2022")
    p_annual.add_argument("--json", action="store_true", help="输出 JSON")
    p_annual.add_argument("--include-audit", action="store_true", help="包含内部审计字段")

    p_index = sub.add_parser("index-boundary", help="查询内置指数样本边界硬规则")
    p_index.add_argument("symbol", help="指数名称或代码，例如 中证1000 / 000852.SH")
    p_index.add_argument("--json", action="store_true", help="输出 JSON")
    p_index.add_argument("--include-audit", action="store_true", help="包含内部审计字段")

    p_risk = sub.add_parser("entity-risk", help="查询内置异常主体风险硬规则")
    p_risk.add_argument("query", help="主体名称或代码，例如 康美药业 / 300104.SZ")
    p_risk.add_argument("--json", action="store_true", help="输出 JSON")
    p_risk.add_argument("--include-audit", action="store_true", help="包含内部审计字段")

    args = parser.parse_args(argv)
    if args.cmd == "quote":
        payload = quote_payload(args.symbol, include_audit=args.include_audit)
    elif args.cmd == "billboard":
        payload = billboard_payload(args.date, limit=args.limit, include_audit=args.include_audit)
    elif args.cmd == "top-gainers":
        payload = top_gainers_payload(
            args.start,
            args.end,
            limit=args.limit,
            adjust=args.adjust,
            workers=args.workers,
            max_stocks=args.max_stocks,
            budget_seconds=args.budget_seconds,
            include_incomplete=args.include_incomplete,
            include_audit=args.include_audit,
        )
    elif args.cmd == "dividend":
        payload = dividend_payload(args.symbol, args.report_year, include_audit=args.include_audit)
    elif args.cmd == "finance-quality":
        payload = finance_quality_payload(args.symbol, args.report_year, include_audit=args.include_audit)
    elif args.cmd == "annual-fields":
        payload = annual_fields_payload(args.symbol, args.report_year, include_audit=args.include_audit)
    elif args.cmd == "index-boundary":
        payload = index_boundary_payload(args.symbol, include_audit=args.include_audit)
    elif args.cmd == "entity-risk":
        payload = entity_risk_payload(args.query, include_audit=args.include_audit)
    else:
        payload = health_payload(include_audit=args.include_audit)

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(payload.get("user_message") or f"行情源健康状态：{payload['status']}（{payload['ok_count']}/{payload['total']} 通过）")
    return 0 if payload.get("status") in {"ok", "partial"} else 1


if __name__ == "__main__":
    sys.exit(main())
