"""
Database engine and session management for TaskVault.
Supports both PostgreSQL (production) and SQLite (local dev), ensuring proper pooling,
foreign key enforcement on SQLite, and transactional session scoping.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event, Engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from taskvault.config import load_config, AppConfig

logger = logging.getLogger("taskvault.database")

Base = declarative_base()

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def get_engine(config: AppConfig | None = None) -> Engine:
    """
    Returns a cached SQLAlchemy Engine instance configured for SQLite or PostgreSQL.
    """
    global _engine, _session_factory
    if _engine is not None:
        return _engine

    cfg = config or load_config()

    if cfg.is_sqlite:
        connect_args = {"check_same_thread": False}
        engine = create_engine(
            cfg.database_url,
            connect_args=connect_args,
            echo=False,
            future=True,
        )

        # Enforce foreign key constraints in SQLite
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    else:
        # Managed PostgreSQL configuration
        engine = create_engine(
            cfg.database_url,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            pool_recycle=1800,
            echo=False,
            future=True,
        )

    _engine = engine
    _session_factory = sessionmaker(
        bind=_engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
    return _engine


def get_session_factory(config: AppConfig | None = None) -> sessionmaker[Session]:
    """
    Returns the sessionmaker instance.
    """
    global _session_factory
    if _session_factory is None:
        get_engine(config)
    assert _session_factory is not None
    return _session_factory


@contextmanager
def get_db_session(config: AppConfig | None = None) -> Generator[Session, None, None]:
    """
    Context manager providing a transactional database session.
    Commits on success, rolls back on exception, and guarantees closure.
    """
    factory = get_session_factory(config)
    session: Session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db(engine: Engine | None = None) -> None:
    """
    Creates all registered schema tables if they do not exist,
    and applies safe additive migrations for existing databases.
    """
    eng = engine or get_engine()
    # Import all models to ensure they are registered with Base.metadata
    from taskvault import models  # noqa: F401
    from sqlalchemy import text, inspect

    Base.metadata.create_all(bind=eng)

    # Safe additive column migration for existing SQLite databases
    with eng.connect() as conn:
        try:
            inspector = inspect(eng)
            if "app_settings" in inspector.get_table_names():
                existing_cols = {c["name"] for c in inspector.get_columns("app_settings")}
                if "daily_goal" not in existing_cols:
                    conn.execute(text("ALTER TABLE app_settings ADD COLUMN daily_goal INTEGER DEFAULT 5 NOT NULL"))
                if "weekly_goal" not in existing_cols:
                    conn.execute(text("ALTER TABLE app_settings ADD COLUMN weekly_goal INTEGER DEFAULT 25 NOT NULL"))

            if "login_attempts" in inspector.get_table_names():
                existing_cols = {c["name"] for c in inspector.get_columns("login_attempts")}
                if "identifier" not in existing_cols:
                    conn.execute(text("ALTER TABLE login_attempts ADD COLUMN identifier VARCHAR(128)"))

            conn.commit()
        except Exception as mig_err:
            logger.warning(f"Auto-migration notice: {mig_err}")

