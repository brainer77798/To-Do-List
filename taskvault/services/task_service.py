"""
Task service layer for TaskVault.
Enforces authentication, business rules, and triggers activity logging & recurrence.
"""

from __future__ import annotations

from datetime import datetime, date
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from taskvault.database import get_db_session
from taskvault.models.task import Task, ChecklistItem
from taskvault.security.access_control import require_auth
from taskvault.repositories import task_repository, security_repository
from taskvault.services.recurrence_service import on_occurrence_completed


@require_auth
def get_task(task_id: str, db_session: Optional[Session] = None) -> Optional[Task]:
    """Retrieves a single task by ID."""
    if db_session:
        return task_repository.get_task_by_id(db_session, task_id)
    with get_db_session() as db:
        return task_repository.get_task_by_id(db, task_id)


@require_auth
def create_quick_task(
    title: str,
    project_id: Optional[str] = None,
    priority: str = "medium",
    due_at: Optional[datetime] = None,
    due_date_only: bool = False,
    planned_for_date: Optional[date] = None,
    db_session: Optional[Session] = None,
) -> Task:
    """Creates a task with minimal required fields."""
    def _do(db: Session) -> Task:
        task = task_repository.create_task(
            db=db,
            title=title,
            project_id=project_id,
            priority=priority,
            due_at=due_at,
            due_date_only=due_date_only,
            planned_for_date=planned_for_date,
        )
        security_repository.log_activity(db, action="task_created", entity_type="task", entity_id=task.id)
        return task

    if db_session:
        return _do(db_session)
    with get_db_session() as db:
        return _do(db)


@require_auth
def create_full_task(
    title: str,
    description: Optional[str] = None,
    status: str = "todo",
    priority: str = "medium",
    project_id: Optional[str] = None,
    parent_task_id: Optional[str] = None,
    category: Optional[str] = None,
    due_at: Optional[datetime] = None,
    due_date_only: bool = False,
    start_at: Optional[datetime] = None,
    planned_for_date: Optional[date] = None,
    estimated_minutes: Optional[int] = None,
    tag_names: Optional[List[str]] = None,
    checklist_texts: Optional[List[str]] = None,
    db_session: Optional[Session] = None,
) -> Task:
    """Creates a task with all available metadata."""
    def _do(db: Session) -> Task:
        task = task_repository.create_task(
            db=db,
            title=title,
            description=description,
            status=status,
            priority=priority,
            project_id=project_id,
            parent_task_id=parent_task_id,
            category=category,
            due_at=due_at,
            due_date_only=due_date_only,
            start_at=start_at,
            planned_for_date=planned_for_date,
            estimated_minutes=estimated_minutes,
            tag_names=tag_names,
            checklist_texts=checklist_texts,
        )
        security_repository.log_activity(db, action="task_created", entity_type="task", entity_id=task.id)
        return task

    if db_session:
        return _do(db_session)
    with get_db_session() as db:
        return _do(db)


@require_auth
def update_task_details(
    task_id: str,
    db_session: Optional[Session] = None,
    **kwargs: Any,
) -> Task:
    """Updates fields of an existing task."""
    def _do(db: Session) -> Task:
        task = task_repository.update_task(db, task_id, **kwargs)
        security_repository.log_activity(db, action="task_updated", entity_type="task", entity_id=task.id)
        return task

    if db_session:
        return _do(db_session)
    with get_db_session() as db:
        return _do(db)


@require_auth
def toggle_task_done(
    task_id: str,
    is_completed: bool,
    db_session: Optional[Session] = None,
) -> Task:
    """Toggles completion and generates next recurring occurrence if applicable."""
    def _do(db: Session) -> Task:
        task = task_repository.set_task_completion(db, task_id, is_completed)
        if is_completed and task.recurrence_series_id:
            on_occurrence_completed(task, db)
        action_name = "task_completed" if is_completed else "task_reopened"
        security_repository.log_activity(db, action=action_name, entity_type="task", entity_id=task.id)
        return task

    if db_session:
        return _do(db_session)
    with get_db_session() as db:
        return _do(db)


