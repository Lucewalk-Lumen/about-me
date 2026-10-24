#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OBHRM 知识库通用检索内核（theory-library / scale-library / r-analysis 共享）。

本文件是 OBHRM 专家团家族的**单一检索标准实现**：同名的三份查询脚本
（query_theories.py / query_scales.py / query_r.py）只做「领域参数 + 渲染回调」
的薄包装，匹配、载入、安全边界、JSON 契约、覆盖率面板全部在此实现一次，
避免同一逻辑在多个技能、多个专家包内各维护一份而彼此漂移。

内核职责：

* **安全边界**：索引 JSON 属包内但用户可编辑的数据，其中由 `id` / `file`
  字段拼出的路径必须做包含性校验，越界一律按「缺失」处理——否则 `../` 或
  绝对路径可驱动读取包外任意文件。
* **绝不回显本机绝对路径**：对外只给相对专家团根的 POSIX 路径或文件名。
* **NFKC 归一**：中文输入法下的全角编号（Ｔ００１ / Ｓ００１ / Ｒ）与半角等价。
* **编号精确匹配**：形如 `8.1` 的查询按相等比较，子串包含会连带命中 `18.1`。
* **JSON 契约**：`--json` 永远向标准输出打印单个可解析对象（含未命中场景），
  人类可读提示改走标准错误，`| jq` 管道不中断。
* **坏数据降级**：单条记录损坏只跳过该条并告警，不带走整批结果；顶层索引
  损坏仍是致命错误（没有索引就无可报告的结果）。
* **消除静默截断**：`--limit` 截掉多少必须写明。
* **覆盖率即时统计**：verified / draft 占比每次检索即时统计，不在文档或代码里固定写死。
* **别名与放宽匹配**：数据层 `_meta.query_aliases` 登记等价说法；整串落空时
  退一步按分词做 OR 匹配（命中词数多者靠前），并显式标注这是放宽结果。

