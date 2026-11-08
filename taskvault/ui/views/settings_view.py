"""
Settings and Data Management view for TaskVault.
Includes full Account Profile, Preferences, Security, Data Backups, and System Info.
"""

from __future__ import annotations

import json
import streamlit as st

from taskvault.ui.components import render_header
from taskvault.services import auth_service, backup_service, task_service
from taskvault.config import load_config
from taskvault.security.passwords import PasswordValidationError
from taskvault.services.auth_service import AccountValidationError


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
    render_header("⚙️ Settings", "Account profile, preferences, security controls, and data management")

    profile = auth_service.get_current_user_profile()

    tab_account, tab_pref, tab_sec, tab_data, tab_about = st.tabs([
        "👤 Account & Profile",
        "🎨 Preferences",
        "🔒 Security",
        "💾 Data & Backup",
        "ℹ️ About",
    ])

    # -----------------------------------------------------------------------
    # Tab 1: Account & Profile
    # -----------------------------------------------------------------------
    with tab_account:
        st.markdown("#### User Profile & Credentials")
        st.caption("Manage your account identity, display name, and login credentials.")

        with st.form("account_profile_form"):
            curr_username = profile.get("username", "user")
            curr_email = profile.get("email", "")
            curr_fullname = profile.get("full_name", "")

            cols_prof = st.columns(2)
            with cols_prof[0]:
                new_username = st.text_input("Username", value=curr_username, help="Unique identifier for logging in.")
            with cols_prof[1]:
                new_email = st.text_input("Email Address", value=curr_email, help="Used for recovery and login.")

            new_fullname = st.text_input("Display / Full Name", value=curr_fullname or "", placeholder="e.g. Alex Mercer")

            # Read-only meta info
            cols_meta = st.columns(2)
            with cols_meta[0]:
                created_dt = profile.get("created_at")
                created_str = created_dt.strftime("%B %d, %Y") if hasattr(created_dt, "strftime") else "Initial Setup"
                st.write(f"**Member Since:** {created_str}")
            with cols_meta[1]:
                st.write(f"**Account ID:** `{profile.get('id', 'master')[:8]}...`")

            save_prof_btn = st.form_submit_button("Save Profile Changes", type="primary")

            if save_prof_btn:
                try:
                    res = auth_service.update_profile(
                        username=new_username,
                        email=new_email,
                        full_name=new_fullname,
                    )
                    if res.get("success"):
                        st.toast("Profile updated successfully!", icon="✅")
                        st.rerun()
                except (AccountValidationError, ValueError) as ex:
                    st.error(str(ex))
                except Exception as ex:
                    st.error(f"Error saving profile: {ex}")

    # -----------------------------------------------------------------------
    # Tab 2: Preferences
    # -----------------------------------------------------------------------
    with tab_pref:
        st.markdown("#### Workspace Preferences & Productivity Goals")
        with st.form("preferences_form"):
            curr_tz = profile.get("timezone") or settings.get("timezone", "America/New_York")
            tz_opts = list(set([curr_tz] + POPULAR_TIMEZONES))
            tz_opts.sort()
            selected_tz = st.selectbox("Timezone", options=tz_opts, index=tz_opts.index(curr_tz))

            theme_opts = ["dark", "light"]
            curr_theme = profile.get("theme") or settings.get("theme", "dark")
            selected_theme = st.selectbox(
                "Theme",
                options=theme_opts,
                index=theme_opts.index(curr_theme) if curr_theme in theme_opts else 0,
                format_func=lambda x: x.capitalize(),
            )

            prio_opts = ["urgent", "high", "medium", "low"]
            curr_prio = profile.get("default_priority") or settings.get("default_priority", "medium")
            selected_prio = st.selectbox(
                "Default Task Priority",
                options=prio_opts,
                index=prio_opts.index(curr_prio) if curr_prio in prio_opts else 2,
                format_func=lambda x: x.capitalize(),
            )

            week_opts = ["Monday", "Sunday"]
            curr_week = profile.get("week_starts_on") or settings.get("week_starts_on", "Monday")
            selected_week = st.selectbox(
                "Week Starts On",
                options=week_opts,
                index=week_opts.index(curr_week) if curr_week in week_opts else 0,
            )

            curr_horizon = profile.get("due_soon_days") or settings.get("due_soon_days", 7)
            selected_horizon = st.slider("Due-Soon Alert Horizon (Days)", min_value=1, max_value=30, value=curr_horizon)

            curr_capacity = profile.get("daily_capacity_minutes") or settings.get("daily_capacity_minutes", 480)
            selected_capacity = st.number_input("Daily Workload Capacity (Minutes)", min_value=60, max_value=1440, value=curr_capacity, step=30)

            st.markdown("##### 🎯 Productivity Goals (Spec Section 7.6)")
            cols_goals = st.columns(2)
            with cols_goals[0]:
                curr_daily_goal = profile.get("daily_goal", 5)
                selected_daily_goal = st.number_input("Daily Completion Goal (Tasks)", min_value=1, max_value=50, value=curr_daily_goal)
            with cols_goals[1]:
                curr_weekly_goal = profile.get("weekly_goal", 25)
                selected_weekly_goal = st.number_input("Weekly Completion Goal (Tasks)", min_value=5, max_value=200, value=curr_weekly_goal)

            save_pref_btn = st.form_submit_button("Save Preferences", type="primary")
            if save_pref_btn:
                auth_service.update_user_preferences(
                    timezone=selected_tz,
                    theme=selected_theme,
                    default_priority=selected_prio,
                    week_starts_on=selected_week,
                    due_soon_days=selected_horizon,
                    daily_capacity_minutes=selected_capacity,
                    daily_goal=selected_daily_goal,
                    weekly_goal=selected_weekly_goal,
                )
                st.toast("Preferences saved successfully!", icon="✅")
                st.rerun()

    # -----------------------------------------------------------------------
    # Tab 3: Security
    # -----------------------------------------------------------------------
    with tab_sec:
        st.markdown("#### Access Control & Session Security")

        # Inactivity timeout setting
        curr_timeout = profile.get("lock_timeout_minutes") or settings.get("lock_timeout_minutes", 10)
        timeout_opts = [5, 10, 15, 30, 60]
        sel_timeout = st.selectbox(
            "Automatic Inactivity Lockout (Minutes)",
            options=timeout_opts,
            index=timeout_opts.index(curr_timeout) if curr_timeout in timeout_opts else 1,
            help="Session locks automatically after this period of inactivity.",
        )
        if sel_timeout != curr_timeout:
            auth_service.update_user_preferences(lock_timeout_minutes=sel_timeout)
            st.toast(f"Inactivity lockout updated to {sel_timeout} minutes.", icon="🔒")
            st.rerun()

        st.markdown("---")
        st.markdown("#### Change Password")
        with st.form("change_password_form"):
            old_pw = st.text_input("Current Password", type="password")
            new_pw = st.text_input("New Password (min 12 characters)", type="password")
            conf_pw = st.text_input("Confirm New Password", type="password")
            change_btn = st.form_submit_button("Update Password", type="primary")

            if change_btn:
                try:
                    success = auth_service.change_password(old_pw, new_pw, conf_pw)
                    if success:
                        st.success("Password updated successfully! Please use your new password on next login.")
                    else:
                        st.error("Current password incorrect.")
                except PasswordValidationError as pe:
                    st.error(str(pe))
                except Exception as ex:
                    st.error(f"Error updating password: {ex}")

        st.markdown("---")
        st.markdown("#### Account Recovery Code")
        st.caption("A one-time emergency recovery code used to reset your password if forgotten.")

        if profile.get("has_recovery_code"):
            st.info("🟢 Recovery Code is configured for this account.")
        else:
            st.warning("⚠️ No recovery code configured yet.")

        if st.session_state.get("new_generated_recovery_code"):
            code = st.session_state["new_generated_recovery_code"]
            with st.container(border=True):
                st.success("New Recovery Code Generated:")
                st.code(code, language="text")
                st.caption("Save this immediately in a password manager. It will disappear on next refresh.")
                if st.button("I have saved this code", type="primary", key="dismiss_rec_btn"):
                    st.session_state.pop("new_generated_recovery_code", None)
                    st.rerun()
        else:
            if st.button("🔄 Generate New Recovery Code", help="Invalidates previous recovery code"):
                new_code = auth_service.regenerate_recovery_code()
                st.session_state["new_generated_recovery_code"] = new_code
                st.toast("New recovery code generated!", icon="🔑")
                st.rerun()

        st.markdown("---")
        st.markdown("#### Session Controls")
        sess_cols = st.columns(2)
        with sess_cols[0]:
            if st.button("🔒 Lock Workspace", use_container_width=True, type="secondary"):
                auth_service.lock_workspace()
                st.rerun()
        with sess_cols[1]:
            if st.button("🚪 Log Out of Account", use_container_width=True, type="primary"):
                auth_service.lock_workspace()
                st.session_state.clear()
                st.rerun()

    # -----------------------------------------------------------------------
    # Tab 4: Data & Backup
    # -----------------------------------------------------------------------
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

                import_mode = st.radio(
                    "Import Strategy",
                    ["merge", "replace"],
                    format_func=lambda x: "Merge (Safely add non-duplicate tasks)" if x == "merge" else "Replace (Erase existing tasks and projects first)",
                )

                if import_mode == "replace":
                    st.warning("⚠️ Warning: 'Replace' will permanently clear current tasks and projects before restoring.")

                if st.button("Start Backup Import", type="primary"):
                    res = backup_service.import_json_backup(payload, mode=import_mode)
                    st.success(f"Restore successful! Imported {res['tasks_imported']} tasks and {res['projects_imported']} projects.")
                    st.rerun()

            except Exception as e:
                st.error(f"Failed to read backup file: {e}")

        st.markdown("---")
        st.markdown("#### 🧹 Database Maintenance")
        maint_cols = st.columns(2)
        with maint_cols[0]:
            if st.button("🗑️ Empty Trash Bin", help="Permanently deletes all tasks currently in trash"):
                count = task_service.empty_trash_bin()
                st.toast(f"Emptied {count} deleted tasks from trash.", icon="🗑️")
                st.rerun()

        st.markdown("---")
        st.markdown("#### ⚠️ Danger Zone: Clear Workspace")
        st.caption("Permanently removes all tasks, projects, tags, and focus logs. Does not delete user accounts.")
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

    # -----------------------------------------------------------------------
    # Tab 5: About
    # -----------------------------------------------------------------------
    with tab_about:
        st.markdown("#### About TaskVault")
        cfg = load_config()
        db_type = "Local SQLite (Development)" if cfg.is_sqlite else "Managed PostgreSQL (Production)"
        st.write(f"**Version:** {cfg.version}")
        st.write(f"**Environment:** `{cfg.env}`")
        st.write(f"**Database Persistence:** {db_type}")
        st.write("**Security Architecture:** Argon2id password-gated access with persistent rate limiting.")
        st.write(f"**Active User:** `{profile.get('username', 'user')}` ({profile.get('email', '')})")

        st.markdown("---")
        st.markdown(
            """
            > **Security Notice:** The TaskVault password gate controls web application access to your private workspace.
            It does not replace hosting-level access controls or constitute end-to-end database encryption.
            Keep your deployment credentials and Streamlit account protected.
            """
        )
