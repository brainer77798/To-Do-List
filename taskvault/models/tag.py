"""
Tag and TaskTag link SQLAlchemy models.
"""

from __future__ import annotations

from sqlalchemy import (
    Column,
    String,
    DateTime,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import relationship

from taskvault.database import Base
from taskvault.models.base import utc_now, generate_uuid


class Tag(Base):
    """
    Tag entity for labeling and categorizing tasks.
    Normalized name enforces uniqueness regardless of case/whitespace.
    """
    __tablename__ = "tags"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(64), nullable=False)
    normalized_name = Column(String(64), nullable=False, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    # Relationships
    tasks = relationship("Task", secondary="task_tags", back_populates="tags")


class TaskTag(Base):
    """
    Many-to-many junction table linking tasks and tags.
    """
    __tablename__ = "task_tags"

    task_id = Column(String(36), ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True)
    tag_id = Column(String(36), ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)

    __table_args__ = (
        Index("idx_task_tags_task", "task_id"),
        Index("idx_task_tags_tag", "tag_id"),
    )

