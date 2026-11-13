from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import streamlit as st

import auth
import rules

CURRENCY = "Kč"

# status -> (label template, badge colour, icon)
STATUS = {
    "available": ("Available", "green", ":material/check_circle:"),
    "want_to_buy": ("Reserved by {who}", "orange", ":material/bookmark:"),
    "want_to_buy_shared": ("Split: {who}", "blue", ":material/group:"),
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
    if status == "want_to_buy_shared":
        who = ", ".join(display_name(p) for p in rules.split_participants(gift)) or "someone"
    elif status == "bought":
        who = display_name(gift.get("bought_by"))
    else:
        who = display_name(gift.get("interested_buyer"))
    st.badge(template.format(who=who), icon=icon, color=color)


def split_caption(gift: dict) -> None:
    """'2 people · 500 Kč each' under a split gift."""
    people = rules.split_participants(gift)
    if gift.get("status") != "want_to_buy_shared" or not people:
        return
    text = f"{len(people)} {'person' if len(people) == 1 else 'people'} splitting"
    if gift.get("price") is not None:
        text += f" · {money(gift['price'] / len(people))} each"
    st.caption(text)


def go_to(year: int, list_id: int | None = None) -> None:
    """Ask the page to switch to a year (and open a list) on the next run.
    Applied by apply_go_to() before the year selector exists: a widget's value can't be
    set from inside a dialog once the widget is on the page."""
    st.session_state["_goto"] = {"year": year, "list_id": list_id}


def apply_go_to() -> None:
    target = st.session_state.pop("_goto", None)
    if not target:
        return
    st.session_state["year"] = target["year"]
    if target["list_id"] is not None:
        st.session_state["open_list"] = target["list_id"]
    else:
        st.session_state.pop("open_list", None)


def flash(message: str, icon: str = "✅") -> None:
    """Show a toast after the next rerun."""
    st.session_state["_flash"] = (message, icon)


def show_flash() -> None:
    item = st.session_state.pop("_flash", None)
    if item:
        st.toast(item[0], icon=item[1])
