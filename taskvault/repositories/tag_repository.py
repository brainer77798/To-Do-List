"""
Repository for Tag operations.
"""

from __future__ import annotations

import re
from typing import List, Optional
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from taskvault.models.tag import Tag, TaskTag
from taskvault.models.task import Task
from taskvault.models.base import utc_now


def normalize_tag_name(name: str) -> str:
    """Normalizes a tag name (lowercased, spaces converted to dashes, non-alphanumeric removed)."""
    cleaned = re.sub(r"[^\w\s-]", "", name.strip().lower())
    return re.sub(r"[-\s]+", "-", cleaned)


def get_all_tags(db: Session) -> List[Tag]:
    """Retrieves all tags sorted alphabetically by name."""
    return list(db.execute(select(Tag).order_by(Tag.name.asc())).scalars().all())


def get_tag_by_id(db: Session, tag_id: str) -> Optional[Tag]:
    """Retrieves a tag by its ID."""
    return db.execute(select(Tag).where(Tag.id == tag_id)).scalar_one_or_none()


def get_tag_by_name(db: Session, name: str) -> Optional[Tag]:
    """Retrieves a tag by its raw or normalized name."""
    norm = normalize_tag_name(name)
    return db.execute(select(Tag).where(Tag.normalized_name == norm)).scalar_one_or_none()


def get_or_create_tags(db: Session, tag_names: List[str]) -> List[Tag]:
    """
    Given a list of tag names, retrieves existing or creates new tags safely.
    Prevents duplicate normalized tags.
    """
    result: List[Tag] = []
    seen_norms = set()

    for name in tag_names:
        clean_name = name.strip()
        if not clean_name:
            continue
        norm = normalize_tag_name(clean_name)
        if not norm or norm in seen_norms:
            continue
        seen_norms.add(norm)

        tag = db.execute(select(Tag).where(Tag.normalized_name == norm)).scalar_one_or_none()
        if not tag:
            tag = Tag(name=clean_name, normalized_name=norm, created_at=utc_now())
            db.add(tag)
            db.flush()
        result.append(tag)

    return result


def rename_tag(db: Session, tag_id: str, new_name: str) -> Tag:
    """Renames an existing tag."""
    tag = get_tag_by_id(db, tag_id)
    if not tag:
        raise ValueError("Tag not found.")
    norm = normalize_tag_name(new_name)
    if not norm:
        raise ValueError("Invalid tag name.")

    # Check if another tag already has this normalized name
    existing = db.execute(select(Tag).where(Tag.normalized_name == norm, Tag.id != tag_id)).scalar_one_or_none()
    if existing:
        raise ValueError(f"Tag with name '{new_name}' already exists.")

    tag.name = new_name.strip()
    tag.normalized_name = norm
    db.flush()
    return tag


def delete_tag(db: Session, tag_id: str) -> bool:
    """Deletes a tag and removes links from tasks."""
    tag = get_tag_by_id(db, tag_id)
    if not tag:
        return False
    # Remove task_tags associations
    db.query(TaskTag).filter(TaskTag.tag_id == tag_id).delete()
    db.delete(tag)
    db.flush()
    return True


def get_tags_with_counts(db: Session) -> List[dict]:
    """Returns all tags along with the count of active (non-deleted, non-archived) tasks."""
    tags = get_all_tags(db)
    result = []
    for tag in tags:
        count = db.execute(
            select(func.count(Task.id))
            .join(TaskTag, TaskTag.task_id == Task.id)
            .where(
                TaskTag.tag_id == tag.id,
                Task.deleted_at.is_(None),
                Task.is_archived.is_(False),
            )
        ).scalar_one()
        result.append({
            "id": tag.id,
            "name": tag.name,
            "normalized_name": tag.normalized_name,
            "count": count,
        })
    return result

