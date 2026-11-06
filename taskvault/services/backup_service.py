"""
Backup, export, and restore services for TaskVault.
Includes CSV formula injection sanitization and secure JSON backup/restore.
"""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from taskvault.database import get_db_session
from taskvault.models.task import Task, ChecklistItem, RecurrenceSeries
from taskvault.models.project import Project
from taskvault.models.tag import Tag, TaskTag
from taskvault.models.security import AppSetting
from taskvault.models.base import utc_now, generate_uuid
from taskvault.security.access_control import require_auth
from taskvault.utils.formatting import sanitize_csv_field
from taskvault.utils.validation import validate_backup_payload, ValidationError
from taskvault.repositories import security_repository, tag_repository


@require_auth
def export_tasks_csv(include_all: bool = False, db_session: Optional[Session] = None) -> str:
    """
    Exports tasks to a UTF-8 CSV string.
    Neutralizes formula injection attacks on user-controlled text.
    """
    def _do_export(db: Session) -> str:
        stmt = select(Task).order_by(Task.created_at.desc())
        if not include_all:
            stmt = stmt.where(Task.deleted_at.is_(None), Task.is_archived.is_(False))

        tasks = db.execute(stmt).scalars().all()
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

        headers = [
            "ID",
            "Title",
            "Description",
            "Status",
            "Priority",
            "Due Date/Time",
            "Project",
            "Tags",
            "Category",
            "Estimated Minutes",
            "Actual Minutes",
            "Is Archived",
            "Is Deleted",
            "Created At",
            "Updated At",
            "Completed At",
        ]
        writer.writerow(headers)

        for t in tasks:
            proj_name = t.project.name if t.project else ""
            tag_names = ", ".join(tag.name for tag in t.tags)
            due_str = t.due_at.isoformat() if t.due_at else ""
            created_str = t.created_at.isoformat() if t.created_at else ""
            updated_str = t.updated_at.isoformat() if t.updated_at else ""
            completed_str = t.completed_at.isoformat() if t.completed_at else ""

            row = [
                t.id,
                sanitize_csv_field(t.title),
                sanitize_csv_field(t.description),
                t.status,
                t.priority,
                due_str,
                sanitize_csv_field(proj_name),
                sanitize_csv_field(tag_names),
                sanitize_csv_field(t.category),
                t.estimated_minutes or "",
                t.actual_minutes or 0,
                t.is_archived,
                bool(t.deleted_at),
                created_str,
                updated_str,
                completed_str,
            ]
            writer.writerow(row)

        return output.getvalue()

    if db_session:
        return _do_export(db_session)
    with get_db_session() as db:
        return _do_export(db)


@require_auth
def export_json_backup(db_session: Optional[Session] = None) -> Dict[str, Any]:
    """
    Generates a complete versioned JSON backup of all workspace tasks, projects,
    tags, checklists, and safe preferences.
    Explicitly excludes sensitive password hashes and database credentials.
    """
    def _do_export(db: Session) -> Dict[str, Any]:
        settings = security_repository.get_settings(db)
        projects = db.execute(select(Project)).scalars().all()
        tasks = db.execute(select(Task)).scalars().all()
        tags = db.execute(select(Tag)).scalars().all()

        safe_settings = {
            "timezone": settings.timezone if settings else "America/New_York",
            "theme": settings.theme if settings else "dark",
            "lock_timeout_minutes": settings.lock_timeout_minutes if settings else 10,
            "week_starts_on": settings.week_starts_on if settings else "Monday",
            "default_priority": settings.default_priority if settings else "medium",
            "due_soon_days": settings.due_soon_days if settings else 7,
            "daily_capacity_minutes": settings.daily_capacity_minutes if settings else 480,
        }

        projects_data = [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "color": p.color,
                "icon": p.icon,
                "status": p.status,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "updated_at": p.updated_at.isoformat() if p.updated_at else None,
                "archived_at": p.archived_at.isoformat() if p.archived_at else None,
            }
            for p in projects
        ]

        tags_data = [
            {
                "id": tg.id,
                "name": tg.name,
                "normalized_name": tg.normalized_name,
            }
            for tg in tags
        ]

        tasks_data = []
        for t in tasks:
            checklist = [
                {
                    "id": item.id,
                    "text": item.text,
                    "is_completed": item.is_completed,
                    "sort_order": item.sort_order,
                }
                for item in t.checklist_items
            ]
            tag_names = [tg.name for tg in t.tags]

            tasks_data.append({
                "id": t.id,
                "title": t.title,
                "description": t.description,
                "status": t.status,
                "priority": t.priority,
                "project_id": t.project_id,
                "parent_task_id": t.parent_task_id,
                "category": t.category,
                "due_at": t.due_at.isoformat() if t.due_at else None,
                "due_date_only": t.due_date_only,
                "start_at": t.start_at.isoformat() if t.start_at else None,
                "planned_for_date": t.planned_for_date.isoformat() if t.planned_for_date else None,
                "estimated_minutes": t.estimated_minutes,
                "actual_minutes": t.actual_minutes,
                "is_archived": t.is_archived,
                "deleted_at": t.deleted_at.isoformat() if t.deleted_at else None,
                "completed_at": t.completed_at.isoformat() if t.completed_at else None,
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "updated_at": t.updated_at.isoformat() if t.updated_at else None,
                "tags": tag_names,
                "checklist_items": checklist,
            })

        return {
            "version": "1.0",
            "app": "TaskVault",
            "exported_at": utc_now().isoformat(),
            "settings": safe_settings,
            "projects": projects_data,
            "tags": tags_data,
            "tasks": tasks_data,
        }

    if db_session:
        return _do_export(db_session)
    with get_db_session() as db:
        return _do_export(db)


