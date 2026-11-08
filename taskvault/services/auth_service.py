"""
Authentication and security service for TaskVault.
Manages user accounts, login, register, forgot password, recovery, and security preferences.
"""

from __future__ import annotations

import re
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session

from taskvault.database import get_db_session
from taskvault.models.security import User, AppSetting
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
from taskvault.repositories import security_repository


class AccountValidationError(Exception):
    """Raised when account creation or profile validation fails."""
    pass


def validate_username(username: str) -> str:
    """Validates username syntax and length."""
    clean = username.strip()
    if not clean:
        raise AccountValidationError("Username cannot be empty.")
    if len(clean) < 3 or len(clean) > 30:
        raise AccountValidationError("Username must be between 3 and 30 characters.")
    if not re.match(r"^[a-zA-Z0-9_.-]+$", clean):
        raise AccountValidationError("Username can only contain letters, numbers, underscores, dashes, and periods.")
    return clean


def validate_email_address(email: str) -> str:
    """Validates email format."""
    clean = email.strip().lower()
    if not clean:
        raise AccountValidationError("Email cannot be empty.")
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", clean):
        raise AccountValidationError("Please enter a valid email address.")
    return clean


def is_first_run(db_session: Optional[Session] = None) -> bool:
    """Returns True if no accounts or workspace credentials exist yet."""
    def _check(db: Session) -> bool:
        users = security_repository.list_users(db)
        if users:
            return False
        settings = security_repository.get_settings(db)
        return settings is None or not settings.password_hash

    if db_session:
        return _check(db_session)
    with get_db_session() as db:
        return _check(db)


def register_user(
    username: str,
    email: str,
    password: str,
    confirm_password: str,
    full_name: Optional[str] = None,
    timezone: str = "America/New_York",
    theme: str = "dark",
    db_session: Optional[Session] = None,
) -> Dict[str, Any]:
    """
    Registers a new user account:
    - Validates username and email syntax and uniqueness
    - Validates password strength (Argon2id)
    - Generates and hashes a security recovery code
    - Unlocks session and returns user info with recovery code
    """
    clean_user = validate_username(username)
    clean_email = validate_email_address(email)
    validate_password_strength(password, confirm_password)

    pw_hash = hash_password(password)
    raw_recovery_code = generate_recovery_code()
    recovery_code_hash = hash_recovery_code(raw_recovery_code)

    def _do_reg(db: Session) -> Dict[str, Any]:
        # Check uniqueness
        if security_repository.get_user_by_username(db, clean_user):
            raise AccountValidationError(f"Username '{clean_user}' is already taken.")
        if security_repository.get_user_by_email(db, clean_email):
            raise AccountValidationError(f"An account with email '{clean_email}' already exists.")

        user = security_repository.create_user(
            db,
            username=clean_user,
            email=clean_email,
            password_hash=pw_hash,
            recovery_code_hash=recovery_code_hash,
            full_name=full_name,
            timezone=timezone,
            theme=theme,
        )

        # Synchronize AppSetting if needed
        existing_settings = security_repository.get_settings(db)
        if not existing_settings:
            security_repository.create_initial_settings(
                db,
                password_hash=pw_hash,
                recovery_code_hash=recovery_code_hash,
                timezone=timezone,
                theme=theme,
            )
        elif not existing_settings.password_hash:
            security_repository.update_settings(
                db,
                password_hash=pw_hash,
                recovery_code_hash=recovery_code_hash,
                timezone=timezone,
                theme=theme,
            )

        security_repository.log_activity(db, action="user_registered", entity_type="auth", entity_id=user.id)
        SessionManager.unlock(user_id=user.id, username=user.username, email=user.email, full_name=user.full_name)

        return {
            "success": True,
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "recovery_code": raw_recovery_code,
        }

    if db_session:
        return _do_reg(db_session)
    with get_db_session() as db:
        return _do_reg(db)