纯标准库，零第三方依赖；Python 3.7+ 可用。
"""
import json
import os
import re
import sys
import unicodedata
from collections import Counter

__all__ = [
    "query_library", "norm", "under", "positive_int", "trunc_hint",
    "coverage", "load_index", "display_path",
]

# 分词放宽匹配时的停用词：这些词单独命中会淹没真正的结果
_STOPWORDS = {
    "the", "a", "an", "of", "and", "or", "in", "on", "with", "for", "to",
    "de", "la", "le", "der", "und",
}
# 用于切分多词查询；中文无空格，靠标点切分
_SPLIT_RE = re.compile(r"[\s,;/、，；]+")

_END_PUNCT = "。．.!？！?；;：:"
_CLOSERS = "\"”）)《》】」』'"
_HANG_PUNCT = set("的和与及或而但并以对从在是、，；：＞＜><")


# ---------------------------------------------------------------- 基础工具
def norm(s):
    """NFKC 归一 + 小写 + 去空白。

    全角 Ｔ００１ / Ｓ００１ / Ｒ（中文输入法常见）须与半角等价，归一后才能
    与 ASCII 编号比对。ASCII 输入经 NFKC 不变，故无行为回退。
    """
    return unicodedata.normalize("NFKC", s or "").lower().strip()


def under(path, root):
    """path 解析后是否仍位于 root 之内（含 root 本身）。"""
    if not path or not root:
        return False
    p = os.path.abspath(path)
    r = os.path.abspath(root)
    return p == r or p.startswith(r + os.sep)


def positive_int(s):
    """argparse type：只接受 >=1 的整数（0 / 负数 / 非数字都拒绝）。"""
    try:
        v = int(s)
    except ValueError:
        raise TypeError("必须是正整数，收到: %r" % s)
    if v < 1:
        raise TypeError("必须是 >=1 的整数，收到: %d" % v)
    return v


def display_path(p, base):
    """把绝对路径渲染为相对 base 的 POSIX 路径；绝不回显本机绝对路径/盘符。"""
    if not p:
        return ""
    try:
        return os.path.relpath(p, base).replace(os.sep, "/")
    except ValueError:      # 跨盘符等无法求相对路径的极端情形
        return os.path.basename(p)


def trunc_hint(v):
    """正文截断三档提示：铁证档（恰 1500 字符=导出上限）/ 疑似未收尾 / 悬挂片段。"""
    s = v if isinstance(v, str) else ""
    if len(s) == 1500:
        return "  【注意】[原文被截断：仅存 1500 字符（导出上限），内容不完整]"
    if len(s) >= 1000 and not any(c in _END_PUNCT for c in s[-40:]) and s[-1:] not in _CLOSERS:
        return f"  【注意】[原文疑似未收尾，仅存 {len(s)} 字符]"
    if len(s) >= 1000:
        tail = s[-60:]
        stripped = s.rstrip()
        dangling = (
            s[-1:] in _HANG_PUNCT
            or (stripped != s and stripped[-1:] not in _END_PUNCT)
            or (tail.count("（") + tail.count("(") > tail.count("）") + tail.count(")"))
        )
        if dangling:
            return f"  【注意】[原文疑似未收尾：末尾为悬挂片段，仅存 {len(s)} 字符]"
    return ""


def coverage(nodes):
    """库内状态覆盖率：每次检索即时统计，不固定写死——与「勿沿用静态数字」的文档口径一致。"""
    c = Counter(n.get("status", "?") for n in nodes if isinstance(n, dict))
    total = len(nodes)
    ver = c.get("verified", 0)
    return {"total": total, "verified": ver, "draft": c.get("draft", 0),
            "deprecated": c.get("deprecated", 0),
            "verified_pct": round(100.0 * ver / total, 1) if total else 0.0}


def load_index(idx_path):
    """载入顶层索引；缺失 / 损坏 / 结构异常时给出可读信息并返回 None（不抛栈回溯）。"""
    name = os.path.basename(idx_path)
    if not os.path.exists(idx_path):
        print(f"[错误] 索引缺失: {name}", file=sys.stderr)
        return None
    try:
        with open(idx_path, encoding="utf-8", errors="replace") as f:
            data = json.load(f)
    except ValueError as e:
        print(f"[错误] 索引 JSON 解析失败: {name} ({type(e).__name__})", file=sys.stderr)
        return None
    except OSError as e:
        print(f"[错误] 索引文件不可读: {name} ({type(e).__name__})", file=sys.stderr)
        return None
    nodes = data.get("nodes", [])
    if not isinstance(nodes, list):
        # 结构异常时给出可读信息，避免后续以字典键为字符串迭代而崩溃
        print(f"[错误] 索引结构异常：nodes 应为数组，实为 {type(nodes).__name__}",
              file=sys.stderr)
        return None
    return data


# ---------------------------------------------------------------------------
# 合并存储：records_dir 下的 entities.json 是条目的**唯一来源**。
#
# v1.0.2 起不再随包分发逐条单文件（Sxxx.json / Txxx.json）：
# 同样的内容在 entities.json 中完整存在，而逐条文件会使包内文件数
# 从约 156 膨胀到 900+，超出专家包审核对文件数的上限。
# 因此本模块只读合并存储；合并存储整体缺失/损坏时降级为索引节点摘要并告警，
# 不再有逐条回退分支。r-analysis 等以 .R 脚本为载体的库 records_dir 为 None，
# 不会走此分支。
_STORE_CACHE = {}

def _load_store(records_dir):
    """载入 records_dir 内的合并存储 entities.json；不存在/损坏返回 None。

    首次失败即告警（stderr）：否则「存储故障」会被下游误报成「库内无匹配」，
    用户会得出"这个条目不存在"的错误结论，而真正的故障被完全吞掉。
    进程内缓存命中后不再重复告警，避免同一故障刷屏。
    """
    if records_dir in _STORE_CACHE:
        return _STORE_CACHE[records_dir]
    store = None
    sp = os.path.join(records_dir, "entities.json")
    if os.path.isfile(sp):
        try:
            with open(sp, encoding="utf-8", errors="replace") as f:
                store = json.load(f)
        except (ValueError, OSError) as e:
            store = None
            print(f"[错误] 合并存储解析失败（{os.path.basename(records_dir)}/entities.json）：{e}",
                  file=sys.stderr)
    if store is None:
        print(f"[错误] 合并存储不可用（{os.path.basename(records_dir)}/entities.json），"
              f"相关条目的正文字段不可用；本结果仅为索引摘要", file=sys.stderr)
    _STORE_CACHE[records_dir] = store
    return store


def _full_record(records_dir, node, id_field):
    """按 id 从合并存储取完整记录；不可得时回退索引节点并打标。

    合并存储是条目的唯一来源（不再随包分发逐条单文件）：
      · 合并存储整体缺失/损坏 → 回退索引节点（只有索引摘要）并告警；
      · 合并存储可用但本条不在其中 → 同样回退索引节点并告警。
    两种情形都在 stderr 显式说明，绝不静默冒充完整记录。
    """
    rec_id = str(node.get(id_field, ""))
    store = _load_store(records_dir)
    if store is not None:
        rec = store.get(rec_id)
        if rec is None and rec_id.isdigit():
            rec = store.get(int(rec_id))
        if rec is not None:
            return rec
        # 合并存储可用、但本条不在其中 → 降级为索引节点并告警
        print(f"[错误] 合并存储中缺少条目 {rec_id}，已回退为索引摘要",
              file=sys.stderr)
        bad = dict(node)
        bad["_load_error"] = True
        return bad
    # 合并存储整体不可用 → 降级为索引节点并告警
    print(f"[错误] 合并存储不可用（{os.path.basename(records_dir)}/entities.json），"
          f"条目 {rec_id} 已回退为索引摘要", file=sys.stderr)
    bad = dict(node)
    bad["_load_error"] = True
    return bad


# ---------------------------------------------------------------- 匹配
def _hay(node, search_fields):
    return norm(" ".join(str(node.get(f, "")) for f in search_fields))


def _is_id_query(q, id_regex, id_prefix):
    """查询词是否形如本库主键（如 T001 / S014 / 8.1）。"""
    if id_regex:
        return bool(id_regex.match(q))
    if id_prefix and len(q) > 1 and q[0] in id_prefix:
        return q[1:].isdigit()
    return False


def _match(node, q, id_field, id_regex, id_prefix, search_fields):
    """匹配单条节点：编号类查询按精确相等（且不再走关键词回退），否则整串包含。

    R 库 method_no 特殊处理：形如 13.1 的查询除精确命中 13.1 本身外，
    同时前缀命中 13.1.1 / 13.1.2 等子级条目——否则用户按章节号查询会
    漏掉该章下的具体方法。
    """
    if _is_id_query(q, id_regex, id_prefix):
        node_id = str(node.get(id_field, "")).lower()
        if node_id == q:
            return True
        # R 库 method_no 前缀匹配：13.1 → 13.1.1 / 13.1.2
        if id_regex and "." in q:
            return node_id.startswith(q + ".")
        return False
    return q in _hay(node, search_fields)


def _tokenize(q):
    return [t for t in _SPLIT_RE.split(norm(q)) if len(t) >= 2 and t not in _STOPWORDS]


def _load_aliases(meta):
    """读取索引 `_meta.query_aliases` 数据层别名表，键归一化。

    形如 {"领导力": ["领导", "领导理论"]}：库内条目命名习惯可能不含查询词的
    某个成分，直接查会 0 命中。别名由数据层登记，检索层只做展开，
    不在代码里内置领域词。
    """
    raw = (meta or {}).get("query_aliases") or {}
    return {norm(k): list(vs) for k, vs in raw.items()}


def _expand(query, aliases):
    """按别名表展开查询词，返回 [原查询, 别名...]（去重保序）。"""
    out = [query]
    for a in aliases.get(norm(query), []):
        if a not in out:
            out.append(a)
    return out


def _relaxed_hits(nodes, queries, search_fields):
    """整串无命中时的放宽检索：按 token 做 OR 匹配，命中 token 数多者靠前。

    仅在整串（含别名）落空后启用，避免精度回归；编号类查询不参与放宽，
    否则会破坏「精确相等」语义。
    """
    tokens = []
    for q in queries:
        for t in _tokenize(q):
            if t not in tokens:
                tokens.append(t)
    if len(tokens) < 2:
        return []
    scored = []
    for n in nodes:
        hay = _hay(n, search_fields)
        c = sum(1 for t in tokens if t in hay)
        if c:
            scored.append((c, n))
    scored.sort(key=lambda x: -x[0])   # stable：同分保持库内原顺序
    return [n for _, n in scored]


# ---------------------------------------------------------------- 主流程
def query_library(*, idx_path, label, noun_key, id_field, search_fields, query,
                  full=False, limit=10, as_json=False,
                  records_dir=None, id_regex=None, id_prefix=None,
                  use_coverage=True, render_header=None, render_full=None):
    """通用知识库检索。

    Args:
        idx_path: 顶层索引 JSON 路径。
        label: 库中文名（用于命中 / 未命中提示）。
        noun_key: `--json` 信封里放结果数组的键名（theories / scales / methods）。
        id_field: 主键字段名（theory_id / scale_id / method_no）。
        search_fields: 关键词整串匹配所扫描的字段列表。
        query / full / limit / as_json: 与 CLI 一致。
        records_dir: 单条记录目录；None 表示「索引即记录」（如 R 方法库）。
        id_regex: 主键形态正则（如 ^\\d+(\\.\\d+)*$）；与 id_prefix 二选一。
        id_prefix: 主键首字符集合（如 "tT" / "sS"），后接纯数字才算编号查询。
        use_coverage: 是否在输出里带 verified / draft 覆盖率面板。
        render_header(node) -> str: 单条非 --full 展示文本。
        render_full(rec, node) -> None: --full 时的明细输出（直接 print）。

    Returns:
        进程退出码（0 = 命中或未命中，1 = 索引缺失 / 损坏 / 结构异常）。
    """
    q = norm(query)
    if not q:
        print("[错误] 查询词不能为空（空查询会命中全部条目，结果无意义）", file=sys.stderr)
        return 1

    data = load_index(idx_path)
    if data is None:
        return 1
    nodes = data.get("nodes", [])

    aliases = _load_aliases(data.get("_meta", {}))
    queries = [x for x in _expand(q, aliases) if x]
    alias_note = " / ".join(queries[1:]) if len(queries) > 1 else ""

    seen, hits = set(), []
    for one in queries:
        for n in nodes:
            nid = n.get(id_field)
            if nid in seen:
                continue
            if _match(n, one, id_field, id_regex, id_prefix, search_fields):
                seen.add(nid)
                hits.append(n)

    relaxed = False
    if not hits and not _is_id_query(q, id_regex, id_prefix):
        hits = _relaxed_hits(nodes, queries, search_fields)
        relaxed = bool(hits)

    total_matched = len(hits)
    cov = coverage(nodes) if use_coverage else None
    hits = hits[:limit]

    if not hits:
        if as_json:
            # --json 始终输出单个可解析对象：人读提示改走 stderr，管道给 jq 才可用
            miss = {"mode": "miss", "query": query, noun_key: [], "lib_size": len(nodes)}
            if cov:
                miss["coverage"] = cov
            print(json.dumps(miss, ensure_ascii=False, indent=2))
            print(f"[未命中] {label}({len(nodes)} 条)无匹配: {query}", file=sys.stderr)
            return 0
        print(f"[未命中] {label}({len(nodes)} 条)无匹配: {query}")
        return 0

    if as_json:
        out = [_full_record(records_dir, n, id_field) if (full and records_dir) else n
               for n in hits]
        # 剥离内部标记 _load_error：JSON 对外契约只含公开字段（schema 中
        # additionalProperties=false 会拒收多余键）。降级事实改由顶层
        # degraded 标记表达，消费方据此知道正文字段不可用。
        degraded = False
        clean = []
        for rec in out:
            if isinstance(rec, dict) and rec.pop("_load_error", None):
                degraded = True
            clean.append(rec)
        payload = {"mode": "search", "query": query,
                   "total_matched": total_matched, "shown": len(hits),
                   noun_key: clean}
        if degraded:
            payload["degraded"] = True
        if cov:
            payload["coverage"] = cov
        if relaxed:
            payload["relaxed_match"] = True
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        # 降级时返回 2：调用方不得把「只有索引摘要」当成完整正文消费。
        # 口径与桥接层 query_concept.py 一致（存储故障 ≠ 库内无匹配）。
        return 2 if degraded else 0

    if cov:
        print(f"=== {label}命中 {len(hits)} 条 (库共 {cov['total']}："
              f"已核验 {cov['verified']} / 草稿 {cov['draft']}，"
              f"已核验占 {cov['verified_pct']}%) ===")
    else:
        print(f"=== {label}命中 {len(hits)} 条 (库共 {len(nodes)}) ===")

    if total_matched > len(hits):
        # 消除静默截断：--limit 截掉了多少必须写明
        print(f"[截断] 共命中 {total_matched} 条，受 --limit {limit} 限制仅展示 "
              f"{len(hits)} 条；可用更精确的关键词或增大 --limit 收窄")
    if relaxed:
        tokens = []
        for one in queries:
            for t in _tokenize(one):
                if t not in tokens:
                    tokens.append(t)
        print(f"（整串未命中，已放宽为分词匹配：{' / '.join(tokens)}；"
              f"按命中词数排序，非精确结果）")
    elif alias_note:
        print(f"（已按数据层别名展开检索：{query} → {alias_note}）")

    degraded_text = False
    for n in hits:
        if render_header:
            print(render_header(n))
        if full and render_full:
            rec = _full_record(records_dir, n, id_field) if records_dir else n
            if rec.get("_load_error"):
                print("  [合并存储不可用] 仅显示索引摘要，正文字段不可用")
                degraded_text = True
                continue
            render_full(rec, n)
    # 降级时返回 2：与 JSON 分支同口径。存储故障不得以 rc=0 静默返回，
    # 否则调用方会把「只有索引摘要」当成完整正文消费。
    if degraded_text:
        print("[错误] 合并存储不可用，部分条目的正文字段未能读出；"
              "以上仅为索引摘要，须先修复存储资产。", file=sys.stderr)
        return 2
    return 0
