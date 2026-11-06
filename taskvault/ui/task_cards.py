"""
Task card and list row rendering components.
Clean, functional controls with no decorative mockups.
"""

from __future__ import annotations

from typing import Optional, Callable
import streamlit as st
from taskvault.models.task import Task
from taskvault.utils.dates import format_relative_due, is_overdue, is_due_today
from taskvault.services import task_service


PRIORITY_COLORS = {
    "urgent": "#EF4444",
    "high": "#F97316",
    "medium": "#3B82F6",
    "low": "#94A3B8",
}


def render_task_card(
    task: Task,
    timezone_name: str,
    key_prefix: str = "",
    on_edit_click: Optional[Callable[[Task], None]] = None,
    show_project: bool = True,
    allow_selection: bool = False,
    is_selected: bool = False,
) -> bool:
    """
    Renders an interactive task card with complete functionality:
    - Checkbox toggle for complete/reopen
    - Priority and due-date badges
    - Subtask and checklist indicators
    - Action controls for edit, duplicate, and delete to trash
    Returns True if selected in selection mode.
    """
    card_key = f"{key_prefix}_{task.id}"
    selected = False

    container = st.container(border=True)
    with container:
        cols = st.columns([0.08, 0.52, 0.22, 0.18])

        # Column 1: Complete toggle or select checkbox
        with cols[0]:
            if allow_selection:
                selected = st.checkbox("", value=is_selected, key=f"sel_{card_key}", label_visibility="collapsed")
            else:
                is_done = task.status == "done"
                if st.checkbox("", value=is_done, key=f"chk_{card_key}", label_visibility="collapsed"):
                    if not is_done:
                        task_service.toggle_task_done(task.id, is_completed=True)
                        st.rerun()
                else:
                    if is_done:
                        task_service.toggle_task_done(task.id, is_completed=False)
                        st.rerun()

        # Column 2: Title and Project / Tags / Subtask Info
        with cols[1]:
            title_style = "text-decoration: line-through; opacity: 0.6;" if task.status == "done" else "font-weight: 500;"
            st.markdown(f"<span style='{title_style} font-size: 1rem;'>{task.title}</span>", unsafe_allow_html=True)

            meta_items = []
            if show_project and task.project:
                meta_items.append(f"📁 <span style='color: {task.project.color or '#3B82F6'};'>{task.project.name}</span>")

            if task.tags:
                tag_strs = " ".join([f"<span style='background: rgba(100,116,139,0.2); padding: 1px 6px; border-radius: 4px; font-size: 0.75rem;'>#{t.name}</span>" for t in task.tags])
                meta_items.append(tag_strs)

            if task.checklist_items:
                done_items = sum(1 for c in task.checklist_items if c.is_completed)
                total_items = len(task.checklist_items)
                meta_items.append(f"☑ {done_items}/{total_items}")

            if task.subtasks:
                done_subs = sum(1 for s in task.subtasks if s.status == "done")
                meta_items.append(f"↳ {done_subs}/{len(task.subtasks)} subtasks")

            if meta_items:
                st.markdown(
                    f"<div style='font-size: 0.8rem; color: #94A3B8; margin-top: 2px;'>{' &bull; '.join(meta_items)}</div>",
                    unsafe_allow_html=True,
                )

        # Column 3: Priority & Due Date
        with cols[2]:
            p_color = PRIORITY_COLORS.get(task.priority, "#3B82F6")
            p_text = task.priority.capitalize()

            due_text = format_relative_due(task.due_at, timezone_name, task.due_date_only)
            due_color = "#94A3B8"
            if is_overdue(task.due_at, timezone_name, task.due_date_only) and task.status != "done":
                due_color = "#EF4444"
            elif is_due_today(task.due_at, timezone_name) and task.status != "done":
                due_color = "#F59E0B"

            st.markdown(
                f"""
                <div style='font-size: 0.8rem; line-height: 1.3;'>
                    <div><span style='color: {p_color}; font-weight: 600;'>●</span> {p_text}</div>
                    <div style='color: {due_color}; font-weight: 500;'>📅 {due_text}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Column 4: Quick Action Controls
        with cols[3]:
            btn_cols = st.columns(3)
            with btn_cols[0]:
                if st.button("✏️", key=f"edit_{card_key}", help="Edit Task"):
                    st.session_state[f"editing_task_id"] = task.id
                    st.rerun()

            with btn_cols[1]:
                if st.button("📋", key=f"dup_{card_key}", help="Duplicate"):
                    task_service.duplicate_task_item(task.id)
                    st.toast("Task duplicated", icon="📋")
                    st.rerun()

            with btn_cols[2]:
                if st.button("🗑️", key=f"del_{card_key}", help="Delete to Trash"):
                    task_service.soft_delete_task(task.id)
                    st.toast("Moved to Trash", icon="🗑️")
                    st.rerun()

    return selected

