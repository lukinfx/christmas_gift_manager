"""'My purchases' and 'Activity' tabs."""
import html

import streamlit as st

import db
import rules
from ui import helpers

EVENT_TEXT = {
    "gift_added": ("added", ":material/add_circle:"),
    "want_to_buy": ("reserved", ":material/bookmark:"),
    "want_to_buy_shared": ("offered to split", ":material/group:"),
    "bought": ("bought", ":material/shopping_bag:"),
    "gift_moved": ("moved", ":material/drive_file_move:"),
    "split_joined": ("joined the split for", ":material/group_add:"),
    "split_left": ("left the split for", ":material/group_remove:"),
    "released": ("released", ":material/undo:"),
    "comment": ("commented on", ":material/chat_bubble:"),
}


def purchases(lists_in_year: list[dict], username: str) -> None:
    summary = rules.purchase_summary(lists_in_year, db.get_gifts_by_list(), username)
    if not summary:
        st.info("You haven't reserved or bought anything this year yet.")
        return

    everything = [g for block in summary for g in block["gifts"]]
    totals = rules.money_totals(everything, username)
    c1, c2, c3 = st.columns(3)
    c1.metric("Reserved", helpers.money(totals["reserved"]) or f"0 {helpers.CURRENCY}", border=True)
    c2.metric("Bought", helpers.money(totals["bought"]) or f"0 {helpers.CURRENCY}", border=True)
    c3.metric("Total", helpers.money(totals["reserved"] + totals["bought"]) or f"0 {helpers.CURRENCY}", border=True)
    if totals["unpriced"]:
        st.caption(f"{totals['unpriced']} gift(s) have no price and aren't counted in the totals.")

    for block in summary:
        gift_list = block["list"]
        st.markdown(f"#### 🎁 {gift_list['name']}")
        st.caption("For " + ", ".join(helpers.display_name(r) for r in gift_list["recipients"]))
        for gift in block["gifts"]:
            with st.container(border=True):
                name_col, price_col, status_col = st.columns([3, 1, 2], vertical_alignment="center")
                name_col.markdown(f"**{gift['name']}**")
                share = rules.my_share(gift, username)
                price_col.write(helpers.money(share) or "–")
                people = rules.split_participants(gift)
                if len(people) > 1 and gift.get("price") is not None:
                    price_col.caption(f"{helpers.money(gift['price'])} ÷ {len(people)}")
                with status_col:
                    helpers.status_badge(gift)


def activity(events: list[dict], lists_by_id: dict[int, dict], cutoff, username: str) -> None:
    """`events` are already filtered for what this user may see; `cutoff` marks the NEW ones."""
    events = [e for e in events if e["list_id"] in lists_by_id][:50]
    if not events:
        st.info("No activity yet. It shows up here as the family adds, reserves and buys gifts.")
        return
    for ev in events:
        verb, icon = EVENT_TEXT.get(ev["kind"], (ev["kind"], ":material/info:"))
        gift_list = lists_by_id[ev["list_id"]]
        ts = rules.parse_ts(ev["created_at"])
        is_new = cutoff is not None and ts is not None and ts > cutoff and ev["actor"] != username
        tag = "<span class='newtag'>NEW</span>" if is_new else ""
        who = html.escape(helpers.display_name(ev["actor"]))
        gift = html.escape(ev.get("gift_name") or "a gift")
        where = html.escape(gift_list["name"])
        st.markdown(
            f"{tag}{icon} <b>{who}</b> {verb} <b>{gift}</b> {'into' if ev['kind'] == 'gift_moved' else 'in'} {where} "
            f"<span class='muted'>· {helpers.ago(ev['created_at'])}</span>",
            unsafe_allow_html=True,
        )
