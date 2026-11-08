"""
Project SQLAlchemy models.
"""

from __future__ import annotations

from sqlalchemy import (
    Column,
    String,
    Text,
    DateTime,
    Index,
)
from sqlalchemy.orm import relationship

from taskvault.database import Base
from taskvault.models.base import utc_now, generate_uuid


class Project(Base):
    """
    Project entity for grouping related tasks.
    """
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    color = Column(String(32), nullable=True, default="#3B82F6")
    icon = Column(String(32), nullable=True, default="folder")
    status = Column(String(32), nullable=False, default="active")  # active, completed, archived
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)
    archived_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    tasks = relationship("Task", back_populates="project")

    __table_args__ = (
        Index("idx_projects_status", "status"),
        Index("idx_projects_name", "name"),
        {"extend_existing": True},
    )

