"""
Repository for Task, ChecklistItem, and Subtask operations.
"""

from __future__ import annotations

from datetime import datetime, date, timezone
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy import select, and_, or_, func, case
from sqlalchemy.orm import Session, joinedload, selectinload

from taskvault.models.task import Task, ChecklistItem
from taskvault.models.project import Project
from taskvault.models.tag import Tag, TaskTag
from taskvault.models.base import utc_now, generate_uuid
from taskvault.repositories.tag_repository import get_or_create_tags


# Priority numerical rank for sorting (Urgent > High > Medium > Low)
PRIORITY_RANK = case(
    (Task.priority == "urgent", 4),
    (Task.priority == "high", 3),
    (Task.priority == "medium", 2),
    (Task.priority == "low", 1),
    else_=0,
)


def get_task_by_id(db: Session, task_id: str) -> Optional[Task]:
    """Retrieves a task with preloaded relationships."""
    return (
        db.execute(
            select(Task)
            .options(
                selectinload(Task.project),
                selectinload(Task.tags),
                selectinload(Task.checklist_items),
                selectinload(Task.subtasks),
            )
            .where(Task.id == task_id)
        )
        .scalar_one_or_none()
    )


def create_task(
    db: Session,
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
    recurrence_series_id: Optional[str] = None,
    occurrence_key: Optional[str] = None,
) -> Task:
    """Creates a new task with optional subtasks, tags, and checklist items."""
    clean_title = title.strip()
    if not clean_title:
        raise ValueError("Task title cannot be empty.")

    # Validate parent task to prevent self-reference or deep cycles
    if parent_task_id:
        parent = db.execute(select(Task).where(Task.id == parent_task_id)).scalar_one_or_none()
        if not parent:
            raise ValueError("Specified parent task does not exist.")
        if parent.parent_task_id is not None:
            raise ValueError("Nesting is restricted to 1 level below parent task.")

    now = utc_now()
    completed_at = now if status == "done" else None

    task = Task(
        id=generate_uuid(),
        title=clean_title,
        description=description.strip() if description else None,
        status=status,
        priority=priority.lower() if priority else "medium",
        project_id=project_id,
        parent_task_id=parent_task_id,
        category=category.strip() if category else None,
        due_at=due_at,
        due_date_only=due_date_only,
        start_at=start_at,
        planned_for_date=planned_for_date,
        estimated_minutes=estimated_minutes,
        actual_minutes=0,
        is_archived=False,
        deleted_at=None,
        completed_at=completed_at,
        created_at=now,
        updated_at=now,
        recurrence_series_id=recurrence_series_id,
        occurrence_key=occurrence_key,
    )
    db.add(task)
    db.flush()

    # Associate tags
    if tag_names:
        tags = get_or_create_tags(db, tag_names)
        task.tags = tags

    # Add checklist items
    if checklist_texts:
        for idx, item_text in enumerate(checklist_texts):
            clean_text = item_text.strip()
            if clean_text:
                item = ChecklistItem(
                    id=generate_uuid(),
                    task_id=task.id,
                    text=clean_text,
                    is_completed=False,
                    sort_order=idx,
                    created_at=now,
                    updated_at=now,
                )
                db.add(item)

    db.flush()
    return task


def update_task(db: Session, task_id: str, **kwargs: Any) -> Task:
    """Updates fields on an existing task."""
    task = get_task_by_id(db, task_id)
    if not task:
        raise ValueError("Task not found.")

    if "title" in kwargs:
        clean_title = kwargs["title"].strip()
        if not clean_title:
            raise ValueError("Task title cannot be empty.")
        task.title = clean_title

    if "description" in kwargs:
        task.description = kwargs["description"].strip() if kwargs["description"] else None

    if "status" in kwargs:
        new_status = kwargs["status"]
        if new_status == "done" and task.status != "done":
            task.completed_at = utc_now()
        elif new_status != "done":
            task.completed_at = None
        task.status = new_status

    if "priority" in kwargs:
        task.priority = kwargs["priority"].lower()

    if "project_id" in kwargs:
        task.project_id = kwargs["project_id"]

    if "parent_task_id" in kwargs:
        new_parent_id = kwargs["parent_task_id"]
        if new_parent_id == task.id:
            raise ValueError("A task cannot be its own parent.")
        if new_parent_id:
            parent = db.execute(select(Task).where(Task.id == new_parent_id)).scalar_one_or_none()
            if not parent:
                raise ValueError("Parent task does not exist.")
            if parent.parent_task_id is not None:
                raise ValueError("Nesting restricted to 1 level.")
        task.parent_task_id = new_parent_id

    if "category" in kwargs:
        task.category = kwargs["category"].strip() if kwargs["category"] else None

    if "due_at" in kwargs:
        task.due_at = kwargs["due_at"]

    if "due_date_only" in kwargs:
        task.due_date_only = bool(kwargs["due_date_only"])

    if "start_at" in kwargs:
        task.start_at = kwargs["start_at"]

    if "planned_for_date" in kwargs:
        task.planned_for_date = kwargs["planned_for_date"]

    if "estimated_minutes" in kwargs:
        task.estimated_minutes = kwargs["estimated_minutes"]

    if "actual_minutes" in kwargs:
        val = kwargs["actual_minutes"]
        if val is not None and val < 0:
            raise ValueError("Actual duration cannot be negative.")
        task.actual_minutes = val or 0

    if "sort_order" in kwargs:
        task.sort_order = kwargs["sort_order"]

    if "tag_names" in kwargs:
        task.tags = get_or_create_tags(db, kwargs["tag_names"])

    task.updated_at = utc_now()
    db.flush()
    return task


