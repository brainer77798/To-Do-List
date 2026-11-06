"""
Tags and Categories Management view for TaskVault.
Fulfills Section 5.9: create, rename, delete tags with duplicate prevention,
task counts, and category filtering.
"""

from __future__ import annotations

import streamlit as st

from taskvault.ui.components import render_header, render_empty_state
from taskvault.ui.task_cards import render_task_card
from taskvault.services import task_service
from taskvault.repositories import tag_repository
from taskvault.database import get_db_session


def render_tags_view(settings: dict) -> None:
    tz_name = settings.get("timezone", "America/New_York")
    render_header("🏷️ Tags & Categories", "Organize labels, inspect usage, and filter by topic")

    tab_tags, tab_tasks = st.tabs(["🏷️ Tag Manager", "🔍 Filter by Tag"])

    with get_db_session() as db:
        tags_with_counts = tag_repository.get_tags_with_counts(db)

    # Tab 1: Tag Manager
    with tab_tags:
        # Create Tag Form
        with st.expander("➕ Create New Tag", expanded=False):
            with st.form("create_tag_form", clear_on_submit=True):
                new_tag_name = st.text_input("Tag Name", placeholder="e.g. backend, urgent, reading")
                create_btn = st.form_submit_button("Create Tag", type="primary")

                if create_btn:
                    if not new_tag_name or not new_tag_name.strip():
                        st.error("Tag name cannot be empty.")
                    else:
                        with get_db_session() as db:
                            created = tag_repository.get_or_create_tags(db, [new_tag_name.strip()])
                        st.toast(f"Tag #{created[0].name} created!", icon="🏷️")
                        st.rerun()

        st.markdown("#### Existing Tags")
        if not tags_with_counts:
            render_empty_state("No tags created yet", "Add tags above or attach them to tasks to see them listed here.", "🏷️")
        else:
            for item in tags_with_counts:
                with st.container(border=True):
                    cols = st.columns([0.45, 0.25, 0.15, 0.15])
                    with cols[0]:
                        st.markdown(f"**#{item['name']}**")
                        st.caption(f"Normalized: `{item['normalized_name']}`")
                    with cols[1]:
                        st.write(f"**{item['count']}** active tasks")

                    # Rename
                    with cols[2]:
                        with st.popover("✏️ Rename"):
                            rename_val = st.text_input("New Name", value=item["name"], key=f"ren_input_{item['id']}")
                            if st.button("Save", key=f"ren_btn_{item['id']}"):
                                try:
                                    with get_db_session() as db:
                                        tag_repository.rename_tag(db, item["id"], rename_val)
                                    st.toast("Tag renamed!", icon="✏️")
                                    st.rerun()
                                except ValueError as ve:
                                    st.error(str(ve))

                    # Delete
                    with cols[3]:
                        if st.button("🗑️", key=f"del_tag_{item['id']}", help="Delete Tag"):
                            with get_db_session() as db:
                                tag_repository.delete_tag(db, item["id"])
                            st.toast(f"Deleted tag #{item['name']}", icon="🗑️")
                            st.rerun()

    # Tab 2: Filter by Tag
    with tab_tasks:
        if not tags_with_counts:
            st.info("Create tags first to filter tasks by tag.")
        else:
            tag_choices = [(t["id"], f"#{t['name']} ({t['count']} tasks)") for t in tags_with_counts]
            selected_tag_id = st.selectbox(
                "Select Tag to Filter",
                options=[t[0] for t in tag_choices],
                format_func=lambda x: dict(tag_choices).get(x, ""),
                key="tag_filter_select",
            )

            if selected_tag_id:
                tagged_tasks = task_service.query_tasks_filtered(
                    tag_id=selected_tag_id,
                    is_archived=False,
                    in_trash=False,
                    exclude_subtasks=True,
                )
                if not tagged_tasks:
                    render_empty_state("No active tasks with this tag", "Tasks with this tag will appear here.", "🏷️")
                else:
                    st.write(f"Showing **{len(tagged_tasks)}** tasks tagged with this label")
                    for t in tagged_tasks:
                        render_task_card(t, tz_name, key_prefix="tag_view_list")
