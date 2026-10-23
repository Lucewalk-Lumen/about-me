"""SQLite 唯一数据源接入层。

职责：
- 计算并暴露 ``DB_PATH``（可被环境变量 ``OBHRM_DB_PATH`` 覆盖；旧名 ``JOURNAL_DB_PATH`` 兼容回退）。
- ``get_conn``：获取连接（开启外键）。
- ``init_schema``：整库重建（DROP + CREATE），保证建库幂等。
- ``find_or_create_journal``：跨源去重注册核心刊。
- ``upsert_rating``：写入/更新某标准的某属性（依赖 UNIQUE 约束幂等）。
"""

from __future__ import annotations

import difflib
import os
import sqlite3
from datetime import datetime
from pathlib import Path

from .normalize import norm_issn, norm_title

# 当前 schema 版本。随 SCHEMA_SQL 结构演进自增；写入 meta.schema_version。
# 与包版本命名空间不同，二者不可混用。
SCHEMA_VERSION = 3

# 拒绝静默合并的标题相似度阈值：norm_issn 命中但归一化标题相似度低于此值，
# 视为不同刊，拒绝合并并显式报错，交由人工裁定。
MERGE_TITLE_SIMILARITY_THRESHOLD = 0.9


class MergeConflictError(Exception):
    """norm_issn 命中但标题差异过大，拒绝静默合并。

    调用方应捕获并按需提示用户人工裁定，而非忽略。
    """


class SchemaError(Exception):
    """数据库 schema 与期望不符（ 断言失败）。"""


# 技能包根目录（本文件向上三级）
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
# 期刊库已拆分为独立数据资产技能 journal-library；DB 真源位于同级兄弟技能
DEFAULT_DB_PATH = _PROJECT_ROOT / ".." / "journal-library" / "db" / "journals.db"

# 允许通过环境变量覆盖 DB 路径（Skill / API 共用同一文件）
# 统一变量名：OBHRM_DB_PATH；旧名 JOURNAL_DB_PATH 保留为兼容回退。
DB_PATH = Path(
    os.environ.get("OBHRM_DB_PATH") or os.environ.get("JOURNAL_DB_PATH") or str(DEFAULT_DB_PATH)
)

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS journals (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    title        TEXT,
    title_cn     TEXT,
    issn_print  TEXT,
    issn_e       TEXT,
    norm_issn    TEXT,
    norm_title   TEXT NOT NULL,
    publisher    TEXT,
    country      TEXT,
    language     TEXT,
    data_version TEXT NOT NULL DEFAULT '2025-2026',
    note         TEXT,
    created_at   TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at   TEXT NOT NULL DEFAULT (datetime('now')),
    subject_area TEXT,
    subfields    TEXT,
    jcr_abbr     TEXT,
    jcr_category TEXT
);
-- 应用层 + DB 层双保险，禁止重复 norm_issn 落入（碰撞由校验流程单独裁定）。
CREATE UNIQUE INDEX IF NOT EXISTS idx_norm_issn_unique ON journals(norm_issn)
    WHERE norm_issn IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_norm_issn   ON journals(norm_issn);
CREATE INDEX IF NOT EXISTS idx_norm_title  ON journals(norm_title);
CREATE INDEX IF NOT EXISTS idx_issn_print ON journals(issn_print);
CREATE INDEX IF NOT EXISTS idx_issn_e     ON journals(issn_e);

CREATE TABLE IF NOT EXISTS ratings (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    journal_id    INTEGER NOT NULL REFERENCES journals(id) ON DELETE CASCADE,
    standard      TEXT NOT NULL,
    attr          TEXT NOT NULL,
    value         TEXT,
    data_year     INTEGER,
    match_method  TEXT,
    confidence    TEXT,
    note          TEXT,
    UNIQUE (journal_id, standard, attr)
);
CREATE INDEX IF NOT EXISTS idx_ratings_journal  ON ratings(journal_id);
CREATE INDEX IF NOT EXISTS idx_ratings_standard ON ratings(standard);

