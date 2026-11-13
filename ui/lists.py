import html
from datetime import datetime, timezone

import streamlit as st

import db
import rules
from ui import dialogs, helpers

GRID = 3  # gift cards per row


def _gift_by_id(list_id: int, gift_id: int) -> dict | None:
    return next((g for g in db.get_gifts_by_list().get(list_id, []) if g["id"] == gift_id), None)


@st.fragment
def _gift_card(list_id: int, gift_id: int, username: str) -> None:
    """One gift. A fragment, so clicking a button only reruns this card, not the page."""
    gift = _gift_by_id(list_id, gift_id)
    gift_list = next((l for l in db.get_all_lists() if l["id"] == list_id), None)
    if gift is None or gift_list is None:
        return
    show_private = rules.can_see_status(gift_list, username)

    with st.container(border=True):
        if gift.get("image_url"):
            st.image(gift["image_url"], width="stretch")
        st.markdown(f"<div class='gift-title'>{html.escape(gift['name'])}</div>", unsafe_allow_html=True)
        if gift.get("description"):
            st.caption(gift["description"])

        if rules.is_recent(gift.get("created_at"), datetime.now(timezone.utc)):
            st.badge("New", icon=":material/fiber_new:", color="red")
        if gift.get("price") is not None:
            st.badge(helpers.money(gift["price"]), icon=":material/payments:", color="gray")
        if show_private:
            helpers.status_badge(gift)
            helpers.split_caption(gift)
        st.markdown(
            f"<span class='muted'>Added by {html.escape(helpers.display_name(gift['added_by']))}</span>",
            unsafe_allow_html=True,
        )

        if gift.get("url"):
            st.link_button("Open in shop", gift["url"], icon=":material/open_in_new:", width="stretch")

        if show_private:
            _actions(gift, username)

        if rules.can_edit_gift(gift, username):
            can_move = rules.can_move_gift(gift, username, gift_list["year"], helpers.today().year)
            cols = st.columns(3 if can_move else 2)  # no empty gap when Move isn't offered
            edit_col, delete_col = cols[0], cols[-1]
            if edit_col.button("Edit", key=f"edit_{gift_id}", icon=":material/edit:", width="stretch"):
                dialogs.edit_gift(gift, username)
            if can_move and cols[1].button(
                "Move", key=f"move_{gift_id}", icon=":material/drive_file_move:", width="stretch",
                help="Move to a list in another year",
            ):
                dialogs.move_gift(gift, username)
            # icon-only: a "Delete" label doesn't fit next to Edit and Move in a narrow card
            with delete_col.popover("", icon=":material/delete:", help="Delete this gift", width="stretch"):
                st.write("Delete this gift and its comments?")
                if st.button("Yes, delete", key=f"del_{gift_id}", type="primary", width="stretch"):
                    db.delete_gift(gift_id)
                    helpers.flash("Gift deleted", "🗑️")
                    st.rerun()


def _actions(gift: dict, username: str) -> None:
    gid = gift["id"]
    status = gift.get("status") or "available"

    if status == "available":
        a, b, c = st.columns(3)
        if a.button("Reserve", key=f"res_{gid}", width="stretch", help="I want to buy this"):
            db.update_gift_status(gid, "want_to_buy", username)
            st.rerun(scope="fragment")
        if b.button("Split", key=f"split_{gid}", width="stretch", help="Share the cost equally with others"):
            db.join_split(gid, username)
            st.rerun(scope="fragment")
        if c.button("Bought", key=f"bought_{gid}", width="stretch", help="Already bought"):
            db.update_gift_status(gid, "bought", username)
            st.rerun(scope="fragment")
    else:
        if rules.can_join_split(gift, username) and st.button(
            "Join split", key=f"join_{gid}", width="stretch", icon=":material/group_add:",
            help="Share the cost equally",
        ):
            db.join_split(gid, username)
            st.rerun(scope="fragment")
        if rules.can_mark_bought(gift, username) and st.button("Mark bought", key=f"bought_{gid}", width="stretch"):
            db.update_gift_status(gid, "bought", username)
            st.rerun(scope="fragment")
        if rules.can_leave_split(gift, username) and st.button(
            "Leave split", key=f"leave_{gid}", width="stretch", icon=":material/group_remove:"
        ):
            db.leave_split(gid, username)
            st.rerun(scope="fragment")
        if rules.can_release_gift(gift, username) and st.button(
            "Release", key=f"rel_{gid}", width="stretch", icon=":material/undo:"
        ):
            db.release_gift(gid, username)
            st.rerun(scope="fragment")

    n = len(db.get_comments_by_gift().get(gid, []))
    if st.button(f"Comments ({n})", key=f"cm_{gid}", width="stretch", icon=":material/chat_bubble:"):
        dialogs.comments(gift, username)


