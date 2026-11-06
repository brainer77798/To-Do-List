"""
Productivity Insights and Analytics view for TaskVault.
Honest, accurate metrics and charts without artificial noise.
"""

from __future__ import annotations

import streamlit as st
import plotly.express as px
import pandas as pd

from taskvault.ui.components import render_header, render_metric_card
from taskvault.services import analytics_service, focus_service


def render_insights_view(settings: dict) -> None:
    tz_name = settings.get("timezone", "America/New_York")
    render_header("📊 Productivity Insights", "Track your momentum and focus patterns over time")

    time_range = st.segmented_control("Time Horizon", ["Last 7 Days", "Last 30 Days", "Last 90 Days"], default="Last 30 Days")
    days = 7 if time_range == "Last 7 Days" else (30 if time_range == "Last 30 Days" else 90)

    # Fetch real trends & streaks
    trends = analytics_service.get_productivity_trends(days=days, timezone_name=tz_name)
    streak_data = analytics_service.calculate_streak(timezone_name=tz_name)

    # Headline Metric cards
    m_cols = st.columns(3)
    render_metric_card(m_cols[0], "Completed In Period", trends["total_completions_in_period"], "#3B82F6")
    render_metric_card(m_cols[1], "Current Daily Streak", f"{streak_data['current_streak']} Days", "#F59E0B")
    avg_per_day = round(trends["total_completions_in_period"] / days, 1)
    render_metric_card(m_cols[2], "Daily Avg Output", f"{avg_per_day} Tasks", "#10B981")

    st.markdown("---")

    # Main Chart: Daily Completion Trend
    df_trends = pd.DataFrame(trends["daily_trends"])
    if not df_trends.empty:
        st.markdown(f"#### 📈 Completion Momentum ({time_range})")
        df_trends["date"] = pd.to_datetime(df_trends["date"]).dt.strftime("%b %d")
        fig = px.area(
            df_trends,
            x="date",
            y="completions",
            labels={"completions": "Completed Tasks", "date": "Date"},
            color_discrete_sequence=["#3B82F6"],
        )
        fig.update_layout(
            margin=dict(l=10, r=10, t=10, b=10),
            height=300,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#94A3B8"),
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor="#334155"),
        )
        st.plotly_chart(fig, use_container_width=True)

    # Split: Time tracked per project & Priority distribution
    chart_cols = st.columns(2)

    with chart_cols[0]:
        st.markdown("#### ⏱️ Time Tracked by Project")
        time_data = focus_service.get_time_by_project()
        if time_data:
            df_time = pd.DataFrame(time_data)
            fig_time = px.bar(
                df_time,
                x="project_name",
                y="total_minutes",
                labels={"project_name": "Project", "total_minutes": "Minutes Tracked"},
                color_discrete_sequence=["#10B981"],
            )
            fig_time.update_layout(
                margin=dict(l=10, r=10, t=10, b=10),
                height=260,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#94A3B8"),
            )
            st.plotly_chart(fig_time, use_container_width=True)
        else:
            st.info("No time tracking sessions recorded yet. Use Focus Mode to record work sessions.")

    with chart_cols[1]:
        st.markdown("#### 🎯 Active Tasks Priority Mix")
        p_counts = trends["priority_counts"]
        if sum(p_counts.values()) > 0:
            df_prio = pd.DataFrame([
                {"Priority": k.capitalize(), "Count": v}
                for k, v in p_counts.items() if v > 0
            ])
            color_map = {"Urgent": "#EF4444", "High": "#F97316", "Medium": "#3B82F6", "Low": "#94A3B8"}
            fig_p = px.pie(
                df_prio,
                names="Priority",
                values="Count",
                hole=0.45,
                color="Priority",
                color_discrete_map=color_map,
            )
            fig_p.update_layout(
                margin=dict(l=10, r=10, t=10, b=10),
                height=260,
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#94A3B8"),
            )
            st.plotly_chart(fig_p, use_container_width=True)
        else:
            st.info("No active tasks found.")

