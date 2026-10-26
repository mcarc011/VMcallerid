"""Streamlit login restoration and acknowledged browser-cookie updates."""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import extra_streamlit_components as stx
import streamlit as st

from auth_sessions import COOKIE_NAME, DEFAULT_SESSION_DAYS, LoginSessions


def sessions():
    config = st.secrets.get("auth", {})
    # Existing deployments already have this server-only API secret. A separate
    # cookie_secret may be configured without changing the existing user table.
    secret = config.get("cookie_secret") or st.secrets.get("CALLER_ID_API_KEY")
    return LoginSessions(secret, config.get("session_days", DEFAULT_SESSION_DAYS))


def users():
    return st.secrets.get("users", {})


def begin_login(username):
    st.session_state["_auth_pending"] = {
        "id": uuid4().hex,
        "token": sessions().issue(username, users()),
    }


def begin_logout():
    # Drop cached call data immediately; never restore the old cookie while its
    # asynchronous deletion is still in progress.
    st.session_state.clear()
    st.session_state["_auth_pending"] = {"id": uuid4().hex, "token": None}


def restore_login():
    manager = stx.CookieManager(key="auth_cookie_init")
    pending = st.session_state.get("_auth_pending")
    if pending:
        token = pending["token"]
        if token is None:
            acknowledged = manager.cookie_manager(
                method="delete", cookie=COOKIE_NAME,
                key="auth_delete_" + pending["id"], default=None,
            )
        else:
            expires = datetime.now(timezone.utc) + timedelta(seconds=sessions().max_age)
            acknowledged = manager.cookie_manager(
                method="set", cookie=COOKIE_NAME, value=token,
                options={"path": "/", "expires": expires.isoformat(),
                         "secure": True, "sameSite": "strict"},
                key="auth_set_" + pending["id"], default=None,
            )
        if acknowledged is not True:
            st.info("Finishing sign-in…" if token else "Signing out…")
            st.stop()
        st.session_state.pop("_auth_pending")
        if token:
            st.session_state["_auth_token"] = token
        st.rerun()

    token = st.session_state.get("_auth_token")
    if token is None:
        read_id = st.session_state.setdefault("_auth_read_id", uuid4().hex)
        # None means the component has not answered yet; {} means no cookies.
        # CookieManager.get_all() uses {} for both, causing a login-page flash.
        cookies = manager.cookie_manager(
            method="getAll", key="auth_read_" + read_id, default=None,
        )
        if cookies is None:
            st.info("Restoring sign-in…")
            st.stop()
        token = cookies.get(COOKIE_NAME) if isinstance(cookies, dict) else None

    username = sessions().verify(token, users())
    st.session_state["authenticated"] = username is not None
    if username:
        st.session_state["_auth_token"] = token
        st.session_state["username"] = username
    else:
        st.session_state.pop("_auth_token", None)
        st.session_state.pop("username", None)


def require_current_login():
    """Also enforce expiry/removal during independently scheduled fragments."""
    if not sessions().verify(st.session_state.get("_auth_token"), users()):
        begin_logout()
        st.rerun(scope="app")
