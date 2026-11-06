"""
Formatting and data sanitization helpers.
"""

from __future__ import annotations

from typing import Optional


def sanitize_csv_field(value: Optional[str]) -> str:
    """
    Prevents CSV / spreadsheet formula injection attacks.
    If a string starts with =, +, -, @, tab, or newline, prefix it with an apostrophe.
    """
    if value is None:
        return ""
    val_str = str(value)
    if not val_str:
        return ""
    trigger_chars = ("=", "+", "-", "@", "\t", "\r", "\n")
    if val_str.startswith(trigger_chars):
        return f"'{val_str}"
    return val_str


def format_duration(minutes: Optional[int]) -> str:
    """Formats an integer number of minutes into a human-readable duration."""
    if not minutes or minutes <= 0:
        return "0m"
    hours = minutes // 60
    rem = minutes % 60
    if hours > 0 and rem > 0:
        return f"{hours}h {rem}m"
    elif hours > 0:
        return f"{hours}h"
    else:
        return f"{rem}m"


def truncate_text(text: Optional[str], max_length: int = 100) -> str:
    """Truncates text with an ellipsis if it exceeds max_length."""
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."

