import streamlit as st

import auth
from ui import login, main


def run() -> None:
    """Called on every Streamlit rerun by streamlit_app.py."""
    st.set_page_config(page_title="Christmas Gift Manager", page_icon="🎄", layout="wide")

    if auth.google_enabled():
        if not auth.google_logged_in():
            login.render_google()
        elif auth.current_user() is None:
            login.render_unauthorized(auth.google_email())
        else:
            main.render()
    elif auth.current_user():
        main.render()
    else:
        login.render()
