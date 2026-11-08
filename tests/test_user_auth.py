"""
Comprehensive tests for multi-user authentication:
- Account creation (username, email, password, recovery code)
- Login via username or email
- Rate limiting on login attempts
- Forgot password recovery code reset flow
- Profile and preference updates
"""

from __future__ import annotations

import pytest
from taskvault.services import auth_service
from taskvault.services.auth_service import AccountValidationError
from taskvault.security.passwords import PasswordValidationError
from taskvault.security.rate_limit import RateLimitExceededError
from taskvault.security.access_control import SessionManager
from taskvault.repositories import security_repository


def test_register_user_success(db_session):
    """Registering a new account stores Argon2id hash and recovery code, and unlocks session."""
    SessionManager.lock()
    res = auth_service.register_user(
        username="alex_dev",
        email="alex@example.com",
        password="MySecretVaultPassword123!",
        confirm_password="MySecretVaultPassword123!",
        full_name="Alex Mercer",
        timezone="America/New_York",
        theme="dark",
        db_session=db_session,
    )
    assert res["success"] is True
    assert res["username"] == "alex_dev"
    assert res["email"] == "alex@example.com"
    assert res["recovery_code"] is not None
    assert SessionManager.is_unlocked() is True
    assert SessionManager.get_current_username() == "alex_dev"

    user = security_repository.get_user_by_username(db_session, "alex_dev")
    assert user is not None
    assert user.password_hash.startswith("$argon2")
    assert "MySecretVaultPassword123!" not in user.password_hash
    assert user.recovery_code_hash.startswith("$argon2")


def test_register_duplicate_username_fails(db_session):
    """Registering with an already used username raises AccountValidationError."""
    auth_service.register_user(
        username="sam_coder",
        email="sam1@example.com",
        password="SuperPassword123!",
        confirm_password="SuperPassword123!",
        db_session=db_session,
    )

    with pytest.raises(AccountValidationError) as exc:
        auth_service.register_user(
            username="SAM_CODER",  # case-insensitive check
            email="sam2@example.com",
            password="SuperPassword123!",
            confirm_password="SuperPassword123!",
            db_session=db_session,
        )
    assert "already taken" in str(exc.value)


def test_register_duplicate_email_fails(db_session):
    """Registering with an already used email raises AccountValidationError."""
    auth_service.register_user(
        username="user_one",
        email="shared@example.com",
        password="SuperPassword123!",
        confirm_password="SuperPassword123!",
        db_session=db_session,
    )

    with pytest.raises(AccountValidationError) as exc:
        auth_service.register_user(
            username="user_two",
            email="SHARED@EXAMPLE.COM",  # case-insensitive check
            password="SuperPassword123!",
            confirm_password="SuperPassword123!",
            db_session=db_session,
        )
    assert "already exists" in str(exc.value)


def test_register_invalid_inputs(db_session):
    """Invalid usernames or emails are rejected."""
    # Username too short
    with pytest.raises(AccountValidationError):
        auth_service.register_user("ab", "valid@example.com", "Password123!456", "Password123!456", db_session=db_session)

    # Username with illegal characters
    with pytest.raises(AccountValidationError):
        auth_service.register_user("user space!", "valid@example.com", "Password123!456", "Password123!456", db_session=db_session)

    # Invalid email
    with pytest.raises(AccountValidationError):
        auth_service.register_user("valid_user", "notanemail", "Password123!456", "Password123!456", db_session=db_session)


def test_login_with_username_and_email(db_session):
    """Users can log in with either their username or their email address."""
    pw = "VaultStrongPass2026!"
    auth_service.register_user(
        username="jordan_b",
        email="jordan@company.com",
        password=pw,
        confirm_password=pw,
        db_session=db_session,
    )

    # Test login with username
    SessionManager.lock()
    res_user = auth_service.login_user("jordan_b", pw, db_session=db_session)
    assert res_user["success"] is True
    assert res_user["user"]["username"] == "jordan_b"
    assert SessionManager.is_unlocked() is True

    # Test login with email
    SessionManager.lock()
    res_email = auth_service.login_user("JORDAN@COMPANY.COM", pw, db_session=db_session)
    assert res_email["success"] is True
    assert res_email["user"]["email"] == "jordan@company.com"
    assert SessionManager.is_unlocked() is True

    # Test login with wrong password
    SessionManager.lock()
    res_wrong = auth_service.login_user("jordan_b", "WrongPass123!", db_session=db_session)
    assert res_wrong["success"] is False
    assert SessionManager.is_unlocked() is False


