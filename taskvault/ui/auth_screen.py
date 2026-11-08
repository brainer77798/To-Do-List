"""
Authentication portal UI for TaskVault:
- Log In (Username or Email + Password)
- Create Account (Username, Email, Full Name, Password, Confirm Password)
- Forgot Password (Username or Email, Recovery Code, New Password Reset)
Strictly isolates unauthenticated sessions from private task/project content.
"""

from __future__ import annotations

import streamlit as st

from taskvault.services import auth_service
from taskvault.services.auth_service import AccountValidationError
from taskvault.security.passwords import PasswordValidationError
from taskvault.security.rate_limit import RateLimitExceededError
from taskvault.config import PRODUCT_NAME


POPULAR_TIMEZONES = [
    "America/New_York",
    "America/Chicago",
    "America/Denver",
    "America/Los_Angeles",
    "America/Toronto",
    "Europe/London",
    "Europe/Paris",
    "Europe/Berlin",
    "Asia/Tokyo",
    "Asia/Singapore",
    "Asia/Kolkata",
    "Australia/Sydney",
    "UTC",
]


def render_auth_portal(default_tab: str = "login") -> None:
    """
    Renders full authentication portal with Log In, Create Account, and Forgot Password tabs.
    """
    # Header Branding
    st.markdown(
        f"""
        <div style="max-width: 520px; margin: 2rem auto 1.25rem auto; text-align: center;">
            <div style="font-size: 2.75rem; margin-bottom: 0.25rem;">🔒</div>
            <h1 style="font-size: 2rem; font-weight: 800; margin: 0; letter-spacing: -0.03em;">{PRODUCT_NAME}</h1>
            <p style="color: #94A3B8; font-size: 0.95rem; margin-top: 0.35rem;">
                Private, password-protected task manager secured with Argon2id
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # If a recovery code was newly generated, show the modal/warning
    if st.session_state.get("auth_new_recovery_code"):
        code = st.session_state["auth_new_recovery_code"]
        msg = st.session_state.get("auth_success_msg", "Account ready!")
        st.markdown(
            f"""
            <div style="max-width: 520px; margin: 0 auto 1.5rem auto;">
            """,
            unsafe_allow_html=True,
        )
        with st.container(border=True):
            st.success(f"✅ {msg}")
            st.warning("⚠️ **Important: Save Your Recovery Code**")
            st.write(
                "If you ever forget your password, this one-time code is the **only** way "
                "to reset your password and restore access to your private tasks."
            )
            st.code(code, language="text")
            st.caption("Store this in a secure password manager. It will not be shown again.")
            if st.button("Proceed to To-Do List ▶", type="primary", use_container_width=True, key="proceed_to_vault_btn"):
                st.session_state.pop("auth_new_recovery_code", None)
                st.session_state.pop("auth_success_msg", None)
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        return

    # Container with tabs
    container_cols = st.columns([0.15, 0.7, 0.15])
    with container_cols[1]:
        with st.container(border=True):
            tab_login, tab_register, tab_forgot = st.tabs(["🔑 Log In", "✨ Create Account", "🔄 Forgot Password"])

            # ---------------------------------------------------------------
            # Tab 1: Log In
            # ---------------------------------------------------------------
            with tab_login:
                st.markdown("##### Sign in to your workspace")
                with st.form("login_form"):
                    identifier = st.text_input(
                        "Username or Email",
                        placeholder="e.g. alex or alex@example.com",
                        key="login_user_input",
                    )
                    password = st.text_input(
                        "Password",
                        type="password",
                        placeholder="Enter your password",
                        key="login_pass_input",
                    )
                    login_btn = st.form_submit_button(
                        "Log In to TaskVault",
                        type="primary",
                        use_container_width=True,
                    )

                    if login_btn:
                        if not identifier.strip():
                            st.error("Please enter your username or email.")
                        elif not password:
                            st.error("Please enter your password.")
                        else:
                            try:
                                res = auth_service.login_user(identifier, password)
                                if res.get("success"):
                                    st.toast("Authenticated successfully!", icon="🔓")
                                    st.rerun()
                                else:
                                    st.error(res.get("error", "Invalid credentials."))
                            except RateLimitExceededError as rle:
                                st.error(
                                    f"Too many failed login attempts. Workspace locked for security. "
                                    f"Please try again in {rle.retry_after_seconds} seconds."
                                )
                            except Exception as ex:
                                st.error(f"Login error: {ex}")

            # ---------------------------------------------------------------
            # Tab 2: Create Account
            # ---------------------------------------------------------------
            with tab_register:
                st.markdown("##### Create your private account")
                with st.form("register_form"):
                    reg_username = st.text_input(
                        "Username *",
                        placeholder="e.g. alex_dev (3-30 letters, numbers, _)",
                        key="reg_user_input",
                    )
                    reg_email = st.text_input(
                        "Email Address *",
                        placeholder="e.g. alex@example.com",
                        key="reg_email_input",
                    )
                    reg_fullname = st.text_input(
                        "Full Name (Optional)",
                        placeholder="e.g. Alex Mercer",
                        key="reg_name_input",
                    )

                    cols_pw = st.columns(2)
                    with cols_pw[0]:
                        reg_password = st.text_input(
                            "Password (min 12 chars) *",
                            type="password",
                            placeholder="Strong master password",
                            key="reg_pass_input",
                        )
                    with cols_pw[1]:
                        reg_confirm = st.text_input(
                            "Confirm Password *",
                            type="password",
                            placeholder="Re-type password",
                            key="reg_confirm_input",
                        )

                    reg_tz = st.selectbox(
                        "Preferred Timezone",
                        options=POPULAR_TIMEZONES,
                        index=0,
                        key="reg_tz_select",
                    )

                    register_btn = st.form_submit_button(
                        "Create Account & Get Started",
                        type="primary",
                        use_container_width=True,
                    )

                    if register_btn:
                        try:
                            res = auth_service.register_user(
                                username=reg_username,
                                email=reg_email,
                                password=reg_password,
                                confirm_password=reg_confirm,
                                full_name=reg_fullname if reg_fullname.strip() else None,
                                timezone=reg_tz,
                            )
                            if res.get("success"):
                                st.session_state["auth_new_recovery_code"] = res["recovery_code"]
                                st.session_state["auth_success_msg"] = f"Account created for {res['username']}!"
                                st.rerun()
                        except (AccountValidationError, PasswordValidationError) as ve:
                            st.error(str(ve))
                        except Exception as ex:
                            st.error(f"Registration error: {ex}")

            # ---------------------------------------------------------------
            # Tab 3: Forgot Password
            # ---------------------------------------------------------------
            with tab_forgot:
                st.markdown("##### Reset password using recovery code")
                st.caption("Enter your username or email and the recovery code generated when creating your account.")
                with st.form("forgot_password_form"):
                    f_identifier = st.text_input(
                        "Username or Email",
                        placeholder="Enter username or email",
                        key="forgot_id_input",
                    )
                    f_code = st.text_input(
                        "Recovery Code (XXXX-XXXX-XXXX-XXXX)",
                        placeholder="e.g. A1B2-C3D4-E5F6-G7H8",
                        key="forgot_code_input",
                    )

                    cols_fpw = st.columns(2)
                    with cols_fpw[0]:
                        f_new_pw = st.text_input(
                            "New Password (min 12 chars)",
                            type="password",
                            key="forgot_new_pass_input",
                        )
                    with cols_fpw[1]:
                        f_conf_pw = st.text_input(
                            "Confirm New Password",
                            type="password",
                            key="forgot_conf_pass_input",
                        )

                    reset_btn = st.form_submit_button(
                        "Reset Password & Enter Workspace",
                        type="primary",
                        use_container_width=True,
                    )

                    if reset_btn:
                        try:
                            res = auth_service.forgot_password_reset(
                                username_or_email=f_identifier,
                                recovery_code=f_code,
                                new_password=f_new_pw,
                                confirm_password=f_conf_pw,
                            )
                            if res.get("success"):
                                if res.get("recovery_code"):
                                    st.session_state["auth_new_recovery_code"] = res["recovery_code"]
                                    st.session_state["auth_success_msg"] = "Password successfully reset!"
                                    st.rerun()
                                else:
                                    st.toast("Password reset! Entering workspace...", icon="🔓")
                                    st.rerun()
                            else:
                                st.error(res.get("error", "Unable to reset password."))
                        except PasswordValidationError as pe:
                            st.error(str(pe))
                        except RateLimitExceededError as rle:
                            st.error(
                                f"Rate limited: Please wait {rle.retry_after_seconds} seconds before trying again."
                            )
                        except Exception as ex:
                            st.error(f"Reset error: {ex}")


def render_first_run_setup() -> None:
    """Renders setup screen on first run (renders auth portal with register focus)."""
    render_auth_portal(default_tab="register")


def render_unlock_screen() -> None:
    """Renders unlock screen when session is locked or unauthenticated."""
    render_auth_portal(default_tab="login")
