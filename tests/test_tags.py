"""
Tests for tag management: create, normalize, rename, delete, assign/remove from tasks.
Covers Section 5.9 requirements of PRIVATE_TASK_MANAGER_BUILD_SPEC.md.
"""

from __future__ import annotations

import uuid
import pytest
from sqlalchemy import select

from taskvault.models.tag import Tag
from taskvault.repositories import tag_repository, task_repository


# ---------------------------------------------------------------------------
# Tag creation and normalization
# ---------------------------------------------------------------------------


def test_create_tag_basic(db_session):
    """Creating a tag returns a Tag object with the given name."""
    tags = tag_repository.get_or_create_tags(db_session, ["MyTag"])
    assert len(tags) == 1
    assert tags[0].name == "MyTag"
    assert tags[0].id is not None


def test_create_tag_normalized_lowercase(db_session):
    """Tags store a normalized_name in lowercase."""
    tags = tag_repository.get_or_create_tags(db_session, ["Alpha"])
    assert tags[0].normalized_name == "alpha"


def test_create_tag_duplicate_prevention(db_session):
    """Creating the same tag twice (case-insensitive) returns the existing one."""
    tags1 = tag_repository.get_or_create_tags(db_session, ["Duplicate"])
    tags2 = tag_repository.get_or_create_tags(db_session, ["DUPLICATE"])
    assert tags1[0].id == tags2[0].id


def test_create_multiple_tags_at_once(db_session):
    """Multiple tags can be created in one call; duplicates within the list are skipped."""
    tags = tag_repository.get_or_create_tags(db_session, ["Alpha", "Beta", "Alpha"])
    names = {t.normalized_name for t in tags}
    assert "alpha" in names
    assert "beta" in names
    # At most 2 unique tags should be returned
    assert len(tags) <= 2


def test_get_tags_with_counts_empty(db_session):
    """get_tags_with_counts returns an empty list when no tags exist."""
    result = tag_repository.get_tags_with_counts(db_session)
    assert isinstance(result, list)
    assert len(result) == 0


def test_get_tags_with_counts_includes_new_tag(db_session):
    """A newly created tag appears in get_tags_with_counts."""
    tag_repository.get_or_create_tags(db_session, ["countme"])
    result = tag_repository.get_tags_with_counts(db_session)
    names = [r["name"] for r in result]
    assert "countme" in names


def test_get_tags_with_counts_dict_keys(db_session):
    """Each entry in get_tags_with_counts has id, name, normalized_name, and count."""
    tag_repository.get_or_create_tags(db_session, ["keycheck"])
    result = tag_repository.get_tags_with_counts(db_session)
    entry = next(r for r in result if r["name"] == "keycheck")
    for key in ("id", "name", "normalized_name", "count"):
        assert key in entry


# ---------------------------------------------------------------------------
# Tag rename
# ---------------------------------------------------------------------------


def test_rename_tag(db_session):
    """Renaming a tag changes its name and updates normalized_name."""
    tags = tag_repository.get_or_create_tags(db_session, ["OldName"])
    tag_id = tags[0].id
    tag_repository.rename_tag(db_session, tag_id, "NewName")

    updated = db_session.execute(select(Tag).where(Tag.id == tag_id)).scalar_one()
    assert updated.name == "NewName"
    assert updated.normalized_name == "newname"


def test_rename_tag_conflict_raises(db_session):
    """Renaming to an existing tag name raises ValueError."""
    tags_first = tag_repository.get_or_create_tags(db_session, ["First"])
    tag_repository.get_or_create_tags(db_session, ["Second"])
    first_id = tags_first[0].id

    with pytest.raises(ValueError):
        tag_repository.rename_tag(db_session, first_id, "Second")


def test_rename_nonexistent_tag_raises(db_session):
    """Renaming a tag that doesn't exist raises ValueError."""
    with pytest.raises(ValueError):
        tag_repository.rename_tag(db_session, str(uuid.uuid4()), "Whatever")


# ---------------------------------------------------------------------------
# Tag deletion
# ---------------------------------------------------------------------------


def test_delete_tag(db_session):
    """Deleting a tag removes it from the database."""
    tags = tag_repository.get_or_create_tags(db_session, ["DeleteMe"])
    tag_id = tags[0].id
    tag_repository.delete_tag(db_session, tag_id)

    result = db_session.execute(select(Tag).where(Tag.id == tag_id)).scalar_one_or_none()
    assert result is None


def test_delete_nonexistent_tag_safe(db_session):
    """Deleting a tag that does not exist returns False and does not raise."""
    result = tag_repository.delete_tag(db_session, str(uuid.uuid4()))
    assert result is False


# ---------------------------------------------------------------------------
# Assign / remove tags from tasks
# ---------------------------------------------------------------------------


def test_assign_tag_to_task_at_creation(db_session):
    """Tags can be assigned to a task when creating it."""
    task = task_repository.create_task(
        db_session,
        title="Tagged task",
        priority="medium",
        tag_names=["feature"],
    )
    assert any(t.normalized_name == "feature" for t in task.tags)


def test_task_with_multiple_tags(db_session):
    """A task can carry multiple tags."""
    task = task_repository.create_task(
        db_session,
        title="Multi-tagged task",
        priority="low",
        tag_names=["alpha", "beta", "gamma"],
    )
    normalized = {t.normalized_name for t in task.tags}
    assert {"alpha", "beta", "gamma"}.issubset(normalized)


def test_remove_all_tags_from_task(db_session):
    """Updating a task with an empty tag list removes all tags."""
    task = task_repository.create_task(
        db_session,
        title="Had tags",
        priority="medium",
        tag_names=["removeme"],
    )
    task_repository.update_task(db_session, task.id, tag_names=[])
    updated = task_repository.get_task_by_id(db_session, task.id)
    assert updated.tags == []


def test_tag_count_increments_with_assigned_tasks(db_session):
    """get_tags_with_counts reflects the number of tasks assigned to a tag."""
    tag_repository.get_or_create_tags(db_session, ["counttest"])
    task_repository.create_task(
        db_session, title="Task A", priority="medium", tag_names=["counttest"],
    )
    task_repository.create_task(
        db_session, title="Task B", priority="medium", tag_names=["counttest"],
    )

    counts = tag_repository.get_tags_with_counts(db_session)
    ct_entry = next((r for r in counts if r["name"] == "counttest"), None)
    assert ct_entry is not None
    assert ct_entry["count"] >= 2
