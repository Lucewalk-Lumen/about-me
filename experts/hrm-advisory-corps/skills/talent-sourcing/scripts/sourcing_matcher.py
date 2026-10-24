#!/usr/bin/env python3
"""talent-sourcing · 寻访匹配引擎

作者：Xing Bu

职责：职位需求（requisition, J 系列）↔ 人才简历库（resumes, R 系列）的
匹配打分。三级关键词（标准名/细分赛道专属名/行业通用别名）均参与匹配，
别名类命中权重低于标准名；sourcing_profile.target_companies 非空时
标注 tier_hit 并优先输出。

匹配分口径（与 SKILL.md 一致，可调）：
    技能命中率 ×50% + 年限契合 ×20% + 城市匹配 ×15% + 目标公司/行业契合 ×15%

运行方式（包内）：
    python3 skills/talent-sourcing/scripts/sourcing_matcher.py --help
    python3 sourcing_matcher.py --req J000001 --pool ../knowledge/resumes --top 10

错误码沿用 errors.py 的 StructuredError 体系（本脚本内置兼容定义，零三方依赖）：
    E001 缺字段 / E020 类型错误 / E040 值越界 / E080 未找到，fail-fast 校验入参。

退出码：0 成功；1 参数/校验错误（E001/E020/E040）；2 文件不存在（E080）。
--help 退出 0（argparse 默认行为）。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# 匹配分权重（默认建议值，可调）
WEIGHT_SKILL = 0.50
WEIGHT_YEARS = 0.20
WEIGHT_CITY = 0.15
WEIGHT_COMPANY_FIT = 0.15

# 三级关键词命中权重：标准名 1.0 / 细分赛道专属名 0.8 / 行业通用别名 0.5
# （权威口径以此处为准，INDEX.md §1.9 同步对齐）
KEYWORD_TIER_WEIGHT = {"standard_terms": 1.0, "niche_terms": 0.8, "aliases": 0.5}

# 年限契合：岗位隐含年限区间提取不到「N年以上」时的中性分
YEARS_NEUTRAL_SCORE = 0.7
# 城市匹配：非同城市且无法关联画像库 hot_cities 时的基准分
CITY_OTHER_SCORE = 0.3


class StructuredError(ValueError):
    """结构化错误（与 hrm-solution/scripts/errors.py 同名兼容定义）。

    携带确定性错误码 code / 出错字段 field / 严重度 severity。
    本脚本零三方依赖、不跨技能 import，故内置同构定义。
    """

    def __init__(self, message: str, code: str | None = None,
                 field: str | None = None, severity: str = "fatal") -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.field = field
        self.severity = severity

    def __str__(self) -> str:
        return self.message


def _err(code: str, message: str, field: str | None = None) -> StructuredError:
    return StructuredError(f"[{code}] {message}", code=code, field=field)


def _resolve(base_script_dir: Path, p: str) -> Path:
    """相对路径相对本脚本所在目录解析。"""
    path = Path(p)
    if not path.is_absolute():
        path = (base_script_dir / path).resolve()
    return path


def _load_json_file(path: Path, what: str) -> dict:
    if not path.exists():
        raise _err("E080", f"{what}不存在：{path}", field=str(path))
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise _err("E020", f"{what}不是合法 JSON：{path}（{exc}）", field=str(path))
    if not isinstance(data, dict):
        raise _err("E020", f"{what}须为 JSON 对象：{path}", field=str(path))
    return data


def load_requisition(req: str, req_dir: str) -> dict:
    """加载职位需求：--req 为 J 系列 ID 时从 req_dir 读取，为 JSON 字符串/文件路径时解析。

    fail-fast 校验：schema=job-requisition、must_have/sourcing_profile 齐备、
    capability_weights 权重合计 100；缺项抛 E001/E020。
    """
    script_dir = Path(__file__).resolve().parent
    req_arg = req.strip()

    if re.fullmatch(r"J\d{6}", req_arg):
        data = _load_json_file(_resolve(script_dir, req_dir) / f"{req_arg}.json",
                               f"职位需求 {req_arg}")
    elif req_arg.startswith("{"):
        try:
            data = json.loads(req_arg)
        except json.JSONDecodeError as exc:
            raise _err("E020", f"--req 不是合法 JSON 字符串（{exc}）", field="--req")
        if not isinstance(data, dict):
            raise _err("E020", "--req JSON 须为对象", field="--req")
    else:
        # 视为 JSON 文件路径
        data = _load_json_file(_resolve(script_dir, req_arg), "职位需求 JSON 文件")

    if data.get("schema") != "job-requisition":
        raise _err("E001", f"schema 须为 \"job-requisition\"，实际为 {data.get('schema')!r}",
                   field="schema")
    if not data.get("req_id"):
        raise _err("E001", "req_id 缺失", field="req_id")
    if not data.get("must_have"):
        raise _err("E001", "must_have 缺失或为空（用于年限区间提取与匹配依据）",
                   field="must_have")
    sp = data.get("sourcing_profile")
    if not isinstance(sp, dict):
        raise _err("E001", "sourcing_profile 缺失或类型错误（须为对象）",
                   field="sourcing_profile")
    if not isinstance(sp.get("skill_keywords"), dict):
        raise _err("E001", "sourcing_profile.skill_keywords 缺失或类型错误",
                   field="sourcing_profile.skill_keywords")
    weights = sp.get("capability_weights")
    if weights is not None:
        if not isinstance(weights, list) or not all(
                isinstance(w, dict) and isinstance(w.get("weight"), (int, float))
                for w in weights):
            raise _err("E020", "capability_weights 须为 [{capability, weight}] 数组",
                       field="sourcing_profile.capability_weights")
        total = sum(w["weight"] for w in weights)
        if abs(total - 100) > 1e-6:
            raise _err("E001",
                       f"capability_weights 权重合计须为 100，实际为 {total}",
                       field="sourcing_profile.capability_weights")
    return data


def expand_keywords(skill_keywords: dict) -> list[dict]:
    """展开三级关键词为统一命中表：[{term, tier, weight}]。

    中英对照词对两个形态都进表；别名类按 KEYWORD_TIER_WEIGHT 降权。
    """
    table: list[dict] = []
    for tier, weight in KEYWORD_TIER_WEIGHT.items():
        entries = skill_keywords.get(tier)
        if entries is None:
            continue  # 该层未配置（null/缺省），视为空
        if not isinstance(entries, list):
            raise _err("E020", f"skill_keywords.{tier} 须为数组",
                       field=f"skill_keywords.{tier}")
        for entry in entries:
            terms: list[str] = []
            if isinstance(entry, dict):
                terms = [t for t in (entry.get("zh"), entry.get("en")) if t]
            elif isinstance(entry, str):
                terms = [entry]
            else:
                raise _err("E020",
                           f"skill_keywords.{tier} 条目须为 {{zh, en}} 或字符串：{entry!r}",
                           field=f"skill_keywords.{tier}")
            for term in terms:
                table.append({"term": str(term).lower(), "tier": tier, "weight": weight})
    return table


def _as_list(value, what: str) -> list:
    """把「可能是字符串」的字段规整为字符串列表。

    档案 JSON 里 `skills` / `certificates` / `tags` / `locations` 等既可能写成
    数组，也可能被写成单个字符串。若直接迭代字符串，Python 会逐字符展开
    （"机器学习" → ["机","器","学","习"]），导致完整命中的技能反而得 0 分，
    且无任何报错。故此处统一规整：字符串按常见分隔符切分，切不出则作单元素。
    """
    if value is None:
        return []
    if isinstance(value, str):
        parts = [p.strip() for p in re.split(r"[,，;；、/|]+", value)]
        parts = [p for p in parts if p]
        return parts if parts else [value]
    if isinstance(value, (list, tuple, set)):
        return [v for v in value if v is not None and str(v).strip()]
    return [value]


def _candidate_text(candidate: dict) -> str:
    """候选人可匹配文本：profile.skills + current_title + project_highlights。"""
    profile = candidate.get("profile", {})
    parts = [str(s) for s in _as_list(profile.get("skills"), "skills")]
    parts.append(str(profile.get("current_title", "")))
    parts.append(str(profile.get("project_highlights", "")))
    return " ".join(parts).lower()


def _skill_score(candidate: dict, keyword_table: list[dict]) -> tuple[float, list[str]]:
    """技能命中率 = 命中关键词的加权分 / 全部关键词加权满分。

    同一 (tier, term) 只计一次（去重）；zh/en 形态各自独立计分——
    候选人命中任一形态即得该形态权重分。
    """
    text = _candidate_text(candidate)
    if not keyword_table:
        return YEARS_NEUTRAL_SCORE, ["岗位未配置 skill_keywords，技能分按中性 0.7 计"]

    full = 0.0
    seen: set[str] = set()
    hit = 0.0
    hits: list[str] = []
    for item in keyword_table:
        key = f'{item["tier"]}:{item["term"]}'
        if key in seen:
            continue
        seen.add(key)
        full += item["weight"]
        if item["term"] in text:
            hit += item["weight"]
            hits.append(f'{item["term"]}({item["tier"]}×{item["weight"]})')
    if full <= 0:
        return YEARS_NEUTRAL_SCORE, ["skill_keywords 为空，技能分按中性 0.7 计"]
    return hit / full, hits


def _years_range_from_must_have(must_have: list) -> tuple[float, float] | None:
    """从 must_have 文本提取「N年以上」→ 区间 [N, N+3]；提取不到返回 None。"""
    for item in must_have or []:
        m = re.search(r"(\d+)\s*年以上", str(item))
        if m:
            n = float(m.group(1))
            return (n, n + 3)
    return None


def _years_score(candidate: dict, requisition: dict) -> tuple[float, str]:
    """年限契合：完全落区间=1.0，差一点=0.5，差距大=0.2；无区间给中性 0.7。"""
    years = candidate.get("profile", {}).get("years_of_exp")
    rng = _years_range_from_must_have(requisition.get("must_have", []))
    if rng is None:
        return YEARS_NEUTRAL_SCORE, "must_have 未含「N年以上」，年限分按中性 0.7 计"
    if not isinstance(years, (int, float)):
        return YEARS_NEUTRAL_SCORE, "候选人 years_of_exp 缺失，年限分按中性 0.7 计"
    lo, hi = rng
    if lo <= years <= hi:
        return 1.0, f"{years} 年落于区间 [{lo:g}, {hi:g}]"
    gap = lo - years if years < lo else years - hi
    if gap <= 2:
        return 0.5, f"{years} 年偏离区间 [{lo:g}, {hi:g}] {gap:g} 年（差一点）"
    return 0.2, f"{years} 年偏离区间 [{lo:g}, {hi:g}] {gap:g} 年（差距大）"


def _load_hot_cities(script_dir: Path) -> set[str]:
    """关联画像库 hot_cities（knowledge/talent-personas/*.json），供城市匹配用。"""
    personas_dir = script_dir.parent / "knowledge" / "talent-personas"
    hot: set[str] = set()
    if not personas_dir.is_dir():
        return hot
    for path in sorted(personas_dir.glob("P*.json")):
        try:
            persona = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        supply = persona.get("supply", {})
        for city in _as_list(supply.get("hot_cities"), "supply.hot_cities"):
            hot.add(str(city))
    return hot


def _city_score(candidate: dict, requisition: dict, hot_cities: set[str]) -> tuple[float, str]:
    """城市匹配：同城市=1.0，画像库 hot_cities 内=0.6，其他=0.3。"""
    cand_city = candidate.get("profile", {}).get("city")
    req_city = requisition.get("city")
    if not req_city:
        return YEARS_NEUTRAL_SCORE, "岗位未标注城市，城市分按中性 0.7 计"
    if cand_city == req_city:
        return 1.0, f"同城市（{cand_city}）"
    if cand_city and cand_city in hot_cities:
        return 0.6, f"{cand_city} 属画像库 hot_cities（岗位城市 {req_city}）"
    return CITY_OTHER_SCORE, f"{cand_city or '城市未知'} 与岗位城市 {req_city} 不同"


def _norm_company(name: str) -> str:
    return re.sub(r"\s+", "", str(name)).lower()


def _company_score(candidate: dict, requisition: dict) -> tuple[float, bool, str]:
    """目标公司/行业契合 + tier_hit 判定。

    current_company 命中 target_companies=1.0 且 tier_hit=true；industry 与
    岗位行业/目标公司业务有交集=0.5；无关=0.2。target_companies 为空时
    不做 tiers 优先（仅按行业契合计分）。
    """
    profile = candidate.get("profile", {})
    cand_company = _norm_company(profile.get("current_company", ""))
    cand_industry = str(profile.get("industry", ""))
    sp = requisition.get("sourcing_profile", {})
    targets = [t for t in _as_list(sp.get("target_companies"),
                                   "sourcing_profile.target_companies")
               if str(t).strip()]

    for t in targets:
        tn = _norm_company(t)
        # cand_company 必须非空：Python 中 "" in "字节跳动" 为 True，
        # 若不挡住空公司名，current_company 为 ""/空白的候选会拿到 company=1.0
        # 且 tier_hit=true（满分 + 排序置顶），反而压过真正无匹配的候选人。
        if tn and cand_company and (tn in cand_company or cand_company in tn):
            return 1.0, True, f"现职公司命中 target_companies（{t}）"

    # 行业契合：候选人 industry 与岗位 title/department/talent_tags 的行业词有交集
    req_text = " ".join([str(requisition.get("title", "")),
                         str(requisition.get("department", "")),
                         *[str(t) for t in _as_list(sp.get("talent_tags"),
                                                    "sourcing_profile.talent_tags")]])
    industry_tokens = [tok for tok in re.split(r"[/、,\s]+", cand_industry) if tok]
    for tok in industry_tokens:
        if tok and tok in req_text:
            return 0.5, False, f"行业相邻（候选人行业 {cand_industry} 与岗位画像有交集）"
    return 0.2, False, "公司与行业均无明确交集"


def score_candidate(candidate: dict, requisition: dict,
                    keyword_table: list[dict],
                    hot_cities: set[str]) -> dict:
    """单候选人打分：四项子分按 WEIGHT_* 加权。

    返回 {candidate_id, match_score（2位）, breakdown, tier_hit, labels, evidence}；
    evidence 逐条记录命中依据，不允许只给分不给依据。
    """
    skill_s, skill_ev = _skill_score(candidate, keyword_table)
    years_s, years_ev = _years_score(candidate, requisition)
    city_s, city_ev = _city_score(candidate, requisition, hot_cities)
    company_s, tier_hit, company_ev = _company_score(candidate, requisition)

    total = (skill_s * WEIGHT_SKILL + years_s * WEIGHT_YEARS
             + city_s * WEIGHT_CITY + company_s * WEIGHT_COMPANY_FIT)

    return {
        "candidate_id": candidate.get("candidate_id"),
        "match_score": round(total, 2),
        "breakdown": {
            "skill": round(skill_s, 2),
            "years": round(years_s, 2),
            "city": round(city_s, 2),
            "company": round(company_s, 2),
        },
        "tier_hit": tier_hit,
        "labels": candidate.get("labels", []),
        "evidence": {
            "skill": skill_ev,
            "years": years_ev,
            "city": city_ev,
            "company": company_ev,
        },
    }


def match(req: str, pool_dir: str, req_dir: str, top: int) -> dict:
    """主匹配流程：加载需求 → 展开关键词 → 遍历人才库 → 打分排序 → 取 top N。

    target_companies 非空时 tier_hit=true 的候选人优先输出（排序按
    match_score 降序，tier_hit 并列时 tier 命中者在前）。
    """
    script_dir = Path(__file__).resolve().parent
    requisition = load_requisition(req, req_dir)

    pool = _resolve(script_dir, pool_dir)
    if not pool.is_dir():
        raise _err("E080", f"人才库目录不存在：{pool}", field=str(pool))
    if top < 1:
        raise _err("E040", f"--top 须为正整数，实际为 {top}", field="--top")

    keyword_table = expand_keywords(requisition["sourcing_profile"]["skill_keywords"])
    hot_cities = _load_hot_cities(script_dir)

    results = []
    for path in sorted(pool.glob("R*.json")):
        candidate = _load_json_file(path, f"候选人档案 {path.name}")
        if candidate.get("status", "active") != "active":
            continue
        results.append(score_candidate(candidate, requisition, keyword_table, hot_cities))

    # tier_hit 优先 + match_score 降序
    results.sort(key=lambda r: (not r["tier_hit"], -r["match_score"],
                                str(r["candidate_id"])))
    results = results[:top]

    return {
        "req_id": requisition.get("req_id"),
        "total_matched": len(results),
        "results": results,
    }


def _cli() -> int:
    parser = argparse.ArgumentParser(
        description="寻访匹配引擎：JD ↔ 人才库三级关键词匹配 + target_companies tier 优先。",
    )
    parser.add_argument("--req", required=True,
                        help="职位需求：J 系列 ID（如 J000001）、requisition JSON 字符串或 JSON 文件路径")
    parser.add_argument("--req-dir", default="../knowledge/requisitions",
                        help="职位需求库目录（默认 ../knowledge/requisitions）")
    parser.add_argument("--pool", default="../knowledge/resumes",
                        help="人才简历库目录（默认 ../knowledge/resumes）")
    parser.add_argument("--top", type=int, default=10, help="返回前 N 个匹配结果，默认 10")
    parser.add_argument("--envelope", action="store_true",
                        help="（预留）经 engine_service 输出统一 schema，当前版本直接输出 payload")

    args = parser.parse_args()

    try:
        out = match(args.req, args.pool, args.req_dir, args.top)
    except StructuredError as exc:
        print(str(exc), file=sys.stderr)
        return 2 if exc.code == "E080" else 1

    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