def login_user(
    username_or_email: str,
    password: str,
    db_session: Optional[Session] = None,
) -> Dict[str, Any]:
    """
    Authenticates a user via username or email and password:
    - Enforces rate limiting
    - Verifies Argon2id password hash
    - On success, unlocks session context
    """
    clean_id = username_or_email.strip()
    if not clean_id:
        return {"success": False, "error": "Username or email is required."}

    def _do_login(db: Session) -> Dict[str, Any]:
        check_rate_limit(db, identifier=clean_id)

        user = security_repository.get_user_by_identifier(db, clean_id)
        if user:
            valid = verify_password(user.password_hash, password)
            record_login_attempt(db, succeeded=valid, identifier=clean_id)
            if valid:
                SessionManager.unlock(
                    user_id=user.id,
                    username=user.username,
                    email=user.email,
                    full_name=user.full_name,
                )
                security_repository.log_activity(db, action="user_login", entity_type="auth", entity_id=user.id)
                return {
                    "success": True,
                    "user": {
                        "id": user.id,
                        "username": user.username,
                        "email": user.email,
                        "full_name": user.full_name,
                        "timezone": user.timezone,
                        "theme": user.theme,
                    },
                }
            return {"success": False, "error": "Incorrect password. Please try again."}

        # Fallback to master AppSetting for legacy or single-vault access
        settings = security_repository.get_settings(db)
        if settings and settings.password_hash and verify_password(settings.password_hash, password):
            record_login_attempt(db, succeeded=True, identifier=clean_id)
            # Find or create a default user record
            fallback_user = security_repository.get_user_by_username(db, "admin")
            if not fallback_user:
                fallback_user = security_repository.create_user(
                    db,
                    username="admin",
                    email="admin@taskvault.local",
                    password_hash=settings.password_hash,
                    recovery_code_hash=settings.recovery_code_hash,
                    full_name="Vault Admin",
                    timezone=settings.timezone,
                    theme=settings.theme,
                )
            SessionManager.unlock(
                user_id=fallback_user.id,
                username=fallback_user.username,
                email=fallback_user.email,
                full_name=fallback_user.full_name,
            )
            return {
                "success": True,
                "user": {
                    "id": fallback_user.id,
                    "username": fallback_user.username,
                    "email": fallback_user.email,
                    "full_name": fallback_user.full_name,
                    "timezone": fallback_user.timezone,
                    "theme": fallback_user.theme,
                },
            }

        record_login_attempt(db, succeeded=False, identifier=clean_id)
        return {"success": False, "error": "Account not found or incorrect credentials."}

    if db_session:
        return _do_login(db_session)
    with get_db_session() as db:
        return _do_login(db)


def forgot_password_reset(
    username_or_email: str,
    recovery_code: str,
    new_password: str,
    confirm_password: str,
    db_session: Optional[Session] = None,
) -> Dict[str, Any]:
    """
    Resets password using account recovery code:
    - Enforces rate limiting
    - Verifies recovery code
    - Generates new Argon2id password hash
    - Generates a fresh recovery code and unlocks session
    """
    clean_id = username_or_email.strip()
    if not clean_id:
        return {"success": False, "error": "Username or email is required."}

    def _do_reset(db: Session) -> Dict[str, Any]:
        check_rate_limit(db, identifier=clean_id)

        user = security_repository.get_user_by_identifier(db, clean_id)
        if user:
            if not user.recovery_code_hash:
                record_login_attempt(db, succeeded=False, identifier=clean_id)
                return {"success": False, "error": "No recovery code is configured for this account."}

            valid = verify_recovery_code(user.recovery_code_hash, recovery_code)
            record_login_attempt(db, succeeded=valid, identifier=clean_id)
            if not valid:
                return {"success": False, "error": "Invalid recovery code."}

            validate_password_strength(new_password, confirm_password)
            new_hash = hash_password(new_password)
            new_raw_code = generate_recovery_code()
            new_code_hash = hash_recovery_code(new_raw_code)

            security_repository.update_user(
                db,
                user.id,
                password_hash=new_hash,
                recovery_code_hash=new_code_hash,
            )

            # Sync AppSetting
            app_set = security_repository.get_settings(db)
            if app_set:
                security_repository.update_settings(db, password_hash=new_hash, recovery_code_hash=new_code_hash)

            SessionManager.unlock(user_id=user.id, username=user.username, email=user.email, full_name=user.full_name)
            security_repository.log_activity(db, action="password_reset_recovery", entity_type="auth", entity_id=user.id)

            return {
                "success": True,
                "username": user.username,
                "recovery_code": new_raw_code,
            }

        # Fallback check on master AppSetting
        app_set = security_repository.get_settings(db)
        if app_set and app_set.recovery_code_hash:
            valid = verify_recovery_code(app_set.recovery_code_hash, recovery_code)
            record_login_attempt(db, succeeded=valid, identifier=clean_id)
            if valid:
                validate_password_strength(new_password, confirm_password)
                new_hash = hash_password(new_password)
                security_repository.update_settings(db, password_hash=new_hash, recovery_code_hash=None)
                SessionManager.unlock()
                return {"success": True, "username": "admin", "recovery_code": None}

        record_login_attempt(db, succeeded=False, identifier=clean_id)
        return {"success": False, "error": "Account not found or invalid recovery code."}

    if db_session:
        return _do_reset(db_session)
    with get_db_session() as db:
        return _do_reset(db)


