"""
FocusSession and ActivityLog SQLAlchemy models.
"""

from __future__ import annotations

from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    DateTime,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import relationship

from taskvault.database import Base
from taskvault.models.base import utc_now, generate_uuid


class FocusSession(Base):
    """
    Records completed Pomodoro / focus sessions and time tracking linked to tasks.
    """
    __tablename__ = "focus_sessions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    task_id = Column(String(36), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Integer, nullable=False, default=0)
    session_type = Column(String(32), nullable=False, default="focus")  # focus, short_break, long_break
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    task = relationship("Task", back_populates="focus_sessions")

    __table_args__ = (
        Index("idx_focus_task_id", "task_id"),
        Index("idx_focus_started_at", "started_at"),
        {"extend_existing": True},
    )


class ActivityLog(Base):
    """
    Audit log of key state transitions (task created, completed, archived, password changed).
    Excludes sensitive passwords or raw private descriptions.
    """
    __tablename__ = "activity_log"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    action = Column(String(64), nullable=False)
    entity_type = Column(String(32), nullable=False)  # task, project, auth, system
    entity_id = Column(String(36), nullable=True)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    __table_args__ = (
        Index("idx_activity_created_at", "created_at"),
        Index("idx_activity_action", "action"),
        {"extend_existing": True},
    )