def set_task_completion(db: Session, task_id: str, is_completed: bool, complete_subtasks: bool = True) -> Task:
    """Toggles task completion."""
    task = get_task_by_id(db, task_id)
    if not task:
        raise ValueError("Task not found.")

    now = utc_now()
    if is_completed:
        task.status = "done"
        task.completed_at = now
        if complete_subtasks and task.subtasks:
            for sub in task.subtasks:
                sub.status = "done"
                sub.completed_at = now
                sub.updated_at = now
    else:
        task.status = "todo"
        task.completed_at = None

    task.updated_at = now
    db.flush()
    return task


def archive_task(db: Session, task_id: str) -> Task:
    """Archives a task."""
    task = get_task_by_id(db, task_id)
    if not task:
        raise ValueError("Task not found.")
    task.is_archived = True
    task.updated_at = utc_now()
    db.flush()
    return task


def restore_task(db: Session, task_id: str) -> Task:
    """Restores a task from archive or trash."""
    task = get_task_by_id(db, task_id)
    if not task:
        raise ValueError("Task not found.")
    task.is_archived = False
    task.deleted_at = None
    task.updated_at = utc_now()
    db.flush()
    return task


def delete_task_to_trash(db: Session, task_id: str) -> Task:
    """Soft-deletes a task to Trash."""
    task = get_task_by_id(db, task_id)
    if not task:
        raise ValueError("Task not found.")
    task.deleted_at = utc_now()
    task.updated_at = utc_now()
    db.flush()
    return task


def permanently_delete_task(db: Session, task_id: str) -> bool:
    """Permanently deletes a task and its dependents."""
    task = get_task_by_id(db, task_id)
    if not task:
        return False
    # SQLAlchemy cascade will remove checklist_items and subtasks
    db.delete(task)
    db.flush()
    return True


def empty_trash(db: Session) -> int:
    """Permanently deletes all tasks currently in Trash."""
    tasks = db.execute(select(Task).where(Task.deleted_at.is_not(None))).scalars().all()
    count = len(tasks)
    for task in tasks:
        db.delete(task)
    db.flush()
    return count


def duplicate_task(db: Session, task_id: str) -> Task:
    """Duplicates a task along with its checklist items and tags."""
    original = get_task_by_id(db, task_id)
    if not original:
        raise ValueError("Task not found.")

    tag_names = [t.name for t in original.tags]
    checklist_texts = [item.text for item in original.checklist_items]

    dup = create_task(
        db=db,
        title=f"{original.title} (Copy)",
        description=original.description,
        status="todo",
        priority=original.priority,
        project_id=original.project_id,
        parent_task_id=None,
        category=original.category,
        due_at=original.due_at,
        due_date_only=original.due_date_only,
        start_at=original.start_at,
        planned_for_date=original.planned_for_date,
        estimated_minutes=original.estimated_minutes,
        tag_names=tag_names,
        checklist_texts=checklist_texts,
    )
    return dup