@require_auth
def import_json_backup(
    data: Dict[str, Any],
    mode: str = "merge",
    db_session: Optional[Session] = None,
) -> Dict[str, int]:
    """
    Imports tasks and projects from validated JSON backup.
    Supports mode='merge' (preserves existing data) and mode='replace' (clears existing tasks/projects first).
    Never overwrites master security credentials (password/recovery hash).
    """
    validate_backup_payload(data)

    def _do_import(db: Session) -> Dict[str, int]:
        if mode == "replace":
            # Clear existing tasks and projects transactionally
            db.query(ChecklistItem).delete()
            db.query(TaskTag).delete()
            db.query(Task).delete()
            db.query(Project).delete()
            db.flush()

        # Import projects
        proj_id_map: Dict[str, str] = {}
        projects_count = 0
        for p_data in data.get("projects", []):
            existing_p = db.execute(select(Project).where(Project.name == p_data["name"])).scalar_one_or_none()
            if not existing_p:
                new_p = Project(
                    id=generate_uuid(),
                    name=p_data["name"],
                    description=p_data.get("description"),
                    color=p_data.get("color", "#3B82F6"),
                    icon=p_data.get("icon", "folder"),
                    status=p_data.get("status", "active"),
                    created_at=utc_now(),
                    updated_at=utc_now(),
                )
                db.add(new_p)
                db.flush()
                proj_id_map[p_data["id"]] = new_p.id
                projects_count += 1
            else:
                proj_id_map[p_data["id"]] = existing_p.id

        # Import tags
        tags_count = 0
        tag_cache: Dict[str, Tag] = {}
        for tg_data in data.get("tags", []):
            clean_name = tg_data["name"]
            tags = tag_repository.get_or_create_tags(db, [clean_name])
            if tags:
                tag_cache[clean_name] = tags[0]
                tags_count += 1

        # Import tasks
        tasks_count = 0
        task_id_map: Dict[str, str] = {}

        # First pass: Create all tasks without parent links to avoid FK violations
        raw_tasks = data.get("tasks", [])
        for t_data in raw_tasks:
            orig_proj_id = t_data.get("project_id")
            mapped_proj_id = proj_id_map.get(orig_proj_id) if orig_proj_id else None

            due_at = datetime.fromisoformat(t_data["due_at"]) if t_data.get("due_at") else None
            start_at = datetime.fromisoformat(t_data["start_at"]) if t_data.get("start_at") else None
            completed_at = datetime.fromisoformat(t_data["completed_at"]) if t_data.get("completed_at") else None
            deleted_at = datetime.fromisoformat(t_data["deleted_at"]) if t_data.get("deleted_at") else None
            planned_date = (
                datetime.fromisoformat(t_data["planned_for_date"]).date()
                if t_data.get("planned_for_date")
                else None
            )

            new_task_id = generate_uuid()
            task_id_map[t_data["id"]] = new_task_id

            task = Task(
                id=new_task_id,
                title=t_data["title"],
                description=t_data.get("description"),
                status=t_data.get("status", "todo"),
                priority=t_data.get("priority", "medium"),
                project_id=mapped_proj_id,
                parent_task_id=None,  # Linked in second pass
                category=t_data.get("category"),
                due_at=due_at,
                due_date_only=t_data.get("due_date_only", False),
                start_at=start_at,
                planned_for_date=planned_date,
                estimated_minutes=t_data.get("estimated_minutes"),
                actual_minutes=t_data.get("actual_minutes", 0),
                is_archived=t_data.get("is_archived", False),
                deleted_at=deleted_at,
                completed_at=completed_at,
                created_at=utc_now(),
                updated_at=utc_now(),
            )
            db.add(task)
            db.flush()

            # Attach tags
            if t_data.get("tags"):
                task_tags = tag_repository.get_or_create_tags(db, t_data["tags"])
                task.tags = task_tags

            # Attach checklist items
            for item in t_data.get("checklist_items", []):
                chk = ChecklistItem(
                    id=generate_uuid(),
                    task_id=task.id,
                    text=item["text"],
                    is_completed=item.get("is_completed", False),
                    sort_order=item.get("sort_order", 0),
                    created_at=utc_now(),
                    updated_at=utc_now(),
                )
                db.add(chk)

            tasks_count += 1

        # Second pass: link subtasks to mapped parent IDs
        for t_data in raw_tasks:
            orig_parent_id = t_data.get("parent_task_id")
            if orig_parent_id and orig_parent_id in task_id_map:
                new_sub_id = task_id_map[t_data["id"]]
                mapped_parent_id = task_id_map[orig_parent_id]
                db.query(Task).filter(Task.id == new_sub_id).update({Task.parent_task_id: mapped_parent_id})

        security_repository.log_activity(
            db,
            action="backup_imported",
            entity_type="system",
            details=f"Imported {tasks_count} tasks, {projects_count} projects in mode={mode}",
        )
        return {
            "projects_imported": projects_count,
            "tasks_imported": tasks_count,
            "tags_imported": tags_count,
        }

    if db_session:
        return _do_import(db_session)
    with get_db_session() as db:
        return _do_import(db)