def get_current_user_profile(db_session: Optional[Session] = None) -> Dict[str, Any]:
    """
    Returns full profile and settings dictionary for the current session user.
    """
    user_id = SessionManager.get_current_user_id()

    def _get(db: Session) -> Dict[str, Any]:
        user: Optional[User] = None
        if user_id:
            user = security_repository.get_user_by_id(db, user_id)
        if not user:
            user = security_repository.get_first_user(db)

        settings = security_repository.get_settings(db)

        if user:
            return {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name or user.username,
                "timezone": user.timezone,
                "theme": user.theme,
                "lock_timeout_minutes": user.lock_timeout_minutes,
                "week_starts_on": user.week_starts_on,
                "default_priority": user.default_priority,
                "due_soon_days": user.due_soon_days,
                "daily_capacity_minutes": user.daily_capacity_minutes,
                "daily_goal": getattr(user, "daily_goal", 5),
                "weekly_goal": getattr(user, "weekly_goal", 25),
                "has_recovery_code": bool(user.recovery_code_hash),
                "created_at": user.created_at,
            }

        # Fallback to settings
        if settings:
            return {
                "id": "master",
                "username": "admin",
                "email": "admin@taskvault.local",
                "full_name": "Vault Administrator",
                "timezone": settings.timezone,
                "theme": settings.theme,
                "lock_timeout_minutes": settings.lock_timeout_minutes,
                "week_starts_on": settings.week_starts_on,
                "default_priority": settings.default_priority,
                "due_soon_days": settings.due_soon_days,
                "daily_capacity_minutes": settings.daily_capacity_minutes,
                "daily_goal": getattr(settings, "daily_goal", 5),
                "weekly_goal": getattr(settings, "weekly_goal", 25),
                "has_recovery_code": bool(settings.recovery_code_hash),
                "created_at": settings.created_at,
            }

        return {
            "id": "default",
            "username": "user",
            "email": "user@taskvault.local",
            "full_name": "TaskVault User",
            "timezone": "America/New_York",
            "theme": "dark",
            "lock_timeout_minutes": 10,
            "week_starts_on": "Monday",
            "default_priority": "medium",
            "due_soon_days": 7,
            "daily_capacity_minutes": 480,
            "daily_goal": 5,
            "weekly_goal": 25,
            "has_recovery_code": False,
            "created_at": None,
        }

    if db_session:
        return _get(db_session)
    with get_db_session() as db:
        return _get(db)


@require_auth
def update_profile(
    username: Optional[str] = None,
    email: Optional[str] = None,
    full_name: Optional[str] = None,
    db_session: Optional[Session] = None,
) -> Dict[str, Any]:
    """Updates profile details for the authenticated user."""
    user_id = SessionManager.get_current_user_id()

    def _do(db: Session) -> Dict[str, Any]:
        user = security_repository.get_user_by_id(db, user_id) if user_id else security_repository.get_first_user(db)
        if not user:
            raise ValueError("User not found.")

        updates: Dict[str, Any] = {}
        if username and username.strip() != user.username:
            clean_u = validate_username(username)
            existing = security_repository.get_user_by_username(db, clean_u)
            if existing and existing.id != user.id:
                raise AccountValidationError(f"Username '{clean_u}' is already taken.")
            updates["username"] = clean_u

        if email and email.strip().lower() != user.email:
            clean_e = validate_email_address(email)
            existing = security_repository.get_user_by_email(db, clean_e)
            if existing and existing.id != user.id:
                raise AccountValidationError(f"Email '{clean_e}' is already registered.")
            updates["email"] = clean_e

        if full_name is not None:
            updates["full_name"] = full_name.strip() or None

        if updates:
            updated_user = security_repository.update_user(db, user.id, **updates)
            SessionManager.unlock(
                user_id=updated_user.id,
                username=updated_user.username,
                email=updated_user.email,
                full_name=updated_user.full_name,
            )
            security_repository.log_activity(db, action="profile_updated", entity_type="auth", entity_id=user.id)
            return {"success": True, "user": updated_user}

        return {"success": True, "user": user}

    if db_session:
        return _do(db_session)
    with get_db_session() as db:
        return _do(db)


