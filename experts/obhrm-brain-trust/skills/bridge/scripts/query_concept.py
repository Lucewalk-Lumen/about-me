#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OBHRM 统一概念检索入口（obhrm-bridge / knowledge 自包含，纯标准库零依赖）

三级检索策略:
  L1 概念桥接  —— 命中 _bridge.json 概念词表，一次返回「教材章节 + 理论 + 量表 + R 方法」四库联动结果
  L2 ID 透传   —— 输入 S001 / T033 / 6.1 等 ID，直接定位单条记录
  L3 全库回退  —— 未收录概念，并行在理论/量表/R 三库做关键词检索

用法:
  python3 query_concept.py "情感"                 # L1 概念桥接（推荐入口）
  python3 query_concept.py "情感" --full          # 展开：读取理论/量表/R 脚本正文
  python3 query_concept.py "T033"                 # L2 ID 透传
  python3 query_concept.py "领导力" --limit 5
  python3 query_concept.py "情感" --json          # 输出原始 JSON（供程序消费）
  python3 query_concept.py "情感" --root <专家团根>  # 显式指定专家团根（等价环境变量 OBHRM_ROOT）

匹配优先级: ID 精确(S/T/数字编号) > 概念词表(label/zh/en 子串) > 三库关键词回退。

健壮性: 兄弟库根缺失为致命错误（退出码 1）；教材目录缺失为非致命，教材锚点降级为提示文本，
其余三库（理论/量表/R 方法）检索照常工作。
"""
import argparse
import json
import os
import re
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
KNOW = os.path.join(SKILL, "knowledge")

BRIDGE = os.path.join(KNOW, "_bridge.json")

# ---------------------------------------------------------------- 路径解析
# 本脚本需跨技能读取三个兄弟库与教材，因此必须确定「兄弟库根」「教材根」与「输出基准」。
# 不再假定任何固定部署形态，改为「向上搜索式定位」：从起点逐级向父目录查找含标记的目录。
# 这样同时兼容两种布局：
#   A 技能布局（本包）    <根>/skills/bridge/scripts/  → 兄弟库在 <根>/skills/，
#                        教材在 <根>/skills/bridge/references/
#   B 旧/平铺布局        <根>/bridge/scripts/          → 兄弟库在 <根>/，教材在 <根>/references/
_LIB_MARK = os.path.join("theory", "knowledge", "_theory_index.json")
_REF_MARK = os.path.join("references", "textbook")
_LEVELS = 6


def _find_up(start, rel_marker, levels=_LEVELS):
    """从 start 起逐级向父目录查找「含 rel_marker 的目录」。

    命中返回该目录（绝对路径），向上 levels 级仍无命中返回 None。
    """
    cur = os.path.abspath(start)
    for _ in range(levels + 1):
        if os.path.exists(os.path.join(cur, rel_marker)):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:          # 已到文件系统根
            break
        cur = parent
    return None


def _under(path, root):
    """path 是否位于 root 之下（含自身）。"""
    if not path or not root:
        return False
    p = os.path.abspath(path)
    r = os.path.abspath(root)
    return p == r or p.startswith(r + os.sep)


def _safe_join(root, rel, suffix=""):
    """把「来自索引/桥接数据」的相对路径拼到 root 下，并做包含性校验。

    索引 JSON（_r_index.json 的 file、_bridge.json 的 theory_id/scale_id）属包内数据，
    但用户可自行编辑（query_concept.py 明确提示可补录条目），因此其中的值不可信：
    `os.path.join` 允许 `../../../` 逃出包根，导致任意文件读取。
    故所有由数据拼出的路径都必须经此函数：越界时返回 ""，调用方按「文件缺失」处理
    （exists=False、不读取），既不崩溃也不静默通过。
    """
    if not root or not rel:
        return ""
    fp = os.path.join(root, rel + suffix)
    return fp if _under(fp, root) else ""


# 模块级兼容别名：由 _bootstrap() 惰性赋值，供 by_id / enrich / read_full / lib_path 等函数引用。
# 之所以惰性求值，是为了避免 import 期就 sys.exit（可被测试或其他脚本安全导入）。
LIB_ROOT = None       # 兄弟库根（含 theory / scale / ranalysis）
REF_ROOT = None       # 教材根（含 references/textbook）
ROOT = None           # 专家团根 / 部署根，输出相对路径的基准
BASE = None           # ROOT 的别名（输出相对路径起点）
T_DIR = S_DIR = R_ROOT = None
T_IDX = S_IDX = R_IDX = TEXTBOOK = None
T_STORE = S_STORE = None


def _resolve_roots(root=None):
    """解析并返回 (ROOT, LIB_ROOT, REF_ROOT)。

    - LIB_ROOT：含 theory 的「兄弟库根」，缺失返回 None（致命）。
    - REF_ROOT：含 references/textbook 的「教材根」，缺失返回 None（非致命）。
    - ROOT    ：输出相对路径的基准；显式传入的专家团根优先，否则按 LIB_ROOT 形态推断。
    """
    # 1) 显式根（--root / OBHRM_ROOT）：指向专家团根目录
    if root:
        root = os.path.abspath(root)
        skills_dir = os.path.join(root, "skills")
        lib_root = skills_dir if os.path.isdir(skills_dir) else root
        # 教材根：优先在显式根内部向上解析；若解析到根之外则忽略，退化为根下两种布局的固定位置
        ref_root = _find_up(root, _REF_MARK, _LEVELS)
        if ref_root is not None and not _under(ref_root, root):
            ref_root = None
        if ref_root is None:
            for cand in (os.path.join(root, "references", "textbook"),
                         os.path.join(root, "skills", "bridge", "references", "textbook")):
                if os.path.isdir(cand):
                    # cand = <教材根>/references/textbook → 上溯两级得教材根
                    ref_root = os.path.dirname(os.path.dirname(cand))
                    break
        return root, lib_root, ref_root

    # 2) 默认：向上搜索式定位（同时兼容新布局与旧布局）
    lib_root = _find_up(SKILL, _LIB_MARK, _LEVELS)
    ref_root = _find_up(HERE, _REF_MARK, _LEVELS)
    # 输出基准：库根以「skills」结尾时取其上一级（专家团根），平铺布局时即库根本身
    if lib_root is not None and os.path.basename(lib_root) == "skills":
        out_root = os.path.dirname(lib_root)
    elif lib_root is not None:
        out_root = lib_root
    else:
        out_root = ref_root or HERE
    return out_root, lib_root, ref_root


def _bootstrap(root=None):
    """惰性解析根路径并填充模块级别名；成功返回 None，致命错误返回可操作提示文本。"""
    global LIB_ROOT, REF_ROOT, ROOT, BASE
    global T_DIR, S_DIR, R_ROOT, T_IDX, S_IDX, R_IDX, TEXTBOOK
    global T_STORE, S_STORE
    out_root, lib_root, ref_root = _resolve_roots(root)
    # 一致性校验：显式 --root 可能指向错误目录，仍需确认库标记确实存在，否则按致命错误处理
    if lib_root is not None and not os.path.exists(os.path.join(lib_root, _LIB_MARK)):
        lib_root = None
    ROOT, BASE = out_root, out_root
    LIB_ROOT, REF_ROOT = lib_root, ref_root
    if lib_root is not None:
        T_DIR = os.path.join(lib_root, "theory/knowledge/theories")
        S_DIR = os.path.join(lib_root, "scale/knowledge/scales")
        # 注意：_r_index.json 的 file 字段相对 skill 根（ranalysis/），非库根
        R_ROOT = os.path.join(lib_root, "ranalysis")
        T_IDX = os.path.join(lib_root, "theory/knowledge/_theory_index.json")
        S_IDX = os.path.join(lib_root, "scale/knowledge/_scale_index.json")
        R_IDX = os.path.join(lib_root, "ranalysis/knowledge/_r_index.json")
        # 条目的唯一来源：合并存储（不再随包分发逐条单文件）
        T_STORE = os.path.join(T_DIR, "entities.json")
        S_STORE = os.path.join(S_DIR, "entities.json")
    if ref_root is not None:
        TEXTBOOK = os.path.join(ref_root, "references", "textbook")
    if lib_root is None:
        return ("[错误] 无法定位兄弟知识库（theory / scale / ranalysis）。\n"
                f"  脚本所在技能目录: {os.path.basename(SKILL)}\n"
                f"  搜索起点: 该技能目录（向上 {_LEVELS} 级）\n"
                "  请从专家团根目录运行，或用 --root <专家团根> / 环境变量 OBHRM_ROOT 显式指定。")
    return None


RE_THEORY_ID = re.compile(r"^[tT]\d+$")
RE_SCALE_ID = re.compile(r"^[sS]\d+$")
RE_METHOD_NO = re.compile(r"^\d+(\.\d+)*$")


def load_json(p, fatal=True):
    """加载 JSON；与同族脚本的 load() 保持同一错误口径：
    损坏/缺失时给出可读信息并退出，既不抛栈回溯、也不回显本机绝对路径。

    fatal=True  （默认）顶层索引：损坏即退出——没有索引就无可报告的结果。
    fatal=False 记录级：损坏时返回 None，由调用方跳过该条并继续，
    避免「一条坏记录带走整批结果」（与 query_scales/query_theories 的降级口径一致）。
    """
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"[错误] JSON 解析失败: {os.path.basename(p)}", file=sys.stderr)
    except UnicodeDecodeError:
        print(f"[错误] 文件非 UTF-8 编码: {os.path.basename(p)}", file=sys.stderr)
    except OSError as e:
        print(f"[错误] 文件不可读: {os.path.basename(p)} ({type(e).__name__})", file=sys.stderr)
    if fatal:
        sys.exit(1)
    return None


def norm(s):
    # NFKC 归一：中文输入法下的全角 ID（Ｔ００１ / Ｓ００１ / Ｒ）与半角等价，
    # 归一后才能与 ASCII ID / 脚本路径比对。ASCII 输入经 NFKC 不变，故无行为回退。
    return unicodedata.normalize("NFKC", s or "").lower().strip()


# ---------------------------------------------------------------------------
# 合并存储（entities.json）是量表 / 理论条目的**唯一来源**。
# v1.0.2 起不再随包分发逐条单文件（Sxxx.json / Txxx.json）：内容在合并存储中
# 完整存在，而逐条文件会使包内文件数从约 156 膨胀到 900+，超出审核对文件数的上限。
_STORE_CACHE = {}


def _load_store(path):
    """载入合并存储；不存在/损坏返回 None（调用方降级处理，不中断检索）。

    降级必须**显式告警**：否则「存储故障」会被误报为「库内无匹配」，
    用户会得出"这个条目不存在"的错误结论，而真正的故障被完全吞掉。
    """
    if path in _STORE_CACHE:
        return _STORE_CACHE[path]
    store = None
    if os.path.isfile(path):
        store = load_json(path, fatal=False)
    if store is None:
        print(f"[错误] 合并存储不可用（{os.path.basename(path)}），"
              f"相关条目的正文字段不可用；本结果仅为索引摘要",
              file=sys.stderr)
    _STORE_CACHE[path] = store
    return store


def _store_lookup(store_path, rec_id, warn=True):
    """按 id 从合并存储取记录；找不到返回 None。

    store_path 为合并存储的文件路径；实际载入走 _load_store 的进程内缓存，
    避免同一份 entities.json 在一次运行内被重复解析。

    warn=True 时，若合并存储可用但该 id 不在其中，会在 stderr 显式告警
    ——「存储里没有这条」与「存储整体故障」是两种不同故障，都不能让用户
    误以为「库内无此条目」。
    """
    if not store_path or not rec_id:
        return None
    store = _load_store(store_path)
    if not isinstance(store, dict):
        return None
    rec = store.get(rec_id)
    if rec is None and str(rec_id).isdigit():
        rec = store.get(int(rec_id))
    if rec is None and warn:
        print(f"[错误] 合并存储中缺少条目 {rec_id}，该条正文字段不可用",
              file=sys.stderr)
    return rec


# 索引规模较大（量表 599 / 理论 134 / R 108），一次运行内可能被反复读取，
# 故做进程内缓存，避免同一批 JSON 重复解析多遍。
_IDX_CACHE = {}


def load_index(key, path):
    """带缓存地加载索引的 nodes 列表。"""
    if key not in _IDX_CACHE:
        _IDX_CACHE[key] = load_json(path)["nodes"]
    return _IDX_CACHE[key]


# 输出路径一律以「专家团根目录」为基准（skills/<库>/…、skills/bridge/references/…），
# 平铺部署下即部署目录（<库>/…、references/…）。两种情形下路径字面都直观可读，
# 上层智能体无需按部署方式改写前缀。
def _rel(path):
    if path is None:
        return ""
    return os.path.relpath(path, BASE).replace(os.sep, "/")


def lib_path(*parts):
    return _rel(os.path.join(LIB_ROOT, *parts))


def ref_path(*parts):
    if REF_ROOT is None:
        return "（教材目录未定位）"
    return _rel(os.path.join(REF_ROOT, *parts))


PATH_HINT = "路径基准：下列相对路径以「专家团根目录」为起点（平铺布局下则为部署根目录）"

# 教材目录缺失时的降级提示（非致命）
REF_MISSING_HINT = "教材锚点: 教材目录未随包分发，教材锚点不可用（理论/量表/R 方法检索不受影响）"

# L1 一次最多展示的概念块数：刻意保持 3（上下文预算取舍），
# 但命中更多时必须显式告知总数/展示数，不做静默截断。
CONCEPT_CAP = 3
TRUNC_HINT = ("[截断] 概念词表命中 {total} 个概念，此处按上下文预算仅展示前 {shown} 个"
              "（--json 的 total_matched/shown 字段同样给出计数）。"
              "如需定位其余概念，请用更具体的构念词，或直接查对应库："
              "query_theories.py / query_scales.py / query_r.py。")


# ---------------------------------------------------------------- L2: ID 透传
def by_id(q):
    # 先做 NFKC 归一：全角 Ｔ００１ / Ｓ００１（中文输入法常见）须与半角等价，
    # 否则下面三个 ASCII 正则（^[tT]\d+$ 等）会直接漏判。归一后仍走同一批正则，
    # 用户输入中的路径穿越字符依旧被这些正则挡住（既有安全边界不变）。
    q = norm(q)
    if RE_THEORY_ID.match(q):
        rec = _store_lookup(T_STORE, q.upper())
        if rec is not None:
            return {"mode": "id", "kind": "theory", "id": q.upper(),
                    "path": lib_path("theory/knowledge/theories", "entities.json"),
                    "record": rec}
        # 存储整体不可用 ≠ 该条目不存在：此时不得继续向 L1/L3 回退，
        # 否则「存储故障」会被误报成「库内无匹配」。
        if _load_store(T_STORE) is None:
            return {"mode": "degraded", "kind": "theory", "id": q.upper(),
                    "path": lib_path("theory/knowledge/theories", "entities.json"),
                    "record": None}
    if RE_SCALE_ID.match(q):
        rec = _store_lookup(S_STORE, q.upper())
        if rec is not None:
            return {"mode": "id", "kind": "scale", "id": q.upper(),
                    "path": lib_path("scale/knowledge/scales", "entities.json"),
                    "record": rec}
        if _load_store(S_STORE) is None:
            return {"mode": "degraded", "kind": "scale", "id": q.upper(),
                    "path": lib_path("scale/knowledge/scales", "entities.json"),
                    "record": None}
    if RE_METHOD_NO.match(q):
        for n in load_index("r", R_IDX):
            if n["method_no"] == q:
                rel = n.get("file") or ""
                # file 来自可编辑的 _r_index.json，须经包含性校验（_safe_join）；
                # 越界时 fp="" → exists=False，按文件缺失处理，不读取包外文件。
                fp = _safe_join(R_ROOT, rel)
                return {"mode": "id", "kind": "method", "id": q,
                        "path": lib_path("ranalysis", rel) if rel else "",
                        "node": n, "exists": bool(fp) and os.path.exists(fp)}
    return None


# L1 概念桥接
PARTIAL_TAIL = 2   # 精确命中之后额外附带的「部分匹配」概念条数上限

# ---- 变体匹配（v1.0.2 新增）------------------------------------------------
# 问题：原有匹配只有「查询 ⊆ 某个词表变体」**单向**（`ql in norm(x)`），
# 导致同一构念的另一种语序/带后缀写法全部落空：
#   · 查询 ⊂ 变体：查「感知组织支持」→ 词表有「组织支持」但匹配不上（语序反转）
#   · 查询 ⊃ 变体：查「公平性」    → 词表有「公平」但匹配不上（带后缀修饰）
# 实测「感知组织支持」「团队心理安全」「员工韧性」「公平性」「决策参与」等
# 高频构念在库内明明有对应条目，却全部报「库内无匹配」——
# 这是「库里有货、用户搜不到」，属可修复的检索缺陷，不是数据缺失。
#
# 修法：新增**反向**匹配——当查询包含某个词表变体时，也算命中。
# 为避免放宽过头引入假阳性，反向匹配设四道闸：
#   (a) 变体长度 >= VARIANT_MIN_LEN 个字符：单字泛词（心/爱/力）不算
#   (b) 变体必须是查询的**真子串**（变体 == 查询时走原有精确逻辑，不重复计）
#   (c) 变体字符被查询覆盖的比例 >= VARIANT_MIN_COVER：防止长查询偶然含一个短泛词
#   (d) 同一查询下按变体长度降序取用，避免同时涌入大量弱变体
VARIANT_MIN_LEN = 2
VARIANT_MIN_COVER = 0.5


def _covered_ratio(variant, query):
    """变体字符被查询覆盖的比例（按字符集合计，中文按字）。"""
    vs = set(variant)
    if not vs:
        return 0.0
    return sum(1 for ch in vs if ch in query) / len(vs)


def _variant_hits(bridge, q):
    """反向匹配：查询包含词表变体时命中该概念（返回 [(概念, 命中变体)]）。

    仅用**中文变体**做反向匹配：英文侧短词（如 "e"）在大词表里做子串匹配
    会被大量误命中，故英文变体不参与反向匹配。
    """
    ql = norm(q)
    out = []
    for cid, b in bridge.items():
        best = None
        for v in b.get("zh", []) or []:
            vl = norm(v)
            if len(vl) < VARIANT_MIN_LEN or vl == ql or vl not in ql:
                continue
            cov = _covered_ratio(vl, ql)
            if cov < VARIANT_MIN_COVER:
                continue
            if best is None or len(vl) > len(best[0]):
                best = (vl, cov)
        if best is not None:
            out.append((b, best[0], best[1]))
    # 变体越长越具体，排前面
    out.sort(key=lambda x: -len(x[1]))
    return out


def by_concept(bridge, q):
    ql = norm(q)
    if not ql:
        # 空串是任意字符串的子串，会让下面的 any(...) 恒真并返回词表首个概念，
        # 属误导性结果，此处直接拒绝。
        return []
    exact, partial = [], []
    for cid, b in bridge.items():
        labels = [cid, b.get("label_zh", "")] + b.get("zh", []) + b.get("en", [])
        if ql in [norm(x) for x in labels]:
            exact.append(b)
        elif any(ql in norm(x) for x in labels):
            partial.append(b)
    # 精确命中不再吞掉部分匹配：查「领导」原本只回 leadership，LMX / 变革型领导 /
    # 服务型领导 等 6 个相关概念被静默丢弃（LMX 是高频构念）。现改为精确 + 少量部分。
    # 截断在 main() 的 hits[:3] 与此处 PARTIAL_TAIL 两处都会显式告知命中总数。
    if exact:
        return exact + partial[:PARTIAL_TAIL]
    # 单向匹配落空时，再试反向变体匹配（查「公平性」→ 命中 justice 的「公平」）。
    # 与 partial 合并返回，并保持 partial 在前（字面更贴近者优先）。
    if partial:
        return partial + [b for b, _, _ in _variant_hits(bridge, q)][:PARTIAL_TAIL]
    return [b for b, _, _ in _variant_hits(bridge, q)][:PARTIAL_TAIL]


# ------------------------------------------------------------ L3: 全库回退
def fallback(q, limit):
    """三库关键词回退。

    截断可见性：真实总数记入 `_total_*`（与 L1 概念路径同口径），
    避免「命中 3 条却只显示 1 条」被误读为全部结果。
    """
    ql = norm(q)
    out = {"theories": [], "scales": [], "methods": []}
    for n in load_index("t", T_IDX):
        if ql in norm(n.get("name_zh")) or ql in norm(n.get("name_en")) or ql in norm(n.get("construct_id")):
            out["theories"].append({"id": n["theory_id"], "zh": n.get("name_zh", ""),
                                    "en": n.get("name_en", ""), "by": ["fallback"]})
    for n in load_index("s", S_IDX):
        # 检索字段须与 query_scales.py 的 search_fields 保持一致（含 title），
        # 否则「量表库能查到、桥接 L3 回退查不到」的不对称命中会出现。
        if (ql in norm(n.get("variable_zh")) or ql in norm(n.get("variable_en"))
                or ql in norm(n.get("construct_id")) or ql in norm(n.get("title"))):
            out["scales"].append({"id": n["scale_id"], "zh": n.get("variable_zh", ""),
                                  "en": n.get("variable_en", ""), "by": ["fallback"]})
    for n in load_index("r", R_IDX):
        if ql in norm(n.get("title")) or ql in norm(n.get("use_condition")):
            out["methods"].append({"id": n["method_no"], "zh": n.get("title", ""),
                                   "stage": n.get("stage", ""), "file": n.get("file", ""), "by": ["fallback"]})
    for k in list(out):
        out["_total_" + k] = len(out[k])
        if limit:
            out[k] = out[k][:limit]
    return out


# ---------------------------------------------------------------- 富化
def enrich(b, limit=None):
    """为桥接结果补充元信息（维度题数、四段覆盖标记、脚本路径）

    limit：每类条目的展示上限。传入时按上限截断条目列表，并把**真实总数**
    记入 `_total_*`，供调用方显式告知「共 N 条、只展示 M 条」——
    否则 JSON 非 --full 路径下 --limit 完全失效（条目列表仍是全量），
    或文本模式只标「【量表 1】」而让用户误以为该概念只有 1 个量表。
    """
    tmeta = {n["theory_id"]: n for n in load_index("t", T_IDX)}
    smeta = {n["scale_id"]: n for n in load_index("s", S_IDX)}
    for t in b.get("theories", []):
        m = tmeta.get(t["id"], {})
        t.update(n_refs=m.get("n_refs", 0), has_what=m.get("has_what", False),
                 has_processes=m.get("has_processes", False),
                 has_struct=m.get("has_struct", False), has_app=m.get("has_app", False),
                 path=lib_path("theory/knowledge/theories", "entities.json"))
        # 读取理论记录中的 note（含 D1 二次补全边界声明），供展示层渲染可见警示；
        # 记录级损坏只跳过该条 note，不影响其余字段。
        r = _store_lookup(T_STORE, t.get("id", ""))
        if r is not None:
            t["note"] = r.get("note") or ""
    for s in b.get("scales", []):
        m = smeta.get(s["id"], {})
        s.update(n_dims=m.get("n_dims", 0), n_items=m.get("n_items", 0),
                 status=m.get("status", ""),
                 has_scoring=m.get("has_scoring"),
                 path=lib_path("scale/knowledge/scales", "entities.json"))
    for mth in b.get("methods", []):
        rel = mth.get("file") or ""
        # 同 by_id：索引 file 字段须做包含性校验，越界视为文件缺失
        fp = _safe_join(R_ROOT, rel)
        mth["display_path"] = lib_path("ranalysis", rel) if rel else ""
        mth.update(exists=bool(fp) and os.path.exists(fp))
    # 条目级截断：统一在此处施加，并保留真实总数
    if limit:
        for key, tk in (("theories", "_total_theories"),
                        ("scales", "_total_scales"),
                        ("methods", "_total_methods")):
            items = b.get(key, []) or []
            b[tk] = len(items)
            if len(items) > limit:
                b[key] = items[:limit]
    return b


def _clip(text, n, path):
    """按 n 截断，并在尾部显式标注截断信息与原文出处路径。

    目的是消除「静默截断」：任何被截断的内容都能从提示中得知原文长度与完整出处，
    上层智能体可据此读取完整正文，而不是误以为已看到全部内容。
    """
    text = text or ""
    if len(text) <= n:
        return text
    return text[:n] + f"…（已截断，原文 {len(text)} 字符，完整内容见 {path}）"


def _seg_head(text, mark):
    """段标题去重：语料正文多数自带段标题（what 116 条中 115 条以「【内容】」开头），
    展示层再拼一次会输出「【内容】【内容】」。仅当正文未自带该标题时才补。"""
    return "" if (text or "").lstrip().startswith(mark) else mark


def read_full(b, limit):
    """--full：读取正文（理论四段正文与文献 / 量表维度与条目 / R 脚本用法）

    路径与容错两条原则：
    - 理论 / 量表正文从**合并存储 entities.json** 取（条目唯一来源，不再有逐条单文件）；
      R 脚本路径来自 _r_index.json 的 file 字段（用户可编辑），须经 _safe_join
      包含性校验，越界即视为记录缺失（无正文），不得读取包外文件。
    - 记录级 JSON 损坏只跳过该条并告警（stderr，仅 basename），不让一条坏记录
      带走整批结果；顶层索引仍是致命错误。
    """
    # 合并存储整体不可用时记下全局降级态：正文取不到 ≠ 原文没写，
    # 展示层须区分二者（否则会把读取故障谎报成"原文未覆盖"）。
    store_down = False
    for t in b.get("theories", [])[:limit]:
        r = _store_lookup(T_STORE, t.get("id", ""))
        if r is None:
            if _load_store(T_STORE) is None:
                store_down = True
            continue
        # 四段正文完整保留（不再静默截断）；是否截断交由展示层 _clip 显式标注
        t["what"] = r.get("what") or ""
        t["processes"] = r.get("processes") or ""
        t["structure"] = r.get("structure") or ""
        t["application"] = r.get("application") or ""
        t["references"] = r.get("references") or ""
        t["note"] = r.get("note") or ""
    for s in b.get("scales", [])[:limit]:
        r = _store_lookup(S_STORE, s.get("id", ""))
        if r is None:
            if _load_store(S_STORE) is None:
                store_down = True
            continue
        s["dimensions"] = r.get("dimensions", [])
        s["items"] = r.get("items", [])
        s["reference_used"] = r.get("reference_used", "")
        # 量表原始出处：主理人引用铁律要求以 background 为准，
        # 此前该字段在桥接层文本模式取不到，成员只能拿取用文献冒出处。
        s["background"] = r.get("background", "")
    for mth in b.get("methods", [])[:limit]:
        fp = _safe_join(R_ROOT, mth.get("file", ""))
        if fp and os.path.exists(fp):
            with open(fp, encoding="utf-8", errors="replace") as f:
                mth["script_head"] = "".join(f.readlines()[:12])
    b["_store_down"] = store_down
    return b


# ---------------------------------------------------------------- 输出
def _seg_state(it):
    """理论四段覆盖标记：内容 what / 作用机制 processes / 结构 structure / 应用 application。

    缺失态显式写为 [原文未覆盖]，严禁以静默 [X] 掩盖或在正文侧补写。
    —— 本函数是上述原则的落地点，因此必须覆盖全部四段：先前只列 3 段而静默丢掉
    processes，与原则本身冲突。
    """
    parts = []
    for label, key in (("what", "has_what"), ("processes", "has_processes"),
                       ("structure", "has_struct"), ("application", "has_app")):
        parts.append(f"{label}[OK]" if it.get(key) else f"{label}[原文未覆盖]")
    return "  ".join(parts)


def _is_d1_supplemented(it):
    """检测理论条目是否含「依据内部教材 D1 二次补全」的内容。"""
    note = it.get("note") or ""
    return ("内源补足" in note) or ("D1" in note and "教材" in note)


def fmt(b, q, full, limit):
    L = []
    is_fb = b["concept_id"].startswith("fallback:")
    if not is_fb:
        L.append(f"=== 概念桥接命中: {b.get('label_zh','')} ({b['concept_id']}) ===")
    if REF_ROOT is None:
        # 教材目录未分发：降级为提示文本，不阻断其余三库检索
        L.append(REF_MISSING_HINT)
    elif b.get("chapter"):
        ch = b["chapter"]
        ch_no = ch[2:].lstrip("0") if isinstance(ch, str) and len(ch) >= 2 else str(ch)
        L.append(f"教材锚点: 第{ch_no}章 {b.get('chapter_title','')}"
                 f"  → {ref_path('references', 'textbook', (ch if isinstance(ch, str) else '') + '.md')}"
                 f"  引用格式【出处：D1,§X.Y】")
    else:
        L.append("教材锚点: 本教材未覆盖该概念")
    # 概念级 note：说明本概念的挂载口径（如"为何不挂某类条目"），
    # 不输出会让用户只看到"无匹配条目"而不知原因，等同静默省略。
    cnote = (b.get("note") or "").strip()
    if cnote:
        L.append(f"挂载说明: {cnote}")
    L.append("")
    for kind, key in (("理论", "theories"), ("量表", "scales"), ("R 方法", "methods")):
        items = b.get(key, []) or []
        # 真实总数（enrich 已按 --limit 截断列表，_total_* 保留原总数）
        total = b.get("_total_" + key, len(items))
        shown = items[:limit]
        L.append(f"【{kind} {len(shown)}】")
        if not items:
            L.append("  （本概念在库中无匹配条目）")
        elif total > len(shown):
            # 消除静默截断：--limit 砍掉了多少必须写明，否则用户会把
            # 「只列出 1 条」误读为「该概念下只有 1 个量表」。
            # （与 library_query.py 的 trunc_hint 同口径：截断可见，不静默。）
            L.append(f"  [截断] 本概念下共 {total} 条{kind}，受 --limit {limit} "
                     f"限制仅展示 {len(shown)} 条；可用更精确的关键词或增大 --limit 收窄")
        for it in shown:
            if key == "theories":
                L.append(f"  {it['id']}  {it['zh']} / {it['en']}")
                nrefs = it.get("n_refs", 0)
                # 文献数为 0 时不写「文献 0 篇」——那会被误读为"该理论没有文献"，
                # 实际含义是"原始资料未登记可核验文献条目"，两者语义完全不同。
                refs_txt = f"文献 {nrefs} 篇" if nrefs else "文献 未登记（原始资料未载明可核验文献条目）"
                L.append(f"       段落[{_seg_state(it)}]  {refs_txt}  → {it['path']}")
                # D1 二次补全可见警示：补足内容来自内部教学教材（二次来源），
                # 非原始文献直采，须提示使用者核对原始出处、勿作权威引用。
                if _is_d1_supplemented(it):
                    L.append("       ⚠️ [内源补足警示] 本条含依据内部教材 D1 的二次补全内容，"
                             "属内部教学二次来源而非原始同行评议文献；状态已降为 draft，"
                             "引用前请核对【出处：D1,§…】锚点所指原始出处，勿作经核验的权威内容。")
                if full:
                    # 四段正文 + 参考文献：read_full() 已全部载入，此前只打印 what，
                    # 使 processes / structure / application / references 被静默丢弃。
                    # 空段按既定口径显式写出「（原文未覆盖）」，不得留白。
                    #
                    # 关键区分：合并存储不可用导致正文取不到，与原文确实为空是
                    # 两回事——前者是**读取故障**（须报故障、退出码 2），后者是
                    # **资料未覆盖**（正常状态）。把故障渲染成"原文未覆盖"，
                    # 等于谎称"原始资料没写"，掩盖了真实故障。
                    store_down = b.get("_store_down")
                    for seg, mark in (("what", "【内容】"), ("processes", "【作用机制】"),
                                      ("structure", "【结构】"), ("application", "【应用】"),
                                      ("references", "【文献】")):
                        txt = it.get(seg) or ""
                        if not txt.strip():
                            if store_down:
                                L.append(f"       {mark}（读取故障：合并存储不可用，"
                                         "正文未能读出——须先修复存储资产）")
                            else:
                                L.append(f"       {mark}（原文未覆盖）")
                            continue
                        L.append(f"       {_seg_head(txt, mark)}{_clip(txt, 220, it['path'])}")
            elif key == "scales":
                L.append(f"  {it['id']}  {it['zh']} / {it['en']}")
                L.append(f"       {it.get('n_dims',0)} 维度 / {it.get('n_items',0)} 题  状态 {it.get('status','')}  → {it['path']}")
                # 计分方式未载明：摘要行即显式告知，不只在 --full 才可见
                if it.get("has_scoring") is False:
                    L.append("       计分方式: （原文未覆盖）该量表各维度的计分方式在原始资料中未载明，"
                             "使用前须回原始文献核对，不臆造计分规则。")
                if full:
                    if b.get("_store_down") and not it.get("dimensions") and not it.get("items"):
                        L.append("       （读取故障：合并存储不可用，量表维度与条目未能读出"
                                 "——须先修复存储资产）")
                    for d in it.get("dimensions", [])[:6]:
                        # 计分方式未载明时显式标注，不留空让人误以为无计分规则
                        sc = d.get("scoring") or "（计分方式未载明）"
                        L.append(f"       维度: {d.get('name_zh','')} ({d.get('item_count',0)}题, {sc})")
                    for itx in it.get("items", [])[:5]:
                        rv = " [反向]" if itx.get("reverse") else ""
                        L.append(f"         {itx.get('no','')}. {itx.get('text','')}{rv}")
                    if it.get("reference_used"):
                        L.append(f"       取用文献: {_clip(it['reference_used'], 110, it['path'])}")
                    # 量表原始出处（引用铁律的依据）：background 缺失即显式说明，
                    # 不得让取用文献被误当原始出处。
                    bg = (it.get("background") or "").strip()
                    if bg:
                        L.append(f"       原始出处: {_clip(bg, 200, it['path'])}")
                    else:
                        L.append("       原始出处: （原文未覆盖）——正式引用前须回原始文献核对，"
                                 "不得以取用文献替代")
            else:
                ok = "" if it.get("exists", True) else "  [文件缺失]"
                p = it.get("display_path") or it.get("file", "")
                L.append(f"  {it['id']}  {it['zh']}  [{it.get('stage','')}]  → {p}{ok}")
                if full and it.get("script_head"):
                    head = it["script_head"].replace("\n", "\n       ")
                    L.append("       " + _clip(head, 400, p))
        L.append("")
    return "\n".join(L)


def _positive_int(s):
    """--limit 必须是正整数：0 会导致「标称 N 条、列出 0 条」，负数会触发静默尾部截取。"""
    try:
        v = int(s)
    except ValueError:
        raise argparse.ArgumentTypeError(f"必须是正整数，收到: {s!r}")
    if v < 1:
        raise argparse.ArgumentTypeError(f"必须是 >=1 的整数，收到: {v}")
    return v


def _shorten(q, n=60):
    """未命中回显时截断超长查询，避免污染输出。"""
    q = (q or "").strip()
    return q if len(q) <= n else q[:n] + f"…（共 {len(q)} 字符）"


def _lib_sizes():
    """实时统计三库规模，避免提示信息中的数字随库扩容而失真。"""
    return (len(load_index("t", T_IDX)), len(load_index("s", S_IDX)),
            len(load_index("r", R_IDX)))


def main():
    ap = argparse.ArgumentParser(description="OBHRM 统一概念检索（教材·理论·量表·R 方法四库联动）")
    ap.add_argument("query", help="概念词(如 情感/领导力) 或 ID(如 S001/T033/6.1)")
    ap.add_argument("--full", action="store_true", help="展开正文（理论四段/量表条目/脚本头）")
    ap.add_argument("--limit", type=_positive_int, default=10, help="每类结果展示条数（正整数，默认 10）")
    ap.add_argument("--json", action="store_true", help="输出原始 JSON")
    ap.add_argument("--root", default=None,
                    help="专家团根目录（覆盖自动定位；等价环境变量 OBHRM_ROOT）")
    args = ap.parse_args()

    if not args.query.strip():
        ap.error("查询词不能为空（空查询会命中全部概念，结果无意义）")

    # 惰性解析根路径：兄弟库缺失才致命；教材缺失仅降级
    root = args.root or os.environ.get("OBHRM_ROOT") or None
    boot_err = _bootstrap(root)
    if boot_err:
        print(boot_err, file=sys.stderr)
        return 1

    if not os.path.exists(BRIDGE):
        print(f"[错误] 桥接索引缺失：{os.path.basename(BRIDGE)}", file=sys.stderr)
        return 1
    bridge = load_json(BRIDGE).get("concepts", {})

    # L2
    hit = by_id(args.query)
    if hit and hit.get("mode") == "degraded":
        # 存储故障：明确报故障，不谎称「库内无匹配」
        print(f"[错误] 合并存储不可用，无法读取条目 {hit['id']} 的正文"
              f"（{hit['path']}）；这不是「库内无此条目」，而是资产读取故障。",
              file=sys.stderr)
        print(f"=== ID 精确命中: {hit['id']} ({hit['kind']}) —— 但正文不可用 ===")
        print(f"路径: {hit['path']}")
        return 2
    if hit:
        if args.json:
            print(json.dumps(hit, ensure_ascii=False, indent=2))
        else:
            print(f"=== ID 精确命中: {hit['id']} ({hit['kind']}) ===")
            print(f"路径: {hit['path']}")
            if hit["kind"] in ("theory", "scale") and not args.full:
                print("（加 --full 读取完整记录）")
            if args.full:
                rec = json.dumps(hit.get("record", hit.get("node", {})), ensure_ascii=False, indent=2)
                print(_clip(rec, 4000, hit["path"]))
        return 0

    # L1
    hits = by_concept(bridge, args.query)
    if hits:
        shown_n = min(len(hits), CONCEPT_CAP)
        # 放宽标注：反向变体匹配命中时必须显式告知「非精确结果」，
        # 否则用户会把「查公平性命中 justice」误读为精确匹配。
        relaxed_by = [v for _, v, _ in _variant_hits(bridge, args.query)]
        relaxed_note = ""
        if relaxed_by and not any(
                norm(args.query) in [norm(x) for x in
                                     ([b.get("concept_id", ""), b.get("label_zh", "")]
                                      + (b.get("zh", []) or []) + (b.get("en", []) or []))]
                for b in hits):
            relaxed_note = ("（本结果含变体匹配：查询词与词表变体不完全相同，"
                            "已按构念变体放宽，如「%s」→「%s」；非精确匹配）"
                            % (args.query, " / ".join(relaxed_by[:3])))
        if args.json:
            out = [read_full(enrich(h, args.limit), args.limit) if args.full
                   else enrich(h, args.limit)
                   for h in hits[:CONCEPT_CAP]]
            # 显式给出命中总数与展示数，消费方才能察觉被截断（原先只拿到 3 条无从判断）
            payload = {"mode": "concept", "query": args.query,
                       "total_matched": len(hits), "shown": shown_n,
                       "concepts": out}
            if relaxed_note:
                payload["relaxed_match"] = True
                payload["relaxed_note"] = relaxed_note
            # 条目级截断同样要显式告知：--limit 作用于每个概念的每一类条目，
            # 概念级 total_matched/shown 不足以反映「量表 30 条只列了 1 条」。
            item_trunc = []
            for b in out:
                for kind, key in (("理论", "theories"), ("量表", "scales"), ("R 方法", "methods")):
                    items = b.get(key, []) or []
                    total = b.get("_total_" + key, len(items))
                    if total > len(items):
                        item_trunc.append({"concept_id": b.get("concept_id", ""),
                                           "kind": kind, "total": total,
                                           "shown": len(items)})
            # 剥离内部计数字段，保持 JSON 契约只含对外字段
            degraded = False
            for b in out:
                for k in ("_total_theories", "_total_scales", "_total_methods"):
                    b.pop(k, None)
                if b.pop("_store_down", None):
                    degraded = True
            if item_trunc:
                payload["item_truncated"] = item_trunc
            # 存储故障须在 JSON 契约里显式可见：调用方不得把"只有索引摘要"
            # 当成完整结果消费。
            if degraded:
                payload["degraded"] = True
                payload["degraded_reason"] = (
                    "合并存储不可用，条目的正文字段未能读出；本结果仅为索引摘要。"
                    "这不是「库内无匹配」，而是资产读取故障。")
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 2 if degraded else 0
        blocks = []
        degraded = False
        for h in hits[:CONCEPT_CAP]:
            b = enrich(dict(h), args.limit)
            if args.full:
                b = read_full(b, args.limit)
                if b.get("_store_down"):
                    degraded = True
            blocks.append(fmt(b, args.query, args.full, args.limit))
        print(PATH_HINT)
        if relaxed_note:
            print(relaxed_note)
        # 消除静默截断：展示上限是上下文预算的有意取舍，但命中总数必须写明，
        # 否则「查 e 命中 106 个概念却只看到 3 个」会被误读为全部结果。
        if len(hits) > CONCEPT_CAP:
            print(TRUNC_HINT.format(total=len(hits), shown=shown_n))
        print(("─" * 70 + "\n").join(blocks))
        if degraded:
            # 与 L2 同口径：存储故障不得以 rc=0 静默返回，那会让调用方
            # 把"只拿到索引摘要"当成完整正文消费。
            print("[错误] 合并存储不可用，部分条目的正文字段未能读出；"
                  "以上仅为索引摘要，须先修复存储资产。", file=sys.stderr)
            return 2
        return 0

    # L3
    fb = fallback(args.query, args.limit)
    # 真实命中总数取各库的 _total_*（fallback 内部已按 limit 截断，列表长度不是总数）
    total = sum(fb.get("_total_" + k, 0) for k in ("theories", "scales", "methods"))
    if total == 0:
        nt, ns, nr = _lib_sizes()
        hint = (f"[未命中] 概念词表({len(bridge)} 个概念)与三库({nt} 理论 / {ns} 量表 / {nr} R 脚本)"
                f"均无匹配: {_shorten(args.query)}")
        if args.json:
            # --json 必须始终输出单个可解析对象：人读提示改走 stderr，
            # 否则管道给 jq / json.loads 会因中文提示行而失败。
            print(json.dumps({"mode": "miss", "query": args.query,
                              "theories": [], "scales": [], "methods": [],
                              "lib_sizes": {"theories": nt, "scales": ns, "methods": nr}},
                             ensure_ascii=False, indent=2))
            print(hint, file=sys.stderr)
            print("建议：更换更通用的构念词（如「领导」「绩效」「信任」），或用英文原词重试。",
                  file=sys.stderr)
            return 0
        print(hint)
        print("建议：更换更通用的构念词（如「领导」「绩效」「信任」），或用英文原词重试。")
        return 0
    if args.json:
        # L3 回退同样走 enrich：回退命中的条目也须带上 n_refs / has_* / n_dims /
        # n_items / status / path —— 回退是命中较弱的一路，核验状态与题数
        # 恰恰最不该缺席，否则消费方在 L3 拿到的元信息比 L1 薄一层。
        fb_json = enrich({"concept_id": "fallback:" + args.query, "label_zh": args.query,
                          "zh": [args.query], "en": [args.query], "note": "全库回退检索结果",
                          **fb}, None)
        payload = {"mode": "fallback", "query": args.query,
                   "theories": fb_json.get("theories", []),
                   "scales": fb_json.get("scales", []),
                   "methods": fb_json.get("methods", [])}
        # 截断可见性：与 L1 概念路径同口径，显式给出真实命中总数
        trunc = []
        for kind, key in (("理论", "theories"), ("量表", "scales"), ("R 方法", "methods")):
            items = payload[key]
            t = fb.get("_total_" + key, len(items))
            if t > len(items):
                trunc.append({"kind": kind, "total": t, "shown": len(items)})
        if trunc:
            payload["item_truncated"] = trunc
        # L3 --full 时正文同样来自合并存储；存储故障须显式可见
        if args.full:
            fb_full = read_full(dict(fb_json), args.limit)
            degraded_l3 = bool(fb_full.get("_store_down"))
            fb_full.pop("_store_down", None)
            if degraded_l3:
                payload["degraded"] = True
                payload["degraded_reason"] = (
                    "合并存储不可用，条目的正文字段未能读出；本结果仅为索引摘要。"
                    "这不是「库内无匹配」，而是资产读取故障。")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 2 if payload.get("degraded") else 0
    print(f"=== 概念词表未收录「{_shorten(args.query)}」，已回退全库检索（命中 {total} 条）===")
    print("提示：若该概念高频使用，可在 knowledge/_bridge.json 的概念词表中补录。\n")
    block = enrich({"concept_id": "fallback:" + args.query, "label_zh": args.query,
                    "zh": [args.query], "en": [args.query], "note": "全库回退检索结果", **fb}, args.limit)
    degraded = False
    if args.full:
        block = read_full(block, args.limit)
        degraded = bool(block.get("_store_down"))
    print(PATH_HINT)
    print(fmt(block, args.query, args.full, args.limit))
    # 截断可见性：L3 路径此前会把「命中 3 条只显示 1 条」写成「命中 1 条」，
    # 与 L1 路径口径不一致——现统一显式告知真实总数。
    for kind, key in (("理论", "theories"), ("量表", "scales"), ("R 方法", "methods")):
        t = fb.get("_total_" + key, 0)
        shown = len(block.get(key, []) or [])
        if t > shown:
            print(f"  [截断] 全库回退共命中 {t} 条{kind}，受 --limit {args.limit} "
                  f"限制仅展示 {shown} 条；可用更精确的关键词或增大 --limit 收窄")
    if degraded:
        print("[错误] 合并存储不可用，部分条目的正文字段未能读出；"
              "以上仅为索引摘要，须先修复存储资产。", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
