import html

import streamlit as st

import db
import rules
from ui import helpers


@st.dialog("New gift list")
def new_list(username: str, year: int, current_year: int) -> None:
    options = sorted({year, current_year, current_year + 1})
    all_users = helpers.names()
    with st.form("new_list_form", border=False):
        name = st.text_input("List name", placeholder="e.g. Presents for Jana")
        recipients = st.multiselect(
            "Who is it for?", list(all_users), format_func=lambda u: all_users[u]
        )
        list_year = st.selectbox("Year", options, index=options.index(year))
        if st.form_submit_button("Create list", type="primary", width="stretch"):
            if not name.strip() or not recipients:
                st.error("Please give the list a name and at least one recipient.")
            else:
                db.create_gift_list(name.strip(), recipients, username, list_year)
                helpers.flash("List created")
                st.rerun()


@st.dialog("Start a new year", width="large")
def start_new_year(user: dict, all_lists: list[dict], current_year: int) -> None:
    """Admin only: copy the list layout of a previous year as empty lists."""
    if not rules.is_admin(user):  # the button is hidden for others, but never trust the UI alone
        st.error("Only admins can do this.")
        return

    years = sorted({l["year"] for l in all_lists}, reverse=True)
    if not years:
        st.info("There are no lists to copy yet.")
        return

    c1, c2 = st.columns(2)
    source_year = c1.selectbox("Copy lists from", years)
    target_options = sorted({current_year, current_year + 1, source_year + 1})
    default_target = current_year if current_year != source_year else source_year + 1
    target_year = c2.selectbox("Create them in", target_options, index=target_options.index(default_target))
    if target_year == source_year:
        st.warning("Pick a different year to copy into.")
        return

    source = [l for l in all_lists if l["year"] == source_year]
    target = [l for l in all_lists if l["year"] == target_year]
    candidates = rules.lists_to_copy(source, target)
    skipped = len(source) - len(candidates)

    if not candidates:
        st.info(f"All of the {source_year} lists already exist in {target_year}.")
        return
    if skipped:
        st.caption(f"{skipped} list(s) already exist in {target_year} and are skipped.")

    by_id = {l["id"]: l for l in candidates}
    chosen = st.multiselect(
        "Lists to copy (gifts are not copied)",
        list(by_id),
        default=list(by_id),
        format_func=lambda i: f"{by_id[i]['name']}  ·  for "
        + ", ".join(helpers.display_name(r) for r in by_id[i]["recipients"]),
    )
    if st.button(f"Create {len(chosen)} list(s) for {target_year}", type="primary", width="stretch", disabled=not chosen):
        created = db.create_gift_lists([by_id[i] for i in chosen], user["username"], target_year)
        st.session_state["year"] = target_year
        helpers.flash(f"Created {created} list(s) for {target_year}", "🎄")
        st.rerun()


@st.dialog("Add a gift")
def add_gift(gift_list: dict, username: str) -> None:
    st.caption(f"Adding to **{gift_list['name']}**")
    with st.form(f"add_gift_{gift_list['id']}", border=False):
        name = st.text_input("Gift name *")
        description = st.text_input("Description (optional)")
        url = st.text_input("Link to shop (optional)", placeholder="https://…")
        c1, c2 = st.columns(2)
        price_raw = c1.text_input(f"Price in {helpers.CURRENCY} (optional)")
        image_raw = c2.text_input("Image URL (optional)")
        if st.form_submit_button("Add gift", type="primary", width="stretch"):
            clean_url = rules.clean_url(url)
            clean_image = rules.clean_url(image_raw)
            price = rules.parse_price(price_raw)
            if not name.strip():
                st.error("Please enter a gift name.")
            elif url.strip() and not clean_url:
                st.error("That doesn't look like a valid shop link.")
            elif image_raw.strip() and not clean_image:
                st.error("That doesn't look like a valid image link.")
            elif price_raw.strip() and price is None:
                st.error("Price must be a number, e.g. 1200.")
            else:
                db.add_gift(
                    gift_list["id"], name.strip(), description.strip(), username,
                    url=clean_url, price=price, image_url=clean_image,
                )
                helpers.flash("Gift added")
                st.rerun()


@st.dialog("Comments")
def comments(gift: dict, username: str) -> None:
    st.markdown(f"**{gift['name']}**")
    existing = db.get_comments_by_gift().get(gift["id"], [])
    if not existing:
        st.caption("No comments yet.")
    for c in existing:
        # user-written text is HTML-escaped because unsafe_allow_html is on
        st.markdown(
            f"<b>{html.escape(helpers.display_name(c['username']))}</b> "
            f"<span class='muted'>· {helpers.ago(c['created_at'])}</span><br>{html.escape(c['comment'])}",
            unsafe_allow_html=True,
        )
    with st.form(f"comment_{gift['id']}", border=False, clear_on_submit=True):
        text = st.text_input("Write a comment")
        if st.form_submit_button("Post", type="primary") and text.strip():
            db.add_comment(gift["id"], text.strip(), username)
            st.rerun()
