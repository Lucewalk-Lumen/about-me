# -*- coding: utf-8 -*-
"""资产库共享读写：胶囊库加载、净化、结构校验、索引渲染。

被 query_capsules.py / share_capsules.py / restore_backup.py 复用，
避免多处各自实现同一口径（加载形态、净化范围、索引格式）而导致漂移。

只依赖 Python 标准库。本模块不是命令行工具，直接运行时只打印用法。
"""
from __future__ import annotations

import json
import hashlib
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

TZ8 = timezone(timedelta(hours=8))

# 胶囊的标识字段：缺失即**结构错误**（阻断），六段正文单独校验
REQUIRED_FIELDS = ("id", "type", "source", "src", "source_quote", "summary", "tags")

# 缺失只算**提示**（不阻断）的字段。
# `src` 是"原生记录指针"，指向**蒸馏者自己本地的**记录；
# 接收他人分发包时该指针按设计已被净化剥离（见 share_capsules.py 的 sanitize 分支），
# 因此它的缺失不代表结构损坏——否则分发包 README 承诺的「--check 应报结构校验通过」就是假的。
# 「引用保真」的强制力由 source（可追溯出处）与 source_quote（原文摘录）承载，两者仍是硬错误。
NOTICE_FIELDS = ("src",)
SECTIONS = ("R", "I", "A1", "A2", "E", "B")

# 索引文件生成标记：带此标记表示"可安全重建"，避免覆盖人工整理的内容
INDEX_MARK = "<!-- generated-by: distill assets_lib.render_index -->"

# 与 agents/distill.md Stage 3「危险命令扫描模式」逐条对应
DANGEROUS_PATTERNS = [
    (r"rm\s+-rf", "rm -rf（递归强制删除，无确认）"),
    (r"curl\s+[^|]*\|\s*(sh|bash)", "curl 管道接 sh（远程脚本直执行，不验证）"),
    (r"base64\s+-d[^\n]*\|\s*(exec|sh)", "base64 解码后管道接 exec（编码后命令执行，隐蔽注入）"),
    (r"(^|[^A-Za-z0-9_])eval\s*\(", "eval（字符串二次求值，注入面）"),
    (r"os\.system\s*\(", "os 模块的 system 调用（Python 系统调用，不捕获子进程错误）"),
]


# --------------------------------------------------------------------------- 加载
def parse_capsules_payload(obj) -> list:
    """把落盘内容归一成"胶囊列表"。

    兼容两种形态：① 直接是数组；② 外层是对象（取 capsules / items / data 之一）。
    形态不对时抛 ValueError，由调用方决定怎么报错。
    """
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        for k in ("capsules", "items", "data"):
            v = obj.get(k)
            if isinstance(v, list):
                return v
        raise ValueError("胶囊库是对象，但没有 capsules / items / data 数组字段")
    raise ValueError("胶囊库既不是数组也不是对象（实为 %s）" % type(obj).__name__)


def parse_capsules_text(text: str) -> list:
    return parse_capsules_payload(json.loads(text))


def load_capsules(assets_dir: Path):
    """读资产库下的 capsules/capsules.json，返回 (列表, 路径)。"""
    p = Path(assets_dir).expanduser() / "capsules" / "capsules.json"
    if not p.is_file():
        raise FileNotFoundError(p)
    return parse_capsules_text(p.read_text(encoding="utf-8")), p


# --------------------------------------------------------------------------- 字段
def step_text(capsule: dict) -> str:
    """把 E 段（可执行步骤）归一成文本。

    E 段允许是字符串、字符串数组，或 {"1": "...", "2": "..."} 这类映射；
    统一拼成文本后再做危险命令扫描，避免因类型不同而漏扫或崩溃。
    """
    e = capsule.get("E", "")
    if e is None:
        return ""
    if isinstance(e, str):
        return e
    if isinstance(e, (list, tuple)):
        parts = []
        for i, item in enumerate(e, 1):
            parts.append(_flatten(item, i))
        return "\n".join(parts)
    if isinstance(e, dict):
        parts = []
        for k in sorted(e, key=lambda x: str(x)):
            parts.append(_flatten(e[k], k))
        return "\n".join(parts)
    return str(e)


def _flatten(item, key) -> str:
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        return " ".join(str(v) for v in item.values())
    return str(item)


def _tag_text(capsule: dict) -> str:
    t = capsule.get("tags", "")
    if isinstance(t, (list, tuple)):
        return "、".join(str(x) for x in t)
    return str(t or "")


