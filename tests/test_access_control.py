"""
Tests verifying access control and that locked sessions cannot execute private services.
"""

import pytest
from taskvault.services import task_service, project_service, backup_service
from taskvault.security.access_control import SessionManager, UnauthorizedAccessError


def test_locked_session_cannot_access_task_services(db_session):
    # Ensure session is locked
    SessionManager.lock()
    assert SessionManager.is_unlocked() is False

    # Calling task creation while locked must raise UnauthorizedAccessError
    with pytest.raises(UnauthorizedAccessError):
        task_service.create_quick_task("Unauthorized task", db_session=db_session)

    # Calling query while locked must raise UnauthorizedAccessError
    with pytest.raises(UnauthorizedAccessError):
        task_service.query_tasks_filtered(db_session=db_session)

    # Calling project services while locked must raise UnauthorizedAccessError
    with pytest.raises(UnauthorizedAccessError):
        project_service.list_projects(db_session=db_session)

    # Calling backup export while locked must raise UnauthorizedAccessError
    with pytest.raises(UnauthorizedAccessError):
        backup_service.export_tasks_csv(db_session=db_session)


def test_inactivity_timeout_locks_session():
    SessionManager.unlock()
    assert SessionManager.is_unlocked(timeout_minutes=10) is True

    # Simulate inactivity by setting last_activity to 15 minutes ago
    state = SessionManager.get_session_state()
    state[SessionManager.KEY_LAST_ACTIVITY] = 0  # epoch 0

    # Checking is_unlocked should now detect timeout and lock
    assert SessionManager.is_unlocked(timeout_minutes=10) is False
    assert state.get(SessionManager.KEY_IS_UNLOCKED) is False