CREATE TABLE IF NOT EXISTS journal_disciplines (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    journal_id   INTEGER NOT NULL REFERENCES journals(id) ON DELETE CASCADE,
    primary_code TEXT NOT NULL,
    subfield     TEXT,
    is_primary   INTEGER NOT NULL DEFAULT 0,
    is_featured  INTEGER NOT NULL DEFAULT 0,
    source       TEXT,
    UNIQUE (journal_id, primary_code)
);
CREATE INDEX IF NOT EXISTS idx_journal_disciplines_journal
    ON journal_disciplines(journal_id);

CREATE TABLE IF NOT EXISTS meta (
    k TEXT PRIMARY KEY,
    v TEXT
);
"""


def get_conn(db_path: Path | None = None, create: bool = False,
             assert_schema: bool = True) -> sqlite3.Connection:
    """获取 SQLite 连接并开启外键约束。

    ``create=False``（默认，查询侧）：数据库文件不存在时直接抛出
    ``OperationalError``（unable to open），由 query.py 捕获后输出降级话术，
    避免误建 0 字节空库、污染磁盘并使「数据库缺失」分支永远触发不到。
    ``create=True``（建库侧）：允许创建目录与新库，供 init_schema/导入使用。

    ``assert_schema``（默认 True，仅只读路径生效）：连接后断言核心表/列存在，
    否则抛 ``SchemaError``。新建库（create=True）跳过断言——其 schema
    由 ``init_schema`` 负责构建。
    """
    path = Path(db_path).resolve() if db_path else DB_PATH
    if create:
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(path))
    else:
        if not path.exists():
            # 只读模式下不自动建库，抛出可被上层翻译为友好话术的异常
            raise sqlite3.OperationalError(
                f"unable to open database file: {path}"
            )
        # 运行期只读：以 mode=ro 打开，兼容只读挂载（immutable / 只读文件系统），
        # 避免读写模式打开只读文件因无法加锁而失败（unable to open database file）。
        # 文件缺失已在上方拦截；uri=True + ?mode=ro 仅授予读权限。
        conn = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    if assert_schema and not create:
        _assert_schema(conn, path)
    return conn


# 只读路径必须存在的核心表（meta 表为惰性创建，不在此强制，
# 否则会对尚未建 meta 表的库误报 SchemaError）。
_REQUIRED_TABLES = ("journals", "ratings", "journal_disciplines")
_REQUIRED_COLUMNS = (
    ("journals", "norm_issn"),
    ("journals", "norm_title"),
    ("journals", "jcr_abbr"),
    ("journals", "jcr_category"),
)


def _assert_schema(conn: sqlite3.Connection, path: Path) -> None:
    """断言核心表/列存在。缺失即抛 ``SchemaError`` 而非静默继续。"""
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type IN ('table','view')")}
    missing_tables = [t for t in _REQUIRED_TABLES if t not in tables]
    if missing_tables:
        raise SchemaError(
            f"数据库 {path} 缺失表/视图: {missing_tables}；"
            f"请用 init_schema() 重建。")
    for table, col in _REQUIRED_COLUMNS:
        # 白名单式校验（与 _ALLOWED_COLS 同族）：table 虽来自内部常量，仍只接受合法标识符并加引号，杜绝注入面。
        if not isinstance(table, str) or not table.isidentifier():
            raise SchemaError(f"内部错误：非法表名 {table!r}")
        cols = {r[1] for r in conn.execute(f'PRAGMA table_info("{table}")')}
        if col not in cols:
            raise SchemaError(
                f"数据库 {path} 表 {table} 缺失列: {col}；schema 版本过旧，请迁移。")


def init_schema(conn: sqlite3.Connection) -> None:
    """整库重建：先 DROP 再 CREATE，确保幂等（重跑 = 干净重来）。"""
    conn.executescript(
        """
        DROP TABLE IF EXISTS ratings;
        DROP TABLE IF EXISTS journal_disciplines;
        DROP TABLE IF EXISTS journals;
        DROP TABLE IF EXISTS meta;
        """
    )
    conn.executescript(SCHEMA_SQL)
    # 记录 schema 版本，供迁移/兼容性判断。
    conn.execute(
        "INSERT OR REPLACE INTO meta(k, v) VALUES('schema_version', ?)",
        (str(SCHEMA_VERSION),),
    )
    conn.commit()


def _safe(v: object) -> str | None:
    """归一空值：None 与空白串统一为 None。

    注意：不再把字面量 "nan"/"none"/"null" 当作空值——它们可能是合法文本
    （如刊名、学科名），误归一会造成静默数据丢失。缺失值应由调用方显式传 None。
    """
    if v is None:
        return None
    s = str(v).strip()
    if s == "":
        return None
    return s


def _title_similarity(a: str, b: str) -> float:
    """归一化刊名相似度（0~1），基于词集合 Jaccard + 序列比对的综合值。

    用于  判定 norm_issn 命中后，新标题与既有标题是否「明显是同一刊」。
    """
    a, b = (norm_title(a), norm_title(b))
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    set_a, set_b = set(a.split()), set(b.split())
    if set_a and set_b:
        jaccard = len(set_a & set_b) / len(set_a | set_b)
    else:
        jaccard = 0.0
    seq = difflib.SequenceMatcher(None, a, b).ratio()
    # 取两者中较高者，避免「仅多一个词」被 Jaccard 低估。
    return max(jaccard, seq)


def find_or_create_journal(
    conn: sqlite3.Connection,
    title: str | None,
    issn: str | None = None,
    eissn: str | None = None,
    publisher: str | None = None,
    title_cn: str | None = None,
    country: str | None = None,
    language: str | None = None,
    note: str | None = None,
    create_if_missing: bool = True,
) -> int | None:
    """按 ISSN（优先）或归一化刊名查找/创建期刊，返回 journal id。

    匹配策略：
    1. norm_issn（print/eISSN 任一）命中 → 复用，必要时补全缺失字段。
    2. norm_title 命中且 publisher 不冲突 → 复用（同名合并）。
    3. norm_title 命中但 publisher 明显冲突 → 视为不同刊，新建（记 note）。
    4. 均未命中 → 新建。

    ``create_if_missing=False`` 时，仅返回已存在期刊 id，未命中返回 ``None``
    （供 AJG2024 等尽力解析场景避免产生脏数据）。
    """
    title = _safe(title)
    publisher = _safe(publisher)
    title_cn = _safe(title_cn)
    country = _safe(country)
    language = _safe(language)
    issn_n = norm_issn(issn) or norm_issn(eissn)
    ntitle = norm_title(title)
    # 至少要有刊名才能建刊
    if not title and not issn_n:
        return None

    cur = conn.cursor()

    # 1) 优先按 norm_issn 匹配
    if issn_n:
        row = cur.execute(
            "SELECT id, title, title_cn, publisher, issn_print, issn_e, "
            "country, language "
            "FROM journals WHERE norm_issn = ?",
            (issn_n,),
        ).fetchone()
        if row:
            # norm_issn 命中但标题差异过大 → 拒绝静默合并，显式报错。
            # 仅当既有标题与新标题都非空且相似度低于阈值时才拒绝；
            # 既有标题为空（仅补全字段）或高度相似则照常合并。
            existing_title = _safe(row["title"])
            if existing_title and ntitle:
                sim = _title_similarity(existing_title, ntitle)
                if sim < MERGE_TITLE_SIMILARITY_THRESHOLD:
                    raise MergeConflictError(
                        f"拒绝合并：norm_issn={issn_n} 命中期刊 id={row['id']}"
                        f"（既有标题「{existing_title}」），但新标题「{ntitle}」"
                        f"归一化相似度={sim:.3f} < 阈值"
                        f"{MERGE_TITLE_SIMILARITY_THRESHOLD}。疑似不同刊，"
                        f"请人工裁定（保留为独立行或显式合并）。"
                    )
            _merge_existing(conn, cur, row, title, publisher, title_cn,
                            country, language, issn, eissn, note)
            return int(row["id"])

    # 2) 按 norm_title 匹配
    if ntitle:
        rows = cur.execute(
            "SELECT id, title, title_cn, publisher, issn_print, issn_e, "
            "country, language "
            "FROM journals WHERE norm_title = ?",
            (ntitle,),
        ).fetchall()
        if rows:
            # 命中同名期刊：直接复用并补全缺失字段。
            # 说明：不同源 publisher 写法常不一致（如 "ACAD MANAGEMENT"
            # 与 "Academy of Management"），同名优先
            # 「合并展示」，不轻易拆分为新刊，以最大化跨源关联。
            row = rows[0]
            _merge_existing(conn, cur, row, title, publisher, title_cn,
                            country, language, issn, eissn, note)
            return int(row["id"])

    # 3) 未命中
    if not create_if_missing:
        return None
    return _insert_journal(conn, cur, title, issn, eissn, publisher,
                             title_cn, country, language, note)


def _merge_existing(conn, cur, row, title, publisher, title_cn,
                    country, language, issn, eissn, note):
    """对已有期刊补全更完整的信息（不覆盖已有非空值）。"""
    jid = int(row["id"])
    updates: dict[str, object] = {}
    if not _safe(row["title"]) and title:
        updates["title"] = title
    if not _safe(row["title_cn"]) and title_cn:
        updates["title_cn"] = title_cn
    if not _safe(row["publisher"]) and publisher:
        updates["publisher"] = publisher
    ip, ie = _safe(row["issn_print"]), _safe(row["issn_e"])
    if not ip and issn:
        updates["issn_print"] = issn
    if not ie and eissn:
        updates["issn_e"] = eissn
    if not _safe(row["country"]) and country:
        updates["country"] = country
    if not _safe(row["language"]) and language:
        updates["language"] = language
    if updates:
        # 列名白名单：当前键来自本函数固定字面量集合；
        # 白名单防止未来重构误将外部输入拼入列名。
        _ALLOWED_COLS = {
            "title", "title_cn", "publisher", "issn_print", "issn_e",
            "country", "language", "updated_at",
        }
        for k in updates:
            if k not in _ALLOWED_COLS:
                raise ValueError(f"非法的期刊字段名: {k}")
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        updates["updated_at"] = datetime.now().isoformat(timespec="seconds")
        set_clause += ", updated_at = ?"
        cur.execute(
            f"UPDATE journals SET {set_clause} WHERE id = ?",
            list(updates.values()) + [jid],
        )
        conn.commit()


def _insert_journal(conn, cur, title, issn, eissn, publisher,
                    title_cn, country, language, note) -> int:
    """插入新期刊记录。"""
    cur.execute(
        """
        INSERT INTO journals
            (title, title_cn, issn_print, issn_e, norm_issn, norm_title,
             publisher, country, language, note)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            title,
            title_cn,
            _safe(issn),
            _safe(eissn),
            norm_issn(issn) or norm_issn(eissn),
            norm_title(title),
            publisher,
            country,
            language,
            note,
        ),
    )
    conn.commit()
    return int(cur.lastrowid)


