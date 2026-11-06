"""
Repository for Project operations and analytics.
"""

from __future__ import annotations

from typing import List, Optional, Dict, Any
from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session

from taskvault.models.project import Project
from taskvault.models.task import Task
from taskvault.models.base import utc_now, generate_uuid


def get_projects(db: Session, status: Optional[str] = None) -> List[Project]:
    """Retrieves projects, optionally filtered by status ('active', 'completed', 'archived')."""
    stmt = select(Project)
    if status:
        stmt = stmt.where(Project.status == status)
    stmt = stmt.order_by(Project.name.asc())
    return list(db.execute(stmt).scalars().all())


def get_project_by_id(db: Session, project_id: str) -> Optional[Project]:
    """Retrieves a single project by ID."""
    return db.execute(select(Project).where(Project.id == project_id)).scalar_one_or_none()


def create_project(
    db: Session,
    name: str,
    description: Optional[str] = None,
    color: Optional[str] = "#3B82F6",
    icon: Optional[str] = "folder",
) -> Project:
    """Creates a new project."""
    clean_name = name.strip()
    if not clean_name:
        raise ValueError("Project name cannot be empty.")

    project = Project(
        id=generate_uuid(),
        name=clean_name,
        description=description.strip() if description else None,
        color=color or "#3B82F6",
        icon=icon or "folder",
        status="active",
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db.add(project)
    db.flush()
    return project


def update_project(db: Session, project_id: str, **kwargs: Any) -> Project:
    """Updates an existing project's attributes."""
    project = get_project_by_id(db, project_id)
    if not project:
        raise ValueError("Project not found.")

    if "name" in kwargs:
        val = kwargs["name"].strip()
        if not val:
            raise ValueError("Project name cannot be empty.")
        project.name = val

    if "description" in kwargs:
        project.description = kwargs["description"].strip() if kwargs["description"] else None
    if "color" in kwargs:
        project.color = kwargs["color"]
    if "icon" in kwargs:
        project.icon = kwargs["icon"]
    if "status" in kwargs:
        project.status = kwargs["status"]
        if project.status == "archived":
            project.archived_at = utc_now()
        elif project.archived_at is not None:
            project.archived_at = None

    project.updated_at = utc_now()
    db.flush()
    return project


def delete_project(db: Session, project_id: str, move_tasks_to_inbox: bool = True) -> bool:
    """
    Deletes a project. If move_tasks_to_inbox is True, reassigns tasks to None (Inbox).
    Never silently deletes tasks when deleting a project.
    """
    project = get_project_by_id(db, project_id)
    if not project:
        return False

    if move_tasks_to_inbox:
        # Move all tasks in this project to Inbox
        db.query(Task).filter(Task.project_id == project_id).update(
            {Task.project_id: None, Task.updated_at: utc_now()},
            synchronize_session="fetch",
        )
    else:
        # Check if project has tasks
        task_count = db.execute(
            select(func.count(Task.id)).where(Task.project_id == project_id)
        ).scalar_one()
        if task_count > 0:
            raise ValueError(f"Project has {task_count} linked tasks. Choose to move them to Inbox first.")

    db.delete(project)
    db.flush()
    return True


def get_project_stats(db: Session, project_id: str) -> Dict[str, Any]:
    """Calculates active task count, completed count, total count, and completion percentage."""
    total = db.execute(
        select(func.count(Task.id)).where(
            Task.project_id == project_id,
            Task.deleted_at.is_(None),
            Task.is_archived.is_(False),
        )
    ).scalar_one()

    completed = db.execute(
        select(func.count(Task.id)).where(
            Task.project_id == project_id,
            Task.status == "done",
            Task.deleted_at.is_(None),
            Task.is_archived.is_(False),
        )
    ).scalar_one()

    pct = round((completed / total * 100), 1) if total > 0 else 0.0

    return {
        "total_tasks": total,
        "completed_tasks": completed,
        "active_tasks": total - completed,
        "completion_percentage": pct,
    }

