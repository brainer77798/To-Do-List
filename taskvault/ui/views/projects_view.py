"""
Projects view for TaskVault.
Project cards, progress tracking, creation, editing, and task management.
"""

from __future__ import annotations

import streamlit as st

from taskvault.ui.components import render_header, render_empty_state
from taskvault.ui.task_cards import render_task_card
from taskvault.ui.task_forms import render_quick_add, render_task_edit_modal
from taskvault.services import project_service, task_service


def render_projects_view(settings: dict) -> None:
    tz_name = settings.get("timezone", "America/New_York")
    render_header("📁 Projects", "Organize tasks into structured goals and workflows")

    if "selected_project_id" not in st.session_state:
        st.session_state.selected_project_id = None

    # Form to create a new project
    with st.expander("➕ Create New Project", expanded=False):
        with st.form("new_project_form", clear_on_submit=True):
            p_name = st.text_input("Project Name *", placeholder="e.g. Website Redesign, Tax Return...")
            p_desc = st.text_area("Description (optional)", placeholder="Purpose or deliverables...")
            cols = st.columns(2)
            with cols[0]:
                p_color = st.color_picker("Project Color", value="#3B82F6")
            with cols[1]:
                p_icon = st.selectbox("Icon", ["folder", "briefcase", "code", "book", "star", "heart", "target"])
            submitted = st.form_submit_button("Create Project", type="primary")

            if submitted:
                if not p_name or not p_name.strip():
                    st.error("Project name cannot be empty.")
                else:
                    new_proj = project_service.create_project(
                        name=p_name.strip(),
                        description=p_desc.strip() if p_desc else None,
                        color=p_color,
                        icon=p_icon,
                    )
                    st.toast(f"Project '{new_proj.name}' created!", icon="📁")
                    st.session_state.selected_project_id = new_proj.id
                    st.rerun()

    projects = project_service.list_projects()

    if not projects:
        render_empty_state("No projects yet", "Create your first project above to group your tasks.", "📁")
        return

    # Project selection tabs or selectbox
    proj_opts = [(p.id, p.name) for p in projects]
    curr_id = st.session_state.selected_project_id or projects[0].id

    # Check if current selected ID is valid
    valid_ids = [p[0] for p in proj_opts]
    if curr_id not in valid_ids:
        curr_id = valid_ids[0]
        st.session_state.selected_project_id = curr_id

    sel_idx = valid_ids.index(curr_id)
    selected_id = st.selectbox(
        "Select Project",
        options=valid_ids,
        index=sel_idx,
        format_func=lambda x: dict(proj_opts).get(x, ""),
        key="project_selector",
    )
    st.session_state.selected_project_id = selected_id

    project = project_service.get_project(selected_id)
    if not project:
        return

    # Project Summary & Stats
    stats = project_service.get_project_summary(project.id)

    with st.container(border=True):
        p_cols = st.columns([0.7, 0.3])
        with p_cols[0]:
            st.markdown(
                f"<h3 style='margin:0; color:{project.color or '#3B82F6'};'>📁 {project.name}</h3>",
                unsafe_allow_html=True,
            )
            if project.description:
                st.caption(project.description)
        with p_cols[1]:
            st.metric(
                label="Completion",
                value=f"{stats['completion_percentage']}%",
                delta=f"{stats['completed_tasks']}/{stats['total_tasks']} Done",
            )

        st.progress(stats["completion_percentage"] / 100.0)

        # Actions: Edit / Archive / Delete
        act_cols = st.columns([0.4, 0.3, 0.3])
        with act_cols[0]:
            if st.button("📦 Archive Project", key=f"arch_proj_{project.id}"):
                project_service.archive_project(project.id)
                st.toast("Project archived", icon="📦")
                st.rerun()
        with act_cols[1]:
            pass
        with act_cols[2]:
            if st.button("🗑️ Delete Project", key=f"del_proj_{project.id}", type="secondary"):
                project_service.delete_project_item(project.id, move_tasks_to_inbox=True)
                st.toast("Project deleted; tasks moved to Inbox.", icon="🗑️")
                st.session_state.selected_project_id = None
                st.rerun()

    st.markdown("---")

    # Quick Add directly into this project
    st.markdown(f"#### ➕ Add Task to {project.name}")
    render_quick_add(
        project_id=project.id,
        default_priority=settings.get("default_priority", "medium"),
        timezone_name=tz_name,
        key_prefix=f"proj_add_{project.id}",
    )

    # Edit modal check
    edit_id = st.session_state.get("editing_task_id")
    if edit_id:
        render_task_edit_modal(edit_id, tz_name, projects, [])

    # Project tasks
    proj_tasks = task_service.query_tasks_filtered(
        project_id=project.id,
        is_archived=False,
        in_trash=False,
        exclude_subtasks=True,
    )

    if not proj_tasks:
        render_empty_state("No tasks in this project", "Capture tasks above to start organizing this project.", "📝")
    else:
        st.write(f"**{len(proj_tasks)} tasks in this project**")
        for t in proj_tasks:
            render_task_card(t, tz_name, key_prefix="proj_view_list", show_project=False)

