"""
Repository for AppSetting, LoginAttempt, and ActivityLog operations.
"""

from __future__ import annotations

from typing import Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.orm import Session

from taskvault.models.security import AppSetting
from taskvault.models.focus import ActivityLog
from taskvault.models.base import utc_now


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

