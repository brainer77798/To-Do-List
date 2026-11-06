"""
First-run setup and workspace unlock screen UI.
Strictly isolates unauthenticated sessions from private task/project content.
"""

from __future__ import annotations

import streamlit as st

from taskvault.services import auth_service
from taskvault.security.passwords import PasswordValidationError
from taskvault.security.rate_limit import RateLimitExceededError
from taskvault.config import PRODUCT_NAME


def render_first_run_setup() -> None:
    """Renders initial setup screen when no workspace password exists."""
    st.markdown(
        f"""
        <div style="max-width: 500px; margin: 3rem auto 1.5rem auto; text-align: center;">
            <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">🛡️</div>
            <h1 style="font-size: 2rem; font-weight: 800; margin: 0; letter-spacing: -0.02em;">Welcome to {PRODUCT_NAME}</h1>
            <p style="color: #94A3B8; font-size: 0.95rem; margin-top: 0.5rem;">
                Set up your private workspace password. Your tasks are protected behind a dedicated Argon2id security gate.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # If recovery code was just generated, show it with warning
    if st.session_state.get("setup_recovery_code"):
        code = st.session_state["setup_recovery_code"]
        st.success("✅ Workspace created successfully!")
        with st.container(border=True):
            st.warning("⚠️ **Important: Save Your Recovery Code**")
            st.write("If you forget your password, this one-time code is the only way to recover access without database administrative intervention.")
            st.code(code, language="text")
            st.caption("Store this in a secure password manager. It will not be shown again.")
            if st.button("Proceed to Workspace ▶", type="primary", use_container_width=True):
                st.session_state.pop("setup_recovery_code", None)
                st.rerun()
        return

    with st.container(border=True):
        with st.form("first_run_form"):
            st.markdown("#### Create Workspace Password")
            password = st.text_input("Master Password (min 12 characters)", type="password")
            confirm_password = st.text_input("Confirm Master Password", type="password")

            enable_recovery = st.checkbox("Generate a one-time recovery code", value=True)

            tz_choice = st.selectbox("Preferred Timezone", ["America/New_York", "America/Chicago", "America/Denver", "America/Los_Angeles", "Europe/London", "UTC"])

            submitted = st.form_submit_button("Create Private Workspace", type="primary", use_container_width=True)

            if submitted:
                try:
                    result = auth_service.setup_initial_workspace(
                        password=password,
                        confirm_password=confirm_password,
                        enable_recovery=enable_recovery,
                        timezone=tz_choice,
                    )
                    if result.get("recovery_code"):
                        st.session_state["setup_recovery_code"] = result["recovery_code"]
                        st.rerun()
                    else:
                        st.rerun()

                except PasswordValidationError as pe:
                    st.error(str(pe))
                except Exception as ex:
                    st.error(f"Setup error: {ex}")


def render_unlock_screen() -> None:
    """Renders the lock screen when workspace is locked."""
    st.markdown(
        f"""
        <div style="max-width: 440px; margin: 4rem auto 1.5rem auto; text-align: center;">
            <div style="font-size: 2.2rem; margin-bottom: 0.5rem;">🔒</div>
            <h1 style="font-size: 1.85rem; font-weight: 800; margin: 0; letter-spacing: -0.02em;">{PRODUCT_NAME} is Locked</h1>
            <p style="color: #94A3B8; font-size: 0.95rem; margin-top: 0.35rem;">
                Enter your master password to unlock your workspace.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        with st.form("unlock_form"):
            password = st.text_input("Password", type="password", placeholder="Enter master password...", label_visibility="collapsed")
            unlocked = st.form_submit_button("Unlock Workspace", type="primary", use_container_width=True)

            if unlocked:
                try:
                    success = auth_service.unlock_workspace(password)
                    if success:
                        st.rerun()
                    else:
                        st.error("Unable to unlock. Check your password or try again later.")
                except RateLimitExceededError as rle:
                    st.error(f"Too many failed unlock attempts. Workspace is locked for security. Please try again in {rle.retry_after_seconds} seconds.")
                except Exception as ex:
                    st.error("Unable to unlock. Check your password or try again later.")

        # Recovery code flow
        with st.expander("Forgot Password?"):
            st.caption("Use your one-time recovery code to set a new password.")
            with st.form("recovery_form"):
                rec_code = st.text_input("Recovery Code (XXXX-XXXX-XXXX-XXXX)")
                new_pw = st.text_input("New Password (min 12 characters)", type="password")
                conf_new_pw = st.text_input("Confirm New Password", type="password")
                recover_btn = st.form_submit_button("Recover & Reset Password")

                if recover_btn:
                    try:
                        ok = auth_service.recover_workspace(rec_code, new_pw, conf_new_pw)
                        if ok:
                            st.success("Workspace unlocked and new password configured!")
                            st.rerun()
                        else:
                            st.error("Invalid recovery code or unable to unlock.")
                    except PasswordValidationError as pe:
                        st.error(str(pe))
                    except RateLimitExceededError as rle:
                        st.error(f"Rate limited: Please wait {rle.retry_after_seconds} seconds.")
                    except Exception as ex:
                        st.error(f"Recovery failed: {ex}")

