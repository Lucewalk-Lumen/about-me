"""关键词字段整词优先，标题/摘要切词兜底（语料自适应分词）。

## 为什么要区分两条路

实测真实中文文献库（CNKI 500 篇、2269 个关键词）发现，**统一切词会破坏完整术语**：

    工作重塑   -> ['工作', '重塑']      （出现 375 次，全部切碎）
    趋近导向   -> ['趋近', '导向']
    组织支持感 -> ['组织', '支持', '感']
    员工创新行为 -> ['员工', '创新', '行为']

1010 种关键词（占 44.5%）被切成碎片——这不是个别现象，而是通用分词器与
专业语料的领域错配。

**关键观察**：题录里的「关键词」字段本身就是作者/数据库给定的**完整术语**，
已由人工确认过语义，再切一遍纯属倒退。切词只对**没有现成术语**的文本
（标题、摘要）才有意义。

因此本模块采取两条路：

1. **关键词字段 → 整词保留**（标点分号已由解析层拆好），仅剔除停用词与
   过短碎片；不做任何再切分。
2. **标题 / 摘要 → 切词**，但先用语料自适应词典兜底：把本领域高频术语
   注册进分词器，避免「工作重塑」这类被切碎。

两条路的术语汇入同一份词频表，供下游聚类与网络使用。

## 用户自建词典

`load_user_dict` 支持用户放置 `user_dict.txt`（每行一词）补充领域外专有名词
（如自造概念、机构简称），无需修改本包。
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

MIN_WORD_LEN = 2
MAX_N = 8
MIN_FREQ = 4          # 只把反复出现的关键词固化为术语（≥4 次），罕见长复合词退回分词器

# 中文虚词/切词标记字符：学术术语不应含这些字。
# 用于否决跨词边界的 n-gram 垃圾（「的影」「响研」「塑的」）。
VIRTUAL_CHARS = set("的了和与及或在从对之其以为被将把所而且则但却也很更最不没无就才都还再又只即等个种些该此下中内外前后上下时个这那有使让给向由至则若如")


def _is_clean_term(w: str) -> bool:
    """是否是一个可整词保留的术语。

    要求：纯中文（或含拉丁字母的混合词如 COVID-19）、长度达标、不含标点。
    """
    if len(w) < MIN_WORD_LEN:
        return False
    return bool(re.fullmatch(r"[一-鿿぀-ヿ가-힯A-Za-z][一-鿿぀-ヿ가-힯A-Za-z0-9\-'.%]*", w))


def split_keyword_field(raw: str | list[str]) -> list[str]:
    """把题录的关键词字段拆成**整词**列表（不再切分）。

    CNKI 的 `%K` 字段用分号分隔；EndNote/GB7714 可能用逗号、分号或换行。
    这里只做分隔符拆分与清洗，**保留每个词的完整形态**。
    """
    if raw is None:
        return []
    items: list[str] = []
    parts = raw if isinstance(raw, list) else re.split(r"[;；,，\n\r]+", str(raw))
    for p in parts:
        w = str(p).strip().strip(".")
        if w and _is_clean_term(w):
            items.append(w)
    return items


def mine_phrases(phrases: list[str], *, min_freq: int = MIN_FREQ,
                 stopwords: set[str] | None = None) -> Counter:
    """统计关键词原串频次——这些就是本领域的稳定术语，无需切分。

    min_freq 门槛的作用：只把**反复出现**的关键词注册为术语。
    低频词（多为某篇论文的偶发表述，如只出现 1 次的「护士工作重塑」）
    不注册，让它退回分词器切分——否则一个罕见的长复合词会因拿到
    高权重而主导整个主题词，语义反而被扭曲。
    """
    stop = stopwords or set()
    c: Counter = Counter()
    for p in phrases:
        if not p or p in stop:
            continue
        if MIN_WORD_LEN <= len(p) <= MAX_N:
            c[p] += 1
    return Counter({w: f for w, f in c.items() if f >= min_freq})


def mine_ngrams(texts: list[str], *, max_n: int = MAX_N,
                min_freq: int = 8,
                stopwords: set[str] | None = None) -> Counter:
    """从标题/摘要等自由文本挖掘 n-gram 候选（供切词兜底用）。

    !!! 重要：本函数默认**不启用**（见 build_domain_dict 的enable_ngrams）。
    原因：自由文本里的 n-gram 极易跨越词边界，实测会产出
    「响机制」「机制研」「工工」这类碎片；一旦注册进分词器，
    反而把原本正确的「影响机制」切错——**固化的错误比不处理更糟**。
    标题/摘要的切词交回分词器原行为（宁可碎片，也不制造错误）。

    保留本函数是为了给「已人工确认的领域词表」留出挂载点：若用户通过
    user_dict.txt 提供确定无误的术语，无需依赖本函数。
    """
    stop = stopwords or set()
    grams: Counter = Counter()
    ngrams: Counter = Counter()
    for s in texts:
        if not s:
            continue
        for run in re.findall(r"[一-鿿]{%d,}" % MIN_WORD_LEN, s):
            L = len(run)
            for n in range(2, min(max_n, L) + 1):
                for i in range(L - n + 1):
                    grams[run[i : i + n]] += 1
                    if n >= 3:
                        ngrams[run[i : i + n]] += 1

    out: Counter = Counter()
    for g, f in ngrams.items():
        if f < min_freq or g in stop:
            continue
        # 三重校验，任一不满足即否决
        head, tail = g[:-1], g[1:]
        if head and grams.get(head, 0) > f * 2:
            continue
        if tail and grams.get(tail, 0) > f * 2:
            continue
        if any(ch in VIRTUAL_CHARS for ch in g):
            continue
        if grams.get(g[0], 0) > f * 2 or grams.get(g[-1], 0) > f * 2:
            continue
        out[g] += f
    return out


def build_domain_dict(refs, *, jieba_mod=None, stopwords: set[str] | None = None,
                      user_dict: str | Path | None = None,
                      enable_ngrams: bool = False) -> dict:
    """构建本领域术语表并注册进分词器。

    参数
    ----
    refs:      题录列表（需含 keywords / title 字段）
    jieba_mod: jieba 模块；为 None 时只返回词表不注册
    stopwords: 中文停用词表
    user_dict: 用户自建词典路径（每行一词）
    enable_ngrams:是否从标题/摘要挖 n-gram。**默认 False**（见
                   mine_ngrams 的说明：跨词边界碎片会固化错误）。

    返回
    ----
    dict: {terms: Counter, registered: int, from_keywords: int,
           from_user: int, ngrams: int}
    """
    phrases: list[str] = []
    texts: list[str] = []
    for r in refs:
        kw = getattr(r, "keywords", None) or []
        if isinstance(kw, str):
            kw = split_keyword_field(kw)
        else:
            kw = [x for x in kw if x]
        phrases.extend(kw)
        t = getattr(r, "title", None)
        if t:
            texts.append(t)

    kw_terms = mine_phrases(phrases, stopwords=stopwords)
    ng_terms = mine_ngrams(texts, stopwords=stopwords) if enable_ngrams else Counter()
    user_terms = load_user_dict(user_dict) if user_dict else []
    user_counter = Counter({w: 10 ** 6 for w in user_terms})  # 用户词最高优先

    terms = kw_terms + ng_terms + user_counter
    registered = apply_to_jieba(jieba_mod, terms)
    return {
        "terms": terms,
        "registered": registered,
        "from_keywords": len(kw_terms),
        "from_ngrams": len(ng_terms),
        "from_user": len(user_terms),
    }


def apply_to_jieba(jieba_mod, terms: Counter, *, freq_base: int = 2000) -> int:
    """把术语注册进分词器。返回注册词数。

    权重按**真实频次缩放**（freq = freq_base + 频次 × 50），而非所有词
    一律用同一高值。若一律同权，jieba 会把罕见长复合词与高频核心术语
    等同看待，反而让低频词主导切分结果。
    """
    if jieba_mod is None or not terms:
        return 0
    n = 0
    for t, f in terms.items():
        if not t or len(t) < MIN_WORD_LEN:
            continue
        try:
            jieba_mod.add_word(t, freq=freq_base + int(f) * 50)
            n += 1
        except Exception:
            continue
    return n


def load_user_dict(path: str | Path) -> list[str]:
    """读取用户自定义词典（每行一词，可选频次）。文件不存在返回空列表。

    用户可补充领域外专有名词，无需改包。
    """
    p = Path(path)
    if not p.exists():
        return []
    words: list[str] = []
    try:
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            w = line.split()[0]
            if w and _is_clean_term(w):
                words.append(w)
    except Exception:
        return words
    return words