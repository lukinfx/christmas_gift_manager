import streamlit as st

import auth
import db
import rules

STATUS_BADGES = {
    "available": (st.success, "Available"),
    "want_to_buy": (st.warning, "Reserved by {who}"),
    "want_to_buy_shared": (st.info, "Shared buy by {who}"),
    "bought": (st.error, "Bought by {who}"),
}


def _sidebar(user: dict) -> None:
    with st.sidebar:
        st.write(f"Logged in as: **{user['display_name']}**")
        if st.button("Logout"):
            auth.log_out()
            st.rerun()

        st.divider()
        st.subheader("Create New Gift List")
        with st.form("create_list_form"):
            list_name = st.text_input("List Name")
            options = [u["username"] for u in auth.load_users()]
            recipients = st.multiselect("Recipients", options)
            if st.form_submit_button("Create List"):
                if list_name and recipients:
                    db.create_gift_list(list_name, recipients, user["username"])
                    st.success("List created!")
                    st.rerun()
                else:
                    st.error("Please fill all fields")


def _status_badge(gift: dict) -> None:
    status = gift.get("status", "available")
    render_fn, template = STATUS_BADGES.get(status, STATUS_BADGES["available"])
    who = gift.get("bought_by") if status == "bought" else gift.get("interested_buyer")
    render_fn(template.format(who=who or "someone"))


def _gift_row(gift: dict, gift_list: dict, username: str, comments: list[dict]) -> None:
    show_private = rules.can_see_status(gift_list, username)
    st.divider()
    col_info, col_status, col_delete = st.columns([3, 1, 0.5])

    with col_info:
        st.markdown(f"### {gift['name']}")
        if gift.get("description"):
            st.write(f"*{gift['description']}*")
        st.caption(f"Added by: {gift['added_by']}")

    with col_status:
        if show_private:
            _status_badge(gift)

    with col_delete:
        if rules.can_delete_gift(gift, username):
            if st.button("🗑️", key=f"delete_{gift['id']}", help="Delete this gift"):
                db.delete_gift(gift["id"])
                st.rerun()

    if not show_private:
        return

    b1, b2, b3 = st.columns(3)
    for col, label, status, prefix in (
        (b1, "Want to Buy", "want_to_buy", "buy"),
        (b2, "Buy Shared", "want_to_buy_shared", "shared"),
        (b3, "Mark Bought", "bought", "bought"),
    ):
        with col:
            if st.button(label, key=f"{prefix}_{gift['id']}", use_container_width=True):
                db.update_gift_status(gift["id"], status, username)
                st.rerun()

    st.markdown("**Comments:**")
    for c in comments:
        st.text(f"{c['username']} ({c['created_at'][:10]}): {c['comment']}")
    with st.form(f"comment_{gift['id']}"):
        new_comment = st.text_input("Add a comment", key=f"new_comment_{gift['id']}")
        if st.form_submit_button("Post Comment") and new_comment:
            db.add_comment(gift["id"], new_comment, username)
            st.rerun()


def _list_card(gift_list: dict, gifts: list[dict], comments_by_gift: dict, username: str) -> None:
    title = f"🎁 {gift_list['name']} (Recipients: {', '.join(gift_list['recipients'])})"
    with st.expander(title, expanded=False):
        if rules.is_recipient(gift_list, username):
            st.info("ℹ️ You're a recipient! You can add gifts you wish to receive, but you'll only see your own gifts.")
        else:
            st.success("✅ You can add gifts for the recipients and see all gifts to mark their status.")

        with st.form(f"add_gift_{gift_list['id']}"):
            st.write("**Add a Gift**")
            c1, c2 = st.columns([2, 1])
            name = c1.text_input("Gift Name", key=f"gift_name_{gift_list['id']}")
            desc = c2.text_input("Description (optional)", key=f"gift_desc_{gift_list['id']}")
            if st.form_submit_button("Add Gift"):
                if name:
                    db.add_gift(gift_list["id"], name, desc, username)
                    st.rerun()
                else:
                    st.error("Please enter a gift name")

        visible = rules.visible_gifts(gift_list, gifts, username)
        if not visible:
            st.write("No gifts in this list yet.")
        for gift in visible:
            _gift_row(gift, gift_list, username, comments_by_gift.get(gift["id"], []))


def render() -> None:
    user = auth.current_user()
    st.title(f"🎄 Christmas Gift Manager - Welcome {user['display_name']}!")
    _sidebar(user)

    lists = db.get_all_lists()
    if not lists:
        st.info("No gift lists yet. Create one using the sidebar!")
        return

    gifts_by_list = db.get_gifts_by_list()
    comments_by_gift = db.get_comments_by_gift()
    for gift_list in lists:
        _list_card(gift_list, gifts_by_list.get(gift_list["id"], []), comments_by_gift, user["username"])
