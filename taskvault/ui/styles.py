"""
Custom CSS styles for TaskVault.
Clean, modern, premium styling adhering to Section 2.1 & 2.3.
"""

from __future__ import annotations


def get_custom_css(theme: str = "dark") -> str:
    """
    Returns custom CSS for visual polish and theme alignment.
    Safe, stable selectors that don't depend on fragile Streamlit internals.
    """
    is_dark = theme != "light"

    bg_card = "#1E293B" if is_dark else "#FFFFFF"
    border_color = "#334155" if is_dark else "#E2E8F0"
    text_muted = "#94A3B8" if is_dark else "#64748B"
    text_primary = "#F8FAFC" if is_dark else "#0F172A"

    return f"""
    <style>
    /* TaskVault Global Polish */
    .tv-header {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 1.5rem;
    }}
    .tv-title {{
        font-size: 1.75rem;
        font-weight: 700;
        color: {text_primary};
        margin: 0;
        letter-spacing: -0.02em;
    }}
    .tv-subtitle {{
        font-size: 0.95rem;
        color: {text_muted};
        margin-top: 0.25rem;
    }}

    /* Card Containers */
    .tv-card {{
        background-color: {bg_card};
        border: 1px solid {border_color};
        border-radius: 8px;
        padding: 1rem 1.25rem;
        margin-bottom: 0.75rem;
    }}

    /* Metric Card */
    .tv-metric-card {{
        background-color: {bg_card};
        border: 1px solid {border_color};
        border-radius: 8px;
        padding: 1.1rem;
        text-align: center;
    }}
    .tv-metric-value {{
        font-size: 2rem;
        font-weight: 700;
        line-height: 1.2;
        color: {text_primary};
    }}
    .tv-metric-label {{
        font-size: 0.85rem;
        font-weight: 500;
        color: {text_muted};
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-top: 0.25rem;
    }}

    /* Badges */
    .tv-badge {{
        display: inline-block;
        padding: 0.2rem 0.6rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.03em;
    }}
    .tv-badge-urgent {{
        background-color: rgba(239, 68, 68, 0.2);
        color: #EF4444;
        border: 1px solid rgba(239, 68, 68, 0.4);
    }}
    .tv-badge-high {{
        background-color: rgba(249, 115, 22, 0.2);
        color: #F97316;
        border: 1px solid rgba(249, 115, 22, 0.4);
    }}
    .tv-badge-medium {{
        background-color: rgba(59, 130, 246, 0.2);
        color: #3B82F6;
        border: 1px solid rgba(59, 130, 246, 0.4);
    }}
    .tv-badge-low {{
        background-color: rgba(100, 116, 139, 0.2);
        color: #94A3B8;
        border: 1px solid rgba(100, 116, 139, 0.4);
    }}

    .tv-badge-overdue {{
        background-color: rgba(239, 68, 68, 0.2);
        color: #EF4444;
        border: 1px solid rgba(239, 68, 68, 0.4);
    }}
    .tv-badge-today {{
        background-color: rgba(245, 158, 11, 0.2);
        color: #F59E0B;
        border: 1px solid rgba(245, 158, 11, 0.4);
    }}
    .tv-badge-done {{
        background-color: rgba(16, 185, 129, 0.2);
        color: #10B981;
        border: 1px solid rgba(16, 185, 129, 0.4);
    }}

    /* Hide default header anchor links */
    .stApp a:first-child {{
        text-decoration: none;
    }}
    </style>
    """

