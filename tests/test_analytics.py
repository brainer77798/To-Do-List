"""
Tests for analytics service: dashboard metrics, streaks, and productivity trends.
Covers Section 7: Reporting & Insights requirements.

All service functions decorated with @require_auth are called through the
authenticated_session fixture so the access control guard is satisfied.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta, date

from taskvault.repositories import task_repository
from taskvault.services import analytics_service


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_done_task(db, title: str, completed_at: datetime):
    """Create a task and set it to 'done' at a specific UTC time."""
    task = task_repository.create_task(db, title=title, priority="medium")
    # update_task handles status='done' by setting completed_at automatically;
    # we pass completed_at override via the 'completed_at' attribute directly so
    # the exact timestamp lands in the DB for precise date assertions.
    task_repository.update_task(db, task.id, status="done")
    # Override completed_at to the exact moment we want
    task.completed_at = completed_at
    db.flush()
    return task


def _make_overdue_task(db, title: str, days_overdue: int = 3):
    """Create an active task with a past due_at so it counts as overdue."""
    past_dt = datetime.now(timezone.utc) - timedelta(days=days_overdue)
    task = task_repository.create_task(db, title=title, priority="high")
    task.due_at = past_dt
    db.flush()
    return task


# ---------------------------------------------------------------------------
# Dashboard metrics
# ---------------------------------------------------------------------------


def test_metrics_empty_vault(authenticated_session):
    """With no tasks, all dashboard metrics are zero."""
    metrics = analytics_service.get_dashboard_metrics(db_session=authenticated_session)
    assert metrics["active_count"] == 0
    assert metrics["completed_today"] == 0
    assert metrics["overdue_count"] == 0


def test_metrics_counts_active_tasks(authenticated_session):
    """active_count reflects non-archived, non-trashed, non-done tasks."""
    task_repository.create_task(authenticated_session, title="T1", priority="medium")
    task_repository.create_task(authenticated_session, title="T2", priority="high")
    metrics = analytics_service.get_dashboard_metrics(db_session=authenticated_session)
    assert metrics["active_count"] >= 2


def test_metrics_completed_today(authenticated_session):
    """completed_today counts tasks completed today (UTC)."""
    now_utc = datetime.now(timezone.utc)
    _make_done_task(authenticated_session, "Done today", now_utc)
    metrics = analytics_service.get_dashboard_metrics(db_session=authenticated_session)
    assert metrics["completed_today"] >= 1


def test_metrics_completed_today_excludes_yesterday(authenticated_session):
    """completed_today does NOT count tasks completed on a previous day."""
    yesterday = datetime.now(timezone.utc) - timedelta(days=1, seconds=1)
    _make_done_task(authenticated_session, "Done yesterday", yesterday)
    metrics = analytics_service.get_dashboard_metrics(db_session=authenticated_session)
    assert metrics["completed_today"] == 0


def test_metrics_overdue_count(authenticated_session):
    """overdue_count counts active tasks whose due_at is in the past."""
    _make_overdue_task(authenticated_session, "Overdue task A")
    _make_overdue_task(authenticated_session, "Overdue task B")
    metrics = analytics_service.get_dashboard_metrics(db_session=authenticated_session)
    assert metrics["overdue_count"] >= 2


def test_metrics_completed_not_counted_as_overdue(authenticated_session):
    """Done tasks with past due_at are NOT counted as overdue."""
    # Create and complete a task with a past due date
    past_dt = datetime.now(timezone.utc) - timedelta(days=5)
    task = task_repository.create_task(authenticated_session, title="Done late", priority="medium")
    task.due_at = past_dt
    authenticated_session.flush()
    task_repository.update_task(authenticated_session, task.id, status="done")

    metrics = analytics_service.get_dashboard_metrics(db_session=authenticated_session)
    assert metrics["overdue_count"] == 0


def test_metrics_weekly_completion_pct_is_float(authenticated_session):
    """weekly_completion_pct is always a float between 0.0 and 100.0."""
    metrics = analytics_service.get_dashboard_metrics(db_session=authenticated_session)
    pct = metrics["weekly_completion_pct"]
    assert isinstance(pct, float)
    assert 0.0 <= pct <= 100.0


# ---------------------------------------------------------------------------
# Streak calculation
# ---------------------------------------------------------------------------


def test_streak_zero_with_no_completions(authenticated_session):
    """Current streak is 0 when nothing is completed."""
    result = analytics_service.calculate_streak(db_session=authenticated_session)
    assert result["current_streak"] == 0


def test_streak_one_for_today_only(authenticated_session):
    """Completing one task today gives a streak >= 1."""
    _make_done_task(authenticated_session, "Today", datetime.now(timezone.utc))
    result = analytics_service.calculate_streak(db_session=authenticated_session)
    assert result["current_streak"] >= 1


def test_streak_consecutive_days(authenticated_session):
    """Completing tasks on 3 consecutive days accumulates a streak of >= 3."""
    now = datetime.now(timezone.utc)
    for days_ago in [0, 1, 2]:
        _make_done_task(authenticated_session, f"Day -{days_ago}", now - timedelta(days=days_ago))
    result = analytics_service.calculate_streak(db_session=authenticated_session)
    assert result["current_streak"] >= 3


def test_streak_broken_by_missing_day(authenticated_session):
    """A gap in completion days resets the streak; only the unbroken tail counts."""
    now = datetime.now(timezone.utc)
    # Complete today only; also 3 days ago — gap on days 1 and 2 breaks the streak
    _make_done_task(authenticated_session, "Today", now)
    _make_done_task(authenticated_session, "3 days ago", now - timedelta(days=3))
    result = analytics_service.calculate_streak(db_session=authenticated_session)
    # Streak should be 1 (only today is consecutive)
    assert result["current_streak"] == 1


# ---------------------------------------------------------------------------
# Productivity trends
# ---------------------------------------------------------------------------


def test_productivity_trends_returns_dict(authenticated_session):
    """get_productivity_trends returns a dict with expected keys."""
    result = analytics_service.get_productivity_trends(days=7, db_session=authenticated_session)
    assert isinstance(result, dict)
    assert "daily_trends" in result
    assert "priority_counts" in result
    assert "total_completions_in_period" in result


def test_productivity_trends_daily_trends_length(authenticated_session):
    """daily_trends list length equals days + 1 (start date inclusive)."""
    result = analytics_service.get_productivity_trends(days=7, db_session=authenticated_session)
    # Service builds daily_counts from day 0..days inclusive
    assert len(result["daily_trends"]) == 8  # days + 1


def test_productivity_trends_has_correct_keys_per_entry(authenticated_session):
    """Each daily_trends entry contains 'date' and 'completions' keys."""
    result = analytics_service.get_productivity_trends(days=7, db_session=authenticated_session)
    for entry in result["daily_trends"]:
        assert "date" in entry
        assert "completions" in entry


def test_productivity_trends_counts_completions(authenticated_session):
    """Completed tasks are reflected in the trends for their date."""
    now = datetime.now(timezone.utc)
    _make_done_task(authenticated_session, "Trend A", now)
    _make_done_task(authenticated_session, "Trend B", now)
    result = analytics_service.get_productivity_trends(days=7, db_session=authenticated_session)
    today_str = date.today().isoformat()
    today_entry = next((e for e in result["daily_trends"] if e["date"] == today_str), None)
    assert today_entry is not None
    assert today_entry["completions"] >= 2


def test_productivity_trends_respects_days_param(authenticated_session):
    """daily_trends length scales with the days parameter."""
    for days in [3, 14]:
        result = analytics_service.get_productivity_trends(days=days, db_session=authenticated_session)
        assert len(result["daily_trends"]) == days + 1  # inclusive start


def test_productivity_trends_priority_counts_all_priorities(authenticated_session):
    """priority_counts contains all four priority levels."""
    result = analytics_service.get_productivity_trends(days=7, db_session=authenticated_session)
    prio = result["priority_counts"]
    for level in ("urgent", "high", "medium", "low"):
        assert level in prio
        assert isinstance(prio[level], int)
