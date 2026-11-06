"""
Security and settings SQLAlchemy models.
"""

from __future__ import annotations

from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    Index,
)
from taskvault.database import Base
from taskvault.models.base import utc_now


class AppSetting(Base):
    """
    Singleton row (id=1) holding application settings, hashed credentials, and preferences.
    """
    __tablename__ = "app_settings"

    id = Column(Integer, primary_key=True, default=1)
    password_hash = Column(String(255), nullable=False)
    recovery_code_hash = Column(String(255), nullable=True)
    timezone = Column(String(64), nullable=False, default="America/New_York")
    theme = Column(String(32), nullable=False, default="dark")
    lock_timeout_minutes = Column(Integer, nullable=False, default=10)
    week_starts_on = Column(String(16), nullable=False, default="Monday")
    default_priority = Column(String(16), nullable=False, default="medium")
    due_soon_days = Column(Integer, nullable=False, default=7)
    daily_capacity_minutes = Column(Integer, nullable=False, default=480)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)


class LoginAttempt(Base):
    """
    Records login attempts for persistent rate limiting and brute force defense.
    """
    __tablename__ = "login_attempts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    attempted_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    succeeded = Column(Boolean, nullable=False, default=False)
    source_fingerprint = Column(String(128), nullable=True)
    blocked_until = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_login_attempt_time", "attempted_at"),
        Index("idx_login_attempt_blocked", "blocked_until"),
    )

