#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
lit_core.py —— 文献计量分析核心库

设计约束（均来自实测，不可违背）:
  1. 源库绝不写入。写操作需同时绕过 collation / query_only / EN_MAKE_SORT_KEY
     三道锁，且 13 个触发器依赖 EndNote 私有函数 -> 写操作结构性不可能。
  2. .enl 使用自定义排序规则 ENCI_Base / ENCIN_zh_CN。未注册时
     PRAGMA quick_check 直接抛 no such collation sequence。
  3. journal_mode = delete（无 WAL）-> 单文件 copy2 即得自洽快照。
  4. immutable=1 在库被外部写入时读到【过期快照】-> 仅对影子副本使用。
  5. refs.id 不连续（min=1, max=10041, count=5558）-> 禁止 id-1 作下标。
  6. keywords 以 \\r 分隔，非逗号。
  7. 关键词需 lower 归一：实测 834 个概念存在大小写变体
     （Performance/performance），不归一会割裂社区。
  8. NMF 用 init='nndsvda' + random_state=42。[!]  精确含义（实测纠正）：
     "确定性"仅指**同一 random_state 下可复现**；sklearn 的 nndsvda 内部
     走 randomized SVD，换 random_state 会改变初始化 → 簇归属变化
     （实测 K=14：random_state 7→ARI 0.74、2024→ARI 0.69）。
     故 random_state 必须固定并写入方法章节，不可只说"用了 SVD 初始化"。
     换种子的一致性由 robust_k.py 检验并给出数值。
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sqlite3
import struct
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field, asdict
from pathlib import Path

# ── 退出码契约（唯一事实源，见 00_项目交付方案.md §8.2.1）──────────────
# 每码必须附修复指引 —— 光有码没有"该跟用户说什么"，Agent 会自行编造。
EXIT = {
    0: "成功",
    1: "源库不可用：请检查移动硬盘是否连接、路径是否正确",
    2: "格式不支持：请确认来源可读（EndNote .enl / refs.json / RIS / BibTeX / "
       "EndNote XML / Zotero zotero.sqlite / WoS· Scopus· CNKI CSV）",
    3: "文件锁占用：请关闭 EndNote 后重试，或使用「分析副本」",
    4: "参数错误：请检查 --k / --threshold 取值范围",
    5: "计算失败：请附日志反馈，属未预期缺陷",
    6: "库损坏：请用 EndNote 的 Repair 功能修复库",
    7: "派生库写入失败：请检查工作目录权限与磁盘空间",
    8: "环境不满足：请改用 Python 3.11+ 解释器（系统 3.9.6 无 numpy）；"
       "若缺的是 R + igraph，请安装 R 并执行 install.packages('igraph')",
}


# ── Rscript 定位（doctor.py 与 sna_r.py 的唯一事实源）──────────────────
# 为什么要抽公共函数：此前两处各写一套 glob —— doctor.py 只扫 Windows 的
# C:\\Program Files\\R，sna_r.py 另扫 macOS/Linux 路径但 Windows pattern 带
# `.exe` 后缀。结果是"同一台机器上 doctor 说找不到、sna_r 找得到"这类
# 自相矛盾，且 Linux 上两边都匹配不到（那里的可执行文件没有 .exe）。
# 探测口径必须唯一，否则门禁与执行层的判断就不可能一致。
R_GLOBE_DIRECTORIES = (
    r"C:/Program Files/R",
    r"C:/Program Files (x86)/R",
    "/Library/Frameworks/R.framework/Versions",
    "/usr/lib/R",
    "/usr/local/lib/R",
    "/opt/homebrew/lib/R",
    "/usr/local/opt/R",
)

# 相对各根目录的候选形态。**必须同时覆盖带 .exe 与不带 .exe 两种**，
# 否则在 Linux/macOS 上会全线漏检。
R_GLOBE_PATTERNS = (
    "R-*/bin/Rscript.exe",     # Windows: C:/Program Files/R/R-4.3.1/bin/
    "R-*/bin/Rscript",         # Linux/macOS 传统安装
    "*/bin/Rscript",           # Linux: /usr/lib/R/bin
    "*/Resources/bin/Rscript",  # macOS framework: .../Versions/4.3-arm64/Resources/bin
    "Versions/*/Resources/bin/Rscript",  # macOS：根目录已指到 Versions 时
    "Versions/*/bin/Rscript",   # macOS framework 备用形态
)


def _r_version_key(p):
    """把 R 安装路径变成可比较的版本元组，用于取「最新的 R」。

    'C:/Program Files/R/R-4.10.0/bin/Rscript.exe' → (1, 4, 10, 0)
    'C:/Program Files/R/R-4.9.2/bin/Rscript.exe'  → (1, 4, 9, 2)
    '/usr/lib/R/bin/Rscript'（无版本号）           → (0, 0, 0, 0)  ← 排最后

    首元素区分「有无版本号」：开发版/手动装版（无版本号）排在正式版之后，
    避免在 R-4.11 与 /usr/local/R 共存时挑到后者。
    """
    import re as _re
    s = str(p)
    m = _re.search(r"R-(\d+)\.(\d+)(?:\.(\d+))?", s)
    if not m:
        return (0, 0, 0, 0)
    major, minor, patch = m.group(1), m.group(2), m.group(3)
    return (1, int(major), int(minor), int(patch or 0))


