"""
Base definitions and helpers for SQLAlchemy models.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone


def utc_now() -> datetime:
    """Returns the current timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


def generate_uuid() -> str:
    """Generates a standard UUID4 hex string."""
    return str(uuid.uuid4())

