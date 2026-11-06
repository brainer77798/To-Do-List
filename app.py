"""
TaskVault - Private, password-protected personal task manager.
Main Streamlit application entrypoint.
"""

from __future__ import annotations

import streamlit as st

from taskvault.config import load_config, PRODUCT_NAME, ConfigurationError
from taskvault.database import init_db
from taskvault.security.access_control import SessionManager
from taskvault.services import auth_service
from taskvault.ui.styles import get_custom_css
from taskvault.ui.auth_screen import render_first_run_setup, render_unlock_screen
from taskvault.ui.navigation import render_sidebar

# Import view components
from taskvault.ui.views.dashboard_view import render_dashboard_view
from taskvault.ui.views.inbox_view import render_inbox_view
from taskvault.ui.views.today_view import render_today_view
from taskvault.ui.views.upcoming_view import render_upcoming_view
from taskvault.ui.views.tasks_view import render_tasks_view
from taskvault.ui.views.board_view import render_board_view
from taskvault.ui.views.calendar_view import render_calendar_view
from taskvault.ui.views.projects_view import render_projects_view
from taskvault.ui.views.completed_view import render_completed_view
from taskvault.ui.views.archive_trash_view import render_archive_trash_view
from taskvault.ui.views.focus_view import render_focus_view
from taskvault.ui.views.insights_view import render_insights_view
from taskvault.ui.views.settings_view import render_settings_view


def main() -> None:
    # Page configuration
    st.set_page_config(
        page_title=PRODUCT_NAME,
        page_icon="🔒",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Load configuration and catch production misconfigurations early
    try:
        config = load_config()
    except ConfigurationError as ce:
        st.error(f"Configuration Error: {ce}")
        st.stop()
        return

    # Initialize schema tables if they do not exist
    try:
        init_db()
    except Exception as db_err:
        st.error(f"Database Initialization Error: {db_err}")
        st.stop()
        return

    # Check first-run status
    try:
        if auth_service.is_first_run():
            st.markdown(get_custom_css("dark"), unsafe_allow_html=True)
            render_first_run_setup()
            return
    except Exception as e:
        st.error(f"Error checking workspace status: {e}")
        st.stop()
        return

    # Fetch security status and settings
    sec_status = auth_service.get_security_status()
    lock_timeout = sec_status.get("lock_timeout_minutes", 10)
    theme = sec_status.get("theme", "dark")

    # Apply CSS styling
    st.markdown(get_custom_css(theme), unsafe_allow_html=True)

    # Enforce access gate: session must be explicitly unlocked and active
    if not SessionManager.is_unlocked(timeout_minutes=lock_timeout):
        render_unlock_screen()
        return

    # Authenticated: Touch session activity to maintain session
    SessionManager.touch_activity()

    # Render sidebar navigation
    active_page = render_sidebar(sec_status)

    # Route to selected destination
    if active_page == "dashboard":
        render_dashboard_view(sec_status)
    elif active_page == "inbox":
        render_inbox_view(sec_status)
    elif active_page == "today":
        render_today_view(sec_status)
    elif active_page == "upcoming":
        render_upcoming_view(sec_status)
    elif active_page == "tasks":
        render_tasks_view(sec_status)
    elif active_page == "board":
        render_board_view(sec_status)
    elif active_page == "calendar":
        render_calendar_view(sec_status)
    elif active_page == "projects":
        render_projects_view(sec_status)
    elif active_page == "completed":
        render_completed_view(sec_status)
    elif active_page == "archive_trash":
        render_archive_trash_view(sec_status)
    elif active_page == "focus":
        render_focus_view(sec_status)
    elif active_page == "insights":
        render_insights_view(sec_status)
    elif active_page == "settings":
        render_settings_view(sec_status)
    else:
        render_dashboard_view(sec_status)


if __name__ == "__main__":
    main()

