"""
Date and timezone utilities for TaskVault.
Accurately handles UTC storage and conversion to owner's configured IANA timezone.
"""

from __future__ import annotations

from datetime import datetime, date, time, timezone, timedelta
from typing import Optional, Tuple
from zoneinfo import ZoneInfo


def get_zoneinfo(tz_name: str) -> ZoneInfo:
    """Returns ZoneInfo object, falling back to UTC if invalid."""
    try:
        return ZoneInfo(tz_name)
    except Exception:
        return ZoneInfo("America/New_York")


def to_utc(dt: datetime, tz_name: str) -> datetime:
    """Converts a local datetime to UTC."""
    if dt.tzinfo is None:
        zi = get_zoneinfo(tz_name)
        dt = dt.replace(tzinfo=zi)
    return dt.astimezone(timezone.utc)


def to_local(dt: Optional[datetime], tz_name: str) -> Optional[datetime]:
    """Converts a UTC datetime to user's configured local timezone."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(get_zoneinfo(tz_name))


def get_local_today(tz_name: str) -> date:
    """Returns today's date in user's local timezone."""
    now_utc = datetime.now(timezone.utc)
    now_local = now_utc.astimezone(get_zoneinfo(tz_name))
    return now_local.date()


def get_local_now(tz_name: str) -> datetime:
    """Returns current datetime in user's local timezone."""
    return datetime.now(timezone.utc).astimezone(get_zoneinfo(tz_name))


def is_overdue(due_at: Optional[datetime], tz_name: str, due_date_only: bool = False) -> bool:
    """
    Checks if a due datetime is in the past.
    For date-only tasks, considered overdue if due date is before today in user's local timezone.
    For datetime tasks, considered overdue if due_at < current UTC time.
    """
    if due_at is None:
        return False
    now_utc = datetime.now(timezone.utc)
    if due_date_only:
        local_due = to_local(due_at, tz_name)
        if not local_due:
            return False
        return local_due.date() < get_local_today(tz_name)
    else:
        if due_at.tzinfo is None:
            due_at = due_at.replace(tzinfo=timezone.utc)
        return due_at < now_utc


def is_due_today(due_at: Optional[datetime], tz_name: str) -> bool:
    """Checks if a due datetime falls on user's current local date."""
    if due_at is None:
        return False
    local_due = to_local(due_at, tz_name)
    if not local_due:
        return False
    return local_due.date() == get_local_today(tz_name)


def is_due_soon(due_at: Optional[datetime], tz_name: str, horizon_days: int = 7) -> bool:
    """
    Checks if a due date is between tomorrow and (today + horizon_days).
    """
    if due_at is None:
        return False
    local_due = to_local(due_at, tz_name)
    if not local_due:
        return False
    today = get_local_today(tz_name)
    horizon = today + timedelta(days=horizon_days)
    return today < local_due.date() <= horizon


def format_relative_due(due_at: Optional[datetime], tz_name: str, due_date_only: bool = False) -> str:
    """Returns a friendly relative human string for due dates."""
    if due_at is None:
        return "No due date"

    local_due = to_local(due_at, tz_name)
    if not local_due:
        return ""

    today = get_local_today(tz_name)
    due_date = local_due.date()
    diff = (due_date - today).days

    time_str = "" if due_date_only else f" at {local_due.strftime('%I:%M %p')}"

    if diff < -1:
        return f"{abs(diff)} days overdue"
    elif diff == -1:
        return f"Yesterday{time_str}"
    elif diff == 0:
        return f"Today{time_str}"
    elif diff == 1:
        return f"Tomorrow{time_str}"
    elif 1 < diff <= 7:
        return f"{local_due.strftime('%A')}{time_str}"
    else:
        return f"{local_due.strftime('%b %d, %Y')}{time_str}"

