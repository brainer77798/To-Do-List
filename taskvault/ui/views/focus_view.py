"""
Focus Mode and Pomodoro Timer view for TaskVault.
Timestamp-based countdown tracking, session logging, and time tracking.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone, timedelta
import streamlit as st

from taskvault.ui.components import render_header
from taskvault.services import task_service, focus_service
from taskvault.models.base import utc_now


def render_focus_view(settings: dict) -> None:
    tz_name = settings.get("timezone", "America/New_York")
    render_header("⏱️ Focus Mode & Pomodoro", "Distraction-free execution for deep work")

    # Fetch active tasks for selection
    active_tasks = task_service.query_tasks_filtered(
        status="todo",
        is_archived=False,
        in_trash=False,
        exclude_subtasks=True,
    )

    task_choices = [("", "No Specific Task (General Focus)")] + [(t.id, t.title) for t in active_tasks]

    # Initialize timer state in session
    if "pomodoro_mode" not in st.session_state:
        st.session_state.pomodoro_mode = "focus"  # focus, short_break, long_break
    if "pomodoro_status" not in st.session_state:
        st.session_state.pomodoro_status = "idle"  # idle, running, paused
    if "pomodoro_end_time" not in st.session_state:
        st.session_state.pomodoro_end_time = None
    if "pomodoro_remaining_seconds" not in st.session_state:
        st.session_state.pomodoro_remaining_seconds = 25 * 60
    if "pomodoro_completed_sessions" not in st.session_state:
        st.session_state.pomodoro_completed_sessions = 0
    if "pomodoro_selected_task" not in st.session_state:
        st.session_state.pomodoro_selected_task = ""

    # Task selector
    st.markdown("#### 🎯 Focus Objective")
    task_idx = [t[0] for t in task_choices].index(st.session_state.pomodoro_selected_task) if st.session_state.pomodoro_selected_task in [t[0] for t in task_choices] else 0
    selected_task_id = st.selectbox(
        "Link Focus to Task",
        options=[t[0] for t in task_choices],
        index=task_idx,
        format_func=lambda x: dict(task_choices).get(x, ""),
        key="foc_task_select",
    )
    st.session_state.pomodoro_selected_task = selected_task_id

    # If linked task selected, display task notes & checklist
    if selected_task_id:
        task = task_service.get_task(selected_task_id)
        if task:
            with st.container(border=True):
                st.markdown(f"**Task:** {task.title}")
                if task.description:
                    st.caption(task.description)
                if task.checklist_items:
                    st.markdown("**Checklist:**")
                    for item in task.checklist_items:
                        chk = st.checkbox(item.text, value=item.is_completed, key=f"foc_chk_{item.id}")
                        if chk != item.is_completed:
                            task_service.toggle_checklist_item_status(item.id, chk)
                            st.rerun()

    st.markdown("---")

    # Mode Selector Tabs
    mode_cols = st.columns(3)
    with mode_cols[0]:
        if st.button("🧠 Focus (25m)", type="primary" if st.session_state.pomodoro_mode == "focus" else "secondary", use_container_width=True):
            st.session_state.pomodoro_mode = "focus"
            st.session_state.pomodoro_remaining_seconds = 25 * 60
            st.session_state.pomodoro_status = "idle"
            st.rerun()

    with mode_cols[1]:
        if st.button("☕ Short Break (5m)", type="primary" if st.session_state.pomodoro_mode == "short_break" else "secondary", use_container_width=True):
            st.session_state.pomodoro_mode = "short_break"
            st.session_state.pomodoro_remaining_seconds = 5 * 60
            st.session_state.pomodoro_status = "idle"
            st.rerun()

    with mode_cols[2]:
        if st.button("🌴 Long Break (15m)", type="primary" if st.session_state.pomodoro_mode == "long_break" else "secondary", use_container_width=True):
            st.session_state.pomodoro_mode = "long_break"
            st.session_state.pomodoro_remaining_seconds = 15 * 60
            st.session_state.pomodoro_status = "idle"
            st.rerun()

    # Calculate remaining time
    now_ts = time.time()
    if st.session_state.pomodoro_status == "running":
        if st.session_state.pomodoro_end_time:
            remaining = int(st.session_state.pomodoro_end_time - now_ts)
            if remaining <= 0:
                # Timer complete!
                st.session_state.pomodoro_status = "idle"
                st.session_state.pomodoro_remaining_seconds = 0
                if st.session_state.pomodoro_mode == "focus":
                    st.session_state.pomodoro_completed_sessions += 1
                    # Record completed session
                    dur = 25 * 60
                    focus_service.record_focus_session(
                        task_id=selected_task_id if selected_task_id else None,
                        started_at=utc_now() - timedelta(seconds=dur),
                        ended_at=utc_now(),
                        duration_seconds=dur,
                        session_type="focus",
                    )
                    st.balloons()
                    st.success("🎉 Focus session completed! Great job. Time for a well-deserved break.")
            else:
                st.session_state.pomodoro_remaining_seconds = remaining

    mins = st.session_state.pomodoro_remaining_seconds // 60
    secs = st.session_state.pomodoro_remaining_seconds % 60
    timer_display = f"{mins:02d}:{secs:02d}"

    st.markdown(
        f"""
        <div style="text-align: center; margin: 2rem 0;">
            <div style="font-size: 5rem; font-weight: 800; font-family: monospace; letter-spacing: -0.05em; color: #3B82F6;">
                {timer_display}
            </div>
            <div style="color: #94A3B8; font-size: 1rem; text-transform: uppercase; letter-spacing: 0.1em;">
                Mode: {st.session_state.pomodoro_mode.replace('_', ' ').title()} &bull; Completed today: {st.session_state.pomodoro_completed_sessions}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Controls
    ctrl_cols = st.columns([0.3, 0.3, 0.2, 0.2])
    with ctrl_cols[0]:
        if st.session_state.pomodoro_status == "running":
            if st.button("⏸️ Pause", use_container_width=True):
                st.session_state.pomodoro_status = "paused"
                st.session_state.pomodoro_remaining_seconds = max(0, int(st.session_state.pomodoro_end_time - now_ts))
                st.session_state.pomodoro_end_time = None
                st.rerun()
        else:
            if st.button("▶️ Start", type="primary", use_container_width=True):
                st.session_state.pomodoro_status = "running"
                st.session_state.pomodoro_end_time = now_ts + st.session_state.pomodoro_remaining_seconds
                st.rerun()

    with ctrl_cols[1]:
        if st.button("🔄 Reset", use_container_width=True):
            st.session_state.pomodoro_status = "idle"
            default_mins = 25 if st.session_state.pomodoro_mode == "focus" else (5 if st.session_state.pomodoro_mode == "short_break" else 15)
            st.session_state.pomodoro_remaining_seconds = default_mins * 60
            st.session_state.pomodoro_end_time = None
            st.rerun()

    with ctrl_cols[2]:
        if st.button("⏭️ Skip", use_container_width=True):
            if st.session_state.pomodoro_mode == "focus":
                st.session_state.pomodoro_mode = "short_break"
                st.session_state.pomodoro_remaining_seconds = 5 * 60
            else:
                st.session_state.pomodoro_mode = "focus"
                st.session_state.pomodoro_remaining_seconds = 25 * 60
            st.session_state.pomodoro_status = "idle"
            st.rerun()

    with ctrl_cols[3]:
        if st.button("💾 Log Now", help="Log completed time to task", use_container_width=True):
            if selected_task_id:
                # Log 25 mins
                focus_service.record_focus_session(
                    task_id=selected_task_id,
                    started_at=utc_now() - timedelta(minutes=25),
                    ended_at=utc_now(),
                    duration_seconds=25 * 60,
                    session_type="focus",
                )
                st.toast("Recorded 25m focus to task!", icon="⏱️")
                st.rerun()
            else:
                st.warning("Please select a task to log time against.")

    # Manual Duration Entry section
    st.markdown("---")
    with st.expander("⏱️ Log Manual Time to Task"):
        with st.form("manual_time_form", clear_on_submit=True):
            t_cols = st.columns([0.6, 0.4])
            with t_cols[0]:
                man_task = st.selectbox(
                    "Task",
                    options=[t[0] for t in task_choices if t[0]],
                    format_func=lambda x: dict(task_choices).get(x, ""),
                )
            with t_cols[1]:
                man_mins = st.number_input("Minutes Spent", min_value=1, max_value=600, value=30, step=5)
            log_btn = st.form_submit_button("Record Time", type="primary")

            if log_btn and man_task:
                focus_service.record_focus_session(
                    task_id=man_task,
                    started_at=utc_now() - timedelta(minutes=man_mins),
                    ended_at=utc_now(),
                    duration_seconds=man_mins * 60,
                    session_type="focus",
                )
                st.toast(f"Logged {man_mins}m to task!", icon="✅")
                st.rerun()

