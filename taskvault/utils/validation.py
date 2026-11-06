"""
Validation helpers for user input and backup payloads.
"""

from __future__ import annotations

from typing import Dict, Any, List


class ValidationError(Exception):
    """Raised when user or schema validation fails."""
    pass


def validate_task_title(title: str) -> str:
    """Validates that a task title is not empty and conforms to sensible length limits."""
    clean = title.strip()
    if not clean:
        raise ValidationError("Task title is required and cannot be blank.")
    if len(clean) > 255:
        raise ValidationError("Task title cannot exceed 255 characters.")
    return clean


def validate_backup_payload(data: Dict[str, Any]) -> None:
    """
    Validates imported JSON backup structure.
    Checks for required keys and valid schema version.
    """
    if not isinstance(data, dict):
        raise ValidationError("Backup file must be a valid JSON object.")

    if "version" not in data:
        raise ValidationError("Backup is missing schema version identifier.")

    if not isinstance(data.get("tasks"), list):
        raise ValidationError("Backup must contain a 'tasks' list.")

    if not isinstance(data.get("projects"), list):
        raise ValidationError("Backup must contain a 'projects' list.")

