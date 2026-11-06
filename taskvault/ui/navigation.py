"""
Navigation sidebar and view routing for TaskVault.
"""

from __future__ import annotations

import streamlit as st

from taskvault.services import auth_service
from taskvault.config import PRODUCT_NAME, APP_VERSION


NAV_ITEMS = [
    ("dashboard", "🏠 Dashboard"),
    ("inbox", "📥 Inbox"),
    ("today", "☀️ My Day"),
    ("upcoming", "📆 Upcoming"),
    ("tasks", "📋 All Tasks"),
    ("board", "📌 Board"),
    ("calendar", "🗓️ Calendar"),
    ("projects", "📁 Projects"),
    ("completed", "✅ Completed"),
    ("archive_trash", "📦 Archive & Trash"),
    ("focus", "⏱️ Focus Mode"),
    ("insights", "📊 Insights"),
    ("settings", "⚙️ Settings"),
]


def render_sidebar(settings: dict) -> str:
    """Renders the navigation sidebar and returns the selected page key."""
    if "current_nav_page" not in st.session_state:
        st.session_state.current_nav_page = "dashboard"

    with st.sidebar:
        # App branding
        st.markdown(
            f"""
            <div style="padding: 0.5rem 0 1rem 0;">
                <div style="font-size: 1.4rem; font-weight: 800; color: #F8FAFC; letter-spacing: -0.03em;">
                    🔒 {PRODUCT_NAME}
                </div>
                <div style="font-size: 0.8rem; color: #94A3B8;">Private Task Manager v{APP_VERSION}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("---")

        # Navigation options
        for key, label in NAV_ITEMS:
            is_active = st.session_state.current_nav_page == key
            btn_type = "primary" if is_active else "secondary"
            if st.button(label, key=f"nav_btn_{key}", use_container_width=True, type=btn_type):
                st.session_state.current_nav_page = key
                st.session_state.pop("editing_task_id", None)
                st.rerun()

        st.markdown("---")

        # Sidebar footer with Manual Lock Now
        st.caption("Active Session")
        if st.button("🔒 Lock Workspace", key="sidebar_lock_btn", use_container_width=True):
            auth_service.lock_workspace()
            st.rerun()

    return st.session_state.current_nav_page

