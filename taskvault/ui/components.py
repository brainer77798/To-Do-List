"""
Reusable UI components for TaskVault.
"""

from __future__ import annotations

from typing import Optional, List, Dict, Any
import streamlit as st
from taskvault.utils.formatting import truncate_text
from taskvault.utils.dates import format_relative_due


def render_header(title: str, subtitle: Optional[str] = None) -> None:
    """Renders consistent page header with title and subtitle."""
    st.markdown(
        f"""
        <div style="margin-bottom: 1.25rem;">
            <h1 style="font-size: 1.85rem; font-weight: 700; margin: 0; padding: 0;">{title}</h1>
            {f'<p style="color: #94A3B8; margin-top: 0.25rem; font-size: 0.95rem;">{subtitle}</p>' if subtitle else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metric_card(col, label: str, value: Any, color: str = "#3B82F6") -> None:
    """Renders a refined metric card inside a streamlit column."""
    with col:
        st.markdown(
            f"""
            <div style="
                background-color: rgba(30, 41, 59, 0.7);
                border: 1px solid rgba(51, 65, 85, 0.8);
                border-radius: 8px;
                padding: 1rem;
                text-align: center;
                margin-bottom: 0.5rem;
            ">
                <div style="font-size: 2rem; font-weight: 700; color: {color}; line-height: 1.1;">{value}</div>
                <div style="font-size: 0.8rem; font-weight: 600; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.05em; margin-top: 0.35rem;">{label}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_empty_state(title: str, description: str, icon: str = "📝") -> None:
    """Renders an empty state placeholder."""
    st.markdown(
        f"""
        <div style="
            text-align: center;
            padding: 2.5rem 1rem;
            border: 1px dashed rgba(71, 85, 105, 0.6);
            border-radius: 8px;
            margin: 1.5rem 0;
            background-color: rgba(15, 23, 42, 0.4);
        ">
            <div style="font-size: 2.2rem; margin-bottom: 0.5rem;">{icon}</div>
            <div style="font-size: 1.1rem; font-weight: 600; color: #E2E8F0;">{title}</div>
            <div style="font-size: 0.9rem; color: #94A3B8; max-width: 400px; margin: 0.35rem auto 0 auto;">{description}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

