#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_institution_network.py —— 机构共现网络（含中英文同义归并）

用法:
    python3 build_institution_network.py <refs.json> [--min-edge 1] [--min-df 1]
        [--top N] [--name-mode first|full] [--keep-isolated] [--seed 42]
        [--no-layout] [--out DIR]
        [--thesaurus <csv>]... [--no-thesaurus]

## 布局 / 着色 / 孤立剔除（2026-10 修复「一个色 / 都排在一起」）

报告端机构画布原先**没有任何坐标**、节点填充色是单一常量，报告 JS 只能把节点排成
规则网格，可读性差。本脚本现与
`build_author_network.py` 完全同构地产出：

    · pos_encoded / edges_encoded —— base64(int16) 内联坐标 / 边；
    · nodes[i].x / nodes[i].y   —— 明文坐标（pos_encoded 缺失时兜底）；
    · nodes[i].component / component_size —— 连通分量（报告端按群着色）。

布局、编码与社群发现由共享模块 `_netutil.py` 提供（此前在作者 / 机构 / 引文三脚本
逐字节复制，易漂移；现统一收敛，三类网络行为完全一致）。布局用纯标准库 FR
（本环境无 numpy），固定 `--seed`（默认 42）→ 同输入同输出；`_netutil.fr_layout`
含 v1.0.0 的"重叠消除"松弛。

**默认剔除孤立机构**（度为 0，本库内不与其他机构共现）：无关系信息，画进网络只是
噪音；剔除数写进 stats.isolated_dropped，不静默删除，`--keep-isolated` 可保留。
[!]  归一 / 归并口径（同义词表、通用归一、merge 审计）**完全不受此影响**，只是把
"已入选但没有任何边"的节点从输出里拿掉。

为什么单独一个脚本（而不是给 build_network.py 加维度参数）:
    build_network.py 的节点是**关键词**，其建网逻辑（噪声词表、hybrid 语料、
    主题着色、CiteSpace 年轮）与机构场景无一复用；而机构共现只有"篇内两两配对"
    一条规则。硬塞进 build_network.py 会让那个已被 run_checks 行为断言锁定的
    脚本变复杂、回归风险上升。独立脚本把回归面收敛在新增文件内，代价是少量
    重复的 argparse/写盘样板——远比污染既有脚本划算。

输入契约（唯一来源：import_sources.py 模块头「机构与被引字段」）:
    refs.json 的每条记录可含两个**可选**字段
      · affiliations: ["<机构原始串>", ...]   本篇机构（可多条）
      · references:   ["<被引原始条目>", ...]  本篇引用的参考文献（本脚本不用）
    缺该键 ⇔ 该篇无机构。字段由 import_sources.py 在导入时保留。

口径（引用规模数字时必须连带标注，缺一不予采信）:
    node         = 机构（归一名）
    edge         = 同篇文献内两机构共现（篇内去重，两两计一次）
    normalize    = 通用归一 + 同义词表，见下
    min_edge     = 1        （默认保留任意出现过的机构对）
    min_df       = 1
    org_dedupe   = per-doc

归一流水线（顺序固定，前六步是"通用归一"，第七步才查表）:
    1) NFKC —— 统一全角/半角与兼容字符；
    2) 去 WoS C1 的 "[作者] " 前缀；
    3) 压空白、剥两端标点；
    4) name_mode=first 时按逗号切片，**跳过开头的院系/部门片段**再取第一个非院系
       片段（天然去掉 ", 城市 邮编, 国家" 与前置院系）；
    5) 缩写展开 Univ→University / Acad→Academy / Inst→Institute / Coll→College /
       Sci→Science / Technol→Technology（让 "Univ" 与 "University" 同键）；
    6) 去尾部邮编；
    7) 查同义词表（references/org_aliases.csv，可 --thesaurus 追加、--no-thesaurus
       关闭）：命中用表中规范名，否则用第 6 步结果。key = 规范名 casefold。

为什么要分"通用归一"和"同义词表"两层:
    只靠表无法穷尽（Univ/University/大小写/邮编/院系缀组合爆炸）；只靠通用规则
    又无法跨语言（"清华大学" 与 "Tsinghua Univ" 无公共子串）。两者叠加才稳：
    通用归一先把机械变形收敛，同义词表只负责"确知是同一所的跨语言/习惯写法"。
    规范名的选择稳定可复现——命中表用表里的规范名，否则用通用归一结果。

合并的可审计性（回答"哪些写法被并到一起了"）:
    · 节点 variants（int，类型不变） = 合并进来的**原始写法种数**；
    · 节点 variants_detail（新增）  = [{"raw": 原始写法, "count": 出现次数}, ...]；
    · stats.merge                   = 本次合并了多少组、节点数变化、表命中数；
    · org_alias_merges.csv          = 原始写法 → 规范名 → 次数（供人工复核）。

疑似同源候选（只建议、不自动合并）: org_alias_candidates.csv
    同义词表不可能穷尽，故另出候选表帮人工找漏。只用**可靠信号**：
      · 信号 B「已知片段对应」（**立候选的必要条件**）：内置高置信度中↔英片段
        表（城市/专名/学科词），命中显著专名 ≥1 或任意片段 ≥2 才触发；
      · 信号 A「同篇中英共现」（**加强证据，不单独立候选**）：同一篇文献里既有
        中文节点又有英文节点。
    **故意不单独使用同篇共现**：一篇多机构论文里"中文单位 + 无关英文单位"
      同篇很常见（如清华与某英文名的海外机构），仅凭共现会大量误报——
      这正是"瞎猜"。故必须有词面片段线索才立候选，共现只用来加证。
    **故意不用**纯字符串相似度 / 编辑距离 / token Jaccard —— 那会把
    "Beijing Univ" 与 "Beijing Normal Univ" 误判同源，正是要避免的。
    候选一律标注"建议人工确认"，绝不写回网络。