def iter_rscript_candidates():
    """按版本倒序产出所有候选 Rscript 路径（跨平台）。

    排序必须按**版本号数值**，不能按字符串：`sorted(reverse=True)` 会把
    'R-4.9.2' 排在 'R-4.11.0' 之前（'9' > '1'），于是多版本共存时会挑到
    旧版 R 做计量分析 —— 结果与用户预期不符，且极难察觉。
    示例：['R-4.6.1','R-4.10.0','R-4.9.2','R-4.11.0']
          字符串倒序 → R-4.9.2 排第一（错）
          版本号倒序 → R-4.11.0 排第一（对）

    无版本号的路径（如 /usr/lib/R/bin/Rscript）排在有版本号的之后，
    保证「有多个正式版本时优先用最新的正式版」。
    """
    seen = set()
    for root in R_GLOBE_DIRECTORIES:
        p0 = Path(root)
        if not p0.is_dir():
            continue
        for pat in R_GLOBE_PATTERNS:
            try:
                hits = sorted(p0.glob(pat), key=_r_version_key, reverse=True)
            except OSError:
                continue  # 无权限/竞态删除：跳过而非让整场探测崩掉
            for h in hits:
                s = str(h)
                if s not in seen and h.is_file():
                    seen.add(s)
                    yield s


def find_rscript():
    """定位 Rscript，返回 (path | None, source)。

    source: "PATH"  → 由 PATH 直接命中；
            "glob"  → 装好了但不在 PATH（Windows 常态，必须兜底查找，
                       否则会把用户推去重装 R）；
            ""      → 确实没找到。

    **本函数是 R 探测的唯一实现** —— doctor.py（门禁）与 sna_r.py（执行层）
    都调用它，杜绝"两处口径不一致导致门禁放行、执行时才失败"。
    """
    rs = shutil.which("Rscript") or shutil.which("Rscript.exe")
    if rs:
        return rs, "PATH"
    for cand in iter_rscript_candidates():
        return cand, "glob"
    return None, ""


class EnlError(Exception):
    def __init__(self, code: int, detail: str = ""):
        self.code = code
        self.detail = detail
        super().__init__(f"[{code}] {EXIT.get(code, '未知错误')}" + (f" | {detail}" if detail else ""))


# ── 输出加固（HTML / JSON / CSV 注入防线）───────────────────
# 文献标题、关键词、作者等字段来自外部来源（CNKI / WoS / Zotero 导入），
# 属不可信输入；导出到 HTML 报告、内联 <script> JSON 与 CSV 时必须过滤，
# 防止 <script> 注入与 Excel 公式注入（=CMD|…）。
def esc_html(s) -> str:
    """HTML 转义（与 build_report 历史口径一致，收敛到核心库统一维护）。"""
    import html as _html
    return _html.escape(str(s if s is not None else ""))


def esc_json(s) -> str:
    """把单值序列化为可安全内联进 HTML <script> 的 JSON 片段。

    关键：转义 `<` `>`（防 </script> 提前闭合）、`&`（防实体解析歧义）、
    U+2028/U+2029（JS 合法 JSON 但在字符串字面量外会报语法错）。
    """
    frag = json.dumps(s, ensure_ascii=False, separators=(",", ":"))
    return (frag.replace("&", "\\u0026")
                .replace("<", "\\u003c")
                .replace(">", "\\u003e")
                .replace("\u2028", "\\u2028")
                .replace("\u2029", "\\u2029"))


_CSV_FORMULA_PREFIXES = ("=", "+", "-", "@")


def esc_csv_cell(v) -> str:
    """CSV 单元格加固：以 = + - @ 开头的文本前置单引号，阻断 Excel/LibreOffice
    打开导出文件时的公式注入（DDE / SYSTEM 命令）。数字与非公式文本原样返回。

    [!]  前导空白也要检查：Excel 以**首字符**判定公式，
    故 ' =1+1' 在 Excel 里安全；但 LibreOffice 开启「修剪空格」或用户手动
    去空格后会执行。判前缀前先 lstrip，覆盖这部分加固不足。
    """
    s = "" if v is None else str(v)
    if s.lstrip().startswith(_CSV_FORMULA_PREFIXES):
        return "'" + s
    return s


# ── 文本规范化 ──────────────────────────────────────────────
# 版权水印整块剥离。实测 677 条（12.2%）含版权串。
# 注意：真实污染源是 rights(462)/reserved(455)/psycinfo(454)，
# `Copyright` 仅 31 条 —— 只过滤 apa 一个词无效。
BOILERPLATE_RE = re.compile(
    r"(copyright|rights\s+reserved|all\s+rights\s+reserved|psycinfo|"
    r"permissions?|\bdoi\s*:|®|©|this\s+article|reprinted|"
    r"未经|版权所有|保留所有权利)",
    re.I,
)

# 中英双语停用词。中文含学术套话（研究/分析/影响/作用/关系/机制/理论/行为/
# 结果/表明/本文）—— 实测不剔除时这些会占据 top-term。
STOP_EN = set("""a an the and or but if then than that this these those is are was were
of in on at to for from by with without within into upon onto over under about across
study studies research researches article articles paper papers journal journals
result results finding findings analysis analyses method methods methodology approach
theory theories model models framework frameworks factor factors effect effects
impact impacts relationship relationships influence influences role roles
significant significantly show shows shown find finds found suggest suggests
use used using useful use based focus focuses focused consider considers
purpose aim objective goal target provide provides provided obtain obtained
report reports reported discuss discusses discussed examine examines examined
increase increases increased decrease decreases decreased change changes changed
level levels number numbers rate rates value values high low greater less
important significant difference differences similarity differences
potential possible likely generally typically often always never
between among within without across among via per
be been being am have has had do does did will would shall should may might must can
could we our us they their them he she his her it its as at by for from in into of on
to with without over under again further once here there all any both each few more
most other some such no nor not only own same so too very when where why how also
which who whom whose because while during before after above below between within
across upon among against toward towards via per etc thus hence therefore however
although though since unless until whether either neither yet still ever never
""".split())