# Checklist item operations
def add_checklist_item(db: Session, task_id: str, text: str) -> ChecklistItem:
    clean_text = text.strip()
    if not clean_text:
        raise ValueError("Checklist item text cannot be empty.")
    max_order = db.execute(
        select(func.coalesce(func.max(ChecklistItem.sort_order), -1)).where(ChecklistItem.task_id == task_id)
    ).scalar_one()

    item = ChecklistItem(
        id=generate_uuid(),
        task_id=task_id,
        text=clean_text,
        is_completed=False,
        sort_order=max_order + 1,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db.add(item)
    db.flush()
    return item


def toggle_checklist_item(db: Session, item_id: str, is_completed: bool) -> ChecklistItem:
    item = db.execute(select(ChecklistItem).where(ChecklistItem.id == item_id)).scalar_one_or_none()
    if not item:
        raise ValueError("Checklist item not found.")
    item.is_completed = is_completed
    item.updated_at = utc_now()
    db.flush()
    return item


def delete_checklist_item(db: Session, item_id: str) -> bool:
    item = db.execute(select(ChecklistItem).where(ChecklistItem.id == item_id)).scalar_one_or_none()
    if not item:
        return False
    db.delete(item)
    db.flush()
    return True


# Querying and filtering tasks
def query_tasks(
    db: Session,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    project_id: Optional[str] = None,
    tag_id: Optional[str] = None,
    category: Optional[str] = None,
    is_archived: bool = False,
    in_trash: bool = False,
    planned_for_date: Optional[date] = None,
    due_before: Optional[datetime] = None,
    due_after: Optional[datetime] = None,
    search_query: Optional[str] = None,
    exclude_subtasks: bool = True,
    sort_by: str = "due_date",
    sort_asc: bool = True,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
) -> List[Task]:
    """
    Powerful parameterized query supporting all filtering, searching, and sorting criteria.
    """
    stmt = (
        select(Task)
        .options(
            selectinload(Task.project),
            selectinload(Task.tags),
            selectinload(Task.checklist_items),
            selectinload(Task.subtasks),
        )
    )

    conditions = []

    # Trash / Archive filters
    if in_trash:
        conditions.append(Task.deleted_at.is_not(None))
    else:
        conditions.append(Task.deleted_at.is_(None))
        conditions.append(Task.is_archived.is_(is_archived))

    if exclude_subtasks:
        conditions.append(Task.parent_task_id.is_(None))

    if status:
        conditions.append(Task.status == status)

    if priority:
        conditions.append(Task.priority == priority.lower())

    if project_id == "inbox":
        conditions.append(Task.project_id.is_(None))
    elif project_id:
        conditions.append(Task.project_id == project_id)

    if category:
        conditions.append(Task.category == category)

    if planned_for_date:
        conditions.append(Task.planned_for_date == planned_for_date)

    if due_before:
        conditions.append(Task.due_at <= due_before)

    if due_after:
        conditions.append(Task.due_at >= due_after)

    if tag_id:
        stmt = stmt.join(TaskTag, TaskTag.task_id == Task.id).where(TaskTag.tag_id == tag_id)

    if search_query:
        pattern = f"%{search_query.strip().lower()}%"
        stmt = stmt.outerjoin(Project, Project.id == Task.project_id)
        stmt = stmt.outerjoin(TaskTag, TaskTag.task_id == Task.id).outerjoin(Tag, Tag.id == TaskTag.tag_id)
        search_filter = or_(
            func.lower(Task.title).like(pattern),
            func.lower(func.coalesce(Task.description, "")).like(pattern),
            func.lower(func.coalesce(Project.name, "")).like(pattern),
            func.lower(func.coalesce(Tag.name, "")).like(pattern),
        )
        conditions.append(search_filter)

    if conditions:
        stmt = stmt.where(and_(*conditions))

    # Apply sorting
    if sort_by == "priority":
        stmt = stmt.order_by(PRIORITY_RANK.desc() if sort_asc else PRIORITY_RANK.asc(), Task.due_at.asc().nullslast())
    elif sort_by == "title":
        stmt = stmt.order_by(Task.title.asc() if sort_asc else Task.title.desc())
    elif sort_by == "created_at":
        stmt = stmt.order_by(Task.created_at.asc() if sort_asc else Task.created_at.desc())
    elif sort_by == "updated_at":
        stmt = stmt.order_by(Task.updated_at.asc() if sort_asc else Task.updated_at.desc())
    elif sort_by == "manual":
        stmt = stmt.order_by(Task.sort_order.asc())
    else:  # Default: due_date
        # Tasks with due date first, then nulls last
        if sort_asc:
            stmt = stmt.order_by(Task.due_at.asc().nullslast(), PRIORITY_RANK.desc(), Task.created_at.desc())
        else:
            stmt = stmt.order_by(Task.due_at.desc().nullslast(), PRIORITY_RANK.desc())

    if limit is not None:
        stmt = stmt.limit(limit)
    if offset is not None:
        stmt = stmt.offset(offset)

    return list(db.execute(stmt).scalars().unique().all())


# Bulk actions
def execute_bulk_action(
    db: Session,
    task_ids: List[str],
    action: str,
    action_value: Optional[Any] = None,
) -> int:
    """Executes bulk operations on a validated set of task IDs."""
    if not task_ids:
        return 0

    now = utc_now()
    tasks = db.execute(select(Task).where(Task.id.in_(task_ids))).scalars().all()
    count = 0

    for task in tasks:
        if action == "mark_done":
            task.status = "done"
            task.completed_at = now
        elif action == "mark_todo":
            task.status = "todo"
            task.completed_at = None
        elif action == "change_priority":
            if action_value in ("low", "medium", "high", "urgent"):
                task.priority = action_value
        elif action == "move_project":
            task.project_id = action_value  # Can be None for Inbox
        elif action == "archive":
            task.is_archived = True
        elif action == "delete":
            task.deleted_at = now
        elif action == "restore":
            task.deleted_at = None
            task.is_archived = False
        task.updated_at = now
        count += 1

    db.flush()
    return count