输出（schema 与 build_network.py 的 network.json 严格对齐；仅新增变体明细字段）:
    <out>/institution_network.json   {nodes:[{id,df,degree,...}], edges:[...], stats:{...}}
    <out>/institution_network_nodes.csv
    <out>/org_alias_merges.csv       原始写法→规范名→次数
    <out>/org_alias_candidates.csv   疑似同源候选（待人工确认）

空态（负向证据）: 若 0 篇含 affiliations，**不静默输出空网络** ——
    stderr 打印明确中文提示，并落盘带 empty_state / notice 的 JSON，退出码 0
    （降级而非失败，与 references/failure_paths.md「可选能力失败不阻塞主流程」一致）。

[!]  仍存在的已知限制（如实标注，不假装完成）:
      · 同义词表**覆盖不全**：只收录高置信度机构，冷门/地方院校可能仍分列；
        表尾预留"增补区"，并用 org_alias_candidates.csv 辅助人工补全。
      · WoS 缩写变形多样：`Sci & Technol` 与 `of Science and Technology` 归一后
        仍是两个字符串（无 "of/and" 补全），故表里对同一校并列多种写法。
      · 候选信号是启发式，会有漏报（跨语言且无共现、片段表未覆盖时发现不了），
        也可能有误报，故只作建议。

退出码: 0 成功（含空态降级）/ 1 输入不可用或同义词表缺失 / 2 输入非 refs.json
        / 5 未预期缺陷
