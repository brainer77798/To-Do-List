"""
Task creation, quick-add, and full editing forms.
"""

from __future__ import annotations

from datetime import datetime, date, time
from typing import Optional, List
import streamlit as st

from taskvault.models.task import Task
from taskvault.models.project import Project
from taskvault.models.tag import Tag
from taskvault.services import task_service, project_service
from taskvault.utils.dates import to_utc, to_local, get_zoneinfo


def render_quick_add(
    project_id: Optional[str] = None,
    planned_for_date: Optional[date] = None,
    default_priority: str = "medium",
    timezone_name: str = "America/New_York",
    key_prefix: str = "quick_add",
) -> None:
    """Renders a fast 1-line capture form."""
    with st.form(key=f"form_{key_prefix}", clear_on_submit=True):
        cols = st.columns([0.65, 0.20, 0.15])
        with cols[0]:
            title = st.text_input(
                "Task title",
                placeholder="What needs to be done? Press Enter to save...",
                label_visibility="collapsed",
                key=f"input_{key_prefix}",
            )
        with cols[1]:
            priority = st.selectbox(
                "Priority",
                options=["medium", "urgent", "high", "low"],
                index=["medium", "urgent", "high", "low"].index(default_priority) if default_priority in ["medium", "urgent", "high", "low"] else 0,
                format_func=lambda x: f"● {x.capitalize()}",
                label_visibility="collapsed",
                key=f"prio_{key_prefix}",
            )
        with cols[2]:
            submitted = st.form_submit_button("Add Task", use_container_width=True, type="primary")

        if submitted:
            if not title or not title.strip():
                st.warning("Please enter a task title.")
            else:
                task_service.create_quick_task(
                    title=title.strip(),
                    project_id=project_id,
                    priority=priority,
                    planned_for_date=planned_for_date,
                )
                st.toast("Task added!", icon="✅")
                st.rerun()