@require_auth
def update_user_preferences(**kwargs: Any) -> bool:
    """Updates preferences for current user and global settings."""
    user_id = SessionManager.get_current_user_id()
    db_session = kwargs.pop("db_session", None)

    def _do(db: Session) -> bool:
        if user_id:
            user = security_repository.get_user_by_id(db, user_id)
            if user:
                security_repository.update_user(db, user.id, **kwargs)

        # Also update global settings
        try:
            security_repository.update_settings(db, **kwargs)
        except Exception:
            pass
        return True

    if db_session:
        return _do(db_session)
    with get_db_session() as db:
        return _do(db)


@require_auth
def regenerate_recovery_code(db_session: Optional[Session] = None) -> str:
    """Generates and stores a new recovery code for the authenticated account."""
    raw_code = generate_recovery_code()
    code_hash = hash_recovery_code(raw_code)
    user_id = SessionManager.get_current_user_id()

    def _do(db: Session) -> str:
        if user_id:
            security_repository.update_user(db, user_id, recovery_code_hash=code_hash)
        app_set = security_repository.get_settings(db)
        if app_set:
            security_repository.update_settings(db, recovery_code_hash=code_hash)
        security_repository.log_activity(db, action="recovery_code_regenerated", entity_type="auth")
        return raw_code

    if db_session:
        return _do(db_session)
    with get_db_session() as db:
        return _do(db)


# ---------------------------------------------------------------------------
# Backward-compatibility API for existing tests and migrations
# ---------------------------------------------------------------------------


def setup_initial_workspace(
    password: str,
    confirm_password: str,
    enable_recovery: bool = True,
    timezone: str = "America/New_York",
    theme: str = "dark",
    db_session: Optional[Session] = None,
) -> Dict[str, Any]:
    """Initializes workspace credentials and default administrator user."""
    validate_password_strength(password, confirm_password)
    pw_hash = hash_password(password)

    raw_recovery_code: Optional[str] = None
    recovery_code_hash: Optional[str] = None
    if enable_recovery:
        raw_recovery_code = generate_recovery_code()
        recovery_code_hash = hash_recovery_code(raw_recovery_code)

    def _do_setup(db: Session):
        existing = security_repository.get_settings(db)
        if existing and existing.password_hash:
            raise ValueError("Workspace is already initialized.")
        if existing:
            security_repository.update_settings(
                db,
                password_hash=pw_hash,
                recovery_code_hash=recovery_code_hash,
                timezone=timezone,
                theme=theme,
            )
        else:
            security_repository.create_initial_settings(
                db,
                password_hash=pw_hash,
                recovery_code_hash=recovery_code_hash,
                timezone=timezone,
                theme=theme,
            )

        # Create or update default user account
        user = security_repository.get_user_by_username(db, "admin")
        if not user:
            user = security_repository.create_user(
                db,
                username="admin",
                email="admin@taskvault.local",
                password_hash=pw_hash,
                recovery_code_hash=recovery_code_hash,
                full_name="Vault Administrator",
                timezone=timezone,
                theme=theme,
            )
        else:
            security_repository.update_user(
                db,
                user.id,
                password_hash=pw_hash,
                recovery_code_hash=recovery_code_hash,
                timezone=timezone,
                theme=theme,
            )

        security_repository.log_activity(db, action="workspace_initialized", entity_type="auth")
        SessionManager.unlock(user_id=user.id, username=user.username, email=user.email, full_name=user.full_name)

    if db_session:
        _do_setup(db_session)
    else:
        with get_db_session() as db:
            _do_setup(db)

    return {
        "success": True,
        "recovery_code": raw_recovery_code,
    }