def upsert_rating(
    conn: sqlite3.Connection,
    journal_id: int,
    standard: str,
    attr: str,
    value: object,
    data_year: int | None = None,
    match_method: str = "issn",
    confidence: str = "high",
    note: str | None = None,
) -> None:
    """写入/更新一条评级（依赖 UNIQUE(journal_id, standard, attr) 幂等）。"""
    val = _safe(value)
    if val is None:
        return
    conn.execute(
        """
        INSERT INTO ratings
            (journal_id, standard, attr, value, data_year,
             match_method, confidence, note)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(journal_id, standard, attr) DO UPDATE SET
            value = excluded.value,
            data_year = excluded.data_year,
            match_method = excluded.match_method,
            confidence = excluded.confidence,
            note = excluded.note
        """,
        (journal_id, standard, attr, val, data_year,
         match_method, confidence, note),
    )
    conn.commit()


def set_meta(conn: sqlite3.Connection, key: str, value: str) -> None:
    """写入元信息键值。

    若 ``meta`` 表缺失（旧库未建），先建表再写，避免
    ``no such table: meta`` 静默失败。
    """
    conn.execute(
        "CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT)"
    )
    conn.execute(
        "INSERT INTO meta(k, v) VALUES(?, ?) "
        "ON CONFLICT(k) DO UPDATE SET v = excluded.v",
        (key, value),
    )
    conn.commit()
