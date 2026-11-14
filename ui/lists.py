import html

import streamlit as st

import db
import rules
from ui import dialogs, helpers


def _gift_by_id(list_id: int, gift_id: int) -> dict | None:
    return next((g for g in db.get_gifts_by_list().get(list_id, []) if g["id"] == gift_id), None)


def _list_by_id(list_id: int) -> dict | None:
    return next((l for l in db.get_all_lists() if l["id"] == list_id), None)


# ---------------------------------------------------------------- the list (information only)

def _row(gift_list: dict, gift: dict, username: str, n_comments: int) -> None:
    """One gift as a compact row. Nothing to do here but read it: clicking the name opens the modal."""
    show_private = rules.can_see_status(gift_list, username)
    # The key gives the row a CSS class ("st-key-gift_row_<id>"). The button at the end is stretched
    # invisibly over the whole row by ui/styles.py, so a tap anywhere on the row opens the modal.
    with st.container(key=f"gift_row_{gift['id']}", border=True, horizontal=True, vertical_alignment="center"):
        if gift.get("image_url"):
            st.image(gift["image_url"], width=72)
        with st.container(gap="xsmall"):
            st.markdown(f"<div class='gift-title'>{html.escape(gift['name'])}</div>", unsafe_allow_html=True)
            line = helpers.info_md(gift, show_private)
            if line:
                st.markdown(line)
            extra = f"Added by {helpers.md_escape(helpers.display_name(gift['added_by']))}"
            if show_private and n_comments:
                extra += f"  ·  :material/chat_bubble: {n_comments}"
            st.caption(extra)
        if st.button(helpers.md_escape(gift["name"]), key=f"open_gift_{gift['id']}", type="tertiary"):
            _open_gift(gift_list["id"], gift, username)


# ---------------------------------------------------------------- the modal (details + actions)

def _open_gift(list_id: int, gift: dict, username: str) -> None:
    # a fresh modal always starts on "Details", with no half-finished delete confirmation
    st.session_state.pop(f"gift_section_{gift['id']}", None)
    st.session_state.pop(f"confirm_delete_{gift['id']}", None)
    # on_dismiss="rerun": closing the modal refreshes the list behind it
    st.dialog(gift["name"], width="medium", on_dismiss="rerun")(_gift_modal)(list_id, gift["id"], username)


def _gift_modal(list_id: int, gift_id: int, username: str) -> None:
    """Runs as a fragment: buttons inside only refresh the modal, and it re-reads the gift every time."""
    gift = _gift_by_id(list_id, gift_id)
    gift_list = _list_by_id(list_id)
    if gift is None or gift_list is None:
        st.info("This gift is no longer in this list.")
        return

    show_private = rules.can_see_status(gift_list, username)
    can_edit = rules.can_edit_gift(gift, username)
    can_move = rules.can_move_gift(gift, username, gift_list["year"], helpers.today().year)
    sections = ["Details"]
    if show_private:
        sections.append("Comments")
    if can_edit:
        sections.append("Edit")
    if can_move:
        sections.append("Move")

    key = f"gift_section_{gift_id}"
    pending = st.session_state.pop(f"_pending_{key}", None)  # set by a section that wants to switch
    if pending in sections:
        st.session_state[key] = pending
    if st.session_state.get(key) not in sections:
        st.session_state.pop(key, None)
    # the default applies only the first time, otherwise Streamlit warns about conflicting values
    section = st.segmented_control(
        "Section", sections, key=key, required=True, label_visibility="collapsed",
        default="Details" if key not in st.session_state else None,
    )

    def back_to_details() -> None:
        st.session_state[f"_pending_{key}"] = "Details"
        st.rerun(scope="fragment")

    if section == "Details":
        _details(gift, gift_list, username, show_private)
    elif section == "Comments":
        dialogs.comments_panel(gift, username)
    elif section == "Edit":
        dialogs.edit_form(gift, username, on_saved=back_to_details)
        dialogs.delete_section(gift, username)
    elif section == "Move":
        dialogs.move_form(gift, username)


def _details(gift: dict, gift_list: dict, username: str, show_private: bool) -> None:
    if gift.get("image_url"):
        st.image(gift["image_url"], width="stretch")
    if gift.get("description"):
        st.write(gift["description"])
    line = helpers.info_md(gift, show_private)
    if line:
        st.markdown(line)
    if show_private:
        helpers.split_caption(gift)
    st.caption(f"Added by {helpers.md_escape(helpers.display_name(gift['added_by']))}")
    if gift.get("url"):
        st.link_button("Open in shop", gift["url"], icon=":material/open_in_new:", width="stretch")
    if show_private:
        st.divider()
        _actions(gift, username)


def _actions(gift: dict, username: str) -> None:
    gid = gift["id"]
    status = gift.get("status") or "available"

    if status == "available":
        # a horizontal container stays one row on a phone (st.columns would stack them)
        with st.container(horizontal=True):
            if st.button("Reserve", key=f"res_{gid}", width="stretch", help="I want to buy this"):
                db.update_gift_status(gid, "want_to_buy", username)
                st.rerun(scope="fragment")
            if st.button("Split", key=f"split_{gid}", width="stretch", help="Share the cost equally with others"):
                db.join_split(gid, username)
                st.rerun(scope="fragment")
            if st.button("Bought", key=f"bought_{gid}", width="stretch", help="Already bought"):
                db.update_gift_status(gid, "bought", username)
                st.rerun(scope="fragment")
        return

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


# ---------------------------------------------------------------- one list of gifts

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

    gifts = rules.visible_gifts(gift_list, db.get_gifts_by_list().get(gift_list["id"], []), username)
    if not gifts:
        st.write("No gifts in this list yet.")
        return
    st.caption("Tap a gift for details and actions.")
    comments = db.get_comments_by_gift()
    for gift in gifts:
        _row(gift_list, gift, username, len(comments.get(gift["id"], [])))


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
