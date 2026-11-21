"""
Database engine and per-request sessions.

Postgres (Supabase): psycopg 3 with a small pool, a connect timeout and a 5 s statement timeout so a
stuck query can't pin a worker. `prepare_threshold=None` disables server-side prepared statements,
which Supabase's transaction pooler (pgbouncer) does not support.

Every round trip to Supabase costs ~70 ms, so connections are not pinged before each use (TCP keepalives
and a 5-minute recycle catch dead ones instead), and GET routes use an autocommit session that skips
the BEGIN/ROLLBACK pair.
"""

from __future__ import annotations

from collections.abc import Iterator

from fastapi import Request
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


def create_db_engine(database_url: str) -> Engine:
    if database_url.startswith("sqlite"):
        # One shared connection so an in-memory database survives across sessions (tests, local runs).
        engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

        @event.listens_for(engine, "connect")
        def _enable_sqlite_foreign_keys(dbapi_conn, _record) -> None:  # type: ignore[no-untyped-def]
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        return engine

    return create_engine(
        database_url,
        pool_size=5,
        max_overflow=5,
        pool_timeout=10,
        pool_recycle=300,
        connect_args={
            "connect_timeout": 10,
            "keepalives": 1,
            "keepalives_idle": 30,
            "keepalives_interval": 10,
            "keepalives_count": 3,
            "prepare_threshold": None,
            "options": "-c statement_timeout=5000",
        },
    )


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def create_read_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Autocommit sessions for read-only routes: each SELECT runs on its own, with no BEGIN/ROLLBACK."""
    return sessionmaker(
        bind=engine.execution_options(isolation_level="AUTOCOMMIT"), autoflush=False, expire_on_commit=False
    )


def get_db(request: Request) -> Iterator[Session]:
    """One session per request; rolled back on any error, closed afterwards."""
    factory: sessionmaker[Session] = request.app.state.session_factory
    session = factory()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_read_db(request: Request) -> Iterator[Session]:
    """Session for GET routes only. It never writes, so it needs no transaction."""
    factory: sessionmaker[Session] = request.app.state.read_session_factory
    session = factory()
    try:
        yield session
    finally:
        session.close()