STOP_ZH = set("""的 了 和 是 就 都 而 及 与 著 或 一个 没有 我们 你们 他们 她们 它们
这 那 这个 那个 这些 那些 之 其 在 对 从 被 把 让 给 向 中 上 下 不 有 也 会
研究 分析 影响 作用 关系 机制 理论 行为 结果 表明 本文 表明 显示 发现 提出
认为 知道 可以 需要 通过 进行 对于 关于 以及 或者 而且 但是 因此 所以
一个 一些 一样 一直 一定 一般 本研究 本文 旨在 试图 表明 指出 认为
具有 进行 存在 属于 包括 主要 重要 显著 有效 进一步 深入
基于 通过 对于 关于 以及 而且 但是 因此 所以 同时 然后 此外 另外
首先 其次 最后 综上 总之 由此 可以能够 应该 必须 需要 想要
研究结果 研究表明 表明 结果 数据显示 数据显示 实证 检验 验证
假设 理论 模型 框架 方法 分析 探讨 讨论 考察 观察 发现 指出
作用 影响 意义 价值 贡献 优势 劣势 问题 对策 建议 措施
近年来 随着 目前 当前 未来 发展 趋势 现状 对策 挑战 机遇
""".split())

_CJK = re.compile(r"[一-鿿]")
_YEAR = re.compile(r"^(?:19|20)\d{2}$")


# ── 术语别名层（回应实测需求） ─────────────────
# 解决三个实测问题：
#   ① 「工作重塑」与 job crafting 同义未合并；
#   ② 中英文数据库混用时中英文对照不好；
#   ③ performance / creativity 这类泛词被单独切出，脱离了
#      「什么样的绩效/创造力」的语境。
# 设计原则（诚实边界）：
#   - 只合并用户可查证、可否决的条目：别名表是**显式文件**，
#     每一行都可在报告里回溯；未经表合并的词一律不动原文。
#   - 泛词（如 lone "performance"）**绝不自动合并**进复合词——那会编造
#     数据没有的语义。只生成 merge_suggestions（文档集包含关系检测）
#     交给用户确认，确认后写进 term_aliases.local.csv 才生效。

