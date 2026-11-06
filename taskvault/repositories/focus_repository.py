"""
Repository for FocusSession and Time Tracking operations.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session

from taskvault.models.focus import FocusSession
from taskvault.models.task import Task
from taskvault.models.project import Project
from taskvault.models.base import utc_now, generate_uuid


def create_focus_session(
    db: Session,
    task_id: Optional[str],
    started_at: datetime,
    ended_at: Optional[datetime] = None,
    duration_seconds: int = 0,
    session_type: str = "focus",
) -> FocusSession:
    """Records a completed or in-progress focus/break session."""
    session = FocusSession(
        id=generate_uuid(),
        task_id=task_id,
        started_at=started_at,
        ended_at=ended_at or utc_now(),
        duration_seconds=max(0, duration_seconds),
        session_type=session_type,
        created_at=utc_now(),
    )
    db.add(session)

    # If linked to a task and duration > 0, update actual_minutes on task
    if task_id and duration_seconds > 0:
        task = db.execute(select(Task).where(Task.id == task_id)).scalar_one_or_none()
        if task:
            mins = duration_seconds // 60
            task.actual_minutes = (task.actual_minutes or 0) + mins
            task.updated_at = utc_now()

    db.flush()
    return session


def get_focus_sessions(
    db: Session,
    task_id: Optional[str] = None,
    since: Optional[datetime] = None,
) -> List[FocusSession]:
    """Retrieves focus sessions filtered by task or timestamp."""
    stmt = select(FocusSession)
    conditions = []
    if task_id:
        conditions.append(FocusSession.task_id == task_id)
    if since:
        conditions.append(FocusSession.started_at >= since)
    if conditions:
        stmt = stmt.where(and_(*conditions))
    stmt = stmt.order_by(FocusSession.started_at.desc())
    return list(db.execute(stmt).scalars().all())


def get_total_time_by_project(db: Session) -> List[Dict[str, Any]]:
    """Calculates total tracked actual minutes aggregated by project."""
    stmt = (
        select(
            Project.name.label("project_name"),
            Project.color.label("color"),
            func.sum(Task.actual_minutes).label("total_minutes"),
        )
        .join(Task, Task.project_id == Project.id)
        .where(
            Task.deleted_at.is_(None),
            Task.actual_minutes > 0,
        )
        .group_by(Project.id, Project.name, Project.color)
    )
    rows = db.execute(stmt).all()
    return [
        {
            "project_name": r.project_name,
            "color": r.color or "#3B82F6",
            "total_minutes": int(r.total_minutes or 0),
        }
        for r in rows
    ]

