"""
Board / Kanban view for TaskVault.
Organized into To Do, In Progress, and Done columns with reliable status transition actions.
"""

from __future__ import annotations

import streamlit as st

from taskvault.ui.components import render_header
from taskvault.ui.task_forms import render_task_edit_modal
from taskvault.services import task_service, project_service
from taskvault.utils.dates import format_relative_due


PRIORITY_COLORS = {
    "urgent": "#EF4444",
    "high": "#F97316",
    "medium": "#3B82F6",
    "low": "#94A3B8",
}


def render_board_view(settings: dict) -> None:
    tz_name = settings.get("timezone", "America/New_York")
    render_header("📌 Board", "Kanban workflow view")

    # Edit modal check
    edit_id = st.session_state.get("editing_task_id")
    projects = project_service.list_projects()
    if edit_id:
        render_task_edit_modal(edit_id, tz_name, projects, [])

    # Project filter on the board
    proj_choices = [("All", "All Projects")] + [(p.id, p.name) for p in projects]
    selected_proj = st.selectbox(
        "Filter by Project",
        options=[p[0] for p in proj_choices],
        format_func=lambda x: dict(proj_choices)[x],
        key="board_proj_filter",
    )

    tasks = task_service.query_tasks_filtered(
        project_id=selected_proj if selected_proj != "All" else None,
        is_archived=False,
        in_trash=False,
        exclude_subtasks=True,
    )

    todo_tasks = [t for t in tasks if t.status == "todo"]
    in_prog_tasks = [t for t in tasks if t.status == "in_progress"]
    done_tasks = [t for t in tasks if t.status == "done"]

    cols = st.columns(3)

    # Column 1: To Do
    with cols[0]:
        st.markdown(f"#### ⏳ To Do ({len(todo_tasks)})")
        for t in todo_tasks:
            _render_board_card(t, tz_name, current_col="todo")

    # Column 2: In Progress
    with cols[1]:
        st.markdown(f"#### 🚀 In Progress ({len(in_prog_tasks)})")
        for t in in_prog_tasks:
            _render_board_card(t, tz_name, current_col="in_progress")

    # Column 3: Done
    with cols[2]:
        st.markdown(f"#### ✅ Done ({len(done_tasks)})")
        for t in done_tasks:
            _render_board_card(t, tz_name, current_col="done")


def _render_board_card(task, tz_name: str, current_col: str) -> None:
    """Renders a compact card for Kanban columns with transition buttons."""
    with st.container(border=True):
        p_color = PRIORITY_COLORS.get(task.priority, "#3B82F6")
        st.markdown(f"<span style='color:{p_color}; font-weight:700;'>●</span> **{task.title}**", unsafe_allow_html=True)

        if task.project:
            st.caption(f"📁 {task.project.name}")

        if task.due_at:
            due_str = format_relative_due(task.due_at, tz_name, task.due_date_only)
            st.caption(f"📅 {due_str}")

        btn_cols = st.columns(3)
        with btn_cols[0]:
            if st.button("✏️", key=f"bd_edit_{task.id}", help="Edit"):
                st.session_state["editing_task_id"] = task.id
                st.rerun()

        if current_col == "todo":
            with btn_cols[1]:
                if st.button("→ Prog", key=f"bd_m_prog_{task.id}"):
                    task_service.update_task_details(task.id, status="in_progress")
                    st.rerun()
            with btn_cols[2]:
                if st.button("→ Done", key=f"bd_m_done_{task.id}"):
                    task_service.toggle_task_done(task.id, is_completed=True)
                    st.rerun()

        elif current_col == "in_progress":
            with btn_cols[1]:
                if st.button("← Todo", key=f"bd_m_todo_{task.id}"):
                    task_service.update_task_details(task.id, status="todo")
                    st.rerun()
            with btn_cols[2]:
                if st.button("→ Done", key=f"bd_m_done_{task.id}"):
                    task_service.toggle_task_done(task.id, is_completed=True)
                    st.rerun()

        elif current_col == "done":
            with btn_cols[1]:
                if st.button("↺ Reopen", key=f"bd_reopen_{task.id}"):
                    task_service.toggle_task_done(task.id, is_completed=False)
                    st.rerun()

