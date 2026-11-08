"""
Focus Mode and Pomodoro Timer view for TaskVault.
Includes real-time interactive HTML5/CSS/JavaScript circular countdown timer with audio chime,
task linking, checklist execution, and persistent database session logging.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone, timedelta
import streamlit as st
import streamlit.components.v1 as components

from taskvault.ui.components import render_header
from taskvault.services import task_service, focus_service
from taskvault.models.base import utc_now


def get_pomodoro_html_widget(theme: str = "dark") -> str:
    """
    Returns a self-contained, real-time interactive HTML5/CSS/JS circular Pomodoro timer.
    Includes Web Audio API chime synthesis for distraction-free audio notification.
    """
    is_dark = theme != "light"
    bg_color = "#0F172A" if is_dark else "#F8FAFC"
    card_bg = "#1E293B" if is_dark else "#FFFFFF"
    text_primary = "#F8FAFC" if is_dark else "#0F172A"
    text_muted = "#94A3B8" if is_dark else "#64748B"
    border_color = "#334155" if is_dark else "#E2E8F0"
    ring_bg = "#334155" if is_dark else "#E2E8F0"

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <style>
            * {{
                box-sizing: border-box;
                margin: 0;
                padding: 0;
                user-select: none;
            }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                background-color: transparent;
                color: {text_primary};
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                padding: 10px;
            }}
            .timer-container {{
                background: {card_bg};
                border: 1px solid {border_color};
                border-radius: 16px;
                padding: 24px;
                display: flex;
                flex-direction: column;
                align-items: center;
                width: 100%;
                max-width: 440px;
                box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.2);
            }}
            /* Mode switcher buttons */
            .mode-switch {{
                display: flex;
                background: {'rgba(15, 23, 42, 0.6)' if is_dark else '#F1F5F9'};
                border-radius: 9999px;
                padding: 4px;
                gap: 4px;
                margin-bottom: 20px;
                border: 1px solid {border_color};
            }}
            .mode-btn {{
                background: transparent;
                border: none;
                color: {text_muted};
                padding: 6px 14px;
                font-size: 0.85rem;
                font-weight: 600;
                border-radius: 9999px;
                cursor: pointer;
                transition: all 0.2s ease;
            }}
            .mode-btn.active {{
                background: #3B82F6;
                color: #FFFFFF;
                box-shadow: 0 2px 8px rgba(59, 130, 246, 0.4);
            }}
            /* SVG Circular Ring */
            .circle-box {{
                position: relative;
                width: 220px;
                height: 220px;
                display: flex;
                align-items: center;
                justify-content: center;
            }}
            .circle-svg {{
                transform: rotate(-90deg);
                width: 220px;
                height: 220px;
            }}
            .circle-bg {{
                fill: none;
                stroke: {ring_bg};
                stroke-width: 8;
            }}
            .circle-progress {{
                fill: none;
                stroke: #3B82F6;
                stroke-width: 8;
                stroke-linecap: round;
                stroke-dasharray: 628;
                stroke-dashoffset: 0;
                transition: stroke-dashoffset 0.5s ease, stroke 0.3s ease;
            }}
            .time-display {{
                position: absolute;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
            }}
            .time-digits {{
                font-family: 'JetBrains Mono', monospace, -apple-system, sans-serif;
                font-size: 3.25rem;
                font-weight: 800;
                color: {text_primary};
                letter-spacing: -0.05em;
                line-height: 1;
            }}
            .status-text {{
                font-size: 0.75rem;
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: 0.1em;
                color: {text_muted};
                margin-top: 8px;
            }}
            /* Controls */
            .controls {{
                display: flex;
                align-items: center;
                gap: 12px;
                margin-top: 24px;
            }}
            .btn {{
                border: none;
                outline: none;
                cursor: pointer;
                border-radius: 10px;
                font-weight: 600;
                font-size: 0.95rem;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 10px 20px;
                transition: all 0.18s cubic-bezier(0.16, 1, 0.3, 1);
            }}
            .btn-primary {{
                background: #3B82F6;
                color: #FFFFFF;
                box-shadow: 0 4px 12px rgba(59, 130, 246, 0.35);
            }}
            .btn-primary:hover {{
                background: #2563EB;
                transform: translateY(-1px);
            }}
            .btn-secondary {{
                background: {'#334155' if is_dark else '#E2E8F0'};
                color: {text_primary};
            }}
            .btn-secondary:hover {{
                background: {'#475569' if is_dark else '#CBD5E1'};
                transform: translateY(-1px);
            }}
            .btn-sm {{
                padding: 8px 14px;
                font-size: 0.8rem;
            }}
            /* Stats bar */
            .stats-bar {{
                display: flex;
                align-items: center;
                justify-content: space-around;
                width: 100%;
                margin-top: 20px;
                padding-top: 16px;
                border-top: 1px solid {border_color};
            }}
            .stat-item {{
                text-align: center;
            }}
            .stat-val {{
                font-size: 1.15rem;
                font-weight: 700;
                color: #3B82F6;
            }}
            .stat-lbl {{
                font-size: 0.7rem;
                text-transform: uppercase;
                color: {text_muted};
                font-weight: 600;
                letter-spacing: 0.05em;
            }}
        </style>
    </head>
    <body>
        <div class="timer-container">
            <!-- Mode switch -->
            <div class="mode-switch">
                <button class="mode-btn active" id="btn-mode-focus" onclick="setMode('focus', 25, '#3B82F6')">🧠 Focus (25m)</button>
                <button class="mode-btn" id="btn-mode-short" onclick="setMode('short_break', 5, '#10B981')">☕ Short Break (5m)</button>
                <button class="mode-btn" id="btn-mode-long" onclick="setMode('long_break', 15, '#8B5CF6')">🌴 Long Break (15m)</button>
            </div>

            <!-- Animated SVG Ring -->
            <div class="circle-box">
                <svg class="circle-svg" viewBox="0 0 220 220">
                    <circle class="circle-bg" cx="110" cy="110" r="100"></circle>
                    <circle class="circle-progress" id="progress-ring" cx="110" cy="110" r="100"></circle>
                </svg>
                <div class="time-display">
                    <div class="time-digits" id="timer-display">25:00</div>
                    <div class="status-text" id="status-label">READY TO FOCUS</div>
                </div>
            </div>

            <!-- Control Buttons -->
            <div class="controls">
                <button class="btn btn-primary" id="start-btn" onclick="toggleTimer()">▶ Start</button>
                <button class="btn btn-secondary" onclick="resetTimer()">🔄 Reset</button>
                <button class="btn btn-secondary btn-sm" onclick="addFiveMinutes()">+5m</button>
            </div>

            <!-- Stats -->
            <div class="stats-bar">
                <div class="stat-item">
                    <div class="stat-val" id="completed-count">0</div>
                    <div class="stat-lbl">Sessions Completed</div>
                </div>
                <div class="stat-item">
                    <div class="stat-val" id="streak-indicator">🔥 Active</div>
                    <div class="stat-lbl">Focus State</div>
                </div>
            </div>
        </div>
    """ + """
        <script>
            const FULL_DASH_ARRAY = 628; // 2 * PI * 100
            let currentMode = 'focus';
            let totalSeconds = 25 * 60;
            let remainingSeconds = totalSeconds;
            let timerInterval = null;
            let isRunning = false;
            let completedSessions = 0;
            let activeColor = '#3B82F6';

            const displayEl = document.getElementById('timer-display');
            const statusEl = document.getElementById('status-label');
            const ringEl = document.getElementById('progress-ring');
            const startBtn = document.getElementById('start-btn');
            const completedCountEl = document.getElementById('completed-count');

            function updateDisplay() {
                const mins = Math.floor(remainingSeconds / 60);
                const secs = remainingSeconds % 60;
                displayEl.textContent = String(mins).padStart(2, '0') + ':' + String(secs).padStart(2, '0');

                // Update circle stroke
                const fraction = (totalSeconds - remainingSeconds) / totalSeconds;
                const offset = FULL_DASH_ARRAY * (1 - fraction);
                ringEl.style.strokeDashoffset = offset;
            }

            function playChime() {
                try {
                    const ctx = new (window.AudioContext || window.webkitAudioContext)();
                    const notes = [523.25, 659.25, 783.99, 1046.5]; // C5, E5, G5, C6 arpeggio
                    notes.forEach((freq, idx) => {
                        const osc = ctx.createOscillator();
                        const gain = ctx.createGain();
                        osc.type = 'sine';
                        osc.frequency.value = freq;
                        const start = ctx.currentTime + (idx * 0.12);
                        gain.gain.setValueAtTime(0.2, start);
                        gain.gain.exponentialRampToValueAtTime(0.001, start + 0.45);
                        osc.connect(gain);
                        gain.connect(ctx.destination);
                        osc.start(start);
                        osc.stop(start + 0.5);
                    });
                } catch(e) {
                    console.log('Web Audio play notice:', e);
                }
            }

            function setMode(mode, minutes, color) {
                currentMode = mode;
                totalSeconds = minutes * 60;
                remainingSeconds = totalSeconds;
                activeColor = color;
                ringEl.style.stroke = color;

                document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
                if (mode === 'focus') document.getElementById('btn-mode-focus').classList.add('active');
                if (mode === 'short_break') document.getElementById('btn-mode-short').classList.add('active');
                if (mode === 'long_break') document.getElementById('btn-mode-long').classList.add('active');

                pauseTimer();
                statusEl.textContent = mode === 'focus' ? 'READY TO FOCUS' : 'RELAX & BREATHE';
                updateDisplay();
            }

            function toggleTimer() {
                if (isRunning) {
                    pauseTimer();
                } else {
                    startTimer();
                }
            }

            function startTimer() {
                if (remainingSeconds <= 0) remainingSeconds = totalSeconds;
                isRunning = true;
                startBtn.textContent = '⏸ Pause';
                startBtn.style.background = '#F59E0B';
                statusEl.textContent = currentMode === 'focus' ? 'FOCUS IN PROGRESS...' : 'BREAK IN PROGRESS...';

                timerInterval = setInterval(() => {
                    remainingSeconds--;
                    updateDisplay();
                    if (remainingSeconds <= 0) {
                        clearInterval(timerInterval);
                        isRunning = false;
                        playChime();
                        if (currentMode === 'focus') {
                            completedSessions++;
                            completedCountEl.textContent = completedSessions;
                            statusEl.textContent = '🎉 SESSION COMPLETE!';
                        } else {
                            statusEl.textContent = '☕ BREAK FINISHED!';
                        }
                        startBtn.textContent = '▶ Start';
                        startBtn.style.background = activeColor;
                    }
                }, 1000);
            }

            function pauseTimer() {
                clearInterval(timerInterval);
                isRunning = false;
                startBtn.textContent = '▶ Start';
                startBtn.style.background = activeColor;
                if (remainingSeconds > 0 && remainingSeconds < totalSeconds) {
                    statusEl.textContent = 'PAUSED';
                }
            }

            function resetTimer() {
                pauseTimer();
                remainingSeconds = totalSeconds;
                statusEl.textContent = currentMode === 'focus' ? 'READY TO FOCUS' : 'READY FOR BREAK';
                updateDisplay();
            }

            function addFiveMinutes() {
                totalSeconds += 5 * 60;
                remainingSeconds += 5 * 60;
                updateDisplay();
            }

            updateDisplay();
        </script>
    </body>
    </html>
    """


