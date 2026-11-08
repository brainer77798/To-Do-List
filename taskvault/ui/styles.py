"""
Custom CSS styles for TaskVault.
Clean, modern, premium styling adhering to Section 2.1 & 2.3 of the build spec.
Features sleek glassmorphism, glowing badges, refined typography, and smooth transitions.
"""

from __future__ import annotations


def get_custom_css(theme: str = "dark") -> str:
    """
    Returns custom CSS for visual polish and theme alignment.
    Safe, stable styling that elevates the Streamlit interface.
    """
    is_dark = theme != "light"

    bg_main = "#0F172A" if is_dark else "#F8FAFC"
    bg_card = "rgba(30, 41, 59, 0.75)" if is_dark else "rgba(255, 255, 255, 0.95)"
    bg_card_hover = "rgba(39, 53, 76, 0.9)" if is_dark else "rgba(241, 245, 249, 1)"
    border_color = "rgba(51, 65, 85, 0.8)" if is_dark else "rgba(226, 232, 240, 0.9)"
    border_accent = "#3B82F6"
    text_muted = "#94A3B8" if is_dark else "#64748B"
    text_primary = "#F8FAFC" if is_dark else "#0F172A"
    shadow_card = "0 4px 12px -2px rgba(0, 0, 0, 0.35)" if is_dark else "0 4px 12px -2px rgba(0, 0, 0, 0.08)"
    shadow_hover = "0 8px 24px -4px rgba(59, 130, 246, 0.25)" if is_dark else "0 8px 24px -4px rgba(0, 0, 0, 0.12)"

    return f"""
    <style>
    /* -------------------------------------------------------------
       TaskVault Custom Global Theme & Typography
       ------------------------------------------------------------- */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

    html, body, [class*="css"] {{
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }}

    code, kbd, samp, pre {{
        font-family: 'JetBrains Mono', monospace !important;
    }}

    /* Sleek Custom Scrollbars */
    ::-webkit-scrollbar {{
        width: 7px;
        height: 7px;
    }}
    ::-webkit-scrollbar-track {{
        background: {'#0B1120' if is_dark else '#F1F5F9'};
    }}
    ::-webkit-scrollbar-thumb {{
        background: {'#334155' if is_dark else '#CBD5E1'};
        border-radius: 9999px;
    }}
    ::-webkit-scrollbar-thumb:hover {{
        background: {'#475569' if is_dark else '#94A3B8'};
    }}

    /* Header styling */
    .tv-header {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 1.5rem;
    }}
    .tv-title {{
        font-size: 1.85rem;
        font-weight: 800;
        color: {text_primary};
        margin: 0;
        letter-spacing: -0.03em;
        line-height: 1.2;
    }}
    .tv-subtitle {{
        font-size: 0.95rem;
        color: {text_muted};
        margin-top: 0.3rem;
        font-weight: 400;
    }}

    /* Card Containers with Glassmorphism & Hover transitions */
    .tv-card {{
        background: {bg_card};
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid {border_color};
        border-radius: 10px;
        padding: 1.15rem 1.35rem;
        margin-bottom: 0.75rem;
        box-shadow: {shadow_card};
        transition: transform 0.18s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.18s ease, border-color 0.18s ease;
    }}
    .tv-card:hover {{
        transform: translateY(-2px);
        box-shadow: {shadow_hover};
        border-color: rgba(59, 130, 246, 0.5);
    }}

    /* Metric Cards */
    .tv-metric-card {{
        background: {bg_card};
        backdrop-filter: blur(10px);
        border: 1px solid {border_color};
        border-radius: 10px;
        padding: 1.25rem 1rem;
        text-align: center;
        box-shadow: {shadow_card};
        transition: all 0.2s ease;
        position: relative;
        overflow: hidden;
    }}
    .tv-metric-card:hover {{
        transform: translateY(-3px);
        box-shadow: {shadow_hover};
        border-color: {border_accent};
    }}
    .tv-metric-value {{
        font-size: 2.25rem;
        font-weight: 800;
        line-height: 1.1;
        color: {text_primary};
        letter-spacing: -0.04em;
    }}
    .tv-metric-label {{
        font-size: 0.8rem;
        font-weight: 600;
        color: {text_muted};
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-top: 0.45rem;
    }}

    /* Badge Pills with Glow */
    .tv-badge {{
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        padding: 0.25rem 0.65rem;
        border-radius: 9999px;
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        transition: all 0.15s ease;
    }}
    .tv-badge-urgent {{
        background-color: rgba(239, 68, 68, 0.18);
        color: #F87171;
        border: 1px solid rgba(239, 68, 68, 0.5);
        box-shadow: 0 0 10px -2px rgba(239, 68, 68, 0.3);
    }}
    .tv-badge-high {{
        background-color: rgba(249, 115, 22, 0.18);
        color: #FB923C;
        border: 1px solid rgba(249, 115, 22, 0.5);
        box-shadow: 0 0 10px -2px rgba(249, 115, 22, 0.25);
    }}
    .tv-badge-medium {{
        background-color: rgba(59, 130, 246, 0.18);
        color: #60A5FA;
        border: 1px solid rgba(59, 130, 246, 0.5);
        box-shadow: 0 0 10px -2px rgba(59, 130, 246, 0.25);
    }}
    .tv-badge-low {{
        background-color: rgba(100, 116, 139, 0.18);
        color: #94A3B8;
        border: 1px solid rgba(100, 116, 139, 0.4);
    }}

    .tv-badge-overdue {{
        background-color: rgba(239, 68, 68, 0.2);
        color: #EF4444;
        border: 1px solid rgba(239, 68, 68, 0.5);
        animation: tv-pulse-subtle 2s infinite;
    }}
    .tv-badge-today {{
        background-color: rgba(245, 158, 11, 0.2);
        color: #FBBF24;
        border: 1px solid rgba(245, 158, 11, 0.5);
    }}
    .tv-badge-done {{
        background-color: rgba(16, 185, 129, 0.2);
        color: #34D399;
        border: 1px solid rgba(16, 185, 129, 0.5);
    }}

    @keyframes tv-pulse-subtle {{
        0%, 100% {{ opacity: 1; }}
        50% {{ opacity: 0.75; }}
    }}

    /* Streamlit Containers Border Polish */
    [data-testid="stVerticalBlockBorderWrapper"] {{
        background: {bg_card} !important;
        backdrop-filter: blur(10px) !important;
        border: 1px solid {border_color} !important;
        border-radius: 10px !important;
        box-shadow: {shadow_card} !important;
        transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
    }}
    [data-testid="stVerticalBlockBorderWrapper"]:hover {{
        border-color: rgba(59, 130, 246, 0.4) !important;
    }}

    /* Sidebar Clean Style */
    [data-testid="stSidebar"] {{
        border-right: 1px solid {border_color} !important;
        background-color: {'#0B1120' if is_dark else '#F8FAFC'} !important;
    }}

    /* Hide default header anchor links */
    .stApp a:first-child {{
        text-decoration: none;
    }}
    </style>
    """
