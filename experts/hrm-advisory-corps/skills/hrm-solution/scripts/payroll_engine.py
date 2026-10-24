#!/usr/bin/env python3
"""HRM Smart Solution Team（HRM 实战参谋团） · 薪酬计算引擎

作者：Xing Bu

功能：
- 个税累计预扣法（2026 综合所得税率表）
- 五险一金（城市级费率，内置北上广深杭示例）
- 年终奖单独计税 + 跳档陷阱检测
- 批量薪资计算

设计原则：
- 全部金额使用 Decimal，避免浮点误差
- 每月计算必须传入前月累计数据
- 数据不落库，由调用方决定归档位置

[!] 政策会调整：城市费率与基数每年 7 月可能变动，使用前核对最新官方数据。
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Dict, List, Optional

from errors import StructuredError


class InputValidationError(StructuredError):
    """薪资入参缺失或类型错误时抛出（fail-fast，杜绝静默算出 gross_pay:0）。

    继承 `StructuredError`（结构化错误码）：携带确定性 `code` / `field`，
    仍保持 `ValueError` 子类，各 CLI 的 `except (ValueError, ArithmeticError)` 不变。
    """


def _is_number(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


# 单笔金额合理上限（HR 场景足够宽：1e12 元 = 1 万亿元）；超过视为越界（E040）。
# 用 Decimal 而非 float：本模块所有金额口径均为 Decimal，float 上限会引入
# 二进制浮点表示误差（1e12 实际为 1000000000000.0000002384…），与 _d() 口径不一致。
_MAX_AMOUNT = Decimal("1e12")


def _validate_payroll_record(data: Dict) -> None:
    """校验单条薪资记录：必填字段齐全且类型正确，可选数值型字段若传必须为数字。

    不回退默认值——缺失或类型错误一律抛 InputValidationError。
    """
    if not isinstance(data, dict):
        raise InputValidationError(f"薪资记录必须是 JSON 对象，实际收到 {type(data).__name__}", code="E020", field=None)

    # 必填且必须 number
    for key in ("baseSalary",):
        if key not in data:
            raise InputValidationError(
                f"必填字段 `{key}` 缺失（注意：入参键名为 camelCase，"
                f"传成 snake_case 如 base_salary 会被视为缺失）。",
                code="E001", field=key,
            )
        if not _is_number(data[key]):
            raise InputValidationError(
                f"字段 `{key}` 必须是数字，实际收到 {data[key]!r}（{type(data[key]).__name__}）",
                code="E020", field=key,
            )
        if data[key] <= 0:
            raise InputValidationError(
                f"字段 `{key}` 必须大于 0，实际收到 {data[key]!r}"
                f"（基本工资为 0 或负数时，社保公积金仍会按城市下限基数代扣，"
                f"实发工资必然为负，属无效薪资记录）",
                code="E040", field=key,
            )
        if data[key] > _MAX_AMOUNT:
            raise InputValidationError(
                f"字段 `{key}` 超出合理范围（上限 1e12），实际收到 {data[key]!r}",
                code="E040", field=key,
            )

    # 必填且必须 str
    if "city" not in data:
        raise InputValidationError("必填字段 `city` 缺失（如：北京/上海/广州/深圳/杭州）", code="E001", field="city")
    if not isinstance(data["city"], str):
        raise InputValidationError(f"`city` 必须是字符串，实际收到 {data['city']!r}", code="E020", field="city")

    # 年/月
    year = data.get("year", 2026)
    month = data.get("month", 1)
    if not isinstance(year, int) or isinstance(year, bool) or year < 2000 or year > 2100:
        raise InputValidationError(f"`year` 必须是 2000-2100 的整数，实际收到 {year!r}", code="E020", field="year")
    if not isinstance(month, int) or isinstance(month, bool) or month < 1 or month > 12:
        raise InputValidationError(f"`month` 必须是 1-12 的整数，实际收到 {month!r}", code="E020", field="month")

    # 可选数值型字段：若传入则必须为数字且非负
    optional_numeric = (
        "positionAllowance", "performanceBonus", "overtimePay",
        "otherIncome", "otherDeductions", "specialDeduction", "insuranceBase",
        "cumulativeTaxPaid", "cumulativeIncome", "cumulativeInsurance", "cumulativeSpecial",
    )
    for key in optional_numeric:
        if key in data and data[key] is not None:
            if not _is_number(data[key]):
                raise InputValidationError(
                    f"可选字段 `{key}` 若为数字类型，实际收到 {data[key]!r}（{type(data[key]).__name__}）",
                    code="E020", field=key,
                )
            if data[key] < 0:
                raise InputValidationError(f"可选字段 `{key}` 不能为负数，实际收到 {data[key]!r}", code="E040", field=key)
            if data[key] > _MAX_AMOUNT:
                raise InputValidationError(
                    f"可选字段 `{key}` 超出合理范围（上限 1e12），实际收到 {data[key]!r}",
                    code="E040", field=key,
                )

    # 累计值必须完整提供或不提供：部分提供会混合真实累计与近似，导致重复征税
    cum_keys = ("cumulativeIncome", "cumulativeInsurance", "cumulativeSpecial")
    provided = [k for k in cum_keys if k in data and data[k] is not None]
    if 0 < len(provided) < len(cum_keys):
        missing = [k for k in cum_keys if k not in provided]
        raise InputValidationError(
            f"累计值必须完整提供或不提供：检测到 {provided}，但缺少 {missing}。"
            f"请同时提供 cumulativeIncome/cumulativeInsurance/cumulativeSpecial，"
            f"或三者都不提供（退化为每月恒定近似）。",
            code="E060", field=None,
        )

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

MONTHLY_DEDUCTION = Decimal("5000") # 每月减除费用（基本）

# 2026 综合所得税率表（年度累计应纳税所得额）
ANNUAL_TAX_BRACKETS: List[Dict[str, Decimal]] = [
    {"upper": Decimal("36000"), "rate": Decimal("0.03"), "deduction": Decimal("0")},
    {"upper": Decimal("144000"), "rate": Decimal("0.10"), "deduction": Decimal("2520")},
    {"upper": Decimal("300000"), "rate": Decimal("0.20"), "deduction": Decimal("16920")},
    {"upper": Decimal("420000"), "rate": Decimal("0.25"), "deduction": Decimal("31920")},
    {"upper": Decimal("660000"), "rate": Decimal("0.30"), "deduction": Decimal("52920")},
    {"upper": Decimal("960000"), "rate": Decimal("0.35"), "deduction": Decimal("85920")},
    {"upper": None, "rate": Decimal("0.45"), "deduction": Decimal("181920")},
]

# 年终奖月度税率表（年终奖 ÷ 12 查表）
BONUS_MONTHLY_BRACKETS: List[Dict[str, Decimal]] = [
    {"upper": Decimal("3000"), "rate": Decimal("0.03"), "deduction": Decimal("0")},
    {"upper": Decimal("12000"), "rate": Decimal("0.10"), "deduction": Decimal("210")},
    {"upper": Decimal("25000"), "rate": Decimal("0.20"), "deduction": Decimal("1410")},
    {"upper": Decimal("35000"), "rate": Decimal("0.25"), "deduction": Decimal("2660")},
    {"upper": Decimal("55000"), "rate": Decimal("0.30"), "deduction": Decimal("4410")},
    {"upper": Decimal("80000"), "rate": Decimal("0.35"), "deduction": Decimal("7160")},
    {"upper": None, "rate": Decimal("0.45"), "deduction": Decimal("15160")},
]

# 年终奖跳档陷阱区间（税后收入不增反降）
BONUS_TRAP_RANGES: List[tuple] = [
    (Decimal("36000"), Decimal("38566.67")),
    (Decimal("144000"), Decimal("160500.00")),
    (Decimal("300000"), Decimal("318333.33")),
    (Decimal("420000"), Decimal("447500.00")),
    (Decimal("660000"), Decimal("706538.46")),
    (Decimal("960000"), Decimal("1120000.00")),
]


def _d(x) -> Decimal:
    return Decimal(str(x))


def _money(x: Decimal) -> Decimal:
    return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# ---------------------------------------------------------------------------
# 社保公积金配置
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class InsuranceConfig:
    city: str
    year: int
    pension_ee: Decimal # 养老个人
    pension_er: Decimal # 养老单位
    medical_ee: Decimal
    medical_er: Decimal
    unemp_ee: Decimal
    unemp_er: Decimal
    injury_er: Decimal
    maternity_er: Decimal
    fund_ee: Decimal # 公积金个人
    fund_er: Decimal # 公积金单位
    base_floor: Decimal
    base_ceiling: Decimal
    fund_floor: Decimal


def _city_configs() -> Dict[str, InsuranceConfig]:
    """内置城市配置（2026 基准示例数据，使用前须核对当年官方政策）。

    个人(EE)费率全国统筹统一，故各城市相同（养老8%/医疗2%/失业0.5%）。
    单位(ER)费率随城市/统筹区与行业不同，须分化；本表依据公开资料给出基准示例，
    仅作演示，正式核算请以当地社保/公积金中心当年通告为准。
    """
    C = {}
    for city, floor, ceil, ffloor, er in [
        # 北京
        ("北京", 6821, 35283, 2420, dict(pension_er="0.16", medical_er="0.09", unemp_er="0.005", injury_er="0.004", maternity_er="0.008", fund_er="0.12")),
        # 上海：公积金单位 5%-7%，取 7% 上限示例
        ("上海", 7384, 36921, 2590, dict(pension_er="0.16", medical_er="0.095", unemp_er="0.005", injury_er="0.004", maternity_er="0.010", fund_er="0.07")),
        # 广州：公积金 5%-12%，取 5% 示例
        ("广州", 5284, 26421, 2300, dict(pension_er="0.16", medical_er="0.065", unemp_er="0.005", injury_er="0.004", maternity_er="0.0085", fund_er="0.05")),
        # 深圳：医疗单位费率 5%（2025 年起降费后延续）；失业单位 0.8%；生育并入医疗故 0；公积金 5%-12% 取 5%
        ("深圳", 2360, 34968, 2360, dict(pension_er="0.16", medical_er="0.05", unemp_er="0.008", injury_er="0.004", maternity_er="0.000", fund_er="0.05")),
        # 杭州
        ("杭州", 4462, 22311, 2280, dict(pension_er="0.16", medical_er="0.095", unemp_er="0.005", injury_er="0.004", maternity_er="0.0085", fund_er="0.12")),
    ]:
        C[city] = InsuranceConfig(
            city=city, year=2026,
            pension_ee=_d("0.08"), pension_er=_d(er["pension_er"]),
            medical_ee=_d("0.02"), medical_er=_d(er["medical_er"]),
            unemp_ee=_d("0.005"), unemp_er=_d(er["unemp_er"]),
            injury_er=_d(er["injury_er"]), maternity_er=_d(er["maternity_er"]),
            fund_ee=_d("0.12"), fund_er=_d(er["fund_er"]),
            base_floor=Decimal(floor), base_ceiling=Decimal(ceil),
            fund_floor=Decimal(ffloor),
        )
    return C


CITY_CONFIGS: Dict[str, InsuranceConfig] = _city_configs()


def verify_city_rates() -> None:
    """回归守卫：雇主费率须随城市分化，禁止静默回退为全相同占位数据。

    个人(EE)费率为全国统筹统一，不在检查范围；仅校验随城市变化的
    medical_er / unemp_er / maternity_er / fund_er。若某字段在所有城市取值相同，
    视为未分化的占位数据并立即报错，防止占位数据导致静默错误。
    """
    for f in ("medical_er", "unemp_er", "maternity_er", "fund_er"):
        vals = {str(CITY_CONFIGS[c].__dict__[f]) for c in CITY_CONFIGS}
        if len(vals) <= 1:
            raise AssertionError(
                f"城市 {f} 费率在所有城市取值相同（{vals}），疑似未分化的占位数据；"
                f"请核对各城市真实费率后再发布。"
            )


def _clamp(base: Decimal, floor: Decimal, ceiling: Decimal) -> Decimal:
    if base < floor:
        return floor
    if base > ceiling:
        return ceiling
    return base


def _find_bracket(amount: Decimal, brackets: List[Dict[str, Decimal]]) -> Dict[str, Decimal]:
    for b in brackets:
        if b["upper"] is None or amount <= b["upper"]:
            return b
    return brackets[-1]


# ---------------------------------------------------------------------------
# 结果结构
# ---------------------------------------------------------------------------

@dataclass
class MonthPayroll:
    year: int
    month: int
    employee_id: str
    employee_name: str
    gross_pay: Decimal
    pension: Decimal = Decimal("0")
    medical: Decimal = Decimal("0")
    unemployment: Decimal = Decimal("0")
    housing_fund: Decimal = Decimal("0")
    total_insurance: Decimal = Decimal("0")
    other_deductions: Decimal = Decimal("0")
    taxable_income: Decimal = Decimal("0")
    tax_amount: Decimal = Decimal("0")
    net_pay: Decimal = Decimal("0")
    # 以下为增强字段（向后兼容，不影响既有取值）
    insurance_base: Decimal = Decimal("0") # 实际用于五险一金的缴费基数
    er_pension: Decimal = Decimal("0")
    er_medical: Decimal = Decimal("0")
    er_unemployment: Decimal = Decimal("0")
    er_injury: Decimal = Decimal("0")
    er_maternity: Decimal = Decimal("0")
    er_housing_fund: Decimal = Decimal("0")
    total_employer: Decimal = Decimal("0") # 单位合计承担


@dataclass
class BonusResult:
    bonus_amount: Decimal
    tax_amount: Decimal
    net_bonus: Decimal
    effective_rate: Decimal
    in_trap_range: bool = False
    trap_note: str = ""


# ---------------------------------------------------------------------------
# 计算引擎
# ---------------------------------------------------------------------------

def calculate_monthly_tax(
    month: int,
    monthly_gross: Decimal,
    monthly_insurance: Decimal,
    special_deduction: Decimal = Decimal("0"),
    cumulative_tax_paid: Decimal = Decimal("0"),
    cumulative_income: Optional[Decimal] = None,
    cumulative_insurance: Optional[Decimal] = None,
    cumulative_special: Optional[Decimal] = None,
) -> Decimal:
    """累计预扣法计算本月应缴个税。

    month: 1-12（决定累计减除费用月数）
    monthly_gross: 本月收入（应发）
    monthly_insurance: 本月社保公积金个人部分
    special_deduction: 本月专项附加扣除
    cumulative_tax_paid: 截至上月（不含本月）的累计已缴个税
    cumulative_income / cumulative_insurance / cumulative_special:
        截至上月（不含本月）的累计收入 / 累计专项扣除 / 累计专项附加扣除。
        传入则按真实累计值计算，支持「变额月薪」（每月收入不同，按「每月恒定」近似会算错）。
        不传则退化为「每月恒定 = 本月」的近似（向后兼容旧调用与文档示例）。
    """
    # 本函数是公开入口（可绕过 payroll_monthly_from_payload 直接调用），
    # 故 month 的 1-12 边界必须在此自守：累计减除费用按 `MONTHLY_DEDUCTION * month`
    # 线性放大，month=13/99 会算出巨额累计应纳税所得额并产出负数实发工资。
    if not isinstance(month, int) or isinstance(month, bool) or month < 1 or month > 12:
        raise InputValidationError(
            f"`month` 必须是 1-12 的整数，实际收到 {month!r}",
            code="E020", field="month",
        )

    monthly_gross = _d(monthly_gross)
    monthly_insurance = _d(monthly_insurance)
    special_deduction = _d(special_deduction)
    cumulative_tax_paid = _d(cumulative_tax_paid)

    # 累计值 = 上月真实累计（如提供）+ 本月；未提供则退化为「每月恒定」近似
    if cumulative_income is None:
        cumulative_income = monthly_gross * month
    else:
        cumulative_income = _d(cumulative_income) + monthly_gross
    if cumulative_insurance is None:
        cumulative_insurance = monthly_insurance * month
    else:
        cumulative_insurance = _d(cumulative_insurance) + monthly_insurance
    if cumulative_special is None:
        cumulative_special = special_deduction * month
    else:
        cumulative_special = _d(cumulative_special) + special_deduction

    cumulative_taxable = (
        cumulative_income - MONTHLY_DEDUCTION * month
        - cumulative_insurance - cumulative_special
    )
    if cumulative_taxable <= 0:
        return Decimal("0")

    bracket = _find_bracket(cumulative_taxable, ANNUAL_TAX_BRACKETS)
    cumulative_tax = cumulative_taxable * bracket["rate"] - bracket["deduction"]
    current_month_tax = cumulative_tax - cumulative_tax_paid
    # 负税额只可能来自「累计已缴 > 累计应缴」这一输入自相矛盾（如 cumulativeTaxPaid
    # 被填成 999999999）。静默 max(·, 0) 会把它伪装成 tax_amount="0.00" 的合法结果，
    # 对薪酬系统是真金白银的口径事故，故 fail-fast 抛 E060。
    if current_month_tax < 0:
        raise InputValidationError(
            f"本月个税为负（{_money(current_month_tax)} 元），累计数据自相矛盾："
            f"截至上月累计已缴个税 {_money(cumulative_tax_paid)} 元 > 按累计应纳税所得额 "
            f"{_money(cumulative_taxable)} 元算出的累计应缴个税 {_money(cumulative_tax)} 元。"
            f"请核对 `cumulativeTaxPaid` 与 cumulativeIncome/cumulativeInsurance/cumulativeSpecial。",
            code="E060", field="cumulativeTaxPaid",
        )
    return current_month_tax


def calculate_insurance(salary: Decimal, city: str, base: Optional[Decimal] = None) -> Dict[str, Decimal]:
    """计算五险一金（个人 + 单位）缴纳部分。

    base: 社保/公积金缴费基数；不传则用当月工资(salary)作为基数（向后兼容）。
          正式核算应传合规基数（见 calculate_payroll 的 insurance_base，
          通常为上一年度月平均工资），避免用含奖金/加班的当月 gross 高估基数。
    """
    salary = _d(salary)
    cfg = CITY_CONFIGS.get(city)
    if cfg is None:
        raise ValueError(f"未配置城市: {city}，可用: {sorted(CITY_CONFIGS.keys())}")

    ins_base = _d(base) if base is not None else salary
    ins_base = _clamp(ins_base, cfg.base_floor, cfg.base_ceiling)
    fund_base = _clamp(ins_base, cfg.fund_floor, cfg.base_ceiling)

    ee = {
        "pension": _money(ins_base * cfg.pension_ee),
        "medical": _money(ins_base * cfg.medical_ee),
        "unemployment": _money(ins_base * cfg.unemp_ee),
        "housing_fund": _money(fund_base * cfg.fund_ee),
    }
    er = {
        "pension": _money(ins_base * cfg.pension_er),
        "medical": _money(ins_base * cfg.medical_er),
        "unemployment": _money(ins_base * cfg.unemp_er),
        "injury": _money(ins_base * cfg.injury_er),
        "maternity": _money(ins_base * cfg.maternity_er),
        "housing_fund": _money(fund_base * cfg.fund_er),
    }
    ee_total = ee["pension"] + ee["medical"] + ee["unemployment"] + ee["housing_fund"]
    er_total = er["pension"] + er["medical"] + er["unemployment"] + er["injury"] + er["maternity"] + er["housing_fund"]

    # 返回个人明细 + 兼容旧键(total) + 单位明细，供调用方统一映射
    out: Dict[str, Decimal] = dict(ee)
    out["total"] = ee_total
    out["ee_total"] = ee_total
    out["er"] = er
    out["er_total"] = er_total
    out["ins_base"] = ins_base
    out["fund_base"] = fund_base
    return out


def calculate_payroll(
    employee_id: str,
    employee_name: str,
    year: int,
    month: int,
    base_salary: Decimal,
    city: str,
    position_allowance: Decimal = Decimal("0"),
    performance_bonus: Decimal = Decimal("0"),
    overtime_pay: Decimal = Decimal("0"),
    other_income: Decimal = Decimal("0"),
    other_deductions: Decimal = Decimal("0"),
    special_deduction: Decimal = Decimal("0"),
    cumulative_tax_paid: Decimal = Decimal("0"),
    cumulative_income: Optional[Decimal] = None,
    cumulative_insurance: Optional[Decimal] = None,
    cumulative_special: Optional[Decimal] = None,
    insurance_base: Optional[Decimal] = None,
) -> MonthPayroll:
    """单月薪资完整计算。入参校验请在调用方（_cli / batch / engine_service）完成。

    insurance_base: 社保/公积金缴费基数（可选）。不传则用当月 gross 作为基数；
        正式核算建议传上一年度月平均工资等合规基数，避免用含奖金/加班的当月
        gross 高估缴费基数。
    """
    base_salary = _d(base_salary)
    position_allowance = _d(position_allowance)
    performance_bonus = _d(performance_bonus)
    overtime_pay = _d(overtime_pay)
    other_income = _d(other_income)
    other_deductions = _d(other_deductions)

    gross = base_salary + position_allowance + performance_bonus + overtime_pay + other_income
    ins = calculate_insurance(gross, city, base=insurance_base)
    total_ins = ins["ee_total"]

    # 名义应税所得（当月口径）：仅用于向调用方展示「当月应发 − 个人五险一金 − 其他扣除」。
    # 注意：实发个税并不由本值算出——个税走累计预扣法（见 calculate_monthly_tax，
    # 税基含专项附加扣除与累计已缴），故本字段是展示口径，不等于实际计税基数。
    taxable = gross - total_ins - other_deductions
    tax = calculate_monthly_tax(
        month=month,
        monthly_gross=gross,
        monthly_insurance=total_ins,
        special_deduction=special_deduction,
        cumulative_tax_paid=cumulative_tax_paid,
        cumulative_income=cumulative_income,
        cumulative_insurance=cumulative_insurance,
        cumulative_special=cumulative_special,
    )
    net = gross - total_ins - other_deductions - tax

    # 负数实发工资不得静默输出：otherDeductions 无语义上限，填入超大值即得巨额负数
    # 实发（如 999999999999 → net ≈ −999999981055.25）。此处 fail-fast 抛 E040。
    if net < 0:
        raise InputValidationError(
            f"实发工资为负（{_money(net)} 元），扣款超过应发：应发 {_money(gross)} − "
            f"个人五险一金 {_money(total_ins)} − 其他扣除 {_money(other_deductions)} − "
            f"个税 {_money(tax)}。请核对 `otherDeductions` 是否超出应发工资。",
            code="E040", field="otherDeductions",
        )

    return MonthPayroll(
        year=year, month=month,
        employee_id=employee_id, employee_name=employee_name,
        gross_pay=_money(gross),
        pension=ins["pension"], medical=ins["medical"],
        unemployment=ins["unemployment"], housing_fund=ins["housing_fund"],
        total_insurance=_money(total_ins), other_deductions=_money(other_deductions),
        taxable_income=_money(taxable), tax_amount=_money(tax),
        net_pay=_money(net),
        insurance_base=ins["ins_base"],
        er_pension=ins["er"]["pension"], er_medical=ins["er"]["medical"],
        er_unemployment=ins["er"]["unemployment"], er_injury=ins["er"]["injury"],
        er_maternity=ins["er"]["maternity"], er_housing_fund=ins["er"]["housing_fund"],
        total_employer=_money(ins["er_total"]),
    )


def batch_calculate_payroll(
    employees: List[Dict],
    year: int,
    month: int,
) -> List[MonthPayroll]:
    """批量计算薪资：列表内每人独立计算，逐条 fail-fast 校验。

    入参映射统一走 `_payroll_kwargs_from_payload`（与 CLI `--payroll` /
    engine_service `payroll.monthly` 同一份契约），累计收入/累计社保/
    累计专项附加（cumulativeIncome / cumulativeInsurance / cumulativeSpecial）
    三个字段在批量路径同样生效——统一映射可避免遗漏字段导致同一员工在批量
    与单条路径下个税口径不一致。

    `year` / `month` 为批量级默认值：记录内显式给出同名字段时以记录为准
    （`_validate_payroll_record` 已校验其合法性），未给出才回退到本参数。
    """
    results = []
    for emp in employees:
        if not isinstance(emp, dict):
            raise InputValidationError(
                f"薪资记录必须是 JSON 对象，实际收到 {type(emp).__name__}",
                code="E020", field=None,
            )
        # 记录级 year/month 优先，缺省才用批量级参数（与单条路径口径一致）
        payload = dict(emp)
        payload.setdefault("year", year)
        payload.setdefault("month", month)
        _validate_payroll_record(payload)  # fail-fast：缺 baseSalary 等直接报错
        results.append(calculate_payroll(**_payroll_kwargs_from_payload(payload)))
    return results


def calculate_year_end_bonus(bonus_amount: Decimal) -> BonusResult:
    """年终奖单独计税 + 跳档陷阱检测。"""
    bonus_amount = _d(bonus_amount)
    if bonus_amount <= 0:
        return BonusResult(
            bonus_amount=Decimal("0"), tax_amount=Decimal("0"),
            net_bonus=Decimal("0"), effective_rate=Decimal("0"),
        )

    monthly = bonus_amount / Decimal("12")
    bracket = _find_bracket(monthly, BONUS_MONTHLY_BRACKETS)
    tax = _money(bonus_amount * bracket["rate"] - bracket["deduction"])
    net = _money(bonus_amount - tax)
    eff_rate = (tax / bonus_amount * 100) if bonus_amount > 0 else Decimal("0")

    trap_note = ""
    in_trap = False
    for lo, hi in BONUS_TRAP_RANGES:
        if lo < bonus_amount <= hi:
            in_trap = True
            trap_note = f"年终奖 {bonus_amount} 落在跳档陷阱区间 ({lo}~{hi})，税后收入低于 {lo} 档，建议调整到 {lo} 或跨过 {hi}。"
            break

    return BonusResult(
        bonus_amount=bonus_amount, tax_amount=tax, net_bonus=net,
        effective_rate=eff_rate.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        in_trap_range=in_trap, trap_note=trap_note,
    )


# ---------------------------------------------------------------------------
# 对外数据契约映射（单一基准）
#
# CLI（`--payroll` / `--bonus`）与 engine_service（端点 `payroll.monthly` /
# `payroll.bonus`）必须产出**完全一致**的入参映射与出参 JSON——两条通路的字段
# 回退口径必须相同（如 `insuranceBase` 缺省时不得一条回退、一条置 None），
# 否则同一份载荷会得到不同结果。统一收敛到本区函数，调用方不得再另行拼装字段。
# ---------------------------------------------------------------------------

def _payroll_kwargs_from_payload(payload: Dict, insurance_base_fallback=None) -> Dict:
    """把 camelCase 载荷规整为 `calculate_payroll()` 的关键字入参。

    `insurance_base_fallback` 仅供 CLI 使用（载荷未给 `insuranceBase` 时回退到
    命令行 `--insurance-base`）；engine_service 不传，行为等同置 None。
    """
    return dict(
        employee_id=payload.get("employeeId", ""),
        employee_name=payload.get("employeeName", ""),
        year=payload.get("year", 2026),
        month=payload.get("month", 1),
        base_salary=payload.get("baseSalary", 0),
        city=payload.get("city", "北京"),
        position_allowance=payload.get("positionAllowance", 0),
        performance_bonus=payload.get("performanceBonus", 0),
        overtime_pay=payload.get("overtimePay", 0),
        other_income=payload.get("otherIncome", 0),
        other_deductions=payload.get("otherDeductions", 0),
        special_deduction=payload.get("specialDeduction", 0),
        cumulative_tax_paid=payload.get("cumulativeTaxPaid", 0),
        cumulative_income=payload.get("cumulativeIncome", None),
        cumulative_insurance=payload.get("cumulativeInsurance", None),
        cumulative_special=payload.get("cumulativeSpecial", None),
        insurance_base=(payload.get("insuranceBase")
                        if payload.get("insuranceBase") is not None
                        else insurance_base_fallback),
    )


def _payroll_result_to_dict(p: MonthPayroll) -> Dict:
    """把 `MonthPayroll` 序列化为对外 JSON 契约（字段与顺序的单一出处）。"""
    return {
        "year": p.year, "month": p.month,
        "employee_id": p.employee_id, "employee_name": p.employee_name,
        "gross_pay": str(p.gross_pay),
        "insurance_base": str(p.insurance_base),
        "total_insurance": str(p.total_insurance),
        "tax_amount": str(p.tax_amount),
        "net_pay": str(p.net_pay),
        "employer": {
            "pension": str(p.er_pension),
            "medical": str(p.er_medical),
            "unemployment": str(p.er_unemployment),
            "injury": str(p.er_injury),
            "maternity": str(p.er_maternity),
            "housing_fund": str(p.er_housing_fund),
            "total": str(p.total_employer),
        },
    }


def payroll_monthly_from_payload(payload: Dict, insurance_base_fallback=None) -> Dict:
    """单月薪资的**唯一契约入口**：校验 → 计算 → 对外 JSON。

    CLI 的 `--payroll` 与 engine_service 的 `payroll.monthly` 都必须经此函数，
    以保证两条通路的入参语义与出参结构永不漂移。
    校验失败抛 `InputValidationError`（其基类为 ValueError），调用方自行决定呈现方式。
    """
    _validate_payroll_record(payload)
    return _payroll_result_to_dict(
        calculate_payroll(**_payroll_kwargs_from_payload(payload, insurance_base_fallback))
    )


def bonus_result_to_dict(r: BonusResult) -> Dict:
    """把 `BonusResult` 序列化为对外 JSON 契约（字段与顺序的单一出处）。"""
    return {
        "bonus_amount": str(r.bonus_amount),
        "tax_amount": str(r.tax_amount),
        "net_bonus": str(r.net_bonus),
        "effective_rate": str(r.effective_rate),
        "in_trap_range": r.in_trap_range,
        "trap_note": r.trap_note,
    }


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------

def _coerce_amount(raw: str) -> "int | float":
    """把 CLI 收到的数字字符串规整为 JSON 数值类型（int / float）。

    用途：`--bonus` 经 argparse 得到的是字符串，而 `engine_service` 的
    `payroll.bonus` handler 要求 `bonusAmount` 为 `int | float`，否则直接
    抛 `_BadRequest(code="E020")`。这里先按 `Decimal` 判定数值有效性，再落回
    数值类型，口径与无 `--envelope` 路径 `calculate_year_end_bonus`
    （内部 `Decimal(str(x))`）完全一致。

    规则：
    - 整值金额（`Decimal` 为整值）→ `int`，避免出现 `36000.0` 这类多余小数；
    - 其余 → `float`；
    - 非有限值（nan / inf）或非法字面量 → 抛 `ValueError`，由调用方转成明确
      报错 + 非零退出码。

    Args:
        raw: 原始字符串，如 "36000"、"36000.50"。

    Returns:
        规整后的 int 或 float。

    Raises:
        ValueError: 当 raw 不是合法的有限数字时。
    """
    try:
        dec = Decimal(str(raw).strip())
    except (InvalidOperation, ValueError):
        raise ValueError(f"金额必须是数字，实际收到 {raw!r}")
    if not dec.is_finite():
        raise ValueError(f"金额必须是有限数字，实际收到 {raw!r}")
    if dec == dec.to_integral_value():
        return int(dec)
    return float(dec)


def _cli() -> int:
    import argparse
    import json

    parser = argparse.ArgumentParser(description="薪酬计算引擎")
    parser.add_argument("--payroll", metavar="JSON", help="单月薪资计算：{\"employeeId\":...,\"baseSalary\":...,\"city\":...,\"year\":...,\"month\":...,\"cumulativeTaxPaid\":...,\"cumulativeIncome\":(可选),\"cumulativeInsurance\":(可选),\"cumulativeSpecial\":(可选),\"insuranceBase\":(可选)}")
    parser.add_argument("--insurance-base", metavar="AMOUNT", help="社保/公积金缴费基数（可选，覆盖默认的当月工资基数）")
    parser.add_argument("--bonus", metavar="AMOUNT", help="年终奖单独计税（Decimal 字符串）")
    parser.add_argument(
        "--envelope", action="store_true",
        help="经 engine_service.dispatch_envelope_json 输出统一 schema（status/version/payload/errors/warnings）",
    )
    args = parser.parse_args()

    if args.envelope:
        # 惰性导入：仅在 --envelope 时经 engine_service 中转统一 schema，避免循环导入
        from engine_service import emit_envelope
        if args.payroll:
            return emit_envelope("payroll.monthly", args.payroll)
        if args.bonus:
            try:
                bonus_amount = _coerce_amount(args.bonus)
            except ValueError as e:
                parser.error(str(e))
            return emit_envelope("payroll.bonus", json.dumps({"bonusAmount": bonus_amount}))
        parser.error("--envelope 需配合 --payroll 或 --bonus 使用")

    if args.payroll:
        try:
            data = json.loads(args.payroll)
        except json.JSONDecodeError as e:
            parser.error(f"--payroll 不是合法 JSON：{e}")
        if not isinstance(data, dict):
            parser.error("--payroll 必须是 JSON 对象（顶层 { }）")
        try:
            result = payroll_monthly_from_payload(
                data,
                # 载荷未给 insuranceBase 时回退到 --insurance-base（engine_service 无此回退）
                insurance_base_fallback=(_d(args.insurance_base) if args.insurance_base else None),
            )
        except (ValueError, ArithmeticError) as e:
            parser.error(f"薪资计算失败：{e}")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if args.bonus:
        try:
            r = calculate_year_end_bonus(args.bonus)
        except (ValueError, ArithmeticError):
            parser.error(f"--bonus 必须是数字金额，实际收到 {args.bonus!r}")
        print(json.dumps(bonus_result_to_dict(r), ensure_ascii=False, indent=2))
        return 0

    parser.print_help()
    return 2


# 导入期回归守卫：城市费率若被静默回退为全相同占位数据，立即失败而不是算错。
verify_city_rates()


if __name__ == "__main__":
    raise SystemExit(_cli())
