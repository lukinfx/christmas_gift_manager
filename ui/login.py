import streamlit as st

import auth


def render() -> None:
    """Legacy username/password form (used until Google login is configured)."""
    st.title("🎄 Christmas Gift Manager")
    st.subheader("Login")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            user = auth.authenticate(username, password)
            if user:
                auth.log_in(user)
                st.rerun()
            else:
                st.error("Invalid username or password")


def render_google() -> None:
    st.title("🎄 Christmas Gift Manager")
    st.write("Sign in with your Google account to see your family's gift lists.")
    st.button("Sign in with Google", type="primary", on_click=st.login)


def render_unauthorized(email: str) -> None:
    st.title("🎄 Christmas Gift Manager")
    st.error(f"**{email}** isn't on the family list yet. Ask Lukas to add your email address.")
    st.button("Sign out and try another account", on_click=st.logout)