def _detail(gift_list: dict, username: str) -> None:
    if st.button("Back to all lists", icon=":material/arrow_back:"):
        st.session_state.pop("open_list", None)
        st.rerun()

    recipients = ", ".join(helpers.display_name(r) for r in gift_list["recipients"])
    top, add = st.columns([4, 1], vertical_alignment="center")
    top.subheader(f"🎁 {gift_list['name']}")
    top.caption(f"For {recipients} · {gift_list['year']}")
    if add.button("Add gift", type="primary", icon=":material/add:", width="stretch"):
        dialogs.add_gift(gift_list, username)

    if rules.is_recipient(gift_list, username):
        st.info("You're a recipient: you can add gifts you'd like, but you only see your own. The rest stays a surprise!")
    else:
        st.success("You can add gift ideas for the recipients and see everything, including who's buying what.")

    gifts = rules.visible_gifts(gift_list, db.get_gifts_by_list().get(gift_list["id"], []), username)
    if not gifts:
        st.write("No gifts in this list yet.")
        return
    for start in range(0, len(gifts), GRID):
        cols = st.columns(GRID)
        for col, gift in zip(cols, gifts[start:start + GRID]):
            with col:
                _gift_card(gift_list["id"], gift["id"], username)


def _overview(lists: list[dict], username: str, new_by_list: dict[int, int]) -> None:
    gifts_by_list = db.get_gifts_by_list()
    for start in range(0, len(lists), 2):
        cols = st.columns(2)
        for col, gift_list in zip(cols, lists[start:start + 2]):
            with col, st.container(border=True):
                st.markdown(f"#### 🎁 {gift_list['name']}")
                st.caption("For " + ", ".join(helpers.display_name(r) for r in gift_list["recipients"]))
                if new_by_list.get(gift_list["id"]):
                    st.badge(f"{new_by_list[gift_list['id']]} new", icon=":material/notifications:", color="red")
                visible = rules.visible_gifts(gift_list, gifts_by_list.get(gift_list["id"], []), username)
                if rules.is_recipient(gift_list, username):
                    st.write(f"{len(visible)} gift(s) you added")
                else:
                    bought = sum(1 for g in visible if g.get("status") == "bought")
                    st.write(f"{len(visible)} gift(s) · {bought} bought")
                if st.button("Open", key=f"open_{gift_list['id']}", width="stretch"):
                    st.session_state["open_list"] = gift_list["id"]
                    st.rerun()


def render(
    lists_in_year: list[dict],
    all_lists: list[dict],
    year: int,
    current_year: int,
    user: dict,
    new_by_list: dict[int, int],
) -> None:
    username = user["username"]
    open_id = st.session_state.get("open_list")
    selected = next((l for l in lists_in_year if l["id"] == open_id), None)
    if selected:
        _detail(selected, username)
        return

    new_col, year_col, _ = st.columns([1, 1.4, 4])
    if new_col.button("New list", type="primary", icon=":material/add:", width="stretch"):
        dialogs.new_list(username, year, current_year)
    if rules.is_admin(user) and year_col.button(
        "Start new year", icon=":material/event_repeat:", width="stretch", help="Admin: copy last year's lists"
    ):
        dialogs.start_new_year(user, all_lists, current_year)
    if not lists_in_year:
        st.info(f"No gift lists for {year} yet. Create one with the button above!")
        return
    _overview(lists_in_year, username, new_by_list)