def load_term_aliases(path: str | os.PathLike | None = None) -> dict:
    """加载术语别名表。

    格式（UTF-8 CSV，无表头）：`别名,规范名,英文对照,备注`
    优先级：term_aliases.local.csv（用户维护，优先生效） >
           term_aliases.csv（随包内置种子表）。
    返回 {别名小写: {"canonical": 规范名, "display_en": 英文对照}}。
    """
    here = Path(__file__).resolve().parent.parent / "references"
    out: dict = {}
    for name in ("term_aliases.csv", "term_aliases.local.csv"):
        p = Path(path) if path else here / name
        if not p.is_file():
            continue
        try:
            with open(p, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    parts = [x.strip() for x in line.split(",")]
                    if len(parts) < 2 or not parts[0] or not parts[1]:
                        continue
                    alias, canon = parts[0].lower(), parts[1]
                    en = parts[2] if len(parts) > 2 else ""
                    out[alias] = {"canonical": canon, "display_en": en}
        except Exception:
            continue
    return out


def apply_term_aliases(kw_list: list, alias_map: dict) -> tuple[list, list]:
    """把一批关键词映射到规范名。返回 (映射后列表, 命中的合并对)。

    命中的合并对 [{alias, canonical}] 供报告回溯「哪些词被合并了」；
    未命中表的关键词保持原样——**不做任何自动语义归并**。

    v1.0.0：查表前先做**连字符/下划线归一**（social-exchange theory →
    social exchange theory）——实测主题详情 chips 里两种写法同时出现，
    根因就是精确查表命中不了连字符变体。
    """
    if not alias_map:
        return list(kw_list), []
    out, hits = [], []
    for w in kw_list:
        low = str(w).lower().strip()
        # 连字符/下划线 → 空格，压缩连续空白（形式归一，不动语序）
        low_norm = re.sub(r"[-_]+", " ", low)
        low_norm = re.sub(r"\s+", " ", low_norm).strip()
        m = alias_map.get(low) or (alias_map.get(low_norm) if low_norm != low else None)
        if m and m["canonical"] != w:
            out.append(m["canonical"])
            hits.append({"alias": w, "canonical": m["canonical"]})
        else:
            out.append(w)
    return out, hits


def merge_suggestions(df_counter, doc_sets: dict, max_suggestions: int = 12) -> list:
    """泛词合并建议：泛词的文档集 ⊆ 若干复合词文档集之并集 → 疑似同一概念。

    例：lone "creativity" 出现的文献若全部也带 "employee creativity" 或
    "team creativity"，则它大概率是被拆散的泛指词。**只建议，不自动合并**——
    由用户确认后再写进 term_aliases.local.csv。
    """
    GENERIC = {"performance", "creativity", "innovation", "behavior", "engagement",
               "satisfaction", "commitment", "burnout", "leadership", "stress",
               "绩效", "创造力", "创新", "行为", "投入", "满意度", "承诺", "倦怠", "领导"}
    suggestions = []
    for w in GENERIC:
        if w not in doc_sets:
            continue
        wset = doc_sets[w]
        hosts = [(h, s) for h, s in doc_sets.items()
                 if h != w and len(h) > len(w) and w in h and s & wset]
        # 只保留「文档集覆盖泛词」程度高的宿主复合词
        hosts = [(h, len(s & wset)) for h, s in hosts
                 if len(s & wset) >= max(2, len(wset) * 0.5)]
        if hosts:
            hosts.sort(key=lambda x: (-x[1], x[0]))
            suggestions.append({
                "generic": w, "df": len(wset),
                "suggest_merge_into": [h for h, _ in hosts[:4]],
                "shared_docs": hosts[0][1],
            })
        if len(suggestions) >= max_suggestions:
            break
    return suggestions


def is_cjk(text: str) -> bool:
    """CJK 判定。注意：不能用源库 language 字段（实测 74% 为空），
    必须按字符判定。正则版本须随 params_json 落库（Q9 遗留项）。"""
    return bool(_CJK.search(text or ""))


def clean_text(s: str | None) -> str:
    """去版权段 + 压缩空白。"""
    if not s:
        return ""
    return re.sub(r"\s+", " ", BOILERPLATE_RE.sub(" ", s)).strip()


def split_keywords(raw: str | None) -> list[str]:
    """EndNote 关键词以 \\r（回车符）分隔，非逗号。"""
    if not raw:
        return []
    return [w.strip() for w in raw.split("\r") if w.strip()]


def norm_keyword(w: str) -> str:
    """关键词归一：仅 lower + 去首尾空白。

    [!]  不可剥离 `*` 前缀——实测带* 的是 MeSH 风格专业概念标记
    （*artificial intelligence / *burnout, professional / *citizenship /
    *behavior, addictive），共 77 个进入 df>=5 主图谱。剥离会让这些
    核心研究构念从网络中消失，导致 1079 节点 ≠ 权威 1094。

    口径对照（实测）：
      仅 lower                    → 1094 节点 / 10672 边  [OK] 权威
      lower + 去* 前缀            → 1079 节点 / 10959 边
      lower + 去* + NFKC         → 1079 节点 / 10959 边（NFKC 无额外影响）

    lower 归一不可省略——实测 834 个概念存在大小写变体，
    不归一会把同一研究概念拆成两个节点并割裂社区。
    """
    return w.lower().strip()


def parse_authors(raw: str | None) -> list[str]:
    """EndNote author 以回车符（chr(13)）分隔，单作者格式 'Last, F. M.'。

    返回 canon 列表：'surname|initials'（小写）。姓氏相同但名字不同（同名作者）靠
    initials 区分；用于跨文献的作者聚合（主题×作者矩阵、核心作者识别）。

    initials 取 rest 中每个空格分隔「词」的首字母（而非所有字母），故
    'Burke, Ronald J.' → 'burke|rj'，'Schaufeli, W. B.' → 'schaufeli|wb'，
    既能区分同名、又避免把全名拼进缩写（按所有字母取首字母会写成 RonaldJ）。
    """
    if not raw:
        return []
    out: list[str] = []
    for a in raw.split(chr(13)):
        a = a.strip()
        if not a:
            continue
        if "," in a:
            sur, rest = a.split(",", 1)
        else:
            sur, rest = a, ""
        sur = sur.strip().lower()
        ini = "".join(t[0].lower() for t in rest.split() if t and t[0].isalpha())
        if sur:
            out.append(f"{sur}|{ini}")
    return out


# ── 只读接入层 ──────────────────────────────────────────────
def _collation(a, b):
    return (a > b) - (a < b)


def open_enl_readonly(path: str | os.PathLike, immutable: bool = False) -> sqlite3.Connection:
    """只读打开 .enl。必须注册自定义 collation，否则查询直接失败。

    immutable=True 仅可用于【影子副本】—— 源库被 EndNote 写入时，
    immutable 会读到过期快照且无任何提示（实测确认）。
    """
    p = Path(path)
    if not p.exists():
        raise EnlError(1, f"源库不存在：{p}")
    uri = f"file:{p}?mode=ro" + ("&immutable=1" if immutable else "")
    try:
        con = sqlite3.connect(uri, uri=True)
        # 缺这两行则任何涉及 jterms/排序的查询抛 OperationalError
        con.create_collation("ENCI_Base", _collation)
        con.create_collation("ENCIN_zh_CN", _collation)
        con.execute("PRAGMA query_only = 1")
        return con
    except sqlite3.OperationalError as e:
        msg = str(e).lower()
        if "collation" in msg:
            raise EnlError(6, f"排序规则异常：{e}")
        if "locked" in msg:
            raise EnlError(3, str(e))
        raise EnlError(6, str(e))
    except sqlite3.DatabaseError as e:
        raise EnlError(6, f"数据库损坏：{e}")


def is_locked(path: str | os.PathLike) -> bool:
    """检测 EndNote 是否正在运行并持锁。

    证据四路：-wal/-journal/-shm 残留文件 / 平台持锁工具 / 进程探测 / 试写。
    任一命中即认为可能占用。

    [!]  跨平台：只用 `lsof` 是 macOS/Linux 专有；
       Windows 上 FileNotFoundError 被 `except: pass` 吞掉 -> **静默漏报**，
       用户以为库未被占用，实则 EndNote 正持锁。改为按平台分派：
         · macOS/Linux：lsof（无则退回 fuser → 再退回 pgrep）
         · Windows：     handle.exe / openfiles 不可靠 -> 改用进程探测
       全程**不抛异常**，探测失败时返回 False 并由调用方在报告里如实标注
       "占用检测不可用"，而不是默认"未占用"。
    """
    p = Path(path)
    # 证据 1：SQLite 残留文件（三平台通用，最可靠）
    for suffix in ("-wal", "-journal", "-shm"):
        if Path(str(p) + suffix).exists():
            return True

    import subprocess
    if os.name == "nt":
        # 证据 2（Windows）：进程名探测。
        # [!]  已知局限（如实说明，不假装能做到）：进程名探测**无法确认该进程
        #   是否持有本库文件**——Windows 没有 Unix 的 lsof 等价物。
        #   因此「EndNote 在运行」可能被误报为「本库被占用」。
        #   缓解：产物中同时给出 lock_probe_available 与本 notice，
        #   报告层会显示「无法判断题录库是否持锁」，让用户自行判断。
        #   早期注释曾声称「校验库文件是否位于该进程常见位置」——该校验
        #   并不存在，属声明与事实相反，已删除而非保留误导性措辞。
        for proc in ("EndNote.exe", "EndNote", "endnote.exe"):
            try:
                out = subprocess.run(
                    ["tasklist", "/FI", f"IMAGENAME eq {proc}"],
                    capture_output=True, text=True, timeout=8)
                low = (out.stdout or "").lower()
                if proc.lower() in low and "no tasks" not in low:
                    return True
            except Exception:
                continue
        return False

    # 证据 2（macOS/Linux）：持锁工具
    for cmd in (["lsof", str(p)], ["fuser", str(p)]):
        try:
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=8)
            # lsof: 有输出即命中；fuser: stdout 打印 PID
            if out.returncode == 0 and (out.stdout or "").strip():
                return True
        except (FileNotFoundError, OSError):
            continue          # 工具不存在 → 试下一个
        except Exception:
            continue

    # 证据 3：进程探测（lsof/fuser 都不可用时的兜底）
    try:
        out = subprocess.run(["pgrep", "-if", "enl"],
                             capture_output=True, text=True, timeout=8)
        if out.returncode == 0 and (out.stdout or "").strip():
            return True
    except (FileNotFoundError, OSError):
        pass
    except Exception:
        pass
    return False


