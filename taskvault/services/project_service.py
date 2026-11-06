"""
Project service layer for TaskVault.
Enforces authentication and business validation.
"""

from __future__ import annotations

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from taskvault.database import get_db_session
from taskvault.models.project import Project
from taskvault.security.access_control import require_auth
from taskvault.repositories import project_repository, security_repository


@require_auth
def list_projects(status: Optional[str] = None, db_session: Optional[Session] = None) -> List[Project]:
    if db_session:
        return project_repository.get_projects(db_session, status=status)
    with get_db_session() as db:
        return project_repository.get_projects(db, status=status)


@require_auth
def get_project(project_id: str, db_session: Optional[Session] = None) -> Optional[Project]:
    if db_session:
        return project_repository.get_project_by_id(db_session, project_id)
    with get_db_session() as db:
        return project_repository.get_project_by_id(db, project_id)


@require_auth
def create_project(
    name: str,
    description: Optional[str] = None,
    color: Optional[str] = "#3B82F6",
    icon: Optional[str] = "folder",
    db_session: Optional[Session] = None,
) -> Project:
    def _do(db: Session) -> Project:
        proj = project_repository.create_project(
            db=db,
            name=name,
            description=description,
            color=color,
            icon=icon,
        )
        security_repository.log_activity(db, action="project_created", entity_type="project", entity_id=proj.id)
        return proj

    if db_session:
        return _do(db_session)
    with get_db_session() as db:
        return _do(db)


@require_auth
def update_project_details(
    project_id: str,
    db_session: Optional[Session] = None,
    **kwargs: Any,
) -> Project:
    def _do(db: Session) -> Project:
        proj = project_repository.update_project(db, project_id, **kwargs)
        security_repository.log_activity(db, action="project_updated", entity_type="project", entity_id=proj.id)
        return proj

    if db_session:
        return _do(db_session)
    with get_db_session() as db:
        return _do(db)


@require_auth
def archive_project(project_id: str, db_session: Optional[Session] = None) -> Project:
    return update_project_details(project_id, status="archived", db_session=db_session)


@require_auth
def delete_project_item(
    project_id: str,
    move_tasks_to_inbox: bool = True,
    db_session: Optional[Session] = None,
) -> bool:
    def _do(db: Session) -> bool:
        res = project_repository.delete_project(db, project_id, move_tasks_to_inbox=move_tasks_to_inbox)
        security_repository.log_activity(
            db, action="project_deleted", entity_type="project", entity_id=project_id
        )
        return res

    if db_session:
        return _do(db_session)
    with get_db_session() as db:
        return _do(db)


@require_auth
def get_project_summary(project_id: str, db_session: Optional[Session] = None) -> Dict[str, Any]:
    if db_session:
        return project_repository.get_project_stats(db_session, project_id)
    with get_db_session() as db:
        return project_repository.get_project_stats(db, project_id)

