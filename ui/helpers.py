from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import streamlit as st

import auth

CURRENCY = "Kč"

# status -> (label template, badge colour, icon)
STATUS = {
    "available": ("Available", "green", ":material/check_circle:"),
    "want_to_buy": ("Reserved by {who}", "orange", ":material/bookmark:"),
    "want_to_buy_shared": ("Split buy: {who}", "blue", ":material/group:"),
    "bought": ("Bought by {who}", "red", ":material/shopping_bag:"),
}


def today():
    try:
        return datetime.now(ZoneInfo("Europe/Prague")).date()
    except Exception:  # tz database missing
        return datetime.now(timezone.utc).date()


def names() -> dict[str, str]:
    return {u["username"]: u["display_name"] for u in auth.load_users()}


def display_name(username: str | None) -> str:
    if not username:
        return "someone"
    return names().get(username, username)


def money(value: float | None) -> str:
    if value is None:
        return ""
    text = f"{value:,.0f}" if float(value).is_integer() else f"{value:,.2f}"
    return f"{text.replace(',', ' ')} {CURRENCY}"


def ago(iso: str) -> str:
    try:
        then = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return ""
    seconds = int((datetime.now(timezone.utc) - then).total_seconds())
    if seconds < 60:
        return "just now"
    if seconds < 3600:
        return f"{seconds // 60} min ago"
    if seconds < 86400:
        return f"{seconds // 3600} h ago"
    if seconds < 7 * 86400:
        return f"{seconds // 86400} d ago"
    return then.strftime("%d %b %Y")


def status_badge(gift: dict) -> None:
    status = gift.get("status") or "available"
    template, color, icon = STATUS.get(status, STATUS["available"])
    who = gift.get("bought_by") if status == "bought" else gift.get("interested_buyer")
    st.badge(template.format(who=display_name(who)), icon=icon, color=color)


def flash(message: str, icon: str = "✅") -> None:
    """Show a toast after the next rerun."""
    st.session_state["_flash"] = (message, icon)


def show_flash() -> None:
    item = st.session_state.pop("_flash", None)
    if item:
        st.toast(item[0], icon=item[1])
