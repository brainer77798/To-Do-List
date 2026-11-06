"""
Security package for TaskVault.
"""

from taskvault.security.passwords import (
    validate_password_strength,
    hash_password,
    verify_password,
    needs_rehash,
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
from taskvault.security.access_control import (
    SessionManager,
    require_auth,
    UnauthorizedAccessError,
)

__all__ = [
    "validate_password_strength",
    "hash_password",
    "verify_password",
    "needs_rehash",
    "generate_recovery_code",
    "hash_recovery_code",
    "verify_recovery_code",
    "PasswordValidationError",
    "check_rate_limit",
    "record_login_attempt",
    "RateLimitExceededError",
    "SessionManager",
    "require_auth",
    "UnauthorizedAccessError",
]

