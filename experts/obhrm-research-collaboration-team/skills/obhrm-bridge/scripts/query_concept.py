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
#   A 技能布局（本包）    <根>/skills/obhrm-bridge/scripts/  → 兄弟库在 <根>/skills/，
#                        教材在 <根>/skills/obhrm-textbook/ob-textbook/（独立技能，单一真源）
_LIB_MARK = os.path.join("theory-library", "knowledge", "_theory_index.json")
# 教材已去重：单一真源为 skills/obhrm-textbook/ob-textbook/（独立技能，v1.1.0 起从 obhrm-research-base 拆出）。
_TEXTBOOK_CANDIDATES = (
    os.path.join("skills", "obhrm-textbook", "ob-textbook"),
)
_REF_MARK = _TEXTBOOK_CANDIDATES[0]
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


def _find_textbook_dir(start):
    """从 start 起逐级向上定位教材目录（返回绝对路径；未命中返回 None）。

    教材单一真源已去重至 skills/obhrm-textbook/ob-textbook/（独立技能），
    命中即返回该目录本身（<根>/skills/obhrm-textbook/ob-textbook）。
    """
    cur = os.path.abspath(start)
    for _ in range(_LEVELS + 1):
        for rel in _TEXTBOOK_CANDIDATES:
            cand = os.path.join(cur, rel)
            if os.path.isdir(cand):
                return cand
        parent = os.path.dirname(cur)
        if parent == cur:
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
LIB_ROOT = None       # 兄弟库根（含 theory-library / scale-library / r-analysis）
REF_ROOT = None       # 教材目录（skills/obhrm-textbook/ob-textbook，教材单一真源）
ROOT = None           # 专家团根 / 部署根，输出相对路径的基准
BASE = None           # ROOT 的别名（输出相对路径起点）
T_DIR = S_DIR = R_ROOT = None
T_IDX = S_IDX = R_IDX = TEXTBOOK = None

# ---------------------------------------------------------------- 合并存储
# 复用 ../kernel/library_query.py 的 entities.json 合并存储实现，避免双份实现漂移。
# 单点真源：entities.json 优先、单文件回退的判定与缓存全部集中在 library_query。
_KERNEL_DIR = os.path.normpath(os.path.join(HERE, "..", "kernel"))
if _KERNEL_DIR not in sys.path:
    sys.path.insert(0, _KERNEL_DIR)
from library_query import _load_store  # noqa: E402


def _store_lookup(records_dir, rec_id):
    """从 entities.json 按键取记录；未命中返回 None（不抛错）。"""
    store = _load_store(records_dir)
    if store is None or not rec_id:
        return None
    rec = store.get(rec_id)
    if rec is None and isinstance(rec_id, str) and rec_id.isdigit():
        rec = store.get(int(rec_id))
    return rec if isinstance(rec, dict) else None


def _display_path(records_dir, rel_base, rec_id):
    """生成对用户展示的「记录出处路径」。

    单文件存在 → 单文件相对路径（保持向后兼容）。
    否则若 entities.json 存在 → `<rel_base>/entities.json#<id>`，明示记录落在合并存储，
    避免用户沿着不存在的单文件路径寻找。
    """
    fp = _safe_join(records_dir, rec_id, ".json")
    if fp and os.path.exists(fp):
        return lib_path(rel_base, rec_id + ".json")
    store = _load_store(records_dir)
    if store is not None and rec_id in store:
        return lib_path(rel_base, f"entities.json#{rec_id}")
    # 记录缺失时仍回单文件路径，配合下游 exists / 文件缺失标注
    return lib_path(rel_base, rec_id + ".json")