"""
from __future__ import annotations

import argparse
import csv
import itertools
import json
import re
import sys
import time
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# 布局 / 编码 / 社群：共享实现（见 _netutil.py —— 收敛此前三处逐字节复制）
from _netutil import (  # noqa: E402
    layout as _layout, communities as _communities,
    encode_pos, encode_edges,
)
from lit_core import EXIT, EnlError, emit, esc_csv_cell  # noqa: E402
from import_sources import _looks_like_org  # noqa: E402

_REFS_FORMAT = "academic-lit-analysis/refs@1"
_BRACKET = re.compile(r"^\s*\[[^\]]*\]\s*")          # WoS C1 的 "[作者, 作者] " 前缀
_ZIP = re.compile(r"\s+\d{4,6}(?:-\d{3,4})?\s*$")    # 尾部邮编（可带 -123 扩位）

# ── 人名过滤（v1.0.0「机构网络里夹杂姓名」） ──
# 来源：CNKI/WoS 导入时部分机构串实为作者名（"余疆" / "Zhang S"）。
# 保守策略：**只剔除「明显像人名」的候选**——绝不用「不像机构就删」的
# 宽松规则，否则 IBM / 华为 这类无机构后缀的真实机构会被误删。
# 被剔除条目计入 stats.person_name_filtered（含示例），可审计、不静默。
_CJK_CHAR = re.compile(r"[\u4e00-\u9fff]")
_INITIAL_TOK = re.compile(r"^[A-Za-z]\.?$")
_PERSON_HINTS = ("大学", "学院", "研究所", "医院", "公司", "实验室",
                 "univ", "coll", "institut", "hospital", "academ",
                 "school", "department", "center", "centre", "corp", "ltd")


def _person_like(name: str) -> bool:
    """候选机构串是否「明显像人名」。

    判定（满足其一且不含任何机构提示词）：
      · 纯中文且 ≤4 个汉字（中文姓名几乎都在 2–4 字，如「余疆」「张三丰」）；
      · 英文含首字母缩写 token（"Zhang S" / "Smith J. M."）；
      · 英文 ≤2 个 token 且全部首字母大写、无机构词（"Jing Zhang"）。
    """
    n = unicodedata.normalize("NFKC", name or "").strip()
    if not n or len(_CJK_CHAR.findall(n)) == 0:
        low = n.lower()
        if any(k in low for k in _PERSON_HINTS):
            return False
        toks = n.split()
        if not toks or len(toks) > 4:
            return False
        if sum(1 for t in toks if _INITIAL_TOK.match(t)) >= 1:
            return True
        if len(toks) == 1:
            # 全大写缩写（IBM / ACM / MIT）通常是机构，不是人名 → 保留
            t = toks[0]
            return not (t.isupper() and len(t) >= 2)
        return (len(toks) <= 2
                and all(t[:1].isupper() for t in toks if t[:1].isalpha()))
    # 含中文：整串机构提示词 → 不是人名
    low = n.lower()
    if any(k in low for k in _PERSON_HINTS):
        return False
    return len(_CJK_CHAR.findall(n)) <= 4 and len(n) <= 12

# 院系/部门片段前缀：name_mode=first 时跳过"院系在前、机构在后"的写法。
_DEPT_PREFIX = re.compile(
    r"^(?:dept|department|school|sch|faculty|college|coll|division|"
    r"center|centre|laboratory|lab|institute|inst)\b", re.I)

# 缩写展开表。只展开**明确的机构用缩写**，且已确认不会误伤全称
# （\bUniv\b 匹配不到 University 内部的 Univ —— 词边界挡住了）。
_ABBR = [
    (re.compile(r"\bUniv\.?\b", re.I), "University"),
    (re.compile(r"\bAcad\.?\b", re.I), "Academy"),
    (re.compile(r"\bInst\.?\b", re.I), "Institute"),
    (re.compile(r"\bColl\.?\b", re.I), "College"),
    (re.compile(r"\bSci\.?\b", re.I), "Science"),
    (re.compile(r"\bTechnol\.?\b", re.I), "Technology"),
]

# 中日韩字符：用于把节点分成"中文侧"与"英文侧"，候选信号只在跨侧判断。
_CJK = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uac00-\ud7af]")

# 默认同义词表：**相对脚本定位**（scripts/../references/org_aliases.csv），
# 保证换机器、换工作目录也能找到，不依赖 cwd。
_DEFAULT_THESAURUS = (Path(__file__).resolve().parent.parent
                      / "references" / "org_aliases.csv")


def load_payload(path: Path) -> dict:
    """读取 refs.json 原始载荷。**不走 refs_from_json** —— 那是 lit_core 的
    接口，会把 affiliations/references 当作未知字段丢弃（不得改动 lit_core）。
    故这里直接读原始 JSON，保留扩展字段。"""
    if path.suffix.lower() != ".json":
        raise EnlError(2, f"本能力依赖 refs.json 的 affiliations 字段；"
                          f"请先用 import_sources.py 把 {path.name} 归一化为 refs.json")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise EnlError(2, f"不是合法 JSON：{e}")
    if payload.get("format") != _REFS_FORMAT:
        raise EnlError(2, f"不是本工具 refs.json 产物（format={payload.get('format')!r}）")
    return payload


def normalize_org(raw: str, name_mode: str = "first") -> str | None:
    """**通用归一**（不含同义词表）。返回归一后的展示串；无效时返回 None。

    为什么按这个顺序（每一步都在消除一类已知变形）：
      1) NFKC：全角/半角（ＡＢＣ / ＡＣＡＤ）与兼容字符统一；
      2) 去 [作者] 前缀：WoS 的 C1 会把作者名塞进方括号，不剥它会污染机构名；
      3) 压空白、剥两端标点：消除排版噪声；
      4) name_mode=first：按逗号切片并**跳过开头院系片段**再取第一段 —— 这是
         去"城市/邮编/国家"与"前置院系"最稳的做法（不靠穷举正则）；
      5) 缩写展开：让 "Tsinghua Univ" 与 "Tsinghua University" 归一到同键；
      6) 去尾部邮编：兜住 name_mode=full 等未切片时残留的邮编。
    """
    s = unicodedata.normalize("NFKC", str(raw or ""))
    s = _BRACKET.sub("", s)                       # 去 WoS "[作者1; 作者2]" 前缀
    s = re.sub(r"\s+", " ", s).strip().strip(".,;|").strip()
    if not s:
        return None
    if name_mode == "first":
        # 主机构名 = 跳过开头连续院系片段后的第一段；至少保留最后一段兜底。
        segs = [x.strip() for x in s.split(",") if x.strip()]
        idx = 0
        while idx < len(segs) - 1 and _DEPT_PREFIX.match(segs[idx]):
            idx += 1
        s = segs[idx] if segs else ""
    if not s:
        return None
    for pat, rep in _ABBR:
        s = pat.sub(rep, s)
    s = _ZIP.sub("", s).strip().strip(".,;").strip()
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) < 2:
        return None
    return s


def raw_form(raw: str) -> str | None:
    """变体记录用的「原始写法」。

    为什么这样定义：只做 NFKC、去 [作者] 前缀、压空白，**保留院系/城市/国家等
    原样信息**（那才是"这家机构的原始写法长什么样"）。做太多清洗会让 variants
    失真，看不出到底合并了哪些"表面不同"的写法。
    """
    s = unicodedata.normalize("NFKC", str(raw or ""))
    s = _BRACKET.sub("", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s or None


def load_thesaurus(paths: list[Path]) -> tuple[dict[str, str], list[str], int]:
    """加载同义词表，返回 (alias_key→canonical, 已加载文件路径, 条目数)。

    键 = 别名经通用归一后 casefold；值 = 规范名经通用归一后的串。
    同时把规范名自身也注册为键（canonical→canonical），保证规范名以原文出现时
    也稳定命中，避免"表里有这个学校但这篇恰好用的是规范名 → 没合并"的漏洞。
    冲突（同一别名指向不同规范名）时**先出现者胜**并打 [warn]，让合并可审计。
    """
    table: dict[str, str] = {}
    files: list[str] = []
    entries = 0
    for p in paths:
        try:
            text = p.read_text(encoding="utf-8-sig")
        except FileNotFoundError:
            raise EnlError(1, f"同义词表不存在：{p}")
        files.append(str(p))
        for ln, line in enumerate(text.splitlines(), 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "," not in line:
                print(f"[warn] 同义词表 {p.name}:{ln} 缺逗号，已跳过：{line!r}",
                      file=sys.stderr)
                continue
            alias, canon = (x.strip() for x in line.split(",", 1))
            nb = normalize_org(alias)
            nc = normalize_org(canon)
            if not nb or not nc:
                print(f"[warn] 同义词表 {p.name}:{ln} 归一后为空，已跳过：{line!r}",
                      file=sys.stderr)
                continue
            entries += 1
            for key, val in ((nb.casefold(), nc), (nc.casefold(), nc)):
                prev = table.get(key)
                if prev is None:
                    table[key] = val
                elif prev != val:
                    print(f"[warn] 同义词表冲突：{key!r} 既→{prev!r} 又→{val!r}"
                          f"（{p.name}:{ln}），保留先出现者", file=sys.stderr)
    return table, files, entries


def build(refs: list, min_edge: int = 1, min_df: int = 1,
          name_mode: str = "first", top: int | None = None,
          thesaurus: dict | None = None, thesaurus_files: list | None = None,
          thesaurus_entries: int = 0, keep_isolated: bool = False):
    """构建机构共现网络。返回 (nodes, edges, stats, merges, candidates)。

    merges     = [(原始写法, 规范名, 次数)]，仅含发生过归一/合并的映射；
    candidates = [dict]，疑似同源待人工确认的建议（见 discover_candidates）。

    默认剔除度为 0 的孤立机构（本库内不与其他机构共现）；`keep_isolated=True`
    可保留。每个节点带 `component` / `component_size`（连通分量 id 与规模，
    按规模降序稳定编号，最大群 id=0）。
    """
    t0 = time.time()
    thesaurus = thesaurus or {}
    docs_total = len(refs)
    docs_with_org = 0

    raw_count: dict[str, Counter] = defaultdict(Counter)   # key → 原始写法计数
    canon_count: dict[str, Counter] = defaultdict(Counter)  # key → 规范名计数
    doc_keys: list[list[str]] = []                          # 每篇的机构 key 列表
    keys_before: set[str] = set()      # 仅通用归一（不查表）时的 key，用于算节点数变化
    remapped: set[str] = set()         # 被同义词表改写过规范名的 key
    thesaurus_hits = 0                 # 命中同义词表的原始条目数
    raw_entries = 0
    person_filtered = 0                    # 被判为人名而剔除的条目数（可审计）
    person_examples: list[str] = []

    for r in refs:
        raw_list = r.get("affiliations") or []
        if raw_list:
            docs_with_org += 1
        keys = []
        for raw in raw_list:
            raw_entries += 1
            base = normalize_org(raw, name_mode)
            if not base:
                continue
            # 人名过滤：明显像人名（且不像机构）的候选不进网络，计数留痕
            if _person_like(base) and not _looks_like_org(base, []):
                person_filtered += 1
                if len(person_examples) < 8:
                    person_examples.append(base)
                continue
            keys_before.add(base.casefold())
            canon = thesaurus.get(base.casefold(), base)
            key = canon.casefold()
            if canon != base:
                remapped.add(key)
                thesaurus_hits += 1
            canon_count[key][canon] += 1
            rf = raw_form(raw)
            if rf:
                raw_count[key][rf] += 1
            keys.append(key)
        doc_keys.append(keys)

    # 每个 key 的展示名：规范名频次最高者，并列取字典序小者 → 跨进程稳定
    display: dict[str, str] = {
        key: sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
        for key, c in canon_count.items()
    }

    # 文档频次 df（篇内去重）
    df = Counter()
    for keys in doc_keys:
        for k in set(keys):
            df[k] += 1

    # 边：篇内两两共现（先篇内去重再组合，避免同一对在同一篇里被计多次）
    edge_count = Counter()
    for keys in doc_keys:
        for a, b in itertools.combinations(sorted(set(keys)), 2):
            edge_count[(a, b)] += 1

    edges_k = [(a, b, c) for (a, b), c in edge_count.items() if c >= min_edge]

    # 节点裁剪：min_df + top（度数优先，tie 用 df、展示名保证全序）
    deg = Counter()
    for a, b, c in edges_k:
        deg[a] += 1
        deg[b] += 1
    keep = {k for k, n in df.items() if n >= min_df}
    if top and len(keep) > top:
        keep = set(sorted(keep, key=lambda k: (-deg.get(k, 0), -df[k], display[k]))[:top])
    edges_k = [(a, b, c) for (a, b, c) in edges_k if a in keep and b in keep]

    # 裁剪后重算度数/权重，保证 nodes.degree 与最终 edges 一致
    deg = Counter()
    wsum = Counter()
    for a, b, c in edges_k:
        deg[a] += 1
        deg[b] += 1
        wsum[a] += c
        wsum[b] += c

    edges = [{"source": display[a], "target": display[b], "weight": c}
             for a, b, c in edges_k]
    edges.sort(key=lambda e: (-e["weight"], e["source"], e["target"]))

    # ── 孤立节点（度为 0）默认剔除 ──
    # 为什么：度为 0 的机构在本库内不与其他任何机构共现 —— 没有关系信息，画进网络
    # 只是噪音（与作者/引文网络同一策略）。**归一 / 归并 / 阈值口径完全不动**，只是把
    # "已入选但没有任何边"的节点从**输出**里拿掉；剔除数写进 stats，不静默删除。
    # [!]  判定用**内部键**（casefold 串，edges_k 的键空间），不是展示名 display[k] ——
    #      两者在发生过同义词表归一时不同（按展示名取度会 KeyError）。
    deg_final = Counter()
    for a, b, _c in edges_k:
        deg_final[a] += 1
        deg_final[b] += 1
    nodes_before = len(keep)                     # 剔除孤立前的节点数（对账用）
    isolated_keys = {k for k in keep if deg_final.get(k, 0) == 0}
    out_keys = set(keep) if keep_isolated else (keep - isolated_keys)

    # ── 连通分量（并查集）+ 稳定编号 ──
    # 编号规则：分量**规模降序**；规模相同按**最小成员名（展示名）升序** → 同输入必然
    # 同输出。**必须按展示名排**：报告端 JS 无 component 字段时用并查集兜底，其成员名
    # 就是节点 id = display，两处编号规则必须一致，否则数据侧/兜底侧颜色会错位。
    # id=0 即最大群，报告端据此让大群优先拿到区分度最高的颜色（对调色板取模）。
    parent = {k: k for k in out_keys}

    def _find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b, _c in edges_k:
        if a in parent and b in parent:
            ra, rb = _find(a), _find(b)
            if ra != rb:
                parent[ra] = rb
    _by_root: dict = defaultdict(list)
    for k in out_keys:
        _by_root[_find(k)].append(k)
    ordered_groups = sorted((sorted(display[k] for k in v) for v in _by_root.values()),
                            key=lambda g: (-len(g), g[0]))
    comp_id: dict[str, int] = {}
    comp_size: dict[str, int] = {}
    for _i, _g in enumerate(ordered_groups):
        for _nm in _g:
            comp_id[_nm] = _i
            comp_size[_nm] = len(_g)

    # ── 社群发现（加权标签传播）+ 稳定编号 ──
    # 与 component 并存、不替代：component 回答"能否连通"，community 回答"关系紧不紧"。
    # 渲染端**优先**用 community 上色；component 字段保留（作者网络语义 + 旧产物/下游依赖）。
    # 编号规则与上面 component **完全一致**：按**展示名**排序（规模降序、同规模最小名升序），
    # 因为报告端 JS 无 community 字段时会用并查集兜底自算，其成员名即节点 id=display，
    # 两处编号规则必须一致，否则数据侧/兜底侧颜色会错位。
    _lab, _mod = _communities(out_keys, edges_k)
    _cgrp: dict = defaultdict(list)
    for _k in out_keys:
        _cgrp[_lab[_k]].append(display[_k])
    _cordered = sorted((sorted(v) for v in _cgrp.values()),
                       key=lambda g: (-len(g), g[0]))
    comm_id: dict[str, int] = {}
    comm_size: dict[str, int] = {}
    for _ci, _g in enumerate(_cordered):
        for _nm in _g:
            comm_id[_nm] = _ci
            comm_size[_nm] = len(_g)

    nodes = [{
        "id": display[k], "label": display[k],
        "df": df[k], "degree": deg.get(k, 0), "weight": wsum.get(k, 0),
        # variants 保持 int（schema 类型不变）：合并了几种**原始写法**。
        "variants": len(raw_count[k]),
        # variants_detail 是合并明细：如实列出被并进来的每种原始写法及次数。
        "variants_detail": [
            {"raw": rw, "count": n}
            for rw, n in sorted(raw_count[k].items(), key=lambda kv: (-kv[1], kv[0]))
        ],
        "component": comp_id[display[k]],
        "component_size": comp_size[display[k]],
        # 社群（着色维度，渲染端优先用它上色；component 仍保留）
        "community": comm_id[display[k]],
        "community_size": comm_size[display[k]],
    } for k in sorted(out_keys, key=lambda k: (-deg.get(k, 0), -df[k], display[k]))]

    # ── 合并审计：原始写法 → 规范名 → 次数（只列真正发生归一的映射）──
    merges: list[tuple[str, str, int]] = []
    for k, c in raw_count.items():
        canon = display[k]
        for rw, n in c.items():
            if rw.casefold() != canon.casefold():
                merges.append((rw, canon, n))
    merges.sort(key=lambda x: (-x[2], x[0]))

    # ── 疑似同源候选（只在未合并的跨语言节点对之间找）──
    candidates = discover_candidates(refs, doc_keys, display)

    merged_groups = sum(1 for k, c in raw_count.items()
                        if len(c) > 1 or k in remapped)
    merged_examples = [
        {"canonical": display[k],
         "variants": [rw for rw, _ in sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))]}
        for k, c in sorted(raw_count.items(), key=lambda kv: -len(kv[1]))
        if len(c) > 1
    ][:5]

    n_out = len(nodes)
    largest = max((len(g) for g in ordered_groups), default=0)
    isolated_out = sum(1 for n in nodes if n["degree"] == 0)
    density = (2.0 * len(edges) / (n_out * (n_out - 1))) if n_out > 1 else 0.0

    stats = {
        "nodes": n_out, "edges": len(edges),
        "nodes_before_isolated_drop": nodes_before,   # 剔除孤立前的节点数（对账用）
        "components": len(ordered_groups),
        "largest_component": largest,
        "largest_component_pct": round(100.0 * largest / n_out, 1) if n_out else 0.0,
        "isolated": isolated_out,                     # 输出图里的孤立节点数（默认 0）
        "isolated_found": len(isolated_keys),          # 阈值筛选后发现的孤立数
        "isolated_dropped": (0 if keep_isolated else len(isolated_keys)),
        "keep_isolated": keep_isolated,
        "max_degree": max((n["degree"] for n in nodes), default=0),
        "max_weight": max((e["weight"] for e in edges), default=0),
        "density": round(density, 6),
        # 社群发现（着色维度）：社群数 / 最大社群规模与占比 / 模块度。占比是关键 ——
        # 若 >80% 说明图本身社群结构单一，颜色仍会偏单色（如实报告，不粉饰）。
        "communities": len(_cordered),
        "largest_community": max((len(g) for g in _cordered), default=0),
        "largest_community_pct": (round(100.0 * max((len(g) for g in _cordered), default=0) / n_out, 1)
                                  if n_out else 0.0),
        "modularity": _mod,
        "community_algorithm": "label_propagation(weighted, deterministic-order)",
        "params": {
            "node_df": min_df, "min_edge_count": min_edge,
            "df_mode": "doc", "org_dedupe": "per-doc",
            "normalize": ("通用归一(NFKC+去[作者]前缀+去院系前缀+缩写展开)"
                          "+去尾部邮编+casefold+同义词表"),
            "name_mode": name_mode,
            "keep_isolated": keep_isolated,
            "thesaurus": list(thesaurus_files or []),
        },
        "coverage": {
            "docs_total": docs_total,
            "docs_with_affiliations": docs_with_org,
            "affiliation_pct": round(docs_with_org / docs_total * 100, 1) if docs_total else 0.0,
            "raw_affiliation_entries": raw_entries,
            "merged_org_keys": len(df),
        },
        # 人名过滤审计：机构串里混入的作者名被剔除的数量与示例（不静默）
        "person_name_filter": {
            "filtered": person_filtered,
            "examples": person_examples,
        },
        # 合并只作用于"节点层"：文档级覆盖率（docs_with_affiliations/docs_total）
        # 按定义不变，故不放进 coverage，而是把"节点数变化"如实报告在 merge 里。
        "merge": {
            "thesaurus_files": list(thesaurus_files or []),
            "thesaurus_entries": thesaurus_entries,
            "thesaurus_hits": thesaurus_hits,
            "nodes_before_merge": len(keys_before),
            "nodes_after_merge": len(df),
            "merged_node_reduction": len(keys_before) - len(df),
            "thesaurus_mapped_keys": len(remapped),
            "merged_groups": merged_groups,
            "merged_examples": merged_examples,
        },
        "elapsed": round(time.time() - t0, 3),
    }
    return nodes, edges, stats, merges, candidates


# ── 候选发现 ──────────────────────────────────────────────────────────────
# 中↔英片段表：只收高置信度的城市/专名/学科词。**仅用于"建议"**，绝不自动合并。
# 为什么用这张表而非字符串相似度：相似度会误判 "Beijing Univ" 与
# "Beijing Normal Univ" 同源；片段表把"什么算同一个机构线索"限定在可解释的
# 语义对应上，误报可控且证据可读。
_FRAGMENTS = [
    ("北京", ["beijing", "peking"]), ("上海", ["shanghai"]), ("天津", ["tianjin"]),
    ("重庆", ["chongqing"]), ("南京", ["nanjing"]), ("杭州", ["hangzhou"]),
    ("广州", ["guangzhou"]), ("深圳", ["shenzhen"]), ("武汉", ["wuhan"]),
    ("西安", ["xian", "xi an"]), ("成都", ["chengdu"]), ("哈尔滨", ["harbin"]),
    ("厦门", ["xiamen"]), ("济南", ["jinan"]), ("长沙", ["changsha"]),
    ("青岛", ["qingdao"]), ("大连", ["dalian"]), ("苏州", ["suzhou"]),
    ("浙江", ["zhejiang"]), ("江苏", ["jiangsu"]), ("广东", ["guangdong"]),
    ("四川", ["sichuan"]), ("山东", ["shandong"]), ("湖北", ["hubei"]),
    ("湖南", ["hunan"]), ("陕西", ["shaanxi"]), ("福建", ["fujian"]),
    ("香港", ["hongkong", "hong kong"]),
    ("清华", ["tsinghua"]), ("北大", ["peking"]), ("复旦", ["fudan"]),
    ("南开", ["nankai"]), ("同济", ["tongji"]),
    ("中山", ["sunyatsen", "sun yat sen", "zhongshan"]),
    ("师范", ["normal"]), ("交通", ["jiaotong", "jiao tong"]),
    ("理工", ["inst", "institute", "technol", "technology", "tech", "polytechnic"]),
    ("科技", ["sci", "science", "technol", "technology", "tech"]),
    ("医科", ["medical", "medicine"]), ("财经", ["finance", "economics", "economic"]),
    ("农业", ["agricultural", "agriculture"]), ("外国语", ["foreign", "studies"]),
    ("矿业", ["mining"]), ("石油", ["petroleum"]),
    ("地质", ["geoscience", "geosciences", "geology"]),
    ("海洋", ["ocean", "marine"]),
    ("航空航天", ["aeronautics", "astronautics", "aerospace"]),
    ("电子", ["electronic", "electronics"]),
    ("邮电", ["posts", "telecommun", "telecommunications"]),
]
# 显著片段（专名）：命中其一即足以触发候选，避免只靠"城市/学科"这类泛词误报。
_DISTINCTIVE = {"清华", "北大", "复旦", "南开", "同济", "中山", "师范", "交通"}


def _latin_norm(s: str) -> str:
    """把英文串压成"小写字母数字 + 单空格"，使 'Sun Yat-sen' 也能匹配
    'sun yat sen'（连字符/点/& 等一律变空格）。"""
    return re.sub(r"[^a-z0-9]+", " ", s.casefold()).strip()


def discover_candidates(refs: list, doc_keys: list[list[str]],
                        display: dict, max_rows: int = 200) -> list[dict]:
    """发现"疑似同源但未合并"的中英节点对，返回建议行（不修改网络）。

    信号 A「同篇中英共现」：同一篇文献的机构列表里既有中文节点又有英文节点——
      用户描述的真实场景（中英题录混在同一篇）正是如此，上下文证据最强。
    信号 B「已知片段对应」：英文节点与中文节点共享已知中↔英片段，且命中显著
      专名 ≥1 或任意片段 ≥2；不要求共现，故能跨篇发现。**这是立候选的必要
      条件**（纯共现单独用会误报，见文件头说明）。
    信号 A「同篇中英共现」：在 B 命中之上，若两者还在同一篇文献里共现，则作为
      **加强证据**一并记录，证据更强、排序更靠前。
    """
    is_cjk = {k: bool(_CJK.search(display[k])) for k in display}
    cjk_keys = [k for k in display if is_cjk[k]]
    latin_keys = [k for k in display if not is_cjk[k]]

    # 信号 A：统计每个 (中文key, 英文key) 在哪几篇同现（仅作加强证据）
    pair_docs: dict[tuple[str, str], list[int]] = defaultdict(list)
    for di, ks in enumerate(doc_keys):
        uniq = set(ks)
        cs = [k for k in uniq if is_cjk.get(k)]
        ls = [k for k in uniq if not is_cjk.get(k)]
        for a in cs:
            for b in ls:
                pair_docs[(a, b)].append(di)

    # 信号 B：片段对应（跨篇，基于 _FRAGMENTS 词典）——立候选的必要条件
    pair_frags: dict[tuple[str, str], list[tuple[str, list[str]]]] = {}
    for a in cjk_keys:
        za = display[a]
        for b in latin_keys:
            zb = _latin_norm(display[b])
            matched = [(zh, [en for en in ens if en in zb])
                       for zh, ens in _FRAGMENTS if zh in za and any(en in zb for en in ens)]
            if not matched:
                continue
            if any(zh in _DISTINCTIVE for zh, _ in matched) or len(matched) >= 2:
                pair_frags[(a, b)] = matched

    rows = []
    for (a, b) in pair_frags:               # 必须有片段对应才立候选
        signals, ev = [], []
        docs = pair_docs.get((a, b))
        if docs:
            signals.append("同篇中英共现")
            sample = [((refs[i].get("title") or "")[:24] or f"#{i}") for i in docs[:3]]
            ev.append(f"共现 {len(docs)} 篇：{'; '.join(sample)}")
        signals.append("已知片段对应")
        ev.append("片段：" + "; ".join(
            f"{zh}↔{'/'.join(matched)}" for zh, matched in pair_frags[(a, b)]))
        rows.append({
            "candidate_a": display[a], "candidate_b": display[b],
            "signal": "+".join(signals), "evidence": " | ".join(ev),
            "suggestion": ("建议人工确认是否同一机构；确认后按 `别名,规范名` "
                           "追加到 references/org_aliases.csv"),
            "_nsig": len(signals), "_co": len(docs or []),
        })
    rows.sort(key=lambda r: (-r["_nsig"], -r["_co"], r["candidate_a"], r["candidate_b"]))
    return rows[:max_rows]


def build_empty_notice(total: int) -> str:
    return ("本数据源不含 affiliations 字段：%d 篇文献中 0 篇含机构，机构共现网络无法构建。"
            "请确认导入源是否提供机构字段（RIS 的 AD/C1、WoS 的 C1、EndNote tagged 的 %%+、"
            "NoteExpress 的 Author Address、CSV 的 Addresses/Affiliations）；"
            "CNKI .enl/.enw 与 Zotero 导出通常不含机构。" % total)


def main() -> int:
    ap = argparse.ArgumentParser(description="机构共现网络（含中英文同义归并）")
    ap.add_argument("target", help="import_sources.py 产出的 refs.json")
    ap.add_argument("--min-edge", type=int, default=1, help="边的最小共现次数（默认 1）")
    ap.add_argument("--min-df", type=int, default=1, help="节点最小文献频次（默认 1）")
    ap.add_argument("--top", type=int, default=None, help="最多保留多少节点（默认不限）")
    ap.add_argument("--name-mode", choices=["first", "full"], default="first",
                    help="first=取首个逗号前的主机构名（默认，去城市/邮编/前院系）；full=保留整串")
    ap.add_argument("--thesaurus", action="append", default=None, metavar="CSV",
                    help="追加同义词表（可多次传）。不传时默认加载包内 "
                         "references/org_aliases.csv")
    ap.add_argument("--no-thesaurus", action="store_true",
                    help="禁用包内默认同义词表（仍可另用 --thesaurus 追加自备表）；"
                         "用于回归对照")
    ap.add_argument("--keep-isolated", action="store_true",
                    help="保留度为 0 的孤立机构（默认剔除；孤立机构在本库内不与其他"
                         "机构共现，画进网络只是噪音）")
    ap.add_argument("--seed", type=int, default=42, help="布局随机种子（可复现）")
    ap.add_argument("--layout-max-nodes", type=int, default=1500,
                    help="参与力导向布局（FR）的核心节点上限（默认 1500，0=不限）。"
                         "超限时按度/文献频次确定性取前 N 个进 FR，其余与度=0 的孤立点"
                         "一起按确定性同心环排到网络外围；避免 O(n²) 在数千节点上退化到"
                         "分钟级（实测 3338 节点纯布局 ≈525s）")
    ap.add_argument("--no-layout", action="store_true",
                    help="跳过布局（只出 nodes/edges，报告端自行现场布局）")
    ap.add_argument("--out", default="./out")
    args = ap.parse_args()

    try:
        src = Path(args.target).expanduser()
        if not src.exists():
            print(f"[error] 输入不存在：{src}", file=sys.stderr)
            print(f"[hint] {EXIT[1]}", file=sys.stderr)
            return 1
        payload = load_payload(src)
        refs = payload.get("refs", [])

        # 组装同义词表路径：默认表自动加载（存在才加），--thesaurus 额外追加，
        # --no-thesaurus 关掉默认表。显式传入的表缺失会报错（不让用户静默失去预期合并）。
        th_paths: list[Path] = []
        if not args.no_thesaurus and _DEFAULT_THESAURUS.exists():
            th_paths.append(_DEFAULT_THESAURUS)
        for extra in (args.thesaurus or []):
            th_paths.append(Path(extra).expanduser())
        thesaurus, th_files, th_entries = load_thesaurus(th_paths)

        nodes, edges, stats, merges, candidates = build(
            refs, min_edge=args.min_edge, min_df=args.min_df,
            name_mode=args.name_mode, top=args.top,
            thesaurus=thesaurus, thesaurus_files=th_files,
            thesaurus_entries=th_entries, keep_isolated=args.keep_isolated)

        # ── 布局：与作者网络同一套确定性 FR（固定种子 → 同输入同输出）──
        # 坐标同时写入明文 x/y（pos_encoded 缺失时兜底）与 pos_encoded/edges_encoded
        # （报告端首屏直接用）。必须在 nodes 排序之后布局，否则 pos_encoded[i] 与
        # nodes[i] 错位（见 run_checks.c_sort_before_layout）。
        if nodes and not args.no_layout:
            pos = _layout(nodes, edges, seed=args.seed, max_nodes=args.layout_max_nodes)
            for i, nd in enumerate(nodes):
                nd["x"] = round(pos[i][0], 2)
                nd["y"] = round(pos[i][1], 2)
            # 如实记账：多少节点走了力导向、多少排在外环（规模与降级幅度可被外部核验）
            _iso = sum(1 for d in nodes if not (d.get("degree") or 0))
            _conn = len(nodes) - _iso
            _cap = args.layout_max_nodes
            _fr_n = _conn if (_cap <= 0 or _conn <= _cap) else _cap
            stats["layout_nodes"] = len(nodes)
            stats["layout_fr_nodes"] = _fr_n
            stats["layout_ring_nodes"] = len(nodes) - _fr_n
            stats["layout_max_nodes"] = _cap

        empty = stats["coverage"]["docs_with_affiliations"] == 0
        if empty:
            notice = build_empty_notice(stats["coverage"]["docs_total"])
            print(f"[warn] {notice}", file=sys.stderr)
        else:
            notice = "机构共现网络：节点=机构，边=同篇文献内两机构共现次数。"
            # 如实交代孤立节点剔除（不静默删）：本库内孤立机构无共现关系，默认不画入。
            _drop = stats.get("isolated_dropped", 0)
            if _drop:
                notice += (" 已剔除 %d 个孤立机构（度=0，本库内不与其他机构共现，"
                           "未画入图中）；如需保留请加 --keep-isolated。" % _drop)
            # 反过来说清"保留/超限"时布局怎么处理：外环节点没有被丢，只是不进 FR。
            _ring = stats.get("layout_ring_nodes", 0)
            if _ring:
                notice += (" 其中 %d 个节点未参与力导向布局（度=0 的孤立机构，或超过 "
                           "--layout-max-nodes=%d 上限的核心尾部），已按确定性同心环排在"
                           "网络外围——节点未丢弃，仅不享受力导向位置。"
                           % (_ring, stats.get("layout_max_nodes", 0)))
            # 说清着色维度：按社群（而非连通分量）着色，并如实报出社群数与最大占比。
            _nc = stats.get("communities", 0)
            if _nc:
                notice += (" 节点颜色按社群（加权标签传播）划分，共 %d 个社群，最大社群占 "
                           "%.1f%%（同色 = 同一共现社群）。" % (_nc, stats.get("largest_community_pct", 0.0)))

        payload_out = {
            "ok": True, "exit_code": 0,
            "library": {"name": src.name, "display_path": src.name,
                        "source": payload.get("source_label") or payload.get("source")},
            "type": "institution-cooccurrence",
            "empty_state": empty,
            "notice": notice,
            "stats": stats,
            "coverage": stats["coverage"],
            "nodes": nodes,
            "edges": edges,
        }
        if nodes and not args.no_layout:
            payload_out["pos_encoded"] = encode_pos(
                [[nd["x"], nd["y"]] for nd in nodes])
            payload_out["edges_encoded"] = encode_edges(
                [(e["source"], e["target"], e["weight"]) for e in edges], nodes)

        outdir = Path(args.out).expanduser()
        outdir.mkdir(parents=True, exist_ok=True)
        (outdir / "institution_network.json").write_text(
            json.dumps(payload_out, ensure_ascii=False, indent=1), encoding="utf-8")
        with open(outdir / "institution_network_nodes.csv", "w", newline="",
                  encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["institution", "df_doc", "degree", "weight", "variants",
                        "component", "component_size", "community", "community_size", "x", "y"])
            for nd in nodes:
                w.writerow([esc_csv_cell(nd["id"]), nd["df"], nd["degree"],
                            nd["weight"], nd["variants"],
                            nd.get("component", ""), nd.get("component_size", ""),
                            nd.get("community", ""), nd.get("community_size", ""),
                            nd.get("x", ""), nd.get("y", "")])
        # 合并审计表：原始写法 → 规范名 → 次数（供人工复核，机构名属不可信输入）
        with open(outdir / "org_alias_merges.csv", "w", newline="",
                  encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["raw", "canonical", "count"])
            for rw, canon, n in merges:
                w.writerow([esc_csv_cell(rw), esc_csv_cell(canon), n])
        # 疑似同源候选：只建议、不自动合并
        with open(outdir / "org_alias_candidates.csv", "w", newline="",
                  encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["candidate_a", "candidate_b", "signal", "evidence", "suggestion"])
            for row in candidates:
                w.writerow([esc_csv_cell(row["candidate_a"]),
                            esc_csv_cell(row["candidate_b"]), row["signal"],
                            esc_csv_cell(row["evidence"]), row["suggestion"]])

        emit({"ok": True, "out": str(outdir), "empty_state": empty,
              "stats": stats, "notice": notice,
              "merges": len(merges), "candidates": len(candidates)})
        return 0
    except EnlError as e:
        print(f"[error] {e}", file=sys.stderr)
        print(f"[hint] {EXIT[e.code]}", file=sys.stderr)
        return e.code
    except Exception as e:  # noqa: BLE001
        print(f"[error] {type(e).__name__}: {e}", file=sys.stderr)
        print(f"[hint] {EXIT[5]}", file=sys.stderr)
        return 5


if __name__ == "__main__":
    sys.exit(main())
