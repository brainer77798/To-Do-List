"""
Tests for authentication, Argon2id password verification, lockout rate-limiting, and recovery.
"""

import pytest
import time
from datetime import timedelta
from taskvault.services import auth_service
from taskvault.security.passwords import (
    hash_password,
    verify_password,
    validate_password_strength,
    PasswordValidationError,
)
from taskvault.security.rate_limit import RateLimitExceededError
from taskvault.security.access_control import SessionManager
from taskvault.repositories import security_repository
from taskvault.models.base import utc_now


def test_first_run_detection(db_session):
    assert auth_service.is_first_run(db_session=db_session) is True


def test_password_strength_validation():
    # Short password rejected
    with pytest.raises(PasswordValidationError):
        validate_password_strength("short123")

    # Mismatched confirmation rejected
    with pytest.raises(PasswordValidationError):
        validate_password_strength("correcthorsebatterystaple", "differenthorsebattery")

    # Valid long password passes
    validate_password_strength("correcthorsebatterystaple", "correcthorsebatterystaple")


def test_setup_initial_workspace(db_session):
    res = auth_service.setup_initial_workspace(
        password="MySecretVaultPassword123!",
        confirm_password="MySecretVaultPassword123!",
        enable_recovery=True,
        db_session=db_session,
    )
    assert res["success"] is True
    assert res["recovery_code"] is not None

    settings = security_repository.get_settings(db_session)
    assert settings is not None
    # Verify Argon2id hash is stored and NOT plaintext
    assert settings.password_hash.startswith("$argon2")
    assert "MySecretVaultPassword123!" not in settings.password_hash

    # Verify recovery code hash is stored and NOT plaintext
    assert settings.recovery_code_hash.startswith("$argon2")
    assert res["recovery_code"] not in settings.recovery_code_hash

    # Workspace should not longer be first run
    assert auth_service.is_first_run(db_session=db_session) is False


def test_unlock_workspace_success_and_failure(db_session):
    pw = "StrongMasterPassword2026!"
    auth_service.setup_initial_workspace(
        password=pw,
        confirm_password=pw,
        db_session=db_session,
    )
    SessionManager.lock()
    assert SessionManager.is_unlocked() is False

    # Incorrect password returns False
    unlocked = auth_service.unlock_workspace("WrongPassword123!", db_session=db_session)
    assert unlocked is False
    assert SessionManager.is_unlocked() is False

    # Correct password unlocks session
    unlocked = auth_service.unlock_workspace(pw, db_session=db_session)
    assert unlocked is True
    assert SessionManager.is_unlocked() is True


def test_persistent_rate_limiting_lockout(db_session):
    pw = "SuperSecurePassword123!"
    auth_service.setup_initial_workspace(
        password=pw,
        confirm_password=pw,
        db_session=db_session,
    )
    SessionManager.lock()

    # Fail 4 times
    for _ in range(4):
        auth_service.unlock_workspace("wrong_pass_attempt", db_session=db_session)

    # 5th failure triggers lockout
    with pytest.raises(RateLimitExceededError) as exc_info:
        auth_service.unlock_workspace("wrong_pass_attempt_5", db_session=db_session)

    assert "Unable to unlock" in str(exc_info.value)
    assert exc_info.value.retry_after_seconds > 0

    # Next attempt (even with correct password) is immediately rejected by persistent rate limiting
    with pytest.raises(RateLimitExceededError):
        auth_service.unlock_workspace(pw, db_session=db_session)


def test_recovery_code_flow(db_session):
    pw = "OriginalPassword123!"
    res = auth_service.setup_initial_workspace(
        password=pw,
        confirm_password=pw,
        enable_recovery=True,
        db_session=db_session,
    )
    recovery_code = res["recovery_code"]
    SessionManager.lock()

    # Use recovery code with new password
    new_pw = "BrandNewVaultPassword456!"
    recovered = auth_service.recover_workspace(
        recovery_code=recovery_code,
        new_password=new_pw,
        confirm_password=new_pw,
        db_session=db_session,
    )
    assert recovered is True
    assert SessionManager.is_unlocked() is True

    # Check that old password no longer works
    SessionManager.lock()
    assert auth_service.unlock_workspace(pw, db_session=db_session) is False

    # Check that new password works
    assert auth_service.unlock_workspace(new_pw, db_session=db_session) is True

    # Recovery code must be invalidated after one use
    SessionManager.lock()
    with pytest.raises(ValueError):
        auth_service.recover_workspace(recovery_code, "YetAnotherPassword123!", "YetAnotherPassword123!", db_session=db_session)


def test_password_change_service(authenticated_session):
    pw = "StartingPassword123!"
    auth_service.setup_initial_workspace(
        password=pw,
        confirm_password=pw,
        db_session=authenticated_session,
    )

    # Change password
    updated = auth_service.change_password(
        old_password=pw,
        new_password="ChangedPassword123!",
        confirm_password="ChangedPassword123!",
        db_session=authenticated_session,
    )
    assert updated is True

    # Verify old password is now invalid and new password works
    SessionManager.lock()
    assert auth_service.unlock_workspace(pw, db_session=authenticated_session) is False
    assert auth_service.unlock_workspace("ChangedPassword123!", db_session=authenticated_session) is True

