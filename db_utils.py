import os
from functools import lru_cache
from typing import Any, Dict, Iterable, Optional, Tuple, Union

from sqlalchemy import create_engine, text


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

    return create_engine(
        database_url,
        pool_pre_ping=True,
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
        self._conn.close()


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
                    generated_at TEXT
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
        else:
            # SQLite: keep INTEGER PRIMARY KEY.
            conn.execute(
                "CREATE TABLE IF NOT EXISTS sale_orders (id INTEGER PRIMARY KEY,username TEXT,dealer_name TEXT,city TEXT,order_id TEXT,report_name TEXT,generated_at TEXT)"
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

        conn.commit()
    finally:
        conn.close()
