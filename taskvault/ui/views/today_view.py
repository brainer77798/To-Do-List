"""
My Day / Today view for TaskVault.
Includes daily workload estimation vs capacity and progress indicators.
"""

from __future__ import annotations

from datetime import datetime, date
import streamlit as st

from taskvault.ui.components import render_header, render_empty_state
from taskvault.ui.task_cards import render_task_card
from taskvault.ui.task_forms import render_quick_add, render_task_edit_modal
from taskvault.services import task_service, project_service
from taskvault.utils.dates import get_local_today, is_overdue, is_due_today, to_local
from taskvault.utils.formatting import format_duration


def render_today_view(settings: dict) -> None:
    tz_name = settings.get("timezone", "America/New_York")
    today = get_local_today(tz_name)
    daily_capacity = settings.get("daily_capacity_minutes", 480)

    render_header(
        "☀️ My Day",
        f"{today.strftime('%A, %B %d, %Y')} &bull; Plan and execute today's highest priorities",
    )

    # Quick Add directly planned for today
    render_quick_add(
        planned_for_date=today,
        default_priority=settings.get("default_priority", "medium"),
        timezone_name=tz_name,
        key_prefix="today_add",
    )

    # Edit modal check
    edit_id = st.session_state.get("editing_task_id")
    if edit_id:
        projects = project_service.list_projects()
        render_task_edit_modal(edit_id, tz_name, projects, [])

    st.markdown("---")

    # Fetch active tasks
    all_active = task_service.query_tasks_filtered(
        is_archived=False,
        in_trash=False,
        exclude_subtasks=True,
    )

    overdue_tasks = []
    today_tasks = []

    total_est_minutes = 0
    completed_today_count = 0

    for t in all_active:
        is_planned = t.planned_for_date == today
        is_due = is_due_today(t.due_at, tz_name)
        is_od = is_overdue(t.due_at, tz_name, t.due_date_only) and t.status != "done"

        if is_od:
            overdue_tasks.append(t)
        elif (is_planned or is_due) and t.status != "done":
            today_tasks.append(t)
            total_est_minutes += (t.estimated_minutes or 30)
        elif t.status == "done" and t.completed_at:
            local_comp = to_local(t.completed_at, tz_name)
            if local_comp and local_comp.date() == today:
                completed_today_count += 1

    total_today_tasks = len(today_tasks) + completed_today_count
    pct = (completed_today_count / total_today_tasks) if total_today_tasks > 0 else 0.0

    # Workload vs Capacity Bar
    cols = st.columns([0.65, 0.35])
    with cols[0]:
        st.write(f"**Today's Progress:** {completed_today_count} of {total_today_tasks} completed")
        st.progress(pct)
    with cols[1]:
        cap_str = format_duration(daily_capacity)
        est_str = format_duration(total_est_minutes)
        if total_est_minutes > daily_capacity:
            st.warning(f"⚠️ Workload: {est_str} (exceeds {cap_str} capacity)")
        else:
            st.info(f"⏱️ Workload: {est_str} / {cap_str} daily capacity")

    # Overdue section
    if overdue_tasks:
        st.markdown("### ⚠️ Overdue Items")
        for t in overdue_tasks:
            render_task_card(t, tz_name, key_prefix="today_od")
        st.markdown("---")

    # Today's Tasks
    st.markdown("### 📋 Planned for Today")
    if not today_tasks:
        render_empty_state("No tasks planned for today", "Add a task above or mark tasks from your project lists for today.", "☀️")
    else:
        for t in today_tasks:
            render_task_card(t, tz_name, key_prefix="today_list")

