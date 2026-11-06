"""
Settings and Data Management view for TaskVault.
"""

from __future__ import annotations

import json
from zoneinfo import available_timezones
import streamlit as st

from taskvault.ui.components import render_header
from taskvault.services import auth_service, backup_service
from taskvault.repositories import security_repository
from taskvault.database import get_db_session
from taskvault.config import load_config
from taskvault.security.passwords import PasswordValidationError


POPULAR_TIMEZONES = [
    "America/New_York",
    "America/Chicago",
    "America/Denver",
    "America/Los_Angeles",
    "America/Toronto",
    "Europe/London",
    "Europe/Paris",
    "Europe/Berlin",
    "Asia/Tokyo",
    "Asia/Singapore",
    "Asia/Kolkata",
    "Australia/Sydney",
    "UTC",
]


def render_settings_view(settings: dict) -> None:
    render_header("⚙️ Settings", "Preferences, security controls, backups, and workspace configuration")

    tab_pref, tab_sec, tab_data, tab_about = st.tabs(["🎨 Preferences", "🔒 Security", "💾 Data & Backup", "ℹ️ About"])

    # Tab 1: Preferences
    with tab_pref:
        st.markdown("#### Workspace Preferences")
        with st.form("preferences_form"):
            curr_tz = settings.get("timezone", "America/New_York")
            tz_opts = list(set([curr_tz] + POPULAR_TIMEZONES))
            tz_opts.sort()
            selected_tz = st.selectbox("Timezone", options=tz_opts, index=tz_opts.index(curr_tz))

            theme_opts = ["dark", "light"]
            curr_theme = settings.get("theme", "dark")
            selected_theme = st.selectbox("Theme", options=theme_opts, index=theme_opts.index(curr_theme), format_func=lambda x: x.capitalize())

            prio_opts = ["urgent", "high", "medium", "low"]
            curr_prio = settings.get("default_priority", "medium")
            selected_prio = st.selectbox("Default Task Priority", options=prio_opts, index=prio_opts.index(curr_prio), format_func=lambda x: x.capitalize())

            curr_horizon = settings.get("due_soon_days", 7)
            selected_horizon = st.slider("Due-Soon Alert Horizon (Days)", min_value=1, max_value=30, value=curr_horizon)

            curr_capacity = settings.get("daily_capacity_minutes", 480)
            selected_capacity = st.number_input("Daily Workload Capacity (Minutes)", min_value=60, max_value=1440, value=curr_capacity, step=30)

            save_pref_btn = st.form_submit_button("Save Preferences", type="primary")
            if save_pref_btn:
                with get_db_session() as db:
                    security_repository.update_settings(
                        db,
                        timezone=selected_tz,
                        theme=selected_theme,
                        default_priority=selected_prio,
                        due_soon_days=selected_horizon,
                        daily_capacity_minutes=selected_capacity,
                    )
                st.toast("Preferences saved!", icon="✅")
                st.rerun()

    # Tab 2: Security
    with tab_sec:
        st.markdown("#### Workspace Access & Authentication")

        # Inactivity timeout setting
        curr_timeout = settings.get("lock_timeout_minutes", 10)
        timeout_opts = [5, 10, 15, 30, 60]
        sel_timeout = st.selectbox(
            "Automatic Inactivity Lockout (Minutes)",
            options=timeout_opts,
            index=timeout_opts.index(curr_timeout) if curr_timeout in timeout_opts else 1,
            help="Session locks automatically after this period of inactivity.",
        )
        if sel_timeout != curr_timeout:
            with get_db_session() as db:
                security_repository.update_settings(db, lock_timeout_minutes=sel_timeout)
            st.toast(f"Inactivity lockout updated to {sel_timeout} minutes.", icon="🔒")
            st.rerun()

        st.markdown("---")
        st.markdown("#### Change Workspace Password")
        with st.form("change_password_form"):
            old_pw = st.text_input("Current Password", type="password")
            new_pw = st.text_input("New Password (min 12 characters)", type="password")
            conf_pw = st.text_input("Confirm New Password", type="password")
            change_btn = st.form_submit_button("Update Password", type="primary")

            if change_btn:
                try:
                    success = auth_service.change_password(old_pw, new_pw, conf_pw)
                    if success:
                        st.success("Password updated successfully! Please re-authenticate on next session.")
                    else:
                        st.error("Current password incorrect.")
                except PasswordValidationError as pe:
                    st.error(str(pe))
                except Exception as ex:
                    st.error(f"Error updating password: {ex}")

        st.markdown("---")
        st.markdown("#### Session Lock")
        if st.button("🔒 Lock Workspace Now", type="secondary"):
            auth_service.lock_workspace()
            st.rerun()

    # Tab 3: Data & Backup
    with tab_data:
        st.markdown("#### Export & Backups")

        exp_cols = st.columns(2)
        with exp_cols[0]:
            st.markdown("##### 📄 CSV Spreadsheet Export")
            st.caption("Exports your tasks into CSV format protected against formula injection.")
            csv_data = backup_service.export_tasks_csv(include_all=True)
            st.download_button(
                label="Download Tasks CSV",
                data=csv_data,
                file_name="taskvault_export.csv",
                mime="text/csv",
                use_container_width=True,
            )

        with exp_cols[1]:
            st.markdown("##### 📦 Full JSON Backup")
            st.caption("Complete versioned backup of tasks, projects, checklists, and safe preferences.")
            json_dict = backup_service.export_json_backup()
            json_str = json.dumps(json_dict, indent=2)
            st.download_button(
                label="Download JSON Backup",
                data=json_str,
                file_name="taskvault_backup.json",
                mime="application/json",
                use_container_width=True,
            )

        st.markdown("---")
        st.markdown("#### 📥 Restore from JSON Backup")
        uploaded_file = st.file_uploader("Upload TaskVault JSON Backup", type=["json"])
        if uploaded_file:
            try:
                payload = json.loads(uploaded_file.getvalue().decode("utf-8"))
                st.write(f"**Backup Preview:** {len(payload.get('tasks', []))} tasks, {len(payload.get('projects', []))} projects.")

                import_mode = st.radio("Import Strategy", ["merge", "replace"], format_func=lambda x: "Merge (Safely add non-duplicate tasks)" if x == "merge" else "Replace (Erase existing tasks and projects first)")

                if import_mode == "replace":
                    st.warning("⚠️ Warning: 'Replace' will permanently clear current tasks and projects before restoring.")

                if st.button("Start Backup Import", type="primary"):
                    res = backup_service.import_json_backup(payload, mode=import_mode)
                    st.success(f"Restore successful! Imported {res['tasks_imported']} tasks and {res['projects_imported']} projects.")
                    st.rerun()

            except Exception as e:
                st.error(f"Failed to read backup file: {e}")

        st.markdown("---")
        st.markdown("#### ⚠️ Danger Zone: Clear Workspace")
        st.caption("Permanently removes all tasks, projects, tags, and focus logs. Does not reset master password.")
        with st.expander("Clear All Data"):
            st.error("This action cannot be undone. Type 'DELETE ALL DATA' to confirm.")
            conf_phrase = st.text_input("Confirmation Phrase", key="clear_all_phrase")
            if st.button("Permanently Wipe All Data", type="primary"):
                if conf_phrase == "DELETE ALL DATA":
                    backup_service.import_json_backup({"version": "1.0", "tasks": [], "projects": [], "tags": []}, mode="replace")
                    st.toast("Workspace wiped successfully.", icon="🗑️")
                    st.rerun()
                else:
                    st.error("Incorrect confirmation phrase.")

    # Tab 4: About
    with tab_about:
        st.markdown("#### About TaskVault")
        cfg = load_config()
        db_type = "Local SQLite (Development)" if cfg.is_sqlite else "Managed PostgreSQL (Production)"
        st.write(f"**Version:** {cfg.version}")
        st.write(f"**Environment:** `{cfg.env}`")
        st.write(f"**Database Persistence:** {db_type}")
        st.write("**Security Architecture:** Argon2id password-gated access with persistent rate limiting.")

        st.markdown("---")
        st.markdown(
            """
            > **Security Notice:** The TaskVault password gate controls web application access to your private workspace.
            It does not replace hosting-level access controls or constitute end-to-end database encryption.
            Keep your deployment credentials and Streamlit account protected.
            """
        )

