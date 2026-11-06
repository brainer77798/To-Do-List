"""
In-app reminder service for TaskVault.
Finds overdue, due today, and due soon tasks and manages session dismissals.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session

from taskvault.database import get_db_session
from taskvault.security.access_control import require_auth
from taskvault.repositories import task_repository
from taskvault.utils.dates import is_overdue, is_due_today, is_due_soon


@require_auth
def get_active_reminders(
    timezone_name: str = "America/New_York",
    horizon_days: int = 7,
    dismissed_ids: Optional[set] = None,
    db_session: Optional[Session] = None,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Identifies tasks needing attention: Overdue, Due Today, and Due Soon.
    Filters out items dismissed during the active session.
    """
    dismissed = dismissed_ids or set()

    def _do(db: Session) -> Dict[str, List[Dict[str, Any]]]:
        active_tasks = task_repository.query_tasks(
            db,
            status="todo",
            is_archived=False,
            in_trash=False,
            exclude_subtasks=False,
        )

        overdue_list = []
        today_list = []
        soon_list = []

        for t in active_tasks:
            if not t.due_at or t.id in dismissed:
                continue

            item = {
                "id": t.id,
                "title": t.title,
                "priority": t.priority,
                "due_at": t.due_at,
                "project": t.project.name if t.project else None,
            }

            if is_overdue(t.due_at, timezone_name, t.due_date_only):
                overdue_list.append(item)
            elif is_due_today(t.due_at, timezone_name):
                today_list.append(item)
            elif is_due_soon(t.due_at, timezone_name, horizon_days):
                soon_list.append(item)

        return {
            "overdue": overdue_list,
            "due_today": today_list,
            "due_soon": soon_list,
        }

    if db_session:
        return _do(db_session)
    with get_db_session() as db:
        return _do(db)