def test_login_rate_limiting_lockout(db_session):
    """Five consecutive failed logins trigger rate limit lockout."""
    pw = "CorrectPassword123!"
    auth_service.register_user(
        username="target_user",
        email="target@example.com",
        password=pw,
        confirm_password=pw,
        db_session=db_session,
    )
    SessionManager.lock()

    # 4 failed attempts
    for _ in range(4):
        auth_service.login_user("target_user", "bad_pass", db_session=db_session)

    # 5th failed attempt triggers lockout
    with pytest.raises(RateLimitExceededError) as exc_info:
        auth_service.login_user("target_user", "bad_pass_5", db_session=db_session)

    assert exc_info.value.retry_after_seconds > 0

    # Subsequent attempt blocked immediately
    with pytest.raises(RateLimitExceededError):
        auth_service.login_user("target_user", pw, db_session=db_session)


def test_forgot_password_reset_flow(db_session):
    """User can reset their password using the recovery code issued at registration."""
    orig_pw = "OriginalPass123!"
    reg = auth_service.register_user(
        username="forgetful_user",
        email="forgetful@example.com",
        password=orig_pw,
        confirm_password=orig_pw,
        db_session=db_session,
    )
    recovery_code = reg["recovery_code"]
    SessionManager.lock()

    # Reset with wrong recovery code fails
    res_bad = auth_service.forgot_password_reset(
        username_or_email="forgetful_user",
        recovery_code="WRONG-CODE-0000-0000",
        new_password="NewSecurePass456!",
        confirm_password="NewSecurePass456!",
        db_session=db_session,
    )
    assert res_bad["success"] is False

    # Reset with correct recovery code succeeds
    new_pw = "NewSecurePass456!"
    res_good = auth_service.forgot_password_reset(
        username_or_email="forgetful@example.com",
        recovery_code=recovery_code,
        new_password=new_pw,
        confirm_password=new_pw,
        db_session=db_session,
    )
    assert res_good["success"] is True
    assert res_good["recovery_code"] is not None
    assert SessionManager.is_unlocked() is True

    # Old password no longer works
    SessionManager.lock()
    old_try = auth_service.login_user("forgetful_user", orig_pw, db_session=db_session)
    assert old_try["success"] is False

    # New password works
    new_try = auth_service.login_user("forgetful_user", new_pw, db_session=db_session)
    assert new_try["success"] is True


def test_update_profile_and_preferences(db_session):
    """User can update profile info and productivity preferences."""
    reg = auth_service.register_user(
        username="pref_user",
        email="pref@example.com",
        password="Pass123456789!",
        confirm_password="Pass123456789!",
        db_session=db_session,
    )
    user_id = reg["user_id"]

    # Update profile
    prof_res = auth_service.update_profile(
        username="pref_user_updated",
        email="new_pref@example.com",
        full_name="New Name",
        db_session=db_session,
    )
    assert prof_res["success"] is True
    assert SessionManager.get_current_username() == "pref_user_updated"

    # Update preferences
    auth_service.update_user_preferences(
        timezone="America/Los_Angeles",
        theme="light",
        default_priority="high",
        daily_goal=8,
        weekly_goal=40,
        db_session=db_session,
    )

    profile = auth_service.get_current_user_profile(db_session=db_session)
    assert profile["timezone"] == "America/Los_Angeles"
    assert profile["theme"] == "light"
    assert profile["default_priority"] == "high"
    assert profile["daily_goal"] == 8
    assert profile["weekly_goal"] == 40
