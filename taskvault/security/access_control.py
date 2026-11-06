"""
Access control, session authorization state, and inactivity locking.
"""

from __future__ import annotations

import time
from typing import Callable, Any
from functools import wraps


class UnauthorizedAccessError(Exception):
    """Raised when an unauthorized or locked session attempts to access private data."""
    pass


class SessionManager:
    """
    Manages session-level unlock state, last activity tracking, and inactivity lockouts.
    Works seamlessly with Streamlit's session state.
    """
    KEY_IS_UNLOCKED = "_tv_unlocked"
    KEY_LAST_ACTIVITY = "_tv_last_activity"
    KEY_SESSION_ID = "_tv_session_id"

    @classmethod
    def get_session_state(cls) -> dict:
        """Safe retrieval of Streamlit's session state dictionary."""
        try:
            import streamlit as st
            return st.session_state
        except Exception:
            # Fallback for non-streamlit contexts (e.g. tests)
            if not hasattr(cls, "_fallback_state"):
                cls._fallback_state = {}
            return cls._fallback_state

    @classmethod
    def is_unlocked(cls, timeout_minutes: int = 10) -> bool:
        """
        Determines whether the current session is unlocked and has not timed out.
        If inactive beyond timeout_minutes, automatically locks the session.
        """
        state = cls.get_session_state()
        if not state.get(cls.KEY_IS_UNLOCKED, False):
            return False

        last_activity = state.get(cls.KEY_LAST_ACTIVITY)
        if last_activity is None:
            cls.lock()
            return False

        now = time.time()
        timeout_seconds = max(1, timeout_minutes) * 60
        if (now - last_activity) > timeout_seconds:
            cls.lock()
            return False

        return True

    @classmethod
    def touch_activity(cls) -> None:
        """
        Updates the last activity timestamp to prevent premature inactivity locking.
        """
        state = cls.get_session_state()
        state[cls.KEY_LAST_ACTIVITY] = time.time()

    @classmethod
    def unlock(cls) -> None:
        """
        Marks the current session as authenticated.
        """
        state = cls.get_session_state()
        state[cls.KEY_IS_UNLOCKED] = True
        state[cls.KEY_LAST_ACTIVITY] = time.time()

    @classmethod
    def lock(cls) -> None:
        """
        Locks the current session and purges transient sensitive data from session state.
        """
        state = cls.get_session_state()
        state[cls.KEY_IS_UNLOCKED] = False
        state[cls.KEY_LAST_ACTIVITY] = None
        # Purge any cached form data or sensitive keys
        keys_to_clear = [k for k in state.keys() if k.startswith("tv_private_")]
        for k in keys_to_clear:
            state.pop(k, None)


def require_auth(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Decorator for services to guarantee caller session is unlocked before executing
    data operations.
    """
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        # Check authorization
        if not SessionManager.is_unlocked():
            raise UnauthorizedAccessError("Access denied: Workspace is locked. Please unlock first.")
        # Refresh activity on valid authenticated service call
        SessionManager.touch_activity()
        return func(*args, **kwargs)
    return wrapper

