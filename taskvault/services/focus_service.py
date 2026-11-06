"""
Focus session and Pomodoro tracking service for TaskVault.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from taskvault.database import get_db_session
from taskvault.models.focus import FocusSession
from taskvault.security.access_control import require_auth
from taskvault.repositories import focus_repository


@require_auth
def record_focus_session(
    task_id: Optional[str],
    started_at: datetime,
    ended_at: Optional[datetime] = None,
    duration_seconds: int = 0,
    session_type: str = "focus",
    db_session: Optional[Session] = None,
) -> FocusSession:
    """Records a completed focus session and credits actual duration to the linked task."""
    if db_session:
        return focus_repository.create_focus_session(
            db=db_session,
            task_id=task_id,
            started_at=started_at,
            ended_at=ended_at,
            duration_seconds=duration_seconds,
            session_type=session_type,
        )
    with get_db_session() as db:
        return focus_repository.create_focus_session(
            db=db,
            task_id=task_id,
            started_at=started_at,
            ended_at=ended_at,
            duration_seconds=duration_seconds,
            session_type=session_type,
        )


@require_auth
def get_time_by_project(db_session: Optional[Session] = None) -> List[Dict[str, Any]]:
    """Retrieves total tracked actual duration per project."""
    if db_session:
        return focus_repository.get_total_time_by_project(db_session)
    with get_db_session() as db:
        return focus_repository.get_total_time_by_project(db)

