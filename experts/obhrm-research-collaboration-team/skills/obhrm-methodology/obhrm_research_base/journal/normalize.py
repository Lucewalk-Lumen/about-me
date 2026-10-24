"""ISSN / 刊名归一化工具。

所有来源解析器、查询引擎、API 共用本模块，禁止在别处重复实现。

说明：

``norm_issn`` 为**强校验**：清洗后必须恰好 8 位且通过 ISSN mod-11 校验位
（第 8 位可为 ``X``=10）；否则返回 ``None``。仅做「去非数字」会导致
``"oxford"`` → ``"x"``、``"2020-2024"`` → ``"20202024"`` 这类明显非 ISSN 的输入
也能拿到一个「看起来合法」的 norm，进而被当作真实刊号参与跨源合并/查询，污染数据。

``is_issn_like`` 收紧为仅接受标准 ISSN 形态 ``^\\d{4}-?\\d{3}[\\dxX]$``，删除原先
``"-" in keyword and len(core)>=7`` 的兜底（它会把 ``"1990-2020"`` 这种年份区间
误判为 ISSN）。
"""

from __future__ import annotations

import re

# 强校验正则：8 位，前 7 位数字 + 第 8 位校验位（数字或 X）。
_ISSN_STRICT_RE = re.compile(r"^\d{7}[\dxX]$")
# 年份区间形态（如 1990-2020 / 2020-2024）：两个 4 位组均落在合理年份区间时，
# 即使清洗后巧合通过 mod-11，也应拒绝（它不是 ISSN）。
_YEAR_RANGE_RE = re.compile(r"^\s*(\d{4})[\s\-.](\d{4})\s*$")


def _looks_like_year_range(s: str) -> bool:
    """判断输入是否像「年份区间」（如 1990-2020）。

    真实 ISSN 的 suffix 组（如 ``1007`` / ``7009`` / ``123X``）几乎不会落在
    ``[1900, 2099]`` 内；而 ``2020-2024`` 这种「起止年份」两段都会落在范围内。
    此判定用于把「巧合通过 mod-11 的非 ISSN 输入」挡在门外（要求
    ``norm_issn("2020-2024")`` / ``("1990-2024")`` 均返回 ``None``）。
    """
    m = _YEAR_RANGE_RE.match(s)
    if not m:
        return False
    try:
        a, b = int(m.group(1)), int(m.group(2))
    except ValueError:
        return False
    return 1900 <= a <= 2099 and 1900 <= b <= 2099


def _issn_check_digit_valid(s: str) -> bool:
    """ISSN mod-11 校验位验证。

    权重 8..1 依次乘 8 位字符（``X``/``x``=10），加权和须为 11 的倍数。
    """
    total = 0
    for i, ch in enumerate(s):
        d = 10 if ch in "xX" else int(ch)
        total += d * (8 - i)
    return total % 11 == 0


def norm_issn(s: object | None) -> str | None:
    """归一化 ISSN（强校验）。

    规则：
    1. 拒绝形如 ``YYYY-YYYY`` 的年份区间（即便清洗后巧合通过 mod-11）。
    2. 去除所有非数字与非末位 ``x`` 的字符（统一小写）。
    3. 必须恰好 8 位且通过 mod-11 校验位，否则返回 ``None``。

    print ISSN 或 eISSN 任一命中即视为同一刊。无有效内容时返回 ``None``。

    示例：
        ``norm_issn("oxford")``        → ``None``
        ``norm_issn("2020-2024")``     → ``None``
        ``norm_issn("see note 7")``    → ``None``
        ``norm_issn("1990-2024")``     → ``None``
        ``norm_issn("2168-1007")``     → ``"21681007"``
        ``norm_issn("1537-260X")``     → ``"1537260x"``
    """
    if s is None:
        return None
    raw = str(s).strip().lower()
    if not raw:
        return None
    # 1) 年份区间直接拒绝
    if _looks_like_year_range(raw):
        return None
    # 2) 仅保留数字与末位可能的 x（ISSN 校验位可为 X=10）
    cleaned = re.sub(r"[^0-9x]", "", raw)
    if not cleaned:
        return None
    # 3) 强校验：8 位 + mod-11 校验位
    if not _ISSN_STRICT_RE.match(cleaned):
        return None
    if not _issn_check_digit_valid(cleaned):
        return None
    return cleaned


