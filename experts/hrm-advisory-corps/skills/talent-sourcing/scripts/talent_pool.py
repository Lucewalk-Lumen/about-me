#!/usr/bin/env python3
"""talent-sourcing · 人才库 CRUD + 索引维护

作者：Xing Bu

职责：人才简历库（knowledge/resumes/）的增删查改、库级 _index.json 维护与
审计日志。档案本身只存脱敏视图（明文联系方式存 PII 保管区，本库不落明文）；
无同意记录（source.consent.obtained=true）的档案拒绝入库（个保法合规硬校验）。

运行方式（包内）：
    python3 skills/talent-sourcing/scripts/talent_pool.py --help
    # 或在本目录下：
    python3 talent_pool.py add --file R000002.json

错误码沿用 errors.py 的 StructuredError 体系（本脚本内置兼容定义，零三方依赖）：
    E001 缺字段 / E020 类型错误 / E040 值越界 / E060 合规拒绝 / E080 未找到。

退出码：0 成功；1 参数/校验错误（E001/E020/E040/E060）；2 文件不存在（E080）。
--help 退出 0（argparse 默认行为）。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

SCHEMA_VERSION = "1.0.0"
SCHEMA_NAME = "talent-resume"
ID_PREFIX = "R"

# 脱敏视图白名单：search 简要信息只允许这些 profile 字段输出（防御性：
# 即使档案被误写入明文联系方式字段，也不会经 search 输出泄露）
_SUMMARY_PROFILE_FIELDS = ("current_company", "current_title", "industry",
                           "city", "years_of_exp", "skills")

# 手机号 / 邮箱明文形态兜底检测（防御性扫描，命中即视为明文 PII 写回）
_RE_PHONE = re.compile(r"1[3-9]\d{9}")
_RE_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")


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


def _today() -> str:
    return date.today().isoformat()


def _resolve_pool(pool_dir: str) -> Path:
    """解析人才库目录：相对路径相对本脚本所在目录解析。"""
    p = Path(pool_dir)
    if not p.is_absolute():
        p = (Path(__file__).resolve().parent / p).resolve()
    return p


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


def _load_index(pool: Path) -> dict:
    idx_path = pool / "_index.json"
    if idx_path.exists():
        return _load_json_file(idx_path, "库级索引 _index.json")
    return {"schema": SCHEMA_NAME, "schema_version": SCHEMA_VERSION,
            "count": 0, "id_prefix": ID_PREFIX, "fields": [],
            "searchable_filters": ["skills", "city", "years_of_exp", "labels", "status"],
            "audit_log": [], "updated_at": _today()}


def _save_index(pool: Path, index: dict) -> None:
    index["updated_at"] = _today()
    (pool / "_index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _validate_record(rec: dict) -> None:
    """档案 schema fail-fast 校验：缺必填字段即拒绝，错误信息指明字段。"""
    if rec.get("schema") != SCHEMA_NAME:
        raise _err("E001", f"schema 须为 \"{SCHEMA_NAME}\"，实际为 {rec.get('schema')!r}",
                   field="schema")
    if rec.get("schema_version") != SCHEMA_VERSION:
        raise _err("E001",
                   f"schema_version 须为 \"{SCHEMA_VERSION}\"，实际为 {rec.get('schema_version')!r}",
                   field="schema_version")
    cid = rec.get("candidate_id")
    if not isinstance(cid, str) or not re.fullmatch(rf"{ID_PREFIX}\d{{6}}", cid):
        raise _err("E001", f"candidate_id 缺失或格式非法（须为 {ID_PREFIX}+6位数字，如 R000002）",
                   field="candidate_id")
    profile = rec.get("profile")
    if not isinstance(profile, dict):
        raise _err("E001", "profile 缺失或类型错误（须为对象）", field="profile")
    for f in ("current_company", "current_title", "city", "years_of_exp", "skills"):
        if f not in profile or profile[f] in (None, "", []):
            raise _err("E001", f"profile.{f} 缺失或为空（必填：技能/城市/年限/现职信息）",
                       field=f"profile.{f}")
    if not isinstance(profile["years_of_exp"], (int, float)) or profile["years_of_exp"] < 0:
        raise _err("E040", "profile.years_of_exp 须为非负数字", field="profile.years_of_exp")
    if not isinstance(profile["skills"], list) or not all(
            isinstance(s, str) for s in profile["skills"]):
        raise _err("E020", "profile.skills 须为字符串数组", field="profile.skills")
    source = rec.get("source")
    if not isinstance(source, dict):
        raise _err("E001", "source 缺失或类型错误（须为对象）", field="source")
    consent = source.get("consent")
    if not isinstance(consent, dict) or consent.get("obtained") is not True:
        raise _err("E060",
                   "合规拒绝：source.consent.obtained 必须为 true 方可入库"
                   "（个人信息保护法要求处理个人信息前取得个人同意）",
                   field="source.consent.obtained")
    if not rec.get("status"):
        raise _err("E001", "status 缺失（如 active / contacted / hired / deleted）",
                   field="status")


def _scan_plaintext_pii(obj: object, path: str = "") -> list[str]:
    """防御性扫描：检测明文手机号 / 邮箱形态，返回命中路径列表。"""
    hits: list[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            hits.extend(_scan_plaintext_pii(v, f"{path}.{k}" if path else str(k)))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            hits.extend(_scan_plaintext_pii(v, f"{path}[{i}]"))
    elif isinstance(obj, str):
        # 脱敏形态（含 *）不算明文
        if "*" not in obj and (_RE_PHONE.search(obj) or _RE_EMAIL.search(obj)):
            hits.append(path)
    return hits


def _record_path(pool: Path, candidate_id: str) -> Path:
    """解析档案路径：强制 ID 格式 + 断言目标落在 pool 目录内（防路径穿越）。

    这是本模块**唯一**的路径构造点，get/update/delete 三条入口全部经此收口。
    add 路径另有 _validate_record 的 ID 校验（纵深防御，此处不依赖它）：
    未校验时 candidate_id 形如 "../secret/other" 或绝对路径即可读写（乃至
    path.unlink 物理删除）人才库之外的文件。
    """
    if not isinstance(candidate_id, str) or not re.fullmatch(rf"{ID_PREFIX}\d{{6}}", candidate_id):
        raise _err("E040",
                   f"candidate_id 格式非法（须为 {ID_PREFIX}+6位数字，如 R000002）：{candidate_id!r}",
                   field="candidate_id")
    path = pool / f"{candidate_id}.json"
    # 纵深防御：ID 格式已排除 ".."，此处再断言解析后目标的父目录 == pool 根，
    # 挡掉符号链接等残余越界。
    if path.resolve().parent != pool.resolve():
        raise _err("E040",
                   f"candidate_id 越界：目标不在人才库目录内，已拒绝：{candidate_id!r}",
                   field="candidate_id")
    return path


def _summary_view(rec: dict) -> dict:
    """search 脱敏简要视图：白名单字段 + labels/status，不含 pii 块及任何其他字段。"""
    profile = rec.get("profile", {})
    return {
        "candidate_id": rec.get("candidate_id"),
        **{f: profile.get(f) for f in _SUMMARY_PROFILE_FIELDS if f in profile},
        "labels": rec.get("labels", []),
        "status": rec.get("status"),
    }


def add_candidate(record_path: str, pool_dir: str) -> dict:
    """新增候选人档案。

    校验：schema/schema_version/candidate_id 前缀；必填字段完整
    （技能/城市/年限/来源/同意记录）；source.consent.obtained 必须为 true，
    否则抛 E060 合规拒绝（fail-fast）。档案本身即脱敏视图，落盘前做
    明文 PII 兜底扫描；写入后更新 _index.json 的 count 与 updated_at。
    """
    pool = _resolve_pool(pool_dir)
    pool.mkdir(parents=True, exist_ok=True)
    rec = _load_json_file(Path(record_path), "候选人档案")
    _validate_record(rec)

    cid = rec["candidate_id"]
    dest = _record_path(pool, cid)
    if dest.exists():
        raise _err("E040", f"档案 {cid} 已存在，新增被拒绝（如需修改请用 update）",
                   field="candidate_id")

    pii_hits = _scan_plaintext_pii(rec)
    if pii_hits:
        raise _err("E060",
                   "合规拒绝：检测到疑似明文联系方式字段（须先脱敏后入库）："
                   + ", ".join(pii_hits),
                   field=", ".join(pii_hits))

    index = _load_index(pool)
    # 序号自动递增：以索引 count 与现有文件的最大序号为准
    existing = sorted(p.stem for p in pool.glob(f"{ID_PREFIX}*.json"))
    max_seq = max([int(s[1:]) for s in existing
                   if re.fullmatch(rf"{ID_PREFIX}\d{{6}}", s)] + [index.get("count", 0)])
    expected = f"{ID_PREFIX}{max_seq + 1:06d}"
    if cid != expected:
        raise _err("E040",
                   f"candidate_id 须为自动递增的下一编号 {expected}（实际为 {cid}）",
                   field="candidate_id")

    rec.setdefault("created_at", _today())
    rec["updated_at"] = _today()
    dest.write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    index["count"] = max_seq + 1
    _save_index(pool, index)
    return {"candidate_id": cid, "stored_at": str(dest), "pool_count": index["count"]}


def get_candidate(candidate_id: str, pool_dir: str) -> dict:
    """按 candidate_id 读取单份档案（脱敏视图）。未找到抛 E080。"""
    pool = _resolve_pool(pool_dir)
    path = _record_path(pool, candidate_id)
    return _load_json_file(path, f"候选人档案 {candidate_id}")


def search_candidates(pool_dir: str, skill: str | None = None,
                      city: str | None = None, years_min: int | None = None,
                      years_max: int | None = None,
                      labels: list[str] | None = None,
                      status: str = "active") -> list[dict]:
    """按条件检索人才库（技能/城市/年限区间/标签/状态），多条件 AND。

    遍历 resumes/ 逐档过滤，返回脱敏简要视图列表（白名单字段，防御性
    不含 pii 块之外的任何联系方式字段）。
    """
    pool = _resolve_pool(pool_dir)
    if not pool.is_dir():
        raise _err("E080", f"人才库目录不存在：{pool}", field=str(pool))

    results: list[dict] = []
    for path in sorted(pool.glob(f"{ID_PREFIX}*.json")):
        # 与 _record_path 的 ID 格式保持一致：非 {ID_PREFIX}+6位数字 的文件
        # 不可寻址，不应出现在检索结果里（否则与 get/update/delete 不自洽）。
        if not re.fullmatch(rf"{ID_PREFIX}\d{{6}}", path.stem):
            continue
        rec = _load_json_file(path, f"候选人档案 {path.name}")
        profile = rec.get("profile", {})
        if status and rec.get("status") != status:
            continue
        if skill and not any(skill.lower() in str(s).lower()
                             for s in profile.get("skills", [])):
            continue
        if city and profile.get("city") != city:
            continue
        years = profile.get("years_of_exp")
        if years_min is not None and (years is None or years < years_min):
            continue
        if years_max is not None and (years is None or years > years_max):
            continue
        if labels:
            rec_labels = rec.get("labels", [])
            if not all(l in rec_labels for l in labels):
                continue
        results.append(_summary_view(rec))
    return results


def update_candidate(candidate_id: str, patch_path: str, pool_dir: str) -> dict:
    """按 JSON patch 更新档案（如 status / last_contacted_at / labels）。

    不允许修改 candidate_id；patch 写入前做明文 PII 兜底扫描（禁止写回
    明文联系方式）；更新 updated_at 并同步 _index.json。
    """
    pool = _resolve_pool(pool_dir)
    path = _record_path(pool, candidate_id)
    rec = _load_json_file(path, f"候选人档案 {candidate_id}")
    patch = _load_json_file(Path(patch_path), "patch JSON")

    if "candidate_id" in patch and patch["candidate_id"] != candidate_id:
        raise _err("E040", "不允许通过 update 修改 candidate_id", field="candidate_id")
    patch.pop("candidate_id", None)

    pii_hits = _scan_plaintext_pii(patch)
    if pii_hits:
        raise _err("E060",
                   "合规拒绝：patch 中检测到疑似明文联系方式字段（禁止写回明文 PII）："
                   + ", ".join(pii_hits),
                   field=", ".join(pii_hits))

    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(rec.get(key), dict):
            rec[key].update(value)
        else:
            rec[key] = value
    rec["updated_at"] = _today()
    _validate_record(rec)

    path.write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    index = _load_index(pool)
    _save_index(pool, index)
    return {"candidate_id": candidate_id, "updated_fields": sorted(patch.keys()),
            "updated_at": rec["updated_at"]}


def delete_candidate(candidate_id: str, pool_dir: str, operator: str,
                     reason: str) -> dict:
    """物理删除候选人档案（个保法第四十七条 删除权）。

    删除档案文件，并在 _index.json 的 audit_log 追加审计条目
    （时间、operator、reason、candidate_id）。删除不可恢复，
    执行前须经主理人确认（由调用方保证）。
    """
    pool = _resolve_pool(pool_dir)
    path = _record_path(pool, candidate_id)
    if not path.exists():
        raise _err("E080", f"候选人档案 {candidate_id} 不存在：{path}",
                   field="candidate_id")

    path.unlink()  # 物理删除（删除权，不可恢复）

    index = _load_index(pool)
    index["count"] = max(0, int(index.get("count", 1)) - 1)
    index.setdefault("audit_log", []).append({
        "action": "delete",
        "candidate_id": candidate_id,
        "operator": operator,
        "reason": reason,
        "at": _today(),
    })
    _save_index(pool, index)
    return {"candidate_id": candidate_id, "deleted": True,
            "pool_count": index["count"]}


def reindex(pool_dir: str) -> dict:
    """重建库级 _index.json：扫描 pool_dir 下全部 R*.json，

    重算 count / fields 覆盖情况 / updated_at，并校验每份档案的
    schema 与必填字段（损坏档案列入报告，不静默跳过）。
    """
    pool = _resolve_pool(pool_dir)
    if not pool.is_dir():
        raise _err("E080", f"人才库目录不存在：{pool}", field=str(pool))

    index = _load_index(pool)
    valid: list[str] = []
    broken: list[dict] = []
    fields_union: set[str] = set()
    for path in sorted(pool.glob(f"{ID_PREFIX}*.json")):
        try:
            rec = _load_json_file(path, f"候选人档案 {path.name}")
            _validate_record(rec)
        except StructuredError as exc:
            broken.append({"file": path.name, "code": exc.code,
                           "message": exc.message, "field": exc.field})
            continue
        valid.append(rec["candidate_id"])
        fields_union.update(rec.keys())

    index["count"] = len(valid)
    index["fields"] = sorted(fields_union)
    _save_index(pool, index)
    return {"count": len(valid), "valid_ids": valid, "broken_files": broken,
            "fields": index["fields"], "updated_at": index["updated_at"]}


def _cli() -> int:
    parser = argparse.ArgumentParser(
        description="人才库 CRUD + 索引维护。档案仅存脱敏视图；无同意记录（source.consent.obtained=true）不入库。",
    )
    parser.add_argument("--pool", default="../knowledge/resumes",
                        help="人才库目录（默认 ../knowledge/resumes，相对本脚本）")
    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add", help="新增候选人档案（JSON 文件）")
    p_add.add_argument("--file", required=True, help="候选人档案 JSON 文件路径")

    p_get = sub.add_parser("get", help="按 ID 读取档案（脱敏视图）")
    p_get.add_argument("candidate_id", help="候选人 ID，如 R000001")

    p_search = sub.add_parser("search", help="按条件检索（脱敏视图列表）")
    p_search.add_argument("--skill", help="技能关键词，如 微服务")
    p_search.add_argument("--city", help="城市，如 杭州")
    p_search.add_argument("--years-min", type=int, help="年限下限")
    p_search.add_argument("--years-max", type=int, help="年限上限")
    p_search.add_argument("--labels", nargs="*", help="标签过滤（多个用空格分隔）")
    p_search.add_argument("--status", default="active", help="状态过滤，默认 active")

    p_update = sub.add_parser("update", help="按 JSON patch 更新档案")
    p_update.add_argument("candidate_id", help="候选人 ID")
    p_update.add_argument("--file", required=True, help="patch JSON 文件路径")

    p_delete = sub.add_parser("delete", help="物理删除档案（删除权，需主理人确认）")
    p_delete.add_argument("candidate_id", help="候选人 ID")
    p_delete.add_argument("--operator", required=True, help="操作人（审计用）")
    p_delete.add_argument("--reason", required=True, help="删除依据（审计用）")

    sub.add_parser("reindex", help="重建库级 _index.json")

    args = parser.parse_args()

    try:
        if args.command == "add":
            out = add_candidate(args.file, args.pool)
        elif args.command == "get":
            out = get_candidate(args.candidate_id, args.pool)
        elif args.command == "search":
            out = search_candidates(args.pool, skill=args.skill, city=args.city,
                                    years_min=args.years_min, years_max=args.years_max,
                                    labels=args.labels, status=args.status)
        elif args.command == "update":
            out = update_candidate(args.candidate_id, args.file, args.pool)
        elif args.command == "delete":
            out = delete_candidate(args.candidate_id, args.pool,
                                   operator=args.operator, reason=args.reason)
        elif args.command == "reindex":
            out = reindex(args.pool)
        else:  # pragma: no cover - argparse required=True 已兜底
            parser.error(f"未知子命令 {args.command}")
            return 1
    except StructuredError as exc:
        print(str(exc), file=sys.stderr)
        return 2 if exc.code == "E080" else 1

    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
