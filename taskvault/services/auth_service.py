"""
Authentication and security service for TaskVault.
Manages setup, unlock, lockout, recovery, and password changes.
"""

from __future__ import annotations

from typing import Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session

from taskvault.database import get_db_session
from taskvault.models.security import AppSetting
from taskvault.security.passwords import (
    validate_password_strength,
    hash_password,
    verify_password,
    generate_recovery_code,
    hash_recovery_code,
    verify_recovery_code,
    PasswordValidationError,
)
from taskvault.security.rate_limit import (
    check_rate_limit,
    record_login_attempt,
    RateLimitExceededError,
)
from taskvault.security.access_control import SessionManager, require_auth
from taskvault.repositories.security_repository import (
    get_settings,
    create_initial_settings,
    update_settings,
    log_activity,
)


def is_first_run(db_session: Optional[Session] = None) -> bool:
    """Returns True if the application has not yet configured a password."""
    if db_session:
        settings = get_settings(db_session)
        return settings is None or not settings.password_hash
    with get_db_session() as db:
        settings = get_settings(db)
        return settings is None or not settings.password_hash


def setup_initial_workspace(
    password: str,
    confirm_password: str,
    enable_recovery: bool = True,
    timezone: str = "America/New_York",
    theme: str = "dark",
    db_session: Optional[Session] = None,
) -> Dict[str, Any]:
    """
    Executes first-run workspace initialization:
    - Validates password length and match
    - Generates Argon2id hash
    - Optionally generates a one-time recovery code
    - Saves settings and unlocks the session
    """
    validate_password_strength(password, confirm_password)
    pw_hash = hash_password(password)

    raw_recovery_code: Optional[str] = None
    recovery_code_hash: Optional[str] = None
    if enable_recovery:
        raw_recovery_code = generate_recovery_code()
        recovery_code_hash = hash_recovery_code(raw_recovery_code)

    def _do_setup(db: Session):
        existing = get_settings(db)
        if existing and existing.password_hash:
            raise ValueError("Workspace is already initialized.")
        if existing:
            update_settings(
                db,
                password_hash=pw_hash,
                recovery_code_hash=recovery_code_hash,
                timezone=timezone,
                theme=theme,
            )
        else:
            create_initial_settings(
                db,
                password_hash=pw_hash,
                recovery_code_hash=recovery_code_hash,
                timezone=timezone,
                theme=theme,
            )
        log_activity(db, action="workspace_initialized", entity_type="auth")

    if db_session:
        _do_setup(db_session)
    else:
        with get_db_session() as db:
            _do_setup(db)

    # Unlock the current user session
    SessionManager.unlock()

    return {
        "success": True,
        "recovery_code": raw_recovery_code,
    }


def unlock_workspace(password: str, db_session: Optional[Session] = None) -> bool:
    """
    Attempts to unlock the workspace:
    - Enforces persistent database rate limiting before checking password
    - Constant-time verifies Argon2id password hash
    - Records persistent attempt result
    - On success, unlocks session state
    """
    def _do_unlock(db: Session) -> bool:
        # Enforce rate limit first
        check_rate_limit(db)

        settings = get_settings(db)
        if not settings or not settings.password_hash:
            raise ValueError("Workspace has not been initialized.")

        valid = verify_password(settings.password_hash, password)
        record_login_attempt(db, succeeded=valid)

        if valid:
            SessionManager.unlock()
            log_activity(db, action="session_unlocked", entity_type="auth")
            return True
        return False

    if db_session:
        return _do_unlock(db_session)
    with get_db_session() as db:
        return _do_unlock(db)


def recover_workspace(
    recovery_code: str,
    new_password: str,
    confirm_password: str,
    db_session: Optional[Session] = None,
) -> bool:
    """
    Unlocks workspace via recovery code and sets a new password:
    - Verifies recovery code against stored verifier
    - Updates password with new Argon2id hash
    - Invalidates recovery code (one-time use)
    """
    def _do_recover(db: Session) -> bool:
        check_rate_limit(db)

        settings = get_settings(db)
        if not settings or not settings.recovery_code_hash:
            record_login_attempt(db, succeeded=False)
            raise ValueError("Recovery code is not configured or workspace is uninitialized.")

        valid = verify_recovery_code(settings.recovery_code_hash, recovery_code)
        record_login_attempt(db, succeeded=valid)

        if not valid:
            return False

        validate_password_strength(new_password, confirm_password)
        new_hash = hash_password(new_password)

        # Invalidate recovery code and save new password hash
        update_settings(db, password_hash=new_hash, recovery_code_hash=None)
        log_activity(db, action="password_recovered", entity_type="auth")
        SessionManager.unlock()
        return True

    if db_session:
        return _do_recover(db_session)
    with get_db_session() as db:
        return _do_recover(db)


@require_auth
def change_password(
    old_password: str,
    new_password: str,
    confirm_password: str,
    db_session: Optional[Session] = None,
) -> bool:
    """
    Changes workspace password:
    - Verifies existing password
    - Validates and hashes new password
    - Saves new hash and logs event
    """
    def _do_change(db: Session) -> bool:
        settings = get_settings(db)
        if not settings or not verify_password(settings.password_hash, old_password):
            return False

        validate_password_strength(new_password, confirm_password)
        new_hash = hash_password(new_password)
        update_settings(db, password_hash=new_hash)
        log_activity(db, action="password_changed", entity_type="auth")
        return True

    if db_session:
        return _do_change(db_session)
    with get_db_session() as db:
        return _do_change(db)


def lock_workspace() -> None:
    """Locks the current session and clears sensitive data."""
    SessionManager.lock()


def get_security_status(db_session: Optional[Session] = None) -> Dict[str, Any]:
    """Returns non-sensitive security and configuration settings for display."""
    def _get_status(db: Session) -> Dict[str, Any]:
        settings = get_settings(db)
        if not settings:
            return {
                "initialized": False,
                "recovery_enabled": False,
                "lock_timeout_minutes": 10,
                "timezone": "America/New_York",
                "theme": "dark",
            }
        return {
            "initialized": bool(settings.password_hash),
            "recovery_enabled": bool(settings.recovery_code_hash),
            "lock_timeout_minutes": settings.lock_timeout_minutes,
            "timezone": settings.timezone,
            "theme": settings.theme,
            "week_starts_on": settings.week_starts_on,
            "default_priority": settings.default_priority,
            "due_soon_days": settings.due_soon_days,
            "daily_capacity_minutes": settings.daily_capacity_minutes,
        }

    if db_session:
        return _get_status(db_session)
    with get_db_session() as db:
        return _get_status(db)

