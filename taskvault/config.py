"""
Configuration management for TaskVault.
Handles database connection resolution, secrets extraction, and environment validation.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


PRODUCT_NAME = "TaskVault"
APP_VERSION = "1.0.0"

# Defaults
DEFAULT_TIMEZONE = "America/New_York"
DEFAULT_THEME = "dark"
DEFAULT_LOCK_TIMEOUT_MINUTES = 10
DEFAULT_DUE_SOON_DAYS = 7
DEFAULT_WEEK_STARTS_ON = "Monday"
DEFAULT_PRIORITY = "medium"
DEFAULT_DAILY_CAPACITY_MINUTES = 480  # 8 hours

# Rate limiting defaults
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_WINDOW_MINUTES = 15
INITIAL_LOCKOUT_MINUTES = 15
MAX_LOCKOUT_MINUTES = 60


class ConfigurationError(Exception):
    """Raised when application configuration is invalid or missing required values."""
    pass


@dataclass(frozen=True)
class AppConfig:
    product_name: str
    version: str
    env: str
    database_url: str
    is_sqlite: bool
    is_production: bool


def get_secret(key: str, default: Optional[str] = None) -> Optional[str]:
    """
    Attempts to read a key from streamlit.secrets, then os.environ, then default.
    """
    # Try Streamlit secrets first
    try:
        import streamlit as st
        if hasattr(st, "secrets") and key in st.secrets:
            return str(st.secrets[key])
    except Exception:
        pass

    # Try environment variables
    env_val = os.environ.get(key)
    if env_val is not None:
        return env_val

    return default


def load_config() -> AppConfig:
    """
    Loads and validates the current application configuration.
    In production mode, enforces that a persistent DATABASE_URL is configured.
    """
    env = (get_secret("APP_ENV", "development") or "development").strip().lower()
    raw_db_url = get_secret("DATABASE_URL")

    is_production = env in ("production", "prod")

    if is_production and not raw_db_url:
        raise ConfigurationError(
            "CRITICAL: Production deployment detected (APP_ENV=production), "
            "but DATABASE_URL is not set. Ephemeral local storage cannot be used in production. "
            "Please configure DATABASE_URL in Streamlit secrets or environment variables."
        )

    if not raw_db_url:
        # Development local fallback
        db_url = "sqlite:///./taskvault.db"
    else:
        db_url = raw_db_url.strip()
        # Normalize postgres:// to postgresql+psycopg:// if needed for SQLAlchemy 2.x
        if db_url.startswith("postgres://"):
            db_url = "postgresql+psycopg://" + db_url[len("postgres://"):]
        elif db_url.startswith("postgresql://") and not db_url.startswith("postgresql+"):
            db_url = "postgresql+psycopg://" + db_url[len("postgresql://"):]

    is_sqlite = db_url.startswith("sqlite")

    return AppConfig(
        product_name=PRODUCT_NAME,
        version=APP_VERSION,
        env=env,
        database_url=db_url,
        is_sqlite=is_sqlite,
        is_production=is_production,
    )

