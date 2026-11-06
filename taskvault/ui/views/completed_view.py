"""
Completed tasks view for TaskVault.
Review completed work and easily reopen tasks.
"""

from __future__ import annotations

import streamlit as st

from taskvault.ui.components import render_header, render_empty_state
from taskvault.services import task_service, project_service
from taskvault.utils.dates import to_local


def render_completed_view(settings: dict) -> None:
    tz_name = settings.get("timezone", "America/New_York")
    render_header("✅ Completed Tasks", "Log of accomplished work")

    projects = project_service.list_projects()
    proj_choices = [("All", "All Projects")] + [(p.id, p.name) for p in projects]
    selected_proj = st.selectbox(
        "Filter by Project",
        options=[p[0] for p in proj_choices],
        format_func=lambda x: dict(proj_choices)[x],
        key="comp_proj_filter",
    )

    completed_tasks = task_service.query_tasks_filtered(
        status="done",
        project_id=selected_proj if selected_proj != "All" else None,
        is_archived=False,
        in_trash=False,
        exclude_subtasks=True,
        sort_by="updated_at",
        sort_asc=False,
    )

    if not completed_tasks:
        render_empty_state("No completed tasks yet", "Complete tasks in Today, Inbox, or Projects to see your accomplishments here.", "🌱")
    else:
        st.write(f"**{len(completed_tasks)} completed tasks**")
        for t in completed_tasks:
            with st.container(border=True):
                cols = st.columns([0.7, 0.2, 0.1])
                with cols[0]:
                    st.markdown(f"**{t.title}**")
                    meta = []
                    if t.project:
                        meta.append(f"📁 {t.project.name}")
                    if t.completed_at:
                        local_comp = to_local(t.completed_at, tz_name)
                        if local_comp:
                            meta.append(f"Completed on {local_comp.strftime('%b %d, %Y at %I:%M %p')}")
                    st.caption(" &bull; ".join(meta))

                with cols[1]:
                    if t.actual_minutes:
                        st.caption(f"⏱️ {t.actual_minutes}m tracked")

                with cols[2]:
                    if st.button("↺ Reopen", key=f"reopen_{t.id}"):
                        task_service.toggle_task_done(t.id, is_completed=False)
                        st.toast("Task reopened!", icon="↺")
                        st.rerun()

