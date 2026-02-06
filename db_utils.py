import logging
import os
from functools import lru_cache
from typing import Any, Dict, Iterable, Optional, Tuple, Union

from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)


def _base_dir() -> str:
    return os.path.dirname(os.path.abspath(__file__))


def _sqlite_url(db_file: str) -> str:
    # SQLAlchemy expects forward slashes for sqlite file URLs.
    db_file_abs = os.path.abspath(db_file)
    return "sqlite:///" + db_file_abs.replace("\\", "/")


def get_database_url(*, default_sqlite_db_file: str) -> str:
    url = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DATABASE_URL")
    if url:
        url = url.strip()
        # Heroku-style URLs sometimes come as postgres://
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://") :]
        
        # fix: Supabase Transaction Pooler (6543) often times out on some networks (like Render).
        # For a standard Flask app (persistent server), Session mode (5432) is preferred and more stable.
        if "supabase.com" in url and ":6543" in url:
            url = url.replace(":6543", ":5432")

        return url

    return _sqlite_url(default_sqlite_db_file)


def is_postgres_url(url: str) -> bool:
    u = (url or "").lower()
    return u.startswith("postgresql://") or u.startswith("postgres://")


@lru_cache(maxsize=8)
def get_engine(database_url: str):
    connect_args: Dict[str, Any] = {}

    # Supabase commonly requires SSL.
    if is_postgres_url(database_url):
        sslmode = os.getenv("DB_SSLMODE", "require").strip().lower()
        # psycopg2 expects sslmode in connect_args.
        connect_args["sslmode"] = sslmode
        # Add connection timeout to fail fast if network is bad
        connect_args["connect_timeout"] = 10
    else:
        # SQLite is often used locally; allow connections to be used across threads
        # (gunicorn gthread workers, etc.).
        connect_args["check_same_thread"] = False

    return create_engine(
        database_url,
        pool_pre_ping=True,
        pool_size=10,        # Default is 5. Increase for production.
        max_overflow=20,     # Allow more temporary connections.
        pool_recycle=1800,   # Recycle connections every 30 mins to avoid stale connections.
        future=True,
        connect_args=connect_args,
    )


ParamsType = Union[None, Dict[str, Any], Tuple[Any, ...], Iterable[Any]]


def _adapt_qmark_params(sql: str, params: ParamsType) -> Tuple[str, Dict[str, Any]]:
    if params is None:
        return sql, {}

    if isinstance(params, dict):
        return sql, params

    if isinstance(params, tuple):
        seq = list(params)
    else:
        seq = list(params)

    bind: Dict[str, Any] = {}
    out = []
    idx = 0
    for ch in sql:
        if ch == "?":
            key = f"p{idx}"
            out.append(f":{key}")
            bind[key] = seq[idx]
            idx += 1
        else:
            out.append(ch)

    return "".join(out), bind


class DBConn:
    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql: str, params: ParamsType = None):
        adapted_sql, bind = _adapt_qmark_params(sql, params)
        return self._conn.execute(text(adapted_sql), bind).mappings()

    def commit(self) -> None:
        self._conn.commit()

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception as e:
            # If the underlying connection is already broken (e.g. intermittent SSL/network issues),
            # SQLAlchemy may raise while rolling back/closing. Don't let cleanup mask the real error.
            logger.warning("DB connection close failed: %s", e)


def connect(*, default_sqlite_db_file: str) -> DBConn:
    url = get_database_url(default_sqlite_db_file=default_sqlite_db_file)
    engine = get_engine(url)
    return DBConn(engine.connect())


def init_schema(*, default_sqlite_db_file: str) -> None:
    url = get_database_url(default_sqlite_db_file=default_sqlite_db_file)
    postgres = is_postgres_url(url)

    conn = connect(default_sqlite_db_file=default_sqlite_db_file)
    try:
        if postgres:
            # Postgres: use BIGSERIAL for autoincrement ids.
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sale_orders (
                    id BIGSERIAL PRIMARY KEY,
                    username TEXT,
                    dealer_name TEXT,
                    city TEXT,
                    order_id TEXT,
                    report_name TEXT,
                    generated_at TEXT,
                    order_type TEXT DEFAULT 'new'
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS order_id_views (
                    id BIGSERIAL PRIMARY KEY,
                    username TEXT,
                    order_id TEXT,
                    viewed_at TEXT,
                    ip TEXT,
                    user_agent TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS issued_order_ids (
                    id BIGSERIAL PRIMARY KEY,
                    order_id TEXT UNIQUE,
                    given_to_name TEXT,
                    dealer_name TEXT,
                    city TEXT,
                    given_by_user TEXT,
                    given_at TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS counters (
                    month_year TEXT PRIMARY KEY,
                    counter INTEGER
                )
                """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS active_sessions (
                    username TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    issued_at TEXT,
                    ip TEXT,
                    user_agent TEXT
                )
                """
            )
        else:
            # SQLite: keep INTEGER PRIMARY KEY.
            conn.execute(
                "CREATE TABLE IF NOT EXISTS sale_orders (id INTEGER PRIMARY KEY,username TEXT,dealer_name TEXT,city TEXT,order_id TEXT,report_name TEXT,generated_at TEXT,order_type TEXT DEFAULT 'new')"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS order_id_views (id INTEGER PRIMARY KEY,username TEXT,order_id TEXT,viewed_at TEXT,ip TEXT,user_agent TEXT)"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS issued_order_ids (id INTEGER PRIMARY KEY,order_id TEXT UNIQUE,given_to_name TEXT,dealer_name TEXT,city TEXT,given_by_user TEXT,given_at TEXT)"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS counters (month_year TEXT PRIMARY KEY,counter INTEGER)"
            )

            conn.execute(
                "CREATE TABLE IF NOT EXISTS active_sessions (username TEXT PRIMARY KEY,session_id TEXT NOT NULL,issued_at TEXT,ip TEXT,user_agent TEXT)"
            )

        conn.commit()
    finally:
        conn.close()