def lock_probe_available(path: str | os.PathLike) -> bool:
    """占用探测能力是否可用。不可用时报告须如实标注，不得默认"未占用"。"""
    import shutil
    if os.name == "nt":
        return bool(shutil.which("tasklist"))
    return bool(shutil.which("lsof") or shutil.which("fuser")
                or shutil.which("pgrep"))


def lock_status(path: str | os.PathLike) -> tuple[bool, bool, str | None]:
    """**统一入口**：一次返回 (busy, probe_ok, notice)。

    存在的理由：`is_locked` 的 docstring 承诺
    「探测失败时由调用方在报告里如实标注占用检测不可用」，
    但此前 9 个调用方里只有 scan_library 兑现了—— 其余 6 个直接
    `busy = is_locked(...)` 就把 False 当"未占用"写进产物，
    在没有 lsof/fuser/pgrep 的平台上会**静默漏报**。
    那正是本包第 4 处「异常/事实被静默吞掉」。

    所有需要报告 busy 状态的模块都应改用本函数，
    并把 notice 原文写进产物/警告，不要自行拼措辞。
    """
    busy = is_locked(path)
    ok = lock_probe_available(path)
    notice = None if ok else (
        "当前平台缺少持锁探测工具（lsof/fuser/pgrep/tasklist），"
        "无法判断题录库是否持锁；数据可能不是最新。")
    return busy, ok, notice


def make_shadow(src: str | os.PathLike, workdir: str | os.PathLike) -> Path:
    """复制影子副本。实测 23MB copy2 仅 0.02s。

    影子副本的价值不是"更安全"而是"唯一可用"—— 实测 EndNote 持锁时
    直连源库报 database is locked，副本可正常读出。
    """
    src, work = Path(src), Path(workdir)
    work.mkdir(parents=True, exist_ok=True)
    dst = work / src.name
    shutil.copy2(src, dst)
    return dst


