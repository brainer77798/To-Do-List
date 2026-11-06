"""
Calendar view for TaskVault.
Responsive calendar grid displaying tasks on due dates with day selection.
"""

from __future__ import annotations

import calendar
from datetime import datetime, date, timedelta
from collections import defaultdict
import streamlit as st

from taskvault.ui.components import render_header, render_empty_state
from taskvault.ui.task_cards import render_task_card
from taskvault.ui.task_forms import render_quick_add, render_task_edit_modal
from taskvault.services import task_service, project_service
from taskvault.utils.dates import get_local_today, to_local


def render_calendar_view(settings: dict) -> None:
    tz_name = settings.get("timezone", "America/New_York")
    today = get_local_today(tz_name)

    render_header("🗓️ Calendar", "Monthly schedule and deadline planner")

    if "cal_year" not in st.session_state:
        st.session_state.cal_year = today.year
    if "cal_month" not in st.session_state:
        st.session_state.cal_month = today.month
    if "cal_selected_date" not in st.session_state:
        st.session_state.cal_selected_date = today

    # Navigation bar
    nav_cols = st.columns([0.2, 0.6, 0.2])
    with nav_cols[0]:
        if st.button("◀ Previous Month", use_container_width=True):
            if st.session_state.cal_month == 1:
                st.session_state.cal_month = 12
                st.session_state.cal_year -= 1
            else:
                st.session_state.cal_month -= 1
            st.rerun()

    with nav_cols[1]:
        month_name = calendar.month_name[st.session_state.cal_month]
        st.markdown(
            f"<h3 style='text-align: center; margin: 0;'>{month_name} {st.session_state.cal_year}</h3>",
            unsafe_allow_html=True,
        )

    with nav_cols[2]:
        if st.button("Next Month ▶", use_container_width=True):
            if st.session_state.cal_month == 12:
                st.session_state.cal_month = 1
                st.session_state.cal_year += 1
            else:
                st.session_state.cal_month += 1
            st.rerun()

    # Edit modal check
    edit_id = st.session_state.get("editing_task_id")
    projects = project_service.list_projects()
    if edit_id:
        render_task_edit_modal(edit_id, tz_name, projects, [])

    # Fetch active tasks
    tasks = task_service.query_tasks_filtered(
        is_archived=False,
        in_trash=False,
        exclude_subtasks=True,
    )

    tasks_by_date = defaultdict(list)
    for t in tasks:
        if t.due_at:
            local_due = to_local(t.due_at, tz_name)
            if local_due:
                tasks_by_date[local_due.date()].append(t)

    # Render Month Matrix
    cal = calendar.monthcalendar(st.session_state.cal_year, st.session_state.cal_month)
    weekdays_header = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    header_cols = st.columns(7)
    for i, name in enumerate(weekdays_header):
        header_cols[i].markdown(f"<div style='text-align: center; font-weight: 700; color: #94A3B8;'>{name}</div>", unsafe_allow_html=True)

    for week in cal:
        week_cols = st.columns(7)
        for i, day in enumerate(week):
            if day == 0:
                week_cols[i].write("")
            else:
                d = date(st.session_state.cal_year, st.session_state.cal_month, day)
                day_tasks = tasks_by_date.get(d, [])
                task_badge = f" ({len(day_tasks)})" if day_tasks else ""

                btn_type = "primary" if d == st.session_state.cal_selected_date else "secondary"
                label = f"{day}{task_badge}"

                if week_cols[i].button(label, key=f"cal_day_{d.isoformat()}", type=btn_type, use_container_width=True):
                    st.session_state.cal_selected_date = d
                    st.rerun()

    st.markdown("---")

    # Selected Date Tasks
    sel_date = st.session_state.cal_selected_date
    st.markdown(f"### 📋 Tasks for {sel_date.strftime('%A, %B %d, %Y')}")

    render_quick_add(
        planned_for_date=sel_date,
        default_priority=settings.get("default_priority", "medium"),
        timezone_name=tz_name,
        key_prefix="cal_quick",
    )

    day_tasks = tasks_by_date.get(sel_date, [])
    if not day_tasks:
        render_empty_state("No tasks due on this date", "Use the quick-add form above to schedule a task for this date.", "📅")
    else:
        for t in day_tasks:
            render_task_card(t, tz_name, key_prefix="cal_list")

