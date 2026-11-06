"""
Recurring tasks and series management view for TaskVault.
Fulfills Section 6: recurring series creation, inspection, pausing, and scheduling.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
import streamlit as st
from sqlalchemy import select

from taskvault.ui.components import render_header, render_empty_state
from taskvault.models.task import RecurrenceSeries
from taskvault.services import recurrence_service, project_service
from taskvault.database import get_db_session
from taskvault.utils.dates import to_local


WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def render_recurrence_view(settings: dict) -> None:
    tz_name = settings.get("timezone", "America/New_York")
    render_header("🔄 Recurring Tasks", "Manage automated routines, repeating habits, and interval schedules")

    projects = project_service.list_projects()

    # Create new recurring series
    with st.expander("➕ Set Up New Recurring Task Series", expanded=False):
        with st.form("create_recurrence_form"):
            title = st.text_input("Series Title *", placeholder="e.g. Weekly Status Report, Clean Inbox...")
            desc = st.text_area("Notes / Template Description", placeholder="Checklist or steps for each occurrence...")

            cols1 = st.columns(3)
            with cols1[0]:
                freq = st.selectbox(
                    "Frequency",
                    options=["daily", "weekdays", "weekly", "monthly", "yearly", "custom"],
                    format_func=lambda x: {
                        "daily": "Every Day",
                        "weekdays": "Weekdays (Mon–Fri)",
                        "weekly": "Every Week",
                        "monthly": "Every Month",
                        "yearly": "Every Year",
                        "custom": "Custom Interval",
                    }[x],
                )
            with cols1[1]:
                interval = st.number_input("Interval (Every N days/weeks/months)", min_value=1, max_value=365, value=1)
            with cols1[2]:
                prio = st.selectbox("Priority", ["medium", "urgent", "high", "low"], format_func=lambda x: x.capitalize())

            # Frequency-specific fields
            weekdays_selected = None
            day_of_month_selected = None

            if freq == "weekly":
                st.markdown("**Repeat on Days:**")
                day_checks = st.columns(7)
                selected_days = []
                for i, d_name in enumerate(WEEKDAY_NAMES):
                    if day_checks[i].checkbox(d_name[:3], value=(i == 0), key=f"wd_chk_{i}"):
                        selected_days.append(i)
                weekdays_selected = selected_days or [0]

            elif freq in ("monthly", "yearly"):
                day_of_month_selected = st.slider("Day of Month", min_value=1, max_value=31, value=min(date.today().day, 28))

            cols2 = st.columns(3)
            with cols2[0]:
                proj_choices = [("", "No Project (Inbox)")] + [(p.id, p.name) for p in projects]
                proj_id = st.selectbox("Assign to Project", options=[p[0] for p in proj_choices], format_func=lambda x: dict(proj_choices).get(x, "Inbox"))
            with cols2[1]:
                st_date = st.date_input("Start Date", value=date.today())
            with cols2[2]:
                has_end = st.checkbox("Set End Date", value=False)
                end_date = st.date_input("End Date", value=date.today(), disabled=not has_end)

            est_mins = st.number_input("Estimated Minutes per Occurrence", min_value=0, max_value=480, value=30, step=15)

            submitted = st.form_submit_button("Create Recurring Series", type="primary")

            if submitted:
                if not title.strip():
                    st.error("Title cannot be empty.")
                else:
                    recurrence_service.create_recurrence_series(
                        title=title.strip(),
                        frequency=freq,
                        interval=interval,
                        weekdays=weekdays_selected,
                        day_of_month=day_of_month_selected,
                        start_date=st_date,
                        end_date=end_date if has_end else None,
                        description=desc.strip() if desc else None,
                        priority=prio,
                        project_id=proj_id if proj_id else None,
                        estimated_minutes=est_mins if est_mins > 0 else None,
                        timezone_name=tz_name,
                    )
                    st.toast(f"Recurring series '{title}' activated!", icon="🔄")
                    st.rerun()

    st.markdown("---")

    # List existing recurrence series
    with get_db_session() as db:
        series_list = list(db.execute(select(RecurrenceSeries).order_by(RecurrenceSeries.created_at.desc())).scalars().all())

    if not series_list:
        render_empty_state("No recurring series yet", "Create a recurring series above to automatically generate tasks on schedule.", "🔄")
    else:
        st.write(f"**{len(series_list)} recurring task templates**")
        for s in series_list:
            with st.container(border=True):
                cols = st.columns([0.55, 0.25, 0.2])
                with cols[0]:
                    status_badge = "⏸️ Paused" if s.is_paused else "🟢 Active"
                    st.markdown(f"**{s.title}** ({status_badge})")

                    freq_str = f"Repeats every {s.interval} {s.frequency}" if s.interval > 1 else f"Repeats {s.frequency}"
                    if s.frequency == "weekly" and s.weekdays:
                        wds = json.loads(s.weekdays)
                        freq_str += f" on {', '.join(WEEKDAY_NAMES[d] for d in wds)}"
                    elif s.day_of_month:
                        freq_str += f" on day {s.day_of_month}"

                    st.caption(f"🔄 {freq_str}")
                    if s.description:
                        st.caption(f"Notes: {s.description}")

                with cols[1]:
                    if s.next_occurrence_at:
                        local_next = to_local(s.next_occurrence_at, tz_name)
                        if local_next:
                            st.write(f"📅 **Next:** {local_next.strftime('%b %d, %Y')}")
                    else:
                        st.caption("No upcoming date")

                with cols[2]:
                    btn_cols = st.columns(2)
                    with btn_cols[0]:
                        pause_label = "▶️ Resume" if s.is_paused else "⏸️ Pause"
                        if st.button(pause_label, key=f"rec_pause_{s.id}"):
                            with get_db_session() as db:
                                live_s = db.execute(select(RecurrenceSeries).where(RecurrenceSeries.id == s.id)).scalar_one()
                                live_s.is_paused = not live_s.is_paused
                                live_s.updated_at = datetime.now(timezone.utc)
                            st.toast(f"Series {'resumed' if s.is_paused else 'paused'}", icon="🔄")
                            st.rerun()

                    with btn_cols[1]:
                        if st.button("🗑️ Delete", key=f"rec_del_{s.id}"):
                            with get_db_session() as db:
                                live_s = db.execute(select(RecurrenceSeries).where(RecurrenceSeries.id == s.id)).scalar_one_or_none()
                                if live_s:
                                    db.delete(live_s)
                            st.toast("Recurring series deleted.", icon="🗑️")
                            st.rerun()
