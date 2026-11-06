"""
Inbox view for TaskVault.
Fast capture area for unorganized tasks.
"""

from __future__ import annotations

import streamlit as st
from taskvault.ui.components import render_header, render_empty_state
from taskvault.ui.task_cards import render_task_card
from taskvault.ui.task_forms import render_quick_add, render_task_edit_modal
from taskvault.services import task_service, project_service


def render_inbox_view(settings: dict) -> None:
    tz_name = settings.get("timezone", "America/New_York")
    render_header("📥 Inbox", "Quickly capture ideas and unsorted tasks. Assign to projects later.")

    # Quick Add
    render_quick_add(
        project_id=None,
        default_priority=settings.get("default_priority", "medium"),
        timezone_name=tz_name,
        key_prefix="inbox_add",
    )

    # Edit Modal check
    edit_id = st.session_state.get("editing_task_id")
    if edit_id:
        projects = project_service.list_projects()
        render_task_edit_modal(edit_id, tz_name, projects, [])

    st.markdown("---")

    # Fetch tasks without project
    tasks = task_service.query_tasks_filtered(
        project_id="inbox",
        status="todo",
        is_archived=False,
        in_trash=False,
        exclude_subtasks=True,
        sort_by="due_date",
        sort_asc=True,
    )

    if not tasks:
        render_empty_state("Inbox Zero!", "Your inbox is completely clear. Tasks added here can be sorted into projects later.", "📥")
    else:
        st.write(f"**{len(tasks)} items in Inbox**")
        for task in tasks:
            render_task_card(task, tz_name, key_prefix="inbox_list", show_project=False)

