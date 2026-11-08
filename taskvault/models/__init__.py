"""
SQLAlchemy models package for TaskVault.
Exports all models to ensure registration with Base.metadata.
"""

from taskvault.database import Base
from taskvault.models.base import utc_now, generate_uuid
from taskvault.models.security import User, AppSetting, LoginAttempt
from taskvault.models.project import Project
from taskvault.models.tag import Tag, TaskTag
from taskvault.models.task import Task, ChecklistItem, RecurrenceSeries
from taskvault.models.focus import FocusSession, ActivityLog

__all__ = [
    "Base",
    "utc_now",
    "generate_uuid",
    "User",
    "AppSetting",
    "LoginAttempt",
    "Project",
    "Tag",
    "TaskTag",
    "Task",
    "ChecklistItem",
    "RecurrenceSeries",
    "FocusSession",
    "ActivityLog",
]

