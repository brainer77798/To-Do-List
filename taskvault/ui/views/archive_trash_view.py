"""
Archive and Trash views for TaskVault.
"""

from __future__ import annotations

import streamlit as st

from taskvault.ui.components import render_header, render_empty_state
from taskvault.services import task_service
from taskvault.utils.dates import to_local


def render_archive_trash_view(settings: dict) -> None:
    tz_name = settings.get("timezone", "America/New_York")
    render_header("📦 Archive & Trash", "Manage archived and deleted items")

    tab1, tab2 = st.tabs(["📦 Archive", "🗑️ Trash"])

    # Tab 1: Archive
    with tab1:
        archived_tasks = task_service.query_tasks_filtered(
            is_archived=True,
            in_trash=False,
            exclude_subtasks=True,
        )

        if not archived_tasks:
            render_empty_state("Archive is empty", "Archived tasks are preserved here out of your daily view.", "📦")
        else:
            st.write(f"**{len(archived_tasks)} archived tasks**")
            for t in archived_tasks:
                with st.container(border=True):
                    cols = st.columns([0.7, 0.15, 0.15])
                    with cols[0]:
                        st.markdown(f"**{t.title}**")
                        if t.project:
                            st.caption(f"📁 {t.project.name}")
                    with cols[1]:
                        if st.button("↺ Restore", key=f"arch_rest_{t.id}"):
                            task_service.restore_task_item(t.id)
                            st.toast("Restored to active tasks!", icon="↺")
                            st.rerun()
                    with cols[2]:
                        if st.button("❌ Delete", key=f"arch_perm_del_{t.id}"):
                            task_service.permanently_delete_task_item(t.id)
                            st.toast("Permanently deleted", icon="❌")
                            st.rerun()

    # Tab 2: Trash
    with tab2:
        trashed_tasks = task_service.query_tasks_filtered(
            in_trash=True,
            exclude_subtasks=False,
        )

        if not trashed_tasks:
            render_empty_state("Trash is empty", "Deleted items appear here before permanent removal.", "🗑️")
        else:
            t_cols = st.columns([0.7, 0.3])
            with t_cols[0]:
                st.write(f"**{len(trashed_tasks)} items in Trash**")
            with t_cols[1]:
                if st.button("⚠️ Empty Trash", type="primary", use_container_width=True):
                    st.session_state.confirm_empty_trash = True

            if st.session_state.get("confirm_empty_trash"):
                with st.container(border=True):
                    st.error("Are you sure you want to permanently delete all items in Trash? This cannot be undone.")
                    c_cols = st.columns(2)
                    if c_cols[0].button("Yes, Empty Trash Now", type="primary"):
                        count = task_service.empty_trash_bin()
                        st.session_state.confirm_empty_trash = False
                        st.toast(f"Deleted {count} tasks permanently.", icon="🗑️")
                        st.rerun()
                    if c_cols[1].button("Cancel"):
                        st.session_state.confirm_empty_trash = False
                        st.rerun()

            for t in trashed_tasks:
                with st.container(border=True):
                    cols = st.columns([0.7, 0.15, 0.15])
                    with cols[0]:
                        st.markdown(f"**{t.title}**")
                        if t.deleted_at:
                            del_local = to_local(t.deleted_at, tz_name)
                            if del_local:
                                st.caption(f"Deleted on {del_local.strftime('%b %d, %Y')}")
                    with cols[1]:
                        if st.button("↺ Restore", key=f"trash_rest_{t.id}"):
                            task_service.restore_task_item(t.id)
                            st.toast("Restored from Trash!", icon="↺")
                            st.rerun()
                    with cols[2]:
                        if st.button("❌ Purge", key=f"trash_perm_{t.id}"):
                            task_service.permanently_delete_task_item(t.id)
                            st.toast("Task permanently purged", icon="❌")
                            st.rerun()

