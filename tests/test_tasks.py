"""
Tests for Task CRUD, checklists, subtasks, search, filtering, and bulk operations.
"""

import pytest
from datetime import datetime, timezone, timedelta
from taskvault.services import task_service, project_service
from taskvault.security.access_control import SessionManager


def test_create_task_minimal(authenticated_session):
    task = task_service.create_quick_task(
        title="Quick groceries task",
        db_session=authenticated_session,
    )
    assert task.id is not None
    assert task.title == "Quick groceries task"
    assert task.status == "todo"
    assert task.priority == "medium"
    assert task.project_id is None
    assert task.deleted_at is None
    assert task.is_archived is False


def test_reject_empty_task_title(authenticated_session):
    with pytest.raises(ValueError):
        task_service.create_quick_task("   ", db_session=authenticated_session)


def test_create_task_full(authenticated_session):
    due = datetime.now(timezone.utc) + timedelta(days=2)
    task = task_service.create_full_task(
        title="Comprehensive feature implementation",
        description="Write thorough unit tests and documentation",
        status="in_progress",
        priority="urgent",
        category="Engineering",
        due_at=due,
        due_date_only=False,
        estimated_minutes=90,
        tag_names=["backend", "security"],
        checklist_texts=["Review spec", "Implement endpoints", "Run pytest"],
        db_session=authenticated_session,
    )
    assert task.title == "Comprehensive feature implementation"
    assert task.status == "in_progress"
    assert task.priority == "urgent"
    assert task.estimated_minutes == 90
    assert len(task.tags) == 2
    assert len(task.checklist_items) == 3


def test_task_completion_lifecycle(authenticated_session):
    task = task_service.create_quick_task("Complete deployment documentation", db_session=authenticated_session)
    assert task.status == "todo"
    assert task.completed_at is None

    # Mark done
    done_task = task_service.toggle_task_done(task.id, is_completed=True, db_session=authenticated_session)
    assert done_task.status == "done"
    assert done_task.completed_at is not None

    # Reopen
    reopened = task_service.toggle_task_done(task.id, is_completed=False, db_session=authenticated_session)
    assert reopened.status == "todo"
    assert reopened.completed_at is None


def test_soft_delete_and_restore(authenticated_session):
    task = task_service.create_quick_task("Task to delete", db_session=authenticated_session)
    task_id = task.id

    # Soft delete
    task_service.soft_delete_task(task_id, db_session=authenticated_session)
    t = task_service.get_task(task_id, db_session=authenticated_session)
    assert t.deleted_at is not None

    # Restore
    task_service.restore_task_item(task_id, db_session=authenticated_session)
    t = task_service.get_task(task_id, db_session=authenticated_session)
    assert t.deleted_at is None


def test_archive_and_restore(authenticated_session):
    task = task_service.create_quick_task("Task to archive", db_session=authenticated_session)
    task_id = task.id

    task_service.archive_task_item(task_id, db_session=authenticated_session)
    t = task_service.get_task(task_id, db_session=authenticated_session)
    assert t.is_archived is True

    task_service.restore_task_item(task_id, db_session=authenticated_session)
    t = task_service.get_task(task_id, db_session=authenticated_session)
    assert t.is_archived is False


def test_permanent_delete(authenticated_session):
    task = task_service.create_quick_task("Task to permanently delete", db_session=authenticated_session)
    task_id = task.id

    task_service.permanently_delete_task_item(task_id, db_session=authenticated_session)
    t = task_service.get_task(task_id, db_session=authenticated_session)
    assert t is None


def test_subtasks_and_no_circular_reference(authenticated_session):
    parent = task_service.create_quick_task("Parent Task", db_session=authenticated_session)
    sub = task_service.create_full_task("Subtask 1", parent_task_id=parent.id, db_session=authenticated_session)

    assert sub.parent_task_id == parent.id

    # A task cannot be its own parent
    with pytest.raises(ValueError):
        task_service.update_task_details(parent.id, parent_task_id=parent.id, db_session=authenticated_session)

    # 1 level nesting limit
    with pytest.raises(ValueError):
        task_service.create_full_task("Sub-subtask", parent_task_id=sub.id, db_session=authenticated_session)


def test_duplicate_task(authenticated_session):
    orig = task_service.create_full_task(
        title="Template task",
        checklist_texts=["Item 1", "Item 2"],
        tag_names=["routine"],
        db_session=authenticated_session,
    )
    dup = task_service.duplicate_task_item(orig.id, db_session=authenticated_session)

    assert dup.id != orig.id
    assert dup.title == "Template task (Copy)"
    assert len(dup.checklist_items) == 2
    assert len(dup.tags) == 1


def test_bulk_operations(authenticated_session):
    t1 = task_service.create_quick_task("Task 1", db_session=authenticated_session)
    t2 = task_service.create_quick_task("Task 2", db_session=authenticated_session)

    count = task_service.execute_bulk_operations(
        task_ids=[t1.id, t2.id],
        action="change_priority",
        action_value="urgent",
        db_session=authenticated_session,
    )
    assert count == 2

    r1 = task_service.get_task(t1.id, db_session=authenticated_session)
    r2 = task_service.get_task(t2.id, db_session=authenticated_session)
    assert r1.priority == "urgent"
    assert r2.priority == "urgent"


def test_search_and_filter(authenticated_session):
    task_service.create_full_task(title="Deploy backend server", description="AWS ECS cluster", db_session=authenticated_session)
    task_service.create_full_task(title="Buy fresh produce", description="Apples and oranges", db_session=authenticated_session)

    # Search by keyword
    results = task_service.query_tasks_filtered(search_query="backend", db_session=authenticated_session)
    assert len(results) == 1
    assert results[0].title == "Deploy backend server"

    # Search in description
    results_desc = task_service.query_tasks_filtered(search_query="apples", db_session=authenticated_session)
    assert len(results_desc) == 1
    assert results_desc[0].title == "Buy fresh produce"