def _field_text(capsule: dict, key: str) -> str:
    v = capsule.get(key, "")
    if key == "tags":
        return _tag_text(capsule)
    if key == "E":
        return step_text(capsule)
    if isinstance(v, (list, tuple)):
        return " ".join(str(x) for x in v)
    if isinstance(v, dict):
        return " ".join(str(x) for x in v.values())
    return str(v or "")


def first_line(capsule: dict, limit: int = 60) -> str:
    """取一句话摘要：优先 summary，退化到 I 段首句。"""
    s = _field_text(capsule, "summary").strip()
    if not s:
        s = _field_text(capsule, "I").strip()
    s = re.sub(r"\s+", " ", s)
    return s if len(s) <= limit else s[: limit - 1] + "…"


# --------------------------------------------------------------------------- 净化
def sanitize_capsules(capsules: list) -> list:
    """净化：剥离私密指针字段。

    只剥离指向个人任务记录的指针（src），不碰 source（作者 / 机构 / 链接）
    与任何角色署名——引用保真优先于净化。
    """
    return [{k: v for k, v in c.items() if k != "src"} for c in capsules]


def scan_dangerous(capsules: list):
    """扫描每条资产 E 段的危险命令模式，返回 [(id, label), ...]。"""
    hits = []
    for c in capsules:
        txt = step_text(c)
        cid = c.get("id", "?")
        for pat, label in DANGEROUS_PATTERNS:
            if re.search(pat, txt):
                hits.append((cid, label))
    return hits


# --------------------------------------------------------------------------- 校验
def validate_capsules_report(capsules: list):
    """结构校验，返回 (errors, notices)。

    * errors  —— 结构损坏，必须阻断（缺 id/type/source/source_quote/summary/tags、
                 六段正文缺失、E 段不可解析、id 重复、tags 类型错）。
    * notices —— 不阻断的提示。目前只有一项：缺 `src`（原生记录指针）。
                 首次蒸馏的产物应当补上它；**接收到的分发包缺 `src` 属正常**，
                 因为该字段按设计已在净化时剥离。

    分级的理由：`src` 指向蒸馏者**本地**的记录，是"本地可追溯性"字段，
    而非内容完整性字段；把它当结构错误会误伤所有分发件。
    引用保真的强制力由 `source` / `source_quote` 承载，两者仍在 errors 里。
    """
    errors = []
    notices = []
    seen = {}
    missing_src = 0
    for i, c in enumerate(capsules):
        where = "第 %d 条" % (i + 1)
        if not isinstance(c, dict):
            errors.append("%s 不是对象（%s）" % (where, type(c).__name__))
            continue
        cid = c.get("id")
        if not isinstance(cid, str) or not cid.strip():
            errors.append("%s 缺 id 或 id 非字符串" % where)
        else:
            if cid in seen:
                errors.append("id 重复：%s（第 %d 条与第 %d 条）" % (cid, seen[cid], i + 1))
            seen[cid] = i + 1
            where = cid
        for f in REQUIRED_FIELDS:
            if f in NOTICE_FIELDS:
                if f not in c or c[f] in (None, "", [], {}):
                    missing_src += 1
                continue
            if f not in c:
                errors.append("%s 缺字段 %s" % (where, f))
            elif c[f] in (None, "", [], {}):
                errors.append("%s 字段 %s 为空" % (where, f))
        st = step_text(c)
        if not st.strip():
            errors.append("%s 的 E 段（可执行步骤）为空或无法解析为文本" % where)
        for s in SECTIONS:
            if s not in c:
                errors.append("%s 缺正文段 %s" % (where, s))
        if "tags" in c and not isinstance(c["tags"], (list, str)):
            errors.append("%s 的 tags 既不是数组也不是字符串" % where)
    if missing_src:
        notices.append(
            "%d 条缺 src（原生记录指针）：首次蒸馏的产物应补上；"
            "若这些胶囊来自他人分发包，则属正常（净化已按设计剥离该指针）" % missing_src)
    return errors, notices


def validate_capsules(capsules: list):
    """结构校验，返回**错误**清单（空列表 = 通过）。不做语义与质量判断。

    兼容入口：只看 errors。需要区分"错误 / 提示"时用 validate_capsules_report。
    """
    return validate_capsules_report(capsules)[0]


# --------------------------------------------------------------------------- 索引
def _cell(s: str) -> str:
    return re.sub(r"\s+", " ", str(s or "")).replace("|", "\\|").strip()


