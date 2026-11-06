"""
Password hashing, verification, validation, and recovery code generation using Argon2id.
Adheres to OWASP recommendations.
"""

from __future__ import annotations

import secrets
import string
import hashlib
import argon2
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError

# Configure Argon2id according to OWASP guidelines
_hasher = PasswordHasher(
    time_cost=2,
    memory_cost=65536,  # 64 MB
    parallelism=1,
    hash_len=32,
    type=argon2.Type.ID,
)

MIN_PASSWORD_LENGTH = 12


class PasswordValidationError(Exception):
    """Raised when password validation rules are violated."""
    pass


def validate_password_strength(password: str, confirm_password: str | None = None) -> None:
    """
    Validates password strength according to spec:
    - Minimum 12 characters.
    - Long passphrases and spaces allowed.
    - Non-empty.
    - Matches confirmation if provided.
    """
    if not password:
        raise PasswordValidationError("Password cannot be empty.")

    if len(password) < MIN_PASSWORD_LENGTH:
        raise PasswordValidationError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters long.")

    if confirm_password is not None and password != confirm_password:
        raise PasswordValidationError("Passwords do not match.")


def hash_password(password: str) -> str:
    """
    Hashes a password with Argon2id using a unique cryptographically random salt.
    """
    validate_password_strength(password)
    return _hasher.hash(password)


def verify_password(stored_hash: str, candidate_password: str) -> bool:
    """
    Verifies candidate password against stored Argon2id hash in constant time.
    Returns True if valid, False otherwise.
    """
    if not stored_hash or not candidate_password:
        return False
    try:
        return _hasher.verify(stored_hash, candidate_password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(stored_hash: str) -> bool:
    """
    Checks if stored hash needs upgrading to newer parameters.
    """
    try:
        return _hasher.check_needs_rehash(stored_hash)
    except Exception:
        return True


def generate_recovery_code() -> str:
    """
    Generates a cryptographically random recovery code formatted as XXXX-XXXX-XXXX-XXXX.
    """
    alphabet = string.ascii_uppercase + string.digits
    groups = ["".join(secrets.choice(alphabet) for _ in range(4)) for _ in range(4)]
    return "-".join(groups)


def hash_recovery_code(code: str) -> str:
    """
    Hashes a recovery code for secure verifier storage.
    Normalizes by stripping hyphens and whitespace and converting to uppercase.
    """
    normalized = code.strip().replace("-", "").replace(" ", "").upper()
    return _hasher.hash(normalized)


def verify_recovery_code(stored_verifier: str, candidate_code: str) -> bool:
    """
    Verifies candidate recovery code against stored verifier.
    """
    if not stored_verifier or not candidate_code:
        return False
    normalized = candidate_code.strip().replace("-", "").replace(" ", "").upper()
    try:
        return _hasher.verify(stored_verifier, normalized)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False

