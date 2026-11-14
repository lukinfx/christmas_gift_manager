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
        helpers.go_to(target_year)
        helpers.flash(f"Created {created} list(s) for {target_year}", "🎄")
        st.rerun()


def _price_text(price) -> str:
    if price is None:
        return ""
    return str(int(price)) if float(price).is_integer() else str(price)


def _gift_form(key: str, submit_label: str, gift: dict | None = None) -> dict | None:
    """The gift fields, shared by 'Add' and 'Edit'. Returns validated values on a valid submit."""
    gift = gift or {}
    with st.form(key, border=False):
        name = st.text_input("Gift name *", value=gift.get("name") or "")
        description = st.text_input("Description (optional)", value=gift.get("description") or "")
        url = st.text_input("Link to shop (optional)", value=gift.get("url") or "", placeholder="https://…")
        c1, c2 = st.columns(2)
        price_raw = c1.text_input(f"Price in {helpers.CURRENCY} (optional)", value=_price_text(gift.get("price")))
        image_raw = c2.text_input("Image URL (optional)", value=gift.get("image_url") or "")
        submitted = st.form_submit_button(submit_label, type="primary", width="stretch")

    if not submitted:
        return None
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
        return {
            "name": name.strip(), "description": description.strip(),
            "url": clean_url, "price": price, "image_url": clean_image,
        }
    return None


@st.dialog("Add a gift")
def add_gift(gift_list: dict, username: str) -> None:
    st.caption(f"Adding to **{gift_list['name']}**")
    values = _gift_form(f"add_gift_{gift_list['id']}", "Add gift")
    if values:
        db.add_gift(gift_list["id"], values["name"], values["description"], username,
                    url=values["url"], price=values["price"], image_url=values["image_url"])
        helpers.flash("Gift added")
        st.rerun()


# ---- Sections of the gift modal (ui/lists.py). Plain functions, not dialogs: Streamlit can't open a
# ---- dialog from inside a dialog, so Edit / Move / Comments live in the one gift dialog.
# ---- They run inside that dialog's fragment, so st.rerun(scope="fragment") refreshes just the modal.

def edit_form(gift: dict, username: str, on_saved) -> None:
    if not rules.can_edit_gift(gift, username):  # the section is hidden for others; never trust the UI alone
        st.error("Only the person who added this gift can edit it.")
        return
    values = _gift_form(f"edit_gift_{gift['id']}", "Save changes", gift)
    if values:
        if db.update_gift(gift["id"], username, **values):
            st.toast("Gift updated", icon="✅")
        else:
            st.toast("Couldn't update this gift", icon="⚠️")
        on_saved()


def delete_section(gift: dict, username: str) -> None:
    """Two-step delete (no popover: keep it simple inside a modal)."""
    if not rules.can_delete_gift(gift, username):
        return
    st.divider()
    key = f"confirm_delete_{gift['id']}"
    if not st.session_state.get(key):
        if st.button("Delete this gift", icon=":material/delete:", width="stretch", key=f"ask_del_{gift['id']}"):
            st.session_state[key] = True
            st.rerun(scope="fragment")
        return
    st.warning("Delete this gift and its comments? This can't be undone.")
    yes, no = st.columns(2)
    if yes.button("Yes, delete", type="primary", width="stretch", key=f"yes_del_{gift['id']}"):
        db.delete_gift(gift["id"])
        st.session_state.pop(key, None)
        helpers.flash("Gift deleted", "🗑️")
        st.rerun()  # full rerun closes the modal
    if no.button("Cancel", width="stretch", key=f"no_del_{gift['id']}"):
        st.session_state.pop(key, None)
        st.rerun(scope="fragment")


def move_form(gift: dict, username: str) -> None:
    all_lists = db.get_all_lists()
    here = next((l for l in all_lists if l["id"] == gift["list_id"]), None)
    current_year = helpers.today().year
    if here is None or not rules.can_move_gift(gift, username, here["year"], current_year):
        # the section is hidden in these cases; never trust the UI alone
        st.error("Only the person who added a gift can move it, and only out of a list from another year.")
        return

    st.markdown(f"Move out of *{here['name']}* ({here['year']})")
    if (gift.get("status") or "available") != "available":
        st.warning("It has been reserved or bought. The status resets to available in the new list.")

    years = sorted({l["year"] for l in all_lists}, reverse=True)
    year = st.selectbox("Year", years, key=f"move_year_{gift['id']}")
    targets = rules.move_targets(all_lists, gift["list_id"], year)
    if not targets:
        st.info(f"There are no other lists in {year}. Create one first.")
        return

    by_id = {l["id"]: l for l in targets}
    target_id = st.selectbox(
        "List",
        list(by_id),
        key=f"move_target_{gift['id']}",
        format_func=lambda i: f"{by_id[i]['name']}  ·  for "
        + ", ".join(helpers.display_name(r) for r in by_id[i]["recipients"]),
    )
    if st.button("Move gift", type="primary", width="stretch", key=f"do_move_{gift['id']}"):
        if db.move_gift(gift["id"], username, target_id, current_year):
            # follow the gift: show the list it now lives in
            helpers.go_to(by_id[target_id]["year"], target_id)
            helpers.flash(f"Moved to {by_id[target_id]['name']}", "📦")
        else:
            helpers.flash("Couldn't move this gift", "⚠️")
        st.rerun()  # full rerun closes the modal


def comments_panel(gift: dict, username: str) -> None:
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
        if st.form_submit_button("Post", type="primary", width="stretch") and text.strip():
            db.add_comment(gift["id"], text.strip(), username)
            st.rerun(scope="fragment")