def render_index(capsules: list, source_note: str = "") -> str:
    """由胶囊列表渲染检索索引（确定性输出，不含 src 指针）。

    顶部写清用途、底部附检索/重建/隐私用法，让拿到索引的人一眼就懂这是什么、怎么用。
    """
    now = datetime.now(TZ8).strftime("%Y-%m-%d %H:%M:%S")
    out = [INDEX_MARK, "# 蒸馏资产索引", ""]
    out.append("> 这是**蒸馏师（甄澄）**每次入库后自动生成的「资产检索索引」，用来快速浏览和检索你沉淀的可复用操作资产。")
    out.append("> 共 %d 条 · 生成于 %s (+08:00)" % (len(capsules), now))
    if source_note:
        out.append("> %s" % source_note)
    out.append("> 本文件由脚本生成，请勿手改；重建：`python3 bin/query_capsules.py --rebuild-index`")
    out.append("> 索引只放可复用做法的摘要（一句话 + 何时用 + 出处 + 标签），**不含**指向你本机任务记录的 `src` 私密指针。")
    out.append("")

    groups = (("capsule", "流程包（capsule）"), ("gene", "操作模式（gene）"))
    other = []
    for kind, title in groups:
        rows = [c for c in capsules if str(c.get("type", "")).lower() == kind]
        out.append("## %s" % title)
        out.append("")
        if not rows:
            out.append("（暂无）")
            out.append("")
            continue
        out.append("| id | 一句话 | 何时用（触发信号） | 出处 | 标签 |")
        out.append("|---|---|---|---|---|")
        for c in rows:
            out.append("| %s | %s | %s | %s | %s |" % (
                _cell(c.get("id")), _cell(first_line(c)), _cell(_field_text(c, "A2")),
                _cell(_field_text(c, "source")), _cell(_tag_text(c))))
        out.append("")
    for c in capsules:
        if str(c.get("type", "")).lower() not in ("capsule", "gene"):
            other.append(c)
    if other:
        out.append("## 其它类型")
        out.append("")
        out.append("| id | 类型 | 一句话 | 出处 | 标签 |")
        out.append("|---|---|---|---|---|")
        for c in other:
            out.append("| %s | %s | %s | %s | %s |" % (
                _cell(c.get("id")), _cell(c.get("type")), _cell(first_line(c)),
                _cell(_field_text(c, "source")), _cell(_tag_text(c))))
        out.append("")
    out.append("---")
    out.append("")
    out.append("### 怎么用这个索引")
    out.append("")
    out.append("- **人读**：直接看上方表格，按「何时用（触发信号）」判断哪条适合当前任务。")
    out.append("- **检索**：`python3 bin/query_capsules.py <关键词>` 按关键词 / 触发信号 / 标签检索；`--id <id>` 看某条全文（R/I/A1/A2/E/B 六段）。")
    out.append("- **重建**：资产有增删后跑一次 `--rebuild-index` 即可刷新本文件；即使删掉也无妨，下次入库会自动重建。")
    out.append("- **隐私**：本索引不写入 `src` 指针，可放心留存或随分发包外发（分发包内的索引由接收方内容现场生成）。")
    out.append("")
    return "\n".join(out)


def write_index(path: Path, text: str, force: bool = False):
    """写索引。若目标已存在且**不带生成标记**，默认不覆盖（避免毁掉人工整理的内容）。"""
    path = Path(path)
    if path.exists() and not force:
        try:
            head = path.read_text(encoding="utf-8")[:400]
        except OSError:
            head = ""
        if INDEX_MARK not in head:
            return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True


# --------------------------------------------------------------------------- 检索
WEIGHTS = (("A2", 3), ("tags", 2), ("summary", 2), ("id", 2),
           ("I", 1), ("R", 1), ("A1", 1), ("E", 1), ("B", 1), ("source", 1))


def search(capsules: list, keywords):
    """按关键词检索，返回 [(score, 命中说明, 胶囊), ...] 降序。

    打分只看命中位置与次数（可复现、可解释），不做模糊推断。
    """
    kws = [k.strip() for k in keywords if k and k.strip()]
    if not kws:
        return []
    scored = []
    for c in capsules:
        total, why = 0, []
        for kw in kws:
            low = kw.lower()
            for field, w in WEIGHTS:
                hay = _field_text(c, field).lower()
                n = hay.count(low)
                if n:
                    total += w * n
                    why.append("%s×%d@%s" % (kw, n, field))
        if total:
            scored.append((total, ", ".join(why), c))
    scored.sort(key=lambda x: (-x[0], str(x[2].get("id", ""))))
    return scored


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


if __name__ == "__main__":
    print(__doc__)
