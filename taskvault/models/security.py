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
from taskvault.models.base import utc_now, generate_uuid


class User(Base):
    """
    User account model for multi-user login and individualized settings.
    """
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    username = Column(String(64), unique=True, nullable=False, index=True)
    email = Column(String(128), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    recovery_code_hash = Column(String(255), nullable=True)
    full_name = Column(String(128), nullable=True)

    # User preferences
    timezone = Column(String(64), nullable=False, default="America/New_York")
    theme = Column(String(32), nullable=False, default="dark")
    lock_timeout_minutes = Column(Integer, nullable=False, default=15)
    week_starts_on = Column(String(16), nullable=False, default="Monday")
    default_priority = Column(String(16), nullable=False, default="medium")
    due_soon_days = Column(Integer, nullable=False, default=7)
    daily_capacity_minutes = Column(Integer, nullable=False, default=480)
    daily_goal = Column(Integer, nullable=False, default=5)
    weekly_goal = Column(Integer, nullable=False, default=25)

    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    __table_args__ = (
        Index("idx_users_username", "username"),
        Index("idx_users_email", "email"),
    )


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
    daily_goal = Column(Integer, nullable=False, default=5)
    weekly_goal = Column(Integer, nullable=False, default=25)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)


class LoginAttempt(Base):
    """
    Records login attempts for persistent rate limiting and brute force defense.
    """
    __tablename__ = "login_attempts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    identifier = Column(String(128), nullable=True)
    attempted_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    succeeded = Column(Boolean, nullable=False, default=False)
    source_fingerprint = Column(String(128), nullable=True)
    blocked_until = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_login_attempt_time", "attempted_at"),
        Index("idx_login_attempt_blocked", "blocked_until"),
        Index("idx_login_attempt_identifier", "identifier"),
    )

