"""
Analytics and productivity insights service for TaskVault.
Generates metrics and trends without inventing false historical data.
"""

from __future__ import annotations

from datetime import datetime, date, timedelta, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session

from taskvault.database import get_db_session
from taskvault.models.task import Task
from taskvault.models.project import Project
from taskvault.security.access_control import require_auth
from taskvault.utils.dates import get_local_today, get_zoneinfo


@require_auth
def get_dashboard_metrics(
    timezone_name: str = "America/New_York",
    due_soon_days: int = 7,
    db_session: Optional[Session] = None,
) -> Dict[str, Any]:
    """Computes headline metrics for the dashboard view."""
    def _do(db: Session) -> Dict[str, Any]:
        today = get_local_today(timezone_name)
        zi = get_zoneinfo(timezone_name)

        # Start and end of today in UTC
        today_start_local = datetime.combine(today, datetime.min.time()).replace(tzinfo=zi)
        today_end_local = datetime.combine(today, datetime.max.time()).replace(tzinfo=zi)
        today_start_utc = today_start_local.astimezone(timezone.utc)
        today_end_utc = today_end_local.astimezone(timezone.utc)

        # Start of current week (Monday)
        start_of_week_date = today - timedelta(days=today.weekday())
        start_of_week_local = datetime.combine(start_of_week_date, datetime.min.time()).replace(tzinfo=zi)
        start_of_week_utc = start_of_week_local.astimezone(timezone.utc)

        # Active tasks (not done, not in trash, not archived)
        active_count = db.execute(
            select(func.count(Task.id)).where(
                Task.status != "done",
                Task.deleted_at.is_(None),
                Task.is_archived.is_(False),
                Task.parent_task_id.is_(None),
            )
        ).scalar_one()

        # Overdue count
        now_utc = datetime.now(timezone.utc)
        overdue_count = db.execute(
            select(func.count(Task.id)).where(
                Task.status != "done",
                Task.deleted_at.is_(None),
                Task.is_archived.is_(False),
                Task.due_at.is_not(None),
                Task.due_at < now_utc,
            )
        ).scalar_one()

        # Due today count
        due_today_count = db.execute(
            select(func.count(Task.id)).where(
                Task.deleted_at.is_(None),
                Task.is_archived.is_(False),
                Task.due_at.is_not(None),
                Task.due_at >= today_start_utc,
                Task.due_at <= today_end_utc,
            )
        ).scalar_one()

        # Completed today
        completed_today = db.execute(
            select(func.count(Task.id)).where(
                Task.status == "done",
                Task.deleted_at.is_(None),
                Task.completed_at >= today_start_utc,
                Task.completed_at <= today_end_utc,
            )
        ).scalar_one()

        # Completed this week
        completed_this_week = db.execute(
            select(func.count(Task.id)).where(
                Task.status == "done",
                Task.deleted_at.is_(None),
                Task.completed_at >= start_of_week_utc,
            )
        ).scalar_one()

        # Weekly completion rate
        tasks_due_or_completed_this_week = db.execute(
            select(func.count(Task.id)).where(
                Task.deleted_at.is_(None),
                Task.is_archived.is_(False),
                (
                    (Task.due_at >= start_of_week_utc)
                    | (Task.completed_at >= start_of_week_utc)
                ),
            )
        ).scalar_one()

        week_pct = (
            round((completed_this_week / tasks_due_or_completed_this_week * 100), 1)
            if tasks_due_or_completed_this_week > 0
            else 0.0
        )

        return {
            "active_count": active_count,
            "overdue_count": overdue_count,
            "due_today_count": due_today_count,
            "completed_today": completed_today,
            "completed_this_week": completed_this_week,
            "weekly_completion_pct": week_pct,
        }

    if db_session:
        return _do(db_session)
    with get_db_session() as db:
        return _do(db)


@require_auth
def get_productivity_trends(
    days: int = 30,
    timezone_name: str = "America/New_York",
    db_session: Optional[Session] = None,
) -> Dict[str, Any]:
    """Computes daily completion trends and priority breakdown for Insights."""
    def _do(db: Session) -> Dict[str, Any]:
        today = get_local_today(timezone_name)
        zi = get_zoneinfo(timezone_name)
        start_date = today - timedelta(days=days)
        start_dt_utc = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=zi).astimezone(timezone.utc)

        # Query completed tasks within time window
        completed_tasks = db.execute(
            select(Task.completed_at).where(
                Task.status == "done",
                Task.deleted_at.is_(None),
                Task.completed_at.is_not(None),
                Task.completed_at >= start_dt_utc,
            )
        ).scalars().all()

        # Group completions by local day
        daily_counts: Dict[str, int] = {}
        for d in range(days + 1):
            cur_day = (start_date + timedelta(days=d)).isoformat()
            daily_counts[cur_day] = 0

        for ct in completed_tasks:
            if ct:
                local_ct = ct.astimezone(zi).date().isoformat()
                if local_ct in daily_counts:
                    daily_counts[local_ct] += 1

        # Priority breakdown across active tasks
        priorities = ["urgent", "high", "medium", "low"]
        priority_counts: Dict[str, int] = {}
        for p in priorities:
            c = db.execute(
                select(func.count(Task.id)).where(
                    Task.priority == p,
                    Task.status != "done",
                    Task.deleted_at.is_(None),
                    Task.is_archived.is_(False),
                )
            ).scalar_one()
            priority_counts[p] = c

        return {
            "daily_trends": [{"date": k, "completions": v} for k, v in daily_counts.items()],
            "priority_counts": priority_counts,
            "total_completions_in_period": len(completed_tasks),
        }

    if db_session:
        return _do(db_session)
    with get_db_session() as db:
        return _do(db)


@require_auth
def calculate_streak(
    timezone_name: str = "America/New_York",
    db_session: Optional[Session] = None,
) -> Dict[str, int]:
    """Computes current consecutive daily completion streak without gamified pressure."""
    def _do(db: Session) -> Dict[str, int]:
        today = get_local_today(timezone_name)
        zi = get_zoneinfo(timezone_name)

        # Get all distinct completion dates in local timezone
        completed_times = db.execute(
            select(Task.completed_at).where(
                Task.status == "done",
                Task.deleted_at.is_(None),
                Task.completed_at.is_not(None),
            )
        ).scalars().all()

        completion_dates = set()
        for ct in completed_times:
            if ct:
                completion_dates.add(ct.astimezone(zi).date())

        current_streak = 0
        check_date = today
        if check_date not in completion_dates:
            # Check if yesterday had completion
            check_date = today - timedelta(days=1)

        while check_date in completion_dates:
            current_streak += 1
            check_date -= timedelta(days=1)

        return {"current_streak": current_streak}

    if db_session:
        return _do(db_session)
    with get_db_session() as db:
        return _do(db)

