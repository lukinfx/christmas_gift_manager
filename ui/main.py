import html

import streamlit as st

import auth
import db
import rules
from ui import extras, helpers, lists, styles


def _header(user: dict, days: int) -> None:
    left, right = st.columns([5, 1], vertical_alignment="center")
    with left:
        if days == 0:
            count = "🎅 Merry Christmas!"
        else:
            count = f"🎅 {days} day{'s' if days != 1 else ''} to Christmas"
        st.markdown(
            f"""<div class="hero">
                <div><h1>🎄 Christmas Gift Manager</h1>
                <div class="sub">Welcome, {html.escape(user['display_name'])}!</div></div>
                <div class="count">{count}</div>
            </div>""",
            unsafe_allow_html=True,
        )
    with right:
        with st.popover(user["display_name"], icon=":material/account_circle:", width="stretch"):
            picture = auth.google_picture()
            if picture:
                st.image(picture, width=64)
            st.caption("Signed in as")
            st.write(f"**{user['display_name']}**")
            if st.button("Log out", width="stretch", icon=":material/logout:"):
                auth.log_out()
                st.rerun()


def render() -> None:
    styles.inject()
    helpers.show_flash()
    user = auth.current_user()
    username = user["username"]
    today = helpers.today()

    _header(user, rules.days_until_christmas(today))

    all_lists = db.get_all_lists()
    years_with_lists = sorted({l["year"] for l in all_lists}, reverse=True)
    years = sorted(set(years_with_lists) | {today.year}, reverse=True)
    year = st.segmented_control(
        "Year",
        years,
        default=rules.default_year(years_with_lists, today.year),
        required=True,
        key="year",
    )
    lists_in_year = [l for l in all_lists if l["year"] == year and not l.get("archived")]

    # opening a list from another year would be confusing: close it when the year changes
    open_id = st.session_state.get("open_list")
    if open_id and not any(l["id"] == open_id for l in lists_in_year):
        st.session_state.pop("open_list", None)

    # ---- "new since last visit" ----
    since = rules.parse_ts(user.get("last_seen_at"))
    if since is None:  # first ever visit: start counting from now, nothing is "new" yet
        db.touch_last_seen(username)
    lists_by_id = {l["id"]: l for l in all_lists}
    visible = rules.visible_events(db.get_recent_events(), lists_by_id, username)
    new = rules.new_events(visible, since, username)
    new_by_list = rules.count_by_list(new)
    if new:
        st.info(
            f"🔔 **{len(new)} new update{'s' if len(new) != 1 else ''}** since your last visit. "
            "Open the **Activity** tab to see them."
        )

    # Tab labels stay fixed on purpose: changing a label would reset the selected tab.
    tab_lists, tab_buy, tab_activity = st.tabs(
        ["🎁 Lists", "🛒 My purchases", "📰 Activity"], key="main_tab", on_change="rerun"
    )
    with tab_lists:
        if tab_lists.open:
            lists.render(lists_in_year, all_lists, year, today.year, user, new_by_list)
    with tab_buy:
        if tab_buy.open:
            extras.purchases(lists_in_year, username)
    with tab_activity:
        if tab_activity.open:
            # remember what was new when the tab was opened, so the NEW markers survive the rerun below
            cutoff = st.session_state.setdefault("activity_cutoff", since)
            year_lists = {l["id"]: l for l in lists_in_year}
            extras.activity(visible, year_lists, cutoff, username)
            if new:  # viewing the feed = seen it: reset the counter
                db.touch_last_seen(username)
                st.rerun()
        else:
            st.session_state.pop("activity_cutoff", None)