def render_task_edit_modal(
    task_id: str,
    timezone_name: str,
    projects: List[Project],
    all_tags: List[Tag],
) -> None:
    """Renders comprehensive modal/expander task editor."""
    task = task_service.get_task(task_id)
    if not task:
        st.session_state.pop("editing_task_id", None)
        return

    st.markdown("### ✏️ Edit Task Details")

    with st.form(key=f"edit_task_form_{task.id}"):
        title = st.text_input("Title *", value=task.title)
        description = st.text_area("Notes / Description", value=task.description or "", height=100)

        cols1 = st.columns(3)
        with cols1[0]:
            status_opts = ["todo", "in_progress", "done"]
            status_labels = {"todo": "To Do", "in_progress": "In Progress", "done": "Done"}
            status = st.selectbox(
                "Status",
                options=status_opts,
                index=status_opts.index(task.status) if task.status in status_opts else 0,
                format_func=lambda x: status_labels[x],
            )
        with cols1[1]:
            prio_opts = ["low", "medium", "high", "urgent"]
            priority = st.selectbox(
                "Priority",
                options=prio_opts,
                index=prio_opts.index(task.priority) if task.priority in prio_opts else 1,
                format_func=lambda x: x.capitalize(),
            )
        with cols1[2]:
            proj_choices = [("", "No Project (Inbox)")] + [(p.id, p.name) for p in projects]
            curr_proj = task.project_id or ""
            proj_idx = [p[0] for p in proj_choices].index(curr_proj) if curr_proj in [p[0] for p in proj_choices] else 0
            selected_proj = st.selectbox(
                "Project",
                options=[p[0] for p in proj_choices],
                index=proj_idx,
                format_func=lambda x: dict(proj_choices).get(x, "Inbox"),
            )

        cols2 = st.columns(3)
        with cols2[0]:
            local_due = to_local(task.due_at, timezone_name) if task.due_at else None
            due_date_val = local_due.date() if local_due else None
            enable_due = st.checkbox("Set Due Date", value=bool(task.due_at))
            due_date = st.date_input("Due Date", value=due_date_val or date.today(), disabled=not enable_due)

        with cols2[1]:
            has_time = bool(local_due and not task.due_date_only)
            enable_time = st.checkbox("Set Specific Time", value=has_time, disabled=not enable_due)
            due_time = st.time_input(
                "Due Time",
                value=local_due.time() if has_time and local_due else time(17, 0),
                disabled=not (enable_due and enable_time),
            )

        with cols2[2]:
            category = st.text_input("Category", value=task.category or "")

        cols3 = st.columns(2)
        with cols3[0]:
            est_mins = st.number_input("Estimated Minutes", min_value=0, max_value=1440, value=task.estimated_minutes or 0, step=15)
        with cols3[1]:
            act_mins = st.number_input("Actual Tracked Minutes", min_value=0, max_value=10000, value=task.actual_minutes or 0, step=15)

        # Tags input
        curr_tag_names = ", ".join(t.name for t in task.tags)
        tag_input = st.text_input("Tags (comma separated)", value=curr_tag_names)

        btn_cols = st.columns([0.4, 0.3, 0.3])
        with btn_cols[0]:
            save_clicked = st.form_submit_button("💾 Save Changes", type="primary", use_container_width=True)
        with btn_cols[1]:
            cancel_clicked = st.form_submit_button("Cancel", use_container_width=True)
        with btn_cols[2]:
            archive_clicked = st.form_submit_button("📦 Archive Task", use_container_width=True)

        if save_clicked:
            if not title.strip():
                st.error("Title cannot be empty.")
            else:
                due_utc: Optional[datetime] = None
                date_only = True
                if enable_due and due_date:
                    zi = get_zoneinfo(timezone_name)
                    if enable_time and due_time:
                        dt_local = datetime.combine(due_date, due_time).replace(tzinfo=zi)
                        date_only = False
                    else:
                        dt_local = datetime.combine(due_date, time(12, 0)).replace(tzinfo=zi)
                        date_only = True
                    due_utc = dt_local.astimezone(get_zoneinfo("UTC"))

                tag_list = [t.strip() for t in tag_input.split(",") if t.strip()]

                task_service.update_task_details(
                    task_id=task.id,
                    title=title.strip(),
                    description=description.strip() if description else None,
                    status=status,
                    priority=priority,
                    project_id=selected_proj if selected_proj else None,
                    category=category.strip() if category else None,
                    due_at=due_utc,
                    due_date_only=date_only,
                    estimated_minutes=est_mins if est_mins > 0 else None,
                    actual_minutes=act_mins,
                    tag_names=tag_list,
                )
                st.session_state.pop("editing_task_id", None)
                st.toast("Task updated!", icon="💾")
                st.rerun()

        elif cancel_clicked:
            st.session_state.pop("editing_task_id", None)
            st.rerun()

        elif archive_clicked:
            task_service.archive_task_item(task.id)
            st.session_state.pop("editing_task_id", None)
            st.toast("Task archived!", icon="📦")
            st.rerun()

    # Checklist management section outside main form
    st.markdown("---")
    st.markdown("#### ☑️ Checklist Items")
    if task.checklist_items:
        for item in task.checklist_items:
            chk_cols = st.columns([0.1, 0.75, 0.15])
            with chk_cols[0]:
                is_done = st.checkbox("", value=item.is_completed, key=f"item_chk_{item.id}", label_visibility="collapsed")
                if is_done != item.is_completed:
                    task_service.toggle_checklist_item_status(item.id, is_done)
                    st.rerun()
            with chk_cols[1]:
                text_st = "text-decoration: line-through; opacity: 0.6;" if item.is_completed else ""
                st.markdown(f"<span style='{text_st}'>{item.text}</span>", unsafe_allow_html=True)
            with chk_cols[2]:
                if st.button("❌", key=f"del_chk_{item.id}", help="Delete item"):
                    task_service.delete_checklist_item_by_id(item.id)
                    st.rerun()

    with st.form(key=f"add_chk_form_{task.id}", clear_on_submit=True):
        new_cols = st.columns([0.8, 0.2])
        with new_cols[0]:
            new_item_text = st.text_input("New item", placeholder="Add checklist step...", label_visibility="collapsed")
        with new_cols[1]:
            add_item_btn = st.form_submit_button("Add Step")
        if add_item_btn and new_item_text.strip():
            task_service.add_checklist_item_to_task(task.id, new_item_text.strip())
            st.rerun()