def unlock_workspace(password: str, db_session: Optional[Session] = None) -> bool:
    """Attempts to unlock the workspace using password."""
    def _do_unlock(db: Session) -> bool:
        check_rate_limit(db)

        settings = security_repository.get_settings(db)
        users = security_repository.list_users(db)

        # Check against users first
        if users:
            for u in users:
                if verify_password(u.password_hash, password):
                    record_login_attempt(db, succeeded=True)
                    SessionManager.unlock(user_id=u.id, username=u.username, email=u.email, full_name=u.full_name)
                    security_repository.log_activity(db, action="session_unlocked", entity_type="auth")
                    return True

        # Check against master settings
        if settings and settings.password_hash:
            valid = verify_password(settings.password_hash, password)
            record_login_attempt(db, succeeded=valid)
            if valid:
                SessionManager.unlock()
                security_repository.log_activity(db, action="session_unlocked", entity_type="auth")
                return True
            return False

        record_login_attempt(db, succeeded=False)
        raise ValueError("Workspace has not been initialized.")

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
    """Recovers access via recovery code and sets a new password."""
    def _do_recover(db: Session) -> bool:
        check_rate_limit(db)

        settings = security_repository.get_settings(db)
        users = security_repository.list_users(db)

        # Try matching user recovery code
        target_user = None
        for u in users:
            if u.recovery_code_hash and verify_recovery_code(u.recovery_code_hash, recovery_code):
                target_user = u
                break

        if not target_user and (not settings or not settings.recovery_code_hash or not verify_recovery_code(settings.recovery_code_hash, recovery_code)):
            record_login_attempt(db, succeeded=False)
            if not settings or not settings.recovery_code_hash:
                raise ValueError("Recovery code is not configured or workspace is uninitialized.")
            return False

        record_login_attempt(db, succeeded=True)
        validate_password_strength(new_password, confirm_password)
        new_hash = hash_password(new_password)

        if target_user:
            security_repository.update_user(db, target_user.id, password_hash=new_hash, recovery_code_hash=None)
            SessionManager.unlock(user_id=target_user.id, username=target_user.username, email=target_user.email, full_name=target_user.full_name)

        if settings:
            security_repository.update_settings(db, password_hash=new_hash, recovery_code_hash=None)
            if not target_user:
                SessionManager.unlock()

        security_repository.log_activity(db, action="password_recovered", entity_type="auth")
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
    """Changes password for the current user or master settings."""
    user_id = SessionManager.get_current_user_id()

    def _do_change(db: Session) -> bool:
        user = security_repository.get_user_by_id(db, user_id) if user_id else None
        settings = security_repository.get_settings(db)

        target_hash = user.password_hash if user else (settings.password_hash if settings else None)
        if not target_hash or not verify_password(target_hash, old_password):
            return False

        validate_password_strength(new_password, confirm_password)
        new_hash = hash_password(new_password)

        if user:
            security_repository.update_user(db, user.id, password_hash=new_hash)
        if settings:
            security_repository.update_settings(db, password_hash=new_hash)

        security_repository.log_activity(db, action="password_changed", entity_type="auth")
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
    profile = get_current_user_profile(db_session=db_session)
    return {
        "initialized": bool(profile.get("id")),
        "recovery_enabled": profile.get("has_recovery_code", False),
        "lock_timeout_minutes": profile.get("lock_timeout_minutes", 10),
        "timezone": profile.get("timezone", "America/New_York"),
        "theme": profile.get("theme", "dark"),
        "week_starts_on": profile.get("week_starts_on", "Monday"),
        "default_priority": profile.get("default_priority", "medium"),
        "due_soon_days": profile.get("due_soon_days", 7),
        "daily_capacity_minutes": profile.get("daily_capacity_minutes", 480),
        "daily_goal": profile.get("daily_goal", 5),
        "weekly_goal": profile.get("weekly_goal", 25),
        "username": profile.get("username", "user"),
        "email": profile.get("email", ""),
        "full_name": profile.get("full_name", ""),
    }


