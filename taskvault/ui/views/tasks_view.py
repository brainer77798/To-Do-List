"""
All Tasks view for TaskVault.
Search, filtering, sorting, bulk actions, and view switcher.
"""

from __future__ import annotations

from typing import List, Set
import streamlit as st

from taskvault.ui.components import render_header, render_empty_state
from taskvault.ui.task_cards import render_task_card
from taskvault.ui.task_forms import render_quick_add, render_task_edit_modal
from taskvault.services import task_service, project_service
from taskvault.repositories import tag_repository


def render_tasks_view(settings: dict) -> None:
    tz_name = settings.get("timezone", "America/New_York")
    render_header("📋 All Tasks", "Complete, searchable catalog with multi-filters and bulk actions")

    # Quick Add
    render_quick_add(
        default_priority=settings.get("default_priority", "medium"),
        timezone_name=tz_name,
        key_prefix="all_tasks_add",
    )

    # Edit modal check
    edit_id = st.session_state.get("editing_task_id")
    projects = project_service.list_projects()
    if edit_id:
        render_task_edit_modal(edit_id, tz_name, projects, [])

    st.markdown("---")

    # Search & Filter Controls
    with st.expander("🔍 Search, Filter & Sort", expanded=False):
        search_col, sort_col, dir_col = st.columns([0.5, 0.3, 0.2])
        with search_col:
            search_query = st.text_input("Search tasks, projects, or tags", placeholder="Type keywords...", key="tasks_search")
        with sort_col:
            sort_by = st.selectbox(
                "Sort by",
                options=["due_date", "priority", "created_at", "updated_at", "title"],
                format_func=lambda x: {
                    "due_date": "Due Date",
                    "priority": "Priority",
                    "created_at": "Recently Created",
                    "updated_at": "Recently Updated",
                    "title": "Title (A-Z)",
                }[x],
                key="tasks_sort",
            )
        with dir_col:
            sort_dir = st.selectbox("Direction", options=["Ascending", "Descending"], key="tasks_sort_dir")
            sort_asc = sort_dir == "Ascending"

        filter_cols = st.columns(4)
        with filter_cols[0]:
            status_f = st.selectbox("Status", options=["All", "todo", "in_progress", "done"], format_func=lambda x: "All Statuses" if x == "All" else x.replace("_", " ").title(), key="filter_status")
        with filter_cols[1]:
            prio_f = st.selectbox("Priority", options=["All", "urgent", "high", "medium", "low"], format_func=lambda x: "All Priorities" if x == "All" else x.title(), key="filter_prio")
        with filter_cols[2]:
            proj_opts = [("All", "All Projects"), ("inbox", "Inbox (No Project)")] + [(p.id, p.name) for p in projects]
            proj_f = st.selectbox("Project", options=[p[0] for p in proj_opts], format_func=lambda x: dict(proj_opts)[x], key="filter_proj")
        with filter_cols[3]:
            cat_f = st.text_input("Category", placeholder="Filter category...", key="filter_cat")

    # Query tasks
    tasks = task_service.query_tasks_filtered(
        status=status_f if status_f != "All" else None,
        priority=prio_f if prio_f != "All" else None,
        project_id=proj_f if proj_f != "All" else None,
        category=cat_f.strip() if cat_f.strip() else None,
        search_query=search_query.strip() if search_query.strip() else None,
        is_archived=False,
        in_trash=False,
        exclude_subtasks=True,
        sort_by=sort_by,
        sort_asc=sort_asc,
    )

    # Bulk actions toggle
    b_cols = st.columns([0.2, 0.8])
    enable_bulk = b_cols[0].checkbox("Bulk Selection Mode", key="enable_bulk_mode")

    if enable_bulk and tasks:
        with st.container(border=True):
            st.markdown("##### ⚡ Bulk Actions on Selected Tasks")
            action_cols = st.columns([0.3, 0.4, 0.3])
            with action_cols[0]:
                bulk_action = st.selectbox(
                    "Action",
                    options=["mark_done", "mark_todo", "change_priority", "move_project", "archive", "delete"],
                    format_func=lambda x: {
                        "mark_done": "Mark Done",
                        "mark_todo": "Mark To Do",
                        "change_priority": "Change Priority",
                        "move_project": "Move to Project",
                        "archive": "Archive",
                        "delete": "Delete to Trash",
                    }[x],
                    key="bulk_action_type",
                )
            with action_cols[1]:
                val = None
                if bulk_action == "change_priority":
                    val = st.selectbox("New Priority", ["urgent", "high", "medium", "low"], key="bulk_val_prio")
                elif bulk_action == "move_project":
                    mv_opts = [("", "Inbox (No Project)")] + [(p.id, p.name) for p in projects]
                    val = st.selectbox("Destination Project", options=[p[0] for p in mv_opts], format_func=lambda x: dict(mv_opts)[x], key="bulk_val_proj")
                    if not val:
                        val = None

            with action_cols[2]:
                apply_bulk = st.button("Apply to Selected", type="primary", use_container_width=True)

            selected_ids = []
            for t in tasks:
                sel = render_task_card(t, tz_name, key_prefix="all_t_bulk", allow_selection=True)
                if sel:
                    selected_ids.append(t.id)

            if apply_bulk:
                if not selected_ids:
                    st.warning("No tasks were selected.")
                else:
                    count = task_service.execute_bulk_operations(selected_ids, bulk_action, val)
                    st.success(f"Updated {count} tasks successfully.")
                    st.rerun()

    else:
        # Standard rendering
        if not tasks:
            render_empty_state("No tasks match criteria", "Try resetting filters or capture a new task above.", "🔍")
        else:
            st.write(f"Showing **{len(tasks)}** tasks")
            for t in tasks:
                render_task_card(t, tz_name, key_prefix="all_t")