def norm_title(s: object | None) -> str:
    """归一化刊名。

    规则：小写、压缩全/半角空白、去除常见标点，便于跨源模糊/精确匹配。
    无有效内容时返回空串。
    """
    if not s:
        return ""
    s = str(s).lower().strip()
    # 全角空格归一
    s = re.sub(r"[\s\u3000]+", " ", s)
    # 去除常见标点
    s = re.sub(r"[().:,&/\-–—]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def norm_query_title(s: object | None, loose: bool = True) -> str:
    """归一化用于「用户查询」的刊名（模糊匹配侧）。

    与入库时使用的 ``norm_title``（激进去标点）互补：本函数更贴近
    用户输入习惯，便于用 ``&`` / ``-`` 等仍可命中库中已归一化的刊名。

    规则（可叠加）：
    1. 去除首尾空白；折叠内部连续空白为单个空格。
    2. 大小写不敏感：整体转小写。
    3. ``loose=True``（默认）时做等价扩展，提升召回：
       - ``&`` 与 ``and`` 等价（互为替换，便于 ``A & B`` 命中 ``A and B``）；
       - ``-`` / ``–`` / ``—``（连字符 / 短破折号 / 长破折号）与空格等价
         （便于 ``Marketing-International`` 命中 ``Marketing International``）。
    4. 保留字母、数字、中文及空格，供 ``LIKE`` 子串模糊匹配。

    返回小写归一串；无任何有效内容时返回空串。
    """
    if not s:
        return ""
    text = str(s).lower().strip()
    text = re.sub(r"\s+", " ", text).strip()
    if loose:
        text = text.replace("&", " and ")
        text = text.replace("–", " ").replace("—", " ")
        text = re.sub(r"-", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
    return text


def is_issn_like(keyword: str) -> bool:
    """判断输入是否像 ISSN（用于查询时选择 ISSN 精确匹配）。

    仅接受标准形态 ``^\\d{4}-?\\d{3}[\\dxX]$``（如 ``2168-1007`` / ``21681007`` /
    ``1537-260X``）。年份区间（``1990-2020``）与松散兜底一律拒绝。
    """
    if not keyword:
        return False
    kw = keyword.strip()
    if _looks_like_year_range(kw):
        return False
    return bool(re.fullmatch(r"\d{4}-?\d{3}[\dxX]", kw))


if __name__ == "__main__":
    # 单测反例：型式校验 + 反例，直接 ``python normalize.py`` 运行。
    import sys

    def _assert(cond, msg):
        if not cond:
            print(f"FAIL: {msg}")
            sys.exit(1)
        print(f"ok: {msg}")

    # 正例
    _assert(norm_issn("2168-1007") == "21681007", "norm_issn valid hyphen")
    _assert(norm_issn("21681007") == "21681007", "norm_issn valid bare")
    _assert(norm_issn("1537-260X") == "1537260x", "norm_issn valid X check")
    # 反例
    _assert(norm_issn("oxford") is None, "norm_issn('oxford') -> None")
    _assert(norm_issn("2020-2024") is None, "norm_issn('2020-2024') -> None")
    _assert(norm_issn("see note 7") is None, "norm_issn('see note 7') -> None")
    _assert(norm_issn("1990-2024") is None, "norm_issn('1990-2024') -> None")
    # is_issn_like 收紧反例
    _assert(is_issn_like("1990-2020") is False, "is_issn_like('1990-2020') -> False")
    _assert(is_issn_like("2020-2024") is False, "is_issn_like('2020-2024') -> False")
    _assert(is_issn_like("oxford") is False, "is_issn_like('oxford') -> False")
    _assert(is_issn_like("2168-1007") is True, "is_issn_like('2168-1007') -> True")
    _assert(is_issn_like("1537-260X") is True, "is_issn_like('1537-260X') -> True")
    print("ALL NORMALIZE TESTS PASSED")