def render_focus_view(settings: dict) -> None:
    tz_name = settings.get("timezone", "America/New_York")
    theme = settings.get("theme", "dark")
    render_header("⏱️ Focus Mode & Pomodoro", "Distraction-free deep work with real-time audio chime countdown")

    # Fetch active tasks for selection
    active_tasks = task_service.query_tasks_filtered(
        status="todo",
        is_archived=False,
        in_trash=False,
        exclude_subtasks=True,
    )

    task_choices = [("", "No Specific Task (General Focus)")] + [(t.id, t.title) for t in active_tasks]

    # Layout: Interactive Real-time HTML5/JS Timer on left, Task Context & Logger on right
    col_timer, col_task = st.columns([0.55, 0.45])

    with col_timer:
        # Embed interactive HTML/JS Pomodoro widget
        html_code = get_pomodoro_html_widget(theme=theme)
        components.html(html_code, height=450)

    with col_task:
        st.markdown("#### 🎯 Focus Objective & Task Checklist")
        if "pomodoro_selected_task" not in st.session_state:
            st.session_state.pomodoro_selected_task = ""

        task_idx = [t[0] for t in task_choices].index(st.session_state.pomodoro_selected_task) if st.session_state.pomodoro_selected_task in [t[0] for t in task_choices] else 0
        selected_task_id = st.selectbox(
            "Link Focus to Task",
            options=[t[0] for t in task_choices],
            index=task_idx,
            format_func=lambda x: dict(task_choices).get(x, ""),
            key="foc_task_select_main",
        )
        st.session_state.pomodoro_selected_task = selected_task_id

        # If linked task selected, display task details & checklist
        if selected_task_id:
            task = task_service.get_task(selected_task_id)
            if task:
                with st.container(border=True):
                    st.markdown(f"**Task:** {task.title}")
                    if task.description:
                        st.caption(task.description)
                    if task.checklist_items:
                        st.markdown("**Checklist:**")
                        for item in task.checklist_items:
                            chk = st.checkbox(item.text, value=item.is_completed, key=f"foc_chk_{item.id}")
                            if chk != item.is_completed:
                                task_service.toggle_checklist_item_status(item.id, chk)
                                st.rerun()

                    # Quick complete task button
                    if st.button("Mark Task Done ✅", key=f"foc_done_btn_{task.id}"):
                        task_service.toggle_task_done(task.id, is_completed=True)
                        st.toast("Task marked completed!", icon="🎉")
                        st.rerun()

        # Quick Log Focus Session to Database
        st.markdown("##### 💾 Save Completed Focus to History")
        log_cols = st.columns([0.65, 0.35])
        with log_cols[0]:
            quick_mins = st.selectbox(
                "Focus Duration",
                [25, 50, 15, 30, 45, 60],
                format_func=lambda m: f"{m} Minutes",
                key="quick_focus_duration_select",
            )
        with log_cols[1]:
            st.write("")
            st.write("")
            if st.button("Log to DB ⏱️", use_container_width=True, type="primary"):
                dur_secs = quick_mins * 60
                focus_service.record_focus_session(
                    task_id=selected_task_id if selected_task_id else None,
                    started_at=utc_now() - timedelta(seconds=dur_secs),
                    ended_at=utc_now(),
                    duration_seconds=dur_secs,
                    session_type="focus",
                )
                st.toast(f"Logged {quick_mins}m focus session!", icon="✅")
                st.rerun()

    # Manual Duration Entry section
    st.markdown("---")
    with st.expander("⏱️ Log Manual Time to Any Task"):
        with st.form("manual_time_form_advanced", clear_on_submit=True):
            t_cols = st.columns([0.6, 0.4])
            with t_cols[0]:
                man_task = st.selectbox(
                    "Select Task",
                    options=[t[0] for t in task_choices if t[0]],
                    format_func=lambda x: dict(task_choices).get(x, ""),
                )
            with t_cols[1]:
                man_mins = st.number_input("Minutes Spent", min_value=1, max_value=600, value=30, step=5)
            log_btn = st.form_submit_button("Record Time in Database", type="primary")

            if log_btn and man_task:
                focus_service.record_focus_session(
                    task_id=man_task,
                    started_at=utc_now() - timedelta(minutes=man_mins),
                    ended_at=utc_now(),
                    duration_seconds=man_mins * 60,
                    session_type="focus",
                )
                st.toast(f"Logged {man_mins}m to task!", icon="✅")
                st.rerun()
