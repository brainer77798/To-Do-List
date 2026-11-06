"""
Tests for recurrence engine: frequency math, month-end clipping, leap years, and idempotency.
"""

import pytest
from datetime import date
from taskvault.services.recurrence_service import (
    calculate_next_occurrence,
    create_recurrence_series,
    on_occurrence_completed,
)
from taskvault.services import task_service


def test_daily_recurrence():
    start = date(2026, 3, 10)
    nxt = calculate_next_occurrence(frequency="daily", interval=1, current_date=start)
    assert nxt == date(2026, 3, 11)

    nxt2 = calculate_next_occurrence(frequency="daily", interval=3, current_date=start)
    assert nxt2 == date(2026, 3, 13)


def test_weekdays_recurrence():
    # Friday 2026-03-13 -> should skip weekend to Monday 2026-03-16
    friday = date(2026, 3, 13)
    nxt = calculate_next_occurrence(frequency="weekdays", interval=1, current_date=friday)
    assert nxt == date(2026, 3, 16)


def test_weekly_recurrence():
    # Monday 2026-03-09 (weekday 0), recurring on Wednesday (2) and Friday (4)
    mon = date(2026, 3, 9)
    nxt = calculate_next_occurrence(frequency="weekly", interval=1, current_date=mon, weekdays=[2, 4])
    assert nxt == date(2026, 3, 11)  # Wednesday

    # From Friday 2026-03-13 -> should wrap around to next Monday's week Wednesday 2026-03-18
    fri = date(2026, 3, 13)
    nxt_wrap = calculate_next_occurrence(frequency="weekly", interval=1, current_date=fri, weekdays=[2, 4])
    assert nxt_wrap == date(2026, 3, 18)


def test_monthly_month_end_clamping():
    # Target day 31: January 31 -> February (non-leap year 2027 or leap year 2028)
    jan_31 = date(2027, 1, 31)
    nxt_feb = calculate_next_occurrence(frequency="monthly", interval=1, current_date=jan_31, day_of_month=31)
    assert nxt_feb == date(2027, 2, 28)  # Clamped to 28 days

    # 31st into April (30 days)
    mar_31 = date(2027, 3, 31)
    nxt_apr = calculate_next_occurrence(frequency="monthly", interval=1, current_date=mar_31, day_of_month=31)
    assert nxt_apr == date(2027, 4, 30)  # Clamped to 30 days


def test_yearly_leap_year_handling():
    # Feb 29, 2028 (leap year) -> 2029 (non-leap year, should become Feb 28)
    leap_date = date(2028, 2, 29)
    nxt_year = calculate_next_occurrence(frequency="yearly", interval=1, current_date=leap_date, day_of_month=29)
    assert nxt_year == date(2029, 2, 28)


def test_recurrence_series_idempotency_and_completion(authenticated_session):
    start = date(2026, 5, 1)
    series = create_recurrence_series(
        title="Weekly Team Status",
        frequency="weekly",
        interval=1,
        start_date=start,
        db_session=authenticated_session,
    )
    assert series.id is not None

    # First task occurrence was generated
    tasks = task_service.query_tasks_filtered(db_session=authenticated_session)
    assert len(tasks) == 1
    t1 = tasks[0]
    assert t1.recurrence_series_id == series.id

    # Mark first occurrence done
    task_service.toggle_task_done(t1.id, is_completed=True, db_session=authenticated_session)

    # Next occurrence should now be created
    all_tasks = task_service.query_tasks_filtered(db_session=authenticated_session)
    assert len(all_tasks) == 2

    # Calling completion again should be idempotent and not create duplicate
    on_occurrence_completed(t1, authenticated_session)
    all_tasks_after = task_service.query_tasks_filtered(db_session=authenticated_session)
    assert len(all_tasks_after) == 2

