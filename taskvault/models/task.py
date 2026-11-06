"""
Task, ChecklistItem, and RecurrenceSeries SQLAlchemy models.
"""

from __future__ import annotations

from sqlalchemy import (
    Column,
    String,
    Text,
    Boolean,
    Integer,
    Date,
    DateTime,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import relationship

from taskvault.database import Base
from taskvault.models.base import utc_now, generate_uuid


class Task(Base):
    """
    Core Task entity supporting subtasks, checklists, recurrence, projects, and tags.
    """
    __tablename__ = "tasks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(32), nullable=False, default="todo")  # todo, in_progress, done
    priority = Column(String(16), nullable=False, default="medium")  # low, medium, high, urgent

    project_id = Column(String(36), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    parent_task_id = Column(String(36), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True)
    category = Column(String(64), nullable=True)

    due_at = Column(DateTime(timezone=True), nullable=True)
    due_date_only = Column(Boolean, nullable=False, default=False)
    start_at = Column(DateTime(timezone=True), nullable=True)
    planned_for_date = Column(Date, nullable=True)  # For My Day planning

    estimated_minutes = Column(Integer, nullable=True)
    actual_minutes = Column(Integer, nullable=False, default=0)

    is_archived = Column(Boolean, nullable=False, default=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)  # Null if not in trash
    completed_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)
    sort_order = Column(Integer, nullable=False, default=0)

    recurrence_series_id = Column(String(36), ForeignKey("recurrence_series.id", ondelete="SET NULL"), nullable=True)
    occurrence_key = Column(String(64), nullable=True)

    # Relationships
    project = relationship("Project", back_populates="tasks")
    tags = relationship("Tag", secondary="task_tags", back_populates="tasks")
    checklist_items = relationship("ChecklistItem", back_populates="task", cascade="all, delete-orphan", order_by="ChecklistItem.sort_order")
    parent_task = relationship("Task", remote_side=[id], back_populates="subtasks")
    subtasks = relationship("Task", back_populates="parent_task", cascade="all, delete-orphan")
    recurrence_series = relationship("RecurrenceSeries", back_populates="tasks")
    focus_sessions = relationship("FocusSession", back_populates="task", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_tasks_status", "status"),
        Index("idx_tasks_priority", "priority"),
        Index("idx_tasks_due_at", "due_at"),
        Index("idx_tasks_project_id", "project_id"),
        Index("idx_tasks_parent_id", "parent_task_id"),
        Index("idx_tasks_deleted_at", "deleted_at"),
        Index("idx_tasks_is_archived", "is_archived"),
        Index("idx_tasks_planned_date", "planned_for_date"),
        Index("idx_tasks_recurrence_occ", "recurrence_series_id", "occurrence_key"),
    )


class ChecklistItem(Base):
    """
    Lightweight checklist items embedded within a task.
    """
    __tablename__ = "checklist_items"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    task_id = Column(String(36), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    text = Column(String(255), nullable=False)
    is_completed = Column(Boolean, nullable=False, default=False)
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    task = relationship("Task", back_populates="checklist_items")

    __table_args__ = (
        Index("idx_checklist_task_id", "task_id"),
    )


class RecurrenceSeries(Base):
    """
    Defines recurrence rule and template for generating repeating task occurrences.
    """
    __tablename__ = "recurrence_series"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    priority = Column(String(16), nullable=False, default="medium")
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    category = Column(String(64), nullable=True)
    estimated_minutes = Column(Integer, nullable=True)

    frequency = Column(String(32), nullable=False)  # daily, weekdays, weekly, monthly, yearly, custom
    interval = Column(Integer, nullable=False, default=1)
    weekdays = Column(Text, nullable=True)  # JSON list of ints e.g. "[0, 2, 4]" (0=Mon)
    day_of_month = Column(Integer, nullable=True)

    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    next_occurrence_at = Column(DateTime(timezone=True), nullable=True)
    timezone = Column(String(64), nullable=False, default="America/New_York")
    is_paused = Column(Boolean, nullable=False, default=False)
    missed_occurrence_policy = Column(String(32), nullable=False, default="skip")  # skip, create_next

    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    tasks = relationship("Task", back_populates="recurrence_series")

    __table_args__ = (
        Index("idx_recurrence_next_at", "next_occurrence_at"),
        Index("idx_recurrence_paused", "is_paused"),
    )
