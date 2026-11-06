"""
Tests for Project CRUD, statistics, and task reassignment safety.
"""

import pytest
from taskvault.services import project_service, task_service


def test_create_and_update_project(authenticated_session):
    p = project_service.create_project(
        name="Quarterly Planning",
        description="Goals and roadmap",
        color="#10B981",
        icon="briefcase",
        db_session=authenticated_session,
    )
    assert p.id is not None
    assert p.name == "Quarterly Planning"
    assert p.status == "active"

    # Update
    updated = project_service.update_project_details(
        project_id=p.id,
        name="Q4 Strategic Planning",
        db_session=authenticated_session,
    )
    assert updated.name == "Q4 Strategic Planning"


def test_delete_project_moves_tasks_to_inbox(authenticated_session):
    proj = project_service.create_project(name="Temporary Project", db_session=authenticated_session)
    task = task_service.create_quick_task(
        title="Project dependent task",
        project_id=proj.id,
        db_session=authenticated_session,
    )
    assert task.project_id == proj.id

    # Delete project with move_tasks_to_inbox=True
    deleted = project_service.delete_project_item(proj.id, move_tasks_to_inbox=True, db_session=authenticated_session)
    assert deleted is True

    # Check that task is NOT deleted and its project_id is cleared (moved to Inbox)
    t = task_service.get_task(task.id, db_session=authenticated_session)
    assert t is not None
    assert t.project_id is None


def test_project_completion_stats(authenticated_session):
    proj = project_service.create_project(name="Stats Test Project", db_session=authenticated_session)
    t1 = task_service.create_quick_task("Task 1", project_id=proj.id, db_session=authenticated_session)
    t2 = task_service.create_quick_task("Task 2", project_id=proj.id, db_session=authenticated_session)

    # 0 of 2 complete
    stats = project_service.get_project_summary(proj.id, db_session=authenticated_session)
    assert stats["total_tasks"] == 2
    assert stats["completed_tasks"] == 0
    assert stats["completion_percentage"] == 0.0

    # Mark 1 done
    task_service.toggle_task_done(t1.id, is_completed=True, db_session=authenticated_session)
    stats = project_service.get_project_summary(proj.id, db_session=authenticated_session)
    assert stats["completed_tasks"] == 1
    assert stats["completion_percentage"] == 50.0

