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
    ("recurrence", "🔄 Recurring"),
    ("tags", "🏷️ Tags & Labels"),
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

        # Sidebar footer with Active User & Session Controls
        username = settings.get("username") or "user"
        email = settings.get("email") or ""
        st.markdown(
            f"""
            <div style="padding: 0.25rem 0 0.5rem 0;">
                <div style="font-size: 0.85rem; font-weight: 600; color: #F1F5F9;">👤 {username}</div>
                {"<div style='font-size: 0.75rem; color: #94A3B8; overflow: hidden; text-overflow: ellipsis;'>" + email + "</div>" if email else ""}
            </div>
            """,
            unsafe_allow_html=True,
        )

        foot_cols = st.columns(2)
        with foot_cols[0]:
            if st.button("🔒 Lock", key="sidebar_lock_btn", use_container_width=True, help="Lock workspace session"):
                auth_service.lock_workspace()
                st.rerun()
        with foot_cols[1]:
            if st.button("🚪 Logout", key="sidebar_logout_btn", use_container_width=True, help="Log out of account"):
                auth_service.lock_workspace()
                st.session_state.clear()
                st.rerun()

    return st.session_state.current_nav_page

