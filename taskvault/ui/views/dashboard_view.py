"""
Dashboard / Home view for TaskVault.
"""

from __future__ import annotations

import streamlit as st
import plotly.express as px
import pandas as pd
from datetime import datetime, timezone, timedelta

from taskvault.ui.components import render_header, render_metric_card, render_empty_state
from taskvault.ui.task_cards import render_task_card
from taskvault.ui.task_forms import render_quick_add, render_task_edit_modal
from taskvault.services import (
    analytics_service,
    reminder_service,
    task_service,
    project_service,
)
from taskvault.repositories import tag_repository
from taskvault.utils.dates import get_local_today, get_local_now, get_zoneinfo


def render_dashboard_view(settings: dict) -> None:
    tz_name = settings.get("timezone", "America/New_York")
    local_now = get_local_now(tz_name)
    today = get_local_today(tz_name)

    # Greeting
    hour = local_now.hour
    greeting = "Good morning" if hour < 12 else "Good afternoon" if hour < 18 else "Good evening"
    render_header(
        title=f"{greeting}",
        subtitle=f"{local_now.strftime('%A, %B %d, %Y')} &bull; Your personal command center",
    )

    # Check for in-app reminders & alerts (Section 8.1)
    if "dismissed_reminders" not in st.session_state:
        st.session_state.dismissed_reminders = set()

    reminders = reminder_service.get_active_reminders(
        timezone_name=tz_name,
        horizon_days=settings.get("due_soon_days", 7),
        dismissed_ids=st.session_state.dismissed_reminders,
    )

    if reminders["overdue"]:
        with st.container(border=True):
            st.error(f"⚠️ You have {len(reminders['overdue'])} overdue task(s) requiring immediate attention!")
            for item in reminders["overdue"][:3]:
                cols = st.columns([0.8, 0.2])
                cols[0].write(f"• **{item['title']}** ({item['priority'].capitalize()})")
                if cols[1].button("Dismiss", key=f"dism_od_{item['id']}"):
                    st.session_state.dismissed_reminders.add(item["id"])
                    st.rerun()

    # Headline Metrics
    metrics = analytics_service.get_dashboard_metrics(
        timezone_name=tz_name,
        due_soon_days=settings.get("due_soon_days", 7),
    )

    m_cols = st.columns(4)
    render_metric_card(m_cols[0], "Active Tasks", metrics["active_count"], "#3B82F6")
    render_metric_card(m_cols[1], "Due Today", metrics["due_today_count"], "#F59E0B")
    render_metric_card(m_cols[2], "Overdue", metrics["overdue_count"], "#EF4444" if metrics["overdue_count"] > 0 else "#94A3B8")
    render_metric_card(m_cols[3], "Done This Week", metrics["completed_this_week"], "#10B981")

    # Quick Add Section
    st.markdown("### ⚡ Quick Capture")
    render_quick_add(
        default_priority=settings.get("default_priority", "medium"),
        timezone_name=tz_name,
        key_prefix="dash_quick",
    )

    # Check if a task edit modal is open
    edit_id = st.session_state.get("editing_task_id")
    if edit_id:
        projects = project_service.list_projects()
        tags = []
        render_task_edit_modal(edit_id, tz_name, projects, tags)

    st.markdown("---")

    # Layout: Next Up & Today Tasks on the Left, Mini Productivity Charts on the Right
    left_col, right_col = st.columns([0.62, 0.38])

    with left_col:
        st.markdown("### 🎯 Today's Focus & Next Up")

        # Query active tasks due today or urgent/high priority
        active_tasks = task_service.query_tasks_filtered(
            status="todo",
            is_archived=False,
            in_trash=False,
            exclude_subtasks=True,
            sort_by="due_date",
            sort_asc=True,
            limit=10,
        )

        if not active_tasks:
            render_empty_state("All clear for today!", "You have no pending tasks right now. Capture one above to get started.", "🎉")
        else:
            for task in active_tasks:
                render_task_card(task, tz_name, key_prefix="dash_list")

    with right_col:
        st.markdown("### 📊 Productivity Trend")
        trends = analytics_service.get_productivity_trends(days=7, timezone_name=tz_name)

        # Plot 7-day completion chart
        df_trends = pd.DataFrame(trends["daily_trends"])
        if not df_trends.empty:
            df_trends["date"] = pd.to_datetime(df_trends["date"]).dt.strftime("%a %d")
            fig = px.bar(
                df_trends,
                x="date",
                y="completions",
                title="Completions (Past 7 Days)",
                labels={"completions": "Done", "date": "Day"},
                color_discrete_sequence=["#3B82F6"],
            )
            fig.update_layout(
                margin=dict(l=10, r=10, t=30, b=10),
                height=220,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#94A3B8", size=10),
                xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=True, gridcolor="#334155"),
            )
            st.plotly_chart(fig, use_container_width=True)

        # Priority Breakdown
        p_counts = trends["priority_counts"]
        if sum(p_counts.values()) > 0:
            df_prio = pd.DataFrame([
                {"Priority": k.capitalize(), "Count": v}
                for k, v in p_counts.items() if v > 0
            ])
            color_map = {"Urgent": "#EF4444", "High": "#F97316", "Medium": "#3B82F6", "Low": "#94A3B8"}
            fig2 = px.pie(
                df_prio,
                names="Priority",
                values="Count",
                title="Active Task Priority",
                hole=0.45,
                color="Priority",
                color_discrete_map=color_map,
            )
            fig2.update_layout(
                margin=dict(l=10, r=10, t=30, b=10),
                height=220,
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#94A3B8", size=10),
            )
            st.plotly_chart(fig2, use_container_width=True)

