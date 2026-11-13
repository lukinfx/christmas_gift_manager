"""Authentication.

Two modes, chosen automatically:
  * Google mode  - when an [auth] section exists in Streamlit secrets. Uses st.login();
                   the Google email is mapped to a username via the `app_users` table.
  * Legacy mode  - users.json + password (fallback until Google is configured).
"""
import json
from pathlib import Path

import streamlit as st

import db
import rules

USERS_FILE = Path(__file__).parent / "users.json"


def google_enabled() -> bool:
    try:
        return "auth" in st.secrets
    except Exception:  # no secrets file at all
        return False


# ---------- user directory ----------

@st.cache_data
def _load_users_file() -> list[dict]:
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)["users"]


def load_users() -> list[dict]:
    """All family members (username, display_name, ...)."""
    return db.get_app_users() if google_enabled() else _load_users_file()


# ---------- legacy password login ----------

def authenticate(username: str, password: str) -> dict | None:
    for user in _load_users_file():
        if user["username"] == username and user["password"] == password:
            return user
    return None


def log_in(user: dict) -> None:
    st.session_state.user = user


# ---------- Google login ----------

def google_logged_in() -> bool:
    return bool(st.user.get("is_logged_in", False))


def google_email() -> str:
    return (st.user.get("email") or "").strip().lower()


def google_picture() -> str | None:
    if google_enabled() and google_logged_in():
        return st.user.get("picture")
    return None


def _google_user() -> dict | None:
    """Map the verified Google email to an app user, or None if not on the guest list."""
    if not google_logged_in() or not st.user.get("email_verified", True):
        return None
    return rules.find_user_by_email(db.get_app_users(), google_email())


# ---------- shared ----------

def current_user() -> dict | None:
    if google_enabled():
        return _google_user()
    return st.session_state.get("user")


def log_out() -> None:
    if google_enabled():
        st.logout()
    else:
        st.session_state.user = None