def lib_digest(path: str | os.PathLike) -> str:
    """blake2b-128 内容指纹。实测全库 0.0299s，distinct=5558 无碰撞。

    用 0.03s 买 100% 正确性：既然全量哈希免费，就不做增量维护
    （record_last_updated 实测 5558 条仅 1046 个不同值，时间戳会漏数据）。
    """
    h = hashlib.blake2b(digest_size=16)
    with open(path, "rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def find_enl(target: "Path | str | os.PathLike") -> Path:
    """定位 .enl。支持直接传入文件或文件夹（用户拖入场景）。

    排除 macOS 的 ._ 资源分叉文件（4096 字节空壳，会污染 glob）。
    多个 .enl 时取最大者（主库通常最大）。
    """
    target = Path(target).expanduser()
    if target.is_file():
        return target
    if not target.is_dir():
        raise EnlError(1, f"路径不存在：{target}")
    cands = [p for p in sorted(target.glob("*.enl")) if not p.name.startswith("._")]
    if not cands:
        raise EnlError(1, f"该目录下未找到 .enl 文件：{target}")
    if len(cands) > 1:
        print(f"[warn] 发现 {len(cands)} 个 .enl，取最大的作为主库", file=sys.stderr)
    return max(cands, key=lambda p: p.stat().st_size)


# ── 数据模型 ────────────────────────────────────────────────
@dataclass
class Ref:
    id: int
    title: str
    abstract: str
    keywords: list[str]      # 已归一（小写）
    year: int | None
    journal: str
    authors: str
    doi: str
    tier: str                # primary_abs | primary_kw | fallback_title | empty
    has_pdf: bool
    pdf_path: str | None
    raw_hash: str
    read_status: str = ""               # EndNote read 字段：'0'=未读/待读 '1'=已读
    author_list: list[str] = field(default_factory=list)  # 解析后的作者 canon 名（按 \r + 姓,名）


TIER_LABELS = {
    "primary_abs": "有摘要（主语料）",
    "primary_kw": "仅关键词（主语料）",
    "fallback_title": "仅标题（降级）",
    "empty": "无内容",
}


def extract_doi(ern: str | None) -> str:
    """electronic_resource_number 混装 4 种格式。实测：纯 DOI 3541 /
    Doi 前缀 438 / ARTN 混装 337 / URL 0 / CNKI 30（非空 4346）。"""
    s = (ern or "").strip()
    if not s:
        return ""
    # ARTN xxx\r10.xxx 混装 -> 取 \r 后段
    for seg in reversed(s.split("\r")):
        m = re.search(r"(10\.\d{4,9}/[^\s\"<>]+)", seg)
        if m:
            return m.group(1)
    return ""


def parse_refs(con: sqlite3.Connection, data_dir: Path | None) -> list[Ref]:
    """读取全部文献。零静默丢弃：每条必须归入某个 tier。"""
    cur = con.cursor()
    # 动态列检查：read_status 在部分 EndNote 版本可能缺失，缺失则降级为空串
    _avail = {r[1] for r in cur.execute("PRAGMA table_info(refs)")}
    _sel = [c for c in ("id", "title", "abstract", "keywords", "year",
                        "secondary_title", "author", "electronic_resource_number")
            if c in _avail]
    _has_rs = "read_status" in _avail
    if _has_rs:
        _sel.append("read_status")
    _idx = {c: i for i, c in enumerate(_sel)}
    rows = cur.execute(
        f"SELECT {','.join(_sel)} FROM refs WHERE trash_state=0"
    ).fetchall()

    # PDF 关联：实测 file_res 5374 条，refs_ord.ro_key_44 存在率 100%，
    # 其余 ro_key_2/3 为 0% —— ro_key_44 判别力充足。
    pdf_map: dict[int, str] = {}
    for rid, fp in cur.execute("SELECT refs_id, file_path FROM file_res"):
        pdf_map[rid] = fp

    # 分组：members 为 [magic:u32][count:u32][refs.id:u32 × count]
    # 实测 50/50 组满足 len == 8 + count*4；45 组非空，union 覆盖 99.5%
    group_map: dict[int, list[str]] = defaultdict(list)
    for gid, spec, members in cur.execute("SELECT group_id, spec, members FROM groups"):
        if not members or len(members) < 8:
            continue
        _, count = struct.unpack_from("<II", members, 0)
        if count == 0 or len(members) != 8 + count * 4:
            continue
        ids = struct.unpack_from(f"<{count}I", members, 8)
        group_map[gid] = [str(x) for x in ids]

    refs: list[Ref] = []
    for row in rows:
        rid = row[_idx["id"]]
        title = row[_idx["title"]]
        abstract = row[_idx["abstract"]]
        kw_raw = row[_idx["keywords"]]
        year_v = row[_idx["year"]]
        journal = row[_idx["secondary_title"]]
        author = row[_idx["author"]]
        ern = row[_idx["electronic_resource_number"]]
        rs = row[_idx["read_status"]] if _has_rs else ""

        title_c = clean_text(title)
        abs_c = clean_text(abstract)
        kws = [k for k in (norm_keyword(w) for w in split_keywords(kw_raw)) if k]

        if abs_c and len(abs_c) >= 50:
            tier = "primary_abs"
        elif kws:
            tier = "primary_kw"
        elif title_c:
            tier = "fallback_title"
        else:
            tier = "empty"
        y = None
        if year_v:
            m = re.search(r"(?:19|20)\d{2}", str(year_v))
            if m:
                y = int(m.group(0))

        rel = pdf_map.get(rid)
        refs.append(Ref(
            id=rid,
            title=title_c,
            abstract=abs_c,
            keywords=kws,
            year=y,
            journal=clean_text(journal),
            authors=clean_text(author),
            doi=extract_doi(ern),
            tier=tier,
            has_pdf=rel is not None,
            pdf_path=(str(data_dir / rel) if (rel and data_dir) else None),
            raw_hash=hashlib.blake2b(
                f"{rid}{chr(0)}{title_c}{chr(0)}{abs_c}".encode(), digest_size=8
            ).hexdigest(),
            read_status=str(rs) if rs is not None else "",
            author_list=parse_authors(author),
        ))
    return refs


# ── 多来源归一化边界（refs.json 交换格式）────────────────────
# 动机：EndNote 无 API，但用户未必用 EndNote。Zotero / NoteExpress / CNKI / WoS
# 的记录格式各异，若每个来源各写一套下游逻辑，必然六套代码六份 bug。
# 做法：所有来源统一归一为 Ref[] → refs.json；下游各模块只认 Ref[]，
#       经 load_refs() 透明接受 .enl 或 refs.json，代码零分叉。
#
# [!]  零静默丢弃对多来源同样成立：tier 判定口径必须与 parse_refs 完全一致，
#    故抽成 assign_tier() 作单一事实源，两条入口共用。

SOURCE_LABELS = {
    "enl": "EndNote .enl",
    "refs_json": "refs.json（多来源归一化产物）",
    "zotero": "Zotero zotero.sqlite",
    "ris": "RIS（CNKI / WoS / Scopus / NoteExpress 导出）",
    "bibtex": "BibTeX",
    "enl_xml": "EndNote XML（.enw）",
    "csv": "CSV（WoS / Scopus / CNKI 导出）",
    "enl_tagged": "EndNote tagged（%T/%A，CNKI 的 .enw 实际格式）",
    "noteexpress": "NoteExpress 原生导出（.net）",
    "cnki_xml": "CNKI XML（.txt/.xml，<Bibliographies>）",
    "cnki_gb7714": "CNKI GB7714 引文列表（纯文本，无摘要）",
    "zotero_rdf": "Zotero RDF（.rdf）",
    "betterbibtex_json": "Better BibTeX JSON（.json）",
    "multi": "多来源合并",
    "wos_tagged": "Web of Science 纯文本（.txt，FN/VR/ER）",
    "wos_html": "Web of Science HTML（.html）",
    "wos_xls": "Web of Science Excel（.xls，需 xlrd）",
}


def assign_tier(abstract: str, keywords: list, title: str) -> str:
    """tier 判定的**单一事实源**。parse_refs 与所有导入器共用。

    与 parse_refs 的历史口径逐字一致（勿改）：
      有摘要且 >=50 字 → primary_abs（主语料）
      否则有关键词    → primary_kw（主语料；关键词是聚类主干信号）
      否则有标题      → fallback_title（降级）
      都不满足        → empty（零静默丢弃的终点）
    """
    if abstract and len(abstract) >= 50:
        return "primary_abs"
    if keywords:
        return "primary_kw"
    if title:
        return "fallback_title"
    return "empty"


def make_ref(rid, title, abstract, keywords, year, journal, authors, doi,
             has_pdf=False, pdf_path=None, read_status="",
             author_list=None, raw_hash=None):
    """构造 Ref 并按统一口径算 tier / raw_hash。非 .enl 来源一律走这里。"""
    title_c = clean_text(title)
    abs_c = clean_text(abstract)
    kws = [k for k in (norm_keyword(w) for w in (keywords or [])) if k]
    if raw_hash is None:
        raw_hash = hashlib.blake2b(
            f"{rid}{chr(0)}{title_c}{chr(0)}{abs_c}".encode(), digest_size=8
        ).hexdigest()
    if author_list is None:
        author_list = parse_authors(authors)
    return Ref(
        id=rid, title=title_c, abstract=abs_c, keywords=kws, year=year,
        journal=clean_text(journal), authors=clean_text(authors),
        doi=(doi or "").strip(), tier=assign_tier(abs_c, kws, title_c),
        has_pdf=bool(has_pdf), pdf_path=pdf_path, raw_hash=raw_hash,
        read_status=str(read_status or ""), author_list=author_list,
    )


def refs_to_json(refs: list, source: str, extra: dict | None = None) -> dict:
    """序列化为 refs.json 载荷（import_refs.py 写盘 / load_refs 读盘）。"""
    return {
        "format": "academic-lit-analysis/refs@1",
        "source": source,
        "source_label": SOURCE_LABELS.get(source, source),
        "count": len(refs),
        "refs": [asdict(r) for r in refs],
        "coverage": coverage_report(refs),
        "meta": extra or {},
    }


def refs_from_json(payload: dict) -> list:
    """refs.json → Ref[]。容忍缺字段（导入器可能只填部分列）。"""
    if payload.get("format") != "academic-lit-analysis/refs@1":
        raise EnlError(2, f"不是 refs.json 载荷（format={payload.get('format')!r}）")
    out = []
    for d in payload.get("refs", []):
        out.append(Ref(
            id=d.get("id"), title=d.get("title", ""), abstract=d.get("abstract", ""),
            keywords=list(d.get("keywords") or []), year=d.get("year"),
            journal=d.get("journal", ""), authors=d.get("authors", ""),
            doi=d.get("doi", ""), tier=d.get("tier", "empty"),
            has_pdf=bool(d.get("has_pdf")), pdf_path=d.get("pdf_path"),
            raw_hash=d.get("raw_hash", ""), read_status=d.get("read_status", ""),
            author_list=list(d.get("author_list") or []),
        ))
    return out


def load_refs(target: "Path | str | os.PathLike",
              workspace: "Path | str | os.PathLike" = "./.lit_work"):
    """**统一装载入口** —— 下游所有模块只认这一个函数。

    返回 (refs, meta)：
      · target 是 .json  → 多来源归一化产物（refs.json）
      · 否则            → .enl 只读链路（影子副本 + mode=ro）
    meta 记录来源，供报告如实标注「本结果来自哪种来源」——
    不可静默把 Zotero 库说成 .enl 库。
    """
    p = Path(target).expanduser()
    if p.is_file() and p.suffix.lower() == ".json":
        payload = json.loads(p.read_text(encoding="utf-8"))
        src = payload.get("source", "refs_json")
        return refs_from_json(payload), {
            "source": src, "source_label": SOURCE_LABELS.get(src, src),
            "display_path": p.name, "is_normalized": True,
        }
    enl = find_enl(p)
    opened = make_shadow(enl, workspace)
    con = open_enl_readonly(opened, immutable=True)
    data_dir = enl.parent / (enl.stem + ".Data")
    refs = parse_refs(con, data_dir if data_dir.exists() else None)
    con.close()
    return refs, {
        "source": "enl", "source_label": SOURCE_LABELS["enl"],
        "display_path": enl.name, "is_normalized": False,
    }


# ── 语料构造 ────────────────────────────────────────────────
def build_corpus(refs: list["Ref"], mode: str = "hybrid",
                 alias_map: dict | None = None) -> list[str]:
    """构造聚类语料。

    mode 三选一（实测 Calinski-Harabasz 可分性，K=12）：
        'hybrid' （默认）关键词为主 + 摘要兜底   CH≈8.1
        'title'  标题 + 摘要 + 关键词（加权）    CH≈6.7
        'keyword' 纯关键词                       CH≈8.0

    'hybrid' 的依据：关键词是研究者手工标注的核心概念，不含摘要的
    行文噪声，实测可分性显著高于含摘要口径。
    但纯关键词有个致命短板：实测中文文献的 EndNote 关键词大量缺失，
    直接用纯关键词会让最大两簇退化为 study/between/when/research/how
    这类英文虚词。因此：
        有关键词的（4004篇）→ 以关键词为主信号，摘要仅作轻量补充
        无关键词的（1554 篇）→ 靠标题 + 摘要兜底，绝不丢弃

    v1.0.0 —— 聚类端中英归一：
        关键词字段先过 `alias_map` 做**确定性术语归一**
        （job crafting→工作重塑、work engagement→工作投入），
        让中英同义关键词在特征空间是同一个词。
        不修这一层时，中文文献聚成「工作重塑」簇、英文文献聚成
        「job crafting」簇 —— 同一概念被拆成两个主题。
        只做别名表精确映射，不做模糊语义合并（避免误并）。
    """
    def _norm_kw(kws):
        if not alias_map:
            return list(kws)
        out = []
        for w in kws:
            m = alias_map.get(str(w).strip().lower())
            out.append(m["canonical"] if m else w)
        return out

    out = []
    for r in refs:
        kws = _norm_kw(r.keywords or [])
        if mode == "keyword":
            out.append(" ".join(kws))
        elif mode == "title":
            out.append(
                (r.title + " ") * 3 + r.abstract + " " + " ".join(kws * 2)
            )
        else:  # hybrid
            if kws:
                # 关键词主导：关键词 ×3，标题 ×1，摘要仅取 120 字作背景
                out.append(
                    " ".join(kws * 3)
                    + " "
                    + r.title
                    + " "
                    + r.abstract[:120]
                )
            else:
                # 无关键词兜底：标题 ×3 + 摘要（此时摘要/标题是唯一信号）
                out.append((r.title + " ") * 3 + r.abstract)
    return out


def tokenize_factory(jieba_mod=None, *, domain_terms=None, alias_map=None):
    """中英分流分词。

    实测：英文占 75.1%（4175篇），令其过中文分词器纯浪费——
    全部过 jieba 需 4.10s，分流后仅 1.47s。

    domain_terms: 本领域术语表（Counter 或词序列）。传入后这些词会被
        注册进 jieba，避免「工作重塑」这类完整术语被切成
        「工作」+「重塑」。为 None 时行为与原来完全一致。

    alias_map (v1.0.0)：分词后再做一次**别名归一**。摘要/标题里的
        "job crafting" 会被英文分流切成 ['job','crafting'] 两个碎片，
        关键词字段的别名映射（build_corpus 层）管不到它们。
        这里在 token 序列上滑窗匹配别名词（含多词别名），把
        ['job','crafting']→['工作重塑']，让摘要端的中英同义词也归一。
        单词别名（job satisfaction→工作满意度 的 satisfaction 部分）
        不会误伤——只替换完整匹配的别名串。
    """
    _jieba = jieba_mod
    if _jieba is not None and domain_terms:
        try:
            from domain_dict import apply_to_jieba as _apply
            _apply(_jieba, domain_terms if hasattr(domain_terms, "items")
                   else Counter(domain_terms))
        except Exception:
            # 词典增强失败不得让主流程失败——退回原有分词行为即可，
            # 碎片化只是效果变差，不会产生错误结论。
            pass

    def tok(s: str) -> list[str]:
        """中英分流 + 混合词拆解。

        不可直接按空格切后就丢弃非纯英文词 —— 实测边界失败：
            '员工performance' → ['员工']        （丢掉 performance）
            'COVID-19疫情'    → ['疫情']        （丢掉 COVID-19）
            '研究1'          → []                （整词丢失）
        这些在组织行为学语料里是真实形态（员工绩效、AI 话题编号）。

        策略：先按空格切词，再对每个词按「英文段 / 中日韩段 / 数字」拆分，
        英文段走停用词、中文段交 jieba。
        """
        out: list[str] = []
        for w in s.split():
            w = w.strip()
            if not w:
                continue
            if not _CJK.search(w):
                # 纯拉丁串：走英文停用词
                lw = w.lower()
                if re.match(r"^[a-z][a-z\-']*[0-9]*$", lw) and lw not in STOP_EN and len(lw) >= 2:
                    out.append(lw)
                continue
            # 含中文：拆成 [拉丁段][中文段][拉丁段] 三部分
            parts = re.findall(r"[A-Za-z][A-Za-z\-']*[0-9]*|[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]+", w)
            for pt in parts:
                if _CJK.search(pt):
                    if _jieba is not None:
                        for t in _jieba.cut(pt):
                            t = t.strip()
                            if len(t) >= 2 and t not in STOP_ZH and _CJK.search(t):
                                out.append(t)
                else:
                    lp = pt.lower()
                    if lp not in STOP_EN and len(lp) >= 2:
                        out.append(lp)
        # v1.0.0：分词后别名归一（滑窗匹配多词别名 → 规范名单 token）
        if alias_map and out:
            out = _apply_aliases_on_tokens(out, alias_map)
        return out

    return tok


def _apply_aliases_on_tokens(tokens: list, alias_map: dict) -> list:
    """在 token 序列上滑窗，把匹配别名的连续 token 折叠成规范名。

    例：['job','crafting'] 命中别名 'job crafting' → ['工作重塑']。
    单词别名（'burnout'→'职业倦怠'）退化为逐 token 查表。
    只替换**完整且最长**的匹配（先 3 词窗、再 2 词、再单词），
    避免 'job' 被单独换成某规范名而留下 'crafting' 孤儿。
    """
    # 预建：按词数分桶的别名查询（小写别名串 → 规范名）
    uni, bi, tri = {}, {}, {}
    for alias, m in alias_map.items():
        canon = m["canonical"]
        n = len(alias.split())
        if n == 1:
            uni[alias] = canon
        elif n == 2:
            bi[alias] = canon
        else:
            tri[alias] = canon
    low = [str(t).lower() for t in tokens]
    out, i, n = [], 0, len(tokens)
    while i < n:
        if i + 3 <= n and " ".join(low[i:i + 3]) in tri:
            out.append(tri[" ".join(low[i:i + 3])]); i += 3; continue
        if i + 2 <= n and " ".join(low[i:i + 2]) in bi:
            out.append(bi[" ".join(low[i:i + 2])]); i += 2; continue
        if low[i] in uni:
            out.append(uni[low[i]]); i += 1; continue
        out.append(tokens[i]); i += 1
    return out


# ── 覆盖诊断（零静默丢弃的证据）────────────────────────────
def coverage_report(refs: list[Ref], con: sqlite3.Connection | None = None) -> dict:
    t = Counter(r.tier for r in refs)
    total = len(refs)
    years = [r.year for r in refs if r.year]
    kw_docs = sum(1 for r in refs if r.keywords)
    rep = {
        "total": total,
        "tier": {
            "primary_abs": t["primary_abs"],
            "primary_kw": t["primary_kw"],
            "fallback_title": t["fallback_title"],
            "empty": t["empty"],
        },
        "tier_labels": TIER_LABELS,
        "zero_drop_identity": t["primary_abs"] + t["primary_kw"] + t["fallback_title"] + t["empty"] == total,
        "no_abstract": sum(1 for r in refs if not r.abstract),
        "no_keywords": total - kw_docs,
        "keyword_coverage_pct": round(kw_docs / total * 100, 1) if total else 0.0,
        "has_pdf": sum(1 for r in refs if r.has_pdf),
        "with_doi": sum(1 for r in refs if r.doi),
        "year_min": min(years) if years else None,
        "year_max": max(years) if years else None,
        "pre_2015": sum(1 for y in years if y < 2015),
        "zh_docs": sum(1 for r in refs if is_cjk(r.title) or is_cjk(r.abstract)),
    }
    rep["zh_pct"] = round(rep["zh_docs"] / total * 100, 1) if total else 0.0
    return rep


def emit(obj: dict) -> None:
    """stdout 只输出 JSON，日志全走 stderr（Agent 契约）。"""
    json.dump(obj, sys.stdout, ensure_ascii=False, indent=2, default=str)
    sys.stdout.write("\n")
