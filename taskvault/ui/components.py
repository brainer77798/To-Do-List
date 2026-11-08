"""
Reusable UI components for TaskVault.
Clean, functional HTML5 and CSS components with elevated aesthetics and smooth transitions.
"""

from __future__ import annotations

from typing import Optional, List, Dict, Any
import streamlit as st
from taskvault.utils.formatting import truncate_text
from taskvault.utils.dates import format_relative_due


def render_header(title: str, subtitle: Optional[str] = None) -> None:
    """Renders consistent, polished page header with title and subtitle."""
    st.markdown(
        f"""
        <div style="margin-bottom: 1.5rem;">
            <h1 style="font-size: 1.9rem; font-weight: 800; margin: 0; padding: 0; letter-spacing: -0.03em;">{title}</h1>
            {f'<p style="color: #94A3B8; margin-top: 0.35rem; font-size: 0.95rem; font-weight: 400;">{subtitle}</p>' if subtitle else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metric_card(col, label: str, value: Any, color: str = "#3B82F6") -> None:
    """Renders a refined metric card with glassmorphism and subtle gradient border."""
    with col:
        st.markdown(
            f"""
            <div style="
                background: linear-gradient(135deg, rgba(30, 41, 59, 0.85) 0%, rgba(15, 23, 42, 0.75) 100%);
                backdrop-filter: blur(12px);
                -webkit-backdrop-filter: blur(12px);
                border: 1px solid rgba(51, 65, 85, 0.8);
                border-top: 2px solid {color};
                border-radius: 12px;
                padding: 1.15rem 1rem;
                text-align: center;
                margin-bottom: 0.6rem;
                box-shadow: 0 4px 14px -2px rgba(0, 0, 0, 0.25);
                transition: transform 0.2s ease, box-shadow 0.2s ease;
            ">
                <div style="font-size: 2.15rem; font-weight: 800; color: {color}; line-height: 1.1; letter-spacing: -0.04em;">{value}</div>
                <div style="font-size: 0.78rem; font-weight: 700; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.08em; margin-top: 0.45rem;">{label}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_empty_state(title: str, description: str, icon: str = "📝") -> None:
    """Renders a modern, welcoming empty state placeholder."""
    st.markdown(
        f"""
        <div style="
            text-align: center;
            padding: 3rem 1.5rem;
            border: 1.5px dashed rgba(71, 85, 105, 0.6);
            border-radius: 12px;
            margin: 1.5rem 0;
            background: linear-gradient(180deg, rgba(30, 41, 59, 0.3) 0%, rgba(15, 23, 42, 0.45) 100%);
            backdrop-filter: blur(8px);
        ">
            <div style="font-size: 2.75rem; margin-bottom: 0.75rem;">{icon}</div>
            <div style="font-size: 1.15rem; font-weight: 700; color: #F1F5F9; letter-spacing: -0.01em;">{title}</div>
            <div style="font-size: 0.92rem; color: #94A3B8; max-width: 440px; margin: 0.45rem auto 0 auto; line-height: 1.5;">{description}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
