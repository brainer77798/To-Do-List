"""
Pytest configuration and fixtures for TaskVault tests.
Uses an isolated in-memory or temporary SQLite database.
"""

import os
import sys
from pathlib import Path

# Ensure taskvault package is always resolvable
repo_root = str(Path(__file__).resolve().parent.parent)
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from taskvault.database import Base
from taskvault.models.base import utc_now
from taskvault.security.access_control import SessionManager
import taskvault.models  # ensure models registered


@pytest.fixture
def db_session():
    """Provides a fresh isolated in-memory SQLite database session for each test."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = Session()

    yield session

    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def authenticated_session(db_session):
    """Sets SessionManager to unlocked state for protected service tests."""
    SessionManager.unlock()
    yield db_session
    SessionManager.lock()
