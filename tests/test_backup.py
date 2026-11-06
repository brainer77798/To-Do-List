"""
Tests for CSV export formula sanitization, JSON export security, and backup import/restore.
"""

import pytest
import csv
import io
import json
from taskvault.services import backup_service, task_service, project_service
from taskvault.utils.formatting import sanitize_csv_field
from taskvault.utils.validation import ValidationError


def test_csv_formula_injection_sanitization():
    # Value starting with '=' should be prepended with apostrophe
    malicious_val = "=cmd|'/C calc'!A0"
    sanitized = sanitize_csv_field(malicious_val)
    assert sanitized.startswith("'=")

    # Plus and minus triggers
    assert sanitize_csv_field("+1234").startswith("'+")
    assert sanitize_csv_field("-SUM(A1:A10)").startswith("'-")
    assert sanitize_csv_field("@SUM(A1:A10)").startswith("'@")

    # Safe text left untouched
    assert sanitize_csv_field("Normal task title") == "Normal task title"


def test_csv_export_format(authenticated_session):
    task_service.create_full_task(
        title="=HYPERLINK('http://attacker.com')",
        description="Safe description",
        db_session=authenticated_session,
    )
    csv_str = backup_service.export_tasks_csv(include_all=True, db_session=authenticated_session)
    reader = csv.reader(io.StringIO(csv_str))
    rows = list(reader)

    # Header check
    assert rows[0][1] == "Title"
    assert rows[0][2] == "Description"

    # Data check (row 1 is title, should be sanitized)
    assert rows[1][1].startswith("'=")


def test_json_backup_excludes_credentials(authenticated_session):
    project_service.create_project(name="Confidential Project", db_session=authenticated_session)
    task_service.create_quick_task("Sensitive task title", db_session=authenticated_session)

    backup_dict = backup_service.export_json_backup(db_session=authenticated_session)

    assert backup_dict["version"] == "1.0"
    assert len(backup_dict["projects"]) == 1
    assert len(backup_dict["tasks"]) == 1

    # Security check: password_hash, recovery_code_hash, and database url must NEVER be exported
    backup_str = json.dumps(backup_dict)
    assert "password_hash" not in backup_str
    assert "recovery_code_hash" not in backup_str
    assert "database_url" not in backup_str


def test_import_invalid_json(authenticated_session):
    with pytest.raises(ValidationError):
        backup_service.import_json_backup({"invalid": "schema"}, db_session=authenticated_session)


def test_import_json_backup_merge_and_replace(authenticated_session):
    p1 = project_service.create_project(name="Original Proj", db_session=authenticated_session)
    task_service.create_quick_task("Task to replace", project_id=p1.id, db_session=authenticated_session)

    # Export clean backup
    clean_backup = {
        "version": "1.0",
        "settings": {},
        "projects": [{"id": "p-1", "name": "Imported Proj", "status": "active"}],
        "tags": [{"id": "tg-1", "name": "urgent-tag", "normalized_name": "urgent-tag"}],
        "tasks": [
            {
                "id": "t-1",
                "title": "Imported Task",
                "status": "todo",
                "priority": "high",
                "project_id": "p-1",
                "tags": ["urgent-tag"],
                "checklist_items": [{"id": "c-1", "text": "Step 1", "is_completed": False, "sort_order": 0}],
            }
        ],
    }

    # Test Replace mode
    res = backup_service.import_json_backup(clean_backup, mode="replace", db_session=authenticated_session)
    assert res["tasks_imported"] == 1
    assert res["projects_imported"] == 1

    # Original task should be gone, imported task should exist
    current_tasks = task_service.query_tasks_filtered(db_session=authenticated_session)
    assert len(current_tasks) == 1
    assert current_tasks[0].title == "Imported Task"
    assert len(current_tasks[0].checklist_items) == 1