@require_auth
def soft_delete_task(task_id: str, db_session: Optional[Session] = None) -> Task:
    """Moves task to Trash."""
    def _do(db: Session) -> Task:
        task = task_repository.delete_task_to_trash(db, task_id)
        security_repository.log_activity(db, action="task_trashed", entity_type="task", entity_id=task.id)
        return task

    if db_session:
        return _do(db_session)
    with get_db_session() as db:
        return _do(db)


@require_auth
def restore_task_item(task_id: str, db_session: Optional[Session] = None) -> Task:
    """Restores task from Trash or Archive."""
    def _do(db: Session) -> Task:
        task = task_repository.restore_task(db, task_id)
        security_repository.log_activity(db, action="task_restored", entity_type="task", entity_id=task.id)
        return task

    if db_session:
        return _do(db_session)
    with get_db_session() as db:
        return _do(db)


@require_auth
def archive_task_item(task_id: str, db_session: Optional[Session] = None) -> Task:
    """Archives a task."""
    def _do(db: Session) -> Task:
        task = task_repository.archive_task(db, task_id)
        security_repository.log_activity(db, action="task_archived", entity_type="task", entity_id=task.id)
        return task

    if db_session:
        return _do(db_session)
    with get_db_session() as db:
        return _do(db)


@require_auth
def permanently_delete_task_item(task_id: str, db_session: Optional[Session] = None) -> bool:
    """Permanently deletes a task and all dependents."""
    def _do(db: Session) -> bool:
        res = task_repository.permanently_delete_task(db, task_id)
        security_repository.log_activity(db, action="task_deleted_permanently", entity_type="task", entity_id=task_id)
        return res

    if db_session:
        return _do(db_session)
    with get_db_session() as db:
        return _do(db)


@require_auth
def empty_trash_bin(db_session: Optional[Session] = None) -> int:
    """Empties the Trash."""
    def _do(db: Session) -> int:
        count = task_repository.empty_trash(db)
        security_repository.log_activity(db, action="trash_emptied", entity_type="task", details=f"Deleted {count} tasks")
        return count

    if db_session:
        return _do(db_session)
    with get_db_session() as db:
        return _do(db)


@require_auth
def duplicate_task_item(task_id: str, db_session: Optional[Session] = None) -> Task:
    """Duplicates a task."""
    def _do(db: Session) -> Task:
        task = task_repository.duplicate_task(db, task_id)
        security_repository.log_activity(db, action="task_duplicated", entity_type="task", entity_id=task.id)
        return task

    if db_session:
        return _do(db_session)
    with get_db_session() as db:
        return _do(db)


@require_auth
def query_tasks_filtered(
    db_session: Optional[Session] = None,
    **kwargs: Any,
) -> List[Task]:
    """Retrieves tasks using parameterized query filters."""
    if db_session:
        return task_repository.query_tasks(db_session, **kwargs)
    with get_db_session() as db:
        return task_repository.query_tasks(db, **kwargs)


@require_auth
def execute_bulk_operations(
    task_ids: List[str],
    action: str,
    action_value: Optional[Any] = None,
    db_session: Optional[Session] = None,
) -> int:
    """Performs bulk operations on multiple tasks."""
    def _do(db: Session) -> int:
        count = task_repository.execute_bulk_action(db, task_ids, action, action_value)
        security_repository.log_activity(
            db, action=f"bulk_{action}", entity_type="task", details=f"Affected {count} tasks"
        )
        return count

    if db_session:
        return _do(db_session)
    with get_db_session() as db:
        return _do(db)


@require_auth
def add_checklist_item_to_task(task_id: str, text: str, db_session: Optional[Session] = None) -> ChecklistItem:
    if db_session:
        return task_repository.add_checklist_item(db_session, task_id, text)
    with get_db_session() as db:
        return task_repository.add_checklist_item(db, task_id, text)


@require_auth
def toggle_checklist_item_status(item_id: str, is_completed: bool, db_session: Optional[Session] = None) -> ChecklistItem:
    if db_session:
        return task_repository.toggle_checklist_item(db_session, item_id, is_completed)
    with get_db_session() as db:
        return task_repository.toggle_checklist_item(db, item_id, is_completed)


@require_auth
def delete_checklist_item_by_id(item_id: str, db_session: Optional[Session] = None) -> bool:
    if db_session:
        return task_repository.delete_checklist_item(db_session, item_id)
    with get_db_session() as db:
        return task_repository.delete_checklist_item(db, item_id)

