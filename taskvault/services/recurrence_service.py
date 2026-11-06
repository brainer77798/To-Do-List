"""
Recurrence service for TaskVault.
Accurately computes next occurrence dates, handles month lengths, leap years,
and guarantees idempotent occurrence generation without duplicates.
"""

from __future__ import annotations

import json
import calendar
from datetime import datetime, date, time, timedelta, timezone
from typing import List, Optional, Dict, Any
from dateutil.relativedelta import relativedelta
from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from taskvault.database import get_db_session
from taskvault.models.task import Task, RecurrenceSeries
from taskvault.models.base import utc_now, generate_uuid
from taskvault.utils.dates import get_zoneinfo, to_utc, to_local
from taskvault.security.access_control import require_auth
from taskvault.repositories.task_repository import create_task


def calculate_next_occurrence(
    frequency: str,
    interval: int,
    current_date: date,
    weekdays: Optional[List[int]] = None,
    day_of_month: Optional[int] = None,
) -> date:
    """
    Computes the next target date based on frequency rules, handling edge cases:
    - Month lengths (e.g. 31st when target month has only 30 or 28 days)
    - Leap years (Feb 29)
    - Weekdays (Mon-Fri)
    """
    interval = max(1, interval)

    if frequency == "daily":
        return current_date + timedelta(days=interval)

    elif frequency == "weekdays":
        # Advance day by day until a weekday (0=Mon, 4=Fri) is found
        candidate = current_date + timedelta(days=1)
        while candidate.weekday() > 4:  # 5=Sat, 6=Sun
            candidate += timedelta(days=1)
        return candidate

    elif frequency == "weekly":
        target_weekdays = sorted(weekdays) if weekdays else [current_date.weekday()]
        # Check remaining days in the same week
        for wd in target_weekdays:
            if wd > current_date.weekday():
                diff = wd - current_date.weekday()
                return current_date + timedelta(days=diff)
        # Advance by interval weeks to the first target weekday
        first_wd = target_weekdays[0]
        days_ahead = (7 * interval) - (current_date.weekday() - first_wd)
        return current_date + timedelta(days=days_ahead)

    elif frequency == "monthly":
        target_day = day_of_month or current_date.day
        # Move interval months ahead
        next_month_ref = current_date + relativedelta(months=interval)
        # Handle month length capping (e.g. 31st in a 30-day month or Feb)
        max_days = calendar.monthrange(next_month_ref.year, next_month_ref.month)[1]
        clamped_day = min(target_day, max_days)
        return date(next_month_ref.year, next_month_ref.month, clamped_day)

    elif frequency == "yearly":
        target_month = current_date.month
        target_day = day_of_month or current_date.day
        next_year = current_date.year + interval
        # Handle leap year edge case (Feb 29 -> Feb 28 on non-leap years)
        if target_month == 2 and target_day == 29 and not calendar.isleap(next_year):
            return date(next_year, 2, 28)
        return date(next_year, target_month, target_day)

    elif frequency == "custom":
        return current_date + timedelta(days=interval)

    else:
        return current_date + timedelta(days=1)


def generate_occurrence_key(series_id: str, target_date: date) -> str:
    """Generates a stable key ensuring idempotency."""
    return f"{series_id}_{target_date.isoformat()}"


@require_auth
def create_recurrence_series(
    title: str,
    frequency: str,
    interval: int = 1,
    weekdays: Optional[List[int]] = None,
    day_of_month: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    description: Optional[str] = None,
    priority: str = "medium",
    project_id: Optional[str] = None,
    category: Optional[str] = None,
    estimated_minutes: Optional[int] = None,
    timezone_name: str = "America/New_York",
    db_session: Optional[Session] = None,
) -> RecurrenceSeries:
    """Creates a new recurrence template and generates its initial task occurrence."""
    clean_title = title.strip()
    if not clean_title:
        raise ValueError("Series title cannot be empty.")

    st_date = start_date or date.today()
    weekdays_json = json.dumps(weekdays) if weekdays else None

    # Compute initial occurrence due datetime
    zi = get_zoneinfo(timezone_name)
    local_dt = datetime.combine(st_date, time(9, 0)).replace(tzinfo=zi)
    initial_due_utc = local_dt.astimezone(timezone.utc)

    def _do_create(db: Session) -> RecurrenceSeries:
        series = RecurrenceSeries(
            id=generate_uuid(),
            title=clean_title,
            description=description.strip() if description else None,
            priority=priority.lower(),
            project_id=project_id,
            category=category.strip() if category else None,
            estimated_minutes=estimated_minutes,
            frequency=frequency.lower(),
            interval=max(1, interval),
            weekdays=weekdays_json,
            day_of_month=day_of_month,
            start_date=st_date,
            end_date=end_date,
            next_occurrence_at=initial_due_utc,
            timezone=timezone_name,
            is_paused=False,
            missed_occurrence_policy="skip",
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        db.add(series)
        db.flush()

        # Generate the first task occurrence
        occ_key = generate_occurrence_key(series.id, st_date)
        create_task(
            db=db,
            title=series.title,
            description=series.description,
            status="todo",
            priority=series.priority,
            project_id=series.project_id,
            category=series.category,
            due_at=initial_due_utc,
            due_date_only=True,
            estimated_minutes=series.estimated_minutes,
            recurrence_series_id=series.id,
            occurrence_key=occ_key,
        )
        return series

    if db_session:
        return _do_create(db_session)
    with get_db_session() as db:
        return _do_create(db)


@require_auth
def on_occurrence_completed(task: Task, db: Session) -> Optional[Task]:
    """
    Called when a recurring task occurrence is completed:
    Calculates next recurrence date and schedules the next occurrence idempotently.
    """
    if not task.recurrence_series_id:
        return None

    series = db.execute(
        select(RecurrenceSeries).where(RecurrenceSeries.id == task.recurrence_series_id)
    ).scalar_one_or_none()
    if not series or series.is_paused:
        return None

    tz_name = series.timezone or "America/New_York"
    zi = get_zoneinfo(tz_name)

    # Base date is current task due date or today
    base_date = to_local(task.due_at, tz_name).date() if task.due_at else date.today()
    parsed_weekdays = json.loads(series.weekdays) if series.weekdays else None

    next_date = calculate_next_occurrence(
        frequency=series.frequency,
        interval=series.interval,
        current_date=base_date,
        weekdays=parsed_weekdays,
        day_of_month=series.day_of_month,
    )

    # Check end date
    if series.end_date and next_date > series.end_date:
        series.is_paused = True
        return None

    occ_key = generate_occurrence_key(series.id, next_date)

    # Check if occurrence already exists (idempotency check)
    existing = db.execute(
        select(Task).where(
            and_(
                Task.recurrence_series_id == series.id,
                Task.occurrence_key == occ_key,
            )
        )
    ).scalar_one_or_none()
    if existing:
        return existing

    next_dt_local = datetime.combine(next_date, time(9, 0)).replace(tzinfo=zi)
    next_due_utc = next_dt_local.astimezone(timezone.utc)
    series.next_occurrence_at = next_due_utc
    series.updated_at = utc_now()

    new_task = create_task(
        db=db,
        title=series.title,
        description=series.description,
        status="todo",
        priority=series.priority,
        project_id=series.project_id,
        category=series.category,
        due_at=next_due_utc,
        due_date_only=True,
        estimated_minutes=series.estimated_minutes,
        recurrence_series_id=series.id,
        occurrence_key=occ_key,
    )
    return new_task

