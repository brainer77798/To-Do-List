"""
Persistent database-backed rate limiting and lockout manager.
Enforces Section 3.4 failed-attempt protection.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import Session

from taskvault.models.security import LoginAttempt
from taskvault.models.base import utc_now
from taskvault.config import (
    MAX_FAILED_ATTEMPTS,
    LOCKOUT_WINDOW_MINUTES,
    INITIAL_LOCKOUT_MINUTES,
    MAX_LOCKOUT_MINUTES,
)


class RateLimitExceededError(Exception):
    """Raised when authentication attempts are blocked by rate limiting."""
    def __init__(self, blocked_until: datetime, retry_after_seconds: int):
        self.blocked_until = blocked_until
        self.retry_after_seconds = retry_after_seconds
        super().__init__("Unable to unlock. Check your password or try again later.")


def check_rate_limit(
    db: Session,
    source_fingerprint: str | None = None,
    identifier: str | None = None,
) -> None:
    """
    Checks if login attempts are currently blocked.
    Raises RateLimitExceededError if currently in lockout.
    """
    now = utc_now()

    # Check if there is an active lockout globally or for this identifier
    conditions = [
        LoginAttempt.blocked_until.is_not(None),
        LoginAttempt.blocked_until > now,
    ]
    if identifier:
        clean_id = identifier.strip().lower()
        query = (
            select(LoginAttempt.blocked_until)
            .where(
                and_(
                    *conditions,
                    or_(
                        LoginAttempt.identifier == clean_id,
                        LoginAttempt.identifier.is_(None),
                    ),
                )
            )
            .order_by(LoginAttempt.blocked_until.desc())
            .limit(1)
        )
    else:
        query = (
            select(LoginAttempt.blocked_until)
            .where(and_(*conditions))
            .order_by(LoginAttempt.blocked_until.desc())
            .limit(1)
        )
    active_block = db.execute(query).scalar_one_or_none()
    if active_block:
        if active_block.tzinfo is None:
            active_block = active_block.replace(tzinfo=timezone.utc)
        retry_seconds = max(1, int((active_block - now).total_seconds()))
        raise RateLimitExceededError(active_block, retry_seconds)


def record_login_attempt(
    db: Session,
    succeeded: bool,
    source_fingerprint: str | None = None,
    identifier: str | None = None,
) -> None:
    """
    Records an authentication attempt. If failed, checks rolling threshold and sets blocked_until.
    If succeeded, clears old failed attempts.
    """
    now = utc_now()
    clean_id = identifier.strip().lower() if identifier else None

    if succeeded:
        # Record success
        db.add(LoginAttempt(
            attempted_at=now,
            succeeded=True,
            source_fingerprint=source_fingerprint,
            identifier=clean_id,
        ))
        # Cleanup older failed attempts after successful unlock
        cutoff = now - timedelta(hours=24)
        db.query(LoginAttempt).filter(LoginAttempt.attempted_at < cutoff).delete()
        db.flush()
        return

    # Record failure
    window_start = now - timedelta(minutes=LOCKOUT_WINDOW_MINUTES)

    # Count recent failures in the rolling window
    fail_query = select(func.count(LoginAttempt.id)).where(
        and_(
            LoginAttempt.succeeded.is_(False),
            LoginAttempt.attempted_at >= window_start,
        )
    )
    if clean_id:
        fail_query = fail_query.where(
            or_(
                LoginAttempt.identifier == clean_id,
                LoginAttempt.identifier.is_(None),
            )
        )

    fail_count = db.execute(fail_query).scalar_one() + 1  # Including this attempt

    blocked_until: datetime | None = None
    if fail_count >= MAX_FAILED_ATTEMPTS:
        # Check previous lockout history to apply exponential/escalating penalty
        prev_lockouts = db.execute(
            select(func.count(LoginAttempt.id)).where(
                and_(
                    LoginAttempt.blocked_until.is_not(None),
                    LoginAttempt.attempted_at >= now - timedelta(hours=24),
                )
            )
        ).scalar_one()

        lockout_duration_mins = min(
            INITIAL_LOCKOUT_MINUTES * (2 ** prev_lockouts),
            MAX_LOCKOUT_MINUTES
        )
        blocked_until = now + timedelta(minutes=lockout_duration_mins)

    attempt = LoginAttempt(
        attempted_at=now,
        succeeded=False,
        source_fingerprint=source_fingerprint,
        identifier=clean_id,
        blocked_until=blocked_until,
    )
    db.add(attempt)
    db.flush()

    if blocked_until:
        retry_seconds = max(1, int((blocked_until - now).total_seconds()))
        raise RateLimitExceededError(blocked_until, retry_seconds)