def _resolve_roots(root=None):
    """解析并返回 (ROOT, LIB_ROOT, REF_ROOT)。

    - LIB_ROOT：含 theory-library 的「兄弟库根」，缺失返回 None（致命）。
    - REF_ROOT：教材目录（skills/obhrm-textbook/ob-textbook），缺失返回 None（非致命）。
    - ROOT    ：输出相对路径的基准；显式传入的专家团根优先，否则按 LIB_ROOT 形态推断。
    """
    # 1) 显式根（--root / OBHRM_ROOT）：指向专家团根目录
    if root:
        root = os.path.abspath(root)
        skills_dir = os.path.join(root, "skills")
        lib_root = skills_dir if os.path.isdir(skills_dir) else root
        # 教材目录：优先在显式根内部定位；若落到根之外则忽略（非致命）。
        ref_root = _find_textbook_dir(root)
        if ref_root is not None and not _under(ref_root, root):
            ref_root = None
        return root, lib_root, ref_root

    # 2) 默认：向上搜索式定位（同时兼容新布局与旧布局）
    lib_root = _find_up(SKILL, _LIB_MARK, _LEVELS)
    ref_root = _find_textbook_dir(HERE)
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
    out_root, lib_root, ref_root = _resolve_roots(root)
    # 一致性校验：显式 --root 可能指向错误目录，仍需确认库标记确实存在，否则按致命错误处理
    if lib_root is not None and not os.path.exists(os.path.join(lib_root, _LIB_MARK)):
        lib_root = None
    ROOT, BASE = out_root, out_root
    LIB_ROOT, REF_ROOT = lib_root, ref_root
    if lib_root is not None:
        T_DIR = os.path.join(lib_root, "theory-library/knowledge/theories")
        S_DIR = os.path.join(lib_root, "scale-library/knowledge/scales")
        # 注意：_r_index.json 的 file 字段相对 skill 根（r-analysis/），非库根
        R_ROOT = os.path.join(lib_root, "r-analysis")
        T_IDX = os.path.join(lib_root, "theory-library/knowledge/_theory_index.json")
        S_IDX = os.path.join(lib_root, "scale-library/knowledge/_scale_index.json")
        R_IDX = os.path.join(lib_root, "r-analysis/knowledge/_r_index.json")
    if ref_root is not None:
        TEXTBOOK = ref_root
    if lib_root is None:
        return ("[错误] 无法定位兄弟知识库（theory-library / scale-library / r-analysis）。\n"
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


# 索引规模较大（量表 599 / 理论 134 / R 108），一次运行内可能被反复读取，
# 故做进程内缓存，避免同一批 JSON 重复解析多遍。
_IDX_CACHE = {}


def load_index(key, path):
    """带缓存地加载索引的 nodes 列表。"""
    if key not in _IDX_CACHE:
        _IDX_CACHE[key] = load_json(path)["nodes"]
    return _IDX_CACHE[key]


# 输出路径一律以「专家团根目录」为基准（skills/<库>/…、skills/obhrm-bridge/references/…），
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
        tid = q.upper()
        # 合并存储优先；单文件回退
        rec = _store_lookup(T_DIR, tid)
        if rec is not None:
            return {"mode": "id", "kind": "theory", "id": tid,
                    "path": _display_path(T_DIR, "theory-library/knowledge/theories", tid),
                    "record": rec}
        fp = os.path.join(T_DIR, tid + ".json")
        if os.path.exists(fp):
            # 记录级损坏不致命：跳过该条并继续（load_json 已打 stderr 告警）
            rec = load_json(fp, fatal=False)
            if rec is not None:
                return {"mode": "id", "kind": "theory", "id": tid,
                        "path": lib_path("theory-library/knowledge/theories",
                                         tid + ".json"),
                        "record": rec}
    if RE_SCALE_ID.match(q):
        sid = q.upper()
        rec = _store_lookup(S_DIR, sid)
        if rec is not None:
            return {"mode": "id", "kind": "scale", "id": sid,
                    "path": _display_path(S_DIR, "scale-library/knowledge/scales", sid),
                    "record": rec}
        fp = os.path.join(S_DIR, sid + ".json")
        if os.path.exists(fp):
            rec = load_json(fp, fatal=False)
            if rec is not None:
                return {"mode": "id", "kind": "scale", "id": sid,
                        "path": lib_path("scale-library/knowledge/scales",
                                         sid + ".json"),
                        "record": rec}
    if RE_METHOD_NO.match(q):
        for n in load_index("r", R_IDX):
            if n["method_no"] == q:
                rel = n.get("file") or ""
                # file 来自可编辑的 _r_index.json，须经包含性校验（_safe_join）；
                # 越界时 fp="" → exists=False，按文件缺失处理，不读取包外文件。
                fp = _safe_join(R_ROOT, rel)
                return {"mode": "id", "kind": "method", "id": q,
                        "path": lib_path("r-analysis", rel) if rel else "",
                        "node": n, "exists": bool(fp) and os.path.exists(fp)}
    return None


# L1 概念桥接
PARTIAL_TAIL = 2   # 精确命中之后额外附带的「部分匹配」概念条数上限


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
    return partial


# ------------------------------------------------------------ L3: 全库回退
def fallback(q, limit):
    ql = norm(q)
    out = {"theories": [], "scales": [], "methods": []}
    for n in load_index("t", T_IDX):
        if ql in norm(n.get("name_zh")) or ql in norm(n.get("name_en")) or ql in norm(n.get("construct_id")):
            out["theories"].append({"id": n["theory_id"], "zh": n.get("name_zh", ""),
                                    "en": n.get("name_en", ""), "by": ["fallback"]})
    for n in load_index("s", S_IDX):
        if ql in norm(n.get("variable_zh")) or ql in norm(n.get("variable_en")) or ql in norm(n.get("construct_id")):
            out["scales"].append({"id": n["scale_id"], "zh": n.get("variable_zh", ""),
                                  "en": n.get("variable_en", ""), "by": ["fallback"]})
    for n in load_index("r", R_IDX):
        if ql in norm(n.get("title")) or ql in norm(n.get("use_condition")):
            out["methods"].append({"id": n["method_no"], "zh": n.get("title", ""),
                                   "stage": n.get("stage", ""), "file": n.get("file", ""), "by": ["fallback"]})
    for k in out:
        out[k] = out[k][:limit]
    return out


# ---------------------------------------------------------------- 富化
def enrich(b):
    """为桥接结果补充元信息（维度题数、四段覆盖标记、脚本路径）"""
    tmeta = {n["theory_id"]: n for n in load_index("t", T_IDX)}
    smeta = {n["scale_id"]: n for n in load_index("s", S_IDX)}
    for t in b.get("theories", []):
        m = tmeta.get(t["id"], {})
        t.update(n_refs=m.get("n_refs", 0), has_what=m.get("has_what", False),
                 has_processes=m.get("has_processes", False),
                 has_struct=m.get("has_struct", False), has_app=m.get("has_app", False),
                 note=m.get("note", ""),
                 path=_display_path(T_DIR, "theory-library/knowledge/theories", t["id"]))
    for s in b.get("scales", []):
        m = smeta.get(s["id"], {})
        s.update(n_dims=m.get("n_dims", 0), n_items=m.get("n_items", 0),
                 status=m.get("status", ""),
                 path=_display_path(S_DIR, "scale-library/knowledge/scales", s["id"]))
    for mth in b.get("methods", []):
        rel = mth.get("file") or ""
        # 同 by_id：索引 file 字段须做包含性校验，越界视为文件缺失
        fp = _safe_join(R_ROOT, rel)
        mth["display_path"] = lib_path("r-analysis", rel) if rel else ""
        mth.update(exists=bool(fp) and os.path.exists(fp))
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
    - theory_id / scale_id 来自桥接与索引（用户可编辑），拼出的路径须经 _safe_join
      包含性校验，越界即视为记录缺失（无正文），不得读取包外文件。
    - 记录级 JSON 损坏只跳过该条并告警（stderr，仅 basename），不让一条坏记录
      带走整批结果；顶层索引仍是致命错误。
    - 存储形态：优先读合并存储 entities.json（本包当前形态），缺失时回退逐文件读取；
      与 library_query._full_record 同一约定。
    """
    for t in b.get("theories", [])[:limit]:
        r = _store_lookup(T_DIR, t.get("id", ""))
        if r is None:
            fp = _safe_join(T_DIR, t.get("id", ""), ".json")
            if fp and os.path.exists(fp):
                r = load_json(fp, fatal=False)
        if r is None:
            continue
        # 四段正文完整保留（不再静默截断）；是否截断交由展示层 _clip 显式标注
        t["what"] = r.get("what") or ""
        t["processes"] = r.get("processes") or ""
        t["structure"] = r.get("structure") or ""
        t["application"] = r.get("application") or ""
        t["references"] = r.get("references") or ""
    for s in b.get("scales", [])[:limit]:
        r = _store_lookup(S_DIR, s.get("id", ""))
        if r is None:
            fp = _safe_join(S_DIR, s.get("id", ""), ".json")
            if fp and os.path.exists(fp):
                r = load_json(fp, fatal=False)
        if r is None:
            continue
        s["dimensions"] = r.get("dimensions", [])
        s["items"] = r.get("items", [])
        s["reference_used"] = r.get("reference_used", "")
    for mth in b.get("methods", [])[:limit]:
        fp = _safe_join(R_ROOT, mth.get("file", ""))
        if fp and os.path.exists(fp):
            with open(fp, encoding="utf-8", errors="replace") as f:
                mth["script_head"] = "".join(f.readlines()[:12])
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
        L.append(f"教材锚点: 第{ch[2:].lstrip('0')}章 {b.get('chapter_title','')}"
                 f"  → {ref_path(ch + '.md')}"
                 f"  引用格式【出处：D1,§X.Y】")
    else:
        L.append("教材锚点: 本教材未覆盖该概念")
    L.append("")
    for kind, key in (("理论", "theories"), ("量表", "scales"), ("R 方法", "methods")):
        items = b.get(key, [])
        # 计数用实际展示条数，避免 --limit 截断后「标称 N 条、列出 M 条」的自相矛盾
        shown = items[:limit]
        L.append(f"【{kind} {len(shown)}】")
        if not items:
            L.append("  （本概念在库中无匹配条目）")
        for it in shown:
            if key == "theories":
                L.append(f"  {it['id']}  {it['zh']} / {it['en']}")
                L.append(f"       段落[{_seg_state(it)}]  文献 {it.get('n_refs',0)} 篇  → {it['path']}")
                if "内源补足" in (it.get("note") or ""):
                    L.append("       ⚠️ [内源补足警示] 本条正文部分由内部教材 D1 自动补足，"
                             "非原始同行评议文献，补足内容不得作为经核验的权威引用。")
                if full:
                    # 四段正文 + 参考文献：read_full() 已全部载入，若只打印 what，
                    # 使 processes / structure / application / references 被静默丢弃。
                    # 空段按既定口径显式写出「（原文未覆盖）」，不得留白。
                    for seg, mark in (("what", "【内容】"), ("processes", "【作用机制】"),
                                      ("structure", "【结构】"), ("application", "【应用】"),
                                      ("references", "【文献】")):
                        txt = it.get(seg) or ""
                        if not txt.strip():
                            L.append(f"       {mark}（原文未覆盖）")
                            continue
                        L.append(f"       {_seg_head(txt, mark)}{_clip(txt, 220, it['path'])}")
            elif key == "scales":
                L.append(f"  {it['id']}  {it['zh']} / {it['en']}")
                L.append(f"       {it.get('n_dims',0)} 维度 / {it.get('n_items',0)} 题  状态 {it.get('status','')}  → {it['path']}")
                if full:
                    for d in it.get("dimensions", [])[:6]:
                        L.append(f"       维度: {d.get('name_zh','')} ({d.get('item_count',0)}题, {d.get('scoring','')})")
                    for itx in it.get("items", [])[:5]:
                        rv = " [反向]" if itx.get("reverse") else ""
                        L.append(f"         {itx.get('no','')}. {itx.get('text','')}{rv}")
                    if it.get("reference_used"):
                        L.append(f"       取用文献: {_clip(it['reference_used'], 110, it['path'])}")
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
    bridge = load_json(BRIDGE)["concepts"]

    # L2
    hit = by_id(args.query)
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
        if args.json:
            out = [read_full(enrich(h), args.limit) if args.full else enrich(h)
                   for h in hits[:CONCEPT_CAP]]
            # 显式给出命中总数与展示数，消费方才能察觉被截断（原先只拿到 3 条无从判断）
            print(json.dumps({"mode": "concept", "query": args.query,
                              "total_matched": len(hits), "shown": shown_n,
                              "concepts": out}, ensure_ascii=False, indent=2))
            return 0
        blocks = []
        for h in hits[:CONCEPT_CAP]:
            b = enrich(dict(h))
            if args.full:
                b = read_full(b, args.limit)
            blocks.append(fmt(b, args.query, args.full, args.limit))
        print(PATH_HINT)
        # 消除静默截断：展示上限是上下文预算的有意取舍，但命中总数必须写明，
        # 否则「查 e 命中 106 个概念却只看到 3 个」会被误读为全部结果。
        if len(hits) > CONCEPT_CAP:
            print(TRUNC_HINT.format(total=len(hits), shown=shown_n))
        print(("─" * 70 + "\n").join(blocks))
        return 0

    # L3
    fb = fallback(args.query, args.limit)
    total = sum(len(v) for v in fb.values())
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
        print(json.dumps({"mode": "fallback", "query": args.query, **fb}, ensure_ascii=False, indent=2))
        return 0
    print(f"=== 概念词表未收录「{_shorten(args.query)}」，已回退全库检索（命中 {total} 条）===")
    print("提示：若该概念高频使用，可在 knowledge/_concept_index.json 与 knowledge/_bridge.json 的概念词表中补录。\n")
    block = enrich({"concept_id": "fallback:" + args.query, "label_zh": args.query,
                    "zh": [args.query], "en": [args.query], "note": "全库回退检索结果", **fb})
    if args.full:
        block = read_full(block, args.limit)
    print(PATH_HINT)
    print(fmt(block, args.query, args.full, args.limit))
    return 0


if __name__ == "__main__":
    sys.exit(main())
