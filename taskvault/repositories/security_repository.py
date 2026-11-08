"""
Repository for User, AppSetting, LoginAttempt, and ActivityLog operations.
"""

from __future__ import annotations

from typing import Optional, Dict, Any, List
from sqlalchemy import select, or_, func
from sqlalchemy.orm import Session

from taskvault.models.security import User, AppSetting
from taskvault.models.focus import ActivityLog
from taskvault.models.base import utc_now, generate_uuid


# ---------------------------------------------------------------------------
# User operations
# ---------------------------------------------------------------------------


def get_user_by_id(db: Session, user_id: str) -> Optional[User]:
    """Retrieves a user by ID."""
    return db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """Retrieves a user by username (case-insensitive)."""
    clean = username.strip().lower()
    return db.execute(select(User).where(func.lower(User.username) == clean)).scalar_one_or_none()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Retrieves a user by email (case-insensitive)."""
    clean = email.strip().lower()
    return db.execute(select(User).where(func.lower(User.email) == clean)).scalar_one_or_none()


def get_user_by_identifier(db: Session, identifier: str) -> Optional[User]:
    """Retrieves a user by either username or email (case-insensitive)."""
    clean = identifier.strip().lower()
    return db.execute(
        select(User).where(
            or_(
                func.lower(User.username) == clean,
                func.lower(User.email) == clean,
            )
        )
    ).scalar_one_or_none()


def list_users(db: Session) -> List[User]:
    """Retrieves all registered users."""
    return list(db.execute(select(User).order_by(User.created_at.asc())).scalars().all())


def get_first_user(db: Session) -> Optional[User]:
    """Retrieves the first registered user or None."""
    return db.execute(select(User).order_by(User.created_at.asc())).scalars().first()


def create_user(
    db: Session,
    username: str,
    email: str,
    password_hash: str,
    recovery_code_hash: Optional[str] = None,
    full_name: Optional[str] = None,
    timezone: str = "America/New_York",
    theme: str = "dark",
) -> User:
    """Creates a new user record."""
    user = User(
        id=generate_uuid(),
        username=username.strip(),
        email=email.strip().lower(),
        password_hash=password_hash,
        recovery_code_hash=recovery_code_hash,
        full_name=full_name.strip() if full_name else None,
        timezone=timezone,
        theme=theme,
        lock_timeout_minutes=15,
        week_starts_on="Monday",
        default_priority="medium",
        due_soon_days=7,
        daily_capacity_minutes=480,
        daily_goal=5,
        weekly_goal=25,
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


def update_user(db: Session, user_id: str, **kwargs: Any) -> User:
    """Updates fields on an existing user."""
    user = get_user_by_id(db, user_id)
    if not user:
        raise ValueError(f"User {user_id} not found.")
    for key, val in kwargs.items():
        if hasattr(user, key) and key not in ("id", "created_at"):
            setattr(user, key, val)
    user.updated_at = utc_now()
    db.flush()
    return user


# ---------------------------------------------------------------------------
# AppSetting operations (Global / Singleton)
# ---------------------------------------------------------------------------


def get_settings(db: Session) -> Optional[AppSetting]:
    """Retrieves the singleton app configuration, or None if first-run."""
    return db.execute(select(AppSetting).where(AppSetting.id == 1)).scalar_one_or_none()


def create_initial_settings(
    db: Session,
    password_hash: str,
    recovery_code_hash: Optional[str] = None,
    timezone: str = "America/New_York",
    theme: str = "dark",
) -> AppSetting:
    """Initializes workspace settings on first run."""
    settings = AppSetting(
        id=1,
        password_hash=password_hash,
        recovery_code_hash=recovery_code_hash,
        timezone=timezone,
        theme=theme,
        lock_timeout_minutes=10,
        week_starts_on="Monday",
        default_priority="medium",
        due_soon_days=7,
        daily_capacity_minutes=480,
        daily_goal=5,
        weekly_goal=25,
    )
    db.add(settings)
    db.flush()
    return settings


def update_settings(db: Session, **kwargs: Any) -> AppSetting:
    """Updates settings attributes."""
    settings = get_settings(db)
    if not settings:
        raise ValueError("App settings not found.")
    for key, val in kwargs.items():
        if hasattr(settings, key) and key != "id":
            setattr(settings, key, val)
    settings.updated_at = utc_now()
    db.flush()
    return settings


def log_activity(
    db: Session,
    action: str,
    entity_type: str,
    entity_id: Optional[str] = None,
    details: Optional[str] = None,
) -> ActivityLog:
    """Logs non-sensitive operational events."""
    log = ActivityLog(
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
        created_at=utc_now(),
    )
    db.add(log)
    db.flush()
    return log


