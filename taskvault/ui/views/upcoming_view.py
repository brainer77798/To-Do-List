"""
Upcoming view for TaskVault.
Group tasks by due date with horizon switching (7, 14, 30 days).
"""

from __future__ import annotations

from datetime import datetime, date, timedelta
from collections import defaultdict
import streamlit as st

from taskvault.ui.components import render_header, render_empty_state
from taskvault.ui.task_cards import render_task_card
from taskvault.ui.task_forms import render_task_edit_modal
from taskvault.services import task_service, project_service
from taskvault.utils.dates import get_local_today, to_local


def render_upcoming_view(settings: dict) -> None:
    tz_name = settings.get("timezone", "America/New_York")
    today = get_local_today(tz_name)

    render_header("📆 Upcoming", "Schedule and deadlines on your horizon")

    # Horizon selector
    horizon_choice = st.segmented_control(
        "Horizon",
        options=["Next 7 Days", "Next 14 Days", "Next 30 Days"],
        default="Next 7 Days",
    )
    horizon_days = 7 if horizon_choice == "Next 7 Days" else 14 if horizon_choice == "Next 14 Days" else 30
    cutoff_date = today + timedelta(days=horizon_days)

    # Edit modal check
    edit_id = st.session_state.get("editing_task_id")
    if edit_id:
        projects = project_service.list_projects()
        render_task_edit_modal(edit_id, tz_name, projects, [])

    # Fetch active tasks
    tasks = task_service.query_tasks_filtered(
        status="todo",
        is_archived=False,
        in_trash=False,
        exclude_subtasks=True,
        sort_by="due_date",
        sort_asc=True,
    )

    # Group tasks by due date
    grouped: dict[date, list] = defaultdict(list)
    no_due_date = []

    for t in tasks:
        if not t.due_at:
            no_due_date.append(t)
            continue
        local_due = to_local(t.due_at, tz_name)
        if not local_due:
            continue
        d = local_due.date()
        if today <= d <= cutoff_date:
            grouped[d].append(t)

    sorted_dates = sorted(grouped.keys())

    if not sorted_dates:
        render_empty_state(f"No upcoming deadlines in next {horizon_days} days", "Enjoy the peace of mind or schedule tasks with due dates.", "🏖️")
    else:
        for d in sorted_dates:
            diff = (d - today).days
            if diff == 0:
                day_heading = f"Today — {d.strftime('%A, %b %d')}"
            elif diff == 1:
                day_heading = f"Tomorrow — {d.strftime('%A, %b %d')}"
            else:
                day_heading = f"{d.strftime('%A, %b %d')} (in {diff} days)"

            st.markdown(f"#### 📅 {day_heading}")
            for t in grouped[d]:
                render_task_card(t, tz_name, key_prefix=f"upc_{d.isoformat()}")
            st.markdown("---")

